# 33GOD Integration Architecture

## Authority model

Root documentation owns component relationships, the normalized Compose
projection, and deployment gates. Component repositories own internal APIs and
implementation. Authority order is executable manifests/runtime configuration,
code, tests/validation, root integration docs, component docs, then historical
plans.

For project lifecycle semantics the approved authority is the planned headless
Lifecycle component. Root Compose process ownership, Bloodbank transport,
Candystore history, Momo judgment, Holocene rendering, and PJangler identity are
separate concerns.

## Validated target

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

Lifecycle: approved extraction target, absent from this deployed topology
```

The candidate is statically validated, not deployed. Fixed container names mean
the target cannot coexist with current component-managed containers during a
cutover.

The later lifecycle vertical slice is a separate target interaction:

```text
PJangler project identity ---> Lifecycle spec/binding
observations + evidence -----> deterministic reconcile
                               state/frontier/obligations/grants
                                           |
                          canonical Bloodbank commands/events
                                           |
                                  Candystore history/read models
                                   /                         \
                     Momo selects legal work       Holocene renders/commands
                                   \                         /
                                    intent ---> Lifecycle validates
```

## Contract matrix

| Concern | Owner | Root projection contract |
|---|---|---|
| NATS streams and Dapr transport | Bloodbank | Tracked initializer is read-only mounted; NATS/init/placement are default |
| Durable event history | Candystore | One PostgreSQL/app/daprd; durable component is Candystore-owned |
| Mission control | Holocene | Web is default; privileged API remains host systemd and is preflighted |
| Project tooling | PJangler | CLI and MCP are run-only; MCP is stdio; no ports/health/daemon |
| Project lifecycle truth (planned) | Lifecycle | No current service; future single writer for spec/state/reconcile/frontier/obligations/capabilities |
| Business process management | Momo | Read frontier, choose legal work, delegate/review, submit intent; no lifecycle writes |
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
- The host API preflight establishes reachability, not application auth safety.
- Holocene history remains a direct HTTP read-side exception to Bloodbank.
- Holocene lifecycle UI must render authoritative version/provenance/freshness
  and submit commands; it cannot compute transitions or write provider state.
- Momo's current direct `tp`/Trello transitions are legacy behavior until the
  lifecycle command seam exists. They are not target lifecycle truth.
- PJangler recipes requiring host files, systemd, or provider credentials remain
  host-authority operations even though narrow container definitions exist.
- A successful cloud render is evidence of honest unsupported assumptions, not
  cloud readiness.

## Lifecycle extraction boundary

The tested Bloodbank controller is the extraction embryo. Its pure evaluator,
leased queue, transactional state/history/outbox persistence, and 21 passing
focused tests are current evidence. The default publisher is unconfigured,
`blocker.detected` lacks a schema, and initial `status.updated` staging can
conflict with the registered schema. No standalone repository/service or root
Compose entry exists.

Extraction must preserve repository provenance and current database history.
The target adds a versioned spec, legal frontier, obligations, capability
validation, idempotent commands, and optimistic state-version checks. Exactly
one writer is a cutover gate.

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
and owner review. See [Drift Governance](./drift-governance.md).
