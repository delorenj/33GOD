"""Hindsight collector: recall, buffer, flush and briefing spans for one turn (source 'hindsight').

Reads, read-only:
  * session journal  ~/.agents/journal/sessions/<cli>-<sid>.jsonl   (briefing, recall, recall_skipped,
    turn_captured, turn_skipped, session_flush*, with invocation_id)
  * `hindsight audit list <bank> --action recall ...`  -> the exact query and ranked memories the prompt
    received (the audit row has no id: matched to the journal row by bank + time + query length)
  * capture buffer   ~/.local/state/33god/hook-hub/capture/<cli>-<sid>.json  (or ctx.live['capture'])
  * `hindsight operation get <bank> <operation_id>` for flush spans (GET only)

Span ids: Ids.recall / Ids.buffer / Ids.flush; the briefing uses 'memory:briefing:<invocation_id>'.
Handler parents are Ids.handler(invocation_id, 'hindsight-recall' | 'hindsight-turn' | 'hindsight-briefing' ...).
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from ..model import (
    Ctx, Fragment, Gap, Ids, Link, Source, Span, iso, ms, tilde,
)

NAME = "hindsight"
SOURCE_ID = "hindsight"

JOURNAL_DIR = Path.home() / ".agents/journal/sessions"
CAPTURE_DIR = Path.home() / ".local/state/33god/hook-hub/capture"
HINDSIGHT_BIN = "hindsight"
FLUSH_RULE = "buffered chars >= 9000, SessionEnd, or 2 h idle (sweeper)"

# hindsight-turn is the hub handler that owns the capture buffer
H_RECALL, H_TURN, H_BRIEFING, H_SESSION_END = "hindsight-recall", "hindsight-turn", "hindsight-briefing", "hindsight-session-end"


# ---------- pure helpers (unit-tested) ----------

def cut(text: Any, n: int) -> Any:
    if not isinstance(text, str) or len(text) <= n:
        return text
    return text[:n] + "…"


def read_journal(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict):
                    r["_t"] = ms(r.get("ts"))
                    rows.append(r)
    except OSError:
        pass
    return rows


def bank_status(status: str | None) -> tuple[str, str | None]:
    """per-bank journal status -> (span status, reason)."""
    s = (status or "").lower()
    if s == "ok":
        return "ok", None
    if s == "empty":
        return "ok", "no_results"
    if s == "timeout":
        return "timeout", "timeout"
    if s in ("", "unknown"):
        return "unknown", None
    return "failed", s


def pick_audit_row(items: list[dict[str, Any]], t0: float, t1: float, query_len: int | None,
                   slack_ms: float = 1200.0) -> dict[str, Any] | None:
    """The audit row that belongs to a recall that ran in [t0, t1]: started inside the span (+slack),
    preferring the row whose query length equals the journal's query_len_sent, then the closest start."""
    best: tuple[tuple[int, float], dict[str, Any]] | None = None
    for it in items:
        if it.get("action") not in (None, "recall"):
            continue
        st = ms(it.get("started_at"))
        if st is None or not (t0 - slack_ms <= st <= t1 + slack_ms):
            continue
        q = ((it.get("request") or {}).get("query")) or ""
        mismatch = 0 if (query_len is None or len(q) == query_len) else 1
        score = (mismatch, abs(st - t0))
        if best is None or score < best[0]:
            best = (score, it)
    return best[1] if best else None


