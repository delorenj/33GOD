"""Sink relay: deliver synthesized audio to a *listening client*, not the caller's speakers.

Problem this solves: a process running on the stack host (an ssh session, a
zellij pane, a Hermes systemd unit, a cron job) has no speakers the human is
sitting in front of. ``paplay`` there plays into an empty room. Audio egress
should follow the *person*, not the process.

Model: a **sink** is a named destination the human owns (``delo-macbook``).
The machine in front of them holds an SSE connection to
``GET /sink/{key}/events``; anything that wants to reach their ears POSTs an
``audio_url`` to ``POST /sink/{key}/play``, and the listener fetches that URL
from the public audio cache and plays it. Only a tiny JSON envelope crosses
this relay -- the audio itself takes the same public ``/audio/<id>.ogg`` path
Telegram already uses.

Why a server relay and not an ssh reverse tunnel: the tunnel dies with the ssh
connection, but a zellij session outlives it, so ``PULSE_SERVER``/port-based
env in that pane goes stale the moment you reconnect. A sink key is a *stable
identity* -- set ``VOX_SINK=delo-macbook`` once in ``~/.zshenv`` and it is
correct forever, from any host, with no tunnel to re-establish.

State is deliberately in-memory and unreplicated. A sink is a live attention
channel: if nobody is listening the message is *worthless*, not pending. That
is also why publish reports a delivery count instead of queueing -- the caller
uses it to decide whether to fall back to local playback.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

logger = logging.getLogger("vox.sink")

# Keys are dict keys, never filesystem paths, so traversal is not the concern.
# The bound exists so an unauthenticated-key-guessing client (or a typo in a
# loop) cannot grow the registry without limit.
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

MAX_KEYS = 256
MAX_LISTENERS_PER_KEY = 8

# Per-listener backlog. A listener that stops draining (laptop asleep, player
# wedged) must not grow memory without bound, and stale speech is worse than no
# speech -- so the queue drops its *oldest* entry rather than blocking the
# publisher or dropping the newest.
QUEUE_MAXSIZE = 32

# Cloudflare reaps idle connections around 100s. Comment frames keep the stream
# warm without the client having to interpret anything.
HEARTBEAT_SECONDS = 20.0


class SinkKeyError(ValueError):
    """Raised when a sink key is not of the accepted shape."""


class SinkCapacityError(RuntimeError):
    """Raised when the registry or a single key is at its listener cap."""


def validate_key(key: str) -> str:
    """Return `key` if it is an acceptable sink name, else raise SinkKeyError."""
    if not KEY_RE.match(key or ""):
        raise SinkKeyError(
            "sink key must be 1-64 chars of [A-Za-z0-9._-] and start alphanumeric"
        )
    return key


class SinkRegistry:
    """Fan-out registry mapping a sink key to the queues of its live listeners.

    Multiple listeners on one key all receive every message (your laptop and
    your desktop both speak). This is fan-out rather than last-writer-wins
    because "which of my machines is the real one" is a question only the human
    can answer, and answering it wrong silently loses the message.
    """

    def __init__(self) -> None:
        self._listeners: dict[str, set[asyncio.Queue]] = {}

    def listener_count(self, key: str) -> int:
        return len(self._listeners.get(key, ()))

    def keys(self) -> list[str]:
        return sorted(self._listeners)

    @asynccontextmanager
    async def subscribe(self, key: str) -> AsyncIterator[asyncio.Queue]:
        """Register a listener queue for `key` for the duration of the block."""
        validate_key(key)
        queues = self._listeners.get(key)
        if queues is None:
            if len(self._listeners) >= MAX_KEYS:
                raise SinkCapacityError(f"too many active sinks (max {MAX_KEYS})")
            queues = set()
            self._listeners[key] = queues
        if len(queues) >= MAX_LISTENERS_PER_KEY:
            raise SinkCapacityError(
                f"sink '{key}' already has {MAX_LISTENERS_PER_KEY} listeners"
            )

        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        queues.add(queue)
        logger.info("sink '%s': listener attached (now %d)", key, len(queues))
        try:
            yield queue
        finally:
            queues.discard(queue)
            if not queues:
                # Drop the empty set so `keys()` reflects live sinks only and an
                # abandoned key does not hold a slot against MAX_KEYS forever.
                self._listeners.pop(key, None)
            logger.info(
                "sink '%s': listener detached (now %d)", key, self.listener_count(key)
            )

    def publish(self, key: str, payload: dict[str, Any]) -> int:
        """Deliver `payload` to every listener on `key`; return how many got it.

        A return of 0 means nobody is listening. Callers treat that as "play it
        yourself instead", which is why this never raises on an unknown key.
        """
        queues = self._listeners.get(key)
        if not queues:
            return 0

        delivered = 0
        for queue in queues:
            if queue.full():
                try:
                    queue.get_nowait()  # evict oldest; stale speech has no value
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(payload)
                delivered += 1
            except asyncio.QueueFull:  # pragma: no cover - evicted above
                logger.warning("sink '%s': listener queue full, dropped", key)
        return delivered


def sse_frame(event: str, data: dict[str, Any]) -> bytes:
    """Encode one Server-Sent Events frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8")


def sse_comment(text: str = "ping") -> bytes:
    """Encode an SSE comment frame (ignored by clients, keeps the stream alive)."""
    return f": {text}\n\n".encode("utf-8")


async def event_stream(
    registry: SinkRegistry, key: str, queue: asyncio.Queue
) -> AsyncIterator[bytes]:
    """Yield SSE frames for one subscribed listener until it disconnects."""
    yield sse_frame("ready", {"key": key, "listeners": registry.listener_count(key)})
    while True:
        try:
            payload = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
        except asyncio.TimeoutError:
            yield sse_comment()
            continue
        yield sse_frame("audio", payload)


# SSE through Traefik + a Cloudflare Tunnel needs these or the stream is
# buffered into uselessness: no-cache defeats intermediary caching, and
# X-Accel-Buffering is the de-facto opt-out honored by proxies in the path.
SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
