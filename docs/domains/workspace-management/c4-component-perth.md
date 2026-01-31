# C4 Component Level: Perth - Terminal Workspace Manager

## Overview
- **Name**: Perth (formerly Zellij)
- **Description**: A terminal workspace with batteries included - terminal multiplexer with PostgreSQL persistence
- **Type**: Terminal Multiplexer Application
- **Technology**: Rust, PostgreSQL, WASM (WebAssembly plugins)
- **Version**: 0.44.0

## Purpose

Perth is a terminal workspace manager (fork of Zellij) that provides sophisticated session, tab, and pane management with persistent state storage in PostgreSQL. It enables developers and AI agents to maintain complex terminal layouts, restore sessions across restarts, and coordinate work through a plugin ecosystem.

Perth extends the standard terminal multiplexer paradigm with write-behind caching for persistence, graceful degradation when database is unavailable, and a rich plugin API for extensibility.

## Software Features

### Session Management
- **Session Creation**: Create named terminal sessions with custom layouts
- **Session Persistence**: Persist session state to PostgreSQL with write-behind caching
- **Session Restoration**: Restore sessions from database after restart
- **Session Listing**: List all active and historical sessions
- **Session Metadata**: Store arbitrary metadata per session

### Tab Management
- **Tab Creation**: Create named tabs within sessions
- **Tab Layouts**: Configure tab layouts (horizontal, vertical, stacked)
- **Tab Persistence**: Persist tab state and configuration
- **Tab Switching**: Fast tab navigation with keybindings
- **Tab Renaming**: Dynamic tab renaming based on content

### Pane Management
- **Pane Splitting**: Split panes horizontally, vertically, or in grids
- **Pane Focus**: Navigate between panes with directional keys
- **Pane Resizing**: Resize panes interactively or programmatically
- **Pane Floating**: Create floating panes over layout
- **Pane Stacking**: Stack panes for space-efficient layouts
- **Pane Commands**: Launch commands in specific panes
- **Pane Persistence**: Persist pane state including CWD and command

### Plugin System
- **WASM Runtime**: Run plugins as WebAssembly modules
- **Plugin API**: Rich API for plugin-host communication
- **Built-in Plugins**: Status bar, tab bar, file manager, session manager
- **Plugin Configuration**: Configure plugins with custom settings
- **Plugin Events**: React to terminal events in plugins

### Layout Management
- **Layout Templates**: Pre-defined layout configurations
- **Layout Loading**: Load layouts from KDL files
- **Layout Swapping**: Dynamically swap layouts at runtime
- **Layout Manager Plugin**: Visual layout management

### IPC (Inter-Process Communication)
- **Client-Server**: Client-server architecture with Unix sockets
- **Command Dispatch**: Send commands from CLI to running sessions
- **Action System**: Rich action system for programmatic control
- **Pipe Protocol**: Pipe commands into panes or plugins

### Persistence Strategy (NFR-003)
- **Write-Behind Caching**: Queue writes for async processing
- **Graceful Degradation**: Continue operation if database unavailable
- **Connection Pooling**: Efficient database connection management (10 max, 2 min)
- **Migration Management**: Automatic schema migrations via SQLx

## Code Elements

This component is organized as a Cargo workspace with multiple crates:

