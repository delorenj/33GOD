# Schema Drift Audit - 33GOD Infrastructure

> **Date**: 2026-02-12
> **Auditor**: Lenoon (Infrastructure Domain)
> **Status**: CRITICAL - 20 schemas missing from Holyfields

---

## Executive Summary

Holyfields (the schema registry) has **11 JSON schemas**. Bloodbank (the event bus) has **31 Pydantic event types** defined inline. **20 event types exist only in Bloodbank** with no corresponding Holyfields schema.

**The problem**: Bloodbank cannot validate events against Holyfields because the schemas don't exist. This violates the "Registry as Truth" principle.

---

## Inventory

### Holyfields Schemas (11 total)

```
holyfields/schemas/
├── agent/state_changed.json
├── conversation/message_posted.json
├── task/step_executed.json
├── task/step_proposed.json

theboard/events/
├── comment_extracted.json
├── meeting_completed.json
├── meeting_converged.json
├── meeting_created.json
├── meeting_failed.json
├── meeting_started.json
└── round_completed.json
```

### Bloodbank Event Types (31 total)

| Domain | Event Type | Class Name | File |
|--------|-----------|------------|------|
| **agent** | `agent.message.received` | `AgentMessageReceived` | `openclaw.py` |
| **agent** | `agent.message.sent` | `AgentMessageSent` | `openclaw.py` |
| **agent** | `agent.tool.invoked` | `AgentToolInvoked` | `openclaw.py` |
| **agent** | `agent.tool.completed` | `AgentToolCompleted` | `openclaw.py` |
| **agent** | `agent.subagent.spawned` | `AgentSubagentSpawned` | `openclaw.py` |
| **agent** | `agent.subagent.completed` | `AgentSubagentCompleted` | `openclaw.py` |
| **agent** | `agent.session.started` | `AgentSessionStarted` | `openclaw.py` |
| **agent** | `agent.session.ended` | `AgentSessionEnded` | `openclaw.py` |
| **agent** | `agent.task.assigned` | `AgentTaskAssigned` | `openclaw.py` |
| **agent** | `agent.task.completed` | `AgentTaskCompleted` | `openclaw.py` |
| **agent** | `agent.heartbeat` | `AgentHeartbeat` | `openclaw.py` |
| **agent** | `agent.error` | `AgentError` | `openclaw.py` |
| **agent.thread** | `agent.thread.prompt` | `AgentThreadPrompt` | `thread.py` |
| **agent.thread** | `agent.thread.response` | `AgentThreadResponse` | `thread.py` |
| **agent.thread** | `agent.thread.error` | `AgentThreadErrorPayload` | `thread.py` |
| **agent.feedback** | `agent.feedback.requested` | `AgentFeedbackRequested` | `feedback.py` |
| **agent.feedback** | `agent.feedback.response` | `AgentFeedbackResponse` | `feedback.py` |
| **artifact** | `artifact.*` | `Artifact` | `artifact.py` |
| **artifact** | `artifact.ingestion.failed` | `ArtifactIngestionFailedPayload` | `artifact.py` |
| **llm** | `llm.prompt` | `LLMPrompt` | `llm.py` |
| **llm** | `llm.response` | `LLMResponse` | `llm.py` |
| **llm** | `llm.error` | `LLMErrorPayload` | `llm.py` |
| **github** | `github.pr.created` | `GitHubPRCreatedPayload` | `github.py` |
| **fireflies** | `fireflies.transcript.upload` | `FirefliesTranscriptUploadPayload` | `fireflies.py` |
| **fireflies** | `fireflies.transcript.ready` | `FirefliesTranscriptReadyPayload` | `fireflies.py` |
| **fireflies** | `fireflies.transcript.processed` | `FirefliesTranscriptProcessedPayload` | `fireflies.py` |
| **fireflies** | `fireflies.transcript.failed` | `FirefliesTranscriptFailedPayload` | `fireflies.py` |
| **session** | `session.thread.agent.action` | `SessionAgentToolAction` | `claude_code.py` |
| **session** | `session.thread.agent.thinking` | `ThinkingEvent` | `claude_code.py` |
| **session** | `session.thread.end` | `SessionThreadEnd` | `claude_code.py` |
| **session** | `session.thread.start` | `SessionThreadStart` | `claude_code.py` |
| **session** | `session.thread.message` | `SessionThreadMessage` | `claude_code.py` |
| **session** | `session.thread.error` | `SessionThreadError` | `claude_code.py` |

