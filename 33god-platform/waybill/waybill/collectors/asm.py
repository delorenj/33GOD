"""ASM collector: agent state machine transitions for one session (source 'asm').

Reads, read-only:
  * Redis (localhost:6379) via redis-cli:  asm:t:<cli>:s:<sid> (stream), asm:a:<cli>:s:<sid> (hash),
    asm:idx:pane:<zellij session>:<pane> (string), nlp:pane:<zellij session>:<pane> (hash, nanoleaf).
    Stream and hash expire 900 s after the last edge, so on a past turn they are usually gone.
  * ~/.local/state/33god/asm/transitions.log (+ .1): the durable record. One line per edge, LOCAL-time
    ISO timestamp with 1 s resolution (the time asm-log ran, so it lags the edge by up to ~1 s), no reason.
  * ctx.live['asm']: pre-captured data from `waybill record` (preferred over Redis when present).

One 'state' span per transition. The assembler links evt -> state through attrs._join.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from ..model import (
    Ctx, Fragment, Gap, Finding, Ids, Link, Source, Span, iso, ms, tilde,
)
from . import hookhub

NAME = "asm"
SOURCE_ID = "asm"

LOG_DIR = Path.home() / ".local/state/33god/asm"
TRANSITIONS_LOG = LOG_DIR / "transitions.log"
DECKARD_UNIT = "deckard"
# an ASM edge and the hub's transition re-entry invocation it causes land within this of each other
STREAM_INV_TOL_MS = 1500.0
LOG_INV_BEFORE_MS = 1000.0          # the log timestamp is truncated to the second: the edge is in [ts, ts + 1 s)
LOG_INV_AFTER_MS = 2500.0
DECKARD_AFTER_MS = 1500.0           # asm-tabpaint renames the tab right after an edge; deckard sees it within this
REDIS_HOST = "127.0.0.1"
REDIS_PORT = "6379"

# redis-cli verbs this module may send. Everything here is a read.
_REDIS_READ_ONLY = {"XRANGE", "HGETALL", "GET", "TTL", "TYPE", "SCAN", "EXISTS", "XLEN"}

# the lifecycle event that drives each ASM edge (SPEC 3a join hint)
REASON_EVENT = {
    "prompt": "bloodbank.conversation.turn.started",
    "tool_req": "bloodbank.agent.tool.requested",
    "tool_done": "bloodbank.agent.tool.completed",
    "quiesce": "bloodbank.conversation.turn.completed",
    "start": "bloodbank.agent.session.started",
}
REASON_PHASE = {
    "start": "session_start",
    "prompt": "prompt_submit",
    "tool_req": "pre_tool",
    "tool_done": "post_tool",
    "fail": "post_tool",
    "quiesce": "turn_end",
}
REASON_WORDS = {
    "start": "on session start",
    "prompt": "on prompt",
    "tool_req": "on tool request",
    "tool_done": "on tool completion",
    "fail": "on tool failure",
    "quiesce": "on quiesce",
    "attention": "on attention",
    "stale": "gone silent (stale)",
    "gone": "process gone",
    "discover": "discovered by sweeper",
}

_LOG_RE = re.compile(
    r"^(?P<ts>\S+)\s+(?P<from>\S+)\s+->\s+(?P<to>\S+)\s+(?P<scope>\S+)\s+held=(?P<held>\S+?)ms\s+pid=(?P<pid>\d+)\s*$"
)


# ---------- pure helpers (unit-tested) ----------

def scope_for(cli: str, sid: str) -> str:
    return f"{cli}:s:{sid}"


def infer_reason(frm: str, to: str) -> str | None:
    """transitions.log carries from/to but not the reason. Infer it from the edge (best effort)."""
    if frm == "none" and to == "starting":
        return "start"
    if frm == "none":
        return "discover"
    if to == "working" and frm in ("starting", "idle", "failed", "stale", "awaiting_human", "blocked"):
        return "prompt"
    if to == "tool_running":
        return "tool_req"
    if frm == "tool_running" and to == "working":
        return "tool_done"
    if to == "idle":
        return "quiesce"
    if to == "failed":
        return "fail"
    if to == "stale":
        return "stale"
    if to == "gone":
        return "gone"
    return None


def fmt_held(held_ms: float | int | None) -> str:
    if held_ms is None:
        return "n/a"
    h = float(held_ms)
    if h < 1000:
        return f"{int(h)} ms"
    if h < 120_000:
        return f"{h / 1000:.1f} s"
    return f"{h / 60000:.1f} min"


def summarize(frm: str, to: str, reason: str | None, held_ms: float | None) -> str:
    why = REASON_WORDS.get(reason or "", f"({reason})" if reason else "")
    held = f" (held {frm} {fmt_held(held_ms)})" if held_ms is not None and frm != "none" else ""
    return f"ASM: {frm} -> {to} {why}{held}".replace("  ", " ").strip()


def parse_log_line(line: str) -> dict[str, Any] | None:
    m = _LOG_RE.match(line.strip())
    if not m:
        return None
    t = ms(m.group("ts"))
    if t is None:
        return None
    held = m.group("held")
    return {
        "scope": m.group("scope"),
        "from": m.group("from"),
        "to": m.group("to"),
        "held_ms": float(held) if re.fullmatch(r"\d+(\.\d+)?", held) else None,
        "at_ms": t + 500.0,          # the log truncates to the second: centre the estimate
        "log_ts_ms": t,
        "log_pid": int(m.group("pid")),   # pid of the asm-log script, NOT the agent
        "src": "log",
    }


def read_log_entries(scope: str, paths: list[Path], lo: float, hi: float) -> list[dict[str, Any]]:
    """Entries for `scope` whose (1 s resolution) timestamp falls in [lo, hi]. Oldest generation first."""
    out: list[dict[str, Any]] = []
    for p in paths:
        try:
            with p.open("r", errors="replace") as fh:
                for line in fh:
                    if scope not in line:
                        continue
                    e = parse_log_line(line)
                    if e and e["scope"] == scope and lo <= e["log_ts_ms"] <= hi:
                        out.append(e)
        except OSError:
            continue
    out.sort(key=lambda e: e["at_ms"])
    return out


def normalize_stream_entry(raw: Any) -> dict[str, Any] | None:
    """Accept [id, ['j', '<json>']] (redis-cli --json), {'id':..,'j':..}, or an already decoded dict."""
    try:
        eid = None
        body: Any = None
        if isinstance(raw, (list, tuple)) and len(raw) == 2:
            eid, fields = raw
            if isinstance(fields, (list, tuple)):
                d = dict(zip(fields[0::2], fields[1::2]))
                body = d.get("j")
            elif isinstance(fields, dict):
                body = fields.get("j")
        elif isinstance(raw, dict):
            eid = raw.get("id") or raw.get("entry_id")
            body = raw.get("j") if "j" in raw else (raw.get("entry") or raw)
        if isinstance(body, str):
            body = json.loads(body)
        if not isinstance(body, dict):
            return None
        at = body.get("at_ms")
        if at is None and isinstance(eid, str) and "-" in eid:
            at = int(eid.split("-")[0])
        if at is None:
            return None
        e = dict(body)
        e["at_ms"] = float(at)
        e["entry_id"] = eid or f"{int(float(at))}-0"
        e["held_ms"] = body.get("held_ms")
        e["src"] = "stream"
        return e
    except (ValueError, TypeError):
        return None


def merge_entries(stream: list[dict[str, Any]], log: list[dict[str, Any]], tol_ms: float = 1500.0) -> list[dict[str, Any]]:
    """Stream entries win. A log line is added only when no unmatched stream entry has the same from/to within tol."""
    used: set[int] = set()
    extra: list[dict[str, Any]] = []
    for le in log:
        hit = None
        for i, se in enumerate(stream):
            if i in used:
                continue
            if se.get("from") == le["from"] and se.get("to") == le["to"] and abs(se["at_ms"] - le["at_ms"]) <= tol_ms:
                hit = i
                break
        if hit is None:
            extra.append(le)
        else:
            used.add(hit)
    out = stream + extra
    out.sort(key=lambda e: e["at_ms"])
    return out


def entry_key(e: dict[str, Any], seen: dict[str, int]) -> str:
    if e.get("src") == "stream":
        return str(e["entry_id"])
    base = f"log-{int(e['log_ts_ms'])}"
    n = seen.get(base, 0)
    seen[base] = n + 1
    return base if n == 0 else f"{base}.{n}"


def build_span(e: dict[str, Any], key: str, profile: str) -> Span:
    frm, to = str(e.get("from") or "?"), str(e.get("to") or "?")
    reason = e.get("reason")
    inferred = False
    if not reason:
        reason = infer_reason(frm, to)
        inferred = reason is not None
    held = e.get("held_ms")
    held_f = float(held) if isinstance(held, (int, float)) or (isinstance(held, str) and held.replace(".", "", 1).isdigit()) else None
    at = e["at_ms"]
    attrs: dict[str, Any] = {
        "from": frm, "to": to, "held_ms": held_f,
        "at": iso(at), "source": e.get("src"),
    }
    for k in ("tools", "subs", "seq", "turn", "basis", "scope"):
        if e.get(k) is not None:
            attrs[k] = e[k]
    if e.get("invocation_id"):
        attrs["invocation_id"] = e["invocation_id"]
    if e.get("zellij_pane") not in (None, ""):
        attrs["pane"] = f"{e.get('zellij_session') or '?'}:{e['zellij_pane']}"
    if e.get("cwd"):
        attrs["cwd"] = tilde(e["cwd"]) if profile == "public" else e["cwd"]
    if inferred:
        attrs["reason_inferred"] = True
    if e.get("src") == "log":
        attrs["at_precision_ms"] = 1000 if e.get("time_precision") != "invocation" else 1
        attrs["log_pid"] = e.get("log_pid")
        attrs["time_precision"] = e.get("time_precision") or "1s"
        if e.get("at_est_ms") is not None:
            attrs["log_estimate_at"] = iso(e["at_est_ms"])
    elif e.get("pid") not in (None, "", "0", 0):
        attrs["pid"] = e["pid"]
    ev = REASON_EVENT.get(reason or "")
    if ev:
        attrs["_join"] = {
            "event_type": ev, "near": at,
            "window_ms": 3000 if e.get("src") == "log" else 2000,
            "link": "triggers",
        }
    refs: dict[str, Any] = {}
    if e.get("seq") is not None:
        refs["seq"] = e["seq"]
    return Span(
        id=Ids.asm(key), kind="state", component="asm", name=f"{frm} -> {to}",
        summary=summarize(frm, to, reason, held_f),
        phase=REASON_PHASE.get(reason or "", "async_after"),
        t0=at, t1=None, status="ok", reason=reason, sync=False, refs=refs, attrs=attrs,
        evidence=[SOURCE_ID],
    )



# ---------- hub transition invocations (SPEC: every edge has an invocation, every invocation an edge) ----------

def snap_to_invocations(entries: list[dict[str, Any]], invs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pair ASM edges with the hub's transition re-entry invocations (native='transition', same cli).

    Stream edges carry exact times, so they only gain `invocation_id`. A transitions.log edge has 1 s resolution
    (centred at +500 ms), so it is SNAPPED to the matching invocation's received_at: the log line can never sort
    before the invocation it caused. A log edge with no invocation keeps its estimate and says so
    (time_precision='1s'). Returns the invocations nothing claimed."""
    free = sorted([i for i in invs if i.get("received_ms") is not None], key=lambda i: i["received_ms"])
    claimed: set[str] = set()

    def take(pred) -> dict[str, Any] | None:
        for i in free:
            if i["invocation_id"] not in claimed and pred(i["received_ms"]):
                claimed.add(i["invocation_id"])
                return i
        return None

    for e in sorted([x for x in entries if x.get("src") == "stream"], key=lambda x: x["at_ms"]):
        best = None
        for i in free:
            if i["invocation_id"] in claimed:
                continue
            d = i["received_ms"] - e["at_ms"]
            if -50.0 <= d <= STREAM_INV_TOL_MS and (best is None or d < best[0]):
                best = (d, i)
        if best is not None:
            claimed.add(best[1]["invocation_id"])
            e["invocation_id"] = best[1]["invocation_id"]
            e["time_precision"] = "ms"
    for e in sorted([x for x in entries if x.get("src") == "log"], key=lambda x: x["log_ts_ms"]):
        lo, hi = e["log_ts_ms"] - LOG_INV_BEFORE_MS, e["log_ts_ms"] + LOG_INV_AFTER_MS
        i = take(lambda r: lo <= r <= hi)
        if i is not None:
            e["at_est_ms"] = e["at_ms"]
            e["at_ms"] = i["received_ms"]
            e["invocation_id"] = i["invocation_id"]
            e["time_precision"] = "invocation"
        else:
            e["time_precision"] = "1s"
    entries.sort(key=lambda x: x["at_ms"])
    return [i for i in free if i["invocation_id"] not in claimed]


