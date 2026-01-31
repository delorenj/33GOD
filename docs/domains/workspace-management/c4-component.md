# C4 Component Level: Workspace Management Domain

## Domain Overview

The Workspace Management domain provides comprehensive Git worktree orchestration, terminal session management, and cognitive context preservation for distributed agentic workflows. The domain comprises three primary services that work together to enable parallel development workflows across multiple git worktrees with full state persistence and context awareness.

## System Components

### 1. iMi - Git Worktree Manager
- **Type**: Command-Line Application
- **Technology**: Rust, PostgreSQL, Git2
- **Documentation**: [c4-component-imi.md](./c4-component-imi.md)
- **Description**: Manages Git worktrees with database-backed state tracking for parallel multi-agent development workflows

### 2. Perth - Terminal Workspace Manager
- **Type**: Terminal Multiplexer Application
- **Technology**: Rust, PostgreSQL, WebAssembly (WASM plugins)
- **Documentation**: [c4-component-perth.md](./c4-component-perth.md)
- **Description**: Terminal workspace manager (fork of Zellij) with PostgreSQL persistence for session/tab/pane state

### 3. Zellij Driver - Cognitive Context Manager
- **Type**: Service Library
- **Technology**: Rust, Redis, RabbitMQ
- **Documentation**: [c4-component-zellij-driver.md](./c4-component-zellij-driver.md)
- **Description**: Cognitive context tracking and intent history management for terminal sessions

## Domain Architecture Diagram

