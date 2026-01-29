# Tonny Agent

Letta-powered AI agent for processing voice transcriptions and generating TTS responses in the 33GOD ecosystem.

## Overview

Tonny is a Bloodbank event consumer that:

1. Listens for `transcription.voice.completed` events from WhisperLiveKit
2. Processes transcriptions through a stateful Letta agent
3. Generates voice responses via ElevenLabs TTS
4. Publishes `tts.response.completed` events back to Bloodbank

**Target latency:** <2 seconds from transcription to TTS completion

## Architecture

```
WhisperLiveKit → Bloodbank → Tonny Agent
                                ↓
                          Letta Agent (LLM)
                                ↓
                          ElevenLabs TTS
                                ↓
                            Bloodbank → (Consumers)
```

## Prerequisites

- Python 3.12+
- RabbitMQ (Bloodbank event bus)
- Letta server (self-hosted or cloud)
- OpenAI or Anthropic API key
- ElevenLabs API key

## Installation

```bash
# Clone repository
cd ~/code/33GOD/services/tonny

# Install dependencies with uv
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

## Configuration

Edit `.env` file:

```bash
# RabbitMQ (Bloodbank)
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Letta
LETTA_BASE_URL=http://localhost:8283
LETTA_API_KEY=your_letta_api_key  # Optional for self-hosted

# LLM Provider
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
LLM_MODEL=gpt-4.1

# ElevenLabs
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Rachel voice
```

## Running the Service

### Development

```bash
# Start service
uv run python -m src.main

# Or with uvicorn reload
uv run uvicorn src.main:app --reload --port 8000
```

### Production

```bash
# Using uvicorn
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or using the main entry point
uv run python -m src.main
```

### Docker

```bash
# Build image
docker build -t tonny-agent .

# Run container
docker run -d \
  --name tonny-agent \
  --env-file .env \
  -p 8000:8000 \
  tonny-agent
```

## API Endpoints

- `GET /health` - Health check
- `GET /metrics` - Processing metrics and latency statistics

## Event Schema

### Consumed Events

**Topic:** `transcription.voice.completed`

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
    "language": "en"
  }
}
```

### Published Events

**Topic:** `tts.response.completed`

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
    "audio_base64": "base64_encoded_audio...",
    "voice_id": "21m00Tcm4TlvDq8ikWAM",
    "model_id": "eleven_monolingual_v1",
    "character_count": 45,
    "original_transcription": "What's the weather today?"
  }
}
```

## Letta Agent Configuration

The Letta agent is configured with a voice-optimized persona:

- **Name:** tonny-voice-assistant
- **Persona:** Helpful voice assistant with concise, conversational responses
- **Context:** Optimized for spoken interactions
- **Memory:** Stateful conversation tracking via session IDs

## Performance Targets

- **Total latency:** <2000ms (transcription → TTS completion)
- **LLM latency:** <1000ms
- **TTS latency:** <500ms
- **Consumer latency:** <500ms

Check `/metrics` endpoint to monitor actual performance.

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html

# Run specific test
uv run pytest tests/test_consumer.py::test_process_transcription
```

### Linting and Formatting

```bash
# Lint with ruff
uv run ruff check src/

# Format code
uv run ruff format src/
```

## Troubleshooting

### Connection Issues

1. **RabbitMQ not reachable:**
   - Check `RABBITMQ_URL` in `.env`
   - Verify RabbitMQ is running: `sudo systemctl status rabbitmq-server`

2. **Letta agent not found:**
   - Check `LETTA_BASE_URL` points to running Letta server
   - Verify Letta server health: `curl http://localhost:8283/health`

3. **ElevenLabs rate limits:**
   - Monitor logs for 429 errors
   - Check `Retry-After` header in logs
   - Consider upgrading ElevenLabs plan for higher quota

### Performance Issues

1. **High latency:**
   - Check `/metrics` endpoint to identify bottleneck (LLM vs TTS)
   - Increase `CONSUMER_PREFETCH_COUNT` for parallel processing
   - Consider using streaming TTS for lower latency

2. **Event loss:**
   - Check dead letter queue: `services.tonny.agent.dlq`
   - Review logs for processing errors
   - Verify HolyFields schema validation

## Integration with 33GOD Ecosystem

### Register in Services Registry

The service is registered in `~/code/33GOD/services/registry.yaml`:

```yaml
services:
  tonny-agent:
    name: "tonny-agent"
    description: "Letta-powered AI agent for voice interaction"
    type: "event-consumer"
    queue_name: "services.tonny.agent"
    routing_keys:
      - "transcription.voice.completed"
    produces:
      - "tts.response.completed"
    status: "active"
```

### Event Flow

1. User speaks → WhisperLiveKit
2. WhisperLiveKit publishes `transcription.voice.completed`
3. Tonny consumes event, processes via Letta
4. Tonny generates TTS, publishes `tts.response.completed`
5. Client applications consume TTS event for audio playback

## Contributing

1. Follow 33GOD service patterns
2. Use structured logging (structlog)
3. Write tests for new features
4. Update documentation
5. Target <2s latency for all changes

## License

MIT

## Contact

Jarad DeLorenzo - 33GOD Ecosystem
