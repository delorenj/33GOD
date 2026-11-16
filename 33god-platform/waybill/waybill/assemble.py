"""Merge collector Fragments into one SPEC-valid Waybill (SPEC sections 2, 3 and 3a).

assemble(window, fragments, profile, mode, argv) -> dict

Inside a Fragment every time is ABSOLUTE epoch ms; the Waybill holds ms relative to clock.t0.
Merging is by deterministic id. The first fragment that names a span owns its identity fields;
later fragments only fill blanks, add refs/attrs keys and extend evidence (they never blank out).
Status is the exception: a more specific status wins (failed > timeout > dropped > skipped > ok >
pending > unknown), because a collector that did not know the outcome leaves the default 'ok'.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import socket
from pathlib import Path
from typing import Any

from . import VERSION
from . import model as M

FORMAT = "33god.waybill"
SCHEMA_VERSION = 1

PHASES = ("prompt_submit", "model_call", "pre_tool", "tool", "post_tool", "turn_end",
          "async_after", "session_start", "session_end")
STATUSES = ("ok", "skipped", "failed", "timeout", "pending", "dropped", "unknown")
LINK_KINDS = ("calls", "runs", "publishes", "delivers", "injects", "feeds", "triggers", "writes",
              "records", "mirrors", "causes")
CONSUMER_KINDS = ("durable", "ephemeral", "core")
OUTCOMES = ("archived", "collected", "routed", "rate-limited", "digested", "ignored", "enriched",
            "delivered", "dropped", "unknown")
SEVERITIES = ("info", "warn", "broken")
SOURCE_STATUSES = ("ok", "empty", "error", "skipped")

PUBLIC_TEXT_LIMIT = 280
FULL_TEXT_LIMIT = 65536
DROPPED = "«dropped»"
ENV_KEYS = {"env", "environ", "environment", "env_vars"}

_STATUS_RANK = {"failed": 7, "timeout": 7, "dropped": 6, "skipped": 5, "ok": 4, "pending": 3, "unknown": 2}

TOOL_HOOKS = {"PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionRequest"}
PRE_TOOL_HOOKS = {"PreToolUse", "PermissionRequest"}
PROMPT_HOOKS = {"UserPromptSubmit"}
STOP_HOOKS = {"Stop", "StopFailure"}

# ext: components have no registry record; give them a readable name and a kind.
EXT_COMPONENTS: dict[str, tuple[str, str]] = {
    "ext:claude-code": ("Claude Code", "cli"),
    "ext:codex-cli": ("Codex CLI", "cli"),
    "ext:codex-exec": ("Codex exec (headless)", "cli"),
    "ext:codex-desktop": ("Codex Desktop", "cli"),
    "ext:nanoleaf": ("Nanoleaf panels", "device"),
    "ext:orca": ("Orca", "external"),
}
SURFACE_COMPONENT = {
    "claude-code": "ext:claude-code",
    "claude-code-headless": "ext:claude-code",
    "codex-cli": "ext:codex-cli",
    "codex-exec": "ext:codex-exec",
    "codex-desktop": "ext:codex-desktop",
}
# registry 'kind' -> waybill Component.kind, plus per-id overrides that read better in the player
_KIND_MAP = {"datastore": "store", "agent": "service", "feature": "service", "library": "service",
             "scheduler": "service", "contract": "service", "ui": "service"}
_KIND_OVERRIDE = {"hook-hub": "handler-host", "hindsight": "memory", "candystore": "store",
                  "holocene": "store", "redis": "store", "asm": "store", "bb-nats": "bus",
                  "bloodbank": "bus", "aai-gateway": "model", "bb-hook": "cli"}
# consumer-name prefixes -> component id, for inventory rows that name no component
_CONSUMER_COMPONENT = [
    ("candystore", "candystore"), ("enricher", "enricher"), ("holocene", "holocene"),
    ("ntfy", "ntfy-router"), ("deckard", "deckard"), ("turn-enricher", "turn-enricher"),
    ("aai-llm-observability", "aai-llm-observability"), ("n8n", "n8n"), ("candybar", "candybar"),
    ("bloodbank-artifact-sidecar", "artifact-sidecar"), ("artifact-sidecar", "artifact-sidecar"),
    ("bloodbank-artifact-vault-projector", "artifact-vault-projector"), ("curator", "curator"),
    ("cost-bridge", "cost-bridge"), ("hermes", "hermes-bloodbank-plugin"),
]

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


# ---------------------------------------------------------------- small helpers

def _empty(v: Any) -> bool:
    return v is None or v == "" or v == [] or v == {}


def _union(a: list, b: list) -> list:
    out = list(a or [])
    for x in b or []:
        if x not in out:
            out.append(x)
    return out


def merge_dict(a: dict, b: dict) -> dict:
    """Fill-blank merge: keys of b are added, nested dicts merge, existing non-empty values stay."""
    out = dict(a or {})
    for k, v in (b or {}).items():
        if k not in out or _empty(out[k]):
            out[k] = v
        elif isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = merge_dict(out[k], v)
        elif isinstance(out[k], list) and isinstance(v, list) and k in ("evidence", "banks", "tags"):
            out[k] = _union(out[k], v)
    return out


def _status_rank(s: Any) -> int:
    return _STATUS_RANK.get(s, 0) if isinstance(s, str) else 0


def merge_span(a: dict, b: dict) -> dict:
    """Merge span b into span a in place (a was seen first)."""
    if _status_rank(b.get("status")) > _status_rank(a.get("status")):
        a["status"] = b["status"]
        if b.get("reason"):
            a["reason"] = b["reason"]
    for k, v in b.items():
        if k in ("status", "id"):
            continue
        if k == "evidence":
            a["evidence"] = _union(a.get("evidence") or [], v or [])
        elif k in ("refs", "attrs"):
            a[k] = merge_dict(a.get(k) or {}, v or {})
        elif k == "sync":
            if v is not None:
                a["sync"] = bool(v) or bool(a.get("sync"))
        elif _empty(a.get(k)) and not _empty(v):
            a[k] = v
    return a


def merge_consumer(a: dict, b: dict) -> dict:
    observed = a.get("evidence") == "observed" or b.get("evidence") == "observed"
    if b.get("evidence") == "observed" and a.get("evidence") != "observed":
        # the observation is the better record; keep a's filter/kind if b has none
        for k in ("outcome", "t", "span", "component", "kind"):
            if not _empty(b.get(k)) and b.get(k) != "unknown":
                a[k] = b[k]
    for k, v in b.items():
        if k == "evidence":
            continue
        if k == "outcome":
            if (a.get("outcome") in (None, "", "unknown")) and v not in (None, "", "unknown"):
                a["outcome"] = v
        elif _empty(a.get(k)) and not _empty(v):
            a[k] = v
    a["evidence"] = "observed" if observed else "inferred"
    return a


def merge_event(a: dict, b: dict) -> dict:
    for k, v in b.items():
        if k == "consumers":
            have = {c.get("name"): c for c in a.setdefault("consumers", [])}
            for c in v or []:
                if c.get("name") in have:
                    merge_consumer(have[c["name"]], c)
                else:
                    a["consumers"].append(dict(c))
                    have[c.get("name")] = a["consumers"][-1]
        elif k == "schema":
            if isinstance(v, dict):
                a["schema"] = merge_dict(a.get("schema") or {}, v)
        elif _empty(a.get(k)) and not _empty(v):
            a[k] = v
    return a


def _jsonable(obj: Any) -> Any:
    d = M.to_jsonable(obj)
    if isinstance(d, dict) and "from_" in d and "from" not in d:
        d["from"] = d.pop("from_")
    return d


def _num(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return M.ms(v)


def _iso_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def fmt_duration(ms_: float | None) -> str:
    if ms_ is None:
        return "?"
    ms_ = max(0.0, float(ms_))
    if ms_ < 1000:
        return f"{int(round(ms_))} ms"
    s = ms_ / 1000.0
    if s < 10:
        return f"{s:.1f} s"
    if s < 60:
        return f"{int(round(s))} s"
    m, sec = divmod(int(round(s)), 60)
    if m < 60:
        return f"{m} m {sec:02d} s"
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} m"


def _b32(n: int, length: int) -> str:
    return "".join(_CROCKFORD[(n >> (5 * i)) & 31] for i in reversed(range(length)))


def waybill_id(t0_ms: float, session_id: str, turn_key: str) -> str:
    """'wb_' + 26 chars: 10 of Crockford base32 time (ULID layout) + 16 of a session/turn hash."""
    ts = int(t0_ms or 0) & ((1 << 48) - 1)
    h = int.from_bytes(hashlib.sha256(f"{session_id}|{turn_key}".encode()).digest()[:10], "big")
    return "wb_" + _b32(ts, 10) + _b32(h, 16)


_REG_CACHE: dict[str, tuple[str | None, str | None]] = {}


def _registry_meta(cid: str) -> tuple[str | None, str | None]:
    """(name, kind) from components/<id>.yaml top-level keys, without a yaml dependency."""
    if cid in _REG_CACHE:
        return _REG_CACHE[cid]
    name = kind = None
    try:
        p = M._REGISTRY_DIR / f"{cid}.yaml"
        if p.is_file():
            for line in p.read_text(errors="replace").splitlines():
                m = re.match(r"^(name|kind):\s*(.+?)\s*$", line)
                if m:
                    val = m.group(2).strip("'\"")
                    if m.group(1) == "name" and name is None:
                        name = val
                    elif m.group(1) == "kind" and kind is None:
                        kind = val
    except OSError:
        pass
    _REG_CACHE[cid] = (name, kind)
    return name, kind


def component_record(cid: str) -> dict:
    reg = M.registry_has(cid)
    if cid in EXT_COMPONENTS:
        name, kind = EXT_COMPONENTS[cid]
    else:
        rname, rkind = _registry_meta(cid) if reg else (None, None)
        name = rname or (cid[4:] if cid.startswith("ext:") else cid)
        kind = _KIND_OVERRIDE.get(cid) or _KIND_MAP.get(rkind or "", rkind) or (
            "external" if cid.startswith("ext:") else "service")
    return {"id": cid, "name": name, "kind": kind, "registry": reg}


def consumer_component(name: str | None) -> str:
    n = (name or "").lower()
    for prefix, cid in _CONSUMER_COMPONENT:
        if n.startswith(prefix):
            return cid
    if n and M.registry_has(n):
        return n
    return n or "unknown"


def _short_type(t: str | None) -> str:
    t = t or ""
    return t[len("bloodbank."):] if t.startswith("bloodbank.") else t


def _subject_for(event_type: str | None) -> str | None:
    if not event_type:
        return None
    return "bloodbank.evt." + _short_type(event_type)


def _hook_native(span: dict) -> str | None:
    a = span.get("attrs") or {}
    for k in ("native", "hook", "hook_event", "native_event"):
        if isinstance(a.get(k), str) and a[k]:
            return a[k]
    return span.get("name")


def _inv_of(span: dict) -> str | None:
    r = span.get("refs") or {}
    if r.get("invocation_id"):
        return r["invocation_id"]
    sid = span.get("id") or ""
    for prefix in ("hook:", "handler:", "context:", "memory:recall:", "memory:buffer:"):
        if sid.startswith(prefix):
            return sid[len(prefix):].split(":")[0]
    return None


def llm_tokens(span: dict) -> tuple[int, int, int]:
    """(input incl. cache, raw input, output) for an llm span; 0 when unknown.

    Accepts attrs.tokens_in / tokens_out (already totals), or attrs.usage / attrs with Anthropic or
    OpenAI style keys (input_tokens + cache_read_input_tokens + cache_creation_input_tokens).
    """
    a = span.get("attrs") or {}
    u = a.get("usage") if isinstance(a.get("usage"), dict) else {}

    def g(*keys: str) -> float | None:
        for d in (u, a):
            for k in keys:
                v = d.get(k)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    return v
        return None

    out = g("tokens_out", "output_tokens", "completion_tokens") or 0
    if isinstance(a.get("tokens_in"), (int, float)):
        total = a["tokens_in"]
        raw = g("input_tokens", "prompt_tokens")
        return int(total), int(raw if raw is not None else total), int(out)
    raw = g("input_tokens", "prompt_tokens") or 0
    cr = g("cache_read_input_tokens", "cache_read_tokens", "cached_tokens") or 0
    cw = g("cache_creation_input_tokens", "cache_write_input_tokens", "cache_creation_tokens") or 0
    return int(raw + cr + cw), int(raw), int(out)


# ---------------------------------------------------------------- the assembler

class _Acc:
    """Accumulates fragments in output shape (dicts), merged by id."""

    def __init__(self) -> None:
        self.spans: dict[str, dict] = {}
        self.events: dict[str, dict] = {}
        self.links: list[dict] = []
        self._link_keys: set[tuple] = set()
        self.artifacts: dict[str, dict] = {}
        self.gaps: list[dict] = []
        self.findings: list[dict] = []
        self.components: dict[str, dict] = {}
        self.sources: list[dict] = []
        self.facts: dict[str, Any] = {}
        self.alias: dict[str, str] = {}

    # -- adders
    def add_span(self, s: dict) -> None:
        if not isinstance(s, dict) or not s.get("id"):
            return
        s.setdefault("refs", {})
        s.setdefault("attrs", {})
        s.setdefault("evidence", [])
        if s["id"] in self.spans:
            merge_span(self.spans[s["id"]], s)
        else:
            self.spans[s["id"]] = s

    def add_event(self, e: dict) -> None:
        if not isinstance(e, dict) or not e.get("id"):
            return
        e.setdefault("consumers", [])
        if e["id"] in self.events:
            merge_event(self.events[e["id"]], e)
        else:
            # consumers of one event must be unique by name
            seen: dict[str, dict] = {}
            for c in list(e["consumers"]):
                if c.get("name") in seen:
                    merge_consumer(seen[c["name"]], c)
                    e["consumers"].remove(c)
                else:
                    seen[c.get("name")] = c
            self.events[e["id"]] = e

    def link(self, frm: str | None, to: str | None, kind: str, label: str | None = None) -> None:
        if not frm or not to or frm == to:
            return
        key = (frm, to, kind)
        if key in self._link_keys:
            return
        self._link_keys.add(key)
        d = {"from": frm, "to": to, "kind": kind}
        if label:
            d["label"] = label
        self.links.append(d)

    def gap(self, component: str, what: str, why: str, severity: str = "info", span: str | None = None) -> None:
        g = {"component": component, "what": what, "why": why, "severity": severity, "span": span}
        if g not in self.gaps:
            self.gaps.append(g)

    def finding(self, severity: str, title: str, detail: str, component: str, evidence: list[str]) -> None:
        if any(f.get("title") == title for f in self.findings):
            return
        self.findings.append({"severity": severity, "title": title, "detail": detail,
                              "component": component, "evidence": list(evidence)})

    def add_fragment(self, frag: Any) -> None:
        src = _jsonable(getattr(frag, "source", None)) if frag is not None else None
        if isinstance(src, dict):
            self.sources.append(src)
        for s in getattr(frag, "spans", None) or []:
            self.add_span(_jsonable(s))
        for e in getattr(frag, "events", None) or []:
            self.add_event(_jsonable(e))
        for ln in getattr(frag, "links", None) or []:
            d = _jsonable(ln)
            if isinstance(d, dict):
                self.link(d.get("from"), d.get("to"), d.get("kind") or "causes", d.get("label"))
        for aid, art in (getattr(frag, "artifacts", None) or {}).items():
            if aid not in self.artifacts:
                self.artifacts[aid] = _jsonable(art)
        for g in getattr(frag, "gaps", None) or []:
            d = _jsonable(g)
            if isinstance(d, dict) and d not in self.gaps:
                self.gaps.append(d)
        for f in getattr(frag, "findings", None) or []:
            d = _jsonable(f)
            if isinstance(d, dict) and not any(x.get("title") == d.get("title") for x in self.findings):
                self.findings.append(d)
        for cid, comp in (getattr(frag, "components", None) or {}).items():
            d = _jsonable(comp)
            if isinstance(d, dict):
                d.setdefault("id", cid)
                if cid in self.components:
                    self.components[cid] = merge_dict(self.components[cid], d)
                else:
                    self.components[cid] = d
        for k, v in (getattr(frag, "facts", None) or {}).items():
            if k in ("consumers", "core_subs") and isinstance(v, list):
                self.facts.setdefault(k, []).extend(v)
            elif _empty(self.facts.get(k)) and not _empty(v):
                self.facts[k] = v

    # -- id rewrite
    def rename(self, old: str, new: str) -> None:
        if old == new or old not in self.spans:
            return
        s = self.spans.pop(old)
        s["id"] = new
        if new in self.spans:
            merge_span(self.spans[new], s)
        else:
            self.spans[new] = s
        self.alias[old] = new

    def resolve(self, sid: str | None) -> str | None:
        seen = 0
        while sid in self.alias and seen < 20:
            sid = self.alias[sid]
            seen += 1
        return sid


SUBAGENT_LAUNCHERS = {"Agent", "Task", "Workflow"}
SUBAGENT_START = {"SubagentStart"}
SUBAGENT_STOP = {"SubagentStop"}


def _off_thread(s: dict) -> bool:
    """An llm/tool span that is not part of the main conversation thread: a subagent call, a background call
    the client never logged (session title), or a gateway row no transcript call matched."""
    a = s.get("attrs") or {}
    return bool(a.get("subagent") or a.get("agent_id") or a.get("background")
                or a.get("counterpart") in ("subagent", "none") or a.get("client_seen") is False)


def _first_llm_after(llms: list[dict], t: float, tol: float = 50.0) -> dict | None:
    for s in llms:
        if s.get("t0") is not None and s["t0"] >= t - tol:
            return s
    return None


def _last_llm_before(llms: list[dict], t: float) -> dict | None:
    best = None
    for s in llms:
        if s.get("t0") is not None and s["t0"] <= t:
            best = s
    return best


def _payload_json(acc: _Acc, ref: str | None) -> Any:
    art = acc.artifacts.get(ref) if ref else None
    if not isinstance(art, dict):
        return None
    if "json" in art:
        return art["json"]
    if art.get("mime") == "application/json" and isinstance(art.get("text"), str):
        try:
            return json.loads(art["text"])
        except ValueError:
            return None
    return None


def _event_tool_call_ids(acc: _Acc, ev: dict) -> list[str]:
    """Every tool id the event carries. Codex hooks put a hook-made hash in data.tool_call_id and the model's
    call_... id in data.payload.tool_use_id, so the caller keeps whichever one names a tool span."""
    env = _payload_json(acc, ev.get("payload"))
    if not isinstance(env, dict):
        return []
    data = env.get("data") if isinstance(env.get("data"), dict) else {}
    out: list[str] = []
    for d in (data.get("payload") if isinstance(data.get("payload"), dict) else {}, data):
        for k in ("tool_call_id", "tool_use_id", "call_id"):
            if isinstance(d.get(k), str) and d[k] and d[k] not in out:
                out.append(d[k])
    return out


def _event_tool_call_id(acc: _Acc, ev: dict) -> str | None:
    ids = _event_tool_call_ids(acc, ev)
    return ids[0] if ids else None


# ---- join passes (all on absolute times) -------------------------------------------------

def _resolve_match_llm(acc: _Acc) -> None:
    gws = [s for s in acc.spans.values() if isinstance(s.get("attrs"), dict) and "_match_llm" in s["attrs"]]
    if not gws:
        return
    llms = [s for s in acc.spans.values() if s.get("kind") == "llm" and "_match_llm" not in (s.get("attrs") or {})]
    used: set[str] = set()
    hints = []
    for g in gws:
        h = g["attrs"].pop("_match_llm") or {}
        near = _num(h.get("near")) or g.get("t1") or g.get("t0") or 0.0
        hints.append((near, g, h))
    hints.sort(key=lambda x: x[0])
    for near, g, h in hints:
        try:
            gin, gout = int(h.get("input_tokens") or 0), int(h.get("output_tokens") or 0)
        except (TypeError, ValueError):
            continue
        if gin + gout <= 0:
            g["attrs"]["client_seen"] = False
            continue
        cands = []
        for s in llms:
            if s["id"] in used:
                continue
            total, raw, out = llm_tokens(s)
            if out == gout and gin in (total, raw):
                cands.append(s)
        if not cands:
            # a call the client never logged (background ai-title, a subagent): keep it, but keep it out
            # of the prompt -> llm -> tool chain unless there is no client-side llm span at all
            g["attrs"]["client_seen"] = False
            continue
        best = min(cands, key=lambda s: abs(near - (s.get("t1") or s.get("t0") or near)))
        used.add(best["id"])
        merge_span(best, g)
        acc.spans.pop(g["id"], None)
        acc.alias[g["id"]] = best["id"]


def _event_type_matches(want: str, have: str | None) -> bool:
    if not have or not want:
        return False
    return have == want or have.endswith("." + _short_type(want)) or _short_type(have) == _short_type(want)


def _resolve_joins(acc: _Acc) -> None:
    hinted = [s for s in list(acc.spans.values()) if isinstance(s.get("attrs"), dict) and "_join" in s["attrs"]]
    if not hinted:
        return
    jobs = []
    for s in hinted:
        h = s["attrs"].pop("_join") or {}
        near = _num(h.get("near")) or s.get("t0")
        jobs.append((near or 0.0, s, h))
    jobs.sort(key=lambda x: x[0])
    by_type: dict[str, list[dict]] = {}
    claimed: set[tuple[str, str]] = set()
    renames: list[tuple[str, str]] = []
    for near, s, h in jobs:
        et = h.get("event_type") or ""
        if et not in by_type:  # 'session.started' (ntfy log) matches 'bloodbank.agent.session.started'
            by_type[et] = [ev for ev in acc.events.values() if _event_type_matches(et, ev.get("type"))]
        w = float(h.get("window_ms") or 3000.0)
        consumer = h.get("consumer")
        key = consumer or s.get("component") or s["id"]
        cands = [ev for ev in by_type[et]
                 if ev.get("t") is not None and abs(ev["t"] - near) <= w and (key, ev["id"]) not in claimed]
        if not cands:
            acc.gap(s.get("component") or "unknown", f"{s.get('name') or s['id']} could not be tied to a {_short_type(et)} event",
                    f"no {_short_type(et)} event within ±{int(w)} ms of the observation (the source carries no event id)",
                    "info", s["id"])
            continue
        # an observer sees an event after it was published: penalise candidates from the future
        best = min(cands, key=lambda ev: (abs(near - ev["t"]) + (0.0 if ev["t"] <= near + 250 else w), ev["t"]))
        claimed.add((key, best["id"]))
        s.setdefault("refs", {}).setdefault("event_id", best["id"])
        target = s["id"]
        if consumer and s.get("kind") == "consume":
            target = M.Ids.consume(consumer, best["id"])
            if target != s["id"]:
                renames.append((s["id"], target))
        acc.link(M.Ids.evt(best["id"]), target, h.get("link") or "delivers")
        if consumer:
            c = {"name": consumer, "component": s.get("component") or consumer_component(consumer),
                 "kind": h.get("consumer_kind") or "core", "filter": h.get("filter"),
                 "outcome": h.get("outcome") or "unknown", "t": s.get("t0"), "evidence": "observed",
                 "span": target}
            merge_event(best, {"consumers": [c]})
    for old, new in renames:
        acc.rename(old, new)


def _infer_consumers(acc: _Acc) -> None:
    cons = acc.facts.get("consumers") or []
    subs = acc.facts.get("core_subs") or []
    if not cons and not subs:
        return
    for ev in acc.events.values():
        subj = ev.get("subject") or _subject_for(ev.get("type"))
        if not subj:
            continue
        add: list[dict] = []
        # an event no bus collector saw (a stub from the publisher receipt) reached core subscribers
        # at most; never claim a JetStream consumer received it
        for c in (cons if ev.get("observed_on_bus") is not False else []):
            if not isinstance(c, dict) or not c.get("name"):
                continue
            stream = c.get("stream")
            if stream and ev.get("stream") and stream != ev["stream"]:
                continue
            filters = c.get("filter_subjects") or ([c["filter_subject"]] if c.get("filter_subject") else [])
            if filters:
                hit = next((f for f in filters if M.match_subject(f, subj)), None)
                if hit is None:
                    continue
            else:
                if not subj.startswith("bloodbank.evt.") and not stream:
                    continue
                hit = None
            kind = c.get("kind") if c.get("kind") in CONSUMER_KINDS else "durable"
            add.append({"name": c["name"], "component": c.get("component") or consumer_component(c["name"]),
                        "kind": kind, "filter": hit, "outcome": "unknown", "t": None,
                        "evidence": "inferred", "span": None})
        seen_core: set[str] = set()
        for sb in subs:
            if not isinstance(sb, dict):
                continue
            name = sb.get("client") or sb.get("name")
            if not name or name in seen_core or not M.match_subject(sb.get("subject"), subj):
                continue
            seen_core.add(name)
            add.append({"name": name, "component": sb.get("component") or consumer_component(name),
                        "kind": "core", "filter": sb.get("subject"), "outcome": "unknown", "t": None,
                        "evidence": "inferred", "span": None})
        if add:
            merge_event(ev, {"consumers": add})


def _settle_consumers(acc: _Acc) -> None:
    """Observed consumers absorb the inferred inventory rows of the same component."""
    for ev in acc.events.values():
        cs = ev.get("consumers") or []
        if ev.get("archived") is not None and not any(
                c.get("component") == "candystore" and c.get("evidence") == "observed" for c in cs):
            merge_event(ev, {"consumers": [{"name": "candystore-events", "component": "candystore",
                                            "kind": "durable", "filter": None, "outcome": "archived",
                                            "t": ev["archived"], "evidence": "observed", "span": None}]})
            cs = ev["consumers"]
        observed = [c for c in cs if c.get("evidence") == "observed"]
        keep = []
        for c in cs:
            if c.get("evidence") != "observed":
                twin = next((o for o in observed if o.get("component") == c.get("component")
                             and (o.get("kind") == c.get("kind") or
                                  (o.get("name") or "").split("-")[0] == (c.get("name") or "").split("-")[0])), None)
                if twin is not None:
                    if not twin.get("filter") and c.get("filter"):
                        twin["filter"] = c["filter"]
                    continue
            keep.append(c)
        for c in keep:
            if c.get("kind") not in CONSUMER_KINDS:
                c["kind"] = "core"
            if c.get("outcome") not in OUTCOMES:
                c["outcome"] = "unknown"
            if c.get("evidence") not in ("observed", "inferred"):
                c["evidence"] = "inferred"
        ev["consumers"] = keep


def _publish_chain(acc: _Acc) -> None:
    for s in list(acc.spans.values()):
        if s.get("kind") != "handler":
            continue
        refs = s.get("refs") or {}
        eid = refs.get("event_id")
        if not eid:
            continue
        attrs = s.get("attrs") or {}
        pid = M.Ids.publish(eid)
        etype = refs.get("event_type") or attrs.get("event_type")
        ev = acc.events.get(eid)
        if ev and not etype:
            etype = ev.get("type")
        if pid not in acc.spans:
            hid = attrs.get("handler_id") or refs.get("handler_id") or s["id"].split(":")[-1]
            pstat = attrs.get("publish_status") or refs.get("publish_status")
            ok = pstat in (None, "", "sent", "ok", "published", "acked")
            comp = "agent-hooks" if hid == "bloodbank-publisher" else (s.get("component") or "hook-hub")
            acc.add_span({
                "id": pid, "kind": "publish", "component": comp, "name": _short_type(etype) or "event",
                "summary": f"{comp} published {_short_type(etype) or 'an event'}"
                           + (f" ({pstat}: a core-NATS PONG, not a JetStream ack)" if pstat == "sent" else
                              (f" ({pstat})" if pstat else "")),
                "phase": s.get("phase"), "t0": s.get("t0"), "t1": s.get("t1"),
                "status": "ok" if ok else "failed", "reason": None if ok else pstat,
                "sync": False, "parent": s["id"],
                "refs": {"event_id": eid, "invocation_id": refs.get("invocation_id"), "handler_id": hid},
                "attrs": {"event_type": etype, "publish_status": pstat, "derived": "handler.refs.event_id"},
                "evidence": list(s.get("evidence") or []),
            })
        acc.link(s["id"], pid, "calls")
        if ev is None:
            ps = acc.spans[pid]
            acc.add_event({
                "id": eid, "type": etype or "unknown", "subject": _subject_for(etype), "stream": None,
                "seq": None, "t": ps.get("t1") or ps.get("t0"), "stored": None, "archived": None,
                "correlationid": None, "causationid": None, "producer": ps.get("component"),
                "publisher_span": pid, "consumers": [], "observed_on_bus": False,
            })
            ev = acc.events[eid]
        if not ev.get("publisher_span"):
            ev["publisher_span"] = pid
    for s in acc.spans.values():
        if s.get("kind") == "publish":
            eid = (s.get("refs") or {}).get("event_id")
            if not eid and s["id"].startswith("publish:"):
                eid = s["id"][len("publish:"):]
            if eid and eid in acc.events:
                acc.link(s["id"], M.Ids.evt(eid), "publishes")
                if not acc.events[eid].get("publisher_span"):
                    acc.events[eid]["publisher_span"] = s["id"]
                if not acc.events[eid].get("producer"):
                    acc.events[eid]["producer"] = s.get("component")


def _tool_hooks(acc: _Acc) -> int:
    """Parent PreToolUse/PostToolUse hooks under tool:<tool_call_id>. Returns unparented count."""
    ev_tool: dict[str, list[str]] = {}
    for ev in acc.events.values():
        tcs = _event_tool_call_ids(acc, ev)
        if tcs:
            ev_tool[ev["id"]] = tcs
    for s in acc.spans.values():
        r = s.get("refs") or {}
        if s.get("kind") == "publish" and r.get("event_id") and r.get("tool_use_id"):
            ev_tool.setdefault(r["event_id"], []).append(r["tool_use_id"])
    handlers_by_inv: dict[str, list[dict]] = {}
    for s in acc.spans.values():
        if s.get("kind") == "handler":
            inv = _inv_of(s)
            if inv:
                handlers_by_inv.setdefault(inv, []).append(s)
    unparented = 0
    for s in acc.spans.values():
        if s.get("kind") != "hook" or _hook_native(s) not in TOOL_HOOKS:
            continue
        refs = s.setdefault("refs", {})
        cands = [refs["tool_use_id"]] if refs.get("tool_use_id") else []
        eids = [refs.get("event_id")] + [(h.get("refs") or {}).get("event_id")
                                         for h in handlers_by_inv.get(_inv_of(s) or "", [])]
        for eid in eids:
            if eid and eid in ev_tool:
                cands += [c for c in ev_tool[eid] if c not in cands]
        tc = next((c for c in cands if M.Ids.tool(c) in acc.spans), None)
        if not tc:
            unparented += 1
            continue
        refs["tool_use_id"] = tc
        tid = M.Ids.tool(tc)
        s["parent"] = tid
        if _hook_native(s) in PRE_TOOL_HOOKS:
            acc.link(s["id"], tid, "triggers", "allowed the tool")
        else:
            acc.link(tid, s["id"], "triggers")
    return unparented


def _default_parents_and_links(acc: _Acc) -> None:
    spans = acc.spans
    for s in spans.values():
        sid, kind = s["id"], s.get("kind")
        inv = _inv_of(s)
        hook_id = M.Ids.hook(inv) if inv else None
        if kind == "handler" and hook_id in spans:
            if not s.get("parent"):
                s["parent"] = hook_id
            acc.link(hook_id, sid, "runs")
        elif kind == "context" and hook_id in spans:
            if not s.get("parent"):
                s["parent"] = hook_id
            parts = sid.split(":")
            src = M.Ids.handler(inv, parts[2]) if len(parts) > 2 else None
            acc.link(src if src in spans else hook_id, sid, "injects")
        elif kind == "memory" and inv and sid.startswith(("memory:recall:", "memory:buffer:")):
            hid = M.Ids.handler(inv, "hindsight-recall" if sid.startswith("memory:recall:") else "hindsight-turn")
            owner = hid if hid in spans else (hook_id if hook_id in spans else None)
            if owner:
                if not s.get("parent"):
                    s["parent"] = owner
                acc.link(owner, sid, "calls")
        elif kind == "consume" and sid.startswith("consume:"):
            eid = sid.split(":", 2)[-1]
            pid = M.Ids.publish(eid)
            if not s.get("parent") and pid in spans:
                s["parent"] = pid
            if eid in acc.events:
                acc.link(M.Ids.evt(eid), sid, "delivers")

    all_llms = sorted([s for s in spans.values() if s.get("kind") == "llm" and s.get("t0") is not None],
                      key=lambda s: (s["t0"], s["id"]))
    llms = [s for s in all_llms if not _off_thread(s)] or [s for s in all_llms if not (s.get("attrs") or {}).get("agent_id")]
    prompt = spans.get(M.Ids.PROMPT)
    hooks = [s for s in spans.values() if s.get("kind") == "hook"]
    for h in hooks:
        nat = _hook_native(h)
        if nat in PROMPT_HOOKS and prompt is not None:
            acc.link(M.Ids.PROMPT, h["id"], "calls")
            if not h.get("parent"):
                h["parent"] = M.Ids.PROMPT
        elif nat in STOP_HOOKS and h.get("t0") is not None:
            last = _last_llm_before(llms, h["t0"])
            if last is not None:
                acc.link(last["id"], h["id"], "triggers", "turn ended")
    if prompt is not None and llms:
        acc.link(M.Ids.PROMPT, llms[0]["id"], "feeds")
    for c in [s for s in spans.values() if s.get("kind") == "context"]:
        t = c.get("t1") if c.get("t1") is not None else c.get("t0")
        if t is None:
            continue
        nxt = _first_llm_after(llms, t)
        if nxt is not None:
            acc.link(c["id"], nxt["id"], "feeds")
    # model -> tool loop
    by_parent: dict[str, list[dict]] = {}
    for s in spans.values():
        if s.get("kind") == "hook" and s.get("parent", "") and str(s.get("parent")).startswith("tool:"):
            by_parent.setdefault(s["parent"], []).append(s)
    for t in sorted([s for s in spans.values() if s.get("kind") == "tool" and s.get("t0") is not None
                     and not _off_thread(s)], key=lambda s: (s["t0"], s["id"])):
        par = spans.get(t.get("parent") or "")
        issuer = par if par is not None and par.get("kind") == "llm" else _last_llm_before(llms, t["t0"])
        if issuer is not None and not t.get("parent"):
            t["parent"] = issuer["id"]
        pres = [h for h in by_parent.get(t["id"], []) if _hook_native(h) in PRE_TOOL_HOOKS]
        if issuer is not None:
            if pres:
                for h in pres:
                    acc.link(issuer["id"], h["id"], "triggers", "tool_use")
            else:
                acc.link(issuer["id"], t["id"], "calls", "tool_use")
        end = t.get("t1") if t.get("t1") is not None else t["t0"]
        nxt = _first_llm_after([s for s in llms if s is not issuer], end, tol=0.0)
        if nxt is not None:
            acc.link(t["id"], nxt["id"], "feeds", "tool_result")


def _hook_event_data(acc: _Acc, hook: dict) -> dict:
    """data of the CloudEvent the hook's bloodbank-publisher sent (via attrs.published_event_id / handler refs)."""
    inv = _inv_of(hook)
    eids = [(hook.get("attrs") or {}).get("published_event_id"), (hook.get("refs") or {}).get("event_id")]
    if inv:
        h = acc.spans.get(M.Ids.handler(inv, "bloodbank-publisher"))
        if h:
            eids.append((h.get("refs") or {}).get("event_id"))
    for eid in eids:
        ev = acc.events.get(eid) if eid else None
        env = _payload_json(acc, ev.get("payload")) if ev else None
        if isinstance(env, dict):
            d = env.get("data") if isinstance(env.get("data"), dict) else env
            if isinstance(d, dict):
                return d
    return {}


