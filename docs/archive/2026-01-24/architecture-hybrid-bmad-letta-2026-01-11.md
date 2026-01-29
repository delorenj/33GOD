# 33GOD Hybrid Multi-Agent Architecture

## BMAD + Letta Integration with Event-Driven Coordination

**Project:** 33GOD Agentic Pipeline Ecosystem
**Date:** 2026-01-11
**Architect:** System Architect (BMAD)
**Status:** Design Complete
**Version:** 1.0.0

---

## Executive Summary

This architecture defines a hybrid multi-agent system combining BMAD workflow orchestration (Claude-based skills for planning/coordination) with Letta autonomous agents (persistent context for long-running implementation tasks), coordinated through Bloodbank's event-driven backbone with PostgreSQL event store for shared state management.

**Key Design Principles:**

- **Control & Agency**: All coordination visible through event audit trail
- **Layered Abstraction**: Clear separation between orchestration and execution
- **Event-Driven Coordination**: Asynchronous, loosely coupled agent collaboration
- **Persistent State**: Letta checkpoints enable session resumability
- **Observable**: Full traceability through event correlation

---

## Architectural Drivers

### AD-001: Multi-Agent Coordination

**Requirement:** Support coordination between Claude-based BMAD workflows and Letta autonomous agents with different capabilities and lifecycles.

**Architectural Impact:**

- Event-driven architecture for asynchronous handoffs
- Shared event store for coordination state
- Correlation ID tracking for causation tracing

### AD-002: Persistent Agent Context

**Requirement:** Letta agents must maintain persistent memory across sessions for long-running tasks.

**Architectural Impact:**

- Checkpoint-based state management
- Event store integration for recovery
- Session lifecycle tracking through events

### AD-003: Observability & Control

**Requirement:** All agent interactions must be traceable, auditable, and debuggable.

**Architectural Impact:**

- Event sourcing pattern for complete audit trail
- Correlation IDs link related events
- PostgreSQL event store enables replay and analysis

### AD-004: Cross-Service Task Orchestration

**Requirement:** Support mise-architect and Director of Engineering coordinating tasks across multiple 33GOD services.

**Architectural Impact:**

- Hierarchical agent relationships
- Collaboration event patterns
- Cross-service state synchronization

### AD-005: Scalability & Extensibility

**Requirement:** Architecture must support adding new agent types (Agno, custom agents) without redesign.

**Architectural Impact:**

- Common event schema for all agent types
- Pluggable agent registration
- Generic handoff patterns

---

## High-Level Architecture

### Pattern: Hybrid Event-Driven Multi-Agent System

**Core Pattern:** BMAD provides workflow orchestration and planning expertise (stateless Claude skills), while Letta provides persistent execution capabilities. Bloodbank event bus coordinates asynchronous collaboration with PostgreSQL event store maintaining shared state.

```
┌─────────────────────────────────────────────────────────────────┐
│                    33GOD Multi-Agent Ecosystem                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │  BMAD Layer      │         │  Letta Layer     │             │
│  │  (Orchestration) │         │  (Execution)     │             │
│  ├──────────────────┤         ├──────────────────┤             │
│  │ • Product Mgr    │         │ • Python Dev     │             │
│  │ • Architect      │         │ • Rust Dev       │             │
│  │ • UX Designer    │         │ • Frontend Dev   │             │
│  │ • Scrum Master   │         │ • QA Engineer    │             │
│  │ • mise-architect │         │ • Custom Agents  │             │
│  └────────┬─────────┘         └─────────┬────────┘             │
│           │                             │                       │
│           └──────────┬──────────────────┘                       │
│                      │                                          │
│           ┌──────────▼──────────────────┐                       │
│           │   Bloodbank Event Bus       │                       │
│           │   (RabbitMQ Topic Exchange) │                       │
│           └──────────┬──────────────────┘                       │
│                      │                                          │
│           ┌──────────▼──────────────────┐                       │
│           │   Event Store (PostgreSQL)  │                       │
│           │   • Event history           │                       │
│           │   • Workflow state          │                       │
│           │   • Checkpoint references   │                       │
│           │   • Correlation tracking    │                       │
│           └─────────────────────────────┘                       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Interaction Flow

1. **BMAD Planning Phase**: Claude skills (Product Manager, Architect) define requirements and architecture
2. **Handoff to Letta**: BMAD emits `bmad.workflow.handoff.requested` event with task context
3. **Letta Execution**: Letta agent accepts task, maintains persistent context via checkpoints
4. **Progress Events**: Letta publishes `agent.letta.checkpoint.saved` as work progresses
5. **Completion Handoff**: Letta emits `agent.letta.task.completed`, BMAD QA Engineer validates
6. **Event Store**: All interactions persisted with correlation IDs for full traceability

---

## Technology Stack

### Orchestration Layer (BMAD)

**Technology:** Claude Code Skills (Prompt Engineering)

**Rationale:**

- Leverages Claude's strong planning and architectural reasoning
- Stateless design simplifies deployment
- Skills are version-controlled markdown documents
- No runtime infrastructure for BMAD agents themselves

**Trade-offs:**

- ✓ Gain: Simple deployment, no state management needed
- ✓ Gain: Excellent at high-level reasoning and coordination
- ✗ Lose: Cannot maintain context across sessions
- ✗ Lose: Limited to single-turn or short multi-turn interactions

**Responsibilities:**

- Requirements analysis (Product Manager, Business Analyst)
- Architecture design (System Architect)
- Task planning and breakdown (Scrum Master)
- Quality validation (Code Reviewer)
- Cross-service orchestration (mise-architect, Director of Engineering)

### Execution Layer (Letta)

**Technology:** Letta Framework (Python-based autonomous agents)

**Rationale:**

- Persistent memory via checkpoint system
- Supports long-running tasks across multiple sessions
- Built-in tool integration (MCP servers, custom functions)
- Multi-agent collaboration capabilities
- Python ecosystem integration (FastAPI, Pydantic, etc.)

**Trade-offs:**

- ✓ Gain: Persistent context enables complex multi-session workflows
- ✓ Gain: Tool calling for code execution, file manipulation
- ✓ Gain: Checkpoint recovery for reliability
- ✗ Lose: Requires runtime infrastructure (Letta server)
- ✗ Lose: More complex deployment and state management

**Responsibilities:**

- Code implementation (Python Dev, Rust Dev, Frontend Dev)
- Long-running refactoring tasks
- Multi-file changes requiring sustained context
- Test generation and execution
- Iterative development based on feedback

### Event Bus (Bloodbank)

**Technology:** RabbitMQ with Topic Exchange

**Rationale:**

- Already deployed in 33GOD ecosystem
- Topic-based routing supports flexible event patterns
- Reliable message delivery with acknowledgments
- Supports pub/sub for multi-consumer scenarios
- Battle-tested for event-driven architectures

**Current Event Schema:**

```python
EventEnvelope:
  event_id: UUID
  event_type: str              # Routing key (e.g., "bmad.workflow.handoff.requested")
  timestamp: datetime
  version: str
  source: Source               # host, type (manual/agent/scheduled), app
  correlation_ids: List[UUID]  # Parent event IDs for causation tracking
  agent_context: AgentContext  # Agent metadata (type, checkpoint_id, etc.)
  payload: T                   # Typed domain payload
