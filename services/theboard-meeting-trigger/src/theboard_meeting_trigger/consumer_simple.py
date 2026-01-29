"""Simplified event consumer for TheBoard meeting triggers."""

import asyncio
import logging

from event_producers import EventConsumer
from event_producers.events.base import EventEnvelope

from .config import settings
from .meeting_creator import MeetingCreator
from .models import (
    ArchitectureReviewPayload,
    FeatureBrainstormPayload,
    MeetingTriggerPayload,
)

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TheboardMeetingTriggerConsumer(EventConsumer):
    """
    Event consumer that creates TheBoard meetings from trigger events.

    Listens for:
    - theboard.meeting.trigger - Direct meeting trigger
    - feature.brainstorm.requested - Feature ideation
    - architecture.review.needed - Architecture discussion
    """

    queue_name = settings.queue_name
    routing_keys = [
        "theboard.meeting.trigger",
        "feature.brainstorm.requested",
        "architecture.review.needed",
        "incident.postmortem.scheduled",
        "decision.analysis.required",
    ]

    def __init__(self):
        """Initialize consumer and meeting creator."""
        super().__init__()
        self.meeting_creator = MeetingCreator()

    @EventConsumer.event_handler("theboard.meeting.trigger")
    async def handle_meeting_trigger(self, envelope: EventEnvelope):
        """Handle direct meeting trigger events."""
        logger.info(f"📥 Received meeting trigger: {envelope.event_id}")

        try:
            payload = MeetingTriggerPayload(**envelope.payload)
            meeting_id, topic = await asyncio.to_thread(
                self.meeting_creator.create_meeting_from_trigger, payload
            )
            logger.info(f"✓ Created meeting {meeting_id}: {topic}")
        except Exception as e:
            logger.error(f"✗ Failed to handle meeting trigger: {e}", exc_info=True)

    @EventConsumer.event_handler("feature.brainstorm.requested")
    async def handle_feature_brainstorm(self, envelope: EventEnvelope):
        """Handle feature brainstorm requests."""
        logger.info(f"📥 Received feature brainstorm: {envelope.event_id}")

        try:
            payload = FeatureBrainstormPayload(**envelope.payload)
            meeting_id, topic = await asyncio.to_thread(
                self.meeting_creator.create_meeting_from_feature_request,
                payload.feature_name,
                payload.feature_description,
                payload.requirements,
            )
            logger.info(f"✓ Created feature brainstorm {meeting_id}: {topic}")
        except Exception as e:
            logger.error(f"✗ Failed to handle feature brainstorm: {e}", exc_info=True)

    @EventConsumer.event_handler("architecture.review.needed")
    async def handle_architecture_review(self, envelope: EventEnvelope):
        """Handle architecture review requests."""
        logger.info(f"📥 Received architecture review: {envelope.event_id}")

        try:
            payload = ArchitectureReviewPayload(**envelope.payload)
            meeting_id, topic = await asyncio.to_thread(
                self.meeting_creator.create_meeting_from_architecture_review,
                payload.component,
                payload.review_focus,
                payload.current_architecture,
            )
            logger.info(f"✓ Created architecture review {meeting_id}: {topic}")
        except Exception as e:
            logger.error(f"✗ Failed to handle architecture review: {e}", exc_info=True)


def main():
    """Run the consumer."""
    logger.info("🚀 Starting TheBoard Meeting Trigger Consumer...")
    logger.info(f"Queue: {settings.queue_name}")
    logger.info(f"Database: {settings.theboard_database_url}")
    logger.info(f"RabbitMQ: {settings.bloodbank_rabbitmq_url}")

    consumer = TheboardMeetingTriggerConsumer()

    try:
        asyncio.run(consumer.run())
    except KeyboardInterrupt:
        logger.info("⏹ Received shutdown signal")
    except Exception as e:
        logger.error(f"💥 Consumer error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
