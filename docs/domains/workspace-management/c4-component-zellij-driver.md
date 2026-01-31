# C4 Component Level: Zellij Driver - Cognitive Context Manager

## Overview
- **Name**: Zellij Driver (zdrive)
- **Description**: Cognitive context manager for Zellij terminals with intent history tracking
- **Type**: Service Library + CLI Tool
- **Technology**: Rust, Redis, RabbitMQ, LLM Integration
- **Version**: 0.1.0

## Purpose

Zellij Driver (zdrive) provides cognitive context management for terminal sessions by tracking developer intent, preserving historical context, and enabling AI-assisted workflows. It acts as a "memory layer" for terminal workspaces, allowing developers and AI agents to understand what work has been done, restore context after interruptions, and coordinate complex workflows.

The system uses Redis for fast state tracking, RabbitMQ for async event coordination, and integrates with multiple LLM providers (Anthropic, OpenAI, Ollama) for context-aware assistance.

## Software Features

### Pane State Tracking
- **State Persistence**: Track pane state in Redis with metadata
- **Lifecycle Tracking**: Monitor pane creation, access, and staleness
- **Metadata Storage**: Store arbitrary key-value metadata per pane
- **Session Association**: Link panes to sessions and tabs
- **Stale Detection**: Mark inactive panes as stale for cleanup

### Intent History Management
- **Intent Logging**: Record developer intent with timestamps
- **Intent Types**: Classify intents (milestone, checkpoint, exploration)
- **Artifact Tracking**: Track files, URLs, and resources referenced
- **Progress Tracking**: Record goal deltas and commands run
- **Source Attribution**: Track manual, automated, or agent-generated intents

### Tab Tracking
- **Tab Registry**: Maintain registry of all tabs across sessions
- **Tab Metadata**: Store tab-specific context and metadata
- **Tab Lifecycle**: Track tab creation and deletion
- **Session Grouping**: Group tabs by session for context

### Snapshot & Restore
- **Context Snapshots**: Capture full context at a point in time
- **Session Restoration**: Restore previous work context
- **Intent Replay**: Review historical intent timeline
- **Filter & Search**: Query intent history with filters

### LLM Integration
- **Multi-Provider**: Support for Anthropic, OpenAI, Ollama
- **Circuit Breaker**: Resilient LLM calls with failure handling
- **Context Injection**: Provide terminal context to LLMs
- **Intent Suggestions**: AI-suggested next steps based on history
- **Noop Mode**: Disable LLM for testing/debugging

### Workflow Orchestration
- **Event Publishing**: Publish workflow events to RabbitMQ
- **Async Coordination**: Coordinate distributed workflows
- **State Synchronization**: Sync state across agents
- **Bloodbank Integration**: Connect to knowledge base for context retrieval

### Filter Engine
- **Regex Filtering**: Filter intents by pattern matching
- **Time Range Queries**: Query intents within time windows
- **Type Filtering**: Filter by intent type (milestone, checkpoint, exploration)
- **Metadata Queries**: Query by metadata key-value pairs

## Code Elements

This component contains the following Rust modules:

- **src/lib.rs** - Public library API
- **src/main.rs** - CLI entry point and command dispatch
- **src/cli.rs** - Command-line interface definitions (Clap)
- **src/state.rs** - Redis state management (panes, tabs, intents)
- **src/types.rs** - Core data types (IntentEntry, PaneRecord, TabRecord)
- **src/orchestrator.rs** - Workflow orchestration and coordination
- **src/llm/** - LLM integration layer
  - `mod.rs` - LLM provider trait
  - `anthropic.rs` - Anthropic Claude integration
  - `openai.rs` - OpenAI API integration
  - `ollama.rs` - Ollama local LLM integration
  - `circuit_breaker.rs` - Resilient LLM call wrapper
  - `noop.rs` - No-op provider for testing
- **src/snapshot.rs** - Context snapshot and restore
- **src/restore.rs** - Session restoration logic
- **src/filter.rs** - Intent filtering and search
- **src/output.rs** - Terminal output formatting
- **src/zellij.rs** - Zellij-specific integrations
- **src/bloodbank.rs** - Bloodbank knowledge base client
- **src/config.rs** - Configuration management
- **src/context.rs** - Context detection and extraction

## Component Architecture

```mermaid
C4Component
    title Component Diagram for Zellij Driver Cognitive Context Manager

    Container_Boundary(zdrive, "Zellij Driver") {
        Component(cli, "CLI Handler", "Rust/Clap", "Parse commands and dispatch actions")
        Component(state_mgr, "State Manager", "Redis Client", "Pane/tab/intent state in Redis")
        Component(orchestrator, "Orchestrator", "Rust/Tokio", "Workflow orchestration and coordination")
        Component(llm_router, "LLM Router", "Rust", "Route to appropriate LLM provider")
        Component(llm_anthropic, "Anthropic Provider", "Rust/Reqwest", "Claude API integration")
        Component(llm_openai, "OpenAI Provider", "Rust/Reqwest", "OpenAI API integration")
        Component(llm_ollama, "Ollama Provider", "Rust/Reqwest", "Local LLM integration")
        Component(circuit_breaker, "Circuit Breaker", "Rust", "LLM failure resilience")
        Component(snapshot, "Snapshot Manager", "Rust", "Context capture and restore")
        Component(restore, "Restore Manager", "Rust", "Session restoration logic")
        Component(filter, "Filter Engine", "Regex", "Intent filtering and search")
        Component(bloodbank, "Bloodbank Client", "Rust/Reqwest", "Knowledge base retrieval")
        Component(config, "Config Manager", "TOML", "Configuration loading")
        Component(output, "Output Formatter", "Rust/Colored", "Terminal output rendering")
    }

    ContainerDb(redis, "Redis", "Key-Value Store", "Fast state cache and intent history")
    ContainerQueue(rabbitmq, "RabbitMQ", "Message Queue", "Async workflow events")
    System_Ext(anthropic, "Anthropic API", "Claude", "AI assistant")
    System_Ext(openai, "OpenAI API", "GPT", "AI assistant")
    System_Ext(ollama, "Ollama", "Local LLM", "Self-hosted AI")
    System_Ext(bloodbank_api, "Bloodbank", "Knowledge Base", "Context retrieval")
    System_Ext(perth, "Perth", "Terminal", "Terminal session source")

    ' Core relationships
    Rel(cli, state_mgr, "Uses", "State operations")
    Rel(cli, orchestrator, "Triggers", "Workflows")
    Rel(orchestrator, state_mgr, "Reads/Writes", "State")
    Rel(orchestrator, llm_router, "Queries", "AI assistance")
    Rel(llm_router, circuit_breaker, "Wraps calls with", "Resilience")
    Rel(circuit_breaker, llm_anthropic, "Routes to", "API calls")
    Rel(circuit_breaker, llm_openai, "Routes to", "API calls")
    Rel(circuit_breaker, llm_ollama, "Routes to", "API calls")
    Rel(snapshot, state_mgr, "Captures", "State snapshot")
    Rel(restore, state_mgr, "Restores", "Historical state")
    Rel(filter, state_mgr, "Queries", "Intent history")
    Rel(orchestrator, bloodbank, "Retrieves", "Knowledge")
    Rel(cli, config, "Loads", "Settings")
    Rel(cli, output, "Formats", "Terminal output")

    ' External relationships
    Rel(state_mgr, redis, "Reads/Writes", "Redis protocol")
    Rel(orchestrator, rabbitmq, "Publishes", "AMQP")
    Rel(llm_anthropic, anthropic, "Calls", "HTTPS/REST")
    Rel(llm_openai, openai, "Calls", "HTTPS/REST")
    Rel(llm_ollama, ollama, "Calls", "HTTP")
    Rel(bloodbank, bloodbank_api, "Calls", "HTTPS/REST")
    Rel(perth, state_mgr, "Tracks panes in", "Redis keys")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## Interfaces

### Command-Line Interface

**Protocol**: CLI (Command-Line Interface)
**Description**: Primary user interface for intent tracking and context management

**Operations**:
- `zdrive log <summary>` - Log a new intent entry
- `zdrive log --type milestone <summary>` - Log milestone intent
- `zdrive history [--limit N]` - Show intent history
- `zdrive history --filter <pattern>` - Filter intent history
- `zdrive panes` - List all tracked panes
- `zdrive panes --session <name>` - List panes for session
- `zdrive touch <pane-name>` - Mark pane as accessed
- `zdrive snapshot` - Create context snapshot
- `zdrive restore <snapshot-id>` - Restore context from snapshot
- `zdrive assist <query>` - Get AI assistance with context
- `zdrive config` - Show current configuration

### Redis Interface

**Protocol**: Redis (async protocol)
**Description**: Fast state storage and retrieval

**Key Patterns**:
- `znav:pane:<pane-name>` - Hash with pane metadata
  - Fields: `session`, `tab`, `pane_id`, `created_at`, `last_seen`, `last_accessed`, `stale`
  - Meta fields: `meta:<key>` for arbitrary metadata
- `znav:tab:<tab-name>` - Hash with tab metadata
- `znav:intent:<pane-name>` - List of intent entry IDs (JSON)
- `znav:intent:entry:<id>` - Hash with intent entry details

**Operations**:
- `HGETALL znav:pane:<name>` - Get pane state
- `HSET znav:pane:<name> <field> <value>` - Update pane field
- `RPUSH znav:intent:<pane-name> <entry-json>` - Append intent entry
- `LRANGE znav:intent:<pane-name> 0 -1` - Get all intents
- `SCAN 0 MATCH znav:pane:*` - List all panes

### RabbitMQ Interface

**Protocol**: AMQP (via lapin)
**Description**: Async event publishing for workflow coordination

**Exchange**: `zdrive.events`
**Routing Keys**:
- `intent.logged` - New intent entry logged
- `pane.created` - New pane created
- `pane.accessed` - Pane accessed
- `session.snapshot` - Session snapshot created
- `session.restored` - Session restored

**Event Payload** (JSON):
```json
{
  "event_type": "intent.logged",
  "timestamp": "2026-01-29T12:00:00Z",
  "pane_name": "feat-new-feature",
  "intent_id": "uuid",
  "summary": "Implemented auth middleware",
  "entry_type": "checkpoint",
  "source": "manual"
}
```

### LLM Provider Interface

**Protocol**: HTTPS/REST (provider-specific)
**Description**: AI assistance with context injection

**Providers**:
1. **Anthropic Claude**
   - Endpoint: `https://api.anthropic.com/v1/messages`
   - Models: `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`
   - Auth: `x-api-key` header

2. **OpenAI**
   - Endpoint: `https://api.openai.com/v1/chat/completions`
   - Models: `gpt-4`, `gpt-3.5-turbo`
   - Auth: `Authorization: Bearer <token>`

3. **Ollama**
   - Endpoint: `http://localhost:11434/api/generate`
   - Models: `llama2`, `mistral`, `codellama`
   - Auth: None (local)

**Context Injection**:
- Intent history included in system prompt
- Recent artifacts listed
- Current pane state summarized
- Goal deltas highlighted

### Bloodbank Interface

**Protocol**: HTTPS/REST
**Description**: Knowledge base retrieval for context enhancement

**Operations**:
- `GET /api/context?pane=<name>` - Get context for pane
- `POST /api/store` - Store knowledge entry
- `GET /api/search?q=<query>` - Search knowledge base

## Dependencies

### Internal Components
- **CLI Handler** uses **State Manager** for all state operations
- **Orchestrator** uses **State Manager** for state tracking
- **Orchestrator** uses **LLM Router** for AI assistance
- **LLM Router** uses **Circuit Breaker** for resilience
- **Circuit Breaker** wraps **LLM Providers** (Anthropic, OpenAI, Ollama)
- **Snapshot Manager** uses **State Manager** for capture
- **Restore Manager** uses **State Manager** for restoration
- **Filter Engine** queries **State Manager** for intent history

### External Systems
- **Redis**: Primary state store for panes, tabs, and intents
- **RabbitMQ**: Async event coordination (optional)
- **Anthropic API**: Claude AI assistance (optional)
- **OpenAI API**: GPT AI assistance (optional)
- **Ollama**: Local LLM (optional)
- **Bloodbank**: Knowledge base for context retrieval (optional)
- **Perth**: Terminal session source (tracks panes)

### Rust Crates
- `redis` v0.27 - Async Redis client
- `lapin` v2.5 - RabbitMQ AMQP client
- `tokio` v1.37 - Async runtime (multi-threaded)
- `reqwest` v0.12 - HTTP client (JSON features)
- `clap` v4.5 - CLI framework (derive)
- `serde` + `serde_json` - Serialization
- `uuid` v1.0 - UUID generation (v4)
- `chrono` v0.4 - Timestamp handling
- `regex` v1.10 - Pattern matching
- `toml` v0.8 - Configuration parsing
- `colored` v2.1 - Terminal output coloring
- `anyhow` v1.0 - Error handling
- `async-trait` v0.1 - Async traits

## Data Models

### IntentEntry
```rust
struct IntentEntry {
    id: Uuid,
    timestamp: DateTime<Utc>,
    summary: String,
    entry_type: IntentType,  // Milestone, Checkpoint, Exploration
    artifacts: Vec<String>,  // Files, URLs, etc.
    commands_run: Option<usize>,
    goal_delta: Option<String>,
    source: IntentSource,  // Manual, Automated, Agent
}

enum IntentType {
    Milestone,    // Major accomplishment
    Checkpoint,   // Regular progress marker (default)
    Exploration,  // Investigative activity
}

enum IntentSource {
    Manual,       // User explicitly logged (default)
    Automated,    // System-generated
    Agent,        // Created by AI agent
}
```

### PaneRecord
```rust
struct PaneRecord {
    pane_name: String,
    session: String,
    tab: String,
    pane_id: Option<String>,
    created_at: String,  // ISO 8601
    last_seen: String,
    last_accessed: String,
    meta: HashMap<String, String>,  // Arbitrary metadata
    stale: bool,
}
```

### TabRecord
```rust
struct TabRecord {
    tab_name: String,
    session: String,
    created_at: String,
    last_accessed: String,
    meta: HashMap<String, String>,
}
```

### SnapshotRecord
```rust
struct SnapshotRecord {
    id: Uuid,
    timestamp: DateTime<Utc>,
    panes: Vec<PaneRecord>,
    intents: Vec<IntentEntry>,
    metadata: HashMap<String, String>,
}
```

## Configuration

### Config File: `~/.config/zellij-driver/config.toml`

```toml
[redis]
url = "redis://localhost:6379"
# Connection timeout in seconds
timeout = 5

[rabbitmq]
url = "amqp://guest:guest@localhost:5672"
# Optional - disable if not using async workflows
enabled = false

[llm]
# Default provider: "anthropic", "openai", "ollama", "noop"
default_provider = "anthropic"

[llm.anthropic]
api_key = "${ANTHROPIC_API_KEY}"
model = "claude-3-sonnet-20240229"

[llm.openai]
api_key = "${OPENAI_API_KEY}"
model = "gpt-4"

[llm.ollama]
base_url = "http://localhost:11434"
model = "llama2"

[bloodbank]
base_url = "http://localhost:8080"
# Optional - disable if not using knowledge base
enabled = false

[intent]
# History limit per pane (default 100)
history_limit = 100
# Auto-cleanup stale panes after N days
stale_threshold_days = 30
```

## Error Handling

### Error Types
```rust
// Using anyhow::Result for error propagation
type Result<T> = anyhow::Result<T>;

// Common error contexts:
- Redis connection failures
- RabbitMQ connection failures
- LLM API errors (rate limits, network errors)
- Invalid configuration
- Serialization errors
```

### Circuit Breaker Pattern
- **Closed**: LLM calls succeed, normal operation
- **Open**: LLM calls fail repeatedly, bypass for N seconds
- **Half-Open**: Test if LLM recovered, allow one call

Parameters:
- Failure threshold: 3 consecutive failures
- Timeout: 30 seconds
- Reset timeout: 60 seconds

## Security

### API Keys
- **Anthropic API Key**: `ANTHROPIC_API_KEY` environment variable
- **OpenAI API Key**: `OPENAI_API_KEY` environment variable
- **Redis Password**: In connection URL if required
- **RabbitMQ Credentials**: In connection URL

### Data Privacy
- Intent history may contain sensitive information
- Redis data not encrypted at rest (use Redis encryption if needed)
- LLM API calls send context to external services (opt-out with noop provider)

### Network Security
- Redis connections should use TLS in production
- RabbitMQ connections should use AMQPS in production
- LLM API calls use HTTPS

## Performance

### Redis Performance
- Multiplexed async connections for high concurrency
- Key namespacing prevents collisions
- Intent history limited to prevent unbounded growth (default 100 per pane)
- SCAN used instead of KEYS for listing (non-blocking)

### LLM Performance
- Circuit breaker prevents cascading failures
- Async LLM calls don't block main thread
- Context size optimized (only recent intents)
- Provider failover supported

### Memory Management
- Intent history pruned by limit
- Stale panes cleaned up automatically
- No in-memory caching (Redis is cache)

## Testing

### Unit Tests
- Mock Redis client for state manager tests
- Noop LLM provider for orchestrator tests
- Regex filter engine tests with known patterns

### Integration Tests
- Real Redis instance (Docker)
- Mock LLM responses
- End-to-end intent logging flow

### Test Utilities
```rust
#[cfg(test)]
mod tests {
    use tokio_test;

    // Mock Redis
    // Mock LLM providers
    // Test intent lifecycle
    // Test circuit breaker
}
```

## Deployment

### Prerequisites
- Rust 2021 edition
- Redis 6+
- RabbitMQ 3.8+ (optional)
- LLM API keys (optional)

### Build
```bash
cargo build --release
# Binary: target/release/zdrive
```

### Installation
```bash
cargo install --path .
# OR
cp target/release/zdrive ~/.local/bin/
```

### Redis Setup
```bash
# Start Redis (Docker)
docker run -d -p 6379:6379 redis:latest

# Or install locally
sudo apt-get install redis-server
```

### RabbitMQ Setup (Optional)
```bash
# Start RabbitMQ (Docker)
docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:management

# Or install locally
sudo apt-get install rabbitmq-server
```

### Configuration
```bash
mkdir -p ~/.config/zellij-driver
cat > ~/.config/zellij-driver/config.toml <<EOF
[redis]
url = "redis://localhost:6379"

[llm]
default_provider = "noop"  # Or configure your provider
EOF
```

### Integration with Perth
```bash
# Perth automatically tracks panes to Redis
# No additional configuration needed
# Ensure Redis URL matches in both configs
```

---

**Component Version**: 0.1.0
**Last Updated**: 2026-01-29
**Rust Edition**: 2021
**Status**: Active Development
**License**: MIT
