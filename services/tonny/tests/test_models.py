"""Tests for data models."""

from datetime import datetime
from uuid import uuid4

import pytest

from src.models import ProcessingMetrics, TranscriptionEvent


def test_transcription_event_parsing():
    """Test TranscriptionEvent parses payload correctly."""
    event = TranscriptionEvent(
        session_id=uuid4(),
        payload={
            "text": "Hello world",
            "confidence": 0.95,
            "language": "en",
        },
    )

    assert event.transcription_text == "Hello world"
    assert event.confidence == 0.95
    assert event.language == "en"


def test_transcription_event_empty_text():
    """Test TranscriptionEvent handles empty text."""
    event = TranscriptionEvent(
        session_id=uuid4(),
        payload={"confidence": 0.95},
    )

    assert event.transcription_text == ""


def test_processing_metrics_latency_calculations():
    """Test ProcessingMetrics calculates latencies correctly."""
    base_time = datetime.utcnow()

    metrics = ProcessingMetrics(
        session_id=uuid4(),
        transcription_received_at=base_time,
        llm_processing_started_at=base_time,
        llm_processing_completed_at=datetime.fromtimestamp(base_time.timestamp() + 0.5),
        tts_processing_started_at=datetime.fromtimestamp(base_time.timestamp() + 0.5),
        tts_processing_completed_at=datetime.fromtimestamp(base_time.timestamp() + 1.0),
        event_published_at=datetime.fromtimestamp(base_time.timestamp() + 1.5),
    )

    assert 400 < metrics.llm_latency_ms < 600  # ~500ms
    assert 400 < metrics.tts_latency_ms < 600  # ~500ms
    assert 1400 < metrics.total_latency_ms < 1600  # ~1500ms
