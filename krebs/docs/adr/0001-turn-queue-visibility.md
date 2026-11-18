# ADR 0001: A queued agent turn is a fact on the bus

- **Status:** accepted, 2026-11-18 (Jarad: "build the gateway queued event and retire the n8n triage lane"). Shipped the same day: Krebs asks liveness before a board turn; the gateway publishes `bloodbank.agent.invocation.queued` at claim; Krebs liveness counts a queued turn whoever sent it; the n8n Ticket Triage lane is deactivated (its durable consumer deleted) and Krebs is the only triage sender, with the quiet window cut from 30 to 10 minutes. Open: the gateway's 4 batch slots have no turn timeout (see Consequences).
- **Question (Jarad):** "Before locking in the sqlite solution: is it a code smell that commands can be
  queued by non-krebs sources? Is there a more idiomatic event-driven pattern to employ here?"
- **Level this decides for (`belsky-doctrine`):** every consumer of agent turn state (Krebs liveness,
  Krebs catch-up triage, the pickup chip, Candystore's feed, dashboards), not only the Krebs orphan
  sweep that raised it.

## Short answer

Many components sending agent commands is normal for a bus. That part is not the smell. Two other
things are:

1. **The gateway's public lifecycle starts at `started`.** It durably accepts a command, keeps it for
   up to 55 minutes waiting for a slot, and says nothing on the bus during that time. So any consumer
   that needs to know "is something pending for this ticket" has to read private state: Krebs's own
   journal today, the gateway's SQLite in the proposal. Fix this once where the facts are produced: the
   gateway publishes `bloodbank.agent.invocation.queued` when it claims a command.
2. **Triage has two dispatchers for one decision.** The n8n Ticket Triage lane and Krebs catch-up
   triage cannot see each other's queued commands. This is the only place the gap has done measurable
   harm: 11 duplicate triage commands are sitting in the gateway right now, and 3 more ran on 11-18.
   Implementation already has a single dispatcher (Krebs). In all 81 orphan actions, the orphan sweep
   never touched a ticket that had a queued non-Krebs turn.

**Recommendation:** option (b), a gateway `queued` event, plus a single writer for triage, plus a
liveness check before Krebs catch-up triage. Do not build option (a); it is acceptable only as a
one-day stopgap.

## How it works today

### The gateway

1. A producer publishes `bloodbank.agent.invocation.start` on `bloodbank.cmd.agent.invocation.start`
   into `BLOODBANK_COMMANDS`, a workqueue stream (`bloodbank/compose/nats/streams.json:67-72`).
   Candystore subscribes only to `bloodbank.evt.>` (`candystore/candystore/ingest.py:34`), so commands
   are never archived. `GET /events?type=bloodbank.agent.invocation.start` returns 0 rows.
2. The batch lane fetches up to `max_ack_pending = max_inflight + queued_capacity (+ detached)`
   (`services/hermes-gateway/bloodbank_hermes_gateway/adapter.py:276-279`, `_consume_once`
   `:957-1001`). The live config is `max_inflight: 4` and `queued_capacity: 64`, with no turn timeout
   and no detach on the batch lane (`~/.hermes/config.yaml:610-611`; detach is configured for the
   interactive lane only, `:627-636`).
3. On fetch, the handler claims a `pending` row in the SQLite journal and builds the `started` events
   at the same moment (`adapter.py:1079-1092`, `execution_state.py:322-352`). `lifecycle_event` stamps
   their `time` with `_now()` (`contract.py:433`), so that time is the claim time.
4. The handler then waits for the conversation lock and an execution slot (`adapter.py:1154`; the
   semaphore is at `:1018-1032`). Only after that does it mark the row `started` and publish the stored
   started events (`:1160-1175`).
5. The gateway README defines `pending` as "no started-event publication has been attempted" and lets a
   pre-start rejection be eventless (`services/hermes-gateway/README.md:420-444`).

The gap sits between steps 3 and 4. One side effect matters for everything below: the `time` on
`invocation.started` is the claim time, not the start time. Candystore's `received_at` column holds the
real start, and that is how the waits below were measured.

### Who sends ticket-correlated commands

Source: Candystore, gateway `invocation.started` events from 2026-11-04 to 2026-11-18. There are 868 of
them. 654 are ticket turns (483 `ticket-grooming`, 171 `ticket-delegation`). Since the v2 cutover on
11-14:

| Turn | Sender | Turns since 11-14 |
|---|---|---|
| implementation (`ticket-delegation`) | krebs tick (`context.dispatcher: krebs-tick`) | 96 |
| implementation | n8n | 0 (Ticket Delegation and Groomed-in-Todo are `"active": false`, `delonet-n8n-workflows/workflows/ticket-delegation--8mmqdMwQYA28ZwUj.json:2`, `ticket-delegation-groomed-in-todo--l0J53w0TsS5PwETk.json:2`) |
| triage (`ticket-grooming`) | n8n Ticket Triage (`plane.ticket.created/transitioned`, `ticket-triage--6wAGA5pdrmHLyhs2.json:2` `"active": true`) | 94 |
| triage | krebs catch-up (`krebs.catch_up.triage`) | 77 (73 were the 11-14 backfill) |

There are about 214 other gateway turns: voice memos, agent-to-agent coordination and CI-failure
notices. Each carries its own correlation id, and **none shares a ticket correlation id**. Some name a
ticket key in `data.context` (the bb34-* and aai51-* coordination turns). PM passes and launch passes
are not Bloodbank commands: they are board-scoped Hermes jobs fired by Candybar, and they never dispatch
(`agents/hermes/pm/.scripts/sentinel.prompt.md`, "This pass never dispatches implementation"). Chat and
Crank reach agents through Telegram and zellij panes, not through this gateway.

### How long commands wait

The wait is `received_at - time` on gateway `invocation.started` events, which is the time from claim
to real start. Last 14 days:

| Turn / sender | n | p50 min | p90 min | max min | over 30 min |
|---|---|---|---|---|---|
| triage, n8n | 365 | 0.0 | 10.7 | 54.8 | 8 |
| implementation, krebs | 96 | 0.0 | 15.8 | 51.3 | 2 |
| triage, krebs catch-up | 77 | 9.7 | 23.1 | 28.3 | 0 |

Commands queue because of slot time. Over 14 days on the batch lane, implementation turns ran p50 20
min, p90 108 min and max 277 min, for 109 slot-hours in total. Triage turns ran p50 4.5 min and p90 7.4
min, for 34 slot-hours. There are four batch slots and no batch timeout.

### Live snapshot, 2026-11-18 16:45 UTC (read-only)

- The gateway journal has 4 `started` rows. All four are Krebs implementation turns (FLUME-13,
  FLUME-14, PJAN-14, PJAN-17), claimed at 14:40 UTC and still running at 16:51. Together they hold
  every batch slot.
- The journal has 35 `pending` rows, claimed between 14:50 and 16:40.
- 13 of the pending rows are Krebs catch-up triages. **11 of those duplicate an n8n triage that is
  already pending for the same ticket:** 33GOD-79, SIDE-49, SLOWBURNS-40, SSBNK-1, SSBNK-2, POOL-62,
  POOL-184, POOL-185, POOL-204, GRUV-164, GRUV-166.
- At 15:39 UTC the n8n lane sent six POOL triages to green-in-between-pm within 12 seconds.
  `docs/lifecycle.md:73` says this kind of burst collides on the board-driver lease, and that the
  second turn then gives up without finishing.
- Since 11-14, three more duplicates have run: EARS-8, EARS-9 and TOLT-80, between 02:10 and 02:20 UTC
  on 11-18. In each case the n8n turn had been queued for 33 to 43 minutes when Krebs sent its own.
- The orphan path is clean. Krebs took 81 orphan actions (19 releases, 62 unsticks), and none hit a
  ticket with a queued turn, whether one that later started or one pending now. No non-Krebs source
  sends commands to In Progress tickets.

To sum up: the hidden queue has caused duplicate triage. It has not caused a wrong orphan release.

## Should non-Krebs sources start work turns on a ticket?

| Turn | Answer | Why |
|---|---|---|
| Implementation (`ticket-delegation`) | **No. Krebs only.** This is already true in practice; make it true in code. | An implementation turn spends a slot and writes In Progress plus `agent:working`. Slot accounting stays accurate only if one component does that. Anyone who wants a ticket worked now writes it to the board (Todo, Todo order), and Krebs reads it from there. The board is the request queue, so no "please dispatch" command is needed. |
| Triage (`ticket-grooming`) | **One dispatcher: Krebs.** Retire the n8n lane. | Two writers deciding the same thing with no shared state produce duplicates, and the duplicates above prove it. Only the dispatcher can pace one triage per desk per tick, which the board-driver lease needs, and n8n bursts instead. n8n's speed advantage doesn't hold up: a Krebs tick comes at most 10 minutes later, while the gateway queue that follows is p90 10.7 min and max 55 min. |
| Verdict / PM pass / launch pass | **Yes, as now.** | These are board-scoped and carry no ticket correlation id. A ticket under review holds no slot, so liveness never needs to see them. |
| Chat, Crank, agent-to-agent coordination about a ticket | **Yes, freely.** | These are conversations, not ticket turns. They keep their own correlation id (measured) and must not adopt the ticket's. Any real work they cause shows up through liveness rules 3 and 4 (agent events, or a worker active in the ticket's worktree). |

