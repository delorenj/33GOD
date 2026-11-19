"""The Factory cast (I-10): the registry says where every component stands on the 3D floor."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_spec = importlib.util.spec_from_file_location(
    "god_atlas_factory", Path(__file__).resolve().parents[1] / "scripts" / "atlas.py")
atlas = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atlas)

SETS = atlas.set_ids()


def rec(cid, **factory):
    return {"id": cid, "name": cid.title(), "kind": "service", "first_party": True, "domain": "G1", "level": "container",
            "parent": "", "status": "live", "summary": "Does a thing.", "role_in_system": "", "tech": [], "runtime": "",
            "public_card": {}, "relations": [], "evidence": ["x"], "notes": "", "surfaces": [], "factory": factory}


def errors(records, extras=None):
    cfg = {"factory_extras": extras or {}}
    return atlas.factory_errors(cfg, records)


class SetIdsTest(unittest.TestCase):
    def test_reads_the_factory_station_list_from_stations_ts(self):
        for s in ("bays", "courier", "dock", "labeldesk", "belt", "archive", "rules", "control", "cataloguer", "clock",
                  "crew", "entrance", "voxxy", "library", "staffing", "soundwing"):
            self.assertIn(s, SETS)
        self.assertEqual(len(SETS), len(set(SETS)))


class ValidateTest(unittest.TestCase):
    def test_a_station_or_a_near_passes(self):
        self.assertEqual(errors([rec("a", station="dock"), rec("b", near="dock", aliases=["b-old"])]), [])

    def test_exactly_one_of_station_and_near(self):
        self.assertTrue(errors([rec("a")]))
        self.assertTrue(errors([rec("a", station="dock", near="belt")]))

    def test_a_missing_block_is_an_error(self):
        r = rec("a")
        r["factory"] = {}
        self.assertTrue(any("no factory" in e for e in errors([r])))

    def test_unknown_set_and_unknown_key(self):
        self.assertTrue(any("not a Factory set" in e for e in errors([rec("a", station="moon")])))
        self.assertTrue(any("not a known key" in e for e in errors([rec("a", station="dock", place="x")])))

    def test_aliases_are_unique_and_never_a_registry_id(self):
        self.assertTrue(any("registry id" in e for e in errors([rec("a", station="dock", aliases=["b"]), rec("b", near="dock")])))
        self.assertTrue(any("already an alias" in e for e in errors([rec("a", station="dock", aliases=["old"]), rec("b", near="dock", aliases=["old"])])))
        self.assertTrue(any("factory_extras" in e for e in errors([rec("a", station="dock", aliases=["ext:x"])], {"ext:x": {"near": "bays", "name": "X"}})))

    def test_extras_need_one_placement_a_name_and_no_registry_collision(self):
        self.assertEqual(errors([rec("a", station="dock")], {"ext:x": {"station": "bays", "name": "X"}}), [])
        self.assertTrue(errors([rec("a", station="dock")], {"ext:x": {"name": "X"}}))
        self.assertTrue(errors([rec("a", station="dock")], {"ext:x": {"station": "bays", "name": " "}}))
        self.assertTrue(any("collides" in e for e in errors([rec("a", station="dock")], {"a": {"station": "bays", "name": "A"}})))


class CastTest(unittest.TestCase):
    cfg = {"factory_extras": {"ext:z": {"near": "bays", "name": "Z"}, "ext:a": {"station": "bays", "name": "A"}}}
    records = [rec("b", near="dock", aliases=["b-old", "b-older"]), rec("a", station="dock")]

    def test_shape_and_determinism(self):
        cast = atlas.cast_document(self.cfg, self.records)
        self.assertEqual((cast["format"], cast["version"]), ("33god.factory-cast", 1))
        self.assertEqual(list(cast["components"]), ["b", "a"])  # records arrive sorted from load_atlas; the cast keeps their order
        self.assertEqual(cast["components"]["a"], {"name": "A", "summary": "Does a thing.", "domain": "G1", "first_party": True,
                                                   "station": "dock", "near": None, "aliases": []})
        self.assertEqual(cast["aliases"], {"b-old": "b", "b-older": "b"})
        self.assertEqual(list(cast["extras"]), ["ext:a", "ext:z"])
        self.assertEqual(cast["extras"]["ext:z"], {"station": None, "near": "bays", "name": "Z"})
        self.assertEqual(cast, atlas.cast_document(self.cfg, self.records))

    def test_digest_moves_when_a_placement_moves(self):
        a = atlas.cast_document(self.cfg, self.records)["digest"]
        moved = [rec("b", near="belt", aliases=["b-old", "b-older"]), rec("a", station="dock")]
        self.assertNotEqual(a, atlas.cast_document(self.cfg, moved)["digest"])

    def test_cast_is_scrubbed_like_the_public_export(self):
        leaky = [rec("a", station="dock")]
        leaky[0]["summary"] = "listens on :8683 at api.delo.sh"
        self.assertTrue(atlas.cast_scrub_findings(atlas.cast_document(self.cfg, leaky)))
        self.assertEqual(atlas.cast_scrub_findings(atlas.cast_document(self.cfg, self.records)), [])


class RealRegistryTest(unittest.TestCase):
    """The committed registry and the committed cast agree, and the cast covers every component."""

    @classmethod
    def setUpClass(cls):
        cls.cfg, cls.records = atlas.load_atlas()

    def test_registry_is_valid_and_cast_is_fresh(self):
        self.assertEqual(atlas.all_errors(self.cfg, self.records), [])
        want = json.dumps(atlas.cast_document(self.cfg, self.records), indent=2, ensure_ascii=False) + "\n"
        self.assertEqual(atlas.OUT_CAST.read_text(), want, "cast.generated.json is stale: run atlas.py render")

    def test_every_component_has_exactly_one_placement(self):
        cast = atlas.cast_document(self.cfg, self.records)
        self.assertEqual(len(cast["components"]), len(self.records))
        for cid, c in cast["components"].items():
            self.assertEqual(sum(1 for k in ("station", "near") if c[k]), 1, cid)

    def test_no_alias_or_extra_is_a_registry_id(self):
        cast = atlas.cast_document(self.cfg, self.records)
        ids = set(cast["components"])
        self.assertFalse(ids & set(cast["aliases"]))
        self.assertFalse(ids & set(cast["extras"]))
        self.assertFalse(set(cast["aliases"]) & set(cast["extras"]))

    def test_check_names_a_stale_cast(self):
        good = json.dumps(atlas.cast_document(self.cfg, self.records), indent=2, ensure_ascii=False) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "cast.generated.json"
            with mock.patch.object(atlas, "OUT_CAST", fake):
                fake.write_text(good.replace('"station": "dock"', '"station": "belt"', 1))
                self.assertEqual(atlas.cmd_check(None), 1)  # a stale cast fails the check
                fake.write_text(good)
                self.assertEqual(atlas.cmd_check(None), 0)


if __name__ == "__main__":
    unittest.main()
