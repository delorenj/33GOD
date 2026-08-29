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

# The hermes-agent generator materializes these trees into every provisioned
# repo, and _lib.sh prefers a repo's own vendored copy over the template's, so
# each copy is an independent generator source and all of them must be scanned.
# One file used to be scanned here; a file is not a target, a generator is.
GENERATED_SCAFFOLDS = (
    "pjangler/templates/hermes-agent/runtime-scaffold",
    "pjangler/templates/hermes-agent/template/.runtime-scaffold",
    "agents/hermes/pm/.runtime-scaffold",
    "bloodbank/agents/hermes/pm/.runtime-scaffold",
    "candystore/agents/hermes/pm/.runtime-scaffold",
    "holocene/agents/hermes/pm/.runtime-scaffold",
    "pjangler/agents/hermes/pm/.runtime-scaffold",
    "candybar/agents/hermes/pm/.runtime-scaffold",
)

# A generated subject must never carry a repo or agent identifier as a subject
# token: routing is fixed at five tokens and targets travel in `data`. The
# version segment is irrelevant to that defect, so the prefix is any run of
# literal tokens -- `bloodbank.evt.v1.repo.{REPO}` and `bloodbank.evt.repo.{REPO}`
# are the same bug and both must be caught. The grammar metavariables
# domain/entity/action/kind are placeholders for tokens, not for identifiers, so
# prose like `bloodbank.evt.<domain>.<entity>.<action>` is exempt.
ROUTING_IDENTIFIER_SUBJECT = re.compile(
    r"""
    bloodbank\.
    (?:[a-z0-9_]+\.)+                      # any literal token run: evt. / evt.v1.repo. / v1.repo.
    (?:
        \{(?!(?i:domain|entity|action|kind)\})[A-Za-z_][A-Za-z0-9_]*\}
      | \{\{(?!\s*(?i:domain|entity|action|kind)\s*\}\})\s*[^}\n]+\}\}
      | <(?!(?i:domain|entity|action|kind)>)[A-Za-z_][A-Za-z0-9_]*>
      | \$\{?(?!(?i:domain|entity|action|kind)\b)[A-Za-z_][A-Za-z0-9_]*\}?
    )
    """,
    re.VERBOSE,
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
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ValueError("expected a YAML mapping")
    return value


def check_root_artifacts(source: Path, docs: Path, report: Reporter) -> None:
    missing = [name for name in REQUIRED_ROOT_DOCS if not (docs / name).is_file()]
    if missing:
        report.fail("root-docs", f"missing required files under {docs}: {', '.join(missing)}")
    else:
        report.passed("root-docs", f"all {len(REQUIRED_ROOT_DOCS)} core files exist under {docs}")

    config_root = docs.parent
    required_configs = (config_root / "_bmad/core/config.yaml", config_root / "_bmad/bmm/config.yaml")
    absent = [str(path) for path in required_configs if not path.is_file()]
    if absent:
        report.fail("root-bmad", f"missing root configuration: {', '.join(absent)}")
    elif yaml is None:
        report.warn("root-bmad", "PyYAML unavailable; files exist but YAML parsing was skipped")
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
            errors = [f"{key}={core.get(key)!r}" for key, value in expected.items() if core.get(key) != value]
            if bmm.get("project_knowledge") != "{project-root}/docs":
                errors.append(f"project_knowledge={bmm.get('project_knowledge')!r}")
            if errors:
                report.fail("root-bmad", "root-relative configuration mismatch: " + ", ".join(errors))
            else:
                report.passed("root-bmad", "root configs parse and resolve to _bmad-output/docs conventions")
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
        report.fail("four-part-scope", f"expected exact ordered parts {PARTS}; found {ids}")
    else:
        report.passed("four-part-scope", "exact Bloodbank/Candystore/Holocene/PJangler declaration")

    missing_roots = [part for part in PARTS if not (source / part).is_dir()]
    if missing_roots:
        report.fail("component-roots", f"missing source directories: {', '.join(missing_roots)}")
    else:
        report.passed("component-roots", "all four live component roots exist")


def check_component_bmad(source: Path, docs: Path, report: Reporter) -> None:
    for part in PARTS:
        root = source / part
        configs = (root / "_bmad/core/config.yaml", root / "_bmad/bmm/config.yaml")
        missing = [str(path.relative_to(source)) for path in configs if not path.is_file()]
        root_docs = (docs / f"architecture-{part}.md", docs / f"development-guide-{part}.md")
        missing.extend(str(path) for path in root_docs if not path.is_file())
        if not (root / "docs").is_dir():
            missing.append(f"{part}/docs/")
        if missing:
            report.fail(f"component-{part}", "missing BMAD/config documentation artifacts: " + ", ".join(missing))
            continue
        if yaml is None:
            report.warn(f"component-{part}", "artifacts exist; PyYAML unavailable for config semantics")
            continue
        try:
            core = load_yaml(configs[0])
            bmm = load_yaml(configs[1])
            problems = []
            if not isinstance(core.get("project_name"), str) or not core.get("project_name"):
                problems.append(f"core project_name={core.get('project_name')!r}")
            if not isinstance(bmm.get("project_name"), str) or not bmm.get("project_name"):
                problems.append(f"bmm project_name={bmm.get('project_name')!r}")
            if bmm.get("project_knowledge") != "{project-root}/docs":
                problems.append(f"project_knowledge={bmm.get('project_knowledge')!r}")
            if problems:
                report.fail(f"component-{part}", "malformed or unresolved BMAD config: " + ", ".join(problems))
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
                    report.passed(f"component-{part}", "BMAD configs parse and root architecture/development docs exist")
            else:
                report.passed(f"component-{part}", "BMAD configs parse and root architecture/development docs exist")
        except Exception as exc:
            report.fail(f"component-{part}", f"config parse failed: {exc}")


def check_platform_manifest(source: Path, report: Reporter) -> None:
    platform = source / "33god-platform"
    component_paths = {part: platform / "components" / f"{part}.yaml" for part in PARTS}
    if yaml is None:
        report.warn("platform-manifests", "PyYAML unavailable; semantic parity was skipped")
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
                report.fail(f"platform-{part}", f"repo resolves to {declared}; expected {expected}")
            else:
                report.passed(f"platform-{part}", f"repo resolves to live {part} checkout")
        except Exception as exc:
            report.fail(f"platform-{part}", f"manifest parse/parity failed: {exc}")

    pjangler_manifest = component_paths["pjangler"]
    if not pjangler_manifest.is_file():
        report.fail("pjangler-health", f"missing {pjangler_manifest}; test-command parity cannot be checked")
        return
    pjangler_text = pjangler_manifest.read_text(encoding="utf-8")
    if "bun test" in pjangler_text:
        report.fail("pjangler-health", "platform health uses Bun, but live project is npm-based")
    elif "npm test" in pjangler_text:
        report.passed("pjangler-health", "platform health uses canonical npm test command")
    else:
        report.warn("pjangler-health", "no recognized PJangler test command in platform manifest")


def function_block(text: str, name: str) -> str:
    match = re.search(rf"^def {re.escape(name)}\([^\n]*\).*?(?=^def |\Z)", text, re.MULTILINE | re.DOTALL)
    return match.group(0) if match else ""


def check_high_risk_contracts(source: Path, report: Reporter) -> None:
    validator = source / "bloodbank/services/agent-hooks/core/validate.py"
    text = validator.read_text(encoding="utf-8") if validator.is_file() else ""
    block = function_block(text, "assert_contract")
    if "assert_subject_matches(" in block:
        report.passed("bloodbank-subject-binding", "runtime contract invokes semantic subject/type equality")
    else:
        report.fail("bloodbank-subject-binding", "assert_contract does not invoke assert_subject_matches")

    heartbeat = source / "bloodbank/services/heartbeat-recorder"
    compose = source / "bloodbank/compose/docker-compose.yml"
    if not compose.is_file():
        report.fail("bloodbank-heartbeat", f"missing {compose}; build-context parity cannot be checked")
    else:
        compose_text = compose.read_text(encoding="utf-8")
        if "services/heartbeat-recorder" in compose_text and not heartbeat.is_dir():
            report.fail("bloodbank-heartbeat", "Compose references missing services/heartbeat-recorder")
        else:
            report.passed("bloodbank-heartbeat", "heartbeat build context is internally consistent")

    candy_compose = source / "candystore/compose.yml"
    candy_pubsub = source / "candystore/dapr-components/pubsub.yaml"
    candy_text = candy_compose.read_text(encoding="utf-8") if candy_compose.is_file() else ""
    pubsub_text = candy_pubsub.read_text(encoding="utf-8") if candy_pubsub.is_file() else ""
    if "MUTUAL EXCLUSION" in candy_text and "candystore-events" in pubsub_text:
        report.passed("candystore-deployment-mode", "standalone manifest declares legacy-profile mutual exclusion")
    else:
        report.fail("candystore-deployment-mode", "mutual-exclusion declaration or durable identity is missing")

    fleet = source / "holocene/apps/api/src/fleet.ts"
    if not fleet.is_file():
        report.fail("holocene-candystore-url", f"missing {fleet}; the default history URL cannot be checked")
    elif re.search(r"https?://candystore:8080", fleet.read_text(encoding="utf-8")):
        report.fail("holocene-candystore-url", "default URL contradicts standalone Candystore port/topology")
    else:
        report.passed("holocene-candystore-url", "default history URL no longer uses candystore:8080")

    check_generated_routing(source, report)


def check_generated_routing(source: Path, report: Reporter) -> None:
    """Fail if any generated agent scaffold embeds a routing identifier in a subject.

    Absence is never a pass. This check previously read one file that had already
    been deleted, so its regex searched an empty string and reported green while
    guarding nothing.
    """
    roots = [source / rel for rel in GENERATED_SCAFFOLDS]
    present = [root for root in roots if root.is_dir()]
    if not present:
        report.fail(
            "pjangler-bloodbank-routing",
            "no generated runtime scaffold exists to scan (looked for "
            + ", ".join(GENERATED_SCAFFOLDS)
            + "); the check has no target and is guarding nothing",
        )
        return

    hits = []
    for root in present:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            match = ROUTING_IDENTIFIER_SUBJECT.search(content)
            if match:
                hits.append(f"{path.relative_to(source)} -> {match.group(0)}")

    if hits:
        report.fail(
            "pjangler-bloodbank-routing",
            "generated subjects embed repo/agent routing identifiers: " + "; ".join(hits),
        )
    else:
        report.passed(
            "pjangler-bloodbank-routing",
            f"{len(present)} generated scaffolds carry no identifier-embedding subjects",
        )


def check_compose_candidate(source: Path, docs_checkout: Path, report: Reporter) -> None:
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
    if result.returncode:
        report.fail("root-compose", detail or f"candidate validator exited {result.returncode}")
    else:
        report.passed("root-compose", detail)


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
        report.passed("doc-markers", f"no forbidden incomplete markers in {len(markdown)} Markdown files")
    if broken:
        report.fail("doc-links", "broken internal links: " + "; ".join(broken))
    else:
        report.passed("doc-links", "all Markdown file links resolve")


def parse_args() -> argparse.Namespace:
    script_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=script_root, help="live source checkout")
    parser.add_argument("--docs-root", type=Path, default=script_root, help="checkout containing root docs/config")
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
