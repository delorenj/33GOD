// The human summary of a tick report (--json prints the report itself).

function scopeName(s) {
  const labels = s.scopeLabels?.length ? ` ${s.scopeLabels.join("+")}` : "";
  const dflt = s.scopeDefault ? " (default)" : "";
  return `${s.identifier ?? s.boardId}${labels}${dflt} -> ${s.agentId}`;
}

function list(items, fmt) {
  return items.map(fmt).join(", ");
}

export function formatReport(report, { verbose = false } = {}) {
  const lines = [];
  const mode = report.dryRun ? "dry run, nothing written" : "live";
  lines.push(`krebs tick (${mode}) ${report.at}: ${report.scopes.length} scope(s), ${report.skipped.length} registry row(s) not scopes`);
  if (report.busy) {
    lines.push("  another tick holds the lock; nothing done");
    return lines.join("\n");
  }
  for (const s of report.scopes) {
    const head = `${scopeName(s)}  wip ${s.wip}  occupied ${s.occupied.length}  free ${s.free}` +
      (s.overLimit ? `  OVER LIMIT by ${s.overLimit} (draining)` : "") +
      (s.review ? "  review:on" : "");
    lines.push("");
    lines.push(head);
    if (s.occupied.length) lines.push(`  in progress: ${s.occupied.join(", ")}`);
    if (s.republishes.length) lines.push(`  republish: ${list(s.republishes, (r) => `${r.key} ${r.commandId} ${r.result}${r.why ? ` (${r.why})` : ""}${r.error ? ` (${r.error})` : ""}`)}`);
    {
      const acted = (s.orphans ?? []).filter((o) => o.result !== "live");
      const live = (s.orphans ?? []).filter((o) => o.result === "live");
      for (const o of acted) lines.push(`  orphan: ${o.key} ${o.action ?? ""} ${o.result}${o.why ? ` (${o.why})` : ""}${o.error ? ` (${o.error})` : ""}`.replace(/  +/g, " ").replace(/^ /, "  "));
      if (live.length) lines.push(`  turn live, left alone: ${list(live, (o) => `${o.key} (${o.why})`)}`);
    }
    lines.push(`  repairs: ${s.repairs.length ? list(s.repairs, (r) => `${r.key} -${r.remove.join(" -")} ${r.result}`) : "none"}`);
    if (s.dispatches.length) {
      for (const d of s.dispatches) {
        const what = d.write ? ` -> ${d.write.state} +${d.write.addLabels.join(" +")}${d.write.start_date ? ` start ${d.write.start_date}` : ""}` : "";
        lines.push(`  dispatch: ${d.key} ${JSON.stringify(d.title)}${what} cmd ${d.commandId ?? "-"} ${d.result}${d.why ? ` (${d.why})` : ""}${d.error ? ` (${d.error})` : ""}`);
      }
    } else {
      const why = s.free <= 0 ? "no free slot" : "no eligible Todo ticket";
      lines.push(`  dispatch: none (${why})`);
    }
    {
      const parts = s.triage.map((t) => `${t.key} ${t.result ?? "?"}${t.commandId ? ` cmd ${t.commandId}` : ""}${t.why ? ` (${t.why})` : ""}${t.error ? ` (${t.error})` : ""}`);
      if (s.triageCapped.length) {
        const shown = s.triageCapped.slice(0, 4);
        const more = s.triageCapped.length - shown.length;
        parts.push(`capped ${s.triageCapped.length}: ${list(shown, (c) => `${c.key} (${c.why})`)}${more ? `, +${more} more (see --json)` : ""}`);
      }
      if (s.triageSeen.length) parts.push(`already triaged at this version: ${s.triageSeen.join(", ")}`);
      lines.push(`  triage catch-up: ${parts.length ? parts.join("; ") : "none"}`);
    }
    {
      const reviews = s.reviews ?? [];
      const parts = reviews.map((t) => `${t.key} ${t.result ?? "?"}${t.attempt > 1 ? ` attempt ${t.attempt}` : ""}${t.commandId ? ` cmd ${t.commandId}` : ""}${t.why ? ` (${t.why})` : ""}${t.error ? ` (${t.error})` : ""}`);
      const capped = s.reviewsCapped ?? [];
      if (capped.length) parts.push(`waiting ${capped.length}: ${capped.slice(0, 4).map((c) => c.key).join(", ")}${capped.length > 4 ? ` +${capped.length - 4} more` : ""}`);
      const seen = s.reviewsSeen ?? [];
      if (seen.length) parts.push(`already asked: ${list(seen, (r) => `${r.key} (${r.why})`)}`);
      if (parts.length) lines.push(`  review: ${parts.join("; ")}`);
    }
    if (s.waiting.length) lines.push(`  queued: ${s.waiting.join(", ")}`);
    if (s.blocked.length) lines.push(`  blocked: ${list(s.blocked, (b) => `${b.key} (${b.why})`)}`);
    if (s.excluded.length) lines.push(`  todo not dispatchable: ${list(s.excluded, (e) => `${e.key} (${e.why})`)}`);
    for (const w of s.warnings) lines.push(`  warning: ${w}`);
    for (const e of s.errors) lines.push(`  ERROR: ${e}`);
  }
  if (verbose && report.skipped.length) {
    lines.push("");
    lines.push("not scopes:");
    for (const k of report.skipped) lines.push(`  ${k.agentId} (${k.identifier ?? k.boardId ?? "?"}): ${k.why}`);
  }
  for (const e of report.errors) lines.push(`ERROR: ${e}`);
  lines.push("");
  lines.push(report.ok ? "ok" : "finished with errors");
  return lines.join("\n");
}
