# Hookd — Agent Guide

Claude Code hook event pipeline. Enriches tool mutation events with repo context and publishes to Bloodbank.

## Tech Stack

- **Language:** Rust (edition 2021)
- **Runtime:** Tokio (async)
- **Messaging:** Lapin (RabbitMQ/AMQP client)
- **Serialization:** Serde + serde_json
- **Tracing:** tracing + tracing-subscriber (JSON + env-filter)
- **Ingestion:** Unix socket (hookd-emit shell script)

## Architecture

```
hookd-emit → Unix Socket → hookd (Rust) → Bloodbank (RabbitMQ) → consumers
```

## Commands

| Task | Command |
|------|---------|
| Build | `cargo build` |
| Run | `cargo run` |
| Test | `cargo test` |
| Lint | `cargo clippy` |
| Full CI | `cargo build && cargo test && cargo clippy` |

## Key Files

- `src/main.rs` — Daemon entrypoint, Unix socket listener
- `src/envelope.rs` — Event envelope construction (wraps hook payloads)
- `src/enrichment.rs` — Repo context enrichment (git metadata, workspace info)
- `src/publisher.rs` — Bloodbank/RabbitMQ publishing via Lapin
- `src/config.rs` — Configuration structs
- `bin/hookd-emit` — Fire-and-forget shell emitter (invoked by Claude Code hooks)

## Conventions

- Tokio async runtime for all I/O
- Events follow Bloodbank envelope format
- Enrichment is idempotent — same hook input produces same enriched output
- Structured JSON logging via tracing-subscriber

## Anti-Patterns

- Never block the Unix socket listener — all processing must be async
- Never hardcode RabbitMQ credentials — use env vars
- Never skip envelope validation before publishing to Bloodbank

## Related

- **Bloodbank**: Event backbone at `../bloodbank/`
- **hookd-bridge**: Separate Python HTTP→Bloodbank bridge in `compose.yml` (not this component)
- **Holyfields**: Schema registry for event contract validation