# ---------- deckard journal ----------

_DECKARD = re.compile(r"^(?P<ts>\S+)\s+\S+\s+deckard\[\d+\]:\s+(?:\[[\d.]+s\]\s+)?(?P<msg>.*)$")
_TAB_META = re.compile(r'tab metadata changed.*?(?:focus\s+"(?P<focus>[^"]*)")?\s*$')


def parse_deckard_lines(text: str, lo: float, hi: float) -> list[dict[str, Any]]:
    """`journalctl -u deckard -o short-iso-precise` -> [{t, msg, focus}] for 'tab metadata changed' lines."""
    out = []
    for raw in (text or "").splitlines():
        m = _DECKARD.match(raw)
        if not m or "tab metadata changed" not in m.group("msg"):
            continue
        t = ms(m.group("ts"))
        if t is None or not (lo <= t <= hi):
            continue
        f = _TAB_META.search(m.group("msg"))
        out.append({"t": t, "msg": m.group("msg").strip()[:200], "focus": (f.group("focus") if f else None)})
    return out


def deckard_lines(lo: float, hi: float, timeout: float = 8.0) -> list[dict[str, Any]]:
    """Read-only `journalctl --user -u deckard` for the window (raises on failure)."""
    p = subprocess.run(
        ["journalctl", "--user", "-u", DECKARD_UNIT, "--since", f"@{lo / 1000.0:.3f}", "--until", f"@{hi / 1000.0:.3f}",
         "-o", "short-iso-precise", "--no-pager", "-q"],
        capture_output=True, text=True, errors="replace", timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or f"rc={p.returncode}").strip()[:200])
    return parse_deckard_lines(p.stdout, lo, hi)


