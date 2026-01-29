# Sprint Plan: Hybrid BMAD + Letta Architecture - Phase 1

**Date:** 2026-01-11
**Scrum Master:** Steve (delorenj)
**Project Level:** 3 (Large-scale multi-component integration)
**Total Stories:** 13 stories
**Total Points:** 57 points
**Planned Sprints:** 2 sprints
**Target Completion:** ~4 weeks from sprint start

---

## Executive Summary

This sprint plan covers Phase 1 (Foundation) of the 33GOD Hybrid Multi-Agent Architecture, integrating BMAD workflow orchestration with Letta autonomous agents through Bloodbank's event-driven infrastructure and PostgreSQL event store.

Phase 1 establishes the foundational event persistence pipeline and basic BMAD → Letta handoff coordination, validating the hybrid architecture approach before proceeding to more advanced features in subsequent phases.

**Key Metrics:**
- Total Stories: 13 stories
- Total Points: 57 points
- Sprints: 2 sprints (2 weeks each)
- Team Capacity: 30 points per sprint
- Target Completion: 2026-02-08 (4 weeks)
- Sprint 1 Utilization: 87% (26/30 points)
- Sprint 2 Utilization: 103% (31/30 points)

**Success Criteria (from architecture):**
- ✅ BMAD can delegate task to Letta agent
- ✅ Events persisted to PostgreSQL
- ✅ Query API returns workflow events

---

## Story Inventory

### STORY-000: Development Environment Setup

**Epic:** Infrastructure Foundation
**Priority:** Must Have
**Points:** 3 points (4-8 hours)
**Sprint:** Sprint 1

**User Story:**
As a developer
I want a complete development environment with all dependencies
So that I can develop and test the hybrid architecture locally

**Acceptance Criteria:**
- [ ] Docker Compose file created with PostgreSQL, RabbitMQ, Redis services
- [ ] PostgreSQL database `event_store` created
- [ ] Bloodbank exchange configured
- [ ] Environment variables documented in .env.example
- [ ] `mise dev` starts all services
- [ ] Health check endpoint confirms all services running

**Technical Notes:**
- PostgreSQL 14+
- RabbitMQ with management plugin
- Redis latest
- Network configuration for inter-service communication
- Volume mounts for data persistence

**Dependencies:** None (foundation story)

---

### STORY-001: PostgreSQL Event Store Schema

**Epic:** Database Foundation
**Priority:** Must Have
**Points:** 3 points (4-8 hours)
**Sprint:** Sprint 1

**User Story:**
As a system architect
I want the PostgreSQL event store schema implemented
So that events can be persisted with proper indexing and queryability

**Acceptance Criteria:**
- [ ] `events` table created with all columns per architecture spec
- [ ] `workflow_state` table created
- [ ] `agent_sessions` table created
- [ ] GIN index on correlation_ids for fast causation queries
- [ ] B-tree indexes on event_type, timestamp, checkpoint_id
- [ ] Migration script tested with rollback capability
- [ ] Sample data inserted for testing

**Technical Notes:**
- Use UUID for all IDs
- JSONB for flexible payload storage
- TIMESTAMPTZ for timezone-aware timestamps
- Foreign key constraints on workflow_id
- Partial index on checkpoint_id (WHERE agent_context IS NOT NULL)

**Schema Reference:**
```sql
CREATE TABLE events (
  event_id UUID PRIMARY KEY,
  event_type VARCHAR(255) NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  version VARCHAR(20) NOT NULL,
  source JSONB NOT NULL,
  correlation_ids UUID[] NOT NULL,
  agent_context JSONB,
  payload JSONB NOT NULL,

  INDEX idx_event_type ON events(event_type),
  INDEX idx_timestamp ON events(timestamp DESC),
  INDEX idx_correlation_ids ON events USING GIN(correlation_ids),
  INDEX idx_checkpoint ON events((agent_context->>'checkpoint_id'))
    WHERE agent_context IS NOT NULL
);

CREATE TABLE workflow_state (
  workflow_id UUID PRIMARY KEY,
  project_name VARCHAR(255) NOT NULL,
  current_phase VARCHAR(50) NOT NULL,
  current_agent VARCHAR(100),
  started_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  metadata JSONB,
  correlation_ids UUID[] NOT NULL,

  INDEX idx_project ON workflow_state(project_name),
  INDEX idx_phase ON workflow_state(current_phase),
  INDEX idx_updated ON workflow_state(updated_at DESC)
);

CREATE TABLE agent_sessions (
  session_id UUID PRIMARY KEY,
  agent_type VARCHAR(50) NOT NULL,
  agent_instance_id VARCHAR(255),
  checkpoint_id VARCHAR(255),
  workflow_id UUID REFERENCES workflow_state(workflow_id),
  started_at TIMESTAMPTZ NOT NULL,
  last_active_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  status VARCHAR(50) NOT NULL,
  metadata JSONB,

  INDEX idx_workflow ON agent_sessions(workflow_id),
  INDEX idx_checkpoint ON agent_sessions(checkpoint_id),
  INDEX idx_status ON agent_sessions(status, last_active_at DESC)
);
```

