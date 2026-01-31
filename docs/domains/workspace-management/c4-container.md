# C4 Container Level: Workspace Management Domain

## Overview

The Workspace Management domain provides integrated terminal workspace orchestration for the 33GOD platform. It consists of three primary containers that work together to manage Git worktrees, terminal multiplexing, and workspace context tracking with distributed persistence.

## Containers

### 1. iMi CLI Tool

- **Name**: iMi CLI Tool
- **Description**: Git worktree management CLI for distributed agentic workflows
- **Type**: Command-line Application
- **Technology**: Rust, Tokio (async runtime), PostgreSQL, SQLite
- **Deployment**: Native binary (`cargo install --path .`)

#### Purpose

iMi is a sophisticated Git worktree management tool designed for asynchronous, parallel multi-agent workflows. It provides intelligent worktree creation, real-time monitoring, and PostgreSQL-backed persistence for worktree history and agent coordination. The tool implements convention-over-configuration principles with opinionated directory structures optimized for concurrent agent operations.

#### Components

This container implements the following core components:
- **CLI Interface**: Command parsing and user interaction (Clap framework)
- **Worktree Manager**: Git worktree lifecycle management
- **Database Manager**: PostgreSQL/SQLite persistence layer
- **Git Manager**: Git operations abstraction (git2 library)
- **Monitor System**: Real-time file change tracking (notify crate)
- **Config Manager**: TOML-based configuration management
- **GitHub Integration**: PR review and project creation (octocrab)

#### Key Features

- Intelligent worktree management with typed workflows (feat, fix, review, aiops, devops)
- PostgreSQL database for multi-agent coordination
- Real-time file monitoring across all worktrees
- Automatic symlink management for shared configuration
- GitHub integration for PR reviews and project creation
- Activity tracking with agent identification
- Convention-based directory structure (`trunk-main/`, `feat-*/`, `pr-*/`, etc.)

#### Interfaces

##### CLI Interface
- **Protocol**: Command-line arguments (stdin/stdout)
- **Description**: Primary user interface for worktree operations
- **Commands**:
  - `iMi init [--repo PATH] [--force]` - Initialize repository structure
  - `iMi add {feat|fix|review|aiops|devops} NAME` - Create typed worktree
  - `iMi status` - Show all worktree status
  - `iMi list` - List active worktrees
  - `iMi remove NAME` - Remove a worktree
  - `iMi monitor` - Start real-time monitoring
  - `iMi trunk` - Switch to trunk worktree
  - `iMi project create NAME` - Create new project from template
  - `iMi doctor` - Verify installation and dependencies

##### Database Interface
- **Protocol**: PostgreSQL wire protocol / SQLite file
- **Description**: Persistent storage for worktree metadata and agent activities
- **Schema**:
  - `projects` - Repository configuration and metadata
  - `worktrees` - Worktree records with Git status tracking
  - `agent_activities` - File change and agent activity logs
  - `worktree_types` - Configurable worktree type definitions

##### Git Integration
- **Protocol**: Git CLI / libgit2
- **Description**: Direct Git repository manipulation
- **Operations**:
  - Worktree creation and removal
  - Branch management
  - Status querying
  - Commit tracking

#### Dependencies

##### External Services
- **PostgreSQL**: Primary database for production deployments
  - Connection via SQLx with async Tokio runtime
  - Schema: `/home/delorenj/code/33GOD/iMi/trunk-main/migrations/`
  - Supports connection pooling and transactions

- **SQLite**: Fallback database for local development
  - File-based storage at `~/.config/iMi/iMi.db`
  - Same schema as PostgreSQL for compatibility

- **GitHub API**: Project creation and PR review integration
  - REST API via octocrab client
  - OAuth token-based authentication

##### File System
- **Git Repositories**: Direct file system access to `.git/` directories
- **Configuration**: `~/.config/iMi/config.toml`
- **Sync Directories**: `sync/global/` and `sync/repo/` for shared configs

#### Infrastructure

- **Deployment Config**: Cargo.toml with release optimizations (LTO, strip, codegen-units=1)
- **Binary Name**: `iMi`
- **Installation Method**: `cargo install` or from source
- **Resources**:
  - Memory: Minimal (<50MB typical)
  - CPU: Burst for Git operations, idle during monitoring
  - Disk: Database grows with worktree history
- **Scaling**: Single-user CLI, no horizontal scaling required

---

### 2. Perth (Zellij Fork)

- **Name**: Perth Terminal Multiplexer
- **Description**: Zellij fork optimized for multi-agent workflows with visual notifications and PostgreSQL persistence
- **Type**: Terminal Multiplexer / IDE
- **Technology**: Rust, WebAssembly (plugins), PostgreSQL, Tokio
- **Deployment**: Native binary with plugin system

#### Purpose

Perth is a specialized fork of Zellij designed as the primary IDE for the 33GOD ecosystem. It extends terminal multiplexing with native visual notifications, frame-based animations, PostgreSQL session persistence, and programmatic workspace control. Built for managing complex multi-agent workflows where dozens of AI agents operate concurrently with immediate visual feedback and robust session recovery.

#### Components

This container deploys the following architectural components:

**Core System**:
- **zellij-client**: Client-side terminal interaction and rendering
- **zellij-server**: Server-side session management and multiplexing
- **zellij-utils**: Shared utilities and configuration
- **zellij-tile**: Plugin API for WebAssembly extensions
- **zellij-tile-utils**: Helper utilities for plugin development

**33GOD Extensions**:
- **Notification Bus**: Pane-level visual alerts with styled borders
- **Animation Engine**: 60fps frame-based UI animations
- **Persistence Manager**: PostgreSQL write-behind session state
- **ZDrive Integration**: External CLI control interface

