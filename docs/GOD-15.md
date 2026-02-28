# GOD-15: Heartbeat Architecture & Hookd-Bridge Fate

**Owner**: Grolf
**Date**: 2026-02-26
**Status**: APPROVED

## 1. Decision: Fate of Hookd-Bridge

| Option | Pros | Cons | Recommendation |
| :--- | :--- | :--- | :--- |
| **KEEP** | Proven stable path (MIG-1). Handles HTTP auth/validation centrally. Zero churn today. | Latency hop (Rabbit→Router→HTTP→Rabbit). Adds "message" vs "text" schema fragility. | **KEEP (Tier 0)** |
| **REMOVE** | Pure event bus (Rabbit→Router→Rabbit). Lower latency. Type safety via envelopes. | Requires new `command.{agent}.heartbeat` consumer logic in agents. Breaking change. | **MIGRATE (Tier 1)** |

**Verdict**: **KEEP for now (Phase A)**. The bridge is working (fixed in `2893e97`). Do not rip it out under fire.
**Plan**: Schedule **Phase B** removal once agents consume RabbitMQ commands directly.

---

## 2. Heartbeat Scheduling Architecture

**Core Concept**: **Universal Tick (Hardware)** + **Per-Agent Schedule (Software)**.
- **Hardware**: `heartbeat-tick` emits `system.heartbeat.tick` every 60s (globally).
- **Software**: `heartbeat-router` reads `heartbeat.json` and decides *if* an agent wakes up.

**Schema: `heartbeat.json`** (Unified)
Supports exact time (meetings), intervals (cleanup), and cron-like windows.

```json
{
  "agent": "lenoon",
  "checks": [
    {
      "id": "morning_standup_prep",
      "type": "exact",
      "schedule": ["09:00", "09:30"],
      "timezone": "America/New_York",
      "prompt": "Check Jira for blockers."
    },
    {
      "id": "stale_branch_cleanup",
      "type": "interval",
      "every_minutes": 240,
      "window": { "start": "09:00", "end": "17:00", "days": ["Mon-Fri"] },
      "prompt": "Delete merged branches."
    },
    {
      "id": "context_compaction",
      "type": "cron",
      "expression": "*/30 * * * *",
      "prompt": "Compact context if >80%."
    }
  ]
}
```

---

## 3. Concrete Rollout Plan

### Phase A: Fix & Stabilize (NOW)
*   **Goal**: Ensure reliability of current interval-based checks.
*   **Action**: `heartbeat-router` already patched to send `text` payload.
*   **Guardrail**: Router logs "Dispatched X checks" vs "HTTP 202" confirmation.
*   **Metric**: `heartbeat_dispatched_total` counter in Prometheus.

### Phase B: Advanced Scheduling (Next Sprint)
*   **Goal**: Support exact-time + cron.
*   **Action**: Update `heartbeat-router` logic to parse new schema.
*   **Guardrail**: Fallback to "every 60m" if schema invalid.

### Phase C: Bridge Demolition (Future)
*   **Goal**: Pure AMQP dispatch.
*   **Action**: Agents bind `command.{self}.heartbeat`. Router publishes directly. Retire `hookd-bridge`.

---

## Tasks & Owners

| Priority | Task | Owner | Status |
| :--- | :--- | :--- | :--- |
| **P0** | **Verify Fix**: Ensure `text` payload flows E2E (Router→Bridge→Agent). | **Grolf** | ✅ Done |
| **P1** | **Schema Upgrade**: Implement `exact` and `cron` logic in `heartbeat-router`. | **Lenoon** | Backlog |
| **P1** | **Observability**: Add Prometheus metrics to `heartbeat-router`. | **Lenoon** | Backlog |
| **P2** | **Bridge Removal**: Prototype direct AMQP heartbeat consumer. | **Grolf** | Backlog |

## Risks
1.  **Schema Drift**: Old `heartbeat.json` files must still work. (Mitigation: Router supports both list/dict formats).
2.  **Tick Miss**: If `heartbeat-tick` dies, time stops. (Mitigation: Docker healthcheck + auto-restart).
3.  **Overload**: 10 agents x 5 checks = 50 concurrent wake-ups. (Mitigation: Router jitter/stagger logic).
