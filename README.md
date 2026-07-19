# 33GOD

**An Event-Driven, Agentic Development Pipeline**

33GOD is a sophisticated platform for orchestrating software development, knowledge management, and automated workflows through multi-agent teams. Built on an event-driven architecture, it enables AI agents and microservices to collaborate asynchronously across multiple projects simultaneously.

> _Everything is an event._ All significant state changes—Git commits, PRs, transcripts, agent decisions, meetings—are emitted as events, allowing autonomous agents to coordinate seamlessly.

> **Product control plane:** the current productized-platform map lives in
> [`33god-platform/`](33god-platform/). Use its component manifests,
> pipeline changelog, and backfill checks before relying on older prose in this
> README.

---

## Components

### Infrastructure & Core

| Component                     | Description                                                                                                                                                                                         |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **[Bloodbank](bloodbank/)**   | Canonical inter-service schemas plus NATS JetStream/Dapr transport. It does not own project-lifecycle semantics.                                                                                    |
| **[Lifecycle](lifecycle/)**   | Sole deterministic project-lifecycle authority: specification, state, reconcile, legal frontier, obligations, grants, and state-changing writes.                                                    |
| **[Candystore](candystore/)** | Append-only Bloodbank event history and durable Lifecycle read projections. It exposes no operational Lifecycle write path.                                                                         |
| **[Perth](perth/)**           | Customized Zellij terminal multiplexer distribution optimized for the 33GOD workflow.                                                                                                               |
| **[Momo](momo/)**             | Policy/process-manager and durable work actor that ranks only Lifecycle-legal work, executes exact canonical skill invocations, and publishes retry-stable artifact evidence through Bloodbank with PubAck-before-ACK. |
| **[Holocene](holocene/)**     | Mission-control renderer backed by Candystore projections, with high-level Lifecycle commands published through Bloodbank. It never derives or persists lifecycle truth.                            |
| **[Candybar](candybar/)**     | Service registry hub and topology visualization dashboard. Built with Next.js + Tauri, displays real-time service health, event flows, and system architecture.                                     |
| **[HeyMa](HeyMa/)**           | Voice interface system integrating WhisperLiveKit for transcription and ElevenLabs for text-to-speech. Includes Chrome extension support.                                                           |
| **[BMAD](bmad/)**             | Business, Management, Architecture, Development methodology configuration. Contains orchestrator configs and agent overrides to enforce consistent process across the ecosystem.                    |
