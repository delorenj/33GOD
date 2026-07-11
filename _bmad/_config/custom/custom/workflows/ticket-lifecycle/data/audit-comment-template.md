# Audit Comment Template

Structured comment format posted to Plane at each state transition.
Designed for programmatic parsing by downstream consumers.

## Format

```
[TICKET-LIFECYCLE] State Transition
---
from: {previous_state}
to: {new_state}
timestamp: {ISO 8601}
agent: {agent_name or "orchestrator"}
reason: {brief reason for transition}
details: {optional structured details}
---
```

## Examples

### Triage -> Ready (AC Sufficient)
```
[TICKET-LIFECYCLE] State Transition
---
from: triage
to: ready
timestamp: 2026-03-08T14:30:00Z
agent: orchestrator
reason: AC passed sufficiency rubric (4/4 criteria met)
---
```

### QA -> In Progress (AC Failed)
```
[TICKET-LIFECYCLE] State Transition
---
from: qa
to: in_progress
timestamp: 2026-03-08T16:45:00Z
agent: qa-agent
reason: AC verification failed (2/5 items failed)
retry: 1/3
details:
  failed_items:
    - ac_item: "User sees confirmation toast after save"
      expected: "Toast appears within 1s of save action"
      observed: "No toast rendered. Save completes silently."
    - ac_item: "Form validates email format"
      expected: "Invalid email shows inline error"
      observed: "Form submits without validation"
  passed_items: [1, 3, 5]
---
```
