import base64
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from waybill.collectors import candystore as cs
from waybill.model import Ctx, Fragment, Ids, Source, TurnWindow, ms

SID = "956a26e9-3f7f-4226-9491-8590d87cc90e"
T0 = ms("2026-11-16T04:00:38.667Z")


def ctx(profile="full"):
    return Ctx(window=TurnWindow(cli="claude", surface="claude-code-headless", session_id=SID, t0=T0,
                                 t_end=ms("2026-11-16T04:00:41.678Z") + 15000), profile=profile)


def frag():
    return Fragment(source=Source(id="candystore", kind="x", locator="x"))


class PureTests(unittest.TestCase):
    def test_correlation_id(self):
        self.assertEqual(cs.correlation_id("claude", SID), SID)
        a = cs.correlation_id("codex", "not-a-uuid")
        self.assertEqual(a, cs.correlation_id("codex", "not-a-uuid"))
        self.assertNotEqual(a, cs.correlation_id("claude", "not-a-uuid"))
        self.assertTrue(cs.is_uuid(a))

    def test_normalize_type_dapr(self):
        et, subj = cs.normalize_type({"type": "com.dapr.event.sent", "topic": "bloodbank.evt.report.session.completed"})
        self.assertEqual(et, "bloodbank.report.session.completed")
        self.assertEqual(subj, "bloodbank.evt.report.session.completed")
        et, subj = cs.normalize_type({"type": "bloodbank.agent.session.started"})
        self.assertEqual(subj, "bloodbank.evt.agent.session.started")

    def test_phase_for_type(self):
        self.assertEqual(cs.phase_for_type("bloodbank.conversation.turn.started"), "prompt_submit")
        self.assertEqual(cs.phase_for_type("bloodbank.conversation.turn.annotated"), "turn_end")
        self.assertEqual(cs.phase_for_type("bloodbank.agent.hook.updated"), "async_after")

    def test_public_clip_and_env_drop(self):
        env = {"id": "e", "type": "t", "data": {"prompt_text": "x" * 1000, "env": {"SECRET": "v"}, "cwd": os.path.expanduser("~/code")}}
        pub, n = cs.shape_envelope(env, "public")
        self.assertEqual(n, 1)
        self.assertEqual(len(pub["data"]["prompt_text"]), cs.PUBLIC_CLIP + 1)
        self.assertEqual(pub["data"]["env"], "«dropped»")
        self.assertEqual(pub["data"]["cwd"], "~/code")
        full, n2 = cs.shape_envelope(env, "full")
        self.assertEqual(n2, 0)
        self.assertEqual(full["data"]["env"], {"SECRET": "v"})
        self.assertEqual(list(full), sorted(full))

    def test_build_sql_validates_ids(self):
        good = "6a5d1c5e-0000-4000-8000-000000000001"
        sql = cs.build_sql([good, "x'; drop table events; --"], ["bad id", good], SID, "2026-11-16T04:00:36.667Z",
                           "2026-11-16T04:00:56.678Z")
        self.assertNotIn("drop table", sql)
        self.assertNotIn("bad id", sql)
        self.assertIn(good, sql)
        self.assertIn("convert_to('" + SID + "'", sql)
        evil = cs.build_sql([], [], "x'); delete from events; --", "a", "b")
        self.assertNotIn("delete from", evil)
        self.assertIn("array[]::uuid[]", evil)


