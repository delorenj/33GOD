"""Holocene read-model collector (SPEC section 1 row 6).

Holocene's ordered (ephemeral) JetStream consumer copies every bloodbank.evt.> message into
~/.local/state/holocene/events.sqlite3 with its stream sequence and collection time. It is the only place
that maps an event id to its JetStream seq, and the only proof that a core-NATS PUB from agent-hooks was
actually stored: a published event missing here 10 s after its time is a Gap.

The table has no index on collected_at, so the cursor range is found by binary search over the integer
primary key (collected_at is insertion-ordered), then only that slice is scanned.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import urllib.parse
from typing import Any

from ..model import BusEvent, Consumer, Ctx, Fragment, Gap, Ids, Source, iso, ms, now_ms, tilde
from . import hookhub
from .candystore import AGENT_PRODUCERS, correlation_id, envelope_artifact, normalize_type, short_type

NAME = "holocene"
DB_PATH = os.path.expanduser(os.environ.get("WAYBILL_HOLOCENE_DB", "~/.local/state/holocene/events.sqlite3"))
CONSUMER = "holocene"
STORE_GRACE_MS = 10_000.0
HOOK_UPDATED = "bloodbank.agent.hook.updated"
SEARCH_SLACK_MS = 30_000.0   # collected_at is not strictly monotonic in cursor; widen the binary search


def _connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect("file:" + urllib.parse.quote(path) + "?mode=ro", uri=True, timeout=5.0)
    con.row_factory = sqlite3.Row
    return con


def first_cursor_at_or_after(con: sqlite3.Connection, at_iso: str) -> int | None:
    """Smallest cursor whose collected_at >= at_iso, by binary search over the rowid. None if none."""
    lo_c, hi_c = con.execute("select min(cursor), max(cursor) from events").fetchone()
    if lo_c is None:
        return None
    first = "select cursor, collected_at from events where cursor >= ? order by cursor limit 1"
    lo, hi = lo_c, hi_c + 1
    while lo < hi:   # lower_bound over cursor values; gaps in the rowid are skipped by jumping to row.cursor
        mid = (lo + hi) // 2
        row = con.execute(first, (mid,)).fetchone()
        if row is None or row["collected_at"] >= at_iso:
            hi = mid
        else:
            lo = row["cursor"] + 1
    row = con.execute(first, (lo,)).fetchone()
    return row["cursor"] if row else None


def matches(env: dict, event_id: str, sid_corr: str, session_id: str, inv_ids: set[str], published: set[str]) -> bool:
    if event_id in published:
        return True
    corr = env.get("correlationid")
    if corr and (corr == sid_corr or corr == session_id or corr in inv_ids):
        return True
    data = env.get("data")
    if isinstance(data, dict) and data.get("session_id") in (session_id, sid_corr):
        return True
    return False


def read_rows(path: str, lo_iso: str, hi_iso: str, needle: str, extra_ids: list[str]) -> tuple[list[dict], dict]:
    """Rows collected in [lo, hi] that mention the session id, are hook.updated, or are one of extra_ids,
    plus store status (max collected_at, checkpoints)."""
    con = _connect(path)
    try:
        start_iso = iso((ms(lo_iso) or 0) - SEARCH_SLACK_MS)
        c0 = first_cursor_at_or_after(con, start_iso)
        status = {"max_collected_at": con.execute("select max(collected_at) from events where cursor = "
                                                  "(select max(cursor) from events)").fetchone()[0]}
        try:
            status["checkpoints"] = [dict(r) for r in con.execute("select * from checkpoints")]
        except sqlite3.Error:
            status["checkpoints"] = []
        rows: list[dict] = []
        if c0 is not None:
            # stop scanning once collected_at is past hi by the slack (the slice is insertion ordered)
            end_iso = iso((ms(hi_iso) or 0) + SEARCH_SLACK_MS)
            c1 = first_cursor_at_or_after(con, end_iso)
            cur_hi = c1 if c1 is not None else (1 << 62)
            rows = [dict(r) for r in con.execute(
                "select cursor, event_id, stream, sequence, subject, type, source, collected_at, envelope from events "
                "where cursor >= ? and cursor <= ? and collected_at >= ? and collected_at <= ? "
                "and (instr(envelope, ?) > 0 or type = ?)",
                (c0, cur_hi, lo_iso, hi_iso, needle, HOOK_UPDATED))]
        have = {r["event_id"] for r in rows}
        want = [i for i in extra_ids if i not in have]
        for i in range(0, len(want), 400):
            chunk = want[i:i + 400]
            rows += [dict(r) for r in con.execute(
                "select cursor, event_id, stream, sequence, subject, type, source, collected_at, envelope from events "
                f"where event_id in ({','.join('?' * len(chunk))})", chunk)]
        rows.sort(key=lambda r: r["cursor"])
        return rows, status
    finally:
        con.close()


def lookup(ids: list[str], path: str | None = None) -> dict[str, dict]:
    """event_id -> {type, subject, stream, sequence, collected_at, envelope(dict)} for ids present in Holocene.
    Uses the UNIQUE index on event_id. Other collectors (logs) use it to attribute ids found in log lines."""
    path = path or DB_PATH
    out: dict[str, dict] = {}
    if not ids:
        return out
    con = _connect(path)
    try:
        for i in range(0, len(ids), 400):
            chunk = ids[i:i + 400]
            for r in con.execute("select event_id, stream, sequence, subject, type, source, collected_at, envelope "
                                 f"from events where event_id in ({','.join('?' * len(chunk))})", chunk):
                d = dict(r)
                try:
                    d["envelope"] = json.loads(d["envelope"])
                except (ValueError, TypeError):
                    d["envelope"] = {}
                out[d["event_id"]] = d
    finally:
        con.close()
    return out


def build(frag: Fragment, ctx: Ctx, rows: list[dict], status: dict, pubs: list[dict], inv_ids: list[str],
          now: float | None = None) -> None:
    now = now if now is not None else now_ms()
    w = ctx.window
    frag.component("holocene", "Holocene", "store")
    sid_corr = correlation_id(w.cli, w.session_id)
    published = {p["event_id"] for p in pubs}
    inv_set = set(inv_ids)
    lo, hi = ctx.margin(2000.0, 0.0)
    seen: dict[str, BusEvent] = {}
    llm_rows = []
    for r in rows:
        try:
            env = json.loads(r["envelope"])
        except (ValueError, TypeError):
            env = {}
        if not isinstance(env, dict):
            env = {}
        eid = r["event_id"]
        if eid in seen or not matches(env, eid, sid_corr, w.session_id, inv_set, published):
            continue
        stored = ms(r["collected_at"])
        et, subject = normalize_type(env) if env else (r["type"], r["subject"])
        t_env = ms(env.get("time")) or stored
        # keep the turn: envelope time inside the window, an event this turn published, or a mirror of its hooks
        mirror = et == HOOK_UPDATED and env.get("correlationid") in inv_set
        if eid not in published and not mirror and not (t_env is not None and lo <= t_env <= hi):
            continue
        if et.startswith("bloodbank.llm."):
            llm_rows.append({"id": eid, "type": et, "seq": r["sequence"], "stream": r["stream"],
                             "collected_at": r["collected_at"]})
            continue
        dapr = env.get("type") == "com.dapr.event.sent"
        ev = BusEvent(
            id=eid, type=et, t=t_env, subject=r["subject"] or subject, stream=r["stream"], seq=r["sequence"],
            stored=stored, correlationid=env.get("correlationid"), causationid=env.get("causationid"),
            producer=env.get("producer") or r.get("source") or env.get("source"),
            publisher_span=Ids.publish(eid) if eid in published else None,
            stored_type=env.get("type") if dapr else None,
            consumers=[Consumer(name=CONSUMER, component="holocene", kind="ephemeral", outcome="collected",
                                filter="bloodbank.evt.>", t=stored, evidence="observed")],
            # same canonical shape as candystore.py, so the artifact id is shared when both saw the envelope
            payload=envelope_artifact(frag, env, ctx.profile, "Dapr envelope (Candystore dead-letters it)" if dapr else None)
            if env else None)
        seen[eid] = ev
        frag.events.append(ev)
    if llm_rows:
        frag.facts["holocene_llm_rows"] = llm_rows   # gateway collector owns llm.* events; seq hints only

    # A core-NATS PUB is proven stored only when Holocene's consumer collected it.
    max_collected = ms(status.get("max_collected_at"))
    for p in pubs:
        eid = p["event_id"]
        et = p.get("event_type") or ""
        if eid in seen or et.startswith("deckard."):
            continue   # attention events go to core-only deckard.evt.attention by design
        if p.get("publish_status") not in ("sent", None):
            continue   # the publisher itself said it did not send
        t_pub = p.get("t_end") or p.get("t_start")
        if t_pub is None or now < t_pub + STORE_GRACE_MS:
            continue
        if max_collected is not None and max_collected < t_pub + STORE_GRACE_MS:
            frag.gaps.append(Gap(
                "holocene", f"{short_type(et)} {eid}: Holocene had not caught up",
                f"Holocene's newest row is {iso(max_collected)}, earlier than the publish + 10 s, so storage is unproven",
                "info", Ids.publish(eid)))
            continue
        frag.gaps.append(Gap(
            "bb-nats", f"{short_type(et)} {eid} published but not seen on the stream",
            "agent-hooks reported publish_status=sent, which is only a core-NATS PONG. Holocene's ordered consumer "
            "never collected it within 10 s, so JetStream BLOODBANK_EVENTS probably never stored it",
            "warn", Ids.publish(eid)))
    frag.facts["holocene"] = {"max_collected_at": status.get("max_collected_at"),
                              "checkpoints": status.get("checkpoints")}


def collect(ctx: Ctx) -> Fragment:
    started = time.monotonic()
    src = Source(id=NAME, kind="sqlite", locator=tilde(DB_PATH) or DB_PATH)
    frag = Fragment(source=src)
    try:
        if not os.path.exists(DB_PATH):
            raise FileNotFoundError(f"Holocene store not found: {tilde(DB_PATH)}")
        w = ctx.window
        lo, hi = ctx.margin(2000.0, STORE_GRACE_MS)
        pubs = hookhub.published_events(ctx)
        inv_ids = hookhub.invocation_ids(ctx)
        needle = correlation_id(w.cli, w.session_id)
        rows, status = read_rows(DB_PATH, iso(lo), iso(hi), needle, [p["event_id"] for p in pubs])
        if needle != w.session_id:
            more, _ = read_rows(DB_PATH, iso(lo), iso(hi), w.session_id, [])
            known = {r["event_id"] for r in rows}
            rows += [r for r in more if r["event_id"] not in known]
        build(frag, ctx, rows, status, pubs, inv_ids)
        src.items = len(frag.events)
        src.status = "ok" if frag.events else "empty"
        if not frag.events:
            frag.gaps.append(Gap("holocene", "Holocene holds no event for this turn",
                                 "the collector may be down or behind; check /api/events/status", "warn"))
    except Exception as exc:  # fail soft
        src.status = "error"
        src.error = f"{type(exc).__name__}: {exc}"
        frag.gaps.append(Gap("holocene", "Holocene read model could not be read", src.error, "warn"))
    src.ms = (time.monotonic() - started) * 1000.0
    return frag
