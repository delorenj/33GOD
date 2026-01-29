#!/usr/bin/env python3
"""
Extract audio from video files or pass through audio files unchanged.

Usage: extract_audio.py <input_file> [output_dir]

Returns JSON: {"success": true, "audio_file": "/path/to/audio.mp3", "extracted": true/false}
"""

import json
import os
import subprocess
import sys
from pathlib import Path


VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.flv'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac'}


def detect_media_type(file_path: Path) -> str:
    """Detect if file is video, audio, or other."""
    ext = file_path.suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    elif ext in AUDIO_EXTENSIONS:
        return 'audio'
    else:
        return 'other'


def extract_audio_from_video(video_path: Path, output_dir: Path) -> Path:
    """Extract audio from video file using ffmpeg."""
    output_file = output_dir / f"{video_path.stem}.mp3"

    # ffmpeg command: extract audio, encode as MP3, quality 2 (high)
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-vn',  # No video
        '-acodec', 'libmp3lame',
        '-q:a', '2',  # Quality 2 (VBR ~170-210 kbps)
        '-y',  # Overwrite output file
        str(output_file)
    ]

    # Run ffmpeg with stderr capture for error handling
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    if not output_file.exists():
        raise RuntimeError(f"ffmpeg did not create output file: {output_file}")

    return output_file


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Missing input file argument"
        }))
        sys.exit(1)

    input_path = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else input_path.parent

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Detect media type
    media_type = detect_media_type(input_path)

    try:
        if media_type == 'video':
            # Extract audio from video
            audio_file = extract_audio_from_video(input_path, output_dir)
            result = {
                "success": True,
                "audio_file": str(audio_file),
                "original_file": str(input_path),
                "media_type": media_type,
                "extracted": True
            }
        elif media_type == 'audio':
            # Audio file, pass through unchanged
            result = {
                "success": True,
                "audio_file": str(input_path),
                "original_file": str(input_path),
                "media_type": media_type,
                "extracted": False
            }
        else:
            # Not a media file
            result = {
                "success": False,
                "error": f"Not a media file: {input_path.suffix}",
                "media_type": media_type
            }
    except Exception as e:
        result = {
            "success": False,
            "error": str(e),
            "original_file": str(input_path)
        }

    print(json.dumps(result))


if __name__ == '__main__':
    main()
