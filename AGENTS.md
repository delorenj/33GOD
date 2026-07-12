# 33GOD — Monorepo Knowledge Base

**Generated:** 2026-07-11

## OVERVIEW

Event-driven agentic development pipeline. Multi-agent teams coordinate asynchronously via Bloodbank (NATS/dapr). Candystore persists everything; Holocene as control plane and dashboard.

## Components

```
./
├── bloodbank/      # NATs Event bus / dapr
├── candystore/     # Event persistence + audit trail
├── holocene/       # Control plane
├── pjangler/       # Project registry, management, and bootstrapping
├── flume/          # Agent hierarchy, role assignment, and company org chart
├── hermes-fleet/   # System-wide registry of project-scoped PM agents
├── plane/          # Open Source ticketing platform and kanban task management
├── n8n/            # Open Source node-based automation platform
├── hindsight/      # Memory framework for agents
├── voxxy/          # Multi-engine TTS service
├── skillex/        # Custom skill framework for agents
├── momo/           # Agentic Ticketing Workflow and Project Lifecycle System
├── bmad/           # Open Source project planning and documentation framework.
```

## Current Working Document

Use ./PRD.md to track state right now, until we initialize BMAD
