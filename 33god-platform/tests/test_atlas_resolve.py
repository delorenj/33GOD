"""The resolver map (I-10.2): `source:` surfaces, tenants and desk families, rendered into the Factory cast."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "god_atlas_resolve", Path(__file__).resolve().parents[1] / "scripts" / "atlas.py")
atlas = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atlas)


def rec(cid, *surfaces):
    return {"id": cid, "name": cid.title(), "kind": "service", "first_party": True, "domain": "G1", "level": "container",
            "parent": "", "status": "live", "summary": "Does a thing.", "role_in_system": "", "tech": [], "runtime": "",
            "public_card": {}, "relations": [], "evidence": ["x"], "notes": "", "surfaces": list(surfaces),
            "factory": {"near": "dock"}}


CFG = {
    "factory_extras": {"tenant-annex": {"near": "entrance", "name": "Tenant annex"}, "ext:x": {"near": "bays", "name": "X", "aliases": ["x-cli"]}},
    "atlas_ignore": [{"kind": "producer", "pattern": "tiller", "tenant": "tiller"},
                     {"kind": "producer", "pattern": "local-script:*", "tenant": "*"},
                     {"kind": "container", "pattern": "gib-*"}],
    "factory_desks": {"hermes-desk": {"owner": "fleet", "producer": "hermes-agent:", "bare": ["hermes-agent"], "near": "crew",
                                      "name": "Hermes desk", "instance": "^[a-z0-9][a-z0-9-]*$", "malformed": ["runtime"],
                                      "routes": {"*-momo": "momo"}}},
}


def recs(*extra):
    return [rec("fleet", "producer:hermes-agent*"), rec("momo"), rec("crank", "source:*#crank.*"), *extra]


class SurfaceRulesTest(unittest.TestCase):
    def test_source_surfaces_split_into_source_and_type(self):
        sources, _ = atlas.surface_rules([rec("crank", "source:*#crank.*"), rec("delosip", "source:urn:33god:service:n8n-*#telephony.*", "source:urn:x")])
        self.assertIn({"source": "*", "type": "crank.*", "id": "crank"}, sources)
        self.assertIn({"source": "urn:x", "type": None, "id": "delosip"}, sources)

    def test_typed_rules_sort_before_untyped_then_longer_first(self):
        sources, _ = atlas.surface_rules([rec("a", "source:urn:long-pattern-here"), rec("b", "source:*#x.*"), rec("c", "source:*#audio.earshot.*")])
        self.assertEqual([s["id"] for s in sources], ["c", "b", "a"])

    def test_producers_sort_exact_before_glob_and_longer_glob_first(self):
        _, producers = atlas.surface_rules([rec("a", "producer:ab*"), rec("b", "producer:abc*"), rec("c", "producer:zz")])
        self.assertEqual([p["id"] for p in producers], ["c", "b", "a"])


class ResolveErrorsTest(unittest.TestCase):
    def errs(self, records, cfg=CFG):
        return atlas.resolve_errors(cfg, records)

    def test_the_fixture_is_clean(self):
        self.assertEqual(self.errs(recs()), [])

    def test_source_syntax_errors(self):
        for bad in ("source:", "source:#crank.*", "source:*#", "source:* #x", "source:*#bloodbank.crank.*", "source:a#b#c"):
            self.assertTrue(self.errs(recs(rec("bad", bad))), bad)

    def test_producer_globs_reject_brackets_and_spaces(self):
        self.assertTrue(self.errs(recs(rec("bad", "producer:a[bc]"))))
        self.assertTrue(self.errs(recs(rec("bad", "producer:a b"))))

    def test_two_components_cannot_claim_one_source_or_producer(self):
        self.assertTrue(any("claimed by both" in e for e in self.errs(recs(rec("dup", "source:*#crank.*")))))
        self.assertTrue(any("claimed by both" in e for e in self.errs(recs(rec("dup", "producer:hermes-agent*")))))

    def test_tenants_need_the_annex_extra(self):
        cfg = {**CFG, "factory_extras": {"ext:x": {"near": "bays", "name": "X"}}}
        self.assertTrue(any("tenant-annex" in e for e in self.errs(recs(), cfg)))

    def test_desk_family_validation(self):
        def with_desk(**kw):
            d = {**CFG["factory_desks"]["hermes-desk"], **kw}
            return {**CFG, "factory_desks": {"hermes-desk": d}}
        self.assertTrue(any("owner" in e for e in self.errs(recs(), with_desk(owner="nobody"))))
        self.assertTrue(any("near" in e for e in self.errs(recs(), with_desk(near="moon"))))
        self.assertTrue(any("regex" in e for e in self.errs(recs(), with_desk(instance="(["))))
        self.assertTrue(any("route" in e for e in self.errs(recs(), with_desk(routes={"*-momo": "ghost"}))))
        self.assertTrue(any("not a known key" in e for e in self.errs(recs(), with_desk(colour="red"))))


class ResolveDocumentTest(unittest.TestCase):
    def test_order_and_shape(self):
        doc = atlas.resolve_document(CFG, recs())
        self.assertEqual(doc["order"], ["source", "tenant", "desk", "producer", "id"])
        self.assertEqual(doc["tenants"]["annex"], "tenant-annex")
        self.assertEqual([t["slug"] for t in doc["tenants"]["rules"]], ["tiller", "*"])
        self.assertEqual(doc["desks"]["hermes-desk"]["routes"], [{"instance": "*-momo", "id": "momo"}])
        self.assertEqual(doc["sources"], [{"source": "*", "type": "crank.*", "id": "crank"}])

    def test_the_cast_carries_it_and_extra_aliases(self):
        cast = atlas.cast_document(CFG, recs())
        self.assertIn("resolve", cast)
        self.assertEqual(cast["aliases"]["x-cli"], "ext:x")

    def test_resolve_changes_move_the_digest(self):
        a = atlas.cast_document(CFG, recs())["digest"]
        b = atlas.cast_document(CFG, recs(rec("more", "source:*#more.*")))["digest"]
        self.assertNotEqual(a, b)

    def test_the_public_cast_scrub_reads_resolve_patterns(self):
        cast = atlas.cast_document(CFG, recs())
        self.assertEqual(atlas.cast_scrub_findings(cast), [])


if __name__ == "__main__":
    unittest.main()
