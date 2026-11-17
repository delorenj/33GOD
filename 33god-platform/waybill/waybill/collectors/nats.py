"""NATS monitoring collector (SPEC section 1 rows 6-7, section 3a facts).

Read-only GETs on the monitoring port: /jsz for the JetStream stream and consumer inventory, /connz for
core subscribers. Produces no spans: the assembler turns facts['consumers'] and facts['core_subs'] into
INFERRED Consumers on every event whose subject they match (model.match_subject), and collectors that saw
a consumer act upgrade it to observed. Never creates a consumer, never connects to the client port.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from typing import Any

from ..model import Ctx, Finding, Fragment, Gap, Source, match_subject, ms, now_ms, registry_has
from . import hookhub

NAME = "nats"
MONITOR_URL = os.environ.get("WAYBILL_NATS_MONITOR", "http://127.0.0.1:8222")
STREAMS = ("BLOODBANK_EVENTS", "BLOODBANK_COMMANDS")
SUB_PREFIXES = ("bloodbank.", "deckard.")
STALE_MS = 3_600_000.0
N8N_IDLE_MS = 86_400_000.0
SNAPSHOT_GAP_MS = 60_000.0

# BB-41: these exact legacy delegation durables were reported inactive in the
# ticket's read-only check. The snapshot cannot verify current workflow state.
RETIRED_DELEGATION_DURABLES = frozenset({
    "n8n-l0J53w0TsS5PwETk-8b302a2c-5f47-5294-88de-9fbd52b2822b",
    "n8n-8mmqdMwQYA28ZwUj-d1000000-0000-4000-8000-000000000001",
})

# (regex on the consumer name, component id); first match wins
CONSUMER_COMPONENTS: list[tuple[str, str]] = [
    (r"^candystore-events$", "candystore"),
    (r"^enricher-events$", "enricher"),
    (r"^holocene_", "holocene"),
    (r"^bloodbank-artifact-sidecar", "artifact-sidecar"),
    (r"^bloodbank-artifact-vault-projector", "artifact-vault-projector"),
    (r"^candybar-", "candybar"),
    (r"^curator", "curator"),
    (r"^n8n-", "n8n"),
    (r"^milkshake", "milkshake"),
    (r"^target-watch", "target-watch"),
    (r"^aai-llm-observability", "aai-llm-observability"),
    (r"^pilot-", "pilot"),
    (r"^bloodbank-hermes-gateway", "hermes-gw"),
]

# core-NATS client connection name -> component id
CLIENT_COMPONENTS: list[tuple[str, str]] = [
    (r"ntfy-router", "ntfy-router"),
    (r"turn-enricher", "turn-enricher"),
    (r"^deckard", "deckard"),
    (r"hook-hub", "hook-hub"),
    (r"^agent-pad", "agent-pad"),
    (r"holocene", "holocene"),
    (r"^candybar", "candybar"),
    (r"artifact-sidecar", "artifact-sidecar"),
    (r"vault-projector", "artifact-vault-projector"),
    (r"^n8n-", "n8n"),
    (r"^bloodbank-pubsub$", "bb-dapr"),
    (r"^aai-llm-observability", "aai-llm-observability"),
    (r"^cost-bridge", "cost-bridge"),
    (r"^farm-command-bridge", "farm-command-bridge"),
    (r"^curator", "curator"),
    (r"^milkshake", "milkshake"),
    (r"^target-watch", "target-watch"),
    (r"hermes", "hermes-gw"),
]


def consumer_component(name: str) -> str:
    for pat, cid in CONSUMER_COMPONENTS:
        if re.search(pat, name or ""):
            return cid
    return f"ext:{name}"


def client_component(client: str | None) -> str:
    c = client or ""
    for pat, cid in CLIENT_COMPONENTS:
        if re.search(pat, c):
            return cid
    stripped = c[len("bloodbank-"):] if c.startswith("bloodbank-") else c
    if stripped and registry_has(stripped):
        return stripped
    return f"ext:{c or 'unnamed'}"


def _seq(d: Any) -> int | None:
    if isinstance(d, dict):
        v = d.get("stream_seq")
        return int(v) if isinstance(v, (int, float)) else None
    return None


def parse_jsz(jsz: dict) -> tuple[list[dict], dict[str, dict]]:
    consumers: list[dict] = []
    streams: dict[str, dict] = {}
    for acc in jsz.get("account_details") or []:
        for sd in acc.get("stream_detail") or []:
            name = sd.get("name")
            st = sd.get("state") or {}
            cfg = sd.get("config") or {}
            streams[name] = {
                "account": acc.get("name"), "messages": st.get("messages"), "bytes": st.get("bytes"),
                "first_seq": st.get("first_seq"), "last_seq": st.get("last_seq"),
                "first_ts": st.get("first_ts"), "last_ts": st.get("last_ts"),
                "consumer_count": st.get("consumer_count"), "subjects": cfg.get("subjects"),
                "max_age_ns": cfg.get("max_age"), "duplicate_window_ns": cfg.get("duplicate_window"),
                "storage": cfg.get("storage"),
            }
            if name not in STREAMS:
                continue
            for c in sd.get("consumer_detail") or []:
                ccfg = c.get("config") or {}
                filters = ccfg.get("filter_subjects") or ([ccfg["filter_subject"]] if ccfg.get("filter_subject") else [])
                durable = bool(ccfg.get("durable_name"))
                cname = c.get("name") or ccfg.get("durable_name") or ccfg.get("name")
                consumers.append({
                    "name": cname, "stream": name, "filter_subjects": filters,
                    "kind": "durable" if durable else "ephemeral",
                    "push_bound": bool(c.get("push_bound")),
                    "push": bool(ccfg.get("deliver_subject")),
                    "deliver_group": ccfg.get("deliver_group"),
                    "deliver_policy": ccfg.get("deliver_policy"), "ack_policy": ccfg.get("ack_policy"),
                    "ack_floor": _seq(c.get("ack_floor")), "delivered": _seq(c.get("delivered")),
                    "num_pending": c.get("num_pending"), "num_ack_pending": c.get("num_ack_pending"),
                    "num_redelivered": c.get("num_redelivered"), "num_waiting": c.get("num_waiting"),
                    "last_active": (c.get("delivered") or {}).get("last_active"),
                    "component": consumer_component(cname),
                })
    return consumers, streams


def parse_connz(connz: dict) -> list[dict]:
    subs: list[dict] = []
    for c in connz.get("connections") or []:
        client = c.get("name")
        if client and client.startswith("waybill"):
            continue  # our own probes, if any
        for s in c.get("subscriptions_list_detail") or []:
            subj = s.get("subject") or ""
            if not subj.startswith(SUB_PREFIXES):
                continue
            subs.append({"client": client, "subject": subj, "component": client_component(client),
                         "queue": s.get("qgroup"), "cid": c.get("cid"), "lang": c.get("lang"),
                         "msgs": s.get("msgs")})
    if not any(x for x in subs):
        # older servers only give subject names
        for c in connz.get("connections") or []:
            for subj in c.get("subscriptions_list") or []:
                if isinstance(subj, str) and subj.startswith(SUB_PREFIXES):
                    subs.append({"client": c.get("name"), "subject": subj,
                                 "component": client_component(c.get("name")), "cid": c.get("cid")})
    return subs


def idle_consumers(consumers: list[dict], subjects: list[str], now: float) -> list[dict]:
    """Durable consumers that should have received one of the turn's subjects but are not consuming."""
    out = []
    for c in consumers:
        if c["stream"] != "BLOODBANK_EVENTS" or not (c.get("num_pending") or 0):
            continue
        hit = sorted({s for s in subjects for f in c["filter_subjects"] if match_subject(f, s)})
        if not hit:
            continue
        last = ms(c.get("last_active"))
        unbound = c.get("push") and not c.get("push_bound")
        if c.get("component") == "n8n":
            # A waiting pull is live even if the last delivered message is old.
            # Last delivery age alone cannot prove 24 hours without polling.
            idle = not (c.get("push_bound") if c.get("push") else (c.get("num_waiting") or 0) > 0)
            if c.get("kind") == "durable" and idle and last is not None and now - last > N8N_IDLE_MS:
                out.append({**c, "subjects_hit": hit,
                            "idle_diagnosis": "retired_lane_residual" if c.get("name") in RETIRED_DELEGATION_DURABLES
                            else "orphan_candidate"})
            continue
        stale = last is None or now - last > STALE_MS
        if unbound or (stale and c.get("kind") == "durable"):
            out.append({**c, "subjects_hit": hit})
    return out


