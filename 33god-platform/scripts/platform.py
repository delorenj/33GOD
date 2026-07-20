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


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
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
    if not is_within(resolved, EXTERNAL_ROOT):
        raise ValueError(
            f"external path resolves outside GOD_EXTERNAL_ROOT: {mapped} -> {resolved}"
        )
    return resolved


def resolve_path(value: str | Path, base: Path = ROOT) -> Path:
    raw = os.path.expandvars(os.path.expanduser(str(value)))
    path = Path(raw)
    if not path.is_absolute():
        if path.parts and path.parts[0] == "..":
            candidate = lexical_path(SOURCE_PLATFORM_ROOT / path)
            if is_within(candidate, SOURCE_ROOT):
                # In-tree component roots are atomic: every descendant stays
                # beneath the selected checkout, so a missing leaf fails
                # closed instead of being borrowed from another checkout.
                resolved = candidate.resolve()
                if not is_within(resolved, SOURCE_ROOT):
                    raise ValueError(
                        "selected in-tree path resolves outside GOD_SOURCE_ROOT: "
                        f"{candidate} -> {resolved}"
                    )
                return resolved
            return resolve_external_path(candidate)
        path = base / path
    return path.resolve()


def platform_config() -> dict[str, Any]:
    return load_yaml(ROOT / "components.yaml")


def component_paths() -> list[Path]:
    cfg = platform_config()
    return [resolve_path(item) for item in cfg.get("component_files", [])]


def load_components() -> list[dict[str, Any]]:
    components = []
    for path in component_paths():
        data = load_yaml(path)
        data["_path"] = path
        components.append(data)
    return components


def recorded_revision(component: dict[str, Any]) -> str | None:
    for field in ("source_revision", "gitlink_revision"):
        value = component.get(field)
        if isinstance(value, str) and value:
            return value
    return None


def acceptance_slice_ids(cfg: dict[str, Any] | None = None) -> list[str]:
    cfg = platform_config() if cfg is None else cfg
    declaration = cfg.get("acceptance_slice") or {}
    if not isinstance(declaration, dict):
        return []
    components = declaration.get("components") or []
    if not isinstance(components, list):
        return []
    return [str(item) for item in components]


def gitlink_entries(root: Path | None = None) -> dict[str, str]:
    """Return root gitlink path -> recorded revision from the selected checkout."""

    root = SOURCE_ROOT if root is None else root
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--stage", "-z"],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        return {}
    entries: dict[str, str] = {}
    for record in result.stdout.split("\0"):
        if not record or "\t" not in record:
            continue
        metadata, path = record.split("\t", 1)
        fields = metadata.split()
        if len(fields) >= 2 and fields[0] == "160000":
            entries[path] = fields[1]
    return entries


def gitmodule_mappings(root: Path | None = None) -> dict[str, dict[str, str]]:
    """Return submodule mappings keyed by path from the selected checkout."""

    root = SOURCE_ROOT if root is None else root
    path = root / ".gitmodules"
    if not path.is_file():
        return {}
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path, encoding="utf-8")
    mappings: dict[str, dict[str, str]] = {}
    for section in parser.sections():
        if not section.startswith('submodule "'):
            continue
        mapped_path = parser.get(section, "path", fallback="").strip()
        if not mapped_path:
            continue
        mappings[mapped_path] = {
            "name": section.removeprefix('submodule "').removesuffix('"'),
            "url": parser.get(section, "url", fallback="").strip(),
        }
    return mappings


def normalize_repository_url(value: str) -> str:
    normalized = value.strip().removesuffix("/").removesuffix(".git")
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix(
            "git@github.com:"
        )
    elif normalized.startswith("ssh://git@github.com/"):
        normalized = "https://github.com/" + normalized.removeprefix(
            "ssh://git@github.com/"
        )
    return normalized.casefold()


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
    if not repo.is_dir() or not (repo / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--show-toplevel", "HEAD"],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        return None
    lines = result.stdout.splitlines()
    if len(lines) != 2 or Path(lines[0]).resolve() != repo.resolve():
        return None
    return lines[1].strip() or None


def git_checkout_origin(repo: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), "config", "--get", "remote.origin.url"],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        return None
    return result.stdout.strip() or None


def component_repo_status(component: dict[str, Any]) -> tuple[str, str | None]:
    """Classify a component's selected repo path.

    Statuses: ``verified`` (initialized Git checkout at the exact recorded
    revision), ``revision-mismatch``, ``uninitialized`` (recorded revision but
    no Git checkout), ``not-a-git-checkout`` (non-empty directory without Git
    identity), ``present`` (exists, no recorded revision), ``missing``.
    """
    repo = resolve_path(component["repo"])
    recorded = recorded_revision(component)
    if recorded is None:
        return ("present", None) if repo.exists() else ("missing", None)

    relative_repo = root_relative_repo(repo)
    if relative_repo is not None:
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

    if not repo.exists():
        return ("uninitialized", None)
    revision = git_checkout_revision(repo)
    if revision is None:
        if not repo.is_dir() or any(repo.iterdir()):
            return ("not-a-git-checkout", None)
        return ("uninitialized", None)
    if revision != recorded:
        return ("revision-mismatch", revision)

    if relative_repo is not None:
        expected_url = gitmodule_mappings()[relative_repo]["url"]
        actual_url = git_checkout_origin(repo)
        if (
            not actual_url
            or normalize_repository_url(actual_url)
            != normalize_repository_url(expected_url)
        ):
            return ("identity-mismatch", revision)
    return ("verified", revision)


