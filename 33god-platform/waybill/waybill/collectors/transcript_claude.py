"""Claude Code transcript collector (source 'transcript').

Slices `~/.claude/projects/*/<sid>.jsonl` from the typed user entry to the turn_duration entry and emits:
prompt, context (merged + split by hook-hub handler marker), llm (deduped by requestRef / message.id),
tool (tool_use -> tool_result), turn. Subagent sidechains contribute their tool calls (attrs.subagent, agent_id);
the assembler hangs them under the SubagentStart hook. Their model calls stay gateway rows.

The file is streamed from the prompt's byte offset; `api-request-blob` / `api-request-shape` lines (huge)
are skipped without being parsed.

Read-only. Stdlib only. Shared helpers (`split_context`, `fmt_tokens`, `Calls`, `transcript_llm_calls`) are
imported by the Codex and gateway collectors.
"""
from __future__ import annotations

import glob
import copy
import json
import os
import re
import sqlite3
import threading
import time
from typing import Any

from ..model import Ctx, Fragment, Gap, Ids, Link, Source, Span, TurnWindow, iso, ms, scrub, tilde
from .. import window as W

SOURCE_ID = "transcript"
CLI = "ext:claude-code"
GATEWAY = "aai-gateway"
HOOKHUB = "hook-hub"
SKIP_PREFIXES = (b'{"type":"api-request-blob"', b'{"type":"api-request-shape"')
FULL_LIMIT = 65536
PUBLIC_LIMIT = 280
USAGE_KEYS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens")


# =====================================================================================================
# formatting helpers
# =====================================================================================================

def fmt_tokens(n: float | int | None) -> str:
    if n is None:
        return "?"
    n = int(n)
    if n < 1000:
        return str(n)
    v = n / 1000.0
    s = f"{v:.1f}" if v < 100 else f"{v:.0f}"
    return s[:-2] + "k" if s.endswith(".0") else s + "k"


def fmt_dur(ms_: float | None) -> str:
    if ms_ is None:
        return "?"
    if ms_ < 1000:
        return f"{int(ms_)} ms"
    return f"{ms_ / 1000.0:.1f} s"


def _limit(ctx: Ctx) -> int:
    return PUBLIC_LIMIT if ctx.profile == "public" else FULL_LIMIT


def prof_text(ctx: Ctx, text: str) -> str:
    """Public profile: home paths become ~ before the artifact is stored."""
    if ctx.profile == "public" and text:
        return tilde(text) or text
    return text


# =====================================================================================================
# hook-hub context splitting
# =====================================================================================================

# (handler id, start regex, kind) with kind: block (explicit close tag), line, paragraph, open (until next marker)
_RECALL_OPEN = re.compile(r"<!-- hindsight:recall bank=([^\s>]+) -->")
_BRIEF_OPEN = re.compile(r"<!-- hindsight:briefing bank=([^\s>]+) -->")
_MARKERS: list[tuple[str, re.Pattern[str], str, str | None]] = [
    ("hindsight-recall", _RECALL_OPEN, "block", "<!-- /hindsight:recall -->"),
    ("hindsight-briefing", _BRIEF_OPEN, "block", "<!-- /hindsight:briefing -->"),
    ("codegraph-prompt", re.compile(r"<codegraph_context"), "block", "</codegraph_context>"),
    ("skill-reminder", re.compile(r"⚡ REMINDER"), "open", None),
    ("crank-tag", re.compile(r"This prompt was typed by Crank, the operator's automated stand-in"), "paragraph", None),
    ("automaticai-routing-start", re.compile(r"AutomaticAI prompt proof marker: AAI_ROUTE_PROOF_[0-9a-f]+"), "line", None),
    ("candystore-context", re.compile(r"CandyStore recent context — "), "open", None),
    ("code-review-graph-status", re.compile(r"(?m)^Nodes: \d+\nEdges: \d+\nFiles:"), "open", None),
]


def split_context(text: str) -> list[dict[str, Any]]:
    """Split merged additionalContext into per-handler segments by the handlers' own markers.

    Returns [{handler, text, banks?}] in order of first appearance. Text no marker claims goes to 'unknown'.
    Several hindsight blocks (one per bank) merge into a single hindsight-recall / -briefing segment.
    """
    if not text or not text.strip():
        return []
    starts: list[tuple[int, str, str, str | None, re.Match[str]]] = []
    for hid, pat, kind, close in _MARKERS:
        for m in pat.finditer(text):
            starts.append((m.start(), hid, kind, close, m))
    starts.sort(key=lambda s: s[0])

    raw: list[dict[str, Any]] = []
    cursor = 0
    i = 0
    while i < len(starts):
        pos, hid, kind, close, m = starts[i]
        if pos < cursor:        # marker text quoted inside an earlier block (e.g. a recalled memory)
            i += 1
            continue
        if pos > cursor and text[cursor:pos].strip():
            raw.append({"handler": "unknown", "text": text[cursor:pos].strip("\n")})
        nxt = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        if kind == "block" and close:
            ci = text.find(close, m.end())
            end = ci + len(close) if ci >= 0 else nxt
        elif kind == "line":
            nl = text.find("\n", m.end())
            end = nl if nl >= 0 else len(text)
        elif kind == "paragraph":
            pb = text.find("\n\n", m.end())
            end = min(pb if pb >= 0 else len(text), nxt)
        else:
            end = nxt
        seg: dict[str, Any] = {"handler": hid, "text": text[pos:end].strip("\n")}
        if hid in ("hindsight-recall", "hindsight-briefing"):
            seg["bank"] = m.group(1)
        raw.append(seg)
        cursor = max(cursor, end)
        i += 1
    if cursor < len(text) and text[cursor:].strip():
        raw.append({"handler": "unknown", "text": text[cursor:].strip("\n")})

    merged: dict[str, dict[str, Any]] = {}
    for seg in raw:
        cur = merged.get(seg["handler"])
        if cur is None:
            cur = merged[seg["handler"]] = {"handler": seg["handler"], "text": seg["text"]}
            if "bank" in seg:
                cur["banks"] = [seg["bank"]]
        else:
            cur["text"] += "\n\n" + seg["text"]
            if "bank" in seg:
                cur.setdefault("banks", []).append(seg["bank"])
    return list(merged.values())


