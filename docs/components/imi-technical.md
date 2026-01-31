# iMi - Technical Implementation Guide

## Overview

iMi is a Rust-based Git worktree management tool designed for asynchronous, parallel multi-agent workflows. It provides intelligent worktree creation, real-time monitoring, and database-backed persistence to coordinate work across multiple AI agents and humans in the 33GOD ecosystem.

## Implementation Details

**Language**: Rust (2021 edition)
**Core Framework**: tokio (async runtime)
**Database**: SQLite (embedded persistence)
**CLI Framework**: clap with derive macros
**Version Control**: git2 (libgit2 bindings)

### Key Technologies

- **tokio**: Async runtime for concurrent operations
- **git2**: Native Git operations (worktree creation, status)
- **rusqlite**: Embedded SQL database for state tracking
- **clap**: Type-safe CLI argument parsing
- **notify**: File system event monitoring
- **serde**: JSON serialization for metadata

## Architecture & Design Patterns

### Convention-Based Worktree Management

iMi enforces a standardized directory structure:

```
~/code/my-project/
├── trunk-main/              # Main branch worktree (convention)
├── feat-user-auth/          # Feature worktree
├── pr-123/                  # Pull request review
├── fix-security-bug/        # Bug fix worktree
├── aiops-new-agent/         # AI operations
├── devops-ci-update/        # DevOps tasks
└── sync/                    # Shared configuration
    ├── global/              # Global dotfiles
    │   ├── coding-rules.md
    │   └── stack-specific.md
    └── repo/                # Repository-specific
        ├── .env
        └── .vscode/
```

**Naming Convention**:
- Prefix + hyphenated description
- Prefixes: `feat-`, `fix-`, `pr-`, `aiops-`, `devops-`
- Main worktree always: `trunk-main`

### Command Patterns

```rust
// src/cli.rs
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "iMi")]
#[command(about = "Git worktree manager for multi-agent workflows")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Create or switch to a feature worktree
    Feat {
        name: String,
        #[arg(long)]
        branch: Option<String>,
    },
    /// Create or switch to a PR review worktree
    Review {
        pr_number: u32,
    },
    /// Create or switch to a bug fix worktree
    Fix {
        name: String,
    },
    /// Monitor all worktrees in real-time
    Monitor,
    /// List all tracked worktrees
    List,
    /// Remove a worktree
    Remove {
        name: String,
    },
}
```

### Database Schema

```sql
-- SQLite schema for worktree tracking
CREATE TABLE worktrees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    path TEXT NOT NULL,
    branch TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_accessed TEXT NOT NULL,
    metadata JSON
);

CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worktree_id INTEGER NOT NULL,
    agent_id TEXT,
    activity_type TEXT NOT NULL,  -- 'file_change', 'commit', 'switch'
    timestamp TEXT NOT NULL,
    details JSON,
    FOREIGN KEY (worktree_id) REFERENCES worktrees(id)
);

CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'human', 'ai'
    current_worktree_id INTEGER,
    last_seen TEXT NOT NULL,
    FOREIGN KEY (current_worktree_id) REFERENCES worktrees(id)
);
```

### Worktree Creation Flow

```rust
// src/worktree.rs
use git2::{Repository, Branch};
use std::path::{Path, PathBuf};

pub struct WorktreeManager {
    repo: Repository,
    db: Database,
}

impl WorktreeManager {
    pub async fn create_worktree(
        &self,
        name: &str,
        prefix: &str,
        branch: Option<&str>,
    ) -> Result<PathBuf, Error> {
        // 1. Construct worktree path
        let worktree_name = format!("{}-{}", prefix, name);
        let worktree_path = self.repo_root()
            .parent()
            .unwrap()
            .join(&worktree_name);

        // 2. Determine branch name
        let branch_name = branch
            .map(String::from)
            .unwrap_or_else(|| format!("{}/{}", prefix, name));

        // 3. Create Git worktree
        let worktree = self.repo.worktree(
            &worktree_name,
            &worktree_path,
            Some(WorktreeOptions::new()
                .reference(&branch_name)
                .create_branch(true)
            )
        )?;

        // 4. Record in database
        self.db.insert_worktree(
            &worktree_name,
            &worktree_path,
            &branch_name,
        ).await?;

        // 5. Create symlinks for shared config
        self.sync_dotfiles(&worktree_path).await?;

        Ok(worktree_path)
    }
}
```

### Real-Time Monitoring

