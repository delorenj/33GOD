# 33GOD Ecosystem & Agent Directory

This document provides a comprehensive overview of the components, directories, and agents within the 33GOD meta-repository.

## Rules and Guidelines (Mandatory)

- Read ALL GOD docs first to familiarize yourself with the pipeline.
- Follow the BMAD method for specification, planning, and review. BMAD is the thinking framework; it does not require an external tracker to be correct.
- You are the Architect and PM of the full 33GOD Pipeline so you have a wide but shallow grasp of the full component ecosystem.
- Work on components may be delegated to the component's specialized Agent PM/Architect when the component is mature enough to own its surface.
- Prefer direct commits on ticket-prefixed branches when moving fast is more valuable than ceremony. A clear commit message + a BMAD artifact in `_bmad-output/` beats a half-synchronized ticket.
- Source of truth is the code, the committed BMAD artifacts, and eventually the Bloodbank event log. External trackers are read-through caches, not authorities.

## 🟡 Plane: SUSPENDED as source of truth (2026-04-22)

**Status:** The 33GOD Plane workspace has drifted far enough from reality that treating it as a truth source produces a web of lies. Bloodbank will become the canonical event log; until it does, we operate without a ticket gate.

**Operating rules during suspension:**

- **No ticket gate.** Do not require a Plane issue to exist before making code changes. Do not block commits on ticket references.
- **Branch naming stays ticket-prefixed when convenient.** If you already have a `GOD-XX` / `BB-XX` issue that matches the work, use it in the branch name and commit subject. If you don't, use a descriptive kebab slug (`fix/nats-healthcheck`, `feat/smoke-test-event`). Both are acceptable.
- **Do not invent new Plane issues speculatively.** Only create a Plane issue when it represents work you are about to do or a decision you have already made and want persistent reference to. No backlog-padding.
- **Do not "sync" BMAD artifacts to Plane on a schedule.** The parity audit rule is rescinded. When Plane and code disagree, trust the code and the commit log.
- **Emit the intent in the commit message, not a ticket description.** Multi-paragraph "why" belongs in `git log`, not a Plane field that will decay.

**Re-enabling Plane:**

Plane returns as a first-class surface only when all three are true:

1. Bloodbank v3 is running reliably (ADR-0001 acceptance met end-to-end).
2. Bloodbank emits `code.*` events on commit / PR / deploy that a Plane sync job can consume.
3. An audit pass (scripted, not manual) confirms every open Plane issue corresponds to either live work or an explicit archived state.

Until then, treat Plane as a read-only historical artifact. Writes to it are optional courtesy, not discipline.

**What this does NOT change:**

- Git hygiene: clean commits, descriptive messages, no force-pushes, no `--no-verify`.
- BMAD artifacts: specs, epic/story breakdowns, ADRs still live under `_bmad-output/` and `docs/architecture/`.
- Review discipline: multi-axis reviews still run before merge. The adversarial review skill is especially load-bearing when the ticket gate is down.
- Branch-per-change workflow: still required, just without the ticket prerequisite.

## Core Infrastructure

### 🩸 Bloodbank

**Directory:** `bloodbank/`
**Role:** Central Event Bus & Runtime Platform.
**Tech (v2, legacy):** RabbitMQ, Python (FastStream/aio-pika).
**Tech (v3, in flight):** Dapr runtime + NATS JetStream broker + CloudEvents 1.0 envelopes + AsyncAPI contracts. Bloodbank becomes an operator-tool surface; production publishing moves into services via Dapr + Holyfields-generated SDKs.
**Description:** The nervous system of 33GOD. v2 provides the legacy RabbitMQ event bus. v3 (tracked in `docs/architecture/v3-implementation-plan.md` and ratified in `docs/architecture/ADR-0001-v3-platform-pivot.md`) pivots to a swap-able broker behind Dapr.
**Source of truth marker:** Once v3 lands, the Bloodbank event log is the canonical system-state record. The metarepo and its components converge on the bus, not on any external tracker.

### 🌊 Flume (Development On Hold)

**Directory:** `flume/`
**Role:** Agentic Protocol & Interfaces.
**Tech:** TypeScript/Node.js.
**Description:** "The Agentic Corporate Protocol". Defines the structural hierarchy (Manager, Contributor), communication interfaces, and role definitions for agents. Agnostic to the underlying intelligence (LLM/Framework).

### 👔 Yi (Development On Hold)

**Directory:** `yi/`
**Role:** Agent Adapter
**Tech:** TypeScript.
**Description:** Abstracts agents to allow many agent frameworks to adhere and plug into the Flume tree in the 33GOD pipeline. Enforces 33GOD conventions on top of the Flume protocol. Wraps specific AI SDKs (Google ADK, Agno, Smolagents) into compliant Manager and Contributor nodes.

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
**Role:** 33GOD Dashboard
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
**Tech:** Next.js + Tauri (Nextauri).
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

### 🖥️ Perth (Development On Hold)

**Directory:** `perth/`
**Role:** Terminal Multiplexer Distribution.
**Tech:** Rust (Zellij Fork/Distro).
**Description:** A customized distribution of the Zellij terminal multiplexer, optimized for the 33GOD workflow.

### 🚗 Zellij Driver (zdrive)

**Directory:** `zellij-driver/`
**Role:** Programmatically create, control, and manage zellij sessions
**Tech:** Rust.
**Description:** A CLI tool (`zdrive`) for managing context within Zellij sessions. Tracks intents, logs milestones, and maintains context across sessions using Redis.

## Services

**Directory:** `services/`
**Role:** Microservices Collection.
**Description:** Contains various standalone bloodbank-driven microservices that register with the 33GOD pipeline through the Service Hub

- **base**: Base service templates/classes.
- **fireflies-transcript-processor**: Processes meeting transcripts from Fireflies.ai.
- **node-red-flow-orchestrator**: Integration with Node-RED.
- **templates**: Service templates (e.g., `generic-consumer`).
- **theboard-meeting-trigger**: Triggers TheBoard meetings from external events.

---

## Active Architecture Pattern: Event-Driven Subscriber Microservices

The system relies on a central event bus (**Bloodbank**) and a decentralized ecosystem of subscriber services.

### Standard Service Interface

- **Base Class:** `BaseSubscriber`
- **Config:** Connects to `BLOODBANK_URL`.
- **Queue Naming:** `services.<domain>.<service_name>`
- **Behavior:** Durable subscriptions, dead-letter handling, idempotent processing.
