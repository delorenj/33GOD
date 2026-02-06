# 33GOD Domain Index

> **Progressive Discovery Guide** — Use this index to determine which domain documentation to load based on the user's prompt. Only load the domains relevant to the task.

---

## Quick Reference

| Domain | Components | Load When... |
|--------|------------|--------------|
| [Infrastructure](#infrastructure) | Bloodbank, Holyfields, Candystore, Candybar | Events, messaging, schemas, contracts |
| [Agent Orchestration](#agent-orchestration) | Flume, Yi, AgentForge, Holocene | Agents, teams, roles, protocols |
| [Workspace Management](#workspace-management) | iMi, Jelmore, Zellij-Driver, Perth | Git, worktrees, sessions, terminals |
| [Meeting & Collaboration](#meeting--collaboration) | TheBoard, TheBoard Room | Brainstorming, meetings, convergence |
| [Dashboards & Voice](#dashboards--voice) | Holocene, HeyMa, Candybar | Dashboard, voice, UI, visualization |
| [Development Tools](#development-tools) | Jelmore, Degenerate, BMAD | Docs sync, methodology, coding sessions |

---

## Domain Details

### Infrastructure

**Files:**
- `infrastructure.md` (comprehensive)
- `event-infrastructure.md` (quick reference)

**Components:**
- **Bloodbank** — Central event bus (RabbitMQ)
- **Holyfields** — Schema registry & type generation
- **Candystore** — Event persistence layer
- **Candybar** — Service registry visualization

**Keywords:** `event`, `message`, `publish`, `subscribe`, `schema`, `contract`, `RabbitMQ`, `topic`, `exchange`, `queue`, `dead letter`, `DLQ`, `correlation`, `tracing`, `Pydantic`, `Zod`, `JSON Schema`, `type generation`, `service registry`, `event bus`

**Load this domain when the prompt mentions:**
- Adding or modifying event types
- Debugging event routing or dead-letter queues
- Working on observability, tracing, or event replay
- Changing schema definitions
- Service-to-service communication
- Event validation or contracts

---

### Agent Orchestration

**Files:**
- `agent-orchestration.md` (comprehensive)

**Components:**
- **Flume** — Agentic Corporate Protocol (TypeScript)
- **Yi** — Opinionated Agent Adapter
- **AgentForge** — Meta-agent team builder
- **Holocene** — Hive mind & agent repository

**Keywords:** `agent`, `orchestration`, `team`, `role`, `manager`, `contributor`, `employee`, `protocol`, `Flume`, `Yi`, `AgentForge`, `Holocene`, `hive mind`, `collective intelligence`, `task assignment`, `agent lifecycle`, `onboarding`, `capability`, `Letta`, `Agno`, `Smolagents`

**Load this domain when the prompt mentions:**
- Creating or managing AI agents
- Team assembly or coordination
- Agent roles and responsibilities
- Protocol definitions
- Agent wrapping or adapters
- Collective decision-making

---

### Workspace Management

**Files:**
- `worktree-terminal.md` (comprehensive)
- `workspace-management.md` (quick reference)

**Components:**
- **iMi** — Git worktree manager (Rust CLI)
- **Jelmore** — Claude Code session manager
- **Zellij-Driver** — Terminal context manager
- **Perth** — Zellij distribution

**Keywords:** `worktree`, `git`, `branch`, `trunk-main`, `feat-*`, `fix-*`, `terminal`, `Zellij`, `session`, `context`, `intent`, `milestone`, `claim`, `release`, `parallel development`, `multi-agent`, `zdrive`, `Perth`

**Load this domain when the prompt mentions:**
- Git worktree management
- Branch naming conventions
- Terminal sessions or multiplexing
- Agent execution context
- Parallel development workflows
- Session state or persistence

---

### Meeting & Collaboration

**Files:**
- `applications.md` (comprehensive)
- `meeting-collaboration.md` (quick reference)

**Components:**
- **TheBoard** — Multi-agent brainstorming system
- **TheBoard Room** — 3D visualization UI

**Keywords:** `meeting`, `brainstorm`, `convergence`, `discussion`, `TheBoard`, `round`, `agent collaboration`, `context compression`, `3D visualization`, `PlayCanvas`, `architecture review`, `feature discussion`, `incident analysis`

**Load this domain when the prompt mentions:**
- Multi-agent brainstorming
- Meeting orchestration
- Convergence detection
- Architecture discussions
- Collaborative decision-making
- Meeting visualization

---

### Dashboards & Voice

**Files:**
- `applications.md` (comprehensive)
- `dashboards-voice.md` (quick reference)

**Components:**
- **Holocene** — Mission control dashboard
- **HeyMa** — Voice interface system
- **Candybar** — Service topology dashboard

**Keywords:** `dashboard`, `voice`, `transcription`, `TTS`, `text-to-speech`, `Whisper`, `ElevenLabs`, `UI`, `visualization`, `portfolio`, `health`, `topology`, `Holocene`, `HeyMa`, `Candybar`

**Load this domain when the prompt mentions:**
- Dashboard features or UI
- Voice commands or transcription
- System visualization
- Service health monitoring
- Portfolio overview
- Real-time data display

---

### Development Tools

**Files:**
- `development-tools.md` (comprehensive)

**Components:**
- **Jelmore** — AI coding session manager
- **Degenerate** — Documentation drift detection
- **BMAD** — Methodology configuration

**Keywords:** `session`, `Claude Code`, `coding assistant`, `documentation`, `drift`, `sync`, `methodology`, `BMAD`, `orchestrator`, `DevLog`, `Degenerate`, `Jelmore`, `OpenCode`, `Codex`, `Gemini`

**Load this domain when the prompt mentions:**
- AI coding sessions
- Documentation synchronization
- Doc drift detection
- Development methodology
- Orchestrator configuration
- Session management APIs

---

## Decision Tree

```
User Prompt
    │
    ├─ mentions events/messaging/schemas?
    │   └─→ Load: Infrastructure
    │
    ├─ mentions agents/teams/orchestration?
    │   └─→ Load: Agent Orchestration
    │
    ├─ mentions git/worktrees/terminals/sessions?
    │   └─→ Load: Workspace Management
    │
    ├─ mentions meetings/brainstorming/convergence?
    │   └─→ Load: Meeting & Collaboration
    │
    ├─ mentions dashboard/voice/UI/visualization?
    │   └─→ Load: Dashboards & Voice
    │
    ├─ mentions docs/methodology/coding sessions?
    │   └─→ Load: Development Tools
    │
    └─ unclear or spans multiple domains?
        └─→ Load: This index + relevant domains
```

---

## File Paths

| Domain | Primary Doc | Quick Reference |
|--------|-------------|-----------------|
| Infrastructure | `docs/domains/infrastructure.md` | `docs/domains/event-infrastructure.md` |
| Agent Orchestration | `docs/domains/agent-orchestration.md` | — |
| Workspace Management | `docs/domains/worktree-terminal.md` | `docs/domains/workspace-management.md` |
| Meeting & Collaboration | `docs/domains/applications.md` | `docs/domains/meeting-collaboration.md` |
| Dashboards & Voice | `docs/domains/applications.md` | `docs/domains/dashboards-voice.md` |
| Development Tools | `docs/domains/development-tools.md` | — |

---

## Usage Pattern

1. **Always start here** — Read this index first
2. **Match keywords** — Scan the user's prompt for domain keywords
3. **Load relevant docs** — Only load the domain docs that match
4. **Use quick reference first** — For simple questions, the quick reference may suffice
5. **Load comprehensive docs** — For implementation work, load the full domain doc
6. **Cross-reference** — Many tasks span domains; load multiple as needed

---

## Component → Domain Mapping

| Component | Domain |
|-----------|--------|
| Bloodbank | Infrastructure |
| Holyfields | Infrastructure |
| Candystore | Infrastructure |
| Candybar | Infrastructure, Dashboards & Voice |
| Flume | Agent Orchestration |
| Yi | Agent Orchestration |
| AgentForge | Agent Orchestration |
| Holocene | Agent Orchestration, Dashboards & Voice |
| iMi | Workspace Management |
| Jelmore | Workspace Management, Development Tools |
| Zellij-Driver | Workspace Management |
| Perth | Workspace Management |
| TheBoard | Meeting & Collaboration |
| TheBoard Room | Meeting & Collaboration |
| HeyMa | Dashboards & Voice |
| Degenerate | Development Tools |
| BMAD | Development Tools |
