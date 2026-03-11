# GOD-11: SVGMe Cron Trigger Transport Fix

## Issue
Cron 6387dcb0 (MomoCrankTrigger) was attempting sessions_send from systemEvent context where tool is unavailable.

## Fix Applied  
Configured cron with announce delivery via openclaw CLI:
```bash
openclaw cron edit 6387dcb0-da53-4dbd-b84a-d8b032ebda58 \
  --announce \
  --to "agent:main:main" \
  --channel last
```

This uses built-in cron delivery mechanism instead of requiring sessions_send in payload.

## Verification
Check delivery configuration:
```bash
openclaw cron list | grep MomoCrankTrigger
# Delivery mode should show: announce
```

Check run logs for delivery:
```bash
tail -1 ~/.openclaw/cron/runs/6387dcb0-da53-4dbd-b84a-d8b032ebda58.jsonl | jq '.deliveryStatus'
# Should show: "delivered" (not "not-requested")
```

## Related
- Issue: https://github.com/delorenj/33GOD/issues/2  
- Job ID: 6387dcb0-da53-4dbd-b84a-d8b032ebda58
- Cron: MomoCrankTrigger
