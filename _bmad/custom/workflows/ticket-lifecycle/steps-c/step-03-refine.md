---
name: 'step-03-refine'
description: 'Spawn Plane Captain sub-agent to define or improve acceptance criteria'

nextStepFile: './step-04-implement.md'
acRubric: '../data/ac-sufficiency-rubric.md'
auditCommentTemplate: '../data/audit-comment-template.md'
planeSkill: '~/.claude/skills/managing-tickets-and-tasks-in-plane/'
---

# Step 3: AC Refinement via Plane Captain

## STEP GOAL:

To spawn a Plane Captain sub-agent that will define or improve the ticket's acceptance criteria until they pass the sufficiency rubric, then transition the ticket to ready state.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- Read the complete step file before taking any action.
- If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread.

### Role Reinforcement:

- You are a workflow orchestrator delegating AC refinement to a specialized agent.
- You provide the Plane Captain with context and rubric failures. You do not refine AC yourself.
- The Plane Captain is a BMAD agent (Claude Code session-scoped), spawned on-demand.

### Step-Specific Rules:

- Focus ONLY on delegating AC refinement and verifying the result.
- FORBIDDEN to write AC yourself. Delegate to Plane Captain.
- FORBIDDEN to begin implementation. That is step 4.
- After refinement, re-evaluate AC against rubric before proceeding.

## EXECUTION PROTOCOLS:

- Spawn Plane Captain sub-agent with ticket context and failed criteria.
- Plane Captain reads ticket, collaborates with PM context, writes AC back to Plane.
- Re-evaluate refined AC against rubric.
- If still insufficient after refinement, mark ticket as blocked.

## CONTEXT BOUNDARIES:

- Step 2 provided: rubric evaluation results, failed criteria with evidence.
- Focus: AC refinement delegation and verification.
- Dependencies: ticket context, rubric failures from step 2.

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise.

### 1. Prepare Plane Captain Context

Assemble the delegation payload for the Plane Captain sub-agent:
- Ticket ID, title, description
- Current AC content (raw)
- Failed rubric criteria with evidence from step 2
- The full rubric from {acRubric} so the Plane Captain knows the target
- Plane API access patterns from {planeSkill}

### 2. Spawn Plane Captain Sub-Agent

Launch a sub-agent with the role of **Plane Captain**:

**Agent Instructions:**
"You are a Plane Captain responsible for defining clear, testable acceptance criteria for ticket {ticket_id}.

Review the ticket description and context. The current AC failed these rubric criteria: {failed_criteria_with_evidence}.

Write new acceptance criteria that satisfy ALL 4 rubric criteria:
1. Non-empty
2. Each item is a testable assertion
3. Items are enumerated (numbered list)
4. At least one item per functional requirement

Update the ticket's AC field in Plane via the API. Return the updated AC content when complete."

### 3. Receive Refined AC

When the Plane Captain sub-agent completes:
- Read the updated AC from Plane (re-fetch ticket to get latest).
- Do NOT trust the sub-agent's return value alone. Verify against Plane.

### 4. Re-Evaluate Against Rubric

Apply the same 4-criteria rubric from {acRubric} to the refined AC.

**IF SUFFICIENT (all 4 criteria pass):**

Post audit comment using {auditCommentTemplate}:
```
[TICKET-LIFECYCLE] State Transition
---
from: refining
to: ready
timestamp: {ISO 8601}
agent: plane-captain
reason: AC refined and passed sufficiency rubric (4/4 criteria met)
---
```

Update ticket status to ready state.
Broadcast Bloodbank event with `new_state: "ready"`.

**Proceeding to implementation...**
Immediately load, read entire file, then execute {nextStepFile}.

**IF STILL INSUFFICIENT:**

Post audit comment:
```
[TICKET-LIFECYCLE] State Transition
---
from: refining
to: blocked
timestamp: {ISO 8601}
agent: orchestrator
reason: AC refinement failed. Plane Captain could not produce sufficient AC.
details:
  still_failing: [{list of criteria still failing}]
---
```

Update ticket status to blocked state.
Broadcast `ticket.stale` Bloodbank event.
EXIT workflow. This ticket needs human intervention.

---

## SYSTEM SUCCESS/FAILURE METRICS

### SUCCESS:

- Plane Captain spawned with complete context and rubric
- AC refined and re-verified against rubric
- Ticket transitioned to ready (or blocked if refinement failed)
- Audit comment posted with transition details
- Bloodbank event broadcast

### FAILURE:

- Writing AC directly instead of delegating to Plane Captain
- Not re-evaluating refined AC against rubric
- Trusting sub-agent return without verifying Plane state
- Proceeding to implementation without rubric passing

**Master Rule:** Delegate, verify, then proceed. Never skip verification.
