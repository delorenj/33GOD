# I-9 bounded owner-planning and handoff proposals

Date: 2026-11-08. **Proposals only, not sent or accepted work.** Created after
[architecture finalization](reviews/final-gates.md). This is a cross-owner contract
map, not a component backlog, story breakdown, command dispatch or authorization
to implement. All candidate proof/input stays disabled until its gates are met.

## Recommended next BMAD step

Owner-side **`bmad-spec` contract adoption/refinement**, citing stable spine ADs,
then owning PMs link or refine existing work. A spec turns the agreed cross-owner
invariants into the owner's precise capability/error/evidence contract; it does
not claim an API is available. Parent I-9 links outcomes and returned evidence,
never runs child implementation loops or copies their ticket states.

Every proposal below is **unsent / acceptance not established**. Existing work
references are source links, not live board-status claims. No new ticket IDs,
PM addresses, execution enrollment or tool names are invented.

## First proposal: Hermes Fleet native `agent.message`

**Planning owner accepted:** Hermes Fleet. Authority source:
[delegated disposition](route-disposition.md). Consulted owner routes:
[component card](../../../../33god-platform/components/hermes-fleet.yaml),
[template README](../../../../hermes-agent-template/README.md), and the canonical
`agent-fleet-operations` skill, which routes shared workforce contracts to the
**Hermes Agent PM board**, not a consuming repo's board. The card identifies
`hermes-agent-template` as the shared runtime/provisioning contract home; this
is not a decision to put protocol code into a template. The owning PM must select
the actual source package/implementation home within its existing runtime
ownership, not add profile-local logic or another input stack.

**Intake gap:** the inspected template checkout has no root `.project.json`
board binding or declared PM address. Neither the actual board identifier nor
active PM acceptance/enrollment has been established here. Do not guess a
`hermes-agent-template-pm`/`hermes-pm` target, repurpose the unrelated peer who
messaged this session, or send a Bloodbank command as a probe. Under later intake
authority, resolve the shared Hermes Agent PM board/actor through the existing
canonical project/agent bindings and actual enrollment, then request a planning
acceptance receipt. A missing route is an explicit gap, not implied delegation.

**Requested planning outcome:** an owner-supported, capability-gated contract for
native submission to the explicitly selected pane-bound local-Linux Claude
process/session incarnation, consuming ASM identity. Stable spine references:
AD-2–6, AD-8–9, AD-12. Reuse [bounded native findings](delivery-feasibility.md);
do not repeat the broad survey or freeze internal binary offsets as a public API.

Owner contract must resolve, with evidence or explicit unsupported:

- External framing/discovery/auth/receipt semantics and compatibility behavior;
  tested digest records evidence, never becomes a permanent deployment pin.
- Exact connected endpoint/process/native-session protection through asynchronous
  ingress, not only a pre-await UUID check or pathname/PID snapshot.
- Independent receiving-input acceptance observable correlated to stable attempt,
  body and native incarnation. No model-consumption requirement; held status,
  sender success or internal `delivered` naming alone is not sufficient.
- Cooperation with crank's uninterrupted final admission exclusion: no detached
  sender/callback can submit after authority loss. Adapter does not own opt-in,
  eligibility policy or retries.
- Precise zero-submission unsupported/refused outcomes versus possible-submission
  unknown; later-release implications. No terminal fallback or permission changes.

**Existing work:** I-8/I-9 have no native-message ticket linked in the checked
initiative artifact. That is an unverified intake gap, not permission to invent a
new ticket. Owning PM searches/reuses its current work first; any missing work is
created only under later authority and linked back, not duplicated here.

**Expected later return:** accepted or blocked planning receipt with true owner
repo/contract/work links; capability matrix with unresolved evidence; precise
proposal for future authorized validation; explicit implemented/tested/installed/
deployed separation. This proposal authorizes no socket input or inference.

## Other owner-planning proposals, dependency ordered

