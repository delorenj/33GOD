# Infrastructure Domain

> The central nervous system of the 33GOD platform. All state changes flow through here as typed events with schema validation.

## Overview

The Infrastructure Domain provides the foundational messaging and contract layer that enables all other 33GOD components to communicate asynchronously. It consists of two core components:

| Component | Role | Tech Stack |
|-----------|------|------------|
| **Bloodbank** | Central Event Bus | RabbitMQ, Python 3.11+, FastStream, aio-pika |
| **Holyfields** | Schema Registry & Contract System | JSON Schema, TypeScript, Pydantic, Zod |

Together, these components enforce the "Everything is an Event" philosophy:
- **Bloodbank** routes and delivers typed events between services
- **Holyfields** defines the canonical schemas that validate all event structures

---

## How These Components Work Together

```
                                 Holyfields
                            (Schema Registry)
                                    |
                    generates       |       validates
                    types           |       events
                    |               |           |
    +---------------+---------------+-----------+---------------+
    |               |               |           |               |
    v               v               v           v               v
[Python         [TypeScript    [Bloodbank   [Candystore    [Candybar
 Services]       Services]      Event Bus]   Persistence]   Dashboard]
    |               |               |           |               |
    +-------+-------+---------------+-----------+---------------+
            |                       |
            |     publish/subscribe |
            +-----------------------+
                    via RabbitMQ
```

### Data Flow

1. **Schema Definition**: Holyfields defines canonical event schemas in JSON Schema format
2. **Code Generation**: Holyfields generates type-safe models (Pydantic for Python, Zod for TypeScript)
3. **Event Publishing**: Services use Bloodbank's Publisher to emit events wrapped in `EventEnvelope`
4. **Schema Validation**: Bloodbank validates events against Holyfields schemas before routing
5. **Event Routing**: RabbitMQ topic exchange routes events to subscribed queues
6. **Event Consumption**: Services consume events from their dedicated queues
7. **Event Persistence**: Candystore persists all events for audit trails and replay

---

## Bloodbank - Central Event Bus

### Purpose

Bloodbank is the **nervous system** of 33GOD, providing RabbitMQ-based messaging infrastructure with:
- Topic-based event routing
- Schema validation at publish time
- Correlation ID tracking for event chains
- Dead Letter Queue (DLQ) handling for failed messages
- Durable subscriptions for fault tolerance

### Key Responsibilities

1. **Event Routing** - Route events to subscribers via topic exchange patterns
2. **Schema Enforcement** - Validate all events against Holyfields schemas
3. **Correlation Tracking** - Propagate correlation IDs through event chains
4. **Reliability** - Ensure zero message loss with DLQs and durable queues
5. **Observability** - Provide health endpoints and Prometheus metrics

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Message Broker | RabbitMQ | Durable message queuing with topic exchange |
| Async Framework | FastStream | Modern Python async messaging framework |
| Low-level Client | aio-pika | Async RabbitMQ client library |
| Validation | jsonschema | JSON Schema validation (>=4.25.1) |
| Models | Pydantic | Type-safe event envelope definitions |
| API | FastAPI | REST endpoints for health and metrics |
| Observability | OpenTelemetry | Distributed tracing |
| Metrics | Prometheus | Metrics collection |

### Event Patterns

#### EventEnvelope Structure

All events in 33GOD are wrapped in a standardized `EventEnvelope`:

```python
class EventEnvelope(BaseModel):
    """Canonical event envelope - source of truth defined in Holyfields."""

    event_id: UUID                      # Unique event identifier
    event_type: str                     # Event type (e.g., 'fireflies.transcript.ready')
    timestamp: datetime                 # Event creation timestamp
    version: str                        # Event schema version (e.g., 'v1')
    source: dict[str, Any]              # Source metadata (host, app, trigger_type)
    correlation_ids: list[UUID]         # Causation chain for tracing
    agent_context: dict[str, Any] | None  # Agent-specific context
    payload: dict[str, Any]             # Event-specific payload data
```

