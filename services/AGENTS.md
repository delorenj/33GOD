# Services — Agent Guide

Collection of standalone Bloodbank-driven microservices. Each service subscribes to events via the BaseSubscriber pattern.

## Registry

Services are registered in `services/registry.yaml`. This is the source of truth for service discovery.

## Standard Interface

- **Base Class:** `BaseSubscriber` (from `services/base/`)
- **Connection:** `BLOODBANK_URL` environment variable
- **Queue Naming:** `services.<domain>.<service_name>`
- **Behavior:** Durable subscriptions, dead-letter handling, idempotent processing

## Service Catalog

| Service | Description | Tech |
|---------|-------------|------|
| agent-feedback-router | Routes agent quality feedback events | Python, uv |
| agent-voice-soprano | Voice synthesis for agent communication | Python, uv |
| candystore | Event persistence and audit trail | Python, FastAPI, SQLAlchemy |
| fireflies-transcript-processor | Processes Fireflies.ai meeting transcripts | Python, Docker |
| mutation-ledger | Tracks state mutations across the pipeline | Python |
| node-red-flow-orchestrator | Visual workflow orchestration | Node-RED, mise |
| postgres-notify-bridge | PostgreSQL NOTIFY/LISTEN → Bloodbank bridge | Python, Docker |
| theboard-meeting-trigger | Triggers TheBoard meetings from events | Python, Docker |
| tonny | TonnyBox companion service | Python, Docker |

## Templates

- `templates/generic-consumer` — Boilerplate for new event consumer services
- `templates/fireflies-transcript-processor` — Reference implementation

## Creating a New Service

1. Copy `templates/generic-consumer`
2. Implement event handler extending `BaseSubscriber`
3. Register in `registry.yaml`
4. Add Dockerfile (multi-stage, non-root)
5. Add to `compose.yml` in project root

## Anti-Patterns

- Never bypass BaseSubscriber for direct RabbitMQ access
- Never skip registry.yaml registration
- Never use synchronous I/O in event handlers
