# Claude Code → Bloodbank Integration

Complete integration of Claude Code CLI with Bloodbank event infrastructure for comprehensive observability and analytics.

## Overview

This integration automatically publishes events to Bloodbank for every Claude Code interaction:

- **Tool Usage**: Every tool call (Read, Write, Bash, etc.) with full metadata
- **Session Lifecycle**: Start/end events with statistics
- **Error Tracking**: Detailed error events with context
- **Thinking Events**: Reasoning/thought processes (when available)

## Quick Start

### 1. Start Bloodbank

```bash
cd bloodbank/trunk-main
mise run start
# Or: uv run python -m event_producers.http
```

### 2. Verify Integration

```bash
# Run integration tests
.claude/hooks/test-integration.sh

# Should output:
# ✅ Bloodbank is running
# ✅ Hook script is executable
# ✅ Session start event processed
# ✅ Tool action event processed
# ...
```

### 3. Use Claude Code Normally

Events are published automatically:

```bash
claude
# Every tool call publishes to session.thread.agent.action
# Session start publishes to session.thread.start
# Session end publishes to session.thread.end
```

### 4. Monitor Events

```bash
# Watch all Claude Code events in real-time
cd bloodbank/trunk-main
python watch_events.py --pattern "session.thread.#"

# Or use RabbitMQ management UI
open http://192.168.1.12:15672
```

## Event Schema

### session.thread.agent.action

Published: After every tool use
Routing Key: `session.thread.agent.action`

```json
{
  "session_id": "uuid",
  "tool_metadata": {
    "tool_name": "Bash",
    "tool_input": {
      "command": "git status",
      "description": "Check status"
    },
    "success": true,
    "execution_time_ms": 125
  },
  "working_directory": "/home/user/project",
  "git_branch": "main",
  "git_status": "modified",
  "turn_number": 5,
  "model": "claude-sonnet-4-5",
  "files_in_context": ["src/app.py"],
  "tags": []
}
```

### session.thread.start

Published: Session begins
Routing Key: `session.thread.start`

```json
{
  "session_id": "uuid",
  "working_directory": "/home/user/project",
  "git_branch": "main",
  "git_remote": "git@github.com:user/repo.git",
  "model": "claude-sonnet-4-5",
  "started_at": "2026-01-30T12:00:00Z",
  "context_files": [],
  "mcp_servers": ["claude-flow", "ruv-swarm"]
}
```

### session.thread.end

Published: Session stops/exits
Routing Key: `session.thread.end`

```json
{
  "session_id": "uuid",
  "end_reason": "user_stop",
  "duration_seconds": 1200,
  "total_turns": 15,
  "total_tokens": 45000,
  "total_cost_usd": 0.135,
  "tools_used": {
    "Read": 8,
    "Write": 3,
    "Bash": 4
  },
  "files_modified": ["src/app.py", "tests/test_app.py"],
  "git_commits": ["abc123def"],
  "final_status": "success",
  "summary": "Implemented user authentication",
  "working_directory": "/home/user/project",
  "git_branch": "feature/auth"
}
```

## Configuration

### Environment Variables

Set in `.claude/settings.json`:

```json
{
  "env": {
    "BLOODBANK_ENABLED": "true",
    "BLOODBANK_DEBUG": "false",
    "BLOODBANK_URL": "http://localhost:8682"
  }
}
```

### Disable Event Publishing

```bash
# Temporarily disable
export BLOODBANK_ENABLED=false

# Or in .claude/settings.json
"BLOODBANK_ENABLED": "false"
```

### Debug Mode

```bash
# Enable verbose logging
export BLOODBANK_DEBUG=true
claude 2>&1 | grep bloodbank-publisher
```

## Architecture

### Hook Execution Flow

```
User → Claude Code CLI
         ↓
    Tool Execution
         ↓
    PostToolUse Hook (settings.json)
         ↓
    bloodbank-publisher.sh
         ├─ Read session state
         ├─ Build event payload
         ├─ HTTP POST to Bloodbank
         └─ Update session stats
         ↓
    Bloodbank HTTP API
         ↓
    RabbitMQ Exchange (bloodbank.events.v1)
         ↓
    Subscribers (analytics, logging, etc.)
```

### Session State Management

The hook maintains session state in:
- **Active**: `.claude/session-tracking.json`
- **Archived**: `.claude/sessions/{session-id}.json`

State includes:
- Session ID (UUID)
- Start timestamp
- Working directory
- Git branch
- Turn counter
- Tool usage statistics

## Use Cases

### 1. Analytics Dashboard

Build real-time dashboards:

```python
from event_producers.rabbit import Consumer

@consumer.subscribe("session.thread.agent.action")
async def track_tool_usage(envelope):
    tool = envelope.payload["tool_metadata"]["tool_name"]
    increment_metric(f"tool.{tool}.count")
```

### 2. Cost Tracking

Monitor token usage and costs:

```python
@consumer.subscribe("session.thread.end")
async def track_costs(envelope):
    tokens = envelope.payload.get("total_tokens", 0)
    cost = tokens * COST_PER_TOKEN
    save_cost_metric(cost)
```