```

### Event Store (PostgreSQL)

**Technology:** PostgreSQL 14+ with JSONB

**Rationale:**

- Already in tech stack (DeLorenzo preference)
- JSONB enables flexible payload storage with indexing
- GIN indexes on correlation_ids for fast causation queries
- ACID guarantees for event consistency
- Supports complex queries for workflow analysis

**Trade-offs:**

- ✓ Gain: Rich query capabilities for event analysis
- ✓ Gain: ACID guarantees ensure data integrity
- ✓ Gain: Familiar technology reduces operational overhead
- ✗ Lose: Not purpose-built event store (vs EventStoreDB)
- ✗ Lose: Requires manual event replay implementation

**Schema Design:**

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

  -- Indexes for common queries
  INDEX idx_event_type ON events(event_type),
  INDEX idx_timestamp ON events(timestamp DESC),
  INDEX idx_correlation_ids ON events USING GIN(correlation_ids),
  INDEX idx_checkpoint ON events((agent_context->>'checkpoint_id'))
    WHERE agent_context IS NOT NULL
);

CREATE TABLE workflow_state (
  workflow_id UUID PRIMARY KEY,
  project_name VARCHAR(255) NOT NULL,
  current_phase VARCHAR(50) NOT NULL,  -- analysis, planning, solutioning, implementation
  current_agent VARCHAR(100),
  started_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  metadata JSONB,
  correlation_ids UUID[] NOT NULL,  -- Links to events for this workflow

  INDEX idx_project ON workflow_state(project_name),
  INDEX idx_phase ON workflow_state(current_phase),
  INDEX idx_updated ON workflow_state(updated_at DESC)
);

CREATE TABLE agent_sessions (
  session_id UUID PRIMARY KEY,
  agent_type VARCHAR(50) NOT NULL,  -- bmad-analyst, letta-python-dev, etc.
  agent_instance_id VARCHAR(255),
  checkpoint_id VARCHAR(255),       -- Letta checkpoint reference
  workflow_id UUID REFERENCES workflow_state(workflow_id),
  started_at TIMESTAMPTZ NOT NULL,
  last_active_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  status VARCHAR(50) NOT NULL,      -- active, paused, completed, failed
  metadata JSONB,

  INDEX idx_workflow ON agent_sessions(workflow_id),
  INDEX idx_checkpoint ON agent_sessions(checkpoint_id),
  INDEX idx_status ON agent_sessions(status, last_active_at DESC)
);
```

### Supporting Infrastructure

**Redis:**

- Session state caching for active workflows
- Real-time agent status tracking
- Pub/sub for live dashboard updates

**Docker Compose:**

- Containerized deployment for all services
- Letta server, Bloodbank consumers, event store
- Development environment parity

**FastAPI:**

- REST APIs for workflow management
- Agent status queries
- Event history browsing
- Holocene dashboard backend

---

## System Components

### Component 1: BMAD Orchestrator

**Purpose:** Workflow coordination and high-level planning using Claude-based skills

**Responsibilities:**

- Execute BMAD workflows (analysis, planning, solutioning phases)
- Coordinate agent handoffs via Bloodbank events
- Validate deliverables from Letta agents
- Maintain workflow state in event store

**Interfaces:**

- Claude Code CLI (user interaction)
- Bloodbank event publishing (coordination)
- Event store queries (workflow state)

**Dependencies:**

- Bloodbank event bus
- PostgreSQL event store
- BMAD skill definitions

**Event Types Produced:**

```python
bmad.workflow.started              # Workflow initiated
bmad.workflow.phase.completed      # Analysis/Planning/Solutioning phase done
bmad.workflow.handoff.requested    # Delegating task to Letta
bmad.workflow.validation.requested # QA review needed
bmad.workflow.completed            # Full workflow done
```

**Event Types Consumed:**

```python
agent.letta.task.completed         # Letta finished assigned work
agent.letta.task.blocked           # Letta needs help
agent.feedback.requested           # Agent needs human input
```

### Component 2: Letta Agent Runtime

**Purpose:** Execute long-running implementation tasks with persistent context

**Responsibilities:**

