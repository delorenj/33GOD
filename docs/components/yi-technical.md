# Yi - Technical Implementation Guide

## Overview

Yi is the opinionated agent adapter layer that enforces 33GOD conventions on top of the Flume protocol. It serves as the "bureaucracy" and "HR department" that wraps specific AI SDKs (Letta, Agno, Smolagents) into compliant Manager and Contributor nodes, providing memory synchronization, lifecycle management, and recruitment/onboarding services.

## Implementation Details

**Language**: TypeScript/Node.js
**Framework**: Flume protocol implementation
**Memory**: YiMemoryStrategy (shared context management)
**Integration**: Agent Forge for recruitment

### Key Technologies

- **Flume Interfaces**: Manager, Contributor, TaskPayload, WorkResult
- **Letta SDK**: Long-term memory management
- **Redis**: Memory shard synchronization
- **Bloodbank**: Event emission for state changes

## Architecture & Design Patterns

### YiManager (Abstract Manager Implementation)

```typescript
import { Manager, Contributor, TaskPayload, WorkResult } from '@33god/flume';

export abstract class YiManager implements Manager {
    role: 'manager' = 'manager';
    contributors: Contributor[] = [];
    protected memory: YiMemoryStrategy;

    constructor(memory: YiMemoryStrategy) {
        this.memory = memory;
    }

    async delegate(task: TaskPayload): Promise<Contributor> {
        // Delegation strategies
        const strategies = {
            'round-robin': this.roundRobinSelection.bind(this),
            'capability-match': this.capabilityMatchSelection.bind(this),
            'llm-driven': this.llmDrivenSelection.bind(this)
        };

        const strategy = this.getDelegationStrategy();
        return strategies[strategy](task);
    }

    private roundRobinSelection(task: TaskPayload): Contributor {
        // Rotate through contributors
        const index = task.id.charCodeAt(0) % this.contributors.length;
        return this.contributors[index];
    }

    private capabilityMatchSelection(task: TaskPayload): Contributor {
        // Match task requirements to contributor capabilities
        return this.contributors.find(c =>
            task.requirements.every(req =>
                c.capabilities.includes(req)
            )
        ) || this.contributors[0];
    }

    private async llmDrivenSelection(task: TaskPayload): Promise<Contributor> {
        // Ask LLM to select best contributor
        const prompt = `
        Task: ${task.description}
        Available contributors: ${this.contributors.map(c => c.metadata.name).join(', ')}

        Select the best contributor for this task.
        `;

        const response = await this.brain.complete(prompt);
        const selectedName = this.parseContributorName(response);

        return this.contributors.find(c => c.metadata.name === selectedName)!;
    }

    protected abstract getDelegationStrategy(): DelegationStrategy['type'];
}
```

### YiMemoryStrategy (Shared Context Management)

```typescript
export class YiMemoryStrategy {
    private redis: Redis;
    private teamId: string;

    constructor(teamId: string) {
        this.redis = new Redis();
        this.teamId = teamId;
    }

    async storeContext(key: string, value: any): Promise<void> {
        await this.redis.hset(
            `team:${this.teamId}:context`,
            key,
            JSON.stringify(value)
        );
    }

    async getContext(key: string): Promise<any> {
        const value = await this.redis.hget(
            `team:${this.teamId}:context`,
            key
        );
        return value ? JSON.parse(value) : null;
    }

    async synchronizeMemoryShards(
        agentId: string,
        updates: Record<string, any>
    ): Promise<void> {
        // Update agent's memory shard
        await this.redis.hset(
            `team:${this.teamId}:agent:${agentId}:memory`,
            updates
        );

        // Broadcast update to team members
        await this.redis.publish(
            `team:${this.teamId}:memory-updates`,
            JSON.stringify({ agentId, updates })
        );
    }
}
```

### OnboardingSpecialist (Context Injection Service)

