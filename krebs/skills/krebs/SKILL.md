---
name: krebs
description: Krebs lifecycle v2, the one ticket lifecycle for every 33GOD Plane board, and the doctrine for agents working it. Use for any board, lifecycle, triage, dispatch, handback, hold, verdict or review work - triaging a Todo ticket, implementing a dispatched one, handing work back with evidence, parking a ticket on a person or a blocker, giving a verdict, or recording a decision event. Replaces the momo skill. Triggers - "triage this ticket", "lifecycle:triaged", "lifecycle:review", "needs-input", "hand back", "SENT BACK", "who dispatches", "krebs tick", "work the board".
---

# Krebs: the board lifecycle (v2)

Source of truth: `~/code/33GOD/krebs/spec/lifecycle.v2.yaml` (rules) and
`~/code/33GOD/krebs/docs/lifecycle.md` (explanation). If this file and the spec disagree, the spec
wins. Krebs retires Momo: no nine-lane boards, no prompt-driven dispatch, no WIP-by-prose.

## Lanes: stock five, everywhere

| Lane | Meaning |
|---|---|
| Backlog | Owner's queue (default lane). Nothing runs from here. |
| Todo | Accepted work. Entering Todo starts triage; a triaged ticket waits here for a slot. |
| In Progress | Being implemented, or waiting for its verdict. |
| Done / Cancelled | Terminal. |

Lifecycle meaning lives in **labels**, never in extra lanes. Do not invent lanes or states.

## Labels and who sets them

| Label | Meaning | Set by |
|---|---|---|
| `agent:working` | an agent turn is running on it now | pickup chip, krebs dispatch, `px claim` |
| `lifecycle:triaged` | triage finished; ready for a slot | the triage turn, as its last action |
| `lifecycle:review` | handed back, awaiting verdict (only valid in In Progress) | the implementation turn |
| `lifecycle:needs-input` | waiting on a person; question is in a comment | any turn |
| `lifecycle:blocked` | waiting on another ticket or outside thing | any turn |
| `agent:failed` | a turn failed, nobody has looked | lane errors |

Hold labels = `needs-input`, `blocked`, `agent:failed`. A held ticket is never dispatched and never
occupies a slot. `px task create -l` refuses `agent:` labels on purpose: they are automation-only.

## Hard rules

1. **Agents never touch `agent:working`.** Not add, not remove, not "to be safe". The pickup chip owns
   it during a turn; otherwise only `px claim` (adds) and `px release|close|cancel` (remove) touch it.
2. **Only `krebs tick` dispatches Todo to In Progress.** It is the one dispatcher, on the Candybar
   `krebs-tick` schedule. Never move a Todo ticket to In Progress yourself, never `px claim` a ticket
   you were not dispatched, never re-dispatch around a full scope. No slot means wait.
3. **Never change a ticket's state from a triage turn.** Triage labels and comments only.
4. **Hold with a label, not a lane.** The lane does not change.
5. **Evidence over status.** A label or lane is a claim; the evidence comment is the proof.
6. Never publish `repo.task.*` / `repo.board.*` events by hand; Plane writes echo through the webhook.

## Triage contract (you were sent a Todo ticket)

Skip it when the ticket already has `lifecycle:triaged` or a hold label (SENT BACK and release
re-entries skip triage). Otherwise read the ticket and check the acceptance criteria: non-empty,
testable, enumerated, covers the requirement. Repair thin criteria by editing the description or
commenting. Do not split it, do not start the work. End with exactly one of:

- **Finished:** add `+lifecycle:triaged` as your **last action**. The chip clears `agent:working` at turn end.
- **Cannot finish without a person:** add `+lifecycle:needs-input` and post the question as a comment
  (one concrete question, what you tried, what answer unblocks it). Do not add `triaged`.

Never both, never neither, and never `triaged` before the work of triage is actually done: it is what
makes the ticket dispatchable.

## Implementation (krebs dispatched you to In Progress)

The ticket is already In Progress with `agent:working`. Do the work in the child repo's own workflow
(delegate code to workers where your role says so). Finish with a handback, which depends on the
scope's registry row (`plane.review`):

| Scope has a verdict giver (`plane.review: true`) | Handback |
|---|---|
| yes | add `+lifecycle:review` and post an evidence comment. Leave it In Progress. Do not close it. |
| no | close it Done (`px close <ref> -m "<evidence>"`) with the evidence comment. |

Evidence comment: what changed (commit/PR/paths), the command or check that proves it, the result
pasted verbatim, what you did not do. A handback with no evidence is a failed handback.

Stuck mid-work: `+lifecycle:needs-input` (question as a comment) or `+lifecycle:blocked` (comment what
it waits on; record the blocker as a Plane relation, `px link add A B --blocks`). The lane stays In
Progress and the ticket stops holding a slot, so krebs can dispatch the next one. Park, do not tunnel.

## Verdict giver (Launch Director, or the PM where there is none)

You see tickets In Progress + `lifecycle:review`. Judge against the acceptance criteria and the
evidence, not the implementer's summary; the reviewer is never the implementer.

- **Accepted:** the PM closes it Done with a one-line reason.
- **SENT BACK:** the PM moves it to **Todo** with the comment `returned: <criterion>` naming the
  specific unmet criterion. It keeps `lifecycle:triaged` and waits for a slot; it is not re-triaged.
  `lifecycle:review` is cleared when it leaves In Progress.

Verdict givers rank, flag and judge. They do not dispatch.

## PM passes

PMs accept (Backlog to Todo), order Todo (Plane `sort_order` is dispatch order, then priority, then
sequence id), park (to Backlog), cancel, close accepted work and relay answers to `needs-input`
tickets. Writes go through `px` or `px-apply.py` (interval-driver), under the board-driver lease
(`interval-driver/scripts/board-lease.py`) when passes can overlap. The lease serializes board
writes; it is not a work limit.

## Slots (what krebs enforces, so you never have to)

Per scope (registry row): 2 implementation slots, `plane.wip` overrides. Occupied = In Progress AND
NOT `lifecycle:review` AND NOT a hold label. Over the limit it drains, never evicts. Dispatch guard:
free slot, `lifecycle:triaged`, no `agent:working`, no hold label, not an `epic` container, no open
blocking relation. Krebs also repairs `lifecycle:review` outside In Progress and `agent:working` on
Done/Cancelled.

## Recording a decision

For a consequential judgment (accepting a review, cutting scope, choosing an approach, parking work),
emit one decision event citing pillars. It writes the local trail and publishes
`bloodbank.repo.decision.recorded` (repo slug in `data.repo`, pillars in `data.basis`):

```bash
python3 ~/code/33GOD/krebs/skills/krebs/scripts/record-decision.py \
  --decision "<one line>" --basis "<pillar-slug>" [--basis "<pillar-slug>" ...] \
  --reasoning "<why: tradeoffs, what you rejected>" [--issue <REF>] --actor <your agent id>
```

Run from inside the repo (it needs the nearest `.project.json`). `--dry-run` prints the envelope
only; `--local-only` skips the bus. Exit 3 means the trail is saved but the bus publish failed. This
records your judgment, not the Plane write itself.

## Never

- Touch `agent:working`, dispatch, or move Todo to In Progress (rules 1 and 2).
- Change state during triage, or end triage without `triaged` or `needs-input`.
- Hold by moving lanes, or leave `lifecycle:review` on a ticket outside In Progress.
- Close a review-required ticket yourself, or review your own work.
- Restate ticket status in docs; link `REF-123` and let the board be the source.
