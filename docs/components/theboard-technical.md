# TheBoard - Technical Implementation Guide

## Overview

TheBoard is a sophisticated multi-agent brainstorming simulation system built on the Agno framework. It orchestrates specialized AI agents through structured meeting workflows, featuring intelligent comment extraction, context compression, convergence detection, and event-driven architecture. Version 2.1.0 is production-ready with PostgreSQL persistence, Redis caching, and RabbitMQ integration.

## Implementation Details

**Language**: Python 3.12+
**Core Framework**: Typer (CLI), Rich (terminal UI)
**Agent Framework**: Agno 2.0+ (multi-agent orchestration)
**Database**: PostgreSQL 16 with SQLAlchemy 2.0 (async ORM)
**Caching**: Redis 7 (session management, preferences)
**Message Queue**: RabbitMQ 3.12 (event bus integration)
**Vector Database**: Qdrant (embedding-based novelty detection)
**Package Manager**: uv (ultra-fast Python dependency manager)

### Key Technologies

- **Typer**: Type-safe CLI framework with argument parsing
- **Rich**: Terminal UI, tables, progress bars, syntax highlighting
- **Agno**: Multi-agent framework for LLM orchestration
- **Letta**: Cross-meeting memory and agent persistence
- **OpenRouter**: Unified LLM API (Claude, GPT, DeepSeek)
- **sentence-transformers**: Embedding generation for semantic clustering
- **NetworkX**: Graph-based clustering for context compression
- **Pydantic**: Data validation and serialization

## Architecture & Design Patterns

### Multi-Layer Service Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     CLI Layer                          │
│  (Typer commands, Rich formatting, user interaction)  │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│                  Service Layer                         │
│  (MeetingService, AgentService, EmbeddingService,     │
│   ExportService, CostEstimationService)               │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│                 Workflow Layer                         │
│  (SimpleMeetingWorkflow - agent orchestration,        │
│   CompressorWorkflow - context optimization)          │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│                  Agent Layer                           │
│  (DomainExpertAgent, NotetakerAgent,                  │
│   CompressorAgent, LettaAgent)                        │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│                  Data Layer                            │
│  (SQLAlchemy models: Meeting, Agent, Response,        │
│   Comment, Round with Alembic migrations)             │
└─────────────────────────────────────────────────────────┘
```

### Event-Driven Architecture

TheBoard integrates with Bloodbank (RabbitMQ) for distributed coordination:

```python
# src/theboard/events/emitter.py
class RabbitMQEventEmitter(EventEmitter):
    """Emit events to Bloodbank event bus"""

    async def emit(self, event: Event) -> None:
        envelope = EventEnvelope(
            id=str(uuid4()),
            event_type=event.type,
            source="theboard",
            timestamp=datetime.utcnow(),
            data=event.payload,
            session_id=event.session_id,
            correlation_id=event.correlation_id
        )

        await self.publisher.publish(
            routing_key=event.type,
            body=envelope.model_dump(),
            message_id=envelope.id
        )
```

**Event Types**:
- `theboard.meeting.created`
- `theboard.meeting.started`
- `theboard.meeting.round_completed`
- `theboard.meeting.comment_extracted`
- `theboard.meeting.converged`
- `theboard.meeting.completed`
- `theboard.meeting.failed`

### Session Management Pattern

**CRITICAL RULE**: Never hold database sessions open during LLM calls to prevent connection pool exhaustion.

```python
# ✓ CORRECT: Short-lived sessions
from theboard.database import get_sync_db

def execute_agent_turn(meeting_id: str, agent_name: str):
    # Short session to fetch data
    with get_sync_db() as db:
        meeting = db.query(Meeting).filter_by(id=meeting_id).first()
        topic = meeting.topic
        context = meeting.accumulated_context
        # Session closes here - connection returned to pool

    # LLM call WITHOUT database session (can take 5-30 seconds)
    agent = DomainExpertAgent(name=agent_name, model="anthropic/claude-sonnet-4")
    result = agent.run(topic, context)  # Long-running, non-blocking

    # New session for storing results
    with get_sync_db() as db:
        response = Response(
            meeting_id=meeting_id,
            agent_id=agent_name,
            content=result.content,
            token_count=result.token_count
        )
        db.add(response)
        db.commit()
