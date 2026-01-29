# {{ cookiecutter.service_name }}

{{ cookiecutter.description }}

## Overview

This is a Bloodbank event consumer that handles {{ cookiecutter.event_types }} events. It inherits from the `EventConsumer` base class which provides:

- Automatic RabbitMQ connection management
- Convention-based queue naming
- Auto-registration of `@event_handler` decorated methods
- Graceful shutdown handling

## Installation

```bash
# Development
pip install -e .

# Production
pip install .
```

## Configuration

Configuration is managed via environment variables or a `.env` file:

```env
RABBIT_URL=amqp://guest:guest@rabbitmq:5672/
EXCHANGE_NAME=bloodbank.events.v1
```

## Usage

```bash
# Run the consumer
{{ cookiecutter.service_name }}
```

## Development

```bash
# Run with hot reload (requires watchfiles)
python -m watchfiles {{ cookiecutter.service_module }}.consumer
```

## Architecture

```
{{ cookiecutter.service_name }}/
├── pyproject.toml       # Package configuration
├── Dockerfile          # Container image
├── README.md           # This file
└── src/
    ├── __init__.py     # Package init
    ├── config.py       # Pydantic settings
    └── consumer.py     # Event consumer implementation
```

## Event Handlers

This consumer handles the following event types:

{% for event_type in cookiecutter.event_types %}
- `{{ event_type }}`
{% endfor %}

## Adding New Handlers

To add a new event handler:

1. Import the event type from `event_producers.events.types`
2. Add the `@EventConsumer.event_handler()` decorator
3. Implement the handler method

```python
from event_producers.events import EventEnvelope
from event_producers.events.types import BloodbankEventType

class MyConsumer(EventConsumer):
    routing_keys: list[BloodbankEventType] = ["my.event.type"]

    @EventConsumer.event_handler("my.event.type")
    async def handle_my_event(self, envelope: EventEnvelope) -> None:
        payload = envelope.payload
        # Process the event...
```
