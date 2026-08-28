# Webhook ingress and fan-out

Krebs receives webhooks from ticket providers, normalizes them to CloudEvents, and
publishes them to Bloodbank. Downstream consumers subscribe; Krebs does not own a
private fan-out graph.

## Ingestion

One HTTP endpoint per provider:

- `POST /webhooks/plane`
- `POST /webhooks/linear`
- `POST /webhooks/trello`

Each handler verifies the provider signature, parses the payload, and emits one or
more normalized Krebs events.

## Normalization

Provider-specific events are mapped to the canonical repo-scoped task events
documented in `spec/event-schemas.md`:

- issue/card creation → `bloodbank.repo.task.created`
- issue/card update → `bloodbank.repo.task.updated`
- comment creation → `bloodbank.repo.task.appended`
- staleness detected by the Krebs sentinel → `bloodbank.repo.task.flagged`

## Fan-out

Krebs publishes normalized events to Bloodbank subjects:

- `bloodbank.evt.repo.task.created`
- `bloodbank.evt.repo.task.updated`
- `bloodbank.evt.repo.task.appended`
- `bloodbank.evt.repo.task.flagged`

Sync adapters (e.g., keep Plane and Linear in parity) consume these events and
write back to other providers via `adapters/tp/`.
