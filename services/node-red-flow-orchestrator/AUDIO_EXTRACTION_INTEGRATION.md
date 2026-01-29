# Audio Extraction Integration for Node-RED Flow

## Overview

This document describes how to add audio extraction from video files to the existing Fireflies-Bloodbank Node-RED flow.

## Architecture Decision

**Problem:** Fireflies API requires audio files, but users may upload video files to the inbox.

**Solution:** Add audio extraction step using ffmpeg before uploading to MinIO/Fireflies.

**Tool choice:** Python script (`scripts/extract_audio.py`) called via exec node
- Testable and maintainable
- Handles both video and audio files
- Returns JSON with extracted audio path

## Current Flow (Tab 1: "Ingest -> Bloodbank")

```
[Watch inbox] → [Filter media] → [Filter events] → [Delay settle] → [Prep MinIO] → [Upload + presign] → ...
```

## Updated Flow

```
[Watch inbox] → [Filter media] → [Filter events] → [Delay settle]
    → [Extract audio] → [Parse extraction result] → [Prep MinIO] → [Upload + presign] → ...
```

## Implementation Steps

### 1. The Python Script (Already Created)

Located at: `scripts/extract_audio.py`

**Features:**
- Detects media type (video/audio/other)
- Extracts audio from video using ffmpeg (MP3, quality 2)
- Passes through audio files unchanged
- Returns JSON: `{"success": true, "audio_file": "/path/to/audio.mp3", "extracted": true/false}`

### 2. Add Nodes in Node-RED UI

Open Node-RED UI at `http://localhost:1880` and modify the "Ingest -> Bloodbank" tab:

#### A. Add "Extract Audio" exec node

**Insert between:** `delay_settle` → `prep_minio`

**Configuration:**
- **Name:** Extract audio
- **Command:** `${SCRIPTS_DIR}/.venv/bin/python ${SCRIPTS_DIR}/extract_audio.py`
- **Append msg.:** `filename`
- **Timeout:** `60` seconds

**Node type:** `exec`

#### B. Add "Parse extraction result" json node

**Insert after:** Extract audio exec node
**Insert before:** prep_minio function node

**Configuration:**
- **Name:** Parse extraction result
- **Action:** Convert between JSON String & Object
- **Property:** `msg.payload`

**Node type:** `json`

#### C. Add "Update file path" function node

**Insert after:** Parse extraction result
**Insert before:** prep_minio

**Configuration:**
- **Name:** Update file path
- **Function code:**
```javascript
// Update filename to point to extracted/original audio file
const result = msg.payload;

if (!result.success) {
    node.error(`Audio extraction failed: ${result.error}`, msg);
    return null;
}

// Update msg.filename to use the audio file
msg.filename = result.audio_file;

// Store metadata
msg.meta = msg.meta || {};
msg.meta.original_file = result.original_file;
msg.meta.audio_file = result.audio_file;
msg.meta.media_type = result.media_type;
msg.meta.extracted = result.extracted;

return msg;
```

**Node type:** `function`

### 3. Update Wiring

1. **Disconnect:** `delay_settle` → `prep_minio`
2. **Connect:** `delay_settle` → `extract_audio` (exec node)
3. **Connect:** `extract_audio` → `parse_extraction_result` (json node)
4. **Connect:** `parse_extraction_result` → `update_file_path` (function node)
5. **Connect:** `update_file_path` → `prep_minio`

### 4. Error Handling

Add debug nodes to catch extraction failures:

**Add node:**
- **Name:** Audio extraction error
- **Node type:** `debug`
- **Connect from:** exec node output 2 (stderr)

### 5. Environment Variables

Ensure these are set in Node-RED settings or `.envrc`:

```bash
export SCRIPTS_DIR="/home/delorenj/code/33GOD/services/node-red-flow-orchestrator/scripts"
export WATCH_DIR="/home/delorenj/audio/inbox"
```

## Testing

### Test Case 1: Video file
```bash
cp test-video.mp4 /home/delorenj/audio/inbox/
# Expected: Audio extracted to .mp3, uploaded to Fireflies
```

### Test Case 2: Audio file
```bash
cp test-audio.mp3 /home/delorenj/audio/inbox/
# Expected: Original file used, uploaded to Fireflies
```

### Test Case 3: Non-media file
```bash
cp document.pdf /home/delorenj/audio/inbox/
# Expected: Flow exits quietly (filtered at "Only media files" node)
```

## Verification

After implementing:

1. Check Node-RED logs for successful extraction:
   ```
   Audio extraction: {"success": true, "audio_file": "...", "extracted": true}
   ```

2. Verify MinIO upload uses the audio file (not video):
   ```
   Uploaded object: recordings/2026-01-20-filename.mp3
   ```

3. Check Fireflies API call uses audio file URL

## Dependencies

### System

```bash
# Install ffmpeg
sudo apt install ffmpeg  # Ubuntu/Debian
brew install ffmpeg      # macOS
```

### Python

Already included in `scripts/.venv` (managed by mise):
- Standard library only (subprocess, pathlib, json)

## Rollback

If issues arise:

1. **Quick fix:** Reconnect `delay_settle` → `prep_minio` directly
2. **Disable extraction:** Set `filter_media` to only accept audio files:
   ```javascript
   // In filter_media switch node
   t: "regex", v: "\\.(mp3|wav|m4a|ogg)$"  // Remove video extensions
   ```

## Architecture Notes

This implementation follows the 33GOD service separation principles:

- **Node-RED:** Multi-protocol orchestration (filesystem → ffmpeg → MinIO → Fireflies API)
- **Python service:** Domain logic (transcript processing, Markdown formatting, artifact events)
- **Separation of concerns:** Media processing in Node-RED, transcript processing in Python service

The audio extraction step has >5 protocols (filesystem, exec, S3, HTTP, RabbitMQ) and conditional logic, justifying Node-RED orchestration over a Watchdog Python service.
