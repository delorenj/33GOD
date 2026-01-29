"""
TheBoard Meeting Trigger - FastStream Consumer

Subscribes to trigger events and creates TheBoard meetings.
Publishes acknowledgment events with correlation tracking.

Migrated from legacy EventConsumer to FastStream per ADR-0002.
"""

import asyncio
import logging
from typing import Any, Dict

from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, ExchangeType

from event_producers.config import settings as bloodbank_settings
from event_producers.events.base import EventEnvelope
from event_producers.rabbit import Publisher

from .config import settings
from .meeting_creator import MeetingCreator
from .models import (
    ArchitectureReviewPayload,
    FeatureBrainstormPayload,
    MeetingTriggerPayload,
    TriggerAcknowledgmentPayload,
)

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize broker and FastStream app
broker = RabbitBroker(bloodbank_settings.rabbit_url)
app = FastStream(broker)

# Initialize meeting creator and publisher
meeting_creator = MeetingCreator()
publisher = Publisher(enable_correlation_tracking=True)


@app.after_startup
async def startup():
    """Initialize publisher connection on app startup."""
    await publisher.start()
    logger.info("TheBoard Meeting Trigger started")


@app.after_shutdown
async def shutdown():
    """Close publisher connection on app shutdown."""
    await publisher.close()
    logger.info("TheBoard Meeting Trigger shutdown")


@broker.subscriber(
    queue=RabbitQueue(
        name="services.theboard.meeting_trigger",
        routing_key="theboard.meeting.trigger",
        durable=True,
    ),
    exchange=RabbitExchange(
        name=bloodbank_settings.exchange_name,
        type=ExchangeType.TOPIC,
        durable=True,
    ),
)
async def handle_meeting_trigger(message_dict: Dict[str, Any]):
    """
    Handle direct meeting trigger events.

    Unwraps EventEnvelope, creates TheBoard meeting.
    Follows ADR-0002: explicit envelope unwrapping pattern.
    """
    # Unwrap EventEnvelope
    envelope = EventEnvelope(**message_dict)

    logger.info(
        "Received meeting trigger: %s (correlation: %s)",
        envelope.event_type,
        envelope.event_id,
    )

    try:
        # Parse payload
        payload = MeetingTriggerPayload(**envelope.payload)

        # Create meeting
        meeting_id, topic = await asyncio.to_thread(
            meeting_creator.create_meeting_from_trigger, payload
        )

        logger.info("✓ Created meeting %s: %s", meeting_id, topic)

    except Exception as e:
        logger.error("✗ Failed to handle meeting trigger: %s", e, exc_info=True)


@broker.subscriber(
    queue=RabbitQueue(
        name="services.theboard.feature_brainstorm",
        routing_key="feature.brainstorm.requested",
        durable=True,
    ),
    exchange=RabbitExchange(
        name=bloodbank_settings.exchange_name,
        type=ExchangeType.TOPIC,
        durable=True,
    ),
)
async def handle_feature_brainstorm(message_dict: Dict[str, Any]):
    """
    Handle feature brainstorm requests.

    Unwraps EventEnvelope, creates feature brainstorm meeting, publishes acknowledgments.
    Follows ADR-0002: explicit envelope unwrapping pattern.
    """
    # Unwrap EventEnvelope
    envelope = EventEnvelope(**message_dict)

    logger.info(
        "Received feature brainstorm request: %s (correlation: %s)",
        envelope.event_type,
        envelope.event_id,
    )

    try:
        payload = FeatureBrainstormPayload(**envelope.payload)

        await _emit_acknowledgment(
            trigger_id=envelope.event_id,
            trigger_type="feature.brainstorm",
            status="processing",
        )

        meeting_id, topic = await asyncio.to_thread(
            meeting_creator.create_meeting_from_feature_request,
            payload.feature_name,
            payload.feature_description,
            payload.requirements,
        )

        logger.info("Created feature brainstorm meeting %s: %s", meeting_id, topic)

        await _emit_acknowledgment(
            trigger_id=envelope.event_id,
            trigger_type="feature.brainstorm",
            status="completed",
            meeting_id=meeting_id,
        )

    except Exception as e:
        logger.error("Failed to handle feature brainstorm: %s", e, exc_info=True)

        await _emit_acknowledgment(
            trigger_id=envelope.event_id,
            trigger_type="feature.brainstorm",
            status="failed",
            error_message=str(e),
        )


