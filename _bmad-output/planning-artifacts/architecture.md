---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - PRD.md
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-18.md
  - README.md
  - docs/index.md
  - docs/project-overview.md
  - docs/integration-architecture.md
  - docs/deployment-guide.md
  - docs/drift-governance.md
  - docs/validation-report.md
  - docs/source-tree-analysis.md
  - docs/project-parts.json
  - docs/project-scan-report.json
  - docs/api-contracts-bloodbank.md
  - docs/api-contracts-candystore.md
  - docs/api-contracts-holocene.md
  - docs/api-contracts-pjangler.md
  - docs/architecture-bloodbank.md
  - docs/architecture-candystore.md
  - docs/architecture-holocene.md
  - docs/architecture-pjangler.md
  - docs/component-inventory-bloodbank.md
  - docs/component-inventory-candystore.md
  - docs/component-inventory-holocene.md
  - docs/component-inventory-pjangler.md
  - docs/data-models-bloodbank.md
  - docs/data-models-candystore.md
  - docs/data-models-holocene.md
  - docs/data-models-pjangler.md
  - docs/development-guide-bloodbank.md
  - docs/development-guide-candystore.md
  - docs/development-guide-holocene.md
  - docs/development-guide-pjangler.md
  - 33god-platform/README.md
  - 33god-platform/components.yaml
  - 33god-platform/compose.yaml
  - 33god-platform/docs/backfills.md
  - 33god-platform/docs/changelog-process.md
  - 33god-platform/docs/product-map.md
  - 33god-platform/docs/integrated-compose-topology-audit.md
  - toad/_bmad-output/planning-artifacts/PRD.md
  - toad/_bmad-output/planning-artifacts/architecture.md
  - toad/_bmad-output/planning-artifacts/product-brief.md
  - hermes-agent-template/docs/architecture.md
  - hermes-agent-template/docs/fleet-control-plane/architecture.md
  - hermes-agent-template/docs/fleet-control-plane/prd.md
  - hermes-agent-template/docs/scrum-master/architecture.md
  - pjangler/docs/architecture.md
  - pjangler/docs/product-brief-pjangler-2026-02-01.md
  - momo/PILLARS.md
  - momo/BRAINDUMP.md
  - momo/_bmad-output/planning-artifacts/PRD.md
  - momo/_bmad-output/planning-artifacts/epics.md
  - momo/_bmad-output/planning-artifacts/product-brief.md
  - momo/docs/architecture.md
  - momo/.project.json
  - momo/mise.toml
  - holocene/.stitch/DESIGN.md
  - holocene/_bmad/custom/workflows/ticket-lifecycle/workflow.md
  - holocene/_bmad/custom/workflows/ticket-lifecycle/workflow-plan-ticket-lifecycle.md
  - bloodbank/services/lifecycle-controller/src/reconciler.py
  - bloodbank/services/lifecycle-controller/src/db/repository.py
  - bloodbank/services/lifecycle-controller/src/db/schema.sql
  - bloodbank/services/lifecycle-controller/src/outbox_publisher.py
  - bloodbank/services/lifecycle-controller/tests/test_reconciler.py
  - bloodbank/services/lifecycle-controller/tests/test_runtime_blockers.py
  - /home/delorenj/code/CommonProject/README.md
  - /home/delorenj/code/CommonProject/copier.yml
  - /home/delorenj/code/CommonProject/mise.toml
  - /home/delorenj/code/CommonProject/template/.project.json.jinja
  - /home/delorenj/code/voxxy/compose.yml
  - /home/delorenj/code/voxxy/compose.engines.yml
  - /home/delorenj/code/voxxy/Dockerfile
  - /home/delorenj/code/voxxy/pyproject.toml
  - /home/delorenj/code/voxxy/engines/voxcpm/Dockerfile
  - /home/delorenj/code/voxxy/engines/vibevoice/Dockerfile
  - /home/delorenj/code/skillex/README.md
  - /home/delorenj/code/skillex/pyproject.toml
  - /home/delorenj/code/skillex/_skf-learn/architecture.md
workflowType: 'architecture'
project_name: '33GOD'
user_name: 'Jarad'
date: '2026-07-18T12:00:00-04:00'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

**Current implementation label (2026-07-18):** the local Lifecycle authority
vertical slice, Candystore projection, Momo policy seam, Holocene read/command
surface, and root failure matrix are implemented. Sections describing the
earlier extraction gap are superseded by the implementation record below.

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

The current root PRD defines thirteen functional requirement groups:

1. Machine-readable platform component registry.
2. Cross-component human and machine changelog.
3. Unified local Compose lifecycle.
4. Isolation of mutable runtime state from source.
5. Durable runtime-state handling.
6. Canonical Hindsight memory hooks.
7. Canonical Bloodbank agent event publication.
8. Bloodbank/Candystore event backbone and audit trail.
9. Holocene mission-control visibility.
10. Unified agent capability routing.
11. Idempotent legacy-project backfills.
12. A separately designed hosted-product path.
13. A single headless lifecycle authority with deterministic state, legal
    frontier, obligations, and capability validation.

The architecture must extend this four-component deployed baseline to cover the
following additional product boundaries:

- **Lifecycle:** implemented headless component that exclusively owns lifecycle
  specification/state/reconciliation, legal frontier, obligations, capability
  validation, and every state-changing write.
- **Momo:** PM/EM process manager, heartbeat-driven business decision system,
  ticket abstraction, delegation workflows, and Hindsight-backed project
  memory. It selects among lifecycle-legal work but never computes or writes
  lifecycle truth.
- **Toad:** on-demand Project Custodian agent that composes PJangler operations;
  it is not itself a runtime service or competing MCP implementation.
- **Hermes Template/Fleet:** versioned agent-generation contract, runtime
  configuration contract, fleet reconciliation, and host survival services.
- **CommonProject:** independently versioned project-scaffold contract consumed
  by PJangler; it generates projects rather than running as a platform daemon.
- **Voxxy:** independently deployable voice service with CPU core, optional GPU
  engines, HTTP/MCP contracts, PostgreSQL dependency, and persistent media.
- **PJangler:** project identity, bootstrap, and provider-neutral bindings
  exposed through CLI and stdio MCP; it requires reproducible packaging but not
  an always-running HTTP service.
- **Skillex:** a possible external capability-distribution dependency. Its
  inclusion in the runtime stack is not yet justified.

The requested progression introduces a new functional requirement: every stage
of unification must declare an AC-gated feature inventory. A stage is complete
only when its listed capabilities are executable and its acceptance checks pass.

**Non-Functional Requirements:**

The existing requirements impose these architectural drivers:

- Local-first operation with independently versioned repositories.
- Immutable and reproducible component inputs.
- Idempotent setup, reconciliation, migration, and stage verification.
- Live manifests, runtime state, and executable checks outrank prose.
- Agent runtime activity must not dirty component source.
- Hooks must fail open without breaking interactive agent sessions.
- All cross-component changes must remain observable and attributable.
- Component implementation ownership stays local to each repository.
- Root owns relationships, deployment projection, progression, and drift gates.
- Hosted deployment must remain separable from host-specific local assumptions.

Additional implications from the expanded scope are:

- Independently deployable runtime services need component-owned image contracts
  suitable for publishing and immutable pinning.
- Agent definitions, Copier templates, CLIs, schemas, and skill bundles need
  versioned artifact contracts appropriate to their execution model; forcing
  all of them into long-running containers would create false uniformity.
- GPU-backed Voxxy engines require capability-aware placement and cannot be
  assumed available on every 33GOD host.
- CommonProject and Voxxy must preserve standalone consumption outside 33GOD.
- Lifecycle, Momo, and Toad must have distinct ownership boundaries: Lifecycle
  governs deterministic project state and legal transitions; Momo governs
  business prioritization and execution process; Toad governs project creation,
  adoption, and portfolio custody.
- Skillex must be separated into two questions: whether 33GOD consumes skills,
  and whether the Skillex product itself belongs in the deployed stack.

**Scale & Complexity:**

- Primary domain: event-driven agentic development and operations platform.
- Complexity level: high.
- Architectural product boundaries: approximately ten, plus optional external
  capabilities and multiple runtime units inside Voxxy and Hermes.
- Deployment modes: persistent service, host service, run-only tool, generated
  template, agent skill, and optional GPU worker.
- Data systems: NATS JetStream, Candystore PostgreSQL, Hindsight memory,
  PJangler project registry, Hermes runtime state, ticket-provider state, and
  Voxxy voice/media state.
- Interaction surfaces: HTTP, MCP over HTTP, MCP over stdio, NATS/Dapr events,
  CLI, systemd, Docker Compose, agent skills, generated repositories, and
  external provider APIs.

There is no regulatory-compliance requirement in the loaded material. Security
and provenance remain important operational requirements, but the architecture
does not need to assume a regulated multi-tenant enterprise environment.

### Technical Constraints & Dependencies

- Lifecycle is the sole target authority for lifecycle spec, operational state,
  reconciliation, frontier, obligations, and capability validation.
