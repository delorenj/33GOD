# 33GOD productized development environment PRD

Status: Draft handoff
Owner: 33GOD Director
Last updated: July 10, 2026

## Summary

33GOD is a private, local-first, cloud-ready development environment made from
multiple active repositories that already behave like one pipeline. The current
problem is coordination: Bloodbank, Candystore, Holocene, PJangler, Hermes
Fleet, Skillex, Hindsight, Pipeline MCP Hub, and related tools change
independently, but their contracts affect one another.

The goal is to productize these pieces into one cohesive platform that a
developer can run locally with `docker compose up` and eventually deploy as a
hosted subscription service. The new `33god-platform/` directory is the first
control-plane slice for that product: it indexes components, records
cross-component changes, defines backfill checks, and starts the path toward a
single compose stack.

## Situation

The 33GOD system grew organically across several repos and host-level config
locations. That was useful while discovering the shape of the pipeline, but it
now creates avoidable maintenance load. A change to agent hooks, Hermes runtime
profiles, event schemas, project templates, or skill routing can quietly break
another component.

Several examples drove this PRD:

- Hindsight memory hooks migrated toward a canonical shared folder, but some
  agent configs still referenced old script paths.
- Bloodbank hook publishing had per-agent drift instead of one canonical
  publisher entrypoint with client-specific adapters.
- Hermes PM runtimes were tracked or submoduled inside project repos even
  though runtimes are mutable operational state.
- Bloodbank, Candystore, and Holocene needed a coordinated baseline before
  moving services into a product stack.
- Existing docs in the repo are stale in places. The current source of truth
  must be live files, validation output, and explicit platform manifests.

## Product vision

33GOD becomes a productized development environment for agentic software
delivery.

The local product gives one operator the whole pipeline on a laptop:

- Event backbone and schemas.
- Durable event history and audit trail.
- Mission-control dashboard.
- Project and agent provisioning.
- Managed long-running PM and worker agents.
- Shared skill hub and memory hooks.
- Unified Bloodbank and Hindsight hook entrypoints.
- Runtime state mounted outside source repos.
- Backups for mutable agent/runtime state.

The hosted product uses the same component graph with stronger auth, tenant
boundaries, managed storage, cloud secrets, and subscription packaging.

## Current control-plane state

`33god-platform/` now exists as the product control-plane directory. It is not
the full compose stack yet. It is a local-first registry and coordination layer.

Current artifacts include:

- `33god-platform/components.yaml`: product profiles, component manifest list,
  contract paths, and change policy.
- `33god-platform/components/*.yaml`: per-component manifests.
- `33god-platform/CHANGELOG.pipeline.md`: human-readable ecosystem changelog.
- `33god-platform/changes/*.jsonl`: machine-readable cross-component change log.
- `33god-platform/backfills/*.yaml`: read-only drift and legacy migration
  manifests.
- `33god-platform/docs/product-map.md`: product card map for the future platform.
- `33god-platform/docs/backfills.md`: backfill program overview.
- `33god-platform/skills/33god-hub/`: unified skill entrypoint for agents.
- `33god-platform/compose.yaml`: thin product-level compose wrapper.
- Root `mise.toml` tasks:
  - `platform:validate`
  - `platform:components`
  - `platform:backfills:check`

Validation state as of this handoff:

- `python3 33god-platform/scripts/platform.py validate`: passes.
- `python3 33god-platform/scripts/platform.py components list`: passes.
- `python3 33god-platform/scripts/platform.py backfills check`: passes.
- `docker compose -f 33god-platform/compose.yaml --profile tools config`:
  passes.

The registry drift found during the PRD handoff is repaired. The
incomplete Flume manifest was removed until its repo path and platform contract
are real.

## Baseline status

The platform baseline checkpoint used for this handoff is
`platform-baseline-2026-07-08`.

| Component  | Status    | Baseline                         | Runtime mode        | Notes                                                                                                                                                                         |
| ---------- | --------- | -------------------------------- | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bloodbank  | GO/YELLOW | Local annotated tag at `1d4fcbc` | `IGNORE_ALL_YELLOW` | `mise run doctor`, `mise run smoketest:schemas`, and `git diff --check` passed. Tag is local-only. PM runtime remains tracked as a submodule with `.gitmodules ignore = all`. |
| Candystore | GO        | Remote tag peels to `48e05c3`    | `DELINKED_GREEN`    | Runtime is delinked from Git. Remote tag exists. Existing `pjangler audit` exception is scoped to `hermes.pm-scaffold`.                                                       |
| Holocene   | GO/YELLOW | Local annotated tag at `800a604` | `IGNORE_ALL_YELLOW` | Focused runtime-drift verification only, not full suite green. PM runtime remains tracked as a submodule with `.gitmodules ignore = all`. Tag is local-only.                  |

