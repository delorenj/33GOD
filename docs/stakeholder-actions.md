# Stakeholder Action Items

## How to Use This Document

Each stakeholder section contains:
- **Immediate Actions** (Do today/tomorrow)
- **This Sprint Actions** (Complete within 2 weeks)
- **Next Sprint Actions** (Complete within 4 weeks)
- **Dependencies** (What you're waiting on)
- **Deliverables** (What others are waiting on from you)

---

## Engineering Leadership

### Immediate Actions (Day 1)

| Action | Outcome | Blocks |
|--------|---------|--------|
| ✅ Review and approve $120K budget request | Unblocks all remediation work | All teams |
| ✅ Identify 2-3 FTE for dedicated assignment | Senior Backend, Full-Stack, DevOps (half) | All teams |
| ✅ Communicate priority to Product Management | Protect engineers from feature diversion | All teams |

### This Sprint Actions (Week 1-2)

| Action | Outcome |
|--------|---------|
| Announce architectural governance changes to all engineering | Teams understand new schema-first culture |
| Establish weekly progress review in leadership standup | Visibility into remediation progress |
| Define escalation path for cross-team conflicts | Architecture Team has resolution authority |

### Next Sprint Actions (Week 3-4)

| Action | Outcome |
|--------|---------|
| Validate Phase 1 completion (DLQ prevents data loss) | Gate for Phase 2 start |
| Review Phase 2 budget spend | Financial oversight |

### Waiting On

| Dependency | From | Status |
|------------|------|--------|
| Remediation roadmap | Architecture | ✅ COMPLETE |
| Risk assessment | Architecture | ✅ COMPLETE |

### Others Waiting On You

| Deliverable | For | Priority |
|-------------|-----|----------|
| Budget approval | All teams | 🔴 CRITICAL |
| FTE protection | All teams | 🔴 CRITICAL |
| Breaking change authority | Architecture | 🟡 HIGH |

---

## Architecture Team

### Immediate Actions (Day 1-2)

| Action | Outcome | Blocks |
|--------|---------|--------|
| ✅ Review canonical EventEnvelope from CONVERGENCE_REPORT.md 5.1 | Schema baseline approved | Holyfields |
| ✅ Decide on domain naming (fireflies vs voice.transcription) | Consistent event type naming | Holyfields, Bloodbank |

### This Sprint Actions (Week 1-2)

| Action | Outcome |
|--------|---------|
| Create schema change RFC template (use CONVERGENCE_REPORT.md 8.1.1) | Governance process documented |
| Define SLIs/SLOs using CONVERGENCE_REPORT.md 8.4.1 table | DevOps can set alert thresholds |
| Establish code review checklist for event-related PRs | Quality gates in place |

### Next Sprint Actions (Week 3-4)

| Action | Outcome |
|--------|---------|
| Document governance in Architecture Decision Records (ADRs) | Permanent record of decisions |
| Define breaking change deprecation timeline (recommend 90 days) | Migration planning clarity |

### Waiting On

| Dependency | From | Status |
|------------|------|--------|
| Current EventEnvelope implementations | All teams | ✅ AVAILABLE |
| Event type inventory | Bloodbank | ✅ AVAILABLE |

### Others Waiting On You

| Deliverable | For | Priority |
|-------------|-----|----------|
| EventEnvelope approval | Holyfields | 🔴 CRITICAL |
| Domain naming decision | Holyfields, Bloodbank | 🟡 HIGH |
| SLI/SLO definitions | DevOps | 🟠 MEDIUM |

---

## Holyfields Team

### Immediate Actions (Day 1-2)

| Action | Outcome | Blocks |
|--------|---------|--------|
| Wait for Architecture approval of EventEnvelope | Cannot proceed without | Self |
| Prepare schema structure based on CONVERGENCE_REPORT.md 5.1 | Ready when approval comes | None |

### This Sprint Actions (Week 1-2)

| Action | Outcome |
|--------|---------|
| Create canonical `EventEnvelope.schema.json` | Single source of truth for all components |
| Create `event_types.schema.json` for known event types | Type definitions for Fireflies, etc. |
| Set up `scripts/generate-python.py` for dataclasses | Bloodbank/Candystore type generation |
| Set up `scripts/generate-typescript.ts` for interfaces | Candybar type generation |

### Next Sprint Actions (Week 3-4)

| Action | Outcome |
|--------|---------|
| Add schema versioning with `$schema` and `version` fields | Backwards compatibility tracking |
| Create CI job to detect schema drift | Automated type safety enforcement |
| Document generator usage in README | Developer onboarding |

### Waiting On

| Dependency | From | Status |
|------------|------|--------|
| EventEnvelope approval | Architecture | ⏳ PENDING |
| Domain naming decision | Architecture | ⏳ PENDING |

### Others Waiting On You

| Deliverable | For | Priority |
|-------------|-----|----------|
| Canonical EventEnvelope schema | All teams | 🔴 CRITICAL |
| Python type generator | Bloodbank, Candystore | 🟡 HIGH |
| TypeScript type generator | Candybar | 🟡 HIGH |

---

## Bloodbank Team

### Immediate Actions (Day 1-2)

| Action | Outcome | Blocks |
|--------|---------|--------|
| Coordinate with DevOps on DLQ timeline | Know when DLQ is ready | DLQ implementation |
| Review existing EventEnvelope in `events/envelope.py` | Understand migration scope | None |

### This Sprint Actions (Week 1-2)

| Action | Outcome |
|--------|---------|
| Wait for DevOps DLX configuration | Cannot implement DLQ routing without |
| Add `jsonschema` validation in `publish()` method | Reject malformed events at source |
| Implement DLQ routing for failed messages | No silent message drops |
| Add retry with exponential backoff (3 attempts, 1s/2s/4s) | Transient failure recovery |

### Next Sprint Actions (Week 3-4)

| Action | Outcome |
|--------|---------|
| Replace manual types with Holyfields-generated dataclasses | Type drift eliminated |
| Add OpenTelemetry tracing spans | Distributed tracing support |
| Add Prometheus metrics endpoint | DevOps monitoring integration |
| Add health endpoint for Kubernetes probes | Infrastructure integration |

### Waiting On

| Dependency | From | Status |
|------------|------|--------|
| RabbitMQ DLX configuration | DevOps | ⏳ PENDING |
| Canonical EventEnvelope schema | Holyfields | ⏳ PENDING |
| Generated Python types | Holyfields | ⏳ PENDING |

### Others Waiting On You

| Deliverable | For | Priority |
|-------------|-----|----------|
| DLQ integration | Candystore | 🔴 CRITICAL |
| Health endpoints | DevOps | 🟡 HIGH |
| Prometheus metrics | DevOps | 🟠 MEDIUM |

---

## Candystore Team

### Immediate Actions (Day 1-2)

| Action | Outcome | Blocks |
|--------|---------|--------|
| Verify DLQ exists before changing ack behavior | Prevent data loss | Ack behavior change |
| Review current model in `models.py` | Understand field mapping | None |

### This Sprint Actions (Week 1-2)

| Action | Outcome |
|--------|---------|
| Add envelope validation layer using jsonschema | Defense in depth |
| Change to NEVER ack failed messages (route to DLQ) | Zero data loss |
| Export OpenAPI spec at `/openapi.json` (FastAPI automatic) | Candybar type generation |
| Add `GET /events/trace/{correlation_id}` endpoint | Correlation chain queries |

### Next Sprint Actions (Week 3-4)

| Action | Outcome |
|--------|---------|
| Replace manual types with Holyfields-generated models | Type drift eliminated |
| Add OpenTelemetry distributed tracing | End-to-end visibility |
| Add integration tests with RabbitMQ + PostgreSQL containers | Reliable testing |
| Implement WebSocket streaming for real-time push | Live event monitoring |

### Waiting On

| Dependency | From | Status |
|------------|------|--------|
| DLQ configuration | DevOps/Bloodbank | ⏳ PENDING |
| Canonical EventEnvelope schema | Holyfields | ⏳ PENDING |

### Others Waiting On You

| Deliverable | For | Priority |
|-------------|-----|----------|
| OpenAPI specification | Candybar | 🟡 HIGH |
| Correlation query API | All teams | 🟡 HIGH |
| Complete event storage | QA, Audit | 🔴 CRITICAL |

---

## Candybar Team

### Immediate Actions (Day 1-2)

| Action | Outcome | Blocks |
|--------|---------|--------|
| Review current type definitions in `src/types/` | Understand migration scope | None |
| Identify all Candystore API call sites | Know what to update | None |

### This Sprint Actions (Week 1-2)

| Action | Outcome |
|--------|---------|
| Wait for Candystore OpenAPI spec | Cannot generate types without |
| Set up openapi-typescript-codegen in build pipeline | Automated client generation |
| Add Zod schemas matching Holyfields definitions | Runtime validation |

### Next Sprint Actions (Week 3-4)

| Action | Outcome |
|--------|---------|
| Replace manual types with generated interfaces | Type drift eliminated |
| Generate API client from OpenAPI spec | Type-safe API calls |
| Implement correlation chain visualization component | User-facing traceability |
| Enhance event viewer with full envelope display | Complete event visibility |

### Waiting On

| Dependency | From | Status |
|------------|------|--------|
| OpenAPI specification | Candystore | ⏳ PENDING |
| TypeScript type generator | Holyfields | ⏳ PENDING |
| Canonical EventEnvelope schema | Holyfields | ⏳ PENDING |

### Others Waiting On You

| Deliverable | For | Priority |
|-------------|-----|----------|
| Correlation chain UI | End users | 🟠 MEDIUM |
| Event viewer enhancement | End users | 🟠 MEDIUM |

---

## DevOps/Infrastructure Team

### Immediate Actions (Day 1-2)

| Action | Outcome | Blocks |
|--------|---------|--------|
| Configure RabbitMQ Dead Letter Exchange | Enable DLQ routing | Bloodbank, Candystore |

```bash
# Commands to run immediately
rabbitmqadmin declare exchange name=bloodbank.events.dlq type=topic durable=true
rabbitmqadmin declare queue name=dlq.all durable=true
rabbitmqadmin declare binding source=bloodbank.events.dlq destination=dlq.all routing_key=#
```

| Update consumer queue declarations with DLX arguments | Route failures to DLQ | All consumers |

### This Sprint Actions (Week 1-2)

| Action | Outcome |
|--------|---------|
| Deploy Prometheus and configure scrape targets | Metrics collection enabled |
| Create Grafana dashboard for event pipeline health | Operational visibility |
| Create DLQ monitoring dashboard | Failed message visibility |

### Next Sprint Actions (Week 3-4)

| Action | Outcome |
|--------|---------|
| Configure OpenTelemetry collector with sampling | Distributed tracing |
| Set up PagerDuty/Slack alerting | Incident notification |
| Enable TLS for RabbitMQ connections | Security hardening |
| Implement blue-green deployment for migrations | Zero-downtime deploys |

### Waiting On

| Dependency | From | Status |
|------------|------|--------|
| Health endpoints | Bloodbank | ⏳ PENDING |
| Prometheus metrics | Bloodbank, Candystore | ⏳ PENDING |
| Alert thresholds (SLOs) | Architecture | ⏳ PENDING |

### Others Waiting On You

| Deliverable | For | Priority |
|-------------|-----|----------|
| RabbitMQ DLX configuration | Bloodbank, Candystore | 🔴 CRITICAL |
| Prometheus endpoints | All teams | 🟡 HIGH |
| Grafana dashboards | All teams | 🟡 HIGH |

---

## QA Team

### Immediate Actions (Day 1-2)

| Action | Outcome | Blocks |
|--------|---------|--------|
| Create docker-compose for integration test environment | CI test infrastructure | None |
| Review Pact contract testing framework | Understand tooling | None |

### This Sprint Actions (Week 1-2)

| Action | Outcome |
|--------|---------|
| Wait for Candystore OpenAPI spec | Cannot write contract tests without |
| Wait for DLQ configuration | Cannot test DLQ routing without |
| Implement Pact contract tests for Candybar ↔ Candystore | Catch breaking changes |
| Add E2E test: Producer → Bloodbank → Candystore → Query | Full flow validation |

### Next Sprint Actions (Week 3-4)

| Action | Outcome |
|--------|---------|
| Add correlation tracking validation tests | Traceability verification |
| Add DLQ capture verification tests | Data loss prevention verification |
| Performance testing with k6 or locust | Baseline performance metrics |
| Security testing for event signing | Security verification |

### Waiting On

| Dependency | From | Status |
|------------|------|--------|
| OpenAPI specification | Candystore | ⏳ PENDING |
| DLQ configuration | DevOps | ⏳ PENDING |
| Stable EventEnvelope | Holyfields | ⏳ PENDING |

### Others Waiting On You

| Deliverable | For | Priority |
|-------------|-----|----------|
| Contract test suite | All teams | 🟡 HIGH |
| E2E test pipeline | All teams | 🟡 HIGH |
| Test coverage reports | Eng Leadership | 🟠 MEDIUM |

---

## Action Timeline Summary

### Day 1 (Immediate)

| Team | Action |
|------|--------|
| Eng Leadership | Approve budget, identify FTE |
| Architecture | Approve EventEnvelope schema |
| DevOps | Configure RabbitMQ DLX |

### Days 2-3

| Team | Action |
|------|--------|
| Holyfields | Create canonical schema |
| DevOps | Complete DLX configuration |
| QA | Set up docker-compose |

### Days 4-7

| Team | Action |
|------|--------|
| Holyfields | Build type generators |
| Bloodbank | Implement DLQ integration |
| Candystore | Add validation layer |

### Week 2

| Team | Action |
|------|--------|
| Bloodbank | Add validation, adopt generated types |
| Candystore | Change ack behavior, export OpenAPI |
| Candybar | Set up type generation pipeline |
| QA | Implement contract tests |

### Week 3-4

| Team | Action |
|------|--------|
| All | Adopt generated types |
| DevOps | Deploy Prometheus, Grafana |
| QA | E2E tests, correlation tests |

### Week 5-8

| Team | Action |
|------|--------|
| All | OpenTelemetry integration |
| Candystore | Correlation query API |
| Candybar | Correlation chain UI |
| QA | Performance testing |

---

## Blockers to Escalate

If any of these are not resolved by the indicated date, escalate to Engineering Leadership:

| Blocker | Required By | Escalate If Not By |
|---------|-------------|-------------------|
| Budget approval | Day 1 | Day 2 |
| Architecture schema approval | Day 1 | Day 2 |
| DevOps DLX configuration | Day 3 | Day 4 |
| Holyfields canonical schema | Day 5 | Day 7 |
| Candystore OpenAPI spec | Week 2 | Week 2 Day 3 |
