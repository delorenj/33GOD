# 33GOD Architecture

**33GOD** is an event-driven, agentic ecosystem designed to orchestrate software development, knowledge management, and automated workflows. It leverages a central event bus (**Bloodbank**) to decouple components, allowing autonomous agents and microservices to collaborate asynchronously.

## Core Principles

1.  **Everything is an Event**: All significant state changes (Git commits, PRs, transcripts ready, agent thoughts) are emitted as events.
2.  **Registry as Truth**: `services/registry.yaml` is the single source of truth for service discovery, topology, and event routing.
3.  **Modular & Autonomous**: Services are small, focused, and independently deployable. They react to events rather than being called directly.
4.  **Agent-Centric**: The system is designed to support AI agents (Claude, Gemini) as first-class citizens that consume and emit events.

## System Context (C4 Level 1)

The following diagram illustrates the high-level interactions between the User, the 33GOD Ecosystem, and external systems.

```mermaid
C4Context
    title System Context Diagram for 33GOD

    Person(user, "Developer / User", "Interacts with the system via CLI, Chat, or Dashboards")

    System_Boundary(33god, "33GOD Ecosystem") {
        System(agents, "AI Agents", "Claude, Gemini, etc. executing tasks")
        System(services, "Microservices", "Specialized workers (Transcript processing, Metrics)")
        System(candybar, "Candybar", "Visualization & Observability Dashboard")
    }

    System_Ext(fireflies, "Fireflies.ai", "Meeting transcription service")
    System_Ext(github, "GitHub", "Source control & PR management")
    System_Ext(obsidian, "Obsidian Vault", "Knowledge base (DeLoDocs)")
    System_Ext(imi, "iMi", "Git Worktree Manager")

    Rel(user, agents, "Instructs via Chat/CLI")
    Rel(user, candybar, "Views system status")
    
    Rel(fireflies, services, "Sends transcripts (Webhooks)")
    Rel(github, services, "Sends PR events (Webhooks)")
    
    Rel(services, obsidian, "Writes Markdown/Data")
    Rel(agents, obsidian, "Reads/Writes context")
    Rel(agents, imi, "Manages worktrees")
```

## Container Diagram (C4 Level 2)

This diagram zooms into the **33GOD Ecosystem** to show the logical containers and their communication via **Bloodbank**.

```mermaid
C4Container
    title Container Diagram for 33GOD Ecosystem

    Person(user, "Developer")

    Container_Boundary(33god, "33GOD") {
        
        Component(bloodbank, "Bloodbank", "RabbitMQ Topic Exchange", "Central Event Bus")
        Component(registry, "Registry", "YAML", "Service Definitions & Topology")
        
        Container(candybar, "Candybar", "React/Tauri", "Visualizes Registry & Live Events")
        
        Container(ff_processor, "Fireflies Processor", "Python/FastAPI", "Converts transcripts to Markdown")
        Container(agent_collector, "Agent Collector", "Python", "Collects agent telemetry")
        Container(future_svc, "Future Services", "Python/Rust", "TheBoard, Flume, etc.")
        
        Container(agents, "Agents", "Claude/Gemini", "Autonomous actors")
    }

    System_Ext(vault, "Vault", "File System")

    Rel(registry, candybar, "Defines Topology")
    
    Rel(agents, bloodbank, "Publishes/Consumes Events")
    Rel(ff_processor, bloodbank, "Consumes 'transcript.ready'")
    
    Rel(ff_processor, vault, "Writes files")
    
    Rel(bloodbank, candybar, "Streams events (WebSocket)")
```

## The Registry

The **Registry** (`services/registry.yaml`) is the heartbeat of the architecture. It defines:

*   **Services**: Name, description, type, and owner.
*   **Queues & Routing**: Which events a service listens to.
*   **Topology**: How services are layered and connected.

**Candybar** reads this registry to generate a dynamic network graph, allowing developers to see the system's architecture in real-time.

## Key Components

### Bloodbank (Event Bus)
*   **Technology**: RabbitMQ + Pydantic Models
*   **Role**: Guarantees delivery, handles routing patterns (Topic Exchange), and enforces schema validation for payloads.

### iMi (Worktree Manager)
*   **Role**: Manages Git worktrees for parallel development.
*   **Integration**: Emits events when worktrees are created/deleted, allowing agents to switch contexts automatically.

### TheBoard (Meeting Sync)
*   **Role**: Manages meeting lifecycles and "The Board" context.
*   **Integration**: Emits `meeting.started`, `meeting.converged` events to trigger recording or note-taking services.

### Flume (Orchestration)
*   **Role**: Handles complex, multi-step workflows (often via n8n).
*   **Integration**: Listens for high-level triggers (e.g., `feature.requested`) and orchestrates the sequence of agent tasks.