```typescript
export class OnboardingSpecialist {
    constructor(private memory: YiMemoryStrategy) {}

    async onboardAgent(
        agent: Employee,
        context: TeamContext
    ): Promise<void> {
        // Inject team context into agent
        const contextSummary = this.summarizeContext(context);

        await agent.onboard(context);

        // Store in memory
        await this.memory.storeContext(
            `agent:${agent.id}:onboarding`,
            {
                completedAt: new Date(),
                contextReceived: contextSummary
            }
        );

        // Emit event
        await this.emitEvent('yi.agent.onboarded', {
            agentId: agent.id,
            teamId: context.teamId
        });
    }

    private summarizeContext(context: TeamContext): string {
        return `
        Mission: ${context.mission}
        Team Size: ${context.roles.size}
        Conventions: ${context.sharedKnowledge.conventions.join(', ')}
        `;
    }
}
```

### Bloodbank Integration (Automatic Event Emission)

```typescript
export class YiEventEmitter {
    private bloodbank: BloodbankPublisher;

    async emitStateChange(
        agent: Employee,
        fromState: EmployeeStatus,
        toState: EmployeeStatus
    ): Promise<void> {
        await this.bloodbank.publish(
            'yi.agent.state.changed',
            {
                event_type: 'yi.agent.state.changed',
                source: 'yi',
                data: {
                    agent_id: agent.id,
                    from_state: fromState,
                    to_state: toState,
                    timestamp: new Date().toISOString()
                }
            }
        );
    }

    async emitWorkCompleted(
        agent: Employee,
        result: WorkResult
    ): Promise<void> {
        await this.bloodbank.publish(
            'yi.work.completed',
            {
                event_type: 'yi.work.completed',
                source: 'yi',
                data: {
                    agent_id: agent.id,
                    task_id: result.taskId,
                    status: result.status,
                    artifacts: result.artifacts?.map(a => a.path)
                }
            }
        );
    }
}
```

## Integration Points

### AgentForge Integration

```typescript
// Yi handles onboarding for agents created by AgentForge
import { AgentForge } from '@33god/agent-forge';

async function recruitAndOnboardTeam(goal: string) {
    // 1. AgentForge creates team
    const forge = new AgentForge();
    const team = await forge.createTeam(goal);

    // 2. Yi onboards each agent
    const onboarding = new OnboardingSpecialist(memory);

    for (const agent of team.members) {
        await onboarding.onboardAgent(agent, team.context);
    }

    return team;
}
```

### Letta SDK Wrapper

```typescript
import { LettaClient } from 'letta-sdk';

export class YiLettaContributor implements Contributor {
    role: 'contributor' = 'contributor';
    private brain: LettaClient;

    constructor(agentId: string) {
        this.brain = new LettaClient({ agentId });
    }

    async execute(task: TaskPayload): Promise<WorkResult> {
        // Use Letta for long-term memory
        const messages = await this.brain.chat(task.description);

        return {
            taskId: task.id,
            status: 'completed',
            output: messages[messages.length - 1].content,
            metadata: {
                startedAt: new Date(),
                completedAt: new Date()
            }
        };
    }
}
```

## Code Examples

### Enforcing Conventions

```typescript
export class ConventionEnforcer {
    private conventions: string[];

    constructor(conventions: string[]) {
        this.conventions = conventions;
    }

    validateWorkResult(result: WorkResult): ValidationResult {
        const violations: string[] = [];

        // Check code style
        if (this.conventions.includes('Use TypeScript')) {
            const hasTypeScript = result.artifacts?.some(a =>
                a.path.endsWith('.ts')
            );
            if (!hasTypeScript) {
                violations.push('Missing TypeScript files');
            }
        }

        // Check test coverage
        if (this.conventions.includes('Test-first development')) {
            const hasTests = result.artifacts?.some(a =>
                a.type === 'test'
            );
            if (!hasTests) {
                violations.push('Missing test artifacts');
            }
        }

        return {
            valid: violations.length === 0,
            violations
        };
    }
}
```

## Related Components

- **Flume**: Protocol that Yi implements
- **AgentForge**: Recruitment service for Yi agents
- **Bloodbank**: Event bus for Yi state changes

---

**Quick Reference**:
- GitHub: `33GOD/yi`
- Package: `@33god/yi`
- Role: Adapter layer (Flume implementation)
