from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path


PLATFORM_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PLATFORM_ROOT / "scripts" / "validate-compose.py"
FIXTURE = PLATFORM_ROOT / "tests" / "fixtures" / "invalid-compose.json"
SPEC = importlib.util.spec_from_file_location("validate_compose", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ComposeSemanticValidationTests(unittest.TestCase):
    def test_failure_fixture_is_rejected_with_actionable_errors(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--rendered-json", str(FIXTURE), "--model", "default"],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("forbidden service bloodbank-candystore", result.stderr)
        self.assertIn("forbidden service platform-ready", result.stderr)
        self.assertIn("Candystore must have exactly postgres/app/daprd", result.stderr)

    def test_all_live_renders_pass_the_semantic_contract(self) -> None:
        source_root = Path(os.environ.get("GOD_SOURCE_ROOT", PLATFORM_ROOT.parent))
        required = [source_root / name for name in ("bloodbank", "candystore", "holocene", "pjangler")]
        if not all(path.is_dir() for path in required):
            self.skipTest("set GOD_SOURCE_ROOT to a populated 33GOD monorepo")
        models = VALIDATOR.render_models(PLATFORM_ROOT / "compose.yaml", source_root)
        self.assertEqual(set(models), {"default", "tools", "full", "cloud"})
        errors = [
            error
            for model_name, model in models.items()
            for error in VALIDATOR.validate_model(model_name, model, source_root.resolve())
        ]
        self.assertEqual(errors, [])

    def test_unpopulated_source_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "not a populated 33GOD monorepo"):
            VALIDATOR.render_models(PLATFORM_ROOT / "compose.yaml", PLATFORM_ROOT / "tests" / "fixtures")


if __name__ == "__main__":
    unittest.main()
