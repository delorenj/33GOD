# RFC: Bloodbank Command System

**Author:** Lenoon (agent:infra)  
**Date:** 2026-02-24  
**Status:** DRAFT — Awaiting Grolf review  
**Tickets:** BB-CMD-1, FSM-1, AGENT-CTRL-1, MIG-1, OBS-1  

---

## 1. Problem Statement

Today, 33GOD is event-only: fire-and-forget. There is no way to:

- **Command** an agent to do something and know it received the instruction
- **Track** whether a command was acknowledged, completed, or failed
- **Correlate** a command to its downstream effects (ack → work → result → state change)
- **Enforce** agent state transitions (idle → working → idle) with guards
- **Observe** command completeness (was every command acked? did every ack produce a result?)

The existing `BaseCommand` abstraction (`core/abstraction.py`) has `execute()` + `EventCollector` but it's in-process only — never published to the bus. There's no wire-level command envelope, no response taxonomy, no FSM.

## 2. Design Principles

1. **Commands and events coexist on the same exchange.** No second exchange. `bloodbank.events.v1` TOPIC exchange handles both. Routing key prefix distinguishes them.
2. **Schema-first.** Every type defined in Holyfields JSON Schema before any Pydantic code exists.
3. **Causation chain.** Every message carries `correlation_id` (trace root) AND `causation_id` (immediate parent). This gives us full DAGs, not just flat traces.
4. **Exactly-once semantics via idempotency keys.** Redis dedup window prevents replay storms.
5. **Agent name IS the address.** `command.{agent}.{action}` — consistent with existing `agent.{name}.{event}` pattern.

## 3. Command Envelope Schema

### 3.1 Wire Format

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://33god.dev/schemas/_common/command_envelope.v1.json",
  "title": "Command Envelope",
  "description": "Wire-level envelope for commands sent to agents via Bloodbank. Commands are imperative (do X), unlike events which are declarative (X happened).",
  "type": "object",
  "allOf": [{ "$ref": "base_event.v1.json" }],
  "properties": {
    "command_id": {
      "$ref": "types.v1.json#/$defs/uuid",
      "description": "Unique ID for this command instance. Used for idempotency and correlation."
    },
    "causation_id": {
      "$ref": "types.v1.json#/$defs/uuid",
      "description": "ID of the event/command that directly caused this command. Forms a DAG with correlation_id."
    },
    "target_agent": {
      "$ref": "types.v1.json#/$defs/agent_name",
      "description": "Agent that should execute this command."
    },
    "issued_by": {
      "type": "string",
      "description": "Identity of the issuer (agent name, 'system', or 'jarad')."
    },
    "priority": {
      "type": "string",
      "enum": ["low", "normal", "high", "critical"],
      "default": "normal",
      "description": "Execution priority. 'critical' bypasses queue ordering."
    },
    "ttl_ms": {
      "type": "integer",
      "minimum": 0,
      "default": 30000,
      "description": "Time-to-live in milliseconds. Command expires if not acked within TTL. 0 = no expiry."
    },
    "idempotency_key": {
      "type": "string",
      "description": "Optional dedup key. If present, duplicate commands with same key within the dedup window are dropped."
    },
    "payload": {
      "type": "object",
      "description": "Command-specific payload. Schema varies by command_type."
    }
  },
  "required": ["command_id", "target_agent", "issued_by", "payload"]
}
```

### 3.2 Routing Keys

Commands and their responses use a strict prefix convention:

| Direction | Pattern | Example |
|-----------|---------|---------|
| **Command** (inbound) | `command.{agent}.{action}` | `command.lenoon.run_drift_check` |
| **Ack** (outbound) | `command.{agent}.{action}.ack` | `command.lenoon.run_drift_check.ack` |
| **Result** (outbound) | `command.{agent}.{action}.result` | `command.lenoon.run_drift_check.result` |
| **Error** (outbound) | `command.{agent}.{action}.error` | `command.lenoon.run_drift_check.error` |
| **State change** (outbound) | `agent.{agent}.state.changed` | `agent.lenoon.state.changed` |

Queue bindings:
- Each agent: `command.{agent}.#` → `agent.{name}.commands` (new queue per agent)
- Candystore: `command.#` → `candystore_events` (persist all commands + responses)
- Holocene WS: `command.#` → `bloodbank.events.v1.bloodbank-ws-broadcaster` (observe all)

### 3.3 Response Schemas

#### Ack

