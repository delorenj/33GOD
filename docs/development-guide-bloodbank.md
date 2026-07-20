# Bloodbank Development Guide

## Scope

Bloodbank owns canonical event schemas, subject/type validation, agent event
publication, NATS JetStream topology, and Dapr transport. Lifecycle is a
separate repository and the sole deterministic lifecycle authority. Bloodbank
does not host, reconcile, or write lifecycle state.

## Prerequisites

- Docker Engine with Compose plugin
- mise
- Python 3.11+
- Optional NATS and Dapr CLIs for focused transport operations

## Core commands

```bash
cd bloodbank
mise run doctor
mise run validate:schemas
mise run hooks:check
mise run smoketest:schemas
mise run repo-health
```

Inspect `bloodbank/mise.toml` before running service tasks. Use only the focused
NATS/Dapr profile needed for the check; root acceptance uses the normalized
projection in `33god-platform/compose.yaml`.

## Contract change workflow

1. Update the canonical event name and schema sources.
2. Run schema syntax, contract consistency, subject/type equality, and hook
   synchronization checks.
3. Add a negative test for malformed subject or envelope semantics.
4. Evaluate Lifecycle publication/consumption, Candystore projection, Momo
   evidence, Holocene commands, and PJangler-generated contract impact.
5. Record cross-component change evidence and run the root drift gate.

## Transport boundary

Bloodbank may validate and transport Lifecycle commands/events, but it may not
derive legal work, reconcile state, grant capabilities, or publish a competing
authoritative result. Current development inputs are `schemas/`,
`docs/event-naming.md`, `compose/`, and `services/agent-hooks/`.

## Operational cautions

Local NATS remains a development topology without production auth/TLS or
multi-tenant boundaries. Do not start Bloodbank's legacy Candystore profile
alongside the root-owned Candystore projection.
