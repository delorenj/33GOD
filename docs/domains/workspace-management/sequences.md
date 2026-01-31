# Workspace Management Domain - Sequence Diagrams

## Overview

Detailed sequence diagrams showing interactions between workspace components, developers, and AI agents.

## 1. Worktree Creation Sequence

Complete interaction flow for creating a new feature worktree.

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant CLI as iMi CLI
    participant DB as SQLite
    participant Git as Git Repository
    participant FS as Filesystem
    participant Sync as sync/ Directory
    participant RMQ as RabbitMQ

    Dev->>CLI: imi feat user-auth
    CLI->>CLI: Parse command<br/>type=feat, name=user-auth

    CLI->>DB: SELECT * FROM worktrees<br/>WHERE branch = 'feat-user-auth'
    DB-->>CLI: No results (new worktree)

    CLI->>Git: git worktree add<br/>feat-user-auth/ feat-user-auth
    Git->>Git: Create worktree directory
    Git->>Git: Create branch feat-user-auth
    Git-->>CLI: Worktree created

    CLI->>FS: Create directory structure
    FS-->>CLI: Directories ready

    loop For each config file
        CLI->>Sync: Read sync/repo/.env
        Sync-->>CLI: Config content
        CLI->>FS: ln -s ../../sync/repo/.env<br/>feat-user-auth/.env
        FS-->>CLI: Symlink created
    end

    CLI->>DB: INSERT INTO worktrees<br/>(path, branch, type, created_at)
    DB-->>CLI: Row inserted

    opt Event Publishing Enabled
        CLI->>RMQ: Publish worktree.created<br/>{path, branch, type}
        RMQ-->>CLI: Event published
    end

    CLI->>CLI: cd feat-user-auth/
    CLI-->>Dev: Worktree ready ✅<br/>Changed to feat-user-auth/
```

## 2. Agent Worktree Claiming Sequence

Shows exclusive worktree access for AI agents.

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant Bloodbank as Bloodbank
    participant iMi as iMi API
    participant DB as SQLite
    participant Monitor as iMi Monitor
    participant Jelmore as Jelmore

    Bloodbank->>Agent: task.assigned<br/>{task_id: 123, feature: "user-auth"}

    Agent->>iMi: imi feat user-auth<br/>--agent-id=claude-agent-1
    iMi->>DB: SELECT agent_id FROM worktrees<br/>WHERE branch = 'feat-user-auth'

    alt Worktree Available
        DB-->>iMi: agent_id IS NULL
        iMi->>DB: UPDATE worktrees<br/>SET agent_id = 'claude-agent-1',<br/>claimed_at = NOW()
        DB-->>iMi: Updated
        iMi->>Bloodbank: Publish worktree.claimed
        Bloodbank->>Monitor: worktree.claimed event
        Monitor->>Monitor: Update dashboard<br/>Show agent activity
        iMi-->>Agent: Worktree claimed ✅

        Agent->>Jelmore: jelmore start claude<br/>--session-id=task-123<br/>--prompt="Implement auth"
        Jelmore->>Jelmore: Execute AI coding session
        Jelmore->>Agent: Session complete<br/>{files_changed: [...]}

        Agent->>iMi: git add . && git commit -m "feat: auth"
        iMi->>Bloodbank: Publish worktree.commit
        Bloodbank->>Monitor: Update dashboard

        Agent->>DB: UPDATE worktrees<br/>SET agent_id = NULL,<br/>released_at = NOW()
        DB-->>Agent: Released
        Agent->>Bloodbank: Publish worktree.released
        Bloodbank->>Monitor: Clear agent activity

    else Worktree Claimed
        DB-->>iMi: agent_id = 'other-agent-2'
        iMi-->>Agent: Error: Worktree claimed by other-agent-2 ❌
        Agent->>Agent: Wait and retry OR<br/>request different worktree
    end
```

## 3. Jelmore AI Session Lifecycle

