---
name: 'step-04-implement'
description: 'Spawn Coding Agent sub-agent to implement ticket requirements and write tests'

nextStepFile: './step-05-review.md'
blockedStepFile: './step-07-complete.md'
auditCommentTemplate: '../data/audit-comment-template.md'
---

# Step 4: Implementation via Coding Agent

## STEP GOAL:

To spawn a Coding Agent sub-agent that implements the ticket requirements and writes tests covering each acceptance criteria item.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- Read the complete step file before taking any action.
- If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread.

### Role Reinforcement:

- You are a workflow orchestrator delegating implementation to a specialized agent.
- You provide the Coding Agent with AC items as goals. You do not write code.
- The Coding Agent is a BMAD agent (Claude Code session-scoped), spawned on-demand.

### Step-Specific Rules:

- Focus ONLY on delegating implementation and handling the result.
- FORBIDDEN to write code yourself. Delegate to Coding Agent.
- FORBIDDEN to verify AC. That is QA's job (step 6).
- If the Coding Agent reports AC ambiguity, route to blocked state.

## EXECUTION PROTOCOLS:

- Spawn Coding Agent with AC items as implementation goals.
- Coding Agent writes code + tests, commits to repo.
- On completion, transition to review gate.
- On AC ambiguity discovery, transition to blocked.

## CONTEXT BOUNDARIES:

- Previous steps provided: ticket context, verified AC items, project context.
- Focus: implementation delegation.
- Dependencies: sufficient AC from step 2/3.

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise.

### 1. Prepare Coding Agent Context

Assemble the delegation payload:
- Ticket ID, title, description
- Enumerated AC items (each item is an implementation goal)
- Project context (repo path, tech stack if available from project-context.md)
- Any defect details from prior QA failures (if this is a retry loop)

### 2. Update Ticket Status

Post audit comment using {auditCommentTemplate}:
```
[TICKET-LIFECYCLE] State Transition
---
from: ready
to: in_progress
timestamp: {ISO 8601}
agent: orchestrator
reason: Implementation starting. Coding agent spawned.
---
```

Update ticket status to in_progress.
Broadcast Bloodbank event with `new_state: "in_progress"`.

### 3. Spawn Coding Agent Sub-Agent

Launch a sub-agent with the role of **Coding Agent**:

**Agent Instructions:**
"You are a Coding Agent implementing ticket {ticket_id}: {ticket_title}.

Your implementation goals are the acceptance criteria items:
{enumerated_ac_items}

{if_retry: 'IMPORTANT: This is retry #{retry_count}. Previous QA found these defects: {defect_details}. Focus on fixing ONLY the failed AC items.'}

Requirements:
1. Implement code changes that satisfy each AC item
2. Write unit tests that verify each AC item (1:1 mapping)
3. Ensure all existing tests still pass (no regressions)
4. Commit changes to the repository

If you discover that any AC item is ambiguous or contradictory, STOP and report the ambiguity. Do not guess.

Return: summary of changes, test results, and any AC ambiguity discovered."

### 4. Handle Coding Agent Result

**IF implementation completed successfully:**

**Proceeding to review gate...**
Immediately load, read entire file, then execute {nextStepFile}.

**IF AC ambiguity discovered:**

Post audit comment:
```
[TICKET-LIFECYCLE] State Transition
---
from: in_progress
to: blocked
timestamp: {ISO 8601}
agent: coding-agent
reason: AC ambiguity discovered during implementation
details:
  ambiguous_items: [{list of ambiguous AC items with explanation}]
---
```

Update ticket status to blocked.
Broadcast `ticket.stale` Bloodbank event.
Load {blockedStepFile} to complete with blocked status.

---

## SYSTEM SUCCESS/FAILURE METRICS

### SUCCESS:

- Coding Agent spawned with AC items as goals
- Implementation delegated, not performed directly
- On success, transitioned to review gate
- On AC ambiguity, transitioned to blocked with details
- Audit comments posted at each transition
- Bloodbank events broadcast

### FAILURE:

- Writing code directly instead of delegating
- Not passing defect details on retry loops
- Ignoring AC ambiguity reports from Coding Agent
- Not posting audit comment before transition

**Master Rule:** Delegate implementation. Handle both success and ambiguity paths.