_PERSISTED = re.compile(r"Full output saved to:\s*(\S+)")


def resolve_persisted(text: str) -> tuple[str, dict[str, Any]]:
    """Large hook contexts are replaced by a 2 KB preview + a file path. Return (full text if readable, info)."""
    if not text.startswith("<persisted-output>"):
        return text, {}
    info: dict[str, Any] = {"persisted": True, "model_saw_chars": len(text)}
    m = _PERSISTED.search(text)
    if m:
        path = m.group(1).rstrip(".,;)")
        info["persisted_path"] = tilde(path)
        try:
            if os.path.isfile(path) and os.path.getsize(path) < 4_000_000:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    full = fh.read()
                info["persisted_chars"] = len(full)
                return full, info
        except OSError:
            pass
    return text, info


# =====================================================================================================
# model-call grouping (shared by main thread and sidechains)
# =====================================================================================================

def _content_blocks(msg: Any) -> list[Any]:
    c = msg.get("content") if isinstance(msg, dict) else None
    return c if isinstance(c, list) else []


def block_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for b in content or []:
        if isinstance(b, dict):
            if b.get("type") == "text":
                parts.append(str(b.get("text") or ""))
            elif b.get("type") == "image":
                parts.append("[image]")
        elif isinstance(b, str):
            parts.append(b)
    return "\n".join(parts)


_RID = re.compile(r"request id:\s*([A-Za-z0-9_\-]+)")


class Calls:
    """Group assistant entries by requestRef (else message.id) into one call, deduping the repeated usage."""

    def __init__(self) -> None:
        self.order: list[dict[str, Any]] = []
        self.by_key: dict[str, dict[str, Any]] = {}
        self.by_msg: dict[str, dict[str, Any]] = {}

    def _new(self, key: str | None) -> dict[str, Any]:
        call = {"n": len(self.order) + 1, "key": key, "t_req": None, "t_first": None, "t_last": None,
                "requested": None, "query_source": None, "effort_param": None, "effort": None, "served": None,
                "usage": {}, "stop_reason": None, "thinking_ms": None, "msg_ids": [], "is_error": False,
                "error_status": None, "error_text": None, "request_id": None, "tool_ids": [], "retries": [],
                "got_response": False}
        self.order.append(call)
        if key:
            self.by_key[key] = call
        return call

    def request(self, d: dict[str, Any]) -> dict[str, Any]:
        params = d.get("params") if isinstance(d.get("params"), dict) else {}
        call = self._new(d.get("id"))
        call["t_req"] = ms(d.get("timestamp"))
        call["query_source"] = d.get("querySource")
        call["requested"] = params.get("model")
        oc = params.get("output_config") if isinstance(params.get("output_config"), dict) else {}
        call["effort_param"] = oc.get("effort")
        return call

    def assistant(self, d: dict[str, Any]) -> dict[str, Any]:
        msg = d.get("message") if isinstance(d.get("message"), dict) else {}
        key, mid = d.get("requestRef"), msg.get("id")
        call = self.by_key.get(key) if key else None
        if call is None and mid:
            call = self.by_msg.get(mid)
        if call is None:
            call = self._new(key or mid)
        if key and key not in self.by_key:
            self.by_key[key] = call
        if mid:
            self.by_msg.setdefault(mid, call)
            if mid not in call["msg_ids"]:
                call["msg_ids"].append(mid)
        ts = ms(d.get("timestamp"))
        if ts is not None:
            call["t_first"] = ts if call["t_first"] is None else min(call["t_first"], ts)
            call["t_last"] = ts if call["t_last"] is None else max(call["t_last"], ts)
        call["got_response"] = True
        if d.get("requestedModel") and not call["requested"]:
            call["requested"] = d.get("requestedModel")
        if d.get("effort"):
            call["effort"] = d.get("effort")
        if d.get("thinkingDurationMs") is not None:
            call["thinking_ms"] = (call["thinking_ms"] or 0) + d["thinkingDurationMs"]
        model = msg.get("model")
        if d.get("isApiErrorMessage") or model == "<synthetic>":
            call["is_error"] = True
            call["error_status"] = d.get("apiErrorStatus") or d.get("error")
            txt = block_text(msg.get("content"))
            call["error_text"] = txt[:300]
            m = _RID.search(txt)
            if m:
                call["request_id"] = m.group(1)
        else:
            if model:
                call["served"] = model
            if msg.get("stop_reason"):
                call["stop_reason"] = msg["stop_reason"]
            u = msg.get("usage") if isinstance(msg.get("usage"), dict) else {}
            for k in USAGE_KEYS:
                v = u.get(k)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    call["usage"][k] = max(call["usage"].get(k, 0), int(v))
        for b in _content_blocks(msg):
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") not in call["tool_ids"]:
                call["tool_ids"].append(b["id"])
        return call

    def last(self) -> dict[str, Any] | None:
        return self.order[-1] if self.order else None


def call_tokens(call: dict[str, Any]) -> tuple[int, int]:
    """(gateway-comparable input total, output) of a grouped call."""
    u = call.get("usage") or {}
    total = int(u.get("input_tokens", 0)) + int(u.get("cache_read_input_tokens", 0)) + int(u.get("cache_creation_input_tokens", 0))
    return total, int(u.get("output_tokens", 0))


# =====================================================================================================
# parsing a turn
# =====================================================================================================

def _first_text(content: Any) -> str:
    return block_text(content)[:120]


_PARSE_CACHE: dict[tuple, Any] = {}
_PARSE_LOCK = threading.Lock()
_PARSE_CACHE_MAX = 8


