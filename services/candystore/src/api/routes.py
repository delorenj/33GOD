"""FastAPI routes for Event Store Manager."""

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query

from ..database import EventStore
from ..models import EventEnvelope, EventQuery, WorkflowState

logger = structlog.get_logger(__name__)

router = APIRouter()

# Shared event store instance (will be initialized in main)
event_store: EventStore | None = None


def set_event_store(store: EventStore) -> None:
    """Set the global event store instance."""
    global event_store
    event_store = store


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "event-store-manager"}


@router.get("/events", response_model=list[EventEnvelope])
async def query_events(
    workflow_id: UUID | None = Query(None, description="Filter by workflow ID"),
    correlation_id: UUID | None = Query(None, description="Filter by correlation ID"),
    event_type: str | None = Query(None, description="Filter by event type (exact or prefix with *)"),
    agent: str | None = Query(None, description="Filter by agent name (matches agent.{name}.* routing keys)"),
    since: datetime | None = Query(None, alias="start_time", description="Filter events after this time"),
    until: datetime | None = Query(None, alias="end_time", description="Filter events before this time"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> list[EventEnvelope]:
    """
    Query events from the event store.

    Supports filtering by:
    - workflow_id: Get all events for a specific workflow
    - correlation_id: Get causation chain
    - event_type: Filter by event type (exact match or prefix*)
    - agent: Filter by agent name (matches agent.{name}.* routing keys)
    - since/until (or start_time/end_time): Time range filtering
    """
    if not event_store:
        raise HTTPException(status_code=503, detail="Event store not available")

    # If agent filter, convert to event_type prefix filter
    effective_event_type = event_type
    if agent and not event_type:
        effective_event_type = f"agent.{agent}.*"

    query = EventQuery(
        workflow_id=workflow_id,
        correlation_id=correlation_id,
        event_type=effective_event_type,
        start_time=since,
        end_time=until,
        limit=limit,
        offset=offset,
    )

    try:
        events = await event_store.query_events(query)
        logger.info("events_queried", count=len(events))
        return events
    except Exception as e:
        logger.error("query_events_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.get("/events/{event_id}", response_model=EventEnvelope)
async def get_event(event_id: UUID) -> EventEnvelope:
    """Get a specific event by ID."""
    if not event_store:
        raise HTTPException(status_code=503, detail="Event store not available")

    # Query for single event
    query = EventQuery(limit=1)
    try:
        # Use raw query for exact event_id match
        if not event_store.pool:
            raise HTTPException(status_code=503, detail="Database not available")

        async with event_store.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT event_id, event_type, timestamp, version,
                       source, correlation_ids, agent_context, payload
                FROM events
                WHERE event_id = $1
                """,
                event_id,
            )

        if not row:
            raise HTTPException(status_code=404, detail="Event not found")

        return EventEnvelope(
            event_id=row["event_id"],
            event_type=row["event_type"],
            timestamp=row["timestamp"],
            version=row["version"],
            source=row["source"],
            correlation_ids=list(row["correlation_ids"]),
            agent_context=row["agent_context"],
            payload=row["payload"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_event_failed", event_id=str(event_id), error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.get("/events/{event_id}/descendants", response_model=list[EventEnvelope])
async def get_event_descendants(
    event_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
) -> list[EventEnvelope]:
    """
    Get all downstream events (descendants) of a given event.

    Traces the causation chain forward from the specified event.
    """
    if not event_store:
        raise HTTPException(status_code=503, detail="Event store not available")

    try:
        # Recursive query to get all descendants
        query = EventQuery(correlation_id=event_id, limit=limit)
        descendants = await event_store.query_events(query)

        logger.info("descendants_queried", event_id=str(event_id), count=len(descendants))
        return descendants
    except Exception as e:
        logger.error("get_descendants_failed", event_id=str(event_id), error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.get("/workflows/{workflow_id}/timeline", response_model=dict[str, Any])
async def get_workflow_timeline(workflow_id: UUID) -> dict[str, Any]:
    """
    Get complete timeline for a workflow.

    Returns workflow state projection and all associated events.
    """
    if not event_store:
        raise HTTPException(status_code=503, detail="Event store not available")

    try:
        # Get workflow state
        workflow_state = await event_store.get_workflow_state(workflow_id)

        if not workflow_state:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Get all events for this workflow
        query = EventQuery(workflow_id=workflow_id, limit=1000)
        events = await event_store.query_events(query)

        return {
            "workflow_state": workflow_state.model_dump(),
            "events": [e.model_dump() for e in events],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_workflow_timeline_failed", workflow_id=str(workflow_id), error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.get("/workflows/{workflow_id}/state", response_model=WorkflowState)
async def get_workflow_state_endpoint(workflow_id: UUID) -> WorkflowState:
    """Get workflow state projection."""
    if not event_store:
        raise HTTPException(status_code=503, detail="Event store not available")

    try:
        workflow_state = await event_store.get_workflow_state(workflow_id)

        if not workflow_state:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return workflow_state
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_workflow_state_failed", workflow_id=str(workflow_id), error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.get("/agents/{session_id}/events", response_model=list[EventEnvelope])
async def get_agent_events(
    session_id: str,
    limit: int = Query(100, ge=1, le=1000),
) -> list[EventEnvelope]:
    """
    Get all events associated with a specific agent session.

    Useful for debugging agent behavior and tracking agent workflows.
    """
    if not event_store:
        raise HTTPException(status_code=503, detail="Event store not available")

    try:
        if not event_store.pool:
            raise HTTPException(status_code=503, detail="Database not available")

        async with event_store.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT event_id, event_type, timestamp, version,
                       source, correlation_ids, agent_context, payload
                FROM events
                WHERE agent_context @> $1
                ORDER BY timestamp DESC
                LIMIT $2
                """,
                {"session_id": session_id},
                limit,
            )

        events = [
            EventEnvelope(
                event_id=row["event_id"],
                event_type=row["event_type"],
                timestamp=row["timestamp"],
                version=row["version"],
                source=row["source"],
                correlation_ids=list(row["correlation_ids"]),
                agent_context=row["agent_context"],
                payload=row["payload"],
            )
            for row in rows
        ]

        logger.info("agent_events_queried", session_id=session_id, count=len(events))
        return events
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_agent_events_failed", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