```json
{
  "$id": "https://33god.dev/schemas/_common/command_ack.v1.json",
  "title": "Command Acknowledgement",
  "description": "Emitted immediately when an agent accepts a command for processing.",
  "type": "object",
  "allOf": [{ "$ref": "base_event.v1.json" }],
  "properties": {
    "command_id": { "$ref": "types.v1.json#/$defs/uuid" },
    "causation_id": { "$ref": "types.v1.json#/$defs/uuid" },
    "target_agent": { "$ref": "types.v1.json#/$defs/agent_name" },
    "estimated_duration_ms": {
      "type": "integer",
      "description": "Optional estimate of how long the command will take."
    }
  },
  "required": ["command_id", "causation_id", "target_agent"]
}
```

#### Result

```json
{
  "$id": "https://33god.dev/schemas/_common/command_result.v1.json",
  "title": "Command Result",
  "description": "Emitted when an agent completes command execution successfully.",
  "type": "object",
  "allOf": [{ "$ref": "base_event.v1.json" }],
  "properties": {
    "command_id": { "$ref": "types.v1.json#/$defs/uuid" },
    "causation_id": { "$ref": "types.v1.json#/$defs/uuid" },
    "target_agent": { "$ref": "types.v1.json#/$defs/agent_name" },
    "duration_ms": { "type": "integer", "description": "Actual execution time." },
    "outcome": {
      "type": "string",
      "enum": ["success", "partial", "skipped"],
      "description": "'partial' when command completed with caveats. 'skipped' when idempotency dedup fired."
    },
    "result_payload": {
      "type": "object",
      "description": "Command-specific result data."
    }
  },
  "required": ["command_id", "causation_id", "target_agent", "outcome"]
}
```

#### Error

```json
{
  "$id": "https://33god.dev/schemas/_common/command_error.v1.json",
  "title": "Command Error",
  "description": "Emitted when a command fails to execute.",
  "type": "object",
  "allOf": [{ "$ref": "base_event.v1.json" }],
  "properties": {
    "command_id": { "$ref": "types.v1.json#/$defs/uuid" },
    "causation_id": { "$ref": "types.v1.json#/$defs/uuid" },
    "target_agent": { "$ref": "types.v1.json#/$defs/agent_name" },
    "error_code": {
      "type": "string",
      "enum": ["timeout", "rejected", "invalid_state", "execution_failed", "not_implemented"],
      "description": "Machine-readable error classification."
    },
    "error_message": { "type": "string", "description": "Human-readable description." },
    "retryable": { "type": "boolean", "default": false },
    "retry_after_ms": { "type": "integer", "description": "Suggested retry delay if retryable." }
  },
  "required": ["command_id", "causation_id", "target_agent", "error_code", "error_message"]
}
```

## 4. FSM State Model (FSM-1)

### 4.1 States

| State | Description | Entry condition |
|-------|-------------|-----------------|
| `idle` | No active command. Ready for work. | Boot / command completed / reset |
| `acknowledging` | Command received, ack being prepared. | Command arrives, passes guards |
| `working` | Actively executing a command. | Ack sent successfully |
| `blocked` | Execution stalled on external dependency. | Agent self-reports or timeout |
| `error` | Command failed. Awaiting retry or manual intervention. | execute() throws / timeout |
| `paused` | Manually paused (by Jarad, Cack, or self). | Explicit pause command |

### 4.2 Transition Matrix

```
             ┌──────────────────────────────────────────────────────┐
             │                                                      │
             ▼                                                      │
         ┌───────┐   cmd received    ┌──────────────┐              │
    ────▶│ idle  │─────────────────▶│ acknowledging │              │
         └───────┘                   └──────┬───────┘              │
           ▲  ▲                             │ ack sent             │
           │  │                             ▼                      │
           │  │                      ┌──────────┐   blocked   ┌─────────┐
           │  │   result/skip        │ working  │────────────▶│ blocked │
           │  │◀─────────────────────└────┬─────┘             └────┬────┘
           │  │                           │                        │
           │  │                           │ error                  │ unblocked
           │  │                           ▼                        │
           │  │                      ┌─────────┐                   │
           │  └──────────────────────│  error  │◀──────────────────┘
           │        reset            └─────────┘       error
           │
           │         pause (from any)     resume
           └─────────────────────────┌─────────┐
                                     │ paused  │
                                     └─────────┘
```

### 4.3 Transition Guards