**Default Plugins** (WebAssembly):
- compact-bar, status-bar, tab-bar - UI components
- strider - File browser
- session-manager - Session persistence UI
- configuration, plugin-manager - Settings management
- layout-manager - Layout templates

#### Key Features

- **Visual Notifications**: Per-pane alerts with error/success/warning styles
- **Animation Engine**: Low-CPU candycane pattern at adaptive FPS
- **PostgreSQL Persistence**: Full session state survives crashes
- **ZDrive Integration**: Programmatic pane navigation and metadata
- **WebAssembly Plugins**: Extensible UI with WASM modules
- **Floating/Stacked Panes**: Advanced layout management
- **Web Client**: Browser-based terminal access

#### Interfaces

##### Terminal Interface
- **Protocol**: Terminal escape sequences (VT100/xterm compatible)
- **Description**: Primary user interaction via terminal emulator
- **Operations**:
  - Pane creation, resizing, navigation
  - Tab management
  - Layout loading and switching
  - Keybinding customization

##### Plugin API (WebAssembly)
- **Protocol**: WASM function calls with message passing
- **Description**: Extensibility interface for custom UI components
- **Specification**: Defined in `zellij-tile/` module
- **Event Types**:
  - `ModeUpdate` - Mode changes (normal, locked, pane, etc.)
  - `TabUpdate` - Tab state changes
  - `PaneUpdate` - Pane focus and layout changes
  - `Key` - Keyboard input events

##### Notification Bus
- **Protocol**: Internal message passing
- **Description**: Cross-pane notification delivery
- **Endpoints**:
  - `notify(pane_id, style, message)` - Send notification
  - `clear_notification(pane_id)` - Clear notification
  - Auto-clear on pane focus

##### Database API
- **Protocol**: PostgreSQL wire protocol
- **Description**: Session persistence and state management
- **Tables**:
  - `sessions` - Active session metadata
  - `panes` - Pane configurations and positions
  - `tabs` - Tab layout and ordering
  - `layouts` - Saved layout templates
- **Operations**:
  - Upsert session state on interval
  - Load session state on attach
  - Graceful degradation if DB unavailable

#### Dependencies

##### Containers Used
- **Redis**: Used by ZDrive for pane metadata (optional integration)
  - Communication: ZDrive CLI bridge
  - Purpose: Cross-process metadata sharing

##### External Systems
- **PostgreSQL**: Session persistence backend
  - Connection string via `DATABASE_URL` environment variable
  - Default: `postgres://perth:perth@localhost:5432/perth`
  - Write-behind caching for performance

- **SSH Server**: Remote session access (optional)
  - Docker container for E2E testing
  - Image: `ghcr.io/linuxserver/openssh-server`

#### Infrastructure

- **Deployment Config**:
  - Cargo workspace with 20+ member crates
  - Docker Compose for E2E testing: `/home/delorenj/code/33GOD/perth/trunk-main/docker-compose.yml`
  - Package metadata for .deb distribution

- **Binary Name**: `zellij` (aliased as `perth` in 33GOD)
- **Plugin Directory**: `~/.config/zellij/plugins/`
- **Configuration**: `~/.config/zellij/config.yaml`

- **Resources**:
  - Memory: 50-200MB depending on pane count
  - CPU: Adaptive (60fps animations degrade to 30fps under load)
  - Disk: Session state in PostgreSQL

- **Scaling**: Single-user sessions, multi-session support

---

### 3. Zellij Driver (zdrive)

- **Name**: Zellij Driver Context Manager
- **Description**: Cognitive context manager for Zellij with intent tracking and Redis persistence
- **Type**: CLI Tool / Context Manager
- **Technology**: Rust, Redis, Tokio, Anthropic/OpenAI/Ollama LLM integration
- **Deployment**: Native binary (`cargo build --release`)

#### Purpose

Zellij Driver (CLI: `zdrive`) is a workspace context manager that combines pane-first navigation with intent tracking. It records what developers and agents are working on, logs milestones, and maintains context across sessions using Redis-backed persistence. Provides programmatic control over Perth/Zellij workspaces with semantic pane naming and LLM-powered snapshot generation.

#### Components

This container implements:
- **CLI Interface**: Command parsing and user interaction (Clap)
- **Orchestrator**: Business logic coordination
- **State Manager**: Redis operations and intent history persistence
- **Zellij Driver**: Zellij action interface via CLI
- **Output Formatter**: Human-readable terminal formatting
- **Snapshot Engine**: LLM-powered context summarization
- **Filter System**: Secret detection and redaction
- **LLM Adapters**: Anthropic, OpenAI, Ollama integrations
- **Bloodbank Publisher**: Event publishing for activity tracking
- **Context Builder**: Pane context aggregation for LLM prompts

#### Key Features

- **Intent Logging**: Record work progress with typed entries (checkpoint, milestone, exploration)
- **Context History**: Review work history with timestamps and artifacts
- **Pane Navigation**: Semantic pane names with automatic tab switching
- **LLM Snapshots**: Automated summaries from work context
- **Agent Attribution**: Track human vs. agent work with `--source` flag
- **Secret Filtering**: Automatic redaction of API keys and credentials
- **Redis Persistence**: Metadata survives Zellij restarts
- **Bloodbank Integration**: Publish workspace events for cross-system visibility

#### Interfaces

