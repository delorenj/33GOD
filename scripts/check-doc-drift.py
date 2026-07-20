#!/usr/bin/env python3
"""Read-only 33GOD topology, documentation, and contract parity check."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

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
    "ghcr.io/delorenj/lifecycle:"
    "sha-cda59658bef6d586c8aa01cacd88bc4e3ee867e0"
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
    "Momo chooses and executes legal work and publishes evidence",
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
    "safe-coexistence ceremony": re.compile(r"(?i)\b(?:safe[- ]?)?coexist(?:ence|s|ing)?\b"),
    "Momo-offline safety ceremony": re.compile(
        r"(?i)\bMomo[- ]offline\s+safety\b"
    ),
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
CURRENT_AUTHORITY_JSON_ARTIFACTS = (
    "docs/project-scan-report.json",
)


class Reporter:
    def __init__(self) -> None:
        self.passes = 0
        self.warnings = 0
        self.failures = 0

    def emit(self, level: str, check: str, detail: str) -> None:
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


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML unavailable")
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ValueError("expected a YAML mapping")
    return value


def check_root_artifacts(source: Path, docs: Path, report: Reporter) -> None:
    missing = [name for name in REQUIRED_ROOT_DOCS if not (docs / name).is_file()]
    if missing:
        report.fail(
            "root-docs", f"missing required files under {docs}: {', '.join(missing)}"
        )
    else:
        report.passed(
            "root-docs", f"all {len(REQUIRED_ROOT_DOCS)} core files exist under {docs}"
        )

    config_root = docs.parent
    required_configs = (
        config_root / "_bmad/core/config.yaml",
        config_root / "_bmad/bmm/config.yaml",
    )
    absent = [str(path) for path in required_configs if not path.is_file()]
    if absent:
        report.fail("root-bmad", f"missing root configuration: {', '.join(absent)}")
    elif yaml is None:
        report.warn(
            "root-bmad", "PyYAML unavailable; files exist but YAML parsing was skipped"
        )
    else:
        try:
            core, bmm = (load_yaml(path) for path in required_configs)
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
    part_ids = tuple(
        str(item.get("id"))
        for item in parts
        if isinstance(item, dict)
    )
    acceptance_slice = platform_data.get("acceptance_slice")
    if not isinstance(acceptance_slice, dict):
        acceptance_slice = {}
    acceptance_components = acceptance_slice.get("components")
    if not isinstance(acceptance_components, list):
        acceptance_components = []
    platform_slice = tuple(
        str(item)
        for item in acceptance_components
    )
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
    if not isinstance(component_files, list):
        component_files = []
    platform_registry = tuple(
        Path(str(item)).stem for item in component_files
    )
    if (
        product_registry.get("scope_policy") != "exact"
        or declared_registry != PRODUCT_COMPONENT_IDS
        or platform_registry != PRODUCT_COMPONENT_IDS
    ):
        errors.append(
            "twelve-component product registry must be the exact ordered set "
            f"{PRODUCT_COMPONENT_IDS}; project-parts={declared_registry}, "
            f"platform={platform_registry}"
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
        str(item.get("part_id"))
        for item in project_types
        if isinstance(item, dict)
    )
    if (
        classification.get("acceptance_slice_count") != len(
            LIFECYCLE_ACCEPTANCE_SLICE
        )
        or classification.get("product_registry_count") != len(
            PRODUCT_COMPONENT_IDS
        )
        or scan_parts != LIFECYCLE_ACCEPTANCE_SLICE
    ):
        errors.append(
            "project-scan-report must record six acceptance parts and twelve "
            f"registry components; counts={classification!r}, parts={scan_parts}"
        )
    if scan_data.get("project_root") != "{project-root}":
        errors.append(
            "project-scan-report project_root must use the reproducible "
            "{project-root} token"
        )
    return errors


def check_part_declaration(source: Path, docs: Path, report: Reporter) -> None:
    parts_path = docs / "project-parts.json"
    scan_path = docs / "project-scan-report.json"
    platform_path = source / "33god-platform/components.yaml"
    try:
        parts_data = json.loads(parts_path.read_text(encoding="utf-8"))
        scan_data = json.loads(scan_path.read_text(encoding="utf-8"))
        platform_data = load_yaml(platform_path)
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
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report.fail("topology-scope", f"cannot parse declaration: {exc}")
        return
    errors = topology_declaration_errors(parts_data, platform_data, scan_data)
    if errors:
        report.fail("topology-scope", "; ".join(errors))
    else:
        report.passed(
            "topology-scope",
            "exact six-component Lifecycle slice and twelve-component registry",
        )

    missing_roots = [
        part for part in LIFECYCLE_ACCEPTANCE_SLICE if not (source / part).is_dir()
    ]
    if missing_roots:
        report.fail(
            "component-roots", f"missing source directories: {', '.join(missing_roots)}"
        )
    else:
        report.passed(
            "component-roots", "all six Lifecycle acceptance roots exist"
        )


def check_component_bmad(source: Path, docs: Path, report: Reporter) -> None:
    for part in DOCUMENTED_COMPONENTS:
        root = source / part
        configs = (root / "_bmad/core/config.yaml", root / "_bmad/bmm/config.yaml")
        missing = [
            str(path.relative_to(source)) for path in configs if not path.is_file()
        ]
        root_docs = (
            docs / f"architecture-{part}.md",
            docs / f"development-guide-{part}.md",
        )
        missing.extend(str(path) for path in root_docs if not path.is_file())
        if not (root / "docs").is_dir():
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
            core = load_yaml(configs[0])
            bmm = load_yaml(configs[1])
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
            elif (config_toml := root / "_bmad/config.toml").is_file():
                with config_toml.open("rb") as handle:
                    canonical = tomllib.load(handle)
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
        if not path.is_file():
            report.fail(f"platform-{part}", f"missing {path}")
            continue
        try:
            item = load_yaml(path)
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

    pjangler_text = component_paths["pjangler"].read_text(encoding="utf-8")
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
        re.sub(r"\s+", " ", paragraph)
        for paragraph in re.split(r"\n\s*\n", text)
    ]
    errors = [
        f"{path} contains {label}"
        for label, pattern in AUTHORITY_PARITY_PATTERNS.items()
        if any(pattern.search(paragraph) for paragraph in paragraphs)
    ]
    normalized_path = path.casefold()
    if (
        "holocene/" in normalized_path
        and re.search(r"(?i)\b33GOD\s+Control[-\s]+Plane\b", text)
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


OPERATIONAL_COMPONENTS = ("bloodbank", "candystore", "holocene", "pjangler")
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
OPERATIONAL_NESTED_MARKERS = (
    "agents/hermes/",
    "templates/commonproject",
    "templates/hermes-agent",
    ".tmp/plugins",
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
TICKET_LIFECYCLE_VARIANT = re.compile(r"(?i)ticket[-_ ]?lifecycle")
MOMO_HOLOCENE_COPY_PATTERN = re.compile(
    r"(?is)(?:\b(?:copy|copies|replica|mirror|byte[- ]identical|stored)\b.{0,100}"
    r"\bHolocene\b|\bHolocene\b.{0,100}"
    r"\b(?:copy|copies|replica|mirror|byte[- ]identical|stored)\b|"
    r"\bMomo/Holocene\b)"
)


def is_own_checkout(repo: Path) -> bool:
    if not repo.is_dir() or not (repo / ".git").exists():
        return False
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
    )
    return not result.returncode and Path(result.stdout.strip()).resolve() == repo.resolve()


def checkout_revision(repo: Path) -> str | None:
    """Return HEAD only when ``repo`` is itself an initialized checkout."""

    if not is_own_checkout(repo):
        return None
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
    )
    return result.stdout.strip() if not result.returncode else None


def repository_gitlinks(repo: Path) -> dict[str, str]:
    if not is_own_checkout(repo):
        return {}
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--stage", "-z"],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        return {}
    gitlinks: dict[str, str] = {}
    for record in result.stdout.split("\0"):
        if not record or "\t" not in record:
            continue
        metadata, relative = record.split("\t", 1)
        fields = metadata.split()
        if len(fields) >= 2 and fields[0] == "160000":
            gitlinks[relative] = fields[1]
    return gitlinks


def repository_files(repo: Path) -> list[Path]:
    if is_own_checkout(repo):
        result = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z"],
            text=True,
            capture_output=True,
        )
        if not result.returncode:
            return [repo / item for item in result.stdout.split("\0") if item]
    if not repo.is_dir():
        return []
    return [
        path
        for path in repo.rglob("*")
        if ".git" not in path.parts and (path.is_file() or path.is_symlink())
    ]


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def is_operational_path(relative: str) -> bool:
    normalized = relative.casefold().replace("\\", "/")
    return any(marker in normalized for marker in OPERATIONAL_PATH_MARKERS)


def scan_operational_repository(
    source: Path,
    component: str,
    repo: Path,
    *,
    nested_label: str | None = None,
) -> list[str]:
    errors: list[str] = []
    for path in repository_files(repo):
        try:
            relative_repo = path.relative_to(repo).as_posix()
        except ValueError:
            continue
        if not is_operational_path(relative_repo):
            continue
        display = f"{component}/{relative_repo}"
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
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > 1_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        context = f"{nested_label}: " if nested_label else ""
        qualifier = "symlink " if symlink else ""
        if TICKET_LIFECYCLE_VARIANT.search(relative_repo) or (
            TICKET_LIFECYCLE_VARIANT.search(text)
            and ("workflow" in relative_repo.casefold() or "command" in relative_repo.casefold())
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
    return errors


def non_momo_operational_surface_errors(source: Path) -> list[str]:
    """Reject semantic lifecycle engines beyond named workflow directories."""

    errors: list[str] = []
    for component in OPERATIONAL_COMPONENTS:
        root = source / component
        if not root.is_dir():
            continue
        errors.extend(scan_operational_repository(source, component, root))
        for relative, recorded in repository_gitlinks(root).items():
            normalized = relative.casefold().replace("\\", "/")
            if not any(marker in normalized for marker in OPERATIONAL_NESTED_MARKERS):
                continue
            nested = root / relative
            if not (nested / ".git").exists():
                errors.append(
                    f"{component} has uninitialized nested gitlink {relative} at "
                    f"{recorded}; semantic absence cannot be proven"
                )
                continue
            actual = checkout_revision(nested)
            if actual != recorded:
                errors.append(
                    f"{component} nested gitlink {relative} checkout="
                    f"{actual or 'unavailable'} expected={recorded}"
                )
                continue
            errors.extend(
                scan_operational_repository(
                    source,
                    component,
                    nested,
                    nested_label=f"{component} nested gitlink {relative}",
                )
            )
    return sorted(set(errors))


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
        for relative in workflow_roots:
            path = root / relative
            if path.is_dir() and any(candidate.is_file() for candidate in path.rglob("*")):
                errors.append(
                    f"{component} retains non-Momo ticket-lifecycle workflow at {relative}"
                )
        for relative in manifest_paths:
            path = root / relative
            if path.is_file() and "ticket-lifecycle" in path.read_text(
                encoding="utf-8"
            ).casefold():
                errors.append(
                    f"{component} registers non-Momo ticket-lifecycle workflow in {relative}"
                )
        for relative in TICKET_LIFECYCLE_COMMAND_SURFACES:
            if (root / relative).is_file():
                errors.append(
                    f"{component} retains non-Momo ticket-lifecycle command surface at {relative}"
                )

    momo = source / "momo"
    if not momo.is_dir():
        return [*errors, "Momo checkout is missing"]
    source_workflow = momo / workflow_roots[0]
    mirror_workflow = momo / workflow_roots[1]
    source_files = {
        path.relative_to(source_workflow)
        for path in source_workflow.rglob("*")
        if path.is_file()
    }
    mirror_files = {
        path.relative_to(mirror_workflow)
        for path in mirror_workflow.rglob("*")
        if path.is_file()
    }
    if not source_files or source_files != mirror_files:
        errors.append("Momo canonical ticket-lifecycle source/mirror file sets differ")
    mismatched_files = [
        relative.as_posix()
        for relative in sorted(source_files & mirror_files)
        if (source_workflow / relative).read_bytes()
        != (mirror_workflow / relative).read_bytes()
    ]
    if mismatched_files:
        errors.append(
            "Momo canonical ticket-lifecycle source/mirror bytes differ: "
            + ", ".join(mismatched_files)
        )
    if any(path.suffix == ".bak" for path in source_files | mirror_files):
        errors.append("Momo canonical ticket-lifecycle workflow retains .bak residue")

    for relative in sorted(source_files):
        path = source_workflow / relative
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if MOMO_HOLOCENE_COPY_PATTERN.search(text):
            errors.append(
                "Momo canonical ticket-lifecycle workflow contains Holocene copy "
                f"claim in {relative.as_posix()}"
            )

    workflow_manifest = momo / manifest_paths[0]
    workflow_rows: list[dict[str, str]] = []
    if workflow_manifest.is_file():
        with workflow_manifest.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if None in row or any(value is None for value in row.values()):
                    errors.append("Momo workflow-manifest contains a malformed CSV row")
                    continue
                row_text = " ".join(str(value) for value in row.values()).casefold()
                if "ticket-lifecycle" in row_text:
                    workflow_rows.append(row)
    if len(workflow_rows) != 1:
        errors.append(
            "Momo must register exactly one canonical ticket-lifecycle workflow"
        )
    else:
        row = workflow_rows[0]
        description = row.get("description", "")
        normalized = description.casefold()
        metadata_valid = (
            row.get("name") == "ticket-lifecycle"
            and row.get("module") == "custom"
            and row.get("path")
            == "_bmad/custom/workflows/ticket-lifecycle/workflow.md"
            and "lifecycle" in normalized
            and "client" in normalized
            and ("bounded" in normalized or "legal work" in normalized)
            and "autonomous multi-agent ticket lifecycle" not in normalized
            and "plane + bloodbank" not in normalized
        )
        if not metadata_valid:
            errors.append(
                "Momo workflow-manifest lacks bounded Lifecycle client metadata"
            )

    files_manifest = momo / manifest_paths[1]
    file_rows = []
    if files_manifest.is_file():
        with files_manifest.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if None in row or any(value is None for value in row.values()):
                    errors.append("Momo files-manifest contains a malformed CSV row")
                    continue
                relative_path = row.get("path", "")
                if isinstance(relative_path, str) and (
                    "ticket-lifecycle" in relative_path.casefold()
                ):
                    file_rows.append(row)
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
        source_path = momo / "_bmad" / relative_path
        expected_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if row.get("hash") != expected_hash:
            errors.append(
                "Momo ticket-lifecycle files-manifest hash differs for "
                f"{relative_path}"
            )
    return errors


def bloodbank_live_inventory_errors(source: Path) -> list[str]:
    """Reject a live Bloodbank lifecycle-controller service or README inventory row."""

    errors: list[str] = []
    if (source / "bloodbank/services/lifecycle-controller").exists():
        errors.append("Bloodbank retains executable services/lifecycle-controller")
    readme = source / "bloodbank/README.md"
    readme_text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    for line in readme_text.splitlines():
        if "`services/`" in line and re.search(
            r"(?i)lifecycle[- ]controller", line
        ):
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


def root_current_guidance_errors(docs_checkout: Path) -> list[str]:
    """Reject root guidance that revives removed authority or stale topology."""

    errors: list[str] = []
    for relative in (
        "docs/development-guide-bloodbank.md",
        "docs/component-inventory-bloodbank.md",
    ):
        path = docs_checkout / relative
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if re.search(r"(?i)(?:bloodbank/)?services/lifecycle-controller", text):
            errors.append(
                f"{relative} contains current Bloodbank guidance to the removed "
                "lifecycle-controller"
            )

    architecture = docs_checkout / "_bmad-output/planning-artifacts/architecture.md"
    architecture_text = (
        architecture.read_text(encoding="utf-8") if architecture.is_file() else ""
    )
    if RETIRED_ARCHITECTURE_INPUT.search(architecture_text):
        errors.append(
            "_bmad-output/planning-artifacts/architecture.md contains retired "
            "architecture input paths"
        )

    for relative in CURRENT_TOPOLOGY_TEXT_ARTIFACTS:
        path = docs_checkout / relative
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if STALE_TOPOLOGY_PATTERN.search(text):
            errors.append(f"{relative} retains obsolete four-part topology guidance")
    return errors


def check_high_risk_contracts(source: Path, report: Reporter) -> None:
    validator = source / "bloodbank/services/agent-hooks/core/validate.py"
    text = validator.read_text(encoding="utf-8") if validator.is_file() else ""
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

    heartbeat = source / "bloodbank/services/heartbeat-recorder"
    compose = source / "bloodbank/compose/docker-compose.yml"
    compose_text = compose.read_text(encoding="utf-8") if compose.is_file() else ""
    if "services/heartbeat-recorder" in compose_text and not heartbeat.is_dir():
        report.fail(
            "bloodbank-heartbeat",
            "Compose references missing services/heartbeat-recorder",
        )
    else:
        report.passed(
            "bloodbank-heartbeat", "heartbeat build context is internally consistent"
        )

    candy_compose = source / "candystore/compose.yml"
    candy_text = (
        candy_compose.read_text(encoding="utf-8") if candy_compose.is_file() else ""
    )
    if "MUTUAL EXCLUSION" in candy_text and "candystore-events" in (
        source / "candystore/dapr-components/pubsub.yaml"
    ).read_text(encoding="utf-8"):
        report.passed(
            "candystore-deployment-mode",
            "standalone manifest declares legacy-profile mutual exclusion",
        )
    else:
        report.fail(
            "candystore-deployment-mode",
            "mutual-exclusion declaration or durable identity is missing",
        )

    fleet = source / "holocene/apps/api/src/fleet.ts"
    fleet_text = fleet.read_text(encoding="utf-8") if fleet.is_file() else ""
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

    consumer = (
        source
        / "pjangler/templates/hermes-agent/runtime-scaffold/bloodbank-consumer.py"
    )
    consumer_text = consumer.read_text(encoding="utf-8") if consumer.is_file() else ""
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


def check_compose_candidate(
    source: Path, docs_checkout: Path, report: Reporter
) -> None:
    validator = docs_checkout / "33god-platform/scripts/validate-compose.py"
    compose = docs_checkout / "33god-platform/compose.yaml"
    if not validator.is_file() or not compose.is_file():
        report.fail("root-compose", "candidate Compose validator or model is missing")
        return
    result = subprocess.run(
        [
            sys.executable,
            str(validator),
            "--compose-file",
            str(compose),
            "--source-root",
            str(source),
        ],
        text=True,
        capture_output=True,
    )
    detail = (result.stdout or result.stderr).strip().replace("\n", "; ")
    current_truth_errors = lifecycle_current_truth_errors(source, docs_checkout)
    if result.returncode or current_truth_errors:
        reasons = [detail] if result.returncode and detail else []
        reasons.extend(current_truth_errors)
        report.fail(
            "root-compose",
            "; ".join(reasons) or f"candidate validator exited {result.returncode}",
        )
    else:
        report.passed(
            "root-compose",
            f"{detail}; exact lifecycle digest, component revisions, ownership text, "
            "authority-parity workflow surfaces, and promoted Momo skill are current",
        )


def lifecycle_current_truth_errors(source: Path, docs_checkout: Path) -> list[str]:
    errors: list[str] = []
    platform = docs_checkout / "33god-platform"
    compose_text = (platform / "compose.yaml").read_text(encoding="utf-8")
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

    for name, expected in COMPONENT_REVISIONS.items():
        actual = checkout_revision(source / name)
        if actual != expected:
            errors.append(
                f"{name} checkout={actual or 'unavailable'} expected={expected}"
            )
        index_result = subprocess.run(
            ["git", "-C", str(source), "ls-files", "--stage", "--", name],
            text=True,
            capture_output=True,
        )
        index_fields = index_result.stdout.split()
        index_mode = index_fields[0] if index_fields else ""
        index_revision = index_fields[1] if len(index_fields) > 1 else ""
        if (
            index_result.returncode
            or index_mode != "160000"
            or index_revision != expected
        ):
            errors.append(
                f"root gitlink {name}={index_revision or 'unavailable'} expected={expected}"
            )
        manifest = platform / "components" / f"{name}.yaml"
        manifest_text = (
            manifest.read_text(encoding="utf-8") if manifest.is_file() else ""
        )
        if expected not in manifest_text:
            errors.append(f"{name} component manifest does not pin {expected}")

    commonproject = source / "pjangler/templates/commonproject"
    commonproject_actual = checkout_revision(commonproject)
    if commonproject_actual != COMMONPROJECT_REVISION:
        errors.append(
            "CommonProject checkout="
            f"{commonproject_actual or 'unavailable'} expected={COMMONPROJECT_REVISION}"
        )
    commonproject_index = subprocess.run(
        [
            "git",
            "-C",
            str(source / "pjangler"),
            "ls-files",
            "--stage",
            "--",
            "templates/commonproject",
        ],
        text=True,
        capture_output=True,
    )
    commonproject_fields = commonproject_index.stdout.split()
    commonproject_mode = commonproject_fields[0] if commonproject_fields else ""
    commonproject_pin = (
        commonproject_fields[1] if len(commonproject_fields) > 1 else ""
    )
    if (
        commonproject_index.returncode
        or commonproject_mode != "160000"
        or commonproject_pin != COMMONPROJECT_REVISION
    ):
        errors.append(
            "PJangler CommonProject gitlink="
            f"{commonproject_pin or 'unavailable'} expected={COMMONPROJECT_REVISION}"
        )
    pjangler_manifest = platform / "components/pjangler.yaml"
    pjangler_manifest_text = pjangler_manifest.read_text(encoding="utf-8")
    if COMMONPROJECT_REVISION not in pjangler_manifest_text:
        errors.append(
            "pjangler component manifest does not pin CommonProject "
            f"{COMMONPROJECT_REVISION}"
        )

    lifecycle_manifest = platform / "components" / "lifecycle.yaml"
    lifecycle_manifest_text = lifecycle_manifest.read_text(encoding="utf-8")
    expected_lifecycle_pins = {
        "image_source_revision": COMPONENT_REVISIONS["lifecycle"],
        "image_tag": LIFECYCLE_TAG,
        "image": LIFECYCLE_IMAGE,
    }
    for field, expected in expected_lifecycle_pins.items():
        if f"{field}: {expected}" not in lifecycle_manifest_text:
            errors.append(
                f"Lifecycle component manifest {field} does not pin {expected}"
            )

    current_paths = [
        docs_checkout / "AGENTS.md",
        docs_checkout / "PRD.md",
        *(
            docs_checkout / relative
            for relative in CURRENT_AUTHORITY_JSON_ARTIFACTS
        ),
        *sorted((docs_checkout / "docs").rglob("*.md")),
        *sorted((docs_checkout / "_bmad-output/planning-artifacts").glob("*.md")),
        *sorted(platform.rglob("*.md")),
        *sorted(platform.rglob("*.yaml")),
        *sorted(platform.rglob("*.jsonl")),
        docs_checkout / "skills/ecosystem/SKILL.md",
        *sorted((docs_checkout / "skills/momo").rglob("*.md")),
        *sorted((docs_checkout / "skills/momo").rglob("*.py")),
    ]
    for component in ("candystore", "holocene", "momo", "pjangler"):
        component_root = source / component
        current_paths.extend(
            [
                component_root / "README.md",
                component_root / "AGENTS.md",
                *sorted((component_root / "docs").rglob("*.md")),
            ]
        )
    holocene_root = source / "holocene"
    current_paths.extend(
        [
            holocene_root / "package.json",
            holocene_root / "agents/hermes/pm/SOUL.md",
            *sorted((holocene_root / ".stitch").rglob("*.md")),
            *sorted((holocene_root / ".stitch").rglob("*.html")),
            *sorted((holocene_root / "apps").rglob("*.ts")),
            *sorted((holocene_root / "apps").rglob("*.tsx")),
            *sorted((holocene_root / "packages").rglob("*.ts")),
            *sorted((holocene_root / "packages").rglob("*.tsx")),
        ]
    )
    bloodbank_root = source / "bloodbank"
    current_paths.extend(
        [
            bloodbank_root / "README.md",
            *sorted((bloodbank_root / "services/agent-hooks").rglob("*.md")),
            *sorted((bloodbank_root / "docs").rglob("*.md")),
        ]
    )
    lifecycle_root = source / "lifecycle"
    current_paths.extend(
        [
            lifecycle_root / "README.md",
            *sorted((lifecycle_root / "docs").rglob("*.md")),
        ]
    )
    current_paths.extend(
        sorted(
            (source / "momo/_bmad/custom/workflows/ticket-lifecycle").rglob("*.md")
        )
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
    seen: set[Path] = set()
    for path in current_paths:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        text = path.read_text(encoding="utf-8")
        try:
            display_path = path.relative_to(docs_checkout).as_posix()
        except ValueError:
            display_path = f"source/{path.relative_to(source).as_posix()}"
        for image in LIFECYCLE_DIGEST_REFERENCE.findall(text):
            if image != LIFECYCLE_IMAGE:
                errors.append(
                    f"{display_path} retains non-current Lifecycle digest"
                )
        for label, pattern in ownership_patterns.items():
            if pattern.search(text):
                errors.append(f"{display_path} contains {label}")
        errors.extend(authority_parity_text_errors(display_path, text))

    ecosystem_path = docs_checkout / "skills/ecosystem/SKILL.md"
    ecosystem_text = (
        ecosystem_path.read_text(encoding="utf-8") if ecosystem_path.is_file() else ""
    )
    errors.extend(ecosystem_authority_errors(ecosystem_text))

    bloodbank_api_path = docs_checkout / "docs/api-contracts-bloodbank.md"
    bloodbank_api_text = (
        bloodbank_api_path.read_text(encoding="utf-8")
        if bloodbank_api_path.is_file()
        else ""
    )
    errors.extend(bloodbank_api_contract_errors(bloodbank_api_text))
    errors.extend(root_current_guidance_errors(docs_checkout))

    promoted = docs_checkout / "skills/momo"
    canonical = source / "momo/skill"
    required_momo_actor_files = {
        Path("resources/obligation-skill-catalog.json"),
        Path("scripts/lifecycle_client.py"),
        Path("scripts/obligation_worker.py"),
    }
    promoted_files = {
        path.relative_to(promoted)
        for path in promoted.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    canonical_files = {
        path.relative_to(canonical)
        for path in canonical.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    if promoted_files != canonical_files:
        errors.append("promoted skills/momo file set differs from momo/skill")
    else:
        changed = [
            str(relative)
            for relative in sorted(promoted_files)
            if (promoted / relative).read_bytes() != (canonical / relative).read_bytes()
        ]
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
        worker_text = (canonical / "scripts/obligation_worker.py").read_text(
            encoding="utf-8"
        )
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
                errors.append(f"Momo worker lacks {label}")
        ordered_worker_contract = [
            required_worker_contract["completion PubAck marker"],
            required_worker_contract["invocation ACK confirmation"],
            required_worker_contract["receipt write"],
        ]
        if all(snippet in worker_text for snippet in ordered_worker_contract):
            positions = [worker_text.index(snippet) for snippet in ordered_worker_contract]
            if positions != sorted(positions):
                errors.append("Momo worker violates PubAck-before-ACK-before-receipt order")

    harness_path = platform / "scripts/verify-lifecycle-live.py"
    harness_text = (
        harness_path.read_text(encoding="utf-8") if harness_path.is_file() else ""
    )
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
            errors.append(f"Lifecycle live harness lacks {label}")
    errors.extend(ticket_lifecycle_surface_errors(source))
    errors.extend(bloodbank_live_inventory_errors(source))
    return errors


def check_docs(docs: Path, report: Reporter) -> None:
    markdown = sorted(docs.glob("*.md"))
    marker_hits = []
    broken = []
    for path in markdown:
        text = path.read_text(encoding="utf-8")
        if FORBIDDEN_MARKERS.search(text):
            marker_hits.append(path.name)
        for target in MARKDOWN_LINK.findall(text):
            clean = target.split("#", 1)[0]
            if not clean or clean.startswith(("http://", "https://", "mailto:")):
                continue
            destination = (path.parent / clean).resolve()
            if not destination.exists():
                broken.append(f"{path.name} -> {target}")
    if marker_hits:
        report.fail("doc-markers", "incomplete markers in: " + ", ".join(marker_hits))
    else:
        report.passed(
            "doc-markers",
            f"no forbidden incomplete markers in {len(markdown)} Markdown files",
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
    check_root_artifacts(source, docs, report)
    check_part_declaration(source, docs, report)
    check_component_bmad(source, docs, report)
    check_platform_manifest(source, report)
    check_high_risk_contracts(source, report)
    check_compose_candidate(source, docs_checkout, report)
    check_docs(docs, report)
    print(f"SUMMARY PASS={report.passes} WARN={report.warnings} FAIL={report.failures}")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
