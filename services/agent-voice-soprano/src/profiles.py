from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class VoiceProfile:
    enabled: bool = True
    mode: str | None = None  # stream|wav
    model_path: str | None = None
    extra_args: str = ""
    text_prefix: str = ""


class VoiceProfileStore:
    """Hot-reloadable YAML voice profile store."""

    def __init__(self, path: Path):
        self.path = path
        self._mtime: float | None = None
        self._default = VoiceProfile()
        self._agents: dict[str, VoiceProfile] = {}

    def get(self, agent_name: str) -> VoiceProfile:
        self._reload_if_needed()
        key = (agent_name or "").strip().lower()
        return self._agents.get(key, self._default)

    def _reload_if_needed(self) -> None:
        if not self.path.exists():
            return

        mtime = self.path.stat().st_mtime
        if self._mtime is not None and mtime <= self._mtime:
            return

        raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        self._default = self._parse_profile(raw.get("default", {}))

        agents: dict[str, VoiceProfile] = {}
        for name, payload in (raw.get("agents") or {}).items():
            agents[str(name).strip().lower()] = self._parse_profile(payload or {})

        self._agents = agents
        self._mtime = mtime

    @staticmethod
    def _parse_profile(data: dict[str, Any]) -> VoiceProfile:
        return VoiceProfile(
            enabled=bool(data.get("enabled", True)),
            mode=(str(data["mode"]).strip().lower() if data.get("mode") else None),
            model_path=(str(data["model_path"]).strip() if data.get("model_path") else None),
            extra_args=str(data.get("extra_args", "")).strip(),
            text_prefix=str(data.get("text_prefix", "")).strip(),
        )
