"""Every domain colour the Atlas can ask for exists in every theme."""

from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "god_atlas_palette", Path(__file__).resolve().parents[1] / "scripts" / "atlas.py")
atlas = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atlas)


class PaletteTest(unittest.TestCase):
    def test_every_hue_is_defined_in_light_and_both_dark_blocks(self):
        css = atlas.TEMPLATE.read_text()
        for n in atlas.DOMAIN_HUES:
            with self.subTest(hue=n):
                self.assertEqual(len(re.findall(rf"--d{n}:\s*#[0-9a-f]{{6}}", css)), 3)

    def test_every_declared_domain_gets_its_own_colour(self):
        cfg, _ = atlas.load_atlas()
        self.assertLessEqual(len(cfg["domains"]), max(atlas.DOMAIN_HUES),
                             "more domains than --d tokens: add a validated hue to atlas/template.html")


if __name__ == "__main__":
    unittest.main()
