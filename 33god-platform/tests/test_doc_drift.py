from __future__ import annotations

from contextlib import redirect_stdout
import copy
import importlib.util
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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


class TopologyScopeDriftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parts = json.loads(
            (ROOT / "docs/project-parts.json").read_text(encoding="utf-8")
        )
        cls.platform = check_doc_drift.load_yaml(
            ROOT / "33god-platform/components.yaml"
        )
        cls.scan = json.loads(
            (ROOT / "docs/project-scan-report.json").read_text(encoding="utf-8")
        )

    def test_current_topology_declarations_pass(self) -> None:
        self.assertEqual(
            check_doc_drift.topology_declaration_errors(
                self.parts, self.platform, self.scan
            ),
            [],
        )

    def test_lifecycle_omission_from_acceptance_slice_is_rejected(self) -> None:
        parts = copy.deepcopy(self.parts)
        parts["parts"] = [item for item in parts["parts"] if item["id"] != "lifecycle"]
        errors = check_doc_drift.topology_declaration_errors(
            parts, self.platform, self.scan
        )
        self.assertTrue(any("Lifecycle acceptance slice" in item for item in errors))

    def test_momo_omission_from_acceptance_slice_is_rejected(self) -> None:
        platform = copy.deepcopy(self.platform)
        platform["acceptance_slice"]["components"].remove("momo")
        errors = check_doc_drift.topology_declaration_errors(
            self.parts, platform, self.scan
        )
        self.assertTrue(any("Lifecycle acceptance slice" in item for item in errors))

    def test_product_registry_omission_is_rejected_independently(self) -> None:
        platform = copy.deepcopy(self.platform)
        platform["component_files"].remove("components/heyma.yaml")
        errors = check_doc_drift.topology_declaration_errors(
            self.parts, platform, self.scan
        )
        self.assertTrue(
            any("twelve-component product registry" in item for item in errors)
        )

    def test_alternate_manifest_directory_is_rejected_independently(self) -> None:
        platform = copy.deepcopy(self.platform)
        platform["component_files"][0] = "alternate/bloodbank.yaml"
        errors = check_doc_drift.topology_declaration_errors(
            self.parts, platform, self.scan
        )
        self.assertTrue(any("platform-paths" in item for item in errors))

    def test_duplicate_yaml_keys_are_rejected_at_nested_levels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.yaml"
            path.write_text(
                "outer:\n  source_revision: wrong\n  source_revision: expected\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate YAML mapping key"):
                check_doc_drift.load_yaml(path)

    def test_canonical_manifest_symlink_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            platform_root = source / "33god-platform"
            components = platform_root / "components"
            outside = root / "outside.yaml"
            components.mkdir(parents=True)
            (platform_root / "components.yaml").write_text("component_files: []\n")
            outside.write_text("id: substituted\n", encoding="utf-8")
            for relative in check_doc_drift.COMPONENT_FILE_PATHS:
                path = platform_root / relative
                path.write_text("id: canonical\n", encoding="utf-8")
            escaped = platform_root / check_doc_drift.COMPONENT_FILE_PATHS[0]
            escaped.unlink()
            escaped.symlink_to(outside)
            errors = check_doc_drift.canonical_platform_manifest_path_errors(source)
            self.assertTrue(
                any("must not traverse a symlink" in item for item in errors)
            )

    def test_scan_report_product_registry_is_exact(self) -> None:
        scan = copy.deepcopy(self.scan)
        scan["findings"]["product_registry"][0] = "substituted"
        errors = check_doc_drift.topology_declaration_errors(
            self.parts, self.platform, scan
        )
        self.assertTrue(any("scan product registry" in item for item in errors))

    def test_absolute_scan_root_is_rejected(self) -> None:
        scan = copy.deepcopy(self.scan)
        scan["project_root"] = "/primary/checkout/33GOD"
        errors = check_doc_drift.topology_declaration_errors(
            self.parts, self.platform, scan
        )
        self.assertTrue(any("reproducible {project-root}" in item for item in errors))

    def test_malformed_topology_declarations_fail_closed(self) -> None:
        errors = check_doc_drift.topology_declaration_errors(
            {"parts": "six", "product_registry": []},
            {"acceptance_slice": [], "component_files": "twelve"},
            {"findings": [], "project_types": "six"},
        )
        self.assertTrue(any("Lifecycle acceptance slice" in item for item in errors))
        self.assertTrue(
            any("twelve-component product registry" in item for item in errors)
        )
        self.assertTrue(any("project-scan-report" in item for item in errors))

    def test_top_level_yaml_list_is_a_controlled_topology_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            docs = root / "docs"
            (source / "33god-platform").mkdir(parents=True)
            docs.mkdir()
            (docs / "project-parts.json").write_text(
                json.dumps(self.parts), encoding="utf-8"
            )
            (docs / "project-scan-report.json").write_text(
                json.dumps(self.scan), encoding="utf-8"
            )
            (source / "33god-platform/components.yaml").write_text(
                "[]\n", encoding="utf-8"
            )
            report = check_doc_drift.Reporter()
            output = io.StringIO()
            with redirect_stdout(output):
                check_doc_drift.check_part_declaration(source, docs, report)
            self.assertEqual(report.failures, 1)
            self.assertIn(
                "cannot parse declaration: expected a YAML mapping",
                output.getvalue(),
            )

    def test_command_rejects_top_level_json_list_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            docs_checkout = Path(temporary)
            docs = docs_checkout / "docs"
            docs.mkdir()
            (docs / "project-parts.json").write_text("[]\n", encoding="utf-8")
            (docs / "project-scan-report.json").write_text(
                json.dumps(self.scan), encoding="utf-8"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(DRIFT_CHECK),
                    "--source-root",
                    str(ROOT),
                    "--docs-root",
                    str(docs_checkout),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "FAIL topology-scope: cannot parse declaration: "
                "project-parts.json: expected a top-level mapping, found list",
                output,
            )
            self.assertNotIn("Traceback", output)

    def test_acceptance_component_root_symlink_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            docs = root / "docs"
            outside = root / "outside/lifecycle"
            (source / "33god-platform").mkdir(parents=True)
            docs.mkdir()
            outside.mkdir(parents=True)
            subprocess.run(
                ["git", "-C", str(source), "init", "-q"],
                check=True,
                text=True,
                capture_output=True,
            )
            for component in check_doc_drift.LIFECYCLE_ACCEPTANCE_SLICE:
                if component == "lifecycle":
                    (source / component).symlink_to(outside, target_is_directory=True)
                else:
                    (source / component).mkdir()
            (docs / "project-parts.json").write_text(
                json.dumps(self.parts), encoding="utf-8"
            )
            (docs / "project-scan-report.json").write_text(
                json.dumps(self.scan), encoding="utf-8"
            )
            (source / "33god-platform/components.yaml").write_text(
                (ROOT / "33god-platform/components.yaml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            report = check_doc_drift.Reporter()
            output = io.StringIO()
            with redirect_stdout(output):
                check_doc_drift.check_part_declaration(source, docs, report)
            self.assertGreaterEqual(report.failures, 1)
            self.assertIn("escapes selected source root", output.getvalue())


class AuthorityParityDriftTests(unittest.TestCase):
    @staticmethod
    def write_momo_workflow_fixture(
        root: Path,
        *,
        workflow_files: dict[str, str] | None = None,
        description: str = "Bounded Lifecycle client for choosing and executing legal work.",
    ) -> None:
        workflow_files = workflow_files or {
            "workflow.md": "Lifecycle bounded client protocol.\n"
        }
        roots = (
            root / "momo/_bmad/custom/workflows/ticket-lifecycle",
            root / "momo/_bmad/_config/custom/custom/workflows/ticket-lifecycle",
        )
        for workflow_root in roots:
            for relative, content in workflow_files.items():
                path = workflow_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        config = root / "momo/_bmad/_config"
        config.mkdir(parents=True, exist_ok=True)
        (config / "workflow-manifest.csv").write_text(
            "name,description,module,path\n"
            f'"ticket-lifecycle","{description}","custom",'
            '"_bmad/custom/workflows/ticket-lifecycle/workflow.md"\n',
            encoding="utf-8",
        )
        rows = ["type,name,module,path,hash"]
        source_root = roots[0]
        for relative in sorted(workflow_files):
            path = source_root / relative
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append(
                f'"md","{Path(relative).stem}","custom",'
                f'"custom/workflows/ticket-lifecycle/{relative}","{digest}"'
            )
        (config / "files-manifest.csv").write_text(
            "\n".join(rows) + "\n", encoding="utf-8"
        )

    @staticmethod
    def git(cwd: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout.strip()

    @classmethod
    def init_repo(cls, path: Path) -> str:
        path.mkdir(parents=True, exist_ok=True)
        cls.git(path, "init", "-q")
        cls.git(path, "config", "user.name", "Drift Test")
        cls.git(path, "config", "user.email", "drift-test@example.invalid")
        return path.as_posix()

    @classmethod
    def add_nested_gitlink(
        cls, component: Path, relative: Path, *, initialized: bool
    ) -> Path:
        cls.init_repo(component)
        nested = component / relative
        if initialized:
            cls.init_repo(nested)
            runner = nested / "runner.sh"
            runner.write_text("tp transition PJAN-1 completed\n", encoding="utf-8")
            cls.git(nested, "add", "runner.sh")
            cls.git(nested, "commit", "-qm", "nested surface")
            revision = cls.git(nested, "rev-parse", "HEAD")
        else:
            nested.mkdir(parents=True)
            revision = "1" * 40
        (component / ".gitmodules").write_text(
            '[submodule "runtime"]\n'
            f"\tpath = {relative.as_posix()}\n"
            "\turl = https://github.com/example/runtime.git\n",
            encoding="utf-8",
        )
        cls.git(
            component,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{revision},{relative.as_posix()}",
        )
        cls.git(component, "add", ".gitmodules")
        cls.git(component, "commit", "-qm", "record nested gitlink")
        return nested

    def test_current_authority_json_artifacts_are_scanned(self) -> None:
        for relative in check_doc_drift.CURRENT_AUTHORITY_JSON_ARTIFACTS:
            current = (ROOT / relative).read_text(encoding="utf-8")
            self.assertEqual(
                check_doc_drift.authority_parity_text_errors(relative, current),
                [],
            )
        stale = current.replace(
            '"display_name": "Holocene"',
            '"display_name": "Holocene control plane"',
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

    def test_standalone_holocene_control_plane_branding_is_rejected(self) -> None:
        errors = check_doc_drift.authority_parity_text_errors(
            "source/holocene/.stitch/DESIGN.md",
            'Eyebrow text: "33GOD Control\n  Plane"',
        )
        self.assertTrue(
            any("standalone Holocene control-plane branding" in item for item in errors)
        )

    def test_cross_component_holocene_control_plane_claim_is_rejected(self) -> None:
        errors = check_doc_drift.authority_parity_text_errors(
            "source/bloodbank/services/agent-hooks/README.md",
            "Publish the health snapshot to the Holocene control-plane dashboard.",
        )
        self.assertTrue(any("Holocene control-plane role" in item for item in errors))

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

    def test_lifecycle_release_promotion_variants_are_rejected(self) -> None:
        for stale in (
            "release-tag promotion remains future work",
            "release tag promotion remains future work",
            "release-promotion remains future work",
        ):
            with self.subTest(stale=stale):
                errors = check_doc_drift.authority_parity_text_errors(
                    "lifecycle/README.md", stale
                )
                self.assertTrue(any("release" in item for item in errors))

    def test_clean_ticket_lifecycle_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_workflow_fixture(root)
            self.assertEqual(check_doc_drift.ticket_lifecycle_surface_errors(root), [])

    def test_momo_source_mirror_byte_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_workflow_fixture(root)
            mirror = (
                root
                / "momo/_bmad/_config/custom/custom/workflows/ticket-lifecycle/workflow.md"
            )
            mirror.write_text(
                mirror.read_text(encoding="utf-8") + "\nbyte drift\n",
                encoding="utf-8",
            )
            errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(
                any("source/mirror bytes differ" in item for item in errors)
            )

    def test_momo_files_manifest_hash_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_workflow_fixture(root)
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
            self.assertTrue(
                any("files-manifest hash differs" in item for item in errors)
            )

    def test_momo_holocene_copy_claims_are_rejected(self) -> None:
        stale_files = {
            "workflow.md": "A copy is stored in Holocene for its PM client.\n",
            "steps-v/step-01-validate.md": (
                "Source/generated copies are byte-identical in Momo/Holocene.\n"
            ),
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_workflow_fixture(root, workflow_files=stale_files)
            errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(any("Holocene copy claim" in item for item in errors))

    def test_momo_manifest_must_describe_bounded_lifecycle_client(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_workflow_fixture(
                root,
                description=(
                    "Autonomous multi-agent ticket lifecycle via Plane + Bloodbank."
                ),
            )
            errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(
                any("bounded Lifecycle client metadata" in item for item in errors)
            )

    def test_negated_or_opposite_momo_policy_metadata_is_rejected(self) -> None:
        descriptions = (
            "Unbounded Lifecycle client for choosing and executing legal work.",
            "Not a bounded Lifecycle client for choosing and executing legal work.",
            "Bounded Lifecycle client for choosing and executing illegal work.",
            "Bounded Lifecycle client that does not execute legal work.",
        )
        for description in descriptions:
            with (
                self.subTest(description=description),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                self.write_momo_workflow_fixture(root, description=description)
                errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
                self.assertTrue(
                    any("bounded Lifecycle client metadata" in item for item in errors)
                )

    def test_momo_policy_requires_separately_legal_choice_and_execution(self) -> None:
        descriptions = (
            "Bounded Lifecycle client for choosing legal work.",
            "Bounded Lifecycle client for choosing legal work while executing all work.",
            "Bounded Lifecycle client for choosing all work while executing legal work.",
        )
        for description in descriptions:
            with (
                self.subTest(description=description),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                self.write_momo_workflow_fixture(root, description=description)
                errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
                self.assertTrue(
                    any("bounded Lifecycle client metadata" in item for item in errors)
                )

    def test_momo_legal_ranking_and_execution_metadata_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_workflow_fixture(
                root,
                description=(
                    "Bounded Lifecycle client for ranking Lifecycle-legal work and "
                    "executing Lifecycle-legal work."
                ),
            )
            self.assertEqual(check_doc_drift.ticket_lifecycle_surface_errors(root), [])

    def test_ticket_lifecycle_separator_variants_count_as_duplicate_rows(self) -> None:
        variants = ("ticket_lifecycle", "ticket lifecycle")
        for variant in variants:
            with (
                self.subTest(variant=variant),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                self.write_momo_workflow_fixture(root)
                manifest = root / "momo/_bmad/_config/workflow-manifest.csv"
                manifest.write_text(
                    manifest.read_text(encoding="utf-8")
                    + f'"{variant}","duplicate","custom","duplicate.md"\n',
                    encoding="utf-8",
                )
                errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
                self.assertTrue(any("exactly one canonical" in item for item in errors))

    def test_momo_workflow_symlink_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_workflow_fixture(root)
            outside = root / "outside-workflow.md"
            outside.write_text("Lifecycle bounded client protocol.\n", encoding="utf-8")
            paths = (
                root / "momo/_bmad/custom/workflows/ticket-lifecycle/workflow.md",
                root
                / "momo/_bmad/_config/custom/custom/workflows/ticket-lifecycle/workflow.md",
            )
            for path in paths:
                path.unlink()
                path.symlink_to(outside)
            errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(any("workflow symlink" in item for item in errors))

    def test_malformed_momo_manifest_csv_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_workflow_fixture(root)
            manifest = root / "momo/_bmad/_config/workflow-manifest.csv"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").rstrip("\n") + ",unexpected\n",
                encoding="utf-8",
            )
            errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(any("malformed CSV row" in item for item in errors))

    def test_momo_csv_duplicate_headers_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_workflow_fixture(root)
            manifest = root / "momo/_bmad/_config/workflow-manifest.csv"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    "name,description,module,path", "name,name,module,path", 1
                ),
                encoding="utf-8",
            )
            errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(
                any("workflow-manifest CSV schema" in item for item in errors)
            )

    def test_momo_csv_malformed_quoting_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_workflow_fixture(root)
            manifest = root / "momo/_bmad/_config/workflow-manifest.csv"
            manifest.write_text(
                "name,description,module,path\n"
                '"ticket-lifecycle","unterminated,custom,path\n',
                encoding="utf-8",
            )
            errors = check_doc_drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(
                any("malformed workflow-manifest CSV" in item for item in errors)
            )

    def test_registered_non_momo_ticket_lifecycle_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_workflow_fixture(root)
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
            self.write_momo_workflow_fixture(root)
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
                commonproject / ".opencode/command/bmad-custom-ticket-lifecycle.md"
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

    def test_direct_sentinel_provider_completion_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "candystore/agents/hermes/pm/.scripts/sentinel.prompt.md"
            path.parent.mkdir(parents=True)
            path.write_text("tp transition CANDY-1 completed\n", encoding="utf-8")
            errors = check_doc_drift.non_momo_operational_surface_errors(root)
            self.assertTrue(
                any("provider completion surface" in item for item in errors)
            )

    def test_neutral_root_bin_provider_completion_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "candystore/bin/issue-autonomous-review.sh"
            path.parent.mkdir(parents=True)
            path.write_text("tp transition CANDY-1 completed\n", encoding="utf-8")
            errors = check_doc_drift.non_momo_operational_surface_errors(root)
            self.assertTrue(
                any("provider completion surface" in item for item in errors)
            )

    def test_backup_and_mirror_variants_are_rejected(self) -> None:
        variants = (
            "pjangler/agents/hermes/sentinel.prompt.md.bak",
            "holocene/mirror/agents/hermes/ticket-runner.md",
        )
        for relative in variants:
            with (
                self.subTest(relative=relative),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                path = root / relative
                path.parent.mkdir(parents=True)
                path.write_text(
                    "Autonomously treat accepted ticket as done.\n", encoding="utf-8"
                )
                errors = check_doc_drift.non_momo_operational_surface_errors(root)
                self.assertTrue(any(relative in item for item in errors))

    def test_symlinked_provider_runner_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "candystore/provider-runner.sh"
            target.parent.mkdir(parents=True)
            target.write_text("tp transition CANDY-1 completed\n", encoding="utf-8")
            link = root / "candystore/agents/hermes/pm/runner.sh"
            link.parent.mkdir(parents=True)
            link.symlink_to(target)
            errors = check_doc_drift.non_momo_operational_surface_errors(root)
            self.assertTrue(any("symlink" in item for item in errors))

    def test_unresolvable_provider_runner_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            link = root / "candystore/agents/hermes/pm/runner.sh"
            link.parent.mkdir(parents=True)
            link.symlink_to(link)
            errors = check_doc_drift.non_momo_operational_surface_errors(root)
            self.assertTrue(any("cannot be resolved safely" in item for item in errors))

    def test_adapter_and_runner_variants_are_rejected(self) -> None:
        for name in ("ticket-adapter.py", "lifecycle_runner.sh"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                path = root / "bloodbank/agents/hermes/pm" / name
                path.parent.mkdir(parents=True)
                path.write_text("move work to started\n", encoding="utf-8")
                errors = check_doc_drift.non_momo_operational_surface_errors(root)
                self.assertTrue(any(name in item for item in errors))

    def test_initialized_nested_gitlink_surface_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.add_nested_gitlink(
                root / "holocene",
                Path("agents/hermes/pm/runtime"),
                initialized=True,
            )
            errors = check_doc_drift.non_momo_operational_surface_errors(root)
            self.assertTrue(any("nested gitlink" in item for item in errors))
            self.assertTrue(
                any("provider completion surface" in item for item in errors)
            )

    def test_arbitrary_path_nested_gitlink_surface_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.add_nested_gitlink(
                root / "holocene", Path("vendor/runtime"), initialized=True
            )
            errors = check_doc_drift.non_momo_operational_surface_errors(root)
            self.assertTrue(any("vendor/runtime" in item for item in errors))
            self.assertTrue(
                any("provider completion surface" in item for item in errors)
            )

    def test_second_level_nested_gitlink_surface_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            component = root / "holocene"
            first = component / "vendor/runtime"
            second = first / "deps/worker"
            self.init_repo(component)
            self.init_repo(first)
            self.init_repo(second)
            runner = second / "bin/close.sh"
            runner.parent.mkdir()
            runner.write_text("tp transition HOLO-1 completed\n", encoding="utf-8")
            self.git(second, "add", "bin/close.sh")
            self.git(second, "commit", "-qm", "provider surface")
            second_revision = self.git(second, "rev-parse", "HEAD")
            (first / ".gitmodules").write_text(
                '[submodule "worker"]\n'
                "\tpath = deps/worker\n"
                "\turl = https://github.com/example/worker.git\n",
                encoding="utf-8",
            )
            self.git(first, "add", ".gitmodules")
            self.git(
                first,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{second_revision},deps/worker",
            )
            self.git(first, "commit", "-qm", "nested worker")
            first_revision = self.git(first, "rev-parse", "HEAD")
            (component / ".gitmodules").write_text(
                '[submodule "runtime"]\n'
                "\tpath = vendor/runtime\n"
                "\turl = https://github.com/example/runtime.git\n",
                encoding="utf-8",
            )
            self.git(
                component,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{first_revision},vendor/runtime",
            )
            self.git(component, "add", ".gitmodules")
            self.git(component, "commit", "-qm", "nested runtime")
            errors = check_doc_drift.non_momo_operational_surface_errors(root)
            self.assertTrue(any("deps/worker" in item for item in errors))
            self.assertTrue(
                any("provider completion surface" in item for item in errors)
            )

    def test_nested_gitlink_symlink_cycle_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            component = root / "holocene"
            self.init_repo(component)
            (component / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            self.git(component, "add", "tracked.txt")
            self.git(component, "commit", "-qm", "root")
            revision = self.git(component, "rev-parse", "HEAD")
            (component / "loop").symlink_to(".", target_is_directory=True)
            self.git(
                component,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{revision},loop",
            )
            self.git(component, "commit", "-qm", "published loop gitlink")
            errors = check_doc_drift.non_momo_operational_surface_errors(root)
            self.assertTrue(
                any("cycle" in item or "symlink" in item for item in errors)
            )

    def test_uninitialized_operational_nested_gitlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.add_nested_gitlink(
                root / "holocene",
                Path("agents/hermes/pm/runtime"),
                initialized=False,
            )
            errors = check_doc_drift.non_momo_operational_surface_errors(root)
            self.assertTrue(
                any("uninitialized nested gitlink" in item for item in errors)
            )

    def test_published_tree_scan_ignores_untracked_wip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "candystore"
            self.init_repo(repo)
            (repo / "README.md").write_text("clean\n", encoding="utf-8")
            self.git(repo, "add", "README.md")
            self.git(repo, "commit", "-qm", "published")
            untracked = repo / "bin/local-only.sh"
            untracked.parent.mkdir()
            untracked.write_text("tp transition CANDY-1 completed\n", encoding="utf-8")
            self.assertEqual(
                check_doc_drift.non_momo_operational_surface_errors(root), []
            )

    def test_bad_published_blob_survives_dirty_and_staged_masking(self) -> None:
        for mutation in ("dirty-replacement", "staged-replacement", "staged-deletion"):
            with (
                self.subTest(mutation=mutation),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                repo = root / "candystore"
                self.init_repo(repo)
                path = repo / "bin/close.sh"
                path.parent.mkdir()
                path.write_text("tp transition CANDY-1 completed\n", encoding="utf-8")
                self.git(repo, "add", "bin/close.sh")
                self.git(repo, "commit", "-qm", "published violation")
                if mutation == "staged-deletion":
                    self.git(repo, "rm", "-q", "bin/close.sh")
                else:
                    path.write_text("clean local replacement\n", encoding="utf-8")
                    if mutation == "staged-replacement":
                        self.git(repo, "add", "bin/close.sh")
                errors = check_doc_drift.non_momo_operational_surface_errors(root)
                self.assertTrue(
                    any("provider completion surface" in item for item in errors)
                )

    def test_clean_published_blob_ignores_bad_dirty_and_staged_bytes(self) -> None:
        for mutation in ("dirty-replacement", "staged-replacement"):
            with (
                self.subTest(mutation=mutation),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                repo = root / "holocene"
                self.init_repo(repo)
                path = repo / "bin/close.sh"
                path.parent.mkdir()
                path.write_text("clean published adapter\n", encoding="utf-8")
                self.git(repo, "add", "bin/close.sh")
                self.git(repo, "commit", "-qm", "published clean adapter")
                path.write_text("tp transition HOLO-1 completed\n", encoding="utf-8")
                if mutation == "staged-replacement":
                    self.git(repo, "add", "bin/close.sh")
                self.assertEqual(
                    check_doc_drift.non_momo_operational_surface_errors(root), []
                )

    def test_staged_nested_gitlink_deletion_cannot_mask_published_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            component = root / "holocene"
            self.add_nested_gitlink(component, Path("vendor/runtime"), initialized=True)
            self.git(component, "rm", "--cached", "-q", "vendor/runtime")
            errors = check_doc_drift.non_momo_operational_surface_errors(root)
            self.assertTrue(any("vendor/runtime" in item for item in errors))
            self.assertTrue(
                any("provider completion surface" in item for item in errors)
            )

    def test_missing_exact_blob_object_fails_even_when_nonoperational(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "candystore"
            self.init_repo(repo)
            readme = repo / "README.md"
            readme.write_text("clean\n", encoding="utf-8")
            self.git(repo, "add", "README.md")
            self.git(repo, "commit", "-qm", "published")
            blob = self.git(repo, "rev-parse", "HEAD:README.md")
            git_dir = Path(self.git(repo, "rev-parse", "--git-dir"))
            if not git_dir.is_absolute():
                git_dir = repo / git_dir
            object_path = git_dir / "objects" / blob[:2] / blob[2:]
            object_path.unlink()
            errors = check_doc_drift.non_momo_operational_surface_errors(root)
            self.assertTrue(any("missing or invalid blob" in item for item in errors))

    def test_committed_operational_symlink_and_non_utf8_blob_fail_closed(self) -> None:
        for variant in ("symlink", "non-utf8"):
            with (
                self.subTest(variant=variant),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                repo = root / "holocene"
                self.init_repo(repo)
                path = repo / "bin/close.sh"
                path.parent.mkdir()
                if variant == "symlink":
                    target = repo / "README.md"
                    target.write_text("clean\n", encoding="utf-8")
                    path.symlink_to("../README.md")
                else:
                    path.write_bytes(b"\xff\xfe\x00")
                self.git(repo, "add", ".")
                self.git(repo, "commit", "-qm", f"published {variant}")
                errors = check_doc_drift.non_momo_operational_surface_errors(root)
                needle = (
                    "operational symlink" if variant == "symlink" else "not valid UTF-8"
                )
                self.assertTrue(any(needle in item for item in errors))

    def test_malformed_duplicate_and_invalid_tree_records_fail_closed(self) -> None:
        object_id = b"1" * 40
        valid = b"100755 blob " + object_id + b"\tbin/close.sh\0"
        malformed = {
            "missing terminator": valid[:-1],
            "missing tab": b"100755 blob " + object_id + b" bin/close.sh\0",
            "duplicate path": valid + valid,
            "invalid mode": b"100600 blob " + object_id + b"\tbin/close.sh\0",
            "non-utf8 path": b"100755 blob " + object_id + b"\tbin/\xff.sh\0",
        }
        for label, raw in malformed.items():
            with (
                self.subTest(label=label),
                self.assertRaisesRegex(RuntimeError, "malformed|duplicate|invalid"),
            ):
                check_doc_drift._parse_git_tree_records(Path("fixture"), raw)

    def test_dirty_deletion_cannot_hide_or_oversize_a_published_violation(self) -> None:
        variants = ("missing", "oversized")
        for variant in variants:
            with (
                self.subTest(variant=variant),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                repo = root / "candystore"
                self.init_repo(repo)
                path = repo / "bin/close.sh"
                path.parent.mkdir()
                content = "tp transition CANDY-1 completed\n"
                if variant == "oversized":
                    content += "x" * 1_000_001
                path.write_text(content, encoding="utf-8")
                self.git(repo, "add", "bin/close.sh")
                self.git(repo, "commit", "-qm", variant)
                if variant == "missing":
                    path.unlink()
                errors = check_doc_drift.non_momo_operational_surface_errors(root)
                if variant == "missing":
                    self.assertTrue(
                        any("provider completion surface" in item for item in errors)
                    )
                else:
                    self.assertTrue(any("oversized" in item for item in errors))

    def test_git_file_enumeration_failure_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            with (
                patch.object(check_doc_drift, "is_own_checkout", return_value=True),
                patch.object(
                    check_doc_drift.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess(["git"], 1, "", "failed"),
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "tracked-file enumeration failed"
                ):
                    check_doc_drift.repository_files(repo)

    def test_staged_conflict_cannot_create_a_published_tree_false_positive(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "holocene"
            self.init_repo(repo)
            (repo / "README.md").write_text("clean\n", encoding="utf-8")
            self.git(repo, "add", "README.md")
            self.git(repo, "commit", "-qm", "published clean tree")
            blob = subprocess.run(
                ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
                input="stage\n",
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", str(repo), "update-index", "--index-info"],
                input=(
                    f"100755 {blob} 1\tbin/close.sh\n100755 {blob} 2\tbin/close.sh\n"
                ),
                check=True,
                text=True,
                capture_output=True,
            )
            errors = check_doc_drift.non_momo_operational_surface_errors(root)
            self.assertEqual(errors, [])

    def test_operational_git_timeout_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            with patch.object(
                check_doc_drift.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(["git"], 10),
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "tracked-file enumeration failed"
                ):
                    check_doc_drift.repository_files(repo)

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

    def test_current_root_bloodbank_controller_guidance_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            guide = root / "docs/development-guide-bloodbank.md"
            guide.parent.mkdir(parents=True)
            guide.write_text(
                "cd bloodbank/services/lifecycle-controller\n", encoding="utf-8"
            )
            errors = check_doc_drift.root_current_guidance_errors(root)
            self.assertTrue(
                any("current Bloodbank guidance" in item for item in errors)
            )

    def test_current_architecture_controller_hosting_claim_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            architecture = root / "_bmad-output/planning-artifacts/architecture.md"
            architecture.parent.mkdir(parents=True)
            architecture.write_text(
                "Bloodbank is hosting the current controller embryo.\n",
                encoding="utf-8",
            )
            errors = check_doc_drift.root_current_guidance_errors(root)
            self.assertTrue(
                any("current controller hosting" in item for item in errors)
            )

    def test_manifest_sha_elsewhere_does_not_satisfy_structural_pin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            platform_root = Path(temporary)
            components = platform_root / "components"
            components.mkdir()
            expected = check_doc_drift.COMPONENT_REVISIONS["bloodbank"]
            (components / "bloodbank.yaml").write_text(
                "id: bloodbank\n"
                f"description: historical revision {expected}\n"
                f"source_revision: {'0' * 40}\n",
                encoding="utf-8",
            )
            errors = check_doc_drift.component_manifest_pin_errors(
                platform_root,
                {"bloodbank": ("source_revision", expected)},
            )
            self.assertTrue(any("source_revision" in item for item in errors))

    def test_deleted_architecture_input_paths_are_rejected(self) -> None:
        stale_paths = (
            "holocene/_bmad/custom/workflows/ticket-lifecycle/workflow.md",
            "bloodbank/services/lifecycle-controller/src/reconciler.py",
        )
        for stale in stale_paths:
            with self.subTest(stale=stale), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                architecture = root / "_bmad-output/planning-artifacts/architecture.md"
                architecture.parent.mkdir(parents=True)
                architecture.write_text(
                    f"---\ninputDocuments:\n  - {stale}\n---\n", encoding="utf-8"
                )
                errors = check_doc_drift.root_current_guidance_errors(root)
                self.assertTrue(
                    any("retired architecture input" in item for item in errors)
                )

    def test_stale_four_part_current_guidance_is_rejected(self) -> None:
        for relative in check_doc_drift.CURRENT_TOPOLOGY_TEXT_ARTIFACTS:
            with (
                self.subTest(relative=relative),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    "The exact four-part component boundary is current.\n",
                    encoding="utf-8",
                )
                errors = check_doc_drift.root_current_guidance_errors(root)
                self.assertTrue(any(relative in item for item in errors))


if __name__ == "__main__":
    unittest.main()
