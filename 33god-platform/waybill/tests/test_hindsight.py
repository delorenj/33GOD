import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waybill.collectors import hindsight as hs
from waybill.model import Ctx, TurnWindow, ms

SID = "7dcf25a3-9dee-4fe2-8da2-7d569ad24599"
PROMPT_INV = "bdbdba89-a2d7-4c49-b0ce-9ecfda3525f4"
STOP_INV = "b4a88a6f-63d9-49c4-989d-53237746813b"
T0 = ms("2026-11-16T03:53:25.284Z")
T_END = ms("2026-11-16T03:58:40.666Z") + 15000

JOURNAL = [
    {"ts": "2026-11-16T03:45:43.772625+00:00", "cli": "claude", "session_id": SID, "invocation_id": "73f946bd", "event": "briefing",
     "bank": "33GOD", "models": {"briefing": "ok"}, "total_chars": 5769, "elapsed_ms": 121},
    {"ts": "2026-11-16T03:53:26.078966+00:00", "cli": "claude", "session_id": SID, "invocation_id": PROMPT_INV, "event": "recall",
     "bank": "33GOD", "banks": ["33GOD"], "prompt_len": 779, "query_len_raw": 779, "query_len_clean": 774, "query_len_sent": 774,
     "total_chars": 5800, "returned_anything": True, "failed_banks": 0, "deadline_s": 4.0, "elapsed_ms": 390,
     "per_bank": [{"bank": "33GOD", "status": "ok", "results": 18, "latency_ms": 385}]},
    {"ts": "2026-11-16T03:58:40.756428+00:00", "cli": "claude", "session_id": SID, "invocation_id": STOP_INV, "event": "turn_captured",
     "turn": 1, "source": "payload", "ask_chars": 774, "outcome_chars": 2386, "files": 0, "buffered_chars": 3264},
]
CAPTURE = {"cli": "claude", "session_id": SID, "bank": "33GOD", "repo": "33GOD", "document_id": f"session-claude-{SID}",
           "pending_asks": [], "turns": [{"n": 1, "ts": "2026-11-16T03:58:40Z", "ask": "A" * 400, "outcome": "B" * 500, "files": []}],
           "batches": []}
AUDIT_ITEM = {
    "id": "1e371edf", "action": "recall", "started_at": "2026-11-16T03:53:25.715890+00:00", "ended_at": "2026-11-16T03:53:26.075346+00:00",
    "duration_ms": 359, "transport": "http",
    "request": {"query": "q" * 774, "budget": "mid", "max_tokens": 1400, "prefer_observations": True, "types": ["world"]},
    "response": {"entities": {"x": 1}, "results": [
        {"type": "world", "text": "T" * 300, "scores": {"final": 0.9, "reranker": 0.8, "semantic": 0.7}, "document_id": "d", "entities": ["e"], "tags": []},
        {"type": "observation", "text": "short", "scores": {"final": 0.5}, "tags": ["t"]}]},
}


def window(**kw):
    base = dict(cli="claude", surface="claude-code", session_id=SID, t0=T0, t_end=T_END, prompt_invocation_id=PROMPT_INV)
    base.update(kw)
    return TurnWindow(**base)


def write_journal(d, rows=JOURNAL):
    p = Path(d, f"claude-{SID}.jsonl")
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return Path(d)


