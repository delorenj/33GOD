# C4 System Context - Node-RED Flow Orchestrator

The Node-RED Flow Orchestrator is the multi-protocol integration layer of the 33GOD ecosystem. It bridges filesystem events, external APIs, and Bloodbank (RabbitMQ) into unified event-driven workflows.

```mermaid
C4Context
  title System Context - Node-RED Flow Orchestrator

  Person(jarad, "Jarad DeLorenzo", "Drops media files into watch directory, manages flows")

  System(nodeRedOrch, "Node-RED Flow Orchestrator", "Multi-protocol workflow orchestration: file watching, media processing, API bridging, and Bloodbank event publishing")

  System(bloodbank, "Bloodbank", "RabbitMQ event backbone - topic exchange bloodbank.events.v1")
  System(holyfields, "Holyfields", "Event schema registry - JSON Schema definitions for all 33GOD events")

  System_Ext(fireflies, "Fireflies.ai", "Meeting transcription SaaS - receives audio, returns transcripts via webhook")
  System_Ext(minio, "MinIO", "S3-compatible object storage at s3.delo.sh - staging bucket for media files")

  System(transcriptProcessor, "Fireflies Transcript Processor", "Domain service: processes transcripts, saves to DeLoDocs, publishes artifact events")

  Rel(jarad, nodeRedOrch, "Drops media files into ~/audio/inbox")
  Rel(nodeRedOrch, minio, "Uploads media files, gets presigned URLs", "S3 API / boto3")
  Rel(nodeRedOrch, fireflies, "Submits audio for transcription", "REST API")
  Rel(fireflies, nodeRedOrch, "Delivers transcript via webhook", "HTTP POST")
  Rel(nodeRedOrch, bloodbank, "Publishes and consumes events", "AMQP 0-9-1")
  Rel(nodeRedOrch, holyfields, "Reads schemas for validation and envelope generation", "Filesystem")
  Rel(bloodbank, transcriptProcessor, "Routes fireflies.transcript.ready", "AMQP")
```

## Key Relationships

| From | To | Protocol | Purpose |
|------|----|----------|---------|
| User | Node-RED | Filesystem | Drop media into watch directory |
| Node-RED | MinIO | S3 API | Upload media, generate presigned URLs |
| Node-RED | Fireflies | REST | Submit audio URL for transcription |
| Fireflies | Node-RED | HTTP webhook | Deliver completed transcript |
| Node-RED | Bloodbank | AMQP | Publish `fireflies.transcript.upload`, `fireflies.transcript.ready` |
| Node-RED | Holyfields | Filesystem | Load schemas for validation and form generation |
| Bloodbank | Downstream | AMQP | Route events to domain-specific consumers |

## Architectural Role

Node-RED acts as the **integration glue** between external systems and the 33GOD event backbone. It owns the multi-protocol orchestration (filesystem, ffmpeg, S3, HTTP, AMQP) while domain-specific processing lives in dedicated services downstream of Bloodbank.