- Bloodbank remains the event-contract and event-transport authority; hosting
  the current controller embryo does not make Bloodbank the target domain owner.
- Candystore remains the canonical durable event-history and read-model
  projection, not the operational lifecycle writer.
- Holocene remains the operator-facing renderer and high-level command surface;
  command results come from Lifecycle.
- PJangler remains the deterministic project identity, bootstrap, and binding
  input owner; lifecycle-looking status in its registry is a projection.
- CommonProject is the mandatory base project-scaffold convention consumed by
  PJangler, not a competing bootstrap mechanism.
- Hermes Template owns generated agent-role structure; mutable runtime state must
  remain outside immutable template artifacts.
- Toad delegates deterministic project/bootstrap work to PJangler.
- Momo must not duplicate lifecycle, ticket-provider, fleet, or project-registry
  truth. It may choose only from the lifecycle-provided legal frontier.
- Voxxy already owns Dockerfiles for its CPU core and GPU engines and already
  supports independent Compose deployment.
- Current root Compose still builds Candystore locally and bind-mounts/builds
  Holocene at startup; this conflicts with the desired registry-pinned end state.
- PJangler, CommonProject, Toad, and Hermes Template are not naturally persistent
  services, so their inclusion must use run-only or artifact-consumption models.
- Several existing documents still describe the system as a four-part candidate
  rather than the live and expanding platform. Those statements are historical
  evidence, not target architecture.
- Toad currently names Skillex as its distribution owner, while the operator is
  questioning whether Skillex belongs in 33GOD. The architecture must resolve
  this without conflating an external dependency with a deployed stack member.

### Cross-Cutting Concerns Identified

1. **Artifact taxonomy:** service images, run-only tool images, CLI packages,
   Copier templates, agent bundles, schemas, and workflow definitions need
   different lifecycle contracts.
2. **Version provenance:** every consumed artifact needs an immutable version,
   source commit, publication identity, and root pin.
3. **Authority taxonomy:** root Compose owns adopted process lifecycles;
   Lifecycle alone owns project-lifecycle truth; component owners retain their
   volumes, schedulers, registries, and mutable state directories.
4. **Acceptance-gated progression:** every integration stage needs static,
   startup, contract, feature, and observability checks.
5. **Dependency ordering:** project scaffolding/identity precedes lifecycle
   binding; lifecycle contract and vertical slice precede agent provisioning
   that can mutate project flow; fleet contracts then precede Momo autonomy.
6. **Event consistency:** lifecycle commands/events and Momo decision events use
   distinct Bloodbank contracts and remain queryable through Candystore.
7. **Dashboard visibility:** Holocene renders lifecycle state version,
   provenance, observation freshness, frontier, obligations, blockers/gates,
   command result, component version, and readiness without recomputing truth.
8. **Standalone compatibility:** CommonProject and Voxxy releases cannot depend
   on the 33GOD monorepo checkout.
9. **Configuration and secrets:** images must consume narrow runtime
   configuration without embedding host credentials or complete host
   environments.
10. **Host-specific authority:** systemd, agent CLIs, filesystem access, GPU
    access, and provider credentials cannot be hidden behind misleading
    container abstractions.
11. **Drift governance:** root architecture and component BMAD documents require
    executable parity checks as the component set expands.
12. **Optionality:** optional services and capabilities must degrade visibly
    without preventing the core event/audit/control pipeline from operating.

## Starter Template Evaluation

### Primary Technology Domain

33GOD is a brownfield, multi-runtime platform and artifact ecosystem. It is not
a single web application, backend, or CLI that benefits from adopting a new
framework starter.

The architecture foundation is therefore:

1. The existing `33god-platform` control plane.
2. CommonProject as the canonical new-repository generator.
3. PJangler as the canonical generator/provisioning interface.
4. Component-owned build and packaging contracts.
5. Root-owned composition, version pins, stage gates, and drift validation.

### Starter Options Considered

#### Generic application starter

Rejected. A Next.js, FastAPI, NestJS, or similar starter would impose one
runtime model on components that deliberately use different technologies and
artifact types.

#### New 33GOD platform starter

Rejected. The live root platform already contains the component registry,
Compose projection, semantic validator, change ledger, and documentation drift
gate. Replacing it would discard working brownfield evidence.

#### CommonProject for every component

Selected with qualification. CommonProject remains the mandatory starting point
for new project repositories, but its generated output must depend on the
declared project type:

- A persistent runtime service receives a Dockerfile and image-publication
  workflow.
- A run-only CLI may receive a tool image when container execution adds value.
- A template repository receives versioned Git/Copier release metadata.
- An agent or skill repository receives its native bundle/package contract.
- A schema-only repository receives a versioned schema artifact contract.
- No component receives a fake server merely to appear in Compose.