**Dependencies:** STORY-000

---

### STORY-002: Database Migration Tooling

**Epic:** Database Foundation
**Priority:** Must Have
**Points:** 2 points (2-4 hours)
**Sprint:** Sprint 1

**User Story:**
As a developer
I want database migration tooling configured
So that schema changes can be version-controlled and deployed safely

**Acceptance Criteria:**
- [ ] Alembic or similar migration tool configured
- [ ] Initial migration file for event schema created
- [ ] `mise db:migrate` runs migrations
- [ ] `mise db:rollback` rolls back last migration
- [ ] Migration history tracked in database
- [ ] CI/CD integration script created

**Technical Notes:**
- Alembic (Python) or golang-migrate recommended
- Migration files in `migrations/` directory
- Idempotent migration scripts
- Production migration runbook documented

**Dependencies:** STORY-001

---

### STORY-003: Bloodbank Event Type Definitions

**Epic:** Event Infrastructure
**Priority:** Must Have
**Points:** 3 points (4-8 hours)
**Sprint:** Sprint 1

**User Story:**
As a system integrator
I want new event types for BMAD-Letta coordination registered in Bloodbank
So that events can be published and consumed with type safety

**Acceptance Criteria:**
- [ ] Event types added to `/home/delorenj/code/33GOD/bloodbank/trunk-main/event_producers/events/types.py`
- [ ] Payload classes defined for each event type
- [ ] Event type literals: `bmad.workflow.*`, `agent.handoff.*`, `agent.letta.*`
- [ ] EVENT_TYPE_TO_PAYLOAD mapping updated
- [ ] Type hints validated with mypy
- [ ] Documentation strings added

**Technical Notes:**
Event types to add:
- `bmad.workflow.started`
- `bmad.workflow.phase.completed`
- `bmad.workflow.handoff.requested`
- `agent.handoff.accepted`
- `agent.letta.checkpoint.saved`
- `agent.letta.task.completed`
- `agent.letta.task.blocked`

**Event Envelope Structure:**
```python
EventEnvelope:
  event_id: UUID
  event_type: str              # Routing key
  timestamp: datetime
  version: str
  source: Source               # host, type, app
  correlation_ids: List[UUID]  # Parent event IDs for causation tracking
  agent_context: AgentContext  # Agent metadata (type, checkpoint_id, etc.)
  payload: T                   # Typed domain payload
```

**Dependencies:** STORY-000

---

### STORY-004: Event Store Manager - Bloodbank Subscription

**Epic:** Event Store Manager
**Priority:** Must Have
**Points:** 5 points (1-2 days)
**Sprint:** Sprint 1

**User Story:**
As an event store manager
I want to subscribe to all Bloodbank events
So that coordination events are captured for persistence

**Acceptance Criteria:**
- [ ] FastAPI service created in `event-store-manager/` directory
- [ ] Bloodbank consumer class subscribes with `#` wildcard routing key
- [ ] Event envelope deserialization working
- [ ] Connection retry logic with exponential backoff
- [ ] Graceful shutdown handler
- [ ] Logging of all received events
- [ ] Unit tests for consumer logic

**Technical Notes:**
- Use aio-pika for async RabbitMQ
- Subscribe to exchange: `bloodbank.events.v1`
- Queue: `event_store_manager_queue` (durable)
- Acknowledge messages only after persistence
- Handle connection failures gracefully

**Dependencies:** STORY-003

---

### STORY-005: Event Store Manager - PostgreSQL Writer

**Epic:** Event Store Manager
**Priority:** Must Have
**Points:** 5 points (1-2 days)
**Sprint:** Sprint 1

**User Story:**
As an event store manager
I want to persist events to PostgreSQL with transactional guarantees
So that events are never lost and consistency is maintained

