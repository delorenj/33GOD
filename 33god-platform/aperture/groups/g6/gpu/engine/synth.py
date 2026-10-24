"""VoxCPM2 synthesis wrapper with the memory-safety patches baked in.

The VoxCPM model is loaded once at startup and reused for every request.
All memory-containment workarounds we derived earlier live here so they
follow the model wherever it runs (HTTP, MCP, CLI, tests).
"""

from __future__ import annotations

import gc
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
import torch

# voxcpm is loaded lazily in Synth.load() so import-time cost stays cheap.

logger = logging.getLogger(__name__)

# Peak VRAM is proportional to reference audio length; 30s is plenty for
# speaker timbre extraction and safely fits on a 24 GB card alongside the
# model state. Raise only if you benchmark more VRAM.
REF_AUDIO_MAX_SECONDS = float(os.environ.get("VOX_REF_AUDIO_MAX_SECONDS", "30"))

# optimize=True triggers torch.compile which balloons peak memory on 24 GB
# cards shared with other workloads. Opt-in only.
VOX_OPTIMIZE = os.environ.get("VOX_OPTIMIZE", "0") == "1"

DEFAULT_MAX_LEN = int(os.environ.get("VOX_MAX_LEN", "2048"))


class Synth:
    """Singleton wrapper around voxcpm.VoxCPM.

    Use :meth:`load` once at startup, then call :meth:`generate` per request.
    """

    def __init__(self, model_id: str = "openbmb/VoxCPM2") -> None:
        self._model_id = model_id
        self._model = None  # lazy

    @property
    def sample_rate(self) -> int:
        assert self._model is not None, "call load() first"
        return self._model.tts_model.sample_rate

    def load(self) -> None:
        """Load the model into GPU/CPU memory. Idempotent."""
        if self._model is not None:
            return
        logger.info("Loading VoxCPM2 model (optimize=%s)...", VOX_OPTIMIZE)
        import voxcpm  # local import: heavy deps
        from huggingface_hub import snapshot_download
        model_path = snapshot_download(self._model_id, revision="32279effe8c19989596f05d353d1447f51d9e915")
        self._model = voxcpm.VoxCPM.from_pretrained(
            model_path,
            load_denoiser=False,
            optimize=VOX_OPTIMIZE,
        )
        logger.info("VoxCPM2 loaded on %s", "cuda" if torch.cuda.is_available() else "cpu")

    def _maybe_trim_reference(self, ref_path: Optional[str]) -> Optional[str]:
        """Trim reference audio > REF_AUDIO_MAX_SECONDS and downmix to mono.

        Returns either the original path (if short enough) or a temp-file
        path with the trimmed audio. Caller is responsible for cleanup if
        a temp path is returned.
        """
        if not ref_path:
            return None
        try:
            info = sf.info(ref_path)
        except Exception as exc:
            logger.warning("Cannot probe reference audio %s: %s", ref_path, exc)
            return ref_path

        if info.duration <= REF_AUDIO_MAX_SECONDS and info.channels <= 1:
            return ref_path

        logger.info(
            "Trimming reference %s (duration=%.1fs channels=%d) to %.0fs mono",
            ref_path, info.duration, info.channels, REF_AUDIO_MAX_SECONDS,
        )
        data, sr = sf.read(
            ref_path, frames=int(REF_AUDIO_MAX_SECONDS * info.samplerate)
        )
        if data.ndim == 2:
            data = data.mean(axis=1)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp.close()
        sf.write(tmp.name, data, sr, subtype="PCM_16")
        return tmp.name

    def generate(
        self,
        *,
        text: str,
        reference_wav_path: Optional[str] = None,
        prompt_wav_path: Optional[str] = None,
        prompt_text: Optional[str] = None,
        cfg_value: float = 2.0,
        inference_timesteps: int = 10,
        normalize: bool = False,
        denoise: bool = False,
        max_len: int = DEFAULT_MAX_LEN,
    ) -> tuple[np.ndarray, int]:
        """Generate a waveform for ``text``. Returns (wav, sample_rate)."""
        assert self._model is not None, "call load() first"
        if not text or not text.strip():
            raise ValueError("text must be a non-empty string")

        trimmed_ref = self._maybe_trim_reference(reference_wav_path)
        trimmed_prompt = self._maybe_trim_reference(prompt_wav_path)
        temp_paths = [
            p for p in (trimmed_ref, trimmed_prompt)
            if p and p != reference_wav_path and p != prompt_wav_path
        ]

        kwargs = dict(
            text=text,
            cfg_value=float(cfg_value),
            inference_timesteps=int(inference_timesteps),
            normalize=bool(normalize),
            denoise=bool(denoise),
            max_len=int(max_len),
            retry_badcase_max_times=1,
        )
        if trimmed_ref:
            kwargs["reference_wav_path"] = trimmed_ref
        if trimmed_prompt and prompt_text:
            kwargs["prompt_wav_path"] = trimmed_prompt
            kwargs["prompt_text"] = prompt_text

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        try:
            wav = self._model.generate(**kwargs)
        finally:
            # Release transient tensors + temp files regardless of outcome.
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
            for p in temp_paths:
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception:
                    pass

        if torch.cuda.is_available():
            peak_gb = torch.cuda.max_memory_allocated() / 1e9
            logger.info("synthesis peak VRAM %.2f GB (text_len=%d)", peak_gb, len(text))

        return wav, self.sample_rate
