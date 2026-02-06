mod config;
mod enrichment;
mod envelope;
mod publisher;

use std::fs;

use tokio::io::AsyncBufReadExt;
use tokio::net::UnixListener;
use tokio::signal;
use tracing::{error, info, warn};

use config::Config;
use enrichment::Enricher;
use envelope::HookEnvelope;
use publisher::Publisher;

#[tokio::main]
async fn main() {
    // Structured logging via RUST_LOG env (default: info)
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "hookd=info".parse().unwrap()),
        )
        .json()
        .init();

    let config = Config::from_env();
    info!(
        socket = %config.socket_path.display(),
        amqp = %config.amqp_url,
        exchange = %config.exchange_name,
        "hookd starting"
    );

    // Clean stale socket
    if config.socket_path.exists() {
        warn!(path = %config.socket_path.display(), "removing stale socket");
        fs::remove_file(&config.socket_path).expect("failed to remove stale socket");
    }

    // Ensure parent directory exists
    if let Some(parent) = config.socket_path.parent() {
        fs::create_dir_all(parent).ok();
    }

    // Write PID file
    if let Some(parent) = config.pid_file.parent() {
        fs::create_dir_all(parent).ok();
    }
    fs::write(&config.pid_file, std::process::id().to_string())
        .expect("failed to write PID file");

    // Start AMQP publisher
    let publisher = Publisher::spawn(&config);

    // Start enricher
    let enricher = Enricher::new(config.agent_id.clone(), config.git_cache_ttl_secs);

    // Bind Unix socket
    let listener = UnixListener::bind(&config.socket_path).expect("failed to bind Unix socket");
    info!(path = %config.socket_path.display(), "listening on Unix socket");

    // Main accept loop with graceful shutdown
    let socket_path = config.socket_path.clone();
    let pid_file = config.pid_file.clone();

    tokio::select! {
        _ = accept_loop(listener, &enricher, &publisher) => {
            info!("accept loop ended");
        }
        _ = shutdown_signal() => {
            info!("shutdown signal received");
        }
    }

    // Cleanup
    info!("cleaning up");
    fs::remove_file(&socket_path).ok();
    fs::remove_file(&pid_file).ok();
    info!("hookd stopped");
}

/// Accept connections and process envelopes.
async fn accept_loop(listener: UnixListener, enricher: &Enricher, publisher: &Publisher) {
    loop {
        match listener.accept().await {
            Ok((stream, _addr)) => {
                let reader = tokio::io::BufReader::new(stream);
                let mut lines = reader.lines();

                // Each connection can send multiple newline-delimited JSON messages
                while let Ok(Some(line)) = lines.next_line().await {
                    if line.is_empty() {
                        continue;
                    }

                    match serde_json::from_str::<HookEnvelope>(&line) {
                        Ok(envelope) => {
                            let tool = envelope.tool_name.clone();
                            match enricher.enrich(envelope).await {
                                Some(event) => {
                                    publisher.publish(event).await;
                                }
                                None => {
                                    warn!(tool = %tool, "failed to enrich envelope (no repo context)");
                                }
                            }
                        }
                        Err(e) => {
                            warn!(error = %e, line = %line.chars().take(200).collect::<String>(), "invalid envelope JSON");
                        }
                    }
                }
            }
            Err(e) => {
                error!(error = %e, "failed to accept connection");
            }
        }
    }
}

/// Wait for SIGTERM or SIGINT for graceful shutdown.
async fn shutdown_signal() {
    let ctrl_c = signal::ctrl_c();
    let mut sigterm = signal::unix::signal(signal::unix::SignalKind::terminate())
        .expect("failed to register SIGTERM handler");

    tokio::select! {
        _ = ctrl_c => { info!("received SIGINT"); }
        _ = sigterm.recv() => { info!("received SIGTERM"); }
    }
}
