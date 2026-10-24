"""Real CPU speech synthesis using eSpeak NG; implements Vox v1 engine wire API."""
import base64
import io
import subprocess
import threading
import wave
from fastapi import FastAPI
from app.engine_contract import EngineSynthesizeRequest

app = FastAPI()
lock = threading.Lock()

@app.get("/healthz")
def healthz():
    return {"engine": "espeak", "ready": True, "model_loaded": True,
            "status": "degraded", "device": "cpu", "reason": "neural_gpu_engine_disabled",
            "capabilities": {"accepts_reference_audio": False, "needs_transcript": False,
                             "output_sample_rate": 22050, "multi_speaker": False}}

@app.post("/v1/synthesize")
def synthesize(req: EngineSynthesizeRequest):
    with lock:
        result = subprocess.run(["espeak-ng", "--stdout", "-v", "en-us", "-s", "150", "--stdin"],
                                input=req.text.encode(), capture_output=True, check=True, timeout=60)
    # eSpeak streaming WAV has placeholder lengths: reframe actual frames.
    with wave.open(io.BytesIO(result.stdout)) as source:
        pcm = source.readframes(source.getnframes())
        rate = source.getframerate()
    out = io.BytesIO()
    with wave.open(out, "wb") as target:
        target.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        target.writeframes(pcm)
    raw = out.getvalue()
    return {"engine": "espeak", "wav_b64": base64.b64encode(raw).decode(),
            "sample_rate": rate, "bytes": len(raw), "duration_s": len(pcm) / 2 / rate}
