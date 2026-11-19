#!/usr/bin/env python3
"""The Factory forge (I-10): pick one Atlas component a night, brief an agent, verify what it built.

The nightly `factory-forge` candybar runs scripts/factory-forge.sh, which drives these subcommands:

    factory_forge.py pick [--component ID] [--explain] [--json]   which component tonight, and why
    factory_forge.py prompt ID                                      the agent's brief for that component
    factory_forge.py snapshot --out FILE                            dirty-tree fingerprint, taken before the agent runs
    factory_forge.py verify ID [--baseline FILE] [--dist DIR]       independent post-run checks, JSON verdict
    factory_forge.py usage CLAUDE_JSON                              token totals from `claude -p --output-format json`
    factory_forge.py showcase ID --shots DIR --out DIR              the showcase page for a shipped asset
    factory_forge.py ledger add|show ...                            the run ledger (manual/sandbox/forge/ledger.json)

The contract is manual/sandbox/forge/CONTRACT.md. Nothing here trusts the agent: `verify` re-derives every
fact from the files, the build and a real browser.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

PLATFORM = Path(__file__).resolve().parents[1]
RUN_FORMAT = "%Y-%m-%dT%H:%M%z"
LEDGER_FORMAT = "33god.factory-forge-ledger"
SHIP_SCORE = 7                      # CONTRACT section 6: 7 to ship
CLIPS = ("idle", "accept", "work", "emit")
SOCKETS = ("in", "hold", "out")
HANDLES = {"parcel", "post", "env", "summary", "any"}
PLACEMENTS = {"station", "kiosk"}
NOTES_MIN_CHARS = 600
COOL_AFTER = 2                      # consecutive failed runs before a component steps back in the queue
STEP_TIMEOUT = 900


class Paths:
    """Every location the forge touches, derived from one platform root so tests can point it at a fixture."""

    def __init__(self, root: Path = PLATFORM):
        self.root = Path(root)

    @property
    def registry(self): return self.root / "components"
    @property
    def sandbox(self): return self.root / "manual" / "sandbox"
    @property
    def assets(self): return self.sandbox / "src" / "assets"
    @property
    def cast(self): return self.sandbox / "src" / "cast.generated.json"
    @property
    def stations_ts(self): return self.sandbox / "src" / "waybill" / "stations.ts"
    @property
    def forge(self): return self.sandbox / "forge"
    @property
    def ledger(self): return self.forge / "ledger.json"
    @property
    def nights(self): return self.root / "overnight" / "site" / "nights"
    @property
    def public_glb(self): return self.sandbox / "public" / "assets"
    @property
    def tools(self): return self.sandbox / "tools" / "forge"

    def asset_dir(self, cid: str) -> Path: return self.assets / cid
    def glb(self, cid: str) -> Path: return self.public_glb / cid / "model.glb"

    def repo_root(self) -> Path:
        out = _run(["git", "-C", str(self.root), "rev-parse", "--show-toplevel"])
        return Path(out.stdout.strip()) if out.returncode == 0 else self.root

    def scope_prefix(self, cid: str) -> str:
        return os.path.relpath(self.asset_dir(cid), self.repo_root()).replace(os.sep, "/") + "/"


def _run(argv, cwd=None, env=None, timeout=STEP_TIMEOUT) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        return subprocess.CompletedProcess(argv, 127, "", str(e))
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(argv, 124, e.stdout or "", f"timed out after {timeout}s")


def _tail(text: str, n: int = 12) -> str:
    return "\n".join((text or "").strip().splitlines()[-n:])


# ---- registry, cast, traffic -------------------------------------------------------------------------

def load_registry(p: Paths) -> dict[str, dict]:
    out = {}
    for f in sorted(p.registry.glob("*.yaml")):
        rec = yaml.safe_load(f.read_text()) or {}
        rec.setdefault("id", f.stem)
        out[rec["id"]] = rec
    return out


def _legacy_stations(p: Paths) -> dict[str, str]:
    """Fallback until cast.generated.json exists: the Factory's old hand table (STATION_OF in stations.ts)."""
    try:
        text = p.stations_ts.read_text()
    except OSError:
        return {}
    m = re.search(r"export const STATION_OF[^{]*\{(.*?)\n\}", text, re.S)
    return dict(re.findall(r"'([^']+)':\s*'([a-z]+)'", m.group(1))) if m else {}


def load_cast(p: Paths, registry: dict[str, dict]) -> tuple[dict[str, dict], str]:
    """id -> {station, near, ...} and the name of the source it came from."""
    if p.cast.exists():
        cast = json.loads(p.cast.read_text())
        return {i: c for i, c in cast.get("components", {}).items()}, "cast.generated.json"
    out, src = {}, "registry factory: blocks"
    legacy = None
    for cid, rec in registry.items():
        fb = rec.get("factory") or {}
        station, near = fb.get("station"), fb.get("near")
        if not station and not near:
            if legacy is None:
                legacy = _legacy_stations(p)
            station = legacy.get(cid)
            if station:
                src = "legacy stations.ts (no cast file yet)"
        out[cid] = {"station": station, "near": near}
    return out, src


