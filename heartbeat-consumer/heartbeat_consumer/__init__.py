"""
Heartbeat Consumer Template for 33GOD Bloodbank

A FastStream-based consumer that handles per-agent heartbeats with pluggable
check handlers. Each agent runs this consumer to process system heartbeat ticks
and execute scheduled checks based on their local heartbeat.json configuration.
"""

__version__ = "1.0.0"
__all__ = [
    "HeartbeatConsumer",
    "HeartbeatConfig",
    "CheckConfig",
    "HandlerRegistry",
    "register_handler",
    "get_handler",
]

from .consumer import HeartbeatConsumer
from .config import HeartbeatConfig, CheckConfig, WindowConfig
from .handlers import HandlerRegistry, register_handler, get_handler, handle_health_report, handle_quarterly_compaction
