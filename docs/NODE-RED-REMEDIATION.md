# Node-RED Fireflies Flow — Remediation Plan

**Date:** 2026-02-17
**Author:** Grolf (Director of Engineering)
**Trigger:** Unauthorized modifications to Fireflies-Bloodbank flow by outside contributor

---

## Summary

An outside coder modified the Node-RED Fireflies transcription flow without understanding our architecture. The changes mix legitimate bug fixes with dangerous credential leaks, wrong connection info, and a rogue publisher that bypasses Bloodbank's envelope validation.

---

## 1. REVERT (dangerous/wrong changes)

### 1a. Remove hardcoded RabbitMQ creds from config.json
**File:** `services/node-red-flow-orchestrator/flows/fireflies-bloodbank.config.json`
**Problem:** Added `"RABBIT_URL": "amqp://guest:guest@localhost:5672/"` — wrong creds (`guest:guest`), wrong port (`5672` vs our `5673`), and hardcoded in a tracked file. We just completed a nuclear cred scrub.
**Action:** Remove the `RABBIT_URL` line entirely. Creds come from environment.

### 1b. Remove rogue standalone publisher
**File:** `services/node-red-flow-orchestrator/scripts/bloodbank_publish.py` (NEW)
**Problem:** Bypasses Bloodbank's publisher API (`localhost:8682`) and `bb` CLI. Uses raw `aio_pika` with no envelope schema validation — any garbage JSON gets published to the exchange.
**Action:** `git rm` / delete this file. Publishing MUST go through Bloodbank's publisher (API or CLI).

### 1c. Revert bb_publish_upload command
**Node:** `bb_publish_upload` in `fireflies-bloodbank.json`
**Problem:** Changed from `bb publish` to the rogue `bloodbank_publish.py` script with wrong default creds.
**Action:** Revert to using `bb` CLI but with the correct path (see §3a).

### 1d. Revert JSON pretty-printing noise
**File:** `fireflies-bloodbank.json`
**Problem:** Compact JSON reformatted to pretty-printed, creating ~150 lines of noise with zero functional change. Makes git blame useless.
**Action:** Revert all formatting-only changes. Keep the file compact.

### 1e. Fix runtime flows.json
**File:** `~/.node-red/flows.json`
**Problem:** Already deployed with wrong creds and rogue publisher.
**Action:** After fixing the source flow, redeploy to runtime.

---

## 2. KEEP (legitimate fixes)

### 2a. `/usr/bin/env` wrapper on subscriber exec nodes
**Nodes:** `Subscribe upload events`, `Subscribe ready events`
**Why:** Ensures PATH resolution works in spawn mode. Good practice.
**Keep as-is.**

### 2b. Dynamic `msg.filename` on file-write nodes
**Nodes:** `write_upload_envelope`, `csv_file`, `md_file`
**Why:** Previously had static empty filenames, breaking file output. Now correctly uses `msg.filename`.
**Keep as-is.**

### 2c. Robust multi-line JSON parsing for `ready_json`
**Node:** `ready_json` (changed from `json` type to `function` type)
**Why:** The subscriber emits chunked stdout. A bare `json` node chokes on multi-line or concatenated JSON. The new function node splits on newlines and parses each line independently with error handling.
**Keep the logic**, but clean up: move the inline JS to a comment block or keep it minimal.

### 2d. Removed dead hardcoded creds from old subscriber commands
**Why:** Old commands had `amqp://thermite:thermite_dev_password@localhost:5674/` hardcoded. Removing these is correct — but the replacement must use proper env vars, not new wrong creds.

---

## 3. FIX PROPERLY

### 3a. Publisher command — use `bb` CLI with correct path
The old `bb` path (`~/.local/share/uv/tools/bloodbank/bin/bb`) was dead. Fix:

```
bb publish fireflies.transcript.upload --envelope-file
```

Ensure `bb` is on PATH via the Node-RED service environment, or use the absolute path from `which bb`. The `bb` CLI reads `RABBIT_URL` from environment — no inline creds.

If `bb` CLI is truly unavailable, use the **Bloodbank Publisher HTTP API** instead:
```bash
curl -s -X POST http://localhost:8682/publish \
  -H "Content-Type: application/json" \
  -d @${envelope_file}
```

