"""G7 memory-reference — a REAL reference memory backend implementing the
pluggable-backend contract (POST /ingest, POST /query).

SQLite FTS5 keyword store over canonical envelopes: searchable text is the
envelope's identity fields (type/subject/producer/service/domain + actor.cli)
plus a bounded slice of data. Not a fake: real storage, real FTS5 query
execution, real readback. It exists (a) to prove the hindsight-bridge's
backend contract end-to-end and (b) as the reference implementation a real
hindsight server replaces via GOD_MEMORY_BACKENDS (see DEFERRED.md).

No LLM: keyword search only. Embeddings/rerank are the bridge's concern.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = os.environ.get("GOD_MEMORY_DB", "/data/memory.db")
PORT = int(os.environ.get("GOD_MEMORY_PORT", "8792"))
MAX_BODY = 1 << 20
LOCK = threading.Lock()

_conn: sqlite3.Connection | None = None


def db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
        conn.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS memory USING fts5(
            event_id UNINDEXED,
            type, subject, producer, service, domain, actor_cli, text, data_json,
            tokenize='unicode61')""")
        _conn = conn
    return _conn


def _search_text(envelope: dict) -> str:
    """Envelope identity fields + bounded data slice. Matches candystore's
    search_text philosophy (envelope-level terms, data.* only via select
    top-level string fields) — see candystore/migrations/003_search.sql."""
    data = envelope.get("data")
    if not isinstance(data, dict):
        data = {}
    parts = [str(envelope.get(f) or "") for f in
             ("type", "subject", "producer", "service", "domain")]
    actor = envelope.get("actor") or {}
    parts.append(str(actor.get("cli") or ""))
    for key in ("project", "repo", "tool_name", "name", "status", "outcome",
                "arguments", "prompt_text"):
        if isinstance(data.get(key), str):
            parts.append(data[key][:2048])
    return "\n".join(parts)


def ingest(events: list[dict]) -> int:
    conn = db()
    stored = 0
    with LOCK, conn:
        for env in events:
            if not isinstance(env, dict) or not env.get("id"):
                continue
            conn.execute(
                "INSERT INTO memory (event_id, type, subject, producer, service, "
                "domain, actor_cli, text, data_json) VALUES (?,?,?,?,?,?,?,?,?)",
                (str(env["id"]), str(env.get("type") or ""),
                 str(env.get("subject") or ""), str(env.get("producer") or ""),
                 str(env.get("service") or ""), str(env.get("domain") or ""),
                 str((env.get("actor") or {}).get("cli") or ""),
                 _search_text(env), json.dumps(env.get("data"))[:16384]))
            stored += 1
    return stored


def _fts_escape(term: str) -> str:
    # FTS5 query syntax escaping: wrap each whitespace-separated term in
    # double quotes so punctuation/keywords in the term cannot alter the query
    # tree (a term like "NOT" or "a-b" would otherwise parse as syntax).
    return " ".join(f'"{piece}"' for piece in term.split() if piece)


def query(q: str, limit: int) -> list[dict]:
    conn = db()
    with LOCK:
        rows = conn.execute(
            "SELECT event_id, type, subject, producer, service, domain, actor_cli, data_json "
            "FROM memory WHERE memory MATCH ? ORDER BY rank LIMIT ?",
            (_fts_escape(q), limit)).fetchall()
    return [{"event_id": r[0], "type": r[1], "subject": r[2], "producer": r[3],
             "service": r[4], "domain": r[5], "actor_cli": r[6], "data": json.loads(r[7])}
            for r in rows]


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        print(format % args, flush=True)

    def do_GET(self) -> None:
        if self.path != "/healthz":
            return self._send(404, {"error": "not found"})
        try:
            with LOCK:
                count = db().execute("SELECT count(*) FROM memory").fetchone()[0]
            ready = True
        except sqlite3.Error as exc:
            count, ready = -1, False
        self._send(200, {"ready": ready, "events": count,
                         "backend": "memory-reference-fts5"})

    def do_POST(self) -> None:
        if self.path not in ("/ingest", "/query"):
            return self._send(404, {"error": "not found"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY:
                return self._send(413, {"error": f"body must be 1..{MAX_BODY} bytes"})
            body = json.loads(self.rfile.read(size))
        except (ValueError, TypeError) as exc:
            return self._send(400, {"error": str(exc)})
        if self.path == "/ingest":
            events = body.get("events") if isinstance(body, dict) else None
            if not isinstance(events, list) or not all(isinstance(e, dict) for e in events):
                return self._send(400, {"error": "body must be {\"events\": [objects]}"})
            return self._send(200, {"stored": ingest(events)})
        q = body.get("q") if isinstance(body, dict) else None
        if not isinstance(q, str) or not q.strip():
            return self._send(400, {"error": "q must be a non-empty string"})
        limit = body.get("limit", 20)
        if not isinstance(limit, int) or not 1 <= limit <= 100:
            return self._send(400, {"error": "limit must be 1..100"})
        return self._send(200, {"results": query(q, limit)})


def main() -> None:
    db()  # create schema at boot so healthz can report a real count
    print(f"memory-reference: db={DB_PATH}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
