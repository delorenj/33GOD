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
    "plane-hook": {"name": "Plane hook", "first_party": True, "producers": ["plane-ingress-reconcile"]},
}
HERMES_DESKS = {"hermes-desk": {"owner": "hermes-fleet", "producer": "hermes-agent:", "bare": ["hermes-agent"], "near": "crew",
                                "name": "Hermes desk", "instance": "^[a-z0-9][a-z0-9-]*$", "malformed": ["runtime"],
                                "routes": []}}
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
        self.assertIsNone(who("someone-px-dedupe-sweep"))

    def test_first_party_prefix_beats_third_party_and_client_manifests_beat_both(self):
        reg = dict(REG, **{"hindsight": {"name": "Hindsight", "first_party": False, "producers": []},
                           "hindsight-ui": {"name": "Hindsight UI", "first_party": True, "producers": []}})
        who = N.worker_resolver(reg, N.resolver(reg), {"hindsight-client-sync": "/home/x/code/clientco"}, {})
        self.assertEqual(who("hindsight-turn"), "hindsight")              # a third-party service still gets its own work
        self.assertEqual(who("hindsight-ui-build"), "hindsight-ui")
        self.assertIsNone(who("hindsight-client-sync"))                   # a client repo's job: no prefix claims it

    def test_manifest_repo_beats_prefix_and_client_jobs_stay_put(self):
        who = N.worker_resolver(REG, N.resolver(REG), {
            "krebs-nightly-report": "/home/x/code/clientco",          # a client repo: never claimed by the krebs- prefix
            "genesis-rollup": "/home/x/code/33GOD/genesis",
        }, {})
        self.assertEqual(who("plane-ingress-reconcile"), "plane-hook")
        self.assertIsNone(who("krebs-nightly-report"))
        self.assertEqual(who("genesis-rollup"), "genesis")


class DstTest(unittest.TestCase):
    def test_fall_back_night_is_wall_clock_minutes(self):
        lo, hi = N.night_window(date(2026, 10, 31))           # clocks fall back 1 Nov 2026, 02:00
        self.assertEqual(int((hi - lo).total_seconds() // 60), 879)
        self.assertEqual(N.wall_minutes(lo, hi, "America/New_York"), 819)
        d = N.fold([row("hook-hub", "bloodbank.a.b", 818)], lo, hi, REG, "America/New_York")
        self.assertEqual(d["window"]["minutes"], 819)
        self.assertEqual(d["totals"]["events"], 1)
        self.assertIn("at time zone 'America/New_York'", N.build_sql(lo, hi, "America/New_York"))
        self.assertIn("'2026-10-31 18:02:00'::timestamp", N.build_sql(lo, hi, "America/New_York"))


class FoldTest(unittest.TestCase):
    reg = None

    def doc(self, rows, profile="public"):
        return N.fold(rows, LO, HI, self.reg or REG, "America/New_York", profile, None, {})

    def test_relayed_events_land_on_their_real_owner(self):
        reg = dict(REG, crank={"name": "Crank", "first_party": True, "producers": [], "sources": ["*#crank.*"]},
                   pjangler={"name": "PJangler", "first_party": True, "producers": ["pjangler"]})
        rows = [dict(row("pjangler", "bloodbank.crank.binding.created", 4, 2), source="urn:33god:service:crank"),
                row("pjangler", "bloodbank.project.registered", 5)]
        d = N.fold(rows, LO, HI, reg, "America/New_York", "public", None, {})
        self.assertEqual(d["minutes"]["crank"], [[4, 2]])
        self.assertEqual(d["minutes"]["pjangler"], [[5, 1]])

    def test_malformed_desks_fold_into_one_unknown_desk_and_still_credit_the_fleet(self):
        self.reg = N.Registry.from_records(REG, desks=HERMES_DESKS)
        d = self.doc([row("hermes-agent:runtime", "bloodbank.agent.session.started", 1),
                      row("hermes-agent:.hermes", "bloodbank.agent.session.started", 2),
                      row("hermes-agent", "bloodbank.agent.tool.requested", 3)], "full")
        self.assertEqual(sorted(d["desks"]), ["unknown"])
        self.assertEqual(d["minutes"]["hermes-fleet"], [[1, 1], [2, 1], [3, 1]])

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
        h = next(c for c in d["components"] if c["id"] == "hindsight")
        self.assertEqual((h["events"], h["credited"]), (0, 3))

    def test_component_events_add_up_and_plumbing_handlers_credit_nothing(self):
        d = self.doc([
            row("hook-hub", "bloodbank.agent.hook.updated", 5, 4),
            row("candybar", "bloodbank.cron.candybar.invoked", 6, 2, "krebs-tick"),
            row("mystery", "bloodbank.x.y", 7, 5),
            row("hook-handler", "hook.handler.succeeded", 5, 4, "nanoleaf"),
            row("hook-handler", "hook.handler.succeeded", 5, 4, "hub-selftest"),
            row("hook-handler", "hook.handler.succeeded", 5, 4, "hindsight-turn"),
        ])
        self.assertEqual(sum(c["events"] for c in d["components"]), d["totals"]["events"] - d["totals"]["unmapped_events"])
        self.assertEqual(d["minutes"]["hook-hub"], [[5, 4]])
        idle = [c["id"] for c in d["idle"]]
        self.assertIn("genesis", idle)                 # first-party, quiet tonight
        self.assertNotIn("krebs", idle)                # worked tonight

    def test_public_profile_counts_but_never_names_private_types(self):
        rows = [row("hook-hub", "bloodbank.telephony.call.started", 3), row("hook-hub", "bloodbank.messaging.sms.received", 4),
                row("hook-hub", "bloodbank.billing.transaction.created", 5)]
        pub = self.doc(rows)
        self.assertEqual(pub["totals"]["events"], 3)
        self.assertEqual(pub["minutes"]["hook-hub"], [[3, 1], [4, 1], [5, 1]])
        self.assertNotIn("telephony", str(pub))
        self.assertNotIn("messaging", str(pub))
        self.assertNotIn("billing", str(pub))
        self.assertEqual(len(self.doc(rows, "full")["types"]), 3)

    def test_components_carry_their_registry_summary(self):
        reg = N.load_registry()
        self.assertTrue(reg["wax"]["summary"].startswith("Processes voice recordings"))
        self.assertTrue(reg["plane-hook"]["summary"].startswith("n8n workflows"))
        self.assertIn("plane-ingress-reconcile", reg["plane-hook"]["producers"])
        self.assertIn("n8n-plane-webhook", reg["plane-hook"]["producers"])     # moved off n8n (I-10.2)
        self.assertNotIn("n8n-plane-webhook", reg["n8n"]["producers"])

    def test_public_profile_aliases_third_party_desks(self):
        rows = [row("hermes-agent:33god-pm", "bloodbank.agent.tool.completed", 1),
                row("hermes-agent:gruvato-pm", "bloodbank.agent.tool.completed", 2),
                row("mystery", "bloodbank.x.y", 3)]
        self.reg = N.Registry.from_records(REG, desks=HERMES_DESKS)
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
