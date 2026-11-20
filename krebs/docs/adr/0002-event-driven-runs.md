# ADR 0002: A Plane edit or a finished turn runs Krebs; the 10-minute tick is the backstop

- **Status:** accepted and shipped 2026-11-20 (Jarad: "yes, make Plane edits trigger a Krebs run").
- **Level this decides for (`belsky-doctrine`):** every Krebs scope (every board in the agents registry, 28 today),
  not only PX or 33GOD.
- **Problem:** a ticket dropped into Todo waited a 10-minute quiet window, then for the next mark, and then one
  triage per tick: five tickets took about an hour. Nothing moved between two ticks.

## Decision

1. **`krebs watch` runs the same tick on events.** An event-driven systemd service (`deploy/krebs-watch.service`):
   a durable JetStream consumer (`krebs-watch` on `BLOODBANK_EVENTS`). It is not a clock: no timer, cron or loop
   of its own. Candybar's `krebs-tick` (every 10 minutes) stays as the backstop and the only recurring schedule.
2. **Two triggers, one board each.**
   - `bloodbank.evt.repo.task.{created,updated,appended}` on an owned board: wait 60 s after the last event of
     the burst (never longer than 180 s after its first), then run that board.
   - `bloodbank.evt.agent.invocation.{completed,failed}` from the gateway for an agent that owns boards: wait 8 s
     (the pickup chip's clearing edit, Candystore's ingest), then run those boards. This is what chains
     triages back to back: the next one starts when the previous turn ends.
3. **The tick runs as `krebs tick --board <id> --json --trigger <kind>`** (the same code path as Candybar's), and its
   journal line records `trigger` (`schedule`, `plane-edit`, `turn-ended`, `quiet-window`, `lock-retry`,
   `busy-lag`), `trigger_detail` and `board`.
4. **The triage quiet window drops from 10 minutes to 2** (spec `board_turns.triage_quiet_seconds`). The watcher
   debounces the edit itself, so the window only has to outlast the debounce. A ticket still inside its window when
   a run happens re-arms the board for the moment the window ends (read off the tick report), if that is under an
   hour away; a later one is left to the backstop.
5. **A scope holds at most one board turn at a time** (spec `board_turns.per_scope: 1`). The old rule ("one per
   scope per tick") was enough while ticks were 10 minutes apart; with runs back to back, the tick would send a
   second triage while the first is still running, and a desk serializes board turns on its lease (two at once
   collided on 2026-11-14). So the tick asks Candystore for the gateway's `queued`/`started` events with no
   `completed`/`failed` for this scope (plus its own journalled sends, which bridge the publish-to-queued gap) and
   sends no triage or review while one is in flight, any ticket, either kind. Candystore unreachable, or a read
   truncated at its row limit, means none sent. A board turn with no end on record after 3 hours is presumed dead.

## What keeps it from looping

- **Echo suppression.** Krebs's own Plane writes (dispatch label and state, repairs, orphan releases) echo through
  the webhook. The watcher reads the tick journal: an event for a ticket Krebs wrote in the last 20 seconds starts
  no run. The shared Pilot identity cannot tell Krebs from the pickup chip, so the match is on the ticket key.
- **Runaway cap.** At most 20 runs per board per 10 minutes, whatever the cause.
- **One run at a time, a 10 s gap.** All runs go through one serialized queue and share `tick.lock` with the
  Candybar tick. A held lock re-arms the board after 5, 10, 20, 40, 60 s, then leaves it to the backstop.
  A per-board lock was rejected: scopes share the cross-scope cap and the journal.
- **Candystore lag.** If the busy guard still sees a turn the watcher has seen end, it looks again after 10 s,
  up to 3 times.

## Measured turn lengths (why the status ETA assumes 5 minutes)

Median triage 4.4 min, review 5.3 min, delegation 6 min (Candystore, 2026-11). Consecutive triages on one board
therefore take about 5 minutes each instead of 10, and the real gain is that the first one starts within about
3 minutes of the drop (60 s debounce, then the 2-minute window) instead of 10 to 20.

## Rejected

- **Tighter Candybar schedule.** Candybar cannot go under a minute, and polling an idle board is what an event
  makes free.
- **Dispatch from the n8n webhook flow.** A second dispatcher; Krebs stays the only one.
- **No debounce.** An editor saves several times in a burst; one run per burst, not one per keystroke.

## Consequences

- `krebs status` reads `~/.local/state/krebs/watch.json` (heartbeat every 30 s). Alive: ETAs follow events, a board
  turn assumed 5 minutes. Not alive: it says so and projects the 10-minute tick.
- If `krebs-watch.service` is down, nothing breaks: the Candybar tick still runs every 10 minutes, now with the
  scope-busy guard and a 2-minute window.
- The row limit on the busy read (1000 lifecycle events in 3 h 5 min) is a ceiling: a fleet an order of magnitude
  busier would need the guard to ask per agent.
