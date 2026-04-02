# C4 Container Diagram - Node-RED Flow Orchestrator

Shows the deployable units that make up the Node-RED Flow Orchestrator and how they interact with external systems.

```mermaid
C4Container
  title Container Diagram - Node-RED Flow Orchestrator

  Person(user, "Jarad", "Drops media into inbox")

  System_Boundary(orchestrator, "Node-RED Flow Orchestrator") {
    Container(nodeRed, "Node-RED Runtime", "Node.js, PM2", "Visual flow engine running at ~/.node-red, managed by PM2")
    Container(flows, "Flow Definitions", "JSON", "Versioned flow configs deployed from flows/*.json")
    Container(holyfieldsNodes, "holyfields-in / holyfields-out", "Node-RED Contrib", "Custom palette nodes for Bloodbank pub/sub with schema validation")
    Container(splitSilence, "split-silence", "Node-RED Contrib", "Custom node: silence detection and audio chunking via ffmpeg")
    Container(bloodbankSub, "bloodbank_subscribe.py", "Python, aio-pika", "Long-running RabbitMQ consumer emitting JSON lines to exec nodes")
    Container(minioPresign, "minio_presign.py", "Python, boto3", "Upload file to MinIO and return presigned URL")
    Container(extractAudio, "extract_audio.py", "Python, ffmpeg", "Extract audio from video files or pass through audio unchanged")
    Container(miseTasks, "mise tasks", "TOML", "Deployment tooling: deploy-flows, install-custom-nodes, setup-scripts")
  }

  System_Ext(filesystem, "Filesystem Watch", "~/audio/inbox directory")
  System_Ext(fireflies, "Fireflies.ai", "Transcription API")
  SystemDb(minio, "MinIO", "S3-compatible storage at s3.delo.sh")
  SystemQueue(bloodbank, "Bloodbank", "RabbitMQ topic exchange")
  System(holyfields, "Holyfields Schemas", "JSON Schema registry")

  Rel(user, filesystem, "Drops media files")
  Rel(nodeRed, filesystem, "Watches for new files", "fs.watch")
  Rel(nodeRed, extractAudio, "Calls for video-to-audio conversion", "child_process exec")
  Rel(nodeRed, splitSilence, "Splits long recordings by silence", "Node-RED wire")
  Rel(nodeRed, minioPresign, "Uploads and presigns media", "child_process exec")
  Rel(nodeRed, bloodbankSub, "Receives events as JSON lines", "child_process exec (long-running)")
  Rel(minioPresign, minio, "Uploads files, generates URLs", "S3 API")
  Rel(nodeRed, fireflies, "Submits audio URL for transcription", "REST API")
  Rel(fireflies, nodeRed, "Delivers transcript webhook", "HTTP POST /webhooks/fireflies")
  Rel(holyfieldsNodes, bloodbank, "Publishes validated event envelopes", "HTTP POST to Bloodbank /events/custom")
  Rel(holyfieldsNodes, bloodbank, "Subscribes to routing key patterns", "AMQP direct via amqplib")
  Rel(holyfieldsNodes, holyfields, "Loads schema catalog for validation", "Filesystem read")
  Rel(flows, nodeRed, "Deployed via mise run deploy-flows")
  Rel(miseTasks, nodeRed, "Deploys flows, restarts PM2")
```

## Container Inventory

| Container | Technology | Runtime | Purpose |
|-----------|-----------|---------|---------|
| Node-RED Runtime | Node.js | PM2 at `~/.node-red` | Visual flow execution engine |
| Flow Definitions | JSON | `flows/*.json` | Versioned source-of-truth for flow configs |
| holyfields-in/out | Node-RED Contrib (JS) | Loaded into Node-RED | Bloodbank pub/sub with Holyfields schema validation |
| split-silence | Node-RED Contrib (JS) | Loaded into Node-RED | Silence detection + audio chunking (ffmpeg) |
| bloodbank_subscribe.py | Python + aio-pika | exec node (long-running) | RabbitMQ consumer bridge for Node-RED |
| minio_presign.py | Python + boto3 | exec node | S3 upload + presigned URL generation |
| extract_audio.py | Python + ffmpeg | exec node | Video-to-audio extraction |
| mise tasks | TOML + shell scripts | CLI | Deployment and management tooling |

## Deployment Notes

- Node-RED runtime lives at `~/.node-red`, managed by PM2
- Flow source-of-truth is `flows/*.json` in this repo, deployed via `mise run deploy-flows`
- Custom nodes are installed via `mise run install-custom-nodes` (npm link into `~/.node-red`)
- Python scripts run in a venv at `scripts/.venv` (managed by `mise run setup-scripts`)
- Two long-running subscriber processes are started via `start-subscribers.sh`
