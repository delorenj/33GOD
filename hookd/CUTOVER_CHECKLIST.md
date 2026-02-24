# GOD-11 MIG-1 — hookd-bridge Cutover Checklist

> **Owner:** Rererere (agent:work)
> **Created:** 2026-02-24
> **Status:** IN PROGRESS
> **RFC Reference:** COMMAND-SYSTEM-RFC.md §6 + §8

---

## Overview

This document tracks the migration from direct OpenClaw hook dispatch to the
Bloodbank command system via the hookd-bridge compatibility layer.

**Architecture:**
```
BEFORE:  OpenClaw hook → agent session (direct, no audit trail)
DURING:  OpenClaw hook → hookd-bridge → CommandEnvelope → Bloodbank → agent adapter
                    ↘ (dual-write: also direct dispatch for safety)
AFTER:   Command issuer → CommandEnvelope → Bloodbank → agent adapter (no hooks)
```

---

## Phase B Prerequisites (must be green before bridge goes live)

| # | Item | Owner | Status | Notes |
|---|------|-------|--------|-------|
| B1 | Command schemas committed in Holyfields | Lenoon | ✅ DONE | `schemas/command/{envelope,ack,result,error}.v1.json` |
| B2 | Pydantic models generated for command schemas | Lenoon/Rererere | ❌ TODO | `holyfields/generated/python/` missing command models |
| B3 | FSM service implemented (Redis Lua scripts) | Lenoon | ✅ DONE | `bloodbank/command_fsm/` — 890 LOC |
| B4 | FSM unit tests passing | Lenoon | ❌ VERIFY | Need to run `bloodbank/command_fsm/` tests |
| B5 | FastStream command consumer (AGENT-CTRL-1) | TBD | ❌ TODO | No adapter exists yet — blocks live commands |
| B6 | OpenClaw loopback binding resolved | TBD | ❌ BLOCKER | Adapter can't reach hooks from Docker containers |
| B7 | Pilot agent wired (Lenoon self-test) | Lenoon | ❌ TODO | Depends on B5 + B6 |

---

## Phase C: Bridge Deployment Checklist

### Infrastructure

- [ ] **C1**: Deploy hookd-bridge as a service (Docker or systemd)
  - Image: Python 3.12 + FastAPI + aio-pika
  - Port: 8099 (configurable via `BRIDGE_PORT`)
  - Health check: `GET /health`
  - Env vars: `HOOKD_AMQP_URL`, `HOOKD_EXCHANGE`, `BRIDGE_PORT`

- [ ] **C2**: Verify AMQP connectivity from bridge container
  - Bridge must reach RabbitMQ on the same exchange as Bloodbank (`bloodbank.events.v1`)
  - Test: `curl http://localhost:8099/health` → `connected: true`

- [ ] **C3**: Register hookd-bridge in `services/registry.yaml`
  - Service name: `hookd-bridge`
  - Type: `compatibility-shim`
  - Depends on: `bloodbank`, `holyfields`

### Dual-Write Phase

- [ ] **C4**: Configure OpenClaw to forward hooks to BOTH:
  1. Direct agent session (existing behavior — kept as safety net)
  2. hookd-bridge endpoint (`POST http://bridge:8099/hooks/{agent}`)
  - This ensures zero downtime: if bridge fails, direct dispatch still works

- [ ] **C5**: Monitor dual-write for 48h minimum
  - Compare: hooks received by bridge vs commands published to Bloodbank
  - Dashboard metric: `bridge_commands_published_total` (add to Holocene OBS-1 dashboard)
  - Alert: bridge error rate > 5% → pause cutover

- [ ] **C6**: Validate command flow end-to-end with pilot agent
  - Send hook to bridge → verify CommandEnvelope on Bloodbank → verify agent adapter receives
  - Check: correlation_id propagates correctly
  - Check: TTL enforcement works (expired hook → error event, not silent drop)

### Tier Rollout (per RFC §8)

- [ ] **D1**: **Tier 1 — Core agents** (Cack, Grolf, Lenoon)
  - Already on host networking, direct bus access
  - Enable command adapter alongside hook dispatch
  - Monitor ack/result rates for 48h
  - Gate: >95% ack rate, >90% result rate, <10% error rate

- [ ] **D2**: **Tier 2 — Engineering agents** (Rererere, Yi)
  - Only after Tier 1 stable for 48h
  - Same monitoring gates as D1

- [ ] **D3**: **Tier 3 — Social/utility agents** (Tonny, Tongy, Rar, Pepe, LalaThing, MomoTheCat)
  - Only after Tier 2 stable for 48h
  - These agents have lower traffic — monitor for 24h minimum

- [ ] **D4**: **Disable direct hook dispatch** per tier
  - Only after all agents in tier have been on dual-write for 48h+
  - Rollback plan: re-enable direct dispatch within 5 minutes

### Deprecation

- [ ] **E1**: All tiers on command adapter only (no direct hooks)
- [ ] **E2**: hookd-bridge kept running for 30 days as rollback safety net
- [ ] **E3**: After 30 days: decommission hookd-bridge
- [ ] **E4**: Remove hook forwarding config from OpenClaw
- [ ] **E5**: Archive bridge code (tag `deprecated/hookd-bridge-v0.1`)

---

## Risk Matrix

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Bridge AMQP disconnect | Commands silently dropped | Medium | Health check + reconnect logic in `aio_pika.connect_robust` |
| Incorrect action inference | Agent receives wrong command | Low | `HOOK_ACTION_MAP` is explicit; fallback uses raw path |
| TTL too aggressive for slow agents | Legitimate commands rejected | Medium | Default 30s; configurable per-call via payload `ttl_ms` |
| Dual-write doubles agent work | Agent processes both hook AND command | HIGH | Agent adapter must deduplicate by `idempotency_key` |
| Bridge latency adds delay | Heartbeats arrive late | Low | Bridge is async (202 Accepted), publish is non-blocking |

---

## Blockers for Live Deployment

1. **B5 — FastStream command consumer**: No agent adapter exists yet. Without this,
   commands published by the bridge have no consumer. The bridge can run (and we can
   verify events land on Bloodbank), but no agent will act on them.

2. **B6 — OpenClaw loopback binding**: Known blocker from RFC. Agents in Docker
   containers can't reach OpenClaw's loopback-bound hooks. Must be resolved for
   the adapter to translate commands back into hook calls.

**Recommendation:** Deploy bridge NOW in observation mode (publish to Bloodbank,
log everything, but don't disable direct hooks). This validates the translation
layer while B5/B6 are resolved in parallel.

---

## Files

| File | Purpose |
|------|---------|
| `hookd/bridge.py` | Bridge service (FastAPI, ~300 LOC) |
| `hookd/CUTOVER_CHECKLIST.md` | This file |
| `tests/conformance/test_command_conformance.py` | Schema + FSM conformance tests (24 tests, GOD-10) |
