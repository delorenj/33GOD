# hookd

Deterministic hook event pipeline for Claude Code tool mutations.

## Architecture

```
hookd-emit → Unix Socket → hookd (Rust) → Bloodbank (RabbitMQ) → consumers
```

## Components

- `bin/hookd-emit` - Fire-and-forget hook emitter (shell script)
- `src/` - Rust daemon that enriches + publishes events
- `config/` - Example hook configurations

## Quick Start

```bash
# Start the daemon
cargo run

# Test with a sample event
echo '{"tool_input":{"file_path":"/tmp/test.rs","content":"fn main() {}"}}' | ./bin/hookd-emit post_tool_use write
```

## Related

- **mutation-ledger**: Consumer service at `services/mutation-ledger/`
- **Bloodbank**: Event backbone at `bloodbank/`
