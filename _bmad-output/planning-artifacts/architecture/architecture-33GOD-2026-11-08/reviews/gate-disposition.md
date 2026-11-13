# I-9 architecture — gate disposition history

**Latest checkpoint, 2026-11-08:** architecture finalized after accepted native
route/owner disposition, fresh independent amended-input/decision-log audit,
rubric/reality PASS and independent adversarial-fix recheck PASS. OQ-1 is resolved;
OQ-2 remains blocking enablement/proof gates. See [final disposition](final-gates.md).
Earlier draft/pending statements below are historical, not current decisions.

## Prior draft checkpoint

Date: 2026-11-08. **Status at that checkpoint: draft; not safe to finalize or hand off for delivery.**

Provenance: this file is the main assistant's consolidation of independent agent
returns, not a reviewer-authored report. Reviews examined the pre-fix draft;
corrections below are author-applied and have not received a second independent
re-approval. The original returns remain in this session's task transcripts.

## Checks and dispositions

| Check | Return | Disposition |
| --- | --- | --- |
| Mechanical spine lint | Zero findings on first draft | Rerun after edits; not semantic readiness |
| Source reconciliation | Three gaps; not safe to finalize | Narrow adopted attribution; restore exact escalation and repeated-failure response |
| Rubric | Coherent initiative scope; authorization revocation gap | Explicit admission/opt-out/eligibility ordering added to OQ-1 and future scenarios |
| Technology/reality lens | Sound as draft; preserve current/target distinction | Source table attributed to separate read-only source check; no new API/version claimed |
| Adversarial compatibility | Identity representations, revocation ordering, duplicate occurrence identity and delivery milestone | Canonical comparison required in owner contract; OQ-1 expanded; AD-6 defines occurrence equivalence/dedup requirement; OQ-2 requires agent CLI acceptance observable, not echo |

Independent reviewers:

- Source reconciliation: task `a3af743e0f3d6f217`.
- Rubric: task `a8306c9a9bb5bdf2a`.
- Reality lens: task `acf1e24a7f1606265`.
- Adversarial lens: task `a3d0a7ed0da6cb241`.
- Bounded source readiness check: task `a954f3f800f8ed5dd`.

The source checker reported Bloodbank `34a18a1` and pjangler `02eeee1`. It found:

- `bloodbank/services/agent-hooks/core/asm.py:205–229,435–439`: invoking-agent
  ancestry/session defect mechanism persists; hook-hub provides parent PID at
  `bloodbank/services/hook-hub/hub.py:248–253`.
- `bloodbank/services/agent-hooks/tests/test_asm.py:23–64` defaults to production
  Redis; fixed transition channel in `core/asm.lua:389–391` prevents isolation.
  No tests were run.
- `.agents/tools/jev-clairic/bin/zcrank.py:371–449`,
  `bin/zcrank-gate.py:290–310` and `hermes/crank-beat-prompt.txt:1`: existing
  tab/pane selection and raw input lack process/session-bound send guards. This
  tool directory was unversioned; no source revision certified.
- `pjangler/src/crank/panes.ts:386–418,475–497,670–675`: provisional Claude
  session validation exists, public process-start token absent, other native
  sessions unresolved. `src/crank/controller.ts:93–146` still tab/project-based.
- New `asm`, `terminal-driver` and `crank` checkouts were absent.

These are independent source-inspection findings, not independently rerun by the
main assistant and not live Redis/deployment observations. Historical ghost-row
counts and deployed behavior were not reverified.

## Remaining blockers

1. **OQ-1:** an enforceable terminal action-time identity/foreground guarantee,
   stale-worker fencing and authorization/state change ordering. No atomic backend
   capability has been demonstrated; a precheck cannot establish the guarantee.
2. **OQ-2:** accepted supported native-session/freshness/comparison contracts and
   concrete complete observations/procedure, including actual agent CLI input
   acceptance and all negative destinations. Generic proposed command names do not
   make this executable.

Resolve through focused owner-contract feasibility planning, not implementation,
new tickets, live input or a silent weaker acceptance condition. A genuine
feasibility/scope conflict returns one exact recommendation/evidence-backed decision.
The latest no-further-questions instruction does not authorize invented answers.

## Focused feasibility disposition — subsequent checkpoint

The earlier blocker list above records the previous review checkpoint. It is
superseded in its classification, not erased as history:

- **OQ-1:** native messaging is a technically credible capability-gated candidate;
  ordinary terminal precheck/send remains rejected. The actual architecture-agreement
  blocker is the narrow route/operation-owner disposition: pane-bound Linux Claude
  native delivery, recommended under Hermes Fleet, instead of specified terminal
  input. FR-2/AD-5 wording must be reconciled if accepted. No approval is inferred.
- **OQ-2:** external compatibility support, exact session fencing across async
  ingress and independently observed receiving-input acceptance remain capability
  prerequisites before enabling/proving input. Missing owner wrappers or production
  deployment alone are not reasons to withhold an agreed invariant contract.
- Crank's final authority must retain exclusion through last-point revocation and
  eligibility revalidation/submission; a lease check then unfenced write is not
  sufficient. Post-submit retraction/continuous idle is not promised.
- FR-6 does not require model consumption. An exact receiving-input queue boundary
  could qualify if its session binding, semantics and independent observation are
  established. The inspected internal `delivered` status alone does not establish
  that. No first CLI is certified for behavioral proof yet; Claude alone is proposed.

Independent challenges:

| Reviewer | Return | Disposition |
| --- | --- | --- |
| Native feasibility, `a2569b30686e21c21` | Native internal adapter technically feasible; support/session/acceptance gaps distinct from wrapper backlog | Corrected feasibility note; no public stability or actual-input PASS claim |
| Scope, `a3d27930da728b83f` | FR-6 permits native outcome, FR-2/AD-5 require explicit reconciliation; owner unassigned; remain pane-bound | One exact delegated route/owner recommendation, no silent owner expansion |

Both received the supplied installed-code findings; neither independently
reinspected the later binary excerpts. Main independently inspected bounded source
and wrote the consolidation. These returns are not independent reapproval of the
final edited documents. Full mechanism evidence, limitations and proposed contract
are in [delivery-feasibility.md](../delivery-feasibility.md).

PRD remains unchanged/final. Spine remains draft solely for the unresolved
consequential route/ownership disposition, not a demand for deployed proof before
architectural agreement. No runtime input, implementation, new service/clock,
spend, merge or deployment was performed.

## Authority and delivery

PRD remains final as a requirements baseline. Architecture remains draft. All three
software/workflow outcomes remain **not run here**. No component code, board state,
schedule, cap, gateway, live pane, commit, merge, push or deployment was changed.
Unrelated dirty files were preserved. The advisor command/skill was unavailable;
these independent reviews are not represented as an advisor invocation.

Notebook binding/overview readbacks passed. Two pre-existing possibly-dispatched
mutation receipts remained warnings; no retry, deletion or repair was attempted.
A derivative notebook copy does not supersede Git artifacts or certify review.
