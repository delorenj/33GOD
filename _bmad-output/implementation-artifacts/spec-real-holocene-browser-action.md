---
title: 'Prove a real Holocene Lifecycle browser action'
type: 'feature'
created: '2026-07-19'
status: 'done'
baseline_commit: 'd4bb749db2bac19b6ae105cdf93d0ba5e3987f40'
context:
  - 'PRD.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-18.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The live Holocene gate currently submits its successful Lifecycle action through the Python harness and starts the web only afterward to take passive Playwright CLI screenshots. That does not prove an operator can act through the rendered legal frontier or see Lifecycle's authoritative result.

**Approach:** Make Holocene own a reusable Chromium proof that reads action identity from semantic DOM state, confirms and clicks the actual enabled control, records the unmocked browser POST/202 receipt, and waits for the rendered authority transition and verdict. Make the root harness invoke and independently verify that receipt while retaining Lifecycle, Bloodbank, and Candystore ownership.

## Boundaries & Constraints

**Always:** Lifecycle alone determines lifecycle truth; Bloodbank owns schemas and transport; Candystore remains append-only audit/projection; Momo chooses and executes legal work; Holocene renders authoritative state and invokes high-level actions. Use the pinned Lifecycle digest, exact component SHAs, isolated resources, stable semantic selectors, real Chromium interaction, and authority/Candystore observations.

**Ask First:** Any change that alters those ownership boundaries, changes the Lifecycle/Bloodbank schema contract, or requires touching a primary checkout or unrelated WIP.