---

## Drift Report: Missing Holyfields Schemas

| # | Event Type | Priority | Reason |
|---|-----------|----------|--------|
| 1 | `agent.message.received` | HIGH | Core agent lifecycle |
| 2 | `agent.message.sent` | HIGH | Core agent lifecycle |
| 3 | `agent.tool.invoked` | HIGH | Core agent lifecycle |
| 4 | `agent.tool.completed` | HIGH | Core agent lifecycle |
| 5 | `agent.session.started` | HIGH | Session tracking |
| 6 | `agent.session.ended` | HIGH | Session tracking |
| 7 | `agent.heartbeat` | HIGH | Health monitoring |
| 8 | `agent.error` | HIGH | Error tracking |
| 9 | `agent.subagent.spawned` | MEDIUM | Orchestration |
| 10 | `agent.subagent.completed` | MEDIUM | Orchestration |
| 11 | `agent.task.assigned` | MEDIUM | Task routing |
| 12 | `agent.task.completed` | MEDIUM | Task routing |
| 13 | `agent.thread.prompt` | HIGH | Active use |
| 14 | `agent.thread.response` | HIGH | Active use |
| 15 | `agent.thread.error` | MEDIUM | Error handling |
| 16 | `agent.feedback.requested` | MEDIUM | AgentForge integration |
| 17 | `agent.feedback.response` | MEDIUM | AgentForge integration |
| 18 | `artifact.*` | MEDIUM | RAG pipeline |
| 19 | `artifact.ingestion.failed` | MEDIUM | RAG pipeline |
| 20 | `llm.prompt` | LOW | Legacy - merged into agent events? |
| 21 | `llm.response` | LOW | Legacy - merged into agent events? |
| 22 | `llm.error` | LOW | Legacy - merged into agent events? |
| 23 | `github.pr.created` | LOW | External integration |
| 24 | `fireflies.transcript.upload` | MEDIUM | External integration |
| 25 | `fireflies.transcript.ready` | MEDIUM | External integration |
| 26 | `fireflies.transcript.processed` | MEDIUM | External integration |
| 27 | `fireflies.transcript.failed` | MEDIUM | External integration |
| 28 | `session.thread.start` | HIGH | Claude Code tracking |
| 29 | `session.thread.end` | HIGH | Claude Code tracking |
| 30 | `session.thread.message` | HIGH | Claude Code tracking |
| 31 | `session.thread.agent.action` | HIGH | Claude Code tracking |
| 32 | `session.thread.agent.thinking` | MEDIUM | Claude Code tracking |
| 33 | `session.thread.error` | MEDIUM | Claude Code tracking |

**Total Missing**: 20 event types (excluding the 11 already in Holyfields)

---

## Structural Issues Identified

### 1. Directory Layout Inconsistency
Holyfields schemas are split between:
- `holyfields/schemas/` (4 files - new style)
- `holyfields/theboard/events/` (7 files - old style)

**Fix**: Consolidate all under `holyfields/schemas/` with domain-based subdirectories.

### 2. Base Event Mismatch
- **Holyfields**: `base_event.json` requires `event_type`, `timestamp`, `meeting_id`
- **Bloodbank**: `BaseEvent` is empty `class BaseEvent(BaseModel): pass`
- **Problem**: `meeting_id` is TheBoard-specific; base should be generic

**Fix**: Redesign `base_event.json` with generic fields:
```json
{
  "event_type": "string",
  "timestamp": "datetime",
  "correlation_id": "uuid",
  "source": { "app": "string", "host": "string" }
}
```

