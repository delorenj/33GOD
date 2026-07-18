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

## Lifecycle Persistence

The lifecycle controller embryo defines lifecycle state/history, dirty reconcile
leases, blockers, gates, checkpoints, observations, and a transactional outbox
in PostgreSQL. Its SQL is duplicated across migration/schema files, is not
installed by Compose, and its default outbox publisher always raises. These
tables are current implementation evidence to migrate with history preservation;
they do not make Bloodbank the target owner of operational lifecycle state.

The embryo also exposes contract drift that must be closed before extraction:
it stages `bloodbank.v1.lifecycle.blocker.detected` without a registered schema,
and the first `status.updated` event can contain an empty `repo` and null
`previous` value that the registered schema rejects.

## Evolution Rules

Schema additions must preserve five-token type/six-token subject identity, kind/action tense, provider-neutral names, and downstream projection compatibility. Add schema, runtime-validation, naming, producer, and consumer evidence together. Bloodbank owns the wire contracts; the planned Lifecycle component owns the deterministic semantics that produce and consume them.
