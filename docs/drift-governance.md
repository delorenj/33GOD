# 33GOD Drift Governance

## Ownership

| Area | Owner |
|---|---|
| Event names, schemas, subjects, NATS/Dapr topology | Bloodbank |
| Lifecycle spec/state/reconcile/frontier/obligations/capability validation and all state-changing writes | Lifecycle |
| Event persistence, ingest, query/read models, audit UI | Candystore |
| Fleet/lifecycle rendering, host controls, high-level command UI | Holocene |
| Registry, project/bootstrap identity, parity, templates, MCP/CLI | PJangler |
| Business prioritization, delegation, review, legal-work selection | Momo |
| Normalized Compose projection, relationships, drift register, release gate | 33GOD root platform |

Root owns a normalized projection; it does not take ownership of component
implementation. Live manifests/code/tests outrank prose. Historical plans are
intent evidence, not current guarantees.

## Required gates

For a component or root change affecting schemas, hooks, public contracts,
templates, ports, networks, secrets, storage, profiles, or runtime boundaries:

1. Run focused component checks.
2. Run platform manifest and backfill validation.
3. Run the candidate semantic validator with an explicit `--source-root`.
4. Run `GOD_SOURCE_ROOT=<populated-root> mise run docs:drift`; this retains the
   prior parity checks and invokes the same candidate validator.
5. Update both the machine change log and pipeline changelog.
6. Update root integration/deployment documentation and obtain owner review.

All Compose renders in this gate are read-only and use
`--no-env-resolution`. A successful render or semantic validation proves
candidate structure, not live health or migration completion. Static validation
may read an authoritative dirty component checkout without modifying it;
deployment cutover requires clean component sources pinned to the candidate's
gitlinks.

The semantic validator covers the integrated local topology, including the
exact Lifecycle digest/no-build rule, dedicated authority storage, fail-closed
migrate/bootstrap/serve ordering, service health/dependencies, and profile
semantics. The isolated live gate covers the client seams and seven failure
invariants.

## Semantic projection contract

The validator guards:

- exact service sets for default, `tools`, `full`, and `cloud`;
- one and only one Candystore PostgreSQL/app/daprd deployment;
- no Bloodbank legacy Candystore or Compose-owned Holocene API;
- fixed dependency/readiness order and host API preflight;
- exact environment-selected ports and the absence of PJangler listeners;
- exact Candystore subscription variables, daprd component/placement command,
  and canonical Bloodbank event path;
- four exact external networks, exact service memberships, and six exact
  external volumes;
- the exact immutable Lifecycle image, absence of a build key, dedicated
  secret/storage, and private database network;
- exact Holocene main Host/auth/proxy target and committed HQ routing labels;
- unresolved Holocene env-file references with no component values in renders;
- component-source mounts resolved from the explicit source root;
- zero-replica, run-only PJangler CLI and stdio MCP behavior; and
- an explicit unsupported cloud gate while local binds remain.

## Current explicit drift

| ID | Severity | Owner | Contradiction | Gate impact |
|---|---:|---|---|---|
| CANDY-DUR-01 | Critical | Candystore | Dead-letter failure can still receive `DROP` acknowledgement | Blocks “never lose an event” claim |
| HOLO-SEC-01 | Critical | Holocene | Host-control API binds all interfaces without app auth/authz | Blocks untrusted-network/cloud use |
| HOLO-SECRET-01 | High | Holocene | Tracked credential history requires rotation/remediation | Blocks treating the integration as safe |
| PJ-REPRO-01 | Critical | PJangler | Template gitlinks plus moving revision resolution are unreproducible | Blocks reproducible provisioning claim |
| PJ-SAFE-01 | High | PJangler | Some MCP operations mutate by default; cancellation/result propagation is unreliable | Blocks broad safe-default claim |
| ROOT-CLOUD-01 | Critical | Root/platform | Candidate retains local binds, external local networks, host systemd authority, local credentials, and single-host storage | Blocks cloud lifecycle use; render-only profile must remain explicitly unsupported |

`docker compose --profile cloud up` is specifically prohibited: Compose also
selects every unprofiled local service, so stateful services may start and mutate
before the rejection container exits. Cloud has no lifecycle task and is only a
configuration/render inspection model.

## Resolved drift

| ID | Resolved | Evidence |
|---|---|---|
| ROOT-COMPOSE-01 | 2026-07-15 | `validate-compose.py` renders and semantically validates default, `tools`, `full`, and `cloud`; focused tests include adversarial legacy services and missing-source failure |
| BB-CONTRACT-01 | 2026-07-15 | Runtime contract invokes exact subject matching; Bloodbank naming gate passes |
| BB-RUN-01 | 2026-07-15 | Heartbeat profile renders and passed its focused smoke evidence |
| BB-PJ-01 | 2026-07-15 | PJangler templates use fixed subjects and envelope-data routing |
| CANDY-HOLO-01 | 2026-07-15 | Holocene fallback uses the standalone Candystore loopback boundary |
| PJ-IDENTITY-01 | 2026-07-15 | Platform registry resolves monorepo PJangler and uses npm |
| LIFE-BOUNDARY-01 | 2026-07-18 | Standalone Lifecycle is the only operational writer; Momo and Holocene use bounded Bloodbank command clients |
| LIFE-OUTBOX-01 | 2026-07-18 | Exact immutable image passed NATS outage/recovery with committed state, ordered outbox, zero pending rows, and eventual publication |
| LIFE-SCHEMA-01 | 2026-07-18 | Bloodbank validation passed at `48031ee…`; exact versioned grants, occurrence-bound completion evidence, client command envelopes, snapshot v3, and Lifecycle replies were exercised |
| LIFE-HOLO-BROWSER-01 | 2026-07-19 | Holocene `80d9cc8…` owns a real Chromium confirmation/click/POST/202/render proof; the root harness independently verifies its receipt and cannot author the successful action |

Resolving `ROOT-COMPOSE-01` means an integrated local stack exists.
`ROOT-CLOUD-01` remains a separate hosted-design concern.

## Runtime ownership policy

The root Compose project is the **process/topology owner** of Bloodbank,
Lifecycle, Candystore, and Holocene web. This does not grant root
project-lifecycle semantic authority.
Bloodbank's legacy Candystore services remain forbidden.
The six volumes and four external networks retain operator-selected identities
across root-stack restarts.

Lifecycle is the sole project-lifecycle writer.
Bloodbank transports its contracts, Candystore is append-only audit/projection
only, PJangler supplies identity, Momo chooses and executes legal work while
publishing evidence, and Holocene only renders and invokes high-level actions
only. Direct provider/database writes from those clients are drift.

## Acceptance policy

Warnings are incomplete evidence without a demonstrated contradiction.
Failures are missing required artifacts or executable conflicts. An accepted
failure needs an owner, expiry, and release-scope exception; documentation alone
does not repair implementation. Cloud-blocked drift cannot be waived into a
lifecycle command.
