"""Atlas hubs lens: `skillex graph` joined to the registry on repository directory."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "god_atlas_hubs", Path(__file__).resolve().parents[1] / "scripts" / "atlas.py")
atlas = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atlas)


def node(nid, kind, name, root=None, health="ok", findings=(), **extra):
    return {"id": nid, "kind": kind, "name": name, "root": root, "health": health,
            "findings": list(findings), "source": extra.pop("source", None), **extra}


def rec(cid, parent="", level="container", first_party=True, status="live"):
    return {"id": cid, "parent": parent, "level": level, "first_party": first_party, "status": status}


COUNT = {"code": "W_SOURCE_HUB_COUNT", "severity": "warning", "message": "2 skills"}
GRAPH = {
    "summary": {"nodes": {"hub": 1, "vendored": 2, "subskill": 1}},
    "nodes": [
        node("skill:alpha", "hub", "alpha", "/r/alpha", source="alpha"),
        node("subskill:alpha/feat", "subskill", "alpha/feat"),
        node("skill:bus-a", "vendored", "bus-a", "/r/bus", source="bus"),
        node("skill:bus-b", "vendored", "bus-b", "/r/bus", source="bus"),
        node("skill:wild", "wild", "wild"),
        node("source:bus", "source", "bus", "/r/bus", health="warning", findings=[COUNT], hubs=["bus-a", "bus-b"]),
        node("skill:stray", "hub", "stray", "/r/nowhere"),
    ],
    "edges": [
        {"from": "skill:alpha", "to": "subskill:alpha/feat", "kind": "routes"},
        {"from": "skill:alpha", "to": "skill:wild", "kind": "loads"},
    ],
}
RECORDS = [rec("alpha"), rec("bus"), rec("bus-part", parent="bus", level="component"), rec("lonely"),
           rec("gone", status="retired")]
REPOS = {"alpha": Path("/r/alpha"), "bus": Path("/r/bus"), "bus-part": Path("/r/bus"), "lonely": Path("/r/lonely"),
         "gone": Path("/r/gone")}


class HubsDocumentTest(unittest.TestCase):
    def setUp(self):
        self.doc = atlas.hubs_document(GRAPH, RECORDS, REPOS)
        self.hub = {h["name"]: h for h in self.doc["hubs"]}

    def test_a_hub_joins_its_component_with_sub_skills_and_loads(self):
        alpha = self.hub["alpha"]
        self.assertEqual(alpha["components"], ["alpha"])
        self.assertEqual(alpha["subskills"], ["feat"])
        self.assertEqual(alpha["loads"], ["wild"])
        self.assertEqual(self.doc["components"]["alpha"]["health"], "ok")

    def test_a_shared_repo_belongs_to_the_container_and_its_one_hub_finding_shows_on_every_hub(self):
        self.assertEqual(self.hub["bus-a"]["components"], ["bus"])
        for name in ("bus-a", "bus-b"):
            self.assertEqual(self.hub[name]["health"], "warning")
            self.assertIn("W_SOURCE_HUB_COUNT", self.hub[name]["codes"])
        self.assertEqual(self.doc["components"]["bus-part"]["hubs"], ["bus-a", "bus-b"])
        self.assertEqual(self.doc["components"]["bus"]["repo_hubs"], ["bus-a", "bus-b"])

    def test_gaps_both_ways(self):
        self.assertEqual(self.doc["unjoined"], ["stray"])
        self.assertEqual(self.doc["no_hub"], ["lonely"], "a retired component is not a gap")
        self.assertNotIn("wild", self.hub)

    def test_the_committed_render_keeps_the_hubs_placeholder_empty(self):
        self.assertIn("/*HUBS_DATA*/null", atlas.TEMPLATE.read_text())
        html = atlas.render_hubs_html({"components": []}, {"x": "</script>"})
        self.assertNotIn("/*HUBS_DATA*/null", html)
        self.assertNotIn('"</script>"', html)


if __name__ == "__main__":
    unittest.main()
