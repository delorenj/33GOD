from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from candystore.db import cursor
from candystore.projects import WORK_DIR_EXPR
from candystore.summarize import (
    UNRESOLVED_PROJECT,
    _prompt_text,
    _reply_text,
    canonical_type,
    summarize,
)

# The `type` column holds two shapes forever: the historical five-token
# `bloodbank.v1.<domain>.<entity>.<action>` on ~718k rows already in the table,
# and the current version-free four-token `bloodbank.<domain>.<entity>.<action>`
# on everything published since. A positional `split_part(type, '.', 3/4)` is
# agnostic to the version token's VALUE, not to its PRESENCE -- drop the token
# and domain/entity shift one slot left, so a --scope filter silently returns
# the WRONG rows instead of erroring (measured: `--scope agent.tool` matched 0
# of the 1128 new-shape rows, and those rows answered `--scope tool` instead).
# Strip the prefix and its optional version first; then domain and entity sit
# at positions 1 and 2 for both shapes.
SCOPE_TYPE_EXPR = "regexp_replace(type, '^bloodbank\\.(v[0-9]+\\.)?', '')"

# The session summary counts events by CANONICAL type. Two independent
# normalizations are needed and `canonical_type()` (summarize.py) already does
# both, so this module keys on its output instead of encoding the knowledge a
# third time:
#   1. the version token -- `bloodbank.v1.conversation.turn.started` and
#      `bloodbank.conversation.turn.started` are the same event;
#   2. the `tool.tool_call.* -> agent.tool.*` ENTITY rename, which survives
#      version-stripping. The live table holds 29,341 v1.tool.tool_call.requested
#      AND 332,443 agent.tool.requested rows across both shapes; counting only
#      the v1 tool_call spelling reported 0 tools for every session recorded
#      since the rename.
TURN_STARTED_TYPE = "bloodbank.conversation.turn.started"
TURN_COMPLETED_TYPE = "bloodbank.conversation.turn.completed"
TOOL_REQUESTED_TYPE = "bloodbank.agent.tool.requested"
TOOL_INVOKED_TYPE = "bloodbank.agent.tool.invoked"

SESSION_START_TYPES = frozenset(
    {
        "bloodbank.agent.session.started",
        "bloodbank.cli.session.started",
    }
)

# A session ends under EITHER spelling. `agent.session.ended` supersedes
# `cli.session.ended` for agent CLIs (bloodbank/docs/event-naming.md) but both
# schemas are live and both are in the corpus, so this is a two-member set, not
# a rename. The old probe was `type.endswith("cli.session.ended")`, which found
# the 592 v1.cli rows and missed all 4,980 agent.session.ended ones -- so for
# every modern session the authoritative `data.total_turns` /
# `data.duration_seconds` payload was never read. `audio.session.ended` is a
# different domain and is deliberately not in here.
SESSION_END_TYPES = frozenset(
    {
        "bloodbank.agent.session.ended",
        "bloodbank.cli.session.ended",
    }
)

SESSION_TYPES = SESSION_START_TYPES | SESSION_END_TYPES

# The project an event belongs to: a PJangler registry slug, resolved through
# project_dir_map (migrations 005/006), or NULL when nothing claims it.
#
# This replaced a basename fallback chain that reported worktrees, subdirectories
# and bare-repo suffixes as projects. It also replaced a SECOND, DIFFERENT
# implementation in summarize.py, which stripped `.git` where this one did not --
# so /events said `intelliforia.git` on the card while /events/<id>/summary said
# `intelliforia` for the same row, on 399 rows in 7 days.
#
# `data.project` is consulted, but only if it names a real registry project.
# Trusting it outright is what the obvious ladder would do, and it is wrong here:
# measured over the whole table, three of its five distinct values are entire
# JSON objects serialized as text ({"name": "James Brennan", "slug": ..., ...}),
# and its highest-volume plain string is `wax` (2,803 rows), which is not a
# registered project at all. Validating against the registry turns all of that
# into an honest NULL instead of a JSON blob rendered as a project name.
#
# `data.repo` / `data.slug` are the last two rungs and they are what make the PM
# lens reachable at all. Measured over 7 days, ZERO of the 1,100+
# repo.task.* / repo.decision.* / repo.board.* rows carry a working_directory --
# they come from the Plane webhook and from PM agents, neither of which has a
# filesystem -- so before these rungs existed, "pick a project, click PM"
# returned an empty feed, which is the single thing the feature is for. Those
# rows carry a repo NAME instead (`33god`, `bloodbank`), which is not always the
# slug (`project`, `bb`), so it is translated through project_alias (007).
#
# Cost: four correlated lookups, every one a primary-key probe rather than the
# prefix scan a naive version would do. Measured 3.5 ms for a 200-row page over
# the default window at two rungs (compare 141 s for a correlated
# longest-prefix subquery, which is exactly why prefix matching lives in the
# map instead of here); re-measured after adding the alias rungs below.
PROJECT_EXPR = f"""COALESCE(
    (SELECT m.slug FROM project_dir_map m WHERE m.work_dir = {WORK_DIR_EXPR}),
    (SELECT p.slug FROM projects p WHERE p.slug = NULLIF(data->>'project', '')),
    (SELECT a.slug FROM project_alias a WHERE a.alias = lower(NULLIF(data->>'repo', ''))),
    (SELECT a.slug FROM project_alias a WHERE a.alias = lower(NULLIF(data->>'slug', '')))
)"""

# For GROUP BY, where a NULL bucket has no name to render. The row-level
# expression stays nullable on purpose -- a consumer should be able to tell
# "no project" from a project literally called "unassigned" -- so the label is
# applied only where a chart axis needs a string.
PROJECT_LABEL_EXPR = f"COALESCE({PROJECT_EXPR}, '{UNRESOLVED_PROJECT}')"

# The same question as PROJECT_EXPR, asked in the direction an index can answer.
#
# `PROJECT_EXPR = %s` would be one definition instead of two, and it was the
# first thing tried -- but as a WHERE predicate it runs its correlated lookups
# on every row in the window rather than on the page, and measured 658 ms over
# 24 h and 3,085 ms over 7 days. Turned inside out into set membership, the
# same question is an index scan.
#
# Two derivations of one concept is exactly the bug CANDYS-37 deleted three
# copies of, so this is only tolerable because it is PROVEN equivalent rather
# than assumed: `test_the_filter_agrees_with_the_display` asserts the two agree
# row for row over the corpus. Equivalence holds because no row carries
# conflicting signals -- measured across 402,478 rows over 30 days, there are
# ZERO cases where the directory says one project and `repo`/`slug`/`project`
# says another. If that ever stops being true the test fails, which is the
# point of writing it down.
PROJECT_FILTER_EXPR = f"""(
    {WORK_DIR_EXPR} IN (SELECT work_dir FROM project_dir_map WHERE slug = %s)
    OR NULLIF(data->>'project', '') = %s
    OR lower(NULLIF(data->>'repo', '')) IN (SELECT alias FROM project_alias WHERE slug = %s)
    OR lower(NULLIF(data->>'slug', '')) IN (SELECT alias FROM project_alias WHERE slug = %s)
)"""

