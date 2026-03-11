from __future__ import annotations

import shlex
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from .profiles import VoiceProfile


def _resolve_player_cmd(path: Path, player_cmd: str) -> list[str]:
    if player_cmd.strip():
        return shlex.split(player_cmd.format(path=str(path)))

    if shutil.which("mpv"):
        return ["mpv", "--no-video", "--really-quiet", str(path)]
    if shutil.which("ffplay"):
        return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", str(path)]
    if shutil.which("aplay"):
        return ["aplay", str(path)]

    raise RuntimeError("No audio player found for wav mode (mpv/ffplay/aplay)")


def build_soprano_cmd(
    text: str,
    soprano_bin: str,
    mode: str,
    default_extra_args: str,
    profile: VoiceProfile,
    output_dir: Path,
) -> tuple[list[str], Path | None]:
    cmd = [soprano_bin, text]

    if profile.model_path:
        cmd += ["--model-path", profile.model_path]

    if default_extra_args:
        cmd.extend(shlex.split(default_extra_args))
    if profile.extra_args:
        cmd.extend(shlex.split(profile.extra_args))

    if mode == "stream":
        cmd.append("-s")
        return cmd, None

    output_dir.mkdir(parents=True, exist_ok=True)
    wav_path = output_dir / f"soprano-{int(time.time())}-{uuid.uuid4().hex[:8]}.wav"
    cmd += ["-o", str(wav_path)]
    return cmd, wav_path


def speak(
    *,
    text: str,
    soprano_bin: str,
    mode: str,
    default_extra_args: str,
    profile: VoiceProfile,
    timeout_sec: int,
    output_dir: Path,
    wav_player_cmd: str,
    dry_run: bool = False,
) -> str:
    cmd, wav_path = build_soprano_cmd(
        text=text,
        soprano_bin=soprano_bin,
        mode=mode,
        default_extra_args=default_extra_args,
        profile=profile,
        output_dir=output_dir,
    )

    if dry_run:
        return f"DRY_RUN: {' '.join(shlex.quote(c) for c in cmd)}"

    subprocess.run(cmd, check=True, timeout=timeout_sec)

    if mode == "wav" and wav_path:
        play_cmd = _resolve_player_cmd(wav_path, wav_player_cmd)
        subprocess.run(play_cmd, check=True, timeout=timeout_sec)
        return f"played:{wav_path}"

    return "streamed"
