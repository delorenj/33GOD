"""Read recent project sessions without changing the durable audit trail."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from uuid import UUID

from candystore.db import cursor
from candystore.handoff import summarize_session, text
from candystore.projects import WORK_DIR_EXPR, Project, resolve
from candystore.query import PROJECT_FILTER_EXPR, _filters

DEFAULT_DAYS = 30
MAX_SESSIONS = 10
NARRATIVE_LIMIT = 60
TOOL_LIMIT = 120
NATIVE_SESSION_EXPR = """COALESCE(
    NULLIF(data->>'session_id', ''), NULLIF(data->>'thread_id', ''),
    NULLIF(data->'payload'->>'session_id', ''),
    NULLIF(data->'payload'->>'conversationId', ''),
    NULLIF(data->'payload'->'session'->>'id', ''),
    NULLIF(raw->>'correlationid', '')
)"""
_TOOL_TYPES = (
    "bloodbank.agent.tool.requested",
    "bloodbank.v1.agent.tool.requested",
    "bloodbank.v1.tool.tool_call.requested",
    "bloodbank.agent.tool.completed",
    "bloodbank.agent.tool.invoked",
    "bloodbank.v1.agent.tool.completed",
    "bloodbank.v1.agent.tool.invoked",
    "bloodbank.v1.tool.tool_call.completed",
    "bloodbank.v1.tool.tool_call.invoked",
)
# Hook receipts share a CLI actor but are hub observations, not agent work.
_AGENT_WORK = """(
    type LIKE 'bloodbank.agent.session.%' OR type LIKE 'bloodbank.v1.agent.session.%'
    OR type LIKE 'bloodbank.cli.session.%' OR type LIKE 'bloodbank.v1.cli.session.%'
    OR type LIKE 'bloodbank.conversation.turn.%' OR type LIKE 'bloodbank.v1.conversation.turn.%'
    OR type LIKE 'bloodbank.agent.tool.%' OR type LIKE 'bloodbank.v1.agent.tool.%'
    OR type LIKE 'bloodbank.v1.tool.tool_call.%'
    OR type LIKE 'bloodbank.repo.task.%' OR type LIKE 'bloodbank.v1.repo.task.%'
    OR type LIKE 'bloodbank.repo.decision.%' OR type LIKE 'bloodbank.v1.repo.decision.%'
)""".replace("%", "%%")
_TOP_LEVEL = """(
    NULLIF(data->'payload'->>'agent_id', '') IS NULL
    AND NULLIF(data->>'parent_invocation_id', '') IS NULL
    AND COALESCE(data->>'hook', data->'payload'->>'hook_event_name', '') != 'SubagentStop'
    AND type != 'bloodbank.agent.hook.updated'
)"""


class ContextError(ValueError):
    pass


def since_time(since: str | None, now: datetime) -> str:
    if since is None:
        return (now - timedelta(days=DEFAULT_DAYS)).isoformat()
    match = re.fullmatch(r"-?([1-9][0-9]*)([mhdw])", since)
    if match:
        seconds = int(match[1]) * {"m": 60, "h": 3600, "d": 86400, "w": 604800}[match[2]]
        try:
            return (now - timedelta(seconds=seconds)).isoformat()
        except OverflowError as exc:
            raise ContextError("since is outside the supported date range") from exc
    try:
        parsed = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContextError(
            "since must be an ISO date/time or a duration such as 24h or 7d"
        ) from exc
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).isoformat()


def _uuid(value: str | None) -> str | None:
    try:
        return str(UUID(value or ""))
    except ValueError:
        return None


def _project(cur, project: str | None, cwd: str | None) -> str:
    if project:
        cur.execute(
            "SELECT slug FROM projects WHERE slug = %s UNION "
            "SELECT slug FROM project_alias WHERE alias = lower(%s)",
            (project, project),
        )
        rows = cur.fetchall()
        if len(rows) != 1:
            raise ContextError(f"unknown or ambiguous project: {text(project, 120)}")
        return rows[0][0]
    if not cwd or not PurePosixPath(cwd).is_absolute():
        raise ContextError("provide an absolute cwd or --project")
    cur.execute("SELECT slug, name, repo_path, ticket_prefix FROM projects")
    slug, _ = resolve(cwd, [Project(*row) for row in cur.fetchall()])
    if slug:
        return slug
    cur.execute("SELECT slug FROM project_dir_map WHERE work_dir = %s", (cwd.rstrip("/"),))
    row = cur.fetchone()
    if row and row[0]:
        return row[0]
    raise ContextError("working directory is not a registered project; specify --project")


def _identity(correlation: str | None, native: str) -> tuple[str, list]:
    if correlation:
        # A typed comparison can use idx_events_correlation_time. Casting the
        # column to text (the legacy session endpoint) prevents that probe.
        return "correlationid = %s::uuid", [correlation]
    return f"correlationid IS NULL AND {NATIVE_SESSION_EXPR} = %s", [native]


def _newest_event(cur, slug: str, where: list[str], params: list, floor: str, ceiling: str):
    """Probe each registered directory/alias, then compare their newest rows.

    A single OR over the project rungs lets LIMIT 1 choose the global time
    index. That scans unrelated work for an inactive project even with the
    expression indexes present. Lateral probes pin the directory/alias as the
    leading index key. The shared project predicate still verifies every row.
    """
    columns = f"id, correlationid, {NATIVE_SESSION_EXPR} AS native_id, actor->>'cli' AS cli, time"
    clause = " AND ".join(where)
    directory = (
        f"SELECT newest.* FROM project_dir_map m CROSS JOIN LATERAL "
        f"(SELECT {columns} FROM events WHERE {clause} AND {WORK_DIR_EXPR} = m.work_dir "
        "ORDER BY time DESC, id DESC LIMIT 1) newest WHERE m.slug = %s"
    )

    def scoped_probe(predicate: str) -> str:
        # Keep alias/project scans on their own leading index key. Without
        # this optimization fence, the planner chooses the directory partial
        # index for an empty alias and scans root work across every project.
        # OFFSET 0 preserves the ordered stream and prevents predicate
        # pushdown; the outer LIMIT stops it at the first qualifying event.
        return (
            f"SELECT {columns} FROM (SELECT id, type, correlationid, actor, data, raw, time "
            "FROM events WHERE time >= %s AND time <= %s "
            f"AND {predicate} ORDER BY time DESC, id DESC OFFSET 0) events "
            f"WHERE {clause} ORDER BY time DESC, id DESC LIMIT 1"
        )

    explicit = "(" + scoped_probe("NULLIF(data->>'project', '') = %s") + ")"
    aliases = [
        "SELECT newest.* FROM project_alias a CROSS JOIN LATERAL "
        "("
        + scoped_probe(f"lower(NULLIF(data->>'{key}', '')) = a.alias")
        + ") newest WHERE a.slug = %s"
        for key in ("repo", "slug")
    ]
    cur.execute(
        "SELECT correlationid, native_id, cli, time, id FROM ("
        + " UNION ALL ".join([directory, explicit, *aliases])
        + ") candidates ORDER BY time DESC, id DESC LIMIT 1",
        [*params, slug, floor, ceiling, slug, *params] + [floor, ceiling, *params, slug] * 2,
    )
    return cur.fetchone()


def latest_context(
    *,
    project: str | None = None,
    cwd: str | None = None,
    since: str | None = None,
    sessions: int = 3,
    exclude_session: str | None = None,
    now: datetime | None = None,
) -> dict:
    if not 1 <= sessions <= MAX_SESSIONS:
        raise ContextError(f"sessions must be between 1 and {MAX_SESSIONS}")
    if exclude_session and len(exclude_session) > 512:
        raise ContextError("exclude_session is too long")
    now = now or datetime.now(UTC)
    floor = since_time(since, now)
    if datetime.fromisoformat(floor) > now:
        raise ContextError("since must not be in the future")
    selected = []
    with cursor() as cur:
        cur.execute("SET LOCAL statement_timeout = '2500ms'")
        # Complex bounded probes can cross PostgreSQL's JIT cost threshold.
        # Compiling those short-lived plans costs more than executing them.
        cur.execute("SET LOCAL jit = off")
        slug = _project(cur, project, cwd)
        where, params = _filters(project=slug, from_time=floor, to_time=now.isoformat())
        where.extend(
            [
                _AGENT_WORK,
                _TOP_LEVEL,
                "NULLIF(actor->>'cli', '') IS NOT NULL",
                f"(correlationid IS NOT NULL OR {NATIVE_SESSION_EXPR} IS NOT NULL)",
            ]
        )
        if exclude_session:
            correlation = _uuid(exclude_session)
            if correlation:
                where.append("correlationid IS DISTINCT FROM %s::uuid")
                params.append(correlation)
            where.append(f"{NATIVE_SESSION_EXPR} IS DISTINCT FROM %s")
            params.append(exclude_session)
            # Non-UUID native IDs are mapped to UUIDs by newer producers. Find
            # their recorded alias instead of guessing a producer's namespace.
            if not correlation:
                cur.execute(
                    f"SELECT correlationid FROM events WHERE time >= %s "
                    f"AND {NATIVE_SESSION_EXPR} = %s AND correlationid IS NOT NULL "
                    "AND type = ANY(%s) LIMIT 10",
                    (
                        floor,
                        exclude_session,
                        [
                            "bloodbank.agent.session.started",
                            "bloodbank.v1.agent.session.started",
                            "bloodbank.cli.session.started",
                            "bloodbank.v1.cli.session.started",
                        ],
                    ),
                )
                aliases = [str(row[0]) for row in cur.fetchall()]
                if aliases:
                    where.append("(correlationid IS NULL OR NOT (correlationid = ANY(%s::uuid[])))")
                    params.append(aliases)
        base_where, base_params = list(where), list(params)
        # Seek the newest event of each distinct (CLI, session), rather than
        # grouping millions of tool rows or assuming every session has an end.
        for _ in range(sessions):
            row = _newest_event(cur, slug, where, params, floor, now.isoformat())
            if row is None:
                break
            correlation = str(row[0]) if row[0] else None
            native, cli, activity = row[1:4]
            identity, identity_params = _identity(correlation, native)
            selected.append((correlation, native, cli, activity))
            where.append(f"NOT (actor->>'cli' = %s AND COALESCE(({identity}), FALSE))")
            params.extend([cli, *identity_params])

        summaries = []
        for correlation, native, cli, activity in selected:
            identity, identity_params = _identity(correlation, native)
            # Some turn-end hooks carry an answer and session ID but omit cwd.
            # Inherit that session's project only for rows with no project
            # signal at all. An explicit different project remains excluded.
            inherited_project = (
                f"({PROJECT_FILTER_EXPR} OR ({WORK_DIR_EXPR} IS NULL "
                "AND NULLIF(data->>'project', '') IS NULL AND NULLIF(data->>'repo', '') IS NULL "
                "AND NULLIF(data->>'slug', '') IS NULL))"
            )
            session_where = [
                inherited_project if part == PROJECT_FILTER_EXPR else part for part in base_where
            ]
            clause = " AND ".join([*session_where, "actor->>'cli' = %s", f"({identity})"])
            query_params = [*base_params, cli, *identity_params]
            events = []
            truncated = False
            for tools, limit in ((False, NARRATIVE_LIMIT), (True, TOOL_LIMIT)):
                cur.execute(
                    "SELECT id, type, time, data FROM events "
                    f"WHERE {clause} AND {'type = ANY(%s)' if tools else 'NOT (type = ANY(%s))'} "
                    "ORDER BY time DESC, id DESC LIMIT %s",
                    [*query_params, list(_TOOL_TYPES), limit + 1],
                )
                rows = cur.fetchall()
                truncated = truncated or len(rows) > limit
                events.extend(
                    {"id": str(r[0]), "type": r[1], "time": r[2].isoformat(), "data": r[3]}
                    for r in rows[:limit]
                )
            summaries.append(
                summarize_session(
                    events,
                    {
                        "session_id": correlation or native,
                        "native_session_id": native,
                        "cli": cli,
                        "last_activity": activity.isoformat(),
                        "sample_truncated": truncated,
                    },
                )
            )
        # PM decisions often have their own correlation ID. Include the
        # project's decisions independently rather than attaching them to an
        # arbitrary nearby session.
        decision_where, decision_params = _filters(
            project=slug,
            from_time=floor,
            to_time=now.isoformat(),
            type="bloodbank.repo.decision.recorded,bloodbank.v1.repo.decision.recorded",
        )
        decisions = []
        for _ in range(3):
            newest = _newest_event(
                cur, slug, decision_where, decision_params, floor, now.isoformat()
            )
            if newest is None:
                break
            event_id = str(newest[4])
            cur.execute(
                "SELECT COALESCE(data->>'decision', data->>'summary', data->>'description') "
                "FROM events WHERE id = %s::uuid",
                (event_id,),
            )
            decision = text(cur.fetchone()[0])
            if decision:
                decisions.append(
                    {"event_id": event_id, "time": newest[3].isoformat(), "text": decision}
                )
            decision_where.append("id != %s::uuid")
            decision_params.append(event_id)
    return {
        "schema_version": 1,
        "project": slug,
        "since": floor,
        "as_of": now.isoformat(),
        "excluded_session": exclude_session,
        "sessions": summaries,
        "decisions": decisions,
    }
