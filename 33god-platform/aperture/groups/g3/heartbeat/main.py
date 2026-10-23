#!/usr/bin/env python3
"""Heartbeat tick producer for Aperture G3 (Agent Fleet Runtime).

Cribbed verbatim from bloodbank/services/heartbeat-tick/main.py
(build_envelope, CloudEvent envelope, tick loop, SIGTERM drain). One
transport adaptation: the source emits through Dapr pub/sub
(`POST {dapr}/v1.0/publish/{pubsub}/{topic}`); G3 has no Dapr placement and
no G1 bus, so publish() uses the shared stdlib NATS JetStream publisher
(nats_publish.publish_event) with a persistence acknowledgment instead.

A small stdlib /healthz endpoint is a G3 addition (the source service reports
health through Dapr/systemd, neither of which exists here).

Env:
  GOD_NATS_HOST / GOD_NATS_URL  broker hostname (default: nats)
  HEARTBEAT_INTERVAL            tick interval seconds (default: 5)
  PRODUCER_ID                   stable instance id (default: heartbeat-tick:<rand>)
  GOD_HEALTHZ_PORT              healthz listen port (default: 8786)
  LOG_LEVEL                     INFO / DEBUG (default: INFO)
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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import nats_publish

LOG = logging.getLogger("heartbeat-tick")


def _now_iso() -> str:
    """RFC3339 UTC timestamp matching the heartbeat schema's `time` field."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


CE_TYPE = "bloodbank.system.heartbeat.received"
SUBJECT = "bloodbank.evt.system.heartbeat.received"


def build_envelope(*, tick_seq: int, producer_id: str, started_at: str, interval_ms: int) -> dict:
    """Construct a Bloodbank CloudEvents envelope per docs/event-naming.md."""
    event_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    return {
        "specversion": "1.0",
        "id": event_id,
        "source": "urn:33god:service:heartbeat-tick",
        "type": CE_TYPE,
        "subject": SUBJECT,
        "time": _now_iso(),
        "datacontenttype": "application/json",
        "dataschema": f"apicurio://holyfields/{CE_TYPE}/versions/1",
        "correlationid": correlation_id,
        "causationid": correlation_id,
        "producer": "heartbeat-tick",
        "service": "heartbeat-tick",
        "domain": "system",
        "schemaref": f"{CE_TYPE}.v1",
        "traceparent": "00-00000000000000000000000000000000-0000000000000000-00",
        "kind": "event",
        "actor": {
            "type": "service",
            "agent_id": f"service:heartbeat-tick:{producer_id}",
            "cli": None,
            "provider": None,
            "model": None,
        },
        "ordering_key": f"system:{producer_id}",
        "data": {
            "source_id": producer_id,
            "sequence": tick_seq,
            "tick_seq": tick_seq,
            "interval_ms": interval_ms,
            "producer_id": producer_id,
            "started_at": started_at,
        },
    }


_running = True
_last_seq: dict = {"seq": None}


def _handle_signal(signum: int, _frame: object) -> None:
    global _running
    LOG.info("received signal %d; draining and exiting", signum)
    _running = False


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/healthz":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"ok": True, "service": "heartbeat-tick", "last_sequence": _last_seq["seq"]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def _serve_healthz(port: int) -> None:
    ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler).serve_forever()


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    topic = os.environ.get("HEARTBEAT_TOPIC", SUBJECT)
    interval_s = float(os.environ.get("HEARTBEAT_INTERVAL", "5"))
    interval_ms = int(interval_s * 1000)
    healthz_port = int(os.environ.get("GOD_HEALTHZ_PORT", "8786"))

    producer_id = os.environ.get("PRODUCER_ID", f"heartbeat-tick:{uuid.uuid4().hex[:8]}")
    started_at = _now_iso()

    LOG.info("starting heartbeat-tick: topic=%s interval=%.2fs producer_id=%s", topic, interval_s, producer_id)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # Wait for the G3 NATS broker and create the stream before first publish.
    # Boot races are real; tolerate up to 60s before giving up.
    deadline = time.monotonic() + 60.0
    while _running and time.monotonic() < deadline:
        try:
            nats_publish.ensure_stream()
            LOG.info("G3 stream ready")
            break
        except (OSError, TimeoutError, RuntimeError) as exc:
            LOG.debug("nats not yet ready: %s", exc)
        time.sleep(2)
    else:
        if not _running:
            return 0
        LOG.error("nats never became healthy")
        return 1

    threading.Thread(target=_serve_healthz, args=(healthz_port,), daemon=True).start()

    tick_seq = 0
    while _running:
        envelope = build_envelope(
            tick_seq=tick_seq,
            producer_id=producer_id,
            started_at=started_at,
            interval_ms=interval_ms,
        )
        try:
            ack = nats_publish.publish_event(topic, envelope, msg_id=envelope["id"])
            _last_seq["seq"] = ack["seq"]
            LOG.info("emitted tick_seq=%d id=%s seq=%s", tick_seq, envelope["id"], ack["seq"])
            tick_seq += 1
        except Exception as exc:
            LOG.warning("publish failed (tick_seq=%d): %s", tick_seq, exc)

        slept = 0.0
        while _running and slept < interval_s:
            chunk = min(0.5, interval_s - slept)
            time.sleep(chunk)
            slept += chunk

    LOG.info("heartbeat-tick exiting; final tick_seq=%d", tick_seq - 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
