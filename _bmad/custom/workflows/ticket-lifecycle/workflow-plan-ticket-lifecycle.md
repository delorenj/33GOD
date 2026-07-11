---
stepsCompleted: ['step-01-discovery', 'step-02-classification', 'step-03-requirements', 'step-04-tools', 'step-05-plan-review', 'step-06-design', 'step-07-foundation', 'step-08-build-first-step', 'step-09-build-remaining-steps', 'step-10-confirmation']
created: 2026-03-08
status: COMPLETE
completionDate: 2026-03-08
approvedDate: 2026-03-08
confirmationDate: 2026-03-08
confirmationType: new_workflow
coverageStatus: complete
workflowName: ticket-lifecycle
---

# Workflow Creation Plan

## Discovery Notes

**User's Vision:**
A fully autonomous, multi-agent ticket lifecycle workflow that takes a Plane board ticket from raw backlog to verified-complete with zero human intervention. Momo (OpenClaw PM agent) orchestrates via Bloodbank events, delegating to BMAD agents for AC refinement, development, and QA validation. Universal across all projects.

**Who It's For:**
Momo (the PM/orchestrator agent) triggers or receives triggers for this workflow. BMAD agents execute the individual phases. The workflow is project-agnostic, resolving project context via the `ticket_provider` block in `.project.json` + workspace detection.

**What It Produces:**
Completed, QA-verified tickets with full audit trail in Plane. Each ticket progresses through a defined state machine with clear handoffs between agent roles.

**Key Insights:**

- Momo is the only agent with Bloodbank/OpenClaw access. All other agents are BMAD (Claude Code session-scoped).
- Three trigger modes: human request to Momo, Momo requesting a BMAD agent, or Bloodbank event from Plane on ticket state change to "ready."
- The Plane Captain agent is spawned on-demand only when AC is insufficient. Not a persistent agent.
- Coding agents receive implementation tasks but Momo never writes code.
- QA agent verifies each AC line item. Failures route back to coding agent with specific defect details.
- Bloodbank event schemas exist at ~/code/33GOD/holyfields/schemas/agent/ (task.assigned, task.completed, message.sent).
- Plane integration via existing skill: managing-tickets-and-tasks-in-plane (API, label routing, ticket scoring).
- The workflow must be universal: works with any project that has a `ticket_provider` block in `.project.json` and Plane workspace registration.

**Agent Roster:**
| Agent | Type | Role | Communication |
|-------|------|------|---------------|
| Momo | OpenClaw | PM/Orchestrator | Bloodbank events (send/receive) |
| Plane Captain | BMAD | AC Refinement | Spawned by workflow, reads/writes Plane API |
| Coding Agent | BMAD | Implementation | Spawned by workflow, writes code + tests |
| QA Agent | BMAD | AC Verification | Spawned by workflow, reads Plane AC, validates |

**State Machine:**
```
ticket.backlog
  -> ticket.triage (evaluate AC against rubric)
    -> [AC insufficient] ticket.refining (Plane Captain defines AC)
      -> ticket.ready
    -> [AC sufficient] ticket.ready
  -> ticket.in-progress (Coding agent implementing)
    -> [implementation discovers AC ambiguity] ticket.blocked (emit ticket.stale event)
  -> ticket.review (Tests passing, code complete)
  -> ticket.qa (QA agent verifying AC line-by-line)
    -> [all AC verified] ticket.done (broadcast Bloodbank event with project_id)
    -> [AC items failed, retries < 3] ticket.in-progress (route back with per-item defect details)
    -> [AC items failed, retries >= 3] ticket.blocked (emit ticket.stale event)
  -> ticket.blocked (requires external intervention, staleness event broadcast)
```

**Staleness Detection:**
Each state has a max duration. If exceeded, the workflow emits a `ticket.stale` Bloodbank event with `project_id`, `ticket_id`, `stuck_state`, and `duration`. The workflow does not retry or escalate. Consumers decide.