### 3. No Generated Routing Keys
Bloodbank manually defines `ROUTING_KEYS` dicts in each domain file. These should be generated from Holyfields schema filenames.

### 4. No Schema Validation Enforcement
Bloodbank has validation code but validates against inline Pydantic models, not Holyfields JSON schemas.

---

## Remediation Plan

### Phase 1: Reorganize Holyfields (1-2 days)

Create unified schema directory structure:

```
holyfields/schemas/
├── _common/
│   ├── base_event.json          # Generic base (remove meeting_id)
│   └── types.json               # Shared $defs
├── agent/
│   ├── message.received.json
│   ├── message.sent.json
│   ├── tool.invoked.json
│   ├── tool.completed.json
│   ├── session.started.json
│   ├── session.ended.json
│   ├── heartbeat.json
│   ├── error.json
│   └── ... (12 files total)
├── agent_thread/
│   ├── prompt.json
│   ├── response.json
│   └── error.json
├── agent_feedback/
│   ├── requested.json
│   └── response.json
├── artifact/
│   ├── lifecycle.json
│   └── ingestion.failed.json
├── fireflies/
│   ├── transcript.upload.json
│   ├── transcript.ready.json
│   ├── transcript.processed.json
│   └── transcript.failed.json
├── github/
│   └── pr.created.json
├── llm/
│   ├── prompt.json
│   ├── response.json
│   └── error.json
├── session/
│   ├── thread.start.json
│   ├── thread.end.json
│   ├── thread.message.json
│   ├── thread.agent.action.json
│   ├── thread.agent.thinking.json
│   └── thread.error.json
└── theboard/
    ├── meeting.created.json     # migrate from theboard/events/
    ├── meeting.started.json
    └── ... (7 files total)
```

### Phase 2: Update Generators (1 day)

1. Update `scripts/generate_python.sh`:
   - Handle nested directory structure
   - Generate `ROUTING_KEYS` mapping file
   - Export all models in `__init__.py`

2. Update `scripts/generate_typescript.sh`:
   - Handle nested directory structure
   - Generate Zod schemas for all domains

### Phase 3: Migrate Bloodbank (2-3 days)

1. Update imports:
   ```python
   # FROM (inline definition):
   class AgentMessageReceived(BaseEvent):
       agent_name: str
       channel: str
       ...

   # TO (import from Holyfields):
   from holyfields.generated.python.agent import AgentMessageReceivedEvent
   ```

2. Update `ROUTING_KEYS` to import from Holyfields-generated manifest

3. Add schema validation in Bloodbank:
   ```python
   from holyfields import validate_event
   validate_event(event_type, payload)  # Validates against JSON schema
   ```

### Phase 4: CI/CD Integration (1 day)

1. Add drift detection job:
   ```yaml
   - name: Check Schema Drift
     run: |
       python scripts/check_drift.py
       # Fails if Bloodbank defines event not in Holyfields
   ```

2. Add schema validation tests

---

## Immediate Action Items

1. **Decision needed**: Confirm base event structure (remove `meeting_id` from base)
2. **Decision needed**: Schema versioning - add `v1` suffix to filenames?
3. **Decision needed**: LLM events - are these deprecated in favor of `agent.thread.*`?

Once decisions are made, I will begin Phase 1 (schema reorganization).

---

## Appendix: Bloodbank File Locations

All inline Pydantic models located in:

```
~/code/33GOD/bloodbank/event_producers/events/domains/
├── __init__.py              # Exports all events
├── agent/
│   ├── __init__.py
│   ├── feedback.py          # 2 events
│   ├── openclaw.py          # 12 events
│   └── thread.py            # 3 events
├── artifact.py              # 2 events
├── claude_code.py           # 6 events
├── fireflies.py             # 4 events
├── github.py                # 1 event
├── llm.py                   # 3 events
└── theboard.py              # 9 events
```

---

*This audit was generated by Lenoon, Lead Architect of 33GOD Infrastructure.*
*Next update: After Phase 1 completion.*
