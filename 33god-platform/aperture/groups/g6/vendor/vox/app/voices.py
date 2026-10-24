"""Voice profile CRUD over asyncpg.

The `voices` table stores metadata and a relative filename under
``VOX_VOICES_DIR``. Audio bytes live on disk, not in postgres.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import asyncpg

VOICES_DIR = Path(os.environ.get("VOX_VOICES_DIR", "/data/voices"))

# voices.persona: NULL = no voxxy-level association (consumers fall back to persona frontmatter),
# PERSONA_NONE = explicitly no persona, otherwise the basename of a persona file
# (plugins/voice-persona/personas/<id>.md). The server stores the slug and never reads persona files.
PERSONA_NONE = "none"
PERSONA_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

_VOICE_COLUMNS = """name, display_name, wav_path, duration_s, prompt_text, tags,
                      elevenlabs_voice_id, vibevoice_ref_path, vibevoice_speaker_tag, persona"""


@dataclass(slots=True)
class Voice:
    name: str
    display_name: str
    wav_path: str  # relative to VOICES_DIR
    duration_s: float
    prompt_text: Optional[str]
    tags: list[str]
    # Optional ElevenLabs voice id for fallback synthesis. When None, the
    # ElevenLabs engine uses its configured default voice.
    elevenlabs_voice_id: Optional[str] = None
    # Per-engine reference audio path overrides (relative to VOICES_DIR).
    # NULL/None means "fall back to wav_path" for that engine.
    vibevoice_ref_path: Optional[str] = None
    vibevoice_speaker_tag: Optional[str] = None
    # Voice -> persona association for spoken-text enrichment (see PERSONA_* above).
    persona: Optional[str] = None

    @property
    def abs_path(self) -> Path:
        return VOICES_DIR / self.wav_path

    def ref_path_for(self, engine: str) -> Path:
        """Engine-specific reference WAV path on disk.

        Falls back to the default ``wav_path`` when no engine-specific override
        is configured. Kept on the dataclass so resolution logic stays colocated
        with the data.
        """
        engine_path_map = {"vibevoice": self.vibevoice_ref_path}
        rel = engine_path_map.get(engine) or self.wav_path
        return VOICES_DIR / rel


class VoiceRepo:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @classmethod
    async def connect(cls, dsn: str) -> "VoiceRepo":
        pool = await asyncpg.create_pool(dsn, min_size=1, max_size=4)
        return cls(pool)

    async def close(self) -> None:
        await self._pool.close()

    async def get(self, name: str) -> Optional[Voice]:
        row = await self._pool.fetchrow(
            f"SELECT {_VOICE_COLUMNS} FROM voices WHERE name = $1",
            name,
        )
        return _row_to_voice(row) if row else None

    async def list(self) -> list[Voice]:
        rows = await self._pool.fetch(
            f"SELECT {_VOICE_COLUMNS} FROM voices ORDER BY name"
        )
        return [_row_to_voice(r) for r in rows]

    async def upsert(
        self,
        *,
        name: str,
        display_name: str,
        wav_path: str,
        duration_s: float,
        source_path: Optional[str] = None,
        prompt_text: Optional[str] = None,
        tags: Optional[list[str]] = None,
        vibevoice_ref_path: Optional[str] = None,
        vibevoice_speaker_tag: Optional[str] = None,
    ) -> Voice:
        # persona is deliberately absent from the ON CONFLICT set: re-uploading a clip keeps its association.
        row = await self._pool.fetchrow(
            """INSERT INTO voices (name, display_name, wav_path, source_path,
                                   duration_s, prompt_text, tags,
                                   vibevoice_ref_path, vibevoice_speaker_tag)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
               ON CONFLICT (name) DO UPDATE SET
                   display_name          = EXCLUDED.display_name,
                   wav_path              = EXCLUDED.wav_path,
                   source_path           = EXCLUDED.source_path,
                   duration_s            = EXCLUDED.duration_s,
                   prompt_text           = EXCLUDED.prompt_text,
                   tags                  = EXCLUDED.tags,
                   vibevoice_ref_path    = EXCLUDED.vibevoice_ref_path,
                   vibevoice_speaker_tag = EXCLUDED.vibevoice_speaker_tag,
                   updated_at            = now()
               RETURNING """ + _VOICE_COLUMNS,
            name, display_name, wav_path, source_path,
            duration_s, prompt_text, tags or [],
            vibevoice_ref_path, vibevoice_speaker_tag,
        )
        return _row_to_voice(row)

    async def set_persona(self, name: str, persona: Optional[str]) -> Optional[Voice]:
        """Set (or with None, clear) the voice's persona; None result means no such voice."""
        row = await self._pool.fetchrow(
            "UPDATE voices SET persona = $2, updated_at = now() WHERE name = $1 RETURNING " + _VOICE_COLUMNS,
            name, persona,
        )
        return _row_to_voice(row) if row else None

    async def delete(self, name: str) -> bool:
        res = await self._pool.execute("DELETE FROM voices WHERE name = $1", name)
        return res.endswith(" 1")


def _row_to_voice(row) -> Voice:
    return Voice(
        name=row["name"],
        display_name=row["display_name"],
        wav_path=row["wav_path"],
        duration_s=float(row["duration_s"]),
        prompt_text=row["prompt_text"],
        tags=list(row["tags"] or []),
        elevenlabs_voice_id=row["elevenlabs_voice_id"],
        vibevoice_ref_path=row["vibevoice_ref_path"],
        vibevoice_speaker_tag=row["vibevoice_speaker_tag"],
        persona=row["persona"],
    )
