# Candystore Architecture

> **Status:** Draft  
> **Date:** 2026-05-24  
> **Scope:** Event audit trail and observability for the 33GOD Bloodbank v3 ecosystem  
> **Goal:** "DataDog for events" — persistent, queryable, pretty-printed event history with heat-map activity views.

---

## 1. Problem Statement

Bloodbank v3 emits CloudEvents 1.0 envelopes over NATS JetStream. Today there is no durable system of record. The existing `claude-events-recorder` and `heartbeat-recorder` are in-memory test bookends (FIFO eviction at 1,024 events). When an agent runs for 12 hours, there is no way to:

- See what happened during the session
- Filter events by project / time window / agent CLI type
- View a readable summary instead of a raw JSON blob
- Understand activity patterns across days

Candystore closes this gap.

---

## 2. Design Principles

1. **Never lose an event** — persist before ack, durable consumer offset
2. **Bloodbank-native** — speak the same CloudEvents 1.0 envelope, Dapr sidecar pattern, stdlib-first Python
3. **Query-first schema** — indexes on every filter dimension the UI needs
4. **Pretty-print by default** — event-type-specific summarizers, raw envelope available on demand
5. **Monorepo-citizen** — lives in `~/code/33GOD/candystore/`, wired into `bloodbank/compose/docker-compose.yml`

---

## 3. System Context

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────────┐
│  Claude Code    │     │  Copilot CLI │     │  heartbeat-tick     │
│  (host hook)    │     │  (host hook) │     │  (container)        │
└────────┬────────┘     └──────┬───────┘     └──────────┬──────────┘
         │                     │                        │
         └─────────────────────┴────────────────────────┘
                                 │
                      NATS JetStream
                    bloodbank.evt.v1.>
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
    ┌─────────▼──────────┐              ┌───────────▼────────────┐
    │  Dapr sidecar      │              │  Dapr sidecar          │
    │  (daprd-candystore)│              │  (daprd-claude-events) │
    └─────────┬──────────┘              └───────────┬────────────┘
              │                                      │
    ┌─────────▼──────────┐              ┌───────────▼────────────┐
    │  candystore-ingest │              │  claude-events-recorder│
    │  POST /events/all  │              │  (in-memory test only) │
    └─────────┬──────────┘              └────────────────────────┘
              │
    ┌─────────▼──────────┐
    │  PostgreSQL 16     │
    │  candystore.events │
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │  candystore-api    │
    │  GET /events       │
    │  GET /sessions/…   │
    │  GET /summary/…    │
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐     ┌─────────────────┐
    │  Web UI (React)    │     │  Candybar desktop│
    │  filter / heatmap  │     │  (future: query) │
    └────────────────────┘     └─────────────────┘
```

---

## 4. Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Runtime | Python 3.11+ | Consistent with bloodbank services |
| HTTP server | `http.server` (stdlib) | Bloodbank service convention; no FastAPI dependency |
| DB driver | `psycopg2-binary` | Minimal, battle-tested |
| Database | PostgreSQL 16 | JSONB for flexible schema, excellent time-series indexes |
| Migrations | Plain SQL + `migrations/` dir | No ORM, no alembic — YAGNI |
| Frontend | Vite 5 + React 19 + Tailwind 3 | Re-use candybar toolchain |
| Charts | Recharts | Already in candybar dependency tree |
| Broker consumer | Dapr pubsub.jetstream | Aligns with bloodbank v3; per-service durable consumer |
| Container | `python:3.11-slim` | Same base as other bloodbank services |

---

## 5. Data Model

### 5.1 `events` table

Every CloudEvents envelope is flattened into typed columns for query speed, with the full envelope preserved in `raw`.

```sql
CREATE TABLE events (
    -- CloudEvents core
    id                  UUID PRIMARY KEY,
    specversion         TEXT NOT NULL DEFAULT '1.0',
    source              TEXT NOT NULL,
    type                TEXT NOT NULL,
    subject             TEXT,
    time                TIMESTAMPTZ NOT NULL,
    datacontenttype     TEXT,
    dataschema          TEXT,

    -- Causality
    correlationid       UUID,
    causationid         UUID,

    -- 33GOD extensions
    producer            TEXT NOT NULL,
    service             TEXT NOT NULL,
    domain              TEXT NOT NULL,
    schemaref           TEXT,
    traceparent         TEXT,
    kind                TEXT NOT NULL,
    actor               JSONB,
    data                JSONB,

    -- Metadata
    received_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ordering_key        TEXT,

    -- Full envelope for reconstruction / raw view
    raw                 JSONB NOT NULL
);

