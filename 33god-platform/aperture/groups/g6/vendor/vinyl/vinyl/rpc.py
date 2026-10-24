"""Shared lightweight plumbing: state paths, RPC socket server, state mirror.

This module must stay dependency-free (no sherpa_onnx, no sounddevice) — the
thin client laptop imports it, and it has neither the model nor the venv for
it. Anything that needs the engine lives in daemon.py / server.py.
"""
import json
import os
import socket
import socketserver
import threading
from pathlib import Path

STATE_DIR = Path("~/.local/state/vinyl").expanduser()
SOCK_PATH = STATE_DIR / "vinyld.sock"
LOCK_PATH = STATE_DIR / "vinyld.lock"
STATE_PATH = STATE_DIR / "state.json"


class State:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.listening = False
        self.started_at: float | None = None
        self.segments_decoded = 0
        self.last_text = ""
        self.partial_text = ""
        self.last_error = ""
        self.trace_id = ""
        self.trace_ref = ""
        self.trace_path = ""
        self.trace_error = ""

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "state": "listening" if self.listening else "idle",
                "started_at": self.started_at,
                "segments_decoded": self.segments_decoded,
                "last_text": self.last_text,
                "partial_text": self.partial_text,
                "last_error": self.last_error,
                "trace_id": self.trace_id,
                "trace_ref": self.trace_ref,
                "trace_path": self.trace_path,
                "trace_error": self.trace_error,
                "pid": os.getpid(),
            }


class RpcHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        cmd = self.rfile.readline().decode().strip()
        resp = self.server.daemon.handle(cmd)  # type: ignore[attr-defined]
        self.wfile.write((json.dumps(resp) + "\n").encode())


class UnixRpcServer(socketserver.UnixStreamServer):
    daemon: object  # VinylDaemon | VinylClientDaemon — both expose handle()


def rpc(cmd: str, timeout: float = 45.0) -> dict:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect(str(SOCK_PATH))
    s.sendall((cmd + "\n").encode())
    f = s.makefile()
    return json.loads(f.readline())


def write_state(snap: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(snap, indent=2))
    tmp.rename(STATE_PATH)