#### Topic Exchange Pattern

Bloodbank uses a topic exchange (`bloodbank.events.v1`) with routing key patterns:

```
Routing Key Pattern              Example
-----------------------          -------------------------
{domain}.{entity}.{action}       fireflies.transcript.ready
{domain}.{entity}.{status}       theboard.meeting.completed
{service}.{resource}.{event}     agent.feedback.requested
```

#### Queue Naming Convention

```
services.{domain}.{service_name}

Examples:
- services.fireflies.transcript_processor
- services.theboard.meeting_trigger
- services.agent.feedback_router
```

### Configuration Options

Environment variables for Bloodbank consumers:

| Variable | Default | Description |
|----------|---------|-------------|
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ connection URL |
| `BLOODBANK_EXCHANGE` | `bloodbank.events.v1` | Topic exchange name |
| `BLOODBANK_EXCHANGE_TYPE` | `topic` | Exchange type |
| `EVENT_STORE_MANAGER_QUEUE` | `event_store_manager_queue` | Queue name |
| `EVENT_STORE_MANAGER_DLQ` | `event_store_manager_dlq` | Dead letter queue name |

### Publisher API

```python
from event_producers.rabbit import Publisher
from event_producers.events.base import create_envelope, Source, TriggerType

# Initialize publisher
publisher = Publisher(enable_correlation_tracking=True)
await publisher.start()

# Create and publish an event
envelope = create_envelope(
    event_type="artifact.created",
    payload={
        "artifact_type": "transcript",
        "file_path": "/path/to/file.md",
    },
    source=Source(
        host="my-service",
        type=TriggerType.AGENT,
        app="my-service",
    ),
)

await publisher.publish(
    routing_key="artifact.created",
    body=envelope.model_dump(mode="json"),
    event_id=envelope.event_id,
)

await publisher.close()
```

### Consumer Patterns

#### FastStream Consumer (Recommended)

```python
from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, ExchangeType
from event_producers.events.base import EventEnvelope

broker = RabbitBroker("amqp://guest:guest@localhost:5672/")
app = FastStream(broker)

@broker.subscriber(
    queue=RabbitQueue(
        name="services.my.consumer",
        routing_key="domain.event.ready",
        durable=True,
    ),
    exchange=RabbitExchange(
        name="bloodbank.events.v1",
        type=ExchangeType.TOPIC,
        durable=True,
    ),
)
async def handle_event(message_dict: dict):
    # Explicit envelope unwrapping (ADR-0002 pattern)
    envelope = EventEnvelope(**message_dict)

    # Process the event
    payload = envelope.payload
    # ... business logic
```

#### aio-pika Consumer (Low-level)

```python
import aio_pika
from aio_pika import ExchangeType, IncomingMessage

connection = await aio_pika.connect_robust("amqp://guest:guest@localhost:5672/")
channel = await connection.channel()
await channel.set_qos(prefetch_count=10)

# Declare exchange
exchange = await channel.declare_exchange(
    "bloodbank.events.v1",
    ExchangeType.TOPIC,
    durable=True,
)

# Declare queue with DLQ
queue = await channel.declare_queue(
    "my_queue",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": "my_queue_dlq",
    },
)

# Bind and consume
await queue.bind(exchange, routing_key="domain.event.*")
await queue.consume(process_message)
```

### Health & Monitoring Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check |
| `/health/ready` | GET | Kubernetes readiness probe |
| `/metrics` | GET | Prometheus metrics |

---

## Holyfields - Schema Registry & Contract System

### Purpose

Holyfields is the **single source of truth** for all event contracts in 33GOD. It:
- Defines canonical event schemas using JSON Schema
- Generates type-safe code for multiple languages
- Enforces schema contracts across all components
- Manages schema versioning and deprecation

### Key Responsibilities