def _subagents(acc: _Acc) -> int:
    """Hang subagent work under the hook that started it.

    SubagentStart's invocation.started event carries the agent id (data.invocation_id); sidechain tool spans and
    subagent gateway rows carry attrs.agent_id. The SubagentStart hook hangs under the main-thread tool that
    launched it (Agent / Task / Workflow). Returns the number of subagent spans left without a start hook."""
    spans = acc.spans
    hooks = [s for s in spans.values() if s.get("kind") == "hook" and s.get("t0") is not None]
    starts: dict[str, dict] = {}
    for h in hooks:
        if _hook_native(h) in SUBAGENT_START:
            aid = _hook_event_data(acc, h).get("invocation_id")
            if isinstance(aid, str) and aid:
                h.setdefault("attrs", {}).setdefault("agent_id", aid)
                starts.setdefault(aid, h)
    launchers = sorted([s for s in spans.values() if s.get("kind") == "tool" and s.get("name") in SUBAGENT_LAUNCHERS
                        and s.get("t0") is not None], key=lambda s: s["t0"])
    for aid, h in starts.items():
        inside = [t for t in launchers if t["t0"] <= h["t0"] and (t.get("t1") is None or h["t0"] <= t["t1"])]
        before = [t for t in launchers if t["t0"] <= h["t0"]]
        tool = (min(inside, key=lambda t: (t.get("t1") or h["t0"]) - t["t0"]) if inside else
                (before[-1] if before else None))
        if tool is not None and tool["id"] != h.get("parent"):
            h["parent"] = tool["id"]
            acc.link(tool["id"], h["id"], "triggers", "spawned a subagent")
    facts = {f.get("agent_id"): f for f in acc.facts.get("subagents") or [] if isinstance(f, dict)}
    for aid, f in facts.items():
        h = starts.get(aid)
        if h is not None:
            a = h.setdefault("attrs", {})
            for k in ("agent_type", "description"):
                if f.get(k) and not a.get(k):
                    a[k] = f[k]
    # subagent llm (gateway rows) and tool spans
    by_agent_llm: dict[str, list[dict]] = {}
    by_agent_tool: dict[str, list[dict]] = {}
    for s in spans.values():
        a = s.get("attrs") or {}
        aid = a.get("agent_id")
        if not aid or s.get("kind") not in ("llm", "tool"):
            continue
        (by_agent_llm if s["kind"] == "llm" else by_agent_tool).setdefault(aid, []).append(s)
    orphans = 0
    for aid in set(by_agent_llm) | set(by_agent_tool):
        h = starts.get(aid)
        llms = sorted(by_agent_llm.get(aid, []), key=lambda s: (s.get("t0") or 0.0, s["id"]))
        tools = sorted(by_agent_tool.get(aid, []), key=lambda s: (s.get("t0") or 0.0, s["id"]))
        by_n = {(x.get("attrs") or {}).get("transcript_llm"): x for x in llms if (x.get("attrs") or {}).get("transcript_llm")}
        for s in llms + tools:
            if h is not None and (not s.get("parent") or s.get("parent") == M.Ids.TURN):
                s["parent"] = h["id"]
            elif h is None:
                orphans += 1
        if h is not None and llms:
            acc.link(h["id"], llms[0]["id"], "triggers", "subagent's first model call")
        for t in tools:
            issuer = by_n.get((t.get("attrs") or {}).get("llm")) or _last_llm_before(llms, t["t0"])
            pres = [x for x in spans.values() if x.get("kind") == "hook" and x.get("parent") == t["id"]
                    and _hook_native(x) in PRE_TOOL_HOOKS]
            src = issuer["id"] if issuer is not None else (h["id"] if h is not None else None)
            if src:
                if pres:
                    for x in pres:
                        acc.link(src, x["id"], "triggers", "tool_use")
                else:
                    acc.link(src, t["id"], "calls", "tool_use")
            end = t.get("t1") if t.get("t1") is not None else t["t0"]
            nxt = _first_llm_after([x for x in llms if x is not issuer], end, tol=0.0)
            if nxt is not None:
                acc.link(t["id"], nxt["id"], "feeds", "tool_result")
    # SubagentStop: the receipt carries no agent id; match the agent whose sidechain ends closest before it
    for h in hooks:
        if _hook_native(h) not in SUBAGENT_STOP:
            continue
        best, best_d = None, None
        for aid, f in facts.items():
            last = _num(f.get("last"))
            if last is None or aid not in starts:
                continue
            d = h["t0"] - last
            if -2000.0 <= d <= 10000.0 and (best_d is None or abs(d) < abs(best_d)):
                best, best_d = aid, d
        if best is None:
            if not h.get("parent") and M.Ids.TURN in spans:
                h["parent"] = M.Ids.TURN
            acc.gap("ext:claude-code", f"SubagentStop at {M.iso(h['t0'])} matches no subagent of this turn",
                    "no sidechain transcript of this turn ends near it: a subagent the transcript does not record "
                    "(Claude Code's own post-turn helpers), or one started before the window", "info", h["id"])
            continue
        st = starts[best]
        h.setdefault("attrs", {}).setdefault("agent_id", best)
        h["attrs"]["agent_matched_by"] = "sidechain end time"
        if not h.get("parent"):
            h["parent"] = st["id"]
        tail = (sorted(by_agent_llm.get(best, []), key=lambda s: s.get("t1") or s.get("t0") or 0.0) or [st])[-1]
        acc.link(tail["id"], h["id"], "triggers", "subagent finished")
    return orphans


