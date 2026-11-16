"""Resolve (session, turn) -> TurnWindow (SPEC section 4, `window.py`).

Read-only. Sources, in order of preference:
  1. hook-hub receipts (`invocations`: UserPromptSubmit / Stop rows for the session), ~4 days retention;
  2. Candystore turn.started / turn.completed (GET /sessions/<sid>), durable;
  3. the transcript itself (Claude user entries with promptSource / Codex thread_turns).

t0 is the submit instant: min(prompt receipt, transcript user entry); for Codex also the rollout
`task_started` (Codex opens the turn, runs the UserPromptSubmit hooks, then persists the user message).
t_end = turn end (Stop) + settle_ms.

The helpers (`claude_transcript_path`, `claude_find_prompt`, `codex_thread`, `codex_turn`, `hook_invocations`,
`nearest_invocation`) are shared by the transcript collectors so every source slices the same turn.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
import urllib.request
from pathlib import Path
from typing import Any, Iterator

from .model import TurnWindow, iso, ms, now_ms

PROMPT_NATIVES = ("UserPromptSubmit",)
END_NATIVES = ("Stop", "StopFailure")

_SID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:_.\-]{0,127}$")


class WindowError(Exception):
    """The turn could not be resolved from any source."""


# ---------- locations (env overrides exist for tests) ----------

def receipts_path() -> str:
    return os.environ.get("WAYBILL_RECEIPTS") or os.path.expanduser("~/.local/state/33god/hook-hub/receipts.sqlite3")


def claude_projects_dir() -> str:
    return os.environ.get("WAYBILL_CLAUDE_PROJECTS") or os.path.expanduser("~/.claude/projects")


def codex_home() -> str:
    return os.environ.get("WAYBILL_CODEX_HOME") or os.path.expanduser("~/.codex")


def candystore_url() -> str:
    return (os.environ.get("WAYBILL_CANDYSTORE_URL") or "http://127.0.0.1:8683").rstrip("/")


def valid_session_id(sid: str | None) -> bool:
    return bool(sid) and bool(_SID_RE.match(str(sid)))


def ro_connect(path: str, timeout: float = 5.0) -> sqlite3.Connection:
    """Open a SQLite file strictly read-only (URI mode=ro). Raises when the file does not exist."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=timeout)
    con.row_factory = sqlite3.Row
    return con


def iso_z(epoch_ms: float) -> str:
    """Receipt timestamp format (ISO, ms, Z) so that string comparison orders correctly."""
    return iso(epoch_ms) or ""


# ---------- hook-hub receipts ----------

def hook_invocations(session_id: str, natives: tuple[str, ...] | None = None,
                     t0_ms: float | None = None, t1_ms: float | None = None) -> list[dict[str, Any]]:
    """Invocations of one session (optionally filtered by native name and received_at window), ascending."""
    sql = ("select invocation_id, cli, native, role, event_type, session_id, identity_kind, received_at, "
           "updated_at, status from invocations where session_id = ?")
    args: list[Any] = [session_id]
    if natives:
        sql += " and native in (%s)" % ",".join("?" * len(natives))
        args += list(natives)
    if t0_ms is not None:
        sql += " and received_at >= ?"
        args.append(iso_z(t0_ms))
    if t1_ms is not None:
        sql += " and received_at <= ?"
        args.append(iso_z(t1_ms))
    sql += " order by received_at"
    with ro_connect(receipts_path()) as con:
        rows = [dict(r) for r in con.execute(sql, args)]
    for r in rows:
        r["received_ms"] = ms(r["received_at"])
        r["updated_ms"] = ms(r["updated_at"])
    return rows


def nearest_invocation(session_id: str, native: str, at_ms: float, before_ms: float = 120000.0) -> dict[str, Any] | None:
    """The latest invocation of `native` for the session received at or before `at_ms` (within before_ms)."""
    try:
        rows = hook_invocations(session_id, (native,), at_ms - before_ms, at_ms + 50)
    except (OSError, sqlite3.Error):
        return None
    return rows[-1] if rows else None


