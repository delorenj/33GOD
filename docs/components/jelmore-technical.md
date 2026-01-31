# Jelmore - Technical Implementation Guide

## Overview

Jelmore provides unified CLI orchestration for multi-provider agentic coding tools (Claude, Gemini, Codex). It offers session management, event-driven integration with Bloodbank, and an extensible hook system for pre/post execution processing.

## Implementation Details

**Language**: Python 3.12+
**Framework**: Typer (CLI), Click (command patterns)
**Package Manager**: uv
**Event Bus**: Bloodbank (RabbitMQ)
**Session Storage**: SQLite or Redis

### Key Technologies

- **Typer**: Type-safe CLI framework
- **Command Pattern**: Provider-agnostic execution
- **Builder Pattern**: Provider-specific command construction
- **Hook System**: Pre/post execution middleware
- **Session Management**: Persistent sessions with continue/resume

## Architecture & Design Patterns

### Command Pattern

```python
# src/jelmore/commands.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ExecutionContext:
    session_id: str
    provider: str
    model: str
    working_directory: Path
    environment: Dict[str, str]

class Command(ABC):
    """Abstract command interface"""

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> CommandResult:
        pass

    @abstractmethod
    async def undo(self, context: ExecutionContext) -> None:
        pass

class ClaudeCodeCommand(Command):
    """Claude Code provider implementation"""

    def __init__(self, prompt: str, files: List[Path]):
        self.prompt = prompt
        self.files = files

    async def execute(self, context: ExecutionContext) -> CommandResult:
        # Build Claude Code CLI invocation
        cmd = [
            'claude',
            'code',
            '--prompt', self.prompt,
            '--files', *[str(f) for f in self.files],
            '--session', context.session_id
        ]

        result = await subprocess.run(
            cmd,
            cwd=context.working_directory,
            env=context.environment,
            capture_output=True
        )

        return CommandResult(
            success=result.returncode == 0,
            output=result.stdout.decode(),
            error=result.stderr.decode(),
            artifacts=self.extract_artifacts(result.stdout)
        )

class GeminiCodeCommand(Command):
    """Gemini provider implementation"""

    def __init__(self, prompt: str):
        self.prompt = prompt

    async def execute(self, context: ExecutionContext) -> CommandResult:
        # Build Gemini CLI invocation
        cmd = [
            'gemini',
            'generate',
            '--prompt', self.prompt,
            '--model', context.model
        ]

        # ... similar execution logic
```

### Builder Pattern

```python
# src/jelmore/builders.py
class CommandBuilder:
    """Fluent interface for building commands"""

    def __init__(self):
        self.provider = None
        self.prompt = None
        self.files = []
        self.options = {}

    def with_provider(self, provider: str) -> 'CommandBuilder':
        self.provider = provider
        return self

    def with_prompt(self, prompt: str) -> 'CommandBuilder':
        self.prompt = prompt
        return self

    def with_files(self, files: List[Path]) -> 'CommandBuilder':
        self.files = files
        return self

    def with_option(self, key: str, value: Any) -> 'CommandBuilder':
        self.options[key] = value
        return self

    def build(self) -> Command:
        """Build the appropriate command based on provider"""
        providers = {
            'claude': ClaudeCodeCommand,
            'gemini': GeminiCodeCommand,
            'codex': CodexCommand
        }

        command_class = providers.get(self.provider)
        if not command_class:
            raise ValueError(f"Unknown provider: {self.provider}")

        return command_class(
            prompt=self.prompt,
            files=self.files,
            **self.options
        )
```

### Hook System

```python
# src/jelmore/hooks.py
class HookManager:
    """Pre/post execution hooks"""

    def __init__(self):
        self.pre_hooks = []
        self.post_hooks = []

    def register_pre_hook(self, hook: Callable):
        self.pre_hooks.append(hook)

    def register_post_hook(self, hook: Callable):
        self.post_hooks.append(hook)

    async def run_pre_hooks(self, context: ExecutionContext):
        for hook in self.pre_hooks:
            await hook(context)

    async def run_post_hooks(
        self,
        context: ExecutionContext,
        result: CommandResult
    ):
        for hook in self.post_hooks:
            await hook(context, result)

# Built-in hooks
async def log_execution_hook(context: ExecutionContext):
    """Log command execution to database"""
    logger.info(f"Executing {context.provider} command in session {context.session_id}")

async def publish_event_hook(context: ExecutionContext, result: CommandResult):
    """Publish execution result to Bloodbank"""
    await bloodbank.publish(
        'jelmore.command.completed',
        {
            'session_id': context.session_id,
            'provider': context.provider,
            'success': result.success,
            'artifacts': result.artifacts
        }
    )
```

### Session Management

```python
# src/jelmore/session.py
class Session:
    """Persistent session with continue/resume semantics"""

    def __init__(self, session_id: str, db: Database):
        self.id = session_id
        self.db = db
        self.history = []

    async def add_command(self, command: Command, result: CommandResult):
        """Append command to session history"""
        self.history.append({
            'command': command,
            'result': result,
            'timestamp': datetime.utcnow()
        })

        await self.db.save_session(self)

    async def continue_session(self, new_prompt: str) -> CommandResult:
        """Continue from last command in session"""
        last_context = self.history[-1]['command'].context

        # Build new command with same context
        command = CommandBuilder() \\
            .with_provider(last_context.provider) \\
            .with_prompt(new_prompt) \\
            .build()

        result = await command.execute(last_context)
        await self.add_command(command, result)

        return result

    async def resume_session(self) -> None:
        """Restore session state from database"""
        data = await self.db.load_session(self.id)
        self.history = data['history']
```

## Configuration

```yaml
# ~/.config/jelmore/config.yml
providers:
  claude:
    default_model: claude-sonnet-4
    executable: claude
  gemini:
    default_model: gemini-pro
    executable: gemini
  codex:
    default_model: gpt-4o
    executable: codex

session:
  storage: sqlite  # or 'redis'
  db_path: ~/.config/jelmore/sessions.db

hooks:
  enabled: true
  pre_hooks:
    - log_execution
  post_hooks:
    - publish_event
    - store_artifacts

bloodbank:
  enabled: true
  url: amqp://localhost:5672/
```

## Integration Points

### CLI Usage

```bash
# Execute with Claude Code
jelmore exec --provider claude --prompt "Implement user authentication"

# Continue session
jelmore continue --session abc-123 --prompt "Add JWT token validation"

# Resume previous session
jelmore resume --session abc-123

# List sessions
jelmore sessions list

# Export session
jelmore sessions export abc-123 --output session.json
```

### Programmatic Usage

```python
from jelmore import CommandBuilder, ExecutionContext, HookManager

# Build and execute command
command = CommandBuilder() \\
    .with_provider('claude') \\
    .with_prompt('Refactor this function') \\
    .with_files([Path('src/main.py')]) \\
    .build()

context = ExecutionContext(
    session_id='my-session',
    provider='claude',
    model='claude-sonnet-4',
    working_directory=Path.cwd(),
    environment=os.environ
)

# Run with hooks
hooks = HookManager()
await hooks.run_pre_hooks(context)
result = await command.execute(context)
await hooks.run_post_hooks(context, result)
```

## Related Components

- **Bloodbank**: Event bus for execution results
- **AgentForge**: Can use Jelmore for agent code generation
- **Holocene**: Dashboard displays Jelmore session history

---

**Quick Reference**:
- CLI: `jelmore`
- Config: `~/.config/jelmore/config.yml`
- Sessions: SQLite or Redis storage
