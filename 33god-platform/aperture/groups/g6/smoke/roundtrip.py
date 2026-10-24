"""Runs inside audio-intake; exercises real in-network APIs, no host ports."""
import hashlib
import io
import json
import os
from pathlib import Path
import time
import wave
import httpx

client = httpx.Client(timeout=120)
key = os.environ.get("GOD_VOX_API_KEY", "")
headers = {"X-API-Key": key} if key else {}
if key:
    unauthorized = client.post("http://vox:8000/synthesize", json={"text": "unauthorized"})
    assert unauthorized.status_code == 401, unauthorized.status_code
    print("PASS Vox missing authentication rejected 401")
health = client.get("http://espeak:8000/healthz").json()
assert health["ready"] and health["status"] == "degraded" and health["device"] == "cpu", health
stt_health = client.get("http://whisper:8766/healthz").json()
assert stt_health["ready"] and stt_health["device"] == "cpu" and stt_health["status"] == "degraded", stt_health
print("PASS GPU boundary", health, stt_health)
r = client.post("http://vox:8000/synthesize", json={"text": "The voice pipeline is working."}, headers=headers)
r.raise_for_status()
assert r.headers["content-type"].startswith("audio/wav") and r.content[:4] == b"RIFF", r.headers
with wave.open(io.BytesIO(r.content)) as audio:
    duration = audio.getnframes() / audio.getframerate()
assert 0 < duration <= 5, duration
print("PASS TTS /synthesize", len(r.content), "WAV bytes", round(duration, 2), "seconds", r.headers.get("x-vox-engine"))
# Test both freshly synthesized speech and the shipped short speech fixture.
for name, raw in [("roundtrip", r.content), ("bundled", Path("/app/smoke/speech.wav").read_bytes())]:
    response = client.post("http://whisper:8766/v1/audio/transcriptions",
                           files={"file": ("speech.wav", raw, "audio/wav")})
    response.raise_for_status()
    transcript = response.json()["text"]
    assert isinstance(transcript, str) and len(transcript.strip()) > 0, transcript
    print("PASS STT", name, "returns a transcript without error:", repr(transcript))
for url, kwargs, code in [
    ("http://vox:8000/synthesize", {"json": {"text": ""}, "headers": headers}, 422),
    ("http://whisper:8766/v1/audio/transcriptions", {"files": {"file": ("bad.wav", b"not audio", "audio/wav")}}, 400),
]:
    response = client.post(url, **kwargs)
    assert response.status_code == code, (response.status_code, response.text)
    print("PASS rejection", code)
# Local intake poller must atomically land identical bytes + durable local receipt.
raw = r.content
digest = hashlib.sha256(raw).hexdigest()
dest = Path("/pipeline/inbox/smoke.wav")
temp = dest.with_suffix(".partial")
temp.write_bytes(raw)
temp.replace(dest)
receipt = Path("/pipeline/receipts") / (digest + ".json")
for _ in range(60):
    if receipt.exists() and not dest.exists():
        break
    time.sleep(0.5)
else:
    raise AssertionError("intake pickup timed out")
assert (Path("/pipeline/input") / (digest + ".wav")).read_bytes() == raw
assert json.loads(receipt.read_text())["sha256"] == digest
print("PASS intake pickup SHA256", digest, "receipt", json.loads(receipt.read_text()))
# Invalid input must quarantine without killing the scan loop.
Path("/pipeline/inbox/bad.wav").write_bytes(b"invalid")
for _ in range(30):
    if Path("/pipeline/inbox/bad.rejected").exists():
        break
    time.sleep(0.5)
else:
    raise AssertionError("invalid intake did not quarantine")
assert client.get("http://audio-intake:8000/healthz").json()["ready"]
print("PASS invalid intake quarantined; poller remains ready")
