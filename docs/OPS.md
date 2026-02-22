# 33GOD Operations — OPS.md

> **Guaranteed Operational Document** — Read this before building, deploying, or touching infrastructure.
>
> **Last Updated**: 2026-02-22

---

## The One Rule

**Run `mise build` or `mise deploy`. Nothing else.**

The mise task system encapsulates all toolchain logic. You don't need to remember `docker compose build`, `pnpm install`, `uv sync`, or any other command. The `mise.toml` in each component knows what to do.

If you change code and it needs to reach production → `mise deploy`.

---

## Cascading Build System

Tasks cascade from root to components. Same command everywhere, different scope.

### From the root (`~/code/33GOD/`)

| Command | What happens |
|---------|--------------|
| `mise build` | Builds **all** components (deps + Docker images) |
| `mise deploy` | Builds + restarts **all** Docker services |
| `mise build:infra` | Builds Bloodbank + WS relay only |
| `mise build:frontend` | Builds Holocene only |
| `mise deploy:infra` | Deploys Bloodbank stack only |
| `mise deploy:frontend` | Deploys Holocene only |

### From a component directory (e.g. `~/code/33GOD/bloodbank/`)

| Command | What happens |
|---------|--------------|
| `mise build` | Builds **this component only** (deps + Docker) |
| `mise deploy` | Builds + restarts **this component's containers** |
| `mise test` | Runs this component's tests |
| `mise lint` | Lints this component |
| `mise health` | Component-specific health check |
| `mise dev` | Dev server (where applicable) |
| `mise logs` | Tail container logs |

### The cascade rule

The **local** `mise.toml` always wins. Running `mise build` in `holocene/` runs Holocene's build task (pnpm + vite + docker), not the root's "build everything" task. This is by design — same command, scoped to where you are.

---

## Component Build Matrix

| Component | Toolchain | Has Docker | mise.toml |
|-----------|-----------|------------|-----------|
| **bloodbank** | Python (uv) | ✅ bloodbank + ws-relay | ✅ |
| **holocene** | Node (pnpm) | ✅ holocene | ✅ |
| **hookd** | Node (bun) | ❌ | ✅ |
| candybar | Node (bun) | ❌ | ❌ (TODO) |
| candystore | Python (uv) | ❌ | ❌ (TODO) |
| flume | Node (pnpm) | ❌ | ❌ (TODO) |
| theboard | Python (uv) | ✅ | ❌ (TODO) |
| perth | Rust (cargo) | ❌ | ❌ (TODO) |

**Rule:** If a component doesn't have a `mise.toml`, it doesn't participate in the cascade yet. Add one following the pattern in existing components.

---

## Docker Compose Services

All containerized services live in `~/code/33GOD/docker-compose.yml`.

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `bloodbank` | 33god-bloodbank | 8682 | Event bus API + publisher |
| `bloodbank-ws-relay` | 33god-bloodbank-ws-relay | 8683 | WebSocket event relay |
| `holocene` | 33god-holocene | 11819 | Dashboard frontend |
| `redis` | redis:7-alpine | 6379 | Cache + correlation tracking |
| `postgres` | postgres:16-alpine | 5432 | Asset registry + event store |
| `theboard-rabbitmq` | rabbitmq:3.12-management | 5673/15673 | Message broker |

### Quick operations

```bash
mise up          # Start all services (no rebuild)
mise down        # Stop all services
mise ps          # Show service status
mise logs        # Tail all logs
mise health      # Full health check
mise status      # Containers + git state
```

---

## Event Flow Architecture

```
Agent action
    ↓
POST http://bloodbank:8682/events/custom
    ↓
RabbitMQ (bloodbank.events.v1 exchange, TOPIC)
    ↓ routing_key: agent.{name}.{action}
bloodbank-ws-relay (consumes agent.#)
    ↓
WebSocket broadcast (ws://bloodbank-ws-relay:8683)
    ↓
Holocene nginx proxy (/ws → relay:8683)
    ↓
Dashboard stream (useBloodbankStream hook)
```

