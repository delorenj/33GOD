"""Files collector: side-effect state files written during the turn (source 'files').

One 'file' span per file write, Ids.file(path, at_ms), component = the writer.

  * agent-hooks per-session publisher state   ~/.local/state/33god/agent-hooks/<cli>/sessions/<sha256(sid)>.json
    (claude and codex still use the older ~/.<cli>/bloodbank-sessions/<sha256(sid)>.json, which is also where a
    finished session is archived). Content is attached as an artifact: last_event_id and the turn counters.
  * publish-errors.log (it logs every SUCCESSFUL publish despite the name): a line has a time, the publisher pid and
    the subject, but no session id, so lines are attributed by time window only. A busy window is aggregated per subject.
  * ~/.local/state/automaticai/session-proof/<sid>.json   (codex route proof: marker, status)
  * the Hindsight session journal: one write per journal row in the window.
The capture buffer belongs to the hindsight collector and is skipped here.
Files are mutated in place, so only a file whose mtime falls in [t0 - 1 s, t_end] is a write of THIS turn.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from ..model import Ctx, Fragment, Gap, Ids, Link, Source, Span, iso, ms, tilde

NAME = "files"
SOURCE_ID = "files"

HOME = Path.home()
STATE = HOME / ".local/state"
JOURNAL_DIR = HOME / ".agents/journal/sessions"
PROOF_DIR = STATE / "automaticai/session-proof"
RECEIPTS = STATE / "33god/hook-hub/receipts.sqlite3"
# journal row event -> the hook-hub handler that appends it
JOURNAL_WRITERS = {"briefing": "hindsight-briefing", "recall": "hindsight-recall", "recall_skipped": "hindsight-recall",
                   "turn_captured": "hindsight-turn", "turn_skipped": "hindsight-turn", "ask_buffered": "hindsight-turn"}
AGG_THRESHOLD = 40          # more publish lines than this in the window -> one span per subject
_PUB_RE = re.compile(r"^(?P<ts>\S+)\s+\[(?P<pid>\d+)\]\s+(?P<msg>.*)$")


# ---------- pure helpers (unit-tested) ----------

def sid_hash(sid: str) -> str:
    return hashlib.sha256(sid.encode("utf-8")).hexdigest()


def in_window(t: float | None, lo: float, hi: float) -> bool:
    return t is not None and lo <= t <= hi


def parse_publish_line(line: str) -> dict[str, Any] | None:
    m = _PUB_RE.match(line.rstrip("\n"))
    if not m:
        return None
    t = ms(m.group("ts"))
    if t is None:
        return None
    msg = m.group("msg").strip()
    subject = None
    ok = False
    if msg.startswith("published "):
        subject = msg[len("published "):].strip()
        ok = True
    return {"t": t, "pid": int(m.group("pid")), "msg": msg, "subject": subject, "ok": ok}


def read_publish_lines(paths: list[Path], lo: float, hi: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in paths:
        try:
            if p.stat().st_mtime * 1000.0 < lo:
                continue
            with p.open("r", errors="replace") as fh:
                for line in fh:
                    e = parse_publish_line(line)
                    if e and lo <= e["t"] <= hi:
                        e["path"] = str(p)
                        out.append(e)
        except OSError:
            continue
    out.sort(key=lambda e: e["t"])
    return out


def aggregate_publishes(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group by (subject or message): count, first and last time, distinct pids."""
    groups: dict[str, dict[str, Any]] = {}
    for e in lines:
        key = e["subject"] if e["ok"] else e["msg"]
        g = groups.setdefault(key, {"key": key, "ok": e["ok"], "count": 0, "first": e["t"], "last": e["t"],
                                    "pids": set(), "path": e["path"]})
        g["count"] += 1
        g["first"] = min(g["first"], e["t"])
        g["last"] = max(g["last"], e["t"])
        g["pids"].add(e["pid"])
        if e.get("event_id"):
            g.setdefault("event_ids", []).append(e["event_id"])
    out = list(groups.values())
    out.sort(key=lambda g: g["first"])
    return out


def subject_to_type(subject: str | None) -> str | None:
    """bloodbank.evt.agent.tool.requested -> bloodbank.agent.tool.requested (the CloudEvent type)."""
    if not subject:
        return None
    parts = subject.split(".")
    if len(parts) == 5 and parts[0] == "bloodbank" and parts[1] in ("evt", "cmd", "rpy"):
        return ".".join([parts[0], *parts[2:]])
    return None


