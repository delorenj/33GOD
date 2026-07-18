#!/usr/bin/env python3
"""Momo's bounded Lifecycle policy-client seam.

The client consumes Candystore's read-only Lifecycle projection, chooses only
authority-returned legal work, resolves authoritative obligation skill refs,
and builds canonical Bloodbank envelopes. It never writes Lifecycle, provider,
Candystore, or local state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry, Resource

LIFECYCLE_TYPE = "bloodbank.v1.lifecycle.intent.submit"
LIFECYCLE_SUBJECT = "bloodbank.cmd.v1.lifecycle.intent.submit"
LIFECYCLE_REPLY_SUBJECT = "bloodbank.rpy.v1.lifecycle.intent.submit"
INVOCATION_TYPE = "bloodbank.v1.agent.invocation.start"
INVOCATION_SUBJECT = "bloodbank.cmd.v1.agent.invocation.start"
EVIDENCE_TYPE = "bloodbank.v1.lifecycle.obligation_evidence.submitted"
EVIDENCE_SUBJECT = "bloodbank.evt.v1.lifecycle.obligation_evidence.submitted"
AUTHORITY_SOURCE = "urn:33god:service:lifecycle"
AUTHORITY_PRODUCER = "delorenj/lifecycle"
AUTHORITY_SERVICE = "lifecycle"
MOMO_SOURCE = "urn:33god:service:momo"
CAPABILITY_ACTION = "lifecycle.intent.submit"
SKILL_NAME = re.compile(r"^(?:[a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SCHEMA_PATH_BY_REF = {
    "bloodbank.v1.agent.invocation.start.v1": ("bloodbank/v1/agent/invocation.start.v1.json"),
    "bloodbank.v1.lifecycle.intent.submit.command.v1": (
        "bloodbank/v1/lifecycle/intent.submit.command.v1.json"
    ),
    "bloodbank.v1.lifecycle.intent.submit.reply.v1": (
        "bloodbank/v1/lifecycle/intent.submit.reply.v1.json"
    ),
    "bloodbank.v1.lifecycle.obligation_evidence.submitted.v1": (
        "bloodbank/v1/lifecycle/obligation_evidence.submitted.v1.json"
    ),
}


class LifecycleClientError(ValueError):
    """A fail-closed client contract violation."""


def fetch_projection(base_url: str, lifecycle_id: str) -> dict[str, Any]:
    """Fetch one read model. Only GET is supported by this client."""

    url = f"{base_url.rstrip('/')}/lifecycles/{lifecycle_id}"
    request = Request(url, method="GET", headers={"Accept": "application/json"})
    with urlopen(request, timeout=10) as response:  # noqa: S310 - operator-supplied URL
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise LifecycleClientError("Candystore projection must be a JSON object")
    return payload


def legal_frontier(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    state_version = _current_state_version(snapshot)
    frontier = snapshot.get("legal_frontier")
    if not isinstance(frontier, list):
        raise LifecycleClientError("authoritative legal_frontier must be an array")
    return sorted(
        [
            item
            for item in frontier
            if isinstance(item, dict)
            and item.get("allowed") is True
            and item.get("expected_state_version") == state_version
        ],
        key=_frontier_rank,
    )


def pending_obligations(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    _current_state_version(snapshot)
    obligations = snapshot.get("obligations")
    if not isinstance(obligations, list):
        raise LifecycleClientError("authoritative obligations must be an array")
    pending = [
        obligation
        for obligation in obligations
        if isinstance(obligation, dict) and obligation.get("status") == "pending"
    ]
    for obligation in pending:
        _required_text(obligation, "id")
        _required_text(obligation, "kind")
        _required_text(obligation, "owner_id")
        resolve_skill_ref(obligation)
    return sorted(pending, key=_obligation_rank)


def resolve_skill_ref(obligation: dict[str, Any]) -> dict[str, str]:
    """Validate and preserve Lifecycle's canonical Skillex identity exactly."""

    ref = obligation.get("skill_ref")
    if not isinstance(ref, dict):
        raise LifecycleClientError("pending obligation is missing skill_ref")
    name = ref.get("name")
    selector = ref.get("selector")
    if not isinstance(name, str) or not SKILL_NAME.fullmatch(name):
        raise LifecycleClientError("skill_ref.name is not a canonical skill name")
    if not isinstance(selector, str) or not selector or any(char.isspace() for char in selector):
        raise LifecycleClientError("skill_ref.selector must be non-empty and contain no whitespace")
    return {"name": name, "selector": selector}


