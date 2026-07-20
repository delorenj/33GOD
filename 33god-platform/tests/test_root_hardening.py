from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


platform = load_script(
    "root_hardening_platform", ROOT / "33god-platform/scripts/platform.py"
)
drift = load_script("root_hardening_drift", ROOT / "scripts/check-doc-drift.py")


class GitFixtureMixin:
    @staticmethod
    def git(repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout.strip()

    @classmethod
    def init_repo(
        cls, repo: Path, *, content: str = "one\n", origin: str | None = None
    ) -> str:
        repo.mkdir(parents=True)
        cls.git(repo, "init", "-q")
        cls.git(repo, "config", "user.name", "Root Hardening Test")
        cls.git(repo, "config", "user.email", "root-hardening@example.invalid")
        if origin is not None:
            cls.git(repo, "remote", "add", "origin", origin)
        (repo / "tracked.txt").write_text(content, encoding="utf-8")
        cls.git(repo, "add", "tracked.txt")
        cls.git(repo, "commit", "-qm", "initial")
        return cls.git(repo, "rev-parse", "HEAD")


class ProcessAndEnvironmentHardeningTests(GitFixtureMixin, unittest.TestCase):
    @staticmethod
    def process_is_gone(pid: int) -> bool:
        try:
            state = Path(f"/proc/{pid}/stat").read_text(encoding="ascii").split()[2]
        except (FileNotFoundError, ProcessLookupError):
            return True
        return state == "Z"

    def test_both_git_wrappers_kill_exited_leader_descendants_for_all_limits(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake_git = root / "git"
            fake_git.write_text(
                "#!/usr/bin/env python3\n"
                "import os, subprocess, sys\n"
                "code = '''import os, sys, time\n"
                "open(os.environ[\"DESCENDANT_PID\"], \"w\", encoding=\"ascii\").write(str(os.getpid()))\n"
                "mode = os.environ[\"DESCENDANT_MODE\"]\n"
                "if mode == \"stdout\": os.write(1, b\"PRIVATE-DESCENDANT\" * 512)\n"
                "if mode == \"stderr\": os.write(2, b\"PRIVATE-DESCENDANT\" * 512)\n"
                "time.sleep(30)\n'''\n"
                "subprocess.Popen([sys.executable, '-c', code])\n",
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            wrappers = (
                (
                    "platform",
                    platform,
                    lambda: platform._run_git_bytes(
                        root, "status", stdout_limit=128, stderr_limit=128
                    ),
                ),
                (
                    "drift",
                    drift,
                    lambda: drift._run_git_process(
                        root,
                        "status",
                        stdout_limit=128,
                        stderr_limit=128,
                    ),
                ),
            )
            for wrapper_name, module, invoke in wrappers:
                for mode in ("stdout", "stderr", "timeout"):
                    with self.subTest(wrapper=wrapper_name, mode=mode):
                        pid_file = root / f"{wrapper_name}-{mode}.pid"
                        environment = {
                            "PATH": f"{root}{os.pathsep}{os.environ['PATH']}",
                            "DESCENDANT_PID": str(pid_file),
                            "DESCENDANT_MODE": mode,
                        }
                        started = time.monotonic()
                        with (
                            patch.dict(os.environ, environment, clear=False),
                            patch.object(module, "GIT_TIMEOUT_SECONDS", 0.25),
                            self.assertRaises((RuntimeError, ValueError)) as raised,
                        ):
                            invoke()
                        self.assertLess(time.monotonic() - started, 3.0)
                        self.assertNotIn("PRIVATE-DESCENDANT", str(raised.exception))
                        for _ in range(100):
                            if pid_file.exists():
                                break
                            time.sleep(0.01)
                        child_pid = int(pid_file.read_text(encoding="ascii"))
                        self.assertTrue(self.process_is_gone(child_pid))

    def test_both_git_wrappers_strip_every_ambient_git_control(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected_repo = root / "expected"
            decoy_repo = root / "decoy"
            expected = self.init_repo(expected_repo, content="expected\n")
            self.init_repo(decoy_repo, content="decoy\n")
            global_config = root / "global.gitconfig"
            global_config.write_text("[core]\n\tbare = true\n", encoding="utf-8")
            shallow = root / "shallow"
            shallow.write_text("0" * 40 + "\n", encoding="ascii")
            controls = {
                "GIT_DIR": str(decoy_repo / ".git"),
                "GIT_WORK_TREE": str(decoy_repo),
                "GIT_COMMON_DIR": str(decoy_repo / ".git"),
                "GIT_OBJECT_DIRECTORY": str(decoy_repo / ".git/objects"),
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(decoy_repo / ".git/objects"),
                "GIT_SHALLOW_FILE": str(shallow),
                "GIT_REPLACE_REF_BASE": "refs/evil/",
                "GIT_INDEX_FILE": str(decoy_repo / ".git/index"),
                "GIT_CONFIG_GLOBAL": str(global_config),
                "GIT_CONFIG_SYSTEM": str(global_config),
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.bare",
                "GIT_CONFIG_VALUE_0": "true",
            }
            with patch.dict(os.environ, controls, clear=False):
                for module in (platform, drift):
                    environment = module._git_environment()
                    for key, value in controls.items():
                        if key in environment:
                            self.assertNotEqual(environment[key], value)
                self.assertEqual(
                    platform._run_git(expected_repo, "rev-parse", "HEAD").stdout.strip(),
                    expected,
                )
                self.assertEqual(
                    drift.run_git(expected_repo, "rev-parse", "HEAD").stdout.strip(),
                    expected,
                )


class ObjectAndSnapshotHardeningTests(GitFixtureMixin, unittest.TestCase):
    def assert_both_reject_closure(self, repo: Path, revision: str) -> None:
        with self.assertRaises((RuntimeError, ValueError)):
            platform.verify_commit_object_graph(repo, revision)
        with self.assertRaises((RuntimeError, ValueError)):
            drift.verify_commit_object_graph(repo, revision)

    def test_partial_shallow_alternate_and_promisor_sources_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            self.init_repo(source)
            (source / "tracked.txt").write_text("two\n", encoding="utf-8")
            self.git(source, "commit", "-qam", "second")
            shallow = root / "shallow"
            subprocess.run(
                [
                    "git",
                    "clone",
                    "-q",
                    "--depth=1",
                    f"file://{source}",
                    str(shallow),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assert_both_reject_closure(
                shallow, self.git(shallow, "rev-parse", "HEAD")
            )

            promisor = root / "promisor"
            revision = self.init_repo(promisor)
            self.git(promisor, "config", "extensions.partialClone", "origin")
            self.git(promisor, "config", "remote.origin.promisor", "true")
            self.assert_both_reject_closure(promisor, revision)

            alternate = root / "alternate"
            revision = self.init_repo(alternate)
            info = alternate / ".git/objects/info"
            info.mkdir(exist_ok=True)
            (info / "alternates").write_text(
                str(source / ".git/objects") + "\n", encoding="utf-8"
            )
            self.assert_both_reject_closure(alternate, revision)

            promisor_pack = root / "promisor-pack"
            revision = self.init_repo(promisor_pack)
            self.git(promisor_pack, "gc", "--prune=now")
            pack = next((promisor_pack / ".git/objects/pack").glob("*.pack"))
            pack.with_suffix(".promisor").touch()
            self.assert_both_reject_closure(promisor_pack, revision)

    def test_corrupt_packed_object_content_is_rejected(self) -> None:
        for module_name in ("platform", "drift"):
            with self.subTest(module=module_name), tempfile.TemporaryDirectory() as temporary:
                repo = Path(temporary) / "repo"
                revision = self.init_repo(repo, content="packed-content\n" * 100)
                self.git(repo, "gc", "--aggressive", "--prune=now")
                pack = next((repo / ".git/objects/pack").glob("*.pack"))
                payload = bytearray(pack.read_bytes())
                payload[len(payload) // 2] ^= 0x01
                pack.chmod(0o600)
                pack.write_bytes(payload)
                verifier = (
                    platform.verify_commit_object_graph
                    if module_name == "platform"
                    else drift.verify_commit_object_graph
                )
                with self.assertRaises((RuntimeError, ValueError)):
                    verifier(repo, revision)

    def test_platform_and_drift_sessions_hold_one_revision_after_head_moves(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            first = self.init_repo(repo, content="first\n")
            with platform.validation_session():
                self.assertEqual(platform.root_commit_revision(repo), first)
                (repo / "tracked.txt").write_text("second\n", encoding="utf-8")
                self.git(repo, "commit", "-qam", "second")
                self.assertEqual(platform.root_commit_revision(repo), first)

            first = self.git(repo, "rev-parse", "HEAD")
            with drift.validation_session():
                snapshot = drift.git_snapshot(repo)
                self.assertIsNotNone(snapshot)
                (repo / "tracked.txt").write_text("third\n", encoding="utf-8")
                self.git(repo, "commit", "-qam", "third")
                self.assertIs(drift.git_snapshot(repo), snapshot)
                self.assertEqual(drift.checkout_revision(repo), first)


class ComposeAndIdentityHardeningTests(GitFixtureMixin, unittest.TestCase):
    def test_compose_uses_committed_candidate_and_never_reports_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checkout = Path(temporary) / "checkout"
            self.init_repo(checkout)
            validator = checkout / "33god-platform/scripts/validate-compose.py"
            compose = checkout / "33god-platform/compose.yaml"
            validator.parent.mkdir(parents=True)
            validator.write_text(
                "print('COMMITTED-CANDIDATE')\n", encoding="utf-8"
            )
            compose.write_text("services: {}\n", encoding="utf-8")
            self.git(checkout, "add", "33god-platform")
            self.git(checkout, "commit", "-qm", "candidate")

            sentinel = "PRIVATE-CANDIDATE-PAYLOAD"
            validator.write_text(
                f"print('{sentinel}')\nraise SystemExit(17)\n", encoding="utf-8"
            )
            output = io.StringIO()
            with redirect_stdout(output):
                drift.check_compose_candidate(
                    checkout, checkout, drift.Reporter()
                )
            self.assertNotIn(sentinel, output.getvalue())
            self.assertNotIn("candidate validator exited", output.getvalue())

            self.git(checkout, "add", str(validator.relative_to(checkout)))
            self.git(checkout, "commit", "-qm", "published bad candidate")
            output = io.StringIO()
            with redirect_stdout(output):
                drift.check_compose_candidate(
                    checkout, checkout, drift.Reporter()
                )
            self.assertIn("candidate validator exited", output.getvalue())
            self.assertNotIn(sentinel, output.getvalue())

    def test_gitlink_path_swap_after_bound_identity_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            component = root / "component"
            origin = "https://github.com/example/component.git"
            revision = self.init_repo(component, origin=origin)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Root Hardening Test")
            self.git(root, "config", "user.email", "root-hardening@example.invalid")
            (root / ".gitmodules").write_text(
                '[submodule "component"]\n\tpath = component\n'
                f"\turl = {origin}\n",
                encoding="utf-8",
            )
            self.git(
                root,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{revision},component",
            )
            self.git(root, "add", ".gitmodules")
            self.git(root, "commit", "-qm", "gitlink")
            original = platform.bound_git_checkout_identity
            swapped = False

            def swap_after_read(bound: object) -> tuple[str | None, str | None]:
                nonlocal swapped
                result = original(bound)
                if not swapped:
                    displaced = root / "component-displaced"
                    component.rename(displaced)
                    component.mkdir()
                    swapped = True
                return result

            with (
                patch.object(platform, "SOURCE_ROOT", root),
                patch.object(
                    platform,
                    "ROOT_GITLINK_CONTRACTS",
                    {"component": (origin, revision)},
                ),
                patch.object(
                    platform,
                    "bound_git_checkout_identity",
                    side_effect=swap_after_read,
                ),
            ):
                errors = platform.validate_gitlink_inventory()
            self.assertTrue(any("changed during identity validation" in item for item in errors))


class PolicyAndTraversalHardeningTests(GitFixtureMixin, unittest.TestCase):
    @staticmethod
    def write_momo_fixture(root: Path, workflow_text: str = "bounded client\n") -> None:
        description = (
            "Bounded Lifecycle client for choosing and ranking only "
            "Lifecycle-legal work and executing only Lifecycle-legal work."
        )
        roots = (
            root / "momo/_bmad/custom/workflows/ticket-lifecycle",
            root / "momo/_bmad/_config/custom/custom/workflows/ticket-lifecycle",
        )
        for workflow_root in roots:
            workflow_root.mkdir(parents=True, exist_ok=True)
            (workflow_root / "workflow.md").write_text(
                workflow_text, encoding="utf-8"
            )
        config = root / "momo/_bmad/_config"
        (config / "workflow-manifest.csv").write_text(
            "name,description,module,path\n"
            f'"ticket-lifecycle","{description}","custom",'
            '"_bmad/custom/workflows/ticket-lifecycle/workflow.md"\n',
            encoding="utf-8",
        )
        digest = __import__("hashlib").sha256(workflow_text.encode()).hexdigest()
        (config / "files-manifest.csv").write_text(
            "type,name,module,path,hash\n"
            '"md","workflow","custom","custom/workflows/'
            f'ticket-lifecycle/workflow.md","{digest}"\n',
            encoding="utf-8",
        )

    def test_unicode_structural_identities_are_enforced_in_csv_and_yaml(self) -> None:
        variants = (
            "ticket‐lifecycle",
            "ticket.lifecycle",
            "ｔｉｃｋｅｔ－ｌｉｆｅｃｙｃｌｅ",
            "ticket lifecycle",
            "ticket/lifecycle",
            "ticket_lifecycle",
            "ticket-lifecycle",
            "ticketlifecycle",
        )
        for variant in variants:
            self.assertTrue(drift.has_ticket_lifecycle_identity(variant), variant)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_fixture(root)
            config = root / "bloodbank/_bmad/_config"
            config.mkdir(parents=True)
            (config / "workflow-manifest.csv").write_text(
                'name,description\n"ticket‐lifecycle","quoted row"\n',
                encoding="utf-8",
            )
            (config / "files-manifest.yaml").write_text(
                "workflows:\n  - name: ｔｉｃｋｅｔ．ｌｉｆｅｃｙｃｌｅ\n",
                encoding="utf-8",
            )
            errors = drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(any("bloodbank registers non-Momo" in item for item in errors))

    def test_momo_duplicate_unicode_identity_and_invalid_non_momo_utf8_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_fixture(root)
            manifest = root / "momo/_bmad/_config/workflow-manifest.csv"
            with manifest.open("a", encoding="utf-8") as handle:
                handle.write(
                    '"ticket．lifecycle","duplicate","custom","other.md"\n'
                )
            errors = drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(any("exactly one canonical" in item for item in errors))

            manifest.write_bytes(b"name,description\n\xff,invalid\n")
            errors = drift.ticket_lifecycle_surface_errors(root)
            self.assertTrue(any("valid UTF-8" in item or "malformed" in item for item in errors))

    def test_negated_holocene_copy_is_allowed_but_positive_copy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_momo_fixture(root, "Never store a copy in Holocene.\n")
            self.assertFalse(
                any(
                    "Holocene copy claim" in item
                    for item in drift.ticket_lifecycle_surface_errors(root)
                )
            )
            self.write_momo_fixture(root, "Store a copy in Holocene.\n")
            self.assertTrue(
                any(
                    "Holocene copy claim" in item
                    for item in drift.ticket_lifecycle_surface_errors(root)
                )
            )

    def test_exact_promoted_prefix_rejects_blob_symlink_and_gitlink_modes(self) -> None:
        for prefix in ("agents/hermes/pm", "pipeline-mcp-hub"):
            for mode in ("blob", "symlink", "gitlink"):
                with (
                    self.subTest(prefix=prefix, mode=mode),
                    tempfile.TemporaryDirectory() as temporary,
                ):
                    repo = Path(temporary) / "repo"
                    self.init_repo(repo)
                    target = repo / prefix
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if mode == "blob":
                        target.write_text("not a directory\n", encoding="utf-8")
                        self.git(repo, "add", prefix)
                    elif mode == "symlink":
                        target.symlink_to("tracked.txt")
                        self.git(repo, "add", prefix)
                    else:
                        self.git(
                            repo,
                            "update-index",
                            "--add",
                            "--cacheinfo",
                            f"160000,{'1' * 40},{prefix}",
                        )
                    self.git(repo, "commit", "-qm", f"{mode} prefix")
                    revision = self.git(repo, "rev-parse", "HEAD")
                    errors = drift.scan_operational_repository(
                        repo,
                        "root",
                        repo,
                        tracked_prefix=prefix,
                        revision=revision,
                    )
                    self.assertTrue(any("prefix is not a directory" in item for item in errors))

    def test_nested_gitlink_with_symlink_ancestor_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested = root / "real-vendor/runtime"
            nested_revision = self.init_repo(nested)
            component = root / "component"
            component.mkdir()
            self.git(component, "init", "-q")
            self.git(component, "config", "user.name", "Root Hardening Test")
            self.git(component, "config", "user.email", "root-hardening@example.invalid")
            self.git(
                component,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{nested_revision},vendor/runtime",
            )
            self.git(component, "commit", "-qm", "nested gitlink")
            (component / "vendor").symlink_to(root / "real-vendor", target_is_directory=True)
            revision = self.git(component, "rev-parse", "HEAD")
            errors = drift.scan_gitlink_tree("component", component, revision)
            self.assertTrue(any("symlink ancestor" in item for item in errors))


class BackfillHardeningTests(unittest.TestCase):
    def test_fifo_swap_and_ancestor_symlink_fail_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fifo = root / "pipe"
            os.mkfifo(fifo)
            started = time.monotonic()
            with self.assertRaises(ValueError):
                platform.read_bounded_regular_file(fifo)
            self.assertLess(time.monotonic() - started, 1.0)

            target = root / "target.txt"
            target.write_text("first\n", encoding="utf-8")
            candidate = platform.iter_search_candidates([str(target)])[0]
            target.rename(root / "original.txt")
            target.write_text("replacement\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed after backfill enumeration"):
                platform.read_bounded_regular_file(candidate)

            real = root / "real"
            real.mkdir()
            (real / "file.txt").write_text("data\n", encoding="utf-8")
            (root / "linked").symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                platform.iter_search_candidates([str(root / "linked/file.txt")])

    def test_glob_and_invocation_resource_bounds_fail_closed_iteratively(self) -> None:
        with self.assertRaisesRegex(ValueError, "pattern length"):
            list(platform.iter_backfill_glob("x" * 4097))
        with self.assertRaisesRegex(ValueError, "recursive wildcard"):
            list(platform.iter_backfill_glob("/" + "/".join(["**"] * 65)))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "one.txt").write_text("one\n", encoding="utf-8")
            (root / "two.txt").write_text("two\n", encoding="utf-8")
            budget = platform.ValidationBudget(max_entries=1)
            with self.assertRaisesRegex(ValueError, "entries bound"):
                platform.iter_search_candidates([str(root)], budget)

    def test_every_aggregate_resource_dimension_has_a_real_negative_control(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.txt"
            second = root / "second.txt"
            first.write_text("first second\n", encoding="utf-8")
            second.write_text("second\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "search-path bound"):
                platform.iter_search_candidates(
                    [str(first)] * (platform.MAX_BACKFILL_SEARCH_PATHS + 1)
                )
            with self.assertRaisesRegex(ValueError, "files bound"):
                platform.iter_search_candidates(
                    [str(root)], platform.ValidationBudget(max_files=1)
                )
            with self.assertRaisesRegex(ValueError, "matches bound"):
                platform.iter_search_candidates(
                    [str(root / "*.txt")],
                    platform.ValidationBudget(max_matches=1),
                )
            candidate = platform.iter_search_candidates([str(first)])[0]
            with self.assertRaisesRegex(ValueError, "retained bytes bound"):
                platform.read_bounded_regular_file(
                    candidate,
                    platform.ValidationBudget(max_retained_bytes=1),
                )

            manifest = root / "manifest.yaml"
            manifest.write_text(
                "id: bounds\n"
                f"search_paths:\n  - {first}\n"
                "forbidden_patterns:\n  - first\n  - second\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "findings bound"):
                platform.scan_backfill(
                    manifest, platform.ValidationBudget(max_findings=1)
                )
            with (
                patch.object(platform, "MAX_BACKFILL_PATTERNS", 1),
                self.assertRaisesRegex(ValueError, "forbidden_patterns"),
            ):
                platform.scan_backfill(manifest)

            with platform.validation_session() as state:
                state.budget.max_git_calls = 0
                with self.assertRaisesRegex(ValueError, "git calls bound"):
                    platform._run_git(ROOT, "rev-parse", "HEAD")
            with self.assertRaisesRegex(ValueError, "time bound"):
                platform.iter_search_candidates(
                    [str(first)], platform.ValidationBudget(wall_seconds=0)
                )

            stderr = io.StringIO()
            with (
                patch.object(platform, "MAX_BACKFILL_MANIFESTS", 1),
                patch.object(
                    platform,
                    "contained_platform_files",
                    return_value=[manifest, manifest],
                ),
                redirect_stderr(stderr),
            ):
                self.assertEqual(platform.cmd_backfills_check(None), 1)
            self.assertIn("manifest count", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