#### Existing component repositories with normalized contracts

Selected for brownfield components. Existing repositories are brought into
conformance through staged component-specific work rather than regeneration.

### Selected Foundation: Brownfield Platform plus CommonProject

**Rationale for Selection:**

This preserves live component ownership while establishing one repeatable rule
for future repositories. CommonProject defines the baseline repository
conventions; PJangler invokes it and records provenance; each component owns its
runtime build; the root platform consumes released artifacts and proves the
integrated behavior.

CommonProject remains independently usable outside 33GOD. Copier supports
versioned templates, explicit VCS references, stored answers, and update checks.
Stable release tags must not move after projects have been generated.

**Canonical Project Initialization:**

```bash
pjangler project create <project-intent>
```

PJangler is responsible for resolving that request into a CommonProject render
at an immutable release reference. The underlying deterministic render contract
is equivalent to:

```bash
copier copy \
  --vcs-ref <immutable-commonproject-release> \
  git@github.com:delorenj/CommonProject.git \
  <destination>
```

Direct Copier use remains supported for CommonProject's independent consumers,
but 33GOD lifecycle workflows use PJangler so registry, board, agent, and
provenance actions remain coordinated.

### Architectural Decisions Provided by the Foundation

**Language and Runtime:**

No platform-wide implementation language is imposed. Each component retains its
native runtime. CommonProject records the selected runtime and emits the
corresponding development and packaging baseline.

**Container Contract:**

Every independently deployable runtime unit owns a Dockerfile in its component
repository.

This rule applies to runtime units, not every conceptual component:

- Candystore application: required.
- Holocene web: required.
- Voxxy core and each independently scheduled engine: required.
- Momo runtime/heartbeat adapter: required if deployed as a container.
- Lifecycle service: present in the validated local Compose set by exact
  immutable digest, with dedicated PostgreSQL and fail-closed
  migrate/bootstrap/serve ordering. Compose never builds it.
- PJangler: optional run-only tool image, not a daemon.
- Bloodbank: upstream service images plus component-owned initialization and
  configuration artifacts; custom runtime code requires its own image.
- CommonProject: no runtime image required.
- Hermes Template: no runtime image required for the template itself.
- Toad: no runtime image required for the agent bundle.
- Skillex: no stack image required unless a network service is introduced.

**Image Publication:**

Runtime images are published to an OCI-compatible registry, initially GHCR.
Each release provides:

- semantic version tag;
- source-commit tag;
- OCI source/revision/version labels;
- immutable manifest digest;
- build provenance or attestation;
- architecture/platform metadata where relevant.

Root Compose references release versions for readability and records or locks
the resolved digest for deterministic deployment. Mutable `latest` references
are not accepted by stage gates.

**Compose Organization:**

The durable target is component-owned Compose fragments included by the root
application model. Each fragment owns its service definitions, health checks,
runtime configuration names, and component-local paths. Root owns:

- selected component versions;
- profiles;
- cross-component networks and dependencies;
- shared infrastructure identities;
- acceptance gates;
- integrated lifecycle commands.

Here "integrated lifecycle commands" means deployment/process commands. Project
lifecycle commands target the standalone Lifecycle component and must not be
implemented as direct Momo, Holocene, provider, or database writes.

The current duplicated root projection remains valid during migration and is
replaced incrementally only after each component fragment passes equivalence
tests.

**Testing Framework:**

No universal test framework is imposed. Every component must expose a normalized
gate contract through `mise` or another root-callable command:

- unit or component tests;
- image build;
- image smoke test;
- health/readiness verification;
- contract verification;
- stage-specific functional acceptance.

Root orchestration consumes results, not framework-specific internals.

**Code Organization:**

CommonProject provides repository-wide conventions. Component internals remain
owned locally. Root architecture does not require identical source trees across
Python, TypeScript, agent-bundle, template, and GPU-engine repositories.

**Development Experience:**

Local component development may continue using source builds and focused
Compose files. Integrated and release verification uses published artifacts.
The same root Compose model accepts an explicit development override for local
build contexts without changing the pinned release definition.

### First Implementation Story

Define and enforce an artifact manifest schema for every registered component:

- artifact type;
- source repository;
- release version;
- immutable source revision;
- registry/package/template location;
- digest or immutable reference;
- runtime mode;
- component-owned validation command;
- root-stage acceptance command.

This contract must land before additional components are added to the live
stack, because it determines what "pinned" means for services, tools, templates,
and agent bundles.

## Approved Lifecycle Authority Correction (2026-07-18)

