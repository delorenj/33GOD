# krebs tick

The Krebs lifecycle v2 dispatcher ([spec](../spec/lifecycle.v2.yaml), [explainer](../docs/lifecycle.md)). It is the only thing that moves a ticket from Todo to In Progress. Candybar runs it every 10 minutes ([`../.candybars/krebs-tick.candybar.toml`](../.candybars/krebs-tick.candybar.toml)).

```bash
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

6. **Triage catch-up** (spec `catch_up.triage`), after every scope has been repaired and dispatched. This covers webhooks the n8n Ticket Triage lane never saw (an n8n restart). A candidate is a Todo ticket in scope with no `lifecycle:triaged`, no hold label, no `agent:working`, no `epic`/`epic:*` label, and `updated_at` more than 30 minutes ago. Per scope the oldest one is kept (one board turn per scope per tick, shared with review turns); across the tick the 6 oldest of those are published; the rest are listed as `capped`. Before a candidate takes the scope's turn, Candystore is asked whether a turn is already queued or running on it (an n8n triage, say); if so it is skipped and the next oldest gets the turn, up to 3 checks per scope (ADR 0001). Each is re-read live (and re-checked) and then gets one `bloodbank.agent.invocation.start` with reason `ticket-grooming`: the Fleet node's `groomTicket` command, with `groomingPrompt` and the same context keys, routed by `resolveFleetAgentForBoard`. **Krebs writes nothing to Plane for triage**; the pickup chip sets `agent:working` when the invocation starts.

The triage command id is `fleetCommandId(uuid5("krebs:triage:<board>:<ticket>:<updated_at>:triage"), "groomTicket", agent)` and `observedAt` is the ticket's `updated_at`, so a retry is byte-identical. A published command is journaled as `triage.publish`; a ticket version with an `ok` entry is never triaged again, and a failed publish is retried on the next tick. If the triage turn leaves the ticket unchanged, `updated_at` does not move, so it is not re-triaged; any edit makes a new version (after another 30 quiet minutes). `--dry-run` lists the planned triages (`triage catch-up:` per scope in the summary, `triage`, `triageCapped` and `triageSeen` in `--json`) and publishes and journals nothing.

7. **Review turns** (spec `catch_up.review`), in the same pass as triage catch-up. A candidate is an In Progress ticket with `lifecycle:review`, no hold label, no `agent:working`, no `epic`/`epic:*` label, and `updated_at` more than 30 minutes ago. It competes with triage candidates for the scope's one board turn, oldest first. The same Candystore check picks it (a live or unknown turn skips it), and it is re-read live before the publish. It then gets one `bloodbank.agent.invocation.start` with reason `ticket-review` and `dispatcher: krebs-tick` to the scope's PM, carrying `reviewPrompt` (judge each criterion on evidence; end with `px close`, `px release -m "returned: …"` or `px attention`). Krebs writes nothing to Plane. The command id is `uuid5("krebs:review:<board>:<ticket>:<updated_at>:<attempt>")` through `fleetCommandId(…, "reviewTicket", agent)`; a version with no verdict is sent again after 3 hours, at most 3 attempts. Journal action: `review.publish`.

Every hold label stops all of the above. `lifecycle:human` (the owner took the ticket by hand) also keeps the ticket out of the orphan sweep and its liveness probe: Krebs reads it and writes nothing.

## Scopes

Scopes come from `~/.hermes/agents-registry.yaml`, one per row that has a `plane:` block, with these exceptions:

- **No board id.** A row whose plane block has no `project_id` is not a scope.
- **Advisory.** A row with `board_scope: advisory` is not a scope.
- **Retired.** `flume retire` turns bloodbank off and removes the plane claim, so a retired row has no plane block left. A row whose `status` or `employment` is `retired` or `suspended`, or that has `retired: true` or a `retired_at`, is also skipped.
- **Not fleet-addressable.** The tick applies the same checks as the n8n Fleet node and the gateway: `profile_name` is set, `bloodbank.enabled` is true or absent, `gateway_scope` is `fleet`, and `target_agent_id` equals the row id.
- **Fenced (best effort).** The tick reads `<project_path>/.project.json`. If `execution.mode` is present and is not `legacy`, the row is skipped. A missing or unreadable manifest counts as legacy. A row whose `project_path` is a parent repo is judged by the parent's manifest. For example, `tolt-pm` points at `~/code/tolt`, not at the game submodule.

On a shared board, each ticket is routed by `resolveFleetAgentForBoard`, the same resolver the n8n triage lane uses (`scope_label`, then `scope_default`). Krebs and triage therefore always agree on which scope owns a ticket. Unlabelled TOLT intake belongs to `tolt-pm`.

Row knobs: `plane.wip` (non-negative integer, default 2) and `plane.review` (when `true`, handback is `lifecycle:review`; otherwise the ticket is closed Done). The handback rule is appended to the dispatch prompt.

## Journal

`~/.local/state/krebs/tick-journal.jsonl`, relocated by `KREBS_STATE_DIR`, or `--journal`. Each action writes one line: `repair`, `orphan.release`, `orphan.unstick`, `orphan.fail`, `triage.publish`, `review.publish`, `dispatch.intent` (which carries the full command), `dispatch.write`, `dispatch.publish`, `dispatch.dropped`, plus one `tick` summary line. A failed write whose outcome is unknown (a timeout, a 5xx) is left pending without verification. The next tick publishes only if the write is actually on the ticket. `tick.lock` in the same directory keeps a hand-run tick from overlapping a scheduled one. A dry run never writes the journal.
