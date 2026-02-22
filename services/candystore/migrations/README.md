# Candystore Migrations

Database migrations for the 33GOD Postgres instance.

## Applied Migrations

### 20260221_001_asset_registry.sql

**Status**: ✅ Applied to `33god-postgres` on 2026-02-21

**Purpose**: Create `asset_registry` table for tracking AI-generated assets across the 33GOD ecosystem with automatic event emission to Bloodbank.

**Features**:
- Asset tracking with full lineage (parent/child relationships)
- Automatic `asset.created` event emission via Postgres NOTIFY
- Content deduplication via unique content_hash
- Support for multiple asset types (invite, font, coloring_page, mockup, listing_copy)
- Model provenance tracking (provider, name, params)
- Correlation tracking via correlation_id

**Event Flow**:
1. Row inserted into `asset_registry`
2. Trigger `trg_asset_registry_emit_created_event` fires
3. Function `asset_registry_emit_created_event()` builds event payload
4. Postgres `pg_notify('bloodbank_events', payload)` sends notification
5. `postgres-notify-bridge` service receives NOTIFY
6. Bridge POSTs to Bloodbank `/publish` endpoint
7. Bloodbank publishes to RabbitMQ exchange `bloodbank.events.v1`
8. Event routed to consumers via routing key `asset.created`

**Schema**:
- See: `holyfields/schemas/asset/created.v1.json`

## Applying Migrations

Manual application:
```bash
cat migrations/20260221_001_asset_registry.sql | \
  docker exec -i 33god-postgres psql -U delorenj -d 33god
```

Verify:
```bash
docker exec 33god-postgres psql -U delorenj -d 33god -c "\d asset_registry"
```

## Testing

Insert test asset:
```sql
INSERT INTO asset_registry (
  agent_name,
  asset_type,
  storage_uri,
  storage_provider,
  content_hash,
  correlation_id
) VALUES (
  'test-agent',
  'mockup',
  'file:///test/sample.png',
  'local',
  'sha256:test123',
  gen_random_uuid()
);
```

Verify event published:
```bash
# Check bridge logs
docker logs 33god-postgres-notify-bridge --tail 20

# Check bloodbank logs
docker logs 33god-bloodbank --tail 20 | grep asset
```
