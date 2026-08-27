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

Base runtime fields: `specversion`, `id`, `source`, `type`, `time`, `correlationid`, `producer`, `service`, `domain`, `kind`, and `data`. Events additionally require `actor` and `ordering_key`. Commands additionally require `actor`, `command_id`, `idempotency_key`, and `delivery=single_consumer`. Replies require `actor`.

The builder also emits subject, schema references, trace context, and nonempty causation. JSON Schema required fields are currently weaker, so consumers needing canonical validity must apply runtime contract rules as well.

## Streams

| Stream | Subjects | Retention | Maximum age |
|---|---|---|---|
| `BLOODBANK_EVENTS` | `bloodbank.evt.v1.>` plus explicitly registered v2 subjects such as `bloodbank.evt.v2.repo.maintenance.failed` | limits | 7 days |
| `BLOODBANK_COMMANDS` | `bloodbank.cmd.v1.>`, `bloodbank.rpy.v1.>` | work queue | 1 day |

No broker-level DLQ or capacity ceiling is configured. Replay metadata exists as headers/conventions, but operator trace/replay CLI commands remain stubs.

## Publication Surfaces

- Canonical agent hook: `services/agent-hooks/publish.py --client <client> --hook <hook>`.
- Dapr HTTP publication: used by the heartbeat reference producer.
- Raw NATS core `PUB`: used by hooks; connection/PING does not prove JetStream persistence.
- `bb verify-envelope`: implemented local validation.

## Known Contract Failure

`assert_contract()` checks subject regex and kind marker but does not call `assert_subject_matches()`. A semantically different subject with the correct kind can pass. Downstream systems must not assume live validation proves type/topic equality until fixed and covered by a negative test.

## Consumers

Candystore subscribes to the cross-version event wildcard `bloodbank.evt.>` and
enforces only a subset; the JetStream stream remains the admission boundary.
Holocene has no functioning direct Bloodbank client. PJangler generators
contain noncanonical subject patterns. These mismatches are governed in [Drift
Governance](./drift-governance.md).
