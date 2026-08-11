# 33GOD productized development environment PRD

Status: Integrated local Compose stack live; component set expanded to thirteen
Owner: 33GOD Director
Last updated: August 10, 2026

## Summary

33GOD is a private, local-first development environment made from multiple
active repositories that already behave like one pipeline. The current problem
is coordination: Bloodbank, Candystore, Holocene, PJangler, Krebs, Momo, Toad,
Hermes Fleet, Pipeline MCP Hub, Skillex, Hindsight, Candybar, and HeyMa change
independently, but their contracts affect one another.

The goal is to productize these pieces into one cohesive platform with one
governed local deployment entrypoint and, later, a separately designed hosted
subscription service. `33god-platform/` indexes components, records
cross-component changes, defines backfill checks, and owns the live normalized
integrated Compose stack.

## Situation

The 33GOD system grew organically across several repos and host-level config
locations. That was useful while discovering the shape of the pipeline, but it
now creates avoidable maintenance load. A change to agent hooks, Hermes runtime
profiles, event schemas, project templates, ticket lifecycle, or skill routing
can quietly break another component.

Several examples drove this PRD:

- Hindsight memory hooks migrated toward a canonical shared folder, but some
  agent configs still referenced old script paths.
- Bloodbank hook publishing had per-agent drift instead of one canonical
  publisher entrypoint with client-specific adapters.
- Hermes PM runtimes were tracked or submoduled inside project repos even
  though runtimes are mutable operational state.
- Bloodbank, Candystore, and Holocene needed a coordinated baseline before
  moving services into a product stack.
- Ticket lifecycle truth was embedded in Momo, so every consumer that needed the
  state machine had to reach into an agent to get it.
- Skills lived in a root `skills/` directory divorced from the components whose
  contracts they described, so a contract change and its skill update landed in
  different commits.
- Feature work accumulated in git worktrees that were never folded back to main,
  producing branches that looked like unmerged work but were stale duplicates of
  code that had already shipped under different SHAs.
- Existing docs in the repo are stale in places. The current source of truth
  must be live files, validation output, and explicit platform manifests.

## Product vision

33GOD becomes a productized development environment for agentic software
delivery.

The local product gives one operator the whole pipeline on a laptop:

- Event backbone and schemas.
- Durable event history and audit trail.
- Mission-control dashboard.
- One canonical ticket-lifecycle state machine and provider abstraction.
- Project and agent provisioning.
- Managed long-running PM and worker agents, plus interactive orchestration.
- Shared skill hub and memory hooks.
- Unified Bloodbank and Hindsight hook entrypoints.
- Runtime state mounted outside source repos.
- Backups for mutable agent/runtime state.

The hosted product uses the same component graph with stronger auth, tenant
boundaries, managed storage, cloud secrets, and subscription packaging.

## Component inventory

Thirteen components are registered in `33god-platform/components.yaml`. Not all
are services; the runtime mode is part of the contract.

| Component        | Role                       | Location                | Runtime mode              | Profile      |
| ---------------- | -------------------------- | ----------------------- | ------------------------- | ------------ |
| Bloodbank        | event backbone             | `bloodbank/` submodule  | Compose service (NATS)    | default      |
| Candystore       | event audit trail          | `candystore/` submodule | Compose service           | default      |
| Holocene         | control-plane dashboard    | `holocene/` submodule   | Compose web + host API    | default      |
| PJangler         | provisioning control plane | `pjangler/` submodule   | run-only CLI + stdio MCP  | tools, full  |
| Krebs            | ticket-lifecycle engine    | `krebs/` in-tree        | spec + adapters, no daemon| integrations |
| Momo             | PM/EM orchestration agent  | `momo/` submodule       | agent skill, not a service| agents       |
| Toad             | project custodian agent    | `toad/` submodule       | CLI + stdio MCP           | agents       |
| Hermes Fleet     | agent runtime fleet        | `hermes-agent-template/`| host systemd + template   | agents       |
| Pipeline MCP Hub | tool dispatch gateway      | `mcp-hub/` submodule    | hosted MCP endpoint       | integrations |
| Skillex          | skill distribution         | `~/code/skillex`        | external registry         | skills       |
| Hindsight        | persistent memory          | `~/.agents`, hosted API | external service + hooks  | skills       |
| Candybar         | topology visualization     | `candybar/` submodule   | optional desktop/web      | optional     |
| HeyMa            | voice interface            | `~/code/HeyMa`          | optional service          | optional     |

