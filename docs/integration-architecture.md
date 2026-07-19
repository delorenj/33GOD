# 33GOD Integration Architecture

**Current state:** Lifecycle local vertical slice implemented and verified on
2026-07-18.

## Authority model

Executable manifests, pinned code, contracts, and tests outrank prose. Root owns
cross-component topology and release gates; each component owns its internals.
Project lifecycle authority remains separate from process deployment ownership.

```text
PJangler identity/binding inputs
              |
              v
observations/evidence -> Lifecycle authority <--- canonical command intent
                         | state/frontier/obligations/grants
                         | transactional state/history/outbox
                         v
                 Bloodbank NATS/JetStream
                         |
              +----------+----------+
              |                     |
              v                     v
     Candystore history       command/reply transport
        + read projection            |
              |                      |
        +-----+------+               |
        |            |               |
        v            v               |
 Momo ranks      Holocene renders     |
 legal work      and initiates        |
        \            /               |
         +-- canonical intents -------+
```

No direct service-to-service mutation path exists. Momo and Holocene publish
through Bloodbank; Lifecycle alone validates and commits resulting state.

## Root process graph

```text
bloodbank-nats healthy -> nats-init complete ------------------+
        |                                                       |
        +-> dapr-placement                                      |
                                                                v
lifecycle-postgres healthy -> migrate -> bootstrap -> Lifecycle ready
        |
        +-- dedicated lifecycle-pgdata on lifecycle-internal

candystore-postgres healthy -> Candystore ready -> durable daprd
                                      |
                                      +-> host Holocene API
                                              |
                                      preflight complete -> Holocene web
```

Lifecycle uses only its private database network and Bloodbank. Candystore uses
its own database/network and joins Bloodbank through its Dapr sidecar. Holocene
does not join the Lifecycle authority network.

## Contract matrix

| Concern | Owner | Exercised integration |
|---|---|---|
| Identity/binding inputs | PJangler | Deterministic input to bootstrap/spec |
| Lifecycle state/reconcile/frontier/obligations/grants | Lifecycle | Exact digest, dedicated PostgreSQL, sole writer |
| Commands/events/transport | Bloodbank | Pinned `48031ee…` schemas and initialized JetStream |
| Event history/read projections | Candystore | Durable consumer, replay-safe current snapshot/verdict API |
| Prioritization/delegation/work execution | Momo | Legal frontier only, exact durable invocation consumption, pinned skill resource, artifact-backed evidence, separated rationale/intent |
| Mission control | Holocene | Candystore-backed DOM, confirmed browser action, Bloodbank command publication, and later authoritative render |
| Deployment/process gates | 33GOD root | Immutable pins, ordering, health, isolation, profile semantics |

## Failure and trust boundaries

- Lifecycle truth progresses while Holocene or Momo is offline.
- Missing/stale projection data renders unknown/degraded.
- Lifecycle readiness fails during a broker outage while committed state and
  liveness remain intact.
- Transactional outbox order and eventual publication survive NATS recovery.
- Stale versions and invalid grants yield stable non-mutating verdicts.
- Pending obligations make the corresponding frontier transition illegal;
  only exact canonical completion evidence from the durable Momo actor can
  unlock authority progression, and the actor ACKs invocation only after its
  completion receives a JetStream PubAck. Completion identity/time are stable
  across redelivery, the exact CloudEvent ID is the JetStream `Nats-Msg-Id`, and
  a clean run rejects a duplicate completion PubAck.
- A late-starting Candystore replays pre-existing snapshots and verdicts, and
  duplicate IDs always project the immutable stored event rather than a
  conflicting delivery.
- The live Holocene seam is an unmocked Chromium confirmation and click. Its
  browser-originated POST receives only a non-authoritative 202 broker receipt;
  success is complete only after Lifecycle's later state/version and
  Candystore's matching causality/verdict visibly render.
- Restarting Lifecycle or its PostgreSQL process preserves the dedicated
  authority volume and does not duplicate transition effects.
- The cloud profile is a render-only rejection model, not a deployment target.

## Current deployment label

The normalized local topology and isolated live acceptance path are implemented.
The host has not been promoted to a cloud topology, this worker branch is not a
release branch, and no release tag is created by this slice.

See [Lifecycle Architecture](./architecture-lifecycle.md),
[Deployment Guide](./deployment-guide.md), and
[Drift Governance](./drift-governance.md).
