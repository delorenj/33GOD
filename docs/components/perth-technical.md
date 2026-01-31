# Perth - Technical Implementation Guide

## Overview

Perth is a specialized fork of Zellij (terminal multiplexer) designed as the primary IDE for the 33GOD ecosystem. It extends Zellij with native support for visual notifications, animation engine, PostgreSQL persistence, and ZDrive integration for programmatic workspace control.

## Implementation Details

**Language**: Rust (2021 edition)
**Base**: Zellij fork (terminal multiplexer)
**Database**: PostgreSQL 16 (session persistence)
**External Integration**: ZDrive CLI (Redis-backed context)
**UI**: TUI with custom notification system

### Key Technologies

- **Zellij**: Base terminal multiplexer (panes, tabs, layouts)
- **tokio**: Async runtime
- **PostgreSQL**: Session state persistence
- **Redis**: ZDrive metadata (via external CLI)
- **WebAssembly**: Plugin system

## Architecture & Design Patterns

### Notification System

```rust
// perth/src/notification/mod.rs
#[derive(Clone, Debug)]
pub enum NotificationStyle {
    Error,
    Success,
    Warning,
}

#[derive(Clone, Debug)]
pub struct Notification {
    pub pane_id: usize,
    pub style: NotificationStyle,
    pub message: String,
    pub created_at: Instant,
    pub auto_clear_on_focus: bool,
}

impl Notification {
    pub fn border_color(&self) -> Color {
        match self.style {
            NotificationStyle::Error => Color::Rgb(255, 0, 0),
            NotificationStyle::Success => Color::Rgb(0, 255, 0),
            NotificationStyle::Warning => Color::Rgb(255, 165, 0),
        }
    }
}

// CLI command
// zellij notify --pane-id 3 --style error --message "Build failed"
```

### Animation Engine

```rust
// perth/src/animation/mod.rs
pub struct CandycaneAnimation {
    frames: Vec<ColorFrame>,
    current_frame: usize,
    fps: u32,
}

impl CandycaneAnimation {
    pub fn new() -> Self {
        Self {
            frames: vec![
                ColorFrame::Block,
                ColorFrame::Dark,
                ColorFrame::Medium,
                ColorFrame::Light,
            ],
            current_frame: 0,
            fps: 60,
        }
    }

    pub fn update(&mut self, delta: Duration) {
        // Advance frame based on FPS
        let frame_duration = Duration::from_millis(1000 / self.fps as u64);

        if delta >= frame_duration {
            self.current_frame = (self.current_frame + 1) % self.frames.len();
        }
    }

    pub fn render(&self) -> ColorFrame {
        self.frames[self.current_frame]
    }
}
```

### PostgreSQL Persistence

```rust
// perth/src/persistence/mod.rs
use tokio_postgres::{Client, NoTls};

pub struct PersistenceManager {
    client: Client,
}

impl PersistenceManager {
    pub async fn new(database_url: &str) -> Result<Self, Error> {
        let (client, connection) = tokio_postgres::connect(database_url, NoTls).await?;

        // Spawn connection handler
        tokio::spawn(async move {
            if let Err(e) = connection.await {
                eprintln!("connection error: {}", e);
            }
        });

        Ok(Self { client })
    }

    pub async fn save_session(&self, session: &Session) -> Result<(), Error> {
        self.client
            .execute(
                "INSERT INTO sessions (id, layout, panes, tabs, created_at) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE SET layout = $2, panes = $3, tabs = $4",
                &[
                    &session.id,
                    &serde_json::to_value(&session.layout)?,
                    &serde_json::to_value(&session.panes)?,
                    &serde_json::to_value(&session.tabs)?,
                    &session.created_at,
                ],
            )
            .await?;

        Ok(())
    }

    pub async fn restore_session(&self, session_id: &str) -> Result<Session, Error> {
        let row = self.client
            .query_one(
                "SELECT id, layout, panes, tabs, created_at FROM sessions WHERE id = $1",
                &[&session_id],
            )
            .await?;

        Ok(Session {
            id: row.get(0),
            layout: serde_json::from_value(row.get(1))?,
            panes: serde_json::from_value(row.get(2))?,
            tabs: serde_json::from_value(row.get(3))?,
            created_at: row.get(4),
        })
    }
}
```

### ZDrive Integration

```rust
// perth/src/zdrive/mod.rs
use std::process::Command;

pub struct ZDriveClient;

impl ZDriveClient {
    pub fn navigate_to_pane(pane_name: &str) -> Result<(), Error> {
        // Call external zdrive CLI
        Command::new("zdrive")
            .arg("pane")
            .arg(pane_name)
            .status()?;

        Ok(())
    }

    pub fn log_intent(pane_name: &str, message: &str) -> Result<(), Error> {
        Command::new("zdrive")
            .arg("pane")
            .arg("log")
            .arg(pane_name)
            .arg(message)
            .status()?;

        Ok(())
    }

    pub fn attach_with_ticket(ticket_id: &str) -> Result<(), Error> {
        Command::new("zdrive")
            .arg("attach")
            .arg("--plane-ticket")
            .arg(ticket_id)
            .status()?;

        Ok(())
    }
}
```

## Configuration

```yaml
# ~/.config/zellij/config.yaml
database_url: postgres://perth:perth@localhost:5432/perth

notifications:
  auto_clear_on_focus: true
  animation_fps: 60

zdrive:
  enabled: true
  redis_url: redis://127.0.0.1:6379/
```

## Integration Points

### Holocene Dashboard Tab

Perth includes a built-in Dashboard tab that integrates:
- **Bloodbank Feed**: Real-time event stream
- **iMi Browser**: Worktree navigation
- **ZDrive Browser**: Intent history and context

### Agent Coordination

Agents can control Perth programmatically:

```rust
// Agent spawns new pane for task
ZDriveClient::navigate_to_pane("agent-task-123");
ZDriveClient::log_intent("agent-task-123", "Started implementing feature X");

// Perth shows notification when task completes
Notification::show(pane_id, NotificationStyle::Success, "Task complete");
```

## Performance

- **Animation FPS**: 60fps (degrades to 30fps under high CPU)
- **Session Save**: <100ms (write-behind caching)
- **Memory**: +50MB over base Zellij

## Related Components

- **Zellij Driver (zdrive)**: External CLI for workspace management
- **iMi**: Worktree management (displayed in Perth dashboard)
- **Bloodbank**: Event stream (displayed in Perth dashboard)

---

**Quick Reference**:
- GitHub: `33GOD/perth`
- Base: Zellij fork
- Database: PostgreSQL (port 5432)
- Docs: `docs/sprint-plan-perth-2026-01-22.md`