1. **Schema Definition** - Maintain JSON Schema definitions for all event types
2. **Code Generation** - Generate Pydantic (Python), Zod (TypeScript), and SQLAlchemy models
3. **Validation** - Provide schemas for runtime validation
4. **Governance** - Own schema change process (RFCs, versioning, deprecation)
5. **CI Integration** - Fail builds when generated code drifts from schemas

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Schema Definition | JSON Schema | Canonical event structure definitions |
| Python Generation | datamodel-code-generator | Generate Pydantic models |
| TypeScript Generation | json-schema-to-zod | Generate Zod validators |
| SQL Generation | Custom | Generate SQLAlchemy models |
| Validation | ajv (TS) / jsonschema (Py) | Runtime validation |

### Schema Directory Structure

```
holyfields/
├── schemas/
│   ├── core/
│   │   └── event-envelope.v1.schema.json    # Canonical EventEnvelope
│   ├── fireflies/
│   │   ├── transcript.upload.v1.schema.json
│   │   └── transcript.ready.v1.schema.json
│   ├── theboard/
│   │   ├── meeting.created.v1.schema.json
│   │   ├── meeting.started.v1.schema.json
│   │   ├── meeting.completed.v1.schema.json
│   │   └── meeting.converged.v1.schema.json
│   ├── agent/
│   │   ├── feedback.requested.v1.schema.json
│   │   └── feedback.response.v1.schema.json
│   └── artifact/
│       └── created.v1.schema.json
├── generated/
│   ├── python/                              # Generated Pydantic models
│   └── typescript/                          # Generated Zod validators
└── scripts/
    ├── generate-python.sh
    └── generate-typescript.sh
```

### Schema Generation Workflow

```mermaid
graph LR
    A[JSON Schema] --> B[datamodel-code-generator]
    A --> C[json-schema-to-zod]
    B --> D[Pydantic Models]
    C --> E[Zod Validators]
    D --> F[Bloodbank, Candystore]
    E --> G[Candybar]
```

#### Generate Python Types

```bash
# Using datamodel-code-generator
npm run generate:python

# Or manually:
datamodel-codegen \
  --input schemas/ \
  --output generated/python/ \
  --input-file-type jsonschema \
  --output-model-type pydantic_v2.BaseModel
```

#### Generate TypeScript Types

```bash
# Using json-schema-to-zod
npm run generate:typescript

# Or manually:
npx json-schema-to-zod \
  --input schemas/ \
  --output generated/typescript/
```

### Example Schema Definition

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://33god.dev/schemas/core/event-envelope.v1.schema.json",
  "title": "EventEnvelope",
  "description": "Canonical event envelope for all 33GOD events",
  "type": "object",
  "required": ["event_id", "event_type", "timestamp", "version", "source", "payload"],
  "properties": {
    "event_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique event identifier"
    },
    "event_type": {
      "type": "string",
      "pattern": "^[a-z]+\\.[a-z]+\\.[a-z]+$",
      "description": "Event type in domain.entity.action format"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp"
    },
    "version": {
      "type": "string",
      "pattern": "^v[0-9]+$",
      "description": "Schema version"
    },
    "source": {
      "type": "object",
      "required": ["host", "type", "app"],
      "properties": {
        "host": { "type": "string" },
        "type": { "type": "string", "enum": ["webhook", "agent", "manual", "system"] },
        "app": { "type": "string" }
      }
    },
    "correlation_ids": {
      "type": "array",
      "items": { "type": "string", "format": "uuid" },
      "default": []
    },
    "agent_context": {
      "type": ["object", "null"],
      "default": null
    },
    "payload": {
      "type": "object",
      "description": "Event-specific payload data"
    }
  }
}
```

### CI/CD Integration

```yaml
# Example GitHub Actions workflow
name: Schema Validation

on: [push, pull_request]

