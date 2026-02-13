# Infra Dispatcher Migration Guide

> **From**: systemd user service (`infra-dispatch.service`)
> **To**: Docker container (`33god-infra-dispatcher`)
> **Migration Date**: 2026-02-12
> **Owner**: Lenoon (Infrastructure Domain)

---

## What Changed

The Infra Dispatcher was running as a **systemd user service for 4 days** without being containerized. This violated the "one compose, one stack" principle.

**Discovery:**
```bash
systemctl --user status infra-dispatch.service
# Active since Sun 2026-02-08 02:08:41 EST; 4 days ago
```

**Resolution:**
- Containerized in `docker-compose.yml`
- Added to Infrastructure GOD doc
- Documented migration steps

---

## Pre-Migration Checklist

- [ ] Copy current state file (for continuity):
  ```bash
  cp ~/.config/openclaw/infra-dispatch-state.json \
     ~/.config/openclaw/infra-dispatch-state.json.backup
  ```

- [ ] Verify systemd service is healthy:
  ```bash
  systemctl --user status infra-dispatch.service
  journalctl --user -u infra-dispatch.service -f
  ```

- [ ] Note current env vars:
  ```bash
  cat ~/.config/openclaw/infra-dispatch.env
  ```

---

## Migration Steps

### Step 1: Stop Systemd Service

```bash
# Stop the systemd service
systemctl --user stop infra-dispatch.service

# Verify stopped
systemctl --user status infra-dispatch.service
```

### Step 2: Copy State File to New Location

The container expects state at `~/.config/openclaw/infra-dispatch-state.json` which is mounted into `/state/`.

```bash
# Ensure directory exists
mkdir -p ~/.config/openclaw

# State file should already be there (it's the same path)
ls -la ~/.config/openclaw/infra-dispatch-state.json
```

### Step 3: Configure Environment

```bash
cd ~/code/33GOD

# Copy example env
cp .env.example .env

# Edit with your values
nano .env
```

**Required variables:**
```bash
# From ~/.config/openclaw/infra-dispatch.env
OPENCLAW_HOOK_TOKEN=ea867bd199f7db8a0a9c8d2ababc4da8539e466cd6b3076e
OPENCLAW_HOOK_URL=http://100.66.29.76:18789/hooks/agent
OPENCLAW_HOOK_DELIVER=false

# Ready gate configuration
INFRA_READY_STATES=unstarted
INFRA_READY_LABELS=ready,automation:go
INFRA_COMPONENT_LABEL_PREFIX=comp:

# State persistence
INFRA_DISPATCH_STATE_HOST_PATH=~/.config/openclaw/infra-dispatch-state.json

# Health checks
INFRA_RUN_CHECKS=true
INFRA_CHECK_TIMEOUT_SECONDS=900

# Optional: Custom component checks
# INFRA_COMPONENT_CHECKS_JSON={...}
```

### Step 4: Start Container

```bash
# Start just the infra-dispatcher
docker-compose up -d infra-dispatcher

# Or start full stack
docker-compose up -d
```

### Step 5: Verify Container Health

```bash
# Check container logs
docker-compose logs -f infra-dispatcher

# Should see:
# "Starting infra dispatcher (ready_states=('unstarted',), ready_labels=('ready', 'automation-go'))"
# "Bound queue bloodbank.events.v1.infra-dispatcher to key: webhook.plane.#"
```

### Step 6: Test Dispatch Flow

1. Create a test Plane ticket
2. Add labels: `ready`, `automation:go`, `comp:bloodbank`
3. Set state: `unstarted`
4. Check dispatcher logs for processing

```bash
docker-compose logs -f infra-dispatcher | grep -i "dispatching\|m2 check"
```

### Step 7: Disable Systemd Service (Permanent)

**Only after confirming container works:**

```bash
# Disable auto-start
systemctl --user disable infra-dispatch.service

# Stop if still running
systemctl --user stop infra-dispatch.service

# Optional: Remove service file
rm ~/.config/systemd/user/infra-dispatch.service
systemctl --user daemon-reload
```

---

## Rollback Plan

If container fails:

```bash
# Stop container
docker-compose stop infra-dispatcher

# Restart systemd service
systemctl --user start infra-dispatch.service
systemctl --user enable infra-dispatch.service
```

---

## Container vs Systemd Differences

| Aspect | Systemd | Container |
|--------|---------|-----------|
| **State file** | `~/.config/openclaw/infra-dispatch-state.json` | Same file, bind-mounted |
| **Component paths** | Host paths | `/components/*` paths in container |
| **Network** | Host network | Docker network (`33god-network`) |
| **OpenClaw URL** | `http://100.66.29.76:18789` | `http://host.docker.internal:18789` |
| **Logs** | `journalctl` | `docker-compose logs` |
| **Auto-start** | systemd | Docker restart policy |

---

## Health Checks

The container includes health check configuration:

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
  interval: 30s
  timeout: 10s
  retries: 3
```

Check container health:
```bash
docker-compose ps infra-dispatcher
```

---

## Troubleshooting

### Issue: "No such file or directory" for state file

**Fix:**
```bash
mkdir -p ~/.config/openclaw
touch ~/.config/openclaw/infra-dispatch-state.json
```

### Issue: Cannot reach OpenClaw hook

**Fix:** Check `OPENCLAW_HOOK_URL` uses `host.docker.internal`:
```bash
# In .env
OPENCLAW_HOOK_URL=http://host.docker.internal:18789/hooks/agent
```

### Issue: Component health checks fail

**Fix:** Verify component paths in `INFRA_COMPONENT_CHECKS_JSON` use `/components/*`:
```bash
INFRA_COMPONENT_CHECKS_JSON='{"bloodbank":{"cwd":"/components/bloodbank","command":"mise x -- uv run pytest -q"}}'
```

### Issue: Duplicate dispatches

**Cause:** State file not persisted between container restarts.

**Fix:** Ensure volume mount is correct:
```yaml
volumes:
  - ~/.config/openclaw/infra-dispatch-state.json:/state/infra-dispatch-state.json
```

---

## Files Modified

- `docker-compose.yml` — Added `infra-dispatcher` service
- `.env.example` — Added Infra Dispatcher env vars
- `docs/domains/infrastructure/GOD.md` — Documented Infra Dispatcher component

---

## References

- **Source Code**: `bloodbank/event_producers/infra_dispatcher.py`
- **Systemd Config**: `~/.config/systemd/user/infra-dispatch.service`
- **Environment**: `~/.config/openclaw/infra-dispatch.env`
- **State**: `~/.config/openclaw/infra-dispatch-state.json`

---

*Migration completed by Lenoon, 2026-02-12*
