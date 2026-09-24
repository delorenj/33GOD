---
name: 33god-merge-forward
description: 33GOD-specific extension of the merge-forward workflow, including product authority boundaries and bounded session-based tuning.
---

# 33GOD merge-forward

Apply the [generic merge-forward workflow](../../../../33god-platform/skills/merge-forward/SKILL.md), then these 33GOD boundaries. Live source and explicit user instructions outrank historical prose.

## Operating model

This is one user and one decision-maker working in pre-production. Deliver the smallest useful slice, verify its changed behavior, and immediately land component `main` followed by root `main`. Preserve unrelated work and avoid long-lived integration branches.

The 33GOD skill applies to this repository and its owned components only. If a
request or transcript is primarily about a sibling repository, stop and resume
from that repository's canonical checkout; its instructions, memory, skills,
and code index are part of the safety boundary. Extract a generic workflow
lesson only when it is directly applicable here. Do not merge, deploy, or
report sibling-repository work as 33GOD work merely because the session opened
in this directory.

## Product authority

- **Momo:** owns the shared PM playbook: prioritization, readiness, delegation,
  review, human questions, and improvement feedback. It is not a second ticket
  state machine or Plane actor.
- **Lifecycle (Krebs):** owns managed ticket execution: claims, leases, lifecycle
  transitions, recovery, evidence gates, and reconciliation.
- **Pilot (`px`):** owns the agent-facing authenticated Plane commands and
  provider operations. Krebs may use its internal provider entrypoint; do not
  duplicate board mutation logic in Momo or Hermes.
- **PJangler:** owns canonical project/role bindings, provisioning, and
  capability readiness; it does not infer missing board bindings or close work.
- **Flume:** owns workforce identity, roster, and role contracts, including a
  named agent's stable personal memory bank; it does not own Plane tickets.
- **Hermes and interactive runtimes:** supervise recorded agent runs; they do
  not own a competing ticket lifecycle.
- **Bloodbank:** owns event contracts, hook ingress, behavioral dispatch, and event publication.
- **Candystore:** owns durable event history.
- **Holocene:** owns the operator-facing control surface and displays runtime evidence.
- Component repositories own their implementations; root owns relationships, pins, and integrated acceptance.

Model authentication and Plane attribution are separate. NewAPI OAuth is only
the model-provider path; each interactive agent and controller repair identity
needs its own native Plane actor and credential. Never infer Plane provenance
from a gateway token or build an implicit gateway-to-Plane mapping.

Changes to these boundaries require an explicit product decision. Routine implementation inside them proceeds under the user's task authorization.

## Delivery

1. Establish the current branch, source changes, and affected live behavior. For diagnosis-only work, if service has recovered and no repair is needed, verify recovery and report findings; no source change or merge is required.
2. Define the smallest outcome and select the checks in [references/gates.md](references/gates.md).
3. Implement only the owning component and its immediate interface changes.
4. Run checks sufficient to prove the changed behavior. Fix reproduced failures.
   Follow asynchronous work to its actual receipt: a successful n8n run may
   have skipped dispatch, and a PM handoff does not prove a worker claimed or
   executed the ticket. When moving an existing delivery target, confirm the
   replacement's delivery receipt before disabling the old path.
   When a change crosses a nested component boundary, run that component's
   focused checks and land its canonical commit before parent gates that inspect
   the component source; then advance the root pin and run integrated checks.
5. Commit and push the component, then advance and push the root pin. Do not
   treat a dirty nested checkout as canonical source for an acceptance gate.
6. Report implementation, installation/runtime proof, and activation readiness
   separately. A distributed skill, healthy service, or passing test does not
   prove native actor enrollment or active-board cutover.

## Session tuning

The hub invokes `scripts/rebalance.py` on a true session close. Native CLIs never register this worker directly. The worker uses the session transcript to propose narrowly scoped edits in a temporary candidate and applies them only when the extension is clean on main. It preserves the product boundaries above, rejects unapproved paths and excessive growth, and records an explicit outcome. Applied changes are committed and pushed immediately; deferred or failed runs do not count as applied work.

Disable the concern for a project with `.agents/local.json`:

```json
{"hooks":{"disabled":["merge-forward-session-rebalance"]}}
```

The worker's subprocess has recursion guards and bounded execution. It never modifies arbitrary project files or the generic global skill. Stop events represent turn completion; they do not trigger session tuning.
