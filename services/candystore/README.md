# Event Store Manager - The Historian

> Infrastructure service that persists all Bloodbank events to PostgreSQL for queryable audit trail and observability.

## Role

**The Historian** of the 33GOD ecosystem - captures every coordination event flowing through Bloodbank and provides queryable history.

## Responsibilities

1. **Event Capture** - Subscribe to ALL Bloodbank events (`#` wildcard)
2. **Event Persistence** - Write events to PostgreSQL with transactional guarantees
3. **Workflow State Projections** - Maintain aggregated workflow state
4. **Query APIs** - Provide REST and WebSocket APIs for event history queries

## Architecture

```
Bloodbank (#) → Event Store Manager → PostgreSQL
                        ↓
                    REST API
                    WebSocket Stream
```

## API Endpoints

- `GET /api/v1/events?workflow_id={id}` - Get all events for workflow
- `GET /api/v1/events?correlation_id={id}` - Get causation chain
- `GET /api/v1/events/{event_id}/descendants` - Get downstream events
- `GET /api/v1/workflows/{workflow_id}/timeline` - Workflow timeline
- `GET /api/v1/agents/{session_id}/events` - Agent-specific events
- `WS /api/v1/events/stream` - Real-time event stream

## Configuration

See `.env.example` for required environment variables.

Key settings:
- `DATABASE_URL` - PostgreSQL connection string
- `RABBITMQ_URL` - Bloodbank connection
- `EVENT_STORE_MANAGER_QUEUE` - RabbitMQ queue name

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Start service
uv run python -m src.main

# Health check
curl http://localhost:8080/health
```

## Database Schema

See `migrations/` for PostgreSQL schema:
- `events` - Event storage with GIN indexes for correlation IDs
- `workflow_state` - Aggregated workflow state projections
- `agent_sessions` - Agent session tracking

## Sprint Plan

Implementation broken down into stories:
- **STORY-001** - PostgreSQL event store schema
- **STORY-004** - Bloodbank subscription
- **STORY-005** - PostgreSQL writer with transactional outbox
- **STORY-006** - Workflow state projections

See `docs/sprint-plan-hybrid-architecture-phase1-2026-01-11.md` for details.

## Status

**Planned** - Registry entry created, scaffolding complete, ready for implementation.
