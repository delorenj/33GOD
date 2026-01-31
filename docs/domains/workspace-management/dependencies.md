# Workspace Management Domain - Dependency Graph

## Overview

This document visualizes dependency relationships in the Workspace Management domain, showing how iMi, Jelmore, Zellij-Driver, and Perth integrate with Git, databases, and event infrastructure.

## 1. Component Dependency Overview

High-level dependencies between workspace components and external systems.

```mermaid
graph TB
    subgraph External["External Dependencies"]
        Git[Git Repository]
        RabbitMQ[RabbitMQ<br/>Bloodbank]
        SQLite[SQLite Database]
        Redis[Redis Cache]
        Postgres[PostgreSQL]
    end

    subgraph Core["Core Components"]
        iMi[iMi<br/>Worktree Manager]
        Jelmore[Jelmore<br/>Session Orchestrator]
        Driver[Zellij-Driver<br/>Context Manager]
        Perth[Perth<br/>Terminal Multiplexer]
    end

    subgraph AI["AI Providers"]
        Claude[Claude Code API]
        Gemini[Gemini Code API]
        Codex[Codex API]
    end

    subgraph Tools["CLI Tools"]
        GH[gh (GitHub CLI)]
        GitCLI[git CLI]
    end

    %% iMi dependencies
    iMi --> Git
    iMi --> SQLite
    iMi --> RabbitMQ
    iMi --> GH
    iMi --> GitCLI

    %% Jelmore dependencies
    Jelmore --> Claude
    Jelmore --> Gemini
    Jelmore --> Codex
    Jelmore --> RabbitMQ
    Jelmore -.->|optional| Redis

    %% Zellij-Driver dependencies
    Driver --> Redis
    Driver -.->|future| Postgres
    Driver --> Perth

    %% Perth dependencies
    Perth --> Driver

    %% Component interdependencies
    Jelmore -.->|uses| iMi
    Driver -.->|monitors| iMi

    style Git fill:#f96
    style RabbitMQ fill:#f96
    style SQLite fill:#fc6
    style Redis fill:#fc6
```

## 2. iMi (Worktree Manager) Dependencies

Detailed dependency graph for iMi component.

```mermaid
graph LR
    subgraph iMi["iMi Rust Binary"]
        Core[Core Logic]
        CLI[CLI Interface<br/>clap]
        DB[Database Layer<br/>sqlx]
        Watch[File Watcher<br/>notify]
        Events[Event Publisher]
    end

    subgraph Storage["Data Storage"]
        SQLite[SQLite<br/>~/.config/iMi/iMi.db]
        FS[Filesystem<br/>Git worktrees]
    end

    subgraph Git["Git Integration"]
        GitRepo[Git Repository<br/>.git/]
        Git2[git2 Library]
        GitCLI[git CLI<br/>git worktree add]
    end

    subgraph External["External Services"]
        GitHub[GitHub API<br/>via gh CLI]
        RMQ[RabbitMQ<br/>Event Bus]
    end

    subgraph RuntimeDeps["Rust Dependencies"]
        Tokio[tokio<br/>Async Runtime]
        Serde[serde<br/>Serialization]
        Clap[clap<br/>CLI Parsing]
        Notify[notify<br/>File Watching]
        Sqlx[sqlx<br/>SQLite Client]
        Git2Lib[git2<br/>Git Library]
        AioPika[aio-pika<br/>RabbitMQ Client]
    end

    Core --> CLI
    Core --> DB
    Core --> Watch
    Core --> Events

    DB --> SQLite
    DB --> Sqlx

    Core --> Git2
    Git2 --> Git2Lib
    Git2Lib --> GitRepo

    Core --> GitCLI
    GitCLI --> FS

    Watch --> Notify
    Notify --> FS

    Events --> AioPika
    AioPika --> RMQ

    CLI --> Clap
    Core --> Tokio
    Core --> Serde

    Core --> GitHub

    style SQLite fill:#fc6
    style RMQ fill:#f96
    style GitRepo fill:#f96
```

