# 33GOD Development Architecture

> A developer's guide to the component architecture, dependencies, and integration patterns of the 33GOD Agentic Development Pipeline.

## System Overview

33GOD is an event-driven, agentic ecosystem built on the principle that **everything is an event**. All significant state changes—Git commits, meeting events, agent thoughts, transcript arrivals—flow through a central event bus as typed, validated messages. Components are decoupled, autonomous, and react to events rather than being called directly.

---

## Domain Architecture

The platform is organized into **6 domains**, each owning a cohesive set of responsibilities:

| Domain | Purpose | Primary Components |
|--------|---------|-------------------|
| **Event Infrastructure** | Central nervous system; event routing and contracts | Bloodbank, Holyfields, Candystore, Candybar |
| **Agent Orchestration** | Protocol layer; agent communication, wrapping, team assembly | Flume, Yi, AgentForge, Holocene |
| **Workspace Management** | Execution context; where agents perform work | iMi, Jelmore, Zellij-Driver, Perth |
| **Meeting & Collaboration** | Multi-agent brainstorming and convergence | TheBoard, TheBoardroom |
| **Dashboards & Voice** | Human-facing interfaces | Holocene, HeyMa, Candybar |
| **Development Tools** | Meta-tooling for development workflow | Jelmore, Degenerate, BMAD |

---

## Component Dependency Graph

```
                                 ┌─────────────────────────────────────────┐
                                 │         EXTERNAL SYSTEMS                │
                                 │   GitHub · Fireflies · Obsidian Vault   │
                                 └──────────────────┬──────────────────────┘
                                                    │ webhooks
                                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              EVENT INFRASTRUCTURE                                     │
│  ┌──────────────┐    validates    ┌──────────────┐    persists    ┌──────────────┐  │
│  │  Holyfields  │◄───────────────►│  Bloodbank   │───────────────►│  Candystore  │  │
│  │   (Schemas)  │                 │  (Event Bus) │                │  (Storage)   │  │
│  └──────────────┘                 └──────┬───────┘                └──────┬───────┘  │
│         │                                │                               │          │
│         │ generates types                │ pub/sub                       │ query    │
│         ▼                                ▼                               ▼          │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                          ALL DOMAIN COMPONENTS                               │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              │                           │                           │
              ▼                           ▼                           ▼
┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐
│   AGENT ORCHESTRATION   │  │  WORKSPACE MANAGEMENT   │  │     APPLICATIONS        │
│                         │  │                         │  │                         │
│  ┌───────┐   ┌───────┐  │  │  ┌───────┐   ┌───────┐  │  │  ┌───────┐   ┌───────┐  │
│  │ Flume │──►│  Yi   │  │  │  │  iMi  │   │Jelmore│  │  │  │TheBoard│  │Candybar│ │
│  │(Proto)│   │(Adapt)│  │  │  │(Workt)│   │(Sessn)│  │  │  │(Brain) │  │(Viz)  │  │
│  └───────┘   └───┬───┘  │  │  └───────┘   └───┬───┘  │  │  └───────┘   └───────┘  │
│                  │      │  │                  │      │  │       │                  │
│  ┌───────────────┴───┐  │  │  ┌───────┐   ┌───┴───┐  │  │  ┌────┴────┐  ┌───────┐ │
│  │    AgentForge     │  │  │  │ Perth │◄──│ZDrive │  │  │  │BoardRoom│  │TalkyT │ │
│  │  (Team Builder)   │  │  │  │ (Term)│   │(Contx)│  │  │  │  (3D)   │  │(Voice)│ │
│  └─────────┬─────────┘  │  │  └───────┘   └───────┘  │  │  └─────────┘  └───────┘ │
│            │            │  │                         │  │                         │
│  ┌─────────▼─────────┐  │  └─────────────────────────┘  └─────────────────────────┘
│  │     Holocene      │  │
│  │ (Mission Control) │  │
│  └───────────────────┘  │
└─────────────────────────┘
```

---

## Component Details

### Event Infrastructure

#### Bloodbank — Central Event Bus
- **Language**: Python 3.11+
- **Frameworks**: FastAPI, FastStream, aio-pika
- **Message Broker**: RabbitMQ (topic exchange)
- **Depends On**: RabbitMQ, Holyfields (schemas)
- **Consumed By**: All event-aware components

