"""Minimal JetStream client over the raw NATS text protocol — stdlib only.

Shared byte-identical between g7/enrichment and g7/hindsight-bridge (copied,
not imported across build contexts; keep both copies in sync).

Supports: CONNECT, request/reply (JS API + publish-with-ack), durable pull
consumers (no_wait polling), plain MSG and HMSG framing (JetStream status
messages arrive as HMSG with a "NATS/1.0 <code>" status line and are surfaced
as JsStatus, not payloads).
"""
from __future__ import annotations

import json
import socket
import time
import uuid


class JsStatus(Exception):
    """A JetStream status message (e.g. 404 no messages) — not an error."""


class NatsError(Exception):
    """Protocol / transport failure; caller should reconnect."""


class NatsConn:
    def __init__(self, url: str, connect_timeout: float = 5.0):
        host, _, port = url.partition("nats://")[2].partition(":")
        if not host:
            raise NatsError(f"bad nats url: {url!r}")
        self.conn = socket.create_connection((host, int(port or 4222)),
                                             timeout=connect_timeout)
        self.conn.settimeout(30.0)
        self.reader = self.conn.makefile("rb")
        info = self.reader.readline()
        if not info.startswith(b"INFO "):
            raise NatsError("NATS INFO missing")
        self._sid = 0
        self._send(b'CONNECT {"verbose":false,"pedantic":false,"tls_required":false,"headers":true}\r\n')

    def close(self) -> None:
        try:
            self.conn.close()
        except OSError:
            pass

    def _send(self, data: bytes) -> None:
        self.conn.sendall(data)

    def _read_line(self) -> bytes:
        line = self.reader.readline()
        if not line:
            raise NatsError("NATS disconnected")
        return line

    def _read_exact(self, n: int) -> bytes:
        data = self.reader.read(n)
        if len(data) != n:
            raise NatsError("NATS truncated payload")
        return data

    def _ping_pong(self, line: bytes) -> bool:
        if line == b"PING\r\n":
            self._send(b"PONG\r\n")
            return True
        return False

    def request(self, subject: str, payload, timeout: float = 5.0) -> dict:
        """One request/reply round trip. `payload` may be dict or bytes.
        Returns the parsed JSON reply; raises JsStatus for status messages."""
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload, separators=(",", ":")).encode()
        elif payload is None:
            payload = b""
        inbox = "_INBOX.g7." + uuid.uuid4().hex
        self._sid += 1
        sid = self._sid
        self._send(f"SUB {inbox} {sid}\r\nUNSUB {sid} 1\r\n".encode())
        self._send(f"PUB {subject} {inbox} {len(payload)}\r\n".encode() + payload + b"\r\n")
        self.conn.settimeout(timeout)
        try:
            msg = self._wait_msg(inbox, sid)
            return json.loads(msg["payload"].decode())
        finally:
            self.conn.settimeout(30.0)

    def _wait_msg(self, inbox: str, sid: int) -> dict:
        while True:
            line = self._read_line()
            if self._ping_pong(line) or line.startswith(b"INFO"):
                continue
            if line.startswith(b"-ERR"):
                raise NatsError(line.decode(errors="replace").strip())
            if line.startswith(b"MSG ") or line.startswith(b"HMSG "):
                return self._parse_message(line, expect_subject=inbox)
            raise NatsError(f"unexpected protocol line: {line!r}")

    def _parse_message(self, line: bytes, expect_subject: str | None = None) -> dict:
        """Parse one MSG/HMSG into {subject, reply, headers, payload(bytes)}.
        Raises JsStatus for NATS/1.0 status messages."""
        headers = b""
        if line.startswith(b"HMSG "):
            parts = line.split()
            # HMSG <subject> <sid> [reply] <hdr_len> <total_len>
            reply = parts[3].decode() if len(parts) == 6 else None
            hdr_len = int(parts[-2])
            total_len = int(parts[-1])
            headers = self._read_exact(hdr_len)
            body_len = total_len - hdr_len
            payload = self._read_exact(body_len) if body_len > 0 else b""
            subject = parts[1].decode()
        else:
            parts = line.split()
            # MSG <subject> <sid> [reply] <len>
            reply = parts[3].decode() if len(parts) == 5 else None
            subject = parts[1].decode()
            payload = self._read_exact(int(parts[-1]))
        if self._read_exact(2) != b"\r\n":
            raise NatsError("missing CRLF after payload")
        if headers:
            status = headers.split(b"\r\n", 1)[0]
            if status.startswith(b"NATS/1.0 ") and not status.startswith(b"NATS/1.0 200"):
                code = status.split(b" ")[1].decode(errors="replace")
                raise JsStatus(f"jetstream status {code}")
        return {"subject": subject, "reply": reply, "headers": headers,
                "payload": payload}

    def publish_ack(self, subject: str, payload: dict, timeout: float = 5.0) -> dict:
        """Publish with JetStream publish-ack (request/reply PUB)."""
        result = self.request(subject, payload, timeout=timeout)
        if isinstance(result, dict) and result.get("error"):
            raise NatsError(f"JetStream error: {result['error']}")
        return result

    def ensure_consumer(self, stream: str, durable: str, filter_subject: str,
                        deliver_policy: str = "all") -> dict:
        """Idempotently create/update a durable pull consumer."""
        return self.request(f"$JS.API.CONSUMER.CREATE.{stream}.{durable}", {
            "stream_name": stream,
            "config": {
                "durable_name": durable,
                "filter_subject": filter_subject,
                "ack_policy": "explicit",
                "deliver_policy": deliver_policy,
                "max_deliver": 10,
            },
        })

    def pull(self, stream: str, durable: str, inbox: str, sid: int,
             batch: int = 1) -> dict | None:
        """One no_wait pull, batch=1: exactly one message OR one status per
        request keeps the synchronous read loop in lockstep with the server
        (batch>1 delivers multiple MSGs per request and desyncs the next
        read). Returns the parsed message or None on 404/408 no-messages."""
        req = json.dumps({"batch": batch, "no_wait": True},
                         separators=(",", ":")).encode()
        self._send(f"PUB $JS.API.CONSUMER.MSG.NEXT.{stream}.{durable} {inbox} "
                   f"{len(req)}\r\n".encode() + req + b"\r\n")
        self.conn.settimeout(10.0)
        try:
            while True:
                line = self._read_line()
                if self._ping_pong(line) or line.startswith(b"INFO"):
                    continue
                if line.startswith(b"-ERR"):
                    raise NatsError(line.decode(errors="replace").strip())
                if line.startswith(b"MSG ") or line.startswith(b"HMSG "):
                    return self._parse_message(line)
                raise NatsError(f"unexpected protocol line: {line!r}")
        except JsStatus:
            return None
        finally:
            self.conn.settimeout(30.0)

    def subscribe_inbox(self, inbox: str) -> int:
        self._sid += 1
        self._send(f"SUB {inbox} {self._sid}\r\n".encode())
        return self._sid

    def ack(self, ack_subject: str) -> None:
        """Acknowledge a delivered message (plain PUB to its reply subject)."""
        self._send(f"PUB {ack_subject} 0\r\n\r\n".encode())


def connect_retry(url: str, tries: int = 60, delay: float = 2.0) -> NatsConn:
    last: Exception | None = None
    for _ in range(tries):
        try:
            return NatsConn(url)
        except (OSError, NatsError) as exc:
            last = exc
            time.sleep(delay)
    raise NatsError(f"cannot connect to {url}: {last}")
