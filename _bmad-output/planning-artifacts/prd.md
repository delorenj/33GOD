---
stepsCompleted: ["step-01-init", "step-02-discovery", "step-03-success", "step-04-journeys", "step-05-domain", "step-06-innovation", "step-07-project-type"]
inputDocuments:
  - "/home/delorenj/code/33GOD/docs/GOD.md"
  - "/home/delorenj/code/33GOD/docs/domains/README.md"
  - "/home/delorenj/code/33GOD/HeyMa/schema-design-feedback.md"
  - "/home/delorenj/code/33GOD/bloodbank/GOD.md"
  - "/home/delorenj/code/33GOD/holyfields/GOD.md"
  - "/home/delorenj/code/33GOD/candybar/docs/architecture-candybar-2026-01-12.md"
  - "/home/delorenj/code/33GOD/HeyMa/docs/bloodbank-integration.md"
workflowType: 'prd'
classification:
  projectType: "Developer Tool / Platform"
  domain: "Scientific/Computational"
  complexity: "High"
  projectContext: "Greenfield"
  coreCriteria:
    - "GOD documentation system with maximum signal-to-noise ratio"
    - "Cross-domain alignment and dependency visibility"
    - "Pure event-driven architecture (Command/Event distinction, no Law of Demeter violations)"
---

# Product Requirements Document

## 33GOD Domain Organization and Event Schema Standardization

## Success Criteria

### User Success (Developers/Agents Using 33GOD)

**Success = Decreasing need to ask the architect**

- **GOD docs answer architecture questions** without needing to trace code or ask humans
- **Event contracts are discoverable** - agents/developers know what to publish/subscribe without guessing
- **Cross-domain dependencies are visible** - clear what breaks when you change X
- **Adding components doesn't break the system** - boundaries and contracts guide safe extension

**The "aha!" moment:** A developer adds a new service to a domain and it just works because GOD docs + event contracts made the path obvious.

### Business Success (Your Success as the Builder)

**Success = Growing autonomy**

Optimize for:
- **↑ Q**: Quality of autonomous completions approaches human-level
- **↑ T**: Number of L-sized tasks 33GOD completes without human intervention
- **↓ E**: Human effort required to supervise/correct/feed the system

**Measurable outcome:** Week-over-week, E decreases while T increases.

**The real goal:** Build an anthropomorphic agentic pipeline that acts increasingly autonomous - less babysitting, more independent problem-solving.

### Technical Success

**Architecture that enables autonomy:**

- **Pure event-driven**: Zero Law of Demeter violations, all communication via Bloodbank
- **Command/Event distinction enforced**: Commands = single consumer mutation, Events = fan-out reads
- **Schema validation at publish time**: Invalid events rejected before they propagate
- **GOD docs stay current**: Automated drift detection (Degenerate) catches doc-code divergence
- **Cross-domain contracts explicit**: Holyfields schema registry documents all event contracts
- **Observable by default**: Every event traceable via correlation_id through Bloodbank

### Measurable Outcomes

**MVP (Walking Skeleton):**
- One complete workflow runs end-to-end across all 6 domains
- Minimal infrastructure operational (Bloodbank + Holyfields + basic schemas)
- Each domain has at least one component responding to events
- GOD docs document the skeleton flow
- Success gate: One L-sized task completes without manual handoffs

**Growth (Increasing Autonomy):**
- 33GOD handles complex multi-domain tasks with minimal supervision
- E measurably decreasing week-over-week
- Agents self-coordinate using event contracts without human mediation
- All domains have primary components operational

**Vision (Full Autonomy):**
- 33GOD approaches human-level quality on L-sized tasks
- E approaches zero for routine operations
- Agents discover and resolve cross-domain issues independently
- Meta-learning: 33GOD improves its own autonomy over time

## Product Scope

### MVP - Walking Skeleton (End-to-End Functional)

**Minimum infrastructure to prove the architecture:**