@broker.subscriber(
    queue=RabbitQueue(
        name="services.theboard.architecture_review",
        routing_key="architecture.review.needed",
        durable=True,
    ),
    exchange=RabbitExchange(
        name=bloodbank_settings.exchange_name,
        type=ExchangeType.TOPIC,
        durable=True,
    ),
)
async def handle_architecture_review(message_dict: Dict[str, Any]):
    """
    Handle architecture review requests.

    Unwraps EventEnvelope, creates architecture review meeting, publishes acknowledgments.
    Follows ADR-0002: explicit envelope unwrapping pattern.
    """
    # Unwrap EventEnvelope
    envelope = EventEnvelope(**message_dict)

    logger.info(
        "Received architecture review request: %s (correlation: %s)",
        envelope.event_type,
        envelope.event_id,
    )

    try:
        payload = ArchitectureReviewPayload(**envelope.payload)

        await _emit_acknowledgment(
            trigger_id=envelope.event_id,
            trigger_type="architecture.review",
            status="processing",
        )

        meeting_id, topic = await asyncio.to_thread(
            meeting_creator.create_meeting_from_architecture_review,
            payload.component,
            payload.review_focus,
            payload.current_architecture,
        )

        logger.info("Created architecture review meeting %s: %s", meeting_id, topic)

        await _emit_acknowledgment(
            trigger_id=envelope.event_id,
            trigger_type="architecture.review",
            status="completed",
            meeting_id=meeting_id,
        )

    except Exception as e:
        logger.error("Failed to handle architecture review: %s", e, exc_info=True)

        await _emit_acknowledgment(
            trigger_id=envelope.event_id,
            trigger_type="architecture.review",
            status="failed",
            error_message=str(e),
        )


@broker.subscriber(
    queue=RabbitQueue(
        name="services.theboard.incident_postmortem",
        routing_key="incident.postmortem.scheduled",
        durable=True,
    ),
    exchange=RabbitExchange(
        name=bloodbank_settings.exchange_name,
        type=ExchangeType.TOPIC,
        durable=True,
    ),
)
async def handle_incident_postmortem(message_dict: Dict[str, Any]):
    """
    Handle incident postmortem requests.

    Unwraps EventEnvelope and creates postmortem meeting.
    Follows ADR-0002: explicit envelope unwrapping pattern.
    """
    # Unwrap EventEnvelope
    envelope = EventEnvelope(**message_dict)

    logger.info(
        "Received incident postmortem request: %s (correlation: %s)",
        envelope.event_type,
        envelope.event_id,
    )

    # Future: Implement postmortem meeting creation
    logger.warning("Incident postmortem handler not yet implemented")


@broker.subscriber(
    queue=RabbitQueue(
        name="services.theboard.decision_analysis",
        routing_key="decision.analysis.required",
        durable=True,
    ),
    exchange=RabbitExchange(
        name=bloodbank_settings.exchange_name,
        type=ExchangeType.TOPIC,
        durable=True,
    ),
)
async def handle_decision_analysis(message_dict: Dict[str, Any]):
    """
    Handle decision analysis requests.

    Unwraps EventEnvelope and creates decision analysis meeting.
    Follows ADR-0002: explicit envelope unwrapping pattern.
    """
    # Unwrap EventEnvelope
    envelope = EventEnvelope(**message_dict)

    logger.info(
        "Received decision analysis request: %s (correlation: %s)",
        envelope.event_type,
        envelope.event_id,
    )

    # Future: Implement decision analysis meeting creation
    logger.warning("Decision analysis handler not yet implemented")


async def _emit_acknowledgment(
    trigger_id: str,
    trigger_type: str,
    status: str,
    meeting_id=None,
    error_message: str | None = None,
):
    """Emit trigger acknowledgment event with correlation tracking."""
    try:
        ack_payload = TriggerAcknowledgmentPayload(
            trigger_id=trigger_id,
            trigger_type=trigger_type,
            status=status,
            meeting_id=meeting_id,
            error_message=error_message,
        )

        await publisher.publish(
            routing_key=f"theboard.meeting.trigger.{status}",
            message=ack_payload.model_dump(mode="json"),
        )

        logger.debug("Emitted acknowledgment: %s for %s", status, trigger_id)

    except Exception as e:
        logger.error("Failed to emit acknowledgment: %s", e)
