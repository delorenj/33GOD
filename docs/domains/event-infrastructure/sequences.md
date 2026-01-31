# Event Infrastructure Domain - Sequence Diagrams

## Overview

This document provides detailed sequence diagrams showing key interaction patterns and message flows in the Event Infrastructure domain.

## 1. Event Publishing Sequence

Standard sequence for publishing an event from a service through Bloodbank to consumers.

```mermaid
sequenceDiagram
    participant Service as Microservice
    participant BB as Bloodbank API
    participant Schema as Holyfields Schema
    participant Redis as Redis Cache
    participant RMQ as RabbitMQ
    participant Q as Consumer Queue
    participant Consumer as Event Consumer

    Service->>Service: Create event payload
    Service->>BB: POST /events/{type}<br/>{payload}

    BB->>Schema: Validate against schema
    Schema-->>BB: Validation result

    alt Schema Invalid
        BB-->>Service: 400 Bad Request<br/>{validation_errors}
    else Schema Valid
        BB->>BB: Generate correlation_id
        BB->>BB: Create EventEnvelope

        opt Correlation Tracking
            BB->>Redis: SET correlation:{id}<br/>{metadata}
            Redis-->>BB: OK
        end

        BB->>RMQ: Publish to exchange<br/>routing_key: domain.entity.action
        RMQ-->>BB: Publisher Confirm
        BB-->>Service: 202 Accepted<br/>{event_id}

        RMQ->>RMQ: Route by pattern
        RMQ->>Q: Deliver message
        Q->>Consumer: Consume message

        Consumer->>Consumer: Process event
        Consumer->>Schema: Validate payload

        alt Processing Success
            Consumer->>Q: ACK message
            Q->>RMQ: Remove from queue
        else Processing Failure
            Consumer->>Q: NACK message
            Q->>Q: Requeue with delay
        end
    end
```

## 2. Webhook Integration Sequence (Fireflies)

Detailed sequence showing how external webhooks are transformed and published.

```mermaid
sequenceDiagram
    participant FF as Fireflies.ai
    participant N8N as n8n Workflow
    participant FFAPI as Fireflies API
    participant BB as Bloodbank API
    participant RMQ as RabbitMQ
    participant Proc as Transcript Processor
    participant Vault as Obsidian Vault
    participant RAG as RAG Service

    FF->>N8N: POST /webhooks/fireflies<br/>{meeting_id}
    N8N->>N8N: Parse webhook payload

    N8N->>FFAPI: GET /transcripts/{id}<br/>Authorization: Bearer {token}
    FFAPI-->>N8N: 200 OK<br/>{full_transcript_data}

    N8N->>N8N: Transform to schema format
    N8N->>N8N: Add metadata<br/>(timestamp, workflow_id)

    N8N->>BB: POST /events/transcript<br/>{transformed_payload}
    BB->>BB: Validate schema
    BB->>RMQ: Publish event<br/>fireflies.transcript.ready
    RMQ-->>BB: Confirm
    BB-->>N8N: 202 Accepted

    RMQ->>Proc: Deliver to transcript queue
    RMQ->>RAG: Deliver to RAG queue

    par Parallel Processing
        Proc->>Proc: Convert to Markdown
        Proc->>Vault: Save transcript.md
        Vault-->>Proc: File saved
        Proc->>RMQ: Publish artifact.created
    and
        RAG->>RAG: Generate embeddings
        RAG->>RAG: Store in vector DB
    end
```

## 3. Dead Letter Queue Handling Sequence

Shows the retry logic and DLQ routing flow.

```mermaid
sequenceDiagram
    participant Q as Primary Queue
    participant C as Consumer
    participant Retry as Retry Logic
    participant DLQ as Dead Letter Queue
    participant Ops as Ops Engineer
    participant UI as RabbitMQ UI

    Q->>C: Deliver message (attempt 1)
    C->>C: Process event
    C--xC: Processing fails

    C->>Q: NACK (requeue=true)
    Q->>Q: Set x-retry-count: 1
    Q->>Q: Delay 5 seconds

    Q->>C: Deliver message (attempt 2)
    C->>C: Process event
    C--xC: Processing fails again

    C->>Q: NACK (requeue=true)
    Q->>Q: Set x-retry-count: 2
    Q->>Q: Delay 10 seconds

    Q->>C: Deliver message (attempt 3)
    C->>C: Process event
    C--xC: Processing fails again

    C->>Q: NACK (requeue=true)
    Q->>Q: Check x-retry-count >= 3

    Q->>DLQ: Route to DLQ<br/>x-death headers attached
    DLQ->>DLQ: Store for 7 days

    DLQ->>Ops: Alert: DLQ message count > 0
    Ops->>UI: Login to RabbitMQ UI
    UI->>DLQ: Get messages
    DLQ-->>UI: Show message + headers

    Ops->>Ops: Investigate failure<br/>(read x-death reason)
    Ops->>Ops: Deploy fix

    Ops->>UI: Click "Requeue Messages"
    UI->>Q: Move messages to primary queue
    Q->>C: Redeliver message
    C->>C: Process successfully
    C->>Q: ACK message
    Q->>Q: Remove from queue
```

