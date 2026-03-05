from __future__ import annotations

import asyncio
import logging
from typing import Any

from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, ExchangeType

from .config import settings
from .profiles import VoiceProfileStore
from .speaker import speak

logger = logging.getLogger("agent_voice_soprano")

broker = RabbitBroker(settings.rabbit_url)
app = FastStream(broker)
profile_store = VoiceProfileStore(settings.profiles_path)


def _extract_agent_name(payload: dict[str, Any]) -> str:
    for key in ("agent_name", "agent", "agentName"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "unknown"


def _extract_text(payload: dict[str, Any]) -> str | None:
    candidates = [
        payload.get("message_preview"),
        payload.get("text"),
        payload.get("message"),
        payload.get("content"),
        payload.get("prompt"),
    ]

    for item in candidates:
        if isinstance(item, str) and item.strip():
            return " ".join(item.split())

    return None


@broker.subscriber(
    queue=RabbitQueue(
        name=settings.queue_name,
        routing_key=settings.routing_key,
        durable=True,
    ),
    exchange=RabbitExchange(
        name=settings.exchange_name,
        type=ExchangeType.TOPIC,
        durable=True,
    ),
)
async def handle_agent_message(message_dict: dict[str, Any]):
    event_type = str(message_dict.get("event_type", "")).strip()

    if event_type.endswith(".message.received") and not settings.speak_on_received:
        logger.debug("Skip received event (VOICE_SPEAK_ON_RECEIVED=false)")
        return
    if event_type.endswith(".message.sent") and not settings.speak_on_sent:
        logger.debug("Skip sent event (VOICE_SPEAK_ON_SENT=false)")
        return
    if event_type and not (
        event_type.endswith(".message.received") or event_type.endswith(".message.sent")
    ):
        logger.debug("Skip non-message event_type=%s", event_type)
        return
    payload = message_dict.get("payload") or {}
    if not isinstance(payload, dict):
        logger.debug("Skip non-dict payload: %s", type(payload).__name__)
        return

    text = _extract_text(payload)
    if not text:
        logger.debug("Skip event without text-like payload fields")
        return

    if settings.max_chars > 0 and len(text) > settings.max_chars:
        text = text[: settings.max_chars].rstrip() + "…"

    agent_name = _extract_agent_name(payload)
    profile = profile_store.get(agent_name)

    if not profile.enabled:
        logger.debug("Voice disabled for agent=%s", agent_name)
        return

    mode = (profile.mode or settings.default_mode or "stream").lower().strip()
    if mode not in {"stream", "wav"}:
        logger.warning("Invalid mode=%s for agent=%s; fallback=stream", mode, agent_name)
        mode = "stream"

    if profile.text_prefix:
        text = f"{profile.text_prefix} {text}"

    if settings.prefix_event_type and event_type:
        text = f"{event_type}. {text}"

    logger.info(
        "Speaking agent=%s event=%s chars=%d mode=%s",
        agent_name,
        event_type or "unknown",
        len(text),
        mode,
    )

    try:
        result = await asyncio.to_thread(
            speak,
            text=text,
            soprano_bin=settings.soprano_bin,
            mode=mode,
            default_extra_args=settings.default_extra_args,
            profile=profile,
            timeout_sec=settings.soprano_timeout_sec,
            output_dir=settings.output_dir,
            wav_player_cmd=settings.wav_player_cmd,
            dry_run=settings.dry_run,
        )
        logger.info("Voice playback result agent=%s result=%s", agent_name, result)
    except Exception:
        logger.exception("Voice playback failed agent=%s", agent_name)


def cli() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info(
        "Starting agent-voice-soprano queue=%s routing=%s exchange=%s profiles=%s",
        settings.queue_name,
        settings.routing_key,
        settings.exchange_name,
        settings.profiles_path,
    )
    asyncio.run(app.run())


if __name__ == "__main__":
    cli()
