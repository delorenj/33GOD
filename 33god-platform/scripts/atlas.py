#!/usr/bin/env python3
"""The Atlas: one map of every 33GOD component, rendered from the registry (I-12).

The registry is 33god-platform/components/*.yaml plus the `domains` and `people`
sections of components.yaml. Everything under 33god-platform/atlas/ that this
script writes is generated: edit the registry, then `atlas.py render`.

    atlas.py check    validate records and fail if rendered views are stale
    atlas.py render   write atlas.json, c4.dsl, c4-containers.mmd, index.html, public.json and
                      the Factory cast (manual/sandbox/src/cast.generated.json)
    atlas.py audit    compare the registry with reality (evidence, coverage, status);
                      --live adds systemd, containers and bus producers; --heal fixes
                      moved evidence lines and re-renders
    atlas.py anchor   record each relation's cited source line as its anchor
    atlas.py hubs     join `skillex graph` to the registry: each component's hub skill and its
                      health, written with the graph page to atlas/hubs/ (live state, untracked;
                      --publish puts the bundle on MinIO)

public.json is the ONLY input a public showcase page may read: it drops runtime,
role_in_system, evidence, notes and every wire's mechanism (via) and evidence,
and the scrub lint fails the build if anything internal is left in it.

The Factory cast says where every component stands on the 3D Factory floor. It comes from each
record's `factory:` block (exactly one of `station:` or `near:`, plus optional `aliases:`) and the
`factory_extras` mapping in components.yaml (ids that are not registry components, such as vendor
CLIs). It is served publicly inside the Factory bundle, so it carries only scrubbed public fields.
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
FACTORY_SRC = ROOT / "manual" / "sandbox" / "src"
STATIONS_TS = FACTORY_SRC / "waybill" / "stations.ts"  # the one place the Factory's SetId list lives
OUT_CAST = FACTORY_SRC / "cast.generated.json"
CAST_FORMAT = "33god.factory-cast"

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
        "factory": component.get("factory") or {},
        "_path": component.get("_path"),
    }


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def set_ids() -> list[str]:
    """The Factory's SetIds, read from `export type SetId = ...` in stations.ts so there is one list."""
    try:
        text = STATIONS_TS.read_text()
    except OSError:
        return []
    m = re.search(r"export type SetId\s*=((?:\s*\|?\s*'[a-z]+')+)", text)
    return re.findall(r"'([a-z]+)'", m.group(1)) if m else []


def placement_errors(where: str, block: Any, sets: list[str]) -> list[str]:
    """`station` / `near`: exactly one, and a known SetId."""
    if not isinstance(block, dict):
        return [f"{where}: factory must be a mapping with station: or near:"]
    errors = []
    given = [k for k in ("station", "near") if block.get(k) not in (None, "")]
    if len(given) != 1:
        errors.append(f"{where}: factory needs exactly one of station / near (has {given or 'neither'})")
    for k in given:
        if block[k] not in sets:
            errors.append(f"{where}: factory.{k} {block[k]!r} is not a Factory set ({' '.join(sets)})")
    return errors


def factory_errors(cfg: dict[str, Any], records: list[dict[str, Any]]) -> list[str]:
    sets = set_ids()
    if not sets:
        return [f"{STATIONS_TS.relative_to(ROOT)}: no `export type SetId = ...` found; the cast needs the Factory's station list"]
    errors: list[str] = []
    ids = {r["id"] for r in records}
    extras = cfg.get("factory_extras") or {}
    claimed: dict[str, str] = {}
    for r in records:
        where = f"component {r['id']}"
        block = r["factory"]
        if not block:
            errors.append(f"{where}: no factory: block (every component stands somewhere on the Factory floor)")
            continue
        errors += placement_errors(where, block, sets)
        for key in block:
            if key not in ("station", "near", "aliases"):
                errors.append(f"{where}: factory.{key} is not a known key (station, near, aliases)")
        aliases = block.get("aliases") or []
        if not isinstance(aliases, list) or not all(isinstance(a, str) and a for a in aliases):
            errors.append(f"{where}: factory.aliases must be a list of ids")
            continue
        for a in aliases:
            if a in ids:
                errors.append(f"{where}: alias {a!r} is a registry id")
            elif a in extras:
                errors.append(f"{where}: alias {a!r} collides with a factory_extras id")
            elif a in claimed:
                errors.append(f"{where}: alias {a!r} is already an alias of {claimed[a]}")
            claimed.setdefault(a, r["id"])
    if not isinstance(extras, dict):
        return errors + ["components.yaml: factory_extras must be a mapping of id -> {station|near, name}"]
    for eid, block in extras.items():
        where = f"factory_extras {eid}"
        if eid in ids:
            errors.append(f"{where}: collides with a registry id; list it as an alias instead")
        errors += placement_errors(where, block, sets)
        if isinstance(block, dict) and not str(block.get("name", "")).strip():
            errors.append(f"{where}: name is empty")
    return errors


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
    errors += factory_errors(cfg, records)
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


