from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_rabbit_url() -> str:
    user = os.getenv("RABBITMQ_USER", "delorenj")
    password = os.getenv("RABBITMQ_PASS", "")
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_PORT", "5673"))
    vhost = os.getenv("RABBITMQ_VHOST", "/")

    auth = quote(user, safe="")
    if password:
        auth = f"{auth}:{quote(password, safe='')}"

    if vhost == "/":
        vhost_path = "/"
    else:
        vhost_path = f"/{quote(vhost, safe='')}"

    return f"amqp://{auth}@{host}:{port}{vhost_path}"


def _default_exchange_name() -> str:
    return os.getenv("EXCHANGE_NAME") or os.getenv("BLOODBANK_EXCHANGE") or "bloodbank.events.v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")

    rabbit_url: str = Field(default_factory=_default_rabbit_url, alias="RABBIT_URL")
    exchange_name: str = Field(default_factory=_default_exchange_name, alias="EXCHANGE_NAME")

    queue_name: str = Field("services.agent.voice_soprano", alias="VOICE_QUEUE_NAME")
    routing_key: str = Field("agent.*.message.*", alias="VOICE_ROUTING_KEY")

    speak_on_received: bool = Field(False, alias="VOICE_SPEAK_ON_RECEIVED")
    speak_on_sent: bool = Field(True, alias="VOICE_SPEAK_ON_SENT")

    soprano_bin: str = Field("soprano", alias="SOPRANO_BIN")
    soprano_timeout_sec: int = Field(45, alias="SOPRANO_TIMEOUT_SEC")
    default_mode: str = Field("stream", alias="SOPRANO_MODE")  # stream|wav
    default_extra_args: str = Field("", alias="SOPRANO_EXTRA_ARGS")

    output_dir: Path = Field(Path("/tmp/agent-voice-soprano"), alias="SOPRANO_OUTPUT_DIR")
    wav_player_cmd: str = Field("", alias="SOPRANO_WAV_PLAYER")

    profiles_path: Path = Field(
        Path("./voice-profiles.yaml"),
        alias="VOICE_PROFILES_PATH",
        description="YAML file defining per-agent voice profiles",
    )

    max_chars: int = Field(500, alias="VOICE_MAX_CHARS")
    prefix_event_type: bool = Field(False, alias="VOICE_PREFIX_EVENT_TYPE")
    dry_run: bool = Field(False, alias="VOICE_DRY_RUN")


settings = Settings()
