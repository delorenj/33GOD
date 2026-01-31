# C4 Code Level: Agent Orchestration Domain

## Overview
- **Name**: Agent Orchestration System
- **Description**: Corporate-metaphor-based hierarchical agent orchestration framework implementing the Flume protocol with Yi adapters, supporting task delegation, memory management, and multi-agent coordination
- **Location**: `/home/delorenj/code/33GOD/flume/trunk-main/packages/`
- **Languages**: TypeScript (primary), Python (task monitoring)
- **Purpose**: Enable scalable, hierarchical agent coordination with corporate-style roles (Contributors, Managers, Directors), stateful lifecycle management, and flexible selection strategies

## Architecture Patterns

### Programming Paradigm: Object-Oriented with Interface-Based Design
- **Pattern**: Hierarchical agent system using inheritance and composition
- **Core Abstraction**: Employee interface extended by Contributor, Manager, Director
- **Design Philosophy**: Corporate anthropomorphization (agents as employees)
- **State Management**: Finite state machine for agent lifecycle
- **Communication**: Event-driven task delegation through RabbitMQ

## Code Elements

### Core Type Definitions (Flume Protocol)

#### `/packages/flume-core/src/types/employee.ts`

**Interfaces:**
- `Employee` - Base interface for all agents
  - Properties: `id: string`, `name: string`, `role: string`, `state: AgentState`, `teamId: string`, `skills: string[]`, `salary: number`
  - Methods: `reportStatus(): Promise<EmployeeStatus>`
  - Location: lines 22-46

- `Contributor` (extends Employee) - Individual contributor, leaf node
  - Methods: `canHandle(task: TaskPayload): boolean | Promise<boolean>`, `execute(task: TaskPayload): Promise<WorkResult>`
  - Location: lines 72-84
  - Purpose: Execute tasks directly without delegation

- `Delegator` - Capability interface for team management
  - Properties: `subordinates: Employee[]`
  - Methods: `recruit(employee: Employee): void`, `release(employeeId: string): void`, `delegate(task: TaskPayload): Promise<WorkResult>`
  - Location: lines 90-110
  - Purpose: Manage subordinates and delegate work

- `Manager` (extends Contributor, Delegator) - Branch node
  - Location: lines 116-118
  - Purpose: Can both execute tasks AND delegate to subordinates

- `Director` (extends Employee, Delegator) - Pure orchestrator
  - Location: lines 124-126
  - Purpose: ONLY delegates, never executes directly

- `SelectionStrategy` - Strategy pattern for candidate selection
  - Properties: `name: string`
  - Methods: `select(task: TaskPayload, candidates: Employee[]): Promise<Employee | null>`
  - Location: lines 132-144

**Data Structures:**
- `EmployeeStatus` - Status report structure
  - Fields: `state`, `currentTaskId?`, `message`, `timestamp`, `blockers?`
  - Location: lines 51-66

#### `/packages/flume-core/src/types/task.ts`

**Interfaces:**
- `TaskPayload` - Atomic unit of work
  - Key fields: `id`, `correlationId`, `parentTaskId?`, `objective`, `context`, `priority?`, `tags?`
  - Plane integration: `externalId?`, `planeWorkspace?`, `planeProjectId?`
  - Location: lines 10-46
  - Dependencies: Flows through delegation hierarchy

- `RecruitmentRequest` - Agent hiring specification
  - Fields: `requiredSkills`, `reportingToManagerId`, `teamId`, `preferredFramework?`, `isContractor?`
  - Location: lines 65-81

**Enums:**
- `TaskState` - Workflow states
  - Values: `draft | open | ready | assigned | in_progress | blocked | in_review | done | failed | cancelled`
  - Location: lines 51-61

#### `/packages/flume-core/src/types/result.ts`

**Interfaces:**
- `WorkResult` - Structured execution response
  - Fields: `status`, `output`, `metrics`, `error?`, `delegatedTo?`, `artifacts?`, `completedAt`
  - Location: lines 9-30

- `ExecutionMetrics` - Performance tracking
  - Fields: `durationMs`, `tokensUsed?`, `costUsd?`, `retries?`, `delegationDepth?`
  - Location: lines 35-50

- `WorkError` - Error details
  - Fields: `code`, `message`, `retryable`, `stack?`, `cause?`
  - Location: lines 55-70

- `Artifact` - Output artifacts (33GOD types)
  - Fields: `id`, `type`, `title`, `content`, `createdAt`, `createdBy`
  - Types: `decision | brief | checkpoint | recommendation | code | document`
  - Location: lines 76-94

#### `/packages/flume-core/src/types/state.ts`

**Enums:**
- `AgentState` - Lifecycle states
  - Values: `initializing | onboarding | idle | working | delegating | blocked | reviewing | errored | terminated`
  - Location: lines 10-19

**Data Structures:**
- `StateTransition` - Audit trail record
  - Fields: `employeeId`, `fromState`, `toState`, `trigger`, `timestamp`, `taskId?`, `error?`
  - Location: lines 24-45

**Constants:**
- `VALID_TRANSITIONS: Record<AgentState, AgentState[]>` - State machine definition
  - Location: lines 51-61
  - Purpose: Validate state transitions

**Functions:**
- `isValidTransition(from: AgentState, to: AgentState): boolean`
  - Location: lines 66-68
  - Purpose: Validate state transitions

### Yi Adapter Layer (Agent Implementation)

#### `/packages/yi-adapter/src/agents/base-contributor.ts`

**Classes:**
- `BaseContributor` (implements Contributor, YiAgent)
  - Properties: `id`, `name`, `role`, `teamId`, `skills`, `salary`, `_state`, `_currentTaskId?`, `_memory?`
  - Constructor: Takes config object with optional id, required name/role/teamId/skills, optional salary (default 50000)
  - Location: lines 23-49
  - Dependencies: uuid for ID generation, Flume core types