##### CLI Interface
- **Protocol**: Command-line arguments (stdin/stdout)
- **Description**: Primary interaction for workspace management
- **Commands**:
  - **Pane Operations**:
    - `zdrive pane NAME [--tab TAB] [--meta KEY=VAL]` - Navigate or create pane
    - `zdrive pane log NAME SUMMARY [--type TYPE] [--source SOURCE] [--artifacts FILES]` - Log intent
    - `zdrive pane history NAME [--last N] [--format FORMAT]` - View history
    - `zdrive pane snapshot NAME` - Generate LLM summary
    - `zdrive pane info NAME` - Get pane metadata
  - **Tab Operations**:
    - `zdrive tab NAME` - Create or switch tab
    - `zdrive list` - List all tracked panes
    - `zdrive reconcile` - Sync state with Zellij
  - **Configuration**:
    - `zdrive config show` - Display configuration
    - `zdrive config set KEY VALUE` - Update setting
    - `zdrive config consent --grant/--revoke` - LLM data consent
  - **Migration**:
    - `zdrive migrate [--dry-run]` - Migrate from v1.0 schema

##### Redis Interface
- **Protocol**: Redis wire protocol (RESP)
- **Description**: Persistent storage for pane metadata and intent history
- **Data Model**:
  - **Pane Hash**: `perth:pane:<name>`
    - Fields: `session`, `tab`, `position`, `created_at`, `last_seen`, `last_accessed`, `meta:*`
  - **Intent History**: `perth:pane:<name>:history`
    - List of JSON-encoded IntentEntry objects (newest first)
    - Limited to 100 entries per pane (configurable)
  - **Tab Index**: `perth:tabs`
    - Set of known tab names
  - **Migration Keys**: `znav:*` (legacy v1.0 keyspace)

##### Zellij Control Interface
- **Protocol**: Zellij CLI via subprocess
- **Description**: Programmatic control of Zellij sessions
- **Operations**:
  - Pane creation and focus
  - Tab switching and creation
  - Layout queries
  - Action execution

##### LLM Interface
- **Protocol**: REST API (Anthropic/OpenAI) or HTTP (Ollama)
- **Description**: Context summarization for automated snapshots
- **Providers**:
  - **Anthropic**: Claude models via Messages API
  - **OpenAI**: GPT models via Chat Completions API
  - **Ollama**: Local models via HTTP endpoint
- **Request Format**: Structured prompts with pane context
- **Response Format**: Markdown summary with checkpoint entry

##### Bloodbank Event Publishing
- **Protocol**: RabbitMQ AMQP (optional)
- **Description**: Publish workspace events for distributed monitoring
- **Event Types**:
  - `workspace.pane.created` - New pane created
  - `workspace.pane.focused` - Pane received focus
  - `workspace.intent.logged` - Intent entry added
  - `workspace.snapshot.generated` - LLM snapshot completed

#### Dependencies

##### Containers Used
- **Redis**: Primary state persistence
  - Default: `redis://127.0.0.1:6379/`
  - Configurable via `~/.config/zellij-driver/config.toml`
  - Keyspace: `perth:*`

- **Perth (Zellij)**: Target workspace for control operations
  - Communication: Zellij CLI subprocess execution
  - Version check: Requires Zellij 0.39.0+

##### External Systems
- **Anthropic API**: Claude LLM for snapshots (optional)
  - Endpoint: `https://api.anthropic.com/v1/messages`
  - Authentication: `ANTHROPIC_API_KEY` environment variable
  - Model: `claude-sonnet-4-20250514` (configurable)

- **OpenAI API**: GPT models for snapshots (optional)
  - Endpoint: `https://api.openai.com/v1/chat/completions`
  - Authentication: `OPENAI_API_KEY` environment variable
  - Model: `gpt-4o` (configurable)

- **Ollama**: Local LLM endpoint (optional)
  - Endpoint: `http://localhost:11434` (configurable)
  - Model: `llama3.2` or any Ollama-compatible model
  - No authentication required

- **Bloodbank RabbitMQ**: Event publishing (optional)
  - Configured via `bloodbank.amqp_url` in config
  - Exchange: `bloodbank.workspace`

#### Infrastructure

- **Deployment Config**:
  - `Cargo.toml`: `/home/delorenj/code/33GOD/zellij-driver/trunk-main/Cargo.toml`
  - Binary: `target/release/zdrive`
  - Installation: Symlink to `~/.local/bin/zdrive`

- **Configuration File**: `~/.config/zellij-driver/config.toml`
  ```toml
  redis_url = "redis://127.0.0.1:6379/"

  [llm]
  provider = "anthropic"  # or "openai", "ollama"
  model = "claude-sonnet-4-20250514"

  [bloodbank]
  amqp_url = "amqp://localhost:5672"
  ```

- **Resources**:
  - Memory: <30MB typical
  - CPU: Burst for LLM requests, idle otherwise
  - Disk: Minimal (config file only, data in Redis)

- **Scaling**: Single-user CLI, concurrent operations supported

---

### 4. Redis Persistence Layer

- **Name**: Redis State Store
- **Description**: In-memory data structure store for workspace context and pane metadata
- **Type**: Database (Key-Value Store)
- **Technology**: Redis 6.0+
- **Deployment**: Docker container or native Redis server

#### Purpose

Provides high-performance, low-latency persistence for workspace context metadata managed by Zellij Driver. Stores pane records, tab indices, and intent history with support for complex data structures (hashes, lists, sets). Ensures workspace state survives Zellij restarts while maintaining sub-millisecond access times.

#### Key Features

- In-memory storage with optional persistence (RDB/AOF)
- Redis Protocol (RESP) for client communication
- Data structure support: Strings, Hashes, Lists, Sets
- Atomic operations for concurrent access
- Keyspace expiration policies (optional)

#### Interfaces

