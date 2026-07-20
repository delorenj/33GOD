#!/usr/bin/env python3
"""33GOD platform manifest, changelog, and backfill utility."""

from __future__ import annotations

import argparse
import configparser
import fnmatch
import glob
import json
import os
import re
import stat
import subprocess
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, NamedTuple
from urllib.parse import urlsplit

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from scripts.validation_runtime import (  # noqa: E402
    BoundDirectory,
    BoundedProcessError,
    ValidationBudget,
    open_bound_directory,
    run_bounded_process,
    sanitized_git_environment,
    terminate_process_group,
    verify_local_git_object_closure,
)

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc


ROOT = Path(__file__).resolve().parents[1]

_BoundedProcessError = BoundedProcessError
_run_bounded_process = run_bounded_process
_terminate_process_group = terminate_process_group


class PlatformValidationState:
    """One command's exact Git views and aggregate resource budget."""

    def __init__(self) -> None:
        self.budget = ValidationBudget()
        self.checkout_roots: dict[str, Path | None] = {}
        self.revisions: dict[str, str] = {}
        self.root_trees: dict[
            tuple[str, str], dict[str, tuple[str, str, str]]
        ] = {}
        self.platform_snapshots: dict[
            tuple[str, str], dict[str, tuple[str, str, int]] | None
        ] = {}


_ACTIVE_VALIDATION_STATE: ContextVar[PlatformValidationState | None] = ContextVar(
    "platform_validation_state", default=None
)


@contextmanager
def validation_session() -> Iterator[PlatformValidationState]:
    existing = _ACTIVE_VALIDATION_STATE.get()
    if existing is not None:
        yield existing
        return
    state = PlatformValidationState()
    token = _ACTIVE_VALIDATION_STATE.set(state)
    try:
        yield state
    finally:
        _ACTIVE_VALIDATION_STATE.reset(token)


def _validation_state() -> PlatformValidationState | None:
    return _ACTIVE_VALIDATION_STATE.get()


def _repository_key(repo: Path) -> str:
    return os.path.abspath(os.fspath(repo))

# The selected source root is exactly one checkout. An explicit GOD_SOURCE_ROOT
# is authoritative; otherwise the checkout that contains this 33god-platform
# directory is selected. Resolution never borrows component leaves from any
# other checkout (including the primary checkout of a linked-worktree chain).
_EXPLICIT_SOURCE_ROOT = os.environ.get("GOD_SOURCE_ROOT")
SOURCE_ROOT_IS_EXPLICIT = bool(_EXPLICIT_SOURCE_ROOT)
SOURCE_ROOT = (
    Path(_EXPLICIT_SOURCE_ROOT).expanduser().resolve()
    if _EXPLICIT_SOURCE_ROOT
    else ROOT.parent.resolve()
)
SOURCE_PLATFORM_ROOT = SOURCE_ROOT / "33god-platform"

# True external siblings (for example ../../skillex and ../../HeyMa) escape the
# selected source root. They resolve only through this external-root policy:
# an explicit GOD_EXTERNAL_ROOT when set, else the selected root's parent.
_EXPLICIT_EXTERNAL_ROOT = os.environ.get("GOD_EXTERNAL_ROOT")
EXTERNAL_ROOT_IS_EXPLICIT = bool(_EXPLICIT_EXTERNAL_ROOT)
EXTERNAL_ROOT = (
    Path(_EXPLICIT_EXTERNAL_ROOT).expanduser().resolve()
    if _EXPLICIT_EXTERNAL_ROOT
    else SOURCE_ROOT.parent
)
MAX_SCAN_FILE_BYTES = 1_000_000
GIT_TIMEOUT_SECONDS = 10
MAX_GIT_OUTPUT_BYTES = 16_000_000
MAX_GIT_TREE_ENTRIES = 100_000
MAX_BACKFILL_ENTRIES = 100_000
MAX_BACKFILL_FILES = 25_000
MAX_BACKFILL_MANIFESTS = 1_000
MAX_BACKFILL_PATTERNS = 1_000
MAX_BACKFILL_SEARCH_PATHS = 1_000
MAX_BACKFILL_PATTERN_LENGTH = 4_096
MAX_BACKFILL_PATTERN_COMPONENTS = 128
MAX_BACKFILL_RECURSIVE_DEPTH = 64
BACKFILL_EXCLUDED_PARTS = {
    ".cache",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "cache",
    "caches",
    "dist",
    "node_modules",
    "venv",
}
BACKFILL_EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
FULL_GIT_REVISION = re.compile(r"[0-9a-f]{40}")
LIFECYCLE_ACCEPTANCE_SLICE = (
    "bloodbank",
    "lifecycle",
    "candystore",
    "momo",
    "holocene",
    "pjangler",
)
PRODUCT_COMPONENT_IDS = (
    *LIFECYCLE_ACCEPTANCE_SLICE,
    "hermes-fleet",
    "skillex",
    "hindsight",
    "pipeline-mcp-hub",
    "candybar",
    "heyma",
)
COMPONENT_FILE_PATHS = tuple(
    f"components/{component_id}.yaml" for component_id in PRODUCT_COMPONENT_IDS
)
COMPONENT_CONTRACTS: dict[str, dict[str, str | None]] = {
    "bloodbank": {
        "role": "schema-contract-transport",
        "repo": "../bloodbank",
        "repository_kind": "root-gitlink",
        "revision_field": "source_revision",
        "revision": "aacd88564ea299924b8298165933ba821640bdba",
        "repository_origin": None,
    },
    "lifecycle": {
        "role": "project-lifecycle-authority",
        "repo": "../lifecycle",
        "repository_kind": "root-gitlink",
        "revision_field": "gitlink_revision",
        "revision": "cda59658bef6d586c8aa01cacd88bc4e3ee867e0",
        "repository_origin": None,
    },
    "candystore": {
        "role": "audit-and-read-projection",
        "repo": "../candystore",
        "repository_kind": "root-gitlink",
        "revision_field": "source_revision",
        "revision": "3c00080446bb9d4cb55c670477983306abcfe7ce",
        "repository_origin": None,
    },
    "momo": {
        "role": "legal-work-chooser-executor",
        "repo": "../momo",
        "repository_kind": "root-gitlink",
        "revision_field": "source_revision",
        "revision": "8eeff1ce839c3bcffc2d3943322bc1dd8ef63fee",
        "repository_origin": None,
    },
    "holocene": {
        "role": "dashboard-renderer",
        "repo": "../holocene",
        "repository_kind": "root-gitlink",
        "revision_field": "source_revision",
        "revision": "2beee67b433f1bd66abf7bce552d90e89413ae27",
        "repository_origin": None,
    },
    "pjangler": {
        "role": "project-identity-bootstrap-bindings",
        "repo": "../pjangler",
        "repository_kind": "root-gitlink",
        "revision_field": "source_revision",
        "revision": "13be237eaa454f22525dd9b4e5dd804b4516c212",
        "repository_origin": None,
    },
    "hermes-fleet": {
        "role": "agent-runtime-fleet",
        "repo": "../hermes-agent-template",
        "repository_kind": "root-gitlink",
        "revision_field": "gitlink_revision",
        "revision": "576327ede2bf0686338fa8eb2735d1e16d03e870",
        "repository_origin": None,
    },
    "skillex": {
        "role": "skill-distribution",
        "repo": "../../skillex",
        "repository_kind": "external-git",
        "revision_field": "source_revision",
        "revision": "8b2f3d2f309c15f7bfcfe981c3dbeae87c50e371",
        "repository_origin": "https://github.com/delorenj/skillex.git",
    },
    "hindsight": {
        "role": "persistent-memory",
        "repo": "~/.agents",
        "repository_kind": "local-runtime",
        "revision_field": None,
        "revision": None,
        "repository_origin": None,
    },
    "pipeline-mcp-hub": {
        "role": "tool-dispatch-gateway",
        "repo": "../pipeline-mcp-hub",
        "repository_kind": "in-tree-source",
        "revision_field": None,
        "revision": None,
        "repository_origin": None,
    },
    "candybar": {
        "role": "topology-visualization",
        "repo": "../candybar",
        "repository_kind": "root-gitlink",
        "revision_field": "gitlink_revision",
        "revision": "509c03f350b5d41ec7a6779a3233dd61c9cbee91",
        "repository_origin": None,
    },
    "heyma": {
        "role": "voice-interface",
        "repo": "../../HeyMa",
        "repository_kind": "external-git",
        "revision_field": "source_revision",
        "revision": "c154bb8b1b4fb2909f6c5d91168a0c2a17298191",
        "repository_origin": "https://github.com/delorenj/HeyMa.git",
    },
}
ROOT_GITLINK_CONTRACTS: dict[str, tuple[str, str]] = {
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


class GitValidationError(ValueError):
    """A deterministic, secret-free Git provenance failure."""


class BackfillCandidate(NamedTuple):
    """One enumerated regular-file inode and its descriptor-relative path."""

    path: Path
    anchor: Path
    relative: PurePosixPath
    device: int
    inode: int


class DuplicateYamlKeyError(ValueError):
    """A YAML mapping repeated a key at some nesting level."""


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: Any, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise DuplicateYamlKeyError("duplicate YAML mapping key")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_yaml_text(text: str, label: str) -> dict[str, Any]:
    try:
        data = yaml.load(text, Loader=_UniqueKeyLoader)
    except DuplicateYamlKeyError as exc:
        raise ValueError(f"{label}: duplicate YAML mapping key") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"{label}: invalid YAML") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{label}: expected YAML mapping")
    return data


def load_yaml(path: Path) -> dict[str, Any]:
    return load_yaml_text(
        path.read_text(encoding="utf-8", errors="strict"), str(path)
    )


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def lexical_path(path: Path) -> Path:
    """Normalize ``.``/``..`` without following symlinks."""

    return Path(os.path.abspath(os.fspath(path)))


