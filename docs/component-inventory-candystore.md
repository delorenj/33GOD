# Candystore Component Inventory

| Component | Location | Responsibility |
|---|---|---|
| HTTP server/router | `candystore/main.py` | Health, Dapr callbacks, query routing, static UI |
| Persistence | `candystore/db.py` | Connections, migrations, validation, event/dead-letter writes |
| Ingestion | `candystore/ingest.py` | Subscription metadata, sanitation, delivery classification |
| Query layer | `candystore/query.py` | Event/session/filter/aggregate SQL |
| Summaries | `candystore/summarize.py` | Human-readable event/session projections |
| Process stats | `candystore/stats.py` | In-memory ingestion counters |
| Schema | `migrations/` | Events and dead-letter PostgreSQL objects |
| Dapr subscription | `dapr-components/pubsub.yaml` | Bloodbank wildcard durable/queue configuration |
| React UI | `web/` | Source for event history/audit interface |
| Static UI | `static/` | Prebuilt assets copied by the backend image |
| Standalone topology | `compose.yml` | PostgreSQL, app, and Dapr sidecar |

The server deliberately combines migration, ingest, query, and static serving in one process. A future split should preserve ingest acknowledgement semantics and one canonical durable consumer.