| From → To | Guard | Side effect |
|-----------|-------|-------------|
| idle → acknowledging | Command not expired (TTL check). Agent not paused. Idempotency key not seen. | Publish `command.{agent}.{action}.ack` |
| acknowledging → working | Ack published successfully. | Publish `agent.{name}.state.changed` (state=working) |
| working → idle | Result produced. | Publish `command.{agent}.{action}.result` + `agent.{name}.state.changed` (state=idle) |
| working → error | execute() failed OR watchdog timeout. | Publish `command.{agent}.{action}.error` + `agent.{name}.state.changed` (state=error) |
| working → blocked | Agent self-reports blockage. | Publish `agent.{name}.state.changed` (state=blocked) |
| blocked → working | Dependency resolved. | Publish `agent.{name}.state.changed` (state=working) |
| blocked → error | Block timeout exceeded. | Publish `command.{agent}.{action}.error` |
| error → idle | Manual reset or auto-retry exhausted. | Publish `agent.{name}.state.changed` (state=idle) |
| * → paused | Explicit pause command. | Store pre-pause state. Publish state.changed (state=paused) |
| paused → {previous} | Explicit resume command. | Restore pre-pause state. Publish state.changed |

### 4.4 Redis State Schema

```
Key:    agent:{name}:fsm
Type:   HASH
Fields:
  state           = "idle" | "acknowledging" | "working" | "blocked" | "error" | "paused"
  version         = integer (monotonic, for optimistic concurrency)
  command_id      = uuid (current command being processed, null if idle)
  entered_at      = ISO 8601 timestamp
  pre_pause_state = state before pause (null if not paused)
  ttl_deadline    = ISO 8601 timestamp (command expiry)
```

**Write pattern (optimistic concurrency):**
```python
# Lua script for atomic compare-and-swap
TRANSITION_SCRIPT = """
local current_version = tonumber(redis.call('HGET', KEYS[1], 'version') or '0')
if current_version ~= tonumber(ARGV[1]) then
    return 0  -- version conflict, retry
end
redis.call('HMSET', KEYS[1],
    'state', ARGV[2],
    'version', current_version + 1,
    'command_id', ARGV[3],
    'entered_at', ARGV[4])
return current_version + 1
"""
```

**Idempotency dedup:**
```
Key:    agent:{name}:idemp:{idempotency_key}
Type:   STRING (value = command_id)
TTL:    300s (5 minute dedup window)
```

**Replay rule:** Commands with an `idempotency_key` that already exists in Redis get a `result` with `outcome: "skipped"` — no state transition, no re-execution.

## 5. Agent Command Adapter (AGENT-CTRL-1)

### 5.1 Subscription Pattern

Every agent gets a dedicated command queue:

```
Queue:   agent.{name}.commands
Binding: command.{name}.# → bloodbank.events.v1
```

### 5.2 Adapter Lifecycle

```
1. Command arrives on agent.{name}.commands
2. Adapter deserializes CommandEnvelope
3. TTL check → expired? emit error(timeout), done
4. Idempotency check → seen? emit result(skipped), done
5. FSM guard: idle → acknowledging (versioned write)
6. Emit ack
7. FSM: acknowledging → working
8. Dispatch to handler (command_type → handler map)
9. On success: emit result, FSM: working → idle
10. On failure: emit error, FSM: working → error
```

### 5.3 OpenClaw Integration

For agents running on OpenClaw, the adapter is a **FastStream consumer** that:
- Subscribes to `command.{agent_name}.#`
- Translates commands into OpenClaw hook calls (`POST /hooks/agent`)
- Maps hook responses back to result/error events

This means AGENT-CTRL-1 depends on resolving the OpenClaw connectivity blocker (loopback binding).

## 6. hookd Compatibility Bridge (MIG-1)

### 6.1 Architecture

```
Legacy path:    OpenClaw hook → agent session (direct)
New path:       OpenClaw hook → hookd-bridge → CommandEnvelope → Bloodbank → agent adapter
```

The bridge is a **thin HTTP shim** that:
1. Accepts existing hook payloads at the same endpoint format
2. Wraps them in a `CommandEnvelope` with:
   - `command_type`: inferred from hook path/payload
   - `issued_by`: "hookd-bridge"
   - `target_agent`: from hook path
   - `correlation_id`: from hook header or generated
3. Publishes to `command.{agent}.{action}` on Bloodbank
4. Returns 202 Accepted (async, no result awaited)

### 6.2 Scope

**Legacy ingress only.** The bridge does NOT replace the command adapter. It's a compatibility layer for:
- Heartbeat router dispatches
- Infra-dispatcher webhook forwards
- Any external system that already calls OpenClaw hooks

Once all callers migrate to publish commands directly on Bloodbank, the bridge is deprecated.

