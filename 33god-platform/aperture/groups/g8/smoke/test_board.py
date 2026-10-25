"""Unit tests for the G8 board adapter state machine + event shapes (no bus,
no HTTP; publish path exercised with a stub connection)."""
import json
import os
import sqlite3
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "board"))
import adapter  # noqa: E402


class StubNats:
    """Records published envelopes; answers a real publish-ack shape."""

    def __init__(self):
        self.published = []

    def publish_ack(self, subject, payload, timeout=5.0):
        self.published.append((subject, payload))
        return {"stream": "BLOODBANK_EVENTS", "seq": len(self.published)}

    def close(self):
        pass


def patch_bus(stub):
    adapter.jsclient.NatsConn = lambda url, connect_timeout=5.0: stub


class BoardStateMachineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        adapter.DB_PATH = os.path.join(self.tmp.name, "board.db")
        self.stub = StubNats()
        patch_bus(self.stub)

    def tearDown(self):
        self.tmp.cleanup()

    def _create(self, title="add one acceptance doc page"):
        return adapter.command({"action": "create", "title": title})

    def test_create_starts_in_backlog_with_lifecycle_correlationid(self):
        r = self._create()
        t = r["ticket"]
        self.assertEqual(t["state"], "backlog")
        uuid.UUID(t["correlationid"])  # valid UUID
        self.assertIsNone(t["commit_sha"])
        # one canonical event published
        subj, env = self.stub.published[-1]
        self.assertEqual(env["type"], "bloodbank.task.ticket.created")
        self.assertEqual(subj, "bloodbank.evt.task.ticket.created")
        self.assertEqual(env["correlationid"], t["correlationid"])

    def test_full_cycle_done_requires_evidence(self):
        r = self._create("small real task")
        tid = r["ticket"]["id"]
        # done from backlog is refused (must go through in_progress)
        with self.assertRaises(ValueError):
            adapter.command({"action": "done", "ticket_id": tid,
                             "commit_sha": "a" * 40, "tests_passed": True})
        adapter.command({"action": "start", "ticket_id": tid})
        # done without evidence refused
        with self.assertRaises(ValueError):
            adapter.command({"action": "done", "ticket_id": tid})
        with self.assertRaises(ValueError):
            adapter.command({"action": "done", "ticket_id": tid, "tests_passed": True})
        with self.assertRaises(ValueError):
            adapter.command({"action": "done", "ticket_id": tid, "commit_sha": "abc"})
        # with evidence: done
        r = adapter.command({"action": "done", "ticket_id": tid,
                             "commit_sha": "b" * 40, "tests_passed": True})
        self.assertEqual(r["ticket"]["state"], "done")
        self.assertEqual(r["ticket"]["commit_sha"], "b" * 40)
        self.assertTrue(r["ticket"]["tests_passed"])
        # double-done refused (not in_progress anymore)
        with self.assertRaises(ValueError):
            adapter.command({"action": "done", "ticket_id": tid,
                             "commit_sha": "c" * 40, "tests_passed": True})

    def test_one_correlationid_across_whole_lifecycle(self):
        r = self._create("chain test")
        tid = r["ticket"]["id"]
        corr = r["ticket"]["correlationid"]
        adapter.command({"action": "start", "ticket_id": tid})
        adapter.command({"action": "done", "ticket_id": tid,
                         "commit_sha": "d" * 40, "tests_passed": True})
        types = [env["type"] for _, env in self.stub.published]
        self.assertEqual(types, ["bloodbank.task.ticket.created",
                                 "bloodbank.task.ticket.started",
                                 "bloodbank.task.ticket.completed"])
        # EVERY envelope carries the same lifecycle correlationid
        for _, env in self.stub.published:
            self.assertEqual(env["correlationid"], corr)
            self.assertEqual(env["data"]["correlationid"], corr)

    def test_envelope_canonical_shape(self):
        self._create()
        _, env = self.stub.published[-1]
        toks = env["type"].split(".")
        self.assertEqual(len(toks), 4)                      # 4-token type
        self.assertEqual(toks[0], "bloodbank")
        self.assertEqual(env["subject"], "bloodbank.evt." + ".".join(toks[1:]))  # 5-token
        self.assertNotEqual(env["type"], env["subject"])    # no conflation
        self.assertEqual(env["domain"], toks[1])
        self.assertEqual(env["kind"], "event")
        self.assertIn("ordering_key", env)
        self.assertEqual(env["producer"], "aperture-g8-board")
        self.assertEqual(env["specversion"], "1.0")
        for req in ("id", "source", "type", "time", "producer", "service",
                    "domain", "kind", "subject", "datacontenttype", "data"):
            self.assertIn(req, env, f"missing {req}")

    def test_rejects_empty_title_and_unknown_action(self):
        with self.assertRaises(ValueError):
            adapter.command({"action": "create", "title": "   "})
        with self.assertRaises(ValueError):
            adapter.command({"action": "explode"})
        with self.assertRaises(ValueError):
            adapter.command({"action": "start", "ticket_id": "no-such-ticket"})

    def test_persistence_across_reopen(self):
        r = self._create("persist me")
        tid = r["ticket"]["id"]
        adapter.command({"action": "start", "ticket_id": tid})
        # new connection == process restart semantics
        with sqlite3.connect(adapter.DB_PATH) as conn:
            row = conn.execute("SELECT state FROM tickets WHERE id=?", (tid,)).fetchone()
        self.assertEqual(row[0], "in_progress")


if __name__ == "__main__":
    unittest.main()
