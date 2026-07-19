---
name: 33god-ecosystem
description: |
  Router / skill-set hub for the 33GOD / DeLoNET project platform. Routes user intent to the right member skill: project bootstrap (33god-projects), pjangler implementation (project-jangler), agent hook/skill fan-out (agent-config-fanout), Hermes fleet operations (agent-fleet-operations), Plane ticket/work-item and board/lane operations (project-lifecycle, never Lifecycle authority), Bloodbank contracts and transport (bloodbank-integration), host conventions (delonet-conventions), versioning (mise-versioning), task authoring (mise-tasks), and memory (hindsight). Use when the request spans multiple 33GOD components or when you are unsure which member skill owns a 33GOD task. Triggers: 33god, 33GOD, DeLoNET, project platform, pjangler, CommonProject, Hermes, Plane, Lifecycle, Bloodbank, agent hooks, skill fan-out, fleet, project bootstrap. Does NOT implement procedures; it loads the member skill that does.
---

# 33GOD Ecosystem

Thin router for the 33GOD / DeLoNET platform. Load this skill when a request touches multiple platform components or when you need to pick the right member skill.

## Operating Principles

- **The project registry is authoritative for project identity and bootstrap metadata only.** Plane and Hermes are downstream integrations; the registry does not own operational Lifecycle truth.
- **`.project.json` is a repo-local projection.** It is authored by `33god-projects`, not by Plane or Hermes.
- **The standalone Lifecycle component is the sole deterministic 33GOD lifecycle authority.** It owns specification/status, state versions, legal transitions and guards, modes, frontier, obligations/blockers/gates/capabilities, reconciliation, and every lifecycle state write.
- **Plane owns ticket/work-item records and board/lane state only.** It does not evaluate or write deterministic Lifecycle truth.
- **`project-lifecycle` routes only Plane ticket/work-item and board/lane mutations.** It never routes deterministic Lifecycle authority evaluation or writes.
- **Momo chooses and executes legal work and publishes evidence.** It does not determine Lifecycle truth or write lifecycle state.
- **Holocene renders authoritative Lifecycle data and invokes high-level actions.** It is not the engine or source of truth and does not persist Lifecycle truth.
- **Bloodbank owns canonical inter-service contracts and NATS/Dapr transport.** No other skill mints event names, and agent CLIs invoke one canonical Bloodbank publisher.
- **Candystore owns append-only audit history and Lifecycle read projections.** It never owns operational Lifecycle writes.
- **Hermes fleet operations stay in `agent-fleet-operations`.** CommonProject does not repair the fleet.
- **Hub bodies route; they do not implement.** Long recipes and command snippets live in member skills.

## Routing Matrix

| User intent | Primary skill | Optional secondary |
|---|---|---|
| Create a new 33GOD project / bootstrap CommonProject / add a PM or Ticket Sentinel | `33god-projects` | `agent-fleet-operations` only for live agent provisioning details; `project-lifecycle` only for Plane ticket/work-item and board/lane mutations |
| Change CommonProject template or pjangler CLI/MCP | `project-jangler` | `33god-projects` for project-facing contract |
| Add a PM or scrum-master agent to this repo | `33god-projects` | `agent-fleet-operations` for runtime/template/systemd details |
| Update Hermes model/profile/default config or fleet self-check | `agent-fleet-operations` | `33god-projects` only if repo projection changes |
| Fix inherited Hermes config after upstream update | `agent-fleet-operations` | none unless repo-local agent projections changed |
| Create or move Plane ticket/work-item records or board/lane state | `project-lifecycle` (Plane mutations only) | `33god-projects` to resolve project binding from `.project.json` |
| Define an event or debug missing envelopes | `bloodbank-integration` | `agent-config-fanout` only if an agent hook projection is broken |
| Change project-scoped hook generation | `agent-config-fanout` | `33god-projects` if CommonProject baseline changes; `bloodbank-integration` if event emission changes |
| Change zsh, Traefik, Tailscale, Docker stack convention | `delonet-conventions` | project skills only if repo scaffold must change |
| Bump version and release | `mise-versioning` | `mise-tasks` only if release task DAG must change |
| Author or debug mise tasks | `mise-tasks` | `delonet-conventions` only for host-level env conventions |
| Hindsight memory operations | `hindsight` | `33god-projects` for wiring during bootstrap only |

## Source-of-Truth Map

| Domain | Owner skill | Durable source |
|---|---|---|
| Project registry / repo bootstrap | `33god-projects` | `~/.config/pjangler/projects.yaml` or `PJ_PROJECT_REGISTRY`; `templates/commonproject`; repo `.project.json` |
| PJangler code | `project-jangler` | `/home/delorenj/code/pjangler/src`, `templates/commonproject` |
| Agent hook/skill fan-out | `agent-config-fanout` | Bloodbank global: `~/code/33GOD/bloodbank/services/agent-hooks/hooks.master.json`; project-scoped: `.agents/hooks/hooks.master.json`, lock files |
| Hermes fleet runtime | `agent-fleet-operations` | `~/.hermes/fleet.env`, `~/.hermes/config.yaml`, `~/.hermes/agents-registry.yaml`, `hermes-agent-template` |
| Plane ticket/work-item and board/lane records | `project-lifecycle` (Plane mutations only) | Plane API / board state; never Lifecycle authority state |
| Event contract + agent event publisher | `bloodbank-integration` | Bloodbank `docs/event-naming.md`, `schemas/`, `services/agent-hooks/publish.py` |
| Host conventions | `delonet-conventions` | home layout, zshyzsh, Docker/Traefik/Tailscale conventions |
| Version workflow | `mise-versioning` | repo `mise.toml`, release tasks |
| Task authoring | `mise-tasks` | repo `mise.toml` `[tasks]` |
| Memory operations | `hindsight` | Hindsight memory banks |

## Common Combinations

**Project bootstrap:** `33god-projects` → `project-lifecycle` (only for Plane ticket/work-item and board/lane mutations) → `agent-fleet-operations` (only for live agent provisioning).

**PJangler implementation:** `project-jangler` → `33god-projects` for expected project-facing contract.

**Agent hook / skill fan-out:** `agent-config-fanout` → `33god-projects` for CommonProject baseline → `bloodbank-integration` if hook events are emitted.

**Hermes fleet maintenance:** `agent-fleet-operations` → `project-lifecycle` only for creating/closing Plane maintenance tickets or moving their board/lane state → `33god-projects` only if `.project.json` or registry projections change.

**Event system work:** `bloodbank-integration` → `agent-config-fanout` for `hooks.master.json` projection/install mechanics. Runtime agent hooks use the single canonical publisher at `~/.agents/hooks/bloodbank/publish.py --client <agent> --hook <event>`.

## Out of Scope

- **Implementation procedures** → member skills.
- **Plane API details for ticket/work-item and board/lane mutations** → `project-lifecycle` (never Lifecycle authority evaluation or writes).
- **Hermes runtime repair steps** → `agent-fleet-operations`.
- **Bloodbank schema authoring details** → `bloodbank-integration`.
- **Generic host/workstation conventions** → `delonet-conventions`.
