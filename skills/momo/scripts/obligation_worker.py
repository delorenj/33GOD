#!/usr/bin/env python3
"""Durably execute one exact Momo-owned Lifecycle obligation invocation."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
CLIENT_SPEC = importlib.util.spec_from_file_location(
    "momo_obligation_worker_lifecycle_client",
    SCRIPT_DIR / "lifecycle_client.py",
)
if CLIENT_SPEC is None or CLIENT_SPEC.loader is None:
    raise ImportError("cannot load Momo's canonical lifecycle client")
lifecycle_client = importlib.util.module_from_spec(CLIENT_SPEC)
CLIENT_SPEC.loader.exec_module(lifecycle_client)


INVOCATION_SUBJECT = lifecycle_client.INVOCATION_SUBJECT
COMPLETION_SUBJECT = lifecycle_client.EVIDENCE_SUBJECT
DEFAULT_STREAM = "BLOODBANK_COMMANDS"
CATALOG_SCHEMA = "momo.obligation-skill-catalog.v1"
EXPECTATION_CONTRACT = "momo.obligation-worker.expectation.v1"
EVIDENCE_PACKAGE_SCHEMA = "momo.obligation-review-evidence-package.v1"
RECEIPT_SCHEMA = "momo.obligation-worker.receipt.v1"
READY_SCHEMA = "momo.obligation-worker.ready.v1"
ADAPTER = "bounded-evidence-review-v1"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
DURABLE_NAME = re.compile(r"^[^\s.*>/\\]+$")
MAX_EVIDENCE_ARTIFACTS = 16
MAX_EVIDENCE_ASSERTIONS = 64
MAX_EVIDENCE_FILE_BYTES = 2 * 1024 * 1024
MAX_EVIDENCE_TOTAL_BYTES = 8 * 1024 * 1024
EXPECTED_FIELDS = {
    "contract",
    "invocation_id",
    "lifecycle_id",
    "obligation_id",
    "obligation_instance_id",
    "activated_at",
    "target_actor_id",
    "expected_state_version",
    "authority_snapshot_event_id",
    "authority_snapshot_event_time",
    "authority_snapshot_correlation_id",
    "correlation_id",
    "causation_id",
    "skill_ref",
}


class ObligationWorkerError(RuntimeError):
    """A fail-closed durable worker error."""


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ObligationWorkerError(f"{label} is unreadable JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ObligationWorkerError(f"{label} must be a JSON object")
    return value


def _json_bytes(value: dict[str, Any]) -> bytes:
    try:
        return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    except (TypeError, ValueError) as exc:
        raise ObligationWorkerError(f"value is not canonical JSON: {exc}") from exc


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise ObligationWorkerError(f"cannot write {path}: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ObligationWorkerError(f"{label} must be non-empty text")
    return value.strip()


def _validated_sha256(value: Any, label: str) -> str:
    value = _required_text(value, label)
    if not SHA256.fullmatch(value):
        raise ObligationWorkerError(f"{label} must be 64 lowercase hex characters")
    return value


def _safe_file(root: Path, relative_path: Any, label: str) -> Path:
    relative = Path(_required_text(relative_path, label))
    if relative.is_absolute() or ".." in relative.parts:
        raise ObligationWorkerError(f"{label} must stay beneath its explicit root")
    unresolved = root / relative
    if unresolved.is_symlink():
        raise ObligationWorkerError(f"{label} cannot be a symlink")
    try:
        root = root.resolve(strict=True)
        candidate = unresolved.resolve(strict=True)
    except OSError as exc:
        raise ObligationWorkerError(f"{label} does not resolve to a file: {exc}") from exc
    if root != candidate and root not in candidate.parents:
        raise ObligationWorkerError(f"{label} escapes its explicit root")
    if not candidate.is_file():
        raise ObligationWorkerError(f"{label} is not a regular file")
    return candidate


def resolve_skill_binding(
    skill_ref: dict[str, Any],
    *,
    catalog_path: Path,
    resource_root: Path,
) -> dict[str, Any]:
    """Resolve one exact selector and verify the promoted resource bytes."""

    catalog = _load_json_object(Path(catalog_path), "skill catalog")
    if set(catalog) != {"schema", "bindings"} or catalog.get("schema") != CATALOG_SCHEMA:
        raise ObligationWorkerError("skill catalog contract is invalid")
    bindings = catalog.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        raise ObligationWorkerError("skill catalog bindings must be a non-empty array")
    expected_ref = {
        "name": _required_text(skill_ref.get("name"), "skill_ref.name"),
        "selector": _required_text(skill_ref.get("selector"), "skill_ref.selector"),
    }
    matches = [
        item
        for item in bindings
        if isinstance(item, dict)
        and item.get("name") == expected_ref["name"]
        and item.get("selector") == expected_ref["selector"]
    ]
    if len(matches) != 1:
        raise ObligationWorkerError(
            f"skill {expected_ref['name']}@{expected_ref['selector']} is not cataloged exactly once"
        )
    binding = matches[0]
    fields = {"name", "selector", "adapter", "resource_path", "resource_sha256"}
    if set(binding) != fields or binding.get("adapter") != ADAPTER:
        raise ObligationWorkerError("skill catalog binding is invalid")
    expected_digest = _validated_sha256(binding.get("resource_sha256"), "resource digest")
    resource_path = _required_text(binding.get("resource_path"), "resource_path")
    resource_file = _safe_file(Path(resource_root), resource_path, "resource_path")
    try:
        resource_bytes = resource_file.read_bytes()
    except OSError as exc:
        raise ObligationWorkerError(f"promoted skill resource is unreadable: {exc}") from exc
    actual_digest = hashlib.sha256(resource_bytes).hexdigest()
    if actual_digest != expected_digest:
        raise ObligationWorkerError(
            f"promoted skill resource digest mismatch: {actual_digest} != {expected_digest}"
        )
    return {
        **binding,
        "resource_file": str(resource_file),
        "catalog_path": str(Path(catalog_path).resolve()),
    }


def validate_invocation(
    command: dict[str, Any], expectation: dict[str, Any]
) -> dict[str, Any]:
    """Require the delivered command to match every exact current-run fact."""

    if set(expectation) != EXPECTED_FIELDS:
        missing = sorted(EXPECTED_FIELDS - set(expectation))
        extra = sorted(set(expectation) - EXPECTED_FIELDS)
        raise ObligationWorkerError(
            f"expectation fields are invalid; missing={missing}, extra={extra}"
        )
    if expectation.get("contract") != EXPECTATION_CONTRACT:
        raise ObligationWorkerError("contract does not identify the worker expectation")
    try:
        plan = lifecycle_client.reconstruct_obligation_invocation_plan(command)
    except lifecycle_client.LifecycleClientError as exc:
        raise ObligationWorkerError(f"delivered invocation is noncanonical: {exc}") from exc
    selection = plan["selection"]
    invocation = plan["invocation_command"]
    context = invocation["data"]["context"]
    actual = {
        "contract": EXPECTATION_CONTRACT,
        "invocation_id": invocation["id"],
        "lifecycle_id": selection["lifecycle_id"],
        "obligation_id": selection["obligation_id"],
        "obligation_instance_id": selection["obligation_instance_id"],
        "activated_at": selection["activated_at"],
        "target_actor_id": selection["target_actor_id"],
        "expected_state_version": selection["state_version"],
        "authority_snapshot_event_id": selection["authority_snapshot_event_id"],
        "authority_snapshot_event_time": selection["authority_snapshot_event_time"],
        "authority_snapshot_correlation_id": selection[
            "authority_snapshot_correlation_id"
        ],
        "correlation_id": invocation["correlationid"],
        "causation_id": invocation["causationid"],
        "skill_ref": context["skill_ref"],
    }
    for field in sorted(EXPECTED_FIELDS):
        if expectation[field] != actual[field]:
            raise ObligationWorkerError(
                f"{field} does not match the delivered invocation: "
                f"{expectation[field]!r} != {actual[field]!r}"
            )
    return plan


def _json_pointer(document: Any, pointer: Any) -> Any:
    pointer = _required_text(pointer, "assertion pointer")
    if pointer == "/":
        tokens = [""]
    elif pointer.startswith("/"):
        tokens = pointer[1:].split("/")
    else:
        raise ObligationWorkerError("assertion pointer must be an absolute JSON pointer")
    value = document
    for raw_token in tokens:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        try:
            if isinstance(value, list):
                value = value[int(token)]
            elif isinstance(value, dict):
                value = value[token]
            else:
                raise KeyError(token)
        except (KeyError, IndexError, ValueError) as exc:
            raise ObligationWorkerError(f"assertion pointer does not resolve: {pointer}") from exc
    return value


def hash_artifact_file(path: Path) -> str:
    """Hash the exact persisted artifact bytes."""

    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ObligationWorkerError(f"cannot hash review artifact: {exc}") from exc


def execute_bounded_review(
    *,
    invocation_plan: dict[str, Any],
    binding: dict[str, Any],
    evidence_package_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Run bounded concrete byte and JSON assertions and write a real report."""

    package_path = Path(evidence_package_path)
    package = _load_json_object(package_path, "evidence package")
    package_fields = {"schema", "run_id", "lifecycle_id", "repo", "artifacts", "assertions"}
    if set(package) != package_fields or package.get("schema") != EVIDENCE_PACKAGE_SCHEMA:
        raise ObligationWorkerError("evidence package contract is invalid")
    run_id = _required_text(package.get("run_id"), "evidence package run_id")
    command = invocation_plan["invocation_command"]
    context = command["data"]["context"]
    for field in ("lifecycle_id", "repo"):
        if package.get(field) != context.get(field):
            raise ObligationWorkerError(f"evidence package {field} does not match invocation")
    artifacts = package.get("artifacts")
    if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= MAX_EVIDENCE_ARTIFACTS:
        raise ObligationWorkerError("evidence artifacts are outside the bounded count")
    package_root = package_path.parent
    documents: dict[str, Any] = {}
    artifact_results: list[dict[str, Any]] = []
    seen_artifacts: set[str] = set()
    total_bytes = 0
    for item in artifacts:
        fields = {"id", "path", "media_type", "size_bytes", "sha256"}
        if not isinstance(item, dict) or set(item) != fields:
            raise ObligationWorkerError("evidence artifact contract is invalid")
        artifact_id = _required_text(item.get("id"), "evidence artifact id")
        if artifact_id in seen_artifacts:
            raise ObligationWorkerError(f"duplicate evidence artifact id: {artifact_id}")
        seen_artifacts.add(artifact_id)
        if item.get("media_type") != "application/json":
            raise ObligationWorkerError("bounded review accepts only application/json evidence")
        path = _safe_file(package_root, item.get("path"), "evidence artifact path")
        try:
            exact_bytes = path.read_bytes()
        except OSError as exc:
            raise ObligationWorkerError(f"evidence artifact is unreadable: {exc}") from exc
        if len(exact_bytes) > MAX_EVIDENCE_FILE_BYTES:
            raise ObligationWorkerError("evidence artifact exceeds the per-file byte limit")
        total_bytes += len(exact_bytes)
        if total_bytes > MAX_EVIDENCE_TOTAL_BYTES:
            raise ObligationWorkerError("evidence package exceeds the total byte limit")
        size = item.get("size_bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size != len(exact_bytes):
            raise ObligationWorkerError(f"evidence artifact size mismatch: {artifact_id}")
        expected_digest = _validated_sha256(item.get("sha256"), "evidence artifact sha256")
        actual_digest = hashlib.sha256(exact_bytes).hexdigest()
        if actual_digest != expected_digest:
            raise ObligationWorkerError(f"evidence artifact digest mismatch: {artifact_id}")
        try:
            documents[artifact_id] = json.loads(exact_bytes)
        except json.JSONDecodeError as exc:
            raise ObligationWorkerError(
                f"evidence artifact is not valid JSON: {artifact_id}: {exc}"
            ) from exc
        artifact_results.append(
            {
                "id": artifact_id,
                "path": item["path"],
                "size_bytes": size,
                "sha256": actual_digest,
            }
        )

    assertions = package.get("assertions")
    if not isinstance(assertions, list) or not 1 <= len(assertions) <= MAX_EVIDENCE_ASSERTIONS:
        raise ObligationWorkerError("evidence assertions are outside the bounded count")
    assertion_results: list[dict[str, str]] = []
    seen_assertions: set[str] = set()
    for assertion in assertions:
        fields = {"id", "artifact_id", "pointer", "equals"}
        if not isinstance(assertion, dict) or set(assertion) != fields:
            raise ObligationWorkerError("evidence assertion contract is invalid")
        assertion_id = _required_text(assertion.get("id"), "evidence assertion id")
        if assertion_id in seen_assertions:
            raise ObligationWorkerError(f"duplicate evidence assertion id: {assertion_id}")
        seen_assertions.add(assertion_id)
        artifact_id = _required_text(assertion.get("artifact_id"), "assertion artifact_id")
        if artifact_id not in documents:
            raise ObligationWorkerError(f"assertion references unknown artifact: {artifact_id}")
        actual = _json_pointer(documents[artifact_id], assertion.get("pointer"))
        if actual != assertion.get("equals"):
            raise ObligationWorkerError(
                f"evidence assertion failed: {assertion_id}: "
                f"{actual!r} != {assertion.get('equals')!r}"
            )
        assertion_results.append(
            {
                "id": assertion_id,
                "artifact_id": artifact_id,
                "pointer": assertion["pointer"],
            }
        )

    lines = [
        "# Momo obligation review report",
        "",
        "- Verdict: PASS",
        f"- Run: `{run_id}`",
        f"- Lifecycle: `{context['lifecycle_id']}`",
        f"- Invocation: `{command['id']}`",
        f"- Skill: `{binding['name']}@{binding['selector']}`",
        f"- Skill resource: `{binding['resource_path']}`",
        f"- Skill resource SHA-256: `{binding['resource_sha256']}`",
        f"- Adapter: `{binding['adapter']}`",
        "",
        "## Artifact byte checks",
        "",
    ]
    lines.extend(
        f"- PASS `{item['id']}`: {item['size_bytes']} bytes, SHA-256 `{item['sha256']}`"
        for item in artifact_results
    )
    lines.extend(["", "## Structured assertions", ""])
    lines.extend(
        f"- PASS `{item['id']}`: `{item['artifact_id']}{item['pointer']}`"
        for item in assertion_results
    )
    report_bytes = ("\n".join(lines) + "\n").encode()
    report_path = Path(report_path)
    _atomic_write(report_path, report_bytes)
    try:
        persisted_bytes = report_path.read_bytes()
    except OSError as exc:
        raise ObligationWorkerError(f"cannot reread review artifact: {exc}") from exc
    if persisted_bytes != report_bytes:
        raise ObligationWorkerError("persisted review artifact bytes differ from adapter output")
    expected_hash = hashlib.sha256(persisted_bytes).hexdigest()
    persisted_hash = hash_artifact_file(report_path)
    if persisted_hash != expected_hash:
        raise ObligationWorkerError("review artifact hash does not match exact persisted bytes")
    if len(set(persisted_hash)) == 1:
        raise ObligationWorkerError("review artifact hash is a placeholder pattern")
    return {
        "artifact_id": f"review-report:{command['id']}",
        "path": str(report_path.resolve()),
        "size_bytes": len(persisted_bytes),
        "sha256": persisted_hash,
        "summary": (
            f"Bounded {binding['name']} review passed "
            f"{len(artifact_results)} artifact and {len(assertion_results)} assertion checks."
        ),
    }


def _delivery_metadata(message: Any, *, expected_stream: str, consumer: str) -> dict[str, Any]:
    try:
        metadata = message.metadata
        delivery = {
            "stream": metadata.stream,
            "consumer": metadata.consumer,
            "stream_sequence": metadata.sequence.stream,
            "consumer_sequence": metadata.sequence.consumer,
            "num_delivered": metadata.num_delivered,
        }
    except (AttributeError, TypeError, ValueError) as exc:
        raise ObligationWorkerError("invocation lacks canonical JetStream metadata") from exc
    if delivery["stream"] != expected_stream:
        raise ObligationWorkerError("delivery stream does not match the configured stream")
    if delivery["consumer"] != consumer:
        raise ObligationWorkerError("delivery consumer does not match the named durable")
    for field in ("stream_sequence", "consumer_sequence", "num_delivered"):
        value = delivery[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ObligationWorkerError(f"delivery {field} must be an integer >= 1")
    return delivery


async def _wait_for_release(path: Path, timeout: float) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if path.is_file():
            return
        await asyncio.sleep(0.05)
    raise ObligationWorkerError(f"completion release file did not appear within {timeout}s")


async def process_invocation_message(
    *,
    message: Any,
    jetstream: Any,
    expectation: dict[str, Any],
    catalog_path: Path,
    resource_root: Path,
    evidence_package_path: Path,
    report_path: Path,
    receipt_path: Path,
    expected_stream: str,
    consumer: str,
    clock: Any = None,
    preview_path: Path | None = None,
    release_path: Path | None = None,
    release_timeout: float = 60.0,
    publish_timeout: float = 10.0,
    ack_timeout: float = 10.0,
) -> dict[str, Any]:
    """Process one broker delivery and positively acknowledge only after PubAck."""

    operations = ["invocation_received"]
    if getattr(message, "subject", None) != INVOCATION_SUBJECT:
        raise ObligationWorkerError("invocation subject is not canonical")
    delivery = _delivery_metadata(message, expected_stream=expected_stream, consumer=consumer)
    try:
        command = json.loads(message.data)
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ObligationWorkerError(f"invocation payload is not JSON: {exc}") from exc
    if not isinstance(command, dict):
        raise ObligationWorkerError("invocation payload must be a JSON object")
    plan = validate_invocation(command, expectation)
    operations.append("invocation_validated")
    binding = resolve_skill_binding(
        plan["selection"]["skill_ref"],
        catalog_path=Path(catalog_path),
        resource_root=Path(resource_root),
    )
    operations.append("skill_resource_verified")
    artifact = execute_bounded_review(
        invocation_plan=plan,
        binding=binding,
        evidence_package_path=Path(evidence_package_path),
        report_path=Path(report_path),
    )
    operations.extend(["review_artifact_written", "review_artifact_hashed"])
    completed_at = clock() if clock is not None else _utc_now()
    try:
        completion_plan = lifecycle_client.build_obligation_completion_evidence(
            plan,
            completed_at=completed_at,
            evidence={
                "kind": "skill_completion",
                "outcome": "completed",
                "artifact_id": artifact["artifact_id"],
                "artifact_sha256": artifact["sha256"],
                "summary": artifact["summary"],
            },
        )
    except lifecycle_client.LifecycleClientError as exc:
        raise ObligationWorkerError(f"completion adapter failed: {exc}") from exc
    completion = completion_plan["completion_evidence"]
    operations.append("completion_built")
    if preview_path is not None:
        _atomic_write(Path(preview_path), _json_bytes(completion))
        operations.append("completion_preview_written")
    if release_path is not None:
        await _wait_for_release(Path(release_path), release_timeout)
        operations.append("completion_released")
    operations.append("completion_publish_requested")
    try:
        puback = await lifecycle_client.publish_envelope_async(
            completion,
            publish=lambda subject, payload: jetstream.publish(
                subject,
                payload,
                timeout=publish_timeout,
            ),
        )
    except Exception as exc:
        raise ObligationWorkerError(f"completion publication failed without PubAck: {exc}") from exc
    puback_stream = getattr(puback, "stream", None)
    puback_sequence = getattr(puback, "seq", None)
    if (
        not isinstance(puback_stream, str)
        or not puback_stream
        or isinstance(puback_sequence, bool)
        or not isinstance(puback_sequence, int)
        or puback_sequence < 1
    ):
        raise ObligationWorkerError("completion publication did not return a positive PubAck")
    operations.append("completion_puback")
    try:
        await message.ack_sync(timeout=ack_timeout)
    except Exception as exc:
        raise ObligationWorkerError(f"invocation ack_sync failed: {exc}") from exc
    operations.append("invocation_ack_sync")
    receipt_operations = [*operations, "receipt_written"]
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "completed",
        "delivery": delivery,
        "invocation": {
            "id": command["id"],
            "subject": command["subject"],
            "correlation_id": command["correlationid"],
            "causation_id": command["causationid"],
        },
        "skill": {
            "name": binding["name"],
            "selector": binding["selector"],
            "adapter": binding["adapter"],
            "resource_path": binding["resource_path"],
            "resource_sha256": binding["resource_sha256"],
            "catalog_path": binding["catalog_path"],
        },
        "artifact": artifact,
        "completion": {
            "event_id": completion["id"],
            "subject": completion["subject"],
            "stream": puback_stream,
            "stream_sequence": puback_sequence,
            "duplicate": bool(getattr(puback, "duplicate", False)),
        },
        "operation_order": [
            {"sequence": index, "operation": operation}
            for index, operation in enumerate(receipt_operations, start=1)
        ],
    }
    _atomic_write(Path(receipt_path), _json_bytes(receipt))
    return receipt


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


async def run_worker(args: argparse.Namespace) -> dict[str, Any]:
    """Connect, establish the named durable, and process exactly one delivery."""

    if not DURABLE_NAME.fullmatch(args.consumer):
        raise ObligationWorkerError("consumer is not a valid named durable")
    for output in (args.ready_file, args.receipt, args.preview_file):
        if output is not None and Path(output).exists():
            raise ObligationWorkerError(f"refusing stale worker output: {output}")
    try:
        import nats
        from nats.js.api import AckPolicy, ConsumerConfig, DeliverPolicy, ReplayPolicy
    except ImportError as exc:
        raise ObligationWorkerError("nats-py is required for durable execution") from exc

    connection = await nats.connect(
        servers=[args.nats_url],
        name=f"momo-obligation-worker-{args.consumer}",
        connect_timeout=min(args.timeout, 10.0),
        max_reconnect_attempts=2,
    )
    try:
        jetstream = connection.jetstream()
        config = ConsumerConfig(
            durable_name=args.consumer,
            ack_policy=AckPolicy.EXPLICIT,
            ack_wait=max(args.timeout, 30.0),
            deliver_policy=DeliverPolicy.ALL,
            replay_policy=ReplayPolicy.INSTANT,
            filter_subject=INVOCATION_SUBJECT,
            max_deliver=3,
            max_ack_pending=1,
        )
        subscription = await jetstream.pull_subscribe(
            INVOCATION_SUBJECT,
            durable=args.consumer,
            stream=args.stream,
            config=config,
        )
        info = await subscription.consumer_info()
        if info.stream_name != args.stream or info.name != args.consumer:
            raise ObligationWorkerError("JetStream created the wrong durable consumer")
        if (
            info.config.filter_subject != INVOCATION_SUBJECT
            or info.config.ack_policy != AckPolicy.EXPLICIT
        ):
            raise ObligationWorkerError("JetStream durable consumer config is noncanonical")
        ready = {
            "schema": READY_SCHEMA,
            "status": "ready",
            "stream": args.stream,
            "consumer": args.consumer,
            "subject": INVOCATION_SUBJECT,
            "ack_policy": "explicit",
            "ready_at": _utc_now(),
        }
        _atomic_write(Path(args.ready_file), _json_bytes(ready))
        try:
            messages = await subscription.fetch(1, timeout=args.timeout)
        except Exception as exc:
            raise ObligationWorkerError(f"durable fetch failed: {exc}") from exc
        if len(messages) != 1:
            raise ObligationWorkerError("durable fetch did not return exactly one invocation")
        return await process_invocation_message(
            message=messages[0],
            jetstream=jetstream,
            expectation=_load_json_object(Path(args.expectation), "invocation expectation"),
            catalog_path=Path(args.catalog),
            resource_root=Path(args.resource_root),
            evidence_package_path=Path(args.evidence_package),
            report_path=Path(args.report),
            receipt_path=Path(args.receipt),
            expected_stream=args.stream,
            consumer=args.consumer,
            preview_path=Path(args.preview_file) if args.preview_file else None,
            release_path=Path(args.release_file) if args.release_file else None,
            release_timeout=args.release_timeout,
            publish_timeout=args.publish_timeout,
            ack_timeout=args.ack_timeout,
        )
    finally:
        await connection.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nats-url", required=True)
    parser.add_argument("--stream", default=DEFAULT_STREAM)
    parser.add_argument("--consumer", required=True)
    parser.add_argument("--expectation", required=True)
    parser.add_argument(
        "--catalog",
        default=str(SCRIPT_DIR.parent / "resources" / "obligation-skill-catalog.json"),
    )
    parser.add_argument("--resource-root", required=True)
    parser.add_argument("--evidence-package", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--ready-file", required=True)
    parser.add_argument("--preview-file")
    parser.add_argument("--release-file")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--release-timeout", type=float, default=90.0)
    parser.add_argument("--publish-timeout", type=float, default=10.0)
    parser.add_argument("--ack-timeout", type=float, default=10.0)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        receipt = asyncio.run(run_worker(args))
    except (ObligationWorkerError, OSError, ValueError) as exc:
        print(f"momo obligation worker: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
