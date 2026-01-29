"""Data models for Tonny Agent."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TranscriptionEvent(BaseModel):
    """Event payload for voice transcription completion."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(default="transcription.voice.completed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(default="whisperlivekit")
    target: str = Field(default="tonny")
    session_id: UUID
    payload: dict[str, Any]

    @property
    def transcription_text(self) -> str:
        """Extract transcription text from payload."""
        return self.payload.get("text", "").strip()

    @property
    def confidence(self) -> float:
        """Extract transcription confidence from payload."""
        return self.payload.get("confidence", 0.0)

    @property
    def language(self) -> str:
        """Extract language from payload."""
        return self.payload.get("language", "en")


class LLMResponse(BaseModel):
    """Response from LLM processing."""

    text: str
    agent_id: str
    session_id: UUID
    processing_time_ms: float
    token_count: Optional[int] = None
    model: str


class TTSResponse(BaseModel):
    """Response from ElevenLabs TTS."""

    audio_url: Optional[str] = None
    audio_base64: Optional[str] = None
    voice_id: str
    model_id: str
    processing_time_ms: float
    character_count: int


class TTSCompletedEvent(BaseModel):
    """Event payload for TTS response completion."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(default="tts.response.completed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(default="tonny")
    target: str = Field(default="")
    session_id: UUID
    payload: dict[str, Any]


class ProcessingMetrics(BaseModel):
    """Metrics for end-to-end processing."""

    session_id: UUID
    transcription_received_at: datetime
    llm_processing_started_at: datetime
    llm_processing_completed_at: datetime
    tts_processing_started_at: datetime
    tts_processing_completed_at: datetime
    event_published_at: datetime

    @property
    def total_latency_ms(self) -> float:
        """Calculate total latency from transcription to TTS completion."""
        delta = self.event_published_at - self.transcription_received_at
        return delta.total_seconds() * 1000

    @property
    def llm_latency_ms(self) -> float:
        """Calculate LLM processing latency."""
        delta = self.llm_processing_completed_at - self.llm_processing_started_at
        return delta.total_seconds() * 1000

    @property
    def tts_latency_ms(self) -> float:
        """Calculate TTS processing latency."""
        delta = self.tts_processing_completed_at - self.tts_processing_started_at
        return delta.total_seconds() * 1000