- Accept task assignments from BMAD orchestrator
- Maintain persistent memory via checkpoints
- Execute code changes, file modifications
- Publish progress events
- Handle iterative feedback loops

**Interfaces:**

- Letta Server API (HTTP/WebSocket)
- Bloodbank event publishing/consuming
- MCP servers for tool integration
- File system access for code changes

**Dependencies:**

- Letta framework and runtime
- Bloodbank event bus
- PostgreSQL event store (checkpoint references)
- Git repositories (iMi worktree integration)

**Event Types Produced:**

```python
agent.handoff.accepted             # Letta accepted task
agent.letta.checkpoint.saved       # Progress checkpoint created
agent.letta.context.updated        # Memory/context changed
agent.letta.task.completed         # Work finished
agent.letta.task.blocked           # Needs assistance
agent.feedback.requested           # Needs human input
```

**Event Types Consumed:**

```python
bmad.workflow.handoff.requested    # New task assignment
agent.handoff.requested            # Peer agent requests help
agent.feedback.response            # Human provided input
agent.collaboration.started        # Join multi-agent task
```

### Component 3: Candystore

**Purpose:** Persist all coordination events with queryable history

**Responsibilities:**

- Subscribe to all Bloodbank events
- Persist events to PostgreSQL with indexes
- Maintain workflow state projections
- Provide event history API
- Support causation queries via correlation IDs

**Interfaces:**

- Bloodbank subscriber (all event types with `#` wildcard)
- PostgreSQL writer
- REST API for event queries
- WebSocket for real-time event streams

**Dependencies:**

- Bloodbank event bus
- PostgreSQL database
- Redis (query caching)

**API Endpoints:**

```
GET  /api/v1/events?workflow_id={id}           # Get all events for workflow
GET  /api/v1/events?correlation_id={id}        # Get causation chain
GET  /api/v1/events/{event_id}/descendants     # Get all downstream events
GET  /api/v1/workflows/{workflow_id}/timeline  # Workflow event timeline
GET  /api/v1/agents/{session_id}/events        # Agent-specific events
POST /api/v1/events/replay                     # Replay event sequence
WS   /api/v1/events/stream                     # Real-time event stream
```

### Component 4: Director of Engineering

**Purpose:** Cross-service orchestration and mise task standardization

**Responsibilities:**

- Coordinate mise-architect across multiple 33GOD services
- Manage top-level mise.toml orchestration patterns
- Delegate service-specific mise work to Letta agents
- Ensure common task interface patterns
- Track cross-service dependencies

**Interfaces:**

- BMAD workflow integration
- Bloodbank event publishing/consuming
- iMi worktree management for multi-repo coordination

**Dependencies:**

- BMAD orchestrator
- mise-architect (BMAD skill)
- Letta agents (service-specific implementation)
- Git repositories across services

**Event Types Produced:**

```python
director.cross-service.task.created      # Multi-service task defined
director.mise.standardization.requested  # Align mise patterns
director.service.delegation.requested    # Delegate to service agent
```

**Event Types Consumed:**

```python
agent.letta.task.completed               # Service agent finished
bmad.workflow.handoff.requested          # BMAD delegates cross-service work
```

### Component 5: Collaboration Coordinator

**Purpose:** Manage multi-agent collaborations (multiple agents working on shared goal)

**Responsibilities:**

- Track active collaborations
- Coordinate agent interactions
- Manage shared context across participants
- Resolve conflicts and deadlocks
- Aggregate results from participants

**Interfaces:**

- Bloodbank event publishing/consuming
- Redis (collaboration state)
- Event store (collaboration history)

**Dependencies:**

- Bloodbank event bus
- Event store
- Redis

**Event Types Produced:**

```python
agent.collaboration.started             # New collaboration initiated
agent.collaboration.participant.joined  # Agent joined collaboration
agent.collaboration.update              # Progress update
agent.collaboration.completed           # Collaboration finished
agent.collaboration.failed              # Collaboration aborted
```

**Event Types Consumed:**

```python
agent.letta.context.updated             # Participant updated state
agent.handoff.requested                 # Participant needs help
agent.letta.task.completed              # Participant finished subtask
```

---

## Data Architecture

### Event Stream Data Model

**Event Envelope** (all events):

```python
{
  "event_id": "uuid-v4",
  "event_type": "bmad.workflow.handoff.requested",
  "timestamp": "2026-01-11T14:30:00Z",
  "version": "1.0.0",
  "source": {
    "host": "hostname",
    "type": "agent",
    "app": "bmad-orchestrator",
    "meta": {}
  },
  "correlation_ids": ["parent-event-uuid"],
  "agent_context": {
    "type": "bmad-architect",
    "name": "System Architect",
    "instance_id": "session-123",
    "checkpoint_id": null  # BMAD agents don't checkpoint
  },
  "payload": {
    # Event-specific data (see payload schemas below)
  }
}
```

### Payload Schemas (Key Event Types)

**bmad.workflow.handoff.requested:**

```python
{
  "workflow_id": "uuid",
  "from_agent": "bmad-architect",
  "to_agent": "letta-python-dev",
  "task_type": "implement_feature",
  "task_description": "Implement user authentication feature",
  "context": {
    "requirements": {...},       # PRD/tech-spec excerpts
    "architecture": {...},       # Architecture decisions
    "file_references": [...],    # Files to modify
    "constraints": {...}
  },
  "deadline": "2026-01-15T00:00:00Z",  # Optional
  "priority": "high"
}
```

**agent.letta.checkpoint.saved:**

```python
{
  "session_id": "uuid",
  "checkpoint_id": "letta-checkpoint-xyz",
  "agent_instance_id": "letta-python-dev-001",
  "checkpoint_type": "progress",  # progress, milestone, pre-handoff
  "summary": "Completed auth module implementation",
  "context_snapshot": {
    "files_modified": [...],
    "current_focus": "Writing unit tests",
    "next_steps": "Integration tests"
  },
  "metrics": {
    "tokens_used": 45000,
    "duration_seconds": 1200
  }
}
```

