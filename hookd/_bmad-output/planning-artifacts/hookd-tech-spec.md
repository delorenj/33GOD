---
title: "hookd - Technical Specification"
type: tech-spec
status: draft
date: 2026-02-06
component: hookd
stepsCompleted: []
sprint: 1
stories:
  - id: HOOKD-1
    title: "hookd-emit CLI"
    status: pending
    size: S
  - id: HOOKD-2
    title: "hookd Rust daemon"
    status: pending
    size: L
  - id: HOOKD-3
    title: "Bloodbank event schema + publishing"
    status: pending
    size: M
  - id: HOOKD-4
    title: "mutation-ledger consumer"
    status: pending
    size: M
  - id: HOOKD-5
    title: "Claude Code hook config"
    status: pending
    size: S
  - id: HOOKD-6
    title: "Integration test + validation"
    status: pending
    size: M
---

# hookd Technical Specification

## Architecture Overview

```
Claude Code Hook
       │
       ▼
  hookd-emit          (shell script or Rust micro-binary)
       │ stdin JSON → Unix socket write
       ▼
     hookd             (Rust daemon, long-running)
       │ enrich with repo context
       │ publish typed event
       ▼
   Bloodbank           (RabbitMQ)
       │
       ├──► mutation-ledger    (FastStream consumer → SQLite)
       └──► [future consumers]
```

## Component Specifications

---

### HOOKD-1: hookd-emit CLI

**Size:** S | **Blocked by:** nothing

**What:** A minimal binary/script that reads tool output from stdin, packages it with the event type and tool name from CLI args, and writes the JSON envelope to a Unix domain socket.

**Interface:**
```bash
# Called from Claude Code hook config
# stdin: tool JSON output (piped by Claude Code)
hookd-emit post_tool_use write
hookd-emit post_tool_use edit
hookd-emit pre_tool_use bash
```

**Behavior:**
1. Read all of stdin into a buffer
2. Construct JSON envelope:
   ```json
   {
     "event_type": "post_tool_use",
     "tool_name": "write",
     "payload": <raw stdin JSON>,
     "timestamp": "<ISO 8601>",
     "pid": <calling process PID>
   }
   ```
3. Connect to Unix socket at `$HOOKD_SOCKET` (default: `/run/user/$UID/hookd.sock`)
4. Write the JSON envelope as a single newline-delimited message
5. Close connection and exit immediately (fire-and-forget)

**Error handling:**
- If socket unavailable: exit 0 silently (never block the hook)
- If stdin empty: exit 0 silently
- Stderr only for `HOOKD_DEBUG=1`

**Implementation choice:** Start as a shell script for speed of delivery. Rewrite in Rust later if the ~2ms shell overhead matters.

```bash
#!/usr/bin/env bash
# hookd-emit - fire-and-forget hook event emitter
set -euo pipefail

EVENT_TYPE="${1:?Usage: hookd-emit <event_type> <tool_name>}"
TOOL_NAME="${2:?Usage: hookd-emit <event_type> <tool_name>}"
SOCKET="${HOOKD_SOCKET:-/run/user/$(id -u)/hookd.sock}"

PAYLOAD=$(cat)
[ -z "$PAYLOAD" ] && exit 0
[ ! -S "$SOCKET" ] && exit 0

jq -nc \
  --arg et "$EVENT_TYPE" \
  --arg tn "$TOOL_NAME" \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" \
  --argjson pid "$$" \
  --argjson payload "$PAYLOAD" \
  '{event_type: $et, tool_name: $tn, payload: $payload, timestamp: $ts, pid: $pid}' \
  | socat - UNIX-CONNECT:"$SOCKET" 2>/dev/null

exit 0
```

**Acceptance Criteria:**
- Given a valid JSON payload on stdin and a running hookd, when `hookd-emit post_tool_use write` is called, then the daemon receives a well-formed envelope
- Given no hookd running (socket missing), when hookd-emit is called, then it exits 0 with no output
- Given empty stdin, when hookd-emit is called, then it exits 0 immediately
- Wall clock time for hookd-emit execution: < 5ms (excluding stdin read)