def repo_is_populated(component: dict[str, Any]) -> bool:
    status, _ = component_repo_status(component)
    if recorded_revision(component) is None:
        return status == "present"
    return status == "verified"


def validate_gitlink_inventory() -> list[str]:
    errors: list[str] = []
    try:
        gitlinks = gitlink_entries()
        mappings = gitmodule_mappings()
    except (configparser.Error, OSError) as exc:
        return [f".gitmodules: cannot parse root gitlink inventory safely: {exc}"]
    missing = sorted(set(gitlinks) - set(mappings))
    extra = sorted(set(mappings) - set(gitlinks))
    if missing:
        errors.append(".gitmodules: missing mappings for gitlinks: " + ", ".join(missing))
    if extra:
        errors.append(".gitmodules: mappings without root gitlinks: " + ", ".join(extra))
    for path, mapping in sorted(mappings.items()):
        url = mapping["url"]
        if not url.startswith("https://"):
            errors.append(
                f".gitmodules: {path} must use a credential-free HTTPS URL, found {url!r}"
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
    configured_ids = tuple(
        Path(str(item)).stem for item in platform_config().get("component_files", [])
    )
    if configured_ids != PRODUCT_COMPONENT_IDS:
        errors.append(
            "components.yaml: component_files must be the exact ordered product "
            f"registry {PRODUCT_COMPONENT_IDS}; found {configured_ids}"
        )
    registry_ids = {
        str(component.get("id")) for component in components if component.get("id")
    }
    unknown = [item for item in slice_ids if item not in registry_ids]
    if unknown:
        errors.append(
            "components.yaml: acceptance_slice components missing from registry: "
            + ", ".join(unknown)
        )
    for component in components:
        if str(component.get("id")) in slice_ids and recorded_revision(component) is None:
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
        }:
            errors.append(
                f"{path}: repo verification failed for {repo}: {status}"
                + (f" at {revision}" if revision else "")
                + f"; recorded {recorded_revision(component)}"
            )

        topics = component.get("changelog", {}).get("topics")
        if not isinstance(topics, list) or not topics:
            errors.append(f"{path}: changelog.topics must be a non-empty list")

        if repo_is_populated(component):
            compose = component.get("compose", {})
            for compose_file in compose.get("files", []) or []:
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
    for path in sorted((ROOT / "changes").glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    item = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    errors.append(f"{path}:{line_no}: invalid JSON: {exc}")
                    continue
                missing = sorted(required - set(item))
                if missing:
                    errors.append(
                        f"{path}:{line_no}: missing required keys: {', '.join(missing)}"
                    )
                change_id = item.get("id")
                if change_id in ids:
                    errors.append(
                        f"{path}:{line_no}: duplicate change id {change_id!r}"
                    )
                ids.add(change_id)
                for key in ("affects", "required_backfills", "docs"):
                    if not isinstance(item.get(key), list):
                        errors.append(f"{path}:{line_no}: {key} must be a list")
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
    for path in sorted((ROOT / "backfills").glob("*.yaml")):
        item = load_yaml(path)
        missing = sorted(required - set(item))
        if missing:
            errors.append(f"{path}: missing required keys: {', '.join(missing)}")
        backfill_id = item.get("id")
        if backfill_id in ids:
            errors.append(f"{path}: duplicate backfill id {backfill_id!r}")
        ids.add(backfill_id)
        if not isinstance(item.get("search_paths"), list):
            errors.append(f"{path}: search_paths must be a list")
        if not isinstance(item.get("forbidden_patterns"), list):
            errors.append(f"{path}: forbidden_patterns must be a list")
    return errors


def cmd_validate(_: argparse.Namespace) -> int:
    errors = []
    errors.extend(validate_components())
    errors.extend(validate_changes())
    errors.extend(validate_backfill_manifests())
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
        try:
            repo: Path | str = resolve_path(component["repo"])
            status, revision = component_repo_status(component)
        except (configparser.Error, OSError, TypeError, ValueError):
            repo = str(component.get("repo", "<missing>"))
            status, revision = "invalid", None
        recorded = recorded_revision(component)
        compose_files = component.get("compose", {}).get("files", []) or []
        rows.append(
            (
                component["id"],
                component["role"],
                "acceptance" if component["id"] in slice_ids else "registry",
                status,
                (revision or recorded or "-")[:12],
                ",".join(component.get("compose", {}).get("profiles", []) or []),
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


def iter_search_files(search_paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for item in search_paths:
        resolved = os.path.expandvars(os.path.expanduser(item))
        candidate = Path(resolved)
        if not candidate.is_absolute():
            resolved = str(ROOT / candidate)
        matches = glob.glob(resolved, recursive=True)
        if not matches:
            maybe = resolve_path(item)
            matches = [str(maybe)] if maybe.exists() else []
        for match in matches:
            path = Path(match)
            if path.is_file():
                files.append(path)
            elif path.is_dir():
                for child in path.rglob("*"):
                    if child.is_file() and ".git" not in child.parts:
                        files.append(child)
    return sorted(set(files))


def scan_backfill(path: Path) -> tuple[str, list[str]]:
    manifest = load_yaml(path)
    patterns = [
        re.compile(re.escape(str(pattern)))
        for pattern in manifest.get("forbidden_patterns", [])
    ]
    findings: list[str] = []
    if not patterns:
        return manifest["id"], findings
    for file_path in iter_search_files(manifest.get("search_paths", [])):
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
    for path in sorted((ROOT / "backfills").glob("*.yaml")):
        backfill_id, findings = scan_backfill(path)
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
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
