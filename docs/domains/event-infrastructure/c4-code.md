# C4 Code Level: Event Infrastructure Domain (Bloodbank)

## Overview
- **Name**: Event Infrastructure - Bloodbank Event Bus
- **Description**: RabbitMQ-based event-driven messaging infrastructure with Pydantic schema validation, FastStream integration, and correlation tracking
- **Location**: `/home/delorenj/code/33GOD/bloodbank/trunk-main/event_producers/`
- **Language**: Python 3.12+
- **Purpose**: Provides a type-safe, schema-validated event bus for inter-service communication across the 33GOD platform using CQRS and event sourcing patterns

## Architecture Pattern

This codebase implements **Event-Driven Architecture** with **CQRS (Command Query Responsibility Segregation)** patterns:

- **Commands**: Actions that change state (e.g., `AgentThreadPrompt`)
- **Events**: Facts about what happened (e.g., `FirefliesTranscriptReadyPayload`)
- **Event Sourcing**: Full correlation tracking via Redis for event causation chains
- **EventEnvelope Pattern**: Generic wrapper for all events with metadata (source, agent context, timestamps)

## Code Elements

### Core Event System

#### EventEnvelope (Generic Container)

**Location**: `event_producers/events/base.py:85-108`

```python
class EventEnvelope(BaseModel, Generic[T]):
    event_id: UUID
    event_type: str  # Routing key
    timestamp: datetime
    version: str  # "1.0.0"
    source: Source
    correlation_ids: List[UUID]
    agent_context: Optional[AgentContext]
    payload: T  # Generic payload type
```

**Purpose**: Universal wrapper for all events in the system. Provides event metadata, correlation tracking, and agent context while keeping payloads type-safe.

**Key Features**:
- Generic type `T` for type-safe payload access
- Automatic UUID generation for `event_id`
- Correlation tracking for parent-child event relationships
- Agent context for AI agent metadata (system prompts, MCP servers, code state)

#### Source Metadata

**Location**: `event_producers/events/base.py:34-41`

```python
class Source(BaseModel):
    host: str  # Machine that generated event
    type: TriggerType  # manual, agent, scheduled, file_watch, hook
    app: Optional[str]
    meta: Optional[Dict[str, Any]]
```

**Purpose**: Identifies the origin of an event (human, agent, cron job, webhook).

#### AgentContext

**Location**: `event_producers/events/base.py:67-80`

```python
class AgentContext(BaseModel):
    type: AgentType  # claude-code, gemini-cli, letta, etc.
    name: Optional[str]
    system_prompt: Optional[str]
    instance_id: Optional[str]
    mcp_servers: Optional[List[str]]
    file_references: Optional[List[str]]
    url_references: Optional[List[str]]
    code_state: Optional[CodeState]
    checkpoint_id: Optional[str]
    meta: Optional[Dict[str, Any]]
```

**Purpose**: Captures rich metadata about AI agents for observability and debugging.

### Envelope Creation Helpers

**Location**: `event_producers/events/envelope.py`

#### Main Factory Functions

```python
def create_envelope(
    event_type: str,
    payload: Any,
    source: Union[Source, str],
    correlation_ids: Optional[List[Union[UUID, str]]] = None,
    agent_context: Optional[AgentContext] = None,
    event_id: Optional[UUID] = None,
) -> EventEnvelope
```

**Purpose**: Primary envelope creation with flexible source handling (accepts string or Source object).

#### Specialized Envelope Creators

```python
def create_http_envelope(...) -> EventEnvelope
def create_agent_envelope(...) -> EventEnvelope
def create_scheduled_envelope(...) -> EventEnvelope
```

**Purpose**: Convenience functions for common event source patterns.

### Publishing Infrastructure

#### Publisher (RabbitMQ)

**Location**: `event_producers/rabbit.py:34-331`

```python
class Publisher:
    def __init__(
        self,
        enable_correlation_tracking: bool = False,
        redis_host: Optional[str] = None,
        redis_port: Optional[int] = None,
        redis_password: Optional[str] = None,
    )

    async def start() -> None
    async def publish(
        routing_key: str,
        body: Dict[str, Any],
        event_id: Optional[UUID] = None,
        parent_event_ids: Optional[List[UUID]] = None,
        correlation_metadata: Optional[Dict[str, Any]] = None,
    ) -> None

    def generate_event_id(event_type: str, **unique_fields) -> UUID
    async def get_correlation_chain(event_id: UUID, direction: str) -> List[UUID]
    async def debug_correlation(event_id: UUID) -> Dict[str, Any]
    async def close() -> None
```

