"""Warm faster-whisper base (int8 CPU); real OpenAI-compatible multipart API."""
import io
import os
import threading
from contextlib import asynccontextmanager
import soundfile as sf
from fastapi import FastAPI, File, UploadFile, HTTPException
from faster_whisper import WhisperModel
from runtime.fetch_models import fetch, ROOT, LOCK

model = None
lock = threading.Lock()

@asynccontextmanager
async def lifespan(app):
    global model
    fetch()
    model = WhisperModel(str(ROOT), device="cpu", compute_type="int8", cpu_threads=2, num_workers=1)
    print("whisper ready: degraded-not-failed device=cpu compute=int8 gpu=disabled", flush=True)
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/healthz")
def healthz():
    return {"ready": model is not None, "status": "degraded", "device": "cpu",
            "reason": "gpu_disabled", "model": LOCK["repository"], "revision": LOCK["revision"]}

@app.post("/v1/audio/transcriptions")
def transcribe(file: UploadFile = File(...)):
    raw = file.file.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise HTTPException(413, "audio exceeds 16 MiB")
    try:
        audio, rate = sf.read(io.BytesIO(raw))
    except Exception:
        raise HTTPException(400, "invalid audio") from None
    if len(audio) / rate > 30:
        raise HTTPException(413, "audio exceeds 30 seconds")
    with lock:
        segments, _ = model.transcribe(io.BytesIO(raw), beam_size=1, language="en", vad_filter=False)
        text = " ".join(segment.text.strip() for segment in segments).strip()
    return {"text": text}
