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
