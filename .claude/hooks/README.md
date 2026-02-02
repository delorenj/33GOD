# Claude Code Bloodbank Integration Hooks

Comprehensive event publishing system that captures all Claude Code interactions and publishes them to Bloodbank for observability, analytics, and debugging.

## Overview

This hook system publishes detailed events to your Bloodbank event bus, enabling:

- **Tool Usage Tracking**: Every tool call (Read, Write, Bash, etc.) with full metadata
- **Session Lifecycle**: Start/end events with statistics and context
- **Observability**: Real-time monitoring of Claude Code sessions
- **Analytics**: Historical analysis of tool usage patterns
- **Debugging**: Complete replay capability for troubleshooting

## Architecture

```
Claude Code CLI
    ↓ (tool invoked)
PostToolUse Hook
    ↓ (JSON input via stdin)
bloodbank-publisher.sh
    ↓ (HTTP POST or bb CLI)
Bloodbank Event Bus (RabbitMQ)
    ↓ (routing key: session.thread.agent.action)
Subscribers (analytics, logging, etc.)
```

## Event Types Published

### 1. `session.thread.agent.action`
Published on **every tool use** (Read, Write, Bash, Grep, etc.)

**Payload**:
```json
{
  "session_id": "uuid",
  "tool_metadata": {
    "tool_name": "Bash",
    "tool_input": {"command": "git status"},
    "success": true
  },
  "working_directory": "/home/user/project",
  "git_branch": "main",
  "git_status": "modified",
  "turn_number": 5,
  "model": "claude-sonnet-4-5"
}
```

### 2. `session.thread.start`
Published when Claude Code session begins

**Payload**:
```json
{
  "session_id": "uuid",
  "working_directory": "/home/user/project",
  "git_branch": "main",
  "git_remote": "git@github.com:user/repo.git",
  "model": "claude-sonnet-4-5",
  "started_at": "2026-01-30T12:00:00Z"
}
```

### 3. `session.thread.end`
Published when session stops/ends

**Payload**:
```json
{
  "session_id": "uuid",
  "end_reason": "user_stop",
  "duration_seconds": 1200,
  "total_turns": 15,
  "tools_used": {
    "Read": 8,
    "Write": 3,
    "Bash": 4
  },
  "files_modified": ["src/app.py", "tests/test_app.py"],
  "git_commits": ["abc123", "def456"],
  "final_status": "success",
  "working_directory": "/home/user/project",
  "git_branch": "main"
}
```

## Configuration

### Environment Variables

Set these in `.claude/settings.json` under `"env"`:

```json
{
  "env": {
    "BLOODBANK_ENABLED": "true",
    "BLOODBANK_DEBUG": "false",
    "BLOODBANK_URL": "http://localhost:8682"
  }
}
```

**Variables**:
- `BLOODBANK_ENABLED`: Set to `"false"` to disable event publishing
- `BLOODBANK_DEBUG`: Set to `"true"` for verbose logging to stderr
- `BLOODBANK_URL`: Bloodbank HTTP API endpoint (default: `http://localhost:8682`)
- `RABBIT_URL`: Direct RabbitMQ connection (from bloodbank `.env`)

### Hook Configuration

The PostToolUse hook publishes events for **all tools** using a universal matcher:

```json
{
  "PostToolUse": [
    {
      "matcher": ".*",
      "hooks": [
        {
          "type": "command",
          "command": "cat | .claude/hooks/bloodbank-publisher.sh tool-action"
        }
      ]
    }
  ]
}
```

The Stop hook publishes session end events:

```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "echo '{}' | .claude/hooks/bloodbank-publisher.sh session-end user_stop"
        }
      ]
    }
  ]
}
```

## Session Tracking

The hook system maintains session state in `.claude/session-tracking.json`:

```json
{
  "session_id": "uuid",
  "started_at": "2026-01-30T12:00:00Z",
  "working_directory": "/home/user/project",
  "git_branch": "main",
  "turn_number": 5,
  "tools_used": {
    "Read": 3,
    "Write": 1,
    "Bash": 1
  }
}
```

Session archives are saved to `.claude/sessions/` on session end.

## Bloodbank Setup

### 1. Start Bloodbank Services

Ensure Bloodbank is running with RabbitMQ:

```bash
cd bloodbank/trunk-main
# Start RabbitMQ and Bloodbank HTTP API
docker-compose up -d  # Or your preferred method
```

### 2. Register Event Schemas

Add the Claude Code event domain to Bloodbank:

```bash
# The events are already defined in:
# bloodbank/trunk-main/event_producers/events/domains/claude_code.py

# Test event publishing
echo '{"test": "data"}' | bb publish session.thread.agent.action --json -
```

### 3. Create Subscribers

Example subscriber for Claude Code events:

```python
from event_producers.rabbit import Consumer
from event_producers.events import EventEnvelope
from event_producers.events.domains.claude_code import SessionAgentToolAction

consumer = Consumer()

@consumer.subscribe("session.thread.#")
async def handle_claude_events(envelope: EventEnvelope):
    if envelope.event_type == "session.thread.agent.action":
        action = SessionAgentToolAction(**envelope.payload)
        print(f"Tool used: {action.tool_metadata.tool_name}")
        print(f"Session: {action.session_id}")

# Run consumer
consumer.run()
```