**Purpose**: RabbitMQ publisher with optional Redis-backed correlation tracking for event causation chains.

**Key Features**:
- Deterministic event ID generation for idempotency
- Publisher confirms for reliable delivery
- Correlation tracking with parent-child relationships
- Graceful degradation if Redis unavailable
- Topic exchange routing

**Dependencies**:
- `aio_pika` for async RabbitMQ
- `orjson` for fast JSON serialization
- `CorrelationTracker` for Redis-backed event correlation

### Consumer Infrastructure

#### FastStream Consumer

**Location**: `event_producers/consumer.py:1-41`

```python
broker = RabbitBroker(settings.rabbit_url)

exchange = RabbitExchange(
    name=settings.exchange_name,  # "bloodbank.events.v1"
    type=ExchangeType.TOPIC,
    durable=True,
)

app = FastStream(broker)
```

**Purpose**: FastStream application and broker configuration for declarative subscribers.

**Usage Pattern**:
```python
@broker.subscriber(
    "fireflies_queue",
    exchange="bloodbank.events.v1",
    routing_key="fireflies.transcript.ready"
)
async def handle_ready(msg: FirefliesTranscriptReadyPayload):
    ...
```

#### Generic Consumer (aio-pika)

**Location**: `event_producers/events/core/consumer.py:10-82`

```python
class Consumer:
    def __init__(self, service_name: str)

    async def start(
        callback: Callable[[dict], Awaitable[None]],
        routing_keys: List[str]
    ) -> None

    async def close() -> None
```

**Purpose**: Lower-level generic RabbitMQ consumer using aio-pika directly.

**Features**:
- QoS prefetch_count=10
- Durable queues
- Topic exchange binding
- Auto-ack on success, nack on failure

### CQRS Command System

#### Command Abstraction

**Location**: `event_producers/events/core/abstraction.py`

```python
class Invokable(ABC, Generic[R]):
    @abstractmethod
    def execute(self, context: CommandContext, collector: EventCollector) -> R

    def rollback(self, context: CommandContext) -> None
```

**Purpose**: Interface for executable commands that produce side effects.

```python
class EventCollector:
    def add(self, event: EventEnvelope) -> None
    def collect(self) -> List[EventEnvelope]
```

**Purpose**: Collects side-effect events produced during command execution (FIFO principle).

```python
class CommandContext(BaseModel):
    correlation_id: UUID
    source_app: str
    agent_context: Optional[AgentContext]
    timestamp: datetime
```

**Purpose**: Execution context passed to command handlers.

```python
class BaseCommand(BaseEvent, Invokable[R]):
    pass  # Commands are Pydantic models + behavior
```

**Purpose**: Base class for commands (data + logic).

#### Command Manager

**Location**: `event_producers/events/core/manager.py:12-91`

```python
class CommandManager:
    def __init__(self, publisher: Publisher)

    async def handle_envelope(self, envelope: EventEnvelope) -> None
    async def _execute_command(self, command: Invokable, envelope: EventEnvelope) -> None
```

**Purpose**: Central orchestrator for CQRS pattern. Routes events to command handlers and publishes side effects.

**Workflow**:
1. Re-hydrate payload from EventEnvelope using registry
2. Check if payload is `Invokable` (command vs fact event)
3. Execute command with context and event collector
4. Publish side-effect events back to RabbitMQ

### Event Registry System

#### EventRegistry

**Location**: `event_producers/events/registry.py:103-436`

```python
class EventRegistry:
    def register(
        event_type: str,
        payload_class: Type[BaseModel],
        domain_name: Optional[str] = None
    ) -> None

    def get_payload_type(self, event_type: str) -> Optional[Type[BaseModel]]
    def is_valid_event_type(self, event_type: str) -> bool
    def list_domains(self) -> List[str]
    def list_domain_events(self, domain_name: str) -> List[str]
    def get_schema(self, event_type: str) -> Optional[Dict[str, Any]]
    def auto_discover_domains(self) -> None
```

