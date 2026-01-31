# Bloodbank - Technical Implementation Guide

## Overview

Bloodbank is the central event bus for the 33GOD ecosystem, providing asynchronous message routing with RabbitMQ as the backbone. It enables decoupled communication between all platform components through topic-based event publishing and subscription.

## Implementation Details

**Language**: Python 3.12+
**Core Framework**: FastAPI (async HTTP server)
**Message Broker**: RabbitMQ 3.12
**Event Format**: Pydantic models with JSON serialization
**Package Manager**: uv (modern Python dependency manager)

### Key Technologies

- **FastAPI**: Async HTTP endpoints for event publishing (port 8000)
- **aio-pika**: Asynchronous RabbitMQ client library
- **Pydantic**: Type-safe event schema definitions
- **RabbitMQ Topic Exchange**: Flexible routing with wildcard subscriptions

## Architecture & Design Patterns

### Event-Driven Architecture

Bloodbank implements a **topic exchange pattern** where:
1. Publishers send events to a single durable exchange (`events`)
2. Routing keys follow hierarchical naming: `<service>.<entity>.<action>`
3. Subscribers bind queues with wildcard patterns (`#`, `*`)
4. Events are persisted durably to survive broker restarts

### Event Envelope Pattern

All events use a standardized `EventEnvelope` wrapper:

```python
from events import EventEnvelope, envelope_for, CalendarEvent

# Create typed event payload
event_data = CalendarEvent(
    summary="Team Standup",
    start_time=datetime(2026, 1, 29, 10, 0),
    end_time=datetime(2026, 1, 29, 10, 30),
    location="Conference Room A"
)

# Wrap in envelope with metadata
envelope = envelope_for(
    event_type="calendar.event.created",
    source="google_calendar_integration",
    data=event_data
)
```

**EventEnvelope Schema**:
```python
class EventEnvelope(BaseModel):
    id: str                      # UUID for idempotency
    event_type: str              # Routing key
    source: str                  # Publishing service
    timestamp: datetime          # ISO8601 creation time
    data: Dict[str, Any]         # Typed payload
    correlation_id: Optional[str]
    session_id: Optional[str]
```

### Publisher Service

`http.py` exposes REST endpoints for event publishing:

```python
@app.post("/events/calendar")
async def publish_calendar_event(
    ev: CalendarEvent,
    request: Request
):
    env = envelope_for(
        "calendar.event.created",
        source=f"http/{request.client.host}",
        data=ev
    )
    await publisher.publish(
        routing_key="calendar.event.created",
        body=env.model_dump(),
        message_id=env.id
    )
    return JSONResponse(env.model_dump())
```

**Key Features**:
- Auto-generates event IDs for idempotency
- Captures source IP for audit trails
- Asynchronous publishing (non-blocking)
- JSON response with full envelope

### Subscriber Pattern

Example subscriber with selective routing:

```python
import asyncio
from rabbit import Subscriber

async def main():
    # Bind to all LLM-related events
    subscriber = Subscriber(binding_key="llm.*")

    async def handle_event(message):
        envelope = EventEnvelope(**message)
        print(f"Received: {envelope.event_type}")
        print(f"Data: {envelope.data}")

    await subscriber.start(callback=handle_event)

asyncio.run(main())
```

**Routing Key Patterns**:
- `#` - All events (Candystore uses this)
- `llm.*` - All LLM service events
- `calendar.event.created` - Specific event type
- `theboard.meeting.*` - All meeting events

## Configuration

### Environment Variables

```bash
# RabbitMQ connection
RABBIT_HOST=localhost
RABBIT_PORT=5672
RABBIT_USER=guest
RABBIT_PASSWORD=guest

# Exchange configuration
EXCHANGE_NAME=events
EXCHANGE_TYPE=topic
EXCHANGE_DURABLE=true

# Publisher HTTP server
HTTP_HOST=0.0.0.0
HTTP_PORT=8000
```

### Docker Deployment

```yaml
# docker-compose.yml
services:
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"  # Management UI
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  bloodbank:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - rabbitmq
    environment:
      RABBIT_HOST: rabbitmq
```

## Integration Points

### Publishing Events

**Via HTTP**:
```bash
curl -X POST http://localhost:8000/events/calendar \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Sprint Planning",
    "start_time": "2026-01-30T14:00:00Z",
    "end_time": "2026-01-30T15:00:00Z"
  }'
```

**Direct from Python**:
```python
from rabbit import Publisher
from events import envelope_for, ArtifactEvent

async def publish_artifact(path: str):
    publisher = Publisher()
    await publisher.start()

    event = ArtifactEvent(path=path, type="code")
    envelope = envelope_for(
        "artifact.created",
        source="agent-forge",
        data=event
    )

    await publisher.publish(
        routing_key="artifact.created",
        body=envelope.model_dump(),
        message_id=envelope.id
    )

    await publisher.close()
```

### Consuming Events

**Simple Consumer**:
```python
from rabbit import Subscriber
import asyncio

async def process_event(message):
    """Handle incoming event"""
    print(f"Event: {message['event_type']}")
    # Process message here

subscriber = Subscriber(binding_key="theboard.meeting.*")
asyncio.run(subscriber.start(callback=process_event))
```