## 7. Holocene Observability (OBS-1)

### 7.1 Command Completeness Dashboard

Track every command through its lifecycle:

| Metric | Source | Alert threshold |
|--------|--------|-----------------|
| Commands issued (rate) | `command.*.* ` events | — |
| Ack rate | ack count / command count | < 95% over 5min |
| Result rate | result count / ack count | < 90% over 15min |
| Error rate | error count / ack count | > 10% over 5min |
| Mean ack latency | ack.timestamp - command.timestamp | > 5s |
| Mean result latency | result.timestamp - ack.timestamp | > 60s |
| Orphaned commands | commands with no ack after TTL | > 0 |
| State distribution | FSM state per agent | any agent in `error` > 5min |

### 7.2 Causation Graph

New Holocene panel: **Command Trace View**
- Input: `correlation_id`
- Shows: command → ack → state changes → result/error as a timeline
- Uses Candystore historical API to reconstruct full chains

### 7.3 Conformance Tests

Automated tests that validate:
1. Every command type has a registered ack/result/error schema in Holyfields
2. Every agent's adapter handles all command types in its subscription
3. No command goes unacked for > 2× TTL

## 8. Rollout Plan

### Phase A: Foundation (BB-CMD-1 + FSM-1) — Week 1
- Commit Holyfields schemas (command_envelope, ack, result, error)
- Generate Pydantic models, drift check
- Implement FSM service (Redis Lua scripts, Python wrapper)
- Unit tests for FSM transitions + guards
- **Risk:** Redis availability. Mitigation: FSM degrades to in-memory (no persistence across restarts).

### Phase B: Adapter + Bridge (AGENT-CTRL-1 + MIG-1) — Week 2
- Implement FastStream command consumer
- Wire adapter into one pilot agent (Lenoon — self-test)
- Build hookd-bridge shim
- **Risk:** OpenClaw connectivity blocker still unresolved. Mitigation: pilot with Lenoon (host networking, can reach loopback).
- **Risk:** Existing event consumers break if routing changes. Mitigation: commands use `command.*` prefix, existing `agent.*` events untouched.

### Phase C: Observability + Rollout (OBS-1) — Week 3
- Holocene command dashboard
- Conformance tests
- Roll adapter to Tier 1 agents (Cack, Grolf, Lenoon)

### Phase D: Cutover — Week 4+
| Tier | Agents | Criteria |
|------|--------|----------|
| 1 (core) | Cack, Grolf, Lenoon | Already on host networking, direct bus access |
| 2 (engineering) | Rererere, Yi | After Tier 1 stable 48h |
| 3 (social/utility) | Tonny, Tongy, Rar, Pepe, LalaThing, MomoTheCat | After Tier 2 stable 48h |

**Deprecation sequence:**
1. Enable command adapter alongside existing hook dispatch (dual-write)
2. Monitor ack/result rates for 48h per tier
3. Disable direct hook dispatch for that tier
4. After all tiers: deprecate hookd-bridge (keep 30 days for rollback)

## 9. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Redis outage | FSM state lost, commands not deduped | Low | Fallback to in-memory FSM + log warning. No silent data loss. |
| OpenClaw loopback binding | Adapter can't reach hooks from Docker | HIGH (known blocker) | Must resolve before Phase B. Use host networking as interim. |
| Routing key collision | `command.*` could match existing consumers | Low | Existing consumers bind `agent.*`, `system.*`, `webhook.*` — no overlap |
| Envelope schema breaks existing publishers | Publishers fail validation | Medium | CommandEnvelope is NEW — no existing publishers affected. Events unchanged. |
| Agent doesn't ack (hung/crashed) | Command appears orphaned | Medium | Watchdog timer on FSM. Auto-transition to error after TTL. |
| Replay storm from reconnect | Duplicate commands flood agent | Low | Idempotency keys + Redis dedup window |

## 10. Open Questions (for Grolf)

1. **Should commands use the same exchange (`bloodbank.events.v1`) or a dedicated `bloodbank.commands.v1`?** This RFC assumes same exchange for simplicity, but separation gives independent scaling.
2. **FSM state: Redis only or Redis + Candystore?** Redis for hot state, but should transitions also persist to Candystore for audit trail?
3. **Command timeout default: 30s reasonable?** Some agent tasks (code generation, meeting orchestration) take minutes.
4. **Should the bridge (MIG-1) be a sidecar or a standalone service?** RFC assumes standalone.

---

*If the schemas are aligned, we're aligned. If they've drifted, nothing else matters until that's fixed.*
