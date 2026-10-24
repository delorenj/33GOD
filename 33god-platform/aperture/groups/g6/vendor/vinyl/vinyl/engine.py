"""G6 adaptation: Vinyl Recognizer interface delegates to one warm Whisper CPU API.
Upstream server, framing, VAD, queues and traces are unchanged. No second model.
"""
import io
import os
from pathlib import Path
import numpy as np
import httpx
import soundfile as sf

SAMPLE_RATE = 16000
DEFAULT_MODEL_DIR = Path("/models")

def is_sparse(text, duration_s):
    return not text

class Recognizer:
    def __init__(self, model_dir=DEFAULT_MODEL_DIR):
        self.url = os.environ.get("GOD_WHISPER_URL", "http://whisper:8766")
        self.trace_config = {"backend": "warm-whisper-http", "device": "cpu"}
        response = httpx.get(self.url + "/healthz", timeout=10)
        response.raise_for_status()
        if not response.json()["ready"]:
            raise RuntimeError("whisper is not ready")

    def decode(self, samples, *, preroll=None, trace=None, **context):
        if preroll is not None and len(preroll):
            samples = np.concatenate([preroll, samples])
        buf = io.BytesIO()
        sf.write(buf, samples, SAMPLE_RATE, format="WAV", subtype="PCM_16")
        response = httpx.post(self.url + "/v1/audio/transcriptions",
                              files={"file": ("segment.wav", buf.getvalue(), "audio/wav")}, timeout=90)
        response.raise_for_status()
        return response.json()["text"]
