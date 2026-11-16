"""Codex transcript collector (source 'transcript').

Slices the rollout JSONL EXACTLY by the `thread_turns` byte offsets (thread_history_1.sqlite) and emits:
prompt, context (hook developer messages, split by handler marker), llm (one per token_usage_record, with the
OpenAI response_id as client_request), tool (function_call / custom_tool_call / web_search_call by call_id) and turn
(task_started .. task_complete). Codex-native bootstrap messages (memory instructions, AGENTS.md, environment)
are not hook output and are skipped.

Read-only. Stdlib only. `codex_llm_calls` is shared with the gateway collector.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from ..model import Ctx, Fragment, Gap, Ids, Link, Source, Span, TurnWindow, iso, ms, scrub, tilde
from .. import window as W
from .transcript_claude import (GATEWAY, HOOKHUB, FULL_LIMIT, _add_link, _build_contexts, _limit, _tool_brief,
                                fmt_dur, fmt_tokens, memoised_parse, prof_text, split_context)

SOURCE_ID = "transcript"
SURFACE_COMPONENT = {"codex-cli": "ext:codex-cli", "codex-exec": "ext:codex-exec", "codex-desktop": "ext:codex-desktop"}
SURFACE_NAME = {"codex-cli": "Codex CLI", "codex-exec": "Codex exec (headless)", "codex-desktop": "Codex Desktop"}
_BOOTSTRAP_USER = ("# AGENTS.md instructions", "<environment_context>", "<user_instructions>", "<permissions instructions>")
_EXIT = re.compile(r"(?:Process exited with code|Exit code:)\s*(-?\d+)")


def _msg_text(payload: dict[str, Any]) -> str:
    parts = []
    for b in payload.get("content") or []:
        if isinstance(b, dict):
            parts.append(str(b.get("text") or ""))
    return "\n".join(parts)


def _usage(u: dict[str, Any]) -> dict[str, int]:
    keys = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens", "reasoning_output_tokens")
    return {k: int(u.get(k) or 0) for k in keys}


def _slice(window: TurnWindow) -> tuple[str, dict[str, Any], int | None]:
    path = window.transcript_path
    thread = None
    if not path:
        thread = W.codex_thread(window.session_id)
        path = (thread or {}).get("rollout_path")
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"no Codex rollout for session {window.session_id}")
    row, idx = W.codex_turn(window.session_id, path, turn_id=window.turn_id,
                            near_ms=None if window.turn_id else window.t0 + 1500, turn_index=window.turn_index)
    if row is None:
        raise LookupError(f"no turn found in rollout {path}")
    return path, row, idx


def parse_turn(window: TurnWindow) -> dict[str, Any]:
    """Memoised per (rollout path + mtime + size, turn): the transcript and gateway collectors share one parse."""
    path = window.transcript_path
    if not path:
        th = W.codex_thread(window.session_id)
        path = (th or {}).get("rollout_path")
    return memoised_parse(path, window, ("codex",), lambda: _parse_turn(window))


def _parse_turn(window: TurnWindow) -> dict[str, Any]:
    path, row, idx = _slice(window)
    start = int(row.get("rollout_byte_offset") or 0)
    end = row.get("rollout_end_byte_offset")
    end = int(end) if end else None

    out: dict[str, Any] = {"path": path, "row": row, "index": idx, "turn_id": row.get("turn_id"), "records": [],
                           "tools": {}, "contexts": [], "task_started": None, "task_complete": None, "model": None,
                           "effort": None, "cwd": None, "prompt": None, "bootstrap_dev_chars": 0, "last_ts": None,
                           "user_ts": None, "native_ids": {}}
    tools: dict[str, dict[str, Any]] = out["tools"]
    items: dict[str, dict[str, Any]] = {}      # item_completed payloads by item id (call_id for exec/file changes)
    last_input_ts: float | None = None
    prev_rec_ts: float | None = None
    user_seen = False
    pending_dev: list[dict[str, Any]] = []

    for _ln, _off, d in W.iter_jsonl(path, start, end):
        ts = ms(d.get("timestamp"))
        if ts:
            out["last_ts"] = ts
        typ = d.get("type")
        p = d.get("payload") if isinstance(d.get("payload"), dict) else {}
        pt = p.get("type")
        if typ == "turn_context":
            out["model"] = out["model"] or p.get("model")
            out["effort"] = out["effort"] or p.get("effort")
            out["cwd"] = out["cwd"] or p.get("cwd")
        elif typ == "event_msg":
            if pt == "task_started":
                out["task_started"] = ts
                out["started_at_s"] = p.get("started_at")
                out["trigger"] = (p.get("turn_attribution") or {}).get("turn_trigger")
            elif pt == "task_complete":
                out["task_complete"] = {"t": ts, "duration_ms": p.get("duration_ms"), "ttft_ms": p.get("time_to_first_token_ms"),
                                        "completed_at": p.get("completed_at")}
            elif pt == "item_completed":
                it = p.get("item") if isinstance(p.get("item"), dict) else {}
                itype = it.get("type")
                if itype == "UserMessage" and out["prompt"] is None:
                    out["prompt"] = "\n".join(str(c.get("text") or "") for c in it.get("content") or [] if isinstance(c, dict))
                    out["user_ts"] = ts
                elif itype in ("CommandExecution", "FileChange", "WebSearch", "McpToolCall"):
                    items[str(it.get("id"))] = {"item": it, "t": ts, "started_ms": p.get("started_at_ms"), "completed_ms": p.get("completed_at_ms")}
        elif typ == "token_usage_record":
            u = _usage(p.get("usage") if isinstance(p.get("usage"), dict) else {})
            n = len(out["records"]) + 1
            t0 = last_input_ts if last_input_ts is not None else prev_rec_ts
            out["records"].append({"n": n, "t": ts, "t0": t0, "response_id": p.get("response_id"), "usage": u})
            prev_rec_ts = ts
            last_input_ts = None
        elif typ == "response_item":
            if pt == "message":
                role = p.get("role")
                text = _msg_text(p)
                if role == "developer":
                    segs = split_context(text)
                    if segs and any(s["handler"] != "unknown" for s in segs):
                        out["contexts"].append({"t": ts, "hook_event": None, "tool_use_id": None, "text": text, "elements": 1,
                                                "_before_user": not user_seen})
                    else:
                        out["bootstrap_dev_chars"] += len(text)
                    last_input_ts = ts
                elif role == "user":
                    if text.lstrip().startswith(_BOOTSTRAP_USER):
                        pass
                    else:
                        user_seen = True
                        if out["prompt"] is None:
                            out["prompt"] = text
                        out["user_ts"] = out["user_ts"] or ts
                        last_input_ts = ts
            elif pt in ("function_call", "custom_tool_call"):
                cid = p.get("call_id")
                raw = p.get("arguments") if pt == "function_call" else p.get("input")
                args: Any = raw
                if isinstance(raw, str):
                    try:
                        args = json.loads(raw)
                    except ValueError:
                        args = raw
                tools[cid] = {"id": cid, "name": p.get("name"), "input": args, "raw_input": raw, "t0": ts, "t1": None,
                              "call_n": len(out["records"]) + 1, "result": None, "exit_code": None, "kind": pt, "next_n": None}
            elif pt in ("function_call_output", "custom_tool_call_output"):
                t = tools.get(p.get("call_id"))
                if t is not None:
                    o = p.get("output")
                    t["result"] = o if isinstance(o, str) else json.dumps(o, ensure_ascii=False, default=str)
                    t["t1"] = ts
                    t["next_n"] = len(out["records"]) + 1
                    m = _EXIT.search(t["result"][:400])
                    if m:
                        t["exit_code"] = int(m.group(1))
                last_input_ts = ts
            elif pt == "web_search_call":
                cid = p.get("id")
                tools[cid] = {"id": cid, "name": "web_search", "input": p.get("action"), "raw_input": None, "t0": ts, "t1": ts,
                              "call_n": len(out["records"]) + 1, "result": None, "exit_code": None, "kind": pt, "next_n": None}

    # enrich tool timing / results from item_completed (call_id == item id for exec & patches; ws_ for searches)
    for cid, t in tools.items():
        rec = items.get(cid)
        if not rec:
            continue
        it = rec["item"]
        # The OUTER span is function_call .. function_call_output (what the model waited for). The item's
        # started/completed are the inner exec run: a 0 ms 'tool' came from using them as the span (finding 11).
        ex0 = float(rec["started_ms"]) if rec.get("started_ms") else None
        ex1 = float(rec["completed_ms"]) if rec.get("completed_ms") else None
        if ex0 is not None or ex1 is not None:
            t["exec"] = {"t0": ex0, "t1": ex1}
        if t["t1"] is None:       # no function_call_output (still running / interrupted): fall back to the item
            t["t1"] = ex1 if ex1 is not None else rec["t"]
        else:                      # outer span always contains the inner run
            if ex0 is not None and t["t0"] is not None:
                t["t0"] = min(t["t0"], ex0)
            if ex1 is not None:
                t["t1"] = max(t["t1"], ex1)
        if t["exit_code"] is None and isinstance(it.get("exit_code"), int):
            t["exit_code"] = it["exit_code"]
        dur = it.get("duration")
        if isinstance(dur, dict):
            t["duration_ms"] = round((dur.get("secs") or 0) * 1000 + (dur.get("nanos") or 0) / 1e6, 1)
        t["item_type"] = it.get("type")
        t["wall_time_ms"] = _wall_time_ms(t.get("result"))
    return out


_WALL = re.compile(r"Wall time:\s*([\d.]+)\s*seconds?", re.I)


def _wall_time_ms(result: str | None) -> float | None:
    """exec_command output carries 'Wall time: 0.0 seconds': the inner run, not the outer tool call."""
    m = _WALL.search((result or "")[:600])
    return round(float(m.group(1)) * 1000.0, 1) if m else None


_SKILL_BLOCK = re.compile(r"<skill>\s*<name>([^<]+)</name>(.*?)</skill>", re.S)
_COMMAND_NAME = re.compile(r"<command-name>\s*([^<]+?)\s*</command-name>")
PROMPT_INJECTION_MIN_CHARS = 500


def prompt_injections(text: str) -> list[dict[str, Any]]:
    """Large skill / slash-command expansions the CLI attached to the prompt text (finding 20): the model saw them as
    part of the user message, so they are context, not what the user typed."""
    out: list[dict[str, Any]] = []
    for m in _SKILL_BLOCK.finditer(text or ""):
        out.append({"kind": "skill", "name": m.group(1).strip(), "chars": len(m.group(0)), "text": m.group(0)})
    cm = _COMMAND_NAME.search(text or "")
    if cm:
        out.append({"kind": "command", "name": cm.group(1).strip(), "chars": len(text), "text": text})
    return [i for i in out if i["chars"] >= PROMPT_INJECTION_MIN_CHARS]


def codex_llm_calls(window: TurnWindow) -> list[dict[str, Any]]:
    parsed = parse_turn(window)
    calls = []
    for r in parsed["records"]:
        u = r["usage"]
        calls.append({"source": "main", "n": r["n"], "agent_id": None, "agent_type": None, "input_tokens": u["input_tokens"],
                      "output_tokens": u["output_tokens"], "t0": r["t0"], "t1": r["t"], "requested_model": parsed["model"],
                      "served_model": None, "client_request": r["response_id"], "query_source": "codex"})
    return calls


def collect(ctx: Ctx) -> Fragment:
    t_start = time.monotonic()
    w = ctx.window
    src = Source(id=SOURCE_ID, kind="jsonl", locator=tilde(w.transcript_path) or f"~/.codex/sessions/**/rollout-*-{w.session_id}.jsonl")
    frag = Fragment(source=src)
    try:
        _collect(ctx, frag)
    except Exception as e:  # noqa: BLE001 - fail soft
        src.status = "error"
        src.error = f"{type(e).__name__}: {e}"
        frag.gaps.append(Gap(SURFACE_COMPONENT.get(w.surface, "ext:codex-cli"), "Codex rollout could not be read", f"{type(e).__name__}: {e}", "warn"))
        frag.spans.clear()
        frag.links.clear()
    src.items = len(frag.spans)
    if src.status == "ok" and not frag.spans:
        src.status = "empty"
    src.ms = round((time.monotonic() - t_start) * 1000.0, 1)
    return frag


def _collect(ctx: Ctx, frag: Fragment) -> None:
    w = ctx.window
    lim = _limit(ctx)
    parsed = parse_turn(w)
    surface = w.surface if w.surface in SURFACE_COMPONENT else "codex-cli"
    cli = SURFACE_COMPONENT[surface]
    frag.component(cli, SURFACE_NAME[surface], "cli")
    frag.component(GATEWAY, "AutomaticAI gateway", "service")
    frag.component(HOOKHUB, "hook-hub", "handler-host")
    seen: set[tuple[str, str, str]] = set()
    records, tools = parsed["records"], parsed["tools"]
    t0 = w.t0 or parsed["task_started"] or parsed["user_ts"] or 0.0

    # --- contexts (hook developer messages): SessionStart before the user message, UserPromptSubmit after it
    for c in parsed["contexts"]:
        text = c["text"]
        is_start = c.pop("_before_user", False) or "hindsight:briefing" in text
        c["hook_event"] = "SessionStart" if is_start and "⚡ REMINDER" not in text else "UserPromptSubmit"
    _build_contexts(ctx, frag, {"contexts": parsed["contexts"]}, seen)

    # --- prompt
    text = parsed["prompt"] if parsed["prompt"] is not None else (w.prompt_text or "")
    pattrs = {"surface": surface, "turn_trigger": parsed.get("trigger"), "chars": len(text), "model": parsed["model"],
              "effort": parsed["effort"], "user_message_t": parsed["user_ts"], "turnIndex": parsed["index"]}
    # the prompt starts when the user message was written (the UPS / prompt-text timestamp), not at the window start,
    # which for codex exec is the session start (finding 20)
    prompt_t0 = parsed["user_ts"] if parsed["user_ts"] is not None and parsed["user_ts"] >= t0 else t0
    frag.spans.append(Span(id=Ids.PROMPT, kind="prompt", component=cli, name="prompt",
                           summary=f"prompt ({len(text)} chars, {parsed.get('trigger') or surface})", phase="prompt_submit",
                           t0=prompt_t0, t1=None, refs={"invocation_id": w.prompt_invocation_id} if w.prompt_invocation_id else {},
                           attrs={k: v for k, v in pattrs.items() if v is not None},
                           payload=frag.artifact(prof_text(ctx, text), limit=FULL_LIMIT), evidence=[SOURCE_ID]))

    for inj in prompt_injections(text):
        sid = f"context:prompt:{inj['kind']}:{inj['name']}"
        frag.spans.append(Span(
            id=sid, kind="context", component=cli, name=f"{inj['kind']} {inj['name']}",
            summary=f"{inj['kind']} {inj['name']} attached to the prompt: {fmt_tokens(inj['chars'])} chars the user did not type",
            phase="prompt_submit", t0=prompt_t0, t1=None, sync=True, parent=Ids.PROMPT,
            attrs={"kind": inj["kind"], "name": inj["name"], "chars": inj["chars"], "source": "prompt text"},
            payload=frag.artifact(prof_text(ctx, inj["text"]), limit=lim), evidence=[SOURCE_ID]))
        _add_link(frag, seen, Ids.PROMPT, sid, "injects")

    # --- llm
    n_tools_by_call: dict[int, int] = {}
    for t in tools.values():
        n_tools_by_call[t["call_n"]] = n_tools_by_call.get(t["call_n"], 0) + 1
    for r in records:
        u = r["usage"]
        tin, tout = u["input_tokens"], u["output_tokens"]
        a0 = r["t0"] if r["t0"] is not None else r["t"]
        dur = (r["t"] - a0) if (r["t"] is not None and a0 is not None) else None
        cached = u["cached_input_tokens"]
        n_tc = n_tools_by_call.get(r["n"], 0)
        summary = (f"model call {r['n']} via {parsed['model'] or '?'}: {fmt_tokens(tin)} in"
                   + (f" ({fmt_tokens(cached)} cached)" if cached else "") + f" / {fmt_tokens(tout)} out, {fmt_dur(dur)}")
        frag.spans.append(Span(
            id=Ids.llm(r["n"]), kind="llm", component=GATEWAY, name=f"model call {r['n']}", summary=summary, phase="model_call",
            t0=a0 if a0 is not None else t0, t1=r["t"], sync=True, parent=Ids.TURN,
            refs={"client_request": r["response_id"]},
            attrs={"requested_model": parsed["model"], "served_model": None,
                   "usage": {**u, "uncached_input_tokens": max(0, tin - cached)}, "tokens_in": tin, "tokens_out": tout,
                   "input_tokens": tin, "output_tokens": tout, "client_request": r["response_id"], "effort": parsed["effort"],
                   "stop_reason": "tool_use" if n_tc else "end_turn", "tool_calls": n_tc, "query_source": "codex"},
            evidence=[SOURCE_ID]))
    if records:
        _add_link(frag, seen, Ids.PROMPT, Ids.llm(records[0]["n"]), "feeds")

    # --- tools
    for cid, t in tools.items():
        inp = t["input"]
        in_text = t["raw_input"] if isinstance(t["raw_input"], str) else json.dumps(inp, ensure_ascii=False, default=str)
        status, reason = "ok", None
        if t["kind"] != "web_search_call":
            if t["t1"] is None:
                status = "pending"
            elif t["exit_code"] not in (None, 0):
                status, reason = "failed", f"exit code {t['exit_code']}"
        brief = _tool_brief(t["name"], inp if isinstance(inp, dict) else {"input": inp if isinstance(inp, str) else ""})
        if isinstance(inp, dict) and isinstance(inp.get("cmd"), str):
            brief = scrub(inp["cmd"].strip().replace("\n", " "))[:90]
        elif isinstance(inp, dict) and isinstance(inp.get("queries"), list) and inp["queries"]:
            brief = scrub(str(inp["queries"][0]))[:90]
        elif t["name"] == "apply_patch" and isinstance(inp, str):
            m = re.search(r"\*\*\* (?:Add|Update|Delete) File: (\S+)", inp)
            brief = tilde(m.group(1)) if m else "patch"
        dur = (t["t1"] - t["t0"]) if (t["t1"] and t["t0"]) else None
        attrs: dict[str, Any] = {"name": t["name"], "tool_use_id": cid, "llm": t["call_n"], "kind": t["kind"],
                                 "input_artifact": frag.artifact(prof_text(ctx, in_text), limit=lim)}
        if t["exit_code"] is not None:
            attrs["exit_code"] = t["exit_code"]
        if t.get("item_type"):
            attrs["item_type"] = t["item_type"]
        ex = t.get("exec") or {}
        if ex.get("t0") is not None and ex.get("t1") is not None:
            attrs["exec_ms"] = round(ex["t1"] - ex["t0"], 1)     # the inner run, inside the outer span
            attrs["exec_start_offset_ms"] = round(ex["t0"] - t["t0"], 1)
        if t.get("wall_time_ms") is not None:
            attrs["exec_wall_ms"] = t["wall_time_ms"]
        payload = None
        if t["result"] is not None:
            payload = frag.artifact(prof_text(ctx, t["result"]), limit=lim)
            attrs["result_artifact"] = payload
            attrs["result_chars"] = len(t["result"])
        frag.spans.append(Span(id=Ids.tool(cid), kind="tool", component=cli, name=t["name"] or "tool",
                               summary=f"{t['name']}: {brief}" + (f" ({fmt_dur(dur)})" if dur is not None else " (no output recorded)"),
                               phase="tool", t0=t["t0"] or t0, t1=t["t1"], status=status, reason=reason, sync=True, parent=Ids.TURN,
                               refs={"tool_use_id": cid}, attrs=attrs, payload=payload, evidence=[SOURCE_ID]))
        _add_link(frag, seen, Ids.llm(t["call_n"]), Ids.tool(cid), "calls")
        nn = t.get("next_n") or (t["call_n"] + 1 if t["kind"] == "web_search_call" else None)
        if nn and nn <= len(records):
            _add_link(frag, seen, Ids.tool(cid), Ids.llm(nn), "feeds")

    # --- turn
    tc = parsed["task_complete"]
    t_end = (tc or {}).get("t") or parsed["last_ts"] or t0
    tattrs: dict[str, Any] = {"duration_ms": (tc or {}).get("duration_ms"), "time_to_first_token_ms": (tc or {}).get("ttft_ms"),
                              "llm_calls": len(records), "tool_calls": len(tools), "native_turn_id": parsed["turn_id"],
                              "status": parsed["row"].get("status"), "bootstrap_developer_chars": parsed["bootstrap_dev_chars"]}
    if tc is None:
        tattrs["duration_ms"] = round(t_end - t0) if t_end and t0 else None
        tattrs["duration_estimated"] = True
    frag.spans.append(Span(id=Ids.TURN, kind="turn", component=cli, name="turn",
                           summary=f"turn {parsed['index'] or '?'}: {len(records)} model call(s), {len(tools)} tool call(s), {fmt_dur(tattrs['duration_ms'])}",
                           phase="turn_end", t0=t0, t1=t_end, status="ok" if tc else "pending", parent=None,
                           attrs={k: v for k, v in tattrs.items() if v is not None}, evidence=[SOURCE_ID]))
    cwd = parsed["cwd"] or w.cwd
    frag.facts.update({k: v for k, v in {
        "turn_id": parsed["turn_id"], "turn_index": parsed["index"], "model_requested": parsed["model"], "model_served": None,
        "surface": surface, "project": os.path.basename((cwd or "").rstrip("/")) or None, "cwd": cwd, "prompt_text": text,
        "transcript_turn_duration_ms": (tc or {}).get("duration_ms"),
    }.items() if v is not None})
    if not records:
        frag.gaps.append(Gap(cli, "no token_usage_record in the turn slice", "the model call has not completed yet, or the rollout predates token records", "info", Ids.TURN))
