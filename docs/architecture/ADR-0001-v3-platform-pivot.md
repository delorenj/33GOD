# ADR-0001: 33GOD Event Platform v3 — Dapr + NATS JetStream + CloudEvents

**Status:** Accepted
**Date:** 2026-04-19
**Plane:** GOD-42
**Supersedes:** implicit v2 assumptions (RabbitMQ + ad-hoc schema validation + Bloodbank as primary publisher).

## Context

The 33GOD event platform (v2) emerged organically around RabbitMQ, FastStream,
and Bloodbank-as-everything. That worked for the early pipeline but created
three structural pressures as scope widened:

1. **Schema governance was implicit.** Bloodbank validated at publish time
   against schemas it defined itself. Producing services had no first-class
   contract story.
2. **Bloodbank accumulated responsibility.** It became both the event bus and
   the publisher, which coupled broker concerns to domain publishing concerns.
3. **Tooling drifted.** RabbitMQ management, consumer scaffolding, replay,
   trace, and observability were each solved ad-hoc per component, with no
   shared runtime.

The 2026-04-19 metarepo slimdown (GOD-41) cleared the surface area to focus
the next build phase. This ADR ratifies the v3 direction that the planning
work in `bloodbank/v3-implementation-plan.md` produced, and promotes it to
metarepo scope because the decisions span Bloodbank, Holyfields, and shared
platform services.

## Decision

We pivot to a v3 event platform with the following locked choices.

### Runtime and transport

- **Runtime platform:** Dapr. Dapr provides the pub/sub, state store, and
  secret store abstractions. Services use Dapr APIs; swapping the broker
  becomes a component-manifest change rather than a code change.
- **Broker:** NATS JetStream. JetStream supplies durable streams, replay,
  and subject hierarchies aligned with the `event.*` / `command.*` / `reply.*`
  conventions below.
- **Local and self-hosted deployment:** Docker Compose. `compose/v3/` is the
  canonical sandbox; Kubernetes is explicitly out of scope for this phase.

### Envelopes

- **Immutable events:** CloudEvents 1.0, with 33GOD extension fields
  (`correlationid`, `causationid`, `producer`, `service`, `domain`,
  `schemaref`, `traceparent`).
- **Commands:** separate command envelope with `command_id`, `target_service`,
  `timeout_ms`, `reply_to`, and payload schema reference. Commands are
  mutable by intent; events are not.
- **Subjects:** `event.<domain>.<entity>.<action>`, `command.<target>.<verb>`,
  `reply.<target>.<verb>`.

### Contracts and discovery

- **Description format:** AsyncAPI at the service level.
- **Central contract and service registry:** Holyfields. Owns CloudEvents
  base schema, command envelope schema, per-service AsyncAPI documents,
  per-event and per-command schemas, and generated SDKs (Python, TypeScript).
- **Human + agent discovery:** EventCatalog, generated from Holyfields.
- **Runtime schema governance:** Apicurio Registry, synchronized from
  Holyfields. Producers and consumers fetch schemas at runtime from Apicurio;
  Holyfields is the write side.

### Role reassignments

- **Bloodbank:** runtime and operations only. Dapr manifests, NATS bootstrap,
  Compose files, operator CLI (doctor / trace / replay / emit), adapter
  migration points, replay and dead-letter tools, v3 operations docs.
  Bloodbank does **not** own business event schemas.
- **Bloodbank CLI (`bb_v3`):** operator tool. It is not the primary production
  publish path; production traffic goes through Dapr publishers inside
  services. The CLI is for emission tests, trace walkthroughs, and replay.
- **Holyfields:** contracts and generation only.
- **Services (producing and consuming):** own their business event/command
  schemas. They publish via Dapr using Holyfields-generated SDKs. They do
  not hand-roll envelopes.

## Naming invariants

Locked by this ADR; do not reopen inside implementation tickets.

| Kind | Value |
|---|---|
| Compose project | `bloodbank-v3` |
| Dapr pub/sub component | `bloodbank-v3-pubsub` |
| Dapr app ID prefix | `bloodbank-v3-` |
| NATS events stream | `BLOODBANK_V3_EVENTS` |
| NATS commands stream | `BLOODBANK_V3_COMMANDS` |
| NATS event subject prefix | `event.` |
| NATS command subject prefix | `command.` |
| NATS reply subject prefix | `reply.` |

