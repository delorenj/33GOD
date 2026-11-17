import os
import json
import logging
import time
from collections import OrderedDict
from fastapi import FastAPI, Request, Response
from fastapi.concurrency import run_in_threadpool
from sentence_transformers import SentenceTransformer
import psycopg2
import requests

from bb_envelope import (
    SESSION_ANNOTATED_SUBJECT,
    build_session_annotated,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("enricher")

app = FastAPI()

# Load model locally
logger.info("Loading SentenceTransformer model BAAI/bge-small-en-v1.5...")
model = SentenceTransformer('BAAI/bge-small-en-v1.5')
logger.info("Model loaded.")

DB_URL = os.environ.get("DATABASE_URL", "postgresql://candystore:***@candystore-postgres:5432/candystore")

def get_db():
    return psycopg2.connect(DB_URL)

# --- event_embeddings parent-row race (33GOD-95) -----------------------------
# The enricher and Candystore consume BLOODBANK_EVENTS through separate durable
# consumers, so an embedding can be ready before Candystore has committed the
# parent `events` row; event_embeddings.event_id REFERENCES events(id), so that
# INSERT raises a foreign-key violation (SQLSTATE 23503). The bound, in two tiers:
#
#   1. In one delivery: retry the INSERT with exponential backoff
#      (EMBED_PARENT_BACKOFF_START seconds, doubling, capped at
#      EMBED_PARENT_BACKOFF_MAX) for at most EMBED_PARENT_WAIT_SECONDS total
#      (default 20s: 0.25+0.5+1+2+4+4+4+4+... ). Far under the Dapr durable's
#      ackWait of 300s, and the durable config is deliberately untouched.
#   2. Across deliveries: if the parent is still absent, answer RETRY so Dapr
#      redelivers, up to EMBED_PARENT_MAX_ATTEMPTS deliveries per event id
#      (default 3, so about a minute of total patience), counted in a bounded
#      in-process LRU. After that the event is written to Candystore's
#      dead_letter table (reason "embedding_parent_absent"), logged at ERROR,
#      and DROPped, so a missing parent is durably visible and never becomes a
#      hot redelivery loop. No orphan embedding is ever written.
#
# DROP happens only once the dead_letter row is committed (_give_up); if that write
# fails the delivery answers RETRY for at most DEAD_LETTER_WRITE_EXTRA_ATTEMPTS more.
# Embed failures and non-FK DB errors use the same shape (EMBED_ERROR_MAX_ATTEMPTS,
# exponential backoff). Session-annotation publish failures back off too, reuse the
# cached roll-up (no repeated LLM calls) and dead-letter on exhaustion.
# The attempt counter is per process: a restart grants a fresh set of attempts.
# Tradeoff: ~1 min of patience for a late parent. A longer Candystore outage
# dead-letters the embedding with its exact envelope for replay (reason
# embedding_parent_absent); raise EMBED_PARENT_MAX_ATTEMPTS to widen the window.
def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default

DEAD_LETTER_REASON_PARENT_ABSENT = "embedding_parent_absent"
DEAD_LETTER_REASON_PUBLISH_FAILED = "session_annotation_publish_failed"
ATTEMPT_LRU_SIZE = 10_000
FK_VIOLATION_SQLSTATE = "23503"

# Injectable clock/sleep so tests drive the backoff deterministically.
_sleep = time.sleep
_monotonic = time.monotonic

class _AttemptCounter:
    """Bounded LRU of delivery attempts keyed by event id."""

    def __init__(self, size: int = ATTEMPT_LRU_SIZE):
        self._size = size
        self._counts: OrderedDict[str, int] = OrderedDict()

    def bump(self, key: str) -> int:
        count = self._counts.pop(key, 0) + 1
        self._counts[key] = count
        while len(self._counts) > self._size:
            self._counts.popitem(last=False)
        return count

    def clear(self, key: str) -> None:
        self._counts.pop(key, None)

    def __len__(self) -> int:
        return len(self._counts)

class _BoundedCache:
    """Small LRU of per-event roll-ups so a publish retry does not redo the LLM call."""

    def __init__(self, size: int = 256):
        self._size = size
        self._items: OrderedDict[str, dict] = OrderedDict()

    def get(self, key: str):
        item = self._items.get(key)
        if item is not None:
            self._items.move_to_end(key)
        return item

    def put(self, key: str, value: dict) -> None:
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self._size:
            self._items.popitem(last=False)

    def pop(self, key: str) -> None:
        self._items.pop(key, None)

_rollup_cache = _BoundedCache()
_embedding_attempts = _AttemptCounter()   # deliveries where the parent events row was absent
_error_attempts = _AttemptCounter()       # deliveries that failed on embed / non-FK DB errors
_publish_attempts = _AttemptCounter()

def _is_fk_violation(err: Exception) -> bool:
    return getattr(err, "pgcode", None) == FK_VIOLATION_SQLSTATE

def _insert_embedding_waiting_for_parent(event_id: str, embedding_list: list) -> bool:
    """INSERT the embedding, waiting a bounded time for the parent event row.

    Returns True once the embedding row exists (ON CONFLICT DO NOTHING makes a
    duplicate delivery a no-op), False when the parent never appeared inside
    EMBED_PARENT_WAIT_SECONDS. Any other DB error propagates.
    """
    budget = _env_float("EMBED_PARENT_WAIT_SECONDS", 20.0)
    delay = _env_float("EMBED_PARENT_BACKOFF_START", 0.25)
    delay_cap = _env_float("EMBED_PARENT_BACKOFF_MAX", 4.0)
    started = _monotonic()
    conn = get_db()
    try:
        while True:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO event_embeddings (event_id, embedding) VALUES (%s, %s) ON CONFLICT (event_id) DO NOTHING",
                        (event_id, embedding_list)
                    )
                conn.commit()
                return True
            except psycopg2.Error as e:
                conn.rollback()
                if not _is_fk_violation(e):
                    raise
            remaining = budget - (_monotonic() - started)
            if remaining <= 0:
                return False
            _sleep(min(delay, remaining))
            delay = min(delay * 2, delay_cap)
    finally:
        conn.close()

