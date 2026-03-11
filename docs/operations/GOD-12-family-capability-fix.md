# GOD-12: Family Agent Capability Fix

## Issue
`agent:family:main` had `capabilities=none` at runtime, blocking dream-cycle artifact persistence and ACK dispatch.

**Symptoms:**
- Dream cycle cron completing but no artifacts persisted
- No ACK file created
- HIGH anomalies from observability touchpoint

## Root Cause
Family agent config had `write` and `exec` in `tools.deny` list:
```json
{
  "id": "family",
  "tools": {
    "allow": ["read", "web_search", "web_fetch", "memory_recall", "memory_store"],
    "deny": ["exec", "write", "edit", "browser", "canvas", "nodes", "gateway"]
  }
}
```

## Fix Applied
Moved `write`, `edit`, `exec` from deny to allow, added `sessions_send`:
```json
{
  "id": "family",
  "tools": {
    "allow": [
      "read", "write", "edit", "exec",
      "web_search", "web_fetch",
      "memory_recall", "memory_store",
      "sessions_send"
    ],
    "deny": ["browser", "canvas", "nodes", "gateway"]
  }
}
```

**Config file:** `~/.openclaw/openclaw.json` (agents.list[])

## Verification
**Test 1: Write capability**
```bash
ls -lh ~/.openclaw/workspace-tonny/god-12-capability-test.txt
# -rw-rw-r-- 1 delorenj delorenj 25 Mar 10 22:01 god-12-capability-test.txt
cat ~/.openclaw/workspace-tonny/god-12-capability-test.txt
# Write capability verified
```

**Test 2: Dream cycle artifacts**
```bash
ls -lh /home/delorenj/d/33GOD/2026-03-10/dream-*family*
# -rw-rw-r-- 1 delorenj delorenj  184 Mar 10 22:02 dream-ack-family.txt
# -rw-rw-r-- 1 delorenj delorenj 1.6K Mar 10 22:02 dream-cycle-family.md
```

**Test 3: sessions_send**
Verified via agent output:
```
ACK to `agent:main:main` | via sessions_send | ✅ Dispatched
```

## Acceptance Criteria
- [x] Family can write artifact files
- [x] Family can write ACK files  
- [x] Family can send ACK via sessions_send
- [x] One successful dream cycle with all artifacts persisted
- [x] No HIGH anomaly repeat expected on next touchpoint

## Related
- Issue: https://github.com/delorenj/33GOD/issues/4
- Agent: family
- Dream cron: b721ac71-51b6-4e35-94de-63977c0723fa
