# Claude Code Hooks Setup Guide

Quick setup guide for claude-flow hooks and Bloodbank integration.

## Quick Start

### 1. Enable Hooks in Settings

The hooks are already configured in `.claude/settings.json`. Verify the configuration:

```bash
cat .claude/settings.json | jq '.hooks'
```

### 2. Configure Bloodbank Connection

Set environment variables in `.claude/settings.json`:

```json
{
  "env": {
    "BLOODBANK_ENABLED": "true",
    "BLOODBANK_URL": "http://localhost:8682",
    "BLOODBANK_DEBUG": "false"
  }
}
```

### 3. Test Hook Execution

```bash
# Test the bloodbank publisher script
echo '{"tool_name": "Bash", "tool_input": {"command": "echo test"}}' | \
  .claude/hooks/bloodbank-publisher.sh tool-action

# Should output debug logs if BLOODBANK_DEBUG=true
```

### 4. Start Using Claude Code

Just use Claude Code normally. Hooks will automatically:
- Publish tool usage events after every tool call
- Track session lifecycle (start/end)
- Maintain session statistics

## Available Hooks

### PostToolUse Hooks

1. **Bloodbank Event Publisher** (Universal)
   - Matcher: `.*` (all tools)
   - Publishes to: `session.thread.agent.action`
   - Captures: Tool name, inputs, context, git state

2. **Claude-Flow Post-Command** (Bash only)
   - Matcher: `Bash`
   - Tracks metrics and stores results

3. **Claude-Flow Post-Edit** (File operations)
   - Matcher: `Write|Edit|MultiEdit`
   - Auto-formats and updates memory

### PreToolUse Hooks

1. **Claude-Flow Pre-Command** (Bash only)
   - Validates safety
   - Prepares resources

2. **Claude-Flow Pre-Edit** (File operations)
   - Auto-assigns agents
   - Loads context

### Stop Hooks

1. **Bloodbank Session End**
   - Publishes final session statistics
   - Archives session data

2. **Claude-Flow Session End**
   - Generates summary
   - Persists state

### Init Hooks

1. **Bloodbank Session Start**
   - Initializes session tracking
   - Publishes session start event

## Hook Input Format

Hooks receive JSON via stdin with this structure:

```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "git status",
    "description": "Check git status"
  },
  "tool_output": "... output if PostToolUse ..."
}
```

## Claude-Flow Companion CLI

The hooks use `npx claude-flow@alpha hooks` for advanced coordination:

```bash
# Available hook commands
npx claude-flow@alpha hooks --help

# Pre-command validation
npx claude-flow@alpha hooks pre-command --command "rm -rf /" --validate-safety

# Post-edit formatting
npx claude-flow@alpha hooks post-edit --file src/app.py --format

# Session end with summary
npx claude-flow@alpha hooks session-end --generate-summary
```

## Debugging Hooks

### Enable Debug Mode

```bash
# In .claude/settings.json
"BLOODBANK_DEBUG": "true"
```

### View Hook Logs

Hooks output to stderr:

```bash
# Run claude code and redirect stderr
claude 2>&1 | grep "bloodbank-publisher"
```

### Test Hook Manually

```bash
# Simulate PostToolUse for Bash
cat <<EOF | .claude/hooks/bloodbank-publisher.sh tool-action
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "echo hello",
    "description": "Test command"
  }
}
EOF
```

### Check Session Tracking

```bash
# Current session
cat .claude/session-tracking.json | jq

# Session history
ls -la .claude/sessions/
```

## Integration with Bloodbank

### Start Bloodbank

```bash
cd bloodbank/trunk-main

# Method 1: Using mise tasks (recommended)
mise run start

# Method 2: Direct Python
uv run python -m event_producers.http
```

### Verify Connection

```bash
# Health check
curl http://localhost:8682/health

# Test event publishing
echo '{"test": "data"}' | \
  bb publish session.thread.agent.action --json -
```

### Subscribe to Events

```bash
# Watch all session events
cd bloodbank/trunk-main
python watch_events.py --pattern "session.thread.#"
```

## Hook Execution Flow

```
User sends prompt to Claude
    ↓
Claude decides to use a tool
    ↓
PreToolUse hooks execute (validation, prep)
    ↓
Tool executes (Read, Write, Bash, etc.)
    ↓
PostToolUse hooks execute:
    1. Bloodbank publisher (universal matcher)
    2. Claude-Flow post-command (if Bash)
    3. Claude-Flow post-edit (if file operation)
    ↓
Events published to Bloodbank
    ↓
Subscribers process events (analytics, logging, etc.)
```

## Configuration Reference

### Full settings.json Structure

```json
{
  "env": {
    "CLAUDE_FLOW_HOOKS_ENABLED": "true",
    "BLOODBANK_ENABLED": "true",
    "BLOODBANK_URL": "http://localhost:8682",
    "BLOODBANK_DEBUG": "false"
  },
  "hooks": {
    "PreToolUse": [...],
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "cat | .claude/hooks/bloodbank-publisher.sh tool-action",
            "description": "Publish all tool usage"
          }
        ]
      }
    ],
    "Stop": [...],
    "Init": [...]
  }
}
```

### Matcher Patterns

- `.*` - All tools (universal)
- `Bash` - Only Bash tool
- `Write|Edit|MultiEdit` - File operations
- `Read|Glob|Grep` - File reading operations
- Custom regex patterns supported

## Troubleshooting

### Hooks Not Running

1. Check hooks are enabled:
   ```bash
   jq '.env.CLAUDE_FLOW_HOOKS_ENABLED' .claude/settings.json
   ```

2. Verify hook script is executable:
   ```bash
   ls -l .claude/hooks/bloodbank-publisher.sh
   chmod +x .claude/hooks/bloodbank-publisher.sh
   ```

3. Test hook directly:
   ```bash
   echo '{}' | .claude/hooks/bloodbank-publisher.sh session-start
   ```

### Events Not Publishing

1. Check Bloodbank is running:
   ```bash
   curl http://localhost:8682/health
   ```

2. Verify RabbitMQ connection:
   ```bash
   # In bloodbank directory
   cat .env
   ```

3. Test with bb CLI:
   ```bash
   bb list-events
   ```

### Permission Issues

```bash
# Fix hook permissions
chmod +x .claude/hooks/*.sh

# Fix session directory
mkdir -p .claude/sessions
chmod 755 .claude/sessions
```

## Advanced Configuration

### Disable Specific Hooks

Set `BLOODBANK_ENABLED=false` to disable event publishing while keeping other hooks active:

```json
{
  "env": {
    "BLOODBANK_ENABLED": "false"
  }
}
```

### Custom Event Handlers

Extend `bloodbank-publisher.sh` with custom event types:

```bash
handle_custom_event() {
    local input="$1"
    # Your custom logic
    publish_to_bloodbank "custom.event" "$payload"
}
```

### Hook Ordering

Hooks execute in the order listed in settings.json. Place critical hooks first.

## Resources

- [Full Bloodbank Integration Guide](README.md)
- [Claude Code Hooks Documentation](https://github.com/anthropics/claude-code)
- [Claude-Flow MCP Server](https://github.com/ruvnet/claude-flow)
- [33GOD Event Architecture](../../docs/domains/event-infrastructure/)