def _record_dead_letter(body: dict, event_id: str, reason: str, error: str) -> bool:
    """Record an event the enricher gave up on in Candystore's dead_letter table.

    Same table and columns Candystore itself uses for events it refuses; raw is
    the exact delivered envelope so it can be replayed once the cause is fixed.
    Returns True only when the row was committed.
    """
    topic = body.get("subject") or body.get("topic")
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO dead_letter (event_id, topic, reason, error, raw) VALUES (%s, %s, %s, %s, %s)",
                (event_id, topic, reason, error,
                 psycopg2.Binary(json.dumps(body).encode("utf-8"))),
            )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Could not record dead_letter ({reason}) for {event_id}: {e}")
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

def _give_up(counter: "_AttemptCounter", key: str, body: dict, event_id: str,
             reason: str, error: str, attempts: int, max_attempts: int) -> dict:
    """Attempts are exhausted: DROP, but only once a dead_letter row exists.

    If the dead_letter write itself fails, answer RETRY and keep the counter so
    the next delivery tries the write again, for at most
    DEAD_LETTER_WRITE_EXTRA_ATTEMPTS more deliveries. Past that the event is
    DROPped with an ERROR log (still bounded: never a hot redelivery loop).
    """
    if _record_dead_letter(body, event_id, reason, error):
        counter.clear(key)
        logger.error(f"DROP {event_id}: {error} (dead_letter recorded, reason {reason})")
        return {"status": "DROP"}
    hard_cap = max_attempts + _env_int("DEAD_LETTER_WRITE_EXTRA_ATTEMPTS", 3)
    if attempts < hard_cap:
        logger.error(f"dead_letter write failed for {event_id} ({reason}); RETRY so it is attempted again (delivery {attempts}/{hard_cap})")
        return {"status": "RETRY"}
    counter.clear(key)
    logger.error(f"DROP {event_id}: {error} (dead_letter WRITE FAILED {attempts} times, reason {reason}; event lost)")
    return {"status": "DROP"}

def _backoff(prefix: str, attempts: int, start: float, cap: float) -> None:
    """Sleep before answering RETRY so a quick redelivery cannot burn its attempts in a blip."""
    delay = min(_env_float(f"{prefix}_BACKOFF_START", start) * (2 ** (attempts - 1)), _env_float(f"{prefix}_BACKOFF_MAX", cap))
    if delay > 0:
        _sleep(delay)

