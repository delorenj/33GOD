"""Letta agent integration for processing transcriptions."""

import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID

import httpx
import structlog

from .config import settings
from .models import LLMResponse

logger = structlog.get_logger(__name__)


class LettaAgent:
    """
    Letta agent wrapper for stateful conversation processing.

    Uses Letta's Python SDK pattern for self-hosted instances.
    """

    def __init__(self) -> None:
        """Initialize Letta agent client."""
        self.base_url = settings.letta_base_url
        self.api_key = settings.letta_api_key
        self.agent_id: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """
        Initialize Letta client and create agent if needed.

        For self-hosted Letta, we use direct HTTP calls rather than SDK
        to avoid dependency issues. Production would use letta Python SDK.
        """
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0,
        )

        try:
            # Check if Tonny agent already exists
            response = await self._client.get("/api/agents")
            response.raise_for_status()
            agents = response.json()

            tonny_agent = next(
                (a for a in agents if a.get("name") == "tonny-voice-assistant"),
                None,
            )

            if tonny_agent:
                self.agent_id = tonny_agent["id"]
                logger.info("letta_agent_found", agent_id=self.agent_id)
            else:
                # Create new agent
                self.agent_id = await self._create_agent()
                logger.info("letta_agent_created", agent_id=self.agent_id)

        except Exception as e:
            logger.error("letta_initialization_failed", error=str(e))
            raise

    async def _create_agent(self) -> str:
        """
        Create a new Letta agent configured for voice assistant tasks.

        Returns agent ID.
        """
        if not self._client:
            raise RuntimeError("Client not initialized")

        # Create agent with voice-optimized persona
        agent_config = {
            "name": "tonny-voice-assistant",
            "persona": (
                "You are Tonny, a helpful voice assistant. "
                "You respond concisely and naturally to voice commands. "
                "Keep responses brief and conversational - users are speaking, not typing."
            ),
            "human": (
                "The user is speaking to you via voice transcription. "
                "They expect quick, spoken-style responses."
            ),
            "llm_config": {
                "model": settings.llm_model,
                "context_window": 8000,
            },
            "embedding_config": {
                "model": settings.embedding_model,
            },
        }

        response = await self._client.post("/api/agents", json=agent_config)
        response.raise_for_status()
        agent_data = response.json()

        return agent_data["id"]

    async def process_message(
        self,
        text: str,
        session_id: UUID,
    ) -> LLMResponse:
        """
        Process transcribed text through Letta agent.

        Args:
            text: Transcribed user message
            session_id: Session ID for context tracking

        Returns:
            LLM response with agent output
        """
        if not self._client or not self.agent_id:
            raise RuntimeError("Agent not initialized")

        start_time = datetime.utcnow()

        try:
            # Send message to agent
            # In Letta, messages are sent as single strings, not conversation history
            # The agent maintains state internally
            response = await self._client.post(
                f"/api/agents/{self.agent_id}/messages",
                json={
                    "message": text,
                    "session_id": str(session_id),
                },
            )
            response.raise_for_status()
            result = response.json()

            # Extract assistant response
            # Letta returns messages array with assistant replies
            assistant_messages = [
                msg for msg in result.get("messages", [])
                if msg.get("role") == "assistant"
            ]

            if not assistant_messages:
                raise ValueError("No assistant response in Letta output")

            response_text = assistant_messages[-1].get("content", "")

            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(
                "letta_processing_completed",
                session_id=str(session_id),
                processing_time_ms=processing_time,
                input_length=len(text),
                output_length=len(response_text),
            )

            return LLMResponse(
                text=response_text,
                agent_id=self.agent_id,
                session_id=session_id,
                processing_time_ms=processing_time,
                model=settings.llm_model,
            )

        except httpx.HTTPError as e:
            logger.error(
                "letta_http_error",
                error=str(e),
                status_code=getattr(e.response, "status_code", None),
            )
            raise
        except Exception as e:
            logger.error("letta_processing_error", error=str(e), error_type=type(e).__name__)
            raise

    async def shutdown(self) -> None:
        """Close Letta client connection."""
        if self._client:
            await self._client.aclose()
            logger.info("letta_client_closed")


# Global agent instance
_agent: Optional[LettaAgent] = None


async def get_agent() -> LettaAgent:
    """Get or create global Letta agent instance."""
    global _agent
    if _agent is None:
        _agent = LettaAgent()
        await _agent.initialize()
    return _agent


async def shutdown_agent() -> None:
    """Shutdown global agent instance."""
    global _agent
    if _agent:
        await _agent.shutdown()
        _agent = None