**Integration Points:**
- Plane REST API (ticket CRUD, status transitions, label routing)
- Bloodbank CLI at ~/code/33GOD/bloodbank/ (event publishing)
- Holyfields schemas at ~/code/33GOD/holyfields/schemas/ (event contracts)
- Plane skill at ~/.claude/skills/managing-tickets-and-tasks-in-plane/

## Classification Decisions

**Workflow Name:** ticket-lifecycle
**Target Path:** _bmad/custom/src/workflows/ticket-lifecycle/

**4 Key Decisions:**
1. **Document Output:** false (orchestrates agent handoffs + Plane state transitions, no persistent doc)
2. **Module Affiliation:** Standalone (universal across all projects, not module-specific)
3. **Session Type:** Single-session (Plane is the state store, each invocation handles one ticket)
4. **Lifecycle Support:** Tri-modal (create + edit + validate, will evolve as agent capabilities grow)

**Structure Implications:**
- Needs `steps-c/`, `steps-e/`, `steps-v/` directories
- No continuation logic (step-01b-continue.md not needed)
- No output document template needed
- Steps orchestrate external systems (Plane API, Bloodbank events, BMAD agent spawning)
- Workflow is reentrant: if interrupted, re-read Plane state and resume from current ticket status

## Requirements

**Flow Structure:**
- Pattern: Branching + looping
- Phases: Triage, Refining (conditional), Implementation, Review, QA Verification, Completion
- Estimated steps: 6-8
- Branch at triage (AC sufficient vs insufficient)
- Loop at QA (failed AC items route back to implementation, max 3 retries)
- Blocked state reachable from in-progress (AC ambiguity) and QA (max retries exceeded)

**User Interaction:**
- Style: Fully autonomous (zero human intervention)
- Decision points: None requiring human input. All decisions are rubric-driven or event-driven.
- Checkpoint frequency: No pauses. Bloodbank events serve as observable checkpoints for external consumers.

**Inputs Required:**
- Required: Ticket ID or Plane board context (ticket_provider.workspace + ticket_provider.board_id from `.project.json`)
- Required: Plane API access (via existing skill `managing-tickets-and-tasks-in-plane`)
- Required: Bloodbank CLI access for event publishing (`~/code/33GOD/bloodbank/`)
- Required: Holyfields event schemas (`~/code/33GOD/holyfields/schemas/`)
- Optional: Trigger mode context (human request, agent delegation, or Bloodbank event)
- Precondition: `.project.json` must exist in project root and contain a `ticket_provider` block with a non-empty `board_id` AND reference a workspace registered in `~/.claude/plane-workspaces.json`. If missing or malformed, workflow exits with a clear error (no silent failure).

**Output Specifications:**
- Type: Actions (not a document)
- Plane ticket state mutations (status transitions through the state machine)
- Bloodbank events broadcast at key transitions with `project_id` from Plane context. Events are broadcast, not addressed to specific agents. Consumers self-select.
- Code changes + tests (produced by coding agent, committed to repo)
- QA verification results: per-AC-item pass/fail verdicts
- Audit trail: structured Plane comments at each state transition (format TBD during step design)
- Frequency: Single ticket per invocation

**Triage AC-Sufficiency Rubric:**
The triage step evaluates AC using these criteria:
1. AC field is non-empty
2. Each AC item is a testable assertion (not vague like "works well")
3. AC items are enumerated (not a prose paragraph)
4. At least one AC item exists per functional requirement referenced in the ticket
If any criterion fails, route to Plane Captain for refinement.

**QA Verification Protocol:**
- Granularity: Line-item (per AC item pass/fail)
- On failure: defect payload includes the failed AC item text, observed behavior, and expected behavior
- Partial passes are tracked. On re-entry after fix, only failed items are re-verified.
- Max retries: 3 per ticket. After 3 failures, ticket moves to `blocked` with full failure history.

