# 33GOD productized development environment PRD

Status: Integrated local Compose stack live
Owner: 33GOD Director
Last updated: July 18, 2026

## Summary

33GOD is a private, local-first development environment made from
multiple active repositories that already behave like one pipeline. The current
problem is coordination: Bloodbank, Candystore, Holocene, PJangler, Hermes
Fleet, Skillex, Hindsight, Pipeline MCP Hub, and related tools change
independently, but their contracts affect one another.

The goal is to productize these pieces into one cohesive platform with one
governed local deployment entrypoint and, later, a separately designed hosted
subscription service. `33god-platform/` indexes components, records
cross-component changes, defines backfill checks, and owns the live normalized
integrated Compose stack.

The implemented product boundary includes a separate, headless `lifecycle`
component. It is the sole authority for versioned lifecycle
specification, operational state, deterministic reconciliation, legal frontier,
obligations, and capability validation. The local vertical slice uses a
dedicated PostgreSQL authority store, canonical Bloodbank transport, durable
Candystore projections, and bounded Momo/Holocene clients.

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

The target local product gives one operator the whole pipeline on a laptop:

- Event backbone and schemas.
- Durable event history and audit trail.
- Deterministic project lifecycle state and legal-work frontier.
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

`33god-platform/` is the product control-plane directory and root-owned
cross-component projection. Root Compose owns Bloodbank core, the dedicated
Lifecycle authority process/storage topology, the canonical Candystore
deployment, and Holocene web; the Holocene API remains a host service by
design.

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
- `33god-platform/compose.yaml`: normalized local target for Bloodbank core,
  Lifecycle PostgreSQL/migrate/bootstrap/serve, exactly one Candystore,
  Holocene API preflight/web, and run-only PJangler tools.
- `33god-platform/scripts/validate-compose.py`: semantic validator for default,
  `tools`, `full`, and render-only unsupported `cloud`.
- Root `mise.toml` tasks:
  - `platform:validate`
  - `platform:components`
  - `platform:backfills:check`
  - `platform:compose:validate`
  - `platform:compose:test`
  - `docs:drift`

The integrated model pins Lifecycle to
`ghcr.io/delorenj/lifecycle@sha256:982a25126a292dba8a6af43c38a4b4c136726c054a0076ba56a8d2055974ec67`
with no build key. Bloodbank is pinned at
`48031ee39c238b9d4715b81b74076635235f96d5`; clients reuse its canonical
snapshot-v3 capability/obligation-occurrence and completion-evidence-v2
contracts instead of defining a competing contract.

Validation state as of this handoff:

- `python3 33god-platform/scripts/platform.py validate`: passes.
- `python3 33god-platform/scripts/platform.py components list`: passes.
- `python3 33god-platform/scripts/platform.py backfills check`: passes.
- Candidate default, `tools`, `full`, and `cloud` renders pass.
- Candidate semantic validation and 20 focused tests pass against the populated
  source root.
- The root documentation drift gate invokes the candidate validator with
  explicit `GOD_SOURCE_ROOT` while preserving all previous parity checks.
- The isolated live gate passes all seven Lifecycle offline/restart/outage/
  persistence invariants, including a real authority commit and ordered outbox
  drain during NATS loss, plus occurrence-isolated obligation evidence,
  authority-spoof rejection, versioned capability and causal-lineage flow,
  true late-subscriber replay, canonical duplicate integrity, and the
  Candystore, Momo, and Holocene seams.

Cloud remains blocked. Its profile exists only to render the unsupported
local-bind model and rejection gate; it must never be used with `docker compose
up`. Selecting `--profile cloud` also selects every unprofiled local service, so
stateful services may start and mutate before the rejection container exits.
Cloud therefore has no lifecycle task and is configuration/render inspection
only. The registry drift found during the original handoff remains repaired.

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
9. Establish one headless lifecycle authority that clients cannot bypass.

## Non-goals

This PRD does not require collapsing every repo into one monorepo. Separate repos
can remain while the product control plane coordinates their contracts.

This PRD does not require open sourcing the platform. The target is private
source with optional hosted subscription access.

