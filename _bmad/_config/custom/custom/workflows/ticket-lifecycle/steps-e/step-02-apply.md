---
name: 'step-e-02-apply'
description: 'Apply requested configuration changes to workflow files'

workflowConfig: '../workflow.yaml'
acRubric: '../data/ac-sufficiency-rubric.md'
auditCommentTemplate: '../data/audit-comment-template.md'
eventSchemas: '../data/event-schemas.md'
---

# Step E2: Apply Configuration Changes

## STEP GOAL:

To apply the gathered configuration changes to the appropriate workflow files.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- Read the complete step file before taking any action.
- Apply changes precisely as confirmed in step E1.

### Role Reinforcement:

- You are applying confirmed changes. No improvisation.
- Edit only the files that need modification.

### Step-Specific Rules:

- Focus ONLY on applying confirmed changes.
- FORBIDDEN to make changes not confirmed in step E1.
- After applying, verify each change was applied correctly.

## MANDATORY SEQUENCE

### 1. Apply Changes by Target File

For each confirmed change from step E1:

**If modifying workflow.yaml:**
- Read {workflowConfig}
- Apply the specific value change
- Write updated file

**If modifying AC rubric:**
- Read {acRubric}
- Apply criteria changes
- Write updated file

**If modifying audit comment template:**
- Read {auditCommentTemplate}
- Apply format changes
- Write updated file

**If modifying event schemas:**
- Read {eventSchemas}
- Apply schema changes
- Write updated file

### 2. Verify Changes

For each modified file, re-read and confirm the change was applied correctly.

### 3. Summary

Present a summary of all changes applied:
- File modified
- What changed (before -> after)

"**All changes applied. Workflow configuration updated.**"

---

## SYSTEM SUCCESS/FAILURE METRICS

### SUCCESS:
- All confirmed changes applied to correct files
- Each change verified after application
- Summary presented with before/after values

### FAILURE:
- Applying unconfirmed changes
- Modifying wrong files
- Not verifying changes after application