# Where an event came from -- the colour of its dot in the feed.
#
# Derived in SQL rather than in summarize.py because the feed CLICKS a dot to
# filter and the timeline strip needs `GROUP BY class`; a Python function that
# runs per row after the rows come back can serve neither. Measured on the live
# table: `GROUP BY class, minute` over the default 60-minute window costs 18 ms.
#
# Order is significant, and the first two branches are the interesting ones:
#
#  * `payload.agent_id` marks a SUBAGENT, and it is checked first because a
#    subagent's events are also agent-CLI events -- the later `agent_cli` branch
#    would swallow every one of them. Verified over the whole table: agent_id
#    NEVER equals session_id (0 of 22,284 `agent_type='default'` rows), so an
#    orchestrator's own events do not carry the key at all. That also settles
#    what `agent_type='default'` is: those rows carry `hook: SubagentStop` and
#    230 distinct agent_ids across 73 sessions, so it is an unnamed subagent,
#    not the orchestrator (CANDYS-50).
#
#  * A `hermes-agent:` producer prefix is a named PM/momo profile
#    (`hermes-agent:33god-pm`). Bare `hermes-agent` is the fleet agent doing
#    ordinary work and stays in `agent`; the colon is the whole distinction.
#
# The Plane webhook arrives through n8n but its provenance is the ticket board,
# so `actor.type = 'ticket_provider'` is checked before the n8n branch --
# otherwise every ticket event would read as generic workflow traffic.
#
# `starts_with()` rather than `LIKE 'x%'` throughout, deliberately. A literal
# `%` in a SQL string that psycopg2 later parameterizes has to be written `%%`,
# and this constant is embedded in queries that sometimes carry params and
# sometimes do not -- so the same text would need two different spellings to be
# correct. `starts_with()` has no escaping to get wrong.
PROVENANCE_EXPR = """CASE
    WHEN data->'payload' ? 'agent_id'                            THEN 'subagent'
    WHEN starts_with(producer, 'hermes-agent:')                  THEN 'pm_agent'
    WHEN actor->>'type' = 'ticket_provider'                      THEN 'ticket_webhook'
    WHEN producer = 'n8n'
         OR starts_with(source, 'urn:33god:integration:n8n:')    THEN 'n8n_workflow'
    WHEN actor->>'type' = 'agent_cli'                            THEN 'agent'
    WHEN actor->>'type' = 'service'
         OR starts_with(source, 'urn:33god:service:')
         OR starts_with(source, 'urn:33god:skill:')              THEN 'service'
    WHEN actor->>'type' = 'operator'                             THEN 'operator'
    ELSE 'other'
END"""

# Every class the classifier can produce, with the colour the feed paints it and
# an honest note about what it cannot see. `coverage` is not decoration: the
# strip and the dots are only trustworthy if their gaps are declared, and two of
# these classes have real ones.
#
# No red and no green anywhere -- those two hues carry OUTCOME on a row, and a
# dot that competes with them for the same channel makes "red" stop meaning bad.
PROVENANCE_CLASSES: dict[str, dict[str, str]] = {
    "agent": {
        "color": "#3b82f6",
        "label": "Agent",
        "description": "An agent CLI acting as the orchestrator of its own session.",
        "coverage": "complete",
    },
    "subagent": {
        "color": "#8b5cf6",
        "label": "Subagent",
        "description": "Work done by a delegated agent, attributed via payload.agent_id.",
        # Stated in the API, not just in a ticket. Measured over 7 days:
        # codex-cli attributes 15,415 subagent rows, while claude-code spawned
        # 388 subagents (Agent/Task/Workflow tool calls) and emitted ZERO
        # attributable rows for them -- its subagent work is in the trail,
        # indistinguishable from the orchestrator's, and lands in `agent`.
        # So a small violet share means "little CODEX subagent work", never
        # "little subagent work". CANDYS-65 is the producer-side fix.
        "coverage": "codex-cli only; claude-code and hermes-agent emit no "
        "per-event subagent marker, so their subagent work counts as `agent`",
    },
    "pm_agent": {
        "color": "#14b8a6",
        "label": "PM agent",
        "description": "A named Hermes PM or momo profile (hermes-agent:<profile>).",
        "coverage": "complete",
    },
    "ticket_webhook": {
        "color": "#ec4899",
        "label": "Ticket board",
        "description": "Plane board activity, delivered through the n8n webhook.",
        "coverage": "complete",
    },
    "n8n_workflow": {
        "color": "#eab308",
        "label": "n8n workflow",
        "description": "An n8n workflow that is not the ticket-board webhook.",
        "coverage": "complete",
    },
    "service": {
        "color": "#64748b",
        "label": "Service",
        "description": "A 33GOD service or skill (tiller, deathwatch, activity-report).",
        "coverage": "complete",
    },
    "operator": {
        "color": "#a3a3a3",
        "label": "Operator",
        "description": "A human acting directly rather than through an agent.",
        "coverage": "complete",
    },
    "other": {
        "color": "#9ca3af",
        "label": "Other",
        "description": "Matched no rule. Should stay empty; if it grows, a producer changed.",
        "coverage": "complete",
    },
}