**Acceptance Criteria:**
- [ ] PostgreSQL async connection pool configured
- [ ] INSERT query for events table
- [ ] Transactional outbox pattern: DB commit then RabbitMQ ACK
- [ ] Error handling with DLQ for failed events
- [ ] Duplicate event detection (idempotency)
- [ ] Metrics for ingestion rate and latency
- [ ] Integration test with actual PostgreSQL

**Technical Notes:**
- Use asyncpg for async PostgreSQL
- Connection pool size: 10-20
- Batch inserts for performance (optional optimization)
- DLQ: `event_store_manager_dlq`
- Log failed events for debugging
- Implement transactional outbox: only ACK RabbitMQ after successful DB write

**Transactional Outbox Pattern:**
```python
async def persist_event(event: EventEnvelope):
    async with db.transaction():
        await db.execute("INSERT INTO events ...", event)
        # Only after successful commit
        await rabbitmq.ack(event.delivery_tag)
```

**Dependencies:** STORY-001, STORY-004

---

### STORY-006: Event Store Manager - Workflow State Projections

**Epic:** Event Store Manager
**Priority:** Should Have
**Points:** 5 points (1-2 days)
**Sprint:** Sprint 1

**User Story:**
As a workflow coordinator
I want workflow state automatically updated based on events
So that current workflow status is queryable

**Acceptance Criteria:**
- [ ] Event handler for `bmad.workflow.started` creates workflow_state record
- [ ] Event handler for `bmad.workflow.phase.completed` updates current_phase
- [ ] Event handler for `agent.handoff.accepted` updates current_agent
- [ ] Event handler for `bmad.workflow.completed` sets completed_at
- [ ] Correlation IDs accumulated in workflow_state.correlation_ids array
- [ ] Unit tests for projection logic

**Technical Notes:**
- Projections run as part of event persistence transaction
- Use PostgreSQL UPSERT (INSERT ... ON CONFLICT UPDATE)
- Log projection failures but don't block event persistence
- Event handlers should be idempotent

**Projection Example:**
```python
@event_handler("bmad.workflow.started")
async def on_workflow_started(event: EventEnvelope):
    await db.execute("""
        INSERT INTO workflow_state (workflow_id, project_name, current_phase, ...)
        VALUES ($1, $2, $3, ...)
        ON CONFLICT (workflow_id) DO UPDATE SET updated_at = $4
    """, event.payload.workflow_id, ...)
```

**Dependencies:** STORY-005

---

### STORY-007: Event Store API - Basic Event Queries

**Epic:** Event Store API
**Priority:** Must Have
**Points:** 5 points (1-2 days)
**Sprint:** Sprint 2

**User Story:**
As a developer
I want to query events by workflow_id, event_type, and time range
So that I can debug workflows and trace agent interactions

**Acceptance Criteria:**
- [ ] FastAPI service created in `event-store-api/` directory
- [ ] `GET /api/v1/events` endpoint with query parameters
- [ ] Filter by workflow_id (via correlation_ids)
- [ ] Filter by event_type
- [ ] Filter by timestamp range (start_time, end_time)
- [ ] Pagination (limit, offset)
- [ ] OpenAPI docs auto-generated
- [ ] Integration test with sample events

**Technical Notes:**
- Query parameters: `?workflow_id=UUID&event_type=bmad.workflow.started&limit=50&offset=0`
- Return EventEnvelope JSON array
- Use indexes for performance
- Default limit: 100, max limit: 1000

**API Endpoint:**
```
GET /api/v1/events
  ?workflow_id=uuid           # Optional filter
  &event_type=bmad.workflow.* # Optional filter (supports wildcards)
  &start_time=ISO8601         # Optional time range start
  &end_time=ISO8601           # Optional time range end
  &limit=100                  # Pagination (default 100, max 1000)
  &offset=0                   # Pagination offset

Response: EventEnvelope[]
```

**Dependencies:** STORY-001

---

### STORY-008: Event Store API - Causation Chain Queries

**Epic:** Event Store API
**Priority:** Must Have
**Points:** 8 points (2-3 days)
**Sprint:** Sprint 2

**User Story:**
As a system debugger
I want to query all descendant events from a given event
So that I can trace the full causation chain of a workflow

**Acceptance Criteria:**
- [ ] `GET /api/v1/events/{event_id}/descendants` endpoint
- [ ] Recursive query using correlation_ids to find all downstream events
- [ ] Return events in chronological order
- [ ] Include depth level in response
- [ ] Prevent infinite loops (max depth: 100)
- [ ] Graph visualization format option (JSON graph)
- [ ] Integration test with multi-level causation chain