**Key Methods:**
- `get state(): AgentState` - State accessor (line 51-53)
- `transitionTo(newState: AgentState, trigger: string): void` - Validated state transitions (lines 58-68)
- `reportStatus(): Promise<EmployeeStatus>` - Status reporting (lines 73-80)
- `getStatusMessage(): string` - Human-readable status (lines 85-104)
- `canHandle(task: TaskPayload): boolean` - Task capability check (lines 110-125)
  - Logic: Must be idle + has relevant skills
- `execute(task: TaskPayload): Promise<WorkResult>` - Execute task with error handling (lines 131-183)
  - Workflow: Check idle → transition to working → doWork() → transition to idle → return result
- `injectMemory(memory: OnboardingPacket): Promise<void>` - Onboarding memory injection (lines 188-192)
- `verifyReadiness(): Promise<boolean>` - Post-onboarding verification (lines 197-205)
- `abstract doWork(task: TaskPayload): Promise<unknown>` - Subclass implementation hook (line 210)

#### `/packages/yi-adapter/src/agents/base-director.ts`

**Classes:**
- `BaseDirector` (implements Director, YiAgent)
  - Properties: `id`, `name`, `role`, `teamId`, `skills`, `salary`, `_state`, `_currentTaskId?`, `_memory?`, `_subordinates: Employee[]`, `selectionStrategy: SelectionStrategy`
  - Constructor: Takes config + selection strategy, default salary 200000
  - Location: lines 24-54
  - Dependencies: SelectionStrategy for delegation decisions

**Key Methods:**
- `get subordinates(): Employee[]` - Safe subordinate list access (lines 60-62)
- `recruit(employee: Employee): void` - Add subordinate (lines 90-97)
- `release(employeeId: string): void` - Remove subordinate (lines 99-107)
- `delegate(task: TaskPayload): Promise<WorkResult>` - Core delegation logic (lines 112-193)
  - Workflow: Apply strategic context → selection strategy → delegate/execute → return enriched result
  - Handles both Manager (delegate) and Contributor (execute) subordinates
- `applyStrategicContext(task: TaskPayload): Promise<TaskPayload>` - Enrich tasks with strategic direction (lines 199-205)
- `handleNoCandidate(task: TaskPayload, startTime: number): Promise<WorkResult>` - Escalation handling (lines 211-226)

### Selection Strategies

#### `/packages/yi-adapter/src/selection/first-match.ts`

**Classes:**
- `FirstMatchSelection` (implements SelectionStrategy)
  - Property: `name = 'first-match'`
  - Method: `select(task, candidates): Promise<Employee | null>`
  - Location: lines 13-45
  - Logic: Iterate until first capable candidate found

- `RoundRobinSelection` (implements SelectionStrategy)
  - Property: `name = 'round-robin'`, `lastIndex = -1`
  - Method: `select(task, candidates): Promise<Employee | null>`
  - Location: lines 50-87
  - Logic: Rotate through candidates for load balancing

#### `/packages/yi-adapter/src/selection/skill-match.ts`

**Interfaces:**
- `SkillMatchScore` - Scoring result
  - Fields: `employee`, `score`, `matchedSkills`, `matchedTags`, `matchedKeywords`
  - Location: lines 18-24

- `SkillMatchConfig` - Configuration
  - Fields: `tagWeight?`, `keywordWeight?`, `minimumScore?`, `requireIdle?`
  - Location: lines 29-38

**Classes:**
- `SkillMatchSelection` (implements SelectionStrategy)
  - Property: `name = 'skill-match'`, `config: Required<SkillMatchConfig>`
  - Constructor: Takes optional config (defaults: tagWeight=3, keywordWeight=1)
  - Location: lines 59-238

**Key Methods:**
- `select(task, candidates): Promise<Employee | null>` - Best skill match selection (lines 70-107)
- `scoreAllCandidates(task, candidates): Promise<SkillMatchScore[]>` - Batch scoring (lines 113-125)
- `scoreCandidate(task, candidate): Promise<SkillMatchScore>` - Individual scoring (lines 130-175)
  - Scoring: tags × 3 + keywords × 1, filtered by canHandle()
- `extractKeywords(objective: string): string[]` - Keyword extraction with stop-word filtering (lines 181-212)
- `getDetailedScores(task, candidates)` - Debugging/analysis helper (lines 217-237)

#### `/packages/yi-adapter/src/selection/llm-driven.ts`

**Interfaces:**
- `LLMProvider` - LLM abstraction
  - Method: `selectCandidate(prompt: string): Promise<number>`
  - Location: lines 13-20

**Classes:**
- `LLMDrivenSelection` (implements SelectionStrategy)
  - Property: `name = 'llm-driven'`, `llmProvider: LLMProvider`, `fallbackToFirstMatch: boolean`
  - Constructor: Takes LLM provider + optional fallback flag
  - Location: lines 26-119

**Key Methods:**
- `select(task, candidates): Promise<Employee | null>` - LLM-based selection with fallback (lines 34-68)
- `buildSelectionPrompt(task, candidates): string` - Construct LLM prompt (lines 73-103)
- `firstMatch(task, candidates): Promise<Employee | null>` - Fallback strategy (lines 108-118)

**Mock Implementation:**
- `MockLLMProvider` (implements LLMProvider)
  - Method: `selectCandidate(prompt): Promise<number>` - Returns 0 for testing
  - Location: lines 125-137

### Memory Management (Yi Adapter)

#### `/packages/yi-adapter/src/memory/strategy.ts`

**Interfaces:**
- `MemoryShard` - Memory storage pointer
  - Fields: `id`, `type`, `pointer`, `createdAt`, `isActive`, `metadata?`
  - Types: `qdrant | agentfile | neo4j | letta-core | redis | custom`
  - Location: lines 11-29

- `YiMemoryStrategy` - Memory operations interface
  - Methods: `fetchContext(knowledgeBaseId)`, `syncContext(knowledgeBaseId, context)`, `search(knowledgeBaseId, query, topK?)`, `getActiveShard(agentId)`, `switchShard(agentId, shardId)`
  - Location: lines 34-72

- `MemoryContext` - Retrieved context structure
  - Fields: `core`, `conversations?`, `knowledge?`, `skills?`, `protocols?`
  - Location: lines 77-92

