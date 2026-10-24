"""vox-tts: universal TTS service.

- HTTP API: POST /synthesize → audio/wav  (engine chain, returns winning bytes)
- HTTP API: POST /synthesize-url → JSON   (engine fallback + URL return)
- Audio cache: GET /audio/{id}.ogg        (Telegram-ready OGG/Opus)
- Sink relay: /sink/{key}/...             (play on the human's machine, not the caller's)
- MCP at /mcp/ (streamable HTTP) for Hermes/OpenClaw/Claude Code
- Voice profile CRUD at /voices
- Health check at /healthz

Environment:
  VOX_DATABASE_URL     postgres DSN (required)
  VOX_VOICES_DIR       directory holding voice WAVs (default: /data/voices)
  VOX_AUDIO_CACHE_DIR  directory for cached OGG blobs (default: /data/audio-cache)
  VOX_AUDIO_TTL_SECONDS  cache lifetime (default: 3600)
  VOX_ENGINES          comma-separated name=url pairs for remote engine sidecars
  VOX_API_KEY          optional shared key protecting HTTP/MCP data-plane routes
  VOX_DEFAULT_SINK     default sink name for the speak_sink MCP tool (optional)
  VOX_REF_AUDIO_MAX_SECONDS  max reference audio length (default 30)
  ELEVENLABS_API_KEY   enables the ElevenLabs fallback engine (optional)
  ELEVENLABS_DEFAULT_VOICE  default ElevenLabs voice id (default: Adam)
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable, Optional

import soundfile as sf
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from app import audio as audio_codec
from app.auth import ApiKeyAuthMiddleware
from app import cache as audio_cache
from app import sink as sink_relay
from app.engines import ElevenLabsEngine, EngineOrchestrator, PermanentEngineError, RemoteEngineClient, SynthResult
from app.voices import PERSONA_NONE, PERSONA_RE, VOICES_DIR, Voice, VoiceRepo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("vox")

REF_AUDIO_MAX_SECONDS = float(os.environ.get("VOX_REF_AUDIO_MAX_SECONDS", "30"))

# ---------- globals populated in lifespan ----------
_repo: VoiceRepo | None = None
_engine: EngineOrchestrator | None = None
_sweep_task: asyncio.Task | None = None

# Sink listeners are plain in-process state, not a lifespan resource: a sink is
# a live attention channel, so there is nothing to open at boot and nothing
# worth persisting across a restart (see app/sink.py).
_sinks = sink_relay.SinkRegistry()


# ---------- engine chain builder ----------

def _build_engine_chain() -> list:
    """Parse VOX_ENGINES env (format 'name=url,name=url'), append ElevenLabs.

    ElevenLabsEngine.available() self-disables without ELEVENLABS_API_KEY so
    appending it unconditionally is safe and keeps the registry env-only.
    """
    spec = os.environ.get("VOX_ENGINES", "").strip()
    remotes: list = []
    for entry in spec.split(","):
        entry = entry.strip()
        if not entry or "=" not in entry:
            continue
        name, url = entry.split("=", 1)
        remotes.append(RemoteEngineClient(name.strip(), url.strip()))
    return remotes + [ElevenLabsEngine()]


# ---------- API models ----------

class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to synthesize")
    voice: Optional[str] = Field(
        None,
        description="Name of a saved voice profile. Omit for voice-design mode.",
    )
    cfg: float = Field(2.0, ge=1.0, le=5.0)
    steps: int = Field(10, ge=1, le=50)
    normalize: bool = False
    denoise: bool = False


class SynthesizeUrlResponse(BaseModel):
    """Response shape shared by POST /synthesize-url and the speak_url MCP tool.

    Clients that deliver audio elsewhere (Telegram sendVoice, browser <audio>,
    Home Assistant media_player) can pass ``audio_url`` directly to those
    surfaces. The third party fetches the OGG/Opus payload from us.
    """
    audio_url: str
    engine: str
    duration_s: Optional[float] = None
    bytes: int
    format: str = "ogg_opus"


class SinkPlayRequest(BaseModel):
    """Envelope pushed to a sink's listeners.

    ``audio_url`` is the only required field because the listener fetches the
    bytes itself from the public audio cache; everything else is metadata the
    listener may log or display.
    """

    audio_url: str = Field(..., description="Fetchable audio URL for the listener to play")
    text: Optional[str] = Field(None, description="What was said, for the listener's log")
    voice: Optional[str] = None
    engine: Optional[str] = None
    duration_s: Optional[float] = None
    format: str = "ogg_opus"


class SinkPlayResponse(BaseModel):
    """Result of a publish. ``delivered == 0`` means nobody was listening.

    Callers use this to decide whether to fall back to playing locally, which is
    why an unlistened sink is a 200 with a zero count rather than an error: not
    reaching a sink is an expected, recoverable outcome.
    """

    key: str
    delivered: int
    audio_url: Optional[str] = None


class SinkStatus(BaseModel):
    key: str
    listeners: int


class VoiceOut(BaseModel):
    name: str
    display_name: str
    duration_s: float
    prompt_text: Optional[str] = None
    tags: list[str] = []
    elevenlabs_voice_id: Optional[str] = None
    vibevoice_ref_path: Optional[str] = None
    vibevoice_speaker_tag: Optional[str] = None
    persona: Optional[str] = None

    @classmethod
    def from_model(cls, v: Voice) -> "VoiceOut":
        return cls(
            name=v.name,
            display_name=v.display_name,
            duration_s=v.duration_s,
            prompt_text=v.prompt_text,
            tags=v.tags,
            elevenlabs_voice_id=v.elevenlabs_voice_id,
            vibevoice_ref_path=v.vibevoice_ref_path,
            vibevoice_speaker_tag=v.vibevoice_speaker_tag,
            persona=v.persona,
        )


class VoicePersonaIn(BaseModel):
    # A persona slug, "none" (explicitly no persona) or null (clear the association).
    persona: Optional[str] = None


# ---------- synthesis helpers ----------

async def _resolve_voice(voice_name: Optional[str]) -> tuple[
    Optional[Callable[[str], Optional[str]]], Optional[str], Optional[str],
    Optional[list[str]],
]:
    """Resolve ``voice_name`` into (reference_resolver, prompt_text, elevenlabs_voice_id, preferred_engines).

    ``reference_resolver`` is a callable ``(engine_name) -> wav_path`` so each
    engine can be pointed at a different reference clip (e.g. a de-noised
    version for VibeVoice) without plumbing engine identity through the whole
    call stack. Falls back to ``v.abs_path`` when the engine-specific file
    doesn't exist.

    ``preferred_engines`` names the engine a cloned voice should be served by
    first (currently: VibeVoice when the profile carries a vibevoice
    reference). None means configured chain order.

    Returns ``(None, None, None, None)`` for voice-design mode (no voice_name).
    """
    if not voice_name:
        return None, None, None, None
    assert _repo is not None
    v = await _repo.get(voice_name)
    if v is None:
        raise HTTPException(404, f"voice '{voice_name}' not found")
    if not v.abs_path.exists():
        raise HTTPException(500, f"voice file missing on disk: {v.abs_path}")

    def resolver(engine: str) -> Optional[str]:
        p = v.ref_path_for(engine)
        return str(p) if p.exists() else str(v.abs_path)

    preferred = ["vibevoice"] if v.vibevoice_ref_path else None
    return resolver, v.prompt_text, v.elevenlabs_voice_id, preferred


async def _synthesize_wav(
    *,
    text: str,
    voice_name: Optional[str],
    cfg: float,
    steps: int,
) -> SynthResult:
    assert _engine is not None
    resolver, prompt_text, eleven_voice_id, preferred = await _resolve_voice(voice_name)
    return await _engine.generate(
        text=text,
        reference_resolver=resolver,
        prompt_text=prompt_text,
        voice_id=eleven_voice_id,
        cfg=cfg,
        steps=steps,
        preferred=preferred,
    )


def _duration_from_wav(wav_bytes: bytes) -> Optional[float]:
    try:
        info = sf.info(io.BytesIO(wav_bytes))
        return float(info.duration)
    except Exception:
        return None


async def _synthesize_and_cache(
    *, text: str, voice_name: Optional[str], cfg: float, steps: int,
    request: Optional[Request] = None,
) -> SynthesizeUrlResponse:
    """Run the fallback chain, transcode to OGG/Opus, cache, return a URL."""
    result = await _synthesize_wav(
        text=text, voice_name=voice_name, cfg=cfg, steps=steps,
    )
    # Transcode off the event loop; ffmpeg blocks.
    ogg_bytes = await asyncio.to_thread(
        audio_codec.to_ogg_opus, result.wav_bytes, input_format="wav",
    )
    cache_id = audio_cache.put(ogg_bytes)
    duration = _duration_from_wav(result.wav_bytes)

    public_base = os.environ.get("VOX_PUBLIC_BASE_URL")
    if public_base:
        audio_url = f"{public_base.rstrip('/')}/audio/{cache_id}.ogg"
    elif request is not None:
        audio_url = str(request.url_for("get_audio", cache_id=cache_id))
    else:
        # MCP callers go through here. Fall back to the well-known public URL.
        audio_url = f"http://vox:8000/audio/{cache_id}.ogg"

    return SynthesizeUrlResponse(
        audio_url=audio_url,
        engine=result.engine,
        duration_s=duration,
        bytes=len(ogg_bytes),
    )


# ---------- FastMCP (defined first so we can nest its lifespan) ----------

mcp = FastMCP(name="vox", instructions=(
    "Text-to-speech tools backed by VoxCPM2 with ElevenLabs fallback. "
    "Use `speak_url` when the audio will be consumed by another service "
    "(Telegram sendVoice, browser, Home Assistant) — returns a fetchable "
    "OGG/Opus URL. Use `speak` only when you need the raw bytes inline. "
    "Use `list_voices_tool` to discover saved voice profiles."
))
mcp_app = mcp.http_app(path="/")  # mount at root of the sub-app so /mcp hits it


# ---------- lifespan (wraps MCP lifespan so its task group boots) ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _repo, _engine, _sweep_task
    dsn = os.environ["VOX_DATABASE_URL"]
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    audio_cache.ensure_dir()

    _repo = await VoiceRepo.connect(dsn)
    _engine = EngineOrchestrator(_build_engine_chain())

    _sweep_task = asyncio.create_task(audio_cache.sweep_loop())

    logger.info(
        "vox-tts core ready: voices_dir=%s audio_cache=%s ref_cap=%.0fs engines=%s",
        VOICES_DIR, audio_cache.AUDIO_CACHE_DIR, REF_AUDIO_MAX_SECONDS,
        [e.name for e in _engine._engines],
    )
    try:
        async with mcp_app.lifespan(app):
            yield
    finally:
        if _sweep_task:
            _sweep_task.cancel()
        await _repo.close()


# ---------- FastAPI ----------

app = FastAPI(title="vox-tts", version="0.2.0", lifespan=lifespan)
app.add_middleware(ApiKeyAuthMiddleware)


@app.get("/healthz")
async def healthz():
    assert _engine is not None
    engines = []
    for e in _engine._engines:
        ready = e.available()
        # For RemoteEngineClient, trigger an actual probe so stale cache
        # doesn't lie. ElevenLabsEngine.available() is instant.
        if hasattr(e, "refresh_health"):
            try:
                ready = await e.refresh_health()
            except Exception:
                ready = False
        engines.append({"name": e.name, "ready": ready})
    overall = any(e["ready"] for e in engines)
    return {"status": "ok" if overall else "degraded", "engines": engines}


# ---------- client installer ----------
#
# The service hosts its own CLI distribution so new workstations can bootstrap
# with one line: `curl -fsSL http://vox:8000/install.sh | sh`. Single source
# of truth (scripts/vox-speak in the repo), TLS-fronted via Traefik, no separate
# hosting. `__BASE__` is substituted at request time so the installer pulls from
# whatever origin served it (handy for local dev + prod on the same template).

_SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "vox-speak"

_INSTALLER_TEMPLATE = """#!/bin/sh
# vox-speak bootstrap installer. Served by __BASE__.
set -eu

