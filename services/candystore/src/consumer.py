"""Bloodbank event consumer for Event Store Manager."""

import asyncio
import json
from typing import Any

import aio_pika
import structlog
from aio_pika import ExchangeType, IncomingMessage
from aio_pika.abc import AbstractRobustConnection

from .config import settings
from .database import EventStore
from .models import EventEnvelope, EventPersistenceResult

logger = structlog.get_logger(__name__)


class EventConsumer:
    """Consumes all events from Bloodbank and persists to PostgreSQL."""

    def __init__(self) -> None:
        """Initialize the event consumer."""
        self.connection: AbstractRobustConnection | None = None
        self.channel: Any = None
        self.queue: Any = None
        self.event_store = EventStore()
        self._shutdown = False

    async def connect(self) -> None:
        """Establish connection to RabbitMQ with exponential backoff."""
        retry_count = 0
        max_retries = 10
        base_delay = 1

        while retry_count < max_retries and not self._shutdown:
            try:
                logger.info("connecting_to_rabbitmq", url=settings.rabbitmq_url)
                self.connection = await aio_pika.connect_robust(
                    settings.rabbitmq_url,
                    heartbeat=60,
                )

                self.channel = await self.connection.channel()
                await self.channel.set_qos(prefetch_count=10)

                # Declare exchange
                exchange = await self.channel.declare_exchange(
                    settings.bloodbank_exchange,
                    ExchangeType.TOPIC,
                    durable=True,
                )

                # Declare queue with DLQ
                self.queue = await self.channel.declare_queue(
                    settings.event_store_manager_queue,
                    durable=True,
                    arguments={
                        "x-dead-letter-exchange": "",
                        "x-dead-letter-routing-key": settings.event_store_manager_dlq,
                    },
                )

                # Declare DLQ
                await self.channel.declare_queue(
                    settings.event_store_manager_dlq,
                    durable=True,
                )

                # Bind queue to exchange with wildcard (#)
                await self.queue.bind(exchange, routing_key="#")

                logger.info(
                    "connected_to_rabbitmq",
                    queue=settings.event_store_manager_queue,
                    exchange=settings.bloodbank_exchange,
                )
                return

            except Exception as e:
                retry_count += 1
                delay = base_delay * (2**retry_count)
                logger.error(
                    "rabbitmq_connection_failed",
                    error=str(e),
                    retry_count=retry_count,
                    retry_delay=delay,
                )
                if retry_count < max_retries:
                    await asyncio.sleep(delay)
                else:
                    raise

    async def start(self) -> None:
        """Start consuming events from Bloodbank."""
        await self.connect()
        await self.event_store.connect()

        logger.info("starting_event_consumer")

        if self.queue:
            await self.queue.consume(self._process_message)

    async def stop(self) -> None:
        """Stop consuming and close connections."""
        logger.info("stopping_event_consumer")
        self._shutdown = True

        if self.connection:
            await self.connection.close()

        await self.event_store.disconnect()

    async def _process_message(self, message: IncomingMessage) -> None:
        """
        Process a single message from Bloodbank.

        Manual ack/reject to avoid double-processing from context manager.
        1. Deserialize event
        2. Persist to PostgreSQL
        3. ACK if persist succeeds, REJECT+requeue otherwise
        """
        try:
            # Deserialize message body
            body = json.loads(message.body.decode())

            # Parse into EventEnvelope
            envelope = EventEnvelope(**body)

            logger.info(
                "processing_event",
                event_id=str(envelope.event_id),
                event_type=envelope.event_type,
                routing_key=message.routing_key,
            )

            # Persist to PostgreSQL
            result: EventPersistenceResult = await self.event_store.persist_event(
                envelope
            )

            if result.success:
                logger.info(
                    "event_persisted",
                    event_id=str(result.event_id),
                    persisted_at=result.persisted_at.isoformat(),
                )
                await message.ack()
            else:
                logger.error(
                    "event_persistence_failed",
                    event_id=str(result.event_id),
                    error=result.error,
                )
                await message.reject(requeue=True)

        except json.JSONDecodeError as e:
            logger.error(
                "invalid_json",
                error=str(e),
                body=message.body.decode()[:200],
            )
            # Don't requeue invalid JSON - send to DLQ
            await message.reject(requeue=False)

        except Exception as e:
            logger.error(
                "message_processing_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Reject and requeue for transient errors
            try:
                await message.reject(requeue=True)
            except Exception:
                pass  # Already processed