def latest_traffic(p: Paths) -> tuple[dict[str, int], str]:
    """Events (plus credited work) per registry id in the newest night digest."""
    files = sorted(p.nights.glob("*.json")) if p.nights.exists() else []
    for f in reversed(files):
        try:
            d = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        rows = d.get("components") or []
        return {r["id"]: int(r.get("events", 0)) + int(r.get("credited", 0)) for r in rows if "id" in r}, f.stem
    return {}, "none"


def read_asset(p: Paths, cid: str) -> dict | None:
    f = p.asset_dir(cid) / "asset.json"
    try:
        return json.loads(f.read_text())
    except (OSError, ValueError):
        return None


def assets_present(p: Paths) -> dict[str, dict]:
    out = {}
    if p.assets.exists():
        for d in sorted(p.assets.iterdir()):
            a = read_asset(p, d.name) if d.is_dir() else None
            if a is not None:
                out[d.name] = a
    return out


# ---- pick ---------------------------------------------------------------------------------------------

def pick(p: Paths, component: str | None = None) -> dict:
    reg = load_registry(p)
    cast, cast_src = load_cast(p, reg)
    traffic, night = latest_traffic(p)
    have = assets_present(p)

    def station_of(cid):
        c = cast.get(cid) or {}
        return c.get("station")

    def reasons(cid):
        r = []
        if station_of(cid):
            r.append(f"station={station_of(cid)}")
        elif (cast.get(cid) or {}).get("near"):
            r.append(f"kiosk near {(cast.get(cid) or {})['near']}")
        t = traffic.get(cid, 0)
        r.append(f"{t} events in night {night}" if t else f"no traffic in night {night}")
        if reg[cid].get("first_party"):
            r.append("first-party")
        if cooling(cid):
            r.append(f"cooling off: its last {COOL_AFTER} forge runs failed")
        return r

    # one body per station (the runtime ignores a second): a station's other registry components stay unbuilt
    held = {station_of(i): i for i in have if station_of(i)}
    candidates = [c for c in reg if c not in have and not (station_of(c) and station_of(c) in held)]
    runs = ledger_read(p)["runs"]

    def cooling(cid):
        """Two failed runs in a row: let another component have tonight rather than burn the same tokens again."""
        last = [r.get("outcome") for r in runs if r.get("id") == cid and r.get("outcome") in ("shipped", "failed")][-COOL_AFTER:]
        return len(last) == COOL_AFTER and all(o == "failed" for o in last)

    mode = "build"
    if component:
        aliases = {a: i for i, c in cast.items() for a in c.get("aliases", [])}
        cid = component if component in reg else aliases.get(component)
        if cid is None:
            raise SystemExit(f"factory_forge: {component!r} is not an Atlas registry id")
        mode = "polish" if cid in have else "build"
        if mode == "build" and station_of(cid) and station_of(cid) in held:
            raise SystemExit(f"factory_forge: {cid} stands at the {station_of(cid)} station, which already has a body ({held[station_of(cid)]}); the runtime shows one body per station")
        chosen = cid
        ranked = [cid]
        why = ["--component override"] + reasons(cid)
        rows = [{"rank": 1, "id": cid, "mode": mode, "reasons": why}]
    elif candidates:
        ranked = sorted(candidates, key=lambda c: (
            1 if cooling(c) else 0, 0 if station_of(c) else 1, -traffic.get(c, 0), 0 if reg[c].get("first_party") else 1, c))
        chosen = ranked[0]
        rows = [{"rank": i + 1, "id": c, "mode": "build", "reasons": reasons(c)} for i, c in enumerate(ranked[:10])]
    else:
        mode = "polish"
        polishable = [c for c in have if c in reg] or list(have)
        if not polishable:
            raise SystemExit("factory_forge: the registry is empty, nothing to pick")

        def key(c):
            f = have[c].get("forge") or {}
            return (float(f.get("score", -1)), str(f.get("run", "")), c)

        ranked = sorted(polishable, key=key)
        chosen = ranked[0]
        rows = []
        for i, c in enumerate(ranked[:10]):
            f = have[c].get("forge") or {}
            rows.append({"rank": i + 1, "id": c, "mode": "polish",
                         "reasons": [f"forge.score {f.get('score', 'unscored')}", f"last forged {f.get('run', 'never')}"]})
        rows[0]["reasons"].insert(0, "every component has an asset: polish the weakest")
    return {"id": chosen, "mode": mode, "candidates": len(candidates), "assets": len(have),
            "registry": len(reg), "cast_source": cast_src, "night": night, "ranked": rows}


def explain(res: dict) -> str:
    lines = [f"factory-forge pick: {res['id']} ({res['mode']} mode)",
             f"  registry {res['registry']} components, {res['assets']} assets, {res['candidates']} without one; "
             f"stations from {res['cast_source']}; traffic from night {res['night']}",
             "  rank  id                         reasons"]
    for r in res["ranked"]:
        lines.append(f"  {r['rank']:>4}  {r['id']:<26} {'; '.join(r['reasons'])}")
    return "\n".join(lines)


