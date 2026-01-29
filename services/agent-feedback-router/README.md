# Agent Feedback Router

FastStream consumer that routes `agent.feedback.requested` events to AgentForge and publishes `agent.feedback.response` events with correlation tracking.

**Migrated to FastStream** per ADR-0002 Phase 2.

## Architecture

**Pattern:** Standalone microservice (not embedded in Bloodbank)
**Consumer Type:** FastStream RabbitMQ subscriber
**Envelope Handling:** Explicit EventEnvelope unwrapping

**Event Flow:**
```
agent.feedback.requested → AgentFeedbackRouter → AgentForge API
                                                        ↓
                                                  agent.feedback.response
```

## Configuration

Environment variables:

- `RABBIT_URL` - RabbitMQ connection (default: `amqp://guest:guest@localhost:5672/`)
- `EXCHANGE_NAME` - Bloodbank exchange (default: `bloodbank.events.v1`)
- `AGENTFORGE_API_URL` - AgentForge base URL (default: `http://localhost:8000`)
- `AGENTFORGE_API_TOKEN` - Optional bearer token for AgentForge API
- `AGENTFORGE_API_TIMEOUT` - Request timeout in seconds (default: `30.0`)

## Installation

```bash
cd /home/delorenj/code/33GOD/services/agent-feedback-router
uv sync
```

## Running

### Development (with hot reload)

```bash
uv run faststream run src.consumer:app --reload
```

### Production

```bash
uv run faststream run src.consumer:app --workers 4
```

### Docker

```bash
docker build -t agent-feedback-router .
docker run -e RABBIT_URL=amqp://rabbitmq:5672/ \
           -e AGENTFORGE_API_URL=http://agentforge:8000 \
           agent-feedback-router
```

## Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html
```

## Correlation Tracking

All published `agent.feedback.response` events include:
- `correlation_ids`: Links back to the original request event
- `event_id`: Deterministic UUID for idempotency
- `source`: Identifies this service as the origin

Query correlation chains via Bloodbank:
```bash
curl "http://localhost:8682/debug/correlation/{event_id}/chain?direction=ancestors"
```

## References

- [ADR-0002: Agent Feedback Architecture](/home/delorenj/code/33GOD/bloodbank/trunk-main/docs/architecture/ADR-0002-agent-feedback-architecture.md)
- [Service Registry](/home/delorenj/code/33GOD/services/registry.yaml)
- [FastStream Onboarding](/home/delorenj/code/33GOD/bloodbank/trunk-main/docs/ONBOARDING_FASTSTREAM.md)
