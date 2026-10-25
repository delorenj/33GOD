"""Unit tests for the G8 dashboard event projection (no bus, no HTTP)."""
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))
import server  # noqa: E402


def env_(etype, corr, data, eid=None):
    return {"id": eid or str(uuid.uuid4()), "type": etype,
            "subject": "bloodbank.evt." + etype.split(".", 1)[1],
            "producer": "test", "time": "2026-10-24T12:00:00.000Z",
            "correlationid": corr, "causationid": corr, "data": data}


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        server.DB_PATH = os.path.join(self.tmp.name, "dash.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_lifecycle_projection_reaches_done_with_evidence(self):
        tid = str(uuid.uuid4())
        corr = str(uuid.uuid4())
        server.project(env_("bloodbank.task.ticket.created", corr,
                            {"ticket_id": tid, "title": "one page", "state": "backlog"}))
        server.project(env_("bloodbank.task.ticket.started", corr,
                            {"ticket_id": tid, "title": "one page", "state": "in_progress"}))
        server.project(env_("bloodbank.task.ticket.completed", corr,
                            {"ticket_id": tid, "title": "one page", "state": "done",
                             "commit_sha": "a" * 40, "tests_passed": True}))
        with server.db() as conn:
            row = conn.execute(
                "SELECT title, state, commit_sha, tests_passed, correlationid"
                " FROM work_items WHERE ticket_id=?", (tid,)).fetchone()
        self.assertEqual(row[0], "one page")
        self.assertEqual(row[1], "done")
        self.assertEqual(row[2], "a" * 40)
        self.assertTrue(row[3])
        self.assertEqual(row[4], corr)

    def test_chain_events_kept_per_correlationid(self):
        tid = str(uuid.uuid4())
        corr = str(uuid.uuid4())
        other = str(uuid.uuid4())
        for etype, state in (("bloodbank.task.ticket.created", "backlog"),
                             ("bloodbank.task.ticket.started", "in_progress")):
            server.project(env_(etype, corr, {"ticket_id": tid, "state": state}))
        server.project(env_("bloodbank.task.cycle.reviewed", corr, {"x": 1}))
        server.project(env_("bloodbank.code.commit.landed", corr, {"x": 2}))
        server.project(env_("bloodbank.task.ticket.created", other,
                            {"ticket_id": str(uuid.uuid4), "state": "backlog"}))
        with server.db() as conn:
            rows = conn.execute(
                "SELECT type FROM chain_events WHERE correlationid=? ORDER BY time",
                (corr,)).fetchall()
        self.assertEqual([r[0] for r in rows], [
            "bloodbank.task.ticket.created", "bloodbank.task.ticket.started",
            "bloodbank.task.cycle.reviewed", "bloodbank.code.commit.landed"])

    def test_out_of_order_events_do_not_downgrade_state(self):
        tid = str(uuid.uuid4())
        corr = str(uuid.uuid4())
        server.project(env_("bloodbank.task.ticket.completed", corr,
                            {"ticket_id": tid, "state": "done", "commit_sha": "b" * 40,
                             "tests_passed": True}))
        # a late-arriving older event must not flip done -> backlog
        server.project(env_("bloodbank.task.ticket.created", corr,
                            {"ticket_id": tid, "state": "backlog"}))
        with server.db() as conn:
            row = conn.execute("SELECT state FROM work_items WHERE ticket_id=?",
                               (tid,)).fetchone()
        self.assertEqual(row[0], "done")

    def test_replay_is_idempotent(self):
        tid = str(uuid.uuid4())
        corr = str(uuid.uuid4())
        e = env_("bloodbank.task.ticket.created", corr,
                 {"ticket_id": tid, "state": "backlog"})
        server.project(e)
        server.project(e)  # replay
        with server.db() as conn:
            items = conn.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
            events = conn.execute("SELECT COUNT(*) FROM chain_events").fetchone()[0]
        self.assertEqual(items, 1)
        self.assertEqual(events, 1)


if __name__ == "__main__":
    unittest.main()
