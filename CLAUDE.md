# Claude Code Configuration - SPARC Development Environment

## 🎯 UNIVERSAL 33GOD FACTS (ALWAYS TRUE)

**Architecture Core Principles:**

1. **Everything is an Event**: All state changes flow through Bloodbank (RabbitMQ)
2. **Registry as Truth**: `services/registry.yaml` defines service topology
3. **Event-Driven Communication**: Components NEVER call each other directly
4. **6 Domains**: Infrastructure, Agent Orchestration, Workspace Management, Meeting & Collaboration, Dashboards & Voice, Development Tools
5. **17+ Components**: Each component has a GOD.md documenting its role

**Documentation Hierarchy (GOD Documents):**

- **System-Level**: `docs/GOD.md` - Overall architecture, cross-domain contracts
- **Domain-Level**: `docs/domains/{domain}/GOD.md` - Domain-specific architecture
- **Component-Level**: `{component}/GOD.md` - Technical deep-dive, event contracts

**Event Contracts:**

- **Pattern**: `{domain}.{entity}.{action}` (e.g., `imi.worktree.created`)
- **Schemas**: Defined in `holyfields/schemas/`
- **Validation**: Bloodbank validates all events at publish time
- **Tracing**: `correlation_id` tracks event chains

**When Working on 33GOD:**

1. Check component's GOD.md for event contracts BEFORE making changes
2. Update GOD docs when adding/changing Bloodbank events
3. Document all emitted and consumed events in component GOD.md
4. Git hook (`.githooks/pre-commit`) prompts for GOD doc updates
5. DO NOT implement code in any component that is owned by another team without coordination. Instead, add tickets to the corresponding Plane project for the responsible team to implement.

**Critical Files:**

- `docs/GOD.md` - System architecture
- `docs/GOD-SYSTEM-GUIDE.md` - GOD doc maintenance guide
- `services/registry.yaml` - Service topology
- `holyfields/schemas/` - Event schemas

## Project Overview

This project uses the BMAD methodology

- Each component in 33GOD is being developed in parallel and tracked in an independent repository
- Each component is assigned to a dedicated team of developers led by a domain-savvy PM and Tech Lead
- Each component is following its own BMAD workflow tailored to its specific needs
- Sitting atop the entire architecture is this main 33GOD repository which coordinates the overall architecture, event contracts, and cross-component integration
- This repository is organized and managed by Giddeon, the 33GOD Repository Custodian. He performs git operations, releases, and ensures consistency across all components.
- The entire 33GOD project is led by Grolf, the Director of Engineering, who oversees the architecture, domain leads, and component teams to ensure successful delivery of the 33GOD vision.
- Each agent is a [Yi](./yi) node (Not Yet Implemented)
- The team structure (distribution of Yi nodes) is managed by [Flume](./flume) (Not Yet Implemented)

## Architectural North Star Principles

### 1. User-Centric Development

- Every task must add intrinsic value to the business strategy team
- Focus on accurate brand/product matching for store inventory optimization
- Prioritize features that directly impact sales and revenue insights
- Design interfaces and reports for clarity and actionability

### 2. Results-Focused Implementation

- No task is complete without validation through testing
- All acceptance criteria must be measurable and testable
- Implementation must demonstrate real, actual results
- Continuous validation throughout development lifecycle

### 3. Walking Skeleton Approach

- Implement wide-and-shallow for complex features
- Establish complete data flow before deep implementation
- Create minimal working implementations for all components
- Focus on system integration before detailed functionality

### 4. Layer-First Design

- Strict separation of concerns
- Single Responsibility Principle at method level
- Promote modularity through clear layer boundaries
- Design for reusability through abstraction

### 5. Composition Over Inheritance

- Favor object composition over class inheritance
- Build complex behaviors from simple components
- Use dependency injection for flexibility
- Design for plug-and-play component replacement

### 6. Strong Encapsulation

- Package parameters in domain-specific payloads
- Return results in structured response objects
- Encode usage patterns in the type system
- Maintain clear boundaries between components
