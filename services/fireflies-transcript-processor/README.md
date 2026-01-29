# Fireflies Transcript Processor

FastStream consumer that processes `fireflies.transcript.ready` events and saves formatted transcripts as Markdown to the Vault.

**Migrated to FastStream** per ADR-0002 Phase 3.

## Architecture

**Pattern:** Standalone microservice (not embedded in Bloodbank)
**Consumer Type:** FastStream RabbitMQ subscriber
**Envelope Handling:** Explicit EventEnvelope unwrapping

**Event Flow:**
```
fireflies.transcript.ready → TranscriptProcessor → Vault (Markdown files)
```

## Configuration

Environment variables:

- `RABBIT_URL` - RabbitMQ connection (default: `amqp://guest:guest@localhost:5672/`)
- `EXCHANGE_NAME` - Bloodbank exchange (default: `bloodbank.events.v1`)
- `VAULT_PATH` - Path to Obsidian Vault (default: `~/code/DeLoDocs`)

## Installation

```bash
cd /home/delorenj/code/33GOD/services/fireflies-transcript-processor
uv sync
```

## Running

### Development (with hot reload)

```bash
uv run faststream run src.consumer:app --reload
```

### Production

```bash
uv run faststream run src.consumer:app --workers 4
```

### Docker

```bash
docker build -t fireflies-transcript-processor .
docker run -e RABBIT_URL=amqp://rabbitmq:5672/ \
           -e VAULT_PATH=/vault \
           -v ~/code/DeLoDocs:/vault \
           fireflies-transcript-processor
```

## Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html
```

## Output Format

Transcripts are saved as Markdown files with YAML frontmatter:

```markdown
---
id: transcript-123
title: "Meeting Title"
date: 2026-01-14T10:00:00Z
type: transcript
source: fireflies
tags:
  - transcript
  - meeting
---

# Meeting Title

**Date:** 2026-01-14T10:00:00Z

## Transcript

**Speaker Name** (00:15):
Transcript text here...
```

Files are saved to: `{VAULT_PATH}/Transcripts/{YYYY-MM-DD}_{Title}.md`

## References

- [ADR-0002: Agent Feedback Architecture](/home/delorenj/code/33GOD/bloodbank/trunk-main/docs/architecture/ADR-0002-agent-feedback-architecture.md)
- [Service Registry](/home/delorenj/code/33GOD/services/registry.yaml)
- [FastStream Onboarding](/home/delorenj/code/33GOD/bloodbank/trunk-main/docs/ONBOARDING_FASTSTREAM.md)
