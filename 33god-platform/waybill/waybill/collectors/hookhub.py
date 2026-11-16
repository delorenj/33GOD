"""hook-hub receipts collector (SPEC section 1 rows 3-5, 8 and 12).

Reads ~/.local/state/33god/hook-hub/receipts.sqlite3 read-only and turns every hook invocation of the
turn into a `hook` span, every execution into a `handler` span, and every publisher execution that names
an event id into a `publish` span. ASM transition re-entries (native='transition', session_id NULL) are
attributed to this session only when their received_at falls inside one of this session's
bloodbank-publisher runs (the publisher feeds ASM, and ASM opens the re-entry frame while it runs).

Other collectors call `invocation_ids(ctx)` and `published_events(ctx)`; both reuse one cached read.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
import urllib.parse
from collections import Counter, defaultdict
from typing import Any

from ..model import Ctx, Finding, Fragment, Gap, Ids, Link, Source, Span, iso, ms, now_ms, tilde

NAME = "hookhub"
DB_PATH = os.path.expanduser(os.environ.get("WAYBILL_HOOKHUB_DB", "~/.local/state/33god/hook-hub/receipts.sqlite3"))

PUBLISHER = "bloodbank-publisher"
# A transition re-entry is attributed to a publisher run when received_at is inside
# [started_at - SLACK_BEFORE, finished_at + SLACK_AFTER]. Measured live: always inside, by 3-46 ms.
SLACK_BEFORE_MS = 25.0
SLACK_AFTER_MS = 150.0
# An execution or invocation that has not moved for this long is reported as stuck.
STUCK_AFTER_MS = 120_000.0

ROLE_PHASE = {
    "session_start": "session_start",
    "prompt_submit": "prompt_submit",
    "pre_tool": "pre_tool",
    "post_tool": "post_tool",
    "turn_completed": "turn_end",
    "session_end": "session_end",
    "invocation_start": "tool",      # SubagentStart fires inside the Agent/Task tool
    "subagent_stop": "tool",
    "invocation_failed": "tool",
}

EXEC_STATUS = {
    "succeeded": "ok",
    "skipped": "skipped",
    "failed": "failed",
    "timed_out": "timeout",
    "selected": "pending",
    "started": "pending",
}

INVOCATION_STATUS = {
    "succeeded": "ok",
    "failed": "failed",
    "skipped": "skipped",
    "received": "pending",
}

_CACHE: dict[tuple, dict[str, Any]] = {}
_LOCK = threading.Lock()


# ---------- pure helpers (unit-tested) ----------

def phase_for(role: str | None, native: str | None) -> str:
    if native == "transition" or not role:
        return "async_after"
    if role == "attention":
        return "pre_tool" if native in ("PermissionRequest", "pre_approval_request") else "turn_end"
    return ROLE_PHASE.get(role, "async_after")


def status_for(exec_status: str | None) -> str:
    return EXEC_STATUS.get(exec_status or "", "unknown")


def short_type(event_type: str | None) -> str:
    if not event_type:
        return "event"
    for prefix in ("bloodbank.", "deckard.v1."):
        if event_type.startswith(prefix):
            return event_type[len(prefix):]
    return event_type


def subject_for(event_type: str | None) -> str | None:
    """Bus subject the publisher uses for an event type (attention goes to core-only deckard.evt.attention)."""
    if not event_type:
        return None
    if event_type.startswith("deckard."):
        return "deckard.evt.attention"
    if event_type.startswith("bloodbank."):
        return "bloodbank.evt." + event_type[len("bloodbank."):]
    return None


def attribute_transitions(transitions: list[dict], publishers: list[dict]) -> tuple[dict[str, dict], list[dict]]:
    """Map transition invocation id -> the publisher execution whose run contains it.

    `publishers` are execution rows (with invocation_id, started_at, finished_at, event_id, event_type) of
    this session's bloodbank-publisher. Among containing runs the nearest preceding start wins.
    Returns (mapping, unattributed transitions).
    """
    runs = []
    for p in publishers:
        s, f = ms(p.get("started_at")), ms(p.get("finished_at"))
        if s is None:
            continue
        runs.append((s, f if f is not None else s, p))
    runs.sort(key=lambda r: r[0])
    mapping: dict[str, dict] = {}
    unattributed: list[dict] = []
    for t in transitions:
        r = ms(t.get("received_at"))
        best = None
        if r is not None:
            for s, f, p in runs:
                if s - SLACK_BEFORE_MS <= r <= f + SLACK_AFTER_MS:
                    if best is None or s > best[0]:
                        best = (s, p)
        if best is None:
            unattributed.append(t)
        else:
            mapping[t["invocation_id"]] = best[1]
    return mapping, unattributed


def run_window(e: dict) -> tuple[float | None, float | None, float | None]:
    """(t0, t1, queued_ms) of the time a handler actually ran.

    started_at..finished_at includes the hub's journal queue wait (measured: a 160 ms nanoleaf run spans 1.6 s),
    so the run is [finished_at - duration_ms, finished_at]; the wait before it is selected_at -> that start.
    Falls back to started_at..finished_at when there is no duration or finished_at.
    """
    sel, st, fin = ms(e.get("selected_at")), ms(e.get("started_at")), ms(e.get("finished_at"))
    dur = e.get("duration_ms")
    try:
        dur_f = float(dur) if dur is not None else None
    except (TypeError, ValueError):
        dur_f = None
    if fin is not None and dur_f is not None and dur_f >= 0:
        t0 = fin - dur_f
        base = sel if sel is not None else st
        queued = max(0.0, t0 - base) if base is not None else None
        return t0, fin, queued
    t0 = st if st is not None else sel
    return t0, fin, None


def _fmt_ms(v: float | None) -> str:
    if v is None:
        return "?"
    if v >= 10_000:
        return f"{v / 1000:.1f} s"
    return f"{int(round(v))} ms"


def handler_summary(e: dict) -> str:
    hid = e.get("handler_id")
    st = e.get("status")
    reason = e.get("reason")
    mode = e.get("mode") or "?"
    dur = e.get("duration_ms")
    if dur is None:
        s, f = ms(e.get("started_at")), ms(e.get("finished_at"))
        dur = (f - s) if (s is not None and f is not None) else None
    if st == "succeeded":
        base = f"{hid} ran {mode} for {_fmt_ms(dur)}"
        if e.get("event_id"):
            base += f", publishing {short_type(e.get('event_type'))} (publish_status={e.get('publish_status') or 'none'})"
        return base + (f" ({reason})" if reason else "")
    if st == "skipped":
        return f"{hid} skipped: {reason or 'no reason recorded'}"
    if st == "failed":
        extra = f", exit {e['exit_code']}" if e.get("exit_code") is not None else ""
        return f"{hid} failed: {reason or 'no reason recorded'} ({_fmt_ms(dur)}{extra})"
    if st == "timed_out":
        return f"{hid} timed out after {_fmt_ms(dur)} and was killed"
    if st in ("selected", "started"):
        return f"{hid} was {st} but never finished (no outcome recorded)"
    return f"{hid}: {st}"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def hook_summary(inv: dict, execs: list[dict], sync_ms: float | None, async_ms: float | None,
                 trigger: dict | None = None) -> str:
    native = inv.get("native")
    if native == "transition":
        ran = [e["handler_id"] for e in execs if e.get("status") == "succeeded"]
        src = short_type(trigger.get("event_type")) if trigger else "a publish"
        return (f"ASM transition re-entry from the {src} publish (synthetic hub invocation, not a user action); "
                f"{', '.join(ran) if ran else 'no handler'} ran")
    if inv.get("status") == "received":
        return f"{native} was claimed by hook-hub but never progressed past 'received'; no handler outcome exists"
    sync = [e for e in execs if e.get("mode") == "sync"]
    asyn = [e for e in execs if e.get("mode") != "sync"]
    if sync:
        head = f"{native} held the CLI for {_fmt_ms(sync_ms)} across {_plural(len(sync), 'sync handler')}"
    else:
        head = f"{native} returned to the CLI at once (no sync handlers)"
    if asyn:
        tail = f"; {_plural(len(asyn), 'async handler')} settled by +{_fmt_ms(async_ms)}"
    else:
        tail = ""
    return head + tail


# ---------- reading ----------

def _connect(path: str) -> sqlite3.Connection:
    uri = "file:" + urllib.parse.quote(path) + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=5.0)
    con.row_factory = sqlite3.Row
    return con


def _chunks(seq: list, n: int = 400):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def read_rows(path: str, session_id: str, cli: str | None, lo_iso: str, hi_iso: str,
              start_lo_iso: str | None = None) -> dict[str, list[dict]]:
    """Raw rows for the session window plus same-cli transitions and their executions and timeline.
    start_lo_iso reaches further back for this session's SessionStart only: a headless CLI starts the session
    several seconds before the prompt, and that hook injected the context the first model call saw."""
    con = _connect(path)
    try:
        invs = [dict(r) for r in con.execute(
            "select * from invocations where session_id = ? and received_at >= ? and received_at <= ? "
            "order by received_at", (session_id, lo_iso, hi_iso))]
        if start_lo_iso:
            invs = [dict(r) for r in con.execute(
                "select * from invocations where session_id = ? and native = 'SessionStart' "
                "and received_at >= ? and received_at < ? order by received_at",
                (session_id, start_lo_iso, lo_iso))] + invs
        trans = []
        if cli:
            # reach back to the earliest session invocation (the SessionStart pre-roll starts before lo_iso): its
            # publisher run opens the ASM none->starting transition re-entry
            tlo = lo_iso
            if invs:
                first = min(r["received_at"] for r in invs)
                ms_first = ms(first)
                if ms_first is not None:
                    tlo = min(lo_iso, iso(ms_first - SLACK_BEFORE_MS - 500.0))
            trans = [dict(r) for r in con.execute(
                "select * from invocations where native = 'transition' and session_id is null and cli = ? "
                "and received_at >= ? and received_at <= ? order by received_at", (cli, tlo, hi_iso))]
        ids = [r["invocation_id"] for r in invs] + [r["invocation_id"] for r in trans]
        execs: list[dict] = []
        events: list[dict] = []
        for chunk in _chunks(ids):
            q = ",".join("?" * len(chunk))
            execs += [dict(r) for r in con.execute(f"select * from executions where invocation_id in ({q})", chunk)]
            events += [dict(r) for r in con.execute(
                f"select sequence, invocation_id, handler_id, status, reason, at from receipt_events "
                f"where invocation_id in ({q})", chunk)]
        events.sort(key=lambda r: r["sequence"])
        return {"invocations": invs, "transitions": trans, "executions": execs, "receipt_events": events}
    finally:
        con.close()


def _key(ctx: Ctx, path: str) -> tuple:
    w = ctx.window
    return (path, w.session_id, w.cli, round(w.t0), round(w.t_end))


def load(ctx: Ctx, path: str | None = None) -> dict[str, Any]:
    """Cached, attributed view of the receipts for this turn window. Raises on DB errors."""
    path = path or DB_PATH
    key = _key(ctx, path)
    with _LOCK:
        if key in _CACHE:
            return _CACHE[key]
        lo, hi = ctx.margin(2000.0, 0.0)
        rows = read_rows(path, ctx.window.session_id, ctx.window.cli, iso(lo), iso(hi),
                         start_lo_iso=iso(ctx.window.t0 - 30000.0))
        data = organize(rows)
        _CACHE[key] = data
        return data


def organize(rows: dict[str, list[dict]]) -> dict[str, Any]:
    """Group executions/timeline by invocation and attribute transitions to this session's publishes."""
    execs_by: dict[str, list[dict]] = defaultdict(list)
    for e in rows["executions"]:
        execs_by[e["invocation_id"]].append(e)
    timeline: dict[str, list[dict]] = defaultdict(list)
    first_seq: dict[str, int] = {}
    handler_seq: dict[tuple[str, str], int] = {}
    for ev in rows["receipt_events"]:
        iid = ev["invocation_id"]
        timeline[iid].append(ev)
        first_seq.setdefault(iid, ev["sequence"])
        if ev.get("handler_id"):
            handler_seq.setdefault((iid, ev["handler_id"]), ev["sequence"])
    for iid, lst in execs_by.items():
        lst.sort(key=lambda e: (handler_seq.get((iid, e["handler_id"]), 1 << 62), e.get("selected_at") or ""))
    session_invs = rows["invocations"]
    publishers = [e for inv in session_invs for e in execs_by.get(inv["invocation_id"], [])
                  if e["handler_id"] == PUBLISHER]
    mapping, unattributed = attribute_transitions(rows["transitions"], publishers)
    trans = [t for t in rows["transitions"] if t["invocation_id"] in mapping]
    invs = session_invs + trans
    invs.sort(key=lambda i: (first_seq.get(i["invocation_id"], 1 << 62), i["received_at"]))
    return {
        "invocations": invs,
        "session_invocations": session_invs,
        "executions": dict(execs_by),
        "timeline": dict(timeline),
        "first_seq": first_seq,
        "triggers": mapping,
        "unattributed_transitions": unattributed,
    }


