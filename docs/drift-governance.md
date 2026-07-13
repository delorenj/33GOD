# 33GOD Drift Governance

## Ownership

The 33GOD Director owns cross-component contract coherence and release gates. Component teams own internal correctness and current component documentation:

| Area | Owner |
|---|---|
| Event names, schemas, subjects, NATS/Dapr topology | Bloodbank team |
| Persistence, ingest outcome, query API, audit UI | Candystore team |
| Fleet projections, host controls, dashboard/API deployment | Holocene team |
| Registry, project projection, parity rules, templates, MCP/CLI | PJangler team |
| Relationships, deployment contracts, drift register, release gate | 33GOD Director/root platform |

## Authority and Overlap

- Root docs govern relationships and deployment contracts.
- Component docs govern internals.
- Live manifests, code, and tests outrank prose.
- Historical plans are evidence of intent, not current guarantees.
- Conflicts become explicit drift records with owner, evidence, severity, and gate impact.

## Cadence

### Component PR Contract Review

Every component PR that affects event schemas/subjects, hook entrypoints/payloads, public HTTP/MCP/CLI contracts, persistence schema, project manifests, templates, ports, networks, secrets, or cross-component runtime behavior must:

1. Run the component’s focused contract checks.
2. Run `python3 scripts/check-doc-drift.py` against live source and candidate docs.
3. Update the platform machine log and human changelog when change-policy triggers apply.
4. Update root integration/deployment docs or explicitly state why no root contract changes.
5. Include review from the owning component team and the 33GOD Director.

### Weekly Scheduled Audit

Run platform validation, component listing, backfill checks, root drift parity, Markdown-link validation, JSON/YAML parsing, and focused component contract tests. The Director triages new failures into component-owned drift records. Warnings must be reviewed; failures cannot be normalized merely because they are old.

### Pre-Compose and Release Gate

Before changing compose topology or releasing a coordinated baseline, render every relevant Compose model, validate all platform manifests, confirm network/port/secret boundaries, confirm Candystore deployment mutual exclusion, and require no unaccepted critical drift. Services need not be started to pass the configuration gate.

## Drift Record Format

Each record contains:

- Stable ID and severity.
- Owning component.
- Executable evidence path and observed behavior.
- Expected contract.
- Impacted consumers.
- Detection command.
- Disposition: open, accepted-with-expiry, fixed, or superseded.
- Required release gate and verification evidence.

## Current Explicit Drift

| ID | Severity | Owner | Contradiction | Gate impact |
|---|---:|---|---|---|
| BB-CONTRACT-01 | Critical | Bloodbank | Runtime validation omits semantic type/subject equality | Blocks contract-complete runtime claim |
| BB-RUN-01 | Critical | Bloodbank | Heartbeat Compose/CI references missing recorder directory | Blocks heartbeat profile/CI |
| BB-PJ-01 | Critical | PJangler/Bloodbank | Generated repo/agent subject routing violates six-token contract | Blocks canonical agent command claim |
| CANDY-DUR-01 | Critical | Candystore | Dead-letter failure can still receive `DROP` acknowledgement | Blocks “never lose an event” claim |
| CANDY-HOLO-01 | High | Holocene/Candystore | Default Candystore URL/port/network is wrong and failure is silent | Blocks reliable history claim |
| HOLO-SEC-01 | Critical | Holocene | Host-control API binds all interfaces without app auth/authz | Blocks untrusted-network/cloud use |
| HOLO-SECRET-01 | High | Holocene | Literal clock credential is tracked in documentation/history | Requires rotation and history remediation |
| PJ-IDENTITY-01 | Critical | Root/PJangler | Platform manifest resolves another PJangler checkout | Blocks authoritative component listing |
| PJ-REPRO-01 | Critical | PJangler | Dirty template gitlinks plus `HEAD` resolution are unreproducible | Blocks reproducible provisioning claim |
| PJ-SAFE-01 | High | PJangler | Some MCP operations mutate by default; cancellation/result propagation is unreliable | Blocks broad safe-default claim |
| ROOT-COMPOSE-01 | High | Root | Product Compose is a tools scaffold, not integrated orchestration | Blocks unified-stack claim |

## Acceptance Policy

Warnings describe risk or incomplete evidence without a direct executable contradiction. Failures represent missing required artifacts or a demonstrated mismatch between two authoritative declarations. The drift checker exits nonzero only for failures. An accepted failure requires a named owner, expiry, and release-scope exception; documentation alone does not repair the implementation.