```

### Three-Tier Context Compression

When context exceeds ~10K characters, automatic compression is triggered:

```python
# src/theboard/workflows/compressor.py
class CompressorWorkflow:
    """Three-tier compression strategy"""

    async def compress(self, comments: List[Comment]) -> List[Comment]:
        # Tier 1: Graph-based clustering
        embeddings = self.embedding_service.generate_embeddings(comments)
        clusters = self.graph_cluster(embeddings, threshold=0.8)

        # Tier 2: LLM semantic merge
        merged_comments = []
        for cluster in clusters:
            if len(cluster) == 1:
                merged_comments.append(cluster[0])  # Skip singletons
            else:
                merged = await self.compressor_agent.merge_cluster(cluster)
                merged_comments.append(merged)

        # Tier 3: Outlier removal
        filtered = self.remove_low_support(
            merged_comments,
            min_support=2  # Mentioned <2 times = noise
        )

        # Mark originals as merged (audit trail)
        for comment in comments:
            comment.is_merged = True

        return filtered

    def graph_cluster(
        self,
        embeddings: List[np.ndarray],
        threshold: float
    ) -> List[List[Comment]]:
        """NetworkX community detection"""
        # Build cosine similarity graph
        G = nx.Graph()
        for i, emb_i in enumerate(embeddings):
            for j, emb_j in enumerate(embeddings[i+1:], start=i+1):
                similarity = cosine_similarity(emb_i, emb_j)
                if similarity > threshold:
                    G.add_edge(i, j, weight=similarity)

        # Detect communities
        communities = nx.community.greedy_modularity_communities(G)

        # Map back to comments
        return [
            [comments[idx] for idx in community]
            for community in communities
        ]
```

**Compression Results**:
- 40-60% token reduction
- Quality preservation (semantic meaning intact)
- Audit trail (original comments preserved with `is_merged=True`)

### Delta Context Propagation

Agents only receive comments from rounds they haven't seen:

```python
# src/theboard/workflows/simple_meeting.py
def build_agent_context(
    agent: Agent,
    all_comments: List[Comment]
) -> str:
    """Build context with only new comments since agent's last turn"""

    # Filter to comments from rounds after agent's last participation
    last_round = agent.agent_last_seen_round or 0
    new_comments = [
        c for c in all_comments
        if c.round_number > last_round
    ]

    # Update agent's last seen round
    agent.agent_last_seen_round = max(
        c.round_number for c in all_comments
    )

    # Format context
    context = "\\n\\n".join([
        f"[{c.category.upper()}] ({c.agent_name}): {c.content}"
        for c in new_comments
    ])

    return context
```

**Token Savings**: 40-60% reduction in multi-round meetings (agents skip redundant context)

### Hybrid Model Strategy

Automatic model selection based on task complexity reduces costs by 60%:

```python
# src/theboard/config/preferences.py
class ModelSelection:
    """Hierarchical model resolution"""

    TASK_COMPLEXITY_MAP = {
        "domain_expert": "high",      # Use best model (Claude Sonnet 4)
        "notetaker": "medium",         # Use mid-tier (Haiku)
        "compressor": "medium",        # Use mid-tier
        "convergence_check": "low",    # Use cheap model
    }

    MODEL_TIERS = {
        "high": "anthropic/claude-sonnet-4",
        "medium": "anthropic/claude-haiku",
        "low": "deepseek/deepseek-v3.1",
    }

    def get_model_for_agent(
        self,
        agent_role: str,
        cli_override: Optional[str] = None,
        meeting_override: Optional[str] = None,
    ) -> str:
        """Resolve model with precedence hierarchy"""

        # 1. CLI argument (highest priority)
        if cli_override:
            return cli_override

        # 2. Meeting-level override
        if meeting_override:
            return meeting_override

        # 3. Agent preferred model
        agent_pref = self.redis.get(f"agent:{agent_role}:preferred_model")
        if agent_pref:
            return agent_pref

        # 4. User preferences (from config)
        user_pref = self.config.get("default_model")
        if user_pref:
            return user_pref

        # 5. Task complexity mapping
        complexity = self.TASK_COMPLEXITY_MAP.get(agent_role, "medium")
        return self.MODEL_TIERS[complexity]
```

### Convergence Detection

Automatic meeting termination when novelty drops below threshold:

```python
# src/theboard/services/convergence.py
class ConvergenceDetector:
    """Embedding-based novelty detection"""

    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold
        self.embedding_service = EmbeddingService()

    async def check_convergence(
        self,
        current_comments: List[Comment],
        all_comments: List[Comment]
    ) -> ConvergenceResult:
        """Check if meeting has converged"""

        # Generate embeddings for current round
        current_embeds = self.embedding_service.generate_embeddings(
            [c.content for c in current_comments]
        )

        # Generate embeddings for historical comments
        historical_embeds = self.embedding_service.generate_embeddings(
            [c.content for c in all_comments if c not in current_comments]
        )

        # Calculate novelty scores
        novelty_scores = []
        for curr_emb in current_embeds:
            max_similarity = max(
                cosine_similarity(curr_emb, hist_emb)
                for hist_emb in historical_embeds
            )
            novelty = 1.0 - max_similarity
            novelty_scores.append(novelty)

        avg_novelty = np.mean(novelty_scores)

        return ConvergenceResult(
            has_converged=avg_novelty < self.threshold,
            novelty_score=avg_novelty,
            threshold=self.threshold,
            recommendation="continue" if avg_novelty >= self.threshold else "stop"
        )
