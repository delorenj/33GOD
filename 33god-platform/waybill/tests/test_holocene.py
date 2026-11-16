import json
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from waybill.collectors import holocene as ho
from waybill.model import Ctx, Fragment, Source, TurnWindow, iso, ms

SID = "956a26e9-3f7f-4226-9491-8590d87cc90e"
T0 = ms("2026-11-16T04:00:38.667Z")


def ctx():
    return Ctx(window=TurnWindow(cli="claude", surface="claude-code-headless", session_id=SID, t0=T0,
                                 t_end=ms("2026-11-16T04:00:41.678Z") + 15000))


def make_db(path, n=200):
    con = sqlite3.connect(path)
    con.execute("create table events(cursor integer primary key, event_id text unique, stream text, sequence integer,"
                " subject text, type text, source text, collected_at text, envelope text)")
    con.execute("create table checkpoints(name text, value text)")
    base = ms("2026-11-16T03:00:00.000Z")
    for i in range(n):   # one row a minute
        t = base + i * 60_000
        env = {"id": f"e{i}", "type": "bloodbank.agent.tool.requested", "time": iso(t), "data": {}}
        con.execute("insert into events values(?,?,?,?,?,?,?,?,?)",
                    (i * 3 + 5, f"e{i}", "BLOODBANK_EVENTS", 1000 + i, "bloodbank.evt.agent.tool.requested",
                     env["type"], "x", iso(t), json.dumps(env)))   # sparse rowids
    con.commit()
    return con


class SearchTests(unittest.TestCase):
    def test_first_cursor_lower_bound(self):
        with tempfile.TemporaryDirectory() as d:
            con = make_db(os.path.join(d, "e.sqlite3"))
            con.row_factory = sqlite3.Row
            base = ms("2026-11-16T03:00:00.000Z")
            self.assertEqual(ho.first_cursor_at_or_after(con, iso(base - 1000)), 5)
            self.assertEqual(ho.first_cursor_at_or_after(con, iso(base)), 5)
            self.assertEqual(ho.first_cursor_at_or_after(con, iso(base + 1)), 8)
            self.assertEqual(ho.first_cursor_at_or_after(con, iso(base + 60_000 * 37)), 37 * 3 + 5)
            self.assertIsNone(ho.first_cursor_at_or_after(con, iso(base + 60_000 * 999)))

    def test_read_rows_window_and_ids(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "e.sqlite3")
            con = make_db(p)
            hit = {"id": "hit", "type": "bloodbank.agent.session.started", "time": "2026-11-16T04:00:37.400Z",
                   "correlationid": SID, "data": {"session_id": SID}}
            con.execute("insert into events values(?,?,?,?,?,?,?,?,?)",
                        (10_000, "hit", "BLOODBANK_EVENTS", 5, "bloodbank.evt.agent.session.started", hit["type"], "x",
                         "2026-11-16T04:00:37.500Z", json.dumps(hit)))
            con.commit()
            con.close()
            rows, status = ho.read_rows(p, "2026-11-16T04:00:36.000Z", "2026-11-16T04:01:00.000Z", SID, ["e3"])
            ids = {r["event_id"] for r in rows}
            self.assertIn("hit", ids)
            self.assertIn("e3", ids)             # looked up by id
            self.assertNotIn("e100", ids)        # session id not mentioned
            self.assertIn("max_collected_at", status)


class MatchTests(unittest.TestCase):
    def test_matches(self):
        m = lambda env, pub=(): ho.matches(env, env.get("id", "x"), SID, SID, {"inv-1"}, set(pub))
        self.assertTrue(m({"correlationid": SID}))
        self.assertTrue(m({"correlationid": "inv-1"}))
        self.assertTrue(m({"data": {"session_id": SID}}))
        self.assertTrue(m({"id": "p"}, ["p"]))
        self.assertFalse(m({"correlationid": "other", "data": {"session_id": "other"}}))


