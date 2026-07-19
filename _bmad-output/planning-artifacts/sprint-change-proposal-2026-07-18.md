# Sprint Change Proposal: Lifecycle Component Boundary Correction

**Date:** 2026-07-18

**Project:** 33GOD

**Status:** Implemented and verified in the local vertical slice
**Approval:** Jarad approved the Lifecycle component boundary correction before
implementation.

## 1. Corrected boundary

The pre-correction planning set assigned project-lifecycle behavior to Momo,
Holocene, or the Bloodbank controller depending on the document. That was an
authority error.

The approved and now implemented model has a separate headless `lifecycle`
component. Lifecycle alone owns:

- deterministic specification and materialized state;
- legal transitions and guards, modes, reconcile, and fingerprinting;
- legal frontier, obligations, blockers, and gates;
- actor capabilities/grants;
- idempotency and expected-state versioning; and
- every state-changing lifecycle write.

The six supporting ownership boundaries remain independent:

| Concern | Owner |
|---|---|
| Project/bootstrap identity and binding inputs | PJangler |
| Lifecycle semantic authority and operational writes | Lifecycle |
| Canonical schemas and NATS/Dapr transport | Bloodbank |
| Append-only event history and read projections | Candystore |
| Legal-work ranking, delegation, evidence, and invocation intent | Momo |
| Rendering and high-level command initiation | Holocene |
| Process topology, pins, profiles, and release gates | 33GOD root |

Root process ownership is not lifecycle semantic ownership. Momo/Hermes and
Lifecycle do not drive the same reconcile loop.

## 2. Implemented outcome

### Runtime and contracts

- Lifecycle runtime source:
  `719e6af0f06f1bdb30937326380ac67581e8dbb8`
- Lifecycle runtime image:
  `ghcr.io/delorenj/lifecycle@sha256:754d04488d57968824d1ddb077ae50eef758f4fad27bf0899c52c6df11d03311`
- Bloodbank contract/transport revision:
  `48031ee39c238b9d4715b81b74076635235f96d5`
- Lifecycle authority/integration revision:
  `719e6af0f06f1bdb30937326380ac67581e8dbb8`

Root Compose references the immutable image digest and contains no Lifecycle
build key. A dedicated PostgreSQL database, secret, volume, and private network
is separated from Candystore. One-shot migration must succeed before
deterministic bootstrap, and bootstrap plus healthy PostgreSQL/NATS/JetStream
must succeed before serve.

### Candystore read model

Candystore revision
`b1f6fda3739d095535b326cc89b9a6c7823f63d8` provides:

- an operationally durable lifecycle consumer;
- replay receipts and idempotent/version-ordered projection updates, including
  canonical persisted-row replay when a duplicate ID conflicts with its input;
- lifecycle/project identity, spec/state versions, authority state,
  fingerprint, provenance, freshness/as-of, frontier, obligations,
  blockers/gates, and stable verdicts; and
- explicit unknown/degraded behavior for missing or stale observations.

Candystore exposes no operational Lifecycle mutation endpoint.

### Momo obligation-to-skill seam

Momo revision
`9e3a67a36b3dfe09b4061029d7b52eab39f4d011`:

- consumes authoritative snapshots/frontier/obligations;
- ranks only legal frontier commands while servicing pending obligations as
  directly correlated actor work rather than borrowing unrelated transitions;
- resolves obligation skill references through the canonical Momo skill
  contract;
- emits decision rationale separately from state-changing intent; and
- publishes canonical agent invocation, exact completion evidence, and
  Lifecycle commands through Bloodbank.

Every state-changing command carries actor, capability/grant, idempotency,
`expected_state_version`, correlation, and causation context. Momo has no
direct Lifecycle, Candystore, provider, or local-truth write path.

### Holocene client surface

Holocene revision
`544ca73f4cc75ef98956873b11085216af12a297`:

- reads Candystore's Lifecycle projection;
- renders identity, versions, provenance/freshness, status/health/phase/
  fingerprint, frontier, obligations, blockers/gates, and stable verdicts;
- renders missing/stale inputs unknown/degraded; and
- publishes schema-exact high-level Lifecycle commands through Bloodbank
  without optimistic local mutation; invalid/missing frontier actions and
  incomplete gate resolutions fail before publication.

The surface follows existing API/web conventions and has focused API, client,
command-envelope, and responsive UI tests.

## 3. Executed failure-proof matrix

The root isolated live gate exercises the exact immutable Lifecycle image using
a unique Compose project, caller-selected free ports, and uniquely named
networks/volumes. It proves:

1. Holocene offline does not halt Lifecycle truth progression.
2. Momo offline does not corrupt or rewrite truth.
3. Lifecycle restart catches up committed observations/outbox work
   deterministically without duplicate transition effects.
4. Stale `expected_state_version` is rejected without mutation.
5. Missing/invalid capability is rejected without mutation.
6. A canonical authority transaction commits state and exact ordered outbox
   rows during NATS outage; recovery publishes those IDs in order and drains
   them without a duplicate transition effect.
7. Dedicated PostgreSQL persistence survives Lifecycle and database process
   restarts.

The same run proves authoritative events and baseline verdicts replay to a
late-starting Candystore, conflicting duplicate IDs project only the canonical
stored row, and spoofed authority candidates remain auditable but excluded.
Pending obligations reject pre-activation and prior-occurrence evidence until
exact active-occurrence completion arrives; repeated occurrences stay
isolated. Versioned grants and real causal lineage flow authority-to-client
through Momo invocation/completion and Holocene render/command seams. Cleanup
targets only resources created by that unique run.

## 4. Publication record

Component feature refs are published before the root gitlink update:

| Component | Branch | Revision |
|---|---|---|
| Bloodbank | `feature/moirai-lifecycle-capability-contract-20260718` | `48031ee39c238b9d4715b81b74076635235f96d5` |
| Lifecycle | `fix/trusted-publication-reconcile-time-20260719` | `719e6af0f06f1bdb30937326380ac67581e8dbb8` |
| Candystore | `feature/moirai-lifecycle-projection-20260718` | `b1f6fda3739d095535b326cc89b9a6c7823f63d8` |
| Momo | `feature/moirai-lifecycle-client-20260718` | `9e3a67a36b3dfe09b4061029d7b52eab39f4d011` |
| Holocene | `feature/moirai-lifecycle-surface-20260718` | `544ca73f4cc75ef98956873b11085216af12a297` |

Each ref was fetched and checked out from anonymous credential-disabled HTTPS,
matched its exact revision, and contained its approved component base.

## 5. Current versus remaining work

This proposal's local Lifecycle authority slice is complete. Current invariants
remain release gates: exactly one lifecycle writer, Bloodbank-only
inter-service traffic, durable read-side history, legal-frontier-only Momo
selection, and renderer-only Holocene behavior.

The cloud profile, production rollout, root integration publication, and final
release tag are separate future decisions. They are not implied by local
Compose or this implementation record.
