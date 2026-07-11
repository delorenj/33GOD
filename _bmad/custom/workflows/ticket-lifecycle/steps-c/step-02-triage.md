---
name: 'step-02-triage'
description: 'Evaluate ticket AC against sufficiency rubric and branch accordingly'

nextStepFile: './step-04-implement.md'
refineStepFile: './step-03-refine.md'
acRubric: '../data/ac-sufficiency-rubric.md'
auditCommentTemplate: '../data/audit-comment-template.md'
---

# Step 2: Triage - AC Sufficiency Evaluation

## STEP GOAL:

To evaluate the ticket's acceptance criteria against the sufficiency rubric and branch to either AC refinement (step 3) or implementation (step 4).

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- Read the complete step file before taking any action.
- If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread.

### Role Reinforcement:

- You are a workflow orchestrator evaluating AC quality against a deterministic rubric.
- You do not subjectively judge AC quality. You apply the 4 binary criteria.
- The rubric is the authority, not your opinion.

### Step-Specific Rules:

- Focus ONLY on AC evaluation against the rubric.
- FORBIDDEN to spawn agents or begin implementation in this step.
- FORBIDDEN to modify AC. If insufficient, route to Plane Captain (step 3).
- Apply all 4 rubric criteria. Do not short-circuit on the first failure.

## EXECUTION PROTOCOLS:

- Load the AC sufficiency rubric from {acRubric}.
- Evaluate each criterion independently.
- Document which criteria passed/failed.
- Branch based on result.

## CONTEXT BOUNDARIES:

- Step 1 provided: ticket ID, title, description, AC field, metadata, project context.
- Focus: AC quality evaluation only.
- Dependencies: ticket context from step 1.

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise.

### 1. Load AC Sufficiency Rubric

Read {acRubric} to load the 4 evaluation criteria:
1. Non-empty
2. Testable assertions
3. Enumerated items
4. Functional requirement coverage

### 2. Extract Acceptance Criteria

From the ticket context acquired in step 1, extract the raw AC field content.

### 3. Evaluate Each Criterion

Apply each of the 4 rubric criteria to the AC content. For each criterion, record:
- Criterion name
- Pass/Fail
- Evidence (what was found or missing)

**Evaluate ALL 4 criteria even if early ones fail.** The complete evaluation is needed for the Plane Captain if refinement is required.

### 4. Determine Sufficiency

```
SUFFICIENT = non_empty AND testable AND enumerated AND fr_coverage
```

### 5. Branch Based on Result

**IF SUFFICIENT (all 4 criteria pass):**

Post audit comment to Plane using {auditCommentTemplate}:
```
[TICKET-LIFECYCLE] State Transition
---
from: triage
to: ready
timestamp: {ISO 8601}
agent: orchestrator
reason: AC passed sufficiency rubric (4/4 criteria met)
---
```

Update ticket status to ready state.

Broadcast Bloodbank event:
```json
{
  "event_type": "ticket.state_changed",
  "payload": {
    "project_id": "{project_id}",
    "ticket_id": "{ticket_id}",
    "previous_state": "triage",
    "new_state": "ready"
  }
}
```

**Proceeding to implementation...**
Immediately load, read entire file, then execute {nextStepFile}.

**IF INSUFFICIENT (any criterion fails):**

Post audit comment to Plane:
```
[TICKET-LIFECYCLE] State Transition
---
from: triage
to: refining
timestamp: {ISO 8601}
agent: orchestrator
reason: AC failed sufficiency rubric ({N}/4 criteria met)
details:
  failed_criteria: [{list of failed criterion names}]
  evidence: [{evidence for each failure}]
---
```

Update ticket status to refining state.

Broadcast Bloodbank event with `new_state: "refining"`.

**Proceeding to AC refinement...**
Immediately load, read entire file, then execute {refineStepFile}.

---

## SYSTEM SUCCESS/FAILURE METRICS

### SUCCESS:

- All 4 rubric criteria evaluated independently
- Complete evidence recorded for each criterion
- Correct branch taken based on evaluation result
- Audit comment posted with full evaluation details
- Bloodbank event broadcast

### FAILURE:

- Short-circuiting evaluation on first failure
- Subjectively judging AC instead of applying rubric
- Not recording evidence for each criterion
- Modifying AC content in this step
- Not posting audit comment before branching

**Master Rule:** The rubric is deterministic. Apply all 4 criteria, record evidence, branch accordingly.