**Purpose**: Centralized registry for event type discovery and payload validation.

**Key Features**:
- Auto-discovery of domain modules
- Maps routing keys to Pydantic payload classes
- JSON schema generation for each event type
- Supports nested domain structures (e.g., `agent/thread`)

**Discovery Pattern**:
```python
# Each domain module exports:
ROUTING_KEYS = {
    "FirefliesTranscriptReadyPayload": "fireflies.transcript.ready",
    "AgentThreadPrompt": "agent.thread.prompt",
}
```

#### EventDomain

**Location**: `event_producers/events/registry.py:26-101`

```python
class EventDomain:
    def __init__(self, name: str, module_name: str)
    def add_event_type(self, event_type: str, payload_class: Type[BaseModel])
    def get_payload_type(self, event_type: str) -> Optional[Type[BaseModel]]
    def list_events(self) -> List[str]
```

**Purpose**: Groups related events by domain (fireflies, agent, github, etc.).

### Domain Event Schemas

#### Fireflies Domain

**Location**: `event_producers/events/domains/fireflies.py`

**Event Types**:

```python
class FirefliesTranscriptUploadPayload(BaseModel):
    """Request to upload media to Fireflies for transcription."""
    media_file: str
    media_duration_seconds: int
    media_type: str
    title: Optional[str]
    user_id: Optional[str]
    created_at: datetime
```
**Routing Key**: `fireflies.transcript.upload`

```python
class FirefliesTranscriptReadyPayload(BaseModel):
    """Published when Fireflies completes transcription (webhook payload)."""
    id: str  # Fireflies meeting ID
    title: str
    date: datetime
    duration: float
    transcript_url: str
    audio_url: Optional[str]
    video_url: Optional[str]
    sentences: List[TranscriptSentence]  # Full transcript included
    summary: Optional[str]
    participants: List[MeetingParticipant]
    speakers: List[str]
    user: FirefliesUser
    host_email: str
    organizer_email: str
    privacy: str
    meeting_link: Optional[str]
    calendar_id: Optional[str]
    calendar_type: Optional[str]
    raw_meeting_info: Optional[Dict[str, Any]]
```
**Routing Key**: `fireflies.transcript.ready`

```python
class FirefliesTranscriptProcessedPayload(BaseModel):
    """Published after transcript is ingested into RAG system."""
    transcript_id: str
    rag_document_id: str
    title: str
    ingestion_timestamp: datetime
    sentence_count: int
    speaker_count: int
    duration_minutes: float
    vector_store: str
    chunk_count: int
    embedding_model: Optional[str]
    metadata: Dict[str, Any]
```
**Routing Key**: `fireflies.transcript.processed`

```python
class FirefliesTranscriptFailedPayload(BaseModel):
    """Published when transcription or processing fails."""
    failed_stage: Literal["upload", "transcription", "processing"]
    error_message: str
    error_code: Optional[str]
    transcript_id: Optional[str]
    media_file: Optional[str]
    timestamp: datetime
    retry_count: int
    is_retryable: bool
    metadata: Dict[str, Any]
```
**Routing Key**: `fireflies.transcript.failed`

**Supporting Models**:

```python
class TranscriptSentence(BaseModel):
    index: int
    speaker_name: Optional[str]
    speaker_id: int
    raw_text: str
    text: str
    start_time: float
    end_time: float
    ai_filters: AIFilters

class AIFilters(BaseModel):
    text_cleanup: str
    task: Optional[str]
    pricing: Optional[str]
    metric: Optional[str]
    question: Optional[str]
    date_and_time: Optional[str]
    sentiment: SentimentType

class MeetingParticipant(BaseModel):
    name: str
    email: Optional[str]

class FirefliesUser(BaseModel):
    user_id: str
    email: str
    name: str
    num_transcripts: int
    minutes_consumed: float
    is_admin: bool
```

#### Agent Thread Domain

**Location**: `event_producers/events/domains/agent/thread.py`

