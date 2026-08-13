# Evidence and Decision Ledger — LiteLLM Agent Control Plane

**Date:** 2026-08-13
**Status:** Reviewed planning evidence — Stage 0 traceability complete

---

## 1. Decision Record

Every architectural decision (AD) from the architecture spine is recorded here
with its rationale, source, and verification evidence.

| AD ID | Decision | Rationale | Source | Verification |
|-------|----------|-----------|--------|-------------|
| AD-ACP-1 | ACP is removable subordinate broker | Prevents ACP being treated as permanent infrastructure; FR16 specifically requires removability | Integration doc §Decision, §Ownership boundaries | ACP-E1.5 shutdown independence test |
| AD-ACP-2 | No permanent identity in ACP | .project.json, PJangler, and Hermes fleet registry are permanent identity authorities; ACP must not create a second source of truth | Integration doc §Ownership table; FR16-AC2 | ACP-E4.1 verification story |
| AD-ACP-3 | One canonical command per ACP turn | Prevents partial/multiple/invalid commands; ensures idempotency and correlation | Integration doc §Managed Hermes adapter contract; FR16-AC3 | ACP-E2.1 adapter implementation |
| AD-ACP-4 | Assistant result is governed Bloodbank contract | ACP chat not complete without canonical result path; prevents ACP becoming the reply authority | Integration doc lines 148-153; FR16-AC4 | ACP-E2.3 gap resolution |
| AD-ACP-5 | DeLoNET LiteLLM is sole credential owner | Prevents credential proliferation; LiteLLM owns model routing and fallback policy | Integration doc §Model and credential policy; FR16-AC5 | ACP-E1.3, ACP-E4.2 |
| AD-ACP-6 | Hindsight is durable memory owner | Prevents memory fragmentation; Candystore for audit, Hindsight for memory, ACP for session-local scratch | Integration doc §Ownership table; FR16-AC6 | ACP-E5.1, ACP-E5.2 |
| AD-ACP-7 | Flume owns hierarchy/delegation | Prevents ACP developing an org model; Flume is the planned delegation authority | Integration doc §Ownership table | ACP-E6.1 mapping contract |
| AD-ACP-8 | OpenNotebook is read model only | Prevents notebook output being treated as authoritative; Git/BMAD are truth | Integration doc §Knowledge custody; FR16-AC7 | ACP-E0 (this artifact) |
| AD-ACP-9 | Stage-gated progression | Prevents deploying capabilities without prior gate evidence; each stage requires prior completion | Integration doc §Pilot plan | Stage 0 receipt: `33GOD-4`–`33GOD-32`; later stages remain gated |
| AD-ACP-10 | Honest platform validation baseline | Prevents ACP claiming to repair unrelated failures; HeyMa RED is pre-existing | Integration doc §Acceptance criteria (line 316) | §4 of readiness assessment |

## 2. Evidence Sources

