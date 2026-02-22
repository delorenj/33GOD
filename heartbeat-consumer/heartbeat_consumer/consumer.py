"""
FastStream-based heartbeat consumer for per-agent message processing.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from faststream import FastStream, Logger
from faststream.rabbit import RabbitBroker, RabbitQueue, RabbitExchange

from .config import HeartbeatConfig, CheckConfig
from .handlers import get_handler, handle_sub_health, handle_quarterly_compaction, register_handler


logger = logging.getLogger("heartbeat_consumer")


class HeartbeatConsumer:
    """
    FastStream consumer for agent heartbeat messages.
    
    Each agent runs one consumer that:
    - Listens on queue `agent.{name}.inbox`
    - Binds to routing keys: `agent.{name}.#` AND `system.heartbeat.#`
    - On system.heartbeat.tick: checks local heartbeat.json for overdue checks
    - Executes the most overdue check and updates lastRun timestamp
    """
    
    def __init__(
        self,
        agent_name: str,
        heartbeat_path: str | Path,
        rabbit_url: str = "amqp://delorenj:delorenj@localhost:5673/",
        exchange_name: str = "bloodbank.events.v1",
    ):
        self.agent_name = agent_name
        self.heartbeat_path = Path(heartbeat_path)
        self.rabbit_url = rabbit_url
        self.exchange_name = exchange_name
        
        # Queue names
        self.queue_name = f"agent.{agent_name}.inbox"
        self.dlq_name = f"agent.{agent_name}.dlq"
        
        # Config loaded at startup and reloaded on each tick
        self.config: HeartbeatConfig | None = None
        
        # FastStream broker and app
        self.broker = RabbitBroker(rabbit_url, max_consumers=1)
        self.app = FastStream(self.broker, title=f"Heartbeat Consumer - {agent_name}")
        
        # Register handlers
        self._register_routes()
    
    def _load_config(self) -> HeartbeatConfig:
        """Load or reload heartbeat configuration."""
        return HeartbeatConfig.load(self.heartbeat_path)
    
    def _save_config(self) -> None:
        """Save updated heartbeat configuration."""
        if self.config:
            self.config.save(self.heartbeat_path)
    
    def _register_routes(self) -> None:
        """Register FastStream message handlers."""
        
        @self.broker.subscriber(
            RabbitQueue(
                self.queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": self.dlq_name,
                },
            ),
            RabbitExchange(self.exchange_name, type="topic"),
            routing_key=f"agent.{self.agent_name}.#",
        )
        async def handle_agent_message(
            routing_key: str,
            body: dict,
            logger: Logger,
        ) -> None:
            """Handle messages routed to this agent's inbox."""
            logger.info(f"Received agent message: {routing_key}")
            # Agent-specific message handling - override in subclass or add handlers
            await self._handle_agent_message(routing_key, body)
        
        @self.broker.subscriber(
            RabbitQueue(
                self.queue_name,
                durable=True,
            ),
            RabbitExchange(self.exchange_name, type="topic"),
            routing_key="system.heartbeat.#",
        )
        async def handle_system_heartbeat(
            routing_key: str,
            body: dict,
            logger: Logger,
        ) -> None:
            """Handle system heartbeat tick."""
            if routing_key == "system.heartbeat.tick":
                await self._process_heartbeat_tick(body, logger)
            else:
                logger.debug(f"Ignoring heartbeat routing key: {routing_key}")
    
    async def _handle_agent_message(self, routing_key: str, body: dict) -> None:
        """
        Override this method to handle agent-specific messages.
        Called for messages matching agent.{name}.#
        """
        logger.info(f"Agent message on {routing_key}: {body.get('event_type', 'unknown')}")
    
    async def _process_heartbeat_tick(self, envelope: dict, logger: Logger) -> None:
        """
        Process a heartbeat tick: check for overdue checks and execute.
        
        Flow:
        1. Reload heartbeat.json
        2. Calculate overdueRatio for each enabled check
        3. Find most overdue check (ratio > 1.0, highest priority)
        4. If overdue: call handler, update lastRun, save config
        5. If nothing overdue: no-op (zero cost)
        """
        try:
            # Reload config fresh each tick
            self.config = self._load_config()
            
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            
            # Find most overdue check
            overdue = self.config.find_overdue_check(now_ms)
            
            if not overdue:
                logger.debug("No overdue checks - heartbeat no-op")
                return
            
            check_name, check_config, ratio = overdue
            
            logger.info(
                f"Executing check '{check_name}' "
                f"(overdue_ratio={ratio:.2f}, priority={check_config.priority})"
            )
            
            # Get handler
            handler = get_handler(check_config.handler)
            if not handler:
                logger.warning(f"No handler registered for '{check_config.handler}', using default")
                handler = get_handler("default")
            
            # Execute handler
            tick_payload = {
                "agent": self.agent_name,
                "check_name": check_name,
                "timestamp": now_ms,
                "envelope": envelope,
            }
            
            try:
                result = await handler(tick_payload, check_config)
                logger.info(f"Check '{check_name}' completed: {result.get('status', 'unknown')}")
                
                # Update lastRun on success
                if result.get("status") in ("success", "skipped"):
                    check_config.last_run = now_ms
                    self._save_config()
                    
            except Exception as e:
                logger.error(f"Handler '{check_config.handler}' failed: {e}")
                # Don't update lastRun on failure - will retry on next tick
                
        except FileNotFoundError:
            logger.error(f"heartbeat.json not found at {self.heartbeat_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in heartbeat.json: {e}")
        except Exception as e:
            logger.error(f"Unexpected error processing heartbeat: {e}")
    
    async def run(self) -> None:
        """Start the consumer."""
        logger.info(f"Starting heartbeat consumer for agent '{self.agent_name}'")
        logger.info(f"Queue: {self.queue_name}")
        logger.info(f"Config: {self.heartbeat_path}")
        
        # Validate config at startup
        try:
            self.config = self._load_config()
            logger.info(f"Loaded config with {len(self.config.checks)} checks")
        except FileNotFoundError:
            logger.warning(f"No heartbeat.json found at {self.heartbeat_path}")
        
        await self.app.run()
    
    def run_sync(self) -> None:
        """Run the consumer synchronously (blocking)."""
        import asyncio
        asyncio.run(self.run())