```mermaid
C4Component
    title Component Diagram for Workspace Management Domain

    Container_Boundary(imi, "iMi - Git Worktree Manager") {
        Component(imi_cli, "CLI Handler", "Rust/Clap", "Command-line interface and user interaction")
        Component(imi_worktree, "Worktree Manager", "Rust", "Git worktree lifecycle management")
        Component(imi_git, "Git Manager", "Rust/Git2", "Low-level git operations and authentication")
        Component(imi_db, "Database Manager", "Rust/SQLx", "Repository and worktree state persistence")
        Component(imi_context, "Context Detector", "Rust", "Git context detection and location awareness")
        Component(imi_monitor, "File Monitor", "Rust/Notify", "Real-time file system change detection")
        Component(imi_github, "GitHub Client", "Rust/Octocrab", "GitHub API integration for PRs")
    }

    Container_Boundary(perth, "Perth - Terminal Workspace") {
        Component(perth_server, "Server Core", "Rust/Tokio", "Terminal multiplexer server runtime")
        Component(perth_client, "Client CLI", "Rust", "Terminal client and command dispatcher")
        Component(perth_persist, "Persistence Manager", "Rust/SQLx", "Write-behind caching for session state")
        Component(perth_screen, "Screen Manager", "Rust", "Terminal screen and layout management")
        Component(perth_panes, "Pane Manager", "Rust", "Terminal pane lifecycle and PTY management")
        Component(perth_plugins, "Plugin System", "WASM/Rust", "Plugin runtime and API")
        Component(perth_route, "Route Handler", "Rust", "Command routing and action dispatch")
    }

    Container_Boundary(zdriver, "Zellij Driver - Cognitive Context") {
        Component(zd_state, "State Manager", "Rust/Redis", "Pane and tab state tracking in Redis")
        Component(zd_orch, "Orchestrator", "Rust/Tokio", "Workflow orchestration and automation")
        Component(zd_llm, "LLM Integration", "Rust", "Multi-provider LLM integration with circuit breaker")
        Component(zd_bloodbank, "Bloodbank Client", "Rust", "Knowledge base and context retrieval")
        Component(zd_snapshot, "Snapshot Manager", "Rust", "Session snapshot and restore")
        Component(zd_filter, "Filter Engine", "Rust/Regex", "Intent filtering and pattern matching")
    }

    ContainerDb(postgres, "PostgreSQL", "PostgreSQL 14+", "Persistent state storage for worktrees and sessions")
    ContainerDb(redis, "Redis", "Redis 6+", "Fast state cache and intent history")
    ContainerQueue(rabbitmq, "RabbitMQ", "Message Queue", "Async workflow coordination")
    System_Ext(github, "GitHub API", "Repository management and PR operations")
    System_Ext(git, "Git", "Version control operations")

    ' iMi internal relationships
    Rel(imi_cli, imi_worktree, "Uses", "Creates/manages worktrees")
    Rel(imi_worktree, imi_git, "Uses", "Git operations")
    Rel(imi_worktree, imi_db, "Uses", "Persists state")
    Rel(imi_worktree, imi_context, "Uses", "Detects context")
    Rel(imi_cli, imi_github, "Uses", "PR operations")
    Rel(imi_monitor, imi_db, "Updates", "File changes")

    ' Perth internal relationships
    Rel(perth_client, perth_server, "Connects to", "IPC")
    Rel(perth_server, perth_screen, "Uses", "Manages layouts")
    Rel(perth_screen, perth_panes, "Contains", "Terminal panes")
    Rel(perth_server, perth_persist, "Uses", "Persists state")
    Rel(perth_route, perth_panes, "Controls", "Pane actions")
    Rel(perth_server, perth_plugins, "Loads", "WASM plugins")

    ' Zellij Driver internal relationships
    Rel(zd_orch, zd_state, "Uses", "State tracking")
    Rel(zd_orch, zd_llm, "Uses", "AI assistance")
    Rel(zd_orch, zd_bloodbank, "Uses", "Knowledge retrieval")
    Rel(zd_snapshot, zd_state, "Uses", "State capture")
    Rel(zd_filter, zd_state, "Filters", "Intent queries")

    ' External dependencies
    Rel(imi_git, git, "Uses", "Git CLI/libgit2")
    Rel(imi_github, github, "Uses", "REST API")
    Rel(imi_db, postgres, "Reads/Writes", "SQL")
    Rel(perth_persist, postgres, "Writes async", "SQL")
    Rel(zd_state, redis, "Reads/Writes", "Key-value")
    Rel(zd_orch, rabbitmq, "Publishes", "Events")

    ' Cross-service integration
    Rel(perth_server, zd_state, "Tracks", "Pane state")
    Rel(perth_panes, imi_worktree, "Launches in", "Worktree paths")
    Rel(zd_orch, perth_client, "Controls", "CLI commands")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## Component Relationships

### Primary Integration Points

1. **Perth → Zellij Driver**: Terminal sessions track cognitive context via Redis state
2. **Perth → iMi**: Terminal panes launch in specific git worktree directories
3. **iMi → PostgreSQL**: Worktree registry and agent activity tracking
4. **Perth → PostgreSQL**: Session, tab, and pane persistence with write-behind caching
5. **Zellij Driver → Redis**: Intent history and pane state tracking
6. **Zellij Driver → RabbitMQ**: Async workflow event publishing

### Data Flow Patterns

**Worktree Creation Flow**:
1. User invokes `iMi add feat <name>` CLI command
2. CLI Handler validates and parses command
3. Worktree Manager creates git worktree via Git Manager
4. Context Detector identifies worktree type and location
5. Database Manager persists worktree record to PostgreSQL
6. File Monitor begins tracking worktree directory

**Session Persistence Flow**:
1. Perth Server manages terminal session lifecycle
2. Pane Manager creates/updates panes in screen
3. Persistence Manager queues write operations (write-behind)
4. Background worker processes queue asynchronously
5. PostgreSQL stores session/tab/pane state

**Intent Tracking Flow**:
1. Zellij Driver Orchestrator observes terminal activity
2. Filter Engine classifies intent type (milestone/checkpoint/exploration)
3. State Manager writes intent entry to Redis
4. Snapshot Manager can restore historical context
5. LLM Integration provides context-aware assistance

## Technology Stack Summary

### iMi
- **Core**: Rust 2021 edition
- **Git**: `git2` (libgit2 bindings)
- **Database**: `sqlx` with PostgreSQL driver
- **CLI**: `clap` v4.5 (derive)
- **Async**: `tokio` (full runtime)
- **Monitoring**: `notify` v6.1 (file watching)
- **GitHub**: `octocrab` v0.38

### Perth
- **Core**: Rust 2021 edition
- **Database**: `sqlx` with PostgreSQL driver
- **IPC**: `interprocess` v1.2
- **Async**: `tokio` v1.38
- **Terminal**: `termwiz`, `vte` (ANSI parsing)
- **Plugins**: WASM runtime with custom API
- **Serialization**: `prost` (protobuf)

### Zellij Driver
- **Core**: Rust 2021 edition
- **Cache**: `redis` v0.27 (async)
- **Queue**: `lapin` v2.5 (RabbitMQ)
- **Async**: `tokio` (multi-threaded runtime)
- **HTTP**: `reqwest` v0.12 (JSON features)
- **AI**: Multi-provider (Anthropic, OpenAI, Ollama)
- **Serialization**: `serde_json`

## Deployment Considerations

### Database Requirements
- **PostgreSQL 14+** required for both iMi and Perth
- Connection pooling configured (10 max, 2 min connections)
- Migrations managed via `sqlx::migrate!` macro
- Graceful degradation if database unavailable (Perth)

### Redis Requirements
- **Redis 6+** for Zellij Driver state management
- Multiplexed async connections via `redis::aio`
- Key namespacing: `znav:pane:*`, `znav:tab:*`, `znav:intent:*`

### RabbitMQ Requirements
- Message queue for async workflow events
- Event types: intent logged, pane created, session restored
- Consumer-based processing patterns

### File System Requirements
- **iMi**: Requires git executable in PATH
- **iMi**: SSH keys for git authentication (~/.ssh/id_*)
- **Perth**: Unix domain sockets for IPC
- **Perth**: PTY allocation for terminal panes

## Security Considerations

### Authentication
- **Git**: SSH key-based authentication (id_ed25519, id_rsa)
- **GitHub**: Personal Access Token (PAT) via environment variables
- **Database**: Connection string with credentials (environment)
- **Redis**: Connection URL with optional authentication

### Secrets Management
- Environment variables for sensitive configuration
- No hardcoded credentials in source code
- SSH keys protected by file system permissions

## Performance Characteristics

### iMi
- Concurrent worktree operations via async/await
- Database connection pooling (10 connections)
- File monitoring with debouncing for high-frequency changes
- Zero-copy path operations where possible

### Perth
- Write-behind caching for persistence (NFR-003)
- Async write queue to prevent blocking main thread
- Efficient terminal rendering with dirty region tracking
- WASM plugin sandboxing with minimal overhead

### Zellij Driver
- Redis multiplexed connections for high concurrency
- Circuit breaker pattern for LLM resilience
- Intent history limited to prevent unbounded growth
- Async/await throughout for non-blocking I/O

## Testing Strategy

### iMi
- Unit tests with `tempfile` for file operations
- Integration tests with real git repositories
- Database tests with `serial_test` for isolation
- Mock-based testing for GitHub API

### Perth
- End-to-end tests in `src/tests/e2e`
- Remote runner for distributed testing
- Snapshot testing with `insta` crate
- PTY simulation for terminal testing

### Zellij Driver
- Component tests with mock Redis
- Circuit breaker testing with fault injection
- LLM provider testing with noop implementation
- Async runtime testing with `tokio-test`

## Monitoring and Observability

### Logging
- **iMi**: `colored` terminal output with progress indicators
- **Perth**: `log` crate with configurable levels
- **Zellij Driver**: Structured logging to stderr

### Metrics
- **iMi**: Database query performance tracking
- **Perth**: Session/tab/pane lifecycle events
- **Zellij Driver**: Intent entry counts, LLM latency

### Health Checks
- **iMi**: Database connectivity via `SELECT 1`
- **Perth**: IPC socket availability
- **Zellij Driver**: Redis ping, RabbitMQ heartbeat

---

**Document Version**: 1.0
**Last Updated**: 2026-01-29
**Domain**: Workspace Management
**Architecture Level**: C4 Component
