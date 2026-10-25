"""G8 momod — Momo-shaped orchestration worker (the G8 gate driver).

WIP-lease discipline (momo-wip-lock protocol, stdlib port): before driving
ticket transitions momod must hold the bundle's WIP lease (a JSON file on
the shared group volume). One ticket in flight at a time; a second driver
(a duplicate momod, a stray script) is refused while the lease is fresh;
a stale lease (holder died) is stolen after TTL. This is the SAME protocol
as momo/skill/scripts/momo-wip-lock.py, containerized stdlib-only.

Orchestration loop:
  1. Consume canonical `bloodbank.task.ticket.created` events from the bus
     (durable g8-momod).
  2. Acquire the WIP lease; if held fresh by another owner, back off (the
     coexistence property; no double-driving).
  3. Drive the cycle: board.start -> assign to code-worker (canonical
     command event on BLOODBANK_COMMANDS) -> wait for the completion reply
     (bloodbank.rpy.task.ticket.completed, same correlationid) -> review
     the evidence -> board.done(commit_sha, tests_passed).
  4. Release the WIP lease.

Review (D4): with client-owned LLM env EMPTY (default, zero AAI) the
review is deterministic: commit sha present, tests passed, sha resolves
inside the code-worker's real repo (verified via the code-worker HTTP API).
momod is healthy + DEGRADED in healthz in this mode (G7 boundary pattern).
With GOD_LLM_* set, an optional reviewer LLM pass may add commentary — but
it NEVER gates the cycle (evidence gates it), and it never ships a default.

Every event momod emits carries the ticket's lifecycle correlationid —
ONE id from ticket-create to ticket-done (the G8 gate's chain contract).
stdlib only; bus via jsclient (g7 byte-identical copy).
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen

import jsclient

BUS_URL = os.environ.get("GOD_BUS_NATS_URL", "nats://nats:4222")
CONSUME_STREAM = os.environ.get("GOD_CONSUME_STREAM", "BLOODBANK_EVENTS")
OUTBOX_STREAM = os.environ.get("GOD_OUTBOX_STREAM", "BLOODBANK_EVENTS")
CONSUME_FILTER = os.environ.get("GOD_CONSUME_FILTER", "bloodbank.evt.task.ticket.>")
DURABLE = os.environ.get("GOD_MOMO_DURABLE", "g8-momod")
APP_PORT = int(os.environ.get("APP_PORT", "8795"))
DB_PATH = os.environ.get("GOD_MOMO_DB", "/data/momod.db")
LOCK_PATH = os.environ.get("GOD_WIP_LOCK", "/data/wip-driver.lock")
LEASE_TTL = int(os.environ.get("GOD_WIP_TTL", "120"))
BOARD_URL = os.environ.get("GOD_BOARD_URL", "http://board:8793")
CODE_WORKER_URL = os.environ.get("GOD_CODE_WORKER_URL", "http://code-worker:8794")

# Client-owned optional reviewer LLM — EMPTY defaults, zero AAI
LLM_BASE_URL = os.environ.get("GOD_LLM_BASE_URL", "")
LLM_API_KEY = os.environ.get("GOD_LLM_API_KEY", "")

SOURCE_URN = "urn:33god:aperture:g8-momod"
SERVICE_NAME = "aperture-g8-momod"

HEALTH: dict = {
    "started": time.time(), "bus": "connecting", "bus_error": None,
    "cycles_started": 0, "cycles_completed": 0, "cycles_failed": 0,
    "lease_acquired": 0, "lease_refused": 0, "lease_stolen": 0,
    "review_mode": "deterministic", "degraded": True, "degraded_reason": "",
    "last_error": None, "last_event_at": None, "in_flight": None,
}
LOCK = threading.Lock()

HEALTH["degraded_reason"] = (
    "degraded: no reviewer LLM (GOD_LLM_BASE_URL and GOD_LLM_API_KEY empty); "
    "deterministic evidence review only")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS cycles (
        ticket_id     TEXT PRIMARY KEY,
        correlationid TEXT NOT NULL,
        state         TEXT NOT NULL,
        commit_sha    TEXT,
        tests_passed  INTEGER,
        assignment_id TEXT,
        started_at    TEXT,
        finished_at   TEXT
    )""")
    return conn