Complete session creation, execution, crash, and resume sequence.

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant CLI as Jelmore CLI
    participant Session as Session Manager
    participant Provider as Claude Provider
    participant API as Claude API
    participant Redis as Redis Cache
    participant DB as Session DB
    participant RMQ as RabbitMQ

    Dev->>CLI: jelmore start claude<br/>--prompt "Fix authentication bug"

    CLI->>Session: Create session
    Session->>Session: Generate session_id<br/>uuid-abc123

    Session->>DB: INSERT INTO sessions<br/>(id, provider, prompt, status)
    DB-->>Session: Session created

    opt Redis Available
        Session->>Redis: SET session:abc123<br/>{provider, prompt, state}
        Redis-->>Session: OK
    end

    Session->>RMQ: Publish session.started
    RMQ-->>Session: Event published

    Session->>Provider: Execute command<br/>invoke_claude(prompt)
    Provider->>API: POST /v1/messages<br/>{system, messages}

    loop Streaming Response
        API-->>Provider: Stream chunk
        Provider-->>CLI: Display output
        Provider->>Session: Save checkpoint
        Session->>Redis: Update state
    end

    API-->>Provider: Completion
    Provider->>Provider: Generate artifacts<br/>(code files)
    Provider-->>Session: Execution complete

    Session->>DB: UPDATE sessions<br/>SET status = 'completed'
    Session->>RMQ: Publish session.ended

    Session-->>Dev: Session complete ✅

    Note over Dev,RMQ: === Terminal Crashes ===

    Dev->>Dev: Terminal unexpectedly closes
    Note over Session,Redis: State preserved in Redis + DB

    Dev->>Dev: Reopen terminal
    Dev->>CLI: jelmore start claude --continue

    CLI->>Session: Resume last session
    Session->>DB: SELECT * FROM sessions<br/>WHERE status = 'in_progress'<br/>ORDER BY created_at DESC LIMIT 1
    DB-->>Session: Session abc123

    opt Redis Available
        Session->>Redis: GET session:abc123
        Redis-->>Session: {state, checkpoint}
    end

    Session->>Session: Restore state from checkpoint
    Session->>Provider: Continue from checkpoint
    Provider->>API: Resume conversation
    API-->>Provider: Continue streaming
    Provider-->>Dev: Session resumed ✅
```

## 4. Zellij-Driver Context Persistence

Terminal intent tracking and restoration across sessions.

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Zellij as Perth (Zellij)
    participant Driver as Zellij-Driver
    participant Redis as Redis
    participant Postgres as PostgreSQL

    Dev->>Zellij: Open terminal
    Zellij->>Driver: Session started<br/>session_id: xyz789

    Driver->>Dev: Capture intent prompt
    Dev-->>Driver: "Refactor database layer"

    Driver->>Redis: HSET session:xyz789<br/>intent "Refactor database layer"
    Redis-->>Driver: OK

    Dev->>Dev: Work on refactoring<br/>Create panes, edit files

    Driver->>Driver: Monitor file changes<br/>in worktree

    Dev->>Driver: Record milestone
    Dev-->>Driver: "Extracted database models"

    Driver->>Redis: LPUSH session:xyz789:milestones<br/>"Extracted database models"
    Redis-->>Driver: OK

    Dev->>Dev: Continue working

    Dev->>Driver: Record milestone
    Dev-->>Driver: "Created repository pattern"

    Driver->>Redis: LPUSH session:xyz789:milestones<br/>"Created repository pattern"
    Redis-->>Driver: OK

    Driver->>Zellij: Update pane metadata
    Zellij->>Zellij: Display milestones in status bar

    Note over Dev,Redis: === Session Interrupted ===

    Dev->>Zellij: Close terminal (Ctrl+D / crash)
    Zellij->>Driver: Session ended
    Driver->>Redis: EXPIRE session:xyz789 86400<br/>(24 hour TTL)
    Redis-->>Driver: OK

    opt Historical Archival
        Driver->>Postgres: INSERT INTO intent_history<br/>(session, intent, milestones)
        Postgres-->>Driver: Archived
    end

    Note over Dev,Postgres: === Time Passes ===

    Dev->>Zellij: Reopen terminal
    Zellij->>Driver: New session started<br/>Check for previous session

    Driver->>Redis: KEYS session:*<br/>Filter by recency
    Redis-->>Driver: Found session:xyz789

    Driver->>Redis: HGETALL session:xyz789
    Redis-->>Driver: {intent, milestones, panes}

    Driver->>Zellij: Restore context<br/>Display intent + milestones
    Zellij-->>Dev: Session context restored ✅<br/>Intent: "Refactor database layer"<br/>Milestones: [2 completed]

    Dev->>Dev: Continue work with full context
```

## 5. Configuration Sync Across Worktrees

