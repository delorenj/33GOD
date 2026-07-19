# Candystore Architecture

## Executive Summary

Candystore is Bloodbank’s durable history/read model: a Python HTTP server, PostgreSQL event store, Dapr JetStream subscriber, and React audit UI. It is compact and understandable, but it is not yet an enterprise audit-of-record because poison preservation, operator-triggered general replay, backup, auth, and migration controls are incomplete.

Candystore never owns operational project-lifecycle truth. It durably records
canonical lifecycle events and maintains the smallest replay-safe,
version-ordered projection used by Holocene. Lifecycle remains the only
lifecycle-state writer.

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

The Dapr sidecar subscribes to `bloodbank.evt.v1.>` using durable
`candystore-events` and queue group `candystore`. Event insertion and Lifecycle
projection share one PostgreSQL transaction. On UUID conflict, Candystore
loads `events.raw` for that ID under `FOR SHARE` and projects that immutable
stored envelope, never the conflicting delivery. A projection failure aborts
the event insert and receipt together; the callback returns 500 so durable
redelivery retries the same operation. Permanent malformed/data failures
return 200 `DROP`.

Candystore validates eight truthy fields plus UUID/time parsing, weaker than Bloodbank’s canonical contract. It does not enforce canonical type/subject equality, actor/order/schema metadata, or full domain/action rules.

## Data Architecture

`events` stores the envelope projection, JSONB raw representation, receive time, and sanitation marker. `dead_letter` stores rejected or sanitized request bytes. A dead-letter insertion catches all failures and callers still acknowledge `DROP`, so malformed messages can be lost during database failure. See [Candystore Data Models](./data-models-candystore.md).

## API Design

The unauthenticated API exposes event filters, event/raw/summary detail, sessions, and aggregate summaries. It has no operational replay or dead-letter browser/export endpoint. Invalid GET input is not consistently converted into structured JSON. See [Candystore API Contracts](./api-contracts-candystore.md).

## Deployment Architecture

The canonical topology is standalone `candystore/compose.yml`: PostgreSQL, app, and Dapr sidecar on internal/external networks. Loopback host ports reduce direct exposure. Bloodbank’s legacy Candystore profile uses the same durable/queue with a different database and must never run concurrently.

The image copies prebuilt `static/` rather than building the frontend, so UI source can be newer than deployed assets. Docker installs Python from minimum constraints instead of the committed lock.

## Testing Strategy

The focused Lifecycle slice adds DB-backed replay, idempotency,
ordering/version, provenance/freshness, unknown/degraded, stable-verdict, and
read-only ownership tests. Broader dead-letter, backup, auth, and frontend risks
remain outside this slice.

## Principal Risks

Best-effort poison durability, weaker-than-canonical validation, no
operator-triggered general replay or backup, dual-deployment message splitting,
liveness used instead of readiness, no app auth, unbounded threaded request
handling, mutable build inputs, and miswired non-Lifecycle Holocene dependency.

## Development Workflow

Use [Candystore Development Guide](./development-guide-candystore.md). Any ingest outcome or schema change requires Bloodbank contract review, Lifecycle replay/projection verification, and Holocene read-client verification.
