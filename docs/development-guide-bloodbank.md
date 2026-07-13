# Bloodbank Development Guide

## Prerequisites

- Docker Engine with Compose plugin
- mise
- Python 3.11 for repository checks; Python 3.12+ for lifecycle-controller development
- `uv` for lifecycle dependencies
- Optional NATS/Dapr CLIs for integration operations

## Safe Setup

Inspect `bloodbank/mise.toml` before entering a mise-managed shell. Component tasks are the supported interface; avoid starting profiles you do not need.

## Core Commands

```bash
cd bloodbank
mise run doctor
mise run validate:schemas
mise run hooks:check
mise run smoketest:schemas
mise run repo-health
```

Runtime commands include `mise run up`, `up:all`, `up:candystore`, `down`, and focused NATS/Dapr smoke tests. `down` removes volumes. The heartbeat profile is currently broken because its recorder build context is missing.

## Lifecycle Controller

```bash
cd bloodbank/services/lifecycle-controller
mise x -- uv run ruff check .
mise x -- uv run pytest -q
PYTHONPATH=src mise x -- uv run python scripts/dogfood_drumjangler.py
```

The dogfood script demonstrates database reconciliation and staged outbox events; it does not demonstrate broker publication.

## Contract Change Workflow

1. Update event naming/schema sources.
2. Run schema syntax, schema-contract consistency, naming tests, and hook synchronization.
3. Add a negative test proving type/subject token equality.
4. Evaluate Candystore ingest/query impact, Holocene type mapping, and PJangler-generated contracts.
5. Add platform change evidence and run root drift parity.

## Testing Notes

Schema and naming checks are stronger than current CI. Run them explicitly. Docker smoke tests create containers, networks, and volumes and should be used only in an authorized integration environment.

## Operational Cautions

The local topology lacks NATS auth/TLS, broker capacity limits, a broker DLQ, complete tracing, and guaranteed JetStream acknowledgement for hook publication. Never use embedded and standalone Candystore simultaneously.
