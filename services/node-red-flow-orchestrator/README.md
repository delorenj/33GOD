# Node-RED Flow Orchestrator

Decoupled flow management for the 33GOD Node-RED instance. This service owns the flow definitions, helper scripts, and deployment tooling. Node-RED itself runs as a PM2-managed service at `~/.node-red`.

## Architecture

```
~/.node-red/                    # Node-RED runtime (PM2-managed)
├── ecosystem.config.js         # PM2 config
├── settings.js                 # Node-RED settings
├── flows.json                  # Active flows (deployed from this service)
└── logs/                       # PM2 logs

~/code/33GOD/services/node-red-flow-orchestrator/   # This service
├── flows/                      # Flow definitions (source of truth)
│   └── *.json
├── scripts/                    # Helper scripts called by flows
│   ├── bloodbank_subscribe.py  # RabbitMQ consumer for Node-RED exec nodes
│   └── minio_presign.py        # MinIO upload + presign helper
├── mise.toml                   # Deployment tasks
└── README.md
```

## Flow Management

Flows are authored and versioned in `flows/`. Deploy to the Node-RED runtime using:

```bash
mise run deploy-flows
```

This copies flow definitions to `~/.node-red/` and restarts Node-RED via PM2.

## Helper Scripts

Node-RED flows use `exec` nodes to call Python scripts for:

- **bloodbank_subscribe.py**: Long-running RabbitMQ consumer that emits JSON lines
- **minio_presign.py**: Upload files to MinIO and return presigned URLs

Scripts require a Python venv with `aio-pika` and `boto3`:

```bash
cd scripts && uv venv && uv pip install aio-pika boto3
```

## Events Produced

| Event | Description |
|-------|-------------|
| `fireflies.transcript.upload` | Media file uploaded to MinIO, ready for Fireflies |
| `fireflies.transcript.ready` | Transcript received from Fireflies webhook |

## PM2 Commands

```bash
# Start Node-RED
pm2 start ~/.node-red/ecosystem.config.js

# View logs
pm2 logs node-red

# Restart after flow changes
pm2 restart node-red

# Set up boot persistence
pm2 save && pm2 startup
```
