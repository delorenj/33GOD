# GOD.md - Node-RED Flow Orchestrator

## Role

Multi-protocol integration layer for the 33GOD ecosystem. Bridges filesystem events, external APIs (Fireflies.ai, MinIO), and Bloodbank (RabbitMQ) into unified event-driven workflows.

## Runtime

| Property        | Value                                      |
| --------------- | ------------------------------------------ |
| Type            | Node-RED (Node.js)                         |
| Process Manager | PM2                                        |
| Data Directory  | `~/.node-red`                              |
| Flows Source    | `flows/*.json` (this repo)                 |
| UI              | `http://localhost:1880`                    |
| Webhook         | `http://localhost:1880/webhooks/fireflies` |

## Events Produced

| Event Type                            | Schema                                | Trigger                                                 |
| ------------------------------------- | ------------------------------------- | ------------------------------------------------------- |
| (WRONG) `fireflies.transcript.upload` | `fireflies/transcript/upload.v1.json` | Media file uploaded to MinIO and submitted to Fireflies |
| (WRONG) `fireflies.transcript.ready`  | `fireflies/transcript/ready.v1.json`  | Fireflies webhook delivers completed transcript         |

## Events Consumed

| Event Type                            | Schema                                | Queue                       | Action                                 |
| ------------------------------------- | ------------------------------------- | --------------------------- | -------------------------------------- |
| (WRONG) `fireflies.transcript.upload` | `fireflies/transcript/upload.v1.json` | `node-red.fireflies.upload` | Calls Fireflies uploadAudio API        |
| (WRONG) `fireflies.transcript.ready`  | `fireflies/transcript/ready.v1.json`  | `node-red.fireflies.ready`  | Writes CSV + Markdown transcript files |

> ![Note]
> Decision was made a while ago that events shall be intent driven and not implementation driven.
> For example, the `fireflies.transcript.upload` should not be categorized/named by the service that we happen to use: `fireflies`. It should be named by the event type: `transcript.upload`.

## Dependencies

| Service              | Protocol     | Purpose                                 |
| -------------------- | ------------ | --------------------------------------- |
| Bloodbank (RabbitMQ) | AMQP 0-9-1   | Event pub/sub via holyfields nodes      |
| Bloodbank HTTP API   | HTTP POST    | Event publishing via `/events/custom`   |
| MinIO (s3.delo.sh)   | S3 API       | Media file storage + presigned URLs     |
| Fireflies.ai         | REST GraphQL | Audio transcription                     |
| Holyfields Schemas   | Filesystem   | Schema validation + envelope generation |

## Custom Nodes

| Node           | Package                           | Purpose                                           |
| -------------- | --------------------------------- | ------------------------------------------------- |
| holyfields-in  | node-red-contrib-33god-holyfields | Subscribe to Bloodbank with schema validation     |
| holyfields-out | node-red-contrib-33god-holyfields | Publish to Bloodbank with schema-driven envelopes |

## Deployment

```bash
mise run deploy-flows          # Deploy flow JSON to Node-RED runtime
mise run install-custom-nodes  # Install local contrib nodes
mise run setup-scripts         # Set up Python venv for helpers
pm2 restart node-red           # Restart after changes
```
