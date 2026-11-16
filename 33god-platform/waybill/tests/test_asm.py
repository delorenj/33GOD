import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waybill.collectors import asm
from waybill.model import Ctx, TurnWindow, ms

SID = "956a26e9-3f7f-4226-9491-8590d87cc90e"
SCOPE = f"claude:s:{SID}"
T0 = ms("2026-11-16T04:00:38.667Z")
T_END = ms("2026-11-16T04:00:41.014Z") + 15000


def window(**kw):
    base = dict(cli="claude", surface="claude-code-headless", session_id=SID, t0=T0, t_end=T_END)
    base.update(kw)
    return TurnWindow(**base)


def log_line(local_ts, frm, to, scope=SCOPE, held=100, pid=1):
    return f"{local_ts}  {frm:<14} -> {to:<14}  {scope}  held={held}ms  pid={pid}\n"


def stream_entry(at_ms, frm, to, reason, seq, **extra):
    import json
    body = {"basis": "sid", "pid": "0", "zellij_pane": "35", "zellij_session": "Workspace", "reason": reason, "tools": 0,
            "held_ms": 152, "to": to, "scope": SCOPE, "cwd": "/home/x", "at_ms": at_ms, "from": frm, "cli": "claude",
            "turn": 1, "seq": seq, "subs": 0}
    body.update(extra)
    return [f"{at_ms}-0", ["j", json.dumps(body)]]


class PureHelpers(unittest.TestCase):
    def test_infer_reason(self):
        cases = {("none", "starting"): "start", ("starting", "working"): "prompt", ("idle", "working"): "prompt",
                 ("working", "tool_running"): "tool_req", ("failed", "tool_running"): "tool_req",
                 ("tool_running", "working"): "tool_done", ("working", "idle"): "quiesce",
                 ("working", "failed"): "fail", ("working", "stale"): "stale", ("idle", "gone"): "gone",
                 ("none", "idle"): "discover"}
        for (f, t), want in cases.items():
            self.assertEqual(asm.infer_reason(f, t), want, (f, t))

    def test_fmt_held_and_summary(self):
        self.assertEqual(asm.fmt_held(673), "673 ms")
        self.assertEqual(asm.fmt_held(4200), "4.2 s")
        self.assertEqual(asm.fmt_held(461892), "7.7 min")
        self.assertEqual(asm.summarize("idle", "working", "prompt", 4200), "ASM: idle -> working on prompt (held idle 4.2 s)")
        self.assertEqual(asm.summarize("none", "starting", "start", 0), "ASM: none -> starting on session start")

    def test_parse_log_line(self):
        e = asm.parse_log_line(log_line("2026-11-15T23:00:39-05:00", "starting", "working", held=673, pid=120257))
        self.assertEqual((e["from"], e["to"], e["scope"], e["held_ms"], e["log_pid"]), ("starting", "working", SCOPE, 673.0, 120257))
        self.assertEqual(e["at_ms"], ms("2026-11-16T04:00:39Z") + 500)   # truncated second, centred
        self.assertIsNone(asm.parse_log_line("garbage"))
        self.assertIsNone(asm.parse_log_line(log_line("2026-11-15T23:00:39-05:00", "a", "b", held="?"))["held_ms"])

    def test_read_log_entries_both_generations(self):
        with tempfile.TemporaryDirectory() as d:
            old, cur = Path(d, "t.log.1"), Path(d, "t.log")
            old.write_text(log_line("2026-11-15T23:00:38-05:00", "none", "starting"))
            cur.write_text(
                log_line("2026-11-15T23:00:39-05:00", "starting", "working")
                + log_line("2026-11-15T23:00:39-05:00", "starting", "working", scope="claude:s:other")
                + log_line("2026-11-15T23:30:00-05:00", "working", "idle"))
            got = asm.read_log_entries(SCOPE, [old, cur], T0 - 2000, T_END)
            self.assertEqual([(e["from"], e["to"]) for e in got], [("none", "starting"), ("starting", "working")])

    def test_normalize_stream_entry_shapes(self):
        raw = stream_entry(1794801225715, "tool_running", "working", "tool_done", 12)
        e = asm.normalize_stream_entry(raw)
        self.assertEqual((e["at_ms"], e["reason"], e["seq"], e["entry_id"]), (1794801225715.0, "tool_done", 12, "1794801225715-0"))
        e2 = asm.normalize_stream_entry({"id": "5-0", "j": raw[1][1]})
        self.assertEqual(e2["to"], "working")
        e3 = asm.normalize_stream_entry({"from": "a", "to": "b", "at_ms": 7})
        self.assertEqual(e3["at_ms"], 7.0)
        self.assertIsNone(asm.normalize_stream_entry(["x", ["j", "not json"]]))

    def test_merge_prefers_stream_and_fills_gaps(self):
        st = [asm.normalize_stream_entry(stream_entry(1000, "working", "tool_running", "tool_req", 3))]
        lg = [
            {"from": "working", "to": "tool_running", "at_ms": 1400.0, "log_ts_ms": 900.0, "src": "log", "scope": SCOPE},
            {"from": "none", "to": "starting", "at_ms": 400.0, "log_ts_ms": 0.0, "src": "log", "scope": SCOPE},
        ]
        out = asm.merge_entries(st, lg)
        self.assertEqual([(e["from"], e["src"]) for e in out], [("none", "log"), ("working", "stream")])

    def test_build_span_join_and_attrs(self):
        e = asm.normalize_stream_entry(stream_entry(1794801205501, "starting", "working", "prompt", 2, held_ms=461892, tools=0))
        sp = asm.build_span(e, asm.entry_key(e, {}), "full")
        self.assertEqual(sp.id, "state:asm:1794801205501-0")
        self.assertEqual((sp.kind, sp.component, sp.name, sp.reason, sp.phase), ("state", "asm", "starting -> working", "prompt", "prompt_submit"))
        self.assertIsNone(sp.t1)
        self.assertEqual(sp.attrs["_join"]["event_type"], "bloodbank.conversation.turn.started")
        self.assertEqual(sp.attrs["_join"]["link"], "triggers")
        self.assertEqual(sp.attrs["pane"], "Workspace:35")
        self.assertEqual(sp.refs["seq"], 2)
        self.assertEqual(sp.evidence, ["asm"])
        pub = asm.build_span(e, "k", "public")
        self.assertEqual(pub.attrs["cwd"], "/home/x")

    def test_no_join_for_fail(self):
        e = asm.normalize_stream_entry(stream_entry(5, "working", "failed", "fail", 9))
        self.assertNotIn("_join", asm.build_span(e, "5-0", "full").attrs)

    def test_log_keys_unique_within_a_second(self):
        seen: dict = {}
        mk = lambda: {"src": "log", "log_ts_ms": 1000.0}
        keys = [asm.entry_key(mk(), seen) for _ in range(3)]
        self.assertEqual(keys, ["log-1000", "log-1000.1", "log-1000.2"])


