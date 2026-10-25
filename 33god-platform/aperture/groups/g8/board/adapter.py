"""G8 board adapter — REAL local sandbox board with Plane's state vocabulary.

Implements the board contract the G8 orchestrator drives:

    create  -> Backlog
    start   -> In Progress
    done    -> Done (requires evidence: commit sha + tests pass)

State vocabulary mirrors Plane's lanes (Backlog / In Progress / Done) so the
adapter seam to a real Plane (px) is config, not code: GOD_BOARD_KIND
selects `sandbox` (this SQLite implementation, default) or `plane`
(documented-deferred — see DEFERRED.md; needs a real Plane instance and
credentials that never travel with a bundle).

The board persists to SQLite on the group volume and publishes a canonical
event for EVERY transition, carrying ONE correlationid for the whole ticket
lifecycle (create -> done). Events:

    bloodbank.task.ticket.created    (kind event, state backlog)
    bloodbank.task.ticket.started    (kind event, state in_progress)
    bloodbank.task.ticket.completed  (kind event, state done + evidence)

NOTE (honest boundary): in the REAL system, Plane ticket facts arrive as
repo.task.* / repo.board.* Plane-webhook events owned by the webhook — not
PM-emitted. This sandbox board is the deployment-local stand-in; its events
use this bundle's own task vocabulary under producer "aperture-g8-board".
See events.md + DEFERRED.md.

HTTP (APP_PORT): /healthz, GET /tickets, GET /ticket/<id>, POST /command
{action: create|start|done, ...}. The command endpoint is what the smoke,
the accept gate, and (in real deployments) the orchestrator call — the
board never trusts out-of-band state.
stdlib only; bus via jsclient (g7 byte-identical copy).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jsclient

BUS_URL = os.environ.get("GOD_BUS_NATS_URL", "nats://nats:4222")
OUTBOX_STREAM = os.environ.get("GOD_OUTBOX_STREAM", "BLOODBANK_EVENTS")
APP_PORT = int(os.environ.get("APP_PORT", "8793"))
DB_PATH = os.environ.get("GOD_BOARD_DB", "/data/board.db")
BOARD_KIND = os.environ.get("GOD_BOARD_KIND", "sandbox")

SOURCE_URN = "urn:33god:aperture:g8-board"
SERVICE_NAME = "aperture-g8-board"
PRODUCER = "aperture-g8-board"

# Plane-lane vocabulary (the adapter contract)
STATES = ("backlog", "in_progress", "done")

HEALTH: dict = {"started": time.time(), "board_kind": BOARD_KIND, "bus": "connecting",
                "bus_error": None, "commands": 0, "published": 0,
                "rejected": 0, "last_error": None, "last_event_at": None}
LOCK = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS tickets (
        id         TEXT PRIMARY KEY,
        title      TEXT NOT NULL,
        state      TEXT NOT NULL,
        summary    TEXT,
        correlationid TEXT NOT NULL,
        commit_sha TEXT,
        tests_passed INTEGER,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_corr ON tickets(correlationid)")
    return conn


# ----------------------------------------------------------- event emission
def ticket_event(action: str, ticket: dict, extra: dict | None = None) -> dict:
    """Canonical envelope for a ticket transition. 4-token type / 5-token
    subject; correlationid is the ticket's LIFECYCLE correlation (one id
    create -> done — the G8 gate's chain contract)."""
    data = {
        "ticket_id": ticket["id"],
        "title": ticket["title"],
        "state": ticket["state"],
        "correlationid": ticket["correlationid"],
    }
    if ticket.get("commit_sha"):
        data["commit_sha"] = ticket["commit_sha"]
    if ticket.get("tests_passed") is not None:
        data["tests_passed"] = bool(ticket["tests_passed"])
    if extra:
        data.update(extra)
    return {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": SOURCE_URN,
        "type": f"bloodbank.task.ticket.{action}",
        "subject": f"bloodbank.evt.task.ticket.{action}",
        "time": now_iso(),
        "datacontenttype": "application/json",
        "correlationid": ticket["correlationid"],
        "causationid": ticket["correlationid"],
        "producer": PRODUCER,
        "service": "aperture-g8",
        "domain": "task",
        "kind": "event",
        "ordering_key": f"task:ticket:{ticket['id']}",
        "actor": {"type": "service", "agent_id": SERVICE_NAME,
                  "cli": None, "provider": None, "model": None},
        "data": data,
    }