**agent.letta.task.completed:**

```python
{
  "session_id": "uuid",
  "workflow_id": "uuid",
  "task_id": "uuid",
  "agent_instance_id": "letta-python-dev-001",
  "final_checkpoint_id": "letta-checkpoint-final",
  "artifacts": [
    {"type": "code", "path": "src/auth/module.py", "status": "modified"},
    {"type": "test", "path": "tests/test_auth.py", "status": "created"},
    {"type": "docs", "path": "docs/auth.md", "status": "created"}
  ],
  "validation": {
    "tests_passed": true,
    "lint_passed": true,
    "coverage_pct": 87.5
  },
  "next_action": "qa_review",  # Suggestion for next step
  "summary": "User authentication feature implemented with tests"
}
```

**agent.collaboration.started:**

```python
{
  "collaboration_id": "uuid",
  "initiator_agent": "director-of-engineering",
  "goal": "Standardize mise tasks across all services",
  "participants": [
    {
      "agent_id": "mise-architect",
      "role": "orchestrator",
      "responsibilities": ["Define patterns", "Review implementations"]
    },
    {
      "agent_id": "letta-python-dev",
      "role": "service-implementer",
      "responsibilities": ["Implement mise.toml for service-a"]
    },
    {
      "agent_id": "letta-rust-dev",
      "role": "service-implementer",
      "responsibilities": ["Implement mise.toml for service-b"]
    }
  ],
  "shared_context": {
    "target_services": ["service-a", "service-b", "service-c"],
    "standard_tasks": ["build", "test", "deploy", "lint"]
  },
  "coordination_strategy": "hierarchical"  # mise-architect leads
}
```

### Workflow State Projection

Event store manager maintains materialized view of workflow state:

```python
{
  "workflow_id": "uuid",
  "project_name": "user-authentication",
  "current_phase": "implementation",
  "current_agent": "letta-python-dev-001",
  "started_at": "2026-01-10T09:00:00Z",
  "updated_at": "2026-01-11T14:30:00Z",
  "completed_at": null,
  "phase_history": [
    {"phase": "analysis", "completed_at": "2026-01-10T10:00:00Z"},
    {"phase": "planning", "completed_at": "2026-01-10T12:00:00Z"},
    {"phase": "solutioning", "completed_at": "2026-01-10T15:00:00Z"},
    {"phase": "implementation", "started_at": "2026-01-11T09:00:00Z"}
  ],
  "agent_handoffs": [
    {"from": "bmad-analyst", "to": "bmad-pm", "at": "2026-01-10T10:00:00Z"},
    {"from": "bmad-architect", "to": "letta-python-dev", "at": "2026-01-11T09:00:00Z"}
  ],
  "correlation_ids": ["event-1-uuid", "event-2-uuid", ...],
  "metadata": {
    "total_agents_involved": 4,
    "bmad_agents": 3,
    "letta_agents": 1
  }
}
```

---

## API Design

### Event Store API

**Base URL:** `https://api.33god.io/v1/events`

**Authentication:** JWT tokens (service-to-service) or API keys

#### Event Queries

```
GET /api/v1/events
Query Parameters:
  - workflow_id: UUID (filter by workflow)
  - event_type: string (filter by type, supports wildcards: agent.letta.*)
  - correlation_id: UUID (get causation chain)
  - agent_id: string (filter by agent)
  - since: ISO8601 timestamp
  - limit: int (default 100, max 1000)
  - offset: int (pagination)

Response:
{
  "events": [...],  # EventEnvelope array
  "total": 1523,
  "limit": 100,
  "offset": 0
}
```

```
GET /api/v1/events/{event_id}
Response: EventEnvelope (single event with full details)
```

```
GET /api/v1/events/{event_id}/descendants
Response:
{
  "root_event": EventEnvelope,
  "descendants": [
    {
      "event": EventEnvelope,
      "depth": 1,  # Levels away from root
      "path": ["uuid-1", "uuid-2", "uuid-3"]  # Causation path
    },
    ...
  ],
  "total_descendants": 45
}
```

#### Workflow Queries

```
GET /api/v1/workflows/{workflow_id}
Response: Workflow state projection

GET /api/v1/workflows/{workflow_id}/timeline
Response:
{
  "workflow_id": "uuid",
  "timeline": [
    {
      "timestamp": "2026-01-10T09:00:00Z",
      "event_type": "bmad.workflow.started",
      "event_id": "uuid",
      "agent": "bmad-analyst",
      "summary": "Workflow initiated"
    },
    ...
  ]
}
```

#### Agent Session Queries

```
GET /api/v1/agents/{session_id}
Response: Agent session details including checkpoint history

GET /api/v1/agents/{session_id}/checkpoints
Response: List of all checkpoints for Letta agent session

GET /api/v1/agents/{session_id}/events
Response: All events produced by this agent session
```

#### Real-Time Streaming

```
WS /api/v1/events/stream
Subscribe to real-time event stream

Message Format:
{
  "type": "event",
  "data": EventEnvelope
}

Client sends filters:
{
  "type": "subscribe",
  "filters": {
    "event_types": ["bmad.workflow.*", "agent.letta.*"],
    "workflow_id": "uuid"
  }
}
```

### Letta Agent API

**Base URL:** `https://letta.33god.io/v1`

