use lapin::{
    options::{BasicPublishOptions, ExchangeDeclareOptions},
    types::FieldTable,
    BasicProperties, Channel, Connection, ConnectionProperties, ExchangeKind,
};
use tokio::sync::mpsc;
use tokio::time::{sleep, Duration};
use tracing::{error, info, warn};

use crate::config::Config;
use crate::envelope::ToolMutationEvent;

/// AMQP publisher with persistent connection, reconnect logic, and buffered sends.
pub struct Publisher {
    tx: mpsc::Sender<ToolMutationEvent>,
}

impl Publisher {
    /// Spawn the publisher background task. Returns a handle for sending events.
    pub fn spawn(config: &Config) -> Self {
        let (tx, rx) = mpsc::channel(config.event_buffer_size);
        let amqp_url = config.amqp_url.clone();
        let exchange = config.exchange_name.clone();

        tokio::spawn(async move {
            publisher_loop(rx, &amqp_url, &exchange).await;
        });

        Self { tx }
    }

    /// Queue an event for publishing. Non-blocking; drops if buffer is full.
    pub async fn publish(&self, event: ToolMutationEvent) {
        let routing_key = event.event_type.clone();
        if let Err(e) = self.tx.try_send(event) {
            warn!(error = %e, "event buffer full, dropping event");
        } else {
            tracing::debug!(routing_key = %routing_key, "event queued for publish");
        }
    }
}

/// Main publisher loop: connect, declare exchange, consume from channel.
async fn publisher_loop(mut rx: mpsc::Receiver<ToolMutationEvent>, amqp_url: &str, exchange: &str) {
    loop {
        match connect_and_publish(&mut rx, amqp_url, exchange).await {
            Ok(()) => {
                info!("publisher channel closed, shutting down");
                return;
            }
            Err(e) => {
                error!(error = %e, "AMQP connection lost, reconnecting in 2s");
                sleep(Duration::from_secs(2)).await;
            }
        }
    }
}

/// Establish connection, declare exchange, and publish events until error or channel close.
async fn connect_and_publish(
    rx: &mut mpsc::Receiver<ToolMutationEvent>,
    amqp_url: &str,
    exchange: &str,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let conn = Connection::connect(amqp_url, ConnectionProperties::default()).await?;
    info!(url = %amqp_url, "AMQP connected");

    let channel = conn.create_channel().await?;
    declare_exchange(&channel, exchange).await?;
    info!(exchange = %exchange, "exchange declared");

    while let Some(event) = rx.recv().await {
        let routing_key = event.event_type.clone();
        let body = serde_json::to_vec(&event)?;

        channel
            .basic_publish(
                exchange,
                &routing_key,
                BasicPublishOptions::default(),
                &body,
                BasicProperties::default()
                    .with_content_type("application/json".into())
                    .with_delivery_mode(2), // persistent
            )
            .await?
            .await?;

        tracing::debug!(
            routing_key = %routing_key,
            file_path = ?event.file_path,
            "event published"
        );
    }

    Ok(())
}

/// Declare the topic exchange (idempotent).
async fn declare_exchange(channel: &Channel, exchange: &str) -> Result<(), lapin::Error> {
    channel
        .exchange_declare(
            exchange,
            ExchangeKind::Topic,
            ExchangeDeclareOptions {
                durable: true,
                ..Default::default()
            },
            FieldTable::default(),
        )
        .await
}