- `MemorySearchResult` - Search result
  - Fields: `content`, `score`, `source`, `timestamp`
  - Location: lines 106-118

- `ConversationEntry` - Conversation history
  - Fields: `role`, `content`, `timestamp`
  - Location: lines 97-101

#### `/packages/yi-adapter/src/memory/team-context.ts`

**Interfaces:**
- `TeamContext` - Complete onboarding context
  - Fields: `teamId`, `missionStatement`, `sharedKnowledgeBaseId`, `accessLevel`, `projectContext?`, `techContext?`, `companyContext?`
  - Location: lines 18-39

- `ProjectContext` - Director-level context
  - Fields: `threads`, `northStars`, `kpis`, `timeline`, `sprintGoals`
  - Location: lines 45-60

- `TechContext` - L&D context
  - Fields: `memories`, `lessonsLearned`, `skills`, `mcpServers`, `tools`
  - Location: lines 66-81

- `CompanyContext` - CEO/Board context
  - Fields: `codingStandards`, `infrastructure`, `securityPolicies`, `communicationProtocols`
  - Location: lines 87-99

- `InfrastructureConfig` - 33GOD infrastructure
  - Fields: `rabbitmq`, `postgres`, `redis`, `qdrant`, `plane`
  - Location: lines 131-164

**Enums/Types:**
- `ContextLevel = 'project' | 'tech' | 'company'` (line 13)
- `accessLevel: 'intern' | 'contractor' | 'full-time' | 'executive'` (line 29)

### Echo Implementation (Testing/Reference)

#### `/packages/yi-echo/src/agents/echo-contributor.ts`

**Classes:**
- `EchoContributor` (extends BaseContributor)
  - Constructor: Configurable, defaults to "Echo IC" role
  - Method: `doWork(task): Promise<string>` - Echoes completion message
  - Location: lines 12-49

- `EchoSlowContributor` (extends EchoContributor)
  - Constructor: Takes delay in ms (default 2000)
  - Method: `doWork(task): Promise<string>` - Adds artificial delay
  - Location: lines 55-77
  - Purpose: Test timeout handling

#### `/packages/yi-echo/src/agents/echo-director.ts`

**Classes:**
- `EchoDirector` (extends BaseDirector)
  - Constructor: Configurable, defaults to "Echo Director" role, uses FirstMatchSelection
  - Method: `applyStrategicContext(task): Promise<TaskPayload>` - Adds strategic metadata
  - Location: lines 12-54

#### `/packages/yi-echo/src/memory/echo-memory.ts`

**Classes:**
- `EchoMemory` (implements YiMemoryStrategy)
  - Property: `name = 'echo-memory'`
  - Storage: In-memory Maps (contexts, shards, activeShards)
  - Location: lines 17-124

**Key Methods:**
- `fetchContext(knowledgeBaseId): Promise<MemoryContext>` - Retrieve or default context (lines 33-45)
- `syncContext(knowledgeBaseId, context): Promise<void>` - Store context (lines 47-53)
- `search(knowledgeBaseId, query, topK?): Promise<MemorySearchResult[]>` - Mock search (lines 55-73)
- `getActiveShard(agentId): Promise<MemoryShard | null>` - Get active shard (lines 75-83)
- `switchShard(agentId, shardId): Promise<void>` - Switch memory checkpoint (lines 85-103)
- `createShard(agentId, type?): MemoryShard` - Create new shard (lines 108-123)

#### `/packages/yi-echo/src/factory/echo-factory.ts`

**Classes:**
- `EchoFactory` (implements AgentFactory)
  - Property: `name = 'echo-factory'`, `defaultTeamId: string`
  - Method: `createAgent(skills, role?): Promise<Employee>` - Factory method
  - Location: lines 17-71

**Key Methods:**
- `canCreate(skills): boolean` - Always returns true (lines 67-70)
- Routing logic: skills → director | manager | slow | failing | contributor

**Functions:**
- `createEchoTeam(teamId?): {director, manager, contributors[]}` - Create pre-wired team
  - Location: lines 76-118
  - Returns: Director with 1 Manager managing 3 Contributors

### Python Task Monitor (BMAD/Bloodbank Integration)

#### `/flume/feat-task/task-monitor/models.py`

**Enums:**
- `TaskStatus` - Task states
  - Values: `PENDING | ASSIGNED | STARTED | IN_PROGRESS | PAUSED | COMPLETED | FAILED | STALE`
  - Location: lines 11-22

- `EventType` - Event types
  - Values: `ASSIGNED | STARTED | IN_PROGRESS | COMPLETED | FAILED | PAUSED | RESUMED | HEARTBEAT`
  - Location: lines 24-35

**Classes (Pydantic Models):**
- `TaskEvent` - Individual event
  - Fields: `event_type`, `timestamp`, `data`, `agent_id?`, `message?`
  - Location: lines 56-76

- `TaskState` - Complete task tracking
  - Fields: `task_id`, `status`, `agent_id?`, `created_at`, `updated_at`, `started_at?`, `completed_at?`, `last_heartbeat?`
  - Metrics: `time_in_queue?`, `time_processing?`, `total_duration?`
  - History: `events: list[TaskEvent]`
  - Location: lines 79-213

**Key Methods (TaskState):**
- `can_transition_to(new_status): bool` - Validate transition (lines 115-117)
- `add_event(event): void` - Add event and update state (lines 119-130)
- `transition_to(new_status, event, force?): void` - State transition with metrics (lines 132-172)
- `is_stale(stale_threshold_seconds?): bool` - Staleness check (lines 173-188)
- `get_duration_in_status(status): float` - Time tracking (lines 190-210)

**Data Structures:**
- `VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]]` - State machine (lines 38-53)

#### `/flume/feat-task/task-monitor/state_manager.py`

**Classes:**
- `TaskStateManager` - In-memory state management with persistence
  - Properties: `tasks: dict[str, TaskState]`, `persistence_path?`, `stale_threshold`, `retention_hours`
  - Constructor: Takes optional persistence config
  - Location: lines 16-426