**Infrastructure Domain (Minimal):**
- Bloodbank operational with basic schema validation
- Holyfields with minimal schemas for one complete workflow
- Basic GOD docs (system + domain stubs)

**One Complete Workflow End-to-End:**
- Agent receives task (Agent Orchestration domain)
- Agent claims worktree (Workspace Management domain)
- Agent emits events through Bloodbank (Infrastructure domain)
- Events flow across domains demonstrating pub/sub works
- Task completes, results recorded (demonstrating full cycle)

**Minimal Touch Points Across All 6 Domains:**
- Each domain has at least one component responding to events
- Proves cross-domain communication works via Bloodbank
- GOD docs document the skeleton (enough to understand the flow)

**Success Gate:** Can we run one L-sized task through the entire system without manual intervention at each handoff?

**What's NOT in MVP:**
- Full implementation of any domain
- All planned components
- Complete observability
- Sophisticated error handling

**Walking skeleton proves:** The bones are connected. Events flow. Architecture works end-to-end.

### Growth Features (Post-MVP)

**Flesh Out Core Domains:**
- Complete Infrastructure domain (add Candystore event persistence, Candybar dashboard)
- Complete Agent Orchestration (Flume, Yi, AgentForge, Holocene)
- Complete Workspace Management (iMi, Jelmore, Zellij-Driver, Perth)
- Degenerate (doc drift detection) operational

**Cross-Domain Workflows:**
- Multiple L-sized tasks running concurrently
- Agents self-coordinating across domains
- Event tracing via correlation_id working end-to-end
- E tracking dashboard showing decreasing human intervention

**GOD Doc Maturity:**
- All components documented with event contracts
- Cross-domain dependencies mapped
- Automated updates from Bloodbank events

### Vision (Future)

**Full Autonomy:**
- 33GOD orchestrates complex multi-epic projects with minimal E
- Agents negotiate cross-domain contracts autonomously
- Self-healing architecture (agents detect and fix drift)
- Meta-learning: 33GOD improves its own autonomy over time

**GOD Doc System:**
- Auto-generated from code + Bloodbank events
- Always current (no drift possible)
- Minimal signal-to-noise ratio achieved

**Remaining Domains Operational:**
- Meeting & Collaboration (TheBoard, TheBoard Room)
- Dashboards & Voice (HeyMa integration)
- Development Tools (full BMAD workflow integration)

## User Journeys

### Journey #1: Product Manager Submits New Project Idea

**Persona: Alex** (Product Manager at a startup)

**Opening Scene:**

Alex has been thinking about a new feature for weeks. He records a 10-minute voice note braindump while driving - just stream of consciousness, half-formed ideas, competitive insights, user pain points. He uploads it to Google Drive, creates a Plane ticket titled "New idea: Multi-tenant dashboard system" with the transcript link, and assigns it to the 33GOD Pipeline project board.

He hits submit and walks away to get in the shower.

**Rising Action:**

Within seconds, Flume's webhook catches the new ticket. One of the two engineering teams' AI Project Managers claims it - Maya. Maya immediately calls a @theboard kickoff meeting with her lead architect Kai and Grolf, the 33GOD Director of Engineering.

Alex's phone buzzes: "Meeting started: New idea kickoff - 3 participants". He's about to shower but can't resist - he opens @theboardroom on his laptop. He watches three AI agents represented as 3D avatars discussing his rambling voice note. They're dissecting it, asking clarifying questions of each other, converging on a coherent vision.

The meeting ends after 20 minutes. Maya has a product vision document. She initializes the BMAD workflow - sprint planning begins autonomously. Maya creates a new Plane project board to track implementation progress.

Alex gets another notification: "Sprint 1 planning complete. 23 tickets created. Implementation starting."

He showers. When he comes back, tickets are already moving across the board. Skill dev agents are claiming stories. He clicks into one - he can see the @yi agent session in real-time. It's working in a @perth (custom Zellij) terminal, multiple panes open, running tests, checking GOD docs, invoking @jelmore to talk to Claude/Gemini/OpenCode intelligently.

