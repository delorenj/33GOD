use std::collections::HashMap;
use std::path::Path;
use std::process::Command;
use std::sync::Arc;
use std::time::Instant;

use serde_json::Value;
use tokio::sync::RwLock;
use tracing::{debug, warn};
use uuid::Uuid;

use crate::envelope::{HookEnvelope, RepoContext, ToolMutationEvent};

/// Cached git context with TTL for avoiding repeated subprocess calls.
struct CachedContext {
    context: RepoContext,
    fetched_at: Instant,
}

/// Enriches raw hook envelopes with repository context and payload extraction.
pub struct Enricher {
    agent_id: String,
    cache_ttl_secs: u64,
    // Cache keyed by git_root path
    cache: Arc<RwLock<HashMap<String, CachedContext>>>,
}

impl Enricher {
    pub fn new(agent_id: String, cache_ttl_secs: u64) -> Self {
        Self {
            agent_id,
            cache_ttl_secs,
            cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Enrich a raw HookEnvelope into a ToolMutationEvent.
    pub async fn enrich(&self, envelope: HookEnvelope) -> Option<ToolMutationEvent> {
        let file_path = extract_file_path(&envelope.payload);
        let repo_context = self.resolve_repo_context(file_path.as_deref()).await?;
        let file_ext = file_path
            .as_deref()
            .and_then(|p| Path::new(p).extension())
            .map(|e| e.to_string_lossy().to_string());
        let lines_changed = extract_lines_changed(&envelope.payload);

        Some(ToolMutationEvent {
            event_type: format!("tool.mutation.{}", envelope.tool_name.to_lowercase()),
            hook_type: envelope.event_type,
            tool_name: envelope.tool_name,
            agent_id: self.agent_id.clone(),
            repo: repo_context,
            file_path,
            file_ext,
            lines_changed,
            raw_payload: envelope.payload,
            timestamp: envelope.timestamp,
            source_pid: envelope.pid,
            correlation_id: Uuid::new_v4().to_string(),
        })
    }

    /// Resolve git context, using cache when possible.
    async fn resolve_repo_context(&self, file_path: Option<&str>) -> Option<RepoContext> {
        // Determine working directory for git commands
        let work_dir = file_path
            .and_then(|p| Path::new(p).parent())
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_else(|| ".".to_string());

        let git_root = git_command(&work_dir, &["rev-parse", "--show-toplevel"])?;

        // Check cache
        {
            let cache = self.cache.read().await;
            if let Some(cached) = cache.get(&git_root) {
                if cached.fetched_at.elapsed().as_secs() < self.cache_ttl_secs {
                    debug!(git_root = %git_root, "using cached repo context");
                    return Some(cached.context.clone());
                }
            }
        }

        // Cache miss or stale: resolve fresh context
        let branch = git_command(&git_root, &["branch", "--show-current"])
            .unwrap_or_else(|| "detached".to_string());
        let head_sha = git_command(&git_root, &["rev-parse", "HEAD"])?;
        let remote_url = git_command(&git_root, &["remote", "get-url", "origin"]);

        let context = RepoContext {
            git_root: git_root.clone(),
            branch,
            head_sha,
            remote_url,
        };

        // Update cache
        {
            let mut cache = self.cache.write().await;
            cache.insert(
                git_root,
                CachedContext {
                    context: context.clone(),
                    fetched_at: Instant::now(),
                },
            );
        }

        Some(context)
    }
}

/// Extract file_path from the tool payload.
/// Tries common Claude Code payload shapes.
fn extract_file_path(payload: &Value) -> Option<String> {
    // PostToolUse shape: payload.tool_input.file_path or payload.tool_input.path
    payload
        .get("tool_input")
        .and_then(|ti| {
            ti.get("file_path")
                .or_else(|| ti.get("path"))
                .or_else(|| ti.get("notebook_path"))
        })
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
}

/// Estimate lines changed from the payload content.
fn extract_lines_changed(payload: &Value) -> Option<u32> {
    let tool_input = payload.get("tool_input")?;

    // Write tool: count lines in content
    if let Some(content) = tool_input.get("content").and_then(|v| v.as_str()) {
        return Some(content.lines().count() as u32);
    }

    // Edit tool: count lines in new_string
    if let Some(new_str) = tool_input.get("new_string").and_then(|v| v.as_str()) {
        return Some(new_str.lines().count() as u32);
    }

    None
}

/// Run a git command and return trimmed stdout, or None on failure.
fn git_command(work_dir: &str, args: &[&str]) -> Option<String> {
    match Command::new("git").args(args).current_dir(work_dir).output() {
        Ok(output) if output.status.success() => {
            Some(String::from_utf8_lossy(&output.stdout).trim().to_string())
        }
        Ok(output) => {
            debug!(
                args = ?args,
                stderr = %String::from_utf8_lossy(&output.stderr),
                "git command failed"
            );
            None
        }
        Err(e) => {
            warn!(error = %e, "failed to run git");
            None
        }
    }
}
