"""Night digest: everything the company did in a window of wall-clock time (`33god.night` v1).

A waybill follows one prompt. A night digest is the wide shot: every Bloodbank event Candystore
archived between two instants, folded into per-minute activity for each registry component. It is
what the Overnight launch page replays instead of staged window activity, and any other surface that
wants "what was the company doing at 03:12" (the Factory, a status page) reads the same file.

Read-only: one aggregate query against Candystore's Postgres (read-only transaction, the password
never leaves the container). No payloads leave the database, only producer, type and time, so the
public profile is safe to commit and serve.

Events resolve to registry components through the one resolver (waybill/registry.py, the map atlas.py
renders into the Factory cast): relay claims on the CloudEvent source and type first (`source:` surfaces,
so pj crank's crank.* events light Crank), then `producer:` surfaces (globs allowed). A component's
`events` are what resolved to it. Two producers do work on behalf of others, so their events are
credited to whoever the work was for:
  - Candybar's invoked/completed/failed events carry the job name; the job resolves to its component
    (producer surface, registry id, longest registry-id prefix, or the repo its `.candybars/` manifest
    lives in). Client-project jobs stay with Candybar.
  - Hook-hub's hook.updated events list each handler that succeeded; each handler resolves the same
    way (plus HANDLER_OWNERS for handlers whose name does not say). The envelope stays with hook-hub,
    so a handler's work lights its owner (`minutes`, `credited`) without adding to anyone's `events`:
    sum(components[].events) == totals.events - totals.unmapped_events. Hook-hub's own plumbing
    handlers (NO_CREDIT) light nothing extra.
Hermes desks (`hermes-agent:<desk>`) keep their desk name when it is a first-party desk (its name
starts with a registry component id or `33god`); in the public profile any other desk becomes
`desk-<n>`, and event types about other people's messages, calls and money (PRIVATE_TYPES) still
count and still light windows but are never named.

Minutes are local wall-clock minutes from the window's local start, so minute m is what a clock on
the wall read, the same clock the page shows. A DST night has one hour fewer (fall back: the repeated
hour folds onto itself) or one empty hour (spring forward).
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

# The resolver lives in registry.py (one map, rendered by atlas.py into the Factory cast); night re-exports it.
from .registry import (CANDYBAR_ROOTS, FIRST_PARTY_ROOT, HANDLER_OWNERS, NO_CREDIT, Registry,  # noqa: F401
                       _as_registry, candybar_manifests, load, load_registry, resolver, worker_resolver)

FORMAT = "33god.night"
VERSION = 1
PG_CONTAINER = "candystore-postgres"
PSQL_ARGV = ["docker", "exec", "-i", PG_CONTAINER, "sh", "-c",
             'psql -X -q -A -t -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "${POSTGRES_DB:-$POSTGRES_USER}" -f -']
RARE = 12          # an event type seen at most this often in the window is a "moment" worth naming
MOMENTS_MAX = 400

# Public profile: types about other people's messages, calls and money are counted, never named.
PRIVATE_TYPES = ("bloodbank.messaging.", "bloodbank.telephony.", "bloodbank.billing.transaction.")


# ---------------------------------------------------------------- window

def night_window(day: date, start: str = "18:02", end: str = "07:41", tz: str = "America/New_York") -> tuple[datetime, datetime]:
    """[day start, next-day end) in tz, returned as aware UTC datetimes. end <= start means the next day."""
    z = ZoneInfo(tz)
    s = datetime.combine(day, time.fromisoformat(start), z)
    e = datetime.combine(day, time.fromisoformat(end), z)
    if e <= s:
        e += timedelta(days=1)
    return s.astimezone(timezone.utc), e.astimezone(timezone.utc)


def wall_minutes(lo: datetime, hi: datetime, tz: str) -> int:
    """Minutes a wall clock in tz advances over [lo, hi) (819 on a normal night, 819 on a DST night too)."""
    z = ZoneInfo(tz)
    a, b = lo.astimezone(z).replace(tzinfo=None), hi.astimezone(z).replace(tzinfo=None)
    return int((b - a).total_seconds() // 60)


def build_sql(lo: datetime, hi: datetime, tz: str = "America/New_York") -> str:
    """Rows of {producer, type, source, m, n, worker}. m: local wall-clock minutes since the window's local
    start. source: the CloudEvent source (the resolver's relay rules read it). worker: the Candybar job
    name, else null. Hook handler successes come back as extra rows with producer 'hook-handler', type
    'hook.handler.succeeded'."""
    if not re.fullmatch(r"[A-Za-z0-9_+/-]+", tz):
        raise ValueError(f"bad time zone: {tz!r}")
    lo_s, hi_s = lo.strftime("%Y-%m-%dT%H:%M:%SZ"), hi.strftime("%Y-%m-%dT%H:%M:%SZ")
    local_lo = lo.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M:%S")
    win = f"time >= '{lo_s}'::timestamptz and time < '{hi_s}'::timestamptz"
    minute = f"floor(extract(epoch from ((time at time zone '{tz}') - '{local_lo}'::timestamp)) / 60)::int"
    return (
        "select coalesce(json_agg(r), '[]'::json) from ("
        f" select coalesce(producer, '') as producer, type, source, {minute} as m, count(*)::int as n,"
        " case when type like 'bloodbank.cron.candybar.%' then raw->'data'->>'name' end as worker"
        f" from events where {win} group by 1, 2, 3, 4, 6"
        " union all"
        f" select 'hook-handler', 'hook.handler.succeeded', null, {minute}, count(*)::int, e->>'handler_id'"
        " from events, jsonb_array_elements(case when jsonb_typeof(raw->'data'->'invocation'->'executions') = 'array'"
        " then raw->'data'->'invocation'->'executions' else '[]'::jsonb end) e"
        f" where type = 'bloodbank.agent.hook.updated' and e->>'status' = 'succeeded' and {win} group by 1, 2, 3, 4, 6"
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
    return desk.startswith("33god") or any((desk == cid or desk.startswith(cid + "-")) and rec["first_party"]
                                           for cid, rec in registry.items())


def fold(rows: list[dict], lo: datetime, hi: datetime, registry: "Registry | dict[str, dict]", tz: str,
         profile: str = "public", label: str | None = None, manifests: dict[str, str] | None = None) -> dict[str, Any]:
    reg = _as_registry(registry)
    registry = reg.records
    resolve = reg.owner
    who = worker_resolver(registry, resolve, manifests or {}, HANDLER_OWNERS)
    minutes_total = wall_minutes(lo, hi, tz)
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
        worker = r.get("worker") or ""
        if handler and worker in NO_CREDIT:
            continue            # hook-hub plumbing: its envelope already lit hook-hub
        cid = (who(worker) or None) if (handler or worker) else None
        if handler and (not cid or cid == "hook-hub"):
            continue            # an unowned handler: its hook-hub envelope already lit hook-hub
        res = None if handler else reg.resolve(producer, et, r.get("source"))
        cid = cid or (res.owner if res else None)
        if not cid:
            unmapped[producer or "(none)"] = unmapped.get(producer or "(none)", 0) + n
            continue
        c = comps.setdefault(cid, {"id": cid, "name": registry[cid]["name"], "summary": registry[cid].get("summary", ""),
                                   "first_party": registry[cid]["first_party"], "events": 0, "credited": 0,
                                   "first": m, "last": m})
        c["credited" if handler else "events"] += n
        c["first"] = min(c["first"], m)
        c["last"] = max(c["last"], m)
        s = series.setdefault(cid, {})
        s[m] = s.get(m, 0) + n
        if res is not None and res.via == "desk" and res.key:
            desk = res.key
            if profile == "public" and not _first_party_desk(desk, registry):
                desk = desk_alias.setdefault(desk, f"desk-{len(desk_alias) + 1}")
            d = desks.setdefault(desk, {})
            d[m] = d.get(m, 0) + n
        if handler:
            continue            # handler credit lights the component; it is not a bus event, so no type or moment
        if profile == "public" and et.startswith(PRIVATE_TYPES):
            continue            # counted and lit, never named
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
        "source": "candystore events (Bloodbank archive), producer + type + source + time only",
        "totals": {"events": total, "components": len(comps), "desks": len(desks), "unmapped_events": sum(unmapped.values())},
        "events_by_minute": by_minute,
        "components": sorted(comps.values(), key=lambda c: (-c["events"], -c["credited"], c["id"])),
        "minutes": {cid: sparse(s) for cid, s in sorted(series.items())},
        "desks": {d: sparse(s) for d, s in sorted(desks.items())},
        "types": sorted(({k: v for k, v in t.items() if k != "minutes"} for t in types.values()), key=lambda t: -t["count"]),
        "moments": moments,
        # First-party components that exist but did not publish tonight: a replay can seat them as lit, idle windows.
        "idle": [{"id": cid, "name": rec["name"], "summary": rec.get("summary", "")}
                 for cid, rec in sorted(registry.items()) if rec["first_party"] and cid not in comps],
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
    return fold(query(build_sql(lo, hi, tz)), lo, hi, load(), tz, profile, label, candybar_manifests())
