"""Regression tests for the recorder-fixer findings (handler bars, event order, candystore lag, ASM edges, consumer
canonicalisation, duplicate edges, bb-hook clients, codex timing/tokens, record filtering, show collapsing ...).

Every test is offline: fragments are built by hand and run through the real assembler."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from waybill import assemble as A  # noqa: E402
from waybill import cli as C  # noqa: E402
from waybill import model as M  # noqa: E402
from waybill import show as S  # noqa: E402
from waybill import window as W  # noqa: E402
from waybill.collectors import asm, hookhub, logs  # noqa: E402
from waybill.collectors import transcript_codex as TC  # noqa: E402
from test_assemble import (EVT_TC, EVT_TS, SID, STOP, T, UPS, _src, handler, hook, links_set,  # noqa: E402
                           spans_by_id, window)


def build(frags, **wkw) -> dict:
    return A.assemble(window(**wkw), frags, profile="full", mode="capture", argv=["waybill", "capture"])


def ev(eid: str, etype: str, t: float, **kw) -> M.BusEvent:
    return M.BusEvent(id=eid, type=etype, t=t, subject="bloodbank.evt." + etype[len("bloodbank."):],
                      stream="BLOODBANK_EVENTS", correlationid=SID, **kw)


class HandlerBars(unittest.TestCase):
    def test_run_window_excludes_queue_wait(self):
        e = {"selected_at": M.iso(T), "started_at": M.iso(T + 10), "finished_at": M.iso(T + 1760), "duration_ms": 160}
        t0, t1, queued = hookhub.run_window(e)
        self.assertAlmostEqual(t1 - t0, 160, places=1)
        self.assertAlmostEqual(queued, 1600, delta=1)       # selected -> run start

    def test_run_window_falls_back_without_duration(self):
        e = {"selected_at": M.iso(T), "started_at": M.iso(T + 10), "finished_at": M.iso(T + 200)}
        t0, t1, queued = hookhub.run_window(e)
        self.assertEqual((round(t0 - T), round(t1 - T), queued), (10, 200, None))

    def test_bar_violation_check(self):
        good = {"spans": [{"id": "h1", "kind": "handler", "t0": 0, "t1": 160, "attrs": {"duration_ms": 160}}]}
        bad = {"spans": [{"id": "h2", "kind": "handler", "t0": 0, "t1": 1760, "attrs": {"duration_ms": 160}}]}
        self.assertEqual(A.handler_bar_violations(good), [])
        self.assertEqual(A.handler_bar_violations(bad), [("h2", 1760, 160.0)])

    def test_assembled_waybill_raises_a_finding_for_a_queue_wait_bar(self):
        hh = M.Fragment(source=_src("hookhub"))
        hh.spans += [hook(UPS, "UserPromptSubmit", T + 20, T + 900), handler(UPS, "nanoleaf", T + 30, T + 1790)]
        hh.spans[-1].attrs["duration_ms"] = 160
        wb = build([hh])
        self.assertTrue(any("handler bar" in f["title"] for f in wb["findings"]))


class EventTimes(unittest.TestCase):
    def _frags(self, env_t: float, stored: float, cause_t1: float):
        hh = M.Fragment(source=_src("hookhub"))
        hh.spans += [hook(UPS, "UserPromptSubmit", T + 20, T + 900)]
        gw = M.Fragment(source=_src("gateway"))
        gw.spans.append(M.Span(id="llm:1", kind="llm", component="aai-gateway", name="call", summary="x",
                               phase="model_call", t0=T + 100, t1=cause_t1, sync=True, evidence=["gateway"]))
        cs = M.Fragment(source=_src("candystore"))
        cs.events.append(ev("e-usage", "bloodbank.llm.usage.recorded", env_t, stored=stored,
                            publisher_span="publish:e-usage"))
        gw.spans.append(M.Span(id="publish:e-usage", kind="publish", component="aai-llm-observer", name="usage",
                               summary="p", phase="model_call", t0=env_t, t1=env_t + 1, parent="llm:1",
                               refs={"event_id": "e-usage"}, evidence=["gateway"]))
        return [hh, gw, cs]

    def test_second_truncated_envelope_uses_stored_time(self):
        # the call finished at +1450 ms; the envelope says +1000 (truncated), JetStream stored it at +1600
        wb = build(self._frags(T + 1000, T + 1600, T + 1450))
        e = next(x for x in wb["events"] if x["id"] == "e-usage")
        self.assertGreaterEqual(e["t"], 1450 - 0.5)
        self.assertEqual(A.event_order_violations(wb), [])
        self.assertIn("t_envelope", e)
        self.assertEqual(e["t_envelope"], 1000)

    def test_event_never_precedes_its_cause_even_without_stored_time(self):
        wb = build(self._frags(T + 1000, None, T + 1450))
        e = next(x for x in wb["events"] if x["id"] == "e-usage")
        self.assertGreaterEqual(e["t"], 1450)
        self.assertIn("clamped", e["t_adjusted"])

    def test_violation_detector_flags_a_real_inversion(self):
        wb = {"spans": [{"id": "llm:1", "kind": "llm", "t0": 0, "t1": 1450},
                        {"id": "publish:x", "kind": "publish", "parent": "llm:1", "t0": 1000}],
              "events": [{"id": "x", "t": 1000, "publisher_span": "publish:x", "causationid": None}]}
        self.assertEqual(A.event_order_violations(wb), ["x"])


class CandystoreSpans(unittest.TestCase):
    def test_consume_span_starts_at_stored_time_and_blames_the_publisher(self):
        hh = M.Fragment(source=_src("hookhub"))
        hh.spans += [hook(UPS, "UserPromptSubmit", T + 20, T + 900),
                     handler(UPS, "bloodbank-publisher", T + 30, T + 60, sync=False, event_id=EVT_TS,
                             event_type="bloodbank.conversation.turn.started")]
        cs = M.Fragment(source=_src("candystore"))
        cs.events.append(M.BusEvent(
            id=EVT_TS, type="bloodbank.conversation.turn.started", t=T + 60, stored=T + 2060, archived=T + 2070,
            subject="bloodbank.evt.conversation.turn.started", stream="BLOODBANK_EVENTS",
            publisher_span=M.Ids.publish(EVT_TS),
            consumers=[M.Consumer(name="candystore-events", component="candystore", kind="durable", outcome="archived",
                                  t=T + 2070, evidence="observed", span=M.Ids.consume("candystore-events", EVT_TS))]))
        cs.spans.append(M.Span(id=M.Ids.consume("candystore-events", EVT_TS), kind="consume", component="candystore",
                               name="turn.started", summary="x", phase="async_after", t0=T + 60, t1=T + 2070,
                               refs={"event_id": EVT_TS}, evidence=["candystore"]))
        wb = build([hh, cs])
        sp = spans_by_id(wb)[M.Ids.consume("candystore-events", EVT_TS)]
        self.assertAlmostEqual(sp["t1"] - sp["t0"], 10, delta=1)             # stored -> received, not 2 s
        self.assertAlmostEqual(sp["attrs"]["publisher_lag_ms"], 2000, delta=5)
        titles = [f for f in wb["findings"] if f["component"] == "hook-hub" and "reached the bus" in f["title"]]
        self.assertEqual(len(titles), 1)


class AsmSnapping(unittest.TestCase):
    def test_log_edges_snap_to_invocations_and_never_precede_them(self):
        invs = [{"invocation_id": "t1", "received_ms": T + 5300.0}]
        entries = [{"src": "log", "at_ms": T + 5500.0, "log_ts_ms": T + 5000.0},      # 1 s log line + 500 centre
                   {"src": "log", "at_ms": T + 60500.0, "log_ts_ms": T + 60000.0}]
        left = asm.snap_to_invocations(entries, invs)
        self.assertEqual(left, [])
        self.assertEqual(entries[0]["at_ms"], T + 5300.0)
        self.assertEqual(entries[0]["time_precision"], "invocation")
        self.assertEqual(entries[0]["invocation_id"], "t1")
        self.assertEqual(entries[1]["time_precision"], "1s")                              # nothing to snap to

    def test_stream_edge_keeps_its_time_and_gains_the_invocation(self):
        invs = [{"invocation_id": "t1", "received_ms": T + 100.0}, {"invocation_id": "t2", "received_ms": T + 9000.0}]
        entries = [{"src": "stream", "at_ms": T + 90.0}]
        left = asm.snap_to_invocations(entries, invs)
        self.assertEqual(entries[0]["at_ms"], T + 90.0)
        self.assertEqual(entries[0]["invocation_id"], "t1")
        self.assertEqual([i["invocation_id"] for i in left], ["t2"])        # an invocation with no edge is reported

    def test_deckard_lines_become_spans_after_an_edge(self):
        text = ("2026-11-16T05:21:20.300000+00:00 host deckard[12]: tab metadata changed focus \"x\"\n"
                "2026-11-16T05:21:25.000000+00:00 host deckard[12]: tab metadata changed focus \"y\"\n"
                "2026-11-16T05:21:20.310000+00:00 host deckard[12]: something else\n")
        t = M.ms("2026-11-16T05:21:20.300Z")
        lines = asm.parse_deckard_lines(text, t - 5000, t + 10000)
        self.assertEqual(len(lines), 2)
        frag = M.Fragment(source=_src("asm"))
        edge = M.Span(id="state:asm:1", kind="state", component="asm", name="none -> starting", summary="e",
                      phase="session_start", t0=t - 100, evidence=["asm"])
        self.assertEqual(asm.deckard_spans(frag, lines, [edge]), 1)           # the 25 s line has no edge in reach
        self.assertEqual(frag.spans[0].component, "deckard")
        self.assertIn(("state:asm:1", frag.spans[0].id, "triggers"), [(l.from_, l.to, l.kind) for l in frag.links])


class CodexTokens(unittest.TestCase):
    def test_uncached_is_input_minus_cached(self):
        span = {"attrs": {"usage": {"input_tokens": 110860, "cached_input_tokens": 58880, "output_tokens": 10},
                          "tokens_in": 110860, "input_tokens": 110860}}
        tin, raw, tout = A.llm_tokens(span)
        self.assertEqual((tin, raw, tout), (110860, 51980, 10))

    def test_anthropic_style_input_excludes_cache(self):
        span = {"attrs": {"usage": {"input_tokens": 3, "cache_read_input_tokens": 40000, "output_tokens": 5}}}
        self.assertEqual(A.llm_tokens(span), (40003, 3, 5))


class ConsumerNames(unittest.TestCase):
    def test_canonical_names(self):
        self.assertEqual(A.canonical_consumer_name("bloodbank-ntfy-router"), "ntfy-router")
        self.assertEqual(A.canonical_consumer_name("holocene_Xy12_1"), "holocene")
        self.assertEqual(A.canonical_consumer_name("candystore-events"), "candystore-events")

    def test_observed_row_drops_inferred_twin_and_keeps_aliases(self):
        hh = M.Fragment(source=_src("hookhub"))
        hh.spans += [hook(UPS, "UserPromptSubmit", T + 20, T + 900)]
        cs = M.Fragment(source=_src("candystore"))
        cs.events.append(ev(EVT_TC, "bloodbank.conversation.turn.completed", T + 3000, consumers=[
            M.Consumer(name="holocene", component="holocene", kind="ephemeral", outcome="collected", t=T + 3001,
                       evidence="observed"),
            M.Consumer(name="holocene_Xy12_1", component="holocene", kind="ephemeral", outcome="unknown",
                       evidence="inferred"),
            M.Consumer(name="bloodbank-ntfy-router", component="ntfy-router", kind="core", outcome="unknown",
                       evidence="inferred"),
            M.Consumer(name="ntfy-router", component="ntfy-router", kind="core", outcome="routed", t=T + 3100,
                       evidence="observed")]))
        wb = build([hh, cs])
        e = next(x for x in wb["events"] if x["id"] == EVT_TC)
        names = sorted(c["name"] for c in e["consumers"])
        self.assertEqual(names.count("holocene"), 1)
        self.assertEqual(names.count("ntfy-router"), 1)
        self.assertFalse(any(n.startswith(("holocene_", "bloodbank-ntfy")) for n in names))
        obs = next(c for c in e["consumers"] if c["name"] == "ntfy-router")
        self.assertEqual(obs["evidence"], "observed")
        self.assertIn("bloodbank-ntfy-router", obs.get("aliases", []))


class Edges(unittest.TestCase):
    def test_duplicate_edge_detector(self):
        links = [{"from": "a", "to": "b", "kind": "calls"}, {"from": "a", "to": "b", "kind": "triggers"},
                 {"from": "a", "to": "c", "kind": "calls"}]
        self.assertEqual(A.duplicate_edges(links), [("a", "b", ["calls", "triggers"])])

    def test_assembled_waybill_has_one_edge_per_pair(self):
        from test_assemble import build as sbuild
        wb = sbuild()
        self.assertEqual(A.duplicate_edges(wb["links"]), [])
        self.assertFalse(any("more than one edge" in f["title"] for f in wb["findings"]))

    def test_llm_to_tool_calls_dropped_when_prehook_chain_exists(self):
        from test_assemble import build as sbuild
        wb = sbuild()
        L = links_set(wb)
        pairs = {(f, t) for f, t, _k in L}
        for f, t, k in L:
            if k == "calls" and f.startswith("llm:") and t.startswith("tool:"):
                self.assertNotIn(("triggers", f, t), {(kk, ff, tt) for ff, tt, kk in L})


class ThinStep2(unittest.TestCase):
    def test_inferred_consumers_are_dropped_first_observed_kept(self):
        wb = build([_frag_with_many_consumers()])
        small = A.thin_to_budget(json.loads(json.dumps(wb)), 1)
        for e in small["events"]:
            for c in e["consumers"]:
                self.assertNotEqual(c.get("evidence"), "inferred")
        obs_before = sum(1 for e in wb["events"] for c in e["consumers"] if c["evidence"] == "observed")
        obs_after = sum(1 for e in small["events"] for c in e["consumers"] if c["evidence"] == "observed")
        self.assertEqual(obs_before, obs_after)


def _frag_with_many_consumers() -> M.Fragment:
    f = M.Fragment(source=_src("candystore"))
    f.events.append(ev(EVT_TS, "bloodbank.conversation.turn.started", T + 100, consumers=[
        M.Consumer(name="candystore-events", component="candystore", kind="durable", outcome="archived", t=T + 110,
                   evidence="observed"),
        M.Consumer(name="enricher-events", component="enricher", kind="durable", outcome="unknown", evidence="inferred"),
        M.Consumer(name="deckard", component="deckard", kind="core", outcome="unknown", evidence="inferred")]))
    return f


class TimestampFlag(unittest.TestCase):
    def test_relative_looking_values_are_flagged_not_silently_trusted(self):
        bad: list = []
        self.assertEqual(A._rel(T + 500, T, bad), 500)
        self.assertEqual(bad, [])
        A._rel(1234.0, T, bad)
        self.assertEqual(bad, [1234.0])

    def test_assembler_emits_a_gap_for_a_non_epoch_time(self):
        hh = M.Fragment(source=_src("hookhub"))
        hh.spans += [hook(UPS, "UserPromptSubmit", T + 20, T + 900)]
        hh.spans.append(M.Span(id="state:odd", kind="state", component="asm", name="odd", summary="x",
                               phase="session_start", t0=1234.0, evidence=["asm"]))
        wb = build([hh])
        self.assertTrue(any("not absolute epoch" in g["what"] for g in wb["gaps"]))


class GatewayTime(unittest.TestCase):
    def test_gateway_request_id_time_wins_and_client_time_is_kept(self):
        tr = M.Fragment(source=_src("transcript"))
        tr.spans.append(M.Span(id=M.Ids.llm(1), kind="llm", component="aai-gateway", name="call", summary="c",
                               phase="model_call", t0=T + 1000, t1=T + 2000, sync=True,
                               attrs={"usage": {"input_tokens": 10, "output_tokens": 5}}, evidence=["transcript"]))
        gw = M.Fragment(source=_src("gateway"))
        gw.spans.append(M.Span(id="llm:gw:r1", kind="llm", component="aai-gateway", name="usage", summary="g",
                               phase="model_call", t0=T + 1040, t1=T + 1990, refs={"request_id": "r1"},
                               attrs={"t0_source": "request_id",
                                      "_match_llm": {"input_tokens": 10, "output_tokens": 5, "near": T + 1990}},
                               evidence=["gateway"]))
        wb = build([tr, gw])
        llm = spans_by_id(wb)[M.Ids.llm(1)]
        self.assertAlmostEqual(llm["t0"], 1040, delta=1)
        self.assertIn("transcript_t", llm["attrs"])
        self.assertAlmostEqual(llm["attrs"]["transcript_t"]["t0"], 1000, delta=1)


class BbHookClients(unittest.TestCase):
    def test_client_span_parents_the_hub_hook_with_a_delta(self):
        hh = M.Fragment(source=_src("hookhub"))
        hh.spans += [hook(UPS, "UserPromptSubmit", T + 20, T + 900)]
        hh.spans.append(hook("inv-pre", "PreToolUse", T + 2040, T + 2090))
        tr = M.Fragment(source=_src("transcript"))
        tr.component("bb-hook", "bb-hook", "service")
        tr.spans.append(M.Span(
            id="clienthook:PreToolUse:%d" % (T + 2000), kind="hook", component="bb-hook", name="PreToolUse (client)",
            summary="client", phase="tool", t0=T + 2000, t1=T + 2100, sync=True,
            attrs={"_hub_match": {"native": "PreToolUse", "tool_use_id": None, "t0": T + 2000, "t1": T + 2100}},
            evidence=["transcript"]))
        wb = build([hh, tr])
        S_ = spans_by_id(wb)
        client = S_["clienthook:PreToolUse:%d" % (T + 2000)]
        hub = S_[M.Ids.hook("inv-pre")]
        self.assertEqual(hub["parent"], client["id"])
        self.assertTrue(client["attrs"]["reached_hub"])
        self.assertAlmostEqual(client["attrs"]["client_minus_hub_ms"], 50, delta=2)

    def test_unmatched_hub_hooks_keep_a_narrowed_gap(self):
        hh = M.Fragment(source=_src("hookhub"))
        hh.spans += [hook(UPS, "UserPromptSubmit", T + 20, T + 900)]
        wb = build([hh])
        gap = [g for g in wb["gaps"] if g["what"].startswith("bb-hook client timing")]
        self.assertTrue(gap)
        self.assertIn("UserPromptSubmit", gap[0]["what"])


class NtfyJoins(unittest.TestCase):
    def _lg(self, lines):
        frag = M.Fragment(source=_src("logs"))
        logs.build_ntfy(frag, lines, [])
        return frag

    def test_every_non_cron_line_is_offered_with_an_optional_join(self):
        lines = [{"t": T + 100.0, "kind": "routed", "type": "bloodbank.llm.usage.recorded"},
                 {"t": T + 100.0, "kind": "rate-limited", "type": "bloodbank.cron.candybar.invoked"},
                 {"t": T + 110.0, "kind": "routed", "type": "com.dapr.event.sent"}]
        frag = self._lg(lines)
        self.assertEqual(len(frag.spans), 2)       # cron chatter never reaches the assembler
        for s in frag.spans:
            self.assertTrue(s.attrs["_join"]["optional"])
            self.assertEqual(s.attrs["_join"]["match"], "type+time")

    def test_assembler_ties_lines_by_stored_time_and_drops_strangers(self):
        hh = M.Fragment(source=_src("hookhub"))
        hh.spans += [hook(UPS, "UserPromptSubmit", T + 20, T + 900)]
        cs = M.Fragment(source=_src("candystore"))
        cs.events.append(ev("e-usage", "bloodbank.llm.usage.recorded", T + 1000, stored=T + 1700))
        cs.events.append(ev("e-report", "bloodbank.report.session.completed", T + 2000, stored=T + 2300,
                            stored_type="com.dapr.event.sent"))
        lines = [{"t": T + 1750.0, "kind": "routed", "type": "bloodbank.llm.usage.recorded"},
                 {"t": T + 2350.0, "kind": "digested", "type": "com.dapr.event.sent"},
                 {"t": T + 9000.0, "kind": "routed", "type": "bloodbank.llm.usage.recorded"}]   # nothing within reach
        lg = M.Fragment(source=_src("logs"))
        logs.build_ntfy(lg, lines, [])
        wb = build([hh, cs, lg])
        notify = [s for s in wb["spans"] if s["kind"] == "notify"]
        self.assertEqual(len(notify), 2)
        by_type = {s["attrs"]["event_type"]: s for s in notify}
        self.assertEqual(by_type["bloodbank.llm.usage.recorded"]["attrs"]["match"], "type+time")
        self.assertEqual(by_type["bloodbank.report.session.completed"]["attrs"]["stored_type"], "com.dapr.event.sent")
        self.assertFalse(any("could not be tied" in g["what"] for g in wb["gaps"] if g["component"] == "ntfy-router"))
        e = next(x for x in wb["events"] if x["id"] == "e-report")
        self.assertTrue(any(c["name"] == "ntfy-router" and c["evidence"] == "observed" for c in e["consumers"]))
        self.assertEqual(e["stored_type"], "com.dapr.event.sent")


class JevAndEnricher(unittest.TestCase):
    def test_parse_jev(self):
        got = logs.parse_jev([(1.0, 'INFO:  1.2.3.4:5 - "POST /typesafe/v1/systemone HTTP/1.1" 200 OK'),
                              (2.0, 'INFO:  1.2.3.4:5 - "GET / HTTP/1.1" 200 OK'),
                              (3.0, 'INFO:  1.2.3.4:5 - "POST /typesafe/v1/systemone HTTP/1.1" 500 Err')])
        self.assertEqual(got, [{"t": 1.0, "code": 200}, {"t": 3.0, "code": 500}])

    def test_jev_span_is_an_off_thread_llm_under_the_enricher_consume(self):
        frag = M.Fragment(source=_src("logs"))
        annotated = [{"t": T + 1100.0, "source_id": EVT_TC, "t_pub": T + 1000.0}]
        jev = [{"t": T + 900.0, "code": 200}, {"t": T + 1050.0, "code": 200}, {"t": T + 5000.0, "code": 200}]
        self.assertEqual(logs.build_jev(frag, jev, annotated), 1)
        sp = frag.spans[0]
        self.assertEqual((sp.kind, sp.component, sp.t0), ("llm", "jev-litellm", T + 1050.0))
        self.assertEqual(sp.parent, M.Ids.consume("turn-enricher", EVT_TC))
        self.assertEqual(sp.attrs["candidates"], 2)
        self.assertTrue(sp.attrs["ambiguous"])        # Hindsight shares the endpoint: two candidates, last taken

    def test_extractors_land_on_consume_span_and_jev_model(self):
        hh = M.Fragment(source=_src("hookhub"))
        hh.spans += [hook(UPS, "UserPromptSubmit", T + 20, T + 900)]
        cs = M.Fragment(source=_src("candystore"))
        completed = ev(EVT_TC, "bloodbank.conversation.turn.completed", T + 1000)
        ann_env = {"id": "e-ann", "type": "bloodbank.conversation.turn.annotated", "causationid": EVT_TC,
                   "data": {"target_event_id": EVT_TC,
                            "extractors": {"jev": "jev-latest", "clairic": "@cf/cloudflare/clairic"}}}
        annotated = ev("e-ann", "bloodbank.conversation.turn.annotated", T + 1200, causationid=EVT_TC,
                       payload=cs.artifact(ann_env))
        cs.events += [completed, annotated]
        lg = M.Fragment(source=_src("logs"))
        logs.build_jev(lg, [{"t": T + 1150.0, "code": 200}], [{"t": T + 1200.0, "source_id": EVT_TC, "t_pub": T + 1000.0}])
        lg.spans.append(M.Span(id=M.Ids.consume("turn-enricher", EVT_TC), kind="consume", component="turn-enricher",
                               name="turn.completed", summary="c", phase="async_after", t0=T + 1000, t1=T + 1200,
                               refs={"event_id": EVT_TC}, evidence=["logs"]))
        wb = build([hh, cs, lg])
        S_ = spans_by_id(wb)
        self.assertEqual(S_[M.Ids.consume("turn-enricher", EVT_TC)]["attrs"]["extractors"]["jev"], "jev-latest")
        jev = S_[M.Ids.jev_llm(EVT_TC)]
        self.assertEqual(jev["attrs"]["model"], "jev-latest")
        self.assertEqual(wb["stats"]["llm_calls"], 0)           # a service's call is not one of the agent's


class DockerBudget(unittest.TestCase):
    def test_tail_timeout_keeps_earlier_partial_data_and_says_so(self):
        calls = []

        def fake_run(argv, timeout):
            calls.append(argv)
            if "--since" in argv:
                return mock.Mock(returncode=0, stdout="", stderr="")
            if "2" in argv:       # the first, small tail is full and still newer than the window start
                return mock.Mock(returncode=0, stdout="2026-11-16T04:00:01Z a\n2026-11-16T04:00:02Z b\n", stderr="")
            raise __import__("subprocess").TimeoutExpired(argv, timeout)

        with mock.patch.object(logs, "_run", side_effect=fake_run), mock.patch.object(logs, "TAIL_STEPS", (2, 4)):
            lines, mode = logs.docker_lines("c", M.ms("2026-11-16T04:00:00Z"), M.ms("2026-11-16T04:05:00Z"), 5)
        self.assertTrue(mode.endswith(":partial"))
        self.assertEqual(len(lines), 2)

    def test_runner_keeps_a_timed_out_collectors_partial_fragment(self):
        part = M.Fragment(source=_src("logs", 3))
        part.spans.append(M.Span(id="x", kind="notify", component="ntfy-router", name="n", summary="s",
                                 phase="async_after", t0=T, evidence=["logs"]))
        out = C._timeout_fragment("logs", part, 25.0)
        self.assertEqual(out.source.status, "ok")
        self.assertEqual(len(out.spans), 1)
        self.assertTrue(any("timed out" in g.what for g in out.gaps))
        none = C._timeout_fragment("logs", None, 25.0)
        self.assertEqual(none.source.status, "error")


class HindsightBufferAsk(unittest.TestCase):
    def test_buffer_ask_starts_with_its_handler(self):
        hh = M.Fragment(source=_src("hookhub"))
        hh.spans += [hook(UPS, "UserPromptSubmit", T + 20, T + 900), handler(UPS, "hindsight-turn", T + 300, T + 350)]
        hs = M.Fragment(source=_src("hindsight"))
        hs.spans.append(M.Span(id=M.Ids.buffer(UPS), kind="memory", component="hindsight", name="buffer ask",
                               summary="b", phase="prompt_submit", t0=T, status="pending", sync=False,
                               parent=M.Ids.handler(UPS, "hindsight-turn"),
                               attrs={"buffer_event": "ask_buffered", "timing": "approximate: prompt submit"},
                               evidence=["hindsight"]))
        wb = build([hh, hs])
        ask = spans_by_id(wb)[M.Ids.buffer(UPS)]
        handler_span = spans_by_id(wb)[M.Ids.handler(UPS, "hindsight-turn")]
        self.assertEqual(ask["t0"], handler_span["t0"])


class MirrorParents(unittest.TestCase):
    def test_hook_updated_mirror_consume_hangs_under_its_hook(self):
        hh = M.Fragment(source=_src("hookhub"))
        hh.spans += [hook(UPS, "UserPromptSubmit", T + 20, T + 900)]
        cs = M.Fragment(source=_src("candystore"))
        mirror = ev("mirror-1", "bloodbank.agent.hook.updated", T + 100)
        mirror.correlationid = UPS
        cs.events.append(mirror)
        cs.spans.append(M.Span(id=M.Ids.consume("candystore-events", "mirror-1"), kind="consume",
                               component="candystore", name="hook.updated", summary="c", phase="async_after",
                               t0=T + 100, t1=T + 110, refs={"event_id": "mirror-1"}, evidence=["candystore"]))
        wb = build([hh, cs])
        sp = spans_by_id(wb)[M.Ids.consume("candystore-events", "mirror-1")]
        self.assertEqual(sp["parent"], M.Ids.hook(UPS))


class CodexTimingAndPrompt(unittest.TestCase):
    def _parse(self, records):
        row = {"rollout_byte_offset": 0, "rollout_end_byte_offset": None, "turn_id": "tid"}
        win = M.TurnWindow(cli="codex", surface="codex-exec", session_id="s", t0=T, t_end=T + 20000)
        with mock.patch.object(TC, "_slice", return_value=("/nope", row, 1)), \
                mock.patch.object(W, "iter_jsonl", return_value=iter(records)):
            return TC._parse_turn(win)

    def test_outer_tool_span_is_call_to_output_not_the_inner_exec(self):
        t = lambda off: M.iso(T + off)  # noqa: E731
        recs = [(1, 0, {"timestamp": t(0), "type": "response_item", "payload": {
                    "type": "function_call", "name": "exec_command", "call_id": "c1", "arguments": "{\"cmd\": \"ls\"}"}}),
                (2, 1, {"timestamp": t(2300), "type": "response_item", "payload": {
                    "type": "function_call_output", "call_id": "c1",
                    "output": "Chunk ID: 1\nWall time: 0.0 seconds\nProcess exited with code 0\nOutput:\nx"}}),
                (3, 2, {"timestamp": t(2301), "type": "event_msg", "payload": {
                    "type": "item_completed", "item": {"type": "CommandExecution", "id": "c1", "exit_code": 0},
                    "started_at_ms": T + 2290, "completed_at_ms": T + 2290}})]
        parsed = self._parse(recs)
        tool = parsed["tools"]["c1"]
        self.assertEqual(tool["t1"] - tool["t0"], 2300)            # the model waited 2.3 s, not 0 ms
        self.assertEqual(tool["exec"], {"t0": T + 2290.0, "t1": T + 2290.0})
        self.assertEqual(tool["wall_time_ms"], 0.0)

    def test_prompt_injections_report_size(self):
        text = "do it\n<skill>\n<name>brainstorm</name>\n" + "x" * 900 + "\n</skill>"
        inj = TC.prompt_injections(text)
        self.assertEqual([(i["kind"], i["name"]) for i in inj], [("skill", "brainstorm")])
        self.assertGreater(inj[0]["chars"], 900)
        self.assertEqual(TC.prompt_injections("<skill><name>tiny</name>x</skill>"), [])      # below the threshold


class RecordFilter(unittest.TestCase):
    def test_automation_and_cwd_are_filtered(self):
        briefs = {"cron": {"cwd": "/work/a", "prompt": "[IMPORTANT: You are running as a scheduled cron job.", "automation": "cron/Crank prompt"},
                  "other": {"cwd": "/elsewhere", "prompt": "hi", "automation": None},
                  "mine": {"cwd": "/work/a/sub", "prompt": "hi", "automation": None}}
        with mock.patch.object(W, "session_brief", side_effect=lambda sid, cli=None: briefs[sid]):
            flt = W.PromptFilter(cwd="/work/a")
            self.assertFalse(flt.accept("cron", "claude"))
            self.assertFalse(flt.accept("other", "claude"))
            self.assertTrue(flt.accept("mine", "claude"))
            self.assertIn("cron", flt.rejected)
            anywhere = W.PromptFilter(cwd="/work/a", any_cwd=True)
            self.assertTrue(anywhere.accept("other", "claude"))
            self.assertFalse(anywhere.accept("cron", "claude"))       # --any lifts the cwd test, not the automation one
            pinned = W.PromptFilter(session="cron")
            self.assertTrue(pinned.accept("cron", "claude"))
            self.assertFalse(pinned.accept("mine", "claude"))

    def test_latest_prompt_after_honours_the_filter(self):
        from test_window import Env, make_receipts, XSID
        with Env() as env:
            make_receipts(env.receipts, [("i1", "claude", "UserPromptSubmit", "sess-a", "2026-11-16T03:00:00Z"),
                                         ("i2", "claude", "UserPromptSubmit", "sess-b", "2026-11-16T03:01:00Z")])

            class OnlyA:
                def accept(self, sid, cli):
                    return sid == "sess-a"
            got = W.latest_prompt_after(M.ms("2026-11-16T02:00:00Z"), "claude", OnlyA())
            self.assertEqual(got[0], "sess-a")
            self.assertEqual(W.latest_prompt_after(M.ms("2026-11-16T02:00:00Z"), "claude")[0], "sess-b")

    def test_cli_has_session_cwd_any_flags(self):
        a = C.build_parser().parse_args(["record", "--session", "abc", "--cwd", "/x", "--any"])
        self.assertEqual((a.session, a.cwd, a.any), ("abc", "/x", True))


class TurnNumbering(unittest.TestCase):
    def test_turn_comes_from_the_transcript_index(self):
        # transcript turn 2 was submitted 20 ms before receipt #3 (receipts include an extra aged-in prompt)
        t_prompt = M.ms("2026-11-16T03:02:00Z")
        receipts = [{"invocation_id": f"r{i}", "cli": "claude", "native": "UserPromptSubmit", "received_ms": t_prompt + off,
                     "session_id": "sid"} for i, off in enumerate((-120000.0, -60000.0, 20.0), 1)]
        with mock.patch.object(W, "transcript_turn_ts", return_value=t_prompt), \
                mock.patch.object(W, "hook_invocations", return_value=receipts), \
                mock.patch.object(W, "claude_transcript_path", return_value=None), \
                mock.patch.object(W, "codex_thread", return_value=None), \
                mock.patch.object(W, "candystore_turns", return_value=([], None)):
            w = W.resolve("11111111-2222-3333-4444-555555555555", cli="claude", turn=2)
        self.assertEqual(w.prompt_invocation_id, "r3")           # not receipts[1]
        self.assertEqual(w.turn_index, 2)
        self.assertEqual(w.turn_source, "transcript")


class ProfileScrub(unittest.TestCase):
    def test_slug_and_remote_user_are_redacted(self):
        user = os.path.basename(M.HOME.rstrip("/"))
        if not user:
            self.skipTest("no home user")
        text = f"~/.claude/projects/-home-{user}-code-33GOD-candystore/x.jsonl git@github.com:{user}/candystore.git"
        out = A._tilde_str(text)
        self.assertIn("-~-code-33GOD-candystore", out)
        self.assertIn("git@github.com:~/candystore.git", out)
        self.assertNotIn(user, out)
        self.assertEqual(A._tilde_str("git@github.com:someone-else/repo.git"), "git@github.com:someone-else/repo.git")


class Memoisation(unittest.TestCase):
    def test_second_parse_of_an_unchanged_file_is_served_from_cache(self):
        from waybill.collectors import transcript_claude as TCL
        win = M.TurnWindow(cli="claude", surface="claude-code", session_id="s", t0=T, t_end=T + 1000)
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            fh.write("{}\n")
            path = fh.name
        try:
            n = []

            def fn():
                n.append(1)
                return {"records": [1, 2]}
            a = TCL.memoised_parse(path, win, ("t",), fn)
            b = TCL.memoised_parse(path, win, ("t",), fn)
            self.assertEqual(len(n), 1)
            self.assertEqual(a, b)
            a["records"].append(3)                                  # callers mutate their copy, never the cache
            self.assertEqual(TCL.memoised_parse(path, win, ("t",), fn), {"records": [1, 2]})
            with open(path, "a") as fh:
                fh.write("{}\n")
            os.utime(path, (time.time() + 5, time.time() + 5))
            TCL.memoised_parse(path, win, ("t",), fn)
            self.assertEqual(len(n), 2)                             # grew -> parsed again
        finally:
            os.unlink(path)


class ShowCollapse(unittest.TestCase):
    def _wb(self):
        spans = [{"id": "turn", "kind": "turn", "component": "cli", "name": "turn", "summary": "", "phase": "turn_end",
                  "t0": 0, "t1": 5000, "status": "ok", "evidence": []}]
        events = [{"id": f"u{i}", "type": "bloodbank.llm.usage.recorded", "t": 1000 + i * 500, "seq": 100 + i,
                   "producer": "obs", "consumers": [{"name": "candystore-events", "evidence": "observed", "outcome": "archived"}],
                   "publisher_span": None} for i in range(4)]
        events.append({"id": "r1", "type": "bloodbank.report.session.completed", "stored_type": "com.dapr.event.sent",
                       "t": 3000, "producer": "enricher", "consumers": [], "publisher_span": None})
        return {"title": "t", "origin": {}, "clock": {"duration_ms": 5000}, "stats": {}, "spans": spans, "events": events,
                "findings": [], "gaps": [], "sources": [], "components": {}, "recorder": {}}

    def test_usage_events_collapse_unless_all(self):
        collapsed = S.render(self._wb(), width=140, color=False)
        self.assertIn("4× llm.usage.recorded", collapsed)
        self.assertEqual(collapsed.count("llm.usage.recorded"), 1)
        expanded = S.render(self._wb(), width=140, show_all=True, color=False)
        self.assertGreaterEqual(expanded.count("llm.usage.recorded"), 4)

    def test_stored_type_is_shown_beside_the_type(self):
        self.assertIn("stored as com.dapr.event.sent", S.render(self._wb(), width=160, show_all=True, color=False))


class HindsightRetain(unittest.TestCase):
    """The flush -> retain -> consolidation chain is covered in test_hindsight.py; this keeps the audit-status mapper honest."""

    def test_audit_status(self):
        from waybill.collectors import hindsight as hs
        self.assertEqual(hs.audit_status({"response": {"status": "completed"}}), ("ok", None))
        self.assertEqual(hs.audit_status({"response": {"success": True}}), ("ok", "accepted"))
        self.assertEqual(hs.audit_status({"response": {"status": "failed"}})[0], "failed")
        self.assertEqual(hs.audit_status({"response": {"status": "processing"}})[0], "pending")


if __name__ == "__main__":
    unittest.main()
