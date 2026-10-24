"""Process-local ingest counters.

Thread-safe (ThreadingHTTPServer serves each request on its own thread). These
back the WARN-on-drop signal today and the /metrics endpoint later (CANDYS-29).
Counts reset on restart — they are a liveness/rate signal, not durable state
(the dead_letter table is the durable record).
"""

from __future__ import annotations

import threading
from collections import Counter

_lock = threading.Lock()
_counters: Counter[str] = Counter()


def incr(name: str, n: int = 1) -> None:
    with _lock:
        _counters[name] += n


def snapshot() -> dict[str, int]:
    with _lock:
        return dict(_counters)
