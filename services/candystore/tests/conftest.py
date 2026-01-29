"""Pytest configuration and fixtures for event-store-manager tests."""

import os

# Set required env vars BEFORE any src imports (settings loads at import time)
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_events")
os.environ.setdefault("RABBITMQ_URL", "amqp://test:test@localhost:5672")