def contained_platform_input(relative: str | Path, *, kind: str) -> Path:
    """Resolve one real, symlink-free input inside the selected platform tree."""

    relative_path = PurePosixPath(str(relative))
    if (
        relative_path.is_absolute()
        or not relative_path.parts
        or any(part in {"", ".", ".."} for part in relative_path.parts)
    ):
        raise ValueError(f"33god-platform input path is not canonical: {relative}")
    platform_lexical = lexical_path(SOURCE_PLATFORM_ROOT)
    candidate = lexical_path(platform_lexical / Path(*relative_path.parts))
    if not is_within(candidate, platform_lexical):
        raise ValueError(f"33god-platform input escapes selected tree: {relative}")
    try:
        platform_resolved = SOURCE_PLATFORM_ROOT.resolve(strict=True)
    except OSError as exc:
        raise ValueError("selected 33god-platform root cannot be resolved") from exc
    if SOURCE_PLATFORM_ROOT.is_symlink() or not SOURCE_PLATFORM_ROOT.is_dir():
        raise ValueError("selected 33god-platform root must be a real directory")
    cursor = SOURCE_PLATFORM_ROOT
    for part in relative_path.parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError(
                f"33god-platform input must not traverse a symlink: {relative}"
            )
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ValueError(
            f"33god-platform input is missing or unreadable: {relative}"
        ) from exc
    if not is_within(resolved, platform_resolved):
        raise ValueError(f"33god-platform input escapes selected tree: {relative}")
    if kind == "file" and not candidate.is_file():
        raise ValueError(f"33god-platform input must be a real file: {relative}")
    if kind == "directory" and not candidate.is_dir():
        raise ValueError(f"33god-platform input must be a real directory: {relative}")
    if kind not in {"file", "directory"}:
        raise ValueError("invalid contained platform input kind")
    return resolved


def contained_platform_files(directory: str, pattern: str) -> list[Path]:
    snapshot = committed_platform_snapshot()
    if snapshot is not None:
        prefix = directory.rstrip("/") + "/"
        relatives = [
            path
            for path in snapshot
            if path.startswith(prefix)
            and "/" not in path.removeprefix(prefix)
            and fnmatch.fnmatchcase(path.removeprefix(prefix), pattern)
        ]
        return [lexical_path(SOURCE_PLATFORM_ROOT / path) for path in sorted(relatives)]
    root = contained_platform_input(directory, kind="directory")
    paths: list[Path] = []
    for candidate in sorted(root.glob(pattern)):
        relative = candidate.relative_to(SOURCE_PLATFORM_ROOT.resolve()).as_posix()
        paths.append(contained_platform_input(relative, kind="file"))
    return paths


def resolve_external_path(candidate: Path) -> Path:
    """Resolve a selected path that escapes the source root.

    External siblings (for example ../../skillex) resolve beneath
    EXTERNAL_ROOT only; there is no fallback into any other checkout.
    """
    candidate = lexical_path(candidate)
    source_resolved = SOURCE_ROOT.resolve()
    external_resolved = EXTERNAL_ROOT.resolve()
    if is_within(external_resolved, source_resolved):
        raise ValueError("GOD_EXTERNAL_ROOT must be outside GOD_SOURCE_ROOT")
    try:
        relative = candidate.relative_to(SOURCE_ROOT.parent)
    except ValueError as exc:
        raise ValueError(
            f"external path escapes the supported sibling boundary: {candidate}"
        ) from exc
    mapped = lexical_path(EXTERNAL_ROOT / relative)
    if not is_within(mapped, EXTERNAL_ROOT):
        raise ValueError(f"external path escapes GOD_EXTERNAL_ROOT: {mapped}")
    resolved = mapped.resolve()
    if is_within(resolved, source_resolved):
        raise ValueError(
            f"external path re-enters GOD_SOURCE_ROOT through policy mapping: {mapped}"
        )
    if not is_within(resolved, EXTERNAL_ROOT):
        raise ValueError(
            f"external path resolves outside GOD_EXTERNAL_ROOT: {mapped} -> {resolved}"
        )
    return resolved


def resolve_path(value: str | Path, base: Path | None = None) -> Path:
    raw = os.path.expandvars(os.path.expanduser(str(value)))
    path = Path(raw)
    if path.is_absolute():
        # Explicit absolute registry paths (notably Hindsight's ~/.agents)
        # intentionally remain supported. Relative paths alone are governed
        # by the selected source/external-root containment policy below.
        return path.resolve()

    selected_base = SOURCE_PLATFORM_ROOT if base is None else base
    anchor = (
        SOURCE_PLATFORM_ROOT if path.parts and path.parts[0] == ".." else selected_base
    )
    candidate = lexical_path(anchor / path)
    if not is_within(candidate, SOURCE_ROOT):
        return resolve_external_path(candidate)

    # In-tree component roots are atomic: every relative descendant stays
    # beneath the selected checkout after lexical normalization and symlink
    # resolution, so missing leaves cannot be borrowed from another checkout.
    resolved = candidate.resolve()
    if not is_within(resolved, SOURCE_ROOT):
        raise ValueError(
            "selected in-tree path resolves outside GOD_SOURCE_ROOT: "
            f"{candidate} -> {resolved}"
        )
    return resolved


def load_platform_yaml(
    relative: str | Path,
    *,
    snapshot: dict[str, tuple[str, str, int]] | None = None,
) -> dict[str, Any]:
    relative_text = PurePosixPath(str(relative)).as_posix()
    return load_yaml_text(
        platform_input_text(relative_text, snapshot=snapshot),
        str(lexical_path(SOURCE_PLATFORM_ROOT / relative_text)),
    )


def platform_config() -> dict[str, Any]:
    snapshot = committed_platform_snapshot()
    return load_platform_yaml("components.yaml", snapshot=snapshot)


def component_paths() -> list[Path]:
    snapshot = committed_platform_snapshot()
    cfg = platform_config()
    declared = cfg.get("component_files")
    if not isinstance(declared, list) or not all(
        isinstance(item, str) for item in declared
    ):
        raise ValueError("components.yaml: component_files must be a list of paths")
    if tuple(declared) != COMPONENT_FILE_PATHS:
        raise ValueError(
            "components.yaml: component_files must be the exact ordered manifest "
            f"paths {COMPONENT_FILE_PATHS}; found {tuple(declared)}"
        )
    if snapshot is None:
        return [contained_platform_input(item, kind="file") for item in declared]
    missing = [item for item in declared if item not in snapshot]
    if missing:
        raise ValueError(
            "committed component manifests are missing: " + ", ".join(missing)
        )
    return [lexical_path(SOURCE_PLATFORM_ROOT / item) for item in declared]


def load_components() -> list[dict[str, Any]]:
    snapshot = committed_platform_snapshot()
    cfg = platform_config()
    declared = cfg.get("component_files")
    if not isinstance(declared, list) or not all(
        isinstance(item, str) for item in declared
    ):
        raise ValueError("components.yaml: component_files must be a list of paths")
    if tuple(declared) != COMPONENT_FILE_PATHS:
        raise ValueError(
            "components.yaml: component_files must be the exact ordered manifest "
            f"paths {COMPONENT_FILE_PATHS}; found {tuple(declared)}"
        )
    components: list[dict[str, Any]] = []
    for relative in declared:
        path = lexical_path(SOURCE_PLATFORM_ROOT / relative)
        data = load_platform_yaml(relative, snapshot=snapshot)
        data["_path"] = path
        components.append(data)
    return components


def recorded_revision(component: dict[str, Any]) -> str | None:
    values: dict[str, str] = {}
    for field in ("source_revision", "gitlink_revision"):
        value = component.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not FULL_GIT_REVISION.fullmatch(value):
            raise ValueError(f"{field} must be an exact lowercase 40-hex revision")
        values[field] = value
    if len(set(values.values())) > 1:
        raise ValueError("conflicting revision fields source_revision/gitlink_revision")
    return next(iter(values.values()), None)


def acceptance_slice_ids(cfg: dict[str, Any] | None = None) -> list[str]:
    cfg = platform_config() if cfg is None else cfg
    declaration = cfg.get("acceptance_slice") or {}
    if not isinstance(declaration, dict):
        return []
    components = declaration.get("components") or []
    if not isinstance(components, list):
        return []
    return [str(item) for item in components]


def _git_environment() -> dict[str, str]:
    return sanitized_git_environment()


def _run_git_bytes(
    repo: Path,
    *args: str,
    input_bytes: bytes | None = None,
    stdout_limit: int = MAX_GIT_OUTPUT_BYTES,
    stderr_limit: int = MAX_GIT_OUTPUT_BYTES,
    allowed_returncodes: frozenset[int] = frozenset({0}),
    pass_fds: tuple[int, ...] = (),
) -> subprocess.CompletedProcess[bytes]:
    operation = args[0] if args else "git"
    state = _validation_state()
    timeout = GIT_TIMEOUT_SECONDS
    if state is not None:
        state.budget.consume("git_calls")
        timeout = state.budget.remaining_seconds(GIT_TIMEOUT_SECONDS)
    try:
        result = _run_bounded_process(
            ["git", "-C", str(repo), *args],
            input_bytes=input_bytes,
            stdout_limit=stdout_limit,
            stderr_limit=stderr_limit,
            timeout=timeout,
            env=_git_environment(),
            pass_fds=pass_fds,
        )
    except _BoundedProcessError as exc:
        if exc.reason == "output":
            raise GitValidationError(
                f"Git command output exceeded its safe bound for {repo}: {operation}"
            ) from exc
        raise GitValidationError(
            f"Git command failed safely for {repo}: {operation}"
        ) from exc
    except OSError as exc:
        raise GitValidationError(
            f"Git command failed safely for {repo}: {operation}"
        ) from exc
    if result.returncode not in allowed_returncodes:
        raise GitValidationError(
            f"Git command failed safely for {repo}: {operation}"
        )
    return result


def _run_git(
    repo: Path,
    *args: str,
    allowed_returncodes: frozenset[int] = frozenset({0}),
    pass_fds: tuple[int, ...] = (),
) -> subprocess.CompletedProcess[str]:
    """Run byte-bounded Git and decode output strictly without payload diagnostics."""

    raw = _run_git_bytes(
        repo,
        *args,
        allowed_returncodes=allowed_returncodes,
        pass_fds=pass_fds,
    )
    try:
        stdout = raw.stdout.decode("utf-8", errors="strict")
        stderr = raw.stderr.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise GitValidationError(
            f"Git command returned invalid text safely for {repo}: "
            f"{args[0] if args else 'git'}"
        ) from exc
    return subprocess.CompletedProcess(raw.args, raw.returncode, stdout, stderr)


def own_checkout_root(repo: Path) -> Path | None:
    key = _repository_key(repo)
    state = _validation_state()
    if state is not None and key in state.checkout_roots:
        return state.checkout_roots[key]
    if not repo.is_dir() or not (repo / ".git").exists():
        if state is not None:
            state.checkout_roots[key] = None
        return None
    result = _run_git(repo, "rev-parse", "--show-toplevel")
    top_level = result.stdout.strip()
    if not top_level:
        raise GitValidationError(f"Git command returned no checkout root for {repo}")
    resolved = Path(top_level).resolve()
    checkout = resolved if resolved == repo.resolve() else None
    if state is not None:
        state.checkout_roots[key] = checkout
    return checkout


