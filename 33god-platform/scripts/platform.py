#!/usr/bin/env python3
"""33GOD platform manifest, changelog, and backfill utility."""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(os.environ.get("GOD_SOURCE_ROOT", ROOT.parent)).expanduser().resolve()
SOURCE_PLATFORM_ROOT = SOURCE_ROOT / "33god-platform"
MAX_SCAN_FILE_BYTES = 1_000_000


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected YAML mapping")
    return data


def resolve_path(value: str | Path, base: Path = ROOT) -> Path:
    raw = os.path.expandvars(os.path.expanduser(str(value)))
    path = Path(raw)
    if not path.is_absolute():
        if str(path).startswith(".."):
            base = SOURCE_PLATFORM_ROOT
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


def validate_components() -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    required = {"id", "name", "role", "repo", "description", "changelog"}
    for component in load_components():
        path = component["_path"]
        missing = sorted(required - set(component))
        if missing:
            errors.append(f"{path}: missing required keys: {', '.join(missing)}")
            continue

        component_id = str(component["id"])
        if component_id in seen:
            errors.append(f"{path}: duplicate component id {component_id!r}")
        seen.add(component_id)

        repo = resolve_path(component["repo"])
        if not repo.exists():
            errors.append(f"{path}: repo path does not exist: {repo}")

        topics = component.get("changelog", {}).get("topics")
        if not isinstance(topics, list) or not topics:
            errors.append(f"{path}: changelog.topics must be a non-empty list")

        compose = component.get("compose", {})
        for compose_file in compose.get("files", []) or []:
            resolved = resolve_path(compose_file)
            if not resolved.exists():
                errors.append(f"{path}: compose file does not exist: {resolved}")

    return errors


def validate_changes() -> list[str]:
    errors: list[str] = []
    required = {"id", "date", "component", "kind", "summary", "affects", "required_backfills", "docs"}
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
                    errors.append(f"{path}:{line_no}: missing required keys: {', '.join(missing)}")
                change_id = item.get("id")
                if change_id in ids:
                    errors.append(f"{path}:{line_no}: duplicate change id {change_id!r}")
                ids.add(change_id)
                for key in ("affects", "required_backfills", "docs"):
                    if not isinstance(item.get(key), list):
                        errors.append(f"{path}:{line_no}: {key} must be a list")
    return errors


def validate_backfill_manifests() -> list[str]:
    errors: list[str] = []
    required = {"id", "title", "owner_component", "kind", "summary", "search_paths", "forbidden_patterns", "remediation"}
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
        contents = item.get("required_contents", {})
        if not isinstance(contents, dict) or not all(
            isinstance(name, str)
            and isinstance(needles, list)
            and all(isinstance(needle, str) and needle for needle in needles)
            for name, needles in contents.items()
        ):
            errors.append(f"{path}: required_contents must map paths to lists of non-empty strings")
        symlinks = item.get("required_symlinks", {})
        if not isinstance(symlinks, dict) or not all(
            isinstance(name, str) and isinstance(target, str) and target
            for name, target in symlinks.items()
        ):
            errors.append(f"{path}: required_symlinks must map paths to targets")
        if "external_root" in item and (not isinstance(item["external_root"], str) or not item["external_root"].strip()):
            errors.append(f"{path}: external_root must be a non-empty path string")
        if (item.get("required_contents") or item.get("required_symlinks")) and not item.get("external_root"):
            errors.append(f"{path}: external_root is required for required checks")
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
    for component in load_components():
        repo = resolve_path(component["repo"])
        compose_files = component.get("compose", {}).get("files", []) or []
        rows.append(
            (
                component["id"],
                component["role"],
                "present" if repo.exists() else "missing",
                ",".join(component.get("compose", {}).get("profiles", []) or []),
                str(repo),
                str(len(compose_files)),
            )
        )
    headers = ("id", "role", "repo", "profiles", "path", "compose")
    widths = [max(len(str(row[i])) for row in [headers, *rows]) for i in range(len(headers))]
    print("  ".join(str(headers[i]).ljust(widths[i]) for i in range(len(headers))))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(str(row[i]).ljust(widths[i]) for i in range(len(row))))
    return 0


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
    patterns = [re.compile(re.escape(str(pattern))) for pattern in manifest.get("forbidden_patterns", [])]
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


def check_required_contract(manifest: dict[str, Any]) -> tuple[str, list[str]]:
    """Check explicit external files and skill memberships without sweeping a repo."""
    if "external_root" not in manifest:
        if manifest.get("required_contents") or manifest.get("required_symlinks"):
            return "NOT VERIFIED", ["external_root missing for required checks"]
        return "OK", []
    root = resolve_path(manifest["external_root"])
    if not root.is_dir():
        return "NOT VERIFIED", [f"external source unavailable: {root}"]
    root = root.resolve()
    findings: list[str] = []

    def contained_path(relative: str) -> Path | None:
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            findings.append(f"{relative!r}: expected path within external_root")
            return None
        path = root / candidate
        try:
            path.resolve().relative_to(root)
        except (ValueError, OSError, RuntimeError):
            findings.append(f"{relative!r}: path escapes external_root or cannot resolve")
            return None
        return path

    for relative, needles in manifest.get("required_contents", {}).items():
        path = contained_path(relative)
        if path is None:
            continue
        if path.is_symlink() or not path.is_file():
            findings.append(f"{path}: expected regular file")
            continue
        try:
            if path.stat().st_size > MAX_SCAN_FILE_BYTES:
                findings.append(f"{path}: exceeds maximum scan size")
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            return "NOT VERIFIED", [f"cannot read {path}: {exc}"]
        for needle in needles:
            if needle not in text:
                findings.append(f"{path}: missing {needle!r}")
    for relative, target in manifest.get("required_symlinks", {}).items():
        path = contained_path(relative)
        if path is None:
            continue
        if not path.is_symlink():
            findings.append(f"{path}: expected symlink to {target!r}")
        elif os.readlink(path) != target or not path.is_dir():
            findings.append(f"{path}: expected resolved symlink to {target!r}")
    return ("STALE" if findings else "OK"), findings


def cmd_backfills_check(_: argparse.Namespace) -> int:
    failures = 0
    for path in sorted((ROOT / "backfills").glob("*.yaml")):
        backfill_id, forbidden_findings = scan_backfill(path)
        manifest = load_yaml(path)
        contract_status, contract_findings = check_required_contract(manifest)
        findings = forbidden_findings + contract_findings
        status = (
            "NOT VERIFIED" if contract_status == "NOT VERIFIED"
            else "STALE" if forbidden_findings or contract_status == "STALE"
            else contract_status
        )
        if status != "OK":
            failures += 1
        print(f"{status} {backfill_id}")
        for finding in findings[:20]:
            print(f"  {finding}")
        if len(findings) > 20:
            print(f"  ... {len(findings) - 20} more")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="33GOD platform control-plane utility")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate manifests, changelog, and backfill manifests")
    validate.set_defaults(func=cmd_validate)

    components = sub.add_parser("components", help="component manifest commands")
    components_sub = components.add_subparsers(dest="components_command", required=True)
    components_list = components_sub.add_parser("list", help="list platform components")
    components_list.set_defaults(func=cmd_components_list)

    backfills = sub.add_parser("backfills", help="backfill commands")
    backfills_sub = backfills.add_subparsers(dest="backfills_command", required=True)
    backfills_check = backfills_sub.add_parser("check", help="run read-only stale-config checks")
    backfills_check.set_defaults(func=cmd_backfills_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
