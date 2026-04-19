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

## Applications

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

## Services

**Directory:** `services/`
**Role:** Microservices Collection.
**Description:** Contains various standalone bloodbank-driven microservices that register with the 33GOD pipeline through the Service Hub

- **base**: Base service templates/classes.
- **fireflies-transcript-processor**: Processes meeting transcripts from Fireflies.ai.
- **node-red-flow-orchestrator**: Integration with Node-RED.
- **templates**: Service templates (e.g., `generic-consumer`).
- **theboard-meeting-trigger**: (dormant since 2026-04-19 slimdown) Triggers TheBoard meetings from external events; re-activates when TheBoard component is reintegrated.

---

## Active Architecture Pattern: Event-Driven Subscriber Microservices

The system relies on a central event bus (**Bloodbank**) and a decentralized ecosystem of subscriber services.

### Standard Service Interface

- **Base Class:** `BaseSubscriber`
- **Config:** Connects to `BLOODBANK_URL`.
- **Queue Naming:** `services.<domain>.<service_name>`
- **Behavior:** Durable subscriptions, dead-letter handling, idempotent processing.