-- Query indexes
CREATE INDEX idx_events_time               ON events(time DESC);
CREATE INDEX idx_events_type               ON events(type);
CREATE INDEX idx_events_domain             ON events(domain);
CREATE INDEX idx_events_correlationid      ON events(correlationid);
CREATE INDEX idx_events_producer           ON events(producer);
CREATE INDEX idx_events_service            ON events(service);
CREATE INDEX idx_events_actor_cli          ON events((actor->>'cli'));
CREATE INDEX idx_events_type_time          ON events(type, time DESC);
CREATE INDEX idx_events_domain_time        ON events(domain, time DESC);
CREATE INDEX idx_events_correlation_time   ON events(correlationid, time);

-- For heat map / aggregation queries
CREATE INDEX idx_events_time_domain        ON events(time, domain);
CREATE INDEX idx_events_time_actorcli      ON events(time, (actor->>'cli'));

-- GIN on data for flexible payload filtering
CREATE INDEX idx_events_data_gin           ON events USING GIN (data jsonb_path_ops);
```

### 5.2 Derived concepts (query-time, not stored)

| Concept | Derivation |
|---------|-----------|
| **project** | `COALESCE(data->>'project', data->>'git_remote', regexp_replace(data->>'working_directory', '.*/', ''))` |
| **cli_type** | `actor->>'cli'` (claude / copilot / gemini / etc.) |
| **session_day** | `DATE(time)` |
| **hour_bucket** | `DATE_TRUNC('hour', time)` |

If derivation proves too slow at scale, we can add generated columns later.

---

## 6. Ingestion Design

### 6.1 Consumer strategy

Candystore uses **Dapr programmatic subscription** with a **per-service durable consumer**.

Unlike the sandbox `pubsub.yaml` (ephemeral consumers for smoke tests), Candystore mounts its own component manifest:

```yaml
# candystore/dapr-components/pubsub.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: bloodbank-pubsub
spec:
  type: pubsub.jetstream
  version: v1
  metadata:
    - name: natsURL
      value: "nats://nats:4222"
    - name: name
      value: "bloodbank-pubsub"
    - name: durableName
      value: "candystore-events"   # ← durable across restarts
    - name: queueGroupName
      value: "candystore"
    - name: streamName
      value: "BLOODBANK_EVENTS"
    - name: deliverPolicy
      value: "all"                  # replay from earliest; operator can override
    - name: ackWait
      value: "30s"
```

### 6.2 Subscription contract

`GET /dapr/subscribe` returns:

```json
[
  {
    "pubsubname": "bloodbank-pubsub",
    "topic": "bloodbank.evt.v1.>",
    "route": "/events/all"
  }
]
```

> **Open question:** Dapr jetstream pubsub wildcard topic support. If `bloodbank.evt.v1.>` is rejected, fallback to explicit topic enumeration generated from `holyfields/schemas/bloodbank/v1/**/*.json`.

### 6.3 Ack policy

```
Dapr POST /events/all  →  INSERT … ON CONFLICT DO NOTHING  →  RETURN 200
```

HTTP 200 tells Dapr to ack the NATS message. If INSERT throws, return 500 — Dapr will retry.

---

## 7. API Design

All JSON. Times are ISO-8601 UTC.

### 7.1 Events

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/events` | List events with filters |
| `GET` | `/events/:id` | Single event + pretty summary |
| `GET` | `/events/:id/raw` | Full raw envelope |

**Query params for `/events`:**

```
type           — exact match or comma list (bloodbank.v1.cli.session.ended)
domain         — exact match (cli, system, agent, …)
from           — ISO-8601 lower bound (inclusive)
to             — ISO-8601 upper bound (inclusive)
correlationid  — session / workflow ID
producer       — producer string
service        — service string
cli            — actor.cli value (claude, copilot, gemini, …)
project        — derived project name (partial match)
limit          — default 100, max 1000
offset         — pagination
```

