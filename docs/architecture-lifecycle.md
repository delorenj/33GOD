# Planned Lifecycle Architecture

**Decision date:** 2026-07-18

**Status:** Approved target; standalone repository/service not implemented

## Purpose

`lifecycle` is the headless authority for deterministic project lifecycle
semantics. It owns the versioned lifecycle specification, operational state,
reconciliation, legal frontier, obligations, blockers, gates, checkpoints, and
capability validation. Every state-changing client submits intent; Lifecycle
decides whether that intent is legal and commits the resulting state.

## Current Evidence

The starting implementation exists inside Bloodbank at pinned revision
`03415705a39d77f1e6d73c8a9c92ee177320df7e` under
`services/lifecycle-controller/`.

Implemented and tested there:

- pure lifecycle evaluation and deterministic state fingerprinting;
- state/health verdicts for active, waiting, blocked, stalled, and degraded;
- observation aggregation, blockers, gates, and checkpoints;
- leased dirty reconcile queue plus periodic sweeper;
- atomic current-state, append-only history, and outbox writes;
- an outbox retry loop and a repeatable Drumjangler dogfood fixture; and
- 21 passing focused tests plus passing Ruff checks.

This is an embryo, not the complete target. Current gaps include:

- no standalone repository, package, image, service, or root Compose entry;
- no configured Bloodbank NATS/Dapr outbox publisher;
- no registered `bloodbank.v1.lifecycle.blocker.detected` schema;
- `status.updated` creation can stage empty `repo` and null `previous` values
  that conflict with its schema;
- no versioned lifecycle spec or command surface;
- no computed legal frontier, obligations, or capability grants; and
- operational tables currently live in the PostgreSQL instance used by the
  Bloodbank/Candystore demo path.

## Authority Boundary

| Concern | Owner |
|---|---|
| Project/bootstrap identity and binding inputs | PJangler |
| Lifecycle spec, state, reconciliation, frontier, obligations, capability validation | Lifecycle |
| Canonical command/event schemas and NATS/Dapr transport | Bloodbank |
| Durable event history and query/read projections | Candystore |
| Business prioritization, delegation, and review process | Momo |
| Dashboard rendering and high-level commands | Holocene |
| Integrated process deployment and release gates | 33GOD root platform |

Physical database co-location during migration does not transfer semantic
ownership. Candystore may store lifecycle events and read projections, but only
Lifecycle writes operational lifecycle state.

## Read Model

An authoritative snapshot must carry at least:

- lifecycle and project identity;
- lifecycle `spec_version` and `state_version`;
- current status, health, phase, and deterministic fingerprint;
- last reconcile time plus observation source/freshness;
- current blockers and gates;
- legal frontier with reason codes;
- outstanding and satisfied obligations; and
- capability grants relevant to the requesting actor.

Consumers must render missing/stale inputs as unknown or degraded. An empty
projection is not evidence of healthy zero work.

## Command Model

Every state-changing command includes:

- lifecycle ID and actor identity;
- requested intent;
- expected `state_version`;
- idempotency key;
- asserted capability/grant context; and
- correlation/causation metadata required by Bloodbank.

Lifecycle returns a stable accepted/rejected/already-applied verdict. It rejects
illegal frontier choices, stale versions, missing capability, and malformed
commands without mutating state.

Accepted commands commit state, append-only history, and the outbox record in
one transaction. Publication can retry independently; a transport failure
cannot erase the committed transition.

## Client Rules

- **Momo** reads the legal frontier and obligations, applies the operator's
  business pillars to rank legal candidates, submits intent, and delegates
  implementation/review. Its decision events record reasoning only.
- **Holocene** renders the authoritative snapshot and submits high-level
  commands. It does not derive state from board columns, colors, local files,
  or button clicks.
- **PJangler** supplies stable project/bootstrap identity. Registry status is a
  projection when sourced from Lifecycle.
- **Bloodbank** validates and transports contracts without interpreting domain
  state.
- **Candystore** persists events and serves read projections without becoming a
  write path.

## Extraction and Cutover

1. Freeze lifecycle vocabulary, IDs, versions, commands, events, frontier,
   obligations, and capability semantics.
2. Create the standalone repository from the Bloodbank controller path while
   preserving commit provenance.
3. Register and validate every lifecycle command/event in Bloodbank; configure
   the outbox publisher.
4. Add deterministic frontier, obligation, capability, and idempotent command
   behavior with golden parity tests for the existing evaluator.
5. Back up current operational tables and record counts, keys, fingerprints,
   history ordering, and outbox publication state.
6. Migrate data, prove one writer, compare the migrated evidence, and retain a
   rollback checkpoint.
7. Wire Candystore projections, then Momo and Holocene clients.
8. Add exactly one Lifecycle service to root Compose only after image, health,
   migration, replay, contract, and rollback gates pass.

## Acceptance

- Exactly one component can write lifecycle state.
- Same ordered inputs and spec version produce the same state fingerprint,
  frontier, obligations, and command verdict.
- Every emitted contract is registered and validates as a complete Bloodbank
  envelope.
- Existing state/history survives extraction with verified evidence.
- Failed event publication remains retryable and observable.
- Momo cannot select work outside the authoritative frontier.
- Holocene renders provenance/freshness and cannot write state directly.
- Root deployment proves one healthy instance and no legacy dual writer.
