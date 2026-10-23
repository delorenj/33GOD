"""G2 demo-only HTTP -> JetStream adapter. Stdlib, no custom n8n nodes.

Not a general Bloodbank ingress: fixed synthetic subject, local broker only.
Acknowledges HTTP only after JetStream returns a persisted sequence number.
"""
import base64
from datetime import datetime
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import socket
import uuid

SUBJECT = "bloodbank.evt.aperture.smoke.g2"          # NATS subject (5 tokens)
SUBJECT_TYPE = "bloodbank.aperture.smoke.g2"          # CloudEvents type (4 tokens)
STREAM = os.environ.get("GOD_OUTBOX_STREAM", "G2_SMOKE")
# Attached mode: publish into an existing bus (e.g. G1's BLOODBANK_EVENTS)
# without owning a stream there — see groups/SEAM-G1-G2.md. Host default is
# the standalone broker service; GOD_BUS_NATS_URL overrides with any
# nats://host:port when the bundle is attached to an external network.
BUS_URL = os.environ.get("GOD_BUS_NATS_URL", "")
BUS_HOST, _, BUS_PORT = BUS_URL.partition("nats://")[2].partition(":") if BUS_URL else ("", "", "")
TARGET_HOST = BUS_HOST or os.environ.get("GOD_NATS_HOST", "nats-outbox-broker")
TARGET_PORT = int(BUS_PORT or 4222)
ATTACHED = bool(BUS_HOST)
TOKEN = os.environ.get("GOD_DEMO_HEADER_TOKEN", "aperture-g2-demo-only")
MAX_BODY = 65536


def request(subject, data):
    """One bounded NATS request/reply; tolerate server PING interleaving."""
    inbox = "_INBOX.g2." + uuid.uuid4().hex
    payload = json.dumps(data, separators=(",", ":")).encode()
    with socket.create_connection((TARGET_HOST, TARGET_PORT), timeout=5) as conn:
        conn.settimeout(5)
        reader = conn.makefile("rb")
        if not reader.readline().startswith(b"INFO "):
            raise RuntimeError("NATS INFO missing")
        conn.sendall(b'CONNECT {"verbose":false,"pedantic":false}\r\n')
        conn.sendall(f"SUB {inbox} 1\r\nUNSUB 1 1\r\n".encode())
        conn.sendall(f"PUB {subject} {inbox} {len(payload)}\r\n".encode() + payload + b"\r\n")
        while True:
            line = reader.readline()
            if not line:
                raise RuntimeError("NATS disconnected")
            if line == b"PING\r\n":
                conn.sendall(b"PONG\r\n")
            elif line.startswith(b"-ERR"):
                raise RuntimeError("NATS protocol error")
            elif line.startswith(b"MSG "):
                size = int(line.split()[-1])
                if size > 2 * MAX_BODY:
                    raise RuntimeError("NATS response too large")
                body = reader.read(size)
                if len(body) != size or reader.read(2) != b"\r\n":
                    raise RuntimeError("NATS truncated response")
                result = json.loads(body)
                if result.get("error"):
                    raise RuntimeError(f"JetStream error: {result['error'].get('err_code')}")
                return result


def setup_stream():
    return request(f"$JS.API.STREAM.CREATE.{STREAM}", {
        "name": STREAM, "subjects": [SUBJECT], "storage": "file",
        "retention": "limits", "max_msgs": 100, "max_bytes": 1048576,
        "max_age": 86400000000000, "num_replicas": 1,
    })


def validate(event):
    if not isinstance(event, dict):
        raise ValueError("CloudEvent object required")
    required = {"id", "source", "specversion", "type", "subject", "time", "datacontenttype",
                "correlationid", "causationid", "producer", "service", "domain", "kind",
                "ordering_key", "actor", "data"}
    if not required.issubset(event):
        raise ValueError("CloudEvent fields missing")
    uuid.UUID(event["id"])
    datetime.fromisoformat(event["time"].replace("Z", "+00:00"))
    # Canonical contract: type = 4 dotted tokens (no kind marker); subject
    # = 5 tokens with evt marker; the (domain,entity,action) triple must
    # agree across both. See bloodbank/docs/event-naming.md §2/§3.
    type_tokens = event["type"].split(".")
    subj_tokens = event["subject"].split(".")
    if (len(type_tokens) != 4 or type_tokens[0] != "bloodbank"
            or event["subject"] != "bloodbank.evt." + event["type"].split(".", 1)[1]):
        raise ValueError("type/subject must follow canonical 4/5-token shape")
    if (event["specversion"] != "1.0" or event["type"] != SUBJECT_TYPE
            or event["subject"] != SUBJECT or event["source"] != "urn:33god:aperture:g2"
            or event["datacontenttype"] != "application/json"
            or event["kind"] not in ("event", "command", "reply")
            or not isinstance(event["data"], dict)):
        raise ValueError("Only the canonical G2 CloudEvent is accepted")


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
        if self.path not in ("/healthz", "/latest"):
            return self.respond(404, {"error": "not found"})
        if self.path != "/healthz" and not self.authorized():
            return self.respond(401, {"error": "demo header required"})
        try:
            if self.path == "/healthz":
                if ATTACHED:
                    return self.respond(200, {"ready": True, "attached": True})
                result = request(f"$JS.API.STREAM.INFO.{STREAM}", {})
                return self.respond(200, {"ready": result["config"]["subjects"] == [SUBJECT]})
            result = request(f"$JS.API.STREAM.MSG.GET.{STREAM}", {"last_by_subj": SUBJECT})
            msg = result["message"]
            return self.respond(200, {"subject": msg["subject"], "sequence": msg["seq"],
                                      "event": json.loads(base64.b64decode(msg["data"]))})
        except (OSError, RuntimeError, ValueError, KeyError) as exc:
            self.respond(503, {"error": str(exc)})

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
            ack = request(SUBJECT, event)
            if ack.get("stream") != STREAM or not isinstance(ack.get("seq"), int):
                raise RuntimeError("JetStream persistence acknowledgment missing")
            self.respond(200, {"published": True, "id": event["id"], "subject": SUBJECT,
                               "stream": STREAM, "sequence": ack["seq"]})
        except (OSError, RuntimeError, ValueError) as exc:
            self.respond(503, {"error": str(exc)})

    def log_message(self, format, *args):
        # No body, auth header or credential logging.
        print(format % args, flush=True)


if __name__ == "__main__":
    if not ATTACHED:
        # Standalone mode owns its demo stream. Attached mode (GOD_BUS_NATS_URL)
        # publishes into the existing bus stream and must NOT create streams.
        setup_stream()
    ThreadingHTTPServer(("0.0.0.0", 8789), Handler).serve_forever()
