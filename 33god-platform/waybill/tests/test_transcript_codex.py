"""Tests for waybill.collectors.transcript_codex (rollout + thread_history fixtures from test_window.make_codex)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from waybill import window as W
from waybill.collectors import transcript_codex as T
from waybill.model import Ctx, iso, ms
from test_window import XSID, Env, make_codex, make_receipts

RECEIPTS = [
    ("c-s", "codex", "SessionStart", XSID, "2026-11-16T04:06:20.448Z"),
    ("c-p1", "codex", "UserPromptSubmit", XSID, "2026-11-16T04:06:20.982Z"),
    ("c-e1", "codex", "Stop", XSID, "2026-11-16T04:06:24.976Z"),
    ("c-p2", "codex", "UserPromptSubmit", XSID, "2026-11-16T04:07:21.000Z"),
]


class CodexCollect(unittest.TestCase):
    def setUp(self):
        self.env = Env().__enter__()
        make_receipts(self.env.receipts, RECEIPTS)
        self.rollout, self.tids = make_codex(self.env)

    def tearDown(self):
        self.env.__exit__()

    def collect(self, turn=1, profile="full", **kw):
        w = W.resolve(XSID, turn=turn)
        return T.collect(Ctx(window=w, profile=profile, **kw))

    def span(self, f, sid):
        return next(s for s in f.spans if s.id == sid)

    def test_slice_is_exact(self):
        f = self.collect(1)
        self.assertEqual(f.source.status, "ok")
        self.assertEqual(sum(1 for s in f.spans if s.kind == "llm"), 2)
        self.assertEqual(sum(1 for s in f.spans if s.kind == "tool"), 2)
        self.assertEqual(self.span(f, "prompt").attrs["chars"], len("prompt number 1"))
        f2 = self.collect(2)
        self.assertEqual(self.span(f2, "prompt").attrs["chars"], len("prompt number 2"))
        self.assertEqual(sum(1 for s in f2.spans if s.kind == "llm"), 2)

    def test_facts_turn_id_is_native(self):
        f = self.collect(1)
        self.assertEqual(f.facts["turn_id"], self.tids[0])
        self.assertEqual(f.facts["turn_index"], 1)
        self.assertEqual(f.facts["surface"], "codex-exec")
        self.assertEqual(f.facts["model_requested"], "automaticai/auto/orchestrator")
        self.assertEqual(self.collect(2).facts["turn_id"], self.tids[1])

    def test_component_per_surface(self):
        self.assertEqual(self.span(self.collect(1), "prompt").component, "ext:codex-exec")

    def test_llm_spans_from_token_usage_records(self):
        f = self.collect(1)
        l1, l2 = self.span(f, "llm:1"), self.span(f, "llm:2")
        self.assertEqual(l1.refs["client_request"], "resp_0_1")
        self.assertEqual(l1.attrs["client_request"], "resp_0_1")
        self.assertEqual(l1.attrs["tokens_in"], 1000)           # Codex input_tokens already includes the cached part
        self.assertEqual(l1.attrs["tokens_out"], 20)
        self.assertEqual(l1.attrs["usage"]["cached_input_tokens"], 400)
        self.assertEqual(l1.attrs["usage"]["reasoning_output_tokens"], 5)
        self.assertEqual(l1.attrs["effort"], "high")
        self.assertEqual(l1.attrs["requested_model"], "automaticai/auto/orchestrator")
        self.assertEqual(l1.attrs["stop_reason"], "tool_use")
        self.assertEqual(l2.attrs["stop_reason"], "end_turn")
        self.assertEqual(l2.attrs["tokens_in"], 1200)
        self.assertTrue(l1.sync)
        self.assertIn("(400 cached)", l1.summary)
        # the second request starts when the tool output was appended
        base = ms("2026-11-16T04:06:19.985Z")
        self.assertEqual(l2.t0, base + 3210)
        self.assertEqual(l2.t1, base + 5000)

    def test_tool_spans_by_call_id(self):
        f = self.collect(1)
        shell, patch = self.span(f, "tool:call_0_1"), self.span(f, "tool:call_0_2")
        self.assertEqual(shell.name, "exec_command")
        self.assertEqual(shell.status, "failed")
        self.assertEqual(shell.attrs["exit_code"], 1)
        self.assertIn("exit code 1", shell.reason)
        self.assertEqual(patch.name, "apply_patch")
        self.assertEqual(patch.status, "ok")
        self.assertIn("/tmp/proj/a.txt", patch.summary)
        self.assertIn("Success.", f.artifacts[patch.payload]["text"])
        got = {(l.from_, l.to, l.kind) for l in f.links}
        self.assertIn(("llm:1", "tool:call_0_1", "calls"), got)
        self.assertIn(("tool:call_0_1", "llm:2", "feeds"), got)
        self.assertIn(("prompt", "llm:1", "feeds"), got)

    def test_turn_span(self):
        f = self.collect(1)
        t = self.span(f, "turn")
        self.assertEqual(t.attrs["duration_ms"], 5050)
        self.assertEqual(t.attrs["time_to_first_token_ms"], 4000)
        self.assertEqual(t.attrs["native_turn_id"], self.tids[0])
        self.assertEqual(t.status, "ok")
        self.assertEqual(t.t1, ms("2026-11-16T04:06:19.985Z") + 5050)

    def test_hook_contexts_split_and_bootstrap_skipped(self):
        f = self.collect(1)
        ids = {s.id for s in f.spans if s.kind == "context"}
        self.assertEqual(ids, {
            "context:c-s", "context:c-s:automaticai-routing-start", "context:c-s:hindsight-briefing",
            "context:c-p1", "context:c-p1:skill-reminder", "context:c-p1:automaticai-routing-start", "context:c-p1:hindsight-recall"})
        self.assertEqual(self.span(f, "context:c-s").phase, "session_start")
        self.assertEqual(self.span(f, "context:c-p1").phase, "prompt_submit")
        # the "## Memory" developer message is Codex-native, not hook output
        self.assertEqual(self.span(f, "turn").attrs["bootstrap_developer_chars"], len("## Memory\nbootstrap only"))
        for s in f.spans:
            if s.kind == "context":
                self.assertNotIn("bootstrap only", f.artifacts[s.payload]["text"])

    def test_turn_two_has_no_session_start_context(self):
        f = self.collect(2)
        self.assertFalse(any(s.id.startswith("context:c-s") for s in f.spans))

    def test_public_profile_truncates(self):
        f = self.collect(1, profile="public")
        s = self.span(f, "context:c-p1:hindsight-recall")
        self.assertLessEqual(len(f.artifacts[s.payload]["text"]), 280)

    def test_missing_rollout_fails_soft(self):
        w = W.resolve(XSID, turn=1)
        self.rollout.unlink()
        f = T.collect(Ctx(window=w))
        self.assertEqual(f.source.status, "error")
        self.assertEqual(f.spans, [])
        self.assertTrue(f.gaps)

    def test_codex_llm_calls_for_gateway(self):
        w = W.resolve(XSID, turn=1)
        calls = T.codex_llm_calls(w)
        self.assertEqual([(c["input_tokens"], c["output_tokens"]) for c in calls], [(1000, 20), (1200, 7)])
        self.assertEqual(calls[0]["client_request"], "resp_0_1")


class CodexScan(unittest.TestCase):
    def test_in_progress_turn_without_history_row(self):
        with Env() as env:
            make_receipts(env.receipts, RECEIPTS)
            rollout, tids = make_codex(env, turns=1)
            import sqlite3
            con = sqlite3.connect(env.codex / "thread_history_1.sqlite")
            con.execute("delete from thread_turns")
            con.commit()
            con.close()
            w = W.resolve(XSID, turn=1)
            f = T.collect(Ctx(window=w))
            self.assertEqual(f.source.status, "ok")
            self.assertEqual(f.facts["turn_id"], tids[0])
            self.assertEqual(sum(1 for s in f.spans if s.kind == "llm"), 2)


if __name__ == "__main__":
    unittest.main()
