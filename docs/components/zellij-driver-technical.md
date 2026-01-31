# Zellij Driver (zdrive/Perth Zellij) - Technical Implementation Guide

## Overview

Zellij Driver provides cognitive context management for Zellij terminal sessions with intent tracking and Redis-backed persistence. The CLI (`zdrive`) combines pane-first navigation with intent logging, allowing developers and agents to track work context, log milestones, and maintain state across sessions.

## Implementation Details

**Language**: Rust (2021 edition)
**CLI**: `zdrive` binary
**Database**: Redis (metadata and intent history)
**Zellij Integration**: Action interface for pane/tab control
**LLM Support**: Anthropic Claude, OpenAI, Ollama (for automated snapshots)

### Key Technologies

- **clap**: CLI argument parsing
- **redis**: Redis client for state management
- **git2**: Git repository integration
- **serde**: JSON serialization
- **tokio**: Async runtime

## Architecture & Design Patterns

### Core Components

```rust
// src/cli.rs - Command structure
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "zdrive")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Pane {
        name: String,
        #[command(subcommand)]
        action: Option<PaneAction>,
    },
    Tab {
        name: String,
    },
    List,
    Reconcile,
    Config {
        #[command(subcommand)]
        action: ConfigAction,
    },
}

#[derive(Subcommand)]
enum PaneAction {
    Log {
        message: String,
        #[arg(long)]
        r#type: Option<EntryType>,
        #[arg(long)]
        artifacts: Vec<String>,
        #[arg(long)]
        source: Option<Source>,
    },
    History {
        #[arg(long)]
        last: Option<usize>,
        #[arg(long)]
        format: Option<OutputFormat>,
    },
    Snapshot,
}
```

### Intent Logging

```rust
// src/state.rs - Intent tracking
#[derive(Serialize, Deserialize)]
pub struct IntentEntry {
    pub timestamp: DateTime<Utc>,
    pub message: String,
    pub entry_type: EntryType,
    pub source: Source,
    pub artifacts: Vec<String>,
}

#[derive(Serialize, Deserialize)]
pub enum EntryType {
    Checkpoint,
    Milestone,
    Exploration,
}

#[derive(Serialize, Deserialize)]
pub enum Source {
    Human,
    Agent,
    Automated,
}

impl StateManager {
    pub async fn log_intent(
        &self,
        pane_name: &str,
        entry: IntentEntry
    ) -> Result<(), Error> {
        let key = format!("perth:pane:{}:history", pane_name);

        // Prepend to list (newest first)
        let entry_json = serde_json::to_string(&entry)?;
        self.redis.lpush(&key, &entry_json).await?;

        // Trim to last 1000 entries
        self.redis.ltrim(&key, 0, 999).await?;

        Ok(())
    }

    pub async fn get_history(
        &self,
        pane_name: &str,
        last_n: Option<usize>
    ) -> Result<Vec<IntentEntry>, Error> {
        let key = format!("perth:pane:{}:history", pane_name);

        let entries: Vec<String> = self.redis
            .lrange(&key, 0, last_n.map(|n| n as isize - 1).unwrap_or(-1))
            .await?;

        Ok(entries
            .into_iter()
            .filter_map(|s| serde_json::from_str(&s).ok())
            .collect())
    }
}
```

### LLM Snapshot Generation

```rust
// src/llm/mod.rs - Automated context summaries
use anthropic_sdk::Client as AnthropicClient;

pub struct SnapshotGenerator {
    client: AnthropicClient,
    consent_granted: bool,
}

impl SnapshotGenerator {
    pub async fn generate_snapshot(
        &self,
        pane_name: &str,
        context: WorkContext
    ) -> Result<String, Error> {
        if !self.consent_granted {
            return Err(Error::ConsentRequired);
        }

        // Redact secrets before sending to LLM
        let sanitized = self.redact_secrets(context);

        let prompt = format!(
            r#"Summarize this development session:

Pane: {}
Recent Activities:
{}

Current State:
- Files Modified: {}
- Last Command: {}

Generate a concise summary (2-3 sentences) of what was accomplished."#,
            pane_name,
            self.format_activities(&sanitized.activities),
            sanitized.modified_files.join(", "),
            sanitized.last_command
        );

        let response = self.client
            .messages()
            .create(anthropic_sdk::types::MessagesRequest {
                model: "claude-sonnet-4-20250514".to_string(),
                messages: vec![Message {
                    role: "user".to_string(),
                    content: prompt,
                }],
                max_tokens: 200,
                ..Default::default()
            })
            .await?;

        Ok(response.content[0].text.clone())
    }

    fn redact_secrets(&self, context: WorkContext) -> WorkContext {
        // Redact API keys, tokens, passwords
        let patterns = [
            r"api[_-]?key[=:]\s*\S+",
            r"token[=:]\s*\S+",
            r"password[=:]\s*\S+",
        ];

        // ... redaction logic
    }
}
```

