"""Audio transcoding helpers.

Telegram voice notes must be OGG/Opus. VoxCPM2 and ElevenLabs both hand us
something else (WAV PCM and MP3 respectively), so everything converges on a
single ``wav_like_to_ogg_opus`` entry point that feeds ffmpeg on stdin and
reads the transcoded stream from stdout.

ffmpeg flags:
  -c:a libopus     Telegram-compatible codec
  -b:a 32k         Voice-grade bitrate; plenty for speech, keeps payload small
  -ar 48000        Opus native sample rate; avoids resample warnings
  -ac 1            Mono; Telegram voice notes are always mono
  -application voip  Opus preset tuned for speech
"""

from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


class FfmpegMissingError(RuntimeError):
    """Raised when ffmpeg is not on PATH. The container Dockerfile installs it."""


def _ffmpeg_bin() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise FfmpegMissingError("ffmpeg not found on PATH")
    return path


def to_ogg_opus(audio_bytes: bytes, *, input_format: str | None = None) -> bytes:
    """Transcode arbitrary ffmpeg-readable audio bytes to OGG/Opus mono 48 kHz.

    ``input_format`` hints ffmpeg's demuxer (``wav``, ``mp3``, ``ogg``). Leaving
    it None lets ffmpeg probe, which is fine for well-formed inputs.
    """
    cmd = [_ffmpeg_bin(), "-hide_banner", "-loglevel", "error"]
    if input_format:
        cmd += ["-f", input_format]
    cmd += [
        "-i", "pipe:0",
        "-c:a", "libopus",
        "-b:a", "32k",
        "-ar", "48000",
        "-ac", "1",
        "-application", "voip",
        "-f", "ogg",
        "pipe:1",
    ]
    proc = subprocess.run(
        cmd, input=audio_bytes, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"ffmpeg failed (rc={proc.returncode}): {stderr}")
    return proc.stdout
