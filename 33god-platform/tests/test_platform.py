from __future__ import annotations

import copy
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
PLATFORM_SCRIPT = ROOT / "33god-platform/scripts/platform.py"
SPEC = importlib.util.spec_from_file_location("platform_control_plane", PLATFORM_SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load platform utility from {PLATFORM_SCRIPT}")
platform = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(platform)


class PlatformRegistryContractTests(unittest.TestCase):
    def test_active_registry_has_exact_twelve_registered_components(self) -> None:
        expected = (
            "bloodbank",
            "lifecycle",
            "candystore",
            "momo",
            "holocene",
            "pjangler",
            "hermes-fleet",
            "skillex",
            "hindsight",
            "pipeline-mcp-hub",
            "candybar",
            "heyma",
        )
        configured = tuple(
            Path(item).stem
            for item in platform.platform_config().get("component_files", [])
        )
        self.assertEqual(configured, expected)
        self.assertEqual(len(set(configured)), 12)
        self.assertTrue(all(path.is_file() for path in platform.component_paths()))

    def test_component_files_are_exact_canonical_ordered_paths(self) -> None:
        config = copy.deepcopy(platform.platform_config())
        config["component_files"][0] = "alternate/bloodbank.yaml"
        components = platform.load_components()
        with patch.object(platform, "platform_config", return_value=config):
            errors = platform.validate_acceptance_slice(components)
        self.assertTrue(any("exact ordered manifest paths" in item for item in errors))

    def test_loaded_manifest_contract_binds_identity_role_repo_kind_and_pin(
        self,
    ) -> None:
        mutations = {
            "id": "lifecycle",
            "role": "project-lifecycle-authority",
            "repo": "/tmp/borrowed-bloodbank",
            "repository_kind": "external-git",
            "source_revision": "0" * 40,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                components = copy.deepcopy(platform.load_components())
                components[0][field] = value
                errors = platform.validate_component_contracts(components)
                self.assertTrue(any("bloodbank" in item for item in errors))

    def test_external_and_non_git_repository_kinds_are_explicit(self) -> None:
        components = {item["id"]: item for item in platform.load_components()}
        self.assertEqual(components["skillex"]["repository_kind"], "external-git")
        self.assertEqual(
            components["skillex"]["source_revision"],
            "8b2f3d2f309c15f7bfcfe981c3dbeae87c50e371",
        )
        self.assertEqual(
            components["skillex"]["repository_origin"],
            "https://github.com/delorenj/skillex.git",
        )
        self.assertEqual(components["heyma"]["repository_kind"], "external-git")
        self.assertEqual(
            components["heyma"]["source_revision"],
            "c154bb8b1b4fb2909f6c5d91168a0c2a17298191",
        )
        self.assertEqual(
            components["heyma"]["repository_origin"],
            "https://github.com/delorenj/HeyMa.git",
        )
        self.assertEqual(components["hindsight"]["repository_kind"], "local-runtime")
        self.assertEqual(
            components["pipeline-mcp-hub"]["repository_kind"], "in-tree-source"
        )

    def test_publication_visibility_matches_public_repository(self) -> None:
        self.assertEqual(
            platform.platform_config()["product"]["visibility"], "public-source"
        )

    def test_lifecycle_acceptance_slice_is_exact_and_separate(self) -> None:
        configured = tuple(platform.acceptance_slice_ids())
        self.assertEqual(configured, platform.LIFECYCLE_ACCEPTANCE_SLICE)
        self.assertEqual(
            tuple(
                Path(item).stem
                for item in platform.platform_config().get("component_files", [])
            ),
            platform.PRODUCT_COMPONENT_IDS,
        )

    def test_malformed_acceptance_slice_fails_closed(self) -> None:
        self.assertEqual(platform.acceptance_slice_ids({"acceptance_slice": []}), [])

    def test_authority_component_roles_are_explicit(self) -> None:
        expected = {
            "bloodbank": "schema-contract-transport",
            "lifecycle": "project-lifecycle-authority",
            "candystore": "audit-and-read-projection",
            "momo": "legal-work-chooser-executor",
            "holocene": "dashboard-renderer",
            "pjangler": "project-identity-bootstrap-bindings",
        }
        components = {item["id"]: item for item in platform.load_components()}
        self.assertEqual(
            {component: components[component]["role"] for component in expected},
            expected,
        )

    def test_authority_component_pins_are_exact(self) -> None:
        expected = {
            "bloodbank": "aacd88564ea299924b8298165933ba821640bdba",
            "lifecycle": "cda59658bef6d586c8aa01cacd88bc4e3ee867e0",
            "candystore": "3c00080446bb9d4cb55c670477983306abcfe7ce",
            "momo": "8eeff1ce839c3bcffc2d3943322bc1dd8ef63fee",
            "holocene": "2beee67b433f1bd66abf7bce552d90e89413ae27",
            "pjangler": "13be237eaa454f22525dd9b4e5dd804b4516c212",
        }
        components = {item["id"]: item for item in platform.load_components()}
        for component, revision in expected.items():
            field = (
                "gitlink_revision" if component == "lifecycle" else "source_revision"
            )
            self.assertEqual(components[component][field], revision)
        self.assertEqual(
            components["pjangler"]["commonproject_revision"],
            "5dce335d10b44692414a5c67f12684ecc4fa5a41",
        )
        self.assertEqual(
            components["lifecycle"]["image"],
            "ghcr.io/delorenj/lifecycle@"
            "sha256:b216be4e1b796236309ee0b39120b0f353b62ee9f3c677901b2441a2c7aef210",
        )

    def test_root_gitlink_contract_is_the_exact_canonical_nine(self) -> None:
        expected = {
            "bloodbank": (
                "https://github.com/delorenj/bloodbank.git",
                "aacd88564ea299924b8298165933ba821640bdba",
            ),
            "candybar": (
                "https://github.com/delorenj/candybar.git",
                "509c03f350b5d41ec7a6779a3233dd61c9cbee91",
            ),
            "candystore": (
                "https://github.com/delorenj/candystore.git",
                "3c00080446bb9d4cb55c670477983306abcfe7ce",
            ),
            "hermes-agent-template": (
                "https://github.com/delorenj/hermes-agent-template.git",
                "576327ede2bf0686338fa8eb2735d1e16d03e870",
            ),
            "holocene": (
                "https://github.com/delorenj/holocene.git",
                "2beee67b433f1bd66abf7bce552d90e89413ae27",
            ),
            "lifecycle": (
                "https://github.com/delorenj/lifecycle.git",
                "cda59658bef6d586c8aa01cacd88bc4e3ee867e0",
            ),
            "momo": (
                "https://github.com/delorenj/momo.git",
                "8eeff1ce839c3bcffc2d3943322bc1dd8ef63fee",
            ),
            "pjangler": (
                "https://github.com/delorenj/pjangler.git",
                "13be237eaa454f22525dd9b4e5dd804b4516c212",
            ),
            "toad": (
                "https://github.com/delorenj/toad.git",
                "34bd4e17ebf5cf7844bf0162b4d83b6ba1e422c5",
            ),
        }
        self.assertEqual(platform.ROOT_GITLINK_CONTRACTS, expected)


class PlatformPathResolutionTests(unittest.TestCase):
    def test_nested_worktree_keeps_selected_repo_and_leaf_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code_root = Path(temporary) / "code"
            primary_checkout = code_root / "33GOD"
            primary_component = primary_checkout / "lifecycle"
            nested_checkout = (
                primary_checkout
                / "worktrees/team-prometheus/worktrees/worktree-prof-fiddlesticks"
            )
            nested_platform = nested_checkout / "33god-platform"
            nested_component = nested_checkout / "lifecycle"

            for path in (
                primary_component,
                nested_platform,
                nested_component,
            ):
                path.mkdir(parents=True)
            (primary_component / "compose.yml").touch()

            with (
                patch.object(platform, "SOURCE_ROOT", nested_checkout),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", nested_platform),
                patch.object(platform, "ROOT", nested_platform),
            ):
                repo = platform.resolve_path("../lifecycle")
                leaf = platform.resolve_path("../lifecycle/compose.yml")
                self.assertEqual(repo, nested_component)
                self.assertEqual(leaf, nested_component / "compose.yml")
                self.assertFalse(leaf.exists())
                self.assertTrue(platform.is_within(repo, nested_checkout))
                self.assertTrue(platform.is_within(leaf, nested_checkout))

    def test_missing_selected_repo_does_not_fall_back_to_primary_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code_root = Path(temporary) / "code"
            primary_component = code_root / "33GOD/lifecycle"
            nested_checkout = code_root / "33GOD/worktrees/team/nested"
            nested_platform = nested_checkout / "33god-platform"
            primary_component.mkdir(parents=True)
            nested_platform.mkdir(parents=True)
            with (
                patch.object(platform, "SOURCE_ROOT", nested_checkout),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", nested_platform),
            ):
                selected = platform.resolve_path("../lifecycle")
                self.assertEqual(selected, nested_checkout / "lifecycle")
                self.assertFalse(selected.exists())

    def test_external_sibling_uses_independent_explicit_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested_checkout = root / "nested/source"
            nested_platform = nested_checkout / "33god-platform"
            external_root = root / "external"
            external_component = external_root / "skillex"
            nested_platform.mkdir(parents=True)
            external_component.mkdir(parents=True)
            with (
                patch.object(platform, "SOURCE_ROOT", nested_checkout),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", nested_platform),
                patch.object(platform, "EXTERNAL_ROOT", external_root),
                patch.object(platform, "EXTERNAL_ROOT_IS_EXPLICIT", True),
            ):
                self.assertEqual(
                    platform.resolve_path("../../skillex"), external_component
                )
                self.assertFalse(
                    platform.is_within(external_component, nested_checkout)
                )

    def test_external_root_may_not_equal_source_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            platform_root = source / "33god-platform"
            platform_root.mkdir(parents=True)
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
                patch.object(platform, "EXTERNAL_ROOT", source),
            ):
                with self.assertRaisesRegex(
                    ValueError, "must be outside GOD_SOURCE_ROOT"
                ):
                    platform.resolve_path("../../skillex")

    def test_external_root_may_not_be_source_descendant(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            platform_root = source / "33god-platform"
            external = source / "external"
            platform_root.mkdir(parents=True)
            external.mkdir()
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
                patch.object(platform, "EXTERNAL_ROOT", external),
            ):
                with self.assertRaisesRegex(
                    ValueError, "must be outside GOD_SOURCE_ROOT"
                ):
                    platform.resolve_path("../../skillex")

    def test_external_root_symlink_reentry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            platform_root = source / "33god-platform"
            external = root / "external"
            platform_root.mkdir(parents=True)
            external.mkdir()
            (external / "skillex").symlink_to(source, target_is_directory=True)
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
                patch.object(platform, "EXTERNAL_ROOT", external),
            ):
                with self.assertRaisesRegex(ValueError, "re-enters GOD_SOURCE_ROOT"):
                    platform.resolve_path("../../skillex")

    def test_embedded_traversal_is_remapped_through_external_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "nested/source"
            platform_root = source / "33god-platform"
            external_root = root / "external"
            controlled = external_root / "outside"
            platform_root.mkdir(parents=True)
            controlled.mkdir(parents=True)
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
                patch.object(platform, "EXTERNAL_ROOT", external_root),
                patch.object(platform, "EXTERNAL_ROOT_IS_EXPLICIT", True),
            ):
                resolved = platform.resolve_path(
                    "nested/../../../outside", base=platform_root
                )
                self.assertEqual(resolved, controlled)
                self.assertTrue(platform.is_within(resolved, external_root))
                self.assertFalse(platform.is_within(resolved, source))

    def test_embedded_traversal_beyond_sibling_boundary_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "nested/source"
            platform_root = source / "33god-platform"
            external_root = root / "external"
            platform_root.mkdir(parents=True)
            external_root.mkdir(parents=True)
            uncontrolled = root / "outside"
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
                patch.object(platform, "EXTERNAL_ROOT", external_root),
                patch.object(platform, "EXTERNAL_ROOT_IS_EXPLICIT", True),
            ):
                with self.assertRaisesRegex(
                    ValueError, "escapes the supported sibling boundary"
                ):
                    platform.resolve_path(
                        "nested/../../../../outside", base=platform_root
                    )
                self.assertFalse(platform.is_within(uncontrolled, external_root))

    def test_explicit_absolute_registry_path_remains_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            registry = Path(temporary) / ".agents"
            registry.mkdir()
            self.assertEqual(platform.resolve_path(registry), registry.resolve())

    def test_selected_component_symlink_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            platform_root = source / "33god-platform"
            outside = root / "outside/lifecycle"
            platform_root.mkdir(parents=True)
            outside.mkdir(parents=True)
            (source / "lifecycle").symlink_to(outside, target_is_directory=True)
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
            ):
                with self.assertRaisesRegex(ValueError, "outside GOD_SOURCE_ROOT"):
                    platform.resolve_path("../lifecycle/compose.yml")

    def test_explicit_source_root_has_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_platform = root / "source/33god-platform"
            checkout_platform = root / "checkout/33god-platform"
            source_repo = root / "source/lifecycle"
            checkout_repo = root / "checkout/lifecycle"
            for path in (
                source_platform,
                checkout_platform,
                checkout_repo,
            ):
                path.mkdir(parents=True)
            with (
                patch.object(platform, "SOURCE_ROOT", root / "source"),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", source_platform),
                patch.object(platform, "SOURCE_ROOT_IS_EXPLICIT", True),
                patch.object(platform, "ROOT", checkout_platform),
            ):
                self.assertFalse(source_repo.exists())
                self.assertEqual(platform.resolve_path("../lifecycle"), source_repo)

    def test_selected_platform_config_changes_and_backfills_are_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            invoking = root / "invoking/33god-platform"
            selected = root / "selected"
            selected_platform = selected / "33god-platform"
            for path in (
                invoking / "changes",
                invoking / "backfills",
                selected_platform / "changes",
                selected_platform / "backfills",
            ):
                path.mkdir(parents=True)
            (invoking / "components.yaml").write_text(
                "product:\n  id: invoking\n", encoding="utf-8"
            )
            (selected_platform / "components.yaml").write_text(
                "product:\n  id: selected\n", encoding="utf-8"
            )
            (invoking / "changes/bad.jsonl").write_text("[]\n", encoding="utf-8")
            (selected_platform / "changes/good.jsonl").write_text("", encoding="utf-8")
            with (
                patch.object(platform, "ROOT", invoking),
                patch.object(platform, "SOURCE_ROOT", selected),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", selected_platform),
            ):
                self.assertEqual(
                    platform.platform_config()["product"]["id"], "selected"
                )
                self.assertEqual(platform.validate_changes(), [])
                self.assertEqual(platform.validate_backfill_manifests(), [])

    def test_selected_platform_root_inputs_reject_external_symlinks(self) -> None:
        for name, kind in (
            ("components.yaml", "file"),
            ("changes", "directory"),
            ("backfills", "directory"),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "source"
                platform_root = source / "33god-platform"
                outside = root / f"outside-{name.replace('.', '-')}"
                platform_root.mkdir(parents=True)
                if kind == "file":
                    outside.write_text("product: {id: attacker}\n", encoding="utf-8")
                else:
                    outside.mkdir()
                (platform_root / name).symlink_to(
                    outside, target_is_directory=kind == "directory"
                )
                with (
                    patch.object(platform, "SOURCE_ROOT", source),
                    patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
                ):
                    if name == "components.yaml":
                        with self.assertRaisesRegex(ValueError, "must not traverse"):
                            platform.platform_config()
                    elif name == "changes":
                        self.assertTrue(
                            any(
                                "must not traverse" in item
                                for item in platform.validate_changes()
                            )
                        )
                    else:
                        self.assertTrue(
                            any(
                                "must not traverse" in item
                                for item in platform.validate_backfill_manifests()
                            )
                        )

    def test_every_enumerated_platform_input_rejects_symlink_escape(self) -> None:
        for directory, filename, validator in (
            ("changes", "escape.jsonl", platform.validate_changes),
            ("backfills", "escape.yaml", platform.validate_backfill_manifests),
        ):
            with (
                self.subTest(directory=directory),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                source = root / "source"
                platform_root = source / "33god-platform"
                selected = platform_root / directory
                outside = root / filename
                selected.mkdir(parents=True)
                outside.write_text("{}\n", encoding="utf-8")
                (selected / filename).symlink_to(outside)
                with (
                    patch.object(platform, "SOURCE_ROOT", source),
                    patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
                ):
                    self.assertTrue(
                        any("must not traverse" in item for item in validator())
                    )

    def test_component_manifest_leaf_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            platform_root = source / "33god-platform"
            components = platform_root / "components"
            outside = root / "bloodbank.yaml"
            components.mkdir(parents=True)
            outside.write_text("id: attacker\n", encoding="utf-8")
            (components / "bloodbank.yaml").symlink_to(outside)
            config = {
                "component_files": list(platform.COMPONENT_FILE_PATHS),
            }
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
                patch.object(platform, "platform_config", return_value=config),
            ):
                with self.assertRaisesRegex(ValueError, "must not traverse"):
                    platform.component_paths()

    def test_relative_backfill_glob_symlink_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            platform_root = source / "33god-platform"
            outside = root / "outside"
            platform_root.mkdir(parents=True)
            outside.mkdir()
            (outside / "secret.txt").write_text("outside\n", encoding="utf-8")
            (platform_root / "linked").symlink_to(outside, target_is_directory=True)
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
            ):
                with self.assertRaisesRegex(ValueError, "backfill path escapes"):
                    platform.iter_search_files(["linked/*.txt"])

    def test_absolute_backfill_path_remains_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "live-runtime.conf"
            path.write_text("runtime\n", encoding="utf-8")
            self.assertEqual(platform.iter_search_files([str(path)]), [path])

    def test_backfill_directory_scan_excludes_generated_python_caches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            platform_root = source / "33god-platform"
            hooks = platform_root / "hooks"
            cache = hooks / "__pycache__"
            cache.mkdir(parents=True)
            source_file = hooks / "publish.py"
            compiled = cache / "publish.cpython-314.pyc"
            source_file.write_text("source\n", encoding="utf-8")
            compiled.write_bytes(b"\xff\xfecompiled")
            original_scandir = os.scandir

            def guarded_scandir(path: object) -> object:
                if Path(path) == cache:
                    raise AssertionError("cache directory was traversed")
                return original_scandir(path)

            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
                patch.object(platform.os, "scandir", guarded_scandir),
            ):
                self.assertEqual(platform.iter_search_files(["hooks"]), [source_file])

    def test_external_ancestor_directory_cannot_reenter_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            external = Path(temporary) / "external"
            source = external / "source"
            platform_root = source / "33god-platform"
            platform_root.mkdir(parents=True)
            (source / "tracked.txt").write_text("source\n", encoding="utf-8")
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
                patch.object(platform, "EXTERNAL_ROOT", external),
            ):
                with self.assertRaisesRegex(ValueError, "ancestor of GOD_SOURCE_ROOT"):
                    platform.iter_search_files(["../../"])

    def test_external_directory_symlink_reentry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            external = Path(temporary) / "external"
            source = external / "source"
            platform_root = source / "33god-platform"
            sibling = external / "sibling"
            platform_root.mkdir(parents=True)
            sibling.mkdir()
            (sibling / "source-link").symlink_to(source, target_is_directory=True)
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
                patch.object(platform, "EXTERNAL_ROOT", external),
            ):
                with self.assertRaisesRegex(ValueError, "re-enters GOD_SOURCE_ROOT"):
                    platform.iter_search_files(["../../sibling"])


