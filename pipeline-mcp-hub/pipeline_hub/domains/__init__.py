"""Domain definitions for the Pipeline MCP Hub.

Each domain groups a set of underlying MCP tools. A domain implements the
`Domain` protocol (see `base.py`): a `name`/`title`/`description` and an async
`load_tools()` that returns `{tool_name: fastmcp.tools.tool.Tool}`.
"""
