# G8 event vocabulary (canonical bloodbank contract)

Every envelope: CloudEvents `type` = 4 tokens
`bloodbank.<domain>.<entity>.<action>`; NATS `subject` = 5 tokens with the
kind marker as token 2; `(domain, entity, action)` identical across both;
`kind` ∈ event|command|reply (enum). All G8 emitters assert this shape in
their own unit tests; the smoke asserts every stored chain envelope against
`/events/<id>/raw`.

## The ticket lifecycle (ONE correlationid create → done)

| type | subject | kind | emitter | when |
|---|---|---|---|---|
| `bloodbank.task.ticket.created` | `bloodbank.evt.task.ticket.created` | event | board | human/gate creates ticket (backlog) |
| `bloodbank.task.ticket.started` | `bloodbank.evt.task.ticket.started` | event | board | momod starts the cycle (in_progress) |
| `bloodbank.task.ticket.assigned` | `bloodbank.cmd.task.ticket.assigned` | **command** | momod | assignment to the code-worker lane (carries `command_id` + `idempotency_key`; BLOODBANK_COMMANDS stream, workqueue) |
| `bloodbank.code.commit.landed` | `bloodbank.evt.code.commit.landed` | event | code-worker | REAL commit + REAL test result published (evt stream) |
| `bloodbank.task.ticket.completed` | `bloodbank.rpy.task.ticket.completed` | **reply** | code-worker | completion reply on the commands stream (rpy marker; momod consumes the fact via the worker's /landed evidence endpoint) |
| `bloodbank.task.cycle.started` | `bloodbank.evt.task.cycle.started` | event | momod | orchestrator begins driving |
| `bloodbank.task.cycle.reviewed` | `bloodbank.evt.task.cycle.reviewed` | event | momod | deterministic evidence review passed (commit + tests) |
| `bloodbank.task.ticket.completed` | `bloodbank.evt.task.ticket.completed` | event | board | ticket closed BY EVIDENCE (done, commit_sha, tests_passed) |
| `bloodbank.task.cycle.failed` | `bloodbank.evt.task.cycle.failed` | event | momod | honest failure publication (reason) |

`bloodbank.task.ticket.completed` appears twice by design: the code-worker's
is the **reply** (rpy marker, commands stream — its id is the completion
fact it owes the assigner) and the board's is the **event** (evt marker,
events stream — the durable public fact of the state change). Same
`(domain, entity, action)` triple, different kind marker — exactly the
contract's kind discipline.

## Boundary notes (honest)

- `repo.task.*` / `repo.board.*` Plane-webhook facts are NOT emitted by this
  bundle — those are Plane-webhook owned in the real system. The sandbox
  board's `bloodbank.task.ticket.*` vocabulary is this bundle's own, and the
  real-Plane adapter deferral (DEFERRED.md §1) records the reconciliation.
- Commands ride `BLOODBANK_COMMANDS` (workqueue, 1d retention): exactly-once
  operational traffic, consumed by the code-worker's own durable
  `g8-code-worker`. Events ride `BLOODBANK_EVENTS` (limits, 7d): durable
  history for candystore + every consumer.
- G8's durables are all `g8-*` (`g8-momod`, `g8-code-worker`,
  `g8-dashboard`, `g8-candystore-events`): one publish reaches every store
  once per durable — never shared with G1/G7's names (coexistence proven in
  smoke/coexist.sh).
