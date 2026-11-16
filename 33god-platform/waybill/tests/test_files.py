import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waybill.collectors import files
from waybill.model import Ctx, TurnWindow, iso, ms

SID = "01a1e288-d177-7eb3-a080-751c3ec47af9"
T0 = ms("2026-11-16T04:06:20.982Z")
T_END = ms("2026-11-16T04:06:24.976Z") + 15000


def window(**kw):
    base = dict(cli="codex", surface="codex-exec", session_id=SID, t0=T0, t_end=T_END)
    base.update(kw)
    return TurnWindow(**base)


def pub_line(ts, subject, pid):
    return f"{ts} [{pid}] published {subject}\n"


class Pure(unittest.TestCase):
    def test_sid_hash_matches_agent_hooks(self):
        self.assertEqual(files.sid_hash("956a26e9-3f7f-4226-9491-8590d87cc90e"),
                         "e16416627f31f0da9bd75ecbd423de8046b10d1b12be341f02c3607d6bcb3191")

    def test_parse_publish_line(self):
        e = files.parse_publish_line(pub_line("2026-11-16T04:06:21.103Z", "bloodbank.evt.conversation.turn.started", 364829))
        self.assertEqual((e["ok"], e["pid"], e["subject"]), (True, 364829, "bloodbank.evt.conversation.turn.started"))
        self.assertEqual(e["t"], ms("2026-11-16T04:06:21.103Z"))
        bad = files.parse_publish_line("2026-11-16T04:06:21.103Z [12] publish failed: timeout")
        self.assertFalse(bad["ok"])
        self.assertIsNone(bad["subject"])
        self.assertIsNone(files.parse_publish_line("nonsense"))

    def test_subject_to_type(self):
        self.assertEqual(files.subject_to_type("bloodbank.evt.agent.tool.requested"), "bloodbank.agent.tool.requested")
        self.assertIsNone(files.subject_to_type("deckard.evt.attention"))

    def test_attribute_lines_uses_each_receipt_once(self):
        t = ms("2026-11-16T04:06:21.103Z")
        lines = [{"t": t, "pid": 1, "msg": "", "subject": "bloodbank.evt.conversation.turn.started", "ok": True, "path": "p"},
                 {"t": t + 50, "pid": 2, "msg": "", "subject": "bloodbank.evt.conversation.turn.started", "ok": True, "path": "p"},
                 {"t": t, "pid": 3, "msg": "", "subject": "bloodbank.evt.agent.tool.requested", "ok": True, "path": "p"}]
        pubs = [{"started": t - 100, "finished": t + 20, "event_type": "bloodbank.conversation.turn.started", "event_id": "E1", "invocation_id": "I1"}]
        got, ignored = files.attribute_lines(lines, pubs)
        self.assertEqual([(g["event_id"], g["pid"]) for g in got], [("E1", 1)])
        self.assertEqual(ignored, 2)

    def test_aggregate_publishes(self):
        mk = lambda t, pid: {"t": t, "pid": pid, "msg": "m", "subject": "bloodbank.evt.agent.tool.requested", "ok": True, "path": "p"}
        g = files.aggregate_publishes([mk(5, 1), mk(9, 2), mk(7, 1)])
        self.assertEqual((len(g), g[0]["count"], g[0]["first"], g[0]["last"], sorted(g[0]["pids"])), (1, 3, 5, 9, [1, 2]))


