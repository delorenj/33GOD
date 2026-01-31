# AgentForge - Technical Implementation Guide

## Overview

AgentForge is a meta-agent system built on the Agno framework that automatically analyzes high-level goals, scouts existing agent libraries, creates specialized agents to fill gaps, and assembles complete ready-to-deploy agent teams. It operates as a 5-agent meta-team that collaborates to build other agent teams.

## Implementation Details

**Language**: Python 3.12+
**Core Framework**: Agno 2.0.2+ (multi-agent orchestration)
**Database**: SQLite (LanceDB for vector storage)
**LLM Provider**: OpenRouter, OpenAI, Anthropic
**Package Manager**: pip/uv
**MCP Server**: Model Context Protocol integration for Claude Code/Cline

### Key Technologies

- **Agno**: Core agent framework with workflows
- **FastAPI**: MCP server implementation
- **LanceDB**: Vector database for semantic agent matching
- **Pydantic**: Type-safe data validation
- **SQLAlchemy**: Database ORM for team persistence
- **OpenRouter**: Multi-provider LLM access

## Architecture & Design Patterns

### Meta-Team Architecture

```
┌─────────────────────────────────────────────────┐
│          Engineering Manager                    │
│          (Central Orchestrator)                 │
└──────────────┬──────────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┬────────────┐
    │          │          │          │            │
┌───▼────┐ ┌──▼────┐ ┌───▼───┐ ┌────▼────┐ ┌─────▼──────┐
│Systems │ │Talent │ │Agent  │ │Integration│ │Delivery   │
│Analyst │ │Scout  │ │Developer│ │Architect │ │Manager    │
└────────┘ └───────┘ └────────┘ └──────────┘ └────────────┘
```

### Agent Roles

**1. Engineering Manager** (Orchestrator):
```python
from agno import Agent, InputSchema, OutputSchema

class InputGoal(InputSchema):
    goal_description: str
    domain: str
    complexity_level: str
    constraints: List[str] = []
    success_criteria: List[str] = []

class TeamRoster(OutputSchema):
    team_members: List[Agent]
    roster_documentation: str
    deployment_guide: str

class EngineeringManager(Agent[InputGoal, TeamRoster]):
    async def process(self, goal: InputGoal) -> TeamRoster:
        # 1. Systems analysis
        strategy = await self.systems_analyst.analyze(goal)

        # 2. Scout existing agents
        scout_report = await self.talent_scout.find_agents(strategy)

        # 3. Create new agents for gaps
        new_agents = await self.agent_developer.create_agents(
            scout_report.gaps
        )

        # 4. Assemble final team
        roster = await self.integration_architect.assemble_team(
            existing=scout_report.matched_agents,
            new=new_agents,
            strategy=strategy
        )

        return roster
```

**2. Systems Analyst** (Strategist):
```python
class SystemsAnalyst(Agent):
    async def analyze(self, goal: InputGoal) -> TeamStrategy:
        """Decomposes goal into capabilities and roles"""
        prompt = f"""
        Analyze this goal and identify required agent capabilities:

        Goal: {goal.goal_description}
        Domain: {goal.domain}
        Complexity: {goal.complexity_level}

        Output:
        1. Required capabilities (list)
        2. Recommended team structure
        3. Inter-agent communication patterns
        4. Success metrics
        """

        result = await self.llm.generate(prompt)

        return TeamStrategy(
            capabilities=result.capabilities,
            team_structure=result.structure,
            communication_patterns=result.patterns,
            metrics=result.metrics
        )
```

**3. Talent Scout** (Librarian):
```python
class TalentScout(Agent):
    def __init__(self):
        self.agent_library = LanceDB("agents.db")

    async def find_agents(self, strategy: TeamStrategy) -> ScoutReport:
        """Searches agent library for reusable agents"""
        matches = []
        gaps = []

        for capability in strategy.capabilities:
            # Semantic search using embeddings
            candidates = await self.agent_library.search(
                query=capability,
                k=5,
                threshold=0.8
            )

            if candidates:
                matches.append({
                    "capability": capability,
                    "agents": candidates,
                    "fit_score": candidates[0].similarity
                })
            else:
                gaps.append(capability)

        return ScoutReport(
            matched_agents=matches,
            gaps=gaps,
            recommendations="..."
        )
```

**4. Agent Developer** (Creator):
```python
class AgentDeveloper(Agent):
    async def create_agents(self, gaps: List[str]) -> List[Agent]:
        """Creates new specialized agents for identified gaps"""
        new_agents = []

        for capability in gaps:
            agent_spec = await self.llm.generate(f"""
            Create an agent specification for: {capability}

            Output:
            - Agent name
            - System prompt
            - Input/output schemas
            - Tool requirements
            - Best practices
            """)

            # Generate agent code
            agent_code = await self.llm.generate(f"""
            Generate Python code for agent:
            {agent_spec}

            Follow Agno framework patterns.
            """)

            # Save and validate
            agent_path = f"agents/{capability}.py"
            with open(agent_path, 'w') as f:
                f.write(agent_code)

            new_agents.append({
                "capability": capability,
                "path": agent_path,
                "spec": agent_spec
            })

        return new_agents
```

