# 33GOD Docker Compose — First Startup Guide

> **Author**: Grolf, Director of Engineering  
> **Date**: 2026-02-17  
> **Status**: Pre-launch checklist

---

## TL;DR — What to Change Before `docker-compose up`

Three things block you right now:

1. **Container name conflict**: The compose defines `container_name: theboard-rabbitmq` but that container already exists (from `trunk-main`). You'll get an error.
2. **Network mismatch**: Traefik routes via the `proxy` network. 33GOD services are on `33god-network`. Traefik can't see them → Bloodbank and Holocene labels do nothing.
3. **Duplicate RabbitMQ**: You don't need a second RabbitMQ. The existing one is fine.

---

## 1. Network Strategy

### The Problem

Traefik discovers containers via Docker labels, but **only on networks it's connected to** — which is `proxy`. The compose puts everything on `33god-network`, so Traefik will never route to Bloodbank (`bloodbank.delo.sh`) or Holocene (`holocene.delo.sh`) even though the labels are correct.

### The Fix

Services need to be on **both** networks:
- `proxy` — so Traefik can reach them
- `33god-network` — so they can talk to each other by service name (redis, rabbitmq, etc.)

Only services with `traefik.enable=true` labels need the `proxy` network. Internal-only services (RabbitMQ, Redis, infra-dispatcher) stay on `33god-network` only.

**Changes to `docker-compose.yml`:**

```yaml
# At the bottom, replace the networks block:
networks:
  33god-network:
    name: 33god-network
    driver: bridge
  proxy:
    external: true    # Use Traefik's existing network
```

Then add `proxy` to `bloodbank` and `holocene` services:

```yaml
  bloodbank:
    networks:
      - 33god-network
      - proxy          # ← ADD THIS

  holocene:
    networks:
      - 33god-network
      - proxy          # ← ADD THIS
```

Leave `rabbitmq`, `redis`, and `infra-dispatcher` on `33god-network` only.

---

## 2. RabbitMQ: Use the Existing One

### Current State

| Container | Compose Project | Network | Host Ports |
|-----------|----------------|---------|------------|
| `theboard-rabbitmq` | `trunk-main` | `trunk-main_theboard-network` | 5673:5672, 15673:15672 |
| `plane-rabbitmq` | `plane` | `proxy` | none |

The 33GOD compose tries to create **another** `theboard-rabbitmq` → instant name conflict.

### What About `plane-rabbitmq`?

Keep it. Plane has its own RabbitMQ with its own vhosts/users. Don't share it — that's correct isolation.

### The Fix: Remove RabbitMQ from 33GOD Compose

The existing `theboard-rabbitmq` (from `trunk-main`) is the same RabbitMQ that 33GOD needs. Instead of defining a new one, connect to it.

**Option A — External network (recommended):**

Remove the `rabbitmq` service entirely from the 33GOD compose. Instead, connect the services that need it to the existing RabbitMQ's network:

```yaml
networks:
  33god-network:
    name: 33god-network
    driver: bridge
  proxy:
    external: true
  theboard-network:
    name: trunk-main_theboard-network
    external: true      # Already exists from trunk-main
```

Then for `bloodbank` and `infra-dispatcher`:

```yaml
  bloodbank:
    networks:
      - 33god-network
      - proxy
      - theboard-network   # ← to reach theboard-rabbitmq
    # Remove depends_on: rabbitmq

  infra-dispatcher:
    networks:
      - 33god-network
      - theboard-network   # ← to reach theboard-rabbitmq
    # Remove depends_on: rabbitmq
```

Also remove:
- The entire `rabbitmq:` service block
- The `rabbitmq-data:` volume

The `RABBITMQ_URL` env vars already point to `theboard-rabbitmq:5672` — that hostname resolves because the container's hostname is `theboard-rabbitmq` and they'll be on the same Docker network.

**Option B — Migrate RabbitMQ into 33GOD compose:**

Stop the `trunk-main` compose's RabbitMQ and let 33GOD own it. This is cleaner long-term but means updating `trunk-main` to also use an external reference. Do this later when you retire `trunk-main`.

**Recommendation: Option A now, Option B later.**

---

## 3. Why Is It Called "TheBoard"?

**TheBoard** is one of the 33GOD components — it's the brainstorming/meeting orchestration system (see the "Meeting & Collaboration" domain in GOD.md). Early in development, the first thing that needed RabbitMQ was TheBoard's real-time meeting event flow, so the container got named `theboard-rabbitmq`.

Over time, RabbitMQ became the **system-wide event bus** (Bloodbank), not just TheBoard's thing. The name stuck.

### Should It Be Renamed?