```python
class AgentThreadPrompt(BaseCommand[AgentThreadResponse]):
    """Command: Send prompt to agent (implements Invokable)."""
    provider: str
    model: Optional[str]
    prompt: str
    project: Optional[str]
    working_dir: Optional[str]
    domain: Optional[str]
    tags: List[str]

    async def execute(
        self,
        context: CommandContext,
        collector: EventCollector
    ) -> AgentThreadResponse
```
**Routing Key**: `agent.thread.prompt`

```python
class AgentThreadResponse(BaseEvent):
    """Event: Agent responded to prompt."""
    provider: str
    prompt_id: Optional[str]  # Deprecated
    response: str
    model: Optional[str]
    tokens_used: Optional[int]
    duration_ms: Optional[int]
```
**Routing Key**: `agent.thread.response`

```python
class AgentThreadErrorPayload(BaseEvent):
    """Event: Agent interaction failed."""
    provider: str
    model: Optional[str]
    error_message: str
    error_code: Optional[str]
    is_retryable: bool
    retry_count: int
```
**Routing Key**: `agent.thread.error`

### Configuration

**Location**: `event_producers/config.py:11-36`

```python
class Settings(BaseSettings):
    service_name: str = "bloodbank"
    environment: str = "dev"

    # RabbitMQ
    rabbit_url: str = "amqp://guest:guest@rabbitmq:5672/"
    exchange_name: str = "bloodbank.events.v1"

    # Redis (correlation tracking)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    correlation_ttl_days: int = 30

    # HTTP server
    http_host: str = "0.0.0.0"
    http_port: int = 8682

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
```

**Purpose**: Centralized configuration using Pydantic Settings with environment variable loading.

## Dependencies

### Internal Dependencies

- `event_producers.events.base` → Core event envelope types
- `event_producers.events.envelope` → Envelope creation helpers
- `event_producers.events.core.*` → CQRS abstractions and command system
- `event_producers.events.registry` → Event type discovery and validation
- `event_producers.events.domains.*` → Domain-specific event payloads
- `event_producers.rabbit` → RabbitMQ publisher
- `event_producers.consumer` → FastStream consumer setup
- `event_producers.config` → Application settings
- `event_producers.correlation_tracker` → Redis correlation tracking

### External Dependencies

**Core Libraries**:
- `pydantic` (v2) - Schema validation and serialization
- `pydantic-settings` - Environment-based configuration
- `aio_pika` - Async RabbitMQ client
- `faststream[rabbit]` - Declarative event streaming framework
- `orjson` - Fast JSON serialization
- `redis` - Correlation tracking storage

**Supporting Libraries**:
- `asyncio` - Async/await infrastructure
- `uuid` - Event ID generation
- `datetime` - Timestamp management
- `logging` - Structured logging
- `typing` - Type hints

## Relationships

### Code Structure Diagram (Module Architecture)

