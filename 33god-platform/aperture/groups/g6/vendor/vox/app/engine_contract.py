"""Shared wire contract for the decoupled engine topology.

Both ``voxxy-core`` (this package) and every engine container import the same
models so request/response shapes cannot silently drift. The engine
microservices vendor-copy this file into their own source tree rather than
depending on ``voxxy-core`` as a library; keep the module free of any heavy
imports so the copy stays trivial.

Versioned under ``/v1/`` on the wire. Breaking changes bump to ``/v2/`` and a
new module; do not edit these models in place.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------- /v1/synthesize ----------


class EngineSynthesizeRequest(BaseModel):
    """Body for ``POST /v1/synthesize`` on any engine.

    Reference audio travels inline as base64-encoded WAV bytes so engines can
    stay stateless (no shared volumes with core). A 3-second 16 kHz mono clip
    is ~100 KB base64-encoded, negligible against ~2 s inference time.
    """

    text: str = Field(..., min_length=1)

    reference_audio_b64: Optional[str] = Field(
        None,
        description=(
            "Reference audio as base64-encoded WAV bytes. Engines that accept "
            "a reference clip resolve this into an in-memory tensor or temp "
            "file. Engines without cloning support ignore it."
        ),
    )
    reference_sample_rate: Optional[int] = Field(
        None,
        description="Informational; engines resample as needed.",
    )

    prompt_text: Optional[str] = Field(
        None,
        description=(
            "Transcript of the reference clip. Only used by engines that "
            "support transcript-guided cloning (e.g. VoxCPM Ultimate Cloning). "
            "Ignored by audio-only engines (e.g. VibeVoice)."
        ),
    )

    voice_id: Optional[str] = Field(
        None,
        description=(
            "Engine-specific voice identifier. For ElevenLabs: the remote "
            "voice id. For VibeVoice: a speaker tag. For VoxCPM: unused."
        ),
    )

    cfg: float = Field(2.0, ge=1.0, le=5.0)
    steps: int = Field(10, ge=1, le=50)


class EngineSynthesizeResponse(BaseModel):
    """Body returned by a successful ``POST /v1/synthesize``."""

    wav_b64: str = Field(..., description="Base64-encoded WAV bytes (PCM_16).")
    sample_rate: int = Field(..., gt=0)
    engine: str = Field(
        ...,
        description="Must match ``engine.name`` in the matching ``/healthz``.",
    )
    duration_s: Optional[float] = None
    bytes: int = Field(..., ge=0, description="Length of the decoded WAV bytes.")


# ---------- error envelope ----------


class EngineErrorBody(BaseModel):
    code: str = Field(
        ...,
        description=(
            "One of INVALID_INPUT | MODEL_ERROR | OOM | TIMEOUT | UNAVAILABLE. "
            "Core's orchestrator uses this to decide fallback vs permanent."
        ),
    )
    message: str


class EngineError(BaseModel):
    """Returned for any non-2xx response from ``/v1/synthesize``."""

    error: EngineErrorBody


# ---------- /healthz ----------


class EngineCapabilities(BaseModel):
    """What an engine can and cannot do.

    Core uses this to skip engines that cannot serve a given request before
    incurring a network round-trip (e.g. a voice has no reference suitable for
    this engine's cloning mode).
    """

    accepts_reference_audio: bool = True
    needs_transcript: bool = False
    max_ref_seconds: Optional[float] = None
    output_sample_rate: int = Field(..., gt=0)
    multi_speaker: bool = False


class EngineHealth(BaseModel):
    """Body returned by ``GET /healthz`` on any engine."""

    engine: str
    ready: bool
    model_loaded: bool
    vram_used_gb: Optional[float] = None
    capabilities: EngineCapabilities


__all__ = [
    "EngineSynthesizeRequest",
    "EngineSynthesizeResponse",
    "EngineError",
    "EngineErrorBody",
    "EngineHealth",
    "EngineCapabilities",
]
