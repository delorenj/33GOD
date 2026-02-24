"""
GOD-11 MIG-1 — hookd Compatibility Bridge

Thin HTTP shim that accepts legacy OpenClaw hook payloads and translates them
into CommandEnvelopes published on Bloodbank. This is a TRANSITIONAL component:
once all callers publish commands directly, this bridge is deprecated.

Architecture (from COMMAND-SYSTEM-RFC.md §6):

    Legacy path:    OpenClaw hook → agent session (direct)
    New path:       OpenClaw hook → hookd-bridge → CommandEnvelope → Bloodbank → agent adapter

The bridge:
  1. Accepts existing hook payloads at the same endpoint format
  2. Wraps them in a CommandEnvelope with:
     - command_id: generated UUID
     - target_agent: from hook path
     - issued_by: "hookd-bridge"
     - action: inferred from hook path/payload
     - correlation_id: from header or generated
  3. Publishes to command.{agent}.{action} on Bloodbank
  4. Returns 202 Accepted (async, no result awaited)

Requires:
  - AMQP connection (RABBITMQ_URL or HOOKD_AMQP_URL)
  - Holyfields schemas for validation (optional, degrades gracefully)
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import aio_pika
from fastapi import FastAPI, Header, Request, Response
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AMQP_URL = os.environ.get(
    "HOOKD_AMQP_URL",
    os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2f"),
)
EXCHANGE_NAME = os.environ.get("HOOKD_EXCHANGE", "bloodbank.events.v1")
BRIDGE_HOST = os.environ.get("BRIDGE_HOST", "0.0.0.0")
BRIDGE_PORT = int(os.environ.get("BRIDGE_PORT", "8099"))
DEFAULT_TTL_MS = 30_000  # 30s, matches envelope.v1.json default


# ---------------------------------------------------------------------------
# Models (mirrors Holyfields command schemas)
# ---------------------------------------------------------------------------

class CommandPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class EventSource(BaseModel):
    host: str = Field(default_factory=lambda: os.uname().nodename)
    app: str = "hookd-bridge"
    trigger_type: str = "webhook"
    user_id: Optional[str] = None


class CommandPayload(BaseModel):
    command_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_agent: str
    issued_by: str = "hookd-bridge"
    action: str
    priority: CommandPriority = CommandPriority.NORMAL
    ttl_ms: int = DEFAULT_TTL_MS
    idempotency_key: Optional[str] = None
    command_payload: dict[str, Any] = Field(default_factory=dict)


class CommandEnvelope(BaseModel):
    """Wire-level command envelope per holyfields/schemas/command/envelope.v1.json"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "command.envelope"
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    version: str = "1.0.0"
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: Optional[str] = None
    source: EventSource = Field(default_factory=EventSource)
    payload: CommandPayload


# ---------------------------------------------------------------------------
# Hook → Command mapping
# ---------------------------------------------------------------------------

# Known hook path patterns and their command action mappings
HOOK_ACTION_MAP: dict[str, str] = {
    "heartbeat": "process_heartbeat",
    "heartbeat.tick": "process_heartbeat",
    "system.heartbeat.tick": "process_heartbeat",
    "webhook": "process_webhook",
    "task": "execute_task",
    "task.assign": "execute_task",
    "message": "process_message",
    "notify": "send_notification",
    "drift_check": "run_drift_check",
    "health_check": "run_health_check",
}


def infer_action(hook_path: str, payload: dict[str, Any]) -> str:
    """
    Infer the command action from the hook path or payload.

    Priority:
      1. Explicit 'action' field in payload
      2. Known hook path mapping
      3. Fallback to sanitized hook path
    """
    # Explicit action in payload takes precedence
    if "action" in payload:
        return str(payload["action"])

    # Try known mappings
    normalized = hook_path.strip("/").lower().replace("/", ".")
    for pattern, action in HOOK_ACTION_MAP.items():
        if pattern in normalized:
            return action

    # Fallback: use the hook path as the action (sanitized)
    return normalized.replace(".", "_").replace("-", "_") or "unknown"


def infer_agent(hook_path: str, payload: dict[str, Any]) -> str:
    """
    Infer the target agent from the hook path or payload.

    Hook paths typically follow: /hooks/{agent} or /hooks/agent/{agent_name}
    """
    if "target_agent" in payload:
        return str(payload["target_agent"])
    if "agent" in payload:
        return str(payload["agent"])
    if "agent_name" in payload:
        return str(payload["agent_name"])

    # Parse from path: /hooks/{agent}/... or /hooks/agent/{name}
    parts = [p for p in hook_path.strip("/").split("/") if p]
    if len(parts) >= 2 and parts[0] == "hooks":
        if parts[1] == "agent" and len(parts) >= 3:
            return parts[2]
        return parts[1]

    return "unknown"


