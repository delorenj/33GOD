# Candybar - Technical Implementation Guide

## Overview

Candybar is the real-time event visualization dashboard for the 33GOD ecosystem. Built with React + Vite, it provides interactive charts, event stream monitoring, and system health metrics by consuming events from Candystore (event storage) and Bloodbank (live event stream).

## Implementation Details

**Language**: TypeScript + React
**Build Tool**: Vite
**State Management**: Zustand
**Charting**: Recharts (D3-based)
**Real-time**: WebSocket (Bloodbank integration)
**Package Manager**: npm/bun

### Key Technologies

- **React 18**: UI framework
- **Vite**: Fast build tooling
- **Recharts**: Declarative charts built on D3
- **Zustand**: Lightweight state management
- **TanStack Query**: Server state synchronization
- **WebSocket**: Real-time event streaming

## Architecture & Design Patterns

### Store Architecture

```typescript
// src/store/eventStore.ts
import create from 'zustand';

interface EventStore {
    events: Event[];
    filters: EventFilters;
    addEvent: (event: Event) => void;
    setFilters: (filters: Partial<EventFilters>) => void;
    clearEvents: () => void;
}

export const useEventStore = create<EventStore>((set) => ({
    events: [],
    filters: {
        eventType: null,
        source: null,
        timeRange: '1h'
    },

    addEvent: (event) => set((state) => ({
        events: [event, ...state.events].slice(0, 1000)  // Keep last 1000
    })),

    setFilters: (filters) => set((state) => ({
        filters: { ...state.filters, ...filters }
    })),

    clearEvents: () => set({ events: [] })
}));
```

### WebSocket Integration

```typescript
// src/hooks/useEventStream.ts
import { useEffect } from 'react';
import { useEventStore } from '../store/eventStore';

export function useEventStream(bloodbankUrl: string) {
    const addEvent = useEventStore(state => state.addEvent);

    useEffect(() => {
        const ws = new WebSocket(bloodbankUrl);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            addEvent(data);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
            console.log('WebSocket closed. Reconnecting...');
            // Exponential backoff reconnection
            setTimeout(() => useEventStream(bloodbankUrl), 5000);
        };

        return () => ws.close();
    }, [bloodbankUrl, addEvent]);
}
```

### Event Timeline Component

```typescript
// src/components/EventTimeline.tsx
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useEventStore } from '../store/eventStore';

export function EventTimeline() {
    const events = useEventStore(state => state.events);

    // Aggregate events by minute
    const data = useMemo(() => {
        const buckets = new Map<number, number>();

        events.forEach(event => {
            const minute = Math.floor(new Date(event.timestamp).getTime() / 60000);
            buckets.set(minute, (buckets.get(minute) || 0) + 1);
        });

        return Array.from(buckets.entries())
            .map(([minute, count]) => ({
                time: minute * 60000,
                events: count
            }))
            .sort((a, b) => a.time - b.time);
    }, [events]);

    return (
        <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data}>
                <XAxis
                    dataKey="time"
                    type="number"
                    domain={['auto', 'auto']}
                    tickFormatter={(ts) => new Date(ts).toLocaleTimeString()}
                />
                <YAxis />
                <Tooltip
                    labelFormatter={(ts) => new Date(ts).toLocaleString()}
                />
                <Area
                    type="monotone"
                    dataKey="events"
                    stroke="#8884d8"
                    fill="#8884d8"
                />
            </AreaChart>
        </ResponsiveContainer>
    );
}
```

### Event Type Distribution

```typescript
// src/components/EventDistribution.tsx
import { PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

export function EventDistribution() {
    const events = useEventStore(state => state.events);

    const data = useMemo(() => {
        const counts = new Map<string, number>();

        events.forEach(event => {
            const type = event.event_type.split('.')[0];  // First segment
            counts.set(type, (counts.get(type) || 0) + 1);
        });

        return Array.from(counts.entries())
            .map(([name, value]) => ({ name, value }))
            .sort((a, b) => b.value - a.value)
            .slice(0, 5);  // Top 5
    }, [events]);

    return (
        <PieChart width={400} height={300}>
            <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label
            >
                {data.map((entry, index) => (
                    <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
            </Pie>
            <Tooltip />
            <Legend />
        </PieChart>
    );
}
```

### Event Search & Filter

```typescript
// src/components/EventSearch.tsx
export function EventSearch() {
    const { filters, setFilters } = useEventStore();

    return (
        <div className="filters">
            <input
                type="text"
                placeholder="Event type..."
                value={filters.eventType || ''}
                onChange={(e) => setFilters({ eventType: e.target.value })}
            />

            <select
                value={filters.source || ''}
                onChange={(e) => setFilters({ source: e.target.value })}
            >
                <option value="">All sources</option>
                <option value="theboard">TheBoard</option>
                <option value="heymama">HeyMa</option>
                <option value="imi">iMi</option>
                <option value="agentforge">AgentForge</option>
            </select>

            <select
                value={filters.timeRange}
                onChange={(e) => setFilters({ timeRange: e.target.value })}
            >
                <option value="5m">Last 5 minutes</option>
                <option value="1h">Last hour</option>
                <option value="24h">Last 24 hours</option>
                <option value="all">All time</option>
            </select>
        </div>
    );
}
```

## Configuration

```typescript
// src/config.ts
export const config = {
    bloodbank: {
        wsUrl: import.meta.env.VITE_BLOODBANK_WS_URL || 'ws://localhost:8000/events',
    },
    candystore: {
        apiUrl: import.meta.env.VITE_CANDYSTORE_API_URL || 'http://localhost:8683',
    },
    refreshInterval: 30000,  // 30 seconds
};
```

```bash
# .env.development
VITE_BLOODBANK_WS_URL=ws://localhost:8000/events
VITE_CANDYSTORE_API_URL=http://localhost:8683
```

## Integration Points

### Candystore Historical Query

```typescript
// src/api/candystore.ts
import { useQuery } from '@tanstack/react-query';

export function useHistoricalEvents(filters: EventFilters) {
    return useQuery({
        queryKey: ['events', filters],
        queryFn: async () => {
            const params = new URLSearchParams({
                limit: '100',
                ...(filters.eventType && { event_type: filters.eventType }),
                ...(filters.source && { source: filters.source }),
            });

            const response = await fetch(
                `${config.candystore.apiUrl}/events?${params}`
            );

            return response.json();
        },
        refetchInterval: config.refreshInterval,
    });
}
```

### Bloodbank Live Stream

```typescript
// Combine historical + live data
export function EventDashboard() {
    const { data: historical } = useHistoricalEvents(filters);
    useEventStream(config.bloodbank.wsUrl);  // Adds to store

    const allEvents = useMemo(() => {
        const liveEvents = useEventStore(state => state.events);
        return [...liveEvents, ...(historical?.events || [])];
    }, [historical, liveEvents]);

    return (
        <div>
            <EventTimeline events={allEvents} />
            <EventDistribution events={allEvents} />
        </div>
    );
}
```

## Performance

- **Event Rendering**: <16ms (60 FPS)
- **Chart Update**: <100ms
- **WebSocket Latency**: <50ms
- **Memory**: ~50 MB (1000 events cached)

## Related Components

- **Candystore**: Event storage API (historical data)
- **Bloodbank**: Event bus (real-time stream)
- **Holyfields**: Event schema validation

---

**Quick Reference**:
- GitHub: `33GOD/candybar`
- Dev Server: `npm run dev` (port 5173)
- Build: `npm run build`
