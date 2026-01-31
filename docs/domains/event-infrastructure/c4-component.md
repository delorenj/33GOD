# C4 Component Level: Event Infrastructure Domain

## Overview

**Domain**: Event Infrastructure
**Components**: Bloodbank (Event Bus), Holyfields (Schema Registry), Services (Consumers & Producers)
**Technology Stack**: RabbitMQ, Redis, Python (Pydantic), TypeScript (Zod), FastAPI
**Version**: 0.2.0

## Purpose

The Event Infrastructure domain provides the foundational event-driven architecture for the 33GOD ecosystem, enabling asynchronous, type-safe communication between distributed microservices. It implements a sophisticated publish-subscribe pattern with correlation tracking, schema validation, and contract-based development.

## Domain Components

### Component Index

1. **Event Bus Core** - RabbitMQ-based message routing and delivery
2. **Schema Registry** - Centralized schema management and code generation
3. **Publisher Services** - Event production and envelope management
4. **Subscriber Services** - Event consumption and processing
5. **Validation Pipeline** - Schema validation and contract enforcement
6. **Correlation Tracking** - Event causation and tracing
7. **Dead Letter Handling** - Error management and retry logic
8. **Monitoring & Observability** - Event metrics and health checks

---

## Component Diagram

```mermaid
C4Component
    title Component Diagram for Event Infrastructure Domain

    Container_Boundary(bloodbank, "Bloodbank Event Bus") {
        Component(publisher, "Publisher Component", "Python/aio_pika", "Manages RabbitMQ connections, publishes events with correlation tracking")
        Component(envelope_mgr, "Envelope Manager", "Python/Pydantic", "Creates standardized event envelopes with metadata")
        Component(consumer, "Consumer Component", "Python/aio_pika", "Generic RabbitMQ consumer with routing key binding")
        Component(correlation, "Correlation Tracker", "Python/Redis", "Tracks event causation chains, generates deterministic IDs")
        Component(validator, "Schema Validator", "Python/jsonschema", "Validates event payloads against HolyFields schemas")
        Component(http_gateway, "HTTP Gateway", "FastAPI", "REST API for event publishing")
        Component(cli_interface, "CLI Interface", "Python/Textual", "Terminal UI for event inspection and publishing")
        Component(registry, "Event Registry", "Python", "Type discovery and domain-based event organization")
        Component(command_proc, "Command Processor", "Python", "Executes Invokable commands with event collection")
        ComponentDb(rabbitmq, "RabbitMQ Broker", "Message Broker", "Topic exchange, durable queues, message routing")
        ComponentDb(redis_store, "Redis Store", "Cache/Store", "Correlation data, event chains, TTL management")
    }

    Container_Boundary(holyfields, "Holyfields Schema Registry") {
        Component(schema_store, "Schema Store", "JSON Schema", "Version-controlled event/command schemas")
        Component(python_gen, "Python Generator", "datamodel-code-generator", "Generates Pydantic models from schemas")
        Component(ts_gen, "TypeScript Generator", "json-schema-to-zod", "Generates Zod schemas and types")
        Component(contract_tests, "Contract Tests", "pytest/vitest", "Validates generated artifacts match schemas")
        Component(version_mgr, "Version Manager", "Semantic Versioning", "Tracks schema versions, detects breaking changes")
    }

    Container_Boundary(services, "Consumer & Producer Services") {
        Component(base_subscriber, "BaseSubscriber", "Abstract Class", "Template for event consumers with retry logic")
        Component(event_producer, "Event Producer", "Application Code", "Business logic that publishes events")
        Component(dlq_handler, "Dead Letter Handler", "Python/aio_pika", "Processes failed messages, implements retry")
        Component(metrics, "Metrics Collector", "Prometheus/Custom", "Tracks event counts, latencies, errors")
    }

    Container_Ext(external_triggers, "External Triggers", "HTTP/CLI/n8n/Webhooks", "Event sources")
    Container_Ext(downstream, "Downstream Services", "TheBoard/TheBoardroom/etc", "Event consumers")
    System_Ext(monitoring, "Monitoring System", "Observability platform")

    Rel(external_triggers, http_gateway, "POST /events", "HTTPS")
    Rel(external_triggers, cli_interface, "bb publish", "CLI")
    Rel(http_gateway, envelope_mgr, "Create envelope")
    Rel(envelope_mgr, registry, "Get payload type")
    Rel(envelope_mgr, validator, "Validate payload")
    Rel(validator, schema_store, "Load schema")
    Rel(http_gateway, publisher, "Publish event")
    Rel(publisher, correlation, "Track correlation")
    Rel(correlation, redis_store, "Store chain")
    Rel(publisher, rabbitmq, "Publish message", "AMQP")
    Rel(rabbitmq, consumer, "Deliver message", "AMQP")
    Rel(consumer, base_subscriber, "Route to handler")
    Rel(base_subscriber, command_proc, "Execute command")
    Rel(command_proc, publisher, "Publish side effects")
    Rel(consumer, dlq_handler, "Failed messages")
    Rel(dlq_handler, rabbitmq, "Retry or DLQ")
    Rel(schema_store, python_gen, "Generate models")
    Rel(schema_store, ts_gen, "Generate schemas")
    Rel(python_gen, event_producer, "Import types")
    Rel(ts_gen, downstream, "Import types")
    Rel(contract_tests, python_gen, "Validate")
    Rel(contract_tests, ts_gen, "Validate")
    Rel(metrics, monitoring, "Export metrics")
    Rel(publisher, metrics, "Record publish")
    Rel(consumer, metrics, "Record consume")
```

