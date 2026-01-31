# TheBoardroom - Technical Implementation Guide

## Overview

TheBoardroom is a real-time 3D visualization for TheBoard multi-agent brainstorming sessions. Built with PlayCanvas engine, it provides an immersive circular table view where AI agents are visualized as participants, showing who's speaking, turn types, and meeting progress in real-time.

## Implementation Details

**Language**: TypeScript
**Rendering Engine**: PlayCanvas (WebGL-based 3D)
**Build Tool**: Vite (required for PlayCanvas shader loading)
**Runtime**: Bun (JavaScript runtime and package manager)
**Event Source**: Bloodbank (RabbitMQ via WebSocket)

### Key Technologies

- **PlayCanvas Engine**: 3D rendering, entity-component system
- **Vite**: Build tooling with specialized shader handling
- **TypeScript**: Type-safe development
- **WebSocket**: Real-time event streaming from Bloodbank
- **Bun**: Ultra-fast package manager and dev server

## Architecture & Design Patterns

### Entity-Component-System (ECS)

PlayCanvas uses an ECS architecture where:
- **Entities**: Game objects (participants, table, camera)
- **Components**: Behavior modules (transform, render, script)
- **Systems**: Update loops that process components

```typescript
// src/entities/Participant.ts
import { Entity } from 'playcanvas';

export class ParticipantEntity extends Entity {
    private agentId: string;
    private agentName: string;
    private isSpeaking: boolean = false;
    private turnType: 'response' | 'turn' | null = null;

    constructor(agentId: string, agentName: string) {
        super();
        this.agentId = agentId;
        this.agentName = agentName;

        // Add visual components
        this.addComponent('model', {
            type: 'capsule',  // Simple avatar shape
        });

        // Add speaking indicator (glow effect)
        this.addComponent('light', {
            type: 'point',
            color: [0, 1, 0],  // Green for active
            intensity: 0,  // Off by default
            range: 2
        });
    }

    setSpeaking(isSpeaking: boolean, turnType: 'response' | 'turn') {
        this.isSpeaking = isSpeaking;
        this.turnType = turnType;

        // Update visual feedback
        const light = this.findComponent('light');
        if (isSpeaking) {
            light.intensity = 1.0;
            light.color = turnType === 'response'
                ? [0, 1, 0]  // Green for response
                : [0, 0.5, 1];  // Blue for turn
        } else {
            light.intensity = 0;
        }
    }
}
```

### Scene Setup

```typescript
// src/scenes/BoardroomScene.ts
import { Application } from 'playcanvas';
import { ParticipantEntity } from '../entities/Participant';

export class BoardroomScene {
    private app: Application;
    private participants: Map<string, ParticipantEntity> = new Map();

    constructor(canvas: HTMLCanvasElement) {
        this.app = new Application(canvas, {
            mouse: new pc.Mouse(canvas),
            touch: new pc.TouchDevice(canvas),
        });

        this.setupCamera();
        this.setupLighting();
        this.setupTable();
    }

    private setupCamera() {
        // Top-down orthographic view
        const camera = new Entity('camera');
        camera.addComponent('camera', {
            clearColor: [0.1, 0.1, 0.1],
            projection: 'orthographic',
            orthoHeight: 10,
        });
        camera.setPosition(0, 20, 0);
        camera.setEulerAngles(-90, 0, 0);
        this.app.root.addChild(camera);
    }

    private setupTable() {
        const table = new Entity('table');
        table.addComponent('model', {
            type: 'cylinder',
        });
        table.setLocalScale(8, 0.2, 8);  // Flat circular table
        this.app.root.addChild(table);
    }

    addParticipant(agentId: string, agentName: string) {
        const participant = new ParticipantEntity(agentId, agentName);

        // Position around circular table
        const index = this.participants.size;
        const angle = (index / 10) * Math.PI * 2;  // Up to 10 participants
        const radius = 6;

        participant.setPosition(
            Math.cos(angle) * radius,
            1,
            Math.sin(angle) * radius
        );

        this.participants.set(agentId, participant);
        this.app.root.addChild(participant);
    }
}
```

### Event Integration

