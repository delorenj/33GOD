"""G7 enrichment worker — ONE real pass over the Bloodbank bus.

Consumes canonical bloodbank.evt.* events (durable JetStream pull consumer,
raw NATS protocol via jsclient), applies a REAL deterministic extraction pass
(typed identity + digest + size class + payload-key shape — fields the source
envelope does not carry), persists the extraction into a worker-owned side
table (SQLite on the group volume), and publishes a derived canonical event
back onto the bus:

    type     bloodbank.<domain>.<entity>.enriched      (4 tokens)
    subject  bloodbank.evt.<domain>.<entity>.enriched  (5 tokens, evt marker)
    causationid = SOURCE event id  — the chain is the point

Deterministic derived ids (UUIDv5 over source id) make redelivery idempotent:
candystore's ON CONFLICT (id) DO NOTHING dedupes, and the side table upserts
by source id. No LLM anywhere in this pass — deterministic extraction only;
LLM-backed passes are the bridge's pluggable client-owned surface.

Also serves HTTP on APP_PORT: /healthz (state + counters) and POST /inqueue
(accept a canonical event envelope directly — same validation, same pass,
publishes derived event; used by the smoke and by callers without bus write
access).
"""
from __future__ import annotations

import hashlib
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
PUBLISH_STREAM = os.environ.get("GOD_OUTBOX_STREAM", "BLOODBANK_EVENTS")
CONSUME_STREAM = os.environ.get("GOD_CONSUME_STREAM", "BLOODBANK_EVENTS")
CONSUME_FILTER = os.environ.get("GOD_CONSUME_FILTER", "bloodbank.evt.>")
# Enriching our own derived output would loop; the filter excludes nothing by
# itself (subjects end .enriched), so the pass itself must skip derived types.
DURABLE = os.environ.get("GOD_ENRICH_DURABLE", "g7-enrichment")
APP_PORT = int(os.environ.get("APP_PORT", "8791"))
DB_PATH = os.environ.get("GOD_ENRICH_DB", "/data/enrichment.db")

NAMESPACE = uuid.UUID("6f1a2c34-83b5-4d97-9f0e-a1b2c3d4e5f6")
SOURCE_URN = "urn:33god:aperture:g7-enrichment"
SERVICE_NAME = "aperture-g7-enrichment"

HEALTH: dict = {"started": time.time(), "bus": "connecting", "bus_error": None,
                "consumed": 0, "enriched": 0, "published": 0, "rejected": 0,
                "errors": 0, "last_error": None, "last_event_at": None}
