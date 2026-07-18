#!/usr/bin/env python3
"""Momo's bounded Lifecycle policy-client seam.

The client consumes Candystore's read-only Lifecycle projection, ranks only
authority-returned legal work, resolves authoritative obligation skill refs,
and builds canonical Bloodbank commands. It never writes Lifecycle, provider,
Candystore, or local state.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

LIFECYCLE_TYPE = "bloodbank.v1.lifecycle.intent.submit"
LIFECYCLE_SUBJECT = "bloodbank.cmd.v1.lifecycle.intent.submit"
INVOCATION_TYPE = "bloodbank.v1.agent.invocation.start"
INVOCATION_SUBJECT = "bloodbank.cmd.v1.agent.invocation.start"
CAPABILITY_ACTION = "lifecycle.intent.submit"
SKILL_NAME = re.compile(r"^(?:[a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])$")


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
    target_agent_id: str,
    requested_at: str,
    correlation_id: str,
    causation_id: str,
    obligation_id: str | None = None,
    rationale: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an agent invocation for an authoritative pending obligation.

    The rationale is returned beside the command, never inserted into a
    Lifecycle state-changing intent. The invocation carries the exact skill ref
    and the evidence shape expected from the worker's completion event.
    """

    state_version = _current_state_version(snapshot)
    frontier = legal_frontier(snapshot)
    if not frontier:
        raise LifecycleClientError("authoritative frontier contains no legal current work")
    obligations = pending_obligations(snapshot)
    if obligation_id is not None:
        obligations = [item for item in obligations if item.get("id") == obligation_id]
    if not obligations:
        raise LifecycleClientError("no matching authoritative pending obligation")
    obligation = obligations[0]
    skill_ref = resolve_skill_ref(obligation)
    lifecycle_id = _required_text(snapshot, "lifecycle_id")
    repo = _required_text(snapshot, "repo")
    actor = _actor(actor)
    target_agent_id = _nonempty(target_agent_id, "target_agent_id")
    requested_at = _timestamp(requested_at, "requested_at")
    correlation_id = _uuid(correlation_id, "correlation_id")
    causation_id = _uuid(causation_id, "causation_id")
    idempotency_key = (
        f"agent.invocation.start:lifecycle:{lifecycle_id}:"
        f"obligation:{obligation['id']}:state:{state_version}"
    )
    event_id = _stable_uuid(f"event:{idempotency_key}")
    command_id = _stable_uuid(f"command:{idempotency_key}")
    command = {
        "specversion": "1.0",
        "id": event_id,
        "source": f"urn:33god:agent:{actor['agent_id']}",
        "type": INVOCATION_TYPE,
        "subject": INVOCATION_SUBJECT,
        "time": requested_at,
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
                f"Resolve Lifecycle obligation {obligation['id']}: "
                f"{obligation.get('description', '')}. Invoke the canonical "
                f"{skill_ref['name']} skill at selector {skill_ref['selector']}."
            ),
            "context": {
                "contract_version": 1,
                "lifecycle_id": lifecycle_id,
                "repo": repo,
                "expected_state_version": state_version,
                "authority_frontier_basis": frontier[0],
                "obligation": obligation,
                "skill_ref": skill_ref,
                "evidence_completion": {
                    "lifecycle_id": lifecycle_id,
                    "obligation_id": obligation["id"],
                    "obligation_satisfied": True,
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
            "skill_ref": skill_ref,
            "authority_frontier_id": frontier[0]["id"],
        },
        "decision_rationale": rationale or {},
        "invocation_command": command,
    }


