"""Main application entry point for Tonny Agent."""

import asyncio
import signal
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI

from .config import settings
from .consumer import TonnyConsumer

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger(__name__)


# Global consumer instance
consumer: TonnyConsumer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown of Bloodbank consumer.
    """
    global consumer

    logger.info("tonny_agent_starting", version="0.1.0")

    # Start consumer
    consumer = TonnyConsumer()
    asyncio.create_task(consumer.start())

    logger.info("tonny_agent_ready")

    yield

    # Shutdown consumer
    logger.info("tonny_agent_shutting_down")
    if consumer:
        await consumer.stop()

    logger.info("tonny_agent_stopped")


# Create FastAPI app
app = FastAPI(
    title="Tonny Agent",
    description="Letta-powered AI agent for processing voice transcriptions",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "tonny-agent",
        "version": "0.1.0",
    }


@app.get("/metrics")
async def get_metrics():
    """
    Get processing metrics.

    Returns statistics about event processing latency.
    """
    if not consumer:
        return {"error": "Consumer not initialized"}

    metrics_data = []
    for session_id, metrics in consumer._metrics.items():
        metrics_data.append({
            "session_id": session_id,
            "total_latency_ms": metrics.total_latency_ms,
            "llm_latency_ms": metrics.llm_latency_ms,
            "tts_latency_ms": metrics.tts_latency_ms,
            "transcription_received_at": metrics.transcription_received_at.isoformat(),
            "event_published_at": metrics.event_published_at.isoformat(),
        })

    return {
        "total_sessions": len(metrics_data),
        "sessions": metrics_data[-50:],  # Last 50 sessions
    }


def main():
    """Run the Tonny Agent service."""
    uvicorn.run(
        "src.main:app",
        host=settings.service_host,
        port=settings.service_port,
        log_level=settings.log_level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()
