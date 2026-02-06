# Event Infrastructure Domain - Dependency Graph

## Overview

This document visualizes the dependency relationships between components in the Event Infrastructure domain, showing build-time dependencies, runtime dependencies, and service integration points.

## 1. Component Dependency Graph

Shows the hierarchical dependencies between all Event Infrastructure components.

```mermaid
graph TB
    subgraph External["External Dependencies"]
        RabbitMQ[RabbitMQ 3.x<br/>Message Broker]
        Redis[Redis 7.x<br/>Cache]
        Postgres[PostgreSQL<br/>Event Store]
        Git[Git Repository<br/>Version Control]
    end

    subgraph BuildTime["Build-Time Dependencies"]
        Holyfields[Holyfields<br/>Schema Registry]
        JSONSchema[JSON Schema<br/>Draft 2020-12]
        CodeGen[Code Generators<br/>datamodel-codegen, json-schema-to-zod]
    end

    subgraph Runtime["Runtime Components"]
        Bloodbank[Bloodbank Publisher<br/>FastAPI]
        Consumers[Event Consumers<br/>Multiple Services]
        HeyMa[HeyMa<br/>Voice Assistant]
    end

    subgraph Generated["Generated Artifacts"]
        PydanticModels[Pydantic Models<br/>Python]
        ZodSchemas[Zod Schemas<br/>TypeScript]
    end

    subgraph Services["Microservices"]
        TranscriptProc[Transcript Processor]
        EventStore[Event Store Manager]
        AgentFeedback[Agent Feedback Router]
        TheBoard[TheBoard Producer]
    end

    subgraph Integration["Integration Layer"]
        N8N[n8n Workflows]
        NodeRED[Node-RED Flows]
        Fireflies[Fireflies.ai<br/>Webhooks]
        GitHub[GitHub Webhooks]
    end

    %% Build-time dependencies
    JSONSchema --> Holyfields
    Holyfields --> CodeGen
    CodeGen --> PydanticModels
    CodeGen --> ZodSchemas
    Holyfields --> Git

    %% Runtime dependencies
    PydanticModels --> Bloodbank
    PydanticModels --> Consumers
    ZodSchemas --> Consumers

    Bloodbank --> RabbitMQ
    Bloodbank --> Redis
    Consumers --> RabbitMQ
    EventStore --> Postgres
    EventStore --> RabbitMQ

    %% Service dependencies
    TranscriptProc --> Consumers
    EventStore --> Consumers
    AgentFeedback --> Consumers
    TheBoard --> Bloodbank
    HeyMa --> Bloodbank

    %% Integration dependencies
    Fireflies --> N8N
    GitHub --> N8N
    N8N --> Bloodbank
    NodeRED --> RabbitMQ

    style Holyfields fill:#9cf
    style RabbitMQ fill:#f96
    style Bloodbank fill:#9f6
```

## 2. Service Dependency Matrix

Detailed matrix showing which services depend on which infrastructure components.

```mermaid
graph LR
    subgraph Services["Microservices"]
        S1[Fireflies Transcript Processor]
        S2[Agent Feedback Router]
        S3[TheBoard Meeting Producer]
        S4[TheBoardroom Visualizer]
        S5[Event Store Manager]
        S6[HeyMa Voice]
    end

    subgraph Infrastructure["Infrastructure Components"]
        RMQ[RabbitMQ<br/>Event Bus]
        BB[Bloodbank<br/>Publisher API]
        HF[Holyfields<br/>Schemas]
        R[Redis<br/>Cache]
        PG[PostgreSQL<br/>Database]
    end

    %% Fireflies Processor dependencies
    S1 -->|Consumes Events| RMQ
    S1 -->|Uses Schemas| HF
    S1 -->|File System| FS[Obsidian Vault]

    %% Agent Feedback Router dependencies
    S2 -->|Consumes Events| RMQ
    S2 -->|Uses Schemas| HF
    S2 -->|Calls API| AF[AgentForge API]

    %% TheBoard Producer dependencies
    S3 -->|Publishes via| BB
    S3 -->|Uses Schemas| HF

    %% TheBoardroom dependencies
    S4 -->|Consumes Events| RMQ
    S4 -->|Uses Schemas| HF
    S4 -->|WebSocket| WS[Browser Clients]

    %% Event Store dependencies
    S5 -->|Consumes All Events| RMQ
    S5 -->|Persists to| PG

    %% HeyMa dependencies
    S6 -->|Publishes via| BB
    S6 -->|Uses Schemas| HF
    S6 -->|Calls| N8N[n8n API]
    S6 -->|Calls| EL[ElevenLabs TTS]

    %% Bloodbank dependencies
    BB -->|Publishes to| RMQ
    BB -->|Tracks in| R

    style RMQ fill:#f96
    style BB fill:#9f6
    style HF fill:#9cf
```

