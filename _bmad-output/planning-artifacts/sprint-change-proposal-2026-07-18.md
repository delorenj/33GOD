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
  `715ab2ea62bcece488c8d6029869af8d3651c39a`
- Lifecycle runtime image:
  `ghcr.io/delorenj/lifecycle@sha256:e391a8aab13ca582e2026846a268a6a228c7b63c25e5d469255572e4b2988526`
- Bloodbank contract/transport revision:
  `cce08181ed9f6de8dd24f058b93d0dd9cda9f2bf`
- Lifecycle integration-document revision:
  `434a1674d35b15aafb38d2d7a022d996ca3ad805`

Root Compose references the immutable image digest and contains no Lifecycle
build key. A dedicated PostgreSQL database, secret, volume, and private network
is separated from Candystore. One-shot migration must succeed before
deterministic bootstrap, and bootstrap plus healthy PostgreSQL/NATS/JetStream
must succeed before serve.

### Candystore read model

Candystore revision
`a54389f121c2ee24052f94fb14bc0ecc811b1dce` adds:

- an operationally durable lifecycle consumer;
- replay receipts and idempotent/version-ordered projection updates;
- lifecycle/project identity, spec/state versions, authority state,
  fingerprint, provenance, freshness/as-of, frontier, obligations,
  blockers/gates, and stable verdicts; and
- explicit unknown/degraded behavior for missing or stale observations.

Candystore exposes no operational Lifecycle mutation endpoint.

### Momo obligation-to-skill seam

Momo revision
`aae900f37de3a15bb4b69c48e61cc87d286526ea`:

- consumes authoritative snapshots/frontier/obligations;
- rejects non-frontier or otherwise illegal work;
- resolves obligation skill references through the canonical Momo skill
  contract;
- emits decision rationale separately from state-changing intent; and
- publishes canonical agent invocation plus Lifecycle command/evidence through
  Bloodbank.

Every state-changing command carries actor, capability/grant, idempotency,
`expected_state_version`, correlation, and causation context. Momo has no
direct Lifecycle, Candystore, provider, or local-truth write path.

### Holocene client surface

Holocene revision
`e1a8141a4f100745512b3bcfdd2e36ad9e9937ea`:

- reads Candystore's Lifecycle projection;
- renders identity, versions, provenance/freshness, status/health/phase/
  fingerprint, frontier, obligations, blockers/gates, and stable verdicts;
- renders missing/stale inputs unknown/degraded; and
- publishes complete high-level Lifecycle commands through Bloodbank without
  optimistic local mutation.

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
6. NATS outage/recovery preserves committed state, per-lifecycle publication
   order, and eventual publication.
7. Dedicated PostgreSQL persistence survives Lifecycle and database process
   restarts.

The same run proves durable Candystore replay/read-only behavior, canonical
Momo skill invocation, Holocene render/command fidelity, and desktop/mobile
rendering. Cleanup targets only resources created by that unique run.

## 4. Publication record

Component feature refs are published before the root gitlink update:

| Component | Branch | Revision |
|---|---|---|
| Candystore | `feature/moirai-lifecycle-projection-20260718` | `a54389f121c2ee24052f94fb14bc0ecc811b1dce` |
| Momo | `feature/moirai-lifecycle-client-20260718` | `aae900f37de3a15bb4b69c48e61cc87d286526ea` |
| Holocene | `feature/moirai-lifecycle-surface-20260718` | `e1a8141a4f100745512b3bcfdd2e36ad9e9937ea` |
| Lifecycle docs | `feature/moirai-lifecycle-integration-docs-20260718` | `434a1674d35b15aafb38d2d7a022d996ca3ad805` |

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
