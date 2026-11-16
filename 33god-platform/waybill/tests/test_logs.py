import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from waybill.collectors import logs
from waybill.model import Ctx, Fragment, Ids, Source, TurnWindow, ms

SID = "956a26e9-3f7f-4226-9491-8590d87cc90e"
T0 = ms("2026-11-16T04:00:38.667Z")


def ctx():
    return Ctx(window=TurnWindow(cli="claude", surface="claude-code-headless", session_id=SID, t0=T0,
                                 t_end=ms("2026-11-16T04:00:41.678Z") + 15000))


def frag():
    return Fragment(source=Source(id="logs", kind="x", locator="x"))


E1 = "00000000-0000-4000-8000-000000000001"
E2 = "00000000-0000-4000-8000-000000000002"


class ParseTests(unittest.TestCase):
    def test_parse_docker_lines(self):
        txt = ("2026-11-16T04:00:38.728123456Z 2026-11-16 04:00:38,728 [ntfy-router] INFO routed: bloodbank.agent.session.started\n"
               "no timestamp here\n"
               "2026-11-16T04:00:39Z second\n")
        got = logs.parse_docker_lines(txt)
        self.assertEqual(len(got), 2)
        self.assertAlmostEqual(got[0][0], ms("2026-11-16T04:00:38.728Z"), delta=1)
        self.assertTrue(got[0][1].startswith("2026-11-16 04:00:38,728"))

    def test_parse_ntfy(self):
        lines = [(1.0, "2026 [ntfy-router] INFO routed: bloodbank.agent.session.started"),
                 (2.0, "2026 [ntfy-router] INFO rate-limited: bloodbank.conversation.turn.started"),
                 (3.0, "2026 [ntfy-router] INFO digested: bloodbank.agent.tool.requested"),
                 (4.0, "2026 [ntfy-router] INFO routed: bloodbank digest: 5 events in 5m"),
                 (5.0, "2026 [ntfy-router] INFO duplicate: bloodbank.agent.session.ended"),
                 (6.0, "unrelated line")]
        got = logs.parse_ntfy(lines)
        self.assertEqual([(g["kind"], g["type"]) for g in got],
                         [("routed", "bloodbank.agent.session.started"), ("rate-limited", "bloodbank.conversation.turn.started"),
                          ("digested", "bloodbank.agent.tool.requested"), ("duplicate", "bloodbank.agent.session.ended")])

    def test_parse_annotation(self):
        a = logs.parse_annotation(f"2026 [turn-enricher] INFO annotated: {E1} signal=0.920 action='ship it' artifacts=4 blocker=None")
        self.assertEqual(a, {"id": E1, "outcome": "annotated", "signal": 0.92, "action": "ship it", "artifacts": 4, "blocker": None})
        b = logs.parse_annotation(f"2026 [turn-enricher] INFO annotated: {E1} signal=0.5 action='x' artifacts=0 blocker='waiting'")
        self.assertEqual(b["blocker"], "waiting")
        n = logs.parse_annotation(f"2026 [turn-enricher] INFO noise: {E2} (signal=0.030)")
        self.assertEqual((n["id"], n["outcome"], n["signal"]), (E2, "noise", 0.03))
        self.assertIsNone(logs.parse_annotation("stats annotated=548 noise=52"))

    def test_parse_hub_log_window_and_timezone(self):
        txt = ("2026-11-15T23:00:01-0500 [5728] receipt journal update failed: OperationalError database is locked\n"
               "2026-11-15T23:00:02-0500 [5728] all quiet\n"
               "2026-11-15T22:00:00-0500 [5728] request failed: JSONDecodeError\n")
        lo, hi = ms("2026-11-16T04:00:00Z"), ms("2026-11-16T04:00:10Z")
        got = logs.parse_hub_log(txt, lo, hi)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["t"], ms("2026-11-16T04:00:01Z"))
        self.assertIn("OperationalError", got[0]["msg"])

    def test_hub_template_collapses_ids_and_numbers(self):
        a = logs.hub_template(f"handler x: TIMEOUT after 5.0s, killed {E1}")
        b = logs.hub_template("handler x: TIMEOUT after 12s, killed 11111111-2222-3333-4444-555555555555")
        self.assertEqual(a, b)