## 4. Voice Transcription Real-Time Sequence

Shows the real-time audio streaming and event publishing flow for TalkyTonny.

```mermaid
sequenceDiagram
    participant Mic as Microphone
    participant Tray as TonnyTray App
    participant WS as WebSocket Server
    participant Whisper as Whisper AI
    participant BB as Bloodbank
    participant RMQ as RabbitMQ
    participant N8N as n8n Workflow
    participant LLM as Claude API
    participant TTS as ElevenLabs

    Mic->>Tray: Capture audio chunk
    Tray->>Tray: Buffer 1 second PCM

    loop Real-time Streaming
        Tray->>WS: Send binary audio<br/>ws://localhost:8888/asr
        WS->>WS: Append to buffer
        WS->>Whisper: Transcribe chunk

        alt Partial Result
            Whisper-->>WS: {text, is_final: false}
            WS-->>Tray: Display partial
        else Final Result
            Whisper-->>WS: {text, is_final: true}
            WS-->>Tray: Display final

            par Event Publishing
                WS->>BB: POST /events/transcription
                BB->>RMQ: Publish event
            and Workflow Trigger
                WS->>N8N: POST /webhook/transcription
            end
        end
    end

    N8N->>N8N: Parse command intent
    N8N->>LLM: Process with Claude
    LLM-->>N8N: Generated response
    N8N->>TTS: POST /v1/text-to-speech
    TTS-->>N8N: Audio stream
    N8N->>Tray: Return audio URL
    Tray->>Tray: Play audio response
```

## 5. Schema Validation and Code Generation Sequence

Build-time sequence for schema processing and artifact generation.

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Git as Git Repository
    participant CI as GitHub Actions
    participant Validate as Schema Validator
    participant GenPy as Python Generator
    participant GenTS as TypeScript Generator
    participant Tests as Contract Tests
    participant Artifact as Build Artifacts

    Dev->>Dev: Create JSON Schema<br/>theboard/events/meeting_created.json
    Dev->>Git: git commit & push

    Git->>CI: Trigger workflow<br/>on push to main

    CI->>Validate: mise run validate:schemas
    Validate->>Validate: Load all .json files

    loop Each Schema
        Validate->>Validate: Validate against Draft 2020-12
        alt Schema Invalid
            Validate-->>CI: Validation error
            CI-->>Dev: Build failed ❌
        end
    end

    Validate-->>CI: All schemas valid ✓

    CI->>GenPy: mise run generate:python
    GenPy->>GenPy: datamodel-codegen<br/>--input schemas/<br/>--output generated/python/
    GenPy-->>CI: Pydantic models generated

    CI->>GenTS: mise run generate:typescript
    GenTS->>GenTS: json-schema-to-zod<br/>--input schemas/<br/>--output generated/typescript/
    GenTS-->>CI: Zod schemas generated

    CI->>Tests: mise run test:all

    par Contract Tests
        Tests->>Tests: Test Python import
        Tests->>Tests: Test TypeScript import
        Tests->>Tests: Validate round-trip
    end

    alt Tests Pass
        Tests-->>CI: All tests passed ✓
        CI->>Artifact: Commit generated files
        Artifact->>Git: Push to repository
        Git-->>Dev: Build success ✅
    else Tests Fail
        Tests-->>CI: Contract violation
        CI-->>Dev: Build failed ❌
    end
```

## 6. Correlation Tracking Sequence

Shows how correlation IDs propagate through distributed workflows.

```mermaid
sequenceDiagram
    participant User as User
    participant BoardUI as TheBoard UI
    participant BoardAPI as TheBoard API
    participant BB as Bloodbank
    participant Redis as Redis
    participant Queue1 as meeting.queue
    participant MeetingSvc as Meeting Service
    participant Queue2 as notification.queue
    participant NotifySvc as Notification Service
    participant Query as Correlation Query

    User->>BoardUI: Create meeting
    BoardUI->>BoardAPI: POST /meetings

    BoardAPI->>BoardAPI: Generate correlation_id<br/>uuid-abc123
    BoardAPI->>BB: Publish meeting.created<br/>correlation_id: uuid-abc123

    BB->>Redis: SET correlation:uuid-abc123<br/>{parent: null, events: []}
    BB->>RMQ: Publish to exchange

    RMQ->>Queue1: Route to meeting.queue
    Queue1->>MeetingSvc: Deliver event

    MeetingSvc->>MeetingSvc: Process meeting creation
    MeetingSvc->>BB: Publish notification.requested<br/>correlation_id: uuid-abc123<br/>parent: meeting.created

    BB->>Redis: APPEND correlation:uuid-abc123<br/>{events: [notification.requested]}
    BB->>RMQ: Publish to exchange

    RMQ->>Queue2: Route to notification.queue
    Queue2->>NotifySvc: Deliver event

    NotifySvc->>NotifySvc: Send email
    NotifySvc->>BB: Publish email.delivered<br/>correlation_id: uuid-abc123<br/>parent: notification.requested

    BB->>Redis: APPEND correlation:uuid-abc123<br/>{events: [email.delivered]}

    User->>Query: GET /correlation/uuid-abc123
    Query->>Redis: GET correlation:uuid-abc123
    Redis-->>Query: Full event chain
    Query-->>User: [{meeting.created}, {notification.requested}, {email.delivered}]
