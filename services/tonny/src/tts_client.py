"""ElevenLabs TTS client for generating voice responses."""

import asyncio
import base64
from datetime import datetime
from typing import Optional

import httpx
import structlog

from .config import settings
from .models import TTSResponse

logger = structlog.get_logger(__name__)


class ElevenLabsClient:
    """
    ElevenLabs TTS client for converting text to speech.

    Supports both streaming and non-streaming modes.
    """

    def __init__(self) -> None:
        """Initialize ElevenLabs client."""
        self.api_key = settings.elevenlabs_api_key
        self.voice_id = settings.elevenlabs_voice_id
        self.model_id = settings.elevenlabs_model_id
        self.base_url = "https://api.elevenlabs.io/v1"
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize HTTP client with API key."""
        if not self.api_key:
            raise ValueError("ElevenLabs API key not configured")

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        logger.info("elevenlabs_client_initialized", voice_id=self.voice_id)

    async def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
    ) -> TTSResponse:
        """
        Convert text to speech using ElevenLabs API.

        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID override

        Returns:
            TTSResponse with audio data
        """
        if not self._client:
            raise RuntimeError("Client not initialized")

        start_time = datetime.utcnow()
        voice = voice_id or self.voice_id

        try:
            # Request TTS generation
            response = await self._client.post(
                f"/text-to-speech/{voice}",
                json={
                    "text": text,
                    "model_id": self.model_id,
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
            )
            response.raise_for_status()

            # Get audio bytes
            audio_bytes = response.content

            # Convert to base64 for event payload
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(
                "tts_generation_completed",
                processing_time_ms=processing_time,
                character_count=len(text),
                audio_size_bytes=len(audio_bytes),
            )

            return TTSResponse(
                audio_base64=audio_base64,
                voice_id=voice,
                model_id=self.model_id,
                processing_time_ms=processing_time,
                character_count=len(text),
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "elevenlabs_http_error",
                status_code=e.response.status_code,
                error=str(e),
            )
            # Check for rate limiting
            if e.response.status_code == 429:
                logger.warning("elevenlabs_rate_limited", retry_after=e.response.headers.get("Retry-After"))
            raise
        except Exception as e:
            logger.error("tts_generation_error", error=str(e), error_type=type(e).__name__)
            raise

    async def text_to_speech_streaming(
        self,
        text: str,
        voice_id: Optional[str] = None,
    ) -> bytes:
        """
        Convert text to speech using streaming API for lower latency.

        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID override

        Returns:
            Audio bytes
        """
        if not self._client:
            raise RuntimeError("Client not initialized")

        voice = voice_id or self.voice_id
        audio_chunks = []

        try:
            async with self._client.stream(
                "POST",
                f"/text-to-speech/{voice}/stream",
                json={
                    "text": text,
                    "model_id": self.model_id,
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
            ) as response:
                response.raise_for_status()

                async for chunk in response.aiter_bytes(chunk_size=4096):
                    audio_chunks.append(chunk)

            return b"".join(audio_chunks)

        except Exception as e:
            logger.error("streaming_tts_error", error=str(e))
            raise

    async def shutdown(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            logger.info("elevenlabs_client_closed")


# Global TTS client instance
_tts_client: Optional[ElevenLabsClient] = None


async def get_tts_client() -> ElevenLabsClient:
    """Get or create global TTS client instance."""
    global _tts_client
    if _tts_client is None:
        _tts_client = ElevenLabsClient()
        await _tts_client.initialize()
    return _tts_client


async def shutdown_tts_client() -> None:
    """Shutdown global TTS client instance."""
    global _tts_client
    if _tts_client:
        await _tts_client.shutdown()
        _tts_client = None
