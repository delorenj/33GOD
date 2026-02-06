# hookd - GOD Document

> **Guaranteed Organizational Document** - Developer-facing reference for hookd
>
> **Last Updated**: 2026-02-06
> **Domain**: Development Tools / Infrastructure
> **Status**: Development

---

## Product Overview

hookd is the **tool mutation event pipeline** for the 33GOD ecosystem. It captures every file write, edit, and command execution performed by AI coding agents (Claude Code, Gemini CLI, etc.) and publishes them as typed, enriched events to Bloodbank. Downstream consumers (mutation-ledger) embed these events into per-project Qdrant vector collections for semantic search over a project's mutation history.

Think of hookd as the "git log for AI actions" - except instead of commits, it captures individual tool invocations with full context: which file, which branch, which agent, what changed.

**Key Capabilities:**
- Fire-and-forget hook event capture (never blocks the agent)
- Git context enrichment (branch, SHA, remote URL) with TTL-cached lookups
- Per-project semantic embedding via Qdrant for intelligent mutation querying
- Dual-mode CLI: structured queries (SQLite) and semantic search (Qdrant)
- Agent-agnostic design (Claude Code today, extensible to Gemini CLI, Codex, etc.)

---

## Architecture Position

```mermaid
graph TB
    subgraph "Agent Layer"
        CC[Claude Code<br/>Agent Hooks]
        GC[Gemini CLI<br/>Future]
        CX[Codex CLI<br/>Future]
    end

    subgraph "hookd Pipeline"
        HE[hookd-emit<br/>Shell Emitter]
        HD[hookd daemon<br/>Rust, Unix Socket]
        BB[Bloodbank<br/>RabbitMQ]
        ML[mutation-ledger<br/>Python Consumer]
    end

    subgraph "Storage"
        QD[Qdrant<br/>Vector Embeddings]
        SQ[SQLite<br/>Local Cache]
    end

    subgraph "Query"
        HQ[hookd-query<br/>CLI]
    end

    CC -->|stdin JSON| HE
    GC -.->|future| HE
    CX -.->|future| HE
    HE -->|Unix socket| HD
    HD -->|AMQP publish| BB
    BB -->|tool.mutation.*| ML
    ML -->|embed| QD
    ML -->|cache| SQ
    HQ -->|semantic search| QD
    HQ -->|structured query| SQ
```

**Role in Pipeline**: hookd sits at the boundary between AI agent tool execution and the 33GOD event bus. It transforms raw hook payloads into enriched, typed events that the rest of the ecosystem can consume, query, and reason about.

---

## Components

### hookd-emit (Shell Emitter)
- **Path**: `bin/hookd-emit`
- **Language**: Bash
- **Dependencies**: `jq`, `socat`
- **Purpose**: Lightweight, fire-and-forget script that reads agent hook stdin, wraps it in a JSON envelope, and writes to the hookd Unix socket
- **Critical property**: Exits 0 on ALL failure paths (empty stdin, missing socket, jq errors, socat failures). Must never block the calling agent.

### hookd daemon (Enrichment + Publisher)
- **Path**: `src/main.rs`
- **Language**: Rust (tokio async)
- **Dependencies**: lapin (AMQP), serde, chrono, tracing, uuid
- **Purpose**: Listens on a Unix socket, enriches raw envelopes with git context (branch, SHA, remote URL), extracts file paths and line counts, publishes typed `ToolMutationEvent` to Bloodbank
- **Enrichment**: Runs `git rev-parse`, `git branch`, `git remote` with a 30s TTL cache per git root
- **Publishing**: AMQP topic exchange `bloodbank.events.v1`, routing key `tool.mutation.{tool_name}`

### mutation-ledger (Semantic Consumer)
- **Path**: `../services/mutation-ledger/`
- **Language**: Python 3.11+
- **Dependencies**: aio-pika, fastembed, qdrant-client, pydantic, structlog
- **Purpose**: Consumes `tool.mutation.#` events, runs semantic enrichment (intent, domain, language classification), generates natural language summaries, embeds into per-project Qdrant collections, caches in SQLite