# Session-end summary optionally targets the AutomaticAI gateway when
# SUMMARY_API_KEY / OPENAI_COMPAT_API_KEY is explicitly configured, defaulting
# to automaticai/free so background summaries never burn subscription pools.
# Per-tool-call LLM slop classification is intentionally retired: tool events
# fire multiple times per second across the fleet and are embedded locally only.
GATEWAY_CHAT_URL = "https://api.automaticai.io/v1/chat/completions"
GATEWAY_DEFAULT_MODEL = "automaticai/free"

def _gateway_endpoint(env_override: str) -> str:
    value = os.environ.get(env_override, "")
    return value or GATEWAY_CHAT_URL

def _gateway_model(env_override: str) -> str:
    value = os.environ.get(env_override, "")
    return value or GATEWAY_DEFAULT_MODEL

def _gateway_key(specific_key_env: str) -> str | None:
    return os.environ.get(specific_key_env, "") or os.environ.get("OPENAI_COMPAT_API_KEY", "") or None

def _chat_completion(endpoint: str, api_key: str, model: str, messages: list, response_format: dict | None = None, timeout: int = 30) -> str:
    """POST one chat completion and return the assistant content.

    The gateway forwards response_format to the upstream model, but not every
    upstream accepts json_schema; on a 400 we retry once without
    response_format, so callers must parse the returned content defensively.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages}
    if response_format is not None:
        payload["response_format"] = response_format
    r = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
    content = ""
    try:
        content = (r.json().get("choices") or [{}])[0].get("message", {}).get("content") or ""
    except Exception:
        pass
    # Two retry triggers, once each: (a) upstream rejects response_format with
    # a 400; (b) 200 with EMPTY content — glm-5.3-flash spends small budgets on
    # reasoning_content and returns an empty completion under response_format
    # (seen live 2026-10-22: json_schema 200-empty, plain prompt 200 with JSON).
    retry_worthy = (r.status_code == 400) or (r.status_code < 300 and not content.strip())
    if retry_worthy and "response_format" in payload:
        logger.warning(f"{model} empty/rejected response_format (status {r.status_code}); retrying without it")
        del payload["response_format"]
        r = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
        try:
            content = (r.json().get("choices") or [{}])[0].get("message", {}).get("content") or ""
        except Exception:
            content = ""
    r.raise_for_status()
    return content

def _parse_json_content(content) -> dict | None:
    """Best-effort JSON parse of assistant content; tolerates markdown fences.

    Returns None whenever the content is empty or not valid JSON — the slop
    gate then just skips annotation instead of crashing the event handler.
    """
    if not content:
        return None
    text = str(content).strip()
    if text.startswith("```"):
        text = "\n".join(line for line in text.splitlines() if not line.strip().startswith("```")).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"LLM content was not parseable JSON: {text[:200]}")
        return None
    return parsed if isinstance(parsed, dict) else None

@app.get("/dapr/subscribe")
def subscribe():
    return [
        {
            "pubsubname": "bloodbank-pubsub",
            "topic": "bloodbank.evt.>",
            "route": "/events/all"
        }
    ]

@app.post("/events/all")
async def handle_all_events(request: Request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return Response(status_code=200)

    # The handlers block (embedding, Postgres, two gateway LLM calls). Run them
    # in the threadpool: inside the event loop they serialized every delivery
    # and the JetStream backlog outgrew the enricher (2026-10-22).
    event_type = body.get("type", "")
    if "agent.tool.completed" in event_type:
        return await run_in_threadpool(_do_handle_tool_completed, body)
    elif "agent.session.ended" in event_type:
        return await run_in_threadpool(_do_handle_session_ended, body)
    
    return {"status": "SUCCESS"} # Ignore others

def _do_handle_tool_completed(body: dict):
    event_id = body.get("id")
    event_data = body.get("data", {})
    
    if not event_id:
        logger.warning("DROP event: no event id")
        return {"status": "DROP"}

    tool_name = event_data.get("tool_name") or event_data.get("name")
    arguments = event_data.get("arguments", {})
    status = event_data.get("status") or event_data.get("outcome") or event_data.get("success")

    if not tool_name:
        logger.warning(f"DROP event {event_id}: not a tool")
        return {"status": "DROP"}

    args_str = json.dumps(arguments) if isinstance(arguments, dict) else str(arguments)
    text_to_embed = f"Tool: {tool_name} | Args: {args_str} | Status: {status}"

    try:
        embedding = model.encode(text_to_embed)
        embedding_list = embedding.tolist()
    except Exception as e:
        logger.error(f"Failed to embed {event_id}: {e}")
        return _retry_or_give_up(body, event_id, "embedding_failed", f"embedding failed: {e}")

    try:
        stored = _insert_embedding_waiting_for_parent(event_id, embedding_list)
    except psycopg2.Error as e:
        logger.error(f"DB Error on {event_id}: {e}")
        return _retry_or_give_up(body, event_id, "embedding_db_error", f"embedding insert failed: {e}")

    if not stored:
        attempts = _embedding_attempts.bump(event_id)
        max_attempts = _env_int("EMBED_PARENT_MAX_ATTEMPTS", 3)
        if attempts < max_attempts:
            logger.warning(f"Parent event {event_id} not in Candystore yet (delivery {attempts}/{max_attempts}); RETRY")
            return {"status": "RETRY"}
        return _give_up(
            _embedding_attempts, event_id, body, event_id, DEAD_LETTER_REASON_PARENT_ABSENT,
            f"parent events row absent after {attempts} deliveries; embedding not written",
            attempts, max_attempts,
        )

    _embedding_attempts.clear(event_id)
    _error_attempts.clear(event_id)
    logger.info(f"Successfully embedded tool event {event_id}")
    return {"status": "SUCCESS"}


def _retry_or_give_up(body: dict, event_id: str, reason: str, error: str) -> dict:
    """Bounded handling for embed failures and non-FK DB errors (33GOD-95 review).

    A permanent failure (e.g. a non-uuid event id, SQLSTATE 22P02) used to make a
    hot Nak/redelivery loop. Now: short exponential backoff inside the delivery,
    RETRY up to EMBED_ERROR_MAX_ATTEMPTS deliveries per event id (default 5),
    then dead_letter (reason embedding_failed / embedding_db_error) and DROP.
    """
    attempts = _error_attempts.bump(event_id)
    max_attempts = _env_int("EMBED_ERROR_MAX_ATTEMPTS", 5)
    if attempts < max_attempts:
        _backoff("EMBED_ERROR", attempts, 0.5, 8.0)
        return {"status": "RETRY"}
    return _give_up(_error_attempts, event_id, body, event_id, reason, error, attempts, max_attempts)


def publish_envelope(topic: str, envelope: dict) -> None:
    """Publish a complete Bloodbank envelope through the Dapr sidecar.

    Content-Type MUST be application/cloudevents+json: Dapr then passes the
    envelope through as-is. With application/json Dapr wraps the body as
    com.dapr.event.sent and the Bloodbank fields vanish (33GOD-95). Raises on
    any failure; callers decide RETRY vs DROP.
    """
    # Dapr sidecar is at enricher-daprd:3501 (as mapped in compose.yaml for enricher-daprd)
    url = f"http://enricher-daprd:3501/v1.0/publish/bloodbank-pubsub/{topic}"
    resp = requests.post(
        url,
        data=json.dumps(envelope).encode("utf-8"),
        headers={"Content-Type": "application/cloudevents+json"},  # literal on purpose: tests/test_dapr_publish_guard.py scans for it
        timeout=5,
    )
    resp.raise_for_status()

def _summarize_session(session_id: str) -> dict:
    """Fetch the session from Candystore and summarize it.

    Returns the roll-up dict, or {"status": ...} when the delivery should end
    here (RETRY on a failed fetch, SUCCESS for an empty session).
    """
    logger.info(f"Session {session_id} ended. Rolling up events...")

    # Fetch all events for the session from candystore
    try:
        resp = requests.get(f"http://candystore:3001/sessions/{session_id}", timeout=5)
        resp.raise_for_status()
        session_data = resp.json()
        events = session_data.get("events", [])
    except Exception as e:
        logger.error(f"Failed to fetch events for session {session_id}: {e}")
        return {"status": "RETRY"}

    if not events:
        logger.info(f"No events found for session {session_id}")
        return {"status": "SUCCESS"}

    # Extract tool summaries and find the cwd
    tool_logs = []
    session_cwd = None
    for e in events:
        d = e.get("data", {})
        if session_cwd is None:
            payload = d.get("payload") if isinstance(d.get("payload"), dict) else {}
            for value in (d.get("working_directory"), payload.get("cwd"), d.get("cwd")):
                if isinstance(value, str) and value.strip():
                    session_cwd = value.strip()
                    break

        if "tool_name" in d or "name" in d:
            t_name = d.get("tool_name") or d.get("name")
            t_args = d.get("arguments", {})
            t_status = d.get("status") or d.get("outcome", "unknown")
            tool_logs.append(f"- {t_name} ({t_status}): {str(t_args)[:100]}...")

    tool_text = "\n".join(tool_logs)
    summary_source = "heuristic"

    # ---------------------------------------------------------
    # CALL LLM (AutomaticAI gateway) TO SUMMARIZE SESSION
    # ---------------------------------------------------------
    api_key = _gateway_key("SUMMARY_API_KEY")
    summary_model = _gateway_model("SESSION_SUMMARY_MODEL")
    summary = ""
    if api_key:
        summary_source = "gateway"
        logger.info(f"Calling gateway ({summary_model}) for session summary...")
        try:
            summary = _chat_completion(
                _gateway_endpoint("SUMMARY_ENDPOINT"),
                api_key,
                summary_model,
                messages=[
                    {"role": "system", "content": "Summarize this agent session into a short dense paragraph (3-4 sentences max). Focus on what was achieved."},
                    {"role": "user", "content": f"Session Tool Calls:\n{tool_text}"}
                ]
            )
        except Exception as err:
            logger.error(f"Gateway LLM call failed: {err}")
            summary = f"Automated summary failed. Included {len(events)} events."
            summary_source = "gateway_failed"
    else:
        logger.info("No SUMMARY_API_KEY/OPENAI_COMPAT_API_KEY set, generating basic heuristic summary.")
        summary = f"Session completed with {len(tool_logs)} tool invocations."

    return {
        "summary": summary,
        "summary_source": summary_source,
        "cwd": session_cwd,
        "event_count": len(events),
        "tool_call_count": len(tool_logs),
    }


def _do_handle_session_ended(body: dict):
    
    session_id = body.get("correlationid")
    
    if not session_id:
        logger.warning("DROP session ended: no session_id")
        return {"status": "DROP"}
    
    # A publish retry must only re-publish: reuse the roll-up (and its gateway LLM
    # summary) computed on the first delivery of this session.ended event.
    rollup_key = body.get("id") if isinstance(body.get("id"), str) else None
    rollup = _rollup_cache.get(rollup_key) if rollup_key else None
    if rollup is None:
        outcome = _summarize_session(session_id)
        if "status" in outcome:
            return outcome
        rollup = outcome
        if rollup_key:
            _rollup_cache.put(rollup_key, rollup)

    # Annotate the session.ended event with the roll-up. The id is derived from
    # the session.ended id, so a redelivery re-publishes the same event and
    # Candystore (dedup on id) keeps one summary.
    try:
        envelope = build_session_annotated(
            source_event=body,
            session_id=session_id,
            cwd=rollup["cwd"],
            summary=rollup["summary"],
            summary_source=rollup["summary_source"],
            event_count=rollup["event_count"],
            tool_call_count=rollup["tool_call_count"],
        )
    except ValueError as e:
        logger.warning(f"DROP session ended {session_id}: {e}")
        if rollup_key:
            _rollup_cache.pop(rollup_key)
        return {"status": "DROP"}

    event_key = envelope["id"]
    try:
        publish_envelope(SESSION_ANNOTATED_SUBJECT, envelope)
    except Exception as e:
        attempts = _publish_attempts.bump(event_key)
        max_attempts = _env_int("PUBLISH_MAX_ATTEMPTS", 5)
        if attempts < max_attempts:
            logger.error(f"Failed to publish session report for {session_id} (attempt {attempts}/{max_attempts}): {e}; RETRY")
            _backoff("PUBLISH", attempts, 1.0, 8.0)
            return {"status": "RETRY"}
        status = _give_up(
            _publish_attempts, event_key, body, body.get("id") or event_key, DEAD_LETTER_REASON_PUBLISH_FAILED,
            f"session annotation publish failed {attempts} times, last error: {e}",
            attempts, max_attempts,
        )
        if status["status"] == "DROP" and rollup_key:
            _rollup_cache.pop(rollup_key)
        return status

    _publish_attempts.clear(event_key)
    if rollup_key:
        _rollup_cache.pop(rollup_key)
    logger.info(f"Successfully rolled up session {session_id} (annotation {event_key})")
    return {"status": "SUCCESS"}