```

## Configuration

### Environment Variables

```bash
# Database (custom port to avoid conflicts)
DATABASE_URL=postgresql://user:password@localhost:5433/theboard

# Redis (custom port)
REDIS_URL=redis://localhost:6380/0

# RabbitMQ (custom port)
RABBITMQ_URL=amqp://guest:guest@localhost:5673/

# Qdrant vector database
QDRANT_HOST=localhost
QDRANT_PORT=6333

# LLM provider
OPENROUTER_API_KEY=your_key_here

# Event emitter (rabbitmq, inmemory, or null)
THEBOARD_EVENT_EMITTER=rabbitmq

# Logging
LOG_LEVEL=INFO
DEBUG=false
```

### User Configuration File

```yaml
# ~/.config/theboard/config.yml
# Auto-generated on first run

default_model: anthropic/claude-sonnet-4
default_strategy: sequential
default_max_rounds: 5
default_agent_count: 5

event_emitter: rabbitmq

compression:
  enabled: true
  threshold: 10000  # characters
  similarity_threshold: 0.8

convergence:
  enabled: true
  novelty_threshold: 0.3

cost_estimation:
  enabled: true
  warn_threshold: 5.0  # USD
```

### Docker Compose Services

```yaml
# compose.yml
services:
  postgres:
    image: postgres:16
    ports:
      - "5433:5432"  # Custom port
    environment:
      POSTGRES_USER: theboard
      POSTGRES_PASSWORD: theboard
      POSTGRES_DB: theboard
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6380:6379"  # Custom port
    volumes:
      - redis_data:/data

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5673:5672"   # AMQP port (custom)
      - "15673:15672" # Management UI (custom)
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"  # HTTP API
      - "6334:6334"  # gRPC
    volumes:
      - qdrant_data:/qdrant/storage

  theboard:
    build: .
    depends_on:
      - postgres
      - redis
      - rabbitmq
      - qdrant
    environment:
      DATABASE_URL: postgresql://theboard:theboard@postgres:5432/theboard
      REDIS_URL: redis://redis:6379/0
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
      QDRANT_HOST: qdrant
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
```

## Integration Points

### CLI Usage

```bash
# Create meeting (wizard mode)
uv run board wizard create

# Create meeting (direct)
uv run board create \\
  --topic "API design: REST vs GraphQL" \\
  --max-rounds 5 \\
  --strategy sequential \\
  --agent-count 5

# Run meeting
uv run board run <meeting-id>

# Run with model override
uv run board run <meeting-id> --model anthropic/claude-opus-4

# Interactive mode (human-in-the-loop)
uv run board run <meeting-id> --interactive

# Check status
uv run board status <meeting-id>

# Export results
uv run board export <meeting-id> --format markdown --output report.md
```

### Programmatic Usage

```python
from theboard.services import MeetingService
from theboard.database import get_sync_db

# Create meeting
with get_sync_db() as db:
    service = MeetingService(db)
    meeting = service.create_meeting(
        topic="How can we optimize database queries?",
        strategy="sequential",
        max_rounds=3,
        agent_count=5
    )

# Execute meeting
from theboard.workflows import SimpleMeetingWorkflow

workflow = SimpleMeetingWorkflow(meeting_id=meeting.id)
workflow.execute()

# Query results
with get_sync_db() as db:
    service = MeetingService(db)
    comments = service.get_comments(meeting.id)

    for comment in comments:
        print(f"[{comment.category}] {comment.agent_name}: {comment.content}")
```

### Event Consumption

```python
# Subscribe to TheBoard events via Bloodbank
from bloodbank import Subscriber
import asyncio

async def handle_meeting_event(message):
    event_type = message["event_type"]

    if event_type == "theboard.meeting.created":
        meeting_id = message["data"]["meeting_id"]
        print(f"New meeting created: {meeting_id}")

    elif event_type == "theboard.meeting.comment_extracted":
        comment = message["data"]["comment"]
        print(f"Comment: [{comment['category']}] {comment['content']}")

