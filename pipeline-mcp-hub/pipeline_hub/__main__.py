"""Entry point for the 33GOD Pipeline MCP Hub.

Usage:
    python -m pipeline_hub stdio   # local, no auth (uses PLANE_API_KEY/PLANE_WORKSPACE_SLUG)
    python -m pipeline_hub http    # served on 0.0.0.0:$HUB_PORT at /mcp, header-PAT auth
"""

from __future__ import annotations

import logging
import os
import sys
from enum import Enum

import uvicorn
from starlette.middleware.cors import CORSMiddleware

from pipeline_hub.server import build_hub

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("pipeline_hub")


class ServerMode(Enum):
    STDIO = "stdio"
    HTTP = "http"


def main() -> None:
    mode = ServerMode.STDIO
    if len(sys.argv) > 1:
        mode = ServerMode(sys.argv[1])

    if mode == ServerMode.STDIO:
        build_hub(with_auth=False).run()
        return

    # HTTP (streamable) mode — clean, header-PAT auth only (no OAuth/SSE machinery).
    hub = build_hub(with_auth=True)
    app = hub.http_app(stateless_http=True)  # streamable endpoint served at /mcp
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    port = int(os.getenv("HUB_PORT", "8080"))
    logger.info("Starting 33GOD Pipeline MCP Hub on 0.0.0.0:%s at /mcp", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info", access_log=False)


if __name__ == "__main__":
    main()
