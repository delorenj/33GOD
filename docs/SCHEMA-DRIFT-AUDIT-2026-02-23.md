# Schema Drift Audit — 2026-02-23

**Auditor:** Lenoon (Infrastructure)  
**Status:** ⚠️ MODERATE DRIFT — models hand-written, not generated

## Summary

| Metric | Count |
|--------|-------|
| Holyfields JSON Schemas (excl _common) | 45 |
| Bloodbank Pydantic BaseEvent classes | 31 |
| Schemas with NO Bloodbank model | 14 |
| Bloodbank models with NO schema | 2 |
| Models generated from schemas | 0 |

## Root Problem

All 31 Bloodbank Pydantic models are **hand-written**, not **generated** from Holyfields schemas. The `generate_python.sh` script exists but produces a single flattened file with only common types — individual event schemas are not generating per-model files.

**Risk:** Any field change in Holyfields won't propagate to Bloodbank models. Schema and runtime types will silently diverge.

## Missing Bloodbank Models (14 schemas with no implementation)

These schemas exist in Holyfields but have no corresponding Pydantic model in Bloodbank:

| Schema | Domain | Notes |
|--------|--------|-------|
| `agent/state.changed.v1.json` | agent | Agent state transitions |
| `agent/thread/prompt.v1.json` | agent | Thread prompts |
| `artifact/ingestion.failed.v1.json` | artifact | Not yet implemented |
| `artifact/lifecycle.v1.json` | artifact | Not yet implemented |
| `asset/created.v1.json` | asset | BB-2 schema exists, model missing |
| `conversation/message.posted.v1.json` | conversation | Not yet implemented |
| `fireflies/transcript/*.v1.json` (×4) | fireflies | Not yet implemented |
| `github/pr.created.v1.json` | github | Not yet implemented |
| `llm/error.v1.json` | llm | Not yet implemented |
| `llm/prompt.v1.json` | llm | Not yet implemented |
| `llm/response.v1.json` | llm | Not yet implemented |
| `task/step.executed.v1.json` | task | Not yet implemented |
| `task/step.proposed.v1.json` | task | Not yet implemented |

## Missing Schemas (2 models with no Holyfields schema)

| Bloodbank Model | File | Notes |
|----------------|------|-------|
| `ParticipantAddedPayload` | `theboard.py` | TheBoard internal event |
| `ParticipantTurnCompletedPayload` | `theboard.py` | TheBoard internal event |

## Generator Status

- **Script:** `holyfields/scripts/generate_python.sh`
- **Tool:** `datamodel-codegen` (installed)
- **Bug:** Heredoc syntax error (fixed: `>>` → `<<`)
- **Issue:** All schemas collapse into single `_internal.py` — needs per-schema output config
- **Action needed:** Configure per-schema generation OR write custom Jinja2 templates

## Recommended Fix Plan

### Phase 1: Fix Generator (2-4 hours)
1. Update `generate_python.sh` to iterate schemas individually
2. Generate one `.py` file per schema with proper Pydantic v2 models
3. Create `__init__.py` that re-exports all models
4. Validate generated models match hand-written ones

### Phase 2: Migrate Bloodbank (4-8 hours)
1. Replace hand-written models with imports from `holyfields.generated.python`
2. Add Holyfields as dependency in Bloodbank's `pyproject.toml`
3. Run full test suite to verify no field drift
4. Remove hand-written model files

### Phase 3: CI Enforcement (1-2 hours)
1. Add CI check: `generate_python.sh` + `git diff --exit-code`
2. If generated files differ from committed → fail CI
3. Prevents silent schema drift going forward

## Production Event Types (from Candystore)

23 unique event types currently flowing in production:
- `agent.{name}.status` (×11 agents)
- `agent.{name}.heartbeat.dispatch` (×9 agents)
- `system.heartbeat` (bridge-emitted)
- `system.heartbeat.tick` (publisher)

Note: Most Holyfields schemas describe events not yet emitted in production.
The bridge currently emits `agent.{name}.status` which has no explicit schema.

---

*Next audit: Run after Phase 1 generator fix.*