```mermaid
---
title: Bloodbank Event Infrastructure - Module Structure
---
classDiagram
    namespace EventCore {
        class EventEnvelope~T~ {
            <<generic>>
            +UUID event_id
            +str event_type
            +datetime timestamp
            +str version
            +Source source
            +List~UUID~ correlation_ids
            +AgentContext? agent_context
            +T payload
        }

        class Source {
            +str host
            +TriggerType type
            +str? app
            +Dict? meta
        }

        class AgentContext {
            +AgentType type
            +str? name
            +str? system_prompt
            +str? instance_id
            +List~str~? mcp_servers
            +List~str~? file_references
            +List~str~? url_references
            +CodeState? code_state
            +Dict? meta
        }
    }

    namespace Infrastructure {
        class Publisher {
            +bool enable_correlation_tracking
            +CorrelationTracker? tracker
            +start() void
            +publish(routing_key, body, event_id, parent_event_ids) void
            +generate_event_id(event_type, **unique_fields) UUID
            +get_correlation_chain(event_id) List~UUID~
            +close() void
        }

        class Consumer {
            +str service_name
            +str queue_name
            +start(callback, routing_keys) void
            +close() void
        }

        class RabbitBroker {
            <<faststream>>
            +str url
            +subscriber(queue, exchange, routing_key)
        }
    }

    namespace CommandSystem {
        class Invokable~R~ {
            <<interface>>
            +execute(context, collector) R
            +rollback(context) void
        }

        class CommandManager {
            +Publisher publisher
            +EventRegistry registry
            +handle_envelope(envelope) void
            -_execute_command(command, envelope) void
        }

        class EventCollector {
            -List~EventEnvelope~ _events
            +add(event) void
            +collect() List~EventEnvelope~
            +count int
        }

        class CommandContext {
            +UUID correlation_id
            +str source_app
            +AgentContext? agent_context
            +datetime timestamp
        }
    }

    namespace Registry {
        class EventRegistry {
            +Dict~str, EventDomain~ domains
            +register(event_type, payload_class, domain_name) void
            +get_payload_type(event_type) Type~BaseModel~?
            +is_valid_event_type(event_type) bool
            +list_domains() List~str~
            +get_schema(event_type) Dict?
            +auto_discover_domains() void
        }

        class EventDomain {
            +str name
            +str module_name
            +Dict~str, Type~ payload_types
            +add_event_type(event_type, payload_class) void
            +get_payload_type(event_type) Type?
            +list_events() List~str~
        }
    }

    namespace DomainEvents {
        class FirefliesTranscriptReadyPayload {
            +str id
            +str title
            +datetime date
            +float duration
            +List~TranscriptSentence~ sentences
            +List~MeetingParticipant~ participants
            +FirefliesUser user
        }

        class AgentThreadPrompt {
            <<command>>
            +str provider
            +str? model
            +str prompt
            +List~str~ tags
            +execute(context, collector) AgentThreadResponse
        }

        class AgentThreadResponse {
            +str provider
            +str response
            +int? tokens_used
            +int? duration_ms
        }
    }

    namespace Utilities {
        class Settings {
            <<pydantic-settings>>
            +str service_name
            +str rabbit_url
            +str exchange_name
            +str redis_host
            +int redis_port
        }

        class EnvelopeFactory {
            <<module>>
            +create_envelope(event_type, payload, source) EventEnvelope
            +create_http_envelope(...) EventEnvelope
            +create_agent_envelope(...) EventEnvelope
            +create_scheduled_envelope(...) EventEnvelope
        }
    }

    EventEnvelope *-- Source : contains
    EventEnvelope *-- AgentContext : contains
    EventEnvelope ..> DomainEvents : payload T

    Publisher --> EventEnvelope : publishes
    Publisher ..> Settings : uses
    Consumer --> EventEnvelope : receives
    Consumer ..> Settings : uses
    RabbitBroker ..> DomainEvents : routes to handlers

    CommandManager --> Publisher : publishes side effects
    CommandManager --> EventRegistry : validates payloads
    CommandManager --> Invokable : executes
    CommandManager ..> EventCollector : uses

    Invokable --> CommandContext : receives
    Invokable --> EventCollector : produces events
    AgentThreadPrompt ..|> Invokable : implements

    EventRegistry o-- EventDomain : contains
    EventDomain ..> DomainEvents : registers

    EnvelopeFactory ..> EventEnvelope : creates
    EnvelopeFactory ..> Source : creates
    EnvelopeFactory ..> AgentContext : creates
```

### Event Flow Diagram (Data Pipeline)

```mermaid
---
title: Event Publishing and Consumption Flow
---
flowchart TB
    subgraph Producer["Event Producer (Any Service)"]
        A1[Create Payload]
        A2[create_envelope]
        A3[Publisher.publish]
    end

    subgraph RabbitMQ["RabbitMQ Exchange"]
        B1{{"bloodbank.events.v1"<br/>Topic Exchange}}
        B2["Queue: fireflies_queue<br/>Binding: fireflies.transcript.*"]
        B3["Queue: agent_queue<br/>Binding: agent.#"]
        B4["Queue: service_A_queue<br/>Binding: #"]
    end

    subgraph CorrelationTracking["Correlation Tracking (Optional)"]
        C1[(Redis)]
        C2[CorrelationTracker]
    end

    subgraph Consumer1["FastStream Consumer"]
        D1[@broker.subscriber]
        D2[Handler Function]
        D3[Process Payload]
    end

    subgraph Consumer2["CQRS Command Consumer"]
        E1[CommandManager]
        E2[Registry Lookup]
        E3[Command.execute]
        E4[EventCollector]
        E5[Publish Side Effects]
    end

    A1 -->|"FirefliesTranscriptReadyPayload"| A2
    A2 -->|"EventEnvelope[T]"| A3
    A3 -->|"routing_key=fireflies.transcript.ready"| B1

    A3 -.->|"track correlation"| C2
    C2 -.->|"parent-child links"| C1

    B1 -->|"route by pattern"| B2
    B1 -->|"route by pattern"| B3
    B1 -->|"route by pattern"| B4

    B2 -->|"JSON message"| D1
    D1 -->|"deserialize"| D2
    D2 -->|"process"| D3

    B3 -->|"JSON message"| E1
    E1 -->|"get payload class"| E2
    E2 -->|"hydrate & execute"| E3
    E3 -->|"collect side effects"| E4
    E4 -->|"publish events"| E5
    E5 -.->|"new events"| B1

    style B1 fill:#f9a,stroke:#333,stroke-width:4px
    style C1 fill:#aaf,stroke:#333,stroke-width:2px
    style D3 fill:#afa,stroke:#333,stroke-width:2px
    style E4 fill:#ffa,stroke:#333,stroke-width:2px
```

