#!/usr/bin/env python3
"""G3 lifecycle-controller — synthetic task envelope transition proof.

The state machine (models.py + reconciler.py) is a verbatim crib of
krebs/src/krebs/project_health/{models,reconciler}.py — pure stdlib, no DB,
no I/O. What the canonical service adds on top (asyncpg/Postgres persistence,
structlog, the krebs-execution worker/sweeper loop, and an outbox publisher
whose default is a literal "not configured" stub) is intentionally NOT
shipped here; see the group README + hook-hub/DEFERRED.md for the extraction
contract. This runner drives the verbatim reconciler over ONE synthetic task
envelope and publishes the resulting lifecycle CloudEvent to the G3 bus with
a JetStream persistence acknowledgment.

Env:
  GOD_G3_LIFECYCLE_ID          synthetic lifecycle id (default: fixed demo UUID)
  GOD_G3_RECONCILE_INTERVAL    re-reconcile interval seconds (default: 15)
  GOD_HEALTHZ_PORT             healthz listen port (default: 8788)
"""
from __future__ import annotations

import json
import logging
import os
import signal
import sys
import threading
import time
import uuid
from datetime import datetime, timezone

from . import nats_publish
from .models import LifecycleHealth, LifecycleStatus, Observation
from .reconciler import reconcile

LOG = logging.getLogger("lifecycle-controller")

DEMO_LIFECYCLE_ID = "a0e5e0d0-0000-4000-8000-000000000003"
CE_TYPE = "bloodbank.lifecycle.status.updated"
SUBJECT = "bloodbank.evt.lifecycle.status.updated"

_running = True
_state: dict = {"last_sequence": None, "previous": None, "current": None}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _synthetic_observation(lifecycle_id: str) -> Observation:
    """One synthetic sentinel snapshot: two runnable work items, no blockers."""
    return Observation(
        lifecycle_id=lifecycle_id,
        source="plane-sentinel",
        kind="work_items_snapshot",
        observed_at=datetime.now(timezone.utc),
        payload={"open_count": 3, "runnable_count": 2},
    )


def _cloud_event(event_type: str, lifecycle_id: str, payload: dict) -> dict:
    event_id = str(uuid.uuid4())
    return {
        "specversion": "1.0",
        "id": event_id,
        "source": "urn:33god:service:lifecycle-controller",
        "type": event_type,
        "subject": SUBJECT,
        "time": _now_iso(),
        "datacontenttype": "application/json",
        "dataschema": f"apicurio://holyfields/{event_type}/versions/1",
        "correlationid": lifecycle_id,
        "causationid": lifecycle_id,
        "producer": "lifecycle-controller",
        "service": "lifecycle-controller",
        "domain": "lifecycle",
        "schemaref": f"{event_type}.v1",
        "kind": "event",
        "actor": {
            "type": "service",
            "agent_id": "service:lifecycle-controller",
            "cli": None,
            "provider": None,
            "model": None,
        },
        "ordering_key": f"lifecycle:{lifecycle_id}",
        "data": payload,
    }


def _run_reconcile(lifecycle_id: str, previous):
    """Run the verbatim reconciler over the synthetic envelope.

    Returns (result, published_seq_or_None). A real status/health change
    publishes a lifecycle CloudEvent; an unchanged re-reconcile publishes
    nothing (the reconciler correctly reports no delta).
    """
    obs = _synthetic_observation(lifecycle_id)
    result = reconcile(
        lifecycle_id=lifecycle_id,
        previous_state=previous,
        observations=[obs],
        active_blockers=[],
        active_gates=[],
        checkpoints=[],
        sentinel_health={},
    )
    seq = None
    if result.state_changed:
        for outbox in result.outbox_events:
            if outbox.event_type == CE_TYPE:
                event = _cloud_event(outbox.event_type, lifecycle_id, outbox.payload)
                ack = nats_publish.publish_event(SUBJECT, event, msg_id=event["id"])
                seq = ack["seq"]
                LOG.info(
                    "transition %s -> %s (reason=%s) published seq=%s id=%s",
                    (result.previous_state.status.value if result.previous_state else "none"),
                    result.current_state.status.value,
                    result.current_state.status_reason,
                    seq,
                    event["id"],
                )
    return result, seq


def _handle_signal(signum, _frame):
    global _running
    LOG.info("received signal %d; draining and exiting", signum)
    _running = False


def _make_health_handler():
    from http.server import BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/healthz":
                self.send_response(404)
                self.end_headers()
                return
            body = json.dumps({
                "ok": True,
                "service": "lifecycle-controller",
                "last_sequence": _state["last_sequence"],
                "transition": {
                    "previous": _state["previous"],
                    "current": _state["current"],
                },
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    return Handler


def main() -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    lifecycle_id = os.environ.get("GOD_G3_LIFECYCLE_ID", DEMO_LIFECYCLE_ID)
    interval_s = float(os.environ.get("GOD_G3_RECONCILE_INTERVAL", "15"))
    healthz_port = int(os.environ.get("GOD_HEALTHZ_PORT", "8788"))

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # Wait for the G3 NATS broker + stream.
    deadline = time.monotonic() + 60.0
    while _running and time.monotonic() < deadline:
        try:
            nats_publish.ensure_stream()
            break
        except (OSError, TimeoutError, RuntimeError) as exc:
            LOG.debug("nats not yet ready: %s", exc)
        time.sleep(2)
    else:
        if not _running:
            return 0
        LOG.error("nats never became healthy")
        return 1

    # First reconcile: PLANNED -> ACTIVE (the synthetic task envelope transition).
    previous = None
    result, seq = _run_reconcile(lifecycle_id, previous)
    _state["last_sequence"] = seq
    _state["previous"] = result.previous_state.status.value if result.previous_state else None
    _state["current"] = result.current_state.status.value
    previous = result.current_state

    from http.server import ThreadingHTTPServer
    server = ThreadingHTTPServer(("0.0.0.0", healthz_port), _make_health_handler())
    threading.Thread(target=server.serve_forever, daemon=True).start()

    # Re-reconcile on the interval: with the same synthetic observation and no
    # new blockers the verdict is unchanged, so the reconciler emits no event.
    # This proves idempotency, not repeated fake transitions.
    while _running:
        slept = 0.0
        while _running and slept < interval_s:
            chunk = min(0.5, interval_s - slept)
            time.sleep(chunk)
            slept += chunk
        if not _running:
            break
        result, seq = _run_reconcile(lifecycle_id, previous)
        if result.state_changed:
            _state["last_sequence"] = seq
            _state["previous"] = result.previous_state.status.value if result.previous_state else None
            _state["current"] = result.current_state.status.value
        previous = result.current_state
        LOG.debug("reconciled; state_changed=%s status=%s", result.state_changed, result.current_state.status.value)

    LOG.info("lifecycle-controller exiting; final status=%s", previous.status.value)
    return 0


if __name__ == "__main__":
    sys.exit(main())
