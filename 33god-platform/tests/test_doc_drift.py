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
        cls.current = (ROOT / "skills/ecosystem/SKILL.md").read_text(encoding="utf-8")

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
        self.assertTrue(
            any("ambiguously maps Ticket lifecycle" in item for item in errors)
        )

    def test_unscoped_project_lifecycle_route_is_rejected(self) -> None:
        unscoped = (
            self.current + "\n| Lifecycle state change | `project-lifecycle` | none |\n"
        )
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


class BloodbankApiContractDriftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.current = (ROOT / "docs/api-contracts-bloodbank.md").read_text(
            encoding="utf-8"
        )

    def test_current_api_contract_passes(self) -> None:
        self.assertEqual(
            check_doc_drift.bloodbank_api_contract_errors(self.current), []
        )

    def test_missing_subject_binding_claim_is_rejected(self) -> None:
        stale = self.current.replace(
            "`assert_contract()` invokes `assert_subject_matches()`",
            "`assert_contract()` does not call `assert_subject_matches()`",
        )
        errors = check_doc_drift.bloodbank_api_contract_errors(stale)
        self.assertTrue(any("missing subject/type binding" in item for item in errors))

    def test_absent_holocene_client_claim_is_rejected(self) -> None:
        stale = self.current.replace(
            "Holocene has an implemented\nBloodbank command client",
            "Holocene has no functioning Bloodbank command client",
        )
        errors = check_doc_drift.bloodbank_api_contract_errors(stale)
        self.assertTrue(
            any("absent Holocene Bloodbank client" in item for item in errors)
        )

    def test_planned_lifecycle_topology_claim_is_rejected(self) -> None:
        stale = self.current.replace(
            "Root Compose runs the standalone Lifecycle authority",
            "Lifecycle still needs to be added to Root Compose",
        )
        errors = check_doc_drift.bloodbank_api_contract_errors(stale)
        self.assertTrue(
            any("planned or absent Lifecycle topology" in item for item in errors)
        )

    def test_unregistered_schema_claim_is_rejected(self) -> None:
        stale = self.current.replace(
            "The\nschemas above are registered and operational",
            "Lifecycle schemas are unregistered and not operational",
        )
        errors = check_doc_drift.bloodbank_api_contract_errors(stale)
        self.assertTrue(
            any("unregistered Lifecycle schemas" in item for item in errors)
        )

    def test_noncanonical_pjangler_claim_is_rejected(self) -> None:
        stale = self.current.replace(
            "PJangler's generators use fixed\nsix-token canonical subjects",
            "PJangler remains noncanonical on Bloodbank subjects",
        )
        errors = check_doc_drift.bloodbank_api_contract_errors(stale)
        self.assertTrue(any("noncanonical PJangler routing" in item for item in errors))

    def test_shared_reconcile_claim_is_rejected(self) -> None:
        stale = self.current + "\nMomo/Hermes and Lifecycle share one reconcile loop.\n"
        errors = check_doc_drift.bloodbank_api_contract_errors(stale)
        self.assertTrue(any("shared reconcile authority" in item for item in errors))

    def test_client_authority_overclaim_is_rejected(self) -> None:
        stale = self.current + "\nPlane writes deterministic Lifecycle truth.\n"
        errors = check_doc_drift.bloodbank_api_contract_errors(stale)
        self.assertTrue(
            any("client lifecycle authority overclaim" in item for item in errors)
        )


if __name__ == "__main__":
    unittest.main()
