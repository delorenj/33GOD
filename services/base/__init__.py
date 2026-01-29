"""
Bloodbank Event Consumer Base Class

Convention-over-configuration pattern for RabbitMQ event consumers.
Inspired by Symfony's service container patterns.

Usage:
    class MyConsumer(EventConsumer):
        queue_name = "my_service"
        routing_keys = ["fireflies.#", "agent.#"]

        @EventConsumer.event_handler("fireflies.transcript.ready")
        async def handle_ready(self, envelope: EventEnvelope):
            print(f"Got transcript: {envelope.payload.id}")

    if __name__ == "__main__":
        MyConsumer().run()
"""

import asyncio
import signal
from abc import ABC
from typing import Callable, Dict, Optional, Any, Coroutine

import aio_pika
from aio_pika.abc import AbstractQueue, AbstractIncomingMessage
import orjson

from event_producers.config import settings
from event_producers.events import EventEnvelope, get_registry


class EventConsumer(ABC):
    """
    Base event consumer with convention-over-configuration.

    Conventions:
    - Subclass name becomes service name
    - Methods decorated with @event_handler() auto-register
    - queue_name defaults to snake_case(class_name)
    - routing_keys defaults to ["#"] (all events)

    Attributes:
        queue_name: RabbitMQ queue name (auto-derived from class name)
        routing_keys: List of routing keys to subscribe to
        prefetch_count: Messages to prefetch (default 1)
    """

    queue_name: Optional[str] = None
    routing_keys: list[str] = ["#"]
    prefetch_count: int = 1
    durable: bool = True

    _handlers: Dict[str, Callable[..., Any]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-register event handler methods from subclasses."""
        # Collect decorated handlers from this class and parents
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if callable(attr) and hasattr(attr, "_event_type"):
                cls._handlers[attr._event_type] = attr
        super().__init_subclass__(**kwargs)

    @classmethod
    def event_handler(
        cls, event_type: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorate methods to handle specific event types.

        Usage:
            @EventConsumer.event_handler("fireflies.transcript.ready")
            async def handle_ready(self, envelope: EventEnvelope):
                ...
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            func._event_type = event_type  # type: ignore[attr-defined]
            return func

        return decorator

    @property
    def service_name(self) -> str:
        """Derive service name from class name (CamelCase → snake_case)."""
        name = self.__class__.__name__
        # Convert CamelCase to snake_case
        import re

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @property
    def default_queue_name(self) -> str:
        """Default queue name based on service name."""
        return f"{self.service_name}_queue"

    async def get_queue(self) -> AbstractQueue:
        """Declare and return queue with bindings."""
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await connection.channel()

        exchange = await channel.declare_exchange(
            settings.exchange_name, aio_pika.ExchangeType.TOPIC, durable=True
        )

        queue_name = self.queue_name or self.default_queue_name
        queue = await channel.declare_queue(queue_name, durable=self.durable)

        for routing_key in self.routing_keys:
            await queue.bind(exchange, routing_key=routing_key)

        # Set QoS for fair dispatch
        await channel.set_qos(prefetch_count=self.prefetch_count)

        return queue

    async def dispatch(self, envelope: EventEnvelope) -> bool:
        """Route event to appropriate handler."""
        handler = self._handlers.get(envelope.event_type)
        if handler:
            await handler(self, envelope)
            return True
        return False

    async def process_message(self, message: AbstractIncomingMessage) -> None:
        """Process a single message from the queue."""
        async with message.process():
            try:
                body = orjson.loads(message.body)
                envelope = EventEnvelope.model_validate(body)

                handled = await self.dispatch(envelope)

                if not handled:
                    print(f"[{self.service_name}] No handler for {envelope.event_type}")

            except Exception as e:
                print(f"[{self.service_name}] Error processing message: {e}")
                raise

    async def run(self) -> None:
        """Start consuming events. Blocks until shutdown."""
        queue = await self.get_queue()

        stop_event = asyncio.Event()

        def signal_handler():
            print(f"[{self.service_name}] Shutting down...")
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_running_loop().add_signal_handler(sig, signal_handler)

        print(f"[{self.service_name}] Listening on queue: {queue.name}")
        print(f"[{self.service_name}] Routing keys: {self.routing_keys}")
        print(
            f"[{self.service_name}] Registered handlers: {list(self._handlers.keys())}"
        )

        try:
            async with queue.iterator() as queue_iter:
                consumer_task = asyncio.create_task(
                    self._consume_loop(queue_iter, stop_event)
                )
                await stop_event.wait()
                consumer_task.cancel()
                try:
                    await consumer_task
                except asyncio.CancelledError:
                    pass
        except asyncio.CancelledError:
            pass
        finally:
            print(f"[{self.service_name}] Stopped")

    async def _consume_loop(self, queue_iter, stop_event: asyncio.Event):
        """Background task consuming messages."""
        async for message in queue_iter:
            if stop_event.is_set():
                break
            await self.process_message(message)


class SyncEventConsumer(EventConsumer):
    """
    Synchronous variant for simple consumers.

    Handlers receive (self, envelope) and can be sync or async.
    """

    async def dispatch(self, envelope: EventEnvelope) -> bool:
        handler = self._handlers.get(envelope.event_type)
        if handler:
            result = handler(self, envelope)
            if asyncio.iscoroutine(result):
                await result
            return True
        return False


# Convenience function for running consumers
def run_consumer(consumer_class: type[EventConsumer]):
    """Bootstrap and run a consumer class."""
    import sys

    print(f"Starting {consumer_class.__name__}...")
    try:
        asyncio.run(consumer_class().run())
    except KeyboardInterrupt:
        sys.exit(0)
