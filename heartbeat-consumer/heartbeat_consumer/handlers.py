"""
Handler plugin interface and default handlers.

Handlers are pluggable functions that execute when a check is triggered.
Register custom handlers using the @register_handler decorator.

Handler signature:
    async def handler(tick_payload: dict, check_config: CheckConfig) -> dict:
        '''Execute the check and return result metadata.'''
        return {"status": "success", "details": {...}}
"""

import asyncio
from dataclasses import asdict
from typing import Callable, Awaitable

from .config import CheckConfig


# Registry of handler functions
_HANDLER_REGISTRY: dict[str, Callable[[dict, CheckConfig], Awaitable[dict]]] = {}


class HandlerRegistry:
    """Registry for pluggable heartbeat check handlers."""
    
    @staticmethod
    def register(name: str, fn: Callable[[dict, CheckConfig], Awaitable[dict]]) -> None:
        """Register a handler function."""
        _HANDLER_REGISTRY[name] = fn
    
    @staticmethod
    def get(name: str) -> Callable[[dict, CheckConfig], Awaitable[dict]] | None:
        """Get a handler by name."""
        return _HANDLER_REGISTRY.get(name)
    
    @staticmethod
    def list() -> list[str]:
        """List all registered handler names."""
        return list(_HANDLER_REGISTRY.keys())


def register_handler(name: str):
    """Decorator to register a handler function."""
    def decorator(fn: Callable[[dict, CheckConfig], Awaitable[dict]]):
        HandlerRegistry.register(name, fn)
        return fn
    return decorator


def get_handler(name: str) -> Callable[[dict, CheckConfig], Awaitable[dict]] | None:
    """Get a handler by name."""
    return HandlerRegistry.get(name)


# ============================================================================
# Default Handlers
# ============================================================================

@register_handler("sub_health")
async def handle_sub_health(tick_payload: dict, check_config: CheckConfig) -> dict:
    """
    Handler for sub-agent health monitoring.
    
    Emits agent status event to Bloodbank with current sub-agent states.
    """
    import json
    import os
    import subprocess
    import time
    import urllib.request
    from uuid import uuid4
    
    agent = tick_payload.get("agent", "unknown")
    BLOODBANK_API = os.environ.get("BLOODBANK_API", "http://127.0.0.1:8682")
    
    def publish_event(event_type: str, payload: dict) -> bool:
        body = json.dumps({
            "event_type": event_type,
            "event_id": str(uuid4()),
            "payload": payload,
            "source": {"host": os.uname().nodename, "type": "agent", "app": "heartbeat-consumer"},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "version": "1.0.0"
        }).encode()
        try:
            req = urllib.request.Request(
                f"{BLOODBANK_API}/events/custom",
                data=body, method="POST",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status == 200
        except Exception as e:
            return False
    
    # Get sub-agent status
    sub_agents = []
    try:
        out = subprocess.run(
            ["openclaw", "sessions", "list", "--json"],
            capture_output=True, text=True, timeout=10
        )
        if out.returncode == 0:
            data = json.loads(out.stdout)
            for sess in data.get("sessions", []):
                key = sess.get("key", "")
                if key.startswith("agent:"):
                    parts = key.split(":")
                    if len(parts) >= 2:
                        sub_agents.append({
                            "name": parts[1],
                            "status": sess.get("status", "unknown"),
                            "model": sess.get("model", "unknown"),
                            "tokens": sess.get("totalTokens", 0),
                        })
    except Exception as e:
        pass
    
    # Publish status event
    check_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    success = publish_event(f"agent.{agent}.sub_health", {
        "agent": agent,
        "sub_agents": sub_agents,
        "sub_agent_count": len(sub_agents),
        "check_time": check_time,
    })
    
    return {
        "status": "success" if success else "failed",
        "sub_agents_checked": len(sub_agents),
        "check_time": check_time,
    }


@register_handler("quarterly_compaction")
async def handle_quarterly_compaction(tick_payload: dict, check_config: CheckConfig) -> dict:
    """
    Placeholder handler for quarterly compaction.
    
    Triggers memory compaction at quarter boundaries.
    Override this with agent-specific implementation.
    """
    from datetime import datetime
    
    now = datetime.utcnow()
    quarter = f"Q{(now.month - 1) // 3 + 1}"
    
    # Check if this quarter is in the trigger list
    if check_config.trigger_on_quarters and quarter not in check_config.trigger_on_quarters:
        return {
            "status": "skipped",
            "reason": f"Quarter {quarter} not in trigger list",
        }
    
    # Placeholder - implement agent-specific compaction logic
    return {
        "status": "success",
        "quarter": quarter,
        "action": "compaction_triggered",
        "note": "Implement agent-specific compaction logic",
    }


@register_handler("default")
async def handle_default(tick_payload: dict, check_config: CheckConfig) -> dict:
    """Default no-op handler."""
    return {
        "status": "success",
        "note": "No handler registered for this check",
        "handler": check_config.handler,
    }