### hookd-query (CLI)
- **Path**: `../services/mutation-ledger/src/query.py`
- **Purpose**: Dual-mode query interface
  - `--since 1h` / `--file auth.py` / `--agent claude-123`: Structured SQLite queries
  - `--search "authentication changes"`: Semantic search via Qdrant

---

## Event Contracts

### Bloodbank Events Emitted

| Event Name | Routing Key | Payload Schema | Trigger Condition |
|------------|-------------|----------------|-------------------|
| Tool Write | `tool.mutation.write` | `ToolMutationEvent` | Agent creates a file via Write tool |
| Tool Edit | `tool.mutation.edit` | `ToolMutationEvent` | Agent modifies a file via Edit tool |
| Tool MultiEdit | `tool.mutation.multiedit` | `ToolMutationEvent` | Agent modifies a file via MultiEdit tool |
| Tool Bash | `tool.mutation.bash` | `ToolMutationEvent` | Agent executes a shell command |
| Tool NotebookEdit | `tool.mutation.notebookedit` | `ToolMutationEvent` | Agent edits a Jupyter notebook |

### Bloodbank Events Consumed

| Event Name | Routing Key | Handler | Purpose |
|------------|-------------|---------|---------|
| All tool mutations | `tool.mutation.#` | `MutationLedgerConsumer._process_message()` | Enrich, embed in Qdrant, cache in SQLite |

### ToolMutationEvent Schema

```json
{
  "event_type": "tool.mutation.write",
  "hook_type": "post_tool_use",
  "tool_name": "Write",
  "agent_id": "claude-session-abc123",
  "repo": {
    "git_root": "/home/user/code/project",
    "branch": "feat/new-feature",
    "head_sha": "a1b2c3d4e5f6",
    "remote_url": "git@github.com:user/project.git"
  },
  "file_path": "/home/user/code/project/src/auth.py",
  "file_ext": "py",
  "lines_changed": 42,
  "raw_payload": { "tool_input": { "...": "..." } },
  "timestamp": "2026-02-06T09:15:00Z",
  "source_pid": 12345,
  "correlation_id": "uuid-v4"
}
```

### Enriched Mutation (Internal)

The mutation-ledger adds semantic metadata before embedding:

| Field | Example | Description |
|-------|---------|-------------|
| `intent` | `new-file`, `modification`, `test`, `configuration`, `ci-cd` | What kind of change |
| `domain` | `implementation`, `api-layer`, `testing`, `infrastructure` | Architectural layer |
| `language` | `rust`, `python`, `typescript` | Language/technology |
| `summary` | `"Agent claude-123 created 'src/auth.py' (python) changing 42 lines for new file on branch 'feat/auth'"` | Natural language summary (vectorized) |

---

## Supported Hooks

hookd is designed to capture events from AI coding agent hook systems. Currently supported:

### Claude Code Hooks

Claude Code provides 7 hook points. hookd currently targets the mutation-relevant subset:

| Hook Point | Supported | Description | hookd Usage |
|------------|-----------|-------------|-------------|
| `PreToolUse` | Planned | Before any tool executes | Future: pre-mutation context capture |
| `PostToolUse` | **Active** | After tool completes | Primary mutation capture point |
| `PreCompact` | No | Before context compaction | Not relevant to mutations |
| `PostCompact` | No | After context compaction | Not relevant to mutations |
| `SessionStart` | Planned | Agent session begins | Future: session correlation |
| `Stop` | Planned | Agent session ends | Future: session summary events |
| `SubagentStop` | No | Subagent completes | Not relevant to mutations |

### Currently Configured Tool Matchers

These matchers are active in the hookd example config (`config/hooks.example.json`):