**Files:**
- `/home/delorenj/code/33GOD/hookd/bin/hookd-emit` (the script)

---

### HOOKD-2: hookd Rust Daemon

**Size:** L | **Blocked by:** HOOKD-1 (for testing), HOOKD-3 (event schema)

**What:** A long-running Rust daemon that listens on a Unix domain socket, receives hook event envelopes from `hookd-emit`, enriches them with repository context, and publishes typed events to Bloodbank via AMQP.

**Responsibilities:**
1. Listen on Unix domain socket (async, tokio)
2. Accept connections, read newline-delimited JSON
3. Deserialize into `HookEnvelope`
4. Enrich with `RepoContext` (git root, branch, HEAD sha, agent ID)
5. Publish to Bloodbank exchange as `ToolMutationEvent`
6. Maintain persistent AMQP connection (reconnect on failure)

**Key Data Structures:**

```rust
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Raw envelope from hookd-emit
#[derive(Debug, Deserialize)]
struct HookEnvelope {
    event_type: String,
    tool_name: String,
    payload: Value,
    timestamp: DateTime<Utc>,
    pid: u32,
}

/// Git context gathered by hookd
#[derive(Debug, Serialize)]
struct RepoContext {
    git_root: String,
    branch: String,
    head_sha: String,
    remote_url: Option<String>,
}

/// Published to Bloodbank
#[derive(Debug, Serialize)]
struct ToolMutationEvent {
    event_type: String,      // "tool.mutation.write", "tool.mutation.edit"
    hook_type: String,        // "post_tool_use", "pre_tool_use"
    agent_id: String,         // from CLAUDE_AGENT_ID env or "unknown"
    repo: RepoContext,
    file_path: Option<String>,  // extracted from payload
    file_ext: Option<String>,
    lines_changed: Option<u32>,
    raw_payload: Value,
    timestamp: DateTime<Utc>,
    source_pid: u32,
}
```

**Payload extraction logic:**
- `file_path`: try `payload.tool_input.file_path`, then `payload.tool_input.path`
- `file_ext`: derive from file_path via `Path::extension()`
- `lines_changed`: try `payload.tool_input.new_string` or `payload.tool_input.content`, count newlines