class MatchTests(unittest.TestCase):
    def test_match_by_time_greedy_and_ambiguity(self):
        lines = [{"t": 1000.0, "kind": "digested", "type": "T"}, {"t": 1100.0, "kind": "digested", "type": "T"},
                 {"t": 1050.0, "kind": "routed", "type": "OTHER"}]
        exp = [{"event_id": "a", "type": "T", "t_lo": 950.0, "t_hi": 1200.0},
               {"event_id": "b", "type": "T", "t_lo": 1000.0, "t_hi": 1200.0},
               {"event_id": "c", "type": "T", "t_lo": 2000.0, "t_hi": 3000.0}]
        got = logs.match_by_time(lines, exp)
        self.assertEqual([(m["expected"]["event_id"], m["line"]["t"], m["candidates"]) for m in got],
                         [("a", 1000.0, 2), ("b", 1100.0, 2)])   # each line is used once; c has no line

    def test_expected_skips_attention_and_unsent(self):
        pubs = [{"event_id": "a", "event_type": "bloodbank.agent.session.started", "publish_status": "sent", "t_start": 10.0, "t_end": 20.0},
                {"event_id": "b", "event_type": "deckard.v1.agent.attention", "publish_status": "sent", "t_start": 10.0, "t_end": 20.0},
                {"event_id": "c", "event_type": "bloodbank.agent.tool.requested", "publish_status": "failed", "t_start": 10.0, "t_end": 20.0}]
        got = logs._expected(pubs, [])
        self.assertEqual([e["event_id"] for e in got], ["a"])
        self.assertEqual(got[0]["t_hi"], 20.0 + logs.MATCH_AFTER_MS)


