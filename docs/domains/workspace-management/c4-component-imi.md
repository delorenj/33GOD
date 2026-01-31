# C4 Component Level: iMi - Git Worktree Manager

## Overview
- **Name**: iMi (Git Worktree Manager)
- **Description**: Decentralized git worktree management tool built for distributed agentic workflows
- **Type**: Command-Line Application
- **Technology**: Rust, PostgreSQL, Git2 (libgit2)
- **Version**: 2.0.2

## Purpose

iMi provides sophisticated Git worktree management designed for asynchronous, parallel multi-agent workflows. It enables multiple AI agents or developers to work simultaneously on different branches of the same repository without conflicts, using Git's worktree feature with opinionated defaults and real-time visibility.

## Software Features

### Core Worktree Management
- **Worktree Creation**: Create typed worktrees (feat, fix, review, aiops, devops, custom)
- **Context Detection**: Automatically detect Git context (in worktree, trunk, repository, or outside)
- **Location Awareness**: Understand repository structure and iMi workspace hierarchy
- **Path Management**: Handle nested repository structures and iMi directories
- **Worktree Types**: Database-driven worktree type system with custom metadata

### Repository Management
- **Repository Registration**: Track repositories in PostgreSQL database
- **Multi-Root Support**: Support multiple repository root directories
- **Path Validation**: Validate and repair repository paths automatically
- **Remote Tracking**: Track remote URLs and default branches
- **Metadata Storage**: Store arbitrary JSON metadata per repository

### GitHub Integration
- **PR Worktrees**: Create worktrees directly from GitHub pull requests
- **PR Checkout**: Use `gh` CLI for authenticated PR operations
- **Issue Tracking**: Link worktrees to GitHub issues
- **Remote Validation**: Validate remote repository existence

### Database Persistence
- **Project Tracking**: Track all registered projects/repositories
- **Worktree Registry**: Maintain registry of all worktrees with state
- **Agent Activity**: Log agent activity within worktrees
- **Worktree Types**: Database-driven type system with custom prefixes
- **In-Flight Tracking**: Track uncommitted changes, ahead/behind counts

### Monitoring & Observability
- **File Watching**: Real-time monitoring of worktree changes
- **Status Tracking**: Monitor git status (clean, modified, conflicted)
- **Activity Logging**: Log agent interactions and file modifications
- **Health Checks**: Doctor command for system diagnostics

### Configuration Management
- **TOML Configuration**: User-configurable settings via config.toml
- **Multi-Root Paths**: Configure multiple repository root directories
- **Default Branches**: Configurable default branch names
- **Remote Settings**: Configure default remote names
- **Path Templates**: Customize worktree path generation

## Code Elements

This component contains the following Rust modules:

- **src/lib.rs** - Public API and module exports
- **src/main.rs** - CLI entry point and command dispatch
- **src/cli.rs** - Command-line interface definitions (Clap)
- **src/commands/** - Command implementations (project, doctor, worktree)
- **src/worktree.rs** - Worktree lifecycle management
- **src/git.rs** - Git operations and authentication
- **src/database.rs** - PostgreSQL persistence layer
- **src/context.rs** - Git context detection and location awareness
- **src/config.rs** - Configuration management
- **src/init.rs** - Repository initialization
- **src/local.rs** - Local repository operations
- **src/monitor.rs** - File system monitoring
- **src/fuzzy.rs** - Fuzzy matching for repository selection
- **src/github/** - GitHub API integration
- **src/error.rs** - Error types and handling

## Component Architecture

```mermaid
C4Component
    title Component Diagram for iMi Git Worktree Manager

    Container_Boundary(imi, "iMi Application") {
        Component(cli, "CLI Handler", "Clap v4.5", "Parses commands and delegates to handlers")
        Component(commands, "Command Handlers", "Rust", "Implements add, list, remove, trunk, doctor")
        Component(worktree_mgr, "Worktree Manager", "Rust", "Orchestrates worktree lifecycle operations")
        Component(git_mgr, "Git Manager", "Git2/libgit2", "Low-level git operations: add, remove, status")
        Component(context, "Context Detector", "Rust", "Detects git context and location type")
        Component(database, "Database Manager", "SQLx + PostgreSQL", "CRUD for projects, worktrees, activity")
        Component(config, "Config Manager", "TOML", "Loads and validates configuration")
        Component(monitor, "File Monitor", "Notify v6.1", "Watches worktree directories for changes")
        Component(github_client, "GitHub Client", "Octocrab v0.38", "GitHub API operations")
        Component(fuzzy, "Fuzzy Matcher", "Rust", "Repository name fuzzy search")
        Component(init, "Init Handler", "Rust", "Repository initialization and trunk setup")
    }

    ContainerDb(postgres, "PostgreSQL", "Database", "Stores projects, worktrees, activity, types")
    System_Ext(git, "Git", "Version Control", "Git executable and libgit2")
    System_Ext(github_api, "GitHub API", "REST API", "Pull requests and repository data")
    System_Ext(gh_cli, "GitHub CLI", "CLI Tool", "gh pr checkout commands")

    Rel(cli, commands, "Dispatches to", "Rust function calls")
    Rel(commands, worktree_mgr, "Uses", "Worktree operations")
    Rel(worktree_mgr, git_mgr, "Uses", "Git operations")
    Rel(worktree_mgr, database, "Uses", "Persist state")
    Rel(worktree_mgr, context, "Uses", "Detect context")
    Rel(worktree_mgr, config, "Uses", "Get settings")
    Rel(commands, github_client, "Uses", "PR operations")
    Rel(commands, fuzzy, "Uses", "Select repository")
    Rel(commands, init, "Uses", "Initialize repos")
    Rel(monitor, database, "Updates", "Activity logs")

    Rel(git_mgr, git, "Calls", "libgit2 + CLI")
    Rel(database, postgres, "Queries", "SQL via SQLx")
    Rel(github_client, github_api, "Calls", "HTTPS/REST")
    Rel(commands, gh_cli, "Spawns", "Process exec")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## Interfaces

### Command-Line Interface

**Protocol**: CLI (Command-Line Interface)
**Description**: Primary user interface for all worktree operations

**Operations**:
- `iMi add <type> <name> [--repo <repo>]` - Create a new worktree of specified type
- `iMi list [--repo <repo>]` - List all worktrees
- `iMi remove <name> [--repo <repo>]` - Remove a worktree
- `iMi trunk [--repo <repo>]` - Get or create trunk worktree path
- `iMi types` - List all worktree types
- `iMi doctor` - Run health diagnostics
- `iMi project create <name>` - Create new project from template
- `iMi project templates` - List available project templates

### Database Interface

**Protocol**: PostgreSQL (SQLx)
**Description**: Persistent storage for all worktree and repository state

**Tables**:
- `projects` - Repository registry with remote URLs and metadata
- `worktrees` - Worktree instances with branch, path, and status
- `agent_activity` - Agent interaction logs
- `worktree_types` - Type definitions with prefixes and metadata

**Stored Procedures**:
- `register_project(name, remote, branch, path, metadata)` - Atomic project registration
- `upsert_worktree(...)` - Insert or update worktree state

### Git Interface

**Protocol**: Git (libgit2 + CLI)
**Description**: Version control operations for worktree management

**Operations**:
- `git worktree add <path> -b <branch>` - Create worktree
- `git worktree remove <path>` - Remove worktree
- `git worktree list` - List existing worktrees
- `git status` - Check worktree status
- `git fetch` - Update remote tracking

### GitHub API Interface

**Protocol**: REST (HTTPS)
**Description**: GitHub integration for PR and issue operations

**Operations**:
- `GET /repos/{owner}/{repo}/pulls/{number}` - Get PR details
- `GET /repos/{owner}/{repo}` - Validate repository existence
- PR checkout via `gh` CLI subprocess

## Dependencies

### Internal Components
- **Worktree Manager** uses **Git Manager** for all git operations
- **Worktree Manager** uses **Database Manager** for state persistence
- **Worktree Manager** uses **Context Detector** for location awareness
- **Command Handlers** use **Fuzzy Matcher** for repository selection
- **CLI Handler** uses **Config Manager** for settings
- **File Monitor** uses **Database Manager** for activity logging

### External Systems
- **PostgreSQL**: Primary data store for all persistent state
- **Git**: Version control system (both libgit2 and CLI)
- **GitHub API**: Repository and PR metadata
- **GitHub CLI (gh)**: Authenticated PR checkout operations

### Rust Crates
- `clap` v4.5 - CLI framework with derive macros
- `sqlx` v0.7 - Async PostgreSQL driver with compile-time query checking
- `git2` v0.18 - libgit2 bindings for git operations
- `tokio` v1.37 - Async runtime (full features)
- `octocrab` v0.38 - GitHub API client
- `notify` v6.1 - File system change notifications
- `serde` + `serde_json` - Serialization for metadata
- `uuid` v1.8 - UUID generation for database records
- `chrono` v0.4 - Timestamp handling
- `colored` v2.1 - Terminal color output
- `dialoguer` v0.11 - Interactive prompts

## Data Models

### Project (Repository)
```rust
struct Project {
    id: Uuid,
    name: String,
    remote_url: String,  // Git remote URL
    default_branch: String,  // e.g., "main"
    path: String,  // Absolute path to trunk worktree
    description: Option<String>,
    metadata: serde_json::Value,  // Arbitrary JSON
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
    active: bool,
}
```

### Worktree
```rust
struct Worktree {
    id: Uuid,
    project_id: Uuid,
    type_id: i32,  // References worktree_types table
    name: String,  // e.g., "feat-new-feature"
    branch_name: String,  // e.g., "feat/new-feature"
    path: String,  // Absolute path to worktree
    agent_id: Option<String>,  // Assigned agent

    // In-flight work tracking
    has_uncommitted_changes: Option<bool>,
    uncommitted_files_count: Option<i32>,
    ahead_of_trunk: Option<i32>,
    behind_trunk: Option<i32>,
    last_commit_hash: Option<String>,
    last_commit_message: Option<String>,
    last_sync_at: Option<DateTime<Utc>>,

    // Merge tracking
    merged_at: Option<DateTime<Utc>>,
    merged_by: Option<String>,
    merge_commit_hash: Option<String>,

    metadata: serde_json::Value,
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
    active: bool,
}
```

### WorktreeType
```rust
struct WorktreeType {
    id: i32,
    name: String,  // e.g., "feat", "fix", "review"
    branch_prefix: String,  // e.g., "feat/"
    worktree_prefix: String,  // e.g., "feat-"
    description: Option<String>,
    is_builtin: bool,
    color: Option<String>,  // Terminal color
    icon: Option<String>,  // Unicode icon
    metadata: serde_json::Value,
    created_at: DateTime<Utc>,
}
```

### GitContext (Runtime)
```rust
enum GitContext {
    InWorktree { repo_path: PathBuf, worktree_path: PathBuf },
    InTrunk { repo_path: PathBuf },
    InRepository { repo_path: PathBuf },
    Outside,
}
```

## Configuration

### Config File: `~/.config/iMi/config.toml`

```toml
[paths]
# Primary root directory for repositories
primary_root = "~/code"

# Additional root directories (optional)
additional_roots = [
    "~/work",
    "~/projects"
]

[git_settings]
# Default branch name
default_branch = "main"

# Default remote name
default_remote = "origin"

[database]
# PostgreSQL connection URL (can also use DATABASE_URL env var)
url = "postgresql://imi:password@localhost:5432/imi"

[ui]
# Enable colored output
colors = true

# Show progress indicators
progress = true
```

## Error Handling

### ImiError Enum
```rust
enum ImiError {
    GitError(git2::Error),
    DatabaseError(sqlx::Error),
    ConfigError(String),
    NotInRepository,
    WorktreeNotFound(String),
    RepositoryNotFound(String),
    InvalidPath(String),
    GitHubError(String),
}
```

All errors are propagated using `anyhow::Result` with context annotations for better error messages.

## Security

### Authentication
- **Git SSH**: Uses SSH keys from `~/.ssh/` (id_ed25519, id_rsa, id_ecdsa)
- **GitHub PAT**: Environment variable `GITHUB_PERSONAL_ACCESS_TOKEN` or `GITHUB_TOKEN`
- **Database**: Connection string with credentials (environment variable recommended)

### Authorization
- File system permissions enforced by OS
- Database row-level security (if configured in PostgreSQL)
- Git operations use user's SSH key and permissions

## Performance

### Async Operations
- All database operations are async (via SQLx + Tokio)
- Concurrent worktree operations supported
- Connection pooling (10 max connections)

### Caching
- No in-memory caching (database is source of truth)
- Git operations use libgit2 for performance
- Context detection cached per command invocation

### Monitoring
- File system watching with debouncing
- Minimal overhead for status checks
- Database query performance tracked in logs

## Testing

### Unit Tests
- Pure functions tested in isolation
- Mock-based database testing
- Temp directories for git operations

### Integration Tests
- Real PostgreSQL database (test database)
- Real git repositories (tempfile)
- Serial execution to prevent conflicts

### Test Utilities
```rust
#[cfg(test)]
mod tests {
    use tempfile::TempDir;
    use tokio_test;

    // Test database setup
    // Test git repository creation
    // Test worktree lifecycle
}
```

## Deployment

### Prerequisites
- Rust 1.92+ (2021 edition)
- PostgreSQL 14+
- Git 2.30+
- GitHub CLI (gh) - optional, for PR features

### Build
```bash
cargo build --release
```

### Installation
```bash
cargo install --path .
# OR
cp target/release/iMi ~/.local/bin/
```

### Database Setup
```bash
# Set connection string
export DATABASE_URL="postgresql://imi:password@localhost:5432/imi"

# Migrations run automatically on first connection
```

### Configuration
```bash
mkdir -p ~/.config/iMi
cp config.example.toml ~/.config/iMi/config.toml
# Edit config.toml with your settings
```

---

**Component Version**: 2.0.2
**Last Updated**: 2026-01-29
**Rust Edition**: 2021
**License**: MIT
