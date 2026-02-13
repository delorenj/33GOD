# Phase 1 Complete: Holyfields Schema Reorganization

> **Date**: 2026-02-12  
> **Status**: ✅ COMPLETE  
> **Phase**: 1 of 4  
> **Owner**: Lenoon (Infrastructure Domain)

---

## Summary

Successfully reorganized Holyfields schema registry with 47 v1 schemas covering all 33 event domains.

### What Was Done

1. **Created new base event schema** (`_common/base_event.v1.json`)
   - Removed TheBoard-specific `meeting_id` from base
   - Added generic fields: `event_id`, `timestamp`, `version`, `correlation_id`, `source`
   - Source metadata includes: `host`, `app`, `trigger_type`, `user_id`

2. **Created TheBoard extension** (`_common/theboard_extension.v1.json`)
   - `meeting_id` now lives here
   - TheBoard events use `allOf` to extend both base and extension

3. **Migrated 47 schemas to new structure**

### Schema Inventory (47 total)

| Domain | Count | Files |
|--------|-------|-------|
| `_common` | 3 | base_event, theboard_extension, types |
| `agent` | 18 | 12 lifecycle + 3 thread + 2 feedback + 1 state |
| `agent/thread` | 3 | prompt, response, error |
| `agent/feedback` | 2 | requested, response |
| `artifact` | 2 | lifecycle, ingestion.failed |
| `conversation` | 1 | message.posted |
| `fireflies` | 4 | upload, ready, processed, failed |
| `github` | 1 | pr.created |
| `llm` | 3 | prompt, response, error (DEPRECATED) |
| `session` | 6 | thread.start, end, message, agent.action, agent.thinking, error |
| `session/thread/agent` | 2 | action, thinking |
| `task` | 2 | step.proposed, step.executed |
| `theboard` | 7 | meeting.created, started, round_completed, comment_extracted, converged, completed, failed |

### New Directory Structure

```
holyfields/schemas/
├── _common/
│   ├── base_event.v1.json          # Generic base (no meeting_id)
│   ├── theboard_extension.v1.json  # Adds meeting_id
│   └── types.v1.json               # Shared $defs
├── agent/
│   ├── error.v1.json
│   ├── heartbeat.v1.json
│   ├── message.received.v1.json
│   ├── message.sent.v1.json
│   ├── session.ended.v1.json
│   ├── session.started.v1.json
│   ├── state.changed.v1.json
│   ├── subagent.completed.v1.json
│   ├── subagent.spawned.v1.json
│   ├── task.assigned.v1.json
│   ├── task.completed.v1.json
│   ├── tool.completed.v1.json
│   ├── tool.invoked.v1.json
│   ├── feedback/
│   │   ├── requested.v1.json
│   │   └── response.v1.json
│   └── thread/
│       ├── error.v1.json
│       ├── prompt.v1.json
│       └── response.v1.json
├── artifact/
│   ├── ingestion.failed.v1.json
│   └── lifecycle.v1.json
├── conversation/
│   └── message.posted.v1.json
├── fireflies/
│   └── transcript/
│       ├── failed.v1.json
│       ├── processed.v1.json
│       ├── ready.v1.json
│       └── upload.v1.json
├── github/
│   └── pr.created.v1.json
├── llm/
│   ├── error.v1.json       # DEPRECATED
│   ├── prompt.v1.json      # DEPRECATED
│   └── response.v1.json    # DEPRECATED
├── session/
│   └── thread/
│       ├── agent/
│       │   ├── action.v1.json
│       │   └── thinking.v1.json
│       ├── end.v1.json
│       ├── error.v1.json
│       ├── message.v1.json
│       └── start.v1.json
├── task/
│   ├── step.executed.v1.json
│   └── step.proposed.v1.json
└── theboard/
    ├── meeting.comment_extracted.v1.json
    ├── meeting.completed.v1.json
    ├── meeting.converged.v1.json
    ├── meeting.created.v1.json
    ├── meeting.failed.v1.json
    ├── meeting.round_completed.v1.json
    └── meeting.started.v1.json
```

### Updated Generator Scripts

- `scripts/generate_python.sh` — Updated for v1 structure
- `scripts/generate_typescript.sh` — Updated for v1 structure

Both scripts now:
- Discover schemas from nested directory structure
- Generate models with proper imports
- Include deprecation notices for LLM events

### Key Design Decisions

1. **Envelope/Payload Pattern**: All events have `event_type` + `payload` structure
2. **Version Suffix**: All files use `.v1.json` suffix for side-by-side versioning
3. **Dot Notation**: Files use dots to match routing keys (e.g., `message.received.v1.json`)
4. **Extensions**: Domain-specific fields added via `allOf` composition
5. **Deprecations**: LLM events marked as deprecated with migration path to `agent.thread.*`

### Bloodbank Exchange Alignment

Per Grolf's note: Exchange name is `bloodbank.events.v1` — already aligned with schema versioning.

### Next Steps (Phase 2)

1. Run updated generators to create Python/TypeScript artifacts
2. Verify generated code compiles/validates
3. Create ROUTING_KEYS manifest for Bloodbank
4. Update Bloodbank imports to use Holyfields

### Files Modified/Created

- `schemas/_common/base_event.v1.json` (NEW)
- `schemas/_common/theboard_extension.v1.json` (NEW)
- `schemas/_common/types.v1.json` (NEW)
- `schemas/agent/*.v1.json` (18 NEW)
- `schemas/artifact/*.v1.json` (2 NEW)
- `schemas/conversation/*.v1.json` (1 NEW)
- `schemas/fireflies/**/*.v1.json` (4 NEW)
- `schemas/github/*.v1.json` (1 NEW)
- `schemas/llm/*.v1.json` (3 NEW, deprecated)
- `schemas/session/**/*.v1.json` (6 NEW)
- `schemas/task/*.v1.json` (2 NEW)
- `schemas/theboard/*.v1.json` (7 NEW)
- `scripts/generate_python.sh` (UPDATED)
- `scripts/generate_typescript.sh` (UPDATED)
- Deleted old schemas from `schemas/agent/state_changed.json`, `schemas/conversation/message_posted.json`, `schemas/task/step_executed.json`, `schemas/task/step_proposed.json`

### Verification

```bash
# Count v1 schemas
find holyfields/schemas -name "*.v1.json" | wc -l
# Output: 47

# Verify structure
ls -la holyfields/schemas/_common/
ls -la holyfields/schemas/agent/
ls -la holyfields/schemas/theboard/
```

---

**Ready for Phase 2: Generator Execution and Validation**

The foundation is solid. Schemas are versioned, organized, and properly structured. Bloodbank can now import from Holyfields instead of defining inline.

— Lenoon 🦎