### Decision

Use the separate headless `lifecycle` component as the only deterministic
authority. Bloodbank retains canonical contracts/transport; no second client
contract or competing reconciler is permitted.

### Current state

- Lifecycle runtime source `cda59658bef6d586c8aa01cacd88bc4e3ee867e0`
  is exercised only as
  `ghcr.io/delorenj/lifecycle@sha256:b216be4e1b796236309ee0b39120b0f353b62ee9f3c677901b2441a2c7aef210`.
- Bloodbank is pinned at
  `aacd88564ea299924b8298165933ba821640bdba`; its canonical snapshot v3
  capability/obligation-occurrence contract and completion-evidence v2 define
  the exact wire path used by authority and clients.
- Root Compose runs dedicated Lifecycle PostgreSQL, one-shot migration,
  deterministic bootstrap, and serve with fail-closed dependencies.
- Candystore consumes canonical lifecycle events durably and serves a replay-safe,
  version-ordered, visibly stale/unknown read projection; duplicate IDs always
  re-project the canonical stored envelope rather than a conflicting delivery.
- Momo ranks only authoritative legal frontier commands, services canonical
  pending obligations as directly correlated actor work, resolves canonical
  skill references, and separates rationale from invocation/evidence/command
  intent.
- Holocene renders the Candystore projection and submits complete high-level
  commands through Bloodbank without local lifecycle mutation. Its reusable
  Chromium proof reads exact action identity from semantic DOM state, accepts
  the matching confirmation, records the real browser POST/202 receipt, and
  waits for the later authoritative state/version/causality/verdict render.
- The isolated live matrix passes all seven offline, restart, stale-version,
  capability, and PostgreSQL persistence invariants. Its outage proof publishes
  through `BLOODBANK_COMMANDS`, observes the deployed durable's ack-pending
  delivery behind a PostgreSQL row lock, stops NATS before releasing the lock,
  proves the single deployed writer's atomic database commit, then proves
  durable idempotent redelivery and ordered outbox recovery without duplicate
  state/history/command-result counts. The matrix also covers
  occurrence-isolated obligation evidence, authority-spoof rejection,
  versioned grants, real causal IDs, pre-start replay, and
  conflicting-duplicate integrity.

### Current authority matrix

| Concern | Sole owner | Allowed client behavior |
|---|---|---|
| Project/bootstrap identity | PJangler | Lifecycle consumes stable identity and binding inputs |
| Lifecycle spec/state/reconcile | Lifecycle | Clients submit observations/evidence and read versioned snapshots |
| Legal frontier/obligations | Lifecycle | Momo ranks only returned legal candidates; Holocene renders them |
| Capability validation | Lifecycle | Commands carry actor/capability/idempotency/state-version context |
| Commands/events/schema/transport | Bloodbank | Lifecycle publishes/consumes only registered canonical contracts |
| Durable event history/read models | Candystore | Clients query projections; Candystore never writes lifecycle state |
| Business prioritization/delegation | Momo | Submit intent; never calculate or persist lifecycle truth |
| UI/operations | Holocene | Render snapshots, confirm/click high-level browser actions, and observe later results; never infer results |
| Process topology and acceptance/drift | 33GOD root | Run exactly one digest-pinned lifecycle authority process and enforce component pins |

### Current interaction

```text
PJangler identity -----> Lifecycle binding/spec
                              |
observations/evidence ------> | deterministic reconcile
                              | -> state + frontier + obligations + grants
                              v
                  canonical Bloodbank events/commands
                              |
                              v
                   Candystore history/read models
                         |                 |
                         v                 v
                  Momo reads          Holocene browser renders
                  frontier, picks     state/provenance, confirms/
                  legal work          clicks, then observes result
                         \                 /
                          -- intent/command --> Lifecycle validates
```

### Command invariants

- Every mutation has an idempotency key and expected `state_version`.
- Lifecycle validates actor capability and transition legality before a write.
- Illegal, stale-version, duplicate, or unauthorized commands return a stable
  verdict without state mutation.
- The state row, append-only history, and outbox event commit atomically.
- Bloodbank transports the contract; Candystore persists the event; neither
  becomes the state authority.
- Momo decision events explain why it selected a legal action. They do not enact
  that action.

### Implementation record

The local vertical slice is complete: immutable image pin, dedicated operational
store, migration/bootstrap/serve chain, canonical Bloodbank publication,
transactional outbox recovery, durable Candystore projection, and bounded
Momo/Holocene clients all have automated and isolated live evidence. Remaining
work is a separate production/cloud rollout decision, not completion of this
local authority slice.
