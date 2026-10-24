-- Re-cap `search_text` on a database that already has 003's first-guess policy.
--
-- 003 originally indexed six prose fields under a 512-char total cap. Measured
-- against the live 871k-row corpus, two of those were dead weight and the total
-- cap was the binding constraint, not the per-field ones:
--
--   * `input_preview` was present on 0 of 871,438 rows. It was copied from a
--     key summarize.py probes defensively, never checked against the corpus,
--     and burned a 256-char slot on 100% of rows.
--   * `payload`'s indexed 256-char window is
--     `{"cwd":..,"turn_id":<uuid>,"tool_name":..,"session_id":<uuid>}`:
--     85.5% carry a UUID -- re-importing the near-uniform hex trigrams this
--     index excludes UUIDs to avoid -- 82% duplicate the separately-indexed
--     tool_name, 71% merely restate `arguments`, and only 48% are distinct.
--     It cost 14% of the index for a median 0.8% recall loss. Dropping it
--     RAISES recall on several terms (`candystore` 8,444 -> 8,545) because the
--     freed budget lets more of `arguments` clear the cap.
--   * The 512 total cap truncated 291,238 rows -- 33.4% of the trail.
--   * `prompt_text` is on only 6,007 rows (0.69%), so a 4000-char cap is nearly
--     free and takes fully-indexed prompts from 50.0% to 88.2%.
--
-- Net, measured same-table at full scale with real GIN indexes on both columns:
-- 345,538,560 B -> 296,976,384 B, a 14% SMALLER index that searches more.
--
-- `arguments` deliberately stays at 256. It is on 89.4% of rows and is the most
-- valuable field in the haystack -- removing it takes `query.py` from 279 hits
-- to 2 and `git push --force` from 65 to 0. Widening it to 512 would close the
-- largest remaining gap (360,109 rows still lose a tail, median 267 chars) but
-- that configuration was never measured, and this file does not ship unmeasured
-- numbers.
--
-- 003_search.sql is the SOURCE OF TRUTH for the expression; it already carries
-- the final form, so a fresh database gets it in one pass and skips this file
-- entirely. The copy below exists only to carry an ALREADY-MIGRATED database
-- across, and the two must stay identical -- tests/test_search.py asserts the
-- resulting column expression directly, from whichever path built it.

DO $$
DECLARE
    stored_expression text;
BEGIN
    SELECT pg_get_expr(d.adbin, d.adrelid)
      INTO stored_expression
      FROM pg_attrdef d
      JOIN pg_attribute a ON a.attrelid = d.adrelid AND a.attnum = d.adnum
     WHERE d.adrelid = 'events'::regclass
       AND a.attname = 'search_text';

    -- `input_preview` is an exact "not yet migrated" marker: 003's original
    -- expression contained it and no later expression ever will. A fresh
    -- database reaches this line with 003's final expression already in place
    -- and returns immediately -- which is what stops init_schema(), who replays
    -- every migration on every boot, from re-rewriting a 4.9 GB table each time
    -- the container restarts.
    IF stored_expression IS NULL OR stored_expression NOT LIKE '%input_preview%' THEN
        RETURN;
    END IF;

    -- A generated column's expression cannot be altered in place, so this is a
    -- full table rewrite under ACCESS EXCLUSIVE (~2 min at 871k rows / 4.9 GB)
    -- plus an index rebuild. Ingest blocks for the duration; Dapr's POST times
    -- out, JetStream redelivers, and the insert is idempotent on CloudEvent id,
    -- so nothing is lost -- but do not run it during a burst.
    ALTER TABLE events DROP COLUMN IF EXISTS search_text;  -- takes its GIN index with it

    ALTER TABLE events ADD COLUMN search_text TEXT
    GENERATED ALWAYS AS (
        left(
            lower(
                coalesce(type, '') || ' ' ||
                coalesce(subject, '') || ' ' ||
                coalesce(producer, '') || ' ' ||
                coalesce(service, '') || ' ' ||
                coalesce(domain, '') || ' ' ||
                coalesce(actor ->> 'cli', '') || ' ' ||
                coalesce(actor ->> 'provider', '') || ' ' ||
                coalesce(data ->> 'project', '') || ' ' ||
                coalesce(data ->> 'working_directory', '') || ' ' ||
                coalesce(data ->> 'git_branch', '') || ' ' ||
                coalesce(data ->> 'git_remote', '') || ' ' ||
                coalesce(data ->> 'repo', '') || ' ' ||
                coalesce(data ->> 'hook', '') || ' ' ||
                coalesce(data ->> 'tool_name', '') || ' ' ||
                coalesce(data ->> 'name', '') || ' ' ||
                coalesce(data ->> 'agent', '') || ' ' ||
                coalesce(data ->> 'agent_name', '') || ' ' ||
                coalesce(data ->> 'model', '') || ' ' ||
                coalesce(data ->> 'status', '') || ' ' ||
                coalesce(data ->> 'outcome', '') || ' ' ||
                coalesce(data ->> 'final_status', '') || ' ' ||
                coalesce(data ->> 'end_reason', '') || ' ' ||
                coalesce(data ->> 'stop_reason', '') || ' ' ||
                left(coalesce(data ->> 'error', ''), 200) || ' ' ||
                left(coalesce(data ->> 'error_message', ''), 200) || ' ' ||
                left(coalesce(data ->> 'prompt_text', ''), 4000) || ' ' ||
                left(coalesce(data ->> 'arguments', ''), 256)
            ),
            4096
        )
    ) STORED;
END $$;

-- Recreated here because the DROP COLUMN above took it. IF NOT EXISTS so the
-- fresh-database path, where 003 already built it, is a no-op.
CREATE INDEX IF NOT EXISTS idx_events_search_trgm ON events USING GIN (search_text gin_trgm_ops);