**RepoContext resolution:**
- Cache per git root (don't shell out to git on every event)
- Refresh cache on branch/HEAD change (check every 30s or on cache miss)
- Git commands: `git rev-parse --show-toplevel`, `git branch --show-current`, `git rev-parse HEAD`
- `agent_id`: read from `$CLAUDE_AGENT_ID` env var, default to `"unknown"`

**AMQP publishing:**
- Exchange: `hookd.events` (topic exchange)
- Routing key: `tool.mutation.{tool_name}` (e.g., `tool.mutation.write`)
- Message: JSON-serialized `ToolMutationEvent`
- Persistent delivery mode
- Connection: maintain single persistent connection via `lapin` crate
- Reconnect with exponential backoff on failure

**Daemon lifecycle:**
- Startup: create socket, connect to AMQP, start listening
- Graceful shutdown on SIGTERM/SIGINT: drain in-flight events, close connections
- PID file at `/run/user/$UID/hookd.pid`
- Systemd user service unit for auto-start

**Acceptance Criteria:**
- Given hookd is running and receives a valid envelope, when it processes the event, then a ToolMutationEvent appears on the `hookd.events` exchange with correct routing key
- Given hookd receives an envelope with a Write tool payload, when it extracts file_path, then the path matches `tool_input.file_path` from the original payload
- Given the AMQP connection drops, when a new event arrives, then hookd reconnects and publishes without data loss (buffer up to 1000 events in memory)
- Given hookd starts, when the socket path already exists (stale), then it removes the stale socket and creates a new one
- Git context cache invalidates and refreshes correctly when branch changes

**Crate dependencies:**
- `tokio` (async runtime)
- `lapin` (AMQP)
- `serde` / `serde_json`
- `chrono`
- `tracing` / `tracing-subscriber` (structured logging)

**Files:**
- `/home/delorenj/code/33GOD/hookd/Cargo.toml`
- `/home/delorenj/code/33GOD/hookd/src/main.rs`
- `/home/delorenj/code/33GOD/hookd/src/envelope.rs` (deserialization)
- `/home/delorenj/code/33GOD/hookd/src/enrichment.rs` (repo context + payload extraction)
- `/home/delorenj/code/33GOD/hookd/src/publisher.rs` (AMQP connection + publish)
- `/home/delorenj/code/33GOD/hookd/src/config.rs` (socket path, AMQP URL, etc.)

---

### HOOKD-3: Bloodbank Event Schema + Exchange Setup

**Size:** M | **Blocked by:** nothing

**What:** Define the `hookd.events` exchange in Bloodbank and register hookd as a producer in the 33GOD service registry.

**Tasks:**
1. Add `hookd.events` topic exchange to Bloodbank exchange definitions
2. Register `hookd` as a producer in `/home/delorenj/code/33GOD/services/registry.yaml`
3. Create the exchange via RabbitMQ management API or Bloodbank provisioning

**Registry entry:**
```yaml
hookd:
  type: producer
  description: "Tool mutation event pipeline for Claude Code hooks"
  exchange: hookd.events
  routing_keys:
    - "tool.mutation.write"
    - "tool.mutation.edit"
    - "tool.mutation.multiedit"
    - "tool.mutation.bash"
    - "tool.mutation.*"
  event_schema: hookd/ToolMutationEvent
  component_path: hookd/
```

**Acceptance Criteria:**
- Given Bloodbank is running, when hookd publishes to `hookd.events`, then messages are routable via `tool.mutation.*` patterns
- hookd appears in service registry with correct exchange and routing key metadata

**Files:**
- `/home/delorenj/code/33GOD/services/registry.yaml` (update)
- `/home/delorenj/code/33GOD/bloodbank/` (exchange provisioning if needed)

---

### HOOKD-4: mutation-ledger Consumer

**Size:** M | **Blocked by:** HOOKD-3

**What:** A FastStream consumer service that subscribes to `tool.mutation.*` events from Bloodbank and stores them as append-only facts in per-repo SQLite databases.

**Architecture:**
- Python service using FastStream with RabbitMQ broker
- One SQLite database per git repo root (stored at `{git_root}/.hookd/mutations.db`)
- Append-only: never update or delete rows

**SQLite Schema:**
```sql
CREATE TABLE IF NOT EXISTS mutations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,        -- "tool.mutation.write"
    hook_type TEXT NOT NULL,          -- "post_tool_use"
    tool_name TEXT NOT NULL,          -- "write", "edit"
    agent_id TEXT NOT NULL,
    file_path TEXT,
    file_ext TEXT,
    lines_changed INTEGER,
    branch TEXT NOT NULL,
    head_sha TEXT NOT NULL,
    raw_payload TEXT NOT NULL,        -- JSON string
    event_timestamp TEXT NOT NULL,    -- ISO 8601
    received_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_mutations_file ON mutations(file_path);
CREATE INDEX IF NOT EXISTS idx_mutations_timestamp ON mutations(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_mutations_agent ON mutations(agent_id);
CREATE INDEX IF NOT EXISTS idx_mutations_branch ON mutations(branch);
```

**Consumer logic:**
1. Subscribe to `hookd.events` exchange, binding `tool.mutation.#`
2. Deserialize `ToolMutationEvent` from message body
3. Resolve SQLite DB path: `{event.repo.git_root}/.hookd/mutations.db`
4. Create DB + tables if not exists
5. Insert row
6. ACK message

**Query interface (CLI):**
```bash
# Built into the mutation-ledger service or as a separate script
hookd-query --repo . --since 1h
hookd-query --repo . --file src/main.rs
hookd-query --repo . --agent claude-abc123
hookd-query --repo . --branch feature/hookd --format json
```

**Acceptance Criteria:**
- Given a `tool.mutation.write` event is published to Bloodbank, when mutation-ledger processes it, then a row appears in the correct repo's SQLite DB
- Given multiple repos produce events, when queried, then each repo's DB contains only its own events
- Given `hookd-query --repo . --since 1h`, when there are 5 mutations in the last hour, then all 5 are returned in chronological order
- DB file created at `{git_root}/.hookd/mutations.db` with proper schema

**Files:**
- `/home/delorenj/code/33GOD/services/mutation-ledger/` (new service directory)
- `/home/delorenj/code/33GOD/services/mutation-ledger/service.py`
- `/home/delorenj/code/33GOD/services/mutation-ledger/models.py`
- `/home/delorenj/code/33GOD/services/mutation-ledger/db.py`
- `/home/delorenj/code/33GOD/services/mutation-ledger/query.py`
- `/home/delorenj/code/33GOD/services/mutation-ledger/pyproject.toml`

---

### HOOKD-5: Claude Code Hook Configuration

**Size:** S | **Blocked by:** HOOKD-1

**What:** Replace the existing gnarly hook one-liners with clean `hookd-emit` calls in Claude Code's hook configuration.

**Target config (in `.claude/settings.json` or equivalent):**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "hookd-emit post_tool_use write"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "hookd-emit post_tool_use bash"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "hookd-emit pre_tool_use $TOOL_NAME"
          }
        ]
      }
    ]
  }
}
```

**Note:** The exact hook config format depends on Claude Code's current hook API. The matcher extracts which tool triggered, and hookd-emit just forwards the payload. Every hook is the same pattern, same binary, different args.

**Acceptance Criteria:**
- Given any Write/Edit/MultiEdit tool fires, when the hook runs, then hookd-emit is called with correct event_type and tool_name
- Given a new tool type needs hooking, when adding it, then only a new matcher entry is needed (no logic changes)
- Hook execution adds < 5ms to tool completion time

**Files:**
- Claude Code hook config (location TBD based on current setup)
- `/home/delorenj/code/33GOD/hookd/config/hooks.example.json` (reference config)

---

### HOOKD-6: Integration Test + End-to-End Validation

**Size:** M | **Blocked by:** HOOKD-1, HOOKD-2, HOOKD-4

**What:** End-to-end test that validates the full pipeline: hookd-emit -> hookd -> Bloodbank -> mutation-ledger -> SQLite.

**Test plan:**
1. Start hookd daemon (test mode, in-process AMQP or testcontainer)
2. Pipe a sample Write tool JSON payload through hookd-emit
3. Verify ToolMutationEvent appears on Bloodbank exchange
4. Verify mutation-ledger stores the fact in SQLite
5. Query the fact via hookd-query and validate fields

**Acceptance Criteria:**
- Full pipeline test passes: emit -> daemon -> broker -> consumer -> storage -> query
- Latency measurement: < 10ms from emit to Bloodbank publish
- hookd handles 100 rapid-fire events without dropping any

**Files:**
- `/home/delorenj/code/33GOD/hookd/tests/` (Rust integration tests)
- `/home/delorenj/code/33GOD/services/mutation-ledger/tests/`

---

## Sprint Plan (1 Sprint)

**Dependency graph:**
```
HOOKD-1 (hookd-emit) ──────┐
                            ├──► HOOKD-5 (hook config)
HOOKD-3 (exchange setup) ──┤
                            ├──► HOOKD-2 (Rust daemon)
                            │         │
                            │         ▼
                            └──► HOOKD-4 (mutation-ledger)
                                      │
                                      ▼
                               HOOKD-6 (integration test)
```

**Suggested execution order:**
1. HOOKD-3 + HOOKD-1 (parallel, no deps)
2. HOOKD-5 (depends on HOOKD-1)
3. HOOKD-2 (depends on HOOKD-3, the big one)
4. HOOKD-4 (depends on HOOKD-3)
5. HOOKD-6 (depends on everything)

**Critical path:** HOOKD-3 -> HOOKD-2 -> HOOKD-6