## Debugging

### Enable Debug Logging

```bash
# In .claude/settings.json
"BLOODBANK_DEBUG": "true"
```

### View Published Events

```bash
# Watch all Claude Code events in real-time
cd bloodbank/trunk-main
python watch_events.py --pattern "session.thread.#"
```

### Test Hook Manually

```bash
# Simulate tool action
echo '{
  "tool_name": "Bash",
  "tool_input": {"command": "echo test"}
}' | .claude/hooks/bloodbank-publisher.sh tool-action

# Check if event was published
bb list-events --filter "session.thread"
```

### Check Session State

```bash
# View current session
cat .claude/session-tracking.json | jq

# View session archives
ls -la .claude/sessions/
cat .claude/sessions/<session-id>.json | jq
```

## Advanced Usage

### Custom Event Publishing

Extend the hook script to publish additional events:

```bash
# Add to bloodbank-publisher.sh
handle_thinking_event() {
    local thinking_text="$1"
    local payload
    payload=$(jq -n \
        --arg session_id "$(get_session_id)" \
        --arg thinking_text "$thinking_text" \
        '{
            session_id: $session_id,
            thinking_text: $thinking_text
        }')
    publish_to_bloodbank "thinking" "$payload"
}
```

### Filter Events by Tool

Only publish specific tools:

```json
{
  "PostToolUse": [
    {
      "matcher": "Bash|Write|Edit",
      "hooks": [
        {
          "type": "command",
          "command": "cat | .claude/hooks/bloodbank-publisher.sh tool-action"
        }
      ]
    }
  ]
}
```

### Batch Event Publishing

The hook system publishes events individually. For batch publishing, modify to queue events and flush periodically.

## Integration with 33GOD Pipeline

The Bloodbank events integrate seamlessly with the 33GOD ecosystem:

1. **iMi**: Worktree manager can subscribe to session events for context switching
2. **Flume**: Session/task manager can track Claude Code sessions
3. **Holocene**: Dagster pipelines can trigger on tool usage patterns
4. **Analytics**: Aggregate tool usage across all developers

### Example: Auto-trigger Tests on File Changes

```python
from event_producers.rabbit import Consumer
from event_producers.events.domains.claude_code import SessionAgentToolAction

consumer = Consumer()

@consumer.subscribe("session.thread.agent.action")
async def auto_test(envelope):
    action = SessionAgentToolAction(**envelope.payload)

    if action.tool_metadata.tool_name in ["Write", "Edit"]:
        # File was modified, trigger tests
        file_path = action.tool_metadata.tool_input.get("file_path")
        if file_path and file_path.endswith(".py"):
            print(f"Running tests for {file_path}...")
            # Trigger test pipeline
```

## Troubleshooting

### Events Not Publishing

1. Check Bloodbank is running:
   ```bash
   curl http://localhost:8682/health
   ```

2. Verify RabbitMQ connection:
   ```bash
   # Check .env in bloodbank/trunk-main
   cat bloodbank/trunk-main/.env
   ```

3. Test direct publishing:
   ```bash
   bb publish session.thread.agent.action --mock
   ```

### Permission Errors

```bash
chmod +x .claude/hooks/bloodbank-publisher.sh
```

### Missing Dependencies

```bash
# Ensure jq is installed
sudo apt-get install jq  # or brew install jq

# Ensure uuid tools
sudo apt-get install uuid-runtime
```

## Monitoring and Analytics

### Real-time Dashboard

Build a real-time dashboard by subscribing to all session events:

```python
# dashboard.py
import asyncio
from collections import defaultdict
from event_producers.rabbit import Consumer

stats = defaultdict(int)

@consumer.subscribe("session.thread.#")
async def update_dashboard(envelope):
    stats[envelope.event_type] += 1
    print(f"Events: {dict(stats)}")
```

### Cost Tracking

Track token usage and costs:

```python
@consumer.subscribe("session.thread.end")
async def track_costs(envelope):
    total_tokens = envelope.payload.get("total_tokens", 0)
    cost_per_token = 0.000003  # Example rate
    cost = total_tokens * cost_per_token
    print(f"Session cost: ${cost:.4f}")
```

## Future Enhancements

Potential extensions:

1. **Thinking Events**: Capture reasoning/thinking tokens (requires Claude Code API extension)
2. **Message Events**: Full conversation history publishing
3. **Error Events**: Detailed error tracking with stack traces
4. **Performance Metrics**: Tool execution times, latency tracking
5. **Context Snapshots**: Periodic dumps of conversation context
6. **Correlation Tracking**: Link related sessions across projects

## Reference

- [Bloodbank Documentation](../bloodbank/trunk-main/docs/)
- [Claude Code Hooks](https://github.com/anthropics/claude-code/docs/hooks)
- [Event Schema Definitions](../bloodbank/trunk-main/event_producers/events/domains/claude_code.py)
- [33GOD Architecture](../docs/domains/event-infrastructure/)