DEST="${VOX_INSTALL_DIR:-$HOME/.local/bin}"
SRC="${VOX_BOOTSTRAP_URL:-__BASE__/bin/vox-speak}"

mkdir -p "$DEST"
# Download to .tmp then rename so a partial write never becomes executable.
curl -fsSL "$SRC" -o "$DEST/vox-speak.tmp"
chmod +x "$DEST/vox-speak.tmp"
mv "$DEST/vox-speak.tmp" "$DEST/vox-speak"

echo "installed: $DEST/vox-speak"

case ":$PATH:" in
  *":$DEST:"*)
    echo "on PATH; try: vox-speak 'hello world'"
    ;;
  *)
    echo "warning: $DEST is not on PATH"
    echo "add this to ~/.zshenv (not ~/.zshrc; non-interactive SSH skips .zshrc):"
    echo "  path=(~/.local/bin \\$path)"
    ;;
esac
"""


@app.get("/bin/vox-speak")
async def bin_vox_speak() -> FileResponse:
    """Serve the raw vox-speak shell script."""
    if not _SCRIPT_PATH.is_file():
        raise HTTPException(404, "vox-speak script not bundled in this image")
    return FileResponse(_SCRIPT_PATH, media_type="text/x-shellscript")


@app.get("/install.sh")
async def install_sh(request: Request) -> Response:
    """Bootstrap installer: `curl -fsSL .../install.sh | sh`."""
    # Traefik terminates TLS upstream, so request.url.scheme is always "http"
    # inside the container. Honour X-Forwarded-Proto/Host so the installer
    # advertises the client-facing URL (http://vox:8000) rather than the
    # internal one.
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.url.netloc
    base = f"{proto}://{host}"
    body = _INSTALLER_TEMPLATE.replace("__BASE__", base)
    return Response(content=body, media_type="text/x-shellscript")


@app.post("/synthesize", responses={200: {"content": {"audio/wav": {}}}})
async def synthesize(req: SynthesizeRequest) -> Response:
    """Raw WAV synthesis. Runs the engine chain, returns the winning engine's bytes."""
    assert _engine is not None and _repo is not None
    try:
        result = await _synthesize_wav(
            text=req.text, voice_name=req.voice, cfg=req.cfg, steps=req.steps,
        )
    except PermanentEngineError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        logger.exception("synthesize failed")
        raise HTTPException(500, f"synthesis failed: {exc}") from exc
    return Response(
        content=result.wav_bytes,
        media_type="audio/wav",
        headers={"X-Vox-Engine": result.engine},
    )


