#!/usr/bin/env python3
"""The Atlas: one map of every 33GOD component, rendered from the registry (I-12).

The registry is 33god-platform/components/*.yaml plus the `domains` and `people`
sections of components.yaml. Everything under 33god-platform/atlas/ that this
script writes is generated: edit the registry, then `atlas.py render`.

    atlas.py check    validate records and fail if rendered views are stale
    atlas.py render   write atlas.json, c4.dsl, c4-containers.mmd, index.html, public.json
    atlas.py audit    compare the registry with reality (evidence, coverage, status);
                      --live adds systemd, containers and bus producers; --heal fixes
                      moved evidence lines and re-renders
    atlas.py anchor   record each relation's cited source line as its anchor

public.json is the ONLY input a public showcase page may read: it drops runtime,
role_in_system, evidence, notes and every wire's mechanism (via) and evidence,
and the scrub lint fails the build if anything internal is left in it.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import importlib.util  # noqa: E402

# scripts/platform.py shares a name with the stdlib module, so load it by path.
_spec = importlib.util.spec_from_file_location("god_platform", Path(__file__).resolve().parent / "platform.py")
_platform = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_platform)
ROOT = _platform.ROOT
load_components = _platform.load_components
platform_config = _platform.platform_config

ATLAS = ROOT / "atlas"
TEMPLATE = ATLAS / "template.html"
OUT_JSON = ATLAS / "atlas.json"
OUT_DSL = ATLAS / "c4.dsl"
OUT_MMD = ATLAS / "c4-containers.mmd"
OUT_HTML = ATLAS / "index.html"
OUT_PUBLIC = ATLAS / "public.json"

KINDS = {"service", "cli", "library", "agent", "datastore", "ui", "bus", "scheduler",
         "gateway", "contract", "feature", "external"}
LEVELS = {"software-system", "container", "component"}
STATUSES = {"live", "built-not-running", "partial", "planned", "retired"}
DOMAIN_HUES = range(1, 14)  # atlas/template.html defines --d1..--d13 per theme
RELATION_KINDS = {"publishes-to", "consumes-from", "calls", "stores-in", "schedules", "hosts",
                  "reads", "writes", "renders", "routes-llm-via", "deploys", "wraps"}
# Fields a public showcase page may carry. Wires keep only from/to/kind.
SHOWCASE_FIELDS = ("id", "name", "kind", "first_party", "domain", "level", "parent", "status",
                   "summary", "tech", "public_card")
# Anything internal: hostnames, IPs, ports, home paths, file names, secret refs, the box, the owner.
SCRUB = re.compile(r"(?i)([a-z0-9-]+\.(?:delo\.sh|ts\.net|automaticai\.io|internal|lan)\b|"
                   r"\b\d{1,3}(?:\.\d{1,3}){3}\b|(?<![\w-]):\d{4,5}\b|localhost|/home/|~/|op://|"
                   r"\bbig-chungus\b|\bdelorenj\b|\bjarad\b|\b[\w-]+\.(?:py|ya?ml|json|toml|env|sh|mjs|ts)\b|"
                   r"\b(?:bloodbank|candybar)\.(?:evt|cmd|rpy)\.)")
SURFACE_KINDS = ("repo", "systemd", "container", "producer")
LIVE_KINDS = {"systemd", "container", "producer"}
PUBLIC_FIELDS = ("id", "name", "kind", "first_party", "domain", "level", "parent", "status",
                 "summary", "role_in_system", "tech", "runtime", "public_card")


def record(component: dict[str, Any]) -> dict[str, Any]:
    c4 = component.get("c4") or {}
    return {
        "id": str(component["id"]),
        "name": component.get("name", component["id"]),
        "kind": component.get("kind"),
        "first_party": component.get("first_party", True),
        "domain": component.get("domain"),
        "level": c4.get("level"),
        "parent": c4.get("parent") or "",
        "status": component.get("status"),
        "summary": component.get("summary") or component.get("description", ""),
        "role_in_system": component.get("role_in_system", ""),
        "tech": component.get("tech") or [],
        "runtime": component.get("runtime", ""),
        "public_card": component.get("public_card") or {},
        "relations": component.get("relations") or [],
        "evidence": component.get("evidence") or [],
        "notes": component.get("notes", ""),
        "surfaces": component.get("surfaces") or [],
        "_path": component.get("_path"),
    }


def load_atlas() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cfg = platform_config()
    records = sorted((record(c) for c in load_components()), key=lambda r: r["id"])
    return cfg, records


def validate(cfg: dict[str, Any], records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    domains = {d["id"] for d in cfg.get("domains", [])}
    ids = {r["id"] for r in records}
    people = {p["id"] for p in cfg.get("people", [])}
    if not domains:
        errors.append("components.yaml: no domains defined")
    for r in records:
        where = f"component {r['id']}"
        if r["kind"] not in KINDS:
            errors.append(f"{where}: kind {r['kind']!r} not in {sorted(KINDS)}")
        if r["domain"] not in domains:
            errors.append(f"{where}: domain {r['domain']!r} is not a declared domain")
        if r["level"] not in LEVELS:
            errors.append(f"{where}: c4.level {r['level']!r} not in {sorted(LEVELS)}")
        if r["level"] == "component" and r["parent"] not in ids:
            errors.append(f"{where}: c4.parent {r['parent']!r} must name a known component")
        if r["parent"] and r["parent"] not in ids:
            errors.append(f"{where}: c4.parent {r['parent']!r} is unknown")
        if r["status"] not in STATUSES:
            errors.append(f"{where}: status {r['status']!r} not in {sorted(STATUSES)}")
        if not r["summary"]:
            errors.append(f"{where}: summary is empty")
        if not r["evidence"]:
            errors.append(f"{where}: evidence is empty; every record must be traceable")
        for rel in r["relations"]:
            target = rel.get("to")
            if target not in ids:
                errors.append(f"{where}: relation to unknown id {target!r}")
            if rel.get("kind") not in RELATION_KINDS:
                errors.append(f"{where}: relation kind {rel.get('kind')!r} not in {sorted(RELATION_KINDS)}")
            if not rel.get("via"):
                errors.append(f"{where}: relation to {target!r} names no mechanism (via)")
            if not rel.get("evidence"):
                errors.append(f"{where}: relation to {target!r} has no evidence")
        for surface in r["surfaces"]:
            if not isinstance(surface, str) or surface.split(":", 1)[0] not in SURFACE_KINDS or ":" not in surface:
                errors.append(f"{where}: surface {surface!r} must be <{'|'.join(SURFACE_KINDS)}>:<name or glob>")
    for p in cfg.get("people", []):
        for target in p.get("uses", []):
            if target not in ids:
                errors.append(f"person {p['id']}: uses unknown id {target!r}")
    for d in cfg.get("domains", []):
        if "hue" in d and d["hue"] not in DOMAIN_HUES:
            errors.append(f"domain {d['id']}: hue {d['hue']!r} must be 1-13 (a --d<n> token in atlas/template.html)")
        if d["id"] in ids:
            errors.append(f"domain {d['id']}: collides with a component id")
    del people
    return errors


def digest(cfg: dict[str, Any], records: list[dict[str, Any]]) -> str:
    clean = [{k: v for k, v in r.items() if k != "_path"} for r in records]
    payload = {"domains": cfg.get("domains", []), "people": cfg.get("people", []), "records": clean}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def atlas_document(cfg: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    edges = []
    for r in records:
        for rel in r["relations"]:
            edges.append({"from": r["id"], "to": rel["to"], "kind": rel["kind"], "via": rel["via"]})
    return {
        "schema": 1,
        "registry_digest": digest(cfg, records),
        "system": {"id": "33god", "name": "33GOD", "summary": cfg.get("product", {}).get("summary", "").strip()},
        "domains": cfg.get("domains", []),
        "people": cfg.get("people", []),
        "components": [{k: r[k] for k in PUBLIC_FIELDS} for r in records],
        "edges": edges,
        "counts": {
            "components": len(records),
            "first_party": sum(1 for r in records if r["first_party"]),
            "external": sum(1 for r in records if not r["first_party"]),
            "live": sum(1 for r in records if r["status"] == "live"),
            "edges": len(edges),
        },
    }


def showcase_document(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": 1,
        "note": "Scrubbed Atlas export for public showcase pages. Generated; do not edit.",
        "registry_digest": doc["registry_digest"],
        "system": doc["system"],
        "domains": [{k: d[k] for k in ("id", "name") if k in d} for d in doc["domains"]],
        "people": [{k: p[k] for k in ("id", "name", "summary", "uses") if k in p} for p in doc["people"]],
        "components": [{k: c[k] for k in SHOWCASE_FIELDS} for c in doc["components"]],
        "edges": [{"from": e["from"], "to": e["to"], "kind": e["kind"]} for e in doc["edges"]],
    }


def scrub_findings(public: dict[str, Any]) -> list[str]:
    findings = []

    def walk(value: Any, where: str) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, f"{where}.{k}")
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, f"{where}[{i}]")
        elif isinstance(value, str):
            for m in SCRUB.finditer(value):
                findings.append(f"public.json{where}: internal detail {m.group(0)!r}; reword it in the registry")

    for c in public["components"]:
        walk({k: c[k] for k in ("name", "summary", "tech", "public_card")}, f"[{c['id']}]")
    walk(public["people"], ".people")
    walk(public["system"], ".system")
    return findings


def q(text: str) -> str:
    return '"' + str(text).replace("\\", "\\\\").replace('"', "'") + '"'


def ident(component_id: str) -> str:
    return "c_" + component_id.replace("-", "_").replace(".", "_")


def render_dsl(doc: dict[str, Any], records: list[dict[str, Any]]) -> str:
    first = {r["id"] for r in records if r["first_party"]}
    # Structurizr nests components only inside first-party containers; a part of an
    # outside system (e.g. our n8n workflows) is drawn as a container of its own.
    nested = lambda r: r["level"] == "component" and r["parent"] in first
    by_parent: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_parent.setdefault(r["parent"] if nested(r) else "", []).append(r)
    lines = ["# GENERATED by 33god-platform/scripts/atlas.py from the component registry. Do not edit.",
             "workspace \"33GOD\" \"One map of every component (I-12)\" {", "  model {"]
    for p in doc["people"]:
        lines.append(f"    {ident(p['id'])} = person {q(p['name'])} {q(p['summary'])}")
    externals = [r for r in by_parent.get("", []) if not r["first_party"]]
    for r in externals:
        lines.append(f"    {ident(r['id'])} = softwareSystem {q(r['name'])} {q(r['summary'])} {{ tags \"External\" }}")
    lines.append(f"    god = softwareSystem \"33GOD\" {q(doc['system']['summary'])} {{")
    for d in doc["domains"]:
        members = [r for r in by_parent.get("", []) if r["first_party"] and r["domain"] == d["id"]]
        if not members:
            continue
        lines.append(f"      group {q(d['name'])} {{")
        for r in members:
            tech = ", ".join(r["tech"][:3])
            lines.append(f"        {ident(r['id'])} = container {q(r['name'])} {q(r['summary'])} {q(tech)} {{")
            for child in by_parent.get(r["id"], []):
                ctech = ", ".join(child["tech"][:3])
                lines.append(f"          {ident(child['id'])} = component {q(child['name'])} {q(child['summary'])} {q(ctech)}")
            lines.append("        }")
        lines.append("      }")
    lines.append("    }")
    for p in doc["people"]:
        for target in p.get("uses", []):
            lines.append(f"    {ident(p['id'])} -> {ident(target)} \"uses\"")
    for e in doc["edges"]:
        lines.append(f"    {ident(e['from'])} -> {ident(e['to'])} {q(e['kind'])} {q(e['via'])}")
    lines += ["  }", "  views {",
              "    systemContext god \"context\" { include * autoLayout }",
              "    container god \"containers\" { include * autoLayout lr }"]
    for r in records:
        if by_parent.get(r["id"]) and r["level"] == "container":
            lines.append(f"    component {ident(r['id'])} {q('components-' + r['id'])} {{ include * autoLayout }}")
    lines += ["    styles {",
              "      element \"External\" { background #8a8f98 }",
              "      element \"Person\" { shape person }",
              "    }", "  }", "}"]
    return "\n".join(lines) + "\n"


def render_mermaid(doc: dict[str, Any], records: list[dict[str, Any]]) -> str:
    lines = ["%% GENERATED by 33god-platform/scripts/atlas.py from the component registry. Do not edit.",
             "flowchart LR"]
    for d in doc["domains"]:
        members = [r for r in records if r["domain"] == d["id"] and r["level"] != "component"]
        if not members:
            continue
        lines.append(f"  subgraph {d['id']}[{q(d['name'])}]")
        for r in members:
            lines.append(f"    {ident(r['id'])}[{q(r['name'])}]")
        lines.append("  end")
    containers = {r["id"]: r for r in records}
    seen = set()
    for e in doc["edges"]:
        src = containers.get(e["from"])
        dst = containers.get(e["to"])
        if not src or not dst:
            continue
        a = src["parent"] if src["level"] == "component" and src["parent"] else src["id"]
        b = dst["parent"] if dst["level"] == "component" and dst["parent"] else dst["id"]
        if a == b or (a, b, e["kind"]) in seen:
            continue
        seen.add((a, b, e["kind"]))
        lines.append(f"  {ident(a)} -->|{e['kind']}| {ident(b)}")
    return "\n".join(lines) + "\n"


def render_html(doc: dict[str, Any]) -> str:
    template = TEMPLATE.read_text()
    marker = "/*ATLAS_DATA*/null"
    if marker not in template:
        raise SystemExit(f"{TEMPLATE}: missing {marker} placeholder")
    data = json.dumps(doc, ensure_ascii=False).replace("</", "<\\/")
    return template.replace(marker, data)


def outputs(cfg: dict[str, Any], records: list[dict[str, Any]]) -> dict[Path, str]:
    doc = atlas_document(cfg, records)
    return {
        OUT_JSON: json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
        OUT_DSL: render_dsl(doc, records),
        OUT_MMD: render_mermaid(doc, records),
        OUT_HTML: render_html(doc),
        OUT_PUBLIC: json.dumps(showcase_document(doc), indent=2, ensure_ascii=False) + "\n",
    }


def all_errors(cfg: dict[str, Any], records: list[dict[str, Any]]) -> list[str]:
    errors = validate(cfg, records)
    if not errors:
        errors = scrub_findings(showcase_document(atlas_document(cfg, records)))
    return errors


def cmd_render(_: argparse.Namespace) -> int:
    cfg, records = load_atlas()
    errors = all_errors(cfg, records)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        print(f"atlas: {len(errors)} registry error(s); nothing rendered", file=sys.stderr)
        return 1
    for path, text in outputs(cfg, records).items():
        path.write_text(text)
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


def cmd_check(_: argparse.Namespace) -> int:
    cfg, records = load_atlas()
    errors = all_errors(cfg, records)
    if not errors:
        for path, text in outputs(cfg, records).items():
            if not path.exists() or path.read_text() != text:
                errors.append(f"{path.relative_to(ROOT)} is stale; run: mise run platform:atlas")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"atlas OK: {len(records)} components")
    return 0


# --- Drift audit: does the registry still match reality? -------------------------------------

SOURCE_ROOT = ROOT.parent  # evidence paths are relative to the 33GOD checkout
EVIDENCE = re.compile(r"^(?P<path>[~/\w.@+-][^\s:]*)(?::(?P<line>\d+)(?:-\d+)?)?$")
SECRETISH = re.compile(r"(?i)(sk-[a-z0-9]{8}|token\s*[=:]\s*['\"][^'\"]{8}|password\s*[=:]\s*['\"][^'\"]+|"
                       r"-----BEGIN|api[_-]?key\s*[=:]\s*['\"][^'\"]{8})")


def evidence_path(text: str) -> tuple[Path | None, int | None]:
    m = EVIDENCE.match(str(text).strip())
    if not m:
        return None, None
    raw = m.group("path")
    path = Path(os.path.expanduser(raw)) if raw.startswith(("~", "/")) else SOURCE_ROOT / raw
    return path, int(m.group("line")) if m.group("line") else None


def read_lines(path: Path) -> list[str] | None:
    try:
        return path.read_text(errors="replace").splitlines()
    except OSError:
        return None


def anchor_for(line: str) -> str | None:
    text = " ".join(line.split())
    if len(text) < 8 or SECRETISH.search(text):
        return None
    return text[:160]


def check_relation_evidence(rec: dict[str, Any], rel: dict[str, Any]) -> tuple[str, str, int | None]:
    """(state, detail, healed_line). state: ok | moved | gone | unverifiable."""
    ev = str(rel.get("evidence", ""))
    if ev.startswith("live:"):
        return "ok", "", None
    path, line = evidence_path(ev)
    if path is None:
        return "unverifiable", f"evidence {ev!r} is not a path[:line] or 'live: <probe>'", None
    if path.is_dir():
        return "ok", "", None
    lines = read_lines(path)
    if lines is None:
        return "gone", f"evidence file {ev} no longer exists", None
    if line and line > len(lines):
        return "gone", f"evidence {ev} points past the end of the file ({len(lines)} lines)", None
    anchor = rel.get("anchor")
    if not anchor or not line:
        return "ok", "", None
    norm = [" ".join(x.split()) for x in lines]
    if norm[line - 1].startswith(anchor):
        return "ok", "", None
    hits = [i + 1 for i, x in enumerate(norm) if x.startswith(anchor)]
    if not hits:
        return "gone", f"anchor no longer in {path.name}: {anchor[:70]!r}; re-verify the wire", None
    best = min(hits, key=lambda i: abs(i - line))
    return "moved", f"{ev} -> line {best}", best


def discover(live: bool) -> tuple[dict[str, set[str]], list[str]]:
    found: dict[str, set[str]] = {k: set() for k in SURFACE_KINDS}
    problems: list[str] = []
    gm = SOURCE_ROOT / ".gitmodules"
    if gm.exists():
        out = subprocess.run(["git", "config", "-f", str(gm), "--get-regexp", r"\.path$"],
                             capture_output=True, text=True)
        found["repo"] |= {line.split()[1] for line in out.stdout.splitlines() if line.strip()}
    services = SOURCE_ROOT / "bloodbank" / "services"
    if services.is_dir():
        found["repo"] |= {f"bloodbank/services/{d.name}" for d in services.iterdir()
                          if d.is_dir() and not d.name.startswith((".", "_"))}
    if not live:
        return found, problems
    probes = {
        "systemd": ["systemctl", "--user", "list-units", "--type=service", "--state=running",
                    "--no-legend", "--plain"],
        "container": ["docker", "ps", "--format", "{{.Names}}"],
        "producer": ["docker", "exec", "candystore-postgres", "sh", "-c",
                     "psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -Atc \"select distinct producer from events "
                     "where time > now() - interval '7 days' and producer is not null\""],
    }
    for kind, argv in probes.items():
        try:
            out = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as exc:
            problems.append(f"probe {kind} failed: {exc}")
            continue
        if out.returncode != 0:
            problems.append(f"probe {kind} failed: {out.stderr.strip()[:200]}")
            continue
        for line in out.stdout.splitlines():
            name = line.split()[0] if line.split() else ""
            if name:
                found[kind].add(name)
    return found, problems


def claims_of(surfaces: list[str], kind: str) -> list[str]:
    return [s.split(":", 1)[1] for s in surfaces if s.split(":", 1)[0] == kind]


def audit(cfg: dict[str, Any], records: list[dict[str, Any]], live: bool) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    heals: list[tuple[dict[str, Any], int, int]] = []

    def add(kind: str, subject: str, detail: str) -> None:
        findings.append({"kind": kind, "subject": subject, "detail": detail})

    for err in all_errors(cfg, records):
        add("registry", "atlas", err)
    for path, text in outputs(cfg, records).items():
        if not path.exists() or path.read_text() != text:
            add("stale-render", str(path.relative_to(ROOT)), "rendered view is older than the registry")

    for r in records:
        for i, rel in enumerate(r["relations"]):
            state, detail, healed = check_relation_evidence(r, rel)
            subject = f"{r['id']} --{rel.get('kind')}--> {rel.get('to')}"
            if state == "moved":
                heals.append((r, i, healed))
                add("evidence-moved", subject, detail)
            elif state in ("gone", "unverifiable"):
                add(f"evidence-{state}", subject, detail)
        for ev in r["evidence"]:
            path, _ = evidence_path(str(ev))
            if path is not None and str(ev).startswith(("/", "~", "33god-platform/", "bloodbank/")) \
                    and not path.exists():
                add("evidence-gone", r["id"], f"component evidence {ev} no longer exists")

    found, problems = discover(live)
    for p in problems:
        add("probe", "audit", p)
    ignores = cfg.get("atlas_ignore", [])
    for kind, names in found.items():
        for name in sorted(names):
            owners = [r["id"] for r in records
                      if any(fnmatch.fnmatchcase(name, pat) for pat in claims_of(r["surfaces"], kind))]
            if owners:
                continue
            if any(i.get("kind") == kind and fnmatch.fnmatchcase(name, i["pattern"]) for i in ignores):
                continue
            add("unregistered", f"{kind}:{name}",
                "no component claims it; add it to a component's surfaces, a new record, or atlas_ignore")
    if live:
        for r in records:
            live_claims = [s for s in r["surfaces"] if s.split(":", 1)[0] in LIVE_KINDS]
            if not live_claims:
                continue
            seen = [s for s in live_claims
                    if any(fnmatch.fnmatchcase(n, s.split(":", 1)[1]) for n in found[s.split(":", 1)[0]])]
            if r["status"] == "live" and not seen:
                add("status", r["id"], f"status live, but none of {live_claims} was observed")
            elif r["status"] in ("built-not-running", "planned", "retired") and seen:
                add("status", r["id"], f"status {r['status']}, but {seen} is running")

    keys = sorted(f"{f['kind']}|{f['subject']}" for f in findings if f["kind"] not in ("evidence-moved", "stale-render"))
    return {
        "live": live,
        "components": len(records),
        "surfaces_seen": {k: len(v) for k, v in found.items()},
        "findings": findings,
        "needs_human": len(keys),
        "digest": hashlib.sha256("\n".join(keys).encode()).hexdigest()[:12],
        "_heals": heals,
    }


def write_relations(path: Path, relations: list[dict[str, Any]]) -> None:
    """Splice a new top-level relations block into a record, keeping its comments."""
    import yaml
    text = path.read_text()
    block = yaml.safe_dump({"relations": relations}, sort_keys=False, allow_unicode=True, width=1000)
    pat = re.compile(r"^relations:.*?(?=^[A-Za-z_#][^\n]*|\Z)", re.S | re.M)
    text = pat.sub(lambda _: block, text, count=1) if pat.search(text) else text.rstrip("\n") + "\n" + block
    path.write_text(text)
    if (yaml.safe_load(path.read_text()).get("relations") or []) != relations:
        raise SystemExit(f"{path}: relations splice did not round-trip")


def cmd_audit(args: argparse.Namespace) -> int:
    cfg, records = load_atlas()
    report = audit(cfg, records, args.live)
    heals = report.pop("_heals")
    if args.heal and heals:
        by_path: dict[Path, list[tuple[int, int]]] = {}
        for r, i, line in heals:
            by_path.setdefault(Path(r["_path"]), []).append((i, line))
        for path, fixes in by_path.items():
            rels = next(r for r in records if Path(r["_path"]) == path)["relations"]
            for i, line in fixes:
                ev = str(rels[i]["evidence"])
                rels[i]["evidence"] = re.sub(r":\d+(-\d+)?$", f":{line}", ev)
            write_relations(path, rels)
        report["healed"] = len(heals)
    if args.heal:
        cfg, records = load_atlas()
        if not validate(cfg, records):
            for path, text in outputs(cfg, records).items():
                if not path.exists() or path.read_text() != text:
                    path.write_text(text)
                    report.setdefault("rerendered", []).append(str(path.relative_to(ROOT)))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for f in report["findings"]:
            print(f"{f['kind']:<20} {f['subject']:<48} {f['detail']}")
        print(f"\naudit: {len(report['findings'])} finding(s), {report['needs_human']} need a person "
              f"(digest {report['digest']}); healed {report.get('healed', 0)}")
    return 1 if report["needs_human"] else 0


def cmd_anchor(args: argparse.Namespace) -> int:
    cfg, records = load_atlas()
    total = 0
    for r in records:
        changed = False
        for rel in r["relations"]:
            if rel.get("anchor") and not args.refresh:
                continue
            path, line = evidence_path(str(rel.get("evidence", "")))
            if not path or not line or not path.is_file():
                continue
            lines = read_lines(path) or []
            if line > len(lines):
                continue
            anchor = anchor_for(lines[line - 1])
            if anchor and rel.get("anchor") != anchor:
                rel["anchor"] = anchor
                changed = True
                total += 1
        if changed:
            write_relations(Path(r["_path"]), r["relations"])
    print(f"anchored {total} relation(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("render").set_defaults(func=cmd_render)
    sub.add_parser("check").set_defaults(func=cmd_check)
    a = sub.add_parser("audit")
    a.add_argument("--live", action="store_true", help="also probe systemd, containers and bus producers")
    a.add_argument("--heal", action="store_true", help="fix moved evidence lines and re-render")
    a.add_argument("--json", action="store_true")
    a.set_defaults(func=cmd_audit)
    an = sub.add_parser("anchor")
    an.add_argument("--refresh", action="store_true", help="re-capture anchors that already exist")
    an.set_defaults(func=cmd_anchor)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
