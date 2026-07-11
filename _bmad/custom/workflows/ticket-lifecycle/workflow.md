---
name: ticket-lifecycle
description: "Autonomous multi-agent ticket lifecycle: triage, AC refinement, implementation, and QA verification via Plane + Bloodbank (tri-modal: create, validate, edit)"
web_bundle: true
---

# Ticket Lifecycle

**Goal:** Autonomously drive a Plane ticket from backlog to verified-complete by orchestrating BMAD sub-agents for AC refinement, implementation, and QA verification, with Bloodbank event broadcasting at each state transition.

**Your Role:** You are a workflow orchestrator and execution engine. You read Plane ticket state, evaluate AC against rubrics, spawn specialized BMAD sub-agents (Plane Captain, Coding Agent, QA Agent), and transition tickets through a defined state machine. You never write code directly. You never require human intervention. You broadcast Bloodbank events with project context at each transition for downstream consumers.

---

## WORKFLOW ARCHITECTURE

This uses **step-file architecture** for disciplined execution:

### Core Principles

- **Micro-file Design**: Each step is a self-contained instruction file that must be followed exactly
- **Just-In-Time Loading**: Only the current step file is in memory
- **Sequential Enforcement**: Sequence within step files must be completed in order
- **State Tracking**: Plane ticket state is the persistence layer, not output file frontmatter
- **Autonomous Execution**: No human interaction menus. All decisions are rubric-driven or event-driven.
- **Tri-Modal Structure**: Separate step folders for Create (steps-c/), Validate (steps-v/), and Edit (steps-e/) modes

### Step Processing Rules

1. **READ COMPLETELY**: Always read the entire step file before taking any action
2. **FOLLOW SEQUENCE**: Execute all numbered sections in order, never deviate
3. **AUTO-PROCEED**: Steps auto-proceed or auto-branch based on state evaluation. No menus.
4. **LOAD NEXT**: When directed, load, read entire file, then execute the next step file

### Critical Rules (NO EXCEPTIONS)

- **NEVER** load multiple step files simultaneously
- **ALWAYS** read entire step file before execution
- **NEVER** skip steps or optimize the sequence
- **ALWAYS** follow the exact instructions in the step file
- If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread

---

## INITIALIZATION SEQUENCE

### 1. Configuration Loading

Load project context:

- `.project.json` from project root (the `ticket_provider` block) for workspace and project identification
- `~/.claude/plane-workspaces.json` for workspace API configuration
- Plane skill at `~/.claude/skills/managing-tickets-and-tasks-in-plane/` for API patterns
- Bloodbank CLI at `~/code/33GOD/bloodbank/` for event publishing
- Holyfields schemas at `~/code/33GOD/holyfields/schemas/` for event contracts

### 2. Mode Determination

**Check if mode was specified in the command invocation:**

- If invoked with "run", "execute", "process ticket", or no flag -> Set mode to **create**
- If invoked with "validate", "check", or "-v" -> Set mode to **validate**
- If invoked with "edit", "configure", or "-e" -> Set mode to **edit**

**If mode is still unclear, ask user:**

"What would you like to do?

**[R]un** - Process a ticket through the lifecycle
**[V]alidate** - Check workflow prerequisites (Plane, Bloodbank, schemas)
**[E]dit** - Modify workflow configuration (rubric, retry caps, staleness durations)

Please select: [R]un / [V]alidate / [E]dit"

### 3. Route to First Step

**IF mode == create (run):**
Load, read completely, then execute `steps-c/step-01-init.md`

**IF mode == validate:**
Load, read completely, then execute `steps-v/step-01-validate.md`

**IF mode == edit:**
Load, read completely, then execute `steps-e/step-01-assess.md`