### Topic-to-subject mapping (clarification added 2026-04-22)

The Dapr `pubsub.jetstream` component maps a Dapr topic name directly to a
NATS subject. Services that want their traffic to land in
`BLOODBANK_V3_EVENTS` must name their Dapr topics with the `event.` prefix
(for example, `event.artifact.created`). The Holyfields-generated SDK
enforces this discipline: services do not hand-write topic names.

There is no Dapr metadata key that prefixes or filters subjects for a
pub/sub component. (An earlier draft of the scaffold used a fabricated
`subjects` metadata key; it was removed on 2026-04-22 after verification
against the Dapr component reference.)

## Consequences

### Positive

- **Swap-ability.** Dapr decouples broker from code; a future move away from
  NATS is a component manifest swap, not a rewrite.
- **Contract clarity.** Holyfields owns the write side; Apicurio owns the
  read side at runtime. Services cannot publish events whose schema is not
  registered.
- **Traceability.** CloudEvents + `correlationid` + `causationid` +
  `traceparent` give a first-class distributed trace story without bolt-on
  middleware.
- **Observability surface.** EventCatalog provides human/agent discovery;
  operators stop grep-ing source for event types.
- **Operator separation.** Bloodbank becomes a focused operator tool;
  service teams own their own publish path, which unblocks parallel work.

### Negative / costs

- **Learning surface.** Four moving parts (Dapr, NATS JetStream, AsyncAPI,
  EventCatalog) vs v2's one (RabbitMQ). Mitigated by scaffolding first,
  production traffic later, and by the documentation-heavy first scaffold
  wave.
- **Contract generation pipeline is new.** Holyfields must produce Python
  and TypeScript SDKs that are consumable in services. This is tracked
  separately under V3-010's Holyfields tracker and blocks production cutover.
- **Migration path for v2 consumers.** Existing RabbitMQ consumers (infra
  dispatcher, node-red flow orchestrator, etc.) must either migrate or run
  in parallel. Adapter scaffolds (V3-008) exist specifically to plan this.
- **Running Apicurio adds ops surface.** Another long-lived service to
  operate. Accepted because alternative is re-implementing schema governance
  in-house, which has a worse long-term cost.

### Neutral / deferred

- **Kubernetes.** Out of scope. Compose is the deployment surface until v3
  stabilizes.
- **Multi-region / clustering.** Out of scope. Single-node JetStream for now.
- **Dapr state store backend.** Scaffold default is `state.in-memory` to
  avoid introducing a Redis dependency before any service actually needs
  durable state. Swap for `state.redis` (or another durable backend) via
  component manifest the first time a service needs cross-restart state.
  Production backend is a later decision; the swap is component-manifest
  only and does not require code change.
- **Replay semantics.** Documented in V3-007; actual tooling beyond docs is
  deferred until after scaffold wave.

## Alternatives considered

- **Stay on RabbitMQ + FastStream, fix schema governance in place.** Rejected
  because it preserves Bloodbank-as-everything and keeps schema validation
  scattered. Revisit cost would be higher later.
- **Kafka instead of NATS JetStream.** Rejected for single-operator /
  self-hosted fit. JetStream covers our durability and replay needs at a
  fraction of the operational complexity, without sacrificing the subject
  hierarchy we want.
- **Skip Dapr, publish to NATS directly from services.** Rejected because it
  locks services to NATS specifically and loses the secret/state
  abstractions. We want the broker to be swappable.
- **Skip Apicurio, use only Holyfields at runtime.** Rejected because it
  forces services to depend on Holyfields repo checkout or a custom API at
  runtime. Apicurio is a boring, standard registry with known semantics.
- **Skip EventCatalog.** Rejected because discovery becomes a grep problem
  again. EventCatalog pays for itself within weeks once event count exceeds
  ~15.

## Implementation

See `docs/architecture/v3-implementation-plan.md` for the ticket-level plan
(V3-001 through V3-011) and Plane decomposition.

## Review triggers

Revisit this ADR if:

- A service cannot produce a CloudEvents envelope because of language or
  runtime constraints.
- Dapr performance characteristics break an SLA we commit to.
- NATS JetStream clustering requirements change the deployment model.
- Apicurio operational cost exceeds its coordination benefit.
- Holyfields SDK generation cannot keep up with contract change rate.

In each case, the ADR is amended with a new status block; decisions are not
silently revised.
