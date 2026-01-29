"""Pydantic models for meeting trigger events."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MeetingTriggerPayload(BaseModel):
    """Payload for theboard.meeting.trigger event."""

    topic: str = Field(
        min_length=10,
        max_length=500,
        description="Brainstorming topic",
    )

    strategy: Literal["sequential", "greedy"] = Field(
        default="sequential",
        description="Execution strategy",
    )

    max_rounds: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of rounds",
    )

    agent_count: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of agents to auto-select",
    )

    model: str | None = Field(
        default=None,
        description="Optional model override",
    )

    requester: str | None = Field(
        default=None,
        description="Service or user that requested the meeting",
    )

    context: dict[str, str] | None = Field(
        default=None,
        description="Additional context for meeting",
    )


class FeatureBrainstormPayload(BaseModel):
    """Payload for feature.brainstorm.requested event."""

    feature_name: str = Field(description="Feature name")
    feature_description: str = Field(description="Feature description")
    requirements: list[str] = Field(default_factory=list, description="Requirements")
    constraints: list[str] = Field(default_factory=list, description="Constraints")


class ArchitectureReviewPayload(BaseModel):
    """Payload for architecture.review.needed event."""

    component: str = Field(description="Component to review")
    review_focus: list[str] = Field(description="Focus areas for review")
    current_architecture: str | None = Field(
        default=None, description="Current architecture description"
    )


class TriggerAcknowledgmentPayload(BaseModel):
    """Payload for trigger acknowledgment events."""

    trigger_id: str = Field(description="Trigger event ID")
    trigger_type: str = Field(description="Type of trigger event")
    status: Literal["received", "processing", "completed", "failed"] = Field(
        description="Trigger processing status"
    )
    meeting_id: UUID | None = Field(
        default=None, description="Created meeting ID (if successful)"
    )
    error_message: str | None = Field(
        default=None, description="Error message (if failed)"
    )
