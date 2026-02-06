# Domain: Applications

> User interfaces and interaction surfaces. Where humans engage with the 33GOD ecosystem.

## Domain Overview

The Applications domain encompasses the user-facing components of the 33GOD platform, providing multiple interaction modalities: multi-agent brainstorming sessions, real-time 3D visualization, service topology dashboards, and voice-driven interfaces. These components transform the underlying event-driven infrastructure into accessible, intuitive experiences for developers, operators, and end users.

### Purpose

This domain serves as the **human-machine interface layer** of the 33GOD ecosystem, enabling:

1. **Collaborative Intelligence** - Multi-agent brainstorming with convergence detection
2. **System Observability** - Real-time visualization of service topology and health
3. **Voice Interaction** - Hands-free control and conversational AI assistance
4. **Immersive Visualization** - 3D meeting rooms for watching agent collaboration unfold

---

## Components

| Component | Directory | Role | Tech Stack | Status |
|-----------|-----------|------|------------|--------|
| **TheBoard** | `theboard/trunk-main` | Multi-agent brainstorming simulation | Python 3.12+, FastAPI, Agno, Letta, PostgreSQL, Redis, Qdrant | Active |
| **TheBoard Room** | `theboardroom/trunk-main` | 3D visualization for meetings | TypeScript, PlayCanvas, Vite, Bun | Active |
| **Candybar** | `candybar/trunk-main` | Service registry dashboard | Next.js 14, Tauri, React, shadcn/ui, Tailwind | Active |
| **HeyMa** | `HeyMa/trunk-main` | Voice interface system | Python (Whisper), Rust (Tauri), Chrome Extension, ElevenLabs | Active |

---

## Component Deep Dives

### 1. TheBoard - Multi-Agent Brainstorming System

**Directory:** `theboard/trunk-main`

#### Purpose and Responsibilities

TheBoard orchestrates collaborative AI brainstorming sessions where multiple agents contribute ideas, debate approaches, and converge on solutions. It acts as a virtual conference room for AI agents to collaborate on complex problems.

#### Key Features

- **Multi-Round Discussions**: Agents contribute in sequential or greedy (parallel) rounds
- **Intelligent Convergence Detection**: Automatically detects when consensus is reached
- **Context Compression**: 3-tier system to manage conversation context efficiently
  - **Tier 1**: Semantic clustering of similar contributions
  - **Tier 2**: LLM-based summarization of clusters
  - **Tier 3**: Outlier removal for noise reduction
- **Cost Tracking**: Monitors LLM API usage throughout sessions
- **Agent Auto-Selection**: Dynamically assembles optimal agent rosters based on topic
- **Comment Extraction**: Identifies key insights from agent contributions

#### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Framework | FastAPI | REST API and async handling |
| AI Framework | Agno, Letta | Agent orchestration |
| Database | PostgreSQL | Meeting persistence |
| Cache | Redis | Session state, rate limiting |
| Vector Store | Qdrant | Semantic search, embeddings |
| CLI | Typer + Rich | Interactive command-line interface |

#### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `THEBOARD_DATABASE_URL` | PostgreSQL connection | `postgresql://theboard:pass@localhost:5433/theboard` |
| `REDIS_URL` | Redis connection | `redis://localhost:6380` |
| `QDRANT_URL` | Qdrant vector store | `http://localhost:6333` |
| `DEFAULT_MODEL` | LLM model | `gpt-4.1` |
| `MAX_ROUNDS` | Maximum brainstorming rounds | `5` |
| `AGENT_COUNT` | Default agent count | `5` |

#### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/meetings` | POST | Create new brainstorming session |
| `/api/meetings/{id}` | GET | Get meeting details |
| `/api/meetings/{id}/start` | POST | Start brainstorming |
| `/api/meetings/{id}/rounds` | GET | Get round history |
| `/health` | GET | Health check |
| `/docs` | GET | OpenAPI documentation |

#### Event Integration

TheBoard publishes events to Bloodbank throughout the meeting lifecycle:

