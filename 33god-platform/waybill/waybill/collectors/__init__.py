"""Waybill collectors: one module per source, each exposing collect(ctx) -> model.Fragment.

REGISTRY is the run order, and it is also the merge priority: when two collectors describe the same
span id, the earlier one keeps identity fields (kind, component, name, t0) and later ones only fill
blanks, add refs/attrs keys and extend evidence (see assemble.merge_span). Receipts come first because
they carry the authoritative hook/handler timeline; enrichers (bus, memory, state, logs) follow.
"""

REGISTRY: list[str] = [
    "hookhub",            # receipts.sqlite3: hook invocations, handler executions, publisher event ids
    "transcript_claude",  # Claude transcript: prompt, injected context, llm requests, tools
    "transcript_codex",   # Codex rollout: the same for Codex CLI / exec / Desktop
    "candystore",         # archived CloudEvents (received_at), envelopes, usage rows, dead letters
    "holocene",           # JetStream seq + collected_at per event id
    "nats",               # consumer inventory (facts.consumers / facts.core_subs), seq lookups
    "gateway",            # AutomaticAI usage rows -> attrs._match_llm
    "hindsight",          # recall audit + journal + buffer/flush
    "asm",                # Redis ASM stream/hash + transitions.log
    "logs",               # docker logs of core consumers -> attrs._join
    "files",              # local state files written during the turn
]

# Collectors that only apply to one CLI; the runner marks the others 'skipped' instead of calling them.
CLI_ONLY: dict[str, str] = {
    "transcript_claude": "claude",
    "transcript_codex": "codex",
}

# Source ids a collector may report under, so --only/--skip accept either spelling.
ALIASES: dict[str, list[str]] = {
    "transcript": ["transcript_claude", "transcript_codex"],
    "hook-hub": ["hookhub"],
    "receipts": ["hookhub"],
    "redis": ["asm"],
    "bus": ["candystore", "holocene", "nats"],
}