##### Redis Protocol (RESP)
- **Protocol**: Redis Serialization Protocol (RESP)
- **Description**: Standard Redis client-server communication
- **Port**: 6379 (default)
- **Authentication**: Optional (configured via `requirepass`)
- **Commands Used**:
  - `HSET`, `HGETALL`, `HDEL` - Pane hash operations
  - `LPUSH`, `LRANGE`, `LTRIM` - Intent history lists
  - `SADD`, `SMEMBERS` - Tab index sets
  - `KEYS`, `SCAN` - Keyspace queries
  - `DEL` - Record deletion

#### Dependencies

##### Containers Used
- **Zellij Driver (zdrive)**: Primary client
  - Connection: `redis` crate with `aio` + `tokio-comp` features
  - Multiplexed async connection for high concurrency

##### External Systems
None. Redis operates as a standalone service.

#### Infrastructure

- **Deployment Config**:
  - Docker: `docker run -d -p 6379:6379 redis:7-alpine`
  - Native: System package manager (`apt install redis-server`)

- **Configuration**:
  - File: `/etc/redis/redis.conf` (Linux) or via command-line args
  - Persistence: RDB snapshots or AOF (append-only file)
  - Memory: `maxmemory` policy for eviction

- **Resources**:
  - Memory: 50-500MB depending on pane count and history depth
  - CPU: Minimal (<5% typical)
  - Disk: RDB/AOF files if persistence enabled

- **Scaling**: Single-instance for workspace management (Redis Cluster not required)

---

### 5. PostgreSQL Database

- **Name**: PostgreSQL Relational Database
- **Description**: Persistent relational storage for iMi worktree metadata and Perth session state
- **Type**: Database (Relational)
- **Technology**: PostgreSQL 16+
- **Deployment**: Docker container or native PostgreSQL server

#### Purpose

Provides durable, ACID-compliant storage for structured worktree and session data. Supports complex queries, transactions, and concurrent access from multiple iMi and Perth instances. Enables historical tracking, agent coordination, and session recovery across system restarts.

#### Key Features

- Full ACID compliance for data integrity
- JSON/JSONB columns for flexible metadata
- Advanced indexing for fast queries
- Foreign key constraints for referential integrity
- Trigger support for automated timestamps
- Connection pooling via SQLx

#### Interfaces

##### PostgreSQL Wire Protocol
- **Protocol**: PostgreSQL wire protocol (version 3.0)
- **Description**: Standard PostgreSQL client-server communication
- **Port**: 5432 (default)
- **Authentication**: Password-based (SCRAM-SHA-256)
- **SSL**: TLS 1.2+ supported (optional)

##### iMi Schema
- **Database**: `imi` (or configured name)
- **Connection String**: Via `DATABASE_URL` environment variable
- **Tables**:
  - `projects` - Repository metadata (id, name, remote_origin, default_branch, trunk_path)
  - `worktrees` - Worktree records (id, project_id, type_id, name, branch_name, path, agent_id)
  - `worktree_types` - Type definitions (id, name, branch_prefix, worktree_prefix)
  - `agent_activities` - Activity logs (id, agent_id, worktree_id, activity_type, file_path)
- **Migrations**: SQLx migrations in `iMi/trunk-main/migrations/`

##### Perth Schema
- **Database**: `perth` (or configured name)
- **Connection String**: Via `DATABASE_URL` environment variable
- **Tables**:
  - `sessions` - Session metadata (session_id, name, created_at, last_attached)
  - `panes` - Pane configurations (id, session_id, tab_id, pane_id, layout)
  - `tabs` - Tab layout (id, session_id, name, position)
  - `layouts` - Saved layouts (id, name, definition)
- **Features**: Write-behind caching, graceful degradation

#### Dependencies

##### Containers Used
- **iMi CLI Tool**: SQLx async client with connection pooling
- **Perth**: SQLx async client with write-behind cache

##### External Systems
None. PostgreSQL operates as a standalone service.

#### Infrastructure

- **Deployment Config**:
  - Docker: `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16-alpine`
  - Native: System package manager (`apt install postgresql-16`)

- **Configuration**:
  - File: `/etc/postgresql/16/main/postgresql.conf`
  - Connection limits: `max_connections` (default 100)
  - Shared buffers: 25% of available RAM recommended

- **Resources**:
  - Memory: 256MB-2GB depending on dataset size
  - CPU: 1-2 cores typical
  - Disk: 1-10GB for typical workspace history

- **Scaling**: Single-instance for workspace management (replication optional for HA)

---

## Container Diagram

