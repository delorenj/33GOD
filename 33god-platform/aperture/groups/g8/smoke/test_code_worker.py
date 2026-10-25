"""Unit tests for the G8 code-worker: REAL git lane + envelope shapes.
Uses a temp workbench; git must exist on the host (it does — the bundle's
own branch). No bus, no HTTP: publish via stub."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code-worker"))
import worker  # noqa: E402


class StubNats:
    def __init__(self):
        self.published = []

    def publish_ack(self, subject, payload, timeout=5.0):
        self.published.append((subject, payload))
        return {"stream": "BLOODBANK_EVENTS", "seq": len(self.published)}

    def close(self):
        pass


def assignment(ticket_id=None, corr=None):
    return {"ticket_id": ticket_id or str(uuid.uuid4()),
            "title": "add one acceptance doc page",
            "correlationid": corr or str(uuid.uuid4()),
            "assignment_id": str(uuid.uuid4())}


class GitLaneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        worker.WORKBENCH = os.path.join(self.tmp.name, "workbench")
        worker.DB_PATH = os.path.join(self.tmp.name, "code-worker.db")
        worker.GIT_NAME = "g8-test-worker"
        worker.GIT_EMAIL = "test@invalid"
        worker.HEALTH["git_version"] = None

    def tearDown(self):
        self.tmp.cleanup()

    def test_implement_lands_a_real_commit_with_passing_tests(self):
        a = assignment()
        result = worker.implement(a)
        self.assertTrue(result["tests_passed"], result["tests_output"])
        self.assertRegex(result["commit_sha"], r"^[0-9a-f]{40}$")
        self.assertEqual(len(result["files"]), 2)
        # the commit REALLY exists in the repo with our message
        log = subprocess.run(["git", "log", "--format=%H%n%s%n%b", "-1"],
                             cwd=worker.WORKBENCH, capture_output=True, text=True)
        self.assertEqual(log.returncode, 0)
        head = log.stdout.splitlines()
        self.assertEqual(head[0], result["commit_sha"])
        self.assertIn(a["ticket_id"], log.stdout)
        self.assertIn(a["correlationid"], log.stdout)
        # the files are tracked
        ls = subprocess.run(["git", "ls-files"], cwd=worker.WORKBENCH,
                            capture_output=True, text=True)
        for f in result["files"]:
            self.assertIn(f, ls.stdout)

    def test_second_assignment_gets_its_own_commit(self):
        r1 = worker.implement(assignment())
        r2 = worker.implement(assignment())
        self.assertNotEqual(r1["commit_sha"], r2["commit_sha"])
        count = subprocess.run(["git", "rev-list", "--count", "HEAD"],
                               cwd=worker.WORKBENCH, capture_output=True, text=True)
        self.assertEqual(count.stdout.strip(), "2")

    def test_handle_assignment_publishes_landed_and_reply(self):
        a = assignment()
        stub = StubNats()
        worker.handle_assignment(stub, {
            "type": "bloodbank.task.ticket.assigned",
            "correlationid": a["correlationid"],
            "id": a["assignment_id"],
            "data": a})
        kinds = [(subj, env["type"]) for subj, env in stub.published]
        self.assertEqual(kinds, [
            ("bloodbank.evt.code.commit.landed", "bloodbank.code.commit.landed"),
            ("bloodbank.rpy.task.ticket.completed", "bloodbank.task.ticket.completed")])
        landed, reply = stub.published[0][1], stub.published[1][1]
        # THE CHAIN: same correlationid, causationid = assignment id
        for env in (landed, reply):
            self.assertEqual(env["correlationid"], a["correlationid"])
            self.assertEqual(env["causationid"], a["assignment_id"])
        self.assertIn("commit_sha", landed["data"])
        self.assertTrue(landed["data"]["tests_passed"])
        self.assertTrue(reply["data"]["evidence_complete"])
        # reply is kind=reply on the COMMANDS subject space (rpy marker)
        self.assertEqual(reply["kind"], "reply")
        self.assertTrue(reply["subject"].startswith("bloodbank.rpy."))

    def test_envelope_canonical_shapes(self):
        a = assignment()
        stub = StubNats()
        worker.handle_assignment(stub, {
            "type": "bloodbank.task.ticket.assigned", "correlationid": a["correlationid"],
            "id": a["assignment_id"], "data": a})
        for _, env in stub.published:
            toks = env["type"].split(".")
            self.assertEqual(len(toks), 4)
            self.assertEqual(toks[0], "bloodbank")
            self.assertNotEqual(env["type"], env["subject"])
            self.assertEqual(env["producer"], "aperture-g8-code-worker")
            self.assertIn("ordering_key", env)

    def test_malformed_assignment_is_dropped_not_crashed(self):
        stub = StubNats()
        worker.handle_assignment(stub, {"type": "x", "data": {"ticket_id": "only-one"}})
        self.assertEqual(stub.published, [])  # no events for malformed input


if __name__ == "__main__":
    unittest.main()
