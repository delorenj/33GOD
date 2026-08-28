# Bloodbank API and Protocol Contracts

## Canonical Event Identity

| Field | Shape | Authority |
|---|---|---|
| CloudEvents `type` | `bloodbank.<domain>.<entity>.<action>` (4 tokens) | `bloodbank/docs/event-naming.md` |
| NATS/Dapr topic | `bloodbank.<evt|cmd|rpy>.<domain>.<entity>.<action>` (5 tokens) | Same naming contract |
| Envelope `kind` | `event`, `command`, or `reply` | Canonical envelope |
| Command target | `data.target_agent_id` or domain payload | Never extra subject tokens |

The three body tokens must match between type and subject. Event actions are past tense; command actions imperative; replies mirror commands.

**There is no version token in `type` or in the subject.** The schema-revision
axis lives only in `dataschema` (`apicurio://holyfields/<type>/versions/<n>`)
and `schemaref` (`<type>.v<N>`) — a trailing `.v1` on a `schemaref` is correct
and must not be stripped. A breaking payload change gets a new action or a new
entity, never a version segment in the wire name.

## Required Runtime Envelope

Base runtime fields: `specversion`, `id`, `source`, `type`, `time`, `correlationid`, `producer`, `service`, `domain`, `kind`, and `data`. Events additionally require `actor` and `ordering_key`. Commands additionally require `actor`, `command_id`, `idempotency_key`, and `delivery=single_consumer`. Replies require `actor`.

The builder also emits subject, schema references, trace context, and nonempty causation. JSON Schema required fields are currently weaker, so consumers needing canonical validity must apply runtime contract rules as well.

## Streams

| Stream | Subjects | Retention | Maximum age |
|---|---|---|---|
| `BLOODBANK_EVENTS` | `bloodbank.evt.>` | limits | 7 days |
| `BLOODBANK_COMMANDS` | `bloodbank.cmd.>`, `bloodbank.rpy.>` | work queue | 1 day |

Subject filters are plain wildcards over the 5-token subject space; see
`bloodbank/compose/nats/streams.json`. There is no versioned wildcard and no
per-version subject registration.

No broker-level DLQ or capacity ceiling is configured. Replay metadata exists as headers/conventions, but operator trace/replay CLI commands remain stubs.

## Publication Surfaces

- Canonical agent hook: `services/agent-hooks/publish.py --client <client> --hook <hook>`.
- Dapr HTTP publication: used by the heartbeat reference producer.
- Raw NATS core `PUB`: used by hooks; connection/PING does not prove JetStream persistence.
- `bb verify-envelope`: implemented local validation.

## Subject/type equality is enforced

`assert_contract()` checks the subject regex and the kind marker **and** calls
`assert_subject_matches()`, so a semantically different subject is rejected even
when it is well-formed and carries the right kind marker. Verified against
`bloodbank/services/agent-hooks/core/validate.py`:

```
type=bloodbank.repo.task.created  subject=bloodbank.evt.repo.board.created
-> ContractViolation: subject 'bloodbank.evt.repo.board.created' does not match
   expected 'bloodbank.evt.repo.task.created'
```

`forward_envelope.py` independently pins all five subject tokens at the
transport door, so a producer that regresses to the retired 6-token shape fails
loudly rather than being forwarded silently.

## Consumers

Candystore subscribes to the cross-version event wildcard `bloodbank.evt.>` and
enforces only a subset; the JetStream stream remains the admission boundary.
Holocene has no functioning direct Bloodbank client. PJangler generators
contain noncanonical subject patterns. These mismatches are governed in [Drift
Governance](./drift-governance.md).