```
POST /api/v1/agents
Create new Letta agent

Request:
{
  "agent_type": "python-dev",
  "name": "Python Developer 001",
  "system_prompt": "You are an expert Python developer...",
  "mcp_servers": ["filesystem", "github"],
  "initial_context": {
    "workflow_id": "uuid",
    "task_description": "..."
  }
}

Response:
{
  "agent_id": "uuid",
  "instance_id": "letta-python-dev-001",
  "status": "active",
  "checkpoint_id": "initial-checkpoint-uuid"
}
```

```
POST /api/v1/agents/{agent_id}/tasks
Assign task to agent

Request:
{
  "task_type": "implement_feature",
  "description": "...",
  "context": {...},
  "correlation_id": "parent-event-uuid"
}

Response:
{
  "task_id": "uuid",
  "status": "accepted",
  "estimated_checkpoints": 3
}
```

```
GET /api/v1/agents/{agent_id}/checkpoints/{checkpoint_id}
Retrieve specific checkpoint

Response:
{
  "checkpoint_id": "uuid",
  "created_at": "timestamp",
  "memory_snapshot": {...},
  "context": {...}
}
```

---

## NFR Coverage

### NFR-001: Observability

**Requirement:** Complete visibility into all agent interactions and workflow state

**Architecture Solution:**

- **Event Sourcing**: Every coordination action produces immutable event
- **Correlation IDs**: Link related events across agent handoffs
- **Event Store API**: Query event history with flexible filters
- **Real-time Streaming**: WebSocket API for live monitoring
- **Holocene Dashboard**: Visualize workflow timelines and agent status

**Implementation Notes:**

- Event store manager subscribes to all events with `#` wildcard
- Correlation IDs form directed acyclic graph of causation
- Dashboard uses WebSocket for sub-second latency updates

**Validation:**

- Query any workflow's complete event history
- Trace causation from any event to its descendants
- Real-time dashboard shows agent state within 500ms

### NFR-002: Reliability & Recovery

**Requirement:** System must handle agent failures gracefully and support recovery

**Architecture Solution:**

- **Letta Checkpoints**: Periodic state snapshots enable resume from failure
- **Event Replay**: Reconstruct workflow state from event history
- **Transactional Outbox**: Events only published after successful DB commit
- **Dead Letter Queue**: Failed event processing sent to DLQ for analysis
- **Circuit Breakers**: Prevent cascading failures between components

**Implementation Notes:**

- Letta agents checkpoint every 50 messages or 10 minutes
- Checkpoint IDs stored in events for recovery correlation
- Event store manager uses transactional outbox pattern
- RabbitMQ DLQ configured with 3 retry attempts

**Validation:**

- Kill Letta agent mid-task, resume from checkpoint
- Simulate network partition, verify event replay
- Test RabbitMQ failure with circuit breaker

### NFR-003: Scalability

**Requirement:** Support 50+ concurrent workflows with multiple agents per workflow

**Architecture Solution:**

- **Stateless BMAD**: Claude skills scale horizontally (no shared state)
- **Letta Agent Pool**: Maintain pool of warm Letta instances
- **Event Bus Partitioning**: RabbitMQ topic exchange scales via queue sharding
- **PostgreSQL Partitioning**: Events table partitioned by timestamp
- **Redis Caching**: Cache hot workflow state projections

**Implementation Notes:**

- Letta agent pool: 10 instances per type (python-dev, rust-dev, etc.)
- PostgreSQL monthly partitions with retention policy
- Redis TTL: 1 hour for workflow state, 5 minutes for agent status

**Validation:**

- Load test: 100 concurrent workflows
- Monitor event throughput: >1000 events/sec
- Query performance: <100ms for recent workflow events

### NFR-004: Data Consistency

**Requirement:** Event store must maintain strong consistency for workflow state

**Architecture Solution:**

- **PostgreSQL ACID**: Transactions guarantee event consistency
- **Idempotency Keys**: Event IDs prevent duplicate event storage
- **Optimistic Locking**: Workflow state updates use version numbers
- **Event Ordering**: Timestamps with microsecond precision

**Implementation Notes:**

- Event store manager uses PostgreSQL transactions
- Duplicate event_id inserts raise unique constraint violation
- Workflow state table has version column incremented on update

**Validation:**

- Concurrent event writes from multiple agents
- Verify no duplicate events in store
- Workflow state always matches event history projection

### NFR-005: Security & Access Control

**Requirement:** Event data must be protected with role-based access

**Architecture Solution:**

- **JWT Authentication**: Service-to-service auth with scoped tokens
- **API Key Authorization**: Per-service API keys for event queries
- **Row-Level Security**: PostgreSQL RLS policies on events table
- **Audit Logging**: All API access logged with user/service context
- **Encryption at Rest**: PostgreSQL data encryption

**Implementation Notes:**

- JWT tokens issued by Auth0 with service claims
- RLS policies filter events by workflow ownership
- API access logs stored in separate audit table

**Validation:**

- Verify BMAD agents can only read their workflow events
- Test unauthorized access returns 403
- Audit logs capture all event queries

### NFR-006: Performance

**Requirement:** Event queries respond in <200ms for p95 latency

**Architecture Solution:**

- **Indexing Strategy**: GIN index on correlation_ids, B-tree on event_type
- **Query Optimization**: Limit clauses, pagination
- **Redis Caching**: Cache recent workflow timelines
- **Connection Pooling**: PgBouncer for PostgreSQL connections
- **Read Replicas**: Separate read traffic from writes

**Implementation Notes:**

- PostgreSQL indexes cover 90% of query patterns
- Redis cache hit rate target: >80%
- PgBouncer pool size: 100 connections

**Validation:**

- Load test event queries with 100 concurrent users
- Monitor p95 latency <200ms
- Cache hit rate >80% during normal operations

---

## Event-Driven Coordination Patterns

### Pattern 1: BMAD → Letta Handoff

