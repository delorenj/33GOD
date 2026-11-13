# PRD Quality Review — I-9: Change crank from one feature hub

## Overall verdict

**Adequate for a review draft, not yet a complete-path acceptance baseline.** The thesis, owner boundaries, constrained first increment and evidence honesty closely match the delegated product input without inventing a general platform. Two acceptance gaps matter downstream: the I-8 proof can be called complete while skipping existing I-8 seam conditions, and the promised repeatable procedure is not yet concrete enough for a fresh agent to perform independently. Neither finding authorizes a live test in this planning pass.

## Decision-readiness — adequate

The draft states what is chosen and what is relinquished: one hub instead of code consolidation or a universal orchestrator (§§1, 5, lines 49–54, 263–282); manual agent-executable handoffs instead of mandatory automation (FR-4, lines 154–167); and explicit escalation without new release authority (FR-5, lines 169–184). It correctly attributes direct versus delegated input (§0, lines 22–34). Its open architecture questions are real (§8, lines 314–330), but acceptance needs tightening before architecture can confidently implement the gate.

## Substance over theater — strong

One operator, coordinating agents and component owners are functional roles, not decorative personas (§2, lines 56–73). NFRs are specific to ownership, binding safety and evidence (§6, lines 284–297). The thesis is distinctive to crank and its fragmented ownership (§1, lines 40–54); no market or innovation claims are padded into this internal-tool PRD.

## Strategic coherence — strong

The progression is discover → map → reuse/delegate → prove → resume (FR-1–9, lines 106–261), consistent with the first-increment scope and deferrals (§5, lines 263–282). Success measures include adverse observations and establish a baseline instead of inventing savings (§7, lines 299–312). The existing I-8 outcome is a focused first proof, not a mandate to complete all I-9 foundation migration (§5, lines 276–279).

## Done-ness clarity — thin

FR-1–5 and FR-7–9 mostly specify inspectable consequences, including stale references, owner-linked failures and revision-bound claims (lines 108–184, 212–261). FR-6 is admirably strict about zero unintended input and observed delivery, but its gate and the promised independent execution need two clarifications.

### Findings

- **High — Reconcile the I-8 complete-path gate** (PRD FR-6, lines 195–210; §7, lines 304–312; source `initiatives.md` I-8, lines 475–496) — The draft's passing scenarios cover rename and process replacement, but existing I-8 seam acceptance also names pane movement between tabs, rediscovery after Zellij restart, a pane with no agent process, and an independent ASM/process-session check. As written, SM-2 plus §7 could report I-8 complete without observing those established conditions. *Fix:* Reconcile FR-6/SM-2 with I-8's existing gate: include the required seam observations in this proof, or explicitly label which are linked, already evidenced at exact applicable revisions and conditions, and which remain unproven. Keep I-8's owner backlog and cap-lift authority where they already live; do not turn this into an all-of-I-9 migration requirement.
- **High — Make the acceptance procedure executable by a fresh agent** (PRD FR-6, lines 188–210; FR-7, lines 212–228; FR-9, lines 246–261; §8, lines 320–325) — The PRD promises a repeatable procedure but currently specifies scenarios and a future architecture decision about observation, not the minimum run protocol. A fresh agent cannot yet tell how to establish a permitted target, distinguish actual input from eligibility, observe zero input for each negative target, or record an unobservable scenario as unproven. *Fix:* Require the hub's eventual procedure to name prerequisites/authorization, scenario setup and resets, positive and negative observation points, expected versus observed results, stop/fail criteria, evidence locations and revision/config capture. Architecture may choose the concrete surfaces; this review does not call for running probes or inventing fixtures now.

## Scope honesty — strong

The deferrals are explicit and match the delegated minimum (§5, lines 263–282). Planning-only authority is distinguished from source policy: `addendum.md` lines 22–25 records main-first source policy, whereas PRD §0 lines 14–20, FR-5 lines 182–184, §5 lines 280–282 and §8 lines 332–335 explicitly withhold merge, deployment, live input and cap change from this review. The requirement for *future* explicitly opted-in live proof is not present permission to target panes (FR-6, lines 190–210). There are no hidden product assumptions that need a fabricated assumption tag.

## Downstream usability — adequate

The glossary differentiates hub, owner, contract, integrated acceptance and evidence (§3, lines 75–99), and FRs are separable enough for architecture. FR-2's named owner classes are helpful but can underspecify the actual path that FR-9 promises a new agent can traverse.

### Findings

- **Medium — Make execution dependencies part of the owner-map test** (PRD FR-2, lines 122–135; FR-9, lines 253–259; source `features.toml` lines 49–58 and `initiatives.md` I-8, lines 457–473) — FR-2 explicitly lists crank, ASM, terminal-driver and pj, then relies on “any additional owner actually required.” The catalog's crank dependency list also names `agent.job` and `clock`, and the existing I-8 delegation includes Candybar economics handling. A map that omits the existing dispatch/clock chain could satisfy the four-item list while leaving a fresh agent unable to explain the real end-to-end result or the unchanged cap. *Fix:* Require the map review to trace the first proof from selection through dispatch, eligibility, terminal input and evidence, linking each participating owner/contract or labeling a currently absent interface as a gap. Reuse catalog and I-8 links rather than adding a new owner table or duplicating tickets.

## Shape fit — strong

This is a proportionate capability spec for a solo operator's brownfield cross-repository tool (§§1–2, lines 40–73). No synthetic UJs, enterprise sign-offs or time/percentage targets are needed; the fresh-agent exercise is more probative than persona prose (FR-9, lines 246–261). Existing and target interfaces are expressly distinguished (§3, lines 88–94; FR-1/2, lines 108–135).

## Mechanical notes

- Local Markdown links in §9 resolve to existing files. FR-1–9, NFR-1–4 and SM-1–3 are each contiguous and unique; no unresolved requirement-ID cross-reference was found.
- Glossary terms are substantially stable; “complete-path,” “integrated” and “I-8 proof” should be read against the same reconciled gate noted above, not treated as three independent passes.
- There are no inline `[ASSUMPTION]` tags or Assumptions Index entries to round-trip, and no UJs; neither is a defect for this directly/delegated-input, single-operator capability spec. No `[NOTE FOR PM]` is necessary merely to decorate the draft: the real tensions are in §8.
- Mechanical inspection only; no tests, live probes, board updates or runtime actions were performed.
