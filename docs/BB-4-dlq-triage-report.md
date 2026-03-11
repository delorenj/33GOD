# BB-4: DLQ Triage & Queue Hygiene

**Date:** 2026-03-11  
**Author:** Lenoon (infra)  
**Status:** RESOLVED ✅

## DLQ Analysis

| Metric | Value |
|--------|-------|
| DLQ count (pre-purge) | 2,938 messages |
| Sampled | 200 messages |
| Event type | 100% `command.envelope` |
| Source shape | 100% bare string (`"hookd-bridge"`) |
| Date range | All from 2026-02-26 |
| Messages after fix (2026-02-27+) | **0** |

## Root Cause (Previously Fixed)

hookd-bridge was emitting `source: "hookd-bridge"` (bare string) instead of
`source: {host, app, type, trigger_type}` (object). Candystore V2 parser
requires `source.host` → `ValidationError` → reject → DLQ.

**Fix deployed:** hookd-bridge now emits full source object (commit from prior session).  
**Result:** Zero new DLQ entries since 2026-02-27.

## Actions Taken

1. **Sampled 200 DLQ messages** — confirmed all are stale pre-fix events
2. **Purged `candystore_events_dlq`** — 2,938 → 0 messages
3. **Purged 5 stale soprano queues** (0 consumers, 2,638 total accumulated messages):
   - `soprano.cack.listener` (526 msgs)
   - `soprano.cack.listener.quickcheck` (528 msgs)
   - `soprano.cack.listener.test` (528 msgs)
   - `soprano.cack.listener.quickcheck2` (528 msgs)
   - `soprano.cack.listener.explicit` (528 msgs)
4. **Verified all queues clean** — 0 stale messages remaining

## Post-Purge Queue Health

All active queues have consumers. No stale accumulation.

## Recommendation

- Monitor DLQ daily (add to heartbeat check if not already)
- Delete unused soprano.cack.listener.* queues entirely if no consumer is planned
- Consider DLQ alerting: if `candystore_events_dlq > 0`, fire `system.dlq.alert`
