"""Service for creating TheBoard meetings from database."""

import logging
from uuid import UUID, uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

# Import TheBoard models directly
# Note: In production, consider shared library or API approach
import sys
from pathlib import Path

# Add TheBoard to path
theboard_path = Path("/home/delorenj/code/33GOD/theboard/trunk-main/src")
sys.path.insert(0, str(theboard_path))

from theboard.models.meeting import Agent, Meeting
from theboard.schemas import StrategyType

from .config import settings
from .models import MeetingTriggerPayload

logger = logging.getLogger(__name__)


class MeetingCreator:
    """Creates TheBoard meetings via direct database access."""

    def __init__(self):
        """Initialize database connection."""
        self.engine = create_engine(
            str(settings.theboard_database_url),
            pool_pre_ping=True,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

    def create_meeting_from_trigger(
        self, payload: MeetingTriggerPayload
    ) -> tuple[UUID, str]:
        """
        Create a new meeting from trigger payload.

        Args:
            payload: Meeting trigger payload

        Returns:
            Tuple of (meeting_id, meeting_topic)

        Raises:
            Exception: If meeting creation fails
        """
        with self.SessionLocal() as db:
            try:
                # Create meeting
                # Note: Agents are selected and assigned during meeting execution,
                # not at creation time. They participate through Response records.
                meeting = Meeting(
                    id=uuid4(),
                    topic=payload.topic,
                    strategy=StrategyType(payload.strategy),
                    max_rounds=payload.max_rounds,
                    model_override=payload.model,
                )

                db.add(meeting)
                db.commit()
                db.refresh(meeting)

                logger.info(
                    f"Created meeting {meeting.id}: {meeting.topic}"
                )

                return meeting.id, meeting.topic

            except Exception as e:
                db.rollback()
                logger.error(f"Failed to create meeting: {e}")
                raise

    def create_meeting_from_feature_request(
        self, feature_name: str, feature_description: str, requirements: list[str]
    ) -> tuple[UUID, str]:
        """
        Create meeting from feature brainstorm request.

        Args:
            feature_name: Name of the feature
            feature_description: Description of the feature
            requirements: List of requirements

        Returns:
            Tuple of (meeting_id, meeting_topic)
        """
        # Construct topic from feature request
        topic = f"Feature Brainstorm: {feature_name} - {feature_description}"

        if len(topic) > 500:
            topic = topic[:497] + "..."

        # Create meeting with default parameters
        payload = MeetingTriggerPayload(
            topic=topic,
            strategy="sequential",
            max_rounds=settings.default_max_rounds,
            agent_count=settings.default_agent_count,
            context={
                "feature_name": feature_name,
                "requirements": ", ".join(requirements[:5]),  # Limit to 5
            },
        )

        return self.create_meeting_from_trigger(payload)

    def create_meeting_from_architecture_review(
        self, component: str, review_focus: list[str], current_architecture: str | None
    ) -> tuple[UUID, str]:
        """
        Create meeting from architecture review request.

        Args:
            component: Component to review
            review_focus: Focus areas for review
            current_architecture: Optional current architecture description

        Returns:
            Tuple of (meeting_id, meeting_topic)
        """
        topic = (
            f"Architecture Review: {component} - "
            f"Focus: {', '.join(review_focus[:3])}"
        )

        if len(topic) > 500:
            topic = topic[:497] + "..."

        payload = MeetingTriggerPayload(
            topic=topic,
            strategy="sequential",
            max_rounds=settings.default_max_rounds,
            agent_count=settings.default_agent_count,
            context={
                "component": component,
                "review_focus": ", ".join(review_focus),
            },
        )

        return self.create_meeting_from_trigger(payload)
