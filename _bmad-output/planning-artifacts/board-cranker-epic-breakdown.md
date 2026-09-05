---
title: "Board Cranker: stateless board contractors"
status: verified
created: 2026-09-02
updated: 2026-09-02
stepsCompleted:
  - delegated-kimi-k3-planning
  - live-plane-readback
  - dependency-repair
  - wip-reconciliation
plane_workspace: 33god
plane_project: 15258893-0206-4e8f-aea6-340eb217988c
---

# Board Cranker epic and implementation stories

## Planning result

Status: REFINED AND VERIFIED

The delegated Kimi K3 planning worker created the parent and original story set on the live 33GOD Plane project. The worker stalled after the Plane writes and never produced its required artifact. Independent PM read-back found that its first story mixed two separately reviewable prerequisites. It was split into 33GOD-43 (schema-validated n8n command publication) and 33GOD-50 (stateless Hermes execution). The dependency chain and epic acceptance criteria were repaired accordingly.

This artifact records live Plane state. It is not implementation evidence.

## Epic

- Identifier: 33GOD-42
- UUID: `bbbc84c2-5661-47c7-a686-a16d1659e601`
- Title: Board Cranker: stateless board contractors
- Priority: high
- State: Backlog
- Parent: none
- Assignees: none
- Start date: none
- Cycle: none
- Labels: none
- URL: https://plane.delo.sh/33god/projects/15258893-0206-4e8f-aea6-340eb217988c/issues/bbbc84c2-5661-47c7-a686-a16d1659e601

Plane has no enabled work-item type for an Epic on this project. 33GOD-42 is therefore the native parent issue for all eight stories; it is not an executable implementation candidate.

## Dependency-ordered stories

| Order | Story | Outcome | Priority | Module | State | Predecessor |
|---:|---|---|---|---|---|---|
| 1 | 33GOD-43 | Publish schema-validated invocation commands from n8n | high | Event Bus | Todo | none |
| 2 | 33GOD-50 | Execute stateless contractor turns through Hermes | high | Gateways and Control Planes | Backlog | 33GOD-43 |
| 3 | 33GOD-44 | Validate bounded contractors from the Board Cranker catalog | high | Project and Ticketing Lifecycle | Backlog | 33GOD-50 |
| 4 | 33GOD-45 | Fortify a newly created Plane ticket end to end | high | Project and Ticketing Lifecycle | Backlog | 33GOD-44 |
| 5 | 33GOD-46 | Reconcile contractor runtime without dual board drivers | high | Project Bootstrapping & Management | Backlog | 33GOD-45 |
| 6 | 33GOD-47 | Advance exactly one ready ticket per hourly crank | high | Project and Ticketing Lifecycle | Backlog | 33GOD-46 |
| 7 | 33GOD-48 | Enforce start, QA rejection, and evidence-backed completion transitions | high | Project and Ticketing Lifecycle | Backlog | 33GOD-47 |
| 8 | 33GOD-49 | Project Board Cranker reproducibly and prove the live 33GOD pilot | high | Agent Configuration and Normalization | Backlog | 33GOD-48 |

### Story identities

- 33GOD-43 — UUID `0f4ac87a-1b03-4921-9a28-75cd3f9bb9f6`  
  https://plane.delo.sh/33god/projects/15258893-0206-4e8f-aea6-340eb217988c/issues/0f4ac87a-1b03-4921-9a28-75cd3f9bb9f6
- 33GOD-50 — UUID `f0d196c5-6634-45fc-9655-f58deb9ccb53`  
  https://plane.delo.sh/33god/projects/15258893-0206-4e8f-aea6-340eb217988c/issues/f0d196c5-6634-45fc-9655-f58deb9ccb53
- 33GOD-44 — UUID `4d839ffa-224e-40d5-b848-b92786e93d40`  
  https://plane.delo.sh/33god/projects/15258893-0206-4e8f-aea6-340eb217988c/issues/4d839ffa-224e-40d5-b848-b92786e93d40
- 33GOD-45 — UUID `8f53bd7f-2bf4-4392-89c8-57f4f06663e1`  
  https://plane.delo.sh/33god/projects/15258893-0206-4e8f-aea6-340eb217988c/issues/8f53bd7f-2bf4-4392-89c8-57f4f06663e1
- 33GOD-46 — UUID `a30da9a5-9d77-4a6a-8185-da863a48b01d`  
  https://plane.delo.sh/33god/projects/15258893-0206-4e8f-aea6-340eb217988c/issues/a30da9a5-9d77-4a6a-8185-da863a48b01d