# ---------- public helpers for other collectors ----------

def earliest_ms(ctx: Ctx) -> float | None:
    """Earliest received_at (epoch ms) among this turn's invocations, SessionStart pre-roll included. None on error."""
    try:
        ts = [ms(i.get("received_at")) for i in load(ctx)["invocations"]]
    except Exception:
        return None
    ts = [t for t in ts if t is not None]
    return min(ts) if ts else None


def transition_invocations(ctx: Ctx) -> list[dict[str, Any]]:
    """Attributed ASM transition re-entry invocations (native='transition') with received_ms. [] on error."""
    try:
        data = load(ctx)
    except Exception:
        return []
    sess = {i["invocation_id"] for i in data["session_invocations"]}
    out = []
    for i in data["invocations"]:
        if i["invocation_id"] in sess:
            continue
        r = dict(i)
        r["received_ms"] = ms(i.get("received_at"))
        r["trigger"] = data["triggers"].get(i["invocation_id"])
        out.append(r)
    return out


def invocation_ids(ctx: Ctx) -> list[str]:
    """Hook invocation ids of this turn (session invocations + attributed ASM transitions). [] on error."""
    try:
        return [i["invocation_id"] for i in load(ctx)["invocations"]]
    except Exception:
        return []


def published_events(ctx: Ctx) -> list[dict[str, Any]]:
    """Events this turn's publisher handlers reported: event_id, event_type, subject, invocation_id, native,
    publish_status, t_start/t_end (epoch ms of the publisher run; the envelope time lies inside). [] on error."""
    try:
        data = load(ctx)
    except Exception:
        return []
    out = []
    for inv in data["invocations"]:
        for e in data["executions"].get(inv["invocation_id"], []):
            if e.get("event_id"):
                out.append({
                    "event_id": e["event_id"], "event_type": e.get("event_type"),
                    "subject": subject_for(e.get("event_type")),
                    "invocation_id": inv["invocation_id"], "native": inv.get("native"),
                    "handler_id": e["handler_id"], "publish_status": e.get("publish_status"),
                    "t_start": ms(e.get("started_at")) or ms(e.get("selected_at")),
                    "t_end": ms(e.get("finished_at")),
                })
    return out


