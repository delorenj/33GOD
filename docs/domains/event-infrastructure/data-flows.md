# Event Infrastructure Domain - Data Flows

## Overview

This document visualizes how data flows through the Event Infrastructure domain, showing message routing patterns, schema validation flows, and event processing pipelines.

## 1. Core Event Publishing Flow

Shows how events are published from services through Bloodbank to RabbitMQ and distributed to subscribers.

```mermaid
flowchart TB
    subgraph Producers["Event Producers"]
        Service[Microservice]
        Webhook[External Webhook<br/>Fireflies, GitHub]
        Agent[AI Agent Service]
    end

    subgraph Validation["Schema Validation Layer"]
        EventData[Event Payload<br/>JSON Data]
        Schema[Holyfields Schema<br/>Pydantic Model]
        Validate{Valid Schema?}
    end

    subgraph Bloodbank["Bloodbank Publisher API"]
        Envelope[Event Envelope<br/>+ Metadata]
        CorrelationID[Add Correlation ID]
        Publisher[RabbitMQ Publisher]
    end

    subgraph RabbitMQ["RabbitMQ Broker"]
        Exchange[Topic Exchange<br/>events]
        Router{Routing Key<br/>Pattern Match}
    end

    subgraph Queues["Consumer Queues"]
        Q1[transcript.queue]
        Q2[meeting.queue]
        Q3[notification.queue]
        DLQ[Dead Letter Queue<br/>*.failed]
    end

    subgraph Consumers["Event Consumers"]
        C1[Transcript Processor]
        C2[Meeting Orchestrator]
        C3[Notification Service]
    end

    Service --> EventData
    Webhook --> EventData
    Agent --> EventData

    EventData --> Schema
    Schema --> Validate
    Validate -->|Yes| Envelope
    Validate -->|No| Error[Validation Error<br/>400 Response]

    Envelope --> CorrelationID
    CorrelationID --> Publisher
    Publisher --> Exchange

    Exchange --> Router
    Router -->|fireflies.*| Q1
    Router -->|theboard.*| Q2
    Router -->|notification.*| Q3

    Q1 --> C1
    Q2 --> C2
    Q3 --> C3

    C1 -.->|Process Failed| DLQ
    C2 -.->|Process Failed| DLQ
    C3 -.->|Process Failed| DLQ

    style Validate decision
    style Router decision
    style DLQ fill:#f96
    style Error fill:#f96
```

## 2. Webhook Integration Flow

Detailed flow showing how external webhooks (Fireflies) are transformed and routed to internal event bus.

```mermaid
flowchart LR
    subgraph External["External Service"]
        FF[Fireflies.ai<br/>Transcript Ready]
    end

    subgraph n8n["n8n Workflow Orchestrator"]
        WH[Webhook Endpoint<br/>/webhooks/fireflies]
        Fetch[Fetch Full Transcript<br/>API Call]
        Transform[Transform Payload<br/>Map to Schema]
        Enrich[Add Metadata<br/>timestamp, workflow_id]
        Publish[Publish to Bloodbank<br/>POST /events/transcript]
    end

    subgraph Bloodbank["Bloodbank"]
        Validate[Schema Validation<br/>Pydantic]
        Envelope[Create Envelope]
        ToRMQ[To RabbitMQ]
    end

    subgraph RabbitMQ["RabbitMQ"]
        Exchange[events exchange]
        Routes{Route by Key}
        TranscriptQ[transcript.queue]
        RAGQ[rag.ingestion.queue]
    end

    subgraph Subscribers["Subscribers"]
        SaveMD[Save to Obsidian<br/>Markdown]
        RAG[RAG Ingestion<br/>Vector DB]
        Notify[Notification Service]
    end

    FF -->|HTTPS POST| WH
    WH --> Fetch
    Fetch --> Transform
    Transform --> Enrich
    Enrich --> Publish

    Publish --> Validate
    Validate --> Envelope
    Envelope --> ToRMQ

    ToRMQ --> Exchange
    Exchange --> Routes
    Routes -->|fireflies.transcript.ready| TranscriptQ
    Routes -->|fireflies.transcript.ready| RAGQ

    TranscriptQ --> SaveMD
    RAGQ --> RAG
    TranscriptQ --> Notify

    style Validate fill:#9f6
    style Routes decision
```

## 3. Schema Generation and Distribution Flow

Shows the build-time flow of schema validation and code generation from Holyfields.

