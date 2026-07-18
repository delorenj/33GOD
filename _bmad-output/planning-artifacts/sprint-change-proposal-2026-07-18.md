# Sprint Change Proposal: Lifecycle Component Boundary Correction

**Date:** 2026-07-18
**Project:** 33GOD
**Mode:** Batch
**Status:** Approved for planning reconciliation and implementation handoff
**Scope classification:** **Major** — fundamental product and architecture replan
**Approval:** Jarad approved the lifecycle-component boundary correction and its
implementation before this Correct Course run. This document records that approval;
the workflow did not pause for a second approval prompt.

## 1. Issue Summary

The current planning set collapses three different responsibilities into Momo,
Holocene, or Bloodbank depending on which document is read:

- Momo is described as an "Agentic Ticketing Workflow and Project Lifecycle
  System" and its workflow directs Momo/Hermes to calculate ticket state and write
  provider transitions.
- Holocene carries a project-local workflow that calls itself the lifecycle
  execution engine and directly transitions Plane tickets.
- Bloodbank contains the only tested deterministic lifecycle controller, including
  state/history tables, reconciliation, leases, blockers, gates, checkpoints,
  observations, and a transactional outbox.

This is an authority error, not a missing greenfield idea. The approved target is a
separate headless `lifecycle` component. It owns the lifecycle specification,
operational lifecycle state, deterministic reconciliation, legal frontier,
obligations, and capability validation. Momo remains the intelligent PM/EM process
manager that chooses among legal work and delegates execution. Holocene remains a
renderer and high-level command surface.

### Trigger and discovery context

The trigger is Team Moirai's approved `lifecycle-component` boundary correction on
parent branch `epic/lifecycle-component`. No root epics or story artifact exists in
the current checkout. Momo's current epics are therefore the affected epic set, and
the missing root epic/story ledger is recorded as a planning gap rather than used as
a reason to halt.

The issue was discovered by comparing current planning prose with live code and
tests. Runtime evidence outranks the older product labels.

### Evidence at the pinned revisions

- Root gitlink: Bloodbank `03415705a39d77f1e6d73c8a9c92ee177320df7e`.
- `services/lifecycle-controller/src/reconciler.py` implements a pure evaluator and
  deterministic state fingerprinting. It produces `active`, `waiting`, `blocked`,
  `stalled`, and `degraded` outcomes from observations, gates, blockers, and
  sentinel health.
- `src/db/repository.py` uses a leased dirty queue and atomically writes current
  state, append-only status history, and outbox rows.
- The pinned focused suite passes: `21 passed`; Ruff passes.
- Bloodbank's schema validator passes all 72 registered schema files, but that does
  not validate emitted controller payloads against every intended contract.
- `OutboxPublisher._default_publish()` raises `RuntimeError("outbox publisher is not
  configured")`; tests prove the row remains unpublished and records the failure.
- The reconciler emits `bloodbank.v1.lifecycle.blocker.detected`, but no matching
  schema exists under `schemas/bloodbank/v1/lifecycle/`.
- The existing `status.updated` schema requires a non-empty `data.repo` and an
  object `data.previous`; the reconciler can stage `repo: ""` and `previous: null`
  on first reconciliation.
- The controller is absent from the integrated Compose model. Its runbook calls the
  real publisher, real sentinels, and Compose wiring follow-up work.
- Momo has a proven process skill but no standalone product implementation in its
  repository. Its current direct-board transition loop is a legacy process path,
  not lifecycle authority.
- Holocene's live code is a transient dashboard/API projection over systemd,
  runtime files, Redis, Prometheus, Traefik, and Candystore. Its Bloodbank client is
  a stub; there is no deployed lifecycle read or command integration.

## 2. Correct Course Checklist Disposition

Legend: `[x]` done, `[N/A]` not applicable, `[!]` implementation follow-up.

### 1. Understand the Trigger and Context

- `[x] 1.1` Triggering work identified: Team Moirai's approved
  `lifecycle-component` epic/branch correction. Root story ID is absent and recorded
  as a planning gap; Momo's epics are used for impact analysis.
- `[x] 1.2` Core problem defined as a misunderstanding of component authority
  exposed during brownfield implementation review. Lifecycle truth is currently
  claimed by multiple clients while the tested embryo lives inside Bloodbank.
- `[x] 1.3` Supporting evidence collected from pinned code, SQL, tests, schemas,
  runbook, root docs, Momo planning/skill docs, and Holocene design/workflow docs.

### 2. Epic Impact Assessment

- `[x] 2.1` Momo's current MVP cannot be completed as originally phrased because it
  authorizes direct transition/state computation and assumes shared board state is
  lifecycle truth.
