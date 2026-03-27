-- ============================================================================
-- Migration 001: Create echobox_ledger table
-- Tracks audio transcription jobs through their full lifecycle.
-- Idempotent: safe to re-run.
-- ============================================================================

-- Required for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ----------------------------------------------------------------------------
-- Table: echobox_ledger
-- Primary key is content_hash (SHA256 of source audio), ensuring exactly one
-- ledger entry per unique audio file. job_id provides a UUID handle for
-- external references and API consumers.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS echobox_ledger (
    -- Identity
    content_hash        TEXT        PRIMARY KEY,
    job_id              UUID        NOT NULL DEFAULT gen_random_uuid(),

    -- Job lifecycle
    status              TEXT        NOT NULL DEFAULT 'detected'
                        CHECK (status IN (
                            'detected',
                            'hashing',
                            'uploading',
                            'uploaded',
                            'transcribing',
                            'ready',
                            'writing',
                            'completed',
                            'failed',
                            'skipped'
                        )),

    -- Source file metadata
    source_path         TEXT,
    source_filename     TEXT,
    source_mime         TEXT,
    source_size_bytes   BIGINT,

    -- MinIO object storage
    minio_bucket        TEXT,
    minio_key           TEXT,
    minio_url           TEXT,

    -- Fireflies integration
    fireflies_id        TEXT,
    fireflies_ref       TEXT,

    -- Output artifacts
    transcript_path     TEXT,
    csv_path            TEXT,

    -- Event correlation
    event_id            UUID,
    correlation_ids     TEXT[]      NOT NULL DEFAULT '{}',

    -- Error tracking
    error_message       TEXT,
    error_stage         TEXT,
    retry_count         INTEGER     NOT NULL DEFAULT 0,

    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

-- ----------------------------------------------------------------------------
-- Indexes
-- ----------------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS idx_echobox_ledger_job_id
    ON echobox_ledger (job_id);

CREATE INDEX IF NOT EXISTS idx_echobox_ledger_status
    ON echobox_ledger (status);

CREATE INDEX IF NOT EXISTS idx_echobox_ledger_fireflies_id
    ON echobox_ledger (fireflies_id);

CREATE INDEX IF NOT EXISTS idx_echobox_ledger_fireflies_ref
    ON echobox_ledger (fireflies_ref);

CREATE INDEX IF NOT EXISTS idx_echobox_ledger_created_at
    ON echobox_ledger (created_at);

CREATE INDEX IF NOT EXISTS idx_echobox_ledger_source_path
    ON echobox_ledger (source_path);

-- ----------------------------------------------------------------------------
-- Trigger function: auto-update updated_at on any row modification
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION echobox_ledger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop-and-recreate is idempotent for triggers (no IF NOT EXISTS for triggers)
DROP TRIGGER IF EXISTS trg_echobox_ledger_updated_at ON echobox_ledger;

CREATE TRIGGER trg_echobox_ledger_updated_at
    BEFORE UPDATE ON echobox_ledger
    FOR EACH ROW
    EXECUTE FUNCTION echobox_ledger_set_updated_at();

-- ----------------------------------------------------------------------------
-- Trigger function: auto-set completed_at when status transitions to 'completed'
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION echobox_ledger_set_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND (OLD.status IS DISTINCT FROM 'completed') THEN
        NEW.completed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_echobox_ledger_completed_at ON echobox_ledger;

CREATE TRIGGER trg_echobox_ledger_completed_at
    BEFORE UPDATE ON echobox_ledger
    FOR EACH ROW
    EXECUTE FUNCTION echobox_ledger_set_completed_at();
