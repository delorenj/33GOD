"""Stdlib-only NATS JetStream publisher + request/reply helper for Aperture G3.

Crib sources (verbatim, adaptation noted inline):
- Socket primitives (_parse_endpoint, _config, _remaining, _resolve, _connect,
  _send, _read_line): bloodbank/services/agent-hooks/core/nats_publish.py —
  env var names adapted from BLOODBANK_* / DECKARD_NATS to the G3 GOD_*
  convention.
- HPUB + JetStream PubAck (publish_event): bloodbank/services/hook-hub/
  observations.py publish() — same header frame, Nats-Msg-Id /
  Nats-Expected-Stream, and correlated PubAck verification.
- JetStream API request/reply (request / ensure_stream / read_last): Aperture
  G2 outbox/server.py request()/setup_stream() pattern, generalized from the
  fixed G2_SMOKE stream to the G3_EVENTS stream.

A PONG is transport progress, never evidence that JetStream stored an event.
publish_event() returns only after the correlated PubAck carries the expected
stream and a positive sequence number.

Env:
  GOD_NATS_HOST   NATS broker hostname (default: "nats")
  GOD_NATS_PORT   NATS client port   (default: 4222)
  G3_STREAM       JetStream stream   (default: "G3_EVENTS")
  G3_SUBJECTS     stream subjects    (default: "bloodbank.evt.>")
"""
from __future__ import annotations

import json
import os
import queue
import socket
import threading
import time
import uuid

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4222
MAX_CONTROL_LINE = 16 * 1024
MAX_BODY = 65536

G3_STREAM = os.environ.get("G3_STREAM", "G3_EVENTS")
G3_SUBJECTS = [s for s in os.environ.get("G3_SUBJECTS", "bloodbank.evt.>").split(",") if s]


def _parse_endpoint(value: str) -> tuple[str, int]:
    endpoint = value.strip()
    if endpoint.startswith("nats://"):
        endpoint = endpoint[7:]
    if not endpoint:
        return DEFAULT_HOST, DEFAULT_PORT
    if endpoint.startswith("["):
        close = endpoint.find("]")
        if close < 0:
            raise ValueError(f"invalid bracketed NATS endpoint: {value!r}")
        host = endpoint[1:close]
        rest = endpoint[close + 1:]
        port = DEFAULT_PORT if not rest else int(rest.removeprefix(":"))
    elif endpoint.count(":") == 1:
        host, port_text = endpoint.rsplit(":", 1)
        port = int(port_text) if port_text else DEFAULT_PORT
    else:
        host, port = endpoint, DEFAULT_PORT
    if not host or not 1 <= port <= 65535:
        raise ValueError(f"invalid NATS endpoint: {value!r}")
    return host, port


def _config() -> tuple[str, int, float]:
    host, port = _parse_endpoint(os.environ.get("GOD_NATS_URL", os.environ.get("GOD_NATS_HOST", f"{DEFAULT_HOST}:{DEFAULT_PORT}")))
    timeout = float(os.environ.get("GOD_NATS_TIMEOUT", "5.0"))
    if timeout <= 0:
        raise ValueError("GOD_NATS_TIMEOUT must be positive")
    return host, port, timeout


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("NATS deadline expired before PONG")
    return remaining


def _resolve(host: str, port: int, deadline: float) -> list[tuple]:
    result: queue.Queue[tuple[bool, object]] = queue.Queue(maxsize=1)

    def resolve() -> None:
        try:
            addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            result.put((True, addresses))
        except BaseException as exc:  # propagate resolver failures in caller thread
            result.put((False, exc))

    threading.Thread(target=resolve, name="g3-nats-dns", daemon=True).start()
    try:
        ok, value = result.get(timeout=_remaining(deadline))
    except queue.Empty as exc:
        raise TimeoutError("NATS deadline expired during DNS") from exc
    if not ok:
        raise value  # type: ignore[misc]
    return value  # type: ignore[return-value]


def _connect(host: str, port: int, deadline: float) -> socket.socket:
    last_error: OSError | None = None
    for family, socktype, proto, _, sockaddr in _resolve(host, port, deadline):
        sock = socket.socket(family, socktype, proto)
        try:
            sock.settimeout(_remaining(deadline))
            sock.connect(sockaddr)
            return sock
        except OSError as exc:
            last_error = exc
            sock.close()
    if last_error is not None:
        raise last_error
    raise OSError(f"no addresses resolved for NATS host {host!r}")


