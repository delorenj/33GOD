# hookd Developer Guide

> How to extend, integrate, and operate the hookd tool mutation pipeline.

---

## Quick Start

```bash
# 1. Build the daemon
cargo build --release

# 2. Start it
RABBIT_URL=amqp://user:pass@192.168.1.12:5672/ \
HOOKD_SOCKET=/run/user/$(id -u)/hookd.sock \
  ./target/release/hookd

# 3. Install hooks into your agent (Claude Code example)
# Add to .claude/settings.json - see "Installing Hooks" section below

# 4. Start the mutation-ledger consumer
cd ../services/mutation-ledger
RABBIT_URL=amqp://user:pass@192.168.1.12:5672/ \
QDRANT_API_KEY=your-key \
  python -m src.consumer

# 5. Query your mutations
hookd-query --search "authentication changes"
hookd-query --since 1h --format json
```

---

## System Architecture

```
┌────────────────────────────────────────────────────┐
│  Agent Hooks (stdin pipe)                          │
│  Claude Code / Gemini CLI / Codex / etc.           │
└───────────────────────┬────────────────────────────┘
                        │ JSON payload via stdin
                        ▼
┌────────────────────────────────────────────────────┐
│  hookd-emit  (bin/hookd-emit)                      │
│  Bash script: jq envelope + socat socket write     │
│  MUST exit 0 on all paths (never block the agent)  │
└───────────────────────┬────────────────────────────┘
                        │ HookEnvelope (JSON over Unix socket)
                        ▼
┌────────────────────────────────────────────────────┐
│  hookd daemon  (src/main.rs)                       │
│  Rust async: socket listener + git enrichment +    │
│  AMQP publisher                                    │
└───────────────────────┬────────────────────────────┘
                        │ ToolMutationEvent (AMQP)
                        ▼
┌────────────────────────────────────────────────────┐
│  Bloodbank (RabbitMQ)                              │
│  Exchange: bloodbank.events.v1 (topic)             │
│  Routing:  tool.mutation.{write,edit,bash,...}      │
└───────────────────────┬────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────┐
│  mutation-ledger  (services/mutation-ledger/)       │
│  Python: semantic enrichment + Qdrant embedding +  │
│  SQLite cache                                      │
└───────────────┬───────────────────┬────────────────┘
                │                   │
                ▼                   ▼
        ┌──────────────┐   ┌──────────────┐
        │   Qdrant     │   │   SQLite     │
        │  (semantic)  │   │  (structured)│
        └──────────────┘   └──────────────┘
```

---

## Installing Hooks into Agents

### Claude Code

Claude Code hooks live in `.claude/settings.json` under the `hooks` key. Each hook gets the tool's JSON payload on stdin and must complete within the timeout.

**Minimal hookd integration** (add to `.claude/settings.json`):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "hookd-emit post_tool_use write",
            "timeout": 5000
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "hookd-emit post_tool_use bash",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

**Key constraints:**
- `hookd-emit` must be on PATH (or use absolute path)
- The hookd daemon must be running (if not, hookd-emit silently exits 0)
- Timeout is 5s. hookd-emit typically completes in <50ms.

**Coexisting with other hooks:** hookd hooks are additive. They can run alongside existing hooks like bloodbank-publisher.sh or claude-flow hooks. Just add the hookd entries to the existing arrays.

### Gemini CLI (Future)

Gemini CLI uses a plugin-based extension model. To add hookd support:

1. Create a Gemini CLI plugin in `adapters/gemini/`
2. The plugin intercepts tool execution events
3. Translates Gemini's event format to hookd's `HookEnvelope`:

```json
{
  "event_type": "post_tool_use",
  "tool_name": "WriteFile",
  "payload": { "...gemini tool output..." },
  "timestamp": "2026-02-06T09:00:00Z",
  "pid": 12345
}
```

4. Writes the envelope to the hookd Unix socket (same as hookd-emit does)

The adapter's job is purely format translation. The hookd daemon handles everything else.

### Codex CLI / Other Agents (Future)

The pattern is the same for any agent:

1. **Identify the hook/extension point** in the agent's system
2. **Write an adapter** that captures tool execution events
3. **Translate to HookEnvelope format** (5 fields: event_type, tool_name, payload, timestamp, pid)
4. **Write to Unix socket** via socat, netcat, or direct socket write

