"""G4 canary — a tiny synthetic Prometheus scrape target the smoke kills.

Serves /metrics (one gauge) and /healthz. It exists so the smoke can stop and
start a REAL god-g4 container and prove the InstanceDown + ContainerGone alert
path (prometheus -> alertmanager -> alert-bridge) end-to-end. It is a smoke
fixture, not an observability component.
"""
from __future__ import annotations

import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("GOD_HEALTHZ_PORT", "8791"))
START = time.time()

METRICS = (
    "# HELP aperture_canary_up 1 if the G4 canary is up.\n"
    "# TYPE aperture_canary_up gauge\n"
    "aperture_canary_up 1\n"
    "# HELP aperture_canary_start_time_seconds canary process start time.\n"
    "# TYPE aperture_canary_start_time_seconds gauge\n"
    f"aperture_canary_start_time_seconds {START:.0f}\n"
)


class Handler(BaseHTTPRequestHandler):
    def _respond(self, status, body, ctype):
        raw = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/healthz":
            return self._respond(200, '{"ok": true, "service": "canary"}', "application/json")
        if self.path == "/metrics":
            return self._respond(200, METRICS, "text/plain; version=0.0.4")
        return self._respond(404, '{"error": "not found"}', "application/json")

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
