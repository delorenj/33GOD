# C4 Level 2: Container Diagram - 33GOD Compose Stack

> Every service in compose.yml and the external systems they depend on.

```mermaid
C4Container
  title Container Diagram - 33GOD Docker Compose Stack

  Person(dev, "Developer", "Monitors dashboards, manages tickets")
  Person(agent, "AI Agent", "Runs in OpenClaw workspace")

  System_Ext(openclaw, "OpenClaw", "Agent runtime — hook endpoints at :18789/:18790")
  System_Ext(plane, "Plane", "Project board — webhooks + API")
  System_Ext(postgres, "PostgreSQL", "192.168.1.12:5432 — platform DB")
  System_Ext(traefik, "Traefik Proxy", "TLS + OAuth at *.delo.sh")

  System_Boundary(infra, "Infrastructure Layer") {
    ContainerQueue(rabbitmq, "RabbitMQ", "3.12 Management Alpine", "Topic exchange: bloodbank.events.v1")
    ContainerDb(redis, "Redis", "7 Alpine", "Correlation tracking, caching, FSM state")
  }

  System_Boundary(core, "Core Event Bus") {
    Container(bloodbank, "Bloodbank", "FastAPI / Python", "Event bus HTTP API — publish, validate, route")
    Container(wsrelay, "Bloodbank WS Relay", "Python", "WebSocket fan-out of live events to browsers")
  }

  System_Boundary(persistence, "Persistence Layer") {
    Container(candystore, "Candystore", "FastAPI / Python", "Event store — persists ALL events to PostgreSQL, serves REST query API")
    Container(pgbridge, "Postgres Notify Bridge", "Python", "Forwards PG NOTIFY channel events into Bloodbank")
  }

  System_Boundary(dashboard, "Dashboard Layer") {
    Container(holocene, "Holocene", "Vite / React / nginx", "Mission Control — real-time event dashboard + Plane proxy")
  }

  System_Boundary(dispatch, "Dispatch Layer (host network)") {
    Container(infra_disp, "Infra Dispatcher", "Python", "Plane webhook events → OpenClaw agent dispatch with ready-gate")
    Container(task_triage, "Task Triage Dispatcher", "Python", "task.inbox.issue.created → OpenClaw triage consumer")
    Container(hookd, "hookd Bridge", "Python", "Legacy hook calls → Bloodbank command envelopes (outbox pattern)")
    Container(cmd_adapter, "Command Adapter", "Python", "Bloodbank commands → FSM guard validation → OpenClaw hook dispatch")
  }

  System_Boundary(agents, "Agent Support (host network)") {
    Container(heartbeat, "Heartbeat Router", "Python", "Self-ticking scheduler — scans agent heartbeat.json, dispatches overdue checks")
    Container(ctx_mon, "Context Monitor", "Python", "Polls agent context usage, enforces 90% compaction policy, resets sessions")
  }

  %% Developer interactions
  Rel(dev, holocene, "Views events, Plane boards", "HTTPS")
  Rel(holocene, bloodbank, "Fetches event metadata", "HTTP")
  Rel(holocene, wsrelay, "Subscribes to live events", "WebSocket")
  Rel(holocene, candystore, "Queries event history", "HTTP REST")

  %% Core event bus wiring
  Rel(bloodbank, rabbitmq, "Publishes validated events", "AMQP")
  Rel(bloodbank, redis, "Tracks correlation IDs", "Redis protocol")
  Rel(wsrelay, rabbitmq, "Subscribes routing_key=#", "AMQP")

  %% Persistence
  Rel(candystore, rabbitmq, "Consumes ALL events", "AMQP")
  Rel(candystore, postgres, "Persists events as JSONB", "SQL")
  Rel(pgbridge, postgres, "Listens on NOTIFY channel", "libpq")
  Rel(pgbridge, bloodbank, "Forwards DB events", "HTTP POST")

  %% Dispatch layer
  Rel(infra_disp, rabbitmq, "Consumes plane webhook events", "AMQP")
  Rel(infra_disp, openclaw, "Dispatches agent tasks", "HTTP hook")
  Rel(task_triage, rabbitmq, "Consumes task.inbox events", "AMQP")
  Rel(task_triage, openclaw, "Dispatches triage tasks", "HTTP hook")
  Rel(hookd, rabbitmq, "Publishes command envelopes", "AMQP")
  Rel(agent, hookd, "Legacy hook calls", "HTTP POST")
  Rel(cmd_adapter, rabbitmq, "Consumes command events", "AMQP")
  Rel(cmd_adapter, redis, "Reads/writes FSM state", "Redis protocol")
  Rel(cmd_adapter, openclaw, "Dispatches validated commands", "HTTP hook")

  %% Agent support
  Rel(heartbeat, rabbitmq, "Publishes dispatch events (best-effort)", "AMQP")
  Rel(heartbeat, openclaw, "Dispatches overdue heartbeat checks", "HTTP hook")
  Rel(ctx_mon, rabbitmq, "Publishes context events", "AMQP")

  %% External routing
  Rel(traefik, bloodbank, "bloodbank.delo.sh", "HTTPS")
  Rel(traefik, holocene, "holocene.delo.sh", "HTTPS")
  Rel(traefik, rabbitmq, "rabbit.delo.sh (mgmt UI)", "HTTPS")
  Rel(traefik, wsrelay, "bloodbank-ws.delo.sh", "WSS")

  UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="2")
```

## Service Summary

| Service | Image/Build | Network | Ports (host) | Depends On |
|---------|-------------|---------|--------------|------------|
| **redis** | `redis:7-alpine` | 33god-network | 6381 | — |
| **rabbitmq** | `rabbitmq:3.12-management-alpine` | 33god-network + proxy | 5673, 15673 | — |
| **bloodbank** | `bloodbank/Dockerfile` | 33god-network + proxy | 8682 | redis, rabbitmq |
| **bloodbank-ws-relay** | `bloodbank/websocket-relay/Dockerfile` | 33god-network + proxy | 8683 | — |
| **candystore** | `services/candystore/Dockerfile` | 33god-network | 8684 | bloodbank |
| **postgres-notify-bridge** | `services/postgres-notify-bridge/Dockerfile` | 33god-network | — | bloodbank |
| **holocene** | `holocene/Dockerfile` | 33god-network + proxy | 11819 | bloodbank, candystore |
| **infra-dispatcher** | `bloodbank/Dockerfile` | host | — | — |
| **task-triage-dispatcher** | `bloodbank/Dockerfile` | host | — | — |
| **hookd-bridge** | `bloodbank/Dockerfile` | host | 18790 | — |
| **command-adapter** | `bloodbank/Dockerfile` | host | — | — |
| **heartbeat-router** | `bloodbank/Dockerfile` | host | — | — |
| **context-monitor** | `bloodbank/Dockerfile` | host | — | — |
