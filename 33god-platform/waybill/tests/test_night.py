"""Tests for waybill.night (the registry and the query rows are fixtures; no database is touched)."""
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waybill import night as N

REG = {
    "candybar": {"name": "Candybar", "first_party": True, "producers": ["candybar"]},
    "hook-hub": {"name": "Hook Hub", "first_party": True, "producers": ["hook-hub"]},
    "hermes-fleet": {"name": "Hermes Fleet", "first_party": True, "producers": ["hermes-agent", "hermes-agent:*"]},
    "agent-hooks": {"name": "Agent Hooks", "first_party": True, "producers": ["claude-code"]},
    "krebs": {"name": "Krebs", "first_party": True, "producers": []},
    "hindsight": {"name": "Hindsight", "first_party": True, "producers": []},
    "genesis": {"name": "Genesis", "first_party": True, "producers": []},
}
LO = datetime(2026, 11, 16, 23, 2, tzinfo=timezone.utc)
HI = datetime(2026, 11, 17, 12, 41, tzinfo=timezone.utc)


def row(producer, type_, m, n=1, worker=None):
    return {"producer": producer, "type": type_, "m": m, "n": n, "worker": worker}


class WindowTest(unittest.TestCase):
    def test_night_crosses_midnight_in_local_time(self):
        lo, hi = N.night_window(date(2026, 11, 16))
        self.assertEqual((lo, hi), (LO, HI))           # EST is UTC-5 in November

    def test_label(self):
        doc = N.fold([], LO, HI, REG, "America/New_York")
        self.assertEqual(doc["window"]["label"], "16–17 Nov 2026")
        self.assertEqual(doc["window"]["minutes"], 819)


class ResolveTest(unittest.TestCase):
    def test_exact_beats_glob_and_glob_matches_desks(self):
        r = N.resolver(REG)
        self.assertEqual(r("hermes-agent"), "hermes-fleet")
        self.assertEqual(r("hermes-agent:gruvato-pm"), "hermes-fleet")
        self.assertIsNone(r("someone-else"))

    def test_workers_resolve_by_owner_prefix_and_manifest(self):
        who = N.worker_resolver(REG, N.resolver(REG), {"nightly-sweep": "genesis"}, {"bloodbank-publisher": "agent-hooks"})
        self.assertEqual(who("krebs-tick"), "krebs")
        self.assertEqual(who("hindsight-turn"), "hindsight")
        self.assertEqual(who("bloodbank-publisher"), "agent-hooks")
        self.assertEqual(who("nightly-sweep"), "genesis")
        self.assertIsNone(who("gruvato-px-dedupe-sweep"))


class FoldTest(unittest.TestCase):
    def doc(self, rows, profile="public"):
        return N.fold(rows, LO, HI, REG, "America/New_York", profile, None, {})

    def test_candybar_jobs_are_credited_to_their_component(self):
        d = self.doc([
            row("candybar", "bloodbank.cron.candybar.invoked", 10, 2, "krebs-tick"),
            row("candybar", "bloodbank.cron.candybar.invoked", 10, 1, "gruvato-px-dedupe-sweep"),
            row("candybar", "bloodbank.cron.tick.fired", 10, 1),
        ])
        self.assertEqual(d["minutes"]["krebs"], [[10, 2]])
        self.assertEqual(d["minutes"]["candybar"], [[10, 2]])   # the client job and the tick stay with Candybar
        self.assertEqual(d["totals"]["events"], 4)

    def test_handler_rows_credit_work_without_double_counting(self):
        d = self.doc([
            row("hook-hub", "bloodbank.agent.hook.updated", 5, 3),
            row("hook-handler", "hook.handler.succeeded", 5, 3, "hindsight-turn"),
            row("hook-handler", "hook.handler.succeeded", 5, 9, "who-knows"),
        ])
        self.assertEqual(d["totals"]["events"], 3)
        self.assertEqual(sum(d["events_by_minute"]), 3)
        self.assertEqual(d["events_by_minute"][5], 3)
        self.assertEqual(d["minutes"]["hindsight"], [[5, 3]])
        self.assertNotIn("who-knows", str(d))

    def test_public_profile_aliases_third_party_desks(self):
        rows = [row("hermes-agent:33god-pm", "bloodbank.agent.tool.completed", 1),
                row("hermes-agent:gruvato-pm", "bloodbank.agent.tool.completed", 2),
                row("mystery", "bloodbank.x.y", 3)]
        pub = self.doc(rows)
        self.assertEqual(sorted(pub["desks"]), ["33god-pm", "desk-1"])
        self.assertNotIn("gruvato", str(pub))
        self.assertNotIn("mystery", str(pub))
        full = self.doc(rows, "full")
        self.assertIn("gruvato-pm", full["desks"])
        self.assertEqual(full["unmapped"], {"mystery": 1})

    def test_out_of_window_rows_are_dropped_and_rare_types_become_moments(self):
        d = self.doc([row("hook-hub", "bloodbank.a.b", -1), row("hook-hub", "bloodbank.a.b", 819),
                      row("claude-code", "bloodbank.agent.session.started", 400)])
        self.assertEqual(d["totals"]["events"], 1)
        self.assertEqual(d["moments"], [{"m": 400, "component": "agent-hooks", "type": "bloodbank.agent.session.started"}])


if __name__ == "__main__":
    unittest.main()
