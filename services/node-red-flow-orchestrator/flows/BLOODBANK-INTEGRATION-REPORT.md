# Bloodbank Integration Report: Node-RED Flow Orchestrator

**Date:** 2026-02-27
**From:** Node-RED Flow Orchestrator Team
**To:** Lenoon, Director of Bloodbank Infra
**Re:** Blocked event pipeline: Node-RED cannot publish to Bloodbank API

---

## Summary

The Node-RED Fireflies transcription pipeline is broken at the event publishing step. Files upload to MinIO successfully, but the `fireflies.transcript.upload` event never reaches Bloodbank, so the downstream consumer (which calls the Fireflies API) never fires.

Two issues were found and one remains unresolved:

| # | Issue | Status | Owner |
|---|-------|--------|-------|
| 1 | File write nodes had empty property expressions | **Fixed** | Node-RED team |
| 2 | Host-to-container networking on port 8682 rejects connections over IPv6 | **Blocked** | Bloodbank Infra |
| 3 | `source.type` enum missing `webhook` value | **Needs Discussion** | Bloodbank Infra |

---

## Issue 2: IPv6 Connection Reset (Blocking)

### Observed Behavior

```
# From host (fails - curl defaults to IPv6 on this machine):
$ curl -X POST http://localhost:8682/publish ...
> Recv failure: Connection reset by peer

# From host, forcing IPv4 (works):
$ curl -4 -X POST http://127.0.0.1:8682/publish ...
> {"status":"published","event_id":"...","event_type":"test"}

# From inside container (works):
$ docker exec 33god-bloodbank curl -X POST http://localhost:8682/publish ...
> {"status":"published","event_id":"...","event_type":"test"}
```

### Root Cause

The `33god-bloodbank` container binds port 8682 on both `0.0.0.0` (IPv4) and `[::]` (IPv6). Docker's proxy listens on both, but the uvicorn process inside the container only binds `127.0.0.1:8682` (IPv4). When `curl` on this host resolves `localhost` to `::1` first (standard on this system), the connection reaches docker-proxy on IPv6, gets forwarded to the container, but uvicorn rejects it.

Node-RED's exec nodes use `curl -s` to publish, which follows the system resolver and hits IPv6 first, causing silent failures.

### Evidence

```
$ ss -tlnp 'sport = :8682'
LISTEN  0.0.0.0:8682  users:(("docker-proxy",pid=3038357))
LISTEN     [::]:8682  users:(("docker-proxy",pid=3038364))
```

The pm2-managed `bloodbank-api` process (non-Docker) previously held this port but crashed in a restart loop:
```
ERROR: [Errno 98] error while attempting to bind on address ('0.0.0.0', 8682): address already in use
```
This is because the Docker container already owns the port. The pm2 process is a stale registration and should be removed or reconfigured.

### Recommended Fix Options

**Option A (quick, Node-RED side):** Change the curl commands in the flow to use `127.0.0.1` instead of `localhost`:
```
curl -s -X POST http://127.0.0.1:8682/publish ...
```

**Option B (proper, Bloodbank Infra side):** Bind uvicorn inside the container to `0.0.0.0:8682` instead of `127.0.0.1:8682` so both IPv4 and IPv6 forwarding works.

**Option C (also proper):** Configure the Docker Compose service with `network_mode: host` or ensure the published port mapping forwards correctly.

We can apply Option A immediately as a workaround if Options B/C need a release cycle.

---

## Issue 3: `source.type` Enum Gap

### Observed Behavior

The Bloodbank container logs show repeated validation errors:

```
Error broadcasting RabbitMQ event to WebSocket: 1 validation error for EventEnvelope
source.type
  Input should be 'manual', 'agent', 'scheduled', 'heartbeat', 'file_watch' or 'hook'
  [type=enum, input_value='webhook', input_type=str]
```

### Context

The Node-RED Webhook tab (Fireflies webhook receiver) will produce events with `source.type: "hook"` which is in the allowed set. However, other producers in the ecosystem are sending `source.type: "webhook"` which gets rejected.

**Current allowed values:** `manual`, `agent`, `scheduled`, `heartbeat`, `file_watch`, `hook`

### Question for Lenoon

Should `webhook` be added to the `source.type` enum? Or should producers sending `webhook` be updated to use `hook` instead? Node-RED flows currently use `file_watch` and `hook`, both of which are valid.

---

## Current Architecture: How Node-RED Publishes

```
Node-RED exec node
  → curl -s -X POST http://localhost:8682/publish
    -H "Content-Type: application/json"
    -d @/path/to/envelope.json
  → Bloodbank API (Docker: 33god-bloodbank)
    → RabbitMQ exchange: bloodbank.events.v1
      → Consumer queues
```

### Envelope format (what Node-RED sends):

```json
{
  "event_type": "fireflies.transcript.upload",
  "event_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "version": "1.0.0",
  "source": {
    "host": "node-red",
    "type": "file_watch",
    "app": "node-red"
  },
  "correlation_ids": [],
  "payload": { ... }
}
```

The `/publish` endpoint accepts `additionalProperties: true` on the request body, wraps it in an internal envelope, and publishes to RabbitMQ. This works correctly when the connection succeeds (verified from inside the container and via forced IPv4).

---

## PM2 Cleanup Note

The `bloodbank-api` pm2 process (id: 7) is stale. It was the pre-Docker way of running the API and will never start while the Docker container holds port 8682. It should be removed from pm2:

```bash
pm2 delete bloodbank-api
```

Similarly, `bloodbank-bridge` (id: 6) appears to be an OpenClaw-specific bridge. Confirm whether it's still needed or if the Docker container subsumes its role.

---

## Action Items

| Priority | Action | Owner |
|----------|--------|-------|
| P0 | Fix IPv6/IPv4 port binding so host processes can reach Bloodbank API | Bloodbank Infra |
| P0 (workaround) | Switch Node-RED curl to `127.0.0.1` until proper fix lands | Node-RED team |
| P1 | Decide on `webhook` vs `hook` for `source.type` enum | Bloodbank Infra |
| P2 | Clean up stale pm2 entries for `bloodbank-api` and `bloodbank-bridge` | Bloodbank Infra |
| P2 | Document the `/publish` endpoint contract for cross-team consumers | Bloodbank Infra |
