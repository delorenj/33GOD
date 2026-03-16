# Hookd — Agent Guide

Daemon that enriches Claude Code hook events with repository context and publishes them to Bloodbank.

## Tech Stack

- **Runtime:** Rust (tokio async runtime) + Bun/TypeScript build tooling
- **Messaging:** RabbitMQ via lapin
- **Serialization:** serde + serde_json
- **Logging:** tracing + tracing-subscriber (structured JSON)
- **Rust Edition:** 2021

## Commands (mise)

| Task | Command |
|------|---------|
| Build | `mise run build` (bun install + lint + build) |
| Test | `mise run test` (bun test) |
| Lint | `mise run lint` |
| Dev | `mise run dev` |
| Start | `mise run start` (daemon mode) |

## Architecture

- Intercepts Claude Code hook events (pre-edit, post-edit, pre-command, etc.)
- Enriches events with git context (repo, branch, file paths)
- Publishes structured events to Bloodbank RabbitMQ exchange
- Local component (NOT a git submodule)

## Conventions

- Structured logging with tracing (JSON format)
- UUID v4 for event correlation
- Fail-fast on RabbitMQ connection loss

## Anti-Patterns

- Never block the tokio runtime with synchronous calls
- Never swallow connection errors silently
- Never publish events without repo context enrichment