# ---- prompt -------------------------------------------------------------------------------------------

def _rel_to(p: Paths, path: Path) -> str:
    return os.path.relpath(path, p.sandbox)


def neighbours(reg: dict, cast: dict, cid: str, limit: int = 14) -> list[dict]:
    out, seen = [], set()
    rec = reg[cid]
    for rel in rec.get("relations") or []:
        t = rel.get("to")
        if t in reg and (t, "out") not in seen:
            seen.add((t, "out"))
            out.append({"id": t, "dir": f"{cid} -> {t}", "kind": rel.get("kind"), "via": rel.get("via")})
    for oid, o in reg.items():
        for rel in o.get("relations") or []:
            if rel.get("to") == cid and (oid, "in") not in seen:
                seen.add((oid, "in"))
                out.append({"id": oid, "dir": f"{oid} -> {cid}", "kind": rel.get("kind"), "via": rel.get("via")})
    for n in out:
        r = reg[n["id"]]
        c = cast.get(n["id"]) or {}
        n["name"], n["summary"] = r.get("name", n["id"]), r.get("summary", "")
        n["place"] = c.get("station") or (f"kiosk near {c['near']}" if c.get("near") else "unplaced")
    return out[:limit]


def best_exemplar(p: Paths, exclude: str) -> tuple[str, dict] | None:
    have = {c: a for c, a in assets_present(p).items() if c != exclude}
    if not have:
        return None
    c = max(have, key=lambda c: (float((have[c].get("forge") or {}).get("score", 0)), c))
    return c, have[c]


def render_prompt(p: Paths, cid: str, mode: str | None = None) -> str:
    reg = load_registry(p)
    if cid not in reg:
        raise SystemExit(f"factory_forge: {cid!r} is not an Atlas registry id")
    cast, cast_src = load_cast(p, reg)
    c = cast.get(cid) or {}
    have = read_asset(p, cid)
    mode = mode or ("polish" if have else "build")
    base = (p.forge / "PROMPT.md").read_text()
    rec_file = p.registry / f"{cid}.yaml"
    rec_text = rec_file.read_text() if rec_file.exists() else yaml.safe_dump(reg[cid], sort_keys=False)
    where = c.get("station") or c.get("near")
    mates = sorted(i for i, o in cast.items() if i != cid and where and (o.get("station") == where or o.get("near") == where))
    mates_assets = [i for i in mates if read_asset(p, i)]
    ex = best_exemplar(p, cid)
    run = datetime.now().astimezone().strftime(RUN_FORMAT)

    out = [base.rstrip(), "", "---", "", f"# This run: {mode} `{cid}`", "",
           f"- **Component id:** `{cid}` ({reg[cid].get('name', cid)}), domain {reg[cid].get('domain', '?')}, "
           f"kind {reg[cid].get('kind', '?')}, first-party: {bool(reg[cid].get('first_party'))}",
           f"- **Mode:** {mode}" + (" (an asset exists: improve it, do not restart from nothing)" if mode == "polish" else " (no asset yet: build the first one)"),
           f"- **Run stamp for `forge.run`:** `{run}`",
           f"- **Your directory (the only place you may write):** `src/assets/{cid}/`  (absolute: `{p.asset_dir(cid)}`)",
           f"- **Generated glb:** `public/assets/{cid}/model.glb` (by `mise run assets`; gitignored; never edit it)",
           f"- **Contract:** `{p.forge / 'CONTRACT.md'}`",
           f"- **Placement:** " + (f"it IS station `{c['station']}`: `placement: \"station\"`, and list the Props.tsx primitives it hides in `replaces`" if c.get("station")
                                   else f"it has no station of its own; its kiosk stands in the annex beside `{c.get('near')}`: `placement: \"kiosk\"`, footprint at most 1.4 x 1.3" if c.get("near")
                                   else "the cast gives it no station and no annex: use `placement: \"kiosk\"` and say so in NOTES.md"),
           f"- **Station source:** {cast_src}", "",
           "## The Atlas record (the truth about what this component does)", "", "```yaml", rec_text.rstrip(), "```", "",
           "## Its neighbours in the Atlas (who it talks to, and where they stand)", ""]
    nb = neighbours(reg, cast, cid)
    if nb:
        out += ["| wire | kind | via | neighbour | stands at | what it is |", "|---|---|---|---|---|---|"]
        out += [f"| {n['dir']} | {n['kind']} | {str(n['via'] or '').replace('|', '/')} | {n['name']} | {n['place']} | {n['summary'].replace('|', '/')} |" for n in nb]
    else:
        out.append("(no relations recorded)")
    out += ["", "## Station context", ""]
    if where:
        out += [f"- Station / set id: `{where}`. Read its surroundings in `src/world/Scene.tsx`, `src/world/Props.tsx` and `src/sim/layout.ts` "
                f"(search for `{where}` and the primitive it uses), and `src/waybill/stations.ts` for the annex slot geometry."]
        out += [f"- Other components that stand at `{where}`: " + (", ".join(f"`{m}`" + (" (has an asset)" if m in mates_assets else "") for m in mates[:20]) or "none")]
    else:
        out += ["- No station placement is known for this component; keep the footprint small and say so in NOTES.md."]
    out += ["", "## Exemplar", ""]
    if ex:
        eid, ea = ex
        out += [f"The best existing asset is `{eid}` (forge score {(ea.get('forge') or {}).get('score', '?')}): read `src/assets/{eid}/build.py`, `asset.json` and `NOTES.md` "
                "for the house style, the helper usage and the clip structure. Match its quality; do not copy its shapes."]
    else:
        out += ["No finished asset exists yet, so you are setting the house style. `forge/fixture/` (if present) is a harness test asset that proves the pipeline works; "
                "it is not a style reference."]
    if mode == "polish":
        out += ["", "## Previous run (polish mode)", "", "`asset.json`:", "", "```json", json.dumps(have, indent=1), "```", ""]
        notes = p.asset_dir(cid) / "NOTES.md"
        if notes.exists():
            out += ["`NOTES.md` as it stands:", "", "```markdown", notes.read_text().rstrip(), "```", ""]
        prev = [r for r in ledger_read(p)["runs"] if r.get("id") == cid]
        if prev:
            out += ["Earlier forge runs for this component (newest last):", "", "```json", json.dumps(prev[-4:], indent=1), "```", ""]
        out += ["Find what scored lowest against the rubric last time, say so first in NOTES.md, then fix that. Keep what works. "
                "You must raise the score or hold it while fixing a real fault; never lower it by regressing."]
    return "\n".join(out) + "\n"


