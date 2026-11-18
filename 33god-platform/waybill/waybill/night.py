"""Night digest: everything the company did in a window of wall-clock time (`33god.night` v1).

A waybill follows one prompt. A night digest is the wide shot: every Bloodbank event Candystore
archived between two instants, folded into per-minute activity for each registry component. It is
what the Overnight launch page replays instead of staged window activity, and any other surface that
wants "what was the company doing at 03:12" (the Factory, a status page) reads the same file.

Read-only: one aggregate query against Candystore's Postgres (read-only transaction, the password
never leaves the container). No payloads leave the database, only producer, type and time, so the
public profile is safe to commit and serve.

Producers resolve to registry components through each component's `surfaces: producer:<name>`
entries (globs allowed, e.g. `producer:hermes-agent:*`). Two producers do work on behalf of
others, so their events are credited to whoever the work was for:
  - Candybar's invoked/completed/failed events carry the job name; the job resolves to its component
    (producer surface, registry id, longest registry-id prefix, or the repo its `.candybars/` manifest
    lives in). Client-project jobs stay with Candybar.
  - Hook-hub's hook.updated events list each handler that succeeded; each handler resolves the same
    way (plus HANDLER_OWNERS for handlers whose name does not say). The envelope stays with hook-hub. Hermes desks (`hermes-agent:<desk>`) keep
their desk name when it is a first-party desk (its name starts with a registry component id or
`33god`); in the public profile any other desk becomes `desk-<n>`.
"""
from __future__ import annotations

import fnmatch
import json
import re
import subprocess
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

FORMAT = "33god.night"
VERSION = 1
REGISTRY_DIR = Path(__file__).resolve().parents[2] / "components"
PG_CONTAINER = "candystore-postgres"
PSQL_ARGV = ["docker", "exec", "-i", PG_CONTAINER, "sh", "-c",
             'psql -X -q -A -t -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "${POSTGRES_DB:-$POSTGRES_USER}" -f -']
RARE = 12          # an event type seen at most this often in the window is a "moment" worth naming
MOMENTS_MAX = 400

# Hook handlers whose id does not start with their owner's registry id.
HANDLER_OWNERS = {
    "bloodbank-publisher": "agent-hooks", "hub-selftest": "hook-hub", "native-clock-guard": "hook-hub",
    "nanoleaf": "hook-hub", "skill-reminder": "skillex", "skill-lint": "skillex",
    "project-notebook-start": "open-notebook", "project-notebook-end": "open-notebook",
}
CANDYBAR_ROOTS = ["~/code", "~/code/33GOD", "~/code/33GOD/bloodbank/services", "~/docker", "~/.config", "~/.agents", "~/HeyMa"]


# ---------------------------------------------------------------- registry

def load_registry(root: Path = REGISTRY_DIR) -> dict[str, dict]:
    """id -> {name, first_party, producers:[globs]} from components/*.yaml (no yaml dependency: the fields are flat)."""
    out: dict[str, dict] = {}
    for p in sorted(root.glob("*.yaml")):
        rec = {"name": p.stem, "first_party": False, "producers": []}
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^name:\s*(.+?)\s*$", line)
            if m:
                rec["name"] = m.group(1).strip("'\"")
            m = re.match(r"^first_party:\s*(\w+)", line)
            if m:
                rec["first_party"] = m.group(1).lower() == "true"
            m = re.match(r"^\s*-\s*producer:(\S+)\s*$", line)
            if m:
                rec["producers"].append(m.group(1))
        out[p.stem] = rec
    return out


def resolver(registry: dict[str, dict]):
    """producer -> component id. Exact surfaces win over globs; longer globs win over shorter ones."""
    exact: dict[str, str] = {}
    globs: list[tuple[str, str]] = []
    for cid, rec in registry.items():
        for g in rec["producers"]:
            if any(ch in g for ch in "*?["):
                globs.append((g, cid))
            else:
                exact.setdefault(g, cid)
    globs.sort(key=lambda gc: -len(gc[0]))

    def resolve(producer: str) -> str | None:
        if producer in exact:
            return exact[producer]
        for g, cid in globs:
            if fnmatch.fnmatchcase(producer, g):
                return cid
        if producer in registry:          # a producer named exactly like its component
            return producer
        return None
    return resolve


