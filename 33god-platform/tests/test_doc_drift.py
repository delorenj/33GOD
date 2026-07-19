from __future__ import annotations

import importlib.util
import hashlib
import shutil
import tempfile
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


class AuthorityParityDriftTests(unittest.TestCase):
    @staticmethod
    def copy_momo_workflow_fixture(root: Path) -> None:
        for relative in (
            Path("_bmad/custom/workflows/ticket-lifecycle"),
            Path("_bmad/_config/custom/custom/workflows/ticket-lifecycle"),
        ):
            shutil.copytree(ROOT / "momo" / relative, root / "momo" / relative)
        config = root / "momo/_bmad/_config"
        config.mkdir(parents=True, exist_ok=True)
        for manifest in ("workflow-manifest.csv", "files-manifest.csv"):
            shutil.copy2(ROOT / "momo/_bmad/_config" / manifest, config / manifest)

    def test_current_authority_json_artifacts_are_scanned(self) -> None:
        for relative in check_doc_drift.CURRENT_AUTHORITY_JSON_ARTIFACTS:
            current = (ROOT / relative).read_text(encoding="utf-8")
            self.assertEqual(
                check_doc_drift.authority_parity_text_errors(relative, current),
                [],
            )
        stale = current.replace(
            "Holocene web dashboard/renderer",
            "Holocene web/control plane",
        )
        self.assertNotEqual(stale, current)
        errors = check_doc_drift.authority_parity_text_errors(
            "docs/project-scan-report.json",
            stale,
        )
        self.assertTrue(any("Holocene control-plane role" in item for item in errors))

    def test_current_deployment_artifacts_have_no_rejected_ceremony(self) -> None:
        errors: list[str] = []
        for relative in check_doc_drift.CURRENT_DEPLOYMENT_ARTIFACTS:
            text = (ROOT / relative).read_text(encoding="utf-8")
            errors.extend(check_doc_drift.authority_parity_text_errors(relative, text))
        self.assertEqual(errors, [])

    def test_holocene_control_plane_labels_are_rejected(self) -> None:
        for stale in (
            "Holocene is the 33GOD control plane.",
            "role: control-plane-dashboard",
            "Control plane: Holocene and platform manifests.",
        ):
            with self.subTest(stale=stale):
                errors = check_doc_drift.authority_parity_text_errors(
                    "33god-platform/components/holocene.yaml", stale
                )
                self.assertTrue(
                    any("Holocene control-plane role" in item for item in errors)
                )

    def test_momo_shared_reconcile_and_truth_claims_are_rejected(self) -> None:
        stale_claims = {
            "Momo and Lifecycle share one reconcile loop.": "shared Momo reconcile loop",
            "Momo shares Lifecycle's reconcile loop.": "shared Momo reconcile loop",
            "Momo determines lifecycle truth.": "Momo determines lifecycle truth",
        }
        for stale, label in stale_claims.items():
            with self.subTest(stale=stale):
                errors = check_doc_drift.authority_parity_text_errors(
                    "docs/integration-architecture.md", stale
                )
                self.assertTrue(any(label in item for item in errors))

    def test_non_lifecycle_component_authority_roles_are_rejected(self) -> None:
        for stale in (
            "Candystore is the lifecycle writer.",
            "PJangler provides a lifecycle engine.",
            "Lifecycle authority is Holocene.",
            "| lifecycle writer | Candystore |",
        ):
            with self.subTest(stale=stale):
                errors = check_doc_drift.authority_parity_text_errors(
                    "33god-platform/components/example.yaml",
                    stale,
                )
                self.assertTrue(
                    any(
                        "non-Lifecycle component authority role" in item
                        for item in errors
                    )
                )

    def test_rejected_deployment_ceremony_phrases_are_rejected(self) -> None:
        stale_phrases = (
            "safe coexistence with unrelated projects",
            "Momo-offline safety",
            "## Promotion boundary",
            "requires a separate owner decision",
            "destructive-looking acceptance work",
            "root integration publication",
            "create a release tag",
        )
        for stale in stale_phrases:
            with self.subTest(stale=stale):
                errors = check_doc_drift.authority_parity_text_errors(
                    "docs/deployment-guide.md", stale
                )
                self.assertTrue(errors)

    def test_current_ticket_lifecycle_surfaces_are_momo_only(self) -> None:
        self.assertEqual(check_doc_drift.ticket_lifecycle_surface_errors(ROOT), [])

    def test_momo_source_mirror_byte_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_momo_workflow_fixture(root)
            mirror = (
                root
                / "momo/_bmad/_config/custom/custom/workflows/ticket-lifecycle/workflow.md"
            )
            mirror.write_text(
                mirror.read_text(encoding="utf-8") + "\nbyte drift\n",
                encoding="utf-8",
            )
            errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(any("source/mirror bytes differ" in item for item in errors))

    def test_momo_files_manifest_hash_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_momo_workflow_fixture(root)
            source = root / "momo/_bmad/custom/workflows/ticket-lifecycle/workflow.md"
            expected_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            manifest = root / "momo/_bmad/_config/files-manifest.csv"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    expected_hash, "0" * 64, 1
                ),
                encoding="utf-8",
            )
            errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(any("files-manifest hash differs" in item for item in errors))

    def test_registered_non_momo_ticket_lifecycle_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_workflow = root / "momo/_bmad/custom/workflows/ticket-lifecycle"
            mirror_workflow = (
                root
                / "momo/_bmad/_config/custom/custom/workflows/ticket-lifecycle"
            )
            source_workflow.mkdir(parents=True)
            mirror_workflow.mkdir(parents=True)
            (source_workflow / "workflow.md").write_text("client", encoding="utf-8")
            (mirror_workflow / "workflow.md").write_text("client", encoding="utf-8")
            momo_config = root / "momo/_bmad/_config"
            (momo_config / "workflow-manifest.csv").write_text(
                "ticket-lifecycle\n", encoding="utf-8"
            )
            (momo_config / "files-manifest.csv").write_text(
                "custom/workflows/ticket-lifecycle/workflow.md\n", encoding="utf-8"
            )
            candystore_config = root / "candystore/_bmad/_config"
            candystore_config.mkdir(parents=True)
            (candystore_config / "workflow-manifest.csv").write_text(
                "ticket-lifecycle\n", encoding="utf-8"
            )
            errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(
                any("candystore registers non-Momo" in item for item in errors)
            )

    def test_pjangler_commonproject_lifecycle_surfaces_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            commonproject = root / "pjangler/templates/commonproject"
            workflow = commonproject / "_bmad/custom/workflows/ticket-lifecycle"
            workflow.mkdir(parents=True)
            (workflow / "workflow.md").write_text("engine", encoding="utf-8")
            config = commonproject / "_bmad/_config"
            config.mkdir(parents=True)
            (config / "workflow-manifest.csv").write_text(
                "ticket-lifecycle\n", encoding="utf-8"
            )
            command = (
                commonproject
                / ".opencode/command/bmad-custom-ticket-lifecycle.md"
            )
            command.parent.mkdir(parents=True)
            command.write_text("command", encoding="utf-8")
            errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(
                any(
                    "pjangler/templates/commonproject retains non-Momo" in item
                    for item in errors
                )
            )
            self.assertTrue(
                any(
                    "pjangler/templates/commonproject registers non-Momo" in item
                    for item in errors
                )
            )
            self.assertTrue(any("command surface" in item for item in errors))

    def test_stale_bloodbank_live_controller_inventory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bloodbank = root / "bloodbank"
            bloodbank.mkdir()
            (bloodbank / "README.md").write_text(
                "| `services/` | heartbeat, lifecycle controller, agent hooks |\n",
                encoding="utf-8",
            )
            errors = check_doc_drift.bloodbank_live_inventory_errors(root)
            self.assertTrue(any("README lists a live" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
