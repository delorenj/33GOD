---
title: Momo, Krebs and Pilot reliable ticket execution
type: feature
created: 2026-09-16
status: in-progress
baseline_commit: 1bb2011d5994
review_loop_iteration: 0
context:
  - /home/delorenj/code/33GOD/AGENTS.md
  - /home/delorenj/code/33GOD/krebs/docs/execution-contract.md
---

<frozen-after-approval reason="User approved the plan and requested implementation">

## Intent

Tickets currently remain in Todo/In Progress after execution, failure or questions. Implement the approved shared lifecycle: Momo is the PM playbook, Krebs enforces execution, Pilot provides authenticated CLI/provider operations, PJangler binds projects and actors, Hermes/interactive adapters supervise runs. Bloodbank carries service commands/events; Candystore records history.

## Boundaries & Constraints

Always preserve unrelated edits, use real Plane actors and secret references, exact lane IDs and readback, one active execution per board, durable fenced attempts, independently reviewed evidence before Done. Root PM delegates to component PMs; interactive Codex/Claude are distinct identities. New managed paths fail closed. Preserve existing non-Plane adapters and project-health data. User authorizes commit/push to main; do not leave branches behind. Missing manual actor enrollment blocks that board's activation, not implementation.

Never equate worker exit with completion, silently fall back to Jarad's credentials, release capacity while an old worker can mutate, retry uncertain creates blindly, or claim unverified deployment/fleet readiness.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected behavior | Error handling |
|---|---|---|---|
| Claim race | Two claims, same board | Exactly one granted worker authority | Other gets conflict |
| Identity | Wrong native user or membership | No provider mutations or run | Explicit enrollment error |
| Success | Current attempt plus frozen AC/artifact evidence | QA, documentation, verified Done | Missing evidence rejected |
| Human question | Current run asks for input | Record question, Needs Attention, park/stop run | No unsafe capacity release |
| Resume | Answer matches question | New fenced generation after capacity acquisition | Scope change revalidates readiness |
| Late result | Old generation after crash/takeover | Audit only | No state changes |
| Partial write | Plane response lost | Durable intent reconciled by readback | No blind duplicate comment/create |
| Recovery | Expired lease or interrupted controller | Persisted reconciliation | No replacement before stopped proof |
| Duplicate | Same command ID and body | Original receipt | Different body rejected |
| Friction | Repeated material px limitation | Attributed deduplicated idea | Queue independently of ticket completion |

</frozen-after-approval>

## Code Map

- `krebs/` — root-owned lifecycle v1/spec/skills; new canonical Python/Postgres execution service and v2 contracts.
- `/home/delorenj/code/pilot/` — standalone Node CLI, existing claim/close, Plane provider, config and idea; indexed. Preserve existing edits to bin/pilot.js and src/commands/schema.js.
- `bloodbank/cli/bb.py`, `bloodbank/schemas/`, `bloodbank/integrations/n8n-nodes-bloodbank/` — command request/reply, schema catalog, legacy dispatch and direct label writers.
- `bloodbank/services/lifecycle-controller/` — existing aggregate project-health prototype; preserve semantics/data during move.
- `momo/skill/`, `momo/spec/momo-agent.spec.yaml` — shared playbook, delegation, existing closeout gates. Preserve delegation.md WIP.
- `hermes-agent-template/template/.scripts/` — heartbeat, sentinel and ticket-provider adapters; old optional close behavior.
- `pjangler/src/commands/hermes/RunCopierTemplate.ts`, project manifest/index — provisioning bindings/readiness. Preserve .env.op WIP.
- `33god-platform/components/krebs.yaml` — root artifact/runtime integration.

## Tasks & Acceptance

Implementation agent owns code and its focused tests across these components; root owns this spec, execution-contract.md, inventory/rollout evidence and final integration review. You are not alone: preserve others' changes, inspect initial diffs and stage only yours. Applicable BMAD instructions require sequential implementation; do not spawn parallel implementers. Use CodeGraph first where indexed. Commit scoped tested units with ticket references when available; root will ensure final push/integration.

**Execution:**
- [ ] Implement versioned commands, evidence, outcomes and receipts; deterministic state machine and Postgres migrations/leases/fencing/dedup/intents/outbox/recovery.
- [ ] Add authenticated Pilot bindings, provider-only helper, pagination/exact states/readback and public lifecycle CLI; managed CRUD cannot bypass controller.
- [ ] Add Bloodbank request/reply/status client and durable controller consumer/publisher with canonical schemas; fence legacy writers per managed board.
- [ ] Integrate Momo, Hermes and interactive runtime behavior, PJangler bindings/readiness; prove installed skill source/version.
- [ ] Preserve project-health module separately, add service packaging, artifact contract, migrations and operational controls.
- [ ] Implement attributed/deduplicated/offline-tolerant Pilot idea feedback.
- [ ] Test all matrix rows and end-to-end controlled execution; deliver inventory, shadow/canary reconciliation and explicit fleet enrollment status.

**Acceptance Criteria:**
- Given a managed board, when work starts, then verified identity and claim precede dispatch; zero unauthorized writes occur.
- Given successful current evidence, when closed, then exact lane progression and provider readback prove completion and durable event history records causation.
- Given a question, crash, provider outage or late callback, when reconciled, then ownership and states remain correct without duplicate workers/questions.
- Given root orchestration, when child work finishes, then verified child receipts and parent integration evidence gate parent completion.
- Given unconfigured actors or legacy writers, when rollout is attempted, then readiness explicitly blocks activation until verified; repeated reconciliation is a no-op.

## Spec Change Log

## Review Triage Log

## Verification

Run focused Python/Postgres, Node CLI and affected template/provisioning tests. Include real database concurrent-claim tests, provider failure injection, restart tests, command ingress identity checks, and installed-runtime/source verification. Record exact results and distinguish fixture, shadow and live proof. Root performs independent review before completion.
