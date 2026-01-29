"""
Fireflies Transcript Processor - FastStream Consumer

Subscribes to fireflies.transcript.ready events and processes them.
Formats transcripts as Markdown and saves them to the Vault.

Migrated from legacy EventConsumer to FastStream per ADR-0002.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, ExchangeType

from event_producers.config import settings as bloodbank_settings
from event_producers.events.base import EventEnvelope, create_envelope, Source, TriggerType
from event_producers.rabbit import Publisher

from .config import settings
from .models import TranscriptData

logger = logging.getLogger(__name__)

# Initialize broker and FastStream app
broker = RabbitBroker(bloodbank_settings.rabbit_url)
app = FastStream(broker)

# Initialize publisher for artifact.created events
publisher = Publisher()


@app.after_startup
async def startup():
    """Initialize on app startup."""
    await publisher.start()
    logger.info("Fireflies Transcript Processor started")


@app.after_shutdown
async def shutdown():
    """Cleanup on app shutdown."""
    await publisher.stop()
    logger.info("Fireflies Transcript Processor shutdown")


@broker.subscriber(
    queue=RabbitQueue(
        name="services.fireflies.transcript_processor",
        routing_key="fireflies.transcript.ready",
        durable=True,
    ),
    exchange=RabbitExchange(
        name=bloodbank_settings.exchange_name,
        type=ExchangeType.TOPIC,
        durable=True,
    ),
)
async def handle_transcript_ready(message_dict: Dict[str, Any]):
    """
    Handle fireflies.transcript.ready events.

    Unwraps EventEnvelope, processes transcript, and saves to Vault.
    Follows ADR-0002: explicit envelope unwrapping pattern.
    """
    # Unwrap EventEnvelope
    envelope = EventEnvelope(**message_dict)

    logger.info(
        "Received transcript event: %s (correlation: %s)",
        envelope.event_type,
        envelope.event_id,
    )

    try:
        # Parse payload into our model
        data = TranscriptData.model_validate(envelope.payload)

        # Process transcript
        await process_transcript(data)

        logger.info(
            "Successfully processed transcript: %s",
            data.title,
        )

    except Exception as e:
        logger.error(
            "Error processing transcript: %s",
            e,
            exc_info=True,
        )
        # Future: publish failure event with correlation tracking
        # await publish_failure_event(envelope, str(e))


async def process_transcript(data: TranscriptData):
    """Formats and saves the transcript to DeLoDocs and publishes artifact.created event."""

    # 1. Format Content
    markdown_content = _format_markdown(data)

    # 2. Generate Filename
    filename = _generate_filename(data)

    # 3. Save File
    output_dir = Path(settings.vault_path) / "Transcriptions"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / filename

    # Write file (sync operation in async function - use executor if heavy)
    # For text files, direct write is usually fine for low throughput
    output_file.write_text(markdown_content, encoding="utf-8")
    logger.info("Saved transcript to %s", output_file)

    # 4. Publish artifact.created event
    artifact_payload = {
        "artifact_type": "transcript",
        "source": "fireflies",
        "file_path": str(output_file),
        "transcript_id": data.id,
        "title": data.title,
        "date": data.date,
    }

    envelope = create_envelope(
        event_type="artifact.created",
        payload=artifact_payload,
        source=Source(
            host="fireflies-transcript-processor",
            type=TriggerType.AGENT,
            app="fireflies-transcript-processor",
        ),
    )

    await publisher.publish(
        routing_key="artifact.created",
        body=envelope.model_dump(mode="json"),
    )
    logger.info("Published artifact.created event for %s", data.title)


def _format_markdown(data: TranscriptData) -> str:
    """Generates the Markdown content with YAML frontmatter."""

    # Helper to format time
    def format_time(seconds: float | None) -> str:
        if seconds is None:
            return "00:00"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    # Build YAML Frontmatter
    lines = [
        "---",
        f"id: {data.id}",
        f'title: "{data.title}"',
        f"date: {data.date}",
        "type: transcript",
        "source: fireflies",
        "tags:",
        "  - transcript",
        "  - meeting",
        "---",
        "",
        f"# {data.title}",
        "",
        f"**Date:** {data.date}",
        "",
        "## Transcript",
        ""
    ]

    # Build Transcript Body
    current_speaker = None

    for sentence in data.sentences:
        speaker = sentence.speaker_name or "Unknown Speaker"
        timestamp = format_time(sentence.start_time)
        text = sentence.text.strip()

        if speaker != current_speaker:
            lines.append(f"\n**{speaker}** ({timestamp}):")
            current_speaker = speaker

        lines.append(f"{text}")

    return "\n".join(lines)


def _generate_filename(data: TranscriptData) -> str:
    """Generates a safe filename: YYYY-MM-DD_Title.md"""
    try:
        # Attempt to parse date from ISO string
        date_obj = datetime.fromisoformat(data.date.replace("Z", "+00:00"))
        date_str = date_obj.strftime("%Y-%m-%d")
    except ValueError:
        # Fallback if date parsing fails
        date_str = datetime.now().strftime("%Y-%m-%d")

    # Sanitize title
    safe_title = re.sub(r'[^a-zA-Z0-9\s-]', '', data.title)
    safe_title = re.sub(r'\s+', '-', safe_title).strip('-')

    return f"{date_str}_{safe_title}.md"