def build_obligation_invocation(
    snapshot: dict[str, Any],
    *,
    actor: dict[str, Any],
    obligation_id: str | None = None,
    rationale: dict[str, Any] | None = None,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build actor work for one authoritative pending obligation.

    A pending obligation is its own legal actor-work contract. No unrelated
    frontier transition is treated as authorization. Invocation/request facts
    are deliberately distinct from completion evidence and cannot satisfy the
    obligation.
    """

    state_version = _current_state_version(snapshot)
    obligations = pending_obligations(snapshot)
    if obligation_id is not None:
        obligations = [item for item in obligations if item.get("id") == obligation_id]
    if not obligations:
        raise LifecycleClientError("no matching authoritative pending obligation")
    obligation = obligations[0]
    skill_ref = resolve_skill_ref(obligation)
    target_agent_id = _required_text(obligation, "owner_id")
    lifecycle_id = _required_text(snapshot, "lifecycle_id")
    repo = _required_text(snapshot, "repo")
    actor = _actor(actor)
    source_event_id, source_event_time = _projection_source(snapshot)
    parameters = _object(parameters or {}, "parameters")
    semantics = {
        "contract": "momo.lifecycle.obligation_invocation.v1",
        "lifecycle_id": lifecycle_id,
        "repo": repo,
        "state_version": state_version,
        "authority_snapshot_event_id": source_event_id,
        "actor": actor,
        "obligation": obligation,
        "target_agent_id": target_agent_id,
        "skill_ref": skill_ref,
        "parameters": parameters,
    }
    identity = _semantic_digest(semantics)
    event_id = _semantic_uuid("invocation-event", identity)
    command_id = _semantic_uuid("invocation-command", identity)
    correlation_id = _semantic_uuid("invocation-correlation", identity)
    causation_id = _semantic_uuid("invocation-causation", identity)
    idempotency_key = f"agent.invocation.start:semantic:{identity}"
    command = {
        "specversion": "1.0",
        "id": event_id,
        "source": f"urn:33god:agent:{actor['agent_id']}",
        "type": INVOCATION_TYPE,
        "subject": INVOCATION_SUBJECT,
        "time": source_event_time,
        "datacontenttype": "application/json",
        "dataschema": "apicurio://holyfields/bloodbank.v1.agent.invocation.start/versions/1",
        "correlationid": correlation_id,
        "causationid": causation_id,
        "producer": "momo",
        "service": "momo",
        "domain": "agent",
        "schemaref": "bloodbank.v1.agent.invocation.start.v1",
        "kind": "command",
        "actor": actor,
        "command_id": command_id,
        "idempotency_key": idempotency_key,
        "delivery": "single_consumer",
        "data": {
            "target_agent_id": target_agent_id,
            "thread_id": None,
            "turn_id": None,
            "prompt": (
                f"Complete Lifecycle obligation {obligation['id']}: "
                f"{obligation.get('description', '')}. Invoke canonical skill "
                f"{skill_ref['name']} at selector {skill_ref['selector']}. "
                "Return concrete completion artifact evidence; this invocation "
                "does not itself satisfy the obligation."
            ),
            "context": {
                "contract_version": 1,
                "lifecycle_id": lifecycle_id,
                "repo": repo,
                "expected_state_version": state_version,
                "authority_snapshot_event_id": source_event_id,
                "obligation": obligation,
                "skill_ref": skill_ref,
                "parameters": parameters,
                "completion_evidence_contract": {
                    "type": EVIDENCE_TYPE,
                    "subject": EVIDENCE_SUBJECT,
                    "obligation_id": obligation["id"],
                    "obligation_kind": obligation["kind"],
                    "target_actor_id": target_agent_id,
                    "invocation_id": event_id,
                },
            },
        },
    }
    return {
        "selection": {
            "kind": "obligation",
            "lifecycle_id": lifecycle_id,
            "state_version": state_version,
            "obligation_id": obligation["id"],
            "target_actor_id": target_agent_id,
            "skill_ref": skill_ref,
            "authority_snapshot_event_id": source_event_id,
        },
        "decision_rationale": rationale or {},
        "invocation_command": command,
    }


def build_obligation_completion_evidence(
    invocation_plan: dict[str, Any],
    *,
    completed_at: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Build canonical completed-skill evidence for Lifecycle to evaluate."""

    selection = _object(invocation_plan.get("selection"), "selection")
    if selection.get("kind") != "obligation":
        raise LifecycleClientError("completion requires an obligation invocation plan")
    command = _object(invocation_plan.get("invocation_command"), "invocation_command")
    if command.get("type") != INVOCATION_TYPE or command.get("subject") != INVOCATION_SUBJECT:
        raise LifecycleClientError("completion invocation command identity is not canonical")
    context = _object(_object(command.get("data"), "invocation data").get("context"), "context")
    contract = _object(context.get("completion_evidence_contract"), "completion contract")
    checks = {
        "obligation_id": selection.get("obligation_id"),
        "target_actor_id": selection.get("target_actor_id"),
        "invocation_id": command.get("id"),
    }
    for key, expected in checks.items():
        if contract.get(key) != expected:
            raise LifecycleClientError(f"completion contract {key} does not match invocation")
    completed_at = _timestamp(completed_at, "completed_at")
    evidence = _completion_evidence(evidence)
    # The invocation actor identifies who requested the work. Completion evidence
    # is a distinct Momo-produced authority observation and therefore carries the
    # canonical service identity required by the Lifecycle consumer contract.
    actor = {"type": "service", "agent_id": "momo"}
    data = {
        "contract_version": 1,
        "lifecycle_id": _required_text(selection, "lifecycle_id"),
        "repo": _required_text(context, "repo"),
        "obligation_id": _required_text(contract, "obligation_id"),
        "obligation_kind": _required_text(contract, "obligation_kind"),
        "target_actor_id": _required_text(contract, "target_actor_id"),
        "invocation_id": _uuid(_required_text(contract, "invocation_id"), "invocation_id"),
        "skill_ref": _skill_ref_value(context.get("skill_ref")),
        "completed_at": completed_at,
        "evidence": evidence,
    }
    identity = _semantic_digest(
        {
            "contract": "momo.lifecycle.obligation_completion.v1",
            "invocation_event_id": command["id"],
            "completed_at": completed_at,
            "data": data,
            "actor": actor,
        }
    )
    envelope = {
        "specversion": "1.0",
        "id": _semantic_uuid("completion-event", identity),
        "source": MOMO_SOURCE,
        "type": EVIDENCE_TYPE,
        "subject": EVIDENCE_SUBJECT,
        "time": completed_at,
        "datacontenttype": "application/json",
        "dataschema": (
            "apicurio://holyfields/bloodbank.v1.lifecycle.obligation_evidence.submitted/versions/1"
        ),
        "correlationid": _uuid(command.get("correlationid"), "invocation correlationid"),
        "causationid": _uuid(command.get("id"), "invocation event id"),
        "producer": "momo",
        "service": "momo",
        "domain": "lifecycle",
        "schemaref": "bloodbank.v1.lifecycle.obligation_evidence.submitted.v1",
        "kind": "event",
        "actor": actor,
        "ordering_key": f"lifecycle:{data['lifecycle_id']}",
        "data": data,
    }
    return {
        "selection": selection,
        "decision_rationale": invocation_plan.get("decision_rationale") or {},
        "completion_evidence": envelope,
    }


def build_lifecycle_intent(
    snapshot: dict[str, Any],
    *,
    actor: dict[str, Any],
    evidence: dict[str, Any],
    frontier_id: str | None = None,
    rationale: dict[str, Any] | None = None,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a deterministic, versioned intent for a legal frontier item only."""

    state_version = _current_state_version(snapshot)
    candidates = legal_frontier(snapshot)
    if frontier_id is not None:
        candidates = [item for item in candidates if item.get("id") == frontier_id]
    if not candidates:
        raise LifecycleClientError("no matching allowed frontier item at the current state version")
    frontier = candidates[0]
    lifecycle_id = _required_text(snapshot, "lifecycle_id")
    repo = _required_text(snapshot, "repo")
    actor = _actor(actor)
    capability = _capability_context(snapshot, actor_id=actor["agent_id"], frontier=frontier)
    evidence = _object(evidence, "evidence")
    if not evidence:
        raise LifecycleClientError("Lifecycle intent requires non-empty evidence metadata")
    intent_name, intent_target = _frontier_intent(frontier)
    intent_parameters = _object(parameters or {}, "parameters")
    intent_parameters.update({"selected_frontier_id": frontier["id"], "evidence": evidence})
    source_event_id, source_event_time = _projection_source(snapshot)
    semantics = {
        "contract": "momo.lifecycle.intent.v1",
        "lifecycle_id": lifecycle_id,
        "repo": repo,
        "expected_state_version": state_version,
        "authority_snapshot_event_id": source_event_id,
        "selected_frontier": frontier,
        "actor": actor,
        "capability": capability,
        "intent": {
            "name": intent_name,
            "target": intent_target,
            "parameters": intent_parameters,
        },
    }
    identity = _semantic_digest(semantics)
    event_id = _semantic_uuid("intent-event", identity)
    command_id = _semantic_uuid("intent-command", identity)
    correlation_id = _semantic_uuid("intent-correlation", identity)
    causation_id = _semantic_uuid("intent-causation", identity)
    idempotency_key = f"lifecycle.intent.submit:semantic:{identity}"
    command = {
        "specversion": "1.0",
        "id": event_id,
        "source": f"urn:33god:agent:{actor['agent_id']}",
        "type": LIFECYCLE_TYPE,
        "subject": LIFECYCLE_SUBJECT,
        "time": source_event_time,
        "datacontenttype": "application/json",
        "dataschema": "apicurio://holyfields/bloodbank.v1.lifecycle.intent.submit.command/versions/1",
        "correlationid": correlation_id,
        "causationid": causation_id,
        "producer": "momo",
        "service": "momo",
        "domain": "lifecycle",
        "schemaref": "bloodbank.v1.lifecycle.intent.submit.command.v1",
        "kind": "command",
        "actor": actor,
        "command_id": command_id,
        "idempotency_key": idempotency_key,
        "delivery": "single_consumer",
        "data": {
            "contract_version": 1,
            "lifecycle_id": lifecycle_id,
            "repo": repo,
            "expected_state_version": state_version,
            "intent": {
                "name": intent_name,
                "target": intent_target,
                "parameters": intent_parameters,
            },
            "capability": capability,
            "requested_at": source_event_time,
        },
    }
    return {
        "selection": {
            "kind": "frontier",
            "lifecycle_id": lifecycle_id,
            "state_version": state_version,
            "frontier": frontier,
            "authority_snapshot_event_id": source_event_id,
        },
        "decision_rationale": rationale or {},
        "lifecycle_command": command,
    }


def verify_command_verdict(command: dict[str, Any], reply: dict[str, Any]) -> dict[str, Any]:
    """Accept only a schema-shaped, identity-matched Lifecycle authority verdict."""

    validate_bloodbank_envelope(command)
    validate_bloodbank_envelope(reply)
    command_data = _object(command.get("data"), "Lifecycle command data")
    capability = _object(command_data.get("capability"), "Lifecycle command capability")
    envelope_checks = {
        "specversion": "1.0",
        "source": AUTHORITY_SOURCE,
        "type": LIFECYCLE_TYPE,
        "subject": LIFECYCLE_REPLY_SUBJECT,
        "datacontenttype": "application/json",
        "dataschema": "apicurio://holyfields/bloodbank.v1.lifecycle.intent.submit.reply/versions/1",
        "correlationid": command.get("correlationid"),
        "causationid": command.get("id"),
        "producer": AUTHORITY_PRODUCER,
        "service": AUTHORITY_SERVICE,
        "domain": "lifecycle",
        "schemaref": "bloodbank.v1.lifecycle.intent.submit.reply.v1",
        "kind": "reply",
    }
    for key, expected in envelope_checks.items():
        if reply.get(key) != expected:
            raise LifecycleClientError(f"Lifecycle reply {key} is not authoritative or matching")
    _uuid(reply.get("id"), "Lifecycle reply id")
    replied_at = _timestamp(reply.get("time"), "Lifecycle reply time")
    authority_actor = _object(reply.get("actor"), "Lifecycle reply actor")
    if (
        authority_actor.get("type") != "service"
        or authority_actor.get("agent_id") != "delorenj.lifecycle"
    ):
        raise LifecycleClientError("Lifecycle reply actor is not the authority")
    _required_text(authority_actor, "instance")
    data = _object(reply.get("data"), "Lifecycle reply data")
    checks = {
        "contract_version": 1,
        "lifecycle_id": command_data.get("lifecycle_id"),
        "repo": command_data.get("repo"),
        "reply_to_command_event_id": command.get("id"),
        "command_id": command.get("command_id"),
        "idempotency_key": command.get("idempotency_key"),
        "expected_state_version": command_data.get("expected_state_version"),
        "capability_id": capability.get("capability_id"),
        "responded_at": replied_at,
    }
    for key, expected in checks.items():
        if data.get(key) != expected:
            raise LifecycleClientError(f"Lifecycle reply {key} does not match the command")
    observed = data.get("observed_state_version")
    if isinstance(observed, bool) or not isinstance(observed, int) or observed < 1:
        raise LifecycleClientError("Lifecycle reply observed_state_version is invalid")
    verdict = data.get("verdict")
    mutated = data.get("mutated")
    resulting = data.get("resulting_state_version")
    applied_event_id = data.get("applied_event_id")
    _required_text(data, "reason_code")
    if verdict == "applied":
        if mutated is not True or not isinstance(resulting, int) or resulting <= observed:
            raise LifecycleClientError("Lifecycle applied verdict has inconsistent mutation fields")
        _uuid(applied_event_id, "applied_event_id")
    elif verdict == "idempotent":
        if mutated is not False or not isinstance(resulting, int) or resulting < observed:
            raise LifecycleClientError(
                "Lifecycle idempotent verdict has inconsistent mutation fields"
            )
        _uuid(applied_event_id, "applied_event_id")
    else:
        raise LifecycleClientError(f"Lifecycle command was not applied: {verdict}")
    return data


def publish_envelope(
    envelope: dict[str, Any],
    *,
    publish: Callable[..., Any] | None = None,
) -> str:
    """Publish one canonical Momo envelope through Bloodbank's NATS helper."""

    identity = (envelope.get("type"), envelope.get("subject"), envelope.get("kind"))
    valid = {
        (LIFECYCLE_TYPE, LIFECYCLE_SUBJECT, "command"),
        (INVOCATION_TYPE, INVOCATION_SUBJECT, "command"),
        (EVIDENCE_TYPE, EVIDENCE_SUBJECT, "event"),
    }
    if identity not in valid:
        raise LifecycleClientError("refusing to publish a non-canonical Momo envelope")
    if envelope.get("kind") == "command" and envelope.get("delivery") != "single_consumer":
        raise LifecycleClientError("refusing to publish an invalid command envelope")
    validate_bloodbank_envelope(envelope)
    if publish is None:
        publish = _bloodbank_publisher()
    subject = str(envelope["subject"])
    payload = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    publish(subject, payload, client_name="momo-lifecycle-client")
    return subject


def validate_bloodbank_envelope(envelope: dict[str, Any]) -> None:
    """Validate an emitted or consumed envelope against the checked-out Bloodbank schema."""

    schemaref = envelope.get("schemaref")
    if schemaref not in SCHEMA_PATH_BY_REF:
        raise LifecycleClientError(f"unsupported canonical Bloodbank schemaref: {schemaref}")
    schemas_root, registry = _bloodbank_schema_registry()
    schema = json.loads((schemas_root / SCHEMA_PATH_BY_REF[schemaref]).read_text(encoding="utf-8"))
    try:
        Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        ).validate(envelope)
    except ValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path) or "<root>"
        raise LifecycleClientError(
            f"Bloodbank schema validation failed at {location}: {exc.message}"
        ) from exc