**Technical Notes:**
- Use PostgreSQL recursive CTE (WITH RECURSIVE)
- Query correlation_ids GIN index for performance
- Format: `{"event": EventEnvelope, "depth": int, "children": [...]}`
- Cache frequent queries in Redis (optional optimization)

**Recursive CTE Example:**
```sql
WITH RECURSIVE causation_chain AS (
  -- Base case: starting event
  SELECT event_id, correlation_ids, 0 as depth
  FROM events
  WHERE event_id = $1

  UNION ALL

  -- Recursive case: find children
  SELECT e.event_id, e.correlation_ids, c.depth + 1
  FROM events e
  JOIN causation_chain c ON e.correlation_ids @> ARRAY[c.event_id]
  WHERE c.depth < 100
)
SELECT * FROM causation_chain ORDER BY depth, timestamp;
```

**API Endpoint:**
```
GET /api/v1/events/{event_id}/descendants
  ?format=tree|flat           # Response format (default: tree)
  ?max_depth=100               # Maximum recursion depth

Response (tree format):
{
  "event": EventEnvelope,
  "depth": 0,
  "children": [
    {
      "event": EventEnvelope,
      "depth": 1,
      "children": [...]
    }
  ]
}
```

**Dependencies:** STORY-007

---

### STORY-009: Event Store API - WebSocket Event Stream

**Epic:** Event Store API
**Priority:** Should Have
**Points:** 5 points (1-2 days)
**Sprint:** Sprint 2

**User Story:**
As a dashboard developer
I want a WebSocket endpoint streaming events in real-time
So that Holocene can display live workflow updates

**Acceptance Criteria:**
- [ ] `WS /api/v1/events/stream` endpoint
- [ ] Filter by event_type via query parameter
- [ ] Filter by workflow_id via query parameter
- [ ] Events pushed <500ms after persistence
- [ ] Connection management (auto-reconnect client-side)
- [ ] Heartbeat messages every 30s
- [ ] Integration test with WebSocket client

**Technical Notes:**
- Use FastAPI WebSocket support
- Redis pub/sub for event broadcasting
- Event Store Manager publishes to Redis after DB write
- WebSocket handler subscribes to Redis channel
- Handle disconnections gracefully

**WebSocket Flow:**
```
1. Event Store Manager writes event to PostgreSQL
2. Event Store Manager publishes to Redis: PUBLISH events:stream "{event_json}"
3. WebSocket handler subscribes: SUBSCRIBE events:stream
4. WebSocket pushes event to connected clients matching filters
```

**WebSocket Endpoint:**
```
WS /api/v1/events/stream
  ?event_type=bmad.workflow.*  # Optional filter
  &workflow_id=uuid            # Optional filter

Messages:
- Event: {"type": "event", "data": EventEnvelope}
- Heartbeat: {"type": "heartbeat", "timestamp": ISO8601}
- Error: {"type": "error", "message": "..."}
```

**Dependencies:** STORY-007

---

### STORY-010: BMAD Orchestrator Event Publishing

**Epic:** BMAD Integration
**Priority:** Must Have
**Points:** 3 points (4-8 hours)
**Sprint:** Sprint 2

**User Story:**
As a BMAD agent
I want to publish handoff events to Bloodbank
So that I can delegate work to Letta agents

**Acceptance Criteria:**
- [ ] BMAD helper function `publish_event(event_type, payload)` created
- [ ] Example BMAD skill updated to publish `bmad.workflow.handoff.requested`
- [ ] Event envelope properly formatted with correlation_ids
- [ ] Bloodbank publisher configured in BMAD context
- [ ] Integration test: BMAD skill publishes event, appears in event store
- [ ] Documentation for BMAD skill developers

**Technical Notes:**
- Add to `~/.claude/skills/bmad/helpers/events.md`
- Use environment variables for RabbitMQ connection
- Generate correlation_id if not provided
- Timestamp in UTC

**Helper Function Example:**
```python
# File: ~/.claude/skills/bmad/helpers/events.py
async def publish_event(
    event_type: str,
    payload: dict,
    correlation_ids: List[UUID] = None
) -> UUID:
    """Publish event to Bloodbank for coordination."""
    event_id = uuid4()
    envelope = EventEnvelope(
        event_id=event_id,
        event_type=event_type,
        timestamp=datetime.now(UTC),
        version="1.0.0",
        source=Source(host=platform.node(), type="agent", app="bmad"),
        correlation_ids=correlation_ids or [],
        agent_context=None,
        payload=payload
    )
    await bloodbank_publisher.publish(event_type, envelope)
    return event_id
```

