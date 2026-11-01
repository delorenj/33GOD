"""Bounded read-only Stitch skill contract checks."""

import importlib.util
import contextlib
import io
from unittest.mock import patch
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "platform.py"
spec = importlib.util.spec_from_file_location("platform", MODULE)
platform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(platform)


class RequiredContractTests(unittest.TestCase):
    def test_bounded_content_and_membership(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "all-skills/stitch").mkdir(parents=True)
            (root / "all-skills/stitch/SKILL.md").write_text("handoff.md\n", encoding="utf-8")
            (root / "sets/min-global").mkdir(parents=True)
            (root / "sets/min-global/stitch").symlink_to("../../all-skills/stitch")
            manifest = {
                "external_root": str(root),
                "required_contents": {"all-skills/stitch/SKILL.md": ["handoff.md"]},
                "required_symlinks": {"sets/min-global/stitch": "../../all-skills/stitch"},
            }
            self.assertEqual(platform.check_required_contract(manifest), ("OK", []))
            (root / "all-skills/stitch/SKILL.md").write_text("old handoff\n", encoding="utf-8")
            status, findings = platform.check_required_contract(manifest)
            self.assertEqual(status, "STALE")
            self.assertIn("missing 'handoff.md'", findings[0])
            (root / "sets/min-global/stitch").unlink()
            status, findings = platform.check_required_contract(manifest)
            self.assertEqual(status, "STALE")
            self.assertTrue(any("expected symlink" in item for item in findings))

    def test_missing_external_root_is_not_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = {"external_root": str(Path(temp) / "missing")}
            status, findings = platform.check_required_contract(manifest)
            self.assertEqual(status, "NOT VERIFIED")
            self.assertIn("external source unavailable", findings[0])

    def test_required_checks_without_root_are_not_verified(self):
        status, findings = platform.check_required_contract({
            "required_contents": {"all-skills/stitch/SKILL.md": ["handoff.md"]},
        })
        self.assertEqual(status, "NOT VERIFIED")
        self.assertIn("external_root missing", findings[0])

    def test_outside_paths_cannot_certify_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "source"
            root.mkdir()
            outside = base / "outside"
            outside.mkdir()
            (outside / "SKILL.md").write_text("contract", encoding="utf-8")
            (root / "alias").symlink_to(outside, target_is_directory=True)
            for name in [str(outside / "SKILL.md"), "../outside/SKILL.md", "alias/SKILL.md"]:
                with self.subTest(name=name):
                    status, findings = platform.check_required_contract({
                        "external_root": str(root),
                        "required_contents": {name: ["contract"]},
                    })
                    self.assertEqual(status, "STALE")
                    self.assertTrue(findings)

    def test_unverified_source_stays_visible_alongside_forbidden_match(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "backfills").mkdir()
            (root / "backfills/check.yaml").touch()
            with patch.object(platform, "ROOT", root), \
                 patch.object(platform, "scan_backfill", return_value=("fixture", ["forbidden match"])), \
                 patch.object(platform, "load_yaml", return_value={}), \
                 patch.object(platform, "check_required_contract", return_value=("NOT VERIFIED", ["source missing"])):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(platform.cmd_backfills_check(None), 1)
                self.assertIn("NOT VERIFIED fixture", output.getvalue())
                self.assertIn("forbidden match", output.getvalue())
                self.assertIn("source missing", output.getvalue())

    def test_broken_symlink_is_not_healthy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "sets/min-global").mkdir(parents=True)
            (root / "sets/min-global/stitch").symlink_to("../../all-skills/stitch")
            status, findings = platform.check_required_contract({
                "external_root": str(root),
                "required_symlinks": {"sets/min-global/stitch": "../../all-skills/stitch"},
            })
            self.assertEqual(status, "STALE")
            self.assertTrue(findings)


if __name__ == "__main__":
    unittest.main()