## 3. Jelmore (Session Orchestrator) Dependencies

Dependency graph showing Jelmore's provider abstraction and integration points.

```mermaid
graph TB
    subgraph Jelmore["Jelmore Python Service"]
        CLI[CLI Interface<br/>Typer]
        API[REST API<br/>FastAPI]
        SessionMgr[Session Manager]
        Providers[Provider Abstraction]
    end

    subgraph ProviderImpl["Provider Implementations"]
        ClaudeProvider[Claude Provider<br/>Command Pattern]
        GeminiProvider[Gemini Provider]
        CodexProvider[Codex Provider]
    end

    subgraph AIAPIs["AI Service APIs"]
        ClaudeAPI[Claude Code API<br/>Anthropic]
        GeminiAPI[Gemini Code API<br/>Google]
        CodexAPI[Codex API<br/>OpenAI]
    end

    subgraph Storage["Data Storage"]
        SessionDB[Session DB<br/>SQLite/PostgreSQL]
        RedisCache[Redis Cache<br/>Session State]
    end

    subgraph Events["Event Integration"]
        Consumer[Event Consumer<br/>agent.prompt]
        Producer[Event Producer<br/>session.*]
        RMQ[RabbitMQ]
    end

    subgraph PythonDeps["Python Dependencies"]
        Typer[typer<br/>CLI Framework]
        FastAPI[fastapi<br/>Web Framework]
        Pydantic[pydantic<br/>Validation]
        AioPika[aio-pika<br/>AMQP Client]
        HTTPX[httpx<br/>HTTP Client]
        SQLAlchemy[sqlalchemy<br/>ORM]
    end

    CLI --> Typer
    API --> FastAPI
    SessionMgr --> Pydantic

    SessionMgr --> Providers
    Providers --> ClaudeProvider
    Providers --> GeminiProvider
    Providers --> CodexProvider

    ClaudeProvider --> HTTPX
    GeminiProvider --> HTTPX
    CodexProvider --> HTTPX

    HTTPX --> ClaudeAPI
    HTTPX --> GeminiAPI
    HTTPX --> CodexAPI

    SessionMgr --> SessionDB
    SessionMgr -.->|optional| RedisCache

    SessionDB --> SQLAlchemy
    RedisCache -.-> RedisPy[redis-py]

    API --> Consumer
    SessionMgr --> Producer
    Consumer --> AioPika
    Producer --> AioPika
    AioPika --> RMQ

    style ClaudeAPI fill:#9cf
    style GeminiAPI fill:#9cf
    style CodexAPI fill:#9cf
    style RMQ fill:#f96
```

## 4. Zellij-Driver Dependencies

Dependency graph for terminal context manager.

```mermaid
graph LR
    subgraph Driver["Zellij-Driver Rust Service"]
        Core[Core Logic]
        Plugin[Zellij Plugin API]
        IntentTracker[Intent Tracker]
        Milestone[Milestone Recorder]
    end

    subgraph Storage["Data Storage"]
        Redis[Redis<br/>Session State]
        Postgres[PostgreSQL<br/>Intent History]
    end

    subgraph Integration["Integration Points"]
        Perth[Perth Terminal<br/>Zellij Fork]
        RMQ[RabbitMQ<br/>Events]
    end

    subgraph RustDeps["Rust Dependencies"]
        Tokio[tokio<br/>Async Runtime]
        RedisLib[redis<br/>Redis Client]
        Sqlx[sqlx<br/>PostgreSQL Client]
        Serde[serde<br/>Serialization]
    end

    Core --> Plugin
    Core --> IntentTracker
    Core --> Milestone

    Plugin --> Perth

    IntentTracker --> Redis
    IntentTracker --> RedisLib
    Milestone --> Redis

    Milestone -.->|future| Postgres
    Postgres -.-> Sqlx

    Core --> Tokio
    Core --> Serde

    Core -.->|future| RMQ

    style Redis fill:#fc6
    style Postgres fill:#fc6
    style Perth fill:#9f6
```

