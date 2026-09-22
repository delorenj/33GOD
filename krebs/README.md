# Krebs

The ticket-lifecycle and task-platform engine for 33GOD.

Krebs owns the canonical state machine that drives work from intake to done and,
in managed v2, the execution authority that turns agent command intents into
provider mutations through Pilot. It does not ingest provider webhooks: the
n8n `Plane → Bloodbank` workflow (`bloodbank/integrations/n8n-nodes-bloodbank`,
`src/plane.ts`) is the single live normalizer, and Plane's webhook echo of a
Krebs write is the fact (see `webhooks/README.md`).

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
| Webhook ingress | none; n8n `Plane → Bloodbank` owns it (`webhooks/README.md`) | — |
| Event observability | `observability/` | Candybar, Holocene, operators |
| MCP surface | `mcp/` (design note, not implemented) | — |

## Design principles

- **One authority per mode.** Managed v2 is enforced by `src/krebs/contract.py`;
  `spec/lifecycle.v1.yaml` documents the earlier interface.
  Per-repo differences are limited to provider label maps and tunable guard knobs,
  never a fork of the machine.
- **Bloodbank is the fan-out bus.** Krebs consumes
  `bloodbank.cmd.lifecycle.task.invoke` and publishes only lifecycle receipts;
  ticket facts (`repo.task.*`, `repo.board.*`) come from the Plane webhook via
  n8n, never from Krebs or an agent.
- **Provider-agnostic by interface.** The `tp` adapter speaks five normalized
  bands — `backlog`, `unstarted`, `started`, `in_review`, `completed` — and maps
  those to each provider's native labels.

## Quick links

- `spec/lifecycle.v1.yaml` — canonical ticket lifecycle
- `spec/event-schemas.md` — the Bloodbank events Krebs consumes and publishes
- `adapters/tp/README.md` — ticket provider interface contract
- `webhooks/README.md` — where provider webhook facts actually come from
- `mcp/README.md` — MCP domain wrappers
