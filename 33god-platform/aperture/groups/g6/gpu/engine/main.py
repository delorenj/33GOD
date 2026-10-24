"""VoxCPM2 engine microservice — engine-container copy.

Implements the ``/v1/synthesize`` + ``/healthz`` contract defined in
``engine.contract`` so ``voxxy-core`` can route synthesis requests here via
``RemoteEngineClient``.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import soundfile as sf
import torch
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from engine.contract import (
    EngineCapabilities,
    EngineHealth,
    EngineSynthesizeRequest,
    EngineSynthesizeResponse,
)
from engine.synth import REF_AUDIO_MAX_SECONDS, Synth

logger = logging.getLogger(__name__)

_synth: Synth | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    global _synth
    if os.environ.get("GOD_GPU", "0") == "1" and torch.cuda.is_available():
        _synth = Synth()
        _synth.load()
        logger.info("voxcpm engine ready")
    else:
        logger.warning("voxcpm degraded-not-failed: GPU disabled or unavailable; synthesis UNAVAILABLE")
    yield
    logger.info("voxcpm engine shutting down")


app = FastAPI(title="vox-engine-voxcpm", version="0.1.0", lifespan=lifespan)


@app.get("/healthz", response_model=EngineHealth)
async def healthz() -> EngineHealth:
    loaded = _synth is not None and _synth._model is not None
    return EngineHealth(
        engine="voxcpm",
        status="ready" if loaded else "degraded",
        reason=None if loaded else "gpu_disabled_or_unavailable",
        ready=loaded,
        model_loaded=loaded,
        vram_used_gb=None,  # deliberately None; do not probe torch at health time
        capabilities=EngineCapabilities(
            accepts_reference_audio=True,
            needs_transcript=False,
            max_ref_seconds=REF_AUDIO_MAX_SECONDS,
            output_sample_rate=16000,
            multi_speaker=False,
        ),
    )


@app.post("/v1/synthesize", response_model=EngineSynthesizeResponse)
async def synthesize(req: EngineSynthesizeRequest) -> Any:
    if _synth is None:
        return JSONResponse(status_code=503, content={"error": {"code": "UNAVAILABLE", "message": "GPU disabled or unavailable"}})

    ref_tmp: str | None = None
    prompt_tmp: str | None = None

    try:
        # Decode reference audio to a temp WAV file if provided.
        if req.reference_audio_b64:
            ref_bytes = base64.b64decode(req.reference_audio_b64)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(ref_bytes)
                ref_tmp = f.name

        # Decode prompt audio to a temp WAV file if transcript-guided cloning.
        # VoxCPM supports prompt_wav_path + prompt_text together; if only
        # prompt_text is set without audio we skip it to avoid a Synth error.
        if req.prompt_text and req.reference_audio_b64:
            # Re-use same bytes as prompt (caller doesn't send a separate clip
            # today; the upstream orchestrator sends the reference as the prompt
            # when a transcript is available).
            prompt_bytes = base64.b64decode(req.reference_audio_b64)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(prompt_bytes)
                prompt_tmp = f.name

        wav_np, sample_rate = _synth.generate(
            text=req.text,
            reference_wav_path=ref_tmp,
            prompt_wav_path=prompt_tmp if req.prompt_text else None,
            prompt_text=req.prompt_text,
            cfg_value=req.cfg,
            inference_timesteps=req.steps,
            normalize=False,
            denoise=False,
        )

    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "INVALID_INPUT", "message": str(exc)}},
        )
    except torch.cuda.OutOfMemoryError:
        logger.exception("CUDA OOM during synthesis")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "OOM", "message": "CUDA out of memory"}},
        )
    except Exception as exc:
        logger.exception("Synthesis failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "MODEL_ERROR", "message": str(exc)}},
        )
    finally:
        # Always clean up temp files regardless of outcome.
        for tmp in (ref_tmp, prompt_tmp):
            if tmp:
                Path(tmp).unlink(missing_ok=True)

    # Encode WAV to base64.
    buf = io.BytesIO()
    sf.write(buf, wav_np, sample_rate, format="WAV", subtype="PCM_16")
    wav_bytes = buf.getvalue()
    wav_b64 = base64.b64encode(wav_bytes).decode("ascii")
    duration_s = len(wav_np) / sample_rate

    return EngineSynthesizeResponse(
        wav_b64=wav_b64,
        sample_rate=sample_rate,
        engine="voxcpm",
        duration_s=duration_s,
        bytes=len(wav_bytes),
    )