**Scenario:** BMAD Architect completes architecture, delegates implementation to Letta Python Dev

**Event Sequence:**

```
1. bmad.workflow.phase.completed
   - from: bmad-architect
   - phase: solutioning
   - correlation_ids: [analysis_event, planning_event]

2. bmad.workflow.handoff.requested
   - from: bmad-architect
   - to: letta-python-dev
   - task: implement_feature
   - context: {architecture decisions, requirements}
   - correlation_ids: [phase_completed_event]

3. agent.handoff.accepted
   - from: letta-python-dev
   - correlation_ids: [handoff_requested_event]
   - checkpoint_id: initial-checkpoint

4. agent.letta.checkpoint.saved (periodic)
   - from: letta-python-dev
   - checkpoint_type: progress
   - correlation_ids: [handoff_accepted_event]

5. agent.letta.task.completed
   - from: letta-python-dev
   - artifacts: [modified files]
   - next_action: qa_review
   - correlation_ids: [handoff_accepted_event, last_checkpoint]

6. bmad.workflow.validation.requested
   - from: bmad-code-reviewer
   - target_agent: letta-python-dev
   - correlation_ids: [task_completed_event]
```

**Correlation ID Chain:**

```
analysis → planning → solutioning → handoff_request → handoff_accept
  → checkpoint_1 → checkpoint_2 → checkpoint_3 → task_complete → validation
```

### Pattern 2: Multi-Agent Collaboration

**Scenario:** Director of Engineering coordinates mise standardization across 3 services with mise-architect + 3 Letta agents

**Event Sequence:**

```
1. agent.collaboration.started
   - from: director-of-engineering
   - participants: [mise-architect, letta-python-dev, letta-rust-dev, letta-ts-dev]
   - goal: standardize_mise_tasks
   - correlation_ids: []

2. director.mise.standardization.requested
   - from: director-of-engineering
   - orchestrator: mise-architect
   - target_services: [service-a, service-b, service-c]
   - correlation_ids: [collaboration_started]

3. agent.collaboration.participant.joined (x4, one per agent)
   - from: mise-architect | letta-python-dev | letta-rust-dev | letta-ts-dev
   - role: orchestrator | implementer | implementer | implementer
   - correlation_ids: [collaboration_started]

4. mise.pattern.defined (from mise-architect)
   - standard_tasks: {build, test, deploy, lint}
   - task_interface: {...}
   - correlation_ids: [collaboration_started]

5. director.service.delegation.requested (x3, one per service)
   - from: director-of-engineering
   - to: letta-python-dev | letta-rust-dev | letta-ts-dev
   - service: service-a | service-b | service-c
   - pattern_reference: pattern_defined_event
   - correlation_ids: [pattern_defined]

6. agent.letta.task.completed (x3, as each finishes)
   - from: letta-{type}-dev
   - service: service-{x}
   - artifacts: [mise.toml, mise-tasks/*]
   - correlation_ids: [delegation_requested]

7. mise.validation.requested (from mise-architect)
   - validates: all_service_implementations
   - correlation_ids: [all task_completed events]

8. agent.collaboration.completed
   - from: director-of-engineering
   - outcome: success
   - summary: All services standardized
   - correlation_ids: [collaboration_started, validation_complete]
```

**Correlation Graph:**

```
collaboration_started
  ├─> mise.standardization.requested
  │     └─> mise.pattern.defined
  │           ├─> service-a.delegation
  │           │     └─> service-a.completed
  │           ├─> service-b.delegation
  │           │     └─> service-b.completed
  │           └─> service-c.delegation
  │                 └─> service-c.completed
  │                       └─> validation.requested
  └─> collaboration.completed
```

### Pattern 3: Letta Checkpoint Recovery

**Scenario:** Letta agent crashes mid-task, recovers from checkpoint

**Event Sequence:**

```
1. agent.letta.checkpoint.saved
   - checkpoint_id: checkpoint-123
   - checkpoint_type: progress
   - context_snapshot: {files_modified, current_focus}

2. agent.letta.session.failed (system detects crash)
   - session_id: original_session
   - last_checkpoint_id: checkpoint-123
   - failure_reason: connection_timeout

3. agent.letta.session.recovery.started
   - new_session_id: recovery_session
   - recovering_from_checkpoint: checkpoint-123
   - correlation_ids: [session_failed]

4. agent.letta.context.restored
   - session_id: recovery_session
   - checkpoint_id: checkpoint-123
   - context_delta: {what changed since checkpoint}
   - correlation_ids: [recovery_started]

5. agent.letta.task.resumed
   - session_id: recovery_session
   - resuming_from: checkpoint-123
   - correlation_ids: [context_restored]

# Continues normally with periodic checkpoints...

6. agent.letta.task.completed
   - session_id: recovery_session
   - correlation_ids: [original handoff, checkpoint-123, task_resumed]
```

### Pattern 4: Feedback Loop (Human in the Loop)

**Scenario:** Letta agent needs clarification from user

**Event Sequence:**

```
1. agent.feedback.requested
   - from: letta-python-dev
   - question: "Should authentication use JWT or session cookies?"
   - context: {architecture decisions, tradeoffs}
   - blocking: true  # Agent paused until response

2. agent.letta.checkpoint.saved (auto-checkpoint before pause)
   - checkpoint_type: pre-feedback
   - correlation_ids: [feedback_requested]

3. agent.letta.session.paused
   - reason: awaiting_feedback
   - correlation_ids: [feedback_requested]

# Human reviews question via Holocene dashboard

4. agent.feedback.response
   - from: human_user
   - decision: "Use JWT with refresh tokens"
   - rationale: "Better for microservices"
   - correlation_ids: [feedback_requested]

5. agent.letta.session.resumed
   - session_id: same_session
   - resuming_from_checkpoint: pre-feedback checkpoint
   - correlation_ids: [feedback_response]

6. agent.letta.context.updated
   - decision_incorporated: "JWT authentication approach"
   - correlation_ids: [feedback_response]

# Work continues...
```