---

## Component Details

### 1. Event Bus Core

**Component Name**: Event Bus Core
**Type**: Message Broker Infrastructure
**Technology**: RabbitMQ 3.x, aio_pika
**Code Location**: `bloodbank/trunk-main/event_producers/rabbit.py`

#### Purpose
Provides the foundational message routing and delivery infrastructure for the entire event-driven ecosystem. Manages durable topic exchanges, persistent queues, and reliable message delivery.

#### Features
- **Topic-based routing**: Events routed by `domain.entity.action` patterns (e.g., `theboard.meeting.created`)
- **Durable exchanges**: Messages survive broker restarts
- **Publisher confirms**: Guaranteed message delivery acknowledgment
- **Connection pooling**: Automatic reconnection with exponential backoff
- **Prefetch control**: QoS settings for consumer throughput tuning

#### Interfaces

##### Publishing Interface
- **Protocol**: AMQP 0.9.1
- **Operations**:
  - `publish(routing_key: str, body: dict, message_id: UUID) -> None` - Publish event to exchange
  - `start() -> None` - Initialize connection pool
  - `close() -> None` - Gracefully shutdown connections

##### Consumption Interface
- **Protocol**: AMQP 0.9.1
- **Operations**:
  - `consume(callback: Callable, routing_keys: List[str]) -> None` - Subscribe to routing patterns
  - `bind(routing_key: str) -> None` - Add routing key binding
  - `ack(delivery_tag: int) -> None` - Acknowledge message processing
  - `nack(delivery_tag: int, requeue: bool) -> None` - Reject message

#### Configuration
```python
# Exchange configuration
EXCHANGE_NAME = "bloodbank.events.v1"
EXCHANGE_TYPE = "topic"
DURABLE = True

# Queue configuration
PREFETCH_COUNT = 10
MESSAGE_TTL = 86400000  # 24 hours
MAX_RETRIES = 3
```

---

### 2. Schema Registry

**Component Name**: Schema Registry (Holyfields)
**Type**: Code Generation Pipeline
**Technology**: JSON Schema, Python (datamodel-code-generator), TypeScript (json-schema-to-zod)
**Code Location**: `holyfields/trunk-main/`

#### Purpose
Provides a single source of truth for event and command schemas, enabling independent component development with guaranteed type safety across Python and TypeScript services.

#### Features
- **Schema-first design**: Define contracts as JSON Schema Draft 2020-12
- **Multi-language codegen**: Auto-generate Pydantic (Python) and Zod (TypeScript) artifacts
- **Version management**: Semantic versioning with breaking change detection
- **Contract testing**: Automated validation of generated code against schemas
- **Component isolation**: Independent schemas for each microservice (theboard, whisperlivekit, etc.)

#### Interfaces

##### Schema Definition Interface
- **Format**: JSON Schema Draft 2020-12
- **Structure**:
  ```json
  {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://33god.dev/schemas/{component}/events/{event}.json",
    "type": "object",
    "properties": {...},
    "required": [...]
  }
  ```

##### Generation Interface
- **Python Output**: Pydantic BaseModel classes
- **TypeScript Output**: Zod schemas with TypeScript type inference
- **Commands**:
  - `mise run generate:python` - Generate Python models
  - `mise run generate:typescript` - Generate TypeScript schemas
  - `mise run validate:schemas` - Validate schema structure
  - `mise run test:all` - Run contract tests

