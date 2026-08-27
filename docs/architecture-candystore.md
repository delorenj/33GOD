# Candystore Architecture

## Executive Summary

Candystore is Bloodbank’s durable history/read model: a Python HTTP server, PostgreSQL event store, Dapr JetStream subscriber, and React audit UI. It is compact and understandable, but it is not yet an enterprise audit-of-record because poison preservation, replay, backup, auth, and migration controls are incomplete.

## Technology Stack

| Category | Technology | Version/evidence |
|---|---|---|
| Backend | Python stdlib `ThreadingHTTPServer` | Python 3.11+ |
| Database | PostgreSQL / psycopg2 | 16-alpine / 2.9.12 |
| Transport | Dapr JetStream component | Dapr 1.13.0 |
| Frontend | React, Vite, Tailwind, Recharts | 19.2.6, 6.4.2, 3.4.19, 2.15.4 |
| Quality | pytest, Ruff | 9.0.3, 0.15.14 |

## Architecture Pattern

Vertical full-stack read model. One Python process applies migrations, receives Dapr callbacks, serves query/summary endpoints, and serves the prebuilt SPA. PostgreSQL and Dapr run separately.

## Ingestion Flow

The Dapr sidecar subscribes to `bloodbank.evt.>` using durable
`candystore-events` and queue group `candystore`. The broad durable-history
filter covers the stream's v1 wildcard and explicitly admitted v2 subjects; it
does not broaden what Bloodbank stores. Accepted events are deduplicated by UUID
and projected into indexed columns plus JSONB. Permanent failures return 200
`DROP`; transient failures return 500 `RETRY`.

Candystore validates eight truthy fields plus UUID/time parsing, weaker than Bloodbank’s canonical contract. It does not enforce canonical type/subject equality, actor/order/schema metadata, or full domain/action rules.

## Data Architecture

`events` stores the envelope projection, JSONB raw representation, receive time, and sanitation marker. `dead_letter` stores rejected or sanitized request bytes. A dead-letter insertion catches all failures and callers still acknowledge `DROP`, so malformed messages can be lost during database failure. See [Candystore Data Models](./data-models-candystore.md).

## API Design

The unauthenticated API exposes event filters, event/raw/summary detail, sessions, and aggregate summaries. It has no operational replay or dead-letter browser/export endpoint. Invalid GET input is not consistently converted into structured JSON. See [Candystore API Contracts](./api-contracts-candystore.md).

## Deployment Architecture

The canonical topology is standalone `candystore/compose.yml`: PostgreSQL, app, and Dapr sidecar on internal/external networks. Loopback host ports reduce direct exposure. Bloodbank’s legacy Candystore profile uses the same durable/queue with a different database and must never run concurrently.

The image copies prebuilt `static/` rather than building the frontend, so UI source can be newer than deployed assets. Docker installs Python from minimum constraints instead of the committed lock.

## Testing Strategy

The repository contains 21 Python tests and a migration shell test. DB-backed tests can skip, and the suite lacks full contract, dead-letter failure, replay, concurrency, migration-ledger, backup, frontend, and live Dapr/NATS coverage.

## Principal Risks

Best-effort poison durability, weaker-than-canonical validation, no replay/backup, dual-deployment message splitting, liveness used instead of readiness, no app auth, unbounded threaded request handling, mutable build inputs, and miswired Holocene dependency.

## Development Workflow

Use [Candystore Development Guide](./development-guide-candystore.md). Any ingest outcome or schema change requires Bloodbank contract review and Holocene read-client verification.
