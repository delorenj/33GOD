#!/usr/bin/env python3
import argparse
import asyncio
import os
import sys

import aio_pika


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


async def main() -> None:
    args = parse_args()
    rabbit_url = os.environ.get("RABBIT_URL") or os.environ.get("BLOODBANK_RABBIT_URL")
    if not rabbit_url:
        print("Missing RABBIT_URL (or BLOODBANK_RABBIT_URL)", file=sys.stderr)
        raise SystemExit(2)

    exchange_name = args.exchange or os.environ.get("BLOODBANK_EXCHANGE") or os.environ.get("EXCHANGE_NAME") or "bloodbank.events.v1"
    queue_name = build_queue_name(args.routing_key, args.queue)

    connection = await aio_pika.connect_robust(rabbit_url)
    channel = await connection.channel()
    exchange = await channel.declare_exchange(exchange_name, aio_pika.ExchangeType.TOPIC, durable=True)
    queue = await channel.declare_queue(queue_name, durable=True)
    await queue.bind(exchange, routing_key=args.routing_key)

    print(
        f"[bloodbank_subscribe] exchange={exchange_name} queue={queue_name} routing_key={args.routing_key}",
        file=sys.stderr,
        flush=True,
    )

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                try:
                    body = message.body.decode()
                except Exception:
                    body = message.body.decode("utf-8", errors="replace")
                print(body, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