## 5. Service Dependency Matrix

Matrix showing which services depend on which infrastructure.

```mermaid
graph TB
    subgraph Services["Workspace Services"]
        S1[iMi]
        S2[Jelmore]
        S3[Zellij-Driver]
        S4[Perth]
    end

    subgraph Infrastructure["Infrastructure Services"]
        Git[Git Repository]
        SQLite[SQLite]
        Redis[Redis]
        Postgres[PostgreSQL]
        RMQ[RabbitMQ]
    end

    subgraph External["External APIs"]
        Claude[Claude API]
        Gemini[Gemini API]
        GitHub[GitHub API]
    end

    %% iMi dependencies
    S1 -->|REQUIRED| Git
    S1 -->|REQUIRED| SQLite
    S1 -->|OPTIONAL| RMQ
    S1 -->|OPTIONAL| GitHub

    %% Jelmore dependencies
    S2 -->|REQUIRED| Claude
    S2 -.->|OPTIONAL| Gemini
    S2 -->|OPTIONAL| Redis
    S2 -->|OPTIONAL| SQLite
    S2 -->|OPTIONAL| RMQ

    %% Zellij-Driver dependencies
    S3 -->|REQUIRED| Redis
    S3 -.->|FUTURE| Postgres
    S3 -->|REQUIRED| S4

    %% Perth dependencies
    S4 -->|OPTIONAL| S3

    style Git fill:#f96
    style Claude fill:#f96
    style Redis fill:#fc6
```

## 6. Startup Dependency Chain

Shows the required order of service initialization.

```mermaid
graph TD
    Start[System Startup] --> Infrastructure

    Infrastructure[1. Infrastructure Layer] --> Git
    Infrastructure --> SQLite
    Infrastructure --> Redis

    Git[Git Repository<br/>Must Exist] --> iMi
    SQLite[SQLite Database<br/>Auto-Created] --> iMi
    Redis[Redis Server<br/>docker-compose up] --> Driver

    iMi[2. iMi Service<br/>Worktree Manager] --> Jelmore

    Jelmore[3. Jelmore Service<br/>Session Orchestrator] --> Ready1
    Driver[4. Zellij-Driver<br/>Context Manager] --> Perth

    Perth[5. Perth Terminal<br/>User Interface] --> Ready2

    Ready1{All Services<br/>Healthy?}
    Ready2{Terminal<br/>Ready?}

    Ready1 -->|Yes| DeveloperReady[Developer Can Start]
    Ready2 -->|Yes| DeveloperReady

    Ready1 -->|No| FailSafe[Degraded Mode<br/>Core Features Only]
    Ready2 -->|No| Fallback[Fallback to Standard Zellij]

    style Git fill:#f96
    style Redis fill:#fc6
    style DeveloperReady fill:#9f6
    style Ready1 decision
    style Ready2 decision
```

## Dependency Impact Analysis

### Critical Dependencies (System Fails if Unavailable)

| Service | Critical Dependency | Impact if Unavailable | Mitigation |
|---------|---------------------|----------------------|------------|
| iMi | Git Repository | Cannot create worktrees | Must be in git repo |
| iMi | SQLite | Cannot track worktrees | Database auto-created |
| Jelmore | AI Provider APIs | Cannot run AI sessions | Multiple provider fallback |
| Zellij-Driver | Redis | Cannot persist context | Graceful degradation |

### Optional Dependencies (Degraded Mode)

| Service | Optional Dependency | Feature Loss | Workaround |
|---------|---------------------|-------------|------------|
| iMi | RabbitMQ | No event publishing | Local-only operation |
| iMi | GitHub CLI | No PR review worktrees | Manual git checkout |
| Jelmore | Redis | No session caching | Slower session resume |
| Zellij-Driver | PostgreSQL | No intent history | Redis-only operation |

### External API Dependencies