**Key Contracts**:
- All events wrapped in `EventEnvelope` (event_id, event_type, timestamp, version, source, correlation_ids, payload)
- Topic exchange pattern: `bloodbank.events.v1`
- Routing key format: `{domain}.{entity}.{action}` (e.g., `theboard.meeting.converged`)
- Queue naming: `services.{domain}.{service_name}`

#### Holyfields — Schema Registry
- **Language**: TypeScript
- **Schema Format**: JSON Schema Draft 2020-12
- **Generates**: Pydantic models (Python), Zod validators (TypeScript), SQLAlchemy models
- **Depends On**: None (source of truth)
- **Consumed By**: Bloodbank (validation), all typed consumers

**Directory Structure**:
```
holyfields/schemas/
├── core/event-envelope.v1.schema.json
├── fireflies/transcript.*.schema.json
├── theboard/meeting.*.schema.json
├── agent/feedback.*.schema.json
└── artifact/created.*.schema.json
```

#### Candystore — Event Persistence
- **Language**: Python 3.12+
- **Frameworks**: FastAPI, SQLAlchemy 2.0
- **Database**: PostgreSQL/SQLite
- **Depends On**: Bloodbank (subscribes to ALL events via `#` wildcard)
- **Provides**: REST API for event queries, correlation chain lookups

#### Candybar — Service Registry Dashboard
- **Language**: TypeScript
- **Frameworks**: Next.js 14, React 19, Tauri
- **UI**: shadcn/ui, Tailwind CSS, D3.js/react-force-graph
- **Depends On**: Candystore (API), Bloodbank (WebSocket stream), `registry.yaml`
- **State Management**: Zustand (client), TanStack Query (server)

---

### Agent Orchestration

#### Flume — Agentic Corporate Protocol
- **Language**: TypeScript
- **Type**: Protocol definitions only (no business logic)
- **Key Abstractions**:
  - `Manager` — coordinates and delegates
  - `Contributor` — executes assigned tasks
  - `TaskPayload` — work assignment structure
  - `WorkResult` — completion deliverable
- **Depends On**: None (pure interfaces)
- **Consumed By**: Yi (implements)

**Package Structure**:
```
flume/packages/
├── core/           # Protocol definitions
├── manager/        # Manager interface
├── contributor/    # Contributor interface
└── events/         # Bloodbank event types
```

#### Yi — Opinionated Agent Adapter
- **Language**: TypeScript
- **Purpose**: Wraps AI SDKs (Letta, Agno, Smolagents, Claude) with Flume protocol compliance
- **Key Classes**:
  - `YiManager` — abstract Flume Manager implementation
  - `YiContributor` — abstract Flume Contributor implementation
  - `YiMemoryStrategy` — cross-agent context synchronization
  - `OnboardingSpecialist` — injects TeamContext into new agents
- **Depends On**: Flume (protocols), Redis (memory sync), Bloodbank (events)
- **Memory Coordination**: Redis-backed memory shards

#### AgentForge — Meta-Agent Team Builder
- **Language**: Python
- **Framework**: Agno
- **Vector Store**: LanceDB
- **Meta-Team** (5 specialized agents):
  1. **Engineering Manager** — coordinates assembly
  2. **Systems Analyst** — analyzes requirements
  3. **Talent Scout** — searches agent definitions
  4. **Agent Developer** — creates missing agents
  5. **Integration Architect** — designs communication topology
- **Depends On**: Holocene (agent definitions), Yi (wrapping), Flume (protocols)
- **Output Formats**: `.claude/agents/*.md`, AmazonQ JSON, OpenCode YAML

#### Holocene — Mission Control Dashboard
- **Language**: TypeScript
- **Frameworks**: React 18, Vite, Tailwind CSS
- **State**: Zustand + TanStack Query
- **Purpose**: Agent repository, team viewer, task monitor, health dashboard
- **Agent Storage**: `.claude/agents/` Markdown format with YAML frontmatter
- **Depends On**: Bloodbank (events), Redis (state), agent definitions

---

### Workspace Management

#### iMi — Git Worktree Manager
- **Language**: Rust
- **Libraries**: Tokio, git2, SQLite
- **Purpose**: Manages parallel development via Git worktrees with agent claiming semantics
- **Conventions**:
  - `trunk-main` — main branch worktree (never delete)
  - `feat-*` — feature worktrees (claim → work → merge)
