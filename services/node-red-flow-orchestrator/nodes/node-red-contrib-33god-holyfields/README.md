# node-red-contrib-33god-holyfields

Holyfields-aware Node-RED nodes for Bloodbank contract workflows.

## Nodes

### `holyfields out`

Schema-driven publisher:
- Select Holyfields contract from dropdown (vetted/all)
- Fill payload using generated generic form
- Publishes full envelope to Bloodbank (`/events/custom` by default)
- Auto-routes command envelope payloads to `command.{agent}.{action}`

### `holyfields in`

Schema-aware consumer:
- Subscribes to Bloodbank exchange/routing key via RabbitMQ
- Optional schema validation (`warn`, `strict`, `off`)
- Output envelope or payload mode

## Configuration assumptions

Defaults are tuned for current 33GOD runtime:
- Holyfields schemas: `$HOLYFIELDS_SCHEMAS_DIR` (required env var)
- Bloodbank publish API: `http://127.0.0.1:8682/events/custom`
- RabbitMQ: `amqp://127.0.0.1:5672/`
- Exchange: `bloodbank.events.v1`

Override schema root with env var:

```bash
export HOLYFIELDS_SCHEMAS_DIR=/custom/path/to/holyfields/schemas
```

## Install (local development)

From `~/.node-red`:

```bash
npm install --save file:../code/33GOD/services/node-red-flow-orchestrator/nodes/node-red-contrib-33god-holyfields
```

Restart Node-RED after install.
