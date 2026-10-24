from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

# The `type` column holds two shapes forever: the historical five-token
# `bloodbank.v1.<domain>.<entity>.<action>` on the ~713k rows already in the
# table, and the current version-free four-token
# `bloodbank.<domain>.<entity>.<action>` on everything published since. Rather
# than key SUMMARIZERS on both spellings of every type -- which doubles the
# table and guarantees the next entry only gets one half -- normalize the
# incoming type ONCE here and key the table on the canonical shape alone.
_VERSION_TOKEN = re.compile(r"^bloodbank\.v[0-9]+\.")

# Renames that survive version-stripping: the entity itself moved. The
# `tool.tool_call.*` lane became `agent.tool.*` with a byte-identical payload
# (verified against live rows: both carry tool_name/tool_call_id/arguments/
# invocation_id/turn_number). Note `tool.tool_call.completed` never existed on
# the bus -- that lane only ever emitted `requested` and `invoked`.
_RENAMED_TYPES = {
    "bloodbank.tool.tool_call.requested": "bloodbank.agent.tool.requested",
    "bloodbank.tool.tool_call.invoked": "bloodbank.agent.tool.invoked",
    "bloodbank.tool.tool_call.completed": "bloodbank.agent.tool.completed",
}


# The LABEL for a row whose directory belongs to no registered project. Used in
# prose (a title) and on a chart axis, never as the value of a `project` field --
# that stays null, so "no project" and a project named "unassigned" cannot be
# confused. Deliberately not "unknown": the project is not unknown, it is
# unassigned -- the repo is simply not in the registry yet (CANDYS-68) or the
# directory is an ephemeral clone (CANDYS-39), and both are actionable.
UNRESOLVED_PROJECT = "unassigned"

# Substituted by summarize() once the resolved slug is known, so a title and its
# own `project` field can never disagree.
_PROJECT_PLACEHOLDER = "\x00project\x00"


def canonical_type(event_type: Any) -> str:
    """Collapse either wire shape onto the canonical version-free type."""
    if not isinstance(event_type, str):
        return ""
    stripped = _VERSION_TOKEN.sub("bloodbank.", event_type, count=1)
    return _RENAMED_TYPES.get(stripped, stripped)


def summarize(
    env: dict[str, Any],
    project: str | None = None,
    provenance: str | None = None,
) -> dict[str, Any]:
    """Render one envelope for display.

    `project` is the row's already-resolved registry slug (query.PROJECT_EXPR).
    It is passed in rather than derived here because the answer depends on the
    PJangler registry, which an envelope cannot see -- and because deriving it
    in two places is precisely the bug this signature exists to prevent: the
    list and the detail pane disagreed about the same event on 399 rows in 7
    days. A caller with no resolved slug (a raw envelope in a test, or
    /events/<id>/summary before the row is read) gets UNRESOLVED_PROJECT rather
    than a second guess.

    `provenance` is the row's class (query.PROVENANCE_EXPR), passed in for the
    same reason: it is derived in SQL so a dot can be clicked to filter and the
    strip can GROUP BY it, and re-deriving it here would be a second definition
    that drifts from the one the filter uses.
    """
    fn = SUMMARIZERS.get(canonical_type(env.get("type", "")), _generic)
    summary = fn(env)
    # Set on EVERY summary, not only the ones whose summarizer happened to
    # mention it. Before, the tool summarizers carried no `project` key at all,
    # so /events reported `james-brennan` for a row whose /summary reported
    # nothing -- a different flavour of the same disagreement, and one that
    # makes the feed's row contract non-uniform (CANDYS-41 needs it present).
    # `project` is DATA and stays nullable: null and a project literally named
    # "unassigned" must remain distinguishable, and the row-level PROJECT_EXPR
    # is nullable too -- so /events and /events/<id>/summary report a
    # byte-identical value for the same row, which is the whole point of this
    # signature. Only the title, which is prose, gets the label.
    summary["project"] = project
    summary["class"] = provenance
    title = summary.get("title")
    if isinstance(title, str) and _PROJECT_PLACEHOLDER in title:
        summary["title"] = title.replace(_PROJECT_PLACEHOLDER, project or UNRESOLVED_PROJECT)
    # Added alongside the per-type keys, not instead of them: EventDetail reads
    # the per-type dict and must keep working with no change at all.
    summary["row"] = row(env, summary, project, provenance)
    return summary


