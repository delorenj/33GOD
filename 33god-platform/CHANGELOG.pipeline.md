# 33GOD Pipeline Changelog

This changelog records changes that affect more than one 33GOD component. It is
fed by `changes/*.jsonl`; update both when a contract shifts.

## 2026-07-20

### Root topology and provenance enforcement

- Made the selected `GOD_SOURCE_ROOT` atomic: every in-tree descendant remains
  beneath it, missing repositories/leaves fail closed, and external Skillex or
  HeyMa paths use the independent `GOD_EXTERNAL_ROOT` policy.
- Separated the exact six-component Lifecycle acceptance slice from the exact
  twelve-component product registry in executable validation and current docs.
- Reconciled every root gitlink with a credential-free HTTPS mapping, preserved
  the exact planned Toad and Hermes Template pins, and made root inventory
  validation require every checkout's own top-level, exact index `HEAD`, and
  normalized origin identity, including gitlinks outside the component registry.
- Expanded root drift fixtures and live scanning to cover semantic provider
  completion surfaces, backups, mirrors, symlinks, adapters/runners,
  operational nested gitlinks, Momo copy/manifest claims, Holocene branding,
  retired Bloodbank guidance, stale architecture inputs, and Lifecycle
  release-promotion variants.

## 2026-07-19

### Lifecycle authority parity

- Published and pinned Bloodbank `aacd885…`, Candystore `3c00080…`, Momo
  `8eeff1c…`, Holocene `2beee67…`, PJangler `13be237…`, and PJangler's
  CommonProject template `5dce335…`.
- Removed every registered Ticket Lifecycle Client Workflow from Bloodbank,
  Candystore, Holocene, PJangler, and CommonProject while retaining Momo's one
  canonical source/mirror registration.
- Defined Bloodbank as schema/transport, Candystore as audit/read projection,
  Momo as legal-work chooser/executor, PJangler as identity/bootstrap/bindings,
  Holocene as dashboard/renderer, and root as exact-pin/topology/acceptance/drift
  owner. Lifecycle remains the only deterministic truth, reconcile, frontier,
  obligation, capability-validity, and write authority.
- Extended root drift and registry tests to reject competing workflow surfaces,
  stale ownership language, stale Bloodbank controller inventory, and retired
  deployment-process wording.

### Real Holocene browser action proof

- Published and pinned Holocene `80d9cc8…` with semantic Lifecycle DOM
  identity, confirmation-bound controls, and a reusable Chromium proof that
  records the actual click, browser POST body, HTTP 202 response body, and
  explicitly non-authoritative broker receipt.
- Replaced the live harness's successful direct API submission and passive
  screenshots with the Holocene-owned browser proof, independent
  authority/Candystore verification, rendered state/version/causality/verdict
  assertions, and desktop/mobile image receipts.
- Added focused component/contract tests and root anti-synthetic gates that
  reject mocked routes, screenshot-only evidence, missing confirmation or
  response capture, harness-authored success POSTs, and missing rendered
  authority outcomes.
- Kept Lifecycle as the sole truth and write authority; Holocene only renders
  the Candystore projection and invokes a high-level Bloodbank command.

### Real Momo obligation execution

- Published and pinned Momo `4c59f10…` with a named durable JetStream actor for
  exact `bmad-code-review@6.10.2` obligation invocations.
- Replaced harness-authored successful evidence with a real bounded review
  report, exact byte SHA-256, completion PubAck before invocation ACK, and a
  machine receipt linking broker delivery, invocation, skill resource,
  artifact, and completion identities.
- Bound completion identity and event time to the immutable invocation, used the
  exact completion CloudEvent ID as `Nats-Msg-Id`, rejected a duplicate PubAck
  in the clean proof, and retained the delivery unacked with no receipt when
  `ack_sync` confirmation fails after PubAck.
- Kept Lifecycle as the sole lifecycle truth authority; Momo chooses and
  executes legal work and publishes evidence only.

## 2026-07-18

### Lifecycle authority vertical slice

- Added the exact-digest Lifecycle authority topology with dedicated
  PostgreSQL, secret, volume, private network, one-shot migration,
  deterministic bootstrap, serve readiness, and no Compose build path.