### Routing Key Patterns

**Exchange**: `bloodbank.events.v1` (TOPIC)

**Pattern Examples**:
- `fireflies.transcript.ready` - Specific event
- `fireflies.transcript.*` - All transcript events
- `agent.thread.#` - All agent thread events (including nested)
- `#` - All events (wildcard consumer)

**Routing Rules**:
- `.` separates words in routing key
- `*` matches exactly one word
- `#` matches zero or more words

## Queue Naming Convention

**Pattern**: `{exchange_name}.{service_name}`

**Example**: `bloodbank.events.v1.rag_consumer`

**Benefits**:
- Clear ownership (which service owns which queue)
- Durable queues survive broker restarts
- Multiple services can subscribe to same routing keys with different queues

## Correlation Tracking

### Purpose
Track event causation chains for debugging, auditing, and distributed tracing.

### Storage
Redis with key pattern: `event:correlation:{event_id}`

### Data Structure
```python
{
    "parents": ["uuid1", "uuid2"],      # Direct parents
    "children": ["uuid3", "uuid4"],     # Direct children
    "metadata": {
        "event_type": "fireflies.transcript.processed",
        "created_at": "2024-01-27T10:00:00Z"
    }
}
```

### Queries
- **Ancestors**: Full chain of parent events leading to this event
- **Descendants**: All events triggered by this event (directly or indirectly)
- **Debug Dump**: Complete correlation graph for an event

### TTL
30 days (configurable via `correlation_ttl_days`)

## Design Patterns

### 1. Generic Event Envelope Pattern
All events share common structure (EventEnvelope) with typed payloads (Generic[T]).

**Benefits**:
- Consistent metadata across all events
- Type-safe payload access
- Easy correlation tracking
- Centralized validation

### 2. CQRS (Command Query Responsibility Segregation)
- **Commands**: Implement `Invokable[R]` with `execute()` method
- **Events**: Plain `BaseEvent` (facts, no behavior)
- **CommandManager**: Orchestrates command execution and side effects

**Benefits**:
- Clear separation of actions vs facts
- Testable business logic
- Automatic side effect publishing
- Rollback support

### 3. Registry Pattern
EventRegistry auto-discovers event types and maps routing keys to Pydantic classes.

**Benefits**:
- Runtime type validation
- JSON schema generation
- API documentation
- Type-safe deserialization

### 4. Factory Pattern
Multiple envelope creation functions for common patterns (HTTP, agent, scheduled).

**Benefits**:
- Consistent envelope creation
- Reduces boilerplate
- Type-safe defaults
- Backward compatibility

### 5. Correlation Tracking Pattern
Redis-backed parent-child event relationships with deterministic event IDs.

**Benefits**:
- Idempotency (same inputs → same event ID)
- Distributed tracing
- Audit trails
- Debugging support

## Code Organization

### Module Structure

