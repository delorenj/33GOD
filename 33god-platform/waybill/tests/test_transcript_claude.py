"""Tests for waybill.collectors.transcript_claude."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from waybill import window as W
from waybill.collectors import transcript_claude as T
from waybill.model import Ctx, Ids, iso, ms
from test_window import (CSID, Env, claude_assistant, claude_turn_entries, claude_user, standard_receipts, write_jsonl, UPS_CONTEXT)


class SplitContext(unittest.TestCase):
    def test_reminder_and_recall(self):
        segs = T.split_context(UPS_CONTEXT)
        self.assertEqual([s["handler"] for s in segs], ["skill-reminder", "hindsight-recall"])
        self.assertTrue(segs[0]["text"].startswith("⚡ REMINDER"))
        self.assertNotIn("hindsight:recall", segs[0]["text"])
        self.assertEqual(segs[1]["banks"], ["proj"])
        self.assertTrue(segs[1]["text"].endswith("<!-- /hindsight:recall -->"))

    def test_one_block_per_bank_merges(self):
        text = ("<!-- hindsight:recall bank=a -->\nA\n<!-- /hindsight:recall -->\n\n"
                "<!-- hindsight:recall bank=b -->\nB\n<!-- /hindsight:recall -->")
        segs = T.split_context(text)
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["banks"], ["a", "b"])
        self.assertIn("A", segs[0]["text"])
        self.assertIn("B", segs[0]["text"])

    def test_marker_quoted_inside_a_block_is_not_split(self):
        text = ("<!-- hindsight:recall bank=a -->\nthe memory says: ⚡ REMINDER is injected by a handler\n<!-- /hindsight:recall -->")
        segs = T.split_context(text)
        self.assertEqual([s["handler"] for s in segs], ["hindsight-recall"])

    def test_crank_and_codegraph_and_unknown(self):
        text = ("Some native leading text\n\nThis prompt was typed by Crank, the operator's automated stand-in. Be careful.\n\n"
                "<codegraph_context>\nFound 3 symbols across 2 files\n</codegraph_context>\ntrailing words")
        segs = {s["handler"]: s for s in T.split_context(text)}
        self.assertEqual(list(segs), ["unknown", "crank-tag", "codegraph-prompt"])
        self.assertIn("leading", segs["unknown"]["text"])
        self.assertIn("trailing", segs["unknown"]["text"])
        self.assertTrue(segs["crank-tag"]["text"].startswith("This prompt was typed by Crank"))
        self.assertNotIn("codegraph", segs["crank-tag"]["text"])

    def test_session_start_handlers(self):
        text = ("<!-- hindsight:briefing bank=x -->\nbrief\n<!-- /hindsight:briefing -->\n\n"
                "CandyStore recent context — proj\nWindow: a to b\n\nNodes: 12\nEdges: 40\nFiles: 3\nrest")
        self.assertEqual([s["handler"] for s in T.split_context(text)],
                         ["hindsight-briefing", "candystore-context", "code-review-graph-status"])

    def test_aai_marker_is_a_single_line(self):
        text = "AutomaticAI prompt proof marker: AAI_ROUTE_PROOF_c28b59f264c5b905977dbe6c65edbdd4. Keep it.\n\n<!-- hindsight:briefing bank=x -->\nb\n<!-- /hindsight:briefing -->"
        segs = T.split_context(text)
        self.assertEqual([s["handler"] for s in segs], ["automaticai-routing-start", "hindsight-briefing"])

    def test_empty_and_unmarked(self):
        self.assertEqual(T.split_context(""), [])
        self.assertEqual(T.split_context("   \n"), [])
        self.assertEqual([s["handler"] for s in T.split_context("just text")], ["unknown"])

    def test_persisted_output_reads_full_file(self):
        with tempfile.TemporaryDirectory() as d:
            full = Path(d) / "hook-x-additionalContext.txt"
            full.write_text("⚡ REMINDER full text\n\n<!-- hindsight:recall bank=a -->\nfull\n<!-- /hindsight:recall -->")
            preview = f"<persisted-output>\nOutput too large (16.7KB). Full output saved to: {full}\n\nPreview (first 2KB):\n⚡ REMINDER ..."
            text, info = T.resolve_persisted(preview)
            self.assertTrue(info["persisted"])
            self.assertEqual(info["model_saw_chars"], len(preview))
            self.assertEqual(info["persisted_chars"], len(text))
            self.assertIn("full\n", text)
            text2, info2 = T.resolve_persisted(preview.replace(str(full), "/nonexistent/file.txt"))
            self.assertTrue(info2["persisted"])
            self.assertTrue(text2.startswith("<persisted-output>"))
            self.assertEqual(T.resolve_persisted("plain")[1], {})


class Formatting(unittest.TestCase):
    def test_tokens_and_durations(self):
        self.assertEqual(T.fmt_tokens(312), "312")
        self.assertEqual(T.fmt_tokens(41700), "41.7k")
        self.assertEqual(T.fmt_tokens(39000), "39k")
        self.assertEqual(T.fmt_tokens(166000), "166k")
        self.assertEqual(T.fmt_dur(905), "905 ms")
        self.assertEqual(T.fmt_dur(4100), "4.1 s")


class CollectBase(unittest.TestCase):
    def setUp(self):
        self.env = Env().__enter__()
        standard_receipts(self.env.receipts)
        self.path = self.env.claude_file(claude_turn_entries())

    def tearDown(self):
        self.env.__exit__()

    def collect(self, profile="full", turn=1):
        w = W.resolve(CSID, turn=turn)
        return T.collect(Ctx(window=w, profile=profile))

    def span(self, frag, sid):
        return next(s for s in frag.spans if s.id == sid)


class CollectClaude(CollectBase):
    def test_spans_present_and_sliced(self):
        f = self.collect()
        self.assertEqual(f.source.status, "ok")
        ids = [s.id for s in f.spans]
        for want in ("prompt", "turn", "llm:1", "llm:2", "tool:toolu_A", "context:inv-p1",
                     "context:inv-p1:skill-reminder", "context:inv-p1:hindsight-recall"):
            self.assertIn(want, ids)
        self.assertNotIn("llm:3", ids)                       # turn 2 is outside the slice
        self.assertEqual(sum(1 for s in f.spans if s.kind == "llm"), 2)

    def test_prompt_span(self):
        f = self.collect()
        p = self.span(f, "prompt")
        self.assertEqual(p.component, "ext:claude-code")
        self.assertEqual(iso(p.t0), "2026-11-16T03:00:00.000Z")
        self.assertEqual(p.attrs["promptId"], "p1")
        self.assertEqual(p.attrs["turnIndex"], 1)
        self.assertEqual(p.attrs["entrypoint"], "cli")
        self.assertEqual(f.artifacts[p.payload]["text"], "do the thing")

    def test_llm_usage_deduped_and_gateway_comparable(self):
        f = self.collect()
        l1 = self.span(f, "llm:1")
        # req-1 has two assistant entries with identical usage: counted once
        self.assertEqual(l1.attrs["usage"]["output_tokens"], 50)
        self.assertEqual(l1.attrs["usage"]["cache_creation_input_tokens"], 1000)
        self.assertEqual(l1.attrs["tokens_in"], 1002)
        self.assertEqual(l1.attrs["input_tokens"], 1002)
        self.assertEqual(l1.attrs["output_tokens"], 50)
        self.assertEqual(l1.refs["client_request"], "req-1")
        self.assertEqual(l1.attrs["requested_model"], "automaticai/auto/orchestrator")
        self.assertEqual(l1.attrs["served_model"], "claude-opus-5-5")
        self.assertEqual(l1.attrs["effort"], "high")
        self.assertEqual(l1.component, "aai-gateway")
        self.assertTrue(l1.sync)
        self.assertEqual(iso(l1.t0), "2026-11-16T03:00:01.000Z")      # the api-request entry
        self.assertEqual(iso(l1.t1), "2026-11-16T03:00:04.000Z")      # the last assistant entry
        l2 = self.span(f, "llm:2")
        self.assertEqual(l2.attrs["tokens_in"], 3 + 1000 + 20)
        self.assertIn("(1k cached)", l2.summary)
        self.assertIn("-> claude-opus-5-5", l2.summary)

    def test_tool_span(self):
        f = self.collect()
        t = self.span(f, "tool:toolu_A")
        self.assertEqual(t.kind, "tool")
        self.assertEqual(t.name, "Bash")
        self.assertEqual(t.status, "ok")
        self.assertTrue(t.sync)
        self.assertEqual(iso(t.t0), "2026-11-16T03:00:04.000Z")
        self.assertEqual(iso(t.t1), "2026-11-16T03:00:05.000Z")
        self.assertEqual(f.artifacts[t.payload]["text"], "file1\nfile2")
        self.assertIn("ls -la", f.artifacts[t.attrs["input_artifact"]]["text"])
        self.assertEqual(t.attrs["hooks"][0]["duration_ms"], 12)

    def test_tool_error_is_failed(self):
        entries = claude_turn_entries()
        for e in entries:
            if isinstance(e, dict) and e.get("type") == "user" and e.get("uuid") == "u-res-A":
                e["message"]["content"][0]["is_error"] = True
                e["message"]["content"][0]["content"] = "boom: permission denied"
        self.env.claude_file(entries)
        t = self.span(self.collect(), "tool:toolu_A")
        self.assertEqual(t.status, "failed")
        self.assertIn("permission denied", t.reason)

    def test_unfinished_tool_is_pending(self):
        entries = [e for e in claude_turn_entries() if not (isinstance(e, dict) and e.get("uuid") == "u-res-A")]
        self.env.claude_file(entries)
        t = self.span(self.collect(), "tool:toolu_A")
        self.assertEqual(t.status, "pending")
        self.assertIsNone(t.t1)

    def test_links(self):
        f = self.collect()
        got = {(l.from_, l.to, l.kind) for l in f.links}
        self.assertIn(("prompt", "llm:1", "feeds"), got)
        self.assertIn(("llm:1", "tool:toolu_A", "calls"), got)
        self.assertIn(("tool:toolu_A", "llm:2", "feeds"), got)
        self.assertIn((Ids.handler("inv-p1", "skill-reminder"), "context:inv-p1:skill-reminder", "injects"), got)
        self.assertIn((Ids.handler("inv-p1", "hindsight-recall"), "context:inv-p1:hindsight-recall", "injects"), got)
        self.assertEqual(len(got), len(f.links))                       # no duplicates

    def test_context_spans(self):
        f = self.collect()
        merged = self.span(f, "context:inv-p1")
        self.assertEqual(merged.component, "hook-hub")
        self.assertEqual(merged.kind, "context")
        self.assertEqual(merged.phase, "prompt_submit")
        self.assertEqual(merged.parent, "hook:inv-p1")
        self.assertEqual(merged.attrs["handlers"], ["skill-reminder", "hindsight-recall"])
        self.assertEqual(iso(merged.t0), "2026-11-16T03:00:00.900Z")
        split = self.span(f, "context:inv-p1:hindsight-recall")
        self.assertEqual(split.attrs["banks"], ["proj"])
        self.assertIn("Memory one", f.artifacts[split.payload]["text"])
        self.assertNotIn("REMINDER", f.artifacts[split.payload]["text"])

    def test_turn_span_and_facts(self):
        f = self.collect()
        t = self.span(f, "turn")
        self.assertEqual(t.attrs["duration_ms"], 20000)
        self.assertEqual(t.attrs["llm_calls"], 2)
        self.assertEqual(t.attrs["tool_calls"], 1)
        self.assertEqual(iso(t.t1), "2026-11-16T03:00:20.050Z")
        self.assertEqual(f.facts["turn_index"], 1)
        self.assertEqual(f.facts["turn_id"], f"{CSID}:turn:1")
        self.assertEqual(f.facts["model_requested"], "automaticai/auto/orchestrator")
        self.assertEqual(f.facts["model_served"], "claude-opus-5-5")
        self.assertEqual(f.facts["surface"], "claude-code")
        self.assertEqual(f.facts["project"], "proj")

    def test_second_turn(self):
        f = self.collect(turn=2)
        self.assertEqual(sum(1 for s in f.spans if s.kind == "llm"), 1)
        self.assertEqual(self.span(f, "prompt").attrs["promptId"], "p2")
        self.assertEqual(f.facts["turn_index"], 2)

    def test_public_profile_cuts_payloads(self):
        entries = claude_turn_entries()
        for e in entries:
            if isinstance(e, dict) and e.get("uuid") == "u-res-A":
                e["message"]["content"][0]["content"] = "line\n" * 500
        self.env.claude_file(entries)
        f = self.collect(profile="public")
        t = self.span(f, "tool:toolu_A")
        art = f.artifacts[t.payload]
        self.assertEqual(len(art["text"]), 280)
        self.assertTrue(art["truncated"])
        full = self.collect(profile="full")
        self.assertGreater(len(full.artifacts[self.span(full, "tool:toolu_A").payload]["text"]), 280)

    def test_secrets_are_scrubbed(self):
        entries = claude_turn_entries()
        for e in entries:
            if isinstance(e, dict) and e.get("uuid") == "u-res-A":
                e["message"]["content"][0]["content"] = "token=sk-or-v1-abcdefghijklmnopqrstuvwxyz0123456789 end"
        self.env.claude_file(entries)
        f = self.collect()
        text = f.artifacts[self.span(f, "tool:toolu_A").payload]["text"]
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz0123456789", text)
        self.assertIn("«redacted»", text)

    def test_api_error_call_failed_with_request_id(self):
        entries = claude_turn_entries()
        idx = next(i for i, e in enumerate(entries) if isinstance(e, dict) and e.get("id") == "req-2")
        entries[idx + 1] = claude_assistant("2026-11-16T03:00:06.000Z", "req-2", "msg-err",
                                            [{"type": "text", "text": "API Error: 529 overloaded (request id: GWRID123abc)"}],
                                            {}, model="<synthetic>", isApiErrorMessage=True, apiErrorStatus=529)
        self.env.claude_file(entries)
        l2 = self.span(self.collect(), "llm:2")
        self.assertEqual(l2.status, "failed")
        self.assertIn("529", l2.reason)
        self.assertEqual(l2.refs["request_id"], "GWRID123abc")

    def test_api_error_system_entry_records_retry(self):
        entries = claude_turn_entries()
        idx = next(i for i, e in enumerate(entries) if isinstance(e, dict) and e.get("id") == "req-2")
        entries.insert(idx + 1, {"type": "system", "subtype": "api_error", "timestamp": "2026-11-16T03:00:05.500Z", "isSidechain": False,
                                 "error": {"status": 529, "formatted": "overloaded (request id: RID777)"}, "retryAttempt": 1, "retryInMs": 500})
        entries.pop(idx + 2)         # req-2's assistant answer never arrived
        self.env.claude_file(entries)
        l2 = self.span(self.collect(), "llm:2")
        self.assertEqual(l2.attrs["retries"][0]["request_id"], "RID777")
        self.assertEqual(l2.status, "failed")

    def test_subagent_sidechains_counted_not_expanded(self):
        sub = self.path.with_suffix("") / "subagents" / "workflows" / "wf_1"
        write_jsonl(sub / "agent-abc.jsonl", [{"type": "user", "isSidechain": True, "promptId": "p1", "timestamp": "2026-11-16T03:00:06.000Z",
                                                "message": {"role": "user", "content": "go"}}])
        (sub / "agent-abc.meta.json").write_text(json.dumps({"agentType": "workflow-subagent", "description": "map:thing"}))
        write_jsonl(sub / "agent-other.jsonl", [{"type": "user", "isSidechain": True, "promptId": "OTHER", "timestamp": "2026-11-16T03:00:06.000Z",
                                                  "message": {"role": "user", "content": "go"}}])
        f = self.collect()
        self.assertEqual(self.span(f, "turn").attrs["subagents"], 1)
        gap = next(g for g in f.gaps if "subagent" in g.what)
        self.assertIn("agent-abc.jsonl", gap.why)
        self.assertIn("map:thing", gap.why)
        self.assertNotIn("agent-other", gap.why)
        self.assertEqual(sum(1 for s in f.spans if s.kind == "llm"), 2)

    def test_no_turn_duration_adds_gap_and_estimates(self):
        entries = [e for e in claude_turn_entries(with_second_turn=False) if not (isinstance(e, dict) and e.get("subtype") == "turn_duration")]
        self.env.claude_file(entries)
        f = self.collect()
        t = self.span(f, "turn")
        self.assertTrue(t.attrs["duration_estimated"])
        self.assertTrue(any("turn_duration" in g.what for g in f.gaps))

    def test_missing_transcript_fails_soft(self):
        w = W.resolve(CSID, turn=1)
        self.path.unlink()
        w.transcript_path = None
        f = T.collect(Ctx(window=w))
        self.assertEqual(f.source.status, "error")
        self.assertTrue(f.source.error)
        self.assertEqual(f.spans, [])
        self.assertTrue(any(g.severity == "warn" for g in f.gaps))

    def test_session_start_context_before_prompt_in_headless(self):
        entries = claude_turn_entries(with_second_turn=False)
        entries.insert(1, {"type": "attachment", "timestamp": "2026-11-16T02:59:59.800Z", "isSidechain": False,
                           "attachment": {"type": "hook_additional_context", "hookEvent": "SessionStart", "hookName": "SessionStart",
                                          "toolUseID": "SessionStart",
                                          "content": ["<!-- hindsight:briefing bank=proj -->\nbrief\n<!-- /hindsight:briefing -->"]}})
        self.env.claude_file(entries)
        f = self.collect()
        self.assertIn("context:inv-s0:hindsight-briefing", [s.id for s in f.spans])
        self.assertEqual(self.span(f, "context:inv-s0").phase, "session_start")


class Streaming(unittest.TestCase):
    def test_blob_lines_are_skipped_unparsed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.jsonl"
            p.write_text('{"type":"api-request-blob","broken": \n{"type":"user","a":1}\n')
            got = list(W.iter_jsonl(str(p), 0, None, T.SKIP_PREFIXES))
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0][2]["type"], "user")


if __name__ == "__main__":
    unittest.main()
