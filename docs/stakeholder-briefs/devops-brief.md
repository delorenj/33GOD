# DevOps/Infrastructure Team Alignment Brief

## Vision Context

**Unified Event Architecture** requires robust infrastructure to support schema validation, dead letter queues, and comprehensive observability. Your infrastructure transforms from basic message routing into an observable, resilient event backbone.

**Your role in the vision:**
- Configure RabbitMQ with Dead Letter Exchanges
- Deploy monitoring stack (Prometheus, Grafana)
- Implement distributed tracing (OpenTelemetry, Jaeger)
- Ensure zero-downtime deployments during migration

## Your Key Requirements

### Critical (Must Complete First)

| Requirement | Type | Source |
|-------------|------|--------|
| Configure RabbitMQ Dead Letter Exchange (DLX) | Infrastructure | CONVERGENCE_REPORT.md #1 |
| Create DLQ monitoring dashboard | Observability | CONVERGENCE_REPORT.md 8.4.2 |
| Deploy Prometheus for all components | Observability | CONVERGENCE_REPORT.md 6.2 |

### High Priority

| Requirement | Type | Source |
|-------------|------|--------|
| Implement Grafana dashboards for event pipeline | Observability | CONVERGENCE_REPORT.md 10.5.1 |
| Configure OpenTelemetry collector | Observability | CROSS_COMPONENT_MISALIGNMENTS.md 4.2 |
| Set up alerting (PagerDuty/Slack) | Observability | CONVERGENCE_REPORT.md 8.4.2 |

### Medium Priority

| Requirement | Type | Source |
|-------------|------|--------|
| TLS for RabbitMQ connections | Security | CONVERGENCE_REPORT.md 7.2 |
| Database backup automation | Disaster Recovery | CONVERGENCE_REPORT.md 7.2 |
| Blue-green deployment for migrations | Infrastructure | CONVERGENCE_REPORT.md 9.1 |

## Dependencies on Others

| Dependency | From Team | Status | Notes |
|------------|-----------|--------|-------|
| Health endpoints | Bloodbank | NEEDED | Required for K8s readiness probes |
| Prometheus metrics | Bloodbank, Candystore | NEEDED | Required for dashboards |
| Alert thresholds | Architecture | NEEDED | Define SLO thresholds |

## Others Depend on You

| Deliverable | For Team | Priority | Impact |
|-------------|----------|----------|--------|
| RabbitMQ DLX configuration | Bloodbank, Candystore | CRITICAL | BLOCKING - Cannot implement DLQ handling without this |
| Prometheus endpoints | All teams | HIGH | Metrics collection |
| Grafana dashboards | All teams | HIGH | Operational visibility |
| Alerting rules | All teams | MEDIUM | Incident detection |

## Potential Conflicts

### Conflict: DLQ Configuration Timing
- **With:** Candystore
- **Nature:** Candystore cannot change ack behavior until DLQ exists
- **Resolution:** DevOps configures DLQ FIRST, notifies Candystore when ready
- **Escalation:** Engineering Leadership if delayed

### Conflict: Observability Overhead
- **With:** All teams
- **Nature:** OpenTelemetry may add latency
- **Resolution:** Use sampling (10% in prod), async exporters
- **Escalation:** Architecture Team

## Recommended Actions

1. **Immediately:** Configure RabbitMQ DLX:
   ```bash
   # Exchange for dead letters
   rabbitmqadmin declare exchange name=bloodbank.events.dlq type=topic durable=true

   # DLQ queue
   rabbitmqadmin declare queue name=dlq.all durable=true
   rabbitmqadmin declare binding source=bloodbank.events.dlq destination=dlq.all routing_key=#
   ```
2. **Immediately:** Update consumer queue declarations with DLX arguments
3. **This sprint:** Deploy Prometheus and configure scrape targets
4. **This sprint:** Create Grafana dashboard for event pipeline health
5. **Next sprint:** Configure OpenTelemetry collector with sampling
6. **Next sprint:** Set up PagerDuty/Slack alerting

## Questions to Resolve

1. DLQ retention policy (24h, 7d, indefinite)?
2. Prometheus scrape interval (15s, 30s, 60s)?
3. Alert escalation policy (P1 to PagerDuty, P2 to Slack)?
4. OpenTelemetry sampling rate in production (1%, 10%, 100%)?

## RabbitMQ DLX Configuration Reference

```python
# Queue declaration with DLX
queue_args = {
    "x-dead-letter-exchange": "bloodbank.events.dlq",
    "x-dead-letter-routing-key": "dlq.candystore",
    "x-message-ttl": 86400000,  # 24 hours
    "x-max-length": 10000,
}

await channel.declare_queue(
    "candystore.events",
    durable=True,
    arguments=queue_args
)
```

## Key Metrics to Monitor

| Metric | SLO | Alert Threshold |
|--------|-----|-----------------|
| Event Publish Success Rate | 99.9% | < 99.5% |
| Event Storage Success Rate | 99.9% | < 99.5% |
| DLQ Size | < 100 | > 1000 |
| End-to-End Latency P99 | < 500ms | > 1000ms |
| Bloodbank Uptime | 99.9% | < 99.5% |