**Never:** Directly POST the successful Holocene action from the harness; mock or intercept browser routes/responses; predict or optimistically mutate lifecycle state; substitute screenshots for interaction; add rollback, safety, stakeholder, or coexistence ceremony; edit `tasks.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|----------------------------|----------------|
| Real allowed action | Current projection, allowed confirmation frontier, matching actor/grant/version | Dialog identity is accepted, browser sends exact POST, API returns 202/non-authoritative receipt, UI later renders authority state/version/source/verdict | Proof fails on any identity, status, body, causality, render, or image mismatch |
| Disabled action | Missing/stale projection, denied frontier, missing grant, or gate resolution without choice | Semantic action control is disabled and no command is sent | Component tests assert disabled contract |
| Confirmation cancelled or command error | Confirmation rejected or non-2xx response | No accepted click receipt, or visible command error; no predicted truth | Focused tests assert behavior/helper contract and rendered error |
| Authority observation delayed | Broker receipt exists but projection/verdict has not caught up | Browser polls rendered DOM until matching command causality and resulting version appear | Bounded timeout emits proof failure and diagnostic screenshots |

</frozen-after-approval>

## Code Map

- `holocene/apps/web/app/lifecycle/lifecycle-details.tsx` -- authoritative rendered state, semantic action/context/verdict selectors, success/error receipts.
- `holocene/apps/web/app/lifecycle/lifecycle-surface.tsx` -- confirmation, real POST, non-optimistic authoritative reload.
- `holocene/scripts/prove-lifecycle-browser.mjs` -- reusable browser interaction and JSON receipt owner.
- `holocene/apps/web/app/lifecycle/*.test.tsx` -- focused render/confirmation/receipt contract tests.
- `33god-platform/scripts/verify-lifecycle-live.py` -- isolated stack orchestration and independent receipt/authority/Candystore validation.
- `33god-platform/tests/test_validate_compose.py` -- anti-synthetic source gates and platform regression suite.
- `33god-platform/components/holocene.yaml`, `scripts/check-doc-drift.py` -- exact Holocene pin and drift enforcement.
- Holocene/root README, architecture/change/changelog artifacts -- current browser seam and unchanged authority boundary.

## Tasks & Acceptance

**Execution:**
- [x] Add semantic Lifecycle DOM contracts and focused component/helper tests without client-side truth prediction.
- [x] Add the Holocene Playwright script, exact request/response/render assertions, JSON receipt, and desktop/mobile screenshots.
- [x] Replace the harness-authored successful POST/screenshot phase with API+web startup, browser-proof invocation, receipt parsing, and independent authority/Candystore/causality checks.
- [x] Add anti-synthetic tests rejecting passive screenshots, direct successful harness POSTs, browser mocks, missing confirmation/202/body capture, and missing rendered-outcome assertions.
- [x] Update Holocene and root docs/BMAD/change artifacts, publish Holocene first, advance the exact root gitlink/manifest/drift pin, then publish root.

**Acceptance Criteria:**
- Given a current confirmation-required Lifecycle frontier, when Chromium loads `/lifecycle/<id>` and clicks the enabled action, then the receipt proves the actual dialog, exact DOM actor/grant/frontier/version, browser-originated POST body, HTTP 202 response body, and explicitly non-authoritative broker receipt.
- Given Lifecycle applies that command, when Candystore projects the result, then the same browser visibly observes the resulting status/version, source correlation/causation, matching command verdict, and writes both screenshots.
- Given any synthetic substitute or missing interaction/outcome assertion, when the root platform tests inspect the proof contract, then they fail.
- Given both repositories are clean and validated, when published, then remote refs resolve to the exact reported Holocene and root commits and the root pin matches Holocene.

## Spec Change Log

- 2026-07-19 review patch: blocked service workers/HAR-style substitutes,
  bound the 202 response to the exact captured request, and compared the full
  rendered verdict against independent authority/Candystore evidence.

## Verification

**Commands:**
- `pnpm test && pnpm typecheck && pnpm build && pnpm lint` in Holocene -- all workspace gates pass.
- `python -m unittest discover -s 33god-platform/tests -p 'test_*.py' -v` -- platform suite passes with at least 41 tests.
- Root default/tools/full/cloud Compose validation, populated-root manifest validation, drift validation, diff check, and code-review graph delta/affected flows -- all pass.
- Fresh isolated `verify-lifecycle-live.py` run with the immutable Lifecycle digest -- receipt contains real dialog/click/POST/202/render identities, two images, authority/Candystore evidence, clean resource teardown, and zero Aion residue.
- `git ls-remote` for both published refs -- exact local commits match remote refs.

## Suggested Review Order

**Real browser proof**

- Drives the actual confirmation, click, request/response, render, and image receipt.
  [`prove-lifecycle-browser.mjs:24`](../../holocene/scripts/prove-lifecycle-browser.mjs#L24)

- Binds the 202 to one unmocked request and rejects service-worker responses.
  [`prove-lifecycle-browser.mjs:208`](../../holocene/scripts/prove-lifecycle-browser.mjs#L208)

**Authority-preserving UI**

- Publishes only current rendered frontier identity and never predicts truth.
  [`lifecycle-surface.tsx:63`](../../holocene/apps/web/app/lifecycle/lifecycle-surface.tsx#L63)

- Exposes stable state, source, actor, grant, frontier, receipt, and verdict semantics.
  [`lifecycle-details.tsx:45`](../../holocene/apps/web/app/lifecycle/lifecycle-details.tsx#L45)

- Rejects any 202 that is not explicitly a non-authoritative broker receipt.
  [`lifecycle-action-contract.ts:48`](../../holocene/apps/web/app/lifecycle/lifecycle-action-contract.ts#L48)

**Independent live verification**

- Starts API/web first, invokes Chromium, then cross-checks Lifecycle and Candystore.
  [`verify-lifecycle-live.py:3247`](../../33god-platform/scripts/verify-lifecycle-live.py#L3247)

- Parses exact browser identities, rendered verdict fields, causality, and image hashes.
  [`verify-lifecycle-live.py:3579`](../../33god-platform/scripts/verify-lifecycle-live.py#L3579)

**Regression and provenance**

- Rejects direct-success POSTs, passive screenshots, mocks, and missing outcome assertions.
  [`test_validate_compose.py:604`](../../33god-platform/tests/test_validate_compose.py#L604)

- Pins the published Holocene implementation into the populated root manifest.
  [`holocene.yaml:6`](../../33god-platform/components/holocene.yaml#L6)