**Key Methods:**
- `initialize(): void` - Load state + start background tasks (lines 51-60)
- `shutdown(): void` - Save state + stop background tasks (lines 62-83)
- `handle_event(task_id, event): void` - Process event and update state (lines 85-131)
- `get_task(task_id): TaskState?` - Retrieve task (lines 153-163)
- `get_all_tasks(status?, agent_id?, limit?, offset?): list[TaskState]` - Query with filtering (lines 165-196)
- `get_active_tasks(): list[TaskState]` - Active tasks only (lines 198-213)
- `get_stale_tasks(): list[TaskState]` - Identify and mark stale tasks (lines 215-239)
- `get_metrics(): dict` - Aggregate metrics (lines 241-312)

**Background Tasks:**
- `_persistence_loop(): void` - Periodic state saving (lines 314-327)
- `_save_state(): void` - Atomic file save (lines 329-357)
- `_load_state(): void` - State restoration (lines 359-385)
- `_cleanup_loop(): void` - Old task cleanup (lines 387-399)
- `_cleanup_old_tasks(): void` - Remove terminal tasks past retention (lines 401-425)

#### `/flume/feat-task/task-monitor/consumer.py`

**Classes:**
- `TaskEventConsumer` - RabbitMQ consumer for task events
  - Properties: `rabbitmq_url`, `exchange_name`, `queue_name`, `routing_key_pattern`, `event_handler?`
  - Location: lines 17-265

**Key Methods:**
- `set_event_handler(handler): void` - Register callback (lines 45-53)
- `connect(): void` - Establish RabbitMQ connection + declare queue (lines 55-93)
- `start_consuming(): void` - Begin message processing loop (lines 95-121)
- `_process_message(message): void` - Parse and handle message (lines 123-169)
- `_extract_task_id(routing_key, body): str?` - Extract task ID (lines 171-191)
- `_map_event_type(event_type_str, body): EventType` - Map to enum (lines 193-223)
- `stop(): void` - Graceful shutdown (lines 244-255)

**Classes:**
- `TaskEventPublisher` - RabbitMQ publisher for alerts
  - Properties: `rabbitmq_url`, `exchange_name`
  - Location: lines 268-369

**Key Methods:**
- `connect(): void` - Establish connection (lines 288-306)
- `publish_alert(task_id, alert_type, message, data?): void` - Publish alert (lines 308-351)
- `close(): void` - Close connections (lines 353-359)

### Hive Mind Configuration (iMi Component)

#### `/iMi/trunk-main/.hive-mind/config/queens.json`

**Data Structures:**
- Queen archetypes for high-level coordination:
  - `strategic` - Long-term planning, analytical (adaptability: 0.7)
  - `tactical` - Execution efficiency, pragmatic (adaptability: 0.9)
  - `adaptive` - Dynamic adjustment, flexible (adaptability: 1.0)
- Location: lines 1-59

#### `/iMi/trunk-main/.hive-mind/config/workers.json`

**Data Structures:**
- Worker archetypes for task execution:
  - `architect` - System design (complexity: 0.9, autonomy: 0.8)
  - `researcher` - Information gathering (complexity: 0.7, autonomy: 0.9)
  - `implementer` - Coding/integration (complexity: 0.8, collaboration: 0.8)
  - `tester` - Quality assurance (complexity: 0.6, autonomy: 0.8)
  - `reviewer` - Code review (complexity: 0.8, collaboration: 0.9)
- Location: lines 1-72

## Dependencies

### Internal Dependencies
- **Flume Core** → Yi Adapter: Yi adapters extend Flume core interfaces
- **Yi Adapter** → Yi Echo: Echo agents reference base classes
- **Yi Adapter** → Memory Strategy: Agents use memory strategies for context
- **Task Monitor (Python)** → RabbitMQ: Consumes lifecycle events
- **All Components** → Flume Protocol Types: Shared type system

### External Dependencies
- **TypeScript**: uuid (ID generation), @flume/core (protocol)
- **Python**: pydantic (validation), aio_pika (RabbitMQ), asyncio (async operations)
- **Infrastructure**: RabbitMQ (event bus), PostgreSQL (persistence), Redis (cache), Qdrant (vector store), Plane (project management)

### Framework Integration Points
- **Yi Adapter**: Letta, Agno, Claude (via LLMProvider)
- **Memory Storage**: Qdrant, Neo4j, Letta-core, Redis, AgentFile
- **Project Management**: Plane (via TaskPayload.externalId)
- **33GOD Ecosystem**: Bloodbank (events), Candybar (decisions), Holocene (checkpoints)

## Relationships

### Class Hierarchy (Object-Oriented)

