"""Unit tests for G8 momod: WIP lease protocol + cycle events (no bus, no
HTTP; board/code-worker stubbed)."""
import json
import os
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "momod"))
import orchestrator  # noqa: E402


class StubNats:
    def __init__(self):
        self.published = []

    def publish_ack(self, subject, payload, timeout=5.0):
        self.published.append((subject, payload))
        return {"stream": "BLOODBANK_EVENTS", "seq": len(self.published)}

    def close(self):
        pass


class WipLeaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        orchestrator.LOCK_PATH = os.path.join(self.tmp.name, "wip.lock")
        orchestrator.LEASE_TTL = 60
        orchestrator.LEASE_OWNER = "test-owner-a"

    def tearDown(self):
        self.tmp.cleanup()

    def test_acquire_then_refuse_second_owner(self):
        self.assertEqual(orchestrator.lease_acquire(), "acquired")
        orchestrator.LEASE_OWNER = "test-owner-b"
        self.assertEqual(orchestrator.lease_acquire(), "refused")

    def test_heartbeat_keeps_lease_fresh(self):
        self.assertEqual(orchestrator.lease_acquire(), "acquired")
        orchestrator.LEASE_TTL = 0  # force staleness window
        orchestrator.lease_heartbeat()  # but heartbeat refreshes it
        orchestrator.LEASE_TTL = 60
        orchestrator.LEASE_OWNER = "test-owner-b"
        # fresh heartbeat => still refused
        self.assertEqual(orchestrator.lease_acquire(), "refused")

    def test_stale_lease_is_stolen(self):
        self.assertEqual(orchestrator.lease_acquire(), "acquired")
        # age the lease beyond TTL
        lease = json.load(open(orchestrator.LOCK_PATH))
        lease["heartbeat_at"] = time.time() - 999
        json.dump(lease, open(orchestrator.LOCK_PATH, "w"))
        orchestrator.LEASE_OWNER = "test-owner-b"
        self.assertEqual(orchestrator.lease_acquire(), "stolen")

    def test_release_only_own_lease(self):
        self.assertEqual(orchestrator.lease_acquire(), "acquired")
        orchestrator.LEASE_OWNER = "test-owner-b"
        orchestrator.lease_release()  # not ours: no-op
        self.assertTrue(os.path.exists(orchestrator.LOCK_PATH))
        orchestrator.LEASE_OWNER = "test-owner-a"
        orchestrator.lease_release()
        self.assertFalse(os.path.exists(orchestrator.LOCK_PATH))


class CycleEventTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        orchestrator.DB_PATH = os.path.join(self.tmp.name, "momod.db")
        orchestrator.LOCK_PATH = os.path.join(self.tmp.name, "wip.lock")
        orchestrator.LEASE_OWNER = "cycle-owner"

    def tearDown(self):
        self.tmp.cleanup()

    def test_assign_command_shape(self):
        ticket = {"ticket_id": str(uuid.uuid4()), "title": "real task",
                  "correlationid": str(uuid.uuid4()), "event_id": str(uuid.uuid4())}
        cmd = orchestrator.assign_command(ticket)
        # canonical COMMAND envelope: kind=command + command_id + idempotency
        self.assertEqual(cmd["type"], "bloodbank.task.ticket.assigned")
        self.assertEqual(cmd["subject"], "bloodbank.cmd.task.ticket.assigned")
        self.assertEqual(cmd["kind"], "command")
        self.assertIn("command_id", cmd)
        self.assertIn("idempotency_key", cmd)
        self.assertNotEqual(cmd["type"], cmd["subject"])
        self.assertEqual(cmd["correlationid"], ticket["correlationid"])
        self.assertEqual(cmd["causationid"], ticket["event_id"])
        self.assertEqual(cmd["data"]["assignment_id"], cmd["id"])

    def test_cycle_events_canonical_and_correlated(self):
        stub = StubNats()
        corr = str(uuid.uuid4())
        ticket = {"ticket_id": str(uuid.uuid4()), "title": "t",
                  "correlationid": corr, "event_id": str(uuid.uuid4())}
        ev = orchestrator.momod_event("reviewed", ticket, {
            "commit_sha": "a" * 40, "tests_passed": True,
            "review_mode": "deterministic"})
        stub.publish_ack(ev["subject"], ev)
        subj, env = stub.published[0]
        self.assertEqual(env["type"], "bloodbank.task.cycle.reviewed")
        self.assertEqual(subj, "bloodbank.evt.task.cycle.reviewed")
        toks = env["type"].split(".")
        self.assertEqual(len(toks), 4)
        self.assertNotEqual(env["type"], env["subject"])
        self.assertEqual(env["correlationid"], corr)
        self.assertEqual(env["causationid"], ticket["event_id"])
        self.assertEqual(env["kind"], "event")
        self.assertEqual(env["data"]["commit_sha"], "a" * 40)

    def test_degraded_default_and_configured(self):
        # default: degraded, deterministic review
        self.assertTrue(orchestrator.HEALTH["degraded"])
        self.assertIn("GOD_LLM_BASE_URL", orchestrator.HEALTH["degraded_reason"])
        self.assertEqual(orchestrator.HEALTH["review_mode"], "deterministic")


if __name__ == "__main__":
    unittest.main()