**Response:**

```json
{
  "events": [
    {
      "id": "uuid",
      "type": "bloodbank.v1.cli.session.ended",
      "time": "2026-05-24T16:00:00Z",
      "producer": "claude-code",
      "cli": "claude",
      "project": "33god",
      "summary": {
        "title": "Session ended — 33god (claude)",
        "duration": "4h 12m",
        "turns": 34,
        "tools_used": 12,
        "final_status": "success"
      }
    }
  ],
  "total": 1523,
  "limit": 100,
  "offset": 0
}
```

### 7.2 Sessions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/sessions/:correlationid` | All events in causal chain, time-ordered |
| `GET` | `/sessions/:correlationid/summary` | Aggregate session report |

**Session summary response:**

```json
{
  "session_id": "uuid",
  "started_at": "2026-05-24T12:00:00Z",
  "ended_at": "2026-05-24T16:12:00Z",
  "duration_seconds": 15120,
  "cli": "claude",
  "project": "33god",
  "events_count": 152,
  "turns": 34,
  "tools_requested": 45,
  "tools_invoked": 42,
  "events_by_type": { "bloodbank.v1.cli.session.started": 1, ... }
}
```

### 7.3 Activity / Heat Map

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/summary/heatmap` | Hourly activity buckets |
| `GET` | `/summary/daily` | Per-day rollups |
| `GET` | `/summary/by-cli` | Aggregate by CLI type |
| `GET` | `/summary/by-project` | Aggregate by derived project |

**Heatmap response:**

```json
{
  "buckets": [
    { "hour": "2026-05-24T12:00:00Z", "count": 12, "project": "33god", "cli": "claude" },
    { "hour": "2026-05-24T13:00:00Z", "count": 8,  "project": "lasertoast", "cli": "copilot" }
  ],
  "group_by": "project"
}
```

### 7.4 Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | 204 No Content |
| `GET` | `/readyz` | 204 if DB reachable |

---

## 8. Pretty-Print Summarizers

Pluggable module `candystore/summarize.py`. Each formatter receives the envelope and returns a `Summary` dict.

```python
SUMMARIZERS: dict[str, Callable] = {
    "bloodbank.v1.cli.session.ended": _session_ended_summary,
    "bloodbank.v1.cli.session.started": _session_started_summary,
    "bloodbank.v1.conversation.turn.started": _turn_summary,
    "bloodbank.v1.tool.tool_call.requested": _tool_summary,
    "system.heartbeat.tick": _heartbeat_summary,
    # … fallback to generic envelope preview
}
```

Example `_session_ended_summary`:

```python
def _session_ended_summary(env: dict) -> dict:
    data = env.get("data", {})
    return {
        "title": f"Session ended — {data.get('git_branch', 'unknown')}",
        "duration": _fmt_duration(data.get("duration_seconds")),
        "turns": data.get("total_turns"),
        "tools_used": len(data.get("tools_used", [])),
        "files_modified": data.get("files_modified"),
        "final_status": data.get("final_status"),
        "end_reason": data.get("end_reason"),
    }