def attribute_lines(lines: list[dict[str, Any]], pubs: list[dict[str, Any]],
                    before_ms: float = 100.0, after_ms: float = 400.0) -> tuple[list[dict[str, Any]], int]:
    """Match publish-errors.log lines to this session's bloodbank-publisher executions (same event type, line time
    inside [started - before, finished + after]). Each execution is used once. Returns (matched lines, ignored count)."""
    used: set[int] = set()
    out: list[dict[str, Any]] = []
    for ln in lines:
        typ = subject_to_type(ln["subject"])
        if not typ:
            continue
        for i, pub in enumerate(pubs):
            if i in used or pub["event_type"] != typ:
                continue
            if pub["started"] - before_ms <= ln["t"] <= pub["finished"] + after_ms:
                used.add(i)
                out.append({**ln, "event_id": pub["event_id"], "invocation_id": pub["invocation_id"]})
                break
    return out, len(lines) - len(out)


def session_publishes(sid: str, lo: float, hi: float) -> list[dict[str, Any]] | None:
    """bloodbank-publisher executions of one session from the hook-hub receipts (read-only). None = unreadable."""
    try:
        con = sqlite3.connect(f"file:{RECEIPTS}?mode=ro", uri=True, timeout=3)
    except sqlite3.Error:
        return None
    try:
        rows = con.execute(
            "select e.started_at, e.finished_at, e.event_type, e.event_id, e.invocation_id "
            "from executions e join invocations i on i.invocation_id = e.invocation_id "
            "where i.session_id = ? and e.handler_id = 'bloodbank-publisher' and e.event_id is not null "
            "and i.received_at between ? and ?",
            (sid, iso(lo - 5000.0), iso(hi + 5000.0))).fetchall()
    except sqlite3.Error:
        return None
    finally:
        con.close()
    out = []
    for st, fin, typ, eid, inv in rows:
        a, b = ms(st), ms(fin)
        if a is None:
            continue
        out.append({"started": a, "finished": b if b is not None else a, "event_type": typ, "event_id": eid, "invocation_id": inv})
    return out


def mtime_ms(p: Path) -> float | None:
    try:
        return os.stat(p).st_mtime_ns / 1e6
    except OSError:
        return None


# ---------- collector ----------

def collect(ctx: Ctx) -> Fragment:
    started = time.monotonic()
    src = Source(id=SOURCE_ID, kind="filesystem",
                 locator="~/.local/state/33god/agent-hooks, ~/.<cli>/bloodbank-sessions, ~/.local/state/automaticai/session-proof, ~/.agents/journal/sessions")
    frag = Fragment(source=src)
    for name in ("_state_file", "_publish_log", "_session_proof", "_journal"):
        try:
            globals()[name](ctx, frag)
        except Exception as ex:  # fail soft, per sub-source
            src.status = "error"
            src.error = f"{name}: {type(ex).__name__}: {ex}"[:300]
            frag.gaps.append(Gap("files", f"file spans ({name.strip('_')})", f"error: {src.error}", "warn"))
    src.items = len(frag.spans)
    if src.status == "ok" and not frag.spans:
        src.status = "empty"
    src.ms = (time.monotonic() - started) * 1000.0
    return frag


def _comp(frag: Fragment, cid: str, name: str, kind: str = "service") -> str:
    return frag.component(cid, name, kind)


def _file_span(frag: Fragment, ctx: Ctx, *, path: str, key_path: str | None = None, at: float, component: str,
               name: str, summary: str, phase: str, attrs: dict[str, Any], payload: str | None = None,
               t1: float | None = None, status: str = "ok", reason: str | None = None) -> Span:
    attrs = {"path": tilde(path), "at": iso(at), **attrs}
    s = Span(id=Ids.file(key_path or path, at), kind="file", component=component, name=name, summary=summary,
             phase=phase, t0=at, t1=t1, status=status, reason=reason, sync=False, attrs=attrs, payload=payload,
             evidence=[SOURCE_ID])
    frag.spans.append(s)
    return s


# ----- agent-hooks per-session publisher state -----

def _state_candidates(cli: str, sid: str) -> list[Path]:
    h = sid_hash(sid)
    return [
        STATE / "33god/agent-hooks" / cli / "sessions" / f"{h}.json",
        HOME / f".{cli}" / "bloodbank-sessions" / f"{h}.json",   # legacy + archive on session end
    ]


