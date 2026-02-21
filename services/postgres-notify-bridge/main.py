#!/usr/bin/env python3
"""
Postgres NOTIFY → Bloodbank Bridge
Listens to `bloodbank_events` channel from 33god-postgres
and publishes events to Bloodbank API.
"""
import asyncio
import json
import logging
import os
import sys
from typing import Any

import asyncpg
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://delorenj@33god-postgres:5432/33god",
)
BLOODBANK_API_URL = os.getenv(
    "BLOODBANK_API_URL",
    "http://bloodbank:8682",
)
NOTIFY_CHANNEL = os.getenv("NOTIFY_CHANNEL", "bloodbank_events")


async def publish_to_bloodbank(event_payload: dict[str, Any]) -> None:
    """Publish event to Bloodbank API."""
    event_type = event_payload.get("event_type", "unknown")
    payload = event_payload.get("payload", {})

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{BLOODBANK_API_URL}/publish",
                json={
                    "event_type": event_type,
                    "payload": payload,
                },
            )
            response.raise_for_status()
            logger.info(
                f"✓ Published {event_type} to Bloodbank (status={response.status_code})"
            )
        except httpx.HTTPError as exc:
            logger.error(f"✗ Failed to publish {event_type}: {exc}")


async def listen_loop(conn: asyncpg.Connection) -> None:
    """Listen for NOTIFY messages and forward to Bloodbank."""
    logger.info(f"Listening on channel: {NOTIFY_CHANNEL}")

    async def notification_handler(
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload_str: str,
    ) -> None:
        logger.info(f"Received NOTIFY (pid={pid}, channel={channel})")
        try:
            payload = json.loads(payload_str)
            await publish_to_bloodbank(payload)
        except json.JSONDecodeError as exc:
            logger.error(f"Invalid JSON in NOTIFY payload: {exc}")
        except Exception as exc:
            logger.error(f"Error handling notification: {exc}")

    await conn.add_listener(NOTIFY_CHANNEL, notification_handler)

    # Keep the connection alive
    while True:
        await asyncio.sleep(1)


async def main() -> None:
    logger.info(f"Starting Postgres NOTIFY → Bloodbank bridge")
    logger.info(f"Postgres DSN: {POSTGRES_DSN}")
    logger.info(f"Bloodbank API: {BLOODBANK_API_URL}")

    while True:
        try:
            conn = await asyncpg.connect(POSTGRES_DSN)
            logger.info("✓ Connected to Postgres")

            try:
                await listen_loop(conn)
            finally:
                await conn.close()

        except asyncpg.PostgresError as exc:
            logger.error(f"Postgres error: {exc}")
            logger.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as exc:
            logger.error(f"Unexpected error: {exc}")
            logger.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
