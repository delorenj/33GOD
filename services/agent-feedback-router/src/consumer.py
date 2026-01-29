"""
Agent Feedback Router - FastStream Consumer

Subscribes to agent.feedback.requested events and routes them to AgentForge.
Publishes agent.feedback.response events with correlation tracking.

Migrated from legacy EventConsumer to FastStream per ADR-0002.
"""

import logging
from typing import Any, Dict

import httpx
from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, ExchangeType

from event_producers.config import settings as bloodbank_settings
from event_producers.events.base import EventEnvelope, Source, TriggerType, create_envelope
from event_producers.events.domains.agent.feedback import (
    AgentFeedbackRequested,
    AgentFeedbackResponse,
)
from event_producers.rabbit import Publisher

from .config import settings

logger = logging.getLogger(__name__)

# Initialize broker and FastStream app
broker = RabbitBroker(bloodbank_settings.rabbit_url)
app = FastStream(broker)

# Initialize publisher for response events
publisher = Publisher(enable_correlation_tracking=True)


@app.after_startup
async def startup():
    """Initialize publisher connection on app startup."""
    await publisher.start()
    logger.info("Agent Feedback Router started")


@app.after_shutdown
async def shutdown():
    """Close publisher connection on app shutdown."""
    await publisher.close()
    logger.info("Agent Feedback Router shutdown")


@broker.subscriber(
    queue=RabbitQueue(
        name="services.agent.feedback_router",
        routing_key="agent.feedback.requested",
        durable=True,
    ),
    exchange=RabbitExchange(
        name=bloodbank_settings.exchange_name,
        type=ExchangeType.TOPIC,
        durable=True,
    ),
)
async def handle_feedback_request(message_dict: Dict[str, Any]):
    """
    Handle agent.feedback.requested events.

    Unwraps EventEnvelope, calls AgentForge API, and publishes response.
    Follows ADR-0002: explicit envelope unwrapping pattern.
    """
    # Unwrap EventEnvelope
    envelope = EventEnvelope(**message_dict)
    request = AgentFeedbackRequested(**envelope.payload)

    logger.info(
        "Received feedback request for agent %s (correlation: %s)",
        request.agent_id,
        envelope.event_id,
    )

    response_text = ""
    error_message = None
    status = "ok"

    try:
        response_text = await _request_feedback(request)
        logger.info("Feedback request succeeded for agent %s", request.agent_id)
    except Exception as exc:
        status = "error"
        error_message = str(exc)
        logger.error(
            "Feedback request failed for agent %s: %s",
            request.agent_id,
            error_message,
            exc_info=True,
        )

    # Build response payload
    response_payload = AgentFeedbackResponse(
        agent_id=request.agent_id,
        letta_agent_id=request.letta_agent_id,
        response=response_text,
        status=status,
        error_message=error_message,
    )

    # Publish response with correlation tracking
    response_envelope = create_envelope(
        event_type="agent.feedback.response",
        payload=response_payload,
        source=Source(
            host="agent-feedback-router",
            type=TriggerType.AGENT,
            app="agent-feedback-router",
        ),
        correlation_ids=[envelope.event_id],
    )

    await publisher.publish(
        routing_key="agent.feedback.response",
        body=response_envelope.model_dump(),
        event_id=response_envelope.event_id,
        parent_event_ids=[envelope.event_id],
    )

    logger.info(
        "Published feedback response (correlation: %s -> %s)",
        envelope.event_id,
        response_envelope.event_id,
    )


async def _request_feedback(request: AgentFeedbackRequested) -> str:
    """
    Call AgentForge API to send message to agent and get response.

    Args:
        request: Validated feedback request payload

    Returns:
        Agent's response text

    Raises:
        httpx.HTTPStatusError: If API call fails
    """
    url = f"{settings.agentforge_api_url}/agents/{request.agent_id}/messages"

    payload = {"message": request.message}
    if request.letta_agent_id:
        payload["letta_agent_id"] = request.letta_agent_id
    if request.context:
        payload["context"] = request.context

    headers = {}
    if settings.agentforge_api_token:
        headers["Authorization"] = f"Bearer {settings.agentforge_api_token}"

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    return data.get("assistant", "")