jobs:
  validate-schemas:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Validate JSON Schemas
        run: |
          npx ajv validate -s schemas/core/event-envelope.v1.schema.json

      - name: Generate Types
        run: |
          npm run generate:python
          npm run generate:typescript

      - name: Check for Drift
        run: |
          git diff --exit-code generated/
```

---

## Integration Points with Other Domains

### Event Consumers by Domain

| Domain | Components | Events Consumed |
|--------|------------|-----------------|
| **Voice & Transcription** | TalkyTonny, Tonny Agent | `transcription.voice.completed` |
| **Meeting Collaboration** | TheBoard, TheBoardRoom | `theboard.meeting.trigger`, `feature.brainstorm.requested` |
| **Agent Orchestration** | AgentForge, Yi, Flume | `agent.feedback.requested`, `feature.requested` |
| **Workspace Management** | iMi, Zellij Driver | `worktree.created`, `session.started` |
| **Dashboards & Visualization** | Candybar, Holocene | All events (`#` wildcard) |
| **Persistence** | Candystore | All events (`#` wildcard) |

### Service Registry

The service registry (`/home/user/33GOD/services/registry.yaml`) is the central authority for:
- Service discovery
- Queue bindings
- Event routing configuration
- Topology visualization (used by Candybar)

---

## Common Use Cases & Examples

### Use Case 1: Processing Fireflies Transcripts

```
1. Fireflies webhook triggers Node-RED
2. Node-RED publishes: fireflies.transcript.ready
3. fireflies-transcript-processor consumes event
4. Processor saves markdown to Vault
5. Processor publishes: artifact.created
6. Candystore persists both events
```

### Use Case 2: Triggering a TheBoard Brainstorming Session

```python
# Publishing a feature brainstorm request
from event_producers.rabbit import Publisher
from event_producers.events.base import create_envelope, Source, TriggerType

async def request_brainstorm(feature_name: str, description: str):
    publisher = Publisher()
    await publisher.start()

    envelope = create_envelope(
        event_type="feature.brainstorm.requested",
        payload={
            "feature_name": feature_name,
            "feature_description": description,
            "requirements": [],
            "constraints": [],
        },
        source=Source(
            host="my-service",
            type=TriggerType.MANUAL,
            app="feature-requester",
        ),
    )

    await publisher.publish(
        routing_key="feature.brainstorm.requested",
        body=envelope.model_dump(mode="json"),
    )

    await publisher.close()
```

### Use Case 3: Creating a New Event Consumer Service

1. **Register in registry.yaml**:
```yaml
my-new-service:
  name: "my-new-service"
  description: "Processes X events and does Y"
  type: "event-consumer"
  queue_name: "services.domain.my_service"
  routing_keys:
    - "domain.entity.action"
  status: "active"
  owner: "33GOD"
  produces:
    - "domain.result.created"
```

2. **Create the consumer**:
```python
from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, ExchangeType

broker = RabbitBroker("amqp://guest:guest@localhost:5672/")
app = FastStream(broker)

@broker.subscriber(
    queue=RabbitQueue(
        name="services.domain.my_service",
        routing_key="domain.entity.action",
        durable=True,
    ),
    exchange=RabbitExchange(
        name="bloodbank.events.v1",
        type=ExchangeType.TOPIC,
        durable=True,
    ),
)
async def handle_event(message_dict: dict):
    envelope = EventEnvelope(**message_dict)
    # Process event...
```

3. **Run with FastStream**:
```bash
uv run faststream run src.consumer:app --reload
```

---

## Troubleshooting Guide

### Problem: Events Not Being Received

**Symptoms**: Consumer is running but not processing events

**Check List**:
1. **Verify RabbitMQ connection**:
   ```bash
   rabbitmqctl list_connections
   ```

2. **Check queue bindings**:
   ```bash
   rabbitmqctl list_bindings | grep your_queue
   ```

3. **Verify routing key matches**:
   ```bash
   # Publisher is using: "fireflies.transcript.ready"
   # Consumer must bind to: "fireflies.transcript.ready" or "fireflies.transcript.*" or "#"
   ```