def candybar_manifests(roots: list[str] = CANDYBAR_ROOTS) -> dict[str, str]:
    """job name -> basename of the repo whose .candybars/ holds its manifest (worktrees skipped)."""
    out: dict[str, str] = {}
    for r in roots:
        base = Path(r).expanduser()
        for d in [base / ".candybars", *base.glob("*/.candybars")]:
            if ".worktrees" in d.parts or not d.is_dir():
                continue
            for f in d.glob("*.candybar.toml"):
                out.setdefault(f.name[: -len(".candybar.toml")], d.parent.name)
    return out


def worker_resolver(registry: dict[str, dict], resolve, manifests: dict[str, str], owners: dict[str, str]):
    """A job or handler name -> the component it works for, or None."""
    ids = sorted(registry, key=len, reverse=True)
    repo_ids = {}
    for cid, rec in registry.items():
        repo_ids.setdefault(cid, cid)

    def who(name: str) -> str | None:
        if not name:
            return None
        if name in owners and owners[name] in registry:
            return owners[name]
        cid = resolve(name)
        if cid:
            return cid
        for i in ids:
            if name.startswith(i + "-"):
                return i
        repo = manifests.get(name)
        if repo and repo in registry:
            return repo
        if repo and repo.lower() in registry:
            return repo.lower()
        return None
    return who


# ---------------------------------------------------------------- window

def night_window(day: date, start: str = "18:02", end: str = "07:41", tz: str = "America/New_York") -> tuple[datetime, datetime]:
    """[day start, next-day end) in tz, returned as aware UTC datetimes. end <= start means the next day."""
    z = ZoneInfo(tz)
    s = datetime.combine(day, time.fromisoformat(start), z)
    e = datetime.combine(day, time.fromisoformat(end), z)
    if e <= s:
        e += timedelta(days=1)
    return s.astimezone(timezone.utc), e.astimezone(timezone.utc)


def build_sql(lo: datetime, hi: datetime) -> str:
    """Rows of {producer, type, m, n, worker}. worker: the Candybar job name, else null. Hook handler
    successes come back as extra rows with producer 'hook-handler', type 'hook.handler.succeeded'."""
    lo_s, hi_s = lo.strftime("%Y-%m-%dT%H:%M:%SZ"), hi.strftime("%Y-%m-%dT%H:%M:%SZ")
    win = f"time >= '{lo_s}'::timestamptz and time < '{hi_s}'::timestamptz"
    minute = f"floor(extract(epoch from (time - '{lo_s}'::timestamptz)) / 60)::int"
    return (
        "select coalesce(json_agg(r), '[]'::json) from ("
        f" select coalesce(producer, '') as producer, type, {minute} as m, count(*)::int as n,"
        " case when type like 'bloodbank.cron.candybar.%' then raw->'data'->>'name' end as worker"
        f" from events where {win} group by 1, 2, 3, 5"
        " union all"
        f" select 'hook-handler', 'hook.handler.succeeded', {minute}, count(*)::int, e->>'handler_id'"
        " from events, jsonb_array_elements(case when jsonb_typeof(raw->'data'->'invocation'->'executions') = 'array'"
        " then raw->'data'->'invocation'->'executions' else '[]'::jsonb end) e"
        f" where type = 'bloodbank.agent.hook.updated' and e->>'status' = 'succeeded' and {win} group by 1, 2, 3, 5"
        ") r;"
    )


def query(sql: str, timeout: float = 120.0) -> list[dict]:
    script = "set default_transaction_read_only = on;\n" + sql + "\n"
    p = subprocess.run(PSQL_ARGV, input=script, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"psql exit {p.returncode}: {(p.stderr or p.stdout).strip()[:400]}")
    out = p.stdout.strip()
    return json.loads(out) if out else []


# ---------------------------------------------------------------- fold

def _first_party_desk(desk: str, registry: dict[str, dict]) -> bool:
    return desk.startswith("33god") or any(desk == cid or desk.startswith(cid + "-") for cid in registry)