The rule: **a command that changes who is working a ticket (takes a slot, sets `agent:working`, or
triages) has exactly one sender. Any other command may come from anywhere, and the gateway announces
every command it accepts, so no consumer needs to know who sent it.**

## Options

### (a) Krebs reads the gateway SQLite

Krebs would open `~/.hermes/bloodbank-hermes-gateway-state.sqlite3` read-only and select rows in state
`pending` or `started` by `json_extract(started_events, '$[1].correlationid')`.

- **For:** it is the smallest change (about 2 h, using `node:sqlite` on Node 24 with no new
  dependency), and it sees exactly what the gateway holds.
- **Coupling:** a Node CLI would depend on a Python service's private schema, and that schema
  migrates. It is happening today: the live file is `user_version 3` with 14 columns, while the source
  on main writes `user_version 4` and adds `capture_outcome`, `captured_events` and `capture_error`
  (`execution_state.py:114-121`). The running gateway predates those commits. A reader written against
  main would be wrong until the next gateway restart.
- **No correlation column:** Krebs would have to parse JSON text out of an outbox payload whose bytes
  the gateway treats as immutable for its own replay reasons.
- **Locking:** the journal runs in `journal_mode=delete` (a rollback journal), so a reader can get
  `SQLITE_BUSY` during gateway writes. It needs `busy_timeout` and a retry.