```mermaid
C4Container
    title Container Diagram for Workspace Management Domain

    Person(developer, "Developer", "Human developer using workspace")
    Person(agent, "AI Agent", "Autonomous agent working in codebase")

    System_Boundary(workspace, "Workspace Management Domain") {
        Container(imi, "iMi CLI Tool", "Rust, Tokio, Git2", "Git worktree manager with intelligent workflows and agent coordination")
        Container(perth, "Perth Multiplexer", "Rust, WASM, Zellij Fork", "Terminal IDE with notifications, animations, and session persistence")
        Container(zdrive, "Zellij Driver", "Rust, Tokio, Redis", "Context manager with intent tracking and LLM snapshots")
        ContainerDb(redis, "Redis Store", "Redis 6+", "Fast in-memory workspace context and pane metadata")
        ContainerDb(postgres, "PostgreSQL", "PostgreSQL 16+", "Persistent worktree history and session state")
    }

    System_Ext(github, "GitHub API", "Project creation and PR reviews")
    System_Ext(anthropic, "Anthropic API", "Claude LLM for context snapshots")
    System_Ext(bloodbank, "Bloodbank MQ", "RabbitMQ event bus for workspace events")
    System_Ext(filesystem, "File System", "Git repositories and configuration")

    Rel(developer, imi, "Manages worktrees", "CLI")
    Rel(developer, perth, "Works in terminal", "Terminal UI")
    Rel(developer, zdrive, "Tracks intent", "CLI")
    Rel(agent, imi, "Creates worktrees", "CLI")
    Rel(agent, zdrive, "Logs progress", "CLI --source agent")

    Rel(imi, postgres, "Persists worktree metadata", "SQLx/PostgreSQL")
    Rel(imi, filesystem, "Manages git worktrees", "git2/Git CLI")
    Rel(imi, github, "Fetches PRs, creates projects", "REST/HTTPS")

    Rel(perth, postgres, "Persists session state", "SQLx/PostgreSQL")
    Rel(perth, filesystem, "Renders terminal output", "PTY/TTY")
    Rel(perth, zdrive, "Receives control commands", "Zellij CLI")

    Rel(zdrive, redis, "Stores pane metadata", "Redis RESP")
    Rel(zdrive, perth, "Controls panes and tabs", "Subprocess/CLI")
    Rel(zdrive, anthropic, "Generates snapshots", "REST/HTTPS")
    Rel(zdrive, bloodbank, "Publishes events", "AMQP")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

### Container Relationships

**Developer Workflow**:
1. Developer runs `iMi feat user-auth` to create feature worktree
2. iMi creates Git worktree and records metadata in PostgreSQL
3. Developer opens Perth (Zellij) in the new worktree directory
4. Perth loads session state from PostgreSQL
5. Developer uses `zdrive pane api-server` to navigate to API pane
6. zdrive stores pane metadata in Redis and focuses the pane in Perth
7. Developer runs `zdrive pane log api-server "Implemented OAuth"`
8. zdrive stores intent entry in Redis and publishes event to Bloodbank

**Agent Workflow**:
1. Agent calls `iMi add fix auth-bug` to create bugfix worktree
2. Agent navigates with `zdrive pane bugfix --tab backend`
3. Agent logs progress: `zdrive pane log bugfix "Fixed token validation" --source agent --artifacts src/auth.rs`
4. Agent commits changes and continues work
5. Periodic `zdrive pane snapshot bugfix` generates LLM summary of work context
6. Snapshot sent to Anthropic API, result stored in Redis intent history

**Cross-System Integration**:
- **iMi → GitHub**: Fetch PR details for review worktrees, create projects from templates
- **Perth → PostgreSQL**: Write-behind caching of session state every 5 seconds
- **zdrive → Redis**: Sub-millisecond pane metadata access for navigation
- **zdrive → Anthropic**: Context summarization for automated snapshots
- **zdrive → Bloodbank**: Publish workspace events for distributed monitoring

---

## API Specifications

### iMi CLI Interface

The iMi CLI provides structured JSON output for programmatic integration:

**Command**: `iMi --json {command}`

**Common Response Format**:
```json
{
  "success": true,
  "data": { /* command-specific data */ },
  "error": null
}
```

**Example: List Worktrees**
```bash
$ iMi --json list
{
  "success": true,
  "data": {
    "worktrees": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "feat-user-auth",
        "type": "feat",
        "branch": "feat/user-auth",
        "path": "/home/user/code/project/feat-user-auth",
        "agent_id": "agent-007",
        "created_at": "2026-01-20T10:30:00Z",
        "has_uncommitted_changes": true,
        "ahead_of_trunk": 3
      }
    ]
  }
}
```

**Example: Worktree Status**
```bash
$ iMi --json status
{
  "success": true,
  "data": {
    "repository": "my-project",
    "trunk": {
      "path": "/home/user/code/my-project/trunk-main",
      "branch": "main",
      "ahead": 0,
      "behind": 0
    },
    "worktrees": [
      {
        "name": "feat-api-v2",
        "type": "feat",
        "dirty_files": 5,
        "ahead": 2,
        "behind": 0,
        "last_commit": "Add endpoint validation"
      }
    ]
  }
}
```

### Zellij Driver CLI Interface

**Command**: `zdrive {command} [options]`

**Intent Entry Structure**:
```json
{
  "timestamp": "2026-01-29T15:45:32Z",
  "entry_type": "checkpoint",
  "source": "human",
  "summary": "Implemented OAuth integration",
  "artifacts": [
    "/path/to/src/auth.rs",
    "/path/to/tests/auth_test.rs"
  ]
}
```

**History Output (JSON)**:
```bash
$ zdrive pane history api-server --format json --last 5
{
  "pane_name": "api-server",
  "session": "main",
  "tab": "backend",
  "total_entries": 42,
  "entries": [
    {
      "timestamp": "2026-01-29T15:45:32Z",
      "entry_type": "milestone",
      "source": "human",
      "summary": "Released API v2.0",
      "artifacts": ["CHANGELOG.md"]
    },
    {
      "timestamp": "2026-01-29T14:20:15Z",
      "entry_type": "checkpoint",
      "source": "agent",
      "summary": "Added rate limiting middleware",
      "artifacts": ["src/middleware/rate_limit.rs"]
    }
  ]
}
```

**Context Format (for LLM injection)**:
```bash
$ zdrive pane history api-server --format context
# Workspace Context: api-server

Session: main / Tab: backend
Total Entries: 42
Time Range: 2026-01-28 10:00 → 2026-01-29 15:45 (1d 5h)

## Recent Activity (Last 5 Entries)

★ [15:45] Released API v2.0
  Artifacts: CHANGELOG.md

● [14:20] [AGENT] Added rate limiting middleware
  Artifacts: src/middleware/rate_limit.rs

● [13:10] Implemented authentication hooks
  Artifacts: src/auth.rs, tests/auth_test.rs

## Current State
Working on API v2.0 release. Latest milestone: released. Recent agent work: rate limiting.