@lru_cache(maxsize=1)
def _bloodbank_schema_registry() -> tuple[Path, Registry]:
    default = Path(__file__).resolve().parents[3] / "bloodbank"
    bloodbank_home = Path(os.environ.get("BLOODBANK_HOME", str(default))).resolve()
    schemas_root = bloodbank_home / "schemas"
    if not schemas_root.is_dir():
        raise LifecycleClientError(
            f"Bloodbank schemas unavailable at {schemas_root}; set BLOODBANK_HOME"
        )
    registry = Registry()
    for path in schemas_root.rglob("*.json"):
        document = json.loads(path.read_text(encoding="utf-8"))
        if "$id" in document:
            registry = registry.with_resource(document["$id"], Resource.from_contents(document))
    return schemas_root, registry


def _bloodbank_publisher() -> Callable[..., Any]:
    bloodbank_home = Path(
        os.environ.get("BLOODBANK_HOME", str(Path.home() / "code" / "33GOD" / "bloodbank"))
    )
    core = bloodbank_home / "services" / "agent-hooks" / "core"
    if not core.is_dir():
        raise LifecycleClientError(f"Bloodbank publisher unavailable at {core}; set BLOODBANK_HOME")
    sys.path.insert(0, str(core))
    try:
        from nats_publish import publish
    except Exception as exc:  # pragma: no cover - environment-specific import
        raise LifecycleClientError(f"cannot import Bloodbank NATS publisher: {exc}") from exc
    return publish