```typescript
// src/events/BloodbankEventSource.ts
interface MeetingEvent {
    event_type: string;
    data: {
        meeting_id: string;
        agent_id?: string;
        agent_name?: string;
        turn_type?: 'response' | 'turn';
    };
}

export class BloodbankEventSource {
    private ws: WebSocket;
    private scene: BoardroomScene;

    constructor(scene: BoardroomScene, websocketUrl: string) {
        this.scene = scene;
        this.ws = new WebSocket(websocketUrl);

        this.ws.onmessage = (event) => {
            const message: MeetingEvent = JSON.parse(event.data);
            this.handleEvent(message);
        };
    }

    private handleEvent(event: MeetingEvent) {
        switch (event.event_type) {
            case 'theboard.meeting.created':
                console.log(`Meeting ${event.data.meeting_id} created`);
                break;

            case 'theboard.participant.added':
                this.scene.addParticipant(
                    event.data.agent_id!,
                    event.data.agent_name!
                );
                break;

            case 'theboard.participant.turn_started':
                this.scene.setParticipantSpeaking(
                    event.data.agent_id!,
                    true,
                    event.data.turn_type!
                );
                break;

            case 'theboard.participant.turn_completed':
                this.scene.setParticipantSpeaking(
                    event.data.agent_id!,
                    false,
                    event.data.turn_type!
                );
                break;

            case 'theboard.meeting.round_completed':
                this.scene.advanceRound();
                break;

            case 'theboard.meeting.completed':
                this.scene.showCompletionAnimation();
                break;
        }
    }
}
```

### Mock Event Source (Development)

```typescript
// src/events/MockEventSource.ts
export class MockEventSource {
    private scene: BoardroomScene;
    private interval: number;

    constructor(scene: BoardroomScene) {
        this.scene = scene;
    }

    start() {
        // Simulate meeting creation
        setTimeout(() => {
            this.simulateMeeting();
        }, 1000);
    }

    private async simulateMeeting() {
        // Add participants
        const agents = [
            'Security Architect',
            'UX Researcher',
            'Backend Developer',
            'Data Engineer',
            'DevOps Engineer'
        ];

        for (const [index, name] of agents.entries()) {
            this.scene.addParticipant(`agent-${index}`, name);
            await this.sleep(500);
        }

        // Simulate 3 rounds
        for (let round = 0; round < 3; round++) {
            for (let i = 0; i < agents.length; i++) {
                const agentId = `agent-${i}`;

                // Start turn
                this.scene.setParticipantSpeaking(agentId, true, 'turn');
                await this.sleep(2000);

                // End turn
                this.scene.setParticipantSpeaking(agentId, false, 'turn');
                await this.sleep(500);
            }

            this.scene.advanceRound();
        }

        this.scene.showCompletionAnimation();
    }

    private sleep(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}
```

## Configuration

### Development Environment

```bash
# Start dev server (auto-opens browser at localhost:3333)
bun run dev

# Type checking
bun run typecheck

# Build for production
bun run build

# Preview production build
bun run preview
```

### Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';

export default defineConfig({
    server: {
        port: 3333,
        open: true
    },
    build: {
        target: 'esnext',
        minify: 'terser',
        // PlayCanvas requires specific shader handling
        assetsInlineLimit: 0
    }
});
```

### PlayCanvas Initialization

```typescript
// src/main.ts
import { Application } from 'playcanvas';
import { BoardroomScene } from './scenes/BoardroomScene';
import { MockEventSource } from './events/MockEventSource';

const canvas = document.getElementById('application-canvas') as HTMLCanvasElement;

// Initialize scene
const scene = new BoardroomScene(canvas);

// Development: Use mock events
if (import.meta.env.DEV) {
    const mockEvents = new MockEventSource(scene);
    mockEvents.start();
} else {
    // Production: Connect to Bloodbank WebSocket
    const bloodbank = new BloodbankEventSource(
        scene,
        'ws://bloodbank.localhost/events'
    );
}

// Start render loop
scene.start();
```

## Integration Points

### Bloodbank WebSocket Integration

```typescript
// Future production integration
interface BloodbankConfig {
    url: string;
    subscriptions: string[];  // Event types to subscribe to
}

const config: BloodbankConfig = {
    url: 'ws://bloodbank.delo.sh/events',
    subscriptions: [
        'theboard.meeting.*',
        'theboard.participant.*'
    ]
};

const eventSource = new BloodbankEventSource(scene, config);
```

### Holyfields Schema Integration

```typescript
// Import generated TypeScript types from Holyfields
import {
    MeetingCreatedEventSchema,
    ParticipantAddedEventSchema
} from '@holyfields/generated/typescript/theboard/events';