# ---- ledger -------------------------------------------------------------------------------------------

def ledger_read(p: Paths) -> dict:
    try:
        d = json.loads(p.ledger.read_text())
        if isinstance(d.get("runs"), list):
            return d
    except (OSError, ValueError):
        pass
    return {"format": LEDGER_FORMAT, "version": 1, "runs": []}


def ledger_add(p: Paths, rec: dict) -> dict:
    d = ledger_read(p)
    row = {k: rec.get(k) for k in ("run", "id", "mode", "outcome", "score", "commit", "tokens", "showcase_url", "duration_s")}
    row["run"] = row["run"] or datetime.now().astimezone().strftime(RUN_FORMAT)
    for k in ("note", "failed"):
        if rec.get(k):
            row[k] = rec[k]
    d["runs"].append(row)
    p.ledger.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.ledger.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, indent=1) + "\n")
    tmp.replace(p.ledger)
    return row


# ---- claude usage -------------------------------------------------------------------------------------

def parse_usage(text: str) -> dict:
    """Token totals from `claude -p --output-format json` (one object, or a list of events ending in one)."""
    try:
        d = json.loads(text)
    except ValueError:
        d = None
        for line in reversed(text.strip().splitlines()):
            try:
                d = json.loads(line)
                break
            except ValueError:
                continue
    if isinstance(d, list):
        d = next((x for x in reversed(d) if isinstance(x, dict) and x.get("type") == "result"), d[-1] if d else {})
    d = d if isinstance(d, dict) else {}
    u = d.get("usage") or {}
    i, o = int(u.get("input_tokens", 0)), int(u.get("output_tokens", 0))
    cw, cr = int(u.get("cache_creation_input_tokens", 0)), int(u.get("cache_read_input_tokens", 0))
    return {"input": i, "output": o, "cache_creation": cw, "cache_read": cr, "total": i + o,
            "cost_usd": d.get("total_cost_usd"), "turns": d.get("num_turns"), "is_error": bool(d.get("is_error")),
            "subtype": d.get("subtype"), "result_excerpt": str(d.get("result", ""))[:400]}


# ---- snapshot and scope -------------------------------------------------------------------------------

def snapshot(p: Paths) -> dict:
    """Fingerprint every dirty or untracked path in the repo, so a later diff names exactly what a run changed."""
    root = p.repo_root()
    head = _run(["git", "-C", str(root), "rev-parse", "HEAD"]).stdout.strip()
    st = _run(["git", "-C", str(root), "status", "--porcelain=v1", "-z", "-uall", "--no-renames"])
    files = {}
    parts = st.stdout.split("\0")
    for entry in parts:
        if len(entry) < 4:
            continue
        code, rel = entry[:2], entry[3:]
        f = root / rel
        try:
            h = hashlib.sha1(f.read_bytes()).hexdigest() if f.is_file() else ("dir" if f.exists() else "gone")
        except OSError:
            h = "unreadable"
        files[rel] = f"{code.strip() or '?'}:{h}"
    return {"head": head, "files": files}


