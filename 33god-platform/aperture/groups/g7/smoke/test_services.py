"""Unit tests for hindsight-bridge config/degradation + memory-reference
ingest/query (no bus, no HTTP, no external LLM)."""
import json
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

# Import both servers as modules from their sibling dirs.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hindsight-bridge"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "memory-reference"))

import importlib

def _load_bridge(env: dict):
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "bridge_under_test",
        str(Path(__file__).resolve().parent.parent / "hindsight-bridge" / "server.py"))
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return _mod


def event(etype="bloodbank.aperture.smoke.g7"):
    eid = str(uuid.uuid4())
    return {"id": eid, "source": "urn:33god:aperture:g7-smoke", "type": etype,
            "subject": "bloodbank.evt." + etype.split(".", 1)[1],
            "time": "2026-10-24T12:00:00Z", "producer": "aperture-g7-smoke",
            "service": "smoke", "domain": etype.split(".")[1], "kind": "event",
            "actor": {"type": "operator", "agent_id": "o", "cli": "g7-test-cli"},
            "data": {"project": "33GOD", "note": "pyramid alignment ritual"}}


class BridgeDegradedTests(unittest.TestCase):
    def test_degraded_when_llm_empty(self):
        bridge = _load_bridge({"GOD_LLM_BASE_URL": "", "GOD_LLM_API_KEY": ""})
        self.assertFalse(bridge.LLM_READY)
        reason = bridge.degraded_reason()
        self.assertIn("degraded", reason)
        self.assertIn("GOD_LLM_BASE_URL", reason)
        self.assertIn("GOD_LLM_API_KEY", reason)
        # embed degrades to None, never raises
        self.assertIsNone(bridge.embed(["hello"]))
        self.assertIsNone(bridge.rerank("q", [{"a": 1}]))
        st = bridge.llm_status()
        self.assertFalse(st["configured"])
        self.assertIsNone(st["base_url"])

    def test_configured_when_set(self):
        bridge = _load_bridge({"GOD_LLM_BASE_URL": "http://10.9.8.7:8000",
                               "GOD_LLM_API_KEY": "test-key-not-real"})
        self.assertTrue(bridge.LLM_READY)
        self.assertIsNone(bridge.degraded_reason())
        # a dead endpoint degrades to None, never raises
        self.assertIsNone(bridge.embed(["x"]))

    def test_backends_parse(self):
        bridge = _load_bridge({"GOD_MEMORY_BACKENDS":
                               "hindsight=http://hindsight:8080; other=http://x/"})
        self.assertEqual(bridge.MEMORY_BACKENDS,
                         {"hindsight": "http://hindsight:8080", "other": "http://x"})

    def test_fanout_isolated_failure(self):
        bridge = _load_bridge({"GOD_MEMORY_BACKENDS": "dead=http://127.0.0.1:1"})
        report = bridge.fan_out([event()])
        self.assertIn("error", report["dead"])

    def test_healthz_exposes_backend_errors(self):
        # Rererere follow-up 2026-10-24: acked bus consumption != stored
        # memory; the error counter must be visible in healthz.
        bridge = _load_bridge({"GOD_MEMORY_BACKENDS": "dead=http://127.0.0.1:1",
                               "GOD_LLM_BASE_URL": "", "GOD_LLM_API_KEY": ""})
        bridge.fan_out([event()])
        self.assertGreaterEqual(bridge.HEALTH["backend_errors"], 1)


class MemoryReferenceTests(unittest.TestCase):
    def _load_memory(self):
        import importlib.util as ilu
        spec = ilu.spec_from_file_location(
            "memory_under_test",
            str(Path(__file__).resolve().parent.parent / "memory-reference" / "server.py"))
        mod = ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.memory = self._load_memory()
        self.memory.DB_PATH = os.path.join(self.tmp.name, "memory.db")
        self.memory._conn = None

    def tearDown(self):
        self.tmp.cleanup()

    def test_ingest_and_keyword_query(self):
        e1 = event()
        e1["data"]["note"] = "pyramid alignment ritual"
        e2 = event("bloodbank.voice.recording.landed")
        e2["data"]["note"] = "unrelated whale facts"
        self.assertEqual(self.memory.ingest([e1, e2]), 2)
        hits = self.memory.query("pyramid", 10)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["event_id"], e1["id"])
        self.assertEqual(hits[0]["type"], e1["type"])
        # envelope-level term (producer) is searchable
        hits = self.memory.query("aperture-g7-smoke", 10)
        self.assertEqual(len(hits), 2)
        # data.* project field is searchable (contract includes select data keys)
        hits = self.memory.query("33GOD", 10)
        self.assertEqual(len(hits), 2)

    def test_ingest_is_idempotent_on_replay(self):
        # Rererere follow-up 2026-10-24: replayed events (bridge restart,
        # JetStream redelivery) must not duplicate. Recall must be deduped.
        e = event()
        self.assertEqual(self.memory.ingest([e]), 1)
        self.assertEqual(self.memory.ingest([e]), 1)      # exact replay
        self.assertEqual(self.memory.ingest([e, e]), 1)   # replay in one batch
        other = event("bloodbank.voice.recording.landed")
        self.assertEqual(self.memory.ingest([e, other]), 2)  # mixed batch
        for term in ("pyramid", "33GOD", "g7-test-cli"):
            hits = self.memory.query(term, 10)
            ids = [h["event_id"] for h in hits]
            self.assertEqual(ids, list(dict.fromkeys(ids)), f"duplicates for {term}")
            self.assertEqual(len(hits), 2, f"expected both events for {term}")

    def test_fts_syntax_is_escaped(self):
        self.memory.ingest([event()])
        # a query that would be FTS syntax errors if unescaped must work
        hits = self.memory.query("NOT OR AND", 10)
        self.assertEqual(hits, [])

    def test_query_no_matches(self):
        self.memory.ingest([event()])
        self.assertEqual(self.memory.query("zzz-no-such-term", 10), [])


if __name__ == "__main__":
    unittest.main()
