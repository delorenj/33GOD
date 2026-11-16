"""show.render on the synthetic waybill (no live systems, no colour)."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_assemble import build  # noqa: E402
from waybill import show  # noqa: E402


def span(i: str, kind: str, name: str, t0: float, t1: float, parent: str | None = "turn", **kw) -> dict:
    d = {"id": i, "kind": kind, "component": "ext:claude-code", "name": name, "summary": name, "phase": "tool",
         "t0": t0, "t1": t1, "status": "ok", "parent": parent, "evidence": ["test"], "attrs": {}, "refs": {}}
    d.update(kw)
    return d


class TestShow(unittest.TestCase):
    def setUp(self) -> None:
        self.wb = build("full")
        self.out = show.render(self.wb, width=140, color=False)

    def test_header_and_sections(self) -> None:
        lines = self.out.splitlines()
        self.assertEqual(lines[0], self.wb["title"])
        self.assertIn("956a26e9", lines[1])
        self.assertIn("Findings (", self.out)
        self.assertIn("Gaps (", self.out)
        self.assertIn("Sources", self.out)

    def test_no_ansi_without_color(self) -> None:
        self.assertNotIn("\x1b[", self.out)
        coloured = show.render(self.wb, width=140, color=True)
        self.assertIn("\x1b[", coloured)

    def test_glyphs_and_bars(self) -> None:
        for glyph in ("✓", "·", "✗", "█", "▒", "◆"):
            self.assertIn(glyph, self.out)

    def test_width_is_respected(self) -> None:
        for width in (100, 120, 160):
            out = show.render(self.wb, width=width, color=False)
            over = [ln for ln in out.splitlines() if len(ln) > width]
            self.assertEqual(over, [], f"width {width}: {over[:2]}")

    def test_turn_sorts_first_and_names_present(self) -> None:
        body = [ln for ln in self.out.splitlines() if "│" in ln]
        self.assertIn("turn", body[1])  # body[0] is the column header
        for name in ("UserPromptSubmit", "hindsight-recall", "claude-opus"):
            self.assertIn(name, self.out)

    def test_fanout_line_for_published_events(self) -> None:
        self.assertIn("↳", self.out)
        self.assertIn("●", self.out)

    def test_tool_runs_collapse_and_all_expands(self) -> None:
        wb = copy.deepcopy(self.wb)
        wb["spans"] += [
            span("tool:t1", "tool", "Bash", 100, 200),
            span("tool:t2", "tool", "Read", 210, 300),
            span("tool:t3", "tool", "Bash", 310, 400),
        ]
        collapsed = show.render(wb, width=140, color=False)
        self.assertIn("▸ 3 tools", collapsed)
        self.assertIn("Bash×2", collapsed)
        full = show.render(wb, width=140, color=False, show_all=True)
        self.assertNotIn("▸ 3 tools", full)
        self.assertGreater(len(full.splitlines()), len(collapsed.splitlines()) - 1)

    def test_repeated_events_group(self) -> None:
        wb = copy.deepcopy(self.wb)
        for n in range(5):
            wb["events"].append({"id": f"ev-rep-{n}", "type": "bloodbank.agent.hook.updated", "subject": None,
                                 "stream": None, "seq": 9000 + n, "t": 500.0 + n * 10, "correlationid": None,
                                 "causationid": None, "producer": None, "publisher_span": None, "consumers": []})
        grouped = show.render(wb, width=140, color=False)
        self.assertIn("5× agent.hook.updated", grouped)
        expanded = show.render(wb, width=140, color=False, show_all=True)
        self.assertNotIn("5× agent.hook.updated", expanded)

    def test_open_span_and_empty_waybill(self) -> None:
        wb = copy.deepcopy(self.wb)
        wb["spans"].append(span("x:open", "file", "still going", 3000, None, status="pending"))
        self.assertIn("still going", show.render(wb, width=120, color=False))
        empty = copy.deepcopy(self.wb)
        empty["spans"], empty["events"], empty["links"] = [], [], []
        self.assertIsInstance(show.render(empty, width=120, color=False), str)

    def test_fmt_helpers(self) -> None:
        self.assertEqual(show._fmt_delta(1), "+1ms")
        neg = show._fmt_delta(-3880)
        self.assertTrue(neg[0] in "-\u2212", neg)
        self.assertNotIn("+", neg)


if __name__ == "__main__":
    unittest.main()