**Usage in BMAD Skill:**
```python
# Publish handoff request from BMAD to Letta
handoff_event_id = await publish_event(
    event_type="bmad.workflow.handoff.requested",
    payload={
        "workflow_id": workflow_id,
        "from_agent": "bmad-architect",
        "to_agent": "letta-python-dev",
        "task": "Implement feature based on analysis",
        "context": {...}
    },
    correlation_ids=[workflow_started_event_id]
)
```

**Dependencies:** STORY-003, STORY-005

---

### STORY-011: Letta Runtime Event Consumption

**Epic:** Letta Integration
**Priority:** Must Have
**Points:** 5 points (1-2 days)
**Sprint:** Sprint 2

**User Story:**
As a Letta agent
I want to consume handoff events from Bloodbank
So that I can accept assigned tasks from BMAD

**Acceptance Criteria:**
- [ ] Letta server Bloodbank consumer configured
- [ ] Event handler for `bmad.workflow.handoff.requested`
- [ ] Letta agent created from handoff payload
- [ ] Agent publishes `agent.handoff.accepted` event
- [ ] Task context loaded into Letta agent memory
- [ ] Integration test: BMAD publishes handoff, Letta accepts and starts work
- [ ] Error handling if Letta unavailable

**Technical Notes:**
- Letta queue: `letta_handoff_queue` (durable)
- Routing key: `bmad.workflow.handoff.#`
- Extract task description and context from payload
- Create Letta agent session via Letta SDK
- Publish acceptance event with session_id
- Load task context into agent memory

**Letta Event Handler:**
```python
@bloodbank_consumer("bmad.workflow.handoff.requested")
async def on_handoff_request(envelope: EventEnvelope):
    payload = envelope.payload

    # Create Letta agent
    agent = await letta_client.create_agent(
        name=payload.to_agent,
        memory={"task": payload.task, "context": payload.context}
    )

    # Publish acceptance event
    await publish_event(
        event_type="agent.handoff.accepted",
        payload={
            "workflow_id": payload.workflow_id,
            "agent_type": "letta",
            "session_id": agent.id,
            "accepted_from": payload.from_agent
        },
        correlation_ids=[envelope.event_id]
    )

    # Start agent execution (async)
    await agent.start()
```

**Dependencies:** STORY-010

---

### STORY-012: End-to-End Handoff Integration Test

**Epic:** Integration Testing
**Priority:** Must Have
**Points:** 5 points (1-2 days)
**Sprint:** Sprint 2

**User Story:**
As a system validator
I want an end-to-end test proving BMAD → Letta handoff works
So that Phase 1 success criteria are met

**Acceptance Criteria:**
- [ ] Test script creates mock BMAD workflow
- [ ] BMAD publishes `bmad.workflow.handoff.requested` event
- [ ] Event persisted to PostgreSQL event store
- [ ] Letta runtime consumes event
- [ ] Letta publishes `agent.handoff.accepted` event
- [ ] Both events queryable via Event Store API
- [ ] Causation chain links the two events via correlation_ids
- [ ] Workflow state updated correctly (current_agent = "letta-python-dev")
- [ ] Test runs in CI/CD pipeline

**Technical Notes:**
- pytest test suite
- Docker Compose test environment
- Fixtures for BMAD and Letta mocks
- Assert on event store contents via API
- Assert on workflow_state table
- Clean up test data after run

**Test Flow:**
```python
async def test_bmad_letta_handoff():
    # 1. Publish handoff request from BMAD
    handoff_event_id = await bmad_client.publish_handoff(
        workflow_id=test_workflow_id,
        to_agent="letta-python-dev",
        task="Test task"
    )

    # 2. Wait for Letta to process (max 5s)
    await asyncio.sleep(2)

    # 3. Query event store for both events
    events = await event_api.get_events(workflow_id=test_workflow_id)
    assert len(events) == 2
    assert events[0].event_type == "bmad.workflow.handoff.requested"
    assert events[1].event_type == "agent.handoff.accepted"

    # 4. Verify causation chain
    descendants = await event_api.get_descendants(handoff_event_id)
    assert len(descendants) == 1
    assert descendants[0].event_id == events[1].event_id

    # 5. Verify workflow state
    workflow = await event_api.get_workflow(test_workflow_id)
    assert workflow.current_agent == "letta-python-dev"
```

**Dependencies:** STORY-010, STORY-011

---

## Sprint Allocation