---

## Deployment Architecture

### Docker Compose Services

```yaml
version: "3.8"

services:
  # Event Bus
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: bloodbank
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  # Event Store
  postgres:
    image: postgres:14
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: event_store
      POSTGRES_USER: bloodbank
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d

  # Redis Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # Candystore
  event-store-manager:
    build: ./event-store-manager
    depends_on:
      - rabbitmq
      - postgres
      - redis
    environment:
      RABBITMQ_URL: amqp://bloodbank:${RABBITMQ_PASSWORD}@rabbitmq:5672
      DATABASE_URL: postgresql://bloodbank:${POSTGRES_PASSWORD}@postgres:5432/event_store
      REDIS_URL: redis://redis:6379
    restart: unless-stopped

  # Letta Server
  letta-server:
    build: ./letta-server
    ports:
      - "8283:8283"
    depends_on:
      - postgres
      - rabbitmq
    environment:
      LETTA_SERVER_PORT: 8283
      LETTA_PG_URI: postgresql://bloodbank:${POSTGRES_PASSWORD}@postgres:5432/letta
      RABBITMQ_URL: amqp://bloodbank:${RABBITMQ_PASSWORD}@rabbitmq:5672
    volumes:
      - letta_data:/root/.letta
    restart: unless-stopped

  # Collaboration Coordinator
  collaboration-coordinator:
    build: ./collaboration-coordinator
    depends_on:
      - rabbitmq
      - redis
      - postgres
    environment:
      RABBITMQ_URL: amqp://bloodbank:${RABBITMQ_PASSWORD}@rabbitmq:5672
      REDIS_URL: redis://redis:6379
      DATABASE_URL: postgresql://bloodbank:${POSTGRES_PASSWORD}@postgres:5432/event_store
    restart: unless-stopped

  # Event Store API
  event-store-api:
    build: ./event-store-api
    ports:
      - "8080:8080"
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://bloodbank:${POSTGRES_PASSWORD}@postgres:5432/event_store
      REDIS_URL: redis://redis:6379
      JWT_SECRET: ${JWT_SECRET}
    restart: unless-stopped

  # Holocene Dashboard (Frontend + Backend)
  holocene:
    build: ./holocene
    ports:
      - "3000:3000"
    depends_on:
      - event-store-api
    environment:
      EVENT_STORE_API_URL: http://event-store-api:8080
    restart: unless-stopped

volumes:
  rabbitmq_data:
  postgres_data:
  redis_data:
  letta_data:
```

### Environment Configuration

**.env file:**

```bash
# Secrets
RABBITMQ_PASSWORD=<strong-password>
POSTGRES_PASSWORD=<strong-password>
JWT_SECRET=<strong-secret>

# Service URLs
EVENT_STORE_API_URL=http://localhost:8080
LETTA_SERVER_URL=http://localhost:8283

# Feature Flags
ENABLE_EVENT_REPLAY=true
ENABLE_CHECKPOINT_RECOVERY=true
```

---

## Traceability

### Functional Requirements Coverage

| FR ID  | Requirement                 | Components                              | Events                          |
| ------ | --------------------------- | --------------------------------------- | ------------------------------- |
| FR-001 | BMAD workflow orchestration | BMAD Orchestrator, Event Store          | bmad.workflow.\*                |
| FR-002 | Letta agent execution       | Letta Runtime, Event Store              | agent.letta.\*                  |
| FR-003 | Agent handoffs              | BMAD Orchestrator, Letta Runtime        | agent.handoff.\*                |
| FR-004 | Persistent agent context    | Letta Runtime, PostgreSQL               | agent.letta.checkpoint.\*       |
| FR-005 | Event history queries       | Candystore, API                         | All events                      |
| FR-006 | Real-time monitoring        | Event Store API, Holocene               | Event stream                    |
| FR-007 | Multi-agent collaboration   | Collaboration Coordinator               | agent.collaboration.\*          |
| FR-008 | Cross-service orchestration | Director of Engineering, mise-architect | director._, mise._              |
| FR-009 | Human feedback loops        | BMAD Orchestrator, Letta Runtime        | agent.feedback.\*               |
| FR-010 | Checkpoint recovery         | Letta Runtime, Event Store              | agent.letta.session.recovery.\* |

### Non-Functional Requirements Coverage

| NFR ID  | Requirement   | Solution                                    | Validation                      |
| ------- | ------------- | ------------------------------------------- | ------------------------------- |
| NFR-001 | Observability | Event sourcing, correlation IDs, dashboard  | Query complete workflow history |
| NFR-002 | Reliability   | Checkpoints, event replay, circuit breakers | Agent recovery from failure     |
| NFR-003 | Scalability   | Stateless BMAD, agent pools, partitioning   | 100 concurrent workflows        |
| NFR-004 | Consistency   | PostgreSQL ACID, idempotency                | No duplicate events             |
| NFR-005 | Security      | JWT auth, RLS policies, encryption          | Unauthorized access blocked     |
| NFR-006 | Performance   | Indexing, caching, connection pooling       | p95 latency <200ms              |

---

## Trade-offs & Decisions

### Decision 1: PostgreSQL vs Purpose-Built Event Store

**Choice:** PostgreSQL with JSONB for event storage

**Trade-offs:**

- ✓ Gain: Familiar technology, existing operational expertise
- ✓ Gain: Rich query capabilities (joins, aggregations, window functions)
- ✓ Gain: ACID guarantees for consistency
- ✗ Lose: Not optimized for event replay (vs EventStoreDB)
- ✗ Lose: Manual implementation of event projections

