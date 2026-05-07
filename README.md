# 33GOD

**An Event-Driven, Agentic Development Pipeline**

33GOD is a sophisticated platform for orchestrating software development, knowledge management, and automated workflows through multi-agent teams. Built on an event-driven architecture, it enables AI agents and microservices to collaborate asynchronously across multiple projects simultaneously.

> _Everything is an event._ All significant state changes—Git commits, PRs, transcripts, agent decisions, meetings—are emitted as events, allowing autonomous agents to coordinate seamlessly.

---

## Components

### Infrastructure & Core

| Component                     | Description                                                                                                                                                                                         |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **[Bloodbank](bloodbank/)**   | Central event bus providing RabbitMQ-based messaging infrastructure. All services communicate through Bloodbank events with topic exchanges, schema validation, and correlation tracking.           |
| **[Holyfields](holyfields/)** | Schema registry and microservice contract system. Maintains canonical event definitions using JSON Schema as source of truth, generating type-safe code for Python (Pydantic) and TypeScript (Zod). |
| **[Candystore](services/)**   | Event Store Manager that persists all events to PostgreSQL for audit and replay.                                                                                                                    |
| **[Perth](perth/)**           | Customized Zellij terminal multiplexer distribution optimized for the 33GOD workflow.                                                                                                               |
| **[Holocene](holocene/)**     | The Hive Mind. Central repository housing agent definitions in `.claude/agents`, collective intelligence, and mission control dashboard for portfolio visibility.                                   |
| **[Candybar](candybar/)**     | Service registry hub and topology visualization dashboard. Built with Next.js + Tauri, displays real-time service health, event flows, and system architecture.                                     |
| **[HeyMa](HeyMa/)**           | Voice interface system integrating WhisperLiveKit for transcription and ElevenLabs for text-to-speech. Includes Chrome extension support.                                                           |
| **[BMAD](bmad/)**             | Business, Management, Architecture, Development methodology configuration. Contains orchestrator configs and agent overrides to enforce consistent process across the ecosystem.                    |
