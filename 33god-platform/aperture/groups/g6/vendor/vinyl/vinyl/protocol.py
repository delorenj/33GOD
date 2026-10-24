"""Wire protocol between vinyl client and server.

Framing: every message is a 4-byte big-endian length + a JSON object.
Audio travels as a control message {"type": "audio", "n": <bytes>}
immediately followed by <n> raw float32 LE samples — no per-sample JSON.

Client -> Server:
  {"type": "hello", "token": str, "rate": 16000}
  {"type": "audio", "n": int} + raw bytes
  {"type": "stop"}     — flush VAD, decode remainder, then expect "stopped"
  {"type": "cancel"}   — drop everything in flight

Server -> Client:
  {"type": "ready"}  | {"type": "error", "error": str}
  {"type": "partial", "segment": int, "text": str} — replace prior partial
  {"type": "final", "segment": int, "text": str}   — replace + commit
  {"type": "busy"}     — another client holds the session
  {"type": "stopped"}  — response to stop, after all finals are sent
"""
import json
import socket
import struct

HEADER = struct.Struct(">I")
PROTO_VERSION = 2


class ProtocolError(Exception):
    pass


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ProtocolError("connection closed mid-frame")
        buf.extend(chunk)
    return bytes(buf)


def send_msg(sock: socket.socket, obj: dict) -> None:
    data = json.dumps(obj).encode()
    sock.sendall(HEADER.pack(len(data)) + data)


def send_audio(sock: socket.socket, pcm: bytes) -> None:
    send_msg(sock, {"type": "audio", "n": len(pcm)})
    sock.sendall(pcm)


def recv_msg(sock: socket.socket, max_bytes: int = 1 << 20) -> tuple[dict, bytes | None]:
    """Returns (message, audio_bytes). audio_bytes is set only for type=audio."""
    (n,) = HEADER.unpack(_recv_exact(sock, HEADER.size))
    if n > max_bytes:
        raise ProtocolError(f"oversized frame: {n}")
    obj = json.loads(_recv_exact(sock, n))
    audio = None
    if obj.get("type") == "audio":
        an = int(obj.get("n", 0))
        if an > 64 << 20:
            raise ProtocolError(f"oversized audio frame: {an}")
        audio = _recv_exact(sock, an)
    return obj, audio
