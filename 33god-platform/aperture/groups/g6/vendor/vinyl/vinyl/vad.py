"""Shared silero VAD construction (used by local daemon and server modes)."""
import os
from pathlib import Path

import sherpa_onnx

SAMPLE_RATE = 16000
VAD_WINDOW = 512
MAX_SEGMENT_SECONDS = 30.0  # keeps ONNX allocations bounded (Orca #7925)

# Progressive hypotheses now provide latency without forcing the VAD to chop
# normal speech into tiny offline-recognizer inputs. 0.35s reproduced one-word
# junk (including "Yeah") at ordinary mid-sentence pauses; 0.65s preserves the
# acoustic context Parakeet needs while partials update once per second.
MIN_SILENCE_SECONDS = float(os.environ.get("VINYL_MIN_SILENCE", "0.65"))
VAD_THRESHOLD = float(os.environ.get("VINYL_VAD_THRESHOLD", "0.35"))

DEFAULT_VAD_MODEL = Path("~/audio/models/silero_vad.onnx").expanduser()


def make_vad(model: Path = DEFAULT_VAD_MODEL) -> sherpa_onnx.VoiceActivityDetector | None:
    """VoiceActivityDetector tuned for dictation, or None if the model file
    is missing (callers fall back to an energy gate)."""
    model = Path(model)
    if not model.exists():
        return None
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = str(model)
    cfg.silero_vad.threshold = VAD_THRESHOLD
    cfg.silero_vad.min_speech_duration = 0.2
    cfg.silero_vad.min_silence_duration = MIN_SILENCE_SECONDS
    cfg.silero_vad.max_speech_duration = MAX_SEGMENT_SECONDS
    cfg.silero_vad.window_size = VAD_WINDOW
    cfg.sample_rate = SAMPLE_RATE
    cfg.num_threads = 1
    cfg.provider = "cpu"
    return sherpa_onnx.VoiceActivityDetector(
        config=cfg, buffer_size_in_seconds=MAX_SEGMENT_SECONDS + 10
    )