The adapter can be:
- A shell script (like hookd-emit for Claude Code)
- A plugin/extension in the agent's native language
- A sidecar process that intercepts agent I/O

---

## Extending hookd: New Hook Types

### Adding a New Tool Matcher

To capture events from a new Claude Code tool (e.g., `WebFetch`):

1. **Update the hook config** (`config/hooks.example.json` or your `.claude/settings.json`):

```json
{
  "matcher": "WebFetch",
  "hooks": [
    {
      "type": "command",
      "command": "hookd-emit post_tool_use webfetch",
      "timeout": 5000
    }
  ]
}
```

2. **Update the enrichment logic** in `services/mutation-ledger/src/enrichment.py` to handle the new tool type in `classify_intent()`:

```python
elif tool == "webfetch":
    return "web-fetch"
```

3. **Register the new routing key** in `services/registry.yaml`:

```yaml
# Under hookd-producer.produces:
- "tool.mutation.webfetch"

# Under event_subscriptions:
tool.mutation.webfetch:
  - "mutation-ledger"
```

4. **Update the Rust daemon** if the new tool has a unique payload shape. The `extract_file_path()` function in `src/enrichment.rs` handles payload parsing:

```rust
fn extract_file_path(payload: &Value) -> Option<String> {
    payload
        .get("tool_input")
        .and_then(|ti| {
            ti.get("file_path")
                .or_else(|| ti.get("path"))
                .or_else(|| ti.get("notebook_path"))
                .or_else(|| ti.get("url"))  // new: WebFetch URL
        })
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
}
```

### Adding New Hook Points (Pre vs Post)

hookd currently captures `PostToolUse` events. To add `PreToolUse`:

1. Configure the hook in `.claude/settings.json` under `PreToolUse`
2. The `event_type` field in the envelope distinguishes pre vs post: `"pre_tool_use"` vs `"post_tool_use"`
3. The daemon already passes `event_type` through as `hook_type` in the `ToolMutationEvent`
4. Downstream consumers can filter on `hook_type` if they only want post-execution events

### Adding Session Lifecycle Events

To capture `SessionStart` and `Stop` hooks:

1. Add to `.claude/settings.json`:

```json
{
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "hookd-emit session_start agent",
          "timeout": 5000
        }
      ]
    }
  ],
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "hookd-emit session_stop agent",
          "timeout": 5000
        }
      ]
    }
  ]
}
```

2. Add new routing keys: `session.lifecycle.start`, `session.lifecycle.stop`
3. Create a separate consumer or extend mutation-ledger to handle session events

---

## Extending: New Enrichment Classifiers

The mutation-ledger's semantic enrichment is in `services/mutation-ledger/src/enrichment.py`. All classifiers are rule-based (no LLM calls) for speed.

### Adding Intent Classifications

Edit `INTENT_PATTERNS` in `enrichment.py`:

```python
INTENT_PATTERNS: list[tuple[str, str]] = [
    (r"test[s_]?/|_test\.|\\.test\\.|spec\\.", "test"),
    (r"\\.lock$|lock\\.json$", "dependency-lock"),
    # ... existing patterns ...
    (r"migration[s]?/", "database-migration"),    # new
    (r"proto/|\\.proto$", "protobuf"),             # new
]
```

### Adding Domain Classifications

Edit `classify_domain()`:

```python
if any(p in path_lower for p in ["/proto/", "/grpc/", "/rpc/"]):
    return "rpc-layer"
```

### Adding Language Mappings

Edit `EXT_MAP`:

```python
EXT_MAP["proto"] = "protobuf"
EXT_MAP["graphql"] = "graphql"
EXT_MAP["tf"] = "terraform"
```

After adding classifiers, add corresponding test cases in `tests/test_enrichment.py`.

---

## Writing New Consumers

Any service can subscribe to `tool.mutation.#` events. To create a new consumer:

### 1. Register in registry.yaml

```yaml
my-mutation-consumer:
  name: "my-mutation-consumer"
  description: "Does something cool with tool mutations"
  type: "event-consumer"
  queue_name: "services.hookd.my_consumer"
  routing_keys:
    - "tool.mutation.#"
  status: "active"
  owner: "33GOD"
```