def executions_near(handler_id: str, at_ms: float, radius_ms: float = 2000.0, path: str | None = None) -> list[dict]:
    """Executions of a handler (any session) that finished within radius of at_ms. Used to attribute hub.log lines."""
    path = path or DB_PATH
    con = _connect(path)
    try:
        return [dict(r) for r in con.execute(
            "select e.invocation_id, e.handler_id, e.status, e.reason, e.started_at, e.finished_at, i.session_id "
            "from executions e join invocations i on i.invocation_id = e.invocation_id "
            "where e.handler_id = ? and coalesce(e.finished_at, e.started_at, e.selected_at) between ? and ?",
            (handler_id, iso(at_ms - radius_ms), iso(at_ms + radius_ms)))]
    finally:
        con.close()


# ---------- building the fragment ----------

def build(frag: Fragment, ctx: Ctx, data: dict[str, Any], now: float | None = None) -> None:
    now = now if now is not None else now_ms()
    frag.component("hook-hub", "hook-hub", "handler-host")
    frag.component("agent-hooks", "agent-hooks publisher", "service")
    frag.component("bb-hook", "bb-hook", "service")

    binary_missing: dict[str, list[str]] = defaultdict(list)
    failures: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    stuck_execs: dict[str, list[str]] = defaultdict(list)
    stuck_invs: list[str] = []

    for inv in data["invocations"]:
        iid = inv["invocation_id"]
        hook_id = Ids.hook(iid)
        execs = data["executions"].get(iid, [])
        native = inv.get("native")
        synthetic = native == "transition"
        phase = phase_for(inv.get("role"), native)
        received = ms(inv.get("received_at"))
        # run windows (not started_at..finished_at, which includes the journal queue wait)
        sync_fin = [run_window(e)[1] for e in execs if e.get("mode") == "sync" and e.get("finished_at")]
        async_fin = [run_window(e)[1] for e in execs if e.get("mode") != "sync" and e.get("finished_at")]
        all_fin = [x for x in sync_fin + async_fin if x is not None]
        t1 = max([x for x in sync_fin if x is not None], default=received)
        settled = max(all_fin, default=None)
        sync_ms = (t1 - received) if (t1 is not None and received is not None) else None
        async_ms = (max(async_fin) - received) if (async_fin and received is not None) else None
        counts = Counter(e.get("status") for e in execs)
        trigger = data["triggers"].get(iid) if synthetic else None
        published = next((e for e in execs if e.get("event_id")), None)
        tl = data["timeline"].get(iid, [])
        payload = frag.artifact({
            "invocation": {k: inv.get(k) for k in ("invocation_id", "cli", "native", "role", "event_type", "session_id",
                                                   "identity_kind", "received_at", "updated_at", "status", "deduplicated")},
            "timeline": [[r["sequence"], r.get("handler_id"), r["status"], r.get("reason"), r["at"]] for r in tl],
        }, note="hook-hub receipt timeline, ordered by receipt_events.sequence")
        attrs: dict[str, Any] = {
            "native": native, "role": inv.get("role"), "event_type": inv.get("event_type"), "cli": inv.get("cli"),
            "identity_kind": inv.get("identity_kind"), "deduplicated": inv.get("deduplicated"),
            "receipt_status": inv.get("status"), "at": inv.get("received_at"),
            "settled_at": iso(settled), "sync_ms": sync_ms, "async_ms": async_ms,
            "handlers": dict(counts), "handler_count": len(execs),
            "receipt_seq": data["first_seq"].get(iid),
        }
        if published:
            attrs["published_event_id"] = published["event_id"]
        parent = Ids.PROMPT if inv.get("role") == "prompt_submit" else None
        if synthetic:
            attrs["synthetic"] = True
            if trigger:
                attrs["triggered_by"] = Ids.handler(trigger["invocation_id"], PUBLISHER)
                attrs["triggered_by_event"] = trigger.get("event_id")
                parent = Ids.handler(trigger["invocation_id"], PUBLISHER)
        status = INVOCATION_STATUS.get(inv.get("status") or "", "unknown")
        frag.spans.append(Span(
            id=hook_id, kind="hook", component="hook-hub", name=native or "hook",
            summary=hook_summary(inv, execs, sync_ms, async_ms, trigger), phase=phase,
            t0=received if received is not None else ctx.window.t0, t1=t1, status=status,
            reason=None, sync=not synthetic, parent=parent,
            refs={"invocation_id": iid}, attrs=attrs, payload=payload, evidence=[NAME]))
        if synthetic and trigger:
            frag.links.append(Link(Ids.handler(trigger["invocation_id"], PUBLISHER), hook_id, "triggers",
                                   "ASM re-entry"))
        if inv.get("status") == "received" and received is not None and now - (ms(inv.get("updated_at")) or received) > STUCK_AFTER_MS:
            stuck_invs.append(hook_id)

        for order, e in enumerate(execs):
            hid = e["handler_id"]
            sid = Ids.handler(iid, hid)
            st = e.get("status")
            rt0, fin, queued = run_window(e)
            t0 = rt0 if rt0 is not None else received
            hattrs: dict[str, Any] = {}
            if queued is not None:
                hattrs["queued_ms"] = round(queued, 3)
            frag.spans.append(Span(
                id=sid, kind="handler", component="hook-hub", name=hid, summary=handler_summary(e),
                phase=phase, t0=t0, t1=fin, status=status_for(st), reason=e.get("reason"),
                sync=(e.get("mode") == "sync"), parent=hook_id,
                refs={k: v for k, v in (("invocation_id", iid), ("handler_id", hid), ("event_id", e.get("event_id"))) if v},
                attrs={"handler_id": hid, "mode": e.get("mode"), "exit_code": e.get("exit_code"),
                       "duration_ms": e.get("duration_ms"), "selected_at": e.get("selected_at"),
                       "started_at": e.get("started_at"), "finished_at": e.get("finished_at"),
                       "publish_status": e.get("publish_status"), "event_type": e.get("event_type"),
                       "order": order, "receipt_status": st, **hattrs},
                evidence=[NAME]))
            frag.links.append(Link(hook_id, sid, "runs"))
            if e.get("event_id"):
                _publish_span(frag, e, sid, phase, t0, fin)
            reason = e.get("reason") or ""
            if reason == "handler_binary_missing":
                binary_missing[hid].append(sid)
            if st in ("failed", "timed_out"):
                failures[(hid, st, reason)].append(sid)
            if st in ("selected", "started"):
                last = ms(e.get("started_at")) or ms(e.get("selected_at")) or 0.0
                if now - last > STUCK_AFTER_MS:
                    stuck_execs[hid].append(sid)

    _findings(frag, binary_missing, failures, stuck_execs, stuck_invs)
    if data["invocations"]:
        frag.gaps.append(Gap(
            "bb-hook", "bb-hook fail-open exits are not recorded by hook-hub",
            "bb-hook prints nothing and exits 0 when the hub is down, stalled or out of budget, so a hook that never "
            "reached hook-hub leaves no receipt. Client-side timing comes from the CLI transcript (hook_success "
            "durationMs) where the CLI logs it", "info"))
        frag.gaps.append(Gap(
            "hook-hub", "handler stdout/stderr not stored by hook-hub",
            "receipts keep status, reason, timings and the wrapper's exit code only; the injected text survives "
            "only in the CLI transcript or rollout", "info"))
    ua = data["unattributed_transitions"]
    frag.facts["hookhub"] = {
        "invocations": len(data["session_invocations"]),
        "transitions": len(data["invocations"]) - len(data["session_invocations"]),
        "transitions_unattributed": len(ua),
        "transitions_unattributed_ids": [t["invocation_id"] for t in ua][:50],
    }
    for inv in data["session_invocations"]:
        if inv.get("role") == "prompt_submit":
            frag.facts.setdefault("prompt_invocation_id", inv["invocation_id"])
        if inv.get("role") == "turn_completed":
            frag.facts["stop_invocation_id"] = inv["invocation_id"]