def audit_artifact(row: dict[str, Any], bank: str, profile: str) -> dict[str, Any]:
    """Compact, rank-ordered view of an audit row: exactly what the prompt received."""
    req = row.get("request") or {}
    resp = row.get("response") or {}
    public = profile == "public"
    query = req.get("query")
    results = []
    for i, r in enumerate(resp.get("results") or [], 1):
        sc = r.get("scores") or {}
        results.append({
            "rank": i,
            "type": r.get("type"),
            "text": cut(r.get("text"), 120) if public else r.get("text"),
            "scores": {k: sc.get(k) for k in ("final", "reranker", "semantic", "keyword") if sc.get(k) is not None},
            "document_id": r.get("document_id"),
            "mentioned_at": r.get("mentioned_at"),
            "entities": r.get("entities") if not public else None,
            "tags": r.get("tags") or [],
        })
    art: dict[str, Any] = {
        "bank": bank,
        "audit_id": row.get("id"),
        "started_at": row.get("started_at"),
        "ended_at": row.get("ended_at"),
        "duration_ms": row.get("duration_ms"),
        "transport": row.get("transport"),
        "request": {
            "query": cut(query, 280) if public else query,
            "budget": req.get("budget"), "max_tokens": req.get("max_tokens"),
            "prefer_observations": req.get("prefer_observations"), "types": req.get("types"),
        },
        "result_count": len(results),
        "by_type": _count_types(results),
        "results": results,
    }
    if not public and resp.get("entities"):
        art["entities"] = resp.get("entities")
    return art


