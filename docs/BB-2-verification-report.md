# BB-2 Verification Report: asset_registry Schema + Event

**Date:** 2026-03-11  
**Author:** Lenoon (infra)  
**Status:** VERIFIED ✅ (with 1 gap noted)

## Schema ↔ Migration Alignment

| Check | Result |
|-------|--------|
| Field count | ✅ 17/17 matched |
| Required fields | ✅ 10/10 matched (NOT NULL ↔ required) |
| asset_type enum | ✅ 5/5 (invite, font, coloring_page, mockup, listing_copy) |
| status enum | ✅ 3/3 (active, revised, deleted) |
| storage_uri regex | ✅ `^(file\|gs\|https\|s3\|volume)://` |
| Trigger payload | ✅ 17/17 fields emitted |

## Database State (33god-postgres)

| Item | Status |
|------|--------|
| Table `asset_registry` | ✅ EXISTS |
| Columns | ✅ 17 columns, types match schema |
| PK (asset_id UUID) | ✅ gen_random_uuid() default |
| FK (lineage_parent_asset_id → self) | ✅ ON DELETE SET NULL |
| Trigger: `trg_asset_registry_set_updated_at` | ✅ ACTIVE |
| Trigger: `trg_asset_registry_emit_created_event` | ✅ ACTIVE (pg_notify → bloodbank_events) |
| Indexes | ✅ 7 indexes (agent_name, correlation_id, asset_type, status, content_hash UNIQUE, model_params GIN, PK) |
| Row count | 3 rows |

## Holyfields Schema

- **Path:** `holyfields/schemas/asset/created.v1.json`
- **Status:** DEPRECATED (marked in title)
- **Successor:** `artifact/lifecycle.v1.json` (uses base_event.v1.json `allOf` pattern)
- **Generated Pydantic model:** `AssetCreatedV1` — **EMPTY BODY** (gap, see below)

## Gap: Empty Generated Model

The `asset/created.v1.json` schema uses `additionalProperties: false` at top level without the `allOf` base_event reference pattern. The Pydantic generator strips all fields, producing an empty model class.

**Impact:** Low — schema is deprecated. The replacement `artifact/lifecycle.v1.json` uses the correct `allOf` pattern and generates properly.

**Recommendation:** Do NOT fix the deprecated schema. Instead:
1. Keep `asset/created.v1.json` as-is for backwards compatibility
2. New code should use `artifact.lifecycle.v1` events
3. Consider adding a migration to emit `artifact.created` from the INSERT trigger (replacing `asset.created`)

## Event Flow

```
INSERT into asset_registry
  → trg_asset_registry_emit_created_event (PL/pgSQL)
  → pg_notify('bloodbank_events', payload)
  → postgres-notify-bridge (if running) picks up NOTIFY
  → publishes to bloodbank.events.v1 exchange as asset.created
```

## Migration Status

The migration `20260221_001_asset_registry.sql` has been **applied** and is live:
- Table, triggers, indexes all present
- 3 existing rows in production
- pg_notify trigger emitting `asset.created` events on INSERT

**No new migration needed** — schema and database are fully aligned.

## Files Verified

| File | Location |
|------|----------|
| Holyfields schema | `holyfields/schemas/asset/created.v1.json` |
| Migration | `services/candystore/migrations/20260221_001_asset_registry.sql` |
| Generated model | `holyfields/src/holyfields/generated/python/asset/created_v1.py` |
| Successor schema | `holyfields/schemas/artifact/lifecycle.v1.json` |