def _publish_span(frag: Fragment, e: dict, handler_span: str, phase: str, t0: float | None, t1: float | None) -> None:
    eid = e["event_id"]
    et = e.get("event_type")
    ps = e.get("publish_status")
    subject = subject_for(et)
    attention = bool(et and et.startswith("deckard."))
    if ps == "sent":
        status = "ok"
    elif ps == "skipped":
        status = "skipped"
    elif e.get("status") in ("failed", "timed_out"):
        status = "failed"
    else:
        status = "unknown"
    if attention:
        summary = (f"agent-hooks put {short_type(et)} on core NATS {subject} (publish_status={ps or 'none'}); "
                   f"attention events are never stored in JetStream")
    elif ps == "sent":
        summary = (f"agent-hooks published {short_type(et)} with a core-NATS PUB; 'sent' only means the PONG came "
                   f"back, not a JetStream ack")
    else:
        summary = f"agent-hooks publish of {short_type(et)} ended with publish_status={ps or 'none'}"
    frag.spans.append(Span(
        id=Ids.publish(eid), kind="publish", component="agent-hooks", name=short_type(et), summary=summary,
        phase=phase, t0=t0 if t0 is not None else 0.0, t1=t1, status=status, sync=False, parent=handler_span,
        refs={"event_id": eid, "invocation_id": e["invocation_id"]},
        attrs={"publish_status": ps, "event_type": et, "subject": subject,
               "transport": "core-nats" + (" (no JetStream)" if attention else " PUB + PONG"),
               "jetstream_ack": False},
        evidence=[NAME]))
    frag.links.append(Link(handler_span, Ids.publish(eid), "calls"))
    frag.links.append(Link(Ids.publish(eid), Ids.evt(eid), "publishes"))