```

## 7. Multi-Consumer Event Distribution Sequence

Shows how a single event is distributed to multiple consumers in parallel.

```mermaid
sequenceDiagram
    participant FF as Fireflies
    participant N8N as n8n
    participant BB as Bloodbank
    participant RMQ as RabbitMQ Exchange
    participant Q1 as transcript.queue
    participant Q2 as rag.queue
    participant Q3 as notification.queue
    participant C1 as Transcript Processor
    participant C2 as RAG Service
    participant C3 as Notification Service
    participant Vault as Obsidian
    participant VecDB as Vector DB
    participant Email as Email Service

    FF->>N8N: Transcript ready webhook
    N8N->>BB: Publish transcript.ready
    BB->>RMQ: Publish to exchange<br/>routing_key: fireflies.transcript.ready

    par Fanout to Multiple Queues
        RMQ->>Q1: Bind pattern: fireflies.transcript.#
        RMQ->>Q2: Bind pattern: fireflies.transcript.#
        RMQ->>Q3: Bind pattern: fireflies.#
    end

    par Parallel Consumption
        Q1->>C1: Deliver message
        C1->>C1: Convert to Markdown
        C1->>Vault: Save file
        C1->>Q1: ACK
    and
        Q2->>C2: Deliver message (same event)
        C2->>C2: Generate embeddings
        C2->>VecDB: Store vectors
        C2->>Q2: ACK
    and
        Q3->>C3: Deliver message (same event)
        C3->>C3: Format notification
        C3->>Email: Send email
        C3->>Q3: ACK
    end

    Note over C1,C3: All consumers process independently<br/>No coordination required
```

## 8. Event Store Persistence Sequence

Shows how all events are persisted to PostgreSQL for event sourcing.

```mermaid
sequenceDiagram
    participant Pub as Event Publisher
    participant RMQ as RabbitMQ
    participant Wildcard as event_store_queue<br/>(binding: #)
    participant Store as Event Store Manager
    participant PG as PostgreSQL
    participant Query as Query API

    Pub->>RMQ: Publish any event<br/>routing_key: theboard.meeting.created

    RMQ->>RMQ: Route to all matching queues
    RMQ->>Wildcard: Deliver to event store<br/>(matches all events with #)

    Wildcard->>Store: Consume event
    Store->>Store: Parse EventEnvelope

    Store->>PG: BEGIN TRANSACTION
    Store->>PG: INSERT INTO events<br/>(event_id, type, payload, timestamp)

    alt Insert Success
        Store->>PG: COMMIT
        PG-->>Store: Success
        Store->>Wildcard: ACK message
    else Insert Failure
        Store->>PG: ROLLBACK
        PG-->>Store: Error
        Store->>Wildcard: NACK (requeue)
    end

    Note over Store,PG: All events persisted<br/>for audit trail

    User->>Query: GET /events?type=meeting.created
    Query->>PG: SELECT * FROM events<br/>WHERE type = 'meeting.created'
    PG-->>Query: Rows
    Query-->>User: Event history
```

## Interaction Patterns Summary

### 1. **Fire-and-Forget**
- Publisher sends event, does not wait for consumer processing
- Example: `meeting.created` → notification service
- Characteristics: Fast, decoupled, no backpressure

### 2. **Request-Correlation**
- Publisher includes correlation ID for distributed tracing
- Example: User action → multiple microservices → aggregated result
- Characteristics: Traceable, debuggable, async

### 3. **Competing Consumers**
- Multiple instances of same consumer share a queue
- Example: 3x transcript processor instances
- Characteristics: Load balanced, scalable, round-robin

### 4. **Publish-Subscribe Fanout**
- Single event delivered to multiple independent consumers
- Example: `transcript.ready` → [processor, RAG, notifier]
- Characteristics: Parallel processing, independent failures

### 5. **Dead Letter Queue Recovery**
- Failed messages routed to DLQ after retry exhaustion
- Example: Processing failure → 3 retries → DLQ → manual fix → requeue
- Characteristics: Fault tolerant, operator intervention

## Timing Characteristics

| Sequence | Latency | Throughput |
|----------|---------|------------|
| Event Publishing | 10-50ms | 10k+ events/sec |
| Webhook Integration | 500ms-2s | 100 webhooks/sec |
| Schema Validation | 1-10ms | In-memory |
| Voice Transcription | 200-500ms | Real-time streaming |
| DLQ Requeue | Manual | N/A |
| Correlation Query | 5-20ms | 1k+ queries/sec |

## Related Documentation

- [Data Flow Diagrams](./data-flows.md) - Message routing patterns
- [Dependency Graph](./dependencies.md) - Component dependencies
- [C4 Context](./c4-context.md) - System context and personas

---

**Version**: 1.0.0
**Last Updated**: 2026-01-29
**Maintained By**: 33GOD Architecture Team
