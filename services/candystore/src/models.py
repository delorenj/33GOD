"""Pydantic models for Event Store Manager."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    """Event envelope structure matching Bloodbank schema."""

    event_id: UUID = Field(description="Unique event identifier")
    event_type: str = Field(description="Event type (e.g., 'fireflies.transcript.ready')")
    timestamp: datetime = Field(description="Event timestamp")
    version: str = Field(description="Event schema version")
    source: dict[str, Any] = Field(description="Event source metadata")
    correlation_ids: list[UUID] = Field(
        default_factory=list,
        description="Correlation IDs for causation tracking",
    )
    agent_context: dict[str, Any] | None = Field(
        default=None,
        description="Agent-specific context (checkpoint_id, session_id, etc.)",
    )
    payload: dict[str, Any] = Field(description="Event payload data")


class WorkflowState(BaseModel):
    """Aggregated workflow state projection."""

    workflow_id: UUID
    workflow_type: str
    status: str  # initiated, in_progress, completed, failed
    created_at: datetime
    updated_at: datetime
    event_count: int
    last_event_type: str | None = None
    agent_sessions: list[str] = Field(default_factory=list)
    checkpoints: list[str] = Field(default_factory=list)


class EventQuery(BaseModel):
    """Query parameters for event retrieval."""

    workflow_id: UUID | None = None
    correlation_id: UUID | None = None
    event_type: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class EventPersistenceResult(BaseModel):
    """Result of event persistence operation."""

    success: bool
    event_id: UUID
    persisted_at: datetime
    error: str | None = None