def _findings(frag: Fragment, binary_missing, failures, stuck_execs, stuck_invs) -> None:
    for hid, spans in sorted(binary_missing.items()):
        frag.findings.append(Finding(
            "broken", f"{hid} never runs: binary not on hook-hub PATH",
            f"hook-hub skipped {hid} {_plural(len(spans), 'time')} in this turn with reason handler_binary_missing. "
            f"The hub runs with a system PATH (/usr/local/sbin:...:/snap/bin) that has no mise shims and no "
            f"~/.local/bin, so concerns.py executable() never finds the handler binary and the handler is dead.",
            "hook-hub", spans[:10] + [NAME]))
    for (hid, st, reason), spans in sorted(failures.items()):
        verb = "timed out" if st == "timed_out" else "failed"
        frag.findings.append(Finding(
            "warn", f"{hid} {verb}" + (f" ({reason})" if reason else ""),
            f"{hid} {verb} {_plural(len(spans), 'time')} in this turn"
            + (f" with reason {reason}" if reason else "")
            + ". The receipt's exit_code is the wrapper's code, and the handler's stderr is not stored.",
            "hook-hub", spans[:10] + [NAME]))
    for hid, spans in sorted(stuck_execs.items()):
        frag.findings.append(Finding(
            "warn", f"{hid} stuck in selected/started",
            f"{_plural(len(spans), 'execution')} of {hid} never recorded an outcome. recover() only runs at hub "
            f"start, so a dead child or a lost receipt write leaves the row pending forever.",
            "hook-hub", spans[:10] + [NAME]))
    if stuck_invs:
        frag.findings.append(Finding(
            "warn", "hook invocations stuck in 'received'",
            f"{_plural(len(stuck_invs), 'invocation')} were claimed but never selected handlers (often a SQLite "
            f"OperationalError mid-dispatch; see hub.log). The CLI got an empty reply.",
            "hook-hub", stuck_invs[:10] + [NAME]))


def collect(ctx: Ctx) -> Fragment:
    started = time.monotonic()
    src = Source(id=NAME, kind="sqlite", locator=tilde(DB_PATH) or DB_PATH)
    frag = Fragment(source=src)
    try:
        if not os.path.exists(DB_PATH):
            raise FileNotFoundError(f"receipts database not found: {tilde(DB_PATH)}")
        data = load(ctx)
        build(frag, ctx, data)
        src.items = len(data["invocations"])
        if not data["invocations"]:
            src.status = "empty"
            frag.gaps.append(Gap(
                "hook-hub", f"no hook-hub receipts for session {ctx.window.session_id} in the window",
                "receipts are kept about 4 days, the hub may have been down (bb-hook fails open), or the CLI's hooks "
                "are not wired to bb-hook", "warn"))
    except Exception as exc:  # fail soft
        src.status = "error"
        src.error = f"{type(exc).__name__}: {exc}"
        frag.gaps.append(Gap("hook-hub", "hook-hub receipts could not be read", src.error, "warn"))
    src.ms = (time.monotonic() - started) * 1000.0
    return frag