| Event | Description |
|-------|-------------|
| `theboard.meeting.created` | New meeting initialized |
| `theboard.meeting.started` | Brainstorming begun |
| `theboard.meeting.round_completed` | Round finished |
| `theboard.meeting.comment_extracted` | Key insight identified |
| `theboard.meeting.converged` | Consensus reached |
| `theboard.meeting.completed` | Meeting concluded |
| `theboard.meeting.failed` | Error occurred |

---

### 2. TheBoard Room - 3D Meeting Visualization

**Directory:** `/home/user/33GOD/theboardroom/trunk-main`

#### Purpose and Responsibilities

TheBoard Room provides an immersive 3D visualization of TheBoard meetings, rendering agents around a virtual conference table with real-time updates as discussions progress.

#### Key Features

- **3D Conference Room**: Circular table with agent avatars
- **Real-Time Updates**: WebSocket-driven live visualization
- **Speaking Indicators**: Visual cues showing which agent is contributing
- **Contribution Display**: Speech bubbles or panels showing agent responses
- **Meeting Progress**: Visual round and convergence indicators

#### Technology Stack

| Technology | Purpose |
|------------|---------|
| TypeScript | Type-safe development |
| PlayCanvas | 3D WebGL rendering engine |
| Vite | Fast build tooling |
| Bun | JavaScript runtime |
| WebSocket | Real-time event streaming |

#### UI/UX Patterns

- **Avatar Ring**: Agents positioned in a circle around the table
- **Focus Mode**: Highlights active speaker
- **Timeline View**: Horizontal progress showing rounds
- **Summary Panel**: Key decisions and extracted comments

#### Integration Points

- Subscribes to `theboard.meeting.*` events via Bloodbank
- Connects to TheBoard API for meeting metadata
- Real-time WebSocket connection for live updates

---

### 3. Candybar - Service Registry Dashboard

**Directory:** `/home/user/33GOD/candybar/trunk-main`

#### Purpose and Responsibilities

Candybar is the visual "Hub" for the 33GOD platform, providing real-time visualization of service topology, health monitoring, and event flow observability. It serves as the mission control for understanding how the ecosystem's microservices interact.

#### Key Features

- **Topology Visualization**: Interactive network graph of services
- **Health Monitoring**: Real-time service status (Online/Offline/Error)
- **Event Flow Display**: Live event stream visualization
- **Service Discovery**: Dynamic registry based on heartbeats
- **Queue Monitoring**: RabbitMQ queue depths and metrics
- **Correlation Tracing**: Track event chains across services

#### Technology Stack

| Technology | Purpose |
|------------|---------|
| Next.js 14 | React framework with App Router |
| Tauri | Desktop app wrapper (Nextauri pattern) |
| React 18 | UI component framework |
| shadcn/ui | Component library |
| Tailwind CSS | Utility-first styling |
| TanStack Query | Server state management |
| Zustand | Client state management |
| D3.js / react-force-graph | Network visualization |

#### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `CANDYSTORE_API_URL` | Event store API | `http://localhost:8080` |
| `BLOODBANK_WS_URL` | WebSocket event stream | `ws://localhost:8080/api/v1/events/stream` |
| `REGISTRY_PATH` | Service registry file | `services/registry.yaml` |

#### Data Sources

1. **Service Registry** (`services/registry.yaml`): Static service definitions
2. **Candystore API**: Event history and correlation queries
3. **Bloodbank WebSocket**: Real-time event stream
4. **Health Endpoints**: Per-service health checks

#### UI/UX Patterns

- **Network Graph**: Force-directed layout showing service relationships
- **Event Stream Panel**: Scrolling list of recent events
- **Service Cards**: Expandable details for each service
- **Correlation View**: Tree visualization of related events
- **Layer View**: Services grouped by topology layer

#### Dashboard Views

| View | Purpose |
|------|---------|
| **Topology** | Network graph of all services |
| **Events** | Live event stream |
| **Health** | Service status overview |
| **Queues** | RabbitMQ queue metrics |
| **Correlations** | Event chain explorer |

