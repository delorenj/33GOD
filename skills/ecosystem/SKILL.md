---
name: 33god-ecosystem
description: |
  Router / skill-set hub for the 33GOD / DeLoNET project platform. Routes user intent to the right member skill: incremental monorepo delivery (33god-merge-forward), project bootstrap (33god-projects), pjangler implementation (project-jangler), agent hook/skill fan-out (agent-config-fanout), Hermes fleet operations (agent-fleet-operations), Plane ticket operations (project-lifecycle), Bloodbank events (bloodbank-integration), host conventions (delonet-conventions), versioning (mise-versioning), task authoring (mise-tasks), and memory (hindsight). Use when the request spans multiple 33GOD components or when you are unsure which member skill owns a 33GOD task. Triggers: 33god, 33GOD, DeLoNET, monorepo integration, Docker Compose, component pin, merge to main, project platform, pjangler, CommonProject, Hermes, Plane, Bloodbank, agent hooks, skill fan-out, fleet, project bootstrap. Does NOT implement procedures; it loads the member skill that does.
---

# 33GOD Ecosystem

Thin router for the 33GOD / DeLoNET platform. Load this skill when a request touches multiple platform components or when you need to pick the right member skill.

## Operating Principles

- **The project registry is the project source of truth.** Plane and Hermes are downstream integrations.
- **`.project.json` is a repo-local projection.** It is authored by `33god-projects`, not by Plane or Hermes.
- **Bloodbank owns event schemas and agent event publishing.** No other skill mints event names, and agent CLIs invoke one canonical Bloodbank publisher.
- **Hermes fleet operations stay in `agent-fleet-operations`.** CommonProject does not repair the fleet.
- **Hub bodies route; they do not implement.** Long recipes and command snippets live in member skills.

## Routing Matrix

| User intent | Primary skill | Optional secondary |
|---|---|---|
| Deliver a cross-component slice, add a component to root Compose, advance source/image pins, or keep integration branches short-lived | `33god-merge-forward` | Relevant domain skill for the component contract |
| Create a new 33GOD project / bootstrap CommonProject / add a PM or Ticket Sentinel | `33god-projects` | `agent-fleet-operations` only for live agent provisioning details; `project-lifecycle` only for live board actions |
| Change CommonProject template or pjangler CLI/MCP | `project-jangler` | `33god-projects` for project-facing contract |
| Add a PM or scrum-master agent to this repo | `33god-projects` | `agent-fleet-operations` for runtime/template/systemd details |
| Update Hermes model/profile/default config or fleet self-check | `agent-fleet-operations` | `33god-projects` only if repo projection changes |
| Fix inherited Hermes config after upstream update | `agent-fleet-operations` | none unless repo-local agent projections changed |
| Create or move Plane tickets | `project-lifecycle` | `33god-projects` to resolve project binding from `.project.json` |
| Define an event or debug missing envelopes | `bloodbank-integration` | `agent-config-fanout` only if an agent hook projection is broken |
| Change project-scoped hook generation | `agent-config-fanout` | `33god-projects` if CommonProject baseline changes; `bloodbank-integration` if event emission changes |
| Change zsh, Traefik, Tailscale, Docker stack convention | `delonet-conventions` | project skills only if repo scaffold must change |
| Bump version and release | `mise-versioning` | `mise-tasks` only if release task DAG must change |
| Author or debug mise tasks | `mise-tasks` | `delonet-conventions` only for host-level env conventions |
| Hindsight memory operations | `hindsight` | `33god-projects` for wiring during bootstrap only |

## Source-of-Truth Map

| Domain | Owner skill | Durable source |
|---|---|---|
| Incremental monorepo delivery / Compose integration | `33god-merge-forward` | component `main`; root `main`; root exact pins/digests; root `tasks.md` |
| Project registry / repo bootstrap | `33god-projects` | `~/.config/pjangler/projects.yaml` or `PJ_PROJECT_REGISTRY`; `templates/commonproject`; repo `.project.json` |
| PJangler code | `project-jangler` | `/home/delorenj/code/pjangler/src`, `templates/commonproject` |
| Agent hook/skill fan-out | `agent-config-fanout` | Bloodbank global: `~/code/33GOD/bloodbank/services/agent-hooks/hooks.master.json`; project-scoped: `.agents/hooks/hooks.master.json`, lock files |
| Hermes fleet runtime | `agent-fleet-operations` | `~/.hermes/fleet.env`, `~/.hermes/config.yaml`, `~/.hermes/agents-registry.yaml`, `hermes-agent-template` |
| Ticket lifecycle | `project-lifecycle` | Plane API / board state |
| Event contract + agent event publisher | `bloodbank-integration` | Bloodbank `docs/event-naming.md`, `schemas/`, `services/agent-hooks/publish.py` |
| Host conventions | `delonet-conventions` | home layout, zshyzsh, Docker/Traefik/Tailscale conventions |
| Version workflow | `mise-versioning` | repo `mise.toml`, release tasks |
| Task authoring | `mise-tasks` | repo `mise.toml` `[tasks]` |
| Memory operations | `hindsight` | Hindsight memory banks |

## Common Combinations

**Monorepo delivery:** `33god-merge-forward` → the relevant component domain skill for contract details. Merge the component to its `main`, then immediately advance and merge root `main` before selecting another slice.

**Project bootstrap:** `33god-projects` → `project-lifecycle` (only for live board work) → `agent-fleet-operations` (only for live agent provisioning).

**PJangler implementation:** `project-jangler` → `33god-projects` for expected project-facing contract.

**Agent hook / skill fan-out:** `agent-config-fanout` → `33god-projects` for CommonProject baseline → `bloodbank-integration` if hook events are emitted.

**Hermes fleet maintenance:** `agent-fleet-operations` → `project-lifecycle` only if creating/closing maintenance tickets → `33god-projects` only if `.project.json` or registry projections change.

**Event system work:** `bloodbank-integration` → `agent-config-fanout` for `hooks.master.json` projection/install mechanics. Runtime agent hooks use the single canonical publisher at `~/.agents/hooks/bloodbank/publish.py --client <agent> --hook <event>`.

## Out of Scope

- **Implementation procedures** → member skills.
- **Plane API details** → `project-lifecycle`.
- **Hermes runtime repair steps** → `agent-fleet-operations`.
- **Bloodbank schema authoring details** → `bloodbank-integration`.
- **Generic host/workstation conventions** → `delonet-conventions`.