def _session_edges(acc: _Acc, window: M.TurnWindow) -> None:
    """SessionEnd inside the window follows the turn's Stop (headless -p / exec exit after one turn)."""
    hooks = sorted([s for s in acc.spans.values() if s.get("kind") == "hook" and s.get("t0") is not None],
                   key=lambda s: s["t0"])
    stops = [h for h in hooks if _hook_native(h) in STOP_HOOKS]
    for h in hooks:
        if _hook_native(h) != "SessionEnd":
            continue
        prev = [x for x in stops if x["t0"] <= h["t0"]]
        if prev:
            acc.link(prev[-1]["id"], h["id"], "triggers", "session ended after the turn")
    # the nanoleaf handler repaints the pane; its redis signal lands inside or just after the handler's run
    painters = [s for s in acc.spans.values() if s.get("kind") == "handler" and s.get("name") == "nanoleaf"
                and s.get("t0") is not None]
    for n in acc.spans.values():
        if n.get("kind") != "notify" or n.get("component") != "ext:nanoleaf" or n.get("t0") is None:
            continue
        fit = [p for p in painters if p["t0"] - 100 <= n["t0"] <= (p.get("t1") or p["t0"]) + 400]
        if fit:
            best = min(fit, key=lambda p: abs(n["t0"] - (p.get("t1") or p["t0"])))
            acc.link(best["id"], n["id"], "triggers", "repainted the pane")
    # hook-hub mirrors each receipt as agent.hook.updated: the hook is that event's publisher
    for ln in acc.links:
        if ln.get("kind") == "mirrors" and ln["to"].startswith("evt:"):
            ev = acc.events.get(ln["to"][4:])
            if ev is not None and not ev.get("publisher_span") and ln["from"] in acc.spans:
                ev["publisher_span"] = ln["from"]
                if not ev.get("producer"):
                    ev["producer"] = acc.spans[ln["from"]].get("component")
    # the enricher's session rollup (on session.ended) is what emits report.session.completed
    rollups = [s for s in acc.spans.values() if s.get("kind") == "consume" and s.get("component") == "enricher"
               and _short_type((s.get("attrs") or {}).get("event_type") or s.get("name")).endswith("session.ended")]
    for ev in acc.events.values():
        if ev.get("publisher_span") or not str(ev.get("type") or "").endswith("report.session.completed"):
            continue
        if rollups and (ev.get("producer") in (None, "enricher")):
            r = rollups[-1]
            acc.link(r["id"], M.Ids.evt(ev["id"]), "publishes", "session rollup report")
            ev["publisher_span"] = r["id"]