class BuildTests(unittest.TestCase):
    def test_build_ntfy_spans_and_join_hints(self):
        lines = [{"t": 1100.0, "kind": "rate-limited", "type": "bloodbank.agent.session.started"},
                 {"t": 1200.0, "kind": "digested", "type": "bloodbank.agent.tool.requested"},
                 {"t": 1210.0, "kind": "digested", "type": "bloodbank.agent.tool.requested"}]
        exp = [{"event_id": E1, "type": "bloodbank.agent.session.started", "t_lo": 1000.0, "t_hi": 4000.0, "t_pub": 1050.0},
               {"event_id": E2, "type": "bloodbank.agent.tool.requested", "t_lo": 1000.0, "t_hi": 4000.0, "t_pub": 1150.0}]
        f = frag()
        self.assertEqual(logs.build_ntfy(f, lines, exp), 2)
        by = {s.id: s for s in f.spans}
        s1 = by[Ids.notify("ntfy-router", E1)]
        self.assertEqual((s1.status, s1.reason, s1.component), ("dropped", "rate_limited", "ntfy-router"))
        self.assertEqual(s1.refs, {"event_id": E1})
        self.assertEqual(s1.attrs["_join"]["event_id"], E1)
        self.assertEqual(s1.attrs["_join"]["consumer_kind"], "core")
        s2 = by[Ids.notify("ntfy-router", E2)]
        self.assertEqual((s2.status, s2.reason), ("ok", "digested"))
        self.assertTrue(s2.attrs["ambiguous"])                 # two digested lines fit: do not claim a ref
        self.assertEqual(s2.refs, {})
        self.assertNotIn("event_id", s2.attrs["_join"])
        self.assertEqual(s2.attrs["guess_event_id"], E2)

    def test_build_enricher_embed_error_and_rollup(self):
        ended = "00000000-0000-4000-8000-0000000000ee"
        pubs = {E1: {"event_id": E1, "event_type": "bloodbank.agent.tool.completed", "t_end": 1000.0},
                E2: {"event_id": E2, "event_type": "bloodbank.agent.tool.requested", "t_end": 1000.0},
                ended: {"event_id": ended, "event_type": "bloodbank.agent.session.ended", "t_end": 1500.0}}
        lines = [(1040.0, f"INFO enricher Successfully embedded tool event {E1}"),
                 (1050.0, f'ERROR enricher DB Error on {E2}: insert or update on table "event_embeddings" violates foreign key'),
                 (1060.0, "INFO enricher Successfully embedded tool event 99999999-0000-4000-8000-000000000000"),
                 (1600.0, f"INFO enricher Session {SID} ended. Rolling up events...")]
        f = frag()
        n, fk = logs.build_enricher(f, ctx(), lines, pubs)
        self.assertEqual(n, 3)
        by = {s.id: s for s in f.spans}
        ok = by[Ids.consume("enricher-events", E1)]
        self.assertEqual((ok.status, ok.component, ok.refs), ("ok", "enricher", {"event_id": E1}))
        self.assertEqual(ok.t1 - ok.t0, 40.0)
        bad = by[Ids.consume("enricher-events", E2)]
        self.assertEqual((bad.status, bad.reason), ("failed", "db_error"))
        self.assertEqual(fk, [bad.id])
        self.assertIn(Ids.consume("enricher-events", ended), by)

    def test_build_turn_enricher(self):
        pubs = {E1: {"event_id": E1, "event_type": "bloodbank.conversation.turn.completed", "t_end": 1000.0},
                E2: {"event_id": E2, "event_type": "bloodbank.conversation.turn.completed", "t_end": 2000.0}}
        lines = [(1100.0, f"2026 [turn-enricher] INFO annotated: {E1} signal=0.920 action='go' artifacts=2 blocker=None"),
                 (2100.0, f"2026 [turn-enricher] INFO noise: {E2} (signal=0.030)"),
                 (2200.0, "2026 [turn-enricher] INFO noise: 99999999-0000-4000-8000-000000000000 (signal=0.1)")]
        f = frag()
        n, annotated = logs.build_turn_enricher(f, lines, pubs)
        self.assertEqual(n, 2)
        self.assertEqual(annotated, [{"t": 1100.0, "source_id": E1, "t_pub": 1000.0}])
        by = {s.id: s for s in f.spans}
        self.assertEqual(by[Ids.consume("turn-enricher", E1)].attrs["_join"]["outcome"], "enriched")
        noise = by[Ids.consume("turn-enricher", E2)]
        self.assertEqual((noise.status, noise.reason), ("skipped", "noise"))
        self.assertEqual(noise.attrs["_join"]["event_type"], "bloodbank.conversation.turn.completed")

    def test_build_daprd_drop_becomes_broken_finding(self):
        env = {"id": E1, "source": "enricher", "topic": "bloodbank.evt.report.session.completed",
               "time": "2026-11-16T04:00:41.000Z", "data": {"session_id": SID}}
        fake = {E1: {"type": "x", "subject": None, "envelope": env}}
        lines = [(ms("2026-11-16T04:00:41.999Z"), f'level=warning msg="DROP status returned from app while processing pub/sub event {E1}"'),
                 (ms("2026-11-16T04:00:42.000Z"), 'level=warning msg="DROP status returned from app while processing pub/sub event '
                                                    '99999999-0000-4000-8000-000000000000"')]
        f = frag()
        with mock.patch("waybill.collectors.holocene.lookup", return_value=fake):
            n = logs.build_daprd(f, ctx(), lines, {})
        self.assertEqual(n, 1)                      # the second id is not this session's
        self.assertEqual([(x.severity, x.title) for x in f.findings],
                         [("broken", "enricher session report dead-lettered by Candystore")])
        sp = f.spans[0]
        self.assertEqual((sp.id, sp.status), (Ids.consume("candystore-events", E1), "dropped"))

    def test_build_hub_aggregates_and_skips_foreign_timeouts(self):
        rows = [{"t": 1000.0, "pid": "1", "msg": "receipt journal update failed: OperationalError locked", "template": "receipt journal update failed: OperationalError locked"},
                {"t": 1500.0, "pid": "1", "msg": "receipt journal update failed: OperationalError locked", "template": "receipt journal update failed: OperationalError locked"},
                {"t": 2000.0, "pid": "1", "msg": "handler other: TIMEOUT after 5.0s, killed", "template": "handler other: TIMEOUT after <n>s, killed"}]
        f = frag()
        foreign = [{"status": "timed_out", "session_id": "someone-else"}]
        with mock.patch.object(logs.hookhub, "executions_near", return_value=foreign):
            n = logs.build_hub(f, ctx(), rows, None)
        self.assertEqual(n, 2)
        self.assertEqual(len(f.findings), 1)
        self.assertEqual(f.findings[0].severity, "warn")
        self.assertIn("x2", f.findings[0].title)
        self.assertEqual(f.facts["hub_log_foreign_timeouts"], 1)

    def test_docker_lines_falls_back_to_tail_when_since_is_empty(self):
        calls = []

        def fake_run(argv, timeout):
            calls.append(argv)
            out = ""
            if "--tail" in argv:
                out = ("2026-11-16T04:00:00.000Z old\n2026-11-16T04:00:40.000Z in\n2026-11-16T05:00:00.000Z late\n")
            return mock.Mock(returncode=0, stdout=out, stderr="")

        with mock.patch.object(logs, "_run", side_effect=fake_run):
            lines, mode = logs.docker_lines("c", ms("2026-11-16T04:00:30Z"), ms("2026-11-16T04:00:50Z"), 5)
        self.assertEqual(mode, "tail:2000")
        self.assertEqual([m for _, m in lines], ["in"])
        self.assertIn("--since", calls[0])
        self.assertIn("--tail", calls[1])

    def test_collect_fails_soft_without_docker(self):
        with mock.patch.object(logs, "_run", side_effect=FileNotFoundError("docker")), \
             mock.patch.object(logs, "HUB_LOG", "/nonexistent/hub.log"), \
             mock.patch.object(logs.hookhub, "published_events", return_value=[]), \
             mock.patch.object(logs.hookhub, "load", side_effect=RuntimeError("no db")):
            fr = logs.collect(ctx())
        self.assertIn(fr.source.status, ("error", "empty"))
        self.assertTrue(fr.gaps)
        self.assertEqual(fr.spans, [])


if __name__ == "__main__":
    unittest.main()
