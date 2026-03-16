# Story: GOD-20 / BB-4 — Agent Label Routing in Infra Dispatcher

**Ticket:** GOD-20 (AGENT-CTRL-1: Agent command adapter rollout)  
**Sub-ticket:** BB-4 (Inbox intake webhook bridge)  
**Branch (main):** `GOD-20-agent-ctrl-checkpoint`  
**Branch (bloodbank):** `BB-4-intake-webhook-bridge`  
**Status:** In Progress

---

## User Story

As the 33GOD platform, I want Plane ticket state-change webhooks to automatically route
to the correct agent based on an `agent:X` label, so that:
- Tickets labeled `agent:grolf` route to `command.grolf.assign_ticket`
- Tickets labeled `agent:lenoon` route to `command.lenoon.assign_ticket`
- Tickets with NO agent label in a `todo`/`unstarted` state route to `command.cack.examine`
- This routing is framework-agnostic (not locked to OpenClaw)

---

## Context

The `infra_dispatcher` already:
1. Consumes `webhook.plane.#` events from Bloodbank
2. Applies a ready-gate (state in `INFRA_READY_STATES`, labels include `INFRA_READY_LABELS`)
3. Extracts `comp:X` labels to determine target component/agent
4. Publishes `command.{target}.assign_ticket` via Bloodbank → Command Adapter

**Gap:** The dispatcher uses `comp:` labels (component-scoped) as its routing signal. TASK.md
requires explicit `agent:X` labels so any agent — OpenClaw or otherwise — can be directly
addressed on a ticket.

**Routing priority (new):**
```
agent:X label  →  command.X.assign_ticket
comp:X label   →  command.X.assign_ticket   (existing fallback)
(nothing)      →  command.{default_agent=cack}.examine
```

---

## Acceptance Criteria

- [ ] `AC-1`: A ticket with label `agent:grolf` publishes `command.grolf.assign_ticket`
- [ ] `AC-2`: A ticket with label `agent:lenoon` publishes `command.lenoon.assign_ticket`
- [ ] `AC-3`: A ticket with `comp:bloodbank` but no `agent:X` label publishes `command.bloodbank.assign_ticket` (unchanged behavior)
- [ ] `AC-4`: A ticket with neither `agent:` nor `comp:` label publishes `command.cack.examine`
- [ ] `AC-5`: `INFRA_AGENT_LABEL_PREFIX` env var configures the agent label prefix (default: `agent:`)
- [ ] `AC-6`: Dead code in `DispatcherConfig.from_env()` (lines 166–199 referencing removed fields) is removed
- [ ] `AC-7`: `build_command_payload()` includes `agent_label` field in the envelope
- [ ] `AC-8`: Tests cover all four routing scenarios

---

## Tasks

- [x] Task 1: Read and understand current `infra_dispatcher.py` state
- [ ] Task 2: Remove dead code from `DispatcherConfig.from_env()` (lines 166–199)
- [ ] Task 3: Add `agent_label_prefix: str = "agent:"` to `DispatcherConfig`
- [ ] Task 4: Implement `_extract_agent_label(labels, prefix) -> str | None`
- [ ] Task 5: Update `evaluate_ready_issue()` to extract and return `agent_label`
- [ ] Task 6: Update `publish_command_event()` — routing priority + `examine` action for default
- [ ] Task 7: Update `build_dispatch_message()` + `build_command_payload()` for `agent_label`
- [ ] Task 8: Update `DispatcherConfig.from_env()` to load `INFRA_AGENT_LABEL_PREFIX`
- [ ] Task 9: Add/update tests (4 routing scenarios)
- [ ] Task 10: `mise run test` passes

---

## Notes

- M2 check (`run_component_check`) uses `comp:` label only. Agent-label routing skips M2 check
  naturally (no component → `{"status": "skipped", "reason": "missing_component"}`).
- Action semantics: `assign_ticket` for explicit routing; `examine` for Cack fallback (triage).
- Env var `INFRA_DEFAULT_AGENT` still controls the fallback agent (default: `cack`).
