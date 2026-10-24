"""G4 alert-bridge — stdlib Alertmanager webhook -> ntfy forwarder.

Cribbed from the Aperture G3 outbox/ntfy-gate stdlib pattern (http.server +
urllib, no pip deps, python:3.12-alpine, non-root). Receives Alertmanager
webhook POSTs (webhook_configs), formats one human line per alert:

    <emoji> <alertname> [<status>] <summary> (<instance>)

and POSTs each line to the ntfy endpoint GOD_NTFY_URL with topic
GOD_NTFY_TOPIC. If GOD_NTFY_URL is empty or the ntfy endpoint is unreachable,
the failure is logged VISIBLY and the bridge keeps serving 200 to
Alertmanager — it is never a single point of failure. Standalone (default)
G4 runs with GOD_NTFY_URL empty; the attach overlay points it at G3's ntfy.

Endpoints:
  GET  /healthz   -> 200 {"ok": true} (always; no upstream dependency)
  POST /webhook   -> parse Alertmanager JSON, format + log + forward each alert

This bridge emits NO bus events (G4 v1 is self-contained observability).
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = logging.getLogger("alert-bridge")

NTFY_URL = os.environ.get("GOD_NTFY_URL", "").rstrip("/")
NTFY_TOPIC = os.environ.get("GOD_NTFY_TOPIC", "aperture-g4-alerts")
HEALTHZ_PORT = int(os.environ.get("GOD_HEALTHZ_PORT", "8789"))
MAX_BODY = 1 << 20  # 1 MiB — Alertmanager webhook batches can be sizable

# Alertmanager sends one of two statuses per batch; individual alerts carry
# their own status too. We key the emoji off the per-alert status.
EMOJI = {"firing": "\U0001f525", "resolved": "\u2705"}


def _fmt_line(alert: dict) -> str:
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    status = alert.get("status", "unknown")
    name = labels.get("alertname", "unknown")
    summary = annotations.get("summary") or annotations.get("description") or ""
    instance = labels.get("instance", "")
    parts = [f"{EMOJI.get(status, '\u26a0\ufe0f')} {name} [{status}]"]
    if summary:
        parts.append(summary)
    if instance:
        parts.append(f"({instance})")
    return " ".join(parts)


def _post_ntfy(line: str, title: str) -> bool:
    if not NTFY_URL:
        LOG.warning("no ntfy URL configured (GOD_NTFY_URL empty); not delivering: %s", line)
        return False
    body = json.dumps({"topic": NTFY_TOPIC, "title": title, "message": line}).encode()
    req = urllib.request.Request(
        NTFY_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        LOG.error("ntfy delivery failed (%s): %s", NTFY_URL, exc)
        return False


def _handle_webhook(payload: bytes) -> dict:
    data = json.loads(payload.decode())
    alerts = data.get("alerts", [])
    delivered = 0
    for alert in alerts:
        line = _fmt_line(alert)
        # Always log the formatted line: it is the smoke's delivery evidence
        # even when GOD_NTFY_URL is unset (honest default).
        LOG.info("alert %s", line)
        if _post_ntfy(line, alert.get("labels", {}).get("alertname", "alert")):
            delivered += 1
    return {"received": len(alerts), "delivered": delivered}


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path != "/healthz":
            return self.respond(404, {"error": "not found"})
        return self.respond(200, {"ok": True, "service": "alert-bridge",
                                  "ntfy_url_configured": bool(NTFY_URL)})

    def do_POST(self):
        if self.path != "/webhook":
            return self.respond(404, {"error": "not found"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY:
                return self.respond(413, {"error": "body must be 1..1048576 bytes"})
            payload = self.rfile.read(size)
            # Parse once so a malformed body is a 400, not a 500 crash loop.
            json.loads(payload.decode())
        except (ValueError, TypeError, AttributeError) as exc:
            return self.respond(400, {"error": f"malformed webhook JSON: {exc}"})
        try:
            return self.respond(200, _handle_webhook(payload))
        except Exception as exc:  # noqa: BLE001 — bridge must keep serving
            LOG.exception("webhook handling failed")
            return self.respond(500, {"error": str(exc)})

    def log_message(self, format, *args):
        pass  # requests are already logged at the alert level; no access-log noise


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    LOG.info("alert-bridge up: ntfy_url=%r topic=%r", NTFY_URL or "", NTFY_TOPIC)
    ThreadingHTTPServer(("0.0.0.0", HEALTHZ_PORT), Handler).serve_forever()