- **Fields**: agent_id (exclusive access), metadata (task source links)
- **Depends On**: Git, SQLite

#### Jelmore — AI Session Manager
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Purpose**: Unified interface for managing coding sessions across providers (Claude, Codex, Gemini)
- **Features**: Session lifecycle (create/pause/resume/terminate), REST API, Docker isolation
- **Depends On**: iMi (worktrees), Zellij-Driver (context), provider APIs

#### Zellij-Driver — Terminal Context Manager
- **Language**: Rust
- **Libraries**: Tokio, Redis
- **Purpose**: Tracks intent and milestones across terminal sessions
- **Persistence**: Redis-backed context state
- **Depends On**: Redis, Perth (terminal)

#### Perth — Customized Zellij Distribution
- **Language**: Rust (Zellij fork)
- **Purpose**: Terminal multiplexer with visual notifications and animation engine
- **Database**: PostgreSQL (session persistence)
- **Controlled By**: Zellij-Driver (programmatic control)

---

### Meeting & Collaboration

#### TheBoard — Multi-Agent Brainstorming
- **Language**: Python 3.12+
- **Frameworks**: FastAPI, Agno
- **Databases**: PostgreSQL, Redis, Qdrant (vector)
- **Features**:
  - Multi-round discussions with convergence detection
  - 3-tier context compression (40-60% token reduction)
  - Cost tracking per session
- **Depends On**: Bloodbank (events), agent pool
- **Events Emitted**: `theboard.meeting.*` (created, started, round_completed, converged, completed)

**Compression Tiers**:
1. Semantic clustering of similar contributions
2. LLM-based summarization of clusters
3. Outlier removal for noise reduction

#### TheBoardroom — 3D Visualization
- **Language**: TypeScript
- **Engine**: PlayCanvas (WebGL)
- **Build**: Vite, Bun
- **Purpose**: Real-time 3D visualization of TheBoard meetings
- **Depends On**: Bloodbank (WebSocket subscription to `theboard.meeting.*`)

---

### Dashboards & Voice

#### HeyMa — Voice Interface System
- **Components**:
  - **WhisperLiveKit** — real-time STT (faster-whisper)
  - **Tonny Agent** — Letta-powered conversational AI
  - **TonnyTray** — Tauri desktop app (Rust + React)
  - **Chrome Extension** — browser voice capture
  - **ElevenLabs** — TTS synthesis
- **Event Flow**:
  ```
  Voice → WhisperLiveKit → transcription.voice.completed
                                      ↓
                              Tonny Agent (Letta)
                                      ↓
                              ElevenLabs TTS
                                      ↓
                        tts.response.completed → Audio
  ```
- **Latency Target**: <2000ms end-to-end
- **Depends On**: Bloodbank, Letta server, ElevenLabs API

---

### Development Tools

#### Degenerate — Documentation Drift Detection
- **Language**: Rust
- **Libraries**: Tokio, git2
- **Purpose**: Detects when code changes have drifted from documentation
- **Sync Modes**: One-way, Two-way, Mirror
- **Sync Markers**: `<!-- degenerate:sync-marker -->` in domain docs

#### BMAD — Methodology Framework
- **Type**: Configuration + agent overrides
- **Phases**: Business → Management → Architecture → Development
- **Config**: `bmad/config.yaml` (project settings, sprint config)
- **DevLog**: `bmad/devlog/tasks/` (timestamped task files)

---

## Cross-Domain Integration Points

### Shared Resources

| Resource | Technology | Purpose |
|----------|------------|---------|
| **Event Bus** | RabbitMQ | Async communication between all components |
| **Database** | PostgreSQL | Shared global state |
| **Cache** | Redis | Session state, memory shards, context |
| **Schema Registry** | Holyfields | Type-safe event contracts |
| **Service Registry** | `services/registry.yaml` | Service discovery, topology |

### Event Flow Patterns

```
User Input ──► HeyMa ──► Bloodbank ──► Services ──► AgentForge
                                   │
                                   ▼
                            Candystore ──► Candybar
                                   │
                                   ▼
                            Holyfields (validation)
                                   │
                                   ▼
                            TheBoard ──► TheBoardroom
                                   │
                                   ▼
                    iMi (worktrees) + Perth (IDE) + ZDrive (context)
                                   │
                                   ▼
                            Holocene (mission control)
```

