#!/usr/bin/env python3
"""Read-only 33GOD topology, documentation, and contract parity check."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import tomllib
import unicodedata
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from scripts.validation_runtime import (  # noqa: E402
    BoundedProcessError,
    ValidationBudget,
    run_bounded_process,
    sanitized_command_environment,
    sanitized_git_environment,
    terminate_process_group,
    verify_local_git_object_closure,
)

try:
    import yaml
except ImportError:  # The structural checks still run without PyYAML.
    yaml = None


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
DOCUMENTED_COMPONENTS = ("bloodbank", "candystore", "holocene", "pjangler")
REQUIRED_ROOT_DOCS = (
    "index.md",
    "project-overview.md",
    "source-tree-analysis.md",
    "integration-architecture.md",
    "deployment-guide.md",
    "drift-governance.md",
    "project-parts.json",
    "project-scan-report.json",
)
FORBIDDEN_MARKERS = re.compile(
    r"(?i)(?:\bTODO\b|\bTBD\b|to be generated|coming soon|not yet generated|placeholder)"
)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
LIFECYCLE_IMAGE = (
    "ghcr.io/delorenj/lifecycle@"
    "sha256:b216be4e1b796236309ee0b39120b0f353b62ee9f3c677901b2441a2c7aef210"
)
LIFECYCLE_TAG = (
    "ghcr.io/delorenj/lifecycle:sha-cda59658bef6d586c8aa01cacd88bc4e3ee867e0"
)
COMPONENT_REVISIONS = {
    "bloodbank": "aacd88564ea299924b8298165933ba821640bdba",
    "lifecycle": "cda59658bef6d586c8aa01cacd88bc4e3ee867e0",
    "candystore": "3c00080446bb9d4cb55c670477983306abcfe7ce",
    "momo": "8eeff1ce839c3bcffc2d3943322bc1dd8ef63fee",
    "holocene": "2beee67b433f1bd66abf7bce552d90e89413ae27",
    "pjangler": "13be237eaa454f22525dd9b4e5dd804b4516c212",
}
COMMONPROJECT_REVISION = "5dce335d10b44692414a5c67f12684ecc4fa5a41"
LIFECYCLE_DIGEST_REFERENCE = re.compile(
    r"ghcr\.io/delorenj/lifecycle@sha256:[0-9a-f]{64}"
)
ECOSYSTEM_AUTHORITY_CONTRACT = (
    "Plane ticket/work-item and board/lane operations "
    "(project-lifecycle, never Lifecycle authority)",
    "standalone Lifecycle component is the sole deterministic 33GOD lifecycle authority",
    "Plane owns ticket/work-item records and board/lane state only",
    "`project-lifecycle` routes only Plane ticket/work-item and board/lane mutations",
    "Momo chooses, ranks, and executes only Lifecycle-legal work and publishes evidence",
    "Holocene renders authoritative Lifecycle data and invokes high-level actions",
    "Bloodbank owns canonical inter-service contracts and NATS/Dapr transport",
    "Candystore owns append-only audit history and Lifecycle read projections",
)
BLOODBANK_API_CURRENT_CONTRACT = (
    "`assert_contract()` invokes `assert_subject_matches()`",
    "registered contracts include snapshot v3",
    "Holocene has an implemented Bloodbank command client",
    "PJangler's generators use fixed six-token canonical subjects",
    "Root Compose runs the standalone Lifecycle authority",
    "schemas above are registered and operational",
)
BLOODBANK_API_STALE_PATTERNS = {
    "missing subject/type binding": re.compile(
        r"(?i)assert_contract.{0,80}(?:does not|doesn't|fails to|omits).{0,40}"
        r"assert_subject_matches"
    ),
    "absent Holocene Bloodbank client": re.compile(
        r"(?i)Holocene.{0,80}(?:lacks|has no|without|does not have|no functioning)"
        r".{0,50}Bloodbank(?: command)? client"
    ),
    "noncanonical PJangler routing": re.compile(
        r"(?i)PJangler.{0,80}\bnon-?canonical\b"
    ),
    "planned or absent Lifecycle topology": re.compile(
        r"(?i)Lifecycle.{0,80}(?:still needs to be added|needs to be added|"
        r"will be added|absent from|not present in).{0,60}(?:Compose|topology)?"
    ),
    "unregistered Lifecycle schemas": re.compile(
        r"(?i)(?:Lifecycle )?schemas?.{0,80}(?:not operational|unregistered|"
        r"not registered|not wired)"
    ),
    "shared reconcile authority": re.compile(
        r"(?i)(?:Momo(?:/Hermes)?|Hermes)\s+(?:and|with)\s+Lifecycle\s+"
        r"(?:share|drive|own).{0,40}reconcile loop"
    ),
    "client lifecycle authority overclaim": re.compile(
        r"(?i)\b(?:Plane|Momo|Holocene)\b.{0,35}"
        r"(?:owns|evaluates|writes|persists|drives).{0,35}"
        r"(?:Lifecycle truth|Lifecycle state|Lifecycle authority)"
    ),
}
AUTHORITY_PARITY_PATTERNS = {
    "Holocene control-plane role": re.compile(
        r"(?i)(?:\bHolocene\b.{0,100}\bcontrol[-_ ]?plane\b|"
        r"\bcontrol[-_ ]?plane\b[^A-Za-z0-9]{0,12}\bHolocene\b|"
        r"\bcontrol-plane-dashboard\b)"
    ),
    "shared Momo reconcile loop": re.compile(
        r"(?i)(?:\bMomo(?:/Hermes)?\s+(?:and|with)\s+Lifecycle\s+"
        r"(?:share|drive|run|own)s?\b.{0,40}\breconcile loop\b|"
        r"\bMomo\s+(?:shares|drives|runs|owns)\s+(?:the\s+)?"
        r"(?:(?:same|one)\s+|Lifecycle's\s+)?reconcile loop\b)"
    ),
    "Momo determines lifecycle truth": re.compile(
        r"(?i)\bMomo\s+(?:determines?|decides?)\s+(?:what\s+is\s+)?"
        r"(?:the\s+)?(?:lifecycle\s+)?truth\b"
    ),
    "non-Lifecycle component authority role": re.compile(
        r"(?i)(?:\b(?:Candystore|PJangler|Holocene)\b\s+"
        r"(?:is|acts as|serves as|owns|runs|provides)\b.{0,60}"
        r"\b(?:lifecycle[- ]authority|lifecycle[- ]writer|lifecycle[- ]engine)\b|"
        r"\b(?:lifecycle[- ]authority|lifecycle[- ]writer|lifecycle[- ]engine)\b\s+"
        r"(?:is|belongs to|is owned by|is provided by)\s+"
        r"\b(?:Candystore|PJangler|Holocene)\b|"
        r"\|\s*(?:lifecycle[- ]authority|lifecycle[- ]writer|lifecycle[- ]engine)\s*"
        r"\|\s*(?:Candystore|PJangler|Holocene)\s*\|)"
    ),
}
DEPLOYMENT_CEREMONY_PATTERNS = {
    "safe-coexistence ceremony": re.compile(
        r"(?i)\b(?:safe[- ]?)?coexist(?:ence|s|ing)?\b"
    ),
    "Momo-offline safety ceremony": re.compile(r"(?i)\bMomo[- ]offline\s+safety\b"),
    "promotion boundary": re.compile(r"(?im)^##\s+Promotion boundary\s*$"),
    "separate owner decision": re.compile(r"(?i)\bseparate owner decision\b"),
    "destructive-looking acceptance ceremony": re.compile(
        r"(?i)\bdestructive[- ]looking acceptance work\b"
    ),
    "release or deployment ceremony": re.compile(
        r"(?i)\b(?:release|promotion|deployment) ceremony\b"
    ),
    "root integration publication ceremony": re.compile(
        r"(?i)\broot integration publication\b"
    ),
    "release-tag ceremony": re.compile(r"(?i)\brelease[- ]tag\b"),
    "release-promotion ceremony": re.compile(r"(?i)\brelease[- ]promotion\b"),
    "release-tag-promotion ceremony": re.compile(
        r"(?i)\brelease[- ]tag[- ]promotion\b"
    ),
}
TICKET_LIFECYCLE_COMMAND_SURFACES = (
    Path(".augment/commands/bmad/workflows/custom-ticket-lifecycle.md"),
    Path(".claude/commands/bmad/custom/workflows/ticket-lifecycle.md"),
    Path(".gemini/commands/bmad-workflow-custom-ticket-lifecycle.toml"),
    Path(".opencode/command/bmad-custom-ticket-lifecycle.md"),
)
CURRENT_DEPLOYMENT_ARTIFACTS = {
    "PRD.md",
    "docs/deployment-guide.md",
    "docs/architecture-lifecycle.md",
    "docs/integration-architecture.md",
    "33god-platform/README.md",
    "_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-18.md",
}
CURRENT_AUTHORITY_JSON_ARTIFACTS = ("docs/project-scan-report.json",)
GIT_TIMEOUT_SECONDS = 10
MAX_GITLINK_DEPTH = 16
MAX_OPERATIONAL_FILE_BYTES = 1_000_000
MAX_GIT_TREE_ENTRIES = 100_000
MAX_GIT_TREE_OUTPUT_BYTES = 16_000_000
MAX_GIT_BATCH_OUTPUT_BYTES = 16_000_000
MAX_GIT_TEXT_OUTPUT_BYTES = 16_000_000
FULL_GIT_REVISION = re.compile(r"[0-9a-f]{40}")
VALID_GIT_TREE_MODES = {"100644", "100755", "120000", "160000"}


_BoundedProcessError = BoundedProcessError
_run_bounded_process = run_bounded_process
_terminate_process_group = terminate_process_group


class ValidationState:
    """One invocation's immutable revisions, trees, and aggregate resource budget."""

    def __init__(self) -> None:
        self.budget = ValidationBudget()
        self.checkout_roots: dict[str, bool] = {}
        self.revisions: dict[str, str | None] = {}
        self.snapshots: dict[tuple[str, str], Any] = {}


_ACTIVE_VALIDATION_STATE: ContextVar[ValidationState | None] = ContextVar(
    "doc_drift_validation_state", default=None
)


@contextmanager
def validation_session() -> Iterator[ValidationState]:
    """Share one exact revision and one finite budget across a complete verdict."""

    existing = _ACTIVE_VALIDATION_STATE.get()
    if existing is not None:
        yield existing
        return
    state = ValidationState()
    token = _ACTIVE_VALIDATION_STATE.set(state)
    try:
        yield state
    finally:
        _ACTIVE_VALIDATION_STATE.reset(token)


def _validation_state() -> ValidationState | None:
    return _ACTIVE_VALIDATION_STATE.get()


def _repository_key(repo: Path) -> str:
    return os.path.abspath(os.fspath(repo))


class DuplicateYamlKeyError(ValueError):
    """A YAML mapping repeated a key at some nesting level."""


if yaml is not None:

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


class Reporter:
    def __init__(self) -> None:
        self.passes = 0
        self.warnings = 0
        self.failures = 0

    def emit(self, level: str, check: str, detail: str) -> None:
        state = _validation_state()
        if state is not None:
            state.budget.check_time()
            if level != "PASS":
                state.budget.consume("findings")
        print(f"{level:<4} {check}: {detail}")
        if level == "PASS":
            self.passes += 1
        elif level == "WARN":
            self.warnings += 1
        else:
            self.failures += 1

    def passed(self, check: str, detail: str) -> None:
        self.emit("PASS", check, detail)

    def warn(self, check: str, detail: str) -> None:
        self.emit("WARN", check, detail)

    def fail(self, check: str, detail: str) -> None:
        self.emit("FAIL", check, detail)


def load_yaml_text(text: str, label: str) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML unavailable")
    try:
        value = yaml.load(text, Loader=_UniqueKeyLoader)
    except DuplicateYamlKeyError as exc:
        raise ValueError(f"{label}: duplicate YAML mapping key") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"{label}: invalid YAML") from exc
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ValueError("expected a YAML mapping")
    return value


def load_yaml(path: Path) -> dict[str, Any]:
    return load_yaml_text(path.read_text(encoding="utf-8", errors="strict"), str(path))


def check_root_artifacts(source: Path, docs: Path, report: Reporter) -> None:
    del source
    checkout = docs.parent
    snapshot = git_snapshot(checkout)
    missing = [
        name
        for name in REQUIRED_ROOT_DOCS
        if not repository_regular_file_exists(checkout, snapshot, f"docs/{name}")
    ]
    if missing:
        report.fail(
            "root-docs", f"missing required files under {docs}: {', '.join(missing)}"
        )
    else:
        report.passed(
            "root-docs", f"all {len(REQUIRED_ROOT_DOCS)} core files exist under {docs}"
        )

    required_configs = (
        "_bmad/core/config.yaml",
        "_bmad/bmm/config.yaml",
    )
    absent = [
        str(checkout / relative)
        for relative in required_configs
        if not repository_regular_file_exists(checkout, snapshot, relative)
    ]
    if absent:
        report.fail("root-bmad", f"missing root configuration: {', '.join(absent)}")
    elif yaml is None:
        report.warn(
            "root-bmad", "PyYAML unavailable; files exist but YAML parsing was skipped"
        )
    else:
        try:
            texts = [
                repository_relative_text(
                    checkout,
                    snapshot,
                    relative,
                    label=f"root BMAD config {relative}",
                )
                for relative in required_configs
            ]
            if any(text is None for text in texts):
                raise RuntimeError("exact root BMAD config blob is missing")
            core, bmm = (
                load_yaml_text(str(text), relative)
                for text, relative in zip(texts, required_configs, strict=True)
            )
            expected = {
                "project_name": "33GOD",
                "user_name": "Jarad",
                "communication_language": "English",
                "document_output_language": "English",
                "output_folder": "{project-root}/_bmad-output",
            }
            errors = [
                f"{key}={core.get(key)!r}"
                for key, value in expected.items()
                if core.get(key) != value
            ]
            if bmm.get("project_knowledge") != "{project-root}/docs":
                errors.append(f"project_knowledge={bmm.get('project_knowledge')!r}")
            if errors:
                report.fail(
                    "root-bmad",
                    "root-relative configuration mismatch: " + ", ".join(errors),
                )
            else:
                report.passed(
                    "root-bmad",
                    "root configs parse and resolve to _bmad-output/docs conventions",
                )
        except Exception as exc:
            report.fail("root-bmad", f"YAML parse failed: {exc}")


