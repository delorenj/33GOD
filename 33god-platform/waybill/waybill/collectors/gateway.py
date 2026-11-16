"""AutomaticAI gateway collector (source 'gateway').

One `llm` span per `bloodbank.llm.usage.recorded` row of the session inside the turn window, read from the Candystore
Postgres `events` table through `docker exec candystore-postgres psql` in a READ ONLY transaction (the GIN index on
`data` makes `data @> {"session_id": ...}` cheap). The row's `request_id` starts with the gateway receive time
(yyyyMMddHHmmssSSS, UTC), which gives the span a millisecond start; the end is estimated from `occurred_at` (second
precision) and `latency_ms` (whole seconds).

Join hint: `attrs._match_llm = {input_tokens, output_tokens, near}` lets the assembler merge the row into the transcript
`llm:<n>` with equal tokens. Rows the transcript cannot account for are classified by `transcript_*.transcript_llm_calls`:
'subagent' (a sidechain made the call), or 'none' = a background call (ai-title and similar haiku-slot requests) and are
flagged. Those two classes get no `_match_llm` hint and sync=False.

With ctx.deep the per-request trace `/api/automaticai/traces/<rid>` is fetched (admin PAT from 1Password, held in memory
only, never logged or stored) and attached as attrs.fallback (routing steps and upstream attempts = fallback hops).
Read-only: SELECTs and HTTP GETs only.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ..model import (BusEvent, Consumer, Ctx, Finding, Fragment, Gap, Ids, Link, Source, Span, TurnWindow, iso, ms, tilde)
from .transcript_claude import GATEWAY, FULL_LIMIT, _limit, fmt_dur, fmt_tokens

SOURCE_ID = "gateway"
USAGE_TYPE = "bloodbank.llm.usage.recorded"
ALLOW_TYPE = "bloodbank.llm.allowance.observed"
STREAM = "BLOODBANK_EVENTS"
PUBLISHER = "aai-llm-observability"
TRACE_BASE = "https://api.automaticai.io/api/automaticai/traces/"
PAT_REF = "op://DeLoSecrets/l2wcxoseb33kpdsfijbpitu73u/credential"
_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:_.\-]{0,127}$")
_RID_TIME = re.compile(r"^(\d{4})(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)(\d{3})")
_PSQL = 'psql -U "$POSTGRES_USER" -d "${POSTGRES_DB:-$POSTGRES_USER}" -Atc "$0"'


# =====================================================================================================
# helpers
# =====================================================================================================

def rid_time_ms(request_id: str | None) -> float | None:
    """Gateway request ids start with the UTC receive time yyyyMMddHHmmssSSS."""
    m = _RID_TIME.match(request_id or "")
    if not m:
        return None
    y, mo, d, h, mi, s, f = m.groups()
    return ms(f"{y}-{mo}-{d}T{h}:{mi}:{s}.{f}Z")


def estimate_end(rid_ms: float | None, occurred_ms: float | None, latency_ms: float | None) -> tuple[float | None, bool]:
    """(end ms, estimated). occurred_at is the completion second (floor); latency_ms is whole seconds."""
    if occurred_ms is None:
        if rid_ms is not None and latency_ms is not None:
            return rid_ms + latency_ms, True
        return None, True
    lo, hi = occurred_ms, occurred_ms + 999.0
    if rid_ms is not None and latency_ms is not None:
        l2, h2 = rid_ms + latency_ms - 500.0, rid_ms + latency_ms + 1000.0
        a, b = max(lo, l2), min(hi, h2)
        if a <= b:
            return (a + b) / 2.0, True
    return (lo + hi) / 2.0, True


def run_psql(sql: str, timeout: float = 20.0) -> list[dict[str, Any]]:
    """Run one SELECT inside a read-only transaction; rows come back as JSON objects (row_to_json)."""
    argv = ["docker", "exec", "candystore-postgres", "sh", "-c", _PSQL, "set default_transaction_read_only=on; " + sql]
    cp = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    if cp.returncode != 0:
        raise RuntimeError(f"psql exit {cp.returncode}: {(cp.stderr or cp.stdout).strip()[:300]}")
    rows = []
    for line in cp.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            rows.append(json.loads(line))
    return rows


def _sql_str(s: str) -> str:
    return s.replace("'", "''")


def fetch_usage_rows(session_id: str, t_a: float, t_b: float, runner=run_psql) -> list[dict[str, Any]]:
    if not _SAFE.match(session_id):
        raise ValueError(f"unsafe session id {session_id!r}")
    sql = ("select row_to_json(t) from (select id, type, time, received_at, subject, correlationid, causationid, producer, data "
           "from events where data @> '" + _sql_str(json.dumps({"session_id": session_id})) + "'::jsonb "
           f"and type = '{USAGE_TYPE}' and time >= '{iso(t_a)}'::timestamptz and time <= '{iso(t_b)}'::timestamptz "
           "order by time, id) t")
    return runner(sql)


def fetch_allowance_rows(request_ids: list[str], t_a: float, t_b: float, runner=run_psql) -> list[dict[str, Any]]:
    rids = [r for r in request_ids if r and _SAFE.match(r)]
    if not rids:
        return []
    inlist = ",".join("'" + _sql_str(r) + "'" for r in rids)
    sql = ("select row_to_json(t) from (select id, type, time, received_at, subject, correlationid, causationid, producer, data "
           f"from events where type = '{ALLOW_TYPE}' and time >= '{iso(t_a)}'::timestamptz and time <= '{iso(t_b)}'::timestamptz "
           f"and data->>'request_id' in ({inlist}) order by time, id) t")
    return runner(sql)


def match_counterparts(rows: list[dict[str, Any]], calls: list[dict[str, Any]], max_skew_ms: float = 20000.0) -> None:
    """Annotate each gateway row dict with class 'main' | 'subagent' | 'none' by equal tokens and nearest time."""
    used: set[int] = set()
    for row in sorted(rows, key=lambda r: r["t1"] or 0):
        best, best_d = None, None
        for i, c in enumerate(calls):
            if i in used or c["input_tokens"] != row["input_tokens"] or c["output_tokens"] != row["output_tokens"]:
                continue
            d = abs((c["t1"] or c["t0"] or row["t1"]) - row["t1"]) if row["t1"] else 0.0
            if d > max_skew_ms:
                continue
            if best is None or d < best_d:
                best, best_d = i, d
        if best is None:
            row["class"] = "none"
            continue
        used.add(best)
        c = calls[best]
        row["class"] = c["source"]
        row["transcript_n"] = c["n"]
        row["agent_id"] = c.get("agent_id")
        row["agent_type"] = c.get("agent_type")


# =====================================================================================================
# deep mode: gateway traces
# =====================================================================================================

def read_pat() -> str | None:
    """Admin PAT from 1Password. Returned to the caller's memory only; never printed or stored."""
    try:
        cp = subprocess.run(["op", "read", PAT_REF], capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    tok = (cp.stdout or "").strip()
    return tok if cp.returncode == 0 and tok else None


def fetch_trace(rid: str, token: str, timeout: float = 8.0) -> dict[str, Any] | None:
    if not _SAFE.match(rid):
        return None
    req = urllib.request.Request(TRACE_BASE + rid, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # GET only
        doc = json.load(resp)
    return doc.get("data") if isinstance(doc, dict) else None


def summarize_trace(data: dict[str, Any]) -> dict[str, Any]:
    tr = data.get("trace") if isinstance(data.get("trace"), dict) else {}
    attempts = [a for a in tr.get("attempts") or [] if isinstance(a, dict)]
    steps = [f"{s.get('stage')}.{s.get('check')}={s.get('result')}" for s in tr.get("steps") or [] if isinstance(s, dict)]
    elapsed = [a.get("elapsed_ms") for a in attempts if isinstance(a.get("elapsed_ms"), (int, float))]
    return {
        "role": data.get("role") or tr.get("role"), "role_source": tr.get("role_source"), "client": data.get("client"),
        "slot_model": tr.get("model"), "target": data.get("target"), "account": data.get("account"),
        "outcome": data.get("outcome"), "status": data.get("status"), "attempts": data.get("attempts"),
        "hops": [{k: a.get(k) for k in ("attempt", "channel_id", "action", "reason", "source", "elapsed_ms")} for a in attempts],
        "upstream_elapsed_ms": sum(elapsed) if elapsed else None, "steps": steps[:40], "created_at": data.get("created_at"),
    }


# =====================================================================================================
# the collector
# =====================================================================================================

def _transcript_calls(window: TurnWindow) -> list[dict[str, Any]] | None:
    try:
        if window.cli == "codex":
            from .transcript_codex import codex_llm_calls
            return codex_llm_calls(window)
        from .transcript_claude import transcript_llm_calls
        return transcript_llm_calls(window)
    except Exception:  # noqa: BLE001 - classification is best effort
        return None


def build_rows(raw: list[dict[str, Any]], t_min: float) -> list[dict[str, Any]]:
    rows = []
    for r in raw:
        d = r.get("data") if isinstance(r.get("data"), dict) else {}
        rid = d.get("request_id")
        occurred = ms(d.get("occurred_at")) or ms(r.get("time"))
        lat = d.get("latency_ms")
        start = rid_time_ms(rid)
        if start is None and occurred is not None and isinstance(lat, (int, float)):
            start = occurred - lat
        if start is not None and start < t_min:
            continue                     # a request received before the prompt: another turn's straggler
        end, est = estimate_end(start, occurred, lat if isinstance(lat, (int, float)) else None)
        u = d.get("usage") if isinstance(d.get("usage"), dict) else {}
        rows.append({"raw": r, "data": d, "rid": rid, "t0": start, "t1": end, "t1_estimated": est, "occurred": occurred,
                     "input_tokens": int(u.get("input_tokens") or 0), "output_tokens": int(u.get("output_tokens") or 0),
                     "class": "unknown"})
    return rows


def collect(ctx: Ctx, runner=run_psql, trace_fetcher=None) -> Fragment:
    t_start = time.monotonic()
    w = ctx.window
    src = Source(id=SOURCE_ID, kind="postgres", locator=f"docker:candystore-postgres events type={USAGE_TYPE} session_id={w.session_id}")
    frag = Fragment(source=src)
    try:
        _collect(ctx, frag, runner, trace_fetcher)
    except Exception as e:  # noqa: BLE001 - fail soft
        src.status = "error"
        src.error = f"{type(e).__name__}: {str(e)[:300]}"
        frag.gaps.append(Gap(GATEWAY, "gateway usage rows could not be read", src.error, "warn"))
        frag.spans.clear()
        frag.events.clear()
        frag.links.clear()
    src.items = len(frag.spans)
    if src.status == "ok" and not frag.spans:
        src.status = "empty"
    src.ms = round((time.monotonic() - t_start) * 1000.0, 1)
    return frag


def _collect(ctx: Ctx, frag: Fragment, runner, trace_fetcher) -> None:
    w = ctx.window
    lim = _limit(ctx)
    t_a, t_b = ctx.margin(2000.0, 5000.0)
    raw = fetch_usage_rows(w.session_id, t_a, t_b, runner)
    rows = build_rows(raw, w.t0 - 1000.0)
    frag.component(GATEWAY, "AutomaticAI gateway", "service")
    frag.component(PUBLISHER, "AutomaticAI LLM observability", "service")
    frag.component("candystore", "Candystore", "store")
    if not rows:
        return

    allow_raw = fetch_allowance_rows([r["rid"] for r in rows], t_a, t_b + 60000.0, runner)
    allow_by_rid: dict[str, list[dict[str, Any]]] = {}
    for a in allow_raw:
        allow_by_rid.setdefault((a.get("data") or {}).get("request_id"), []).append(a)

    calls = _transcript_calls(w)
    if calls is not None:
        match_counterparts(rows, calls)
    else:
        frag.gaps.append(Gap(GATEWAY, "gateway rows could not be matched to transcript model calls",
                             "the transcript collector failed or the transcript is missing; rows are left to the assembler's token match", "info"))

    traces: dict[str, dict[str, Any]] = {}
    if ctx.deep:
        traces = _deep_traces(ctx, frag, rows, trace_fetcher)

    seen: set[tuple[str, str, str]] = set()

    def add_link(a: str, b: str, kind: str) -> None:
        if (a, b, kind) not in seen:
            seen.add((a, b, kind))
            frag.links.append(Link(from_=a, to=b, kind=kind))

    background: list[dict[str, Any]] = []
    for row in rows:
        d, r, rid = row["data"], row["raw"], row["rid"]
        u = d.get("usage") if isinstance(d.get("usage"), dict) else {}
        cls = row["class"]
        sid = f"gw:{rid}"
        status, reason = "ok", None
        if d.get("outcome") not in (None, "completed") or (d.get("status_code") not in (None, 200)):
            status, reason = "failed", f"{d.get('outcome')} {d.get('status_code')}"
        lat_s = (d.get("latency_ms") or 0) / 1000.0
        tr = traces.get(rid)
        t1 = row["t1"]
        t1_source = "occurred_at+latency"
        if tr and tr.get("upstream_elapsed_ms") and tr.get("created_at") and ms(tr["created_at"]) is not None:
            t1 = ms(tr["created_at"]) + float(tr["upstream_elapsed_ms"])
            t1_source = "trace"
        attrs: dict[str, Any] = {
            "route": d.get("route"), "requested_model": d.get("requested_model"), "native_model": d.get("native_model"),
            "served_model": d.get("returned_model") or d.get("native_model"), "effective_effort": d.get("effective_effort"),
            "requested_effort": d.get("requested_effort"), "usage": u, "tokens_in": row["input_tokens"], "tokens_out": row["output_tokens"],
            "ttft_ms": d.get("time_to_first_token_ms"), "latency_ms": d.get("latency_ms"), "outcome": d.get("outcome"),
            "status_code": d.get("status_code"), "token_name": (d.get("consumer") or {}).get("token_name"),
            "gateway_log_id": d.get("gateway_log_id"), "request_id": rid, "account_id": d.get("account_id"),
            "provider": d.get("provider"), "billing_class": d.get("billing_class"), "request_path": d.get("request_path"),
            "usage_id": d.get("usage_id"), "occurred_at": d.get("occurred_at"), "t1_estimated": True, "t1_source": t1_source,
            "counterpart": cls,
        }
        if row.get("transcript_n"):
            attrs["transcript_llm"] = row["transcript_n"]
        sync: bool | None = True
        if cls == "subagent":
            sync = False
            attrs["agent_id"] = row.get("agent_id")
            if row.get("agent_type"):
                attrs["agent_type"] = row["agent_type"]
        elif cls == "none":
            sync = False
            attrs["background"] = True
            background.append(row)
        else:
            attrs["_match_llm"] = {"input_tokens": row["input_tokens"], "output_tokens": row["output_tokens"],
                                   "near": t1 if t1 is not None else row["occurred"]}
        allow = allow_by_rid.get(rid) or []
        if allow:
            attrs["allowance"] = [{"window": (a.get("data") or {}).get("window"),
                                   "utilization_percent": (a.get("data") or {}).get("utilization_percent"),
                                   "reset_at": (a.get("data") or {}).get("reset_at")} for a in allow]
        if tr:
            attrs["fallback"] = tr
            if tr.get("role"):
                attrs["slot_role"] = tr["role"]
            if tr.get("slot_model"):
                attrs["slot_model"] = tr["slot_model"]
        label = {"subagent": " [subagent call]", "none": " [background call, no transcript counterpart]"}.get(cls, "")
        summary = (f"gateway {d.get('route') or '?'} -> {d.get('native_model') or '?'}: {fmt_tokens(row['input_tokens'])} in / "
                   f"{fmt_tokens(row['output_tokens'])} out, {lat_s:.0f} s"
                   + (f", first token {fmt_dur(d.get('time_to_first_token_ms'))}" if d.get("time_to_first_token_ms") is not None else "") + label)
        eid = r.get("id")
        refs: dict[str, Any] = {"request_id": rid}
        if eid:
            refs["event_id"] = eid
        frag.spans.append(Span(
            id=sid, kind="llm", component=GATEWAY, name=f"gateway {d.get('route') or 'request'}", summary=summary, phase="model_call",
            t0=row["t0"] if row["t0"] is not None else w.t0, t1=t1, status=status, reason=reason, sync=sync, parent=Ids.TURN,
            refs=refs, attrs={k: v for k, v in attrs.items() if v is not None}, evidence=[SOURCE_ID]))

        # --- the usage event and its publish
        if eid:
            _add_event(frag, add_link, r, sid, row, lim, kind="usage")
            for a in allow:
                _add_event(frag, add_link, a, sid, row, lim, kind="allowance")
        if tr and isinstance(tr.get("attempts"), int) and tr["attempts"] > 1:
            frag.findings.append(Finding("info", f"request {rid[-8:]} took {tr['attempts']} upstream attempts",
                                         "the gateway fell back between channels: " + " -> ".join(
                                             f"{h.get('action')}({h.get('reason') or 'ok'}, channel {h.get('channel_id')})" for h in tr.get("hops") or []),
                                         GATEWAY, [sid]))

    if background:
        frag.gaps.append(Gap(GATEWAY, f"{len(background)} gateway call(s) have no transcript counterpart",
                             "background model calls the CLI makes outside the conversation (session title, summaries; usually the "
                             "haiku/fast slot): " + ", ".join(
                                 b["rid"][-10:] + (f" (slot {traces[b['rid']]['role']})" if traces.get(b["rid"], {}).get("role") else "")
                                 for b in background[:10]), "info", f"gw:{background[0]['rid']}"))
    frag.facts["gateway_rows"] = len(rows)
    frag.facts["gateway_background"] = len(background)
    holocene_enrich(frag)


def holocene_enrich(frag: Fragment, lookup=None) -> None:
    """The llm.* events are found in Candystore by session; JetStream seq + stored time come from Holocene by id.

    Holocene's own collector cannot attribute llm.allowance.observed to a session, so the gateway collector, which
    knows the ids, asks Holocene for them (read-only lookup on the UNIQUE event_id index)."""
    ids = [e.id for e in frag.events if e.seq is None]
    if not ids:
        return
    try:
        from . import holocene
        found = (lookup or holocene.lookup)(ids)
        cname = getattr(holocene, "CONSUMER", "holocene")
    except Exception as e:  # noqa: BLE001 - fail soft
        frag.gaps.append(Gap("holocene", "JetStream sequence of the llm.* events",
                             f"Holocene lookup failed ({type(e).__name__}: {str(e)[:160]}); stored state unknown", "info"))
        return
    for ev in frag.events:
        h = found.get(ev.id)
        if not h:
            continue
        ev.seq = h.get("sequence")
        ev.stream = h.get("stream") or ev.stream
        ev.stored = ms(h.get("collected_at"))
        if not any(c.name == cname for c in ev.consumers):
            ev.consumers.append(Consumer(name=cname, component="holocene", kind="ephemeral", outcome="collected",
                                         filter="bloodbank.evt.>", t=ev.stored, evidence="observed"))


def _add_event(frag: Fragment, add_link, r: dict[str, Any], gw_span: str, row: dict[str, Any], lim: int, kind: str) -> None:
    eid = r["id"]
    t_env = ms(r.get("time")) or row["occurred"] or 0.0
    archived = ms(r.get("received_at"))
    pub = Ids.publish(eid)
    short = "llm.usage.recorded" if kind == "usage" else "llm.allowance.observed"
    frag.spans.append(Span(id=pub, kind="publish", component=PUBLISHER, name=short,
                           summary=f"{PUBLISHER} published {short} for request {row['rid'][-8:]}", phase="async_after",
                           t0=t_env, t1=None, sync=False, parent=gw_span,
                           refs={"event_id": eid, "request_id": row["rid"]}, attrs={"stream": STREAM}, evidence=[SOURCE_ID]))
    payload = frag.artifact(r.get("data") or {}, limit=lim)
    frag.events.append(BusEvent(
        id=eid, type=r.get("type") or (USAGE_TYPE if kind == "usage" else ALLOW_TYPE), t=t_env, subject=r.get("subject"),
        stream=STREAM, archived=archived, correlationid=r.get("correlationid"), causationid=r.get("causationid"),
        producer=r.get("producer"), publisher_span=pub,
        consumers=[Consumer(name="candystore-events", component="candystore", kind="durable", outcome="archived",
                            t=archived, evidence="observed")],
        payload=payload))
    if kind == "usage":
        add_link(gw_span, pub, "records")
    add_link(pub, Ids.evt(eid), "publishes")


def _deep_traces(ctx: Ctx, frag: Fragment, rows: list[dict[str, Any]], trace_fetcher) -> dict[str, dict[str, Any]]:
    fetch = trace_fetcher
    token = None
    if fetch is None:
        token = read_pat()
        if not token:
            frag.gaps.append(Gap(GATEWAY, "gateway traces were not fetched", "the admin PAT could not be read from 1Password", "info"))
            return {}
        fetch = lambda rid: fetch_trace(rid, token)  # noqa: E731
    rids = [r["rid"] for r in rows if r.get("rid")][:150]
    out: dict[str, dict[str, Any]] = {}
    errors = 0
    deadline = time.monotonic() + max(ctx.timeout_s, 10.0) * 2

    def one(rid: str) -> tuple[str, dict[str, Any] | None]:
        if time.monotonic() > deadline:
            return rid, None
        try:
            data = fetch(rid)
            return rid, summarize_trace(data) if isinstance(data, dict) else None
        except (urllib.error.URLError, OSError, ValueError):
            return rid, None

    with ThreadPoolExecutor(max_workers=6) as pool:
        for rid, summ in pool.map(one, rids):
            if summ:
                out[rid] = summ
            else:
                errors += 1
    token = None  # drop the reference; it was never logged or written
    if errors:
        frag.gaps.append(Gap(GATEWAY, f"{errors} of {len(rids)} gateway trace(s) could not be fetched",
                             "HTTP error, timeout or empty trace (traces age out of the gateway)", "info"))
    return out