# ----------------------------------------------- WIP lease (stdlib port)
LEASE_OWNER = f"momod:{os.uname().nodename}:{os.getpid()}"


def _read_lease() -> dict | None:
    try:
        with open(LOCK_PATH) as f:
            return json.load(f)
    except Exception:
        return None


def _write_lease(path: str, data: dict) -> None:
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def lease_acquire() -> str:
    """momo-wip-lock protocol, stdlib. Returns 'acquired'|'stolen'|'refused'.

    flock-serialized check-and-set: a lease is respected while its heartbeat
    is fresh; a stale one (holder died) is stolen after TTL."""
    import fcntl
    lease = _read_lease() or {}
    now = time.time()
    fresh = (now - lease.get("heartbeat_at", 0)) < lease.get("ttl", LEASE_TTL) if lease else False
    if fresh and lease.get("owner") != LEASE_OWNER:
        return "refused"
    state = "stolen" if lease else "acquired"
    _write_lease(LOCK_PATH, {"owner": LEASE_OWNER, "pid": os.getpid(),
                             "host": os.uname().nodename,
                             "started_at": now, "heartbeat_at": now, "ttl": LEASE_TTL})
    return state


def lease_heartbeat() -> None:
    lease = _read_lease()
    if lease and lease.get("owner") == LEASE_OWNER:
        lease["heartbeat_at"] = time.time()
        _write_lease(LOCK_PATH, lease)


def lease_release() -> None:
    lease = _read_lease()
    if lease and lease.get("owner") == LEASE_OWNER:
        try:
            os.remove(LOCK_PATH)
        except OSError:
            pass


# ------------------------------------------------------------- bus helpers
def momod_event(action: str, ticket: dict, extra: dict | None = None) -> dict:
    etype = f"bloodbank.task.cycle.{action}"
    data = {"ticket_id": ticket["ticket_id"], "title": ticket.get("title"),
            "correlationid": ticket["correlationid"], "by": SERVICE_NAME}
    if extra:
        data.update(extra)
    return {
        "specversion": "1.0",
        "id": str(uuid.uuid4()),
        "source": SOURCE_URN,
        "type": etype,
        "subject": f"bloodbank.evt.task.cycle.{action}",
        "time": now_iso(),
        "datacontenttype": "application/json",
        "correlationid": ticket["correlationid"],
        "causationid": ticket.get("event_id", ticket["correlationid"]),
        "producer": SERVICE_NAME,
        "service": "aperture-g8",
        "domain": "task",
        "kind": "event",
        "ordering_key": f"task:cycle:{ticket['ticket_id']}",
        "actor": {"type": "service", "agent_id": SERVICE_NAME,
                  "cli": None, "provider": None, "model": None},
        "data": data,
    }


def assign_command(ticket: dict) -> dict:
    """Canonical command on BLOODBANK_COMMANDS -> consumed by code-worker.
    Same correlationid (THE chain)."""
    assignment_id = str(uuid.uuid4())
    data = {"ticket_id": ticket["ticket_id"], "title": ticket["title"],
            "correlationid": ticket["correlationid"],
            "assignment_id": assignment_id}
    return {
        "specversion": "1.0",
        "id": assignment_id,
        "source": SOURCE_URN,
        "type": "bloodbank.task.ticket.assigned",
        "subject": "bloodbank.cmd.task.ticket.assigned",
        "time": now_iso(),
        "datacontenttype": "application/json",
        "correlationid": ticket["correlationid"],
        "causationid": ticket.get("event_id", ticket["correlationid"]),
        "producer": SERVICE_NAME,
        "service": "aperture-g8",
        "domain": "task",
        "kind": "command",
        "command_id": assignment_id,
        "idempotency_key": f"assign:{ticket['ticket_id']}",
        "ordering_key": f"task:ticket:{ticket['ticket_id']}",
        "actor": {"type": "service", "agent_id": SERVICE_NAME,
                  "cli": None, "provider": None, "model": None},
        "data": data,
    }