def build_lifecycle_intent(
    snapshot: dict[str, Any],
    *,
    actor: dict[str, Any],
    capability_version: int,
    requested_at: str,
    correlation_id: str,
    causation_id: str,
    evidence: dict[str, Any],
    frontier_id: str | None = None,
    rationale: dict[str, Any] | None = None,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a versioned canonical intent for a legal frontier item only."""

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
    capability = _capability_context(
        snapshot,
        actor_id=actor["agent_id"],
        capability_version=capability_version,
        frontier=frontier,
    )
    if not isinstance(evidence, dict) or not evidence:
        raise LifecycleClientError("Lifecycle intent requires non-empty evidence metadata")
    requested_at = _timestamp(requested_at, "requested_at")
    correlation_id = _uuid(correlation_id, "correlation_id")
    causation_id = _uuid(causation_id, "causation_id")
    intent_name, intent_target = _frontier_intent(frontier)
    intent_parameters = dict(parameters or {})
    intent_parameters.update(
        {
            "selected_frontier_id": frontier["id"],
            "evidence": evidence,
        }
    )
    idempotency_key = (
        f"lifecycle.intent.submit:{lifecycle_id}:frontier:{frontier['id']}:state:{state_version}"
    )
    event_id = _stable_uuid(f"event:{idempotency_key}")
    command_id = _stable_uuid(f"command:{idempotency_key}")
    command = {
        "specversion": "1.0",
        "id": event_id,
        "source": f"urn:33god:agent:{actor['agent_id']}",
        "type": LIFECYCLE_TYPE,
        "subject": LIFECYCLE_SUBJECT,
        "time": requested_at,
        "datacontenttype": "application/json",
        "dataschema": (
            "apicurio://holyfields/bloodbank.v1.lifecycle.intent.submit.command/versions/1"
        ),
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
            "requested_at": requested_at,
        },
    }
    return {
        "selection": {
            "kind": "frontier",
            "lifecycle_id": lifecycle_id,
            "state_version": state_version,
            "frontier": frontier,
        },
        "decision_rationale": rationale or {},
        "lifecycle_command": command,
    }


def verify_command_verdict(command: dict[str, Any], reply: dict[str, Any]) -> dict[str, Any]:
    """Accept only a matching authoritative applied/idempotent command result."""

    if reply.get("subject") != "bloodbank.rpy.v1.lifecycle.intent.submit":
        raise LifecycleClientError("reply is not a Lifecycle intent verdict")
    data = reply.get("data")
    if not isinstance(data, dict):
        raise LifecycleClientError("Lifecycle reply data must be an object")
    command_data = command.get("data")
    if not isinstance(command_data, dict):
        raise LifecycleClientError("Lifecycle command data must be an object")
    checks = {
        "reply_to_command_event_id": command.get("id"),
        "command_id": command.get("command_id"),
        "idempotency_key": command.get("idempotency_key"),
        "lifecycle_id": command_data.get("lifecycle_id"),
        "expected_state_version": command_data.get("expected_state_version"),
    }
    for key, expected in checks.items():
        if data.get(key) != expected:
            raise LifecycleClientError(f"Lifecycle reply {key} does not match the command")
    if data.get("verdict") not in {"applied", "idempotent"}:
        raise LifecycleClientError(f"Lifecycle command was not applied: {data.get('verdict')}")
    return data


def publish_envelope(
    envelope: dict[str, Any],
    *,
    publish: Callable[..., Any] | None = None,
) -> str:
    """Publish a canonical command through Bloodbank's NATS transport helper."""

    subject = envelope.get("subject")
    if subject not in {LIFECYCLE_SUBJECT, INVOCATION_SUBJECT}:
        raise LifecycleClientError("refusing to publish a non-canonical Momo command subject")
    if envelope.get("kind") != "command" or envelope.get("delivery") != "single_consumer":
        raise LifecycleClientError("refusing to publish an invalid command envelope")
    if publish is None:
        publish = _bloodbank_publisher()
    payload = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    publish(subject, payload, client_name="momo-lifecycle-client")
    return str(subject)


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


def _capability_context(
    snapshot: dict[str, Any],
    *,
    actor_id: str,
    capability_version: int,
    frontier: dict[str, Any],
) -> dict[str, Any]:
    if isinstance(capability_version, bool) or capability_version < 1:
        raise LifecycleClientError("capability_version must be an integer >= 1")
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
    published_version = grant.get("capability_version")
    if published_version is not None and published_version != capability_version:
        raise LifecycleClientError("capability_version does not match the authoritative grant")
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


def _actor(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LifecycleClientError("actor must be an object")
    actor_type = _required_text(value, "type")
    agent_id = _required_text(value, "agent_id")
    return {
        "type": actor_type,
        "agent_id": agent_id,
        **{key: value[key] for key in ("cli", "provider", "model") if key in value},
    }


def _required_text(value: dict[str, Any], key: str) -> str:
    return _nonempty(value.get(key), key)


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LifecycleClientError(f"{name} must be non-empty text")
    return value.strip()


def _timestamp(value: str, name: str) -> str:
    value = _nonempty(value, name)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LifecycleClientError(f"{name} must be RFC 3339") from exc
    if parsed.tzinfo is None:
        raise LifecycleClientError(f"{name} must include an offset")
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _uuid(value: str, name: str) -> str:
    try:
        return str(uuid.UUID(_nonempty(value, name)))
    except ValueError as exc:
        raise LifecycleClientError(f"{name} must be a UUID") from exc


def _stable_uuid(value: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"momo-lifecycle-client:{value}"))


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
    obligation.add_argument("--target-agent", required=True)
    _common_command_args(obligation, capability=False)

    intent = subparsers.add_parser("plan-intent")
    intent.add_argument("--snapshot", required=True)
    intent.add_argument("--frontier-id")
    intent.add_argument("--capability-version", required=True, type=int)
    intent.add_argument("--evidence", required=True)
    intent.add_argument("--parameters")
    _common_command_args(intent, capability=True)

    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument("--envelope", required=True)

    args = parser.parse_args()
    try:
        if args.command == "fetch":
            _print(fetch_projection(args.candystore_url, args.lifecycle_id))
        elif args.command == "plan-obligation":
            result = build_obligation_invocation(
                _load_json(args.snapshot),
                actor=_cli_actor(args),
                target_agent_id=args.target_agent,
                requested_at=args.requested_at,
                correlation_id=args.correlation_id,
                causation_id=args.causation_id,
                obligation_id=args.obligation_id,
            )
            _print(result)
        elif args.command == "plan-intent":
            result = build_lifecycle_intent(
                _load_json(args.snapshot),
                actor=_cli_actor(args),
                capability_version=args.capability_version,
                requested_at=args.requested_at,
                correlation_id=args.correlation_id,
                causation_id=args.causation_id,
                evidence=_load_json(args.evidence),
                frontier_id=args.frontier_id,
                parameters=_load_json(args.parameters) if args.parameters else None,
            )
            _print(result)
        else:
            envelope = _load_json(args.envelope)
            print(f"published {publish_envelope(envelope)}")
    except (LifecycleClientError, OSError, json.JSONDecodeError) as exc:
        print(f"momo lifecycle client: {exc}", file=sys.stderr)
        return 2
    return 0


def _common_command_args(parser: argparse.ArgumentParser, *, capability: bool) -> None:
    del capability
    parser.add_argument("--actor-id", default="momo")
    parser.add_argument("--actor-type", default="agent_cli")
    parser.add_argument("--cli", default=os.environ.get("MOMO_CLI", "codex"))
    parser.add_argument("--provider", default=os.environ.get("MOMO_PROVIDER", "openai"))
    parser.add_argument("--requested-at", required=True)
    parser.add_argument("--correlation-id", required=True)
    parser.add_argument("--causation-id", required=True)


def _cli_actor(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "type": args.actor_type,
        "agent_id": args.actor_id,
        "cli": args.cli,
        "provider": args.provider,
    }


if __name__ == "__main__":
    raise SystemExit(main())
