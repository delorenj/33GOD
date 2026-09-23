# Input Reconciliation — Current 33GOD Ownership Evidence

## Sources

- Root `README.md`
- `flume/AGENTS.md`
- `holocene/AGENTS.md`

## What the PRD carries forward

- Flume owns workforce identity, roles, hierarchy, and workforce policy.
- PJangler owns project identity and registry concerns; Krebs and Pilot own
  ticket lifecycle; Hermes owns runtime execution and receipts.
- Holocene is the single-operator mission-control host and initial `/hq`
  surface.
- DeloHQ remains a bounded executive surface rather than a parallel control
  plane.

## Gaps or decisions made during reconciliation

1. Current component docs establish ownership but do not yet define the
   DeloHQ projection schemas, freshness budgets, or bounded-action contracts;
   those remain architecture open questions.
2. Holocene documentation describes the existing operational surface, not the
   final DeloHQ experience; the PRD treats `/hq` as the in-place starting point
   rather than declaring the current UI complete.
3. The PRD avoids copying stale historical statements that Flume is inactive;
   the current active Flume boundary is the governing input for this run.
