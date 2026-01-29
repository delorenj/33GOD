# Bloodbank Team Alignment Brief

## Vision Context

**Unified Event Architecture** positions Bloodbank as the intelligent gateway for all 33GOD event traffic. Your component transforms from a simple message router into a validation-enrichment layer that enforces schema contracts and ensures zero data loss.

**Your role in the vision:**
- Primary enforcement point for EventEnvelope standardization
- First line of schema validation (before RabbitMQ)
- Correlation ID propagation source
- Observability instrumentation origin

## Your Key Requirements

### Critical (Must Complete First)

| Requirement | Type | Source |
|-------------|------|--------|
| Implement Dead Letter Queue (DLQ) | Functional | CONVERGENCE_REPORT.md #1 |
| Add envelope validation before publish | Functional | CROSS_COMPONENT_MISALIGNMENTS.md 3.2 |
| Fix schema validation path mapping | Functional | CONVERGENCE_REPORT.md #6 |
| Integrate CorrelationTracker into publish flow | Functional | CROSS_COMPONENT_MISALIGNMENTS.md 3.6 |

### High Priority

| Requirement | Type | Source |
|-------------|------|--------|
| Add `/health` and `/health/ready` endpoints | Non-functional | CROSS_COMPONENT_MISALIGNMENTS.md 4.4 |
| Add Prometheus metrics (events_published, latency) | Non-functional | CROSS_COMPONENT_MISALIGNMENTS.md 4.5 |
| Implement retry logic with exponential backoff | Non-functional | CROSS_COMPONENT_MISALIGNMENTS.md 4.3 |
| Add rate limiting (slowapi) | Security | CROSS_COMPONENT_MISALIGNMENTS.md 5.2 |

### Medium Priority

| Requirement | Type | Source |
|-------------|------|--------|
| Add OpenTelemetry trace propagation | Non-functional | CONVERGENCE_REPORT.md 6.2 |
| Implement event signing (HMAC) | Security | CROSS_COMPONENT_MISALIGNMENTS.md 5.1 |

## Dependencies on Others

| Dependency | From Team | Status | Notes |
|------------|-----------|--------|-------|
| Canonical EventEnvelope schema | Holyfields | NEEDED | Must define before you can validate |
| Schema file path standardization | Holyfields | NEEDED | Current paths don't match validator expectations |
| Generated Pydantic models | Holyfields | NEEDED | Replace hand-written models in `events/domains/` |

## Others Depend on You

| Deliverable | For Team | Priority | Impact |
|-------------|----------|----------|--------|
| DLQ routing | Candystore | CRITICAL | Without DLQ, failed messages are lost forever |
| Validated envelopes | Candystore | CRITICAL | Invalid events corrupt database |
| Correlation IDs populated | Candystore, Candybar | HIGH | Required for event traceability |
| Health endpoints | DevOps | HIGH | Required for Kubernetes readiness probes |
| Prometheus metrics | DevOps | HIGH | Required for monitoring dashboards |

## Potential Conflicts

### Conflict: Schema Validation Performance
- **With:** All consumers (latency impact)
- **Nature:** Adding validation at publish may increase latency
- **Resolution:** Cache compiled schemas, async validation, sampling (100% dev, 10% prod)
- **Escalation:** Architecture Team

### Conflict: Breaking Change to EventEnvelope
- **With:** Candybar, Candystore
- **Nature:** Standardizing envelope structure requires all consumers to update
- **Resolution:** Dual-publish during transition (old + new format for 2 weeks)
- **Escalation:** Engineering Leadership

## Recommended Actions

1. **Immediately:** Configure RabbitMQ DLX (Dead Letter Exchange) with `bloodbank.events.dlq`
2. **Immediately:** Update consumer queue declarations with `x-dead-letter-exchange` argument
3. **This sprint:** Add envelope validation using jsonschema (already in dependencies)
4. **This sprint:** Integrate CorrelationTracker.track() into publish flow
5. **Next sprint:** Add health endpoints and Prometheus metrics
6. **Next sprint:** Implement rate limiting with slowapi

## Questions to Resolve

1. What latency budget is acceptable for validation overhead?
2. Should validation be async (fire-and-forget) or blocking?
3. What sampling rate for production validation (100%, 10%, 1%)?
4. Who owns the DLQ monitoring dashboard?
