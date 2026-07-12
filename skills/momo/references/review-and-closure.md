# Review and closure

Clearing the review lane is the **normal per-pass path**, not an escape hatch. Momo runs an
independent adversarial review against the operator's locked intent and acts on the verdict
autonomously — it does not wait for the operator's first right of refusal. The operator's QA
is *deferred* to an end-of-product sweep over the review lane, backed by a queryable decision
trail; a downstream regression rollback is the safety valve.

These scripts live in the repo's `<role_dir>/.scripts/sentinel/bin/` and are provider-
agnostic. A manual session calls them directly.

## 1. Close gate (evidence completeness) — a hard automated lock

```bash
<role_dir>/.scripts/sentinel/bin/issue-close-gate.sh <ISSUE> [REPO_ROOT]
# exit 0 = PASS, 1 = FAIL (missing/incomplete evidence), 2 = bad usage
```

It validates the evidence file `_bmad-output/implementation-artifacts/issue-evidence/<ISSUE>.md`.
Requirements (see `templates/issue-evidence.md`, which matches exactly):

- Must contain these `##` headings: **Issue, Acceptance Criteria, Repo Changes,
  Verification, Ledger Update, Known Gaps, Close Recommendation**.
- Must contain the literal lines `Ledger updated: yes` and `Close recommendation: ready`.
- Must NOT contain (case-insensitive, anywhere) the placeholder words `TBD`, `TODO`,
  `not run`, `pending`, `unknown`. **Gotcha:** these trip on narrative prose too — write
  "no gaps" not "none pending", "did not execute" not "not run".

The close gate does **not** check for a worker-attribution line. Still, always include a
`- Worker:` (or `- Implemented by:`) line in the evidence (the template does): it is what
the autonomous review's **independence check** reads to confirm reviewer ≠ implementer. That
check only HOLDs when a parsed implementer *equals* the reviewer — a missing worker line
fails neither gate, but then independence is unproven, so write it.

## 2. Autonomous adversarial review — the decision engine

```bash
<role_dir>/.scripts/sentinel/bin/issue-autonomous-review.sh <ISSUE> <ISSUE>.review.md
# exit 0 = accepted, 3 = held (or disabled), 2 = missing inputs, 1 = adapter transition failed (--close only)
```

It chains, accumulating HOLD reasons: report structure → **reviewer independence** (reviewer
agent ≠ the implementer named in evidence) → drift rubric → adversarial findings → reviewer
decision → the close gate. It ALWAYS emits
`bloodbank.v1.repo.<repo>.issue.autonomous_review.decided` with the full verdict. You author
the review report at `<ISSUE>.review.md` (shape in `templates/review-report.md`).

**Drift rubric** — accept only `none`/`minor` with no unresolved critical/high finding:
- `significant` (HOLD): an AC unmet; capability added/removed beyond the ACs/milestone;
  contradicts a locked decision/north star or locked architecture; pulls later work into
  now; introduces a new external dependency/credential/paid action.
- `minor` (accept allowed): internal refactors, extra tests, naming, cosmetics, docs.
- `none`: matches locked intent and ACs.

The close gate stays a HARD lock: the script will not emit `accepted` while the gate fails,
drift is `significant`, a critical/high finding stands, or independence isn't satisfied.
Run WITHOUT `--close`.

## 3. Act on the verdict (autonomously — no grace wait)

- **accepted** (exit 0): treat the ticket as **done for dependents and flow**, but **leave
  it in the review lane** — that lane is the operator's deferred-QA queue. Do NOT
  auto-transition to `completed` (`--close` is an optional operator QA-sweep flag the loop
  omits). Post ONE ticket comment stating the autonomous acceptance with a pointer to the
  report — never a "waiting on you" comment. Record a Momo decision event
  (`record-decision.py`, basis `evidence-over-status`, `bias-to-reversible-action`). A
  dependent blocked only on this feature is now unblocked.
- **held** (exit 3 with a real finding): move the ticket back to active (`started` if a
  worker takes it now, else `unstarted`); record the hold reasons; emit the decision event.
  When in doubt, hold.
- Distinguish **held-by-finding** from **disabled-by-config**: a run disabled via
  `reconcile.auto_review=false` / `RECONCILE_AUTO_REVIEW=off` also exits 3 but emits NO
  decision event — read the stderr message.

## 4. Downstream regression rollback (the safety valve)

If a later dependent proves a review-accepted feature is ACTUALLY BROKEN: move the accepted
ticket back to active as a **prerequisite** of the dependent (`tp transition`); comment
naming the dependent + symptom; emit
`bloodbank.v1.repo.<repo>.issue.review_rollback.recorded` `{issue, surfaced_by, reason}` (via
the sentinel `emit-event.py`) plus a Momo decision event. This is expected and healthy — the
trade for deferring operator QA, not a failure.

## Out-of-scope blockers (review does NOT clear these)

Record and wait, exactly as before: external credentials / third-party access / paid
actions; an undecided product decision; ACs not actually satisfied by evidence; a dependency
on another open, unblocked issue.

## Anti-stall (repeat, because it matters)

For any review-lane ticket there are exactly three legitimate outcomes: **accepted** (move
on), **held** (back to active), or a genuine **out-of-scope blocker** (recorded + waited on).
There is no fourth "waiting for the operator's sign-off" state.