#### Code Elements
- `common/schemas/` - Shared base types and enums
- `theboard/events/` - TheBoard event schemas (7 events)
- `whisperlivekit/events/` - Transcription event schemas
- `scripts/generate_python.py` - Python code generator
- `scripts/generate_typescript.ts` - TypeScript code generator
- `tests/python/` - Pydantic contract tests
- `tests/typescript/` - Zod contract tests

---

### 3. Publisher Services

**Component Name**: Publisher Services
**Type**: Event Production Layer
**Technology**: Python/FastAPI, Pydantic
**Code Location**: `bloodbank/trunk-main/event_producers/`

#### Purpose
Manages event envelope creation, payload validation, and event publishing workflow. Provides both programmatic and HTTP interfaces for event production.

#### Features
- **Envelope standardization**: Wraps all events in typed `EventEnvelope[T]` with metadata
- **Source tracking**: Records WHO triggered event (manual, agent, scheduled, webhook)
- **Agent context**: Captures AI agent metadata (type, prompt, files, git state)
- **Type-safe publishing**: Generic envelope with payload type inference
- **HTTP gateway**: REST API for external event producers
- **CLI interface**: Terminal UI for manual event publishing

#### Interfaces

##### HTTP Publishing API
- **Protocol**: REST/HTTP
- **Base URL**: `http://localhost:8000`
- **Operations**:
  - `POST /events/publish` - Generic publish endpoint
    ```json
    {
      "event_type": "theboard.meeting.created",
      "payload": {...}
    }
    ```
  - `POST /events/{domain}` - Domain-specific endpoints (backward compat)
  - `GET /health` - Health check

##### Programmatic Publishing API
- **Protocol**: Python API
- **Operations**:
  ```python
  from event_producers.rabbit import Publisher
  from event_producers.events import envelope_for

  publisher = Publisher()
  await publisher.start()

  envelope = envelope_for(
      event_type="theboard.meeting.created",
      source="my-service",
      data=meeting_data
  )

  await publisher.publish(
      routing_key=envelope.event_type,
      body=envelope.model_dump(),
      message_id=envelope.event_id
  )
  ```

##### CLI Publishing API
- **Protocol**: CLI
- **Commands**:
  - `bb publish --type "theboard.meeting.created" --payload '{...}'`
  - `bb watch-events --routing-key "theboard.*"`
  - `bb inspect --event-id <uuid>`

#### Code Elements
- `http.py` - FastAPI gateway
- `rabbit.py` - Publisher implementation
- `cli.py` - CLI interface
- `events/envelope.py` - Envelope creation helpers
- `events/base.py` - Base envelope types

---

### 4. Subscriber Services

**Component Name**: Subscriber Services
**Type**: Event Consumption Layer
**Technology**: Python/aio_pika, Abstract Base Classes
**Code Location**: `bloodbank/trunk-main/event_producers/events/core/`

#### Purpose
Provides reusable patterns for event consumers with built-in retry logic, error handling, and dead-letter queue management.

#### Features
- **BaseSubscriber pattern**: Abstract class for consistent consumer implementation
- **Routing key binding**: Subscribe to specific event patterns (e.g., `theboard.*`, `#`)
- **Automatic retry**: Configurable retry with exponential backoff
- **Dead-letter handling**: Failed messages routed to DLQ for analysis
- **Generic consumer**: Reusable consumer for any event type

#### Interfaces

##### Consumer Interface
- **Protocol**: Python ABC
- **Required Methods**:
  ```python
  class BaseSubscriber(ABC):
      @abstractmethod
      async def handle_event(self, envelope: EventEnvelope) -> None:
          """Process the event"""
          pass

      @abstractmethod
      def get_routing_keys(self) -> List[str]:
          """Return routing keys to subscribe"""
          pass
  ```

##### Consumer Implementation Example
```python
from event_producers.events.core.consumer import Consumer

consumer = Consumer(service_name="my-service")

async def handle_meeting_created(payload: dict):
    envelope = EventEnvelope(**payload)
    # Process event
    logger.info(f"Meeting created: {envelope.payload}")

await consumer.start(
    callback=handle_meeting_created,
    routing_keys=["theboard.meeting.*"]
)
```

#### Code Elements
- `events/core/consumer.py` - Generic consumer implementation
- `events/core/abstraction.py` - BaseCommand, EventCollector patterns
- `subscriber_example.py` - Example subscriber

---

### 5. Validation Pipeline