def topology_declaration_errors(
    parts_data: dict[str, Any],
    platform_data: dict[str, Any],
    scan_data: dict[str, Any],
) -> list[str]:
    """Validate the six-component slice separately from the product registry."""

    errors: list[str] = []
    parts = parts_data.get("parts")
    if not isinstance(parts, list):
        parts = []
    part_ids = tuple(str(item.get("id")) for item in parts if isinstance(item, dict))
    acceptance_slice = platform_data.get("acceptance_slice")
    if not isinstance(acceptance_slice, dict):
        acceptance_slice = {}
    acceptance_components = acceptance_slice.get("components")
    if not isinstance(acceptance_components, list):
        acceptance_components = []
    platform_slice = tuple(str(item) for item in acceptance_components)
    if (
        parts_data.get("scope_policy") != "lifecycle-acceptance-slice-exact"
        or part_ids != LIFECYCLE_ACCEPTANCE_SLICE
        or platform_slice != LIFECYCLE_ACCEPTANCE_SLICE
    ):
        errors.append(
            "Lifecycle acceptance slice must be the exact ordered set "
            f"{LIFECYCLE_ACCEPTANCE_SLICE}; project-parts={part_ids}, "
            f"platform={platform_slice}"
        )

    product_registry = parts_data.get("product_registry")
    if not isinstance(product_registry, dict):
        product_registry = {}
    registry_components = product_registry.get("components")
    if not isinstance(registry_components, list):
        registry_components = []
    declared_registry = tuple(str(item) for item in registry_components)
    component_files = platform_data.get("component_files")
    platform_manifest_paths = (
        tuple(component_files)
        if isinstance(component_files, list)
        and all(isinstance(item, str) for item in component_files)
        else ()
    )
    if (
        product_registry.get("scope_policy") != "exact"
        or declared_registry != PRODUCT_COMPONENT_IDS
        or platform_manifest_paths != COMPONENT_FILE_PATHS
    ):
        errors.append(
            "twelve-component product registry must be the exact ordered set "
            f"{PRODUCT_COMPONENT_IDS}; project-parts={declared_registry}, "
            f"platform-paths={platform_manifest_paths}"
        )

    findings = scan_data.get("findings")
    if not isinstance(findings, dict):
        findings = {}
    classification = findings.get("project_classification")
    if not isinstance(classification, dict):
        classification = {}
    project_types = scan_data.get("project_types")
    if not isinstance(project_types, list):
        project_types = []
    scan_parts = tuple(
        str(item.get("part_id")) for item in project_types if isinstance(item, dict)
    )
    if (
        classification.get("acceptance_slice_count") != len(LIFECYCLE_ACCEPTANCE_SLICE)
        or classification.get("product_registry_count") != len(PRODUCT_COMPONENT_IDS)
        or scan_parts != LIFECYCLE_ACCEPTANCE_SLICE
    ):
        errors.append(
            "project-scan-report must record six acceptance parts and twelve "
            f"registry components; counts={classification!r}, parts={scan_parts}"
        )
    scan_registry_value = findings.get("product_registry")
    scan_registry = (
        tuple(str(item) for item in scan_registry_value)
        if isinstance(scan_registry_value, list)
        else ()
    )
    if scan_registry != PRODUCT_COMPONENT_IDS:
        errors.append(
            "project-scan-report scan product registry must be the exact ordered "
            f"set {PRODUCT_COMPONENT_IDS}; found {scan_registry}"
        )
    if scan_data.get("project_root") != "{project-root}":
        errors.append(
            "project-scan-report project_root must use the reproducible "
            "{project-root} token"
        )
    return errors


def canonical_platform_manifest_path_errors(source: Path) -> list[str]:
    """Require every platform declaration to be a real canonical in-tree file."""

    errors: list[str] = []
    snapshot = git_snapshot(source)
    required = ("components.yaml", *COMPONENT_FILE_PATHS)
    if snapshot is not None:
        for relative in required:
            path = f"33god-platform/{relative}"
            entry = snapshot.get(path)
            if entry is None:
                errors.append(f"{path} is missing or unreadable")
            elif entry[0] not in {"100644", "100755"}:
                errors.append(f"{path} must be a regular exact Git blob")
        return errors

    source_resolved = source.resolve()
    platform = source / "33god-platform"
    try:
        platform_resolved = platform.resolve(strict=True)
    except (OSError, RuntimeError):
        return ["33god-platform is missing or cannot be resolved safely"]
    if (
        platform.is_symlink()
        or not platform.is_dir()
        or not path_is_within(platform_resolved, source_resolved)
    ):
        return ["33god-platform must be a real directory inside the selected source"]

    for relative in required:
        candidate = platform / relative
        cursor = platform
        traverses_symlink = False
        for part in PurePosixPath(relative).parts:
            cursor /= part
            if cursor.is_symlink():
                traverses_symlink = True
                break
        if traverses_symlink:
            errors.append(f"33god-platform/{relative} must not traverse a symlink")
            continue
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            errors.append(f"33god-platform/{relative} is missing or unreadable")
            continue
        if not candidate.is_file() or not path_is_within(resolved, platform_resolved):
            errors.append(
                f"33god-platform/{relative} must be a real file inside 33god-platform"
            )
    return errors


def check_part_declaration(source: Path, docs: Path, report: Reporter) -> None:
    platform_path = source / "33god-platform/components.yaml"
    path_errors = canonical_platform_manifest_path_errors(source)
    try:
        docs_checkout = docs.parent
        docs_snapshot = git_snapshot(docs_checkout)
        source_snapshot = (
            docs_snapshot if source == docs_checkout else git_snapshot(source)
        )
        parts_text = repository_relative_text(
            docs_checkout,
            docs_snapshot,
            "docs/project-parts.json",
            label="root project-parts declaration",
        )
        scan_text = repository_relative_text(
            docs_checkout,
            docs_snapshot,
            "docs/project-scan-report.json",
            label="root project scan declaration",
        )
        platform_text = repository_relative_text(
            source,
            source_snapshot,
            "33god-platform/components.yaml",
            label="root platform declaration",
        )
        if parts_text is None or scan_text is None or platform_text is None:
            raise RuntimeError("an exact root topology declaration is missing")
        parts_data = json.loads(parts_text)
        scan_data = json.loads(scan_text)
        platform_data = load_yaml_text(platform_text, str(platform_path))
        for label, declaration in (
            ("project-parts.json", parts_data),
            ("project-scan-report.json", scan_data),
            ("33god-platform/components.yaml", platform_data),
        ):
            if not isinstance(declaration, dict):
                raise ValueError(
                    f"{label}: expected a top-level mapping, found "
                    f"{type(declaration).__name__}"
                )
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        report.fail("topology-scope", f"cannot parse declaration: {exc}")
        return
    errors = [
        *path_errors,
        *topology_declaration_errors(parts_data, platform_data, scan_data),
    ]
    if errors:
        report.fail("topology-scope", "; ".join(errors))
    else:
        report.passed(
            "topology-scope",
            "exact six-component Lifecycle slice and twelve-component registry",
        )

    root_errors: list[str] = []
    source_resolved = source.resolve()
    for part in LIFECYCLE_ACCEPTANCE_SLICE:
        candidate = source / part
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            root_errors.append(f"{part} is missing or cannot be resolved safely")
            continue
        if (
            candidate.is_symlink()
            or not candidate.is_dir()
            or not path_is_within(resolved, source_resolved)
        ):
            root_errors.append(f"{part} escapes selected source root")
    if root_errors:
        report.fail("component-roots", "; ".join(root_errors))
    else:
        report.passed("component-roots", "all six Lifecycle acceptance roots exist")


def check_component_bmad(source: Path, docs: Path, report: Reporter) -> None:
    docs_checkout = docs.parent
    docs_snapshot = git_snapshot(docs_checkout)
    for part in DOCUMENTED_COMPONENTS:
        root = source / part
        component_snapshot = git_snapshot(root)
        config_relatives = ("_bmad/core/config.yaml", "_bmad/bmm/config.yaml")
        configs = tuple(root / relative for relative in config_relatives)
        missing = [
            str(path.relative_to(source))
            for path, relative in zip(configs, config_relatives, strict=True)
            if not repository_regular_file_exists(root, component_snapshot, relative)
        ]
        root_doc_relatives = (
            f"docs/architecture-{part}.md",
            f"docs/development-guide-{part}.md",
        )
        missing.extend(
            str(docs_checkout / relative)
            for relative in root_doc_relatives
            if not repository_regular_file_exists(
                docs_checkout, docs_snapshot, relative
            )
        )
        if not repository_directory_exists(root, component_snapshot, "docs"):
            missing.append(f"{part}/docs/")
        if missing:
            report.fail(
                f"component-{part}",
                "missing BMAD/config documentation artifacts: " + ", ".join(missing),
            )
            continue
        if yaml is None:
            report.warn(
                f"component-{part}",
                "artifacts exist; PyYAML unavailable for config semantics",
            )
            continue
        try:
            config_texts = [
                repository_relative_text(
                    root,
                    component_snapshot,
                    relative,
                    label=f"{part} BMAD config {relative}",
                )
                for relative in config_relatives
            ]
            if any(text is None for text in config_texts):
                raise RuntimeError(f"{part} exact BMAD config blob is missing")
            core, bmm = (
                load_yaml_text(str(text), relative)
                for text, relative in zip(
                    config_texts, config_relatives, strict=True
                )
            )
            problems = []
            if not isinstance(core.get("project_name"), str) or not core.get(
                "project_name"
            ):
                problems.append(f"core project_name={core.get('project_name')!r}")
            if not isinstance(bmm.get("project_name"), str) or not bmm.get(
                "project_name"
            ):
                problems.append(f"bmm project_name={bmm.get('project_name')!r}")
            if bmm.get("project_knowledge") != "{project-root}/docs":
                problems.append(f"project_knowledge={bmm.get('project_knowledge')!r}")
            if problems:
                report.fail(
                    f"component-{part}",
                    "malformed or unresolved BMAD config: " + ", ".join(problems),
                )
            elif repository_regular_file_exists(
                root, component_snapshot, "_bmad/config.toml"
            ):
                canonical_text = repository_relative_text(
                    root,
                    component_snapshot,
                    "_bmad/config.toml",
                    label=f"{part} canonical BMAD config",
                )
                if canonical_text is None:
                    raise RuntimeError(f"{part} exact canonical config is missing")
                canonical = tomllib.loads(canonical_text)
                canonical_name = canonical.get("core", {}).get("project_name")
                if canonical_name != core.get("project_name"):
                    report.fail(
                        f"component-{part}",
                        f"canonical config project_name={canonical_name!r}; core YAML={core.get('project_name')!r}",
                    )
                else:
                    report.passed(
                        f"component-{part}",
                        "BMAD configs parse and root architecture/development docs exist",
                    )
            else:
                report.passed(
                    f"component-{part}",
                    "BMAD configs parse and root architecture/development docs exist",
                )
        except Exception as exc:
            report.fail(f"component-{part}", f"config parse failed: {exc}")


def check_platform_manifest(source: Path, report: Reporter) -> None:
    platform = source / "33god-platform"
    snapshot = git_snapshot(source)
    path_errors = canonical_platform_manifest_path_errors(source)
    if path_errors:
        report.fail("platform-manifests", "; ".join(path_errors))
        return
    component_paths = {
        part: platform / "components" / f"{part}.yaml"
        for part in LIFECYCLE_ACCEPTANCE_SLICE
    }
    if yaml is None:
        report.warn(
            "platform-manifests", "PyYAML unavailable; semantic parity was skipped"
        )
        return
    for part, path in component_paths.items():
        relative = f"33god-platform/components/{part}.yaml"
        if not repository_regular_file_exists(source, snapshot, relative):
            report.fail(f"platform-{part}", f"missing {path}")
            continue
        try:
            text = repository_relative_text(
                source,
                snapshot,
                relative,
                label=f"{part} platform manifest",
            )
            if text is None:
                raise RuntimeError("exact component manifest blob is missing")
            item = load_yaml_text(text, relative)
            declared = (platform / str(item["repo"])).resolve()
            expected = (source / part).resolve()
            if declared != expected:
                report.fail(
                    f"platform-{part}",
                    f"repo resolves to {declared}; expected {expected}",
                )
            else:
                report.passed(
                    f"platform-{part}", f"repo resolves to live {part} checkout"
                )
        except Exception as exc:
            report.fail(f"platform-{part}", f"manifest parse/parity failed: {exc}")

    pjangler_text = repository_relative_text(
        source,
        snapshot,
        "33god-platform/components/pjangler.yaml",
        label="pjangler platform manifest",
    ) or ""
    if "bun test" in pjangler_text:
        report.fail(
            "pjangler-health", "platform health uses Bun, but live project is npm-based"
        )
    elif "npm test" in pjangler_text:
        report.passed(
            "pjangler-health", "platform health uses canonical npm test command"
        )
    else:
        report.warn(
            "pjangler-health",
            "no recognized PJangler test command in platform manifest",
        )


