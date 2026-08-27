# 33GOD Integration Architecture

## Authority model

Root documentation owns component relationships, the normalized Compose
projection, and deployment gates. Component repositories own internal APIs and
implementation. Authority order is executable manifests/runtime configuration,
code, tests/validation, root integration docs, component docs, then historical
plans.

The canonical end-to-end facts/intent map is [33GOD Event and Command
Journey](./event-journey.md). Its editable Excalidraw source contains the
platform context, focused Plane ingress, and both message traces.

## Current live topology

Verified on 2026-08-27 UTC, Compose project `33god-platform` owns the running
Bloodbank NATS, Candystore app/sidecar/PostgreSQL, event toaster, and Holocene
web containers. The host owns the Holocene API and Hermes Bloodbank gateway;
n8n owns the public Plane provenance boundary.

```text
Plane --signed raw HTTPS--> n8n Plane → Bloodbank --fact--> BLOODBANK_EVENTS
                                                             |
                                                             +--> Candystore
                                                             |       |
                                                             |       +--> Holocene
                                                             +--> Event toaster

Momo / UI / CLI --intent--> BLOODBANK_COMMANDS --> Hermes gateway
                                                     | registry-gated dispatch
                                                     +--> Hermes target
                                                     +--> lifecycle facts --> EVENTS
```

The active Plane workflow is `iMw484J1ZCqKME2C`; both `33god` and
`automaticai` are Plane workspace tenants on this same personal infrastructure.
The `automaticai` slug is routing identity, not a second service or ownership
boundary. Port `8477` is retired.

## Root composition model

```text
Bloodbank NATS --healthy--> NATS init --completed--------------------+
       |                                                              |
       +--> Dapr placement                                            |
                                                                      v
Candystore PostgreSQL --healthy--> app --ready--> one Candystore daprd
                                             durable candystore-events
                         |
                         +--> host Holocene API reads 127.0.0.1:8683
                                      |
                                      v preflight /health on :4000
                              Holocene web on proxy:3001

PJangler CLI / stdio MCP: tools/full, zero replicas, explicit run only
Cloud: render-only unsupported local-bind model
```

The local core of this model is deployed. The `cloud` model remains render-only
and unsupported, and fixed container names still forbid starting a second
component-managed copy beside the root-owned services.

## Contract matrix

| Concern | Owner | Root projection contract |
|---|---|---|
| NATS streams and Dapr transport | Bloodbank | Tracked initializer is read-only mounted; NATS/init/placement are default |
| Durable event history | Candystore | One PostgreSQL/app/daprd; durable component is Candystore-owned |
| Mission control | Holocene | Web is default; privileged API remains host systemd and is preflighted |
| Project tooling | PJangler | CLI and MCP are run-only; MCP is stdio; no ports/health/daemon |
| Networks | Bloodbank/Candystore/host proxy owners | Exact external names are preserved |
| Persistent data | Component/runtime owners | Five adopted volumes are external; legacy volumes remain detached |
| Cross-component projection | 33god-platform | Root normalizes names/dependencies without editing component sources |

## Ports and reachability

The validator preserves NATS `4222`/`8222`, Dapr placement `50005`, loopback
Candystore PostgreSQL `5434`, loopback Candystore app `8683`, and loopback
Candystore daprd `3504`. Holocene web exposes container-only `3001` to Traefik.
Compose publishes no `4000`; the existing host API owns it. PJangler publishes
no ports.

## Failure and trust boundaries

- `nats-init` must finish before the durable Candystore sidecar starts.
- Candystore readiness includes PostgreSQL; app liveness alone is insufficient.
- Plane ingress must verify HMAC over the exact raw request body, select a
  1Password secret reference by `webhook_id`, and resolve a project route before
  publication. Unknown identity, bad signature, or missing route means no event.
- A healthy Hermes gateway is not proof of dispatch eligibility. The fleet
  registry is a separate default-deny gate; the current snapshot has no enabled
  Bloodbank routes.
- The host API preflight establishes reachability, not application auth safety.
- Holocene history remains a direct HTTP read-side exception to Bloodbank.
- PJangler recipes requiring host files, systemd, or provider credentials remain
  host-authority operations even though narrow container definitions exist.
- A successful cloud render is evidence of honest unsupported assumptions, not
  cloud readiness.

## Data and network safety

External networks are `bloodbank-network`, `candystore-internal`, and `proxy`.
Adopted volumes are `bloodbank_bloodbank-nats-data`, `candystore_pgdata`, and
the three `holocene_*` dependency/build volumes listed in the deployment guide.
The projection forbids the Bloodbank legacy Candystore services. Detached
legacy volumes remain preserved and unmounted.

## Change discipline

Any event, template, port, network, secret-source, storage, service-cardinality,
profile, or host-boundary change requires a machine change record, pipeline
changelog entry, relevant semantic-validator update, root documentation update,
and owner review. A pipeline journey change additionally requires live rejection
and durable-delivery evidence. See [Drift Governance](./drift-governance.md) and
[Event and Command Journey](./event-journey.md).
