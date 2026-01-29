"""Tests for meeting trigger consumer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.theboard_meeting_trigger.consumer import TheboardMeetingTriggerConsumer
from src.theboard_meeting_trigger.models import MeetingTriggerPayload


@pytest.fixture
def consumer():
    """Create consumer instance."""
    return TheboardMeetingTriggerConsumer()


@pytest.fixture
def mock_event_envelope():
    """Create mock event envelope."""
    envelope = MagicMock()
    envelope.event_id = "test-event-123"
    envelope.payload = {
        "topic": "Test brainstorming topic for architecture patterns",
        "strategy": "sequential",
        "max_rounds": 3,
        "agent_count": 5,
    }
    return envelope


@pytest.mark.asyncio
async def test_handle_meeting_trigger_success(consumer, mock_event_envelope):
    """Test successful meeting trigger handling."""
    meeting_id = uuid4()

    with patch.object(
        consumer.meeting_creator,
        "create_meeting_from_trigger",
        return_value=(meeting_id, "Test topic"),
    ):
        with patch.object(consumer, "_emit_acknowledgment", new_callable=AsyncMock):
            await consumer.handle_meeting_trigger(mock_event_envelope)

            # Should emit processing and completed acknowledgments
            assert consumer._emit_acknowledgment.call_count == 2


@pytest.mark.asyncio
async def test_handle_meeting_trigger_failure(consumer, mock_event_envelope):
    """Test meeting trigger handling with creation failure."""
    with patch.object(
        consumer.meeting_creator,
        "create_meeting_from_trigger",
        side_effect=Exception("Database error"),
    ):
        with patch.object(consumer, "_emit_acknowledgment", new_callable=AsyncMock):
            await consumer.handle_meeting_trigger(mock_event_envelope)

            # Should emit processing and failed acknowledgments
            assert consumer._emit_acknowledgment.call_count == 2

            # Last call should have status="failed"
            last_call = consumer._emit_acknowledgment.call_args_list[-1]
            assert last_call[1]["status"] == "failed"