```mermaid
flowchart TB
    subgraph Development["Development Time"]
        Dev[Developer]
        Schema[JSON Schema<br/>theboard/events/meeting_created.json]
        Git[Git Repository]
    end

    subgraph CI["CI/CD Pipeline"]
        CI_Start[GitHub Action<br/>Triggered]
        Validate[Validate Schemas<br/>mise run validate:schemas]
        Generate[Generate Code<br/>mise run generate:all]
        Test[Contract Tests<br/>mise run test:all]
        CI_Pass{Tests Pass?}
    end

    subgraph Artifacts["Generated Artifacts"]
        PyModels[Python Pydantic Models<br/>generated/python/]
        TSModels[TypeScript Zod Schemas<br/>generated/typescript/]
    end

    subgraph Services["Consumer Services"]
        PyService[Python Service<br/>Import Pydantic]
        TSService[TypeScript Service<br/>Import Zod]
        RuntimeVal[Runtime Validation]
    end

    Dev --> Schema
    Schema --> Git
    Git --> CI_Start

    CI_Start --> Validate
    Validate --> Generate
    Generate --> PyModels
    Generate --> TSModels

    PyModels --> Test
    TSModels --> Test
    Test --> CI_Pass

    CI_Pass -->|Yes| Git
    CI_Pass -->|No| FailBuild[Build Fails<br/>Schema Error]

    Git --> PyService
    Git --> TSService

    PyService --> RuntimeVal
    TSService --> RuntimeVal

    RuntimeVal --> SafeExecution[Type-Safe Execution]

    style CI_Pass decision
    style FailBuild fill:#f96
    style SafeExecution fill:#9f6
```

## 4. Dead Letter Queue Processing Flow

Shows how failed messages are handled and requeued.

```mermaid
flowchart TB
    subgraph Consumption["Message Consumption"]
        Queue[Primary Queue<br/>transcripts.queue]
        Consumer[Event Consumer]
        Process{Process<br/>Success?}
    end

    subgraph Retry["Retry Logic"]
        Retry1[Retry 1<br/>5s delay]
        Retry2[Retry 2<br/>10s delay]
        Retry3[Retry 3<br/>30s delay]
        MaxRetries{Max Retries<br/>Reached?}
    end

    subgraph DLQ["Dead Letter Queue"]
        DLQQueue[transcripts.failed<br/>7-day TTL]
        Monitor[Ops Monitoring<br/>Alert]
    end

    subgraph Resolution["Manual Resolution"]
        Ops[Operations/SRE]
        Investigate[Investigate Failure<br/>Read payload + headers]
        Fix[Fix Root Cause<br/>Deploy fix]
        Requeue[Requeue Messages<br/>RabbitMQ UI]
    end

    subgraph Success["Success Path"]
        ACK[ACK Message]
        Remove[Remove from Queue]
    end

    Queue --> Consumer
    Consumer --> Process

    Process -->|Success| ACK
    ACK --> Remove

    Process -->|Fail| Retry1
    Retry1 -->|Fail| Retry2
    Retry2 -->|Fail| Retry3
    Retry3 --> MaxRetries

    MaxRetries -->|Yes| DLQQueue
    MaxRetries -->|No| Queue

    DLQQueue --> Monitor
    Monitor --> Ops
    Ops --> Investigate
    Investigate --> Fix
    Fix --> Requeue
    Requeue --> Queue

    style Process decision
    style MaxRetries decision
    style Remove fill:#9f6
    style DLQQueue fill:#f96
```

## 5. Event Correlation and Tracing Flow

Shows how correlation IDs propagate through distributed event chains.

```mermaid
flowchart LR
    subgraph Request["Initial Request"]
        User[User Action]
        GenID[Generate<br/>Correlation ID<br/>uuid-123]
    end

    subgraph Event1["Event 1: Meeting Created"]
        E1Publish[theboard.meeting.created<br/>correlation_id: uuid-123]
        E1Queue[meeting.queue]
        E1Process[Meeting Processor]
    end

    subgraph Event2["Event 2: Notification Sent"]
        E2Publish[notification.sent<br/>correlation_id: uuid-123<br/>parent: meeting.created]
        E2Queue[notification.queue]
        E2Process[Notification Service]
    end

    subgraph Event3["Event 3: Email Delivered"]
        E3Publish[notification.email.delivered<br/>correlation_id: uuid-123<br/>parent: notification.sent]
        E3Queue[email.queue]
        E3Process[Email Service]
    end

    subgraph Tracking["Correlation Tracking"]
        Redis[Redis Cache<br/>24h TTL]
        Chain[Correlation Chain<br/>uuid-123 → [e1, e2, e3]]
        Query[GET /correlation/uuid-123]
    end

    User --> GenID
    GenID --> E1Publish
    E1Publish --> E1Queue
    E1Queue --> E1Process

    E1Process --> E2Publish
    E2Publish --> E2Queue
    E2Queue --> E2Process

    E2Process --> E3Publish
    E3Publish --> E3Queue
    E3Queue --> E3Process

    E1Publish -.->|Store| Redis
    E2Publish -.->|Store| Redis
    E3Publish -.->|Store| Redis

    Redis --> Chain
    Chain --> Query
    Query --> DebugTool[Distributed Tracing<br/>Debug Tool]

    style Chain fill:#9cf
    style DebugTool fill:#9f6
```

