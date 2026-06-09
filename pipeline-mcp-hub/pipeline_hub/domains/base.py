"""Domain protocol for the Pipeline MCP Hub."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fastmcp.tools.tool import Tool


@runtime_checkable
class Domain(Protocol):
    """A named group of MCP tools the hub can expose lazily.

    Implementations are cheap to construct; the (potentially expensive) tool
    materialization happens in `load_tools()`, which the registry calls once
    and caches.
    """

    name: str
    """Stable identifier used in `list_domains` / `call_domain_tool` (e.g. "plane")."""

    title: str
    """Human-readable label."""

    description: str
    """One- or two-sentence summary the model reads to decide whether to load this domain."""

    async def load_tools(self) -> dict[str, Tool]:
        """Return the domain's tools keyed by tool name.

        Raising is allowed: the registry isolates per-domain load failures so a
        broken/optional domain (e.g. a missing dependency) does not take down
        the hub — it simply reports as unavailable.
        """
        ...
