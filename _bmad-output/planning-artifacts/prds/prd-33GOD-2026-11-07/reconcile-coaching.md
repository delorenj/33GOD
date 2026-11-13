# Source reconciliation — I-9 coaching

Initial review: 2026-11-08. Source reviewer returned findings directly; it reported
that its environment prohibited report-file writes. This file is the main
assistant's faithful summary and disposition, not a reviewer-authored artifact.

Sources examined by reviewer: PRD, addendum, canonical memlog, I-8/I-9 initiative
records, feature catalog. Direct operator and delegated PM inputs remain distinct.

## Original verdict

Mostly aligned; three gaps (0 high, 1 medium, 2 low). Captured: reusable hub,
linked owners/work, agent-performable manual coordination, exact-revision evidence,
honest failures, fresh-agent reuse and all stated deferrals.

## Findings and disposition

1. **Medium: stronger completion gate.** Draft required I-8 to pass before the
   first I-9 increment could complete, but delegated input also permits a reusable
   handoff with real outstanding failures. **Resolved by delegated pjangler-pm
   decision, 2026-11-08:** separately track reusable workflow demonstration,
   scoped behavioral proof and full I-8 acceptance. PRD §7 records independent
   evidence for each. A failed behavior result cannot become a behavioral pass.
2. **Low: identifier portability omitted.** I-9 prohibits hardcoded job IDs,
   Candybar IDs, session names and home paths. **Applied:** narrow architecture
   constraint in addendum, not a generic linting workstream.
3. **Low: BMAD learning intention omitted.** **Applied:** preserve brief downstream
   step-purpose/artifact explanations, not a training project or approval ritual.

## Independent rubric review disposition

See `review-rubric.md` for original independent findings, retained unchanged.

- **High: complete I-8 gate versus scoped proof. Resolved by delegated decision.**
  Cross-pane migration/pane movement and restart recovery remain outstanding I-8
  work, not prerequisites for demonstrating the narrower workflow or proof and
  not silently waived. PRD §7 separates all three outcomes; FR-6 explicitly
  preserves independent process/session corroboration and no-agent/no-input.
- **High: executable proof protocol. Applied to requirements.** FR-6 now requires
  prerequisites/authorization, setup/reset, positive/negative observation points,
  expected/observed results, stop/fail conditions and evidence/revision capture.
  Concrete commands remain architecture work, not invented live tests now.
- **Medium: execution-dependency coverage. Applied.** FR-2 traces selection,
  dispatch, eligibility, input and evidence, including Hermes/Candybar as applicable,
  through existing authoritative links rather than a second owner table.

These are first-pass dispositions, not a reviewer re-approval or final PRD pass.
No code, test execution, merge, deployment or cap change was performed.
