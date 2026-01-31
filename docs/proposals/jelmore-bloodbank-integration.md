# Jelmore → Bloodbank Integration Proposal

## Current State

### Jelmore
- Provider abstraction layer for agentic coding tools (Claude Code, Gemini CLI, etc.)
- Has session management and command execution
- Tracks correlation IDs and side effects
- **No event emission to Bloodbank yet**

### Holyfields
- Event schema registry using JSON Schema Draft 2020-12
- Auto-generates Pydantic (Python) and Zod (TypeScript)
- Has `theboard/`, `whisperlivekit/` domains
- **No `jelmore/` domain yet**

### Bloodbank
- RabbitMQ-based event bus
- Has HTTP API for publishing events
- Registry system for event domains
- **No jelmore event handlers yet**

## Proposed Architecture

### Event Flow
```
User → Jelmore → Provider (Claude Code/Gemini/etc.)
                     ↓
                 Provider Hook → Bloodbank (direct publish)
                     ↓
                 Topic Exchange (jelmore.*)
                     ↓
                 Subscribers (analytics, logging, Jelmore itself if needed)
```

**Key Principle**: Each provider publishes its own telemetry directly to Bloodbank. Jelmore orchestrates but doesn't proxy events.

### Unified Agent Coder Schema (Option A)

Single event stream with `agent_type` discriminator:

```json
{
  "event_type": "jelmore.agent.action",
  "agent_type": "claude-code",
  "action_type": "tool_use",
  "common_payload": {
    "session_id": "uuid",
    "correlation_id": "uuid",
    "turn_number": 5
  },
  "agent_extensions": {
    // Claude Code specific fields if needed
  }
}
```

**Pros**:
- Single subscription pattern: `jelmore.agent.#`
- Agent-agnostic consumers
- Simpler querying and analytics
- Enforces unified interface

**Cons**:
- `agent_extensions` is less type-safe
- Harder to evolve agent-specific fields
- All consumers get all agents (mitigated by routing key filtering)

### Alternative: Side-Effect Events (Option B)

Jelmore emits generic event + agent-specific side-effects:

```json
// Generic event
{
  "event_type": "jelmore.agent.action",
  "action_type": "tool_use",
  "unified_payload": {...}
}

// Side-effect event (separate)
{
  "event_type": "jelmore.agent.claude_code.action",
  "correlation_id": "uuid",  // Links to parent
  "claude_specific_field": "..."
}
```

**Pros**:
- Agent-specific type safety
- Selective subscription
- Cleaner separation of concerns

**Cons**:
- More events to manage
- Potential duplication
- Coordination overhead

## Recommended Approach

**Option A** with typed extension schema:

```typescript
// Discriminated union pattern
type AgentExtensions =
  | { agent_type: "claude-code", claude_extensions: ClaudeCodeExtensions }
  | { agent_type: "gemini-cli", gemini_extensions: GeminiExtensions }
  | { agent_type: "generic", extensions: Record<string, unknown> }
```

This gives us:
- Single event stream
- Type-safe extensions
- Agent-agnostic consumers
- Graceful degradation for unknown agents

## Holyfields Schema Design

### Directory Structure
```
holyfields/
├── common/schemas/
│   ├── base_event.json                 # Already exists
│   └── agent_types.json                # NEW: Agent type enum
├── jelmore/
│   ├── events/
│   │   ├── agent_action.json           # Tool use, file edit, etc.
│   │   ├── session_started.json        # Session lifecycle
│   │   ├── session_ended.json
│   │   └── agent_error.json            # Error tracking
│   └── commands/
│       └── agent_prompt.json           # Command schema
└── generated/
    ├── python/
    │   └── jelmore/
    │       └── events/
    │           ├── agent_action.py
    │           └── ...
    └── typescript/
        └── jelmore/
            └── events/
                └── agent_action.ts
```

