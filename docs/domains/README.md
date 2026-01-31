# 33GOD Domain Documentation

## Overview

This directory contains comprehensive C4 model documentation and Mermaid diagrams for all five domains in the 33GOD platform. Each domain includes data flow diagrams, dependency graphs, and sequence diagrams that visualize system architecture at multiple levels of detail.

## Documentation Structure

Each domain folder contains:

1. **C4 Documentation** (4 levels)
   - `c4-context.md` - System context, personas, external systems
   - `c4-container.md` - Deployment architecture, containers, APIs
   - `c4-component.md` - Internal component structure
   - `c4-code.md` - Implementation details, code-level architecture

2. **Mermaid Diagrams** (3 types)
   - `data-flows.md` - How data moves through the domain
   - `dependencies.md` - Component dependencies and integration points
   - `sequences.md` - Interaction patterns and message flows

## The 5 Domains

### 1. Event Infrastructure
**Components**: Bloodbank, Holyfields, Services

Provides distributed event streaming, schema validation, and service coordination through RabbitMQ message brokering and contract-based schema management.

**Documentation**:
- [C4 Context](./event-infrastructure/c4-context.md)
- [C4 Container](./event-infrastructure/c4-container.md)
- [Data Flows](./event-infrastructure/data-flows.md) - 6 flow diagrams
- [Dependencies](./event-infrastructure/dependencies.md) - 6 dependency graphs
- [Sequences](./event-infrastructure/sequences.md) - 8 sequence diagrams

**Key Flows**:
- Event publishing and routing (Publish-Subscribe pattern)
- Webhook integration (Fireflies, GitHub)
- Schema validation and code generation
- Dead letter queue handling
- Voice transcription (TalkyTonny)

---

### 2. Workspace Management
**Components**: iMi, Jelmore, Zellij-Driver, Perth

Intelligent Git worktree management, AI session orchestration, and terminal context persistence for asynchronous parallel workflows.

**Documentation**:
- [C4 Context](./workspace-management/c4-context.md)
- [C4 Container](./workspace-management/c4-container.md)
- [Data Flows](./workspace-management/data-flows.md) - 7 flow diagrams
- [Dependencies](./workspace-management/dependencies.md) - 7 dependency graphs
- [Sequences](./workspace-management/sequences.md) - 8 sequence diagrams

**Key Flows**:
- Worktree creation and claiming
- Agent exclusive access coordination
- AI session persistence and recovery
- Terminal context tracking (intent + milestones)
- Configuration synchronization via symlinks

---

### 3. Agent Orchestration
**Components**: Flume, Yi, AgentForge, Holocene, BMAD

Protocol-driven hierarchical task delegation and meta-agent team building across multiple AI frameworks (Letta, Agno, Smolagents).

**Documentation**:
- [C4 Context](./agent-orchestration/c4-context.md)
- [C4 Container](./agent-orchestration/c4-container.md)
- [Data Flows](./agent-orchestration/data-flows.md) - Meta-agent team building, task delegation
- [Dependencies](./agent-orchestration/dependencies.md) - Framework dependencies, protocol layers
- [Sequences](./agent-orchestration/sequences.md) - Hierarchical delegation patterns

**Key Flows**:
- Meta-agent team building (5-agent meta-team)
- Hierarchical task delegation (Director → Manager → Contributor)
- Framework-agnostic adapter pattern (Yi)
- BMAD workflow orchestration
- Hive mind coordination

---

### 4. Meeting & Collaboration
**Components**: TheBoard, TheBoardroom

Meeting lifecycle orchestration, convergence detection, and real-time visualization of meeting states.

**Documentation**:
- [C4 Context](./meeting-collaboration/c4-context.md)
- [C4 Container](./meeting-collaboration/c4-container.md)
- [Data Flows](./meeting-collaboration/data-flows.md) - Meeting lifecycle, transcript processing
- [Dependencies](./meeting-collaboration/dependencies.md) - Fireflies integration, event dependencies
- [Sequences](./meeting-collaboration/sequences.md) - Meeting convergence, transcript flow

**Key Flows**:
- Meeting detection and convergence
- Fireflies recording integration
- Transcript processing and storage
- Real-time meeting state updates
- TheBoardroom visualization

---

### 5. Dashboards & Voice
**Components**: Candybar, TalkyTonny, Jelmore Dashboard

Voice-controlled AI assistant, service registry visualization, and real-time observability dashboards.