def memoised_parse(path: str | None, window: TurnWindow, extra: tuple, fn):
    """Parse a turn once per (file identity, turn selector): the transcript and gateway collectors both need the same
    parse, and the transcript is the biggest file the recorder reads (finding 34). The key is the path with its mtime
    and size, so a transcript that grew since the last parse is read again. Callers get a deep copy to mutate."""
    try:
        st = os.stat(path) if path else None
    except OSError:
        st = None
    if st is None:
        return fn()
    key = (path, st.st_mtime_ns, st.st_size, window.session_id, window.t0, window.turn_index, window.turn_id,
           window.t_end, *extra)
    with _PARSE_LOCK:
        hit = _PARSE_CACHE.get(key)
    if hit is None:
        hit = fn()
        with _PARSE_LOCK:
            if len(_PARSE_CACHE) >= _PARSE_CACHE_MAX:
                _PARSE_CACHE.pop(next(iter(_PARSE_CACHE)))
            _PARSE_CACHE[key] = hit
    return copy.deepcopy(hit)


def parse_turn(window: TurnWindow, profile: str = "full") -> dict[str, Any]:
    path = window.transcript_path or W.claude_transcript_path(window.session_id)
    return memoised_parse(path, window, ("claude", profile), lambda: _parse_turn(window, profile))


