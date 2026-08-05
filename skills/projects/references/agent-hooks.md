---
pipeline-status:
  - new
---
# Agent Hooks: Hindsight Memory + Bloodbank Events

Every Hermes agent provisioned into a 33god repo is wired for two cross-cutting capabilities
by default: **Hindsight** (persistent memory) and **Bloodbank** (the NATS event bus). Both are
part of provisioning, not bolted on later.

> This file covers the **harness/global** layer (how an agent gets Hindsight recall/retain +
> Bloodbank emit/consume). For the **per-dev, committed fan-out** that ships these same hooks —
> plus skills — to every teammate and every agent CLI (Claude/Codex/Hermes/Kimi) from a repo
> SSOT, see [project-scoped-hooks.md](project-scoped-hooks.md).

## Hindsight memory (recall + retain)

Hindsight is the shared team memory at `https://api.hs.delo.sh` (config `~/.hindsight/config`).
It is wired at the **harness** layer, not per-repo code. The machine-global
hook scripts live together under `~/.agents/hooks/hindsight/`; live agent configs
should point there, not to per-agent or `.old` script folders:

- **Recall (passive):** a `UserPromptSubmit` hook recalls relevant memories before each prompt;
  results arrive in `<hindsight-memory>` tags. Bank resolution:
  `BANK=$(basename "$(git rev-parse --show-toplevel)")`, falling back to `general`
  (`infra` for homelab, `33GOD`/`33god-core` for the platform).
- **Retain (active):** `hindsight memory retain $BANK "<learning>" --context <category>`
  (categories: architecture, conventions, debugging, deployment, dependencies, preferences,
  session-summary, code-edit).
- **Recall on demand:** `hindsight memory recall $BANK "<question>" --budget mid`.

The Hermes runtime scaffold seeds `runtime/memories/{MEMORY.md,USER.md}` as the agent's local
memory surface. For the full API, bank-routing architecture, and reflection, use the
`hindsight` skill — this hub only states that agents are memory-wired by default.

The runtime is also the target of the named Hermes profile symlink
`~/.hermes/profiles/<repo>-<role>`. Hooks and memories remain profile-local in
that runtime repo even though `config.yaml` inherits shared non-secret defaults
from the fleet default profile.

## Bloodbank events (emit + consume)

Bloodbank is the NATS event bus (`BLOODBANK_NATS_HOST`/`PORT`, default `127.0.0.1:4222`;
compose at `~/code/33GOD/bloodbank`). Each agent is both a consumer and a producer.
Machine-global agent lifecycle hooks are normalized through one publisher:

```bash
python3 ~/.agents/hooks/bloodbank/publish.py --client <claude|codex|copilot|hermes> --hook <native-event>
```

Client-specific payload prep belongs in Bloodbank's adapter package
(`services/agent-hooks/clients/<client>.py`), not in separate per-agent publisher
trees. Legacy `claude/publish.py`, `codex/publish.py`, `copilot/publish.py`, and
`hermes/publish.py` are compatibility wrappers only.

**Binding (in `agents/hermes/<role>/role.yaml`):**
```yaml
bloodbank:
  subscribe:
    - "bloodbank.evt.v1.repo.<repo>.>"          # all events for this repo
    - "bloodbank.cmd.v1.agent.<agent_id>.>"     # commands addressed to this agent
  producer: "hermes-agent:<agent_id>"
```

**Consume:** there is intentionally **no per-agent consumer**. Command ingress
is the single fleet-shared `hermes-fleet-bloodbank-gateway.service`, which
subscribes once to `bloodbank.cmd.v1.agent.invocation.start` and routes
`data.target_agent_id` → the agent's Hermes profile via the fleet registry.
`60-bloodbank.sh` is a compatibility checkpoint only — it installs no files or
services. A `bloodbank-consumer.py` or `hermes-<agent>-consumer.service`
sighting is drift (`pj migrate hermes.registry-parity` removes it).

**Emit:** agents publish through the envelope helper. The PM's sentinel pass
emits via `.scripts/sentinel/bin/emit-event.py`; producer identity is
`hermes-agent:<agent_id>`.

**Subject scheme:**
- `bloodbank.evt.v1.repo.<repo>.>` — repo-scoped events.
- `bloodbank.cmd.v1.agent.invocation.start` — the single command subject; the
  target agent travels in `data.target_agent_id`, never in the subject.

Skipping (e.g. local-only provisioning): `SKIP_BLOODBANK=1` makes `60-bloodbank.sh` a no-op.

## Wiring checklist when adding/repairing an agent

1. `role.yaml` has the `bloodbank.subscribe` subjects + `producer` for this `agent_id`/`repo`.
2. `runtime/bloodbank-consumer.py` exists and is fully rendered (no `{{...}}`); re-run
   `./.scripts/60-bloodbank.sh` if not.
3. The live CLI hook config calls `~/.agents/hooks/bloodbank/publish.py --client <agent> --hook ...`;
   run `cd ~/code/33GOD/bloodbank && mise run health:hooks:check` after repair.
4. Hindsight: the harness `UserPromptSubmit` recall hook is active and the bank resolves to the
   repo (verify with `hindsight memory recall $BANK "smoke" --budget low`).
5. Memory surface present: `runtime/memories/MEMORY.md` + `USER.md`.
