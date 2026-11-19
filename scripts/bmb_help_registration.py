#!/usr/bin/env python3
"""Apply the project-local BMB help correction to generated and consumed catalogs.

The upstream BMB asset and builder skills are read-only. No installer cleanup occurs.
Run with --check to detect drift, or --apply after making a backup of live CSVs.
"""
import argparse
import csv
import io
import json
from pathlib import Path

MODULE = "BMad Builder"
TARGETS = ("_bmad/module-help.csv", "_bmad/_config/bmad-help.csv")
OVERLAY = Path(__file__).with_name("bmb-help-overlay.csv")
ROUTES = {
    "SB": ("bmad-bmb-setup", "configure", "scripts/merge-config.py"),
    "BA": ("bmad-agent-builder", "build-process", "references/build-process.md"),
    "AA": ("bmad-agent-builder", "quality-analysis", "references/quality-analysis.md"),
    "BW": ("bmad-workflow-builder", "build-process", "references/build-process.md"),
    "AW": ("bmad-workflow-builder", "scan-orchestration", "references/scan-orchestration.md"),
    "IM": ("bmad-module-builder", "ideate-module", "references/ideate-module.md"),
    "CM": ("bmad-module-builder", "create-module", "references/create-module.md"),
    "VM": ("bmad-module-builder", "validate-module", "references/validate-module.md"),
}
# The installed module builder dispatches -H to Create even when Validate is requested.
ARGS = {
    "SB": "{--headless: skip prompts}|{inline values: skip prompts with provided values}",
    "BA": "{-H: headless mode}|{description: initial agent concept}|{path: existing agent to edit or rebuild}",
    "AA": "{-H: headless mode}|{path: agent to analyze}",
    "BW": "{-H: headless mode}|{description: initial skill concept}|{path: existing skill to edit}",
    "AW": "{-H: headless mode}|{path: skill to analyze}",
    "IM": "{description: initial module idea}",
    "CM": "{-H: headless mode}|{path: skills folder or single SKILL.md}",
    "VM": "{path: module or skill to validate}",
}


def parsed(text):
    return list(csv.reader(io.StringIO(text)))


def validate(skills_dir, overlay):
    rows = parsed(overlay)
    assert len(rows) == len(ROUTES) + 2, "overlay must advertise exactly eight actions plus metadata"
    assert len(rows[0]) == 13, "unexpected catalog schema"
    assert rows[1][0:2] == [MODULE, "_meta"] and len(rows[1]) == 13, "missing BMB documentation metadata"
    codes = set()
    for row in rows[2:]:
        assert len(row) == 13 and row[0] == MODULE, "bad overlay row"
        code = row[3]
        assert code in ROUTES and code not in codes, "unsupported or duplicate menu code"
        codes.add(code)
        skill, action, reference = ROUTES[code]
        assert (row[1], row[5], row[6]) == (skill, action, ARGS[code]), f"bad route or args: {code}"
        base = skills_dir / skill
        skill_text = (base / "SKILL.md").read_text()
        assert action in skill_text and reference in skill_text, f"missing intent route: {code}"
        assert (base / reference).is_file(), f"missing installed reference: {code}"
        if "{-H: headless mode}" in row[6]:
            assert "-H" in skill_text, f"missing installed headless route: {code}"
    assert "If `--headless` or `-H` is passed, route to CM" in (
        skills_dir / "bmad-module-builder/SKILL.md"
    ).read_text(), "module builder headless dispatch needs revalidation"
    # Explicitly exclude the historical conversion promise/--convert route.
    assert "convert-process" not in overlay and "--convert" not in overlay


def corrected(text, overlay):
    # The installed catalogs have physical one-line CSV records. Refuse to
    # reserialize foreign rows: their original bytes and order are retained.
    lines = text.splitlines(keepends=True)
    rows = parsed(text)
    assert len(rows) == len(lines) and rows, "multiline or empty catalog is not supported"
    assert rows[0] == parsed(overlay)[0], "catalog schema differs from overlay"
    assert all(len(row) == len(rows[0]) for row in rows), "malformed catalog row"
    newline = "\r\n" if "\r\n" in lines[0] else "\n"
    bmb = [line + newline for line in overlay.splitlines()[1:]]
    output = [lines[0]]
    inserted = False
    for line, row in zip(lines[1:], rows[1:]):
        if row[0] == MODULE:
            if not inserted:
                output.extend(bmb)
                inserted = True
        else:
            output.append(line)
    if not inserted:
        # A final foreign record without a terminator must remain the exact EOF
        # record; appending to it would concatenate two CSV rows.
        if output[-1].endswith(("\r\n", "\n")):
            output.extend(bmb)
        else:
            assert len(output) > 1 and output[-2].endswith(("\r\n", "\n")), (
                "cannot insert before an unterminated header"
            )
            output[-1:-1] = bmb
    return "".join(output)


def run(root, apply, skills_dir):
    overlay = OVERLAY.read_text()
    validate(skills_dir, overlay)
    changes = {}
    pending = {}
    for name in TARGETS:
        path = root / name
        assert path.is_file() and not path.is_symlink(), f"missing or linked target: {path}"
        before = path.read_bytes()
        after = corrected(before.decode("utf-8"), overlay).encode("utf-8")
        changes[name] = before != after
        pending[name] = after
    if apply:
        for name in TARGETS:
            if changes[name]:
                (root / name).write_bytes(pending[name])
    print(json.dumps({"changed": changes, "applied": apply}, sort_keys=True))
    return 1 if not apply and any(changes.values()) else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--skills-dir", type=Path, help="Installed skill directory (defaults to project .agents/skills)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        skills_dir = args.skills_dir or args.project_root / ".agents/skills"
        raise SystemExit(run(args.project_root.resolve(), args.apply, skills_dir))
    except (AssertionError, OSError, ValueError) as exc:
        parser.exit(2, f"BMB registration refused: {exc}\n")