def _parse_turn(window: TurnWindow, profile: str = "full") -> dict[str, Any]:
    path = window.transcript_path or W.claude_transcript_path(window.session_id)
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"no Claude transcript for session {window.session_id}")
    prompts = W.claude_prompts(path)
    entry = W.claude_find_prompt(path, near_ms=window.t0, turn_index=window.turn_index, prompts=prompts)
    if entry is None:
        raise LookupError(f"no typed user entry near {iso(window.t0)} in {path}")

    calls = Calls()
    tools: dict[str, dict[str, Any]] = {}
    contexts: list[dict[str, Any]] = []
    hooks_by_tool: dict[str, list[dict[str, Any]]] = {}
    prompt_hooks: list[dict[str, Any]] = []
    client_hooks: list[dict[str, Any]] = []
    metas: list[dict[str, Any]] = []
    result_calls: dict[str, int] = {}
    info: dict[str, Any] = {"turn_duration": None, "stop_hook_summary": None, "compactions": 0, "scheduled": 0,
                            "api_errors": 0, "entries": 0}
    last_ts = entry["ts"]
    limit_ts = (window.t_end or 0) + 60000 if window.t_end else None

    for _ln, off, d in W.iter_jsonl(path, entry["offset"], None, SKIP_PREFIXES):
        info["entries"] += 1
        if d.get("isSidechain"):
            continue
        typ = d.get("type")
        ts = ms(d.get("timestamp"))
        if off != entry["offset"] and limit_ts and ts and ts > limit_ts:
            break
        if ts:
            last_ts = max(last_ts or 0, ts)
        if typ == "user":
            if off != entry["offset"] and d.get("promptSource") and d.get("turnPosition"):
                break
            msg = d.get("message") if isinstance(d.get("message"), dict) else {}
            blocks = _content_blocks(msg)
            results = [b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_result"]
            for b in results:
                tid = b.get("tool_use_id")
                t = tools.get(tid)
                if t is None:
                    continue
                t["t1"] = ts
                t["is_error"] = bool(b.get("is_error"))
                t["result"] = block_text(b.get("content"))
                t["result_uuid"] = d.get("uuid")
                tur = d.get("toolUseResult")
                if isinstance(tur, dict):
                    for k in ("durationMs", "exitCode", "interrupted", "returnCodeInterpretation"):
                        if k in tur:
                            t.setdefault("meta", {})[k] = tur[k]
                result_calls[tid] = len(calls.order) + 1
            if d.get("isMeta") and not results and off != entry["offset"]:
                metas.append({"t": ts, "chars": len(block_text(msg.get("content"))), "head": _first_text(msg.get("content"))})
        elif typ == "api-request":
            calls.request(d)
        elif typ == "assistant":
            call = calls.assistant(d)
            msg = d.get("message") if isinstance(d.get("message"), dict) else {}
            for b in _content_blocks(msg):
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") not in tools:
                    tools[b["id"]] = {"id": b["id"], "name": b.get("name"), "input": b.get("input"), "t0": ts, "t1": None,
                                      "is_error": False, "result": None, "call_n": call["n"], "hooks": []}
        elif typ == "attachment":
            a = d.get("attachment") if isinstance(d.get("attachment"), dict) else {}
            at = a.get("type")
            if at == "hook_additional_context":
                c = a.get("content")
                text = "\n\n".join(str(x) for x in c) if isinstance(c, list) else str(c or "")
                contexts.append({"t": ts, "hook_event": a.get("hookEvent"), "hook_name": a.get("hookName"),
                                 "tool_use_id": a.get("toolUseID"), "text": text, "elements": len(c) if isinstance(c, list) else 1})
            elif at == "hook_success":
                rec = {"name": a.get("hookName"), "event": a.get("hookEvent"), "duration_ms": a.get("durationMs"),
                       "exit_code": a.get("exitCode"), "t": ts}
                client_hooks.append(client_hook_record(a, ts))
                tid = a.get("toolUseID")
                if isinstance(tid, str) and tid.startswith("toolu_"):
                    hooks_by_tool.setdefault(tid, []).append(rec)
                elif a.get("hookEvent") == "UserPromptSubmit":
                    prompt_hooks.append(rec)
        elif typ == "system":
            st = d.get("subtype")
            if st == "turn_duration":
                info["turn_duration"] = {"duration_ms": d.get("durationMs"), "message_count": d.get("messageCount"),
                                         "pending_workflows": d.get("pendingWorkflowCount"), "t": ts}
                break
            elif st == "stop_hook_summary":
                info["stop_hook_summary"] = {"count": d.get("hookCount"), "t": ts,
                                             "prevented": d.get("preventedContinuation"),
                                             "hooks": [{"command": scrub(str(h.get("command", ""))[:120]), "duration_ms": h.get("durationMs")}
                                                       for h in d.get("hookInfos") or [] if isinstance(h, dict)]}
            elif st == "api_error":
                info["api_errors"] += 1
                err = d.get("error") if isinstance(d.get("error"), dict) else {}
                txt = str(err.get("formatted") or err.get("message") or "")
                m = _RID.search(txt)
                rec = {"status": err.get("status"), "request_id": m.group(1) if m else None, "attempt": d.get("retryAttempt"),
                       "retry_in_ms": d.get("retryInMs"), "t": ts}
                lc = calls.last()
                if lc is not None:
                    lc["retries"].append(rec)
                    if m and not lc["request_id"]:
                        lc["request_id"] = m.group(1)
            elif st == "compact_boundary":
                info["compactions"] += 1
            elif st == "scheduled_task_fire":
                info["scheduled"] += 1

    # pre-turn SessionStart contexts (headless / exec: the briefing is written just before the user entry)
    pre, pre_hooks = _pre_turn_records(path, entry["offset"], entry["ts"])
    client_hooks = pre_hooks + client_hooks
    for t in tools.values():
        t["hooks"] = hooks_by_tool.get(t["id"], [])
    return {"path": path, "entry": entry, "calls": calls.order, "tools": tools, "contexts": pre + contexts,
            "prompt_hooks": prompt_hooks, "client_hooks": client_hooks, "metas": metas, "result_calls": result_calls, "info": info, "last_ts": last_ts}


def client_hook_kind(command: str) -> str:
    """Which hook command a transcript hook_success belongs to."""
    c = command or ""
    if "bb-hook" in c:
        return "bb-hook"
    if "ORCA_AGENT_HOOK" in c or ".orca/agent-hooks" in c:
        return "orca"
    if "codex-mcp-helper-reaper" in c:
        return "codex-mcp-helper-reaper"
    return "other"


def client_hook_record(a: dict[str, Any], ts: float | None) -> dict[str, Any]:
    """One CLI-side hook run from a transcript `hook_success` attachment (timestamp = when it finished)."""
    cmd = str(a.get("command") or "")
    kind = client_hook_kind(cmd)
    dur = a.get("durationMs")
    try:
        dur_f = float(dur) if dur is not None else None
    except (TypeError, ValueError):
        dur_f = None
    return {"event": a.get("hookEvent"), "name": a.get("hookName"), "tool_use_id": a.get("toolUseID"),
            "duration_ms": dur_f, "exit_code": a.get("exitCode"), "t": ts, "kind": kind,
            "command": scrub(cmd[:160]) if kind in ("bb-hook", "other") else None}


def _pre_turn_records(path: str, offset: int, t0: float | None, lookback_ms: float = 30000.0,
                      max_bytes: int = 3_000_000) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """SessionStart records written just before the user entry: (additionalContext contexts, hook_success runs)."""
    out: list[dict[str, Any]] = []
    hooks: list[dict[str, Any]] = []
    if not offset or t0 is None:
        return out, hooks
    start = max(0, offset - max_bytes)
    try:
        with open(path, "rb") as fh:
            fh.seek(start)
            blob = fh.read(offset - start)
    except OSError:
        return out, hooks
    for raw in blob.split(b"\n"):
        if (b'"hook_additional_context"' not in raw and b'"hook_success"' not in raw) or raw.startswith(SKIP_PREFIXES):
            continue
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        a = d.get("attachment") if isinstance(d.get("attachment"), dict) else {}
        ts = ms(d.get("timestamp"))
        if a.get("hookEvent") != "SessionStart" or ts is None:
            continue
        if not (t0 - lookback_ms <= ts <= t0 + 2000):
            continue
        if a.get("type") == "hook_additional_context":
            c = a.get("content")
            text = "\n\n".join(str(x) for x in c) if isinstance(c, list) else str(c or "")
            out.append({"t": ts, "hook_event": "SessionStart", "hook_name": a.get("hookName"),
                        "tool_use_id": a.get("toolUseID"), "text": text, "elements": len(c) if isinstance(c, list) else 1})
        elif a.get("type") == "hook_success":
            hooks.append(client_hook_record(a, ts))
    return out, hooks


def _pre_turn_contexts(path: str, offset: int, t0: float | None, lookback_ms: float = 30000.0,
                       max_bytes: int = 3_000_000) -> list[dict[str, Any]]:
    return _pre_turn_records(path, offset, t0, lookback_ms, max_bytes)[0]


# =====================================================================================================
# subagent sidechains
# =====================================================================================================

def subagent_files(path: str, prompt_id: str | None) -> list[dict[str, Any]]:
    """Sidechain transcripts of this session whose first entries carry the turn's promptId."""
    base = path[:-6] if path.endswith(".jsonl") else path
    root = os.path.join(base, "subagents")
    if not os.path.isdir(root):
        return []
    out = []
    for p in sorted(glob.glob(os.path.join(glob.escape(root), "**", "agent-*.jsonl"), recursive=True)):
        pid = None
        first_ts = None
        try:
            with open(p, "rb") as fh:
                for i, raw in enumerate(fh):
                    if i >= 6:
                        break
                    if raw.startswith(SKIP_PREFIXES) or not raw.strip():
                        continue
                    try:
                        d = json.loads(raw)
                    except ValueError:
                        continue
                    pid = pid or d.get("promptId")
                    first_ts = first_ts or ms(d.get("timestamp"))
                    if pid:
                        break
        except OSError:
            continue
        if prompt_id and pid and pid != prompt_id:
            continue
        meta: dict[str, Any] = {}
        mp = p[:-6] + ".meta.json"
        try:
            with open(mp, "r", encoding="utf-8") as fh:
                meta = json.load(fh)
        except (OSError, ValueError):
            pass
        stem = os.path.basename(p)[:-6]
        out.append({"path": p, "rel": os.path.relpath(p, base), "agent_id": stem[len("agent-"):] if stem.startswith("agent-") else stem,
                    "agent_type": meta.get("agentType"), "description": meta.get("description"),
                    "workflow_phase": meta.get("workflowPhase"), "first_ts": first_ts})
    return out


def sidechain_calls(sub: dict[str, Any]) -> list[dict[str, Any]]:
    calls = Calls()
    try:
        with open(sub["path"], "rb") as fh:
            for raw in fh:
                if b'"type":"assistant"' not in raw[:200] and b'"type": "assistant"' not in raw[:200] and b'"usage"' not in raw:
                    continue
                if raw.startswith(SKIP_PREFIXES):
                    continue
                try:
                    d = json.loads(raw)
                except ValueError:
                    continue
                if d.get("type") == "assistant":
                    calls.assistant(d)
    except OSError:
        return []
    return calls.order


def sidechain_tools(sub: dict[str, Any]) -> dict[str, Any]:
    """Tool calls and the time span of one subagent sidechain: {'tools': {tool_use_id: {...}}, 'first', 'last', 'calls'}.

    Same tool shape as parse_turn (name, input, t0, t1, is_error, result, call_n); call_n counts the sidechain's own
    model calls, which is what the gateway collector stores as attrs.transcript_llm on a subagent row."""
    calls = Calls()
    tools: dict[str, dict[str, Any]] = {}
    first = last = None
    try:
        with open(sub["path"], "rb") as fh:
            for raw in fh:
                if raw.startswith(SKIP_PREFIXES) or not raw.strip():
                    continue
                try:
                    d = json.loads(raw)
                except ValueError:
                    continue
                ts = ms(d.get("timestamp"))
                if ts is not None:
                    first = ts if first is None else min(first, ts)
                    last = ts if last is None else max(last, ts)
                typ = d.get("type")
                msg = d.get("message") if isinstance(d.get("message"), dict) else {}
                if typ == "assistant":
                    call = calls.assistant(d)
                    for b in _content_blocks(msg):
                        if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") not in tools:
                            tools[b["id"]] = {"id": b["id"], "name": b.get("name"), "input": b.get("input"), "t0": ts,
                                              "t1": None, "is_error": False, "result": None, "call_n": call["n"]}
                elif typ == "user":
                    for b in _content_blocks(msg):
                        if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") in tools:
                            t = tools[b["tool_use_id"]]
                            t["t1"] = ts
                            t["is_error"] = bool(b.get("is_error"))
                            t["result"] = block_text(b.get("content"))
    except OSError:
        pass
    return {"tools": tools, "first": first, "last": last, "calls": len(calls.order)}


def transcript_llm_calls(window: TurnWindow, include_sidechains: bool = True) -> list[dict[str, Any]]:
    """Every model call the transcript saw for this turn (main thread + sidechains) for gateway attribution.

    [{'source': 'main'|'subagent', 'n', 'agent_id', 'agent_type', 'input_tokens', 'output_tokens', 't0', 't1',
      'requested_model', 'served_model', 'client_request'}]
    """
    out: list[dict[str, Any]] = []
    parsed = parse_turn(window)
    for c in parsed["calls"]:
        i, o = call_tokens(c)
        out.append({"source": "main", "n": c["n"], "agent_id": None, "agent_type": None, "input_tokens": i, "output_tokens": o,
                    "t0": c["t_req"] or c["t_first"], "t1": c["t_last"], "requested_model": c["requested"],
                    "served_model": c["served"], "client_request": c["key"], "query_source": c["query_source"]})
    if include_sidechains:
        for sub in subagent_files(parsed["path"], parsed["entry"].get("promptId")):
            for c in sidechain_calls(sub):
                i, o = call_tokens(c)
                out.append({"source": "subagent", "n": c["n"], "agent_id": sub["agent_id"], "agent_type": sub["agent_type"],
                            "input_tokens": i, "output_tokens": o, "t0": c["t_first"], "t1": c["t_last"],
                            "requested_model": c["requested"], "served_model": c["served"], "client_request": c["key"],
                            "query_source": "subagent"})
    return out


# =====================================================================================================
# the collector
# =====================================================================================================

def _tool_brief(name: str | None, inp: Any) -> str:
    if not isinstance(inp, dict):
        return name or "tool"
    for k in ("description", "command", "file_path", "path", "pattern", "query", "url", "prompt", "skill", "name"):
        v = inp.get(k)
        if isinstance(v, str) and v.strip():
            return scrub(v.strip().replace("\n", " "))[:90]
    for v in inp.values():
        if isinstance(v, str) and v.strip():
            return scrub(v.strip().replace("\n", " "))[:90]
    return name or "tool"


def _context_phase(hook_event: str | None) -> str:
    return "session_start" if hook_event == "SessionStart" else "prompt_submit"


def _hook_phase(hook_event: str | None) -> str:
    ev = hook_event or ""
    if ev == "SessionStart":
        return "session_start"
    if ev in ("PreToolUse", "PermissionRequest"):
        return "pre_tool"
    if ev.startswith("PostTool"):
        return "post_tool"
    if ev in ("Stop", "StopFailure"):
        return "turn_end"
    if ev == "SessionEnd":
        return "session_end"
    return "prompt_submit"


def _add_link(frag: Fragment, seen: set[tuple[str, str, str]], a: str, b: str, kind: str) -> None:
    k = (a, b, kind)
    if k not in seen:
        seen.add(k)
        frag.links.append(Link(from_=a, to=b, kind=kind))


CLIENT_HOOK_COMPONENT = {"bb-hook": "bb-hook", "orca": "ext:orca", "codex-mcp-helper-reaper": "ext:codex-mcp-helper-reaper",
                         "other": "ext:hook-command"}
CLIENT_HOOK_LABEL = {"bb-hook": "bb-hook", "orca": "Orca shim", "codex-mcp-helper-reaper": "codex-mcp-helper-reaper",
                     "other": "hook command"}


def _build_client_hooks(ctx: Ctx, frag: Fragment, parsed: dict[str, Any]) -> None:
    """CLI-side hook runs (transcript hook_success: durationMs, exit code). bb-hook ones are joined to the hub
    invocation by the assembler (attrs._hub_match); the Orca shim and the codex MCP helper reaper stand alone."""
    w = ctx.window
    seen: dict[str, int] = {}
    for h in parsed.get("client_hooks") or []:
        t1, dur = h.get("t"), h.get("duration_ms")
        if t1 is None or dur is None:
            continue
        if t1 < w.t0 - 35000.0 or (w.t_end and t1 > w.t_end + 60000.0):
            continue
        ev = h.get("event") or "hook"
        kind = h.get("kind") or "other"
        comp = CLIENT_HOOK_COMPONENT.get(kind, "ext:hook-command")
        label = CLIENT_HOOK_LABEL.get(kind, kind)
        if comp.startswith("ext:"):
            frag.component(comp, label, "external")
        else:
            frag.component(comp, label, "cli")
        base = Ids.client_hook(ev, t1 - dur)
        n = seen.get(base, 0)
        seen[base] = n + 1
        failed = str(h.get("exit_code")) not in ("0", "None", "")
        attrs: dict[str, Any] = {"hook_event": ev, "hook_name": h.get("name"), "duration_ms": dur,
                                 "exit_code": h.get("exit_code"), "client": kind, "client_side": True,
                                 "tool_use_id": h.get("tool_use_id") if str(h.get("tool_use_id") or "").startswith("toolu_") else None}
        if h.get("command"):
            attrs["command"] = h["command"]
        if kind == "bb-hook":
            attrs["_hub_match"] = {"native": ev, "tool_use_id": attrs["tool_use_id"]}
        frag.spans.append(Span(
            id=Ids.client_hook(ev, t1 - dur, n), kind="hook", component=comp, name=f"{ev} ({label})",
            summary=f"{label} ran the {ev} hook for {fmt_dur(dur)} on the CLI side (transcript hook_success durationMs)",
            phase=_hook_phase(ev), t0=t1 - dur, t1=t1, status="failed" if failed else "ok", sync=True,
            refs={"tool_use_id": attrs["tool_use_id"]} if attrs["tool_use_id"] else {}, attrs=attrs,
            evidence=[SOURCE_ID]))


def _build_contexts(ctx: Ctx, frag: Fragment, parsed: dict[str, Any], seen: set[tuple[str, str, str]]) -> None:
    w = ctx.window
    lim = _limit(ctx)
    inv_rows: list[dict[str, Any]] | None = None     # one receipts connection for every context
    for c in parsed["contexts"]:
        ev = c["hook_event"] or "UserPromptSubmit"
        ts = c["t"] or w.t0
        inv = None
        if ev == "UserPromptSubmit" and w.prompt_invocation_id and ts >= w.t0 - 2000:
            inv = w.prompt_invocation_id
        else:
            if inv_rows is None:
                try:
                    inv_rows = W.hook_invocations(w.session_id)
                except (OSError, sqlite3.Error):
                    inv_rows = []
            row = W.nearest_invocation(w.session_id, ev, ts + 100, rows=inv_rows)
            inv = row["invocation_id"] if row else None
        if not inv:
            inv = f"{ev}:{c['tool_use_id'] or int(ts)}"
            frag.gaps.append(Gap(HOOKHUB, f"{ev} context at {iso(ts)} could not be tied to a hook-hub invocation",
                                 "no receipt within 2 min before it (aged out or never recorded); toolUseID used as the key", "info"))
        text, pinfo = resolve_persisted(c["text"])
        segs = split_context(text)
        handlers = [s["handler"] for s in segs]
        merged_id = Ids.context(inv)
        attrs: dict[str, Any] = {"hook_event": ev, "chars": len(text), "tool_use_id": c["tool_use_id"], "handlers": handlers,
                                 "elements": c["elements"], "model_saw_chars": len(c["text"]), **pinfo}
        if pinfo.get("persisted") and "persisted_chars" not in pinfo:
            attrs["note"] = "model saw only the 2 KB preview; full file not readable"
        frag.spans.append(Span(
            id=merged_id, kind="context", component=HOOKHUB, name="additionalContext",
            summary=f"{ev} hook context injected: {fmt_tokens(len(text))} chars from {len(handlers)} handler(s) ({', '.join(handlers) or 'none'})",
            phase=_context_phase(ev), t0=ts, t1=None, sync=True, parent=Ids.hook(inv),
            refs={"invocation_id": inv, "tool_use_id": c["tool_use_id"]}, attrs=attrs,
            payload=frag.artifact(prof_text(ctx, text), limit=lim, note="injected context" + (" (persisted file)" if pinfo.get("persisted_chars") else "")),
            evidence=[SOURCE_ID]))
        for s in segs:
            hid = s["handler"]
            sattrs: dict[str, Any] = {"handler_id": hid, "hook_event": ev, "chars": len(s["text"])}
            if s.get("banks"):
                sattrs["banks"] = s["banks"]
            sid = Ids.context(inv, hid)
            frag.spans.append(Span(
                id=sid, kind="context", component=HOOKHUB, name=hid,
                summary=f"{hid} injected {fmt_tokens(len(s['text']))} chars" + (f" (bank {', '.join(s['banks'])})" if s.get("banks") else ""),
                phase=_context_phase(ev), t0=ts, t1=None, sync=True, parent=merged_id,
                refs={"invocation_id": inv, "handler_id": hid}, attrs=sattrs,
                payload=frag.artifact(prof_text(ctx, s["text"]), limit=lim), evidence=[SOURCE_ID]))
            if hid != "unknown":
                _add_link(frag, seen, Ids.handler(inv, hid), sid, "injects")
        if any(s["handler"] == "unknown" for s in segs):
            frag.gaps.append(Gap(HOOKHUB, f"{ev} context contains text no known handler marker claims",
                                 "assigned to handler 'unknown' (a handler without a recognised marker, e.g. project-notebook-start)",
                                 "info", Ids.context(inv, "unknown")))


def _llm_span(ctx: Ctx, c: dict[str, Any], n_total: int) -> Span:
    u = c["usage"]
    i_raw, cr, cw, out = (u.get(k, 0) for k in USAGE_KEYS)
    tin, tout = call_tokens(c)
    t0 = c["t_req"] if c["t_req"] is not None else c["t_first"]
    t1 = c["t_last"]
    dur = (t1 - t0) if (t0 is not None and t1 is not None) else None
    status, reason = "ok", None
    if c["is_error"]:
        status, reason = "failed", f"api_error {c['error_status']}" if c["error_status"] else "api_error"
    elif not c["got_response"]:
        status, reason = ("failed", f"api_error {c['retries'][-1].get('status')}") if c["retries"] else ("unknown", "no assistant entry recorded")
    served = c["served"]
    requested = c["requested"]
    if status == "ok":
        cached = f" ({fmt_tokens(cr)} cached)" if cr else ""
        summary = (f"model call {c['n']} via {requested or '?'} -> {served or '?'}: {fmt_tokens(tin)} in{cached} / {fmt_tokens(tout)} out, {fmt_dur(dur)}")
    else:
        summary = f"model call {c['n']} via {requested or '?'} failed ({reason})"
    refs: dict[str, Any] = {"client_request": c["key"]}
    if c["request_id"]:
        refs["request_id"] = c["request_id"]
    attrs: dict[str, Any] = {
        "requested_model": requested, "served_model": served,
        "usage": {"input_tokens": i_raw, "cache_read_input_tokens": cr, "cache_creation_input_tokens": cw, "output_tokens": out},
        "tokens_in": tin, "tokens_out": tout, "input_tokens": tin, "output_tokens": tout,
        "stop_reason": c["stop_reason"], "client_request": c["key"], "effort": c["effort"] or c["effort_param"],
        "query_source": c["query_source"], "thinking_ms": c["thinking_ms"], "tool_calls": len(c["tool_ids"]),
        "message_ids": c["msg_ids"][:3],
    }
    if c["retries"]:
        attrs["retries"] = c["retries"]
    return Span(id=Ids.llm(c["n"]), kind="llm", component=GATEWAY, name=f"model call {c['n']}", summary=summary,
                phase="model_call", t0=t0 if t0 is not None else ctx.window.t0, t1=t1, status=status, reason=reason, sync=True,
                parent=Ids.TURN, refs=refs, attrs=attrs, evidence=[SOURCE_ID])


def _tool_span(ctx: Ctx, frag: Fragment, t: dict[str, Any], t_fallback: float, lim: int,
               extra: dict[str, Any] | None = None) -> Span:
    """One tool_use -> tool_result as a tool span (main thread, or a subagent sidechain when extra is given)."""
    tid, inp = t["id"], t["input"]
    in_text = json.dumps(inp, ensure_ascii=False, default=str) if not isinstance(inp, str) else inp
    status, reason = "ok", None
    if t["t1"] is None:
        status = "pending"
    elif t["is_error"]:
        status, reason = "failed", (t["result"] or "")[:120] or "tool error"
    attrs: dict[str, Any] = {"name": t["name"], "tool_use_id": tid, "llm": t["call_n"],
                             "input_artifact": frag.artifact(prof_text(ctx, in_text), limit=lim),
                             "is_error": t["is_error"]}
    if extra:
        attrs.update({k: v for k, v in extra.items() if v is not None})
    if t.get("meta"):
        attrs["result_meta"] = t["meta"]
    if t.get("hooks"):
        attrs["hooks"] = [{"name": h["name"], "duration_ms": h["duration_ms"], "exit_code": h["exit_code"]} for h in t["hooks"]]
    payload = None
    if t["result"] is not None:
        payload = frag.artifact(prof_text(ctx, t["result"]), limit=lim)
        attrs["result_artifact"] = payload
        attrs["result_chars"] = len(t["result"])
    dur = (t["t1"] - t["t0"]) if (t["t1"] and t["t0"]) else None
    brief = _tool_brief(t["name"], inp)
    who = f"[{extra.get('agent_type') or 'subagent'}] " if extra and extra.get("subagent") else ""
    sp = Span(id=Ids.tool(tid), kind="tool", component=CLI, name=t["name"] or "tool",
              summary=f"{who}{t['name']}: {brief}" + (f" ({fmt_dur(dur)})" if dur is not None else " (no result recorded)"),
              phase="tool", t0=t["t0"] or t_fallback, t1=t["t1"], status=status, reason=reason,
              sync=None if extra and extra.get("subagent") else True,
              parent=None if extra and extra.get("subagent") else Ids.TURN,
              refs={"tool_use_id": tid}, attrs=attrs, payload=payload, evidence=[SOURCE_ID])
    frag.spans.append(sp)
    return sp


def collect(ctx: Ctx) -> Fragment:
    t_start = time.monotonic()
    w = ctx.window
    path = w.transcript_path or W.claude_transcript_path(w.session_id)
    src = Source(id=SOURCE_ID, kind="jsonl", locator=tilde(path) or f"~/.claude/projects/*/{w.session_id}.jsonl")
    frag = Fragment(source=src)
    try:
        _collect(ctx, frag, path)
    except Exception as e:  # noqa: BLE001 - every collector fails soft
        src.status = "error"
        src.error = f"{type(e).__name__}: {e}"
        frag.gaps.append(Gap(CLI, "Claude transcript could not be read", f"{type(e).__name__}: {e}", "warn"))
        frag.spans.clear()
        frag.links.clear()
    src.items = len(frag.spans)
    if src.status == "ok" and not frag.spans:
        src.status = "empty"
    src.ms = round((time.monotonic() - t_start) * 1000.0, 1)
    return frag


def _collect(ctx: Ctx, frag: Fragment, path: str | None) -> None:
    w = ctx.window
    lim = _limit(ctx)
    if path:
        w.transcript_path = path
    parsed = parse_turn(w, ctx.profile)
    entry, calls, tools, info = parsed["entry"], parsed["calls"], parsed["tools"], parsed["info"]
    frag.component(CLI, "Claude Code", "cli")
    frag.component(GATEWAY, "AutomaticAI gateway", "service")
    frag.component(HOOKHUB, "hook-hub", "handler-host")
    seen: set[tuple[str, str, str]] = set()
    t0 = entry["ts"] if entry["ts"] is not None else w.t0
    surface = W.claude_surface(entry.get("entrypoint"), entry.get("promptSource"), entry.get("userType"))
    turn_index = entry.get("turnIndex") or w.turn_index
    turn_id = w.turn_id or (f"{w.session_id}:turn:{turn_index}" if turn_index else None)

    # --- prompt
    pattrs = {"promptId": entry.get("promptId"), "turnIndex": entry.get("turnIndex"), "promptIndex": entry.get("promptIndex"),
              "entrypoint": entry.get("entrypoint"), "promptSource": entry.get("promptSource"), "turnOrigin": entry.get("turnOrigin"),
              "surface": surface, "permissionMode": entry.get("permissionMode"), "version": entry.get("version"),
              "chars": len(entry.get("text") or "")}
    if parsed["metas"]:
        pattrs["meta_injections"] = [{"chars": m["chars"], "head": scrub(m["head"])} for m in parsed["metas"][:10]]
    if parsed["prompt_hooks"]:
        pattrs["prompt_hooks"] = parsed["prompt_hooks"][:20]
    text = entry.get("text") or ""
    frag.spans.append(Span(id=Ids.PROMPT, kind="prompt", component=CLI, name="prompt",
                           summary=f"typed prompt ({len(text)} chars, {entry.get('promptSource')})" if entry.get("promptSource") == "typed"
                           else f"{entry.get('promptSource')} prompt ({len(text)} chars)",
                           phase="prompt_submit", t0=t0, t1=None, parent=None,
                           refs={"invocation_id": w.prompt_invocation_id} if w.prompt_invocation_id else {},
                           attrs={k: v for k, v in pattrs.items() if v is not None},
                           payload=frag.artifact(prof_text(ctx, text), limit=FULL_LIMIT), evidence=[SOURCE_ID]))

    # --- context
    _build_contexts(ctx, frag, parsed, seen)
    _build_client_hooks(ctx, frag, parsed)

    # --- llm
    for c in calls:
        frag.spans.append(_llm_span(ctx, c, len(calls)))
    if calls:
        _add_link(frag, seen, Ids.PROMPT, Ids.llm(calls[0]["n"]), "feeds")

    # --- tools
    n_calls = len(calls)
    for tid, t in tools.items():
        _tool_span(ctx, frag, t, t0, lim)
        _add_link(frag, seen, Ids.llm(t["call_n"]), Ids.tool(tid), "calls")
        nxt = parsed["result_calls"].get(tid)
        if nxt and nxt <= n_calls:
            _add_link(frag, seen, Ids.tool(tid), Ids.llm(nxt), "feeds")

    # --- subagent sidechains: their tool calls become tool spans (the assembler hangs them under the SubagentStart
    # hook of the same agent id); their model calls stay gateway rows (attributed there by agent id)
    subs = subagent_files(parsed["path"], entry.get("promptId"))
    sub_facts = []
    sub_tools = sub_late = 0
    for sub in subs:
        sc = sidechain_tools(sub)
        extra = {"subagent": True, "agent_id": sub["agent_id"], "agent_type": sub.get("agent_type")}
        for t in sc["tools"].values():
            if t["t0"] is not None and w.t_end and t["t0"] > w.t_end:
                sub_late += 1          # background subagents outlive the turn; the waybill stops at t_end
                continue
            _tool_span(ctx, frag, t, sc["first"] or t0, lim, extra=extra)
            sub_tools += 1
        sub_facts.append({"agent_id": sub["agent_id"], "agent_type": sub.get("agent_type"),
                          "description": scrub(str(sub.get("description") or ""))[:200] or None,
                          "first": sc["first"], "last": sc["last"], "calls": sc["calls"], "tools": len(sc["tools"]),
                          "file": sub["rel"]})
    if subs:
        listing = "; ".join(f"{s['rel']}" + (f" [{s['agent_type']}]" if s.get("agent_type") else "") +
                            (f" {s['description']!r}" if s.get("description") else "") for s in subs[:12])
        if len(subs) > 12:
            listing += f"; +{len(subs) - 12} more"
        frag.gaps.append(Gap(CLI, f"{len(subs)} subagent sidechain(s): tool calls expanded, model calls only as gateway rows",
                             f"{sub_tools} subagent tool call(s) are tool spans"
                             + (f" ({sub_late} more ran after the window closed and are not included)" if sub_late else "")
                             + "; the subagents' own model calls appear as gateway llm spans with attrs.agent_id. "
                             f"files: {scrub(listing)}", "info"))
        frag.facts["subagents"] = sub_facts

    # --- turn
    td, shs = info["turn_duration"], info["stop_hook_summary"]
    t_end = (td or {}).get("t") or (shs or {}).get("t") or parsed["last_ts"] or t0
    first_req = next((c["requested"] for c in calls if c["requested"]), None)
    last_served = next((c["served"] for c in reversed(calls) if c["served"]), None)
    tattrs: dict[str, Any] = {"duration_ms": (td or {}).get("duration_ms"),
                              "message_count": (td or {}).get("message_count"),
                              "pending_workflows": (td or {}).get("pending_workflows"),
                              "llm_calls": n_calls, "tool_calls": len(tools), "subagents": len(subs),
                              "compactions": info["compactions"], "api_errors": info["api_errors"],
                              "stop_hooks": shs, "has_turn_duration": td is not None}
    if td is None:
        tattrs["duration_ms"] = round(t_end - t0) if t_end and t0 else None
        tattrs["duration_estimated"] = True
    frag.spans.append(Span(id=Ids.TURN, kind="turn", component=CLI, name="turn",
                           summary=f"turn {turn_index or '?'}: {n_calls} model call(s), {len(tools)} tool call(s), {fmt_dur(tattrs['duration_ms'])}"
                           + (f", {len(subs)} subagent(s)" if subs else ""),
                           phase="turn_end", t0=t0, t1=t_end, sync=None, parent=None,
                           attrs={k: v for k, v in tattrs.items() if v is not None}, evidence=[SOURCE_ID]))

    frag.facts.update({k: v for k, v in {
        "turn_id": turn_id, "turn_index": turn_index, "model_requested": first_req, "model_served": last_served,
        "surface": surface, "project": os.path.basename((entry.get("cwd") or "").rstrip("/")) or None,
        "cwd": entry.get("cwd"), "prompt_text": text, "transcript_turn_duration_ms": (td or {}).get("duration_ms"),
        "subagent_count": len(subs),
    }.items() if v is not None})
    if td is None:
        frag.gaps.append(Gap(CLI, "transcript has no turn_duration entry for this turn",
                             "headless (-p) sessions and in-progress turns write only stop_hook_summary; the turn end is estimated", "info", Ids.TURN))