**Component Name**: Validation Pipeline
**Type**: Schema Validation & Contract Enforcement
**Technology**: Python/jsonschema, JSON Schema Draft 2020-12
**Code Location**: `bloodbank/trunk-main/event_producers/schema_validator.py`

#### Purpose
Validates event payloads against HolyFields JSON schemas before publishing, ensuring contract compliance and preventing invalid events from entering the system.

#### Features
- **Pre-publish validation**: Validate payloads before RabbitMQ publish
- **Schema discovery**: Auto-discover schemas from HolyFields repository
- **Schema caching**: LRU cache for performance
- **Strict/permissive modes**: Fail or warn on missing schemas
- **Detailed error messages**: Path-based validation errors
- **Envelope validation**: Validates envelope structure separately

#### Interfaces

##### Validation Interface
- **Protocol**: Python API
- **Operations**:
  ```python
  from event_producers.schema_validator import validate_event

  result = validate_event(
      event_type="theboard.meeting.created",
      payload={"meeting_id": "...", "topic": "..."},
      strict=True
  )

  if not result.valid:
      raise ValidationError(result.errors)
  ```

##### Validation Result
```python
@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    schema_path: Optional[str]
```

#### Schema Discovery Logic
1. Parse event type: `component.entity.action`
2. Map to HolyFields component directory
3. Search for schema file: `{component}/events/{event}.v1.schema.json`
4. Load and cache schema
5. Validate using jsonschema library

#### Code Elements
- `schema_validator.py` - Validator implementation
- `tests/test_schema_validation.py` - Validation tests

---

### 6. Correlation Tracking

**Component Name**: Correlation Tracker
**Type**: Event Causation & Tracing
**Technology**: Redis, UUID v5 (deterministic)
**Code Location**: `bloodbank/trunk-main/event_producers/correlation_tracker.py`

#### Purpose
Tracks causal relationships between events, enabling debugging of event chains, idempotency through deterministic IDs, and distributed tracing.

#### Features
- **Deterministic event IDs**: UUID v5 based on `event_type + unique_key`
- **Correlation chains**: Parent → child event relationships stored in Redis
- **Bidirectional queries**: Find ancestors or descendants of any event
- **TTL management**: Correlation data expires after 30 days
- **Async Redis**: Non-blocking correlation tracking with connection pooling
- **Graceful degradation**: System works without Redis (logs warning)

#### Interfaces

##### ID Generation Interface (Sync)
```python
def generate_event_id(
    event_type: str,
    unique_key: str,
    namespace: str = "bloodbank"
) -> UUID:
    """Generate deterministic UUID for idempotency"""
    # Same input → same UUID
    return uuid5(NAMESPACE_OID, f"{namespace}:{event_type}:{unique_key}")
```

##### Correlation Tracking Interface (Async)
```python
async def add_correlation(
    child_event_id: UUID,
    parent_event_ids: List[UUID],
    metadata: Optional[Dict] = None
) -> None:
    """Link child event to parent events"""

async def get_parents(event_id: UUID) -> List[UUID]:
    """Get immediate parent event IDs"""

async def get_children(event_id: UUID) -> List[UUID]:
    """Get immediate child event IDs"""

async def get_correlation_chain(
    event_id: UUID,
    direction: str = "ancestors",  # or "descendants"
    max_depth: int = 100
) -> List[UUID]:
    """Get full correlation chain"""
```

#### Redis Data Model
```
# Forward mapping: child → parents
bloodbank:correlation:forward:{child_id} = {
    "parent_event_ids": ["uuid1", "uuid2"],
    "created_at": "2025-01-29T...",
    "metadata": {...}
}

# Reverse mapping: parent → children (set)
bloodbank:correlation:reverse:{parent_id} = {"child_id1", "child_id2", ...}
```

#### Code Elements
- `correlation_tracker.py` - Tracker implementation
- `tests/test_correlation_tracking.py` - Correlation tests

---

### 7. Dead Letter Handling

**Component Name**: Dead Letter Handler
**Type**: Error Recovery & Retry Logic
**Technology**: RabbitMQ DLX (Dead Letter Exchange)
**Code Location**: Consumer implementation pattern

#### Purpose
Manages failed message processing, implements retry strategies, and routes permanently failed messages to dead-letter queues for analysis.

#### Features
- **Automatic retry**: Exponential backoff for transient failures
- **Max retry limits**: Prevent infinite retry loops
- **DLX routing**: Failed messages routed to separate queue
- **Failure analysis**: Dead letters preserved for debugging
- **Manual reprocessing**: CLI tools to replay dead letters

#### Interfaces

