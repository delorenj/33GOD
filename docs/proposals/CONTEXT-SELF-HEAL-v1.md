# Context Self-Heal v1 (Deterministic)

Status: Draft ready for implementation  
Owner: Cack  
Date: 2026-02-26

## Non-negotiables

1. Every agent is responsible for its own context.
2. At **>=90%**, compaction + restart happens immediately.
3. No managerial intervention is required for normal compaction flow.

## Threshold policy

- `<80%`: normal operation
- `>=80% and <90%`: warning zone; update checkpoint notes continuously
- `>=90%`: execute compaction pipeline now

## Deterministic compaction pipeline

1. Emit `agent.context.check` with current usage.
2. Write `memory/context-compaction-latest.md` with strict schema:
   - Active tasks (ticket IDs)
   - Decisions made
   - Open blockers
   - Next 3 actions
   - Handoff links/files
3. Emit `agent.context.compact`.
4. Restart/compact session.
5. On boot, read `memory/context-compaction-latest.md` first.
6. Emit `agent.context.compacted` and resume work.

## Note-taker strategy (incremental)

### Phase A (ship now)
- Rule-based structured note writer (no model dependency).
- Triggered each time agent enters warning zone, and before compaction.
- Overwrites `context-compaction-latest.md`.

### Phase B (upgrade)
- Weighted note ledger (`memory/context-ledger.ndjson`) that scores:
  - decisions
  - blockers
  - owner changes
  - delivery artifacts
- Compaction summary generated from weighted ledger + latest notes.
- Dream cycle rolls compact summaries into day/week summaries.

## Why this works

- Deterministic and cheap.
- No cross-agent babysitting.
- Recovery is immediate and consistent.
- Produces auditable artifacts for handoff and daily review.