```mermaid
---
title: Flume Agent Class Hierarchy
---
classDiagram
    namespace FlumeCore {
        class Employee {
            <<interface>>
            +id string
            +name string
            +role string
            +state AgentState
            +teamId string
            +skills string[]
            +salary number
            +reportStatus() EmployeeStatus
        }

        class Contributor {
            <<interface>>
            +canHandle(task) boolean
            +execute(task) WorkResult
        }

        class Delegator {
            <<interface>>
            +subordinates Employee[]
            +recruit(employee) void
            +release(employeeId) void
            +delegate(task) WorkResult
        }

        class Manager {
            <<interface>>
        }

        class Director {
            <<interface>>
        }

        class SelectionStrategy {
            <<interface>>
            +name string
            +select(task, candidates) Employee
        }
    }

    namespace YiAdapter {
        class BaseContributor {
            <<abstract>>
            #_state AgentState
            #_currentTaskId string
            #_memory OnboardingPacket
            +transitionTo(newState, trigger) void
            +execute(task) WorkResult
            +injectMemory(memory) void
            #doWork(task)* unknown
        }

        class BaseDirector {
            <<abstract>>
            #_subordinates Employee[]
            #selectionStrategy SelectionStrategy
            +recruit(employee) void
            +release(employeeId) void
            +delegate(task) WorkResult
            #applyStrategicContext(task) TaskPayload
            #handleNoCandidate(task) WorkResult
        }

        class FirstMatchSelection {
            +name "first-match"
            +select(task, candidates) Employee
        }

        class SkillMatchSelection {
            +name "skill-match"
            -config SkillMatchConfig
            +select(task, candidates) Employee
            +scoreAllCandidates(task, candidates) SkillMatchScore[]
            -extractKeywords(objective) string[]
        }

        class LLMDrivenSelection {
            +name "llm-driven"
            -llmProvider LLMProvider
            +select(task, candidates) Employee
            -buildSelectionPrompt(task, candidates) string
        }

        class YiMemoryStrategy {
            <<interface>>
            +name string
            +fetchContext(knowledgeBaseId) MemoryContext
            +syncContext(knowledgeBaseId, context) void
            +search(knowledgeBaseId, query, topK) MemorySearchResult[]
            +getActiveShard(agentId) MemoryShard
            +switchShard(agentId, shardId) void
        }
    }

    namespace YiEcho {
        class EchoContributor {
            #doWork(task) string
        }

        class EchoDirector {
            #applyStrategicContext(task) TaskPayload
        }

        class EchoMemory {
            -contexts Map
            -shards Map
            -activeShards Map
            +fetchContext(knowledgeBaseId) MemoryContext
            +createShard(agentId, type) MemoryShard
        }

        class EchoFactory {
            +name "echo-factory"
            +createAgent(skills, role) Employee
            +canCreate(skills) boolean
        }
    }

    Employee <|-- Contributor : extends
    Employee <|-- Delegator : extends
    Contributor <|-- Manager : extends
    Delegator <|-- Manager : extends
    Employee <|-- Director : extends
    Delegator <|-- Director : extends

    Contributor <|.. BaseContributor : implements
    Director <|.. BaseDirector : implements

    BaseContributor <|-- EchoContributor : extends
    BaseDirector <|-- EchoDirector : extends

    SelectionStrategy <|.. FirstMatchSelection : implements
    SelectionStrategy <|.. SkillMatchSelection : implements
    SelectionStrategy <|.. LLMDrivenSelection : implements

    YiMemoryStrategy <|.. EchoMemory : implements

    BaseDirector --> SelectionStrategy : uses
    LLMDrivenSelection --> LLMProvider : uses
    BaseContributor --> OnboardingPacket : stores
    BaseDirector --> OnboardingPacket : stores
```

### Task Delegation Flow (Functional)

```mermaid
---
title: Task Delegation Flow
---
flowchart TB
    subgraph TaskInput[Task Creation]
        A[Create TaskPayload]
        A --> B{Task Type}
    end

    subgraph DirectorLayer[Director Layer]
        B -->|Strategic| C[Director.delegate]
        C --> D[applyStrategicContext]
        D --> E[SelectionStrategy.select]
        E --> F{Found Candidate?}
        F -->|Yes| G{Candidate Type}
        F -->|No| H[handleNoCandidate]
    end

    subgraph ManagerLayer[Manager Layer]
        G -->|Manager| I[Manager.delegate]
        I --> J[SkillMatchSelection]
        J --> K{Has Subordinate?}
        K -->|Yes| L[Delegate to Contributor]
        K -->|No| M[Manager.execute]
    end

    subgraph ContributorLayer[Contributor Layer]
        G -->|Contributor| N[Contributor.execute]
        L --> N
        M --> N
        N --> O[canHandle check]
        O -->|Yes| P[transitionTo working]
        P --> Q[doWork]
        Q --> R[transitionTo idle]
        R --> S[Return WorkResult]
    end

    subgraph ResultFlow[Result Propagation]
        S --> T[Add delegationDepth]
        T --> U[Add metrics]
        U --> V[Return to Director]
        H --> W[Return error result]
        W --> V
    end

    subgraph Events[Event Publishing]
        P -.->|state change| X[Bloodbank Event]
        R -.->|state change| X
        S -.->|completion| X
        X --> Y[RabbitMQ task.lifecycle.*]
    end

    style DirectorLayer fill:#e1f5ff
    style ManagerLayer fill:#fff5e1
    style ContributorLayer fill:#e1ffe1
    style Events fill:#ffe1e1
```

### State Machine (Agent Lifecycle)

```mermaid
---
title: Agent State Machine
---
stateDiagram-v2
    [*] --> initializing: New agent created
    initializing --> onboarding: Memory injection
    initializing --> errored: Initialization failed
    initializing --> terminated: Creation aborted

    onboarding --> idle: verifyReadiness
    onboarding --> errored: Onboarding failed
    onboarding --> terminated: Onboarding aborted

    idle --> working: execute(task)
    idle --> delegating: delegate(task)
    idle --> blocked: External dependency
    idle --> terminated: Agent shutdown

    working --> idle: Task completed
    working --> blocked: Waiting on resource
    working --> reviewing: Need review
    working --> errored: Execution failed
    working --> terminated: Force shutdown

    delegating --> idle: Subordinate completed
    delegating --> blocked: Subordinate blocked
    delegating --> errored: Delegation failed
    delegating --> terminated: Force shutdown

    blocked --> idle: Unblocked
    blocked --> working: Resume work
    blocked --> delegating: Resume delegation
    blocked --> errored: Unblock failed
    blocked --> terminated: Force shutdown

    reviewing --> idle: Review passed
    reviewing --> errored: Review failed
    reviewing --> terminated: Force shutdown

    errored --> idle: Recovery successful
    errored --> terminated: Unrecoverable

    terminated --> [*]: Agent destroyed
```

### Memory Architecture (Module Structure)