def validate_selected_roots() -> None:
    if own_checkout_root(SOURCE_ROOT) is None:
        raise GitValidationError(
            f"{SOURCE_ROOT}: selected source root must be its own Git checkout"
        )
    source_resolved = SOURCE_ROOT.resolve()
    platform_resolved = SOURCE_PLATFORM_ROOT.resolve()
    if (
        SOURCE_PLATFORM_ROOT.is_symlink()
        or not SOURCE_PLATFORM_ROOT.is_dir()
        or not is_within(platform_resolved, source_resolved)
    ):
        raise ValueError(
            "selected 33god-platform root must be a real directory inside GOD_SOURCE_ROOT"
        )
    if is_within(EXTERNAL_ROOT.resolve(), source_resolved):
        raise ValueError("GOD_EXTERNAL_ROOT must be outside GOD_SOURCE_ROOT")
    snapshot = committed_platform_snapshot()
    if snapshot is None:
        contained_platform_input("components.yaml", kind="file")
        contained_platform_input("changes", kind="directory")
        contained_platform_input("backfills", kind="directory")
    else:
        if "components.yaml" not in snapshot:
            raise ValueError("committed 33god-platform/components.yaml is missing")
        for directory in ("changes", "backfills"):
            prefix = directory + "/"
            if not any(path.startswith(prefix) for path in snapshot):
                raise ValueError(
                    f"committed 33god-platform/{directory} directory is missing"
                )


def verify_commit_object_graph(repo: Path, revision: str) -> None:
    """Require one exact commit and all of its reachable objects to be local."""

    try:
        verify_local_git_object_closure(
            repo,
            revision,
            lambda args, payload, limit, allowed: _run_git_bytes(
                repo,
                *args,
                input_bytes=payload,
                stdout_limit=limit,
                stderr_limit=limit,
                allowed_returncodes=allowed,
            ),
            max_objects=MAX_GIT_TREE_ENTRIES,
            max_output_bytes=MAX_GIT_OUTPUT_BYTES,
        )
    except (GitValidationError, OSError, UnicodeError, ValueError) as exc:
        raise GitValidationError(
            f"Git commit closure contains a missing or invalid object, or uses "
            f"non-local provenance, for {repo}"
        ) from exc


def root_commit_revision(root: Path) -> str:
    key = _repository_key(root)
    state = _validation_state()
    if state is not None and key in state.revisions:
        return state.revisions[key]
    revision = _run_git(root, "rev-parse", "HEAD").stdout.strip()
    if not FULL_GIT_REVISION.fullmatch(revision):
        raise GitValidationError("root Git checkout returned an invalid HEAD revision")
    verify_commit_object_graph(root, revision)
    if state is not None:
        state.revisions[key] = revision
    return revision


def root_tree_entries(
    root: Path, revision: str | None = None
) -> dict[str, tuple[str, str, str]]:
    """Read the exact root commit tree, independent of index/worktree state."""

    if own_checkout_root(root) is None:
        raise GitValidationError(
            f"{root}: selected source root must be its own Git checkout"
        )
    exact_revision = root_commit_revision(root) if revision is None else revision
    key = (_repository_key(root), exact_revision)
    state = _validation_state()
    if state is not None and key in state.root_trees:
        return state.root_trees[key]
    verify_commit_object_graph(root, exact_revision)
    result = _run_git(root, "ls-tree", "-z", "--full-tree", exact_revision)
    entries: dict[str, tuple[str, str, str]] = {}
    records = result.stdout.split("\0")
    if records[-1:] != [""]:
        raise GitValidationError("root Git commit tree returned malformed data")
    for record in records[:-1]:
        state = _validation_state()
        if state is not None:
            state.budget.consume("entries")
        if "\t" not in record:
            raise GitValidationError("root Git commit tree contains a malformed record")
        metadata, path = record.split("\t", 1)
        fields = metadata.split(" ")
        if len(fields) != 3 or any(not field for field in fields):
            raise GitValidationError("root Git commit tree contains a malformed record")
        mode, object_type, object_id = fields
        if (
            not path
            or "/" in path
            or any(ord(character) < 32 or ord(character) == 127 for character in path)
            or path in entries
            or mode not in {"040000", "100644", "100755", "120000", "160000"}
            or not FULL_GIT_REVISION.fullmatch(object_id)
        ):
            raise GitValidationError("root Git commit tree contains invalid metadata")
        expected_type = {
            "040000": "tree",
            "100644": "blob",
            "100755": "blob",
            "120000": "blob",
            "160000": "commit",
        }[mode]
        if object_type != expected_type:
            raise GitValidationError(
                "root Git commit tree contains invalid object type"
            )
        entries[path] = (mode, object_type, object_id)
    if state is not None:
        state.root_trees[key] = entries
    return entries


def committed_file_entries(
    root: Path, revision: str, prefix: str
) -> dict[str, tuple[str, str, int]]:
    """Enumerate verified regular blobs below one exact committed prefix."""

    verify_commit_object_graph(root, revision)
    raw = _run_git_bytes(
        root,
        "ls-tree",
        "-r",
        "-z",
        "--full-tree",
        revision,
        "--",
        prefix,
    ).stdout
    records = raw.split(b"\0")
    if records[-1:] != [b""]:
        raise GitValidationError("root Git commit tree returned malformed data")
    entries: dict[str, tuple[str, str, int]] = {}
    object_ids: list[str] = []
    for record in records[:-1]:
        if len(entries) >= MAX_GIT_TREE_ENTRIES or b"\t" not in record:
            raise GitValidationError("root Git commit tree exceeds or violates bounds")
        state = _validation_state()
        if state is not None:
            state.budget.consume("entries")
        metadata, raw_path = record.split(b"\t", 1)
        fields = metadata.split(b" ")
        try:
            mode, object_type, object_id = (
                field.decode("ascii", errors="strict") for field in fields
            )
            path = raw_path.decode("utf-8", errors="strict")
        except (UnicodeError, ValueError) as exc:
            raise GitValidationError("root Git commit tree contains malformed data") from exc
        relative_path = PurePosixPath(path)
        if (
            len(fields) != 3
            or not path
            or relative_path.is_absolute()
            or any(part in {"", ".", ".."} for part in relative_path.parts)
            or any(ord(character) < 32 or ord(character) == 127 for character in path)
            or mode not in {"100644", "100755"}
            or object_type != "blob"
            or not FULL_GIT_REVISION.fullmatch(object_id)
            or path in entries
        ):
            raise GitValidationError("root Git commit tree contains invalid file metadata")
        entries[path] = (mode, object_id, -1)
        object_ids.append(object_id)
    if not object_ids:
        return entries
    payload = b"".join(f"{object_id}\n".encode("ascii") for object_id in object_ids)
    checked = _run_git_bytes(
        root,
        "cat-file",
        "--batch-check=%(objectname) %(objecttype) %(objectsize)",
        input_bytes=payload,
    ).stdout
    lines = checked.splitlines()
    if len(lines) != len(object_ids):
        raise GitValidationError("root Git blob verification returned malformed data")
    for path, expected, line in zip(entries, object_ids, lines, strict=True):
        try:
            fields = line.decode("ascii", errors="strict").split(" ")
        except UnicodeError as exc:
            raise GitValidationError(
                "root Git blob verification returned malformed data"
            ) from exc
        if (
            len(fields) != 3
            or fields[0] != expected
            or fields[1] != "blob"
            or not fields[2].isdigit()
        ):
            raise GitValidationError(
                "root Git commit tree references a missing or invalid blob"
            )
        mode, object_id, _size = entries[path]
        entries[path] = (mode, object_id, int(fields[2]))
    return entries


def committed_platform_snapshot() -> dict[str, tuple[str, str, int]] | None:
    """Return the exact platform subtree, or an explicit non-Git fallback marker."""

    state = _validation_state()
    state_key = (_repository_key(SOURCE_ROOT), _repository_key(SOURCE_PLATFORM_ROOT))
    if state is not None and state_key in state.platform_snapshots:
        return state.platform_snapshots[state_key]
    if lexical_path(SOURCE_PLATFORM_ROOT) != lexical_path(
        SOURCE_ROOT / "33god-platform"
    ):
        if state is not None:
            state.platform_snapshots[state_key] = None
        return None
    if own_checkout_root(SOURCE_ROOT) is None:
        if state is not None:
            state.platform_snapshots[state_key] = None
        return None
    revision = root_commit_revision(SOURCE_ROOT)
    prefix = "33god-platform/"
    snapshot = {
        path.removeprefix(prefix): entry
        for path, entry in committed_file_entries(
            SOURCE_ROOT, revision, prefix.rstrip("/")
        ).items()
        if path.startswith(prefix)
    }
    if state is not None:
        state.platform_snapshots[state_key] = snapshot
    return snapshot


def platform_input_bytes(
    relative: str | Path,
    *,
    snapshot: dict[str, tuple[str, str, int]] | None = None,
    max_bytes: int = MAX_SCAN_FILE_BYTES,
) -> bytes:
    relative_text = PurePosixPath(str(relative)).as_posix()
    selected = committed_platform_snapshot() if snapshot is None else snapshot
    if selected is None:
        path = contained_platform_input(relative_text, kind="file")
        try:
            with path.open("rb") as handle:
                payload = handle.read(max_bytes + 1)
        except OSError as exc:
            raise ValueError(f"33god-platform input cannot be read: {relative_text}") from exc
        if len(payload) > max_bytes:
            raise ValueError(f"33god-platform input exceeds its bound: {relative_text}")
        state = _validation_state()
        if state is not None:
            state.budget.consume("retained_bytes", len(payload))
        return payload
    entry = selected.get(relative_text)
    if entry is None:
        raise ValueError(f"committed 33god-platform input is missing: {relative_text}")
    _mode, object_id, object_size = entry
    if object_size > max_bytes:
        raise ValueError(f"committed 33god-platform input exceeds its bound: {relative_text}")
    payload = _run_git_bytes(
        SOURCE_ROOT,
        "cat-file",
        "blob",
        object_id,
        stdout_limit=max_bytes,
    ).stdout
    if len(payload) != object_size:
        raise ValueError(
            f"committed 33god-platform input changed while reading: {relative_text}"
        )
    state = _validation_state()
    if state is not None:
        state.budget.consume("retained_bytes", len(payload))
    return payload


