"""33GOD Pipeline MCP Hub.

A multi-domain MCP server that exposes a tiny, stable top-level surface
(`list_domains`, `list_domain_tools`, `call_domain_tool`) and gates large
domain toolsets (Plane, BloodBank, ticket-lifecycle, ...) behind it. Domain
tool schemas are only loaded into the model's context when explicitly
requested via `list_domain_tools`, keeping per-request token cost low and
working on any MCP client regardless of `tools/list_changed` support.
"""

__version__ = "0.1.0"
