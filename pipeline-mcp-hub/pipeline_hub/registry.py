"""Domain registry — the internal index the discovery/dispatcher tools sit on top of.

Holds `(domain -> {tool_name -> Tool})`, materialized lazily on first use and cached.
Per-domain load failures are isolated so one broken domain doesn't take down the hub.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastmcp.tools.tool import Tool, ToolResult

from pipeline_hub.domains.base import Domain

logger = logging.getLogger("pipeline_hub.registry")


class DomainRegistry:
    def __init__(self) -> None:
        self._domains: dict[str, Domain] = {}
        self._tools: dict[str, dict[str, Tool]] = {}
        self._errors: dict[str, str] = {}
        self._loaded = False
        self._lock = asyncio.Lock()

    def register(self, domain: Domain) -> None:
        self._domains[domain.name] = domain

    async def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        async with self._lock:
            if self._loaded:
                return
            for name, domain in self._domains.items():
                try:
                    self._tools[name] = await domain.load_tools()
                except Exception as exc:  # noqa: BLE001 - isolate per-domain failures
                    self._tools[name] = {}
                    self._errors[name] = f"{type(exc).__name__}: {exc}"
                    logger.exception("Failed to load domain '%s'", name)
            self._loaded = True

    async def list_domains(self) -> list[dict[str, Any]]:
        await self._ensure_loaded()
        out: list[dict[str, Any]] = []
        for name, domain in self._domains.items():
            entry: dict[str, Any] = {
                "domain": name,
                "title": domain.title,
                "description": domain.description,
                "tool_count": len(self._tools.get(name, {})),
                "status": "error" if name in self._errors else "ok",
            }
            if name in self._errors:
                entry["error"] = self._errors[name]
            out.append(entry)
        return out

    async def list_domain_tools(self, domain: str) -> list[dict[str, Any]]:
        await self._ensure_loaded()
        self._require_domain(domain)
        tools = self._tools.get(domain, {})
        return [
            {
                "name": name,
                "description": tool.description or "",
                "input_schema": tool.parameters,
            }
            for name, tool in sorted(tools.items())
        ]

    async def call(self, domain: str, tool: str, arguments: dict[str, Any]) -> Any:
        await self._ensure_loaded()
        self._require_domain(domain)
        tools = self._tools.get(domain, {})
        if tool not in tools:
            available = ", ".join(sorted(tools)) or "(none)"
            raise ValueError(
                f"Unknown tool '{tool}' in domain '{domain}'. "
                f"Call list_domain_tools('{domain}') to see options. Available: {available}"
            )
        result: ToolResult = await tools[tool].run(arguments)
        return self._unwrap(result)

    def _require_domain(self, domain: str) -> None:
        if domain not in self._domains:
            available = ", ".join(sorted(self._domains)) or "(none)"
            raise ValueError(
                f"Unknown domain '{domain}'. Call list_domains() first. Available: {available}"
            )
        if domain in self._errors:
            raise ValueError(
                f"Domain '{domain}' failed to load and is unavailable: {self._errors[domain]}"
            )

    @staticmethod
    def _unwrap(result: ToolResult) -> Any:
        """Map a ToolResult to a plain JSON-serializable value for re-return by the hub."""
        if result.structured_content is not None:
            return result.structured_content
        texts = [getattr(block, "text", None) for block in result.content]
        texts = [t for t in texts if t is not None]
        if len(texts) == 1:
            return texts[0]
        return texts or None
