# The board-clearing loop

When the goal is "just clear the board" (no single named ticket), Momo runs a
policy loop that reads Lifecycle's authoritative snapshot/frontier, applies the
Pillars to choose legal work, delegates, reviews, submits intent/evidence, and
renders the result. **Do not implement or mirror a state machine in Momo.**

## Invariant

If Lifecycle offers a legal work-start action, exactly one implementation worker
is active or Momo records why none can be selected. WIP = 1 is shared with
Hermes. Command idempotency and expected-version checks prevent double state
writes; the WIP lock additionally prevents double worker dispatch.

## Authority and advisory policy

The canonical inputs are Lifecycle's versioned spec/state, legal frontier,
obligations, blockers, and capability grants. Provider lanes and the workflow's
legacy normalized labels are projections only.

Momo may use these advisory policy inputs without claiming state authority:

- **AC readiness rubric:** `non_empty ∧ testable ∧ enumerated ∧ fr_coverage`.
- **QA policy:** attempt focused repair/re-verification within the configured
  budget, then submit the evidence and verdict.
- **Staleness policy:** report stale observations; Lifecycle decides their state
  consequence.

Pillars rank actions already present in the legal frontier. They cannot invent an
action, satisfy an obligation, validate a capability, or advance state.

## One loop pass

1. **Awareness:** resolve PJangler identity; fetch the authoritative Lifecycle
   snapshot/frontier/obligations/grants; then inspect provider-owned ticket/board records, Hermes
   client state, evidence, event trail, and live workers.
2. **Is a worker already active and healthy?** (yours or Hermes'). Yes → monitor it, record
   state, and go to step 6. WIP=1.
3. **Service review obligations first.** Use `lifecycle_client.py
   plan-obligation` for a pending authoritative obligation with canonical
   `skill_ref`; publish its agent invocation through Bloodbank and submit the
   resulting completion evidence. Non-pending or non-current work is rejected.
4. **If no worker is active, choose exactly one legal frontier item** using the
   selection policy below. Submit idempotent work-start intent with expected
   state version. Delegate only after Lifecycle accepts it.
5. **Advance policy work** through triage, delegation, gates, review, and evidence
   submission. Refetch after every command; never predict the next state.
6. **Staleness sweep** — record and submit stale observations. Lifecycle decides
   whether they block, degrade, or leave state unchanged.
7. **Update your read of the world** and decide: continue, wait (timer), or stop.

## Selection policy (when no worker is active)

Consider only actions in the authoritative legal frontier, then pick the first
that applies:

1. An obligation needing only agent-doable evidence/AC repair.
2. An unblocked legal work item in the active product milestone.
3. A legal unstarted candidate that is a clear value-add, unambiguous, and has
   enough data to start without guessing.
   Recording this pull as a decision event (basis `keep-the-pipeline-unblocked`,
   `smallest-reviewable-increment`) is **mandatory** — it is you spending the operator's trust.
4. A small, high-priority backlog candidate only if Lifecycle exposes a legal
   acquisition action and Momo's judgment says it is valuable and ready.

If picking would require guessing intent, do not pick — refine first, or leave it and record
why.

## Stop conditions (end the loop cleanly — do not spin)

Stop and report when **any** of these hold:

- **Three consecutive intervals with zero activity.** Track `idle_intervals`. An interval
  counts as activity if the authoritative state/version changed, a worker started/finished, a review
  resolved, or evidence changed. A pass that only re-observes the same state increments
  `idle_intervals`; any activity resets it to 0. At `idle_intervals == 3`, stop.
- **No legal action remains** beyond backlog candidates that fail the Pillar/readiness bar.
- **Every remaining candidate is an out-of-scope blocker** — external credentials,
  third-party access, paid actions, or an undecided product decision. Record each and wait.
- The next action needs **destructive git ops / production credentials / a paid action** —
  stop and surface it for the operator.

**Never** stop merely because reviewed work "looks good, waiting on the operator."
Submit the review evidence and render Lifecycle's authoritative obligation/state.

Always **record a decision event** when you stop, naming which condition fired and why.

## Waiting on CI / workers — the 10-minute timer

When the only thing to do is wait (CI running, a delegated worker still executing, an
external agent's PR pending), **do not busy-spin and do not end the session** — set a
re-check timer so the pipeline keeps moving:

- Preferred: run the loop under the **`loop`** skill at a 10-minute cadence, e.g.
  `/loop 10m be Momo and take one board-clearing pass`. Each firing is one pass; the loop's
  `idle_intervals` counter applies across firings.
- Or self-pace with a ~600s wake-up (ScheduleWakeup) carrying the same "take one pass"
  intent.
- On each wake: re-read worker/CI state. If the awaited thing finished, resume the pipeline
  and reset `idle_intervals`. If still pending, increment `idle_intervals` and re-arm the
  timer — until a stop condition fires.

Ten minutes is the default heartbeat for a waiting operator session; shorten only if you are
polling something that changes faster, lengthen if you are genuinely idle.

## End-of-run report

When you stop, report: Lifecycle ID/spec/state version and frontier summary,
provider ticket/board records, tickets touched, evidence
touched, the active worker/blocker (if any), the decision events you emitted, the stop
condition that fired, and the single next recommended action.
