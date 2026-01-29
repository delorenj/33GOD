# {{ cookiecutter.service_name }}

{{ cookiecutter.service_description }}

## Configuration

Environment variables:

- `RABBITMQ_URL`: Connection string for RabbitMQ
- `EXCHANGE_NAME`: Name of the topic exchange

## Development

```bash
# Install dependencies
uv sync

# Run locally
uv run python -m src.consumer
```
