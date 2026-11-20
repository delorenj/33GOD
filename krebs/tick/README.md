# krebs tick

The Krebs lifecycle v2 dispatcher ([spec](../spec/lifecycle.v2.yaml), [explainer](../docs/lifecycle.md)). It is the only thing that moves a ticket from Todo to In Progress. Candybar runs it every 10 minutes ([`../.candybars/krebs-tick.candybar.toml`](../.candybars/krebs-tick.candybar.toml)).

```bash
node ~/code/33GOD/krebs/bin/krebs.mjs status --board PX         # what is happening, and when each ticket moves
node ~/code/33GOD/krebs/bin/krebs.mjs tick --dry-run            # read-only plan, every scope
node ~/code/33GOD/krebs/bin/krebs.mjs tick --dry-run --board TOLT --verbose
node ~/code/33GOD/krebs/bin/krebs.mjs tick --json               # what Candybar runs (live)
cd ~/code/33GOD/krebs && npm test                               # node:test, fakes only
```

It has no dependencies and no install step. It reads Candystore at `KREBS_CANDYSTORE_URL` (default `http://127.0.0.1:8683`) to tell whether an agent turn is live. It loads Pilot's Plane client from `../pilot/src` and the bloodbank n8n package's built `dist/` from `../bloodbank/integrations/n8n-nodes-bloodbank`. `KREBS_PILOT_DIR` and `KREBS_BLOODBANK_N8N_DIR` override those paths. If `dist/` is stale, rebuild it there; Krebs takes the routing, the command ids, the delegation prompt and the envelope from it.

## What one tick does

For each scope, in agent-id order:

1. **Owed publishes.** A dispatch whose publish failed on an earlier tick is republished with the same command. The tick republishes only while the ticket is still In Progress with no `lifecycle:review` and no hold label. The command is replayed from the journal byte for byte, because the gateway rejects a reused command id whose envelope digest differs. After 24 hours the tick drops the dispatch and reports it.
2. **Repairs.** It removes `lifecycle:review` from tickets that are not In Progress, and `agent:working` from Done and Cancelled tickets. Each repair is one delta label write.
2b. **Orphans** (spec `orphans`, 33GOD-93). A ticket unchanged for 30 minutes that holds a slot (In Progress, no `lifecycle:review`, no hold label, not an epic) or carries `agent:working` is checked against Candystore (`GET /events`, by the ticket correlation id, plus recent worker activity in a worktree named for the ticket; `tick/liveness.mjs`). With no live turn, a slot holder is released to Todo (one write: Todo and `-agent:working`, then one comment), and any other ticket loses its stale `agent:working`. A ticket already released twice in 7 days gets `+agent:failed` instead. Caps: 2 releases per scope, 12 per tick, 30 label removals per tick. Candystore unreachable means the ticket is left alone with a warning. Released tickets count as Todo for the rest of the tick, so their slots refill at once.
3. **Slots.** `occupied` counts In Progress tickets that carry neither `lifecycle:review` nor a hold label. `free` is `plane.wip` (default 2) minus `occupied`, and never goes below 0. A scope over its limit drains: nothing is dispatched and nothing is evicted.
4. **Dispatch.** A candidate is a Todo ticket that carries `lifecycle:triaged`, has no `agent:working`, no hold label and no `epic`/`epic:*` label, and has no `blocked_by` relation to a ticket outside the completed and cancelled groups. Candidates are ordered by `sort_order`, then priority, then sequence id. For each pick, the tick re-reads the ticket live and checks the guard again. It then makes one Plane write (In Progress, `+agent:working`, and `start_date` if none is set) and publishes `bloodbank.agent.invocation.start` with reason `ticket-delegation` to the scope owner.

The command id is `fleetCommandId(dispatchId, "delegateTicket", agent)`, where `dispatchId = uuid5("krebs:dispatch:<board>:<ticket>:<updated_at before the write>")`. A retry of the same dispatch reuses the id. A later re-dispatch of the same ticket, for example after a SENT BACK, gets a new one.

