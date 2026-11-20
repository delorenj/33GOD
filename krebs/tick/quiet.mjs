// Quiet windows: the tickets a board run left waiting only for time to pass.
//
// A Todo ticket becomes a triage candidate once it has been unchanged for the triage quiet window, and a
// handed-back ticket a review candidate after the review window. A run that finds one of them still inside
// its window does nothing for it, and nothing will wake the board when the window ends: no Plane edit is
// coming. `krebs watch` reads these times from the run's report and re-arms the board for the earliest one,
// which is what lets a ticket dropped into Todo be triaged two minutes later instead of at the next tick.

import { REVIEW_MIN_AGE_MS, TRIAGE_MIN_AGE_MS, reviewGuard, triageGuard } from "./select.mjs";

/**
 * [{key, kind: "triage"|"review", eligibleAt (ms)}] for the tickets that pass every check except the
 * quiet window. The tick tests `now - updated_at > window`, so a ticket is taken 1 ms after the window.
 */
export function quietWindows(tickets, nowMs, { triageMinAgeMs = TRIAGE_MIN_AGE_MS, reviewMinAgeMs = REVIEW_MIN_AGE_MS } = {}) {
  const out = [];
  for (const t of tickets) {
    const updated = Date.parse(t.updatedAt ?? "");
    if (!Number.isFinite(updated)) continue;
    if (triageGuard(t, nowMs, Number.NEGATIVE_INFINITY) === null) {
      if (triageGuard(t, nowMs, triageMinAgeMs) !== null) out.push({ key: t.key, kind: "triage", eligibleAt: updated + triageMinAgeMs + 1 });
    } else if (reviewGuard(t, nowMs, Number.NEGATIVE_INFINITY) === null) {
      if (reviewGuard(t, nowMs, reviewMinAgeMs) !== null) out.push({ key: t.key, kind: "review", eligibleAt: updated + reviewMinAgeMs + 1 });
    }
  }
  return out.sort((a, b) => a.eligibleAt - b.eligibleAt);
}