**Documentation**:
- [C4 Context](./dashboards-voice/c4-context.md)
- [C4 Container](./dashboards-voice/c4-container.md)
- [Data Flows](./dashboards-voice/data-flows.md) - Voice transcription, dashboard updates
- [Dependencies](./dashboards-voice/dependencies.md) - Whisper AI, WebSocket, event streaming
- [Sequences](./dashboards-voice/sequences.md) - Voice command processing, real-time updates

**Key Flows**:
- Voice transcription (Whisper AI)
- Intent recognition and workflow triggering
- Real-time dashboard updates (WebSocket)
- Service registry visualization (Candybar)
- Agent observability (Holocene)

---

## Diagram Types Explained

### Data Flow Diagrams
Visualize how information moves through components:
- **Flowcharts** - Process flows, decision points, data transformations
- **Swimlane diagrams** - Multi-actor workflows
- **Pipeline diagrams** - Sequential processing stages

### Dependency Graphs
Show architectural dependencies:
- **Component graphs** - Service-to-service dependencies
- **Build vs runtime** - Temporal dependency separation
- **Layered architecture** - Hierarchical dependency tiers
- **Impact analysis** - Critical vs optional dependencies

### Sequence Diagrams
Detail interaction patterns:
- **Message flows** - Communication between services
- **Time-ordered interactions** - Chronological execution
- **Error handling** - Failure scenarios and recovery
- **Event-driven patterns** - Asynchronous communication

## Mermaid Diagram Features

All diagrams use professional Mermaid syntax with:
- **Color coding** - Critical (red), Important (orange), Success (green)
- **Decision nodes** - Diamond shapes for conditional logic
- **Subgraphs** - Logical grouping of related components
- **Styling** - Consistent visual language across all diagrams
- **Comments** - Explanatory notes for complex flows

## Quick Reference

| Domain | Components | Primary Pattern | Key Technology |
|--------|-----------|-----------------|----------------|
| Event Infrastructure | Bloodbank, Holyfields | Event-Driven | RabbitMQ, Pydantic |
| Workspace Management | iMi, Jelmore | Worktree Isolation | Git, SQLite, Redis |
| Agent Orchestration | Flume, Yi, AgentForge | Hierarchical Delegation | Multi-framework adapters |
| Meeting & Collaboration | TheBoard, TheBoardroom | Convergence Detection | Fireflies, WebSocket |
| Dashboards & Voice | Candybar, TalkyTonny | Real-time Streaming | Whisper, WebSocket |

## Cross-Domain Integration

All domains integrate through:
- **Bloodbank Event Bus** - Asynchronous event-driven communication
- **PostgreSQL Database** - Shared global state
- **Redis Cache** - Shared session and state caching
- **Holyfields Schemas** - Type-safe event contracts

## Navigation

- [Architecture Overview](../ARCHITECTURE.md) - System-wide architecture
- [Service ERD](../SERVICE_ERD.md) - Entity relationship diagrams
- [Unified Requirements Map](../unified-requirements-map.md) - Cross-domain requirements

## Diagram Statistics

| Domain | Data Flows | Dependencies | Sequences | Total |
|--------|-----------|--------------|-----------|-------|
| Event Infrastructure | 6 | 6 | 8 | 20 |
| Workspace Management | 7 | 7 | 8 | 22 |
| Agent Orchestration | 2 | 1 | 1 | 4 |
| Meeting & Collaboration | 1 | 1 | 1 | 3 |
| Dashboards & Voice | 2 | 1 | 2 | 5 |
| **Total** | **18** | **16** | **20** | **54** |

## Rendering Diagrams

### Mermaid Live Editor
View and edit diagrams online:
1. Visit https://mermaid.live
2. Copy diagram code from markdown files
3. Paste into editor for live rendering

### VS Code Extensions
Recommended extensions:
- **Markdown Preview Mermaid Support** - Inline rendering
- **Mermaid Markdown Syntax Highlighting** - Syntax highlighting

### CLI Rendering
Generate PNG/SVG from diagrams:
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i diagram.md -o diagram.png
```

## Contributing

When adding or updating diagrams:
1. Follow existing naming conventions (`data-flows.md`, `dependencies.md`, `sequences.md`)
2. Use consistent color scheme (critical=red, important=orange, success=green)
3. Include diagram titles and descriptions
4. Add version and last updated date
5. Link to related documentation

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-29 | Initial comprehensive Mermaid diagram set for all 5 domains |

---

**Maintained By**: 33GOD Architecture Team
**Last Updated**: 2026-01-29
**Total Diagrams**: 54 professional Mermaid visualizations