```
event_producers/
├── events/
│   ├── base.py              # EventEnvelope, Source, AgentContext
│   ├── envelope.py          # Envelope factory functions
│   ├── registry.py          # EventRegistry, EventDomain
│   ├── types.py             # Enum types and constants
│   ├── utils.py             # Helper utilities
│   ├── core/
│   │   ├── abstraction.py   # Invokable, BaseCommand, EventCollector
│   │   ├── consumer.py      # Generic Consumer class
│   │   └── manager.py       # CommandManager
│   └── domains/
│       ├── fireflies.py     # Fireflies event payloads
│       ├── github.py        # GitHub event payloads
│       ├── llm.py           # LLM event payloads
│       ├── artifact.py      # Artifact event payloads
│       ├── theboard.py      # TheBoard event payloads
│       └── agent/
│           ├── thread.py    # Agent thread event payloads
│           └── feedback.py  # Agent feedback event payloads
├── rabbit.py                # Publisher class
├── consumer.py              # FastStream broker and app
├── config.py                # Settings (Pydantic)
├── correlation_tracker.py   # Redis correlation tracking
├── http.py                  # HTTP webhook receiver
├── cli.py                   # CLI commands
└── schema_validator.py      # Schema validation utilities
```

### Domain Module Pattern

Each domain module (`events/domains/*.py`) exports:

```python
# 1. Pydantic payload models
class FirefliesTranscriptReadyPayload(BaseModel):
    ...

# 2. Routing key mapping
ROUTING_KEYS = {
    "FirefliesTranscriptReadyPayload": "fireflies.transcript.ready",
    "FirefliesTranscriptUploadPayload": "fireflies.transcript.upload",
}
```

EventRegistry auto-discovers these modules at startup.

## Usage Examples

### Publishing an Event

```python
from event_producers.rabbit import Publisher
from event_producers.events.envelope import create_http_envelope
from event_producers.events.domains.fireflies import FirefliesTranscriptReadyPayload

# Create payload
payload = FirefliesTranscriptReadyPayload(
    id="meeting_123",
    title="Team Standup",
    date=datetime.now(timezone.utc),
    duration=15.5,
    transcript_url="https://app.fireflies.ai/...",
    sentences=[...],
    participants=[...],
    user=FirefliesUser(...),
    host_email="host@example.com",
    organizer_email="organizer@example.com",
    privacy="private"
)

# Create envelope
envelope = create_http_envelope(
    event_type="fireflies.transcript.ready",
    payload=payload,
    client_host="127.0.0.1",
    app_name="fireflies-webhook"
)

# Publish
publisher = Publisher(enable_correlation_tracking=True)
await publisher.start()
await publisher.publish(
    routing_key="fireflies.transcript.ready",
    body=envelope.model_dump(mode="json"),
    parent_event_ids=[upload_event_id]  # Link to upload event
)
```

### Consuming Events (FastStream)

```python
from event_producers.consumer import broker
from event_producers.events.domains.fireflies import FirefliesTranscriptReadyPayload

@broker.subscriber(
    "rag_consumer_queue",
    exchange="bloodbank.events.v1",
    routing_key="fireflies.transcript.ready"
)
async def handle_transcript_ready(msg: FirefliesTranscriptReadyPayload):
    """Process transcript and ingest into RAG system."""
    print(f"Processing transcript: {msg.title}")

    # Ingest into vector store
    await ingest_transcript(msg.sentences)

    # Publish processed event
    processed_payload = FirefliesTranscriptProcessedPayload(
        transcript_id=msg.id,
        rag_document_id=doc_id,
        title=msg.title,
        ingestion_timestamp=datetime.now(timezone.utc),
        sentence_count=len(msg.sentences),
        speaker_count=len(msg.speakers),
        duration_minutes=msg.duration,
        vector_store="chroma",
        chunk_count=num_chunks
    )

    # Create and publish envelope
    envelope = create_envelope(
        event_type="fireflies.transcript.processed",
        payload=processed_payload,
        source="rag_consumer/localhost",
        correlation_ids=[msg.event_id]  # Link back to ready event
    )

    await publisher.publish(
        routing_key="fireflies.transcript.processed",
        body=envelope.model_dump(mode="json"),
        parent_event_ids=[envelope.correlation_ids[0]]
    )
```

### Executing Commands (CQRS)

