# C4 Dynamic: Event Flow Through 33GOD

> Numbered request flows showing how events move through the system.

## Flow 1: Agent Hook Call → Command Execution

An AI agent makes a legacy hook call that gets translated, validated, and dispatched.

```mermaid
C4Dynamic
  title Agent Hook → Command Execution Flow

  Person(agent, "AI Agent", "Running in OpenClaw workspace")
  Container(hookd, "hookd Bridge", "Python", "Legacy → command envelope")
  ContainerQueue(rabbitmq, "RabbitMQ", "AMQP", "bloodbank.events.v1")
  Container(cmd_adapter, "Command Adapter", "Python", "FSM guard + dispatch")
  ContainerDb(redis, "Redis", "7 Alpine", "FSM state")
  System_Ext(openclaw, "OpenClaw", "Agent runtime")
  Container(candystore, "Candystore", "Python", "Event persistence")
  ContainerDb(postgres, "PostgreSQL", "16", "Event store")

  Rel(agent, hookd, "1. POST /hooks/agent", "HTTP")
  Rel(hookd, rabbitmq, "2. Publish command envelope", "AMQP")
  Rel(cmd_adapter, rabbitmq, "3. Consume command event", "AMQP")
  Rel(cmd_adapter, redis, "4. Check FSM guard state", "Redis")
  Rel(cmd_adapter, openclaw, "5. Dispatch validated command", "HTTP hook")
  Rel(candystore, rabbitmq, "6. Persist event to history", "AMQP")
  Rel(candystore, postgres, "7. INSERT event JSONB", "SQL")
```

## Flow 2: Plane Ticket → Agent Dispatch

A Plane webhook triggers infra-dispatcher to spin up an agent via OpenClaw.

```mermaid
C4Dynamic
  title Plane Ticket → Agent Dispatch Flow

  System_Ext(plane, "Plane", "Project board")
  Container(bloodbank, "Bloodbank", "FastAPI", "Event bus API")
  ContainerQueue(rabbitmq, "RabbitMQ", "AMQP", "bloodbank.events.v1")
  Container(infra_disp, "Infra Dispatcher", "Python", "Ready-gate dispatch")
  System_Ext(openclaw, "OpenClaw", "Agent runtime")
  Container(candystore, "Candystore", "Python", "Event persistence")

  Rel(plane, bloodbank, "1. POST webhook (ticket moved)", "HTTPS")
  Rel(bloodbank, rabbitmq, "2. Publish plane.webhook.* event", "AMQP")
  Rel(infra_disp, rabbitmq, "3. Consume plane event", "AMQP")
  Rel(infra_disp, openclaw, "4. Dispatch agent task (if ready-gate passes)", "HTTP hook")
  Rel(candystore, rabbitmq, "5. Persist event", "AMQP")
```

## Flow 3: Task Inbox Triage

A new task enters the inbox and gets triaged to the appropriate agent.

```mermaid
C4Dynamic
  title Task Inbox Triage Flow

  Container(bloodbank, "Bloodbank", "FastAPI", "Event bus API")
  ContainerQueue(rabbitmq, "RabbitMQ", "AMQP", "bloodbank.events.v1")
  Container(task_triage, "Task Triage Dispatcher", "Python", "Inbox → triage")
  System_Ext(openclaw, "OpenClaw", "Agent runtime")

  Rel(bloodbank, rabbitmq, "1. task.inbox.issue.created published", "AMQP")
  Rel(task_triage, rabbitmq, "2. Consume inbox event", "AMQP")
  Rel(task_triage, openclaw, "3. Dispatch to triage agent", "HTTP hook")
```

## Flow 4: Real-Time Dashboard

Developer views live events flowing through the system.

```mermaid
C4Dynamic
  title Real-Time Dashboard Flow

  Person(dev, "Developer", "Monitoring the platform")
  Container(holocene, "Holocene", "React / nginx", "Mission Control dashboard")
  Container(candystore, "Candystore", "Python", "Event history API")
  ContainerDb(postgres, "PostgreSQL", "16", "Event store")
  Container(wsrelay, "WS Relay", "Python", "WebSocket fan-out")
  ContainerQueue(rabbitmq, "RabbitMQ", "AMQP", "bloodbank.events.v1")

  Rel(dev, holocene, "1. Open holocene.delo.sh", "HTTPS")
  Rel(holocene, candystore, "2. GET /api/v1/events (history)", "HTTP")
  Rel(candystore, postgres, "3. SELECT events", "SQL")
  Rel(holocene, wsrelay, "4. Connect WebSocket (live)", "WSS")
  Rel(wsrelay, rabbitmq, "5. Subscribe routing_key=#", "AMQP")
```

## Flow 5: Heartbeat Check Dispatch

The heartbeat router scans agent workspaces and dispatches overdue checks.

```mermaid
C4Dynamic
  title Heartbeat Dispatch Flow

  Container(heartbeat, "Heartbeat Router", "Python", "Self-ticking scheduler")
  ContainerQueue(rabbitmq, "RabbitMQ", "AMQP", "bloodbank.events.v1")
  System_Ext(openclaw, "OpenClaw", "Agent runtime")

  Rel(heartbeat, heartbeat, "1. asyncio timer fires (60s)")
  Rel(heartbeat, heartbeat, "2. Scan ~/.openclaw/*/heartbeat.json")
  Rel(heartbeat, openclaw, "3. POST hook for overdue agents", "HTTP")
  Rel(heartbeat, rabbitmq, "4. Publish dispatch event (best-effort)", "AMQP")
```

## Flow 6: Database Change → Event Pipeline

A Postgres NOTIFY triggers an event through the pipeline.

```mermaid
C4Dynamic
  title Postgres NOTIFY → Bloodbank Flow

  ContainerDb(postgres, "PostgreSQL", "16", "Platform DB")
  Container(pgbridge, "PG Notify Bridge", "Python", "LISTEN/NOTIFY relay")
  Container(bloodbank, "Bloodbank", "FastAPI", "Event bus API")
  ContainerQueue(rabbitmq, "RabbitMQ", "AMQP", "bloodbank.events.v1")

  Rel(postgres, pgbridge, "1. NOTIFY bloodbank_events payload", "libpq")
  Rel(pgbridge, bloodbank, "2. POST /publish event", "HTTP")
  Rel(bloodbank, rabbitmq, "3. Validate + publish to exchange", "AMQP")
```
