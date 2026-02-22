# 33GOD Master Heartbeat Tick Publisher

FastStream service that publishes `system.heartbeat.tick` events to Bloodbank every 60 seconds.

## Overview

This service maintains a master heartbeat for the 33GOD ecosystem, publishing tick events to RabbitMQ that can be consumed by various agents and services.

## Event Schema

```json
{
  "tick": 12345,
  "timestamp": "2026-02-22T21:37:00Z",
  "quarter": "Q4",
  "dayOfWeek": "sunday",
  "epochMs": 1771802220000
}
```

**Quarter Calculation** (America/New_York timezone):
- Q1: 00:00-06:00
- Q2: 06:00-12:00
- Q3: 12:00-18:00
- Q4: 18:00-00:00

## Quick Start

### 1. Install Dependencies

```bash
cd ~/code/33GOD/heartbeat-tick
uv pip install -e .
```

Or with pip:
```bash
pip install -e .
```

### 2. Configure Environment

Create `.env` file or export variables:

```bash
# Required: RabbitMQ connection
export RABBITMQ_URL="amqp://delorenj@localhost:5673/"
export RABBITMQ_PASS="your-password-here"

# Optional: defaults shown
export BLOODBANK_EXCHANGE="bloodbank.events.v1"
export TICK_INTERVAL_S="60"
export LOG_LEVEL="INFO"
```

### 3. Run

```bash
python publisher.py
```

Or as a module:
```bash
python -m publisher
```

## Systemd Service

### Install the service

```bash
sudo cp systemd/heartbeat-tick.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable heartbeat-tick
sudo systemctl start heartbeat-tick
```

### Check status

```bash
sudo systemctl status heartbeat-tick
sudo journalctl -u heartbeat-tick -f
```

### Environment file

Create `/etc/heartbeat-tick.env`:
```bash
RABBITMQ_URL=amqp://delorenj@localhost:5673/
RABBITMQ_PASS=your-password
BLOODBANK_EXCHANGE=bloodbank.events.v1
TICK_INTERVAL_S=60
LOG_LEVEL=INFO
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `RABBITMQ_URL` | `amqp://delorenj@localhost:5673/` | AMQP connection URL |
| `RABBITMQ_PASS` | - | Password (if not in URL) |
| `BLOODBANK_EXCHANGE` | `bloodbank.events.v1` | Exchange name |
| `TICK_INTERVAL_S` | `60` | Seconds between ticks |
| `LOG_LEVEL` | `INFO` | Logging level |

## Architecture

- Uses **FastStream** for robust RabbitMQ publishing
- Publishes to `bloodbank.events.v1` exchange (TOPIC type)
- Routing key: `system.heartbeat.tick`
- Graceful shutdown on SIGTERM/SIGINT
- Monotonic tick counter (resets on restart)

## Troubleshooting

**Connection refused:**
- Verify RabbitMQ is running: `docker ps | grep rabbitmq`
- Check port 5673 is accessible
- Verify credentials in `.env`

**Permission denied:**
- Ensure user has access to vhost `/`
- Check RabbitMQ user permissions: `rabbitmqctl list_users`

## License

Part of the 33GOD ecosystem.
