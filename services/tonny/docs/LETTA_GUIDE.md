# Letta Integration Guide for Tonny Agent

## Introduction to Letta

Letta (formerly MemGPT) is a stateful agent framework that maintains conversation context across interactions. Unlike stateless LLM APIs, Letta agents:

- Remember previous conversations via session IDs
- Manage their own memory (working memory + long-term archival)
- Can use tools and functions
- Support multi-turn dialogues

**Why Letta for Tonny?**

Voice interactions benefit from memory - users expect the assistant to remember what was said earlier in the conversation. Letta provides this out-of-the-box.

## Self-Hosted vs Cloud

### Self-Hosted Letta (Recommended)

**Pros:**
- Full control over data
- No usage fees
- Lower latency
- Customize agent behavior

**Cons:**
- Requires server infrastructure
- You manage updates

**Setup:**

```bash
# Install Letta
pip install letta

# Start server
letta server

# Runs on http://localhost:8283
```

### Letta Cloud

**Pros:**
- Zero infrastructure
- Managed updates
- Built-in monitoring

**Cons:**
- Usage fees
- Data leaves your infrastructure
- Higher latency

**Setup:**

1. Sign up at https://letta.com
2. Get API key
3. Set `LETTA_BASE_URL=https://api.letta.com`
4. Set `LETTA_API_KEY=your_key`

## Letta Agent Architecture

### Memory System

Letta agents have three memory types:

1. **Working Memory (Core Memory)**
   - Persona (agent identity)
   - Human (user description)
   - Limited size (~2KB)
   - Always in context

2. **Archival Memory**
   - Long-term storage
   - Retrieved via semantic search
   - Unlimited size

3. **Recall Memory**
   - Conversation history
   - Chronological retrieval

### Message Flow

```
User Message → Letta Agent
                ↓
         Check Memory
                ↓
         LLM Processing
                ↓
         Tool Calls (if needed)
                ↓
         Update Memory
                ↓
         Return Response
```

## Configuring Tonny's Letta Agent

### Persona Design

The persona defines how Tonny behaves. Current configuration:

```python
persona = (
    "You are Tonny, a helpful voice assistant. "
    "You respond concisely and naturally to voice commands. "
    "Keep responses brief and conversational - users are speaking, not typing."
)
```

**Customization Tips:**

- **Domain expertise:** Add "You specialize in [domain]"
- **Tone:** "You are friendly and casual" vs "You are formal and professional"
- **Constraints:** "Never provide medical advice" or "Always cite sources"

Example for a developer assistant:

```python
persona = (
    "You are Tonny, a senior software engineer assistant. "
    "You provide concise technical guidance for voice interactions. "
    "Focus on practical solutions over theory. "
    "Assume the user is coding and needs quick answers."
)
```

### Human Description

Describes the user for context:

```python
human = (
    "The user is speaking to you via voice transcription. "
    "They expect quick, spoken-style responses."
)
```

Customize based on your use case:

```python
human = (
    "The user is a busy executive who uses voice commands "
    "while multitasking. They value efficiency and brevity."
)
```

### LLM Configuration

Current settings:

```python
"llm_config": {
    "model": "gpt-4.1",  # Or claude-sonnet-4.5
    "context_window": 8000,
}
```

**Model Selection:**

| Model | Speed | Quality | Cost | Best For |
|-------|-------|---------|------|----------|
| gpt-3.5-turbo | Fast | Good | Low | Quick responses |
| gpt-4.1 | Medium | Excellent | Medium | Balanced performance |
| claude-sonnet-4.5 | Medium | Excellent | Medium | Complex reasoning |
| gpt-4o | Medium | Excellent | High | Multimodal tasks |

**Recommendation:** Start with `gpt-4.1`, switch to `gpt-3.5-turbo` if latency is critical.

## Session Management

### Session IDs

Tonny uses `session_id` from transcription events to maintain conversation context:

```python
response = await agent.process_message(
    text="What's the weather?",
    session_id=uuid.UUID("session-123")
)
```

**Best Practices:**

1. **User-scoped sessions:** One session per user
2. **Conversation-scoped:** New session per conversation
3. **Time-based:** Reset session after inactivity

### Session Persistence

Letta automatically persists session state. To retrieve:

```python
# Get session history
response = await client.get(f"/api/agents/{agent_id}/sessions/{session_id}")
```

## Adding Tools to Tonny

Letta agents can call tools (functions). Example: Weather lookup

### 1. Define Tool

```python
def get_weather(location: str) -> str:
    """Get current weather for a location."""
    # API call to weather service
    return f"Weather in {location}: Sunny, 72°F"
```

