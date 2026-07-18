# Bloodbank Data Models

## Schema Authority

`bloodbank/schemas/` is the canonical JSON Schema registry for event, command,
and reply contracts. The current validation script registers and validates 72
schema IDs. Domains cover agent, attendance, audio, CLI, conversation, finance,
lifecycle, LLM, repository, and system activity.

## Envelope Model

The envelope combines CloudEvents 1.0 fields with Bloodbank metadata: identity/type/time/source, correlation and causation, producer/service/domain/kind, actor, ordering, schema references, tracing, and domain data. Command models add command ID, idempotency key, delivery policy, and target fields in data.

## Schema/Runtime Divergence

The common schema omits several runtime-required fields from its `required` array and describes `subject` as an entity path, while locked routing uses it as the NATS subject in live builders/artifacts. It permits null causation for roots where the builder expects a nonempty value. Validation mode is optional for hook publication.

## Lifecycle contracts, not persistence

At the current pinned revision Bloodbank owns the canonical Lifecycle
command/event/reply schemas and NATS/JetStream transport. Operational Lifecycle
state/history/outbox tables live only in Lifecycle's dedicated PostgreSQL
authority database. Any older controller SQL under Bloodbank is historical
lineage/evidence and is not started by the root topology.

## Evolution Rules

Schema additions must preserve five-token type/six-token subject identity, kind/action tense, provider-neutral names, and downstream projection compatibility. Add schema, runtime-validation, naming, producer, and consumer evidence together. Bloodbank owns the wire contracts; Lifecycle owns the deterministic semantics that produce and consume them.
