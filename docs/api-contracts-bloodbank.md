# Bloodbank API and Protocol Contracts

## Canonical Event Identity

| Field | Shape | Authority |
|---|---|---|
| CloudEvents `type` | `bloodbank.v1.<domain>.<entity>.<action>` | `bloodbank/docs/event-naming.md` |
| NATS/Dapr topic | `bloodbank.<evt|cmd|rpy>.v1.<domain>.<entity>.<action>` | Same naming contract |
| Envelope `kind` | `event`, `command`, or `reply` | Canonical envelope |
| Command target | `data.target_agent_id` or domain payload | Never extra subject tokens |

The three body tokens must match between type and subject. Event actions are past tense; command actions imperative; replies mirror commands.

## Required Runtime Envelope

Canonical runtime fields include `specversion`, `id`, `source`, `type`,
`subject`, `time`, `correlationid`, `causationid`, `producer`, `service`,
`domain`, `kind`, `actor`, and `data`. Events additionally require
`ordering_key`. Commands additionally require `command_id`, `idempotency_key`,
and `delivery=single_consumer`. Registered lifecycle schemas also bind the exact
`datacontenttype`, `dataschema`, and `schemaref` values.

A root-issued command sets `correlationid=command_id` and may use null
`causationid`. A command derived from an authoritative projection inherits the
snapshot's correlation lineage and sets `causationid` to that exact snapshot
CloudEvent ID. Trace context remains optional.

## Streams

| Stream | Subjects | Retention | Maximum age |
|---|---|---|---|
| `BLOODBANK_EVENTS` | `bloodbank.evt.v1.>` | limits | 7 days |
| `BLOODBANK_COMMANDS` | `bloodbank.cmd.v1.>`, `bloodbank.rpy.v1.>` | work queue | 1 day |

No broker-level DLQ or capacity ceiling is configured. Replay metadata exists as headers/conventions, but operator trace/replay CLI commands remain stubs.

## Publication Surfaces

- Canonical agent hook: `services/agent-hooks/publish.py --client <client> --hook <hook>`.
- Dapr HTTP publication: used by the heartbeat reference producer.
- Raw NATS core `PUB`: used by hooks; connection/PING does not prove JetStream persistence.
- `bb verify-envelope`: implemented local validation.

## Runtime Contract Binding

`assert_contract()` invokes `assert_subject_matches()`, so runtime validation
binds CloudEvent type, NATS/Dapr subject, and envelope kind rather than accepting
a structural lookalike. Bloodbank's schema, naming, compatibility, producer, and
consumer suites include negative subject/type/const/version cases.

## Consumers

Lifecycle is the active command consumer and canonical lifecycle event/reply
producer. Bloodbank's registered contracts include snapshot v3 with required
`capability_version` and authority-owned `obligation_instance_id`, obligation
completion evidence v2, and the versioned command/reply schemas.

Candystore durably consumes the canonical event/reply streams, validates exact
schema plus Lifecycle authority identity, retains append-only audit rows, and
projects only accepted authority envelopes. Holocene has an implemented
Bloodbank command client: it reads Candystore's projection, inherits the exact
snapshot correlation lineage and causation event, and publishes high-level
commands through the canonical subject. Its current core-NATS PING/PONG receipt
means broker protocol processing, not durable JetStream acceptance. Momo uses
the same contracts for legal actor-work selection, skill invocation, completion
evidence, and Lifecycle command intent. PJangler's generators use fixed
six-token canonical subjects; routing identity stays in payload/subscription
scope rather than extra subject tokens.

Root Compose runs the standalone Lifecycle authority, its dedicated
PostgreSQL database, and the existing Bloodbank NATS/JetStream topology. The
schemas above are registered and operational in the exercised runtime path.

Bloodbank owns these canonical schemas and transport. Lifecycle alone evaluates
and writes lifecycle truth; Candystore is audit/read-only, Momo chooses actor
work, and Holocene renders authoritative data and invokes high-level actions.