def deckard_spans(frag: Fragment, lines: list[dict[str, Any]], edges: list[Span]) -> int:
    """Instant, observed spans for deckard's 'tab metadata changed' lines that follow one of this turn's ASM edges
    (the tab painter renames the tab on every edge). Lines with no edge in reach belong to some other pane."""
    n = 0
    used: set[str] = set()
    for ln in sorted(lines, key=lambda x: x["t"]):
        cands = [e for e in edges if -50.0 <= ln["t"] - e.t0 <= DECKARD_AFTER_MS]
        if not cands:
            continue
        edge = max(cands, key=lambda e: e.t0)          # the nearest preceding edge
        sid = Ids.notify("deckard", str(int(ln["t"])))
        if sid in used:
            continue
        used.add(sid)
        frag.component("deckard", "deckard", "service")
        frag.spans.append(Span(
            id=sid, kind="notify", component="deckard", name="tab metadata changed",
            summary=f"deckard saw the zellij tab change {int(round(ln['t'] - edge.t0))} ms after ASM {edge.name}"
                    + (f" (focus {ln['focus']!r})" if ln.get("focus") else ""),
            phase="async_after", t0=ln["t"], t1=ln["t"], status="ok", sync=False,
            attrs={"journal": ln["msg"], "focus": ln.get("focus"), "at": iso(ln["t"]), "after_edge": edge.id},
            evidence=[SOURCE_ID]))
        frag.links.append(Link(edge.id, sid, "triggers", "tab repaint"))
        n += 1
    return n