## 6. Voice Assistant Event Flow (TalkyTonny)

Shows the real-time voice transcription and event publishing pipeline.

```mermaid
flowchart TB
    subgraph Desktop["Desktop Application"]
        Mic[Microphone<br/>Audio Input]
        TonnyTray[TonnyTray App<br/>Tauri/Rust]
    end

    subgraph Server["WhisperLiveKit Server"]
        WS[WebSocket Server<br/>ws://localhost:8888/asr]
        AudioBuffer[Audio Buffer<br/>16kHz PCM]
        Whisper[Whisper AI<br/>faster-whisper]
        Transcribe[Transcription<br/>Text + Confidence]
    end

    subgraph Publishing["Event Publishing"]
        EventPayload[Create Event<br/>talkytonny.transcription.completed]
        Bloodbank[Bloodbank API<br/>POST /events/transcription]
        RMQ[RabbitMQ<br/>events exchange]
    end

    subgraph Workflows["Workflow Orchestration"]
        N8N[n8n Workflow<br/>Webhook Trigger]
        Process[Process Command<br/>Intent Recognition]
        Execute[Execute Workflow<br/>API Calls]
    end

    subgraph Response["Response Generation"]
        LLM[LLM Processing<br/>Claude/GPT]
        TTS[ElevenLabs TTS<br/>Generate Audio]
        Playback[Audio Playback<br/>Desktop Speaker]
    end

    Mic --> TonnyTray
    TonnyTray -->|Binary Audio| WS
    WS --> AudioBuffer
    AudioBuffer --> Whisper
    Whisper --> Transcribe

    Transcribe --> EventPayload
    EventPayload --> Bloodbank
    Bloodbank --> RMQ

    Transcribe --> N8N
    N8N --> Process
    Process --> Execute

    Execute --> LLM
    LLM --> TTS
    TTS --> Playback

    style Whisper fill:#9cf
    style LLM fill:#9cf
    style TTS fill:#9cf
```

## Data Flow Patterns Summary

### 1. **Publish-Subscribe Pattern**
- **Use Case**: Domain events requiring multiple independent consumers
- **Example**: `fireflies.transcript.ready` → [processor, RAG, notifier]
- **Characteristics**: Decoupled, scalable, asynchronous

### 2. **Request-Reply Pattern** (Async)
- **Use Case**: Command events expecting acknowledgment
- **Example**: `agent.task.assign` → `agent.task.accepted`
- **Characteristics**: Correlation IDs, reply queues

### 3. **Event Sourcing Pattern**
- **Use Case**: Audit trail and event replay
- **Example**: All events persisted to PostgreSQL event store
- **Characteristics**: Immutable log, queryable history

### 4. **Dead Letter Queue Pattern**
- **Use Case**: Failed message handling
- **Example**: Retry exhaustion → `transcripts.failed` queue
- **Characteristics**: TTL, manual requeue, alerting

### 5. **Content-Based Routing**
- **Use Case**: Route by routing key patterns
- **Example**: `theboard.meeting.*` → meeting queue
- **Characteristics**: Topic exchange, wildcard patterns

## Message Format Standards

### Event Envelope Structure
```json
{
  "event_id": "uuid-v4",
  "event_type": "theboard.meeting.created",
  "timestamp": "2026-01-29T10:30:00Z",
  "correlation_id": "uuid-v4",
  "source": "theboard-service",
  "payload": {
    // Holyfields-validated event data
  },
  "metadata": {
    "version": "1.0",
    "schema_version": "2.0.0"
  }
}
```

### Routing Key Convention
```
<domain>.<entity>.<action>
│        │        └─ action: created, updated, deleted, ready
│        └─ entity: meeting, transcript, agent
└─ domain: theboard, fireflies, talkytonny, flume
```

## Performance Metrics

| Flow | Latency Target | Throughput |
|------|---------------|------------|
| Event Publishing | < 50ms p99 | 10k+ msg/s |
| Schema Validation | < 10ms | In-memory |
| Webhook → Event | < 2s | Rate limited |
| Voice Transcription → Event | < 500ms | Real-time |
| DLQ Requeue | Manual | N/A |

## Related Documentation

- [Dependency Graph](./dependencies.md) - Component dependencies and integration points
- [Sequence Diagrams](./sequences.md) - Interaction patterns and message flows
- [C4 Context](./c4-context.md) - System context and personas
- [C4 Container](./c4-container.md) - Container deployment architecture

---

**Version**: 1.0.0
**Last Updated**: 2026-01-29
**Maintained By**: 33GOD Architecture Team