- **Reach:** it fixes one consumer. Candystore, the chip and the UI stay blind. It has the same hole as
  (b) for commands still sitting in JetStream.
- **Verdict:** acceptable as a stopgap, but the wrong place to integrate.

### (b) The gateway emits `bloodbank.agent.invocation.queued` at durable claim

When `claim_pending` writes the row, the gateway also stores and publishes a `queued` fact. Every
`queued` closes with exactly one `completed` or `failed`, and `started` is optional in between.

- **Naming fit:** domain `agent` and entity `invocation` already exist. The action `queued` is already
  allowlisted (`bloodbank/docs/event-naming.md:451`, `services/agent-hooks/core/validate.py:160-161`)
  and means the same thing in two existing journeys: `audio.harvest` (command `start` -> `queued` ->
  `started` -> `completed`) and `cron.steward_task` (`event-naming.md:365`, `:401`). The subject is
  `bloodbank.evt.agent.invocation.queued`, so the event lands in `BLOODBANK_EVENTS` and in Candystore
  with no subscription change. The only new artifact is the schema file.
- **For:** the event log becomes complete. Candystore can answer "is anything pending for this ticket"
  whoever sent the command, and Krebs keeps a single data source over HTTP. Liveness rule 3 (any `agent`
  event on the correlation id within 30 minutes) would already count a fresh `queued` before any Krebs
  change. The event is stored in the journal and replayed with a deterministic id on redelivery, which
  matches the gateway's outbox rule, and Candystore drops the duplicate by id
  (`candystore/ingest.py:77`).