def latest_prompt_after(epoch_ms: float, cli: str | None = None) -> tuple[str, str, float] | None:
    """Live mode: the most recent UserPromptSubmit receipt received strictly after `epoch_ms`.

    Returns (session_id, invocation_id, received_ms) or None. Rows without a session id are ignored.
    """
    sql = ("select invocation_id, session_id, received_at from invocations where native in (%s) "
           "and received_at > ? and session_id is not null and session_id != ''" % ",".join("?" * len(PROMPT_NATIVES)))
    args: list[Any] = list(PROMPT_NATIVES) + [iso_z(epoch_ms)]
    if cli:
        sql += " and cli = ?"
        args.append(cli)
    sql += " order by received_at desc limit 1"
    try:
        with ro_connect(receipts_path()) as con:
            row = con.execute(sql, args).fetchone()
    except (OSError, sqlite3.Error):
        return None
    if not row:
        return None
    return row["session_id"], row["invocation_id"], ms(row["received_at"]) or 0.0


def _latest_prompt_any(cli: str | None, at_ms: float | None) -> dict[str, Any] | None:
    sql = ("select invocation_id, cli, session_id, received_at from invocations where native in (%s) "
           "and session_id is not null and session_id != ''" % ",".join("?" * len(PROMPT_NATIVES)))
    args: list[Any] = list(PROMPT_NATIVES)
    if cli:
        sql += " and cli = ?"
        args.append(cli)
    if at_ms is not None:
        sql += " and received_at <= ?"
        args.append(iso_z(at_ms + 0.5))
    sql += " order by received_at desc limit 1"
    with ro_connect(receipts_path()) as con:
        row = con.execute(sql, args).fetchone()
    return dict(row) if row else None


# ---------- Claude transcript ----------

def claude_transcript_path(session_id: str) -> str | None:
    """Glob ~/.claude/projects/*/<sid>.jsonl (the dir is the LAUNCH dir slug, not the cwd)."""
    if not valid_session_id(session_id):
        return None
    hits = glob.glob(os.path.join(glob.escape(claude_projects_dir()), "*", glob.escape(session_id) + ".jsonl"))
    if not hits:
        return None
    return max(hits, key=lambda p: os.path.getmtime(p))


def iter_jsonl(path: str, start: int = 0, end: int | None = None,
               skip_prefixes: tuple[bytes, ...] = (b'{"type":"api-request-blob"',)) -> Iterator[tuple[int, int, dict[str, Any]]]:
    """Stream (line_no, byte_offset, entry) from a JSONL file, skipping huge blob lines without parsing them."""
    with open(path, "rb") as fh:
        if start:
            fh.seek(start)
        off = start
        n = 0
        for raw in fh:
            line_off = off
            off += len(raw)
            n += 1
            if end is not None and line_off >= end:
                break
            if not raw.strip() or raw.startswith(skip_prefixes):
                continue
            try:
                entry = json.loads(raw)
            except ValueError:
                continue
            if isinstance(entry, dict):
                yield n, line_off, entry


def claude_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(str(b.get("text") or ""))
            elif isinstance(b, str):
                parts.append(b)
        return "\n".join(parts)
    return ""


def claude_prompts(path: str) -> list[dict[str, Any]]:
    """Every prompt-opening user entry (promptSource set, turnPosition present, main thread), in file order."""
    out: list[dict[str, Any]] = []
    with open(path, "rb") as fh:
        off = 0
        for raw in fh:
            line_off = off
            off += len(raw)
            if b'"promptSource"' not in raw or b'"turnPosition"' not in raw:
                continue
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            if d.get("type") != "user" or not d.get("promptSource") or d.get("isSidechain"):
                continue
            tp = d.get("turnPosition") or {}
            msg = d.get("message") or {}
            out.append({
                "offset": line_off, "uuid": d.get("uuid"), "promptId": d.get("promptId"),
                "ts": ms(d.get("timestamp")), "timestamp": d.get("timestamp"),
                "turnIndex": tp.get("turnIndex"), "promptIndex": tp.get("promptIndex"),
                "promptSource": d.get("promptSource"), "turnOrigin": d.get("turnOrigin"),
                "entrypoint": d.get("entrypoint"), "userType": d.get("userType"), "cwd": d.get("cwd"),
                "text": claude_text(msg.get("content")), "version": d.get("version"),
                "permissionMode": d.get("permissionMode"), "gitBranch": d.get("gitBranch"),
            })
    return out