| Matcher Pattern | Hook Point | Tool(s) Captured |
|----------------|------------|------------------|
| `Write\|Edit\|MultiEdit\|NotebookEdit` | PostToolUse | File creation and modification |
| `Bash` | PostToolUse | Shell command execution |
| `.*` | PreToolUse | All tools (planned) |

### Agent Compatibility Matrix

| Agent | Hook System | Status | Integration Path |
|-------|------------|--------|------------------|
| **Claude Code** | `.claude/settings.json` hooks | **Active** | `hookd-emit` via `command` hook type |
| **Gemini CLI** | Plugin system | **Planned** | Adapter needed for Gemini's plugin format |
| **Codex CLI** | Custom hooks | **Planned** | Adapter for OpenAI Codex hook format |
| **AmazonQ** | Extension points | **Planned** | Q Developer customization hooks |
| **Cursor** | Extension API | **Planned** | VS Code extension integration |

---

## Non-Event Interfaces

### CLI: hookd-emit

```bash
# Fire-and-forget mutation capture
echo '{"tool_input":{"file_path":"/src/main.rs","content":"..."}}' | hookd-emit post_tool_use Write

# Bash command capture
echo '{"tool_input":{"command":"cargo test"}}' | hookd-emit post_tool_use Bash
```

### CLI: hookd-query

```bash
# Structured queries (SQLite)
hookd-query --since 1h                              # Last hour of mutations
hookd-query --since 7d --file auth.py               # Auth file changes this week
hookd-query --branch feat/hookd --format json        # Branch-specific, JSON output

# Semantic search (Qdrant)
hookd-query --search "authentication changes"        # Natural language query
hookd-query --search "database migrations" --limit 5 # Top 5 results
hookd-query --search "test failures" --agent claude-123  # Agent-specific
```

### Daemon Control

```bash
# Start daemon (reads config from env vars)
HOOKD_SOCKET=/run/user/1000/hookd.sock \
HOOKD_AMQP_URL=amqp://user:pass@host:5672/ \
  ./target/release/hookd

# Environment variables
HOOKD_SOCKET          # Unix socket path (default: /run/user/$UID/hookd.sock)
HOOKD_AMQP_URL        # AMQP connection URL (also reads RABBITMQ_URL, RABBIT_URL)
HOOKD_EXCHANGE         # Exchange name (default: bloodbank.events.v1)
HOOKD_PID_FILE         # PID file path
HOOKD_GIT_CACHE_TTL    # Git context cache TTL in seconds (default: 30)
HOOKD_BUFFER_SIZE      # Event buffer size (default: 1000)
CLAUDE_AGENT_ID        # Agent identifier for events
RUST_LOG               # Logging level (e.g., hookd=debug)
```

---

## Technical Deep-Dive

### Technology Stack
- **hookd-emit**: Bash + jq + socat
- **hookd daemon**: Rust 1.85+, tokio, lapin (AMQP), serde, tracing
- **mutation-ledger**: Python 3.11+, aio-pika, fastembed (BAAI/bge-small-en-v1.5, 384 dims), qdrant-client
- **Storage**: Qdrant (primary, semantic), SQLite (secondary, structured cache)

### Data Flow

```
Agent Hook (stdin JSON)
    │
    ▼
hookd-emit (bash)
    │  Wraps in HookEnvelope {event_type, tool_name, payload, timestamp, pid}
    │  Writes to Unix socket via socat
    ▼
hookd daemon (rust)
    │  Deserializes HookEnvelope
    │  Extracts file_path from payload (tool_input.file_path / .path / .notebook_path)
    │  Resolves git context (branch, sha, remote_url) with 30s cache
    │  Estimates lines_changed from content/new_string
    │  Generates correlation_id (UUIDv4)
    │  Publishes ToolMutationEvent to Bloodbank
    ▼
RabbitMQ (bloodbank.events.v1)
    │  Routing key: tool.mutation.{tool_name}
    ▼
mutation-ledger (python)
    │  Deserializes ToolMutationEvent
    │  classify_intent() → new-file, modification, test, config, docs, ci-cd, ...
    │  classify_domain() → implementation, api-layer, testing, data-layer, ...
    │  compute_language() → rust, python, typescript, ...
    │  generate_summary() → natural language for embedding
    │  Embeds summary via fastembed (BAAI/bge-small-en-v1.5, 384 dims)
    │  Upserts to Qdrant collection: mutations-{repo_name}-{hash}
    │  Caches in SQLite: {git_root}/.hookd/mutations.db
    ▼
Qdrant (per-project collection)
    │  Cosine similarity search
    ▼
hookd-query (python CLI)
```