```mermaid
---
title: Memory Strategy Architecture
---
classDiagram
    namespace MemoryAbstraction {
        class YiMemoryStrategy {
            <<interface>>
            +fetchContext(knowledgeBaseId) MemoryContext
            +syncContext(knowledgeBaseId, context) void
            +search(knowledgeBaseId, query, topK) MemorySearchResult[]
            +getActiveShard(agentId) MemoryShard
            +switchShard(agentId, shardId) void
        }

        class MemoryShard {
            <<data>>
            +id string
            +type string
            +pointer string
            +createdAt string
            +isActive boolean
            +metadata Record
        }

        class MemoryContext {
            <<data>>
            +core string
            +conversations ConversationEntry[]
            +knowledge Record
            +skills string[]
            +protocols string[]
        }

        class TeamContext {
            <<data>>
            +teamId string
            +missionStatement string
            +sharedKnowledgeBaseId string
            +accessLevel string
            +projectContext ProjectContext
            +techContext TechContext
            +companyContext CompanyContext
        }
    }

    namespace MemoryImplementations {
        class EchoMemory {
            +name "echo-memory"
            -contexts Map~string, MemoryContext~
            -shards Map~string, MemoryShard[]~
            -activeShards Map~string, string~
            +fetchContext(knowledgeBaseId) MemoryContext
            +createShard(agentId, type) MemoryShard
        }

        class QdrantMemory {
            <<external>>
            +name "qdrant"
            -client QdrantClient
            +fetchContext(knowledgeBaseId) MemoryContext
            +search(knowledgeBaseId, query, topK) MemorySearchResult[]
        }

        class LettaCoreMemory {
            <<external>>
            +name "letta-core"
            -agent LettaAgent
            +fetchContext(knowledgeBaseId) MemoryContext
        }
    }

    namespace Agents {
        class BaseContributor {
            #_memory OnboardingPacket
            +injectMemory(memory) void
            +verifyReadiness() boolean
        }

        class BaseDirector {
            #_memory OnboardingPacket
            +injectMemory(memory) void
        }
    }

    YiMemoryStrategy <|.. EchoMemory : implements
    YiMemoryStrategy <|.. QdrantMemory : implements
    YiMemoryStrategy <|.. LettaCoreMemory : implements

    YiMemoryStrategy --> MemoryShard : manages
    YiMemoryStrategy --> MemoryContext : returns

    BaseContributor --> TeamContext : receives
    BaseDirector --> TeamContext : receives

    TeamContext --> MemoryContext : provides
```

### Python Task Monitor (Data Pipeline)

```mermaid
---
title: Task Monitoring Pipeline
---
flowchart LR
    subgraph Producers[Event Producers]
        A[Agent State Change]
        B[Task Assignment]
        C[Heartbeat Timer]
        D[Task Completion]
    end

    subgraph RabbitMQ[Message Bus]
        A --> E[task.lifecycle.started]
        B --> F[task.lifecycle.assigned]
        C --> G[task.lifecycle.heartbeat]
        D --> H[task.lifecycle.completed]
        E --> I[amq.topic Exchange]
        F --> I
        G --> I
        H --> I
        I --> J[task_monitor_queue]
    end

    subgraph Consumer[TaskEventConsumer]
        J --> K[_process_message]
        K --> L[_extract_task_id]
        L --> M[_map_event_type]
        M --> N[Create TaskEvent]
        N --> O[Call event_handler]
    end

    subgraph StateManager[TaskStateManager]
        O --> P[handle_event]
        P --> Q{Task Exists?}
        Q -->|No| R[Create TaskState]
        Q -->|Yes| S[Get TaskState]
        R --> T[transition_to]
        S --> T
        T --> U[Update metrics]
        U --> V[Add to events]
        V --> W[In-memory storage]
    end

    subgraph Persistence[Background Tasks]
        W -.->|60s| X[_persistence_loop]
        X --> Y[_save_state JSON]
        W -.->|3600s| Z[_cleanup_loop]
        Z --> AA[Remove old tasks]
    end

    subgraph API[REST API / WebSocket]
        W --> AB[get_task]
        W --> AC[get_all_tasks]
        W --> AD[get_metrics]
        W --> AE[get_stale_tasks]
        AE --> AF[Mark as stale]
        AF --> AG[Publish alert]
    end

    style RabbitMQ fill:#fff5e1
    style StateManager fill:#e1f5ff
    style Persistence fill:#e1ffe1
```

## Code Examples

### Example 1: Creating and Delegating a Task

```typescript
// File: packages/yi-echo/src/walking-skeleton.ts (conceptual)

import { v4 as uuid } from 'uuid';
import { TaskPayload } from '@flume/core';
import { createEchoTeam } from './factory/echo-factory.js';

// Create a hierarchical team
const { director, manager, contributors } = createEchoTeam('demo-team');

// Create a task
const task: TaskPayload = {
  id: uuid(),
  correlationId: uuid(),
  objective: 'Build authentication service',
  context: {
    requirements: 'JWT-based authentication with refresh tokens',
    frameworks: ['Express', 'TypeScript'],
  },
  priority: 10,
  tags: ['backend', 'security', 'typescript'],
  createdAt: new Date().toISOString(),
  timeout: 300000, // 5 minutes
};

// Delegate from top (Director → Manager → Contributor)
const result = await director.delegate(task);

console.log(`Task ${task.id} completed with status: ${result.status}`);
console.log(`Delegation depth: ${result.metrics.delegationDepth}`);
console.log(`Duration: ${result.metrics.durationMs}ms`);
console.log(`Delegated through: Director → Manager → ${result.delegatedTo}`);
```

**Execution Flow:**
1. Director receives task
2. Director applies strategic context (adds priority, executive sponsorship)
3. Director's SelectionStrategy (FirstMatch) scans subordinates
4. Manager is selected (matches skills, state is idle)
5. Manager delegates to subordinates using SkillMatchSelection
6. Contributor with 'typescript' + 'backend' skills scores highest
7. Contributor executes task via `doWork()`
8. Result propagates back: Contributor → Manager → Director
9. Each level adds delegation depth, aggregates metrics

### Example 2: Custom Selection Strategy