## 3. Schema Dependency Tree

Shows how schemas inherit from common base types and depend on each other.

```mermaid
graph TB
    subgraph Common["Common Schemas (common/)"]
        BaseEvent[BaseEvent<br/>event_id, timestamp, source]
        Enums[Enums<br/>MeetingStatus, TranscriptFormat]
        Types[Common Types<br/>UUID, ISO8601Timestamp]
    end

    subgraph TheBoard["TheBoard Schemas (theboard/events/)"]
        MeetingCreated[meeting_created.json]
        MeetingStarted[meeting_started.json]
        MeetingEnded[meeting_ended.json]
        ParticipantJoined[participant_joined.json]
    end

    subgraph Fireflies["Fireflies Schemas (fireflies/events/)"]
        TranscriptReady[transcript_ready.json]
        TranscriptProcessed[transcript_processed.json]
    end

    subgraph HeyMa["HeyMa Schemas (heymama/events/)"]
        TranscriptionCompleted[transcription_completed.json]
        CommandRecognized[command_recognized.json]
    end

    subgraph AgentForge["AgentForge Schemas (agentforge/events/)"]
        FeedbackRequested[feedback_requested.json]
        FeedbackReceived[feedback_received.json]
    end

    %% Base dependencies
    BaseEvent --> MeetingCreated
    BaseEvent --> MeetingStarted
    BaseEvent --> MeetingEnded
    BaseEvent --> TranscriptReady
    BaseEvent --> TranscriptionCompleted
    BaseEvent --> FeedbackRequested

    Enums --> MeetingCreated
    Enums --> TranscriptReady

    Types --> BaseEvent

    %% Cross-schema dependencies
    MeetingCreated -.->|References| ParticipantJoined
    TranscriptReady -.->|Triggers| TranscriptProcessed

    style BaseEvent fill:#9cf
    style Enums fill:#fc6
    style Types fill:#fc6
```

## 4. External System Integration Dependencies

Maps external system dependencies and their failure impact.

```mermaid
graph TB
    subgraph EventInfra["Event Infrastructure"]
        Core[Core Event Bus<br/>RabbitMQ + Bloodbank]
    end

    subgraph Critical["Critical Dependencies<br/>(System Fails if Down)"]
        C1[RabbitMQ Broker]
        C2[Holyfields Schemas<br/>Build-time Only]
    end

    subgraph Important["Important Dependencies<br/>(Degraded Mode if Down)"]
        I1[Redis Cache<br/>Correlation Tracking]
        I2[PostgreSQL<br/>Event Store]
    end

    subgraph Optional["Optional Dependencies<br/>(Graceful Degradation)"]
        O1[n8n Workflows]
        O2[ElevenLabs TTS]
        O3[Obsidian File System]
    end

    subgraph External["External Data Sources"]
        E1[Fireflies.ai API]
        E2[GitHub Webhooks]
        E3[Letta Agent Framework]
    end

    %% Critical dependencies
    Core -.->|REQUIRES| C1
    Core -.->|REQUIRES<br/>build-time| C2

    %% Important dependencies
    Core -->|Uses| I1
    Core -->|Uses| I2

    %% Optional dependencies
    Core -->|Integrates| O1
    Core -->|Integrates| O2
    Core -->|Integrates| O3

    %% External sources
    E1 --> O1
    E2 --> O1
    O1 --> Core
    E3 --> Core

    style C1 fill:#f96
    style C2 fill:#f96
    style I1 fill:#fc6
    style I2 fill:#fc6
    style O1 fill:#9f6
    style O2 fill:#9f6
    style O3 fill:#9f6
```

## 5. Runtime Dependency Graph

Shows the order of startup dependencies and health check chains.

```mermaid
graph TD
    Start[System Startup] --> RMQ

    RMQ[1. RabbitMQ Broker<br/>Start First] --> Exchange
    Exchange[2. Create Exchange<br/>events topic] --> Redis

    Redis[3. Redis Cache<br/>Optional] --> Bloodbank

    Bloodbank[4. Bloodbank Publisher<br/>Wait for RabbitMQ] --> Services

    Services[5. Consumer Services<br/>Wait for Bloodbank] --> Health

    Health{Health Checks<br/>All Green?}

    Health -->|Yes| Ready[System Ready]
    Health -->|No| Retry[Retry with<br/>Exponential Backoff]

    Retry --> Health

    subgraph HealthChecks["Health Check Dependencies"]
        HC1[RabbitMQ Connection]
        HC2[Redis Connection]
        HC3[Bloodbank API]
        HC4[Consumer Queues]
    end

    Health -.-> HC1
    Health -.-> HC2
    Health -.-> HC3
    Health -.-> HC4

    style RMQ fill:#f96
    style Health decision
    style Ready fill:#9f6
```