### 3b. RabbitMQ connection — correct values
| Setting | Correct Value |
|---------|--------------|
| Host | `localhost` (from host) or `theboard-rabbitmq` (from container) |
| Port | **`5673`** (host-mapped) |
| Credentials | From environment: `${RABBITMQ_USER}:${RABBITMQ_PASS}` |
| RABBIT_URL format | `amqp://${RABBITMQ_USER}:${RABBITMQ_PASS}@localhost:5673/` |

**Credentials are in 1Password** and injected via `op run` or docker-compose env. Never hardcode.

### 3c. Config.json — environment-only references
`fireflies-bloodbank.config.json` should contain only non-secret config:
```json
{
  "WATCH_DIR": "/home/delorenj/audio/inbox",
  "SCRIPTS_DIR": "/home/delorenj/code/33GOD/services/node-red-flow-orchestrator/scripts"
}
```

`RABBIT_URL` must come from the process environment (systemd unit, `.env` file loaded at runtime, or `op run`).

### 3d. Re-compact the flow JSON
After applying functional changes, re-compact to single-line arrays:
```bash
cd services/node-red-flow-orchestrator/flows
python3 -c "
import json, sys
with open('fireflies-bloodbank.json') as f:
    data = json.load(f)
with open('fireflies-bloodbank.json', 'w') as f:
    json.dump(data, f, separators=(',', ':'))
"
# Then selectively pretty-print only the top-level array for readability
```

Or simply `git checkout` the formatting and manually re-apply only the functional diffs.

---

## 4. Execution Steps

```bash
cd ~/code/33GOD

# Step 1: Backup current state
git stash push -m "pre-remediation-backup" -- \
  services/node-red-flow-orchestrator/flows/fireflies-bloodbank.json \
  services/node-red-flow-orchestrator/flows/fireflies-bloodbank.config.json

# Step 2: Remove rogue publisher
rm services/node-red-flow-orchestrator/scripts/bloodbank_publish.py

# Step 3: Restore config.json (remove RABBIT_URL line)
git checkout -- services/node-red-flow-orchestrator/flows/fireflies-bloodbank.config.json

# Step 4: Restore flow JSON to last committed version
git checkout -- services/node-red-flow-orchestrator/flows/fireflies-bloodbank.json

# Step 5: Now manually re-apply ONLY the legitimate fixes from §2:
#   - /usr/bin/env wrapper on subscriber exec nodes
#   - msg.filename on file-write nodes
#   - Multi-line JSON parser for ready_json
#   - Fix bb_publish_upload to use correct bb path + env-based RABBIT_URL
#   - Fix subscriber commands to use env-based RABBIT_URL (no hardcoded creds)

# Step 6: Verify bb CLI is available
which bb || echo "NEED TO FIX: bb CLI not on PATH"

# Step 7: Verify RabbitMQ connectivity with correct creds
# (load creds from 1Password or .env first)
python3 -c "
import pika
url = 'amqp://${RABBITMQ_USER}:${RABBITMQ_PASS}@localhost:5673/'
conn = pika.BlockingConnection(pika.URLParameters(url))
print('RabbitMQ OK')
conn.close()
"

# Step 8: Redeploy to Node-RED runtime
# Option A: Restart Node-RED (picks up flow file)
sudo systemctl restart nodered
# Option B: Use Node-RED admin API
curl -X POST http://localhost:1880/flows -H "Content-Type: application/json" \
  -d @services/node-red-flow-orchestrator/flows/fireflies-bloodbank.json

# Step 9: Verify flows are running
curl -s http://localhost:1880/flows | python3 -m json.tool | head -20

# Step 10: Commit the clean fix
git add services/node-red-flow-orchestrator/
git commit -m "fix(node-red): remediate unauthorized flow changes

- Reverted hardcoded creds and wrong RabbitMQ port
- Removed rogue aio_pika publisher (use bb CLI)
- Kept: /usr/bin/env wrapper, msg.filename, multi-line JSON parsing
- RABBIT_URL sourced from environment only (port 5673)"
```

---

## Post-Remediation Checklist

- [ ] `bloodbank_publish.py` deleted
- [ ] No hardcoded credentials in any tracked file
- [ ] `RABBIT_URL` points to `localhost:5673` via environment
- [ ] `bb` CLI is on PATH and functional
- [ ] Subscriber nodes use `/usr/bin/env` wrapper
- [ ] `ready_json` uses multi-line parser
- [ ] File nodes use `msg.filename`
- [ ] Runtime `~/.node-red/flows.json` matches source
- [ ] Flow deploys and processes a test event end-to-end
- [ ] `git diff` shows only intentional functional changes (no formatting noise)
