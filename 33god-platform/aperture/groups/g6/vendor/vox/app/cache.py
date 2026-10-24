"""Filesystem audio cache with TTL sweeping.

The flow: synth engine produces bytes, we transcode to OGG/Opus, drop the
result under ``VOX_AUDIO_CACHE_DIR`` as ``<uuid>.ogg``, and return a URL that
third parties (Telegram, Hermes, browsers) can fetch. Entries are short-lived
by design; a background task sweeps anything older than VOX_AUDIO_TTL_SECONDS.

This is intentionally not Redis. The cache is write-once, fetch-once, and
durability is not a goal. If the pod dies before Telegram fetches, the caller
re-requests. Keeping it on the container's bind-mounted disk also means
debug tools (file, mpv, etc.) work against the cached files directly.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

AUDIO_CACHE_DIR = Path(os.environ.get("VOX_AUDIO_CACHE_DIR", "/data/audio-cache"))
AUDIO_TTL_SECONDS = int(os.environ.get("VOX_AUDIO_TTL_SECONDS", "3600"))
SWEEP_INTERVAL_SECONDS = int(os.environ.get("VOX_AUDIO_SWEEP_INTERVAL", "300"))


def ensure_dir() -> None:
    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def put(ogg_bytes: bytes) -> str:
    """Write bytes to the cache, return the opaque id (filename without .ogg)."""
    ensure_dir()
    cache_id = uuid.uuid4().hex
    path = AUDIO_CACHE_DIR / f"{cache_id}.ogg"
    # Atomic-ish: write to .tmp then rename so partial reads never hit a half
    # file. Telegram fetches are observable from the outside, so we care.
    tmp = path.with_suffix(".ogg.tmp")
    tmp.write_bytes(ogg_bytes)
    tmp.rename(path)
    return cache_id


def path_for(cache_id: str) -> Path | None:
    """Return the absolute path for a cache id if it exists, else None."""
    # Reject anything that looks like a path traversal attempt. Cache ids are
    # hex uuids so a strict isalnum check is sufficient.
    if not cache_id or not cache_id.isalnum():
        return None
    path = AUDIO_CACHE_DIR / f"{cache_id}.ogg"
    return path if path.exists() else None


def _sweep_once() -> int:
    ensure_dir()
    now = time.time()
    removed = 0
    for entry in AUDIO_CACHE_DIR.glob("*.ogg*"):
        try:
            if now - entry.stat().st_mtime > AUDIO_TTL_SECONDS:
                entry.unlink(missing_ok=True)
                removed += 1
        except OSError:
            continue
    return removed


async def sweep_loop() -> None:
    """Background task: expire stale cache entries on an interval."""
    while True:
        try:
            n = _sweep_once()
            if n:
                logger.info("audio cache sweep removed %d stale entries", n)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("audio cache sweep error: %s", exc)
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