**With Error Handling**:
```python
async def safe_process(message):
    try:
        envelope = EventEnvelope(**message)
        # Business logic here
        await process_meeting_event(envelope)
    except Exception as e:
        logger.error(f"Failed to process event: {e}")
        # Dead letter queue or retry logic

subscriber = Subscriber(
    binding_key="#",
    queue_name="my-service-queue",
    auto_ack=False  # Manual ACK for reliability
)
```

## Performance Characteristics

### Throughput

- **Publisher**: 5000+ events/sec (single instance)
- **Latency**: <10ms event publish time
- **RabbitMQ**: 20k+ msgs/sec (durable exchange)

### Scalability Patterns

**Horizontal Scaling**:
- Run multiple publisher instances behind load balancer
- Each subscriber gets dedicated queue (work distribution)
- RabbitMQ clustering for high availability

**Message Persistence**:
- Durable exchange survives broker restarts
- Messages marked persistent by default
- Subscriber queues survive client disconnections

## Edge Cases & Troubleshooting

### Duplicate Events

**Problem**: Network retries can cause duplicate publishes
**Solution**: Use envelope `id` field for idempotency:

```python
async def handle_with_dedup(message):
    event_id = message["id"]

    # Check if already processed
    if await redis.exists(f"processed:{event_id}"):
        return  # Skip duplicate

    # Process event
    await process_event(message)

    # Mark as processed (24hr TTL)
    await redis.setex(
        f"processed:{event_id}",
        86400,
        "1"
    )
```

### Dead Letter Handling

**Problem**: Consumer fails to process event
**Solution**: Configure dead letter exchange:

```python
# In subscriber setup
subscriber = Subscriber(
    binding_key="llm.*",
    queue_args={
        "x-dead-letter-exchange": "dlx",
        "x-message-ttl": 300000  # 5 min retry
    }
)
```

### Connection Loss Recovery

**Problem**: RabbitMQ broker restarts
**Solution**: Auto-reconnect with exponential backoff:

```python
async def resilient_subscriber():
    while True:
        try:
            subscriber = Subscriber(binding_key="#")
            await subscriber.start(callback=handle_event)
        except ConnectionError:
            backoff = min(60, 2 ** retry_count)
            await asyncio.sleep(backoff)
            retry_count += 1
```

## Code Examples

### Custom Event Type

```python
# In events.py
class MeetingCreatedEvent(BaseModel):
    meeting_id: str
    topic: str
    participant_count: int
    scheduled_time: datetime
    metadata: Optional[Dict[str, Any]] = None

# Publisher endpoint
@app.post("/events/meeting/created")
async def publish_meeting_created(event: MeetingCreatedEvent):
    envelope = envelope_for(
        "theboard.meeting.created",
        source="theboard",
        data=event
    )
    await publisher.publish(
        "theboard.meeting.created",
        envelope.model_dump(),
        message_id=envelope.id
    )
    return envelope
```

### Multi-Event Subscription

```python
async def handle_multiple_topics():
    """Subscribe to multiple event types"""
    subscriber = Subscriber(binding_key="theboard.meeting.*")

    async def route_event(message):
        event_type = message["event_type"]

        handlers = {
            "theboard.meeting.created": handle_created,
            "theboard.meeting.started": handle_started,
            "theboard.meeting.completed": handle_completed,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(message)
        else:
            logger.warning(f"No handler for: {event_type}")

    await subscriber.start(callback=route_event)
```

## Migration & Versioning

### Event Schema Evolution

**Adding Optional Fields** (Non-breaking):
```python
class CalendarEvent(BaseModel):
    summary: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: Optional[List[str]] = []  # New field
```

**Breaking Changes** (Versioning):
```python
# Use versioned routing keys
envelope_for(
    "calendar.event.created.v2",  # Version in routing key
    source="calendar-service",
    data=CalendarEventV2(...)
)

# Consumers can bind to specific versions
subscriber = Subscriber(binding_key="calendar.event.created.v2")
```

## Deployment Best Practices

1. **Health Checks**: Expose `/health` endpoint with RabbitMQ connection status
2. **Monitoring**: Track publish latency, queue depth, consumer lag
3. **Rate Limiting**: Use token bucket for burst protection
4. **Circuit Breakers**: Fail fast when RabbitMQ unavailable
5. **Logging**: Structured JSON logs with correlation IDs

## Security Considerations

- **Authentication**: Use RabbitMQ user accounts (not guest in production)
- **TLS**: Enable SSL/TLS for encrypted transport
- **Authorization**: Vhosts for multi-tenant isolation
- **Validation**: Pydantic enforces schema compliance
- **Sanitization**: Escape user input in event payloads

## Related Components

- **Holyfields**: Event schema registry and validation
- **Candystore**: Universal event storage and audit trail
- **Services**: Microservices consuming specific event streams
- **TheBoard**: Publishes meeting orchestration events
- **TalkyTonny**: Publishes transcription events

---

**Quick Reference**:
- GitHub: `33GOD/bloodbank`
- Port: 8000 (HTTP), 5672 (RabbitMQ)
- Docs: `GREENFIELD_DEPLOYMENT.md`, `MIGRATION_v1_to_v2.md`
