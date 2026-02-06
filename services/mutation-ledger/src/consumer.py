"""Bloodbank event consumer: enriches tool mutations and embeds into Qdrant."""

import asyncio
import json

import aio_pika
import structlog
from aio_pika import ExchangeType, IncomingMessage
from aio_pika.abc import AbstractRobustConnection

from .config import settings
from .db import insert_mutation
from .enrichment import enrich
from .models import ToolMutationEvent
from .vector_store import MutationVectorStore

logger = structlog.get_logger(__name__)


class MutationLedgerConsumer:
    """
    Consumes tool.mutation.* events from Bloodbank, enriches with semantic
    metadata, and stores in both Qdrant (primary) and SQLite (local cache).
    """

    def __init__(self) -> None:
        self.connection: AbstractRobustConnection | None = None
        self.channel = None
        self.queue = None
        self._shutdown = False
        self.vector_store = MutationVectorStore()

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
                await self.channel.set_qos(
                    prefetch_count=settings.consumer_prefetch_count,
                )

                exchange = await self.channel.declare_exchange(
                    settings.exchange_name,
                    ExchangeType.TOPIC,
                    durable=True,
                )

                self.queue = await self.channel.declare_queue(
                    settings.queue_name,
                    durable=True,
                )

                await self.queue.bind(
                    exchange,
                    routing_key=settings.routing_key_pattern,
                )

                logger.info(
                    "connected_to_rabbitmq",
                    queue=settings.queue_name,
                    exchange=settings.exchange_name,
                    routing_key=settings.routing_key_pattern,
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
        """Start consuming events."""
        await self.connect()
        logger.info("starting_mutation_ledger_consumer")

        if self.queue:
            await self.queue.consume(self._process_message)

    async def stop(self) -> None:
        """Stop consuming and close connections."""
        logger.info("stopping_mutation_ledger_consumer")
        self._shutdown = True
        if self.connection:
            await self.connection.close()

    async def _process_message(self, message: IncomingMessage) -> None:
        """Process a tool mutation event: enrich, embed, cache."""
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                event = ToolMutationEvent(**body)

                # Semantic enrichment
                enriched = enrich(event)

                logger.info(
                    "mutation_enriched",
                    tool=event.tool_name,
                    file=event.file_path,
                    intent=enriched.intent,
                    domain=enriched.domain,
                    language=enriched.language,
                )

                # Primary: embed into Qdrant
                await self.vector_store.store(enriched)

                # Secondary: SQLite local cache for fast CLI queries
                if settings.sqlite_cache_enabled:
                    await insert_mutation(event)

            except json.JSONDecodeError as e:
                logger.error(
                    "invalid_json",
                    error=str(e),
                    body=message.body.decode()[:200],
                )

            except Exception as e:
                logger.error(
                    "message_processing_error",
                    error=str(e),
                    error_type=type(e).__name__,
                )


async def run() -> None:
    """Entry point for the consumer service."""
    consumer = MutationLedgerConsumer()

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(
        __import__("signal").SIGTERM,
        lambda: asyncio.ensure_future(consumer.stop()),
    )

    try:
        await consumer.start()
        while not consumer._shutdown:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run())
