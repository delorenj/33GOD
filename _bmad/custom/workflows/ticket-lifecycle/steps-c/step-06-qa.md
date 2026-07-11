---
name: 'step-06-qa'
description: 'Spawn QA Agent for line-item AC verification with retry loop handling'

doneStepFile: './step-07-complete.md'
retryStepFile: './step-04-implement.md'
auditCommentTemplate: '../data/audit-comment-template.md'
workflowConfig: '../workflow.yaml'
---

# Step 6: QA Verification via QA Agent

## STEP GOAL:

To spawn a QA Agent that verifies each acceptance criteria item line-by-line, handling pass/fail/retry/blocked outcomes.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- Read the complete step file before taking any action.
- If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread.

### Role Reinforcement:

- You are a workflow orchestrator delegating QA verification to a specialized agent.
- You provide the QA Agent with AC items and code changes. You do not verify AC yourself.
- The QA Agent is a BMAD agent (Claude Code session-scoped), spawned on-demand.

### Step-Specific Rules:

- Focus ONLY on delegating QA verification and handling the result.
- FORBIDDEN to verify AC yourself. Delegate to QA Agent.
- FORBIDDEN to fix code. Route failures back to Coding Agent (step 4).
- Track retry count. Max retries loaded from {workflowConfig}.
- On re-entry after a fix, only failed items need re-verification.

## EXECUTION PROTOCOLS:

- Load retry limit from {workflowConfig}.
- Track which AC items have previously passed (partial pass tracking).
- Spawn QA Agent for line-item verification.
- Handle: all pass -> done, partial fail + retries available -> retry, max retries -> blocked.

## CONTEXT BOUNDARIES:

- Step 5 confirmed: tests pass, coverage maps to AC.
- Focus: functional AC verification (does the implementation actually satisfy each AC item?).
- Dependencies: passing tests from step 5, AC items, code changes.

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise.

### 1. Load Retry Configuration

Read {workflowConfig} to get `qa.max_retries` (default: 3).

Check current retry count from ticket context:
- If this is the first QA pass: retry_count = 0
- If returning from a failed QA cycle: increment retry_count

### 2. Determine Items to Verify

**If first QA pass (retry_count == 0):**
- Verify ALL AC items.

**If retry (retry_count > 0):**
- Only verify previously failed AC items.
- Previously passed items retain their pass status.

### 3. Spawn QA Agent Sub-Agent

Launch a sub-agent with the role of **QA Agent**:

**Agent Instructions:**
"You are a QA Agent verifying acceptance criteria for ticket {ticket_id}: {ticket_title}.

Verify each of the following AC items by testing the actual implementation:
{ac_items_to_verify}

For EACH item, produce a verdict:
- PASS: The implementation satisfies this AC item. Include evidence.
- FAIL: The implementation does NOT satisfy this AC item. Include:
  - The AC item text
  - Expected behavior
  - Observed behavior

Be thorough. Test edge cases where the AC implies them. Do not assume correctness from test results alone. Manually verify the actual behavior.

Return: structured per-item verdicts."

### 4. Aggregate Results

Combine QA Agent results with any previously passed items to produce a complete AC verification report:

For each AC item:
- Item text
- Verdict (PASS/FAIL)
- Evidence or defect details

### 5. Branch Based on Results

**IF ALL AC ITEMS PASS:**

Post audit comment using {auditCommentTemplate}:
```
[TICKET-LIFECYCLE] State Transition
---
from: qa
to: done
timestamp: {ISO 8601}
agent: qa-agent
reason: All AC items verified (100% pass)
details:
  total_items: {count}
  passed: {count}
  retries_used: {retry_count}
---
```

Update ticket status to done.
Broadcast Bloodbank event with `new_state: "done"`.

**Proceeding to completion...**
Immediately load, read entire file, then execute {doneStepFile}.

**IF ANY ITEMS FAIL AND retry_count < max_retries:**

Post audit comment:
```
[TICKET-LIFECYCLE] State Transition
---
from: qa
to: in_progress
timestamp: {ISO 8601}
agent: qa-agent
reason: AC verification failed ({failed_count}/{total_count} items failed)
retry: {retry_count + 1}/{max_retries}
details:
  failed_items:
    - ac_item: "{item text}"
      expected: "{expected behavior}"
      observed: "{observed behavior}"
  passed_items: [{list of passed item indices}]
---
```

Update ticket status to in_progress.
Broadcast Bloodbank event with `new_state: "in_progress"`.

**Routing back to implementation with defect details...**
Immediately load, read entire file, then execute {retryStepFile}.

**IF ANY ITEMS FAIL AND retry_count >= max_retries:**

Post audit comment:
```
[TICKET-LIFECYCLE] State Transition
---
from: qa
to: blocked
timestamp: {ISO 8601}
agent: orchestrator
reason: QA max retries exceeded ({max_retries}/{max_retries}). Ticket blocked.
details:
  still_failing: [{list of AC items still failing with defect details}]
  failure_history: [{summary of each retry attempt}]
---
```

Update ticket status to blocked.
Broadcast `ticket.stale` Bloodbank event with full failure history.

**Ticket blocked. Exiting to completion...**
Immediately load, read entire file, then execute {doneStepFile}.

---

## SYSTEM SUCCESS/FAILURE METRICS

### SUCCESS:

- QA Agent spawned with correct AC items (all on first pass, only failed on retry)
- Per-item verdicts collected with evidence/defect details
- Retry count tracked and max enforced
- Correct branch taken based on results and retry state
- Defect payload includes specific expected vs observed details
- Partial passes preserved across retries

### FAILURE:

- Verifying AC directly instead of delegating to QA Agent
- Re-verifying already-passed items on retry
- Not tracking retry count
- Exceeding max retries without blocking
- Vague defect descriptions (must include expected vs observed)

**Master Rule:** Line-item verification. Track retries. Provide specific defect details on failure.
