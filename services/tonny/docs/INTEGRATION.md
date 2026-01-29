# Tonny Agent Integration Guide

## Overview

This guide covers integrating Tonny Agent into the 33GOD ecosystem for voice-to-AI-to-TTS workflows.

## Prerequisites

1. **RabbitMQ (Bloodbank)** running and accessible
2. **Letta server** (self-hosted or Letta Cloud)
3. **HolyFields schemas** for event validation
4. **API Keys:**
   - OpenAI or Anthropic (for LLM)
   - ElevenLabs (for TTS)

## Step 1: Install Letta Server (Self-Hosted)

For production, run your own Letta server:

```bash
# Install Letta
pip install letta

# Start Letta server
letta server

# Server runs on http://localhost:8283
```

For Letta Cloud, sign up at https://letta.com and get your API key.

## Step 2: Configure Tonny

```bash
cd ~/code/33GOD/services/tonny

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
nano .env
```

Update `.env`:

```bash
# Bloodbank (RabbitMQ)
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Letta (self-hosted)
LETTA_BASE_URL=http://localhost:8283

# OR Letta Cloud
# LETTA_BASE_URL=https://api.letta.com
# LETTA_API_KEY=your_cloud_key

# LLM Provider
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4.1

# ElevenLabs
ELEVENLABS_API_KEY=your_key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

## Step 3: Start Tonny Agent

```bash
# Development
uv run python -m src.main

# Production (with systemd)
sudo cp tonny.service /etc/systemd/system/
sudo systemctl enable tonny
sudo systemctl start tonny
```

## Step 4: Verify Integration

### Check Health

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "tonny-agent",
  "version": "0.1.0"
}
```

### Test Event Flow

1. **Publish test transcription event:**

```bash
# Using Bloodbank CLI (if available)
bb publish \
  --event-type transcription.voice.completed \
  --routing-key transcription.voice.completed \
  --payload '{
    "event_id": "test-123",
    "event_type": "transcription.voice.completed",
    "timestamp": "2026-01-27T10:00:00Z",
    "source": "whisperlivekit",
    "target": "tonny",
    "session_id": "session-456",
    "payload": {
      "text": "Hello Tonny, what time is it?",
      "confidence": 0.98,
      "language": "en"
    }
  }'
```

2. **Check Tonny logs:**

```bash
# Development
tail -f logs/tonny.log

# Systemd
journalctl -u tonny -f
```

Expected log output:

```json
{"event": "processing_transcription", "session_id": "session-456", "text_length": 29}
{"event": "llm_processing_completed", "session_id": "session-456", "latency_ms": 450}
{"event": "tts_generation_completed", "session_id": "session-456", "latency_ms": 380}
{"event": "processing_completed", "total_latency_ms": 1250, "latency_target_met": true}
```

3. **Verify TTS event published:**

Check Bloodbank for `tts.response.completed` event on topic `tts.response.completed`.

## Step 5: Monitor Performance

Access metrics endpoint:

```bash
curl http://localhost:8000/metrics
```

Example response:

```json
{
  "total_sessions": 42,
  "sessions": [
    {
      "session_id": "session-456",
      "total_latency_ms": 1250,
      "llm_latency_ms": 450,
      "tts_latency_ms": 380,
      "transcription_received_at": "2026-01-27T10:00:00Z",
      "event_published_at": "2026-01-27T10:00:01.250Z"
    }
  ]
}
```

## Event Schema Reference

### Consumed Event: `transcription.voice.completed`

Published by: WhisperLiveKit

```json
{
  "event_id": "uuid",
  "event_type": "transcription.voice.completed",
  "timestamp": "2026-01-27T10:00:00Z",
  "source": "whisperlivekit",
  "target": "tonny",
  "session_id": "uuid",
  "payload": {
    "text": "What's the weather today?",
    "confidence": 0.98,
    "language": "en",
    "audio_metadata": {
      "duration_ms": 1500,
      "sample_rate": 16000
    }
  }
}
```

### Published Event: `tts.response.completed`

