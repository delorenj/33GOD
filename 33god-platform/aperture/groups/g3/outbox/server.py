"""G3 demo-only HTTP -> JetStream adapter. Stdlib, no custom deps.

Cribbed from Aperture G2 outbox/server.py, generalized for the G3 fleet bus:

- Fixed synthetic publish subject (bloodbank.evt.aperture.smoke.g3) so the
  adapter is NOT a general Bloodbank ingress.
- GET /latest?subject=<s> reads back ANY retained event in the G3_EVENTS
  stream (heartbeat, lifecycle, agent invocation, smoke) — so one smoke
  client can verify every G3 event path from the stream, not an HTTP cache.
- The direct publish path waits for a JetStream persistence acknowledgment
  (shared nats_publish.publish_event, cribbed from bloodbank hook-hub).
"""
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
import uuid

import nats_publish

SUBJECT = "bloodbank.evt.aperture.smoke.g3"          # NATS subject (5 tokens)
SUBJECT_TYPE = "bloodbank.aperture.smoke.g3"          # CloudEvents type (4 tokens)
STREAM = nats_publish.G3_STREAM
TOKEN = os.environ.get("GOD_DEMO_HEADER_TOKEN", "aperture-g3-demo-only")
MAX_BODY = 65536


def validate(event):
    if not isinstance(event, dict):
        raise ValueError("CloudEvent object required")
    required = {"id", "source", "specversion", "type", "subject", "time", "datacontenttype", "data"}
    if not required.issubset(event):
        raise ValueError("CloudEvent fields missing")
    uuid.UUID(event["id"])
    datetime.fromisoformat(event["time"].replace("Z", "+00:00"))
    if (event["specversion"] != "1.0" or event["type"] != SUBJECT_TYPE
            or event["subject"] != SUBJECT or event["source"] != "urn:33god:aperture:g3"
            or event["kind"] not in ("event", "command", "reply")
            or event["datacontenttype"] != "application/json" or not isinstance(event["data"], dict)):
        raise ValueError("Only the synthetic G3 CloudEvent is accepted")


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def authorized(self):
        return hmac.compare_digest(self.headers.get("X-Aperture-Demo", ""), TOKEN)

    def do_GET(self):
        if self.path == "/healthz":
            try:
                result = nats_publish.request(f"$JS.API.STREAM.INFO.{STREAM}", {})
                ready = not result.get("error") and "bloodbank.evt.>" in result["config"]["subjects"]
                return self.respond(200, {"ready": ready, "stream": STREAM})
            except (OSError, RuntimeError, ValueError, KeyError) as exc:
                return self.respond(503, {"error": str(exc)})

        if self.path.startswith("/latest"):
            if not self.authorized():
                return self.respond(401, {"error": "demo header required"})
            subject = self._query_subject()
            if not subject.startswith("bloodbank.evt."):
                return self.respond(400, {"error": "subject must be in the bloodbank.evt. domain"})
            try:
                return self.respond(200, nats_publish.read_last(subject, stream=STREAM))
            except (OSError, RuntimeError, ValueError, KeyError) as exc:
                return self.respond(503, {"error": str(exc)})

        return self.respond(404, {"error": "not found"})

    def _query_subject(self):
        from urllib.parse import urlparse, parse_qs
        return parse_qs(urlparse(self.path).query).get("subject", [SUBJECT])[0]

    def do_POST(self):
        if self.path != "/publish":
            return self.respond(404, {"error": "not found"})
        if not self.authorized():
            return self.respond(401, {"error": "demo header required"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY:
                return self.respond(413, {"error": "body must be 1..65536 bytes"})
            event = json.loads(self.rfile.read(size))
            validate(event)
        except (ValueError, TypeError, AttributeError) as exc:
            return self.respond(400, {"error": str(exc)})
        try:
            ack = nats_publish.publish_event(SUBJECT, event, msg_id=event["id"], stream=STREAM)
            if ack.get("stream") != STREAM or not isinstance(ack.get("seq"), int):
                raise RuntimeError("JetStream persistence acknowledgment missing")
            self.respond(200, {"published": True, "id": event["id"], "subject": SUBJECT,
                               "stream": STREAM, "sequence": ack["seq"]})
        except (OSError, RuntimeError, ValueError) as exc:
            self.respond(503, {"error": str(exc)})

    def log_message(self, format, *args):
        print(format % args, flush=True)


if __name__ == "__main__":
    # Create the G3 stream on startup (idempotent; other services may already
    # have done so). Retry briefly so a cold `up` doesn't race the broker.
    import time
    for _ in range(30):
        try:
            nats_publish.ensure_stream()
            break
        except (OSError, TimeoutError, RuntimeError) as exc:
            time.sleep(2)
    ThreadingHTTPServer(("0.0.0.0", 8789), Handler).serve_forever()