```

---

## 9. Web UI

React SPA built with Vite, served as static files from `/` by the Python HTTP server.

### 9.1 Routes

| Route | View |
|-------|------|
| `/` | Event stream (default filter: today) |
| `/events/:id` | Event detail with pretty summary + raw JSON toggle |
| `/sessions/:id` | Session timeline (vertical list of events in chain) |
| `/heatmap` | Activity heat map with project / CLI toggles |
| `/explore` | Free-form filter builder |

### 9.2 Key components

- **FilterBar** — time range (preset: today / yesterday / 7d / 30d), project dropdown, CLI type chips, event type multi-select
- **EventList** — infinite scroll table, summary cards for session.end
- **EventDetail** — pretty summary top, collapsible raw envelope bottom
- **HeatMap** — Recharts calendar heat map or hourly bar chart
- **SessionTimeline** — causation-linked events, duration gaps highlighted

### 9.3 Color coding by CLI type

| CLI | Color |
|-----|-------|
| claude | amber-500 |
| copilot | blue-500 |
| gemini | teal-500 |
| opencode | violet-500 |

---

## 10. Deployment

### 10.1 Compose profile

Added to `bloodbank/compose/docker-compose.yml` under profile `candystore`:

```yaml
services:
  candystore:
    build:
      context: ../../candystore
    container_name: bloodbank-candystore
    profiles: [candystore]
    environment:
      APP_PORT: "3001"
      DATABASE_URL: "postgresql://candystore:candystore@postgres:5432/candystore"
      SUBSCRIBE_PUBSUB: "bloodbank-pubsub"
    ports:
      - "${BLOODBANK_CANDystore_PORT:-3603}:3001"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - bloodbank-network

  daprd-candystore:
    image: daprio/daprd:1.13.0
    container_name: bloodbank-daprd-candystore
    profiles: [candystore]
    command:
      - "./daprd"
      - "--app-id=bloodbank-candystore"
      - "--dapr-http-port=3500"
      - "--dapr-grpc-port=50001"
      - "--app-port=3001"
      - "--app-channel-address=candystore"
      - "--app-protocol=http"
      - "--resources-path=/components"
      - "--placement-host-address=dapr-placement:50005"
    volumes:
      - ./components:/components:ro
      - ../../candystore/dapr-components:/components/candystore:ro
    depends_on:
      nats-init:
        condition: service_completed_successfully
      candystore:
        condition: service_healthy
    networks:
      - bloodbank-network

  postgres:
    image: postgres:16-alpine
    container_name: bloodbank-postgres
    profiles: [candystore]
    environment:
      POSTGRES_USER: candystore
      POSTGRES_PASSWORD: candystore
      POSTGRES_DB: candystore
    volumes:
      - bloodbank-postgres-data:/var/lib/postgresql/data
      - ../../candystore/migrations:/docker-entrypoint-initdb.d:ro
    networks:
      - bloodbank-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U candystore"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  bloodbank-postgres-data:
```

### 10.2 Boot sequence

```bash
cd ~/code/33GOD/bloodbank
mise run up                    # NATS + nats-init
mise run up:candystore         # new task: postgres + candystore + daprd
```

---

## 11. Testing Strategy

| Layer | Approach |
|-------|----------|
| DB schema | `mise run test:schema` — validate migrations run cleanly on fresh Postgres |
| Ingestion | `mise run test:ingest` — publish 100 synthetic events, assert all in DB, assert idempotency (same id twice = one row) |
| API | `mise run test:api` — hit every endpoint, assert contracts |
| Summarizers | Unit tests for each formatter |
| End-to-end | `mise run smoketest:candystore` — full compose profile up, inject events, query API, assert heatmap shape |

---

## 12. Open Questions

1. **Dapr wildcard topic** — Does `pubsub.jetstream` support `bloodbank.evt.v1.>` in programmatic subscriptions? If not, we enumerate topics from `holyfields/schemas/bloodbank/v1/**/*.json` at build time.
2. **Project derivation** — Is `git_remote` always present? Should we normalize repo URLs to project names? Should project be an explicit field in future schema versions?
3. **Retention** — Personal use implies "keep everything", but should we support TTL / archival? Defer.
4. **Candybar integration** — Should Candybar query Candystore API directly, or should Candystore push to a WebSocket? Defer to Candybar roadmap.

---

## 13. Milestones

| Milestone | Deliverable | Est |
|-----------|-------------|-----|
| M1 — Bootstrap | Project scaffold, DB connection, health endpoint | 1h |
| M2 — Ingestion | Dapr subscribe, INSERT path, idempotency | 2h |
| M3 — Query API | `/events`, `/sessions`, filters, pagination | 2h |
| M4 — Summarizers | Session end + 5 core event types | 1h |
| M5 — Heat map API | `/summary/heatmap`, `/summary/by-cli` | 1h |
| M6 — Web UI shell | Vite scaffold, router, filter bar | 2h |
| M7 — Web UI views | Event list, detail, session timeline, heatmap | 3h |
| M8 — Compose + CI | Docker build, profile, smoke test | 1h |
