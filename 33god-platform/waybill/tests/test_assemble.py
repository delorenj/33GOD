"""Assembler tests on a small synthetic turn (no live systems)."""
from __future__ import annotations

import copy
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waybill import model as M  # noqa: E402
from waybill.assemble import apply_profile, assemble, llm_tokens, merge_span, waybill_id  # noqa: E402

T = 1794801638000.0
SID = "956a26e9-3f7f-4226-9491-8590d87cc90e"
UPS, PRE, POST, STOP = ("inv-ups-0001", "inv-pre-0002", "inv-post-0003", "inv-stop-0004")
EVT_TS, EVT_TREQ, EVT_TDONE, EVT_TC, EVT_LOST = (
    "e1000000-0000-4000-8000-000000000001", "e2000000-0000-4000-8000-000000000002",
    "e3000000-0000-4000-8000-000000000003", "e4000000-0000-4000-8000-000000000004",
    "e5000000-0000-4000-8000-000000000005")
TOOL = "toolu_01ABCDEF"
ZERO_TP = "00-00000000000000000000000000000000-0000000000000000-00"


def window(**kw) -> M.TurnWindow:
    d = dict(cli="claude", surface="claude-code-headless", session_id=SID, t0=T, t_end=T + 19000,
             turn_end=T + 4000, turn_id=f"{SID}:turn:1", turn_index=1,
             prompt_text="Reply with the single word: pong", cwd="/tmp",
             prompt_invocation_id=UPS, stop_invocation_id=STOP, settle_ms=15000.0)
    d.update(kw)
    return M.TurnWindow(**d)


def _src(sid: str, items: int = 1) -> M.Source:
    return M.Source(id=sid, kind="test", locator=f"test:{sid}", status="ok", items=items, ms=1.0)


def hook(inv: str, native: str, t0: float, t1: float, sync: bool = True) -> M.Span:
    return M.Span(id=M.Ids.hook(inv), kind="hook", component="hook-hub", name=native,
                  summary=f"{native} invocation", phase="prompt_submit", t0=t0, t1=t1, sync=sync,
                  refs={"invocation_id": inv}, attrs={"native": native}, evidence=["hookhub"])


def handler(inv: str, hid: str, t0: float, t1: float, status: str = "ok", reason: str | None = None,
            sync: bool = True, event_id: str | None = None, event_type: str | None = None) -> M.Span:
    refs = {"invocation_id": inv, "handler_id": hid}
    attrs = {"handler_id": hid, "mode": "sync" if sync else "async"}
    if event_id:
        refs["event_id"] = event_id
        refs["event_type"] = event_type
        attrs["publish_status"] = "sent"
    return M.Span(id=M.Ids.handler(inv, hid), kind="handler", component="hook-hub", name=hid,
                  summary=f"{hid} {status}", phase="prompt_submit", t0=t0, t1=t1, status=status,
                  reason=reason, sync=sync, refs=refs, attrs=attrs, evidence=["hookhub"])


