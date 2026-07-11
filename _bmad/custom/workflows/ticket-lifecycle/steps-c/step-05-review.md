---
name: 'step-05-review'
description: 'Validate tests pass and coverage maps to AC items before QA'

nextStepFile: './step-06-qa.md'
retryStepFile: './step-04-implement.md'
auditCommentTemplate: '../data/audit-comment-template.md'
---

# Step 5: Review Gate

## STEP GOAL:

To validate that all tests pass, test coverage maps to AC items, and no regressions exist before handing off to QA.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- Read the complete step file before taking any action.
- If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread.

### Role Reinforcement:

- You are a workflow orchestrator performing automated review checks.
- This is a validation gate, not a code review. Check tests and coverage, not code quality.

### Step-Specific Rules:

- Focus ONLY on test validation and AC coverage mapping.
- FORBIDDEN to modify code or tests. If they fail, route back to implementation.
- FORBIDDEN to perform QA verification. That is step 6.
- This is an auto-proceed validation step. No human interaction.

## EXECUTION PROTOCOLS:

- Run the test suite.
- Verify test coverage maps to AC items.
- Check for regressions in existing tests.
- Branch: pass -> QA, fail -> back to implementation.

## CONTEXT BOUNDARIES:

- Step 4 produced: code changes + tests committed to repo.
- Focus: automated test validation only.
- Dependencies: committed code and tests from Coding Agent.

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise.

### 1. Run Test Suite

Execute the project's test suite. Capture:
- Total tests run
- Tests passed
- Tests failed
- Test output/errors

### 2. Verify AC Coverage

For each AC item, check that at least one test exists that explicitly verifies it.
- Map each AC item to its corresponding test(s).
- Identify any AC items with no test coverage.

### 3. Check for Regressions

Compare current test results against the baseline:
- Any previously passing tests now failing?
- Any test suite errors unrelated to the new changes?

### 4. Evaluate Review Gate

**ALL THREE must pass:**
1. All tests pass (zero failures)
2. Every AC item has at least one covering test
3. No regressions in existing test suite

**IF ALL PASS:**

Post audit comment using {auditCommentTemplate}:
```
[TICKET-LIFECYCLE] State Transition
---
from: review
to: qa
timestamp: {ISO 8601}
agent: orchestrator
reason: Review gate passed. All tests pass, AC coverage complete, no regressions.
details:
  tests_run: {count}
  tests_passed: {count}
  ac_coverage: {N}/{total} items covered
---
```

Update ticket status to qa.
Broadcast Bloodbank event with `new_state: "qa"`.

**Proceeding to QA verification...**
Immediately load, read entire file, then execute {nextStepFile}.

**IF ANY FAIL:**

Post audit comment:
```
[TICKET-LIFECYCLE] State Transition
---
from: review
to: in_progress
timestamp: {ISO 8601}
agent: orchestrator
reason: Review gate failed. Routing back to implementation.
details:
  test_failures: [{list of failing tests}]
  uncovered_ac: [{list of AC items without tests}]
  regressions: [{list of regressed tests}]
---
```

Update ticket status back to in_progress.
Broadcast Bloodbank event with `new_state: "in_progress"`.

**Routing back to implementation with review failures...**
Immediately load, read entire file, then execute {retryStepFile}.

---

## SYSTEM SUCCESS/FAILURE METRICS

### SUCCESS:

- Test suite executed completely
- AC-to-test coverage mapping performed
- Regression check completed
- Correct branch taken based on all three checks
- Audit comment includes test metrics

### FAILURE:

- Not running the full test suite
- Skipping AC coverage mapping
- Modifying code or tests in this step
- Not documenting specific failures when routing back

**Master Rule:** This is an automated gate. Check, record, branch. Never fix.
