"""Small, evidence-backed handoffs. Pure stdlib; also used by the HTTP CLI."""

from __future__ import annotations

import json
import re
from typing import Any

MAX_BRIEF_CHARS = 8000

# Audit payloads can contain credentials. Never reproduce them in a briefing.
_CREDENTIAL = re.compile(
    r"(?i)(?:sk-(?:or-v1-|ant-api\w*-)?[\w-]{16,}|"
    r"(?:gh[pousr]_|github_pat_)[\w]{20,}|Bearer\s+[\w.+=/-]{16,}|"
    r"eyJ[\w-]{10,}\.[\w-]+\.[\w-]+)"
)
_ASSIGNMENT = re.compile(
    r"(?i)(\b[\w-]*(?:api[_-]?key|token|password|secret|credential)[\w-]*"
    r"[\"']?\s*[:=]\s*)([\"']?)(?!op://)[^\s,;\"'}]+"
)
_USERINFO = re.compile(r"(\w+://[^\s/:]+:)[^\s/@]+(@)")
_HARNESS_BLOCK = re.compile(
    r"<(AGENTS\.md|environment_context|permissions|skills_instructions|"
    r"system-reminder|developer_instructions|available_skills)\b[^>]*>.*?</\1>",
    re.S,
)


def text(value: Any, limit: int = 420) -> str:
    """Bound and scrub human text, without interpreting it as instructions."""
    if not isinstance(value, str):
        return ""
    value = _HARNESS_BLOCK.sub("", value[:80_000])
    value = _CREDENTIAL.sub("[redacted]", value)
    value = _ASSIGNMENT.sub(r"\1\2[redacted]", value)
    value = _USERINFO.sub(r"\1[redacted]\2", value)
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _value(data: dict, *keys: str) -> Any:
    for key in keys:
        part: Any = data
        for name in key.split("."):
            part = part.get(name) if isinstance(part, dict) else None
        if part is not None and part != "":
            return part
    return None


def _items(value: Any) -> list[str]:
    values = value if isinstance(value, list) else [value]
    return [clean for item in values if (clean := text(item))]


def _arguments(data: dict) -> dict:
    args = _value(data, "arguments", "payload.tool_input", "payload.toolCall.args")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            args = {"patch": args}
    return args if isinstance(args, dict) else {}


def _failed(data: dict) -> bool:
    status = _value(data, "outcome", "status", "payload.outcome")
    if isinstance(status, str) and status.lower() in {"error", "failed", "failure"}:
        return True
    for part in (data, data.get("result"), _value(data, "payload.tool_response")):
        if not isinstance(part, dict):
            continue
        if part.get("is_error") is True or part.get("error"):
            return True
        code = part.get("exit_code")
        if isinstance(code, int) and code != 0:
            return True
    return False


def _paths(args: dict) -> list[str]:
    paths = _items(_value(args, "file_path", "path", "absolute_path", "target_file"))
    patch = _value(args, "patch", "input", "patch_text", "code")
    if isinstance(patch, str):
        # Nested orchestrator tool calls often carry a JSON-escaped patch.
        patch = patch.replace("\\n", "\n")
        paths.extend(
            text(path)
            for path in re.findall(r"\*\*\* (?:Update|Add|Delete) File: ([^\r\n]+)", patch)
        )
    return paths


def _type(value: str) -> str:
    value = re.sub(r"^bloodbank\.v\d+\.", "bloodbank.", value)
    return value.replace("bloodbank.tool.tool_call.", "bloodbank.agent.tool.")