**5. Integration Architect** (Coordinator):
```python
class IntegrationArchitect(Agent):
    async def assemble_team(
        self,
        existing: List[Agent],
        new: List[Agent],
        strategy: TeamStrategy
    ) -> TeamRoster:
        """Assembles final team with workflows and docs"""

        # Define agent collaboration workflows
        workflows = await self.define_workflows(
            agents=existing + new,
            patterns=strategy.communication_patterns
        )

        # Create deployment documentation
        deployment_guide = await self.llm.generate(f"""
        Create deployment guide for team:
        - Existing agents: {[a.name for a in existing]}
        - New agents: {[a["capability"] for a in new]}
        - Workflows: {workflows}

        Include:
        1. Setup instructions
        2. Configuration
        3. Execution examples
        4. Troubleshooting
        """)

        return TeamRoster(
            team_members=existing + new,
            workflows=workflows,
            roster_documentation=strategy.as_markdown(),
            deployment_guide=deployment_guide
        )
```

### MCP Server Integration

```python
# mcp_server/team_server.py
from mcp import MCPServer
from agentforge import EngineeringManager

server = MCPServer("agentforge-team")

@server.tool("agentforge_create_team")
async def create_team(
    goal_description: str,
    domain: str = "general",
    complexity: str = "medium"
) -> dict:
    """Full team creation workflow"""
    em = EngineeringManager()

    goal = InputGoal(
        goal_description=goal_description,
        domain=domain,
        complexity_level=complexity
    )

    roster = await em.process(goal)

    return {
        "team_size": len(roster.team_members),
        "team_members": [a.name for a in roster.team_members],
        "documentation": roster.roster_documentation,
        "deployment_guide": roster.deployment_guide
    }

@server.tool("agentforge_scout_agents")
async def scout_agents(capability: str) -> dict:
    """Search agent library for specific capability"""
    scout = TalentScout()

    results = await scout.agent_library.search(
        query=capability,
        k=10
    )

    return {
        "matches": [
            {
                "name": r.name,
                "similarity": r.similarity,
                "capabilities": r.capabilities
            }
            for r in results
        ]
    }
```

## Configuration

### Environment Variables

```bash
# LLM Provider
OPENROUTER_API_KEY=your_key
OPENAI_API_KEY=your_key  # Alternative
ANTHROPIC_API_KEY=your_key  # Alternative

# Agent Library Paths
AGENT_LIBRARY_PATH=/path/to/agents
TEAMS_LIBRARY_PATH=/path/to/teams

# Database
DATABASE_URL=sqlite:///agentforge.db

# MCP API (optional)
MCP_API_KEY=your_mcp_key
```

### Agent Library Structure

```
agents/
├── web-development/
│   ├── frontend-developer.py
│   ├── backend-developer.py
│   └── database-architect.py
├── data-science/
│   ├── data-engineer.py
│   ├── ml-engineer.py
│   └── model-validator.py
└── content/
    ├── content-strategist.py
    ├── copywriter.py
    └── social-media-manager.py
```

## Integration Points

### Claude Code Usage

```bash
# In Claude Code/Cline chat:
"Create a team to build a real-time chat application"

# AgentForge MCP tool is invoked automatically:
# - Analyzes requirements
# - Scouts existing agents
# - Creates missing agents
# - Returns complete team specification
```

### Programmatic Usage

```python
from agentforge import EngineeringManager, InputGoal

async def create_team():
    em = EngineeringManager()

    goal = InputGoal(
        goal_description="Build a customer support chatbot",
        domain="customer service",
        complexity_level="medium",
        constraints=["Must integrate with existing CRM"],
        success_criteria=["80%+ query automation", "<30s response time"]
    )

    roster = await em.process(goal)

    print(f"Created team with {len(roster.team_members)} agents:")
    for agent in roster.team_members:
        print(f"  - {agent.name}: {agent.expertise}")

    # Save team for deployment
    with open("team_roster.md", "w") as f:
        f.write(roster.roster_documentation)
```

## Performance Characteristics

- **Team Generation**: 30-120 seconds (depends on complexity)
- **Agent Library Search**: <1 second (vector database)
- **New Agent Creation**: 10-30 seconds per agent
- **Memory Usage**: 100-500 MB (depends on library size)

## Related Components

- **Holocene**: Dashboard displays AgentForge teams
- **iMi**: Spawns agents into dedicated worktrees
- **Bloodbank**: Event bus for team coordination

---

**Quick Reference**:
- GitHub: `33GOD/agent-forge`
- MCP Tools: `agentforge_create_team`, `agentforge_scout_agents`
- Docs: `SYSTEM_ARCHITECTURE.md`, `docs/MCP_SERVER_GUIDE.md`
