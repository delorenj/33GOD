#!/usr/bin/env python3
"""Run the isolated live Lifecycle/client failure-proof matrix.

Every Docker resource is uniquely named and removed explicitly during cleanup.
Registry images are exercised only by immutable digest.
"""

from __future__ import annotations

import argparse
import base64
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid


PLATFORM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PLATFORM_ROOT.parent
COMPOSE_FILE = PLATFORM_ROOT / "compose.yaml"
LIFECYCLE_IMAGE = (
    "ghcr.io/delorenj/lifecycle@"
    "sha256:b216be4e1b796236309ee0b39120b0f353b62ee9f3c677901b2441a2c7aef210"
)
NATS_BOX_IMAGE = (
    "natsio/nats-box@"
    "sha256:0784ab710aefaf6ef037ed797ee7dcde613c6ad208c4dbff1945fc7c1b5b5375"
)
ACTOR_ID = "operator:33god-bootstrap"
CAPABILITY_ID = "cap:33god-platform:lifecycle-command"
REPO = "delorenj/33GOD"
COMMAND_STREAM = "BLOODBANK_COMMANDS"
COMMAND_CONSUMER = "lifecycle-authority-commands-v1"
INVOCATION_SUBJECT = "bloodbank.cmd.v1.agent.invocation.start"
PROTECTED_BASELINE_CONTAINERS = (
    "bloodbank-nats",
    "bloodbank-dapr-placement",
    "candystore-postgres",
    "candystore",
    "candystore-daprd",
    "holocene-web",
)


class LiveProofError(RuntimeError):
    pass


def run(
    command: list[str],
    *,
    cwd: Path = SOURCE_ROOT,
    env: dict[str, str] | None = None,
    check: bool = True,
    timeout: float = 180,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise LiveProofError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{detail[-4000:]}"
        )
    return result


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wire_time(offset_seconds: int = 0) -> str:
    value = datetime.now(UTC) + timedelta(seconds=offset_seconds)
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def stable_uuid(value: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"33god-live-matrix:{value}"))


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def wait_for(
    description: str,
    predicate: Callable[[], Any],
    *,
    timeout: float = 60,
    interval: float = 0.2,
) -> Any:
    deadline = time.monotonic() + timeout
    last: Any = None
    while time.monotonic() < deadline:
        try:
            last = predicate()
            if last:
                return last
        except (OSError, ValueError, LiveProofError) as exc:
            last = exc
        time.sleep(interval)
    raise LiveProofError(f"timed out waiting for {description}; last={last!r}")


