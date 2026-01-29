# Candystore Team Alignment Brief

## Vision Context

**Unified Event Architecture** makes Candystore the authoritative event store that preserves full-fidelity EventEnvelopes. Your storage layer transforms from a field-dropping consumer into a complete audit trail with correlation chain queries.

**Your role in the vision:**
- Store complete EventEnvelope without dropping fields
- Validate events before persistence (defense in depth)
- Provide correlation chain query APIs for traceability
- Expose OpenAPI spec for type-safe client generation

## Your Key Requirements

### Critical (Must Complete First)

| Requirement | Type | Source |
|-------------|------|--------|
| Add envelope validation before storage | Functional | CROSS_COMPONENT_MISALIGNMENTS.md 3.2 |
| Never ack failed messages (route to DLQ) | Functional | CONVERGENCE_REPORT.md #1 |
| Export OpenAPI specification | Functional | CROSS_COMPONENT_MISALIGNMENTS.md 3.5 |

### High Priority

| Requirement | Type | Source |
|-------------|------|--------|
| Add correlation chain query API | Functional | CROSS_COMPONENT_MISALIGNMENTS.md 3.6 |
| Complete workflow state projection | Functional | DIRECTOR_FINAL_REPORT.md 2.4 |
| Add integration tests | Non-functional | DIRECTOR_FINAL_REPORT.md 2.4 |

### Medium Priority

| Requirement | Type | Source |
|-------------|------|--------|
| Implement WebSocket streaming | Functional | DIRECTOR_FINAL_REPORT.md 2.4 |
| Add OpenTelemetry distributed tracing | Non-functional | DIRECTOR_FINAL_REPORT.md 2.4 |
| Enhance Prometheus metrics | Non-functional | CONVERGENCE_REPORT.md 6.2 |

## Dependencies on Others

| Dependency | From Team | Status | Notes |
|------------|-----------|--------|-------|
| DLQ configuration in RabbitMQ | Bloodbank/DevOps | NEEDED | Must have DLQ before changing ack behavior |
| Canonical EventEnvelope schema | Holyfields | NEEDED | Validation requires schema |
| Generated SQLAlchemy models | Holyfields | OPTIONAL | Can use manual models initially |

## Others Depend on You

| Deliverable | For Team | Priority | Impact |
|-------------|----------|----------|--------|
| OpenAPI specification | Candybar | HIGH | Generate TypeScript client |
| Correlation query API | All teams | HIGH | Event chain traceability |
| Complete event storage | QA, Audit | CRITICAL | Audit trail completeness |

## Potential Conflicts

### Conflict: DLQ Behavior Change
- **With:** Bloodbank/DevOps
- **Nature:** Cannot stop acking failed messages until DLQ exists
- **Resolution:** Bloodbank must configure DLQ FIRST, then Candystore changes ack behavior
- **Escalation:** Engineering Leadership if Bloodbank delays

### Conflict: Database Migration Downtime
- **With:** All teams
- **Nature:** Schema changes may require downtime
- **Resolution:** Use zero-downtime migration strategy (add columns nullable, backfill, switch reads, drop old)
- **Escalation:** DevOps

## Recommended Actions

1. **Immediately:** Verify DLQ exists before changing ack behavior (coordinate with Bloodbank)
2. **Immediately:** Add envelope validation layer using jsonschema
3. **This sprint:** Export OpenAPI spec (FastAPI does this automatically at `/openapi.json`)
4. **This sprint:** Add `GET /events/trace/{correlation_id}` endpoint
5. **Next sprint:** Add integration tests with RabbitMQ + PostgreSQL containers
6. **Next sprint:** Implement WebSocket streaming for real-time event push

## Questions to Resolve

1. What is the retention policy for stored events?
2. Should correlation chain queries return full events or summaries?
3. What database indexing strategy for correlation_ids (GIN index on JSONB)?
4. WebSocket auth mechanism (JWT, session cookie)?

## QA Validation Notes

Per QA_VALIDATION_REPORT.md, the following claims were **verified accurate** for Candystore:
- `correlation_ids` is correctly plural (list[UUID])
- `agent_context` is persisted (dict[str, Any] | None)
- `source` is stored as dict (not flattened to string)

No corrections needed for Candystore model claims.
