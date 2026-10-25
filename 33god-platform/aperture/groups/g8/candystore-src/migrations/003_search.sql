-- Free-text search over the event trail (the /events `q` parameter).
--
-- Idempotent (IF NOT EXISTS / OR REPLACE) to match 001 and 002: init_schema()
-- replays every migration on each boot.

-- Trigram matching is what an audit trail actually needs. Its search terms are
-- file paths, tool names, branch names and command fragments -- `query.py`,
-- `33GOD/candystore`, `--no-verify`. A tsvector/FTS index word-stems and
-- tokenizes those into uselessness; trigrams match an arbitrary substring.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- One denormalized, lowercased haystack per event.
--
-- GENERATED ... STORED rather than an expression index, for two reasons:
--   1. It cannot drift. An expression index would force the exact same
--      expression to be repeated in query.py, and a silent mismatch there does
--      not error -- it just stops using the index and full-scans 871k rows.
--   2. `data` is TOASTed (avg 2.7 KB, max 599 KB). An expression index has to
--      detoast every candidate row to recheck the match; a stored column is
--      read inline off the heap page.
--
-- Field order is load-bearing: cheap, high-signal identity fields first, so the
-- total cap can only ever eat into prose. What is IN the haystack was measured
-- against the live corpus rather than guessed, and the first guess was wrong
-- twice (see 004_search_caps.sql for the numbers):
--
--   * `arguments` is the single most valuable field, not the noisy one. It is
--     on 89.4% of rows and it is where file paths and commands live. Removing
--     it takes `query.py` from 279 hits to 2.
--   * `payload` and `input_preview` are NOT here on purpose. input_preview is
--     present on 0 rows; payload's indexed window is 85.5% UUID, which re-imports
--     exactly the near-uniform hex trigrams this index excludes UUIDs to avoid.
--   * `prompt_text` gets a large cap because prompt-bearing rows are only 0.69%
--     of the trail, so generosity there is nearly free.
ALTER TABLE events ADD COLUMN IF NOT EXISTS search_text TEXT
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

-- gin_trgm_ops answers ILIKE '%term%'. Note the index can only help a pattern
-- of 3+ characters -- shorter terms have no full trigram and degrade to a seq
-- scan, which is why query.py refuses to run one. ~275 MB at 871k rows, and
-- growth is linear in row count from here (the sublinear regime where new rows
-- mostly repeat existing trigrams saturates around 200k rows).
CREATE INDEX IF NOT EXISTS idx_events_search_trgm ON events USING GIN (search_text gin_trgm_ops);
