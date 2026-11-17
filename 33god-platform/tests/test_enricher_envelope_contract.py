"""AC-1 drift guard: the enricher's session report is a Bloodbank-contract-valid envelope.

The enricher image cannot import bloodbank code, so enricher/bb_envelope.py
vendors a minimal builder. This test imports the REAL contract from the
bloodbank checkout (services/agent-hooks/core/validate.py plus
schemas/bloodbank/agent/session.annotated.json) and proves what the enricher
sends passes assert_contract AND the JSON Schema. If bloodbank changes the
contract (allowlist, base envelope, payload schema) and the vendored builder
does not follow, this goes red.

It also drives the real handler end to end with the HTTP layer stubbed, so the
wire format (URL, topic, Content-Type, body) is asserted, not just the dict.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
import unittest.mock
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_enricher_llm import PLATFORM_ROOT, STUBS, FakeResponse, _chat_ok, main  # noqa: E402

import bb_envelope  # noqa: E402  (enricher dir is on sys.path via test_enricher_llm)

BLOODBANK_ROOT = PLATFORM_ROOT.parent / "bloodbank"
VALIDATE_PY = BLOODBANK_ROOT / "services" / "agent-hooks" / "core" / "validate.py"
SCHEMA_PATH = BLOODBANK_ROOT / "schemas" / "bloodbank" / "agent" / "session.annotated.json"

SESSION_ID = "0d8c06e8-1fbb-5e96-bf89-22564a776074"
ENDED_ID = "dcd69da1-5d9a-42b8-a5a7-3cb69f678b43"
TRACEPARENT = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"


def _load_validate():
    spec = importlib.util.spec_from_file_location("bloodbank_core_validate", VALIDATE_PY)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ended(**overrides) -> dict:
    body = {
        "id": ENDED_ID,
        "type": "bloodbank.agent.session.ended",
        "correlationid": SESSION_ID,
        "traceparent": TRACEPARENT,
        "actor": {"type": "agent_cli", "agent_id": "bloodbank.agent.hermes", "cli": "hermes", "provider": None, "model": None},
        "data": {"session_id": "local-abc", "working_directory": "/home/delorenj/HeyMa"},
    }
    body.update(overrides)
    return body


@unittest.skipUnless(VALIDATE_PY.exists() and SCHEMA_PATH.exists(), "bloodbank checkout (validate.py + session.annotated.json) not present")
class SessionAnnotatedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validate = _load_validate()

    def _build(self, **kw) -> dict:
        args = dict(
            source_event=_ended(),
            session_id=SESSION_ID,
            cwd="/home/delorenj/HeyMa",
            summary="Did things.",
            summary_source="gateway",
            event_count=12,
            tool_call_count=7,
        )
        args.update(kw)
        return bb_envelope.build_session_annotated(**args)

    def test_type_and_subject_are_the_canonical_names(self) -> None:
        self.assertEqual(bb_envelope.SESSION_ANNOTATED_TYPE, "bloodbank.agent.session.annotated")
        self.assertEqual(bb_envelope.SESSION_ANNOTATED_SUBJECT, "bloodbank.evt.agent.session.annotated")
        self.assertEqual(
            self.validate.subject_for(bb_envelope.SESSION_ANNOTATED_TYPE, "event"),
            bb_envelope.SESSION_ANNOTATED_SUBJECT,
        )

    def test_envelope_passes_assert_contract(self) -> None:
        self.validate.assert_contract(self._build())

    def test_envelope_validates_against_the_schema_file(self) -> None:
        # validate_envelope = assert_contract + jsonschema with format checking
        # against schemas/bloodbank/agent/session.annotated.json.
        self.validate.validate_envelope(self._build())
        self.validate.validate_envelope(self._build(cwd=None, summary_source="heuristic", event_count=0, tool_call_count=0))
        self.validate.validate_envelope(self._build(summary_source="gateway_failed"))

    def test_schema_is_strict_so_the_guard_has_teeth(self) -> None:
        env = self._build()
        env["data"]["surprise"] = 1
        with self.assertRaises(self.validate.EnvelopeInvalid):
            self.validate.validate_envelope(env)
        env = self._build()
        env["data"]["summary_source"] = "magic"
        with self.assertRaises(self.validate.EnvelopeInvalid):
            self.validate.validate_envelope(env)

    def test_envelope_carries_the_bloodbank_fields_candystore_demanded(self) -> None:
        env = self._build()
        for field in ("producer", "service", "domain", "kind", "actor", "ordering_key", "schemaref", "dataschema", "traceparent"):
            self.assertIn(field, env)
        self.assertEqual((env["producer"], env["service"], env["domain"], env["kind"]), ("enricher", "enricher", "agent", "event"))
        self.assertEqual(env["dataschema"], "apicurio://holyfields/bloodbank.agent.session.annotated/versions/1")
        self.assertEqual(env["schemaref"], "bloodbank.agent.session.annotated.v1")

    def test_identity_and_causation_are_preserved(self) -> None:
        env = self._build()
        self.assertEqual(env["correlationid"], SESSION_ID)
        self.assertEqual(env["causationid"], ENDED_ID)
        self.assertEqual(env["data"]["target_event_id"], ENDED_ID)
        self.assertEqual(env["data"]["session_id"], SESSION_ID)
        self.assertEqual(env["traceparent"], TRACEPARENT)
        self.assertEqual(env["actor"]["agent_id"], "bloodbank.agent.hermes")
        self.assertEqual(env["ordering_key"], f"session:{SESSION_ID}")

    def test_missing_actor_and_traceparent_fall_back(self) -> None:
        src = _ended()
        del src["actor"], src["traceparent"]
        env = self._build(source_event=src)
        self.assertEqual(env["actor"]["type"], "service")
        self.assertEqual(env["traceparent"], bb_envelope.ZERO_TRACEPARENT)
        self.validate.validate_envelope(env)

    def test_non_uuid_session_id_is_hashed_for_correlationid_but_kept_in_data(self) -> None:
        env = self._build(session_id="local-abc")
        uuid.UUID(env["correlationid"])
        self.assertEqual(env["data"]["session_id"], "local-abc")
        self.validate.validate_envelope(env)

    def test_source_without_a_uuid_id_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            self._build(source_event=_ended(id="evt-1"))

    def test_event_id_is_deterministic_per_session_ended(self) -> None:
        first = self._build(now="2026-11-17T00:00:00.000Z", summary="a")
        again = self._build(now="2026-11-17T09:09:09.000Z", summary="b")
        self.assertEqual(first["id"], again["id"])
        other = self._build(source_event=_ended(id="11111111-2222-4333-8444-555555555555"))
        self.assertNotEqual(first["id"], other["id"])
        uuid.UUID(first["id"])
        # Pinned: the namespace must never change or redelivery stops being idempotent.
        self.assertEqual(bb_envelope.annotation_event_id(ENDED_ID), first["id"])


@unittest.skipUnless(VALIDATE_PY.exists() and SCHEMA_PATH.exists(), "bloodbank checkout not present")
class SessionReportOnTheWireTests(unittest.TestCase):
    """Drive the real handler; assert what actually reaches the Dapr sidecar."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.validate = _load_validate()

    def setUp(self) -> None:
        STUBS.posts.clear()
        STUBS.responses.clear()
        main._publish_attempts._counts.clear()
        main._rollup_cache._items.clear()
        self.sleeps: list[float] = []
        self.dead_letters: list[tuple] = []
        self.dead_letter_ok = True

        def record(body, event_id, reason, error):
            self.dead_letters.append((event_id, reason, error, body))
            return self.dead_letter_ok

        for p in (
            unittest.mock.patch.object(main, "_sleep", self.sleeps.append),
            unittest.mock.patch.object(main, "_record_dead_letter", record),
        ):
            p.start()
            self.addCleanup(p.stop)

    def _run(self, publish_status: int = 200, env: dict | None = None):
        events = [
            {"data": {"working_directory": "/home/delorenj/HeyMa"}},
            {"data": {"tool_name": "write_file", "arguments": {"p": 1}, "status": "success"}},
            {"data": {"name": "run_tests", "arguments": {}, "outcome": "ok"}},
        ]
        STUBS.responses.clear()
        if not main._rollup_cache._items:  # a cached roll-up (publish retry) skips the fetch and the LLM call
            STUBS.responses.extend([FakeResponse(payload={"events": events}), _chat_ok("Shipped the thing.")])
        STUBS.responses.append(FakeResponse(status_code=publish_status, text="boom"))
        env = {"PATH": "/usr/bin", "OPENAI_COMPAT_API_KEY": "shared", **(env or {})}
        with unittest.mock.patch.dict(main.os.environ, env, clear=True):
            return main._do_handle_session_ended(_ended())

    def test_publish_goes_to_the_canonical_topic_as_a_cloudevents_json_body(self) -> None:
        status = self._run()
        self.assertEqual(status, {"status": "SUCCESS"})
        publish = STUBS.posts[-1]
        self.assertTrue(
            publish["url"].endswith("/v1.0/publish/bloodbank-pubsub/bloodbank.evt.agent.session.annotated"),
            publish["url"],
        )
        # application/cloudevents+json is what stops Dapr wrapping the body as com.dapr.event.sent.
        self.assertEqual(publish["headers"]["Content-Type"], "application/cloudevents+json")
        envelope = json.loads(publish["data"])
        self.validate.validate_envelope(envelope)
        self.assertEqual(envelope["data"]["session_id"], SESSION_ID)
        self.assertEqual(envelope["data"]["cwd"], "/home/delorenj/HeyMa")
        self.assertEqual(envelope["data"]["summary"], "Shipped the thing.")
        self.assertEqual(envelope["data"]["event_count"], 3)
        self.assertEqual(envelope["data"]["tool_call_count"], 2)
        self.assertEqual(envelope["data"]["summary_source"], "gateway")

    def test_redelivery_republishes_the_same_event_id(self) -> None:
        self._run()
        first = json.loads(STUBS.posts[-1]["data"])["id"]
        STUBS.posts.clear()
        self._run()
        self.assertEqual(json.loads(STUBS.posts[-1]["data"])["id"], first)

    def test_publish_failure_is_not_a_silent_success_and_is_bounded(self) -> None:
        self.assertEqual(self._run(publish_status=500), {"status": "RETRY"})
        for _ in range(3):
            self.assertEqual(self._run(publish_status=500), {"status": "RETRY"})
        # PUBLISH_MAX_ATTEMPTS (default 5): the fifth failure stops the loop.
        self.assertEqual(self._run(publish_status=500), {"status": "DROP"})
        # ...and a later success still works and resets the count.
        self.assertEqual(self._run(), {"status": "SUCCESS"})

    def test_publish_retries_back_off_exponentially(self) -> None:
        for _ in range(4):
            self.assertEqual(self._run(publish_status=500), {"status": "RETRY"})
        self.assertEqual(self.sleeps, [1.0, 2.0, 4.0, 8.0])

    def test_publish_retry_reuses_the_summary_instead_of_calling_the_llm_again(self) -> None:
        self.assertEqual(self._run(publish_status=500), {"status": "RETRY"})
        STUBS.responses.clear()
        # Retry: only the publish may hit the wire (no session fetch, no gateway call).
        STUBS.responses.append(FakeResponse(status_code=200, text="ok"))
        posts_before = len(STUBS.posts)
        with unittest.mock.patch.dict(main.os.environ, {"PATH": "/usr/bin", "OPENAI_COMPAT_API_KEY": "shared"}, clear=True):
            self.assertEqual(main._do_handle_session_ended(_ended()), {"status": "SUCCESS"})
        self.assertEqual(len(STUBS.posts) - posts_before, 1)
        self.assertEqual(json.loads(STUBS.posts[-1]["data"])["data"]["summary"], "Shipped the thing.")
        self.assertEqual(len(main._rollup_cache._items), 0)

    def test_exhausted_publish_is_dead_lettered_not_silently_dropped(self) -> None:
        for _ in range(4):
            self._run(publish_status=500)
        self.assertEqual(self._run(publish_status=500), {"status": "DROP"})
        self.assertEqual(len(self.dead_letters), 1)
        event_id, reason, error, body = self.dead_letters[0]
        self.assertEqual(reason, "session_annotation_publish_failed")
        self.assertEqual(event_id, ENDED_ID)
        self.assertEqual(body["id"], ENDED_ID)  # the session.ended envelope, replayable
        self.assertIn("5 times", error)
        self.assertEqual(len(main._rollup_cache._items), 0)

    def test_failed_dead_letter_write_keeps_retrying_for_a_bounded_few(self) -> None:
        self.dead_letter_ok = False
        for _ in range(4):
            self._run(publish_status=500)
        # Deliveries 5..7 cannot record the dead_letter row: RETRY; the 8th gives up loudly.
        self.assertEqual([self._run(publish_status=500)["status"] for _ in range(4)], ["RETRY", "RETRY", "RETRY", "DROP"])


if __name__ == "__main__":
    unittest.main()