# ---- normalisation ------------------------------------------------------------------------

def _infer_phase(s: dict, turn_end: float | None) -> str:
    kind = s.get("kind")
    nat = _hook_native(s) if kind == "hook" else None
    if kind == "llm":
        return "model_call"
    if kind == "tool":
        return "tool"
    if nat in PRE_TOOL_HOOKS:
        return "pre_tool"
    if nat in ("PostToolUse", "PostToolUseFailure"):
        return "post_tool"
    if nat in STOP_HOOKS:
        return "turn_end"
    if nat == "SessionStart":
        return "session_start"
    if nat == "SessionEnd":
        return "session_end"
    t0 = s.get("t0")
    if turn_end is not None and t0 is not None and t0 > turn_end:
        return "async_after"
    return "prompt_submit"


def _default_summary(s: dict) -> str:
    kind, name, comp = s.get("kind") or "span", s.get("name") or s["id"], s.get("component") or "?"
    st = s.get("status") or "ok"
    reason = f" ({s['reason']})" if s.get("reason") else ""
    if st == "ok":
        return f"{comp} {kind} {name}"
    return f"{comp} {kind} {name}: {st}{reason}"


def _rel(v: Any, t0: float) -> float | None:
    x = _num(v)
    if x is None:
        return None
    if abs(x) < 1e11:          # already relative (or garbage near the epoch): leave as is
        return round(x, 3)
    return round(x - t0, 3)