## 6. Build Pipeline Dependencies

Shows CI/CD build order and artifact dependencies.

```mermaid
graph LR
    subgraph Source["Source Code"]
        Schemas[JSON Schemas<br/>holyfields/]
        BBCode[Bloodbank Code<br/>Python]
        ConsumerCode[Consumer Code<br/>Python/TS]
    end

    subgraph Build["Build Pipeline"]
        ValidateSchemas[Validate Schemas<br/>jsonschema]
        GeneratePython[Generate Python<br/>datamodel-codegen]
        GenerateTS[Generate TypeScript<br/>json-schema-to-zod]
        ContractTests[Contract Tests<br/>pytest + vitest]
    end

    subgraph Artifacts["Build Artifacts"]
        PyModels[generated/python/]
        TSModels[generated/typescript/]
    end

    subgraph Deploy["Deployment"]
        BBDeploy[Deploy Bloodbank<br/>Docker]
        ConsumerDeploy[Deploy Consumers<br/>Docker/K8s]
    end

    Schemas --> ValidateSchemas
    ValidateSchemas --> GeneratePython
    ValidateSchemas --> GenerateTS

    GeneratePython --> PyModels
    GenerateTS --> TSModels

    PyModels --> ContractTests
    TSModels --> ContractTests

    ContractTests --> BBCode
    ContractTests --> ConsumerCode

    BBCode --> BBDeploy
    ConsumerCode --> ConsumerDeploy

    PyModels --> BBDeploy
    PyModels --> ConsumerDeploy
    TSModels --> ConsumerDeploy

    style ValidateSchemas fill:#9cf
    style ContractTests fill:#9cf
```

## Dependency Impact Analysis

### High Impact (System Failure if Unavailable)

| Dependency | Impact | Mitigation |
|------------|--------|------------|
| RabbitMQ Broker | Complete system failure | RabbitMQ clustering, persistent queues |
| Holyfields Schemas | Build failure (runtime unaffected) | Schema validation in CI, cached artifacts |

### Medium Impact (Degraded Performance)

| Dependency | Impact | Mitigation |
|------------|--------|------------|
| Redis Cache | Lost correlation tracking | Graceful degradation, optional feature |
| PostgreSQL Event Store | Lost event history | Event store is optional, async writes |

### Low Impact (Feature Loss Only)

| Dependency | Impact | Mitigation |
|------------|--------|------------|
| n8n Workflows | Lost webhook automation | Direct consumer integration |
| ElevenLabs TTS | No voice responses | Fallback to text-only |
| Obsidian Vault | Lost transcript storage | Alternative storage backends |

## Versioning Strategy

### Schema Versioning
- **Format**: Semantic Versioning (2.1.0)
- **Breaking Change**: Major version bump (1.x.x → 2.0.0)
- **New Field**: Minor version bump (1.1.x → 1.2.0)
- **Bug Fix**: Patch version bump (1.1.1 → 1.1.2)

### API Versioning
- **Bloodbank REST API**: URL-based (`/v1/events/`, `/v2/events/`)
- **RabbitMQ Events**: Routing key includes version (`theboard.v1.meeting.created`)

### Compatibility Matrix

| Component | Python Schemas | TypeScript Schemas | RabbitMQ |
|-----------|---------------|-------------------|----------|
| Bloodbank Publisher | 2.0+ | N/A | 3.x |
| Python Consumers | 2.0+ | N/A | 3.x |
| TypeScript Consumers | N/A | 2.0+ | 3.x |
| Event Store Manager | 2.0+ | N/A | 3.x |

## Circular Dependency Prevention

### Avoided Patterns
- **No Consumer → Bloodbank**: Consumers never publish via Bloodbank API (direct RabbitMQ)
- **No Schema → Service Code**: Services import generated schemas, never raw JSON
- **No Build-time → Runtime**: Holyfields runs at build-time only

### Dependency Rules
1. **Acyclic Graph**: All dependencies form a Directed Acyclic Graph (DAG)
2. **Layered Architecture**: Clear separation between build-time and runtime
3. **Interface Segregation**: Services depend on interfaces (Pydantic/Zod), not implementations

## Related Documentation

- [Data Flow Diagrams](./data-flows.md) - Message routing and processing flows
- [Sequence Diagrams](./sequences.md) - Interaction patterns
- [C4 Container](./c4-container.md) - Container deployment architecture

---

**Version**: 1.0.0
**Last Updated**: 2026-01-29
**Maintained By**: 33GOD Architecture Team