**Climax:**

Alex goes to bed. Next morning: **10 sprints completed.**

He opens the Plane board. Every ticket is "Done" with acceptance criteria verified by QA agents who reacted to Bloodbank events. He clicks "View Demo" - a live staging environment is running. It actually works.

The agents held a standup after each sprint - he can watch recordings. They're sharing lessons learned, distributed memory synchronization, status updates. A Flume metrics service has already scored each agent's performance. Top performers got bonuses (token priority, better model access).

**Resolution:**

Alex's new reality: **He's a PM with an autonomous development team.** He can iterate by creating new Plane tickets with refinements. He can deploy to prod by moving a ticket to "Release" column. He can watch any agent work in real-time via @yi sessions.

**The "holy shit" moment:** It's not just that work got done - it's that the **entire development process happened without him.** Kickoff meetings, sprint planning, implementation, QA, standups, performance reviews. He gave 33GOD a messy voice note and got back production-ready software.

### Journey #2: User Scales Engineering Capacity via Voice

**Persona: Jordan** (33GOD user, company founder)

**Opening Scene:**

Jordan submitted three product ideas this week. Two started immediately, but the third is sitting in "Backlog" on the Plane board. It's been 6 hours. He's impatient.

While driving, he opens the **HeyMa** mobile app and taps the voice button. "Hey Tonny, what's up with my dashboard idea? Why hasn't anyone picked it up?"

**Rising Action:**