def http_json(path: str, timeout: float) -> Any:
    req = urllib.request.Request(MONITOR_URL + path, headers={"Accept": "application/json", "User-Agent": "waybill"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def collect(ctx: Ctx) -> Fragment:
    started = time.monotonic()
    src = Source(id=NAME, kind="http", locator=f"{MONITOR_URL}/jsz?streams=true&consumers=true&config=true + /connz?subs=detail")
    frag = Fragment(source=src)
    try:
        frag.component("bb-nats", "NATS JetStream", "bus")
        jsz = http_json("/jsz?streams=true&consumers=true&config=true", ctx.timeout_s)
        consumers, streams = parse_jsz(jsz)
        frag.facts["consumers"] = consumers
        frag.facts["streams"] = streams
        frag.facts["nats_observed_at"] = jsz.get("now")
        try:
            connz = http_json("/connz?subs=detail&limit=1024", ctx.timeout_s)
            frag.facts["core_subs"] = parse_connz(connz)
        except Exception as exc:
            frag.facts["core_subs"] = []
            src.error = f"connz: {type(exc).__name__}: {exc}"
            frag.gaps.append(Gap("bb-nats", "core-NATS subscribers not listed", src.error, "warn"))
        src.items = len(consumers)
        src.status = "ok" if consumers else "empty"
        now = ms(jsz.get("now")) or now_ms()
        if now - ctx.window.t_end > SNAPSHOT_GAP_MS:
            frag.gaps.append(Gap(
                "bb-nats", "consumer inventory is a snapshot at capture time, not at the turn",
                f"/jsz and /connz were read {int((now - ctx.window.t_end) / 1000)} s after the turn; consumers created "
                f"or removed in between are not reflected, and ack floors have moved on", "info"))
        subjects = sorted({p["subject"] for p in hookhub.published_events(ctx) if p.get("subject")})
        for c in idle_consumers(consumers, subjects, now):
            diagnosis = c.get("idle_diagnosis")
            if diagnosis == "retired_lane_residual":
                title = f"JetStream consumer {c['name']} has a retired-lane residual backlog"
                state = ("matches a historically inactive BB-41 delegation durable; current workflow state is not "
                         "verified by this NATS snapshot. Do not reactivate or replay it; verify ownership before retirement")
            elif diagnosis == "orphan_candidate":
                title = f"JetStream consumer {c['name']} is an idle backlog candidate"
                state = ("has no current bound push or waiting pull and last delivery was over 24 hours ago; "
                         "one snapshot does not prove a continuous outage or workflow activation state")
            else:
                title = f"JetStream consumer {c['name']} is not consuming"
                state = "unbound" if c.get("push") and not c.get("push_bound") else "idle"
            frag.findings.append(Finding(
                "warn", title,
                f"{c['name']} ({c['kind']}, filter {', '.join(c['filter_subjects']) or '>'}) matches "
                f"{', '.join(c['subjects_hit'])} from this turn but {state}"
                f" (last active {c.get('last_active') or 'never'}) with {c.get('num_pending')} messages pending.",
                c["component"], [NAME]))
    except Exception as exc:  # fail soft
        src.status = "error"
        src.error = f"{type(exc).__name__}: {exc}"
        frag.gaps.append(Gap("bb-nats", "NATS monitoring endpoint could not be read", src.error, "warn"))
    src.ms = (time.monotonic() - started) * 1000.0
    return frag
