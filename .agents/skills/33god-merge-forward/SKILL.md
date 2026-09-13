---
name: 33god-merge-forward
description: 33GOD-specific extension of the merge-forward workflow, including product authority boundaries and bounded session-based tuning.
---

# 33GOD merge-forward

Apply the [generic merge-forward workflow](../../../../33god-platform/skills/merge-forward/SKILL.md), then these 33GOD boundaries. Live source and explicit user instructions outrank historical prose.

## Operating model

This is one user and one decision-maker working in pre-production. Deliver the smallest useful slice, verify its changed behavior, and immediately land component `main` followed by root `main`. Preserve unrelated work and avoid long-lived integration branches.

## Product authority

- **Lifecycle:** PJangler owns deterministic project and fleet provisioning.
- **Momo:** owns ongoing project orchestration and delegates implementation.
- **Bloodbank:** owns event contracts, hook ingress, behavioral dispatch, and event publication.
- **Candystore:** owns durable event history.
- **Holocene:** owns the operator-facing control surface and displays runtime evidence.
- Component repositories own their implementations; root owns relationships, pins, and integrated acceptance.

Changes to these boundaries require an explicit product decision. Routine implementation inside them proceeds under the user's task authorization.

## Delivery

1. Establish the current branch, source changes, and affected live behavior.
2. Define the smallest outcome and select the checks in [references/gates.md](references/gates.md).
3. Implement only the owning component and its immediate interface changes.
4. Run checks sufficient to prove the changed behavior. Fix reproduced failures.
5. Commit and push the component, then advance and push the root pin.
6. Report what is running, what was tested, and material remaining limits.

## Session tuning

The hub invokes `scripts/rebalance.py` on a true session close. Native CLIs never register this worker directly. The worker uses the session transcript to propose narrowly scoped edits in a temporary candidate and applies them only when the extension is clean on main. It preserves the product boundaries above, rejects unapproved paths and excessive growth, and records an explicit outcome. Applied changes are committed and pushed immediately; deferred or failed runs do not count as applied work.

Disable the concern for a project with `.agents/local.json`:

```json
{"hooks":{"disabled":["merge-forward-session-rebalance"]}}
```

The worker's subprocess has recursion guards and bounded execution. It never modifies arbitrary project files or the generic global skill. Stop events represent turn completion; they do not trigger session tuning.
