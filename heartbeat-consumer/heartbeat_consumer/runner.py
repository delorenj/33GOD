#!/usr/bin/env python3
"""
Heartbeat Consumer Runner

Entry point for running the per-agent heartbeat consumer.
Usage:
    AGENT_NAME=cack HEARTBEAT_PATH=/home/delorenj/.openclaw/workspace/heartbeat.json python -m heartbeat_consumer.runner
    
Environment Variables:
    AGENT_NAME: Agent name (required)
    HEARTBEAT_PATH: Path to heartbeat.json (required)
    RABBIT_URL: RabbitMQ URL (default: amqp://delorenj:delorenj@localhost:5673/)
    EXCHANGE_NAME: Exchange name (default: bloodbank.events.v1)
    LOG_LEVEL: Logging level (default: INFO)
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from heartbeat_consumer import HeartbeatConsumer


def main():
    """Run the heartbeat consumer."""
    # Get configuration from environment
    agent_name = os.environ.get("AGENT_NAME")
    heartbeat_path = os.environ.get("HEARTBEAT_PATH")
    rabbit_url = os.environ.get("RABBIT_URL", "amqp://delorenj:delorenj@localhost:5673/")
    exchange_name = os.environ.get("EXCHANGE_NAME", "bloodbank.events.v1")
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    
    # Validate required config
    if not agent_name:
        print("ERROR: AGENT_NAME environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    if not heartbeat_path:
        print("ERROR: HEARTBEAT_PATH environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    
    # Create and run consumer
    consumer = HeartbeatConsumer(
        agent_name=agent_name,
        heartbeat_path=heartbeat_path,
        rabbit_url=rabbit_url,
        exchange_name=exchange_name,
    )
    
    try:
        consumer.run_sync()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