def platform_input_text(
    relative: str | Path,
    *,
    snapshot: dict[str, tuple[str, str, int]] | None = None,
    max_bytes: int = MAX_SCAN_FILE_BYTES,
) -> str:
    try:
        return platform_input_bytes(
            relative, snapshot=snapshot, max_bytes=max_bytes
        ).decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ValueError(f"33god-platform input is not valid UTF-8: {relative}") from exc


def selected_platform_relative(path: Path) -> str | None:
    try:
        return lexical_path(path).relative_to(
            lexical_path(SOURCE_PLATFORM_ROOT)
        ).as_posix()
    except ValueError:
        return None


def selected_input_text(path: Path, *, max_bytes: int = MAX_SCAN_FILE_BYTES) -> str:
    relative = selected_platform_relative(path)
    snapshot = committed_platform_snapshot() if relative is not None else None
    if relative is not None and snapshot is not None:
        return platform_input_text(
            relative, snapshot=snapshot, max_bytes=max_bytes
        )
    try:
        with path.open("rb") as handle:
            payload = handle.read(max_bytes + 1)
    except OSError as exc:
        raise ValueError(f"{path}: cannot be read safely") from exc
    if len(payload) > max_bytes:
        raise ValueError(f"{path}: exceeds its safe input bound")
    try:
        return payload.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ValueError(f"{path}: is not valid UTF-8") from exc


def load_selected_yaml(path: Path) -> dict[str, Any]:
    return load_yaml_text(selected_input_text(path), str(path))


def gitlink_entries(root: Path | None = None) -> dict[str, str]:
    """Return root gitlinks from the exact selected HEAD commit tree."""

    root = SOURCE_ROOT if root is None else root
    return {
        path: object_id
        for path, (mode, _kind, object_id) in root_tree_entries(root).items()
        if mode == "160000"
    }


def gitmodule_mappings(root: Path | None = None) -> dict[str, dict[str, str]]:
    """Return mappings from the exact committed, regular ``.gitmodules`` blob."""

    root = SOURCE_ROOT if root is None else root
    if own_checkout_root(root) is None:
        raise GitValidationError(
            f"{root}: selected source root must be its own Git checkout"
        )
    tree_entries = root_tree_entries(root)
    tree_entry = tree_entries.get(".gitmodules")
    if tree_entry is None:
        return {}
    mode, object_type, object_id = tree_entry
    if mode != "100644" or object_type != "blob":
        raise GitValidationError(".gitmodules must be a regular committed file")
    try:
        size_text = _run_git(root, "cat-file", "-s", object_id).stdout.strip()
        if not size_text.isdigit() or int(size_text) > MAX_SCAN_FILE_BYTES:
            raise GitValidationError(".gitmodules exceeds its safe size bound")
        content = _run_git(root, "cat-file", "blob", object_id).stdout
    except (OSError, UnicodeError, ValueError) as exc:
        raise GitValidationError(".gitmodules cannot be read safely") from exc
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(content, source="<committed .gitmodules>")
    except (configparser.Error, UnicodeError) as exc:
        raise GitValidationError(".gitmodules is malformed") from exc
    mappings: dict[str, dict[str, str]] = {}
    for section in parser.sections():
        if not section.startswith('submodule "'):
            continue
        mapped_path = parser.get(section, "path", fallback="").strip()
        if not mapped_path:
            continue
        mapped = Path(mapped_path)
        lexical_checkout = lexical_path(root / mapped)
        if mapped.is_absolute() or not is_within(lexical_checkout, root):
            raise GitValidationError(
                ".gitmodules contains a submodule path that escapes the selected root"
            )
        name = section.removeprefix('submodule "').removesuffix('"')
        if mapped_path in mappings:
            raise GitValidationError(
                ".gitmodules contains an ambiguous duplicate submodule path"
            )
        mappings[mapped_path] = {
            "name": name,
            "url": parser.get(section, "url", fallback="").strip(),
        }
    return mappings


def normalize_repository_url(value: str) -> str:
    message = "repository URL must be credential-free hostful HTTPS"
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(message)
    if any(ord(character) < 32 for character in value):
        raise ValueError(message)
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError(message) from exc
    if (
        parsed.scheme.casefold() != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not parsed.path
        or parsed.path == "/"
    ):
        raise ValueError(message)
    repository_path = parsed.path.rstrip("/")
    if repository_path.casefold().endswith(".git"):
        repository_path = repository_path[:-4]
    if not repository_path or repository_path == "/":
        raise ValueError(message)
    host = hostname.casefold()
    if port is not None:
        host = f"{host}:{port}"
    return f"https://{host}{repository_path}".casefold()


def normalize_checkout_origin(value: str) -> str:
    """Normalize a local checkout origin to its credential-free HTTPS identity.

    Canonical declarations must already be HTTPS. A repository-local origin may
    use GitHub's credential-free ``git@`` transport without changing the
    checkout; no other userinfo or transport is accepted.
    """

    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError(
            "checkout origin must identify a credential-free hostful HTTPS repository"
        )
    try:
        return normalize_repository_url(value)
    except ValueError:
        pass
    scp_match = re.fullmatch(r"git@([A-Za-z0-9.-]+):([^?#]+)", value)
    if scp_match:
        return normalize_repository_url(
            f"https://{scp_match.group(1)}/{scp_match.group(2)}"
        )
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError(
            "checkout origin must identify a credential-free hostful HTTPS repository"
        ) from exc
    if (
        parsed.scheme.casefold() == "ssh"
        and parsed.username == "git"
        and parsed.password is None
        and parsed.hostname
        and port is None
        and parsed.path not in {"", "/"}
        and not parsed.query
        and not parsed.fragment
    ):
        return normalize_repository_url(f"https://{parsed.hostname}{parsed.path}")
    raise ValueError(
        "checkout origin must identify a credential-free hostful HTTPS repository"
    )


def root_relative_repo(repo: Path) -> str | None:
    try:
        relative = repo.resolve().relative_to(SOURCE_ROOT)
    except ValueError:
        return None
    if relative == Path("."):
        return None
    return relative.as_posix()


def is_real_directory_chain(root: Path, checkout: Path) -> bool:
    """Reject symlink or non-directory indirection below one lexical root."""

    root_lexical = lexical_path(root)
    checkout_lexical = lexical_path(checkout)
    try:
        relative = checkout_lexical.relative_to(root_lexical)
    except ValueError:
        return False
    cursor = root_lexical
    for part in relative.parts:
        cursor /= part
        try:
            metadata = cursor.lstat()
        except OSError:
            return False
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            return False
    return bool(relative.parts)


def git_checkout_revision(repo: Path) -> str | None:
    """HEAD revision of an initialized Git checkout, else None.

    An empty or plain directory is not an initialized checkout even when a
    parent repository would answer `rev-parse` for it.
    """
    if own_checkout_root(repo) is None:
        return None
    revision = _run_git(repo, "rev-parse", "HEAD").stdout.strip()
    if not FULL_GIT_REVISION.fullmatch(revision):
        raise GitValidationError(f"Git returned an invalid HEAD revision for {repo}")
    verify_commit_object_graph(repo, revision)
    return revision


def git_checkout_origin(repo: Path) -> str | None:
    raw = _run_git_bytes(
        repo,
        "config",
        "--local",
        "--get",
        "remote.origin.url",
        allowed_returncodes=frozenset({0, 1}),
    )
    try:
        stdout = raw.stdout.decode("utf-8", errors="strict")
        raw.stderr.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise GitValidationError(
            f"Git command returned invalid text safely for {repo}: config"
        ) from exc
    if raw.returncode == 1 and not stdout.strip():
        return None
    if raw.returncode:
        raise GitValidationError(f"Git command failed safely for {repo}: config")
    return stdout.strip() or None


def bound_git_checkout_identity(
    bound: BoundDirectory,
) -> tuple[str | None, str | None]:
    """Read revision and origin from the same held checkout directory inode."""

    repo = bound.process_path
    inherited = (bound.fd,)
    prefix = _run_git(repo, "rev-parse", "--show-prefix", pass_fds=inherited)
    if prefix.stdout.strip():
        return None, None
    inside = _run_git(
        repo, "rev-parse", "--is-inside-work-tree", pass_fds=inherited
    ).stdout.strip()
    if inside != "true":
        return None, None
    revision = _run_git(
        repo, "rev-parse", "HEAD", pass_fds=inherited
    ).stdout.strip()
    if not FULL_GIT_REVISION.fullmatch(revision):
        raise GitValidationError("bound checkout returned an invalid HEAD revision")
    try:
        verify_local_git_object_closure(
            repo,
            revision,
            lambda args, payload, limit, allowed: _run_git_bytes(
                repo,
                *args,
                input_bytes=payload,
                stdout_limit=limit,
                stderr_limit=limit,
                allowed_returncodes=allowed,
                pass_fds=inherited,
            ),
            max_objects=MAX_GIT_TREE_ENTRIES,
            max_output_bytes=MAX_GIT_OUTPUT_BYTES,
        )
    except (GitValidationError, OSError, UnicodeError, ValueError) as exc:
        raise GitValidationError("bound checkout has an invalid commit closure") from exc
    raw_origin = _run_git_bytes(
        repo,
        "config",
        "--local",
        "--get",
        "remote.origin.url",
        allowed_returncodes=frozenset({0, 1}),
        pass_fds=inherited,
    )
    try:
        origin = raw_origin.stdout.decode("utf-8", errors="strict").strip()
        raw_origin.stderr.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise GitValidationError("bound checkout origin is not valid UTF-8") from exc
    if raw_origin.returncode == 1 and not origin:
        return revision, None
    if raw_origin.returncode != 0:
        raise GitValidationError("bound checkout origin cannot be read safely")
    return revision, origin or None


