# Candybar Team Alignment Brief

## Vision Context

**Unified Event Architecture** makes Candybar a type-safe, real-time window into the entire event ecosystem. Your monitoring UI transforms from a manually-synchronized consumer into a generated-types consumer with runtime validation.

**Your role in the vision:**
- Visualize events using types generated from Holyfields schemas
- Validate incoming events at runtime with Zod
- Provide real-time observability for the entire event pipeline
- Serve as the developer-facing verification tool for event flow

## Your Key Requirements

### Critical (Must Complete First)

| Requirement | Type | Source |
|-------------|------|--------|
| Replace hand-written types with Holyfields-generated types | Functional | CROSS_COMPONENT_MISALIGNMENTS.md 3.4 |
| Add `version` field to BloodbankEvent interface | Functional | CROSS_COMPONENT_MISALIGNMENTS.md 1.4 |
| Add runtime validation with Zod | Functional | CONVERGENCE_REPORT.md 2.1.3 |

### High Priority

| Requirement | Type | Source |
|-------------|------|--------|
| Generate TypeScript client from Candystore OpenAPI | Functional | CROSS_COMPONENT_MISALIGNMENTS.md 3.5 |
| Implement auto-reconnect with exponential backoff | Non-functional | DIRECTOR_FINAL_REPORT.md 2.3 |
| Add unit tests (Rust + TypeScript) | Non-functional | DIRECTOR_FINAL_REPORT.md 2.3 |

### Medium Priority

| Requirement | Type | Source |
|-------------|------|--------|
| Add event persistence (IndexedDB) | Functional | DIRECTOR_FINAL_REPORT.md 2.3 |
| Integrate OS credential managers | Security | DIRECTOR_FINAL_REPORT.md 2.3 |
| Use proper UUID/Date types instead of strings | Functional | CROSS_COMPONENT_MISALIGNMENTS.md 1.1 |

## Dependencies on Others

| Dependency | From Team | Status | Notes |
|------------|-----------|--------|-------|
| Generated TypeScript types | Holyfields | NEEDED | Replace `types/bloodbank.ts` |
| OpenAPI specification | Candystore | NEEDED | Generate REST client |
| Stable EventEnvelope structure | Bloodbank | NEEDED | Current structure may change |

## Others Depend on You

| Deliverable | For Team | Priority | Impact |
|-------------|----------|----------|--------|
| Event visualization | All teams | MEDIUM | Debugging and monitoring tool |
| DLQ monitoring view | DevOps | MEDIUM | Visibility into failed messages |
| Contract test implementation | QA | MEDIUM | Pact tests for Candystore API |

## Potential Conflicts

### Conflict: Type Generation Integration
- **With:** Holyfields
- **Nature:** Need to agree on generated file location and import paths
- **Resolution:** Generated types in `src/types/generated/`, manual types removed
- **Escalation:** None needed

### Conflict: EventEnvelope Breaking Changes
- **With:** Bloodbank
- **Nature:** Adding `version` field and fixing types requires code changes
- **Resolution:** Coordinate with Bloodbank on dual-publish timeline
- **Escalation:** Engineering Leadership if timeline conflict

## Recommended Actions

1. **Immediately:** Add `version: string` to BloodbankEvent interface (temporary fix)
2. **This sprint:** Create `src/types/generated/` directory for Holyfields output
3. **This sprint:** Update imports to use generated types once available
4. **This sprint:** Add Zod runtime validation at RabbitMQ message handler
5. **Next sprint:** Generate Candystore API client from OpenAPI
6. **Next sprint:** Implement auto-reconnect for RabbitMQ connection

## Questions to Resolve

1. Where should generated TypeScript types be placed in repo?
2. Should Zod validation errors be displayed to user or just logged?
3. What reconnection strategy for RabbitMQ (exponential backoff parameters)?
4. Should invalid events be shown in UI with warning, or filtered out?