### Sprint 1 (Weeks 1-2) - 26/30 points (87% utilization)

**Goal:** Establish event store infrastructure and event persistence pipeline

**Start Date:** 2026-01-11
**End Date:** 2026-01-25

**Stories:**
| Story | Title | Points | Priority |
|-------|-------|--------|----------|
| STORY-000 | Development Environment Setup | 3 | Must Have |
| STORY-001 | PostgreSQL Event Store Schema | 3 | Must Have |
| STORY-002 | Database Migration Tooling | 2 | Must Have |
| STORY-003 | Bloodbank Event Type Definitions | 3 | Must Have |
| STORY-004 | Event Store Manager - Bloodbank Subscription | 5 | Must Have |
| STORY-005 | Event Store Manager - PostgreSQL Writer | 5 | Must Have |
| STORY-006 | Event Store Manager - Workflow State Projections | 5 | Should Have |

**Total:** 26 points

**Sprint 1 Deliverable:**
Events from Bloodbank persisted to PostgreSQL with workflow state tracking. Event Store Manager service running and ingesting all Bloodbank events.

**Sprint 1 Risks:**
- **High:** PostgreSQL configuration complexity in Docker Compose
- **Medium:** Async pattern learning curve for aio-pika and asyncpg
- **Medium:** Transactional outbox pattern implementation
- **Low:** Migration tooling setup

**Mitigation:**
- Start with STORY-000 to establish solid foundation
- Use architecture document SQL schema as reference
- Test async patterns in isolation before integration

---

### Sprint 2 (Weeks 3-4) - 31/30 points (103% utilization)

**Goal:** Complete event query API and end-to-end BMAD → Letta handoff

**Start Date:** 2026-01-26
**End Date:** 2026-02-08

**Stories:**
| Story | Title | Points | Priority |
|-------|-------|--------|----------|
| STORY-007 | Event Store API - Basic Event Queries | 5 | Must Have |
| STORY-008 | Event Store API - Causation Chain Queries | 8 | Must Have |
| STORY-009 | Event Store API - WebSocket Event Stream | 5 | Should Have |
| STORY-010 | BMAD Orchestrator Event Publishing | 3 | Must Have |
| STORY-011 | Letta Runtime Event Consumption | 5 | Must Have |
| STORY-012 | End-to-End Handoff Integration Test | 5 | Must Have |

**Total:** 31 points (slightly over capacity, acceptable for final sprint)

**Sprint 2 Deliverable:**
Complete BMAD → Letta handoff working with queryable event history via REST and WebSocket APIs. All Phase 1 success criteria met.

**Sprint 2 Risks:**
- **High:** Recursive CTE query complexity in STORY-008
- **High:** Letta integration unknowns in STORY-011
- **Medium:** WebSocket connection stability in STORY-009
- **Medium:** End-to-end test environment setup in STORY-012

**Mitigation:**
- Prototype recursive CTE query early in sprint
- Review Letta SDK documentation before starting STORY-011
- Use existing WebSocket patterns from 33GOD ecosystem
- Containerize test environment for reproducibility

---

## Epic Traceability

| Epic ID | Epic Name | Stories | Total Points | Sprint |
|---------|-----------|---------|--------------|--------|
| Infrastructure Foundation | Development environment and tooling | STORY-000 | 3 | Sprint 1 |
| Database Foundation | PostgreSQL schema and migrations | STORY-001, STORY-002 | 5 | Sprint 1 |
| Event Infrastructure | Bloodbank event type definitions | STORY-003 | 3 | Sprint 1 |
| Event Store Manager | Event persistence and projections | STORY-004, STORY-005, STORY-006 | 15 | Sprint 1 |
| Event Store API | Query APIs and real-time streaming | STORY-007, STORY-008, STORY-009 | 18 | Sprint 2 |
| BMAD Integration | BMAD event publishing | STORY-010 | 3 | Sprint 2 |
| Letta Integration | Letta event consumption | STORY-011 | 5 | Sprint 2 |
| Integration Testing | End-to-end validation | STORY-012 | 5 | Sprint 2 |

---

## Functional Requirements Coverage

Based on architecture document NFRs and deliverables:

| Requirement | Description | Stories | Sprint |
|-------------|-------------|---------|--------|
| Event Persistence | All Bloodbank events persisted to PostgreSQL | STORY-001, STORY-004, STORY-005 | 1 |
| Event Queryability | Events queryable by various filters | STORY-007, STORY-008 | 2 |
| Causation Tracking | Correlation IDs enable causation queries | STORY-008 | 2 |
| Real-time Monitoring | WebSocket event streaming | STORY-009 | 2 |
| Workflow State | Automatic workflow state projections | STORY-006 | 1 |
| BMAD → Letta Handoff | BMAD delegates to Letta agents | STORY-010, STORY-011 | 2 |
| Event Type Safety | Type-safe event definitions | STORY-003 | 1 |
| Database Migrations | Version-controlled schema changes | STORY-002 | 1 |
| Integration Validation | End-to-end handoff testing | STORY-012 | 2 |

---

## Risks and Mitigation

### Technical Risks

**High Priority:**

1. **Recursive CTE Complexity (STORY-008)**
   - **Risk:** PostgreSQL recursive query may be difficult to implement correctly
   - **Impact:** Delays in causation chain feature
   - **Mitigation:** Prototype query early in Sprint 2, consult PostgreSQL documentation, start with simple implementation

2. **Letta Integration Unknowns (STORY-011)**
   - **Risk:** Letta SDK integration may have unexpected challenges
   - **Impact:** End-to-end handoff may not work as designed
   - **Mitigation:** Review Letta SDK docs before implementation, create minimal prototype first

3. **Transactional Outbox Pattern (STORY-005)**
   - **Risk:** Implementing transactional outbox correctly is critical for data consistency
   - **Impact:** Lost events or duplicate processing
   - **Mitigation:** Research pattern thoroughly, write comprehensive tests, consider using library

**Medium Priority:**

4. **Async Pattern Learning Curve (STORY-004, STORY-005)**
   - **Risk:** asyncio, aio-pika, asyncpg may require significant learning
   - **Impact:** Development slower than estimated
   - **Mitigation:** Start with simple examples, isolate async patterns for testing

5. **Docker Compose Complexity (STORY-000)**
   - **Risk:** Service orchestration and networking may be tricky
   - **Impact:** Development environment not stable
   - **Mitigation:** Use proven Docker Compose patterns from other 33GOD services

6. **WebSocket Stability (STORY-009)**
   - **Risk:** WebSocket connections may drop or not reconnect properly
   - **Impact:** Dashboard may miss events
   - **Mitigation:** Implement heartbeat and reconnection logic, test with connection disruptions

**Low Priority:**

7. **Migration Tooling Setup (STORY-002)**
   - **Risk:** Alembic configuration may take longer than expected
   - **Impact:** Minor delay in Sprint 1
   - **Mitigation:** 2-point story has buffer, can extend if needed

---

### Resource Risks

**1. Solo Developer Capacity**
- **Risk:** Single developer (Steve) means no parallelization
- **Impact:** Any blocker completely stops progress
- **Mitigation:** Prioritize unblocking issues immediately, seek help on Discord/forums if stuck

**2. Context Switching**
- **Risk:** Switching between different technologies (PostgreSQL, RabbitMQ, FastAPI, Letta)
- **Impact:** Slower ramp-up time for each technology
- **Mitigation:** Complete related stories together, batch learning for each tech stack

---

### Scope Risks

**1. Scope Creep**
- **Risk:** Temptation to add features beyond Phase 1 scope
- **Impact:** Delays Phase 1 completion
- **Mitigation:** Stick to acceptance criteria strictly, defer enhancements to Phase 2-5

**2. Over-Engineering**
- **Risk:** Building more infrastructure than needed for Phase 1
- **Impact:** Wasted effort, delayed delivery
- **Mitigation:** Implement minimum viable version first, optimize in later phases

---

## Dependencies

### External Dependencies

1. **Bloodbank Event Bus**
   - **Status:** Active in 33GOD ecosystem
   - **Impact:** Foundation for all event-driven coordination
   - **Owner:** Steve (delorenj)

2. **Letta Framework**
   - **Status:** External open-source project
   - **Impact:** Required for autonomous agent execution
   - **Risk:** API changes or bugs in Letta SDK
   - **Mitigation:** Pin Letta version, monitor releases

3. **PostgreSQL 14+**
   - **Status:** Standard database
   - **Impact:** Event store persistence
   - **Risk:** Minimal (mature technology)

4. **RabbitMQ**
   - **Status:** Deployed in 33GOD ecosystem
   - **Impact:** Event bus infrastructure
   - **Risk:** Minimal (existing deployment)

---

### Internal Dependencies

1. **33GOD Service Registry**
   - **Location:** `/home/delorenj/code/33GOD/services/registry.yaml`
   - **Impact:** Event Store Manager must be registered as subscriber
   - **Action:** Add entry in Sprint 1