def infer_priority(payload: dict[str, Any]) -> CommandPriority:
    """Infer priority from payload hints."""
    if payload.get("priority"):
        try:
            return CommandPriority(payload["priority"])
        except ValueError:
            pass
    # Heartbeats are low priority; everything else normal
    if payload.get("event_type", "").startswith("system.heartbeat"):
        return CommandPriority.LOW
    return CommandPriority.NORMAL


def hook_to_command(
    hook_path: str,
    payload: dict[str, Any],
    correlation_id: Optional[str] = None,
) -> CommandEnvelope:
    """
    Transform a legacy hook call into a CommandEnvelope.

    This is the core translation layer. It maps the unstructured hook
    format into the typed command system defined by COMMAND-SYSTEM-RFC.md.
    """
    agent = infer_agent(hook_path, payload)
    action = infer_action(hook_path, payload)
    priority = infer_priority(payload)

    # Strip metadata fields from the command_payload to avoid duplication
    command_data = {
        k: v for k, v in payload.items()
        if k not in {"target_agent", "agent", "agent_name", "action", "priority"}
    }

    return CommandEnvelope(
        correlation_id=correlation_id or str(uuid.uuid4()),
        causation_id=None,  # Root command (no prior cause)
        source=EventSource(user_id=payload.get("issued_by")),
        payload=CommandPayload(
            target_agent=agent,
            issued_by=payload.get("issued_by", "hookd-bridge"),
            action=action,
            priority=priority,
            ttl_ms=int(payload.get("ttl_ms", DEFAULT_TTL_MS)),
            idempotency_key=payload.get("idempotency_key"),
            command_payload=command_data,
        ),
    )


# ---------------------------------------------------------------------------
# AMQP Publisher
# ---------------------------------------------------------------------------

class BridgePublisher:
    """Async AMQP publisher for command envelopes."""

    def __init__(self):
        self._connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None
        self._exchange: Optional[aio_pika.abc.AbstractExchange] = None

    async def connect(self):
        self._connection = await aio_pika.connect_robust(AMQP_URL)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            EXCHANGE_NAME,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

    async def close(self):
        if self._connection:
            await self._connection.close()

    async def publish(self, envelope: CommandEnvelope) -> str:
        """
        Publish a CommandEnvelope to Bloodbank.

        Routing key: command.{target_agent}.{action}
        Returns: the routing key used
        """
        if not self._exchange:
            raise RuntimeError("Publisher not connected. Call connect() first.")

        routing_key = (
            f"command.{envelope.payload.target_agent}.{envelope.payload.action}"
        )

        body = envelope.model_dump_json().encode()

        await self._exchange.publish(
            aio_pika.Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                message_id=envelope.event_id,
                correlation_id=envelope.correlation_id,
                timestamp=datetime.now(timezone.utc),
            ),
            routing_key=routing_key,
        )

        return routing_key


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

publisher = BridgePublisher()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await publisher.connect()
    yield
    await publisher.close()


app = FastAPI(
    title="hookd-bridge",
    description="MIG-1: Legacy hook → CommandEnvelope compatibility bridge",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "component": "hookd-bridge",
        "exchange": EXCHANGE_NAME,
        "connected": publisher._exchange is not None,
    }


@app.post("/hooks/{agent_path:path}", status_code=202)
async def hook_endpoint(
    agent_path: str,
    request: Request,
    x_correlation_id: Optional[str] = Header(None),
    x_request_id: Optional[str] = Header(None),
):
    """
    Accept legacy hook payloads and publish as CommandEnvelopes.

    Endpoint mirrors the existing OpenClaw hook format:
      POST /hooks/{agent}
      POST /hooks/agent/{name}
      POST /hooks/{agent}/{action}

    Returns 202 Accepted immediately (fire-and-forget).
    """
    try:
        body = await request.json()
    except Exception:
        return Response(
            content='{"error": "invalid JSON body"}',
            status_code=400,
            media_type="application/json",
        )

    correlation_id = x_correlation_id or x_request_id

    # Translate hook → command
    hook_path = f"/hooks/{agent_path}"
    envelope = hook_to_command(hook_path, body, correlation_id)

    # Publish to Bloodbank
    try:
        routing_key = await publisher.publish(envelope)
    except Exception as e:
        return Response(
            content=json.dumps({"error": "publish_failed", "detail": str(e)}),
            status_code=502,
            media_type="application/json",
        )

    return {
        "accepted": True,
        "command_id": envelope.payload.command_id,
        "routing_key": routing_key,
        "correlation_id": envelope.correlation_id,
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "bridge:app",
        host=BRIDGE_HOST,
        port=BRIDGE_PORT,
        log_level="info",
    )
