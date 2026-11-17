"""Atlas drift audit (I-12): evidence anchors, surface coverage, status."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_spec = importlib.util.spec_from_file_location(
    "god_atlas_audit", Path(__file__).resolve().parents[1] / "scripts" / "atlas.py")
atlas = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atlas)


def rec(cid="x", status="live", surfaces=(), relations=()):
    return {"id": cid, "status": status, "surfaces": list(surfaces), "relations": list(relations),
            "evidence": []}


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / "svc.py"
        self.file.write_text("import os\n\nclient.publish('bloodbank.evt.x', body)\n")

    def tearDown(self):
        self.tmp.cleanup()

    def rel(self, line, anchor="client.publish('bloodbank.evt.x', body)"):
        return {"to": "y", "kind": "publishes-to", "evidence": f"{self.file}:{line}", "anchor": anchor}

    def test_anchor_on_cited_line_is_ok(self):
        self.assertEqual(atlas.check_relation_evidence({}, self.rel(3))[0], "ok")

    def test_anchor_that_moved_heals_to_its_new_line(self):
        self.file.write_text("import os\nimport sys\n\n\nclient.publish('bloodbank.evt.x', body)\n")
        state, _, line = atlas.check_relation_evidence({}, self.rel(3))
        self.assertEqual((state, line), ("moved", 5))

    def test_anchor_that_vanished_needs_a_person(self):
        self.file.write_text("import os\n\nclient.call('somewhere-else')\n")
        self.assertEqual(atlas.check_relation_evidence({}, self.rel(3))[0], "gone")

    def test_missing_file_and_prose_evidence(self):
        self.assertEqual(atlas.check_relation_evidence({}, {"evidence": "/nope/x.py:1"})[0], "gone")
        self.assertEqual(atlas.check_relation_evidence({}, {"evidence": "see the README"})[0], "unverifiable")
        self.assertEqual(atlas.check_relation_evidence({}, {"evidence": "live: docker ps"})[0], "ok")

    def test_anchor_never_records_secret_shaped_text(self):
        self.assertIsNone(atlas.anchor_for("API_KEY = 'sk-abcdefgh12345678'"))
        self.assertIsNone(atlas.anchor_for("x = 1"))


class CoverageTest(unittest.TestCase):
    def run_audit(self, records, found, ignore=(), live=True):
        cfg = {"atlas_ignore": list(ignore)}
        surfaces = {k: set() for k in atlas.SURFACE_KINDS}
        for k, names in found.items():
            surfaces[k] |= set(names)
        with mock.patch.object(atlas, "discover", return_value=(surfaces, [])), \
             mock.patch.object(atlas, "all_errors", return_value=[]), \
             mock.patch.object(atlas, "outputs", return_value={}):
            return atlas.audit(cfg, records, live)

    def kinds(self, report):
        return sorted((f["kind"], f["subject"]) for f in report["findings"])

    def test_unclaimed_surface_is_flagged(self):
        report = self.run_audit([rec()], {"container": ["mystery-db"]})
        self.assertIn(("unregistered", "container:mystery-db"), self.kinds(report))
        self.assertEqual(report["needs_human"], 1)

    def test_glob_claim_and_ignore_cover_surfaces(self):
        records = [rec(surfaces=["container:plane-*"])]
        ignore = [{"kind": "container", "pattern": "jellyfin*", "reason": "household media"}]
        report = self.run_audit(records, {"container": ["plane-api", "jellyfin"]}, ignore)
        self.assertEqual(report["findings"], [])

    def test_status_drift_both_directions(self):
        records = [rec("down", "live", ["systemd:down.service"]),
                   rec("ghost", "planned", ["systemd:ghost.service"])]
        report = self.run_audit(records, {"systemd": ["ghost.service"]})
        self.assertEqual(self.kinds(report), [("status", "down"), ("status", "ghost")])

    def test_digest_is_stable_for_the_same_findings(self):
        a = self.run_audit([rec()], {"container": ["b", "a"]})
        b = self.run_audit([rec()], {"container": ["a", "b"]})
        self.assertEqual(a["digest"], b["digest"])


if __name__ == "__main__":
    unittest.main()
