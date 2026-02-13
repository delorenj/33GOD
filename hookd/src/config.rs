use std::env;
use std::path::PathBuf;

/// Daemon configuration resolved from environment variables with sensible defaults.
#[derive(Debug, Clone)]
pub struct Config {
    pub socket_path: PathBuf,
    pub amqp_url: String,
    pub exchange_name: String,
    pub pid_file: PathBuf,
    pub agent_id: String,
    pub git_cache_ttl_secs: u64,
    pub event_buffer_size: usize,
}

impl Config {
    pub fn from_env() -> Self {
        let uid = unsafe { libc::getuid() };
        let run_dir = format!("/run/user/{uid}");

        let raw_amqp = env::var("HOOKD_AMQP_URL")
            .or_else(|_| env::var("RABBITMQ_URL"))
            .or_else(|_| env::var("RABBIT_URL"))
            .unwrap_or_else(|_| "amqp://localhost:5672/%2f".to_string());

        // lapin treats trailing "/" as empty vhost; ensure we use "%2f" for default vhost
        let amqp_url = normalize_amqp_vhost(&raw_amqp);

        Self {
            socket_path: env::var("HOOKD_SOCKET")
                .map(PathBuf::from)
                .unwrap_or_else(|_| PathBuf::from(format!("{run_dir}/hookd.sock"))),
            amqp_url,
            exchange_name: env::var("HOOKD_EXCHANGE")
                .unwrap_or_else(|_| "bloodbank.events.v1".to_string()),
            pid_file: env::var("HOOKD_PID_FILE")
                .map(PathBuf::from)
                .unwrap_or_else(|_| PathBuf::from(format!("{run_dir}/hookd.pid"))),
            agent_id: env::var("CLAUDE_AGENT_ID").unwrap_or_else(|_| "unknown".to_string()),
            git_cache_ttl_secs: env::var("HOOKD_GIT_CACHE_TTL")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(30),
            event_buffer_size: env::var("HOOKD_BUFFER_SIZE")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(1000),
        }
    }
}

/// Normalize AMQP URL vhost for lapin compatibility.
/// lapin interprets a trailing "/" as an empty vhost, while RabbitMQ clients
/// like pika treat it as the default "/" vhost. This function ensures the
/// URL always ends with "/%2f" when no explicit vhost is specified.
fn normalize_amqp_vhost(url: &str) -> String {
    // Already has an explicit vhost (e.g., /%2f or /myvhost)
    if url.contains("/%2f") || url.contains("/%2F") {
        return url.to_string();
    }

    // Strip scheme to work with authority+path
    let (scheme, rest) = if let Some(idx) = url.find("://") {
        (&url[..idx + 3], &url[idx + 3..])
    } else {
        ("amqp://", url)
    };

    // Find the port or host boundary, then check what's after
    // Pattern: user:pass@host:port/ or user:pass@host:port
    if let Some(slash_idx) = rest.find('/') {
        let after_slash = &rest[slash_idx + 1..];
        if after_slash.is_empty() {
            // URL like amqp://user:pass@host:5672/ → add %2f
            return format!("{}{}%2f", scheme, &rest[..=slash_idx]);
        }
        // Has explicit vhost already
        url.to_string()
    } else {
        // No slash after host:port → append /%2f
        format!("{}{}/{}", scheme, rest, "%2f")
    }
}