def validate_component_contracts(
    components: list[dict[str, Any]],
) -> list[str]:
    """Bind every canonical manifest position to one exact product identity."""

    errors: list[str] = []
    if len(components) != len(PRODUCT_COMPONENT_IDS):
        errors.append(
            "components.yaml: loaded manifest count must match the exact product registry"
        )
    for index, component_id in enumerate(PRODUCT_COMPONENT_IDS):
        if index >= len(components):
            errors.append(
                f"components/{component_id}.yaml: canonical manifest is missing"
            )
            continue
        component = components[index]
        contract = COMPONENT_CONTRACTS[component_id]
        expected_path = (SOURCE_PLATFORM_ROOT / COMPONENT_FILE_PATHS[index]).resolve()
        actual_path = component.get("_path")
        if not isinstance(actual_path, Path) or actual_path.resolve() != expected_path:
            errors.append(
                f"components/{component_id}.yaml: manifest is not loaded from its exact canonical path"
            )
        for field in ("id", "role", "repo", "repository_kind"):
            expected = component_id if field == "id" else contract[field]
            if component.get(field) != expected:
                errors.append(
                    f"components/{component_id}.yaml: {field} must be {expected!r}"
                )
        expected_revision_field = contract["revision_field"]
        expected_revision = contract["revision"]
        for field in ("source_revision", "gitlink_revision"):
            if field == expected_revision_field:
                if component.get(field) != expected_revision:
                    errors.append(
                        f"components/{component_id}.yaml: {field} must pin {expected_revision}"
                    )
            elif field in component:
                errors.append(
                    f"components/{component_id}.yaml: unexpected revision field {field}"
                )
        expected_origin = contract["repository_origin"]
        if expected_origin is None:
            if "repository_origin" in component:
                errors.append(
                    f"components/{component_id}.yaml: repository_origin is not permitted"
                )
        elif component.get("repository_origin") != expected_origin:
            errors.append(
                f"components/{component_id}.yaml: repository_origin must match the canonical public origin"
            )
        elif normalize_repository_url(str(expected_origin)) != normalize_repository_url(
            str(component["repository_origin"])
        ):
            errors.append(
                f"components/{component_id}.yaml: repository_origin is not canonical"
            )
    if tuple(str(item.get("id")) for item in components) != PRODUCT_COMPONENT_IDS:
        errors.append("component manifests must preserve the exact ordered product IDs")
    return errors


def component_repo_status(component: dict[str, Any]) -> tuple[str, str | None]:
    """Classify a component's selected repo path.

    Statuses: ``verified`` (initialized Git checkout at the exact recorded
    revision), ``revision-mismatch``, ``uninitialized`` (recorded revision but
    no Git checkout), ``not-a-git-checkout`` (non-empty directory without Git
    identity), ``present`` (exists, no recorded revision), ``missing``.
    """
    repo = resolve_path(component["repo"])
    repository_kind = component.get("repository_kind")
    recorded = recorded_revision(component)
    if repository_kind == "local-runtime":
        if not repo.exists():
            return ("missing", None)
        return ("present", None) if repo.is_dir() else ("not-a-runtime-root", None)
    if repository_kind == "in-tree-source":
        if not is_within(repo.resolve(), SOURCE_ROOT.resolve()):
            return ("path-policy-mismatch", None)
        if not repo.exists():
            return ("missing", None)
        return ("present", None) if repo.is_dir() else ("not-a-source-root", None)
    if repository_kind not in {"root-gitlink", "external-git"}:
        return ("invalid-repository-kind", None)
    if recorded is None:
        return ("revision-missing", None)

    relative_repo = root_relative_repo(repo)
    if repository_kind == "root-gitlink":
        if relative_repo is None:
            return ("path-policy-mismatch", None)
        gitlinks = gitlink_entries()
        mappings = gitmodule_mappings()
        gitlink_revision = gitlinks.get(relative_repo)
        if gitlink_revision is None:
            return ("gitlink-missing", None)
        if gitlink_revision != recorded:
            return ("gitlink-mismatch", gitlink_revision)
        mapping = mappings.get(relative_repo)
        if mapping is None:
            return ("unmapped", gitlink_revision)
        canonical_contract = ROOT_GITLINK_CONTRACTS.get(relative_repo)
        if canonical_contract is not None:
            canonical_origin, canonical_revision = canonical_contract
            if recorded != canonical_revision:
                return ("gitlink-contract-mismatch", gitlink_revision)
            if mapping["url"] != canonical_origin:
                return ("identity-mismatch", gitlink_revision)
    elif relative_repo is not None:
        return ("path-policy-mismatch", None)

    if not repo.exists():
        return ("uninitialized", None)
    revision = git_checkout_revision(repo)
    if revision is None:
        if not repo.is_dir() or any(repo.iterdir()):
            return ("not-a-git-checkout", None)
        return ("uninitialized", None)
    if revision != recorded:
        return ("revision-mismatch", revision)

    if repository_kind == "root-gitlink":
        mapping_url = gitmodule_mappings()[relative_repo]["url"]
        canonical_contract = ROOT_GITLINK_CONTRACTS.get(relative_repo)
        expected_url = (
            canonical_contract[0] if canonical_contract is not None else mapping_url
        )
        if canonical_contract is not None and mapping_url != expected_url:
            return ("identity-mismatch", revision)
        actual_url = git_checkout_origin(repo)
        if not actual_url:
            return ("identity-mismatch", revision)
        try:
            if normalize_checkout_origin(actual_url) != normalize_repository_url(
                expected_url
            ):
                return ("identity-mismatch", revision)
        except ValueError:
            return ("identity-mismatch", revision)
    else:
        expected_url = component.get("repository_origin")
        if not isinstance(expected_url, str):
            return ("identity-mismatch", revision)
        actual_url = git_checkout_origin(repo)
        if not actual_url:
            return ("identity-mismatch", revision)
        try:
            if normalize_checkout_origin(actual_url) != normalize_repository_url(
                expected_url
            ):
                return ("identity-mismatch", revision)
        except ValueError:
            return ("identity-mismatch", revision)
    return ("verified", revision)


def repo_is_populated(component: dict[str, Any]) -> bool:
    status, _ = component_repo_status(component)
    return status in {"present", "verified"}


def validate_gitlink_inventory() -> list[str]:
    errors: list[str] = []
    try:
        gitlinks = gitlink_entries()
        mappings = gitmodule_mappings()
    except GitValidationError as exc:
        return [f".gitmodules: cannot parse root gitlink inventory safely: {exc}"]
    except (configparser.Error, OSError, ValueError):
        return [".gitmodules: cannot parse root gitlink inventory safely"]
    expected_paths = tuple(ROOT_GITLINK_CONTRACTS)
    actual_gitlink_paths = tuple(gitlinks)
    actual_mapping_paths = tuple(sorted(mappings))
    if actual_gitlink_paths != expected_paths:
        errors.append(
            "root gitlink inventory must be the exact ordered canonical nine paths; "
            f"found {actual_gitlink_paths}"
        )
    if actual_mapping_paths != expected_paths:
        errors.append(
            ".gitmodules must map the exact ordered canonical nine paths; "
            f"found {actual_mapping_paths}"
        )
    missing = sorted(set(gitlinks) - set(mappings))
    extra = sorted(set(mappings) - set(gitlinks))
    if missing:
        errors.append(
            ".gitmodules: missing mappings for gitlinks: " + ", ".join(missing)
        )
    if extra:
        errors.append(
            ".gitmodules: mappings without root gitlinks: " + ", ".join(extra)
        )
    for path, mapping in sorted(mappings.items()):
        url = mapping["url"]
        try:
            normalize_repository_url(url)
        except ValueError:
            errors.append(
                f".gitmodules: {path} repository URL must be credential-free hostful HTTPS"
            )
        canonical = ROOT_GITLINK_CONTRACTS.get(path)
        if canonical is None:
            errors.append(
                f".gitmodules: {path} has no canonical public origin contract"
            )
        elif url != canonical[0]:
            errors.append(
                f".gitmodules: {path} URL must equal its canonical public HTTPS origin"
            )
    for path, expected_revision in sorted(gitlinks.items()):
        mapping = mappings.get(path)
        if mapping is None:
            continue
        canonical = ROOT_GITLINK_CONTRACTS.get(path)
        if canonical is None:
            errors.append(f"root gitlink {path}: no canonical revision contract")
            continue
        canonical_origin, canonical_revision = canonical
        if expected_revision != canonical_revision:
            errors.append(
                f"root gitlink {path}: commit revision does not match canonical contract"
            )
        checkout = lexical_path(SOURCE_ROOT / path)
        if not is_within(checkout, SOURCE_ROOT):
            errors.append(
                f"root gitlink {path}: checkout path escapes GOD_SOURCE_ROOT: {checkout}"
            )
            continue
        if not checkout.exists() and not checkout.is_symlink():
            errors.append(
                f"root gitlink {path}: checkout is not initialized as its own "
                f"Git repository at commit revision {expected_revision}"
            )
            continue
        if (checkout.exists() or checkout.is_symlink()) and not is_real_directory_chain(
            SOURCE_ROOT, checkout
        ):
            errors.append(
                f"root gitlink {path}: checkout path and ancestors must be real "
                "non-symlink directories"
            )
            continue
        try:
            with open_bound_directory(SOURCE_ROOT, PurePosixPath(path)) as bound:
                actual_revision, actual_origin = bound_git_checkout_identity(bound)
                stable_binding = bound.canonical_path_matches()
        except (GitValidationError, OSError, ValueError):
            errors.append(
                f"root gitlink {path}: checkout identity cannot be read safely "
                "from one bound directory inode"
            )
            continue
        if not stable_binding:
            errors.append(
                f"root gitlink {path}: checkout path changed during identity validation"
            )
            continue
        if actual_revision is None:
            errors.append(
                f"root gitlink {path}: checkout is not initialized as its own "
                f"Git repository at commit revision {expected_revision}"
            )
            continue
        if actual_revision != expected_revision:
            errors.append(
                f"root gitlink {path}: checkout HEAD {actual_revision} does not "
                f"match commit revision {expected_revision}"
            )

        if not actual_origin:
            errors.append(
                f"root gitlink {path}: initialized checkout has no origin; "
                "expected the repository-local canonical origin"
            )
        else:
            try:
                matches = normalize_checkout_origin(
                    actual_origin
                ) == normalize_repository_url(canonical_origin)
            except ValueError:
                matches = False
            if not matches:
                errors.append(
                    f"root gitlink {path}: checkout origin does not match canonical "
                    "public identity or is not credential-free"
                )
    return errors


