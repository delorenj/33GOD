# Holocene - Technical Implementation Guide

## Overview

Holocene is the mission control dashboard for the 33GOD Agentic Development Pipeline. Built with React + Vite, it provides a unified interface for monitoring agent activities, managing workflows, viewing event streams, and controlling the entire ecosystem from a single dashboard.

## Implementation Details

**Language**: TypeScript + React
**Build Tool**: Vite
**State Management**: Zustand + TanStack Query
**UI Components**: React + Tailwind CSS
**Real-time**: WebSocket (multiple sources)
**Package Manager**: npm/bun

### Key Technologies

- **React 18**: Modern React with concurrent features
- **Vite**: Lightning-fast build tooling
- **Zustand**: Lightweight global state
- **TanStack Query**: Server state synchronization
- **Tailwind CSS**: Utility-first styling
- **date-fns**: Date manipulation
- **clsx + tailwind-merge**: Dynamic class management

## Architecture & Design Patterns

### Dashboard Layout

```typescript
// src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';

function App() {
    return (
        <BrowserRouter>
            <DashboardLayout>
                <Routes>
                    <Route path="/" element={<OverviewPage />} />
                    <Route path="/events" element={<EventStreamPage />} />
                    <Route path="/agents" element={<AgentManagementPage />} />
                    <Route path="/workflows" element={<WorkflowsPage />} />
                    <Route path="/sessions" element={<SessionsPage />} />
                    <Route path="/metrics" element={<MetricsPage />} />
                </Routes>
            </DashboardLayout>
        </BrowserRouter>
    );
}
```

### Multi-Source State Management

```typescript
// src/store/globalStore.ts
import create from 'zustand';

interface GlobalStore {
    // Event stream
    events: Event[];
    addEvent: (event: Event) => void;

    // Agent tracking
    agents: Map<string, AgentStatus>;
    updateAgent: (id: string, status: AgentStatus) => void;

    // Workflow execution
    workflows: Workflow[];
    addWorkflow: (workflow: Workflow) => void;

    // System health
    systemHealth: SystemHealth;
    updateHealth: (health: SystemHealth) => void;
}

export const useGlobalStore = create<GlobalStore>((set) => ({
    events: [],
    addEvent: (event) => set((state) => ({
        events: [event, ...state.events].slice(0, 500)
    })),

    agents: new Map(),
    updateAgent: (id, status) => set((state) => ({
        agents: new Map(state.agents).set(id, status)
    })),

    workflows: [],
    addWorkflow: (workflow) => set((state) => ({
        workflows: [...state.workflows, workflow]
    })),

    systemHealth: { status: 'unknown' },
    updateHealth: (health) => set({ systemHealth: health })
}));
```

### Event Stream Integration

```typescript
// src/hooks/useMultiSourceEvents.ts
export function useMultiSourceEvents() {
    const addEvent = useGlobalStore(state => state.addEvent);

    useEffect(() => {
        // Bloodbank WebSocket
        const bloodbankWs = new WebSocket('ws://localhost:8000/events');
        bloodbankWs.onmessage = (e) => {
            addEvent({ ...JSON.parse(e.data), source: 'bloodbank' });
        };

        // Candystore polling (historical)
        const candystoreInterval = setInterval(async () => {
            const response = await fetch('http://localhost:8683/events?limit=50');
            const { events } = await response.json();
            events.forEach(addEvent);
        }, 30000);  // 30 seconds

        return () => {
            bloodbankWs.close();
            clearInterval(candystoreInterval);
        };
    }, [addEvent]);
}
```

### Agent Status Dashboard

```typescript
// src/components/AgentDashboard.tsx
export function AgentDashboard() {
    const agents = useGlobalStore(state => state.agents);

    // Fetch agent statuses from multiple sources
    const { data: agentForgeAgents } = useQuery({
        queryKey: ['agents', 'agentforge'],
        queryFn: () => fetch('/api/agentforge/agents').then(r => r.json()),
        refetchInterval: 10000
    });

    const { data: yiAgents } = useQuery({
        queryKey: ['agents', 'yi'],
        queryFn: () => fetch('/api/yi/agents').then(r => r.json()),
        refetchInterval: 10000
    });

    const allAgents = useMemo(() => {
        return [
            ...(agentForgeAgents || []),
            ...(yiAgents || []),
            ...Array.from(agents.values())
        ];
    }, [agentForgeAgents, yiAgents, agents]);

    return (
        <div className="grid grid-cols-3 gap-4">
            {allAgents.map(agent => (
                <AgentCard
                    key={agent.id}
                    agent={agent}
                    onClick={() => navigate(`/agents/${agent.id}`)}
                />
            ))}
        </div>
    );
}

function AgentCard({ agent }: { agent: Agent }) {
    const statusColors = {
        idle: 'bg-gray-200',
        working: 'bg-blue-500',
        blocked: 'bg-red-500',
        completed: 'bg-green-500'
    };

    return (
        <div className="p-4 border rounded-lg shadow">
            <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${statusColors[agent.status]}`} />
                <h3 className="font-semibold">{agent.name}</h3>
            </div>
            <p className="text-sm text-gray-600">{agent.currentTask || 'Idle'}</p>
            <div className="mt-2 text-xs text-gray-500">
                Last active: {formatDistance(agent.lastActive, new Date())} ago
            </div>
        </div>
    );
}
```

### Workflow Visualization

```typescript
// src/components/WorkflowGraph.tsx
import { useMemo } from 'react';

