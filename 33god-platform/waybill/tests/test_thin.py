"""thin_to_budget keeps the document valid and referentially intact, and says what it dropped."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_assemble import build  # noqa: E402
from test_schema import SCHEMA, validate  # noqa: E402
from waybill.assemble import thin_to_budget, _size  # noqa: E402


class ThinTest(unittest.TestCase):
    def test_noop_when_under_budget(self):
        wb = build("public")
        n = len(wb["spans"])
        thin_to_budget(wb, _size(wb) + 10)
        self.assertEqual(len(wb["spans"]), n)

    def test_tiny_budget_stays_valid(self):
        wb = build("public")
        thin_to_budget(wb, 1)
        self.assertEqual(validate(wb, SCHEMA, SCHEMA), [])
        ids = {s["id"] for s in wb["spans"]} | {"evt:" + e["id"] for e in wb["events"]}
        self.assertEqual([ln for ln in wb["links"] if ln["from"] not in ids or ln["to"] not in ids], [])
        self.assertTrue(all(s["parent"] in ids for s in wb["spans"] if s.get("parent")))
        self.assertTrue(all(s["payload"] in wb["artifacts"] for s in wb["spans"] if s.get("payload")))
        self.assertEqual(wb["stats"]["spans"], len(wb["spans"]))
        self.assertIn("thinned", wb["gaps"][-1]["what"])


if __name__ == "__main__":
    unittest.main()
