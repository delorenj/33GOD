from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import subprocess
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


class PlatformValidationFailureTests(unittest.TestCase):
    @staticmethod
    def component(repo: str, *, revision: str | None = None) -> dict[str, object]:
        item: dict[str, object] = {
            "id": "component",
            "name": "Component",
            "role": "test",
            "repo": repo,
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
                patch.object(platform, "acceptance_slice_ids", return_value=["component"]),
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
            self.assertTrue(any("compose file does not exist" in item for item in errors))


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
        mapped_path = component.relative_to(root).as_posix()
        (root / ".gitmodules").write_text(
            f'[submodule "{mapped_path}"]\n'
            f"\tpath = {mapped_path}\n"
            f"\turl = {url}\n",
            encoding="utf-8",
        )
        self.git(
            root,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{revision},{mapped_path}",
        )

    def test_plain_child_cannot_inherit_wrapper_git_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wrapper = root / "wrapper"
            wrapper.mkdir()
            self.git(wrapper, "init", "-q")
            child = wrapper / "component"
            child.mkdir()
            self.assertIsNone(platform.git_checkout_revision(child))

    def test_exact_gitlink_head_and_origin_are_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            component = source / "component"
            url = "https://github.com/example/component.git"
            revision = self.init_repo(
                component, "git@github.com:example/component.git"
            )
            self.configure_superproject(source, component, revision, url)
            component_data = {
                "id": "component",
                "repo": "../component",
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
            revision = self.init_repo(
                component, "git@github.com:example/component.git"
            )
            self.configure_superproject(source, component, revision, url)
            with patch.object(platform, "SOURCE_ROOT", source):
                self.assertEqual(platform.validate_gitlink_inventory(), [])

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
            with patch.object(platform, "SOURCE_ROOT", source):
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
            with patch.object(platform, "SOURCE_ROOT", source):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(
                any(
                    "root gitlink component" in item
                    and "does not match index revision" in item
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
            with patch.object(platform, "SOURCE_ROOT", source):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(
                any(
                    "root gitlink component" in item
                    and "does not match .gitmodules URL" in item
                    for item in errors
                )
            )

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
            (source / ".gitmodules").write_text("[broken\n", encoding="utf-8")
            with patch.object(platform, "SOURCE_ROOT", source):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(any("cannot parse" in item for item in errors))

    def test_duplicate_gitmodule_paths_fail_as_ambiguous_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            self.git(source, "init", "-q")
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
            with patch.object(platform, "SOURCE_ROOT", source):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(
                any(
                    "ambiguous duplicate submodule path 'shared'" in item
                    for item in errors
                )
            )

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
            platform.normalize_repository_url(item["url"])
            for item in mappings.values()
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
                platform.normalize_repository_url(
                    platform.git_checkout_origin(checkout) or ""
                ),
                platform.normalize_repository_url(mappings[path]["url"]),
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