- **Against:** it changes a contract. Once `queued` has been published, a pre-start rejection can no
  longer be eventless and must close with `invocation.failed` (`README.md:443-444`). It adds one event
  per turn, about 900 per 14 days. It has the same hole as (a): while a lane is paused for a drain, its
  commands wait in JetStream unfetched (`adapter.py:947-955`).
- **Effort:** about a day for the gateway and its tests, and about 2 h for Krebs.

### (c) Single writer: only Krebs sends ticket-work commands; everyone else requests

Other sources would publish a request, for example a new `bloodbank.repo.task.dispatch` command, and
Krebs would forward it.

- **For:** Krebs would know everything from its own journal.
- **Against:** Krebs is a stateless CLI that runs every 10 minutes, not a consumer. It would need a
  durable pull consumer drained on each tick, or it would have to become a service. Everything routed
  through it would wait up to 10 more minutes. Implementation already has a request channel (the
  board). For chat and coordination, Krebs is the wrong owner.
- **Verdict:** right for the turns that change who works a ticket (implementation now, triage next),
  wrong as a rule for everything.

### (d) Read the NATS JetStream consumer state

`consumer info` returns counts (`num_pending`, `num_ack_pending`), not correlation ids. Getting a
per-ticket answer means direct-getting messages by sequence and decoding envelopes that sit in another
consumer's in-flight set, and on a workqueue stream a fetch is a claim. This is the coupling of (a)
again, moved into the broker. **Rejected.**

### (e) Also considered

- **Archive commands in Candystore** with a core-NATS tap on `bloodbank.cmd.>`; a workqueue stream
  refuses a second, overlapping consumer. An archived command proves it was sent, not that it was
  accepted, so poison, terminated or misrouted commands would look live until the cap expires. A core
  tap also delivers at most once. Rejected; (b) carries the sender anyway.
- **Producer-side `requested` facts** would mean changing every producer (Krebs, the Fleet node, the
  holocene watcher, the agent send tools) instead of one gateway. Rejected.
- **A gateway heartbeat or lease per open execution** would detect a dead gateway sooner than today's
  8 h cap. Pending rows already survive restarts and replay, so it isn't needed now. Revisit if a
  gateway crash ever strands a ticket.
- **A Candystore `turns` projection** (correlationid to queued, started and ended) is the read model of
  (b). `turnState` already computes it per request; build the projection when a second consumer needs
  it.
- **Gateway-side dedupe** ("one open triage per ticket") would put business policy into the transport.
  Rejected.

## Decision

Adopt (b). Make triage single-writer (the narrow part of (c)). Have Krebs check liveness before
catch-up triage.

## Change list

### Bloodbank: hermes-gateway, schemas, docs

1. `services/hermes-gateway/bloodbank_hermes_gateway/contract.py`: add
   `INVOCATION_QUEUED = "bloodbank.agent.invocation.queued"` and a `queued_event(invocation)` built
   with `lifecycle_event`, with `causationid` set to the command envelope `id`. `data` carries:
   - `invocation_id`, `thread_id`, `turn_id` (the same as `started`)
   - `context`: an echo of the command's `data.context` (`_command_context`)
   - `issuer`: the command's `actor`, verbatim (the same key `final_answer_event` already uses)
   - `command_service`: the command envelope's `service` (for example `krebs-tick` or
     `n8n-ticket-grooming`)
   - optional `lane_inflight` and `lane_queued` at claim time, for capacity diagnostics
   - `lifecycle_event` already adds `command_id`, `idempotency_key`, `target_agent_id`,
     `profile_name` and `lane`

   Pass it through `validate_fact`.
2. `execution_state.py`: add a nullable `queued_events TEXT` column, using the same pattern as
   `:114-119`. `claim_pending` writes it in the same INSERT, and `ExecutionRecord` gains
   `queued_events`.
