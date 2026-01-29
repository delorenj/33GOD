"""Bloodbank event consumer for processing transcription events."""

import asyncio
import json
from datetime import datetime
from typing import Any

import aio_pika
import structlog
from aio_pika import ExchangeType, IncomingMessage
from aio_pika.abc import AbstractRobustConnection

from .config import settings
from .letta_agent import get_agent, shutdown_agent
from .models import ProcessingMetrics, TranscriptionEvent, TTSCompletedEvent
from .tts_client import get_tts_client, shutdown_tts_client

logger = structlog.get_logger(__name__)


class TonnyConsumer:
    """
    Consumes transcription events from Bloodbank and processes through Letta + TTS.

    Processing flow:
    1. Receive transcription.voice.completed event
    2. Validate against HolyFields schema
    3. Extract text and pass to Letta agent
    4. Send LLM response to ElevenLabs TTS
    5. Publish tts.response.completed event back to Bloodbank
    """

    def __init__(self) -> None:
        """Initialize the Tonny consumer."""
        self.connection: AbstractRobustConnection | None = None
        self.channel: Any = None
        self.queue: Any = None
        self._shutdown = False
        self._metrics: dict[str, ProcessingMetrics] = {}

    async def connect(self) -> None:
        """Establish connection to RabbitMQ with exponential backoff."""
        retry_count = 0
        max_retries = 10
        base_delay = 1

        while retry_count < max_retries and not self._shutdown:
            try:
                logger.info("connecting_to_rabbitmq", url=settings.rabbitmq_url)
                self.connection = await aio_pika.connect_robust(
                    settings.rabbitmq_url,
                    heartbeat=60,
                )

                self.channel = await self.connection.channel()
                await self.channel.set_qos(prefetch_count=settings.consumer_prefetch_count)

                # Declare exchange
                exchange = await self.channel.declare_exchange(
                    settings.bloodbank_exchange,
                    ExchangeType.TOPIC,
                    durable=True,
                )

                # Declare queue with DLQ
                self.queue = await self.channel.declare_queue(
                    settings.tonny_queue,
                    durable=True,
                    arguments={
                        "x-dead-letter-exchange": "",
                        "x-dead-letter-routing-key": settings.tonny_dlq,
                    },
                )

                # Declare DLQ
                await self.channel.declare_queue(
                    settings.tonny_dlq,
                    durable=True,
                )

                # Bind to transcription events
                await self.queue.bind(exchange, routing_key="transcription.voice.completed")

                logger.info(
                    "connected_to_rabbitmq",
                    queue=settings.tonny_queue,
                    exchange=settings.bloodbank_exchange,
                    routing_key="transcription.voice.completed",
                )
                return

            except Exception as e:
                retry_count += 1
                delay = base_delay * (2**retry_count)
                logger.error(
                    "rabbitmq_connection_failed",
                    error=str(e),
                    retry_count=retry_count,
                    retry_delay=delay,
                )
                if retry_count < max_retries:
                    await asyncio.sleep(delay)
                else:
                    raise

    async def start(self) -> None:
        """Start consuming events from Bloodbank."""
        await self.connect()

        # Initialize Letta agent and TTS client
        await get_agent()
        await get_tts_client()

        logger.info("starting_tonny_consumer")

        if self.queue:
            await self.queue.consume(self._process_message)

    async def stop(self) -> None:
        """Stop consuming and close connections."""
        logger.info("stopping_tonny_consumer")
        self._shutdown = True

        if self.connection:
            await self.connection.close()

        # Shutdown clients
        await shutdown_agent()
        await shutdown_tts_client()

    async def _process_message(self, message: IncomingMessage) -> None:
        """
        Process a transcription event.

        Flow:
        1. Deserialize and validate event
        2. Extract transcription text
        3. Process through Letta agent
        4. Generate TTS response
        5. Publish TTS event
        6. ACK message
        """
        async with message.process():
            session_id = None
            try:
                # Deserialize message
                body = json.loads(message.body.decode())

                # Parse into TranscriptionEvent
                event = TranscriptionEvent(**body)
                session_id = event.session_id

                # Initialize metrics
                metrics = ProcessingMetrics(
                    session_id=session_id,
                    transcription_received_at=datetime.utcnow(),
                    llm_processing_started_at=datetime.utcnow(),
                    llm_processing_completed_at=datetime.utcnow(),
                    tts_processing_started_at=datetime.utcnow(),
                    tts_processing_completed_at=datetime.utcnow(),
                    event_published_at=datetime.utcnow(),
                )

                logger.info(
                    "processing_transcription",
                    event_id=str(event.event_id),
                    session_id=str(session_id),
                    text_length=len(event.transcription_text),
                )

                # Validate we have text to process
                if not event.transcription_text:
                    logger.warning("empty_transcription", event_id=str(event.event_id))
                    return

                # Process through Letta agent
                metrics.llm_processing_started_at = datetime.utcnow()
                agent = await get_agent()
                llm_response = await agent.process_message(
                    event.transcription_text,
                    session_id,
                )
                metrics.llm_processing_completed_at = datetime.utcnow()

                logger.info(
                    "llm_processing_completed",
                    session_id=str(session_id),
                    latency_ms=metrics.llm_latency_ms,
                )

                # Generate TTS response
                metrics.tts_processing_started_at = datetime.utcnow()
                tts_client = await get_tts_client()
                tts_response = await tts_client.text_to_speech(llm_response.text)
                metrics.tts_processing_completed_at = datetime.utcnow()

                logger.info(
                    "tts_generation_completed",
                    session_id=str(session_id),
                    latency_ms=metrics.tts_latency_ms,
                )

                # Publish TTS event to Bloodbank
                await self._publish_tts_event(event, llm_response.text, tts_response)
                metrics.event_published_at = datetime.utcnow()

                # Log final metrics
                logger.info(
                    "processing_completed",
                    session_id=str(session_id),
                    total_latency_ms=metrics.total_latency_ms,
                    llm_latency_ms=metrics.llm_latency_ms,
                    tts_latency_ms=metrics.tts_latency_ms,
                    latency_target_met=metrics.total_latency_ms < settings.max_processing_latency_ms,
                )

                # Store metrics for analysis
                self._metrics[str(session_id)] = metrics

            except json.JSONDecodeError as e:
                logger.error(
                    "invalid_json",
                    error=str(e),
                    body=message.body.decode()[:200],
                )
                # Don't requeue invalid JSON
                await message.reject(requeue=False)

            except Exception as e:
                logger.error(
                    "message_processing_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    session_id=str(session_id) if session_id else None,
                )
                # Reject and requeue for transient errors
                await message.reject(requeue=True)

    async def _publish_tts_event(
        self,
        original_event: TranscriptionEvent,
        response_text: str,
        tts_response: Any,
    ) -> None:
        """
        Publish TTS completion event to Bloodbank.

        Args:
            original_event: Original transcription event
            response_text: LLM response text
            tts_response: TTS response object
        """
        if not self.channel:
            raise RuntimeError("Channel not initialized")

        # Construct TTS event
        tts_event = TTSCompletedEvent(
            session_id=original_event.session_id,
            target=original_event.source,  # Send back to originating service
            payload={
                "response_text": response_text,
                "audio_base64": tts_response.audio_base64,
                "voice_id": tts_response.voice_id,
                "model_id": tts_response.model_id,
                "character_count": tts_response.character_count,
                "original_transcription": original_event.transcription_text,
            },
        )

        # Publish to exchange
        exchange = await self.channel.get_exchange(settings.bloodbank_exchange)
        await exchange.publish(
            aio_pika.Message(
                body=tts_event.model_dump_json().encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="tts.response.completed",
        )

        logger.info(
            "tts_event_published",
            event_id=str(tts_event.event_id),
            session_id=str(tts_event.session_id),
            routing_key="tts.response.completed",
        )
