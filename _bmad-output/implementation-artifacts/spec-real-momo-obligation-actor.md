---
title: 'Real Momo obligation actor for lifecycle live proof'
type: 'bugfix'
created: '2026-07-18'
status: 'completed'
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

**Transport Contract Follow-up (2026-07-19):**
- [x] Native completion publication -- publish the exact completion CloudEvent ID as `Nats-Msg-Id` and capture/assert it in the fake JetStream.
- [x] ACK ambiguity -- prove `ack_sync` failure after completion PubAck leaves the invocation unacked and writes no receipt.
- [x] Retry identity -- derive completion ID/time from the immutable invocation and prove redelivery reconstructs the same event.
- [x] Root parity -- promote byte-identical Momo skill bytes, pin exact component revision `4c59f10460798f1ba8853b4f0b59b56ce31bacbd`, and require broker-stored header plus non-duplicate clean PubAck evidence.
- [x] Validation and live proof -- pass 77 Momo tests, 40 root platform tests, Ruff/compile/diff, four Compose models, drift `21/0/0`, populated-root manifest validation, review-graph change/flow analysis, fresh live proof, and zero `aion-*` residue.
- [x] Ordered publication -- push and verify Momo `fix/real-obligation-worker-20260719`, then push and verify root `feature/prometheus-real-momo-execution` at implementation checkpoint `585d47c5ba60f74dfe81149f959c447de4be3755`.

**Acceptance Criteria:**
- Given the actor is ready before publish, when the canonical invocation reaches JetStream, then the receipt delivery sequence and invocation ID match the publisher PubAck exactly.
- Given a current-run evidence package and exact promoted skill resource, when the adapter succeeds, then the artifact exists and its independently recomputed byte hash equals both receipt and completion evidence.
- Given completion publication, when operation order is inspected, then the completion PubAck precedes invocation `ack_sync`; every earlier failure leaves it unacked.
- Given adversarial cloned evidence, when Lifecycle reconciles it, then only the untouched actor completion satisfies the exact active occurrence.
- Given the validated actor receipt, when authoritative observation completes, then Lifecycle is active, Candystore stores the actor event exactly once, and no alternate lifecycle writer exists.
- Given final cleanup and pushed refs, when inventories and `ls-remote` are checked, then no isolated residue remains and exact Momo/root commits are remotely fetchable.

## Spec Change Log

- 2026-07-19: Completed the native JetStream publication/ACK follow-up, published Momo `4c59f10460798f1ba8853b4f0b59b56ce31bacbd`, published root implementation checkpoint `585d47c5ba60f74dfe81149f959c447de4be3755`, verified canonical stored message ID and non-duplicate completion PubAck in isolated project `aion-lifecycle-21568c89df`, and confirmed zero-residue cleanup.

## Design Notes

The selector is an explicit adapter compatibility mapping, not an inferred BMAD package version. The worker verifies the promoted resource bytes, reconstructs the invocation plan solely from the delivered envelope, and uses Momo's existing full semantic verifier. Completion time is derived from that immutable invocation, so an ACK-ambiguous redelivery reconstructs the same CloudEvent ID/time and the same `Nats-Msg-Id`. An optional release file lets the harness publish negative clones derived from the actor-authored completion preview before the actor publishes the only satisfying event.

## Verification

**Commands:**
- `cd momo && mise run test && mise run lint` -- 77 tests and Ruff pass.
- `mise run platform:compose:test` -- 40 root platform tests pass.
- `GOD_SOURCE_ROOT=/home/delorenj/code/33GOD mise run platform:validate` and `mise run platform:compose:validate` -- manifest registry and default/tools/full/cloud semantics pass.
- `mise run docs:drift` -- root contracts and exact pins agree at `21 PASS / 0 WARN / 0 FAIL`.
- `python3 33god-platform/scripts/verify-lifecycle-live.py --proof-dir /tmp/33god-lifecycle-proof-syntaxsorcerer-transport-C0E0AISE --screenshots-dir /tmp/33god-lifecycle-proof-syntaxsorcerer-transport-C0E0AISE/screenshots` -- real actor matrix passes and preserves receipt/report/proof.
- `git ls-remote --heads origin refs/heads/<exact-ref>` -- Momo and root refs matched their delivered commits before this closure record.

## Final Follow-up Proof

- **Published refs:** Momo `fix/real-obligation-worker-20260719` at `4c59f10460798f1ba8853b4f0b59b56ce31bacbd`; root `feature/prometheus-real-momo-execution` implementation checkpoint at `585d47c5ba60f74dfe81149f959c447de4be3755`.
- **Fresh run:** project `aion-lifecycle-21568c89df`, lifecycle `lc_aion_21568c89df`, proof `/tmp/33god-lifecycle-proof-syntaxsorcerer-transport-C0E0AISE/proof.json`, pinned image `ghcr.io/delorenj/lifecycle@sha256:b216be4e1b796236309ee0b39120b0f353b62ee9f3c677901b2441a2c7aef210`.
- **Actor identity:** invocation `1528fbfb-b967-537e-b6d2-4422df1c8dc8`; completion `35244f41-e18e-5f38-97a8-dfa7f9a4fdce`; stored `Nats-Msg-Id` exactly equals the completion ID; completion PubAck stream sequence `18`, `duplicate=false`.
- **Ordering:** `completion_puback` sequence `10`, `invocation_ack_sync` sequence `11`, `receipt_written` sequence `12`; durable consumer ended with `num_ack_pending=0`.
- **Artifact:** `/tmp/33god-lifecycle-proof-syntaxsorcerer-transport-C0E0AISE/momo-obligation/review-report.md`, 1172 bytes, SHA-256 `e32eea6f7e6fd398a475f6ca29baa0ca6ac167fb5a97c47847aa30f652407483`; promoted resource `.agents/skills/bmad-code-review/SKILL.md`, SHA-256 `c303ef6d8cc507ef268e95978052250289bd0c76941441a023baebfd807c1efd`.
- **Authority/audit:** Lifecycle reached `active`; authoritative observation count `1`; Candystore event count `1`; Momo never wrote lifecycle truth.
- **Cleanup:** proof summary reports no remaining containers, networks, volumes, local Candystore image, or ephemeral secret; independent global `aion-*` container/network/volume/image inventories were empty.
