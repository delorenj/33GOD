#!/usr/bin/env python3
"""G3 containerized Hermes agent — heartbeat -> task -> publish -> readback.

This is the D3 proof boundary, not an interactive agent. The container runs
the real ``hermes-agent`` package from PyPI plus the vendored Bloodbank
hermes-gateway plugin, and this entrypoint demonstrates the agent's
event-publication path:

1. Verify hermes-agent is installed and the vendored plugin imports against
   Hermes' own ``gateway`` / ``hermes_cli`` modules (a real integration check,
   not a name-only one).
2. On each heartbeat tick, build a synthetic ``bloodbank.agent.invocation.start``
   command envelope, validate it through the plugin's own ``decode_command``
   fail-closed boundary, and construct the real lifecycle events with the
   plugin's ``started_events`` (the SAME code a live gateway uses).
3. Publish ``bloodbank.agent.invocation.started`` to the G3 NATS bus with a
   JetStream persistence acknowledgment, then read the retained message back
   and verify id/subject/sequence correlation.

Telegram/webhook ingress is NOT claimed here: it needs the G4 edge and is
documented in the group README.

Env:
  GOD_NATS_HOST / GOD_NATS_URL   broker hostname (default: nats)
  GOD_G3_PROFILE                 synthetic Hermes profile name (default: g3-demo)
  GOD_G3_HEARTBEAT_INTERVAL      heartbeat interval seconds (default: 5)
  GOD_HEALTHZ_PORT               healthz listen port (default: 8787)
"""
from __future__ import annotations

import importlib.metadata
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

LOG = logging.getLogger("g3-hermes-agent")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


_running = True
_last: dict = {"sequence": None, "id": None, "subject": None}


def _handle_signal(signum, _frame):
    global _running
    LOG.info("received signal %d; draining and exiting", signum)
    _running = False


def _verify_stack():
    """Return a list of (label, evidence) proving hermes + plugin are present."""
    evidence = []
    try:
        evidence.append(("hermes-agent", importlib.metadata.version("hermes-agent")))
    except importlib.metadata.PackageNotFoundError:
        evidence.append(("hermes-agent", "MISSING"))
    try:
        import bloodbank_hermes_gateway  # noqa: F401  (full adapter + contract import)
        evidence.append(("bloodbank_hermes_gateway", "imports (adapter + contract)"))
    except Exception as exc:
        evidence.append(("bloodbank_hermes_gateway", f"IMPORT FAILED: {type(exc).__name__}: {exc}"))
    try:
        eps = importlib.metadata.entry_points()
        names = [ep.name for ep in eps.select(group="hermes_agent.plugins")]
        evidence.append(("hermes_agent.plugins entry points", names))
    except Exception as exc:
        evidence.append(("hermes_agent.plugins entry points", f"ERROR: {exc}"))
    return evidence


def build_command_envelope(profile: str) -> dict:
    """A fully-valid synthetic bloodbank command envelope (per decode_command)."""
    return {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": "urn:33god:service:g3-heartbeat-task",
        "type": "bloodbank.agent.invocation.start",
        "time": _now_iso(),
        "datacontenttype": "application/json",
        "correlationid": str(uuid.uuid4()),
        "producer": "g3-heartbeat-task",
        "service": "g3-heartbeat-task",
        "domain": "agent",
        "kind": "command",
        "command_id": str(uuid.uuid4()),
        "idempotency_key": str(uuid.uuid4()),
        "delivery": "single_consumer",
        "actor": {"type": "service", "agent_id": "service:g3-heartbeat-task"},
        "data": {
            "target_agent_id": "g3-demo-agent",
            "prompt": "G3 heartbeat synthetic task: report ready and publish invocation.started",
            "thread_id": None,
            "turn_id": None,
            "context": {"reason": "g3-smoke", "board_id": "g3", "ticket_id": "g3-synthetic"},
        },
    }


def heartbeat_once(profile: str):
    """One heartbeat -> task -> publish -> readback cycle. Returns the ack dict."""
    from bloodbank_hermes_gateway.contract import (
        BATCH,
        Invocation,
        decode_command,
        started_events,
    )

    envelope = build_command_envelope(profile)
    decoded = decode_command(json.dumps(envelope).encode(), lane=BATCH)
    invocation = Invocation.from_envelope(decoded, profile=profile, lane=BATCH.name)
    _turn, started = started_events(invocation)

    ack = nats_publish.publish_event(started["subject"], started, msg_id=started["id"])
    readback = nats_publish.read_last(started["subject"])

    assert readback["subject"] == started["subject"], readback
    assert readback["sequence"] == ack["seq"], (readback, ack)
    assert readback["event"]["id"] == started["id"], readback

    _last.update({"sequence": ack["seq"], "id": started["id"], "subject": started["subject"]})
    return ack, started


def main() -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    profile = os.environ.get("GOD_G3_PROFILE", "g3-demo")
    interval_s = float(os.environ.get("GOD_G3_HEARTBEAT_INTERVAL", "5"))
    healthz_port = int(os.environ.get("GOD_HEALTHZ_PORT", "8787"))

    for label, value in _verify_stack():
        LOG.info("stack: %s = %s", label, value)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

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

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/healthz":
                self.send_response(404)
                self.end_headers()
                return
            body = json.dumps({"ok": True, "service": "g3-hermes-agent", "last": _last}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    threading.Thread(
        target=ThreadingHTTPServer(("0.0.0.0", healthz_port), HealthHandler).serve_forever,
        daemon=True,
    ).start()

    tick = 0
    while _running:
        try:
            ack, started = heartbeat_once(profile)
            LOG.info(
                "heartbeat task published: type=%s subject=%s seq=%s id=%s tick=%d",
                started["type"], started["subject"], ack["seq"], started["id"], tick,
            )
            tick += 1
        except Exception as exc:
            LOG.error("heartbeat task failed (tick=%d): %s", tick, exc)

        slept = 0.0
        while _running and slept < interval_s:
            chunk = min(0.5, interval_s - slept)
            time.sleep(chunk)
            slept += chunk

    LOG.info("g3-hermes-agent exiting; final tick=%d", tick - 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
