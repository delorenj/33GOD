"""Candystore archive collector (SPEC section 1 rows 7, 8, 11 and 12).

HTTP (127.0.0.1:8683) gives the session's envelopes; Postgres (read-only, through `docker exec
candystore-postgres psql` with the container's own env) gives what the API hides: received_at (the
archived-at time), the hook.updated mirrors keyed by invocation id, service-produced events caused by the
turn's events (turn-enricher's turn.annotated), and dead-lettered rows that mention the session.
llm.* events are skipped: the gateway collector owns them.
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
import uuid
from typing import Any

from ..model import (BusEvent, Consumer, Ctx, Finding, Fragment, Gap, Ids, Link, Source, Span, iso, ms, tilde)
from . import hookhub

NAME = "candystore"
BASE_URL = os.environ.get("WAYBILL_CANDYSTORE_URL", "http://127.0.0.1:8683")
PG_CONTAINER = os.environ.get("WAYBILL_CANDYSTORE_PG", "candystore-postgres")
CONSUMER = "candystore-events"
HOOK_UPDATED = "bloodbank.agent.hook.updated"
PUBLIC_CLIP = 280
FULL_CLIP = 8192
# producers whose causationid is the publisher's linear per-session chain, not true causation
AGENT_PRODUCERS = frozenset({"claude-code", "codex-cli", "codex", "claude", "hermes", "opencode", "hook-hub"})

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_SAFE_SID = re.compile(r"^[A-Za-z0-9._:\-]{1,200}$")

PSQL_ARGV = ["docker", "exec", "-i", PG_CONTAINER, "sh", "-c",
             'psql -X -q -A -t -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "${POSTGRES_DB:-$POSTGRES_USER}" -f -']


# ---------- pure helpers (shared shape with holocene.py) ----------

def is_uuid(v: Any) -> bool:
    return isinstance(v, str) and bool(_UUID.match(v))


def correlation_id(cli: str | None, session_id: str) -> str:
    """agent-hooks clients/base.py get_correlation_id: the session UUID, else uuid5(URL, 'bloodbank:<cli>:<sid>')."""
    try:
        return str(uuid.UUID(session_id))
    except (ValueError, AttributeError, TypeError):
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"bloodbank:{cli}:{session_id}"))


def normalize_type(env: dict) -> tuple[str, str | None]:
    """(type, subject) of an envelope. Dapr-wrapped events (type com.dapr.event.sent) take their type from topic."""
    et = env.get("type") or "unknown"
    subject = env.get("subject")
    topic = env.get("topic")
    if et == "com.dapr.event.sent" and isinstance(topic, str) and topic.startswith("bloodbank.evt."):
        return "bloodbank." + topic[len("bloodbank.evt."):], topic
    if not subject and et.startswith("bloodbank."):
        subject = "bloodbank.evt." + et[len("bloodbank."):]
    return et, subject or topic


def short_type(et: str | None) -> str:
    return hookhub.short_type(et)


def phase_for_type(et: str | None) -> str:
    et = et or ""
    if et.endswith("session.started"):
        return "session_start"
    if et.endswith("turn.started"):
        return "prompt_submit"
    if et.endswith("tool.requested"):
        return "pre_tool"
    if et.endswith("tool.completed"):
        return "post_tool"
    if et.endswith(("turn.completed", "turn.annotated")):
        return "turn_end"
    if et.endswith("session.ended"):
        return "session_end"
    if et.endswith(("invocation.started", "invocation.completed", "invocation.failed")):
        return "tool"
    return "async_after"


def clip_strings(obj: Any, limit: int, home_to_tilde: bool = False) -> tuple[Any, int]:
    """Copy obj with every string longer than limit cut (marked with an ellipsis). Returns (copy, n_clipped)."""
    n = 0

    def walk(o: Any) -> Any:
        nonlocal n
        if isinstance(o, str):
            s = tilde(o) if home_to_tilde else o
            if len(s) > limit:
                n += 1
                return s[:limit] + "…"
            return s
        if isinstance(o, list):
            return [walk(x) for x in o]
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items()}
        return o

    return walk(obj), n


def sort_keys(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: sort_keys(obj[k]) for k in sorted(obj)}
    if isinstance(obj, list):
        return [sort_keys(x) for x in obj]
    return obj


def shape_envelope(env: dict, profile: str) -> tuple[dict, int]:
    """Envelope ready for an artifact: canonical key order, data strings clipped (280 public / 8 KiB full),
    and under 'public' home paths become '~' and environment values are dropped."""
    public = profile == "public"
    out = dict(env)
    n = 0
    if "data" in out:
        data = out["data"]
        if public and isinstance(data, dict):
            data = {k: ("«dropped»" if k.lower() in ("env", "environment") else v) for k, v in data.items()}
        out["data"], n = clip_strings(data, PUBLIC_CLIP if public else FULL_CLIP, public)
    if public:
        out = {k: (clip_strings(v, 4096, True)[0] if k != "data" else v) for k, v in out.items()}
    return sort_keys(out), n


def envelope_artifact(frag: Fragment, env: dict, profile: str, note: str | None = None) -> str:
    shaped, n = shape_envelope(env, profile)
    extra = f"{n} long data field(s) clipped" if n else None
    note = "; ".join(x for x in (note, extra) if x) or None
    return frag.artifact(shaped, mime="application/json", note=note)


def in_window(t: float | None, lo: float, hi: float) -> bool:
    return t is not None and lo <= t <= hi


# ---------- I/O ----------

def http_json(path: str, timeout: float) -> Any:
    req = urllib.request.Request(BASE_URL + path, headers={"Accept": "application/json", "User-Agent": "waybill"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def psql_json(sql: str, timeout: float) -> Any:
    """Run one read-only statement that returns a single JSON value. The password never leaves the container."""
    script = "set default_transaction_read_only = on;\n" + sql + "\n"
    p = subprocess.run(PSQL_ARGV, input=script, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"psql exit {p.returncode}: {(p.stderr or p.stdout).strip()[:400]}")
    out = p.stdout.strip()
    return json.loads(out) if out else None


def _uuid_array(ids: list[str]) -> str:
    good = sorted({i for i in ids if is_uuid(i)})
    if not good:
        return "array[]::uuid[]"
    return "array[" + ",".join(f"'{i}'" for i in good) + "]::uuid[]"


def build_sql(event_ids: list[str], invocation_ids: list[str], session_id: str, lo_iso: str, hi_iso: str) -> str:
    cols = ("'id', id::text, 'type', type, 'subject', subject, 'time', time, 'received_at', received_at, "
            "'correlationid', correlationid::text, 'causationid', causationid::text, 'producer', producer, 'raw', raw")
    sid_check = "false"
    if _SAFE_SID.match(session_id or ""):
        sid_check = f"position(convert_to('{session_id}', 'UTF8') in raw) > 0"
    return (
        "select json_build_object(\n"
        f" 'archived', (select coalesce(json_agg(json_build_object('id', id::text, 'received_at', received_at)), '[]'::json)"
        f" from events where id = any({_uuid_array(event_ids)})),\n"
        f" 'mirrors', (select coalesce(json_agg(json_build_object({cols}) order by time), '[]'::json)"
        f" from events where type = '{HOOK_UPDATED}' and correlationid = any({_uuid_array(invocation_ids)})),\n"
        f" 'caused', (select coalesce(json_agg(json_build_object({cols}) order by time), '[]'::json)"
        f" from events where causationid = any({_uuid_array(event_ids)}) and type not like 'bloodbank.llm.%'"
        f" and not (id = any({_uuid_array(event_ids)}))),\n"
        f" 'dead', (select coalesce(json_agg(json_build_object('id', id, 'event_id', event_id, 'topic', topic,"
        f" 'reason', reason, 'error', error, 'received_at', received_at, 'raw_b64', encode(raw, 'base64')) order by received_at), '[]'::json)"
        f" from dead_letter where received_at >= '{lo_iso}' and received_at <= '{hi_iso}' and {sid_check})\n"
        ");"
    )


# ---------- building ----------

def _consume_span(frag: Fragment, eid: str, et: str, t_env: float | None, t_arch: float | None,
                  status: str = "ok", reason: str | None = None, summary: str | None = None) -> str:
    sid = Ids.consume(CONSUMER, eid)
    lag = (t_arch - t_env) if (t_arch is not None and t_env is not None) else None
    if summary is None:
        if lag is not None:
            summary = f"Candystore archived {short_type(et)} {int(round(lag))} ms after it was published"
        else:
            summary = f"Candystore archived {short_type(et)} (archive time not read)"
    frag.spans.append(Span(
        id=sid, kind="consume", component="candystore", name=short_type(et), summary=summary,
        phase=phase_for_type(et), t0=t_env if t_env is not None else (t_arch or 0.0), t1=t_arch,
        status=status, reason=reason, sync=False, refs={"event_id": eid},
        attrs={"consumer": CONSUMER, "lag_ms": lag, "archived_at": iso(t_arch), "event_type": et},
        evidence=[NAME]))
    frag.links.append(Link(Ids.evt(eid), sid, "delivers"))
    return sid


def _event(frag: Fragment, ctx: Ctx, env: dict, archived: float | None, published: set[str],
           outcome: str = "archived", fallback: dict | None = None) -> BusEvent:
    fallback = fallback or {}
    eid = env.get("id") or fallback.get("id")
    et, subject = normalize_type(env)
    if et == "unknown" and fallback.get("type"):
        et = fallback["type"]
    subject = subject or fallback.get("subject")
    t_env = ms(env.get("time")) or ms(fallback.get("time")) or archived or ctx.window.t0
    consumer = Consumer(name=CONSUMER, component="candystore", kind="durable", outcome=outcome,
                        filter="bloodbank.evt.>", t=archived, evidence="observed",
                        span=Ids.consume(CONSUMER, eid))
    return BusEvent(
        id=eid, type=et, t=t_env, subject=subject, archived=archived,
        correlationid=env.get("correlationid") or fallback.get("correlationid"),
        causationid=env.get("causationid") or fallback.get("causationid"),
        producer=env.get("producer") or fallback.get("producer") or env.get("source"),
        publisher_span=Ids.publish(eid) if eid in published else None,
        consumers=[consumer], payload=envelope_artifact(frag, env, ctx.profile))


def build(frag: Fragment, ctx: Ctx, session_events: list[dict], pg: dict | None, published: set[str],
          inv_ids: list[str]) -> None:
    frag.component("candystore", "Candystore", "store")
    lo, hi = ctx.margin(2000.0, 0.0)
    archived = {r["id"]: ms(r.get("received_at")) for r in (pg or {}).get("archived", [])}
    seen: set[str] = set()

    for e in session_events:
        env = e["_env"]
        eid = env.get("id") or e.get("id")
        if not eid or eid in seen:
            continue
        seen.add(eid)
        arch = archived.get(eid)
        ev = _event(frag, ctx, env, arch, published, fallback=e)
        frag.events.append(ev)
        if arch is not None:
            _consume_span(frag, eid, ev.type, ev.t, arch)
        elif pg is not None:
            frag.gaps.append(Gap("candystore", f"{short_type(ev.type)} {eid} has no received_at",
                                 "the HTTP API returned it but Postgres had no row for the id", "info"))

    # hook-hub's hook.updated mirrors (correlationid = invocation id, real JetStream PubAck)
    inv_set = set(inv_ids)
    for r in (pg or {}).get("mirrors", []):
        eid = r["id"]
        if eid in seen:
            continue
        seen.add(eid)
        env = r.get("raw") if isinstance(r.get("raw"), dict) else {}
        arch = ms(r.get("received_at"))
        ev = _event(frag, ctx, env, arch, published, fallback=r)
        ev.producer = ev.producer or "hook-hub"
        frag.events.append(ev)
        _consume_span(frag, eid, ev.type, ev.t, arch)
        inv = r.get("correlationid")
        if inv in inv_set:
            frag.links.append(Link(Ids.hook(inv), Ids.evt(eid), "mirrors", "hook.updated"))

    # service-produced events caused by the turn's events (turn-enricher turn.annotated, artifact.created ...)
    for r in (pg or {}).get("caused", []):
        eid = r["id"]
        if eid in seen or (r.get("producer") or "") in AGENT_PRODUCERS:
            continue  # agent events come from the session listing; one caused by our last event is the next turn's
        t_env = ms(r.get("time"))
        if not in_window(t_env, lo, hi + 10_000):
            continue
        seen.add(eid)
        env = r.get("raw") if isinstance(r.get("raw"), dict) else {}
        arch = ms(r.get("received_at"))
        ev = _event(frag, ctx, env, arch, published, fallback=r)
        frag.events.append(ev)
        _consume_span(frag, eid, ev.type, ev.t, arch)
    # true causation for service-produced events (the publisher chain stays in attrs.causationid only)
    ids_here = {ev.id for ev in frag.events}
    for ev in frag.events:
        if ev.causationid and ev.causationid in ids_here and ev.producer not in AGENT_PRODUCERS \
                and ev.causationid != ev.id:
            frag.links.append(Link(Ids.evt(ev.causationid), Ids.evt(ev.id), "causes", ev.producer))

    # dead letters that mention the session (the enricher's report.session.completed)
    for r in (pg or {}).get("dead", []):
        try:
            raw_text = base64.b64decode(r.get("raw_b64") or "").decode("utf-8", "replace")
        except (ValueError, TypeError):
            raw_text = ""
        try:
            env = json.loads(raw_text) if raw_text else {}
        except ValueError:
            env = {}
        eid = env.get("id") or r.get("event_id") or f"dead_letter:{r.get('id')}"
        et, subject = normalize_type(env) if env else ("unknown", r.get("topic"))
        arch = ms(r.get("received_at"))
        reason = r.get("reason") or "dead_letter"
        err = r.get("error") or ""
        src = env.get("source") or "unknown producer"
        if eid not in seen:
            seen.add(eid)
            frag.events.append(BusEvent(
                id=eid, type=et, t=ms(env.get("time")) or arch or ctx.window.t0, subject=subject, archived=None,
                correlationid=env.get("correlationid"), causationid=env.get("causationid"), producer=src,
                consumers=[Consumer(name=CONSUMER, component="candystore", kind="durable", outcome="dropped",
                                    filter="bloodbank.evt.>", t=arch, evidence="observed",
                                    span=Ids.consume(CONSUMER, eid))],
                payload=envelope_artifact(frag, env or {"raw": raw_text}, ctx.profile, "Candystore dead_letter.raw")))
            _consume_span(frag, eid, et, ms(env.get("time")), arch, status="dropped", reason=reason,
                          summary=f"Candystore dead-lettered {short_type(et)} from {src}: {reason}"
                                  + (f" ({err})" if err else ""))
        if src == "enricher" or et.endswith("report.session.completed"):
            frag.component("enricher", "enricher", "service")
            title = "enricher session report dead-lettered by Candystore"
        else:
            title = f"{short_type(et)} dead-lettered by Candystore"
        summary_text = (env.get("data") or {}).get("summary") if isinstance(env.get("data"), dict) else None
        frag.findings.append(Finding(
            "broken", title,
            f"Candystore rejected {et} {eid} from {src} on {r.get('topic') or 'its topic'} ({reason}: {err or 'no error text'})"
            + (f"; the summary '{summary_text}' survives only in dead_letter.raw" if summary_text else "")
            + ". It is a Dapr envelope (type com.dapr.event.sent), not a 33GOD CloudEvent.",
            "candystore", [Ids.evt(eid), Ids.consume(CONSUMER, eid), NAME]))


def collect(ctx: Ctx) -> Fragment:
    started = time.monotonic()
    w = ctx.window
    src = Source(id=NAME, kind="http+postgres",
                 locator=f"{BASE_URL}/sessions/<sid> + docker exec {PG_CONTAINER} psql (read-only)")
    frag = Fragment(source=src)
    lo, hi = ctx.margin(2000.0, 0.0)
    try:
        corr = correlation_id(w.cli, w.session_id)
        published = {p["event_id"] for p in hookhub.published_events(ctx)}
        inv_ids = hookhub.invocation_ids(ctx)
        sess = http_json("/sessions/" + urllib.parse.quote(corr, safe=""), ctx.timeout_s)
        rows = []
        for e in (sess or {}).get("events", []) or []:
            et = e.get("type") or ""
            if et.startswith("bloodbank.llm."):
                continue
            if not in_window(ms(e.get("time")), lo, hi) and e.get("id") not in published:
                continue
            env = e.get("raw") if isinstance(e.get("raw"), dict) else None
            if env is None and e.get("id"):
                try:
                    env = http_json(f"/events/{urllib.parse.quote(e['id'], safe='')}/raw", ctx.timeout_s)
                except Exception:
                    env = None
            e["_env"] = env if isinstance(env, dict) else {k: e.get(k) for k in ("id", "type", "time", "correlationid", "producer", "data")}
            rows.append(e)
        pg = None
        try:
            sql = build_sql([r["_env"].get("id") or r.get("id") for r in rows] + sorted(published),
                            inv_ids, w.session_id, iso(lo), iso(hi))
            pg = psql_json(sql, max(ctx.timeout_s, 30.0))
        except Exception as exc:
            src.error = f"postgres: {type(exc).__name__}: {exc}"
            frag.gaps.append(Gap("candystore", "Candystore archive times, hook.updated mirrors and dead letters not read",
                                 src.error, "warn"))
        build(frag, ctx, rows, pg, published, inv_ids)
        src.items = len(frag.events)
        src.status = "ok" if frag.events else "empty"
        archived_ids = {r["id"] for r in (pg or {}).get("archived", [])}
        pub_by_id = {p["event_id"]: p for p in hookhub.published_events(ctx)}
        missing = sorted(published - {ev.id for ev in frag.events} - archived_ids) if pg is not None else []
        for eid in missing:
            p = pub_by_id.get(eid, {})
            et = p.get("event_type") or ""
            if et.startswith("deckard."):
                continue  # attention events never reach JetStream, so Candystore never sees them
            frag.gaps.append(Gap("candystore", f"{short_type(et)} {eid} was published but is not in Candystore",
                                 "candystore-events never archived it (or its correlationid is not the session)",
                                 "warn", Ids.publish(eid)))
    except Exception as exc:  # fail soft
        src.status = "error"
        src.error = f"{type(exc).__name__}: {exc}"
        frag.gaps.append(Gap("candystore", "Candystore could not be read", src.error, "warn"))
    src.ms = (time.monotonic() - started) * 1000.0
    return frag