# ------------------------------------------------------------ command logic
def apply_command(conn: sqlite3.Connection, action: str, payload: dict) -> dict:
    """Pure state machine + persistence. Returns the ticket row after the
    transition. Raises ValueError on any invalid command (bad state hop,
    missing evidence, unknown ticket)."""
    if action == "create":
        title = (payload.get("title") or "").strip()
        if not title:
            raise ValueError("create requires a non-empty title")
        tid = str(uuid.uuid4())
        corr = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO tickets (id, title, state, summary, correlationid,"
            " created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (tid, title, "backlog", payload.get("summary"), corr, now_iso(), now_iso()))
        conn.commit()
        row = conn.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
    elif action == "start":
        row = _get(conn, payload)
        if row["state"] != "backlog":
            raise ValueError(f"start requires backlog state, got {row['state']}")
        conn.execute("UPDATE tickets SET state='in_progress', updated_at=? WHERE id=?",
                     (now_iso(), row["id"]))
        conn.commit()
        row = _get(conn, payload)
    elif action == "done":
        row = _get(conn, payload)
        if row["state"] != "in_progress":
            raise ValueError(f"done requires in_progress state, got {row['state']}")
        commit_sha = (payload.get("commit_sha") or "").strip()
        if not commit_sha or len(commit_sha) < 7:
            raise ValueError("done requires commit_sha evidence (>=7 hex chars)")
        tests_passed = payload.get("tests_passed")
        if tests_passed is not True:
            raise ValueError("done requires tests_passed=true evidence")
        conn.execute(
            "UPDATE tickets SET state='done', commit_sha=?, tests_passed=1, updated_at=? WHERE id=?",
            (commit_sha, now_iso(), row["id"]))
        conn.commit()
        row = _get(conn, payload)
    else:
        raise ValueError(f"unknown action: {action}")
    return _row_to_dict(row)


def _get(conn: sqlite3.Connection, payload: dict) -> sqlite3.Row:
    tid = payload.get("ticket_id")
    if not tid:
        raise ValueError("ticket_id required")
    row = conn.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
    if row is None:
        raise ValueError(f"no such ticket: {tid}")
    return row


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "ticket_id": row["id"], "title": row["title"], "state": row["state"],
            "summary": row["summary"], "correlationid": row["correlationid"],
            "commit_sha": row["commit_sha"],
            "tests_passed": None if row["tests_passed"] is None else bool(row["tests_passed"]),
            "created_at": row["created_at"], "updated_at": row["updated_at"]}


ACTION_EVENT = {"create": "created", "start": "started", "done": "completed"}


def command(payload: dict) -> dict:
    """Validate -> apply -> publish. One canonical event per transition,
    correlated by the ticket's lifecycle correlationid."""
    action = payload.get("action")
    if action not in ACTION_EVENT:
        raise ValueError("action must be create|start|done")
    conn = db()
    ticket = apply_command(conn, action, payload)
    env = ticket_event(ACTION_EVENT[action], ticket)
    nc = jsclient.NatsConn(BUS_URL)
    try:
        ack = nc.publish_ack(env["subject"], env)
        if not isinstance(ack.get("seq"), int):
            raise jsclient.NatsError(f"publish ack missing seq: {ack!r}")
    finally:
        nc.close()
    with LOCK:
        HEALTH["commands"] += 1
        HEALTH["published"] += 1
        HEALTH["last_event_at"] = now_iso()
    return {"status": "ok", "ticket": ticket,
            "event": {"id": env["id"], "type": env["type"],
                      "correlationid": env["correlationid"], "sequence": ack["seq"]}}


def reject(reason: str) -> None:
    with LOCK:
        HEALTH["rejected"] += 1
        HEALTH["last_error"] = reason


# ------------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args) -> None:  # noqa: A002
        print(format % args, flush=True)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            return self._send(200, dict(HEALTH, uptime_s=round(time.time() - HEALTH["started"], 1)))
        if self.path == "/tickets":
            with db() as conn:
                rows = conn.execute("SELECT * FROM tickets ORDER BY created_at DESC").fetchall()
            return self._send(200, {"tickets": [_row_to_dict(r) for r in rows]})
        if self.path.startswith("/ticket/"):
            tid = self.path.split("/ticket/", 1)[1]
            with db() as conn:
                row = conn.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
            if row is None:
                return self._send(404, {"error": f"no such ticket: {tid}"})
            return self._send(200, {"ticket": _row_to_dict(row)})
        return self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/command":
            return self._send(404, {"error": "not found"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= (1 << 20):
                return self._send(413, {"error": "body must be 1..1048576 bytes"})
            payload = json.loads(self.rfile.read(size))
        except (ValueError, TypeError) as exc:
            reject(f"bad body: {exc}")
            return self._send(400, {"error": str(exc)})
        try:
            result = command(payload)
        except ValueError as exc:
            reject(str(exc))
            return self._send(400, {"error": str(exc)})
        except Exception as exc:  # bus down etc.
            reject(f"internal: {exc}")
            return self._send(502, {"error": str(exc)[:300]})
        return self._send(200, result)


def main() -> None:
    print(f"board: kind={BOARD_KIND} db={DB_PATH} bus={BUS_URL}", flush=True)
    HEALTH["bus"] = "ok"  # per-command short-lived connections; no long loop
    server = ThreadingHTTPServer(("0.0.0.0", APP_PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