- `[x] 2.2` Momo epics require a new authority gate and lifecycle-client stories;
  direct board mutation becomes a temporary legacy path, not the target contract.
- `[x] 2.3` All remaining Momo epics were reviewed. Promotion, demo, autonomous twin,
  heartbeat, and MCP work all depend on the headless lifecycle read/command seam.
- `[x] 2.4` No product-value epic becomes obsolete, but state-machine ownership
  inside Momo/Hermes/Holocene is superseded. New extraction, contract, migration,
  projection, and client-integration work is required.
- `[x] 2.5` Resequencing is required: contract and lifecycle vertical slice precede
  Momo autonomy, Holocene commands, and deployment claims.

### 3. Artifact Conflict and Impact Analysis

- `[x] 3.1` Root PRD conflicts found in component roles and ambiguous use of
  "lifecycle" for both product state and Compose process ownership. The local MVP
  remains achievable, but the standalone lifecycle slice is added as a prerequisite
  for autonomous project management.
- `[x] 3.2` Root architecture conflicts found in authority, data ownership, event
  contracts, integration order, and missing component/runtime boundaries.
- `[x] 3.3` Holocene UX impact assessed. Lifecycle state must be rendered with source,
  state version, observation freshness, blockers, obligations, and legal commands.
  The UI must never infer authoritative state from color, ticket columns, or stale
  local files.
- `[x] 3.4` Secondary artifacts assessed: root governance/deployment docs, Momo
  product planning and process skill, Holocene design and custom workflow copies,
  Bloodbank schemas/outbox wiring, Candystore read models, PJangler identity, root
  Compose, migration/rollback, tests, and observability.

### 4. Path Forward Evaluation

- `[x] 4.1` **Direct Adjustment: viable only as a Major replan.** Existing controller
  code and Momo value are retained, while ownership and sequencing change. Effort:
  High. Risk: Medium if history and schema gates are enforced; High otherwise.
- `[x] 4.2` **Potential Rollback: not viable.** No deployed standalone lifecycle
  service exists to roll back, and discarding the tested Bloodbank embryo would lose
  useful behavior and history. Effort: Medium. Risk: High.
- `[x] 4.3` **MVP Review: viable and required.** The product goal remains, but Momo
  autonomy and Holocene command work move behind the lifecycle vertical slice. Effort:
  High. Risk: Medium.
- `[x] 4.4` **Selected approach: Hybrid of Direct Adjustment and MVP Review.** Extract
  and extend the tested embryo, preserve its history, correct contracts, then migrate
  clients. This maximizes reuse without preserving the wrong ownership boundary.

### 5. Sprint Change Proposal Components

- `[x] 5.1` Issue summary is evidence-backed and blame-free.
- `[x] 5.2` Epic and artifact impacts are enumerated in this proposal and reflected
  in the reconciled artifacts.
- `[x] 5.3` Recommended path and rejected rollback are documented with trade-offs.
- `[x] 5.4` MVP impact and sequenced implementation plan are defined below.
- `[x] 5.5` Handoff roles are explicit: PM/Architect for replan, lifecycle team for
  extraction, Bloodbank for contracts/transport, Candystore for history/read models,
  Momo and Holocene owners for clients, PJangler for identity, root platform for
  deployment gates.

### 6. Final Review and Handoff

- `[x] 6.1` All checklist sections were completed. Implementation items remain
  intentionally marked as handoff work, not documentation completion claims.
- `[x] 6.2` Proposal checked against pinned live evidence and current/target state
  is distinguished throughout.
- `[x] 6.3` Explicit user approval was supplied before execution and is recorded at
  the top of this proposal.
- `[N/A] 6.4` No `sprint-status.yaml` exists, and no root epics/stories were added or
  renumbered in a sprint ledger. Momo's epics are reconciled in place.
- `[x] 6.5` Next steps, responsibilities, order, and success criteria are defined
  below. Team Moirai receives the implementation handoff.

## 3. Impact Analysis

### Epic and story impact

Momo's Gate and Epics E0-E6 remain recognizable, but their authority contract
changes:

1. Add a lifecycle authority gate before Momo's install/demo/autonomy work.
2. Make project identity a PJangler input and lifecycle binding a lifecycle-owned
   record.
3. Replace "Momo computes/reconciles/transitions state" with "Momo reads the
   authoritative snapshot/frontier, selects among legal work, and submits intent."
4. Keep delegation, independent review, evidence capture, business prioritization,
   and decision provenance in Momo.
5. Treat direct `tp`/Trello state transitions as temporary legacy behavior that
   cannot be called the target lifecycle path.
6. Gate the autonomous twin and high-level MCP commands on capability validation,
   optimistic state versioning, idempotency, and lifecycle command responses.

