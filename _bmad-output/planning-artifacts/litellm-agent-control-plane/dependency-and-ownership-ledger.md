# Dependency and Ownership Ledger — LiteLLM Agent Control Plane

**Date:** 2026-08-13
**Status:** Reviewed planning baseline — Stage 0 complete; downstream dependency gates unresolved

---

## 1. Ownership Table

Every concern has exactly one canonical owner. ACP's relationship is documented
for each. This table is adapted from the integration decision document and
reproduced here for traceability.

| ID | Concern | Canonical owner | ACP relationship | Boundary rule |
|----|---------|----------------|------------------|---------------|
| OWN-1 | Product intent, architecture, epics, stories | Git + BMAD artifacts | Reads approved definitions; never becomes product record | AD-ACP-8 |
| OWN-2 | Project, board, permanent agent identity | `.project.json` + PJangler | Read-only projection; no duplicate permanent identities | AD-ACP-2 |
| OWN-3 | Ticket lifecycle | Krebs | Consumes normalized work state; no private state machine | FR12 |
| OWN-4 | Workforce hierarchy, delegation policy | Flume (planned) | Execution port beneath Flume; no competing org model | AD-ACP-7 |
| OWN-5 | Fleet profiles, host lifecycle | Hermes fleet registry + systemd | Calls registered profiles; no per-agent ACP consumer or scheduler | AD-ACP-1 |
| OWN-6 | Command ingress, event contracts | Bloodbank | Translates ACP turns into canonical commands; consumes correlated events | AD-ACP-3 |
| OWN-7 | Durable event history | Candystore | ACP holds only session projection/cache | AD-ACP-6 |
| OWN-8 | Durable agent memory | Hindsight | ACP memory is optional session-local scratch only | AD-ACP-6 |
| OWN-9 | Models, provider credentials, budgets, fallbacks | DeLoNET LiteLLM | Uses scoped virtual key and stable gateway aliases | AD-ACP-5 |
| OWN-10 | Tool and skill distribution | Pipeline MCP Hub, Skillex, project manifests | References approved tools; no duplicate source of truth | FR10 |
| OWN-11 | Operator mission control | Holocene | Supplies runtime/session data to existing control surface | AD-ACP-1 |
| OWN-12 | Mobile executive surface | DeLoHQ (Holocene `/hq`) | Status, approvals, exceptions, budgets, coarse controls only | AD-ACP-1 |
| OWN-13 | Research corpus and synthesis | OpenNotebook | Searchable read model over canonical sources; never authoritative | AD-ACP-8 |

## 2. Cross-Component Dependency Graph

```
ACP → Bloodbank (command publication, event consumption)
    → Candystore (event persistence, trace query)
    → DeLoNET LiteLLM (model requests via scoped key)
    → Hermes fleet (target profile routing via data.target_agent_id)
    → Holocene (health/session data projection — Stage 3)
    → DeLoHQ (approval/exception surface — Stage 3)
    → Flume (execution port — Stage 4; Flume has no repo yet)
    → Hindsight (memory boundary — verification only, not integration)

ACP ← PJangler (permanent identity boundary — ACP reads nothing from PJangler directly)
ACP ← .project.json (identity boundary — ACP reads nothing)
ACP ← Krebs (ticket boundary — ACP consumes nothing directly)
ACP ← Skillex (tool boundary — ACP references nothing directly)
ACP ← Pipeline MCP Hub (tool boundary — deferred to later stages)
```

## 3. Stage Dependency Table