---

## Adding a New Component

1. Create `mise.toml` in the component directory
2. Define at minimum: `build`, `test` tasks
3. If it has a Dockerfile, add `deploy` task that runs `docker compose build` + `up -d`
4. Add the component name to the root `mise.toml` COMPONENTS array in the `build` task
5. Add a `<component>:build` shortcut in root `mise.toml`
6. Register in `components.toml` manifest

**Template for a Python component with Docker:**

```toml
[env]
_.file = [".env"]

[tasks.build]
description = "Build <component>: Python deps + Docker image"
run = """
#!/usr/bin/env bash
set -euo pipefail
echo "▸ <component>: syncing deps..."
uv sync --quiet
echo "▸ <component>: building Docker image..."
cd {{ config_root }}/..
docker compose build <service-name>
echo "✅ <component>: built"
"""

[tasks.deploy]
description = "Deploy <component>"
depends = ["build"]
run = """
#!/usr/bin/env bash
set -euo pipefail
cd {{ config_root }}/..
docker compose up -d <service-name>
echo "✅ <component>: deployed"
"""

[tasks.test]
description = "Run tests"
run = "uv run pytest -q tests/"
```

**Template for a Node component (no Docker):**

```toml
[tasks.build]
description = "Build <component>"
run = """
#!/usr/bin/env bash
set -euo pipefail
bun install --silent
bun run build
echo "✅ <component>: built"
"""

[tasks.test]
run = "bun run test"
```

---

## Critical Rules

1. **Never run `docker compose build` directly.** Use `mise build` or `mise deploy`. The mise task handles deps + build + any pre-steps.

2. **Never edit a running container.** If you change code, run `mise deploy` to rebuild the image and restart the container. Docker layer caching will make unchanged layers fast.

3. **Always commit before deploying.** The Docker build copies your working directory. Uncommitted changes get baked into the image with no traceability.

4. **If you add a Dockerfile, add a mise deploy task.** No Docker service should exist without a corresponding mise task.

5. **If health fails, check logs.** `mise logs` or `mise -C <component> run logs`.

---

## Troubleshooting

### "I changed code but the container doesn't reflect it"
```bash
mise deploy   # Rebuilds Docker image + restarts
```

### "mise build says 'no such task'"
```bash
mise trust    # Trust the mise.toml in this directory
mise tasks    # List available tasks
```

### "Docker build is using cached layers"
```bash
# Add --no-cache (one-time escape hatch)
docker compose build --no-cache <service>
docker compose up -d <service>
```

### "Which container am I looking at?"
```bash
mise ps       # Shows all services + status
mise health   # Shows health + queue state
```

### "Holocene dashboard shows no events"
Three things to check:
1. **Is the WS relay running?** `docker ps | grep ws-relay`
2. **Is the agent status emitter running?** `crontab -l | grep emit-agent-status`
3. **Is the relay bound to `#`?** `docker logs 33god-bloodbank-ws-relay 2>&1 | grep Bound`
   - Must say `routing key '#'`, NOT `'agent.#'`

### "RabbitMQ authentication failed after password rotation"
Password rotations must be atomic:
```bash
# 1. Update the .env file
vim ~/code/33GOD/.env  # Change RABBITMQ_PASS

# 2. Change the password in RabbitMQ
docker exec theboard-rabbitmq rabbitmqctl change_password delorenj "<new_password>"

# 3. Restart ALL dependent services
docker compose restart bloodbank bloodbank-ws-relay
```
Never rotate the password without steps 1-3 in sequence.

### "API returns 200 but events don't appear in dashboard"
This is the most dangerous failure mode — silent data loss. Check in order:
1. Relay messages must include `"type": "event"` — check `websocket-relay/relay.py`
2. Publisher must use `mandatory=True` + `on_return_raises=True` — check `event_producers/rabbit.py`
3. Routing key must match queue bindings — check `docker exec theboard-rabbitmq rabbitmqctl list_bindings`

---

_Grolf 🪨 — "Run mise build. That's it."_
