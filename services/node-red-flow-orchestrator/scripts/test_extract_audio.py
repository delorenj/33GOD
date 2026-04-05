"""P1 tests for extract_audio.py (T24-T26)."""
from pathlib import Path

from extract_audio import detect_media_type


# T24: detects video file extension and returns media_type "video"
def test_video_extensions_detected():
    assert detect_media_type(Path("meeting.mp4")) == "video"
    assert detect_media_type(Path("clip.mov")) == "video"
    assert detect_media_type(Path("movie.mkv")) == "video"


# T25: passes through audio file with media_type "audio"
def test_audio_extensions_detected():
    assert detect_media_type(Path("song.mp3")) == "audio"
    assert detect_media_type(Path("recording.wav")) == "audio"
    assert detect_media_type(Path("voice.m4a")) == "audio"


# T26: rejects non-media file with media_type "other"
def test_non_media_returns_other():
    assert detect_media_type(Path("report.pdf")) == "other"
    assert detect_media_type(Path("notes.txt")) == "other"
    assert detect_media_type(Path("resume.docx")) == "other"