```rust
// src/monitor.rs
use notify::{Watcher, RecursiveMode, EventKind};
use tokio::sync::mpsc;

pub struct WorktreeMonitor {
    watchers: Vec<Box<dyn Watcher>>,
    db: Database,
}

impl WorktreeMonitor {
    pub async fn start(&mut self) -> Result<(), Error> {
        let (tx, mut rx) = mpsc::channel(1000);

        // Watch all worktrees
        for worktree in self.db.list_worktrees().await? {
            let tx_clone = tx.clone();

            let mut watcher = notify::recommended_watcher(
                move |res: Result<notify::Event, _>| {
                    if let Ok(event) = res {
                        let _ = tx_clone.blocking_send(event);
                    }
                }
            )?;

            watcher.watch(
                &Path::new(&worktree.path),
                RecursiveMode::Recursive
            )?;

            self.watchers.push(Box::new(watcher));
        }

        // Process events
        while let Some(event) = rx.recv().await {
            match event.kind {
                EventKind::Modify(_) => {
                    self.handle_file_change(event).await?;
                }
                EventKind::Create(_) => {
                    self.handle_file_created(event).await?;
                }
                _ => {}
            }
        }

        Ok(())
    }

    async fn handle_file_change(
        &self,
        event: notify::Event
    ) -> Result<(), Error> {
        for path in event.paths {
            if let Some(worktree) = self.db.find_worktree_by_path(&path).await? {
                self.db.log_activity(
                    worktree.id,
                    "file_change",
                    serde_json::json!({
                        "file": path.to_string_lossy(),
                        "timestamp": chrono::Utc::now(),
                    })
                ).await?;
            }
        }
        Ok(())
    }
}
```

## Configuration

### Config File

```toml
# ~/.config/iMi/config.toml
[sync_settings]
enabled = true
user_sync_path = "sync/user"
local_sync_path = "sync/local"

[git_settings]
default_branch = "main"
remote_name = "origin"
auto_fetch = true
prune_on_fetch = true

[monitoring_settings]
enabled = true
refresh_interval_ms = 1000
watch_file_changes = true
track_agent_activity = true

# Files to symlink across all worktrees
symlink_files = [
    ".env",
    ".vscode/settings.json",
    ".gitignore.local",
    ".mise.toml"
]

# Exclude patterns for monitoring
exclude_patterns = [
    "node_modules/",
    ".git/",
    "target/",
    ".venv/"
]
```

### Environment Variables

```bash
# Database location
IMI_DB_PATH=~/.local/share/imi/worktrees.db

# Repository root (auto-detected by default)
IMI_REPO_ROOT=/home/user/code/my-project

# Logging
IMI_LOG_LEVEL=info
IMI_LOG_FILE=~/.local/share/imi/imi.log
```

## Integration Points

### Agent Coordination Example

```rust
// Agent announces presence
pub struct Agent {
    id: String,
    name: String,
    agent_type: AgentType,
}

#[derive(serde::Serialize, serde::Deserialize)]
enum AgentType {
    Human,
    AICodeWriter,
    AIReviewer,
    AITester,
}

impl Agent {
    pub async fn claim_worktree(
        &self,
        worktree: &str,
        db: &Database
    ) -> Result<(), Error> {
        // Register agent in database
        db.upsert_agent(
            &self.id,
            &self.name,
            &self.agent_type
        ).await?;

        // Claim worktree
        db.assign_agent_to_worktree(
            &self.id,
            worktree
        ).await?;

        // Log start of work
        db.log_activity(
            worktree,
            "agent_claimed",
            serde_json::json!({
                "agent_id": &self.id,
                "agent_type": &self.agent_type,
                "timestamp": chrono::Utc::now(),
            })
        ).await?;

        Ok(())
    }
}
```

### CLI Usage for Agents

```bash
# Agent 1: Create feature worktree
imi feat payment-gateway
# Output: Created worktree at ~/code/myapp/feat-payment-gateway

# Agent 2: Create PR review worktree
imi review 456
# Output: Created worktree at ~/code/myapp/pr-456

# Agent 3: Monitor all activities
imi monitor
# Output: Real-time display of file changes across all worktrees
```

### Bloodbank Event Integration

```rust
// src/events.rs - Publish worktree events to Bloodbank
use bloodbank::Publisher;

pub async fn publish_worktree_created(
    worktree_name: &str,
    branch: &str,
    agent_id: Option<&str>
) -> Result<(), Error> {
    let publisher = Publisher::new().await?;

    let event = serde_json::json!({
        "event_type": "imi.worktree.created",
        "source": "imi",
        "data": {
            "worktree": worktree_name,
            "branch": branch,
            "agent_id": agent_id,
            "timestamp": chrono::Utc::now(),
        }
    });

    publisher.publish(
        "imi.worktree.created",
        event
    ).await?;

    Ok(())
}
```

## Performance Characteristics

### Operation Latency

- **Worktree Creation**: ~200ms (Git + database write)
- **Worktree Switch**: ~50ms (database lookup + shell integration)
- **File Change Detection**: <10ms (notify library event)
- **Database Query**: <5ms (SQLite indexed lookups)

### Resource Usage

- **Memory**: 5-10 MB baseline
- **CPU**: <1% idle, 5-10% during monitoring
- **Disk I/O**: Minimal (append-only activity log)
- **Database Size**: ~1 KB per worktree + 100 bytes per activity

### Scalability

- **Max Worktrees**: 1000+ per repository
- **Max Concurrent Agents**: 50+
- **File Watch Limit**: OS-dependent (typically 8192 on Linux)

## Edge Cases & Troubleshooting

### Orphaned Worktrees

**Problem**: Git worktree exists but not in database
**Solution**: Reconciliation command

