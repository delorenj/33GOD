// The prompt a Krebs dispatch sends: the n8n package's delegationPrompt (the
// v2 "Krebs has already dispatched it to you" text, kept in one place for every
// producer), plus the one fact only the registry row knows: whether this
// scope's handback is a review or a close.

export function dispatchPrompt(fleet, facts, projectPath, review) {
  const base = fleet.delegationPrompt(facts, projectPath);
  const handback = review
    ? "This scope REQUIRES review (agents-registry plane.review: true): hand back by adding " +
      "`lifecycle:review` with the evidence comment, and leave the ticket In Progress. Do not close it."
    : "This scope has NO review step (agents-registry plane.review is not true): hand back by " +
      "closing the ticket Done with the evidence comment.";
  return `${base}\nHandback for this scope (from krebs tick): ${handback}\n`;
}

/**
 * The prompt of a review turn: the scope's PM gives the verdict on a ticket
 * handed back with lifecycle:review (spec catch_up.review). Launch Directors are
 * retired; the PM is the verdict giver in steady and launch mode alike.
 */
export function reviewPrompt(facts, projectPath) {
  const key = facts.ticketKey || facts.ticketId || "(unknown)";
  const ref = facts.title ? `${key} — ${JSON.stringify(facts.title)}` : key;
  const where = [
    projectPath ? `Repo checkout: ${projectPath} (run px from there; it reads that repo's .project.json)` : null,
    facts.boardId ? `Plane board id: ${facts.boardId} (pass it as project_id on every Plane tool call)` : null,
  ].filter(Boolean);
  return (
    `Review turn from krebs tick. ${ref} on the ${facts.repo || "project"} board is In Progress with ` +
    "`lifecycle:review`: its implementation turn handed it back. You are this project's verdict giver " +
    "(Launch Directors are retired; the PM judges, in steady and launch mode alike).\n" +
    (where.length ? `\nWhere things are — use these verbatim:\n${where.join("\n")}\n` : "") +
    "\nBefore anything else, re-read the ticket live (`px show <ref>`). If it is no longer In Progress, " +
    "no longer carries `lifecycle:review`, or carries a hold label (`lifecycle:needs-input`, " +
    "`lifecycle:blocked`, `agent:failed`, `lifecycle:human`), stop and change nothing. " +
    "`lifecycle:human` means the owner holds it by hand: write nothing at all.\n" +
    "\nThen judge it:\n" +
    "  1. Read the acceptance criteria and the handback evidence comment, and open the linked commits or PRs.\n" +
    "  2. Check every criterion against evidence you verify yourself (run the check, read the landed diff), " +
    "not against the implementer's summary. The reviewer is never the implementer: for code, delegate an " +
    "independent review worker that did not write it and give it the criteria, not the conclusion.\n" +
    "  3. End with exactly one verdict:\n" +
    '     - Accepted: `px close <ref> -m "<one line: why it passes, with the evidence link>"`.\n' +
    '     - Sent back: `px release <ref> -m "returned: <the specific unmet criterion and what would satisfy it>"`. ' +
    "It goes to Todo, keeps `lifecycle:triaged` and waits for a slot; Krebs clears `lifecycle:review`.\n" +
    '     - Cannot judge without a person: `px attention <ref> -m "<one concrete question>"`.\n' +
    "\nNever add or remove `agent:working` or `lifecycle:human`, never dispatch, and never move the ticket " +
    "except through those three commands. One verdict, then end the turn.\n"
  );
}
