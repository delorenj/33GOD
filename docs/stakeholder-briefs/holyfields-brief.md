# Holyfields Team Alignment Brief

## Vision Context

**Unified Event Architecture** makes Holyfields the single source of truth for all event contracts. Your schema registry transforms from documentation into an active enforcement mechanism that generates code for every component.

**Your role in the vision:**
- Define the canonical EventEnvelope structure that ALL components must use
- Generate type-safe code for Python (Pydantic), TypeScript (Zod), and SQL (SQLAlchemy)
- Provide CI validation that fails builds when schemas and code diverge
- Own the schema change governance process (RFCs, versioning, deprecation)

## Your Key Requirements

### Critical (Must Complete First)

| Requirement | Type | Source |
|-------------|------|--------|
| Define canonical EventEnvelope in `schemas/core/event-envelope.v1.schema.json` | Functional | CONVERGENCE_REPORT.md 5.1 |
| Standardize schema directory structure | Functional | CONVERGENCE_REPORT.md 5.2 |
| Implement Python code generator (datamodel-code-generator) | Functional | CROSS_COMPONENT_MISALIGNMENTS.md 3.1 |
| Implement TypeScript code generator (json-schema-to-zod) | Functional | CROSS_COMPONENT_MISALIGNMENTS.md 3.1 |

### High Priority

| Requirement | Type | Source |
|-------------|------|--------|
| Resolve Fireflies vs WhisperLiveKit domain naming | Functional | CROSS_COMPONENT_MISALIGNMENTS.md 1.3 |
| Add TheBoard schemas with `theboard.*` prefix | Functional | CROSS_COMPONENT_MISALIGNMENTS.md 1.2 |
| Create CI pipeline for schema validation | Non-functional | CONVERGENCE_REPORT.md 8.1.1 |
| Implement SQL/SQLAlchemy generator | Functional | CONVERGENCE_REPORT.md 5.2 |

### Medium Priority

| Requirement | Type | Source |
|-------------|------|--------|
| Add Rust bindings generator for Candybar | Functional | DIRECTOR_FINAL_REPORT.md 2.3 |
| Create schema change RFC template | Process | CONVERGENCE_REPORT.md 8.1.1 |

## Dependencies on Others

| Dependency | From Team | Status | Notes |
|------------|-----------|--------|-------|
| Event type inventory | Bloodbank | AVAILABLE | Review `events/types.py` for complete list |
| Field requirements | Candystore | AVAILABLE | Review `models.py` for storage needs |
| TypeScript type needs | Candybar | AVAILABLE | Review `types/bloodbank.ts` for UI needs |

## Others Depend on You

| Deliverable | For Team | Priority | Impact |
|-------------|----------|----------|--------|
| Canonical EventEnvelope schema | Bloodbank | CRITICAL | Cannot implement validation without this |
| Generated Pydantic models | Bloodbank | CRITICAL | Replace 4 hand-written envelope definitions |
| Generated TypeScript types | Candybar | HIGH | Eliminate type drift, add runtime validation |
| Generated SQLAlchemy models | Candystore | HIGH | Ensure database stores all envelope fields |
| Schema file paths | Bloodbank | HIGH | SchemaValidator needs correct paths |

## Potential Conflicts

### Conflict: Domain Naming (Fireflies vs WhisperLiveKit)
- **With:** Bloodbank, Candybar
- **Nature:** Two names for same transcription domain
- **Resolution Options:**
  - A: Standardize on `fireflies` (user-facing brand)
  - B: Standardize on `whisperlivekit` (technical name)
  - C: Use `voice.transcription.*` (domain-agnostic)
- **Recommendation:** Option C for future flexibility
- **Escalation:** Architecture Team

### Conflict: TheBoard Event Prefix
- **With:** Bloodbank
- **Nature:** Bloodbank uses `meeting.*`, schemas expect `theboard.*`
- **Resolution:** Bloodbank updates to use `theboard.*` prefix
- **Escalation:** None needed (clear fix)

## Recommended Actions

1. **Immediately:** Create `schemas/core/event-envelope.v1.schema.json` with canonical structure
2. **Immediately:** Reorganize schema directories to match expected paths:
   ```
   schemas/
   ├── core/
   │   └── event-envelope.v1.schema.json
   ├── fireflies/
   │   ├── transcript.upload.v1.schema.json
   │   └── transcript.ready.v1.schema.json
   └── theboard/
       ├── meeting.created.v1.schema.json
       └── meeting.started.v1.schema.json
   ```
3. **This sprint:** Implement `npm run generate:python` using datamodel-code-generator
4. **This sprint:** Implement `npm run generate:typescript` using json-schema-to-zod
5. **Next sprint:** Add CI job that regenerates types and fails if drift detected
6. **Next sprint:** Create RFC process for schema changes

## Questions to Resolve

1. Final decision on Fireflies vs WhisperLiveKit vs voice.transcription domain naming?
2. Should generated code live in Holyfields repo or be published as packages?
3. What is the deprecation timeline for breaking schema changes (90 days? 180 days)?
4. Who approves schema change RFCs?