The baseline is good enough to proceed with platform-stack planning, but it is
not a clean release train yet. Bloodbank and Holocene still need runtime
delinking or an explicit migration plan from tracked runtime submodules to
mounted runtime volumes.

## Goals

The product must make the whole 33GOD pipeline feel like one maintained system.

1. Provide one local compose entrypoint for the platform.
2. Keep implementation ownership in component repos while centralizing platform
   contracts in `33god-platform/`.
3. Normalize agent memory and event hooks across agent clients.
4. Move agent runtimes out of tracked source repos and into mounted volumes.
5. Back up mutable runtime state with `forever-ago`.
6. Make cross-component changes visible through a pipeline changelog.
7. Give agents one skill hub for 33GOD routing and reference lookup.
8. Preserve a path to hosted, private, subscription-based deployment.

## Non-goals

This PRD does not require collapsing every repo into one monorepo. Separate repos
can remain while the product control plane coordinates their contracts.

This PRD does not require open sourcing the platform. The target is private
source with optional hosted subscription access.

This PRD does not require replacing every legacy workflow in the first slice.
Legacy projects can be backfilled in stages.

## Functional requirements

### FR1. Platform component registry

`33god-platform/` must maintain a machine-readable registry of all product
components, their repo paths, compose files, health checks, ownership, public
product card, source-of-truth files, and backfill obligations.

Acceptance criteria:

- `platform:validate` fails when a referenced component manifest is missing.
- `platform:components` lists every registered component and repo presence.
- Component manifests use stable IDs and explicit source-of-truth paths.
- The registry distinguishes active product components from deprecated or
  legacy components.

### FR2. Cross-component changelog

The platform must record changes that affect multiple components in both human
and machine-readable forms.

Acceptance criteria:

- Any event schema, hook entrypoint, project template, Hermes runtime contract,
  skill routing, compose boundary, port, secret, or storage change creates a
  `changes/*.jsonl` entry.
- `CHANGELOG.pipeline.md` summarizes those changes for human handoff.
- Each change names affected components and required backfills.

### FR3. Unified compose stack

The product must provide a single compose stack with profiles for local,
full-workstation, and cloud deployment shapes.

Acceptance criteria:

- `docker compose -f 33god-platform/compose.yaml --profile tools config` stays
  green.
- The stack evolves from the current thin wrapper into service definitions or
  includes for Bloodbank, Candystore, Holocene, and required infrastructure.
- Profiles match the control-plane definitions:
  - `default`: core, audit, control, and skills.
  - `full`: default plus provisioning, agents, integrations, and optional
    surfaces.
  - `cloud`: full deployment shape without local-only assumptions.

### FR4. Runtime state isolation

Agent runtimes must not be tracked as project source. Runtime state must live in
mounted or named volumes.

Acceptance criteria:

- New agent runtimes are provisioned outside tracked project source by default.
- Existing tracked Hermes PM runtimes are migrated or explicitly marked as
  temporary `IGNORE_ALL_YELLOW` state.
- Source repos remain clean when agents run, checkpoint, or update runtime
  state.
- Runtime volume paths are documented in the platform manifest or deployment
  docs.

### FR5. Runtime backup strategy

Mutable agent and runtime volumes must be backed up through `forever-ago`.

Acceptance criteria:

- Runtime backups support a tiered retention policy:
  - nightly, keep 3;
  - weekly, keep 2;
  - monthly, keep 2.
- Retention values are configurable.
- Backup jobs are safe to run repeatedly.
- Restore instructions exist before runtime delinking is applied broadly.

### FR6. Canonical Hindsight hooks

Hindsight memory flow must be normalized across all agents.

Acceptance criteria:

- There is one canonical Hindsight hook directory.
- Recall, retain, summary, journal, and related entrypoints are one script per
  action.
- Agent configs invoke the same canonical scripts regardless of whether the
  client stores config in TOML, JSON, shell hooks, or another format.
- Legacy references to `hindsight.old` are detected by a backfill check and
  removed.

### FR7. Canonical Bloodbank agent publisher

Agent lifecycle events must use one canonical Bloodbank publisher.

Acceptance criteria:

- Agent clients call `~/.agents/hooks/bloodbank/publish.py --client <client>
--hook <native-hook>`.
- Client-specific payload preparation lives behind the publisher, not in
  separate per-agent publisher scripts.
- Hook failures fail open and never block the host agent.
- Bloodbank schemas remain the source of truth for event envelopes.

### FR8. Event backbone and audit trail

Bloodbank and Candystore must form the core event spine.

Acceptance criteria:

- All inter-service communication flows through Bloodbank.
- Candystore persists event history for query, replay, and summaries.
- Direct service-to-service calls are treated as integration debt.
- Schema validation and subject naming checks are part of the platform gate.