class BuildTests(unittest.TestCase):
    def test_build_archive_mirror_dead_letter(self):
        eid = "00000000-0000-4000-8000-00000000000a"
        mid = "00000000-0000-4000-8000-00000000000b"
        did = "00000000-0000-4000-8000-00000000000c"
        env = {"id": eid, "type": "bloodbank.agent.session.started", "time": "2026-11-16T04:00:37.400Z",
               "correlationid": SID, "producer": "claude-code", "data": {"session_id": SID}}
        mirror = {"id": mid, "type": cs.HOOK_UPDATED, "time": "2026-11-16T04:00:38.000Z", "received_at": "2026-11-16T04:00:38.020Z",
                  "correlationid": "inv-1", "causationid": None, "producer": None,
                  "raw": {"id": mid, "type": cs.HOOK_UPDATED, "time": "2026-11-16T04:00:38.000Z", "correlationid": "inv-1"}}
        dead_env = {"id": did, "type": "com.dapr.event.sent", "topic": "bloodbank.evt.report.session.completed",
                    "source": "enricher", "time": "2026-11-16T04:00:41.000Z", "data": {"session_id": SID, "summary": "S"}}
        pg = {"archived": [{"id": eid, "received_at": "2026-11-16T04:00:37.430Z"}], "mirrors": [mirror], "caused": [],
              "dead": [{"id": 1, "event_id": did, "topic": "t", "reason": "malformed", "error": "missing id",
                        "received_at": "2026-11-16T04:00:41.100Z",
                        "raw_b64": base64.b64encode(json.dumps(dead_env).encode()).decode()}]}
        f = frag()
        cs.build(f, ctx(), [{"id": eid, "_env": env}], pg, {eid}, ["inv-1"])
        by = {e.id: e for e in f.events}
        self.assertEqual(set(by), {eid, mid, did})
        self.assertEqual(by[eid].consumers[0].name, "candystore-events")
        self.assertEqual(by[eid].consumers[0].evidence, "observed")
        self.assertEqual(by[eid].publisher_span, Ids.publish(eid))
        self.assertEqual(by[did].consumers[0].outcome, "dropped")
        consume = {s.id: s for s in f.spans}[Ids.consume("candystore-events", eid)]
        self.assertAlmostEqual(consume.attrs["lag_ms"], 30, delta=1)
        self.assertTrue(any(l.kind == "mirrors" and l.to == Ids.evt(mid) for l in f.links))
        self.assertEqual([x.title for x in f.findings], ["enricher session report dead-lettered by Candystore"])
        self.assertEqual(f.findings[0].severity, "broken")

    def test_caused_skips_agent_producers(self):
        eid = "00000000-0000-4000-8000-00000000000a"
        ann = "00000000-0000-4000-8000-0000000000ff"
        nxt = "00000000-0000-4000-8000-0000000000fe"
        env = {"id": eid, "type": "bloodbank.conversation.turn.completed", "time": "2026-11-16T04:00:41.000Z", "producer": "claude-code"}
        mk = lambda i, prod, et: {"id": i, "type": et, "time": "2026-11-16T04:00:42.000Z", "received_at": "2026-11-16T04:00:42.010Z",
                                  "causationid": eid, "producer": prod,
                                  "raw": {"id": i, "type": et, "time": "2026-11-16T04:00:42.000Z", "causationid": eid, "producer": prod}}
        pg = {"archived": [], "mirrors": [], "dead": [],
              "caused": [mk(ann, "turn-enricher", "bloodbank.conversation.turn.annotated"), mk(nxt, "claude-code", "bloodbank.conversation.turn.started")]}
        f = frag()
        cs.build(f, ctx(), [{"id": eid, "_env": env}], pg, set(), [])
        ids = {e.id for e in f.events}
        self.assertIn(ann, ids)
        self.assertNotIn(nxt, ids)
        self.assertTrue(any(l.kind == "causes" and l.from_ == Ids.evt(eid) and l.to == Ids.evt(ann) for l in f.links))

    def test_collect_fails_soft(self):
        old = cs.BASE_URL
        cs.BASE_URL = "http://127.0.0.1:9"
        try:
            c = ctx()
            c.timeout_s = 1.0
            fr = cs.collect(c)
            self.assertEqual(fr.source.status, "error")
            self.assertTrue(fr.gaps)
        finally:
            cs.BASE_URL = old


if __name__ == "__main__":
    unittest.main()