```python
from event_producers.events.domains.agent.thread import AgentThreadPrompt
from event_producers.events.core.manager import CommandManager
from event_producers.rabbit import Publisher

# Create command payload
command = AgentThreadPrompt(
    provider="anthropic",
    model="claude-sonnet-4",
    prompt="Analyze this codebase",
    project="bloodbank",
    tags=["analysis", "code-review"]
)

# Wrap in envelope
envelope = create_agent_envelope(
    event_type="agent.thread.prompt",
    payload=command,
    agent_type="claude-code",
    agent_name="Code Analyzer"
)

# Publish command
await publisher.publish(
    routing_key="agent.thread.prompt",
    body=envelope.model_dump(mode="json")
)

# Command consumer (separate service)
@broker.subscriber("command_processor_queue", routing_key="agent.thread.#")
async def process_command(envelope_dict: dict):
    manager = CommandManager(publisher)
    envelope = EventEnvelope.model_validate(envelope_dict)
    await manager.handle_envelope(envelope)
    # CommandManager will:
    # 1. Hydrate AgentThreadPrompt from registry
    # 2. Execute command.execute()
    # 3. Collect side effects (AgentThreadResponse)
    # 4. Publish side effect events
```

## Testing Considerations

### Unit Testing

```python
def test_envelope_creation():
    payload = FirefliesTranscriptUploadPayload(
        media_file="/path/to/file.mp4",
        media_duration_seconds=900,
        media_type="video/mp4"
    )

    envelope = create_http_envelope(
        event_type="fireflies.transcript.upload",
        payload=payload,
        client_host="127.0.0.1"
    )

    assert envelope.event_type == "fireflies.transcript.upload"
    assert envelope.source.type == TriggerType.MANUAL
    assert isinstance(envelope.event_id, UUID)
```

### Integration Testing

```python
async def test_command_execution():
    # Setup
    collector = EventCollector()
    context = CommandContext(
        correlation_id=uuid4(),
        source_app="test",
        agent_context=None,
        timestamp=datetime.now(timezone.utc)
    )

    # Execute command
    command = AgentThreadPrompt(
        provider="anthropic",
        model="claude-sonnet-4",
        prompt="Test prompt"
    )

    result = await command.execute(context, collector)

    # Verify side effects
    events = collector.collect()
    assert len(events) == 1
    assert events[0].event_type == "agent.thread.response"
```

## Performance Characteristics

### Publisher
- **Connection**: Persistent connection with automatic reconnection
- **Serialization**: orjson (faster than stdlib json)
- **Delivery**: Publisher confirms enabled (reliable)
- **Correlation Tracking**: 1ms timeout per publish (non-blocking)

### Consumer
- **QoS**: prefetch_count=10 (process up to 10 messages concurrently)
- **Acknowledgment**: Auto-ack on success, nack on failure
- **Deserialization**: Pydantic validation on receive

### Registry
- **Discovery**: One-time at startup (auto_discover_domains)
- **Lookup**: O(1) hash map access per event type

## Security Considerations

1. **Credential Management**: RabbitMQ and Redis credentials via environment variables
2. **Input Validation**: Pydantic models validate all incoming data
3. **Error Handling**: Graceful degradation (correlation tracking optional)
4. **Logging**: Sensitive data redacted in logs (URL credentials masked)

## Future Enhancements

1. **Schema Versioning**: Support for breaking payload changes via event type versioning (e.g., `.v2`)
2. **Dead Letter Queues**: Automatic retry logic with exponential backoff
3. **Event Replay**: Redis persistence for event sourcing and replay
4. **Metrics**: Prometheus metrics for event throughput, latency, error rates
5. **Distributed Tracing**: OpenTelemetry integration for span tracking

## Notes

- **Thread Safety**: All async operations use `asyncio.Lock` for connection management
- **Idempotency**: Use `generate_event_id()` for deterministic event IDs
- **Backward Compatibility**: `envelope_for()` deprecated but still supported
- **FastStream vs aio-pika**: FastStream for declarative subscribers, aio-pika for low-level control
- **Correlation vs Causation**: `correlation_ids` tracks parent events; Redis stores full graph
- **Command Execution**: Commands can be sync or async (CommandManager handles both)

---

**Last Updated**: 2026-01-29
**Code Version**: Based on commit `2d6edae` (trunk-main branch)
**Documentation Standard**: C4 Model Code Level