@app.post("/synthesize-url", response_model=SynthesizeUrlResponse)
async def synthesize_url(req: SynthesizeRequest, request: Request, response: Response) -> SynthesizeUrlResponse:
    """Synthesize with engine fallback, transcode to OGG/Opus, return a URL.

    Consumers like Telegram's sendVoice fetch the URL directly from our
    /audio/<id>.ogg route. The cache entry expires per ``VOX_AUDIO_TTL_SECONDS``.
    """
    try:
        resp = await _synthesize_and_cache(
            text=req.text, voice_name=req.voice, cfg=req.cfg, steps=req.steps,
            request=request,
        )
    except PermanentEngineError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("synthesize_url failed")
        raise HTTPException(500, f"synthesis failed: {exc}") from exc
    response.headers["X-Vox-Engine"] = resp.engine
    return resp


@app.get("/audio/{cache_id}.ogg", name="get_audio")
async def get_audio(cache_id: str) -> FileResponse:
    """Serve a cached OGG/Opus blob. Called by Telegram when sendVoice fires."""
    path = audio_cache.path_for(cache_id)
    if path is None:
        raise HTTPException(404, "audio expired or not found")
    # inline so Telegram's probe works; Cache-Control to keep CDN honest
    return FileResponse(
        path,
        media_type="audio/ogg",
        headers={"Cache-Control": "public, max-age=600"},
    )


