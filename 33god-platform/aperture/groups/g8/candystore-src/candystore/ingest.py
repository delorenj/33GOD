from __future__ import annotations

import json
import logging
import os
from typing import Any

from candystore import stats
from candystore.db import insert_event, record_dead_letter, sanitize_envelope

logger = logging.getLogger("candystore.ingest")

SUBSCRIBE_PUBSUB = os.environ.get("SUBSCRIBE_PUBSUB", "bloodbank-pubsub")
# ONE wildcard covering every subject the BLOODBANK_EVENTS stream binds
# (bloodbank/compose/nats/streams.json), whatever the grammar happens to be:
# `bloodbank.evt.>` matches the legacy `bloodbank.evt.v1.*`/`v2.*` subjects and
# the current version-free `bloodbank.evt.<domain>.<entity>.<action>` alike.
#
# It must be one subject, not a list. A Dapr pubsub.jetstream component creates
# a single consumer, and a JetStream consumer is tied to one filter subject, so
# declaring two topics makes the second fail at startup with
#   nats: subject does not match consumer
# leaving it silently unsubscribed. `bloodbank.evt.v1.>` alone had exactly that
# effect on the v2 subject: pr-crusher's action-phase failure -- its
# highest-severity event -- reached the stream and was never projected here.
#
# The lesson generalizes past that incident: any subscription that enumerates
# subjects is a second copy of the stream config, and it goes stale silently --
# the events simply stop arriving, with no error anywhere. Do not reintroduce a
# per-subject topic list here. The wildcard adds no risk: a consumer only ever
# receives what the stream already holds, and this projection is meant to be the
# store's complete durable history.
SUBSCRIBE_TOPIC = os.environ.get("SUBSCRIBE_TOPIC", "bloodbank.evt.>")
SUBSCRIBE_ROUTE = os.environ.get("SUBSCRIBE_ROUTE", "/events/all")


def subscribe_response() -> list[dict[str, str]]:
    """Return Dapr programmatic subscription declarations."""
    return [
        {
            "pubsubname": SUBSCRIBE_PUBSUB,
            "topic": SUBSCRIBE_TOPIC,
            "route": SUBSCRIBE_ROUTE,
        }
    ]


def known_event_routes() -> set[str]:
    return {SUBSCRIBE_ROUTE}


def handle_event(body: bytes, topic: str | None = None) -> dict[str, Any]:
    envelope = json.loads(body.decode("utf-8"))
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a JSON object")

    clean, sanitized = sanitize_envelope(envelope)
    inserted = insert_event(clean, sanitized=sanitized)
    if sanitized:
        # Persisted with NUL stripped rather than poison-looping forever. Not
        # silent, and not lossy: mark the row (events.sanitized), count it, log,
        # and preserve the EXACT original bytes in dead_letter so the producer's
        # true input stays recoverable (jsonb cannot hold the NUL itself).
        stats.incr("sanitized")
        logger.warning(
            "stripped NUL before insert: event %s topic=%s", clean.get("id"), topic
        )
        record_dead_letter(body, reason="nul-sanitized", topic=topic, event_id=clean.get("id"))
    stats.incr("inserted" if inserted else "duplicate")
    return {"status": "SUCCESS", "inserted": inserted}