### Core Event Schema: `agent_action.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://33god.dev/schemas/jelmore/events/agent_action.json",
  "title": "Agent Action Event",
  "description": "Emitted when an agentic coder performs an action (tool use, file edit, command execution)",
  "type": "object",
  "allOf": [
    { "$ref": "../../common/schemas/base_event.json" }
  ],
  "properties": {
    "event_type": {
      "type": "string",
      "const": "jelmore.agent.action"
    },
    "agent_type": {
      "$ref": "../../common/schemas/agent_types.json#/$defs/agent_type"
    },
    "action_type": {
      "type": "string",
      "enum": ["tool_use", "file_read", "file_write", "command_exec", "thinking"],
      "description": "Type of action performed"
    },
    "session_id": {
      "$ref": "../../common/schemas/base_event.json#/$defs/uuid"
    },
    "correlation_id": {
      "$ref": "../../common/schemas/base_event.json#/$defs/uuid"
    },
    "turn_number": {
      "type": "integer",
      "minimum": 1,
      "description": "Turn number in session"
    },
    "working_directory": {
      "type": "string",
      "description": "Working directory for action"
    },
    "git_branch": {
      "type": "string",
      "description": "Active git branch"
    },
    "git_status": {
      "type": "string",
      "enum": ["clean", "modified", "unknown"],
      "description": "Git working tree status"
    },
    "tool_metadata": {
      "$ref": "#/$defs/tool_metadata"
    },
    "agent_extensions": {
      "type": "object",
      "description": "Agent-specific extension fields",
      "additionalProperties": true
    }
  },
  "required": [
    "event_type",
    "timestamp",
    "agent_type",
    "action_type",
    "session_id",
    "correlation_id",
    "turn_number",
    "tool_metadata"
  ],
  "$defs": {
    "tool_metadata": {
      "type": "object",
      "properties": {
        "tool_name": {
          "type": "string",
          "description": "Name of tool invoked (e.g., Bash, Read, Write)"
        },
        "tool_input": {
          "type": "object",
          "description": "Tool input parameters",
          "additionalProperties": true
        },
        "success": {
          "type": "boolean",
          "description": "Whether tool execution succeeded"
        },
        "execution_time_ms": {
          "type": "integer",
          "minimum": 0,
          "description": "Tool execution time"
        },
        "error_message": {
          "type": "string",
          "description": "Error message if failed"
        }
      },
      "required": ["tool_name", "tool_input", "success"]
    }
  }
}
```

### Agent Types Enum: `agent_types.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://33god.dev/schemas/common/agent_types.json",
  "title": "Agent Types",
  "description": "Enumeration of supported agentic coding tools",
  "$defs": {
    "agent_type": {
      "type": "string",
      "enum": [
        "claude-code",
        "gemini-cli",
        "gemini-code",
        "cursor",
        "windsurf",
        "generic"
      ],
      "description": "Type of agentic coding tool"
    }
  }
}
```

## Work Breakdown

### Phase 1: Schema Definition (Holyfields)
**Owner**: Jarad (direct work, no external team)

- [ ] Create `holyfields/jelmore/` directory structure
- [ ] Define `common/schemas/agent_types.json`
- [ ] Define `jelmore/events/agent_action.json`
- [ ] Define `jelmore/events/session_started.json`
- [ ] Define `jelmore/events/session_ended.json`
- [ ] Define `jelmore/events/agent_error.json`
- [ ] Run `mise run generate:all`
- [ ] Run `mise run test:all`
- [ ] Commit schemas + generated artifacts

### Phase 2: Bloodbank Integration (Plane Tickets)
**Owner**: Bloodbank team

#### Ticket 1: Register Jelmore Domain
**Epic**: Bloodbank Event Registry
**Story**: As a developer, I want Jelmore events registered in Bloodbank so I can publish and subscribe to agent coder events

**Acceptance Criteria**:
- [ ] Jelmore domain registered in `event_producers/events/registry.py`
- [ ] Auto-discovery includes `jelmore` domain
- [ ] `bb list-events` shows jelmore events

**Implementation**:
```python
# bloodbank/trunk-main/event_producers/events/domains/jelmore.py
from holyfields.generated.python.jelmore.events import (
    AgentActionEvent,
    SessionStartedEvent,
    SessionEndedEvent,
    AgentErrorEvent,
)