Krebs is tracked directly in the root repository rather than as a submodule. It
is a specification and adapter surface, not a deployable daemon, so it has no
independent release train yet. Promoting it to its own repository is an open
issue, not a settled decision.

Skillex, Hindsight, and HeyMa live outside the monorepo checkout. Their
manifests point at their real paths; `platform:components` reports presence.

### Components named in the architecture document but not yet present

`AGENTS.md` (the architecture decision document) describes **CommonProject** and
**Voxxy** as product boundaries. Neither has a checkout in this monorepo and
neither has a component manifest. CommonProject exists as the Copier template
PJangler renders from; Voxxy is a design target. Both are excluded from the
active registry until a repository and contract exist, matching the rule applied
to Flume, Holyfields, and Hookd.

## Current control-plane state

`33god-platform/` is the product control-plane directory and root-owned
cross-component projection. Root Compose owns Bloodbank core, the canonical
Candystore deployment, and Holocene web; the Holocene API remains a healthy host
service by design.

Current artifacts include:

- `33god-platform/components.yaml`: product profiles, component manifest list,
  contract paths, and change policy.
- `33god-platform/components/*.yaml`: thirteen per-component manifests.
- `33god-platform/CHANGELOG.pipeline.md`: human-readable ecosystem changelog.
- `33god-platform/changes/*.jsonl`: machine-readable cross-component change log.
- `33god-platform/backfills/*.yaml`: read-only drift and legacy migration
  manifests.
- `33god-platform/docs/product-map.md`: product card map for the future platform.
- `33god-platform/skills/`: root-owned skills — `33god-hub`, `merge-forward`,
  and `skillex-skill-registry`.
- `33god-platform/compose.yaml`: normalized local target for Bloodbank core,
  exactly one Candystore, Holocene API preflight/web, and run-only PJangler
  tools.
- `33god-platform/scripts/validate-compose.py`: semantic validator for default,
  `tools`, `full`, and render-only unsupported `cloud`.
- Root `mise.toml` tasks: `platform:validate`, `platform:components`,
  `platform:backfills:check`, `platform:compose:validate`,
  `platform:compose:test`, `docs:drift`, `skills-sync`, and
  `skills-provision-packs`.

Validation state as of this update:

- `python3 33god-platform/scripts/platform.py validate`: passes.
- `python3 33god-platform/scripts/platform.py components list`: passes, thirteen
  components, all present.
- `python3 33god-platform/scripts/platform.py backfills check`: four OK, one
  STALE (`momo-lifecycle-duplicate-v1`, intentionally open — see Open issues).

Cloud remains blocked. Its profile exists only to render the unsupported
local-bind model and rejection gate; it must never be used with `docker compose
up`. Selecting `--profile cloud` also selects every unprofiled local service, so
stateful services may start and mutate before the rejection container exits.
Cloud therefore has no lifecycle task and is configuration/render inspection
only.

## Baseline status

Every submodule pin equals its `origin/main` tip as of August 10, 2026. This is
the first checkpoint where that has been true across the whole family.

| Component             | Pin          | Describe                                    | Runtime mode        | Notes                                                                    |
| --------------------- | ------------ | ------------------------------------------- | ------------------- | ------------------------------------------------------------------------ |
| Bloodbank             | `4f394a4c9b` | `platform-baseline-2026-07-08-26-g4f394a4`  | `IGNORE_ALL_YELLOW` | Owns its integration and SDK-generation skills. PM runtime still tracked. |
| Candystore            | `03abfe0b62` | `platform-baseline-2026-07-08-8-g03abfe0`   | `DELINKED_GREEN`    | Runtime delinked from Git. Remote tag exists.                            |
| Holocene              | `4fd42681e7` | `platform-baseline-2026-07-08-9-g4fd4268`   | `IGNORE_ALL_YELLOW` | PM runtime still tracked as a submodule with `ignore = all`.             |
| PJangler              | `46e1b44cd3` | `PJAN-44-v1.2.26-7-g46e1b44`                | clean               | OIDC trusted publishing (PJAN-45). Owns seven skills.                    |
| Momo                  | `8e90551c65` | —                                           | clean               | Hardened orchestration: lane gate, tree lock, findings ledger. 16 tests. |
| Toad                  | `ca69373db0` | —                                           | clean               | Dry-run by default; live actions gated by `TOAD_ALLOW_LIVE=1`.           |
| Hermes Agent Template | `a3c60f0f0e` | —                                           | clean               | Template checkout-path fix.                                              |
| Pipeline MCP Hub      | `967e41758a` | —                                           | clean               | Served at `https://mcp.delo.sh/mcp`.                                     |
| Candybar              | `9af829d0b6` | `bloodbank-integrated-7-g9af829d`           | `IGNORE_ALL_YELLOW` | Only delta is untracked Hermes PM runtime state.                         |

