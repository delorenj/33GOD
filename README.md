# 33GOD

**An Event-Driven, Agentic Development Ecosystem**

33GOD is a sophisticated platform for orchestrating software development, knowledge management, and automated workflows through multi-agent teams. Built on an event-driven architecture, it enables AI agents and microservices to collaborate asynchronously across multiple projects simultaneously.

> *Everything is an event.* All significant state changes—Git commits, PRs, transcripts, agent decisions, meetings—are emitted as events, allowing autonomous agents to coordinate seamlessly.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              33GOD Platform                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌────────────┐  │
│   │ TalkyTonny  │    │   Flume     │    │  AgentForge │    │  TheBoard  │  │
│   │   (Voice)   │───▶│ (Protocol)  │───▶│   (Teams)   │───▶│(Brainstorm)│  │
│   └─────────────┘    └─────────────┘    └─────────────┘    └────────────┘  │
│          │                  │                  │                  │         │
│          ▼                  ▼                  ▼                  ▼         │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    BLOODBANK (Central Event Bus)                     │  │
│   │                         RabbitMQ + FastStream                        │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│          │                  │                  │                  │         │
│          ▼                  ▼                  ▼                  ▼         │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌────────────┐  │
│   │  Holyfields │    │   Jelmore   │    │     iMi     │    │  Candybar  │  │
│   │  (Schemas)  │    │ (Sessions)  │    │ (Worktrees) │    │ (Registry) │  │
│   └─────────────┘    └─────────────┘    └─────────────┘    └────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### Infrastructure & Core

| Component | Description |
|-----------|-------------|
| **[Bloodbank](bloodbank/)** | Central event bus providing RabbitMQ-based messaging infrastructure. All services communicate through Bloodbank events with topic exchanges, schema validation, and correlation tracking. |
| **[Holyfields](holyfields/)** | Schema registry and microservice contract system. Maintains canonical event definitions using JSON Schema as source of truth, generating type-safe code for Python (Pydantic) and TypeScript (Zod). |
| **[Candystore](services/)** | Event Store Manager that persists all events to PostgreSQL for audit and replay. |

### Git & Worktree Management

| Component | Description |
|-----------|-------------|
| **[iMi](iMi/)** | Rust CLI for managing Git worktrees in a decentralized, multi-agent workflow. Enforces `trunk-main`, `feat-*`, `fix-*` directory structure and tracks branches linked to projects and tasks. |
| **[Zellij Driver](zellij-driver/)** | Context manager (`zdrive`) for Zellij terminal sessions. Tracks intents, logs milestones, and maintains context across sessions using Redis. |
| **[Perth](perth/)** | Customized Zellij terminal multiplexer distribution optimized for the 33GOD workflow. |

### Agent Frameworks & Orchestration

| Component | Description |
|-----------|-------------|
| **[Flume](flume/)** | The Agentic Corporate Protocol. Defines organizational hierarchy (Manager, Contributor), communication interfaces, and role definitions. Framework-agnostic orchestration layer. |
| **[Yi](yi/)** | The Opinionated Agent Adapter. Enforces 33GOD conventions on top of Flume, wrapping AI SDKs (Letta, Agno, Smolagents) into compliant Manager and Contributor nodes. |
| **[AgentForge](agent-forge/)** | Meta-agent team builder. Uses a team of specialized agents (Engineering Manager, Systems Analyst, Talent Scout, Agent Developer, Integration Architect) to dynamically assemble optimal agent rosters. |

### Repositories & Intelligence

| Component | Description |
|-----------|-------------|
| **[Holocene](holocene/)** | The Hive Mind. Central repository housing agent definitions in `.claude/agents`, collective intelligence, and mission control dashboard for portfolio visibility. |
| **[Degenerate](degenerate/)** | Rust CLI for documentation sync and drift detection. Tracks documentation state across components and maintains consistency. |

### Applications & Interfaces

| Component | Description |
|-----------|-------------|
| **[TheBoard](theboard/)** | Multi-agent brainstorming simulation system. Features intelligent comment extraction, context compression, and convergence detection for ideation and architecture discussions. |
| **[TheBoard Room](theboardroom/)** | Web UI for TheBoard brainstorming sessions. |
| **[Candybar](candybar/)** | Service registry hub and topology visualization dashboard. Built with Next.js + Tauri, displays real-time service health, event flows, and system architecture. |
| **[TalkyTonny](TalkyTonny/)** | Voice interface system integrating WhisperLiveKit for transcription and ElevenLabs for text-to-speech. Includes Chrome extension support. |

### Development Tools