### Key Event Types

| Event | Producer | Consumers |
|-------|----------|-----------|
| `fireflies.transcript.ready` | Node-RED webhook | Fireflies processor |
| `theboard.meeting.*` | TheBoard | TheBoardroom, Candybar |
| `agent.feedback.requested` | Yi adapters | Agent pool |
| `task.assigned` / `task.completed` | Flume | Yi, AgentForge |
| `transcription.voice.completed` | WhisperLiveKit | Tonny Agent |
| `tts.response.completed` | Tonny Agent | HeyMa clients |
| `worktree.created` | iMi | Jelmore, agents |

---

## Technology Stack Summary

### Languages
| Language | Components |
|----------|------------|
| **Rust** | iMi, Perth, Zellij-Driver, Degenerate |
| **Python** | Bloodbank, TheBoard, Candystore, AgentForge, Jelmore, HeyMa (backend) |
| **TypeScript** | Flume, Yi, Holocene, Candybar, TheBoardroom, HeyMa (frontend), Holyfields |

### Databases
| Database | Purpose | Used By |
|----------|---------|---------|
| **PostgreSQL** | Primary persistence | TheBoard, Candystore, Perth |
| **SQLite** | Lightweight local storage | iMi, Candystore (alt) |
| **Redis** | Caching, session state, memory sync | Yi, Zellij-Driver, TheBoard |
| **Qdrant** | Vector embeddings | TheBoard, AgentForge |
| **LanceDB** | Vector search for agent matching | AgentForge |

### Frameworks
| Category | Technologies |
|----------|--------------|
| **Backend** | FastAPI, FastStream, aio-pika, SQLAlchemy, Typer |
| **Frontend** | React, Next.js, Vite, PlayCanvas, Recharts |
| **State** | Zustand, TanStack Query, Pydantic |
| **Build** | Vite, Cargo, uv, Bun |
| **Desktop** | Tauri |

---

## Agent Lifecycle

### 1. Definition (Holocene)
Agent defined in `.claude/agents/*.md` with YAML frontmatter specifying capabilities, domains, and constraints.

### 2. Assembly (AgentForge)
Meta-team analyzes goal → Talent Scout searches definitions → Integration Architect designs topology → Team assembled with Flume hierarchy.

### 3. Initialization (Yi)
Yi wraps each agent → OnboardingSpecialist injects TeamContext → Agents transition: `INITIALIZING` → `ONBOARDING` → `WORKING`.

### 4. Execution (Flume)
Manager receives `TaskPayload` → Delegates to Contributors → Contributors return `WorkResult` → Events emitted throughout.

### 5. Coordination
- Heartbeats every 30 seconds
- Memory synchronized via `YiMemoryStrategy`
- Health monitored via Holocene dashboard

---

## File Locations

| Component | Directory |
|-----------|-----------|
| Bloodbank | `bloodbank/trunk-main/` |
| Holyfields | `holyfields/trunk-main/` |
| Candystore | `services/candystore/` |
| Candybar | `candybar/trunk-main/` |
| Flume | `flume/trunk-main/` |
| Yi | `yi/trunk-main/` |
| AgentForge | `agent-forge/trunk-main/` |
| Holocene | `holocene/trunk-main/` |
| iMi | `iMi/trunk-main/` |
| Jelmore | `jelmore/trunk-main/` |
| Zellij-Driver | `zellij-driver/` |
| Perth | `perth/trunk-main/` |
| TheBoard | `theboard/trunk-main/` |
| TheBoardroom | `theboardroom/trunk-main/` |
| HeyMa | `HeyMa/trunk-main/` |
| Degenerate | `degenerate/trunk-main/` |
| BMAD Config | `bmad/config.yaml` |
| Service Registry | `services/registry.yaml` |
| Domain Docs | `docs/domains/` |
| Component Docs | `docs/components/` |

---

## Related Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [Domain Documentation Index](./domains/DOMAINS.md)
- [Component Technical Docs](./components/README.md)
- [Unified Requirements Map](./unified-requirements-map.md)
- [Service ERD](./SERVICE_ERD.md)

---

**Last Updated**: 2026-01-31