---

### 4. HeyMa - Voice Interface System

**Directory:** `/home/user/33GOD/HeyMa/trunk-main`

#### Purpose and Responsibilities

HeyMa enables voice-driven interaction with the 33GOD ecosystem, transcribing speech to text and generating spoken responses. It serves as the auditory interface for hands-free operation and conversational AI assistance.

#### Key Features

- **Real-Time Transcription**: WhisperLiveKit for streaming STT
- **Conversational AI**: Letta-powered stateful agent responses
- **Text-to-Speech**: ElevenLabs high-quality voice synthesis
- **Multi-Platform**: Desktop app (Tauri) + Chrome extension
- **Session Memory**: Maintains conversation context across interactions
- **Low Latency**: Target <2s end-to-end response time

#### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Transcription | WhisperLiveKit | Real-time speech-to-text |
| Agent | Letta | Stateful conversational AI |
| TTS | ElevenLabs | Voice synthesis |
| Desktop | Tauri (Rust) | Native desktop application |
| Browser | Chrome Extension | Web-based voice capture |
| Backend | Python (aio-pika) | Event consumer service |

#### Components Architecture

```
User Voice --> WhisperLiveKit --> transcription.voice.completed
                                          |
                                          v
                                   Tonny Agent (Letta)
                                          |
                                          v
                                   ElevenLabs TTS
                                          |
                                          v
                              tts.response.completed --> Audio Playback
```

#### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `RABBITMQ_URL` | Bloodbank connection | `amqp://guest:guest@localhost:5672/` |
| `LETTA_BASE_URL` | Letta server URL | `http://localhost:8283` |
| `LETTA_API_KEY` | Letta API key (optional) | - |
| `LLM_PROVIDER` | LLM backend | `openai` |
| `LLM_MODEL` | Model to use | `gpt-4.1` |
| `ELEVENLABS_API_KEY` | ElevenLabs API key | - |
| `ELEVENLABS_VOICE_ID` | Voice selection | `21m00Tcm4TlvDq8ikWAM` (Rachel) |
| `ELEVENLABS_MODEL_ID` | TTS model | `eleven_monolingual_v1` |
| `MAX_PROCESSING_LATENCY_MS` | Target latency | `2000` |

#### API Endpoints (Tonny Agent Service)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/metrics` | GET | Processing latency statistics |

#### Event Integration

**Consumed Events:**

| Event | Source | Description |
|-------|--------|-------------|
| `transcription.voice.completed` | WhisperLiveKit | Transcribed text ready for processing |

**Published Events:**

| Event | Target | Description |
|-------|--------|-------------|
| `tts.response.completed` | Client applications | Audio response ready for playback |

#### Performance Targets

| Metric | Target |
|--------|--------|
| Total Latency | <2000ms |
| LLM Processing | <1000ms |
| TTS Generation | <500ms |
| Consumer Overhead | <500ms |

---

## Integration with Other Domains

### Infrastructure Domain (Bloodbank)

All Applications domain components integrate with Bloodbank as the central event bus:

```
TheBoard          -->  theboard.meeting.* events  -->  Bloodbank
TheBoard Room     <--  theboard.meeting.* events  <--  Bloodbank
Candybar          <--  WebSocket event stream     <--  Candystore <-- Bloodbank
HeyMa        <->  voice/tts events           <->  Bloodbank
```

### Meeting Trigger Service

The `theboard-meeting-trigger` service bridges ecosystem events to TheBoard:

**Consumed Events:**
- `theboard.meeting.trigger` - Direct meeting trigger
- `feature.brainstorm.requested` - Feature ideation requests
- `architecture.review.needed` - Architecture discussion triggers
- `incident.postmortem.scheduled` - Post-incident analysis (planned)
- `decision.analysis.required` - Decision support (planned)

**Published Events:**
- `theboard.meeting.trigger.processing` - Acknowledgment
- `theboard.meeting.trigger.completed` - Success
- `theboard.meeting.trigger.failed` - Failure

### Schema Registry (Holyfields)

