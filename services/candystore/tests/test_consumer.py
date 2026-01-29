"""Tests for Event Store Manager consumer."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from aio_pika import IncomingMessage

from src.consumer import EventConsumer
from src.models import EventEnvelope, EventPersistenceResult


@pytest.fixture
def sample_event() -> EventEnvelope:
    """Create a sample event envelope for testing."""
    return EventEnvelope(
        event_id=uuid4(),
        event_type="test.event",
        timestamp=datetime.now(timezone.utc),
        version="1.0.0",
        source={"service": "test", "instance": "test-1"},
        correlation_ids=[],
        agent_context=None,
        payload={"test": "data"},
    )


@pytest.fixture
def mock_message(sample_event: EventEnvelope) -> MagicMock:
    """Create a mock RabbitMQ message."""
    message = MagicMock(spec=IncomingMessage)
    message.body = json.dumps(sample_event.model_dump(mode="json")).encode()
    message.routing_key = "test.event"
    message.process = MagicMock()
    message.reject = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_consumer_initialization():
    """Test consumer initializes correctly."""
    consumer = EventConsumer()

    assert consumer.connection is None
    assert consumer.channel is None
    assert consumer.queue is None
    assert consumer.event_store is not None
    assert consumer._shutdown is False


@pytest.mark.asyncio
@patch("src.consumer.aio_pika.connect_robust")
async def test_consumer_connect(mock_connect: AsyncMock):
    """Test consumer connects to RabbitMQ."""
    # Setup mocks
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_exchange = AsyncMock()
    mock_queue = AsyncMock()

    mock_connect.return_value = mock_connection
    mock_connection.channel.return_value = mock_channel
    mock_channel.declare_exchange.return_value = mock_exchange
    mock_channel.declare_queue.return_value = mock_queue

    consumer = EventConsumer()
    await consumer.connect()

    # Verify connection established
    mock_connect.assert_called_once()
    assert consumer.connection == mock_connection
    assert consumer.channel == mock_channel

    # Verify queue bound to exchange
    mock_queue.bind.assert_called_once()


@pytest.mark.asyncio
async def test_consumer_process_message_success(
    mock_message: MagicMock, sample_event: EventEnvelope
):
    """Test successful message processing."""
    consumer = EventConsumer()

    # Mock event store
    consumer.event_store.persist_event = AsyncMock(
        return_value=EventPersistenceResult(
            success=True,
            event_id=sample_event.event_id,
            persisted_at=datetime.now(timezone.utc),
        )
    )

    # Process message
    await consumer._process_message(mock_message)

    # Verify event was persisted
    consumer.event_store.persist_event.assert_called_once()
    call_args = consumer.event_store.persist_event.call_args[0][0]
    assert call_args.event_id == sample_event.event_id
    assert call_args.event_type == sample_event.event_type


@pytest.mark.asyncio
async def test_consumer_process_message_invalid_json():
    """Test handling of invalid JSON message."""
    consumer = EventConsumer()

    # Create message with invalid JSON
    message = MagicMock(spec=IncomingMessage)
    message.body = b"invalid json{"
    message.routing_key = "test.event"
    message.process = MagicMock()
    message.reject = AsyncMock()

    # Process message
    await consumer._process_message(message)

    # Verify message was rejected without requeue (sent to DLQ)
    message.reject.assert_called_once_with(requeue=False)


@pytest.mark.asyncio
async def test_consumer_process_message_persistence_failure(
    mock_message: MagicMock, sample_event: EventEnvelope
):
    """Test handling of persistence failure."""
    consumer = EventConsumer()

    # Mock event store to return failure
    consumer.event_store.persist_event = AsyncMock(
        return_value=EventPersistenceResult(
            success=False,
            event_id=sample_event.event_id,
            persisted_at=datetime.now(timezone.utc),
            error="Database connection failed",
        )
    )

    # Process message
    await consumer._process_message(mock_message)

    # Verify message was rejected with requeue (retry)
    mock_message.reject.assert_called_once_with(requeue=True)


@pytest.mark.asyncio
async def test_consumer_shutdown():
    """Test consumer shutdown."""
    consumer = EventConsumer()

    # Mock connections
    consumer.connection = AsyncMock()
    consumer.event_store.disconnect = AsyncMock()

    # Shutdown
    await consumer.stop()

    # Verify cleanup
    assert consumer._shutdown is True
    consumer.connection.close.assert_called_once()
    consumer.event_store.disconnect.assert_called_once()


@pytest.mark.asyncio
@patch("src.consumer.aio_pika.connect_robust")
async def test_consumer_connect_retry(mock_connect: AsyncMock):
    """Test consumer retries connection on failure."""
    # First two attempts fail, third succeeds
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_exchange = AsyncMock()
    mock_queue = AsyncMock()

    mock_connect.side_effect = [
        Exception("Connection failed"),
        Exception("Connection failed"),
        mock_connection,
    ]

    mock_connection.channel.return_value = mock_channel
    mock_channel.declare_exchange.return_value = mock_exchange
    mock_channel.declare_queue.return_value = mock_queue

    consumer = EventConsumer()

    # This should succeed after retries
    await consumer.connect()

    # Verify connection established after retries
    assert mock_connect.call_count == 3
    assert consumer.connection == mock_connection
