# Flume - Technical Implementation Guide

## Overview

Flume is the implementation-agnostic protocol defining the structural hierarchy, communication interfaces, and role definitions for the 33GOD ecosystem. It provides pure TypeScript/Node.js interfaces that act as the standard for any agent to participate, using strict anthropomorphic roles (Employees, Managers, Contributors) rather than traditional AI terminology.

## Implementation Details

**Language**: TypeScript/Node.js
**Pattern**: Protocol/Interface definitions (no implementation logic)
**Paradigm**: Corporate hierarchy metaphor
**Integration**: Framework-agnostic (works with Letta, Agno, Smolagents)

### Key Concepts

- **Manager**: Orchestrator/Delegator role (routes work to contributors)
- **Contributor**: Individual contributor/leaf node (executes tasks)
- **TaskPayload**: The assignment (input specification)
- **WorkResult**: The deliverable (output specification)
- **State Machine**: Lifecycle states (initializing, onboarding, working, blocked)

## Architecture & Design Patterns

### Core Interfaces

```typescript
// flume/src/interfaces/Employee.ts
export interface Employee {
    id: string;
    role: EmployeeRole;
    status: EmployeeStatus;
    metadata: EmployeeMetadata;

    // Lifecycle methods
    initialize(): Promise<void>;
    onboard(context: TeamContext): Promise<void>;
    work(task: TaskPayload): Promise<WorkResult>;
    reportStatus(): EmployeeStatus;
}

export type EmployeeRole = 'manager' | 'contributor';

export enum EmployeeStatus {
    INITIALIZING = 'initializing',
    ONBOARDING = 'onboarding',
    IDLE = 'idle',
    WORKING = 'working',
    BLOCKED = 'blocked',
    FAILED = 'failed'
}

export interface EmployeeMetadata {
    name: string;
    expertise: string[];
    teamId: string;
    hiredAt: Date;
}
```

### Task & Work Interfaces

```typescript
// flume/src/interfaces/Work.ts
export interface TaskPayload {
    id: string;
    description: string;
    requirements: string[];
    constraints?: string[];
    context?: Record<string, any>;
    priority: 'low' | 'medium' | 'high' | 'critical';
    deadline?: Date;
}

export interface WorkResult {
    taskId: string;
    status: 'completed' | 'partial' | 'failed' | 'blocked';
    output: any;
    artifacts?: Artifact[];
    blockers?: Blocker[];
    metadata: {
        startedAt: Date;
        completedAt: Date;
        tokensUsed?: number;
        cost?: number;
    };
}

export interface Artifact {
    type: 'code' | 'documentation' | 'test' | 'config';
    path: string;
    content: string;
}

export interface Blocker {
    reason: string;
    severity: 'low' | 'medium' | 'high';
    requiresHumanIntervention: boolean;
}
```

### Manager Interface

```typescript
// flume/src/interfaces/Manager.ts
export interface Manager extends Employee {
    role: 'manager';
    contributors: Contributor[];

    // Delegation methods
    delegate(task: TaskPayload): Promise<Contributor>;
    monitorProgress(): ProgressReport;
    handleBlocker(blocker: Blocker): Promise<Resolution>;
    consolidateResults(results: WorkResult[]): WorkResult;
}

export interface DelegationStrategy {
    type: 'round-robin' | 'capability-match' | 'load-balance' | 'llm-driven';
    selectContributor(
        task: TaskPayload,
        available: Contributor[]
    ): Contributor;
}

export interface ProgressReport {
    tasksInProgress: number;
    tasksCompleted: number;
    tasksFailed: number;
    blockedContributors: number;
}
```

### Contributor Interface

```typescript
// flume/src/interfaces/Contributor.ts
export interface Contributor extends Employee {
    role: 'contributor';
    capabilities: string[];

    // Execution methods
    execute(task: TaskPayload): Promise<WorkResult>;
    requestHelp(issue: string): Promise<Assistance>;
    reportProgress(update: ProgressUpdate): void;
}

export interface ProgressUpdate {
    taskId: string;
    percentComplete: number;
    currentStep: string;
    estimatedCompletion?: Date;
}
```

### Team Context

```typescript
// flume/src/interfaces/Team.ts
export interface TeamContext {
    teamId: string;
    mission: string;
    roles: Map<string, Employee>;
    sharedKnowledge: KnowledgeBase;
    communicationProtocol: Protocol;
}

export interface KnowledgeBase {
    facts: Record<string, any>;
    conventions: string[];
    bestPractices: string[];
    recentDecisions: Decision[];
}

export interface Decision {
    id: string;
    topic: string;
    outcome: string;
    rationale: string;
    decidedAt: Date;
    decidedBy: string;
}
```

## Configuration

Flume itself has no configuration - it's pure interface definitions. Configuration exists in adapter layers (Yi).

## Integration Points

### Yi Adapter Integration