def _send(sock: socket.socket, data: bytes, deadline: float) -> None:
    sock.settimeout(_remaining(deadline))
    sock.sendall(data)


def _read_line(
    sock: socket.socket, buffered: bytearray, deadline: float
) -> tuple[bytes, bytearray]:
    while True:
        boundary = buffered.find(b"\r\n")
        if boundary >= 0:
            if boundary > MAX_CONTROL_LINE:
                raise RuntimeError("NATS control line exceeds bounded input")
            line = bytes(buffered[:boundary])
            return line, bytearray(buffered[boundary + 2:])
        if len(buffered) > MAX_CONTROL_LINE:
            raise RuntimeError("NATS control line exceeds bounded input")
        sock.settimeout(_remaining(deadline))
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("NATS connection reached EOF before PONG")
        buffered.extend(chunk)


def request(subject: str, data: dict, *, timeout: float = 5.0) -> dict:
    """One bounded NATS request/reply; tolerate server PING interleaving.

    Returns the JSON response body as-is, INCLUDING any JetStream ``error``
    member (callers inspect ``.get("error")``). Transport/protocol failures
    raise. Cribbed from G2 outbox/server.py request().
    """
    inbox = "_INBOX.g3." + uuid.uuid4().hex
    payload = json.dumps(data, separators=(",", ":")).encode()
    host, port, _ = _config()
    deadline = time.monotonic() + timeout
    with _connect(host, port, deadline) as sock:
        line, buffered = _read_line(sock, bytearray(), deadline)
        if not line.startswith(b"INFO "):
            raise RuntimeError("NATS INFO missing")
        _send(sock, b'CONNECT {"verbose":false,"pedantic":false}\r\n', deadline)
        _send(sock, f"SUB {inbox} 1\r\nUNSUB 1 1\r\n".encode(), deadline)
        _send(sock, f"PUB {subject} {inbox} {len(payload)}\r\n".encode() + payload + b"\r\n", deadline)
        while True:
            line, buffered = _read_line(sock, buffered, deadline)
            if line == b"PING":
                _send(sock, b"PONG\r\n", deadline)
            elif line.startswith(b"-ERR"):
                raise RuntimeError("NATS protocol error")
            elif line.startswith(b"MSG "):
                size = int(line.split()[-1])
                if size > 2 * MAX_BODY:
                    raise RuntimeError("NATS response too large")
                while len(buffered) < size + 2:
                    sock.settimeout(_remaining(deadline))
                    chunk = sock.recv(min(16384, size + 2 - len(buffered)))
                    if not chunk:
                        raise RuntimeError("NATS truncated response")
                    buffered.extend(chunk)
                if buffered[size:size + 2] != b"\r\n":
                    raise RuntimeError("NATS truncated response")
                return json.loads(bytes(buffered[:size]))


def ensure_stream(
    name: str = G3_STREAM, subjects: list[str] | None = None, *, timeout: float = 5.0
) -> dict:
    """Idempotent JetStream stream creation.

    INFO first; a missing stream (err_code 10059) triggers CREATE; a lost
    CREATE race (err_code 10058, "already in use") is treated as success.
    """
    subjects = subjects if subjects is not None else G3_SUBJECTS
    info = request(f"$JS.API.STREAM.INFO.{name}", {}, timeout=timeout)
    if not info.get("error"):
        return info
    if info["error"].get("err_code") != 10059:  # not "stream not found"
        raise RuntimeError(f"STREAM.INFO failed: {info['error']}")
    created = request(
        f"$JS.API.STREAM.CREATE.{name}",
        {
            "name": name,
            "subjects": subjects,
            "storage": "file",
            "retention": "limits",
            "max_msgs": 1000,
            "max_bytes": 10485760,
            "max_age": 86400000000000,
            "num_replicas": 1,
        },
        timeout=timeout,
    )
    if created.get("error"):
        if created["error"].get("err_code") == 10058:  # already exists
            return {"created": False, "already_existed": True}
        raise RuntimeError(f"STREAM.CREATE failed: {created['error']}")
    return created


