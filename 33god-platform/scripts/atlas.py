#!/usr/bin/env python3
"""The Atlas: one map of every 33GOD component, rendered from the registry (I-12).

The registry is 33god-platform/components/*.yaml plus the `domains` and `people`
sections of components.yaml. Everything under 33god-platform/atlas/ that this
script writes is generated: edit the registry, then `atlas.py render`.

    atlas.py check    validate records and fail if rendered views are stale
    atlas.py render   write atlas.json, c4.dsl, c4-containers.mmd, index.html
"""
from __future__ import annotations

import argparse
import hashlib
import json
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

KINDS = {"service", "cli", "library", "agent", "datastore", "ui", "bus", "scheduler",
         "gateway", "contract", "feature", "external"}
LEVELS = {"software-system", "container", "component"}
STATUSES = {"live", "built-not-running", "partial", "planned", "retired"}
RELATION_KINDS = {"publishes-to", "consumes-from", "calls", "stores-in", "schedules", "hosts",
                  "reads", "writes", "renders", "routes-llm-via", "deploys", "wraps"}
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
    for p in cfg.get("people", []):
        for target in p.get("uses", []):
            if target not in ids:
                errors.append(f"person {p['id']}: uses unknown id {target!r}")
    for d in cfg.get("domains", []):
        if d["id"] in ids:
            errors.append(f"domain {d['id']}: collides with a component id")
    del people
    return errors


def digest(cfg: dict[str, Any], records: list[dict[str, Any]]) -> str:
    payload = {"domains": cfg.get("domains", []), "people": cfg.get("people", []), "records": records}
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


def q(text: str) -> str:
    return '"' + str(text).replace("\\", "\\\\").replace('"', "'") + '"'


def ident(component_id: str) -> str:
    return "c_" + component_id.replace("-", "_").replace(".", "_")


def render_dsl(doc: dict[str, Any], records: list[dict[str, Any]]) -> str:
    by_parent: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_parent.setdefault(r["parent"] if r["level"] == "component" else "", []).append(r)
    lines = ["# GENERATED by 33god-platform/scripts/atlas.py from the component registry. Do not edit.",
             "workspace \"33GOD\" \"One map of every component (I-12)\" {", "  model {"]
    for p in doc["people"]:
        lines.append(f"    {ident(p['id'])} = person {q(p['name'])} {q(p['summary'])}")
    externals = [r for r in records if not r["first_party"] and r["level"] != "component"]
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
    }


def cmd_render(_: argparse.Namespace) -> int:
    cfg, records = load_atlas()
    errors = validate(cfg, records)
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
    errors = validate(cfg, records)
    if not errors:
        for path, text in outputs(cfg, records).items():
            if not path.exists() or path.read_text() != text:
                errors.append(f"{path.relative_to(ROOT)} is stale; run: mise run platform:atlas")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"atlas OK: {len(records)} components")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("render").set_defaults(func=cmd_render)
    sub.add_parser("check").set_defaults(func=cmd_check)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
