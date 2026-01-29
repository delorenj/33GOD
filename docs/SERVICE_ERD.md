# Table of Contents

- PRD.md
- UX_Design_Doc.md

## File: PRD.md

- Extension: .md
- Language: markdown
- Size: 9406 bytes
- Created: 2025-11-06 18:14:18
- Modified: 2025-11-06 18:14:18

### Code

---

## modified: 2025-11-06T18:14:18-05:00

# Holocene: The Master Plan

### 🚀 30-Second Elevator Pitch

**Holocene** is a mission control dashboard for the multi-project portfolio of the 33GOD Agentic Development Pipeline. It shows what moved today, who contributed, and which decisions mattered—so founders and PMs can lead without drowning in detail. Calm, decisive, and human-aware.

---

### 🧭 Problem & Mission

**Problem**: Leaders managing multiple initiatives lack fast, high-signal visibility into daily progress, decisions, and agent contributions. The 33GADP produces a high volume of data, every command, log, event, agent action, subagent action, everything is tracked and retained. This results in a noisy environment where getting a finger on the pulse of the pipeline is not a trivial task.

**Mission**: To make sense of this data and surface only the bits that matter, while maintaining the ability to drill down to different layers of data upon request.

---

### 🎯 Target Audience

- **Founder and Sole Engineer: Me**
  - tracking portfolio health & velocity
  - reviewing decisions, ownership, and plan drift.
  - drilling into rationale and context behind change.

---

### 🧩 Core Features

- **Portfolio Overview** — Top 3 moving projects, momentum deltas, brief summaries.
- **Decision Radar** — Ranked feed of impactful decisions; autonomy alerts.
- **Agent Constellation** — Collaboration graph, pair highlights, effectiveness notes.
- **Plans & Commitments** — Drift detection between commitments and execution.
- **Risks & Blockers** — Portfolio-wide issues surfaced automatically.
- **Project Drill-down** — Tabs for Activity, Agents, Decisions, and Infra.
- **Briefing Mode** — Auto-generated AM/PM briefs with key diffs.
- **Saved Views** — Shared, persistent “mission layouts” by focus (e.g. risk, owner).

---

### 🛠 High-Level Tech Stack

- **Frontend**: React + Vite + TypeScript + shadcn/ui + Tailwind → Fast UI with rich interactivity.
- **Backend**: Postgres + Redis → Reliable, self-hosted state & snapshot store.
- **Auth**: GitHub OAuth → Secure, flexible login for teams.
- **Docs/Reports**: Markdown & PDF export → Lightweight daily summaries.

Each tech choice reinforces performance, clarity, and self-hosted sovereignty.

---

### 🗺 Conceptual Data Model (ERD in words)

- **Repo**
  - Cloned locally by [iMi](/home/delorenj/d/Projects/33GOD/iMi/PRD.md)
  - Has many → **Decisions**, **Checkpoints**, **YiContributors**, **EventsProduced**, **EventsConsumed**, **Sessions**, **Worktrees**, **Tasks**, **Briefs** (by task, by feature, by day, by week), **Recommendations**, **Skills**,
  - Has one → **LeadArchitect**, **ProjectManager**, **QALead**, **ProductRoadmap**, **PRD**, **MVPAC** (set of acceptance criteria to meet the minimal requirements for a viable product)

- **Project**
  - Created and managed by [Flume](/home/delorenj/d/Projects/33GOD/Flume/PRD.md)
  - Maybe implemented as an extension or plugin to Plane?
  - Has many → **Repos**, **Decisions**, **Tasks**, **Sessions**, **Briefs** (rollups from child repo briefs), **Recommendations**, **Skills**
  - Has one → **PRD**, **ProjectDirector** (delegates to child Project Managers), **EngineeringDirector**, **QADirector**, **ProjectRoadmap**, **MVPAC** (set of acceptance criteria to meet the minimal requirements for a viable product)

