"""vinyl server mode — remote dictation backend (the heavy-lifting side).

Listens on TCP for a paired vinyl client. One client session at a time
(single-owner discipline). Uses its own lock file, so the server host can
also run `vinyl client --server 127.0.0.1` for its own hotkey dictation.

Per session: fresh losslessly framed silero VAD -> progressive/final decode
requests -> shared warm Recognizer -> partial/final text frames back.

The server writes the same ~/.local/state/vinyl/state.json mirror the local
daemon writes, so the tray on this machine shows RED while a remote client
dictates. Each session records received audio and its decode/transport timeline
locally, linked to the client trace that owns injection and desktop observation.
"""
import json
import os
import socket
import socketserver
import threading
import time
from fcntl import flock, LOCK_EX, LOCK_NB
from pathlib import Path

import numpy as np

from . import __version__
from .engine import Recognizer, DEFAULT_MODEL_DIR, SAMPLE_RATE, is_sparse
from .protocol import ProtocolError, recv_msg, send_msg
from .rpc import STATE_DIR, STATE_PATH, write_state
from .streaming import DecodeQueue, DecodeRequest, VadSegmenter
from .trace import TraceSession
from .vad import make_vad, MAX_SEGMENT_SECONDS, DEFAULT_VAD_MODEL, MIN_SILENCE_SECONDS, VAD_THRESHOLD

DEFAULT_PORT = 7733
STOP_JOIN_TIMEOUT = MAX_SEGMENT_SECONDS + 15
ABORT_JOIN_TIMEOUT = 5.0
TOKEN_PATH = Path("~/.config/vinyl/server.token").expanduser()
# Separate lock from the local daemon: on the server host you may run
# `vinyl serve` (for remote clients) AND `vinyl client --server 127.0.0.1`
# (this machine's own hotkey dictation) side by side.
SERVE_LOCK_PATH = STATE_DIR / "vinyld-serve.lock"


def load_or_create_token(path: Path = TOKEN_PATH) -> str:
    path = Path(path)
    if path.exists():
        return path.read_text().strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    token = os.urandom(24).hex()
    path.write_text(token + "\n")
    path.chmod(0o600)
    return token