| Owner / existing authoritative reference | Bounded planning request | Dependencies / expected return |
| --- | --- | --- |
| Bloodbank current ASM provider; [I-9 BB-32 and BB-33](../../initiatives.md#i-9-33god-features-formal-repos-one-owner-per-atom) | Reconcile existing isolation/identity work against AD-4/9 before any proof. ASM is target facts owner; do not create another detector in crank/Fleet. | Return actual owner work links and current evidence for isolated Redis/channel behavior and invoking process/native session correctness; do not run tests or repair here. |
| ASM target owner; [I-9 extraction delegation](../../initiatives.md#i-9-33god-features-formal-repos-one-owner-per-atom), [catalog](../../../../features.toml) | Define canonical namespace/boot/PID/start-token/session equality, freshness, uncertainty and process-to-pane corroboration. Reuse BB-33 and PJAN-202 detection knowledge. | Return owner contract/provisional-provider designation and gaps; extraction/repo creation are not dispatched. Required facts block dependent candidate input when absent. |
| Terminal-driver target owner; [I-9 approved split](../../initiatives.md#i-9-33god-features-formal-repos-one-owner-per-atom) | Plan only required topology/location interface, neutral types, no agent classification, no reverse Deckard dependency. Native path does not require a new terminal-send implementation. | Preserve Perth/zellij-driver and installed `zdrive` contracts; no repurposing. Return topology/provisional-provider boundary and existing work link, not a new input stack. |
| Crank; [I-8 binding/engine delegation](../../initiatives.md#i-8-pane-bound-crank), [catalog current homes](../../../../features.toml) | Adopt AD-3/5/6: live-session opt-in, uninterrupted final submit authority, persisted stable attempts/trigger equivalence and incarnation-scoped uncertainty fence. Define authority takeover exclusion, not an expiring lease plus unfenced writer. | Depends on ASM/Fleet/topology contract capabilities. Return owner-side contract/work reuse and integrated proof arrangement; unknown survives re-opt-in/new binding and only decisive evidence clears it. No hub repo creation or registry migration here. |
| PJangler; [I-8 PJAN-202 and CLI/TUI delegation](../../initiatives.md#i-8-pane-bound-crank) | Reuse read-only inventory and existing `pj crank tui`; propose owner-backed selection/mutation and accurate reason/outcome projection. | No parallel registry/detector or new dashboard. Return links to existing work and UI contract dependence; PJAN-202 is provisional discovery, not a certified send API. |
| Candybar / runner; [I-8/I-9 existing work](../../initiatives.md#i-8-pane-bound-crank), CAND-52 historical link in I-9 | Identify only actual occurrence identity/dispatch evidence needed by crank; retain existing Candybar clock/native runner/cap. Reuse previous work rather than reopen its delivery. | No new schedule, job/service or cap change. Return existing occurrence contract and unresolved evidence gap. |

Existing board links for later authenticated readback (not status assertions):
[BB-32](https://plane.delo.sh/33god/browse/BB-32/),
[BB-33](https://plane.delo.sh/33god/browse/BB-33/),
[PJAN-202](https://plane.delo.sh/33god/browse/PJAN-202/),
[CAND-52](https://plane.delo.sh/33god/browse/CAND-52/).

## Catalog reconciliation proposal, not a silent edit

Root `features.toml` is still the authoritative catalog. Its current crank
`requires` includes `pane.input` and lacks the newly assigned `agent.message`
atom. The older I-8 scope remains broader than this first proof. The narrow
planning amendment did not authorize catalog/model or initiative rewrites.

Before future owner implementation/handoff is treated as ready, the parent
planning owner must reconcile the accepted `agent.message` owner and first-proof
native route in the catalog, preserving terminal-driver's separate `pane.input`
ownership and distinguishing wider I-8 scope. Do not infer a new runtime feature,
API, CLI or formal repo from that catalog correction. This is a visible linked
planning dependency, not a second authoritative owner table or fabricated blocker
to the architecture agreement.

## Handoff admission and evidence rules

Before a later actual handoff, resolve the real PM/intake route and governing
execution enrollment, read existing linked work and record an acceptance/blocking
receipt. Assignment ≠ accepted work, publication ≠ execution, local tests ≠
installed/deployed capability. Do not send these proposals from this session.

Owner returns must identify exact contract/revision evidence, failed/unproved
capabilities, accepted work links and next authorized step. I-9 indexes those
returns without editable copies of status. A fresh agent follows those links;
private coaching history is not a dependency.

Enablement/proof waits for all three native capability gates and required
identity/isolation/admission contracts. Later separately authorized real-agent
proof observes native submissions and receiving inputs, including every negative
destination and binding-change uncertainty cases. No partial local result
promotes any of the three independent hub/scoped-behavior/full-I-8 verdicts.

No proposal here authorizes code, runtime input, services/clocks, spend, cap change,
commits/pushes, merge, deployment, owner dispatch or duplicate component backlogs.