def _state_file(ctx: Ctx, frag: Fragment) -> None:
    w = ctx.window
    lo, hi = w.t0 - 1000.0, w.t_end
    _comp(frag, "agent-hooks", "agent-hooks publisher", "handler-host")
    found = False
    for p in _state_candidates(w.cli, w.session_id):
        t = mtime_ms(p)
        if t is None:
            continue
        found = True
        try:
            data = json.loads(p.read_text())
        except (OSError, ValueError):
            data = None
        if not in_window(t, lo, hi):
            frag.gaps.append(Gap(
                "agent-hooks", "per-session publisher state at the time of this turn",
                f"{tilde(str(p))} was last written {iso(t)}, outside the window: it is rewritten in place on every event, "
                "so the file shows the latest state, not this turn's", "info"))
            continue
        art = None
        if isinstance(data, dict):
            d = dict(data)
            if ctx.profile == "public" and d.get("working_directory"):
                d["working_directory"] = tilde(d["working_directory"])
            art = frag.artifact(d, note="agent-hooks per-session publisher state (causation chain head and counters)")
        d = data if isinstance(data, dict) else {}
        last = d.get("last_event_id")
        sp = _file_span(
            frag, ctx, path=str(p), at=t, component="agent-hooks", name="session state",
            summary=(f"agent-hooks wrote the per-session publisher state {tilde(str(p))} "
                     f"(last_event_id {str(last)[:8] + '…' if last else 'n/a'}, turn {d.get('conversation_turn_number')}, "
                     f"{d.get('turn_number')} tool calls counted)"),
            phase="async_after",
            attrs={k: d.get(k) for k in ("last_event_id", "current_turn_id", "turn_number", "conversation_turn_number", "tools_used")
                   if d.get(k) is not None} | ({"archived": True} if "bloodbank-sessions" in str(p) else {}),
            payload=art)
        if last:
            # the publisher rewrites this file after each publish; the last one it records wrote this version
            sp.refs["event_id"] = str(last)
            frag.links.append(Link(Ids.publish(str(last)), sp.id, "writes", "per-session publisher state"))
    if not found:
        frag.gaps.append(Gap("agent-hooks", "per-session publisher state file",
                             f"no state file for session ({w.cli}, sha256 {sid_hash(w.session_id)[:12]}…) at either path", "info"))


# ----- publish-errors.log -----

def _publish_paths(cli: str) -> list[Path]:
    paths: list[Path] = []
    for base in (HOME / f".{cli}" / "bloodbank-sessions", STATE / "33god/agent-hooks" / cli):
        paths += [Path(str(base / "publish-errors.log") + ".1"), base / "publish-errors.log"]
    return [p for p in paths if p.exists()]


def _publish_log(ctx: Ctx, frag: Fragment) -> None:
    w = ctx.window
    lo, hi = w.t0 - 1000.0, w.t_end
    paths = _publish_paths(w.cli)
    if not paths:
        return
    lines = read_publish_lines(paths, lo, hi)
    if not lines:
        return
    _comp(frag, "agent-hooks", "agent-hooks publisher", "handler-host")
    pubs = session_publishes(w.session_id, lo, hi)
    if pubs:
        matched, ignored = attribute_lines(lines, pubs)
        tool_lines = [e for e in matched if ".tool." in (e["subject"] or "")]
        crowded = len(tool_lines) > AGG_THRESHOLD     # a long tool loop would bury the waterfall in 1-row spans
        single = [e for e in matched if not (crowded and e in tool_lines)]
        for e in single:
            sp = _publish_span(frag, ctx, e["path"], e["t"], e["subject"], 1, True, e["t"], {e["pid"]},
                               attribution="matched to a bloodbank-publisher receipt of this session",
                               refs={"event_id": e["event_id"], "invocation_id": e["invocation_id"]})
            frag.links.append(Link(Ids.publish(e["event_id"]), sp.id, "writes", "publish log line"))
        if crowded:
            for g in aggregate_publishes(tool_lines):
                sp = _publish_span(frag, ctx, g["path"], g["first"], g["key"], g["count"], True, g["last"], g["pids"],
                                   attribution="matched to this session's publisher receipts, aggregated per subject")
                for eid in g.get("event_ids") or []:
                    frag.links.append(Link(Ids.publish(eid), sp.id, "writes", "publish log line"))
        frag.gaps.append(Gap(
            "agent-hooks", "other publish-errors.log lines in the window",
            f"publish-errors.log has no session id: {len(matched)} lines matched this session's publisher receipts "
            f"(event type + time); {ignored} lines from other sessions were ignored", "info"))
        return
    note = ("publish-errors.log carries no session id and the hook-hub receipts were unavailable or empty for this "
            f"session; lines are attributed by time window only and include other sessions ({len(lines)} lines, "
            f"{len({l['pid'] for l in lines})} publisher pids)")
    if len(lines) <= AGG_THRESHOLD:
        for e in lines:
            _publish_span(frag, ctx, e["path"], e["t"], e["subject"] or e["msg"], 1, e["ok"], e["t"], {e["pid"]})
    else:
        for g in aggregate_publishes(lines):
            _publish_span(frag, ctx, g["path"], g["first"], g["key"], g["count"], g["ok"], g["last"], g["pids"])
    frag.gaps.append(Gap("agent-hooks", "which publish-errors.log lines belong to this session", note, "info"))


