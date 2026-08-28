# Bloodbank Architecture

## Executive Summary

Bloodbank is the canonical 33GOD event-contract authority and a partial local event runtime. Its strongest layer is schema and naming enforcement; its deployment layer contains reference services and operational gaps. Treat it as contract-complete and runtime-partial.

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

CloudEvents type is `bloodbank.<domain>.<entity>.<action>` (4 tokens). NATS subject is `bloodbank.<evt|cmd|rpy>.<domain>.<entity>.<action>` (5 tokens). The `(domain, entity, action)` tokens must match. Neither carries a version token — schema revisions live in `dataschema`/`schemaref` only. Commands place target identifiers in `data`, never additional subject tokens.

The live `assert_contract()` validates type shape, tense, kind, required fields, domain agreement, subject regex, subject kind marker, **and** subject/type token equality via `assert_subject_matches()`. A mismatched subject raises `ContractViolation`.

## Runtime Components

- NATS streams: seven-day event limits retention; one-day command/reply work-queue retention.
- Stream initializer: creates streams and updates subjects, but does not reconcile every retention/storage property.
- Dapr: event pub/sub component only; command/reply has no equivalent component.
- Agent hooks: canonical mapper/builder plus raw core-NATS publisher; fail-open unless strict mode is set.
- Heartbeat producer: Dapr publisher; Compose points to a missing heartbeat recorder.
- Lifecycle controller: tested reconciliation/outbox design, absent from Compose with an unconfigured publisher.
- Apicurio and EventCatalog: deployed scaffolds without proven source synchronization.

## Data Architecture

Canonical event schemas live in `schemas/`. The common JSON Schema and hook runtime validator disagree on required metadata, subject semantics, and null causation behavior. JSON Schema validity alone is therefore insufficient. See [Bloodbank Data Models](./data-models-bloodbank.md).

## API and Protocol Design

Bloodbank exposes broker/Dapr protocols rather than a first-class application HTTP API. Operator surfaces include the `bb` CLI, schema checks, hook synchronization, NATS/Dapr smoke tests, trace/replay scaffolds, and registry/catalog UIs. See [Bloodbank Contracts](./api-contracts-bloodbank.md).

## Deployment Architecture

Default Compose establishes broker/runtime infrastructure; optional profiles add subscription, heartbeat, Candystore, and smoke-test services. The embedded Candystore profile conflicts with canonical standalone Candystore and must remain disabled when standalone is active. NATS/auth/TLS and broad port exposure limit the topology to a trusted local machine.

## Testing Strategy

Focused evidence at the audit snapshot: 61 schema documents valid, 59 domain contract schemas consistent, 68 naming tests passing, hook generation synchronized, and 21 lifecycle tests passing. CI does not run the complete schema/naming/hook suite and contains a broken heartbeat context.

## Principal Risks

Semantic subject mismatch acceptance, missing heartbeat build context, no JetStream acknowledgement in hook publication, lifecycle outbox unable to publish, weak stream reconciliation, no broker DLQ/capacity limits, unauthenticated local infrastructure, and sensitive hook payload retention.

## Development Workflow

Use [Bloodbank Development Guide](./development-guide-bloodbank.md). Contract changes require downstream Candystore, Holocene, and PJangler review plus root drift-governance evidence.
