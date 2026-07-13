# 33GOD Integration Architecture

## Authority Model

Root documentation owns component relationships, shared contract interpretation, and deployment gates. Component repositories own internal APIs and implementation. When sources disagree, use this order:

1. Live executable manifests and runtime configuration.
2. Live code.
3. Tests and validation output.
4. Root integration documentation.
5. Current component documentation.
6. Historical plans and generated artifacts.

Contradictions are drift records. They are not resolved by choosing whichever prose is most convenient.

## System Flow

```text
PJangler templates/registry
        │ generated runtime + local projections
        ▼
Hermes/agent producers ──CloudEvents/NATS──► Bloodbank JetStream
                                                │ Dapr durable subscription
                                                ▼
                                         Candystore/Postgres
                                                │ HTTP read side
                                                ▼
                                         Holocene mission control

Direct/transitional paths:
agent-hook health ──Redis──────────────────────► Holocene
Holocene ──host files/systemd/Traefik/bgls────► local machine controls
PJangler ──.project.json/registry─────────────► generated projects and Holocene projections
```

## Contract Matrix

| Concern | Canonical owner | Current consumer behavior | Drift rule |
|---|---|---|---|
| Event type and subject | Bloodbank `docs/event-naming.md` and `schemas/` | Candystore accepts a weaker subset; PJangler generators violate routing in places | Bloodbank contract wins; record producer/consumer mismatch |
| Durable event history | Candystore PostgreSQL schema and ingest code | Holocene reads it over HTTP | Direct read-side HTTP is an explicit CQRS exception |
| Project identity | PJangler central registry plus `.project.json` projection | Holocene and generated agents consume projections | Registry is catalog/bootstrap authority; local manifest is runtime projection |
| Fleet control | Holocene API and host integration | Browser/API callers mutate host services | Must be treated as a privileged local control boundary |
| Platform coordination | `33god-platform/` registry/change/backfill manifests | Root scripts validate declared paths and records | Platform scaffold does not imply runtime orchestration |

## Bloodbank to Candystore

Candystore’s Dapr sidecar subscribes to `bloodbank.evt.v1.>` on `BLOODBANK_EVENTS` with durable `candystore-events` and queue group `candystore`. The canonical deployment is Candystore’s standalone Compose. Bloodbank’s embedded `candystore` profile uses the same durable/queue but a separate database; running both splits the audit trail and is prohibited.

Delivery outcomes are `SUCCESS` for inserts/duplicates, `DROP` for permanently invalid input, and `RETRY` for transient exceptions. A dead-letter write failure is currently ignored before `DROP`, so the system does not guarantee preservation of every poison message.

## Candystore to Holocene

Holocene reads history directly from Candystore. This is an approved architectural description of current behavior, not transport through Bloodbank. The current default `http://candystore:8080` is wrong for the live host-systemd API; standalone Candystore exposes `127.0.0.1:8683` and listens at container port `3001`. Holocene swallows failures into empty history, so the connection needs explicit configuration and observable failure before it can be called reliable.

## PJangler to Bloodbank

PJangler-generated Hermes runtimes contain a core-NATS consumer and local envelope construction. Current subscriptions embed repository or agent identifiers in subject tokens, conflicting with Bloodbank’s fixed six-token subject. Received commands become inbox JSON files rather than Hermes execution turns. Sentinel output is local JSONL, not broker publication. This is transitional integration, not durable command delivery.

## Bloodbank to Holocene

Holocene’s package-level Bloodbank client is a no-op stub. Live hook-health data reaches Holocene through Redis, and Holocene duplicates hook-type mappings. Its parser does not understand the canonical `publish.py --client … --hook …` option order. Root docs therefore classify the path as a bypass/projection pending a real transport client.

## Failure Boundaries

- NATS and Dapr outages prevent event delivery but should not be confused with Candystore HTTP health.
- Candystore liveness does not imply database readiness because its container healthcheck uses `/healthz` rather than `/readyz`.
- Holocene history failures appear as empty data unless separately observed.
- PJangler recipes execute with host-user authority; some MCP operations mutate by default.
- The product Compose target only validates a tools container and starts no component services.

## Change Discipline

Any change to event schemas/subjects, hook payloads, templates, ports/networks/secrets, or cross-part deployment behavior requires a platform machine change record, human changelog entry, relevant drift check update, and component-owner review. See [Drift Governance](./drift-governance.md).