LOCK = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# ---------------------------------------------------------------- side table
def db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS extraction (
        source_id     TEXT PRIMARY KEY,
        source_type   TEXT NOT NULL,
        domain        TEXT NOT NULL,
        entity        TEXT NOT NULL,
        action        TEXT NOT NULL,
        producer      TEXT,
        service       TEXT,
        actor_cli     TEXT,
        actor_type    TEXT,
        payload_keys  TEXT NOT NULL,
        payload_sha256 TEXT NOT NULL,
        payload_bytes INTEGER NOT NULL,
        size_class    TEXT NOT NULL,
        correlationid TEXT,
        derived_id    TEXT NOT NULL,
        extracted_at  TEXT NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_extraction_domain ON extraction(domain)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_extraction_derived ON extraction(derived_id)")
    return conn


# ------------------------------------------------------------- the real pass
def extract(envelope: dict) -> dict | None:
    """Typed extraction. Produces fields the source does NOT carry: canonical
    (domain,entity,action) split, payload digest + size class, payload key
    shape, actor identity, deterministic derived id. None = rejected."""
    if not isinstance(envelope, dict):
        return None
    etype = envelope.get("type")
    subject = envelope.get("subject")
    data = envelope.get("data")
    sid = envelope.get("id")
    if not isinstance(etype, str) or not isinstance(data, dict) or not sid:
        return None
    tokens = etype.split(".")
    if len(tokens) != 4 or tokens[0] != "bloodbank":
        return None
    if subject != "bloodbank.evt." + ".".join(tokens[1:]):
        return None
    try:
        sid = str(uuid.UUID(str(sid)))
    except (ValueError, AttributeError, TypeError):
        return None
    # Never enrich derived events (loop guard) — also skip our own urn.
    if tokens[3] == "enriched" or envelope.get("source") == SOURCE_URN:
        return None
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"))
    actor = envelope.get("actor") or {}
    return {
        "source_id": sid,
        "source_type": etype,
        "domain": tokens[1],
        "entity": tokens[2],
        "action": tokens[3],
        "producer": envelope.get("producer"),
        "service": envelope.get("service"),
        "actor_cli": actor.get("cli"),
        "actor_type": actor.get("type"),
        "payload_keys": sorted(data.keys()),
        "payload_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "payload_bytes": len(raw),
        "size_class": "tiny" if len(raw) < 256 else "small" if len(raw) < 4096 else "large",
        "correlationid": envelope.get("correlationid"),
        "derived_id": str(uuid.uuid5(NAMESPACE, sid)),
    }


def derive(envelope: dict, x: dict) -> dict:
    """Canonical derived event. type/subject agree on (domain,entity); the
    payload is built FROM the extraction (the transform is visible in data)."""
    etype = f"bloodbank.{x['domain']}.{x['entity']}.enriched"
    corr = envelope.get("correlationid") or x["source_id"]
    return {
        "specversion": "1.0",
        "id": x["derived_id"],
        "source": SOURCE_URN,
        "type": etype,
        "subject": f"bloodbank.evt.{x['domain']}.{x['entity']}.enriched",
        "time": now_iso(),
        "datacontenttype": "application/json",
        "correlationid": corr,
        "causationid": x["source_id"],
        "producer": SERVICE_NAME,
        "service": "aperture-g7",
        "domain": x["domain"],
        "kind": "event",
        "ordering_key": f"g7:enrichment:{x['source_id']}",
        "actor": {"type": "service", "agent_id": SERVICE_NAME,
                  "cli": None, "provider": None, "model": None},
        "data": {
            "pass": "typed-extraction-v1",
            "extraction": x,
        },
    }


def persist(conn: sqlite3.Connection, x: dict) -> None:
    conn.execute("""INSERT INTO extraction (
        source_id, source_type, domain, entity, action, producer, service,
        actor_cli, actor_type, payload_keys, payload_sha256, payload_bytes,
        size_class, correlationid, derived_id, extracted_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(source_id) DO NOTHING""", (
        x["source_id"], x["source_type"], x["domain"], x["entity"], x["action"],
        x["producer"], x["service"], x["actor_cli"], x["actor_type"],
        json.dumps(x["payload_keys"]), x["payload_sha256"], x["payload_bytes"],
        x["size_class"], x["correlationid"], x["derived_id"], now_iso()))
    conn.commit()


def process(conn: sqlite3.Connection, nc: jsclient.NatsConn, envelope: dict) -> dict:
    """Validate -> extract -> persist -> publish. Returns a status dict."""
    x = extract(envelope)
    if x is None:
        with LOCK:
            HEALTH["rejected"] += 1
        return {"status": "rejected", "reason": "not a canonical non-derived bloodbank.evt event"}
    persist(conn, x)
    derived = derive(envelope, x)
    ack = nc.publish_ack(derived["subject"], derived)
    if not isinstance(ack.get("seq"), int):
        raise jsclient.NatsError(f"publish ack missing seq: {ack!r}")
    with LOCK:
        HEALTH["enriched"] += 1
        HEALTH["published"] += 1
        HEALTH["last_event_at"] = now_iso()
    return {"status": "enriched", "source_id": x["source_id"],
            "derived_id": x["derived_id"], "derived_type": derived["type"],
            "causationid": derived["causationid"], "sequence": ack["seq"]}


# ------------------------------------------------------------- bus consumer
def consume_loop() -> None:
    conn = db()
    while True:
        try:
            nc = jsclient.connect_retry(BUS_URL)
            HEALTH["bus"] = "connected"
            HEALTH["bus_error"] = None
            print(f"worker: bus connected {BUS_URL} stream={CONSUME_STREAM}", flush=True)
            nc.ensure_consumer(CONSUME_STREAM, DURABLE, CONSUME_FILTER)
            inbox = f"_INBOX.g7e.{uuid.uuid4().hex}"
            sid = nc.subscribe_inbox(inbox)
            while True:
                msg = nc.pull(CONSUME_STREAM, DURABLE, inbox, sid)
                if msg is None:
                    time.sleep(1.0)
                    continue
                envelope = json.loads(msg["payload"].decode())
                # deliver_subject / ack needed even on rejection: explicit-ack
                # policy means an un-acked delivery redelivers (max_deliver 10)
                # then stops. A malformed payload is a permanent defect: ack it
                # (drop) so it never poison-loops.
                try:
                    result = process(conn, nc, envelope)
                    if result["status"] == "rejected":
                        print(f"worker: rejected {envelope.get('id')}: {result['reason']}", flush=True)
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError) as exc:
                    with LOCK:
                        HEALTH["rejected"] += 1
                    print(f"worker: malformed delivery: {exc}", flush=True)
                except Exception as exc:  # transient: no ack -> redelivery
                    with LOCK:
                        HEALTH["errors"] += 1
                        HEALTH["last_error"] = str(exc)[:300]
                    print(f"worker: transient error, will redeliver: {exc}", flush=True)
                    raise
                with LOCK:
                    HEALTH["consumed"] += 1
                nc.ack(msg["reply"])
        except Exception as exc:
            HEALTH["bus"] = "reconnecting"
            HEALTH["bus_error"] = str(exc)[:300]
            print(f"worker: bus loop error: {exc}; reconnect in 5s", flush=True)
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

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        print(format % args, flush=True)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            return self._send(200, dict(HEALTH, uptime_s=round(time.time() - HEALTH["started"], 1)))
        if self.path == "/extractions":
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute(
                    "SELECT source_id, source_type, domain, entity, derived_id, size_class "
                    "FROM extraction ORDER BY extracted_at DESC LIMIT 100").fetchall()
            return self._send(200, {"extractions": [
                {"source_id": r[0], "source_type": r[1], "domain": r[2], "entity": r[3],
                 "derived_id": r[4], "size_class": r[5]} for r in rows]})
        return self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/inqueue":
            return self._send(404, {"error": "not found"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= (1 << 20):
                return self._send(413, {"error": "body must be 1..1048576 bytes"})
            envelope = json.loads(self.rfile.read(size))
        except (ValueError, TypeError) as exc:
            return self._send(400, {"error": str(exc)})
        if extract(envelope) is None:
            return self._send(400, {"error": "not a canonical non-derived bloodbank.evt event"})
        try:
            with _BUS as nc:
                result = process(db(), nc, envelope)
        except _NoBus as exc:
            return self._send(503, {"error": f"bus unavailable: {exc}"})
        except Exception as exc:
            return self._send(502, {"error": str(exc)[:300]})
        return self._send(200, result)


class _NoBus(Exception):
    pass


class _BusHolder:
    """One short-lived connection per /inqueue call — the consumer loop owns
    the long-lived one. Keeps the handler honest under concurrency."""

    def __enter__(self):
        try:
            return jsclient.NatsConn(BUS_URL)
        except (OSError, jsclient.NatsError) as exc:
            raise _NoBus(str(exc)) from exc

    def __exit__(self, *exc):
        return False


_BUS = _BusHolder()


def main() -> None:
    print(f"worker: db={DB_PATH} bus={BUS_URL} consume_stream={CONSUME_STREAM} "
          f"publish_stream={PUBLISH_STREAM}", flush=True)
    threading.Thread(target=consume_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", APP_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