2. **Bloodbank Event Types**
   - **Location:** `/home/delorenj/code/33GOD/bloodbank/trunk-main/event_producers/events/types.py`
   - **Impact:** New event types must be added before consumption
   - **Action:** STORY-003 in Sprint 1

3. **Architecture Document**
   - **Location:** `/home/delorenj/code/33GOD/zellij-driver/docs/architecture-hybrid-bmad-letta-2026-01-11.md`
   - **Impact:** Source of truth for event schemas and component design
   - **Action:** Reference throughout implementation

---

## Definition of Done

For a story to be considered complete:

- [ ] Code implemented and committed to repository
- [ ] Unit tests written and passing (≥80% coverage for business logic)
- [ ] Integration tests passing (for API and service stories)
- [ ] Code follows 33GOD style guidelines (Python: PEP 8, Black formatted)
- [ ] Type hints added (Python: mypy validated)
- [ ] Documentation updated (README, API docs, inline comments)
- [ ] Docker Compose service running (if applicable)
- [ ] `mise <task>` commands working (if applicable)
- [ ] Manual testing performed
- [ ] Acceptance criteria validated ✅
- [ ] No critical bugs or blockers

---

## Next Steps

**Immediate:** Begin Sprint 1

**Sprint 1 Kickoff:**
1. Run `mise dev` to start development environment (after STORY-000)
2. Implement stories in dependency order
3. Daily check-in: Review progress, identify blockers
4. End of Sprint 1: Demo event persistence pipeline

**Sprint 2 Kickoff:**
1. Review Sprint 1 deliverables
2. Validate Event Store Manager is stable
3. Begin Event Store API implementation
4. End of Sprint 2: Demo full BMAD → Letta handoff

**Phase 1 Completion:**
- Run STORY-012 end-to-end integration test
- Validate all success criteria met
- Document lessons learned
- Plan Phase 2 (Checkpoints & Recovery)

---

## Implementation Commands

**Start Development:**
```bash
# After STORY-000 completion
cd /home/delorenj/code/33GOD/zellij-driver
mise dev  # Starts all Docker Compose services
```

**Database Operations:**
```bash
# After STORY-002 completion
mise db:migrate   # Run database migrations
mise db:rollback  # Rollback last migration
mise db:reset     # Reset database to clean state
```

**Service Management:**
```bash
# Event Store Manager
mise event-store:start
mise event-store:logs
mise event-store:stop

# Event Store API
mise event-api:start
mise event-api:logs
mise event-api:stop
```

**Testing:**
```bash
# Run all tests
mise test

# Run specific test suite
mise test:unit
mise test:integration
mise test:e2e
```

---

## Sprint Cadence

**Sprint Length:** 2 weeks

**Sprint Ceremonies:**

**Sprint Planning** (Monday, Week 1)
- Review sprint goal and stories
- Confirm story acceptance criteria
- Identify potential risks
- Set up development environment (Sprint 1 only)

**Daily Stand-up** (Optional for solo developer)
- What did I complete yesterday?
- What am I working on today?
- Any blockers?

**Mid-Sprint Check-in** (Friday, Week 1)
- Review progress (points completed vs capacity)
- Adjust if behind schedule
- Identify any blockers

**Sprint Review** (Friday, Week 2)
- Demo completed stories
- Validate acceptance criteria met
- Review what worked well

**Sprint Retrospective** (Friday, Week 2)
- What went well?
- What could be improved?
- Action items for next sprint

---

## Success Metrics

**Phase 1 Success Criteria (from architecture):**
- ✅ BMAD can delegate task to Letta agent
- ✅ Events persisted to PostgreSQL
- ✅ Query API returns workflow events

**Completion Criteria:**
- All 13 stories marked complete
- All acceptance criteria validated
- End-to-end integration test passing
- Event Store Manager running and ingesting events
- Event Store API serving queries
- Documentation complete

**Quality Metrics:**
- Unit test coverage ≥80%
- All integration tests passing
- No critical or high-severity bugs
- Code reviewed and approved
- Performance: Event ingestion <100ms p95
- Performance: Query API <200ms p95

---

**This sprint plan was created using BMAD Method v6 - Phase 4 (Implementation Planning)**

**Architecture Reference:** `/home/delorenj/code/33GOD/zellij-driver/docs/architecture-hybrid-bmad-letta-2026-01-11.md`

**Sprint Status:** `.bmad/sprint-status.yaml`