## Suggested Next Steps
- Verify deployment pipeline
- Update API documentation
- Monitor error rates post-release
```

**Pane Info Output**:
```bash
$ zdrive pane info api-server
{
  "pane_name": "api-server",
  "status": "active",
  "session": "main",
  "tab": "backend",
  "pane_id": "3",
  "created_at": "2026-01-28T10:00:00Z",
  "last_seen": "2026-01-29T15:50:00Z",
  "last_accessed": "2026-01-29T15:45:32Z",
  "metadata": {
    "project": "myapp",
    "owner": "developer"
  }
}
```

### Perth Notification Interface

Perth's notification system is controlled via Zellij actions (not exposed as REST API). Notifications are triggered programmatically via plugins or external tools.

**Notification Styles**:
- `error` - Red border with pulse animation
- `success` - Green border with fade-in
- `warning` - Yellow border with blink

**Example (via Zellij action)**:
```bash
# Via zellij CLI (requires Perth fork)
zellij action notify --pane-id 3 --style error --message "Build failed"
```

**Auto-clear Behavior**:
- Notifications automatically clear when pane receives focus
- Can be manually cleared via `zellij action clear-notification --pane-id 3`

### Redis Data Structures

**Pane Record** (`perth:pane:<name>`):
```
HGETALL perth:pane:api-server
{
  "session": "main",
  "tab": "backend",
  "pane_id": "3",
  "created_at": "2026-01-28T10:00:00Z",
  "last_seen": "2026-01-29T15:50:00Z",
  "last_accessed": "2026-01-29T15:45:32Z",
  "stale": "false",
  "meta:project": "myapp",
  "meta:owner": "developer"
}
```

**Intent History** (`perth:pane:<name>:history`):
```
LRANGE perth:pane:api-server:history 0 4
[
  "{\"timestamp\":\"2026-01-29T15:45:32Z\",\"entry_type\":\"milestone\",\"source\":\"human\",\"summary\":\"Released API v2.0\",\"artifacts\":[\"CHANGELOG.md\"]}",
  "{\"timestamp\":\"2026-01-29T14:20:15Z\",\"entry_type\":\"checkpoint\",\"source\":\"agent\",\"summary\":\"Added rate limiting\",\"artifacts\":[\"src/middleware/rate_limit.rs\"]}"
]
```

**Tab Index** (`perth:tabs`):
```
SMEMBERS perth:tabs
["backend", "frontend", "database", "monitoring"]
```

### PostgreSQL Schemas

**iMi Database Schema** (excerpt):

```sql
-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    remote_origin TEXT NOT NULL,
    default_branch VARCHAR(100) NOT NULL DEFAULT 'main',
    trunk_path TEXT NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE
);

-- Worktrees table
CREATE TABLE worktrees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    type_id INTEGER REFERENCES worktree_types(id),
    name VARCHAR(255) NOT NULL,
    branch_name VARCHAR(255) NOT NULL,
    path TEXT NOT NULL,
    agent_id VARCHAR(100),
    has_uncommitted_changes BOOLEAN,
    uncommitted_files_count INTEGER,
    ahead_of_trunk INTEGER,
    behind_trunk INTEGER,
    last_commit_hash VARCHAR(40),
    last_commit_message TEXT,
    last_sync_at TIMESTAMPTZ,
    merged_at TIMESTAMPTZ,
    merged_by VARCHAR(100),
    merge_commit_hash VARCHAR(40),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE,
    UNIQUE(project_id, name)
);