class CollectTests(unittest.TestCase):
    def setUp(self):
        # no live journal / receipts in unit tests
        for target, ret in (("deckard_lines", []),):
            p = mock.patch.object(asm, target, return_value=ret)
            p.start()
            self.addCleanup(p.stop)
        for target, ret in (("earliest_ms", None), ("transition_invocations", [])):
            p = mock.patch.object(asm.hookhub, target, return_value=ret)
            p.start()
            self.addCleanup(p.stop)

    def _log_dir(self, d, text):
        cur = Path(d, "transitions.log")
        cur.write_text(text)
        return cur

    def test_log_only_when_redis_empty(self):
        with tempfile.TemporaryDirectory() as d:
            cur = self._log_dir(d, log_line("2026-11-15T23:00:38-05:00", "none", "starting")
                                + log_line("2026-11-15T23:00:39-05:00", "starting", "working", held=673)
                                + log_line("2026-11-15T23:00:41-05:00", "working", "idle", held=1745))
            with mock.patch.object(asm, "TRANSITIONS_LOG", cur), mock.patch.object(asm, "_redis", return_value=[]):
                f = asm.collect(Ctx(window=window()))
        self.assertEqual(f.source.status, "ok")
        self.assertEqual([s.reason for s in f.spans], ["start", "prompt", "quiesce"])
        self.assertTrue(all(s.attrs.get("reason_inferred") for s in f.spans))
        self.assertTrue(any("transitions.log has 1 s resolution" in g.why for g in f.gaps))
        self.assertTrue(any(fi.title.startswith("ASM never reaches 'gone'") for fi in f.findings))
        self.assertTrue(any(g.component == "ext:zellij" for g in f.gaps))   # tab painter has no record

    def test_redis_down_fails_soft(self):
        with tempfile.TemporaryDirectory() as d:
            cur = self._log_dir(d, "")
            with mock.patch.object(asm, "TRANSITIONS_LOG", cur), \
                 mock.patch.object(asm, "_redis", side_effect=asm.RedisError("down")):
                f = asm.collect(Ctx(window=window()))
        self.assertEqual(f.source.status, "empty")
        self.assertEqual(f.spans, [])
        self.assertTrue(f.gaps)

    def test_unexpected_exception_is_an_error_source(self):
        with mock.patch.object(asm, "read_log_entries", side_effect=ValueError("boom")), \
             mock.patch.object(asm, "_redis", return_value=[]):
            f = asm.collect(Ctx(window=window()))
        self.assertEqual(f.source.status, "error")
        self.assertIn("boom", f.source.error)
        self.assertTrue(any(g.severity == "warn" for g in f.gaps))

    def test_live_capture_preferred_and_nanoleaf_span(self):
        live = {
            "stream": [stream_entry(int(T0) + 300, "starting", "working", "prompt", 2),
                       stream_entry(int(T0) + 2400, "working", "idle", "quiesce", 3)],
            "hash": {"scope": SCOPE, "session_id": "", "correlationid": "", "zellij_pane": "35", "zellij_session": "Workspace"},
            "pane_idx": "claude:s:parent-session",
            "nlp": {"state": "hitl", "ts": str((T0 + 2500) / 1000)},
        }
        with tempfile.TemporaryDirectory() as d:
            cur = self._log_dir(d, log_line("2026-11-15T23:00:39-05:00", "starting", "working"))
            with mock.patch.object(asm, "TRANSITIONS_LOG", cur), \
                 mock.patch.object(asm, "_redis", side_effect=AssertionError("redis must not be touched in live mode")):
                f = asm.collect(Ctx(window=window(), live={"asm": live}))
        kinds = [(s.kind, s.component) for s in f.spans]
        self.assertEqual(kinds.count(("state", "asm")), 2)            # log line deduped against the live stream
        notify = [s for s in f.spans if s.kind == "notify"]
        self.assertEqual(len(notify), 1)
        self.assertEqual(notify[0].component, "ext:nanoleaf")
        self.assertTrue(any("points at" in g.why for g in f.gaps))      # pane index -> parent session
        self.assertTrue(any("session_id" in fi.title for fi in f.findings))

    def test_redis_verbs_are_read_only(self):
        with self.assertRaises(asm.RedisError):
            asm._redis("SET", "k", "v")
        with self.assertRaises(asm.RedisError):
            asm._redis("DEL", "k")


if __name__ == "__main__":
    unittest.main()
