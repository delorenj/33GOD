#!/usr/bin/env python3
"""Verify the queued Atlas brief and Flume-generated advisory hire projection."""
import json
import pathlib
import unittest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
ROLE = ROOT / "agents/hermes/art-director/role.yaml"
SOUL = ROOT / "agents/hermes/art-director/SOUL.md"
BRIEF = ROOT / "33god-platform/atlas/ART-DIRECTOR-FIRST-BRIEF.md"


class ArtDirectorHireTest(unittest.TestCase):
    def test_one_new_advisory_post_preserves_pm_board(self):
        project = json.loads((ROOT / ".project.json").read_text())
        role = yaml.safe_load(ROLE.read_text())
        self.assertIn("33god-platform/atlas", role["purpose"])
        self.assertEqual(role["agent_id"], "33god-art-director")
        self.assertEqual(role["board_scope"], "advisory")
        self.assertFalse(role["reconcile"]["enabled"])
        self.assertEqual(role["telegram"]["provisioning_status"], "deferred")
        self.assertNotIn("project_id", role["plane"])
        self.assertNotIn("board_id", role["plane"])
        self.assertEqual(role["ticket_provider"]["board_id"], project["ticket_provider"]["board_id"])
        self.assertEqual(project["agents"]["33god-pm"]["role"], "pm")
        self.assertEqual(project["agents"]["33god-art-director"]["role"], "art-director")
        self.assertEqual([x for x in project["agents"] if x.endswith("art-director")], ["33god-art-director"])
        self.assertIn("Never read `atlas.json`", SOUL.read_text())

    def test_brief_is_queued_and_public_projection_only(self):
        body = BRIEF.read_text()
        for term in ("queued, not authorized for production", "typography, color, motion and illustration",
                     "Manual I-10", "FLUME-86", "FLUME-87", "mise run platform:atlas:check",
                     "only** `33god-platform/atlas/public.json`", "never the private `atlas.json` or component YAML",
                     "fix a hit in the registry", "manual personal-name/privacy review",
                     "does **not** clear the production gate"):
            self.assertIn(term.lower(), body.lower())


if __name__ == "__main__":
    unittest.main()
