# Heartbeat Consumer Template

Per-agent heartbeat consumer for the 33GOD Bloodbank ecosystem. Built on FastStream + RabbitMQ.

## Overview

Each agent in the 33GOD ecosystem runs a heartbeat consumer that:

- Listens on queue `agent.{name}.inbox`
- Binds to routing keys: `agent.{name}.#` AND `system.heartbeat.#`
- On receiving `system.heartbeat.tick`, checks local `heartbeat.json` for overdue checks
- Executes the most overdue check and updates `lastRun` timestamp
- Zero-cost no-op when nothing is due

## Quick Start

### 1. Install

```bash
cd ~/code/33GOD/heartbeat-consumer
pip install -e .
```

### 2. Create heartbeat.json

```bash
cp examples/cack.heartbeat.json ~/.openclaw/workspace/heartbeat.json
```

### 3. Run Consumer

```bash
export AGENT_NAME=cack
export HEARTBEAT_PATH=/home/delorenj/.openclaw/workspace/heartbeat.json
export RABBIT_URL="amqp://delorenj:delorenj@localhost:5673/"
heartbeat-consumer
```

## Architecture

```
system.heartbeat.tick (cron every minute)
    ↓
RabbitMQ bloodbank.events.v1 exchange
    ↓ routing_key=system.heartbeat.#
agent.{name}.inbox queue
    ↓
HeartbeatConsumer
    ├─ Reload heartbeat.json
    ├─ Calculate overdueRatio = (now - lastRun) / cadenceMs
    ├─ Find most overdue check (ratio > 1.0, priority sorted)
    ├─ Execute handler_{check.handler}(tick_payload, check_config)
    └─ Update lastRun and save config
```

## heartbeat.json Schema

```json
{
  "$schema": "heartbeat.v1",
  "agent": "cack",
  "checks": {
    "sub_health": {
      "cadenceMs": 900000,
      "window": {"start": "00:00", "end": "23:59", "tz": "America/New_York"},
      "lastRun": 0,
      "priority": 1,
      "handler": "sub_health",
      "enabled": true
    },
    "quarterly_compaction": {
      "cadenceMs": 21600000,
      "triggerOnQuarters": ["Q1", "Q2", "Q3", "Q4"],
      "lastRun": 0,
      "priority": 2,
      "handler": "quarterly_compaction",
      "enabled": true
    }
  },
  "paused": {}
}
```

### Check Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cadenceMs` | integer | ✅ | Check interval in milliseconds |
| `handler` | string | ✅ | Handler function name to execute |
| `priority` | integer | | Tie-breaker when multiple checks overdue (lower = higher) |
| `enabled` | boolean | | Whether check is active |
| `window` | object | | Optional time window restriction |
| `window.start` | string | | HH:MM start time |
| `window.end` | string | | HH:MM end time |
| `window.tz` | string | | Timezone for window evaluation |
| `triggerOnQuarters` | string[] | | Only trigger on specific quarters (Q1-Q4) |
| `meta` | object | | Custom metadata for handler use |

## Handler Plugin Interface

Handlers are async functions that execute when a check triggers.

### Built-in Handlers

| Handler | Description |
|---------|-------------|
| `sub_health` | Emits agent status event with sub-agent health to Bloodbank |
| `quarterly_compaction` | Placeholder for memory compaction (implement per-agent) |
| `default` | No-op fallback |

### Custom Handlers

```python
from heartbeat_consumer import register_handler, CheckConfig

@register_handler("my_custom_check")
async def handle_my_custom_check(tick_payload: dict, check_config: CheckConfig) -> dict:
    """
    Execute custom check logic.
    
    Args:
        tick_payload: Contains agent, check_name, timestamp, envelope
        check_config: The check configuration from heartbeat.json
    
    Returns:
        dict with at least {"status": "success"|"failed"|"skipped", ...}
    """
    agent = tick_payload["agent"]
    
    # Your logic here
    result = await do_something()
    
    return {
        "status": "success",
        "details": result,
    }
```

Register handlers **before** starting the consumer:

```python
from heartbeat_consumer import HeartbeatConsumer

# Import module to trigger @register_handler decorators
import my_custom_handlers

consumer = HeartbeatConsumer(...)
consumer.run_sync()
```

## Integration in Agent Workspace

### systemd Service

Create `/etc/systemd/system/cack-heartbeat.service`:

