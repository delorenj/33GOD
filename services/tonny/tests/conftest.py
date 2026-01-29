"""Pytest fixtures for Tonny Agent tests."""

import asyncio
from datetime import datetime
from typing import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.models import TranscriptionEvent


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_transcription_event() -> TranscriptionEvent:
    """Create sample transcription event for testing."""
    return TranscriptionEvent(
        event_id=uuid4(),
        event_type="transcription.voice.completed",
        timestamp=datetime.utcnow(),
        source="whisperlivekit",
        target="tonny",
        session_id=uuid4(),
        payload={
            "text": "What's the weather today?",
            "confidence": 0.98,
            "language": "en",
        },
    )


@pytest.fixture
async def mock_letta_client(mocker):
    """Mock Letta client for testing."""
    mock_client = mocker.AsyncMock()
    mock_client.post.return_value.json.return_value = {
        "messages": [
            {
                "role": "assistant",
                "content": "The weather today is sunny and 72 degrees.",
            }
        ]
    }
    return mock_client


@pytest.fixture
async def mock_elevenlabs_client(mocker):
    """Mock ElevenLabs client for testing."""
    mock_client = mocker.AsyncMock()
    mock_client.post.return_value.content = b"fake_audio_data"
    return mock_client