##### Consumer Error Handling
```python
async def _on_message(self, message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            payload = orjson.loads(message.body)
            await self._callback(payload)
            # Auto-ack on success
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Auto-nack + DLX route
            raise e
```

##### DLX Configuration
```python
# Queue with DLX
queue_args = {
    "x-dead-letter-exchange": "bloodbank.events.dlx",
    "x-dead-letter-routing-key": "failed",
    "x-message-ttl": 86400000,  # 24 hours
    "x-max-retries": 3
}
```

#### Retry Strategy
1. **First failure**: Nack with requeue
2. **Second failure**: Nack with requeue + exponential delay
3. **Third failure**: Nack without requeue → DLX
4. **Dead letter queue**: Manual analysis and replay

---

### 8. Monitoring & Observability

**Component Name**: Metrics Collector
**Type**: Observability & Health Monitoring
**Technology**: Prometheus (planned), Python logging
**Code Location**: Distributed across components

#### Purpose
Provides visibility into event bus health, throughput, latencies, and error rates. Enables proactive issue detection and performance optimization.

#### Features
- **Event counters**: Published/consumed events per routing key
- **Latency metrics**: End-to-end event processing time
- **Error rates**: Failed validations, consumer errors, DLQ entries
- **Connection health**: RabbitMQ/Redis connection status
- **Correlation depth**: Event chain depth metrics

#### Interfaces

##### Metrics Interface (Planned)
```python
# Prometheus metrics
event_published_total = Counter(
    "bloodbank_events_published_total",
    "Total events published",
    ["routing_key"]
)

event_consumed_total = Counter(
    "bloodbank_events_consumed_total",
    "Total events consumed",
    ["routing_key", "consumer"]
)

event_validation_errors = Counter(
    "bloodbank_validation_errors_total",
    "Schema validation failures",
    ["event_type"]
)

event_processing_latency = Histogram(
    "bloodbank_processing_latency_seconds",
    "Event processing latency",
    ["routing_key"]
)
```

##### Health Check Interface
```http
GET /health
Response: {
  "status": "healthy",
  "rabbitmq": "connected",
  "redis": "connected",
  "holyfields": "available"
}
```

---

## Component Relationships

### Publisher Flow
1. **External Trigger** → **HTTP Gateway** (POST /events/publish)
2. **HTTP Gateway** → **Registry** (Get payload type)
3. **HTTP Gateway** → **Envelope Manager** (Create envelope)
4. **Envelope Manager** → **Schema Validator** (Validate payload)
5. **Schema Validator** → **Schema Store** (Load schema)
6. **HTTP Gateway** → **Publisher** (Publish event)
7. **Publisher** → **Correlation Tracker** (Track correlation)
8. **Correlation Tracker** → **Redis Store** (Store chain)
9. **Publisher** → **RabbitMQ** (AMQP publish)

### Subscriber Flow
1. **RabbitMQ** → **Consumer** (Deliver message)
2. **Consumer** → **BaseSubscriber** (Route to handler)
3. **BaseSubscriber** → **Command Processor** (Execute command, if applicable)
4. **Command Processor** → **Publisher** (Publish side effects)
5. **Consumer** → **Dead Letter Handler** (On failure)
6. **Dead Letter Handler** → **RabbitMQ** (Retry or DLQ)

### Schema Evolution Flow
1. **Developer** → **Schema Store** (Define/update schema)
2. **CI Pipeline** → **Python Generator** (Generate Pydantic models)
3. **CI Pipeline** → **TypeScript Generator** (Generate Zod schemas)
4. **CI Pipeline** → **Contract Tests** (Validate artifacts)
5. **CI Pipeline** → **Version Manager** (Detect breaking changes)
6. **Event Producer** → **Python Generator** (Import types)
7. **Downstream Services** → **TypeScript Generator** (Import types)

---

## Design Patterns Used

### 1. Envelope Pattern
All events wrapped in standardized `EventEnvelope[T]` with metadata, enabling consistent handling across the ecosystem.

### 2. Registry Pattern
Centralized event type discovery and validation through domain-based organization.

### 3. Command Pattern
Commands implement `Invokable[R]` interface with `execute()` and `rollback()` methods, enabling transactional event processing.

### 4. Publisher-Subscriber Pattern
Topic-based routing with multiple consumers per event type, enabling loose coupling.

### 5. Dead Letter Queue Pattern
Failed messages routed to separate queue for analysis and manual retry.

### 6. Schema Registry Pattern
Centralized schema management with code generation for type safety.

