# Lifecycle Architecture

**Decision date:** 2026-07-18

**Implementation state:** Current local vertical slice, verified against the
immutable runtime image

## Runtime pin

- Runtime image:
  `ghcr.io/delorenj/lifecycle@sha256:f15d5934d1007f83fe46348a059c59ade8262dbd3b067f629633d28693843abf`
- Image source and gitlink revision:
  `eefc35388125a016dc2b2c905950fd8a2981322d`
- Bloodbank contract revision:
  `155f2d774964d1c73694ce2c576fe5f50b91eefb`

Root Compose references only the immutable digest. It never rebuilds Lifecycle
and has no Lifecycle build or local-image substitution.

## Sole authority

Lifecycle alone owns the versioned specification, operational state,
deterministic reconcile, legal transitions and guards, modes, frontier,
obligations, blockers and gates, actor capabilities, idempotency,
`expected_state_version`, deterministic fingerprints, and all state-changing
writes.

The surrounding ownership split is:

| Concern | Owner |
|---|---|
| Project/bootstrap identity and binding inputs | PJangler |
| Lifecycle semantics and operational writes | Lifecycle |
| Canonical command/event schemas and NATS/Dapr transport | Bloodbank |
| Append-only event history and read projections | Candystore |
| Legal-work ranking, delegation, evidence, and invocation intent | Momo |
| Read rendering and high-level command initiation | Holocene |
| Process topology, immutable pins, profiles, and gates | 33GOD root |

Database location never transfers semantic ownership. Lifecycle has an isolated
PostgreSQL authority database; Candystore has separate storage and credentials.

## Process topology

Root Compose starts a healthy dedicated PostgreSQL service, runs
`python -m main migrate` once, runs deterministic `python -m main bootstrap`
once, then runs `python -m main serve`. Migration or bootstrap failure prevents
serve. Serve also waits for healthy NATS and successful canonical JetStream
initialization. Readiness checks database and Bloodbank connectivity; liveness
remains available during a broker outage.

Lifecycle commits state, append-only history, and outbox rows transactionally.
Publication retries after transport recovery without undoing the committed
transition or duplicating its effect.

## Read contract

Candystore's durable JetStream consumer projects canonical lifecycle events
idempotently and in version order. The read model retains:

- lifecycle and project identity;
- `spec_version`, `state_version`, status, health, phase, and fingerprint;
- provenance/source observation and observation as-of/freshness;
- legal frontier and obligations;
- blockers and gates; and
- stable command verdicts.

Missing or stale observations are represented as unknown/degraded, never as an
empty healthy state. Candystore exposes no operational lifecycle mutation
endpoint.

## Command contract

Every state-changing command carries:

- lifecycle ID and actor identity;
- capability/grant context;
- idempotency key;
- `expected_state_version`;
- correlation and causation identifiers; and
- the canonical Bloodbank envelope and subject.

Lifecycle returns stable applied, stale, unauthorized, illegal, or duplicate
verdicts. A stale version, invalid versioned capability, or transition blocked
by a pending obligation is rejected without mutation. Snapshot v2 carries each
grant's required `capability_version`; clients consume that authoritative value.

In `waiting`, the independent-review obligation is computed before the legal
frontier. `waiting -> active` is disallowed while that obligation is pending.
An invocation or review request is not satisfaction: only the canonical
Bloodbank completion-evidence event with matching lifecycle, obligation,
target actor, skill reference, and completed artifact evidence can satisfy it.
Lifecycle records that observation and alone performs the resulting reconcile.

Momo reads only the authoritative projection, filters and ranks the legal
frontier, resolves an obligation's canonical skill reference, emits decision
rationale separately from invocation/command intent, and publishes through
Bloodbank. Holocene reads the Candystore projection and publishes high-level
commands through Bloodbank. Neither client derives, persists, or optimistically
mutates lifecycle truth.

## Executed failure matrix

The isolated gate in
`33god-platform/scripts/verify-lifecycle-live.py` exercises the exact digest
with unique ports, networks, and volumes. It proves:

1. Holocene offline does not halt Lifecycle transitions.
2. Momo offline does not corrupt or rewrite truth.
3. Lifecycle restart catches up committed observations/outbox work without a
   duplicate transition effect.
4. Stale `expected_state_version` is rejected without mutation.
5. Missing or invalid capability is rejected without mutation.
6. NATS outage preserves committed state and per-lifecycle outbox order;
   recovery eventually publishes all rows.
7. The dedicated PostgreSQL volume survives Lifecycle and PostgreSQL process
   restarts.

The same run starts Candystore only after authority snapshot and verdict events
exist, proves their durable replay, attempts a conflicting duplicate ID and
proves projection from the canonical stored envelope, exercises pending
obligation rejection and exact completion-evidence unlock, verifies versioned
capabilities, and checks Momo/Holocene client fidelity. Cleanup addresses only
the unique resources allocated by the run.

## Current versus future

Current: the local authority topology, three client seams, immutable image pin,
semantic gates, and isolated failure matrix are implemented. Future: a separate
hosted/cloud design, production rollout decision, release promotion, and any
additional lifecycle domains. The cloud profile is intentionally unsupported.
