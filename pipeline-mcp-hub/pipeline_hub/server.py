"""Hub assembly: build the registry of domains and the served FastMCP instance."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from pipeline_hub.domains.plane import PlaneDomain
from pipeline_hub.hub_tools import register_hub_tools
from pipeline_hub.registry import DomainRegistry

logger = logging.getLogger("pipeline_hub.server")


def build_registry() -> DomainRegistry:
    """Register all domains the hub composes. Add new domains here."""
    registry = DomainRegistry()
    registry.register(PlaneDomain())
    # Phase 1: registry.register(BloodBankDomain())
    # Phase 2: registry.register(TicketLifecycleDomain())
    return registry


def build_hub(with_auth: bool = True) -> FastMCP:
    """Build the served hub.

    Args:
        with_auth: When True (HTTP mode), require header-PAT auth using the same
            scheme as plane-mcp-server (Authorization: Bearer <PAT> + x-workspace-slug),
            so in-process Plane tools resolve the caller's credentials from the
            request context. When False (stdio/local), no auth provider is attached
            and Plane tools fall back to PLANE_API_KEY / PLANE_WORKSPACE_SLUG env vars.
    """
    auth = None
    if with_auth:
        # Reuse plane-mcp-server's header verifier so the access-token claims
        # (auth_method=api_key_header, workspace_slug) match what
        # plane_mcp.client.get_plane_client_context() expects.
        from plane_mcp.auth import PlaneHeaderAuthProvider

        auth = PlaneHeaderAuthProvider(required_scopes=["read", "write"])

    hub = FastMCP("33GOD Pipeline MCP Hub", auth=auth)
    register_hub_tools(hub, build_registry())
    return hub
