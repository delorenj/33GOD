# krebs tick

The Krebs lifecycle v2 dispatcher ([spec](../spec/lifecycle.v2.yaml), [explainer](../docs/lifecycle.md)). It is the only thing that moves a ticket from Todo to In Progress. Candybar runs it every 10 minutes ([`../.candybars/krebs-tick.candybar.toml`](../.candybars/krebs-tick.candybar.toml)).

```bash
node ~/code/33GOD/krebs/bin/krebs.mjs tick --dry-run            # read-only plan, every scope
node ~/code/33GOD/krebs/bin/krebs.mjs tick --dry-run --board TOLT --verbose
node ~/code/33GOD/krebs/bin/krebs.mjs tick --json               # what Candybar runs (live)
cd ~/code/33GOD/krebs && npm test                               # node:test, fakes only
```

It has no dependencies and no install step. It loads Pilot's Plane client from `../pilot/src` and the bloodbank n8n package's built `dist/` from `../bloodbank/integrations/n8n-nodes-bloodbank`. `KREBS_PILOT_DIR` and `KREBS_BLOODBANK_N8N_DIR` override those paths. If `dist/` is stale, rebuild it there; Krebs takes the routing, the command ids, the delegation prompt and the envelope from it.

## What one tick does

For each scope, in agent-id order:

1. **Owed publishes.** A dispatch whose publish failed on an earlier tick is republished with the same command. The tick republishes only while the ticket is still In Progress with no `lifecycle:review` and no hold label. The command is replayed from the journal byte for byte, because the gateway rejects a reused command id whose envelope digest differs. After 24 hours the tick drops the dispatch and reports it.
2. **Repairs.** It removes `lifecycle:review` from tickets that are not In Progress, and `agent:working` from Done and Cancelled tickets. Each repair is one delta label write.
3. **Slots.** `occupied` counts In Progress tickets that carry neither `lifecycle:review` nor a hold label. `free` is `plane.wip` (default 2) minus `occupied`, and never goes below 0. A scope over its limit drains: nothing is dispatched and nothing is evicted.
4. **Dispatch.** A candidate is a Todo ticket that carries `lifecycle:triaged`, has no `agent:working`, no hold label and no `epic`/`epic:*` label, and has no `blocked_by` relation to a ticket outside the completed and cancelled groups. Candidates are ordered by `sort_order`, then priority, then sequence id. For each pick, the tick re-reads the ticket live and checks the guard again. It then makes one Plane write (In Progress, `+agent:working`, and `start_date` if none is set) and publishes `bloodbank.agent.invocation.start` with reason `ticket-delegation` to the scope owner.

The command id is `fleetCommandId(dispatchId, "delegateTicket", agent)`, where `dispatchId = uuid5("krebs:dispatch:<board>:<ticket>:<updated_at before the write>")`. A retry of the same dispatch reuses the id. A later re-dispatch of the same ticket, for example after a SENT BACK, gets a new one.

## Scopes

Scopes come from `~/.hermes/agents-registry.yaml`, one per row that has a `plane:` block, with these exceptions:

- **No board id.** A row whose plane block has no `project_id` is not a scope. Launch directors are like this: they give verdicts but own no board.
- **Advisory.** A row with `board_scope: advisory` is not a scope.
- **Retired.** `flume retire` turns bloodbank off and removes the plane claim, so a retired row has no plane block left. A row whose `status` or `employment` is `retired` or `suspended`, or that has `retired: true` or a `retired_at`, is also skipped.
- **Not fleet-addressable.** The tick applies the same checks as the n8n Fleet node and the gateway: `profile_name` is set, `bloodbank.enabled` is true or absent, `gateway_scope` is `fleet`, and `target_agent_id` equals the row id.
- **Fenced (best effort).** The tick reads `<project_path>/.project.json`. If `execution.mode` is present and is not `legacy`, the row is skipped. A missing or unreadable manifest counts as legacy. A row whose `project_path` is a parent repo is judged by the parent's manifest. For example, `tolt-pm` points at `~/code/tolt`, not at the game submodule.

On a shared board, each ticket is routed by `resolveFleetAgentForBoard`, the same resolver the n8n triage lane uses (`scope_label`, then `scope_default`). Krebs and triage therefore always agree on which scope owns a ticket. Unlabelled TOLT intake belongs to `tolt-pm`.

Row knobs: `plane.wip` (non-negative integer, default 2) and `plane.review` (when `true`, handback is `lifecycle:review`; otherwise the ticket is closed Done). The handback rule is appended to the dispatch prompt.

## Journal

`~/.local/state/krebs/tick-journal.jsonl`, relocated by `KREBS_STATE_DIR`, or `--journal`. Each action writes one line: `repair`, `dispatch.intent` (which carries the full command), `dispatch.write`, `dispatch.publish`, `dispatch.dropped`, plus one `tick` summary line. A failed write whose outcome is unknown (a timeout, a 5xx) is left pending without verification. The next tick publishes only if the write is actually on the ticket. `tick.lock` in the same directory keeps a hand-run tick from overlapping a scheduled one. A dry run never writes the journal.
