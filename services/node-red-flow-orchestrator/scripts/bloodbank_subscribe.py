#!/usr/bin/env python3
"""Subscribe to Bloodbank (RabbitMQ) events and emit JSON lines on stdout.

Designed to be spawned by Node-RED exec nodes. Features:
  - Reads RABBIT_URL from environment (default: amqp://delorenj:...@localhost:5673/)
  - Retries connection with exponential backoff (forever)
  - Logs status to stderr so Node-RED sees it on the error output
  - Emits one JSON line per message on stdout for Node-RED to parse
"""
import argparse
import asyncio
import os
import signal
import sys
import time

import aio_pika

# Hardcoded fallback matching the PM2 ecosystem config
DEFAULT_RABBIT_URL = "amqp://delorenj:Ittr5eesol@localhost:5673/"

MAX_RETRY_DELAY = 30  # seconds
INITIAL_RETRY_DELAY = 2  # seconds


def log(msg: str) -> None:
    """Log to stderr with timestamp prefix."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[bloodbank_subscribe {ts}] {msg}", file=sys.stderr, flush=True)


def build_queue_name(routing_key: str, suffix: str | None) -> str:
    if suffix:
        return suffix
    safe = routing_key.replace("*", "star").replace("#", "all").replace(".", "-")
    return f"node-red.{safe}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Subscribe to Bloodbank events and emit JSON lines.")
    parser.add_argument("--routing-key", required=True, help="Routing key or pattern (e.g., fireflies.transcript.ready)")
    parser.add_argument("--queue", default=None, help="Queue name (default: node-red.<routing-key>)")
    parser.add_argument("--exchange", default=None, help="Exchange name (default: BLOODBANK_EXCHANGE env)")
    return parser.parse_args()


async def consume(args: argparse.Namespace, rabbit_url: str) -> None:
    """Connect, declare, bind, and consume forever. Raises on connection failure."""
    exchange_name = args.exchange or os.environ.get("BLOODBANK_EXCHANGE") or os.environ.get("EXCHANGE_NAME") or "bloodbank.events.v1"
    queue_name = build_queue_name(args.routing_key, args.queue)

    log(f"Connecting to {rabbit_url.split('@')[-1]} ...")
    connection = await aio_pika.connect_robust(
        rabbit_url,
        timeout=15,
        reconnect_interval=5,
    )
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(exchange_name, aio_pika.ExchangeType.TOPIC, durable=True)
    queue = await channel.declare_queue(queue_name, durable=True)
    await queue.bind(exchange, routing_key=args.routing_key)

    log(f"CONNECTED exchange={exchange_name} queue={queue_name} routing_key={args.routing_key}")

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                try:
                    body = message.body.decode()
                except Exception:
                    body = message.body.decode("utf-8", errors="replace")
                print(body, flush=True)


async def main() -> None:
    args = parse_args()
    rabbit_url = os.environ.get("RABBIT_URL") or os.environ.get("BLOODBANK_RABBIT_URL") or DEFAULT_RABBIT_URL

    log(f"Starting subscriber for routing_key={args.routing_key}")
    log(f"RABBIT_URL target: {rabbit_url.split('@')[-1]}")

    delay = INITIAL_RETRY_DELAY
    while True:
        try:
            await consume(args, rabbit_url)
        except KeyboardInterrupt:
            log("Interrupted, shutting down.")
            break
        except Exception as exc:
            log(f"Connection error: {exc}")
            log(f"Retrying in {delay}s ...")
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_RETRY_DELAY)
        else:
            # If consume returns cleanly (shouldn't normally), reset delay
            delay = INITIAL_RETRY_DELAY


if __name__ == "__main__":
    # Ignore SIGINT gracefully (Node-RED sends it on redeploy)
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