function handleEvent(rawEvent: unknown) {
    // Runtime validation with Zod
    try {
        const event = MeetingCreatedEventSchema.parse(rawEvent);
        scene.handleMeetingCreated(event);
    } catch (error) {
        console.error('Invalid event schema:', error);
    }
}
```

## Performance Characteristics

### Rendering Performance

- **Target FPS**: 60fps
- **Participant Limit**: 10 agents (circular table layout)
- **Draw Calls**: <50 per frame
- **Memory Usage**: ~50MB (scene + assets)

### Optimization Strategies

```typescript
// Use object pooling for particles/effects
class ParticlePool {
    private pool: Entity[] = [];
    private activeParticles: Set<Entity> = new Set();

    acquire(): Entity {
        let particle = this.pool.pop();
        if (!particle) {
            particle = this.createParticle();
        }
        this.activeParticles.add(particle);
        return particle;
    }

    release(particle: Entity) {
        particle.enabled = false;
        this.activeParticles.delete(particle);
        this.pool.push(particle);
    }
}
```

### Adaptive Quality

```typescript
// Reduce quality on low-end devices
class QualityManager {
    private targetFPS = 60;
    private currentFPS = 60;

    update(deltaTime: number) {
        this.currentFPS = 1 / deltaTime;

        if (this.currentFPS < 30) {
            // Reduce shadow quality
            this.app.lightmapper.shadowQuality = 'low';

            // Reduce particle count
            this.particleSystem.maxParticles /= 2;
        }
    }
}
```

## Edge Cases & Troubleshooting

### WebSocket Reconnection

```typescript
class ResilientWebSocket {
    private ws: WebSocket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectDelay = 30000;

    connect(url: string) {
        this.ws = new WebSocket(url);

        this.ws.onclose = () => {
            // Exponential backoff
            const delay = Math.min(
                1000 * Math.pow(2, this.reconnectAttempts),
                this.maxReconnectDelay
            );

            setTimeout(() => {
                this.reconnectAttempts++;
                this.connect(url);
            }, delay);
        };

        this.ws.onopen = () => {
            this.reconnectAttempts = 0;
        };
    }
}
```

### Late-Joining Participants

**Problem**: Participant added mid-meeting, table already full
**Solution**: Dynamic table resizing

```typescript
private resizeTable(participantCount: number) {
    const radius = Math.max(6, participantCount * 0.8);  // Grow with participants

    // Reposition all participants
    this.participants.forEach((participant, index) => {
        const angle = (index / participantCount) * Math.PI * 2;
        participant.setPosition(
            Math.cos(angle) * radius,
            1,
            Math.sin(angle) * radius
        );
    });

    // Resize table
    this.table.setLocalScale(radius + 2, 0.2, radius + 2);
}
```

## Code Examples

### Custom Visual Effects

```typescript
// Convergence pulse animation
class ConvergenceEffect {
    private pulseEntity: Entity;

    show() {
        this.pulseEntity = new Entity('convergence-pulse');
        this.pulseEntity.addComponent('model', {
            type: 'sphere'
        });

        // Animate pulse
        this.app.on('update', (dt: number) => {
            const scale = 1 + Math.sin(Date.now() / 200) * 0.2;
            this.pulseEntity.setLocalScale(scale, scale, scale);
        });
    }
}
```

### Camera Controls

```typescript
// Orbit camera for interactive exploration
class OrbitCamera {
    private camera: Entity;
    private radius = 20;
    private angle = 0;

    update(deltaTime: number) {
        // Slow orbit around table
        this.angle += deltaTime * 0.1;

        this.camera.setPosition(
            Math.cos(this.angle) * this.radius,
            20,
            Math.sin(this.angle) * this.radius
        );

        this.camera.lookAt(0, 0, 0);  // Always look at table center
    }
}
```

## Deployment

### Production Build

```bash
# Build optimized bundle
bun run build

# Output: dist/
# - index.html
# - assets/
#   - main-[hash].js
#   - playcanvas-[hash].js
#   - styles-[hash].css
```

### Hosting (Static Site)

```nginx
# nginx.conf
server {
    listen 80;
    server_name boardroom.delo.sh;

    root /var/www/theboardroom/dist;
    index index.html;

    # WebSocket proxy to Bloodbank
    location /events {
        proxy_pass http://bloodbank:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Related Components

- **TheBoard**: Event producer (meeting orchestration)
- **Bloodbank**: Event bus (WebSocket stream)
- **Holyfields**: Event schema definitions

---

**Quick Reference**:
- GitHub: `33GOD/theboardroom`
- Dev Server: `http://localhost:3333`
- Package Manager: Bun (NOT npm)
