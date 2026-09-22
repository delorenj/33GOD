# Provider webhooks

Krebs does not receive, verify or normalize provider webhooks. It has no HTTP
endpoint: there is no `/webhooks/plane`, `/webhooks/linear` or
`/webhooks/trello`, and this directory holds no code.

## Where provider facts come from

The single live normalizer is the n8n **`Plane → Bloodbank`** workflow. Its
Webhook node (`POST /webhook/plane` on n8n) feeds the `PlaneBloodbank` node from
`bloodbank/integrations/n8n-nodes-bloodbank`, which verifies the Plane HMAC over
the raw body and calls `normalizePlaneWebhook()` in `src/plane.ts`. Each
delivery that routes to a known board becomes exactly one fact, published
NATS-direct with `producer: n8n-plane-webhook`:

| Plane delivery (`data.provider_event_type`) | Bloodbank type |
|---|---|
| project created (`plane.board.created`) | `bloodbank.repo.board.created` |
| issue created (`plane.ticket.created`) | `bloodbank.repo.task.created` |
| issue updated (`plane.ticket.updated`) | `bloodbank.repo.task.updated` |
| issue state change (`plane.ticket.transitioned`) | `bloodbank.repo.task.updated` |
| issue deleted (`plane.ticket.deleted`) | `bloodbank.repo.task.updated` |
| issue comment created (`plane.ticket.commented`) | `bloodbank.repo.task.appended` |

There is no Linear or Trello normalizer, and nothing publishes
`bloodbank.repo.task.flagged`. The `plane.*` names are n8n trigger aliases that
filter the canonical subject; they never appear in a wire type. Payloads are
defined by `bloodbank/schemas/bloodbank/repo/*.json`.

## What Krebs does instead

Managed v2 (`src/krebs/`) turns agent command intents into provider mutations.
It pull-subscribes `bloodbank.cmd.lifecycle.task.invoke`, writes to Plane
through Pilot (`pilot/src/provider-helper.js`), replies on
`bloodbank.rpy.lifecycle.task.invoke` and records
`bloodbank.evt.lifecycle.receipt.recorded`. It reads ticket state from Plane
through Pilot and does not subscribe to `repo.task.*`.

The provider's webhook echo of a Krebs write is the fact. Neither Krebs nor
any agent publishes `repo.task.*` or `repo.board.*` itself.