def _current_state_version(snapshot: dict[str, Any]) -> int:
    status = snapshot.get("projection_status")
    if status != "current":
        raise LifecycleClientError(f"Lifecycle projection is not current: {status or 'unknown'}")
    version = snapshot.get("state_version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise LifecycleClientError("authoritative state_version must be an integer >= 1")
    return version


def _projection_source(snapshot: dict[str, Any]) -> tuple[str, str]:
    source = _object(snapshot.get("source"), "authoritative projection source")
    event_id = _uuid(source.get("event_id"), "authority snapshot event_id")
    event_time = _timestamp(source.get("event_time"), "authority snapshot event_time")
    return event_id, event_time


def _capability_context(
    snapshot: dict[str, Any],
    *,
    actor_id: str,
    frontier: dict[str, Any],
) -> dict[str, Any]:
    state_version = _current_state_version(snapshot)
    lifecycle_id = _required_text(snapshot, "lifecycle_id")
    expected_scope = f"lifecycle:{lifecycle_id}"
    grants = snapshot.get("capabilities")
    if not isinstance(grants, list):
        raise LifecycleClientError("authoritative capabilities must be an array")
    grant = next(
        (
            item
            for item in grants
            if isinstance(item, dict)
            and item.get("actor_id") == actor_id
            and item.get("scope") == expected_scope
            and item.get("state_version") == state_version
            and isinstance(item.get("actions"), list)
            and (CAPABILITY_ACTION in item["actions"] or frontier.get("action") in item["actions"])
        ),
        None,
    )
    if grant is None:
        raise LifecycleClientError(
            "no current authoritative capability grant for this actor/action"
        )
    capability_version = grant.get("capability_version")
    if (
        isinstance(capability_version, bool)
        or not isinstance(capability_version, int)
        or capability_version < 1
    ):
        raise LifecycleClientError("authoritative capability_version must be an integer >= 1")
    return {
        "capability_id": _required_text(grant, "capability_id"),
        "capability_version": capability_version,
        "action": CAPABILITY_ACTION,
        "scope": expected_scope,
        "issued_to": actor_id,
    }


def _frontier_intent(frontier: dict[str, Any]) -> tuple[str, str]:
    action = _required_text(frontier, "action")
    identifier = _required_text(frontier, "id")
    if action == "transition" and identifier.startswith("transition:"):
        target = identifier.rsplit(":", 1)[-1]
    elif (
        action == "resolve_gate"
        and identifier.startswith("gate:")
        and identifier.endswith(":resolve")
    ):
        target = identifier[len("gate:") : -len(":resolve")]
    elif action == "set_mode" and identifier.startswith("mode:"):
        target = identifier[len("mode:") :]
    else:
        raise LifecycleClientError("frontier item cannot be mapped to a canonical Lifecycle intent")
    return action, _nonempty(target, "frontier intent target")


def _frontier_rank(item: dict[str, Any]) -> tuple[int, str]:
    priorities = {"work_item": 0, "gate_resolution": 1, "state_transition": 2, "command": 3}
    return priorities.get(str(item.get("kind")), 9), str(item.get("id", ""))


def _obligation_rank(item: dict[str, Any]) -> tuple[int, str, str]:
    due = item.get("due_at")
    return (0 if due else 1, str(due or ""), str(item.get("id", "")))


def _completion_evidence(value: dict[str, Any]) -> dict[str, str]:
    value = _object(value, "completion evidence")
    expected = {"kind", "outcome", "artifact_id", "artifact_sha256", "summary"}
    if set(value) != expected:
        raise LifecycleClientError("completion evidence must contain only the canonical fields")
    if value.get("kind") != "skill_completion" or value.get("outcome") != "completed":
        raise LifecycleClientError("completion evidence must report completed skill work")
    artifact_sha = _required_text(value, "artifact_sha256")
    if not SHA256.fullmatch(artifact_sha):
        raise LifecycleClientError("artifact_sha256 must be 64 lowercase hex characters")
    summary = _required_text(value, "summary")
    if len(summary) > 500:
        raise LifecycleClientError("completion evidence summary exceeds 500 characters")
    return {
        "kind": "skill_completion",
        "outcome": "completed",
        "artifact_id": _required_text(value, "artifact_id"),
        "artifact_sha256": artifact_sha,
        "summary": summary,
    }


def _skill_ref_value(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise LifecycleClientError("completion skill_ref must be an object")
    return resolve_skill_ref({"skill_ref": value})


def _actor(value: Any) -> dict[str, Any]:
    value = _object(value, "actor")
    actor_type = _required_text(value, "type")
    agent_id = _required_text(value, "agent_id")
    return {
        "type": actor_type,
        "agent_id": agent_id,
        **{key: value[key] for key in ("cli", "provider", "model") if key in value},
    }


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LifecycleClientError(f"{name} must be an object")
    return dict(value)


def _required_text(value: dict[str, Any], key: str) -> str:
    return _nonempty(value.get(key), key)


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LifecycleClientError(f"{name} must be non-empty text")
    return value.strip()


def _timestamp(value: Any, name: str) -> str:
    value = _nonempty(value, name)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LifecycleClientError(f"{name} must be RFC 3339") from exc
    if parsed.tzinfo is None:
        raise LifecycleClientError(f"{name} must include an offset")
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _uuid(value: Any, name: str) -> str:
    try:
        return str(uuid.UUID(_nonempty(value, name)))
    except ValueError as exc:
        raise LifecycleClientError(f"{name} must be a UUID") from exc


def _semantic_digest(value: dict[str, Any]) -> str:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    except (TypeError, ValueError) as exc:
        raise LifecycleClientError(f"semantic request must be canonical JSON: {exc}") from exc
    return hashlib.sha256(encoded).hexdigest()


def _semantic_uuid(kind: str, digest: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"momo-lifecycle-client:{kind}:{digest}"))


def _load_json(path: str) -> dict[str, Any]:
    if path == "-":
        value = json.load(sys.stdin)
    else:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise LifecycleClientError(f"{path} must contain a JSON object")
    return value


def _print(value: dict[str, Any]) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch")
    fetch_parser.add_argument("--candystore-url", required=True)
    fetch_parser.add_argument("--lifecycle-id", required=True)

    obligation = subparsers.add_parser("plan-obligation")
    obligation.add_argument("--snapshot", required=True)
    obligation.add_argument("--obligation-id")
    obligation.add_argument("--parameters")
    _actor_args(obligation)

    completion = subparsers.add_parser("complete-obligation")
    completion.add_argument("--invocation-plan", required=True)
    completion.add_argument("--completed-at", required=True)
    completion.add_argument("--evidence", required=True)

    intent = subparsers.add_parser("plan-intent")
    intent.add_argument("--snapshot", required=True)
    intent.add_argument("--frontier-id")
    intent.add_argument("--evidence", required=True)
    intent.add_argument("--parameters")
    _actor_args(intent)

    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument("--envelope", required=True)

    args = parser.parse_args()
    try:
        if args.command == "fetch":
            _print(fetch_projection(args.candystore_url, args.lifecycle_id))
        elif args.command == "plan-obligation":
            _print(
                build_obligation_invocation(
                    _load_json(args.snapshot),
                    actor=_cli_actor(args),
                    obligation_id=args.obligation_id,
                    parameters=_load_json(args.parameters) if args.parameters else None,
                )
            )
        elif args.command == "complete-obligation":
            _print(
                build_obligation_completion_evidence(
                    _load_json(args.invocation_plan),
                    completed_at=args.completed_at,
                    evidence=_load_json(args.evidence),
                )
            )
        elif args.command == "plan-intent":
            _print(
                build_lifecycle_intent(
                    _load_json(args.snapshot),
                    actor=_cli_actor(args),
                    evidence=_load_json(args.evidence),
                    frontier_id=args.frontier_id,
                    parameters=_load_json(args.parameters) if args.parameters else None,
                )
            )
        else:
            envelope = _load_json(args.envelope)
            print(f"published {publish_envelope(envelope)}")
    except (LifecycleClientError, OSError, json.JSONDecodeError) as exc:
        print(f"momo lifecycle client: {exc}", file=sys.stderr)
        return 2
    return 0


def _actor_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--actor-id", default="momo")
    parser.add_argument("--actor-type", default="agent_cli")
    parser.add_argument("--cli", default=os.environ.get("MOMO_CLI", "codex"))
    parser.add_argument("--provider", default=os.environ.get("MOMO_PROVIDER", "openai"))


def _cli_actor(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "type": args.actor_type,
        "agent_id": args.actor_id,
        "cli": args.cli,
        "provider": args.provider,
    }


if __name__ == "__main__":
    raise SystemExit(main())
