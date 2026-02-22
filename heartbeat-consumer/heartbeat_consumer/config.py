"""
Configuration models and heartbeat.json loader.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Any, Optional


@dataclass
class WindowConfig:
    """Time window for when a check can run."""
    start: str  # HH:MM format
    end: str  # HH:MM format
    tz: str = "America/New_York"

    def is_within(self, dt: datetime) -> bool:
        """Check if datetime falls within this window."""
        import pytz
        tz = pytz.timezone(self.tz)
        local_dt = dt.astimezone(tz)
        current_time = local_dt.time()
        start_time = datetime.strptime(self.start, "%H:%M").time()
        end_time = datetime.strptime(self.end, "%H:%M").time()
        
        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:
            # Window spans midnight
            return current_time >= start_time or current_time <= end_time


@dataclass
class CheckConfig:
    """Configuration for a single heartbeat check."""
    cadence_ms: int
    handler: str
    priority: int = 1
    enabled: bool = True
    last_run: int = 0
    window: Optional[WindowConfig] = None
    # Optional fields for specialized checks
    trigger_on_quarters: Optional[list[str]] = None  # ["Q1", "Q2", "Q3", "Q4"]
    meta: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "CheckConfig":
        """Parse check config from dict."""
        window = None
        if "window" in data:
            window = WindowConfig(**data["window"])
        
        return cls(
            cadence_ms=data.get("cadenceMs", 900000),
            handler=data.get("handler", "default"),
            priority=data.get("priority", 1),
            enabled=data.get("enabled", True),
            last_run=data.get("lastRun", 0),
            window=window,
            trigger_on_quarters=data.get("triggerOnQuarters"),
            meta=data.get("meta", {}),
        )

    def to_dict(self) -> dict:
        """Serialize to dict for saving."""
        result = {
            "cadenceMs": self.cadence_ms,
            "window": {
                "start": self.window.start,
                "end": self.window.end,
                "tz": self.window.tz,
            } if self.window else None,
            "lastRun": self.last_run,
            "priority": self.priority,
            "handler": self.handler,
            "enabled": self.enabled,
        }
        if self.trigger_on_quarters:
            result["triggerOnQuarters"] = self.trigger_on_quarters
        if self.meta:
            result["meta"] = self.meta
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class HeartbeatConfig:
    """Root configuration loaded from heartbeat.json."""
    schema_version: str
    agent: str
    checks: dict[str, CheckConfig]
    paused: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "HeartbeatConfig":
        """Load configuration from heartbeat.json file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Heartbeat config not found: {path}")
        
        with open(path, "r") as f:
            data = json.load(f)
        
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "HeartbeatConfig":
        """Parse config from dict."""
        checks = {
            name: CheckConfig.from_dict(check_data)
            for name, check_data in data.get("checks", {}).items()
        }
        
        return cls(
            schema_version=data.get("$schema", "heartbeat.v1"),
            agent=data.get("agent", "unknown"),
            checks=checks,
            paused=data.get("paused", {}),
        )

    def to_dict(self) -> dict:
        """Serialize to dict for saving."""
        return {
            "$schema": self.schema_version,
            "agent": self.agent,
            "checks": {name: check.to_dict() for name, check in self.checks.items()},
            "paused": self.paused,
        }

    def save(self, path: str | Path) -> None:
        """Save configuration to heartbeat.json file."""
        path = Path(path)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def find_overdue_check(self, now_ms: int) -> Optional[tuple[str, CheckConfig, float]]:
        """
        Find the most overdue check based on current time.
        
        Returns tuple of (check_name, check_config, overdue_ratio) or None.
        Most overdue = highest ratio > 1.0, tie-broken by priority.
        """
        import pytz
        
        candidates = []
        now_dt = datetime.fromtimestamp(now_ms / 1000, tz=pytz.UTC)
        
        for name, check in self.checks.items():
            if not check.enabled:
                continue
            
            # Check time window if defined
            if check.window and not check.window.is_within(now_dt):
                continue
            
            # Calculate overdue ratio
            elapsed = now_ms - check.last_run
            ratio = elapsed / check.cadence_ms if check.cadence_ms > 0 else float('inf')
            
            if ratio > 1.0:
                candidates.append((name, check, ratio))
        
        if not candidates:
            return None
        
        # Sort by ratio desc, then priority asc (lower number = higher priority)
        candidates.sort(key=lambda x: (-x[2], x[1].priority))
        return candidates[0]
