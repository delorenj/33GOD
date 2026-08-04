# Krebs

The ticket-lifecycle and task-platform engine for 33GOD.

Krebs owns the canonical state machine that drives work from intake to done, the
ticket-provider abstraction that lets that machine talk to Plane, Linear, Trello,
or any future tracker, and the webhook fan-out layer that turns provider events
into normalized Bloodbank events for downstream observability and synchronization.

## Scope

| Concern | Owner in Krebs | Consumed by |
|---|---|---|
| Lifecycle state machine | `spec/lifecycle.v1.yaml` | Momo, Hermes PM, MCP hub, Holocene |
| Provider abstraction | `adapters/tp/` | Momo, Hermes PM, lifecycle engine, sync jobs |
| Webhook ingress / fan-out | `webhooks/` | Bloodbank, provider sync adapters |
| Event observability | `observability/` | Candybar, Holocene, operators |
| MCP surface | `mcp/` | `mcp-hub` |

## Design principles

- **One state machine.** `spec/lifecycle.v1.yaml` is the only canonical machine.
  Per-repo differences are limited to provider label maps and tunable guard knobs,
  never a fork of the machine.
- **Bloodbank is the fan-out bus.** Krebs normalizes provider webhooks to
  CloudEvents and publishes them; consumers subscribe, Krebs does not maintain a
  private dispatch graph.
- **Provider-agnostic by interface.** The `tp` adapter speaks five normalized
  bands — `backlog`, `unstarted`, `started`, `in_review`, `completed` — and maps
  those to each provider's native labels.

## Quick links

- `spec/lifecycle.v1.yaml` — canonical ticket lifecycle
- `spec/event-schemas.yaml` — normalized CloudEvents emitted by Krebs
- `adapters/tp/README.md` — ticket provider interface contract
- `webhooks/README.md` — webhook ingress and fan-out
- `mcp/README.md` — MCP domain wrappers
