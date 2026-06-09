"""Plane domain — reuses the existing plane-mcp-server tool definitions in-process.

We register all of plane-mcp-server's tools into a throwaway FastMCP instance and
hand the hub their `Tool` objects. The tools are NOT mounted on the hub's served
server; the hub only exposes them via the discovery/dispatcher surface. When the
dispatcher runs a Plane tool, it executes inside the hub's live request context, so
`plane_mcp.client.get_plane_client_context()` resolves the caller's PAT + workspace
from the access token transparently (same header-auth scheme as plane-mcp-server).
"""

from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.tools.tool import Tool


class PlaneDomain:
    name = "plane"
    title = "Plane Project Management"
    description = (
        "Plane work items, projects, cycles, modules, epics, initiatives, labels, "
        "states, pages, comments, links, work logs, intake, and workspace operations. "
        "Authenticates with the caller's Plane PAT (Authorization: Bearer) and "
        "x-workspace-slug header."
    )

    async def load_tools(self) -> dict[str, Tool]:
        # Imported lazily so the hub still starts if plane-mcp-server is absent.
        from plane_mcp.tools import register_tools

        internal = FastMCP("plane-internal")
        register_tools(internal)
        return await internal.get_tools()