# ---------- sink relay ----------

def _validated_key(key: str) -> str:
    """Validate a sink key, translating the domain error into a 422."""
    try:
        return sink_relay.validate_key(key)
    except sink_relay.SinkKeyError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/sink/{key}", response_model=SinkStatus)
async def sink_status(key: str) -> SinkStatus:
    """Report how many listeners a sink currently has.

    Cheap enough to probe before every synthesis, which is the point: the caller
    checks this first so it can synthesize down the *right* path -- WAV inline
    for local playback, or OGG-to-cache when a sink will fetch it -- instead of
    synthesizing twice when it guesses wrong.
    """
    return SinkStatus(key=_validated_key(key), listeners=_sinks.listener_count(key))


@app.post("/sink/{key}/play", response_model=SinkPlayResponse)
async def sink_play(key: str, req: SinkPlayRequest) -> SinkPlayResponse:
    """Push an already-synthesized audio URL to a sink's listeners.

    Deliberately thin so anything that can POST JSON -- Node-RED, n8n, a shell
    script, an agent -- can reach the human's speakers without going through the
    CLI.
    """
    _validated_key(key)
    delivered = _sinks.publish(key, req.model_dump())
    return SinkPlayResponse(key=key, delivered=delivered, audio_url=req.audio_url)


@app.post("/sink/{key}/say", response_model=SinkPlayResponse)
async def sink_say(key: str, req: SynthesizeRequest, request: Request) -> SinkPlayResponse:
    """Synthesize and push to a sink in one call.

    The one-liner form for fleet callers:
    ``curl -X POST $VOX/sink/workstation/say -d '{"text":"build done"}'``.
    Synthesis runs even when nobody is listening so the response still carries a
    usable ``audio_url`` -- the caller can fall back to playing it itself.
    """
    _validated_key(key)
    try:
        resp = await _synthesize_and_cache(
            text=req.text, voice_name=req.voice, cfg=req.cfg, steps=req.steps,
            request=request,
        )
    except PermanentEngineError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("sink_say failed")
        raise HTTPException(500, f"synthesis failed: {exc}") from exc

    delivered = _sinks.publish(key, {
        "audio_url": resp.audio_url,
        "text": req.text,
        "voice": req.voice,
        "engine": resp.engine,
        "duration_s": resp.duration_s,
        "format": resp.format,
    })
    return SinkPlayResponse(key=key, delivered=delivered, audio_url=resp.audio_url)