# The one-click scopes -- the "PM button" and its siblings. This is the whole
# no-query-language bet: a lens is a NAMED predicate on the server, so the chip
# a person clicks and the query an agent runs are the same thing and cannot
# drift into two dialects of the same question.
#
# A lens says WHAT KIND of event; `?class=` says WHO produced it. Keeping those
# separate is deliberate -- a `subagents` lens would just restate
# `class=subagent`, and two spellings of one filter is how a facet model starts
# growing the grammar it was supposed to replace. They compose: AND across
# facets, OR within one.
#
# Counts are measured over 7 days and every lens is non-empty; a chip that can
# only ever show an empty feed does not ship. No `LIKE 'x%'` anywhere, for the
# same reason PROVENANCE_EXPR avoids it: a literal % needs doubling only when
# psycopg2 parameterizes the statement, and these predicates are embedded in
# queries that sometimes carry params and sometimes do not.
LENSES: dict[str, dict[str, str]] = {
    "pm": {
        "label": "PM",
        "description": "Tickets, decisions, boards and intake -- the project-management trail.",
        "sql": (
            f"(starts_with({SCOPE_TYPE_EXPR}, 'repo.task.') "
            f"OR {SCOPE_TYPE_EXPR} = 'repo.decision.recorded' "
            f"OR starts_with({SCOPE_TYPE_EXPR}, 'repo.board.') "
            f"OR starts_with({SCOPE_TYPE_EXPR}, 'repo.intake.'))"
        ),
    },
    "decisions": {
        "label": "Decisions",
        "description": "Judgment calls recorded against pillars.",
        "sql": f"({SCOPE_TYPE_EXPR} = 'repo.decision.recorded')",
    },
    "sessions": {
        "label": "Sessions",
        "description": "Agent sessions starting and ending.",
        # Enumerated rather than matched on a `session.` suffix, which would
        # also sweep in `audio.session.*` -- a different domain entirely, and
        # the same trap SESSION_END_TYPES above already documents.
        "sql": (
            f"({SCOPE_TYPE_EXPR} IN ('agent.session.started', 'agent.session.ended', "
            "'cli.session.started', 'cli.session.ended'))"
        ),
    },
    "turns": {
        "label": "Turns",
        "description": "Conversation turns and messages.",
        "sql": f"(starts_with({SCOPE_TYPE_EXPR}, 'conversation.'))",
    },
    "agents": {
        "label": "Agents",
        "description": "Agent invocations -- one entry per delegated unit of work.",
        "sql": f"(starts_with({SCOPE_TYPE_EXPR}, 'agent.invocation.'))",
    },
    "tools": {
        "label": "Tools",
        "description": "Tool calls. 96% of the trail by volume; usually what you collapse.",
        # Both spellings: the `tool.tool_call.* -> agent.tool.*` entity rename
        # survives version-stripping, so SCOPE_TYPE_EXPR alone does not fold them.
        "sql": (
            f"(starts_with({SCOPE_TYPE_EXPR}, 'agent.tool.') "
            f"OR starts_with({SCOPE_TYPE_EXPR}, 'tool.tool_call.'))"
        ),
    },
    "errors": {
        "label": "Errors",
        "description": "Anything that failed, across every family.",
        # Cross-cutting rather than a type family, which is the point of it.
        # An UNEXPECTED container exit belongs here; the 227-a-week deliberate
        # restarts emphatically do not, or the lens becomes noise.
        "sql": (
            "(lower(data->>'outcome') IN "
            "('error','failure','failed','timeout','timed_out','cancelled','canceled') "
            f"OR {SCOPE_TYPE_EXPR} ~ '\\.failed$' "
            f"OR (starts_with({SCOPE_TYPE_EXPR}, 'system.process.') "
            "AND data->>'expected_exit' = 'false'))"
        ),
    },
    "ops": {
        "label": "Ops",
        "description": "Process exits and repo maintenance runs.",
        "sql": (
            f"(starts_with({SCOPE_TYPE_EXPR}, 'system.process.') "
            f"OR starts_with({SCOPE_TYPE_EXPR}, 'repo.maintenance.'))"
        ),
    },
    "reports": {
        "label": "Reports",
        "description": "Activity reports and generated summaries.",
        "sql": (
            f"(starts_with({SCOPE_TYPE_EXPR}, 'reporting.') "
            f"OR {SCOPE_TYPE_EXPR} = 'project.activity.recorded')"
        ),
    },
}


# Free-text search (`q`) runs against the generated `search_text` column and its
# trigram index (migrations/003_search.sql).
#
# A trigram index cannot answer a pattern with no complete 3-gram in it, so a
# 1- or 2-character term silently degrades to a sequential scan of every row --
# 869k rows and ~4 GB of TOAST at the time of writing, i.e. minutes per
# keystroke from a search-as-you-type box. Short terms are refused instead of
# served slowly; the caller gets a 400 that says so.
SEARCH_MIN_TERM = 3

# An unbounded `/events` is a sequential scan over the whole table -- 886k rows
# and ~4.9 GB of TOAST at the time of writing -- because the useful filters are
# jsonb-derived expressions the planner cannot estimate. Measured on the live
# table: a project-filtered page cost 8.45 s, split 4,024 ms for the COUNT(*)
# and 4,049 ms for the LIMIT 100 SELECT, against 84 ms for a bare
# `COUNT(*) FROM events`. The same query bound to 24 h with LIMIT 200 and no
# count came back in 166 ms.
#
# So interactive browsing gets a default window, and the count becomes opt-in
# and capped. Both are policies of the *browse*, not of the query: a caller
# that names its own range means it, and `list_events` keeps answering exactly
# what it is asked. `applied_window()` is where the policy lives so that the
# HTTP layer and any future CLI share one definition of "recent".
DEFAULT_WINDOW_HOURS = 24

# Cap for an interactive count. Answering "more than 10,000" costs an index
# scan that stops early; answering "118,745" costs a full scan of the matches.
# Nothing in the UI renders the difference, so it is not worth 4 seconds.
COUNT_CAP = 10_000


class SearchError(ValueError):
    """A `q` the search index cannot serve. Distinct from a bare ValueError so
    main.py can answer 400 for it without also swallowing an unrelated internal
    ValueError and reporting a server bug as the caller's fault."""

# LIKE metacharacters in a user's term are literal text, not syntax: searching
# `file_path` must not match `filexpath`, and `100%` must not match everything.
# psycopg2 parameterizes the VALUE, which stops injection but leaves `%` and `_`
# meaningful to the pattern matcher, so they are escaped here. Backslash first,
# or it would double-escape the escapes added after it. LIKE's default escape
# character is backslash, so no ESCAPE clause is needed.
_LIKE_ESCAPES = str.maketrans({"\\": "\\\\", "%": "\\%", "_": "\\_"})