def summarize_session(events: list[dict], metadata: dict) -> dict:
    """Extract recorded requests, outcomes and handoffs; never invent completion."""
    sections: dict[str, list[dict]] = {
        name: []
        for name in (
            "requests",
            "outcomes",
            "changes",
            "decisions",
            "unfinished",
            "errors",
            "next_steps",
        )
    }
    ended = False
    branch = ""

    def add(name: str, value: Any, event: dict) -> None:
        for clean in _items(value):
            item = {"text": clean, "event_id": event["id"], "time": event["time"]}
            # Keep the latest reference for a repeated fact.
            sections[name] = [entry for entry in sections[name] if entry["text"] != clean]
            sections[name].append(item)

    for event in sorted(events, key=lambda entry: (entry["time"], entry["id"])):
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        kind = _type(event["type"])
        branch = text(data.get("git_branch"), 100) or branch
        if kind.endswith(("agent.session.ended", "cli.session.ended")):
            ended = True
            add(
                "changes",
                [f"Recorded modified file: {p}" for p in _items(data.get("files_modified"))],
                event,
            )
            add("outcomes", _value(data, "summary", "handoff.summary"), event)
        if kind == "bloodbank.conversation.turn.started":
            add(
                "requests",
                _value(
                    data,
                    "prompt_text",
                    "prompt",
                    "user_message",
                    "payload.prompt",
                    "payload.extra.user_message",
                    "payload.extra.prompt",
                    "payload.user_message",
                ),
                event,
            )
        if kind.endswith(("conversation.turn.completed", "agent.session.ended")):
            message = _value(
                data,
                "reply_text",
                "last_assistant_message",
                "summary",
                "payload.reply_text",
                "payload.last_assistant_message",
                "payload.prompt_response",
                "payload.extra.final_response",
                "payload.extra.response",
            )
            add("outcomes", message, event)
            if isinstance(message, str):
                # Keep explicit pending work even when it appears after the
                # bounded opening excerpt of a long final response.
                for sentence in re.split(r"\n+|(?<=[.!?])\s+", message[:80_000]):
                    if re.search(
                        r"\b(?:remaining work|remains pending|pending:|blocked on|"
                        r"not yet|unverified|still (?:needed|needs|pending))\b",
                        sentence,
                        re.I,
                    ):
                        add("unfinished", sentence, event)
                    if re.match(
                        r"\s*(?:[-*]\s*)?(?:Next steps?|Suggested next step)\s*:", sentence, re.I
                    ):
                        add("next_steps", sentence, event)
        if kind.endswith("repo.decision.recorded"):
            add("decisions", _value(data, "decision", "summary", "description"), event)
        if kind.endswith("repo.task.completed"):
            add("outcomes", _value(data, "summary", "title", "name"), event)
        add(
            "unfinished",
            _value(
                data,
                "unfinished",
                "remaining_work",
                "blockers",
                "handoff.unfinished",
                "handoff.remaining_work",
            ),
            event,
        )
        add("next_steps", _value(data, "next_steps", "next_step", "handoff.next_steps"), event)

        if kind in {"bloodbank.agent.tool.completed", "bloodbank.agent.tool.invoked"}:
            tool = text(_value(data, "tool_name", "payload.tool_name"), 80)
            args = _arguments(data)
            if _failed(data):
                error = _value(data, "error", "result.error", "payload.error")
                add(
                    "errors",
                    f"{tool or 'Tool'} reported failure"
                    + (f": {text(error, 240)}" if text(error) else ""),
                    event,
                )
            elif _value(data, "outcome", "status") in {"success", "succeeded", "completed"}:
                if re.search(r"edit|write|patch|replace", tool, re.I):
                    add("changes", [f"Edit reported successful: {p}" for p in _paths(args)], event)
                command = args.get("command")
                if isinstance(command, str):
                    # Preserve useful test/build/commit evidence, not full shell pipelines.
                    match = re.search(
                        r"(?:^|[\s;&])((?:pytest|ruff|npm (?:test|run (?:test|build))|"
                        r"pnpm (?:test|build)|git (?:commit|push))\b[^\n;&]{0,140})",
                        command,
                    )
                    if match:
                        add("outcomes", f"Tool reported success: {text(match[1], 160)}", event)

    caps = {
        "requests": 2,
        "outcomes": 3,
        "changes": 5,
        "decisions": 3,
        "unfinished": 3,
        "errors": 2,
        "next_steps": 2,
    }
    output = {
        **metadata,
        "branch": branch or None,
        "status": "ended" if ended else "no_recorded_end",
    }
    for name, entries in sections.items():
        output[name] = entries[-caps[name] :]
    if len(sections["requests"]) > 1:
        # A final "yes, do this" needs the earlier request it refers to.
        output["requests"] = [sections["requests"][0], sections["requests"][-1]]
    output["coverage"] = {
        "has_request": bool(output["requests"]),
        "has_outcome": bool(output["outcomes"]),
        "has_explicit_handoff": bool(output["unfinished"] or output["next_steps"]),
        "events_sampled": len(events),
        "sample_truncated": bool(metadata.get("sample_truncated")),
    }
    return output


