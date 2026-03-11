# GOD-11: Observability False-Positive Fix

## Issue
Observability touchpoint (`agent:main:cron:f9f1a844...`) reports `agent:svgme:cron:6387dcb0...` as failed based on stale historical session logs.

**Actual current state (verified):**
```
job_id: 6387dcb0-da53-4dbd-b84a-d8b032ebda58
name: MomoCrankTrigger
lastStatus: ok
consecutiveErrors: 0
lastDurationMs: 0
```

## Root Cause
Observability queries `sessions_list` and matches sessionKey patterns like `agent:svgme:cron:6387dcb0-*`, returning historical aborted sessions from before job migration to systemEvent pattern.

## Fix Implementation

### 1. Query Strategy Change
**Before:** Match on `sessionKey` pattern from `sessions_list`
```python
# OLD - returns stale sessions
sessions = sessions_list()
svgme_cron = [s for s in sessions if 'svgme:cron:6387' in s.sessionKey]
```

**After:** Query cron job state directly
```python
# NEW - current job state only
crons = cron_list()
svgme = next(c for c in crons if c.id == '6387dcb0-da53-4dbd-b84a-d8b032ebda58')
health = {
    'lastStatus': svgme.state.lastStatus,
    'consecutiveErrors': svgme.state.consecutiveErrors
}
```

### 2. Health Signal
**Escalate only when:**
- `state.consecutiveErrors > 0` OR
- `state.lastStatus != 'ok'`

**Suppress:**
- Historical session anomalies when current job state is green

### 3. Output Format
Include job-level state in observability reports:
```
agent:svgme:cron:6387dcb0... | lastStatus=ok | consecutiveErrors=0 | ✓ HEALTHY
```

## Verification
```bash
# Check current job state
openclaw cron list | grep 6387dcb0
# Should show: lastStatus=ok, consecutiveErrors=0

# Verify no false alarms in next observability run
tail ~/.openclaw/cron/runs/f9f1a844-cdc1-4b8e-8c57-c7c8d80ea191.jsonl
# Should not flag svgme cron if job state is green
```

## Related
- Issue: https://github.com/delorenj/33GOD/issues/2
- Observability cron: f9f1a844-cdc1-4b8e-8c57-c7c8d80ea191
- SVGMe cron: 6387dcb0-da53-4dbd-b84a-d8b032ebda58
