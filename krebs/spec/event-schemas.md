# Krebs event schemas

The authority for event identity is
[`bloodbank/docs/event-naming.md`](../../bloodbank/docs/event-naming.md); the
runtime enforcement point is
`bloodbank/services/agent-hooks/core/validate.py`. Payload schemas live in
`bloodbank/schemas/bloodbank/`. This file only records which of them Krebs
touches.

## What Krebs publishes and consumes (managed v2)

| Direction | Subject | Schema |
|---|---|---|
| consumes (JetStream pull, durable `krebs-execution-v2`) | `bloodbank.cmd.lifecycle.task.invoke` | `lifecycle/task.invoke.json` |
| replies (signed receipt) | `bloodbank.rpy.lifecycle.task.invoke` | `lifecycle/task.invoke.json` |
| publishes (transactional outbox) | `bloodbank.evt.lifecycle.receipt.recorded` | `lifecycle/receipt.recorded.json` |

Source: `src/krebs/service.py` and `src/krebs/controller.py`.

## Ticket facts are not Krebs events

Krebs emits **no** `bloodbank.repo.task.*` or `bloodbank.repo.board.*`
events. Those facts come from one producer, the n8n `Plane → Bloodbank`
workflow (`bloodbank/integrations/n8n-nodes-bloodbank/src/plane.ts`,
`normalizePlaneWebhook()`), with `producer: n8n-plane-webhook` and
`source: urn:33god:integration:n8n:plane-webhook`:

| Plane delivery | `data.provider_event_type` | Bloodbank type | Schema |
|---|---|---|---|
| project created | `plane.board.created` | `bloodbank.repo.board.created` | `repo/board.created.json` |
| issue created | `plane.ticket.created` | `bloodbank.repo.task.created` | `repo/task.created.json` |
| issue updated | `plane.ticket.updated` | `bloodbank.repo.task.updated` | `repo/task.updated.json` |
| issue state change | `plane.ticket.transitioned` | `bloodbank.repo.task.updated` | `repo/task.updated.json` |
| issue deleted | `plane.ticket.deleted` | `bloodbank.repo.task.updated` | `repo/task.updated.json` |
| issue comment created | `plane.ticket.commented` | `bloodbank.repo.task.appended` | `repo/task.appended.json` |

There is no Linear or Trello normalizer. `bloodbank.repo.task.flagged` has no
schema and no producer.

When Krebs writes to Plane through Pilot, Plane's webhook echo of that write
is the fact. Krebs does not publish a fact of its own for it.
