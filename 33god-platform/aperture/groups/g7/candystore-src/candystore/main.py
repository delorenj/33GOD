from __future__ import annotations

import json
import logging
import mimetypes
import os
import sys
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
from uuid import UUID

import psycopg2

from candystore import stats
from candystore.context import ContextError, latest_context
from candystore.db import check_connection, init_schema, record_dead_letter
from candystore.ingest import handle_event, known_event_routes, subscribe_response
from candystore.query import (
    COUNT_CAP,
    LENSES,
    PROVENANCE_CLASSES,
    SearchError,
    applied_window,
    by_cli,
    by_project,
    daily,
    get_event,
    get_event_record,
    get_event_with_project,
    get_session_events,
    get_session_summary,
    heatmap,
    known_project_slugs,
    list_classes,
    list_feed,
    list_lenses,
    list_projects,
    parse_time_bound,
    timeline,
)
from candystore.summarize import summarize

logger = logging.getLogger("candystore")

# Default to loopback so a bare `python -m candystore.main` never exposes the
# unauthenticated ingest+query API to the LAN. The container overrides this to
# 0.0.0.0 (see compose.yml) so the Dapr sidecar can reach the app over the
# docker network; the host port is published on 127.0.0.1 there.
APP_HOST = os.environ.get("APP_HOST", "127.0.0.1")
APP_PORT = int(os.environ.get("APP_PORT", "3001"))
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class Handler(BaseHTTPRequestHandler):
    server_version = "Candystore/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if self._wants_html() and self._serve_spa_route(path):
            return

        if path == "/dapr/subscribe":
            self._send_json(200, subscribe_response())
            return
        if path == "/healthz":
            self._send_empty(204)
            return
        if path == "/readyz":
            try:
                ok = check_connection()
            except Exception as exc:
                self._send_json(503, {"ready": False, "error": str(exc)})
                return
            self._send_empty(204 if ok else 503)
            return

        if path == "/context/latest":
            qs = parse_qs(parsed.query)
            try:
                response = latest_context(
                    project=_first(qs, "project"), cwd=_first(qs, "cwd"),
                    since=_first(qs, "since"),
                    sessions=int(_first(qs, "sessions") or "3"),
                    exclude_session=_first(qs, "exclude_session"),
                )
            except (ContextError, ValueError) as exc:
                self._send_json(400, {"error": str(exc)})
                return
            except psycopg2.Error:
                logger.exception("context query failed")
                self._send_json(503, {"error": "context query unavailable; retry later"})
                return
            self._send_json(200, response)
            return

        if path == "/events":
            qs = parse_qs(parsed.query)
            try:
                limit = int(_first(qs, "limit") or "100")
                offset = int(_first(qs, "offset") or "0")
            except ValueError as exc:
                self._send_json(400, {"error": f"invalid limit or offset: {exc}"})
                return
            # Browsing is bounded by default and the count is opt-in; both are
            # policies of the HTTP surface, not of the query (query.py explains
            # the measurements). `?total=1` buys a capped count.
            correlationid = _first(qs, "correlationid")
            q = _first(qs, "q")
            # `?project=` is a registry slug now, so a typo is a client error
            # rather than a silently empty feed. "no events yet" and "no such
            # project" are different answers and only one of them is the
            # caller's mistake.
            project = _first(qs, "project")
            if project and project not in known_project_slugs():
                self._send_json(
                    400,
                    {
                        "error": f"unknown project slug {project!r}",
                        "hint": "GET /projects lists the registry; run "
                        "`mise run project:sync` after registering a new one",
                    },
                )
                return
            # Same treatment as `project`: an unknown class is the caller's
            # typo, and answering it with an empty feed would look like "no
            # such traffic" instead of "no such class".
            provenance = _first(qs, "class")
            unknown = [
                value.strip()
                for value in (provenance or "").split(",")
                if value.strip() and value.strip() not in PROVENANCE_CLASSES
            ]
            if unknown:
                self._send_json(
                    400,
                    {
                        "error": f"unknown provenance class {', '.join(repr(u) for u in unknown)}",
                        "valid": sorted(PROVENANCE_CLASSES),
                    },
                )
                return
            lens = _first(qs, "lens")
            bad_lenses = [
                value.strip()
                for value in (lens or "").split(",")
                if value.strip() and value.strip() not in LENSES
            ]
            if bad_lenses:
                self._send_json(
                    400,
                    {
                        "error": f"unknown lens {', '.join(repr(b) for b in bad_lenses)}",
                        "valid": sorted(LENSES),
                    },
                )
                return
            from_time, to_time = applied_window(
                parse_time_bound(_first(qs, "from")),
                parse_time_bound(_first(qs, "to")),
                correlationid=correlationid,
                q=q,
            )
            try:
                result = list_feed(
                    # `tools=0` hides tool ROWS by folding them; it never
                    # removes them from the counts (query.list_feed).
                    tools=_first(qs, "tools") not in ("0", "false", "no", "off"),
                    type=_first(qs, "type"),
                    domain=_first(qs, "domain"),
                    from_time=from_time,
                    to_time=to_time,
                    correlationid=correlationid,
                    producer=_first(qs, "producer"),
                    service=_first(qs, "service"),
                    cli=_first(qs, "cli"),
                    project=project,
                    provenance=provenance,
                    lens=lens,
                    scope=_first(qs, "scope"),
                    q=q,
                    limit=limit,
                    offset=offset,
                    total=_flag(qs, "total"),
                    count_cap=COUNT_CAP,
                )
            except SearchError as exc:
                # A `q` the index cannot serve is the caller's to fix; say so
                # rather than running a scan that would take minutes. Anything
                # else still raises, so a real server fault is not disguised.
                self._send_json(400, {"error": str(exc)})
                return
            self._send_json(200, result)
            return

        if path.startswith("/events/") and path.endswith("/summary"):
            event_id = path.split("/")[-2]
            # The resolved slug comes back with the envelope so this summary's
            # `project` cannot disagree with the one /events reported for the
            # same row -- which it did, on 399 rows in 7 days.
            found = get_event_with_project(event_id)
            if found is None:
                self._send_empty(404)
                return
            ev, project = found
            self._send_json(200, {"summary": summarize(ev, project), "raw": ev})
            return

        if path.startswith("/events/") and path.endswith("/raw"):
            event_id = path.split("/")[-2]
            ev = get_event(event_id)
            if ev is None:
                self._send_empty(404)
                return
            self._send_json(200, ev)
            return

        if path.startswith("/events/"):
            event_id = path.split("/")[-1]
            ev = get_event_record(event_id)
            if ev is None:
                self._send_empty(404)
                return
            self._send_json(200, ev)
            return

        if path.startswith("/sessions/") and path.endswith("/summary"):
            session_id = path.split("/")[-2]
            self._send_json(200, get_session_summary(session_id))
            return

        if path.startswith("/sessions/"):
            parts = [part for part in path.split("/") if part]
            if len(parts) == 2:
                session_id = unquote(parts[1])
                self._send_json(
                    200,
                    {"session_id": session_id, "events": get_session_events(session_id)},
                )
                return

        if path == "/projects":
            qs = parse_qs(parsed.query)
            window = _first(qs, "window") or "24h"
            hours = _WINDOW_HOURS.get(window)
            if hours is None:
                self._send_json(
                    400,
                    {
                        "error": f"unknown window {window!r}",
                        "valid": sorted(_WINDOW_HOURS),
                    },
                )
                return
            self._send_json(200, list_projects(window_hours=hours))
            return

        if path == "/summary/timeline":
            qs = parse_qs(parsed.query)
            try:
                bucket = int(_first(qs, "bucket") or "60")
            except ValueError:
                self._send_json(400, {"error": "bucket must be an integer"})
                return
            project = _first(qs, "project")
            if project and project not in known_project_slugs():
                self._send_json(400, {"error": f"unknown project slug {project!r}"})
                return
            # The strip shares the feed's window policy, so the chart and the
            # rows below it always describe the same span.
            from_time, to_time = applied_window(
                parse_time_bound(_first(qs, "from")),
                parse_time_bound(_first(qs, "to")),
            )
            try:
                self._send_json(
                    200,
                    timeline(
                        bucket_seconds=bucket,
                        group=_first(qs, "group") or "class",
                        from_time=from_time,
                        to_time=to_time,
                        type=_first(qs, "type"),
                        domain=_first(qs, "domain"),
                        correlationid=_first(qs, "correlationid"),
                        producer=_first(qs, "producer"),
                        service=_first(qs, "service"),
                        cli=_first(qs, "cli"),
                        project=project,
                        provenance=_first(qs, "class"),
                        lens=_first(qs, "lens"),
                        scope=_first(qs, "scope"),
                        q=_first(qs, "q"),
                    ),
                )
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
            except SearchError as exc:
                self._send_json(400, {"error": str(exc)})
            return

        if path == "/lenses":
            qs = parse_qs(parsed.query)
            window = _first(qs, "window") or "24h"
            hours = _WINDOW_HOURS.get(window)
            if hours is None:
                self._send_json(
                    400,
                    {"error": f"unknown window {window!r}", "valid": sorted(_WINDOW_HOURS)},
                )
                return
            self._send_json(200, list_lenses(window_hours=hours))
            return

        if path == "/classes":
            qs = parse_qs(parsed.query)
            window = _first(qs, "window") or "24h"
            hours = _WINDOW_HOURS.get(window)
            if hours is None:
                self._send_json(
                    400,
                    {"error": f"unknown window {window!r}", "valid": sorted(_WINDOW_HOURS)},
                )
                return
            self._send_json(200, list_classes(window_hours=hours))
            return

        if path == "/summary/heatmap":
            qs = parse_qs(parsed.query)
            group = _first(qs, "group") or "project"
            self._send_json(
                200,
                {
                    "buckets": heatmap(
                        group_by=group,
                        from_time=_first(qs, "from"),
                        to_time=_first(qs, "to"),
                    ),
                    "group_by": group,
                },
            )
            return

        if path == "/summary/daily":
            qs = parse_qs(parsed.query)
            self._send_json(
                200,
                {"days": daily(from_time=_first(qs, "from"), to_time=_first(qs, "to"))},
            )
            return

        if path == "/summary/by-cli":
            qs = parse_qs(parsed.query)
            self._send_json(
                200,
                {"items": by_cli(from_time=_first(qs, "from"), to_time=_first(qs, "to"))},
            )
            return

        if path == "/summary/by-project":
            qs = parse_qs(parsed.query)
            self._send_json(
                200,
                {"items": by_project(from_time=_first(qs, "from"), to_time=_first(qs, "to"))},
            )
            return

        if self._serve_static(path):
            return

        self._send_empty(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path not in known_event_routes():
            self._send_empty(404)
            return

        raw = self.rfile.read(int(self.headers.get("Content-Length", "0") or "0"))
        try:
            result = handle_event(raw, topic=path)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError, RecursionError) as exc:
            # Malformed / off-contract event (RecursionError = pathologically
            # nested JSON, un-parseable and thus permanent, not transient). Dapr
            # only honors DROP on a 2xx response; a non-2xx means "retry", which
            # turns a bad event into a poison message that redelivers forever.
            self._drop(raw, path, "malformed", exc)
            return
        except (psycopg2.DataError, psycopg2.IntegrityError) as exc:
            # The DB rejected the value as un-storable (e.g. a NUL that slipped
            # past sanitization, an out-of-range timestamp, a NOT NULL breach).
            # This is a permanent data defect, not a transient failure — DROP it
            # (with a dead_letter record) rather than 500-retry it forever.
            self._drop(raw, path, "db-data-error", exc)
            return
        except Exception as exc:
            # Genuinely transient (DB down, connection reset, etc.). RETRY is
            # correct: NATS redelivers and the idempotent insert dedupes.
            stats.incr("retried")
            logger.error("RETRY event on %s: %s", path, exc)
            self._send_json(500, {"status": "RETRY", "error": str(exc)})
            return

        self._send_json(200, result)

    def _drop(self, raw: bytes, topic: str, reason: str, exc: Exception) -> None:
        """Acknowledge (200) an un-storable event after preserving its bytes."""
        stats.incr("dropped")
        record_dead_letter(raw, reason=reason, topic=topic, error=str(exc))
        logger.warning("DROP event on %s (%s): %s", topic, reason, exc)
        self._send_json(200, {"status": "DROP", "error": str(exc)})

    def _send_json(self, status: int, body: object) -> None:
        payload = json.dumps(body, default=_json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_file(self, status: int, path: Path, content_type: str | None = None) -> None:
        payload = path.read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", content_type or _content_type(path))
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _wants_html(self) -> bool:
        return "text/html" in self.headers.get("Accept", "")

    def _serve_spa_route(self, path: str) -> bool:
        if path == "/" or path == "/index.html":
            return self._serve_index()
        if path in {"/heatmap", "/sessions", "/projects"}:
            return self._serve_index()
        # `/projects/<slug>` is the feed screen. It has to be listed BEFORE the
        # API's own /projects handler is reached, and it is only taken when the
        # request actually wants HTML -- `curl /projects` still gets JSON.
        if path.startswith("/projects/"):
            return self._serve_index()
        if path.startswith("/sessions/"):
            return self._serve_index()
        if path.startswith("/events/") and not (path.endswith("/summary") or path.endswith("/raw")):
            return self._serve_index()
        return False

    def _serve_index(self) -> bool:
        index = STATIC_DIR / "index.html"
        if not index.exists():
            return False
        self._send_file(200, index, "text/html")
        return True

    def _serve_static(self, path: str) -> bool:
        if path in {"/", "/index.html"}:
            return self._serve_index()
        rel = Path(unquote(path.lstrip("/")))
        if rel.is_absolute() or ".." in rel.parts:
            return False
        target = STATIC_DIR / rel
        if target.is_file() and target.resolve().is_relative_to(STATIC_DIR.resolve()):
            self._send_file(200, target)
            return True
        return False


def run(host: str = APP_HOST, port: int = APP_PORT) -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    init_schema()
    server = ThreadingHTTPServer((host, port), Handler)
    logger.info("candystore: listening on %s:%s", host, port)
    sys.stderr.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> int:
    run()
    return 0


def _first(qs: dict[str, list[str]], key: str) -> str | None:
    vals = qs.get(key)
    return vals[0] if vals else None


# The window presets the picker offers. A closed set rather than a duration
# parser: every extra shape is another way for a caller to ask for a scan.
_WINDOW_HOURS = {"1h": 1, "24h": 24, "7d": 24 * 7, "30d": 24 * 30}


# Accepts the spellings a querystring actually arrives in. `?total` with no
# value parses to [""] rather than being absent, and someone writing it by hand
# means yes -- so a bare flag is true.
_TRUTHY = frozenset({"", "1", "true", "yes", "on"})


def _flag(qs: dict[str, list[str]], key: str) -> bool:
    value = _first(qs, key)
    return value is not None and value.strip().lower() in _TRUTHY


def _json_default(value: Any) -> str:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def _content_type(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


if __name__ == "__main__":
    raise SystemExit(main())