**Review Gate Requirements:**
- All unit tests pass (coding agent's test suite)
- Test coverage maps to AC items (QA agent validates coverage, not just green results)
- No regressions in existing test suite

**Staleness Detection:**
- Each state has a configurable max duration
- On expiry: `ticket.stale` Bloodbank event with `project_id`, `ticket_id`, `stuck_state`, `duration`
- Workflow does not retry or escalate. Consumers decide.

**Concurrency Model:** (design-time concern)
- To be resolved during step design. Key question: can multiple ticket-lifecycle instances run in parallel on the same repo?

**Audit Trail Format:** (design-time concern)
- Comment structure in Plane TBD. Should support programmatic parsing by downstream consumers.

**Success Criteria:**
- Ticket reaches `done` state with all AC line items verified (line-item granularity)
- Full audit trail in Plane (structured comments at each state transition)
- Bloodbank events fired at handoff points with project context (broadcast, not agent-addressed)
- No human intervention required end-to-end
- Graceful handling of QA failures (max 3 retries, then blocked with full history)
- Graceful handling of staleness (event emitted, no infinite hangs)
- Precondition failures (missing `.project.json` or `ticket_provider` block) produce clear errors, not silent failures

**Instruction Style:**
- Overall: Mixed
- Prescriptive for: state transitions, Plane API calls, AC-sufficiency rubric, event schemas, retry caps
- Intent-based for: agent delegation (coding agent gets goals + AC, not line-by-line instructions), QA verification approach
- Notes: The workflow orchestrates agents but does not micromanage their internal execution

## Tools Configuration

**Core BMAD Tools:**
- **Party Mode:** Excluded - Fully autonomous workflow, no creative brainstorming needed
- **Advanced Elicitation:** Excluded - No human interaction points to deepen
- **Brainstorming:** Excluded - No ideation phases in autonomous execution

**LLM Features:**
- **Web-Browsing:** Excluded - All data from Plane API + local repo
- **File I/O:** Included - Reads `.project.json` (ticket_provider block), coding agent writes code/tests, reads Holyfields schemas
- **Sub-Agents:** Included - Core mechanism: spawns Plane Captain, Coding Agent, QA Agent as needed
- **Sub-Processes:** Excluded - Single ticket per invocation, no parallelism needed

**Memory:**
- Type: Single-session
- Tracking: Plane ticket state is the persistence layer. No sidecar or session memory needed.
- Reentrant: If interrupted, re-read Plane state and resume from current ticket status.

**External Integrations:**
- Plane REST API via existing skill (`managing-tickets-and-tasks-in-plane`)
- Bloodbank CLI (`~/code/33GOD/bloodbank/`) for event publishing
- Holyfields event schemas (`~/code/33GOD/holyfields/schemas/`) for event contracts

**Installation Requirements:**
- None. All integrations already installed and available.

**Workflow Structure Preview:**

Phase 1: Context Resolution
- Resolve project context from `.project.json` (ticket_provider block) + `~/.claude/plane-workspaces.json`
- Validate preconditions (workspace exists, API accessible)
- Exit with clear error if preconditions fail

Phase 2: Ticket Acquisition & Triage
- Select ticket (by ID or scoring algorithm from Plane skill)
- Evaluate AC against sufficiency rubric
- Branch: sufficient -> Phase 4, insufficient -> Phase 3

Phase 3: AC Refinement (conditional)
- Spawn Plane Captain agent to define/improve AC
- Plane Captain reads ticket context, writes structured AC back to Plane
- Transition ticket to `ready` state

Phase 4: Implementation
- Spawn Coding Agent with AC items as goals
- Agent implements code + writes tests covering each AC item
- On AC ambiguity -> `blocked` + staleness event
- On completion -> transition to `review`

Phase 5: Review Gate
- Validate all tests pass, coverage maps to AC items
- Transition to `qa`

Phase 6: QA Verification
- Spawn QA Agent for line-item AC verification
- Per-item pass/fail verdicts
- All pass -> `done` + broadcast Bloodbank event
- Any fail (retries < 3) -> back to Phase 4 with defect details
- Any fail (retries >= 3) -> `blocked` + staleness event

Phase 7: Completion
- Broadcast `ticket.state_changed` event with `project_id`
- Post structured audit comment to Plane

## Workflow Design

### Create Mode (steps-c/) - 7 Steps

| Step | File | Type | Goal | Menu |
|------|------|------|------|------|
| 01 | step-01-init.md | Init (non-continuable) | Resolve project context, validate preconditions, acquire ticket | Auto-proceed |
| 02 | step-02-triage.md | Branch | Evaluate AC against sufficiency rubric, branch | Auto-branch |
| 03 | step-03-refine.md | Middle (simple) | Spawn Plane Captain to define/improve AC | Auto-proceed |
| 04 | step-04-implement.md | Middle (simple) | Spawn Coding Agent with AC goals | Auto-proceed |
| 05 | step-05-review.md | Validation sequence | Validate tests pass, coverage maps to AC | Auto-proceed |
| 06 | step-06-qa.md | Branch + loop | Spawn QA Agent for line-item verification | Auto-branch |
| 07 | step-07-complete.md | Final | Broadcast event, post audit comment, mark done | None |

### Edit Mode (steps-e/) - 2 Steps

| Step | File | Goal |
|------|------|------|
| 01 | step-01-assess.md | Load workflow config, check for issues, present modification options |
| 02 | step-02-apply.md | Apply edits (rubric thresholds, retry caps, staleness durations, state machine) |

### Validate Mode (steps-v/) - 1 Step

| Step | File | Goal |
|------|------|------|
| 01 | step-01-validate.md | Validate: .project.json ticket_provider block exists, Bloodbank CLI accessible, schemas present, skill installed |

### Data Flow

```
step-01-init
  reads: .project.json (ticket_provider block), ~/.claude/plane-workspaces.json
  produces: project context (workspace_id, project_id, ticket_id, ticket data)
  -> step-02

step-02-triage
  reads: ticket AC from Plane API
  evaluates: AC sufficiency rubric (4 criteria)
  branches: sufficient -> step-04 | insufficient -> step-03

step-03-refine
  spawns: Plane Captain sub-agent
  input: ticket context + AC gaps
  produces: updated AC in Plane
  -> step-04

step-04-implement
  spawns: Coding Agent sub-agent
  input: AC items as goals
  produces: code + tests committed to repo
  on AC ambiguity: -> step-07 (blocked)
  -> step-05

step-05-review
  validates: test suite passes, coverage maps to AC
  on failure: -> step-04 (retry)
  -> step-06

step-06-qa
  spawns: QA Agent sub-agent
  input: AC items + code changes
  produces: per-item pass/fail verdicts
  all pass: -> step-07 (done)
  fail + retries < 3: -> step-04 (with defect details)
  fail + retries >= 3: -> step-07 (blocked)

step-07-complete
  broadcasts: ticket.state_changed Bloodbank event
  posts: structured audit comment to Plane
  end
```

### File Structure

```
ticket-lifecycle/
├── workflow.md                    # Entry point with mode routing
├── workflow.yaml                  # Config (staleness durations, retry caps, rubric)
├── data/
│   ├── ac-sufficiency-rubric.md   # 4-criteria AC evaluation rubric
│   ├── audit-comment-template.md  # Structured comment format for Plane
│   └── event-schemas.md           # Bloodbank event payload references
├── steps-c/
│   ├── step-01-init.md
│   ├── step-02-triage.md
│   ├── step-03-refine.md
│   ├── step-04-implement.md
│   ├── step-05-review.md
│   ├── step-06-qa.md
│   └── step-07-complete.md
├── steps-e/
│   ├── step-01-assess.md
│   └── step-02-apply.md
└── steps-v/
    └── step-01-validate.md
```

### Interaction Pattern

No A/P/C menus. Fully autonomous. Every step auto-proceeds or auto-branches based on rubric/state evaluation.

### Role and Persona

Workflow orchestrator. Reads state, evaluates rubrics, spawns agents, transitions tickets. Pure execution engine.

### Subprocess Optimization

- Pattern 1 (Grep/Regex) at step-01-init: search for .project.json in project tree
- Pattern 4 (Parallel) deferred to v2: QA could parallelize AC item checks

### Error Handling

- step-01-init: Precondition failure -> clear error, exit
- step-02-triage: Rubric is deterministic (4 binary criteria)
- step-04-implement: AC ambiguity -> blocked state
- step-06-qa: Max 3 retries, then blocked
- All steps: Staleness timer, ticket.stale event on timeout
