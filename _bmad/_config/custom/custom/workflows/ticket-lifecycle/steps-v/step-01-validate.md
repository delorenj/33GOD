---
name: 'step-v-01-validate'
description: 'Validate all workflow prerequisites: Plane config, Bloodbank CLI, Holyfields schemas, and workflow configuration'

workflowConfig: '../workflow.yaml'
acRubric: '../data/ac-sufficiency-rubric.md'
eventSchemas: '../data/event-schemas.md'
---

# Step V1: Validate Workflow Prerequisites

## STEP GOAL:

To verify that all external dependencies, configuration files, and tooling required by the ticket-lifecycle workflow are present and correctly configured.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- Read the complete step file before taking any action.
- Report ALL findings before concluding. Do not stop at the first failure.

### Role Reinforcement:

- You are a diagnostic checker. Read-only. No modifications.
- Present clear pass/fail results with actionable remediation for failures.

### Step-Specific Rules:

- Focus ONLY on prerequisite validation.
- FORBIDDEN to modify any files, configuration, or state.
- FORBIDDEN to process tickets or trigger workflows.
- Check ALL items even if early checks fail.

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise.

### 1. Validate Plane Configuration

**Check `.project.json` in project root:**
- [ ] File exists
- [ ] Contains a `ticket_provider` block
- [ ] `ticket_provider.workspace` is present
- [ ] `ticket_provider.board_id` is present and non-empty

**Check `~/.claude/plane-workspaces.json`:**
- [ ] File exists
- [ ] Contains entry matching `ticket_provider.workspace` from `.project.json`
- [ ] Entry has `api_key` and `base_url`

**Check Plane skill:**
- [ ] Directory exists at `~/.claude/skills/managing-tickets-and-tasks-in-plane/`

**Validate Plane API connectivity:**
- [ ] Attempt a read-only API call (e.g., list states) to confirm credentials work

### 2. Validate Bloodbank CLI

**Check Bloodbank installation:**
- [ ] Directory exists at `~/code/33GOD/bloodbank/`
- [ ] CLI is executable (check for main entry point)

**Check Bloodbank connectivity:**
- [ ] Attempt a health check or connection test to RabbitMQ

### 3. Validate Holyfields Schemas

**Check schema registry:**
- [ ] Directory exists at `~/code/33GOD/holyfields/schemas/`
- [ ] Contains event schema definitions

**Verify required event types exist:**
- [ ] `ticket.state_changed` schema present or documentable
- [ ] `ticket.stale` schema present or documentable

### 4. Validate Workflow Configuration

**Check {workflowConfig}:**
- [ ] File exists and is valid YAML
- [ ] `ac_rubric` section present with all 4 criteria
- [ ] `qa.max_retries` defined (numeric, > 0)
- [ ] `staleness` section with durations for: triage, refining, in_progress, review, qa
- [ ] `plane_states` mapping present

**Check {acRubric}:**
- [ ] File exists
- [ ] Contains all 4 binary criteria (non_empty, testable, enumerated, fr_coverage)

**Check {eventSchemas}:**
- [ ] File exists
- [ ] Documents `ticket.state_changed` payload
- [ ] Documents `ticket.stale` payload

### 5. Present Validation Report

Display a structured report:

```
TICKET-LIFECYCLE PREREQUISITE VALIDATION
========================================

Plane Configuration:
  .project.json (ticket_provider) [PASS/FAIL]
  plane-workspaces.json ...... [PASS/FAIL]
  Plane skill ................ [PASS/FAIL]
  Plane API connectivity ..... [PASS/FAIL]

Bloodbank:
  CLI installation ........... [PASS/FAIL]
  RabbitMQ connectivity ...... [PASS/FAIL]

Holyfields:
  Schema registry ............ [PASS/FAIL]
  Required event schemas ..... [PASS/FAIL]

Workflow Configuration:
  workflow.yaml .............. [PASS/FAIL]
  AC sufficiency rubric ...... [PASS/FAIL]
  Event schema docs .......... [PASS/FAIL]

Overall: [ALL CHECKS PASSED / X of Y FAILED]
```

**IF ALL PASS:**
"**All prerequisites validated. Workflow is ready for execution.**"

**IF ANY FAIL:**
For each failure, provide:
- What failed
- Why it matters
- How to fix it

"**Prerequisites incomplete. Resolve the above issues before running the workflow.**"

---

## SYSTEM SUCCESS/FAILURE METRICS

### SUCCESS:

- All prerequisite categories checked (Plane, Bloodbank, Holyfields, Config)
- Every check item evaluated even if others fail
- Clear pass/fail report with remediation steps for failures
- No files or state modified during validation

### FAILURE:

- Stopping at the first failure without checking remaining items
- Modifying any configuration or state
- Attempting to process tickets or trigger workflow execution
- Missing remediation guidance for failed checks

**Master Rule:** Read-only diagnostic. Check everything. Report clearly. Fix nothing.