def scope_check(p: Paths, cid: str, before: dict | None) -> tuple[bool, str, list[str]]:
    now = snapshot(p)
    was = (before or {"files": {}})["files"]
    changed = sorted(k for k in set(now["files"]) | set(was) if now["files"].get(k) != was.get(k))
    prefix = p.scope_prefix(cid)
    # The agent is briefed inside the platform; the monorepo around it has other writers (bus logs, submodule
    # pointers, parallel agents) whose edits during a 40-minute run are not the agent's doing. Watch the platform.
    plat = os.path.relpath(p.root, p.repo_root()).replace(os.sep, "/")
    plat = "" if plat == "." else plat + "/"
    elsewhere = [k for k in changed if not k.startswith(plat)]
    stray = [k for k in changed if k.startswith(plat) and not k.startswith(prefix)]
    inside = len(changed) - len(stray) - len(elsewhere)
    moved = bool(before and before.get("head") and before["head"] != now["head"])
    detail = f"{len(changed)} path(s) changed, {inside} inside {prefix}"
    if moved:
        detail += f"; HEAD moved {before['head'][:8]} -> {now['head'][:8]} during the run (commits are not in this diff)"
    if elsewhere:
        detail += f"; {len(elsewhere)} outside {plat or 'the repo'} ignored (other writers): " + ", ".join(elsewhere[:6])
    if stray:
        detail += "; OUTSIDE: " + ", ".join(stray[:12])
    return not stray, detail, stray


# ---- verify -------------------------------------------------------------------------------------------

