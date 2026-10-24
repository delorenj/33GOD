"""Actual Vinyl authenticated TCP stream -> warm Whisper -> final text."""
from pathlib import Path
import socket
import subprocess
import numpy as np
from vinyl.protocol import send_msg, send_audio, recv_msg

token = Path("/home/voice/.config/vinyl/server.token").read_text().strip()
# Missing/incorrect token rejection.
with socket.create_connection(("127.0.0.1", 7733), timeout=10) as sock:
    send_msg(sock, {"type": "hello", "token": "incorrect"})
    assert recv_msg(sock)[0] == {"type": "error", "error": "unauthorized"}
print("PASS Vinyl unauthorized rejected")
raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", "/app/smoke/speech.wav",
                               "-f", "f32le", "-ar", "16000", "-ac", "1", "pipe:1"])
raw += np.zeros(16000, dtype="<f4").tobytes()
with socket.create_connection(("127.0.0.1", 7733), timeout=90) as sock:
    send_msg(sock, {"type": "hello", "token": token, "rate": 16000})
    assert recv_msg(sock)[0]["type"] == "ready"
    for start in range(0, len(raw), 6400):
        send_audio(sock, raw[start:start + 6400])
    send_msg(sock, {"type": "stop"})
    finals = []
    while True:
        frame, _ = recv_msg(sock)
        assert frame["type"] != "error", frame
        if frame["type"] == "final":
            finals.append(frame["text"])
        if frame["type"] == "stopped":
            break
assert any(text.strip() for text in finals), finals
print("PASS Vinyl TCP -> Whisper final:", finals)