### Artifact conflicts

| Artifact | Conflict | Required correction |
|---|---|---|
| Root PRD | No standalone lifecycle authority; ambiguous Compose "lifecycle owner" | Add lifecycle requirement and use "process owner" for Compose |
| Root architecture | Momo governs execution; Bloodbank implicitly owns lifecycle semantics | Add explicit six-way authority split and extraction state |
| Momo planning | Momo is called lifecycle system and writes state | Recast as intelligent process manager and lifecycle client |
| Momo skill/workflow | Direct board state is treated as reconciliation truth | Mark current path legacy; target reads frontier and submits commands |
| Holocene workflow | Holocene repo workflow claims execution/state transition authority | Make it a client workflow and keep dashboard read/command-only |
| Bloodbank docs | Controller described as Bloodbank runtime component | Describe current embryo and target extraction; retain schema/transport ownership |
| Candystore docs | Shared DB can imply state ownership | Limit authority to event history/read projections |
| PJangler docs | Registry carries lifecycle-looking status | Limit authority to project/bootstrap identity and binding inputs |
| Deployment docs | Current Compose can be read as hosting lifecycle | State that no standalone lifecycle service is deployed or gated yet |

### Technical impact

The correction requires a new repository/service and contract surface. It also
requires a history-preserving extraction of the Bloodbank controller, not a rewrite.
The existing controller does not yet implement the complete target: legal frontier,
obligations, capability grants, a production command surface, configured outbox
publication, schema-complete events, or deployed wiring remain implementation work.

## 4. Detailed Before-to-After Proposals

### Product boundary

**Before**

> Momo is the Project Lifecycle System; Momo/Hermes reconciles the board and writes
> provider state. Holocene workflow code can also drive the same state machine.

**After**

> `lifecycle` is the only authority for lifecycle spec, state, reconciliation,
> frontier, obligations, and capability validation. Momo chooses among legal work
> and submits intent. Holocene renders state and submits high-level commands.

**Rationale:** Business judgment and UI interaction are clients of deterministic
state, not competing writers of it.

### Bloodbank

**Before**

> Bloodbank contains event transport/contracts and the lifecycle controller service.

**After**

> Bloodbank owns transport and canonical schemas/contracts. The existing controller
> directory is the tested extraction embryo and historical source. Lifecycle semantic
> ownership moves to the standalone component after contract closure and migration.

**Rationale:** The event bus should not also own domain state solely because the first
implementation was incubated there.

### Candystore

**Before**

> Lifecycle operational tables live in the Candystore PostgreSQL database used by the
> Bloodbank demo, which can be mistaken for Candystore domain ownership.

**After**

> The lifecycle component owns its operational store and migration. Candystore owns
> durable Bloodbank event history and query/read models. Physical co-location during a
> migration window does not transfer semantic ownership.

### PJangler

**Before**

> Registry/project projections include lifecycle-looking status and reconciliation
> settings that can be read as lifecycle truth.

**After**

> PJangler owns stable project/bootstrap identity and emits the binding inputs needed
> to create or locate a lifecycle. Lifecycle state and progress fields are projections
> only when sourced from the lifecycle component.

### Momo

**Before**

> Momo selects a ticket, transitions it directly, mirrors the state machine, computes
> staleness, and decides closure.

**After**

> Momo reads `state_version`, legal frontier, blockers, obligations, and capability
> grants; applies business pillars to choose among eligible actions; submits an
> idempotent intent; delegates work/review; and returns observations/evidence. It never
> calculates or writes lifecycle truth. Momo decision events explain judgment but do
> not enact state transitions.

### Holocene

**Before**

> Holocene project workflows and Hermes docs call themselves the lifecycle execution
> engine and authorize direct ticket transitions/closure.

**After**

> Holocene renders authoritative lifecycle snapshots/read models and exposes a small
> high-level command surface. Commands are accepted or rejected by `lifecycle`; the UI
> renders the resulting authoritative state. Local heuristics are display hints only.

### UI/UX

**Before**

> Ticket velocity, sentinel files, and board columns can look authoritative even when
> inputs are stale or Candystore reads fail silently.

**After**

> Lifecycle panels show source, state version, reconciled time, observation freshness,
> frontier, obligations, blockers/gates, and command outcome. Missing data is shown as
> unknown/degraded, never as an empty healthy state.

## 5. Recommended Approach

Use a history-preserving extraction and strangler migration:

1. **Freeze the boundary and vocabulary.** Define lifecycle IDs, spec version,
   state version, commands, events, frontier, obligations, capability grants, and
   idempotency rules. PJangler identity is an input, not lifecycle state.