### 2. Register Tool with Letta

```python
# When creating agent
agent_config = {
    "tools": [
        {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["location"]
            }
        }
    ]
}
```

### 3. Handle Tool Calls

```python
# In process_message
if "tool_calls" in result:
    for tool_call in result["tool_calls"]:
        if tool_call["name"] == "get_weather":
            weather = get_weather(tool_call["arguments"]["location"])
            # Send tool result back to agent
```

## Memory Management

### Custom Memory Blocks

Add domain-specific memory:

```python
agent_config = {
    "memory_blocks": [
        {
            "name": "user_preferences",
            "label": "User Preferences",
            "description": "User's settings and preferences",
            "value": "Preferred temperature unit: Celsius",
        },
        {
            "name": "conversation_context",
            "label": "Context",
            "description": "Current conversation context",
            "value": "",
        }
    ]
}
```

### Archival Memory

Store long-term information:

```python
# Add to archival memory
await client.post(
    f"/api/agents/{agent_id}/archival",
    json={
        "content": "User's favorite color is blue",
        "metadata": {"category": "preferences"}
    }
)

# Search archival memory
results = await client.get(
    f"/api/agents/{agent_id}/archival/search",
    params={"query": "favorite color"}
)
```

## Performance Optimization

### Reduce Latency

1. **Smaller model:** `gpt-3.5-turbo` vs `gpt-4.1`
2. **Lower context window:** 4000 vs 8000 tokens
3. **Streaming responses:** Get first tokens faster
4. **Cache common queries:** Pre-compute frequent responses

### Cost Optimization

1. **Use cheaper models** for simple queries
2. **Limit context window** to reduce token usage
3. **Implement caching** for repeated questions
4. **Monitor token usage** via `/metrics`

## Advanced Patterns

### Multi-Agent Collaboration

Run multiple Letta agents for different tasks:

```python
# Weather agent
weather_agent = await create_agent("weather-specialist")

# Calendar agent
calendar_agent = await create_agent("calendar-assistant")

# Route based on intent
if "weather" in user_text:
    response = await weather_agent.process_message(text, session_id)
else:
    response = await calendar_agent.process_message(text, session_id)
```

### Conversation Handoff

Transfer conversation between agents:

```python
# Export session from agent A
session_data = await client.get(f"/api/agents/{agent_a}/sessions/{session_id}/export")

# Import to agent B
await client.post(f"/api/agents/{agent_b}/sessions/import", json=session_data)
```

## Troubleshooting

### Agent not remembering context

**Solution:**

1. Verify session ID is consistent across messages
2. Check memory blocks are updating
3. Increase context window if hitting limits

### Slow responses

**Solution:**

1. Switch to faster model
2. Reduce context window
3. Use streaming API
4. Check Letta server logs for bottlenecks

### Tool calls not working

**Solution:**

1. Verify tool schema matches function signature
2. Check tool is registered with agent
3. Review Letta logs for tool call errors

## Monitoring Letta

### Logs

```bash
# Letta server logs
tail -f ~/.letta/logs/server.log

# Tonny integration logs
journalctl -u tonny -f | grep letta
```

### Metrics

Track via Tonny `/metrics`:

```json
{
  "llm_latency_ms": 450,
  "token_count": 234,
  "model": "gpt-4.1"
}
```

## Resources

- Letta Documentation: https://docs.letta.com
- Letta GitHub: https://github.com/letta-ai/letta
- Letta Discord: https://discord.gg/letta
- 33GOD Integration Patterns: See `/docs/INTEGRATION.md`

## Example Configurations

### Personal Assistant

```python
{
    "persona": "You are Tonny, a personal assistant who helps manage tasks, calendar, and reminders via voice commands.",
    "tools": ["add_task", "check_calendar", "set_reminder"],
    "memory_blocks": [
        {"name": "tasks", "description": "User's current tasks"},
        {"name": "schedule", "description": "User's schedule"}
    ]
}
```

### Developer Assistant

```python
{
    "persona": "You are Tonny, a senior developer who provides quick coding help and technical guidance via voice.",
    "tools": ["search_docs", "run_command", "explain_code"],
    "memory_blocks": [
        {"name": "current_project", "description": "Active project context"},
        {"name": "tech_stack", "description": "Technologies being used"}
    ]
}
```

### Home Automation

```python
{
    "persona": "You are Tonny, a smart home assistant who controls devices and answers questions about your home.",
    "tools": ["control_lights", "set_thermostat", "check_security"],
    "memory_blocks": [
        {"name": "device_states", "description": "Current device states"},
        {"name": "automations", "description": "Active automation rules"}
    ]
}
```
