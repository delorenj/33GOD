-- The previous index (idx_events_native_session_time) had a WHERE correlationid IS NULL clause.
-- However, context.py queries for the correlation ID alias of a native session using:
--   NATIVE_SESSION_EXPR = %s AND correlationid IS NOT NULL
-- We need an index that covers correlationid IS NOT NULL to prevent sequential scans
-- that trigger the 2.5s statement timeout.
CREATE INDEX IF NOT EXISTS idx_events_native_session_alias_time ON events (
    (COALESCE(
        NULLIF(data->>'session_id', ''), NULLIF(data->>'thread_id', ''),
        NULLIF(data->'payload'->>'session_id', ''),
        NULLIF(data->'payload'->>'conversationId', ''),
        NULLIF(data->'payload'->'session'->>'id', ''),
        NULLIF(raw->>'correlationid', '')
    )), time DESC
) WHERE correlationid IS NOT NULL;