def validate_acceptance_slice(components: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    cfg = platform_config()
    declaration = cfg.get("acceptance_slice")
    if not isinstance(declaration, dict) or not isinstance(
        declaration.get("components"), list
    ):
        return ["components.yaml: acceptance_slice.components must be a list"]
    slice_ids = [str(item) for item in declaration["components"]]
    if not slice_ids:
        errors.append("components.yaml: acceptance_slice.components is empty")
    if len(set(slice_ids)) != len(slice_ids):
        errors.append("components.yaml: acceptance_slice.components has duplicates")
    if tuple(slice_ids) != LIFECYCLE_ACCEPTANCE_SLICE:
        errors.append(
            "components.yaml: acceptance_slice.components must be the exact ordered "
            f"Lifecycle slice {LIFECYCLE_ACCEPTANCE_SLICE}; found {tuple(slice_ids)}"
        )
    component_files = platform_config().get("component_files")
    configured_paths = (
        tuple(component_files) if isinstance(component_files, list) else ()
    )
    if configured_paths != COMPONENT_FILE_PATHS:
        errors.append(
            "components.yaml: component_files must be the exact ordered manifest "
            f"paths {COMPONENT_FILE_PATHS}; found {configured_paths}"
        )
    registry_ids = tuple(str(component.get("id")) for component in components)
    if registry_ids != PRODUCT_COMPONENT_IDS:
        errors.append(
            "component manifests must load as the exact ordered product registry; "
            f"found {registry_ids}"
        )
    for component in components:
        try:
            revision = recorded_revision(component)
        except ValueError as exc:
            errors.append(f"{component.get('_path', '<unknown>')}: {exc}")
            continue
        if str(component.get("id")) in slice_ids and revision is None:
            errors.append(
                f"{component['_path']}: acceptance-slice component must record an "
                "exact source_revision or gitlink_revision"
            )
    return errors


def validate_components() -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    required = {"id", "name", "role", "repo", "description", "changelog"}
    try:
        components = load_components()
    except (configparser.Error, OSError, TypeError, ValueError) as exc:
        return [f"component registry cannot be loaded safely: {exc}"]
    try:
        errors.extend(validate_gitlink_inventory())
    except (configparser.Error, OSError, TypeError, ValueError) as exc:
        errors.append(f"root gitlink inventory cannot be loaded safely: {exc}")
    try:
        errors.extend(validate_acceptance_slice(components))
    except (OSError, TypeError, ValueError) as exc:
        errors.append(
            f"components.yaml: acceptance slice cannot be loaded safely: {exc}"
        )
    try:
        errors.extend(validate_component_contracts(components))
    except (OSError, TypeError, ValueError) as exc:
        errors.append(
            f"components.yaml: component contracts cannot be loaded safely: {exc}"
        )
    slice_ids = set(acceptance_slice_ids())
    for component in components:
        path = component["_path"]
        missing = sorted(required - set(component))
        if missing:
            errors.append(f"{path}: missing required keys: {', '.join(missing)}")
            continue

        component_id = str(component["id"])
        if component_id in seen:
            errors.append(f"{path}: duplicate component id {component_id!r}")
        seen.add(component_id)

        try:
            repo = resolve_path(component["repo"])
            status, revision = component_repo_status(component)
        except (configparser.Error, OSError, TypeError, ValueError) as exc:
            errors.append(f"{path}: repo path cannot be resolved safely: {exc}")
            continue
        repository_kind = component.get("repository_kind")
        if component_id in slice_ids:
            if status != "verified":
                detail = status
                if revision:
                    detail = f"{status} at {revision}"
                errors.append(
                    f"{path}: acceptance-slice repo is not a verified initialized "
                    f"Git checkout at its recorded revision: {repo} ({detail})"
                )
        elif status in {
            "revision-mismatch",
            "gitlink-mismatch",
            "gitlink-contract-mismatch",
            "gitlink-missing",
            "unmapped",
            "identity-mismatch",
            "not-a-git-checkout",
            "not-a-runtime-root",
            "not-a-source-root",
            "path-policy-mismatch",
            "invalid-repository-kind",
            "revision-missing",
        }:
            errors.append(
                f"{path}: repo verification failed for {repo}: {status}"
                + (f" at {revision}" if revision else "")
                + f"; recorded {recorded_revision(component)}"
            )
        elif repository_kind == "in-tree-source" and status != "present":
            errors.append(
                f"{path}: in-tree source root is unavailable at {repo}: {status}"
            )

        changelog = component.get("changelog")
        if not isinstance(changelog, dict):
            errors.append(f"{path}: changelog must be a mapping")
            topics = None
        else:
            topics = changelog.get("topics")
        if not isinstance(topics, list) or not topics:
            errors.append(f"{path}: changelog.topics must be a non-empty list")

        compose = component.get("compose")
        if not isinstance(compose, dict):
            errors.append(f"{path}: compose must be a mapping")
            compose = {}
        compose_files = compose.get("files", [])
        compose_profiles = compose.get("profiles", [])
        if not isinstance(compose_files, list):
            errors.append(f"{path}: compose.files must be a list")
            compose_files = []
        elif not all(isinstance(item, str) for item in compose_files):
            errors.append(f"{path}: compose.files must contain only paths")
            compose_files = []
        if not isinstance(compose_profiles, list):
            errors.append(f"{path}: compose.profiles must be a list")
        elif not all(isinstance(item, str) for item in compose_profiles):
            errors.append(f"{path}: compose.profiles must contain only strings")

        if repo_is_populated(component):
            for compose_file in compose_files:
                try:
                    resolved = resolve_path(compose_file)
                except (OSError, ValueError) as exc:
                    errors.append(
                        f"{path}: compose path cannot be resolved safely: {exc}"
                    )
                    continue
                if not is_within(resolved, repo):
                    errors.append(
                        f"{path}: compose file escapes selected component root "
                        f"{repo}: {resolved}"
                    )
                    continue
                if not resolved.exists():
                    errors.append(f"{path}: compose file does not exist: {resolved}")

    return errors


def validate_changes() -> list[str]:
    errors: list[str] = []
    required = {
        "id",
        "date",
        "component",
        "kind",
        "summary",
        "affects",
        "required_backfills",
        "docs",
    }
    ids: set[str] = set()
    try:
        paths = contained_platform_files("changes", "*.jsonl")
    except (OSError, ValueError) as exc:
        return [f"changes: cannot enumerate selected inputs safely: {exc}"]
    for path in paths:
        try:
            text = selected_input_text(path)
        except (OSError, ValueError) as exc:
            errors.append(f"{path}: cannot read change log safely: {exc}")
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}:{line_no}: invalid JSON: {exc}")
                continue
            if not isinstance(item, dict):
                errors.append(
                    f"{path}:{line_no}: expected a JSON object, found "
                    f"{type(item).__name__}"
                )
                continue
            missing = sorted(required - set(item))
            if missing:
                errors.append(
                    f"{path}:{line_no}: missing required keys: {', '.join(missing)}"
                )
            for key in ("id", "date", "component", "kind", "summary"):
                value = item.get(key)
                if not isinstance(value, str) or not value.strip():
                    errors.append(
                        f"{path}:{line_no}: {key} must be a non-empty string"
                    )
            change_id = item.get("id")
            if not isinstance(change_id, str) or not change_id.strip():
                pass
            elif change_id in ids:
                errors.append(f"{path}:{line_no}: duplicate change id {change_id!r}")
            else:
                ids.add(change_id)
            for key in ("affects", "required_backfills", "docs"):
                value = item.get(key)
                if not isinstance(value, list):
                    errors.append(f"{path}:{line_no}: {key} must be a list")
                elif not all(isinstance(entry, str) for entry in value):
                    errors.append(f"{path}:{line_no}: {key} must contain only strings")
    return errors


def validate_backfill_manifests() -> list[str]:
    errors: list[str] = []
    required = {
        "id",
        "title",
        "owner_component",
        "kind",
        "summary",
        "search_paths",
        "forbidden_patterns",
        "remediation",
    }
    ids: set[str] = set()
    try:
        paths = contained_platform_files("backfills", "*.yaml")
    except (OSError, ValueError) as exc:
        return [f"backfills: cannot enumerate selected inputs safely: {exc}"]
    for path in paths:
        try:
            item = load_selected_yaml(path)
        except (OSError, ValueError) as exc:
            errors.append(f"{path}: cannot load backfill safely: {exc}")
            continue
        missing = sorted(required - set(item))
        if missing:
            errors.append(f"{path}: missing required keys: {', '.join(missing)}")
        backfill_id = item.get("id")
        if not isinstance(backfill_id, str) or not backfill_id.strip():
            errors.append(f"{path}: id must be a non-empty string")
        elif backfill_id in ids:
            errors.append(f"{path}: duplicate backfill id {backfill_id!r}")
        else:
            ids.add(backfill_id)
        search_paths = item.get("search_paths")
        forbidden_patterns = item.get("forbidden_patterns")
        if not isinstance(search_paths, list):
            errors.append(f"{path}: search_paths must be a list")
        elif not all(isinstance(entry, str) for entry in search_paths):
            errors.append(f"{path}: search_paths must contain only strings")
        if not isinstance(forbidden_patterns, list):
            errors.append(f"{path}: forbidden_patterns must be a list")
        elif not all(isinstance(entry, str) for entry in forbidden_patterns):
            errors.append(f"{path}: forbidden_patterns must contain only strings")
    return errors


def cmd_validate(_: argparse.Namespace) -> int:
    errors: list[str] = []
    for label, validator in (
        ("component registry", validate_components),
        ("change logs", validate_changes),
        ("backfill manifests", validate_backfill_manifests),
    ):
        try:
            errors.extend(validator())
        except (configparser.Error, OSError, TypeError, ValueError) as exc:
            errors.append(f"{label} cannot be validated safely: {exc}")
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        return 1
    print("33GOD platform manifest OK")
    return 0


def cmd_components_list(_: argparse.Namespace) -> int:
    rows = []
    try:
        components = load_components()
        slice_ids = set(acceptance_slice_ids())
    except (configparser.Error, OSError, TypeError, ValueError) as exc:
        print(
            f"ERROR component registry cannot be loaded safely: {exc}", file=sys.stderr
        )
        return 1
    for component in components:
        component_id = component.get("id")
        role = component.get("role")
        component_id_text = (
            str(component_id) if component_id is not None else "<missing>"
        )
        role_text = str(role) if role is not None else "<missing>"
        repo_value = component.get("repo")
        if repo_value is None:
            repo: Path | str = "<missing>"
            status, revision = "invalid", None
        else:
            try:
                repo = resolve_path(repo_value)
                status, revision = component_repo_status(component)
            except (configparser.Error, OSError, TypeError, ValueError):
                repo = str(repo_value)
                status, revision = "invalid", None
        recorded = recorded_revision(component)
        compose = component.get("compose")
        if not isinstance(compose, dict):
            compose = {}
        compose_files = compose.get("files", [])
        compose_profiles = compose.get("profiles", [])
        if not isinstance(compose_files, list):
            compose_files = []
            status = "invalid"
        if not isinstance(compose_profiles, list):
            compose_profiles = []
            status = "invalid"
        rows.append(
            (
                component_id_text,
                role_text,
                "acceptance" if component_id_text in slice_ids else "registry",
                status,
                (revision or recorded or "-")[:12],
                ",".join(str(item) for item in compose_profiles),
                str(repo),
                str(len(compose_files)),
            )
        )
    headers = (
        "id",
        "role",
        "scope",
        "repo",
        "revision",
        "profiles",
        "path",
        "compose",
    )
    widths = [
        max(len(str(row[i])) for row in [headers, *rows]) for i in range(len(headers))
    ]
    print("  ".join(str(headers[i]).ljust(widths[i]) for i in range(len(headers))))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(str(row[i]).ljust(widths[i]) for i in range(len(row))))
    errors = validate_components()
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 1 if errors else 0