### Qdrant Collection Naming

Collections are derived from the repo identity for portability:

```
mutations-{repo_name}-{sha256_short_hash}
```

Example: `mutations-33god-3060c791` for `https://github.com/delorenj/33GOD.git`

Uses `remote_url` when available (portable across machines), falls back to `git_root`.

### Configuration

**mutation-ledger config** (`src/config.py`):

| Setting | Env Var | Default |
|---------|---------|---------|
| RabbitMQ URL | `MUTATION_LEDGER_RABBITMQ_URL` / `RABBIT_URL` | `amqp://guest:guest@localhost:5672/` |
| Exchange | `MUTATION_LEDGER_EXCHANGE_NAME` | `bloodbank.events.v1` |
| Queue | `MUTATION_LEDGER_QUEUE_NAME` | `services.hookd.mutation_ledger` |
| Qdrant URL | `MUTATION_LEDGER_QDRANT_URL` | `http://172.19.0.22:6333` |
| Qdrant API Key | `QDRANT_API_KEY` | (required) |
| Embedding Model | `MUTATION_LEDGER_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` |
| SQLite Cache | `MUTATION_LEDGER_SQLITE_CACHE_ENABLED` | `true` |

---

## Development

### Setup

```bash
# Build hookd daemon
cd hookd
cargo build --release

# Install mutation-ledger deps
cd ../services/mutation-ledger
pip install aio-pika pydantic-settings structlog aiosqlite qdrant-client fastembed
```

### Running Locally

```bash
# Terminal 1: Start hookd daemon
RABBIT_URL=amqp://user:pass@host:5672/ \
HOOKD_SOCKET=/tmp/hookd-dev.sock \
RUST_LOG=hookd=debug \
  ./target/release/hookd

# Terminal 2: Start mutation-ledger consumer
cd services/mutation-ledger
RABBIT_URL=amqp://user:pass@host:5672/ \
QDRANT_API_KEY=your-key \
  python -m src.consumer

# Terminal 3: Send a test event
echo '{"tool_input":{"file_path":"/tmp/test.py","content":"hello"}}' | \
  HOOKD_SOCKET=/tmp/hookd-dev.sock bin/hookd-emit post_tool_use Write
```

### Testing

```bash
# Unit tests (enrichment logic)
cd services/mutation-ledger
python -m pytest tests/test_enrichment.py -v

# Integration tests (Qdrant store + search)
python tests/test_integration.py

# hookd-emit shell tests
cd hookd
bash tests/test_hookd_emit.sh
```

---

## Deployment

hookd is designed to run as a user-level daemon (not containerized), since it needs access to the host filesystem for git context resolution.

**Recommended setup:**
1. Build release binary: `cargo build --release`
2. Place `bin/hookd-emit` on PATH
3. Run daemon via systemd user service or process manager
4. Configure agent hooks to pipe through `hookd-emit`
5. Run mutation-ledger as a standalone Python service (containerizable)

---

## References

- **Domain Doc**: `docs/domains/development-tools/GOD.md`
- **System Doc**: `docs/GOD.md`
- **Service Registry**: `services/registry.yaml` (hookd-producer, mutation-ledger)
- **Source (daemon)**: `hookd/src/`
- **Source (consumer)**: `services/mutation-ledger/src/`
- **Hook Config Reference**: `hookd/config/hooks.example.json`