class Pure(unittest.TestCase):
    def test_bank_status(self):
        self.assertEqual(hs.bank_status("ok"), ("ok", None))
        self.assertEqual(hs.bank_status("empty"), ("ok", "no_results"))
        self.assertEqual(hs.bank_status("timeout"), ("timeout", "timeout"))
        self.assertEqual(hs.bank_status("http_400"), ("failed", "http_400"))

    def test_flush_status(self):
        self.assertEqual(hs.flush_status("session_flush", "submitted"), ("pending", "retain_submitted"))
        self.assertEqual(hs.flush_status("session_flush_confirmed"), ("ok", "retain_confirmed"))
        self.assertEqual(hs.flush_status("session_flush_failed")[0], "failed")
        self.assertEqual(hs.flush_status("session_flush_abandoned")[0], "dropped")

    def test_pick_audit_row_by_time_and_query_length(self):
        t0 = ms("2026-11-16T03:53:25.634Z")
        t1 = t0 + 450
        a = dict(AUDIT_ITEM)
        far = {**AUDIT_ITEM, "id": "far", "started_at": "2026-11-16T03:50:00+00:00"}
        other_q = {**AUDIT_ITEM, "id": "otherq", "request": {"query": "short"}}
        self.assertEqual(hs.pick_audit_row([far, other_q, a], t0, t1, 774)["id"], "1e371edf")
        self.assertEqual(hs.pick_audit_row([far], t0, t1, 774), None)
        self.assertEqual(hs.pick_audit_row([other_q], t0, t1, 774)["id"], "otherq")   # length mismatch still beats nothing

    def test_audit_artifact_profiles(self):
        full = hs.audit_artifact(AUDIT_ITEM, "33GOD", "full")
        pub = hs.audit_artifact(AUDIT_ITEM, "33GOD", "public")
        self.assertEqual(len(full["results"][0]["text"]), 300)
        self.assertEqual(len(pub["results"][0]["text"]), 121)        # 120 + ellipsis
        self.assertEqual(pub["results"][0]["scores"]["final"], 0.9)  # scores kept
        self.assertEqual(pub["by_type"], {"world": 1, "observation": 1})
        self.assertNotIn("entities", pub)
        self.assertIn("entities", full)
        self.assertEqual(len(pub["request"]["query"]), 281)

    def test_recall_spans_for_row_without_per_bank(self):
        self.assertEqual(hs.recall_spans_for_row({"banks": ["a", "b"], "returned_anything": True})[0][0], "a")


