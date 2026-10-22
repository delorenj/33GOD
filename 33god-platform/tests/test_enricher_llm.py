"""Unit tests for the enricher's AutomaticAI gateway LLM integration.

Imports enricher/main.py with the heavy runtime deps (sentence_transformers,
fastapi, psycopg2, requests) replaced by in-process stubs so the suite runs
anywhere. Exercises the gateway defaults, key fallback chain, the
json_schema 400-retry path, and defensive JSON parsing end to end through
the event handlers.
"""

from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

PLATFORM_ROOT = Path(__file__).resolve().parents[1]

GATEWAY_URL = "https://api.automaticai.io/v1/chat/completions"
DEFAULT_MODEL = "automaticai/auto/fast"


class FakeHTTPError(Exception):
    pass


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise FakeHTTPError(f"HTTP {self.status_code}: {self.text}")


def _install_stubs() -> tuple[types.ModuleType, list[dict]]:
    """Seed sys.modules with stubs for main.py's imports; return the requests
    stub and its call log."""
    requests_stub = types.ModuleType("requests")
    posts: list[dict] = []
    responses: list[FakeResponse] = []
    gets: list[FakeResponse] = []

    def _post(url, headers=None, json=None, timeout=None):
        # deepcopy: _chat_completion mutates its payload dict on the 400 retry,
        # and the log must preserve what each call actually sent.
        posts.append({"url": url, "headers": dict(headers or {}), "json": copy.deepcopy(json), "timeout": timeout})
        return responses.pop(0)

    def _get(url, timeout=None):
        gets.append(url)
        return responses.pop(0)

    requests_stub.post = _post
    requests_stub.get = _get
    requests_stub.exceptions = types.SimpleNamespace(HTTPError=FakeHTTPError)

    fastapi_stub = types.ModuleType("fastapi")
    fastapi_stub.FastAPI = lambda: types.SimpleNamespace(get=lambda *a, **k: (lambda f: f), post=lambda *a, **k: (lambda f: f))
    fastapi_stub.Request = object
    fastapi_stub.Response = lambda **kwargs: types.SimpleNamespace(status_code=kwargs.get("status_code", 200))

    sentence_transformers_stub = types.ModuleType("sentence_transformers")

    class _FakeModel:
        def encode(self, _text):
            return types.SimpleNamespace(tolist=lambda: [0.0] * 8)

    sentence_transformers_stub.SentenceTransformer = lambda *a, **k: _FakeModel()

    psycopg2_stub = types.ModuleType("psycopg2")
    psycopg2_stub.Error = Exception

    class _FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, *a, **k):
            return None

    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def cursor(self):
            return _FakeCursor()

    psycopg2_stub.connect = lambda *a, **k: _FakeConn()

    for name, module in (
        ("fastapi", fastapi_stub),
        ("sentence_transformers", sentence_transformers_stub),
        ("psycopg2", psycopg2_stub),
        ("requests", requests_stub),
    ):
        sys.modules.setdefault(name, module)

    stub_state = types.SimpleNamespace(posts=posts, responses=responses, gets=gets)
    sys.modules["_enricher_test_stubs"] = stub_state
    return requests_stub, posts


