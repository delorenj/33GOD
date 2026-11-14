"""The Atlas public export must never carry internal detail (I-12 scrub rule)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "god_atlas", Path(__file__).resolve().parents[1] / "scripts" / "atlas.py")
atlas = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atlas)


def doc(**component):
    base = {"id": "x", "name": "X", "kind": "service", "first_party": True, "domain": "G1",
            "level": "container", "parent": "", "status": "live", "summary": "Does a thing.",
            "role_in_system": "", "tech": [], "runtime": "", "public_card": {}}
    base.update(component)
    return {"registry_digest": "d", "system": {"id": "33god", "name": "33GOD", "summary": ""},
            "domains": [{"id": "G1", "name": "Bus"}], "people": [],
            "components": [base], "edges": [{"from": "x", "to": "x", "kind": "calls", "via": "POST :8683/x"}]}


class ScrubTest(unittest.TestCase):
    def test_drops_private_fields_and_wire_mechanisms(self):
        public = atlas.showcase_document(doc(runtime="/home/delorenj/x on big-chungus"))
        self.assertNotIn("runtime", public["components"][0])
        self.assertNotIn("role_in_system", public["components"][0])
        self.assertEqual(public["edges"], [{"from": "x", "to": "x", "kind": "calls"}])

    def test_flags_internal_detail_in_public_text(self):
        for leak in ("routes api.delo.sh", "listens on :8683", "reads ~/code/x", "see main.py",
                     "box big-chungus", "on 192.168.1.10", "emits bloodbank.evt.agent.done", "op://vault"):
            with self.subTest(leak=leak):
                self.assertTrue(atlas.scrub_findings(atlas.showcase_document(doc(summary=leak))))

    def test_clean_text_passes(self):
        clean = "Carries every event between agents and the people who run them."
        self.assertEqual(atlas.scrub_findings(atlas.showcase_document(doc(summary=clean))), [])


if __name__ == "__main__":
    unittest.main()