@app.get("/sink/{key}/events")
async def sink_events(key: str) -> StreamingResponse:
    """Subscribe to a sink as an SSE stream. Held open until the client leaves.

    The listener is registered for the life of the stream and torn down when the
    generator is closed, which Starlette does on client disconnect.
    """
    _validated_key(key)

    async def stream():
        try:
            async with _sinks.subscribe(key) as queue:
                async for frame in sink_relay.event_stream(_sinks, key, queue):
                    yield frame
        except sink_relay.SinkCapacityError as exc:
            yield sink_relay.sse_frame("error", {"message": str(exc)})
        except asyncio.CancelledError:  # normal client disconnect
            raise

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers=sink_relay.SSE_HEADERS,
    )


@app.get("/voices", response_model=list[VoiceOut])
async def list_voices() -> list[VoiceOut]:
    assert _repo is not None
    return [VoiceOut.from_model(v) for v in await _repo.list()]


@app.get("/voices/{name}", response_model=VoiceOut)
async def get_voice(name: str) -> VoiceOut:
    assert _repo is not None
    v = await _repo.get(name)
    if v is None:
        raise HTTPException(404, f"voice '{name}' not found")
    return VoiceOut.from_model(v)


@app.post("/voices", response_model=VoiceOut)
async def create_voice(
    name: str = Form(..., description="Slug used as the API key, e.g. 'rick'"),
    display_name: str = Form(...),
    prompt_text: Optional[str] = Form(None),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    audio: UploadFile = File(..., description="Reference audio (any format sf can read)"),
) -> VoiceOut:
    """Create or replace a voice profile.

    Uploaded audio is trimmed to REF_AUDIO_MAX_SECONDS and downmixed to mono
    before being stored under VOICES_DIR as <name>.wav.
    """
    assert _repo is not None

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio.filename or "up").suffix) as tmp:
        shutil.copyfileobj(audio.file, tmp)
        src_tmp = tmp.name

    try:
        info = sf.info(src_tmp)
        frames = int(min(info.duration, REF_AUDIO_MAX_SECONDS) * info.samplerate)
        data, sr = sf.read(src_tmp, frames=frames)
        if data.ndim == 2:
            data = data.mean(axis=1)
        dest = VOICES_DIR / f"{name}.wav"
        sf.write(dest, data, sr, subtype="PCM_16")
        duration = min(info.duration, REF_AUDIO_MAX_SECONDS)
    finally:
        Path(src_tmp).unlink(missing_ok=True)

    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    v = await _repo.upsert(
        name=name, display_name=display_name, wav_path=dest.name,
        duration_s=duration, source_path=audio.filename,
        prompt_text=prompt_text, tags=tag_list,
        # Auto-populate per-engine ref for zero-friction onboarding. Operators
        # can later POST a different clip per engine if they want engine-specific
        # tuning; the default here means "same clip for everyone".
        vibevoice_ref_path=dest.name,
        vibevoice_speaker_tag=None,  # reserved for future multi-speaker
    )
    return VoiceOut.from_model(v)


