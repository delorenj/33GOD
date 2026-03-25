# C4 Level 4: Deployment Diagram - 33GOD Stack

> How services map to Docker networks and host networking.

```mermaid
C4Deployment
  title Deployment Diagram - 33GOD Compose Stack

  Deployment_Node(host, "delo-workstation", "Ubuntu Linux") {

    Deployment_Node(traefik_proxy, "Traefik Proxy Network", "external: proxy") {
      Deployment_Node(tls, "TLS Termination", "Let's Encrypt + Google OAuth") {
        Container(traefik, "Traefik", "Reverse Proxy", "*.delo.sh routing")
      }
    }

    Deployment_Node(docker_bridge, "33god-network", "Docker bridge network") {

      Deployment_Node(infra_tier, "Infrastructure Tier", "Stateful services") {
        ContainerQueue(rabbitmq, "RabbitMQ", "3.12 Management Alpine", "Port 5673→5672, 15673→15672")
        ContainerDb(redis, "Redis", "7 Alpine", "Port 6381→6379, AOF persistence")
      }

      Deployment_Node(api_tier, "API Tier", "Core event bus") {
        Container(bloodbank, "Bloodbank", "FastAPI", "Port 8682")
        Container(wsrelay, "WS Relay", "Python", "Port 8683")
      }

      Deployment_Node(persistence_tier, "Persistence Tier", "Event storage") {
        Container(candystore, "Candystore", "FastAPI", "Port 8684")
        Container(pgbridge, "PG Notify Bridge", "Python", "No exposed port")
      }

      Deployment_Node(ui_tier, "UI Tier", "Frontend") {
        Container(holocene, "Holocene", "nginx + Vite React", "Port 11819")
      }
    }

    Deployment_Node(host_net, "Host Network", "network_mode: host — reaches loopback services") {

      Deployment_Node(dispatch_group, "Dispatch Services", "Route events to OpenClaw") {
        Container(infra_disp, "Infra Dispatcher", "Python", "Consumes plane events")
        Container(task_triage, "Task Triage Dispatcher", "Python", "Consumes inbox events")
        Container(hookd, "hookd Bridge", "Python", "Listens :18790")
        Container(cmd_adapter, "Command Adapter", "Python", "FSM guard + dispatch")
      }

      Deployment_Node(agent_group, "Agent Support", "Maintain agent health") {
        Container(heartbeat, "Heartbeat Router", "Python", "60s tick scheduler")
        Container(ctx_mon, "Context Monitor", "Python", "Compaction enforcement")
      }
    }

    Deployment_Node(external_host, "Host Services (non-Docker)", "Running on bare metal") {
      Container(openclaw, "OpenClaw", "Agent Runtime", "Hooks at :18789, hookd-bridge at :18790")
    }
  }

  Deployment_Node(db_server, "Database Server", "192.168.1.12") {
    ContainerDb(postgres, "PostgreSQL 16", "PostgreSQL", "Port 5432, DB: 33god")
  }

  %% Bridge network connections
  Rel(bloodbank, rabbitmq, "AMQP", "rabbitmq:5672")
  Rel(bloodbank, redis, "Redis", "33god-redis:6379")
  Rel(wsrelay, rabbitmq, "AMQP", "rabbitmq:5672")
  Rel(candystore, rabbitmq, "AMQP", "rabbitmq:5672")
  Rel(candystore, postgres, "SQL", "192.168.1.12:5432")
  Rel(pgbridge, postgres, "LISTEN", "192.168.1.12:5432")
  Rel(pgbridge, bloodbank, "HTTP", "bloodbank:8682")
  Rel(holocene, bloodbank, "HTTP", "bloodbank:8682")
  Rel(holocene, candystore, "HTTP", "candystore:8080")

  %% Host network connections (reach RabbitMQ via mapped port)
  Rel(infra_disp, rabbitmq, "AMQP", "127.0.0.1:5673")
  Rel(task_triage, rabbitmq, "AMQP", "127.0.0.1:5673")
  Rel(hookd, rabbitmq, "AMQP", "127.0.0.1:5673")
  Rel(cmd_adapter, rabbitmq, "AMQP", "127.0.0.1:5673")
  Rel(cmd_adapter, redis, "Redis", "127.0.0.1:6381")
  Rel(heartbeat, rabbitmq, "AMQP", "127.0.0.1:5673")
  Rel(ctx_mon, rabbitmq, "AMQP", "127.0.0.1:5673")

  %% Dispatch to OpenClaw
  Rel(infra_disp, openclaw, "HTTP hook", "127.0.0.1:18789")
  Rel(task_triage, openclaw, "HTTP hook", "127.0.0.1:18789")
  Rel(cmd_adapter, openclaw, "HTTP hook", "127.0.0.1:18789")
  Rel(heartbeat, openclaw, "HTTP hook", "127.0.0.1:18789")

  %% Traefik routing
  Rel(traefik, bloodbank, "bloodbank.delo.sh")
  Rel(traefik, holocene, "holocene.delo.sh")
  Rel(traefik, rabbitmq, "rabbit.delo.sh")
  Rel(traefik, wsrelay, "bloodbank-ws.delo.sh")
```

## Network Topology

| Network | Type | Services | Why |
|---------|------|----------|-----|
| **33god-network** | Docker bridge | redis, rabbitmq, bloodbank, ws-relay, candystore, pg-notify-bridge, holocene | Internal service mesh with DNS resolution |
| **proxy** | External (Traefik) | rabbitmq, bloodbank, ws-relay, holocene | TLS-terminated public routing at *.delo.sh |
| **host** | network_mode: host | heartbeat-router, context-monitor, infra-dispatcher, task-triage-dispatcher, hookd-bridge, command-adapter | Must reach OpenClaw on 127.0.0.1:18789 (loopback-bound) |

## Port Map

| Host Port | Container Port | Service | Protocol |
|-----------|---------------|---------|----------|
| 5673 | 5672 | RabbitMQ | AMQP |
| 15673 | 15672 | RabbitMQ | HTTP (Management UI) |
| 6381 | 6379 | Redis | Redis |
| 8682 | 8682 | Bloodbank | HTTP |
| 8683 | 8683 | WS Relay | WebSocket |
| 8684 | 8080 | Candystore | HTTP |
| 11819 | 80 | Holocene | HTTP (nginx) |
| 18790 | — (host) | hookd Bridge | HTTP |
