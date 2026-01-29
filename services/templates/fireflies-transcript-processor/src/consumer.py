"""
{{ cookiecutter.service_name }} - Event Consumer

Consumes {{ cookiecutter.event_types }} events from Bloodbank and processes them.
"""

import asyncio
import sys
from typing import Optional

from event_producers.config import settings
from event_producers.events import EventEnvelope
from event_producers.events.types import BloodbankEventType

# Import the base consumer from the services package
sys.path.insert(0, "/home/delorenj/code/33GOD/services")
from base import EventConsumer


class {{ cookiecutter.class_name }}Consumer(EventConsumer):
    """
    Consumer for {{ cookiecutter.event_types }} events.

    Attributes:
        queue_name: RabbitMQ queue name (auto-derived from class name)
        routing_keys: Routing keys to subscribe to
    """

    # Override to set a specific queue name
    # queue_name = "{{ cookiecutter.service_name }}_queue"

    # Override to set specific routing keys
    routing_keys: list[BloodbankEventType] = [
        {% for event_type in cookiecutter.event_types %}
        "{{ event_type }}",
        {% endfor %}
    ]

    {% for handler in cookiecutter.handlers %}
    @EventConsumer.event_handler("{{ handler.event_type }}")
    async def handle_{{ handler.name }}(self, envelope: EventEnvelope) -> None:
        """
        Handle {{ handler.description }}.

        Args:
            envelope: The event envelope containing the payload
        """
        # TODO: Implement handler logic
        print(f"[{{ self.service_name }}] Received {{ handler.event_type }}")
        print(f"[{{ self.service_name }}] Payload: {{ envelope.payload }}")

        # Access payload with type safety:
        # payload = envelope.payload  # Typed as {{ handler.payload_type }}
        pass

    {% endfor %}

    async def on_startup(self) -> None:
        """Called when consumer starts."""
        print(f"[{{ self.service_name }}] Starting up...")
        # Initialize connections, load models, etc.

    async def on_shutdown(self) -> None:
        """Called when consumer shuts down."""
        print(f"[{{ self.service_name }}] Shutting down...")
        # Cleanup connections, save state, etc.


# Convenience function for running the consumer
def run():
    """Run the consumer."""
    print("Starting {{ cookiecutter.service_name }}...")
    try:
        asyncio.run({{ cookiecutter.class_name }}Consumer().run())
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    run()
