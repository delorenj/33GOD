# PRD Reconciliation — LiteLLM Agent Control Plane

**Parent PRD:** [`PRD.md`](../../../PRD.md)
**Date:** 2026-08-13
**Status:** Reconciled planning baseline — Stage 0 complete; implementation gates unresolved

## 1. What changed

The root PRD was already updated to include ACP as part of the component
inventory and FR16 ("Normalized agent sessions and research custody").
This reconciliation confirms that FR16's acceptance criteria are complete,
boundaries correct, and non-goals preserved.

## 2. FR16 — Normalized agent sessions and research custody

**FR16 text (from PRD.md lines 467-490):**

> The platform must support a gated normalized session broker and searchable
> research corpus without moving canonical ownership into either system.

**Seven acceptance criteria — all confirmed:**

| AC | Criterion | Status | Notes |
|----|-----------|--------|-------|
| FR16-AC1 | ACP deployed only as pinned, protected, removable lab service until managed-agent adapter passes gates | CONFIRMED | Stage 1 isolation requirement in integration doc §Security gates |
| FR16-AC2 | Permanent identity remains in .project.json, PJangler, Hermes fleet; ACP owns only disposable runtime/session identity | CONFIRMED | Integration doc ownership table; non-goal §2 |
| FR16-AC3 | Managed ACP publishes schema-valid `bloodbank.v1.agent.invocation.start` commands through fleet-shared gateway using `data.target_agent_id`, correlation, idempotency | CONFIRMED | Integration doc §Managed Hermes adapter contract |
| FR16-AC4 | Assistant text/artifacts return through governed correlated Bloodbank message before ACP chat complete | CONFIRMED | Known gap; integration doc §lines 148-153 |
| FR16-AC5 | DeLoNET LiteLLM retains every provider credential and fallback rule; ACP gets only scoped virtual key | CONFIRMED | Integration doc §Model and credential policy |
| FR16-AC6 | Hindsight durable memory, Candystore durable audit, Holocene mission control, DeLoHQ bounded executive controls | CONFIRMED | Ownership table preserved |
| FR16-AC7 | OpenNotebook project corpus indexes canonical sources with provenance, never ingests secrets or becomes decision record | CONFIRMED | Integration doc §Knowledge custody |

## 3. New or impacted functional requirements

**FR8 (Event backbone) — ASSISTANT-MESSAGE GAP IDENTIFIED:**
FR8 requires all inter-service communication through NATS JetStream. The known
`bloodbank.v1.conversation.message.appended` gap means the assistant result path
for ACP turns does not yet exist. This is recorded as a Bloodbank dependency
(see [Dependency Ledger](dependency-and-ownership-ledger.md)).

**FR10 (Skill hub) — AFFECTED:**
ACP references approved tools from Pipeline MCP Hub and Skillex. No new skill
is required for Stage 0. The `33god-hermes` adapter may require a Bloodbank
integration skill update when Stage 2 is reached.

**FR9 (Mission control) — AFFECTED:**
Holocene will consume ACP health and session state in Stage 3. No Holocene
changes required before that stage.

## 4. MVP plan impact

Phase 5 ("Add director-grade operations") already includes the ACP item:

> *Run the ACP isolated lab and managed-Hermes adapter spike after BMAD
> alignment; project only approved session health into Holocene and bounded
> approvals/status into DeLoHQ.*

No MVP phase change is needed. ACP work fits within Phase 5 with Stage 0-4
sequencing.

## 5. Non-functional requirements — no change

All eight NFRs from the root PRD (private source, local-first, cloud-blocked,
idempotent, fail-open hooks, source-of-truth clarity, no hidden runtime dirt,
observable gates, secret hygiene) remain unchanged. ACP does not weaken any NFR.

## 6. Open issues — no new issues

The root PRD's eight open issues are unchanged. Open issue 8 ("Run the ACP BMAD
alignment and isolated pilot") is the direct parent of this work.

## 7. FR Coverage Map (ACP-specific)

| FR | Covered by | ACP-specific treatment |
|----|-----------|----------------------|
| FR1 (Registry) | components.yaml | ACP NOT added until gates satisfied |
| FR4 (Runtime isolation) | Mounted volumes | ACP has its own DB, no runtime tracked |
| FR8 (Event backbone) | Bloodbank NATS | Adapter publishes canonical commands |
| FR9 (Mission control) | Holocene | Stage 3 consumes ACP session data |
| FR10 (Skill hub) | 33god-hub | No new skill needed for Stage 0 |
| FR12 (Ticket lifecycle) | Krebs | ACP consumes normalized state only |
| FR16 (ACP) | This reconciliation | Planned coverage via ACP-E0 through ACP-E6; all work is traceable through `33GOD-4`–`33GOD-32`; implementation remains gated |