# ---- profiles -------------------------------------------------------------------------------

def _cut(s: str, limit: int) -> tuple[str, bool]:
    if len(s) <= limit:
        return s, False
    return s[:limit] + "…", True


def _cut_leaves(obj: Any, limit: int) -> tuple[Any, bool]:
    if isinstance(obj, str):
        return _cut(obj, limit)
    if isinstance(obj, list):
        out, any_cut = [], False
        for x in obj:
            y, c = _cut_leaves(x, limit)
            out.append(y)
            any_cut = any_cut or c
        return out, any_cut
    if isinstance(obj, dict):
        out_d, any_cut = {}, False
        for k, v in obj.items():
            y, c = _cut_leaves(v, limit)
            out_d[k] = y
            any_cut = any_cut or c
        return out_d, any_cut
    return obj, False


_HOME_ESC = M.HOME.replace("/", "\\/")


def _tilde_str(s: str) -> str:
    if M.HOME and M.HOME in s:
        s = s.replace(M.HOME, "~")
    if _HOME_ESC and _HOME_ESC in s:
        s = s.replace(_HOME_ESC, "~")
    return s


def _public_walk(obj: Any) -> Any:
    if isinstance(obj, str):
        return _tilde_str(obj)
    if isinstance(obj, list):
        return [_public_walk(x) for x in obj]
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in ENV_KEYS and v not in (None, "", [], {}):
                out[k] = {kk: DROPPED for kk in v} if isinstance(v, dict) else DROPPED
            else:
                out[k] = _public_walk(v)
        return out
    return obj


def apply_profile(wb: dict, profile: str) -> dict:
    """Apply a SPEC section 2 profile to a finished waybill dict, then scrub. Idempotent."""
    if profile == "public":
        keep = {s.get("payload") for s in wb.get("spans", []) if s.get("kind") == "prompt" and s.get("payload")}
        for aid, art in list((wb.get("artifacts") or {}).items()):
            if aid in keep or not isinstance(art, dict):
                continue
            cut = False
            if isinstance(art.get("text"), str):
                art["text"], c = _cut(art["text"], PUBLIC_TEXT_LIMIT)
                cut = cut or c
            if "json" in art:
                art["json"], c = _cut_leaves(art["json"], PUBLIC_TEXT_LIMIT)
                cut = cut or c
            if cut:
                art["truncated"] = True
                art.setdefault("note", "cut to 280 chars per string for the public profile")
        for s in wb.get("spans", []):
            if isinstance(s.get("attrs"), dict):
                s["attrs"], _ = _cut_leaves(s["attrs"], PUBLIC_TEXT_LIMIT)
        wb = _public_walk(wb)
        wb.setdefault("recorder", {})["profile"] = "public"
    return M.scrub_obj(wb)


