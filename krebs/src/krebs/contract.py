"""Pure lifecycle decisions; all external facts are supplied by verified adapters."""
from copy import deepcopy
import hashlib
import json
import uuid

LANES = ("Backlog", "Needs Re-evaluation", "Todo", "In Progress", "E2E Testing & QA",
         "Ready for Documentation", "Done", "Needs Attention", "Cancelled")
OPERATIONS = {"claim", "handoff", "complete", "attention", "resume", "release", "cancel",
              "takeover", "status", "heartbeat", "finish", "review", "get", "comment", "update", "create", "start"}

class Rejected(ValueError):
    pass

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def require(condition, message):
    if not condition:
        raise Rejected(message)

def validate(command):
    for key in ("command_id", "idempotency_key", "project_id", "ticket_id", "actor_id",
                "runtime_id", "run_id", "correlation_id", "causation_id"):
        require(isinstance(command.get(key), str) and command[key], f"missing {key}")
    for key in ("command_id", "correlation_id", "causation_id"):
        try: uuid.UUID(command[key])
        except (ValueError, TypeError, AttributeError): raise Rejected(f"{key} must be UUID")
    require(command.get("version") == 2, "unsupported command version")
    require(command.get("operation") in OPERATIONS, "unsupported operation")
    require(type(command.get("expected_revision")) is int, "expected_revision required")
    require(type(command.get("generation")) is int, "generation required")
    require(isinstance(command.get("payload", {}), dict), "payload must be object")
    require(command["generation"] >= 0 and command["expected_revision"] >= 0, "negative fence/revision")
    try: json.dumps(command, allow_nan=False)
    except ValueError: raise Rejected("non-finite JSON number")

