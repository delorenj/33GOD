# GOD-14: Pure Event-Driven Pipeline & Temporal Fit

**Status**: APPROVED
**Owner**: Grolf
**Date**: 2026-02-26

## Objective
Establish a **Single Source of Truth** (Candystore) with **Zero Dual-Writes** and **Full Lifecycle Visibility** for the 33GOD ecosystem.

## Core Principles
1.  **Candystore is Truth**: Only Candystore writes to the history DB.
2.  **Events are Facts**: UI updates based on events, not local state.
3.  **Temporal for Work**: Long-running tasks go to Temporal; chat stays in Bloodbank.
4.  **No Dual-Writes**: Agents publish to RabbitMQ; consumers (Candystore) persist.

## Architecture

### 1. Routing & Topics (Baseline)
We strictly adhere to current routing to avoid drift/churn:
-   **Commands (Intent)**: `command.{target_agent}.{action}`
    -   `command.agent.lenoon.chat`
    -   `command.system.broadcast.alert`
-   **Events (Facts)**: `agent.{source_agent}.{type}.{status}`
    -   `agent.lenoon.message.sent`
    -   `agent.lenoon.tool.completed`
    -   `system.heartbeat.tick`

### 2. The Envelope (Non-Negotiable)
All messages must contain these fields for sanity, replay, and debugging:
```json
{
  "event_id": "uuidv7",          // Unique ID of this specific message
  "trace_id": "uuidv7",          // Correlation ID for the whole flow
  "causation_id": "uuidv7",      // ID of the message that caused this one
  "idempotency_key": "string",   // For de-dupe (hash of content + timestamp bucket)
  "producer": "agent:lenoon",    // Who sent it
  "occurred_at": "iso8601",      // When it happened
  "type": "message.sent",        // Semantic type
  "payload": { ... }             // Domain data
}
```

### 3. Persistence (Candystore Scope)
Candystore is the **Auditor**. It subscribes to and persists:
-   `command.#` (Intent - what we *wanted* to happen)
-   `agent.#` (Facts - what *actually* happened)
-   `system.#` (Context - heartbeats, alerts)

It **DOES NOT** filter. It records everything to the immutable `events` log.

### 4. Outbox Pattern (Phase B)
-   **Location**: **Messaging Adapter / Bridge Layer** (not deep agent runtime).
-   **Mechanism**:
    1.  Adapter receives external signal (e.g., HTTP request).
    2.  Writes to local SQLite `outbox` table.
    3.  Background thread publishes to RabbitMQ.
    4.  Deletes on ACK.

### 5. Holocene Visibility
The UI must render the *lifecycle*, not just the text.
-   **State 1: Queued** (Grey) - Sent to Bridge.
-   **State 2: Published** (Light Grey) - ACK'd by Broker.
-   **State 3: Persisted** (Solid) - `event.saved` from Candystore.
-   **State 4: Delivered/Failed** (Status Icon) - Consumer ACK/NACK.

### 6. Temporal Role
-   **Chat/Messaging**: **Bloodbank** (RabbitMQ). Low latency, high volume.
-   **Complex Tasks**: **Temporal**. Durability, retries, long-running.
    -   Trigger: `command.agent.{name}.deploy` -> Temporal Workflow.
    -   Feedback: Workflow publishes `agent.{name}.task.update` events back to Bloodbank.

## 3-Phase Rollout Plan

### Phase A: The Listener (Immediate / Low Risk)
*   **Goal**: Holocene stops trusting itself.
*   **Action**:
    1.  Update Candystore to consume `command.#` + `agent.#`.
    2.  Update Holocene to listen for `agent.{name}.message.*` to confirm display.
    3.  **No breaking changes to agents.**

### Phase B: The Outbox (Migration)
*   **Goal**: Guaranteed Delivery.
*   **Action**:
    1.  Implement SQLite Outbox in the Python Command Adapter.
    2.  Ensure `trace_id` propagation.

### Phase C: The Cutover (Strict Mode)
*   **Goal**: Single Writer.
*   **Action**:
    1.  Revoke DB write permissions for everyone except Candystore.
    2.  Force all UI updates via Event Bus.

## Risks & Guardrails
-   **Latency**: Mitigate with Optimistic UI (grey state).
-   **Loops**: Sender Filter (discard `source == self`).
-   **Replay**: Deterministic replay from Candystore to rebuild UI state after outage.