def synthetic() -> list:
    hh = M.Fragment(source=_src("hookhub", 14))
    hh.spans += [
        hook(UPS, "UserPromptSubmit", T + 20, T + 900),
        handler(UPS, "skill-reminder", T + 30, T + 80),
        handler(UPS, "crank-tag", T + 80, T + 85, "skipped", "not_a_crank_prompt"),
        handler(UPS, "hindsight-recall", T + 85, T + 400),
        handler(UPS, "codegraph-prompt", T + 400, T + 402, "skipped", "handler_binary_missing"),
        handler(UPS, "claude-notify", T + 402, T + 410, "failed", "handler_binary_missing"),
        handler(UPS, "bloodbank-publisher", T + 25, T + 70, sync=False, event_id=EVT_TS,
                event_type="bloodbank.conversation.turn.started"),
        hook(PRE, "PreToolUse", T + 2005, T + 2050),
        handler(PRE, "bloodbank-publisher", T + 2006, T + 2040, sync=False, event_id=EVT_TREQ,
                event_type="bloodbank.agent.tool.requested"),
        hook(POST, "PostToolUse", T + 2510, T + 2560),
        handler(POST, "bloodbank-publisher", T + 2511, T + 2540, sync=False, event_id=EVT_TDONE,
                event_type="bloodbank.agent.tool.completed"),
        hook(STOP, "Stop", T + 3900, T + 4100),
        handler(STOP, "bloodbank-publisher", T + 3901, T + 3950, sync=False, event_id=EVT_TC,
                event_type="bloodbank.conversation.turn.completed"),
        handler(STOP, "hindsight-turn", T + 3901, T + 3990, sync=False, event_id=EVT_LOST,
                event_type="bloodbank.memory.turn.buffered"),
    ]

    tr = M.Fragment(source=_src("transcript_claude", 6))
    tr.component("ext:claude-code", "Claude Code", "cli")
    tr.spans += [
        M.Span(id="prompt", kind="prompt", component="ext:claude-code", name="prompt",
               summary="Operator typed a prompt.", phase="prompt_submit", t0=T, t1=T + 910, sync=True,
               payload=tr.artifact("Reply with the single word: pong"), evidence=["transcript_claude"]),
        M.Span(id=M.Ids.context(UPS), kind="context", component="hook-hub", name="additionalContext",
               summary="6998 chars of context went back to the model.", phase="prompt_submit",
               t0=T + 905, t1=None, payload=tr.artifact("x" * 1000 + " see /home/x/notes"),
               evidence=["transcript_claude"]),
        M.Span(id=M.Ids.llm(1), kind="llm", component="aai-gateway", name="claude-opus", summary="first call",
               phase="model_call", t0=T + 950, t1=T + 2000, sync=True,
               attrs={"usage": {"input_tokens": 3, "cache_read_input_tokens": 40000,
                                "cache_creation_input_tokens": 1000, "output_tokens": 50},
                      "env": {"ANTHROPIC_BASE_URL": "http://x"}},
               evidence=["transcript_claude"]),
        M.Span(id=M.Ids.tool(TOOL), kind="tool", component="ext:claude-code", name="Bash",
               summary="Bash ran `ls`. key sk-ant-abcdefghijklmnopqrstuvwxyz0123456789", phase="tool",
               t0=T + 2010, t1=T + 2500, sync=True, refs={"tool_use_id": TOOL}, evidence=["transcript_claude"]),
        M.Span(id=M.Ids.llm(2), kind="llm", component="aai-gateway", name="claude-opus", summary="second call",
               phase="model_call", t0=T + 2600, t1=T + 3800, sync=True,
               attrs={"usage": {"input_tokens": 5, "cache_read_input_tokens": 41000, "output_tokens": 20}},
               evidence=["transcript_claude"]),
    ]
    tr.links.append(M.Link(from_=M.Ids.tool(TOOL), to="file:nope", kind="writes"))
    tr.facts.update({"model_requested": "automaticai/auto/orchestrator", "model_served": "claude-opus-5.5"})

    def env(eid: str, etype: str, t: float, data: dict) -> dict:
        return {"id": eid, "type": etype, "time": M.iso(t), "correlationid": SID, "causationid": None,
                "traceparent": ZERO_TP, "data": data}

    cs = M.Fragment(source=_src("candystore", 4))
    for eid, et, t, data, archived in [
        (EVT_TS, "bloodbank.conversation.turn.started", T + 60, {"prompt_text": "Reply with the single word: pong"}, T + 70),
        (EVT_TREQ, "bloodbank.agent.tool.requested", T + 2030, {"tool_call_id": TOOL}, T + 2041),
        (EVT_TDONE, "bloodbank.agent.tool.completed", T + 2530, {"tool_call_id": TOOL}, None),
        (EVT_TC, "bloodbank.conversation.turn.completed", T + 3940, {}, T + 3950),
    ]:
        ev = M.BusEvent(id=eid, type=et, t=t, subject="bloodbank.evt." + et[len("bloodbank."):],
                        stream="BLOODBANK_EVENTS", archived=archived, correlationid=SID,
                        payload=cs.artifact(env(eid, et, t, data)))
        if archived:
            ev.consumers.append(M.Consumer(name="candystore-events", component="candystore", kind="durable",
                                           outcome="archived", t=archived, evidence="observed"))
        cs.events.append(ev)

    ho = M.Fragment(source=_src("holocene", 4))
    for n, eid in enumerate([EVT_TS, EVT_TREQ, EVT_TDONE, EVT_TC]):
        ho.events.append(M.BusEvent(id=eid, type="", t=T, seq=10430844 + n, stored=T + 62 + n,
                                    consumers=[M.Consumer(name="holocene", component="holocene", kind="ephemeral",
                                                          outcome="collected", t=T + 63 + n, evidence="observed")]))

    na = M.Fragment(source=_src("nats", 5))
    na.facts["consumers"] = [
        {"name": "candystore-events", "stream": "BLOODBANK_EVENTS", "filter_subjects": ["bloodbank.evt.>"],
         "kind": "durable", "component": "candystore"},
        {"name": "enricher-events", "stream": "BLOODBANK_EVENTS", "filter_subjects": ["bloodbank.evt.agent.tool.>"],
         "kind": "durable"},
        {"name": "holocene_Xy12", "stream": "BLOODBANK_EVENTS", "filter_subjects": [], "kind": "ephemeral"},
    ]
    na.facts["core_subs"] = [
        {"client": "ntfy-router", "subject": "bloodbank.evt.>", "component": "ntfy-router"},
        {"client": "deckard", "subject": "bloodbank.evt.conversation.turn.>", "component": "deckard"},
    ]

    gw = M.Fragment(source=_src("gateway", 2))
    gw.spans += [
        M.Span(id="llm:gw:req1", kind="llm", component="aai-gateway", name="usage", summary="gateway row",
               phase="model_call", t0=T + 1000, t1=T + 2100, refs={"request_id": "req1"},
               attrs={"route": "claude-opus-5.5",
                      "_match_llm": {"input_tokens": 41003, "output_tokens": 50, "near": T + 2100}},
               evidence=["gateway"]),
        M.Span(id="llm:gw:req9", kind="llm", component="aai-gateway", name="ai-title", summary="background call",
               phase="model_call", t0=T + 1500, t1=T + 1600, refs={"request_id": "req9"},
               attrs={"usage": {"input_tokens": 7, "output_tokens": 7},
                      "_match_llm": {"input_tokens": 7, "output_tokens": 7, "near": T + 1600}},
               evidence=["gateway"]),
    ]

    lg = M.Fragment(source=_src("logs", 2))
    lg.spans += [
        M.Span(id=f"consume:ntfy-router:at:{int(T + 150)}", kind="consume", component="ntfy-router",
               name="routed", summary="ntfy-router routed turn.started", phase="async_after", t0=T + 150,
               attrs={"_join": {"event_type": "conversation.turn.started", "near": T + 150,
                                "consumer": "ntfy-router", "consumer_kind": "core", "outcome": "routed"}},
               evidence=["logs"]),
        M.Span(id=f"consume:ntfy-router:at:{int(T + 9000)}", kind="consume", component="ntfy-router",
               name="rate-limited", summary="ntfy-router rate-limited session.ended", phase="async_after",
               t0=T + 9000, attrs={"_join": {"event_type": "agent.session.ended", "near": T + 9000,
                                             "consumer": "ntfy-router", "outcome": "rate-limited"}},
               evidence=["logs"]),
    ]

    class Broken:  # a collector that returned junk must not sink the waybill
        source = _src("broken")
        spans = [object()]
        events = None
        links = None

    return [hh, tr, cs, ho, na, gw, lg, Broken()]


