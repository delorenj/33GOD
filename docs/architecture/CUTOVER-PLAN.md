# Agent Tier Rollout & Cutover Plan (GOD-6 / CUTOVER-1)

**Author:** Lenoon (agent:infra)  
**Date:** 2026-02-24  
**Status:** READY — All prerequisites deployed  

---

## Prerequisites (All Complete ✅)

| Component | Ticket | Status |
|-----------|--------|--------|
| Command schemas | GOD-1 | ✅ 4 Holyfields schemas |
| Redis FSM | GOD-2 | ✅ 6 states, Lua CAS |
| Command adapter | GOD-3 | ✅ Running, 11 agents bound |
| hookd bridge | GOD-4 | ✅ Running on :18790 |
| Conformance dashboard | GOD-5 | ✅ Holocene Commands tab |

## Tier Definitions

### Tier 0: Infrastructure Agents (Week 1)
- **Agents:** `lenoon`
- **Why first:** Infra agent, lowest risk, can self-diagnose issues
- **Method:** Redirect heartbeat-router and infra-dispatcher to use hookd-bridge (:18790) instead of OpenClaw hooks (:18789) directly
- **Rollback:** Revert env vars to point back to OpenClaw

### Tier 1: Engineering Agents (Week 2)  
- **Agents:** `grolf`, `rererere`
- **Why second:** Engineering agents with predictable workloads
- **Method:** Same hookd-bridge redirect
- **Validation:** Monitor command conformance dashboard for ack rate > 95%, success rate > 90%

### Tier 2: Application Agents (Week 3)
- **Agents:** `cack`, `rar`, `pepe`, `lalathing`, `momothecat`
- **Why third:** Higher-traffic agents, more diverse command patterns
- **Validation:** 48h burn-in with conformance metrics before proceeding

### Tier 3: Social/Family Agents (Week 4)
- **Agents:** `tonny`, `tongy`, `yi`
- **Why last:** Human-facing agents, lowest tolerance for disruption
- **Validation:** 72h burn-in, Jarad sign-off required

## Cutover Steps Per Tier

### 1. Pre-flight
```bash
# Verify command adapter is healthy
curl -s http://localhost:18790/healthz | jq .status
# Verify agent FSM is initialized
redis-cli -h 33god-redis HGETALL "agent:{name}:fsm"
```

### 2. Redirect Traffic
For each caller (heartbeat-router, infra-dispatcher):
```yaml
# Change env var from:
OPENCLAW_HOOK_URL: http://127.0.0.1:18789/hooks/agent
# To:
OPENCLAW_HOOK_URL: http://127.0.0.1:18790/hooks/agent
```

### 3. Validate
- Watch Holocene Commands tab for the agent
- Confirm: envelope → ack → result lifecycle completes
- Check ack latency < 5s
- Check success rate > 90%

### 4. Burn-in
- Tier 0: 24h
- Tier 1: 48h  
- Tier 2: 48h
- Tier 3: 72h

### 5. Promote
- Mark tier as stable in this document
- Update MEMORY.md
- Close Plane ticket

## Rollback Procedure

Instant rollback per-agent:
1. Change `OPENCLAW_HOOK_URL` back to `:18789`
2. Restart the caller container
3. Agent resumes direct OpenClaw dispatch (no FSM, no command bus)

FSM state persists in Redis but is harmless when not in use.

## Deprecation Timeline

Once all Tier 3 agents are stable (est. Week 5):
1. Remove direct hook dispatch from heartbeat-router and infra-dispatcher
2. Deprecate hookd-bridge (all callers now publish commands directly to Bloodbank)
3. Archive hookd_bridge/ code (keep for reference)
4. Update RFC status to IMPLEMENTED

## Success Criteria

- [ ] All 11 agents processing commands via the adapter
- [ ] Ack rate ≥ 95% across all agents (measured over 24h)
- [ ] Success rate ≥ 90% across all agents
- [ ] Mean ack latency < 5s
- [ ] Zero data loss during cutover (verified via Candystore event counts)
- [ ] Holocene dashboard showing full lifecycle for all agents