### 7. Correlation ID Pattern
Parent-child event relationships tracked through Redis, enabling distributed tracing.

### 8. Template Method Pattern
`BaseSubscriber` abstract class defines subscription workflow, subclasses implement event handling.

---

## Extension Points

### Adding New Event Types
1. Define JSON schema in HolyFields (`{component}/events/{event}.v1.schema.json`)
2. Run `mise run generate:all` to generate Python/TypeScript artifacts
3. Import generated types in producer/consumer code
4. Publish events using generated Pydantic models

### Adding New Consumers
1. Subclass `BaseSubscriber` or use generic `Consumer`
2. Implement `handle_event()` method
3. Define routing keys in `get_routing_keys()`
4. Start consumer with `await consumer.start()`

### Adding New Validation Rules
1. Update JSON schema in HolyFields
2. Validator automatically uses updated schema (cached)
3. Contract tests validate new rules

### Adding Custom Correlation Logic
1. Extend `CorrelationTracker` class
2. Override `add_correlation()` to add custom metadata
3. Implement custom query methods

---

## Deployment Considerations

### RabbitMQ Configuration
- **Exchange**: `bloodbank.events.v1` (topic, durable)
- **Queues**: Auto-created per service, durable
- **Prefetch**: 10 messages per consumer
- **Message TTL**: 24 hours
- **Dead letter exchange**: `bloodbank.events.dlx`

### Redis Configuration
- **Purpose**: Correlation tracking only (non-critical)
- **TTL**: 30 days
- **Database**: 0 (default)
- **Connection pool**: Async, auto-reconnect

### HolyFields Integration
- **Location**: Relative path or environment variable
- **Auto-discovery**: Searches common locations
- **Fallback**: Permissive mode if schemas not found

### Environment Variables
```bash
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
REDIS_HOST=localhost
REDIS_PORT=6379
HOLYFIELDS_PATH=/path/to/holyfields/trunk-main
VALIDATION_STRICT=true
```

---

## Performance Characteristics

### Throughput
- **Publisher**: ~1000 events/sec (single instance)
- **Consumer**: ~500 events/sec (depends on handler logic)
- **Validation**: ~2000 schemas/sec (with caching)

### Latency
- **Publish**: 5-10ms (without correlation tracking)
- **Publish + Correlation**: 15-25ms (Redis write)
- **Consume**: <5ms (envelope parsing)
- **End-to-end**: 20-50ms (depending on consumer logic)

### Scalability
- **Horizontal scaling**: Multiple publisher/consumer instances
- **Queue partitioning**: Separate queues per service
- **RabbitMQ clustering**: Multi-node broker deployment

---

## Testing Strategy

### Unit Tests
- Publisher: Connection pooling, retry logic
- Consumer: Message parsing, error handling
- Validator: Schema matching, error messages
- Correlation: ID generation, chain traversal

### Integration Tests
- End-to-end publish → consume flow
- Schema validation with real HolyFields schemas
- Correlation tracking with Redis
- Dead letter queue handling

### Contract Tests
- Generated Pydantic models match schemas
- Generated Zod schemas match schemas
- TypeScript types match Pydantic models

---

## Related Documentation

### Bloodbank
- [Architecture](file:///home/delorenj/code/33GOD/bloodbank/trunk-main/docs/ARCHITECTURE.md)
- [CLI Reference](file:///home/delorenj/code/33GOD/bloodbank/trunk-main/docs/bb-cli-reference.md)
- [Event Types](file:///home/delorenj/code/33GOD/bloodbank/trunk-main/docs/EVENT_TYPES.md)
- [RabbitMQ Infrastructure](file:///home/delorenj/code/33GOD/bloodbank/trunk-main/docs/rabbitmq-infrastructure.md)

### Holyfields
- [Product Brief](file:///home/delorenj/code/33GOD/holyfields/trunk-main/docs/product-brief-holyfields-2026-01-14.md)
- [Technical Specification](file:///home/delorenj/code/33GOD/holyfields/trunk-main/docs/tech-spec-holyfields-2026-01-14.md)
- [README](file:///home/delorenj/code/33GOD/holyfields/trunk-main/README.md)

---

## Version History

- **0.2.0** (Current): Added schema validation, correlation tracking, CLI interface
- **0.1.0**: Initial event bus with RabbitMQ, basic publisher/consumer

---

## Contributors

- Jarad DeLorenzo - Lead Architect, 33GOD Ecosystem
- Claude Sonnet 4.5 - Documentation & Component Analysis