-- Agent activities table
CREATE TABLE agent_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(100) NOT NULL,
    worktree_id UUID REFERENCES worktrees(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    file_path TEXT,
    description TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_worktrees_project_id ON worktrees(project_id);
CREATE INDEX idx_worktrees_active ON worktrees(active) WHERE active = TRUE;
CREATE INDEX idx_agent_activities_worktree_id ON agent_activities(worktree_id);
CREATE INDEX idx_agent_activities_created_at ON agent_activities(created_at DESC);
```

**Perth Database Schema** (conceptual - actual implementation in Zellij codebase):

```sql
-- Sessions table
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_attached TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Panes table
CREATE TABLE panes (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    tab_id UUID REFERENCES tabs(id) ON DELETE CASCADE,
    pane_id VARCHAR(50) NOT NULL,
    layout JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabs table
CREATE TABLE tabs (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    position INTEGER NOT NULL,
    layout JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Technology Stack Summary

### Container Technologies

| Container | Language | Runtime | Framework | Database | External APIs |
|-----------|----------|---------|-----------|----------|---------------|
| **iMi** | Rust 2021 | Tokio async | Clap CLI | PostgreSQL/SQLite | GitHub REST API |
| **Perth** | Rust 2021 | Tokio async | Zellij/WASM | PostgreSQL | None |
| **zdrive** | Rust 2021 | Tokio async | Clap CLI | Redis | Anthropic/OpenAI/Ollama, Bloodbank AMQP |
| **Redis** | C | Single-threaded event loop | Native | N/A | N/A |
| **PostgreSQL** | C | Multi-process | Native | N/A | N/A |

### Key Rust Dependencies

**iMi**:
- `clap 4.5` - CLI framework
- `tokio 1.37` - Async runtime
- `git2 0.18` - Git operations
- `sqlx 0.7` - PostgreSQL/SQLite client
- `notify 6.1` - File system monitoring
- `octocrab 0.38` - GitHub API client

**Perth (Zellij)**:
- `tokio 1.38` - Async runtime
- `sqlx 0.7` - PostgreSQL client
- `prost 0.11` - Protocol Buffers
- `termwiz 0.23` - Terminal rendering
- `notify-debouncer-full 0.3` - File watching

**zdrive**:
- `clap 4.5` - CLI framework
- `tokio 1.37` - Async runtime
- `redis 0.27` - Redis client with async
- `reqwest 0.12` - HTTP client for LLM APIs
- `lapin 2.5` - RabbitMQ AMQP client
- `serde_json 1.0` - JSON serialization

---

## Deployment Architecture

### Development Environment

```
Developer Workstation
├── iMi binary (~10MB)
│   └── PostgreSQL (localhost:5432)
├── Perth binary (~15MB)
│   └── PostgreSQL (localhost:5432)
├── zdrive binary (~8MB)
│   └── Redis (localhost:6379)
└── Git repositories
    └── Worktree directories
```

### Production Environment (Optional Multi-User)

```
Shared Server
├── PostgreSQL (persistent storage)
│   ├── iMi database
│   └── Perth database
├── Redis (session cache)
│   └── Pane metadata
└── Multiple user sessions
    ├── User 1: iMi + Perth + zdrive
    ├── User 2: iMi + Perth + zdrive
    └── User N: iMi + Perth + zdrive
```

### Container Communication Flow

```
┌─────────────┐
│  Developer  │
└──────┬──────┘
       │ CLI commands
       ↓
┌─────────────────────────────────────────┐
│              iMi CLI Tool               │
│  ┌────────────────────────────────────┐ │
│  │ Worktree Manager                   │ │
│  │ - Create/remove worktrees          │ │
│  │ - Monitor file changes             │ │
│  │ - Track agent activities           │ │
│  └────────────────────────────────────┘ │
└──────┬────────────────────┬─────────────┘
       │                    │
       │ SQLx              │ git2/Git CLI
       ↓                    ↓
┌──────────────┐      ┌──────────────┐
│  PostgreSQL  │      │  File System │
│  - Worktree  │      │  - .git/     │
│    metadata  │      │  - Worktrees │
│  - Agent     │      │  - Symlinks  │
│    activities│      └──────────────┘
└──────────────┘

┌─────────────┐
│  Developer  │
│  AI Agent   │
└──────┬──────┘
       │ Terminal UI / CLI
       ↓
┌─────────────────────────────────────────┐
│         Perth (Zellij Fork)             │
│  ┌────────────────────────────────────┐ │
│  │ Server + Client                    │ │
│  │ - Pane multiplexing                │ │
│  │ - Visual notifications             │ │
│  │ - Animation engine                 │ │
│  │ - Plugin system (WASM)             │ │
│  └────────────────────────────────────┘ │
└──────┬────────────────────┬─────────────┘
       │                    │
       │ SQLx              │ PTY/TTY
       ↓                    ↓
┌──────────────┐      ┌──────────────┐
│  PostgreSQL  │      │  Terminal    │
│  - Session   │      │  - Render    │
│    state     │      │  - Input     │
│  - Layouts   │      └──────────────┘
└──────────────┘

┌─────────────┐
│ Dev/Agent   │
└──────┬──────┘
       │ CLI commands
       ↓
┌─────────────────────────────────────────┐
│        Zellij Driver (zdrive)           │
│  ┌────────────────────────────────────┐ │
│  │ Orchestrator                       │ │
│  │ - Pane navigation                  │ │
│  │ - Intent logging                   │ │
│  │ - LLM snapshots                    │ │
│  │ - Event publishing                 │ │
│  └────────────────────────────────────┘ │
└──┬───┬───────────────┬──────────────┬───┘
   │   │               │              │
   │   │ Redis RESP   │ Subprocess   │ AMQP
   ↓   ↓               ↓              ↓
┌────┐ ┌──────┐  ┌────────┐  ┌──────────┐
│API │ │Redis │  │ Perth  │  │Bloodbank │
│LLM │ │Store │  │ Zellij │  │  MQ      │
└────┘ └──────┘  └────────┘  └──────────┘
```

---

## Security Considerations

### iMi Security
- **PostgreSQL Credentials**: Stored in connection string (env var or config file)
- **GitHub Tokens**: OAuth token in environment variable (`GITHUB_TOKEN`)
- **File System Access**: Full access to Git repositories (by design)
- **Recommendations**:
  - Use environment variables for sensitive credentials
  - Restrict file permissions on config files (0600)
  - Run iMi with user-level permissions (not root)

### Perth Security
- **PostgreSQL Credentials**: Connection string via `DATABASE_URL`
- **Session Data**: Sensitive terminal output persisted to database
- **Plugin System**: WASM sandbox prevents malicious plugins from system access
- **Recommendations**:
  - Encrypt PostgreSQL connection with TLS
  - Implement database access controls (row-level security)
  - Audit plugin sources before installation

### zdrive Security
- **Redis Access**: No authentication by default (localhost only)
- **LLM Data Transmission**: Pane context sent to third-party APIs
- **Secret Filtering**: Automatic redaction of API keys, passwords, tokens
- **Consent Mechanism**: Explicit user consent required for LLM snapshots
- **Recommendations**:
  - Enable Redis authentication (`requirepass` in redis.conf)
  - Use Ollama for sensitive projects (local LLM, no data transmission)
  - Review filtered secrets regularly (`zdrive config show`)
  - Revoke LLM consent after use (`zdrive config consent --revoke`)

### Redis Security
- **Network Exposure**: Bind to localhost only (default)
- **Authentication**: Optional password authentication
- **Recommendations**:
  - Enable `requirepass` for production
  - Use firewall rules to restrict access
  - Enable TLS for remote connections

### PostgreSQL Security
- **Authentication**: SCRAM-SHA-256 password hashing
- **Network Exposure**: Bind to localhost or use TLS
- **Recommendations**:
  - Use strong passwords for database users
  - Enable TLS for connections (`sslmode=require`)
  - Implement role-based access control (RBAC)
  - Regular backups with encryption

---

## Performance Characteristics

### iMi Performance
- **Worktree Creation**: 100-500ms (Git overhead)
- **Status Queries**: 50-200ms (Git status calls)
- **Monitoring**: Real-time (<50ms latency)
- **Database Queries**: <10ms for typical operations
- **Bottlenecks**: Git operations (worktree create/remove)
- **Optimization**: Parallel worktree operations, connection pooling

### Perth Performance
- **Rendering**: 60fps (adaptive to 30fps under load)
- **Session Load**: 100-500ms from PostgreSQL
- **Pane Switching**: <50ms
- **Database Writes**: Write-behind cache (non-blocking)
- **Bottlenecks**: Terminal rendering, animation updates
- **Optimization**: Dirty region rendering, adaptive FPS

### zdrive Performance
- **Pane Navigation**: <100ms
- **Intent Logging**: <50ms (Redis write)
- **History Queries**: <20ms (Redis list read)
- **LLM Snapshots**: 2-10 seconds (network latency)
- **Bottlenecks**: LLM API calls, Redis network latency
- **Optimization**: Multiplexed Redis connections, snapshot caching

### Redis Performance
- **Read Latency**: Sub-millisecond
- **Write Latency**: Sub-millisecond
- **Throughput**: 50K+ ops/sec (single-threaded)
- **Memory Usage**: ~50-500MB typical
- **Bottlenecks**: Network latency (if remote)
- **Optimization**: Pipelining, connection pooling

### PostgreSQL Performance
- **Query Latency**: 5-50ms depending on complexity
- **Throughput**: 1K-10K transactions/sec
- **Memory Usage**: 256MB-2GB
- **Bottlenecks**: Disk I/O, index maintenance
- **Optimization**: Indexes on foreign keys, connection pooling, query optimization

---

## Monitoring and Observability

### iMi Monitoring
- **Built-in**: `iMi monitor` real-time file change monitoring
- **Logs**: Standard output (can redirect to file)
- **Metrics**: Agent activity counts, worktree status
- **Health Check**: `iMi doctor` command
- **Recommended Tools**: None (single-user CLI)

### Perth Monitoring
- **Built-in**: Session manager plugin shows active sessions
- **Logs**: Zellij log file (`~/.cache/zellij/zellij.log`)
- **Metrics**: Pane count, tab count, session uptime
- **Health Check**: `zellij list-sessions`
- **Recommended Tools**: System monitoring (htop, top)

### zdrive Monitoring
- **Built-in**: `zdrive list` shows tracked panes
- **Logs**: Standard error output
- **Metrics**: Intent entry counts, pane history depth
- **Health Check**: `zdrive config show`
- **Events**: Bloodbank integration for distributed monitoring
- **Recommended Tools**: Bloodbank dashboard (if enabled)

### Redis Monitoring
- **Built-in**: `redis-cli INFO` command
- **Metrics**: Memory usage, connected clients, operations/sec
- **Logs**: Redis log file (configurable location)
- **Health Check**: `redis-cli PING`
- **Recommended Tools**: Redis Insight, Grafana + Redis exporter

### PostgreSQL Monitoring
- **Built-in**: `pg_stat_*` system views
- **Metrics**: Connection count, transaction rate, cache hit ratio
- **Logs**: PostgreSQL log files (CSV or text format)
- **Health Check**: `pg_isready` command
- **Recommended Tools**: pgAdmin, Grafana + PostgreSQL exporter

---

## Future Enhancements

### Planned Features (Roadmap)

**iMi**:
- Multi-repository management (cross-project worktrees)
- Remote agent coordination via message queue
- Worktree templates for common workflows
- Integration with Perth for automatic pane creation

**Perth**:
- Dashboard plugin (Milestone 1: Holocene Dashboard)
- Bloodbank/iMi/Jelmore adapters (Sprint 2)
- Template registry for layout instantiation (Sprint 3)
- Real-time collaboration features

**zdrive**:
- Multi-session support (track panes across Zellij sessions)
- Advanced LLM prompting for domain-specific snapshots
- Integration with iMi for worktree-aware context
- Pane dependency graphs (track which panes interact)

### Integration Opportunities

- **iMi ↔ zdrive**: Automatic pane creation when iMi creates worktree
- **Perth ↔ iMi**: Worktree-aware tab naming and layouts
- **zdrive ↔ Bloodbank**: Enhanced event streaming for distributed teams
- **Perth ↔ zdrive**: Notification triggers on intent milestones

---

## Conclusion

The Workspace Management domain provides a comprehensive, integrated solution for managing terminal workspaces in distributed, multi-agent development environments. The three primary containers (iMi, Perth, zdrive) work together with Redis and PostgreSQL persistence to deliver:

- **Intelligent Git worktree management** with agent coordination (iMi)
- **Advanced terminal multiplexing** with visual feedback and session persistence (Perth)
- **Cognitive context tracking** with LLM-powered summarization (zdrive)

This architecture supports the 33GOD platform's vision of seamless human-agent collaboration by providing robust workspace isolation, persistent context, and real-time visibility into development activities. All containers are built in Rust for performance, safety, and reliability, with asynchronous I/O for high concurrency and low latency.

**Key architectural principles**:
- **Container isolation**: Each container has a single, well-defined responsibility
- **Polyglot persistence**: PostgreSQL for durable structured data, Redis for fast session state
- **API-first design**: All containers expose programmatic interfaces (CLI, Redis protocol, PostgreSQL wire protocol)
- **Graceful degradation**: Optional features (LLM snapshots, Bloodbank events) don't block core functionality
- **Developer experience**: Minimal configuration, opinionated defaults, clear error messages

This C4 Container documentation provides the technical foundation for understanding deployment architecture, API contracts, and inter-container communication patterns in the Workspace Management domain.