class Collect(unittest.TestCase):
    def run_collect(self, rows=JOURNAL, capture=CAPTURE, audit=(AUDIT_ITEM,), profile="full", **wk):
        with tempfile.TemporaryDirectory() as d:
            jd = write_journal(d, rows)
            with mock.patch.object(hs, "JOURNAL_DIR", jd), \
                 mock.patch.object(hs, "audit_list", return_value=list(audit)) as al, \
                 mock.patch.object(hs, "_load_capture", return_value=(capture, "file" if capture else "absent")):
                f = hs.collect(Ctx(window=window(**wk), profile=profile))
        return f, al

    def test_recall_buffer_and_audit(self):
        f, al = self.run_collect()
        byid = {s.id: s for s in f.spans}
        rec = byid[f"memory:recall:{PROMPT_INV}:33GOD"]
        self.assertEqual((rec.kind, rec.component, rec.sync, rec.status), ("memory", "hindsight", True, "ok"))
        self.assertEqual(rec.parent, f"handler:{PROMPT_INV}:hindsight-recall")
        self.assertEqual(rec.attrs["results"], 18)
        self.assertEqual(rec.attrs["injected_chars"], 5800)
        self.assertEqual(rec.attrs["query_chars"], 774)
        self.assertAlmostEqual(rec.t1 - rec.t0, 385, places=3)
        self.assertIsNotNone(rec.payload)
        art = f.artifacts[rec.payload]["json"]
        self.assertEqual(art["result_count"], 2)
        self.assertEqual(art["results"][0]["rank"], 1)
        self.assertIn(("handler:%s:hindsight-recall" % PROMPT_INV, rec.id, "calls"), [(l.from_, l.to, l.kind) for l in f.links])
        ask = byid[f"memory:buffer:{PROMPT_INV}"]
        turn = byid[f"memory:buffer:{STOP_INV}"]
        for s in (ask, turn):
            self.assertEqual((s.status, s.reason), ("pending", "retain_deferred"))
            self.assertIn("9000", s.summary)
        self.assertIn("Hindsight retain is deferred; this waybill ends before the document is written", [g.why for g in f.gaps])
        self.assertEqual(f.facts["project"], "33GOD")
        self.assertNotIn("memory:briefing:73f946bd", byid)    # session start is outside the window
        self.assertEqual(f.source.items, 3)

    def test_public_profile_cuts_memory_and_turn_text(self):
        f, _ = self.run_collect(profile="public")
        texts = [a["json"] for a in f.artifacts.values() if "json" in a]
        recall = next(t for t in texts if "results" in t)
        self.assertLessEqual(len(recall["results"][0]["text"]), 121)
        turn = next(t for t in texts if t.get("turn") == 1)
        self.assertLessEqual(len(turn["outcome"]), 281)

    def test_recall_skipped_and_failed_bank(self):
        rows = [
            {"ts": "2026-11-16T03:53:26+00:00", "invocation_id": PROMPT_INV, "event": "recall_skipped",
             "reason": "query_under_min_length_after_cleanup", "query_len_raw": 9, "query_len_clean": 0},
            {"ts": "2026-11-16T03:53:27+00:00", "invocation_id": "inv2", "event": "recall", "banks": ["a", "b"], "elapsed_ms": 100,
             "total_chars": 10, "per_bank": [{"bank": "a", "status": "timeout", "results": 0, "latency_ms": 4000},
                                            {"bank": "b", "status": "empty", "results": 0, "latency_ms": 90}]},
        ]
        f, al = self.run_collect(rows=rows, capture=None)
        by = {s.id: s for s in f.spans}
        sk = by[f"memory:recall:{PROMPT_INV}:none"]
        self.assertEqual((sk.status, sk.reason), ("skipped", "query_under_min_length_after_cleanup"))
        self.assertEqual(by["memory:recall:inv2:a"].status, "timeout")
        self.assertEqual(by["memory:recall:inv2:b"].reason, "no_results")
        al.assert_not_called()   # nothing to audit when no bank returned results

    def test_audit_failure_is_a_gap_not_a_crash(self):
        with tempfile.TemporaryDirectory() as d:
            jd = write_journal(d)
            with mock.patch.object(hs, "JOURNAL_DIR", jd), \
                 mock.patch.object(hs, "audit_list", side_effect=RuntimeError("401")), \
                 mock.patch.object(hs, "_load_capture", return_value=(None, "absent")):
                f = hs.collect(Ctx(window=window()))
        self.assertEqual(f.source.status, "ok")
        rec = next(s for s in f.spans if s.name == "recall")
        self.assertIsNone(rec.payload)
        self.assertTrue(any("audit list failed" in g.why for g in f.gaps))

    def test_flush_spans(self):
        op = "2b935394-1a96-545a-9636-9748892ec5cb"
        rows = JOURNAL + [
            {"ts": "2026-11-16T03:58:41+00:00", "invocation_id": STOP_INV, "event": "session_flush", "bank": "33GOD",
             "document_id": "d", "operation_id": op, "turns": [1, 1], "attempt": 0, "trigger": "size", "status": "submitted"},
            {"ts": "2026-11-16T04:30:00+00:00", "invocation_id": "", "event": "session_flush_confirmed", "operation_id": op, "turns": [1, 1]},
        ]
        with tempfile.TemporaryDirectory() as d:
            jd = write_journal(d, rows)
            with mock.patch.object(hs, "JOURNAL_DIR", jd), mock.patch.object(hs, "audit_list", return_value=[AUDIT_ITEM]), \
                 mock.patch.object(hs, "_load_capture", return_value=(CAPTURE, "file")), \
                 mock.patch.object(hs, "operation_get", return_value={"status": "completed"}):
                f = hs.collect(Ctx(window=window()))
        fl = next(s for s in f.spans if s.id == f"memory:flush:{op}")
        self.assertEqual((fl.status, fl.reason), ("pending", "retain_submitted"))   # confirmation lands after the window
        self.assertEqual(fl.attrs["after_window"][0]["event"], "session_flush_confirmed")
        self.assertIsNotNone(fl.payload)

    def test_missing_journal_is_empty_not_error(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(hs, "JOURNAL_DIR", Path(d)), mock.patch.object(hs, "_load_capture", return_value=(None, "absent")):
                f = hs.collect(Ctx(window=window()))
        self.assertEqual(f.source.status, "empty")
        self.assertTrue(f.gaps)

    def test_turn_skipped_without_capture(self):
        rows = [{"ts": "2026-11-16T03:58:40+00:00", "invocation_id": STOP_INV, "event": "turn_skipped", "reason": "turn_trivial",
                 "source": "payload", "outcome_chars": 4}]
        f, _ = self.run_collect(rows=rows, capture=None)
        s = f.spans[0]
        self.assertEqual((s.id, s.status, s.reason), (f"memory:buffer:{STOP_INV}", "skipped", "turn_trivial"))


if __name__ == "__main__":
    unittest.main()