def list_events(
    *,
    type: str | None = None,
    domain: str | None = None,
    from_time: str | None = None,
    to_time: str | None = None,
    correlationid: str | None = None,
    producer: str | None = None,
    service: str | None = None,
    cli: str | None = None,
    project: str | None = None,
    provenance: str | None = None,
    lens: str | None = None,
    scope: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    total: bool = True,
    count_cap: int | None = None,
) -> dict[str, Any]:
    """List events matching the filters, newest first.

    `total=False` skips the count entirely and returns `total: None`.
    `count_cap=N` stops counting at N+1 and sets `total_capped`, so the answer
    becomes "at least N" instead of an exact figure. Leaving `count_cap=None`
    on a query with no time bound is the 4-second, 25 GB-of-buffers path
    described above -- deliberate for a caller that genuinely needs the exact
    number, wrong for anything interactive. The HTTP layer passes
    `count_cap=COUNT_CAP`.
    """
    where, params = _filters(
        type=type,
        domain=domain,
        from_time=from_time,
        to_time=to_time,
        correlationid=correlationid,
        producer=producer,
        service=service,
        cli=cli,
        project=project,
        provenance=provenance,
        lens=lens,
        scope=scope,
        q=q,
    )
    limit = max(1, min(int(limit), 1000))
    offset = max(0, int(offset))

    clause = " AND ".join(where)
    select_sql = f"""
    SELECT id, type, time, producer, service, domain, actor, data, correlationid, raw,
           {PROJECT_EXPR} AS project, {PROVENANCE_EXPR} AS class
    FROM events
    WHERE {clause}
    ORDER BY time DESC
    LIMIT %s OFFSET %s
    """

    # Counting through a bounded subquery lets Postgres stop as soon as the cap
    # is reached instead of finding every match. `count_cap` is an int from
    # this module, never caller text, but it is still bound as a parameter
    # rather than interpolated -- the next person to touch this line should not
    # have to work out which of the two f-strings is safe.
    if count_cap is None:
        count_sql = f"SELECT COUNT(*) FROM events WHERE {clause}"
        count_params = list(params)
    else:
        count_sql = f"SELECT COUNT(*) FROM (SELECT 1 FROM events WHERE {clause} LIMIT %s) capped"
        count_params = [*params, count_cap + 1]

    with cursor() as cur:
        counted: int | None = None
        if total:
            cur.execute(count_sql, count_params)
            counted = cur.fetchone()[0]
        cur.execute(select_sql, [*params, limit, offset])
        rows = cur.fetchall()
        dialog_by_session = _fetch_session_dialog(
            cur,
            [str(row[8]) for row in rows if row[8] and canonical_type(row[1]) in SESSION_TYPES],
        )

    events = [
        _preview_from_row(row, dialog_by_session.get(str(row[8])) if row[8] else None)
        for row in rows
    ]
    return {
        "events": events,
        "total": counted,
        # True means "at least `total`", not "exactly". A consumer that renders
        # the number must render the distinction too, or it reports 10,000
        # events as fact when there are 118,745.
        "total_capped": bool(count_cap is not None and counted == count_cap + 1),
        "limit": limit,
        "offset": offset,
        # The applied window, echoed so a caller can see the default it got
        # rather than inferring it. Both null means "the whole trail".
        "window": {"from": from_time, "to": to_time},
    }


def get_event_record(event_id: str) -> dict[str, Any] | None:
    sql = f"""
    SELECT id, type, time, producer, service, domain, actor, data, correlationid, raw,
           {PROJECT_EXPR} AS project, {PROVENANCE_EXPR} AS class
    FROM events
    WHERE id = %s
    """
    with cursor() as cur:
        cur.execute(sql, (event_id,))
        row = cur.fetchone()
        if not row:
            return None
        dialog_by_session = _fetch_session_dialog(
            cur,
            [str(row[8])] if row[8] and canonical_type(row[1]) in SESSION_TYPES else [],
        )
    return _preview_from_row(row, dialog_by_session.get(str(row[8])) if row[8] else None)


# ---------------------------------------------------------------------------
# The collapsed feed (CANDYS-48).
#
# Tool calls are 95.9% of the trail -- 159,816 of 166,723 rows over 7 days. A
# feed that renders them one per row is a scroll bar, not a feed. With them
# hidden, every consecutive run of tool events between two orchestrator-level
# events becomes ONE fold row carrying the count, the top tools and the span.
#
# Server-side rather than in the browser because the boundary between runs
# depends on rows the browser may not have (it holds a page; a run can be
# longer), and because shipping 25x the bytes to throw them away is the thing
# the filter pushdown exists to avoid.
#
# Two invariants make it trustworthy:
#   * An ERROR terminates a run and gets its own row, so a fold can never hide
#     a failure. That is why a fold needs no error badge.
#   * The counts are exact. Sum of fold counts + plain rows == the unfiltered
#     row count for the same window. Rows are collapsed; nothing is sampled.
# ---------------------------------------------------------------------------

# A run shorter than this renders as plain rows. A chevron over one item is
# noise, and hiding two rows behind a control that costs a click to open is a
# worse trade than just showing them.
MIN_FOLD_RUN = 3

# How many distinct tool names a fold names before it says "+N more".
FOLD_TOP_TOOLS = 3


def _is_tool_row(event: dict[str, Any]) -> bool:
    canonical = canonical_type(event.get("type"))
    return canonical.startswith("bloodbank.agent.tool.")


def _fold(run: list[dict[str, Any]]) -> dict[str, Any]:
    """Collapse a run of tool rows into one counted marker."""
    names = Counter(
        (event.get("summary") or {}).get("tool") or "tool" for event in run
    )
    top = names.most_common(FOLD_TOP_TOOLS)
    # Newest first, matching the feed's own order, so `from`/`to` read the way
    # the rows are laid out.
    newest, oldest = run[0], run[-1]
    return {
        "kind": "fold",
        # Stable within a page and derived from the run itself, so React can
        # key on it without the list reshuffling on every poll.
        "id": f"fold:{oldest['id']}:{newest['id']}",
        "count": len(run),
        "tools": dict(top),
        "other_tools": max(0, len(names) - len(top)),
        "from": oldest.get("time"),
        "to": newest.get("time"),
        "class": newest.get("class"),
        "project": newest.get("project"),
        # The members, fetchable without re-deriving the run boundaries.
        "member_ids": [event["id"] for event in run],
    }