**Yes, eventually.** The correct name would be `33god-rabbitmq` or just `rabbitmq` (within the 33GOD compose context). But renaming means:
- Updating `trunk-main` compose
- Updating any hardcoded connection strings
- Recreating the container (data persists in the volume)

**Not urgent.** The hostname in `RABBITMQ_URL` is just a DNS name on the Docker network. When you consolidate to a single compose (Option B above), rename it then.

---

## 4. Step-by-Step: First Startup

### Prerequisites

```bash
# Confirm existing infra is running
docker ps | grep -E 'traefik|theboard-rabbitmq'
# Both should be running
```

### Step 1: Edit docker-compose.yml

Apply these changes:

1. **Delete the entire `rabbitmq:` service block** (lines ~10-32)
2. **Delete `rabbitmq-data:` from the volumes section**
3. **Remove `depends_on: rabbitmq` from `bloodbank` and `infra-dispatcher`**
4. **Replace the `networks:` section** at the bottom:

```yaml
networks:
  33god-network:
    name: 33god-network
    driver: bridge
  proxy:
    external: true
  theboard-network:
    name: trunk-main_theboard-network
    external: true
```

5. **Update service networks:**

```yaml
  bloodbank:
    networks:
      - 33god-network
      - proxy
      - theboard-network

  holocene:
    networks:
      - 33god-network
      - proxy

  infra-dispatcher:
    networks:
      - 33god-network
      - theboard-network

  redis:
    networks:
      - 33god-network    # (unchanged)
```

### Step 2: Create .env file

```bash
cd ~/code/33GOD
cp .env.example .env  # if it exists, otherwise create:
```

Required variables:
```env
RABBITMQ_USER=delorenj
RABBITMQ_PASS=<get from existing rabbitmq or 1Password>
RABBITMQ_VHOST=/
BLOODBANK_EXCHANGE=bloodbank.events.v1
PLANE_33GOD_API_KEY=<from 1Password if needed>
```

### Step 3: Build and start

```bash
cd ~/code/33GOD

# Build images first (bloodbank + holocene have Dockerfiles)
docker compose build

# Start just redis first
docker compose up -d redis

# Then the rest
docker compose up -d
```

### Step 4: Verify

```bash
# Check all containers started
docker compose ps

# Check Bloodbank can reach RabbitMQ
docker compose logs bloodbank | tail -20

# Check Traefik picked up the new services
curl -s https://bloodbank.delo.sh/health
curl -s https://holocene.delo.sh/health
```

---

## 5. Other Issues to Watch

| Issue | Detail | Severity |
|-------|--------|----------|
| **Redis port conflict** | Host port 6380 — check nothing else uses it: `ss -tlnp \| grep 6380` | Low |
| **Bloodbank port 8682** | Exposed on host — fine for dev, but Traefik should be the entry point in prod | Low |
| **Holocene port 11819** | Same as above | Low |
| **`host.docker.internal`** | Used in infra-dispatcher's `OPENCLAW_HOOK_URL` — works on Docker Desktop, on Linux needs `extra_hosts: ["host.docker.internal:host-gateway"]` | **Medium** |
| **Volume mounts** | `INFRA_DISPATCH_STATE_HOST_PATH` defaults to `~/.config/openclaw/infra-dispatch-state.json` — ensure file exists or Docker creates a directory instead | Low |
| **Holyfields schemas** | `./holyfields/schemas` mounted into Bloodbank — confirm directory exists | Low |

### Linux `host.docker.internal` Fix

Add to `infra-dispatcher`:

```yaml
  infra-dispatcher:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

---

## Summary of Compose Changes

```diff
 # Remove entire rabbitmq service block
-  rabbitmq:
-    image: rabbitmq:3-management-alpine
-    ... (entire block)

 # Remove rabbitmq volume
-  rabbitmq-data:
-    driver: local

 # Bloodbank: add networks, remove rabbitmq dependency
   bloodbank:
-    depends_on:
-      rabbitmq:
-        condition: service_healthy
     depends_on:
       redis:
         condition: service_healthy
     networks:
       - 33god-network
+      - proxy
+      - theboard-network

 # Holocene: add proxy network
   holocene:
     networks:
       - 33god-network
+      - proxy

 # Infra-dispatcher: add theboard-network, remove rabbitmq dep
   infra-dispatcher:
-    depends_on:
-      rabbitmq:
-        condition: service_healthy
     networks:
       - 33god-network
+      - theboard-network
+    extra_hosts:
+      - "host.docker.internal:host-gateway"

 # Networks section
 networks:
   33god-network:
     name: 33god-network
     driver: bridge
+  proxy:
+    external: true
+  theboard-network:
+    name: trunk-main_theboard-network
+    external: true
```
