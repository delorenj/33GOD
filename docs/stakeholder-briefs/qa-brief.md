# QA Team Alignment Brief

## Vision Context

**Unified Event Architecture** requires comprehensive testing to prevent the type drift and integration failures identified in the audit. Your team transforms from manual testing into automated contract testing and continuous validation.

**Your role in the vision:**
- Implement contract tests between all component pairs
- Validate schema changes don't break consumers
- Ensure 100% correlation tracking coverage
- Verify DLQ handling prevents data loss

## Your Key Requirements

### Critical (Must Complete First)

| Requirement | Type | Source |
|-------------|------|--------|
| Implement contract tests (Candybar ↔ Candystore) | Testing | CROSS_COMPONENT_MISALIGNMENTS.md 3.5 |
| Add E2E tests for full event flow | Testing | CONVERGENCE_REPORT.md 7.1 |
| Verify DLQ captures all failed messages | Testing | CONVERGENCE_REPORT.md 7.2 |

### High Priority

| Requirement | Type | Source |
|-------------|------|--------|
| Schema compatibility tests | Testing | CONVERGENCE_REPORT.md 7.1 |
| Correlation tracking validation | Testing | CONVERGENCE_REPORT.md 10.2 |
| Integration tests with real RabbitMQ + PostgreSQL | Testing | DIRECTOR_FINAL_REPORT.md 2.4 |

### Medium Priority

| Requirement | Type | Source |
|-------------|------|--------|
| Performance/load testing | Testing | CONVERGENCE_REPORT.md 7.2 |
| Security testing (event signing) | Testing | CROSS_COMPONENT_MISALIGNMENTS.md 5.1 |

## Dependencies on Others

| Dependency | From Team | Status | Notes |
|------------|-----------|--------|-------|
| OpenAPI specification | Candystore | NEEDED | Required for contract tests |
| DLQ configuration | DevOps | NEEDED | Required for DLQ validation tests |
| Stable EventEnvelope | Architecture | NEEDED | Test against canonical structure |

## Others Depend on You

| Deliverable | For Team | Priority | Impact |
|-------------|----------|----------|--------|
| Contract test suite | All teams | HIGH | Catch breaking changes before deploy |
| E2E test pipeline | All teams | HIGH | Validate full event flow |
| Test coverage reports | Engineering Leadership | MEDIUM | Quality metrics |

## Potential Conflicts

### Conflict: Test Environment Resources
- **With:** DevOps
- **Nature:** Integration tests require RabbitMQ + PostgreSQL containers
- **Resolution:** Use docker-compose for CI, shared staging for E2E
- **Escalation:** Engineering Leadership

### Conflict: Test Coverage Goals
- **With:** All teams
- **Nature:** 100% coverage may slow development
- **Resolution:** Focus on critical paths (envelope validation, correlation, DLQ)
- **Escalation:** Architecture Team

## Recommended Actions

1. **Immediately:** Create docker-compose for integration test environment
2. **This sprint:** Implement Pact contract tests for Candybar ↔ Candystore
3. **This sprint:** Add E2E test: Producer → Bloodbank → Candystore → Query
4. **Next sprint:** Add correlation tracking validation tests
5. **Next sprint:** Add DLQ capture verification tests
6. **Future:** Performance testing with k6 or locust

## Test Strategy

### Contract Tests (Pact)

```typescript
// Candybar expects from Candystore
describe('Event Query Contract', () => {
  it('returns events with correlation_ids array', async () => {
    await provider
      .uponReceiving('a request for events by session')
      .withRequest({ method: 'GET', path: '/events', query: { session_id: '...' } })
      .willRespondWith({
        status: 200,
        body: {
          events: eachLike({
            event_id: string(),
            event_type: string(),
            correlation_ids: eachLike(string()),  // MUST be array
            agent_context: like({})                // MUST be present
          })
        }
      });
  });
});
```

### E2E Tests

```python
async def test_full_event_flow():
    # 1. Publish event via Bloodbank
    envelope = create_test_envelope('fireflies.transcript.ready')
    await bloodbank.publish(envelope)

    # 2. Wait for Candystore persistence
    await asyncio.sleep(0.5)

    # 3. Query Candystore
    stored = await candystore.get_event(envelope.event_id)

    # 4. Verify full fidelity
    assert stored.event_id == envelope.event_id
    assert stored.correlation_ids == envelope.correlation_ids
    assert stored.agent_context is not None
    assert stored.version == envelope.version
```

### DLQ Validation

```python
async def test_failed_message_routed_to_dlq():
    # 1. Publish malformed event
    malformed = {"event_type": "invalid"}  # Missing required fields
    await bloodbank.publish_raw(malformed)

    # 2. Check DLQ
    dlq_message = await dlq_consumer.get_message(timeout=5)

    # 3. Verify routing
    assert dlq_message is not None
    assert dlq_message.routing_key == "dlq.candystore"
```

## Questions to Resolve

1. What CI resources available for integration tests (Docker-in-Docker)?
2. Contract test ownership (QA writes, developers maintain)?
3. E2E test frequency (every PR, nightly, weekly)?
4. Performance test baseline targets (events/sec, latency P99)?

## QA Validation Findings (Meta)

Per QA_VALIDATION_REPORT.md, the cross-component analysis had 82% truth factor with 3 errors:
1. Candystore `correlation_ids` is correctly plural ✓
2. Candystore `agent_context` is persisted ✓
3. Bloodbank `jsonschema` dependency exists ✓

**Lesson:** Always verify claims against actual source code before testing.
