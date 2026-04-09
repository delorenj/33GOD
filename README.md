# 33GOD

**An Event-Driven, Agentic Development Ecosystem**

33GOD is a sophisticated platform for orchestrating software development, knowledge management, and automated workflows through multi-agent teams. Built on an event-driven architecture, it enables AI agents and microservices to collaborate asynchronously across multiple projects simultaneously.

> _Everything is an event._ All significant state changes—Git commits, PRs, transcripts, agent decisions, meetings—are emitted as events, allowing autonomous agents to coordinate seamlessly.

---

## Architecture Overview

TODO

## Components

### Infrastructure & Core

| Component                           | Description                                                                                                                                                                                         |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **[Bloodbank](bloodbank/)**         | Central event bus providing RabbitMQ-based messaging infrastructure. All services communicate through Bloodbank events with topic exchanges, schema validation, and correlation tracking.           |
| **[Holyfields](holyfields/)**       | Schema registry and microservice contract system. Maintains canonical event definitions using JSON Schema as source of truth, generating type-safe code for Python (Pydantic) and TypeScript (Zod). |
| **[Candystore](services/)**         | Event Store Manager that persists all events to PostgreSQL for audit and replay.                                                                                                                    |
| **[Zellij Driver](zellij-driver/)** | Context manager (`zdrive`) for Zellij terminal sessions. Tracks intents, logs milestones, and maintains context across sessions using Redis.                                                        |
| **[Perth](perth/)**                 | Android Client App to connect to zellij backend through proxy bridge adapter for voice controlled terminal sessions.                                                                                |
| **[Holocene](holocene/)**           | web dashboard                                                                                                                                                                                       |
| **[TheBoard](theboard/)**           | Multi-agent brainstorming simulation system. Features intelligent comment extraction, context compression, and convergence detection for ideation and architecture discussions.                     |
| **[TheBoard Room](theboardroom/)**  | Web UI for TheBoard brainstorming sessions.                                                                                                                                                         |
| **[HeyMa](HeyMa/)**                 | Voice interface system integrating WhisperLiveKit for transcription and ElevenLabs for text-to-speech. Includes Chrome extension support.                                                           |
| **[Jelmore](jelmore/)**             | Session manager for Claude Code. FastAPI service managing long-lived AI coding sessions with unified interface for Codex, Claude, Gemini, Auggie, CoPilot, and OpenCode.                            |
| **[hUUk](hUUk/)**                   | Unified hook system to integrate 33god throughout all cli coders (claude, gemini, codex, opencode)                                                                                                  |

---

## Event-Driven Design

### Core Patterns

- **Event Sourcing**: Every action is an immutable event stored in PostgreSQL, enabling full audit trails and replay
- **Correlation Tracking**: Related events linked by `correlation_ids` for tracing causation chains
- **Type Safety**: All events validated against Holyfields schemas before routing
- **Durable Subscriptions**: Services use named queues (`services.<domain>.<service_name>`) to survive restarts
- **Dead Letter Queues**: Failed messages route to DLQs for replay and debugging
