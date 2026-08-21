# Product Brief Delta — LiteLLM Agent Control Plane (ACP)

**Status:** Approved planning baseline — Stage 0 traceability complete; implementation gated
**Parent baseline:** [`33GOD PRD`](../../../PRD.md)
**Reconciliation date:** 2026-08-13
**Decision document:** [`33god-platform/docs/litellm-agent-control-plane-integration.md`](../../../33god-platform/docs/litellm-agent-control-plane-integration.md)

## 1. What changed

The 33GOD product brief previously named ACP only as a planned integration
boundary. This delta promotes ACP from "observed external project" to
"approved gated integration with defined ownership boundaries and pilot plan."
The brief's existing twelve-component registry, non-goals, and MVP phases are
unchanged.

## 2. The problem this solves (within 33GOD)

33GOD has no normalized session broker. Each coding-agent runtime (OpenCode,
Claude Code, Codex) negotiates sessions, turns, and streamed output through its
own protocol. Holocene is forced to either implement every agent protocol or
stay blind to live session detail. Flume's hierarchy, delegation, and escalation
model needs an execution port that it does not own and that can be developed
independently.

ACP supplies that port: a lower-level session API (create/resume, send turn,
stream events, normalize runtime state, attach tools, terminate) that Flume
calls without embedding runtime-protocol complexity.

## 3. What ACP is (within 33GOD)

- A pinned, isolated, removable lab service on PostgreSQL.
- A session/runtime broker beneath Flume's delegation model.
- An immediate disposable-agent laboratory for testing runtimes, tools, and models.
- A normalized session projection provider for Holocene and DeLoHQ.

## 4. What ACP is NOT (non-goals, preserved from parent)

- NOT the 33GOD control plane.
- NOT a replacement for Holocene or DeLoHQ.
- NOT a replacement for Flume's org model or delegation.
- NOT a replacement for `.project.json` or PJangler identity.
- NOT a replacement for Bloodbank/Candystore event/audit authority.
- NOT a replacement for Hindsight memory.
- NOT a credential store or model router (DeLoNET LiteLLM remains sole owner).
- NOT a permanent `components.yaml` member until registry gates are satisfied.

## 5. Key boundary rules (inherited from parent brief)

| Concern | Canonical owner | ACP role |
|---------|----------------|----------|
| Project identity | `.project.json` + PJangler | Read-only projection |
| Ticket lifecycle | Krebs | Consumes normalized state |
| Workforce hierarchy | Flume | Execution port beneath |
| Event contracts | Bloodbank | Translates turns to commands |
| Audit history | Candystore | Session projection/cache only |
| Agent memory | Hindsight | Session-local scratch only |
| Model credentials | DeLoNET LiteLLM | Scoped virtual key only |
| Mission control | Holocene | Supplies runtime/session data |
| Executive surface | DeLoHQ (Holocene `/hq`) | Bounded controls only |
| Research corpus | OpenNotebook | Read model only, never authoritative |

## 6. Pilot plan (Stage 0-4, from integration document)

- **Stage 0:** BMAD alignment plus traceable work on the active `33GOD Platform` Plane board. Complete: 1 initiative container, 7 epics, and 21 stories are recorded as `33GOD-4` through `33GOD-32`, with all 28 requested parent links verified. See the [dispatch receipt](../../../33god-platform/knowledge/33god-pm-litellm-acp-dispatch.yaml).
- **Stage 1:** Isolated lab deployment with pinned ACP, separate DB, scoped LiteLLM key.
- **Stage 2:** Canonical Bloodbank bridge (`33god-hermes` adapter, command publication, assistant response contract).
- **Stage 3:** Operator projections in Holocene and DeLoHQ.
- **Stage 4:** Flume execution port mapping work requests onto normalized sessions.

## 7. Success criteria

All criteria from the integration decision document are adopted. Key gates:

- ACP is pinned, isolated, protected, removable.
- No provider credential duplicated outside LiteLLM.
- No permanent identity duplicated outside PJangler/fleet.
- Each turn produces one schema-valid, idempotent Bloodbank command.
- Killing ACP leaves the fleet fully operational.
- Platform validation baseline is recorded honestly (HeyMa red is pre-existing).

## 8. Platform validation note

The current `platform:validate` status for HeyMa is RED due to missing Compose
manifest. This is a pre-existing condition unrelated to ACP. ACP does not claim
to repair it. ACP's own validation status will be evaluated independently when
it satisfies registry gates.

**Linked artifacts:**
- [PRD Reconciliation](prd-reconciliation.md)
- [Architecture Spine](ARCHITECTURE-SPINE.md)
- [Epics and Stories](epics-and-stories.md)
- [Implementation Readiness](implementation-readiness-assessment.md)
- [Dependency & Ownership Ledger](dependency-and-ownership-ledger.md)
- [Evidence & Decision Ledger](evidence-and-decision-ledger.md)
- [33GOD PM / Plane Dispatch Receipt](../../../33god-platform/knowledge/33god-pm-litellm-acp-dispatch.yaml)