- **Employee**
  - Instance of **[Yi Node](/home/delorenj/d/Projects/33GOD/Yi/PRD.md)**, an Anthropomorphized Agent Orchestrator
  - Linked to → **Projects**/**Repos** via contributions (**Commits**, **PRs**, **Sessions**, **Tasks**)
  - Has many → **AssignedTasks**, **AcceptedTasks**, **RequestsForReview**, **DomainsOfExperience** (unique, semantic memories formed during **Sessions**, think memory_bank), **DomainsOfExpertise** (skills implanted via context - knowledge base, system prompt, claude skills, mcp server), **PeerReviews** (anthropomorphized system of periodic reviews, for personal growth and self-reflection), **MemoryShards** (tracks memory type/framework, pointer to data locations - could be qdrant collections, agentfiles, neo4j volumes, etc), **Decisions**, **DailyStandup** (every 24 hours, active agents must submit an async standup stating what they did yesterday, what they plan to do today, and any blockers they have - they can also request human-in-the-loop guidance), **ProducedEvents**, **ConsumedEvents**
  - Has one → **ActiveTask**, **AgentFile**
  - Fields:
    - **Salary** (anthropomorphized measurement of “importance” to the well-being and growth of the company/pipeline), simplified leveling system for implicit rank.
    - **AgentType**: Letta, Agno, Claude, etc
    - **Personality**
    - **Background**,
    - **ActiveMemoryShard**: Agents could have accumulated many blocks of contiguous memories, but can only have one active at a time. Ideally agent has only one, but realistically i foresee this being needed since ideally we have one clean git trunk history, but we all know that doesn’t happen. Think of this as checkpoint system, but for memory instead of semantic context or code.

- **Task**
  - Instance created/managed by [Flume]
  - Created by → **Employee** or Human-in-the-loop
  - Has many → **Contributors** (employees that have actively work on the task at least once), **Sessions** (each Jelmore session invoked manually by a human (me) or agentically by an employee), **Checkpoints** (git commit SHAs), **ProducedEvents** (`flume.task.completed`), **ConsumedEvents** (`flume.task.accept`)
  - Has one → **Lifecycle** (custom state machine, differs per task type), **Assignee** (no one but assignee can accept task), **ActiveEmployee** (if lifecycle state is `ready`, and **Assignee** is `null`, an employee can `accept` the task, thus setting the **ActiveEmployee** and blocking anyone else from accepting. Note)
  - _Fields_:
    - **RawTask**: Tasks are usually created via markdown file. This is the raw unprocessed task.
    - **Title**: Determined via processing by the repo’s project manager. Single sentence, high-level description
    - **Description**: Determined via processing by the repo’s project manager. Long-form description of the task and it’s overall place in the project.
    - **Requirements**: Determined via processing by the repo’s project manager. Set of comprehensive requirements that formally define the task.
    - **Plan**: Determined via processing by the repo’s lead architect. A comprehensive implementation plan that, if sufficiently complex, can be recursively split into sub-**Tasks**, with each subtask getting this parent task as a dependency.
    - **AcceptanceCriteria**: Processed last, by the repo’s QALead. A set of concrete, actionable steps to follow with expected result that if true, signals all requirements have been satisfied
    - **State**: One of the states defined in the **Lifecycle** state machine assigned to this task. There are core states that _MUST_ exist to be a valid **Lifecycle**:
      - `open` → initial state.
      - `ready` → can be accepted by employee, or closed by creator or a superior
      - `done` → Considered complete, but with no guarantees. Not tested.
      - `closed` → No longer considered a ‘todo’ item. Not complete. Like it never happened.
    - **IdealCandidate**: Blurb describing what traits, skills, tools, context, required for high chance of task successful completion

- **Session**
  - A long-running agentic coding process kicked off by a prompt driven by [Jelmore](/home/delorenj/d/Projects/33GOD/Jelmore/PRD.md)
  - Jelmore `Sessions` are wrapped in Zellij tmux instances which can be joined and hijacked anytime by a human.
  - Sessions can also be joined by other agents to observe output and take notes for instance.
  - Every input (prompt) and output (response) produces a [Bloodbank](/home/delorenj/d/Projects/33GOD/BloodBank/README.md) `Event` that can be subscribed to (i.e. a logger)
  - Jelmore acts to unify into a common interface the invocation and configuration of Codex, ClaudeCode, Gemini, Auggie, CoPilot, and OpenCode
  - Jelmore handles the model selection, provider selection, tracks token count, handles timeouts and errors, ensures parity among skills and MCP servers
  - Jelmore DOES NOT handle the higher-level agent management.

> Note: `Jelmore` can be invoked by CLI, API, or MCP tool and in this 33GOD pipeline it is typically invoked by the higher-level `Yi Nodes`.
> Each `Yi` node contains an agent instance that represents a single employee. The parent-child relationship between `Yi` nodes is defined by
> the `Flume Tree` which is modeled after a typical corporate hierarchy in terms of roles and responsibilties, role diversity and distribution, IC-Manager ratio (with the exception of swarms).

- **Worktree**
  - Created by [iMi](/home/delorenj/d/Projects/33GOD/iMi/PRD.md), it's an extension of a git worktree
  - Serves as a mechanism to claim a branch by an agent as well as act as a registry to link projects, tasks, branches, etc to a location on the localhost.

- **Decision**
  - One of several artifact types that can be created during a `Session`

- **Brief**
  - One of several artifact types. It is a rollup of work or summary within some discrete window of time, over one or more files, sessions, tasks, components, or projects

- **Checkpoint**
  - A serialized snapshot of a slice of time during a `Session`
  - Deserialization should result in lossless return to state for entities:
    - Agents the partook in the session should have their memories truncated back to what it was at that slice in time.
    - Source code that was modified during the session should be restored.
    - Event fired to note the checkpoint's creation
    - Event fired when checkpoint is restored.

- **Recommendation**
  - An actionable statement made by an agent that can either be invoked or not
  - Invocation can be decided by a `Decision` artifact, by a human-in-the-loop, or by another agent.
  - A Recommendation can be bound by constraint:
    1. i.e. recommend to deploy this to stage before prod.
    2. it is instead deployed directly to prod
    3. Recommendation is no longer applicable and can be deleted
  - Or by time window:
    1. i.e. recommend to deploy before friday
    2. it is deployed immediately
    3. Recommendation is no longer applicable and can be deleted.

---

### 🎨 UI Design Principles (Krug-inspired)

- **Don’t make me think**: Momentum scores, agent ranks, and decision impact are immediately scannable.
- **Design for scanning**: Cards, grids, and brief headlines use visual hierarchy and typography to guide attention.
