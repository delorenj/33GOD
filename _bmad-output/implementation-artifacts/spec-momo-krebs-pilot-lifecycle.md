---
title: Momo, Krebs and Pilot reliable ticket execution
type: feature
created: 2026-09-16
status: in-review
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

All three reviews completed before triage. A new third reviewer thread was unavailable (platform thread limit); the idle grounding reviewer ran verification-gap instructions against the supplied diff. Each finding below was checked against its own source/call path. Shared-parent ephemeral review actors are intentional; no finding requests a native account for every temporary reviewer.

All entries are kept as implementation patches: the approved execution contract already specifies the required behavior, so there is no unresolved intent or change to frozen acceptance. Related entries are grouped for implementation only after these individual verdicts. No existing work is reverted.

| ID | Severity | Verified finding | Source consequence / disposition |
|---|---|---|---|
| B1 | high | Successful outcome still swept as abnormal exit | Keep; patch — controller sweep ignores record.outcome. |
| B2 | high | Null acceptance passes equality checks | Keep; patch — review/handoff accept None after update. |
| B3 | high | No delivered outcome required for closeout | Keep; patch — handoff checks evidence but not successful finish. |
| B4 | high | Cross-ticket takeover strands old ticket | Keep; patch — stop targets old attempt; projection targets new ticket. |
| B5 | high | Invalid start wedges pending intent | Keep; patch — argv validated only inside recovery. |
| B6 | high | Lost transient unit allows duplicate dispatch | Keep; patch — runtime start dedup uses only LoadState. |
| B7 | high | Plane outage prevents local revocation/stop | Keep; patch — sweep reads provider before expiry and recover verifies first. |
| B8 | high | Managed Backlog cannot become Todo | Keep; patch — planning transition absent from operations. |
| B9 | high | Inactive-ticket CRUD requires worker | Keep; patch — comment/update enter active-attempt gate. |
| B10 | high | Retry exhaustion has no operator reset | Keep; patch — all acquisition paths reject exhausted flag. |
| B11 | high | Malformed command can kill consumer | Keep; patch — exception handler assumes command dict and correlation. |
| B12 | high | Pins omit transitive helper and skill files | Keep; patch — verify hashes only two entrypoints. |
| B13 | high | Explicit board outside CWD bypasses managed routing | Keep; patch — config loads execution only from ancestor manifest. |
| B14 | high | Malformed manifest reactivates legacy | Keep; patch — heartbeat fallback and readJson swallow parse failure. |
| B15 | high | Readiness accepts unusable recovery/runtime bindings | Keep; patch — service omits controller actor, roles, prefix and supervisor probe. |
| B16 | high | Standalone health import missing dependency | Keep; patch — old pyproject has no canonical Krebs dependency. |
| B17 | medium | Legacy idea submission regressed | Keep; patch — new submit requires execution.actors before queue. |
| B18 | high | Feedback crash leaves permanent lock | Keep; patch — mkdir lock has no ownership/recovery or flush path. |
| E1 | high | Invalid start permanently blocks board | Keep; patch — confirmed independently at contract start and recovery. |
| E2 | high | Restart can repeat disappeared transient launch | Keep; patch — no durable launch-attempt record. |
| E3 | high | Expired pending start can launch | Keep; patch — recovery calls runtime.start before lease check. |
| E4 | high | Null acceptance drops child gates | Keep; patch — required_children falls back to empty for None. |
| E5 | high | Takeover leaves old projection active | Keep; patch — no old-ticket provider action in plan. |
| E6 | high | PATCH then failed question POST strands intent | Keep; patch — one sent bit covers two independent mutations. |
| E7 | high | Comment blesses changed human scope | Keep; patch — all observed revisions overwrite provider_revision. |
| E8 | high | Scope race between validation and apply/readback | Keep; patch — helper lacks expected content revision guard. |
| E9 | high | Operator cannot reset exhausted retry state | Keep; patch — no operation changes retry_exhausted to false. |
| E10 | high | Lock-before-spool can lose idea | Keep; patch — lock survives process exit before persist. |
| E11 | high | Standalone health dependency missing | Keep; patch — checkout fallback requires sibling root source. |
| E12 | high | Internal helper apply lacks durable intent check | Keep; patch — handle accepts caller binding and disables execution fence. |
| E13 | high | Readiness lacks repair actor/runtime prerequisites | Keep; patch — verified service and PJ readiness differences. |
| E14 | high | Installed referenced playbook not pinned | Keep; patch — SKILL.md hash does not cover managed-execution.md. |
| V1 | high | Default test command can pass with all skipped | Keep; patch — reviewer ran20skipped; all new test groups opt-in. |
| V2 | high | Production provider writes not exercised | Keep; patch — existing provider tests verify only enrollment; execution substitutes lane-only fixtures. |
| V3 | high | Legacy managed dispatch/ACK fences untested | Keep; patch — tests do not execute managed/shadow/cached callback branches. |
| V4 | high | Managed heartbeat behavior untested | Keep; patch — existing heartbeat tests remain legacy; adapter fence test separate. |
| V5 | high | Feedback spool and delivery recovery untested | Keep; patch — no test imports idea submit/recovery. |
| V6 | high | Undispatched claim renewed forever | Keep; patch — adapter renews every active claim; sweep only probes dispatched runs. |
| R1 | high | Managed heartbeat never invokes idle PM planning | Keep; patch — adapter only status/renew/exit disables autonomous board operation. |
| R2 | high | Run ID reuse across generations remains possible | Keep; patch — unit identity based on run_id; contract does not enforce uniqueness. |
| R3 | high | Approved distinct operator override missing | Keep; patch — operation set lacks audited override path. |
| R4 | medium | Momo distribution text contradicts actual registry | Keep; patch — SKILL.md calls all-skills retired though native Hermes consumes it. |

Additional independent path checks: R5 (high, keep/patch) — runtime stop/running derive units from mutable actor configuration; freeze supervisor identity so a changed prefix cannot prove the old worker stopped. R6 (high, keep/patch) — parent completion must reject operator-override receipts and verify declared child identity, rather than accepting arbitrary global Done receipts.

Correction groups: execution gates (B1–B5/B8–B10/E1/E4/E5/E9/R2/R3); durable launch and local recovery (B6/B7/E2/E3/V6/R1); provider step/content integrity (E6–E8/E12/V2); ingress and ownership (B11/B13/B14); full artifact/readiness/compatibility (B12/B15/B16/E11/E13/E14/R4); feedback (B17/B18/E10/V5); required behavioral gates (V1/V3/V4). Root owns the real HTTP provider and transport integration checks; implementation agent owns code fixes and other regression checks.

## Verification

Run focused Python/Postgres, Node CLI and affected template/provisioning tests. Include real database concurrent-claim tests, provider failure injection, restart tests, command ingress identity checks, and installed-runtime/source verification. Record exact results and distinguish fixture, shadow and live proof. Root performs independent review before completion.