def cast_document(cfg: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    """Where every component stands on the Factory floor. Sorted and deterministic."""
    components: dict[str, Any] = {}
    aliases: dict[str, str] = {}
    for r in records:
        f = r["factory"]
        components[r["id"]] = {
            "name": r["name"], "summary": r["summary"], "domain": r["domain"], "first_party": r["first_party"],
            "station": f.get("station") or None, "near": f.get("near") or None,
            "aliases": sorted(f.get("aliases") or []),
        }
        for a in f.get("aliases") or []:
            aliases[a] = r["id"]
    extras = {eid: {"station": b.get("station") or None, "near": b.get("near") or None, "name": str(b["name"])}
              for eid, b in sorted((cfg.get("factory_extras") or {}).items())}
    body = {"components": components, "aliases": dict(sorted(aliases.items())), "extras": extras}
    return {"format": CAST_FORMAT, "version": 1,
            "digest": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(), **body}


def cast_scrub_findings(cast: dict[str, Any]) -> list[str]:
    findings = []
    for cid, c in cast["components"].items():
        for k in ("name", "summary"):
            findings += [f"cast.components[{cid}].{k}: internal detail {m.group(0)!r}; reword it in the registry"
                         for m in SCRUB.finditer(str(c[k]))]
    for eid, e in cast["extras"].items():
        findings += [f"cast.extras[{eid}].name: internal detail {m.group(0)!r}" for m in SCRUB.finditer(e["name"])]
    return findings


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
        OUT_CAST: json.dumps(cast_document(cfg, records), indent=2, ensure_ascii=False) + "\n",
    }


def all_errors(cfg: dict[str, Any], records: list[dict[str, Any]]) -> list[str]:
    errors = validate(cfg, records)
    if not errors:
        errors = scrub_findings(showcase_document(atlas_document(cfg, records))) \
            + cast_scrub_findings(cast_document(cfg, records))
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
        print(f"wrote {rel(path)}")
    return 0


def cmd_check(_: argparse.Namespace) -> int:
    cfg, records = load_atlas()
    errors = all_errors(cfg, records)
    if not errors:
        for path, text in outputs(cfg, records).items():
            if not path.exists() or path.read_text() != text:
                errors.append(f"{rel(path)} is stale; run: mise run platform:atlas")
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
            add("stale-render", str(rel(path)), "rendered view is older than the registry")

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
                    report.setdefault("rerendered", []).append(str(rel(path)))
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


# --- Hubs: which skill hub each component owns, and its health (skillex graph) ---------------

HUBS_OUT = ATLAS / "hubs"
HUB_NODE_KINDS = {"hub", "vendored"}


def component_repos() -> dict[str, Path]:
    """Component id -> its repository directory. An empty repo means "no repository of its own"."""
    repos: dict[str, Path] = {}
    for component in load_components():
        raw = str(component.get("repo") or "").strip()
        if not raw:
            continue
        path = _platform.resolve_path(raw)
        if path.exists():
            repos[str(component["id"])] = path.resolve()
    return repos


