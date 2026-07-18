from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DRIFT_CHECK = ROOT / "scripts/check-doc-drift.py"
SPEC = importlib.util.spec_from_file_location("check_doc_drift", DRIFT_CHECK)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load drift checker from {DRIFT_CHECK}")
check_doc_drift = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_doc_drift)


class EcosystemAuthorityDriftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.current = (ROOT / "skills/ecosystem/SKILL.md").read_text(
            encoding="utf-8"
        )

    def test_current_ecosystem_authority_contract_passes(self) -> None:
        self.assertEqual(check_doc_drift.ecosystem_authority_errors(self.current), [])

    def test_ambiguous_ticket_lifecycle_route_is_rejected(self) -> None:
        ambiguous = self.current.replace(
            "| Plane ticket/work-item and board/lane records | "
            "`project-lifecycle` (Plane mutations only) | "
            "Plane API / board state; never Lifecycle authority state |",
            "| Ticket lifecycle | `project-lifecycle` | Plane API / board state |",
        )
        errors = check_doc_drift.ecosystem_authority_errors(ambiguous)
        self.assertTrue(any("ambiguously maps Ticket lifecycle" in item for item in errors))

    def test_unscoped_project_lifecycle_route_is_rejected(self) -> None:
        unscoped = self.current + "\n| Lifecycle state change | `project-lifecycle` | none |\n"
        errors = check_doc_drift.ecosystem_authority_errors(unscoped)
        self.assertTrue(
            any("without Plane ticket/board scope" in item for item in errors)
        )

    def test_unscoped_plain_frontmatter_route_is_rejected(self) -> None:
        unscoped = self.current.replace(
            "Plane ticket/work-item and board/lane operations "
            "(project-lifecycle, never Lifecycle authority)",
            "deterministic lifecycle operations (project-lifecycle)",
        )
        errors = check_doc_drift.ecosystem_authority_errors(unscoped)
        self.assertTrue(
            any(
                "missing ownership statement: Plane ticket/work-item" in item
                for item in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
