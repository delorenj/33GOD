#!/usr/bin/env python3
"""G3 optional ntfy-upstream-gate — minimal stdlib forwarder.

Optional (`upstream` profile). Long-polls a local ntfy source topic and
forwards each message to a configured upstream ntfy server. If no upstream is
configured (the G3 default) it logs that once and stays healthy-but-inert —
any real upstream gate's topic/credentials are deployment-owned and are NOT
shipped here.

Env:
  GOD_NTFY_SOURCE_URL       local ntfy base URL (default: http://ntfy)
  GOD_NTFY_SOURCE_TOPIC     source topic (default: deploys)
  GOD_NTFY_UPSTREAM_URL     upstream ntfy base URL (empty = inert, documented)
  GOD_NTFY_UPSTREAM_TOPIC   upstream topic (empty = inert)
  GOD_HEALTHZ_PORT          healthz listen port (default: 8790)
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = logging.getLogger("ntfy-upstream-gate")


def _http_json(url, timeout=60.0):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _post(url, message: dict, timeout=15.0):
    body = json.dumps(message).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status


def main() -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    source = os.environ.get("GOD_NTFY_SOURCE_URL", "http://ntfy")
    source_topic = os.environ.get("GOD_NTFY_SOURCE_TOPIC", "deploys")
    upstream = os.environ.get("GOD_NTFY_UPSTREAM_URL", "")
    upstream_topic = os.environ.get("GOD_NTFY_UPSTREAM_TOPIC", "")
    healthz_port = int(os.environ.get("GOD_HEALTHZ_PORT", "8790"))

    if not upstream or not upstream_topic:
        LOG.warning("no upstream configured (GOD_NTFY_UPSTREAM_URL/TOPIC); gate is inert")
    else:
        LOG.info("forwarding %s/%s -> %s/%s", source, source_topic, upstream, upstream_topic)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b'{"ok": true, "service": "ntfy-upstream-gate"}'
            if self.path != "/healthz":
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    threading.Thread(target=ThreadingHTTPServer(("0.0.0.0", healthz_port), Handler).serve_forever, daemon=True).start()

    since = "all"
    while True:
        if not upstream or not upstream_topic:
            time.sleep(30)
            continue
        try:
            events = _http_json(f"{source}/{source_topic}/json?poll=1&since={since}")
            for ev in events:
                _post(f"{upstream}/{upstream_topic}", {"topic": upstream_topic, "title": ev.get("title", ""), "message": ev.get("message", "")})
                since = str(ev.get("id", since))
                LOG.info("forwarded message id=%s", ev.get("id"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            LOG.warning("forward poll failed: %s", exc)
            time.sleep(5)


if __name__ == "__main__":
    main()
