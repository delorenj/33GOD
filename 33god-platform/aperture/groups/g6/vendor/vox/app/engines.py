"""Synthesis engines with a pluggable interface and fallback orchestration.

Engines are pluggable. Today the shipped set is:

- ``RemoteEngineClient``: HTTP/JSON client that speaks the ``/v1/synthesize``
  contract defined in :mod:`app.engine_contract`. One instance per entry in
  ``VOX_ENGINES`` (``name=url,name=url``). The local VoxCPM2 engine now runs
  as a sidecar container and is accessed via ``RemoteEngineClient``; there is
  no longer an in-process model loader in this package.
- ``ElevenLabsEngine``: remote ElevenLabs TTS. Stays in-core because it's
  already a remote call; wrapping it in another container would add a hop for
  nothing. Terminal fallback when all remote engines fail.

:class:`EngineOrchestrator` tries engines in order; first success wins. The
request shape is the same for every engine so a new one is just another
implementation of :class:`SynthEngine`.
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import time
from dataclasses import dataclass
from typing import Callable, Optional, Protocol

import httpx
import soundfile as sf

from app.engine_contract import (
    EngineHealth,
    EngineSynthesizeRequest,
    EngineSynthesizeResponse,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SynthResult:
    wav_bytes: bytes
    sample_rate: int
    engine: str  # identifies which engine served, e.g. "voxcpm" or "elevenlabs"


class SynthEngine(Protocol):
    """Contract every synthesis engine implements.

    ``name`` surfaces in telemetry and in the ``engine`` field of the tool
    response so callers can detect when a fallback engaged. ``available()`` is
    a cheap pre-flight to skip engines that can't possibly serve (e.g. no API
    key). ``generate`` is the actual work and must raise on failure so the
    orchestrator can try the next engine.
    """

    name: str

    def available(self) -> bool: ...

    async def generate(
        self,
        *,
        text: str,
        reference_wav_path: Optional[str] = None,
        prompt_text: Optional[str] = None,
        voice_id: Optional[str] = None,
        cfg: float = 2.0,
        steps: int = 10,
    ) -> SynthResult: ...


# ElevenLabs "eleven_turbo_v2_5" is the current cheap+fast model. PCM output
# gives us a WAV we can hand to the same transcoder pipeline as VoxCPM output.
# Changing the output_format to mp3 would save bandwidth at the cost of an
# extra transcode hop.
ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"
ELEVENLABS_MODEL_ID = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")
ELEVENLABS_OUTPUT_FORMAT = os.environ.get(
    "ELEVENLABS_OUTPUT_FORMAT", "pcm_24000"
)  # pcm_24000 returns raw 16-bit PCM at 24kHz; we wrap it in WAV framing


class ElevenLabsEngine:
    """Remote ElevenLabs TTS. Activates when ELEVENLABS_API_KEY is set.

    Returns WAV bytes so the downstream transcoder doesn't need a special
    case. When ``voice_id`` is not passed, falls back to
    ``ELEVENLABS_DEFAULT_VOICE`` env var (Adam by default).
    """

    name = "elevenlabs"

    def __init__(self) -> None:
        self._api_key = os.environ.get("ELEVENLABS_API_KEY")
        self._default_voice = os.environ.get(
            "ELEVENLABS_DEFAULT_VOICE", "pNInz6obpgDQGcFmaJgB"
        )  # "Adam"
        self._timeout = float(os.environ.get("ELEVENLABS_TIMEOUT_SECONDS", "20"))

    def available(self) -> bool:
        return bool(self._api_key)

    async def generate(
        self,
        *,
        text: str,
        reference_wav_path: Optional[str] = None,
        prompt_text: Optional[str] = None,
        voice_id: Optional[str] = None,
        cfg: float = 2.0,
        steps: int = 10,
    ) -> SynthResult:
        if not self.available():
            raise RuntimeError("ELEVENLABS_API_KEY not set")

        vid = voice_id or self._default_voice
        url = f"{ELEVENLABS_API_BASE}/text-to-speech/{vid}"
        params = {"output_format": ELEVENLABS_OUTPUT_FORMAT}
        headers = {
            "xi-api-key": self._api_key,
            "accept": "audio/wav",
            "content-type": "application/json",
        }
        payload = {"text": text, "model_id": ELEVENLABS_MODEL_ID}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, params=params, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"elevenlabs {resp.status_code}: {resp.text[:200]}"
                )
            audio = resp.content

        # pcm_24000 is raw PCM without headers; wrap in WAV container so the
        # transcoder stays format-agnostic. Other output_formats (mp3_*) return
        # already-framed bytes and bypass this wrapping.
        if ELEVENLABS_OUTPUT_FORMAT.startswith("pcm_"):
            sr = int(ELEVENLABS_OUTPUT_FORMAT.split("_")[1])
            import numpy as np
            pcm = np.frombuffer(audio, dtype=np.int16)
            buf = io.BytesIO()
            sf.write(buf, pcm, sr, format="WAV", subtype="PCM_16")
            audio = buf.getvalue()
            return SynthResult(wav_bytes=audio, sample_rate=sr, engine=self.name)

        # Non-PCM paths: bytes are already a container; let the transcoder
        # probe. sample_rate is best-effort informational only.
        return SynthResult(wav_bytes=audio, sample_rate=0, engine=self.name)


class PermanentEngineError(RuntimeError):
    """Engine returned a 4xx. Do not fall through to the next engine.

    4xx means the request itself is wrong (bad text, missing voice, malformed
    reference). Retrying on a different engine would just produce the same
    failure, and might mask the real issue. Surface it to the caller.
    """


class RemoteEngineClient:
    """SynthEngine that speaks to a container over HTTP/JSON.

    Matches the ``/v1/synthesize`` + ``/healthz`` contract in
    :mod:`app.engine_contract`. One instance per configured remote engine;
    core reads ``VOX_ENGINES`` (``name=url,name=url``) at startup and builds
    one ``RemoteEngineClient`` per entry.

    Health is cached for ``_HEALTH_TTL_SECONDS`` so ``available()`` doesn't hit
    the wire on every orchestrator pass; orchestrator loops happen on every
    synth request, and a 100ms health probe per request per engine adds up.
    """

    _HEALTH_TTL_SECONDS = 10.0

    def __init__(
        self,
        name: str,
        base_url: str,
        *,
        timeout: float | None = None,
        health_timeout: float = 2.0,
    ) -> None:
        if timeout is None:
            # Local GPU engines can take minutes on a long utterance when the
            # card is shared; a short cap silently falls through to ElevenLabs.
            timeout = float(os.environ.get("VOX_ENGINE_TIMEOUT_SECONDS", "240"))
        self.name = name
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._health_timeout = health_timeout
        # Cached (timestamp, ready) pair. None forces a probe on first call.
        self._health_cache: Optional[tuple[float, bool]] = None
        self._health_lock = asyncio.Lock()

    # --- health ---

    async def _probe_health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._health_timeout) as client:
                resp = await client.get(f"{self._base_url}/healthz")
            if resp.status_code != 200:
                logger.warning(
                    "engine %s healthz %d: %s", self.name,
                    resp.status_code, resp.text[:200],
                )
                return False
            parsed = EngineHealth.model_validate(resp.json())
            if parsed.engine != self.name:
                # Not fatal, but worth flagging: config mismatch means a rename
                # somewhere. Keep serving if ``ready`` is true.
                logger.warning(
                    "engine %s name mismatch: remote reports %r",
                    self.name, parsed.engine,
                )
            return bool(parsed.ready and parsed.model_loaded)
        except Exception as exc:  # noqa: BLE001
            logger.warning("engine %s healthz failed: %r", self.name, exc)
            return False

    def available(self) -> bool:
        """Non-async per Protocol; reads the cached health value.

        First call returns True optimistically so the first synth attempt
        triggers a real probe via ``generate()``. Subsequent calls reflect the
        last observed health within the TTL window.
        """
        if self._health_cache is None:
            return True
        ts, ok = self._health_cache
        if time.monotonic() - ts > self._HEALTH_TTL_SECONDS:
            return True  # let the next generate() refresh the cache
        return ok

    async def refresh_health(self) -> bool:
        """Explicit async probe. Useful for /healthz aggregation in core."""
        async with self._health_lock:
            ok = await self._probe_health()
            self._health_cache = (time.monotonic(), ok)
            return ok

    # --- generate ---

    async def generate(
        self,
        *,
        text: str,
        reference_wav_path: Optional[str] = None,
        prompt_text: Optional[str] = None,
        voice_id: Optional[str] = None,
        cfg: float = 2.0,
        steps: int = 10,
    ) -> SynthResult:
        ref_b64: Optional[str] = None
        ref_sr: Optional[int] = None
        if reference_wav_path:
            # Read raw bytes, don't decode/re-encode. Engines know how to handle
            # WAV framing; keeping bytes intact preserves whatever bit depth
            # and channel layout the caller chose.
            with open(reference_wav_path, "rb") as fh:
                ref_bytes = fh.read()
            ref_b64 = base64.b64encode(ref_bytes).decode("ascii")
            try:
                ref_sr = int(sf.info(reference_wav_path).samplerate)
            except Exception:
                ref_sr = None

        payload = EngineSynthesizeRequest(
            text=text,
            reference_audio_b64=ref_b64,
            reference_sample_rate=ref_sr,
            prompt_text=prompt_text,
            voice_id=voice_id,
            cfg=cfg,
            steps=steps,
        )

        url = f"{self._base_url}/v1/synthesize"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(url, json=payload.model_dump())
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            self._health_cache = (time.monotonic(), False)
            raise RuntimeError(
                f"engine {self.name} transport error: {exc!r}"
            ) from exc

        if resp.status_code == 200:
            body = EngineSynthesizeResponse.model_validate(resp.json())
            wav = base64.b64decode(body.wav_b64)
            # Mark healthy on success so subsequent available() checks stay cheap.
            self._health_cache = (time.monotonic(), True)
            return SynthResult(
                wav_bytes=wav, sample_rate=body.sample_rate, engine=self.name,
            )

        # Non-2xx. Distinguish between "try the next engine" and "stop here".
        body_text = resp.text[:500]
        if 400 <= resp.status_code < 500:
            # Bad input; next engine will hit the same error. Surface it.
            raise PermanentEngineError(
                f"engine {self.name} {resp.status_code}: {body_text}"
            )
        # 5xx: transient on this engine. Mark unhealthy, fall through.
        self._health_cache = (time.monotonic(), False)
        raise RuntimeError(
            f"engine {self.name} {resp.status_code}: {body_text}"
        )


class EngineOrchestrator:
    """Try engines in order. First success wins; log every fallback."""

    def __init__(self, engines: list[SynthEngine]) -> None:
        self._engines = engines

    async def generate(
        self,
        *,
        text: str,
        reference_wav_path: Optional[str] = None,
        reference_resolver: Optional[Callable[[str], Optional[str]]] = None,
        prompt_text: Optional[str] = None,
        voice_id: Optional[str] = None,
        cfg: float = 2.0,
        steps: int = 10,
        preferred: Optional[list[str]] = None,
    ) -> SynthResult:
        """Run the engine chain; first success wins.

        Args:
            reference_wav_path: Legacy / no-voice-profile path. Used when
                ``reference_resolver`` is not supplied.
            reference_resolver: Per-engine callable ``(engine_name) -> path``.
                When provided, it takes precedence over ``reference_wav_path``
                and lets each engine use a different reference clip (e.g. a
                de-noised version for VibeVoice).
            preferred: Optional engine names to try before the rest of the
                chain. A voice whose clone lives on a specific engine (e.g. a
                VibeVoice reference) should be served by that engine first.
                Stable sort preserves configured order within each group, so
                fallback order still follows ``VOX_ENGINES``.
        """
        text_len = len(text)
        last_exc: Optional[BaseException] = None
        tried: list[str] = []  # engines attempted before the winner (for fallback tracking)
        engines = self._engines
        if preferred:
            engines = sorted(engines, key=lambda e: 0 if e.name in preferred else 1)
        for engine in engines:
            if not engine.available():
                logger.info("engine %s skipped (unavailable)", engine.name)
                continue
            effective_ref = (
                reference_resolver(engine.name)
                if reference_resolver is not None
                else reference_wav_path
            )
            try:
                result = await engine.generate(
                    text=text,
                    reference_wav_path=effective_ref,
                    prompt_text=prompt_text,
                    voice_id=voice_id,
                    cfg=cfg,
                    steps=steps,
                )
                logger.info("engine %s served (%d bytes)", engine.name, len(result.wav_bytes))
                fallback_from = ",".join(tried)
                logger.info(
                    "synth.completed engine=%s text_len=%d bytes=%d sample_rate=%d fallback_from=%s",
                    engine.name, text_len, len(result.wav_bytes), result.sample_rate, fallback_from,
                )
                return result
            except PermanentEngineError:
                # 4xx from a remote engine: propagate, don't try the next.
                # Retrying would just reproduce the same validation error.
                raise
            except Exception as exc:  # noqa: BLE001 - deliberately broad
                last_exc = exc
                # repr() because many torch/voxcpm exceptions have empty str().
                # Keep a traceback for diagnostic logs; stays on the WARNING
                # level so it's filterable.
                logger.warning(
                    "engine %s failed: %r", engine.name, exc, exc_info=True,
                )
                tried.append(engine.name)
                continue
        # All engines failed. Raise the last error for the caller to translate.
        logger.warning(
            "synth.failed tried=%s last_error=%r text_len=%d",
            ",".join(tried), last_exc, text_len,
        )
        raise RuntimeError(
            f"all synthesis engines failed; last error: {last_exc!r}"
        )
