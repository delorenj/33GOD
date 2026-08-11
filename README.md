# 33GOD

**An Event-Driven, Agentic Development Pipeline**

33GOD is a platform for orchestrating software development, knowledge
management, and automated workflows through multi-agent teams. Built on an
event-driven architecture, it lets AI agents and microservices collaborate
asynchronously across multiple projects simultaneously.

> _Everything is an event._ All significant state changes — Git commits, PRs,
> transcripts, agent decisions, ticket transitions, meetings — are emitted as
> events, allowing autonomous agents to coordinate seamlessly.

> **Product control plane:** the productized-platform map lives in
> [`33god-platform/`](33god-platform/). Its component manifests, pipeline
> changelog, and backfill checks are the source of truth. Prefer them, and
> [`PRD.md`](PRD.md), over prose anywhere else in the tree.

---

## Components

Thirteen components are registered in
[`33god-platform/components.yaml`](33god-platform/components.yaml). Not every
component is a service — runtime mode is part of each component's contract, and
specs, templates, CLIs, and agent bundles are first-class.

### Core pipeline

| Component                     | Runtime mode              | Description                                                                                                                                             |
| ----------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **[Bloodbank](bloodbank/)**   | Compose service           | Central event bus on **NATS JetStream** with Dapr placement. Owns event schemas, subject naming, and the canonical agent-hook publisher.                 |
| **[Candystore](candystore/)** | Compose service           | Event Store Manager. Persists every Bloodbank event to PostgreSQL for audit, query, and replay.                                                          |
| **[Holocene](holocene/)**     | Compose web + host API    | Mission control. Component health, hook health, agent/fleet status, and platform-stack readiness. The API runs as host systemd by design.                |
| **[Krebs](krebs/)**           | Spec + adapters           | The ticket-lifecycle engine. Owns the **one** canonical state machine, the provider abstraction over Plane/Linear/Trello, and webhook normalization.     |

### Provisioning & orchestration

| Component                                       | Runtime mode             | Description                                                                                                                                     |
| ----------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **[PJangler](pjangler/)**                       | run-only CLI + stdio MCP | Deterministic project and fleet provisioning. `pjangler project create` is the canonical way to start a new repo.                               |
| **[Toad](toad/)**                               | CLI + stdio MCP          | Project Custodian. Creates, adopts, audits, and migrates projects by composing PJangler. Dry-run by default; live actions need `TOAD_ALLOW_LIVE=1`. |
| **[Momo](momo/)**                               | Agent skill              | PM/EM orchestrator. Holds roadmap and next action, delegates every code change. The interactive twin of the autonomous Hermes PM.                |
| **[Hermes Agent Template](hermes-agent-template/)** | Template + host systemd | Versioned agent-generation contract, runtime configuration, fleet reconciliation, and host survival services.                                    |

### Integrations & surfaces

| Component                     | Runtime mode         | Description                                                                                                                          |
| ----------------------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **[Pipeline MCP Hub](mcp-hub/)** | Hosted MCP endpoint | Fronts many tool domains behind three tools (`list_domains`, `list_domain_tools`, `call_domain_tool`) so agents aren't flooded with schemas. Served at `https://mcp.delo.sh/mcp`. |
| **[Candybar](candybar/)**     | Optional desktop/web | Service registry hub and topology visualization. Real-time service health, event flows, and system architecture.                      |
| **Skillex** (`~/code/skillex`) | External registry   | Skill registry and distribution — one source of truth for skills across the stack.                                                   |
| **Hindsight** (`~/.agents`)   | External service     | Persistent agent memory. Recall, retain, reflect, with per-project banks. API at `https://api.hs.delo.sh`.                            |
| **HeyMa** (`~/code/HeyMa`)    | Optional service     | Voice interface. WhisperLiveKit transcription plus ElevenLabs text-to-speech, with Chrome extension support.                          |

Skillex, Hindsight, and HeyMa live outside this checkout; their manifests point
at their real paths and `platform:components` reports presence.

---

## Quick start

```bash
# Validate the control plane
mise run platform:validate
mise run platform:components
mise run platform:backfills:check

# Render and check the local Compose target
mise run platform:compose:validate

# Bring up the local stack
docker compose -f 33god-platform/compose.yaml up -d
```

The `cloud` profile is **render-only**. It exists to document an unsupported
deployment shape and carries an explicit rejection gate — never `docker compose
up` with it.

---

## Repository layout

This is a monorepo of submodules plus root-owned coordination.

```
33god-platform/   Control plane: manifests, compose projection, gates, changelog
krebs/            Ticket-lifecycle spec, adapters, webhooks (tracked in-tree)
skills/           Symlinks to component-owned skills — not a source of truth
agents/hermes/    Hermes agent role profiles (runtime state is never tracked)
docs/             Per-component architecture, contracts, and inventory docs
_bmad/            BMAD method config; _bmad-output/ holds planning artifacts
<component>/      Independently versioned submodules
```

`AGENTS.md` symlinks to the architecture decision document at
`_bmad-output/planning-artifacts/architecture.md`; `CLAUDE.md` and `GEMINI.md`
chain to `AGENTS.md`.

### Skills are component-owned

Each skill lives with the component whose contract it describes, so a contract
change and its skill update land in the same commit:

| Skills                                                          | Owner                |
| --------------------------------------------------------------- | -------------------- |
| `bloodbank-integration`, `bloodbank-sdk-generation`             | `bloodbank/skills/`  |
| `agent-fleet-operations`, `mise-*`, `pjangler-*`, `projects`    | `pjangler/skills/`   |
| `project-lifecycle`, `task-triage`                              | `krebs/skills/`      |
| `33god-hub`, `merge-forward`, `skillex-skill-registry`          | `33god-platform/skills/` |

Root `skills/` holds only links to those owners. Never edit through a link
expecting the owner to follow.

---

## Working here

- **Trunk discipline.** Merge or rebase back to `main` optimistically. Do not
  leave work in a worktree or a long-lived branch.
- **Pins at tip.** Every submodule pin should equal that submodule's
  `origin/main` tip at checkpoint time.
- **Runtime is never source.** Agent runtime state lives outside tracked source.
  Do not add a tracked runtime submodule.
- **One lifecycle machine.** Consume `krebs/spec/lifecycle.v1.yaml` by pointer.
  Per-repo differences are label maps, never a forked machine.
- **Secrets.** `.env` is materialized by `op inject` from the committed
  `.env.op` reference file and is never tracked.

Cross-component changes — event schemas, hook entrypoints, runtime contracts,
project templates, the lifecycle machine, skill ownership, compose boundaries,
ports, secrets, or storage — belong in
[`33god-platform/CHANGELOG.pipeline.md`](33god-platform/CHANGELOG.pipeline.md)
and may require a backfill.
