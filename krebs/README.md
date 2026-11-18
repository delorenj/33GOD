# Krebs

The one ticket lifecycle every 33GOD board follows, and `krebs tick`, the small state manager that enforces it.

- **Spec:** [`spec/lifecycle.v2.yaml`](spec/lifecycle.v2.yaml) (the rules; it wins any disagreement).
- **Explainer:** [`docs/lifecycle.md`](docs/lifecycle.md).
- **Dispatcher:** [`tick/`](tick/README.md), fired by Candybar every 10 minutes ([`.candybars/krebs-tick.candybar.toml`](.candybars/krebs-tick.candybar.toml)).
- **Agent skill:** [`skills/krebs/SKILL.md`](skills/krebs/SKILL.md) (what an agent on a Krebs board may and may not do).
- **Decisions:** [`docs/adr/`](docs/adr/).

In one paragraph: every board uses Plane's five stock lanes, and lifecycle meaning lives in labels. A ticket entering Todo is triaged; `krebs tick` is the only thing that moves a triaged ticket to In Progress, two slots per scope; the implementation turn hands it back with `lifecycle:review`; Krebs then sends the scope's PM a review turn, and the PM closes it, sends it back to Todo, or asks a person. Hold labels (`lifecycle:needs-input`, `lifecycle:blocked`, `agent:failed`, and the owner's own `lifecycle:human`) take a ticket out of the flow. A ticket nobody is working on (Candystore shows no live turn) never keeps a slot or `agent:working`.

```bash
mise run tick:dry      # read-only plan, every scope
mise run test          # node:test, fakes only
```

No dependencies and no install step: Node 24, Pilot's Plane client (`../pilot/src`) and the bloodbank n8n package's built `dist/` (`../bloodbank/integrations/n8n-nodes-bloodbank`).

## Layout

| Path | What |
|---|---|
| `tick/` | `krebs tick`: repairs, orphans, slots, dispatch, triage catch-up, review turns |
| `bin/krebs.mjs` | the CLI entry |
| `adapters/tp/` | the `tp` ticket-provider shell adapter (vendored into the Hermes agent template) |
| `skills/krebs/` | the agent skill and `record-decision.py` |
| `spec/`, `docs/` | the lifecycle spec, its explainer, ADRs |

The Python managed-execution engine (`src/krebs`, Postgres schema `krebs`, `bloodbank.cmd.lifecycle.task.invoke`) and the v1 nine-phase spec were deleted on 2026-11-18. Neither was in use. `git log -- src spec/lifecycle.v1.yaml` has them.