def publish_event(
    subject: str,
    event: dict,
    *,
    msg_id: str,
    stream: str = G3_STREAM,
    timeout: float = 5.0,
) -> dict:
    """Publish one CloudEvent with a JetStream storage acknowledgement.

    Header-publish (HPUB) with Nats-Msg-Id (dedup) and Nats-Expected-Stream,
    then waits for the correlated PubAck on the reply inbox. Returns the ack
    dict ({stream, seq, ...}) only after the broker confirms persistence.
    Cribbed from bloodbank hook-hub observations.py publish().
    """
    host, port, _ = _config()
    deadline = time.monotonic() + timeout
    payload = json.dumps(event, separators=(",", ":")).encode()
    if len(payload) > MAX_BODY:
        raise ValueError("event exceeds transport limit")
    inbox = "_INBOX.g3pub." + uuid.uuid4().hex
    headers = (
        f"NATS/1.0\r\nNats-Msg-Id: {msg_id}\r\n"
        f"Nats-Expected-Stream: {stream}\r\n\r\n"
    ).encode()
    with _connect(host, port, deadline) as sock:
        line, buffered = _read_line(sock, bytearray(), deadline)
        if not line.startswith(b"INFO "):
            raise RuntimeError("invalid_nats_greeting")
        info = json.loads(line[5:])
        if len(payload) + len(headers) > info.get("max_payload", MAX_BODY + 1024):
            raise ValueError("event exceeds broker limit")
        options = {
            "verbose": False, "pedantic": False, "name": "g3-publisher",
            "lang": "python-stdlib", "version": "1", "protocol": 1,
            "headers": True, "no_responders": True,
        }
        frame = (
            b"CONNECT " + json.dumps(options).encode() + b"\r\n"
            + f"SUB {inbox} 1\r\nUNSUB 1 1\r\n".encode()
            + f"HPUB {subject} {inbox} {len(headers)} {len(headers) + len(payload)}\r\n".encode()
            + headers + payload + b"\r\n"
        )
        _send(sock, frame, deadline)
        while True:
            line, buffered = _read_line(sock, buffered, deadline)
            if line == b"PING":
                _send(sock, b"PONG\r\n", deadline)
            elif line.startswith(b"-ERR") or line.startswith(b"HMSG"):
                raise RuntimeError("jetstream_publish_rejected")
            elif line.startswith(b"MSG "):
                parts = line.split()
                size = int(parts[-1])
                if len(parts) not in {4, 5} or parts[1].decode() != inbox or parts[2] != b"1" or not 0 < size <= 16384:
                    raise RuntimeError("invalid_jetstream_ack")
                while len(buffered) < size + 2:
                    sock.settimeout(_remaining(deadline))
                    chunk = sock.recv(min(16384, size + 2 - len(buffered)))
                    if not chunk:
                        raise RuntimeError("jetstream_ack_incomplete")
                    buffered.extend(chunk)
                if buffered[size:size + 2] != b"\r\n":
                    raise RuntimeError("invalid_jetstream_ack")
                ack = json.loads(bytes(buffered[:size]))
                if ack.get("error") or ack.get("stream") != stream or not isinstance(ack.get("seq"), int) or ack["seq"] < 1:
                    raise RuntimeError("jetstream_ack_failed")
                return ack
            # Ignore PONG: only the correlated PubAck finishes the publish.


def read_last(subject: str, *, stream: str = G3_STREAM, timeout: float = 5.0) -> dict:
    """Read back the latest retained message for a subject from the stream.

    Uses $JS.API.STREAM.MSG.GET with last_by_subj; the stored message body is
    base64 and decoded back into the original event. No HTTP cache stands in
    for bus evidence. Cribbed from G2 outbox/server.py GET /latest.
    """
    import base64

    result = request(
        f"$JS.API.STREAM.MSG.GET.{stream}",
        {"last_by_subj": subject},
        timeout=timeout,
    )
    if result.get("error"):
        raise RuntimeError(f"STREAM.MSG.GET failed: {result['error']}")
    msg = result["message"]
    return {
        "subject": msg["subject"],
        "sequence": msg["seq"],
        "event": json.loads(base64.b64decode(msg["data"])),
    }