Real-time configuration propagation via symlinks.

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant File as sync/repo/.env
    participant Watcher as File Watcher
    participant iMi as iMi Sync Manager
    participant DB as SQLite
    participant WT1 as trunk-main/
    participant WT2 as feat-api/
    participant WT3 as fix-bug/

    Dev->>File: Edit .env file<br/>Add DATABASE_URL

    File->>Watcher: File modified event
    Watcher->>iMi: Notify change in sync/

    iMi->>DB: SELECT path FROM worktrees<br/>WHERE active = true
    DB-->>iMi: [trunk-main/, feat-api/, fix-bug/]

    par Update All Worktrees
        iMi->>WT1: Verify symlink<br/>trunk-main/.env → sync/repo/.env
        WT1-->>iMi: Symlink valid ✅
    and
        iMi->>WT2: Verify symlink<br/>feat-api/.env → sync/repo/.env
        WT2-->>iMi: Symlink valid ✅
    and
        iMi->>WT3: Verify symlink<br/>fix-bug/.env → sync/repo/.env
        WT3-->>iMi: Symlink valid ✅
    end

    iMi-->>Dev: Config synced to all worktrees ✅

    Note over Dev,WT3: All worktrees now see updated .env
```

## 6. Pull Request Review Workflow

Sequence for creating and cleaning up PR review worktrees.

```mermaid
sequenceDiagram
    participant Rev as Code Reviewer
    participant iMi as iMi CLI
    participant GH as gh CLI
    participant GitHub as GitHub API
    participant Git as Git Repository
    participant DB as SQLite
    participant FS as Filesystem

    Rev->>iMi: imi review 123
    iMi->>GH: gh pr view 123<br/>--json headRefName,number

    GH->>GitHub: GET /repos/{owner}/{repo}/pulls/123
    GitHub-->>GH: {head_ref: "feat-add-auth", ...}
    GH-->>iMi: PR metadata

    iMi->>GH: gh pr checkout 123
    GH->>Git: Fetch PR branch
    Git-->>GH: Branch fetched

    iMi->>Git: git worktree add<br/>review-123/ feat-add-auth
    Git->>FS: Create review-123/ directory
    Git-->>iMi: Worktree created

    iMi->>iMi: Create symlinks<br/>sync/ → review-123/

    iMi->>DB: INSERT INTO worktrees<br/>(path, type, pr_number)
    DB-->>iMi: Registered

    iMi->>FS: cd review-123/
    iMi-->>Rev: Review worktree ready ✅

    Rev->>Rev: Review code<br/>Run tests<br/>Create suggestion commits

    Rev->>iMi: imi remove review-123

    iMi->>Git: git worktree remove review-123/
    Git->>FS: Delete directory
    Git-->>iMi: Worktree removed

    iMi->>DB: DELETE FROM worktrees<br/>WHERE path = 'review-123/'
    DB-->>iMi: Deleted

    iMi-->>Rev: Review worktree cleaned up ✅
```

## 7. Real-Time Monitoring Dashboard

Sequence showing how monitor dashboard aggregates live data.

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant CLI as iMi monitor
    participant DB as SQLite
    participant Watcher as File Watchers
    participant Git as Git CLI
    participant Display as Dashboard UI

    Dev->>CLI: imi monitor
    CLI->>DB: SELECT * FROM worktrees<br/>WHERE active = true
    DB-->>CLI: [feat-api, feat-ui, fix-bug]

    loop For each worktree
        CLI->>Watcher: Start file watcher<br/>notify::watch(path)
        Watcher-->>CLI: Watcher started
    end

    CLI->>Display: Render initial dashboard
    Display-->>Dev: Show 3 active worktrees

    Note over Dev,Display: === Real-Time Updates ===

    Watcher->>Watcher: Detect file change<br/>feat-api/src/api.ts modified
    Watcher->>CLI: File change event

    CLI->>Git: git -C feat-api/ status --short
    Git-->>CLI: M src/api.ts

    CLI->>DB: SELECT agent_id FROM worktrees<br/>WHERE path = 'feat-api/'
    DB-->>CLI: agent_id = 'claude-agent-1'

    CLI->>Display: Update worktree status<br/>feat-api: claude-agent-1 active<br/>Modified: src/api.ts (2s ago)
    Display-->>Dev: Dashboard refreshed

    Watcher->>Watcher: Detect commit<br/>feat-ui/.git/refs/heads/feat-ui
    Watcher->>CLI: Commit detected

    CLI->>Git: git -C feat-ui/ log -1<br/>--pretty=format:"%h %s"
    Git-->>CLI: abc1234 feat: add login UI

    CLI->>Display: Update worktree status<br/>feat-ui: 1 commit ahead<br/>Last commit: abc1234
    Display-->>Dev: Dashboard refreshed

    loop Every 5 seconds
        CLI->>Display: Refresh all status
        Display-->>Dev: Live updates
    end
```

