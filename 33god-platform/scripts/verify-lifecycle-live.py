#!/usr/bin/env python3
"""Run the isolated live Lifecycle/client failure-proof matrix.

Every Docker resource is uniquely named and removed explicitly during cleanup.
Registry images are exercised only by immutable digest.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
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
    "sha256:f15d5934d1007f83fe46348a059c59ade8262dbd3b067f629633d28693843abf"
)
NATS_BOX_IMAGE = (
    "natsio/nats-box@"
    "sha256:0784ab710aefaf6ef037ed797ee7dcde613c6ad208c4dbff1945fc7c1b5b5375"
)
ACTOR_ID = "operator:33god-bootstrap"
CAPABILITY_ID = "cap:33god-platform:lifecycle-command"
REPO = "delorenj/33GOD"
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
    def __init__(self, screenshots_dir: Path | None) -> None:
        self.suffix = uuid.uuid4().hex[:10]
        self.project = f"aion-lifecycle-{self.suffix}"
        self.lifecycle_id = f"lc_aion_{self.suffix}"
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
        self.created_resources = False
        self.cleaned = False
        self.prestart_snapshot_event_id: str | None = None
        self.prestart_verdict_command_id: str | None = None
        self.containers_before: list[str] = []
        self.summary: dict[str, Any] = {
            "project": self.project,
            "lifecycle_id": self.lifecycle_id,
            "image": LIFECYCLE_IMAGE,
            "bloodbank_commit": "155f2d774964d1c73694ce2c576fe5f50b91eefb",
            "invariants": {},
            "seams": {},
        }

    def compose(self, *args: str, check: bool = True, timeout: float = 180):
        return run(
            [
                "docker",
                "compose",
                "--project-name",
                self.project,
                "--file",
                str(COMPOSE_FILE),
                *args,
            ],
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

    def psql(self, sql: str) -> str:
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
        ).stdout.strip()

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
              'observed_through', observed_through
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

    def command_result(self, event_id: str) -> dict[str, Any] | None:
        raw = self.psql(
            """
            SELECT json_build_object(
              'verdict', verdict, 'mutated', mutated, 'reason_code', reason_code,
              'expected_state_version', expected_state_version,
              'observed_state_version', observed_state_version,
              'resulting_state_version', resulting_state_version,
              'command_id', command_id, 'idempotency_key', idempotency_key
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
              SELECT event_sequence, event_id::text, subject,
                     published_at IS NOT NULL AS published, published_at
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
        return wait_for(
            f"command {event_id} verdict {verdict}",
            lambda: (
                value
                if (value := self.command_result(event_id))
                and value.get("verdict") == verdict
                else None
            ),
        )

    def wait_state_version(
        self, minimum: int, status: str | None = None
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
        causation_id: str | None = None,
    ) -> dict[str, Any]:
        requested_at = wire_time()
        if capability_version is None:
            capability_version = self.capability_version()
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
            "correlationid": stable_uuid(f"{self.suffix}:correlation:{label}"),
            "causationid": causation_id,
            "producer": "lifecycle-live-matrix",
            "service": "lifecycle-live-matrix",
            "domain": "lifecycle",
            "schemaref": "bloodbank.v1.lifecycle.intent.submit.command.v1",
            "kind": "command",
            "actor": {"type": "agent_api", "agent_id": actor_id},
            "command_id": stable_uuid(f"{self.suffix}:command:{label}"),
            "idempotency_key": f"lifecycle-live-matrix:{self.suffix}:{label}",
            "delivery": "single_consumer",
            "data": {
                "contract_version": 1,
                "lifecycle_id": self.lifecycle_id,
                "repo": REPO,
                "expected_state_version": expected_state_version,
                "intent": {"name": "transition", "target": target, "parameters": {}},
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

        print("[live] proving Holocene/Momo offline authority progression", flush=True)
        first = self.command(
            "clients-offline", expected_state_version=1, target="waiting"
        )
        self.publish(first)
        first_result = self.wait_command(first["id"], "applied")
        progressed = self.wait_state_version(2, "waiting")
        obligation = next(
            (
                item
                for item in progressed.get("obligations", [])
                if item.get("id") == "independent-review"
            ),
            None,
        )
        waiting_frontier = next(
            (
                item
                for item in progressed.get("legal_frontier", [])
                if item.get("id") == "transition:waiting:active"
            ),
            None,
        )
        if (
            obligation is None
            or obligation.get("status") != "pending"
            or waiting_frontier is None
            or waiting_frontier.get("allowed") is not False
            or waiting_frontier.get("reason_code") != "PENDING_OBLIGATIONS"
        ):
            raise LiveProofError(
                "first WAITING authority snapshot did not expose the pending "
                "obligation and disallowed frontier"
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

        print("[live] proving pending-obligation progression rejection", flush=True)
        pending_before = self.counts()
        premature = self.command(
            "pending-obligation-reject",
            expected_state_version=progressed["state_version"],
            target="active",
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
        if stale_result["mutated"] or after_stale["state_version"] != 2:
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
            expected_state_version=2,
            target="active",
            actor_id="agent:intruder",
            capability_id="cap:missing",
            capability_version=capability_version,
        )
        self.publish(unauthorized)
        unauthorized_result = self.wait_command(unauthorized["id"], "unauthorized")
        after_unauthorized = self.state()
        if unauthorized_result["mutated"] or after_unauthorized["state_version"] != 2:
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
            "[live] proving NATS outage/recovery and ordered eventual publication",
            flush=True,
        )
        outage_before_state = self.state()
        outage_before_counts = self.counts()
        events_before = int(self.stream_info("BLOODBANK_EVENTS")["state"]["messages"])
        commands_before = int(
            self.stream_info("BLOODBANK_COMMANDS")["state"]["messages"]
        )
        self.compose("stop", "bloodbank-nats")
        degraded = self.wait_health("/readyz", 503)
        still_live = self.wait_health("/livez", 200)
        time.sleep(1)
        if self.state() != outage_before_state:
            raise LiveProofError("NATS outage rewrote committed Lifecycle state")
        if self.counts()["history"] != outage_before_counts["history"]:
            raise LiveProofError("NATS outage changed transition history")
        self.compose("start", "bloodbank-nats")
        self.wait_container_health("bloodbank-nats")
        recovered = self.wait_health("/readyz", 200, timeout=90)
        current = self.state()
        if current["status"] != "waiting":
            raise LiveProofError(
                f"expected guarded waiting state before recovery command: {current}"
            )
        recovery_observation = self.observation("nats-recovery")
        self.publish(recovery_observation)
        wait_for(
            "post-recovery observation commit and outbox publication",
            lambda: (
                value
                if (value := self.counts())["observations"]
                == outage_before_counts["observations"] + 1
                and value["outbox_pending"] == 0
                else None
            ),
            timeout=90,
        )
        observation_state = self.wait_state_version(
            current["state_version"] + 1, "waiting"
        )
        guarded = next(
            item
            for item in observation_state["legal_frontier"]
            if item["id"] == "transition:waiting:active"
        )
        if (
            guarded["allowed"] is not False
            or guarded["reason_code"] != "PENDING_OBLIGATIONS"
        ):
            raise LiveProofError(
                "post-recovery reconcile bypassed the pending obligation"
            )
        current = observation_state
        recovery_command = self.command(
            "nats-recovery",
            expected_state_version=current["state_version"],
            target="active",
        )
        self.publish(recovery_command)
        recovery_result = self.wait_command(recovery_command["id"], "illegal")
        waiting = self.state()
        if waiting != current or recovery_result["mutated"]:
            raise LiveProofError("post-outage guarded command mutated authority state")
        wait_for("empty committed outbox", lambda: self.counts()["outbox_pending"] == 0)
        rows = self.outbox_rows()
        sequences = [int(item["event_sequence"]) for item in rows]
        published_times = [item["published_at"] for item in rows]
        if sequences != sorted(set(sequences)) or not all(
            item["published"] for item in rows
        ):
            raise LiveProofError(
                "outbox ordering/uniqueness/eventual publication failed"
            )
        if published_times != sorted(published_times):
            raise LiveProofError(
                "per-lifecycle publication timestamps are out of sequence"
            )
        events_after = int(self.stream_info("BLOODBANK_EVENTS")["state"]["messages"])
        commands_after = int(
            self.stream_info("BLOODBANK_COMMANDS")["state"]["messages"]
        )
        if events_after <= events_before:
            raise LiveProofError(
                "recovered NATS received no eventual Lifecycle publication"
            )
        self.summary["invariants"]["6_nats_outage_recovery"] = {
            "ready_during_outage": degraded,
            "live_during_outage": still_live,
            "ready_after_recovery": recovered,
            "committed_state_before": outage_before_state,
            "result": recovery_result,
            "recovery_observation_event_id": recovery_observation["id"],
            "state_after": waiting,
            "event_messages_before": events_before,
            "event_messages_after": events_after,
            "command_reply_messages_before": commands_before,
            "command_reply_messages_after": commands_after,
            "outbox_sequences": sequences,
            "outbox_pending": 0,
        }

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
        volume_after = self.docker(
            "inspect", "--format", mount_format, postgres_container
        ).stdout.strip()
        if volume_before != self.volumes["lifecycle"] or volume_after != volume_before:
            raise LiveProofError(
                "Lifecycle PostgreSQL did not retain its dedicated volume"
            )
        if self.state() != persistent_state or self.counts() != persistent_counts:
            raise LiveProofError(
                "state did not survive service/PostgreSQL process restart"
            )
        self.summary["invariants"]["7_postgres_persistence"] = {
            "volume": volume_after,
            "state": persistent_state,
            "counts": persistent_counts,
        }

        snapshots = [
            item
            for item in self.outbox_rows()
            if item["subject"] == "bloodbank.evt.v1.lifecycle.snapshot.updated"
        ]
        if not snapshots:
            raise LiveProofError("authority emitted no pre-Candystore snapshot")
        self.prestart_snapshot_event_id = snapshots[-1]["event_id"]
        self.prestart_verdict_command_id = premature["command_id"]

    def run_clients(self) -> None:
        print("[live] starting durable Candystore projection", flush=True)
        self.compose(
            "up",
            "-d",
            "--build",
            "--wait",
            "--wait-timeout",
            "180",
            "candystore-daprd",
            timeout=300,
        )
        authority = self.state()
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
                "authority snapshot"
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
            "[live] exercising Momo obligation invocation and completion evidence",
            flush=True,
        )
        momo_script = SOURCE_ROOT / "momo" / "skill" / "scripts" / "lifecycle_client.py"
        with tempfile.TemporaryDirectory(prefix=f"aion-momo-{self.suffix}-") as temp:
            temp_dir = Path(temp)
            snapshot_path = temp_dir / "snapshot.json"
            evidence_path = temp_dir / "evidence.json"
            invocation_plan_path = temp_dir / "invocation-plan.json"
            invocation_path = temp_dir / "invocation.json"
            completion_path = temp_dir / "completion.json"
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
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
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
            invocation_plan_path.write_text(json.dumps(invocation), encoding="utf-8")
            invocation_path.write_text(
                json.dumps(invocation["invocation_command"]), encoding="utf-8"
            )
            publish_env = os.environ.copy()
            publish_env.update(
                {
                    "BLOODBANK_HOME": str(SOURCE_ROOT / "bloodbank"),
                    "BLOODBANK_NATS_HOST": "127.0.0.1",
                    "BLOODBANK_NATS_PORT": str(self.ports["nats"]),
                }
            )
            invocation_publish = run(
                [
                    sys.executable,
                    str(momo_script),
                    "publish",
                    "--envelope",
                    str(invocation_path),
                ],
                env=publish_env,
            )
            if (
                "bloodbank.cmd.v1.agent.invocation.start"
                not in invocation_publish.stdout
            ):
                raise LiveProofError(
                    "Momo did not publish the canonical invocation subject"
                )
            evidence_path.write_text(
                json.dumps(
                    {
                        "kind": "skill_completion",
                        "outcome": "completed",
                        "artifact_id": f"review-report:{self.suffix}",
                        "artifact_sha256": "a" * 64,
                        "summary": "Independent review completed with concrete artifact evidence.",
                    }
                ),
                encoding="utf-8",
            )
            completion = json.loads(
                run(
                    [
                        sys.executable,
                        str(momo_script),
                        "complete-obligation",
                        "--invocation-plan",
                        str(invocation_plan_path),
                        "--completed-at",
                        wire_time(),
                        "--evidence",
                        str(evidence_path),
                    ]
                ).stdout
            )
            completion_event = completion["completion_evidence"]
            if (
                completion_event["data"]["obligation_id"] != pending_obligation["id"]
                or completion_event["data"]["target_actor_id"]
                != pending_obligation["owner_id"]
                or completion_event["causationid"]
                != invocation["invocation_command"]["id"]
                or completion_event["data"]["evidence"]["outcome"] != "completed"
            ):
                raise LiveProofError(
                    "Momo completion evidence lost obligation identity"
                )
            completion_path.write_text(json.dumps(completion_event), encoding="utf-8")
            completion_publish = run(
                [
                    sys.executable,
                    str(momo_script),
                    "publish",
                    "--envelope",
                    str(completion_path),
                ],
                env=publish_env,
            )
            momo_state = self.wait_state_version(
                snapshot["state_version"] + 1, "active"
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
            "blocked_frontier": blocked_frontier,
            "completion_subject": completion_event["subject"],
            "completion_event_id": completion_event["id"],
            "completion_publish": completion_publish.stdout.strip(),
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
        self.summary["seams"]["holocene"] = {
            "read_state_version": api_projection["state_version"],
            "publish_receipt": queued,
            "authoritative_capability_version": grant["capability_version"],
            "command_result": holocene_result,
            "rendered_state_version": rendered["state_version"],
            "rendered_status": rendered["status"],
            "verdict_count": len(rendered["command_verdicts"]),
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
        "--screenshots-dir",
        type=Path,
        help="run desktop/mobile browser proof and preserve screenshots here",
    )
    args = parser.parse_args()
    harness = Harness(args.screenshots_dir)
    try:
        summary = harness.execute()
        harness.finish_cleanup_evidence()
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