def render_context(context: dict) -> str:
    """The same bounded Markdown handoff for humans and every native hook."""
    sessions = context.get("sessions", [])
    project = text(context.get("project"), 120)
    lines = [
        f"CandyStore recent context — {project}",
        f"Window: {context.get('since')} to {context.get('as_of')}",
        "Historical evidence; verify the current checkout before continuing.",
    ]
    if not sessions:
        lines.append("No prior sessions found in this project and time window.")
    for session in sessions:
        section_start = len(lines)
        lines.extend(
            [
                "",
                f"{text(session.get('cli'), 40)} session {session['session_id']} "
                f"(last activity {session['last_activity']}; {session['status']})",
            ]
        )
        if session.get("branch"):
            lines.append(f"Branch recorded: {session['branch']}")
        for key, label in (
            ("requests", "Request"),
            ("outcomes", "Recorded outcome"),
            ("unfinished", "Unfinished"),
            ("next_steps", "Recorded next step"),
            ("errors", "Past failure; resolution unverified"),
            ("decisions", "Decision"),
            ("changes", "Change"),
        ):
            entries = session.get(key, [])
            visible = entries if key == "requests" else entries[-1:]
            for entry in visible:
                lines.append(f"- {label}: {text(entry['text'], 220)} [event {entry['event_id']}]")
        coverage = session["coverage"]
        if not coverage["has_request"]:
            lines.append("- Coverage: no user request captured in the sampled events.")
        if not coverage["has_outcome"]:
            lines.append("- Coverage: no narrative outcome captured in the sampled events.")
        if coverage["sample_truncated"]:
            lines.append("- Coverage: a bounded sample; earlier events may be omitted.")
        # Leave room for every selected session, not just a very verbose first
        # one. JSON retains all the sampled evidence and its references.
        budget = (MAX_BRIEF_CHARS - 2300) // max(1, len(sessions))
        lines[section_start:] = _bounded_lines(lines[section_start:], budget)
    decisions = context.get("decisions", [])
    if decisions:
        lines.extend(["", "Recent project decisions:"])
        lines.extend(f"- {entry['text']} [event {entry['event_id']}]" for entry in decisions)
    if sessions and not sessions[0]["next_steps"]:
        lines.extend(
            [
                "",
                "Suggested next step: inspect the current diff and checks, then review "
                "the latest recorded request and unfinished work before resuming.",
            ]
        )
    lines.append(
        "More sampled evidence: --json. Drill down: GET /events/<event-id>/raw; "
        "session IDs identify the source work."
    )
    return "\n".join(_bounded_lines(lines, MAX_BRIEF_CHARS))


def _bounded_lines(lines: list[str], limit: int) -> list[str]:
    if len("\n".join(lines)) <= limit:
        return lines
    marker = "- More recorded evidence is available with --json."
    result = []
    used = 0
    for line in lines:
        if used + len(line) + 1 > limit - len(marker) - 1:
            break
        result.append(line)
        used += len(line) + 1
    return [*result, marker]
