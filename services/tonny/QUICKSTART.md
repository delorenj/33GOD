# Tonny Agent - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites

1. **RabbitMQ** (Bloodbank event bus)
   ```bash
   sudo apt install rabbitmq-server
   sudo systemctl start rabbitmq-server
   ```

2. **Letta Server** (AI agent framework)
   ```bash
   pip install letta
   letta server  # Runs on http://localhost:8283
   ```

3. **API Keys**
   - OpenAI API key (or Anthropic)
   - ElevenLabs API key

### Installation

```bash
cd ~/code/33GOD/services/tonny

# Run quick start script
./scripts/quickstart.sh

# OR manually:
uv sync
cp .env.example .env
nano .env  # Add your API keys
uv run python -m src.main
```

### Configuration

Edit `.env` file:

```bash
# Required
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...

# Optional (defaults shown)
LETTA_BASE_URL=http://localhost:8283
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
LLM_MODEL=gpt-4.1
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

### Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "service": "tonny-agent",
  "version": "0.1.0"
}
```

### Test Event Processing

Publish a test transcription event:

```bash
# Using RabbitMQ management UI:
# http://localhost:15672 (guest/guest)

# Publish to exchange: bloodbank.events.v1
# Routing key: transcription.voice.completed
# Payload:
{
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
}
```

Watch logs:

```bash
# Logs will show:
processing_transcription
llm_processing_completed
tts_generation_completed
processing_completed (with latency metrics)
tts_event_published
```

### Monitor Performance

```bash
curl http://localhost:8000/metrics
```

## 🎯 What Happens When You Send a Voice Message

1. **WhisperLiveKit** transcribes your voice → publishes event
2. **Tonny** consumes event from Bloodbank
3. **Letta agent** processes text with context
4. **ElevenLabs** generates voice response
5. **Tonny** publishes TTS event back to Bloodbank
6. **Client apps** play audio response

**Total time: <2 seconds** ⚡

## 📚 Next Steps

- See [README.md](README.md) for full documentation
- See [docs/INTEGRATION.md](docs/INTEGRATION.md) for ecosystem integration
- See [docs/LETTA_GUIDE.md](docs/LETTA_GUIDE.md) for AI customization
- See [docs/DEPLOYMENT_REPORT.md](docs/DEPLOYMENT_REPORT.md) for technical details

## 🆘 Troubleshooting

**RabbitMQ not running:**
```bash
sudo systemctl status rabbitmq-server
sudo systemctl start rabbitmq-server
```

**Letta not running:**
```bash
letta server
```

**Port 8000 already in use:**
```bash
SERVICE_PORT=8001 uv run python -m src.main
```

**API key errors:**
- Verify keys in `.env` are valid
- Check you have credits/quota remaining

## 💡 Tips

- Use `gpt-3.5-turbo` for faster responses (lower quality)
- Use `gpt-4.1` for better responses (slightly slower)
- Check `/metrics` to identify latency bottlenecks
- Monitor RabbitMQ queue depth to detect processing issues