def build(profile: str = "full", **wkw) -> dict:
    return assemble(window(**wkw), synthetic(), profile=profile, mode="capture", argv=["waybill", "capture"])


def spans_by_id(wb: dict) -> dict:
    return {s["id"]: s for s in wb["spans"]}


def links_set(wb: dict) -> set:
    return {(ln["from"], ln["to"], ln["kind"]) for ln in wb["links"]}


class TestAssemble(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.wb = build()
        cls.S = spans_by_id(cls.wb)
        cls.E = {e["id"]: e for e in cls.wb["events"]}
        cls.L = links_set(cls.wb)

    def test_identity(self) -> None:
        wb = self.wb
        self.assertEqual(wb["format"], "33god.waybill")
        self.assertEqual(wb["version"], 1)
        self.assertTrue(wb["id"].startswith("wb_"))
        self.assertEqual(len(wb["id"]), 29)
        self.assertEqual(wb["id"], build()["id"], "id must be deterministic")
        self.assertLess(waybill_id(T, SID, "1"), waybill_id(T + 1000, SID, "1"), "id must sort by time")
        self.assertEqual(wb["recorder"]["mode"], "capture")
        self.assertEqual(wb["title"], 'claude-code-headless · "Reply with the single word: pong" · 4.0 s')

    def test_times_rebased_and_sorted(self) -> None:
        self.assertEqual(self.S["prompt"]["t0"], 0.0)
        self.assertEqual(self.S[M.Ids.hook(UPS)]["t0"], 20.0)
        t0s = [(s["t0"], s["id"]) for s in self.wb["spans"]]
        self.assertEqual(t0s, sorted(t0s))
        ts = [e["t"] for e in self.wb["events"]]
        self.assertEqual(ts, sorted(ts))
        self.assertEqual(self.E[EVT_TS]["archived"], 70.0)
        self.assertEqual(self.E[EVT_TS]["stored"], 62.0)
        self.assertEqual(self.wb["clock"]["duration_ms"], 4000.0)

    def test_event_merge(self) -> None:
        ev = self.E[EVT_TS]
        self.assertEqual(ev["type"], "bloodbank.conversation.turn.started", "empty type must not blank out")
        self.assertEqual(ev["seq"], 10430844)
        self.assertEqual(ev["publisher_span"], M.Ids.publish(EVT_TS))

    def test_match_llm(self) -> None:
        self.assertNotIn("llm:gw:req1", self.S)
        self.assertEqual(self.S["llm:1"]["refs"]["request_id"], "req1")
        self.assertEqual(self.S["llm:1"]["attrs"]["route"], "claude-opus-5.5")
        self.assertIn("gateway", self.S["llm:1"]["evidence"])
        self.assertIn("transcript_claude", self.S["llm:1"]["evidence"])
        self.assertIn("llm:gw:req9", self.S, "an unmatched usage row stays its own llm span")
        self.assertNotIn("_match_llm", self.S["llm:gw:req9"]["attrs"])

    def test_join_hint(self) -> None:
        cid = M.Ids.consume("ntfy-router", EVT_TS)
        self.assertIn(cid, self.S)
        self.assertNotIn("_join", self.S[cid]["attrs"])
        cons = {c["name"]: c for c in self.E[EVT_TS]["consumers"]}
        self.assertEqual(cons["ntfy-router"]["evidence"], "observed")
        self.assertEqual(cons["ntfy-router"]["outcome"], "routed")
        self.assertEqual(cons["ntfy-router"]["span"], cid)
        self.assertIn((M.Ids.evt(EVT_TS), cid, "delivers"), self.L)
        self.assertTrue(any("could not be tied" in g["what"] for g in self.wb["gaps"]))

    def test_inferred_consumers(self) -> None:
        ts = {c["name"]: c for c in self.E[EVT_TS]["consumers"]}
        self.assertEqual(ts["deckard"]["evidence"], "inferred")
        self.assertEqual(ts["candystore-events"]["evidence"], "observed")
        self.assertNotIn("enricher-events", ts, "enricher filter is agent.tool.>")
        self.assertNotIn("holocene_Xy12", ts, "observed holocene absorbs the inferred ephemeral consumer")
        req = {c["name"]: c for c in self.E[EVT_TREQ]["consumers"]}
        self.assertEqual(req["enricher-events"]["evidence"], "inferred")
        self.assertEqual(req["enricher-events"]["filter"], "bloodbank.evt.agent.tool.>")
        self.assertNotIn("deckard", req)

    def test_publish_chain(self) -> None:
        pid = M.Ids.publish(EVT_TS)
        self.assertEqual(self.S[pid]["component"], "agent-hooks")
        self.assertIn((M.Ids.handler(UPS, "bloodbank-publisher"), pid, "calls"), self.L)
        self.assertIn((pid, M.Ids.evt(EVT_TS), "publishes"), self.L)
        lost = self.E[EVT_LOST]
        self.assertFalse(lost["observed_on_bus"])
        self.assertEqual(lost["subject"], "bloodbank.evt.memory.turn.buffered")
        self.assertTrue(all(c["kind"] == "core" for c in lost["consumers"]))
        self.assertTrue(any("never seen stored" in g["what"] and EVT_LOST in g["what"] for g in self.wb["gaps"]))
        self.assertTrue(any("no observed archive" in g["what"] and EVT_TDONE in g["what"] for g in self.wb["gaps"]))

    def test_tool_hooks_and_chain(self) -> None:
        tid = M.Ids.tool(TOOL)
        self.assertEqual(self.S[M.Ids.hook(PRE)]["parent"], tid)
        self.assertEqual(self.S[M.Ids.hook(POST)]["parent"], tid)
        self.assertEqual(self.S[M.Ids.hook(PRE)]["refs"]["tool_use_id"], TOOL)
        self.assertEqual(self.S[tid]["parent"], "llm:1")
        self.assertIn(("llm:1", M.Ids.hook(PRE), "triggers"), self.L)
        self.assertIn((M.Ids.hook(PRE), tid, "triggers"), self.L)
        self.assertIn((tid, M.Ids.hook(POST), "triggers"), self.L)
        self.assertIn((tid, "llm:2", "feeds"), self.L)

    def test_prompt_context_links(self) -> None:
        self.assertIn(("prompt", M.Ids.hook(UPS), "calls"), self.L)
        self.assertIn((M.Ids.context(UPS), "llm:1", "feeds"), self.L)
        self.assertEqual(self.S[M.Ids.context(UPS)]["parent"], M.Ids.hook(UPS))
        self.assertEqual(self.S[M.Ids.handler(UPS, "crank-tag")]["parent"], M.Ids.hook(UPS))
        self.assertEqual(self.S[M.Ids.hook(UPS)]["parent"], "prompt")

    def test_dangling_links_dropped(self) -> None:
        self.assertFalse(any(ln["to"] == "file:nope" for ln in self.wb["links"]))
        self.assertTrue(any("file:nope" in g["what"] for g in self.wb["gaps"]))
        nodes = {s["id"] for s in self.wb["spans"]} | {"evt:" + e["id"] for e in self.wb["events"]}
        for ln in self.wb["links"]:
            self.assertIn(ln["from"], nodes)
            self.assertIn(ln["to"], nodes)

    def test_findings(self) -> None:
        titles = [f["title"] for f in self.wb["findings"]]
        self.assertTrue(any(t.startswith("no distributed trace id") for t in titles))
        self.assertIn("claude-notify failed: handler_binary_missing", titles)
        f = next(f for f in self.wb["findings"] if f["title"].startswith("claude-notify"))
        self.assertEqual(f["severity"], "broken")

    def test_stats(self) -> None:
        st = self.wb["stats"]
        self.assertEqual(st["tools"], 1)
        self.assertEqual(st["llm_calls"], 3)
        self.assertEqual(st["tokens_in"], 41003 + 41005 + 7)
        self.assertEqual(st["tokens_out"], 77)
        self.assertEqual(st["sync_wait_ms"], 880.0)
        self.assertEqual(st["handlers_skipped"], 2)
        self.assertEqual(st["handlers_failed"], 1)
        self.assertGreater(st["consumers_inferred"], 0)
        self.assertGreater(st["consumers_observed"], 0)
        self.assertEqual(st["spans_hook"], 4)

    def test_components(self) -> None:
        comps = self.wb["components"]
        self.assertEqual(comps["ext:claude-code"]["kind"], "cli")
        self.assertFalse(comps["ext:claude-code"]["registry"])
        self.assertIn("deckard", comps)
        self.assertEqual(comps["hook-hub"]["kind"], "handler-host")
        self.assertTrue(comps["hook-hub"]["registry"])

    def test_scrub_and_failsoft(self) -> None:
        txt = json.dumps(self.wb)
        self.assertNotIn("sk-ant-abcdefghijklmnopqrstuvwxyz", txt)
        self.assertIn(M.REDACTED, self.S[M.Ids.tool(TOOL)]["summary"])
        self.assertIn("broken", [s["id"] for s in self.wb["sources"]])

    def test_origin(self) -> None:
        o = self.wb["origin"]
        self.assertEqual(o["turn_id"], f"{SID}:turn:1")
        self.assertEqual(o["model"], {"requested": "automaticai/auto/orchestrator", "served": "claude-opus-5.5"})
        self.assertEqual(self.wb["prompt"]["chars"], len("Reply with the single word: pong"))
        self.assertEqual(self.wb["prompt"]["sha256"], M.sha256("Reply with the single word: pong"))


class TestProfilesAndEdges(unittest.TestCase):
    def test_public_profile(self) -> None:
        wb = build(profile="public")
        self.assertEqual(wb["recorder"]["profile"], "public")
        self.assertEqual(wb["prompt"]["text"], "Reply with the single word: pong")
        ctx = spans_by_id(wb)[M.Ids.context(UPS)]
        art = wb["artifacts"][ctx["payload"]]
        self.assertTrue(art["truncated"])
        self.assertLessEqual(len(art["text"]), 281)
        self.assertEqual(spans_by_id(wb)["llm:1"]["attrs"]["env"], {"ANTHROPIC_BASE_URL": "«dropped»"})
        self.assertNotIn(os.path.expanduser("~") + "/", json.dumps(wb))

    def test_public_is_idempotent(self) -> None:
        wb = build(profile="public")
        again = apply_profile(copy.deepcopy(wb), "public")
        self.assertEqual(wb, again)

    def test_turn_open(self) -> None:
        frags = [f for f in synthetic() if getattr(getattr(f, "source", None), "id", "") != "hookhub"]
        wb = assemble(window(turn_end=None, stop_invocation_id=None), frags, "full", "record", None)
        self.assertTrue(any(g["what"] == "turn still open" and g["severity"] == "warn" for g in wb["gaps"]))
        self.assertEqual(spans_by_id(wb)["turn"]["status"], "pending")

    def test_empty_fragments(self) -> None:
        wb = assemble(window(), [], "full", "capture", None)
        self.assertEqual({s["id"] for s in wb["spans"]}, {"prompt", "turn"})
        self.assertEqual(wb["events"], [])

    def test_merge_span_rules(self) -> None:
        a = {"id": "x", "kind": "hook", "name": "A", "status": "ok", "t0": 1.0, "evidence": ["s1"],
             "refs": {"a": 1}, "attrs": {}}
        merge_span(a, {"id": "x", "kind": "tool", "name": "", "status": "failed", "reason": "boom", "t0": 9.0,
                       "t1": 5.0, "evidence": ["s2", "s1"], "refs": {"b": 2, "a": 3}, "attrs": {"k": "v"}})
        self.assertEqual(a["kind"], "hook")
        self.assertEqual(a["name"], "A")
        self.assertEqual(a["status"], "failed")
        self.assertEqual(a["reason"], "boom")
        self.assertEqual(a["t0"], 1.0)
        self.assertEqual(a["t1"], 5.0)
        self.assertEqual(a["evidence"], ["s1", "s2"])
        self.assertEqual(a["refs"], {"a": 1, "b": 2})
        merge_span(a, {"id": "x", "status": "ok"})
        self.assertEqual(a["status"], "failed", "a default 'ok' must not hide a failure")

    def test_llm_tokens(self) -> None:
        self.assertEqual(llm_tokens({"attrs": {"tokens_in": 10, "tokens_out": 2}}), (10, 10, 2))
        self.assertEqual(llm_tokens({"attrs": {"usage": {"input_tokens": 1, "cache_read_input_tokens": 9,
                                                         "output_tokens": 3}}}), (10, 1, 3))
        self.assertEqual(llm_tokens({"attrs": {}}), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
