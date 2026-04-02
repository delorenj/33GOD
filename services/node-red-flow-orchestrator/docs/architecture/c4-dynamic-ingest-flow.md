# C4 Dynamic Diagram - Media Ingest to Transcription Flow

The primary workflow: a media file dropped into the inbox is processed through audio extraction, uploaded to MinIO, submitted to Fireflies for transcription, and the resulting transcript is published to Bloodbank.

```mermaid
C4Dynamic
  title Dynamic Diagram - Ingest to Bloodbank Pipeline

  Person(user, "Jarad", "Drops media file")
  Container(inbox, "Watch Directory", "~/audio/inbox")
  Container(nodeRed, "Node-RED Runtime", "Node.js/PM2", "Flow engine")
  Container(extractAudio, "extract_audio.py", "Python/ffmpeg", "Audio extraction")
  Container(splitSilence, "split-silence", "Node-RED node", "Silence detection")
  Container(minioPresign, "minio_presign.py", "Python/boto3", "S3 upload")
  SystemDb(minio, "MinIO", "s3.delo.sh")
  System_Ext(fireflies, "Fireflies.ai", "Transcription API")
  Container(holyfieldsOut, "holyfields-out", "Node-RED node", "Event publisher")
  SystemQueue(bloodbank, "Bloodbank", "RabbitMQ")

  Rel(user, inbox, "1. Drop media file (mp4/mp3/wav)")
  Rel(nodeRed, inbox, "2. Detect new file via fs.watch")
  Rel(nodeRed, extractAudio, "3. Extract audio (if video)", "exec node")
  Rel(nodeRed, splitSilence, "4. Split by silence regions", "Node-RED wire")
  Rel(nodeRed, minioPresign, "5. Upload chunk + get presigned URL", "exec node")
  Rel(minioPresign, minio, "6. PUT object to transcription-staging bucket", "S3 API")
  Rel(nodeRed, fireflies, "7. Submit presigned URL for transcription", "REST API")
  Rel(nodeRed, holyfieldsOut, "8. Publish fireflies.transcript.upload", "Node-RED wire")
  Rel(holyfieldsOut, bloodbank, "9. POST envelope to Bloodbank", "HTTP")

  UpdateRelStyle(user, inbox, $textColor="blue", $offsetY="-10")
  UpdateRelStyle(nodeRed, extractAudio, $textColor="blue", $offsetY="-10")
  UpdateRelStyle(minioPresign, minio, $textColor="green", $offsetY="-10")
  UpdateRelStyle(holyfieldsOut, bloodbank, $textColor="red", $offsetY="-10")
```

## Webhook Return Path

```mermaid
C4Dynamic
  title Dynamic Diagram - Fireflies Webhook to Bloodbank

  System_Ext(fireflies, "Fireflies.ai", "Transcription complete")
  Container(nodeRed, "Node-RED Runtime", "Node.js/PM2", "Webhook receiver")
  Container(holyfieldsOut, "holyfields-out", "Node-RED node", "Event publisher")
  SystemQueue(bloodbank, "Bloodbank", "RabbitMQ")
  Container(transcriptProc, "Transcript Processor", "Python/FastStream", "Domain service")

  Rel(fireflies, nodeRed, "1. POST transcript to /webhooks/fireflies", "HTTP webhook")
  Rel(nodeRed, holyfieldsOut, "2. Build fireflies.transcript.ready envelope", "Node-RED wire")
  Rel(holyfieldsOut, bloodbank, "3. POST envelope to Bloodbank", "HTTP")
  Rel(bloodbank, transcriptProc, "4. Route to transcript processor queue", "AMQP")

  UpdateRelStyle(fireflies, nodeRed, $textColor="green", $offsetY="-10")
  UpdateRelStyle(holyfieldsOut, bloodbank, $textColor="red", $offsetY="-10")
```

## Flow Steps Detail

### Ingest Pipeline (Tab 1: "Ingest -> Bloodbank")

| Step | Node Type | Action | Failure Mode |
|------|-----------|--------|-------------|
| 1 | watch | Detect new file in `~/audio/inbox` | Inotify limit; restart Node-RED |
| 2 | switch | Filter: only media extensions (mp3/wav/m4a/mp4/mov/mkv) | Non-media silently dropped |
| 3 | switch | Filter: only `rename` events (debounce) | Duplicate events filtered |
| 4 | delay | 2s settle time for large file writes | N/A |
| 5 | exec | `extract_audio.py` - extract audio if video | ffmpeg not installed; timeout 60s |
| 6 | split-silence | Detect silence gaps, split into activity chunks | ffprobe/ffmpeg failure |
| 7 | exec | `minio_presign.py` - upload chunk + presign | Missing creds; MinIO down |
| 8 | http request | POST to Fireflies upload API | API key invalid; rate limit |
| 9 | holyfields-out | Publish `fireflies.transcript.upload` to Bloodbank | Bloodbank HTTP API down |

### Webhook Return Path

| Step | Node Type | Action |
|------|-----------|--------|
| 1 | http in | Receive POST at `/webhooks/fireflies` |
| 2 | function | Extract transcript data, build payload |
| 3 | holyfields-out | Publish `fireflies.transcript.ready` to Bloodbank |

## Events Produced

| Event | Schema | Trigger |
|-------|--------|---------|
| `fireflies.transcript.upload` | `fireflies/transcript/upload.v1.json` | Media uploaded to MinIO, submitted to Fireflies |
| `fireflies.transcript.ready` | `fireflies/transcript/ready.v1.json` | Fireflies webhook delivers completed transcript |