```typescript
// Yi implements Flume interfaces
import { Manager, Contributor, TaskPayload, WorkResult } from '@33god/flume';
import { YiMemoryStrategy } from '@33god/yi';
import { LettaClient } from 'letta-sdk';

class EngineeringManager implements Manager {
    role: 'manager' = 'manager';
    contributors: Contributor[] = [];
    private brain: LettaClient;

    constructor(private memory: YiMemoryStrategy) {
        this.brain = new LettaClient();
    }

    async delegate(task: TaskPayload): Promise<Contributor> {
        // Yi provides delegation logic
        const strategy: DelegationStrategy = {
            type: 'capability-match',
            selectContributor: (task, available) => {
                // Match task requirements to contributor capabilities
                return available.find(c =>
                    task.requirements.every(req =>
                        c.capabilities.includes(req)
                    )
                ) || available[0];  // Fallback
            }
        };

        return strategy.selectContributor(task, this.contributors);
    }

    async work(task: TaskPayload): Promise<WorkResult> {
        // Manager work is delegation
        const contributor = await this.delegate(task);
        const result = await contributor.work(task);

        // Consolidate if needed
        return result;
    }
}

class BackendDeveloper implements Contributor {
    role: 'contributor' = 'contributor';
    capabilities = ['typescript', 'node.js', 'postgresql', 'rest-api'];

    async execute(task: TaskPayload): Promise<WorkResult> {
        // Actual implementation uses Letta/Agno
        // Flume just defines the contract
        const output = await this.brain.complete(task.description);

        return {
            taskId: task.id,
            status: 'completed',
            output,
            metadata: {
                startedAt: new Date(),
                completedAt: new Date()
            }
        };
    }
}
```

### Event Integration (Bloodbank)

```typescript
// Flume defines event shapes, Yi emits them
export interface StateChangeEvent {
    employeeId: string;
    fromState: EmployeeStatus;
    toState: EmployeeStatus;
    timestamp: Date;
    reason?: string;
}

// In Yi adapter:
async function transitionState(
    employee: Employee,
    newState: EmployeeStatus
) {
    const event: StateChangeEvent = {
        employeeId: employee.id,
        fromState: employee.status,
        toState: newState,
        timestamp: new Date()
    };

    // Publish to Bloodbank
    await bloodbank.publish('yi.agent.state.changed', event);

    employee.status = newState;
}
```

## Code Examples

### Defining a Custom Employee Type

```typescript
import { Employee, TaskPayload, WorkResult } from '@33god/flume';

class QAEngineer implements Employee {
    id: string;
    role: 'contributor' = 'contributor';
    status = EmployeeStatus.INITIALIZING;
    metadata = {
        name: 'QA Engineer',
        expertise: ['testing', 'automation', 'quality-assurance'],
        teamId: 'product-team',
        hiredAt: new Date()
    };

    async initialize(): Promise<void> {
        // Setup testing framework
        this.status = EmployeeStatus.IDLE;
    }

    async onboard(context: TeamContext): Promise<void> {
        // Learn team conventions
        const testingConventions = context.sharedKnowledge.conventions
            .filter(c => c.includes('test'));

        console.log('Learned conventions:', testingConventions);
    }

    async work(task: TaskPayload): Promise<WorkResult> {
        this.status = EmployeeStatus.WORKING;

        // QA work: write tests
        const tests = await this.generateTests(task.description);

        this.status = EmployeeStatus.IDLE;

        return {
            taskId: task.id,
            status: 'completed',
            output: tests,
            artifacts: [{
                type: 'test',
                path: 'tests/feature.test.ts',
                content: tests
            }],
            metadata: {
                startedAt: new Date(),
                completedAt: new Date()
            }
        };
    }

    reportStatus(): EmployeeStatus {
        return this.status;
    }

    private async generateTests(description: string): Promise<string> {
        // Implementation via LLM or template
        return `describe('${description}', () => { /* tests */ });`;
    }
}
```

### Team Assembly

```typescript
import { Manager, Contributor, TeamContext } from '@33god/flume';

async function assembleProductTeam(): Promise<Manager> {
    const manager = new EngineeringManager(memoryStrategy);

    const contributors: Contributor[] = [
        new BackendDeveloper(),
        new FrontendDeveloper(),
        new QAEngineer(),
        new DevOpsEngineer()
    ];

    // Initialize all employees
    await manager.initialize();
    for (const contributor of contributors) {
        await contributor.initialize();
    }

    // Create team context
    const context: TeamContext = {
        teamId: 'product-team',
        mission: 'Build e-commerce platform',
        roles: new Map([
            ['manager', manager],
            ...contributors.map(c => [c.metadata.name, c])
        ]),
        sharedKnowledge: {
            facts: {},
            conventions: ['Use TypeScript', 'Test-first development'],
            bestPractices: ['Code review required', 'CI/CD mandatory'],
            recentDecisions: []
        },
        communicationProtocol: {
            updateFrequency: 'every-commit',
            reportingFormat: 'markdown'
        }
    };

    // Onboard all employees
    await manager.onboard(context);
    for (const contributor of contributors) {
        await contributor.onboard(context);
    }

    manager.contributors = contributors;

    return manager;
}
```

## Design Philosophy

### Why "Corporate Hierarchy"?

Flume uses corporate metaphors because:
1. **Universally Understood**: Everyone knows manager/employee dynamics
2. **Scalable Pattern**: Proven to handle complex organizational work
3. **Clear Responsibilities**: No ambiguity about who does what
4. **Natural Delegation**: Mimics human team structures

### Anti-Pattern: No Implementation Logic

Flume is **purely protocol**. It does NOT:
- Implement LLM inference
- Handle memory management
- Manage state persistence
- Define specific agent behaviors

Those responsibilities belong to adapter layers (Yi) or implementation frameworks (Letta, Agno).

## Related Components

- **Yi**: Opinionated adapter layer that implements Flume interfaces
- **AgentForge**: Uses Flume patterns for team structure
- **Bloodbank**: Event bus for Flume state changes

---

**Quick Reference**:
- GitHub: `33GOD/flume`
- Package: `@33god/flume`
- Role: Protocol definition (interfaces only)
