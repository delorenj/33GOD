use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Raw envelope received from hookd-emit over the Unix socket.
/// This is the wire format: minimal, no enrichment.
#[derive(Debug, Deserialize)]
pub struct HookEnvelope {
    pub event_type: String,
    pub tool_name: String,
    pub payload: Value,
    pub timestamp: DateTime<Utc>,
    pub pid: u32,
}

/// Git repository context gathered by the daemon.
#[derive(Debug, Clone, Serialize)]
pub struct RepoContext {
    pub git_root: String,
    pub branch: String,
    pub head_sha: String,
    pub remote_url: Option<String>,
}

/// Enriched event published to Bloodbank.
/// This is the canonical schema consumers (mutation-ledger) receive.
#[derive(Debug, Serialize)]
pub struct ToolMutationEvent {
    pub event_type: String,
    pub hook_type: String,
    pub tool_name: String,
    pub agent_id: String,
    pub repo: RepoContext,
    pub file_path: Option<String>,
    pub file_ext: Option<String>,
    pub lines_changed: Option<u32>,
    pub raw_payload: Value,
    pub timestamp: DateTime<Utc>,
    pub source_pid: u32,
    pub correlation_id: String,
}