| Reference | Type | SHA/Revision | Relevance |
|-----------|------|-------------|-----------|
| [`33god-platform/docs/litellm-agent-control-plane-integration.md`](../../../33god-platform/docs/litellm-agent-control-plane-integration.md) | Canonical decision document | `d9997a9fdc750ee239911789acb765b94e0e9536` (root revision) | Primary source for ownership boundaries, pilot plan, security gates, success criteria |
| [`PRD.md`](../../../PRD.md) | Canonical product PRD | `d9997a9fdc750ee239911789acb765b94e0e9536` (root revision) | FR16 requirements; component inventory; Phase 5 ACP mention |
| [`33god-platform/docs/product-map.md`](../../../33god-platform/docs/product-map.md) | Product card map | `d9997a9fdc750ee239911789acb765b94e0e9536` (root revision) | ACP as planned integration boundary; integration layer description |
| [`33god-platform/knowledge/open-notebook-33god.yaml`](../../../33god-platform/knowledge/open-notebook-33god.yaml) | Notebook custody receipt | `d9997a9fdc750ee239911789acb765b94e0e9536` (root revision) | Source list (11 sources), processing state, custody rules |
| [`33god-platform/knowledge/33god-pm-litellm-acp-dispatch.yaml`](../../../33god-platform/knowledge/33god-pm-litellm-acp-dispatch.yaml) | PM dispatch and Plane receipt | Current planning package | Bloodbank lineage; active board binding; 29 real work items; verified hierarchy |
| [`architecture.md`](../architecture.md) | Parent architecture spine | `d9997a9fdc750ee239911789acb765b94e0e9536` (root revision) | Inherited invariants AD(platform/1-9); project context analysis |
| [Bloodbank Hermes gateway contract](https://github.com/delorenj/bloodbank/blob/4f394a4c9b145549ae2e4eeb9ff150fa5afa1aa9/services/hermes-gateway/README.md) | Fleet gateway contract; canonical URL at root-pinned submodule revision because submodule is uninitialized locally | `bloodbank@4f394a4c9b` | Command routing, gateway behavior, subscription model; local link not verified in this worktree |
| [Bloodbank invocation schema](https://github.com/delorenj/bloodbank/blob/4f394a4c9b145549ae2e4eeb9ff150fa5afa1aa9/schemas/bloodbank/v1/agent/invocation.start.v1.json) | Command schema; canonical URL at root-pinned submodule revision because submodule is uninitialized locally | `bloodbank@4f394a4c9b` | Schema validation for ACP adapter commands; local link not verified in this worktree |
| [PJangler fleet operations contract](https://github.com/delorenj/pjangler/blob/46e1b44cd3189e061be7eb0631b2f3814bfa7f6e/skills/agent-fleet-operations/SKILL.md) | Fleet operations contract; canonical URL at root-pinned submodule revision because submodule is uninitialized locally | `pjangler@46e1b44cd3` | Profile lifecycle, target agent routing; local link not verified in this worktree |
| ACP upstream repository | External | Candidate: `53bfd20e2fec51fc8f665fb614512c6b138367da` | Reference architecture, runtime SDK, Hermes template |
| [Holocene org model](https://github.com/delorenj/holocene/blob/4fd42681e7e878f34b41f881713b0173bb08957a/packages/org-model/src/index.ts) | Implementation; canonical URL at root-pinned submodule revision because submodule is uninitialized locally | `holocene@4fd42681e7` | Org hierarchy consumed by Flume/ACP; local link not verified in this worktree |
| DeLoNET LiteLLM gateway policy | External (delorenj/docker) | `586c4a1ace2e4` | LiteLLM gateway configuration, virtual key model |
| OpenNotebook (`notebook:5n0x8mn63mvijhj7b2zl`) | Live service | N/A (live) | 11-source corpus; authentication-gated |

## 3. Security Gate Mapping (from Integration Decision)

The 10 required security gates from the integration decision document are mapped
to epics/stories:

| # | Gate | Mapped to | Verification |
|---|------|-----------|-------------|
| 1 | Pin upstream commit or immutable image digest | ACP-E1.1 | Pin SHA in deployment config |
| 2 | Dedicated ACP database and internal service hostname | ACP-E1.2 | Separate PostgreSQL; internal-only DNS |
| 3 | Browser and API routes behind existing DeLoNET access boundary | ACP-E1.2 | Internal hostname, no public exposure |
| 4 | No ACP runtime-harness administration exposed to untrusted networks | ACP-E1.2 | Network isolation; internal-only |
| 5 | Provider secrets in DeLoNET LiteLLM; scoped virtual key only | ACP-E1.3, ACP-E4.2 | Scoped key verification |
| 6 | ACP session metadata free of repo secrets and full env dumps | ACP-E1.3 | Bounded `data.context`; no env injection |
| 7 | Command/session correlation in Bloodbank and Candystore | ACP-E2.1, ACP-E2.2, ACP-E2.5 | Correlation IDs in every command/event |
| 8 | Classify ACP data, implement the required backup path, and pass restore testing | Blocking pre-Stage-2 gate | BR-1 must pass before ACP-E2 begins |
| 9 | Complete security review before ACP can trigger a permanent fleet profile | ACP-E1.1, ACP-E4 | Security review document |
| 10 | Kill switch that disables adapter without touching fleet-shared gateway | ACP-E1.5 | Shutdown independence test; adapter kill switch |

## 4. OpenNotebook Custody Receipt

The deterministic project notebook `33GOD - Platform Architecture and Control Plane`
(`notebook:5n0x8mn63mvijhj7b2zl`) began with this 11-source corpus:

| Source | Authority | Ingestion status |
|--------|-----------|-----------------|
| ACP integration decision (2026-08-13) | canonical | Completed |
| 33GOD root PRD (2026-08-13) | canonical | Completed |
| 33GOD BMAD architecture snapshot | canonical-bmad | Completed |
| 33GOD platform product map | canonical-projection | Completed |
| Bloodbank Hermes gateway contract | canonical-component-contract | Completed |
| Bloodbank agent invocation schema v1 | canonical-schema | Completed |
| Hermes fleet operations contract | live-operations-contract | Completed |
| Holocene org model implementation | live-implementation | Completed |
| DeLoNET LiteLLM gateway policy | canonical-stack-policy | Completed |
| Flume PRD (vault snapshot) | historical-design-input | Completed |
| Flume and Yi architecture (vault snapshot) | historical-design-input | Completed |

**Custody status:**
- All sources completed processing: ✅
- Embeddings enabled: ❌ (no configured model provider)
- Configured model providers: 0
- Secret ingestion: ⛔ Forbidden

**Freshness acceptance gate:** Before Stage 1, compare every canonical source's
current revision with this custody receipt. Any mismatch requires re-ingestion and
a new completed receipt; if re-ingestion cannot complete, record an explicit
blocking exception. Historical “Completed” status alone does not prove freshness.

The reviewed BMAD expansion is exactly these nine additional read-model sources:

1. `.memlog.md`
2. `product-brief-delta.md`
3. `prd-reconciliation.md`
4. `ARCHITECTURE-SPINE.md`
5. `epics-and-stories.md`
6. `implementation-readiness-assessment.md`
7. `dependency-and-ownership-ledger.md`
8. `evidence-and-decision-ledger.md`
9. `33god-platform/knowledge/33god-pm-litellm-acp-dispatch.yaml`

Completed source IDs, content hashes, revisions, and aggregate source count belong
only in `33god-platform/knowledge/open-notebook-33god.yaml`; this narrative ledger
must not be used as a live notebook receipt.

## 5. Stage 0 Plane Traceability Evidence

- Active binding: workspace `33god`, project `33GOD Platform`, identifier `33GOD`,
  UUID `15258893-0206-4e8f-aea6-340eb217988c`.
- `33GOD-4` is the ordinary-issue initiative container required by this older
  Plane deployment, which does not expose native initiative/work-item-type APIs.
- Seven epic issues and 21 story issues occupy `33GOD-5` through `33GOD-32`.
- The PM-authored dispatcher used exact stable-key-prefixed titles as idempotency
  keys, then read every issue back from Plane.
- All 28 requested epic/story parent links were accepted and verified; no
  description-only fallback was needed.
- Bloodbank thread `bmad:33god:litellm-acp`, correlation
  `c46b02ea-6175-5743-8fef-fa75e5d7dd6f`, and terminal planning stream sequence
  `1365` preserve the delegation lineage.
- The authoritative item-by-item IDs and disposition are in the machine-readable
  [dispatch receipt](../../../33god-platform/knowledge/33god-pm-litellm-acp-dispatch.yaml).

## 6. Planning Artifact Inventory

| Artifact | Path | Status |
|----------|------|--------|
| `.memlog.md` | `.memlog.md` | ✅ Current through adversarial review |
| `product-brief-delta.md` | `product-brief-delta.md` | ✅ Reviewed planning baseline |
| `prd-reconciliation.md` | `prd-reconciliation.md` | ✅ Reconciled |
| `ARCHITECTURE-SPINE.md` | `ARCHITECTURE-SPINE.md` | ✅ Reviewed planning baseline |
| `epics-and-stories.md` | `epics-and-stories.md` | ✅ 7 epics / 21 stories; Plane-linked |
| `implementation-readiness-assessment.md` | `implementation-readiness-assessment.md` | ✅ Stage 0 assessed complete; deployment still gated |
| `dependency-and-ownership-ledger.md` | `dependency-and-ownership-ledger.md` | ✅ Reviewed planning baseline |
| `evidence-and-decision-ledger.md` | `evidence-and-decision-ledger.md` | ✅ Current evidence ledger |
| PM / Plane dispatch receipt | `../../../33god-platform/knowledge/33god-pm-litellm-acp-dispatch.yaml` | ✅ 29 items; 28 parent links verified |

## 7. ACP Candidate Revision Record

- **Decision date inspected:** 2026-08-13
- **Upstream candidate:** `53bfd20e2fec51fc8f665fb614512c6b138367da`
- **Root repo:** `797cf0098b27cae1434baceb66bb5d880f98bb9c` (origin/main baseline)
- **Worktree:** `.worktrees/33gpm-litellm-acp-planning/`

**Important:** The pinned ACP revision must be refreshed and re-reviewed before
any Stage 1 deployment. The candidate SHA is the revision inspected during
planning; the upstream may have moved since.