4. **Check exchange exists**:
   ```bash
   rabbitmqctl list_exchanges | grep bloodbank
   ```

### Problem: Messages Going to Dead Letter Queue

**Symptoms**: Messages appearing in DLQ instead of being processed

**Check List**:
1. **Check consumer logs for errors**:
   ```bash
   docker logs my-consumer-service 2>&1 | grep ERROR
   ```

2. **Inspect DLQ messages**:
   ```bash
   rabbitmqctl list_queues name messages | grep dlq
   ```

3. **Common causes**:
   - Invalid JSON in message body
   - Missing required fields in EventEnvelope
   - Consumer exception during processing
   - Schema validation failure

### Problem: Schema Validation Failing

**Symptoms**: Events rejected before publishing

**Check List**:
1. **Validate envelope structure**:
   ```python
   from jsonschema import validate
   import json

   with open("schemas/core/event-envelope.v1.schema.json") as f:
       schema = json.load(f)

   validate(instance=your_envelope, schema=schema)
   ```

2. **Check event_type format**: Must match `^[a-z]+\.[a-z]+\.[a-z]+$`

3. **Check required fields**:
   - `event_id` (UUID)
   - `event_type` (string)
   - `timestamp` (ISO 8601)
   - `version` (e.g., "v1")
   - `source` (object with host, type, app)
   - `payload` (object)

### Problem: Correlation IDs Not Propagating

**Symptoms**: Events not linked in causation chains

**Solution**:
```python
# When publishing a follow-up event, include parent's event_id in correlation_ids
child_envelope = create_envelope(
    event_type="child.event.created",
    payload={...},
    source=source,
    correlation_ids=[parent_envelope.event_id],  # Link to parent
)
```

### Problem: Consumer Memory Growing

**Symptoms**: Container memory increasing over time

**Solutions**:
1. Set proper prefetch count:
   ```python
   await channel.set_qos(prefetch_count=10)  # Don't set too high
   ```

2. Acknowledge messages promptly:
   ```python
   async with message.process():  # Auto-acks on success
       # Process message...
   ```

3. Avoid storing messages in memory; process and discard

---

## When to Explore This Domain

An AI agent should dig into the Infrastructure Domain when the user's prompt involves:

- **Events/Messaging**: "publish an event", "subscribe to events", "event bus", "RabbitMQ"
- **Schemas/Contracts**: "event schema", "validate message", "type generation", "Pydantic", "Zod"
- **Service Communication**: "how do services talk", "async communication", "message queue"
- **Reliability**: "dead letter queue", "message persistence", "event replay"
- **Tracing**: "correlation IDs", "event chain", "causation tracking"
- **Creating Services**: "new consumer", "subscribe to Bloodbank", "process events"

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `/home/user/33GOD/bloodbank/trunk-main/` | Bloodbank event bus implementation |
| `/home/user/33GOD/holyfields/trunk-main/` | Schema registry and generators |
| `/home/user/33GOD/services/registry.yaml` | Central service registry |
| `/home/user/33GOD/services/candystore/` | Event persistence layer |
| `/home/user/33GOD/services/templates/generic-consumer/` | Consumer service template |
| `/home/user/33GOD/docs/stakeholder-briefs/bloodbank-brief.md` | Bloodbank requirements |
| `/home/user/33GOD/docs/stakeholder-briefs/holyfields-brief.md` | Holyfields requirements |

---

## Related Documentation

- [Architecture Overview](/home/user/33GOD/docs/ARCHITECTURE.md)
- [Unified Requirements Map](/home/user/33GOD/docs/unified-requirements-map.md)
- [Service Developer Guide](/home/user/33GOD/docs/archive/2026-01-24/SERVICES_GUIDE.md)
- [Agents Directory](/home/user/33GOD/AGENTS.md)

---

## Last Updated

2026-01-30