def _glob_static_prefix(path: Path) -> Path:
    parts: list[str] = []
    for part in path.parts:
        if glob.has_magic(part):
            break
        parts.append(part)
    return Path(*parts) if parts else Path(path.anchor or ".")


def _relative_backfill_pattern(item: str) -> tuple[str, Path]:
    candidate = lexical_path(SOURCE_PLATFORM_ROOT / item)
    source_resolved = SOURCE_ROOT.resolve()
    if is_within(candidate, SOURCE_ROOT):
        allowed_root = source_resolved
        mapped = candidate
    else:
        if is_within(EXTERNAL_ROOT.resolve(), source_resolved):
            raise ValueError("GOD_EXTERNAL_ROOT must be outside GOD_SOURCE_ROOT")
        try:
            relative = candidate.relative_to(SOURCE_ROOT.parent)
        except ValueError as exc:
            raise ValueError(
                f"relative backfill path escapes the supported sibling boundary: {item}"
            ) from exc
        mapped = lexical_path(EXTERNAL_ROOT / relative)
        allowed_root = EXTERNAL_ROOT.resolve()
        if not is_within(mapped, EXTERNAL_ROOT):
            raise ValueError(
                f"relative backfill path escapes GOD_EXTERNAL_ROOT: {item}"
            )
    prefix = _glob_static_prefix(mapped)
    resolved_prefix = prefix.resolve()
    if not is_within(resolved_prefix, allowed_root):
        raise ValueError(f"relative backfill path escapes its governed root: {item}")
    if is_within(resolved_prefix, source_resolved) and allowed_root != source_resolved:
        raise ValueError(f"relative backfill path re-enters GOD_SOURCE_ROOT: {item}")
    return str(mapped), allowed_root


def _validate_governed_backfill_path(
    path: Path, governed_root: Path, item: str, *, directory: bool
) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError(
            f"relative backfill path cannot be resolved safely: {item}"
        ) from exc
    governed_resolved = governed_root.resolve()
    source_resolved = SOURCE_ROOT.resolve()
    if not is_within(resolved, governed_resolved):
        raise ValueError(f"relative backfill path escapes its governed root: {item}")
    if governed_resolved != source_resolved:
        if is_within(resolved, source_resolved):
            raise ValueError(
                f"relative backfill path re-enters GOD_SOURCE_ROOT: {item}"
            )
        if directory and is_within(source_resolved, resolved):
            raise ValueError(
                f"relative backfill directory is an ancestor of GOD_SOURCE_ROOT: {item}"
            )
    return resolved


def _backfill_budget(budget: ValidationBudget | None = None) -> ValidationBudget:
    if budget is not None:
        return budget
    state = _validation_state()
    if state is not None:
        return state.budget
    return ValidationBudget(
        max_entries=MAX_BACKFILL_ENTRIES,
        max_files=MAX_BACKFILL_FILES,
        max_matches=MAX_BACKFILL_ENTRIES,
    )


def _validate_backfill_pattern(pattern: str) -> tuple[Path, tuple[str, ...]]:
    if len(pattern.encode("utf-8", errors="strict")) > MAX_BACKFILL_PATTERN_LENGTH:
        raise ValueError("backfill glob exceeds its pattern length bound")
    candidate = Path(pattern)
    parts = candidate.parts[1:] if candidate.anchor else candidate.parts
    if len(parts) > MAX_BACKFILL_PATTERN_COMPONENTS:
        raise ValueError("backfill glob exceeds its component bound")
    if sum(part == "**" for part in parts) > MAX_BACKFILL_RECURSIVE_DEPTH:
        raise ValueError("backfill glob exceeds its recursive wildcard bound")
    return (Path(candidate.anchor) if candidate.anchor else Path("."), tuple(parts))


def iter_backfill_glob(
    pattern: str, budget: ValidationBudget | None = None
) -> Any:
    """Expand a finite glob iteratively without following any symlink."""

    active_budget = _backfill_budget(budget)
    root, parts = _validate_backfill_pattern(pattern)
    stack: list[tuple[Path, int, int]] = [(root, 0, 0)]
    inspected_states: set[tuple[int, int, int]] = set()
    while stack:
        active_budget.check_time()
        base, index, depth = stack.pop()
        if index == len(parts):
            yield base
            continue
        part = parts[index]
        if part not in {"**"} and not glob.has_magic(part):
            child = base / part
            try:
                metadata = child.lstat()
            except (FileNotFoundError, NotADirectoryError):
                continue
            except OSError as exc:
                raise ValueError(
                    f"backfill glob path cannot be inspected safely: {child}"
                ) from exc
            if stat.S_ISLNK(metadata.st_mode):
                raise ValueError(f"backfill glob must not traverse a symlink: {child}")
            if child.name in BACKFILL_EXCLUDED_PARTS:
                continue
            stack.append((child, index + 1, depth))
            continue

        try:
            base_metadata = base.lstat()
        except (FileNotFoundError, NotADirectoryError):
            continue
        except OSError as exc:
            raise ValueError(
                f"backfill glob directory cannot be inspected safely: {base}"
            ) from exc
        if stat.S_ISLNK(base_metadata.st_mode):
            raise ValueError(f"backfill glob must not traverse a symlink: {base}")
        if not stat.S_ISDIR(base_metadata.st_mode):
            continue
        state_key = (index, base_metadata.st_dev, base_metadata.st_ino)
        if state_key in inspected_states:
            raise ValueError("backfill glob directory cycle detected")
        inspected_states.add(state_key)
        if part == "**":
            stack.append((base, index + 1, depth))
        try:
            iterator = os.scandir(base)
            with iterator:
                for entry in iterator:
                    active_budget.consume("entries")
                    if entry.name in BACKFILL_EXCLUDED_PARTS:
                        continue
                    child = Path(entry.path)
                    try:
                        metadata = entry.stat(follow_symlinks=False)
                    except OSError as exc:
                        raise ValueError(
                            f"backfill glob entry cannot be inspected safely: {child}"
                        ) from exc
                    if stat.S_ISLNK(metadata.st_mode):
                        continue
                    if part == "**":
                        if stat.S_ISDIR(metadata.st_mode):
                            if depth >= MAX_BACKFILL_RECURSIVE_DEPTH:
                                raise ValueError(
                                    "backfill glob exceeds its recursive depth bound"
                                )
                            stack.append((child, index, depth + 1))
                        elif index + 1 == len(parts):
                            stack.append((child, index + 1, depth))
                    elif (
                        not (entry.name.startswith(".") and not part.startswith("."))
                        and fnmatch.fnmatchcase(entry.name, part)
                    ):
                        stack.append((child, index + 1, depth))
        except OSError as exc:
            raise ValueError(
                f"backfill glob directory cannot be enumerated safely: {base}"
            ) from exc


def _absolute_no_symlink_entry(path: Path, item: str) -> tuple[Path, os.stat_result]:
    absolute = lexical_path(path)
    anchor = Path(absolute.anchor)
    cursor = anchor
    try:
        metadata = anchor.lstat()
    except OSError as exc:
        raise ValueError(
            f"backfill path cannot be resolved or inspected safely: {item}"
        ) from exc
    for part in absolute.parts[1:]:
        cursor /= part
        try:
            metadata = cursor.lstat()
        except OSError as exc:
            raise ValueError(
                f"backfill path cannot be resolved or inspected safely: {item}"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"backfill path must not traverse a symlink: {item}")
    return absolute, metadata


def _candidate_from_metadata(path: Path, metadata: os.stat_result) -> BackfillCandidate:
    absolute = lexical_path(path)
    return BackfillCandidate(
        path=absolute,
        anchor=Path(absolute.anchor),
        relative=PurePosixPath(*absolute.parts[1:]),
        device=metadata.st_dev,
        inode=metadata.st_ino,
    )