### Core Crates
- **zellij-server/** - Server runtime, persistence, screen management
  - `src/lib.rs` - Server core orchestration
  - `src/screen.rs` - Terminal screen and layout management
  - `src/route.rs` - Command routing and action dispatch
  - `src/panes/` - Pane lifecycle management
  - `src/persistence/` - PostgreSQL persistence layer
  - `src/plugins/` - Plugin runtime and API
  - `src/pty.rs` - PTY (pseudo-terminal) management
  - `src/background_jobs.rs` - Async job processing
  - `src/os_input_output.rs` - OS-level I/O operations

- **zellij-client/** - Client CLI and server communication
  - Command parsing and dispatch
  - IPC socket communication
  - Session attachment logic

- **zellij-utils/** - Shared utilities, types, and configuration
  - KDL layout parsing
  - Configuration management
  - Common data structures
  - Logging infrastructure

- **zellij-tile/** - Plugin API for WASM plugins
  - Plugin trait definitions
  - Event types
  - UI component helpers

### Default Plugins
- **default-plugins/status-bar** - Status bar with session info
- **default-plugins/tab-bar** - Tab navigation and display
- **default-plugins/strider** - File manager plugin
- **default-plugins/session-manager** - Session management UI
- **default-plugins/configuration** - Configuration editor
- **default-plugins/plugin-manager** - Plugin installer
- **default-plugins/layout-manager** - Layout editor

### Build System
- **xtask/** - Build automation and CI tasks
  - `src/build.rs` - Build orchestration
  - `src/test.rs` - Test runner
  - `src/ci.rs` - CI pipeline tasks

## Component Architecture

```mermaid
C4Component
    title Component Diagram for Perth Terminal Workspace

    Container_Boundary(perth, "Perth Application") {
        Component(client, "Client CLI", "Rust/Clap", "Parse commands and connect to server")
        Component(server, "Server Core", "Rust/Tokio", "Main server runtime and orchestration")
        Component(screen, "Screen Manager", "Rust", "Terminal screen rendering and layout")
        Component(panes, "Pane Manager", "Rust", "Pane lifecycle and PTY management")
        Component(route, "Route Handler", "Rust", "Action routing and dispatch")
        Component(persist, "Persistence Manager", "SQLx + PostgreSQL", "Write-behind caching for state")
        Component(plugins, "Plugin Runtime", "WASM", "Load and execute WASM plugins")
        Component(pty, "PTY Manager", "Rust/nix", "Pseudo-terminal allocation")
        Component(ipc, "IPC Handler", "Unix Sockets", "Client-server communication")
        Component(config, "Config Manager", "KDL", "Parse and validate configuration")
        Component(layout, "Layout Engine", "KDL", "Parse and apply layout templates")
        Component(background, "Background Jobs", "Tokio", "Async task processing")
    }

    Container_Boundary(plugins_boundary, "Plugin Ecosystem") {
        Component(status_bar, "Status Bar", "WASM", "Session status display")
        Component(tab_bar, "Tab Bar", "WASM", "Tab navigation UI")
        Component(strider, "Strider", "WASM", "File manager")
        Component(session_mgr, "Session Manager", "WASM", "Session management UI")
    }

    ContainerDb(postgres, "PostgreSQL", "Database", "Sessions, tabs, panes, metadata")
    System_Ext(terminal, "Terminal", "TTY", "User terminal emulator")
    System_Ext(shell, "Shell", "Process", "User shell (bash, zsh, etc.)")
    System_Ext(zdrive, "Zellij Driver", "Service", "Cognitive context tracking")

    ' Core relationships
    Rel(client, ipc, "Connects via", "Unix socket")
    Rel(ipc, server, "Dispatches to", "Action messages")
    Rel(server, route, "Routes actions to", "Handler functions")
    Rel(route, screen, "Updates", "Layout changes")
    Rel(route, panes, "Controls", "Pane actions")
    Rel(screen, panes, "Contains", "Pane tree")
    Rel(panes, pty, "Allocates", "PTY per pane")
    Rel(server, persist, "Queues writes to", "Async channel")
    Rel(server, plugins, "Loads", "WASM modules")
    Rel(server, background, "Spawns", "Async tasks")
    Rel(server, config, "Reads", "Configuration")
    Rel(screen, layout, "Applies", "Layout templates")

    ' Plugin relationships
    Rel(plugins, status_bar, "Runs", "WASM")
    Rel(plugins, tab_bar, "Runs", "WASM")
    Rel(plugins, strider, "Runs", "WASM")
    Rel(plugins, session_mgr, "Runs", "WASM")

    ' External relationships
    Rel(persist, postgres, "Writes async", "SQL")
    Rel(client, terminal, "Attached to", "PTY")
    Rel(pty, shell, "Spawns", "Fork/exec")
    Rel(panes, zdrive, "Tracks state in", "Redis")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## Interfaces

### Command-Line Interface

**Protocol**: CLI (Command-Line Interface)
**Description**: Client interface for session management and commands

**Operations**:
- `perth` - Launch new session or attach to existing
- `perth attach <session>` - Attach to session by name
- `perth list-sessions` - List all sessions
- `perth kill-session <session>` - Terminate session
- `perth action <action>` - Send action to running session
- `perth run <command>` - Run command in new pane
- `perth edit <file>` - Edit file in new pane
- `perth plugin <url>` - Load plugin in session

### IPC Interface

**Protocol**: Unix Domain Sockets + Protobuf
**Description**: Client-server communication for action dispatch

**Message Types**:
- `ClientToServerMsg::Action(Action)` - Execute action in server
- `ClientToServerMsg::TerminalResize` - Notify of terminal resize
- `ClientToServerMsg::TerminalPixelDimensions` - Pixel dimensions
- `ServerToClientMsg::Exit` - Server shutdown notification
- `ServerToClientMsg::UnblockInputThread` - Resume input processing

### Plugin API

**Protocol**: WASM Interface
**Description**: Plugin-host communication API

**Capabilities**:
- **State Queries**: Get pane list, tab info, session state
- **UI Updates**: Update plugin UI, render components
- **Event Handling**: React to pane focus, tab switch, key press
- **Action Dispatch**: Trigger actions in host (new pane, close tab)
- **File Operations**: Read/write files, list directories
- **IPC**: Communicate with other plugins

**Plugin Trait**:
```rust
trait ZellijPlugin {
    fn load(&mut self);
    fn update(&mut self, event: Event);
    fn render(&mut self, rows: usize, cols: usize);
}
```

### Database Interface

**Protocol**: PostgreSQL (SQLx)
**Description**: Persistent state storage with write-behind caching

**Tables**:
- `sessions` - Session metadata and last active timestamp
- `tabs` - Tab configuration and position
- `panes` - Pane state including command, CWD, size, position
- `layouts` - Saved layout templates
- `metadata` - Arbitrary key-value metadata

**Write Operations** (Queued Async):
- `CreateSession(SessionRecord)` - Insert new session
- `UpdateSession{id, last_active}` - Update activity timestamp
- `CreateTab(TabRecord)` - Insert new tab
- `UpdateTab(TabRecord)` - Update tab state
- `DeleteTab(tab_id)` - Remove tab
- `CreatePane(PaneRecord)` - Insert new pane
- `UpdatePane(PaneRecord)` - Update pane state
- `DeletePane(pane_id)` - Remove pane

**Read Operations** (Sync):
- `get_session(name)` - Retrieve session by name
- `list_sessions()` - List all sessions
- `get_tabs(session_id)` - Get tabs for session
- `get_panes(tab_id)` - Get panes for tab

## Dependencies

### Internal Components
- **Client** uses **IPC Handler** for server communication
- **Server** uses **Route Handler** for action dispatch
- **Route Handler** uses **Screen Manager** for layout updates
- **Screen Manager** uses **Pane Manager** for pane tree
- **Pane Manager** uses **PTY Manager** for terminal allocation
- **Server** uses **Persistence Manager** for state storage
- **Server** uses **Plugin Runtime** for WASM execution
- **Server** uses **Config Manager** for settings
- **Screen Manager** uses **Layout Engine** for templates

### External Systems
- **PostgreSQL**: State persistence (graceful degradation if unavailable)
- **Terminal Emulator**: User interface (any ANSI-compatible terminal)
- **Shell**: User shell spawned in panes (bash, zsh, fish, etc.)
- **Zellij Driver**: Cognitive context tracking via Redis (optional)

### Rust Crates
- `tokio` v1.38 - Async runtime (full features)
- `sqlx` v0.7 - PostgreSQL driver with compile-time query checking
- `clap` v3.2 - CLI framework
- `interprocess` v1.2 - Unix socket IPC
- `nix` v0.23 - Unix system calls (PTY, signals)
- `prost` v0.11 - Protobuf serialization for IPC
- `kdl` v4.5 - KDL parser for layouts and config
- `termwiz` v0.23 - Terminal rendering
- `vte` v0.11 - ANSI escape sequence parsing
- `notify` v6.1 - File watching for config reloads
- `uuid` v1.4 - UUID generation for IDs
- `serde` + `serde_json` - Serialization
- `log` v0.4 - Logging framework

## Data Models

### SessionRecord
```rust
struct SessionRecord {
    id: Uuid,
    name: String,
    created_at: DateTime<Utc>,
    last_active: DateTime<Utc>,
    layout_name: Option<String>,
    metadata: serde_json::Value,
}
```

### TabRecord
```rust
struct TabRecord {
    id: Uuid,
    session_id: Uuid,
    position: i32,  // Tab order
    name: String,
    is_focused: bool,
    layout_type: String,  // "horizontal", "vertical", "stacked"
    metadata: serde_json::Value,
}
```

### PaneRecord
```rust
struct PaneRecord {
    id: Uuid,
    tab_id: Uuid,
    pane_id: Option<i32>,  // Internal pane ID
    title: String,
    command: Option<String>,
    cwd: String,
    is_focused: bool,
    is_floating: bool,
    is_stacked: bool,
    position_x: i32,
    position_y: i32,
    width: u16,
    height: u16,
    metadata: serde_json::Value,
}
```

### WriteOperation (Async Queue)
```rust
enum WriteOperation {
    CreateSession(SessionRecord),
    UpdateSession { id: Uuid, last_active: DateTime<Utc> },
    CreateTab(TabRecord),
    UpdateTab(TabRecord),
    DeleteTab(Uuid),
    CreatePane(PaneRecord),
    UpdatePane(PaneRecord),
    DeletePane(Uuid),
}
```

## Configuration

### Config File: `~/.config/perth/config.kdl`

```kdl
// Database connection
persistence {
    database_url "postgresql://perth:password@localhost:5432/perth"
    // Gracefully degrades if unavailable (NFR-003)
    required false
}

// Keybindings
keybindings {
    normal {
        bind "Ctrl p" { SwitchToMode "Pane"; }
        bind "Ctrl t" { SwitchToMode "Tab"; }
    }
    pane {
        bind "h" { MoveFocus "Left"; }
        bind "l" { MoveFocus "Right"; }
        bind "j" { MoveFocus "Down"; }
        bind "k" { MoveFocus "Up"; }
    }
}

// Layouts
layouts {
    layout_dir "~/.config/perth/layouts"
}

// Plugins
plugins {
    status-bar location="file:~/.config/perth/plugins/status-bar.wasm"
    tab-bar location="file:~/.config/perth/plugins/tab-bar.wasm"
}
```

### Layout File: `~/.config/perth/layouts/dev.kdl`

```kdl
layout {
    pane split_direction="vertical" {
        pane split_direction="horizontal" {
            pane command="nvim"
            pane
        }
        pane size="30%"
    }
}
```

## Error Handling

### PersistenceError Enum
```rust
enum PersistenceError {
    ConnectionFailed(String),
    QueryFailed(String),
    MigrationFailed(String),
    SerializationError(String),
}

type PersistenceResult<T> = Result<T, PersistenceError>;
```

### Graceful Degradation (NFR-003)
- If PostgreSQL is unavailable, Perth continues without persistence
- Write operations silently ignored (no errors to user)
- Read operations return empty results
- Log warnings for debugging

## Security

### IPC Security
- Unix sockets restricted to user permissions (0700)
- Socket files in user-specific directory
- No network exposure

### Plugin Sandboxing
- WASM plugins run in sandboxed environment
- Limited host API access
- No direct file system or network access (only via API)

### Database Security
- Connection string from environment variable or config
- No hardcoded credentials
- PostgreSQL row-level security supported

## Performance

### Write-Behind Caching
- Async write queue to prevent blocking main thread
- Batch writes when possible
- Unbounded channel (no backpressure on UI)
- Background worker processes queue continuously

### Connection Pooling
- PostgreSQL pool: 10 max, 2 min connections
- 5-second acquire timeout
- Automatic connection recycling

### Terminal Rendering
- Dirty region tracking for efficient updates
- ANSI escape sequence optimization
- Minimal redraws on pane focus changes

### Plugin Performance
- WASM compilation cached
- Efficient event dispatch to plugins
- Plugins run in main thread (fast communication)

## Testing

### End-to-End Tests
- Located in `src/tests/e2e/`
- Remote runner for distributed testing
- Test cases in `cases.rs`
- Step definitions in `steps.rs`

### Unit Tests
- Component-level tests throughout codebase
- Mock-based persistence testing
- PTY simulation for pane testing

### Snapshot Testing
- Uses `insta` crate for snapshot tests
- Terminal output snapshot comparisons
- Layout rendering verification

## Deployment

### Prerequisites
- Rust 1.92+ (2021 edition)
- PostgreSQL 14+ (optional, graceful degradation)
- Unix-like OS (Linux, macOS)

### Build
```bash
cargo build --release
# Binary: target/release/perth
```

### Installation
```bash
cargo install --path .
# OR
cp target/release/perth ~/.local/bin/
```

### Database Setup (Optional)
```bash
# Set connection string
export DATABASE_URL="postgresql://perth:password@localhost:5432/perth"

# Migrations run automatically on first connection
```

### Configuration
```bash
mkdir -p ~/.config/perth/layouts ~/.config/perth/plugins
perth setup --generate-config
# Edit ~/.config/perth/config.kdl
```

### Plugin Installation
```bash
# Plugins installed automatically from config
# Or manually:
cp plugins/*.wasm ~/.config/perth/plugins/
```

---

**Component Version**: 0.44.0
**Last Updated**: 2026-01-29
**Rust Edition**: 2021
**License**: MIT
**Upstream**: Zellij (forked for 33GOD platform)
