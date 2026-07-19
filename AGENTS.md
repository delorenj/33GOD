# 33GOD — Monorepo Knowledge Base

**Generated:** 2026-07-19

## OVERVIEW

Event-driven agentic development pipeline. Multi-agent teams coordinate asynchronously via Bloodbank (NATS/Dapr). Lifecycle alone owns deterministic lifecycle truth and reconciliation; Candystore persists audit history and read projections; Holocene renders the operator dashboard and submits high-level actions.

## Components

```
./
├── bloodbank/      # Canonical schemas plus NATS/Dapr transport
├── lifecycle/      # Sole deterministic lifecycle authority
├── candystore/     # Append-only audit history and read projections
├── holocene/       # Dashboard, renderer, and high-level actions
├── pjangler/       # Project identity, bootstrap, and bindings
├── flume/          # Agent hierarchy, role assignment, and company org chart
├── hermes-fleet/   # System-wide registry of project-scoped PM agents
├── plane/          # Open Source ticketing platform and kanban task management
├── n8n/            # Open Source node-based automation platform
├── hindsight/      # Memory framework for agents
├── voxxy/          # Multi-engine TTS service
├── skillex/        # Custom skill framework for agents
├── momo/           # Policy chooser/executor; never lifecycle truth authority
├── 33god-platform/ # Root-owned pins, topology, acceptance, and drift
├── bmad/           # Open Source project planning and documentation framework.
```

## Current Working Document

Use ./PRD.md to track state right now, until we initialize BMAD
