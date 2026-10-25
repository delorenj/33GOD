-- Poison-safety (CANDYS E1). Idempotent (IF NOT EXISTS) so it is safe under the
-- current no-ledger init_schema and does not block on the schema_migrations
-- ledger (CANDYS-24).

-- Durable record of every event candystore REFUSED to store (malformed JSON,
-- failed validation, or a PostgreSQL data error). `raw` is BYTEA so the exact
-- original bytes — including any U+0000 NUL that jsonb/text cannot hold — are
-- preserved for inspection and replay after a producer fix. This is what makes
-- a DROP recoverable instead of silent loss (never-lose-an-event).
CREATE TABLE IF NOT EXISTS dead_letter (
    id           BIGSERIAL PRIMARY KEY,
    event_id     TEXT,
    topic        TEXT,
    reason       TEXT NOT NULL,
    error        TEXT,
    raw          BYTEA NOT NULL,
    received_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dead_letter_received_at ON dead_letter(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_dead_letter_reason ON dead_letter(reason);

-- Marker for rows whose payload contained a PostgreSQL-unstorable value
-- (e.g. a U+0000 NUL in captured tool I/O) that was stripped before insert so
-- the event could still be persisted. FALSE for normal rows. Lets the trail
-- answer "which records did we have to alter to store?".
ALTER TABLE events ADD COLUMN IF NOT EXISTS sanitized BOOLEAN NOT NULL DEFAULT FALSE;