def collapse_tool_runs(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fold consecutive tool rows, leaving everything else alone.

    Pure, so the boundary rules are testable without a database.
    """
    out: list[dict[str, Any]] = []
    run: list[dict[str, Any]] = []

    def flush() -> None:
        if not run:
            return
        if len(run) >= MIN_FOLD_RUN:
            out.append(_fold(run))
        else:
            out.extend(run)
        run.clear()

    for event in events:
        summary = event.get("summary") or {}
        failed = (summary.get("row") or {}).get("ok") is False
        if _is_tool_row(event) and not failed:
            run.append(event)
            continue
        # A failure ends the run AND stands on its own, which is what lets a
        # collapsed feed still be a place you would notice something breaking.
        flush()
        out.append(event)
    flush()
    return out


def list_feed(*, tools: bool = True, **kwargs: Any) -> dict[str, Any]:
    """`list_events`, optionally with consecutive tool runs collapsed.

    `tools=False` does NOT filter tool calls out of the query -- it folds them
    after the fact. That distinction is the honesty rule made mechanical: the
    rows are collapsed, the counts are not, so `folded` reports exactly how
    many events are behind the markers and the arithmetic still closes.
    """
    result = list_events(**kwargs)
    if tools:
        result["rows"] = result["events"]
        result["folded"] = 0
        return result

    rows = collapse_tool_runs(result["events"])
    result["rows"] = rows
    result["folded"] = sum(
        row["count"] for row in rows if row.get("kind") == "fold"
    )
    return result


def get_event_with_project(event_id: str) -> tuple[dict[str, Any], str | None] | None:
    """The raw envelope plus its resolved project slug.

    /events/<id>/summary needs both: the envelope to summarize, and the slug so
    its `project` agrees with the one /events reported for the same row.
    """
    with cursor() as cur:
        cur.execute(
            f"SELECT raw, {PROJECT_EXPR}, correlationid, type FROM events WHERE id = %s",
            (event_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        raw, project, correlationid, event_type = row
        dialog = None
        if correlationid and canonical_type(event_type) in SESSION_TYPES:
            dialog = _fetch_session_dialog(cur, [str(correlationid)]).get(str(correlationid))
    if dialog and isinstance(raw, dict):
        raw, _ = _merge_session_dialog(raw, raw.get("data"), event_type, dialog)
    return (raw, project)


def get_event(event_id: str) -> dict[str, Any] | None:
    with cursor() as cur:
        cur.execute("SELECT raw FROM events WHERE id = %s", (event_id,))
        row = cur.fetchone()
    return row[0] if row else None


def get_session_events(correlationid: str) -> list[dict[str, Any]]:
    sql = f"""
    SELECT id, type, time, producer, service, domain, actor, data, correlationid, raw,
           {PROJECT_EXPR} AS project, {PROVENANCE_EXPR} AS class
    FROM events
    WHERE correlationid::text = %s
    ORDER BY time ASC
    """
    with cursor() as cur:
        cur.execute(sql, (correlationid,))
        rows = cur.fetchall()

    dialog = _extract_session_dialog((row[1], row[7]) for row in rows)
    events = []
    for row in rows:
        raw, data = _merge_session_dialog(row[9], row[7], row[1], dialog)
        events.append(
            {
                "id": str(row[0]),
                "type": row[1],
                "time": _iso(row[2]),
                "producer": row[3],
                "service": row[4],
                "domain": row[5],
                "actor": row[6],
                "data": data,
                "correlationid": str(row[8]) if row[8] else None,
                "project": row[10],
                "class": row[11],
                "summary": summarize(raw, row[10], row[11]),
                "raw": raw,
            }
        )
    return events


def get_session_summary(correlationid: str) -> dict[str, Any]:
    return session_summary(correlationid, get_session_events(correlationid))


def session_summary(correlationid: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    """Roll a session's timeline up into counts. Pure: no DB, so it is testable
    without CANDYSTORE_TEST_DATABASE_URL (see tests/test_session_summary.py)."""
    # `events_by_type` keeps the RAW spelling -- it is a report of what is
    # literally in the table, and collapsing it would hide a producer still
    # emitting a retired shape. Every derived COUNT below reads the canonical
    # tally instead, so it sees both wire shapes as one event.
    event_types = Counter(event["type"] for event in events)
    canonical_counts = Counter(canonical_type(event["type"]) for event in events)

    started_at = events[0]["time"] if events else None
    ended_at = events[-1]["time"] if events else None
    duration_seconds = _duration_seconds(started_at, ended_at)
    session_end = next(
        (event for event in reversed(events) if canonical_type(event["type"]) in SESSION_END_TYPES),
        None,
    )
    data = (session_end or {}).get("data") or {}
    actor = ((session_end or events[0])["actor"] if events else {}) or {}

    # The session-end payload is authoritative when it is there, but a session
    # still in flight (or one whose end event never landed) has no payload at
    # all -- fall back to counting the timeline. `is None` rather than dict
    # default: a present-but-null field must fall back too.
    total_turns = data.get("total_turns")
    if total_turns is None:
        total_turns = canonical_counts.get(TURN_STARTED_TYPE, 0)
    reported_duration = data.get("duration_seconds")
    if reported_duration is None:
        reported_duration = duration_seconds

    return {
        "session_id": correlationid,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": reported_duration,
        "cli": actor.get("cli"),
        # Read off the rows, which arrive already resolved from
        # get_session_events. session_summary stays pure (no DB), and there is
        # still exactly one definition of "project" in the codebase.
        "project": _session_project(events),
        "events_count": len(events),
        "turns": total_turns,
        "tools_requested": canonical_counts.get(TOOL_REQUESTED_TYPE, 0),
        "tools_invoked": canonical_counts.get(TOOL_INVOKED_TYPE, 0),
        "events_by_type": dict(event_types),
    }


def heatmap(
    group_by: str = "project",
    from_time: str | None = None,
    to_time: str | None = None,
) -> list[dict[str, Any]]:
    group_col = {
        "project": PROJECT_LABEL_EXPR,
        "cli": "COALESCE(actor->>'cli', 'unknown')",
        "domain": "domain",
    }.get(group_by, "domain")

    sql = f"""
    SELECT DATE_TRUNC('hour', time) AS hour, {group_col} AS bucket, COUNT(*) AS count
    FROM events
    WHERE time >= %s AND time <= %s
    GROUP BY hour, bucket
    ORDER BY hour DESC, count DESC
    """
    with cursor() as cur:
        cur.execute(sql, (from_time or "1970-01-01", to_time or "2099-01-01"))
        rows = cur.fetchall()

    return [
        {
            "hour": _iso(row[0]),
            "bucket": row[1],
            group_by if group_by in {"project", "cli", "domain"} else "domain": row[1],
            "count": row[2],
        }
        for row in rows
    ]


def daily(from_time: str | None = None, to_time: str | None = None) -> list[dict[str, Any]]:
    sql = """
    SELECT DATE_TRUNC('day', time) AS day, COUNT(*) AS count
    FROM events
    WHERE time >= %s AND time <= %s
    GROUP BY day
    ORDER BY day DESC
    """
    with cursor() as cur:
        cur.execute(sql, (from_time or "1970-01-01", to_time or "2099-01-01"))
        rows = cur.fetchall()
    return [{"day": _iso(row[0]), "count": row[1]} for row in rows]


def by_cli(from_time: str | None = None, to_time: str | None = None) -> list[dict[str, Any]]:
    sql = """
    SELECT COALESCE(actor->>'cli', 'unknown') AS cli, COUNT(*) AS count
    FROM events
    WHERE time >= %s AND time <= %s
    GROUP BY cli
    ORDER BY count DESC, cli ASC
    """
    with cursor() as cur:
        cur.execute(sql, (from_time or "1970-01-01", to_time or "2099-01-01"))
        rows = cur.fetchall()
    return [{"cli": row[0], "count": row[1]} for row in rows]


# Bucket widths the strip offers, in seconds. A closed set, like the window
# presets: an arbitrary width is another way to ask for a scan, and the strip
# only ever needs about 40 columns across whatever span is shown.
TIMELINE_BUCKETS = (1, 60, 300, 1800, 3600)

# Datadog's literal rule, and a good one: past six, colours repeat and a stacked
# bar stops being readable. The seventh series is the honest remainder.
MAX_TIMELINE_SERIES = 6


def timeline(
    *,
    bucket_seconds: int = 60,
    group: str = "class",
    from_time: str | None = None,
    to_time: str | None = None,
    **filters: str | None,
) -> dict[str, Any]:
    """Bucketed counts for the strip above the feed.

    Stacked by provenance CLASS rather than by event type, because 96% of the
    trail is one type and stacking by type renders a single solid block that
    answers nothing.

    Deliberately takes no `tools` argument. The strip counts every event that
    matches the SCOPE, including tool calls the feed is currently folding --
    so collapsing the feed never changes the shape of the chart above it. That
    is the honesty rule made mechanical: rows are collapsed, counts are not.
    """
    if bucket_seconds not in TIMELINE_BUCKETS:
        raise ValueError(f"bucket must be one of {TIMELINE_BUCKETS}")
    group_expr = {
        "class": PROVENANCE_EXPR,
        "project": PROJECT_LABEL_EXPR,
        "cli": "COALESCE(actor->>'cli', 'unknown')",
        "domain": "domain",
    }.get(group)
    if group_expr is None:
        raise ValueError("group must be one of class, project, cli, domain")

    where, params = _filters(from_time=from_time, to_time=to_time, **filters)
    clause = " AND ".join(where)

    # floor(epoch / width) * width is the bucket start. Cheaper and clearer
    # than date_trunc for widths date_trunc has no name for (5 min, 30 min).
    sql = f"""
    SELECT to_timestamp(floor(extract(epoch FROM time) / %s) * %s) AS bucket,
           {group_expr} AS series,
           COUNT(*) AS count
    FROM events
    WHERE {clause}
    GROUP BY 1, 2
    ORDER BY 1
    """
    with cursor() as cur:
        cur.execute(sql, [bucket_seconds, bucket_seconds, *params])
        rows = cur.fetchall()

    totals: Counter[str] = Counter()
    for _, series, count in rows:
        totals[series or "unknown"] += count
    keep = {name for name, _ in totals.most_common(MAX_TIMELINE_SERIES)}
    truncated = set(totals) - keep

    buckets: dict[str, Counter[str]] = {}
    for bucket, series, count in rows:
        name = series or "unknown"
        # The remainder is folded into one series rather than dropped, so the
        # bars still sum to the true total.
        key = name if name in keep else "other"
        buckets.setdefault(_iso(bucket), Counter())[key] += count

    return {
        "buckets": [
            {"bucket": bucket, "series": dict(counts), "total": sum(counts.values())}
            for bucket, counts in sorted(buckets.items())
        ],
        "series": sorted(keep) + (["other"] if truncated else []),
        # Echoed so the legend can print "1 min per column" verbatim -- a
        # histogram that does not say its resolution invites being misread.
        "bucket_seconds": bucket_seconds,
        "group_by": group,
        "truncated_series": sorted(truncated),
    }


def parse_time_bound(value: str | None) -> str | None:
    """Accept `-90m` / `-24h` / `-7d` alongside an ISO timestamp.

    A relative bound is what both the strip and a CLI actually want to say, and
    without it every caller reimplements the same subtraction slightly
    differently. Anything unrecognized is passed through untouched so the
    database still reports a genuine typo rather than this silently reshaping it.
    """
    if not value or not value.startswith("-"):
        return value
    match = re.fullmatch(r"-(\d+)([smhd])", value.strip())
    if not match:
        return value
    amount, unit = int(match.group(1)), match.group(2)
    seconds = amount * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return (datetime.now(UTC) - timedelta(seconds=seconds)).isoformat()


def list_projects(window_hours: int = DEFAULT_WINDOW_HOURS) -> dict[str, Any]:
    """The PJangler registry, each project with its event count in the window.

    Reads the `projects` projection rather than deriving a project list from
    the trail. `/summary/by-project` does the latter and it is why the old
    picker offered `dist`, `.agents`, `mirror` and `james-brennan.git` as
    choices -- and took 11.59 s to do it.

    A registry project with no events is included with count 0. It has to be:
    a freshly created project is unselectable otherwise, and that is exactly
    when someone goes looking for it.
    """
    counts_sql = f"""
    SELECT m.slug, COUNT(*) AS events
    FROM events e
    JOIN project_dir_map m ON m.work_dir = {WORK_DIR_EXPR}
    WHERE e.time >= NOW() - make_interval(hours => %s)
      AND m.slug IS NOT NULL
    GROUP BY m.slug
    """
    with cursor() as cur:
        cur.execute(counts_sql, (window_hours,))
        counts = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute(
            "SELECT slug, name, repo_path, ticket_prefix FROM projects ORDER BY slug"
        )
        registry = cur.fetchall()

    projects = [
        {
            "slug": row[0],
            "name": row[1],
            "repo_path": row[2],
            "ticket_prefix": row[3],
            "count": counts.get(row[0], 0),
        }
        for row in registry
    ]
    return {
        "projects": projects,
        # Echoed rather than baked into the field name: calling it `count_24h`
        # would be a lie the moment someone passes ?window=7d.
        "window_hours": window_hours,
    }


def list_classes(window_hours: int = DEFAULT_WINDOW_HOURS) -> dict[str, Any]:
    """Every provenance class with its colour, its count, and its blind spots.

    The counts come from the data; `coverage` is a declared property of the
    classifier. Both are served together on purpose -- a dot whose gaps are
    only written down in a ticket is a dot that lies by omission.
    """
    with cursor() as cur:
        cur.execute(
            f"SELECT {PROVENANCE_EXPR} AS class, COUNT(*) FROM events "
            "WHERE time >= NOW() - make_interval(hours => %s) GROUP BY 1",
            (window_hours,),
        )
        counts = {row[0]: row[1] for row in cur.fetchall()}
    return {
        "classes": [
            {"class": name, **meta, "count": counts.get(name, 0)}
            for name, meta in PROVENANCE_CLASSES.items()
        ],
        "window_hours": window_hours,
    }


def list_lenses(window_hours: int = DEFAULT_WINDOW_HOURS) -> dict[str, Any]:
    """Every lens with its count in the window, so a chip can show its size."""
    counts: dict[str, int] = {}
    with cursor() as cur:
        for name, meta in LENSES.items():
            cur.execute(
                f"SELECT COUNT(*) FROM events "
                f"WHERE time >= NOW() - make_interval(hours => %s) AND {meta['sql']}",
                (window_hours,),
            )
            counts[name] = cur.fetchone()[0]
    return {
        "lenses": [
            {
                "lens": name,
                "label": meta["label"],
                "description": meta["description"],
                "count": counts[name],
            }
            for name, meta in LENSES.items()
        ],
        "window_hours": window_hours,
    }


def known_project_slugs() -> set[str]:
    with cursor() as cur:
        cur.execute("SELECT slug FROM projects")
        return {row[0] for row in cur.fetchall()}


def by_project(from_time: str | None = None, to_time: str | None = None) -> list[dict[str, Any]]:
    sql = f"""
    SELECT {PROJECT_LABEL_EXPR} AS project, COUNT(*) AS count
    FROM events
    WHERE time >= %s AND time <= %s
    GROUP BY project
    ORDER BY count DESC, project ASC
    """
    with cursor() as cur:
        cur.execute(sql, (from_time or "1970-01-01", to_time or "2099-01-01"))
        rows = cur.fetchall()
    return [{"project": row[0], "count": row[1]} for row in rows]


def _filters(**kwargs: str | None) -> tuple[list[str], list[Any]]:
    """Build the WHERE fragments and params for a set of filters.

    Every filter is optional and read with `.get()`. It used to index kwargs
    directly, which quietly made every key MANDATORY -- so a caller that
    legitimately did not care about `type` got a KeyError rather than an
    unfiltered query, and every new caller had to pass the full set to work at
    all.
    """
    where = ["1=1"]
    params: list[Any] = []

    event_type = kwargs.get("type")
    if event_type:
        values = [value.strip() for value in event_type.split(",") if value.strip()]
        if len(values) == 1:
            where.append("type = %s")
            params.append(values[0])
        elif values:
            placeholders = ", ".join(["%s"] * len(values))
            where.append(f"type IN ({placeholders})")
            params.extend(values)
    scope = kwargs.get("scope")
    if scope:
        values = [value.strip() for value in scope.split(",") if value.strip()]
        conditions = []
        for value in values:
            parts = value.split(".")
            if len(parts) == 2:
                # domain.entity — match both, version-agnostically
                conditions.append(
                    f"split_part({SCOPE_TYPE_EXPR}, '.', 1) = %s "
                    f"AND split_part({SCOPE_TYPE_EXPR}, '.', 2) = %s"
                )
                params.extend(parts)
            elif len(parts) == 1:
                # domain only
                conditions.append(f"split_part({SCOPE_TYPE_EXPR}, '.', 1) = %s")
                params.append(parts[0])
        if conditions:
            where.append(f"({' OR '.join(conditions)})")
    if kwargs.get("domain"):
        where.append("domain = %s")
        params.append(kwargs.get("domain"))
    if kwargs.get("from_time"):
        where.append("time >= %s")
        params.append(kwargs.get("from_time"))
    if kwargs.get("to_time"):
        where.append("time <= %s")
        params.append(kwargs.get("to_time"))
    if kwargs.get("correlationid"):
        where.append("correlationid::text = %s")
        params.append(kwargs.get("correlationid"))
    if kwargs.get("producer"):
        where.append("producer = %s")
        params.append(kwargs.get("producer"))
    if kwargs.get("service"):
        where.append("service = %s")
        params.append(kwargs.get("service"))
    if kwargs.get("cli"):
        where.append("actor->>'cli' = %s")
        params.append(kwargs.get("cli"))
    lens = kwargs.get("lens")
    if lens:
        values = [value.strip() for value in lens.split(",") if value.strip()]
        clauses = [LENSES[value]["sql"] for value in values if value in LENSES]
        if clauses:
            where.append(f"({' OR '.join(clauses)})")
    provenance = kwargs.get("provenance")
    if provenance:
        values = [value.strip() for value in provenance.split(",") if value.strip()]
        if values:
            # Multi-select within one facet is OR. Across facets it is AND.
            # That rule is the substitute for a query grammar, so it is applied
            # identically everywhere rather than per-endpoint.
            placeholders = ", ".join(["%s"] * len(values))
            where.append(f"{PROVENANCE_EXPR} IN ({placeholders})")
            params.extend(values)
    if kwargs.get("project"):
        # A registry slug, resolved the same way PROJECT_EXPR resolves it -- not
        # a substring of a basename. The old `PROJECT_EXPR ILIKE '%...%'` was
        # wrong in both directions: it matched `intelliforia` against
        # `intelliforia-mobile`, and it missed every worktree whose basename
        # does not contain the project name. It was also non-sargable, so it
        # cost a full scan (measured 8.45 s; the planner estimated 37 rows
        # against 118,745).
        #
        where.append(PROJECT_FILTER_EXPR)
        params.extend([kwargs.get("project")] * 4)
    if kwargs.get("q") and kwargs.get("q").strip():
        clause, search_params = _search_clause(kwargs.get("q"))
        where.append(clause)
        params.extend(search_params)

    return where, params


def _search_clause(q: str) -> tuple[str, list[Any]]:
    """Build the WHERE fragment for a free-text `q`.

    Raises SearchError on a term the trigram index cannot serve; main.py turns
    that into a 400 rather than letting it become a minutes-long scan.
    """
    text = q.strip()

    # A bare UUID is an id, not prose. Pasting an event id or a session
    # (correlation) id into the search box is the single most common thing an
    # operator does with one, and both columns are btree-indexed -- so answer it
    # exactly and instantly instead of trigram-scanning for a 36-character
    # string that `search_text` deliberately does not even contain (UUID
    # trigrams are near-uniform hex and would bloat the index for nothing).
    event_id = _as_uuid(text)
    if event_id:
        return "(id = %s::uuid OR correlationid = %s::uuid)", [event_id, event_id]

    # Whitespace separates terms that must ALL match, rather than one literal
    # phrase: `search_text` is a concatenation of fields, so `candystore Edit`
    # meaning "an Edit tool call in candystore" is both the useful reading and
    # the only one that can match across two fields.
    terms = text.split()
    short = sorted({term for term in terms if len(term) < SEARCH_MIN_TERM})
    if short:
        raise SearchError(
            f"search terms must be at least {SEARCH_MIN_TERM} characters: "
            f"{', '.join(repr(term) for term in short)}"
        )

    clause = " AND ".join(["search_text ILIKE %s"] * len(terms))
    params = [f"%{term.translate(_LIKE_ESCAPES)}%" for term in terms]
    return f"({clause})", params


def applied_window(
    from_time: str | None,
    to_time: str | None,
    *,
    correlationid: str | None = None,
    q: str | None = None,
    hours: int = DEFAULT_WINDOW_HOURS,
    now: datetime | None = None,
) -> tuple[str | None, str | None]:
    """Resolve the time window an interactive browse should actually run over.

    Returns the (from, to) to hand to `list_events`. Pure: no DB, so the policy
    is testable without a database (see tests/test_window.py).

    Exactly one thing is ever invented: a missing `from`. `to` is passed
    through untouched, because a floor is what makes a query cheap and a
    ceiling is not -- `?to=2026-01-01` with no floor is still a scan of every
    row before that date, which is the case this function exists to prevent.

    The invented floor is anchored to `to_time` when there is one, not to
    wall-clock now. A now-relative floor under `?to=2026-01-01` would describe
    a window that ends eight months before it starts, return nothing, and read
    as "no events" instead of "you asked for an empty range".

    An explicit `from` is never overridden -- naming a floor is a statement
    that you want that floor.

    Point lookups are exempt, and this is the part that is easy to get wrong.
    `correlationid` and a bare-UUID `q` both resolve through a btree index to a
    handful of rows, and they are how the UI answers its two most common
    questions: pasting an event or session id into the search box, and
    following a session drill-down. Windowing them would break "paste an id,
    find the event" for anything older than a day -- which, on an audit trail,
    is nearly everything.
    """
    if from_time:
        return from_time, to_time
    if correlationid or (q and _as_uuid(q.strip())):
        return None, to_time
    end = _parse_time(to_time) or (now or datetime.now(UTC))
    return (end - timedelta(hours=hours)).isoformat(), to_time


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _as_uuid(value: str) -> str | None:
    try:
        return str(UUID(value))
    except (ValueError, AttributeError, TypeError):
        return None


def _extract_session_dialog(
    turn_rows: Any,
) -> dict[str, str]:
    """Derive a session's opening prompt and latest reply from its ordered turn rows."""
    dialog: dict[str, str] = {}
    for event_type, data in turn_rows:
        if not isinstance(data, dict):
            continue
        kind = canonical_type(event_type)
        if kind == TURN_STARTED_TYPE and "prompt_text" not in dialog:
            prompt = _prompt_text(data)
            if prompt:
                dialog["prompt_text"] = prompt
        elif kind == TURN_COMPLETED_TYPE:
            reply = _reply_text(data)
            if reply:
                dialog["reply_text"] = reply
            if "prompt_text" not in dialog:
                prompt = _prompt_text(data)
                if prompt:
                    dialog["prompt_text"] = prompt
    return dialog


def _fetch_session_dialog(
    cur: Any,
    correlation_ids: list[str],
) -> dict[str, dict[str, str]]:
    """Batch-resolve initial prompt and final reply for a set of session correlation IDs."""
    valid_ids = sorted({cid for cid in correlation_ids if _as_uuid(cid)})
    if not valid_ids:
        return {}
    cur.execute(
        """
        SELECT correlationid::text, type, data
        FROM events
        WHERE correlationid = ANY(%s::uuid[])
          AND type IN (
              'bloodbank.conversation.turn.started',
              'bloodbank.v1.conversation.turn.started',
              'bloodbank.conversation.turn.completed',
              'bloodbank.v1.conversation.turn.completed'
          )
        ORDER BY time ASC
        """,
        (valid_ids,),
    )
    grouped: dict[str, list[tuple[str, Any]]] = {}
    for cid, event_type, data in cur.fetchall():
        grouped.setdefault(cid, []).append((event_type, data))
    return {cid: _extract_session_dialog(turns) for cid, turns in grouped.items()}


def _merge_session_dialog(
    raw: Any,
    data: Any,
    event_type: Any,
    dialog: dict[str, str] | None,
) -> tuple[Any, Any]:
    """Attach correlated session prompt/reply onto session.started and session.ended."""
    if not dialog or not isinstance(raw, dict):
        return raw, data
    kind = canonical_type(event_type)
    if kind not in SESSION_TYPES:
        return raw, data

    merged_data = dict(data) if isinstance(data, dict) else {}
    changed = False
    if "prompt_text" in dialog and not _prompt_text(merged_data):
        merged_data["prompt_text"] = dialog["prompt_text"]
        changed = True
    if kind in SESSION_END_TYPES and "reply_text" in dialog and not _reply_text(merged_data):
        merged_data["reply_text"] = dialog["reply_text"]
        changed = True
    if not changed:
        return raw, data
    return {**raw, "data": merged_data}, merged_data


def _preview_from_row(
    row: tuple[Any, ...],
    dialog: dict[str, str] | None = None,
) -> dict[str, Any]:
    raw, data = _merge_session_dialog(row[9], row[7], row[1], dialog)
    summary = summarize(raw, row[10], row[11])
    actor = row[6] or {}
    event = {
        "id": str(row[0]),
        "type": row[1],
        "time": _iso(row[2]),
        "producer": row[3],
        "service": row[4],
        "domain": row[5],
        "actor": actor,
        "data": data,
        "correlationid": str(row[8]) if row[8] else None,
        "cli": actor.get("cli"),
        "project": row[10],
        "class": row[11],
        "summary": summary,
    }
    # Extension fields that the preview's column list does not model still
    # need to reach API consumers — agents deciding what to do with an event
    # from a dying worktree session cannot wait for a raw-column query.
    if isinstance(raw, dict) and raw.get("ephemeral") is not None:
        event["ephemeral"] = raw["ephemeral"]
    return event


def _session_project(events: list[dict[str, Any]]) -> str | None:
    """The session's project: the first resolved slug among its events.

    Scanning rather than reading events[0] because a session can legitimately
    start outside a registered project and move into one -- 472 of 2,204
    measured sessions span more than one directory. `None` when nothing in the
    session resolves.
    """
    for event in events:
        if event.get("project"):
            return str(event["project"])
    return None


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return str(value)


def _duration_seconds(started_at: str | None, ended_at: str | None) -> int | None:
    if not started_at or not ended_at:
        return None
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return int((end - start).total_seconds())


