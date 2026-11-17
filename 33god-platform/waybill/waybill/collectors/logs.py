"""Container and hub log collector (SPEC section 1 rows 7, 11 and 12).

Downstream core-NATS and Dapr consumers leave no ack record anywhere; their docker log lines are the only
evidence they acted. This collector reads, read-only:

- bloodbank-ntfy-router: 'routed:' / 'rate-limited:' / 'digested:' / 'duplicate:' lines. They carry the
  event TYPE only, so each one is matched by time to an event this turn published and handed to the
  assembler as an attrs._join hint (plus attrs._join.event_id when the time match is unambiguous).
- enricher: 'Successfully embedded tool event <id>', 'DB Error on <id>', 'DROP embedding for <id>: parent event never appeared', session roll-ups.
- bloodbank-turn-enricher: 'annotated: <turn.completed id> ...' / 'noise: <id> ...'. Its json-file log
  cannot be read with --since/--until (docker returns nothing), so an empty --since read falls back to --tail.
- candystore-daprd: 'DROP status returned ... pub/sub event <id>' (dead-letters), 'RETRY'.
- ~/.local/state/33god/hook-hub/hub.log: local-time (with offset), second-precision lines with no session
  or invocation id: OperationalError, JSONDecodeError, TIMEOUT.

Every docker read uses `docker logs -t` so timestamps are the daemon's UTC receive time (ns precision).
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ..model import Ctx, Finding, Fragment, Gap, Ids, Link, Source, Span, is_enricher_report, iso, ms, tilde
from . import hookhub

NAME = "logs"
NTFY = os.environ.get("WAYBILL_NTFY_CONTAINER", "bloodbank-ntfy-router")
ENRICHER = os.environ.get("WAYBILL_ENRICHER_CONTAINER", "enricher")
TURN_ENRICHER = os.environ.get("WAYBILL_TURN_ENRICHER_CONTAINER", "bloodbank-turn-enricher")
DAPRD = os.environ.get("WAYBILL_DAPRD_CONTAINER", "candystore-daprd")
JEV = os.environ.get("WAYBILL_JEV_CONTAINER", "jev-litellm")
HUB_LOG = os.path.expanduser(os.environ.get("WAYBILL_HUB_LOG", "~/.local/state/33god/hook-hub/hub.log"))
TAIL_STEPS = (2000, 20000, 200000)
TAIL_CALL_CAP_S = 8.0       # one `docker logs --tail N` call may not eat the whole collector budget (finding 23)
NTFY_NOISE = ("bloodbank.cron.",)   # scheduler chatter: hundreds of lines a minute, never part of a turn
JEV_PATH = "/typesafe/v1/systemone"
MATCH_BEFORE_MS = 50.0      # a log line can precede the publisher run's recorded start by clock skew only
MATCH_AFTER_MS = 3000.0     # how long after its publish a consumer line is still attributed to the event

_TS = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z)\s(.*)$")
_NTFY = re.compile(r"\[ntfy-router\]\s+\w+\s+(routed|rate-limited|digested|duplicate):\s+(\S+)\s*$")
_EMBED = re.compile(r"Successfully embedded tool event ([0-9a-fA-F-]{36})")
_DBERR = re.compile(r"DB Error on ([0-9a-fA-F-]{36}):\s*(.*)$")
# the enricher gave up on an embedding after the bounded wait/retry for a parent event that never appeared (33GOD-95)
_PARENT_DROP = re.compile(r"DROP embedding for ([0-9a-fA-F-]{36}): (parent event never appeared.*)$")
_ROLLUP = re.compile(r"Session (\S+) ended\. Rolling up events")
_NOEVENTS = re.compile(r"No events found for session (\S+)")
_ANNOT = re.compile(r"\[turn-enricher\]\s+\w+\s+annotated:\s+([0-9a-fA-F-]{36})\s+signal=([\d.]+)\s+action=(.*?)\s+"
                    r"artifacts=(\d+)\s+blocker=(.*)$")
_NOISE = re.compile(r"\[turn-enricher\]\s+\w+\s+noise:\s+([0-9a-fA-F-]{36})\s+\(signal=([\d.]+)\)")
_JEV = re.compile(r'"POST ' + re.escape("/typesafe/v1/systemone") + r' HTTP/[\d.]+"\s+(\d{3})')
_DAPR = re.compile(r"(DROP|RETRY) status returned from app while processing pub/sub event ([0-9a-fA-F-]{36})")
_HUB = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:?\d\d)?)\s+\[(\d+)\]\s+(.*)$")
_HUB_INTEREST = re.compile(r"OperationalError|JSONDecodeError|TIMEOUT|TimeoutError|no budget left")
_HUB_TIMEOUT = re.compile(r"handler (\S+): TIMEOUT after ([\d.]+)s")
_HUB_ASYNC = re.compile(r"async handler (\S+) failed: (\w+)")

NTFY_STATUS = {"routed": ("ok", None), "digested": ("ok", "digested"),
               "rate-limited": ("dropped", "rate_limited"), "duplicate": ("skipped", "duplicate")}


# ---------- pure parsing (unit-tested) ----------

def parse_docker_lines(text: str) -> list[tuple[float, str]]:
    """`docker logs -t` output -> [(epoch ms, message)]; lines without a timestamp are dropped."""
    out = []
    for raw in (text or "").splitlines():
        m = _TS.match(raw)
        if not m:
            continue
        t = ms(m.group(1))
        if t is not None:
            out.append((t, m.group(2)))
    return out


def parse_ntfy(lines: list[tuple[float, str]]) -> list[dict]:
    out = []
    for t, msg in lines:
        m = _NTFY.search(msg)
        if m and m.group(2).startswith(("bloodbank.", "com.dapr")):
            out.append({"t": t, "kind": m.group(1), "type": m.group(2)})
    return out


def match_by_time(lines: list[dict], expected: list[dict]) -> list[dict]:
    """Greedy, earliest-first: each expected {event_id, type, t_lo, t_hi} takes the first unused line of its
    type in [t_lo, t_hi]. Returns [{line, expected, candidates}] where candidates counts same-type lines in range."""
    by_type: dict[str, list[dict]] = defaultdict(list)
    for ln in sorted(lines, key=lambda x: x["t"]):
        by_type[ln["type"]].append(ln)
    used: set[int] = set()
    out = []
    for ex in sorted(expected, key=lambda e: e["t_lo"]):
        pool = [ln for ln in by_type.get(ex["type"], []) if ex["t_lo"] <= ln["t"] <= ex["t_hi"]]
        pick = next((ln for ln in pool if id(ln) not in used), None)
        if pick is None:
            continue
        used.add(id(pick))
        out.append({"line": pick, "expected": ex, "candidates": len(pool)})
    return out


def hub_template(msg: str) -> str:
    s = re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F-]{27}", "<id>", msg)
    s = re.sub(r"\d+(\.\d+)?s\b", "<n>s", s)
    return s


def parse_hub_log(text: str, lo: float, hi: float) -> list[dict]:
    out = []
    for raw in (text or "").splitlines():
        m = _HUB.match(raw)
        if not m:
            continue
        t = ms(m.group(1))
        if t is None or not (lo <= t <= hi):
            continue
        msg = m.group(3)
        if _HUB_INTEREST.search(msg):
            out.append({"t": t, "pid": m.group(2), "msg": msg, "template": hub_template(msg)})
    return out


def parse_annotation(msg: str) -> dict | None:
    m = _ANNOT.search(msg)
    if m:
        action = m.group(3).strip()
        if len(action) >= 2 and action[0] == action[-1] and action[0] in "'\"":
            action = action[1:-1]
        blocker = m.group(5).strip()
        if blocker == "None":
            blocker = None
        elif len(blocker) >= 2 and blocker[0] == blocker[-1] and blocker[0] in "'\"":
            blocker = blocker[1:-1]
        return {"id": m.group(1), "outcome": "annotated", "signal": float(m.group(2)), "action": action,
                "artifacts": int(m.group(4)), "blocker": blocker}
    m = _NOISE.search(msg)
    if m:
        return {"id": m.group(1), "outcome": "noise", "signal": float(m.group(2))}
    return None


def parse_jev(lines: list[tuple[float, str]]) -> list[dict]:
    """jev-litellm access-log lines for POST /typesafe/v1/systemone -> [{t, code}]; t is the RESPONSE time."""
    out = []
    for t, msg in lines:
        m = _JEV.search(msg)
        if m:
            out.append({"t": t, "code": int(m.group(1))})
    return out


# ---------- I/O ----------

def _run(argv: list[str], timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, errors="replace", timeout=timeout)


def docker_lines(container: str, lo: float, hi: float, timeout: float,
                 deadline: float | None = None) -> tuple[list[tuple[float, str]], str]:
    """Lines of a container's log in [lo, hi] (epoch ms) and how they were read ('since', 'tail:N', or either with a
    ':partial' suffix when the budget ran out). A tail read that times out keeps what the earlier, smaller tail got."""
    p = _run(["docker", "logs", "-t", "--since", iso(lo), "--until", iso(hi), container], timeout)
    if p.returncode != 0:
        raise RuntimeError(f"docker logs {container}: {(p.stderr or '').strip()[:300]}")
    lines = parse_docker_lines(p.stdout) + parse_docker_lines(p.stderr)
    if lines:
        return sorted(lines, key=lambda x: x[0]), "since"
    mode = "since"
    for n in TAIL_STEPS:   # json-file logs whose --since read comes back empty (turn-enricher)
        left = None if deadline is None else deadline - time.monotonic()
        if left is not None and left <= 0.5:
            mode += ":partial"
            break
        budget = min(timeout, TAIL_CALL_CAP_S * (1 + TAIL_STEPS.index(n)), left if left is not None else timeout)
        try:
            p = _run(["docker", "logs", "-t", "--tail", str(n), container], budget)
        except subprocess.TimeoutExpired:
            mode += ":partial"
            break
        if p.returncode != 0:
            break
        got = parse_docker_lines(p.stdout) + parse_docker_lines(p.stderr)
        mode = f"tail:{n}"
        lines = got
        if not got or min(t for t, _ in got) <= lo or len(got) < n:
            break
    return sorted([(t, m) for t, m in lines if lo <= t <= hi], key=lambda x: x[0]), mode


def read_hub_log(lo: float, hi: float) -> list[dict]:
    out: list[dict] = []
    for path in (HUB_LOG + ".1", HUB_LOG):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                out += parse_hub_log(fh.read(), lo, hi)
        except FileNotFoundError:
            continue
    return out


# ---------- building ----------

def _pub_index(pubs: list[dict]) -> dict[str, dict]:
    return {p["event_id"]: p for p in pubs}


def _expected(pubs: list[dict], extra: list[dict]) -> list[dict]:
    out = []
    for p in pubs:
        et = p.get("event_type") or ""
        if not et.startswith("bloodbank.") or p.get("publish_status") not in ("sent", None):
            continue
        t0 = p.get("t_start") or p.get("t_end")
        t1 = p.get("t_end") or t0
        if t0 is None:
            continue
        out.append({"event_id": p["event_id"], "type": et, "t_lo": t0 - MATCH_BEFORE_MS, "t_hi": t1 + MATCH_AFTER_MS,
                    "t_pub": t1})
    return out + extra


def _ntfy_summary(kind: str, st: str, when: str) -> str:
    return {
        "routed": f"ntfy-router routed {st} to ntfy (push sent){when}",
        "digested": f"ntfy-router folded {st} into the 300 s digest{when}",
        "rate-limited": f"ntfy-router rate-limited {st}: the notification was dropped by the token bucket",
        "duplicate": f"ntfy-router ignored {st} as a duplicate",
    }[kind]


def build_ntfy(frag: Fragment, lines: list[dict], expected: list[dict]) -> int:
    n = 0
    matched = match_by_time(lines, expected)
    used = {id(m["line"]) for m in matched}
    for m in matched:
        ln, ex = m["line"], m["expected"]
        status, reason = NTFY_STATUS[ln["kind"]]
        et = ln["type"]
        st = hookhub.short_type(et)
        exact = m["candidates"] == 1 and ex.get("event_id")
        key = ex.get("event_id") or str(int(ln["t"]))
        lag = ln["t"] - ex["t_pub"] if ex.get("t_pub") else None
        when = f" {int(round(lag))} ms after publish" if lag is not None and lag >= 0 else ""
        join = {"event_type": et, "near": ex.get("t_pub") or ln["t"], "window_ms": MATCH_AFTER_MS,
                "consumer": "ntfy-router", "consumer_kind": "core", "outcome": ln["kind"], "link": "delivers"}
        if exact:
            join["event_id"] = ex["event_id"]
        frag.spans.append(Span(
            id=Ids.notify("ntfy-router", key), kind="notify", component="ntfy-router", name=f"{ln['kind']} {st}",
            summary=_ntfy_summary(ln["kind"], st, when), phase="async_after", t0=ln["t"], t1=None, status=status,
            reason=reason, sync=False,
            refs={"event_id": ex["event_id"]} if exact else {},
            attrs={"_join": join, "match": "type+time", "candidates": m["candidates"], "ambiguous": m["candidates"] > 1,
                   "guess_event_id": ex.get("event_id"), "at": iso(ln["t"]), "log": f"{ln['kind']}: {et}"},
            evidence=[NAME]))
        n += 1
    # Every other line is offered to the assembler, which knows ALL of the turn's events (llm.usage.recorded,
    # allowance, agent.session.annotated (legacy: report.session.completed), Dapr-wrapped ones ...) and matches by type + stored time. Lines that match
    # no event of this turn are shared-log noise and are dropped there (join.optional), never a gap (finding 7).
    seq: dict[int, int] = defaultdict(int)
    for ln in sorted(lines, key=lambda x: x["t"]):
        if id(ln) in used or ln["type"].startswith(NTFY_NOISE):
            continue
        status, reason = NTFY_STATUS[ln["kind"]]
        et = ln["type"]
        st = hookhub.short_type(et)
        ms_key = int(ln["t"])
        seq[ms_key] += 1
        key = f"{ms_key}.{seq[ms_key]}" if seq[ms_key] > 1 else str(ms_key)
        join = {"event_type": et, "near": ln["t"], "window_ms": MATCH_AFTER_MS, "consumer": "ntfy-router",
                "consumer_kind": "core", "outcome": ln["kind"], "link": "delivers", "optional": True,
                "use_stored": True, "match": "type+time"}
        frag.spans.append(Span(
            id=Ids.notify("ntfy-router", key), kind="notify", component="ntfy-router", name=f"{ln['kind']} {st}",
            summary=_ntfy_summary(ln["kind"], st, ""), phase="async_after", t0=ln["t"], t1=None, status=status,
            reason=reason, sync=False, refs={},
            attrs={"_join": join, "at": iso(ln["t"]), "log": f"{ln['kind']}: {et}"}, evidence=[NAME]))
    return n


def _consume(frag: Fragment, consumer: str, component: str, eid: str, et: str | None, t0: float, t1: float | None,
             status: str, reason: str | None, summary: str, kind: str, outcome: str, attrs: dict | None = None) -> str:
    sid = Ids.consume(consumer, eid)
    a = {"_join": {"event_type": et or "", "near": t0, "window_ms": MATCH_AFTER_MS, "consumer": consumer,
                   "consumer_kind": kind, "outcome": outcome, "link": "delivers", "event_id": eid},
         "at": iso(t1 if t1 is not None else t0)}
    a.update(attrs or {})
    frag.spans.append(Span(
        id=sid, kind="consume", component=component, name=hookhub.short_type(et) if et else consumer,
        summary=summary, phase="async_after", t0=t0, t1=t1, status=status, reason=reason, sync=False,
        refs={"event_id": eid}, attrs=a, evidence=[NAME]))
    return sid


def build_enricher(frag: Fragment, ctx: Ctx, lines: list[tuple[float, str]], pubs: dict[str, dict]) -> tuple[int, list[str]]:
    n = 0
    fk: list[str] = []
    ended = next((p for p in pubs.values() if (p.get("event_type") or "").endswith("session.ended")), None)
    for t, msg in lines:
        m = _EMBED.search(msg)
        if m and m.group(1) in pubs:
            p = pubs[m.group(1)]
            t0 = p.get("t_end") or t
            _consume(frag, "enricher-events", "enricher", p["event_id"], p.get("event_type"), t0, t, "ok",
                     "embedded", f"enricher embedded {hookhub.short_type(p.get('event_type'))} "
                                 f"{_ms_txt(t - t0)} after publish", "durable", "enriched")
            n += 1
            continue
        m = _DBERR.search(msg) or _PARENT_DROP.search(msg)
        if m and m.group(1) in pubs:
            p = pubs[m.group(1)]
            t0 = p.get("t_end") or t
            sid = _consume(frag, "enricher-events", "enricher", p["event_id"], p.get("event_type"), t0, t, "failed",
                           "db_error", f"enricher failed to embed {hookhub.short_type(p.get('event_type'))}: "
                                       f"{m.group(2)[:160]}", "durable", "dropped", {"error": m.group(2)[:500]})
            fk.append(sid)
            n += 1
            continue
        m = _ROLLUP.search(msg) or _NOEVENTS.search(msg)
        if m and m.group(1) == ctx.window.session_id and ended:
            noevents = "No events found" in msg
            sid = Ids.consume("enricher-events", ended["event_id"])
            existing = next((s for s in frag.spans if s.id == sid), None)
            if existing:
                existing.t1 = t
                if noevents:
                    existing.reason = "no_events_found"
                    existing.summary = "enricher rolled up the session on session.ended but found no events for it"
                continue
            _consume(frag, "enricher-events", "enricher", ended["event_id"], ended.get("event_type"),
                     ended.get("t_end") or t, t, "ok", "no_events_found" if noevents else "rollup",
                     "enricher rolled up the session on session.ended" + (" but found no events for it" if noevents else ""),
                     "durable", "enriched")
            n += 1
    return n, fk


def _ms_txt(v: float) -> str:
    return f"{v / 1000:.1f} s" if v >= 10_000 else f"{int(round(v))} ms"


def build_turn_enricher(frag: Fragment, lines: list[tuple[float, str]], pubs: dict[str, dict]) -> tuple[int, list[dict]]:
    n = 0
    annotated: list[dict] = []
    for t, msg in lines:
        a = parse_annotation(msg)
        if not a or a["id"] not in pubs:
            continue
        p = pubs[a["id"]]
        t0 = p.get("t_end") or t
        if a["outcome"] == "annotated":
            summary = (f"turn-enricher annotated the turn (signal {a['signal']:.2f}: '{a.get('action')}')"
                       + (f", blocker: {a['blocker']}" if a.get("blocker") else ""))
            status, reason, outcome = "ok", "annotated", "enriched"
            annotated.append({"t": t, "source_id": a["id"], "t_pub": t0})
        else:
            summary = f"turn-enricher classified the turn as noise (signal {a['signal']:.2f}); nothing was published"
            status, reason, outcome = "skipped", "noise", "ignored"
        attrs = {k: v for k, v in a.items() if k not in ("id", "outcome")}
        _consume(frag, "turn-enricher", "turn-enricher", a["id"], p.get("event_type"), t0, t, status, reason,
                 summary, "core", outcome, attrs)
        n += 1
    return n, annotated


JEV_BEFORE_MS = 100.0   # a model call's access-log line may precede the enricher's own 'annotated' line by clock skew


def build_jev(frag: Fragment, jev: list[dict], annotated: list[dict]) -> int:
    """turn-enricher's Jev extractor call (finding 8). jev-litellm logs only the RESPONSE time, so the span is an
    instant at that time; the line is chosen as the last completed POST /typesafe/v1/systemone between the
    turn.completed publish and the 'annotated' line (the enricher publishes only after its extractors answered).
    Other clients share that endpoint (Hindsight's extraction), so more than one candidate = ambiguous."""
    n = 0
    for a in annotated:
        lo, hi = (a.get("t_pub") or a["t"]) - JEV_BEFORE_MS, a["t"] + JEV_BEFORE_MS
        cands = [j for j in jev if lo <= j["t"] <= hi]
        if not cands:
            continue
        pick = max(cands, key=lambda j: j["t"])
        sid = Ids.jev_llm(a["source_id"])
        ok = 200 <= pick["code"] < 300
        frag.component("jev-litellm", "jev-litellm", "service")
        parent = Ids.consume("turn-enricher", a["source_id"])
        frag.spans.append(Span(
            id=sid, kind="llm", component="jev-litellm", name="jev extractor",
            summary=(f"turn-enricher's Jev extraction call answered HTTP {pick['code']} at {iso(pick['t'])} "
                     f"(jev-litellm logs the response time only)"
                     + (f"; {len(cands)} candidate calls, the last was taken" if len(cands) > 1 else "")),
            phase="async_after", t0=pick["t"], t1=pick["t"], status="ok" if ok else "failed",
            reason=None if ok else f"http_{pick['code']}", sync=False, parent=parent,
            refs={"event_id": a["source_id"]},
            attrs={"provider": "jev-litellm", "endpoint": JEV_PATH, "http_status": pick["code"], "background": True,
                   "service_call": True, "purpose": "turn-enricher extractor", "match": "time-window",
                   "candidates": len(cands), "ambiguous": len(cands) > 1, "duration_unknown": True,
                   "at": iso(pick["t"])},
            evidence=[NAME]))
        frag.links.append(Link(parent, sid, "calls", "jev extractor"))
        n += 1
    return n


def build_daprd(frag: Fragment, ctx: Ctx, lines: list[tuple[float, str]], pubs: dict[str, dict]) -> int:
    hits = [(t, m.group(1), m.group(2)) for t, msg in lines for m in [_DAPR.search(msg)] if m]
    if not hits:
        return 0
    ids = sorted({h[2] for h in hits})
    try:
        from .holocene import lookup
        known = lookup(ids)
    except Exception:
        known = {}
    sid = ctx.window.session_id
    n = 0
    for t, kind, eid in hits:
        row = known.get(eid) or {}
        env = row.get("envelope") or {}
        data = env.get("data") if isinstance(env.get("data"), dict) else {}
        ours = eid in pubs or env.get("correlationid") == sid or data.get("session_id") == sid
        if not ours:
            continue
        topic = env.get("topic") or row.get("subject") or ""
        et = ("bloodbank." + topic[len("bloodbank.evt."):]) if topic.startswith("bloodbank.evt.") else (
            row.get("type") or (pubs.get(eid) or {}).get("event_type") or "unknown")
        src = env.get("source") or "unknown producer"
        if kind == "DROP":
            span = _consume(frag, "candystore-events", "candystore", eid, et, ms(env.get("time")) or t, t, "dropped",
                            "dapr_drop", f"Candystore's Dapr sidecar DROPped {hookhub.short_type(et)} from {src}",
                            "durable", "dropped", {"daprd": "DROP"})
            title = ("enricher session report dead-lettered by Candystore"
                     if is_enricher_report(src, et)
                     else f"{hookhub.short_type(et)} dead-lettered by Candystore")
            frag.findings.append(Finding(
                "broken", title,
                f"candystore-daprd logged 'DROP status returned from app' for {et} {eid} from {src} at {iso(t)}: "
                f"Candystore refused it and Dapr will not redeliver.", "candystore",
                [Ids.evt(eid), span, NAME]))
        else:
            frag.findings.append(Finding(
                "warn", f"Candystore asked Dapr to RETRY {hookhub.short_type(et)}",
                f"candystore-daprd logged RETRY for {et} {eid} at {iso(t)}.", "candystore", [Ids.evt(eid), NAME]))
        n += 1
    return n


def build_hub(frag: Fragment, ctx: Ctx, rows: list[dict], data: dict | None) -> int:
    if not rows:
        return 0
    ours = defaultdict(list)   # handler_id -> [(finish_ms, status, span id)]
    if data:
        for inv in data["invocations"]:
            for e in data["executions"].get(inv["invocation_id"], []):
                t = ms(e.get("finished_at")) or ms(e.get("started_at")) or ms(e.get("selected_at"))
                ours[e["handler_id"]].append((t, e.get("status"), Ids.handler(inv["invocation_id"], e["handler_id"])))
    groups: dict[str, dict] = {}
    foreign = 0
    for r in rows:
        evidence: list[str] = []
        attributed = False
        m = _HUB_TIMEOUT.search(r["msg"]) or _HUB_ASYNC.search(r["msg"])
        if m:
            hid = m.group(1)
            near = [s for (t, st, s) in ours.get(hid, []) if t is not None and r["t"] - 2000 <= t <= r["t"] + 3000
                    and st in ("timed_out", "failed", "selected", "started")]
            if near:
                evidence, attributed = near[:5], True
            elif _HUB_TIMEOUT.search(r["msg"]):
                try:
                    others = hookhub.executions_near(hid, r["t"] + 500, 2500)
                except Exception:
                    others = []
                if any(o.get("status") == "timed_out" and o.get("session_id") != ctx.window.session_id for o in others):
                    foreign += 1
                    continue   # the receipts show it was another session's handler
        g = groups.setdefault(r["template"], {"count": 0, "first": r["t"], "last": r["t"], "evidence": [],
                                              "attributed": 0, "example": r["msg"]})
        g["count"] += 1
        g["last"] = max(g["last"], r["t"])
        g["attributed"] += int(attributed)
        g["evidence"] += [e for e in evidence if e not in g["evidence"]]
    for tpl, g in groups.items():
        where = (f"{g['attributed']} of them line up with this turn's own handlers" if g["attributed"]
                 else "hub.log carries no session or invocation id, so they may belong to any agent")
        frag.findings.append(Finding(
            "warn", f"hook-hub logged '{tpl}' x{g['count']} during the turn",
            f"hub.log (local time, second precision) logged '{g['example']}' {g['count']} time(s) between "
            f"{iso(g['first'])} and {iso(g['last'])}; {where}. These failures never reach the receipts, so a "
            f"handler can silently not run or a reply can come back empty.",
            "hook-hub", g["evidence"][:10] + [NAME]))
    frag.facts["hub_log_foreign_timeouts"] = foreign
    return sum(g["count"] for g in groups.values())


def collect(ctx: Ctx) -> Fragment:
    started = time.monotonic()
    src = Source(id=NAME, kind="docker-logs+file",
                 locator=f"docker logs -t {NTFY} {ENRICHER} {TURN_ENRICHER} {DAPRD} {JEV}; {tilde(HUB_LOG)}")
    frag = Fragment(source=src)
    ctx.partials[NAME] = frag
    lo, hi = ctx.margin(4000.0, 2000.0)
    errors: list[str] = []
    items = 0
    modes: dict[str, str] = {}
    deadline = started + max(5.0, ctx.timeout_s * 0.85)
    try:
        pub_list = hookhub.published_events(ctx)
        pubs = _pub_index(pub_list)
        try:
            data = hookhub.load(ctx)
        except Exception:
            data = None

        # Read every container at once with a per-call budget: one slow `docker logs --tail` must not starve the
        # rest, and whatever a read did return is kept (finding 23).
        raw: dict[str, tuple[list[tuple[float, str]], str] | Exception] = {}

        def fetch(container: str) -> None:
            try:
                raw[container] = docker_lines(container, lo, hi, ctx.timeout_s, deadline)
            except Exception as exc:
                raw[container] = exc

        containers = (TURN_ENRICHER, NTFY, ENRICHER, DAPRD, JEV)
        with ThreadPoolExecutor(max_workers=len(containers)) as pool:
            list(pool.map(fetch, containers))

        def read(container: str) -> list[tuple[float, str]]:
            got = raw.get(container)
            if isinstance(got, Exception) or got is None:
                exc = got if got is not None else RuntimeError("not read")
                errors.append(f"{container}: {type(exc).__name__}: {exc}")
                return []
            lines, mode = got
            modes[container] = mode
            if mode.endswith(":partial"):
                frag.gaps.append(Gap("logs", f"{container} log read was cut short",
                                     f"docker logs {container} ran out of its time budget ({mode}); lines before the "
                                     "cut are kept, later ones may be missing", "warn"))
            return lines

        te_lines = read(TURN_ENRICHER)
        if te_lines or TURN_ENRICHER in modes:
            frag.component("turn-enricher", "turn-enricher", "service")
        n, annotated = build_turn_enricher(frag, te_lines, pubs)
        items += n

        jev_lines = parse_jev(read(JEV))
        items += build_jev(frag, jev_lines, annotated)

        ntfy_lines = parse_ntfy(read(NTFY))
        extra = [{"event_id": None, "type": "bloodbank.conversation.turn.annotated", "t_lo": a["t"] - 100.0,
                  "t_hi": a["t"] + MATCH_AFTER_MS, "t_pub": a["t"]} for a in annotated]
        frag.component("ntfy-router", "ntfy-router", "service")
        items += build_ntfy(frag, ntfy_lines, _expected(pub_list, extra))

        frag.component("enricher", "enricher", "service")
        n, fk = build_enricher(frag, ctx, read(ENRICHER), pubs)
        items += n
        if fk:
            frag.findings.append(Finding(
                "warn", "enricher could not embed some of this turn's events",
                f"{len(fk)} enricher 'DB Error' line(s): the embedding insert raced Candystore's own insert "
                f"(event_embeddings foreign key) or failed outright; event_embeddings has no timestamp to confirm a retry.",
                "enricher", fk[:10] + [NAME]))

        frag.component("candystore", "Candystore", "store")
        items += build_daprd(frag, ctx, read(DAPRD), pubs)

        frag.component("hook-hub", "hook-hub", "handler-host")
        try:
            items += build_hub(frag, ctx, read_hub_log(lo - 1000.0, hi + 1000.0), data)
        except Exception as exc:
            errors.append(f"hub.log: {type(exc).__name__}: {exc}")

        frag.facts["log_read_modes"] = modes
        if TURN_ENRICHER in modes and not te_lines:
            frag.gaps.append(Gap("turn-enricher", "no turn-enricher line for this turn's turn.completed",
                                 "the container log was read (" + modes[TURN_ENRICHER] + ") but held nothing in the "
                                 "window; turn-enricher is a core subscriber, so a turn.completed it missed leaves no trace",
                                 "info"))
        frag.gaps.append(Gap("ntfy-router", "ntfy-router lines carry the event type only",
                             "notify spans are matched to events by type and time (attrs.match = type+time, "
                             "attrs.candidates > 1 = ambiguous); the ntfy message id and HTTP status are not logged", "info"))
        src.items = items
        src.status = "ok" if items else "empty"
        if errors:
            src.error = "; ".join(errors)[:1000]
            if len(errors) >= 5:
                src.status = "error"
            frag.gaps.append(Gap("logs", "some logs could not be read", src.error, "warn"))
    except Exception as exc:  # fail soft
        src.status = "error"
        src.error = f"{type(exc).__name__}: {exc}"
        frag.gaps.append(Gap("logs", "container and hub logs could not be read", src.error, "warn"))
    src.ms = (time.monotonic() - started) * 1000.0
    return frag