### 3. Auto-trigger CI/CD

Trigger tests when files change:

```python
@consumer.subscribe("session.thread.agent.action")
async def auto_test(envelope):
    if envelope.payload["tool_metadata"]["tool_name"] == "Write":
        file_path = envelope.payload["tool_metadata"]["tool_input"]["file_path"]
        if file_path.endswith(".py"):
            trigger_test_pipeline(file_path)
```

### 4. Session Replay

Replay sessions for debugging:

```bash
# Get session history
cat .claude/sessions/{session-id}.json | jq

# Replay all tool actions
bb replay-session {session-id}
```

### 5. Productivity Metrics

Track developer productivity:

```python
@consumer.subscribe("session.thread.end")
async def productivity_metrics(envelope):
    metrics = {
        "duration": envelope.payload["duration_seconds"],
        "turns": envelope.payload["total_turns"],
        "files_modified": len(envelope.payload["files_modified"]),
        "commits": len(envelope.payload["git_commits"])
    }
    save_session_metrics(metrics)
```

## Integration with 33GOD

### iMi (Worktree Manager)

Subscribe to session events for context switching:

```python
@consumer.subscribe("session.thread.start")
async def sync_worktree(envelope):
    branch = envelope.payload["git_branch"]
    imi_switch_context(branch)
```

### Flume (Session Manager)

Track sessions across the platform:

```python
@consumer.subscribe("session.thread.#")
async def sync_session(envelope):
    flume_update_session(envelope.payload)
```

### Holocene (Dagster)

Trigger pipelines based on events:

```python
@consumer.subscribe("session.thread.end")
async def trigger_pipeline(envelope):
    if envelope.payload["files_modified"]:
        dagster_trigger("post_session_pipeline")
```

## Troubleshooting

### Events Not Publishing

1. **Check Bloodbank**:
   ```bash
   curl http://localhost:8682/healthz
   ```

2. **Check RabbitMQ**:
   ```bash
   # Verify connection from bloodbank/.env
   cat bloodbank/trunk-main/.env | grep RABBIT_URL
   ```

3. **Test Hook Directly**:
   ```bash
   echo '{"tool_name": "Test"}' | .claude/hooks/bloodbank-publisher.sh tool-action
   ```

4. **Enable Debug Logging**:
   ```bash
   BLOODBANK_DEBUG=true claude 2>&1 | grep bloodbank
   ```

### Hook Not Executing

1. **Verify Permissions**:
   ```bash
   ls -l .claude/hooks/bloodbank-publisher.sh
   chmod +x .claude/hooks/bloodbank-publisher.sh
   ```

2. **Check Settings**:
   ```bash
   jq '.hooks.PostToolUse' .claude/settings.json
   ```

3. **Test Settings**:
   ```bash
   jq '.env.BLOODBANK_ENABLED' .claude/settings.json
   # Should output: "true"
   ```

### Session State Issues

1. **Reset Session**:
   ```bash
   rm -f .claude/session-tracking.json
   # New session will auto-initialize
   ```

2. **View Active Session**:
   ```bash
   cat .claude/session-tracking.json | jq
   ```

3. **Archive Current Session**:
   ```bash
   echo '{}' | .claude/hooks/bloodbank-publisher.sh session-end manual
   ```

## Files Created

```
.claude/
├── settings.json                          # Updated with hooks
├── hooks/
│   ├── bloodbank-publisher.sh            # Event publisher script
│   ├── test-integration.sh               # Integration tests
│   ├── README.md                          # Full documentation
│   └── setup.md                           # Quick setup guide
├── session-tracking.json                  # Active session state
└── sessions/                              # Archived sessions
    └── {session-id}.json

bloodbank/trunk-main/event_producers/
└── events/
    └── domains/
        └── claude_code.py                 # Event schemas
```

## API Endpoints (Bloodbank)

All endpoints accept JSON payloads matching event schemas.

### Tool Action
```bash
POST http://localhost:8682/events/claude-code/tool-action
```

### Session Start
```bash
POST http://localhost:8682/events/claude-code/session-start
```

### Session End
```bash
POST http://localhost:8682/events/claude-code/session-end
```

### Message
```bash
POST http://localhost:8682/events/claude-code/message
```

### Error
```bash
POST http://localhost:8682/events/claude-code/error
```

### Thinking
```bash
POST http://localhost:8682/events/claude-code/thinking
```

## Future Enhancements

1. **Message Events**: Capture full conversation history
2. **Thinking Events**: Expose reasoning tokens (requires API extension)
3. **Error Events**: Automatic error reporting
4. **Context Snapshots**: Periodic context dumps
5. **Correlation Tracking**: Link sessions across projects
6. **Cost Attribution**: Per-feature cost tracking

## Resources

- [Hook Documentation](.claude/hooks/README.md)
- [Setup Guide](.claude/hooks/setup.md)
- [Event Schemas](bloodbank/trunk-main/event_producers/events/domains/claude_code.py)
- [Bloodbank Architecture](bloodbank/trunk-main/docs/ARCHITECTURE.md)
- [33GOD Event Infrastructure](docs/domains/event-infrastructure/)