def _publish_span(frag: Fragment, ctx: Ctx, path: str, t0: float, what: str, count: int, ok: bool,
                  last: float, pids: set[int], attribution: str = "time window only (ambiguous)",
                  refs: dict[str, Any] | None = None) -> Span:
    key = f"{path}#{what}#{min(pids) if len(pids) == 1 else 'multi'}"
    attrs: dict[str, Any] = {"subject": what if ok else None, "message": None if ok else what, "count": count,
                             "pids": sorted(pids)[:8], "attribution": attribution}
    summary = (f"agent-hooks logged {'a publish of ' if ok else ''}{what}"
               + (f" x{count}" if count > 1 else "") + f" to {tilde(path)}")
    sp = _file_span(frag, ctx, path=path, key_path=key, at=t0, component="agent-hooks", name="publish-errors.log",
                    summary=summary, phase="async_after", attrs={k: v for k, v in attrs.items() if v is not None},
                    t1=last if count > 1 and last > t0 else None, status="ok" if ok else "failed",
                    reason=None if ok else "publish_error")
    if refs:
        sp.refs.update(refs)
    return sp


# ----- codex route proof -----

def _session_proof(ctx: Ctx, frag: Fragment) -> None:
    w = ctx.window
    p = PROOF_DIR / f"{w.session_id}.json"
    t = mtime_ms(p)
    if t is None:
        return
    if not in_window(t, w.t0 - 1000.0, w.t_end):
        frag.gaps.append(Gap("hook-hub", "codex route proof at the time of this turn",
                             f"{tilde(str(p))} last written {iso(t)}, outside the window (rewritten in place)", "info"))
        return
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        d = {}
    _comp(frag, "hook-hub", "hook-hub", "handler-host")
    art = frag.artifact(d, note="AutomaticAI route proof (codex only): marker and verification status") if d else None
    sp = _file_span(frag, ctx, path=str(p), at=t, component="hook-hub", name="route proof",
               summary=(f"hook-hub (automaticai-routing) wrote the codex route proof: status {d.get('status')}, "
                        f"availability {d.get('proof_availability')}"),
               phase="async_after",
               attrs={k: d.get(k) for k in ("status", "proof_availability", "migration_requested") if d.get(k) is not None}
               | {"marker_present": bool(d.get("marker"))},
               payload=art)
    # automaticai-routing-start writes it on the prompt, automaticai-routing-final rewrites it after Stop
    if w.turn_end is not None and t >= w.turn_end and w.stop_invocation_id:
        writer = Ids.handler(w.stop_invocation_id, "automaticai-routing-final")
    elif w.prompt_invocation_id:
        writer = Ids.handler(w.prompt_invocation_id, "automaticai-routing-start")
    else:
        writer = None
    if writer:
        frag.links.append(Link(writer, sp.id, "writes", "route proof"))


# ----- hindsight journal writes -----

def _journal(ctx: Ctx, frag: Fragment) -> None:
    w = ctx.window
    p = JOURNAL_DIR / f"{w.cli}-{w.session_id}.jsonl"
    try:
        fh = p.open("r", errors="replace")
    except OSError:
        return
    lo, hi = w.t0 - 1000.0, w.t_end
    with fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            t = ms(r.get("ts")) if isinstance(r, dict) else None
            if not in_window(t, lo, hi):
                continue
            _comp(frag, "hindsight", "Hindsight", "memory")
            ev = r.get("event")
            sp = _file_span(frag, ctx, path=str(p), at=t, component="hindsight", name=f"journal {ev}",
                       summary=f"Hindsight appended a '{ev}' row to the session journal {tilde(str(p))}",
                       phase=("turn_end" if str(ev).startswith("turn_") else "prompt_submit" if ev in ("recall", "recall_skipped")
                              else "session_start" if ev == "briefing" else "async_after"),
                       attrs={"event": ev, "invocation_id": r.get("invocation_id")})
            inv = r.get("invocation_id")
            if inv:
                sp.refs["invocation_id"] = inv
                writer = JOURNAL_WRITERS.get(str(ev)) or ("hindsight-session-end" if str(ev).startswith("session_flush") else None)
                frag.links.append(Link(Ids.handler(inv, writer) if writer else Ids.hook(inv), sp.id, "writes", "journal row"))
