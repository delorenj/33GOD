"""Minimal stdlib Bloodbank v1 envelope builder for the enricher.

The enricher image is built from this directory only, so it cannot import
bloodbank/services/agent-hooks/core/envelope.py at runtime. This module is the
vendored subset the enricher needs: one event type, one builder.

It is NOT a second source of truth. The contract lives in bloodbank/ (naming
allowlists in services/agent-hooks/core/validate.py, the envelope in
schemas/_common/cloudevent_base.v1.json, the payload in
schemas/bloodbank/agent/session.annotated.json). The drift guard is
33god-platform/tests/test_enricher_envelope_contract.py, which imports those
files from the bloodbank checkout and proves what this builder emits passes
assert_contract and validates against the schema. Change the contract and that
test goes red here.

Why this exists (33GOD-95): the enricher used to POST a bare dict to Dapr, which
wrapped it as com.dapr.event.sent with no Bloodbank fields, and Candystore
dead-lettered every report (reason=malformed).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

# Canonical identity of the enricher's session roll-up (mirrors
# bloodbank.conversation.turn.annotated from the turn-enricher).
SESSION_ANNOTATED_TYPE = "bloodbank.agent.session.annotated"
SESSION_ANNOTATED_SUBJECT = "bloodbank.evt.agent.session.annotated"
SESSION_ANNOTATED_SCHEMAREF = f"{SESSION_ANNOTATED_TYPE}.v1"
SESSION_ANNOTATED_DATASCHEMA = f"apicurio://holyfields/{SESSION_ANNOTATED_TYPE}/versions/1"

SERVICE_NAME = "enricher"
SOURCE = "urn:33god:service:enricher"

# Dapr passes a body with this Content-Type through untouched; any other
# Content-Type gets wrapped in a com.dapr.event.sent envelope.
CLOUDEVENTS_CONTENT_TYPE = "application/cloudevents+json"

ZERO_TRACEPARENT = "00-00000000000000000000000000000000-0000000000000000-00"

# Fixed namespace so annotation_event_id() is stable across processes and
# restarts. Never change it: redelivery idempotency depends on it.
_ID_NAMESPACE = uuid.UUID("6f1c2a3e-5b7d-5e0a-9c41-33a0e0c1e001")

SUMMARY_SOURCES = ("gateway", "heuristic", "gateway_failed")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _is_uuid(value: object) -> bool:
    try:
        uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return False
    return isinstance(value, str)


def annotation_event_id(source_event_id: str) -> str:
    """Deterministic id of the annotation for one session.ended event.

    Redelivery of the same session.ended produces the same id, so Candystore
    (which dedups on id) stores one summary however many times the handler
    runs or the publish is retried.
    """
    return str(uuid.uuid5(_ID_NAMESPACE, f"session.annotated:{source_event_id}"))


def build_session_annotated(
    *,
    source_event: dict,
    session_id: str,
    cwd: str | None,
    summary: str,
    summary_source: str,
    event_count: int,
    tool_call_count: int,
    now: str | None = None,
) -> dict:
    """Build the bloodbank.agent.session.annotated envelope for one session.ended.

    source_event is the delivered agent.session.ended envelope: its id becomes
    causationid and data.target_event_id; its actor and traceparent are copied.
    """
    if summary_source not in SUMMARY_SOURCES:
        raise ValueError(f"summary_source {summary_source!r} not in {SUMMARY_SOURCES}")
    source_id = source_event.get("id")
    if not _is_uuid(source_id):
        raise ValueError(f"source event id {source_id!r} is not a uuid; cannot set causationid/target_event_id")
    # The base schema types correlationid as a uuid. Candystore's session key is
    # one already; hash anything else so the envelope still validates while
    # data.session_id keeps the raw value.
    correlation_id = session_id if _is_uuid(session_id) else str(uuid.uuid5(_ID_NAMESPACE, f"session:{session_id}"))
    actor = source_event.get("actor")
    if not isinstance(actor, dict) or not actor.get("type") or not actor.get("agent_id"):
        actor = {"type": "service", "agent_id": f"service:{SERVICE_NAME}", "cli": None, "provider": None, "model": None}
    traceparent = source_event.get("traceparent")
    if not isinstance(traceparent, str) or len(traceparent) != 55:
        traceparent = ZERO_TRACEPARENT
    return {
        "specversion": "1.0",
        "id": annotation_event_id(source_id),
        "source": SOURCE,
        "type": SESSION_ANNOTATED_TYPE,
        "subject": SESSION_ANNOTATED_SUBJECT,
        "time": now or _now_iso(),
        "datacontenttype": "application/json",
        "dataschema": SESSION_ANNOTATED_DATASCHEMA,
        "correlationid": correlation_id,
        "causationid": source_id,
        "producer": SERVICE_NAME,
        "service": SERVICE_NAME,
        "domain": "agent",
        "schemaref": SESSION_ANNOTATED_SCHEMAREF,
        "traceparent": traceparent,
        "kind": "event",
        "actor": actor,
        "ordering_key": f"session:{correlation_id}",
        "data": {
            "schema_version": 1,
            "session_id": session_id,
            "cwd": cwd,
            "summary": summary,
            "event_count": event_count,
            "tool_call_count": tool_call_count,
            "summary_source": summary_source,
            "target_event_id": source_id,
        },
    }
