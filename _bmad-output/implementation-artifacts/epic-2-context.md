# Epic 2 Context: Repo-Independent Named Specialist Workforce

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Establish the architecture and tooling to define, house, and invoke portable named agents bound by Role/Job Description with traveling Hindsight memory, curated Skillex skills, framework-agnostic harness projections, and Bloodbank event dispatch — establishing our walking skeleton with the inaugural n8n workflow specialist and big-chungus infra specialist.

## Stories

- Story 2.1: Portable Named Agent Contract & Skillex Pack Binding
- Story 2.2: Framework-Agnostic Projection Engine
- Story 2.3: Provision the n8n Workflow Specialist
- Story 2.4: Provision the Big Chungus Infrastructure Specialist
- Story 2.5: Event-Driven Dispatch & Lifecycle via Bloodbank

## Requirements & Constraints

- Agents are defined by Role and Job Description rather than tied to a single repository checkout.
- Agent skills are curated via reference-only Skillex packs/sets, preserving canonical skill sources in `~/code/skillex/all-skills/` without copying payloads.
- Personal Hindsight memory banks (`agent-<name>`) travel with the agent across all invocation contexts (CLI, daemon, background events).
- Agent definitions must be normalized and framework-agnostic, capable of projecting into Hermes profiles, dynamic CLI harnesses, and headless workers.
- Event-driven invocation uses the shared Bloodbank fleet gateway with routing via canonical `target_agent_id` and CloudEvents lifecycle tracking.

## Technical Decisions

- **Skill Topology:** Follows Skillex ADR-0001 (reference-only packs in `~/code/skillex/packs/` and sets in `~/code/skillex/sets/`). The agent's desk directory provides compiled `.agents/skills` symlinks.
- **Agent Desks:** Canonical desk location at `~/.agents/workforce/<name>/` housing the agent's charter, runtime configuration, and skill links.
- **Memory Layering:** Hindsight `write_bank: agent-<name>` and recall configuration configured per specialist.
- **Command & Event Bus:** Commands dispatched to `bloodbank.cmd.agent.invocation.start` with `data.target_agent_id`. Ingress handled by fleet gateway emitting `bloodbank.agent.invocation.started|completed|failed`.

## Cross-Story Dependencies

- Story 2.1 establishes the contract and desk structure that Story 2.2 projects into harnesses.
- Stories 2.3 and 2.4 instantiate the first concrete specialists using the contracts from 2.1 and 2.2.
- Story 2.5 validates end-to-end event-driven invocation of the provisioned specialists.