2. **Close Bloodbank contract drift.** Register every emitted command/event, make
   payloads validate, and decide the first-state `previous` contract. Configure a real
   publisher adapter behind the transactional outbox.
3. **Extract with history.** Create the standalone repository from the Bloodbank
   controller directory while preserving commit provenance. Move the pure evaluator,
   repository tests, SQL, worker/sweeper, and dogfood evidence as the starting point.
4. **Extend the embryo.** Add versioned lifecycle specs, deterministic legal frontier,
   obligation evaluation, capability validation, optimistic command handling, and
   idempotent command results.
5. **Migrate operational data safely.** Back up current lifecycle tables; compare row
   counts, primary keys, state fingerprints, status history, and outbox publication
   state; cut over a single writer; retain a documented rollback checkpoint.
6. **Wire Bloodbank and Candystore.** Lifecycle publishes canonical events through
   Bloodbank; Candystore persists history and exposes read projections without writing
   lifecycle state.
7. **Migrate clients.** Momo adopts snapshot/frontier/command APIs before direct board
   transitions are retired. Holocene adopts read models and high-level commands. Legacy
   direct paths remain visibly non-authoritative until removed.
8. **Deploy and gate.** Add exactly one lifecycle service to the root platform only
   after image, storage, health, migration, contract, replay, and rollback gates pass.

### Effort, risk, and timeline impact

- **Effort:** High. This crosses contracts, data, service extraction, two clients, and
  deployment governance.
- **Primary risks:** history loss, dual writers, schema-incompatible events, stale UI
  presented as truth, Momo bypassing the command seam, and accidental claims that the
  planned service is already deployed.
- **Risk controls:** immutable source pin, backup/checksum evidence, single-writer gate,
  schema validation of real envelopes, deterministic golden tests, command idempotency,
  state-version preconditions, and explicit current/target labels.
- **Timeline impact:** Momo autonomous lifecycle behavior and Holocene lifecycle commands
  move behind the lifecycle vertical slice. Existing dashboard/process behavior may
  continue as legacy operation but cannot satisfy the new target acceptance criteria.

## 6. Implementation Handoff

### Classification and recipients

This is a **Major** change. Route the implementation to Team Moirai's Product Manager /
Solution Architect and lifecycle implementation lead.

| Owner | Responsibility |
|---|---|
| PM / Architect | Keep authority boundaries and sequencing consistent across backlog and architecture |
| Lifecycle component | Extract/extend evaluator, own operational state, commands, frontier, obligations, capability validation |
| Bloodbank | Own canonical schemas, envelopes, subjects, NATS/Dapr transport, publisher adapter |
| Candystore | Persist canonical events and expose durable history/read models |
| PJangler | Provide stable project/bootstrap identity and lifecycle binding inputs |
| Momo | Select among lifecycle-legal work, submit intents, delegate/review, emit decision rationale |
| Holocene | Render lifecycle read models and expose high-level commands only |
| Root platform | Add image/storage/deployment/drift gates after the vertical slice is proven |

### Sequencing constraints

- Do not deploy Momo/Hermes autonomy against the target model before the lifecycle
  command and capability-validation seam exists.
- Do not add Holocene lifecycle mutations that write a provider or database directly.
- Do not delete or rewrite Bloodbank controller history during extraction.
- Do not claim Candystore event history is the operational lifecycle store.
- Do not add the planned service to the validated Compose set until migration and
  rollback acceptance evidence exists.

### Success criteria

1. Exactly one component writes lifecycle state.
2. Identical ordered inputs and spec version produce identical state fingerprint,
   frontier, obligations, and command verdicts.
3. Every lifecycle command/event validates against a registered Bloodbank contract;
   no producer emits an unregistered type.
4. Outbox publication reaches Bloodbank and failed publication remains retryable and
   observable without losing the committed state transition.
5. Existing lifecycle rows and append-only history survive extraction with verified
   counts, identifiers, fingerprints, and timestamps.
6. Candystore persists the canonical lifecycle event stream and can rebuild/read the
   supported projections.
7. Momo can select only from the authoritative frontier; an illegal or stale-version
   intent is rejected without state mutation.
8. Holocene displays state provenance/freshness and sends commands without computing
   the resulting lifecycle state.
9. PJangler project identity resolves deterministically to the intended lifecycle.
10. Root deployment proves one healthy lifecycle instance, migration/rollback gates,
    and no legacy dual writer.

## 7. Completion and Remaining Work

This Correct Course deliverable reconciles planning and documentation only. It does not
implement, deploy, or cut over the lifecycle vertical slice. The next logical work is the
contract-first lifecycle extraction epic described above, beginning with Bloodbank schema
closure and a history-preserving repository extraction plan.