### FR9. Mission control

Holocene must become the operator-facing control plane for platform health.

Acceptance criteria:

- Holocene surfaces component health, hook health, agent/fleet status, and
  platform-stack readiness.
- It distinguishes focused verification from full-suite green.
- It can display baseline status across Bloodbank, Candystore, Holocene, and
  future components.

### FR10. Unified skill hub

Agents must start from one 33GOD skill hub before drilling into component
skills.

Acceptance criteria:

- `33god-platform/skills/33god-hub/` routes agents to component references.
- Skillex remains the durable source for distributed skill packages.
- The hub names source-of-truth boundaries, especially project registry,
  Bloodbank events, Hermes fleet state, and agent hook fan-out.

### FR11. Backfill program

Legacy projects and configs must be brought forward through explicit,
idempotent backfills.

Acceptance criteria:

- Backfill manifests declare search paths, forbidden patterns, owner component,
  summary, and remediation notes.
- Initial backfills remain read-only until each remediation is reversible and
  safe.
- A future `backfills apply <id>` flow must be gated and auditable.

### FR12. Hosted product path

The local platform must leave a clear path to a hosted subscription product.

Acceptance criteria:

- Component manifests contain product-card language that can feed a teaser or
  subscriber-facing landing page.
- Cloud deployment has explicit auth, tenant, storage, secret, and backup
  requirements.
- Local-only assumptions are isolated from cloud profiles.

## Non-functional requirements

- **Private source:** The platform is not designed as open source by default.
- **Local-first:** The laptop deployment must work before cloud deployment.
- **Cloud-ready:** The component graph must map cleanly to managed cloud
  storage, network, auth, and secrets.
- **Idempotent operations:** Backfills, validation, setup, and backups must be
  safe to rerun.
- **Fail-open hooks:** Agent hooks must not break interactive agent sessions.
- **Source-of-truth clarity:** The platform must name whether a file is source
  of truth or projection before agents change it.
- **No hidden runtime dirt:** Agent runtime mutations must not dirty source
  repos.
- **Observable gates:** Validation output must be concrete enough for agents to
  route follow-up work.

## Open issues

These issues are the first things the director must triage.

1. Decide whether Flume belongs in the active product registry.
   Add it only after the repo exists and the manifest has real health,
   source-of-truth, and changelog fields.

2. Decide whether Candybar, Holyfields, and Hookd are active product cards,
   legacy components, or replaced capabilities.

3. Migrate Bloodbank and Holocene PM runtimes from `IGNORE_ALL_YELLOW` to
   `DELINKED_GREEN`.

4. Define the `forever-ago` backup wrapper or enhancement for tiered retention.

5. Convert `33god-platform/compose.yaml` from a thin scaffold into a real stack
   plan.

6. Reconcile root repo dirt before treating `33GOD` itself as a release branch.

## MVP plan

### Phase 1. Repair the control plane

Keep the current registry valid and trustworthy as components move.

- Maintain `platform:validate`, `platform:components`, and
  `platform:backfills:check` as passing gates.
- Decide active versus legacy component status for Candybar, Holyfields, Hookd,
  and any future Flume manifest.
- Record each registry change in `CHANGELOG.pipeline.md` and `changes/*.jsonl`.

### Phase 2. Normalize runtime and hooks

Remove the biggest sources of daily drift.

- Finish canonical Hindsight hook fan-out.
- Finish canonical Bloodbank publisher fan-out.
- Move Hermes PM runtimes into mounted volumes.
- Add runtime backup and restore docs.

### Phase 3. Build the local compose stack

Turn the control plane into a usable local product.

- Compose Bloodbank, Candystore, Holocene, and required infrastructure.
- Mount config and runtime volumes explicitly.
- Add health gates and smoke-test tasks.
- Make one command bring up the useful local baseline.

### Phase 4. Add director-grade operations

Make the platform operable by agents and humans.

- Promote pipeline changelog use into the default change workflow.
- Add baseline ledger generation.
- Surface stack health in Holocene.
- Create backfill apply flows only after dry-run checks are reliable.

### Phase 5. Prepare hosted deployment

Package the same graph for cloud deployment.

- Define tenant, auth, billing, storage, and backup boundaries.
- Add deployment profiles and cloud secret handling.
- Convert product cards into landing-page-ready capability descriptions.

## Director handoff

The director must treat `33god-platform/` as the coordination surface and the
component repos as implementation owners. Do not let a component-local fix hide
cross-component contract changes. If a change affects event schemas, hook
entrypoints, runtime state, project templates, skills, compose, ports, secrets,
or storage, it belongs in the platform changelog and may require a backfill.

The immediate recommendation is to move to runtime delinking and backup
strategy, then expand `compose.yaml` into the real local stack. Keep the
platform registry green before and after each step.