def _tool_env(p: Paths) -> dict:
    """PATH with the sandbox's own node first (mise), so npx and node resolve under a stripped environment."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("__MISE_") and k != "MISE_SHELL"}   # activate-hook state breaks nested mise
    home = env.get("HOME") or str(Path.home())
    mise = shutil.which("mise") or f"{home}/.local/bin/mise"
    extra = []
    r = _run([mise, "which", "node"], cwd=p.sandbox, timeout=60)
    if r.returncode == 0 and r.stdout.strip():
        extra.append(str(Path(r.stdout.strip()).parent))
    extra += [f"{home}/.local/bin", os.path.dirname(mise)]
    env["PATH"] = ":".join(dict.fromkeys(extra + env.get("PATH", "/usr/local/bin:/usr/bin:/bin").split(":")))
    env["MISE_BIN"] = mise
    return env


def _load_glbcheck(p: Paths):
    spec = importlib.util.spec_from_file_location("glbcheck", p.tools / "glbcheck.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["glbcheck"] = mod
    spec.loader.exec_module(mod)
    return mod


def check_manifest(a: dict, cid: str, c: dict) -> list[tuple[str, bool, str]]:
    """asset.json against CONTRACT section 2."""
    res = []
    add = lambda n, ok, d="": res.append((n, bool(ok), d))   # noqa: E731
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)   # noqa: E731
    add("manifest-format", a.get("format") == "33god.factory-asset" and a.get("version") == 1, f"format={a.get('format')!r} version={a.get('version')!r}")
    add("manifest-id", a.get("id") == cid, f"id={a.get('id')!r}, directory {cid!r}")
    add("manifest-title", isinstance(a.get("title"), str) and 3 <= len(a["title"]) <= 80, repr(a.get("title")))
    pl = a.get("placement")
    add("manifest-placement", pl in PLACEMENTS, repr(pl))
    if c.get("station"):
        add("placement-matches-cast", pl == "station", f"the cast gives {cid} station {c['station']}, so placement must be 'station' (got {pl!r})")
    elif c:
        add("placement-matches-cast", pl == "kiosk", f"the cast gives {cid} no station, so placement must be 'kiosk' (got {pl!r})")
    rep = a.get("replaces", [])
    add("manifest-replaces", isinstance(rep, list) and all(isinstance(x, str) for x in rep) and (pl != "station" or len(rep) > 0) and (pl != "kiosk" or not rep),
        f"replaces={rep!r} (station assets name at least one primitive; kiosks none)")
    fp = a.get("footprint")
    fp_ok = isinstance(fp, list) and len(fp) == 2 and all(num(x) and x > 0 for x in fp)
    add("manifest-footprint", fp_ok and (pl != "kiosk" or (fp[0] <= 1.4 and fp[1] <= 1.3)), f"footprint={fp!r}" + (" (kiosk slot is 1.4 x 1.3)" if pl == "kiosk" else ""))
    add("manifest-height", num(a.get("height")) and 0 < a["height"] <= 6, f"height={a.get('height')!r}")
    add("manifest-scale-rotation", num(a.get("scale", 1)) and a.get("scale", 1) > 0 and num(a.get("rotationY", 0)), f"scale={a.get('scale')!r} rotationY={a.get('rotationY')!r}")
    h = a.get("handles")
    add("manifest-handles", isinstance(h, list) and h and set(h) <= HANDLES, f"handles={h!r}")
    cl = a.get("clips")
    add("manifest-clips", isinstance(cl, dict) and set(cl) == set(CLIPS) and all(isinstance(v, str) and v for v in cl.values()), f"clips={cl!r}")
    so = a.get("sockets")
    add("manifest-sockets", isinstance(so, dict) and set(so) == set(SOCKETS) and all(isinstance(v, str) and v for v in so.values()), f"sockets={so!r}")
    b = a.get("budget")
    add("manifest-budget", isinstance(b, dict) and num(b.get("tris")) and num(b.get("glbKB")) and 0 < b["tris"] <= 15000 and 0 < b["glbKB"] <= 600, f"budget={b!r}")
    f = a.get("forge")
    f_ok = isinstance(f, dict) and isinstance(f.get("run"), str) and f["run"] and isinstance(f.get("rounds"), int) and 1 <= f["rounds"] <= 3 and num(f.get("score")) and 0 <= f["score"] <= 10
    add("manifest-forge", f_ok, f"forge={f!r} (run string, rounds 1-3, score 0-10)")
    add("ship-score", f_ok and f["score"] >= SHIP_SCORE, f"self-score {f.get('score') if isinstance(f, dict) else None!r}, {SHIP_SCORE} to ship")
    return res


def verify(p: Paths, cid: str, baseline: dict | None = None, dist: Path | None = None, out: Path | None = None,
           skip_build: bool = False, skip_browser: bool = False, keep_dist: bool = False) -> dict:
    checks: list[dict] = []
    add = lambda name, ok, detail="": checks.append({"name": name, "ok": bool(ok), "detail": detail})   # noqa: E731
    reg = load_registry(p)
    cast, _ = load_cast(p, reg)
    d = p.asset_dir(cid)
    env = _tool_env(p)
    out = out or Path(tempfile.mkdtemp(prefix=f"factory-forge-{cid}-"))
    out.mkdir(parents=True, exist_ok=True)
    add("registry-id", cid in reg, f"{cid} is {'' if cid in reg else 'not '}an Atlas registry id")

    ok, detail, stray = scope_check(p, cid, baseline)
    add("scope", ok, detail)

    asset = None
    mf = d / "asset.json"
    if not mf.exists():
        add("asset.json", False, f"missing {mf}")
    else:
        try:
            asset = json.loads(mf.read_text())
            add("asset.json", True, "parses")
        except ValueError as e:
            add("asset.json", False, f"invalid JSON: {e}")
    if asset is not None:
        for n, o, det in check_manifest(asset, cid, cast.get(cid) or {}):
            add(n, o, det)
        st = (cast.get(cid) or {}).get("station")
        other = sorted(i for i in assets_present(p) if i != cid and st and (cast.get(i) or {}).get("station") == st)
        add("station-free", not other, f"{cid} is the {st} station's body" if not other else f"the {st} station already has a body ({other[0]}); the runtime ignores a second")

    bp = d / "build.py"
    add("build.py", bp.exists() and bp.stat().st_size > 400, f"{bp.stat().st_size} bytes" if bp.exists() else "missing")
    nm = d / "NOTES.md"
    text = nm.read_text() if nm.exists() else ""
    missing = [w for w in ("Idle", "Accept", "Work", "Emit") if w not in text]
    add("NOTES.md", len(text) >= NOTES_MIN_CHARS and not missing,
        f"{len(text)} chars" + (f"; never mentions {missing}" if missing else "") + (f"; under {NOTES_MIN_CHARS}" if len(text) < NOTES_MIN_CHARS else ""))

    glb = p.glb(cid)
    if not skip_build and asset is not None:
        r = _run([env["MISE_BIN"], "run", "assets"], cwd=p.sandbox, env=env)
        add("mise run assets", r.returncode == 0, "built" if r.returncode == 0 else _tail(r.stdout + r.stderr))
    if glb.exists():
        stale = bp.exists() and glb.stat().st_mtime + 1 < bp.stat().st_mtime
        add("glb-built", not stale, f"{glb} {glb.stat().st_size // 1024} KB" + (" (older than build.py: stale)" if stale else ""))
        try:
            gc = _load_glbcheck(p)
            for n, o, det in gc.check(glb, asset):
                add(n, o, det)
        except Exception as e:  # noqa: BLE001
            add("glb-validator", False, f"{type(e).__name__}: {e}")
    else:
        add("glb-built", False, f"{glb} does not exist")

    tsc = _run(["npx", "--no-install", "tsc", "--noEmit"], cwd=p.sandbox, env=env)
    add("tsc", tsc.returncode == 0, "clean" if tsc.returncode == 0 else _tail(tsc.stdout + tsc.stderr, 20))
    own = dist is None
    dist = dist or Path(tempfile.mkdtemp(prefix=f"factory-check-{os.getpid()}-"))
    vb = _run(["npx", "--no-install", "vite", "build", "--outDir", str(dist), "--emptyOutDir"], cwd=p.sandbox, env=env)
    add("vite-build", vb.returncode == 0, "built to a temp outDir" if vb.returncode == 0 else _tail(vb.stdout + vb.stderr, 20))
    sc = _run(["node", "--import", "./tools/waybill/register.mjs", "--experimental-strip-types", "tools/waybill/selfcheck.ts"], cwd=p.sandbox, env=env)
    add("waybill-selfcheck", sc.returncode == 0, _tail(sc.stdout, 1) if sc.returncode == 0 else _tail(sc.stdout + sc.stderr, 12))

    shots = out / "shots"
    if skip_browser:
        add("shoot", True, "skipped (--skip-browser)")
    elif vb.returncode != 0:
        add("shoot", False, "no build to shoot")
    else:
        r = _run([sys.executable, str(p.tools / "shoot.py"), cid, "--dist", str(dist), "--out", str(shots)], cwd=p.sandbox, env=env, timeout=1200)
        summary = {}
        try:
            summary = json.loads((shots / "console.json").read_text())
        except (OSError, ValueError):
            pass
        errs = summary.get("errors", [])
        add("shoot", r.returncode == 0 and not errs and (shots / "contact-sheet.png").exists(),
            f"{len(errs)} console error(s); {summary.get('frames', 0)} frames" if summary else _tail(r.stdout + r.stderr, 12))
        if errs:
            add("console-clean", False, "; ".join(str(e)[:160] for e in errs[:4]))
    if own and not keep_dist:
        shutil.rmtree(dist, ignore_errors=True)

    failed = [c["name"] for c in checks if not c["ok"]]
    forge = (asset or {}).get("forge") if isinstance(asset, dict) else None
    return {"id": cid, "pass": not failed, "failed": failed, "score": (forge or {}).get("score") if isinstance(forge, dict) else None,
            "title": (asset or {}).get("title") if isinstance(asset, dict) else None, "shots": str(shots), "out": str(out),
            "stray_paths": stray, "checks": checks}


# ---- showcase page ------------------------------------------------------------------------------------

def _md_excerpt(text: str, limit: int = 2400) -> str:
    out, size = [], 0
    for block in re.split(r"\n\s*\n", text.strip()):
        b = block.strip()
        if b.startswith("#"):
            level = len(b) - len(b.lstrip("#"))
            html_b = f"<h{min(level + 1, 4)}>{html.escape(b.lstrip('# ').strip())}</h{min(level + 1, 4)}>"
        elif b.startswith(("- ", "* ")):
            items = "".join(f"<li>{html.escape(l.lstrip('-* ').strip())}</li>" for l in b.splitlines() if l.strip())
            html_b = f"<ul>{items}</ul>"
        else:
            html_b = f"<p>{html.escape(' '.join(b.split()))}</p>"
        size += len(b)
        out.append(html_b)
        if size > limit:
            out.append("<p class=\"more\">(excerpt: the full NOTES.md is in the repo)</p>")
            break
    return "\n".join(out)


def render_showcase(p: Paths, cid: str, shots: Path, out: Path, tokens: dict | None = None, run: str = "", commit: str = "") -> Path:
    out.mkdir(parents=True, exist_ok=True)
    pngs = sorted(shots.glob("*.png")) if shots.exists() else []
    for f in pngs:
        shutil.copy(f, out / f.name)
    a = read_asset(p, cid) or {}
    reg = load_registry(p)
    rec = reg.get(cid, {})
    notes = p.asset_dir(cid) / "NOTES.md"
    f = a.get("forge") or {}
    turn = [x for x in pngs if x.name.startswith("turn-")]
    cycle = sorted((x for x in pngs if x.name.split("-")[0] in CLIPS), key=lambda x: (CLIPS.index(x.name.split("-")[0]), x.name))
    visit = [x for x in pngs if x.name.startswith("visit-")]
    situ = [x for x in pngs if x.name.startswith("situ")]
    fig = lambda items: "".join(f'<figure><img src="{html.escape(x.name)}" alt="{html.escape(x.stem)}" loading="lazy"><figcaption>{html.escape(x.stem)}</figcaption></figure>' for x in items)   # noqa: E731
    tk = f"{tokens['total']:,} tokens" if tokens and tokens.get("total") else ""
    live = f"https://manual.delo.sh/sandbox/?at={cid}"
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(a.get('title') or cid)} - Factory forge</title>
<style>
:root {{ --bg:#EFE6D4; --card:#FBF6EA; --ink:#2B2620; --mute:#6B6257; --line:#D9CDB4; --accent:#E8833A; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#1D1A16; --card:#27231E; --ink:#EFE6D4; --mute:#A89E8F; --line:#3A342C; --accent:#F0A060; }} }}
:root[data-theme="dark"] {{ --bg:#1D1A16; --card:#27231E; --ink:#EFE6D4; --mute:#A89E8F; --line:#3A342C; --accent:#F0A060; }}
* {{ box-sizing:border-box }} body {{ margin:0; background:var(--bg); color:var(--ink); font:16px/1.55 system-ui,sans-serif }}
main {{ max-width:1080px; margin:0 auto; padding:28px 16px 64px }}
h1 {{ font-size:28px; margin:0 0 4px }} h2 {{ font-size:18px; margin:32px 0 10px; color:var(--accent) }}
.meta {{ color:var(--mute); margin:0 0 18px }} .meta b {{ color:var(--ink) }}
a {{ color:var(--accent) }} .btn {{ display:inline-block; padding:8px 14px; border:1px solid var(--accent); border-radius:8px; text-decoration:none; font-weight:600 }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:10px }}
figure {{ margin:0; background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:hidden }}
figure img {{ width:100%; display:block }} figcaption {{ padding:6px 10px; color:var(--mute); font-size:13px }}
.wide figure {{ max-width:720px }} .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:4px 20px 12px }}
.card h2,.card h3,.card h4 {{ margin:16px 0 6px }} .more {{ color:var(--mute); font-style:italic }}
</style></head><body><main>
<h1>{html.escape(a.get('title') or cid)}</h1>
<p class="meta"><b>{html.escape(cid)}</b> - {html.escape(rec.get('summary', ''))}<br>
{html.escape(f.get('run', run))} - self-score <b>{html.escape(str(f.get('score', '?')))}/10</b> after {html.escape(str(f.get('rounds', '?')))} round(s){' - ' + html.escape(tk) if tk else ''}{' - commit <code>' + html.escape(commit[:10]) + '</code>' if commit else ''}</p>
<p><a class="btn" href="{html.escape(live)}">Visit it on the Factory floor</a></p>
<h2>Turntable</h2><div class="grid">{fig(turn)}</div>
<h2>The cycle: idle, accept, work, emit</h2><div class="grid">{fig(cycle)}</div>
<h2>A parcel passes through</h2><div class="grid">{fig(visit)}</div>
<h2>In place on the floor</h2><div class="grid wide">{fig(situ)}</div>
<h2>Forge notes</h2><div class="card">{_md_excerpt(notes.read_text()) if notes.exists() else '<p>No notes.</p>'}</div>
</main></body></html>
"""
    (out / "index.html").write_text(page)
    return out / "index.html"


