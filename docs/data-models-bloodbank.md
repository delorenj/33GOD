# Bloodbank Data Models

## Schema Authority

`bloodbank/schemas/` contains 61 JSON Schema draft 2020-12 documents: two common schemas and 59 concrete contracts (53 events, six commands, no reply schemas). Domains cover agent, attendance, audio, CLI, conversation, finance, lifecycle, LLM, repository, and system activity.

## Envelope Model

The envelope combines CloudEvents 1.0 fields with Bloodbank metadata: identity/type/time/source, correlation and causation, producer/service/domain/kind, actor, ordering, schema references, tracing, and domain data. Command models add command ID, idempotency key, delivery policy, and target fields in data.

## Schema/Runtime Divergence

The common schema omits several runtime-required fields from its `required` array and describes `subject` as an entity path, while locked routing uses it as the NATS subject in live builders/artifacts. It permits null causation for roots where the builder expects a nonempty value. Validation mode is optional for hook publication.

## Lifecycle Persistence

The lifecycle controller defines lifecycle state/history, dirty reconcile leases, blockers, gates, checkpoints, observations, and a transactional outbox in PostgreSQL. Its SQL is duplicated across migration/schema files, is not installed by Compose, and its default outbox publisher always raises.

## Evolution Rules

Schema additions must preserve five-token type/six-token subject identity, kind/action tense, provider-neutral names, and downstream projection compatibility. Add schema, runtime-validation, naming, producer, and consumer evidence together.
