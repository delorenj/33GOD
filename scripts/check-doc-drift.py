#!/usr/bin/env python3
"""Read-only 33GOD four-part documentation and contract parity check."""

from __future__ import annotations

import argparse
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


PARTS = ("bloodbank", "candystore", "holocene", "pjangler")
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
    "sha256:982a25126a292dba8a6af43c38a4b4c136726c054a0076ba56a8d2055974ec67"
)
COMPONENT_REVISIONS = {
    "bloodbank": "48031ee39c238b9d4715b81b74076635235f96d5",
    "lifecycle": "797fcf4e0cba45a86720f7af4b94ed73be921d38",
    "candystore": "b3b4d829b1e7ff52ea4f36f8124a4b80a6435d07",
    "momo": "4c41a998ccfd34afa47d86326c90b958b05fc1a8",
    "holocene": "e8cecb983d4f4f210a729d9ddfd2330e9d98e729",
}
LIFECYCLE_DIGEST_REFERENCE = re.compile(
    r"ghcr\.io/delorenj/lifecycle@sha256:[0-9a-f]{64}"
)
ECOSYSTEM_AUTHORITY_CONTRACT = (
    "Plane ticket/work-item and board/lane operations "
    "(project-lifecycle, never Lifecycle authority)",
    "standalone Lifecycle component is the sole deterministic 33GOD lifecycle authority",
    "Plane owns ticket/work-item records and board/lane state only",
    "`project-lifecycle` routes only Plane ticket/work-item and board/lane mutations",
    "Momo chooses and ranks what legal work to attempt and publishes evidence",
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
        value = yaml.safe_load(handle) or {}
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


def check_part_declaration(source: Path, docs: Path, report: Reporter) -> None:
    path = docs / "project-parts.json"
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ids = tuple(item["id"] for item in data["parts"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report.fail("four-part-scope", f"cannot parse declaration: {exc}")
        return
    if ids != PARTS or data.get("scope_policy") != "exact":
        report.fail(
            "four-part-scope", f"expected exact ordered parts {PARTS}; found {ids}"
        )
    else:
        report.passed(
            "four-part-scope",
            "exact Bloodbank/Candystore/Holocene/PJangler declaration",
        )

    missing_roots = [part for part in PARTS if not (source / part).is_dir()]
    if missing_roots:
        report.fail(
            "component-roots", f"missing source directories: {', '.join(missing_roots)}"
        )
    else:
        report.passed("component-roots", "all four live component roots exist")


def check_component_bmad(source: Path, docs: Path, report: Reporter) -> None:
    for part in PARTS:
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
    component_paths = {part: platform / "components" / f"{part}.yaml" for part in PARTS}
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
            "and promoted Momo skill are current",
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
        result = subprocess.run(
            ["git", "-C", str(source / name), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
        )
        actual = result.stdout.strip()
        if result.returncode or actual != expected:
            errors.append(
                f"{name} checkout={actual or 'unavailable'} expected={expected}"
            )
        manifest = platform / "components" / f"{name}.yaml"
        manifest_text = (
            manifest.read_text(encoding="utf-8") if manifest.is_file() else ""
        )
        if expected not in manifest_text:
            errors.append(f"{name} component manifest does not pin {expected}")

    current_paths = [
        docs_checkout / "PRD.md",
        *sorted((docs_checkout / "docs").rglob("*.md")),
        *sorted((docs_checkout / "_bmad-output/planning-artifacts").glob("*.md")),
        *sorted(platform.rglob("*.md")),
        *sorted(platform.rglob("*.yaml")),
        *sorted(platform.rglob("*.jsonl")),
        docs_checkout / "skills/ecosystem/SKILL.md",
        *sorted((docs_checkout / "skills/momo").rglob("*.md")),
        *sorted((docs_checkout / "skills/momo").rglob("*.py")),
    ]
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
        for image in LIFECYCLE_DIGEST_REFERENCE.findall(text):
            if image != LIFECYCLE_IMAGE:
                errors.append(
                    f"{path.relative_to(docs_checkout)} retains non-current Lifecycle digest"
                )
        for label, pattern in ownership_patterns.items():
            if pattern.search(text):
                errors.append(f"{path.relative_to(docs_checkout)} contains {label}")

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

    promoted = docs_checkout / "skills/momo"
    canonical = source / "momo/skill"
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
