# Bloodbank Architecture

## Current integration role

Bloodbank at
`155f2d774964d1c73694ce2c576fe5f50b91eefb` is the canonical
inter-service contract and transport authority. It owns Lifecycle
command/event/reply schemas, subject naming, NATS JetStream topology, Dapr
transport components, and stream initialization. It does not own deterministic
Lifecycle semantics or operational lifecycle state.

## Contract model

CloudEvents type is `bloodbank.v1.<domain>.<entity>.<action>`. NATS subjects
are `bloodbank.<evt|cmd|rpy>.v1.<domain>.<entity>.<action>`. Target IDs remain
inside envelope data rather than creating routing-specific subject variants.

Lifecycle clients reuse the locked schemas at this revision. Snapshot v2
requires authoritative `capability_version` on every grant, while the canonical
completion-evidence event distinguishes completed skill work from invocation or
review requests. Commands carry
actor, capability/grant context, idempotency, expected state version,
correlation, and causation metadata. No component in this slice creates a
parallel contract.

## Runtime topology

Root Compose runs:

- immutable NATS with JetStream persistence;
- the tracked, read-only Bloodbank stream initializer; and
- Dapr placement plus Candystore's Bloodbank pub/sub component.

Lifecycle connects to NATS for canonical commands/events/replies. Candystore's
durable Dapr consumer projects canonical lifecycle events. Momo and Holocene
publish client intent through Bloodbank; neither connects to an authority
database or writes provider lifecycle state.

Any older lifecycle-controller implementation remaining under Bloodbank is
historical lineage/evidence. Root Compose does not start it. The standalone
Lifecycle component and its dedicated PostgreSQL database are the only current
operational authority path.

## Failure boundary

Lifecycle commits state/history/outbox before publication. During a broker
outage its readiness becomes unavailable but committed state and liveness
remain. After NATS recovery, outbox publication resumes in per-lifecycle order
until no rows remain pending. Bloodbank transport failure never transfers
semantic authority to a client or Candystore.

## Validation

The pinned Bloodbank Lifecycle contract lock is rerun read-only. Root semantic
tests also verify the NATS/init dependency, exact stream initializer mounts,
network membership, and durable Candystore transport path. The isolated live
gate verifies real command/event/reply traffic and broker outage recovery.

## Ownership rule

Contract additions must preserve fixed type/subject identity, kind/action
semantics, provider-neutral names, and downstream projection compatibility.
Schema, runtime validation, naming, producer, and consumer evidence move
together. Bloodbank decides whether the wire contract is canonical; Lifecycle
decides and writes domain truth.

Use [Bloodbank Development Guide](./development-guide-bloodbank.md) and
[Bloodbank Contracts](./api-contracts-bloodbank.md) for component details.