```ini
[Unit]
Description=Cack Heartbeat Consumer
After=network.target rabbitmq.service

[Service]
Type=simple
User=delorenj
Environment="AGENT_NAME=cack"
Environment="HEARTBEAT_PATH=/home/delorenj/.openclaw/workspace/heartbeat.json"
Environment="RABBIT_URL=amqp://delorenj:delorenj@localhost:5673/"
Environment="EXCHANGE_NAME=bloodbank.events.v1"
Environment="LOG_LEVEL=INFO"
WorkingDirectory=/home/delorenj/.openclaw/workspace
ExecStart=/home/delorenj/.local/bin/heartbeat-consumer
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable --now cack-heartbeat
```

### Docker Compose

```yaml
services:
  cack-heartbeat:
    build: ./heartbeat-consumer
    environment:
      - AGENT_NAME=cack
      - HEARTBEAT_PATH=/config/heartbeat.json
      - RABBIT_URL=amqp://delorenj:delorenj@rabbitmq:5672/
    volumes:
      - ./workspace/heartbeat.json:/config/heartbeat.json:ro
    restart: unless-stopped
```

### Programmatic Usage

```python
from heartbeat_consumer import HeartbeatConsumer, register_handler, CheckConfig

@register_handler("ping")
async def handle_ping(tick_payload: dict, check_config: CheckConfig) -> dict:
    return {"status": "success", "message": "pong"}

consumer = HeartbeatConsumer(
    agent_name="my_agent",
    heartbeat_path="/path/to/heartbeat.json",
    rabbit_url="amqp://delorenj:delorenj@localhost:5673/",
    exchange_name="bloodbank.events.v1",
)

consumer.run_sync()  # Blocks until interrupted
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_NAME` | (required) | Agent name (matches queue routing) |
| `HEARTBEAT_PATH` | (required) | Path to heartbeat.json |
| `RABBIT_URL` | `amqp://delorenj:delorenj@localhost:5673/` | RabbitMQ connection URL |
| `EXCHANGE_NAME` | `bloodbank.events.v1` | Bloodbank exchange name |
| `LOG_LEVEL` | `INFO` | Python logging level |

## Testing

### Manual Heartbeat Trigger

```bash
python - <<'PY'
import asyncio
import aio_pika
import orjson
from datetime import datetime, timezone
from uuid import uuid4

async def main():
    conn = await aio_pika.connect_robust("amqp://delorenj:delorenj@localhost:5673/")
    ch = await conn.channel()
    ex = await ch.declare_exchange("bloodbank.events.v1", aio_pika.ExchangeType.TOPIC, durable=True)

    body = orjson.dumps({
        "event_id": str(uuid4()),
        "event_type": "system.heartbeat.tick",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "source": {"host": "local", "type": "manual", "app": "test"},
        "payload": {"tick_id": str(uuid4())[:8]},
    })

    await ex.publish(aio_pika.Message(body=body), routing_key="system.heartbeat.tick")
    await conn.close()
    print("Heartbeat tick sent")

asyncio.run(main())
PY
```

### Check Queue Bindings

```bash
# List queues
rabbitmqadmin -u delorenj -p delorenj -P 15673 list queues

# Check queue bindings
rabbitmqadmin -u delorenj -p delorenj -P 15673 list bindings
```

## File Structure

```
heartbeat-consumer/
├── heartbeat_consumer/       # Main package
│   ├── __init__.py
│   ├── consumer.py           # FastStream consumer implementation
│   ├── config.py             # HeartbeatConfig dataclass
│   ├── handlers.py           # Built-in handlers + plugin interface
│   └── runner.py             # CLI entry point
├── schemas/
│   └── heartbeat.v1.json     # JSON Schema for validation
├── examples/
│   └── cack.heartbeat.json   # Example configuration
├── pyproject.toml
└── README.md
```

## Troubleshooting

### Consumer not receiving heartbeats

1. Check RabbitMQ connection: `curl http://localhost:15673/api/overview -u delorenj:delorenj`
2. Verify queue exists: `rabbitmqadmin list queues name messages`
3. Check bindings: `rabbitmqadmin list bindings source destination routing_key`

### Handler not found

Ensure handler is registered before consumer starts:

```python
# Good: import registers the handler
from my_handlers import custom_handler

consumer = HeartbeatConsumer(...)
```

### Check not triggering

1. Verify `enabled: true` in heartbeat.json
2. Check `window` restrictions (timezones!)
3. Ensure `cadenceMs` and `lastRun` values are correct
4. Check logs for overdue ratio calculations

## References

- **Bloodbank**: `~/code/33GOD/bloodbank/GOD.md`
- **FastStream**: https://faststream.airt.ai/latest/
- **RabbitMQ**: https://www.rabbitmq.com/tutorials/amqp-concepts.html
