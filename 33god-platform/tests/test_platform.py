from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
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
    def test_active_registry_has_exact_twelve_populated_components(self) -> None:
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
            field = "gitlink_revision" if component == "lifecycle" else "source_revision"
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


class PlatformPathResolutionTests(unittest.TestCase):
    def test_nested_worktree_prefers_selected_component_and_external_sibling(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code_root = Path(temporary) / "code"
            primary_checkout = code_root / "33GOD"
            primary_platform = primary_checkout / "33god-platform"
            primary_component = primary_checkout / "lifecycle"
            external_component = code_root / "skillex"
            nested_checkout = (
                primary_checkout
                / "worktrees/team-prometheus/worktrees/worktree-prof-fiddlesticks"
            )
            nested_platform = nested_checkout / "33god-platform"
            nested_component = nested_checkout / "lifecycle"
            linked_git_dir = primary_checkout / ".git/worktrees/prof-fiddlesticks"

            for path in (
                primary_platform,
                primary_component,
                external_component,
                nested_platform,
                nested_component,
                linked_git_dir,
            ):
                path.mkdir(parents=True)
            (nested_checkout / ".git").write_text(
                f"gitdir: {linked_git_dir}\n", encoding="utf-8"
            )
            (linked_git_dir / "commondir").write_text("../..\n", encoding="utf-8")
            (primary_component / "compose.yml").touch()

            source_root = platform.discover_primary_checkout_root(nested_checkout)
            self.assertEqual(source_root, primary_checkout)
            with (
                patch.object(
                    platform,
                    "SOURCE_PLATFORM_ROOT",
                    source_root / "33god-platform",
                ),
                patch.object(platform, "SOURCE_ROOT_IS_EXPLICIT", False),
                patch.object(platform, "ROOT", nested_platform),
            ):
                self.assertEqual(
                    platform.resolve_path("../lifecycle"), nested_component
                )
                self.assertEqual(
                    platform.resolve_path("../lifecycle/compose.yml"),
                    primary_component / "compose.yml",
                )
                self.assertEqual(
                    platform.resolve_path("../../skillex"), external_component
                )

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
                patch.object(platform, "SOURCE_PLATFORM_ROOT", source_platform),
                patch.object(platform, "SOURCE_ROOT_IS_EXPLICIT", True),
                patch.object(platform, "ROOT", checkout_platform),
            ):
                self.assertFalse(source_repo.exists())
                self.assertEqual(platform.resolve_path("../lifecycle"), source_repo)

    def test_worker_checkout_fallback_handles_new_selected_component(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_platform = root / "source/33god-platform"
            checkout_platform = root / "checkout/33god-platform"
            checkout_repo = root / "checkout/lifecycle"
            for path in (source_platform, checkout_platform, checkout_repo):
                path.mkdir(parents=True)
            with (
                patch.object(platform, "SOURCE_PLATFORM_ROOT", source_platform),
                patch.object(platform, "SOURCE_ROOT_IS_EXPLICIT", False),
                patch.object(platform, "ROOT", checkout_platform),
            ):
                self.assertEqual(platform.resolve_path("../lifecycle"), checkout_repo)


if __name__ == "__main__":
    unittest.main()
