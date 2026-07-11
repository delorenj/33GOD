---
name: 'step-07-complete'
description: 'Broadcast completion event, post final audit comment, and exit workflow'

auditCommentTemplate: '../data/audit-comment-template.md'
eventSchemas: '../data/event-schemas.md'
---

# Step 7: Completion

## STEP GOAL:

To broadcast the final Bloodbank event, post the closing audit comment to Plane, and exit the workflow.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- Read the complete step file before taking any action.
- If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread.

### Role Reinforcement:

- You are a workflow orchestrator performing final bookkeeping.
- This is the last step. Clean exit with full audit trail.

### Step-Specific Rules:

- Focus ONLY on completion bookkeeping.
- FORBIDDEN to modify ticket state beyond what was set in the previous step.
- Handle both "done" and "blocked" terminal states.

## EXECUTION PROTOCOLS:

- Post final audit comment summarizing the full lifecycle.
- Broadcast terminal Bloodbank event.
- Exit cleanly.

## CONTEXT BOUNDARIES:

- Previous step set the terminal state (done or blocked).
- Focus: audit trail completion and event broadcasting.
- This is the final step. No next step.

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise.

### 1. Determine Terminal State

Check the ticket's current state (set by the previous step):
- **done**: All AC items verified, ticket complete.
- **blocked**: Max retries exceeded, AC ambiguity, or refinement failure.

### 2. Post Final Audit Summary

Post a summary audit comment to Plane using {auditCommentTemplate}:

**For "done" state:**
```
[TICKET-LIFECYCLE] Workflow Complete
---
terminal_state: done
timestamp: {ISO 8601}
agent: orchestrator
summary: Ticket processed through full lifecycle. All AC items verified.
lifecycle:
  started: {workflow_start_timestamp}
  completed: {now}
  states_visited: [{list of all states the ticket passed through}]
  retries_used: {qa_retry_count}
  agents_spawned: [{list: plane-captain (if used), coding-agent, qa-agent}]
---
```

**For "blocked" state:**
```
[TICKET-LIFECYCLE] Workflow Complete
---
terminal_state: blocked
timestamp: {ISO 8601}
agent: orchestrator
summary: Ticket blocked. Requires external intervention.
reason: {blocked_reason from previous step}
lifecycle:
  started: {workflow_start_timestamp}
  blocked_at: {now}
  states_visited: [{list of all states}]
  blocking_details: {details from previous step}
---
```

### 3. Broadcast Terminal Event

Using {eventSchemas}, broadcast the final Bloodbank event:

```json
{
  "event_type": "ticket.state_changed",
  "version": "v1",
  "payload": {
    "project_id": "{project_id}",
    "ticket_id": "{ticket_id}",
    "previous_state": "{previous_state}",
    "new_state": "{terminal_state}",
    "trigger_source": "ticket-lifecycle-workflow",
    "terminal": true
  }
}
```

### 4. Exit Workflow

**Workflow complete.** No further steps.

Report final status:
- Ticket ID and title
- Terminal state (done or blocked)
- Total states visited
- Agents spawned
- Retries used (if any)

---

## SYSTEM SUCCESS/FAILURE METRICS

### SUCCESS:

- Final audit summary posted with full lifecycle details
- Terminal Bloodbank event broadcast with `terminal: true`
- Clean exit with status report
- Both "done" and "blocked" paths handled

### FAILURE:

- Exiting without posting final audit summary
- Not broadcasting terminal event
- Attempting further state transitions after completion
- Missing lifecycle details in summary

**Master Rule:** Clean exit. Full audit trail. No loose ends.