| Stage | Key | Depends on | Owner | Story |
|-------|-----|------------|-------|-------|
| 0 | BMAD Alignment + Plane traceability | Complete on active `33GOD Platform` board: `33GOD-4`–`33GOD-32`; 29 items and 28 parent links verified | 33god-pm | ACP-E0.1 |
| 1 | Isolated Lab | Stage 0 | 33god-platform | ACP-E1.1 through E1.5 |
| 1a | Scoped LiteLLM key | Stage 1 (ACP running) | 33god-platform | ACP-E1.3 |
| 2 | Bloodbank Bridge | Stage 1, Bloodbank schema, Fleet gateway | 33god-platform (Bloodbank) | ACP-E2.1 through E2.5 |
| 2a | Assistant response contract | Stage 2, Bloodbank schema work, Candystore review | Bloodbank | ACP-E2.3 |
| 3 | Operator Projections | Stage 2, Candystore correlation | Holocene | ACP-E3.1 through E3.3 |
| 4 | Flume Execution Port | Stage 3, Flume repository/contract | Flume (planned) | ACP-E6.1 through E6.3 |
| X | Identity verification | Stage 1+ | 33god-platform | ACP-E4.1, E4.2 |
| X | Memory/audit verification | Stage 2+ | Hindsight, Candystore | ACP-E5.1, E5.2 |

## 4. External Dependencies

| Dependency | Type | Version/Ref | Owner | Status |
|------------|------|-------------|-------|--------|
| LiteLLM Agent Control Plane upstream | Open source | Candidate: 53bfd20e2fec51fc8f665fb614512c6b138367da | LiteLLM Labs | Pending security review |
| DeLoNET LiteLLM gateway | Self-hosted | GHCR image, latest stable | DeLoNET | Operational |
| Bloodbank Hermes gateway | Self-hosted | bloodbank@d894ee8f | 33GOD | Operational |
| Bloodbank invocation schema | Self-hosted | `bloodbank.v1.agent.invocation.start.v1` | 33GOD | Operational; gap in assistant message path |
| Candystore | Self-hosted | `03abfe0b62` (baseline) | 33GOD | Operational; needs consumer review for ACP-E2.3 |
| Holocene | Self-hosted | `4fd42681e7` (baseline) | 33GOD | Operational; Stage 3 target |
| OpenNotebook | Self-hosted | notebook:5n0x8mn63mvijhj7b2zl | 33GOD | Operational; no embeddings, no model provider |
| PostgreSQL | Infrastructure | ACP's own DB | 33GOD | To be provisioned in Stage 1 |

## 5. Required Skills and Tools

| Skill/Tool | Owner | Used for |
|-----------|-------|----------|
| `agent-fleet-operations` | PJangler | Fleet profile management; ACP calls registered profiles |
| Bloodbank CDP | Bloodbank | Schema validation, subject naming |
| Platform validate/compose | 33god-platform | Validation gates before/after ACP deployment |
| forever-ago | 33god-platform | Candidate backup mechanism; classification and successful restore test block Stage 2 |

## 6. Known Gaps

| Gap | Impact | Resolution path | Story |
|-----|--------|----------------|-------|
| `bloodbank.v1.conversation.message.appended` not published by fleet gateway | ACP chat cannot complete; no canonical assistant result path | Bloodbank contract work, Candystore and Holocene consumer review | ACP-E2.3 |
| ACP upstream revision may change | Deployed pin may diverge from planning assumption | Refresh pin before Stage 1; re-run security review | ACP-E1.1 |
| Flume has no repository or contract | ACP-E6 is design-only; no implementation possible | Flume must have real repo before Stage 4 | ACP-E6 |
| HeyMa missing Compose manifest | Platform validation RED on unrelated component | HeyMa-own work; ACP does not repair | N/A (recorded) |
| OpenNotebook receipt may become stale after canonical-source changes | Research read model can silently diverge from Git/BMAD truth | Compare source revisions and re-ingest stale sources before Stage 1, or record a blocking exception | ACP-E0.1 |

## 7. Resolved Stage 0 Preconditions

| Precondition | Resolution | Evidence |
|--------------|------------|----------|
| Plane binding | `.project.json` and the PM role now target workspace `33god`, project `33GOD Platform` (`15258893-0206-4e8f-aea6-340eb217988c`) | `33god-platform/knowledge/33god-pm-litellm-acp-dispatch.yaml` |
| Work hierarchy | `33GOD-4` initiative container, 7 epics, 21 stories; 28/28 non-root parent links verified by readback | Dispatch receipt item ledger |
| Credential boundary | Adapter resolves only `PLANE_33GOD_API_KEY` from runtime dotenv data; the receipt contains no credential material | Plane adapter and dispatch receipt |