class Collect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.state = self.home / ".local/state"
        patches = {
            "HOME": self.home, "STATE": self.state, "JOURNAL_DIR": self.home / ".agents/journal/sessions",
            "PROOF_DIR": self.state / "automaticai/session-proof", "RECEIPTS": self.state / "receipts.sqlite3",
        }
        import waybill.model as model
        self.patches = [mock.patch.object(files, k, v) for k, v in patches.items()] + [mock.patch.object(model, "HOME", str(self.home))]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])
        self.addCleanup(self.tmp.cleanup)
        # fixtures
        import os
        h = files.sid_hash(SID)
        self.state_path = self.home / ".codex/bloodbank-sessions" / f"{h}.json"
        self.state_path.parent.mkdir(parents=True)
        self.state_path.write_text(json.dumps({"session_id": SID, "last_event_id": "0fe0feb9-f038", "turn_number": 0,
                                               "conversation_turn_number": 1, "working_directory": str(self.home / "work")}))
        in_win = (T0 + 3000) / 1000
        os.utime(self.state_path, (in_win, in_win))
        self.log = self.home / ".codex/bloodbank-sessions/publish-errors.log"
        self.log.write_text(
            pub_line("2026-11-16T04:06:21.103Z", "bloodbank.evt.conversation.turn.started", 100)
            + pub_line("2026-11-16T04:06:21.200Z", "bloodbank.evt.conversation.turn.started", 101)    # other session
            + pub_line("2026-11-16T04:06:25.105Z", "bloodbank.evt.conversation.turn.completed", 102)
            + pub_line("2026-11-16T05:00:00.000Z", "bloodbank.evt.conversation.turn.completed", 103))  # outside the window
        self.proof = self.state / "automaticai/session-proof" / f"{SID}.json"
        self.proof.parent.mkdir(parents=True)
        self.proof.write_text(json.dumps({"session_id": SID, "marker": "AAI_ROUTE_PROOF_x", "status": "pending", "proof_availability": "unverified"}))
        os.utime(self.proof, (in_win + 1, in_win + 1))
        self.journal = self.home / ".agents/journal/sessions" / f"codex-{SID}.jsonl"
        self.journal.parent.mkdir(parents=True)
        self.journal.write_text(json.dumps({"ts": "2026-11-16T04:06:21.525291+00:00", "event": "recall", "invocation_id": "INV"}) + "\n"
                                + json.dumps({"ts": "2026-11-16T03:00:00+00:00", "event": "briefing", "invocation_id": "OLD"}) + "\n")

    def _receipts(self):
        con = sqlite3.connect(self.state / "receipts.sqlite3")
        con.executescript("""
            create table invocations (invocation_id text primary key, session_id text, received_at text);
            create table executions (invocation_id text, handler_id text, started_at text, finished_at text,
                                     event_type text, event_id text);
        """)
        con.execute("insert into invocations values ('I1', ?, '2026-11-16T04:06:20.982Z')", (SID,))
        con.execute("insert into invocations values ('I2', ?, '2026-11-16T04:06:24.976Z')", (SID,))
        con.execute("insert into executions values ('I1','bloodbank-publisher','2026-11-16T04:06:20.990Z','2026-11-16T04:06:21.110Z',"
                    "'bloodbank.conversation.turn.started','E1')")
        con.execute("insert into executions values ('I2','bloodbank-publisher','2026-11-16T04:06:25.000Z','2026-11-16T04:06:25.110Z',"
                    "'bloodbank.conversation.turn.completed','E2')")
        con.commit()
        con.close()

    def test_with_receipts_attribution(self):
        self._receipts()
        f = files.collect(Ctx(window=window(), profile="public"))
        by_name = {}
        for s in f.spans:
            by_name.setdefault(s.name, []).append(s)
        pubs = by_name["publish-errors.log"]
        self.assertEqual(sorted(s.refs["event_id"] for s in pubs), ["E1", "E2"])      # pid 101 (other session) dropped
        self.assertEqual(pubs[0].attrs["subject"][:9], "bloodbank")
        e1 = next(sp for sp in pubs if sp.refs["event_id"] == "E1")
        self.assertIn(("publish:E1", e1.id, "writes"), [(l.from_, l.to, l.kind) for l in f.links])
        st = by_name["session state"][0]
        self.assertEqual((st.kind, st.component), ("file", "agent-hooks"))
        self.assertTrue(st.attrs["path"].startswith("~/.codex/bloodbank-sessions/"))     # tilde'd
        self.assertEqual(f.artifacts[st.payload]["json"]["working_directory"], "~/work")  # public profile
        proof = by_name["route proof"][0]
        self.assertEqual(proof.component, "hook-hub")
        self.assertTrue(proof.attrs["marker_present"])
        self.assertEqual([s.attrs["event"] for s in by_name["journal recall"]], ["recall"])   # briefing outside window
        self.assertNotIn("journal briefing", by_name)
        self.assertTrue(all(s.kind == "file" and s.evidence == ["files"] for s in f.spans))

    def test_without_receipts_falls_back_to_time_window(self):
        f = files.collect(Ctx(window=window()))
        pubs = [s for s in f.spans if s.name == "publish-errors.log"]
        self.assertEqual(len(pubs), 3)    # 3 lines inside the window, ambiguity flagged
        self.assertTrue(all("ambiguous" in s.attrs["attribution"] for s in pubs))
        self.assertTrue(any("no session id" in g.why for g in f.gaps))

    def test_state_file_outside_window_is_a_gap(self):
        import os
        late = (T_END + 60000) / 1000
        os.utime(self.state_path, (late, late))
        f = files.collect(Ctx(window=window()))
        self.assertFalse([s for s in f.spans if s.name == "session state"])
        self.assertTrue(any("outside the window" in g.why for g in f.gaps))

    def test_crowded_tool_lines_are_aggregated(self):
        self._receipts()
        con = sqlite3.connect(self.state / "receipts.sqlite3")
        lines = ""
        for i in range(60):
            t = T0 + 100 + i * 30
            con.execute("insert into invocations values (?, ?, ?)", (f"T{i}", SID, iso(t)))
            con.execute("insert into executions values (?,?,?,?,?,?)", (f"T{i}", "bloodbank-publisher", iso(t), iso(t + 20),
                                                                         "bloodbank.agent.tool.requested", f"TE{i}"))
            lines += pub_line(iso(t + 10), "bloodbank.evt.agent.tool.requested", 500 + i)
        con.commit()
        con.close()
        self.log.write_text(self.log.read_text() + lines)
        f = files.collect(Ctx(window=window()))
        tool = [s for s in f.spans if s.name == "publish-errors.log" and "tool.requested" in s.summary]
        self.assertEqual(len(tool), 1)
        self.assertEqual(tool[0].attrs["count"], 60)

    def test_collect_fails_soft(self):
        with mock.patch.object(files, "_state_file", side_effect=OSError("disk")):
            f = files.collect(Ctx(window=window()))
        self.assertEqual(f.source.status, "error")
        self.assertTrue(any(g.severity == "warn" for g in f.gaps))
        self.assertTrue(f.spans)    # the other sub-sources still ran


if __name__ == "__main__":
    unittest.main()
