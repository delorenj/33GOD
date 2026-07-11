---
name: 'step-e-01-assess'
description: 'Assess current workflow configuration and present modification options'

nextStepFile: './step-02-apply.md'
workflowConfig: '../workflow.yaml'
acRubric: '../data/ac-sufficiency-rubric.md'
auditCommentTemplate: '../data/audit-comment-template.md'
eventSchemas: '../data/event-schemas.md'
---

# Step E1: Assess Workflow Configuration

## STEP GOAL:

To load and present the current workflow configuration, identify what can be modified, and gather the user's requested changes.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- Read the complete step file before taking any action.
- YOU ARE A FACILITATOR. Present current state, gather requested changes.

### Role Reinforcement:

- You are a workflow configuration editor.
- Present current values clearly. Let the user decide what to change.

### Step-Specific Rules:

- Focus ONLY on assessment and change gathering.
- FORBIDDEN to apply changes in this step. That is step E2.
- Present all configurable values from workflow.yaml and data files.

## MANDATORY SEQUENCE

### 1. Load Current Configuration

Read {workflowConfig} and present all configurable values:

**AC Sufficiency Rubric:**
- Load {acRubric} and summarize criteria

**QA Configuration:**
- Max retries: {value from config}

**Staleness Durations (minutes):**
- Triage: {value}
- Refining: {value}
- In Progress: {value}
- Review: {value}
- QA: {value}

**Plane State Mapping:**
- Present current state name mappings

**Event Configuration:**
- Load {eventSchemas} and summarize event types

### 2. Present Modification Options

"**Current workflow configuration loaded. What would you like to modify?**

Configurable areas:
1. **AC Rubric** - Add/remove/modify sufficiency criteria
2. **QA Retry Limit** - Change max retry count
3. **Staleness Durations** - Adjust per-state timeout thresholds
4. **State Mapping** - Change Plane status names
5. **Event Schemas** - Modify Bloodbank event payloads
6. **Audit Comment Format** - Change comment template structure

Tell me which area(s) you want to modify and what changes you need."

### 3. Gather Changes

Collect the user's requested modifications. For each change:
- Current value
- Requested new value
- Confirm understanding

### 4. Present MENU OPTIONS

Display: **Select an Option:** [C] Continue to Apply Changes

#### Menu Handling Logic:
- IF C: Save gathered changes, then load, read entire file, then execute {nextStepFile}
- IF Any other: help user, then redisplay menu

---

## SYSTEM SUCCESS/FAILURE METRICS

### SUCCESS:
- All configurable values presented clearly
- User changes gathered with current vs new values
- Changes confirmed before proceeding to apply

### FAILURE:
- Applying changes in this step
- Not presenting current values before gathering changes
- Proceeding without user confirmation
