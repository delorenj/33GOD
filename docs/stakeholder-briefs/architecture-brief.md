# Architecture Team Alignment Brief

## Vision Context

**Unified Event Architecture** requires strong governance to prevent the schema drift and type divergence that created the current 23 misalignments. Your team transforms from reactive reviewers into proactive guardians of architectural integrity.

**Your role in the vision:**
- Define and enforce the canonical EventEnvelope structure
- Own the schema change RFC process
- Set SLIs/SLOs for the event pipeline
- Arbitrate cross-team conflicts on breaking changes

## Your Key Requirements

### Critical (Must Complete First)

| Requirement | Type | Source |
|-------------|------|--------|
| Approve canonical EventEnvelope structure | Decision | CONVERGENCE_REPORT.md 5.1 |
| Define schema versioning rules | Process | CONVERGENCE_REPORT.md 5.3 |
| Establish code review standards for events | Process | CONVERGENCE_REPORT.md 8.2 |

### High Priority

| Requirement | Type | Source |
|-------------|------|--------|
| Create schema change RFC template | Process | CONVERGENCE_REPORT.md 8.1.1 |
| Define SLIs/SLOs for event pipeline | Non-functional | CONVERGENCE_REPORT.md 8.4.1 |
| Approve domain naming (Fireflies vs WhisperLiveKit) | Decision | CROSS_COMPONENT_MISALIGNMENTS.md 1.3 |

### Medium Priority

| Requirement | Type | Source |
|-------------|------|--------|
| Define breaking change deprecation timeline | Process | CONVERGENCE_REPORT.md 5.3 |
| Establish quality gates for CI/CD | Process | CONVERGENCE_REPORT.md 8.3 |

## Dependencies on Others

| Dependency | From Team | Status | Notes |
|------------|-----------|--------|-------|
| Current EventEnvelope implementations | All | AVAILABLE | Review for synthesis |
| Event type inventory | Bloodbank | AVAILABLE | Review `events/types.py` |
| Storage requirements | Candystore | AVAILABLE | Review `models.py` |

## Others Depend on You

| Deliverable | For Team | Priority | Impact |
|-------------|----------|----------|--------|
| EventEnvelope approval | Holyfields | CRITICAL | BLOCKING - Cannot generate types without approved schema |
| Domain naming decision | Holyfields, Bloodbank | HIGH | Resolves Fireflies/WhisperLiveKit confusion |
| SLI/SLO definitions | DevOps | MEDIUM | Alert thresholds |
| RFC process | All teams | MEDIUM | Schema change governance |

## Decisions Required

### Decision 1: Canonical EventEnvelope Structure

**Options:**

A. **Bloodbank-based** (recommended)
```json
{
  "event_id": "uuid",
  "event_type": "string",
  "timestamp": "date-time",
  "version": "string",
  "source": { "host": "string", "type": "enum", "app": "string", "meta": "object" },
  "correlation_ids": ["uuid"],
  "agent_context": { ... },
  "payload": { ... },
  "trace_context": { "trace_id": "string", "span_id": "string" }
}
```

B. **Minimal** (smaller, faster, less context)
```json
{
  "event_id": "uuid",
  "event_type": "string",
  "timestamp": "date-time",
  "payload": { ... }
}
```

**Recommendation:** Option A - preserves traceability, supports future needs

### Decision 2: Domain Naming

**Options:**
- A: `fireflies.*` (user-facing brand)
- B: `whisperlivekit.*` (technical implementation)
- C: `voice.transcription.*` (domain-agnostic)

**Recommendation:** Option C - allows switching implementations without event type changes

### Decision 3: Breaking Change Timeline

**Options:**
- A: 90 days deprecation, 180 days removal
- B: 30 days deprecation, 60 days removal
- C: No deprecation, immediate breaking changes

**Recommendation:** Option A for production safety

## Potential Conflicts

### Conflict: Schema Approval Speed
- **With:** Holyfields
- **Nature:** Holyfields blocked until Architecture approves canonical schema
- **Resolution:** Expedite review, target 1-2 day turnaround
- **Escalation:** Engineering Leadership if delayed

### Conflict: Breaking Change Resistance
- **With:** All consumer teams
- **Nature:** Standardization requires breaking changes that teams resist
- **Resolution:** Dual-publish strategy, clear migration timeline
- **Escalation:** Engineering Leadership

## Recommended Actions

1. **Immediately:** Review and approve canonical EventEnvelope structure from CONVERGENCE_REPORT.md 5.1
2. **Immediately:** Decide on Fireflies/WhisperLiveKit/voice.transcription naming
3. **This sprint:** Create schema change RFC template (use CONVERGENCE_REPORT.md 8.1.1 as base)
4. **This sprint:** Define SLIs/SLOs using CONVERGENCE_REPORT.md 8.4.1 table
5. **Next sprint:** Establish code review checklist for event-related PRs
6. **Next sprint:** Document governance process in Architecture Decision Records (ADRs)

## Questions to Resolve

1. How many architects required to approve schema RFCs?
2. What is the escalation path for schema change conflicts?
3. Should SLOs be different for dev/staging/prod environments?
4. Who owns the schema governance documentation?
