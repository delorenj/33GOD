// How many board turns (triage, review) one ticket gets per stretch in a stage, and what
// happens at the cap. Pure policy plus one activity-log read; run.mjs does the writes.
//
// The rule (spec catch_up.review / catch_up.triage, "attempts"): Krebs sends a ticket at
// most MAX board turns of a kind per EPISODE (tick/episode.mjs: since the handback, or
// since the ticket entered Todo, or since a person last cleared a hold), at least RETRY
// apart. A ticket whose episode has used them all is parked: agent:failed plus one
// comment, and no further turn until a person removes the label (which starts a new
// episode). Before 2026-11-20 the count was keyed on the ticket version, which the
// turn's own pickup chip rewrites, so the cap could never trip.

import { readEpisode } from "./episode.mjs";

/** A review turn that ended without a verdict is asked again after this long, up to this many times per episode. */
export const REVIEW_RETRY_MS = 3 * 60 * 60 * 1000;
export const REVIEW_MAX_ATTEMPTS = 3;
/** A triage turn that ended without lifecycle:triaged or a hold label: shorter gap (it gates dispatch), same cap. */
export const TRIAGE_RETRY_MS = 30 * 60 * 1000;
export const TRIAGE_MAX_ATTEMPTS = 3;

export const STAGES = Object.freeze({
  review: { max: REVIEW_MAX_ATTEMPTS, retryMs: REVIEW_RETRY_MS, noun: "review turn", ends: "a verdict (close, release or attention)" },
  triage: { max: TRIAGE_MAX_ATTEMPTS, retryMs: TRIAGE_RETRY_MS, noun: "triage turn", ends: "lifecycle:triaged or a hold label" },
});

/**
 * What to do with one board-turn candidate.
 *   sends   this ticket's published turns of the kind in the look-back window, oldest first ([{at}]).
 * Returns one of
 *   {action: "send", attempt}                  the next attempt number within the episode
 *   {action: "wait", why, sent}                inside the retry gap
 *   {action: "park", attempts, lastAt}         the episode has used every attempt
 *   {action: "unreadable", why}                the activity log could not be read: do nothing
 * A ticket with no prior send never reads the log (the first turn of a healthy ticket costs nothing extra).
 */
export async function judgeBoardTurn({ plane, ws, board, ticket, stage, sends, nowMs }) {
  const rule = STAGES[stage];
  let sent = sends;
  if (sends.length) {
    const ep = await readEpisode(plane, { ticket, stage, ws, board });
    if (!ep.ok) return { action: "unreadable", why: ep.why };
    sent = sends.filter((s) => Date.parse(s.at) >= ep.startMs);
  }
  const last = sent[sent.length - 1];
  const lastMs = last ? Date.parse(last.at ?? "") : NaN;
  if (sent.length >= rule.max) return { action: "park", attempts: sent.length, lastAt: last?.at ?? null };
  if (Number.isFinite(lastMs) && nowMs - lastMs < rule.retryMs) {
    return { action: "wait", why: `${rule.noun} sent ${Math.round((nowMs - lastMs) / 60000)} min ago`, sent: sent.length };
  }
  return { action: "send", attempt: sent.length + 1 };
}

/** The one comment a parked ticket gets (plain words: the reader is Jarad, not the PM). */
export function parkComment(stage, attempts, lastAtIso) {
  const rule = STAGES[stage];
  const what =
    stage === "review"
      ? "asked the project manager to review this handed-back ticket"
      : "asked the project manager to triage this ticket";
  const when = lastAtIso ? ` (the last one at ${lastAtIso.slice(0, 16).replace("T", " ")}Z)` : "";
  return (
    `<p>Krebs ${what} ${attempts} times${when}, and none of those turns ended with ${rule.ends}. ` +
    `It has stopped asking and added <code>agent:failed</code> so this does not repeat. ` +
    `Look at the project manager's last turn on this ticket, fix what stops it, then remove <code>agent:failed</code>: ` +
    `Krebs starts a fresh count of ${rule.max} when you do.</p>`
  );
}