ROUTING_KEYS = {
    "AgentActionEvent": "jelmore.agent.action",
    "SessionStartedEvent": "jelmore.session.started",
    "SessionEndedEvent": "jelmore.session.ended",
    "AgentErrorEvent": "jelmore.agent.error",
}
```

#### Ticket 2: Add HTTP Endpoints
**Epic**: Bloodbank HTTP API
**Story**: As a Claude Code hook, I want HTTP endpoints to publish Jelmore events directly to Bloodbank

**Acceptance Criteria**:
- [ ] `POST /events/jelmore/agent/action` endpoint
- [ ] `POST /events/jelmore/session/started` endpoint
- [ ] `POST /events/jelmore/session/ended` endpoint
- [ ] `POST /events/jelmore/agent/error` endpoint
- [ ] Request validation using Pydantic models
- [ ] Returns event envelope with event_id

**Implementation**:
```python
# bloodbank/trunk-main/event_producers/http.py

from event_producers.events.domains.jelmore import (
    AgentActionEvent,
    SessionStartedEvent,
    SessionEndedEvent,
    AgentErrorEvent,
)

@app.post("/events/jelmore/agent/action")
async def publish_agent_action(ev: AgentActionEvent, request: Request):
    client_host = request.client.host if request.client else "unknown"
    source = Source(host=client_host, type=TriggerType.AGENT, app="jelmore")
    envelope = await publish_event_object(ev, source)
    return JSONResponse(envelope.model_dump())

# ... similar for other events
```

#### Ticket 3: Update CLI
**Epic**: Bloodbank CLI
**Story**: As a developer, I want to publish Jelmore events via CLI for testing

**Acceptance Criteria**:
- [ ] `bb publish jelmore.agent.action --json payload.json`
- [ ] Mock data generation: `bb publish jelmore.agent.action --mock`
- [ ] Event listing includes jelmore events

### Phase 3: Claude Code Hook Update
**Owner**: Jarad (direct work)

- [ ] Update `.claude/hooks/bloodbank-publisher.sh` to use unified schema
- [ ] Map Claude Code tool usage to `jelmore.agent.action` events
- [ ] Set `agent_type: "claude-code"`
- [ ] Publish to `/events/jelmore/agent/action` endpoint
- [ ] Update session tracking to use Jelmore schema
- [ ] Test integration with `test-integration.sh`

### Phase 4: Jelmore Event Emission (Optional Future)
**Owner**: Jelmore team (future work)

- [ ] Add event publisher to Jelmore
- [ ] Emit events on provider invocation
- [ ] Emit events on session lifecycle
- [ ] Subscribe to provider-published events for correlation

## Migration Path

### Immediate (Phase 1-3)
1. Define schemas in Holyfields
2. Bloodbank team adds endpoints/registry
3. Update Claude Code hook to publish

### Short-term
- Other providers (Gemini CLI, Cursor) adopt same schema
- Jelmore adds event subscription for correlation tracking

### Long-term
- Jelmore becomes event-driven orchestrator
- Providers publish, Jelmore subscribes and coordinates
- Full observability across all agent coders

## Open Questions

1. **Base Event Inheritance**: Should jelmore events extend `base_event.json` (which has `meeting_id`) or create a new `base_agent_event.json`?
   - **Recommendation**: Create `base_agent_event.json` with `session_id` instead of `meeting_id`

2. **Extension Field Validation**: How strict should `agent_extensions` validation be?
   - **Recommendation**: Start permissive (`additionalProperties: true`), add typed extensions later

3. **Event Retention**: How long should jelmore events be retained?
   - **Recommendation**: 30 days default, configurable per subscriber

4. **Cost Tracking**: Include token/cost fields in `agent_action` event?
   - **Recommendation**: Yes, add `tokens_used` and `cost_usd` as optional fields

## Next Steps

1. **Decision**: Approve Option A (unified schema with extensions)
2. **Schema Work**: Create Holyfields schemas (2-3 hours)
3. **Plane Tickets**: Create 3 tickets in Bloodbank backlog
4. **Hook Update**: Update Claude Code hook after Bloodbank endpoints live

## Timeline (Effort Estimates)

- **Phase 1** (Holyfields): S (2-3 hours)
- **Phase 2** (Bloodbank): M (1 day, split across 3 tickets)
- **Phase 3** (Hook Update): S (1-2 hours)

**Total**: M effort, can be parallelized
