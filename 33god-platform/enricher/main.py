import os
import json
import logging
from fastapi import FastAPI, Request, Response
from sentence_transformers import SentenceTransformer
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("enricher")

app = FastAPI()

# Load model locally
logger.info("Loading SentenceTransformer model BAAI/bge-small-en-v1.5...")
model = SentenceTransformer('BAAI/bge-small-en-v1.5')
logger.info("Model loaded.")

DB_URL = os.environ.get("DATABASE_URL", "postgresql://candystore:candystore@candystore-postgres:5432/candystore")

def get_db():
    return psycopg2.connect(DB_URL)

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
    # JEV Anti-Slop (System One classification) via OpenRouter
    # ---------------------------------------------------------
    jev_endpoint = os.environ.get("JEV_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions")
    jev_api_key = os.environ.get("JEV_API_KEY")
    if jev_api_key:
        try:
            logger.info(f"Calling OpenRouter JEV route for slop classification on {event_id}...")
            r = requests.post(jev_endpoint, headers={
                "Authorization": f"Bearer {jev_api_key}",
                "Content-Type": "application/json"
            }, json={
                "model": "aai/openrouter-personal",
                "messages": [
                    {"role": "system", "content": "You are a classifier checking for 'slop' (unhelpful, generic, or unwanted automated AI output). Classify this event payload."},
                    {"role": "user", "content": text_to_embed}
                ],
                "response_format": {
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
            }, timeout=10)
            r.raise_for_status()
            res = r.json()
            
            # Parse the structured output
            content = res.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                try:
                    result = json.loads(content)
                    if result.get("is_slop"):
                        logger.info(f"JEV detected slop in {event_id}. Emitting bloodbank.review.slop.annotated...")
                        emit_event("bloodbank.evt.review.slop.annotated", {
                            "target_event_id": event_id,
                            "tool_name": tool_name,
                            "confidence": result.get("confidence"),
                            "reason": result.get("reason")
                        })
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JEV JSON response: {content}")
        except Exception as err:
            logger.error(f"JEV API call failed: {err}")
    else:
        logger.info("JEV_API_KEY not set. Skipping live JEV evaluation.")

    return {"status": "SUCCESS"}


import requests

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
    # CALL LLM (e.g., OpenRouter) TO SUMMARIZE SESSION
    # ---------------------------------------------------------
    api_key = os.environ.get("OPENROUTER_API_KEY")
    summary = ""
    if api_key:
        logger.info("Calling OpenRouter for session summary...")
        try:
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={
                "Authorization": f"Bearer {api_key}"
            }, json={
                "model": "google/gemini-flash-1.5-8b",
                "messages": [
                    {"role": "system", "content": "Summarize this agent session into a short dense paragraph (3-4 sentences max). Focus on what was achieved."},
                    {"role": "user", "content": f"Session Tool Calls:\n{tool_text}"}
                ]
            }, timeout=10)
            r.raise_for_status()
            summary = r.json()["choices"][0]["message"]["content"]
        except Exception as err:
            logger.error(f"OpenRouter LLM call failed: {err}")
            summary = f"Automated summary failed. Included {len(events)} events."
    else:
        logger.info("No OPENROUTER_API_KEY set, generating basic heuristic summary.")
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
