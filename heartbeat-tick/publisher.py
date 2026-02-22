"""33GOD Master Heartbeat Tick Publisher for Bloodbank.

Publishes `system.heartbeat.tick` event to RabbitMQ every 60 seconds.
Uses FastStream for robust message publishing.

Event payload schema:
{
    "tick": 12345,                          // Monotonic counter
    "timestamp": "2026-02-22T21:37:00Z",    // ISO-8601 UTC
    "quarter": "Q4",                        // Q1-Q4 based on America/New_York hour
    "dayOfWeek": "sunday",                  // lowercase day name
    "epochMs": 1771802220000                // Unix epoch milliseconds
}

Quarter calculation (America/New_York):
    Q1: 00:00-06:00
    Q2: 06:00-12:00
    Q3: 12:00-18:00
    Q4: 18:00-00:00

Environment:
    RABBITMQ_URL        AMQP connection string (default: amqp://delorenj@localhost:5673/)
    RABBITMQ_PASS       RabbitMQ password (required if not in URL)
    BLOODBANK_EXCHANGE  Exchange name (default: bloodbank.events.v1)
    TICK_INTERVAL_S     Seconds between ticks (default: 60)
    LOG_LEVEL           Logging level (default: INFO)
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import socket
import sys
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, ExchangeType

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("heartbeat-tick")

# Configuration
RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://delorenj@localhost:5673/")
RABBITMQ_PASS = os.environ.get("RABBITMQ_PASS", "")
BLOODBANK_EXCHANGE = os.environ.get("BLOODBANK_EXCHANGE", "bloodbank.events.v1")
TICK_INTERVAL_S = int(os.environ.get("TICK_INTERVAL_S", "60"))
HOSTNAME = socket.gethostname()

# Event constants
EVENT_TYPE = "system.heartbeat.tick"
ROUTING_KEY = "system.heartbeat.tick"
TZ = ZoneInfo("America/New_York")


def get_rabbitmq_url() -> str:
    """Build RabbitMQ URL from components if password is separate."""
    if RABBITMQ_PASS and RABBITMQ_URL:
        # Insert password into URL if needed
        if "://" in RABBITMQ_URL:
            scheme, rest = RABBITMQ_URL.split("://", 1)
            if "@" not in rest or ":" not in rest.split("@")[0]:
                # No password in URL, insert it
                if "@" in rest:
                    user, host_part = rest.split("@", 1)
                    return f"{scheme}://{user}:{RABBITMQ_PASS}@{host_part}"
                else:
                    return f"{scheme}://delorenj:{RABBITMQ_PASS}@{rest}"
    return RABBITMQ_URL


def calculate_quarter(hour: int) -> str:
    """Calculate quarter based on America/New_York hour.
    
    Q1: 00:00-06:00 (hours 0-5)
    Q2: 06:00-12:00 (hours 6-11)
    Q3: 12:00-18:00 (hours 12-17)
    Q4: 18:00-00:00 (hours 18-23)
    """
    if 0 <= hour < 6:
        return "Q1"
    elif 6 <= hour < 12:
        return "Q2"
    elif 12 <= hour < 18:
        return "Q3"
    else:
        return "Q4"


def create_tick_payload(tick: int) -> dict:
    """Create the heartbeat tick payload.
    
    Args:
        tick: Monotonic counter (resets on restart)
        
    Returns:
        Dict matching the required payload schema
    """
    now_utc = datetime.now(timezone.utc)
    now_ny = now_utc.astimezone(TZ)
    
    return {
        "tick": tick,
        "timestamp": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quarter": calculate_quarter(now_ny.hour),
        "dayOfWeek": now_ny.strftime("%A").lower(),
        "epochMs": int(now_utc.timestamp() * 1000),
    }


def create_envelope(tick: int) -> dict:
    """Create a full Bloodbank event envelope.
    
    Args:
        tick: Monotonic counter
        
    Returns:
        Full event envelope with payload
    """
    from uuid import uuid4
    
    now_utc = datetime.now(timezone.utc)
    
    return {
        "event_id": str(uuid4()),
        "event_type": EVENT_TYPE,
        "timestamp": now_utc.isoformat(),
        "version": "1.0.0",
        "source": {
            "host": HOSTNAME,
            "type": "scheduled",
            "app": "heartbeat-tick-publisher",
        },
        "correlation_ids": [],
        "payload": create_tick_payload(tick),
    }


class HeartbeatTickPublisher:
    """FastStream-based heartbeat tick publisher."""
    
    def __init__(
        self,
        rabbitmq_url: Optional[str] = None,
        exchange_name: str = BLOODBANK_EXCHANGE,
        tick_interval: int = TICK_INTERVAL_S,
    ):
        self.rabbitmq_url = rabbitmq_url or get_rabbitmq_url()
        self.exchange_name = exchange_name
        self.tick_interval = tick_interval
        self.tick_count = 0
        self._shutdown_event = asyncio.Event()
        
        # Initialize FastStream broker
        self.broker = RabbitBroker(self.rabbitmq_url)
        self.exchange = RabbitExchange(
            name=self.exchange_name,
            type=ExchangeType.TOPIC,
            durable=True,
        )
        self.app = FastStream(self.broker)
    
    def _setup_signal_handlers(self) -> None:
        """Set up graceful shutdown handlers."""
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_handler)
    
    def _signal_handler(self) -> None:
        """Handle shutdown signals."""
        logger.info("Shutdown signal received, stopping publisher...")
        self._shutdown_event.set()
    
    async def publish_tick(self) -> None:
        """Publish a single heartbeat tick."""
        self.tick_count += 1
        envelope = create_envelope(self.tick_count)
        
        try:
            await self.broker.publish(
                message=envelope,
                exchange=self.exchange_name,
                routing_key=ROUTING_KEY,
            )
            logger.info(
                "Tick #%d published: quarter=%s, day=%s, epochMs=%d",
                self.tick_count,
                envelope["payload"]["quarter"],
                envelope["payload"]["dayOfWeek"],
                envelope["payload"]["epochMs"],
            )
        except Exception as e:
            logger.error("Failed to publish tick #%d: %s", self.tick_count, e)
            raise
    
    async def run(self) -> None:
        """Main publisher loop."""
        logger.info(
            "Starting heartbeat tick publisher: "
            "exchange=%s, interval=%ds, url=%s",
            self.exchange_name,
            self.tick_interval,
            self.rabbitmq_url.replace(RABBITMQ_PASS, "***") if RABBITMQ_PASS else self.rabbitmq_url,
        )
        
        # Set up signal handlers
        self._setup_signal_handlers()
        
        # Start the FastStream app (connects to RabbitMQ)
        await self.broker.start()
        logger.info("Connected to RabbitMQ")
        
        try:
            while not self._shutdown_event.is_set():
                # Publish tick
                await self.publish_tick()
                
                # Wait for interval or shutdown
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.tick_interval,
                    )
                except asyncio.TimeoutError:
                    # Normal interval elapsed, continue loop
                    pass
        finally:
            await self.broker.close()
            logger.info(
                "Publisher shut down after %d ticks",
                self.tick_count,
            )


async def main() -> None:
    """Entry point."""
    publisher = HeartbeatTickPublisher()
    await publisher.run()


if __name__ == "__main__":
    asyncio.run(main())