# ---------- redis (read only) ----------

class RedisError(RuntimeError):
    pass


def _redis(*args: str, timeout: float = 5.0) -> Any:
    verb = args[0].upper() if args else ""
    if verb not in _REDIS_READ_ONLY:
        raise RedisError(f"refusing non-read redis verb {verb!r}")
    try:
        p = subprocess.run(
            ["redis-cli", "-h", REDIS_HOST, "-p", REDIS_PORT, "--json", *args],
            capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as ex:
        raise RedisError(f"redis-cli: {ex}") from ex
    out = (p.stdout or "").strip()
    if p.returncode != 0 or (out.startswith("Error") or out.startswith("Could not connect")):
        raise RedisError((out or p.stderr or f"rc={p.returncode}").strip()[:200])
    if not out:
        return None
    try:
        return json.loads(out)
    except ValueError as ex:
        raise RedisError(f"unparsable redis-cli output: {out[:120]}") from ex


def _hash_to_dict(v: Any) -> dict[str, Any]:
    if isinstance(v, dict):
        return v
    if isinstance(v, list):
        return dict(zip(v[0::2], v[1::2]))
    return {}


def _live_asm(ctx: Ctx) -> dict[str, Any] | None:
    live = ctx.live.get("asm") if ctx.live else None
    if not live:
        return None
    if isinstance(live, list):
        return {"stream": live}
    if isinstance(live, dict):
        return live
    return None


# ---------- collector ----------

def collect(ctx: Ctx) -> Fragment:
    started = time.monotonic()
    w = ctx.window
    scope = scope_for(w.cli, w.session_id)
    stream_key = f"asm:t:{scope}"
    hash_key = f"asm:a:{scope}"
    src = Source(id=SOURCE_ID, kind="redis+log", locator=f"redis://localhost:6379/{stream_key} + ~/.local/state/33god/asm/transitions.log")
    frag = Fragment(source=src)
    frag.component("asm", "ASM (agent state machine)", "store")
    try:
        _collect(ctx, frag, scope, stream_key, hash_key)
    except Exception as ex:  # fail soft, always
        src.status = "error"
        src.error = f"{type(ex).__name__}: {ex}"[:300]
        frag.gaps.append(Gap("asm", "ASM transitions", f"collector error: {src.error}", "warn"))
    src.items = len(frag.spans)
    if src.status == "ok" and not frag.spans:
        src.status = "empty"
    src.ms = (time.monotonic() - started) * 1000.0
    return frag


def _collect(ctx: Ctx, frag: Fragment, scope: str, stream_key: str, hash_key: str) -> None:
    w = ctx.window
    lo, hi = w.t0 - 2000.0, w.t_end
    # the SessionStart pre-roll (a headless CLI starts its session seconds before the prompt) opens the none->starting
    # edge before w.t0 - 2 s: reach back to the earliest hub invocation of the turn
    earliest = hookhub.earliest_ms(ctx)
    if earliest is not None:
        lo = min(lo, earliest - 1000.0)
    invs = hookhub.transition_invocations(ctx)
    src = frag.source
    notes: list[str] = []

    live = _live_asm(ctx)
    stream: list[dict[str, Any]] = []
    hash_: dict[str, Any] = {}
    pane_idx: str | None = None
    nlp: dict[str, Any] | None = None
    redis_ok = False

    if live is not None:
        for raw in live.get("stream", []) or []:
            e = normalize_stream_entry(raw)
            if e and (e.get("scope") in (None, scope)):
                stream.append(e)
        hash_ = _hash_to_dict(live.get("hash"))
        pane_idx = live.get("pane_idx")
        nlp = live.get("nlp") if isinstance(live.get("nlp"), dict) else None
        notes.append("live capture")
    else:
        try:
            raw = _redis("XRANGE", stream_key, str(int(lo)), str(int(hi)))
            redis_ok = True
            for r in raw or []:
                e = normalize_stream_entry(r)
                if e:
                    stream.append(e)
            hash_ = _hash_to_dict(_redis("HGETALL", hash_key))
        except RedisError as ex:
            notes.append(f"redis unavailable: {ex}")
            frag.gaps.append(Gap("asm", "ASM Redis stream", f"redis-cli failed: {ex}", "info"))
        if redis_ok and not stream:
            notes.append("redis stream expired (900 s TTL after the last edge)")
    stream = [e for e in stream if lo <= e["at_ms"] <= hi]

    log = read_log_entries(scope, [Path(str(TRANSITIONS_LOG) + ".1"), TRANSITIONS_LOG], lo, hi)
    entries = merge_entries(stream, log)
    if log and not stream:
        notes.append("transitions.log only (1 s resolution, reasons inferred)")
        frag.gaps.append(Gap(
            "asm", "exact ASM edge times and reasons",
            "Redis stream expired; transitions.log has 1 s resolution, no reason, and no tool/sub counters", "info"))
    elif log and stream and len(entries) > len(stream):
        notes.append(f"{len(entries) - len(stream)} edges only in transitions.log")

    unclaimed = snap_to_invocations(entries, invs)
    seen: dict[str, int] = {}
    edge_spans: list[Span] = []
    for e in entries:
        sp = build_span(e, entry_key(e, seen), ctx.profile)
        edge_spans.append(sp)
        frag.spans.append(sp)
        if e.get("invocation_id"):
            frag.links.append(Link(sp.id, Ids.hook(e["invocation_id"]), "triggers", "ASM re-entry"))
    _invocation_findings(frag, edge_spans, unclaimed, invs)
    try:
        dl = deckard_lines(min(lo, w.t0) - 500.0, hi + 2000.0)
        n_deckard = deckard_spans(frag, dl, edge_spans)
    except Exception as ex:
        dl, n_deckard = [], 0
        frag.gaps.append(Gap("deckard", "deckard tab-change journal not read", f"journalctl failed: {ex}"[:200], "info"))

    if not entries:
        frag.gaps.append(Gap(
            "asm", f"ASM transitions for {scope}",
            "no edge in the window: Redis stream expired and transitions.log has no matching line", "warn"))

    _scope_findings(frag, scope, entries, hash_)
    _pane_and_painters(ctx, frag, scope, entries, hash_, pane_idx, nlp, live is not None)

    if not n_deckard:
        frag.gaps.append(Gap(
            "ext:zellij", "tab painter result (glyph on the zellij tab)",
            "asm-tabpaint keeps no history and deckard's journal showed no 'tab metadata changed' line after an edge; "
            "only the ASM edge (the painter's input) is recorded", "info"))
    if notes:
        src.error = None
        frag.facts["asm_notes"] = notes


def _invocation_findings(frag: Fragment, edges: list[Span], unclaimed: list[dict[str, Any]],
                         invs: list[dict[str, Any]]) -> None:
    """Every transition invocation should have an edge. (An edge with no invocation is normal for a sweeper edge and
    is only counted.)"""
    if unclaimed:
        frag.findings.append(Finding(
            "warn", f"{len(unclaimed)} hook-hub transition invocation(s) have no ASM edge",
            "native='transition' re-entries were attributed to this turn's publishers, but no Redis stream entry or "
            "transitions.log line matches them in time: " + ", ".join(i["invocation_id"][:8] for i in unclaimed[:6])
            + ". The edge may have aged out of Redis (900 s) before the log line was written.", "asm",
            [Ids.hook(i["invocation_id"]) for i in unclaimed[:5]]))
    frag.facts["asm_invocations"] = {"transitions": len(invs), "edges": len(edges),
                                      "edges_with_invocation": sum(1 for e in edges if e.attrs.get("invocation_id")),
                                      "invocations_without_edge": len(unclaimed)}


def _scope_findings(frag: Fragment, scope: str, entries: list[dict[str, Any]], hash_: dict[str, Any]) -> None:
    if not entries:
        return
    ids = [s.id for s in frag.spans][:3]
    frag.findings.append(Finding(
        "info",
        "ASM never reaches 'gone' for session-keyed scopes",
        f"{scope} is keyed by the native session id (pid recorded as 0). SessionEnd/Stop only quiesce it; the sweeper "
        "cannot prove a sid scope gone, so it just expires 900 s after the last edge.",
        "asm", ids))
    if hash_ and hash_.get("scope") and not hash_.get("session_id") and not hash_.get("correlationid"):
        frag.findings.append(Finding(
            "info", "ASM hash carries no session_id / correlationid",
            f"HGETALL asm:a:{scope} has empty session_id and correlationid; only the scope embeds the session id.",
            "asm", ids))


def _pane_and_painters(ctx: Ctx, frag: Fragment, scope: str, entries: list[dict[str, Any]],
                       hash_: dict[str, Any], pane_idx: str | None, nlp: dict[str, Any] | None, live: bool) -> None:
    w = ctx.window
    zs = pane = None
    for e in reversed(entries):
        if e.get("zellij_pane") not in (None, ""):
            zs, pane = e.get("zellij_session"), str(e["zellij_pane"])
            break
    if not pane and hash_.get("zellij_pane"):
        zs, pane = hash_.get("zellij_session"), str(hash_["zellij_pane"])
    if not (zs and pane):
        frag.gaps.append(Gap(
            "ext:nanoleaf", "nanoleaf pane colour",
            "pane unknown (transitions.log has no pane); nlp:pane:* keeps only the latest value per pane", "info"))
        return
    key = f"{zs}:{pane}"
    if not live:
        try:
            pane_idx = _redis("GET", f"asm:idx:pane:{key}")
            nlp = _hash_to_dict(_redis("HGETALL", f"nlp:pane:{key}")) or None
        except RedisError as ex:
            frag.gaps.append(Gap("ext:nanoleaf", "nanoleaf pane colour", f"redis-cli failed: {ex}", "info"))
            return
    if isinstance(pane_idx, str) and pane_idx and pane_idx != scope:
        frag.gaps.append(Gap(
            "asm", "pane-based attribution",
            f"asm:idx:pane:{key} points at {pane_idx}, not {scope}: a nested or headless run inherits the parent's pane", "info"))
    if not nlp or not nlp.get("ts"):
        frag.gaps.append(Gap("ext:nanoleaf", "nanoleaf pane colour",
                             f"nlp:pane:{key} absent or expired (6 h TTL, latest value only)", "info"))
        return
    ts_ms = ms(float(nlp["ts"]))
    if ts_ms is not None and (w.t0 - 1000.0) <= ts_ms <= w.t_end:
        frag.component("ext:nanoleaf", "Nanoleaf", "device")
        frag.spans.append(Span(
            id=Ids.notify("nanoleaf", str(int(ts_ms))), kind="notify", component="ext:nanoleaf",
            name=f"pane -> {nlp.get('state')}",
            summary=f"Nanoleaf: pane {key} painted '{nlp.get('state')}' (latest value only)",
            phase="async_after", t0=ts_ms, status="ok", sync=False,
            attrs={"pane": key, "state": nlp.get("state"), "at": iso(ts_ms), "latest_only": True},
            evidence=[SOURCE_ID]))
    else:
        frag.gaps.append(Gap(
            "ext:nanoleaf", "nanoleaf pane colour for this turn",
            f"nlp:pane:{key} was last written at {iso(ts_ms)} (state '{nlp.get('state')}'), outside the window; "
            "only the latest value is kept", "info"))
