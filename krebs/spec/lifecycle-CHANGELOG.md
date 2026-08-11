# Lifecycle spec — changelog

> **Promoted to Krebs.** This document was written when the lifecycle machine
> lived at `momo/lifecycle/`. The machine is now owned by Krebs at
> `krebs/spec/lifecycle.v1.yaml`; historical `momo/lifecycle/...` paths below
> read as `krebs/spec/...`. Momo consumes the machine by pointer.

Semver: **major** = a state added/removed or a transition/guard semantics change
(breaks consumers) → a new `lifecycle.vN.yaml` file; **minor** = a new optional
guard knob or default change; **patch** = docs/typo. Consumers pin the major line
(`spec: krebs/spec/lifecycle.v1`).

## v1.0.0 — 2026-07-21

- **Promoted** the ticket-lifecycle state machine out of the ~30 per-repo
  `_bmad/custom/workflows/ticket-lifecycle/workflow.yaml` copies into this one
  versioned SSOT (`lifecycle.v1.yaml`). Basis: `build-lego-not-statues` (one
  machine definition, not N forks), `gang-of-four-by-default` (State + the `tp`
  adapter as Strategy for per-repo labels).
- Made transitions + guards **explicit** (they lived in prose in
  `board-clearing-loop.md` + step files): the 4-criterion AC rubric (no
  short-circuit), `qa.max_retries=3` (reverify-failed-only), reviewer-independence,
  WIP=1, per-state staleness watchdogs, the set-board-before-review precondition,
  and a single `blocked_funnel`.
- Provider **labels removed** from the machine — they move to the `tp` adapter's
  normalized-state map (the `states:` label map in each repo workflow.yaml is
  deleted; a per-repo file becomes a knobs-only overlay).

See `./README.md` for the full design rationale and the consumer-rewiring plan.