@app.put("/voices/{name}/persona", response_model=VoiceOut)
async def set_voice_persona(name: str, body: VoicePersonaIn) -> VoiceOut:
    """Associate a spoken-text persona with a voice.

    ``persona`` is a persona id (basename of plugins/voice-persona/personas/<id>.md), ``"none"``
    to suppress persona enrichment for this voice, or ``null`` to clear the association. The
    server stores the slug only; it does not read persona files.
    """
    assert _repo is not None
    persona = body.persona.strip() if body.persona is not None else None
    if persona is not None and persona.lower() == PERSONA_NONE:
        persona = PERSONA_NONE  # consumers compare against the literal 'none'
    if persona is not None and persona != PERSONA_NONE and not PERSONA_RE.match(persona):
        raise HTTPException(422, f"invalid persona {body.persona!r}: expected [A-Za-z0-9][A-Za-z0-9_.-]* or 'none'")
    v = await _repo.set_persona(name, persona)
    if v is None:
        raise HTTPException(404, f"voice '{name}' not found")
    return VoiceOut.from_model(v)


@app.delete("/voices/{name}")
async def delete_voice(name: str):
    assert _repo is not None
    v = await _repo.get(name)
    if v is None:
        raise HTTPException(404, f"voice '{name}' not found")
    await _repo.delete(name)
    try:
        v.abs_path.unlink(missing_ok=True)
    except Exception:
        pass
    return {"deleted": name}


# ---------- FastMCP tools ----------

def _default_voice() -> Optional[str]:
    """Resolve the default voice from env, falling back to 'rick'.

    Set VOX_DEFAULT_VOICE in the container env to change the fleet default.
    Pass voice="" (empty string) to explicitly request voice-design mode.
    """
    return os.environ.get("VOX_DEFAULT_VOICE", "rick")


