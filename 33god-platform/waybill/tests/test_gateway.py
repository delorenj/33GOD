"""Tests for waybill.collectors.gateway (psql output and traces are faked; nothing touches the live system)."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from waybill.collectors import gateway as G
from waybill.model import Ctx, TurnWindow, iso, ms, to_jsonable

SID = "956a26e9-3f7f-4226-9491-8590d87cc90e"
T0 = ms("2026-11-16T04:00:38.646Z")
T_END = ms("2026-11-16T04:00:41.014Z") + 15000
RID1 = "202611160400397108849668268d9d60KCZoh0q"      # received 04:00:39.710Z
RID2 = "20261116040040100000000000000000bgROUND"      # received 04:00:40.100Z (a background call)


def window():
    return TurnWindow(cli="claude", surface="claude-code", session_id=SID, t0=T0, t_end=T_END, turn_end=T_END - 15000)


def usage_row(eid, rid, occurred, inp, out, latency=1000, route="automaticai/intelliforia/claude-opus-5.5", **extra):
    data = {"route": route, "usage": {"input_tokens": inp, "output_tokens": out, "uncached_input_tokens": 2, "cache_read_input_tokens": 0,
                                      "cache_write_input_tokens": inp - 2, "reasoning_output_tokens": 0},
            "outcome": "completed", "consumer": {"kind": "gateway_token", "agent": "claude-code", "token_name": "aai:claude-code:1"},
            "usage_id": "newapi-log:1", "account_id": "claude-x", "latency_ms": latency, "request_id": rid, "session_id": SID,
            "occurred_at": occurred, "status_code": 200, "native_model": "claude-opus-5-5", "request_path": "/v1/messages",
            "billing_class": "subscription", "gateway_log_id": 947807, "returned_model": "claude-opus-5-5", "requested_model": route,
            "effective_effort": "high", "requested_effort": "high", "time_to_first_token_ms": 627}
    data.update(extra)
    return {"id": eid, "type": G.USAGE_TYPE, "time": occurred.replace("Z", "+00:00"), "received_at": "2026-11-16T04:00:41.325801+00:00",
            "subject": "bloodbank.evt.llm.usage.recorded", "correlationid": eid, "causationid": None,
            "producer": "automaticai-usage-exporter", "data": data}


def allowance_row(eid, rid, cause, win="five_hour"):
    return {"id": eid, "type": G.ALLOW_TYPE, "time": "2026-11-16T04:00:40+00:00", "received_at": "2026-11-16T04:00:41.335590+00:00",
            "subject": "bloodbank.evt.llm.allowance.observed", "correlationid": eid, "causationid": cause, "producer": "automaticai-usage-exporter",
            "data": {"window": win, "utilization_percent": 3.5, "reset_at": "2026-11-16T09:00:00Z", "request_id": rid}}


class FakeRunner:
    def __init__(self, usage, allowance=()):
        self.usage, self.allowance, self.sql = usage, list(allowance), []

    def __call__(self, sql, timeout=20.0):
        self.sql.append(sql)
        return list(self.usage if G.USAGE_TYPE in sql and "allowance" not in sql else self.allowance)


MAIN_CALL = {"source": "main", "n": 1, "agent_id": None, "agent_type": None, "input_tokens": 41765, "output_tokens": 49,
             "t0": ms("2026-11-16T04:00:39.598Z"), "t1": ms("2026-11-16T04:00:40.982Z"), "requested_model": "r", "served_model": "s",
             "client_request": "req"}


class Pure(unittest.TestCase):
    def test_rid_time(self):
        self.assertEqual(iso(G.rid_time_ms(RID1)), "2026-11-16T04:00:39.710Z")
        self.assertIsNone(G.rid_time_ms("not-a-request-id"))
        self.assertIsNone(G.rid_time_ms(None))

    def test_estimate_end_uses_occurred_and_latency(self):
        start = G.rid_time_ms(RID1)
        occurred = ms("2026-11-16T04:00:40Z")
        end, est = G.estimate_end(start, occurred, 1000)
        self.assertTrue(est)
        self.assertGreaterEqual(end, occurred)
        self.assertLess(end, occurred + 1000)
        self.assertAlmostEqual(G.estimate_end(None, occurred, None)[0], occurred + 499.5, places=1)
        self.assertEqual(G.estimate_end(start, None, 1000)[0], start + 1000)
        self.assertIsNone(G.estimate_end(None, None, None)[0])

    def test_match_counterparts(self):
        t = ms("2026-11-16T04:00:40.9Z")
        rows = [
            {"input_tokens": 41765, "output_tokens": 49, "t1": t, "rid": "a"},
            {"input_tokens": 1500, "output_tokens": 30, "t1": t, "rid": "b"},
            {"input_tokens": 777, "output_tokens": 5, "t1": t, "rid": "c"},
        ]
        calls = [MAIN_CALL,
                 {**MAIN_CALL, "source": "subagent", "n": 3, "agent_id": "abc", "agent_type": "workflow-subagent",
                  "input_tokens": 777, "output_tokens": 5, "t1": t}]
        G.match_counterparts(rows, calls)
        self.assertEqual([r["class"] for r in rows], ["main", "none", "subagent"])
        self.assertEqual(rows[2]["agent_id"], "abc")

    def test_match_counterparts_is_one_to_one(self):
        t = ms("2026-11-16T04:00:40.9Z")
        rows = [{"input_tokens": 1, "output_tokens": 1, "t1": t, "rid": "a"}, {"input_tokens": 1, "output_tokens": 1, "t1": t + 100, "rid": "b"}]
        G.match_counterparts(rows, [{**MAIN_CALL, "input_tokens": 1, "output_tokens": 1, "t1": t}])
        self.assertEqual(sorted(r["class"] for r in rows), ["main", "none"])

    def test_match_counterparts_respects_time_skew(self):
        rows = [{"input_tokens": 41765, "output_tokens": 49, "t1": MAIN_CALL["t1"] + 600000, "rid": "a"}]
        G.match_counterparts(rows, [MAIN_CALL])
        self.assertEqual(rows[0]["class"], "none")


class Sql(unittest.TestCase):
    def test_usage_query_is_read_only_shaped(self):
        r = FakeRunner([])
        G.fetch_usage_rows(SID, T0, T_END, r)
        sql = r.sql[0]
        self.assertTrue(sql.lstrip().lower().startswith("select"))
        self.assertIn("@>", sql)
        self.assertIn(SID, sql)
        self.assertIn(G.USAGE_TYPE, sql)
        for bad in (";", "insert ", "update ", "delete ", "drop "):
            self.assertNotIn(bad, sql.lower())

    def test_unsafe_session_id_rejected(self):
        with self.assertRaises(ValueError):
            G.fetch_usage_rows("x'; drop table events; --", T0, T_END, FakeRunner([]))

    def test_run_psql_argv_sets_read_only_and_has_no_password(self):
        cp = mock.Mock(returncode=0, stdout='SET\n{"id": "e1"}\nnoise\n', stderr="")
        with mock.patch("subprocess.run", return_value=cp) as run:
            rows = G.run_psql("select 1")
        argv = run.call_args[0][0]
        self.assertEqual(argv[:4], ["docker", "exec", "candystore-postgres", "sh"])
        self.assertIn("default_transaction_read_only=on", argv[-1])
        self.assertNotIn("PGPASSWORD", " ".join(argv))
        self.assertIn("$POSTGRES_USER", argv[5])
        self.assertEqual(rows, [{"id": "e1"}])

    def test_run_psql_error(self):
        with mock.patch("subprocess.run", return_value=mock.Mock(returncode=2, stdout="", stderr="boom")):
            with self.assertRaises(RuntimeError):
                G.run_psql("select 1")

    def test_allowance_query_only_for_safe_ids(self):
        r = FakeRunner([])
        self.assertEqual(G.fetch_allowance_rows(["a b'c"], T0, T_END, r), [])
        self.assertEqual(r.sql, [])
        G.fetch_allowance_rows([RID1], T0, T_END, r)
        self.assertIn(RID1, r.sql[0])


class Collect(unittest.TestCase):
    def run_collect(self, rows, allowance=(), calls=(MAIN_CALL,), **ctx_kw):
        runner = FakeRunner(rows, allowance)
        with mock.patch.object(G, "_transcript_calls", return_value=list(calls) if calls is not None else None):
            return G.collect(Ctx(window=window(), **ctx_kw), runner=runner)

    def test_main_row(self):
        row = usage_row("ev-1", RID1, "2026-11-16T04:00:40Z", 41765, 49)
        f = self.run_collect([row], [allowance_row("al-1", RID1, "ev-1"), allowance_row("al-2", RID1, "ev-1", "weekly")])
        self.assertEqual(f.source.status, "ok")
        s = next(x for x in f.spans if x.id == f"gw:{RID1}")
        self.assertEqual(s.kind, "llm")
        self.assertEqual(s.component, "aai-gateway")
        self.assertEqual(s.phase, "model_call")
        self.assertEqual(iso(s.t0), "2026-11-16T04:00:39.710Z")
        self.assertTrue(s.sync)
        self.assertEqual(s.refs["request_id"], RID1)
        self.assertEqual(s.refs["event_id"], "ev-1")
        self.assertEqual(s.attrs["_match_llm"]["input_tokens"], 41765)
        self.assertEqual(s.attrs["_match_llm"]["output_tokens"], 49)
        self.assertIn("near", s.attrs["_match_llm"])
        self.assertEqual(s.attrs["route"], "automaticai/intelliforia/claude-opus-5.5")
        self.assertEqual(s.attrs["native_model"], "claude-opus-5-5")
        self.assertEqual(s.attrs["effective_effort"], "high")
        self.assertEqual(s.attrs["ttft_ms"], 627)
        self.assertEqual(s.attrs["latency_ms"], 1000)
        self.assertEqual(s.attrs["status_code"], 200)
        self.assertEqual(s.attrs["token_name"], "aai:claude-code:1")
        self.assertEqual(s.attrs["gateway_log_id"], 947807)
        self.assertEqual(s.attrs["tokens_in"], 41765)
        self.assertEqual(s.attrs["counterpart"], "main")
        self.assertEqual([a["window"] for a in s.attrs["allowance"]], ["five_hour", "weekly"])
        self.assertTrue(s.attrs["t1_estimated"])
        self.assertEqual(s.status, "ok")

    def test_events_publish_spans_and_links(self):
        row = usage_row("ev-1", RID1, "2026-11-16T04:00:40Z", 41765, 49)
        f = self.run_collect([row], [allowance_row("al-1", RID1, "ev-1")])
        ev = {e.id: e for e in f.events}
        self.assertEqual(set(ev), {"ev-1", "al-1"})
        e = ev["ev-1"]
        self.assertEqual(e.type, G.USAGE_TYPE)
        self.assertEqual(e.stream, "BLOODBANK_EVENTS")
        self.assertEqual(e.publisher_span, "publish:ev-1")
        self.assertEqual(iso(e.archived), "2026-11-16T04:00:41.325Z")
        self.assertEqual((e.consumers[0].name, e.consumers[0].outcome, e.consumers[0].evidence), ("candystore-events", "archived", "observed"))
        self.assertEqual(ev["al-1"].causationid, "ev-1")
        self.assertIn(f.artifacts[e.payload]["json"]["request_id"], (RID1,))
        pub = next(s for s in f.spans if s.id == "publish:ev-1")
        self.assertEqual((pub.kind, pub.component), ("publish", "aai-llm-observability"))
        got = {(l.from_, l.to, l.kind) for l in f.links}
        self.assertIn((f"gw:{RID1}", "publish:ev-1", "records"), got)
        self.assertIn(("publish:ev-1", "evt:ev-1", "publishes"), got)
        self.assertEqual(len(got), len(f.links))

    def test_background_and_subagent_rows_get_no_match_hint(self):
        bg = usage_row("ev-2", RID2, "2026-11-16T04:00:41Z", 1481, 30, route="automaticai/personal/claude-sonnet-5.5")
        main = usage_row("ev-1", RID1, "2026-11-16T04:00:40Z", 41765, 49)
        sub_rid = "20261116040040500000000000000000subAGNT"
        sub = usage_row("ev-3", sub_rid, "2026-11-16T04:00:41Z", 777, 5)
        sub_call = {**MAIN_CALL, "source": "subagent", "agent_id": "abc", "agent_type": "workflow-subagent", "input_tokens": 777,
                    "output_tokens": 5, "t1": ms("2026-11-16T04:00:41.2Z")}
        f = self.run_collect([main, bg, sub], calls=[MAIN_CALL, sub_call])
        by = {s.id: s for s in f.spans if s.kind == "llm"}
        self.assertIn("_match_llm", by[f"gw:{RID1}"].attrs)
        b = by[f"gw:{RID2}"]
        self.assertTrue(b.attrs["background"])
        self.assertNotIn("_match_llm", b.attrs)
        self.assertFalse(b.sync)
        self.assertIn("no transcript counterpart", b.summary)
        s = by[f"gw:{sub_rid}"]
        self.assertEqual(s.attrs["counterpart"], "subagent")
        self.assertEqual(s.attrs["agent_id"], "abc")
        self.assertNotIn("_match_llm", s.attrs)
        self.assertFalse(s.sync)
        gap = next(g for g in f.gaps if "no transcript counterpart" in g.what)
        self.assertIn("1 gateway call", gap.what)
        self.assertEqual(f.facts["gateway_background"], 1)

    def test_rows_before_the_prompt_are_dropped(self):
        old_rid = "20261116035900000000000000000000oldROW"
        f = self.run_collect([usage_row("ev-0", old_rid, "2026-11-16T03:59:01Z", 5, 5), usage_row("ev-1", RID1, "2026-11-16T04:00:40Z", 41765, 49)])
        self.assertEqual([s.id for s in f.spans if s.kind == "llm"], [f"gw:{RID1}"])

    def test_failed_request(self):
        row = usage_row("ev-1", RID1, "2026-11-16T04:00:40Z", 41765, 49, outcome="upstream_error", status_code=529)
        s = next(x for x in self.run_collect([row]).spans if x.kind == "llm")
        self.assertEqual(s.status, "failed")
        self.assertIn("529", s.reason)

    def test_empty_result(self):
        f = self.run_collect([])
        self.assertEqual(f.source.status, "empty")
        self.assertEqual(f.spans, [])

    def test_fail_soft_when_postgres_is_down(self):
        def boom(sql, timeout=20.0):
            raise RuntimeError("psql exit 1: container not running")
        f = G.collect(Ctx(window=window()), runner=boom)
        self.assertEqual(f.source.status, "error")
        self.assertIn("container not running", f.source.error)
        self.assertEqual((f.spans, f.events, f.links), ([], [], []))
        self.assertTrue(any(g.severity == "warn" for g in f.gaps))

    def test_transcript_unavailable_leaves_matching_to_assembler(self):
        row = usage_row("ev-1", RID1, "2026-11-16T04:00:40Z", 41765, 49)
        f = self.run_collect([row], calls=None)
        s = next(x for x in f.spans if x.kind == "llm")
        self.assertIn("_match_llm", s.attrs)
        self.assertEqual(s.attrs["counterpart"], "unknown")
        self.assertTrue(any("could not be matched" in g.what for g in f.gaps))


class Deep(unittest.TestCase):
    TRACE = {"role": "fast", "client": "claude-code", "target": "t", "account": "a", "outcome": "served", "status": 200, "attempts": 2,
             "created_at": "2026-11-16T04:00:39.712951Z",
             "trace": {"role_source": "slot", "model": "automaticai/auto/fast",
                       "steps": [{"seq": 1, "stage": "request", "check": "role", "result": "fast"}],
                       "attempts": [{"attempt": 1, "channel_id": 6, "action": "failover", "reason": "rate_limited", "source": "routing", "elapsed_ms": 200},
                                    {"attempt": 2, "channel_id": 7, "action": "success", "reason": "request_completed", "source": "upstream", "elapsed_ms": 900}]}}

    def collect(self, **kw):
        row = usage_row("ev-1", RID1, "2026-11-16T04:00:40Z", 41765, 49)
        runner = FakeRunner([row])
        with mock.patch.object(G, "_transcript_calls", return_value=[MAIN_CALL]):
            return G.collect(Ctx(window=window(), deep=True), runner=runner, **kw)

    def test_trace_attached_as_fallback(self):
        f = self.collect(trace_fetcher=lambda rid: self.TRACE)
        s = next(x for x in f.spans if x.kind == "llm")
        fb = s.attrs["fallback"]
        self.assertEqual(fb["role"], "fast")
        self.assertEqual(fb["attempts"], 2)
        self.assertEqual([h["action"] for h in fb["hops"]], ["failover", "success"])
        self.assertEqual(fb["upstream_elapsed_ms"], 1100)
        self.assertIn("request.role=fast", fb["steps"])
        self.assertEqual(s.attrs["slot_role"], "fast")
        self.assertEqual(s.attrs["t1_source"], "trace")
        self.assertEqual(s.t1, ms("2026-11-16T04:00:39.712951Z") + 1100)
        self.assertTrue(any("2 upstream attempts" in x.title for x in f.findings))

    def test_trace_failure_is_a_gap_not_an_error(self):
        def bad(rid):
            raise OSError("timeout")
        f = self.collect(trace_fetcher=bad)
        self.assertEqual(f.source.status, "ok")
        self.assertTrue(any("could not be fetched" in g.what for g in f.gaps))

    def test_not_deep_never_fetches(self):
        row = usage_row("ev-1", RID1, "2026-11-16T04:00:40Z", 41765, 49)
        called = []
        with mock.patch.object(G, "_transcript_calls", return_value=[MAIN_CALL]):
            G.collect(Ctx(window=window(), deep=False), runner=FakeRunner([row]), trace_fetcher=lambda rid: called.append(rid))
        self.assertEqual(called, [])

    def test_pat_is_used_but_never_stored_in_the_fragment(self):
        secret = "PAT-SECRET-VALUE-0123456789"
        seen = {}

        def fake_fetch(rid, token, timeout=8.0):
            seen["token"] = token
            return self.TRACE

        with mock.patch.object(G, "read_pat", return_value=secret), mock.patch.object(G, "fetch_trace", side_effect=fake_fetch):
            f = self.collect()
        self.assertEqual(seen["token"], secret)
        self.assertNotIn(secret, json.dumps(to_jsonable(f), default=str))

    def test_missing_pat_is_a_gap(self):
        with mock.patch.object(G, "read_pat", return_value=None):
            f = self.collect()
        self.assertTrue(any("not fetched" in g.what for g in f.gaps))
        self.assertNotIn("fallback", next(x for x in f.spans if x.kind == "llm").attrs)

    def test_read_pat_uses_op_read_and_hides_failures(self):
        with mock.patch("subprocess.run", return_value=mock.Mock(returncode=0, stdout="tok\n")) as run:
            self.assertEqual(G.read_pat(), "tok")
        self.assertEqual(run.call_args[0][0][:2], ["op", "read"])
        with mock.patch("subprocess.run", return_value=mock.Mock(returncode=1, stdout="")):
            self.assertIsNone(G.read_pat())
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            self.assertIsNone(G.read_pat())


if __name__ == "__main__":
    unittest.main()