Consumed by: Client applications, Candybar

```json
{
  "event_id": "uuid",
  "event_type": "tts.response.completed",
  "timestamp": "2026-01-27T10:00:02Z",
  "source": "tonny",
  "target": "whisperlivekit",
  "session_id": "uuid",
  "payload": {
    "response_text": "The weather today is sunny and 72 degrees.",
    "audio_base64": "base64_encoded_mp3...",
    "voice_id": "21m00Tcm4TlvDq8ikWAM",
    "model_id": "eleven_monolingual_v1",
    "character_count": 45,
    "original_transcription": "What's the weather today?"
  }
}
```

## Letta Agent Customization

### Modify Agent Persona

Edit `src/letta_agent.py`:

```python
agent_config = {
    "name": "tonny-voice-assistant",
    "persona": (
        "You are Tonny, a helpful assistant specialized in [YOUR DOMAIN]. "
        "You provide concise, actionable responses. "
        "Keep answers under 2 sentences when possible."
    ),
    "human": (
        "The user is speaking via voice. "
        "They prefer quick, conversational replies."
    ),
}
```

### Add Custom Memory Blocks

```python
# In agent_config
"memory_blocks": [
    {
        "name": "user_preferences",
        "label": "user_preferences",
        "description": "User's preferences and settings",
        "value": "",
    },
]
```

## Troubleshooting

### Issue: Events not being consumed

**Solution:**

1. Check RabbitMQ connection:
   ```bash
   rabbitmqctl list_queues
   ```

2. Verify queue exists:
   ```bash
   rabbitmqctl list_queues | grep tonny
   ```

3. Check exchange binding:
   ```bash
   rabbitmqadmin list bindings
   ```

### Issue: High latency (>2s)

**Solution:**

1. Check metrics endpoint to identify bottleneck
2. If LLM latency high:
   - Switch to faster model (e.g., gpt-3.5-turbo)
   - Increase timeout
3. If TTS latency high:
   - Use streaming TTS API
   - Pre-generate common responses

### Issue: Letta agent not responding

**Solution:**

1. Verify Letta server is running:
   ```bash
   curl http://localhost:8283/health
   ```

2. Check Letta logs for errors
3. Verify API key (if using Letta Cloud)

## Production Deployment

### Systemd Service

Create `/etc/systemd/system/tonny.service`:

```ini
[Unit]
Description=Tonny Agent - Voice AI Service
After=network.target rabbitmq-server.service

[Service]
Type=simple
User=tonny
WorkingDirectory=/opt/tonny
Environment="PATH=/opt/tonny/.venv/bin"
ExecStart=/opt/tonny/.venv/bin/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Docker Compose

```yaml
version: '3.8'

services:
  tonny:
    build: .
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      - rabbitmq
      - letta
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  letta:
    image: letta/letta:latest
    ports:
      - "8283:8283"
    environment:
      - LETTA_LLM_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY}

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
```

## Integration with Other Services

### Candybar (Event Monitoring)

Tonny events automatically appear in Candybar. Configure visualization:

```yaml
# In Candybar config
event_filters:
  - event_type: "transcription.voice.completed"
    color: "#4CAF50"
    icon: "microphone"
  - event_type: "tts.response.completed"
    color: "#2196F3"
    icon: "speaker"
```

### WhisperLiveKit (Transcription Service)

Ensure WhisperLiveKit publishes to correct routing key:

```python
# In WhisperLiveKit
await publish_event(
    routing_key="transcription.voice.completed",
    event={
        "target": "tonny",  # Routes to Tonny
        # ...
    }
)
```

## Next Steps

1. Add custom tools to Letta agent for domain-specific tasks
2. Implement streaming TTS for lower latency
3. Add conversation history persistence
4. Integrate with additional LLM providers (Claude, Gemini)
5. Add voice activity detection for better UX

## Support

For issues or questions:

1. Check logs: `journalctl -u tonny -f`
2. Review metrics: `curl localhost:8000/metrics`
3. Test components independently
4. File issue in 33GOD repository