All event payloads are validated against Holyfields schemas for type safety.

### Event Store (Candystore)

Candybar queries Candystore for:
- Historical event data
- Correlation chain queries
- Workflow state projections

---

## Common Use Cases

### Use Case 1: Feature Brainstorming

**Trigger:** Developer publishes `feature.brainstorm.requested` event

```python
# Example: Triggering a feature brainstorm
await publisher.publish(
    routing_key="feature.brainstorm.requested",
    payload={
        "feature_name": "Real-time Collaboration",
        "feature_description": "Allow multiple users to edit documents simultaneously",
        "requirements": ["Conflict resolution", "Presence indicators", "Offline support"]
    }
)
```

**Flow:**
1. Meeting trigger service creates TheBoard session
2. Agents auto-selected based on topic
3. Multi-round discussion with convergence detection
4. TheBoard Room visualizes progress in 3D
5. Final summary and decisions published as events

### Use Case 2: Voice-Driven Development

**Trigger:** User speaks to HeyMa

```
User: "What's the status of the authentication service?"
```

**Flow:**
1. WhisperLiveKit transcribes speech
2. Tonny agent processes via Letta
3. Agent queries system state (potentially triggering events)
4. Response generated and spoken via ElevenLabs
5. User hears: "The authentication service is healthy with 99.8% uptime."

### Use Case 3: System Health Monitoring

**Trigger:** Operator opens Candybar dashboard

**Flow:**
1. Candybar loads service registry topology
2. WebSocket connects to Candystore for live events
3. Health endpoints polled for each service
4. Network graph displays real-time status
5. Event stream shows activity across the platform

### Use Case 4: Architecture Review

**Trigger:** CI/CD publishes `architecture.review.needed` event after detecting significant changes

```python
await publisher.publish(
    routing_key="architecture.review.needed",
    payload={
        "component": "Authentication Module",
        "review_focus": ["Security", "Scalability", "API Design"],
        "current_architecture": "JWT-based with Redis session store"
    }
)
```

**Flow:**
1. Meeting trigger creates architecture review session
2. Specialized agents (Security, Architecture, API Design) auto-selected
3. Structured review with focus areas
4. Recommendations and decisions published

---

## Troubleshooting Guide

### TheBoard Issues

#### Meeting Not Starting

**Symptoms:** Meeting creation succeeds but rounds never begin

**Checks:**
1. Verify PostgreSQL connection: `psql $THEBOARD_DATABASE_URL -c "SELECT 1"`
2. Check Redis: `redis-cli -u $REDIS_URL ping`
3. Verify agent configuration: Check logs for "agent initialization"
4. Review Qdrant health: `curl http://localhost:6333/health`

**Common Fixes:**
- Restart TheBoard service
- Clear Redis cache: `redis-cli FLUSHDB`
- Check LLM API key validity

#### Convergence Not Detected

**Symptoms:** Meetings run to max rounds without converging

**Checks:**
1. Review convergence threshold in settings
2. Check if agents are producing substantially different outputs
3. Verify embedding model is working (Qdrant similarity)

**Common Fixes:**
- Adjust `CONVERGENCE_THRESHOLD` (default: 0.85)
- Use a more capable model
- Reduce agent diversity for clearer consensus

### Candybar Issues

#### Services Not Appearing

**Symptoms:** Dashboard shows empty or partial topology

**Checks:**
1. Verify `registry.yaml` path is correct
2. Check Candystore API health: `curl http://localhost:8080/health`
3. Confirm WebSocket connection in browser dev tools

**Common Fixes:**
- Restart Candybar
- Verify service registry YAML syntax
- Check for CORS issues with API

#### Stale Health Status

**Symptoms:** Services show outdated status

**Checks:**
1. Verify health endpoint polling interval
2. Check network connectivity to services
3. Review browser console for errors

**Common Fixes:**
- Clear browser cache
- Adjust polling interval
- Check service health endpoint implementations

### HeyMa Issues

#### No Transcription

**Symptoms:** Speech not being converted to text