The baseline is good enough to proceed with platform-stack planning, but it is
not a clean release train yet. Bloodbank, Holocene, and Candybar still need
runtime delinking or an explicit migration plan from tracked runtime submodules
to mounted runtime volumes.

## Goals

The product must make the whole 33GOD pipeline feel like one maintained system.

1. Provide one local compose entrypoint for the platform.
2. Keep implementation ownership in component repos while centralizing platform
   contracts in `33god-platform/`.
3. Normalize agent memory and event hooks across agent clients.
4. Move agent runtimes out of tracked source repos and into mounted volumes.
5. Back up mutable runtime state with `forever-ago`.
6. Make cross-component changes visible through a pipeline changelog.
7. Give agents one skill hub for 33GOD routing and reference lookup, with each
   skill owned by the component whose contract it describes.
8. Keep exactly one ticket-lifecycle state machine across every consumer.
9. Preserve a path to hosted, private, subscription-based deployment.

## Non-goals

This PRD does not require collapsing every repo into one monorepo. Separate repos
can remain while the product control plane coordinates their contracts.

This PRD does not require open sourcing the platform. The target is private
source with optional hosted subscription access.

This PRD does not require replacing every legacy workflow in the first slice.
Legacy projects can be backfilled in stages.

This PRD does not require every component to be a container. Specs, templates,
CLIs, and agent bundles are first-class artifact types; inventing a daemon so a
component can appear in Compose is an anti-goal.

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
- Every component declares a runtime mode; non-service components declare an
  execution model rather than an empty compose block.

### FR2. Cross-component changelog

The platform must record changes that affect multiple components in both human
and machine-readable forms.

Acceptance criteria:

- Any event schema, hook entrypoint, project template, Hermes runtime contract,
  lifecycle machine, skill ownership, compose boundary, port, secret, or storage
  change creates a `changes/*.jsonl` entry.
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
- The default contains Bloodbank NATS/init/placement, exactly one standalone
  Candystore PostgreSQL/app/daprd, Holocene API preflight, and Holocene web.
- The Holocene API remains host systemd; Compose must not publish port 4000.
- PJangler CLI and stdio MCP are zero-replica, run-only tools with no ports,
  HTTP health, or daemon lifecycle.
- Profiles match the control-plane definitions:
  - `default`: the local core/audit/control target.
  - `tools` and `full`: default plus run-only PJangler definitions.
  - `cloud`: render-only unsupported evidence with an explicit rejection gate.
- The semantic validator enforces ports, start order, three external networks,
  exact service memberships, five adopted external volumes, the canonical
  Candystore Dapr subscription path, exact Holocene Host/auth/proxy labels,
  unresolved Holocene env-file references, and the exclusion of Bloodbank
  legacy Candystore.
- Checked-in render tasks use `--no-env-resolution`; caller-selected port
  overrides are validated rather than masked.

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
- No change may introduce a **new** tracked runtime submodule. A branch that
  adds one is rejected regardless of the value of its other content.

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

- All inter-service communication flows through Bloodbank over NATS JetStream.
- Candystore persists event history for query, replay, and summaries.
- Direct service-to-service calls are treated as integration debt.
- Schema validation and subject naming checks are part of the platform gate.

### FR9. Mission control

Holocene must become the operator-facing control plane for platform health.

Acceptance criteria:

- Holocene surfaces component health, hook health, agent/fleet status, and
  platform-stack readiness.
- It distinguishes focused verification from full-suite green.
- It can display baseline status across every registered component.

### FR10. Unified skill hub and component-owned skills

Agents must start from one 33GOD skill hub before drilling into component
skills, and every skill must be owned by the component whose contract it
describes.

Acceptance criteria:

- `33god-platform/skills/33god-hub/` routes agents to component references.
- Each skill's source of truth lives in its owning component repository:
  Bloodbank owns event-integration skills, PJangler owns provisioning and mise
  skills, Krebs owns lifecycle and triage skills, and `33god-platform/` owns
  cross-cutting skills.
