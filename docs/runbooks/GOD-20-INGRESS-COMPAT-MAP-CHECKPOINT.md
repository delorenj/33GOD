# GOD-20 — AGENT-CTRL Ingress Compatibility Map + Adapter Checkpoint

**Timestamp (ET):** 2026-03-12 06:18  
**Owner:** Lenoon (infra)  
**Slice:** 06:05 → 06:35 ET execution window

## 1) Ingress Compatibility Map (Current)

| Ingress Source | Entry Point | Compatibility Layer | Exchange/Routing | Adapter Path | Status |
|---|---|---|---|---|---|
| Legacy OpenClaw hook senders | `POST :18790/hooks/agent` | `hookd-bridge` parses `sessionKey` + text | `bloodbank.events.v1` → `command.{agent}.{action}` | `command-adapter` consumes `command.*` and dispatches to `:18789/hooks/agent` | ✅ Active |
| Heartbeat local scheduler | `heartbeat-router` → `OPENCLAW_HOOK_URL=http://127.0.0.1:18790/hooks/agent` | Same bridge path as legacy | Same command route fan-in | Same adapter execution path | ✅ Active |
| Infra-dispatcher | `OPENCLAW_HOOK_URL=http://127.0.0.1:18790/hooks/agent` | Same bridge path as legacy | Same command route fan-in | Same adapter execution path | ✅ Active |
| Native command publishers | AMQP publish direct to `command.{agent}.{action}` | No compatibility shim required | `bloodbank.events.v1` topic | `command-adapter` direct consume | ✅ Supported |

### Normalization Guarantees (compatibility-critical)
- `hookd-bridge` emits canonical `command.envelope`
- `source` is object-shaped (`host/app/type/trigger_type`) not bare string
- Routing normalized via `normalize_action()` aliases

---

## 2) Adapter Rollout Checkpoint (Live Runtime)

### Service Health
- `33god-hookd-bridge`: running/healthy
- `33god-command-adapter`: running/healthy
- `33god-heartbeat-router`: running/healthy
- `33god-infra-dispatcher`: running/healthy
- `33god-bloodbank`: running/healthy
- `33god-candystore`: running/healthy
- `33god-holocene`: running/healthy

### Adapter Roster (bound)
`cack,grolf,rererere,lenoon,tonny,tongy,rar,pepe,lalathing,momothecat,yi`

### Bridge Health Counter Snapshot
`GET /healthz` on `:18790`:
- `received`: 6866
- `published`: 6009
- `errors`: 0
- `rabbitmq_connected`: true

### Queue Snapshot (checkpoint)
- `agent.commands` → `0` msgs, `1` consumer ✅
- `candystore_events` → `0` msgs, `1` consumer ✅
- `bloodbank.events.v1.bloodbank-ws-broadcaster` → `0` msgs, `1` consumer ✅
- `heartbeat-router` → `0` msgs, `1` consumer ✅
- `candystore_events_dlq` → `448` msgs, `0` consumers ⚠️

---

## 3) Delta Shipped This Slice

1. **Produced explicit ingress compatibility map** for all active ingress classes (legacy hook, heartbeat, infra-dispatcher, native command publishers) into one manager-readable artifact.
2. **Captured live adapter checkpoint evidence** (health, roster, bridge counters, queue state) with current values.
3. **Flagged operational delta requiring follow-up**: `candystore_events_dlq` has re-accumulated to 448 messages after prior BB-4 purge.

---

## 4) Known Blockers / Risks

1. **DLQ re-growth** (`candystore_events_dlq=448`) indicates either stale backlog replay or a new rejection path; needs targeted sample triage before expanding rollout.
2. **Agent FSM stuck states (rar/tongy)** observed in adapter logs (not-idle/error rejection pattern), requiring state reset/runbook validation for cleaner command acceptance.

---

## 5) Immediate Next Slice (20–30m)

1. Sample 50 DLQ messages, classify by timestamp + event_type + source-shape.
2. Decide safe purge vs active regression path.
3. If active regression: patch producer path and re-verify with one forced command lifecycle test.
4. Publish GOD-20 QA support handoff note to manager with go/no-go recommendation for further adapter ingress expansion.