class _Session:
    """One remote dictation session: VAD in, ordered partials/finals out."""

    def __init__(self, recognizer: Recognizer, sock: socket.socket,
                 trace: TraceSession | None = None):
        self.recognizer = recognizer
        self.sock = sock
        self.trace = trace if trace is not None else TraceSession("server")
        self.vad = make_vad()
        self.segmenter = VadSegmenter(self.vad, trace=self.trace) if self.vad is not None else None
        self.q: DecodeQueue = DecodeQueue(trace=self.trace)
        self.alive = True
        self.segments = 0
        self.audio_frames = 0
        self._send_lock = threading.Lock()
        self._closed = False
        self.trace.event("server.session.ready", vad_available=self.vad is not None)
        if self.segmenter:
            self.trace.event("vad.config", threshold=VAD_THRESHOLD,
                             min_silence_s=MIN_SILENCE_SECONDS, max_segment_s=MAX_SEGMENT_SECONDS,
                             partial_min_samples=self.segmenter.partial_min_samples,
                             partial_interval_samples=self.segmenter.partial_interval_samples)
        self.decode_thread = threading.Thread(target=self._decode_loop, daemon=True)
        self.decode_thread.start()

    def feed(self, pcm: bytes) -> None:
        self.trace.audio(pcm, frames=len(pcm) // 4, sample_rate=16000,
                         source="network", start_sample=self.audio_frames)
        samples = np.frombuffer(pcm, dtype="<f4")
        self.audio_frames += int(samples.size)
        if self.segmenter is None:
            self.trace.event("audio.dropped", reason="vad_unavailable", frames=int(samples.size))
            return  # energy-gate fallback not supported remotely; require VAD
        for request in self.segmenter.feed(samples):
            self.q.put(request)

    def flush(self) -> None:
        self.trace.event("server.flush.start")
        if self.segmenter is not None:
            for request in self.segmenter.flush():
                self.q.put(request)
        self.trace.event("server.flush.end")

    def send(self, msg: dict) -> None:
        # Messages are generated here, never the raw client's hello/auth object.
        fields = {"frame_type": msg["type"]}
        if msg["type"] in ("partial", "final"):
            fields.update(segment=msg["segment"], text=msg["text"])
        elif msg["type"] == "error":
            fields["error"] = msg["error"]
        begin = time.monotonic_ns()
        with self._send_lock:
            if not self.alive:
                self.trace.event("network.send.dropped", reason="inactive_session", **fields)
                return
            self.trace.event("network.send.start", **fields)
            try:
                send_msg(self.sock, msg)
            except OSError as e:
                self.trace.event("network.send.error", error=str(e), frame_type=msg["type"])
                raise
            self.trace.event("network.send.end", duration_ms=(time.monotonic_ns() - begin) / 1e6,
                             **fields)

    def finish(self) -> None:
        """Stop accepting audio, decode the remainder, reply stopped."""
        self.trace.event("session.stop.requested")
        self.flush()
        self.q.put(None)
        self.decode_thread.join(timeout=STOP_JOIN_TIMEOUT)
        if self.decode_thread.is_alive():
            self.trace.event("session.error", stage="stop", error="decode drain timed out")
            raise TimeoutError("decode drain timed out")
        if self.alive:
            self.send({"type": "stopped", "segments": self.segments,
                       "trace_ref": self.trace.ref})

    def abort(self, reason: str = "cancelled") -> bool:
        """Bound cleanup; return whether the shared recognizer is free to reuse."""
        if self._closed:
            return not self.decode_thread.is_alive()
        self._closed = True
        self.alive = False
        # A peer that stops reading can leave sendall holding _send_lock.
        # Shutdown first and never wait for that lock while disabling output.
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.trace.event("session.output.disabled", reason=reason)
        self.q.put(None)
        if self.decode_thread is not threading.current_thread():
            self.decode_thread.join(timeout=ABORT_JOIN_TIMEOUT)
        worker_pending = self.decode_thread.is_alive()
        if worker_pending:
            self.trace.event("decode.worker.pending", reason=reason, output_disabled=True,
                             recognizer_reserved=True)
        self.trace.finish(reason, audio_frames_received=self.audio_frames,
                          segments_decoded=self.segments, incomplete=worker_pending)
        return not worker_pending

    def _decode_loop(self) -> None:
        while True:
            request = self.q.get()
            if request is None:
                return
            fields = request.trace_fields()
            if not self.alive:
                self.trace.event("decode.dropped", reason="inactive_session", **fields)
                continue
            begin = time.monotonic_ns()
            self.trace.event("decode.start", queue_wait_ms=(begin - request.created_ns) / 1e6,
                             **fields)
            try:
                context = {key: value for key, value in fields.items() if key != "samples"}
                text = self.recognizer.decode(request.samples, preroll=request.preroll,
                                              trace=self.trace, **context)
                self.trace.event("decode.completed", text=text,
                                 duration_ms=(time.monotonic_ns() - begin) / 1e6, **fields)
                if not self.alive:
                    self.trace.event("decode.dropped", reason="inactive_session", text=text, **fields)
                elif request.final and text:
                    self.send({"type": "final", "segment": request.segment, "text": text})
                    self.segments += 1
                elif not request.final and not is_sparse(text, len(request.samples) / SAMPLE_RATE):
                    self.send({"type": "partial", "segment": request.segment, "text": text})
                elif text:
                    # Still a collapse after the second opinion. Don't spend a
                    # client's keystrokes typing it and backing over it.
                    self.trace.event("publish.withheld", text=text,
                                     reason="sparse_hypothesis", **fields)
                else:
                    self.trace.event("decode.dropped", reason="empty_transcript", **fields)
            except (OSError, ProtocolError) as e:
                self.trace.event("session.error", stage="decode_transport", error=str(e), **fields)
                self.alive = False
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                return
            except Exception as e:  # one bad segment must not kill the session
                self.trace.event("decode.error", error=str(e), **fields)
                try:
                    self.send({"type": "error", "error": str(e)})
                except OSError:
                    self.alive = False
                    try:
                        self.sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    return