def decide(board, command, now, ticket, reviews=(), children=()):
    """Return next snapshot and durable provider action; never perform I/O here."""
    state = deepcopy(board)
    op = command["operation"]
    payload = command.get("payload", {})
    active = state.get("active")
    record = state["tickets"].get(command["ticket_id"], {})
    if op in {"status", "get"}:
        return state, None
    if op not in {"claim", "resume", "takeover", "create"}:
        if not active or command["generation"] != active["generation"] or (op != "review" and command["run_id"] != active["run_id"]):
            return state, {"audit_only": True, "reason": "obsolete attempt"}
        require(active["ticket_id"] == command["ticket_id"], "ticket does not own capacity")
        if op != "review":
            require(command["actor_id"] == active["actor_id"], "attempt belongs to another actor")
        require(now < active["lease_until"], "lease expired; stop proof required")
        require(not active.get("revoked"), "attempt authority revoked")
    require(command["expected_revision"] == state["revision"], "revision conflict")
    action = None
    if op in {"claim", "resume", "takeover"}:
        require(not active or op == "takeover", "board capacity occupied; stopped proof required")
        if op == "resume":
            question = record.get("question", {})
            require(question and question.get("id") == payload.get("question_id") and not question.get("answered"), "unknown or answered question")
            require(payload.get("answer"), "answer required")
            require(not record.get("retry_exhausted"), "retry budget exhausted; operator re-evaluation required")
            question["answered"] = payload["answer"]
        else:
            require(not record.get("question") or record["question"].get("answered"), "open question requires resume with its answer")
            require(op == "takeover" or ticket["lane"] in {"Todo", "Needs Attention"}, "ticket is not ready")
        require(not record.get("retry_exhausted"), "retry budget exhausted; operator re-evaluation required")
        require(payload.get("acceptance") and payload.get("artifact"), "freeze acceptance and artifact before dispatch")
        require(payload.get("ticket_revision") == ticket["revision"], "ticket changed; revalidate readiness")
        state["generation"] += 1
        active = {"actor_id": command["actor_id"], "run_id": command["run_id"],
                  "runtime_id": command["runtime_id"], "ticket_id": command["ticket_id"],
                  "generation": state["generation"], "lease_until": now + 300,
                  "artifact": payload["artifact"], "acceptance": payload["acceptance"],
                  "ticket_revision": ticket["revision"], "correlation_id": command["correlation_id"], "revoked": False}
        state["active"] = active
        record.update({"lane": "In Progress", "attempt": active, "dispatched": False, "outcome": None, "retries": record.get("retries", 0)})
        action = {"lane": "In Progress", "working": True, "assign": True, "stop": op == "takeover" and bool(board.get("active"))}
    elif op == "start":
        require(not record.get("dispatched"), "run already dispatched")
        action = {"runtime_start": payload.get("argv")}
        record["dispatched"] = True
    elif op == "heartbeat":
        active["lease_until"] = now + 300
    elif op == "review":
        require(command["run_id"] != active["run_id"], "independent reviewer identity and run required")
        require(payload.get("artifact") == active["artifact"] and payload.get("acceptance") == active["acceptance"], "review evidence is stale")
        require(payload.get("kind") in {"spec", "quality"} and payload.get("passed") is True and payload.get("receipt"), "review failed or lacks receipt")
    elif op in {"handoff", "complete"}:
        evidence = payload.get("evidence", {})
        require(evidence.get("artifact") == active["artifact"] and evidence.get("acceptance") == active["acceptance"], "evidence is not frozen to current artifact")
        require(ticket["revision"] == record.get("provider_revision", active["ticket_revision"]), "provider content changed; readiness invalidated")
        valid = [r for r in reviews if r["evidence"].get("artifact") == active["artifact"] and r["evidence"].get("acceptance") == active["acceptance"] and r["run_id"] != active["run_id"]]
        kinds = {r["evidence"]["kind"] for r in valid}
        require({"spec", "quality"} <= kinds, "independent spec and quality reviews required")
        lane = payload.get("lane", "Done" if op == "complete" else "E2E Testing & QA")
        progression = {"In Progress": "E2E Testing & QA", "E2E Testing & QA": "Ready for Documentation", "Ready for Documentation": "Done"}
        require(progression.get(record.get("lane")) == lane, "invalid lane progression")
        gates = ["tests"] if lane == "E2E Testing & QA" else ["tests", "docs", "notebook", "skill", "main", "push", "deployment"]
        for name in gates:
            gate = evidence.get(name, {})
            require((gate.get("passed") is True and bool(gate.get("receipt"))) or (gate.get("applicable") is False and bool(gate.get("reason"))), f"missing {name} evidence")
        required_children = active["acceptance"].get("children", []) if isinstance(active["acceptance"], dict) else []
        require(set(required_children) <= set(children), "child completion receipts not verified")
        if required_children:
            require(evidence.get("integration", {}).get("passed") is True and evidence["integration"].get("receipt"), "parent integration evidence required")
        record["lane"] = lane
        action = {"lane": lane, "working": lane != "Done", "stop": lane == "Done"}
        if lane == "Done":
            state["active"] = None
    elif op in {"attention", "release", "cancel", "finish"}:
        if op == "finish" and payload.get("outcome") == "success":
            require(payload.get("artifact"), "delivered artifact required")
            if payload["artifact"] != active["artifact"]:
                active["artifact"] = payload["artifact"]
                record["lane"] = "In Progress"
                action = {"lane": "In Progress", "working": True}
            record["outcome"] = payload
        else:
            if op == "finish":
                require(payload.get("classification") in {"recoverable", "dependency", "terminal"}, "classify failure")
                if payload["classification"] == "recoverable":
                    record["retries"] = record.get("retries", 0) + 1
                    record["retry_exhausted"] = record["retries"] >= 3
            lane = "Cancelled" if op == "cancel" else "Todo" if op == "release" else "Needs Attention"
            if op == "attention":
                require(payload.get("question_id") and payload.get("question") and payload.get("context"), "question id, question and context required")
                require(not record.get("question") or record["question"].get("answered"), "question already open")
                record["question"] = {"id": payload["question_id"], "text": payload["question"], "context": payload["context"], "resume_state": record.get("lane")}
            record["lane"] = lane
            action = {"lane": lane, "working": False, "stop": True, "question": record.get("question") if op == "attention" else None}
            state["active"] = None
    elif op == "comment":
        require(payload.get("text"), "comment text required")
        action = {"comment": payload["text"]}
    elif op == "update":
        require(set(payload) <= {"name", "description_html"} and bool(payload), "managed updates cannot bypass lifecycle state")
        action = {"update": payload}
        active["acceptance"] = None  # changed scope requires release and re-claim
    elif op == "create":
        require(not active, "capacity occupied")
        require(payload.get("name"), "name required")
        action = {"create": {"name": payload["name"], "description_html": payload.get("description_html", "")}, "lane": "Backlog"}
    state["tickets"][command["ticket_id"]] = record
    state["revision"] += 1
    return state, action
