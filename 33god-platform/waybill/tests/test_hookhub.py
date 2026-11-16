import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from waybill.collectors import hookhub
from waybill.model import Ctx, Fragment, Source, TurnWindow, ms

SID = "11111111-2222-3333-4444-555555555555"


def window():
    return TurnWindow(cli="claude", surface="claude-code", session_id=SID, t0=ms("2026-11-16T04:00:38.000Z"),
                      t_end=ms("2026-11-16T04:00:50.000Z"))


SCHEMA = """
create table invocations(invocation_id text, cli text, native text, role text, event_type text, session_id text,
  identity_kind text, received_at text, updated_at text, status text, deduplicated int);
create table executions(invocation_id text, handler_id text, mode text, status text, reason text, selected_at text,
  started_at text, finished_at text, duration_ms real, exit_code int, event_id text, event_type text, publish_status text);
create table receipt_events(sequence integer primary key, invocation_id text, handler_id text, status text, reason text, at text);
"""


def make_db(path):
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    inv = lambda i, native, role, at, sid=SID, status="completed": con.execute(
        "insert into invocations values(?,?,?,?,?,?,?,?,?,?,0)",
        (i, "claude", native, role, None, sid, "session", at, at, status))
    inv("i-prompt", "UserPromptSubmit", "prompt_submit", "2026-11-16T04:00:38.100Z")
    inv("t-ours", "transition", None, "2026-11-16T04:00:38.300Z", sid=None)
    inv("t-other", "transition", None, "2026-11-16T04:00:45.000Z", sid=None)
    ex = lambda i, h, mode, st, reason, s, f, eid=None, et=None, ps=None: con.execute(
        "insert into executions values(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (i, h, mode, st, reason, s, s, f, None, None, eid, et, ps))
    ex("i-prompt", "hindsight-recall", "sync", "succeeded", "recall_completed",
       "2026-11-16T04:00:38.110Z", "2026-11-16T04:00:38.402Z")
    ex("i-prompt", "bloodbank-publisher", "async", "succeeded", None, "2026-11-16T04:00:38.200Z",
       "2026-11-16T04:00:38.400Z", "evt-1", "bloodbank.conversation.turn.started", "sent")
    ex("i-prompt", "codegraph-prompt", "sync", "skipped", "repository_not_indexed",
       "2026-11-16T04:00:38.120Z", "2026-11-16T04:00:38.130Z")
    ex("t-ours", "asm-transition", "async", "succeeded", None, "2026-11-16T04:00:38.310Z", "2026-11-16T04:00:38.320Z")
    for n, (i, h, st) in enumerate([("i-prompt", "hindsight-recall", "succeeded"), ("i-prompt", "bloodbank-publisher", "succeeded")], 1):
        con.execute("insert into receipt_events values(?,?,?,?,?,?)", (n, i, h, st, None, "2026-11-16T04:00:38.400Z"))
    con.commit()
    con.close()


class PureTests(unittest.TestCase):
    def test_phase_for(self):
        self.assertEqual(hookhub.phase_for("prompt_submit", "UserPromptSubmit"), "prompt_submit")
        self.assertEqual(hookhub.phase_for("turn_completed", "Stop"), "turn_end")
        self.assertEqual(hookhub.phase_for(None, "transition"), "async_after")
        self.assertEqual(hookhub.phase_for("attention", "PermissionRequest"), "pre_tool")
        self.assertEqual(hookhub.phase_for("attention", "Notification"), "turn_end")
        self.assertEqual(hookhub.phase_for("subagent_stop", "SubagentStop"), "tool")

    def test_status_for(self):
        self.assertEqual(hookhub.status_for("succeeded"), "ok")
        self.assertEqual(hookhub.status_for("timed_out"), "timeout")
        self.assertEqual(hookhub.status_for("started"), "pending")
        self.assertEqual(hookhub.status_for("weird"), "unknown")

    def test_short_type_and_subject(self):
        self.assertEqual(hookhub.short_type("bloodbank.agent.session.started"), "agent.session.started")
        self.assertEqual(hookhub.short_type("deckard.v1.agent.attention"), "agent.attention")
        self.assertEqual(hookhub.subject_for("bloodbank.agent.tool.requested"), "bloodbank.evt.agent.tool.requested")
        self.assertEqual(hookhub.subject_for("deckard.v1.agent.attention"), "deckard.evt.attention")
        self.assertIsNone(hookhub.subject_for(None))

    def test_attribute_transitions(self):
        pubs = [{"invocation_id": "a", "started_at": "2026-11-16T04:00:10.000Z", "finished_at": "2026-11-16T04:00:10.200Z"},
                {"invocation_id": "b", "started_at": "2026-11-16T04:00:10.100Z", "finished_at": "2026-11-16T04:00:10.400Z"}]
        trans = [{"invocation_id": "t1", "received_at": "2026-11-16T04:00:10.150Z"},
                 {"invocation_id": "t2", "received_at": "2026-11-16T04:00:10.390Z"},
                 {"invocation_id": "t3", "received_at": "2026-11-16T04:00:30.000Z"}]
        mapping, un = hookhub.attribute_transitions(trans, pubs)
        self.assertEqual(mapping["t1"]["invocation_id"], "b")     # nearest preceding start wins
        self.assertEqual(mapping["t2"]["invocation_id"], "b")
        self.assertEqual([t["invocation_id"] for t in un], ["t3"])

    def test_handler_summary(self):
        s = hookhub.handler_summary({"handler_id": "h", "status": "succeeded", "mode": "sync", "duration_ms": 292,
                                     "reason": "recall_completed"})
        self.assertEqual(s, "h ran sync for 292 ms (recall_completed)")
        self.assertIn("skipped: repository_not_indexed",
                      hookhub.handler_summary({"handler_id": "h", "status": "skipped", "reason": "repository_not_indexed"}))
        self.assertIn("handler_exit_nonzero", hookhub.handler_summary(
            {"handler_id": "h", "status": "failed", "reason": "handler_exit_nonzero", "duration_ms": 103, "exit_code": 0}))
        self.assertIn("timed out after 15.0 s", hookhub.handler_summary({"handler_id": "h", "status": "timed_out", "duration_ms": 15000}))
        self.assertIn("never finished", hookhub.handler_summary({"handler_id": "h", "status": "started"}))


class DbTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "receipts.sqlite3")
        make_db(self.path)
        hookhub._CACHE.clear()
        self.ctx = Ctx(window=window())

    def tearDown(self):
        self.dir.cleanup()
        hookhub._CACHE.clear()

    def test_load_attributes_only_contained_transitions(self):
        data = hookhub.load(self.ctx, self.path)
        ids = [i["invocation_id"] for i in data["invocations"]]
        self.assertIn("i-prompt", ids)
        self.assertIn("t-ours", ids)
        self.assertNotIn("t-other", ids)
        self.assertEqual([t["invocation_id"] for t in data["unattributed_transitions"]], ["t-other"])

    def test_read_only_connection(self):
        con = hookhub._connect(self.path)
        with self.assertRaises(sqlite3.OperationalError):
            con.execute("delete from invocations")
        con.close()

    def test_build_emits_spans_links_and_findings(self):
        data = hookhub.load(self.ctx, self.path)
        frag = Fragment(source=Source(id="hookhub", kind="sqlite", locator="x"))
        hookhub.build(frag, self.ctx, data, now=ms("2026-11-16T05:00:00.000Z"))
        kinds = {}
        for s in frag.spans:
            kinds[s.kind] = kinds.get(s.kind, 0) + 1
        self.assertEqual(kinds.get("hook"), 2)
        self.assertEqual(kinds.get("handler"), 4)
        self.assertEqual(kinds.get("publish"), 1)
        self.assertTrue(any(l.kind == "publishes" for l in frag.links))
        self.assertTrue(any(g.what.startswith("bb-hook") or "bb-hook" in g.component for g in frag.gaps))
        hook = next(s for s in frag.spans if s.kind == "hook" and s.refs.get("invocation_id") == "i-prompt")
        self.assertIn("held the CLI", hook.summary)

    def test_public_helpers(self):
        old = hookhub.DB_PATH
        hookhub.DB_PATH = self.path
        try:
            self.assertEqual(sorted(hookhub.invocation_ids(self.ctx)), ["i-prompt", "t-ours"])
            hookhub._CACHE.clear()
            pubs = hookhub.published_events(self.ctx)
            self.assertEqual(len(pubs), 1)
            self.assertEqual(pubs[0]["event_id"], "evt-1")
            self.assertEqual(pubs[0]["subject"], "bloodbank.evt.conversation.turn.started")
            near = hookhub.executions_near("hindsight-recall", ms("2026-11-16T04:00:38.402Z"), 500, self.path)
            self.assertEqual(len(near), 1)
        finally:
            hookhub.DB_PATH = old

    def test_collect_fails_soft(self):
        old = hookhub.DB_PATH
        hookhub.DB_PATH = os.path.join(self.dir.name, "missing.sqlite3")
        try:
            frag = hookhub.collect(self.ctx)
            self.assertEqual(frag.source.status, "error")
            self.assertTrue(frag.gaps)
        finally:
            hookhub.DB_PATH = old


if __name__ == "__main__":
    unittest.main()