export function WorkflowGraph({ workflow }: { workflow: Workflow }) {
    // Convert workflow steps to graph nodes/edges
    const graph = useMemo(() => {
        const nodes = workflow.steps.map(step => ({
            id: step.id,
            label: step.name,
            status: step.status
        }));

        const edges = workflow.steps.flatMap(step =>
            step.dependencies.map(depId => ({
                from: depId,
                to: step.id
            }))
        );

        return { nodes, edges };
    }, [workflow]);

    return (
        <svg width="100%" height="400">
            {/* Simple DAG visualization */}
            {graph.nodes.map((node, index) => (
                <g key={node.id} transform={`translate(${index * 150}, 50)`}>
                    <circle
                        r="30"
                        fill={node.status === 'completed' ? '#22c55e' : '#94a3b8'}
                    />
                    <text textAnchor="middle" y="40">{node.label}</text>
                </g>
            ))}

            {graph.edges.map(edge => (
                <line
                    key={`${edge.from}-${edge.to}`}
                    x1={/* calculate from node position */}
                    y1={50}
                    x2={/* calculate to node position */}
                    y2={50}
                    stroke="#cbd5e1"
                    strokeWidth="2"
                />
            ))}
        </svg>
    );
}
```

### System Health Monitoring

```typescript
// src/components/SystemHealth.tsx
export function SystemHealth() {
    const { data: health } = useQuery({
        queryKey: ['system-health'],
        queryFn: async () => {
            const responses = await Promise.allSettled([
                fetch('http://localhost:8000/health'),  // Bloodbank
                fetch('http://localhost:8683/health'),  // Candystore
                fetch('http://localhost:5433/health'),  // TheBoard
            ]);

            return {
                bloodbank: responses[0].status === 'fulfilled',
                candystore: responses[1].status === 'fulfilled',
                theboard: responses[2].status === 'fulfilled',
            };
        },
        refetchInterval: 5000
    });

    return (
        <div className="grid grid-cols-3 gap-4">
            <ServiceStatus name="Bloodbank" healthy={health?.bloodbank} />
            <ServiceStatus name="Candystore" healthy={health?.candystore} />
            <ServiceStatus name="TheBoard" healthy={health?.theboard} />
        </div>
    );
}
```

## Configuration

```typescript
// src/config.ts
export const config = {
    api: {
        bloodbank: import.meta.env.VITE_BLOODBANK_URL || 'http://localhost:8000',
        candystore: import.meta.env.VITE_CANDYSTORE_URL || 'http://localhost:8683',
        theboard: import.meta.env.VITE_THEBOARD_URL || 'http://localhost:5433',
        agentforge: import.meta.env.VITE_AGENTFORGE_URL || 'http://localhost:8080',
    },
    websocket: {
        bloodbank: import.meta.env.VITE_BLOODBANK_WS || 'ws://localhost:8000/events',
    },
    refreshIntervals: {
        events: 30000,      // 30 seconds
        agents: 10000,      // 10 seconds
        health: 5000,       // 5 seconds
        workflows: 15000,   // 15 seconds
    }
};
```

## Integration Points

### Multi-Component Data Aggregation

```typescript
// Fetch data from multiple services
export function OverviewPage() {
    const { data: events } = useQuery({
        queryKey: ['overview', 'events'],
        queryFn: () => fetch(`${config.api.candystore}/events?limit=10`).then(r => r.json())
    });

    const { data: agents } = useQuery({
        queryKey: ['overview', 'agents'],
        queryFn: () => fetch(`${config.api.agentforge}/agents`).then(r => r.json())
    });

    const { data: meetings } = useQuery({
        queryKey: ['overview', 'meetings'],
        queryFn: () => fetch(`${config.api.theboard}/meetings`).then(r => r.json())
    });

    return (
        <div className="space-y-6">
            <EventStreamWidget events={events?.events} />
            <AgentStatusWidget agents={agents} />
            <MeetingHistoryWidget meetings={meetings} />
        </div>
    );
}
```

## Performance

- **Initial Load**: <2 seconds
- **Dashboard Update**: <100ms
- **WebSocket Latency**: <50ms
- **Memory**: ~75 MB

## Related Components

- **Bloodbank**: Real-time event stream
- **Candystore**: Historical event storage
- **TheBoard**: Meeting orchestration
- **AgentForge**: Agent management
- **iMi**: Worktree browser

---

**Quick Reference**:
- Dev Server: `npm run dev` (port 5173)
- Build: `npm run build`
- Package: `@33god/holocene`