- Published and pinned Bloodbank `48031ee…` as the canonical schema/NATS/Dapr
  authority, adding snapshot v3 occurrence/capability identity and exact
  completion-evidence v2 while retaining the tracked JetStream initializer.
- Published and pinned Lifecycle `797fcf4…`, Candystore `b3b4d82…`, Momo
  `4c41a99…`, and Holocene `e8cecb9…` for occurrence-isolated obligation truth,
  authority-validated projection, real causal identity, and complete
  authoritative client semantics.
- Added semantic/adversarial tests and the isolated live seven-invariant
  failure matrix with pre-start durable replay, pending-obligation rejection,
  canonical active-occurrence satisfaction, authority-spoof rejection,
  versioned grants, conflicting-duplicate integrity, and a real single-writer
  outage proof: canonical JetStream ingress, deployed-consumer ack-pending and
  PostgreSQL row blocking, atomic commit while NATS is down, durable idempotent
  redelivery, ordered outbox drain, unique Docker resources, and exact cleanup.
- Preserved the six-way semantic ownership boundary; cloud remains render-only
  and unsupported.

## 2026-07-15

### Root Compose Cutover

- Published Holocene `edaf31b`, pinned all four component gitlinks, and added
  formal Holocene and PJangler submodule mappings at the monorepo root.
- Replaced the three component-owned Compose lifecycles with the root project.
  Bloodbank core, one Candystore triplet, and Holocene web are live under
  `33god-platform`; PJangler remains clean, pinned, and run-only.
- Adopted the Holocene `/hq` plus `/_next/static` routing contract and removed
  the excluded legacy Bloodbank PostgreSQL container.

### Integrated Compose Target

- Replaced the readiness scaffold with a root-owned normalized projection for
  Bloodbank NATS/init/placement, one standalone Candystore triplet, Holocene
  host-API preflight and web, and opt-in run-only PJangler CLI/MCP tools.
- Preserved ports, three external network identities, and five adopted external
  volume identities; excluded Bloodbank's legacy Candystore services and kept
  detached legacy volumes outside the target.
- Added a semantic validator and focused tests for default, `tools`, `full`,
  and render-only unsupported `cloud` models.
- Extended the documentation drift gate to validate the candidate against an
  explicit source root. Cloud deployment remains blocked.
- Hardened every checked-in render task with `--no-env-resolution`, preserved
  caller-selected port overrides for validation, and suppressed captured
  Compose errors that could otherwise disclose component env-file values.
- Expanded semantic/adversarial gates for the canonical Candystore subscription
  and daprd placement path, exact Traefik Host/auth/proxy behavior, and exact
  per-service network isolation. The committed Holocene `/hq` router and its
  `/_next/static` asset path are the pinned baseline.

### Registry Truth Reconciliation

- Corrected PJangler, Hermes Fleet, and HeyMa paths to their live checkouts and
  restored PJangler's canonical npm health command.
- Removed Holyfields and Hookd from the active component list because neither
  repository is present in the current platform checkout. Their manifest files
  remain as historical definitions until those components are deliberately
  restored.
- Re-established the platform manifest validator as a live-truth gate.

## 2026-07-10

### Component Registry Repair

- Restored the Candybar, Holyfields, and Hookd component manifests referenced by
  `components.yaml`.
- Removed the incomplete Flume manifest from the active registry until the repo
  path and platform contract are real.
- Re-established `platform:validate` and `platform:components` as usable
  control-plane gates for the next director handoff.

## 2026-07-08

### Platform Control Plane Bootstrap

- Added the `33god-platform` control-plane scaffold.
- Indexed the current component constellation: Bloodbank, Candystore, Holocene,
  PJangler, Hermes Fleet, Skillex, Hindsight, Pipeline MCP Hub, Candybar, HeyMa,
  Holyfields, and Hookd.
- Established the first machine-readable change entry and read-only backfill
  checks for canonical Hindsight/Bloodbank hook migrations.
- Added a unified `33god-hub` skill entrypoint so agents start from one product
  map before drilling into component-specific skills.

Backfill checks introduced:

- `hindsight-canonical-hooks-v1`
- `bloodbank-canonical-agent-publisher-v1`
- `hermes-inherited-profile-config-v1`
- `skillex-33god-hub-v1`
