---
title: 'Real Momo obligation actor for lifecycle live proof'
type: 'bugfix'
created: '2026-07-18'
status: 'review'
baseline_commit: 'af23690150a7ae2738ceea144889efaafccc6716'
context:
  - 'AGENTS.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - 'docs/architecture-lifecycle.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The lifecycle live matrix publishes a canonical Momo invocation but the harness fabricates a placeholder artifact hash, builds completion evidence, and publishes the satisfying event itself. This proves envelope construction rather than broker-delivered execution.

**Approach:** Add a bounded Momo worker that durably consumes the exact JetStream command, resolves and executes the pinned `bmad-code-review@6.10.2` adapter against current-run evidence, writes and hashes a real report, publishes occurrence-bound evidence, and acknowledges only after the completion PubAck. Make the harness prove that chain independently before trusting Lifecycle and Candystore.

## Boundaries & Constraints

**Always:** Preserve Lifecycle as sole lifecycle authority; Bloodbank schemas and NATS/JetStream as transport authority; Candystore as append-only audit/projection; Momo as legal-work chooser/executor only; Holocene as renderer. Preserve invocation subject/type, target, occurrence, state version, authority snapshot, correlation, and causation. Keep the pinned Lifecycle image digest. Use isolated proof resources and exact cleanup. Keep `momo/skill` and root `skills/momo` synchronized and pin every Momo consumer to the pushed component commit.

**Ask First:** Any Lifecycle/Bloodbank schema change, authority-boundary change, destructive action outside isolated `aion-*` resources, or need to alter unrelated WIP.

**Never:** Let the harness author/publish final success, call `complete-obligation` for success, pass an invocation directly to the worker, accept placeholder hashes, acknowledge before completion publication, write lifecycle truth from Momo, edit `tasks.md`, touch primary checkouts, or push unverified refs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| Real execution | Exact canonical invocation on `BLOODBANK_COMMANDS` | Durable consumes it, adapter writes report, completion gets PubAck, invocation gets ack, receipt links all identities/hashes | No synthetic fallback |
| Invalid invocation | Wrong target, skill, occurrence, causal field, or no JetStream metadata | No completion and no positive ack | Fail closed with diagnostic |
| Adapter/package failure | Missing resource, digest drift, malformed package, failed concrete check | No success event and no ack | Preserve logs/artifact evidence |
| Publication failure | Completion publish has no PubAck | Invocation remains unacked | Exit nonzero for redelivery |
| Tampered receipt/artifact | Receipt size/hash differs from exact bytes | Harness rejects proof before authority wait | Fail matrix and clean resources |
| Adversarial fixtures | Actor-authored completion cloned with pre-activation or wrong occurrence | Obligation stays pending until untouched actor completion | Record as negative fixtures only |

</frozen-after-approval>

## Code Map

- `momo/skill/scripts/lifecycle_client.py` -- canonical immutable invocation and completion builders.
- `momo/skill/scripts/obligation_worker.py` -- new durable consumer, adapter executor, publisher, and receipt writer.
- `momo/skill/resources/obligation-skill-catalog.json` -- exact selector-to-promoted-resource digest binding.
- `momo/tests/` -- worker, client, and anti-placeholder behavior.
- `33god-platform/scripts/verify-lifecycle-live.py` -- isolated actor choreography and independent proof checks.
- `33god-platform/tests/test_validate_compose.py` -- anti-synthetic semantic gates.
- `scripts/check-doc-drift.py` and platform/root docs/manifests -- exact Momo pin and claim parity.

## Tasks & Acceptance

**Execution:**
- [x] Momo worker/catalog/client/tests/dependencies -- implement consume, validate, resolve, execute, hash, publish, ack, receipt, and failure semantics.
- [x] Promoted root Momo skill -- mirror component skill bytes without drift.
- [x] Live harness/platform tests -- replace synthetic success and retain actor-derived occurrence fixtures.
- [x] Manifests/docs/changelog/drift constants -- describe real actor execution while preserving authority language and exact pins.
- [x] Component/root Git refs -- branch from accepted pins, commit, push, advance gitlink, and verify remote fetchability.
- [x] Validation/live proof/cleanup -- run focused/full tests, four Compose models, drift gate, fresh Holocene build if required, isolated live matrix, and zero-residue audit.

**Acceptance Criteria:**
- Given the actor is ready before publish, when the canonical invocation reaches JetStream, then the receipt delivery sequence and invocation ID match the publisher PubAck exactly.
- Given a current-run evidence package and exact promoted skill resource, when the adapter succeeds, then the artifact exists and its independently recomputed byte hash equals both receipt and completion evidence.
- Given completion publication, when operation order is inspected, then the completion PubAck precedes invocation `ack_sync`; every earlier failure leaves it unacked.
- Given adversarial cloned evidence, when Lifecycle reconciles it, then only the untouched actor completion satisfies the exact active occurrence.
- Given the validated actor receipt, when authoritative observation completes, then Lifecycle is active, Candystore stores the actor event exactly once, and no alternate lifecycle writer exists.
- Given final cleanup and pushed refs, when inventories and `ls-remote` are checked, then no isolated residue remains and exact Momo/root commits are remotely fetchable.

## Spec Change Log

- 2026-07-19: Implemented the durable Momo obligation actor, promoted its exact skill bytes, replaced synthetic harness success, and verified component commit `9b6b1e7d30001f5918d32e99cbcbf5200fc29e1d`, root implementation checkpoint `e485f941d8b366a72e1a4477b221f3e7739e7cba`, the isolated live proof, and zero-residue cleanup.

## Design Notes

The selector is an explicit adapter compatibility mapping, not an inferred BMAD package version. The worker verifies the promoted resource bytes, reconstructs the invocation plan solely from the delivered envelope, and uses Momo's existing full semantic verifier. An optional release file lets the harness publish negative clones derived from the actor-authored completion preview before the actor publishes the only satisfying event.

## Verification

**Commands:**
- `cd momo && mise run test && mise run lint` -- all focused/full Momo checks pass.
- `mise run platform:validate && mise run platform:compose:test && mise run platform:compose:validate` -- registry, units, and default/tools/full/cloud semantics pass.
- `mise run docs:drift` -- root contracts and exact pins agree.
- `python3 33god-platform/scripts/verify-lifecycle-live.py --proof-dir <fresh-dir> --screenshots-dir <fresh-dir>/screenshots` -- real actor matrix passes and preserves receipt/report.
- `git ls-remote --heads origin <exact-ref>` -- component and root refs resolve to delivered commits.