class PlatformValidationFailureTests(unittest.TestCase):
    @staticmethod
    def component(repo: str, *, revision: str | None = None) -> dict[str, object]:
        item: dict[str, object] = {
            "id": "component",
            "name": "Component",
            "role": "test",
            "repo": repo,
            "repository_kind": "local-runtime",
            "description": "Validation fixture.",
            "changelog": {"topics": ["component"]},
            "compose": {"files": []},
            "_path": Path("components/component.yaml"),
        }
        if revision is not None:
            item["gitlink_revision"] = revision
        return item

    def test_missing_selected_acceptance_repo_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing_repo = Path(temporary) / "component"
            component = self.component("../component", revision="1" * 40)
            with (
                patch.object(platform, "load_components", return_value=[component]),
                patch.object(platform, "validate_gitlink_inventory", return_value=[]),
                patch.object(platform, "validate_acceptance_slice", return_value=[]),
                patch.object(
                    platform, "acceptance_slice_ids", return_value=["component"]
                ),
                patch.object(platform, "resolve_path", return_value=missing_repo),
            ):
                errors = platform.validate_components()
            self.assertTrue(any("acceptance-slice repo" in item for item in errors))

    def test_missing_selected_compose_leaf_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "component"
            repo.mkdir()
            missing_compose = repo / "compose.yml"
            component = self.component("../component")
            component["compose"] = {"files": ["../component/compose.yml"]}

            def selected_path(value: str | Path, base: Path = platform.ROOT) -> Path:
                del base
                return repo if str(value) == "../component" else missing_compose

            with (
                patch.object(platform, "load_components", return_value=[component]),
                patch.object(platform, "validate_gitlink_inventory", return_value=[]),
                patch.object(platform, "validate_acceptance_slice", return_value=[]),
                patch.object(platform, "acceptance_slice_ids", return_value=[]),
                patch.object(platform, "resolve_path", side_effect=selected_path),
            ):
                errors = platform.validate_components()
            self.assertTrue(
                any("compose file does not exist" in item for item in errors)
            )

    def test_conflicting_revision_fields_are_rejected(self) -> None:
        component = self.component("../component", revision="1" * 40)
        component["source_revision"] = "2" * 40
        with self.assertRaisesRegex(ValueError, "conflicting revision fields"):
            platform.recorded_revision(component)

    def test_malformed_nested_manifest_values_fail_closed(self) -> None:
        malformed = self.component("../component")
        malformed["changelog"] = []
        malformed["compose"] = {"files": "compose.yml", "profiles": {"default": True}}
        with (
            patch.object(platform, "load_components", return_value=[malformed]),
            patch.object(platform, "validate_gitlink_inventory", return_value=[]),
            patch.object(platform, "validate_acceptance_slice", return_value=[]),
            patch.object(platform, "validate_component_contracts", return_value=[]),
            patch.object(platform, "acceptance_slice_ids", return_value=[]),
        ):
            errors = platform.validate_components()
        self.assertTrue(any("changelog must be a mapping" in item for item in errors))
        self.assertTrue(any("compose.files must be a list" in item for item in errors))
        self.assertTrue(
            any("compose.profiles must be a list" in item for item in errors)
        )

    def test_jsonl_top_level_list_is_a_controlled_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            platform_root = Path(temporary) / "33god-platform"
            changes = platform_root / "changes"
            changes.mkdir(parents=True)
            (changes / "malformed.jsonl").write_text("[]\n", encoding="utf-8")
            with patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root):
                errors = platform.validate_changes()
        self.assertTrue(any("expected a JSON object" in item for item in errors))

    def test_invalid_yaml_is_path_qualified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "broken.yaml"
            path.write_text("value: [unterminated\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r"broken\.yaml: invalid YAML"):
                platform.load_yaml(path)

    def test_duplicate_yaml_keys_are_rejected_at_nested_levels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.yaml"
            path.write_text(
                "component:\n  source_revision: wrong\n  source_revision: expected\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate YAML mapping key"):
                platform.load_yaml(path)

    def test_change_required_scalars_must_be_typed_and_nonempty(self) -> None:
        malformed_values = {
            "id": {},
            "date": False,
            "component": None,
            "kind": [],
            "summary": "   ",
        }
        with tempfile.TemporaryDirectory() as temporary:
            platform_root = Path(temporary) / "33god-platform"
            changes = platform_root / "changes"
            changes.mkdir(parents=True)
            item = {
                **malformed_values,
                "affects": [],
                "required_backfills": [],
                "docs": [],
            }
            (changes / "malformed.jsonl").write_text(
                json.dumps(item) + "\n", encoding="utf-8"
            )
            with patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root):
                errors = platform.validate_changes()
            for key in malformed_values:
                self.assertTrue(
                    any(
                        f"{key} must be a non-empty string" in error for error in errors
                    )
                )

    def test_cli_uses_selected_checkout_and_never_tracebacks_on_bad_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            selected = Path(temporary) / "selected"
            selected_platform = selected / "33god-platform"
            selected_platform.mkdir(parents=True)
            (selected_platform / "changes").mkdir()
            (selected_platform / "backfills").mkdir()
            subprocess.run(
                ["git", "-C", str(selected), "init", "-q"],
                check=True,
                text=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(selected), "config", "user.name", "Platform Test"],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(selected),
                    "config",
                    "user.email",
                    "platform-test@example.invalid",
                ],
                check=True,
            )
            (selected_platform / "components.yaml").write_text(
                "component_files: [unterminated\n", encoding="utf-8"
            )
            (selected_platform / "changes/fixture.jsonl").write_text(
                "{}\n", encoding="utf-8"
            )
            (selected_platform / "backfills/fixture.yaml").write_text(
                "{}\n", encoding="utf-8"
            )
            subprocess.run(
                ["git", "-C", str(selected), "add", "33god-platform"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(selected), "commit", "-qm", "bad target"],
                check=True,
            )
            env = os.environ.copy()
            env["GOD_SOURCE_ROOT"] = str(selected)
            result = subprocess.run(
                [sys.executable, str(PLATFORM_SCRIPT), "validate"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 1)
            self.assertIn(str(selected_platform / "components.yaml"), output)
            self.assertNotIn("Traceback", output)

    def test_components_list_rejects_scalar_compose_fields_without_traceback(
        self,
    ) -> None:
        component = self.component("../component")
        component["compose"] = {"files": "compose.yml", "profiles": "default"}
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(platform, "load_components", return_value=[component]),
            patch.object(platform, "acceptance_slice_ids", return_value=[]),
            patch.object(
                platform, "validate_components", return_value=["invalid compose"]
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            self.assertEqual(platform.cmd_components_list(None), 1)
        self.assertIn("invalid compose", stderr.getvalue())


class PlatformBackfillFailureTests(unittest.TestCase):
    @staticmethod
    def write_manifest(path: Path, target: Path, *, include_id: bool = True) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        id_line = "id: fixture\n" if include_id else ""
        path.write_text(
            id_line
            + "title: Fixture\n"
            + "owner_component: bloodbank\n"
            + "kind: config\n"
            + "summary: Fixture scan.\n"
            + f"search_paths:\n  - {target}\n"
            + "forbidden_patterns:\n  - forbidden-marker\n"
            + "remediation: Remove marker.\n",
            encoding="utf-8",
        )

    def test_oversized_and_undecodable_backfill_targets_fail_closed(self) -> None:
        for variant in ("oversized", "undecodable"):
            with (
                self.subTest(variant=variant),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                target = root / "target.txt"
                if variant == "oversized":
                    target.write_text(
                        "forbidden-marker\n" + "x" * platform.MAX_SCAN_FILE_BYTES,
                        encoding="utf-8",
                    )
                else:
                    target.write_bytes(b"\xff\xfeforbidden-marker")
                manifest = root / "fixture.yaml"
                self.write_manifest(manifest, target)
                with self.assertRaisesRegex(
                    ValueError,
                    "size limit" if variant == "oversized" else "valid UTF-8",
                ):
                    platform.scan_backfill(manifest)

    def test_unreadable_backfill_target_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.txt"
            target.write_text("forbidden-marker\n", encoding="utf-8")
            manifest = root / "fixture.yaml"
            self.write_manifest(manifest, target)
            original_open = os.open

            def selective_open(path: object, *args: object, **kwargs: object) -> int:
                if Path(path) == target or (
                    Path(path) == Path(target.name) and kwargs.get("dir_fd") is not None
                ):
                    raise PermissionError("denied")
                return original_open(path, *args, **kwargs)

            with (
                patch.object(platform.os, "open", selective_open),
                self.assertRaisesRegex(ValueError, "cannot be read"),
            ):
                platform.scan_backfill(manifest)

    def test_unreadable_backfill_directory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "scan"
            restricted = target / "restricted"
            restricted.mkdir(parents=True)
            (restricted / "blocked.txt").write_text(
                "forbidden-marker\n", encoding="utf-8"
            )
            manifest = root / "fixture.yaml"
            self.write_manifest(manifest, target)
            original_scandir = os.scandir

            def selective_scandir(path: object) -> object:
                if Path(path) == restricted:
                    raise PermissionError("denied")
                return original_scandir(path)

            with (
                patch.object(platform.os, "scandir", selective_scandir),
                self.assertRaisesRegex(ValueError, "cannot be enumerated"),
            ):
                platform.scan_backfill(manifest)
            with (
                patch.object(platform.os, "scandir", selective_scandir),
                self.assertRaisesRegex(ValueError, "cannot be enumerated"),
            ):
                platform.iter_search_files([str(target / "*" / "*.txt")])

    def test_growing_and_virtual_backfill_files_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "growing.txt"
            target.write_text("clean\n", encoding="utf-8")
            original_read = os.read
            grew = False

            def growing_read(descriptor: int, size: int) -> bytes:
                nonlocal grew
                chunk = original_read(descriptor, size)
                if chunk and not grew:
                    grew = True
                    with target.open("ab") as handle:
                        handle.write(b"later\n")
                return chunk

            with (
                patch.object(platform.os, "read", growing_read),
                self.assertRaisesRegex(ValueError, "changed while reading"),
            ):
                platform.read_bounded_regular_file(target)

        virtual = Path("/proc/self/cmdline")
        if virtual.exists():
            with self.assertRaisesRegex(ValueError, "virtual backfill file"):
                platform.read_bounded_regular_file(virtual)

    def test_missing_backfill_id_returns_one_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            platform_root = Path(temporary) / "33god-platform"
            target = Path(temporary) / "target.txt"
            target.write_text("clean\n", encoding="utf-8")
            manifest = platform_root / "backfills/missing-id.yaml"
            self.write_manifest(manifest, target, include_id=False)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                result = platform.cmd_backfills_check(None)
            output = stdout.getvalue() + stderr.getvalue()
            self.assertEqual(result, 1)
            self.assertIn("id must be a non-empty string", output)
            self.assertNotIn("Traceback", output)
            self.assertNotIn("KeyError", output)


class PlatformRepositoryProvenanceTests(unittest.TestCase):
    @staticmethod
    def git(cwd: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout.strip()

    def init_repo(self, path: Path, origin: str) -> str:
        path.mkdir(parents=True)
        self.git(path, "init", "-q")
        self.git(path, "config", "user.name", "Platform Test")
        self.git(path, "config", "user.email", "platform-test@example.invalid")
        self.git(path, "remote", "add", "origin", origin)
        (path / "tracked.txt").write_text("one\n", encoding="utf-8")
        self.git(path, "add", "tracked.txt")
        self.git(path, "commit", "-qm", "initial")
        return self.git(path, "rev-parse", "HEAD")

    def configure_superproject(
        self, root: Path, component: Path, revision: str, url: str
    ) -> None:
        root.mkdir(parents=True, exist_ok=True)
        if not (root / ".git").exists():
            self.git(root, "init", "-q")
        self.git(root, "config", "user.name", "Platform Test")
        self.git(root, "config", "user.email", "platform-test@example.invalid")
        mapped_path = component.relative_to(root).as_posix()
        (root / ".gitmodules").write_text(
            f'[submodule "{mapped_path}"]\n\tpath = {mapped_path}\n\turl = {url}\n',
            encoding="utf-8",
        )
        self.git(
            root,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{revision},{mapped_path}",
        )
        self.git(root, "add", ".gitmodules")
        self.git(root, "commit", "-qm", "record root gitlink")

    def loose_object_path(self, repo: Path, object_id: str) -> Path:
        git_dir = Path(self.git(repo, "rev-parse", "--git-dir"))
        if not git_dir.is_absolute():
            git_dir = repo / git_dir
        return git_dir / "objects" / object_id[:2] / object_id[2:]

    def test_plain_child_cannot_inherit_wrapper_git_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wrapper = root / "wrapper"
            wrapper.mkdir()
            self.git(wrapper, "init", "-q")
            child = wrapper / "component"
            child.mkdir()
            self.assertIsNone(platform.git_checkout_revision(child))

    def test_selected_source_root_cannot_inherit_wrapper_git_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            wrapper = Path(temporary) / "wrapper"
            wrapper.mkdir()
            self.git(wrapper, "init", "-q")
            selected = wrapper / "selected"
            selected.mkdir()
            with patch.object(platform, "SOURCE_ROOT", selected):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(any("its own Git checkout" in item for item in errors))

    def test_exact_gitlink_head_and_origin_are_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            component = source / "component"
            url = "https://github.com/example/component.git"
            revision = self.init_repo(component, url)
            self.configure_superproject(source, component, revision, url)
            component_data = {
                "id": "component",
                "repo": "../component",
                "repository_kind": "root-gitlink",
                "gitlink_revision": revision,
            }
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(
                    platform, "SOURCE_PLATFORM_ROOT", source / "33god-platform"
                ),
            ):
                self.assertEqual(
                    platform.component_repo_status(component_data),
                    ("verified", revision),
                )

                (component / "tracked.txt").write_text("two\n", encoding="utf-8")
                self.git(component, "commit", "-qam", "advance")
                advanced = self.git(component, "rev-parse", "HEAD")
                self.assertEqual(
                    platform.component_repo_status(component_data),
                    ("revision-mismatch", advanced),
                )

    def test_exact_external_git_checkout_is_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            external = root / "external/skillex"
            origin = "https://github.com/example/skillex.git"
            revision = self.init_repo(external, origin)
            component = {
                "id": "skillex",
                "repo": "../../skillex",
                "repository_kind": "external-git",
                "source_revision": revision,
                "repository_origin": origin,
            }
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(platform, "resolve_path", return_value=external),
            ):
                self.assertEqual(
                    platform.component_repo_status(component), ("verified", revision)
                )

    def test_missing_external_git_checkout_is_honestly_uninitialized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing"
            component = {
                "id": "skillex",
                "repo": "../../skillex",
                "repository_kind": "external-git",
                "source_revision": "1" * 40,
                "repository_origin": "https://github.com/example/skillex.git",
            }
            with patch.object(platform, "resolve_path", return_value=missing):
                self.assertEqual(
                    platform.component_repo_status(component), ("uninitialized", None)
                )

    def test_external_file_cannot_masquerade_as_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fake = Path(temporary) / "passwd"
            fake.write_text("root:x:0:0\n", encoding="utf-8")
            component = {
                "id": "skillex",
                "repo": "../../skillex",
                "repository_kind": "external-git",
                "source_revision": "1" * 40,
                "repository_origin": "https://github.com/example/skillex.git",
            }
            with patch.object(platform, "resolve_path", return_value=fake):
                self.assertEqual(
                    platform.component_repo_status(component),
                    ("not-a-git-checkout", None),
                )

    def test_local_runtime_and_in_tree_source_do_not_use_parent_git_identity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime = root / ".agents"
            pipeline = root / "source/pipeline-mcp-hub"
            runtime.mkdir()
            pipeline.mkdir(parents=True)
            with (
                patch.object(platform, "SOURCE_ROOT", root / "source"),
                patch.object(platform, "resolve_path", side_effect=[runtime, pipeline]),
            ):
                self.assertEqual(
                    platform.component_repo_status(
                        {
                            "id": "hindsight",
                            "repo": "~/.agents",
                            "repository_kind": "local-runtime",
                        }
                    ),
                    ("present", None),
                )
                self.assertEqual(
                    platform.component_repo_status(
                        {
                            "id": "pipeline-mcp-hub",
                            "repo": "../pipeline-mcp-hub",
                            "repository_kind": "in-tree-source",
                        }
                    ),
                    ("present", None),
                )

    def test_exact_mapped_pin_can_be_honestly_uninitialized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            component = source / "component"
            revision = "1" * 40
            component.mkdir(parents=True)
            self.configure_superproject(
                source,
                component,
                revision,
                "https://github.com/example/component.git",
            )
            component_data = {
                "id": "component",
                "repo": "../component",
                "repository_kind": "root-gitlink",
                "gitlink_revision": revision,
            }
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(
                    platform, "SOURCE_PLATFORM_ROOT", source / "33god-platform"
                ),
            ):
                self.assertEqual(
                    platform.component_repo_status(component_data),
                    ("uninitialized", None),
                )

    def test_initialized_gitlink_inventory_is_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            component = source / "component"
            url = "https://github.com/example/component.git"
            revision = self.init_repo(component, "git@github.com:example/component.git")
            self.configure_superproject(source, component, revision, url)
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(
                    platform,
                    "ROOT_GITLINK_CONTRACTS",
                    {"component": (url, revision)},
                ),
            ):
                self.assertEqual(platform.validate_gitlink_inventory(), [])

    def test_git_replacement_refs_cannot_substitute_root_tree_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            self.init_repo(repo, "https://github.com/example/root.git")
            bad_commit = self.git(repo, "rev-parse", "HEAD")
            bad_blob = self.git(repo, "rev-parse", "HEAD:tracked.txt")
            (repo / "tracked.txt").write_text("clean replacement\n", encoding="utf-8")
            self.git(repo, "commit", "-qam", "clean replacement")
            clean_commit = self.git(repo, "rev-parse", "HEAD")
            self.git(repo, "reset", "--hard", "-q", bad_commit)
            self.git(repo, "replace", bad_commit, clean_commit)
            entries = platform.root_tree_entries(repo)
            self.assertEqual(entries["tracked.txt"][2], bad_blob)

    def test_platform_manifest_semantics_ignore_staged_and_dirty_bytes(self) -> None:
        for mutation in ("bad-commit-clean-stage", "clean-commit-bad-dirty"):
            with (
                self.subTest(mutation=mutation),
                tempfile.TemporaryDirectory() as temporary,
            ):
                source = Path(temporary) / "source"
                platform_root = source / "33god-platform"
                platform_root.mkdir(parents=True)
                self.git(source, "init", "-q")
                self.git(source, "config", "user.name", "Platform Test")
                self.git(
                    source,
                    "config",
                    "user.email",
                    "platform-test@example.invalid",
                )
                manifest = platform_root / "components.yaml"
                committed = "bad" if mutation.startswith("bad") else "clean"
                mutable = "clean" if committed == "bad" else "bad"
                manifest.write_text(f"marker: {committed}\n", encoding="utf-8")
                self.git(source, "add", "33god-platform/components.yaml")
                self.git(source, "commit", "-qm", "published manifest")
                manifest.write_text(f"marker: {mutable}\n", encoding="utf-8")
                if mutation.endswith("stage"):
                    self.git(source, "add", "33god-platform/components.yaml")
                with (
                    patch.object(platform, "SOURCE_ROOT", source),
                    patch.object(platform, "SOURCE_PLATFORM_ROOT", platform_root),
                ):
                    self.assertEqual(platform.platform_config()["marker"], committed)

    def test_missing_component_head_commit_fails_with_surviving_ref(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "component"
            revision = self.init_repo(repo, "https://github.com/example/component.git")
            self.loose_object_path(repo, revision).unlink()
            with self.assertRaisesRegex(ValueError, "missing|failed safely"):
                platform.git_checkout_revision(repo)

    def test_missing_unrelated_root_blob_or_subtree_fails_closed(self) -> None:
        for kind in ("blob", "tree"):
            with (
                self.subTest(kind=kind),
                tempfile.TemporaryDirectory() as temporary,
            ):
                repo = Path(temporary) / "root"
                self.init_repo(repo, "https://github.com/example/root.git")
                unrelated = repo / "unrelated/data.txt"
                unrelated.parent.mkdir()
                unrelated.write_text("unrelated\n", encoding="utf-8")
                self.git(repo, "add", "unrelated/data.txt")
                self.git(repo, "commit", "-qm", "unrelated subtree")
                expression = "HEAD:unrelated/data.txt" if kind == "blob" else "HEAD:unrelated"
                object_id = self.git(repo, "rev-parse", expression)
                self.loose_object_path(repo, object_id).unlink()
                with self.assertRaisesRegex(ValueError, "missing or invalid object"):
                    platform.root_tree_entries(repo)

    def test_root_gitlink_checkout_symlink_indirection_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            borrowed = source / "borrowed"
            checkout = source / "component"
            url = "https://github.com/example/component.git"
            revision = self.init_repo(borrowed, url)
            self.configure_superproject(source, checkout, revision, url)
            checkout.symlink_to(borrowed, target_is_directory=True)
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(
                    platform,
                    "ROOT_GITLINK_CONTRACTS",
                    {"component": (url, revision)},
                ),
            ):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(any("non-symlink directories" in item for item in errors))

    def test_streaming_git_output_caps_kill_and_reap_real_flooders(self) -> None:
        for stream_name in ("stdout", "stderr"):
            with (
                self.subTest(stream=stream_name),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                fake_git = root / "git"
                pid_file = root / "pid"
                fake_git.write_text(
                    "#!/usr/bin/env python3\n"
                    "import os, sys, time\n"
                    "with open(os.environ['FLOOD_PID_FILE'], 'w', encoding='ascii') as handle:\n"
                    "    handle.write(str(os.getpid()))\n"
                    "stream = sys.stdout.buffer if os.environ['FLOOD_STREAM'] == 'stdout' else sys.stderr.buffer\n"
                    "stream.write(b'PRIVATE-FLOOD-PAYLOAD' * 512)\n"
                    "stream.flush()\n"
                    "time.sleep(30)\n",
                    encoding="utf-8",
                )
                fake_git.chmod(0o755)
                environment = {
                    "PATH": f"{root}{os.pathsep}{os.environ['PATH']}",
                    "FLOOD_PID_FILE": str(pid_file),
                    "FLOOD_STREAM": stream_name,
                }
                started = time.monotonic()
                with (
                    patch.dict(os.environ, environment),
                    self.assertRaises(platform.GitValidationError) as raised,
                ):
                    platform._run_git_bytes(
                        root,
                        "status",
                        stdout_limit=1024,
                        stderr_limit=1024,
                    )
                self.assertLess(time.monotonic() - started, 5)
                self.assertNotIn("PRIVATE-FLOOD-PAYLOAD", str(raised.exception))
                child_pid = int(pid_file.read_text(encoding="ascii"))
                with self.assertRaises(ProcessLookupError):
                    os.kill(child_pid, 0)

    def test_uninitialized_gitlink_without_component_row_fails_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            orphan = source / "orphan"
            revision = "1" * 40
            self.configure_superproject(
                source,
                orphan,
                revision,
                "https://github.com/example/orphan.git",
            )
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(
                    platform,
                    "ROOT_GITLINK_CONTRACTS",
                    {"orphan": ("https://github.com/example/orphan.git", revision)},
                ),
            ):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(
                any(
                    "root gitlink orphan" in item and "not initialized" in item
                    for item in errors
                )
            )

    def test_gitlink_inventory_rejects_checkout_revision_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            component = source / "component"
            url = "https://github.com/example/component.git"
            actual = self.init_repo(component, url)
            expected = "1" * 40
            self.assertNotEqual(actual, expected)
            self.configure_superproject(source, component, expected, url)
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(
                    platform,
                    "ROOT_GITLINK_CONTRACTS",
                    {"component": (url, expected)},
                ),
            ):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(
                any(
                    "root gitlink component" in item
                    and "does not match commit revision" in item
                    for item in errors
                )
            )

    def test_gitlink_inventory_rejects_checkout_origin_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            component = source / "component"
            expected_url = "https://github.com/example/component.git"
            revision = self.init_repo(
                component, "https://github.com/other/component.git"
            )
            self.configure_superproject(source, component, revision, expected_url)
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(
                    platform,
                    "ROOT_GITLINK_CONTRACTS",
                    {"component": (expected_url, revision)},
                ),
            ):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(
                any(
                    "root gitlink component" in item
                    and "does not match canonical public identity" in item
                    for item in errors
                )
            )

    def test_fork_substitution_cannot_redefine_canonical_root_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            component = source / "component"
            fork = "https://github.com/example-fork/component.git"
            canonical = "https://github.com/example/component.git"
            revision = self.init_repo(component, fork)
            self.configure_superproject(source, component, revision, fork)
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(
                    platform,
                    "ROOT_GITLINK_CONTRACTS",
                    {"component": (canonical, revision)},
                ),
            ):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(
                any("canonical public HTTPS origin" in item for item in errors)
            )
            self.assertTrue(any("canonical public identity" in item for item in errors))

    def test_components_list_inherits_gitlink_inventory_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            orphan = source / "orphan"
            self.configure_superproject(
                source,
                orphan,
                "1" * 40,
                "https://github.com/example/orphan.git",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(
                    platform,
                    "ROOT_GITLINK_CONTRACTS",
                    {
                        "orphan": (
                            "https://github.com/example/orphan.git",
                            "1" * 40,
                        )
                    },
                ),
                patch.object(platform, "load_components", return_value=[]),
                patch.object(platform, "acceptance_slice_ids", return_value=[]),
                patch.object(platform, "validate_acceptance_slice", return_value=[]),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                result = platform.cmd_components_list(None)
            self.assertEqual(result, 1)
            self.assertIn("root gitlink orphan", stderr.getvalue())

    def test_components_list_reports_missing_repo_without_keyerror(self) -> None:
        component = {
            "id": "malformed",
            "name": "Malformed",
            "role": "test",
            "description": "Missing repo fixture.",
            "changelog": {"topics": ["malformed"]},
            "_path": Path("components/malformed.yaml"),
        }
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(platform, "load_components", return_value=[component]),
            patch.object(platform, "acceptance_slice_ids", return_value=[]),
            patch.object(platform, "validate_gitlink_inventory", return_value=[]),
            patch.object(platform, "validate_acceptance_slice", return_value=[]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = platform.cmd_components_list(None)
        self.assertEqual(result, 1)
        self.assertIn("missing required keys: repo", stderr.getvalue())

    def test_components_list_reports_missing_id_and_role_without_keyerror(self) -> None:
        component = {
            "name": "Malformed",
            "repo": "../malformed",
            "description": "Missing identity fixture.",
            "changelog": {"topics": ["malformed"]},
            "_path": Path("components/malformed.yaml"),
        }
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(platform, "load_components", return_value=[component]),
            patch.object(platform, "acceptance_slice_ids", return_value=[]),
            patch.object(platform, "validate_gitlink_inventory", return_value=[]),
            patch.object(platform, "validate_acceptance_slice", return_value=[]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = platform.cmd_components_list(None)
        self.assertEqual(result, 1)
        self.assertIn("missing required keys: id, role", stderr.getvalue())

    def test_components_list_reports_unsafe_repo_without_crashing(self) -> None:
        component = {
            "id": "unsafe",
            "role": "test",
            "repo": "../../../../outside",
            "compose": {},
            "_path": Path("components/unsafe.yaml"),
        }
        with (
            patch.object(platform, "load_components", return_value=[component]),
            patch.object(platform, "acceptance_slice_ids", return_value=[]),
            patch.object(platform, "resolve_path", side_effect=ValueError("escape")),
            patch.object(
                platform,
                "validate_components",
                return_value=["components/unsafe.yaml: unsafe repo"],
            ),
            patch("builtins.print"),
        ):
            self.assertEqual(platform.cmd_components_list(None), 1)

    def test_malformed_gitmodules_inventory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            self.git(source, "init", "-q")
            self.git(source, "config", "user.name", "Platform Test")
            self.git(source, "config", "user.email", "platform-test@example.invalid")
            (source / ".gitmodules").write_text("[broken\n", encoding="utf-8")
            self.git(source, "add", ".gitmodules")
            self.git(source, "commit", "-qm", "malformed gitmodules fixture")
            with patch.object(platform, "SOURCE_ROOT", source):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(any("cannot parse" in item for item in errors))

    def test_duplicate_gitmodule_paths_fail_as_ambiguous_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            self.git(source, "init", "-q")
            self.git(source, "config", "user.name", "Platform Test")
            self.git(source, "config", "user.email", "platform-test@example.invalid")
            revision = "1" * 40
            (source / ".gitmodules").write_text(
                '[submodule "first"]\n'
                "\tpath = shared\n"
                "\turl = https://github.com/example/first.git\n"
                '[submodule "second"]\n'
                "\tpath = shared\n"
                "\turl = https://github.com/example/second.git\n",
                encoding="utf-8",
            )
            self.git(
                source,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{revision},shared",
            )
            self.git(source, "add", ".gitmodules")
            self.git(source, "commit", "-qm", "duplicate mapping fixture")
            with patch.object(platform, "SOURCE_ROOT", source):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(
                any("ambiguous duplicate submodule path" in item for item in errors)
            )

    def test_gitmodule_symlink_escape_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            outside = root / "outside.gitmodules"
            source.mkdir()
            self.git(source, "init", "-q")
            self.git(source, "config", "user.name", "Platform Test")
            self.git(source, "config", "user.email", "platform-test@example.invalid")
            outside.write_text(
                '[submodule "component"]\n'
                "\tpath = component\n"
                "\turl = https://github.com/example/component.git\n",
                encoding="utf-8",
            )
            (source / ".gitmodules").symlink_to(outside)
            blob = subprocess.run(
                ["git", "-C", str(source), "hash-object", "-w", "--stdin"],
                input=str(outside),
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            tree = subprocess.run(
                ["git", "-C", str(source), "mktree"],
                input=f"120000 blob {blob}\t.gitmodules\n",
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            commit = subprocess.run(
                ["git", "-C", str(source), "commit-tree", tree],
                input="symlink gitmodules fixture\n",
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            self.git(source, "update-ref", "HEAD", commit)
            with patch.object(platform, "SOURCE_ROOT", source):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(
                any(
                    ".gitmodules" in item and "regular committed file" in item
                    for item in errors
                ),
                errors,
            )

    def test_nonzero_duplicate_index_stages_cannot_mask_committed_inventory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            component = source / "component"
            url = "https://github.com/example/component.git"
            revision = self.init_repo(component, url)
            self.configure_superproject(source, component, revision, url)
            subprocess.run(
                ["git", "-C", str(source), "update-index", "--index-info"],
                input=(
                    f"160000 {revision} 1\tcomponent\n160000 {revision} 2\tcomponent\n"
                ),
                check=True,
                text=True,
                capture_output=True,
            )
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(
                    platform,
                    "ROOT_GITLINK_CONTRACTS",
                    {"component": (url, revision)},
                ),
            ):
                self.assertEqual(platform.validate_gitlink_inventory(), [])

    def test_git_timeout_and_oserror_are_controlled_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            failures = (
                platform._BoundedProcessError("timeout"),
                OSError("git unavailable"),
            )
            for failure in failures:
                with (
                    self.subTest(failure=type(failure).__name__),
                    patch.object(
                        platform, "_run_bounded_process", side_effect=failure
                    ),
                ):
                    with self.assertRaisesRegex(
                        ValueError, "Git command failed safely"
                    ):
                        platform.git_checkout_revision(repo)

    def test_repository_urls_require_credential_free_hostful_https(self) -> None:
        self.assertEqual(
            platform.normalize_repository_url(
                "https://github.com/Example/Component.git/"
            ),
            "https://github.com/example/component",
        )
        invalid = (
            "git@github.com:example/component.git",
            "https:///example/component.git",
            "https://user:secret@github.com/example/component.git",
            "https://github.com/example/component.git?token=secret",
            "https://github.com/example/component.git#fragment",
            "https://github.com",
        )
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    ValueError, "credential-free hostful HTTPS"
                ):
                    platform.normalize_repository_url(value)

    def test_checkout_ssh_origin_rejects_any_explicit_port(self) -> None:
        self.assertEqual(
            platform.normalize_checkout_origin(
                "ssh://git@github.com/example/component.git"
            ),
            "https://github.com/example/component",
        )
        for value in (
            "ssh://git@github.com:22/example/component.git",
            "ssh://git@github.com:2222/example/component.git",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    ValueError, "credential-free hostful HTTPS repository"
                ),
            ):
                platform.normalize_checkout_origin(value)

    def test_invalid_credential_url_is_never_echoed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            component = source / "component"
            credential_url = (
                "https://user:do-not-print-this@github.com/example/component.git"
            )
            revision = self.init_repo(component, credential_url)
            self.configure_superproject(source, component, revision, credential_url)
            with (
                patch.object(platform, "SOURCE_ROOT", source),
                patch.object(
                    platform,
                    "ROOT_GITLINK_CONTRACTS",
                    {
                        "component": (
                            "https://github.com/example/component.git",
                            revision,
                        )
                    },
                ),
            ):
                output = "\n".join(platform.validate_gitlink_inventory())
            self.assertIn("credential-free hostful HTTPS", output)
            self.assertNotIn("do-not-print-this", output)
            self.assertNotIn("user:", output)

    def test_malformed_gitmodules_parser_diagnostic_redacts_source_line(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            self.git(source, "init", "-q")
            self.git(source, "config", "user.name", "Platform Test")
            self.git(source, "config", "user.email", "platform-test@example.invalid")
            sentinel = "DO-NOT-PRINT-THIS-SECRET"
            (source / ".gitmodules").write_text(
                f"https://user:{sentinel}@github.com/example/component.git\n",
                encoding="utf-8",
            )
            self.git(source, "add", ".gitmodules")
            self.git(source, "commit", "-qm", "secret-bearing malformed fixture")
            with patch.object(platform, "SOURCE_ROOT", source):
                output = "\n".join(platform.validate_gitlink_inventory())
            self.assertIn("cannot parse root gitlink inventory safely", output)
            self.assertNotIn(sentinel, output)
            self.assertNotIn("https://user:", output)

    def test_checkout_origin_uses_repository_local_configuration_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            self.git(repo, "init", "-q")
            global_config = root / "global.gitconfig"
            global_config.write_text(
                '[remote "origin"]\n\turl = https://github.com/example/inherited.git\n',
                encoding="utf-8",
            )
            with patch.dict(
                os.environ, {"GIT_CONFIG_GLOBAL": str(global_config)}, clear=False
            ):
                self.assertIsNone(platform.git_checkout_origin(repo))

    def test_live_root_inventory_excludes_private_runtime_and_verifies_sources(
        self,
    ) -> None:
        gitlinks = platform.gitlink_entries(ROOT)
        mappings = platform.gitmodule_mappings(ROOT)
        expected_paths = {
            "bloodbank",
            "candybar",
            "candystore",
            "hermes-agent-template",
            "holocene",
            "lifecycle",
            "momo",
            "pjangler",
            "toad",
        }
        forbidden_runtime = "agents/hermes/pm/runtime"

        self.assertNotIn(forbidden_runtime, gitlinks)
        self.assertNotIn(forbidden_runtime, mappings)
        self.assertEqual(set(gitlinks), expected_paths)
        self.assertEqual(set(mappings), expected_paths)

        normalized_urls = [
            platform.normalize_repository_url(item["url"]) for item in mappings.values()
        ]
        self.assertTrue(
            all(item["url"].startswith("https://") for item in mappings.values())
        )
        self.assertEqual(len(normalized_urls), len(set(normalized_urls)))

        for path, expected_revision in gitlinks.items():
            checkout = ROOT / path
            self.assertEqual(
                platform.git_checkout_revision(checkout), expected_revision
            )
            self.assertEqual(
                platform.normalize_repository_url(mappings[path]["url"]),
                platform.normalize_checkout_origin(
                    platform.git_checkout_origin(checkout) or ""
                ),
            )

        self.assertEqual(
            gitlinks["candybar"],
            "509c03f350b5d41ec7a6779a3233dd61c9cbee91",
        )
        self.assertEqual(
            gitlinks["hermes-agent-template"],
            "576327ede2bf0686338fa8eb2735d1e16d03e870",
        )
        self.assertEqual(
            gitlinks["toad"],
            "34bd4e17ebf5cf7844bf0162b4d83b6ba1e422c5",
        )

    def test_live_root_gitlink_inventory_is_fully_verified(self) -> None:
        self.assertEqual(platform.validate_gitlink_inventory(), [])


if __name__ == "__main__":
    unittest.main()