```typescript
// File: custom-selection-strategy.ts

import {
  SelectionStrategy,
  TaskPayload,
  Employee,
  Contributor
} from '@flume/core';

/**
 * Load-aware selection strategy that considers current workload.
 * Selects the idle contributor with the lowest salary (junior first).
 */
export class LoadAwareSelection implements SelectionStrategy {
  readonly name = 'load-aware';

  async select(
    task: TaskPayload,
    candidates: Employee[]
  ): Promise<Employee | null> {
    // Filter to idle contributors who can handle the task
    const available: Contributor[] = [];

    for (const candidate of candidates) {
      if (candidate.state !== 'idle') continue;
      if (!('canHandle' in candidate)) continue;

      const contributor = candidate as Contributor;
      const canHandle = await contributor.canHandle(task);

      if (canHandle) {
        available.push(contributor);
      }
    }

    if (available.length === 0) {
      console.log(`[LoadAware] No available candidates for "${task.objective}"`);
      return null;
    }

    // Sort by salary (ascending) - junior developers first
    available.sort((a, b) => a.salary - b.salary);

    const selected = available[0];
    console.log(
      `[LoadAware] Selected ${selected.name} (salary: $${selected.salary}) ` +
      `for "${task.objective}"`
    );

    return selected;
  }
}

// Usage in Director
import { BaseDirector } from '@yi/adapter';

class CustomDirector extends BaseDirector {
  constructor(config: any) {
    super(config, new LoadAwareSelection());
  }
}
```

### Example 3: Memory-Aware Agent with Context Injection

```typescript
// File: packages/yi-adapter/src/hr/onboarding-specialist.ts (conceptual)

import { BaseContributor, TeamContext, YiMemoryStrategy } from '@yi/adapter';
import { TaskPayload, WorkResult } from '@flume/core';

/**
 * Onboarding packet injected during agent initialization.
 */
export interface OnboardingPacket {
  mission: string;
  teamContext: TeamContext;
  knowledgeBaseId: string;
  contextSummary: string;
}

/**
 * Agent that uses memory strategy for context-aware execution.
 */
export class MemoryAwareContributor extends BaseContributor {
  constructor(
    config: any,
    private memoryStrategy: YiMemoryStrategy
  ) {
    super(config);
  }

  protected async doWork(task: TaskPayload): Promise<string> {
    // Fetch relevant context from memory
    const context = await this.memoryStrategy.fetchContext(
      this._memory?.knowledgeBaseId ?? 'default'
    );

    // Search for relevant past experiences
    const relevantMemories = await this.memoryStrategy.search(
      this._memory?.knowledgeBaseId ?? 'default',
      task.objective,
      5 // top 5 results
    );

    console.log(`[${this.name}] Retrieved context: ${context.core}`);
    console.log(`[${this.name}] Found ${relevantMemories.length} relevant memories`);

    // Use context to inform task execution
    const insights = relevantMemories
      .map(m => `- ${m.content} (score: ${m.score})`)
      .join('\n');

    const result = `
Task: ${task.objective}
Context: ${context.core}
Relevant past work:
${insights}

Execution complete with context-aware approach.
    `.trim();

    // Sync new learnings back to memory
    await this.memoryStrategy.syncContext(
      this._memory?.knowledgeBaseId ?? 'default',
      {
        ...context,
        knowledge: {
          ...context.knowledge,
          [`task-${task.id}`]: {
            objective: task.objective,
            result,
            timestamp: new Date().toISOString(),
          },
        },
      }
    );

    return result;
  }
}

// Onboarding flow
async function onboardAgent(
  agent: MemoryAwareContributor,
  teamContext: TeamContext
): Promise<void> {
  // Inject memory during onboarding
  const packet: OnboardingPacket = {
    mission: teamContext.missionStatement,
    teamContext,
    knowledgeBaseId: teamContext.sharedKnowledgeBaseId,
    contextSummary: 'You are a backend developer on the auth team',
  };

  await agent.injectMemory(packet);

  // Verify readiness
  const ready = await agent.verifyReadiness();

  if (ready) {
    console.log(`[HR] ${agent.name} onboarding complete - ready for work`);
  } else {
    console.error(`[HR] ${agent.name} onboarding failed`);
  }
}
```

### Example 4: Python Task Monitor Integration

```python
# File: flume/feat-task/task-monitor/main.py (simplified)

import asyncio
from consumer import TaskEventConsumer
from state_manager import TaskStateManager
from models import TaskEvent

async def main():
    # Initialize state manager
    state_manager = TaskStateManager(
        persistence_path=Path("./data/tasks.json"),
        persistence_interval=60,
        stale_threshold=300,  # 5 minutes
        retention_hours=24,
    )
    await state_manager.initialize()

    # Initialize consumer
    consumer = TaskEventConsumer(
        rabbitmq_url="amqp://guest:guest@localhost:5672/",
        exchange_name="amq.topic",
        queue_name="task_monitor_queue",
        routing_key_pattern="task.lifecycle.*",
    )

    # Register event handler
    async def handle_event(task_id: str, event: TaskEvent) -> None:
        await state_manager.handle_event(task_id, event)

        # Log state transitions
        task = await state_manager.get_task(task_id)
        if task:
            print(f"Task {task_id}: {task.status} (agent: {task.agent_id})")

    consumer.set_event_handler(handle_event)

    # Connect and start consuming
    await consumer.connect()
    print("Task monitor started. Consuming events...")

    try:
        await consumer.start_consuming()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await consumer.stop()
        await state_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

**Event Flow:**
1. Agent transitions state (e.g., `idle → working`)
2. Agent publishes RabbitMQ message to `task.lifecycle.started`
3. TaskEventConsumer receives message via queue binding
4. Consumer extracts task_id, maps event type to `EventType.STARTED`
5. Consumer calls `handle_event(task_id, event)`
6. TaskStateManager updates or creates TaskState
7. State transitions from `PENDING → STARTED`, metrics updated
8. Background tasks periodically save to JSON, cleanup old tasks
9. REST API/WebSocket serves real-time task status

### Example 5: Hive Mind Worker Specialization

```json
// File: .hive-mind/config/workers.json (usage in agent factory)

