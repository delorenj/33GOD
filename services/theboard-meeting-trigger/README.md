# TheBoard Meeting Trigger

FastStream consumer that automatically creates TheBoard brainstorming meetings in response to ecosystem trigger events.

**Migrated to FastStream** per ADR-0002 Phase 3.

## Architecture

**Pattern:** Standalone microservice (not embedded in Bloodbank)
**Consumer Type:** FastStream RabbitMQ subscriber with multiple event handlers
**Envelope Handling:** Explicit EventEnvelope unwrapping

**Event Flow:**
```
trigger events → MeetingTrigger → TheBoard API → acknowledgments
```

## Events Consumed

- `theboard.meeting.trigger` - Direct meeting trigger with full meeting spec
- `feature.brainstorm.requested` - Feature ideation trigger
- `architecture.review.needed` - Architecture discussion trigger
- `incident.postmortem.scheduled` - Incident analysis trigger (planned)
- `decision.analysis.required` - Decision-making support trigger (planned)

## Events Produced

- `theboard.meeting.trigger.processing` - Acknowledgment of trigger received
- `theboard.meeting.trigger.completed` - Meeting created successfully
- `theboard.meeting.trigger.failed` - Meeting creation failed

## Configuration

Environment variables:

- `RABBIT_URL` - RabbitMQ connection (default: `amqp://guest:guest@localhost:5672/`)
- `EXCHANGE_NAME` - Bloodbank exchange (default: `bloodbank.events.v1`)
- `THEBOARD_API_URL` - TheBoard API URL (default: `http://localhost:8000`)
- `THEBOARD_DATABASE_URL` - TheBoard database connection

## Installation

```bash
cd /home/delorenj/code/33GOD/services/theboard-meeting-trigger
uv sync
```

## Running

### Development (with hot reload)

```bash
uv run faststream run src.theboard_meeting_trigger.consumer:app --reload
```

### Production

```bash
uv run faststream run src.theboard_meeting_trigger.consumer:app --workers 4
```

### Docker

```bash
docker build -t theboard-meeting-trigger .
docker run -d \
  --name theboard-meeting-trigger \
  --network 33god-network \
  -e RABBIT_URL=amqp://rabbitmq:5672/ \
  -e THEBOARD_DATABASE_URL=postgresql+psycopg://theboard:pass@postgres:5432/theboard \
  theboard-meeting-trigger
```

## Queue Architecture

Each event type has its own dedicated queue following the naming convention:

- `services.theboard.meeting_trigger` → `theboard.meeting.trigger`
- `services.theboard.feature_brainstorm` → `feature.brainstorm.requested`
- `services.theboard.architecture_review` → `architecture.review.needed`
- `services.theboard.incident_postmortem` → `incident.postmortem.scheduled`
- `services.theboard.decision_analysis` → `decision.analysis.required`

This allows independent scaling and monitoring of each trigger type.

## Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html
```

### Publishing Test Events

```python
import asyncio
from event_producers.rabbit import Publisher
from event_producers.events.base import create_envelope, Source, TriggerType

async def test():
    pub = Publisher()
    await pub.start()

    envelope = create_envelope(
        event_type="theboard.meeting.trigger",
        payload={
            "topic": "Test brainstorm on API design patterns",
            "strategy": "sequential",
            "max_rounds": 3,
            "agent_count": 5
        },
        source=Source(host="test", type=TriggerType.MANUAL, app="test")
    )

    await pub.publish(
        routing_key="theboard.meeting.trigger",
        body=envelope.model_dump(),
        event_id=envelope.event_id
    )

    await pub.close()

asyncio.run(test())
```

## References

- [ADR-0002: Agent Feedback Architecture](/home/delorenj/code/33GOD/bloodbank/trunk-main/docs/architecture/ADR-0002-agent-feedback-architecture.md)
- [Service Registry](/home/delorenj/code/33GOD/services/registry.yaml)
- [FastStream Onboarding](/home/delorenj/code/33GOD/bloodbank/trunk-main/docs/ONBOARDING_FASTSTREAM.md)
- [TheBoard Documentation](/home/delorenj/code/33GOD/services/theboard-producer/)