- 33GOD-47 — UUID `a48940c0-0d8c-47ad-be8e-88ab28282e83`  
  https://plane.delo.sh/33god/projects/15258893-0206-4e8f-aea6-340eb217988c/issues/a48940c0-0d8c-47ad-be8e-88ab28282e83
- 33GOD-48 — UUID `61fe643a-d89f-4f74-a601-858b7bee7284`  
  https://plane.delo.sh/33god/projects/15258893-0206-4e8f-aea6-340eb217988c/issues/61fe643a-d89f-4f74-a601-858b7bee7284
- 33GOD-49 — UUID `f57bff57-a557-4507-a6b6-e620bcf806d3`  
  https://plane.delo.sh/33god/projects/15258893-0206-4e8f-aea6-340eb217988c/issues/f57bff57-a557-4507-a6b6-e620bcf806d3

## Plan coverage

| Approved-plan capability | Owning story |
|---|---|
| Bloodbank/n8n command primitive, complete schema validation, fleet route selection | 33GOD-43 |
| Enforced memoryless Hermes turn, required project skills/context, target-scoped execution idempotency | 33GOD-50 |
| Contractor JSON Schema, Board Cranker skill/catalog, versioned manifests and receipts | 33GOD-44 |
| `ticket.fortify` vertical tracer through the real Plane/n8n/Bloodbank path | 33GOD-45 |
| Pjangler plan/apply/status/disable, profile projection, hourly cron reconciliation, legacy-loop exclusion | 33GOD-46 |
| One-ticket hourly crank and shared WIP=1 | 33GOD-47 |
| Start date, QA pass/fail/retry, proof-backed completion and compensation | 33GOD-48 |
| Skillex vendoring, template/submodule parity, live 33GOD pilot and convergence | 33GOD-49 |

## Live verification

Verified by Plane read-back on 2026-09-02:

- Parent relation: all eight stories have parent UUID `bbbc84c2-5661-47c7-a686-a16d1659e601`.
- Descriptions: every story includes business goal, scope, non-goals, enumerated/testable acceptance criteria with FR references, likely owning files, dependency, required tests/live evidence, and metadata contract.
- Priority: epic and all eight stories are native `high`.
- Assignment: empty on epic and all stories.
- Start date: null on epic and all stories.
- Cycle: no current or upcoming cycle exists; all remain unset.
- Labels: empty; no label soup duplicates native fields.
- Modules: verified against live module membership. 33GOD-43 is Event Bus; 33GOD-50 is Gateways and Control Planes; 33GOD-44/45/47/48 are Project and Ticketing Lifecycle; 33GOD-46 is Project Bootstrapping & Management; 33GOD-49 is Agent Configuration and Normalization.
- State: 33GOD-43 alone is Todo; every dependent story and the parent remain Backlog.
- Native dependency relation: unavailable. The self-hosted Plane relation endpoint returned HTTP 404. Predecessor IDs are explicit in descriptions and in this artifact; no native relation was fabricated.

## WIP reconciliation before implementation

Plane showed three unrelated items in In Progress: 33GOD-33, 33GOD-35, and 33GOD-36. No matching worker or 33GOD worktree existed.

- Repository handbacks and decision events prove 33GOD-33 and 33GOD-35 were independently accepted.
- 33GOD-36 has a completed implementation handback and test evidence, but no independent review/acceptance artifact.
- All three were moved to E2E Testing & QA with truth-check comments, not Done.

Decision event: `2fe4adce-ff65-4556-9b8a-75a29a9f9c38`.

The implementation WIP slot is therefore free. E2E Testing & QA is review work, not an active implementation lease.

## First executable story

33GOD-43 is the sole dependency-unblocked implementation story. It is small enough to review independently and explicitly excludes the stateless Hermes execution work now owned by 33GOD-50.

Required gate before claiming completion:

1. Implement in a clean isolated Bloodbank worktree using strict RED→GREEN TDD.
2. Capture base/head SHAs and the exact RED and GREEN test outputs.
3. Run focused n8n tests plus `npm test`, schema validation, schema smoke, and command smoke.
4. Pass a fresh specification reviewer.
5. Pass a different fresh quality/security reviewer.
6. Merge, push, and verify no unpushed work before 33GOD-50 becomes unblocked.

## Blockers and cautions

- The current n8n publisher validates required fields but does not yet perform complete JSON Schema validation.
- The invocation schema currently permits missing/null prompt while the gateway requires a non-empty prompt.
- The publisher has event-only envelope construction despite generated command schema discovery.
- Do not hand-edit generated schema output.
- Do not infer successful publication from a hand-built command; the n8n publisher itself must build and reject envelopes correctly.
- 33GOD-50 remains blocked until 33GOD-43 passes both independent review gates.
