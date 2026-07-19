# Candystore HTTP API Contracts

## Ingestion

`GET /dapr/subscribe` declares the wildcard Bloodbank event subscription by default. Dapr delivers to `POST /events/all`; explicit legacy routes exist when explicit subscription mode is selected.

| Outcome | HTTP | Dapr status | Meaning |
|---|---:|---|---|
| New event | 200 | `SUCCESS` | Inserted |
| Existing UUID | 200 | `SUCCESS` | Incoming body discarded; canonical stored `events.raw` is projected in the same transaction |
| Invalid JSON/envelope/time or permanent DB rejection | 200 | `DROP` | Dead-letter attempted |
| Other/transient exception | 500 | `RETRY` | Delivery retried |

Candystore requires truthy `id`, `source`, `type`, `time`, `producer`, `service`, `domain`, and `kind`, plus UUID/time parsing. This is not full Bloodbank validation.

If insertion or projection raises a transient exception, neither the audit row
nor projection receipt commits and Dapr retries. Duplicate delivery can safely
complete a projection that was absent before migration because the retry reads
the already-persisted canonical row under a PostgreSQL share lock.

## Health

- `GET /healthz`: process liveness, unconditional 204.
- `GET /readyz`: database `SELECT 1`, 204 or 503.

## Event Reads

- `GET /events`
- `GET /events/:id`
- `GET /events/:id/raw`
- `GET /events/:id/summary`

List filters: comma-separated `type` and `scope`, `domain`, inclusive `from`/`to`, `correlationid`, `producer`, `service`, `cli`, substring `project`, `limit` (1–1000), and nonnegative `offset`.

## Session and Aggregate Reads

- `GET /sessions/:correlationid`
- `GET /sessions/:correlationid/summary`
- `GET /summary/heatmap`
- `GET /summary/daily`
- `GET /summary/by-cli`
- `GET /summary/by-project`

## Limitations

The API is unauthenticated. Pagination lacks stable secondary ordering. Invalid GET parameters and database errors are not consistently structured. Non-UUID correlations may be stored as null and become unqueryable. No dead-letter list/export/replay, event replay, or broker republish API exists.

Holocene should call the standalone service through host loopback `http://127.0.0.1:8683` in the current split topology.
