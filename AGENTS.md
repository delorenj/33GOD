# 33GOD — Monorepo Knowledge Base

**Generated:** 2026-05-07
**Branch:** main

## OVERVIEW

Event-driven agentic development pipeline. Multi-agent teams coordinate asynchronously via Bloodbank (NATS/dapr). Candystore persists everything; Holocene as control plane and dashboard Everything is an event.

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
├── momo/           # Just a skill, but a core component of the pipeline. Defines the ticket lifecycle
├── bmad/           # Open Source project planning and documentation framework.





```

## WHERE TO LOOK

| Task                       | Location                          | Notes                                       |
| -------------------------- | --------------------------------- | ------------------------------------------- |
| Publish/subscribe events   | `bloodbank/`                      | RabbitMQ via aio-pika, topic exchange       |
| Define event schemas       | `holyfields/schemas/`             | JSON Schema source of truth                 |
| Use typed events (Python)  | `holyfields/packages/python/`     | Generated Pydantic models                   |
| Use typed events (TS)      | `holyfields/packages/typescript/` | Generated Zod schemas                       |
| Query historical events    | `candystore/`                     | REST API + PostgreSQL                       |
| Visualize event flows      | `candybar/`                       | Real-time WebSocket dashboard               |
| Claude Code hooks → events | `hookd/`                          | Unix socket → RabbitMQ bridge               |
| Deploy full stack          | `compose.yml`                     | `docker compose up -d`                      |
| Agent definitions          | `.agents/team/`                   | Agent configs for multi-agent orchestration |

## CONVENTIONS

- **Event naming**: `{domain}.{entity}.{action}` (e.g. `transcription.voice.completed`)
- **Async-first**: All I/O in Python services uses async/await
- **Schema-driven**: Holyfields JSON Schema is the single source of truth for event contracts
- **Never hand-edit generated code** in `holyfields/packages/*/generated`
- **Mise for tooling**: All sub-projects use `mise.toml` for task definitions
- **Docker Compose** at root for full-stack deployment
- **Bloodbank** is the only inter-service communication channel — never direct calls
- **ruff** for Python linting, **eslint + clippy** for Candybar

## ANTI-PATTERNS (THIS PROJECT)

- Never bypass Bloodbank for direct service-to-service calls
- Never hand-edit generated Pydantic/Zod artifacts in Holyfields
- Never skip schema validation — `mise run ci` before PR
- Never use synchronous I/O in event handlers
- Never lose events — persist before acknowledging
- Never skip migrations for schema changes in Candystore

## UNIQUE STYLES

- Linked AGENTS.md: Root `mise.toml` symlinks agent files via `link-agentfiles.sh` hook
- Monorepo with Docker Compose at root — sub-projects build from repo root context
- Each sub-project has its own `AGENTS.md` — read it before working in that directory

## COMMANDS

```bash
# Full stack deployment
docker compose up -d                     # Start everything
docker compose ps                        # Service status

# Bloodbank
(cd bloodbank && mise run deploy)        # Build + deploy
(cd bloodbank && mise run test)          # Run tests
(cd bloodbank && mise run lint)          # Lint

# Holyfields — schema workflow
(cd holyfields && mise run validate:schemas)   # Validate JSON Schemas
(cd holyfields && mise run generate:all)       # Generate Python + TS bindings
(cd holyfields && mise run check:drift)        # Check generated code matches schemas
(cd holyfields && mise run ci)                 # Full CI: validate + generate + test + typecheck

# Candystore
(cd candystore && mise run start)              # Start consumer + API
(cd candystore && uv run pytest)               # Run tests

# Candybar
(cd candybar && npm run dev)                   # Tauri dev mode
(cd candybar && npm run lint)                  # ESLint
(cd candybar && npm run clippy)                # Rust clippy

# Hookd
(cd hookd && cargo run)                        # Start daemon
```

## NOTES

- Bloodbank v3 pivot planned: Dapr + NATS JetStream + CloudEvents (see `bloodbank/v3-implementation-plan.md`). Current v2 is RabbitMQ.
- `hookd/` (Rust daemon) is separate from `hookd-bridge` (Python HTTP→RabbitMQ bridge in Docker Compose).
- Holyfields schemas are mounted read-only into Bloodbank container for runtime validation.
- RabbitMQ management UI at `http://localhost:15673` when stack is running.
