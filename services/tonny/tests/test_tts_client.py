"""Tests for ElevenLabs TTS client."""

import base64

import pytest

from src.tts_client import ElevenLabsClient


@pytest.mark.asyncio
async def test_tts_client_initialization(mocker):
    """Test TTS client initializes with API key."""
    mocker.patch("src.config.settings.elevenlabs_api_key", "test-key")

    mock_client = mocker.AsyncMock()
    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    client = ElevenLabsClient()
    await client.initialize()

    assert client.api_key == "test-key"


@pytest.mark.asyncio
async def test_tts_client_generates_audio(mocker):
    """Test TTS client generates audio successfully."""
    mocker.patch("src.config.settings.elevenlabs_api_key", "test-key")

    fake_audio = b"fake_audio_bytes"
    mock_http_client = mocker.AsyncMock()
    mock_http_client.post.return_value.content = fake_audio
    mocker.patch("httpx.AsyncClient", return_value=mock_http_client)

    client = ElevenLabsClient()
    await client.initialize()

    response = await client.text_to_speech("Hello world")

    assert response.audio_base64 == base64.b64encode(fake_audio).decode("utf-8")
    assert response.character_count == len("Hello world")
    assert response.processing_time_ms > 0


@pytest.mark.asyncio
async def test_tts_client_handles_rate_limit(mocker):
    """Test TTS client handles rate limiting gracefully."""
    mocker.patch("src.config.settings.elevenlabs_api_key", "test-key")

    mock_response = mocker.Mock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "60"}

    mock_http_client = mocker.AsyncMock()
    mock_http_client.post.side_effect = Exception("Rate limited")

    mocker.patch("httpx.AsyncClient", return_value=mock_http_client)

    client = ElevenLabsClient()
    await client.initialize()

    with pytest.raises(Exception):
        await client.text_to_speech("Test")
