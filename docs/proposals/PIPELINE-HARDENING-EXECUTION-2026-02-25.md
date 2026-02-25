# Pipeline Hardening Execution Plan (2026-02-25)

Owner: Cack  
Requested by: Jarad  
Status: **EXECUTING**

## Objectives (from morning overview)

1. Create deterministic Plane workspace routing (stop duplicate project/board placement).
2. Establish incubator workflow in 33god workspace for idea intake.
3. Make context compaction deterministic + self-healing per agent.
4. Move heartbeat/context checks to event-driven invocation, with per-agent overrides.
5. Improve observability UX so every update has clear cause/category.
6. Remove no-op hook noise (empty payload chatter).

---

## 1) Deterministic Plane Workspace Routing (Decision Lock)

### Canonical rule
- **33god workspace** = internal platform/pipeline work.
- **lasertoast workspace** = external revenue products built with pipeline.

### Routing matrix
- Bloodbank / Holyfields / Holocene / Candystore / Perth / Yi / Flume / iMi / platform infra
  - -> `33god`
- ChoreScore / Wean / SVGMe / Overworld / Cack.io / Thermite / Jobby / Scalp / Stem / DigiPop / Jacksnaps
  - -> `lasertoast`

### Hard rule
When uncertain, route to `33god` **Incubator** as a seed ticket, then promote/formalize with explicit workspace move.

---

## 2) Incubator Board Workflow (33god workspace)

Board states:
1. **Seed**
2. **Make it happen**
3. **It has begun**
4. **Promoted**
5. **Formalized**

Labels (minimum):
- `idea:new-project`
- `idea:feature`
- `idea:refactor`
- `idea:architecture`
- `idea:monetization`

Promotion criteria:
- Clear owner
- Fit decision (workspace/project)
- Definition of done
- Execution path assigned

---

## 3) Context Self-Heal Standard (Deterministic)

### Threshold policy
- `>= 80%`: warning zone (agent self-prepares compaction notes)
- `>= 90%`: mandatory self-compaction + restart
- `> 100%`: policy breach (must self-heal immediately, no human ping)

### Event API (v1 draft)
- `agent.context.check`
- `agent.context.compact`
- `agent.context.compacted`
- `agent.context.reset`
- `agent.context.reset.completed`

### Compaction contract (standardized)
Each compaction writes:
- `what_changed`
- `in_flight_work`
- `open_blockers`
- `next_actions`
- `handoff_context`

Daily/weekly rollups:
- Dream cycle merges same-day compactions -> day summary
- Weekly job merges day summaries -> week summary

---

## 4) Heartbeat Execution Model (Global + Per-Agent)

### Config sources
- `heartbeat/global.json`
- `heartbeat/agents/{agent}.json`

### Merge order
1. global defaults
2. per-agent override

### Tick behavior
On each system heartbeat tick:
1. load merged heartbeat config
2. evaluate due actions
3. fire Bloodbank events for each due action
4. execute via consumers (not ad-hoc chat logic)

---

## 5) Observability Message Contract (Jarad-facing)

Every outward status line must include:
- **Cause** (what triggered this run)
- **Action** (what was actually done)
- **Impact** (what changed / what remains blocked)

No internal ratios unless action-required.
No empty/no-op chatter.

---

## 6) Immediate Fixes Executed

- ✅ No-op hook suppression implemented in `hookd-bridge`:
  - Empty `text` + `hook_dispatch` now returns `204` and **does not publish** a command.
  - Prevents spammy empty `raw_text` no-op messages.

---

## Next concrete implementation tasks

1. Add machine-readable routing policy file and validator script.
2. Add context lifecycle event schemas to Holyfields.
3. Implement agent-local pre-response context hook (self-check + self-heal at 90%).
4. Add Holocene view cards for context state (`healthy/watch/compact/restarting`).
5. Add heartbeat config loader (global + per-agent) and event dispatcher.

---

## Success criteria

- Duplicate workspace placements drop to zero.
- No manual “please reset context” messages needed.
- No empty hook no-op messages in user channel.
- Heartbeat actions execute through Bloodbank events with traceable cause.
- Morning overview is understandable at a glance.