3. `adapter.py` `_handle_broker_message`: after the claim block (`:1072-1122`), publish
   `persisted.queued_events` for `pending` and `started` rows before entering
   `async with lock, self._execution_slot(lane)` (`:1154`). Treat a publish failure the way started's
   is treated: NAK, and the row stays pending. On the completed-replay path (`:1124-1128`), publish
   queued before started and terminal.
4. Close a pre-start rejection (`adapter.py:1591`, `execution_state.py:550`) with `invocation.failed`
   (`failure_code: rejected_pre_start`) and no `conversation.turn.*`, since no turn began. The CHECK on
   `rejected_pre_start` forbids `terminal_events` (`execution_state.py:168-170`), so either rebuild the
   failed event deterministically from the envelope and `rejected_at` on replay, or send the rejection
   through the existing `rejected_closing` -> `rejected_closed` closure. Either way, every `queued`
   still gets exactly one terminal. A `TurnNotRun` retry leaves the row pending, so `queued` correctly
   stays open.
5. Optional, in the same change: build `started_events` in `mark_started` instead of at claim, so that
   `invocation.started.time` is the real start. This is safe because a `pending` row's started events
   were never published (`README.md:422-424`). Afterwards the queue wait is simply
   `started.time - queued.time`, visible to anyone.
6. Add `schemas/bloodbank/agent/invocation.queued.json`, shaped like `invocation.started.json`: require
   `invocation_id`; `issuer` and `command_service` are optional.
7. `docs/event-naming.md`:
   - §7, the invocation row (`:343`): the journey becomes `queued` (exactly one per command the gateway
     accepted, at durable claim, before a slot) -> `started` (0..1 per attempt) -> `progressed` ->
     `detached` -> `completed` | `failed`. Every `queued` closes with exactly one terminal.
   - §8.1 `queued` (`:451`): add `agent.invocation.queued`.
   - §3.2: the gateway emits queued, started, completed and failed for both lanes.
8. `services/hermes-gateway/README.md:420-444`: `pending` now means "queued published, started not yet
   attempted", and a pre-start rejection is no longer eventless once queued has been published.
9. Tests:
   - `tests/test_adapter.py`: `queued` is published before a slot is taken; a replay reuses the same
     event id; a rejection closes the `queued`.
   - `hermes-agent-template/tests/test_bloodbank_consumer_contract.py:963`: add `queued` to the
     lifecycle type list.
10. Request one restart with `hermes-gateway-restart --reason "invocation.queued"`. The restart that is
    already pending also migrates the journal to `user_version 4`.

Consumers that should not need changes: the pickup chip triggers on started, completed and failed only,
so `agent:working` keeps meaning "running". The ntfy-router does not subscribe to `queued`.

### Krebs

1. `tick/liveness.mjs`:
   - Add `QUEUED` and track `queued` per invocation.
   - Rule 1 becomes "an invocation `queued` or `started` with no end, less than `MAX_OPEN_TURN` (3 h
     for triage) after `queued`". `why` names the state and the sender, for example "queued 40 min ago
     by n8n-ticket-grooming".
   - Rule 0 stays, with a narrower comment: it covers only the gap between a Krebs publish and the
     gateway's claim. That gap is seconds normally, or minutes while a lane is paused for a drain.
   - Optional: a rule-0 command more than 30 minutes old with no `queued` on record raises a warning
     ("not accepted by the gateway"). The ticket stays live until the cap.
2. `tick/run.mjs`, catch-up triage (`:566-585` and `:691-731`): today nothing checks liveness before
   publishing. Probe each candidate at selection time (`:566-585`), so a skipped ticket does not use up
   the scope's one triage for the tick, and skip any ticket with a live turn ("a turn is already queued
   or running"). This step can ship before (b): it already catches running n8n triages, and it catches
   queued ones once (b) lands.