def _count_types(results: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in results:
        out[r.get("type") or "?"] = out.get(r.get("type") or "?", 0) + 1
    return out


def recall_spans_for_row(row: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """One (bank, per_bank dict) per bank that the recall row covers."""
    per = row.get("per_bank")
    if isinstance(per, list) and per:
        return [(str(p.get("bank")), p) for p in per if isinstance(p, dict)]
    banks = row.get("banks") or ([row.get("bank")] if row.get("bank") else [])
    return [(str(b), {"bank": b, "status": "ok" if row.get("returned_anything") else "unknown"}) for b in banks]


def flush_status(event: str, row_status: str | None = None) -> tuple[str, str | None]:
    if event == "session_flush":
        s = (row_status or "submitted").lower()
        if s == "submitted":
            return "pending", "retain_submitted"
        if s in ("retry", "unknown", "sending"):
            return "pending", f"retain_{s}"
        return "unknown", s
    return {
        "session_flush_confirmed": ("ok", "retain_confirmed"),
        "session_flush_failed": ("failed", "retain_failed"),
        "session_flush_abandoned": ("dropped", "retain_abandoned"),
        "session_flush_unverifiable": ("unknown", "retain_unverifiable"),
    }.get(event, ("unknown", event))


# ---------- runners ----------

def _run_hindsight(args: list[str], timeout: float) -> Any:
    p = subprocess.run([HINDSIGHT_BIN, *args], capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or f"rc={p.returncode}").strip()[:200])
    return json.loads(p.stdout)


def audit_list(bank: str, start_ms: float, end_ms: float, timeout: float) -> list[dict[str, Any]]:
    d = _run_hindsight(["audit", "list", bank, "--action", "recall", "--start-date", iso(start_ms) or "",
                        "--end-date", iso(end_ms) or "", "-o", "json", "-l", "20"], timeout)
    return d.get("items", []) if isinstance(d, dict) else (d or [])


def operation_get(bank: str, op_id: str, timeout: float) -> dict[str, Any]:
    return _run_hindsight(["operation", "get", bank, op_id, "-o", "json"], timeout)


# ---------- collector ----------

def collect(ctx: Ctx) -> Fragment:
    started = time.monotonic()
    w = ctx.window
    jpath = JOURNAL_DIR / f"{w.cli}-{w.session_id}.jsonl"
    src = Source(id=SOURCE_ID, kind="journal+audit+capture", locator=f"{tilde(str(jpath))} + hindsight audit list + capture buffer")
    frag = Fragment(source=src)
    frag.component("hindsight", "Hindsight", "memory")
    try:
        _collect(ctx, frag, jpath)
    except Exception as ex:  # fail soft, always
        src.status = "error"
        src.error = f"{type(ex).__name__}: {ex}"[:300]
        frag.gaps.append(Gap("hindsight", "Hindsight memory spans", f"collector error: {src.error}", "warn"))
    src.items = len(frag.spans)
    if src.status == "ok" and not frag.spans:
        src.status = "empty"
    src.ms = (time.monotonic() - started) * 1000.0
    return frag


def _load_capture(ctx: Ctx) -> tuple[dict[str, Any] | None, str]:
    live = ctx.live.get("capture") if ctx.live else None
    if isinstance(live, dict) and live:
        return live, "live"
    p = CAPTURE_DIR / f"{ctx.window.cli}-{ctx.window.session_id}.json"
    try:
        return json.loads(p.read_text()), "file"
    except (OSError, ValueError):
        return None, "absent"


def _collect(ctx: Ctx, frag: Fragment, jpath: Path) -> None:
    w = ctx.window
    lo, hi = w.t0 - 2000.0, w.t_end
    rows = read_journal(jpath)
    if not rows:
        frag.gaps.append(Gap("hindsight", "Hindsight session journal",
                             f"{tilde(str(jpath))} absent or empty", "info"))
    in_win = [r for r in rows if r["_t"] is not None and lo <= r["_t"] <= hi]
    frag.facts["memory_banks"] = sorted({b for r in in_win if r.get("event") == "recall" for b, _ in recall_spans_for_row(r)})

    prompt_inv = w.prompt_invocation_id
    for r in in_win:
        if r.get("event") in ("recall", "recall_skipped") and r.get("invocation_id"):
            prompt_inv = prompt_inv or r["invocation_id"]

    for r in in_win:
        ev = r.get("event")
        if ev == "recall":
            _recall(ctx, frag, r)
        elif ev == "recall_skipped":
            _recall_skipped(frag, r)
        elif ev == "briefing":
            _briefing(frag, r)

    _capture_spans(ctx, frag, in_win, prompt_inv)
    _flush_spans(ctx, frag, rows, in_win)


# ----- recall -----

def _recall(ctx: Ctx, frag: Fragment, r: dict[str, Any]) -> None:
    inv = r.get("invocation_id") or ""
    finished = r["_t"]
    elapsed = float(r.get("elapsed_ms") or 0.0)
    h0 = finished - elapsed
    handler = Ids.handler(inv, H_RECALL)
    banks = recall_spans_for_row(r)
    single = len(banks) == 1
    for bank, pb in banks:
        lat = pb.get("latency_ms")
        t0 = h0
        t1 = h0 + float(lat) if lat is not None else finished
        status, reason = bank_status(pb.get("status"))
        sid = Ids.recall(inv, bank)
        attrs: dict[str, Any] = {
            "bank": bank,
            "results": pb.get("results"),
            "injected_chars": r.get("total_chars") if single else None,
            "injected_chars_total": r.get("total_chars"),
            "latency_ms": lat,
            "query_chars": r.get("query_len_sent"),
            "query_chars_raw": r.get("query_len_raw"),
            "prompt_chars": r.get("prompt_len"),
            "deadline_s": r.get("deadline_s"),
            "handler_elapsed_ms": r.get("elapsed_ms"),
            "banks": r.get("banks"),
            "timing": "derived from journal ts minus handler elapsed",
        }
        n = pb.get("results")
        summary = (f"Hindsight recall from bank {bank}: {n if n is not None else '?'} memories"
                   + (f", {r.get('total_chars')} chars injected" if single and r.get("total_chars") is not None else "")
                   + (f", {lat} ms" if lat is not None else "")
                   + (f" ({reason})" if reason and status != "ok" else ""))
        span = Span(id=sid, kind="memory", component="hindsight", name="recall", summary=summary,
                    phase="prompt_submit", t0=t0, t1=t1, status=status, reason=reason, sync=True,
                    parent=handler, refs={"invocation_id": inv}, attrs={k: v for k, v in attrs.items() if v is not None},
                    evidence=[SOURCE_ID])
        frag.spans.append(span)
        frag.links.append(Link(handler, sid, "calls", "recall"))
        if status == "ok" and (n is None or n > 0):
            _attach_audit(ctx, frag, span, bank, t0, max(t1, finished), r.get("query_len_sent"))


def _attach_audit(ctx: Ctx, frag: Fragment, span: Span, bank: str, t0: float, t1: float, qlen: int | None) -> None:
    try:
        items = audit_list(bank, t0 - 1500.0, t1 + 1500.0, ctx.timeout_s)
    except Exception as ex:
        frag.gaps.append(Gap("hindsight", f"recall audit for bank {bank}",
                             f"hindsight audit list failed: {str(ex)[:160]}", "info", span.id))
        return
    row = pick_audit_row(items, t0, t1, qlen)
    if row is None:
        frag.gaps.append(Gap("hindsight", f"recall audit row for bank {bank}",
                             "no audit row matched by bank + time + query length (audit retention or clock mismatch)",
                             "info", span.id))
        return
    art = audit_artifact(row, bank, ctx.profile)
    span.payload = frag.artifact(art, note=f"Hindsight audit row {row.get('id')}: exact query and ranked memories the prompt received")
    span.attrs["audit_id"] = row.get("id")
    span.attrs["server_started_at"] = row.get("started_at")
    span.attrs["server_duration_ms"] = row.get("duration_ms")
    span.attrs["result_types"] = art["by_type"]
    span.attrs["audit_results"] = art["result_count"]
    top = [r["scores"].get("final") for r in art["results"][:1] if r.get("scores")]
    if top:
        span.attrs["top_score"] = top[0]


def _recall_skipped(frag: Fragment, r: dict[str, Any]) -> None:
    inv = r.get("invocation_id") or ""
    reason = r.get("reason")
    sid = Ids.recall(inv, "none")
    handler = Ids.handler(inv, H_RECALL)
    frag.spans.append(Span(
        id=sid, kind="memory", component="hindsight", name="recall",
        summary=f"Hindsight recall skipped: {reason} (cleaned query {r.get('query_len_clean')} chars of {r.get('query_len_raw')})",
        phase="prompt_submit", t0=r["_t"], t1=None, status="skipped", reason=reason, sync=True, parent=handler,
        refs={"invocation_id": inv},
        attrs={k: r.get(k) for k in ("query_len_raw", "query_len_clean") if r.get(k) is not None},
        evidence=[SOURCE_ID]))
    frag.links.append(Link(handler, sid, "calls", "recall skipped"))


def _briefing(frag: Fragment, r: dict[str, Any]) -> None:
    inv = r.get("invocation_id") or ""
    elapsed = float(r.get("elapsed_ms") or 0.0)
    models = r.get("models") or {}
    ok = [k for k, v in models.items() if v == "ok"]
    sid = f"memory:briefing:{inv}"
    handler = Ids.handler(inv, H_BRIEFING)
    status = "ok" if ok else "skipped"
    frag.spans.append(Span(
        id=sid, kind="memory", component="hindsight", name="briefing",
        summary=f"Hindsight briefing from bank {r.get('bank')}: {len(ok)}/{len(models)} mental models, {r.get('total_chars')} chars injected, {int(elapsed)} ms",
        phase="session_start", t0=r["_t"] - elapsed, t1=r["_t"], status=status,
        reason=None if ok else "no_briefing_models", sync=True, parent=handler, refs={"invocation_id": inv},
        attrs={"bank": r.get("bank"), "models": models, "injected_chars": r.get("total_chars"), "elapsed_ms": r.get("elapsed_ms")},
        evidence=[SOURCE_ID]))
    frag.links.append(Link(handler, sid, "calls", "briefing"))


# ----- capture buffer -----

def _capture_spans(ctx: Ctx, frag: Fragment, in_win: list[dict[str, Any]], prompt_inv: str | None) -> None:
    w = ctx.window
    cap, cap_src = _load_capture(ctx)
    public = ctx.profile == "public"
    turn_rows = [r for r in in_win if r.get("event") in ("turn_captured", "turn_skipped")]
    if cap and cap.get("repo"):
        frag.facts.setdefault("project", cap.get("repo"))
    emitted = False

    cap_turns = {t.get("n"): t for t in (cap or {}).get("turns", []) if isinstance(t, dict)}
    first_cap = next((r for r in turn_rows if r.get("event") == "turn_captured"), None)

    # the ask, buffered at prompt submit
    ask_chars = first_cap.get("ask_chars") if first_cap else None
    ask_text = None
    if first_cap and cap_turns.get(first_cap.get("turn")):
        ask_text = cap_turns[first_cap["turn"]].get("ask")
    elif cap and cap.get("pending_asks"):
        ask_text = cap["pending_asks"][-1]
        ask_chars = ask_chars if ask_chars is not None else len(ask_text)
    if prompt_inv and (ask_chars is not None or ask_text is not None):
        sid = Ids.buffer(prompt_inv)
        handler = Ids.handler(prompt_inv, H_TURN)
        art = frag.artifact({
            "document_id": (cap or {}).get("document_id") or f"session-{w.cli}-{w.session_id}",
            "bank": (cap or {}).get("bank"), "buffered": "ask",
            "ask": cut(ask_text, 280) if public else ask_text,
        }, note="cleaned ask held in the local capture buffer (max 1200 chars)") if ask_text is not None else None
        frag.spans.append(Span(
            id=sid, kind="memory", component="hindsight", name="buffer ask",
            summary=f"Hindsight buffered the ask locally ({ask_chars} chars). Retain is deferred until {FLUSH_RULE}.",
            phase="prompt_submit", t0=w.t0, t1=None, status="pending", reason="retain_deferred", sync=False,
            parent=handler, refs={"invocation_id": prompt_inv},
            attrs={"buffer_event": "ask_buffered", "ask_chars": ask_chars, "flush_rule": FLUSH_RULE,
                   "document_id": f"session-{w.cli}-{w.session_id}", "timing": "approximate: prompt submit"},
            payload=art, evidence=[SOURCE_ID]))
        frag.links.append(Link(handler, sid, "writes", "ask_buffered"))
        emitted = True

    # the turn, buffered at Stop (or skipped)
    for r in turn_rows:
        inv = r.get("invocation_id") or ""
        sid = Ids.buffer(inv)
        handler = Ids.handler(inv, H_TURN)
        if r["event"] == "turn_skipped":
            frag.spans.append(Span(
                id=sid, kind="memory", component="hindsight", name="buffer turn",
                summary=f"Hindsight did not buffer the turn: {r.get('reason')} ({r.get('outcome_chars')} chars of answer)",
                phase="turn_end", t0=r["_t"], t1=None, status="skipped", reason=r.get("reason"), sync=False,
                parent=handler, refs={"invocation_id": inv},
                attrs={k: r.get(k) for k in ("source", "outcome_chars") if r.get(k) is not None},
                evidence=[SOURCE_ID]))
            frag.links.append(Link(handler, sid, "writes", "turn_skipped"))
            continue
        t = cap_turns.get(r.get("turn"))
        art = None
        if t:
            art = frag.artifact({
                "document_id": (cap or {}).get("document_id"), "bank": (cap or {}).get("bank"),
                "turn": t.get("n"), "ts": t.get("ts"),
                "ask": cut(t.get("ask"), 280) if public else t.get("ask"),
                "outcome": cut(t.get("outcome"), 280) if public else t.get("outcome"),
                "files": t.get("files"),
                "buffered_chars": r.get("buffered_chars"),
                "batches": [{k: b.get(k) for k in ("id", "status", "attempt", "next_at", "trigger", "turns")}
                            for b in (cap or {}).get("batches", []) if isinstance(b, dict)],
            }, note="turn held in the local capture buffer until the document is flushed")
        frag.spans.append(Span(
            id=sid, kind="memory", component="hindsight", name="buffer turn",
            summary=(f"Hindsight buffered turn {r.get('turn')} locally ({r.get('buffered_chars')} chars buffered). "
                     f"Retain is deferred until {FLUSH_RULE}."),
            phase="turn_end", t0=r["_t"], t1=None, status="pending", reason="retain_deferred", sync=False,
            parent=handler, refs={"invocation_id": inv},
            attrs={"buffer_event": "turn_buffered", "turn": r.get("turn"), "ask_chars": r.get("ask_chars"),
                   "outcome_chars": r.get("outcome_chars"), "files": r.get("files"),
                   "buffered_chars": r.get("buffered_chars"), "flush_rule": FLUSH_RULE,
                   "document_id": f"session-{w.cli}-{w.session_id}", "capture_source": cap_src},
            payload=art, evidence=[SOURCE_ID]))
        frag.links.append(Link(handler, sid, "writes", "turn_buffered"))
        emitted = True

    if emitted:
        frag.gaps.append(Gap("hindsight", "Hindsight retain",
                             "Hindsight retain is deferred; this waybill ends before the document is written", "info"))
    if cap_src == "absent":
        frag.gaps.append(Gap("hindsight", "capture buffer contents",
                             "capture file absent (deleted at session end or never created): buffered text is not recoverable",
                             "info"))


# ----- flush -----

def _flush_spans(ctx: Ctx, frag: Fragment, rows: list[dict[str, Any]], in_win: list[dict[str, Any]]) -> None:
    flush_rows = [r for r in in_win if str(r.get("event", "")).startswith("session_flush") and r.get("operation_id")]
    if not flush_rows:
        return
    by_op: dict[str, list[dict[str, Any]]] = {}
    for r in flush_rows:
        by_op.setdefault(r["operation_id"], []).append(r)
    all_rows = [r for r in rows if r.get("operation_id")]
    for op, rs in by_op.items():
        rs.sort(key=lambda r: r["_t"])
        first = rs[0]
        main = next((r for r in rs if r["event"] == "session_flush"), first)
        last = rs[-1]
        status, reason = flush_status(last["event"], last.get("status"))
        bank = main.get("bank") or next((r.get("bank") for r in rs if r.get("bank")), None)
        later = [r for r in all_rows if r.get("operation_id") == op and r["_t"] > ctx.window.t_end]
        attrs: dict[str, Any] = {
            "operation_id": op, "bank": bank, "document_id": main.get("document_id"),
            "turns": main.get("turns"), "attempt": main.get("attempt"), "trigger": main.get("trigger"),
            "events": [r["event"] for r in rs],
        }
        if later:
            attrs["after_window"] = [{"event": r["event"], "at": r.get("ts")} for r in later]
        sid = Ids.flush(op)
        inv = main.get("invocation_id") or ""
        handler = Ids.handler(inv, H_TURN) if main.get("trigger") == "size" else Ids.handler(inv, H_SESSION_END)
        art = None
        if bank:
            try:
                art = frag.artifact(operation_get(bank, op, ctx.timeout_s), note="GET operation status (read-only)")
            except Exception as ex:
                attrs["operation_lookup"] = f"failed: {str(ex)[:120]}"
        frag.spans.append(Span(
            id=sid, kind="memory", component="hindsight", name="flush",
            summary=f"Hindsight flush of turns {main.get('turns')} ({main.get('trigger')}): {reason}",
            phase="turn_end" if main.get("trigger") == "size" else "session_end",
            t0=first["_t"], t1=last["_t"] if last is not first else None, status=status, reason=reason,
            sync=False, parent=handler if inv else None, refs={"invocation_id": inv} if inv else {},
            attrs={k: v for k, v in attrs.items() if v is not None}, payload=art, evidence=[SOURCE_ID]))
        if inv:
            frag.links.append(Link(handler, sid, "writes", "flush"))
