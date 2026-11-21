"""Tests for waybill.registry, the one resolver (I-10.2). The committed cast is the fixture for the real
rules; Registry.from_records builds small registries for precedence. tools/cast/resolve.cases.json is shared
with the player's selfcheck, so Python and TypeScript cannot drift apart."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waybill import registry as R

CASES = Path(__file__).resolve().parents[2] / "manual" / "sandbox" / "tools" / "cast" / "resolve.cases.json"
DESKS = {"hermes-desk": {"owner": "hermes-fleet", "producer": "hermes-agent:", "bare": ["hermes-agent"], "near": "crew",
                         "name": "Hermes desk", "instance": "^[a-z0-9][a-z0-9-]*$", "malformed": ["runtime"],
                         "routes": [{"instance": "*-momo", "id": "momo"}]}}
RECORDS = {
    "crank": {"name": "Crank", "first_party": True, "producers": [], "sources": ["*#crank.*"]},
    "pjangler": {"name": "PJangler", "first_party": True, "producers": ["pjangler"]},
    "delosip": {"name": "DeloSIP", "first_party": True, "producers": [], "sources": ["urn:33god:service:n8n-*#telephony.*"]},
    "n8n": {"name": "n8n", "first_party": False, "producers": ["n8n"]},
    "hermes-fleet": {"name": "Hermes fleet", "first_party": True, "producers": ["hermes-agent*"]},
    "momo": {"name": "Momo", "first_party": True, "producers": []},
}


class RealCast(unittest.TestCase):
    def test_cast_loads_with_a_resolution_map(self):
        reg = R.load()
        self.assertIn("crank", reg.components)
        self.assertTrue(reg.sources and reg.desks and reg.tenants["rules"])

    def test_shared_cases_agree_with_the_player(self):
        reg = R.load()
        cases = json.loads(CASES.read_text())
        self.assertGreater(len(cases), 20)
        for c in cases:
            r = reg.resolve(c["producer"], c["type"], c["source"])
            self.assertEqual((r.id, r.owner, r.via, r.key), (c["id"], c["owner"], c["via"], c["key"]), c)

    def test_ids_are_never_dropped_and_unknown_is_explicit(self):
        reg = R.load()
        self.assertEqual(reg.resolve("manual-test", "bloodbank.x.y.z").id, "unknown")
        self.assertEqual(reg.resolve("", None).via, "unknown")
        self.assertEqual(reg.resolve(None, None).id, "unknown")

    def test_extra_aliases_resolve_as_ids(self):
        reg = R.load()
        self.assertEqual(reg.canonical("copilot-cli"), "ext:copilot")
        self.assertEqual(reg.canonical("antigravity-cli"), "ext:antigravity")
        self.assertEqual(reg.name_of("ext:antigravity"), "Antigravity CLI")

    def test_every_producer_in_the_map_resolves_to_a_known_id(self):
        reg = R.load()
        known = set(reg.components) | set(reg.extras)
        for p in reg._exact:
            self.assertIn(reg._exact[p], known, p)


class Sources(unittest.TestCase):
    def setUp(self):
        self.reg = R.Registry.from_records(RECORDS, desks=DESKS, tenants=[{"producer": "tiller", "slug": "tiller"},
                                                                         {"producer": "local-script:*", "slug": "*"}])

    def test_relayed_events_land_on_the_claimant(self):
        r = self.reg.resolve("pjangler", "bloodbank.crank.binding.created", "urn:33god:service:crank")
        self.assertEqual((r.id, r.owner, r.via), ("crank", "crank", "source"))
        self.assertEqual(self.reg.resolve("pjangler", "bloodbank.repo.task.updated", "x").id, "pjangler")

    def test_source_and_type_must_both_match(self):
        n8n = "urn:33god:service:n8n-bloodbank-node"
        self.assertEqual(self.reg.resolve("n8n", "bloodbank.telephony.call.started", n8n).id, "delosip")
        self.assertEqual(self.reg.resolve("n8n", "bloodbank.telephony.call.started", "urn:other").id, "n8n")
        self.assertEqual(self.reg.resolve("n8n", "bloodbank.audio.file.received", n8n).id, "n8n")

    def test_a_missing_source_never_matches_a_source_pattern(self):
        self.assertEqual(self.reg.resolve("n8n", "bloodbank.telephony.call.started", None).id, "n8n")

    def test_a_source_claim_beats_a_tenant_and_a_producer(self):
        self.assertEqual(self.reg.resolve("tiller", "bloodbank.crank.x.y", "s").id, "crank")


class Desks(unittest.TestCase):
    def setUp(self):
        self.reg = R.Registry.from_records(RECORDS, desks=DESKS)

    def test_each_profile_gets_its_own_desk_owned_by_the_fleet(self):
        r = self.reg.resolve("hermes-agent:tolt-pm", "bloodbank.agent.tool.requested")
        self.assertEqual((r.id, r.owner, r.via, r.key), ("hermes-desk:tolt-pm", "hermes-fleet", "desk", "tolt-pm"))

    def test_momo_desks_go_to_the_momo_kiosk(self):
        r = self.reg.resolve("hermes-agent:genesis-momo", "bloodbank.agent.tool.requested")
        self.assertEqual((r.id, r.owner, r.key), ("momo", "momo", "genesis-momo"))

    def test_malformed_ids_share_one_unknown_desk(self):
        for p in ("hermes-agent:.hermes", "hermes-agent:runtime", "hermes-agent:v_hermes_home", "hermes-agent:", "hermes-agent"):
            r = self.reg.resolve(p, "bloodbank.agent.tool.requested")
            self.assertEqual((r.id, r.owner), ("hermes-desk:unknown", "hermes-fleet"), p)

    def test_desk_names(self):
        self.assertEqual(self.reg.name_of("hermes-desk:tolt-pm"), "tolt-pm")
        self.assertEqual(self.reg.name_of("hermes-desk:unknown"), "Hermes desk (unnamed)")


class Tenants(unittest.TestCase):
    def setUp(self):
        self.reg = R.Registry.from_records(RECORDS, tenants=[{"producer": "tiller", "slug": "tiller"},
                                                            {"producer": "local-script:*", "slug": "*"}])

    def test_tenant_slugs(self):
        self.assertEqual(self.reg.resolve("tiller").id, "tenant:tiller")
        r = self.reg.resolve("local-script:gruvato")
        self.assertEqual((r.id, r.owner, r.via, r.key), ("tenant:gruvato", None, "tenant", "gruvato"))

    def test_tenant_names(self):
        self.assertEqual(self.reg.name_of("tenant:gruvato"), "gruvato")


class Precedence(unittest.TestCase):
    def test_exact_producer_beats_a_glob_and_a_glob_beats_an_id(self):
        reg = R.Registry.from_records({"a": {"name": "A", "first_party": True, "producers": ["x*"]},
                                       "b": {"name": "B", "first_party": True, "producers": ["xy"]},
                                       "xz": {"name": "XZ", "first_party": True, "producers": []}})
        self.assertEqual(reg.resolve("xy").id, "b")
        self.assertEqual(reg.resolve("xz").id, "a")
        self.assertEqual(reg.resolve("xz").via, "producer")
        self.assertEqual(R.Registry.from_records({"xz": {"name": "XZ", "producers": []}}).resolve("xz").via, "id")

    def test_the_cache_does_not_mix_sources(self):
        reg = R.Registry.from_records(RECORDS)
        self.assertEqual(reg.resolve("n8n", "bloodbank.crank.a.b", "s").id, "crank")
        self.assertEqual(reg.resolve("n8n", "bloodbank.crank.a.b", None).id, "crank")
        self.assertEqual(reg.resolve("n8n", "bloodbank.other.a.b", "s").id, "n8n")

    def test_legacy_records_round_trip(self):
        recs = R.Registry.from_records(RECORDS).records
        self.assertIn("pjangler", recs["pjangler"]["producers"])
        self.assertEqual(R.resolver(RECORDS)("pjangler"), "pjangler")


if __name__ == "__main__":
    unittest.main()


NIGHT_REG = {
    "candybar": {"name": "Candybar", "first_party": True, "producers": ["candybar"]},
    "hermes-fleet": {"name": "Hermes Fleet", "first_party": True, "producers": ["hermes-agent", "hermes-agent:*"]},
    "agent-hooks": {"name": "Agent Hooks", "first_party": True, "producers": ["claude-code"]},
    "krebs": {"name": "Krebs", "first_party": True, "producers": []},
    "hindsight": {"name": "Hindsight", "first_party": True, "producers": []},
    "genesis": {"name": "Genesis", "first_party": True, "producers": []},
    "plane-hook": {"name": "Plane hook", "first_party": True, "producers": ["plane-ingress-reconcile"]},
}


class WorkerResolveTest(unittest.TestCase):
    """Moved from the retired night.py tests: the resolver and the Candybar-job / hook-handler credit."""

    def test_exact_beats_glob_and_glob_matches_desks(self):
        r = R.resolver(NIGHT_REG)
        self.assertEqual(r("hermes-agent"), "hermes-fleet")
        self.assertEqual(r("hermes-agent:gruvato-pm"), "hermes-fleet")
        self.assertIsNone(r("someone-else"))

    def test_workers_resolve_by_owner_prefix_and_manifest(self):
        who = R.worker_resolver(NIGHT_REG, R.resolver(NIGHT_REG), {"nightly-sweep": "genesis"}, {"bloodbank-publisher": "agent-hooks"})
        self.assertEqual(who("krebs-tick"), "krebs")
        self.assertEqual(who("hindsight-turn"), "hindsight")
        self.assertEqual(who("bloodbank-publisher"), "agent-hooks")
        self.assertEqual(who("nightly-sweep"), "genesis")
        self.assertIsNone(who("someone-px-dedupe-sweep"))

    def test_first_party_prefix_beats_third_party_and_client_manifests_beat_both(self):
        reg = dict(NIGHT_REG, **{"hindsight": {"name": "Hindsight", "first_party": False, "producers": []},
                                 "hindsight-ui": {"name": "Hindsight UI", "first_party": True, "producers": []}})
        who = R.worker_resolver(reg, R.resolver(reg), {"hindsight-client-sync": "/home/x/code/clientco"}, {})
        self.assertEqual(who("hindsight-turn"), "hindsight")              # a third-party service still gets its own work
        self.assertEqual(who("hindsight-ui-build"), "hindsight-ui")
        self.assertIsNone(who("hindsight-client-sync"))                   # a client repo's job: no prefix claims it

    def test_manifest_repo_beats_prefix_and_client_jobs_stay_put(self):
        who = R.worker_resolver(NIGHT_REG, R.resolver(NIGHT_REG), {
            "krebs-nightly-report": "/home/x/code/clientco",          # a client repo: never claimed by the krebs- prefix
            "genesis-rollup": "/home/x/code/33GOD/genesis",
        }, {})
        self.assertEqual(who("plane-ingress-reconcile"), "plane-hook")
        self.assertIsNone(who("krebs-nightly-report"))
        self.assertEqual(who("genesis-rollup"), "genesis")


class PublicProfileRulesTest(unittest.TestCase):
    def test_first_party_desk_keeps_its_name_others_alias(self):
        self.assertTrue(R.first_party_desk("33god-pm", NIGHT_REG))
        self.assertTrue(R.first_party_desk("krebs-pm", NIGHT_REG))
        self.assertFalse(R.first_party_desk("clientco-pm", NIGHT_REG))
        self.assertFalse(R.first_party_desk("krebsish", NIGHT_REG))

    def test_private_types_cover_messages_calls_and_money(self):
        for t in ("bloodbank.messaging.x", "bloodbank.telephony.y", "bloodbank.billing.transaction.z"):
            self.assertTrue(t.startswith(R.PRIVATE_TYPES), t)
        self.assertFalse("bloodbank.repo.task.created".startswith(R.PRIVATE_TYPES))