### 2. Implement the Consumer

Follow the 33GOD aio-pika consumer pattern:

```python
import aio_pika
from aio_pika import ExchangeType

async def consume():
    connection = await aio_pika.connect_robust("amqp://...")
    channel = await connection.channel()
    exchange = await channel.declare_exchange(
        "bloodbank.events.v1", ExchangeType.TOPIC, durable=True
    )
    queue = await channel.declare_queue(
        "services.hookd.my_consumer", durable=True
    )
    await queue.bind(exchange, routing_key="tool.mutation.#")

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                event = json.loads(message.body)
                # event is a ToolMutationEvent dict
                # Do your thing here
```

### 3. Consumer Ideas

Some useful consumers that could be built:
- **Mutation rate alerter**: Fire a Slack notification if mutation rate exceeds a threshold
- **Code review assistant**: Aggregate mutations per branch, generate PR summaries
- **Agent leaderboard**: Track which agents are most productive per project
- **Drift detector**: Compare mutation domains against expected project focus areas
- **Cost estimator**: Correlate mutations with LLM token usage for per-feature cost tracking

---

## Troubleshooting

### hookd-emit silently exits

This is by design. Check:
1. Is the hookd daemon running? (`ls -la /run/user/$(id -u)/hookd.sock`)
2. Is `jq` installed? (`which jq`)
3. Is `socat` installed? (`which socat`)
4. Enable debug mode: `HOOKD_DEBUG=1 hookd-emit post_tool_use Write < test.json`

### Daemon can't connect to RabbitMQ

Check the vhost. lapin (Rust AMQP) treats trailing `/` differently than Python pika:
- **Wrong**: `amqp://user:pass@host:5672/` (lapin sees empty vhost)
- **Right**: `amqp://user:pass@host:5672/%2f` (explicit default vhost)

The daemon auto-normalizes this, but check `RUST_LOG=hookd=debug` output for connection errors.

### No messages reaching mutation-ledger

1. Check RabbitMQ management UI: `http://host:15672`
2. Verify queue `services.hookd.mutation_ledger` exists and has bindings
3. Verify the routing key matches: `tool.mutation.#` should catch all tool mutations
4. Check daemon logs for "event published" entries

### Qdrant collection not created

1. Verify Qdrant is reachable: `curl http://172.19.0.22:6333/collections`
2. Check `QDRANT_API_KEY` is set
3. The collection is created lazily on first mutation for a given repo

---

## File Map

```
hookd/
├── bin/
│   └── hookd-emit              # Shell emitter (bash + jq + socat)
├── src/
│   ├── main.rs                 # Daemon entry: socket listener + shutdown
│   ├── config.rs               # Env var config with AMQP vhost normalization
│   ├── envelope.rs             # Data types: HookEnvelope, RepoContext, ToolMutationEvent
│   ├── enrichment.rs           # Git context resolver + payload extraction
│   └── publisher.rs            # AMQP publisher with reconnect + buffering
├── config/
│   └── hooks.example.json      # Reference Claude Code hook configuration
├── tests/
│   └── test_hookd_emit.sh      # Shell tests for hookd-emit
├── Cargo.toml                  # Rust dependencies
├── GOD.md                      # Architecture reference (this component)
├── DEV_README.md               # This file
└── .env                        # Local env vars (not committed)

services/mutation-ledger/
├── src/
│   ├── __init__.py
│   ├── config.py               # Settings (Qdrant, RabbitMQ, embedding model)
│   ├── models.py               # ToolMutationEvent, EnrichedMutation (Pydantic)
│   ├── enrichment.py           # Intent/domain/language classifiers + summary
│   ├── vector_store.py         # Qdrant client, collection management, embedding
│   ├── consumer.py             # RabbitMQ consumer wiring
│   ├── db.py                   # SQLite cache (append-only mutations table)
│   └── query.py                # CLI: structured + semantic query
├── tests/
│   ├── test_enrichment.py      # Unit tests (13 tests)
│   └── test_integration.py     # Integration tests (Qdrant store + search)
└── pyproject.toml              # Python project config (v0.2.0)
```
