# BB-3: Decentralized Local Scheduler Cutover

**Ticket:** BB-3 (Plane ticket creation blocked — API key expired, needs refresh)  
**Directive:** Jarad via Cack, 2026-03-07: one-shot cutover, no phased migration  
**Owner:** Lenoon (infra)  
**Status:** EXECUTING

## What Changed

### Before (Centralized Architecture)
```
heartbeat-tick (publisher) → system.heartbeat.tick → RabbitMQ → heartbeat-router (consumer) → OpenClaw hooks
```
- Two containers: `33god-heartbeat-tick` + `33god-heartbeat-router`
- Global tick published every 60s to RabbitMQ
- Router consumed ticks and dispatched agent checks
- Stale crontab: `rererere_heartbeat_worker.py` running outside Docker

### After (Decentralized Local Scheduler)
```
heartbeat-router (local_scheduler) → asyncio timer → scan workspaces → dispatch via OpenClaw hooks
                                   └→ Bloodbank publish (best-effort, observability only)
```
- Single container: `33god-heartbeat-router` running `heartbeat_tick.local_scheduler`
- No RabbitMQ dependency for tick generation (self-ticking via asyncio)
- RabbitMQ used for best-effort dispatch event publishing only
- Scans `heartbeat.json` from all agent workspaces on each tick

## Cutover Actions (One-Shot)

1. ✅ `local_scheduler.py` already deployed and running in `33god-heartbeat-router`
2. ✅ Compose updated: heartbeat-router command changed to `heartbeat_tick.local_scheduler`
3. ✅ Compose updated: heartbeat-tick service REMOVED from compose
4. ☐ Stop and remove orphaned `33god-heartbeat-tick` container
5. ☐ Remove stale crontab entry: `rererere_heartbeat_worker.py`
6. ☐ Remove old `system.heartbeat.tick` queue from RabbitMQ (cleanup)
7. ☐ Verify local scheduler is dispatching correctly post-cutover
8. ☐ Commit + push all changes

## Rollback

If local scheduler fails:
```bash
# 1. Restore heartbeat-tick to compose (add service definition back)
# 2. Revert heartbeat-router command to: ["python", "-m", "heartbeat_tick.router"]
# 3. docker compose up -d heartbeat-tick heartbeat-router
# 4. Verify system.heartbeat.tick events flowing
```

Keep `publisher.py` and `router.py` in the repo for rollback capability.
Do NOT delete them until 7-day burn-in passes.

## Evidence Required
- `docker ps` showing only `33god-heartbeat-router` (no `33god-heartbeat-tick`)
- `crontab -l` showing no heartbeat entries
- Local scheduler logs showing successful dispatches
- No `system.heartbeat.tick` queue in RabbitMQ
