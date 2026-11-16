"""record must leave a codex helper session (prompt + SessionEnd, no Stop) and follow the real one."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from waybill import cli as C
from waybill import live
from waybill import model as M


def _db(rows):
    d = tempfile.mkdtemp()
    p = Path(d) / "r.sqlite3"
    con = sqlite3.connect(p)
    con.execute("create table invocations (invocation_id text, session_id text, native text, cli text, received_at text)")
    con.executemany("insert into invocations values (?,?,?,?,?)", rows)
    con.commit()
    con.close()
    return p


class HelperSessionTest(unittest.TestCase):
    def setUp(self):
        self.p = _db([
            ("p1", "helper", "UserPromptSubmit", "codex", "2026-11-16T05:12:12.260Z"),
            ("p2", "real", "UserPromptSubmit", "codex", "2026-11-16T05:12:13.624Z"),
            ("e1", "helper", "SessionEnd", "codex", "2026-11-16T05:12:19.942Z"),
            ("s2", "real", "Stop", "codex", "2026-11-16T05:12:26.871Z"),
            ("e2", "real", "SessionEnd", "codex", "2026-11-16T05:12:26.976Z"),
        ])
        self.patch = mock.patch.object(C, "RECEIPTS", self.p)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.t0 = M.ms("2026-11-16T05:12:12.000Z")

    def test_helper_ended_without_stop(self):
        self.assertTrue(live.ended_without_stop("helper", self.t0))

    def test_real_session_has_stop(self):
        self.assertFalse(live.ended_without_stop("real", self.t0))

    def test_next_prompt_skips_rejected(self):
        got = live.next_prompt_after(self.t0 - 5000, "codex", {"helper"})
        self.assertEqual(got[0], "real")
        self.assertEqual(got[1], "p2")


if __name__ == "__main__":
    unittest.main()