# ---- cli ----------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=PLATFORM, help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("pick"); s.add_argument("--component"); s.add_argument("--explain", action="store_true"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("prompt"); s.add_argument("id"); s.add_argument("--mode", choices=["build", "polish"])
    s = sub.add_parser("snapshot"); s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("verify"); s.add_argument("id"); s.add_argument("--baseline", type=Path); s.add_argument("--dist", type=Path)
    s.add_argument("--out", type=Path); s.add_argument("--skip-build", action="store_true"); s.add_argument("--skip-browser", action="store_true"); s.add_argument("--keep-dist", action="store_true")
    s = sub.add_parser("usage"); s.add_argument("file", type=Path)
    s = sub.add_parser("showcase"); s.add_argument("id"); s.add_argument("--shots", type=Path, required=True); s.add_argument("--out", type=Path, required=True)
    s.add_argument("--tokens", help="JSON from `usage`"); s.add_argument("--commit", default="")
    s = sub.add_parser("ledger"); lsub = s.add_subparsers(dest="lcmd", required=True)
    la = lsub.add_parser("add")
    for k in ("run", "id", "mode", "outcome", "commit", "showcase-url", "note"):
        la.add_argument(f"--{k}")
    la.add_argument("--score", type=float); la.add_argument("--tokens", help="a number or a JSON object"); la.add_argument("--duration-s", type=float)
    la.add_argument("--failed", help="comma-separated names of the checks that failed")
    lsub.add_parser("show")
    a = ap.parse_args(argv)
    p = Paths(a.root.resolve())

    if a.cmd == "pick":
        res = pick(p, a.component)
        print(json.dumps(res, indent=1) if a.json else (explain(res) if a.explain else f"{res['id']} {res['mode']}"))
        return 0
    if a.cmd == "prompt":
        sys.stdout.write(render_prompt(p, a.id, a.mode))
        return 0
    if a.cmd == "snapshot":
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(snapshot(p)))
        return 0
    if a.cmd == "verify":
        base = json.loads(a.baseline.read_text()) if a.baseline else None
        v = verify(p, a.id, base, a.dist, a.out, a.skip_build, a.skip_browser, a.keep_dist)
        print(json.dumps(v, indent=1))
        return 0 if v["pass"] else 1
    if a.cmd == "usage":
        print(json.dumps(parse_usage(a.file.read_text())))
        return 0
    if a.cmd == "showcase":
        print(render_showcase(p, a.id, a.shots, a.out, json.loads(a.tokens) if a.tokens else None, commit=a.commit))
        return 0
    if a.cmd == "ledger":
        if a.lcmd == "show":
            print(json.dumps(ledger_read(p), indent=1))
            return 0
        tokens = a.tokens
        if tokens:
            try:
                tokens = json.loads(tokens)
            except ValueError:
                pass
        row = ledger_add(p, {"run": a.run, "id": a.id, "mode": a.mode, "outcome": a.outcome, "score": a.score, "commit": a.commit,
                             "tokens": tokens, "showcase_url": a.showcase_url, "duration_s": a.duration_s, "note": a.note,
                             "failed": [x for x in (a.failed or "").split(",") if x]})
        print(json.dumps(row))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