{
  "architect": {
    "name": "System Architect",
    "capabilities": ["system-design", "architecture-patterns", "scalability-planning"],
    "complexity": 0.9,
    "autonomy": 0.8,
    "collaboration": 0.7
  },
  "implementer": {
    "name": "Implementation Specialist",
    "capabilities": ["coding", "debugging", "integration"],
    "complexity": 0.8,
    "autonomy": 0.7,
    "collaboration": 0.8
  }
}
```

```typescript
// Usage in agent factory
import workersConfig from './.hive-mind/config/workers.json';

class HiveMindFactory implements AgentFactory {
  async createAgent(skills: string[], role?: string): Promise<Employee> {
    // Match skills to worker archetype
    for (const [archetypeKey, archetype] of Object.entries(workersConfig)) {
      const match = archetype.capabilities.some(cap =>
        skills.includes(cap)
      );

      if (match) {
        return new SpecializedContributor({
          name: archetype.name,
          role: role ?? archetype.name,
          skills: archetype.capabilities,
          complexity: archetype.complexity,
          autonomy: archetype.autonomy,
        });
      }
    }

    // Fallback to generic contributor
    return new EchoContributor({ skills, role });
  }
}
```

## Agent Communication Patterns

### Pattern 1: Hierarchical Delegation Chain
- **Flow**: Director → Manager → Contributor
- **Decision Points**: SelectionStrategy at each level
- **Context Enrichment**: Each level adds strategic/tactical context
- **Result Aggregation**: Metrics bubble up, delegation depth tracked

### Pattern 2: Skill-Based Routing
- **Mechanism**: SkillMatchSelection scores candidates
- **Scoring**: Tag matches (×3) + Keyword matches (×1)
- **Filtering**: canHandle() validation, state checks
- **Use Case**: Optimal agent selection for specialized tasks

### Pattern 3: Memory-Driven Execution
- **Context Fetching**: YiMemoryStrategy.fetchContext()
- **Search**: Semantic search for relevant past work
- **Learning**: Sync new knowledge back to memory
- **Checkpointing**: MemoryShard switching for rollback

### Pattern 4: Event-Driven Monitoring
- **Publishing**: Agents emit state changes to RabbitMQ
- **Consumption**: TaskEventConsumer subscribes to patterns
- **State Management**: TaskStateManager maintains central state
- **Alerting**: Stale task detection, failure notifications

## BMAD Workflow Integration

### BMAD (Bloodbank Message-based Agent Delegation) Mapping:
1. **Brief** → TaskPayload with objective and context
2. **Mission** → TeamContext.missionStatement injected during onboarding
3. **Artifact** → WorkResult.artifacts (decisions, checkpoints, briefs)
4. **Decision** → SelectionStrategy.select() and Director.applyStrategicContext()

### Event Routing (RabbitMQ):
- **Exchange**: `amq.topic` (topic exchange)
- **Routing Keys**:
  - `task.lifecycle.assigned` → Task assigned to agent
  - `task.lifecycle.started` → Agent begins execution
  - `task.lifecycle.in_progress` → Heartbeat / progress update
  - `task.lifecycle.completed` → Task finished successfully
  - `task.lifecycle.failed` → Task failed with error
  - `task.alert.stale` → Task stale (no heartbeat)
- **Queues**: Consumers bind with patterns (e.g., `task.lifecycle.*`)

## Notes

### Design Philosophy
The agent orchestration system follows a **corporate anthropomorphization** approach where:
- **Employees** are autonomous agents with roles, skills, and salaries
- **Contributors** (ICs) execute tasks directly
- **Managers** balance hands-on work with delegation
- **Directors** (VPs) only orchestrate, never execute
- **HR** handles onboarding, context injection, and agent lifecycle

### State Machine Guarantees
- **Validated Transitions**: All state changes checked against `VALID_TRANSITIONS`
- **Audit Trail**: Every transition logged with trigger, timestamp, task ID
- **Recovery**: Error states allow transition back to idle
- **Terminal States**: Completed/failed/terminated prevent further transitions

### Selection Strategy Trade-offs
| Strategy | Speed | Accuracy | Use Case |
|----------|-------|----------|----------|
| FirstMatch | Fast | Low | MVP, deterministic testing |
| RoundRobin | Fast | Medium | Load balancing |
| SkillMatch | Medium | High | Optimal skill utilization |
| LLMDriven | Slow | Highest | Complex task-agent matching |

### Memory Strategy Support
- **Qdrant**: Vector similarity search, high-dimensional context
- **Letta-core**: Persistent LLM memory, conversation continuity
- **Neo4j**: Graph-based knowledge, relationship tracking
- **Redis**: Fast key-value cache, session storage
- **AgentFile**: Local file-based persistence
- **Custom**: Pluggable interface for any backend

### Scalability Considerations
1. **Horizontal Scaling**: Agents are stateless (state in TaskStateManager)
2. **Task Distribution**: RabbitMQ topic exchange enables multi-consumer patterns
3. **Memory Sharding**: Agents can switch between memory checkpoints
4. **Delegation Depth**: Tracked to prevent infinite recursion
5. **Stale Detection**: Heartbeat mechanism prevents zombie tasks

### Future Extensions
- **Dynamic Hiring**: RecruitmentRequest → AgentFactory → Onboard → Recruit
- **Cross-Team Collaboration**: TeamContext sharing via MCP servers
- **Swarm Intelligence**: Hive mind queen/worker coordination
- **Adaptive Selection**: Neural network-based candidate scoring
- **Temporal Workflows**: Long-running sagas with checkpoints

### Integration with 33GOD Ecosystem
- **Bloodbank**: Event bus for agent coordination
- **Candybar**: Decision artifact storage
- **Holocene**: Checkpoint/rollback via memory shards
- **Plane**: External task synchronization (TaskPayload.externalId)
- **iMi**: Hive mind configuration for swarm behaviors
- **Perth**: (Not analyzed in this document - separate component)

---

**Last Updated**: 2026-01-29
**Agent Orchestration Version**: Flume v1.0.0, Yi Adapter v1.0.0
**Task Monitor Version**: Python 3.11+, Pydantic v2.x, aio_pika v9.x