class _Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        srv: "_Server" = self.server  # type: ignore[assignment]
        sock: socket.socket = self.request
        try:
            msg, _ = recv_msg(sock)
        except (ProtocolError, OSError, json.JSONDecodeError, AttributeError, ValueError):
            return
        if msg.get("type") != "hello" or msg.get("token") != srv.token:
            try:
                send_msg(sock, {"type": "error", "error": "unauthorized"})
            except OSError:
                pass
            return
        if not srv.session_lock.acquire(blocking=False):
            try:
                send_msg(sock, {"type": "busy"})
            except OSError:
                pass
            return
        # Authentication is complete. Only explicitly selected non-secret
        # metadata enters the recorder; no auth packet or token is serialized.
        parent_ref = msg.get("trace_ref")
        if not isinstance(parent_ref, str) or len(parent_ref) > 512 or srv.token in parent_ref:
            parent_ref = None
        trace = TraceSession("server", metadata={"vinyl_version": __version__,
                                                "recognizer": getattr(srv.recognizer, "trace_config", {}),
                                                "peer": str(self.client_address[0]),
                                                "sample_rate": 16000}, parent_ref=parent_ref)
        session = None
        reason = "disconnected"
        try:
            trace.event("network.receive", frame_type="hello", authenticated=True)
            session = _Session(srv.recognizer, sock, trace=trace)
            srv._set_state("listening", peer=str(self.client_address[0]), trace=trace)
            session.send({"type": "ready", "trace_ref": trace.ref})
            while session.alive:
                try:
                    msg, audio = recv_msg(sock)
                except (ProtocolError, OSError, json.JSONDecodeError, AttributeError, ValueError) as e:
                    trace.event("network.receive.error", error=str(e))
                    break
                kind = msg.get("type")
                trace.event("network.receive", frame_type=kind if kind in (
                    "audio", "stop", "cancel") else "unknown", bytes=len(audio) if audio else 0)
                if kind == "audio" and audio:
                    session.feed(audio)
                elif kind == "stop":
                    session.finish()
                    reason = "stopped"
                    break
                elif kind == "cancel":
                    trace.event("session.cancel.requested")
                    reason = "cancelled"
                    break
        except Exception as e:
            reason = "error"
            trace.event("session.error", stage="server", error=str(e).replace(srv.token, "[redacted]"))
        finally:
            worker_stopped = session.abort(reason) if session is not None else True
            if session is None:
                trace.finish(reason)
            if worker_stopped:
                try:
                    srv._set_state("idle", trace=trace)
                finally:
                    srv.session_lock.release()
            else:
                srv._set_state("stopping", peer=str(self.client_address[0]), trace=trace)
                # The trace is durably incomplete and the TCP handler can exit,
                # but no second session may use sherpa while this call remains
                # in flight. A daemon reaper releases ownership after it exits.
                def release_when_finished():
                    session.decode_thread.join()
                    try:
                        srv._set_state("idle", trace=trace)
                    finally:
                        srv.session_lock.release()
                threading.Thread(target=release_when_finished, daemon=True,
                                 name="vinyl-server-reaper").start()


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    recognizer: Recognizer
    token: str
    session_lock: threading.Lock

    def _set_state(self, state: str, peer: str | None = None,
                   trace: TraceSession | None = None) -> None:
        if trace is not None:
            self._trace_info = trace.info()
        snap = {
            "state": state,
            "mode": "server",
            "peer": peer,
            "pid": os.getpid(),
            "started_at": getattr(self, "_started_at", None) if state != "idle" else None,
            **getattr(self, "_trace_info", {}),
        }
        if state != "idle":
            self._started_at = snap["started_at"] or time.time()
            snap["started_at"] = self._started_at
        try:
            write_state(snap)
        except OSError:
            pass


def serve(host: str = "0.0.0.0", port: int = DEFAULT_PORT,
          model_dir: Path = DEFAULT_MODEL_DIR, token: str | None = None) -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_fd = open(SERVE_LOCK_PATH, "w")
    try:
        flock(lock_fd, LOCK_EX | LOCK_NB)
    except BlockingIOError:
        print("vinyl server already running (lock held)", flush=True)
        return 1

    token = token or load_or_create_token()
    recognizer = Recognizer(model_dir)
    server = _Server((host, port), _Handler)
    server.recognizer = recognizer
    server.token = token
    server.session_lock = threading.Lock()
    server._set_state("idle")
    print(f"vinyl server listening on {host}:{port} (token: {TOKEN_PATH})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