def iter_search_candidates(
    search_paths: list[str], budget: ValidationBudget | None = None
) -> list[BackfillCandidate]:
    active_budget = _backfill_budget(budget)
    if len(search_paths) > MAX_BACKFILL_SEARCH_PATHS:
        raise ValueError("backfill scan exceeds its search-path bound")
    files: dict[Path, BackfillCandidate] = {}
    visited_directories: set[tuple[int, int]] = set()

    def inspect(
        path: Path, governed_root: Path | None, item: str
    ) -> tuple[Path, os.stat_result]:
        try:
            absolute, metadata = _absolute_no_symlink_entry(path, item)
        except ValueError as exc:
            if governed_root is not None:
                try:
                    resolved = path.resolve(strict=True)
                except OSError:
                    pass
                else:
                    if is_within(resolved, lexical_path(SOURCE_ROOT)):
                        raise ValueError(
                            f"relative backfill path re-enters GOD_SOURCE_ROOT: {item}"
                        ) from exc
            raise
        if governed_root is not None:
            governed = lexical_path(governed_root)
            if not is_within(absolute, governed):
                raise ValueError(f"relative backfill path escapes its governed root: {item}")
            if stat.S_ISDIR(metadata.st_mode) and is_within(
                lexical_path(SOURCE_ROOT), absolute
            ):
                raise ValueError(
                    f"relative backfill directory is an ancestor of GOD_SOURCE_ROOT: {item}"
                )
            if governed != lexical_path(SOURCE_ROOT) and is_within(
                absolute, lexical_path(SOURCE_ROOT)
            ):
                raise ValueError(f"relative backfill path re-enters GOD_SOURCE_ROOT: {item}")
        return absolute, metadata

    def add_file(path: Path, metadata: os.stat_result) -> None:
        if path.suffix.casefold() in BACKFILL_EXCLUDED_SUFFIXES:
            return
        if path not in files:
            active_budget.consume("files")
            files[path] = _candidate_from_metadata(path, metadata)

    def walk_directory(root: Path, governed_root: Path | None, item: str) -> None:
        stack = [(root, 0)]
        while stack:
            active_budget.check_time()
            directory, depth = stack.pop()
            absolute, directory_metadata = inspect(directory, governed_root, item)
            if not stat.S_ISDIR(directory_metadata.st_mode):
                raise ValueError(f"backfill target is not a directory: {directory}")
            identity = (directory_metadata.st_dev, directory_metadata.st_ino)
            if identity in visited_directories:
                raise ValueError("backfill directory traversal cycle detected")
            visited_directories.add(identity)
            if depth > MAX_BACKFILL_RECURSIVE_DEPTH:
                raise ValueError("backfill scan exceeds its recursive depth bound")
            try:
                iterator = os.scandir(absolute)
                with iterator:
                    for entry in iterator:
                        active_budget.consume("entries")
                        if entry.name in BACKFILL_EXCLUDED_PARTS:
                            continue
                        child = Path(entry.path)
                        try:
                            entry_metadata = entry.stat(follow_symlinks=False)
                        except OSError as exc:
                            raise ValueError(
                                "backfill directory entry cannot be inspected safely: "
                                f"{child}"
                            ) from exc
                        if stat.S_ISLNK(entry_metadata.st_mode):
                            if governed_root is not None:
                                try:
                                    resolved = child.resolve(strict=True)
                                except OSError:
                                    continue
                                if is_within(resolved, lexical_path(SOURCE_ROOT)):
                                    raise ValueError(
                                        "relative backfill path re-enters "
                                        f"GOD_SOURCE_ROOT: {item}"
                                    )
                            continue
                        child_absolute, metadata = inspect(
                            child, governed_root, item
                        )
                        if stat.S_ISDIR(metadata.st_mode):
                            stack.append((child_absolute, depth + 1))
                        elif stat.S_ISREG(metadata.st_mode):
                            add_file(child_absolute, metadata)
                        else:
                            raise ValueError(
                                "backfill target is not a regular file or directory: "
                                f"{child}"
                            )
            except OSError as exc:
                raise ValueError(
                    f"backfill directory cannot be enumerated safely: {directory}"
                ) from exc

    for item in search_paths:
        if not isinstance(item, str):
            raise ValueError("backfill search path must be a string")
        expanded = os.path.expandvars(os.path.expanduser(item))
        _validate_backfill_pattern(expanded)
        candidate = Path(expanded)
        if any(part in BACKFILL_EXCLUDED_PARTS for part in candidate.parts):
            continue
        governed_root: Path | None = None
        if candidate.is_absolute():
            pattern = expanded
        else:
            pattern, governed_root = _relative_backfill_pattern(expanded)
        matched = False
        for matched_path in iter_backfill_glob(pattern, active_budget):
            matched = True
            active_budget.consume("matches")
            path, metadata = inspect(Path(matched_path), governed_root, item)
            if any(part in BACKFILL_EXCLUDED_PARTS for part in path.parts):
                continue
            if stat.S_ISDIR(metadata.st_mode):
                walk_directory(path, governed_root, item)
            elif stat.S_ISREG(metadata.st_mode):
                add_file(path, metadata)
            else:
                raise ValueError(
                    f"backfill target is not a regular file or directory: {path}"
                )
        if not matched and not glob.has_magic(pattern):
            try:
                path, metadata = inspect(Path(pattern), governed_root, item)
            except ValueError:
                if Path(pattern).exists() or Path(pattern).is_symlink():
                    raise
                continue
            if stat.S_ISDIR(metadata.st_mode):
                walk_directory(path, governed_root, item)
            elif stat.S_ISREG(metadata.st_mode):
                add_file(path, metadata)
            else:
                raise ValueError(
                    f"backfill target is not a regular file or directory: {path}"
                )
    return [files[path] for path in sorted(files)]


def iter_search_files(search_paths: list[str]) -> list[Path]:
    """Compatibility view over the inode-bearing production enumeration."""

    return [candidate.path for candidate in iter_search_candidates(search_paths)]


def read_bounded_regular_file(
    target: Path | BackfillCandidate,
    budget: ValidationBudget | None = None,
) -> str:
    """Read the enumerated inode through no-follow, nonblocking descriptors."""

    active_budget = _backfill_budget(budget)
    if isinstance(target, BackfillCandidate):
        candidate = target
    else:
        try:
            path, metadata = _absolute_no_symlink_entry(Path(target), str(target))
        except ValueError as exc:
            raise ValueError(
                f"{target}: changed while reading or is a virtual backfill file"
            ) from exc
        candidate = _candidate_from_metadata(path, metadata)
    path = candidate.path
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    root_fd = -1
    directory_fd = -1
    descriptor = -1
    try:
        root_fd = os.open(candidate.anchor, directory_flags)
        directory_fd = root_fd
        parent_parts = candidate.relative.parts[:-1]
        if not candidate.relative.parts:
            raise ValueError(f"{path}: invalid descriptor-relative backfill path")
        for part in parent_parts:
            next_fd = os.open(part, directory_flags, dir_fd=directory_fd)
            if directory_fd != root_fd:
                os.close(directory_fd)
            directory_fd = next_fd
        descriptor = os.open(
            candidate.relative.parts[-1], file_flags, dir_fd=directory_fd
        )
        before = os.fstat(descriptor)
        if (before.st_dev, before.st_ino) != (candidate.device, candidate.inode):
            raise ValueError(f"{path}: changed after backfill enumeration")
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"{path}: is not a regular backfill scan file")
        if before.st_size > MAX_SCAN_FILE_BYTES:
            raise ValueError(f"{path}: exceeds the backfill scan size limit")
        payload = bytearray()
        while len(payload) <= MAX_SCAN_FILE_BYTES:
            active_budget.check_time()
            chunk = os.read(
                descriptor,
                min(65536, MAX_SCAN_FILE_BYTES + 1 - len(payload)),
            )
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) > MAX_SCAN_FILE_BYTES:
            payload.clear()
            raise ValueError(f"{path}: exceeds the backfill scan size limit")
        after = os.fstat(descriptor)
        stable_metadata = (
            (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
            and before.st_size == after.st_size == len(payload)
            and before.st_mtime_ns == after.st_mtime_ns
            and before.st_ctime_ns == after.st_ctime_ns
        )
        if not stable_metadata:
            payload.clear()
            raise ValueError(
                f"{path}: changed while reading or is a virtual backfill file"
            )
        active_budget.consume("retained_bytes", len(payload))
        try:
            return bytes(payload).decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise ValueError(f"{path}: is not valid UTF-8") from exc
    except OSError as exc:
        raise ValueError(f"{path}: cannot be read for backfill scanning") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if directory_fd >= 0 and directory_fd != root_fd:
            os.close(directory_fd)
        if root_fd >= 0:
            os.close(root_fd)


def scan_backfill(
    path: Path, budget: ValidationBudget | None = None
) -> tuple[str, list[str]]:
    active_budget = _backfill_budget(budget)
    manifest = load_selected_yaml(path)
    backfill_id = manifest.get("id")
    if not isinstance(backfill_id, str) or not backfill_id.strip():
        raise ValueError(f"{path}: id must be a non-empty string")
    raw_patterns = manifest.get("forbidden_patterns")
    search_paths = manifest.get("search_paths")
    if not isinstance(raw_patterns, list) or not all(
        isinstance(item, str) for item in raw_patterns
    ):
        raise ValueError(f"{path}: forbidden_patterns must be a list of strings")
    if not isinstance(search_paths, list) or not all(
        isinstance(item, str) for item in search_paths
    ):
        raise ValueError(f"{path}: search_paths must be a list of strings")
    if len(raw_patterns) > MAX_BACKFILL_PATTERNS:
        raise ValueError(f"{path}: forbidden_patterns exceeds its finite bound")
    if len(search_paths) > MAX_BACKFILL_SEARCH_PATHS:
        raise ValueError(f"{path}: search_paths exceeds its finite bound")
    for pattern in raw_patterns:
        if len(pattern.encode("utf-8", errors="strict")) > MAX_BACKFILL_PATTERN_LENGTH:
            raise ValueError(f"{path}: forbidden pattern exceeds its length bound")
    patterns = [re.compile(re.escape(str(pattern))) for pattern in raw_patterns]
    findings: list[str] = []
    if not patterns:
        return backfill_id, findings
    for candidate in iter_search_candidates(search_paths, active_budget):
        text = read_bounded_regular_file(candidate, active_budget)
        for pattern in patterns:
            active_budget.check_time()
            if pattern.search(text):
                active_budget.consume("findings")
                finding = f"{candidate.path}: matched {pattern.pattern}"
                active_budget.consume("retained_bytes", len(finding.encode("utf-8")))
                findings.append(finding)
    return backfill_id, findings


def cmd_backfills_check(_: argparse.Namespace) -> int:
    failures = 0
    try:
        paths = contained_platform_files("backfills", "*.yaml")
    except (OSError, ValueError) as exc:
        print(
            f"ERROR backfills: cannot enumerate selected inputs safely: {exc}",
            file=sys.stderr,
        )
        return 1
    if len(paths) > MAX_BACKFILL_MANIFESTS:
        print(
            "ERROR backfills: manifest count exceeds its finite bound",
            file=sys.stderr,
        )
        return 1
    budget = _backfill_budget()
    for path in paths:
        try:
            backfill_id, findings = scan_backfill(path, budget)
        except (OSError, TypeError, ValueError, re.error) as exc:
            failures += 1
            print(f"ERROR {path}: cannot scan backfill safely: {exc}", file=sys.stderr)
            continue
        if findings:
            failures += 1
            print(f"STALE {backfill_id}")
            for finding in findings[:20]:
                print(f"  {finding}")
            if len(findings) > 20:
                print(f"  ... {len(findings) - 20} more")
        else:
            print(f"OK {backfill_id}")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="33GOD platform control-plane utility")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser(
        "validate", help="validate manifests, changelog, and backfill manifests"
    )
    validate.set_defaults(func=cmd_validate)

    components = sub.add_parser("components", help="component manifest commands")
    components_sub = components.add_subparsers(dest="components_command", required=True)
    components_list = components_sub.add_parser("list", help="list platform components")
    components_list.set_defaults(func=cmd_components_list)

    backfills = sub.add_parser("backfills", help="backfill commands")
    backfills_sub = backfills.add_subparsers(dest="backfills_command", required=True)
    backfills_check = backfills_sub.add_parser(
        "check", help="run read-only stale-config checks"
    )
    backfills_check.set_defaults(func=cmd_backfills_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        with validation_session():
            validate_selected_roots()
            return args.func(args)
    except (configparser.Error, OSError, TypeError, ValueError) as exc:
        print(f"ERROR validation failed safely: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