class BuildTests(unittest.TestCase):
    def row(self, eid, et, t, coll, **env_extra):
        env = {"id": eid, "type": et, "time": t, "correlationid": SID, "data": {}}
        env.update(env_extra)
        return {"cursor": 1, "event_id": eid, "stream": "BLOODBANK_EVENTS", "sequence": 77, "subject": None, "type": et,
                "source": "x", "collected_at": coll, "envelope": json.dumps(env)}

    def frag(self):
        return Fragment(source=Source(id="holocene", kind="sqlite", locator="x"))

    def test_events_and_missing_gap(self):
        r = self.row("a", "bloodbank.agent.session.started", "2026-11-16T04:00:37.400Z", "2026-11-16T04:00:37.410Z")
        llm = self.row("l", "bloodbank.llm.request.completed", "2026-11-16T04:00:39.000Z", "2026-11-16T04:00:39.010Z")
        pubs = [{"event_id": "a", "event_type": "bloodbank.agent.session.started", "publish_status": "sent",
                 "t_start": ms("2026-11-16T04:00:37.3Z"), "t_end": ms("2026-11-16T04:00:37.4Z")},
                {"event_id": "gone", "event_type": "bloodbank.agent.tool.requested", "publish_status": "sent",
                 "t_start": ms("2026-11-16T04:00:38.0Z"), "t_end": ms("2026-11-16T04:00:38.1Z")},
                {"event_id": "att", "event_type": "deckard.v1.agent.attention", "publish_status": "sent",
                 "t_start": ms("2026-11-16T04:00:38.0Z"), "t_end": ms("2026-11-16T04:00:38.1Z")}]
        f = self.frag()
        status = {"max_collected_at": "2026-11-16T04:30:00.000Z", "checkpoints": []}
        ho.build(f, ctx(), [r, llm], status, pubs, [], now=ms("2026-11-16T04:31:00.000Z"))
        self.assertEqual([e.id for e in f.events], ["a"])
        ev = f.events[0]
        self.assertEqual((ev.stream, ev.seq), ("BLOODBANK_EVENTS", 77))
        self.assertEqual(ev.consumers[0].kind, "ephemeral")
        self.assertEqual(ev.consumers[0].name, "holocene")
        self.assertEqual(f.facts["holocene_llm_rows"][0]["id"], "l")
        gaps = [g for g in f.gaps if "published but not seen" in g.what]
        self.assertEqual(len(gaps), 1)
        self.assertIn("gone", gaps[0].what)           # attention events never reach the stream, so no gap for them

    def test_no_gap_inside_grace_or_when_behind(self):
        pubs = [{"event_id": "x", "event_type": "bloodbank.agent.tool.requested", "publish_status": "sent",
                 "t_start": ms("2026-11-16T04:00:38.0Z"), "t_end": ms("2026-11-16T04:00:38.1Z")}]
        f = self.frag()
        ho.build(f, ctx(), [], {"max_collected_at": "2026-11-16T04:30:00.000Z"}, pubs, [], now=ms("2026-11-16T04:00:40.0Z"))
        self.assertFalse(f.gaps)
        f = self.frag()
        ho.build(f, ctx(), [], {"max_collected_at": "2026-11-16T04:00:39.000Z"}, pubs, [], now=ms("2026-11-16T05:00:00.0Z"))
        self.assertEqual([g.severity for g in f.gaps], ["info"])

    def test_mirror_kept_outside_window(self):
        r = self.row("m", ho.HOOK_UPDATED, "2026-11-16T04:30:00.000Z", "2026-11-16T04:30:00.010Z", correlationid="inv-1")
        f = self.frag()
        ho.build(f, ctx(), [r], {}, [], ["inv-1"], now=ms("2026-11-16T05:00:00.0Z"))
        self.assertEqual([e.id for e in f.events], ["m"])

    def test_collect_fails_soft(self):
        old = ho.DB_PATH
        ho.DB_PATH = "/nonexistent/holocene.sqlite3"
        try:
            fr = ho.collect(ctx())
            self.assertEqual(fr.source.status, "error")
            self.assertTrue(fr.gaps)
        finally:
            ho.DB_PATH = old


if __name__ == "__main__":
    unittest.main()
