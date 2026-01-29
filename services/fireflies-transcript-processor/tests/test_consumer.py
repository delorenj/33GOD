import pytest
from unittest.mock import patch, MagicMock
from src.consumer import ServiceConsumer
from src.models import TranscriptData, Sentence
from src.config import settings

@pytest.fixture
def sample_transcript_data():
    return TranscriptData(
        id="123",
        title="Test Meeting",
        date="2023-10-27T10:00:00Z",
        sentences=[
            Sentence(text="Hello world", speaker_name="Alice", start_time=0.0),
            Sentence(text="Hi Alice", speaker_name="Bob", start_time=5.0),
        ]
    )

@pytest.mark.asyncio
async def test_process_transcript_creates_file(tmp_path, sample_transcript_data):
    # Override vault_path to use tmp_path
    with patch("src.consumer.settings.vault_path", str(tmp_path)):
        consumer = ServiceConsumer()
        
        await consumer.process_transcript(sample_transcript_data)
        
        # Verify directory structure
        output_dir = tmp_path / "Transcripts"
        assert output_dir.exists()
        
        # Verify file exists
        expected_filename = "2023-10-27_Test-Meeting.md"
        output_file = output_dir / expected_filename
        assert output_file.exists()
        
        # Verify content
        content = output_file.read_text()
        assert "# Test Meeting" in content
        assert "**Date:** 2023-10-27T10:00:00Z" in content
        assert "**Alice** (00:00):" in content
        assert "Hello world" in content
        assert "**Bob** (00:05):" in content
        assert "Hi Alice" in content

@pytest.mark.asyncio
async def test_handle_event_valid_payload(tmp_path, sample_transcript_data):
    # Mock the envelope
    envelope = MagicMock()
    envelope.event_type = "fireflies.transcript.ready"
    envelope.payload = sample_transcript_data.model_dump()
    
    with patch("src.consumer.settings.vault_path", str(tmp_path)):
        consumer = ServiceConsumer()
        
        await consumer.handle_event(envelope)
        
        # Verify file creation (indirectly verifies process_transcript was called)
        output_dir = tmp_path / "Transcripts"
        expected_filename = "2023-10-27_Test-Meeting.md"
        assert (output_dir / expected_filename).exists()