```rust
pub async fn reconcile_worktrees(&self) -> Result<(), Error> {
    // Get Git worktrees
    let git_worktrees = self.repo.worktrees()?;

    // Get database worktrees
    let db_worktrees = self.db.list_worktrees().await?;

    // Find orphans
    for git_wt in git_worktrees {
        if !db_worktrees.iter().any(|db| db.name == git_wt) {
            // Add to database
            self.db.import_worktree(&git_wt).await?;
            println!("Imported orphaned worktree: {}", git_wt);
        }
    }

    // Find stale database entries
    for db_wt in db_worktrees {
        if !git_worktrees.contains(&db_wt.name) {
            // Clean up database
            self.db.remove_worktree(&db_wt.name).await?;
            println!("Removed stale database entry: {}", db_wt.name);
        }
    }

    Ok(())
}
```

### Symlink Conflicts

**Problem**: Dotfile symlink already exists as regular file
**Solution**: Backup and replace strategy

```rust
async fn sync_dotfiles(&self, worktree_path: &Path) -> Result<(), Error> {
    let sync_root = self.repo_root().parent().unwrap().join("sync/repo");

    for file in &self.config.symlink_files {
        let target = sync_root.join(file);
        let link = worktree_path.join(file);

        if link.exists() {
            if link.is_symlink() {
                // Remove old symlink
                fs::remove_file(&link)?;
            } else {
                // Backup existing file
                let backup = link.with_extension("backup");
                fs::rename(&link, &backup)?;
                println!("Backed up existing file to: {}", backup.display());
            }
        }

        // Create symlink
        unix::fs::symlink(&target, &link)?;
    }

    Ok(())
}
```

### Agent Conflict Detection

**Problem**: Multiple agents modify same file simultaneously
**Solution**: Activity log with conflict warnings

```rust
async fn check_for_conflicts(
    &self,
    worktree: &str,
    file_path: &Path
) -> Result<Option<Conflict>, Error> {
    // Get recent activities on this file
    let recent = self.db.get_recent_activities(
        worktree,
        file_path,
        Duration::from_secs(60)  // Last 60 seconds
    ).await?;

    // Multiple agents modified in short window?
    let unique_agents: HashSet<_> = recent
        .iter()
        .filter_map(|a| a.agent_id.as_ref())
        .collect();

    if unique_agents.len() > 1 {
        return Ok(Some(Conflict {
            file: file_path.to_path_buf(),
            agents: unique_agents.into_iter().cloned().collect(),
            activities: recent,
        }));
    }

    Ok(None)
}
```

## Code Examples

### Creating Worktrees Programmatically

```rust
use imi::{WorktreeManager, Database};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let db = Database::open("~/.local/share/imi/worktrees.db").await?;
    let manager = WorktreeManager::new(db)?;

    // Create feature worktree
    let worktree = manager.create_worktree(
        "user-authentication",
        "feat",
        None  // Auto-generate branch name
    ).await?;

    println!("Created worktree at: {}", worktree.display());

    // Log agent activity
    manager.db.log_activity(
        "feat-user-authentication",
        "agent_started_work",
        serde_json::json!({
            "agent_id": "ai-coder-001",
            "task": "Implement OAuth2 flow",
        })
    ).await?;

    Ok(())
}
```

### Monitoring Worktree Status

```rust
// Query worktree status
async fn get_worktree_status(
    db: &Database,
    worktree: &str
) -> Result<WorktreeStatus, Error> {
    let wt = db.get_worktree(worktree).await?;
    let activities = db.get_recent_activities(worktree, Duration::from_secs(3600)).await?;
    let assigned_agents = db.get_agents_in_worktree(worktree).await?;

    let repo = Repository::open(&wt.path)?;
    let head = repo.head()?;
    let branch = head.shorthand().unwrap_or("unknown");

    let status = repo.statuses(None)?;
    let dirty_files = status.iter()
        .filter(|e| e.status() != git2::Status::CURRENT)
        .count();

    Ok(WorktreeStatus {
        name: wt.name.clone(),
        branch: branch.to_string(),
        dirty_files,
        active_agents: assigned_agents,
        recent_activity_count: activities.len(),
        last_modified: activities.first().map(|a| a.timestamp),
    })
}
```

## Deployment Best Practices

1. **Shell Integration**: Add `imi` to PATH and shell completion
2. **Auto-Sync**: Run `imi reconcile` on shell startup
3. **Monitoring**: Start `imi monitor` in background terminal
4. **Cleanup**: Periodically archive old worktrees
5. **Backup**: Database auto-backups to `~/.local/share/imi/backups/`

## Related Components

- **Perth (Zellij)**: Terminal multiplexer with iMi integration
- **Bloodbank**: Event bus for worktree lifecycle events
- **AgentForge**: Spawns agents into dedicated worktrees
- **Holocene**: Dashboard displays worktree activity

---

**Quick Reference**:
- GitHub: `33GOD/iMi`
- Binary: `target/release/imi`
- Database: `~/.local/share/imi/worktrees.db`
- Config: `~/.config/iMi/config.toml`
