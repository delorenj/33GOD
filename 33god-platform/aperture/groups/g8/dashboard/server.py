"""G8 dashboard — Holocene-shaped apps surface, fed by candystore events.

Tails the bus (durable g8-dashboard) and projects ticket-cycle events into
a work-items view (SQLite). Serves a single-page HTML app in-network that
displays each completed work item WITH its evidence: title, state, commit
sha, tests-passed, and the full correlated event chain (by correlationid,
read back from the local projection of canonical events).

This is the "Holocene-shaped" surface: the real holocene app is an apps+API+
web product; this bundle ships the SHAPE that matters for the G8 gate — a
dashboard the client can see, displaying the completed work item, backed by
candystore events (not by direct board reads: the projection is event-fed,
so dashboard state == bus truth == board truth).
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
CONSUME_STREAM = os.environ.get("GOD_CONSUME_STREAM", "BLOODBANK_EVENTS")
CONSUME_FILTER = os.environ.get("GOD_CONSUME_FILTER", "bloodbank.evt.>")
DURABLE = os.environ.get("GOD_DASH_DURABLE", "g8-dashboard")
APP_PORT = int(os.environ.get("APP_PORT", "8796"))
DB_PATH = os.environ.get("GOD_DASH_DB", "/data/dashboard.db")

SERVICE_NAME = "aperture-g8-dashboard"

HEALTH: dict = {"started": time.time(), "bus": "connecting", "bus_error": None,
                "events_seen": 0, "items_updated": 0, "last_error": None,
                "last_event_at": None}
LOCK = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS work_items (
        ticket_id      TEXT PRIMARY KEY,
        title          TEXT,
        state          TEXT NOT NULL,
        correlationid  TEXT NOT NULL,
        commit_sha     TEXT,
        tests_passed   INTEGER,
        updated_at     TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS chain_events (
        event_id       TEXT PRIMARY KEY,
        correlationid  TEXT NOT NULL,
        type           TEXT NOT NULL,
        subject        TEXT,
        producer       TEXT,
        time           TEXT,
        data           TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chain_corr ON chain_events(correlationid)")
    return conn


def project(envelope: dict) -> None:
    """Event-fed projection: work_items state from ticket.* events; every
    canonical event into chain_events (the displayed chain)."""
    etype = envelope.get("type", "")
    data = envelope.get("data") or {}
    corr = envelope.get("correlationid")
    with db() as conn:
        conn.execute("""INSERT OR IGNORE INTO chain_events
            (event_id, correlationid, type, subject, producer, time, data)
            VALUES (?,?,?,?,?,?,?)""",
            (envelope.get("id"), corr, etype, envelope.get("subject"),
             envelope.get("producer"), envelope.get("time"), json.dumps(data)))
        if etype.startswith("bloodbank.task.ticket.") and data.get("ticket_id"):
            tid = data["ticket_id"]
            state = data.get("state")
            existing = conn.execute(
                "SELECT state FROM work_items WHERE ticket_id=?", (tid,)).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO work_items (ticket_id, title, state, correlationid,"
                    " commit_sha, tests_passed, updated_at) VALUES (?,?,?,?,?,?,?)",
                    (tid, data.get("title"), state or "backlog", corr,
                     data.get("commit_sha"), None if data.get("tests_passed") is None
                     else int(bool(data.get("tests_passed"))), now_iso()))
            else:
                # monotonic state machine for display: backlog -> in_progress -> done
                rank = {"backlog": 0, "in_progress": 1, "done": 2}
                new_state = state or existing[0]
                if rank.get(new_state, 0) >= rank.get(existing[0], 0):
                    conn.execute(
                        "UPDATE work_items SET state=?, title=COALESCE(?, title),"
                        " correlationid=COALESCE(?, correlationid),"
                        " commit_sha=COALESCE(?, commit_sha),"
                        " tests_passed=COALESCE(?, tests_passed), updated_at=?"
                        " WHERE ticket_id=?",
                        (new_state, data.get("title"), corr, data.get("commit_sha"),
                         None if data.get("tests_passed") is None
                         else int(bool(data.get("tests_passed"))), now_iso(), tid))
    with LOCK:
        HEALTH["events_seen"] += 1
        HEALTH["items_updated"] += 1
        HEALTH["last_event_at"] = now_iso()


def consume_loop() -> None:
    while True:
        try:
            nc = jsclient.connect_retry(BUS_URL)
            HEALTH["bus"] = "connected"
            HEALTH["bus_error"] = None
            print(f"dashboard: bus connected {BUS_URL}", flush=True)
            nc.ensure_consumer(CONSUME_STREAM, DURABLE, CONSUME_FILTER)
            inbox = f"_INBOX.g8d.{uuid.uuid4().hex}"
            sid = nc.subscribe_inbox(inbox)
            while True:
                msg = nc.pull(CONSUME_STREAM, DURABLE, inbox, sid)
                if msg is None:
                    time.sleep(1.0)
                    continue
                try:
                    envelope = json.loads(msg["payload"].decode())
                    project(envelope)
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError) as exc:
                    print(f"dashboard: malformed delivery: {exc}", flush=True)
                except Exception as exc:
                    with LOCK:
                        HEALTH["last_error"] = str(exc)[:300]
                    print(f"dashboard: transient error, will redeliver: {exc}", flush=True)
                    raise
                nc.ack(msg["reply"])
        except Exception as exc:
            HEALTH["bus"] = "reconnecting"
            HEALTH["bus_error"] = str(exc)[:300]
            print(f"dashboard: bus loop error: {exc}; reconnect in 5s", flush=True)
            time.sleep(5.0)


# ------------------------------------------------------------------- HTTP
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Aperture G8 — Work Items</title>
<style>
 body{font-family:system-ui,sans-serif;background:#0f1115;color:#e6e6e6;margin:2rem}
 h1{font-size:1.3rem} .sub{color:#8a93a3;font-size:.85rem;margin-bottom:1.5rem}
 table{border-collapse:collapse;width:100%}
 th,td{padding:.55rem .8rem;text-align:left;border-bottom:1px solid #232733}
 th{color:#8a93a3;font-weight:500;font-size:.8rem;text-transform:uppercase}
 .mono{font-family:ui-monospace,monospace;font-size:.8rem}
 .state{display:inline-block;padding:.15rem .6rem;border-radius:99px;font-size:.75rem}
 .backlog{background:#2b303c}.in_progress{background:#3b2f16;color:#e8c66a}
 .done{background:#15301f;color:#5fd08a}
 .chain{margin-top:.4rem;color:#8a93a3;font-size:.75rem}
 .chain span{margin-right:.6rem}
 a{color:#7aa2f7}
</style></head><body>
<h1>G8 · Work Items</h1>
<div class="sub">Holocene-shaped surface — projection of canonical candystore
events (bloodbank.task.*). Board truth == bus truth == this view.</div>
<table><thead><tr>
<th>Ticket</th><th>Title</th><th>State</th><th>Commit</th><th>Tests</th>
</tr></thead><tbody id="rows"></tbody></table>
<script>
fetch('/api/items').then(r=>r.json()).then(d=>{
 const tb=document.getElementById('rows');
 d.items.forEach(it=>{
   const tr=document.createElement('tr');
   const commit = it.commit_sha
     ? `<span class="mono">${it.commit_sha.slice(0,12)}</span>` : '—';
   const tests = it.tests_passed===null?'—':(it.tests_passed?'✅ pass':'❌ fail');
   const chain = (d.chains[it.ticket_id]||[]).map(e=>e.type).join(' → ');
   tr.innerHTML=`<td class="mono">${it.ticket_id.slice(0,8)}</td>
     <td>${esc(it.title||'')}<div class="chain"><span>${chain}</span></div></td>
     <td><span class="state ${it.state}">${it.state.replace('_',' ')}</span></td>
     <td>${commit}</td><td>${tests}</td>`;
   tb.appendChild(tr);
 });
});
function esc(s){return s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body, ctype: str = "application/json") -> None:
        raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args) -> None:  # noqa: A002
        pass

    def do_GET(self) -> None:
        if self.path == "/healthz":
            return self._send(200, dict(HEALTH, uptime_s=round(time.time() - HEALTH["started"], 1)))
        if self.path == "/" or self.path == "/index.html":
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if self.path == "/api/items":
            with db() as conn:
                items = conn.execute(
                    "SELECT ticket_id, title, state, correlationid, commit_sha,"
                    " tests_passed, updated_at FROM work_items"
                    " ORDER BY updated_at DESC LIMIT 100").fetchall()
                chains: dict = {}
                for (corr,) in conn.execute(
                        "SELECT DISTINCT correlationid FROM work_items").fetchall():
                    rows = conn.execute(
                        "SELECT event_id, type, producer, time FROM chain_events"
                        " WHERE correlationid=? ORDER BY time", (corr,)).fetchall()
                    # map correlation -> its ticket chain
                    for it in items:
                        if it[3] == corr:
                            chains[it[0]] = [
                                {"event_id": r[0], "type": r[1], "producer": r[2],
                                 "time": r[3]} for r in rows]
            return self._send(200, {"items": [
                {"ticket_id": r[0], "title": r[1], "state": r[2], "correlationid": r[3],
                 "commit_sha": r[4], "tests_passed": None if r[5] is None else bool(r[5]),
                 "updated_at": r[6]} for r in items], "chains": chains})
        return self._send(404, {"error": "not found"})


def main() -> None:
    print(f"dashboard: db={DB_PATH} bus={BUS_URL}", flush=True)
    threading.Thread(target=consume_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", APP_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