- Root `skills/` contains only links to those owners, never divergent copies.
- Skillex remains the durable distribution mechanism for packaged skills.
- The hub names source-of-truth boundaries, especially project registry,
  Bloodbank events, ticket lifecycle, Hermes fleet state, and agent hook
  fan-out.

### FR11. Backfill program

Legacy projects and configs must be brought forward through explicit,
idempotent backfills.

Acceptance criteria:

- Backfill manifests declare search paths, forbidden patterns, owner component,
  summary, and remediation notes.
- Initial backfills remain read-only until each remediation is reversible and
  safe.
- A future `backfills apply <id>` flow must be gated and auditable.

### FR12. Single ticket-lifecycle authority

Krebs must own the only canonical ticket-lifecycle state machine, and every
consumer must resolve it from there.

Acceptance criteria:

- `krebs/spec/lifecycle.v1.yaml` is the only machine; no component ships a fork.
- Per-repo variation is limited to provider label maps and tunable guard knobs,
  expressed through the `tp` adapter's normalized-state map and the per-repo
  state map.
- The `tp` adapter exposes exactly five normalized bands: `backlog`,
  `unstarted`, `started`, `in_review`, `completed`.
- Momo, Hermes PM, Pipeline MCP Hub, and Holocene consume the machine by
  pointer, never by copy.
- `momo-lifecycle-duplicate-v1` reports OK once `momo/lifecycle/` is retired.
- Krebs normalizes provider webhooks to Bloodbank events rather than
  maintaining a private dispatch graph.

### FR13. Orchestration and custody boundaries

Momo and Toad must have distinct, non-overlapping ownership.

Acceptance criteria:

- Momo governs ongoing project execution: roadmap, next action, delegation,
  review, and closure. It delegates every code change and edits no code itself.
- Toad governs project creation, adoption, audit, and migration, delegating
  deterministic work to PJangler.
- Neither duplicates ticket-provider, fleet, or project-registry truth.
- Toad's networked and irreversible actions are dry-run by default and gated by
  `TOAD_ALLOW_LIVE=1`.
- `momo/PILLARS.md` is referenced by every agent carrier, never copied.

### FR14. Trunk discipline

Work must not accumulate in worktrees or long-lived branches.

Acceptance criteria:

- Component work merges or rebases back to `main` optimistically rather than
  waiting on a clean release train.
- Every submodule pin in the root repository equals that submodule's
  `origin/main` tip at checkpoint time.
- Worktrees are removed once their branch is contained in `origin/main`, or once
  its content is proven superseded by a content comparison rather than a commit
  count.
- A branch whose files are byte-identical to `main`, or whose merge would delete
  content `main` already has, is treated as superseded and pruned, not merged.

### FR15. Hosted product path

The local platform must leave a clear path to a hosted subscription product.

Acceptance criteria:

- Component manifests contain product-card language that can feed a teaser or
  subscriber-facing landing page.
- Cloud deployment has explicit auth, tenant, storage, secret, and backup
  requirements.
- Local-only assumptions remain visible in the render-only cloud model until a
  separate hosted architecture removes them.

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
- **Secret hygiene:** `.env` is materialized by `op inject` from the committed
  `.env.op` reference file and is never tracked. A missing `op` binary must not
  clobber an existing `.env`.

## Open issues

These issues are the first things the director must triage.

1. **Retire `momo/lifecycle/`.** It is a drifted pre-promotion copy of the Krebs
   machine; both `lifecycle.v1.yaml` and `lifecycle.schema.json` differ from
   `krebs/spec/`. Momo's own spec already points at Krebs, so the copy has no
   consumer justification. Tracked by `momo-lifecycle-duplicate-v1`.

2. **Decide Krebs's repository home.** Krebs is tracked in-tree while every other
   first-class component is an independently versioned repo. It needs either its
   own repository and release train or an explicit decision that specs live in
   the root.

3. **Decide whether CommonProject and Voxxy become registered components.** Both
   are named in the architecture document; neither has a checkout or manifest.
   Apply the same rule used for Flume: register only after the repo exists and
   the manifest has real health, source-of-truth, and changelog fields.

4. **Decide whether Flume belongs in the active product registry.** Unchanged
   from the previous revision; still no repository.

