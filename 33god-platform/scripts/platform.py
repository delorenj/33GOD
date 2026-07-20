#!/usr/bin/env python3
"""33GOD platform manifest, changelog, and backfill utility."""

from __future__ import annotations

import argparse
import configparser
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc


ROOT = Path(__file__).resolve().parents[1]

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


class GitValidationError(ValueError):
    """A deterministic, secret-free Git provenance failure."""


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected YAML mapping")
    return data


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def lexical_path(path: Path) -> Path:
    """Normalize ``.``/``..`` without following symlinks."""

    return Path(os.path.abspath(os.fspath(path)))


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
        SOURCE_PLATFORM_ROOT
        if path.parts and path.parts[0] == ".."
        else selected_base
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


def platform_config() -> dict[str, Any]:
    return load_yaml(SOURCE_PLATFORM_ROOT / "components.yaml")


def component_paths() -> list[Path]:
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
    return [resolve_path(item, base=SOURCE_PLATFORM_ROOT) for item in declared]


def load_components() -> list[dict[str, Any]]:
    components = []
    for path in component_paths():
        data = load_yaml(path)
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


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run bounded Git without ever reflecting command output into diagnostics."""

    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            text=True,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitValidationError(
            f"Git command failed safely for {repo}: {args[0] if args else 'git'}"
        ) from exc
    if result.returncode:
        raise GitValidationError(
            f"Git command failed safely for {repo}: {args[0] if args else 'git'}"
        )
    return result


def own_checkout_root(repo: Path) -> Path | None:
    if not repo.is_dir() or not (repo / ".git").exists():
        return None
    result = _run_git(repo, "rev-parse", "--show-toplevel")
    top_level = result.stdout.strip()
    if not top_level:
        raise GitValidationError(f"Git command returned no checkout root for {repo}")
    resolved = Path(top_level).resolve()
    return resolved if resolved == repo.resolve() else None


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


def gitlink_entries(root: Path | None = None) -> dict[str, str]:
    """Return root gitlink path -> recorded revision from the selected checkout."""

    root = SOURCE_ROOT if root is None else root
    if own_checkout_root(root) is None:
        raise GitValidationError(
            f"{root}: selected source root must be its own Git checkout"
        )
    result = _run_git(root, "ls-files", "--stage", "-z")
    entries: dict[str, str] = {}
    seen_paths: set[str] = set()
    for record in result.stdout.split("\0"):
        if not record:
            continue
        if "\t" not in record:
            raise GitValidationError("root Git index contains a malformed stage record")
        metadata, path = record.split("\t", 1)
        fields = metadata.split()
        if len(fields) != 3:
            raise GitValidationError("root Git index contains a malformed stage record")
        mode, revision, stage = fields
        if stage != "0" or path in seen_paths:
            raise GitValidationError(
                f"root Git index has a nonzero or duplicate index stage for {path}"
            )
        seen_paths.add(path)
        if not FULL_GIT_REVISION.fullmatch(revision):
            raise GitValidationError(f"root Git index has an invalid object ID for {path}")
        if mode == "160000":
            entries[path] = fields[1]
    return entries


def gitmodule_mappings(root: Path | None = None) -> dict[str, dict[str, str]]:
    """Return submodule mappings keyed by path from the selected checkout."""

    root = SOURCE_ROOT if root is None else root
    if own_checkout_root(root) is None:
        raise GitValidationError(
            f"{root}: selected source root must be its own Git checkout"
        )
    path = root / ".gitmodules"
    if not path.exists() and not path.is_symlink():
        return {}
    if path.is_symlink():
        raise ValueError(f"{path}: .gitmodules must not be a symlink")
    resolved_path = path.resolve(strict=True)
    if not path.is_file() or not is_within(resolved_path, root.resolve()):
        raise ValueError(f"{path}: .gitmodules escapes the selected source root")
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path, encoding="utf-8")
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
            raise ValueError(
                f"{path}: submodule path {mapped_path!r} escapes the selected root"
            )
        name = section.removeprefix('submodule "').removesuffix('"')
        if mapped_path in mappings:
            previous = mappings[mapped_path]["name"]
            raise ValueError(
                f"{path}: ambiguous duplicate submodule path {mapped_path!r} "
                f"in sections {previous!r} and {name!r}"
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
    except ValueError as exc:
        raise ValueError(
            "checkout origin must identify a credential-free hostful HTTPS repository"
        ) from exc
    if (
        parsed.scheme.casefold() == "ssh"
        and parsed.username == "git"
        and parsed.password is None
        and parsed.hostname
        and parsed.path not in {"", "/"}
        and not parsed.query
        and not parsed.fragment
    ):
        return normalize_repository_url(
            f"https://{parsed.hostname}{parsed.path}"
        )
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
    return revision


def git_checkout_origin(repo: Path) -> str | None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "config",
                "--local",
                "--get",
                "remote.origin.url",
            ],
            text=True,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitValidationError(
            f"Git command failed safely for {repo}: config"
        ) from exc
    if result.returncode == 1 and not result.stdout.strip():
        return None
    if result.returncode:
        raise GitValidationError(f"Git command failed safely for {repo}: config")
    return result.stdout.strip() or None


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
            errors.append(f"components/{component_id}.yaml: canonical manifest is missing")
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
        expected_url = gitmodule_mappings()[relative_repo]["url"]
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
    except (configparser.Error, OSError, ValueError) as exc:
        return [f".gitmodules: cannot parse root gitlink inventory safely: {exc}"]
    missing = sorted(set(gitlinks) - set(mappings))
    extra = sorted(set(mappings) - set(gitlinks))
    if missing:
        errors.append(".gitmodules: missing mappings for gitlinks: " + ", ".join(missing))
    if extra:
        errors.append(".gitmodules: mappings without root gitlinks: " + ", ".join(extra))
    for path, mapping in sorted(mappings.items()):
        url = mapping["url"]
        try:
            normalize_repository_url(url)
        except ValueError:
            errors.append(
                f".gitmodules: {path} repository URL must be credential-free hostful HTTPS"
            )
    for path, expected_revision in sorted(gitlinks.items()):
        mapping = mappings.get(path)
        if mapping is None:
            continue
        checkout = lexical_path(SOURCE_ROOT / path)
        if not is_within(checkout, SOURCE_ROOT):
            errors.append(
                f"root gitlink {path}: checkout path escapes GOD_SOURCE_ROOT: {checkout}"
            )
            continue
        resolved_checkout = checkout.resolve()
        if not is_within(resolved_checkout, SOURCE_ROOT):
            errors.append(
                f"root gitlink {path}: checkout resolves outside GOD_SOURCE_ROOT: "
                f"{checkout} -> {resolved_checkout}"
            )
            continue

        actual_revision = git_checkout_revision(checkout)
        if actual_revision is None:
            errors.append(
                f"root gitlink {path}: checkout is not initialized as its own "
                f"Git repository at index revision {expected_revision}"
            )
            continue
        if actual_revision != expected_revision:
            errors.append(
                f"root gitlink {path}: checkout HEAD {actual_revision} does not "
                f"match index revision {expected_revision}"
            )

        actual_origin = git_checkout_origin(checkout)
        expected_origin = mapping["url"]
        if not actual_origin:
            errors.append(
                f"root gitlink {path}: initialized checkout has no origin; "
                "expected the repository-local canonical origin"
            )
        else:
            try:
                matches = normalize_checkout_origin(
                    actual_origin
                ) == normalize_repository_url(expected_origin)
            except ValueError:
                matches = False
            if not matches:
                errors.append(
                    f"root gitlink {path}: checkout origin does not match .gitmodules "
                    "URL identity or is not credential-free"
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
        errors.append(f"components.yaml: acceptance slice cannot be loaded safely: {exc}")
    try:
        errors.extend(validate_component_contracts(components))
    except (OSError, TypeError, ValueError) as exc:
        errors.append(f"components.yaml: component contracts cannot be loaded safely: {exc}")
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
    for path in sorted((SOURCE_PLATFORM_ROOT / "changes").glob("*.jsonl")):
        try:
            handle = path.open("r", encoding="utf-8")
        except OSError as exc:
            errors.append(f"{path}: cannot read change log safely: {exc}")
            continue
        with handle:
            for line_no, line in enumerate(handle, start=1):
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
                change_id = item.get("id")
                if not isinstance(change_id, str) or not change_id:
                    errors.append(f"{path}:{line_no}: id must be a non-empty string")
                elif change_id in ids:
                    errors.append(
                        f"{path}:{line_no}: duplicate change id {change_id!r}"
                    )
                else:
                    ids.add(change_id)
                for key in ("affects", "required_backfills", "docs"):
                    value = item.get(key)
                    if not isinstance(value, list):
                        errors.append(f"{path}:{line_no}: {key} must be a list")
                    elif not all(isinstance(entry, str) for entry in value):
                        errors.append(
                            f"{path}:{line_no}: {key} must contain only strings"
                        )
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
    for path in sorted((SOURCE_PLATFORM_ROOT / "backfills").glob("*.yaml")):
        try:
            item = load_yaml(path)
        except (OSError, ValueError) as exc:
            errors.append(f"{path}: cannot load backfill safely: {exc}")
            continue
        missing = sorted(required - set(item))
        if missing:
            errors.append(f"{path}: missing required keys: {', '.join(missing)}")
        backfill_id = item.get("id")
        if backfill_id in ids:
            errors.append(f"{path}: duplicate backfill id {backfill_id!r}")
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
        print(f"ERROR component registry cannot be loaded safely: {exc}", file=sys.stderr)
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
            raise ValueError(f"relative backfill path escapes GOD_EXTERNAL_ROOT: {item}")
    prefix = _glob_static_prefix(mapped)
    resolved_prefix = prefix.resolve()
    if not is_within(resolved_prefix, allowed_root):
        raise ValueError(f"relative backfill path escapes its governed root: {item}")
    if is_within(resolved_prefix, source_resolved) and allowed_root != source_resolved:
        raise ValueError(f"relative backfill path re-enters GOD_SOURCE_ROOT: {item}")
    return str(mapped), allowed_root


def iter_search_files(search_paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for item in search_paths:
        if not isinstance(item, str):
            raise ValueError("backfill search path must be a string")
        expanded = os.path.expandvars(os.path.expanduser(item))
        candidate = Path(expanded)
        governed_root: Path | None = None
        if candidate.is_absolute():
            pattern = expanded
        else:
            pattern, governed_root = _relative_backfill_pattern(expanded)
        matches = glob.glob(pattern, recursive=True)
        if not matches:
            if not glob.has_magic(pattern):
                maybe = Path(pattern)
                matches = [str(maybe)] if maybe.exists() else []
        for match in matches:
            path = Path(match)
            if governed_root is not None:
                resolved_match = path.resolve()
                if not is_within(resolved_match, governed_root):
                    raise ValueError(
                        f"relative backfill path escapes its governed root: {item}"
                    )
                if governed_root != SOURCE_ROOT.resolve() and is_within(
                    resolved_match, SOURCE_ROOT.resolve()
                ):
                    raise ValueError(
                        f"relative backfill path re-enters GOD_SOURCE_ROOT: {item}"
                    )
            if path.is_file():
                files.append(path)
            elif path.is_dir():
                for child in path.rglob("*"):
                    if governed_root is not None and not is_within(
                        child.resolve(), governed_root
                    ):
                        raise ValueError(
                            f"relative backfill path escapes its governed root: {item}"
                        )
                    if child.is_file() and ".git" not in child.parts:
                        files.append(child)
    return sorted(set(files))


def scan_backfill(path: Path) -> tuple[str, list[str]]:
    manifest = load_yaml(path)
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
    patterns = [
        re.compile(re.escape(str(pattern)))
        for pattern in raw_patterns
    ]
    findings: list[str] = []
    if not patterns:
        return manifest["id"], findings
    for file_path in iter_search_files(search_paths):
        try:
            if file_path.stat().st_size > MAX_SCAN_FILE_BYTES:
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in patterns:
            if pattern.search(text):
                findings.append(f"{file_path}: matched {pattern.pattern}")
    return manifest["id"], findings


def cmd_backfills_check(_: argparse.Namespace) -> int:
    failures = 0
    for path in sorted((SOURCE_PLATFORM_ROOT / "backfills").glob("*.yaml")):
        try:
            backfill_id, findings = scan_backfill(path)
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
        validate_selected_roots()
        return args.func(args)
    except (configparser.Error, OSError, TypeError, ValueError) as exc:
        print(f"ERROR validation failed safely: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
