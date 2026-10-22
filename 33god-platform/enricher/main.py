import os
import json
import logging
from fastapi import FastAPI, Request, Response
from sentence_transformers import SentenceTransformer
import psycopg2
import requests

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

# Both LLM calls (slop gate and session summary) target the AutomaticAI
# gateway, an OpenAI-compatible chat-completions endpoint. Per-call overrides:
# JEV_ENDPOINT/JEV_MODEL for the slop gate, SUMMARY_ENDPOINT/SESSION_SUMMARY_MODEL
# for the summary. Keys resolve the call-specific JEV_API_KEY / SUMMARY_API_KEY
# first and fall back to a shared OPENAI_COMPAT_API_KEY.
GATEWAY_CHAT_URL = "https://api.automaticai.io/v1/chat/completions"
GATEWAY_DEFAULT_MODEL = "automaticai/auto/fast"

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

    event_type = body.get("type", "")
    if "agent.tool.completed" in event_type:
        return await _do_handle_tool_completed(body)
    elif "agent.session.ended" in event_type:
        return await _do_handle_session_ended(body)
    
    return {"status": "SUCCESS"} # Ignore others

async def _do_handle_tool_completed(body: dict):
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
        return {"status": "RETRY"}

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO event_embeddings (event_id, embedding) VALUES (%s, %s) ON CONFLICT (event_id) DO NOTHING",
                    (event_id, embedding_list)
                )
    except psycopg2.Error as e:
        logger.error(f"DB Error on {event_id}: {e}")
        return {"status": "RETRY"}

    logger.info(f"Successfully embedded tool event {event_id}")
    
    # ---------------------------------------------------------
    # JEV Anti-Slop (System One classification) via AutomaticAI gateway
    # ---------------------------------------------------------
    jev_api_key = _gateway_key("JEV_API_KEY")
    jev_model = _gateway_model("JEV_MODEL")
    if jev_api_key:
        try:
            logger.info(f"Calling gateway JEV route ({jev_model}) for slop classification on {event_id}...")
            content = _chat_completion(
                _gateway_endpoint("JEV_ENDPOINT"),
                jev_api_key,
                jev_model,
                messages=[
                    {"role": "system", "content": "You are a classifier checking for 'slop' (unhelpful, generic, or unwanted automated AI output). Classify this event payload. Reply with JSON only: {\"is_slop\": boolean, \"confidence\": number, \"reason\": string}."},
                    {"role": "user", "content": text_to_embed}
                ],
                # json_schema preferred; _chat_completion drops it and retries
                # when an upstream rejects it, so parsing stays defensive.
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "slop_classification",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "is_slop": {"type": "boolean"},
                                "confidence": {"type": "number"},
                                "reason": {"type": "string"}
                            },
                            "required": ["is_slop", "confidence", "reason"],
                            "additionalProperties": False
                        },
                        "strict": True
                    }
                }
            )
            result = _parse_json_content(content)
            if result is not None and result.get("is_slop"):
                logger.info(f"JEV detected slop in {event_id}. Emitting bloodbank.review.slop.annotated...")
                session_id = body.get("correlationid")
                cwd = (
                    event_data.get("working_directory")
                    or event_data.get("cwd")
                    or (arguments.get("Cwd") if isinstance(arguments, dict) else None)
                )
                emit_event("bloodbank.evt.review.slop.annotated", {
                    "target_event_id": event_id,
                    "session_id": session_id,
                    "cwd": cwd,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "confidence": result.get("confidence"),
                    "reason": result.get("reason")
                })
        except Exception as err:
            logger.error(f"JEV API call failed: {err}")
    else:
        logger.info("No JEV_API_KEY/OPENAI_COMPAT_API_KEY set. Skipping live JEV evaluation.")

    return {"status": "SUCCESS"}


def emit_event(topic: str, payload: dict):
    # Dapr sidecar is at enricher-daprd:3501 (as mapped in compose.yaml for enricher-daprd)
    url = f"http://enricher-daprd:3501/v1.0/publish/bloodbank-pubsub/{topic}"
    try:
        resp = requests.post(url, json=payload, timeout=2)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to emit {topic}: {e}")

async def _do_handle_session_ended(body: dict):
    
    session_id = body.get("correlationid")
    event_data = body.get("data", {})
    
    if not session_id:
        logger.warning("DROP session ended: no session_id")
        return {"status": "DROP"}
    
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

    # ---------------------------------------------------------
    # CALL LLM (AutomaticAI gateway) TO SUMMARIZE SESSION
    # ---------------------------------------------------------
    api_key = _gateway_key("SUMMARY_API_KEY")
    summary_model = _gateway_model("SESSION_SUMMARY_MODEL")
    summary = ""
    if api_key:
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
    else:
        logger.info("No SUMMARY_API_KEY/OPENAI_COMPAT_API_KEY set, generating basic heuristic summary.")
        summary = f"Session completed with {len(tool_logs)} tool invocations."

    # Emit the session completed report
    emit_event("bloodbank.evt.report.session.completed", {
        "session_id": session_id,
        "cwd": session_cwd,
        "summary": summary,
        "event_count": len(events)
    })
    
    logger.info(f"Successfully rolled up session {session_id}")
    return {"status": "SUCCESS"}
