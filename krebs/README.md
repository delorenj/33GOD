# Krebs

The ticket-lifecycle and task-platform engine for 33GOD.

Krebs owns the canonical state machine that drives work from intake to done, the
ticket-provider abstraction that lets that machine talk to Plane, Linear, Trello,
or any future tracker, and the webhook fan-out layer that turns provider events
into normalized Bloodbank events for downstream observability and synchronization.

## Managed execution v2

The implemented Plane execution authority is `src/krebs/`: durable attempts,
leases, fencing, authenticated commands, provider intents, reconciliation and
an event outbox. Pilot owns the Plane API adapter; Momo is the shared PM
playbook; Hermes/systemd supervise runs; PJangler owns canonical bindings.

`spec/lifecycle.v1.yaml` and the interfaces below describe the earlier lifecycle
surface. They do not override the managed v2 command and lane contract.

- [Execution contract](docs/execution-contract.md)
- [Rollout evidence and enrollment blockers](docs/rollout-evidence.md)
- [Activation runbook](docs/activation.md)
- Required integration gate: `python ops/test.py` (Docker, user systemd and uv).
- Immutable host installation: `python ops/install.py RELEASE.json --destination RELEASE_DIR`.
  Installation does not enable or start the service; readiness must pass first.
- Project-health remains separately packaged under `src/krebs/project_health/`.

## Earlier lifecycle interfaces

| Concern | Owner in Krebs | Consumed by |
|---|---|---|
| Lifecycle state machine | `spec/lifecycle.v1.yaml` | Momo, Hermes PM, MCP hub, Holocene |
| Provider abstraction | `adapters/tp/` | Momo, Hermes PM, lifecycle engine, sync jobs |
| Webhook ingress / fan-out | `webhooks/` | Bloodbank, provider sync adapters |
| Event observability | `observability/` | Candybar, Holocene, operators |
| MCP surface | `mcp/` | `mcp-hub` |

## Design principles

- **One authority per mode.** Managed v2 is enforced by `src/krebs/contract.py`;
  `spec/lifecycle.v1.yaml` documents the earlier interface.
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
