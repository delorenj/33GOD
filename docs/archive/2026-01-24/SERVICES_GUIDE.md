# Service Developer Guide

Welcome to the **33GOD** pipeline! This guide will help you create, register, and deploy a new microservice that integrates with the Bloodbank event ecosystem.

## 1. The Philosophy

Services in 33GOD are:

- **Passive Consumers**: They sleep until an interesting event happens.
- **Single Purpose**: Do one thing well (e.g., "Save Transcript", "Calculate Cost").
- **Stateless**: Prefer storing state in the Vault or a database, not in memory.

## 2. The Registry (`services/registry.yaml`)

Before writing code, define your service's existence.

1.  Open `services/registry.yaml`.
2.  Add a new entry under `services`:

```yaml
my-new-service:
  name: "my-new-service"
  description: "Does something amazing when X happens"
  type: "event-consumer"
  queue_name: "my_new_service_queue"
  routing_keys:
    - "domain.event.happened"
  status: "planned"
  owner: "33GOD"
  tags: ["feature", "domain"]
```

3.  Update `event_subscriptions` map:

```yaml
event_subscriptions:
  domain.event.happened:
    - "my-new-service"
```

## 3. Creating the Service

We use `cookiecutter` templates to scaffold services.

### Step 1: Generate Code

```bash
cd services
# Assuming the template exists or you copy from 'generic-consumer'
cp -r templates/generic-consumer/{{cookiecutter.service_slug}} ./my-new-service
# Rename and customize files (or use a cookiecutter tool if installed)
```

_Note: You can manually copy `services/fireflies-transcript-processor` as a reference implementation._

### Step 2: Implement the Consumer

Edit `src/consumer.py`. Your class should inherit from `EventConsumer`.

```python
from event_producers import EventConsumer, EventEnvelope

class MyServiceConsumer(EventConsumer):
    queue_name = "my_new_service_queue"
    routing_keys = ["domain.event.happened"]

    @EventConsumer.event_handler("domain.event.happened")
    async def handle_event(self, envelope: EventEnvelope):
        logger.info(f"Received: {envelope.payload}")
        # Do work here
```

### Step 3: Define Models

If your event payload is complex, define Pydantic models in `src/models.py`.

## 4. Testing

We prioritize testing. Use `pytest` and `unittest.mock`.

1.  Create `tests/test_consumer.py`.
2.  Mock the `EventConsumer` dependencies.

```bash
cd services/my-new-service
uv run pytest
```

## 5. Deployment

1.  **Dependencies**: Ensure `pyproject.toml` dependencies are correct.
2.  **Bloodbank**: Ensure `bloodbank` is linked (usually via local path in dev).
3.  **Run**:
    ```bash
    uv run python -m src.consumer
    ```

## 6. Best Practices

- **Idempotency**: Ensure processing the same event twice doesn't break things.
- **Error Handling**: Catch exceptions and log them. Don't crash the consumer.
- **Vault Integration**: If you write to the Vault, use `settings.vault_path`.