5. **Migrate Bloodbank, Holocene, and Candybar PM runtimes from
   `IGNORE_ALL_YELLOW` to `DELINKED_GREEN`.** Candybar's only working-tree delta
   is its tracked Hermes PM runtime pointer, which proves the cost of the
   current model.

6. **Define the `forever-ago` backup wrapper or enhancement for tiered
   retention.**

7. **Reconcile the root auto-checkpoint writer.** Something in the environment
   commits submodule pin bumps to the root repository outside an interactive
   session. It is currently producing correct commits, but an unattended writer
   on the release branch needs an explicit owner and an audit trail.

8. **Triage `candystore/impl/candystore-audit-trail`.** From May 25; every file
   differs from a `main` that has moved 21 commits past it. The branch ref is
   preserved and its worktree is removed. Decide whether any of the CANPM-T1/T2
   events-migration work is still wanted before deleting the ref.

**Resolved 2026-07-15:** Candybar remains active. Holyfields and Hookd are
legacy definitions and are excluded from the active component list until their
repositories and contracts are deliberately restored.

**Resolved 2026-07-15:** The root projection and semantic validator model the
integrated local stack; root Compose owns its lifecycle.

**Resolved 2026-08-10:** Root repo dirt is reconciled. Every submodule pin
equals its `origin/main` tip, skills have component owners, and Momo, Toad, and
Krebs are registered components.

**Resolved 2026-08-11:** The company-reporter split is closed. The Hermes
template absorbed the reporter role, its least-privilege runtime contract,
`secret-scan.py`, and the salvaged reporter health watchdog. The parent branch
was deleted rather than merged: its generated `agents/hermes/reporter/` profile
is regenerable from the template, its `scrum-master/` tooling had already been
renamed to `sentinel/` upstream, its standalone sentinel runner was superseded
by the fused `heartbeat.sh`, and it carried a tracked runtime submodule that
FR4 forbids. No worktrees remain anywhere in the family.

## MVP plan

### Phase 1. Repair the control plane

Keep the current registry valid and trustworthy as components move.

- Maintain `platform:validate`, `platform:components`, and
  `platform:backfills:check` as passing gates.
- Preserve the active/legacy decision for Candybar, Holyfields, Hookd, and any
  future Flume, CommonProject, or Voxxy manifest as live repositories change.
- Record each registry change in `CHANGELOG.pipeline.md` and `changes/*.jsonl`.

### Phase 2. Normalize runtime and hooks

Remove the biggest sources of daily drift.

- Finish canonical Hindsight hook fan-out.
- Finish canonical Bloodbank publisher fan-out.
- Move Hermes PM runtimes into mounted volumes.
- Add runtime backup and restore docs.

### Phase 3. Build the local compose stack

The normalized candidate and static gates are implemented. Make root Compose
the sole lifecycle owner of the local product.

- Preserve exact adopted volumes and external networks through the handoff.
- Stop old component projects, start the root target in dependency order, and
  verify exactly one durable Candystore consumer.

### Phase 4. Consolidate lifecycle truth

Make Krebs the only machine every consumer reads.

- Retire `momo/lifecycle/` and prove the pointer resolves for every consumer.
- Land the `tp` adapter contract and provider label maps for Plane, with Linear
  and Trello behind the same five bands.
- Normalize provider webhooks into Bloodbank events and verify them in
  Candystore.
- Decide Krebs's repository home and, if extracted, publish its release train.

### Phase 5. Add director-grade operations

Make the platform operable by agents and humans.

- Promote pipeline changelog use into the default change workflow.
- Add baseline ledger generation.
- Surface stack health in Holocene.
- Create backfill apply flows only after dry-run checks are reliable.

### Phase 6. Prepare hosted deployment

Design a hosted graph that removes the local assumptions; do not promote the
current render-only cloud profile.

- Define tenant, auth, billing, storage, and backup boundaries.
- Add deployment profiles and cloud secret handling.
- Convert product cards into landing-page-ready capability descriptions.

## Director handoff

The director must treat `33god-platform/` as the coordination surface and the
component repos as implementation owners. Do not let a component-local fix hide
cross-component contract changes. If a change affects event schemas, hook
entrypoints, runtime state, project templates, the lifecycle machine, skill
ownership, compose, ports, secrets, or storage, it belongs in the platform
changelog and may require a backfill.

Operate the local product through root Compose. Keep the platform registry,
semantic validator, and documentation drift gate green after component or
topology changes. Keep every submodule pin at its tip and never let work settle
in a worktree. Cloud remains a separate design phase.