def hubs_document(graph: dict[str, Any], records: list[dict[str, Any]], repos: dict[str, Path]) -> dict[str, Any]:
    """Join a skillex graph to the registry on repository directory (graph node `root`)."""
    nodes = graph["nodes"]
    by_id = {n["id"]: n for n in nodes}
    out: dict[str, list[dict[str, Any]]] = {}
    inc: dict[str, list[dict[str, Any]]] = {}
    for e in graph["edges"]:
        out.setdefault(e["from"], []).append(e)
        inc.setdefault(e["to"], []).append(e)
    by_root: dict[str, list[str]] = {}
    for cid, path in repos.items():
        by_root.setdefault(str(path), []).append(cid)
    parent = {r["id"]: r["parent"] for r in records}

    def names(edges: list[dict[str, Any]], key: str) -> list[str]:
        return sorted({by_id[e[key]]["name"] for e in edges if e[key] in by_id})

    rank = ["ok", "warning", "error"].index
    sources = {n["root"]: n for n in nodes if n["kind"] == "source" and n.get("root")}
    hubs: list[dict[str, Any]] = []
    components: dict[str, dict[str, Any]] = {}
    for n in nodes:
        if n["kind"] not in HUB_NODE_KINDS:
            continue
        # The repository's own findings (one hub per repo) belong on every hub it holds.
        src = sources.get(n.get("root") or "")
        own = list(n["findings"]) + [f for f in (src or {}).get("findings", []) if f["code"] != "E_HUB_COUNT"
                                     or not any(g["code"] == "E_HUB_COUNT" for g in n["findings"])]
        matched = sorted(by_root.get(n.get("root") or "", []))
        # A repo shared by a container and its parts (bloodbank) belongs to the container.
        primary = [c for c in matched if parent.get(c) not in matched] or matched
        hub = {
            "name": n["name"],
            "kind": n["kind"],
            "source": n.get("source"),
            "root": n.get("root"),
            "health": max([n["health"], (src or {}).get("health", "ok")], key=rank),
            "codes": sorted({f["code"] for f in own}),
            "findings": len(own),
            "subskills": [x.split("/", 1)[-1] for x in names([e for e in out.get(n["id"], []) if e["kind"] == "routes"], "to")],
            "loads": names([e for e in out.get(n["id"], []) if e["kind"] == "loads"], "to"),
            "loaded_by": names([e for e in inc.get(n["id"], []) if e["kind"] == "loads"], "from"),
            "components": primary,
        }
        hubs.append(hub)
        for cid in matched:
            components.setdefault(cid, {"hubs": []})["hubs"].append(n["name"])
    for cid, entry in components.items():
        src = sources.get(str(repos[cid]))
        entry["repo_hubs"] = (src or {}).get("hubs", entry["hubs"])
        entry["health"] = max((h["health"] for h in hubs if h["name"] in entry["hubs"]), key=rank, default="ok")
    first_party = {r["id"] for r in records if r["first_party"] and r["level"] != "component"}
    return {
        "schema": 1,
        "graph_page": "skills.html",
        "summary": graph["summary"],
        "hubs": sorted(hubs, key=lambda h: h["name"]),
        "components": dict(sorted(components.items())),
        "unjoined": sorted(h["name"] for h in hubs if not h["components"]),
        "no_hub": sorted(c for c in first_party if c in repos and c not in components),
    }


def render_hubs_html(doc: dict[str, Any], hubs: dict[str, Any]) -> str:
    marker = "/*HUBS_DATA*/null"
    html = render_html(doc)
    if marker not in html:
        raise SystemExit(f"{TEMPLATE}: missing {marker} placeholder")
    return html.replace(marker, json.dumps(hubs, ensure_ascii=False).replace("</", "<\\/"))


def cmd_hubs(args: argparse.Namespace) -> int:
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cmd = [*args.skillex.split(), "graph", "--json", "--html", str(out / "skills.html")]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        print(f"atlas hubs: {cmd[0]} not found (needs skillex >= 0.4.9)", file=sys.stderr)
        return 1
    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(f"atlas hubs: skillex graph gave no JSON (exit {proc.returncode}): {proc.stderr.strip()[-400:]}",
              file=sys.stderr)
        return 1
    graph = envelope.get("data")
    if not graph:
        print(f"atlas hubs: skillex graph failed: {envelope.get('findings')}", file=sys.stderr)
        return 1
    cfg, records = load_atlas()
    hubs = hubs_document(graph, records, component_repos())
    (out / "hubs.json").write_text(json.dumps(hubs, indent=2, ensure_ascii=False) + "\n")
    (out / "index.html").write_text(render_hubs_html(atlas_document(cfg, records), hubs))
    bad = [h for h in hubs["hubs"] if h["health"] != "ok"]
    print(f"atlas hubs: {len(hubs['hubs'])} hubs, {len(hubs['components'])} components joined, "
          f"{len(bad)} not ok, {len(hubs['no_hub'])} first-party without a hub -> {rel(out)}")
    if args.publish:
        publish = Path.home() / ".agents/skills/artifacts/scripts/publish.py"
        res = subprocess.run([sys.executable, str(publish), str(out), "--name", "atlas-hubs", "--project", "33god"],
                             capture_output=True, text=True)
        url = (res.stdout.strip().splitlines() or [""])[-1]
        if res.returncode != 0 or not url.startswith("https://"):
            print(f"atlas hubs: publish failed: {res.stderr.strip()[-400:]}", file=sys.stderr)
            return 1
        print(url)
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
    h = sub.add_parser("hubs", help="join skillex graph to the registry (live state, untracked)")
    h.add_argument("--out", default=str(HUBS_OUT), help="bundle directory (default atlas/hubs)")
    h.add_argument("--skillex", default="skillex", help="skillex command (default: skillex on PATH)")
    h.add_argument("--publish", action="store_true", help="publish the bundle with the artifacts skill")
    h.set_defaults(func=cmd_hubs)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