## 8. Multi-Agent Coordination via Events

Shows how multiple agents coordinate worktree access via Bloodbank.

```mermaid
sequenceDiagram
    participant A1 as Agent 1 (Claude)
    participant A2 as Agent 2 (Gemini)
    participant RMQ as RabbitMQ
    participant iMi as iMi
    participant DB as SQLite

    A1->>RMQ: Subscribe to task.assigned
    A2->>RMQ: Subscribe to task.assigned

    RMQ->>A1: task.assigned<br/>{task: "Feature A"}
    RMQ->>A2: task.assigned<br/>{task: "Feature B"}

    par Agent 1 Claims
        A1->>iMi: Claim feat-feature-a
        iMi->>DB: Check availability
        DB-->>iMi: Available
        iMi->>DB: SET agent_id = 'claude-1'
        iMi->>RMQ: Publish worktree.claimed
        iMi-->>A1: Claimed ✅
    and Agent 2 Claims
        A2->>iMi: Claim feat-feature-b
        iMi->>DB: Check availability
        DB-->>iMi: Available
        iMi->>DB: SET agent_id = 'gemini-1'
        iMi->>RMQ: Publish worktree.claimed
        iMi-->>A2: Claimed ✅
    end

    par Agent 1 Works
        A1->>A1: Generate code
        A1->>iMi: Commit changes
        iMi->>RMQ: Publish worktree.commit
    and Agent 2 Works
        A2->>A2: Generate code
        A2->>iMi: Commit changes
        iMi->>RMQ: Publish worktree.commit
    end

    par Agent 1 Releases
        A1->>iMi: Release feat-feature-a
        iMi->>DB: SET agent_id = NULL
        iMi->>RMQ: Publish worktree.released
    and Agent 2 Releases
        A2->>iMi: Release feat-feature-b
        iMi->>DB: SET agent_id = NULL
        iMi->>RMQ: Publish worktree.released
    end

    Note over A1,DB: Both agents worked in parallel<br/>No conflicts, clean coordination
```

## Interaction Patterns Summary

### 1. **Synchronous Command Pattern**
- CLI command blocks until worktree ready
- Example: `imi feat` waits for git worktree creation
- Characteristics: User-friendly, immediate feedback

### 2. **Asynchronous Event Pattern**
- Agent claims worktree via events, not direct calls
- Example: `task.assigned` → claim → work → release
- Characteristics: Decoupled, scalable

### 3. **File Watch Pattern**
- React to filesystem changes in real-time
- Example: sync/ edit → detect → update symlinks
- Characteristics: Reactive, low latency

### 4. **Checkpoint/Resume Pattern**
- Continuous state persistence for crash recovery
- Example: Jelmore session interrupted → resume from checkpoint
- Characteristics: Fault tolerant, stateful

### 5. **Exclusive Lock Pattern**
- SQLite agent_id column prevents concurrent access
- Example: Agent 1 claims → Agent 2 waits
- Characteristics: Conflict-free, serialized access

## Timing Characteristics

| Sequence | Duration | Notes |
|----------|----------|-------|
| Worktree Creation | 500ms-1s | Depends on git repo size |
| Agent Claim | 10-50ms | SQLite transaction |
| Session Start | 1-5s | AI API latency |
| Context Restore | 100-500ms | Redis lookup |
| Config Sync | 50-200ms | Per worktree |
| Monitor Refresh | 100ms-1s | Real-time updates |

## Related Documentation

- [Data Flow Diagrams](./data-flows.md) - Data movement patterns
- [Dependency Graph](./dependencies.md) - Component dependencies
- [C4 Context](./c4-context.md) - System context

---

**Version**: 1.0.0
**Last Updated**: 2026-01-29
**Maintained By**: 33GOD Architecture Team