| API | Service | Fallback Strategy |
|-----|---------|-------------------|
| Claude Code API | Jelmore | Switch to Gemini or Codex |
| Gemini Code API | Jelmore | Switch to Claude or Codex |
| GitHub API | iMi | Use git CLI directly |

## 7. Build-Time vs Runtime Dependencies

Separates build and runtime dependency concerns.

```mermaid
graph LR
    subgraph BuildTime["Build-Time Dependencies"]
        RustToolchain[Rust Toolchain<br/>1.70+]
        PythonEnv[Python 3.10+<br/>uv/pip]
        Cargo[Cargo<br/>Rust Package Manager]
        UV[uv<br/>Python Package Manager]
    end

    subgraph BuildArtifacts["Build Artifacts"]
        iMiBinary[iMi Binary<br/>Rust Executable]
        JelmorePkg[Jelmore Package<br/>Python Wheel]
        DriverBinary[Zellij-Driver Binary]
    end

    subgraph Runtime["Runtime Dependencies"]
        Git[Git 2.30+]
        SQLite[SQLite 3.35+]
        Redis[Redis 7.x]
        RMQ[RabbitMQ 3.x]
        AIAPIs[AI Provider APIs]
    end

    RustToolchain --> Cargo
    Cargo --> iMiBinary
    Cargo --> DriverBinary

    PythonEnv --> UV
    UV --> JelmorePkg

    iMiBinary --> Git
    iMiBinary --> SQLite
    iMiBinary -.-> RMQ

    JelmorePkg --> AIAPIs
    JelmorePkg -.-> Redis
    JelmorePkg -.-> RMQ

    DriverBinary --> Redis

    style RustToolchain fill:#9cf
    style PythonEnv fill:#9cf
    style Git fill:#f96
    style AIAPIs fill:#f96
```

## Dependency Version Constraints

### Rust Dependencies (iMi, Zellij-Driver)

```toml
[dependencies]
tokio = { version = "1.35", features = ["full"] }
git2 = "0.18"
sqlx = { version = "0.7", features = ["sqlite", "runtime-tokio"] }
notify = "6.1"
serde = { version = "1.0", features = ["derive"] }
clap = { version = "4.4", features = ["derive"] }
redis = { version = "0.24", features = ["tokio-comp"] }
```

### Python Dependencies (Jelmore)

```toml
[dependencies]
typer = "^0.9.0"
fastapi = "^0.109.0"
pydantic = "^2.5.0"
aio-pika = "^9.3.0"
httpx = "^0.26.0"
sqlalchemy = "^2.0.0"
redis = "^5.0.0"
```

### System Dependencies

| Component | Minimum Version | Recommended |
|-----------|----------------|-------------|
| Git | 2.30+ | 2.43+ |
| SQLite | 3.35+ | 3.45+ |
| Redis | 6.2+ | 7.2+ |
| PostgreSQL | 13+ | 16+ |
| RabbitMQ | 3.11+ | 3.13+ |

## Circular Dependency Prevention

### Design Principles

1. **Layered Architecture**: iMi (bottom) → Jelmore (middle) → Driver (top)
2. **No Circular Imports**: Services never import each other's code
3. **Event-Driven Decoupling**: Communication via Bloodbank events, not direct calls
4. **Interface Segregation**: Depend on abstractions (SQLite schema), not implementations

### Avoided Patterns

- **Jelmore → iMi (code)**: Jelmore never imports iMi, uses CLI or events
- **Driver → Jelmore (code)**: Driver monitors but doesn't invoke Jelmore
- **iMi → Jelmore (code)**: iMi doesn't know about Jelmore, uses events

## Related Documentation

- [Data Flow Diagrams](./data-flows.md) - Data movement patterns
- [Sequence Diagrams](./sequences.md) - Interaction flows
- [C4 Context](./c4-context.md) - System context

---

**Version**: 1.0.0
**Last Updated**: 2026-01-29
**Maintained By**: 33GOD Architecture Team