def http_json(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: float = 5,
) -> tuple[int, Any]:
    payload = json.dumps(body).encode() if body is not None else None
    request = Request(
        url,
        data=payload,
        method=method,
        headers={
            "accept": "application/json",
            **({"content-type": "application/json"} if payload is not None else {}),
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read()
        return exc.code, json.loads(raw) if raw else None


def terminate(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


class Harness:
    def __init__(
        self,
        screenshots_dir: Path | None,
        proof_dir: Path | None = None,
    ) -> None:
        self.suffix = uuid.uuid4().hex[:10]
        self.project = f"aion-lifecycle-{self.suffix}"
        self.lifecycle_id = f"lc_aion_{self.suffix}"
        self.proof_dir = proof_dir.resolve() if proof_dir is not None else None
        if self.proof_dir is not None:
            if self.proof_dir.exists():
                if any(self.proof_dir.iterdir()):
                    raise LiveProofError(
                        f"proof directory must be empty: {self.proof_dir}"
                    )
            else:
                self.proof_dir.mkdir(parents=True)
        self.password = secrets.token_hex(20)
        self.secret_dir = PLATFORM_ROOT / f".aion-secret-{self.suffix}"
        self.secret_dir.mkdir(mode=0o700)
        self.secret_file = self.secret_dir / "lifecycle-postgres-password"
        secret_fd = os.open(
            self.secret_file,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(secret_fd, "w", encoding="utf-8") as secret_handle:
            secret_handle.write(self.password)
        self.secret_file.chmod(0o444)
        self.screenshots_dir = screenshots_dir
        self.candystore_image = f"candystore:aion-{self.suffix}"
        self.ports = {
            key: free_port()
            for key in (
                "nats",
                "nats_monitor",
                "placement",
                "lifecycle",
                "candystore_postgres",
                "candystore",
                "candystore_dapr",
                "api",
                "web",
            )
        }
        self.networks = {
            "bloodbank": f"aion-{self.suffix}-bloodbank",
            "lifecycle": f"aion-{self.suffix}-lifecycle",
            "candystore": f"aion-{self.suffix}-candystore",
            "proxy": f"aion-{self.suffix}-proxy",
        }
        self.volumes = {
            "nats": f"aion-{self.suffix}-nats",
            "lifecycle": f"aion-{self.suffix}-lifecycle-pg",
            "candystore": f"aion-{self.suffix}-candystore-pg",
            "holocene": f"aion-{self.suffix}-holocene-node",
            "holocene_web": f"aion-{self.suffix}-holocene-web-node",
            "holocene_next": f"aion-{self.suffix}-holocene-next",
        }
        self.env = os.environ.copy()
        self.env.update(
            {
                "GOD_SOURCE_ROOT": str(SOURCE_ROOT),
                "LIFECYCLE_POSTGRES_PASSWORD_FILE": str(self.secret_file),
                "LIFECYCLE_BOOTSTRAP_ID": self.lifecycle_id,
                "LIFECYCLE_BOOTSTRAP_NAME": f"Aion matrix {self.suffix}",
                "LIFECYCLE_BOOTSTRAP_REPO": REPO,
                "LIFECYCLE_BOOTSTRAP_ACTOR_ID": ACTOR_ID,
                "LIFECYCLE_BOOTSTRAP_CAPABILITY_ID": CAPABILITY_ID,
                "LIFECYCLE_BOOTSTRAP_AS_OF": wire_time(-60),
                "BLOODBANK_NATS_CLIENT_PORT": str(self.ports["nats"]),
                "BLOODBANK_NATS_MONITOR_PORT": str(self.ports["nats_monitor"]),
                "BLOODBANK_DAPR_PLACEMENT_PORT": str(self.ports["placement"]),
                "LIFECYCLE_PORT": str(self.ports["lifecycle"]),
                "CANDYSTORE_POSTGRES_PORT": str(self.ports["candystore_postgres"]),
                "CANDYSTORE_PORT": str(self.ports["candystore"]),
                "CANDYSTORE_DAPR_HTTP_PORT": str(self.ports["candystore_dapr"]),
                "BLOODBANK_NETWORK_NAME": self.networks["bloodbank"],
                "LIFECYCLE_NETWORK_NAME": self.networks["lifecycle"],
                "CANDYSTORE_NETWORK_NAME": self.networks["candystore"],
                "PROXY_NETWORK_NAME": self.networks["proxy"],
                "BLOODBANK_NATS_VOLUME": self.volumes["nats"],
                "LIFECYCLE_POSTGRES_VOLUME": self.volumes["lifecycle"],
                "CANDYSTORE_POSTGRES_VOLUME": self.volumes["candystore"],
                "HOLOCENE_NODE_MODULES_VOLUME": self.volumes["holocene"],
                "HOLOCENE_WEB_NODE_MODULES_VOLUME": self.volumes["holocene_web"],
                "HOLOCENE_WEB_NEXT_VOLUME": self.volumes["holocene_next"],
                "CANDYSTORE_IMAGE": self.candystore_image,
            }
        )
        self.api_process: subprocess.Popen[bytes] | None = None
        self.web_process: subprocess.Popen[bytes] | None = None
        self.lifecycle_lock_holder: subprocess.Popen[bytes] | None = None
        self.lifecycle_lock_application = f"lifecycle-outage-lock-{self.suffix}"
        self.lifecycle_lock_backend_pid: int | None = None
        self.lifecycle_recovery_guard: subprocess.Popen[bytes] | None = None
        self.lifecycle_recovery_application = (
            f"lifecycle-outage-recovery-{self.suffix}"
        )
        self.momo_actor_process: subprocess.Popen[bytes] | None = None
        self.created_resources = False
        self.cleaned = False
        self.prestart_snapshot_event_id: str | None = None
        self.prestart_verdict_command_id: str | None = None
        self.containers_before: list[str] = []
        self.summary: dict[str, Any] = {
            "project": self.project,
            "lifecycle_id": self.lifecycle_id,
            "image": LIFECYCLE_IMAGE,
            "bloodbank_commit": "48031ee39c238b9d4715b81b74076635235f96d5",
            "proof_dir": str(self.proof_dir) if self.proof_dir is not None else None,
            "invariants": {},
            "seams": {},
        }

    def compose_command(self, *args: str) -> list[str]:
        return [
            "docker",
            "compose",
            "--project-name",
            self.project,
            "--file",
            str(COMPOSE_FILE),
            *args,
        ]

    def compose(self, *args: str, check: bool = True, timeout: float = 180):
        return run(
            self.compose_command(*args),
            env=self.env,
            check=check,
            timeout=timeout,
        )

    def docker(self, *args: str, check: bool = True, timeout: float = 180):
        return run(["docker", *args], check=check, timeout=timeout)

    def container_inventory(self) -> list[str]:
        return sorted(
            item
            for item in self.docker(
                "ps", "-a", "--format", "{{.Names}}"
            ).stdout.splitlines()
            if item
        )

    def owned_resource_inventory(self) -> dict[str, Any]:
        containers = sorted(
            item
            for item in self.docker(
                "ps",
                "-a",
                "--filter",
                f"label=com.docker.compose.project={self.project}",
                "--format",
                "{{.Names}}",
            ).stdout.splitlines()
            if item
        )
        networks = set(
            self.docker("network", "ls", "--format", "{{.Name}}").stdout.splitlines()
        )
        volumes = set(
            self.docker("volume", "ls", "--format", "{{.Name}}").stdout.splitlines()
        )
        image = self.docker("image", "inspect", self.candystore_image, check=False)
        return {
            "containers": containers,
            "networks": sorted(set(self.networks.values()) & networks),
            "volumes": sorted(set(self.volumes.values()) & volumes),
            "local_image_present": image.returncode == 0,
        }

    def create_resources(self) -> None:
        for name in self.networks.values():
            self.docker("network", "create", name)
        for name in self.volumes.values():
            self.docker("volume", "create", name)
        self.created_resources = True

    def cleanup(self) -> None:
        if self.cleaned:
            return
        terminate(self.momo_actor_process)
        self.release_lifecycle_recovery_guard(check=False)
        self.release_lifecycle_row_lock(check=False)
        terminate(self.web_process)
        terminate(self.api_process)
        self.compose("down", "--remove-orphans", "--timeout", "10", check=False)
        if self.created_resources:
            for name in reversed(tuple(self.volumes.values())):
                self.docker("volume", "rm", name, check=False)
            for name in reversed(tuple(self.networks.values())):
                self.docker("network", "rm", name, check=False)
        self.docker("image", "rm", self.candystore_image, check=False)
        self.secret_file.unlink(missing_ok=True)
        if self.secret_dir.exists():
            self.secret_dir.rmdir()
        self.cleaned = True

    def preflight(self) -> None:
        self.containers_before = self.container_inventory()
        self.summary["isolation"] = {
            "containers_before": self.containers_before,
            "protected_before": {
                name: name in self.containers_before
                for name in PROTECTED_BASELINE_CONTAINERS
            },
        }
        rendered = self.compose("config", "--format", "json").stdout
        if self.password in rendered:
            raise LiveProofError(
                "Compose render disclosed the Lifecycle PostgreSQL secret"
            )
        services = json.loads(rendered)["services"]
        for name in ("lifecycle-migrate", "lifecycle-bootstrap", "lifecycle"):
            if (
                services[name].get("image") != LIFECYCLE_IMAGE
                or "build" in services[name]
            ):
                raise LiveProofError(f"{name} image/build invariant failed")
        for name, service in services.items():
            if name != "candystore" and "@sha256:" not in service.get("image", ""):
                raise LiveProofError(f"{name} registry image is not digest pinned")
            if "container_name" in service:
                raise LiveProofError(f"{name} rendered a fixed container_name")
        semantic = run(
            [
                sys.executable,
                str(PLATFORM_ROOT / "scripts" / "validate-compose.py"),
                "--source-root",
                str(SOURCE_ROOT),
            ],
            env=self.env,
        )
        self.summary["compose"] = {
            "semantic": semantic.stdout.strip(),
            "services": sorted(services),
            "lifecycle_has_build": False,
        }

    def psql(
        self,
        sql: str,
        *,
        check: bool = True,
        timeout: float = 180,
    ) -> str:
        return self.compose(
            "exec",
            "-T",
            "lifecycle-postgres",
            "psql",
            "-X",
            "-qAt",
            "-U",
            "lifecycle",
            "-d",
            "lifecycle",
            "-c",
            sql,
            check=check,
            timeout=timeout,
        ).stdout.strip()

    def start_lifecycle_row_lock(self) -> subprocess.Popen[bytes]:
        """Hold the target authority row in one visible PostgreSQL session."""

        if (
            self.lifecycle_lock_holder is not None
            and self.lifecycle_lock_holder.poll() is None
        ):
            raise LiveProofError("Lifecycle row-lock holder is already running")
        sql = f"""
BEGIN;
SELECT lifecycle_id
FROM lifecycle_state
WHERE lifecycle_id = {sql_literal(self.lifecycle_id)}
FOR UPDATE;
SELECT pg_sleep(300);
ROLLBACK;
"""
        self.lifecycle_lock_holder = subprocess.Popen(
            self.compose_command(
                "exec",
                "-T",
                "--env",
                f"PGAPPNAME={self.lifecycle_lock_application}",
                "lifecycle-postgres",
                "psql",
                "-X",
                "-qAt",
                "-v",
                "ON_ERROR_STOP=1",
                "-U",
                "lifecycle",
                "-d",
                "lifecycle",
                "-c",
                sql,
            ),
            cwd=SOURCE_ROOT,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return self.lifecycle_lock_holder

    def wait_lifecycle_row_lock(self) -> dict[str, Any]:
        """Require pg_stat_activity proof that the lock transaction is active."""

        def probe() -> dict[str, Any] | None:
            process = self.lifecycle_lock_holder
            if process is None:
                raise LiveProofError("Lifecycle row-lock holder was not started")
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                detail = (stderr or stdout).decode(errors="replace").strip()
                raise LiveProofError(
                    "Lifecycle row-lock holder exited before becoming active: "
                    + detail[-2000:]
                )
            raw = self.psql(
                """
                SELECT json_build_object(
                  'pid', pid, 'application_name', application_name,
                  'state', state, 'wait_event_type', wait_event_type,
                  'wait_event', wait_event
                )::text
                FROM pg_stat_activity
                WHERE application_name = %s
                  AND state = 'active'
                  AND query LIKE '%%FOR UPDATE%%'
                  AND query LIKE '%%pg_sleep(300)%%'
                ORDER BY pid
                LIMIT 1
                """
                % sql_literal(self.lifecycle_lock_application)
            )
            return json.loads(raw) if raw else None

        activity = wait_for(
            "active Lifecycle row-lock holder in pg_stat_activity",
            probe,
            timeout=30,
        )
        self.lifecycle_lock_backend_pid = int(activity["pid"])
        return activity

    def wait_blocked_lifecycle_writer(self) -> dict[str, Any]:
        """Prove a deployed service backend is waiting behind the row holder."""

        if self.lifecycle_lock_backend_pid is None:
            raise LiveProofError("Lifecycle row-lock holder has no PostgreSQL pid")
        holder_pid = self.lifecycle_lock_backend_pid

        def probe() -> dict[str, Any] | None:
            raw = self.psql(
                f"""
                SELECT json_build_object(
                  'pid', pid, 'application_name', application_name,
                  'state', state, 'wait_event_type', wait_event_type,
                  'wait_event', wait_event,
                  'blocking_pids', pg_blocking_pids(pid)
                )::text
                FROM pg_stat_activity
                WHERE pid <> {holder_pid}
                  AND {holder_pid} = ANY(pg_blocking_pids(pid))
                  AND wait_event_type = 'Lock'
                ORDER BY pid
                LIMIT 1
                """
            )
            return json.loads(raw) if raw else None

        return wait_for(
            "deployed Lifecycle PostgreSQL writer blocked by row lock",
            probe,
            timeout=30,
        )

    def release_lifecycle_row_lock(self, *, check: bool = True) -> None:
        """Terminate the unique PostgreSQL holder and its attached client."""

        process = self.lifecycle_lock_holder
        if process is None and self.lifecycle_lock_backend_pid is None:
            return
        terminated = self.psql(
            """
            SELECT COUNT(*)
            FROM (
              SELECT pg_terminate_backend(pid) AS terminated
              FROM pg_stat_activity
              WHERE application_name = %s
                AND pid <> pg_backend_pid()
            ) AS holders
            WHERE terminated
            """
            % sql_literal(self.lifecycle_lock_application),
            check=check,
            timeout=15,
        )
        terminate(process)
        self.lifecycle_lock_holder = None
        self.lifecycle_lock_backend_pid = None
        if check and terminated != "1":
            raise LiveProofError(
                f"expected one Lifecycle row-lock backend to terminate, got {terminated!r}"
            )

    def start_lifecycle_recovery_guard(self) -> subprocess.Popen[bytes]:
        """Keep restart-time sweeping separate from the redelivery assertion."""

        if (
            self.lifecycle_recovery_guard is not None
            and self.lifecycle_recovery_guard.poll() is None
        ):
            raise LiveProofError("Lifecycle recovery guard is already running")
        sql = """
BEGIN;
LOCK TABLE lifecycle_reconcile_queue IN ACCESS EXCLUSIVE MODE;
SELECT pg_sleep(300);
ROLLBACK;
"""
        self.lifecycle_recovery_guard = subprocess.Popen(
            self.compose_command(
                "exec",
                "-T",
                "--env",
                f"PGAPPNAME={self.lifecycle_recovery_application}",
                "lifecycle-postgres",
                "psql",
                "-X",
                "-qAt",
                "-v",
                "ON_ERROR_STOP=1",
                "-U",
                "lifecycle",
                "-d",
                "lifecycle",
                "-c",
                sql,
            ),
            cwd=SOURCE_ROOT,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return self.lifecycle_recovery_guard

    def wait_lifecycle_recovery_guard(self) -> dict[str, Any]:
        def probe() -> dict[str, Any] | None:
            process = self.lifecycle_recovery_guard
            if process is None:
                raise LiveProofError("Lifecycle recovery guard was not started")
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                detail = (stderr or stdout).decode(errors="replace").strip()
                raise LiveProofError(
                    "Lifecycle recovery guard exited before becoming active: "
                    + detail[-2000:]
                )
            raw = self.psql(
                """
                SELECT json_build_object(
                  'pid', pid, 'application_name', application_name,
                  'state', state, 'wait_event_type', wait_event_type,
                  'wait_event', wait_event
                )::text
                FROM pg_stat_activity
                WHERE application_name = %s
                  AND state = 'active'
                  AND query LIKE '%%LOCK TABLE lifecycle_reconcile_queue%%'
                  AND query LIKE '%%pg_sleep(300)%%'
                ORDER BY pid
                LIMIT 1
                """
                % sql_literal(self.lifecycle_recovery_application)
            )
            return json.loads(raw) if raw else None

        return wait_for(
            "active restart-time reconcile isolation guard",
            probe,
            timeout=30,
        )

    def release_lifecycle_recovery_guard(self, *, check: bool = True) -> None:
        process = self.lifecycle_recovery_guard
        if process is None:
            return
        terminated = self.psql(
            """
            SELECT COUNT(*)
            FROM (
              SELECT pg_terminate_backend(pid) AS terminated
              FROM pg_stat_activity
              WHERE application_name = %s
                AND pid <> pg_backend_pid()
            ) AS guards
            WHERE terminated
            """
            % sql_literal(self.lifecycle_recovery_application),
            check=check,
            timeout=15,
        )
        terminate(process)
        self.lifecycle_recovery_guard = None
        if check and terminated != "1":
            raise LiveProofError(
                f"expected one Lifecycle recovery guard to terminate, got {terminated!r}"
            )

    def candystore_psql(self, sql: str) -> str:
        return self.compose(
            "exec",
            "-T",
            "candystore-postgres",
            "psql",
            "-X",
            "-qAt",
            "-U",
            "candystore",
            "-d",
            "candystore",
            "-c",
            sql,
        ).stdout.strip()

    def state(self) -> dict[str, Any]:
        raw = self.psql(
            """
            SELECT json_build_object(
              'status', status, 'health', health, 'mode', mode,
              'spec_version', spec_version, 'state_version', state_version,
              'fingerprint', state_fingerprint, 'legal_frontier', legal_frontier,
              'obligations', obligations, 'capabilities', capabilities,
              'observed_through', observed_through,
              'last_reconciled_at', last_reconciled_at
            )::text
            FROM lifecycle_state WHERE lifecycle_id = %s
            """
            % sql_literal(self.lifecycle_id)
        )
        if not raw:
            raise LiveProofError("Lifecycle state row is missing")
        return json.loads(raw)

    def capability_version(self) -> int:
        state = self.state()
        grant = next(
            (
                item
                for item in state.get("capabilities", [])
                if item.get("capability_id") == CAPABILITY_ID
                and item.get("actor_id") == ACTOR_ID
            ),
            None,
        )
        if grant is None:
            raise LiveProofError("authoritative bootstrap capability grant is missing")
        version = grant.get("capability_version")
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise LiveProofError(
                "authoritative capability_version is missing or invalid"
            )
        return version

    def counts(self) -> dict[str, int]:
        values = tuple([sql_literal(self.lifecycle_id)] * 5)
        raw = self.psql(
            """
            SELECT json_build_object(
              'history', (SELECT COUNT(*) FROM lifecycle_status_history WHERE lifecycle_id = %s),
              'commands', (SELECT COUNT(*) FROM lifecycle_command_results WHERE lifecycle_id = %s),
              'observations', (SELECT COUNT(*) FROM lifecycle_observations WHERE lifecycle_id = %s),
              'outbox', (SELECT COUNT(*) FROM lifecycle_event_outbox WHERE lifecycle_id = %s),
              'outbox_pending', (SELECT COUNT(*) FROM lifecycle_event_outbox
                WHERE lifecycle_id = %s AND published_at IS NULL)
            )::text
            """
            % values
        )
        return {key: int(value) for key, value in json.loads(raw).items()}

    def reconcile_queue_depth(self) -> int:
        return int(
            self.psql(
                "SELECT COUNT(*) FROM lifecycle_reconcile_queue "
                f"WHERE lifecycle_id = {sql_literal(self.lifecycle_id)}"
            )
        )

    def command_result(self, event_id: str) -> dict[str, Any] | None:
        raw = self.psql(
            """
            SELECT json_build_object(
              'verdict', verdict, 'mutated', mutated, 'reason_code', reason_code,
              'expected_state_version', expected_state_version,
              'observed_state_version', observed_state_version,
              'resulting_state_version', resulting_state_version,
              'command_event_id', command_event_id, 'command_id', command_id,
              'idempotency_key', idempotency_key,
              'capability_id', capability_id, 'applied_event_id', applied_event_id,
              'reply_event_id', reply_envelope->>'id',
              'reply_subject', reply_envelope->>'subject',
              'reply_correlation_id', reply_envelope->>'correlationid',
              'reply_causation_id', reply_envelope->>'causationid'
            )::text
            FROM lifecycle_command_results WHERE command_event_id = %s::uuid
            """
            % sql_literal(event_id)
        )
        return json.loads(raw) if raw else None

    def outbox_rows(self) -> list[dict[str, Any]]:
        raw = self.psql(
            """
            SELECT COALESCE(json_agg(row_to_json(items)), '[]'::json)::text
            FROM (
              SELECT id, event_sequence, event_id::text, event_type, subject,
                     aggregate_version, published_at IS NOT NULL AS published,
                     envelope->>'causationid' AS causation_id,
                     envelope->'data'->>'verdict' AS verdict,
                     published_at, publish_attempts, next_attempt_at, error
              FROM lifecycle_event_outbox WHERE lifecycle_id = %s
              ORDER BY event_sequence
            ) AS items
            """
            % sql_literal(self.lifecycle_id)
        )
        return json.loads(raw)

    def publish(self, envelope: dict[str, Any]) -> None:
        self.docker(
            "run",
            "--rm",
            "--network",
            self.networks["bloodbank"],
            NATS_BOX_IMAGE,
            "nats",
            "--server=nats://nats:4222",
            "pub",
            str(envelope["subject"]),
            json.dumps(envelope, sort_keys=True, separators=(",", ":")),
        )

    def publish_jetstream(self, envelope: dict[str, Any]) -> dict[str, Any]:
        """Publish one canonical envelope and require the owning stream's ack."""

        program = """
import asyncio
import json
import os

import nats


async def main():
    envelope = json.loads(os.environ['BLOODBANK_ENVELOPE'])
    client = await nats.connect('nats://nats:4222')
    try:
        ack = await client.jetstream().publish(
            envelope['subject'],
            json.dumps(envelope, sort_keys=True, separators=(',', ':')).encode(),
            headers={'Nats-Msg-Id': envelope['id']},
        )
        print(json.dumps({
            'duplicate': bool(ack.duplicate),
            'event_id': envelope['id'],
            'stream': ack.stream,
            'stream_sequence': ack.seq,
            'subject': envelope['subject'],
        }, sort_keys=True))
    finally:
        await client.drain()


asyncio.run(main())
"""
        result = self.docker(
            "run",
            "--rm",
            "--network",
            self.networks["bloodbank"],
            "--env",
            "BLOODBANK_ENVELOPE="
            + json.dumps(envelope, sort_keys=True, separators=(",", ":")),
            "--entrypoint",
            "python",
            LIFECYCLE_IMAGE,
            "-c",
            program,
        )
        return json.loads(result.stdout)

    def stream_info(self, name: str) -> dict[str, Any]:
        result = self.docker(
            "run",
            "--rm",
            "--network",
            self.networks["bloodbank"],
            NATS_BOX_IMAGE,
            "nats",
            "--server=nats://nats:4222",
            "stream",
            "info",
            name,
            "--json",
        )
        return json.loads(result.stdout)

    def consumer_info(self, stream: str, consumer: str) -> dict[str, Any]:
        result = self.docker(
            "run",
            "--rm",
            "--network",
            self.networks["bloodbank"],
            NATS_BOX_IMAGE,
            "nats",
            "--server=nats://nats:4222",
            "consumer",
            "info",
            stream,
            consumer,
            "--json",
        )
        return json.loads(result.stdout)

    def start_momo_obligation_actor(
        self,
        *,
        workspace: Path,
        consumer: str,
    ) -> subprocess.Popen[bytes]:
        """Start the promoted durable Momo actor before invocation publication."""

        worker = SOURCE_ROOT / "skills" / "momo" / "scripts" / "obligation_worker.py"
        catalog = (
            SOURCE_ROOT
            / "skills"
            / "momo"
            / "resources"
            / "obligation-skill-catalog.json"
        )
        command = [
            "uv",
            "run",
            "--project",
            str(SOURCE_ROOT / "momo"),
            "python",
            str(worker),
            "--nats-url",
            f"nats://127.0.0.1:{self.ports['nats']}",
            "--stream",
            COMMAND_STREAM,
            "--consumer",
            consumer,
            "--expectation",
            str(workspace / "invocation-expectation.json"),
            "--catalog",
            str(catalog),
            "--resource-root",
            str(SOURCE_ROOT / "momo"),
            "--evidence-package",
            str(workspace / "evidence-package.json"),
            "--report",
            str(workspace / "review-report.md"),
            "--receipt",
            str(workspace / "worker-receipt.json"),
            "--ready-file",
            str(workspace / "worker-ready.json"),
            "--preview-file",
            str(workspace / "completion-preview.json"),
            "--release-file",
            str(workspace / "completion.release"),
            "--timeout",
            "120",
            "--release-timeout",
            "120",
        ]
        log_path = workspace / "worker.log"
        with log_path.open("wb") as log_handle:
            process = subprocess.Popen(
                command,
                cwd=SOURCE_ROOT,
                env=os.environ.copy(),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )
        self.momo_actor_process = process
        return process

    def container_status(self, service: str) -> str:
        container = self.compose("ps", "-a", "-q", service).stdout.strip()
        if not container:
            return "missing"
        return self.docker(
            "inspect", "--format", "{{.State.Status}}", container
        ).stdout.strip()

    def stream_messages_since(
        self, name: str, *, after_sequence: int
    ) -> list[dict[str, Any]]:
        """Read exact persisted JetStream envelopes after one stream sequence."""

        info = self.stream_info(name)
        last_sequence = int(info["state"].get("last_seq", 0))
        messages: list[dict[str, Any]] = []
        for sequence in range(after_sequence + 1, last_sequence + 1):
            message = self.stream_message(name, sequence, missing_ok=True)
            if message is not None:
                messages.append(message)
        return messages

    def stream_message(
        self,
        name: str,
        sequence: int,
        *,
        missing_ok: bool = False,
    ) -> dict[str, Any] | None:
        """Read one stream sequence, allowing WorkQueue-retention gaps."""

        result = self.docker(
            "run",
            "--rm",
            "--network",
            self.networks["bloodbank"],
            NATS_BOX_IMAGE,
            "nats",
            "--server=nats://nats:4222",
            "stream",
            "get",
            name,
            str(sequence),
            "--json",
            check=False,
        )
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()
            if missing_ok and "no message found (10037)" in detail:
                return None
            raise LiveProofError(
                f"could not read JetStream {name} sequence {sequence}: {detail[-2000:]}"
            )
        record = json.loads(result.stdout)
        encoded = record.get("data")
        if not isinstance(encoded, str):
            raise LiveProofError(
                f"JetStream {name} sequence {sequence} omitted encoded data"
            )
        try:
            envelope = json.loads(base64.b64decode(encoded, validate=True))
        except (ValueError, json.JSONDecodeError) as exc:
            raise LiveProofError(
                f"JetStream {name} sequence {sequence} is not a JSON envelope"
            ) from exc
        return {
            "stream": name,
            "stream_sequence": int(record.get("seq", sequence)),
            "subject": record.get("subject"),
            "event_id": envelope.get("id"),
            "event_type": envelope.get("type"),
            "kind": envelope.get("kind"),
            "stored_at": record.get("time"),
        }

    def wait_health(
        self, path: str, status: int, timeout: float = 60
    ) -> dict[str, Any]:
        url = f"http://127.0.0.1:{self.ports['lifecycle']}{path}"

        def probe():
            actual, body = http_json(url)
            return body if actual == status else None

        return wait_for(f"Lifecycle {path} HTTP {status}", probe, timeout=timeout)

    def wait_container_health(self, service: str, timeout: float = 60) -> str:
        def probe():
            container = self.compose("ps", "-q", service).stdout.strip()
            if not container:
                return None
            result = self.docker(
                "inspect",
                "--format",
                "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
                container,
            )
            return "healthy" if result.stdout.strip() == "healthy" else None

        return wait_for(f"{service} container health", probe, timeout=timeout)

    def wait_command(self, event_id: str, verdict: str) -> dict[str, Any]:
        result = wait_for(
            f"command {event_id} result",
            lambda: self.command_result(event_id),
        )
        if result.get("verdict") != verdict:
            raise LiveProofError(
                f"command {event_id} expected verdict {verdict!r}, got {result!r}"
            )
        return result

    def wait_state_version(
        self,
        minimum: int,
        status: str | None = None,
        *,
        timeout: float = 60,
    ) -> dict[str, Any]:
        return wait_for(
            f"Lifecycle state version >= {minimum}"
            + (f" status={status}" if status else ""),
            lambda: (
                value
                if (value := self.state())["state_version"] >= minimum
                and (status is None or value["status"] == status)
                else None
            ),
            timeout=timeout,
        )

    def command(
        self,
        label: str,
        *,
        expected_state_version: int,
        target: str,
        actor_id: str = ACTOR_ID,
        capability_id: str = CAPABILITY_ID,
        capability_version: int | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        intent_name: str = "transition",
        parameters: dict[str, Any] | None = None,
        requested_at: str | None = None,
    ) -> dict[str, Any]:
        requested_at = requested_at or wire_time()
        if capability_version is None:
            capability_version = self.capability_version()
        command_id = stable_uuid(f"{self.suffix}:command:{label}")
        if causation_id is not None and correlation_id is None:
            raise LiveProofError("derived commands must inherit parent correlation_id")
        if correlation_id is None:
            correlation_id = command_id
        return {
            "specversion": "1.0",
            "id": stable_uuid(f"{self.suffix}:event:{label}"),
            "source": "urn:33god:service:lifecycle-live-matrix",
            "type": "bloodbank.v1.lifecycle.intent.submit",
            "subject": "bloodbank.cmd.v1.lifecycle.intent.submit",
            "time": requested_at,
            "datacontenttype": "application/json",
            "dataschema": (
                "apicurio://holyfields/"
                "bloodbank.v1.lifecycle.intent.submit.command/versions/1"
            ),
            "correlationid": correlation_id,
            "causationid": causation_id,
            "producer": "lifecycle-live-matrix",
            "service": "lifecycle-live-matrix",
            "domain": "lifecycle",
            "schemaref": "bloodbank.v1.lifecycle.intent.submit.command.v1",
            "kind": "command",
            "actor": {"type": "agent_api", "agent_id": actor_id},
            "command_id": command_id,
            "idempotency_key": f"lifecycle-live-matrix:{self.suffix}:{label}",
            "delivery": "single_consumer",
            "data": {
                "contract_version": 1,
                "lifecycle_id": self.lifecycle_id,
                "repo": REPO,
                "expected_state_version": expected_state_version,
                "intent": {
                    "name": intent_name,
                    "target": target,
                    "parameters": parameters or {},
                },
                "capability": {
                    "capability_id": capability_id,
                    "capability_version": capability_version,
                    "action": "lifecycle.intent.submit",
                    "scope": f"lifecycle:{self.lifecycle_id}",
                    "issued_to": actor_id,
                },
                "requested_at": requested_at,
            },
        }

    def observation(self, label: str) -> dict[str, Any]:
        observed_at = wire_time()
        return {
            "specversion": "1.0",
            "id": stable_uuid(f"{self.suffix}:observation:{label}"),
            "source": "urn:33god:integration:lifecycle-live-matrix",
            "type": "bloodbank.v1.repo.task.recorded",
            "subject": "bloodbank.evt.v1.repo.task.recorded",
            "time": observed_at,
            "datacontenttype": "application/json",
            "dataschema": "apicurio://holyfields/bloodbank.v1.repo.task.recorded/versions/1",
            "correlationid": stable_uuid(
                f"{self.suffix}:observation-correlation:{label}"
            ),
            "causationid": None,
            "producer": "lifecycle-live-matrix",
            "service": "lifecycle-live-matrix",
            "domain": "repo",
            "schemaref": "bloodbank.v1.repo.task.recorded.v1",
            "kind": "event",
            "actor": {"type": "service", "agent_id": "lifecycle-live-matrix"},
            "ordering_key": f"task:{REPO}:AION-{self.suffix}",
            "data": {
                "repo": REPO,
                "task_id": f"AION-{self.suffix}",
                "title": "Lifecycle restart catch-up proof",
                "change_kind": "status",
                "from": "provider-backlog",
                "to": "provider-done",
                "updated_at": observed_at,
            },
        }

    def projection(self) -> dict[str, Any]:
        status, body = http_json(
            f"http://127.0.0.1:{self.ports['candystore']}/lifecycles/{self.lifecycle_id}"
        )
        if status != 200 or not isinstance(body, dict):
            raise LiveProofError(f"Candystore projection returned {status}: {body!r}")
        return body

    def wait_projection(
        self,
        *,
        minimum_version: int,
        status: str | None = None,
        command_id: str | None = None,
    ) -> dict[str, Any]:
        observed: dict[str, Any] | None = None

        def probe():
            nonlocal observed
            value = self.projection()
            observed = value
            if value.get("projection_status") != "current":
                return None
            if int(value.get("state_version") or 0) < minimum_version:
                return None
            if status is not None and value.get("status") != status:
                return None
            if command_id is not None and not any(
                item.get("command_id") == command_id
                for item in value.get("command_verdicts", [])
            ):
                return None
            return value

        try:
            return wait_for(
                "current Candystore Lifecycle projection", probe, timeout=90
            )
        except LiveProofError as exc:
            raise LiveProofError(f"{exc}; observed_projection={observed!r}") from exc

    def run_core_matrix(self) -> None:
        print("[live] starting pinned Lifecycle authority topology", flush=True)
        self.compose("up", "-d", "--wait", "--wait-timeout", "120", "lifecycle")
        ready = self.wait_health("/readyz", 200)
        live = self.wait_health("/livez", 200)
        if ready.get("status") != "ready" or live != {"status": "live"}:
            raise LiveProofError("Lifecycle health contracts did not return ready/live")
        initial = self.state()
        if initial["status"] != "active" or initial["state_version"] != 1:
            raise LiveProofError(f"unexpected deterministic bootstrap state: {initial}")
        capability_version = self.capability_version()

        running = set(
            self.compose("ps", "--services", "--status", "running").stdout.split()
        )
        if "holocene-web" in running or any(
            name.startswith("momo") for name in running
        ):
            raise LiveProofError("Holocene/Momo must be offline for independence proof")

        print(
            "[live] proving trusted pre-publication replay and offline progression",
            flush=True,
        )
        target_waiting_version = initial["state_version"] + 1
        occurrence_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                "lifecycle-obligation-occurrence:"
                f"{self.lifecycle_id}:independent-review:waiting:"
                f"{target_waiting_version}",
            )
        )
        claimed_completion = wire_time(120)
        prepublished_invocation_id = stable_uuid(
            f"{self.suffix}:prepublished-invocation"
        )
        prepublished_evidence = {
            "specversion": "1.0",
            "id": stable_uuid(f"{self.suffix}:evidence:prepublished"),
            "source": "urn:33god:service:momo",
            "type": "bloodbank.v1.lifecycle.obligation_evidence.submitted",
            "subject": "bloodbank.evt.v1.lifecycle.obligation_evidence.submitted",
            "time": claimed_completion,
            "datacontenttype": "application/json",
            "dataschema": (
                "apicurio://holyfields/"
                "bloodbank.v1.lifecycle.obligation_evidence.submitted/versions/2"
            ),
            "correlationid": stable_uuid(f"{self.suffix}:prepublished-correlation"),
            "causationid": prepublished_invocation_id,
            "producer": "momo",
            "service": "momo",
            "domain": "lifecycle",
            "schemaref": ("bloodbank.v1.lifecycle.obligation_evidence.submitted.v2"),
            "kind": "event",
            "actor": {"type": "service", "agent_id": "momo"},
            "ordering_key": f"lifecycle:{self.lifecycle_id}",
            "data": {
                "contract_version": 2,
                "lifecycle_id": self.lifecycle_id,
                "repo": REPO,
                "obligation_id": "independent-review",
                "obligation_instance_id": occurrence_id,
                "obligation_kind": "independent_review",
                "target_actor_id": "agent:independent-reviewer",
                "invocation_id": prepublished_invocation_id,
                "skill_ref": {"name": "bmad-code-review", "selector": "6.10.2"},
                "completed_at": claimed_completion,
                "evidence": {
                    "kind": "skill_completion",
                    "outcome": "completed",
                    "artifact_id": f"future-review:{self.suffix}",
                    "artifact_sha256": "f" * 64,
                    "summary": (
                        "Forged future completion published before activation."
                    ),
                },
            },
        }
        prepublished_ack = self.publish_jetstream(prepublished_evidence)
        if (
            prepublished_ack.get("stream") != "BLOODBANK_EVENTS"
            or prepublished_ack.get("event_id") != prepublished_evidence["id"]
            or prepublished_ack.get("subject") != prepublished_evidence["subject"]
            or not isinstance(prepublished_ack.get("stream_sequence"), int)
            or prepublished_ack["stream_sequence"] <= 0
            or prepublished_ack.get("duplicate") is not False
        ):
            raise LiveProofError(
                f"prepublished evidence lacked an exact JetStream ack: {prepublished_ack!r}"
            )
        prepublished_stream_row = next(
            (
                item
                for item in self.stream_messages_since(
                    "BLOODBANK_EVENTS",
                    after_sequence=int(prepublished_ack["stream_sequence"]) - 1,
                )
                if item["event_id"] == prepublished_evidence["id"]
            ),
            None,
        )
        if (
            prepublished_stream_row is None
            or prepublished_stream_row.get("stream") != prepublished_ack["stream"]
            or prepublished_stream_row.get("stream_sequence")
            != prepublished_ack["stream_sequence"]
            or prepublished_stream_row.get("subject")
            != prepublished_evidence["subject"]
            or not isinstance(prepublished_stream_row.get("stored_at"), str)
        ):
            raise LiveProofError(
                "prepublished evidence has no immutable JetStream storage timestamp"
            )
        trusted_publication = datetime.fromisoformat(
            prepublished_stream_row["stored_at"].replace("Z", "+00:00")
        )
        claimed_completion_value = datetime.fromisoformat(
            claimed_completion.replace("Z", "+00:00")
        )

        def prepublished_observation_row() -> dict[str, Any] | None:
            raw = self.psql(
                "SELECT json_build_object("
                "'received_at', received_at, 'observed_at', observed_at, "
                "'source_event_id', source_event_id::text)::text "
                "FROM lifecycle_observations "
                f"WHERE source_event_id = {sql_literal(prepublished_evidence['id'])}::uuid"
            )
            return json.loads(raw) if raw else None

        persisted_prepublication = wait_for(
            "canonical pre-WAITING observation persistence",
            prepublished_observation_row,
            timeout=90,
        )
        persisted_received_at = datetime.fromisoformat(
            persisted_prepublication["received_at"].replace("Z", "+00:00")
        )
        persisted_observed_at = datetime.fromisoformat(
            persisted_prepublication["observed_at"].replace("Z", "+00:00")
        )
        preactivation = wait_for(
            "pre-WAITING evidence reconciliation",
            lambda: (
                current
                if (current := self.state())["state_version"]
                == initial["state_version"]
                and current["status"] == "active"
                and self.reconcile_queue_depth() == 0
                and self.counts()["outbox_pending"] == 0
                else None
            ),
            timeout=120,
        )
        preactivation_authority_time = datetime.fromisoformat(
            preactivation["last_reconciled_at"].replace("Z", "+00:00")
        )
        activation = wire_time()
        activation_value = datetime.fromisoformat(activation.replace("Z", "+00:00"))
        if (
            persisted_prepublication["source_event_id"] != prepublished_evidence["id"]
            or persisted_observed_at != claimed_completion_value
            or not (
                preactivation_authority_time
                <= trusted_publication
                < activation_value
                < claimed_completion_value
                and persisted_received_at < activation_value
            )
        ):
            raise LiveProofError(
                "prepublication chronology was not immutable storage <= canonical "
                "receipt < activation < claimed completion"
            )

        first = self.command(
            "clients-offline",
            expected_state_version=preactivation["state_version"],
            target="waiting",
            requested_at=activation,
        )
        self.publish(first)
        first_result = self.wait_command(first["id"], "applied")
        first_waiting = self.wait_state_version(target_waiting_version, "waiting")
        obligation = next(
            (
                item
                for item in first_waiting.get("obligations", [])
                if item.get("id") == "independent-review"
            ),
            None,
        )
        waiting_frontier = next(
            (
                item
                for item in first_waiting.get("legal_frontier", [])
                if item.get("id") == "transition:waiting:active"
            ),
            None,
        )
        if (
            first_waiting.get("state_version") != target_waiting_version
            or obligation is None
            or obligation.get("status") != "pending"
            or waiting_frontier is None
            or waiting_frontier.get("allowed") is not False
            or waiting_frontier.get("reason_code") != "PENDING_OBLIGATIONS"
        ):
            raise LiveProofError(
                "first WAITING authority snapshot did not expose the pending "
                "obligation and disallowed frontier"
            )
        progressed = wait_for(
            "prepublished evidence replay rejection",
            lambda: (
                current
                if (current := self.state())["state_version"]
                == first_waiting["state_version"]
                and current["status"] == "waiting"
                and next(
                    item
                    for item in current["obligations"]
                    if item["id"] == "independent-review"
                )["status"]
                == "pending"
                and self.reconcile_queue_depth() == 0
                and self.counts()["outbox_pending"] == 0
                else None
            ),
            timeout=120,
        )
        obligation = next(
            item
            for item in progressed["obligations"]
            if item["id"] == "independent-review"
        )
        waiting_frontier = next(
            item
            for item in progressed["legal_frontier"]
            if item["id"] == "transition:waiting:active"
        )
        occurrence_activation = datetime.fromisoformat(
            obligation["activated_at"].replace("Z", "+00:00")
        )
        if (
            persisted_prepublication["source_event_id"] != prepublished_evidence["id"]
            or obligation["obligation_instance_id"] != occurrence_id
            or obligation["status"] != "pending"
            or waiting_frontier["allowed"] is not False
            or waiting_frontier["reason_code"] != "PENDING_OBLIGATIONS"
            or not (
                trusted_publication < occurrence_activation < claimed_completion_value
                and persisted_received_at < occurrence_activation
            )
        ):
            raise LiveProofError(
                "trusted prepublication replay satisfied or changed the active occurrence"
            )
        self.summary["invariants"]["1_holocene_offline"] = {
            "running_services": sorted(running),
            "result": first_result,
            "state": progressed,
        }
        self.summary["invariants"]["2_momo_offline"] = {
            "running_services": sorted(running),
            "state_version": progressed["state_version"],
            "status": progressed["status"],
        }
        self.summary["invariants"]["trusted_prepublication_replay"] = {
            "event_id": prepublished_evidence["id"],
            "invocation_id": prepublished_invocation_id,
            "causation_id": prepublished_evidence["causationid"],
            "correlation_id": prepublished_evidence["correlationid"],
            "ordering_key": prepublished_evidence["ordering_key"],
            "jetstream_ack": prepublished_ack,
            "stream_record": prepublished_stream_row,
            "trusted_publication_at": prepublished_stream_row["stored_at"],
            "observation_received_at": persisted_prepublication["received_at"],
            "observation_observed_at": persisted_prepublication["observed_at"],
            "observation_existed_before_waiting": True,
            "occurrence_activated_at": obligation["activated_at"],
            "claimed_completed_at": claimed_completion,
            "obligation_instance_id": occurrence_id,
            "preactivation_authority_time": preactivation["last_reconciled_at"],
            "preactivation_state_version": preactivation["state_version"],
            "first_waiting_state_version": first_waiting["state_version"],
            "post_activation_state_version": progressed["state_version"],
            "status_after_replay": obligation["status"],
        }

        print("[live] proving pending-obligation progression rejection", flush=True)
        pending_before = self.counts()
        premature = self.command(
            "pending-obligation-reject",
            expected_state_version=progressed["state_version"],
            target="active",
            correlation_id=first["correlationid"],
            causation_id=first["id"],
        )
        self.publish(premature)
        premature_result = self.wait_command(premature["id"], "illegal")
        pending_after = self.state()
        if (
            premature_result["mutated"]
            or premature_result["reason_code"] != "PENDING_OBLIGATIONS"
            or pending_after["state_version"] != progressed["state_version"]
            or pending_after["status"] != "waiting"
            or self.counts()["history"] != pending_before["history"]
        ):
            raise LiveProofError("pending obligation did not fail closed")
        self.summary["invariants"]["authority_obligation_guard"] = {
            "obligation": obligation,
            "frontier": waiting_frontier,
            "result": premature_result,
            "state_version": pending_after["state_version"],
            "history_count": pending_before["history"],
            "capability_version": capability_version,
        }

        print(
            "[live] proving stale version and invalid capability rejection", flush=True
        )
        stale_before = self.counts()
        stale = self.command("stale", expected_state_version=1, target="active")
        self.publish(stale)
        stale_result = self.wait_command(stale["id"], "stale")
        after_stale = self.state()
        if (
            stale_result["mutated"]
            or after_stale["state_version"] != progressed["state_version"]
        ):
            raise LiveProofError("stale expected_state_version mutated authority state")
        if self.counts()["history"] != stale_before["history"]:
            raise LiveProofError(
                "stale expected_state_version appended transition history"
            )
        self.summary["invariants"]["4_stale_expected_version"] = {
            "result": stale_result,
            "state_version": after_stale["state_version"],
            "history_count": stale_before["history"],
            "capability_version": capability_version,
        }

        unauthorized_before = self.counts()
        unauthorized = self.command(
            "unauthorized",
            expected_state_version=progressed["state_version"],
            target="active",
            actor_id="agent:intruder",
            capability_id="cap:missing",
            capability_version=capability_version,
        )
        self.publish(unauthorized)
        unauthorized_result = self.wait_command(unauthorized["id"], "unauthorized")
        after_unauthorized = self.state()
        if (
            unauthorized_result["mutated"]
            or after_unauthorized["state_version"] != progressed["state_version"]
        ):
            raise LiveProofError("invalid capability mutated authority state")
        if self.counts()["history"] != unauthorized_before["history"]:
            raise LiveProofError("invalid capability appended transition history")
        self.summary["invariants"]["5_invalid_capability"] = {
            "result": unauthorized_result,
            "state_version": after_unauthorized["state_version"],
            "history_count": unauthorized_before["history"],
            "submitted_capability_version": capability_version,
        }

        print(
            "[live] proving durable observation catch-up and restart deduplication",
            flush=True,
        )
        observation_before = self.counts()
        self.compose("stop", "lifecycle")
        observation = self.observation("restart-catchup")
        self.publish(observation)
        self.publish(observation)
        self.compose("start", "lifecycle")
        self.wait_health("/readyz", 200)
        wait_for(
            "one idempotent observation after duplicate delivery",
            lambda: (
                value
                if (value := self.counts())["observations"]
                == observation_before["observations"] + 1
                and value["outbox_pending"] == 0
                else None
            ),
            timeout=90,
        )
        time.sleep(1)
        catchup_state = self.state()
        catchup_counts = self.counts()
        self.compose("restart", "lifecycle")
        self.wait_health("/readyz", 200)
        time.sleep(1)
        restart_state = self.state()
        restart_counts = self.counts()
        if restart_state != catchup_state or restart_counts != catchup_counts:
            raise LiveProofError(
                "Lifecycle restart duplicated committed observation effects"
            )
        self.summary["invariants"]["3_restart_catchup"] = {
            "source_event_id": observation["id"],
            "state": restart_state,
            "counts": restart_counts,
            "duplicate_deliveries": 2,
            "durable_observations": 1,
        }

        print(
            "[live] proving real single-writer NATS outage commit and redelivery",
            flush=True,
        )
        outage_before_state = self.state()
        outage_before_counts = self.counts()
        if outage_before_counts["outbox_pending"] != 0:
            raise LiveProofError("outage proof requires an initially drained outbox")
        outage_before_rows = self.outbox_rows()
        before_event_ids = {item["event_id"] for item in outage_before_rows}
        event_stream_before = self.stream_info("BLOODBANK_EVENTS")["state"]
        command_stream_before = self.stream_info(COMMAND_STREAM)["state"]
        command_consumer_before = self.consumer_info(
            COMMAND_STREAM, COMMAND_CONSUMER
        )
        event_last_before = int(event_stream_before.get("last_seq", 0))
        command_last_before = int(command_stream_before.get("last_seq", 0))
        deployed_lifecycle_container = self.compose("ps", "-q", "lifecycle").stdout.strip()
        if not deployed_lifecycle_container:
            raise LiveProofError("deployed Lifecycle Compose container is missing")
        mode_frontier = next(
            (
                item
                for item in outage_before_state["legal_frontier"]
                if item["id"] == "mode:manual" and item["allowed"]
            ),
            None,
        )
        if mode_frontier is None:
            raise LiveProofError("authority exposed no legal set_mode transaction")
        target_mode = mode_frontier["id"].split(":", 1)[1]
        outage_command = self.command(
            "nats-outage-authority-commit",
            expected_state_version=outage_before_state["state_version"],
            target=target_mode,
            intent_name="set_mode",
        )

        lock_holder_activity: dict[str, Any]
        blocked_writer_activity: dict[str, Any]
        blocked_consumer_info: dict[str, Any]
        outage_publish_ack: dict[str, Any]
        nats_down_status: str
        lifecycle_stopped_status: str
        try:
            self.start_lifecycle_row_lock()
            lock_holder_activity = self.wait_lifecycle_row_lock()
            outage_publish_ack = self.publish_jetstream(outage_command)
            if (
                outage_publish_ack.get("stream") != COMMAND_STREAM
                or outage_publish_ack.get("subject") != outage_command["subject"]
                or outage_publish_ack.get("event_id") != outage_command["id"]
                or outage_publish_ack.get("duplicate") is not False
            ):
                raise LiveProofError(
                    f"canonical outage command publish was not unique: {outage_publish_ack}"
                )
            blocked_consumer_info = wait_for(
                f"{COMMAND_CONSUMER} ack-pending delivery",
                lambda: (
                    value
                    if int(
                        (value := self.consumer_info(
                            COMMAND_STREAM, COMMAND_CONSUMER
                        )).get("num_ack_pending", 0)
                    )
                    >= 1
                    and int(value.get("delivered", {}).get("stream_seq", 0))
                    >= int(outage_publish_ack["stream_sequence"])
                    else None
                ),
                timeout=30,
            )
            blocked_writer_activity = self.wait_blocked_lifecycle_writer()

            self.compose("stop", "bloodbank-nats")
            nats_down_status = wait_for(
                "isolated NATS container to stop",
                lambda: (
                    status
                    if (status := self.container_status("bloodbank-nats"))
                    == "exited"
                    else None
                ),
                timeout=30,
            )
            degraded = self.wait_health("/readyz", 503)
            still_live = self.wait_health("/livez", 200)
            if self.state() != outage_before_state:
                raise LiveProofError(
                    "blocked deployed writer changed Lifecycle state before lock release"
                )
            if self.counts()["history"] != outage_before_counts["history"]:
                raise LiveProofError(
                    "blocked deployed writer appended history before lock release"
                )

            self.release_lifecycle_row_lock()
            outage_result = self.wait_command(outage_command["id"], "applied")

            # Discard the disconnected client's buffered ACK. Starting this same
            # Compose container after NATS recovery forces durable redelivery.
            self.compose("stop", "--timeout", "5", "lifecycle")
            lifecycle_stopped_status = wait_for(
                "deployed Lifecycle container to stop after its database commit",
                lambda: (
                    status
                    if (status := self.container_status("lifecycle")) == "exited"
                    else None
                ),
                timeout=30,
            )
        finally:
            self.release_lifecycle_row_lock(check=False)

        outage_committed_state = self.state()
        outage_committed_counts = self.counts()
        if (
            outage_result["verdict"] != "applied"
            or outage_result["mutated"] is not True
            or outage_committed_state["state_version"]
            != outage_before_state["state_version"] + 1
            or outage_committed_state["mode"] != target_mode
            or outage_committed_state["status"] != "waiting"
            or outage_committed_counts["history"]
            != outage_before_counts["history"] + 1
            or outage_committed_counts["commands"]
            != outage_before_counts["commands"] + 1
        ):
            raise LiveProofError(
                "deployed Lifecycle transaction did not commit exactly once while NATS was down"
            )
        before_obligation = next(
            item
            for item in outage_before_state["obligations"]
            if item["id"] == "independent-review"
        )
        committed_obligation = next(
            item
            for item in outage_committed_state["obligations"]
            if item["id"] == "independent-review"
        )
        if (
            committed_obligation["obligation_instance_id"]
            != before_obligation["obligation_instance_id"]
            or committed_obligation["activated_at"] != before_obligation["activated_at"]
        ):
            raise LiveProofError(
                "unrelated outage transaction changed the active obligation occurrence"
            )

        outage_rows_during = [
            item
            for item in self.outbox_rows()
            if item["event_id"] not in before_event_ids
        ]
        pending_event_ids = [item["event_id"] for item in outage_rows_during]
        pending_sequences = [
            int(item["event_sequence"]) for item in outage_rows_during
        ]
        if (
            len(outage_rows_during) < 2
            or outage_result["applied_event_id"] not in pending_event_ids
            or outage_result["reply_event_id"] not in pending_event_ids
            or any(item["published"] for item in outage_rows_during)
            or pending_sequences != sorted(set(pending_sequences))
            or outage_committed_counts["outbox"]
            != outage_before_counts["outbox"] + len(outage_rows_during)
            or outage_committed_counts["outbox_pending"] != len(outage_rows_during)
        ):
            raise LiveProofError(
                "database commit while NATS was down did not retain exact ordered pending outbox rows"
            )

        recovery_guard_activity: dict[str, Any]
        nats_restarted_consumer: dict[str, Any]
        recovered_consumer_info: dict[str, Any]
        try:
            # A non-mutating table lock keeps the service's immediate startup
            # sweep from changing state while redelivery idempotency is measured.
            self.start_lifecycle_recovery_guard()
            recovery_guard_activity = self.wait_lifecycle_recovery_guard()

            self.compose("start", "bloodbank-nats")
            self.wait_container_health("bloodbank-nats")
            nats_restarted_consumer = wait_for(
                "persisted ack-pending delivery after NATS restart",
                lambda: (
                    value
                    if int(
                        (value := self.consumer_info(
                            COMMAND_STREAM, COMMAND_CONSUMER
                        )).get("num_ack_pending", 0)
                    )
                    >= 1
                    else None
                ),
                timeout=30,
            )
            event_stream_before_recovery = self.stream_info("BLOODBANK_EVENTS")[
                "state"
            ]
            command_stream_before_recovery = self.stream_info(COMMAND_STREAM)[
                "state"
            ]
            if (
                int(event_stream_before_recovery["messages"])
                != int(event_stream_before["messages"])
                or int(command_stream_before_recovery["messages"])
                != int(command_stream_before["messages"]) + 1
            ):
                raise LiveProofError(
                    "outbox publication occurred before the deployed Lifecycle service recovered"
                )
            persisted_outage_command = self.stream_message(
                COMMAND_STREAM, int(outage_publish_ack["stream_sequence"])
            )
            if (
                persisted_outage_command is None
                or persisted_outage_command["event_id"] != outage_command["id"]
                or persisted_outage_command["subject"] != outage_command["subject"]
            ):
                raise LiveProofError(
                    "canonical outage command was not persisted at its acknowledged sequence"
                )

            self.compose("start", "lifecycle")
            recovered_lifecycle_container = self.compose(
                "ps", "-q", "lifecycle"
            ).stdout.strip()
            if recovered_lifecycle_container != deployed_lifecycle_container:
                raise LiveProofError(
                    "Lifecycle recovery replaced the deployed Compose container"
                )
            recovered = self.wait_health("/readyz", 200, timeout=90)
            blocked_delivery_sequence = int(
                blocked_consumer_info.get("delivered", {}).get("consumer_seq", 0)
            )
            recovered_consumer_info = wait_for(
                f"{COMMAND_CONSUMER} durable redelivery acknowledgement",
                lambda: (
                    value
                    if int(
                        (value := self.consumer_info(
                            COMMAND_STREAM, COMMAND_CONSUMER
                        )).get("num_ack_pending", 0)
                    )
                    == 0
                    and int(value.get("delivered", {}).get("consumer_seq", 0))
                    > blocked_delivery_sequence
                    else None
                ),
                timeout=120,
            )
            command_removed_after_ack = wait_for(
                "acked outage command WorkQueue retention",
                lambda: (
                    True
                    if self.stream_message(
                        COMMAND_STREAM,
                        int(outage_publish_ack["stream_sequence"]),
                        missing_ok=True,
                    )
                    is None
                    else None
                ),
                timeout=30,
            )

            def recovered_outage_rows() -> list[dict[str, Any]] | None:
                matching = [
                    item
                    for item in self.outbox_rows()
                    if item["event_id"] not in before_event_ids
                ]
                idempotent = [
                    item
                    for item in matching
                    if item["verdict"] == "idempotent"
                    and item["causation_id"] == outage_command["id"]
                ]
                if (
                    len(matching) == len(outage_rows_during) + 1
                    and len(idempotent) == 1
                    and all(item["published"] for item in matching)
                ):
                    return matching
                return None

            outage_rows_after = wait_for(
                "outage outbox drain plus one idempotent redelivery reply",
                recovered_outage_rows,
                timeout=120,
            )
            recovered_state = self.state()
            recovered_counts = self.counts()
            recovered_result = self.command_result(outage_command["id"])
            if (
                recovered_state != outage_committed_state
                or recovered_counts["history"]
                != outage_committed_counts["history"]
                or recovered_counts["commands"]
                != outage_committed_counts["commands"]
                or recovered_counts["observations"]
                != outage_committed_counts["observations"]
                or recovered_counts["outbox"]
                != outage_committed_counts["outbox"] + 1
                or recovered_counts["outbox_pending"] != 0
                or recovered_result != outage_result
            ):
                raise LiveProofError(
                    "durable command redelivery duplicated authoritative state, history, or command results"
                )

            outage_event_ids = [item["event_id"] for item in outage_rows_after]
            event_messages = self.stream_messages_since(
                "BLOODBANK_EVENTS", after_sequence=event_last_before
            )
            command_messages = self.stream_messages_since(
                COMMAND_STREAM, after_sequence=command_last_before
            )
            recovered_messages = [*event_messages, *command_messages]
            exact_stream_rows = [
                message
                for message in recovered_messages
                if message["event_id"] in set(outage_event_ids)
            ]
            stream_counts = {
                event_id: sum(
                    message["event_id"] == event_id for message in exact_stream_rows
                )
                for event_id in outage_event_ids
            }
            if any(count != 1 for count in stream_counts.values()):
                raise LiveProofError(
                    f"recovered JetStream did not persist exact outbox IDs once: {stream_counts}"
                )

            recovered_by_id = {item["event_id"]: item for item in outage_rows_after}
            published_times = [
                recovered_by_id[event_id]["published_at"]
                for event_id in outage_event_ids
            ]
            if published_times != sorted(published_times):
                raise LiveProofError(
                    "per-lifecycle outage outbox rows published out of sequence"
                )
            for stream_name in ("BLOODBANK_EVENTS", COMMAND_STREAM):
                stream_rows = sorted(
                    (
                        message
                        for message in exact_stream_rows
                        if message["stream"] == stream_name
                    ),
                    key=lambda item: item["stream_sequence"],
                )
                stream_outbox_sequences = [
                    int(recovered_by_id[item["event_id"]]["event_sequence"])
                    for item in stream_rows
                ]
                if stream_outbox_sequences != sorted(stream_outbox_sequences):
                    raise LiveProofError(
                        f"{stream_name} reordered per-lifecycle outage publications"
                    )

            rows = self.outbox_rows()
            sequences = [int(item["event_sequence"]) for item in rows]
            if sequences != sorted(set(sequences)) or not all(
                item["published"] for item in rows
            ):
                raise LiveProofError(
                    "outbox ordering/uniqueness/eventual publication failed"
                )
            events_after = int(
                self.stream_info("BLOODBANK_EVENTS")["state"]["messages"]
            )
            commands_after = int(
                self.stream_info(COMMAND_STREAM)["state"]["messages"]
            )
            self.summary["invariants"]["6_nats_outage_recovery"] = {
                "deployed_lifecycle_container": deployed_lifecycle_container,
                "lock_holder": lock_holder_activity,
                "blocked_writer": blocked_writer_activity,
                "consumer_before": command_consumer_before,
                "consumer_blocked": blocked_consumer_info,
                "consumer_after_nats_restart": nats_restarted_consumer,
                "consumer_after_redelivery": recovered_consumer_info,
                "command_publish_ack": outage_publish_ack,
                "persisted_command_before_redelivery": persisted_outage_command,
                "command_removed_after_ack": command_removed_after_ack,
                "nats_status_during_outage": nats_down_status,
                "lifecycle_status_after_commit": lifecycle_stopped_status,
                "recovery_guard": recovery_guard_activity,
                "ready_during_outage": degraded,
                "live_during_outage": still_live,
                "ready_after_recovery": recovered,
                "committed_state_before": outage_before_state,
                "authority_command_event_id": outage_command["id"],
                "authority_command_id": outage_command["command_id"],
                "result_during_outage": outage_result,
                "state_during_outage": outage_committed_state,
                "counts_before": outage_before_counts,
                "counts_during_outage": outage_committed_counts,
                "counts_after_redelivery": recovered_counts,
                "pending_outbox_during_outage": outage_rows_during,
                "recovered_outbox_rows": outage_rows_after,
                "recovered_stream_messages": exact_stream_rows,
                "stream_id_counts": stream_counts,
                "event_messages_before": int(event_stream_before["messages"]),
                "event_messages_before_recovery": int(
                    event_stream_before_recovery["messages"]
                ),
                "event_messages_after": events_after,
                "command_reply_messages_before": int(
                    command_stream_before["messages"]
                ),
                "command_reply_messages_before_recovery": int(
                    command_stream_before_recovery["messages"]
                ),
                "command_reply_messages_after": commands_after,
                "outbox_sequences": sequences,
                "outbox_pending": 0,
            }
        finally:
            self.release_lifecycle_recovery_guard(check=False)

        print("[live] settling the post-command deterministic reconcile", flush=True)
        # The same deployed container was already restarted for durable
        # redelivery. Releasing the recovery guard unblocks its startup sweep;
        # another restart here could strand a just-claimed reconcile lease.
        self.wait_health("/readyz", 200)
        settled_state = self.wait_state_version(
            outage_committed_state["state_version"] + 1,
            "waiting",
            timeout=120,
        )
        wait_for(
            "settled post-command reconcile queue/outbox",
            lambda: (
                True
                if self.reconcile_queue_depth() == 0
                and self.counts()["outbox_pending"] == 0
                else None
            ),
            timeout=120,
        )
        settled_obligation = next(
            item
            for item in settled_state["obligations"]
            if item["id"] == "independent-review"
        )
        if (
            settled_state["mode"] != "manual"
            or settled_obligation["status"] != "pending"
            or settled_obligation["obligation_instance_id"]
            != committed_obligation["obligation_instance_id"]
            or settled_obligation["activated_at"]
            != committed_obligation["activated_at"]
        ):
            raise LiveProofError(
                "deterministic post-command reconcile changed the obligation occurrence"
            )

        print(
            "[live] proving dedicated PostgreSQL volume/process persistence", flush=True
        )
        persistent_state = self.state()
        persistent_counts = self.counts()
        postgres_container = self.compose(
            "ps", "-q", "lifecycle-postgres"
        ).stdout.strip()
        mount_format = (
            '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}'
            "{{.Name}}{{end}}{{end}}"
        )
        volume_before = self.docker(
            "inspect", "--format", mount_format, postgres_container
        ).stdout.strip()
        self.compose("stop", "lifecycle", "lifecycle-postgres")
        self.compose("start", "lifecycle-postgres")
        self.wait_container_health("lifecycle-postgres")
        self.compose("start", "lifecycle")
        self.wait_health("/readyz", 200)
        wait_for(
            "empty persistence-restart reconcile queue/outbox",
            lambda: (
                True
                if self.reconcile_queue_depth() == 0
                and self.counts()["outbox_pending"] == 0
                else None
            ),
        )
        time.sleep(1)
        volume_after = self.docker(
            "inspect", "--format", mount_format, postgres_container
        ).stdout.strip()
        if volume_before != self.volumes["lifecycle"] or volume_after != volume_before:
            raise LiveProofError(
                "Lifecycle PostgreSQL did not retain its dedicated volume"
            )
        persisted_state_after = self.state()
        persisted_counts_after = self.counts()
        if (
            persisted_state_after != persistent_state
            or persisted_counts_after != persistent_counts
        ):
            raise LiveProofError(
                "state did not survive service/PostgreSQL process restart: "
                f"state_before={persistent_state!r} state_after={persisted_state_after!r} "
                f"counts_before={persistent_counts!r} counts_after={persisted_counts_after!r}"
            )
        self.summary["invariants"]["7_postgres_persistence"] = {
            "volume": volume_after,
            "state": persistent_state,
            "counts": persistent_counts,
            "settled_from_state_version": outage_committed_state["state_version"],
        }

        print(
            "[live] enabling autonomous progression for completion evidence",
            flush=True,
        )
        wait_for(
            "settled autonomous-mode command frontier",
            lambda: (
                True
                if self.reconcile_queue_depth() == 0
                and self.counts()["outbox_pending"] == 0
                else None
            ),
        )
        autonomous_before = self.state()
        autonomous_frontier = next(
            (
                item
                for item in autonomous_before["legal_frontier"]
                if item["id"] == "mode:autonomous" and item["allowed"]
            ),
            None,
        )
        if (
            autonomous_frontier is None
            or autonomous_frontier["expected_state_version"]
            != autonomous_before["state_version"]
        ):
            raise LiveProofError(
                "authority exposed no current legal autonomous-mode frontier"
            )
        autonomous_command = self.command(
            "autonomous-after-persistence",
            expected_state_version=autonomous_frontier["expected_state_version"],
            target="autonomous",
            intent_name="set_mode",
        )
        self.publish(autonomous_command)
        autonomous_result = self.wait_command(autonomous_command["id"], "applied")
        if (
            autonomous_result["mutated"] is not True
            or autonomous_result["command_event_id"] != autonomous_command["id"]
            or autonomous_result["command_id"] != autonomous_command["command_id"]
            or autonomous_result["reply_subject"]
            != "bloodbank.rpy.v1.lifecycle.intent.submit"
            or autonomous_result["reply_correlation_id"]
            != autonomous_command["correlationid"]
            or autonomous_result["reply_causation_id"] != autonomous_command["id"]
        ):
            raise LiveProofError(
                "Bloodbank autonomous-mode transaction lost authority identity: "
                f"result={autonomous_result!r} state={self.state()!r}"
            )
        autonomous_state = self.wait_state_version(
            autonomous_before["state_version"] + 1, "waiting"
        )
        persistent_obligation = next(
            item
            for item in autonomous_before["obligations"]
            if item["id"] == "independent-review"
        )
        autonomous_obligation = next(
            item
            for item in autonomous_state["obligations"]
            if item["id"] == "independent-review"
        )
        if (
            autonomous_state["mode"] != "autonomous"
            or autonomous_obligation["status"] != "pending"
            or autonomous_obligation["obligation_instance_id"]
            != persistent_obligation["obligation_instance_id"]
            or autonomous_obligation["activated_at"]
            != persistent_obligation["activated_at"]
        ):
            raise LiveProofError(
                "mode change altered the guarded obligation occurrence"
            )
        wait_for(
            "drained autonomous-mode outbox",
            lambda: self.counts()["outbox_pending"] == 0,
        )
        self.summary["invariants"]["authority_progression_mode"] = {
            "command_event_id": autonomous_command["id"],
            "command_id": autonomous_command["command_id"],
            "command_subject": autonomous_command["subject"],
            "command_correlation_id": autonomous_command["correlationid"],
            "command_causation_id": autonomous_command["causationid"],
            "reply_event_id": autonomous_result["reply_event_id"],
            "reply_subject": autonomous_result["reply_subject"],
            "reply_correlation_id": autonomous_result["reply_correlation_id"],
            "reply_causation_id": autonomous_result["reply_causation_id"],
            "result": autonomous_result,
            "state": autonomous_state,
        }

        self.prestart_verdict_command_id = premature["command_id"]

    def run_clients(self) -> None:
        print(
            "[live] creating the stopped late-subscriber topology",
            flush=True,
        )
        self.compose(
            "create",
            "--build",
            "candystore-postgres",
            "dapr-placement",
            "candystore",
            "candystore-daprd",
            timeout=300,
        )
        candystore_containers = {
            service: self.compose("ps", "-q", "--all", service).stdout.strip()
            for service in (
                "candystore-postgres",
                "dapr-placement",
                "candystore",
                "candystore-daprd",
            )
        }
        if any(not container for container in candystore_containers.values()):
            raise LiveProofError(
                "Candystore late-subscriber containers were not created exactly: "
                f"{candystore_containers!r}"
            )
        created_statuses = {
            service: self.docker(
                "inspect", "--format", "{{.State.Status}}", container
            ).stdout.strip()
            for service, container in candystore_containers.items()
        }
        if any(
            status not in {"created", "exited"} for status in created_statuses.values()
        ):
            raise LiveProofError(
                "Candystore durable subscriber started before the replay cutoff: "
                f"{created_statuses!r}"
            )

        self.wait_health("/readyz", 200)
        wait_for(
            "drained pre-Candystore authority reconcile/outbox",
            lambda: (
                True
                if self.reconcile_queue_depth() == 0
                and self.counts()["outbox_pending"] == 0
                else None
            ),
        )
        authority = self.state()
        snapshots = [
            item
            for item in self.outbox_rows()
            if item["subject"] == "bloodbank.evt.v1.lifecycle.snapshot.updated"
        ]
        if not snapshots:
            raise LiveProofError("authority emitted no pre-Candystore snapshot")
        self.prestart_snapshot_event_id = snapshots[-1]["event_id"]
        self.compose("stop", "lifecycle")
        running = set(
            self.compose("ps", "--services", "--status", "running").stdout.split()
        )
        if "lifecycle" in running:
            raise LiveProofError("Lifecycle did not stop at the replay cutoff")

        print("[live] starting durable Candystore projection", flush=True)
        self.docker(
            "start",
            candystore_containers["candystore-postgres"],
            candystore_containers["dapr-placement"],
        )
        self.wait_container_health("candystore-postgres")
        self.docker("start", candystore_containers["candystore"])
        self.wait_container_health("candystore", timeout=180)
        self.docker("start", candystore_containers["candystore-daprd"])
        running = set(
            self.compose("ps", "--services", "--status", "running").stdout.split()
        )
        if "lifecycle" in running:
            raise LiveProofError(
                "late-subscriber setup restarted Lifecycle before replay proof"
            )
        if authority["status"] != "waiting":
            raise LiveProofError(
                "late-subscriber proof requires the guarded pre-existing waiting state; "
                f"observed={authority!r}"
            )
        if (
            self.prestart_snapshot_event_id is None
            or self.prestart_verdict_command_id is None
        ):
            raise LiveProofError("pre-Candystore replay identities were not recorded")
        projection = self.wait_projection(
            minimum_version=authority["state_version"],
            status=authority["status"],
            command_id=self.prestart_verdict_command_id,
        )
        if (
            projection.get("source", {}).get("event_id")
            != self.prestart_snapshot_event_id
        ):
            raise LiveProofError(
                "late-starting Candystore did not replay the exact pre-existing "
                "authority snapshot: "
                f"expected={self.prestart_snapshot_event_id!r} "
                f"actual={projection.get('source', {}).get('event_id')!r}"
            )
        projection_source = projection["source"]
        expected_source_identity = {
            "event_type": "bloodbank.v1.lifecycle.snapshot.updated",
            "subject": "bloodbank.evt.v1.lifecycle.snapshot.updated",
            "authority_source": "urn:33god:service:lifecycle",
            "producer": "delorenj/lifecycle",
            "service": "lifecycle",
            "kind": "event",
            "domain": "lifecycle",
            "schema_ref": "bloodbank.v1.lifecycle.snapshot.updated.v3",
            "data_schema": (
                "apicurio://holyfields/"
                "bloodbank.v1.lifecycle.snapshot.updated/versions/3"
            ),
        }
        if (
            any(
                projection_source.get(key) != value
                for key, value in expected_source_identity.items()
            )
            or projection_source.get("actor", {}).get("agent_id")
            != "delorenj.lifecycle"
            or not projection_source.get("correlation_id")
            or not projection_source.get("causation_id")
        ):
            raise LiveProofError(
                "Candystore replay lost exact Lifecycle authority/causal metadata"
            )
        replay_verdict = next(
            item
            for item in projection["command_verdicts"]
            if item["command_id"] == self.prestart_verdict_command_id
        )
        if replay_verdict["verdict"] != "illegal" or replay_verdict["mutated"]:
            raise LiveProofError(
                "pre-existing baseline verdict replay changed semantics"
            )
        required = {
            "lifecycle_id",
            "repo",
            "spec_version",
            "state_version",
            "status",
            "health",
            "fingerprint",
            "legal_frontier",
            "obligations",
            "blockers",
            "gates",
            "capabilities",
            "provenance",
            "freshness",
            "source",
            "command_verdicts",
        }
        missing = required - set(projection)
        if missing:
            raise LiveProofError(
                f"Candystore projection omitted fields: {sorted(missing)}"
            )
        grant = next(
            item
            for item in projection["capabilities"]
            if item["capability_id"] == CAPABILITY_ID and item["actor_id"] == ACTOR_ID
        )
        if grant["capability_version"] != self.capability_version():
            raise LiveProofError("Candystore changed authoritative capability_version")
        unknown_status, unknown = http_json(
            f"http://127.0.0.1:{self.ports['candystore']}/lifecycles/missing-{self.suffix}"
        )
        write_status, _ = http_json(
            f"http://127.0.0.1:{self.ports['candystore']}/lifecycles/{self.lifecycle_id}/actions",
            method="POST",
            body={"intent": "forbidden"},
        )
        if (
            unknown_status != 200
            or unknown.get("projection_status") != "missing"
            or unknown.get("health") != "degraded"
            or write_status != 404
        ):
            raise LiveProofError(
                "Candystore unknown/read-only ownership boundary failed"
            )
        self.summary["seams"]["candystore"] = {
            "projection_version": projection["state_version"],
            "projection_status": projection["projection_status"],
            "source_event_id": projection["source"]["event_id"],
            "source_identity": {
                **expected_source_identity,
                "actor": projection_source["actor"],
                "correlation_id": projection_source["correlation_id"],
                "causation_id": projection_source["causation_id"],
            },
            "prestart_snapshot_event_id": self.prestart_snapshot_event_id,
            "prestart_verdict_command_id": self.prestart_verdict_command_id,
            "prestart_verdict": replay_verdict,
            "late_subscriber_replayed_before_post_start_traffic": True,
            "capability_version": grant["capability_version"],
            "unknown": {
                "projection_status": unknown["projection_status"],
                "health": unknown["health"],
            },
            "write_status": write_status,
        }

        print(
            "[live] proving canonical-row integrity for a conflicting duplicate",
            flush=True,
        )
        canonical_raw = json.loads(
            self.candystore_psql(
                "SELECT raw::text FROM events WHERE id = "
                f"{sql_literal(self.prestart_snapshot_event_id)}::uuid"
            )
        )
        conflicting = json.loads(json.dumps(canonical_raw))
        conflicting["data"]["state_version"] = authority["state_version"] + 100
        conflicting["data"]["previous_state_version"] = authority["state_version"] + 99
        conflicting["data"]["state"]["status"] = "completed"
        conflicting["data"]["state"]["phase"] = "spoofed"
        conflicting["data"]["capabilities"][0]["capability_version"] = 999
        conflicting["data"]["publication"]["aggregate_version"] = (
            authority["state_version"] + 100
        )
        conflicting["data"]["publication"]["event_sequence"] = 999999
        duplicate_status, duplicate_result = http_json(
            f"http://127.0.0.1:{self.ports['candystore']}/events/all",
            method="POST",
            body=conflicting,
        )
        if duplicate_status != 200 or duplicate_result != {
            "status": "SUCCESS",
            "inserted": False,
        }:
            raise LiveProofError(
                f"conflicting duplicate was not deduplicated: {duplicate_result}"
            )
        after_duplicate = self.projection()
        canonical_after = json.loads(
            self.candystore_psql(
                "SELECT raw::text FROM events WHERE id = "
                f"{sql_literal(self.prestart_snapshot_event_id)}::uuid"
            )
        )
        duplicate_count = int(
            self.candystore_psql(
                "SELECT COUNT(*) FROM events WHERE id = "
                f"{sql_literal(self.prestart_snapshot_event_id)}::uuid"
            )
        )
        stable_fields = (
            "state_version",
            "status",
            "phase",
            "fingerprint",
            "source",
            "publication",
        )
        if (
            canonical_after != canonical_raw
            or duplicate_count != 1
            or any(
                after_duplicate[field] != projection[field] for field in stable_fields
            )
            or after_duplicate["capabilities"] != projection["capabilities"]
        ):
            raise LiveProofError(
                "conflicting duplicate influenced canonical history or projection"
            )
        self.summary["seams"]["candystore"]["conflicting_duplicate"] = {
            "event_id": self.prestart_snapshot_event_id,
            "inserted": duplicate_result["inserted"],
            "canonical_row_count": duplicate_count,
            "canonical_state_version": after_duplicate["state_version"],
            "spoofed_state_version": conflicting["data"]["state_version"],
            "canonical_capability_version": after_duplicate["capabilities"][0][
                "capability_version"
            ],
            "spoofed_capability_version": 999,
        }

        print(
            "[live] proving spoofed authority candidates stay audit-only",
            flush=True,
        )
        spoof_snapshot = json.loads(json.dumps(canonical_raw))
        spoof_snapshot["id"] = stable_uuid(f"{self.suffix}:spoof:snapshot")
        spoof_snapshot["source"] = "urn:attacker"
        spoof_snapshot["subject"] = "evil.subject"
        spoof_snapshot["producer"] = "attacker"
        spoof_snapshot["service"] = "attacker"
        spoof_snapshot["actor"] = {"type": "service", "agent_id": "attacker"}
        spoof_snapshot["data"]["provenance"]["authority"] = "attacker"
        spoof_snapshot["data"]["state_version"] = authority["state_version"] + 200
        spoof_snapshot["data"]["previous_state_version"] = (
            authority["state_version"] + 199
        )
        spoof_snapshot["data"]["publication"]["aggregate_version"] = (
            authority["state_version"] + 200
        )
        spoof_snapshot["data"]["publication"]["event_sequence"] = 999998
        spoof_snapshot["data"]["state"]["status"] = "completed"
        spoof_snapshot_status, spoof_snapshot_result = http_json(
            f"http://127.0.0.1:{self.ports['candystore']}/events/all",
            method="POST",
            body=spoof_snapshot,
        )

        canonical_reply_raw = json.loads(
            self.candystore_psql(
                "SELECT raw::text FROM events WHERE kind = 'reply' "
                "AND data->>'command_id' = "
                f"{sql_literal(self.prestart_verdict_command_id)} "
                "ORDER BY time DESC LIMIT 1"
            )
        )
        spoof_reply = json.loads(json.dumps(canonical_reply_raw))
        spoof_reply["id"] = stable_uuid(f"{self.suffix}:spoof:reply")
        spoof_reply["source"] = "urn:attacker"
        spoof_reply["subject"] = "evil.subject"
        spoof_reply["producer"] = "attacker"
        spoof_reply["service"] = "attacker"
        spoof_reply["actor"] = {"type": "service", "agent_id": "attacker"}
        spoof_reply["data"]["verdict"] = "stale"
        spoof_reply["data"]["reason_code"] = "EXPECTED_STATE_VERSION_MISMATCH"
        spoof_reply_status, spoof_reply_result = http_json(
            f"http://127.0.0.1:{self.ports['candystore']}/events/all",
            method="POST",
            body=spoof_reply,
        )
        projection_after_spoofs = self.projection()
        verdict_after_spoof = next(
            item
            for item in projection_after_spoofs["command_verdicts"]
            if item["command_id"] == self.prestart_verdict_command_id
        )
        spoof_audit_rows = {
            "snapshot": int(
                self.candystore_psql(
                    "SELECT COUNT(*) FROM events WHERE id = "
                    f"{sql_literal(spoof_snapshot['id'])}::uuid"
                )
            ),
            "reply": int(
                self.candystore_psql(
                    "SELECT COUNT(*) FROM events WHERE id = "
                    f"{sql_literal(spoof_reply['id'])}::uuid"
                )
            ),
        }
        spoof_receipts = {
            "snapshot": int(
                self.candystore_psql(
                    "SELECT COUNT(*) FROM lifecycle_projection_receipts WHERE event_id = "
                    f"{sql_literal(spoof_snapshot['id'])}::uuid"
                )
            ),
            "reply": int(
                self.candystore_psql(
                    "SELECT COUNT(*) FROM lifecycle_projection_receipts WHERE event_id = "
                    f"{sql_literal(spoof_reply['id'])}::uuid"
                )
            ),
        }
        if (
            spoof_snapshot_status != 200
            or spoof_snapshot_result != {"status": "SUCCESS", "inserted": True}
            or spoof_reply_status != 200
            or spoof_reply_result != {"status": "SUCCESS", "inserted": True}
            or spoof_audit_rows != {"snapshot": 1, "reply": 1}
            or spoof_receipts != {"snapshot": 0, "reply": 0}
            or projection_after_spoofs["source"] != projection["source"]
            or projection_after_spoofs["state_version"] != projection["state_version"]
            or verdict_after_spoof["verdict"] != "illegal"
            or verdict_after_spoof["mutated"] is not False
        ):
            raise LiveProofError(
                "spoofed Lifecycle authority candidate mutated projection or verdict"
            )
        self.summary["seams"]["candystore"]["authority_spoof_rejection"] = {
            "spoof_snapshot_event_id": spoof_snapshot["id"],
            "spoof_reply_event_id": spoof_reply["id"],
            "audit_rows": spoof_audit_rows,
            "projection_receipts": spoof_receipts,
            "canonical_source_event_id": projection_after_spoofs["source"]["event_id"],
            "canonical_verdict": verdict_after_spoof,
        }

        self.compose("start", "lifecycle")
        self.wait_health("/readyz", 200)

        print("[live] exercising real Momo durable obligation actor", flush=True)
        momo_script = (
            SOURCE_ROOT / "skills" / "momo" / "scripts" / "lifecycle_client.py"
        )
        if self.proof_dir is None:
            workspace_context: Any = tempfile.TemporaryDirectory(
                prefix=f"aion-momo-{self.suffix}-"
            )
        else:
            actor_workspace = self.proof_dir / "momo-obligation"
            actor_workspace.mkdir()
            workspace_context = nullcontext(str(actor_workspace))
        with workspace_context as temp:
            temp_dir = Path(temp)
            snapshot_path = temp_dir / "snapshot.json"
            evidence_package_path = temp_dir / "evidence-package.json"
            expectation_path = temp_dir / "invocation-expectation.json"
            invocation_plan_path = temp_dir / "invocation-plan.json"
            invocation_path = temp_dir / "invocation.json"
            preactivation_path = temp_dir / "preactivation-evidence.json"
            wrong_occurrence_path = temp_dir / "wrong-occurrence-evidence.json"
            ready_path = temp_dir / "worker-ready.json"
            preview_path = temp_dir / "completion-preview.json"
            release_path = temp_dir / "completion.release"
            receipt_path = temp_dir / "worker-receipt.json"
            report_path = temp_dir / "review-report.md"
            actor_log_path = temp_dir / "worker.log"
            fetched = run(
                [
                    sys.executable,
                    str(momo_script),
                    "fetch",
                    "--candystore-url",
                    f"http://127.0.0.1:{self.ports['candystore']}",
                    "--lifecycle-id",
                    self.lifecycle_id,
                ]
            )
            snapshot = json.loads(fetched.stdout)
            snapshot_bytes = (
                json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
            ).encode()
            snapshot_path.write_bytes(snapshot_bytes)
            pending_obligation = next(
                item
                for item in snapshot["obligations"]
                if item["id"] == "independent-review" and item["status"] == "pending"
            )
            blocked_frontier = next(
                item
                for item in snapshot["legal_frontier"]
                if item["id"] == "transition:waiting:active"
            )
            if blocked_frontier["allowed"] is not False:
                raise LiveProofError(
                    "Momo received a falsely legal pending-obligation frontier"
                )
            projection_source = snapshot["source"]
            invocation = json.loads(
                run(
                    [
                        sys.executable,
                        str(momo_script),
                        "plan-obligation",
                        "--snapshot",
                        str(snapshot_path),
                        "--actor-id",
                        ACTOR_ID,
                    ]
                ).stdout
            )
            skill_ref = invocation["selection"]["skill_ref"]
            if skill_ref != {"name": "bmad-code-review", "selector": "6.10.2"}:
                raise LiveProofError(
                    f"Momo changed canonical obligation skill ref: {skill_ref}"
                )
            if "decision_rationale" in invocation["invocation_command"]["data"]:
                raise LiveProofError("Momo mixed rationale into invocation intent")
            if (
                invocation["selection"]["target_actor_id"]
                != pending_obligation["owner_id"]
            ):
                raise LiveProofError(
                    "Momo changed the authoritative obligation target actor"
                )
            if (
                invocation["selection"]["obligation_instance_id"]
                != pending_obligation["obligation_instance_id"]
                or invocation["selection"]["activated_at"]
                != pending_obligation["activated_at"]
                or invocation["invocation_command"]["correlationid"]
                != projection_source["correlation_id"]
                or invocation["invocation_command"]["causationid"]
                != projection_source["event_id"]
            ):
                raise LiveProofError(
                    "Momo invocation lost authoritative occurrence or causal lineage"
                )
            invocation_plan_path.write_text(
                json.dumps(invocation, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            invocation_path.write_text(
                json.dumps(
                    invocation["invocation_command"], indent=2, sort_keys=True
                )
                + "\n",
                encoding="utf-8",
            )
            selection = invocation["selection"]
            invocation_command = invocation["invocation_command"]
            invocation_context = invocation_command["data"]["context"]
            expectation = {
                "contract": "momo.obligation-worker.expectation.v1",
                "invocation_id": invocation_command["id"],
                "lifecycle_id": selection["lifecycle_id"],
                "obligation_id": selection["obligation_id"],
                "obligation_instance_id": selection["obligation_instance_id"],
                "activated_at": selection["activated_at"],
                "target_actor_id": selection["target_actor_id"],
                "expected_state_version": selection["state_version"],
                "authority_snapshot_event_id": selection[
                    "authority_snapshot_event_id"
                ],
                "authority_snapshot_event_time": selection[
                    "authority_snapshot_event_time"
                ],
                "authority_snapshot_correlation_id": selection[
                    "authority_snapshot_correlation_id"
                ],
                "correlation_id": invocation_command["correlationid"],
                "causation_id": invocation_command["causationid"],
                "skill_ref": invocation_context["skill_ref"],
            }
            expectation_path.write_text(
                json.dumps(expectation, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            obligation_index = snapshot["obligations"].index(pending_obligation)
            evidence_package = {
                "schema": "momo.obligation-review-evidence-package.v1",
                "run_id": self.project,
                "lifecycle_id": self.lifecycle_id,
                "repo": REPO,
                "artifacts": [
                    {
                        "id": "current-authority-projection",
                        "path": snapshot_path.name,
                        "media_type": "application/json",
                        "size_bytes": len(snapshot_bytes),
                        "sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
                    }
                ],
                "assertions": [
                    {
                        "id": "lifecycle-id",
                        "artifact_id": "current-authority-projection",
                        "pointer": "/lifecycle_id",
                        "equals": self.lifecycle_id,
                    },
                    {
                        "id": "authority-state-version",
                        "artifact_id": "current-authority-projection",
                        "pointer": "/state_version",
                        "equals": selection["state_version"],
                    },
                    {
                        "id": "authority-snapshot-event",
                        "artifact_id": "current-authority-projection",
                        "pointer": "/source/event_id",
                        "equals": selection["authority_snapshot_event_id"],
                    },
                    {
                        "id": "active-obligation-occurrence",
                        "artifact_id": "current-authority-projection",
                        "pointer": (
                            f"/obligations/{obligation_index}/obligation_instance_id"
                        ),
                        "equals": selection["obligation_instance_id"],
                    },
                    {
                        "id": "pending-obligation-status",
                        "artifact_id": "current-authority-projection",
                        "pointer": f"/obligations/{obligation_index}/status",
                        "equals": "pending",
                    },
                    {
                        "id": "canonical-skill-ref",
                        "artifact_id": "current-authority-projection",
                        "pointer": f"/obligations/{obligation_index}/skill_ref",
                        "equals": skill_ref,
                    },
                    {
                        "id": "authoritative-target",
                        "artifact_id": "current-authority-projection",
                        "pointer": f"/obligations/{obligation_index}/owner_id",
                        "equals": selection["target_actor_id"],
                    },
                ],
            }
            evidence_package_path.write_text(
                json.dumps(evidence_package, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            actor_consumer = f"aion-momo-{self.suffix}"
            actor_process = self.start_momo_obligation_actor(
                workspace=temp_dir,
                consumer=actor_consumer,
            )

            def actor_output(path: Path) -> dict[str, Any] | None:
                if path.is_file():
                    return json.loads(path.read_text(encoding="utf-8"))
                returncode = actor_process.poll()
                if returncode is None:
                    return None
                log = actor_log_path.read_text(encoding="utf-8", errors="replace")
                return {"worker_exit": returncode, "worker_log": log[-4000:]}

            actor_ready = wait_for(
                "Momo durable actor readiness",
                lambda: actor_output(ready_path),
                timeout=120,
            )
            if actor_ready.get("status") != "ready" or actor_ready.get(
                "consumer"
            ) != actor_consumer:
                raise LiveProofError(f"Momo durable actor failed readiness: {actor_ready}")
            invocation_publish_ack = self.publish_jetstream(invocation_command)
            if (
                invocation_publish_ack.get("stream") != COMMAND_STREAM
                or invocation_publish_ack.get("event_id") != invocation_command["id"]
                or invocation_publish_ack.get("subject") != INVOCATION_SUBJECT
                or not isinstance(
                    invocation_publish_ack.get("stream_sequence"), int
                )
                or invocation_publish_ack["stream_sequence"] < 1
                or invocation_publish_ack.get("duplicate") is not False
            ):
                raise LiveProofError(
                    "Momo invocation publication lacked an exact JetStream PubAck: "
                    f"{invocation_publish_ack!r}"
                )
            completion_event = wait_for(
                "Momo actor completion preview",
                lambda: actor_output(preview_path),
                timeout=120,
            )
            if (
                completion_event["data"]["obligation_id"] != pending_obligation["id"]
                or completion_event["data"]["obligation_instance_id"]
                != pending_obligation["obligation_instance_id"]
                or completion_event["data"]["target_actor_id"]
                != pending_obligation["owner_id"]
                or completion_event["causationid"]
                != invocation["invocation_command"]["id"]
                or completion_event["correlationid"]
                != invocation["invocation_command"]["correlationid"]
                or completion_event["data"]["evidence"]["outcome"] != "completed"
            ):
                raise LiveProofError(
                    "Momo completion evidence lost obligation identity"
                )

            activated_at = datetime.fromisoformat(
                pending_obligation["activated_at"].replace("Z", "+00:00")
            )
            preactivation_time = (
                (activated_at - timedelta(seconds=1))
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            )
            preactivation_event = json.loads(json.dumps(completion_event))
            preactivation_event["id"] = stable_uuid(
                f"{self.suffix}:evidence:preactivation"
            )
            preactivation_event["time"] = preactivation_time
            preactivation_event["data"]["completed_at"] = preactivation_time
            preactivation_event["data"]["evidence"]["artifact_id"] = (
                f"historical-review:{self.suffix}"
            )
            preactivation_path.write_text(
                json.dumps(preactivation_event, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            preactivation_publish = self.publish_jetstream(preactivation_event)
            preactivation_state = wait_for(
                "pre-activation evidence rejection",
                lambda: (
                    current
                    if (current := self.state())["state_version"]
                    > snapshot["state_version"]
                    and current["status"] == "waiting"
                    and next(
                        item
                        for item in current["obligations"]
                        if item["id"] == "independent-review"
                    )["status"]
                    == "pending"
                    else None
                ),
                timeout=90,
            )
            preactivation_obligation = next(
                item
                for item in preactivation_state["obligations"]
                if item["id"] == "independent-review"
            )
            if (
                preactivation_obligation["obligation_instance_id"]
                != pending_obligation["obligation_instance_id"]
                or preactivation_obligation["activated_at"]
                != pending_obligation["activated_at"]
                or preactivation_obligation["status"] != "pending"
            ):
                raise LiveProofError(
                    "pre-activation evidence changed the active obligation occurrence"
                )

            wrong_occurrence_event = json.loads(json.dumps(completion_event))
            wrong_occurrence_event["id"] = stable_uuid(
                f"{self.suffix}:evidence:wrong-occurrence"
            )
            wrong_occurrence_event["data"]["obligation_instance_id"] = stable_uuid(
                f"{self.suffix}:prior-obligation-occurrence"
            )
            wrong_occurrence_event["data"]["evidence"]["artifact_id"] = (
                f"prior-occurrence-review:{self.suffix}"
            )
            wrong_occurrence_path.write_text(
                json.dumps(wrong_occurrence_event, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            wrong_occurrence_publish = self.publish_jetstream(wrong_occurrence_event)
            wrong_occurrence_state = wait_for(
                "wrong-occurrence evidence rejection",
                lambda: (
                    current
                    if (current := self.state())["state_version"]
                    > preactivation_state["state_version"]
                    and current["status"] == "waiting"
                    and next(
                        item
                        for item in current["obligations"]
                        if item["id"] == "independent-review"
                    )["status"]
                    == "pending"
                    else None
                ),
                timeout=90,
            )
            wrong_occurrence_obligation = next(
                item
                for item in wrong_occurrence_state["obligations"]
                if item["id"] == "independent-review"
            )
            if (
                wrong_occurrence_obligation["obligation_instance_id"]
                != pending_obligation["obligation_instance_id"]
                or wrong_occurrence_obligation["status"] != "pending"
            ):
                raise LiveProofError(
                    "prior-occurrence evidence satisfied the active occurrence"
                )

            release_path.write_text("publish actor completion\n", encoding="utf-8")
            receipt = wait_for(
                "Momo obligation receipt",
                lambda: actor_output(receipt_path),
                timeout=120,
            )
            if receipt.get("status") != "completed":
                raise LiveProofError(f"Momo actor failed before receipt: {receipt}")
            actor_exit = wait_for(
                "Momo obligation actor exit",
                lambda: (
                    {"returncode": returncode}
                    if (returncode := actor_process.poll()) is not None
                    else None
                ),
                timeout=30,
            )
            actor_log = actor_log_path.read_text(encoding="utf-8", errors="replace")
            if actor_exit["returncode"] != 0:
                raise LiveProofError(
                    f"Momo obligation actor exited {actor_exit['returncode']}: "
                    f"{actor_log[-4000:]}"
                )

            workspace_root = temp_dir.resolve()
            artifact_path = Path(receipt["artifact"]["path"]).resolve()
            if (
                workspace_root not in artifact_path.parents
                or artifact_path != report_path.resolve()
            ):
                raise LiveProofError(
                    "receipt/artifact identity mismatch: artifact escaped proof workspace"
                )
            artifact_bytes = artifact_path.read_bytes()
            artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
            if (
                len(artifact_sha256) != 64
                or any(character not in "0123456789abcdef" for character in artifact_sha256)
                or len(set(artifact_sha256)) == 1
            ):
                raise LiveProofError("Momo actor produced a placeholder success hash")
            if (
                receipt["artifact"]["sha256"] != artifact_sha256
                or receipt["artifact"]["size_bytes"] != len(artifact_bytes)
                or completion_event["data"]["evidence"]["artifact_sha256"]
                != artifact_sha256
                or receipt["completion"]["event_id"] != completion_event["id"]
                or receipt["completion"]["subject"] != completion_event["subject"]
                or receipt["completion"]["stream"] != "BLOODBANK_EVENTS"
                or not isinstance(receipt["completion"]["stream_sequence"], int)
                or receipt["completion"]["stream_sequence"] < 1
                or receipt["delivery"]["stream"] != COMMAND_STREAM
                or receipt["delivery"]["consumer"] != actor_consumer
                or receipt["delivery"]["stream_sequence"]
                != invocation_publish_ack["stream_sequence"]
                or receipt["invocation"]["id"] != invocation_command["id"]
                or receipt["invocation"]["correlation_id"]
                != invocation_command["correlationid"]
                or receipt["invocation"]["causation_id"]
                != invocation_command["causationid"]
            ):
                raise LiveProofError("receipt/artifact identity mismatch")
            resource_relative = Path(receipt["skill"]["resource_path"])
            resource_root = (SOURCE_ROOT / "momo").resolve()
            skill_resource_path = (resource_root / resource_relative).resolve()
            if (
                resource_relative.is_absolute()
                or ".." in resource_relative.parts
                or resource_root not in skill_resource_path.parents
                or hashlib.sha256(skill_resource_path.read_bytes()).hexdigest()
                != receipt["skill"]["resource_sha256"]
                or receipt["skill"]["name"] != skill_ref["name"]
                or receipt["skill"]["selector"] != skill_ref["selector"]
            ):
                raise LiveProofError("Momo receipt skill resource identity mismatch")
            operation_order = [
                item["operation"] for item in receipt["operation_order"]
            ]
            if (
                operation_order.index("completion_puback")
                >= operation_order.index("invocation_ack_sync")
                or [item["sequence"] for item in receipt["operation_order"]]
                != list(range(1, len(operation_order) + 1))
            ):
                raise LiveProofError("Momo invocation ACK preceded completion PubAck")
            actor_consumer_info = self.consumer_info(COMMAND_STREAM, actor_consumer)
            if actor_consumer_info.get("num_ack_pending") != 0:
                raise LiveProofError("Momo durable consumer retained an ACK-pending invocation")

            momo_state = self.wait_state_version(
                wrong_occurrence_state["state_version"] + 1, "active"
            )
            momo_projection = self.wait_projection(
                minimum_version=momo_state["state_version"],
                status="active",
            )
            if momo_projection["obligations"]:
                raise LiveProofError(
                    "Lifecycle retained a satisfied obligation as pending"
                )
            evidence_rows = int(
                self.psql(
                    "SELECT COUNT(*) FROM lifecycle_observations "
                    f"WHERE lifecycle_id = {sql_literal(self.lifecycle_id)} "
                    "AND kind = 'obligation_evidence' "
                    f"AND source_event_id = {sql_literal(completion_event['id'])}::uuid"
                )
            )
            candystore_evidence_rows = int(
                self.candystore_psql(
                    "SELECT COUNT(*) FROM events WHERE id = "
                    f"{sql_literal(completion_event['id'])}::uuid"
                )
            )
            if evidence_rows != 1 or candystore_evidence_rows != 1:
                raise LiveProofError(
                    "completion evidence was not durably observed exactly once"
                )
        self.summary["seams"]["momo"] = {
            "skill_ref": skill_ref,
            "invocation_subject": invocation["invocation_command"]["subject"],
            "invocation_event_id": invocation["invocation_command"]["id"],
            "target_actor_id": invocation["selection"]["target_actor_id"],
            "obligation_instance_id": pending_obligation["obligation_instance_id"],
            "activated_at": pending_obligation["activated_at"],
            "authority_snapshot_event_id": projection_source["event_id"],
            "correlation_id": projection_source["correlation_id"],
            "blocked_frontier": blocked_frontier,
            "preactivation_evidence": {
                "event_id": preactivation_event["id"],
                "completed_at": preactivation_time,
                "publish": preactivation_publish,
                "state_version": preactivation_state["state_version"],
                "status": preactivation_obligation["status"],
            },
            "wrong_occurrence_evidence": {
                "event_id": wrong_occurrence_event["id"],
                "submitted_obligation_instance_id": wrong_occurrence_event["data"][
                    "obligation_instance_id"
                ],
                "publish": wrong_occurrence_publish,
                "state_version": wrong_occurrence_state["state_version"],
                "status": wrong_occurrence_obligation["status"],
            },
            "completion_subject": completion_event["subject"],
            "completion_event_id": completion_event["id"],
            "invocation_puback": invocation_publish_ack,
            "actor_ready": actor_ready,
            "actor_receipt": receipt,
            "actor_consumer": actor_consumer_info,
            "actor_exit": actor_exit,
            "actor_log": str(actor_log_path),
            "artifact": {
                "path": str(artifact_path),
                "size_bytes": len(artifact_bytes),
                "sha256": artifact_sha256,
            },
            "authority_evidence_rows": evidence_rows,
            "candystore_evidence_rows": candystore_evidence_rows,
            "state_before": snapshot["state_version"],
            "state_after": momo_state["state_version"],
            "status_after": momo_state["status"],
        }

        print("[live] exercising Holocene read/action and browser surfaces", flush=True)
        holocene = SOURCE_ROOT / "holocene"
        api_entry = holocene / "apps" / "api" / "dist" / "server.js"
        web_entry = holocene / "apps" / "web" / ".next" / "BUILD_ID"
        if not api_entry.is_file() or not web_entry.is_file():
            raise LiveProofError(
                "run pnpm build in holocene before the live client gate"
            )
        api_env = os.environ.copy()
        api_env.update(
            {
                "PORT": str(self.ports["api"]),
                "HOST": "127.0.0.1",
                "CANDYSTORE_URL": f"http://127.0.0.1:{self.ports['candystore']}",
                "BLOODBANK_NATS_URLS": f"nats://127.0.0.1:{self.ports['nats']}",
            }
        )
        self.api_process = subprocess.Popen(
            ["node", str(api_entry)],
            cwd=holocene,
            env=api_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        def api_health():
            status, body = http_json(f"http://127.0.0.1:{self.ports['api']}/health")
            return body if status == 200 and body.get("ok") is True else None

        wait_for("Holocene API health", api_health)
        api_status, api_projection = http_json(
            f"http://127.0.0.1:{self.ports['api']}/api/modules/lifecycle/{self.lifecycle_id}"
        )
        if (
            api_status != 200
            or api_projection["state_version"] != momo_state["state_version"]
        ):
            raise LiveProofError("Holocene did not render Candystore faithfully")
        holocene_frontier = next(
            item
            for item in api_projection["legal_frontier"]
            if item["id"] == "transition:active:waiting" and item["allowed"]
        )
        grant = next(
            item
            for item in api_projection["capabilities"]
            if item["actor_id"] == ACTOR_ID
        )
        action_body = {
            "frontier_id": holocene_frontier["id"],
            "expected_state_version": api_projection["state_version"],
            "actor": {"type": "operator", "agent_id": ACTOR_ID},
            "capability_id": grant["capability_id"],
            "parameters": {},
        }
        action_status, queued = http_json(
            (
                f"http://127.0.0.1:{self.ports['api']}/api/modules/lifecycle/"
                f"{self.lifecycle_id}/actions"
            ),
            method="POST",
            body=action_body,
        )
        if (
            action_status != 202
            or queued.get("broker_processed") is not True
            or queued.get("durable_jetstream_acknowledged") is not False
            or queued.get("authority_accepted") is not False
            or queued.get("correlation_id")
            != api_projection["source"]["correlation_id"]
            or queued.get("causation_id") != api_projection["source"]["event_id"]
        ):
            raise LiveProofError(f"Holocene action was not non-authoritative: {queued}")
        holocene_result = self.wait_command(queued["command_event_id"], "applied")
        holocene_state = self.wait_state_version(
            api_projection["state_version"] + 1, "waiting"
        )
        rendered = self.wait_projection(
            minimum_version=holocene_state["state_version"],
            status="waiting",
            command_id=queued["command_id"],
        )
        repeated_obligation = next(
            item
            for item in rendered["obligations"]
            if item["id"] == "independent-review"
        )
        repeated_frontier = next(
            item
            for item in rendered["legal_frontier"]
            if item["id"] == "transition:waiting:active"
        )
        if (
            repeated_obligation["status"] != "pending"
            or repeated_obligation["obligation_instance_id"]
            == pending_obligation["obligation_instance_id"]
            or repeated_frontier["allowed"] is not False
            or repeated_frontier["reason_code"] != "PENDING_OBLIGATIONS"
            or rendered["source"]["correlation_id"] != queued["correlation_id"]
            or rendered["source"]["causation_id"] != queued["command_event_id"]
        ):
            raise LiveProofError(
                "repeated WAITING occurrence reused prior evidence or lost causality"
            )

        wait_for(
            "drained repeated-occurrence outbox",
            lambda: self.counts()["outbox_pending"] == 0,
        )
        quiesce_authority = self.state()
        quiesce_projection = self.wait_projection(
            minimum_version=quiesce_authority["state_version"],
            status="waiting",
            command_id=queued["command_id"],
        )
        manual_frontier = next(
            (
                item
                for item in quiesce_authority["legal_frontier"]
                if item["id"] == "mode:manual" and item["allowed"]
            ),
            None,
        )
        if (
            quiesce_projection["state_version"] != quiesce_authority["state_version"]
            or manual_frontier is None
            or manual_frontier["expected_state_version"]
            != quiesce_authority["state_version"]
        ):
            raise LiveProofError(
                "authority/projection did not expose a synchronized manual-mode frontier"
            )
        quiesce_command = self.command(
            "manual-before-repeated-restart",
            expected_state_version=manual_frontier["expected_state_version"],
            target="manual",
            correlation_id=quiesce_projection["source"]["correlation_id"],
            causation_id=quiesce_projection["source"]["event_id"],
            intent_name="set_mode",
        )
        self.publish(quiesce_command)
        quiesce_result = self.wait_command(quiesce_command["id"], "applied")
        if (
            quiesce_result["mutated"] is not True
            or quiesce_result["command_event_id"] != quiesce_command["id"]
            or quiesce_result["command_id"] != quiesce_command["command_id"]
            or quiesce_result["reply_subject"]
            != "bloodbank.rpy.v1.lifecycle.intent.submit"
            or quiesce_result["reply_correlation_id"]
            != quiesce_command["correlationid"]
            or quiesce_result["reply_causation_id"] != quiesce_command["id"]
        ):
            raise LiveProofError(
                "Bloodbank restart-quiesce transaction lost authority identity"
            )
        quiesced_state = self.wait_state_version(
            quiesce_authority["state_version"] + 1, "waiting"
        )
        quiesced_obligation = next(
            item
            for item in quiesced_state["obligations"]
            if item["id"] == "independent-review"
        )
        if (
            quiesced_state["mode"] != "manual"
            or quiesced_obligation["status"] != "pending"
            or quiesced_obligation["obligation_instance_id"]
            != repeated_obligation["obligation_instance_id"]
            or quiesced_obligation["activated_at"]
            != repeated_obligation["activated_at"]
        ):
            raise LiveProofError(
                "restart quiesce changed the repeated obligation occurrence"
            )
        wait_for(
            "drained restart-quiesce outbox",
            lambda: self.counts()["outbox_pending"] == 0,
        )
        self.compose("restart", "lifecycle")
        self.wait_health("/readyz", 200)
        repeated_state_before_restart = self.wait_state_version(
            quiesced_state["state_version"] + 1, "waiting"
        )
        wait_for(
            "settled repeated-occurrence reconcile queue/outbox",
            lambda: (
                True
                if self.reconcile_queue_depth() == 0
                and self.counts()["outbox_pending"] == 0
                else None
            ),
        )
        settled_repeated_obligation = next(
            item
            for item in repeated_state_before_restart["obligations"]
            if item["id"] == "independent-review"
        )
        if (
            repeated_state_before_restart["mode"] != "manual"
            or settled_repeated_obligation["status"] != "pending"
            or settled_repeated_obligation["obligation_instance_id"]
            != repeated_obligation["obligation_instance_id"]
            or settled_repeated_obligation["activated_at"]
            != repeated_obligation["activated_at"]
        ):
            raise LiveProofError(
                "post-quiesce reconcile changed the repeated obligation occurrence"
            )
        repeated_counts_before_restart = self.counts()
        self.compose("restart", "lifecycle")
        self.wait_health("/readyz", 200)
        wait_for(
            "empty repeated-occurrence restart queue/outbox",
            lambda: (
                True
                if self.reconcile_queue_depth() == 0
                and self.counts()["outbox_pending"] == 0
                else None
            ),
        )
        time.sleep(1)
        repeated_state_after_restart = self.state()
        repeated_counts_after_restart = self.counts()
        repeated_after_restart = next(
            item
            for item in repeated_state_after_restart["obligations"]
            if item["id"] == "independent-review"
        )
        if (
            repeated_state_after_restart != repeated_state_before_restart
            or repeated_counts_after_restart != repeated_counts_before_restart
            or repeated_after_restart["obligation_instance_id"]
            != repeated_obligation["obligation_instance_id"]
            or repeated_after_restart["status"] != "pending"
        ):
            raise LiveProofError(
                "restart changed or duplicated the repeated obligation occurrence: "
                f"state_before={repeated_state_before_restart!r} "
                f"state_after={repeated_state_after_restart!r} "
                f"counts_before={repeated_counts_before_restart!r} "
                f"counts_after={repeated_counts_after_restart!r}"
            )
        self.summary["seams"]["holocene"] = {
            "read_state_version": api_projection["state_version"],
            "publish_receipt": queued,
            "authoritative_capability_version": grant["capability_version"],
            "command_result": holocene_result,
            "rendered_state_version": rendered["state_version"],
            "rendered_status": rendered["status"],
            "verdict_count": len(rendered["command_verdicts"]),
            "correlation_id": queued["correlation_id"],
            "causation_id": queued["causation_id"],
            "repeated_occurrence": {
                "prior_obligation_instance_id": pending_obligation[
                    "obligation_instance_id"
                ],
                "active_obligation_instance_id": repeated_obligation[
                    "obligation_instance_id"
                ],
                "activated_at": repeated_obligation["activated_at"],
                "frontier": repeated_frontier,
                "state_version": repeated_state_after_restart["state_version"],
                "restart_quiesce": {
                    "command_event_id": quiesce_command["id"],
                    "command_id": quiesce_command["command_id"],
                    "command_subject": quiesce_command["subject"],
                    "correlation_id": quiesce_command["correlationid"],
                    "causation_id": quiesce_command["causationid"],
                    "reply_event_id": quiesce_result["reply_event_id"],
                    "reply_subject": quiesce_result["reply_subject"],
                    "reply_correlation_id": quiesce_result["reply_correlation_id"],
                    "reply_causation_id": quiesce_result["reply_causation_id"],
                    "result": quiesce_result,
                    "settled_state_version": repeated_state_before_restart[
                        "state_version"
                    ],
                },
                "restart_counts": repeated_counts_after_restart,
            },
        }

        if self.screenshots_dir is not None:
            self.screenshots_dir.mkdir(parents=True, exist_ok=True)
            web_env = os.environ.copy()
            web_env.update(
                {
                    "HOLOCENE_WEB_PORT": str(self.ports["web"]),
                    "HOLOCENE_API_INTERNAL_URL": f"http://127.0.0.1:{self.ports['api']}",
                    "NEXT_TELEMETRY_DISABLED": "1",
                }
            )
            self.web_process = subprocess.Popen(
                ["pnpm", "--filter", "@holocene/web", "start"],
                cwd=holocene,
                env=web_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            page_url = (
                f"http://127.0.0.1:{self.ports['web']}/lifecycle/{self.lifecycle_id}"
            )

            def page_ready():
                try:
                    with urlopen(page_url, timeout=3) as response:
                        return response.status == 200
                except OSError:
                    return False

            wait_for("Holocene web page", page_ready)
            desktop = self.screenshots_dir / f"{self.project}-desktop.png"
            mobile = self.screenshots_dir / f"{self.project}-mobile.png"
            base = [
                "pnpm",
                "exec",
                "playwright",
                "screenshot",
                "--wait-for-selector",
                "main.lifecycle-shell",
                "--wait-for-timeout",
                "2000",
                "--full-page",
            ]
            run(
                [*base, "--viewport-size", "1440,1000", page_url, str(desktop)],
                cwd=holocene,
                timeout=90,
            )
            run(
                [
                    *base,
                    "--browser",
                    "chromium",
                    "--device",
                    "Pixel 7",
                    page_url,
                    str(mobile),
                ],
                cwd=holocene,
                timeout=90,
            )
            self.summary["seams"]["holocene"]["screenshots"] = [
                str(desktop),
                str(mobile),
            ]

    def execute(self) -> dict[str, Any]:
        self.preflight()
        self.create_resources()
        self.run_core_matrix()
        self.run_clients()
        self.wait_container_health("lifecycle", timeout=120)
        raw_ps = self.compose("ps", "-a", "--format", "json").stdout.strip()
        try:
            parsed_ps = json.loads(raw_ps)
            final_ps = parsed_ps if isinstance(parsed_ps, list) else [parsed_ps]
        except json.JSONDecodeError:
            final_ps = [
                json.loads(line) for line in raw_ps.splitlines() if line.strip()
            ]
        self.summary["compose"]["final_ps"] = final_ps
        self.summary["cleanup"] = {
            "project": self.project,
            "networks": list(self.networks.values()),
            "volumes": list(self.volumes.values()),
            "local_image": self.candystore_image,
            "ephemeral_secret": "remove after stack teardown",
        }
        return self.summary

    def finish_cleanup_evidence(self) -> None:
        self.cleanup()
        containers_after = self.container_inventory()
        protected_after = {
            name: name in containers_after for name in PROTECTED_BASELINE_CONTAINERS
        }
        if protected_after != self.summary["isolation"]["protected_before"]:
            raise LiveProofError("an unrelated protected baseline container changed")
        remaining = self.owned_resource_inventory()
        if (
            remaining["containers"]
            or remaining["networks"]
            or remaining["volumes"]
            or remaining["local_image_present"]
        ):
            raise LiveProofError(
                f"isolated live resources remain after cleanup: {remaining}"
            )
        self.summary["isolation"]["containers_after"] = containers_after
        self.summary["isolation"]["protected_after"] = protected_after
        self.summary["cleanup"]["completed"] = True
        self.summary["cleanup"]["ephemeral_secret_removed"] = (
            not self.secret_file.exists() and not self.secret_dir.exists()
        )
        self.summary["cleanup"]["remaining"] = remaining


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--proof-dir",
        type=Path,
        help="preserve the machine proof, Momo receipt, and review artifact here",
    )
    parser.add_argument(
        "--screenshots-dir",
        type=Path,
        help="run desktop/mobile browser proof and preserve screenshots here",
    )
    args = parser.parse_args()
    harness = Harness(args.screenshots_dir, args.proof_dir)
    try:
        summary = harness.execute()
        harness.finish_cleanup_evidence()
        if harness.proof_dir is not None:
            (harness.proof_dir / "proof.json").write_text(
                json.dumps(summary, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
        return 0
    except (LiveProofError, OSError, subprocess.TimeoutExpired, ValueError) as exc:
        print(f"Lifecycle live matrix failed: {exc}", file=sys.stderr, flush=True)
        diagnostics = harness.compose(
            "logs",
            "--no-color",
            "--tail",
            "120",
            "lifecycle",
            "lifecycle-migrate",
            "lifecycle-bootstrap",
            "bloodbank-nats",
            "nats-init",
            "candystore",
            "candystore-daprd",
            "candystore-postgres",
            "dapr-placement",
            check=False,
        )
        if diagnostics.stdout.strip():
            print(diagnostics.stdout, file=sys.stderr, flush=True)
        database = harness.compose(
            "exec",
            "-T",
            "candystore-postgres",
            "psql",
            "-U",
            "candystore",
            "-d",
            "candystore",
            "-At",
            "-c",
            (
                "SELECT 'events=' || COUNT(*) FROM events;"
                "SELECT 'projections=' || COUNT(*) FROM lifecycle_projections;"
                "SELECT 'receipts=' || COUNT(*) FROM lifecycle_projection_receipts;"
                "SELECT 'dead_letters=' || COUNT(*) FROM dead_letter;"
                "SELECT COALESCE(reason, '') || ':' || COALESCE(error, '') "
                "FROM dead_letter ORDER BY id DESC LIMIT 5;"
            ),
            check=False,
        )
        if database.stdout.strip():
            print(
                "Candystore database diagnostics:\n" + database.stdout,
                file=sys.stderr,
                flush=True,
            )
        for label, port, path in (
            ("subscription", harness.ports["candystore"], "/dapr/subscribe"),
            ("dapr metadata", harness.ports["candystore_dapr"], "/v1.0/metadata"),
        ):
            try:
                code, body = http_json(f"http://127.0.0.1:{port}{path}")
                print(
                    f"Candystore {label}: status={code} body={body!r}",
                    file=sys.stderr,
                    flush=True,
                )
            except OSError as diagnostic_error:
                print(
                    f"Candystore {label} unavailable: {diagnostic_error}",
                    file=sys.stderr,
                    flush=True,
                )
        return 1
    finally:
        harness.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