subscriber = Subscriber(binding_key="theboard.meeting.*")
asyncio.run(subscriber.start(callback=handle_meeting_event))
```

## Performance Characteristics

### Latency Benchmarks

- **Meeting Creation**: <500ms
- **Single Agent Turn**: 5-30 seconds (LLM-dependent)
- **Notetaker Extraction**: 3-10 seconds
- **Context Compression**: 2-5 seconds
- **Convergence Check**: 1-2 seconds
- **Full 5-Round Meeting**: 2-5 minutes

### Token Usage

- **Without Optimization**: ~50K tokens per 5-round meeting
- **With Delta Propagation**: ~30K tokens (40% savings)
- **With Compression**: ~20K tokens (60% total savings)

### Cost Estimation

```python
# Approximate costs (Claude Sonnet 4 pricing)
PRICING_TABLE = {
    "anthropic/claude-sonnet-4": {
        "input": 0.003 / 1000,   # $3 per 1M tokens
        "output": 0.015 / 1000,  # $15 per 1M tokens
    },
    "anthropic/claude-haiku": {
        "input": 0.00025 / 1000,
        "output": 0.00125 / 1000,
    },
}

# Typical 5-round meeting with hybrid strategy:
# - Domain Experts: 15K input, 5K output (Sonnet 4) = $0.12
# - Notetaker: 8K input, 2K output (Haiku) = $0.005
# - Compressor: 5K input, 2K output (Haiku) = $0.003
# Total: ~$0.13 per meeting
```

## Edge Cases & Troubleshooting

### Database Connection Pool Exhaustion

**Problem**: Long-running LLM calls block database connections
**Solution**: Short-lived session pattern (see "Session Management" above)

### Convergence False Positives

**Problem**: Meeting stops prematurely due to low novelty
**Solution**: Adjust threshold or use manual `--max-rounds`

```bash
# Lower threshold for more lenient convergence
uv run board create --topic "..." --convergence-threshold 0.2

# Disable convergence entirely
uv run board create --topic "..." --disable-convergence
```

### Event Emission Failures

**Problem**: RabbitMQ unavailable, events not published
**Solution**: Graceful degradation with null emitter

```yaml
# config.yml
event_emitter: null  # Disable event publishing
```

### Memory Leaks in Long Meetings

**Problem**: Embeddings accumulate in memory
**Solution**: Batch processing and cleanup

```python
# Clear embedding cache after each round
self.embedding_service.clear_cache()

# Use batch processing for large comment sets
for batch in chunk_list(comments, size=50):
    embeddings = self.embedding_service.generate_embeddings(batch)
    process_batch(embeddings)
```

## Code Examples

### Custom Agent Pool

```yaml
# data/agents/custom_pool.yaml
agents:
  - name: Security Architect
    expertise: security, authentication, encryption
    persona: Paranoid about vulnerabilities, insists on defense-in-depth
    preferred_model: anthropic/claude-sonnet-4

  - name: Performance Engineer
    expertise: optimization, profiling, scalability
    persona: Obsessed with latency and throughput
    preferred_model: anthropic/claude-haiku

  - name: UX Researcher
    expertise: user experience, accessibility, usability
    persona: Advocates for users, questions technical assumptions
    preferred_model: deepseek/deepseek-v3.1
```

```bash
# Seed custom agents
uv run python scripts/seed_agents.py --file data/agents/custom_pool.yaml
```

### Custom Export Template

```jinja2
{# templates/custom_report.j2 #}
# Meeting Report: {{ meeting.topic }}

**Meeting ID**: {{ meeting.id }}
**Status**: {{ meeting.status }}
**Rounds**: {{ meeting.current_round }} / {{ meeting.max_rounds }}
**Participants**: {{ agents|length }} agents

## Summary

{{ meeting.summary or "No summary available" }}

## Key Insights

{% for category in ["idea", "recommendation", "concern"] %}
### {{ category|title }}s
{% for comment in comments if comment.category == category %}
- **{{ comment.agent_name }}**: {{ comment.content }}
{% endfor %}
{% endfor %}

## Full Transcript

{% for round in range(1, meeting.current_round + 1) %}
### Round {{ round }}
{% for response in responses if response.round_number == round %}
**{{ response.agent_name }}**: {{ response.content }}

*Extracted Comments*:
{% for comment in comments if comment.response_id == response.id %}
  - [{{ comment.category }}] {{ comment.content }}
{% endfor %}
{% endfor %}
{% endfor %}

## Cost Analysis

- Total Tokens: {{ total_tokens }}
- Estimated Cost: ${{ "%.2f"|format(estimated_cost) }}

---
*Generated by TheBoard v2.1.0*
```

```bash
# Export with custom template
uv run board export <meeting-id> \\
  --format template \\
  --template custom_report.j2 \\
  --output report.md
```

## Related Components

- **Bloodbank**: Event bus for meeting lifecycle events
- **Holyfields**: Event schema definitions
- **TheBoardroom**: 3D visualization of meetings in real-time
- **Candystore**: Event storage and audit trail
- **Letta**: Cross-meeting agent memory

---

**Quick Reference**:
- GitHub: `33GOD/theboard`
- Docs: `docs/USER_GUIDE.md`, `docs/DEVELOPER.md`, `docs/TROUBLESHOOTING.md`
- CLI Help: `uv run board --help`