# ---- size budget (opt-in, public samples) ---------------------------------------------------------

def _size(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))


def _shallow(v: Any) -> Any:
    if isinstance(v, dict):
        return f"{{…{len(v)} keys}}"
    if isinstance(v, list):
        return f"[…{len(v)} items]"
    return v


def _drop_spans(wb: dict, ids: set[str]) -> None:
    """Remove spans (and everything parented under them), the links touching them, and dangling references."""
    spans = wb.get("spans", [])
    kids: dict[str, list[str]] = {}
    for s in spans:
        if s.get("parent"):
            kids.setdefault(s["parent"], []).append(s["id"])
    gone: set[str] = set()
    todo = list(ids)
    while todo:
        i = todo.pop()
        if i not in gone:
            gone.add(i)
            todo.extend(kids.get(i, []))
    wb["spans"] = [s for s in spans if s["id"] not in gone]
    wb["links"] = [ln for ln in wb.get("links", []) if ln["from"] not in gone and ln["to"] not in gone]
    for ev in wb.get("events", []):
        if ev.get("publisher_span") in gone:
            ev.pop("publisher_span")
        for c in ev.get("consumers") or []:
            if c.get("span") in gone:
                c.pop("span")


def thin_to_budget(wb: dict, max_bytes: int) -> dict:
    """Shrink a (public) waybill until its compact JSON fits max_bytes, cheapest loss first, and say what went.
    Every step keeps the span tree, the links between kept spans, the events and their observed consumers."""
    notes: list[str] = []
    if _size(wb) <= max_bytes:
        return wb
    # 1. raw envelopes and receipts: the events/spans already carry the facts; keep attributes + a shallow data
    arts = wb.get("artifacts") or {}
    keep = {s.get("payload") for s in wb.get("spans", []) if s.get("kind") in ("prompt", "tool", "memory", "context")
            and s.get("payload")}
    n = 0
    for aid, art in list(arts.items()):
        j = art.get("json") if isinstance(art, dict) else None
        if aid in keep or not isinstance(j, dict):
            continue
        if "specversion" in j and isinstance(j.get("data"), dict):
            j = {k: v for k, v in j.items() if k not in ("data", "traceparent", "dataschema")}
            j["data"] = {k: _shallow(v) for k, v in art["json"]["data"].items()}
        elif "invocation" in j and "timeline" in j:
            j = {"invocation": j["invocation"]}
        else:
            continue
        art["json"] = j
        art["truncated"] = True
        art["note"] = "envelope/receipt reduced to its attributes for the sample size budget"
        n += 1
    if n:
        notes.append(f"{n} raw envelope/receipt artifacts reduced to their attributes")
    # 2. inferred consumers (a guess from subscription tables) are the bulk of every event's consumer list
    if _size(wb) > max_bytes:
        dropped = 0
        for ev in wb.get("events", []):
            cs = ev.get("consumers")
            if isinstance(cs, list):
                kept = [c for c in cs if c.get("kind") != "inferred" and c.get("outcome") != "unknown"]
                dropped += len(cs) - len(kept)
                ev["consumers"] = kept
        if dropped:
            notes.append(f"{dropped} inferred consumer rows dropped (observed ones kept)")
    # 3. skipped handlers: fold into their hook's attrs.skipped_handlers
    if _size(wb) > max_bytes:
        spans = wb.get("spans", [])
        has_child = {s.get("parent") for s in spans if s.get("parent")}
        extra_links = {x for ln in wb.get("links", []) if ln.get("kind") != "runs" for x in (ln["from"], ln["to"])}
        fold = {s["id"]: s for s in spans if s.get("kind") == "handler" and s.get("status") == "skipped"
                and s["id"] not in has_child and s["id"] not in extra_links and s.get("parent")}
        by_hook: dict[str, list[str]] = {}
        for s in fold.values():
            by_hook.setdefault(s["parent"], []).append(f"{s.get('name')}" + (f" [{s['reason']}]" if s.get("reason") else ""))
        for s in spans:
            if s["id"] in by_hook:
                s.setdefault("attrs", {})["skipped_handlers"] = by_hook[s["id"]]
        wb["spans"] = [s for s in spans if s["id"] not in fold]
        wb["links"] = [ln for ln in wb.get("links", []) if ln["from"] not in fold and ln["to"] not in fold]
        if fold:
            notes.append(f"{len(fold)} skipped-handler spans folded into their hook's attrs.skipped_handlers")
    # 4. span attrs that restate t0/t1 and the receipt ids
    if _size(wb) > max_bytes:
        for s in wb.get("spans", []):
            a = s.get("attrs")
            if isinstance(a, dict):
                for k in ("selected_at", "started_at", "finished_at", "receipt_status", "order"):
                    a.pop(k, None)
        notes.append("redundant span timing attrs (selected_at/started_at/finished_at) dropped")
    # 5. artifacts nothing important points at (raw envelopes, receipts): drop them and the span pointers
    if _size(wb) > max_bytes:
        keepa = {s.get("payload") for s in wb.get("spans", []) if s.get("kind") in ("prompt", "tool", "memory", "context")
                 and s.get("payload")}
        for s in wb.get("spans", []):
            if s.get("payload") and s["payload"] not in keepa:
                s.pop("payload")
        wb["artifacts"] = {k: v for k, v in (wb.get("artifacts") or {}).items() if k in keepa}
        notes.append("raw envelope and receipt artifacts dropped (only prompt, tool, memory and context payloads kept)")
    # 6. the hook-hub mirror (agent.hook.updated): one event, publish span and archive span per receipt
    if _size(wb) > max_bytes:
        mirror = {ev["id"] for ev in wb.get("events", []) if str(ev.get("type") or "").endswith("agent.hook.updated")}
        if mirror:
            ids = {f"publish:{e}" for e in mirror}
            ids |= {s["id"] for s in wb.get("spans", [])
                    if (s.get("refs") or {}).get("event_id") in mirror and s.get("kind") in ("publish", "consume", "notify")}
            _drop_spans(wb, ids)
            wb["events"] = [ev for ev in wb["events"] if ev["id"] not in mirror]
            wb["links"] = [ln for ln in wb["links"] if not (ln["to"].startswith("evt:") and ln["to"][4:] in mirror)
                           and not (ln["from"].startswith("evt:") and ln["from"][4:] in mirror)]
            notes.append(f"{len(mirror)} agent.hook.updated mirror events (and their publish/archive spans) dropped")
    # 7. leaf handlers that did nothing the tree needs (no children, no links but the hook's own): fold the rest
    if _size(wb) > max_bytes:
        spans = wb.get("spans", [])
        has_child = {s.get("parent") for s in spans if s.get("parent")}
        extra_links = {x for ln in wb.get("links", []) if ln.get("kind") != "runs" for x in (ln["from"], ln["to"])}
        fold = {s["id"]: s for s in spans if s.get("kind") == "handler" and s["id"] not in has_child
                and s["id"] not in extra_links and s.get("parent")}
        by_hook = {}
        for s in fold.values():
            by_hook.setdefault(s["parent"], []).append(f"{s.get('name')}:{s.get('status')}")
        for s in spans:
            if s["id"] in by_hook:
                s.setdefault("attrs", {}).setdefault("folded_handlers", by_hook[s["id"]])
        _drop_spans(wb, set(fold))
        if fold:
            notes.append(f"{len(fold)} leaf handler spans folded into their hook's attrs.folded_handlers")
    # 9. archive spans nothing hangs off: the event's observed consumer row already says candystore archived it
    if _size(wb) > max_bytes:
        parents = {s.get("parent") for s in wb.get("spans", []) if s.get("parent")}
        linked = {x for ln in wb.get("links", []) if ln.get("kind") not in ("delivers",) for x in (ln["from"], ln["to"])}
        cs = {s["id"] for s in wb.get("spans", []) if s.get("kind") == "consume" and s.get("component") == "candystore"
              and s["id"] not in parents and s["id"] not in linked}
        _drop_spans(wb, cs)
        if cs:
            notes.append(f"{len(cs)} candystore archive spans dropped (the event's consumer row keeps the outcome)")
    # 8. ntfy digest notices
    if _size(wb) > max_bytes:
        nt = {s["id"] for s in wb.get("spans", []) if s.get("kind") == "notify"}
        _drop_spans(wb, nt)
        if nt:
            notes.append(f"{len(nt)} notify spans dropped")
    st = wb.get("stats")
    if isinstance(st, dict):          # the structural counts describe the file; turn totals (handlers, tokens) stay
        for k in [k for k in st if k.startswith("spans_")]:
            st[k] = 0
        for sp in wb.get("spans", []):
            st[f"spans_{sp['kind']}"] = st.get(f"spans_{sp['kind']}", 0) + 1
        st["spans"], st["events"] = len(wb.get("spans", [])), len(wb.get("events", []))
        st["links"], st["artifacts"] = len(wb.get("links", [])), len(wb.get("artifacts") or {})
    wb.setdefault("gaps", []).append({
        "component": "waybill", "severity": "info",
        "what": f"sample thinned to fit {max_bytes // 1024} KiB",
        "why": "; ".join(notes) + f". Final size {_size(wb) // 1024} KiB compact."})
    return wb