6. **Triage** (spec `catch_up.triage`), after every scope has been repaired and dispatched. Krebs is the only triage sender: the n8n Ticket Triage lane was retired on 2026-11-18 (ADR 0001). A candidate is a Todo ticket in scope with no `lifecycle:triaged`, no hold label, no `agent:working`, no `epic`/`epic:*` label, and `updated_at` more than 10 minutes ago. Per scope one candidate is kept (one board turn per scope per tick, shared with review turns, alternating: after a triage turn the scope's oldest review goes first, after a review the oldest triage); across the tick triage turns come before reviews, oldest first, and 6 are published; the rest are listed as `capped`. Before a candidate takes the scope's turn, Candystore is asked whether a turn is already queued or running on it (the gateway's `agent.invocation.queued`, whoever sent it); if so it is skipped and the next oldest gets the turn, up to 3 checks per scope (ADR 0001). Each is re-read live (and re-checked) and then gets one `bloodbank.agent.invocation.start` with reason `ticket-grooming`: the Fleet node's `groomTicket` command, with `groomingPrompt` and the same context keys, routed by `resolveFleetAgentForBoard`. **Krebs writes nothing to Plane for triage**; the pickup chip sets `agent:working` when the invocation starts.

The triage command id is `fleetCommandId(uuid5("krebs:triage:<board>:<ticket>:<updated_at>:triage"), "groomTicket", agent)` and `observedAt` is the ticket's `updated_at`, so a retry is byte-identical. A published command is journaled as `triage.publish`; a ticket version with an `ok` entry is never triaged again, and a failed publish is retried on the next tick. If the triage turn leaves the ticket unchanged, `updated_at` does not move, so it is not re-triaged; any edit makes a new version (after another 10 quiet minutes). `--dry-run` lists the planned triages (`triage catch-up:` per scope in the summary, `triage`, `triageCapped` and `triageSeen` in `--json`) and publishes and journals nothing.

7. **Review turns** (spec `catch_up.review`), in the same pass as triage catch-up. A candidate is an In Progress ticket with `lifecycle:review`, no hold label, no `agent:working`, no `epic`/`epic:*` label, and `updated_at` more than 30 minutes ago. It competes with triage candidates for the scope's one board turn (alternating, as above). The same Candystore check picks it (a live or unknown turn skips it), and it is re-read live before the publish. It then gets one `bloodbank.agent.invocation.start` with reason `ticket-review` and `dispatcher: krebs-tick` to the scope's PM, carrying `reviewPrompt` (judge each criterion on evidence; end with `px close`, `px release -m "returned: …"` or `px attention`). Krebs writes nothing to Plane. The command id is `uuid5("krebs:review:<board>:<ticket>:<updated_at>:<attempt>")` through `fleetCommandId(…, "reviewTicket", agent)`; a version with no verdict is sent again after 3 hours, at most 3 attempts. Journal action: `review.publish`.

Every hold label stops all of the above. `lifecycle:human` (the owner took the ticket by hand) also keeps the ticket out of the orphan sweep and its liveness probe: Krebs reads it and writes nothing.

## Scopes

Scopes come from `~/.hermes/agents-registry.yaml`, one per row that has a `plane:` block, with these exceptions:

- **No board id.** A row whose plane block has no `project_id` is not a scope.
- **Advisory.** A row with `board_scope: advisory` is not a scope.
- **Retired.** `flume retire` turns bloodbank off and removes the plane claim, so a retired row has no plane block left. A row whose `status` or `employment` is `retired` or `suspended`, or that has `retired: true` or a `retired_at`, is also skipped.
- **Not fleet-addressable.** The tick applies the same checks as the n8n Fleet node and the gateway: `profile_name` is set, `bloodbank.enabled` is true or absent, `gateway_scope` is `fleet`, and `target_agent_id` equals the row id.
- **Fenced (best effort).** The tick reads `<project_path>/.project.json`. If `execution.mode` is present and is not `legacy`, the row is skipped. A missing or unreadable manifest counts as legacy. A row whose `project_path` is a parent repo is judged by the parent's manifest. For example, `tolt-pm` points at `~/code/tolt`, not at the game submodule.

On a shared board, each ticket is routed by `resolveFleetAgentForBoard`, the same resolver the n8n Fleet node and pickup chip use (`scope_label`, then `scope_default`). Krebs and the chip therefore always agree on which scope owns a ticket. Unlabelled TOLT intake belongs to `tolt-pm`.

Row knobs: `plane.wip` (non-negative integer, default 2) and `plane.review` (when `true`, handback is `lifecycle:review`; otherwise the ticket is closed Done). The handback rule is appended to the dispatch prompt.

## Journal

`~/.local/state/krebs/tick-journal.jsonl`, relocated by `KREBS_STATE_DIR`, or `--journal`. Each action writes one line: `repair`, `orphan.release`, `orphan.unstick`, `orphan.fail`, `triage.publish`, `review.publish`, `dispatch.intent` (which carries the full command), `dispatch.write`, `dispatch.publish`, `dispatch.dropped`, plus one `tick` summary line. A failed write whose outcome is unknown (a timeout, a 5xx) is left pending without verification. The next tick publishes only if the write is actually on the ticket. `tick.lock` in the same directory keeps a hand-run tick from overlapping a scheduled one. A dry run never writes the journal.

## Watching the pipeline

`krebs status` answers "what is happening on my board, and when will each ticket move?". It is read-only: no Plane write, no publish, no `tick.lock`, no journal line. It runs the tick's own dry-run plan (`runTick` with `dryRun` and an `inspect` hook, so triage eligibility, dispatch order, slot math, blockers and orphans are the tick's decisions, not a copy) and adds Candystore's live turns and a projection of the next ticks.

```bash
krebs status                       # every scope; idle and fully parked scopes collapse to one line
krebs status --board PX            # one board, every Todo / In Progress ticket
krebs status --board PX --json     # the same data as a stable object
krebs status --ticket PX-12        # one ticket, any lane: stage, why, ETA, turn history, journal trail
```

Per scope it prints: the header (board -> agent, WIP occupied/limit), the last tick and its result (the journal's last `tick` line), the next tick (an estimate); **in flight now** (turns Candystore says are queued or running, with how long); every ticket with a **stage**, the **reason** in plain English and an **ETA** for its next transition; the last 10 journal actions; and, when nothing is running, one **why nothing moved** line.

Stages: `waiting: quiet window`, `waiting: agent activity`, `next for triage`, `queued for triage #n`, `triage in flight`, `triage already sent` (a version the tick already triaged and that is still untriaged: edit it), `ready to dispatch`, `waiting for a WIP slot behind <slot holders>`, `blocked_by <ticket>`, `in progress (delegation running 12m)`, `in progress: no live turn` (orphan release ETA), `in review: waiting for quiet` / `review turn queued` / `turn already sent`, `held: <label>`, `epic: never dispatched`, `agent:working` with no live turn. `--ticket` also shows `backlog` and `done`.

### Timing: what fires when

| What | When | Notes |
|---|---|---|
| The tick | every 10 minutes on the mark (`:00 :10 :20 ...`), Candybar `krebs-tick` | everything below happens at a tick, never between two |
| Triage eligibility | Todo, no `lifecycle:triaged`, no hold label, no `agent:working`, not an epic, `updated_at` older than 10 minutes | any edit (a comment, a label, a move into Todo) restarts the 10-minute clock |
| Triage throughput | 1 board turn per scope per tick, 6 per tick across scopes, oldest `updated_at` first | the one turn is shared with review and alternates with it, so a review can take a triage turn's place |
| Triage turn | starts at the tick, ends when the agent adds `lifecycle:triaged` (or `needs-input`) | minutes; the ticket cannot be dispatched until it ends |
| Dispatch | the first tick after `lifecycle:triaged` lands, into free WIP slots (`plane.wip`, default 2), in Todo order | a full scope waits for a handback, a hold label or Done |
| Review eligibility | In Progress + `lifecycle:review`, no hold, no `agent:working`, quiet 30 minutes | then 1 board turn per scope per tick as above; resent after 3 h, at most 3 times |
| Orphan release | In Progress holding a slot (or any `agent:working`), quiet 30 minutes, no live turn in Candystore | back to Todo; a second release in 7 days becomes `agent:failed` |

Worst-case latency for N untriaged tickets dropped into Todo at once on one scope, assuming idle agents: the first triage starts at the first tick more than 10 minutes after the drop (10 to 20 minutes), then one more every 10 minutes, so the last starts 10N to 10N+10 minutes after the drop. Each ticket is dispatchable one tick after its own triage ends, so the last is dispatched about 10N+20 minutes after the drop (when a slot is free). N = 8: about 90 minutes to finish triage and 100 to dispatch the last one. Already-triaged tickets skip the queue and go at the next tick while slots are free. The PX drop of 2026-11-20 (5 untriaged, 2 triaged): dispatch of the triaged pair at the next tick, triage of the five at +10 min steps, the last one ~72 minutes after the drop.

### `--json` shape (version 1)

```text
{ version: 1, generatedAt, estimates,
  tick: { everyMinutes: 10, last: {at, finishedAt, ok, scopes, dispatched, triaged, reviews, repaired, errors} | null,
          overdue: bool, nextEstimate },
  candystore: { ok, error, url },
  registry, journal,
  scopes: [ { board, boardId, agentId, scopeLabels, wip, occupied: [key], free, overLimit, reviewRequired,
              idle: bool,                       // no Todo / In Progress ticket at all
              inFlight: [ {key, title, kind, reason, state: running|queued|detached|sent, since, runningMinutes, invocationId} ],
              idleReason: string | null,        // set when inFlight is empty
              tickets: [ {key, title, lane, state, labels, updatedAt,
                          stage, stageLabel, reason,
                          eta: ISO | null, etaNote: string | null,    // an estimate; null = depends on something else
                          queuePosition: n | null, blockedBy: string | null} ],
              counts: { <stage>: n },
              recent: [ {ts, ageMinutes, action, key, ok, detail} ],  // last 10 journal actions of this agent
              warnings, errors } ],
  ticket?: { ...row, scope, journal: [...], turns: [ {invocationId, reason, queuedAt, startedAt, endedAt, outcome, detachedAt} ] } }   // --ticket only
```

`stage` is one of: `ready`, `wait-slot`, `blocked-by`, `triage-next`, `triage-queued`, `quiet-window`, `triage-seen`, `triage-inflight`, `turn-inflight`, `working`, `in-progress`, `in-progress-idle`, `review-wait`, `review-inflight`, `review-sent`, `review-working`, `review-noverdict`, `held`, `epic`, `other-lane`, `backlog`, `done`, `cancelled`. Exit code 0; 2 for a usage error. Candystore unreachable is reported under `candystore` and in the text, never a crash; stages then say they cannot tell.

### How accurate are the ETAs?

They are projections, marked `~`. A ticket with agent activity on it in the last 30 minutes (a review turn that just ended, a worker in its worktree) is skipped by the tick as "turn live" without using the scope's turn, so its ETA waits for the end of that quiet window (`waiting: agent activity`); status asks Candystore for this on every ticket in the board-turn pool. They assume every tick fires on the 10-minute mark, nobody edits a ticket meanwhile (an edit restarts its quiet window), turns end quickly, and the 6-per-tick cross-scope cap does not bite (on a busy tick a scope can lose its turn to older tickets elsewhere). A dispatch needing a slot has no ETA: it depends on when a running turn hands back. `blocked_by` is only read for tickets the dispatch walk reaches, so a ticket behind a full scope shows `waiting for a WIP slot` until a slot opens, then its blocker.
