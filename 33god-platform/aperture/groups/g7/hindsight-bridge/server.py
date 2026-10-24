"""G7 hindsight-bridge — tails the BLOODBANK bus into pluggable memory backends.

Two jobs, both honest about degradation:

1. TAIL: durable JetStream pull consumer (g7-hindsight-bridge) over every
   bloodbank.evt.* envelope; each envelope is POSTed to every configured
   memory backend (GOD_MEMORY_BACKENDS, ';'-separated name=url pairs) at its
   /ingest endpoint. Per-backend failure degrades (logged + counted), never
   crashes, never blocks the ack — a memory outage must not stall the bus.

2. QUERY: /query fans out to every backend's /query, merges results, and
   optionally reranks via the EXTERNAL LLM endpoint. Keyword search needs no
   LLM and works with zero LLM config.

D1 ZERO-AAI, CLIENT-OWNED LLM: any embeddings/rerank call targets an external
OpenAI-compatible endpoint via GOD_LLM_BASE_URL / GOD_LLM_API_KEY — both EMPTY
by default. Empty => the bridge comes up DEGRADED (no embeddings, no rerank;
keyword search only) and /healthz says exactly which vars are empty. It never
crashes on missing config.

Backend HTTP contract (what a real hindsight server must implement):
    POST /ingest  {"events": [envelope, ...]}  -> 2xx {"stored": <int>}
    POST /query   {"q": str, "limit": int}      -> 2xx {"results": [ {...}, ...]}
This bundle ships `memory-reference`, a real working reference backend
(SQLite FTS5 keyword store) implementing that contract; swapping in a real
hindsight server is a GOD_MEMORY_BACKENDS config change (see DEFERRED.md).
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jsclient

# ---------------------------------------------------------------- env surface
LLM_BASE_URL = (os.environ.get("GOD_LLM_BASE_URL") or "").strip().rstrip("/")
LLM_API_KEY = (os.environ.get("GOD_LLM_API_KEY") or "").strip()
LLM_EMBED_MODEL = os.environ.get("GOD_LLM_EMBED_MODEL", "text-embedding-3-small")
LLM_RERANK_MODEL = (os.environ.get("GOD_LLM_RERANK_MODEL") or "").strip()
LLM_TIMEOUT = float(os.environ.get("GOD_LLM_TIMEOUT", "10"))

MEMORY_BACKENDS: dict[str, str] = {}
for _pair in (os.environ.get("GOD_MEMORY_BACKENDS") or "").split(";"):
    _name, _sep, _url = _pair.strip().partition("=")
    if _sep and _name and _url:
        MEMORY_BACKENDS[_name.rstrip("/")] = _url.rstrip("/")

BUS_URL = os.environ.get("GOD_BUS_NATS_URL", "nats://bus:4222")
CONSUME_STREAM = os.environ.get("GOD_CONSUME_STREAM", "BLOODBANK_EVENTS")
CONSUME_FILTER = os.environ.get("GOD_CONSUME_FILTER", "bloodbank.evt.>")
DURABLE = os.environ.get("GOD_BRIDGE_DURABLE", "g7-hindsight-bridge")
PORT = int(os.environ.get("GOD_BRIDGE_PORT", "8790"))
MAX_BODY = 1 << 20

LLM_READY = bool(LLM_BASE_URL and LLM_API_KEY)

HEALTH: dict = {"started": time.time(), "bus": "connecting", "bus_error": None,
                "tailed": 0, "fanned_out": 0, "backend_errors": 0,
                "last_error": None, "last_event_at": None}
LOCK = threading.Lock()

# ------------------------------------------------------- external HTTP helpers
import urllib.error  # noqa: E402
import urllib.request  # noqa: E402


def _http_json(url: str, payload: dict, timeout: float = 15.0,
               headers: dict | None = None) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def llm_status() -> dict:
    """Config-level readiness only. No startup probes: a slow external
    endpoint must not wedge the healthcheck; runtime failures degrade."""
    return {"configured": LLM_READY, "base_url": LLM_BASE_URL or None,
            "embed_model": LLM_EMBED_MODEL if LLM_READY else None,
            "rerank_model": LLM_RERANK_MODEL or None}


def degraded_reason() -> str | None:
    if LLM_READY:
        return None
    missing = []
    if not LLM_BASE_URL:
        missing.append("GOD_LLM_BASE_URL")
    if not LLM_API_KEY:
        missing.append("GOD_LLM_API_KEY")
    return ("degraded: no embeddings/rerank (" + " and ".join(missing)
            + " empty); keyword search only")


def embed(texts: list[str]) -> list[list[float]] | None:
    """EXTERNAL OpenAI-compatible /v1/embeddings. None on any failure or when
    degraded — callers fall back to keyword search, never crash."""
    if not LLM_READY:
        return None
    try:
        out = _http_json(f"{LLM_BASE_URL}/v1/embeddings",
                         {"model": LLM_EMBED_MODEL, "input": texts[:64]},
                         headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                         timeout=LLM_TIMEOUT)
        return [item["embedding"] for item in out["data"]]
    except Exception:
        return None


def rerank(query: str, documents: list[dict]) -> list[dict] | None:
    """Optional EXTERNAL /v1/rerank (OpenAI-compatible where offered).
    None when unconfigured/failing — keyword order stands."""
    if not (LLM_READY and LLM_RERANK_MODEL):
        return None
    try:
        out = _http_json(f"{LLM_BASE_URL}/v1/rerank",
                         {"model": LLM_RERANK_MODEL, "query": query,
                          "documents": [json.dumps(d)[:2000] for d in documents]},
                         headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                         timeout=LLM_TIMEOUT)
        order = [hit["index"] for hit in
                 sorted(out["results"], key=lambda h: -h.get("relevance_score", 0))]
        if sorted(order) == list(range(len(documents))):
            return [documents[i] for i in order]
    except Exception:
        pass
    return None


def fan_out(events: list[dict]) -> dict:
    """Push envelopes to every configured backend. Isolated failures are
    reported per backend; nothing raises."""
    report: dict[str, dict] = {}
    for name, url in MEMORY_BACKENDS.items():
        entry: dict = {"stored": 0}
        try:
            out = _http_json(f"{url}/ingest", {"events": events})
            entry["stored"] = int(out.get("stored", 0))
        except Exception as exc:
            entry["error"] = str(exc)[:300]
            with LOCK:
                HEALTH["backend_errors"] += 1
        report[name] = entry
    with LOCK:
        HEALTH["fanned_out"] += len(events)
    return report


def query_memory(q: str, limit: int) -> dict:
    """Fan-out query + merge + optional external rerank. Keyword search works
    with zero backends and zero LLM config (empty merge, mode=keyword)."""
    merged: list[dict] = []
    backends: dict[str, dict] = {}
    for name, url in MEMORY_BACKENDS.items():
        try:
            out = _http_json(f"{url}/query", {"q": q, "limit": limit})
            results = out.get("results", [])
            backends[name] = {"results": len(results)}
            for r in results:
                if isinstance(r, dict):
                    r.setdefault("backend", name)
                    merged.append(r)
        except Exception as exc:
            backends[name] = {"error": str(exc)[:300]}
    reranked = rerank(q, merged[:50]) if merged else None
    return {"q": q, "results": (reranked or merged)[:limit], "backends": backends,
            "reranked": bool(reranked),
            "mode": "semantic" if reranked else "keyword"}


# ----------------------------------------------------------------- bus tail
def tail_loop() -> None:
    while True:
        try:
            nc = jsclient.connect_retry(BUS_URL)
            HEALTH["bus"] = "connected"
            HEALTH["bus_error"] = None
            print(f"bridge: bus connected {BUS_URL} stream={CONSUME_STREAM}", flush=True)
            nc.ensure_consumer(CONSUME_STREAM, DURABLE, CONSUME_FILTER)
            inbox = f"_INBOX.g7b.{uuid.uuid4().hex}"
            sid = nc.subscribe_inbox(inbox)
            while True:
                msg = nc.pull(CONSUME_STREAM, DURABLE, inbox, sid)
                if msg is None:
                    time.sleep(1.0)
                    continue
                try:
                    envelope = json.loads(msg["payload"].decode())
                    if isinstance(envelope, dict):
                        fan_out([envelope])
                        with LOCK:
                            HEALTH["tailed"] += 1
                            HEALTH["last_event_at"] = envelope.get("time")
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                    # permanently malformed: ack (drop) rather than loop
                    with LOCK:
                        HEALTH["tailed"] += 1
                    print("bridge: malformed delivery dropped", flush=True)
                nc.ack(msg["reply"])
        except Exception as exc:
            HEALTH["bus"] = "reconnecting"
            HEALTH["bus_error"] = str(exc)[:300]
            print(f"bridge: bus loop error: {exc}; reconnect in 5s", flush=True)
            time.sleep(5.0)


# -------------------------------------------------------------------- HTTP
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
        reason = degraded_reason()
        self._send(200, {
            "ready": True,
            "degraded": reason is not None,
            "degraded_reason": reason,
            "llm": llm_status(),
            "backends": dict(MEMORY_BACKENDS),
            "backend_count": len(MEMORY_BACKENDS),
            "bus": HEALTH["bus"],
            "tailed": HEALTH["tailed"],
        })

    def do_POST(self) -> None:
        if self.path == "/query":
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BODY:
                    return self._send(413, {"error": f"body must be 1..{MAX_BODY} bytes"})
                body = json.loads(self.rfile.read(size))
                q = body.get("q")
                limit = int(body.get("limit", 20))
                if not isinstance(q, str) or not q.strip():
                    return self._send(400, {"error": "q must be a non-empty string"})
                if not 1 <= limit <= 100:
                    return self._send(400, {"error": "limit must be 1..100"})
            except (ValueError, TypeError, AttributeError) as exc:
                return self._send(400, {"error": str(exc)})
            return self._send(200, query_memory(q, limit))

        if self.path == "/ingest":
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BODY:
                    return self._send(413, {"error": f"body must be 1..{MAX_BODY} bytes"})
                body = json.loads(self.rfile.read(size))
                events = body.get("events") if isinstance(body, dict) else None
                if not isinstance(events, list) or not all(isinstance(e, dict) for e in events):
                    return self._send(400, {"error": "body must be {\"events\": [objects]}"})
            except (ValueError, TypeError) as exc:
                return self._send(400, {"error": str(exc)})
            return self._send(200, {"accepted": len(events), "fanout": fan_out(events)})

        if self.path == "/embed":
            if not LLM_READY:
                return self._send(503, {"error": degraded_reason() or "degraded"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BODY:
                    return self._send(413, {"error": f"body must be 1..{MAX_BODY} bytes"})
                texts = json.loads(self.rfile.read(size)).get("texts")
                if not isinstance(texts, list) or not texts \
                        or not all(isinstance(t, str) for t in texts):
                    return self._send(400, {"error": "body must be {\"texts\": [strings]}"})
            except (ValueError, TypeError, AttributeError) as exc:
                return self._send(400, {"error": str(exc)})
            vectors = embed(texts)
            if vectors is None:
                return self._send(502, {"error": "external embedding endpoint failed"})
            return self._send(200, {"model": LLM_EMBED_MODEL, "vectors": vectors})

        return self._send(404, {"error": "not found"})


def main() -> None:
    print(f"bridge: llm_ready={LLM_READY} backends={sorted(MEMORY_BACKENDS)}", flush=True)
    threading.Thread(target=tail_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
