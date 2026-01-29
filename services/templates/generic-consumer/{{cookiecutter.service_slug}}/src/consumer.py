import asyncio
import logging
from services.base import EventConsumer
from event_producers.events import EventEnvelope
from .config import settings

logger = logging.getLogger(__name__)

class ServiceConsumer(EventConsumer):
    queue_name = "{{ cookiecutter.queue_name }}"
    routing_keys = ["{{ cookiecutter.routing_key }}"]

    @EventConsumer.event_handler("{{ cookiecutter.routing_key }}")
    async def handle_event(self, envelope: EventEnvelope):
        logger.info(f"Received event: {envelope.event_type}")
        # Add your processing logic here
        # payload = envelope.payload
        # ...

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(ServiceConsumer().run())
    except KeyboardInterrupt:
        pass
