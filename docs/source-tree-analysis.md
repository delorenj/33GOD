# 33GOD Source Tree Analysis

**Date:** 2026-07-20

## Scope

The root is a coordination workspace for independently versioned repositories.
Two boundaries are intentionally separate:

- the exact Lifecycle acceptance slice is Bloodbank, Lifecycle, Candystore,
  Momo, Holocene, and PJangler;
- the product registry contains twelve entries, adding Hermes Fleet, Skillex,
  Hindsight, Pipeline MCP Hub, Candybar, and HeyMa.

Root files own cross-component topology, exact pins, acceptance, and drift.
Component repositories remain authoritative for their implementations.

```text
33GOD/
├── _bmad/                              # Root BMAD configuration
├── _bmad-output/planning-artifacts/    # Current root planning artifacts
├── docs/                               # Cross-component knowledge
├── scripts/
│   └── check-doc-drift.py              # Topology and semantic parity gate
├── 33god-platform/
│   ├── components.yaml                 # Six-slice plus twelve-registry policy
│   ├── components/*.yaml               # Component ownership and pins
│   ├── compose.yaml                    # Root-owned normalized local topology
│   ├── scripts/platform.py             # Registry/provenance utility
│   ├── scripts/validate-compose.py     # Four-model semantic validator
│   ├── tests/                          # Positive and adversarial gates
│   └── changes/*.jsonl                 # Machine-readable platform changes
├── bloodbank/                          # Schemas and NATS/Dapr transport
├── lifecycle/                          # Sole deterministic lifecycle authority
├── candystore/                         # Audit history and read projections
├── momo/                               # Legal-work chooser/executor client
├── holocene/                           # Dashboard and high-level actions
├── pjangler/                           # Project identity/bootstrap/bindings
├── hermes-agent-template/              # Planned pinned fleet template gitlink
└── toad/                               # Planned pinned delegating client gitlink
```

The other registry repositories are either root-local directories or explicit
external siblings. Their presence in the product registry does not add them to
the Lifecycle acceptance slice.

## Checkout and path policy

`GOD_SOURCE_ROOT` selects exactly one 33GOD checkout. When it is set, it is
authoritative. A selected in-tree component root is atomic: every descendant
resolves beneath that root, and a missing repository or leaf fails closed.
No path may borrow bytes from a primary checkout through a linked-worktree Git
common directory.

True external siblings such as Skillex and HeyMa use the independent
`GOD_EXTERNAL_ROOT` policy. The external root is never used to resolve an
in-tree component. Both selected and external paths reject symlink escapes.

## Projection boundaries

| Root artifact | Reads from component source | Does not own |
|---|---|---|
| `compose.yaml` | Bloodbank transport, Lifecycle image contract, Candystore build/Dapr components, Holocene source/env, PJangler tools | Component implementation or runtime truth |
| `validate-compose.py` | Required paths beneath explicit `--source-root` | Component correctness beyond the projected contract |
| `platform.py` | Root gitlinks, `.gitmodules`, component manifests, exact checkout identity/revision | Component mutation or pin advancement |
| `check-doc-drift.py` | Acceptance roots, nested operational gitlinks, current docs, semantic surfaces | Lifecycle state or destructive remediation |

## Acceptance entrypoints

| Part | Entrypoint | Root acceptance role |
|---|---|---|
| Bloodbank | NATS image plus `compose/nats/init.sh` | Broker, canonical streams, Dapr placement |
| Lifecycle | Immutable OCI digest | Dedicated database, migrate/bootstrap/serve |
| Candystore | `python -m candystore.main` plus daprd | One audit/read-projection deployment |
| Momo | Durable obligation actor and Lifecycle client | Choose and execute only Lifecycle-legal work |
| Holocene | Next.js web plus host Fastify API | Render and submit high-level actions |
| PJangler | Node CLI and stdio MCP | Project identity and binding inputs |

## Configuration boundaries

- Root `_bmad` files use root-relative tokens.
- Component credentials, host systemd state, and provider configuration remain
  outside root ownership.
- Root validation checks a repository's own top-level, origin identity, root
  gitlink revision, and checkout `HEAD`; an empty directory is uninitialized.
- Every mapped root gitlink must be an initialized checkout at the exact index
  revision and normalized `.gitmodules` origin, even without a component row.
- External networks and volumes retain their exact identities; validation does
  not create, remove, or migrate them.
