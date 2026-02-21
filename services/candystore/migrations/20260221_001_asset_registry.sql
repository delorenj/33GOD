-- 20260221_001_asset_registry.sql
-- 33GOD Postgres migration: asset_registry + asset.created emission trigger

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS asset_registry (
    asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    asset_type TEXT NOT NULL CHECK (asset_type IN (
        'invite', 'font', 'coloring_page', 'mockup', 'listing_copy'
    )),
    storage_uri TEXT NOT NULL,
    storage_provider TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    prompt_text TEXT,
    model_provider TEXT,
    model_name TEXT,
    model_params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_event_id UUID,
    correlation_id UUID NOT NULL,
    lineage_parent_asset_id UUID NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revised', 'deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,

    CONSTRAINT fk_asset_registry_parent
      FOREIGN KEY (lineage_parent_asset_id)
      REFERENCES asset_registry(asset_id)
      ON DELETE SET NULL,

    CONSTRAINT chk_asset_storage_uri_scheme
      CHECK (storage_uri ~ '^(file|gs|https|s3|volume)://')
);

CREATE INDEX IF NOT EXISTS idx_asset_registry_agent_name
  ON asset_registry(agent_name);

CREATE INDEX IF NOT EXISTS idx_asset_registry_correlation_id
  ON asset_registry(correlation_id);

CREATE INDEX IF NOT EXISTS idx_asset_registry_asset_type
  ON asset_registry(asset_type);

CREATE INDEX IF NOT EXISTS idx_asset_registry_status
  ON asset_registry(status);

CREATE UNIQUE INDEX IF NOT EXISTS idx_asset_registry_content_hash
  ON asset_registry(content_hash);

CREATE INDEX IF NOT EXISTS idx_asset_registry_model_params_gin
  ON asset_registry USING GIN (model_params_json);

CREATE OR REPLACE FUNCTION asset_registry_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_asset_registry_set_updated_at ON asset_registry;
CREATE TRIGGER trg_asset_registry_set_updated_at
BEFORE UPDATE ON asset_registry
FOR EACH ROW
EXECUTE FUNCTION asset_registry_set_updated_at();

-- Emit asset.created event on INSERT.
-- Uses PostgreSQL NOTIFY channel as Bloodbank handoff bridge.
CREATE OR REPLACE FUNCTION asset_registry_emit_created_event()
RETURNS TRIGGER AS $$
DECLARE
  payload JSONB;
BEGIN
  payload := jsonb_build_object(
    'event_type', 'asset.created',
    'payload', jsonb_build_object(
      'asset_id', NEW.asset_id,
      'agent_name', NEW.agent_name,
      'asset_type', NEW.asset_type,
      'storage_uri', NEW.storage_uri,
      'storage_provider', NEW.storage_provider,
      'content_hash', NEW.content_hash,
      'prompt_text', NEW.prompt_text,
      'model_provider', NEW.model_provider,
      'model_name', NEW.model_name,
      'model_params_json', NEW.model_params_json,
      'source_event_id', NEW.source_event_id,
      'correlation_id', NEW.correlation_id,
      'lineage_parent_asset_id', NEW.lineage_parent_asset_id,
      'status', NEW.status,
      'created_at', NEW.created_at,
      'updated_at', NEW.updated_at,
      'deleted_at', NEW.deleted_at
    )
  );

  PERFORM pg_notify('bloodbank_events', payload::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_asset_registry_emit_created_event ON asset_registry;
CREATE TRIGGER trg_asset_registry_emit_created_event
AFTER INSERT ON asset_registry
FOR EACH ROW
EXECUTE FUNCTION asset_registry_emit_created_event();
