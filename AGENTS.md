# 33GOD Ecosystem & Agent Directory

This document provides a comprehensive overview of the components, directories, and agents within the 33GOD meta-repository.

## Core Infrastructure

### 🩸 Bloodbank
**Directory:** `bloodbank/`
**Role:** Central Event Bus & Infrastructure.
**Tech:** RabbitMQ, Python (FastStream/aio-pika), Kubernetes.
**Description:** The nervous system of 33GOD. Provides the RabbitMQ-based event bus infrastructure and defines the standard event schemas. Contains the core `rabbit.py` publisher/subscriber logic and deployment configs.

### 🌳 iMi
**Directory:** `iMi/`
**Role:** Worktree Management CLI.
**Tech:** Rust.
**Description:** A command-line tool for managing Git worktrees, specifically designed to support decentralized, multi-agent development workflows. Enforces the `trunk-main`, `feat-*` directory structure.

### 🌊 Flume
**Directory:** `flume/`
**Role:** Agentic Protocol & Interfaces.
**Tech:** TypeScript/Node.js.
**Description:** "The Agentic Corporate Protocol". Defines the structural hierarchy (Manager, Contributor), communication interfaces, and role definitions for agents. Agnostic to the underlying intelligence (LLM/Framework).

### 👔 Yi
**Directory:** `yi/`
**Role:** Agent Adapter & Enforcer.
**Tech:** TypeScript.
**Description:** "The Opinionated Agent Adapter". Enforces 33GOD conventions on top of the Flume protocol. Wraps specific AI SDKs (Letta, Agno, Smolagents) into compliant Manager and Contributor nodes.

### 📜 Holyfields
**Directory:** `holyfields/`
**Role:** Microservice Contract System.
**Tech:** JSON Schema, Pydantic, Zod.
**Description:** A centralized event schema registry using JSON Schema as the source of truth for Bloodbank events. Facilitates async communication contracts between LLM coding agents and services.

## Agent Frameworks & Platforms

### ⚒️ AgentForge
**Directory:** `agent-forge/`
**Role:** Meta-Agent Team Builder.
**Tech:** Python, Agno.
**Description:** A system for building specialized agent teams. Uses a meta-team of agents (Engineering Manager, Systems Analyst, Talent Scout, Agent Developer, Integration Architect) to analyze goals and assemble optimal agent rosters.

### 🧠 Holocene
**Directory:** `holocene/`
**Role:** Hive Mind & Agent Repository.
**Description:** The central repository for the "Hive Mind" and a vast collection of agent definitions (in `.claude/agents`). Acts as the container for the collective intelligence and potentially the runtime for many core agents.

### 📐 BMAD
**Directory:** `bmad/`
**Role:** Methodology & Orchestration.
**Description:** Configuration and definitions for the **BMAD** (Business, Management, Architecture, Development) methodology. Likely contains orchestrator configs (`config.yaml`) and agent overrides to enforce the BMAD process across the ecosystem.

## Applications

### 🎯 TheBoard
**Directory:** `theboard/`
**Role:** Multi-Agent Brainstorming Simulation.
**Tech:** Python, Typer, Rich, Agno, Letta, Postgres, Redis, Qdrant.
**Description:** A sophisticated system for simulating brainstorming sessions with AI agents. Features intelligent comment extraction, context compression, and convergence detection.
- **TheBoardRoom** (`theboardroom/`): Frontend/UI for TheBoard.

### 🍬 Candybar
**Directory:** `candybar/`
**Role:** Service Registry Hub.
**Tech:** Next.js + Tauri (Nextauri).
**Description:** The visual "Hub" for the 33GOD platform service registry. Visualizes service topology and health.

### 🗣️ HeyMa
**Directory:** `HeyMa/`
**Role:** Voice Interface.
**Tech:** Python (Whisper), Rust (Tauri), Chrome Extension.
**Description:** A voice-to-text system allowing users to talk to their computer. Integrates WhisperLiveKit for transcription and ElevenLabs for TTS.

### 🐚 Jelmore
**Directory:** `jelmore/`
**Role:** Session Manager for Claude Code.
**Tech:** FastAPI, Docker.
**Description:** Manages long-lived, interactive sessions with Claude Code AI. Provides a REST API to control AI coding sessions programmatically.

## Development Tools

### 🖥️ Perth
**Directory:** `perth/`
**Role:** Terminal Multiplexer Distribution.
**Tech:** Rust (Zellij Fork/Distro).
**Description:** A customized distribution of the Zellij terminal multiplexer, optimized for the 33GOD workflow.

### 🚗 Zellij Driver (zdrive)
**Directory:** `zellij-driver/`
**Role:** Context Manager.
**Tech:** Rust.
**Description:** A CLI tool (`zdrive`) for managing context within Zellij sessions. Tracks intents, logs milestones, and maintains context across sessions using Redis.

## Services

**Directory:** `services/`
**Role:** Microservices Collection.
**Description:** Contains various standalone microservices that plug into the ecosystem (usually via Bloodbank).
- **agent-feedback-router**: Routes feedback events.
- **base**: Base service templates/classes.
- **event-store-manager**: Manages event persistence.
- **fireflies-transcript-processor**: Processes meeting transcripts from Fireflies.ai.
- **node-red-flow-orchestrator**: Integration with Node-RED.
- **templates**: Service templates (e.g., `generic-consumer`).
- **theboard-meeting-trigger**: Triggers TheBoard meetings from external events.

---

## Active Architecture Pattern: Event-Driven Subscriber Microservices

The system relies on a central event bus (**Bloodbank**) and a decentralized ecosystem of subscriber services.

### Core Components

1.  **Event Backbone (Bloodbank)**: RabbitMQ Topic Exchanges (`amq.topic`).
2.  **Service Registry (Candybar)**: Central authority for service discovery and health monitoring.
3.  **Subscriber Microservices**: Autonomous agents/services implementing `BaseSubscriber`.

### Standard Service Interface

- **Base Class:** `BaseSubscriber`
- **Config:** Connects to `BLOODBANK_URL`.
- **Queue Naming:** `services.<domain>.<service_name>`
- **Behavior:** Durable subscriptions, dead-letter handling, idempotent processing.
