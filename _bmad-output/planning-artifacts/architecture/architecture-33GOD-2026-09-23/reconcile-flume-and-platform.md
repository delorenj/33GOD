# Architecture Input Reconciliation — Flume and Platform Contracts

## Sources

- `flume/contracts/handbook.yaml`
- `flume/AGENTS.md`
- `README.md`
- `docs/integration-architecture.md`
- `33god-platform/components.yaml`

## Reality ratified by the spine

- Flume's handbook is a declared authority and projection contract with schema
  version 5 and contract version 1.4.0.
- Flume owns workforce identity and managed workforce state; PJangler owns
  project identity and board binding; Hermes owns runtime/profile execution.
- Bloodbank and Candystore remain the event transport and durable-history path;
  Holocene is a read-side projection and operator surface.
- The root platform owns the Compose projection, while the host API remains
  `holocene-api.service`.

## Gaps or migration pressure

1. The handbook declares authorities and projections but does not yet provide
   the DeloHQ-specific read transport; AD-5 leaves that transport open while
   preventing Holocene from making legacy presentation metadata authoritative.
2. The platform contract establishes deployment ownership but does not define
   DeloHQ view-model schemas; AD-3, AD-9, and AD-11 make those schemas a
   Holocene-owned browser boundary.
3. The current platform is local-first and single-operator; multi-tenant
   identity, independent DeloHQ deployment, and a cloud lifecycle remain out of
   this feature spine.