def _load_main():
    spec = importlib.util.spec_from_file_location("enricher_main", PLATFORM_ROOT / "enricher" / "main.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


_install_stubs()
main = _load_main()
STUBS = sys.modules["_enricher_test_stubs"]


def _chat_ok(content: str) -> FakeResponse:
    return FakeResponse(payload={"choices": [{"message": {"content": content}}]})


def _tool_event_body() -> dict:
    return {
        "id": "evt-1",
        "correlationid": "sess-1",
        "data": {
            "tool_name": "write_file",
            "arguments": {"path": "/tmp/x", "Cwd": "/repo"},
            "status": "success",
        },
    }


class GatewayConfigTests(unittest.TestCase):
    def test_endpoint_and_model_default_to_the_gateway(self) -> None:
        env = {"PATH": "/usr/bin"}
        with mock.patch.dict(main.os.environ, env, clear=True):
            self.assertEqual(main._gateway_endpoint("JEV_ENDPOINT"), GATEWAY_URL)
            self.assertEqual(main._gateway_endpoint("SUMMARY_ENDPOINT"), GATEWAY_URL)
            self.assertEqual(main._gateway_model("JEV_MODEL"), DEFAULT_MODEL)
            self.assertEqual(main._gateway_model("SESSION_SUMMARY_MODEL"), DEFAULT_MODEL)

    def test_endpoint_and_model_env_overrides_win(self) -> None:
        env = {
            "PATH": "/usr/bin",
            "JEV_ENDPOINT": "http://elsewhere/v1/chat/completions",
            "SUMMARY_ENDPOINT": "http://summary-only/v1/chat/completions",
            "JEV_MODEL": "other/model",
            "SESSION_SUMMARY_MODEL": "summary/model",
        }
        with mock.patch.dict(main.os.environ, env, clear=True):
            self.assertEqual(main._gateway_endpoint("JEV_ENDPOINT"), "http://elsewhere/v1/chat/completions")
            self.assertEqual(main._gateway_endpoint("SUMMARY_ENDPOINT"), "http://summary-only/v1/chat/completions")
            self.assertEqual(main._gateway_model("JEV_MODEL"), "other/model")
            self.assertEqual(main._gateway_model("SESSION_SUMMARY_MODEL"), "summary/model")

    def test_specific_key_wins_over_shared_fallback(self) -> None:
        env = {"PATH": "/usr/bin", "JEV_API_KEY": "jev-token", "OPENAI_COMPAT_API_KEY": "shared"}
        with mock.patch.dict(main.os.environ, env, clear=True):
            self.assertEqual(main._gateway_key("JEV_API_KEY"), "jev-token")
            self.assertEqual(main._gateway_key("SUMMARY_API_KEY"), "shared")

    def test_shared_key_covers_both_calls_when_specifics_absent(self) -> None:
        env = {"PATH": "/usr/bin", "OPENAI_COMPAT_API_KEY": "shared"}
        with mock.patch.dict(main.os.environ, env, clear=True):
            self.assertEqual(main._gateway_key("JEV_API_KEY"), "shared")
            self.assertEqual(main._gateway_key("SUMMARY_API_KEY"), "shared")

    def test_empty_specific_key_falls_back_and_no_key_is_none(self) -> None:
        env = {"PATH": "/usr/bin", "JEV_API_KEY": "", "OPENAI_COMPAT_API_KEY": "shared"}
        with mock.patch.dict(main.os.environ, env, clear=True):
            self.assertEqual(main._gateway_key("JEV_API_KEY"), "shared")
        with mock.patch.dict(main.os.environ, {"PATH": "/usr/bin"}, clear=True):
            self.assertIsNone(main._gateway_key("JEV_API_KEY"))
            self.assertIsNone(main._gateway_key("SUMMARY_API_KEY"))


class ChatCompletionTests(unittest.TestCase):
    def setUp(self) -> None:
        STUBS.posts.clear()
        STUBS.responses.clear()

    def test_plain_completion_sends_bearer_key_and_returns_content(self) -> None:
        STUBS.responses.append(_chat_ok("hi"))
        content = main._chat_completion(GATEWAY_URL, "tok", DEFAULT_MODEL, [{"role": "user", "content": "x"}])
        self.assertEqual(content, "hi")
        self.assertEqual(len(STUBS.posts), 1)
        call = STUBS.posts[0]
        self.assertEqual(call["url"], GATEWAY_URL)
        self.assertEqual(call["headers"]["Authorization"], "Bearer tok")
        self.assertEqual(call["json"]["model"], DEFAULT_MODEL)
        self.assertNotIn("response_format", call["json"])

    def test_json_schema_rejected_with_400_retries_once_without_it(self) -> None:
        STUBS.responses.extend([
            FakeResponse(status_code=400, text="response_format json_schema unsupported"),
            _chat_ok('{"is_slop": false, "confidence": 0.1, "reason": "fine"}'),
        ])
        response_format = {"type": "json_schema", "json_schema": {"name": "slop_classification", "strict": True}}
        content = main._chat_completion(
            GATEWAY_URL, "tok", DEFAULT_MODEL, [{"role": "user", "content": "x"}],
            response_format=response_format,
        )
        self.assertEqual(content, '{"is_slop": false, "confidence": 0.1, "reason": "fine"}')
        self.assertEqual(len(STUBS.posts), 2)
        self.assertIn("response_format", STUBS.posts[0]["json"])
        self.assertEqual(STUBS.posts[0]["json"]["response_format"], response_format)
        self.assertNotIn("response_format", STUBS.posts[1]["json"])
        self.assertEqual(STUBS.posts[1]["url"], GATEWAY_URL)
        self.assertEqual(STUBS.posts[1]["json"]["model"], DEFAULT_MODEL)

    def test_400_without_response_format_does_not_retry(self) -> None:
        STUBS.responses.append(FakeResponse(status_code=400, text="bad request"))
        with self.assertRaises(FakeHTTPError):
            main._chat_completion(GATEWAY_URL, "tok", DEFAULT_MODEL, [{"role": "user", "content": "x"}])
        self.assertEqual(len(STUBS.posts), 1)

    def test_500_with_response_format_does_not_retry(self) -> None:
        STUBS.responses.extend([
            FakeResponse(status_code=500, text="upstream exploded"),
            _chat_ok("never reached"),
        ])
        with self.assertRaises(FakeHTTPError):
            main._chat_completion(
                GATEWAY_URL, "tok", DEFAULT_MODEL, [{"role": "user", "content": "x"}],
                response_format={"type": "json_schema"},
            )
        self.assertEqual(len(STUBS.posts), 1)


class ParseJsonContentTests(unittest.TestCase):
    def test_plain_json_object_parses(self) -> None:
        self.assertEqual(main._parse_json_content('{"a": 1}'), {"a": 1})

    def test_markdown_fenced_json_parses(self) -> None:
        fenced = '```json\n{"is_slop": true, "confidence": 0.9, "reason": "slop"}\n```'
        self.assertEqual(main._parse_json_content(fenced)["is_slop"], True)

    def test_non_object_json_returns_none(self) -> None:
        self.assertIsNone(main._parse_json_content("[1, 2, 3]"))

    def test_garbage_returns_none(self) -> None:
        self.assertIsNone(main._parse_json_content("the model rambled"))

    def test_empty_returns_none(self) -> None:
        self.assertIsNone(main._parse_json_content(""))
        self.assertIsNone(main._parse_json_content(None))


class SessionSummaryHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        STUBS.posts.clear()
        STUBS.responses.clear()

    def _run(self, body: dict) -> None:
        asyncio.run(main._do_handle_session_ended(body))

    def test_summary_targets_gateway_defaults_and_emits_report(self) -> None:
        events = [
            {"data": {"tool_name": "write_file", "arguments": {"p": 1}, "status": "success", "cwd": "/repo"}},
            {"data": {"name": "run_tests", "arguments": {}, "outcome": "ok"}},
        ]
        STUBS.responses.extend([
            FakeResponse(payload={"events": events}),  # candystore fetch
            _chat_ok("Did things and shipped them."),
        ])
        emitted = {}
        with mock.patch.dict(main.os.environ, {"PATH": "/usr/bin", "OPENAI_COMPAT_API_KEY": "shared"}, clear=True):
            with mock.patch.object(main, "emit_event", side_effect=lambda topic, payload: emitted.update({"topic": topic, "payload": payload})):
                self._run({"correlationid": "sess-1", "data": {}})
        post = STUBS.posts[0]
        self.assertEqual(post["url"], GATEWAY_URL)
        self.assertEqual(post["json"]["model"], DEFAULT_MODEL)
        self.assertNotIn("response_format", post["json"])
        self.assertEqual(post["headers"]["Authorization"], "Bearer shared")
        self.assertEqual(emitted["topic"], "bloodbank.evt.report.session.completed")
        self.assertEqual(emitted["payload"]["summary"], "Did things and shipped them.")
        self.assertEqual(emitted["payload"]["session_id"], "sess-1")
        self.assertEqual(emitted["payload"]["cwd"], "/repo")
        self.assertEqual(emitted["payload"]["event_count"], 2)

    def test_no_key_uses_heuristic_and_makes_no_llm_call(self) -> None:
        STUBS.responses.append(FakeResponse(payload={"events": [{"data": {"tool_name": "t", "arguments": {}, "status": "ok"}}]}))
        emitted = {}
        with mock.patch.dict(main.os.environ, {"PATH": "/usr/bin"}, clear=True):
            with mock.patch.object(main, "emit_event", side_effect=lambda topic, payload: emitted.update({"topic": topic, "payload": payload})):
                self._run({"correlationid": "sess-1", "data": {}})
        self.assertEqual(STUBS.posts, [])
        self.assertEqual(emitted["payload"]["summary"], "Session completed with 1 tool invocations.")

    def test_specific_summary_endpoint_and_model_override(self) -> None:
        STUBS.responses.extend([
            FakeResponse(payload={"events": [{"data": {"tool_name": "t", "arguments": {}, "status": "ok"}}]}),
            _chat_ok("summary"),
        ])
        emitted = {}
        env = {
            "PATH": "/usr/bin",
            "SUMMARY_API_KEY": "sum-token",
            "SUMMARY_ENDPOINT": "http://summary-gw/v1/chat/completions",
            "SESSION_SUMMARY_MODEL": "automaticai/free",
        }
        with mock.patch.dict(main.os.environ, env, clear=True):
            with mock.patch.object(main, "emit_event", side_effect=lambda topic, payload: emitted.update({"topic": topic, "payload": payload})):
                self._run({"correlationid": "sess-1", "data": {}})
        self.assertEqual(STUBS.posts[0]["url"], "http://summary-gw/v1/chat/completions")
        self.assertEqual(STUBS.posts[0]["json"]["model"], "automaticai/free")
        self.assertEqual(STUBS.posts[0]["headers"]["Authorization"], "Bearer sum-token")


class SlopGateHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        STUBS.posts.clear()
        STUBS.responses.clear()

    def _run(self, body: dict) -> dict:
        return asyncio.run(main._do_handle_tool_completed(body))

    def test_slop_detection_round_trip_through_gateway(self) -> None:
        STUBS.responses.append(_chat_ok('{"is_slop": true, "confidence": 0.88, "reason": "generic filler"}'))
        emitted = {}
        with mock.patch.dict(main.os.environ, {"PATH": "/usr/bin", "OPENAI_COMPAT_API_KEY": "shared"}, clear=True):
            with mock.patch.object(main, "emit_event", side_effect=lambda topic, payload: emitted.update({"topic": topic, "payload": payload})):
                status = self._run(_tool_event_body())
        self.assertEqual(status, {"status": "SUCCESS"})
        post = STUBS.posts[0]
        self.assertEqual(post["url"], GATEWAY_URL)
        self.assertEqual(post["json"]["model"], DEFAULT_MODEL)
        self.assertEqual(post["headers"]["Authorization"], "Bearer shared")
        self.assertEqual(post["json"]["response_format"]["type"], "json_schema")
        self.assertEqual(emitted["topic"], "bloodbank.evt.review.slop.annotated")
        self.assertEqual(emitted["payload"]["target_event_id"], "evt-1")
        self.assertEqual(emitted["payload"]["confidence"], 0.88)
        self.assertEqual(emitted["payload"]["reason"], "generic filler")
        self.assertEqual(emitted["payload"]["cwd"], "/repo")

    def test_schema_rejection_falls_back_to_bare_json_and_still_annotates(self) -> None:
        STUBS.responses.extend([
            FakeResponse(status_code=400, text="json_schema unsupported upstream"),
            _chat_ok('```json\n{"is_slop": true, "confidence": 0.5, "reason": "fenced"}\n```'),
        ])
        emitted = {}
        with mock.patch.dict(main.os.environ, {"PATH": "/usr/bin", "OPENAI_COMPAT_API_KEY": "shared"}, clear=True):
            with mock.patch.object(main, "emit_event", side_effect=lambda topic, payload: emitted.update({"topic": topic, "payload": payload})):
                status = self._run(_tool_event_body())
        self.assertEqual(status, {"status": "SUCCESS"})
        self.assertEqual(len(STUBS.posts), 2)
        self.assertNotIn("response_format", STUBS.posts[1]["json"])
        self.assertEqual(emitted["payload"]["confidence"], 0.5)

    def test_unparseable_content_skips_annotation_without_failing(self) -> None:
        STUBS.responses.append(_chat_ok("definitely not json"))
        emitted = {}
        with mock.patch.dict(main.os.environ, {"PATH": "/usr/bin", "OPENAI_COMPAT_API_KEY": "shared"}, clear=True):
            with mock.patch.object(main, "emit_event", side_effect=lambda topic, payload: emitted.update({"topic": topic, "payload": payload})):
                status = self._run(_tool_event_body())
        self.assertEqual(status, {"status": "SUCCESS"})
        self.assertEqual(emitted, {})

    def test_not_slop_emits_nothing(self) -> None:
        STUBS.responses.append(_chat_ok('{"is_slop": false, "confidence": 0.02, "reason": "real work"}'))
        emitted = {}
        with mock.patch.dict(main.os.environ, {"PATH": "/usr/bin", "OPENAI_COMPAT_API_KEY": "shared"}, clear=True):
            with mock.patch.object(main, "emit_event", side_effect=lambda topic, payload: emitted.update({"topic": topic, "payload": payload})):
                self._run(_tool_event_body())
        self.assertEqual(emitted, {})

    def test_no_key_skips_llm_entirely(self) -> None:
        emitted = {}
        with mock.patch.dict(main.os.environ, {"PATH": "/usr/bin"}, clear=True):
            with mock.patch.object(main, "emit_event", side_effect=lambda topic, payload: emitted.update({"topic": topic, "payload": payload})):
                status = self._run(_tool_event_body())
        self.assertEqual(status, {"status": "SUCCESS"})
        self.assertEqual(STUBS.posts, [])
        self.assertEqual(emitted, {})


if __name__ == "__main__":
    unittest.main()