This PRD does not require replacing every legacy workflow in the first slice.
Legacy projects can be backfilled in stages.

This slice does not promote the render-only cloud profile, publish the root
integration branch, or create a release tag.

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

The product must provide a single governed local Compose target while making
unsupported deployment shapes impossible to mistake for production readiness.

Acceptance criteria:

- `docker compose -f 33god-platform/compose.yaml --profile tools config --no-env-resolution`
  stays green.
- The root owns a normalized projection while components retain internal
  implementation ownership.
- The default contains Bloodbank NATS/init/placement; dedicated Lifecycle
  PostgreSQL/migrate/bootstrap/serve; exactly one standalone Candystore
  PostgreSQL/app/daprd; Holocene API preflight; and Holocene web.
- The Holocene API remains host systemd; Compose must not publish port 4000.
- PJangler CLI and stdio MCP are zero-replica, run-only tools with no ports,
  HTTP health, or daemon lifecycle.
- Profiles match the control-plane definitions:
  - `default`: the local core/audit/control target.
  - `tools` and `full`: default plus run-only PJangler definitions.
  - `cloud`: render-only unsupported evidence with an explicit rejection gate.
- The semantic validator enforces ports, start order, four external networks,
  exact service memberships, six adopted external volumes, the canonical
  Candystore Dapr subscription path, exact Holocene Host/auth/proxy labels,
  unresolved Holocene env-file references, Lifecycle's exact digest/no-build
  contract, and the exclusion of Bloodbank legacy Candystore.
- Checked-in render tasks use `--no-env-resolution`; caller-selected port
  overrides are validated rather than masked.
- Static validation may use the authoritative dirty primary source read-only,
  but Compose cutover requires clean component sources pinned to the intended
  gitlink commits.

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
- Local-only assumptions remain visible in the render-only cloud model until a
  separate hosted architecture removes them.

### FR13. Headless lifecycle authority

The platform must have exactly one component that owns lifecycle semantics and
state. Its clients may supply observations, evidence, and intent, but may not
calculate or persist lifecycle truth.

Acceptance criteria:

- The `lifecycle` component owns the versioned lifecycle spec, materialized
  state, deterministic reconcile function, legal frontier, obligations,
  blockers/gates/checkpoints, and capability validation.
- PJangler supplies stable project/bootstrap identity and lifecycle binding
  inputs; its registry is not lifecycle state.
- Momo reads authoritative state/frontier/obligations, applies business judgment
  to choose among legal work, and submits idempotent intent. It never writes
  lifecycle truth.
- Holocene renders authoritative read models and exposes high-level commands;
  it never infers or writes the resulting state.
- Bloodbank owns canonical lifecycle command/event schemas and transport.
- Candystore owns durable event history and lifecycle read projections, not the
  operational lifecycle writer.
- The standalone component preserves the deterministic controller lineage while
  owning its dedicated operational database and publication path.
- The vertical slice proves configured outbox publication, registered/validated
  contracts, one operational writer, durable projections, bounded clients, and
  the seven-invariant live failure matrix.

## Non-functional requirements

- **Private source:** The platform is not designed as open source by default.
- **Local-first:** The laptop deployment must work before cloud deployment.
- **Cloud-blocked until proven:** No hosted lifecycle command is supported until
  managed storage, network, auth, secrets, tenancy, and backup/restore replace
  the local assumptions.
- **Idempotent operations:** Backfills, validation, setup, and backups must be
  safe to rerun.
- **Fail-open hooks:** Agent hooks must not break interactive agent sessions.
- **Source-of-truth clarity:** The platform must name whether a file is source
  of truth or projection before agents change it.
- **No hidden runtime dirt:** Agent runtime mutations must not dirty source
  repos.
- **Observable gates:** Validation output must be concrete enough for agents to
  route follow-up work.
- **Single lifecycle writer:** Momo, Holocene, Bloodbank, Candystore, PJangler,
  and provider adapters cannot bypass the lifecycle command boundary.