**Checks:**
1. Verify WhisperLiveKit is running
2. Check microphone permissions
3. Review browser console (Chrome extension) or Tauri logs

**Common Fixes:**
- Grant microphone access
- Restart WhisperLiveKit service
- Check audio input device selection

#### High Latency

**Symptoms:** Response time exceeds 2s target

**Checks:**
1. Review `/metrics` endpoint for breakdown
2. Check LLM provider status
3. Verify ElevenLabs quota hasn't been exceeded

**Common Fixes:**
- Use faster LLM model (e.g., `gpt-4o-mini`)
- Enable streaming TTS
- Increase `CONSUMER_PREFETCH_COUNT`

#### ElevenLabs Rate Limiting

**Symptoms:** TTS generation fails with 429 errors

**Checks:**
1. Check ElevenLabs dashboard for quota usage
2. Review `Retry-After` header in logs

**Common Fixes:**
- Upgrade ElevenLabs plan
- Implement client-side caching for common responses
- Reduce voice quality settings temporarily

### General Event Issues

#### Events Not Processing

**Symptoms:** Events published but not consumed

**Checks:**
1. Verify RabbitMQ is running: `rabbitmqctl status`
2. Check queue bindings: `rabbitmqctl list_bindings`
3. Review dead letter queue for failed messages

**Common Fixes:**
- Restart consumer services
- Check routing key spelling
- Verify exchange exists: `rabbitmqctl list_exchanges`

#### Correlation Chain Broken

**Symptoms:** Related events not linked

**Checks:**
1. Verify `correlation_ids` are being passed correctly
2. Check Candystore logs for ingestion errors

**Common Fixes:**
- Ensure all services use `event_producers` library correctly
- Verify `enable_correlation_tracking=True` in publishers

---

## When to Include This Domain Context

Pass this domain documentation to AI agents when:

- Building or debugging **user-facing features**
- Working on **brainstorming or multi-agent collaboration**
- Developing **dashboard or visualization** components
- Implementing **voice interaction** features
- Troubleshooting **service discovery** or **health monitoring**
- Creating **meeting triggers** or **event automation**
- Optimizing **real-time communication** (WebSocket, streaming)
- Adding new **UI components** to the ecosystem

### Keyword Triggers

Include this domain for queries containing:
- brainstorming, meeting, convergence, collaboration
- dashboard, visualization, topology, graph
- voice, speech, transcription, TTS, ElevenLabs, Whisper
- service registry, health check, monitoring
- Candybar, TheBoard, HeyMa
- user interface, UI, frontend
- 3D, PlayCanvas, WebGL
- Tauri, desktop app, Chrome extension

---

## Key File Locations

| Component | Primary Location |
|-----------|------------------|
| TheBoard | `/home/user/33GOD/theboard/trunk-main/` |
| TheBoard Room | `/home/user/33GOD/theboardroom/trunk-main/` |
| Candybar | `/home/user/33GOD/candybar/trunk-main/` |
| HeyMa | `/home/user/33GOD/HeyMa/trunk-main/` |
| Meeting Trigger Service | `/home/user/33GOD/services/theboard-meeting-trigger/` |
| Tonny Agent Service | `/home/user/33GOD/services/tonny/` |
| Candystore (Event Store) | `/home/user/33GOD/services/candystore/` |
| Service Registry | `/home/user/33GOD/services/registry.yaml` |

---

## Related Documentation

- [Event Infrastructure Domain](/home/user/33GOD/docs/domains/event-infrastructure.md)
- [Meeting & Collaboration Domain](/home/user/33GOD/docs/domains/meeting-collaboration.md)
- [Dashboards & Voice Domain](/home/user/33GOD/docs/domains/dashboards-voice.md)
- [Architecture Overview](/home/user/33GOD/docs/ARCHITECTURE.md)
- [Unified Requirements Map](/home/user/33GOD/docs/unified-requirements-map.md)

---

## Last Sync

<!-- degenerate:sync-marker -->
Commit: (auto-generated)
Date: 2026-01-30