def _fmt_duration(seconds: Any) -> str:
    if seconds is None:
        return "unknown"
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "unknown"

    hours, rem = divmod(max(seconds, 0), 3600)
    minutes, secs = divmod(rem, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def _preview(value: Any, limit: int = 200) -> str | None:
    """One-line, length-bounded rendering of an arbitrary payload field."""
    if value is None or value == "" or value == {} or value == []:
        return None
    if not isinstance(value, str):
        try:
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            value = str(value)
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1] + "\u2026"


def _non_empty_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return value
    return None


def _prompt_text(data: dict[str, Any]) -> str | None:
    """Extract the human or orchestrator prompt across producer dialects.

    Producers do not agree on one slot: Claude Code and Codex CLI populate
    `data.prompt_text`, while Hermes `pre_llm_call` leaves `prompt_text` empty
    and sends `data.payload.extra.user_message`, subagent invocations carry
    `data.payload.child_goal`, and command envelopes carry `context.prompt`.
    """
    for key in ("prompt_text", "prompt", "user_message", "user_input", "user_prompt"):
        found = _non_empty_str(data.get(key))
        if found:
            return found

    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    for key in (
        "prompt_text",
        "prompt",
        "user_message",
        "user_input",
        "user_prompt",
        "child_goal",
    ):
        found = _non_empty_str(payload.get(key))
        if found:
            return found

    extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}
    for key in ("user_message", "prompt_text", "prompt", "user_input", "user_prompt"):
        found = _non_empty_str(extra.get(key))
        if found:
            return found

    history = extra.get("conversation_history")
    if isinstance(history, list):
        for entry in reversed(history):
            if isinstance(entry, dict) and entry.get("role") == "user":
                found = _non_empty_str(entry.get("content"))
                if found:
                    return found

    context = data.get("context") if isinstance(data.get("context"), dict) else {}
    for key in ("prompt", "user_message", "prompt_text"):
        found = _non_empty_str(context.get(key))
        if found:
            return found

    return None


def _reply_text(data: dict[str, Any]) -> str | None:
    """Extract the assistant or subagent reply across producer dialects."""
    for key in ("reply_text", "last_assistant_message", "final_response", "response"):
        found = _non_empty_str(data.get(key))
        if found:
            return found

    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    for key in (
        "reply_text",
        "last_assistant_message",
        "prompt_response",
        "final_response",
        "response",
        "child_summary",
    ):
        found = _non_empty_str(payload.get(key))
        if found:
            return found

    extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}
    for key in ("final_response", "reply_text", "response", "last_assistant_message"):
        found = _non_empty_str(extra.get(key))
        if found:
            return found

    handoff = data.get("handoff") if isinstance(data.get("handoff"), dict) else {}
    found = _non_empty_str(handoff.get("summary"))
    if found:
        return found

    return None


def _dialog_text(data: dict[str, Any]) -> str | None:
    """Extract general dialog, message, or transcription text."""
    for key in ("transcript_text", "text", "message", "content"):
        found = _non_empty_str(data.get(key))
        if found:
            return found
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    for key in ("transcript_text", "text", "message", "content"):
        found = _non_empty_str(payload.get(key))
        if found:
            return found
    return None


