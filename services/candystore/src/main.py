"""Event Store Manager - The Historian service entrypoint."""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import routes
from .config import settings
from .consumer import EventConsumer

# Configure stdlib logging FIRST so structlog has handlers to write to
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
        if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global consumer instance
consumer: EventConsumer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown."""
    global consumer

    logger.info(
        "starting_event_store_manager",
        environment=settings.environment,
        database_url=settings.database_url.split("@")[-1],  # Hide credentials
    )

    # Initialize consumer
    consumer = EventConsumer()

    # Set event store in routes
    routes.set_event_store(consumer.event_store)

    # Start consuming events in background with error surfacing
    async def _run_consumer() -> None:
        try:
            await consumer.start()
        except Exception as exc:
            logger.error("consumer_fatal_error", error=str(exc), error_type=type(exc).__name__)
            raise

    consumer_task = asyncio.create_task(_run_consumer())

    # Add callback to surface task exceptions immediately
    def _on_consumer_done(task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            logger.error("consumer_task_failed", error=str(exc))

    consumer_task.add_done_callback(_on_consumer_done)

    logger.info("event_store_manager_started")

    try:
        yield
    finally:
        # Shutdown
        logger.info("shutting_down_event_store_manager")

        if consumer:
            await consumer.stop()

        # Cancel consumer task
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

        logger.info("event_store_manager_stopped")


# Create FastAPI app
app = FastAPI(
    title="Event Store Manager",
    description="The Historian - Persists all Bloodbank events to PostgreSQL",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(routes.router, prefix=settings.api_prefix)

# Also mount health check at root for easier discovery
app.include_router(routes.router, tags=["health"])


def handle_signal(signum: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    logger.info("received_shutdown_signal", signal=signum)
    sys.exit(0)


def main() -> None:
    """Run the Event Store Manager service."""
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Run uvicorn server
    uvicorn.run(
        "src.main:app",
        host=settings.event_store_manager_host,
        port=settings.event_store_manager_port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",
    )


if __name__ == "__main__":
    main()
