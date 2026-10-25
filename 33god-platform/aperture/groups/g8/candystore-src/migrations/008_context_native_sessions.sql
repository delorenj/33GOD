-- Historical producers used non-UUID session IDs, which remain in raw/data
-- even when the normalized correlation column is NULL. Keep those sessions
-- queryable without rewriting the audit trail. New UUID sessions use 001's
-- existing correlation/time index. This is safe under migration replay.
CREATE INDEX IF NOT EXISTS idx_events_native_session_time ON events (
    (COALESCE(
        NULLIF(data->>'session_id', ''), NULLIF(data->>'thread_id', ''),
        NULLIF(data->'payload'->>'session_id', ''),
        NULLIF(data->'payload'->>'conversationId', ''),
        NULLIF(data->'payload'->'session'->>'id', ''),
        NULLIF(raw->>'correlationid', '')
    )), time DESC
) WHERE correlationid IS NULL;

-- Session discovery seeks the newest work within each registered directory.
-- Time alone is insufficient: an inactive project's most recent event can
-- sit behind millions of newer events from unrelated projects.
CREATE INDEX IF NOT EXISTS idx_events_context_workdir_time ON events (
    (COALESCE(NULLIF(data->>'working_directory', ''), NULLIF(data->'payload'->>'cwd', ''))),
    time DESC
);
CREATE INDEX IF NOT EXISTS idx_events_context_project_time ON events (
    (NULLIF(data->>'project', '')), time DESC
) WHERE NULLIF(data->>'project', '') IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_events_context_repo_time ON events (
    (lower(NULLIF(data->>'repo', ''))), time DESC
) WHERE NULLIF(data->>'repo', '') IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_events_context_slug_time ON events (
    (lower(NULLIF(data->>'slug', ''))), time DESC
) WHERE NULLIF(data->>'slug', '') IS NOT NULL;

-- Busy projects have many hook-observation receipts in each directory. A
-- newest-agent-work probe must not walk all those receipts (or subagents) to
-- find one root session. Keep the predicate aligned with context.py's
-- _TOP_LEVEL; include id for deterministic timestamp ties. A simple predicate
-- avoids expensive implication checks on the lifecycle scope's many ORs.
CREATE INDEX IF NOT EXISTS idx_events_context_agent_workdir_time ON events (
    (COALESCE(NULLIF(data->>'working_directory', ''), NULLIF(data->'payload'->>'cwd', ''))),
    time DESC, id DESC
) WHERE NULLIF(actor->>'cli', '') IS NOT NULL
    AND NULLIF(data->'payload'->>'agent_id', '') IS NULL
    AND NULLIF(data->>'parent_invocation_id', '') IS NULL
    AND COALESCE(data->>'hook', data->'payload'->>'hook_event_name', '') != 'SubagentStop'
    AND type != 'bloodbank.agent.hook.updated';
