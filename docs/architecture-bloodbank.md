# Bloodbank Architecture

## Executive Summary

Bloodbank is the canonical 33GOD event-contract and transport authority and a partial local event runtime. Its strongest layer is schema and naming enforcement; its deployment layer contains reference services and operational gaps. The lifecycle controller currently incubated here is the tested embryo for a separate component, not Bloodbank's target domain authority.

## Technology Stack

| Category | Technology | Version/evidence |
|---|---|---|
| Broker | NATS JetStream | `nats:2.10-alpine` |
| Runtime integration | Dapr | 1.13.0 |
| Reference services | Python | 3.11 containers; lifecycle requires 3.12+ |
| Persistence | PostgreSQL | 16-alpine for Candystore/lifecycle data |
| Schema | JSON Schema | draft 2020-12, 61 documents |
| Registry/catalog | Apicurio / EventCatalog | 3.0.6 / 2.11.1 |
| Orchestration | Docker Compose, mise | Component-owned |

## Architecture Pattern

Contract-first event backbone with NATS stream routing, Dapr pub/sub adaptation, schema-defined CloudEvents, reference producers/consumers, and operator tooling. Bloodbank deliberately delegates durable query history to Candystore.

## Contract Architecture

CloudEvents type is `bloodbank.v1.<domain>.<entity>.<action>`. NATS subject is `bloodbank.<evt|cmd|rpy>.v1.<domain>.<entity>.<action>`. The `(domain, entity, action)` tokens must match. Commands place target identifiers in `data`, never additional subject tokens.

The live `assert_contract()` validates type shape, tense, kind, required fields, domain agreement, subject regex, and subject kind marker. It does not call the existing `assert_subject_matches()`, so semantically mismatched type/subject tokens pass. This is critical implementation drift.

## Runtime Components

- NATS streams: seven-day event limits retention; one-day command/reply work-queue retention.
- Stream initializer: creates streams and updates subjects, but does not reconcile every retention/storage property.
- Dapr: event pub/sub component only; command/reply has no equivalent component.
- Agent hooks: canonical mapper/builder plus raw core-NATS publisher; fail-open unless strict mode is set.
- Heartbeat producer: Dapr publisher; Compose points to a missing heartbeat recorder.
- Lifecycle controller embryo: pure evaluator, leased queue, atomic state/history/outbox persistence, worker/sweeper, and 21 passing focused tests. It is absent from Compose, its publisher is unconfigured, and it must be extracted with history preservation into the standalone Lifecycle component.
- Apicurio and EventCatalog: deployed scaffolds without proven source synchronization.

## Data Architecture

Canonical event schemas live in `schemas/`. The common JSON Schema and hook runtime validator disagree on required metadata, subject semantics, and null causation behavior. JSON Schema validity alone is therefore insufficient. See [Bloodbank Data Models](./data-models-bloodbank.md).

Lifecycle-specific drift is also concrete: the reconciler emits unregistered
`bloodbank.v1.lifecycle.blocker.detected`, while initial `status.updated`
staging can supply empty `repo` and null `previous` values rejected by its
registered schema. Bloodbank owns closing those contracts; Lifecycle owns the
resulting domain behavior.

## API and Protocol Design

Bloodbank exposes broker/Dapr protocols rather than a first-class application HTTP API. Operator surfaces include the `bb` CLI, schema checks, hook synchronization, NATS/Dapr smoke tests, trace/replay scaffolds, and registry/catalog UIs. See [Bloodbank Contracts](./api-contracts-bloodbank.md).

## Deployment Architecture

Default Compose establishes broker/runtime infrastructure; optional profiles add subscription, heartbeat, Candystore, and smoke-test services. The embedded Candystore profile conflicts with canonical standalone Candystore and must remain disabled when standalone is active. NATS/auth/TLS and broad port exposure limit the topology to a trusted local machine.

## Testing Strategy

Focused evidence at the audit snapshot: 61 schema documents valid, 59 domain contract schemas consistent, 68 naming tests passing, hook generation synchronized, and 21 lifecycle tests passing. CI does not run the complete schema/naming/hook suite and contains a broken heartbeat context.

## Principal Risks

Semantic subject mismatch acceptance, missing heartbeat build context, no JetStream acknowledgement in hook publication, lifecycle outbox unable to publish, lifecycle schema drift, accidental retention of lifecycle semantic ownership during extraction, weak stream reconciliation, no broker DLQ/capacity limits, unauthenticated local infrastructure, and sensitive hook payload retention.

## Development Workflow

Use [Bloodbank Development Guide](./development-guide-bloodbank.md). Contract changes require downstream Lifecycle, Candystore, Momo, Holocene, and PJangler review plus root drift-governance evidence. Bloodbank controller code is read-only extraction evidence in this correction; no application refactor is claimed here.