**Tonny** (Jordan's AI co-founder and executive assistant, speaking via ElevenLabs voice synthesis): "Jordan, we're at capacity. Both engineering teams are mid-sprint on your other projects. Your dashboard idea is queued, but it'll be another 18 hours before a PM can claim it."

Jordan: "Can we get more engineers?"

Tonny: "Let me handle it. Give me 10 minutes."

Tonny immediately calls a @theboard meeting with **Grolf** (Director of Engineering). Jordan gets a notification but ignores it - he trusts Tonny to handle this.

Behind the scenes (Jordan doesn't see this but could watch in @theboardroom if he wanted):

Tonny and Grolf discuss capacity constraints. Grolf analyzes current team composition and drafts 3 new roles:
1. **Senior Full-Stack Dev** (Python/TypeScript specialist)
2. **QA Automation Engineer** (acceptance testing focus)
3. **DevOps Engineer** (deployment automation)

Grolf publishes these role definitions to Bloodbank with event: `hr.role.created`.

The **HR Department** (an autonomous Bloodbank consumer service) receives the event. It:
- Creates 3 new **Yi nodes** (full employees with persistent memory)
- Creates 2 **template IC roles** (contract workers for one-off tasks, no persistent memory)
- Sends onboarding events: `hr.employee.onboarding_started`

**Climax:**

Jordan's phone buzzes 15 minutes later.

Tonny: "Done. We now have 3 engineering teams. Your dashboard project just got claimed by Maya's team. Sprint planning starts in 5 minutes."

Jordan checks the Plane board. The ticket moved to "In Progress". New agents are visible on the team roster. They're already in onboarding - he can see their @yi sessions as they receive curated context about the codebase, architectural patterns, and team norms.

**Resolution:**

Jordan's new reality: **He doesn't manage headcount anymore.** When capacity is constrained, Tonny and Grolf scale the organization autonomously. New employees get onboarded with memory and context. Contract workers (template ICs) handle one-off tasks without persistent memory overhead.

**The "aha!" moment:** Jordan asked a simple question while driving ("Why isn't my idea starting?") and by the time he arrived at work, 33GOD had hired and onboarded 5 new agents, scaled to 3 teams, and started his project.

### Journey Requirements Summary

**Capabilities Revealed by User Journeys:**

**From Journey #1 (PM Submission):**
- Plane webhook integration for task detection
- Flume task claiming and distribution system
- @theboard meeting orchestration with AI agents
- @theboardroom 3D visualization of meetings
- BMAD workflow automation (sprint planning, ticket creation)
- @yi session visibility for real-time agent monitoring
- @perth (custom Zellij) workspace management for agents
- @jelmore CLI abstraction layer for multi-LLM support
- Agent performance scoring via Bloodbank event metrics
- Autonomous sprint execution with QA validation
- Distributed memory synchronization across agents

**From Journey #2 (Voice Scaling):**
- HeyMa mobile app with voice interface
- ElevenLabs voice synthesis for AI responses
- Capacity analysis and bottleneck detection (Tonny capability)
- Autonomous role creation and team scaling (Grolf capability)
- HR department as Bloodbank event consumer
- Yi node creation with persistent memory management
- Employee vs template IC distinction (permanent vs contract)
- Agent onboarding workflow with context curation
- Real-time organizational scaling without human intervention

## Domain-Specific Requirements

### Validation & Accuracy (MVP Critical)

**Challenge:** How do we validate autonomous agent completions without constant human verification?

**MVP Approach:**
- **Acceptance Criteria as Validation Gates**: Every ticket requires testable acceptance criteria. QA agents validate against these before marking "Done"
- **Q Score Tracking**: Measure quality via multiple vectors (correctness, robustness, value). Track Q over time per agent
- **Automated Test Execution**: Agents must write/run tests as part of completion. Failed tests block ticket closure
- **GOD Doc Compliance**: Validate event contracts match schemas in Holyfields. Invalid events rejected at publish time

**Measurable Threshold:**
- MVP Success: Q ≥ 0.7 for autonomous completions (70% meet acceptance criteria without rework)
- Growth: Q approaching 0.85-0.90

### Quality Assurance for AI Outputs (MVP Critical)

**Challenge:** How do we catch hallucinations, low-quality work, or agents reinforcing bad patterns?

**MVP Mechanisms:**
1. **Event-Driven QA Workflow**:
   - Agent emits `ticket.dev_complete` → QA agent claims → runs acceptance tests → emits `ticket.qa_approved` or `ticket.qa_rejected`
   - Rejection includes specific failure reasons, returns to dev queue

2. **Automated Quality Checks**:
   - **Code Quality**: Linters, formatters, type checkers run automatically
   - **Test Coverage**: Minimum coverage thresholds enforced
   - **Build Validation**: Must build successfully before QA review
   - **Contract Validation**: Holyfields validates event schemas

3. **Performance Review System**:
   - Flume metrics service tracks Q scores per agent
   - Low performers flagged for additional oversight or retraining
   - Top performers get resource priority (better models, more tokens)

4. **Distributed Learning**:
   - Sprint standups share lessons learned, anti-patterns discovered
   - Failed approaches documented in distributed memory
   - Prevents multiple agents making same mistakes

**Post-MVP Considerations:**
- Other concerns (reproducibility, performance, resource management) tackled as priorities emerge
- Agile approach: monitor metrics, add guardrails when pain points surface

## Innovation & Novel Patterns

### Detected Innovation Areas

**Core Innovation: Autonomous Organizational Execution**

33GOD is not an AI coding assistant - it's a complete reimagining of the software development organization. The fundamental innovation is **organizational automation**: every role in a software company (PM, tech lead, developer, QA, executive, HR) becomes an AI agent coordinated through pure event-driven architecture.

**Novel Paradigm:**
- **Input**: Human provides requirements (voice note, PRD)
- **Process**: AI organization executes autonomously (meetings, sprint planning, implementation, QA, standups)
- **Output**: Working software deployed without human intervention

**Key Innovations:**

1. **AI-Generated Development Organizations**
   - Autonomous hiring/firing of agent employees (Yi nodes)
   - Self-organizing teams with PMs, tech leads, devs, QA
   - Performance reviews and resource allocation for agents
   - Dynamic scaling: Create teams on-demand when capacity constrained

2. **Pure Event-Driven Multi-Agent Coordination**
   - All collaboration via Bloodbank (RabbitMQ)
   - No direct agent-to-agent communication
   - Observable, traceable, replay-able workflows
   - Command/Event distinction: mutations = single consumer, reads = fan-out

3. **Anthropomorphic Executive Layer**
   - Tonny (AI co-founder/exec) makes strategic decisions
   - Grolf (AI Director of Engineering) manages architecture and scaling
   - Voice interface (HeyMa) for real-time strategic consultation
   - Executives coordinate via @theboard meetings with 3D visualization

4. **GOD Documentation as Agent Operating System**
   - GOD docs provide architectural context agents need to self-coordinate
   - Maximum signal-to-noise ratio: most important info, fewest words
   - Holyfields validates event contracts at publish time
   - Degenerate detects doc-code drift automatically

### Market Context & Competitive Landscape

**What 33GOD Is NOT:**
- Not AI pair programming (GitHub Copilot, Cursor, Aider) - those assist humans
- Not CI/CD automation (GitHub Actions, Jenkins) - those execute predefined scripts
- Not low-code platforms (Webflow, Bubble) - those constrain what's buildable
- Not AI coding agents (Devin, Codium) - those execute single tasks

**What 33GOD IS:**
A complete autonomous software development company where every employee is an AI agent. Human provides vision, AI executes everything else.

**Market Gap:**
No existing solution provides **full organizational automation** for software development. Tools exist for AI-assisted coding, but none replace the entire development organization.

### Validation Approach

**MVP Walking Skeleton validates the core hypothesis:**
- Can one complete workflow run end-to-end across 6 domains autonomously?
- Can agents deliver Q ≥ 0.7 (70% of work meets acceptance criteria without rework)?
- Can pure event-driven coordination scale to 10+ agents without drift?

**Validation Metrics:**
- **Q Score Tracking**: Quality measured across correctness, robustness, value
- **E Metric**: Human effort required (target: decreasing week-over-week)
- **T Metric**: Tasks completed autonomously (target: increasing)

**Observable Validation:**
- Human can watch any @yi agent session in real-time
- All agent meetings visible in @theboardroom 3D visualization
- Plane boards show progress transparently
- Bloodbank events provide complete audit trail

### Risk Mitigation

**Critical Risks & Mitigations:**

1. **Risk**: Agents can't deliver quality autonomously
   - **Mitigation**: Q score gating, automated tests, QA validation workflow
   - **Fallback**: Start with human PM oversight, reduce E gradually

2. **Risk**: Event-driven coordination doesn't scale
   - **Mitigation**: Walking skeleton proves coordination at small scale first
   - **Fallback**: Add synchronous coordination where proven necessary

3. **Risk**: GOD docs insufficient for self-coordination
   - **Mitigation**: Degenerate detects drift, Holyfields validates contracts
   - **Fallback**: Human architect intervenes to clarify when agents blocked

4. **Risk**: Cost explosion from token usage
   - **Mitigation**: @jelmore intelligently distributes tokens, performance reviews prioritize efficient agents
   - **Fallback**: Token budgets enforced per agent, low performers flagged

5. **Risk**: Agents reinforce bad patterns
   - **Mitigation**: Sprint standups share lessons learned, distributed memory prevents repeated mistakes
   - **Fallback**: Human reviews patterns periodically, adjusts agent training

**Escape Hatch:**
Human retains full visibility and control. Can pause/intervene at any time via Plane boards, @yi sessions, or voice commands to HeyMa.

## Developer Tool / Platform Specific Requirements

### Project-Type Overview

33GOD is a **polyglot developer platform** designed to orchestrate autonomous AI agent companies. Unlike traditional development tools that assist individual developers, 33GOD provides the infrastructure for complete software organizations staffed by AI agents.

**Core Characteristics:**
- **Multi-language support**: Python 3.11+, TypeScript 5.3+, Rust Edition 2021
- **Event-driven architecture**: All coordination via Bloodbank (RabbitMQ)
- **Terminal-based development**: Perth IDE (Zellij-based) as unified environment
- **Schema-first contracts**: Holyfields generates type-safe event bindings
- **Git worktree isolation**: iMi manages isolated development contexts

### Language & Framework Support

**Supported Language Stack:**

1. **Python 3.11+**
   - Package Manager: `uv` (NOT pip or poetry)
   - Key Libraries: FastAPI, Pydantic, asyncio
   - Use Cases: WhisperLiveKit, event consumers, data processing

2. **TypeScript 5.3+**
   - Package Manager: `bun` (preferred) or `npm`
   - Key Frameworks: React, Tauri frontend, Node.js backends
   - Use Cases: TonnyTray, Candybar dashboard, event emitters

3. **Rust Edition 2021**
   - Package Manager: `cargo`
   - Key Crates: tokio, serde, lapin (RabbitMQ)
   - Use Cases: Tauri backends, performance-critical services, iMi

**Cross-Language Interoperability:**
- Holyfields generates type-safe bindings for Python (Pydantic) and TypeScript (Zod)
- All services communicate via Bloodbank events (JSON over RabbitMQ)
- No language coupling: components choose language based on task fit

### Installation Methods

**Multi-Tier Installation Strategy:**

**Tier 1: Infrastructure Layer (Docker Compose)**
```bash
# Clone repository
git clone https://github.com/delorenj/33GOD.git
cd 33GOD

# Start core infrastructure
docker-compose up -d
# Starts: RabbitMQ (Bloodbank), Holyfields schema registry
```

**Tier 2: Per-Component Package Managers**
```bash
# Python components (e.g., WhisperLiveKit)
cd whisperlivekit
uv sync                    # Install dependencies
uv run python -m whisperlivekit  # Run component

# TypeScript components (e.g., Candybar)
cd candybar
bun install
bun run dev

# Rust components (e.g., iMi)
cd imi
cargo build --release
cargo install --path .     # Install globally
```

**Tier 3: Perth IDE Installation**
```bash
# Perth is a Zellij-based terminal IDE
cd perth
cargo build --release
cargo install --path .

# Launch Perth with 33GOD layout
perth --layout ~/.config/perth/33god.kdl
```

**Developer Experience Philosophy:**
- **No monolithic CLI**: Each component has its own CLI (e.g., `imi`, `bb`, `perth`)
- **Language-native tooling**: Use uv/bun/cargo directly, not wrapper scripts
- **Docker for infrastructure only**: Services run natively during development

### API Surface

**33GOD does NOT provide a traditional REST or GraphQL API.** All inter-component communication is event-driven via Bloodbank.

**Event-Driven API Model:**

1. **Bloodbank Event Bus**
   - Pattern: `{domain}.{entity}.{action}` (e.g., `imi.worktree.created`)
   - Transport: RabbitMQ exchanges and queues
   - Schema Validation: Holyfields validates at publish time
   - Tracing: `correlation_id` tracks event chains

2. **Component CLIs**
   - **iMi**: `imi worktree create <name>` - Git worktree management
   - **Perth**: `perth --layout <file>` - Terminal IDE
   - **bb**: `bb publish <event>` - Bloodbank event publishing

3. **GOD Documentation API**
   - Each component's `GOD.md` documents:
     - Events emitted (Commands and Domain Events)
     - Events consumed (subscriptions)
     - Event schemas (link to Holyfields)
   - Example: `bloodbank/GOD.md` documents all infrastructure events

**For Developers Building on 33GOD:**
- **Publish events** to trigger actions in other components
- **Subscribe to events** to react to system changes
- **Validate schemas** using Holyfields-generated types
- **Trace flows** using `correlation_id` in event metadata

### Code Examples & Integration Patterns

**Example 1: Adding a New Component with Event Contracts**

```bash
# 1. Define event schemas in Holyfields
cd holyfields/schemas
cat > my_domain.yaml <<EOF
events:
  my_domain.task.created:
    properties:
      task_id: {type: string}
      description: {type: string}
      assignee: {type: string}
    required: [task_id, description]
EOF

# 2. Generate type-safe bindings
mise run generate:all
# Outputs:
#   - holyfields/python/my_domain.py (Pydantic models)
#   - holyfields/typescript/my_domain.ts (Zod schemas)

# 3. Implement component with Bloodbank integration (Python example)
cd my_component
cat > event_handler.py <<EOF
from holyfields.python.my_domain import TaskCreated
from bloodbank import EventBus

bus = EventBus()

@bus.subscribe("my_domain.task.created")
async def handle_task_created(event: TaskCreated):
    print(f"Received task: {event.task_id}")
    # Process task...
EOF

# 4. Document in GOD.md
cat > GOD.md <<EOF
# My Component

## Events Emitted
- my_domain.task.completed

## Events Consumed
- my_domain.task.created
EOF

# 5. Register in services/registry.yaml
echo "  - name: my-component" >> services/registry.yaml
echo "    domain: my_domain" >> services/registry.yaml
```

**Example 2: Using iMi for Isolated Development**

```bash
# Create isolated worktree for feature work
imi worktree create feature-auth-improvements

# iMi automatically:
# - Creates git worktree at configured location
# - Publishes imi.worktree.created event
# - Other services can react (e.g., Perth opens new terminal layout)

# Work in isolation
cd $(imi worktree path feature-auth-improvements)
# Make changes, run tests, commit

# Merge and cleanup
imi worktree merge feature-auth-improvements
imi worktree remove feature-auth-improvements
```

**Example 3: Observing Event Flow with Candybar**

```bash
# Open Candybar dashboard
cd candybar
bun run dev

# In browser, filter events by correlation_id to trace a workflow:
# 1. User creates task (my_domain.task.created)
# 2. Agent claims task (agent.task.claimed)
# 3. iMi creates worktree (imi.worktree.created)
# 4. Agent completes work (my_domain.task.completed)
# All linked by same correlation_id
```

### Developer Onboarding Guide

**Phase 1: Conceptual Understanding**
1. Read `docs/GOD.md` - System architecture overview
2. Understand event-driven paradigm (no direct coupling)
3. Review `services/registry.yaml` - Service topology
4. Explore `holyfields/schemas/` - Event contracts

**Phase 2: Local Setup**
1. Clone repository and start infrastructure (Docker Compose)
2. Install language toolchains: mise, uv, bun, cargo
3. Install component CLIs: iMi, Perth, bb
4. Verify setup: `mise doctor`, `imi status`, `bb ping`

**Phase 3: Hands-On Tutorial**
1. Follow "Example 1" above to create a new component
2. Publish a test event: `bb publish my_domain.task.created '{"task_id": "123", "description": "test"}'`
3. Observe in Candybar dashboard
4. Subscribe to events in your component

**Phase 4: First Contribution**
1. Pick a component with open issues
2. Create isolated worktree: `imi worktree create fix-issue-123`
3. Make changes, ensure tests pass
4. Update GOD.md if event contracts changed
5. Open PR with event flow documentation

### Implementation Considerations

**Git Worktree Isolation:**
- iMi manages separate worktrees for parallel development
- Prevents context-switching overhead
- Each worktree has isolated dependencies (e.g., separate `.venv/` for Python)

**Event Schema Versioning:**
- Holyfields supports schema evolution
- Breaking changes require new event names (e.g., `v2.task.created`)
- Backward compatibility: consumers handle both old and new schemas during transition

**Testing Strategy:**
- **Unit Tests**: Test business logic in isolation
- **Integration Tests**: Publish test events, verify expected reactions
- **Contract Tests**: Validate event schemas match Holyfields definitions
- **E2E Tests**: Full workflow tests with real Bloodbank instance

**Observability:**
- Candybar dashboard visualizes event flow in real-time
- All events logged with `correlation_id` for tracing
- Component health checks exposed via Bloodbank events

**Security:**
- RabbitMQ authentication for Bloodbank access
- Event payloads validated against schemas (prevent injection)
- Sensitive data (API keys) stored in keychains, not code