- **Deterministic authority:** Identical ordered inputs and spec version produce
  identical state fingerprint, frontier, obligations, and command verdicts.

## Open issues

These issues are the first things the director must triage.

1. Decide whether Flume belongs in the active product registry.
   Add it only after the repo exists and the manifest has real health,
   source-of-truth, and changelog fields.

2. **Resolved 2026-07-15:** Candybar remains active. Holyfields and Hookd are
   legacy definitions and are excluded from the active component list until
   their repositories and contracts are deliberately restored.

3. Migrate Bloodbank and Holocene PM runtimes from `IGNORE_ALL_YELLOW` to
   `DELINKED_GREEN`.

4. Define the `forever-ago` backup wrapper or enhancement for tiered retention.

5. **Resolved 2026-07-15:** the root projection and semantic validator model the
   integrated local stack; root Compose owns its lifecycle.

6. Reconcile root repo dirt before treating `33GOD` itself as a release branch.

7. **Resolved 2026-07-18:** the standalone Lifecycle authority, dedicated
   persistence, outbox/contract path, Candystore projection, Momo seam,
   Holocene surface, and root isolated failure matrix are implemented.

## MVP plan

### Phase 1. Repair the control plane

Keep the current registry valid and trustworthy as components move.

- Maintain `platform:validate`, `platform:components`, and
  `platform:backfills:check` as passing gates.
- Preserve the active/legacy decision for Candybar, Holyfields, Hookd, and any
  future Flume manifest as live repositories change.
- Record each registry change in `CHANGELOG.pipeline.md` and `changes/*.jsonl`.

### Phase 2. Normalize runtime and hooks

Remove the biggest sources of daily drift.

- Finish canonical Hindsight hook fan-out.
- Finish canonical Bloodbank publisher fan-out.
- Move Hermes PM runtimes into mounted volumes.
- Add runtime backup and restore docs.

### Phase 2a. Establish lifecycle authority — implemented

- Lifecycle owns identity-bound spec/state versions, frontier, obligations,
  grants, commands, deterministic reconcile, and every operational write.
- Root Compose provides dedicated persistence and fail-closed
  migrate/bootstrap/serve ordering with the immutable image digest.
- Bloodbank carries canonical contracts; Candystore durably projects events.
- Momo invokes only legal frontier work and Holocene renders/commands without
  local truth.
- The isolated failure matrix proves offline independence, restart/idempotency,
  stale-version and capability rejection, NATS recovery/order, and PostgreSQL
  persistence.

### Phase 3. Build the local compose stack

The normalized candidate and static gates are implemented. Make root Compose
the sole **process owner** of the adopted local services. This deployment term
does not grant project-lifecycle semantic authority.

- Preserve exact adopted volumes and external networks through the handoff.
- Stop old component projects, start the root target in dependency order, and
  verify exactly one durable Candystore consumer.

### Phase 4. Add director-grade operations

Make the platform operable by agents and humans.

- Promote pipeline changelog use into the default change workflow.
- Add baseline ledger generation.
- Surface stack health in Holocene.
- Create backfill apply flows only after dry-run checks are reliable.

### Phase 5. Prepare hosted deployment

Design a hosted graph that removes the local assumptions; do not promote the
current render-only cloud profile.

- Define tenant, auth, billing, storage, and backup boundaries.
- Add deployment profiles and cloud secret handling.
- Convert product cards into landing-page-ready capability descriptions.

## Director handoff

The director must treat `33god-platform/` as the coordination surface and the
component repos as implementation owners. Do not let a component-local fix hide
cross-component contract changes. If a change affects event schemas, hook
entrypoints, runtime state, project templates, skills, compose, ports, secrets,
or storage, it belongs in the platform changelog and may require a backfill.

Operate the local product through root Compose. Keep the platform registry,
semantic validator, and documentation drift gate green after component or
topology changes. Cloud remains a separate design phase.

For project lifecycle, route all state-changing intent through Bloodbank to the
standalone `lifecycle` component. Do not describe Momo business judgment,
Holocene display state, Candystore history, Bloodbank transport, or PJangler
identity as lifecycle truth.