# ---- main entry -------------------------------------------------------------------------------

def _git_project(cwd: str | None) -> str | None:
    if not cwd:
        return None
    try:
        p = Path(cwd)
        for d in [p, *p.parents]:
            if (d / ".git").exists():
                return d.name
    except OSError:
        return None
    return None


def assemble(window: M.TurnWindow, fragments: list, profile: str = "full", mode: str = "capture",
             argv: list[str] | None = None) -> dict:
    acc = _Acc()
    for frag in fragments or []:
        try:
            acc.add_fragment(frag)
        except Exception as exc:  # a malformed fragment must not sink the waybill
            sid = getattr(getattr(frag, "source", None), "id", "?")
            acc.gap("unknown", f"fragment from {sid} could not be merged", f"{type(exc).__name__}: {exc}", "warn")
    t0 = float(window.t0)
    facts = acc.facts
    cli = window.cli or facts.get("cli") or "unknown"
    surface = window.surface or facts.get("surface") or cli
    cli_comp = SURFACE_COMPONENT.get(surface) or (f"ext:{surface}" if surface else "ext:unknown")
    turn_end = window.turn_end
    prompt_text = window.prompt_text if window.prompt_text is not None else facts.get("prompt_text")

    # root spans the player needs even when no collector produced them
    if M.Ids.PROMPT not in acc.spans:
        ups = next((s for s in acc.spans.values() if s.get("kind") == "hook" and _hook_native(s) in PROMPT_HOOKS), None)
        acc.add_span({
            "id": M.Ids.PROMPT, "kind": "prompt", "component": cli_comp, "name": "prompt",
            "summary": f"The operator submitted a {len(prompt_text or '')}-char prompt in {surface}.",
            "phase": "prompt_submit", "t0": t0, "t1": (ups or {}).get("t1"), "status": "ok", "sync": True,
            "parent": None, "refs": {"invocation_id": window.prompt_invocation_id} if window.prompt_invocation_id else {},
            "attrs": {"derived": "window"}, "evidence": [],
        })
    if M.Ids.TURN not in acc.spans:
        stopped = turn_end is not None
        acc.add_span({
            "id": M.Ids.TURN, "kind": "turn", "component": cli_comp, "name": "turn",
            "summary": (f"The turn ran {fmt_duration(turn_end - t0)} from submit to Stop." if stopped
                        else "The turn had not reached Stop when the window closed."),
            "phase": "prompt_submit", "t0": t0, "t1": turn_end, "status": "ok" if stopped else "pending",
            "sync": None, "parent": None,
            "refs": {"invocation_id": window.stop_invocation_id} if window.stop_invocation_id else {},
            "attrs": {"derived": "window"}, "evidence": [],
        })

    _resolve_match_llm(acc)
    _resolve_joins(acc)
    _publish_chain(acc)
    _infer_consumers(acc)
    _settle_consumers(acc)
    unparented_tool_hooks = _tool_hooks(acc)
    orphan_subagent = _subagents(acc)
    _session_edges(acc, window)
    _default_parents_and_links(acc)

    # apply id aliases everywhere
    if acc.alias:
        new_links, keys = [], set()
        for ln in acc.links:
            f, t = acc.resolve(ln["from"]), acc.resolve(ln["to"])
            if f == t or (f, t, ln["kind"]) in keys:
                continue
            keys.add((f, t, ln["kind"]))
            new_links.append({**ln, "from": f, "to": t})
        acc.links = new_links
        for s in acc.spans.values():
            if s.get("parent"):
                s["parent"] = acc.resolve(s["parent"])
        for ev in acc.events.values():
            if ev.get("publisher_span"):
                ev["publisher_span"] = acc.resolve(ev["publisher_span"])
            for c in ev.get("consumers") or []:
                if c.get("span"):
                    c["span"] = acc.resolve(c["span"])

    # components referenced anywhere
    def need(cid: str | None) -> None:
        if cid and cid not in acc.components:
            acc.components[cid] = component_record(cid)
    for s in acc.spans.values():
        if not s.get("component"):
            s["component"] = cli_comp if s.get("kind") in ("prompt", "turn", "tool") else "unknown"
        need(s["component"])
    for ev in acc.events.values():
        for c in ev.get("consumers") or []:
            if not c.get("component"):
                c["component"] = consumer_component(c.get("name"))
            need(c["component"])
    for cid, comp in list(acc.components.items()):
        base = component_record(cid)
        comp["id"] = cid
        comp["name"] = comp.get("name") or base["name"]
        if not comp.get("kind") or (comp.get("kind") == "service" and base["kind"] != "service"):
            comp["kind"] = base["kind"]
        comp["registry"] = M.registry_has(cid)

    # ---- rebase to clock.t0 and normalise required fields
    spans_out: list[dict] = []
    for s in acc.spans.values():
        s["t0"] = _rel(s.get("t0"), t0)
        s["t1"] = _rel(s.get("t1"), t0)
        if s["t0"] is None:
            s["t0"] = s["t1"] if s["t1"] is not None else 0.0
            s.setdefault("attrs", {})["t0_unknown"] = True
        if s["t1"] is not None and s["t1"] < s["t0"]:
            s["t1"] = s["t0"]
        for c_k in ("refs", "attrs"):
            if not isinstance(s.get(c_k), dict):
                s[c_k] = {}
        if not isinstance(s.get("evidence"), list):
            s["evidence"] = []
        s["kind"] = s.get("kind") or "span"
        s["name"] = s.get("name") or s["id"]
        if s.get("status") not in STATUSES:
            s["attrs"].setdefault("raw_status", s.get("status"))
            s["status"] = "unknown"
        if not s.get("summary"):
            s["summary"] = _default_summary(s)
        for opt in ("sync", "payload"):          # optional in the SPEC: absent, never null
            if s.get(opt) is None:
                s.pop(opt, None)
        if s.get("sync") is not None:
            s["sync"] = bool(s["sync"])
        spans_out.append(s)
    turn_end_rel = _rel(turn_end, t0) if turn_end is not None else None
    for s in spans_out:
        if s.get("phase") not in PHASES:
            if s.get("phase"):
                s["attrs"].setdefault("raw_phase", s["phase"])
            s["phase"] = _infer_phase(s, turn_end_rel)
    events_out: list[dict] = []
    for ev in acc.events.values():
        ev["t"] = _rel(ev.get("t"), t0)
        if ev["t"] is None:
            ps = acc.spans.get(ev.get("publisher_span") or "")
            ev["t"] = (ps or {}).get("t1") if (ps or {}).get("t1") is not None else (ps or {}).get("t0", 0.0)
        ev["stored"] = _rel(ev.get("stored"), t0)
        ev["archived"] = _rel(ev.get("archived"), t0)
        for c in ev.get("consumers") or []:
            c["t"] = _rel(c.get("t"), t0)
        for k in ("subject", "stream", "seq", "correlationid", "causationid", "producer", "publisher_span"):
            ev.setdefault(k, None)
        ev["type"] = ev.get("type") or "unknown"
        if isinstance(ev.get("seq"), float) and ev["seq"].is_integer():
            ev["seq"] = int(ev["seq"])
        elif ev.get("seq") is not None and not isinstance(ev["seq"], int):
            try:
                ev["seq"] = int(ev["seq"])
            except (TypeError, ValueError):
                ev["seq"] = None
        for opt in ("payload", "schema"):
            if ev.get(opt) is None:
                ev.pop(opt, None)
        events_out.append(ev)

    # ---- drop dangling references
    known = {s["id"] for s in spans_out} | {M.Ids.evt(e["id"]) for e in events_out}
    comp_of = {s["id"]: s.get("component") for s in spans_out}
    comp_of.update({M.Ids.evt(e["id"]): e.get("producer") for e in events_out})
    links_out, missing = [], {}
    for ln in acc.links:
        kind = ln.get("kind")
        if kind not in LINK_KINDS:
            ln = {**ln, "kind": "causes", "label": ln.get("label") or str(kind)}
        if not ln.get("label"):
            ln = {k: v for k, v in ln.items() if k != "label"}
        if ln["from"] in known and ln["to"] in known:
            links_out.append(ln)
        else:
            gone = ln["to"] if ln["from"] in known else ln["from"]
            other = ln["from"] if gone == ln["to"] else ln["to"]
            m = missing.setdefault(gone, {"n": 0, "comp": comp_of.get(other)})
            m["n"] += 1
    for node, m in missing.items():
        acc.gap(m["comp"] or "unknown", f"{node} was referenced but no collector observed it",
                f"{m['n']} link(s) dropped because one end is missing from the waybill", "info")
    for s in spans_out:
        if s.get("parent") and s["parent"] not in known:
            s["attrs"].setdefault("unresolved_parent", s["parent"])
            s["parent"] = None
    span_ids = {s["id"] for s in spans_out}
    for ev in events_out:
        if ev.get("publisher_span") and ev["publisher_span"] not in span_ids:
            ev["publisher_span"] = None
        for c in ev.get("consumers") or []:
            if c.get("span") and c["span"] not in span_ids:
                c["span"] = None

    # ---- derived gaps and findings
    bus_events = [e for e in events_out if (e.get("subject") or "").startswith("bloodbank.evt.")
                  or e.get("stream")]
    any_seq = any(e.get("seq") is not None for e in events_out)
    any_archived = any(e.get("archived") is not None for e in events_out)
    published = [e for e in bus_events if e.get("publisher_span")]
    never_stored = set()

    def per_type_gaps(rows: list[dict], component: str, what: str, what_many: str, why: str) -> None:
        by_t: dict[str, list[dict]] = {}
        for e in rows:
            by_t.setdefault(_short_type(e["type"]), []).append(e)
        for et, evs in by_t.items():
            if len(evs) <= 2:
                for e in evs:
                    acc.gap(component, f"{et} {e['id']} {what}", why, "warn", e.get("publisher_span"))
            else:
                ids = ", ".join(e["id"] for e in evs[:3])
                acc.gap(component, f"{len(evs)} {et} events {what_many}", f"{why} (first: {ids}…)", "warn",
                        evs[0].get("publisher_span"))

    if any_seq:
        rows = [e for e in published if e.get("seq") is None]
        never_stored.update(e["id"] for e in rows)
        per_type_gaps(rows, "bb-nats", "published (PONG) but never seen stored",
                      "published (PONG) but never seen stored",
                      "the publisher got a core-NATS PONG, but no JetStream sequence was found for the id")
    elif published:
        acc.gap("bb-nats", "JetStream sequence unknown for every event",
                "no collector resolved a stream seq (holocene/nats unavailable), so 'stored' cannot be checked",
                "info")
    if any_archived:
        rows = [e for e in bus_events if e["id"] not in never_stored and e.get("archived") is None
                and not any(c.get("component") == "candystore" and c.get("evidence") == "observed"
                            and c.get("outcome") in ("archived", "dropped") for c in e.get("consumers") or [])]
        per_type_gaps(rows, "candystore", "has no observed archive", "have no observed archive",
                      "Candystore holds no row for this event id (not ingested, dropped, or still in flight)")
    elif bus_events:
        acc.gap("candystore", "archive state unknown for every event",
                "no collector reported a Candystore received_at", "info")
    stop_seen = window.stop_invocation_id or turn_end is not None or any(
        s.get("kind") == "hook" and _hook_native(s) in STOP_HOOKS for s in spans_out)
    if not stop_seen:
        acc.gap(cli_comp, "turn still open",
                "no Stop hook invocation was seen for this turn before the window closed", "warn", M.Ids.TURN)
    tps = []
    for e in events_out:
        env = _payload_json(acc, e.get("payload"))
        if isinstance(env, dict):
            tps.append(env.get("traceparent"))
    if tps and not any(isinstance(tp, str) and tp.replace("-", "").strip("0") for tp in tps):
        acc.finding("info", "no distributed trace id: traceparent is all zeros on every event; "
                    "the waybill reconstructs causation itself",
                    f"{len(tps)} envelope(s) inspected; none carries a real W3C traceparent "
                    "(placeholder 00-000…-000…-00 or absent).", "agent-hooks",
                    [M.Ids.evt(e["id"]) for e in events_out[:5]])
    failed_handlers: dict[tuple, list[str]] = {}
    for s in spans_out:
        if s.get("kind") == "handler" and s.get("status") in ("failed", "timeout"):
            hid = (s.get("attrs") or {}).get("handler_id") or s["id"].split(":")[-1]
            failed_handlers.setdefault((hid, s["status"], s.get("reason") or ""), []).append(s["id"])
    covered = {x for f in acc.findings for x in f.get("evidence") or []}
    for (hid, st, reason), ids in failed_handlers.items():
        if covered.intersection(ids):
            continue
        sev = "broken" if reason in ("handler_binary_missing", "broken_symlink") else "warn"
        acc.finding(sev, f"{hid} {st}" + (f": {reason}" if reason else ""),
                    f"hook-hub reported {hid} as {st} in {len(ids)} invocation(s) of this turn.",
                    "hook-hub", ids)
    if orphan_subagent:
        acc.gap("ext:claude-code", f"{orphan_subagent} subagent span(s) could not be tied to a SubagentStart hook",
                "no SubagentStart receipt whose invocation.started event names the agent id (receipts aged out, or the "
                "subagent started before the window)", "info")
    if unparented_tool_hooks:
        acc.gap("hook-hub", f"{unparented_tool_hooks} tool hook(s) could not be tied to a tool call",
                "no publisher event with data.tool_call_id (or no matching tool span) was found", "info")

    # ---- normalise gaps / findings / sources
    for g in acc.gaps:
        g["severity"] = g.get("severity") if g.get("severity") in SEVERITIES else "info"
        g.setdefault("span", None)
        for k in ("component", "what", "why"):
            g[k] = str(g.get(k) or "")
    for f in acc.findings:
        f["severity"] = f.get("severity") if f.get("severity") in SEVERITIES else "info"
        f["evidence"] = list(f.get("evidence") or [])
        for k in ("title", "detail", "component"):
            f[k] = str(f.get(k) or "")
    for src in acc.sources:
        src["status"] = src.get("status") if src.get("status") in SOURCE_STATUSES else "error"
        src["items"] = int(src.get("items") or 0)
        src["ms"] = round(float(src.get("ms") or 0.0), 1)
        src["locator"] = str(src.get("locator") or "")
        src.setdefault("error", None)

    spans_out.sort(key=lambda s: (s["t0"], s["id"]))
    events_out.sort(key=lambda e: (e["t"] if e["t"] is not None else 0.0, e["id"]))

    # ---- stats
    stats: dict[str, float] = {"spans": len(spans_out), "events": len(events_out), "links": len(links_out),
                               "artifacts": len(acc.artifacts), "gaps": len(acc.gaps), "findings": len(acc.findings)}
    for s in spans_out:
        stats[f"spans_{s['kind']}"] = stats.get(f"spans_{s['kind']}", 0) + 1
    llm_spans = [s for s in spans_out if s["kind"] == "llm"]
    stats["tools"] = sum(1 for s in spans_out if s["kind"] == "tool")
    stats["llm_calls"] = len(llm_spans)
    tin = tout = traw = 0
    for s in llm_spans:
        a, b, c = llm_tokens(s)
        tin, traw, tout = tin + a, traw + b, tout + c
    stats["tokens_in"], stats["tokens_in_uncached"], stats["tokens_out"] = tin, traw, tout
    ups = next((s for s in spans_out if s["kind"] == "hook" and _hook_native(s) in PROMPT_HOOKS), None)
    if ups is not None and ups.get("t1") is not None:
        stats["sync_wait_ms"] = round(ups["t1"] - ups["t0"], 1)
    handlers = [s for s in spans_out if s["kind"] == "handler"]
    stats["handlers"] = len(handlers)
    stats["handlers_ok"] = sum(1 for s in handlers if s["status"] == "ok")
    stats["handlers_skipped"] = sum(1 for s in handlers if s["status"] == "skipped")
    stats["handlers_failed"] = sum(1 for s in handlers if s["status"] in ("failed", "timeout"))
    cons = [c for e in events_out for c in e.get("consumers") or []]
    stats["consumers_observed"] = sum(1 for c in cons if c.get("evidence") == "observed")
    stats["consumers_inferred"] = sum(1 for c in cons if c.get("evidence") != "observed")
    stats["hooks"] = sum(1 for s in spans_out if s["kind"] == "hook")

    # ---- origin / prompt / clock / identity
    turn_id = window.turn_id or facts.get("turn_id")
    turn_index = window.turn_index if window.turn_index is not None else facts.get("turn_index")
    cwd = window.cwd or facts.get("cwd")
    req, served = facts.get("model_requested"), facts.get("model_served")
    if not served:
        for s in llm_spans:
            a = s.get("attrs") or {}
            served = a.get("model_served") or a.get("served_model") or a.get("model")
            req = req or a.get("model_requested") or a.get("requested_model")
            if served:
                break
    origin = {
        "cli": cli, "surface": surface, "session_id": window.session_id, "turn_id": turn_id,
        "turn_index": turn_index, "cwd": cwd, "project": facts.get("project") or _git_project(cwd),
        "model": {"requested": req, "served": served} if (req or served) else None,
    }
    full_text = prompt_text
    ptxt, ptrunc = (None, False)
    if full_text is not None:
        ptxt, ptrunc = _cut(full_text, FULL_TEXT_LIMIT)
    prompt = {"text": ptxt, "chars": len(full_text or ""), "sha256": M.sha256(full_text or ""), "truncated": ptrunc}
    t_end = float(window.t_end) if window.t_end else (turn_end or t0)
    dur = (turn_end - t0) if turn_end is not None else max(0.0, t_end - t0 - float(window.settle_ms or 0))
    clock = {"t0": M.iso(t0), "t_end": M.iso(t_end), "duration_ms": round(dur, 1),
             "settle_ms": float(window.settle_ms or 0), "turn_end_ms": turn_end_rel}
    turn_key = turn_id or (str(turn_index) if turn_index is not None else str(int(t0)))
    wid = waybill_id(t0, window.session_id or "", turn_key)
    first = re.sub(r"\s+", " ", (full_text or "").strip())
    snippet = first[:60] + ("…" if len(first) > 60 else "")
    title = f'{surface} · "{snippet}" · {fmt_duration(dur)}'

    wb = {
        "format": FORMAT, "version": SCHEMA_VERSION, "id": wid, "title": title,
        "recorded_at": _iso_now(),
        "recorder": {"name": "waybill", "version": VERSION, "host": socket.gethostname(), "mode": mode,
                     "profile": profile if profile in ("full", "public") else "full",
                     "argv": list(argv) if argv is not None else None},
        "origin": origin, "prompt": prompt, "clock": clock,
        "components": dict(sorted(acc.components.items())),
        "spans": spans_out, "events": events_out, "links": links_out,
        "artifacts": acc.artifacts, "gaps": acc.gaps, "findings": acc.findings,
        "sources": acc.sources, "stats": stats,
    }
    if wb["recorder"]["argv"] is None:
        del wb["recorder"]["argv"]
    return apply_profile(wb, wb["recorder"]["profile"])