def _session_ended(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    actor = env.get("actor") or {}
    cli = actor.get("cli")
    prompt = _prompt_text(data)
    reply = _reply_text(data)
    return {
        "title": f"Session ended - {_PROJECT_PLACEHOLDER} ({cli or 'unknown'})",
        "cli": cli,
        "provider": actor.get("provider"),
        "project": None,
        "duration": _fmt_duration(data.get("duration_seconds")),
        "turns": data.get("total_turns"),
        "tools_used": len(data.get("tools_used") or []),
        "files_modified": data.get("files_modified"),
        "git_commits": data.get("git_commits"),
        "final_status": data.get("final_status"),
        "end_reason": data.get("end_reason"),
        "prompt_preview": _preview(prompt),
        "reply_preview": _preview(reply),
        "working_directory": data.get("working_directory"),
    }


def _session_started(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    actor = env.get("actor") or {}
    prompt = _prompt_text(data)
    return {
        "title": f"Session started - {_PROJECT_PLACEHOLDER}",
        "cli": actor.get("cli"),
        "project": None,
        "prompt_preview": _preview(prompt),
        "working_directory": data.get("working_directory"),
        "git_branch": data.get("git_branch"),
        "git_remote": data.get("git_remote"),
    }


def _turn_index(data: dict[str, Any]) -> Any:
    """turn_index if the producer sent one, else the `<thread>:<n>` suffix."""
    for key in ("turn_index", "turn_number"):
        if data.get(key) is not None:
            return data[key]
    turn_id = data.get("turn_id")
    if isinstance(turn_id, str) and ":" in turn_id:
        tail = turn_id.rsplit(":", 1)[1]
        if tail.isdigit():
            return int(tail)
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    for key in ("turn_index", "turn_number"):
        if payload.get(key) is not None:
            return payload[key]
    extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}
    if extra.get("turn_index") is not None:
        return extra["turn_index"]
    if extra.get("is_first_turn") is True:
        return 1
    return None


def _turn_started(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    actor = env.get("actor") or {}
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}
    index = _turn_index(data)
    prompt = _prompt_text(data)
    return {
        "title": f"Turn started - {index if index is not None else 'unknown'}",
        "session_id": data.get("session_id") or data.get("thread_id"),
        "turn_index": index,
        "model": data.get("model") or actor.get("model") or extra.get("model"),
        "prompt_preview": _preview(prompt),
    }


def _turn_completed(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    actor = env.get("actor") or {}
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else {}
    index = _turn_index(data)
    reply = _reply_text(data)
    prompt = _prompt_text(data)
    reply_length = data.get("reply_length")
    if reply_length is None and isinstance(reply, str):
        reply_length = len(reply)
    return {
        "title": f"Turn completed - {index}" if index is not None else "Turn completed",
        "session_id": data.get("session_id") or data.get("thread_id"),
        "turn_index": index,
        "model": data.get("model") or actor.get("model") or extra.get("model"),
        "status": _tool_status(data),
        "delivered": data.get("delivered"),
        "reply_length": reply_length,
        "reply_preview": _preview(reply),
        "prompt_preview": _preview(prompt),
    }


def _message_appended(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    role = data.get("role") or "message"
    dialog = _dialog_text(data) or _reply_text(data) or _prompt_text(data)
    return {
        "title": f"Message appended ({role})",
        "role": role,
        "session_id": data.get("session_id") or data.get("thread_id"),
        "turn_index": _turn_index(data),
        "message_preview": _preview(dialog),
    }


def _audio_dialog(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    verb = _verb_from_type(env.get("type", ""))
    reply = _reply_text(data)
    transcript = _non_empty_str(data.get("transcript_text")) or _dialog_text(data)
    return {
        "title": f"Audio {verb}",
        "session_id": data.get("session_id") or data.get("memo_id"),
        "status": _tool_status(data),
        "reply_preview": _preview(reply),
        "transcript_preview": _preview(transcript),
    }


def _inbound_message(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    sender = data.get("sender") or data.get("from_number") or data.get("channel")
    msg = _dialog_text(data) or _prompt_text(data)
    return {
        "title": f"Message received - {sender}" if sender else "Message received",
        "sender": sender,
        "channel": data.get("channel") or data.get("platform"),
        "message_preview": _preview(msg),
    }


def _tool_status(data: dict[str, Any]) -> Any:
    """`status` is legacy; live rows carry `outcome`, or a `success` bool."""
    for key in ("status", "outcome"):
        if data.get(key) is not None:
            return data[key]
    success = data.get("success")
    if isinstance(success, bool):
        return "success" if success else "failure"
    return None


def _tool_event(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    tool = data.get("tool_name") or data.get("name") or "tool"
    return {
        "title": f"{tool} - {_verb_from_type(env.get('type', ''))}",
        "tool": tool,
        "status": _tool_status(data),
        "duration": _fmt_duration(data.get("duration_seconds")),
        "input_preview": data.get("input_preview") or _preview(data.get("arguments")),
    }


def _agent_event(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    prompt = _prompt_text(data)
    reply = _reply_text(data)
    return {
        "title": f"Agent invocation - {_verb_from_type(env.get('type', ''))}",
        "agent": (
            data.get("agent")
            or data.get("agent_name")
            or data.get("source_agent_id")
        ),
        "status": data.get("status") or data.get("stop_reason") or _tool_status(data),
        "duration": _fmt_duration(data.get("duration_seconds")),
        "prompt_preview": _preview(prompt),
        "reply_preview": _preview(reply),
        "error": _preview(data.get("error") or data.get("error_message")),
        "invocation_id": data.get("invocation_id"),
    }


def _heartbeat(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    # `source_id` is the schema field name; `producer_id` is the legacy one.
    source = data.get("producer_id") or data.get("source_id") or env.get("producer")
    return {
        "title": f"Heartbeat - {source or 'unknown'}",
        # `or` would mask a legitimate sequence 0, so probe explicitly.
        "tick_seq": (
            data["tick_seq"] if data.get("tick_seq") is not None else data.get("sequence")
        ),
        "producer_id": data.get("producer_id") or data.get("source_id"),
        "service": env.get("service"),
    }


def _generic(env: dict[str, Any]) -> dict[str, Any]:
    actor = env.get("actor") or {}
    return {
        "title": env.get("type", "unknown event"),
        "producer": env.get("producer"),
        "service": env.get("service"),
        "domain": env.get("domain"),
        "cli": actor.get("cli"),
        "project": None,
    }




# ---------------------------------------------------------------------------
# The feed row contract (CANDYS-41).
#
# `summarize()` returns a DIFFERENT dict shape per event type, which is right
# for a detail pane and unusable for a dense fixed-height feed row: a renderer
# cannot lay out fields whose names change with the type. `row()` is the flat,
# always-present projection the feed lays out, added ALONGSIDE the per-type
# dict rather than replacing it -- so the detail pane keeps working untouched.
#
# Every key is present on every event. Optional VALUES are null; optional KEYS
# would put the type-switching back.
# ---------------------------------------------------------------------------

# The one-line body a row shows after its headline, in priority order per
# family. First key that yields something wins. Dialog keys (`reply_preview`,
# `prompt_preview`, `message_preview`, `transcript_preview`) come ahead of
# metadata so conversation turns and sessions always surface their actual
# human/agent dialog rather than `working_directory`. `arguments` is last among
# the tool keys because it is the noisiest and `input_preview` is already trimmed.
_BODY_KEYS = (
    "reply_preview",
    "reply_text",
    "prompt_preview",
    "prompt_text",
    "message_preview",
    "transcript_preview",
    "transcript_text",
    "text",
    "input_preview",
    "command",
    "file_path",
    "ticket_title",
    "decision",
    "reasoning",
    "incident_summary",
    "title",
    "error",
    "error_message",
    "working_directory",
    "arguments",
)

# A row is 28px and middle-truncates, so the body only has to survive as far as
# the CSS. 160 characters is generous for that and keeps /events?limit=1000
# from re-inflating after CANDYS-42 drops `data`.
_BODY_LIMIT = 160

# Outcome vocabularies, lowercased. Anything outside both is a status we render
# verbatim but refuse to judge -- `ok` stays null rather than guessing, because
# a wrong glyph is worse than no glyph.
_OK_STATUSES = frozenset(
    {"success", "succeeded", "completed", "complete", "ok", "passed", "done", "expected"}
)
_FAILED_STATUSES = frozenset(
    {
        "error",
        "failure",
        "failed",
        "timeout",
        "timed_out",
        "cancelled",
        "canceled",
        "denied",
        "blocked",
        "unexpected",
    }
)


def status_string(value: Any) -> str | None:
    """Coerce whatever a producer put in `status`/`outcome` into a string.

    It is not always one. Measured on the live table: 358,717 rows carry a
    string outcome and 90 carry an OBJECT, and the old `_tool_status` returned
    it raw -- so a pr-crusher row's status reached the UI as `{"status": ...,
    "merge_attempts": 3, ...}` and would have rendered as JSON inside a 28px
    row. All 90 of those objects carry a `status` key, and 68 also carry
    `success`, so there is something real to read; the fallback is the word
    "unknown", never the JSON.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return "success" if value else "failure"
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in ("status", "outcome", "state", "result"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
        success = value.get("success")
        if isinstance(success, bool):
            return "success" if success else "failure"
        return "unknown"
    return str(value)


def _outcome_ok(status: str | None) -> bool | None:
    """True / False / None -- the third state is load-bearing.

    The feed draws a glyph from this, and an unrecognized status like
    `recorded_fragmentary_intake_pending_clarification` is neither good news
    nor bad. Null means "render it neutral", not "assume fine".
    """
    if not status:
        return None
    lowered = status.lower()
    if lowered in _OK_STATUSES:
        return True
    if lowered in _FAILED_STATUSES:
        return False
    return None


def _actor_label(env: dict[str, Any], provenance: str | None) -> str:
    """Who did this, in the fewest characters that stay unambiguous."""
    data = env.get("data") or {}
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
    actor = env.get("actor") or {}
    cli = actor.get("cli")
    producer = env.get("producer") or ""

    if provenance == "subagent":
        # The whole point of the violet dot is WHICH subagent, so name it.
        agent_type = payload.get("agent_type")
        if agent_type and agent_type != "default":
            return f"{cli or producer}/{agent_type}"
        return f"{cli or producer}/subagent"
    if provenance == "pm_agent" and ":" in producer:
        # `hermes-agent:33god-pm` -> `33god-pm`; the prefix is on every one of
        # them and carries no information once the dot is teal.
        return producer.split(":", 1)[1]
    return cli or producer or env.get("service") or "unknown"


def _duration_ms(data: dict[str, Any]) -> int | None:
    for key, scale in (("duration_ms", 1), ("duration_seconds", 1000)):
        value = data.get(key)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return int(value * scale)
    return None


def _body(env: dict[str, Any], summary: dict[str, Any]) -> str | None:
    data = env.get("data") or {}
    for key in _BODY_KEYS:
        # The per-type summary is consulted first: where a summarizer already
        # trimmed a field (`input_preview`), its version is better than the raw
        # one, and where it renamed one, this still finds it.
        for source in (summary, data):
            if key in source:
                rendered = _preview(source[key], _BODY_LIMIT)
                # A body that repeats the headline wastes the row's second line
                # and reads as a rendering bug. Equality is not enough to catch
                # it: the two are truncated at different limits, so a decision
                # event's headline and body differ by an ellipsis while saying
                # the same thing. Compare on a normalized leading fragment.
                if rendered and not _echoes(rendered, summary.get("title")):
                    return rendered
    return None


# Long enough that two genuinely different fields will not collide, short
# enough to survive both truncation limits.
_ECHO_PREFIX = 48


def _echoes(body: str, headline: Any) -> bool:
    if not isinstance(headline, str):
        return False
    fragment = body.rstrip("\u2026").strip()[:_ECHO_PREFIX]
    return bool(fragment) and fragment in headline


def row(
    env: dict[str, Any],
    summary: dict[str, Any],
    project: str | None,
    provenance: str | None,
) -> dict[str, Any]:
    """The flat, always-present projection a feed row renders from."""
    data = env.get("data") or {}
    status = status_string(summary.get("status") if "status" in summary else _tool_status(data))
    return {
        "headline": summary.get("title") or env.get("type") or "unknown event",
        "body": _body(env, summary),
        "actor_label": _actor_label(env, provenance),
        "status": status,
        "ok": _outcome_ok(status),
        "class": provenance,
        "project_label": project or UNRESOLVED_PROJECT,
        "duration_ms": _duration_ms(data),
    }


# ---------------------------------------------------------------------------
# The PM / ops families (CANDYS-43).
#
# By VOLUME these are a rounding error -- measured 7d, they are 1,644 of
# 166,723 rows, and the deep-dive's "68% render generic" claim is long dead at
# 0.98%. But volume-weighted coverage was the wrong metric: 100% of the lens a
# person actually clicks lived in that residual, so every PM event rendered as
# a bare type string with `ticket_key`, `phase` and `decision` sitting unread
# one level down.
# ---------------------------------------------------------------------------


_UUIDISH = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)

# Real Plane phase names are short words: Backlog, Todo, In Progress, Done,
# Cancelled. Nothing legitimate is 40 characters or contains markup.
_MAX_PHASE_NAME = 40


def _phase_name(value: Any) -> str | None:
    """A phase name, or None for the many things that are not one.

    `previous_phase` is misnamed on the wire. Measured over every
    repo.task.updated row that carries it (381): 185 are a raw Plane state
    UUID, 131 contain HTML, 136 are longer than 40 characters (max 5,518), and
    the short ones that remain are values like `urgent`, `high`, `none`,
    `440000` and `1100000`. It is not the previous PHASE -- it is the previous
    value of whichever field changed, whether that was the state, the priority,
    the sort order or the description.

    So there is no dependable "from" phase in this data at all, and a headline
    of the form `Backlog <- <p>Filed by the ack wiring test...` is what happens
    if you assume otherwise. CANDYS-69 is the producer-side fix; until it
    lands, a row says where a ticket LANDED and stays silent about where it
    came from.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > _MAX_PHASE_NAME:
        return None
    if _UUIDISH.match(text) or "<" in text or text.isdigit():
        return None
    return text


def _strip_html(value: Any) -> Any:
    """Plane delivers comment bodies as HTML. A 28px row wants the sentence."""
    if not isinstance(value, str):
        return value
    return re.sub(r"<[^>]+>", " ", value)


def _ticket_ref(data: dict[str, Any]) -> str:
    """A short human-facing ticket reference.

    `ticket_key` is present on all but a handful of rows. When it is not, the
    only remaining id is a UUID, which is unreadable at row width -- so it is
    shortened rather than printed in full.
    """
    for key in ("ticket_key", "issue"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    task_id = data.get("task_id")
    if isinstance(task_id, str) and task_id.strip():
        return task_id.strip()[:8] if _UUIDISH.match(task_id.strip()) else task_id.strip()
    return "ticket"


def _repo_task(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    ref = _ticket_ref(data)
    phase = _phase_name(data.get("phase"))
    previous = _phase_name(data.get("previous_phase"))
    action = _verb_from_type(env.get("type", ""))

    # A comment is the one member of this family with no ticket_key at all
    # (measured: 0 of 245 have one, 245 of 245 have a body), so the comment
    # itself is the only thing worth putting in the headline. Without this it
    # renders as the useless "ticket - appended".
    comment = _preview(_strip_html(data.get("body")), 120)
    if action == "appended" and comment:
        return {
            "title": f"Comment \u00b7 {comment}",
            "ticket": data.get("ticket_key"),
            "board": data.get("slug") or data.get("repo"),
            "comment": _preview(_strip_html(data.get("body")), 400),
            "provider": data.get("provider"),
        }

    # A phase transition is the thing worth reading, so it wins the headline
    # when there is one. Measured: 365 of 396 repo.task.updated rows carry a
    # previous_phase; the other 31 are description/label edits, where an arrow
    # would invent a transition that did not happen.
    fields = data.get("changed_fields")
    fields = [str(f) for f in fields] if isinstance(fields, list) else []
    state_moved = bool({"state", "state_id"} & set(fields))

    if phase and state_moved:
        # Where it landed. Not where it came from -- see _phase_name.
        headline = f"{ref} \u00b7 \u2192 {phase}"
    elif fields:
        headline = f"{ref} \u00b7 {', '.join(fields[:3])} changed"
    else:
        title = _preview(data.get("title"), 80)
        headline = f"{ref} \u00b7 {title}" if title else f"{ref} \u00b7 {action}"

    return {
        "title": headline,
        "ticket": ref,
        "board": data.get("slug") or data.get("repo"),
        "phase": phase,
        "previous_phase": previous,
        # Kept verbatim so the detail pane can still show what arrived, and so
        # the gap is visible rather than silently dropped.
        "previous_phase_raw": data.get("previous_phase"),
        "band": data.get("tp_band"),
        "ticket_title": _preview(data.get("title"), 200),
        "changed_fields": data.get("changed_fields"),
        "provider": data.get("provider"),
        "trigger": data.get("trigger_source") or data.get("provider_event_type"),
    }


def _repo_decision(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    decision = _preview(data.get("decision"), 200)
    who = data.get("decided_by")
    issue = data.get("issue")

    # 255 of 264 rows carry decision text. The rest still have an issue and a
    # repo, which beats printing the type -- an unreadable decision event is
    # exactly the one you would want to click into.
    subject = decision or (f"decision on {issue}" if issue else "decision recorded")
    headline = f"{who} \u00b7 {subject}" if who else subject

    return {
        "title": headline,
        "decision": decision,
        "decided_by": who,
        "issue": issue,
        "repo": data.get("repo"),
        "basis": data.get("basis"),
        "reasoning": _preview(data.get("reasoning"), 400),
    }


def _repo_board(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    key = data.get("board_key") or data.get("slug") or data.get("repo") or "board"
    return {
        "title": f"Board {key} - {_verb_from_type(env.get('type', ''))}",
        "board": key,
        "repo": data.get("repo") or data.get("slug"),
        "provider": data.get("provider"),
    }


def _repo_intake(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    what = _preview(data.get("note") or data.get("audit") or data.get("summary"), 160)
    return {
        "title": f"Intake {_verb_from_type(env.get('type', ''))}"
        + (f" - {what}" if what else ""),
        "note": what,
        "audit": data.get("audit"),
        "repo": data.get("repo"),
    }


def _repo_maintenance(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    repo = data.get("repository") or data.get("repo") or ""
    # `repository` is a git remote here, not a name.
    short = repo.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git") if repo else None
    return {
        "title": f"Maintenance {_verb_from_type(env.get('type', ''))}"
        + (f" - {short}" if short else ""),
        "repo": short,
        # `outcome` is an OBJECT on these rows; status_string() unwraps it for
        # the feed row while the detail pane keeps the whole thing.
        "status": data.get("outcome"),
        "run_id": data.get("run_id"),
        "tick": data.get("tick"),
    }


def _process_exited(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    name = data.get("container_name") or data.get("compose_service") or data.get("resource")
    summary_text = _preview(data.get("incident_summary"), 200)
    exit_code = data.get("exit_code")
    expected = data.get("expected_exit")

    # `expected_exit` is the whole point: traefik-deathwatch restarts things on
    # purpose, and 227 rows a week of "container died" that were all deliberate
    # would train you to ignore the class.
    verdict = "expected" if expected else "unexpected"
    headline = f"{name or 'process'} exited ({verdict})"
    if exit_code is not None:
        headline += f" code {exit_code}"

    return {
        "title": headline,
        "container": name,
        "exit_code": exit_code,
        "expected": expected,
        # NOT data["status"] -- that is the container's state after the
        # restart ("running"), which on an event titled "exited" reads as a
        # contradiction and tells you nothing about whether to care.
        "status": verdict,
        "container_status": data.get("status"),
        "incident": summary_text,
        "image": data.get("image"),
        "url": data.get("url"),
        "http_code": data.get("http_code"),
    }


def _project_activity(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    project = data.get("project")
    name = project.get("slug") if isinstance(project, dict) else project
    audience = data.get("audience")
    return {
        "title": f"Activity report - {name or 'project'}"
        + (f" ({audience})" if audience else ""),
        "project_name": name,
        "audience": audience,
        "window": data.get("window"),
    }


def _report_completed(env: dict[str, Any]) -> dict[str, Any]:
    data = env.get("data") or {}
    date = data.get("report_date") or data.get("completed_at")
    return {
        "title": f"Report completed - {date}" if date else "Report completed",
        "report_date": data.get("report_date"),
        "run_id": data.get("run_id"),
        "status": data.get("outcome"),
        "delivery": data.get("delivery"),
    }


def _verb_from_type(event_type: str) -> str:
    return event_type.rsplit(".", 1)[-1].replace("_", " ") if event_type else "event"


# Keys are CANONICAL types only -- summarize() normalizes before the lookup,
# so each entry covers both the historical `bloodbank.v1.*` rows and the
# current version-free ones. `agent.session.*` supersedes `cli.session.*` for
# agent CLIs (see schemas/bloodbank/agent/session.ended.json) but both still
# have schemas and both are in the table, so both are listed.
SUMMARIZERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "bloodbank.agent.session.started": _session_started,
    "bloodbank.agent.session.ended": _session_ended,
    "bloodbank.cli.session.started": _session_started,
    "bloodbank.cli.session.ended": _session_ended,
    "bloodbank.conversation.turn.started": _turn_started,
    "bloodbank.conversation.turn.completed": _turn_completed,
    "bloodbank.conversation.message.appended": _message_appended,
    "bloodbank.audio.memo.received": _audio_dialog,
    "bloodbank.audio.memo.transcribed": _audio_dialog,
    "bloodbank.audio.memo.replied": _audio_dialog,
    "bloodbank.audio.transcription.completed": _audio_dialog,
    "bloodbank.messaging.message.received": _inbound_message,
    "bloodbank.telephony.sms.received": _inbound_message,
    "bloodbank.telephony.rcs.received": _inbound_message,
    "bloodbank.telephony.mms.received": _inbound_message,
    "bloodbank.agent.tool.requested": _tool_event,
    "bloodbank.agent.tool.invoked": _tool_event,
    "bloodbank.agent.tool.completed": _tool_event,
    "bloodbank.agent.invocation.started": _agent_event,
    "bloodbank.agent.invocation.completed": _agent_event,
    "bloodbank.agent.invocation.failed": _agent_event,
    "bloodbank.system.heartbeat.received": _heartbeat,
    # Pre-Bloodbank raw heartbeat spelling; has no version token to strip.
    "system.heartbeat.tick": _heartbeat,
    # The PM / ops families -- low volume, high signal. See CANDYS-43.
    "bloodbank.repo.task.created": _repo_task,
    "bloodbank.repo.task.updated": _repo_task,
    "bloodbank.repo.task.appended": _repo_task,
    "bloodbank.repo.task.deleted": _repo_task,
    "bloodbank.repo.decision.recorded": _repo_decision,
    "bloodbank.repo.board.created": _repo_board,
    "bloodbank.repo.board.updated": _repo_board,
    "bloodbank.repo.intake.triaged": _repo_intake,
    "bloodbank.repo.intake.received": _repo_intake,
    "bloodbank.repo.maintenance.started": _repo_maintenance,
    "bloodbank.repo.maintenance.completed": _repo_maintenance,
    "bloodbank.repo.maintenance.failed": _repo_maintenance,
    "bloodbank.system.process.exited": _process_exited,
    "bloodbank.project.activity.recorded": _project_activity,
    "bloodbank.reporting.report.completed": _report_completed,
}

