"""Atlas Graph view: every relation kind has a legend entry and a style, and the render carries the view."""

from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "god_atlas_graph", Path(__file__).resolve().parents[1] / "scripts" / "atlas.py")
atlas = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atlas)

DEFAULT_ON = {"calls", "publishes-to", "consumes-from", "reads", "writes", "stores-in", "routes-llm-via"}


def edge_kinds() -> dict[str, dict[str, str]]:
    """The template's EDGE_KINDS table: kind -> {fam, dash, on}."""
    text = atlas.TEMPLATE.read_text()
    block = re.search(r"const EDGE_KINDS = \{(.*?)\n  \};", text, re.S)
    assert block, "atlas/template.html: no `const EDGE_KINDS = {...};` table"
    rows = re.findall(r"'([a-z-]+)':\s*\{\s*fam:\s*'(\w+)',\s*dash:\s*'([^']*)',\s*on:\s*(true|false)\s*\}", block.group(1))
    return {k: {"fam": f, "dash": d, "on": on} for k, f, d, on in rows}


class LegendTest(unittest.TestCase):
    def setUp(self):
        self.kinds = edge_kinds()

    def test_every_relation_kind_has_a_legend_entry(self):
        self.assertEqual(set(self.kinds), atlas.RELATION_KINDS)

    def test_every_kind_used_in_the_registry_is_styled(self):
        _, records = atlas.load_atlas()
        used = {rel["kind"] for r in records for rel in r["relations"]}
        self.assertLessEqual(used, set(self.kinds))

    def test_default_on_kinds(self):
        self.assertEqual({k for k, v in self.kinds.items() if v["on"] == "true"}, DEFAULT_ON)

    def test_each_kind_draws_differently(self):
        styles = [(v["fam"], v["dash"]) for v in self.kinds.values()]
        self.assertEqual(len(styles), len(set(styles)), "two relation kinds share a colour family and dash")

    def test_every_colour_family_is_defined_in_light_and_both_dark_blocks(self):
        css = atlas.TEMPLATE.read_text()
        for fam in {v["fam"] for v in self.kinds.values()}:
            with self.subTest(fam=fam):
                self.assertEqual(len(re.findall(rf"--e-{fam}:\s*#[0-9a-f]{{6}}", css)), 3)
                self.assertIn(f".f-{fam} {{ --ec: var(--e-{fam}); }}", css)


class RenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg, records = atlas.load_atlas()
        cls.doc = atlas.atlas_document(cfg, records)
        cls.html = atlas.render_html(cls.doc)

    def test_the_render_contains_the_graph_view(self):
        for needle in ('data-view="graph"', 'id="view-graph"', 'id="gSvg"', 'id="gKinds"', 'id="gDomains"'):
            self.assertIn(needle, self.html)
        self.assertIn("'graph'", re.search(r"const VIEWS = \[[^\]]*\]", self.html).group(0))

    def test_the_committed_render_is_current(self):
        self.assertEqual(atlas.OUT_HTML.read_text(), self.html, "atlas/index.html is stale; run atlas.py render")

    def test_graph_is_self_contained_and_deterministic(self):
        self.assertNotIn("Math.random", self.html)
        self.assertNotRegex(self.html, r"<script[^>]+src=")

    def test_hub_layer_appears_only_with_hubs(self):
        self.assertIn("const HUBS = /*HUBS_DATA*/null;", self.html)
        hubs = {"schema": 1, "graph_page": "https://skills.delo.sh/?context=catalog", "summary": {"nodes": {}}, "hubs": [], "components": {},
                "unjoined": [], "no_hub": []}
        self.assertIn('"graph_page": "https://skills.delo.sh/?context=catalog"', atlas.render_hubs_html(self.doc, hubs))
        self.assertRegex(atlas.TEMPLATE.read_text(), r"hubList = HUBS \?")


if __name__ == "__main__":
    unittest.main()
