"""The hub's client-facing surface: the ONLY tools an MCP client ever sees.

This is the "discovery + dispatcher gating" pattern: cheap, stable, client-agnostic.
Domain tool schemas are not in context until the model calls `list_domain_tools`.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from pipeline_hub.registry import DomainRegistry


def register_hub_tools(mcp: FastMCP, registry: DomainRegistry) -> None:
    @mcp.tool()
    async def list_domains() -> list[dict[str, Any]]:
        """List the tool domains available in this hub. START HERE.

        Each domain bundles many underlying tools that are intentionally NOT loaded
        into your context yet. Returns each domain's name, title, description,
        tool_count, and load status. To use a domain, call
        list_domain_tools(domain) to load its tool schemas, then invoke a tool with
        call_domain_tool(domain, tool, arguments).
        """
        return await registry.list_domains()

    @mcp.tool()
    async def list_domain_tools(domain: str) -> list[dict[str, Any]]:
        """Load and list the tools in a domain, each with its name, description, and input_schema.

        Call this only for a domain you actually intend to use — it is what brings that
        domain's tool schemas into context. Then call call_domain_tool(domain, tool, arguments)
        to invoke a specific tool.
        """
        return await registry.list_domain_tools(domain)

    @mcp.tool()
    async def call_domain_tool(
        domain: str,
        tool: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Invoke a specific tool within a domain and return its result.

        `arguments` is a JSON object that must conform to that tool's `input_schema`
        (from list_domain_tools(domain)). Example:
            call_domain_tool("plane", "list_projects", {})
        """
        return await registry.call(domain, tool, arguments or {})