@mcp.tool
async def speak(
    text: str,
    voice: Optional[str] = None,
    cfg: float = 2.0,
    steps: int = 10,
) -> dict:
    """Synthesize speech and return the audio as base64-encoded WAV bytes.

    Prefer ``speak_url`` for most delivery surfaces; this tool only exists for
    callers that must have the raw bytes inline.

    Args:
        text: What to say.
        voice: Name of a saved voice profile. Defaults to the service default
            voice (rick). Pass empty string "" for voice-design mode.
        cfg: Classifier-free guidance scale (1.0-5.0).
        steps: Diffusion inference steps (higher = better quality, slower).
    """
    import base64
    if voice is None:
        voice = _default_voice()
    result = await _synthesize_wav(
        text=text, voice_name=voice, cfg=cfg, steps=steps,
    )
    return {
        "audio_wav_b64": base64.b64encode(result.wav_bytes).decode("ascii"),
        "voice": voice,
        "engine": result.engine,
        "bytes": len(result.wav_bytes),
    }


@mcp.tool
async def speak_url(
    text: str,
    voice: Optional[str] = None,
    cfg: float = 2.0,
    steps: int = 10,
) -> dict:
    """Synthesize speech and return a short-lived OGG/Opus URL.

    The returned URL is Telegram-ready: pass it to the ``telegram`` channel's
    ``send`` action with ``asVoice: true`` and Telegram's servers fetch
    directly. Also works for browser <audio>, Home Assistant media_player,
    Discord, etc. Entries expire after VOX_AUDIO_TTL_SECONDS (default 1h).

    Args:
        text: What to say.
        voice: Name of a saved voice profile. Defaults to the service default
            voice (rick). Pass empty string "" for voice-design mode.
        cfg: Classifier-free guidance scale (1.0-5.0).
        steps: Diffusion inference steps (higher = better quality, slower).
    """
    if voice is None:
        voice = _default_voice()
    resp = await _synthesize_and_cache(
        text=text, voice_name=voice, cfg=cfg, steps=steps,
    )
    return resp.model_dump()


@mcp.tool
async def speak_sink(
    text: str,
    sink: Optional[str] = None,
    voice: Optional[str] = None,
    cfg: float = 2.0,
    steps: int = 10,
) -> dict:
    """Speak to the human wherever they are, instead of into the host's speakers.

    An agent running on a server has no speakers anyone is sitting in front of.
    This routes the audio to a named *sink* -- the machine the human is actually
    at, which holds a listening connection (``voxxy listen``).

    ``delivered: 0`` means no machine was listening on that sink; the returned
    ``audio_url`` is still valid, so fall back to delivering it another way
    (Telegram, a message) rather than assuming the human heard it.

    Args:
        text: What to say.
        sink: Sink name. Defaults to the service default (VOX_DEFAULT_SINK).
        voice: Saved voice profile. Defaults to the service default voice.
        cfg: Classifier-free guidance scale (1.0-5.0).
        steps: Diffusion inference steps (higher = better quality, slower).
    """
    key = sink or os.environ.get("VOX_DEFAULT_SINK", "")
    if not key:
        return {"error": "no sink given and VOX_DEFAULT_SINK is unset"}
    try:
        sink_relay.validate_key(key)
    except sink_relay.SinkKeyError as exc:
        return {"error": str(exc)}

    if voice is None:
        voice = _default_voice()
    resp = await _synthesize_and_cache(
        text=text, voice_name=voice, cfg=cfg, steps=steps,
    )
    delivered = _sinks.publish(key, {
        "audio_url": resp.audio_url,
        "text": text,
        "voice": voice,
        "engine": resp.engine,
        "duration_s": resp.duration_s,
        "format": resp.format,
    })
    return {"sink": key, "delivered": delivered, **resp.model_dump()}


@mcp.tool
async def list_voices_tool() -> list[dict]:
    """List all available saved voice profiles."""
    assert _repo is not None
    return [
        {
            "name": v.name,
            "display_name": v.display_name,
            "duration_s": v.duration_s,
            "tags": v.tags,
            "elevenlabs_voice_id": v.elevenlabs_voice_id,
            "persona": v.persona,
        }
        for v in await _repo.list()
    ]


# Mount FastMCP's streamable HTTP app at /mcp so clients can:
#   hermes mcp add vox --url http://vox:8000/mcp/
# path="/" above means the MCP endpoint sits at the mount root, not /mcp/mcp.
app.mount("/mcp", mcp_app)