### Zellij Action Integration

```rust
// src/zellij.rs - Pane navigation
use std::process::Command;

pub struct ZellijDriver;

impl ZellijDriver {
    pub fn navigate_to_pane(pane_name: &str) -> Result<(), Error> {
        // First, try to focus existing pane
        if let Ok(pane_id) = self.find_pane_by_name(pane_name) {
            self.focus_pane(pane_id)?;
        } else {
            // Create new pane
            self.create_pane(pane_name)?;
        }

        Ok(())
    }

    fn find_pane_by_name(&self, name: &str) -> Result<usize, Error> {
        // Query Redis for pane metadata
        let key = format!("perth:pane:{}", name);
        // ... lookup logic
    }

    fn focus_pane(&self, pane_id: usize) -> Result<(), Error> {
        Command::new("zellij")
            .arg("action")
            .arg("focus-pane")
            .arg(pane_id.to_string())
            .status()?;

        Ok(())
    }

    fn create_pane(&self, name: &str) -> Result<(), Error> {
        Command::new("zellij")
            .arg("action")
            .arg("new-pane")
            .arg("--name")
            .arg(name)
            .status()?;

        Ok(())
    }
}
```

## Configuration

```toml
# ~/.config/zellij-driver/config.toml
[redis_settings]
redis_url = "redis://127.0.0.1:6379/"

[llm_settings]
provider = "anthropic"  # anthropic, openai, or ollama
model = "claude-sonnet-4-20250514"
consent_granted = false  # Must explicitly grant

[monitoring_settings]
auto_snapshot_threshold_seconds = 30
exclude_patterns = ["node_modules/", ".git/", "target/"]
```

## Integration Points

### Shell Hook Integration

```zsh
# ~/.zshrc - Auto-snapshot on long commands
zdrive_snapshot_on_complete() {
    local last_status=$?
    local elapsed=$SECONDS

    if [[ $elapsed -gt 30 ]]; then
        local pane_name=$(basename "$PWD")
        zdrive pane snapshot "$pane_name" 2>/dev/null &!
    fi

    return $last_status
}

preexec() { SECONDS=0 }
precmd() { zdrive_snapshot_on_complete }
```

### Git Hook Integration

```bash
# .git/hooks/post-commit
#!/bin/bash
PANE_NAME=$(basename "$PWD")
COMMIT_MSG=$(git log -1 --format=%s)
FILES_CHANGED=$(git diff-tree --no-commit-id --name-only -r HEAD | head -5)

zdrive pane log "$PANE_NAME" "Committed: $COMMIT_MSG" \
    --type milestone \
    --source automated \
    --artifacts $FILES_CHANGED
```

### Agent Integration

```rust
// Agents can log their work automatically
pub async fn agent_log_work(
    pane: &str,
    task: &str,
    artifacts: Vec<String>
) -> Result<(), Error> {
    let entry = IntentEntry {
        timestamp: Utc::now(),
        message: format!("Completed: {}", task),
        entry_type: EntryType::Checkpoint,
        source: Source::Agent,
        artifacts,
    };

    StateManager::new().await?
        .log_intent(pane, entry)
        .await
}
```

## Code Examples

### Programmatic Usage

```rust
use zdrive::{StateManager, IntentEntry, EntryType, Source};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let state = StateManager::new().await?;

    // Log milestone
    state.log_intent(
        "api-server",
        IntentEntry {
            timestamp: Utc::now(),
            message: "Implemented OAuth2 authentication".to_string(),
            entry_type: EntryType::Milestone,
            source: Source::Human,
            artifacts: vec![
                "src/auth/oauth.rs".to_string(),
                "tests/auth/oauth_test.rs".to_string(),
            ],
        }
    ).await?;

    // Get recent history
    let history = state.get_history("api-server", Some(10)).await?;

    for entry in history {
        println!("[{}] {}: {}",
            entry.entry_type,
            entry.timestamp.format("%H:%M"),
            entry.message
        );
    }

    Ok(())
}
```

## Performance

- **Redis Lookup**: <5ms
- **Pane Navigation**: <50ms
- **LLM Snapshot**: 1-3 seconds
- **Memory**: 5-10 MB

## Related Components

- **Perth**: Zellij fork that zdrive controls
- **iMi**: Worktree management (separate but complementary)
- **Bloodbank**: Can publish intent logs as events

---

**Quick Reference**:
- Binary: `zdrive`
- Database: Redis (port 6379)
- Config: `~/.config/zellij-driver/config.toml`