**Rationale:** PostgreSQL already in stack (DeLorenzo preference). Rich querying more valuable than specialized event store features for 33GOD use case. Event replay frequency expected to be low (recovery scenarios only).

### Decision 2: RabbitMQ vs Kafka

**Choice:** RabbitMQ topic exchange (already deployed)

**Trade-offs:**

- ✓ Gain: Already running in Bloodbank infrastructure
- ✓ Gain: Simpler operational model vs Kafka
- ✓ Gain: Topic-based routing fits event patterns
- ✗ Lose: Lower throughput ceiling vs Kafka
- ✗ Lose: No built-in event retention (use PostgreSQL instead)

**Rationale:** RabbitMQ sufficient for expected event volume (<1000 events/sec). Operational simplicity prioritized over extreme throughput. Event retention handled by PostgreSQL event store.

### Decision 3: Letta vs Custom Agent Framework

**Choice:** Letta framework for autonomous agents

**Trade-offs:**

- ✓ Gain: Built-in checkpoint system for persistence
- ✓ Gain: Active development community
- ✓ Gain: MCP server integration
- ✓ Gain: Multi-agent collaboration primitives
- ✗ Lose: Dependency on third-party framework
- ✗ Lose: Less control over agent internals

**Rationale:** Persistent context via checkpoints critical for long-running tasks. Building equivalent checkpoint system from scratch would be XL effort. Letta's MCP integration aligns with 33GOD tooling strategy.

### Decision 4: Event Store as Shared State

**Choice:** PostgreSQL event store for coordination state

**Trade-offs:**

- ✓ Gain: Single source of truth for workflow state
- ✓ Gain: Audit trail for debugging and compliance
- ✓ Gain: Enables event replay for recovery
- ✓ Gain: Causation tracking via correlation IDs
- ✗ Lose: Additional infrastructure complexity
- ✗ Lose: Write amplification (every event persisted)

**Rationale:** Control/agency requirements mandate full observability. Event sourcing provides complete audit trail. Correlation IDs enable causal analysis. Write amplification acceptable given event volume and PostgreSQL performance.

---

## Implementation Roadmap

### Phase 1: Foundation (Effort: L)

**Goal:** Event store infrastructure and basic BMAD → Letta handoff

**Deliverables:**

- PostgreSQL event schema (tables, indexes)
- Event store manager (Bloodbank subscriber → PostgreSQL writer)
- Event store API (basic event queries)
- New event types registered in Bloodbank
- BMAD orchestrator publishes handoff events
- Letta runtime consumes handoff events

**Success Criteria:**

- BMAD can delegate task to Letta agent
- Events persisted to PostgreSQL
- Query API returns workflow events

### Phase 2: Checkpoints & Recovery (Effort: M)

**Goal:** Letta persistent context and recovery

**Deliverables:**

- Letta checkpoint events
- Checkpoint storage integration
- Recovery workflow implementation
- Agent session tracking

**Success Criteria:**

- Letta saves checkpoints every 10 minutes
- Agent can resume from checkpoint after failure
- Session state queryable via API

### Phase 3: Collaboration (Effort: L)

**Goal:** Multi-agent coordination patterns

**Deliverables:**

- Collaboration coordinator service
- Collaboration events
- Director of Engineering workflows
- mise-architect integration

**Success Criteria:**

- 3 agents coordinate on cross-service task
- Collaboration state tracked in event store
- Director can orchestrate mise standardization

### Phase 4: Observability (Effort: M)

**Goal:** Dashboard and monitoring

**Deliverables:**

- Event stream WebSocket API
- Holocene workflow timeline view
- Agent status dashboard
- Causation graph visualization

**Success Criteria:**

- Real-time event stream <500ms latency
- Workflow timeline shows all agent transitions
- Causation graph navigable from any event

### Phase 5: Production Hardening (Effort: M)

**Goal:** Reliability, performance, security

**Deliverables:**

- Circuit breakers
- PostgreSQL read replicas
- Redis caching
- JWT authentication
- Load testing and optimization

**Success Criteria:**

- p95 query latency <200ms
- 100 concurrent workflows supported
- All API endpoints authenticated

---

## Validation Checklist

- ✅ All architectural drivers addressed
- ✅ Components defined with responsibilities
- ✅ Event schemas documented
- ✅ API contracts specified
- ✅ NFRs mapped to solutions
- ✅ Technology choices justified
- ✅ Trade-offs documented
- ✅ Coordination patterns detailed
- ✅ Deployment architecture specified
- ✅ Implementation roadmap provided

---

## Next Steps

1. **Review with Director of Engineering**: Validate cross-service coordination patterns
2. **BMAD Sprint Planning**: Break Phase 1 into implementation stories
3. **Letta Integration Prototype**: Validate checkpoint recovery approach
4. **Event Schema Finalization**: Lock down event types before implementation begins
5. **Infrastructure Provisioning**: Set up PostgreSQL event store, Redis cache

---

## References

- Bloodbank Event Architecture: `/home/delorenj/code/33GOD/bloodbank/trunk-main/EventDrivenArchitecture.md`
- Bloodbank Event Types: `/home/delorenj/code/33GOD/bloodbank/trunk-main/event_producers/events/types.py`
- Service Registry: `/home/delorenj/code/33GOD/services/registry.yaml`
- mise-architect Agent: `~/.claude/skills/bmad/bmb/mise-architect/SKILL.md`
- 33GOD System Expert Skill: `~/.claude/skills/33god-system-expert/SKILL.md`

---

**Document Control:**

- **Created:** 2026-01-11
- **Last Modified:** 2026-01-11
- **Approved By:** [Pending Director of Engineering Review]
- **Version:** 1.0.0