| Component | Description |
|-----------|-------------|
| **[Jelmore](jelmore/)** | Session manager for Claude Code. FastAPI service managing long-lived AI coding sessions with unified interface for Codex, Claude, Gemini, Auggie, CoPilot, and OpenCode. |
| **[BMAD](bmad/)** | Business, Management, Architecture, Development methodology configuration. Contains orchestrator configs and agent overrides to enforce consistent process across the ecosystem. |

---

## Pipeline Flow

```
1. INITIATION
   └─ Voice (TalkyTonny) │ Git commit │ Webhook │ Manual task
                         ▼
2. ORCHESTRATION
   └─ Flume receives trigger → AgentForge assembles team
                         ▼
3. EXECUTION
   └─ Yi agents claim tasks → Jelmore spins up sessions → iMi manages worktrees
                         ▼
4. EVENT EMISSION
   └─ All events flow through Bloodbank → Validated by Holyfields → Stored by Candystore
                         ▼
5. COLLABORATION
   └─ TheBoard triggered for brainstorming → Convergence analysis → Decisions emitted
                         ▼
6. VISIBILITY
   └─ Candybar displays topology │ Holocene shows portfolio │ Degenerate syncs docs
```

---

## Event-Driven Design

### Core Patterns

- **Event Sourcing**: Every action is an immutable event stored in PostgreSQL, enabling full audit trails and replay
- **Correlation Tracking**: Related events linked by `correlation_ids` for tracing causation chains
- **Type Safety**: All events validated against Holyfields schemas before routing
- **Durable Subscriptions**: Services use named queues (`services.<domain>.<service_name>`) to survive restarts
- **Dead Letter Queues**: Failed messages route to DLQs for replay and debugging

### Event Flow Example

```
feature.requested
    │
    ├──▶ Flume (orchestration)
    │       └──▶ agent.team.assembled
    │
    ├──▶ Event Store Manager (persistence)
    │
    └──▶ Holocene (portfolio tracking)
              │
              └──▶ session.started
                      │
                      ├──▶ code.committed (multiple)
                      │
                      ├──▶ architecture.review.needed
                      │       └──▶ TheBoard Meeting Trigger
                      │               └──▶ decision.made
                      │
                      └──▶ feature.completed
```

---

## Technology Stack

| Layer | Technologies |
|-------|--------------|
| **Event Bus** | RabbitMQ, FastStream (Python async) |
| **Schemas** | JSON Schema, Pydantic, Zod |
| **Backend** | Python (FastAPI, aio-pika), Rust |
| **Agents** | Claude (Jelmore), Letta, Agno, Smolagents |
| **Frontend** | Next.js + Tauri, React + shadcn/ui |
| **Database** | PostgreSQL, Redis, Qdrant (vector) |
| **Terminal** | Zellij (Perth distro) |
| **Voice** | WhisperLiveKit, ElevenLabs |
| **Integration** | Node-RED, Fireflies.ai, GitHub, Obsidian |

---

## Services

The `/services` directory contains microservices that consume and produce events:

| Service | Purpose |
|---------|---------|
| **Fireflies Transcript Processor** | Processes `fireflies.transcript.ready` events, outputs markdown to Vault |
| **Event Store Manager (Candystore)** | Subscribes to all events, persists to PostgreSQL, provides REST/WebSocket APIs |
| **TheBoard Meeting Trigger** | Watches for brainstorming triggers, creates automated sessions |
| **Agent Feedback Router** | Routes feedback requests to AgentForge |
| **Tonny Agent** | Letta-powered voice processing with ElevenLabs TTS |
| **Node-RED Orchestrator** | Manages external integrations and flow definitions |

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- RabbitMQ instance (or use provided Docker config)
- PostgreSQL, Redis, Qdrant
- Node.js 18+ and Python 3.11+
- Rust toolchain (for CLI tools)

### Clone with Submodules

```bash
git clone --recursive https://github.com/your-org/33GOD.git
cd 33GOD

# Or if already cloned:
git submodule update --init --recursive
```

### Infrastructure Setup

```bash
# Start core infrastructure
docker-compose up -d rabbitmq postgres redis qdrant

# Initialize Bloodbank exchanges
cd bloodbank && ./scripts/init-exchanges.sh
```

### Component Development

Each component is an independent repository. Navigate to its directory and follow component-specific instructions:

```bash
cd bloodbank/trunk-main
# Follow bloodbank/README.md

cd ../holyfields/trunk-main
# Follow holyfields/README.md
```

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - C4 diagrams and system design
- [Service Registry](services/registry.yaml) - Service definitions and topology
- [Unified Requirements](docs/unified-requirements-map.md) - Event architecture roadmap
- [Agents Directory](AGENTS.md) - Component reference

---

## License

See individual component repositories for licensing information.
