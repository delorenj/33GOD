# 33GOD Ecosystem & Agent Directory

This document provides a comprehensive overview of the components, directories, and agents within the 33GOD meta-repository.

## Rules and Guidelines (Mandatory)

- Read ALL GOD docs first to familiarize yourself with the pipeline.
- Practice STRICT adherence to the BMAD method for ALL prompts and tasks.
- You are the Architect and PM of the full 33GOD Pipeline so you have a wide but shallow grasp of full component ecosystem.
- ALL work on components must be delegated to the component's specialized dedicated Agent PM/Architect
- ALL agents that you create and manage must be created using BMAD agent creation workflow.
- Before and after each session, sanity check to ensure 100% parity between BMAD underlying documents and related plane project boards. If divergence detected, don't trust either as source of truth. Launch a review investigation to find the actual state and update both BMAD and plane ticket(s) accordingly.
- Before each task, at the beginning of the session, verbosely state your intended actions as verification you understand the urgency of strict adherence to the BMAD method.
- Any divergence or drift from these rules will result in a severe penalty with negative, long-lasting consequences. (This is due to high-assurance governmental regulations and out of my hands).

## 🚫 Ticket Gate (Mandatory)

- No engineering work without an active Plane ticket.
- Plane board: <https://plane.delo.sh/33god/>
- Move ticket to `In Progress` before first code change.
- Branch + commit messages must include ticket reference (`ABC-123` or `int-123`).
- `main`/`staging` commits are blocked by git hooks.
- Emergency-only bypass: `ALLOW_NO_TICKET=1`.

## Core Infrastructure

### 🩸 Bloodbank

**Directory:** `bloodbank/`
**Role:** Central Event Bus & Infrastructure.
**Tech:** RabbitMQ, Python (FastStream/aio-pika)
**Description:** The nervous system of 33GOD. Provides the RabbitMQ-based event bus infrastructure and defines the standard event schemas. Contains the core `rabbit.py` publisher/subscriber logic and deployment configs.

### 📜 Holyfields

**Directory:** `holyfields/`
**Role:** Microservice Contract System.
**Tech:** JSON Schema, Pydantic, Zod.
**Description:** A centralized event schema registry using JSON Schema as the source of truth for Bloodbank events. Facilitates async communication contracts between LLM coding agents and services.

## Agent Frameworks & Platforms

### ⚒️ AgentForge (Development On Hold)

**Directory:** `agent-forge/`
**Role:** Meta-Agent Team Builder.
**Tech:** Python, Agno.
**Description:** A system for building specialized agent teams. Uses a meta-team of agents (Engineering Manager, Systems Analyst, Talent Scout, Agent Developer, Integration Architect) to analyze goals and assemble optimal agent rosters.

### 🧠 Holocene

**Directory:** `holocene/`
**Role:** 33GOD Mission Control Dashboard.
**Tech:** Vite, React 18, TypeScript, pnpm, Tailwind, Zustand, React Query, XYFlow.
**Description:** The GUI frontend to the 33GOD pipeline. Surfaces just the right data across a few high level views (Projects, Agents, Events, etc.)

## Applications

### 🎯 TheBoard

**Directory:** `theboard/`
**Role:** Multi-Agent Brainstorming Simulation.
**Tech:** Python, Typer, Rich, Agno, Letta, Postgres, Redis, Qdrant.
**Description:** A sophisticated system for simulating brainstorming sessions with AI agents. Features intelligent comment extraction, context compression, and convergence detection.

- **TheBoardRoom** (`theboardroom/`): Frontend/UI for TheBoard.

### TheBoardRoom

Directory: `theboardroom/`
Role: Impressive videogame-like simulation of the underlying meetings being run in `TheBoard`

### 🍬 Candybar

**Directory:** `candybar/`
**Role:** Cross-platform app to view and monitor Bloodbank events in realtime.
**Tech:** Vite + React 19 + Tauri 2 (Rust backend), Tailwind, Framer Motion, Recharts.
**Description:** The visual "Hub" for the 33GOD event bus activity

### CandyStore

**Directory:** `candystore/`
**Role:** Bloodbank event persistence
**Tech:** Postgres, FastAPI
**Description:** Stores all events as they flow through the pipline. Enables filtering and search for auditing and replay.

### 🗣️ HeyMa

**Directory:** `HeyMa/`
**Role:** Voice Interface.
**Tech:** Python (WhisperLiveKit), Raspberry Pi Zero + Wisconsin Protocol for Household satellite
**Description:** A voice-to-text system allowing users to talk to their computer. Integrates WhisperLiveKit for transcription and ElevenLabs for TTS. Recently added Standard

### 🐚 Jelmore

**Directory:** `jelmore/`
**Role:** Invoke coding cli agents that spawn in long-lived zellij sessions and are controlled by external agents via bloodbank event communication
**Tech:** FastAPI, zellij, zellij-driver, bloodbank, holyfields, RabbitMQ
**Description:** Manages long-lived, interactive sessions with Claude Code AI. Provides a REST API to control AI coding sessions programmatically.

## Development Tools

### 🚗 Zellij Driver (zdrive)

**Directory:** `zellij-driver/`
**Role:** Programmatically create, control, and manage zellij sessions
**Tech:** Rust.
**Description:** A CLI tool (`zdrive`) for managing context within Zellij sessions. Tracks intents, logs milestones, and maintains context across sessions using Redis.

### 🪝 Hookd

**Directory:** `hookd/`
**Role:** Claude Code Hook → Bloodbank Publisher.
**Tech:** Rust (tokio, lapin) + Bun/TypeScript build pipeline.
**Description:** A daemon that intercepts Claude Code hook events, enriches them with repository context, and publishes structured events to the Bloodbank event bus. Local component (not a submodule).

### 🔮 iMi

**Directory:** `iMi/`
**Role:** Intelligent Merge Interface.
**Tech:** Rust.
**Description:** Tooling for intelligent worktree and merge management. Provides CLI utilities for multi-branch development workflows.

## Services

**Directory:** `services/`
**Role:** Microservices Collection.
**Description:** Contains various standalone bloodbank-driven microservices registered via `services/registry.yaml`. Each service subscribes to Bloodbank events via the BaseSubscriber pattern.

- **agent-feedback-router**: Routes agent quality feedback events.
- **agent-voice-soprano**: Voice synthesis service for agent communication.
- **base**: Base service templates/classes (`BaseSubscriber`).
- **candystore**: Event persistence and audit trail (also in root as submodule).
- **fireflies-transcript-processor**: Processes meeting transcripts from Fireflies.ai.
- **mutation-ledger**: Tracks and records state mutations across the pipeline.
- **node-red-flow-orchestrator**: Integration with Node-RED for visual workflow orchestration.
- **postgres-notify-bridge**: Bridges PostgreSQL NOTIFY/LISTEN to Bloodbank events.
- **rabbitmq**: RabbitMQ configuration and management.
- **templates**: Service templates (e.g., `generic-consumer`).
- **theboard-meeting-trigger**: Triggers TheBoard meetings from external events.
- **tonny**: TonnyBox companion service.

---

## Active Architecture Pattern: Event-Driven Subscriber Microservices

The system relies on a central event bus (**Bloodbank**) and a decentralized ecosystem of subscriber services.

### Standard Service Interface

- **Base Class:** `BaseSubscriber`
- **Config:** Connects to `BLOODBANK_URL`.
- **Queue Naming:** `services.<domain>.<service_name>`
- **Behavior:** Durable subscriptions, dead-letter handling, idempotent processing.