3. `spec/lifecycle.v2.yaml`:
   - `orphans.liveness.live_when` (`:122-127`) and `catch_up.triage` (`:140`).
   - After the n8n lane is retired, the triage transition's `does:` (`:78`) becomes "krebs tick sends
     the triage turn".
   - Bump `spec_version` to 2.3.0 and record it as an owner decision in the spec header (the changelog file was deleted with spec v1).
4. `docs/lifecycle.md:72-73, 97`: update to match.
5. Tests: `tick/test/orphans.test.mjs` (queued with no end is live; queued then failed is idle) and
   the run tests (a catch-up triage is skipped when a turn is live).

### n8n (owner decision, after Krebs step 2)

- Deactivate Ticket Triage (`delonet-n8n-workflows/workflows/ticket-triage--6wAGA5pdrmHLyhs2.json`).
  Lower Krebs's triage minimum age from 30 min to one tick. Keep 1 per scope and 6 per tick.
- Delete the inactive Ticket Delegation and Groomed-in-Todo workflows, so that implementation having one
  sender is enforced in code, not just by a config flag.
- Keep the Pickup Chip.

Order: Krebs step 2, then the gateway `queued` change, then the n8n retirement.

## What Krebs liveness looks like afterwards

A ticket's turn is **live** when any of these holds:

0. Krebs published a command less than the cap ago and the gateway has not yet announced `queued` for
   it (this bridges publish to claim).
1. An invocation is `queued` or `started` with no `completed` or `failed`, and was queued less than 8 h
   ago (3 h for triage). It doesn't matter who sent it.
2. An invocation `detached` less than 24 h ago.
3. Any `agent` or `conversation` event appeared on the ticket correlation id in the last 30 min.
4. An agent-CLI event appeared in the last 30 min with a working directory that names the ticket key.

Candystore unreachable means unknown, and Krebs touches nothing. All senders are seen through one HTTP
source. The journal remains only as the bridge for Krebs's own commands. The same probe gates catch-up
triage.

## Consequences and what this does not solve

- Queue depth per agent and per ticket becomes readable from the bus
  (`/events?type=bloodbank.agent.invocation.queued`). That exposes the next problem.
- **Not solved here: capacity.** Krebs allows 2 implementation turns per scope across every registered
  scope, while the gateway runs 4 batch turns for the whole fleet, with no batch timeout. That mismatch
  is why commands wait up to 55 minutes, and why today four implementation turns blocked every triage
  for over two hours. A follow-up ADR should pick one of three options: a fleet-wide Krebs cap equal to
  the gateway's batch slots; a separate gateway lane for implementation turns; or detaching batch
  implementation turns the way the interactive lane already does.
- Remaining gap: commands still in JetStream while a lane is not pulling. Krebs covers its own through
  rule 0. For other senders the gap lasts minutes, which is under the 30-minute triage age and goes away
  once n8n stops sending triage.

## Appendix: how the numbers were measured

- Candystore HTTP: `GET /events?service=bloodbank-hermes-gateway&type=bloodbank.agent.invocation.started&from=2026-11-04T00:00:00Z&limit=1000`,
  grouped by `data.lane`, `data.context.reason`, `data.context.dispatcher` and
  `data.context.provider_event_type`.
- Candystore Postgres (`docker exec candystore-postgres psql`):
  - queue wait = `received_at - time` on gateway `invocation.started`
  - slot time = the first `completed`/`failed` `received_at` minus `started.received_at`, joined on
    `data.command_id`
  - duplicates = a pair of `ticket-grooming` starts on one correlation id, a Krebs one and an n8n one,
    less than 3 h apart, where the Krebs claim came before the n8n turn ended
  - orphan check = for each Krebs journal `orphan.*` entry, any gateway start on that `ticket_id` with
    `time < ts < received_at`
- Gateway journal (`sqlite3 -readonly`): `state` and `lane` counts; the open rows' `started_events`
  decoded for `context.reason`, `ticket_key` and the sender.
- Krebs journal: `~/.local/state/krebs/tick-journal.jsonl`, `orphan.release` / `orphan.unstick` /
  `triage.publish` / `dispatch.publish`.