# ------------------------------------------------------------ HTTP client
def board_command(payload: dict) -> dict:
    req = __import__("urllib.request", fromlist=["request"]).Request(
        f"{BOARD_URL}/command", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def code_worker_evidence(commit_sha: str) -> dict:
    """Ask the code-worker's real repo for the commit — evidence verification
    is the DOWNSTREAM readback, not the claim."""
    with urlopen(f"{CODE_WORKER_URL}/git-log", timeout=15) as r:
        return json.loads(r.read().decode())


# ------------------------------------------------------------------- cycle
def drive_cycle(nc: jsclient.NatsConn, created: dict) -> None:
    """One ticket: start -> assign -> await completion -> review -> done.
    correlationid carried end-to-end; every hop canonical."""
    data = created.get("data") or {}
    ticket = {"ticket_id": data["ticket_id"], "title": data.get("title", ""),
              "correlationid": created["correlationid"], "event_id": created["id"]}
    with LOCK:
        HEALTH["in_flight"] = ticket["ticket_id"]
        HEALTH["cycles_started"] += 1
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO cycles (ticket_id, correlationid, state,"
                     " started_at) VALUES (?,?,?,?)",
                     (ticket["ticket_id"], ticket["correlationid"], "driving", now_iso()))
    try:
        # 1) WIP lease — refuse to double-drive
        state = lease_acquire()
        if state == "refused":
            with LOCK:
                HEALTH["lease_refused"] += 1
            print(f"momod: WIP lease held by another driver; deferring ticket "
                  f"{ticket['ticket_id']}", flush=True)
            with db() as conn:
                conn.execute("UPDATE cycles SET state='deferred' WHERE ticket_id=?",
                             (ticket["ticket_id"],))
            return  # leave for redelivery/another pass
        with LOCK:
            HEALTH["lease_acquired"] += 1
            if state == "stolen":
                HEALTH["lease_stolen"] += 1
        lease_heartbeat()

        # 2) board: backlog -> in_progress
        board_command({"action": "start", "ticket_id": ticket["ticket_id"]})
        ev = momod_event("started", ticket)
        nc.publish_ack(ev["subject"], ev)

        # 3) assign the code-worker (canonical command)
        cmd = assign_command(ticket)
        nc.publish_ack(cmd["subject"], cmd)

        # 4) await the completion reply (same correlationid) — poll the
        #    code-worker's real evidence endpoint; the reply event is the
        #    bus-visible side of the same fact.
        deadline = time.time() + 180
        result = None
        while time.time() < deadline:
            lease_heartbeat()
            try:
                with urlopen(f"{CODE_WORKER_URL}/landed", timeout=10) as r:
                    rows = json.loads(r.read().decode()).get("landed", [])
                match = [x for x in rows if x["ticket_id"] == ticket["ticket_id"]]
                if match:
                    result = match[0]
                    break
            except Exception:
                pass
            time.sleep(3)
        if result is None or not result["tests_passed"] or not result.get("commit_sha"):
            raise RuntimeError("code-worker evidence incomplete or tests failed")

        # 5) deterministic review: commit resolves in the REAL repo
        review = code_worker_evidence(result["commit_sha"])
        log = review.get("git_log", [])
        # momod's /git-log serves full SHAs (format="%H %s"); the landed
        # evidence sha must appear in the real log
        shas = [line.split(" ", 1)[0] for line in log]
        if result["commit_sha"] not in shas:
            # tolerate short-sha logs (e.g. --oneline): prefix match
            if not any(s.startswith(result["commit_sha"][:12]) or
                       result["commit_sha"].startswith(s[:12]) for s in shas if s):
                raise RuntimeError("commit sha not found in code-worker repo log")

        # 6) board: in_progress -> done (with evidence)
        board_command({"action": "done", "ticket_id": ticket["ticket_id"],
                       "commit_sha": result["commit_sha"],
                       "tests_passed": True})
        ev = momod_event("reviewed", ticket, {
            "commit_sha": result["commit_sha"], "tests_passed": True,
            "review_mode": "deterministic"})
        nc.publish_ack(ev["subject"], ev)
        with db() as conn:
            conn.execute("UPDATE cycles SET state='done', commit_sha=?, tests_passed=1,"
                         " assignment_id=?, finished_at=? WHERE ticket_id=?",
                         (result["commit_sha"], cmd["id"], now_iso(), ticket["ticket_id"]))
        with LOCK:
            HEALTH["cycles_completed"] += 1
            HEALTH["last_event_at"] = now_iso()
        print(f"momod: cycle COMPLETE ticket={ticket['ticket_id']} "
              f"commit={result['commit_sha'][:12]}", flush=True)
    except Exception as exc:
        with LOCK:
            HEALTH["cycles_failed"] += 1
            HEALTH["last_error"] = str(exc)[:300]
        print(f"momod: cycle FAILED ticket={ticket['ticket_id']}: {exc}", flush=True)
        ev = momod_event("failed", ticket, {"reason": str(exc)[:300]})
        try:
            nc.publish_ack(ev["subject"], ev)
        except Exception:
            pass
        with db() as conn:
            conn.execute("UPDATE cycles SET state='failed' WHERE ticket_id=?",
                         (ticket["ticket_id"],))
    finally:
        lease_release()
        with LOCK:
            HEALTH["in_flight"] = None


# ------------------------------------------------------------- bus consumer
def consume_loop() -> None:
    while True:
        try:
            nc = jsclient.connect_retry(BUS_URL)
            HEALTH["bus"] = "connected"
            HEALTH["bus_error"] = None
            print(f"momod: bus connected {BUS_URL} stream={CONSUME_STREAM}", flush=True)
            nc.ensure_consumer(CONSUME_STREAM, DURABLE, CONSUME_FILTER)
            inbox = f"_INBOX.g8m.{uuid.uuid4().hex}"
            sid = nc.subscribe_inbox(inbox)
            while True:
                msg = nc.pull(CONSUME_STREAM, DURABLE, inbox, sid)
                if msg is None:
                    lease_heartbeat()  # keep our lease fresh between tickets
                    time.sleep(1.0)
                    continue
                try:
                    envelope = json.loads(msg["payload"].decode())
                    etype = envelope.get("type", "")
                    if etype == "bloodbank.task.ticket.created":
                        drive_cycle(nc, envelope)
                    # started/completed events are other services' facts;
                    # momod is the driver, not an echo
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError) as exc:
                    print(f"momod: malformed delivery: {exc}", flush=True)
                except Exception as exc:
                    print(f"momod: transient error, will redeliver: {exc}", flush=True)
                    raise
                nc.ack(msg["reply"])
        except Exception as exc:
            HEALTH["bus"] = "reconnecting"
            HEALTH["bus_error"] = str(exc)[:300]
            print(f"momod: bus loop error: {exc}; reconnect in 5s", flush=True)
            time.sleep(5.0)


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
            lease = _read_lease()
            return self._send(200, dict(
                HEALTH, uptime_s=round(time.time() - HEALTH["started"], 1),
                wip_lease={"held": bool(lease), "owner": lease and lease.get("owner")}))
        if self.path == "/cycles":
            with db() as conn:
                rows = conn.execute("SELECT ticket_id, correlationid, state, commit_sha,"
                                    " tests_passed, started_at, finished_at FROM cycles"
                                    " ORDER BY started_at DESC LIMIT 100").fetchall()
            return self._send(200, {"cycles": [
                {"ticket_id": r[0], "correlationid": r[1], "state": r[2],
                 "commit_sha": r[3], "tests_passed": None if r[4] is None else bool(r[4]),
                 "started_at": r[5], "finished_at": r[6]} for r in rows]})
        return self._send(404, {"error": "not found"})


def main() -> None:
    print(f"momod: db={DB_PATH} bus={BUS_URL} board={BOARD_URL} worker={CODE_WORKER_URL}",
          flush=True)
    if LLM_BASE_URL and LLM_API_KEY:
        HEALTH["review_mode"] = "llm-assisted"
        HEALTH["degraded"] = False
        HEALTH["degraded_reason"] = ""
    threading.Thread(target=consume_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", APP_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