def function_block(text: str, name: str) -> str:
    match = re.search(
        rf"^def {re.escape(name)}\([^\n]*\).*?(?=^def |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(0) if match else ""


def ecosystem_authority_errors(ecosystem_text: str) -> list[str]:
    errors: list[str] = []
    if not ecosystem_text:
        return ["skills/ecosystem/SKILL.md is missing"]

    for statement in ECOSYSTEM_AUTHORITY_CONTRACT:
        if statement not in ecosystem_text:
            errors.append(
                "skills/ecosystem/SKILL.md is missing ownership statement: " + statement
            )
    if re.search(
        r"(?im)^\|\s*Ticket lifecycle\s*\|\s*`project-lifecycle`",
        ecosystem_text,
    ):
        errors.append(
            "skills/ecosystem/SKILL.md ambiguously maps Ticket lifecycle to project-lifecycle"
        )
    for line_number, line in enumerate(ecosystem_text.splitlines(), start=1):
        if "project-lifecycle" not in line:
            continue
        if not re.search(
            r"(?i)(?:\bPlane\b|\btickets?\b|\bwork-items?\b|\bboard(?:/lane)?\b)",
            line,
        ):
            errors.append(
                "skills/ecosystem/SKILL.md line "
                f"{line_number} routes project-lifecycle without Plane ticket/board scope"
            )
    return errors


def bloodbank_api_contract_errors(api_text: str) -> list[str]:
    """Reject stale current-truth claims in the root Bloodbank API surface."""

    if not api_text:
        return ["docs/api-contracts-bloodbank.md is missing"]
    normalized = re.sub(r"\s+", " ", api_text)
    errors = [
        "docs/api-contracts-bloodbank.md is missing current statement: " + statement
        for statement in BLOODBANK_API_CURRENT_CONTRACT
        if statement not in normalized
    ]
    for label, pattern in BLOODBANK_API_STALE_PATTERNS.items():
        if pattern.search(normalized):
            errors.append(f"docs/api-contracts-bloodbank.md contains {label}")
    return errors


def authority_parity_text_errors(path: str, text: str) -> list[str]:
    """Reject current prose or manifest language that transfers authority."""

    paragraphs = [
        re.sub(r"\s+", " ", paragraph) for paragraph in re.split(r"\n\s*\n", text)
    ]
    errors = [
        f"{path} contains {label}"
        for label, pattern in AUTHORITY_PARITY_PATTERNS.items()
        if any(pattern.search(paragraph) for paragraph in paragraphs)
    ]
    normalized_path = path.casefold()
    if "holocene/" in normalized_path and re.search(
        r"(?i)\b33GOD\s+Control[-\s]+Plane\b", text
    ):
        errors.append(f"{path} contains standalone Holocene control-plane branding")
    if path in CURRENT_DEPLOYMENT_ARTIFACTS or normalized_path.startswith(
        ("source/lifecycle/", "lifecycle/")
    ):
        errors.extend(
            f"{path} contains {label}"
            for label, pattern in DEPLOYMENT_CEREMONY_PATTERNS.items()
            if pattern.search(text)
        )
    return errors


OPERATIONAL_COMPONENTS = (
    "bloodbank",
    "candybar",
    "candystore",
    "hermes-agent-template",
    "holocene",
    "lifecycle",
    "pjangler",
    "pipeline-mcp-hub",
    "toad",
)
OPERATIONAL_PATH_MARKERS = (
    "agents/hermes/",
    "/sentinel",
    "sentinel.",
    "scrum-master",
    "adapter",
    "runner",
    "mirror",
    "_bmad/",
    ".augment/",
    ".claude/commands/",
    ".gemini/commands/",
    ".opencode/command/",
)
OPERATIONAL_SCRIPT_SUFFIXES = (
    ".bash",
    ".cjs",
    ".fish",
    ".js",
    ".mjs",
    ".nu",
    ".ps1",
    ".py",
    ".rb",
    ".sh",
    ".ts",
    ".tsx",
    ".zsh",
)
OPERATIONAL_EXCLUDED_PARTS = (
    "archive",
    "archives",
    "docs",
    "examples",
    "fixtures",
    "test",
    "tests",
    "__pycache__",
)
PROVIDER_COMPLETION_PATTERNS = (
    re.compile(
        r"(?i)\b(?:tp|ticket[-_ ]?provider)\s+transition\b[^\n]{0,120}"
        r"\b(?:completed|started|done)\b"
    ),
    re.compile(r"(?i)\bmove\s+work\b[^\n]{0,80}\bstarted\b"),
    re.compile(
        r"(?i)\bautonom(?:ous|ously)\b[^\n]{0,120}\b(?:treat|treated|treats)\b"
        r"[^\n]{0,80}\b(?:done|completed)\b"
    ),
    re.compile(
        r"(?i)\b(?:ticket provider|provider board)\b.{0,120}"
        r"\b(?:authoritative|source of truth|SOT)\b"
    ),
    re.compile(r"(?i)\bunblocks?\s+dependents?\b"),
)
MOMO_HOLOCENE_COPY_ACTION = re.compile(
    r"(?i)\b(?:copy|copies|copied|replica|mirror|mirrored|byte[- ]identical|"
    r"store|stores|stored|persist|persists|persisted)\b"
)
MOMO_HOLOCENE_COORDINATOR = re.compile(
    r"\s*(?:(?:,\s*)?\b(and|or|nor|yet|then|while|whereas|although|though)\b|"
    r"(,))\s*",
    re.IGNORECASE,
)
MOMO_HOLOCENE_NEGATION_EXCEPTION = re.compile(
    r"(?:\b(?:not|[\w]+n't)\s+(?:only|merely|just)|"
    r"\b(?:not|never|cannot|[\w]+n't)\s+(?:not|never|without|[\w]+n't))\s*$",
    re.IGNORECASE,
)
MOMO_HOLOCENE_NEGATION_MARKER = re.compile(
    r"\b(?:never|neither|no|not|cannot|without|[\w]+n't|"
    r"prohibit(?:s|ed)?|forbid(?:s|den)?|bar(?:s|red)?|disallow(?:s|ed)?)\b",
    re.IGNORECASE,
)
MOMO_HOLOCENE_NEGATED_ACTION_PREFIX = re.compile(
    r"(?:"
    r"\b(?:never|neither|no|not|cannot)\b|"
    r"\b[\w]+n't\b|"
    r"\b(?:do|does|did|is|are|was|were|be|been|being|has|have|had|"
    r"will|would|shall|should|can|could|must|may|might)\s+not\b|"
    r"\bwithout(?:\s+(?:a|any|the))?"
    r")"
    r"(?:\s+(?:currently|ever|again|directly|indirectly|locally|remotely|"
    r"separately|also|otherwise|automatically|permanently|temporarily))*\s*$",
    re.IGNORECASE,
)
MOMO_HOLOCENE_DOUBLE_NEGATED_PROHIBITION = re.compile(
    r"\b(?:not|[\w]+n't)\s+(?:expressly\s+)?"
    r"(?:prohibit(?:s|ed)?|forbid(?:s|den)?|bar(?:s|red)?|disallow(?:s|ed)?)\b",
    re.IGNORECASE,
)
MOMO_HOLOCENE_PROHIBITION_PREFIX = re.compile(
    r"\b(?:prohibit(?:s|ed)?|forbid(?:s|den)?|bar(?:s|red)?|disallow(?:s|ed)?)\b"
    r"(?:\s+[\w-]+){0,5}\s*$",
    re.IGNORECASE,
)
MOMO_HOLOCENE_PASSIVE_NEGATION = re.compile(
    r"^\s+(?:(?:is|are|was|were|be|been|being|has|have|had|will|would|shall|"
    r"should|can|could|must)\s+(?:not|never)\b|"
    r"(?:is|are|was|were|has|have|had|will|would|shall|should|can|could|must)"
    r"n't\b)(?!\s+(?:only|merely|just)\b)",
    re.IGNORECASE,
)
MOMO_HOLOCENE_BARE_COPY_VERB = re.compile(
    r"^\s*(?:(?:then|also|ever|again|directly|indirectly)\s+){0,2}"
    r"(?:copy|copies|copied|mirror|mirrored|store|stores|stored|persist|"
    r"persists|persisted)\b",
    re.IGNORECASE,
)
MOMO_HOLOCENE_BARE_SHARED_AUX_VERB = re.compile(
    r"^\s*(?:(?:then|also|ever|again|directly|indirectly)\s+){0,2}"
    r"(?:copy|mirror|store|persist)\b",
    re.IGNORECASE,
)
MOMO_POLICY_APOSTROPHE_TRANSLATION = str.maketrans(
    {"‘": "'", "’": "'", "ʼ": "'", "＇": "'"}
)


def has_ticket_lifecycle_identity(value: str) -> bool:
    """Recognize one structural identity across canonical separator variants."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    structural = "".join(
        character
        if character.isalnum()
        else " "
        if unicodedata.category(character)[0] in {"C", "P", "S", "Z"}
        or character.isspace()
        else " "
        for character in normalized
    )
    tokens = tuple(structural.split())
    return "ticketlifecycle" in tokens or any(
        tokens[index : index + 2] == ("ticket", "lifecycle")
        for index in range(max(0, len(tokens) - 1))
    )


def exact_momo_policy_description(description: str) -> bool:
    """Accept only the normalized, independently scoped legal-work contract."""

    normalized = re.sub(
        r"\s+", " ", unicodedata.normalize("NFKC", description).casefold()
    ).strip()
    return bool(
        re.fullmatch(
            r"bounded lifecycle client for choosing and ranking only "
            r"lifecycle-legal work and executing only lifecycle-legal work\.?",
            normalized,
        )
    )


def momo_policy_coordination_units(clause: str) -> list[tuple[str, str | None]]:
    """Split predicate coordinators while retaining the preceding relationship."""

    units: list[tuple[str, str | None]] = []
    cursor = 0
    separator: str | None = None
    for boundary in MOMO_HOLOCENE_COORDINATOR.finditer(clause):
        unit = clause[cursor : boundary.start()]
        if unit.strip():
            units.append((unit, separator))
        separator = boundary.group(1).casefold() if boundary.group(1) else ","
        cursor = boundary.end()
    unit = clause[cursor:]
    if unit.strip():
        units.append((unit, separator))
    return units


def has_clear_holocene_copy_prohibition(
    unit: str, targets: list[re.Match[str]]
) -> bool:
    """Recognize only negation attached directly to one copy/storage predicate."""

    if len(MOMO_HOLOCENE_NEGATION_MARKER.findall(unit)) > 1:
        return False
    for target in targets:
        before = unit[: target.start()]
        if MOMO_HOLOCENE_NEGATION_EXCEPTION.search(before):
            continue
        if MOMO_HOLOCENE_NEGATED_ACTION_PREFIX.search(before):
            return True
        if (
            MOMO_HOLOCENE_PROHIBITION_PREFIX.search(before)
            and not MOMO_HOLOCENE_DOUBLE_NEGATED_PROHIBITION.search(before)
        ):
            return True
        if MOMO_HOLOCENE_PASSIVE_NEGATION.match(unit[target.end() :]):
            return True
    return False


def has_positive_holocene_copy_claim(text: str) -> bool:
    """Reject copy ownership claims while permitting an explicit prohibition."""

    normalized = unicodedata.normalize("NFKC", text).translate(
        MOMO_POLICY_APOSTROPHE_TRANSLATION
    )
    clauses = re.split(
        r"(?:[;:\n]|\s+[—–]\s+|(?<=[.!?])\s+|\bbut\b|\bhowever\b)",
        normalized,
        flags=re.IGNORECASE,
    )
    for clause in clauses:
        if not re.search(r"(?i)\bHolocene\b", clause):
            continue
        units = momo_policy_coordination_units(clause)
        action_units = [
            (unit, separator, list(MOMO_HOLOCENE_COPY_ACTION.finditer(unit)))
            for unit, separator in units
        ]
        scoped_action_units = {
            index
            for index, (unit, _separator, actions) in enumerate(action_units)
            if actions and re.search(r"(?i)\bHolocene\b", unit)
        }
        previous_negated_copy_predicate = False
        previous_wide_scope_negation = False
        for index, (unit, separator, actions) in enumerate(action_units):
            if not actions:
                previous_negated_copy_predicate = False
                previous_wide_scope_negation = False
                continue
            explicitly_prohibited = has_clear_holocene_copy_prohibition(unit, actions)
            bare_copy_verb = MOMO_HOLOCENE_BARE_COPY_VERB.search(unit)
            shared_aux_verb = MOMO_HOLOCENE_BARE_SHARED_AUX_VERB.search(unit)
            inherits_prohibition = (
                previous_negated_copy_predicate
                and bare_copy_verb is not None
                and (shared_aux_verb is not None or previous_wide_scope_negation)
                and (
                    separator in {"and", "or", "nor"}
                    or (separator == "," and not unit[bare_copy_verb.end() :].strip())
                )
            )
            if explicitly_prohibited or inherits_prohibition:
                previous_negated_copy_predicate = True
                previous_wide_scope_negation = (
                    previous_wide_scope_negation
                    if inherits_prohibition
                    else re.search(r"(?i)\b(?:never|neither)\b", unit) is not None
                )
                continue
            previous_negated_copy_predicate = False
            previous_wide_scope_negation = False
            if not scoped_action_units or index in scoped_action_units:
                return True
        if any(actions for _unit, _separator, actions in action_units):
            continue
        for unit, _separator in units:
            pairing = re.search(r"(?i)\bMomo\s*/\s*Holocene\b", unit)
            if pairing is not None and not has_clear_holocene_copy_prohibition(
                unit, [pairing]
            ):
                return True
    return False


def structured_identity_values(text: str, suffix: str, label: str) -> list[str]:
    """Return scalar registration fields from strict CSV or YAML input."""

    if suffix.casefold() == ".csv":
        try:
            values: list[str] = []
            for row in csv.reader(io.StringIO(text, newline=""), strict=True):
                state = _validation_state()
                if state is not None:
                    state.budget.consume("entries", len(row))
                values.extend(str(value) for value in row)
            return values
        except csv.Error as exc:
            raise RuntimeError(f"{label} contains malformed CSV") from exc
    if suffix.casefold() not in {".yaml", ".yml"}:
        raise RuntimeError(f"{label} is not a supported structured manifest")
    data = load_yaml_text(text, label)
    values: list[str] = []
    stack: list[Any] = [data]
    while stack:
        state = _validation_state()
        if state is not None:
            state.budget.check_time()
        value = stack.pop()
        if isinstance(value, dict):
            stack.extend(value.keys())
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
        elif value is not None:
            if state is not None:
                state.budget.consume("entries")
            values.append(str(value))
    return values


def _git_environment() -> dict[str, str]:
    return sanitized_git_environment()


def _run_git_process(
    repo: Path,
    *args: str,
    input_bytes: bytes | None = None,
    stdout_limit: int,
    stderr_limit: int,
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
            raise RuntimeError(
                f"Git command output exceeded its safe bound for {repo}: {operation}"
            ) from exc
        raise RuntimeError(
            f"Git command failed safely for {repo}: {operation}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"Git command failed safely for {repo}: {operation}"
        ) from exc
    if result.returncode not in allowed_returncodes:
        raise RuntimeError(f"Git command failed safely for {repo}: {operation}")
    return result


def run_git(
    repo: Path,
    *args: str,
    allowed_returncodes: frozenset[int] = frozenset({0}),
    pass_fds: tuple[int, ...] = (),
) -> subprocess.CompletedProcess[str]:
    raw = _run_git_process(
        repo,
        *args,
        stdout_limit=MAX_GIT_TEXT_OUTPUT_BYTES,
        stderr_limit=MAX_GIT_TEXT_OUTPUT_BYTES,
        allowed_returncodes=allowed_returncodes,
        pass_fds=pass_fds,
    )
    try:
        stdout = raw.stdout.decode("utf-8", errors="strict")
        stderr = raw.stderr.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise RuntimeError(
            f"Git command returned invalid text safely for {repo}: "
            f"{args[0] if args else 'git'}"
        ) from exc
    return subprocess.CompletedProcess(raw.args, raw.returncode, stdout, stderr)


def run_git_bytes(
    repo: Path,
    *args: str,
    input_bytes: bytes | None = None,
    max_output_bytes: int,
    allowed_returncodes: frozenset[int] = frozenset({0}),
    pass_fds: tuple[int, ...] = (),
) -> bytes:
    """Run bounded Git and return raw stdout without exposing stderr."""

    return _run_git_process(
        repo,
        *args,
        input_bytes=input_bytes,
        stdout_limit=max_output_bytes,
        stderr_limit=MAX_GIT_BATCH_OUTPUT_BYTES,
        allowed_returncodes=allowed_returncodes,
        pass_fds=pass_fds,
    ).stdout


def is_own_checkout(repo: Path) -> bool:
    key = _repository_key(repo)
    state = _validation_state()
    if state is not None and key in state.checkout_roots:
        return state.checkout_roots[key]
    if not repo.is_dir() or not (repo / ".git").exists():
        if state is not None:
            state.checkout_roots[key] = False
        return False
    result = run_git(repo, "rev-parse", "--show-toplevel")
    top_level = result.stdout.strip()
    if not top_level:
        raise RuntimeError(f"Git returned no checkout root for {repo}")
    own = Path(top_level).resolve() == repo.resolve()
    if state is not None:
        state.checkout_roots[key] = own
    return own


def checkout_revision(repo: Path) -> str | None:
    """Return HEAD only when ``repo`` is itself an initialized checkout."""

    key = _repository_key(repo)
    state = _validation_state()
    if state is not None and key in state.revisions:
        return state.revisions[key]
    if not is_own_checkout(repo):
        if state is not None:
            state.revisions[key] = None
        return None
    result = run_git(repo, "rev-parse", "HEAD")
    revision = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise RuntimeError(f"Git returned an invalid HEAD revision for {repo}")
    verify_commit_object_graph(repo, revision)
    if state is not None:
        state.revisions[key] = revision
    return revision


def verify_commit_object_graph(repo: Path, revision: str) -> None:
    """Require one exact commit and all of its reachable objects to be local."""

    try:
        verify_local_git_object_closure(
            repo,
            revision,
            lambda args, payload, limit, allowed: _run_git_process(
                repo,
                *args,
                input_bytes=payload,
                stdout_limit=limit,
                stderr_limit=limit,
                allowed_returncodes=allowed,
            ),
            max_objects=MAX_GIT_TREE_ENTRIES,
            max_output_bytes=MAX_GIT_TREE_OUTPUT_BYTES,
        )
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        raise RuntimeError(
            f"{repo}: exact Git tree references a missing or invalid blob/tree "
            "object, or uses non-local provenance"
        ) from exc


def _parse_git_tree_records(repo: Path, raw: bytes) -> list[tuple[str, str, str, str]]:
    """Parse canonical ``git ls-tree -rz`` records without trusting path bytes."""

    if len(raw) > MAX_GIT_TREE_OUTPUT_BYTES:
        raise RuntimeError(f"{repo}: exact Git tree exceeds its safe output bound")
    entries: list[tuple[str, str, str, str]] = []
    seen: set[str] = set()
    records = raw.split(b"\0")
    if records[-1:] != [b""]:
        raise RuntimeError(f"{repo}: malformed exact Git tree record stream")
    for record in records[:-1]:
        if len(entries) >= MAX_GIT_TREE_ENTRIES:
            raise RuntimeError(f"{repo}: exact Git tree exceeds its entry bound")
        state = _validation_state()
        if state is not None:
            state.budget.consume("entries")
        if b"\t" not in record:
            raise RuntimeError(f"{repo}: malformed exact Git tree record")
        metadata, raw_relative = record.split(b"\t", 1)
        fields = metadata.split(b" ")
        if len(fields) != 3 or any(not field for field in fields):
            raise RuntimeError(f"{repo}: malformed exact Git tree record")
        try:
            mode, object_type, object_id = (
                field.decode("ascii", errors="strict") for field in fields
            )
            relative = raw_relative.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise RuntimeError(f"{repo}: malformed exact Git tree data") from exc
        raw_parts = relative.split("/")
        relative_path = PurePosixPath(relative)
        if (
            not relative
            or len(raw_relative) > 4096
            or relative_path.is_absolute()
            or any(part in {"", ".", ".."} for part in raw_parts)
            or any(
                ord(character) < 32 or ord(character) == 127 for character in relative
            )
        ):
            raise RuntimeError(f"{repo}: malformed exact Git tree path")
        if mode not in VALID_GIT_TREE_MODES:
            raise RuntimeError(f"{repo}: exact Git tree contains an invalid mode")
        expected_type = "commit" if mode == "160000" else "blob"
        if object_type != expected_type or not FULL_GIT_REVISION.fullmatch(object_id):
            raise RuntimeError(
                f"{repo}: exact Git tree contains invalid object metadata"
            )
        if relative in seen:
            raise RuntimeError(f"{repo}: exact Git tree contains a duplicate path")
        seen.add(relative)
        entries.append((mode, object_type, object_id, relative))
    return entries


def _git_blob_sizes(repo: Path, object_ids: list[str]) -> dict[str, int]:
    unique_ids = list(dict.fromkeys(object_ids))
    if not unique_ids:
        return {}
    if len(unique_ids) > MAX_GIT_TREE_ENTRIES:
        raise RuntimeError(f"{repo}: exact Git tree exceeds its object bound")
    payload = b"".join(f"{object_id}\n".encode("ascii") for object_id in unique_ids)
    raw = run_git_bytes(
        repo,
        "cat-file",
        "--batch-check=%(objectname) %(objecttype) %(objectsize)",
        input_bytes=payload,
        max_output_bytes=MAX_GIT_BATCH_OUTPUT_BYTES,
    )
    lines = raw.splitlines()
    if len(lines) != len(unique_ids):
        raise RuntimeError(
            f"{repo}: exact Git blob verification returned malformed data"
        )
    sizes: dict[str, int] = {}
    for expected, line in zip(unique_ids, lines, strict=True):
        try:
            fields = line.decode("ascii", errors="strict").split(" ")
        except UnicodeError as exc:
            raise RuntimeError(
                f"{repo}: exact Git blob verification returned malformed data"
            ) from exc
        if (
            len(fields) != 3
            or fields[0] != expected
            or fields[1] != "blob"
            or not fields[2].isdigit()
        ):
            raise RuntimeError(
                f"{repo}: exact Git tree references a missing or invalid blob"
            )
        sizes[expected] = int(fields[2])
    return sizes


def repository_tree_entries(
    repo: Path, revision: str
) -> list[tuple[str, str, str, str, int | None]]:
    """Enumerate and verify every object reachable from one exact commit tree."""

    if not is_own_checkout(repo):
        return []
    if not FULL_GIT_REVISION.fullmatch(revision):
        raise RuntimeError(f"{repo}: invalid exact Git commit revision")
    verify_commit_object_graph(repo, revision)
    raw = run_git_bytes(
        repo,
        "ls-tree",
        "-r",
        "-z",
        "--full-tree",
        revision,
        max_output_bytes=MAX_GIT_TREE_OUTPUT_BYTES,
    )
    entries = _parse_git_tree_records(repo, raw)
    blob_sizes = _git_blob_sizes(
        repo,
        [
            object_id
            for mode, _kind, object_id, _relative in entries
            if mode != "160000"
        ],
    )
    return [
        (
            mode,
            object_type,
            object_id,
            relative,
            None if mode == "160000" else blob_sizes[object_id],
        )
        for mode, object_type, object_id, relative in entries
    ]


GitSnapshot = dict[str, tuple[str, str, int | None]]


def git_snapshot(repo: Path, revision: str | None = None) -> GitSnapshot | None:
    """Capture one verified commit tree, or signal an explicit non-Git fallback."""

    if not is_own_checkout(repo):
        return None
    exact_revision = checkout_revision(repo) if revision is None else revision
    if exact_revision is None:
        raise RuntimeError(f"{repo}: exact Git revision is unavailable")
    key = (_repository_key(repo), exact_revision)
    state = _validation_state()
    if state is not None and key in state.snapshots:
        return state.snapshots[key]
    snapshot = {
        relative: (mode, object_id, object_size)
        for mode, _kind, object_id, relative, object_size in repository_tree_entries(
            repo, exact_revision
        )
    }
    if state is not None:
        state.snapshots[key] = snapshot
    return snapshot


def snapshot_blob_bytes(
    repo: Path,
    snapshot: GitSnapshot,
    relative: str,
    *,
    label: str,
    max_bytes: int = MAX_OPERATIONAL_FILE_BYTES,
) -> bytes | None:
    entry = snapshot.get(relative)
    if entry is None:
        return None
    mode, object_id, object_size = entry
    if mode not in {"100644", "100755"} or object_size is None:
        raise RuntimeError(f"{label} is not a regular exact Git blob")
    if object_size > max_bytes:
        raise RuntimeError(f"{label} exceeds its safe size bound")
    blob = run_git_bytes(
        repo,
        "cat-file",
        "blob",
        object_id,
        max_output_bytes=max_bytes,
    )
    if len(blob) != object_size:
        raise RuntimeError(f"{label} exact Git blob size changed while reading")
    state = _validation_state()
    if state is not None:
        state.budget.consume("retained_bytes", len(blob))
    return blob


def bounded_filesystem_bytes(
    repo: Path,
    relative: str,
    *,
    label: str,
    max_bytes: int = MAX_OPERATIONAL_FILE_BYTES,
) -> bytes | None:
    """Strict non-Git fallback for tests and deliberately unpacked sources."""

    path = repo / Path(PurePosixPath(relative))
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink():
        raise RuntimeError(f"{label} symlink is not permitted")
    try:
        resolved = path.resolve(strict=True)
        repo_resolved = repo.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f"{label} cannot be resolved safely") from exc
    if not path_is_within(resolved, repo_resolved) or not path.is_file():
        raise RuntimeError(f"{label} is not a contained regular file")
    try:
        with path.open("rb") as handle:
            payload = handle.read(max_bytes + 1)
    except OSError as exc:
        raise RuntimeError(f"{label} cannot be read safely") from exc
    if len(payload) > max_bytes:
        raise RuntimeError(f"{label} exceeds its safe size bound")
    state = _validation_state()
    if state is not None:
        state.budget.consume("retained_bytes", len(payload))
    return payload


def repository_relative_bytes(
    repo: Path,
    snapshot: GitSnapshot | None,
    relative: str,
    *,
    label: str,
    max_bytes: int = MAX_OPERATIONAL_FILE_BYTES,
) -> bytes | None:
    if snapshot is not None:
        return snapshot_blob_bytes(
            repo, snapshot, relative, label=label, max_bytes=max_bytes
        )
    return bounded_filesystem_bytes(
        repo, relative, label=label, max_bytes=max_bytes
    )


def repository_relative_text(
    repo: Path,
    snapshot: GitSnapshot | None,
    relative: str,
    *,
    label: str,
    max_bytes: int = MAX_OPERATIONAL_FILE_BYTES,
) -> str | None:
    payload = repository_relative_bytes(
        repo, snapshot, relative, label=label, max_bytes=max_bytes
    )
    if payload is None:
        return None
    try:
        return payload.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise RuntimeError(f"{label} is not valid UTF-8") from exc


def repository_regular_file_exists(
    repo: Path, snapshot: GitSnapshot | None, relative: str
) -> bool:
    """Test file existence against the exact tree or an explicit fixture tree."""

    if snapshot is not None:
        entry = snapshot.get(relative)
        return entry is not None and entry[0] in {"100644", "100755"}
    path = repo / Path(PurePosixPath(relative))
    return path.is_file() and not path.is_symlink()


def repository_directory_exists(
    repo: Path, snapshot: GitSnapshot | None, relative: str
) -> bool:
    """Test directory existence without following fixture symlinks."""

    normalized = relative.rstrip("/") + "/"
    if snapshot is not None:
        return any(path.startswith(normalized) for path in snapshot)
    path = repo / Path(PurePosixPath(relative))
    return path.is_dir() and not path.is_symlink()


def repository_gitlinks(repo: Path, revision: str | None = None) -> dict[str, str]:
    snapshot = git_snapshot(repo, revision)
    if snapshot is None:
        return {}
    return {
        relative: object_id
        for relative, (mode, object_id, _size) in snapshot.items()
        if mode == "160000"
    }


def _filesystem_file_entries(repo: Path) -> list[tuple[Path, str]]:
    if not repo.is_dir():
        return []
    return [
        (
            path,
            "120000"
            if path.is_symlink()
            else "100755"
            if path.is_file() and path.stat().st_mode & 0o111
            else "100644",
        )
        for path in repo.rglob("*")
        if ".git" not in path.parts and (path.is_file() or path.is_symlink())
    ]


def repository_files(repo: Path) -> list[Path]:
    try:
        if is_own_checkout(repo):
            revision = checkout_revision(repo)
            if revision is None:
                raise RuntimeError(f"{repo}: exact Git revision is unavailable")
            return [
                repo / relative
                for mode, _kind, _object_id, relative, _size in repository_tree_entries(
                    repo, revision
                )
                if mode != "160000"
            ]
        return [path for path, _mode in _filesystem_file_entries(repo)]
    except RuntimeError as exc:
        raise RuntimeError(
            f"tracked-file enumeration failed for {repo}: {exc}"
        ) from exc


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def has_real_directory_chain(root: Path, checkout: Path) -> bool:
    """Require every lexical descendant component to be a real directory."""

    root_lexical = Path(os.path.abspath(root))
    checkout_lexical = Path(os.path.abspath(checkout))
    try:
        relative = checkout_lexical.relative_to(root_lexical)
    except ValueError:
        return False
    if not relative.parts:
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
    return True


def is_operational_path(relative: str) -> bool:
    normalized = "/" + relative.casefold().replace("\\", "/").lstrip("/")
    return any(marker in normalized for marker in OPERATIONAL_PATH_MARKERS)


def is_operational_candidate(relative: str, mode: str) -> bool:
    normalized = relative.casefold().replace("\\", "/")
    parts = tuple(part for part in normalized.split("/") if part)
    if any(part in OPERATIONAL_EXCLUDED_PARTS for part in parts):
        return False
    if mode == "100755" or normalized.endswith(OPERATIONAL_SCRIPT_SUFFIXES):
        return True
    name = parts[-1] if parts else ""
    return (
        is_operational_path(normalized)
        or "prompt" in name
        or "/commands/" in f"/{normalized}/"
        or "/command/" in f"/{normalized}/"
    )


def scan_operational_repository(
    source: Path,
    component: str,
    repo: Path,
    *,
    nested_label: str | None = None,
    tracked_prefix: str | None = None,
    revision: str | None = None,
) -> list[str]:
    del source
    errors: list[str] = []
    try:
        repo_is_checkout = is_own_checkout(repo)
        if repo_is_checkout:
            exact_revision = checkout_revision(repo) if revision is None else revision
            if exact_revision is None:
                raise RuntimeError(f"{repo}: exact Git revision is unavailable")
            tree_entries = repository_tree_entries(repo, exact_revision)
            filesystem_entries: list[tuple[Path, str]] = []
        else:
            tree_entries = []
            filesystem_entries = _filesystem_file_entries(repo)
    except RuntimeError as exc:
        return [f"{component}: tracked-file enumeration failed: {exc}"]

    for mode, _kind, object_id, relative_repo, object_size in tree_entries:
        if tracked_prefix is not None and relative_repo == tracked_prefix.rstrip("/"):
            if mode not in {"040000"}:
                errors.append(
                    f"{component}/{tracked_prefix.rstrip('/')} exact promoted prefix "
                    "is not a directory tree"
                )
            continue
        if mode == "160000":
            continue
        if tracked_prefix is not None:
            prefix = tracked_prefix.rstrip("/") + "/"
            if not relative_repo.startswith(prefix):
                continue
            display_relative = relative_repo.removeprefix(prefix)
        else:
            display_relative = relative_repo
        if not is_operational_candidate(display_relative, mode):
            continue
        display = f"{component}/{display_relative}"
        context = f"{nested_label}: " if nested_label else ""
        if mode == "120000":
            errors.append(
                f"{context}{display} is an operational symlink in the exact "
                "published tree; semantic absence cannot be proven"
            )
            continue
        if object_size is None:
            errors.append(f"{context}{display} has invalid exact Git blob metadata")
            continue
        if object_size > MAX_OPERATIONAL_FILE_BYTES:
            errors.append(
                f"{context}{display} is tracked but cannot be inspected: oversized"
            )
            continue
        try:
            blob = run_git_bytes(
                repo,
                "cat-file",
                "blob",
                object_id,
                max_output_bytes=MAX_OPERATIONAL_FILE_BYTES,
            )
        except RuntimeError as exc:
            errors.append(
                f"{context}{display} exact published blob cannot be inspected: {exc}"
            )
            continue
        if len(blob) != object_size:
            errors.append(
                f"{context}{display} exact published blob size changed while reading"
            )
            continue
        try:
            text = blob.decode("utf-8", errors="strict")
        except UnicodeError:
            errors.append(f"{context}{display} exact published blob is not valid UTF-8")
            continue
        if has_ticket_lifecycle_identity(display_relative) or (
            has_ticket_lifecycle_identity(text)
            and (
                "workflow" in display_relative.casefold()
                or "command" in display_relative.casefold()
            )
        ):
            errors.append(
                f"{context}{display} retains a non-Momo ticket-lifecycle "
                "operational surface"
            )
        if any(pattern.search(text) for pattern in PROVIDER_COMPLETION_PATTERNS):
            errors.append(
                f"{context}{display} retains a provider completion surface "
                "through an operational adapter/runner/sentinel"
            )

    for path, mode in filesystem_entries:
        try:
            relative_repo = path.relative_to(repo).as_posix()
        except ValueError:
            continue
        if tracked_prefix is not None:
            prefix = tracked_prefix.rstrip("/") + "/"
            if not relative_repo.startswith(prefix):
                continue
            display_relative = relative_repo.removeprefix(prefix)
        else:
            display_relative = relative_repo
        if not is_operational_candidate(display_relative, mode):
            continue
        display = f"{component}/{display_relative}"
        symlink = path.is_symlink()
        if symlink:
            try:
                resolved = path.resolve(strict=True)
                resolved_repo = repo.resolve()
            except (OSError, RuntimeError) as exc:
                errors.append(
                    f"{display} is an operational symlink that cannot be "
                    f"resolved safely: {exc}"
                )
                continue
            if not path_is_within(resolved, resolved_repo):
                errors.append(f"{display} is an operational symlink escaping its repo")
                continue
        if not path.exists() or not path.is_file():
            errors.append(f"{display} is tracked but cannot be inspected")
            continue
        try:
            if path.stat().st_size > MAX_OPERATIONAL_FILE_BYTES:
                errors.append(
                    f"{display} is tracked but cannot be inspected: oversized"
                )
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{display} is tracked but cannot be inspected: {exc}")
            continue
        context = f"{nested_label}: " if nested_label else ""
        qualifier = "symlink " if symlink else ""
        if has_ticket_lifecycle_identity(display_relative) or (
            has_ticket_lifecycle_identity(text)
            and (
                "workflow" in display_relative.casefold()
                or "command" in display_relative.casefold()
            )
        ):
            errors.append(
                f"{context}{display} retains a non-Momo ticket-lifecycle "
                f"{qualifier}operational surface"
            )
        if any(pattern.search(text) for pattern in PROVIDER_COMPLETION_PATTERNS):
            errors.append(
                f"{context}{display} retains a provider completion surface "
                f"through an operational {qualifier}adapter/runner/sentinel"
            )
    if tracked_prefix is not None and not tree_entries:
        prefix_path = repo / Path(PurePosixPath(tracked_prefix))
        if (prefix_path.exists() or prefix_path.is_symlink()) and (
            prefix_path.is_symlink() or not prefix_path.is_dir()
        ):
            errors.append(
                f"{component}/{tracked_prefix.rstrip('/')} promoted prefix "
                "is not a real directory"
            )
    return errors


def scan_gitlink_tree(
    component: str,
    repo: Path,
    expected_revision: str,
    *,
    depth: int = 0,
    seen: set[tuple[Path, str]] | None = None,
) -> list[str]:
    errors: list[str] = []
    if depth > MAX_GITLINK_DEPTH:
        return [
            f"{component} nested gitlink traversal exceeded depth {MAX_GITLINK_DEPTH}"
        ]
    if repo.is_symlink():
        return [
            f"{component} nested gitlink checkout is a symlink and cannot be trusted"
        ]
    if not (repo / ".git").exists():
        return [
            f"{component} has uninitialized nested gitlink at {expected_revision}; "
            "semantic absence cannot be proven"
        ]
    try:
        resolved = repo.resolve(strict=True)
    except (OSError, RuntimeError):
        return [
            f"{component} has uninitialized nested gitlink at {expected_revision}; "
            "semantic absence cannot be proven"
        ]
    seen = set() if seen is None else seen
    key = (resolved, expected_revision)
    if key in seen:
        return [f"{component} nested gitlink traversal cycle detected"]
    seen.add(key)
    try:
        actual = checkout_revision(repo)
    except RuntimeError as exc:
        seen.remove(key)
        return [f"{component} nested gitlink Git failure: {exc}"]
    if actual != expected_revision:
        seen.remove(key)
        return [
            f"{component} nested gitlink checkout={actual or 'unavailable'} "
            f"expected={expected_revision}"
        ]
    errors.extend(
        scan_operational_repository(
            repo.parent,
            component,
            repo,
            nested_label=f"{component} nested gitlink",
            revision=expected_revision,
        )
    )
    try:
        nested_gitlinks = repository_gitlinks(repo, expected_revision)
    except RuntimeError as exc:
        errors.append(f"{component} nested gitlink enumeration failed: {exc}")
        seen.remove(key)
        return errors
    repo_resolved = repo.resolve()
    repo_lexical = Path(os.path.abspath(repo))
    for relative, recorded in sorted(nested_gitlinks.items()):
        relative_path = Path(relative)
        nested = repo / relative_path
        lexical = Path(os.path.abspath(nested))
        if relative_path.is_absolute() or not path_is_within(lexical, repo_lexical):
            errors.append(
                f"{component} nested gitlink path {relative} escapes its repo"
            )
            continue
        try:
            nested_resolved = nested.resolve(strict=True)
        except (OSError, RuntimeError):
            errors.append(
                f"{component} has uninitialized nested gitlink {relative} at "
                f"{recorded}; semantic absence cannot be proven"
            )
            continue
        if (
            not has_real_directory_chain(repo, nested)
            or not path_is_within(nested_resolved, repo_resolved)
        ):
            errors.append(
                f"{component} nested gitlink {relative} has a symlink ancestor "
                "or escapes its repo"
            )
            continue
        errors.extend(
            scan_gitlink_tree(
                f"{component}/{relative}",
                nested,
                recorded,
                depth=depth + 1,
                seen=seen,
            )
        )
    seen.remove(key)
    return errors


def non_momo_operational_surface_errors(source: Path) -> list[str]:
    """Reject semantic lifecycle engines beyond named workflow directories."""

    errors: list[str] = []
    try:
        source_is_checkout = is_own_checkout(source)
    except RuntimeError as exc:
        return [f"selected source Git identity cannot be verified: {exc}"]
    if source_is_checkout:
        try:
            root_revision = checkout_revision(source)
            if root_revision is None:
                raise RuntimeError("selected source exact Git revision is unavailable")
            root_gitlinks = repository_gitlinks(source, root_revision)
        except RuntimeError as exc:
            return [f"root gitlink enumeration failed: {exc}"]
        for relative, recorded in sorted(root_gitlinks.items()):
            if relative == "momo":
                continue
            if not has_real_directory_chain(source, source / relative):
                errors.append(
                    f"{relative} nested gitlink checkout has a symlink ancestor "
                    "or is not a real directory"
                )
                continue
            errors.extend(scan_gitlink_tree(relative, source / relative, recorded))
        for component, tracked_prefix in (
            ("root/agents/hermes/pm", "agents/hermes/pm"),
            ("pipeline-mcp-hub", "pipeline-mcp-hub"),
        ):
            errors.extend(
                scan_operational_repository(
                    source,
                    component,
                    source,
                    tracked_prefix=tracked_prefix,
                    revision=root_revision,
                )
            )
        return sorted(set(errors))

    for component in OPERATIONAL_COMPONENTS:
        root = source / component
        if not root.is_dir():
            continue
        errors.extend(scan_operational_repository(source, component, root))
        try:
            nested_gitlinks = repository_gitlinks(root)
        except RuntimeError as exc:
            errors.append(f"{component} nested gitlink enumeration failed: {exc}")
            continue
        for relative, recorded in sorted(nested_gitlinks.items()):
            if not has_real_directory_chain(root, root / relative):
                errors.append(
                    f"{component}/{relative} nested gitlink checkout has a "
                    "symlink ancestor or is not a real directory"
                )
                continue
            errors.extend(
                scan_gitlink_tree(f"{component}/{relative}", root / relative, recorded)
            )
    return sorted(set(errors))


def canonical_workflow_files(
    workflow_root: Path,
    momo_root: Path,
    label: str,
    snapshot: GitSnapshot | None = None,
) -> tuple[set[Path], list[str]]:
    errors: list[str] = []
    if snapshot is not None:
        prefix = workflow_root.relative_to(momo_root).as_posix().rstrip("/") + "/"
        files: set[Path] = set()
        for relative, (mode, _object_id, _size) in snapshot.items():
            if not relative.startswith(prefix):
                continue
            child = relative.removeprefix(prefix)
            if not child:
                continue
            if mode == "120000":
                errors.append(
                    f"Momo {label} workflow symlink is not permitted: {child}"
                )
            elif mode == "160000":
                errors.append(
                    f"Momo {label} workflow nested gitlink is not permitted: {child}"
                )
            else:
                files.add(Path(PurePosixPath(child)))
        return files, errors
    if not workflow_root.exists() and not workflow_root.is_symlink():
        return set(), errors
    if workflow_root.is_symlink():
        return set(), [f"Momo {label} workflow symlink is not permitted"]
    try:
        root_resolved = workflow_root.resolve(strict=True)
        momo_resolved = momo_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        return set(), [f"Momo {label} workflow cannot be resolved safely: {exc}"]
    if not workflow_root.is_dir() or not path_is_within(root_resolved, momo_resolved):
        return set(), [f"Momo {label} workflow escapes the Momo checkout"]
    files: set[Path] = set()
    for path in workflow_root.rglob("*"):
        if path.is_symlink():
            errors.append(
                f"Momo {label} workflow symlink is not permitted: "
                f"{path.relative_to(workflow_root).as_posix()}"
            )
            continue
        try:
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            errors.append(
                f"Momo {label} workflow path cannot be resolved safely: {exc}"
            )
            continue
        if not path_is_within(resolved, root_resolved):
            errors.append(f"Momo {label} workflow path escapes its canonical root")
            continue
        if path.is_file():
            files.add(path.relative_to(workflow_root))
    return files, errors


def strict_csv_rows(
    path: Path,
    expected_headers: tuple[str, ...],
    label: str,
    containment_root: Path,
    snapshot: GitSnapshot | None = None,
) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    rows: list[dict[str, str]] = []
    try:
        if snapshot is not None:
            relative = path.relative_to(containment_root).as_posix()
            text = repository_relative_text(
                containment_root,
                snapshot,
                relative,
                label=f"Momo {label} CSV",
            )
            if text is None:
                return [], errors
            handle: Any = io.StringIO(text, newline="")
        else:
            if not path.exists() and not path.is_symlink():
                return [], errors
            if path.is_symlink():
                return [], [f"Momo {label} CSV symlink is not permitted"]
            resolved = path.resolve(strict=True)
            root_resolved = containment_root.resolve(strict=True)
            if not path_is_within(resolved, root_resolved):
                return [], [f"Momo {label} CSV escapes the Momo checkout"]
            handle = path.open(encoding="utf-8", errors="strict", newline="")
        with handle:
            reader = csv.DictReader(handle, strict=True)
            headers = tuple(reader.fieldnames or ())
            if headers != expected_headers or len(headers) != len(set(headers)):
                errors.append(
                    f"Momo {label} CSV schema must be exactly {expected_headers}"
                )
                return rows, errors
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    errors.append(f"Momo {label} contains a malformed CSV row")
                    continue
                rows.append({str(key): str(value) for key, value in row.items()})
    except (OSError, RuntimeError, UnicodeError, csv.Error) as exc:
        errors.append(f"Momo malformed {label} CSV: {exc}")
    return rows, errors


def ticket_lifecycle_surface_errors(source: Path) -> list[str]:
    """Allow only Momo's canonical ticket-lifecycle client workflow."""

    errors: list[str] = non_momo_operational_surface_errors(source)
    workflow_roots = (
        Path("_bmad/custom/workflows/ticket-lifecycle"),
        Path("_bmad/_config/custom/custom/workflows/ticket-lifecycle"),
    )
    manifest_paths = (
        Path("_bmad/_config/workflow-manifest.csv"),
        Path("_bmad/_config/files-manifest.csv"),
    )
    non_momo_roots = {
        "bloodbank": source / "bloodbank",
        "candystore": source / "candystore",
        "holocene": source / "holocene",
        "pjangler": source / "pjangler",
        "pjangler/templates/commonproject": (
            source / "pjangler/templates/commonproject"
        ),
    }
    for component, root in non_momo_roots.items():
        try:
            snapshot = git_snapshot(root)
        except RuntimeError as exc:
            errors.append(f"{component} exact Git tree cannot be inspected: {exc}")
            continue
        for relative in workflow_roots:
            prefix = relative.as_posix().rstrip("/") + "/"
            if snapshot is not None:
                present = any(path.startswith(prefix) for path in snapshot)
            else:
                path = root / relative
                present = path.is_dir() and any(
                    candidate.is_file() for candidate in path.rglob("*")
                )
            if present:
                errors.append(
                    f"{component} retains non-Momo ticket-lifecycle workflow at {relative}"
                )
        structured_manifests = {relative.as_posix() for relative in manifest_paths}
        if snapshot is not None:
            structured_manifests.update(
                relative
                for relative in snapshot
                if relative.startswith("_bmad/")
                and "manifest" in PurePosixPath(relative).name.casefold()
                and PurePosixPath(relative).suffix.casefold()
                in {".csv", ".yaml", ".yml"}
            )
        else:
            config_root = root / "_bmad"
            if config_root.is_dir() and not config_root.is_symlink():
                structured_manifests.update(
                    path.relative_to(root).as_posix()
                    for path in config_root.rglob("*")
                    if path.is_file()
                    and not path.is_symlink()
                    and "manifest" in path.name.casefold()
                    and path.suffix.casefold() in {".csv", ".yaml", ".yml"}
                )
        for relative_text in sorted(structured_manifests):
            relative = Path(PurePosixPath(relative_text))
            try:
                text = repository_relative_text(
                    root,
                    snapshot,
                    relative_text,
                    label=f"{component} {relative_text}",
                )
                values = (
                    []
                    if text is None
                    else structured_identity_values(
                        text, relative.suffix, f"{component} {relative_text}"
                    )
                )
            except RuntimeError as exc:
                errors.append(
                    f"{component} workflow registration cannot be inspected: {exc}"
                )
                continue
            if any(has_ticket_lifecycle_identity(value) for value in values):
                errors.append(
                    f"{component} registers non-Momo ticket-lifecycle workflow in {relative}"
                )
        for relative in TICKET_LIFECYCLE_COMMAND_SURFACES:
            if snapshot is not None:
                present = relative.as_posix() in snapshot
            else:
                present = (root / relative).is_file()
            if present:
                errors.append(
                    f"{component} retains non-Momo ticket-lifecycle command surface at {relative}"
                )

    momo = source / "momo"
    if momo.is_symlink():
        return [*errors, "Momo checkout symlink is not permitted"]
    if not momo.is_dir():
        return [*errors, "Momo checkout is missing"]
    try:
        momo_snapshot = git_snapshot(momo)
    except RuntimeError as exc:
        return [*errors, f"Momo exact Git tree cannot be inspected: {exc}"]
    source_workflow = momo / workflow_roots[0]
    mirror_workflow = momo / workflow_roots[1]
    source_files, source_file_errors = canonical_workflow_files(
        source_workflow, momo, "canonical source", momo_snapshot
    )
    mirror_files, mirror_file_errors = canonical_workflow_files(
        mirror_workflow, momo, "canonical mirror", momo_snapshot
    )
    errors.extend(source_file_errors)
    errors.extend(mirror_file_errors)
    if not source_files or source_files != mirror_files:
        errors.append("Momo canonical ticket-lifecycle source/mirror file sets differ")
    mismatched_files: list[str] = []
    source_texts: dict[Path, str] = {}
    for relative in sorted(source_files & mirror_files):
        source_relative = f"{workflow_roots[0].as_posix()}/{relative.as_posix()}"
        mirror_relative = f"{workflow_roots[1].as_posix()}/{relative.as_posix()}"
        try:
            source_bytes = repository_relative_bytes(
                momo,
                momo_snapshot,
                source_relative,
                label=f"Momo canonical source {relative.as_posix()}",
            )
            mirror_bytes = repository_relative_bytes(
                momo,
                momo_snapshot,
                mirror_relative,
                label=f"Momo canonical mirror {relative.as_posix()}",
            )
            if source_bytes is None or mirror_bytes is None:
                raise RuntimeError("exact canonical workflow blob is missing")
        except RuntimeError as exc:
            errors.append(
                "Momo canonical ticket-lifecycle workflow file cannot be read: "
                f"{relative.as_posix()}: {exc}"
            )
            continue
        for label, payload in (("source", source_bytes), ("mirror", mirror_bytes)):
            try:
                decoded = payload.decode("utf-8", errors="strict")
            except UnicodeError:
                errors.append(
                    "Momo canonical ticket-lifecycle "
                    f"{label} is not valid UTF-8: {relative.as_posix()}"
                )
            else:
                if label == "source":
                    source_texts[relative] = decoded
        if source_bytes != mirror_bytes:
            mismatched_files.append(relative.as_posix())
    if mismatched_files:
        errors.append(
            "Momo canonical ticket-lifecycle source/mirror bytes differ: "
            + ", ".join(mismatched_files)
        )
    if any(path.suffix == ".bak" for path in source_files | mirror_files):
        errors.append("Momo canonical ticket-lifecycle workflow retains .bak residue")

    for relative, text in sorted(source_texts.items()):
        if has_positive_holocene_copy_claim(text):
            errors.append(
                "Momo canonical ticket-lifecycle workflow contains Holocene copy "
                f"claim in {relative.as_posix()}"
            )

    workflow_manifest = momo / manifest_paths[0]
    workflow_manifest_rows, workflow_manifest_errors = strict_csv_rows(
        workflow_manifest,
        ("name", "description", "module", "path"),
        "workflow-manifest",
        momo,
        momo_snapshot,
    )
    errors.extend(workflow_manifest_errors)
    workflow_rows = [
        row
        for row in workflow_manifest_rows
        if any(
            has_ticket_lifecycle_identity(str(value)) for value in row.values()
        )
    ]
    if len(workflow_rows) != 1:
        errors.append(
            "Momo must register exactly one canonical ticket-lifecycle workflow"
        )
    else:
        row = workflow_rows[0]
        description = row.get("description", "")
        metadata_valid = (
            row.get("name") == "ticket-lifecycle"
            and row.get("module") == "custom"
            and row.get("path") == "_bmad/custom/workflows/ticket-lifecycle/workflow.md"
            and exact_momo_policy_description(description)
        )
        if not metadata_valid:
            errors.append(
                "Momo workflow-manifest lacks bounded Lifecycle client metadata"
            )

    files_manifest = momo / manifest_paths[1]
    files_manifest_rows, files_manifest_errors = strict_csv_rows(
        files_manifest,
        ("type", "name", "module", "path", "hash"),
        "files-manifest",
        momo,
        momo_snapshot,
    )
    errors.extend(files_manifest_errors)
    file_rows = [
        row
        for row in files_manifest_rows
        if has_ticket_lifecycle_identity(row.get("path", ""))
    ]
    expected_manifest_paths = {
        f"custom/workflows/ticket-lifecycle/{relative.as_posix()}"
        for relative in source_files
    }
    actual_manifest_paths = [row.get("path", "") for row in file_rows]
    if (
        len(file_rows) != len(source_files)
        or set(actual_manifest_paths) != expected_manifest_paths
        or len(actual_manifest_paths) != len(set(actual_manifest_paths))
    ):
        errors.append(
            "Momo ticket-lifecycle files-manifest paths differ from canonical source"
        )
    for row in file_rows:
        relative_path = row.get("path", "")
        if relative_path not in expected_manifest_paths:
            continue
        try:
            payload = repository_relative_bytes(
                momo,
                momo_snapshot,
                f"_bmad/{relative_path}",
                label=f"Momo files-manifest source {relative_path}",
            )
            if payload is None:
                raise RuntimeError("exact source blob is missing")
            expected_hash = hashlib.sha256(payload).hexdigest()
        except RuntimeError as exc:
            errors.append(
                "Momo ticket-lifecycle files-manifest source cannot be read for "
                f"{relative_path}: {exc}"
            )
            continue
        if row.get("hash") != expected_hash:
            errors.append(
                f"Momo ticket-lifecycle files-manifest hash differs for {relative_path}"
            )
    return errors


def bloodbank_live_inventory_errors(source: Path) -> list[str]:
    """Reject a live Bloodbank lifecycle-controller service or README inventory row."""

    errors: list[str] = []
    bloodbank = source / "bloodbank"
    try:
        snapshot = git_snapshot(bloodbank)
    except RuntimeError as exc:
        return [f"Bloodbank exact Git tree cannot be inspected: {exc}"]
    if snapshot is not None:
        controller_present = any(
            relative == "services/lifecycle-controller"
            or relative.startswith("services/lifecycle-controller/")
            for relative in snapshot
        )
    else:
        controller_present = (bloodbank / "services/lifecycle-controller").exists()
    if controller_present:
        errors.append("Bloodbank retains executable services/lifecycle-controller")
    try:
        readme_text = repository_relative_text(
            bloodbank,
            snapshot,
            "README.md",
            label="Bloodbank README",
        ) or ""
    except RuntimeError as exc:
        errors.append(f"Bloodbank README cannot be inspected safely: {exc}")
        readme_text = ""
    for line in readme_text.splitlines():
        if "`services/`" in line and re.search(r"(?i)lifecycle[- ]controller", line):
            errors.append("Bloodbank README lists a live lifecycle controller service")
    return errors


CURRENT_TOPOLOGY_TEXT_ARTIFACTS = (
    "PRD.md",
    "33god-platform/README.md",
    "docs/deployment-guide.md",
    "docs/source-tree-analysis.md",
    "docs/project-overview.md",
    "docs/index.md",
    "mise.toml",
)
STALE_TOPOLOGY_PATTERN = re.compile(
    r"(?i)\b(?:exact\s+)?four[- ]part\b|"
    r"\bfour\s+independently\s+versioned\s+component\b|"
    r"\bfour\s+component\s+(?:roots?|trees?|knowledge)\b"
)
RETIRED_ARCHITECTURE_INPUT = re.compile(
    r"(?im)^\s*-\s+(?:holocene/_bmad/custom/workflows/ticket-lifecycle/|"
    r"bloodbank/services/lifecycle-controller/)"
)
CURRENT_BLOODBANK_CONTROLLER_HOSTING = re.compile(
    r"(?i)\bBloodbank\b.{0,100}\bhosting\b.{0,80}"
    r"\bcurrent\s+(?:lifecycle[- ]?)?controller(?:\s+embryo)?\b"
)


def root_current_guidance_errors(docs_checkout: Path) -> list[str]:
    """Reject root guidance that revives removed authority or stale topology."""

    errors: list[str] = []
    try:
        snapshot = git_snapshot(docs_checkout)
    except RuntimeError as exc:
        return [f"root current guidance exact Git tree cannot be inspected: {exc}"]

    def current_text(relative: str) -> str:
        try:
            return (
                repository_relative_text(
                    docs_checkout,
                    snapshot,
                    relative,
                    label=f"root current guidance {relative}",
                )
                or ""
            )
        except RuntimeError as exc:
            errors.append(f"{relative} cannot be inspected safely: {exc}")
            return ""

    for relative in (
        "docs/development-guide-bloodbank.md",
        "docs/component-inventory-bloodbank.md",
    ):
        text = current_text(relative)
        if re.search(r"(?i)(?:bloodbank/)?services/lifecycle-controller", text):
            errors.append(
                f"{relative} contains current Bloodbank guidance to the removed "
                "lifecycle-controller"
            )

    architecture_text = current_text(
        "_bmad-output/planning-artifacts/architecture.md"
    )
    if RETIRED_ARCHITECTURE_INPUT.search(architecture_text):
        errors.append(
            "_bmad-output/planning-artifacts/architecture.md contains retired "
            "architecture input paths"
        )
    if CURRENT_BLOODBANK_CONTROLLER_HOSTING.search(architecture_text):
        errors.append(
            "_bmad-output/planning-artifacts/architecture.md contains current "
            "controller hosting language for Bloodbank"
        )

    for relative in CURRENT_TOPOLOGY_TEXT_ARTIFACTS:
        text = current_text(relative)
        if STALE_TOPOLOGY_PATTERN.search(text):
            errors.append(f"{relative} retains obsolete four-part topology guidance")
    return errors


def check_high_risk_contracts(source: Path, report: Reporter) -> None:
    snapshots = {
        component: git_snapshot(source / component)
        for component in ("bloodbank", "candystore", "holocene", "pjangler")
    }

    def component_text(component: str, relative: str) -> str:
        return repository_relative_text(
            source / component,
            snapshots[component],
            relative,
            label=f"{component} high-risk contract {relative}",
        ) or ""

    text = component_text("bloodbank", "services/agent-hooks/core/validate.py")
    block = function_block(text, "assert_contract")
    if "assert_subject_matches(" in block:
        report.passed(
            "bloodbank-subject-binding",
            "runtime contract invokes semantic subject/type equality",
        )
    else:
        report.fail(
            "bloodbank-subject-binding",
            "assert_contract does not invoke assert_subject_matches",
        )

    compose_text = component_text("bloodbank", "compose/docker-compose.yml")
    if "services/heartbeat-recorder" in compose_text and not repository_directory_exists(
        source / "bloodbank",
        snapshots["bloodbank"],
        "services/heartbeat-recorder",
    ):
        report.fail(
            "bloodbank-heartbeat",
            "Compose references missing services/heartbeat-recorder",
        )
    else:
        report.passed(
            "bloodbank-heartbeat", "heartbeat build context is internally consistent"
        )

    candy_text = component_text("candystore", "compose.yml")
    candy_pubsub_text = component_text(
        "candystore", "dapr-components/pubsub.yaml"
    )
    if "MUTUAL EXCLUSION" in candy_text and "candystore-events" in candy_pubsub_text:
        report.passed(
            "candystore-deployment-mode",
            "standalone manifest declares legacy-profile mutual exclusion",
        )
    else:
        report.fail(
            "candystore-deployment-mode",
            "mutual-exclusion declaration or durable identity is missing",
        )

    fleet_text = component_text("holocene", "apps/api/src/fleet.ts")
    if '"http://candystore:8080"' in fleet_text:
        report.fail(
            "holocene-candystore-url",
            "default URL contradicts standalone Candystore port/topology",
        )
    else:
        report.passed(
            "holocene-candystore-url",
            "default history URL no longer uses candystore:8080",
        )

    consumer_text = component_text(
        "pjangler", "templates/hermes-agent/runtime-scaffold/bloodbank-consumer.py"
    )
    noncanonical = re.search(
        r"bloodbank\.(?:evt\.v1\.repo|cmd\.v1\.agent)\."
        r"(?:\{(?:REPO|AGENT_ID)\}|\{\{[^}]+\}\}|<(?:repo|agent_id)>)",
        consumer_text,
    )
    if noncanonical:
        report.fail(
            "pjangler-bloodbank-routing",
            "generated subjects embed repo/agent routing identifiers",
        )
    else:
        report.passed(
            "pjangler-bloodbank-routing",
            "generated subjects follow fixed six-token routing",
        )


def component_manifest_pin_errors(
    platform_root: Path,
    pins: dict[str, tuple[str, str]],
    *,
    checkout_root: Path | None = None,
    snapshot: GitSnapshot | None = None,
) -> list[str]:
    """Validate revision fields structurally; unrelated text never satisfies a pin."""

    errors: list[str] = []
    for name, (expected_field, expected_revision) in pins.items():
        manifest = platform_root / "components" / f"{name}.yaml"
        try:
            if snapshot is None:
                data = load_yaml(manifest)
            else:
                if checkout_root is None:
                    raise RuntimeError("exact manifest checkout root is missing")
                relative = manifest.relative_to(checkout_root).as_posix()
                text = repository_relative_text(
                    checkout_root,
                    snapshot,
                    relative,
                    label=f"{name} component manifest",
                )
                if text is None:
                    raise RuntimeError("exact component manifest blob is missing")
                data = load_yaml_text(text, relative)
        except (OSError, RuntimeError, ValueError) as exc:
            errors.append(f"{name} component manifest cannot be parsed safely: {exc}")
            continue
        if data.get(expected_field) != expected_revision:
            errors.append(
                f"{name} component manifest {expected_field} does not pin "
                f"{expected_revision}"
            )
        other_field = (
            "gitlink_revision"
            if expected_field == "source_revision"
            else "source_revision"
        )
        if other_field in data:
            errors.append(
                f"{name} component manifest has conflicting revision semantics: "
                f"unexpected {other_field}"
            )
    return errors


def check_compose_candidate(
    source: Path, docs_checkout: Path, report: Reporter
) -> None:
    try:
        snapshot = git_snapshot(docs_checkout)
        if snapshot is None:
            raise RuntimeError("candidate root must be an explicit Git checkout")
        validator_bytes = snapshot_blob_bytes(
            docs_checkout,
            snapshot,
            "33god-platform/scripts/validate-compose.py",
            label="committed candidate Compose validator",
        )
        compose_bytes = snapshot_blob_bytes(
            docs_checkout,
            snapshot,
            "33god-platform/compose.yaml",
            label="committed candidate Compose model",
        )
    except RuntimeError:
        report.fail("root-compose", "candidate Compose validator or model is missing")
        return
    if validator_bytes is None or compose_bytes is None:
        report.fail("root-compose", "candidate Compose validator or model is missing")
        return
    try:
        with tempfile.TemporaryDirectory(prefix="33god-compose-candidate-") as temporary:
            platform = Path(temporary) / "33god-platform"
            scripts = platform / "scripts"
            scripts.mkdir(parents=True, mode=0o700)
            validator = scripts / "validate-compose.py"
            compose = platform / "compose.yaml"
            validator.write_bytes(validator_bytes)
            compose.write_bytes(compose_bytes)
            validator.chmod(0o500)
            compose.chmod(0o400)
            environment = sanitized_command_environment()
            home = Path(temporary) / "home"
            home.mkdir(mode=0o700)
            environment["HOME"] = str(home)
            state = _validation_state()
            timeout = (
                state.budget.remaining_seconds(GIT_TIMEOUT_SECONDS)
                if state is not None
                else GIT_TIMEOUT_SECONDS
            )
            result = _run_bounded_process(
                [
                    sys.executable,
                    str(validator),
                    "--compose-file",
                    str(compose),
                    "--source-root",
                    str(source),
                ],
                stdout_limit=MAX_GIT_TEXT_OUTPUT_BYTES,
                stderr_limit=MAX_GIT_TEXT_OUTPUT_BYTES,
                timeout=timeout,
                env=environment,
                cwd=platform,
            )
    except (_BoundedProcessError, OSError, UnicodeError, ValueError):
        report.fail("root-compose", "candidate validator failed safely")
        return
    current_truth_errors = lifecycle_current_truth_errors(source, docs_checkout)
    if result.returncode or current_truth_errors:
        reasons = (
            [f"candidate validator exited {result.returncode}"]
            if result.returncode
            else []
        )
        reasons.extend(current_truth_errors)
        report.fail(
            "root-compose",
            "; ".join(reasons) or "candidate validator failed safely",
        )
    else:
        report.passed(
            "root-compose",
            "committed validator and Compose model passed; exact lifecycle digest, "
            "component revisions, ownership text, "
            "authority-parity workflow surfaces, and promoted Momo structural "
            "prerequisites are current; native/live execution is a separate gate",
        )


def lifecycle_current_truth_errors(source: Path, docs_checkout: Path) -> list[str]:
    errors: list[str] = []
    platform = docs_checkout / "33god-platform"
    try:
        docs_snapshot = git_snapshot(docs_checkout)
        compose_text = repository_relative_text(
            docs_checkout,
            docs_snapshot,
            "33god-platform/compose.yaml",
            label="root Compose",
        )
        if compose_text is None:
            raise RuntimeError("exact Compose blob is missing")
    except (OSError, RuntimeError) as exc:
        return [f"Compose cannot be read safely: {exc}"]
    if compose_text.count(LIFECYCLE_IMAGE) != 1:
        errors.append(
            "Compose must define exactly one exact-digest Lifecycle image anchor"
        )
    for service in ("lifecycle-migrate", "lifecycle-bootstrap", "lifecycle"):
        block = re.search(
            rf"(?ms)^  {re.escape(service)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
            compose_text,
        )
        if (
            block is None
            or "image: *lifecycle-image" not in block.group("body")
            or re.search(r"(?m)^    build:", block.group("body"))
        ):
            errors.append(
                f"Lifecycle Compose service {service} is missing, unpinned, or defines build"
            )

    try:
        root_gitlinks = repository_gitlinks(source)
    except RuntimeError as exc:
        errors.append(f"root gitlink enumeration failed: {exc}")
        root_gitlinks = {}
    manifest_pins = {
        name: (
            "gitlink_revision" if name == "lifecycle" else "source_revision",
            expected,
        )
        for name, expected in COMPONENT_REVISIONS.items()
    }
    errors.extend(
        component_manifest_pin_errors(
            platform,
            manifest_pins,
            checkout_root=docs_checkout,
            snapshot=docs_snapshot,
        )
    )
    for name, expected in COMPONENT_REVISIONS.items():
        try:
            actual = checkout_revision(source / name)
        except RuntimeError as exc:
            errors.append(f"{name} checkout Git failure: {exc}")
            actual = None
        if actual != expected:
            errors.append(
                f"{name} checkout={actual or 'unavailable'} expected={expected}"
            )
        index_revision = root_gitlinks.get(name, "")
        if index_revision != expected:
            errors.append(
                f"root gitlink {name}={index_revision or 'unavailable'} expected={expected}"
            )

    commonproject = source / "pjangler/templates/commonproject"
    try:
        commonproject_actual = checkout_revision(commonproject)
    except RuntimeError as exc:
        errors.append(f"CommonProject checkout Git failure: {exc}")
        commonproject_actual = None
    if commonproject_actual != COMMONPROJECT_REVISION:
        errors.append(
            "CommonProject checkout="
            f"{commonproject_actual or 'unavailable'} expected={COMMONPROJECT_REVISION}"
        )
    try:
        commonproject_pin = repository_gitlinks(source / "pjangler").get(
            "templates/commonproject", ""
        )
    except RuntimeError as exc:
        errors.append(f"PJangler nested gitlink enumeration failed: {exc}")
        commonproject_pin = ""
    if commonproject_pin != COMMONPROJECT_REVISION:
        errors.append(
            "PJangler CommonProject gitlink="
            f"{commonproject_pin or 'unavailable'} expected={COMMONPROJECT_REVISION}"
        )
    try:
        pjangler_text = repository_relative_text(
            docs_checkout,
            docs_snapshot,
            "33god-platform/components/pjangler.yaml",
            label="pjangler component manifest",
        )
        if pjangler_text is None:
            raise RuntimeError("exact pjangler manifest blob is missing")
        pjangler_manifest = load_yaml_text(
            pjangler_text, "33god-platform/components/pjangler.yaml"
        )
    except (OSError, RuntimeError, ValueError) as exc:
        errors.append(f"pjangler component manifest cannot be parsed safely: {exc}")
        pjangler_manifest = {}
    if pjangler_manifest.get("commonproject_revision") != COMMONPROJECT_REVISION:
        errors.append(
            "pjangler component manifest does not pin CommonProject "
            f"{COMMONPROJECT_REVISION}"
        )

    try:
        lifecycle_text = repository_relative_text(
            docs_checkout,
            docs_snapshot,
            "33god-platform/components/lifecycle.yaml",
            label="Lifecycle component manifest",
        )
        if lifecycle_text is None:
            raise RuntimeError("exact Lifecycle manifest blob is missing")
        lifecycle_manifest = load_yaml_text(
            lifecycle_text, "33god-platform/components/lifecycle.yaml"
        )
    except (OSError, RuntimeError, ValueError) as exc:
        errors.append(f"Lifecycle component manifest cannot be parsed safely: {exc}")
        lifecycle_manifest = {}
    expected_lifecycle_pins = {
        "image_source_revision": COMPONENT_REVISIONS["lifecycle"],
        "image_tag": LIFECYCLE_TAG,
        "image": LIFECYCLE_IMAGE,
    }
    for field, expected in expected_lifecycle_pins.items():
        if lifecycle_manifest.get(field) != expected:
            errors.append(
                f"Lifecycle component manifest {field} does not pin {expected}"
            )

    ownership_patterns = {
        "Momo lifecycle authority": re.compile(
            r"(?i)\bMomo\s+(?:owns|calculates|persists|writes|drives)\s+(?:the\s+)?lifecycle"
        ),
        "Holocene lifecycle authority": re.compile(
            r"(?i)\bHolocene\s+(?:owns|derives|persists|writes|calculates)\s+(?:the\s+)?lifecycle"
        ),
        "Bloodbank lifecycle semantics": re.compile(
            r"(?i)\bBloodbank\s+owns\s+(?:deterministic\s+)?lifecycle\s+(?:semantics|state|truth)"
        ),
        "Candystore lifecycle writes": re.compile(
            r"(?i)\bCandystore\s+(?:owns|performs|accepts)\s+(?:operational\s+)?lifecycle\s+writes"
        ),
        "Plane lifecycle authority": re.compile(
            r"(?i)\bPlane\s+(?:owns|evaluates|writes|calculates|persists|drives)\s+"
            r"(?:(?:the|deterministic|operational)\s+)?(?:project[- ]?)?lifecycle"
        ),
        "forward-plan bureaucracy": re.compile(
            r"(?i)\b(?:rollback plan|safety valve|safety procedure|stakeholder gate|approval[- ]gate)\b"
        ),
        "stale absent Lifecycle wording": re.compile(
            r"(?i)\bLifecycle\b.{0,50}\b(?:not implemented|not yet implemented|planned only)\b"
        ),
    }
    current_texts: dict[str, str] = {}

    def add_exact_current_texts(
        repo: Path,
        revision: str | None,
        display_prefix: str,
        include: Any,
    ) -> None:
        try:
            snapshot = git_snapshot(repo, revision)
        except RuntimeError as exc:
            errors.append(f"{display_prefix or 'root'} current tree cannot be inspected: {exc}")
            return
        if snapshot is None:
            errors.append(
                f"{display_prefix or 'root'} current tree is not an explicit Git checkout"
            )
            return
        for relative, (mode, _object_id, _size) in sorted(snapshot.items()):
            if mode == "160000" or not include(relative):
                continue
            display_path = f"{display_prefix}{relative}"
            try:
                text = repository_relative_text(
                    repo,
                    snapshot,
                    relative,
                    label=f"current guidance {display_path}",
                )
            except RuntimeError as exc:
                errors.append(f"{display_path} cannot be inspected safely: {exc}")
                continue
            if text is not None:
                current_texts.setdefault(display_path, text)

    root_exact = {
        "AGENTS.md",
        "PRD.md",
        *CURRENT_AUTHORITY_JSON_ARTIFACTS,
        "skills/ecosystem/SKILL.md",
    }
    add_exact_current_texts(
        docs_checkout,
        None,
        "",
        lambda relative: (
            relative in root_exact
            or (relative.startswith("docs/") and relative.endswith(".md"))
            or (
                relative.startswith("_bmad-output/planning-artifacts/")
                and relative.endswith(".md")
                and "/" not in relative.removeprefix(
                    "_bmad-output/planning-artifacts/"
                )
            )
            or (
                relative.startswith("33god-platform/")
                and relative.endswith((".md", ".yaml", ".jsonl"))
            )
            or (
                relative.startswith("skills/momo/")
                and relative.endswith((".md", ".py"))
            )
        ),
    )

    component_selectors: dict[str, Any] = {
        "candystore": lambda relative: relative in {"README.md", "AGENTS.md"}
        or (relative.startswith("docs/") and relative.endswith(".md")),
        "pjangler": lambda relative: relative in {"README.md", "AGENTS.md"}
        or (relative.startswith("docs/") and relative.endswith(".md")),
        "momo": lambda relative: relative in {"README.md", "AGENTS.md"}
        or (relative.startswith("docs/") and relative.endswith(".md"))
        or (
            relative.startswith("_bmad/custom/workflows/ticket-lifecycle/")
            and relative.endswith(".md")
        ),
        "holocene": lambda relative: relative
        in {"README.md", "AGENTS.md", "package.json", "agents/hermes/pm/SOUL.md"}
        or (relative.startswith("docs/") and relative.endswith(".md"))
        or (
            relative.startswith(".stitch/")
            and relative.endswith((".md", ".html"))
        )
        or (
            relative.startswith(("apps/", "packages/"))
            and relative.endswith((".ts", ".tsx"))
        ),
        "bloodbank": lambda relative: relative == "README.md"
        or (
            relative.startswith(("services/agent-hooks/", "docs/"))
            and relative.endswith(".md")
        ),
        "lifecycle": lambda relative: relative == "README.md"
        or (relative.startswith("docs/") and relative.endswith(".md")),
    }
    for component, include in component_selectors.items():
        add_exact_current_texts(
            source / component,
            COMPONENT_REVISIONS[component],
            f"source/{component}/",
            include,
        )

    for display_path, text in current_texts.items():
        for image in LIFECYCLE_DIGEST_REFERENCE.findall(text):
            if image != LIFECYCLE_IMAGE:
                errors.append(f"{display_path} retains non-current Lifecycle digest")
        for label, pattern in ownership_patterns.items():
            if pattern.search(text):
                errors.append(f"{display_path} contains {label}")
        errors.extend(authority_parity_text_errors(display_path, text))

    ecosystem_text = current_texts.get("skills/ecosystem/SKILL.md", "")
    errors.extend(ecosystem_authority_errors(ecosystem_text))

    bloodbank_api_text = current_texts.get("docs/api-contracts-bloodbank.md", "")
    errors.extend(bloodbank_api_contract_errors(bloodbank_api_text))
    errors.extend(root_current_guidance_errors(docs_checkout))

    required_momo_actor_files = {
        Path("resources/obligation-skill-catalog.json"),
        Path("scripts/lifecycle_client.py"),
        Path("scripts/obligation_worker.py"),
    }
    try:
        promoted_snapshot = docs_snapshot
        canonical_snapshot = git_snapshot(
            source / "momo", COMPONENT_REVISIONS["momo"]
        )
    except RuntimeError as exc:
        errors.append(f"Momo promoted/canonical exact trees cannot be inspected: {exc}")
        promoted_snapshot = {}
        canonical_snapshot = {}
    if promoted_snapshot is None or canonical_snapshot is None:
        errors.append("Momo promoted/canonical roots must be explicit Git checkouts")
        promoted_snapshot = promoted_snapshot or {}
        canonical_snapshot = canonical_snapshot or {}

    def exact_prefix_files(snapshot: GitSnapshot, prefix: str) -> set[Path]:
        files: set[Path] = set()
        normalized = prefix.rstrip("/") + "/"
        for relative, (mode, _object_id, _size) in snapshot.items():
            if not relative.startswith(normalized):
                continue
            child = Path(PurePosixPath(relative.removeprefix(normalized)))
            if "__pycache__" in child.parts or child.suffix == ".pyc":
                continue
            if mode not in {"100644", "100755"}:
                errors.append(f"{prefix}/{child.as_posix()} is not a regular blob")
                continue
            files.add(child)
        return files

    promoted_files = exact_prefix_files(promoted_snapshot, "skills/momo")
    canonical_files = exact_prefix_files(canonical_snapshot, "skill")
    if promoted_files != canonical_files:
        errors.append("promoted skills/momo file set differs from momo/skill")
    else:
        changed: list[str] = []
        for relative in sorted(promoted_files):
            try:
                promoted_bytes = snapshot_blob_bytes(
                    docs_checkout,
                    promoted_snapshot,
                    f"skills/momo/{relative.as_posix()}",
                    label=f"promoted skills/momo/{relative.as_posix()}",
                )
                canonical_bytes = snapshot_blob_bytes(
                    source / "momo",
                    canonical_snapshot,
                    f"skill/{relative.as_posix()}",
                    label=f"canonical momo/skill/{relative.as_posix()}",
                )
            except RuntimeError as exc:
                errors.append(f"Momo promoted/canonical blob cannot be read: {exc}")
                continue
            if promoted_bytes != canonical_bytes:
                changed.append(relative.as_posix())
        if changed:
            errors.append(
                "promoted skills/momo differs byte-for-byte: " + ", ".join(changed)
            )
    missing_actor_files = sorted(required_momo_actor_files - canonical_files)
    if missing_actor_files:
        errors.append(
            "Momo durable obligation actor files are missing: "
            + ", ".join(str(path) for path in missing_actor_files)
        )
    else:
        try:
            worker_text = repository_relative_text(
                source / "momo",
                canonical_snapshot,
                "skill/scripts/obligation_worker.py",
                label="Momo canonical obligation worker",
            ) or ""
        except RuntimeError as exc:
            errors.append(f"Momo canonical obligation worker cannot be read: {exc}")
            worker_text = ""
        required_worker_contract = {
            "invocation-derived completion time": 'completed_at = command["time"]',
            "canonical JetStream message ID": (
                'headers={"Nats-Msg-Id": completion["id"]}'
            ),
            "completion PubAck marker": 'operations.append("completion_puback")',
            "invocation ACK confirmation": "await message.ack_sync(",
            "receipt write": "_atomic_write(Path(receipt_path)",
        }
        for label, snippet in required_worker_contract.items():
            if snippet not in worker_text:
                errors.append(
                    f"Momo worker lacks structural source prerequisite: {label}"
                )
        ordered_worker_contract = [
            required_worker_contract["completion PubAck marker"],
            required_worker_contract["invocation ACK confirmation"],
            required_worker_contract["receipt write"],
        ]
        if all(snippet in worker_text for snippet in ordered_worker_contract):
            positions = [
                worker_text.index(snippet) for snippet in ordered_worker_contract
            ]
            if positions != sorted(positions):
                errors.append(
                    "Momo worker structural source prerequisites do not retain "
                    "PubAck-before-ACK-before-receipt order; execution proof remains native/live"
                )

    try:
        harness_text = repository_relative_text(
            docs_checkout,
            promoted_snapshot,
            "33god-platform/scripts/verify-lifecycle-live.py",
            label="Lifecycle live harness",
        ) or ""
    except RuntimeError as exc:
        errors.append(f"Lifecycle live harness cannot be read: {exc}")
        harness_text = ""
    required_harness_contract = {
        "stored completion message lookup": (
            "completion_stream_message = self.stream_message("
        ),
        "clean non-duplicate completion PubAck": (
            'receipt["completion"]["duplicate"] is not False'
        ),
        "stored canonical completion message ID": (
            '"Nats-Msg-Id": completion_event["id"]'
        ),
    }
    for label, snippet in required_harness_contract.items():
        if snippet not in harness_text:
            errors.append(
                f"Lifecycle live harness lacks structural source prerequisite: {label}"
            )
    errors.extend(ticket_lifecycle_surface_errors(source))
    errors.extend(bloodbank_live_inventory_errors(source))
    return errors


def check_docs(docs: Path, report: Reporter) -> None:
    checkout = docs.parent
    snapshot = git_snapshot(checkout)
    if snapshot is not None:
        markdown_relatives = sorted(
            relative
            for relative, (mode, _object_id, _size) in snapshot.items()
            if relative.startswith("docs/")
            and "/" not in relative.removeprefix("docs/")
            and relative.endswith(".md")
            and mode in {"100644", "100755"}
        )
    else:
        markdown_relatives = [
            path.relative_to(checkout).as_posix()
            for path in sorted(docs.glob("*.md"))
            if path.is_file() and not path.is_symlink()
        ]
    marker_hits = []
    broken = []
    for relative in markdown_relatives:
        path = checkout / relative
        text = repository_relative_text(
            checkout,
            snapshot,
            relative,
            label=f"root documentation {relative}",
        ) or ""
        if FORBIDDEN_MARKERS.search(text):
            marker_hits.append(path.name)
        for target in MARKDOWN_LINK.findall(text):
            clean = target.split("#", 1)[0]
            if not clean or clean.startswith(("http://", "https://", "mailto:")):
                continue
            target_relative = os.path.normpath(
                os.path.join(os.path.dirname(relative), clean)
            ).replace(os.sep, "/")
            if target_relative.startswith("../") or target_relative == "..":
                broken.append(f"{path.name} -> {target}")
                continue
            if snapshot is not None:
                destination_exists = target_relative in snapshot or any(
                    item.startswith(target_relative.rstrip("/") + "/")
                    for item in snapshot
                )
            else:
                destination = checkout / Path(PurePosixPath(target_relative))
                destination_exists = destination.exists()
            if not destination_exists:
                broken.append(f"{path.name} -> {target}")
    if marker_hits:
        report.fail("doc-markers", "incomplete markers in: " + ", ".join(marker_hits))
    else:
        report.passed(
            "doc-markers",
            f"no forbidden incomplete markers in {len(markdown_relatives)} Markdown files",
        )
    if broken:
        report.fail("doc-links", "broken internal links: " + "; ".join(broken))
    else:
        report.passed("doc-links", "all Markdown file links resolve")


def parse_args() -> argparse.Namespace:
    script_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root", type=Path, default=script_root, help="live source checkout"
    )
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=script_root,
        help="checkout containing root docs/config",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source_root.expanduser().resolve()
    docs_checkout = args.docs_root.expanduser().resolve()
    docs = docs_checkout / "docs"
    report = Reporter()
    print(f"33GOD drift check\nsource={source}\ndocs={docs}")
    with validation_session():
        try:
            source_is_checkout = is_own_checkout(source)
        except RuntimeError as exc:
            report.fail("source-checkout", f"Git identity cannot be verified safely: {exc}")
            source_is_checkout = False
        if not source_is_checkout:
            report.fail(
                "source-checkout",
                "selected source root must be its own Git checkout, not an inherited wrapper path",
            )
        checks = (
            ("root-artifacts", lambda: check_root_artifacts(source, docs, report)),
            ("topology", lambda: check_part_declaration(source, docs, report)),
            ("component-bmad", lambda: check_component_bmad(source, docs, report)),
            ("platform-manifest", lambda: check_platform_manifest(source, report)),
            ("high-risk-contracts", lambda: check_high_risk_contracts(source, report)),
            (
                "root-compose",
                lambda: check_compose_candidate(source, docs_checkout, report),
            ),
            ("docs", lambda: check_docs(docs, report)),
        )
        for label, check in checks:
            try:
                check()
            except (csv.Error, OSError, RuntimeError, TypeError, ValueError) as exc:
                report.fail(label, f"validation failed safely: {exc}")
    print(f"SUMMARY PASS={report.passes} WARN={report.warnings} FAIL={report.failures}")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