def fold(rows: list[dict], lo: datetime, hi: datetime, registry: dict[str, dict], tz: str,
         profile: str = "public", label: str | None = None, manifests: dict[str, str] | None = None) -> dict[str, Any]:
    resolve = resolver(registry)
    who = worker_resolver(registry, resolve, manifests or {}, HANDLER_OWNERS)
    minutes_total = int((hi - lo).total_seconds() // 60)
    comps: dict[str, dict] = {}
    series: dict[str, dict[int, int]] = {}
    desks: dict[str, dict[int, int]] = {}
    types: dict[tuple[str, str], dict] = {}
    unmapped: dict[str, int] = {}
    desk_alias: dict[str, str] = {}
    total = 0
    by_minute = [0] * minutes_total     # real envelopes per minute (handler credit rows excluded)

    for r in rows:
        producer, et, m, n = r.get("producer") or "", r.get("type") or "", int(r["m"]), int(r["n"])
        if m < 0 or m >= minutes_total or not et:
            continue
        handler = producer == "hook-handler"
        if not handler:
            total += n          # handler rows describe work inside hook-hub events already counted
            by_minute[m] += n
        cid = (who(r.get("worker") or "") or None) if (handler or r.get("worker")) else None
        if handler and not cid:
            continue            # an unowned handler: its hook-hub envelope already lit hook-hub
        cid = cid or resolve(producer)
        if not cid:
            unmapped[producer or "(none)"] = unmapped.get(producer or "(none)", 0) + n
            continue
        c = comps.setdefault(cid, {"id": cid, "name": registry[cid]["name"], "first_party": registry[cid]["first_party"],
                                   "events": 0, "first": m, "last": m})
        c["events"] += n
        c["first"] = min(c["first"], m)
        c["last"] = max(c["last"], m)
        s = series.setdefault(cid, {})
        s[m] = s.get(m, 0) + n
        if producer.startswith("hermes-agent:"):
            desk = producer.split(":", 1)[1]
            if profile == "public" and not _first_party_desk(desk, registry):
                desk = desk_alias.setdefault(desk, f"desk-{len(desk_alias) + 1}")
            d = desks.setdefault(desk, {})
            d[m] = d.get(m, 0) + n
        t = types.setdefault((cid, et), {"component": cid, "type": et, "count": 0, "first": m, "minutes": []})
        t["count"] += n
        t["first"] = min(t["first"], m)
        t["minutes"].append(m)

    def sparse(d: dict[int, int]) -> list[list[int]]:
        return [[k, d[k]] for k in sorted(d)]

    moments = []
    for t in types.values():
        if t["count"] <= RARE:
            for m in sorted(set(t["minutes"]))[:3]:
                moments.append({"m": m, "component": t["component"], "type": t["type"]})
        else:
            moments.append({"m": t["first"], "component": t["component"], "type": t["type"], "first_of": t["count"]})
    moments.sort(key=lambda x: (x["m"], x["component"], x["type"]))
    moments = moments[:MOMENTS_MAX]

    z = ZoneInfo(tz)
    ls, le = lo.astimezone(z), hi.astimezone(z)
    return {
        "format": FORMAT,
        "version": VERSION,
        "profile": profile,
        "window": {
            "since": lo.strftime("%Y-%m-%dT%H:%M:%SZ"), "until": hi.strftime("%Y-%m-%dT%H:%M:%SZ"), "tz": tz,
            "local_since": ls.strftime("%Y-%m-%dT%H:%M"), "local_until": le.strftime("%Y-%m-%dT%H:%M"),
            "minutes": minutes_total,
            "label": label or _label(ls, le),
        },
        "source": "candystore events (Bloodbank archive), producer + type + time only",
        "totals": {"events": total, "components": len(comps), "desks": len(desks), "unmapped_events": sum(unmapped.values())},
        "events_by_minute": by_minute,
        "components": sorted(comps.values(), key=lambda c: -c["events"]),
        "minutes": {cid: sparse(s) for cid, s in sorted(series.items())},
        "desks": {d: sparse(s) for d, s in sorted(desks.items())},
        "types": sorted(({k: v for k, v in t.items() if k != "minutes"} for t in types.values()), key=lambda t: -t["count"]),
        "moments": moments,
        "unmapped": dict(sorted(unmapped.items(), key=lambda kv: -kv[1])) if profile == "full" else {"producers": len(unmapped)},
    }


def _label(ls: datetime, le: datetime) -> str:
    if ls.date() == le.date():
        return f"{ls.day} {ls.strftime('%b %Y')}"
    if (ls.month, ls.year) == (le.month, le.year):
        return f"{ls.day}–{le.day} {le.strftime('%b %Y')}"
    return f"{ls.day} {ls.strftime('%b')} – {le.day} {le.strftime('%b %Y')}"


def build(day: date, start: str = "18:02", end: str = "07:41", tz: str = "America/New_York",
          profile: str = "public", label: str | None = None) -> dict[str, Any]:
    lo, hi = night_window(day, start, end, tz)
    return fold(query(build_sql(lo, hi)), lo, hi, load_registry(), tz, profile, label, candybar_manifests())