def claude_find_prompt(path: str, near_ms: float | None = None, turn_index: int | None = None,
                       prompts: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """Pick the user entry that opened the turn.

    Claude writes the entry tens of ms BEFORE the UserPromptSubmit receipt, so with a receipt time the entry
    closest to it (and not after it by more than 5 s) wins; otherwise the entry with turnIndex == N.
    """
    prompts = prompts if prompts is not None else claude_prompts(path)
    if not prompts:
        return None
    if near_ms is not None:
        cands = [p for p in prompts if p["ts"] is not None and p["ts"] <= near_ms + 5000 and p["ts"] >= near_ms - 600000]
        if cands:
            return min(cands, key=lambda p: abs(p["ts"] - near_ms))
    if turn_index is not None:
        same = [p for p in prompts if p.get("turnIndex") == turn_index]
        if same:
            return same[-1]
        if 1 <= turn_index <= len(prompts):
            return prompts[turn_index - 1]
        return None
    return prompts[-1]


def claude_surface(entrypoint: str | None, prompt_source: str | None = None, user_type: str | None = None) -> str:
    ep = (entrypoint or "").lower()
    if ep.startswith("sdk") or (prompt_source or "") == "sdk":
        return "claude-code-headless"
    if ep == "claude-desktop":
        return "claude-desktop"
    return "claude-code"


# ---------- Codex ----------

def codex_surface(originator: str | None, source: str | None = None) -> str:
    o = (originator or "").strip().lower()
    if o in ("codex_exec", "exec", "codex-exec"):
        return "codex-exec"
    if o in ("codex_work_desktop", "codex desktop", "codex_desktop", "codex-desktop") or "desktop" in o:
        return "codex-desktop"
    if o in ("codex-tui", "codex_tui", "cli", "codex_cli_rs", "codex-cli", "tui"):
        return "codex-cli"
    if not o and (source or "") == "exec":
        return "codex-exec"
    return "codex-cli"


def codex_thread(session_id: str) -> dict[str, Any] | None:
    try:
        with ro_connect(os.path.join(codex_home(), "state_5.sqlite")) as con:
            row = con.execute("select id, rollout_path, originator, source, thread_source, cwd, model, "
                              "reasoning_effort, cli_version, created_at_ms, updated_at_ms, title "
                              "from threads where id = ?", (session_id,)).fetchone()
    except (OSError, sqlite3.Error):
        row = None
    if row:
        return dict(row)
    # fall back to the sessions tree (rollout-<ts>-<sid>.jsonl)
    hits = glob.glob(os.path.join(glob.escape(codex_home()), "sessions", "*", "*", "*", "rollout-*-" + glob.escape(session_id) + ".jsonl"))
    if hits:
        return {"id": session_id, "rollout_path": max(hits, key=os.path.getmtime), "originator": None, "source": None}
    return None


def codex_turns(session_id: str) -> list[dict[str, Any]]:
    """thread_turns rows (byte offsets into the rollout), ascending by rollout ordinal."""
    try:
        with ro_connect(os.path.join(codex_home(), "thread_history_1.sqlite")) as con:
            rows = [dict(r) for r in con.execute(
                "select turn_id, rollout_ordinal, rollout_end_ordinal, rollout_byte_offset, rollout_end_byte_offset, "
                "started_at, completed_at, duration_ms, status, first_user_item_id, final_agent_item_id, root_turn_id "
                "from thread_turns where thread_id = ? order by rollout_ordinal", (session_id,))]
    except (OSError, sqlite3.Error):
        return []
    return rows


def codex_scan_turns(rollout_path: str) -> list[dict[str, Any]]:
    """Fallback when thread_history has no row (in-progress turn / lagging projection): scan task_started."""
    turns: list[dict[str, Any]] = []
    with open(rollout_path, "rb") as fh:
        off = 0
        for raw in fh:
            line_off = off
            off += len(raw)
            if b'"task_started"' not in raw and b'"task_complete"' not in raw:
                continue
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            p = d.get("payload") or {}
            if d.get("type") != "event_msg" or not isinstance(p, dict):
                continue
            if p.get("type") == "task_started":
                if turns and turns[-1].get("rollout_end_byte_offset") is None:
                    turns[-1]["rollout_end_byte_offset"] = line_off
                turns.append({"turn_id": p.get("turn_id"), "rollout_byte_offset": line_off, "rollout_end_byte_offset": None,
                              "started_at": p.get("started_at"), "completed_at": None, "status": "in_progress",
                              "rollout_ordinal": d.get("ordinal")})
            elif p.get("type") == "task_complete" and turns and turns[-1]["turn_id"] == p.get("turn_id"):
                turns[-1]["rollout_end_byte_offset"] = off
                turns[-1]["completed_at"] = p.get("completed_at")
                turns[-1]["duration_ms"] = p.get("duration_ms")
                turns[-1]["status"] = "completed"
    return turns


def codex_turn(session_id: str, rollout_path: str | None, turn_id: str | None = None,
               near_ms: float | None = None, turn_index: int | None = None) -> tuple[dict[str, Any] | None, int | None]:
    """Pick the Codex turn (row, 1-based index) by native turn_id, by receipt time, or by index."""
    turns = codex_turns(session_id)
    if (not turns or (turn_id and not any(t["turn_id"] == turn_id for t in turns))) and rollout_path and os.path.exists(rollout_path):
        scanned = codex_scan_turns(rollout_path)
        known = {t["turn_id"] for t in turns}
        turns = turns + [t for t in scanned if t["turn_id"] not in known]
        turns.sort(key=lambda t: t.get("rollout_byte_offset") or 0)
    if not turns:
        return None, None
    if turn_id:
        for i, t in enumerate(turns):
            if t["turn_id"] == turn_id:
                return t, i + 1
    if near_ms is not None:
        near_s = near_ms / 1000.0
        cands = [(i, t) for i, t in enumerate(turns) if t.get("started_at") is not None and t["started_at"] <= near_s + 1]
        if cands:
            i, t = cands[-1]
            return t, i + 1
    if turn_index is not None and 1 <= turn_index <= len(turns):
        return turns[turn_index - 1], turn_index
    return turns[-1], len(turns)


def codex_turn_head(rollout_path: str, turn: dict[str, Any]) -> dict[str, Any]:
    """Cheap facts from the head of a turn slice: task_started ts, cwd/model/effort, the user prompt."""
    out: dict[str, Any] = {}
    start = int(turn.get("rollout_byte_offset") or 0)
    end = turn.get("rollout_end_byte_offset")
    for _, _, d in iter_jsonl(rollout_path, start, int(end) if end else None):
        typ = d.get("type")
        p = d.get("payload") if isinstance(d.get("payload"), dict) else {}
        if typ == "event_msg" and p.get("type") == "task_started" and "task_started_ms" not in out:
            out["task_started_ms"] = ms(d.get("timestamp"))
        elif typ == "turn_context" and "cwd" not in out:
            out["cwd"] = p.get("cwd")
            out["model"] = p.get("model")
            out["effort"] = p.get("effort")
        elif typ == "event_msg" and p.get("type") == "item_completed" and (p.get("item") or {}).get("type") == "UserMessage":
            item = p.get("item") or {}
            texts = [c.get("text", "") for c in item.get("content") or [] if isinstance(c, dict)]
            out["user_ms"] = ms(d.get("timestamp"))
            out["prompt_text"] = "\n".join(texts)
            break
        elif typ in ("token_usage_record",) or (typ == "response_item" and p.get("type") == "function_call"):
            break
    return out


def codex_session_meta(rollout_path: str) -> dict[str, Any]:
    try:
        with open(rollout_path, "rb") as fh:
            first = fh.readline()
        d = json.loads(first)
        if d.get("type") == "session_meta":
            p = d.get("payload") or {}
            return {k: v for k, v in p.items() if k != "base_instructions"}
    except (OSError, ValueError):
        pass
    return {}


# ---------- Candystore fallback ----------

def candystore_turns(session_id: str, timeout: float = 10.0) -> tuple[list[dict[str, Any]], str | None]:
    """[(turn.started event, matching turn.completed or None)] from GET /sessions/<sid>, plus the cli."""
    url = f"{candystore_url()}/sessions/{session_id}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        doc = json.load(resp)
    events = sorted(doc.get("events") or [], key=lambda e: ms(e.get("time")) or 0)
    starts = [e for e in events if e.get("type") == "bloodbank.conversation.turn.started"]
    cli = None
    for e in events:
        actor = e.get("actor") or {}
        if actor.get("cli"):
            cli = actor["cli"]
            break
    turns = []
    for i, s in enumerate(starts):
        t0 = ms(s.get("time")) or 0
        nxt = ms(starts[i + 1].get("time")) if i + 1 < len(starts) else None
        done = None
        for e in events:
            if e.get("type") != "bloodbank.conversation.turn.completed":
                continue
            te = ms(e.get("time")) or 0
            if te >= t0 and (nxt is None or te <= nxt):
                done = e
                break
        turns.append({"started": s, "completed": done, "t0": t0, "t_done": ms(done.get("time")) if done else None})
    return turns, cli


# ---------- resolve ----------

def _pick(items: list[Any], turn: int | None, latest: bool, at_ms: float | None, key) -> tuple[Any, int] | tuple[None, None]:
    if not items:
        return None, None
    if turn is not None:
        if 1 <= turn <= len(items):
            return items[turn - 1], turn
        return None, None
    if at_ms is not None:
        best = None
        for i, it in enumerate(items):
            if (key(it) or 0) <= at_ms + 0.5:
                best = (it, i + 1)
        return best if best else (None, None)
    return items[-1], len(items)


def resolve(session_id: str | None = None, cli: str | None = None, turn: int | None = None, latest: bool = False,
            at: str | None = None, settle_ms: float = 15000) -> TurnWindow:
    """Resolve one prompt turn. Defaults to the latest turn of the session when no selector is given."""
    at_ms = ms(at) if at is not None else None
    if at is not None and at_ms is None:
        raise WindowError(f"cannot parse --at {at!r}")
    notes: list[str] = []

    if not session_id:
        try:
            row = _latest_prompt_any(cli, at_ms)
        except (OSError, sqlite3.Error) as e:
            raise WindowError(f"no session given and hook-hub receipts are unreadable: {e}") from e
        if not row:
            raise WindowError("no session given and no UserPromptSubmit receipt found")
        session_id = row["session_id"]
        cli = cli or row["cli"]
        if at_ms is None:
            latest = True
    if not valid_session_id(session_id):
        raise WindowError(f"invalid session id {session_id!r}")

    prompt_inv: dict[str, Any] | None = None
    stop_inv: dict[str, Any] | None = None
    turn_index: int | None = None
    prompt_ms: float | None = None
    turn_end: float | None = None
    t_done_hint: float | None = None

    # 1. receipts
    receipts: list[dict[str, Any]] = []
    try:
        receipts = hook_invocations(session_id, PROMPT_NATIVES + END_NATIVES)
    except (OSError, sqlite3.Error) as e:
        notes.append(f"receipts unreadable: {e}")
    prompts = [r for r in receipts if r["native"] in PROMPT_NATIVES]
    ends = [r for r in receipts if r["native"] in END_NATIVES]
    if prompts:
        prompt_inv, turn_index = _pick(prompts, turn, latest, at_ms, key=lambda r: r["received_ms"])
    if prompt_inv:
        cli = cli or prompt_inv["cli"]
        prompt_ms = prompt_inv["received_ms"]
        nxt = prompts[turn_index] if turn_index is not None and turn_index < len(prompts) else None
        nxt_ms = nxt["received_ms"] if nxt else None
        for e in ends:
            if e["received_ms"] > prompt_ms and (nxt_ms is None or e["received_ms"] <= nxt_ms):
                stop_inv = e
                break
        if stop_inv:
            turn_end = stop_inv["received_ms"]
        elif nxt_ms is not None:
            turn_end = nxt_ms

    # 2. Candystore fallback
    if prompt_inv is None:
        try:
            cs_turns, cs_cli = candystore_turns(session_id)
        except Exception as e:  # noqa: BLE001 - fail soft, try the transcript next
            cs_turns, cs_cli = [], None
            notes.append(f"candystore unreadable: {e}")
        if cs_turns:
            chosen, turn_index = _pick(cs_turns, turn, latest, at_ms, key=lambda t: t["t0"])
            if chosen:
                cli = cli or cs_cli
                prompt_ms = chosen["t0"]
                t_done_hint = chosen["t_done"]
                if t_done_hint is not None:
                    turn_end = t_done_hint
                else:
                    idx = cs_turns.index(chosen)
                    if idx + 1 < len(cs_turns):
                        turn_end = cs_turns[idx + 1]["t0"]

    # cli inference from the filesystem
    claude_path = None
    thread = None
    if cli in (None, "claude"):
        claude_path = claude_transcript_path(session_id)
        if claude_path and cli is None:
            cli = "claude"
    if cli in (None, "codex"):
        thread = codex_thread(session_id)
        if thread and cli is None:
            cli = "codex"
    if cli is None:
        raise WindowError(f"session {session_id} not found in receipts, Candystore or transcripts ({'; '.join(notes)})")

    window = TurnWindow(cli=cli, surface=cli, session_id=session_id, t0=prompt_ms or 0.0, t_end=0.0,
                        settle_ms=float(settle_ms))
    window.prompt_invocation_id = prompt_inv["invocation_id"] if prompt_inv else None
    window.stop_invocation_id = stop_inv["invocation_id"] if stop_inv else None

    if cli == "claude":
        _resolve_claude(window, claude_path or claude_transcript_path(session_id), prompt_ms, turn_index, turn, latest, at_ms)
    elif cli == "codex":
        _resolve_codex(window, thread or codex_thread(session_id), prompt_ms, turn_index, turn, latest, at_ms)
    else:
        window.surface = cli
        window.turn_index = turn_index

    if window.t0 == 0.0:
        raise WindowError(f"could not place the turn of session {session_id} in time ({'; '.join(notes)})")

    if turn_end is None and getattr(window, "_transcript_end_ms", None):
        turn_end = window._transcript_end_ms  # type: ignore[attr-defined]
    window.turn_end = turn_end
    window.t_end = (turn_end + window.settle_ms) if turn_end is not None else now_ms()
    if hasattr(window, "_transcript_end_ms"):
        delattr(window, "_transcript_end_ms")
    return window


def _resolve_claude(window: TurnWindow, path: str | None, prompt_ms: float | None, turn_index: int | None,
                    turn: int | None, latest: bool, at_ms: float | None) -> None:
    window.transcript_path = path
    window.surface = "claude-code"
    entry = None
    prompts: list[dict[str, Any]] = []
    if path:
        prompts = claude_prompts(path)
        if prompt_ms is not None:
            entry = claude_find_prompt(path, near_ms=prompt_ms, turn_index=turn_index, prompts=prompts)
        else:  # 3. transcript-only fallback
            entry, turn_index = _pick(prompts, turn, latest, at_ms, key=lambda p: p["ts"])
    if entry:
        window.surface = claude_surface(entry.get("entrypoint"), entry.get("promptSource"), entry.get("userType"))
        window.prompt_text = entry.get("text")
        window.cwd = entry.get("cwd")
        if entry.get("turnIndex"):
            turn_index = entry["turnIndex"]
        if entry.get("ts") is not None:
            window.t0 = min(prompt_ms, entry["ts"]) if prompt_ms is not None else entry["ts"]
        if prompt_ms is None:
            # transcript-only: the turn ends at the next prompt entry (the turn_duration is read by the collector)
            later = [p for p in prompts if p["ts"] and entry["ts"] and p["ts"] > entry["ts"]]
            if later:
                window._transcript_end_ms = later[0]["ts"]  # type: ignore[attr-defined]
    elif prompt_ms is not None:
        window.t0 = prompt_ms
    window.turn_index = turn_index
    window.turn_id = f"{window.session_id}:turn:{turn_index}" if turn_index else None


def _resolve_codex(window: TurnWindow, thread: dict[str, Any] | None, prompt_ms: float | None, turn_index: int | None,
                   turn: int | None, latest: bool, at_ms: float | None) -> None:
    path = (thread or {}).get("rollout_path")
    window.transcript_path = path
    meta = codex_session_meta(path) if path and os.path.exists(path) else {}
    window.surface = codex_surface(meta.get("originator") or (thread or {}).get("originator"),
                                   meta.get("source") or (thread or {}).get("source"))
    window.cwd = meta.get("cwd") or (thread or {}).get("cwd")
    row = None
    if path and os.path.exists(path):
        if prompt_ms is not None:
            row, idx = codex_turn(window.session_id, path, near_ms=prompt_ms, turn_index=turn_index)
        else:
            turns = codex_turns(window.session_id) or codex_scan_turns(path)
            row, idx = _pick(turns, turn, latest, at_ms,
                             key=lambda t: (t.get("started_at") or 0) * 1000.0)
        if row:
            turn_index = idx
            head = codex_turn_head(path, row)
            window.turn_id = row.get("turn_id")
            window.prompt_text = head.get("prompt_text")
            window.cwd = head.get("cwd") or window.cwd
            cands = [v for v in (prompt_ms, head.get("user_ms"), head.get("task_started_ms")) if v is not None]
            if cands:
                window.t0 = min(cands)
            if prompt_ms is None and row.get("completed_at"):
                window._transcript_end_ms = float(row["completed_at"]) * 1000.0  # type: ignore[attr-defined]
    if not row and prompt_ms is not None:
        window.t0 = prompt_ms
    window.turn_index = turn_index
