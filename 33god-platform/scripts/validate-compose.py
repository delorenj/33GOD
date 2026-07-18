#!/usr/bin/env python3
"""Render and semantically validate the integrated 33GOD Compose model."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


PROFILE_SERVICES = {
    "default": {
        "bloodbank-nats",
        "nats-init",
        "lifecycle-postgres",
        "lifecycle-migrate",
        "lifecycle-bootstrap",
        "lifecycle",
        "dapr-placement",
        "candystore-postgres",
        "candystore",
        "candystore-daprd",
        "holocene-api-preflight",
        "holocene-web",
    },
    "tools": {
        "bloodbank-nats",
        "nats-init",
        "lifecycle-postgres",
        "lifecycle-migrate",
        "lifecycle-bootstrap",
        "lifecycle",
        "dapr-placement",
        "candystore-postgres",
        "candystore",
        "candystore-daprd",
        "holocene-api-preflight",
        "holocene-web",
        "pjangler-cli",
        "pjangler-mcp",
    },
    "full": {
        "bloodbank-nats",
        "nats-init",
        "lifecycle-postgres",
        "lifecycle-migrate",
        "lifecycle-bootstrap",
        "lifecycle",
        "dapr-placement",
        "candystore-postgres",
        "candystore",
        "candystore-daprd",
        "holocene-api-preflight",
        "holocene-web",
        "pjangler-cli",
        "pjangler-mcp",
    },
    "cloud": {
        "bloodbank-nats",
        "nats-init",
        "lifecycle-postgres",
        "lifecycle-migrate",
        "lifecycle-bootstrap",
        "lifecycle",
        "dapr-placement",
        "candystore-postgres",
        "candystore",
        "candystore-daprd",
        "holocene-api-preflight",
        "holocene-web",
        "cloud-unsupported",
    },
}

FORBIDDEN_SERVICES = {
    "platform-ready",
    "postgres",
    "daprd",
    "daprd-candystore",
    "bloodbank-postgres",
    "bloodbank-candystore",
    "bloodbank-daprd-candystore",
    "holocene-api",
}

EXPECTED_VOLUMES = {
    "bloodbank-nats-data": "bloodbank_bloodbank-nats-data",
    "lifecycle-pgdata": "lifecycle_pgdata",
    "candystore-pgdata": "candystore_pgdata",
    "holocene-node-modules": "holocene_holocene_node_modules",
    "holocene-web-node-modules": "holocene_holocene_web_node_modules",
    "holocene-web-next": "holocene_holocene_web_next",
}

EXPECTED_NETWORKS = {
    "bloodbank-network",
    "lifecycle-internal",
    "candystore-internal",
    "proxy",
}

EXPECTED_SERVICE_NETWORKS = {
    "bloodbank-nats": {"bloodbank-network"},
    "nats-init": {"bloodbank-network"},
    "lifecycle-postgres": {"lifecycle-internal"},
    "lifecycle-migrate": {"lifecycle-internal"},
    "lifecycle-bootstrap": {"lifecycle-internal"},
    "lifecycle": {"lifecycle-internal", "bloodbank-network"},
    "dapr-placement": {"bloodbank-network"},
    "candystore-postgres": {"candystore-internal"},
    "candystore": {"candystore-internal", "proxy"},
    "candystore-daprd": {"candystore-internal", "bloodbank-network"},
    "holocene-api-preflight": {"candystore-internal"},
    "holocene-web": {"proxy"},
    "pjangler-cli": {"default"},
    "pjangler-mcp": {"default"},
    "cloud-unsupported": set(),
}

LIFECYCLE_IMAGE = (
    "ghcr.io/delorenj/lifecycle@"
    "sha256:982a25126a292dba8a6af43c38a4b4c136726c054a0076ba56a8d2055974ec67"
)

EXPECTED_PINNED_IMAGES = {
    "bloodbank-nats": "nats@sha256:b83efabe3e7def1e0a4a31ec6e078999bb17c80363f881df35edc70fcb6bb927",
    "nats-init": "natsio/nats-box@sha256:0784ab710aefaf6ef037ed797ee7dcde613c6ad208c4dbff1945fc7c1b5b5375",
    "lifecycle-postgres": "postgres@sha256:20edbde7749f822887a1a022ad526fde0a47d6b2be9a8364433605cf65099416",
    "lifecycle-migrate": LIFECYCLE_IMAGE,
    "lifecycle-bootstrap": LIFECYCLE_IMAGE,
    "lifecycle": LIFECYCLE_IMAGE,
    "dapr-placement": "daprio/dapr@sha256:0d9dbe22d81dad91f3cde6f85a31ad0185ceaa55f82a4ba29cc46020f31a79d4",
    "candystore-postgres": "postgres@sha256:20edbde7749f822887a1a022ad526fde0a47d6b2be9a8364433605cf65099416",
    "candystore-daprd": "daprio/daprd@sha256:286806d0eac7edc37c310427e7813da403257f51395eeec912cdd2889f9a9b37",
    "holocene-api-preflight": "curlimages/curl@sha256:9a1ed35addb45476afa911696297f8e115993df459278ed036182dd2cd22b67b",
    "holocene-web": "node@sha256:1031993481795705055273f2eef0c24597abdcb277d6e058c82f78cbbdef92a6",
    "pjangler-cli": "node@sha256:1031993481795705055273f2eef0c24597abdcb277d6e058c82f78cbbdef92a6",
    "pjangler-mcp": "node@sha256:1031993481795705055273f2eef0c24597abdcb277d6e058c82f78cbbdef92a6",
    "cloud-unsupported": "alpine@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc",
}

EXPECTED_LIFECYCLE_BOOTSTRAP_ENV = {
    "LIFECYCLE_BOOTSTRAP_ID",
    "LIFECYCLE_BOOTSTRAP_NAME",
    "LIFECYCLE_BOOTSTRAP_REPO",
    "LIFECYCLE_BOOTSTRAP_ACTOR_ID",
    "LIFECYCLE_BOOTSTRAP_CAPABILITY_ID",
    "LIFECYCLE_BOOTSTRAP_AS_OF",
    "LIFECYCLE_BOOTSTRAP_MODE",
}

EXPECTED_CANDYSTORE_EVENT_ENV = {
    "SUBSCRIBE_PUBSUB": "bloodbank-pubsub",
    "SUBSCRIBE_TOPIC": "bloodbank.evt.v1.>",
    "SUBSCRIBE_ROUTE": "/events/all",
    "BLOODBANK_SCHEMAS_DIR": "/bloodbank-schemas",
}

EXPECTED_CANDYSTORE_DAPRD_COMMAND = [
    "./daprd",
    "--app-id=candystore",
    "--dapr-http-port=3500",
    "--dapr-grpc-port=50001",
    "--app-port=3001",
    "--app-channel-address=candystore-app",
    "--app-protocol=http",
    "--resources-path=/components",
    "--placement-host-address=dapr-placement:50005",
    "--log-level=info",
]

EXPECTED_HOLOCENE_LABELS = {
    "traefik.enable": "true",
    "traefik.http.routers.holocene-web.entrypoints": "websecure",
    "traefik.http.routers.holocene-web.rule": "Host(`holocene.delo.sh`)",
    "traefik.http.routers.holocene-web.priority": "300",
    "traefik.http.routers.holocene-web.middlewares": "google-auth@file",
    "traefik.http.services.holocene-web.loadbalancer.server.port": "3001",
    "traefik.http.routers.holocene-web.service": "holocene-web",
    "traefik.http.routers.holocene-web.tls": "true",
    "traefik.http.routers.holocene-web.tls.certresolver": "letsencrypt",
    "traefik.http.routers.holocene-hq.rule": "Host(`holocene.delo.sh`) && (PathPrefix(`/hq`) || PathPrefix(`/_next/static`))",
    "traefik.http.routers.holocene-hq.priority": "350",
    "traefik.http.routers.holocene-hq.entrypoints": "websecure",
    "traefik.http.routers.holocene-hq.service": "holocene-web",
    "traefik.http.routers.holocene-hq.tls": "true",
    "traefik.http.routers.holocene-hq.tls.certresolver": "letsencrypt",
    "traefik.docker.network": "proxy",
}


def _service(model: dict[str, Any], name: str) -> dict[str, Any]:
    return model.get("services", {}).get(name, {})


def _mount(service: dict[str, Any], target: str) -> dict[str, Any] | None:
    return next(
        (
            mount
            for mount in service.get("volumes", [])
            if mount.get("target") == target
        ),
        None,
    )


def _aliases(service: dict[str, Any], network: str) -> set[str]:
    config = service.get("networks", {}).get(network) or {}
    return set(config.get("aliases", []))


def _published_ports(service: dict[str, Any]) -> set[tuple[int, int, str]]:
    return {
        (
            int(port.get("published", 0)),
            int(port.get("target", 0)),
            port.get("host_ip", ""),
        )
        for port in service.get("ports", [])
    }


def _dependency(service: dict[str, Any], dependency: str) -> str | None:
    value = service.get("depends_on", {}).get(dependency)
    if isinstance(value, dict):
        return value.get("condition")
    return None


def validate_model(
    model_name: str, model: dict[str, Any], source_root: Path
) -> list[str]:
    """Return every semantic violation in one rendered Compose model."""
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(f"{model_name}: {message}")

    services = model.get("services", {})
    actual_services = set(services)
    expected_services = PROFILE_SERVICES[model_name]
    require(
        actual_services == expected_services,
        f"service set mismatch (missing={sorted(expected_services - actual_services)}, extra={sorted(actual_services - expected_services)})",
    )
    for forbidden in sorted(FORBIDDEN_SERVICES & actual_services):
        errors.append(f"{model_name}: forbidden service {forbidden}")
    for name, expected_image in EXPECTED_PINNED_IMAGES.items():
        if name in services:
            require(
                services[name].get("image") == expected_image,
                f"service {name} must use immutable image {expected_image}",
            )
    require(
        all("container_name" not in service for service in services.values()),
        "services must remain Compose-project scoped without fixed container_name values",
    )

    candystore_services = {name for name in actual_services if "candystore" in name}
    require(
        candystore_services
        == {"candystore-postgres", "candystore", "candystore-daprd"},
        f"Candystore must have exactly postgres/app/daprd, got {sorted(candystore_services)}",
    )

    networks = model.get("networks", {})
    allowed_networks = EXPECTED_NETWORKS | (
        {"default"} if model_name in {"tools", "full"} else set()
    )
    require(
        set(networks) == allowed_networks,
        f"network set must be {sorted(allowed_networks)}",
    )
    for name in EXPECTED_NETWORKS:
        network = networks.get(name, {})
        require(
            bool(network.get("name")),
            f"network {name} must resolve to a non-empty caller-selectable name",
        )
        require(network.get("external") is True, f"network {name} must be external")
    external_network_names = [
        networks[name].get("name") for name in EXPECTED_NETWORKS if name in networks
    ]
    require(
        len(external_network_names) == len(set(external_network_names)),
        "external network resource names must be unique",
    )

    for name, service in services.items():
        actual_memberships = set(service.get("networks", {}))
        expected_memberships = EXPECTED_SERVICE_NETWORKS.get(name)
        if expected_memberships is not None:
            require(
                actual_memberships == expected_memberships,
                f"service {name} network memberships must be exactly {sorted(expected_memberships)}",
            )

    volumes = model.get("volumes", {})
    require(
        set(volumes) == set(EXPECTED_VOLUMES),
        "only the six adopted named volumes may be declared",
    )
    for key in EXPECTED_VOLUMES:
        volume = volumes.get(key, {})
        require(
            bool(volume.get("name")),
            f"volume {key} must resolve to a non-empty caller-selectable name",
        )
        require(
            volume.get("external") is True,
            f"volume {key} must be external to prevent empty replacement data",
        )
    external_volume_names = [
        volumes[name].get("name") for name in EXPECTED_VOLUMES if name in volumes
    ]
    require(
        len(external_volume_names) == len(set(external_volume_names)),
        "external volume resource names must be unique",
    )

    nats_ports = _published_ports(_service(model, "bloodbank-nats"))
    require(
        {(target, host) for _, target, host in nats_ports}
        == {(4222, "127.0.0.1"), (8222, "127.0.0.1")},
        f"NATS must publish only loopback targets 4222 and 8222; rendered {sorted(nats_ports)}",
    )
    require(
        {
            (target, host)
            for _, target, host in _published_ports(_service(model, "dapr-placement"))
        }
        == {(50005, "127.0.0.1")},
        "Dapr placement must publish only loopback target 50005",
    )
    require(
        {
            (target, host)
            for _, target, host in _published_ports(
                _service(model, "candystore-postgres")
            )
        }
        == {(5432, "127.0.0.1")},
        "Candystore PostgreSQL must publish only loopback target 5432",
    )
    require(
        {
            (target, host)
            for _, target, host in _published_ports(_service(model, "candystore"))
        }
        == {(3001, "127.0.0.1")},
        "Candystore app must publish only loopback target 3001",
    )
    require(
        {
            (target, host)
            for _, target, host in _published_ports(_service(model, "candystore-daprd"))
        }
        == {(3500, "127.0.0.1")},
        "Candystore daprd must publish only loopback target 3500",
    )
    require(
        {
            (target, host)
            for _, target, host in _published_ports(_service(model, "lifecycle"))
        }
        == {(8080, "127.0.0.1")},
        "Lifecycle must publish only loopback target 8080",
    )
    published_bindings = [
        (port.get("host_ip", ""), int(port.get("published", 0)))
        for service in services.values()
        for port in service.get("ports", [])
    ]
    require(
        all(0 < published <= 65535 for _, published in published_bindings),
        "all caller-selected published ports must be valid",
    )
    require(
        len(published_bindings) == len(set(published_bindings)),
        "caller-selected published ports must not collide on the same bind address",
    )
    for name, service in services.items():
        require(
            all(
                int(port.get("published", 0)) != 4000
                for port in service.get("ports", [])
            ),
            f"service {name} must not publish the host Holocene API port 4000",
        )

    nats_mount = _mount(_service(model, "bloodbank-nats"), "/data/jetstream")
    require(
        nats_mount is not None and nats_mount.get("source") == "bloodbank-nats-data",
        "NATS must use the adopted JetStream volume",
    )

    init = _service(model, "nats-init")
    require(
        _dependency(init, "bloodbank-nats") == "service_healthy",
        "nats-init must wait for healthy NATS",
    )
    for relative, target in (
        ("compose/nats/streams.json", "/work/streams.json"),
        ("compose/nats/init.sh", "/work/init.sh"),
    ):
        mount = _mount(init, target)
        expected_source = str((source_root / "bloodbank" / relative).resolve())
        require(
            mount is not None
            and mount.get("source") == expected_source
            and mount.get("read_only") is True,
            f"nats-init must read-only mount Bloodbank {relative}",
        )
    require(
        set(init.get("entrypoint", [])) == {"/bin/sh", "/work/init.sh"},
        "nats-init must execute Bloodbank's tracked initializer",
    )
    require(
        init.get("environment", {}).get("NATS_URL") == "nats://nats:4222",
        "nats-init must target canonical NATS DNS and port",
    )
    require(
        _service(model, "bloodbank-nats")
        .get("environment", {})
        .get("BLOODBANK_NATS_URL")
        == "nats://nats:4222",
        "Bloodbank NATS service metadata must retain canonical NATS DNS and port",
    )
    require(
        _aliases(_service(model, "bloodbank-nats"), "bloodbank-network") >= {"nats"},
        "NATS must retain the nats DNS alias",
    )
    placement = _service(model, "dapr-placement")
    require(
        _aliases(placement, "bloodbank-network") >= {"dapr-placement"},
        "placement must retain the dapr-placement DNS alias",
    )
    require(
        placement.get("command", []) == ["./placement", "--port", "50005"],
        "placement must listen on canonical port 50005",
    )

    lifecycle_names = {name for name in actual_services if name.startswith("lifecycle")}
    require(
        lifecycle_names
        == {
            "lifecycle-postgres",
            "lifecycle-migrate",
            "lifecycle-bootstrap",
            "lifecycle",
        },
        f"Lifecycle must have exactly postgres/migrate/bootstrap/serve, got {sorted(lifecycle_names)}",
    )
    lifecycle_secret = model.get("secrets", {}).get("lifecycle-postgres-password", {})
    require(
        lifecycle_secret.get("file")
        == os.environ.get(
            "LIFECYCLE_POSTGRES_PASSWORD_FILE",
            "/run/secrets/33god-lifecycle-postgres-password",
        ),
        "Lifecycle PostgreSQL password must come from the dedicated file-backed Compose secret",
    )

    def require_lifecycle_secret(service_name: str) -> None:
        mounted = _service(model, service_name).get("secrets", [])
        require(
            mounted
            == [
                {
                    "source": "lifecycle-postgres-password",
                    "target": "/run/secrets/lifecycle-postgres-password",
                }
            ],
            f"{service_name} must mount only the dedicated Lifecycle PostgreSQL secret",
        )

    lifecycle_postgres = _service(model, "lifecycle-postgres")
    require_lifecycle_secret("lifecycle-postgres")
    require(
        not lifecycle_postgres.get("ports"),
        "Lifecycle PostgreSQL must not publish a host port",
    )
    require(
        lifecycle_postgres.get("environment", {})
        == {
            "POSTGRES_USER": "lifecycle",
            "POSTGRES_DB": "lifecycle",
            "POSTGRES_PASSWORD_FILE": "/run/secrets/lifecycle-postgres-password",
        },
        "Lifecycle PostgreSQL must use only its dedicated database and password file",
    )
    require(
        _aliases(lifecycle_postgres, "lifecycle-internal") >= {"lifecycle-postgres"},
        "Lifecycle PostgreSQL must retain its private DNS alias",
    )
    lifecycle_pg_mount = _mount(lifecycle_postgres, "/var/lib/postgresql/data")
    require(
        lifecycle_pg_mount is not None
        and lifecycle_pg_mount.get("source") == "lifecycle-pgdata",
        "Lifecycle PostgreSQL must use only the dedicated lifecycle-pgdata volume",
    )

    for name, cli in (
        ("lifecycle-migrate", "migrate"),
        ("lifecycle-bootstrap", "bootstrap"),
        ("lifecycle", "serve"),
    ):
        service = _service(model, name)
        require_lifecycle_secret(name)
        require(
            "build" not in service, f"{name} must never contain a Compose build section"
        )
        require(
            service.get("entrypoint") == ["/bin/sh", "-eu", "-c"],
            f"{name} must fail closed through the strict secret-loading entrypoint",
        )
        command = "\n".join(service.get("command", []))
        require(
            f"python -m main {cli}" in command,
            f"{name} must execute Lifecycle's published {cli} CLI",
        )
        require(
            "/run/secrets/lifecycle-postgres-password" in command
            and "LIFECYCLE_DATABASE_URL" in command,
            f"{name} must construct its isolated database URL from the mounted secret",
        )
        require(
            "candystore" not in command.lower(),
            f"{name} must not reference Candystore storage",
        )

    migrate = _service(model, "lifecycle-migrate")
    bootstrap = _service(model, "lifecycle-bootstrap")
    lifecycle = _service(model, "lifecycle")
    require(migrate.get("restart") == "no", "Lifecycle migration must be a one-shot")
    require(
        _dependency(migrate, "lifecycle-postgres") == "service_healthy",
        "Lifecycle migration must wait for healthy dedicated PostgreSQL",
    )
    require(bootstrap.get("restart") == "no", "Lifecycle bootstrap must be a one-shot")
    require(
        _dependency(bootstrap, "lifecycle-migrate") == "service_completed_successfully",
        "Lifecycle bootstrap must wait for successful migration",
    )
    require(
        set(bootstrap.get("environment", {})) == EXPECTED_LIFECYCLE_BOOTSTRAP_ENV
        and all(
            str(value).strip() for value in bootstrap.get("environment", {}).values()
        ),
        "Lifecycle bootstrap must receive the complete deterministic identity/spec input set",
    )
    bootstrap_command = "\n".join(bootstrap.get("command", []))
    for flag in (
        "--lifecycle-id",
        "--name",
        "--repo",
        "--actor-id",
        "--capability-id",
        "--as-of",
        "--mode",
    ):
        require(flag in bootstrap_command, f"Lifecycle bootstrap must pass {flag}")

    require(
        lifecycle.get("restart") == "unless-stopped",
        "Lifecycle serve must restart unless explicitly stopped",
    )
    require(
        _dependency(lifecycle, "lifecycle-postgres") == "service_healthy",
        "Lifecycle serve must wait for healthy dedicated PostgreSQL",
    )
    require(
        _dependency(lifecycle, "lifecycle-bootstrap")
        == "service_completed_successfully",
        "Lifecycle serve must wait for successful bootstrap",
    )
    require(
        _dependency(lifecycle, "bloodbank-nats") == "service_healthy",
        "Lifecycle serve must wait for healthy canonical NATS",
    )
    require(
        _dependency(lifecycle, "nats-init") == "service_completed_successfully",
        "Lifecycle serve must wait for canonical stream initialization",
    )
    require(
        lifecycle.get("environment", {})
        == {
            "BLOODBANK_NATS_URLS": "nats://nats:4222",
            "LIFECYCLE_INSTANCE": "33god-platform",
            "LIFECYCLE_HTTP_HOST": "0.0.0.0",
            "LIFECYCLE_HTTP_PORT": "8080",
        },
        "Lifecycle serve must expose only its narrow runtime configuration",
    )
    lifecycle_health = " ".join(
        str(item) for item in lifecycle.get("healthcheck", {}).get("test", [])
    )
    require(
        "python -m main healthcheck" in lifecycle_health
        and "/readyz" in lifecycle_health,
        "Lifecycle Compose health must use the published readiness CLI",
    )

    postgres = _service(model, "candystore-postgres")
    app = _service(model, "candystore")
    daprd = _service(model, "candystore-daprd")
    require(
        app.get("build", {}).get("context")
        == str((source_root / "candystore").resolve())
        and isinstance(app.get("image"), str)
        and bool(app.get("image"))
        and "@sha256:" not in app.get("image", ""),
        "Candystore must be the only local Compose build and must use the selected source root",
    )
    candystore_dockerfile = source_root / "candystore" / "Dockerfile"
    if candystore_dockerfile.is_file():
        first_line = candystore_dockerfile.read_text(encoding="utf-8").splitlines()[0]
        require(
            first_line
            == "FROM python@sha256:e031123e3d85762b141ad1cbc56452ba69c6e722ebf2f042cc0dc86c47c0d8b3",
            "Candystore's exercised registry base image must be immutable",
        )
    require(
        _aliases(postgres, "candystore-internal") >= {"postgres"},
        "Candystore PostgreSQL must retain postgres DNS",
    )
    require(
        _aliases(app, "candystore-internal") >= {"candystore-app"},
        "Candystore app must retain candystore-app DNS",
    )
    require(
        _aliases(app, "proxy") >= {"candystore"},
        "Candystore must retain its proxy DNS alias",
    )
    for key, expected in EXPECTED_CANDYSTORE_EVENT_ENV.items():
        require(
            app.get("environment", {}).get(key) == expected,
            f"Candystore {key} must remain {expected!r} for the canonical Bloodbank event path",
        )
    schema_mount = _mount(app, "/bloodbank-schemas")
    require(
        schema_mount is not None
        and schema_mount.get("source")
        == str((source_root / "bloodbank" / "schemas").resolve())
        and schema_mount.get("read_only") is True,
        "Candystore must read-only mount the exact checked-out Bloodbank schema registry",
    )
    require(
        len(app.get("volumes", [])) == 1,
        "Candystore app must have only the canonical Bloodbank schema mount",
    )
    require(
        _dependency(app, "candystore-postgres") == "service_healthy",
        "Candystore app must wait for healthy PostgreSQL",
    )
    require(
        "/readyz" in " ".join(app.get("healthcheck", {}).get("test", [])),
        "Candystore dependency health must use /readyz",
    )
    require(
        _dependency(daprd, "nats-init") == "service_completed_successfully",
        "Candystore daprd must wait for stream initialization",
    )
    require(
        _dependency(daprd, "dapr-placement") == "service_started",
        "Candystore daprd must depend on placement",
    )
    require(
        _dependency(daprd, "candystore") == "service_healthy",
        "Candystore daprd must wait for the ready app",
    )
    daprd_mount = _mount(daprd, "/components")
    require(
        daprd_mount is not None
        and daprd_mount.get("source")
        == str((source_root / "candystore" / "dapr-components").resolve())
        and daprd_mount.get("read_only") is True,
        "Candystore daprd must exclusively mount Candystore's durable component contract read-only",
    )
    require(
        len(daprd.get("volumes", [])) == 1,
        "Candystore daprd must have only the canonical /components mount",
    )
    require(
        daprd.get("command", []) == EXPECTED_CANDYSTORE_DAPRD_COMMAND,
        "Candystore daprd command must retain the canonical app, component, and placement event path",
    )

    preflight = _service(model, "holocene-api-preflight")
    require(
        _dependency(preflight, "candystore") == "service_healthy",
        "Holocene host API preflight must follow Candystore readiness",
    )
    require(
        "http://host.docker.internal:4000/health" in preflight.get("command", []),
        "Holocene preflight must check the host API boundary",
    )
    holocene = _service(model, "holocene-web")
    require(not holocene.get("ports"), "Holocene web must have no published port")
    require(
        set(holocene.get("expose", [])) == {"3001"},
        "Holocene web must expose only container port 3001",
    )
    require(
        set(holocene.get("networks", {})) == {"proxy"},
        "Holocene web must attach only to proxy",
    )
    require(
        _aliases(holocene, "proxy") >= {"holocene-web"},
        "Holocene web must retain its proxy DNS alias",
    )
    require(
        _dependency(holocene, "holocene-api-preflight")
        == "service_completed_successfully",
        "Holocene web must wait for the host API preflight",
    )
    require(
        holocene.get("environment", {}).get("HOLOCENE_API_INTERNAL_URL")
        == "http://host.docker.internal:4000",
        "Holocene web must cross the host boundary at host.docker.internal:4000",
    )
    extra_hosts = json.dumps(holocene.get("extra_hosts", {}), sort_keys=True)
    require(
        "host.docker.internal" in extra_hosts and "host-gateway" in extra_hosts,
        "Holocene web must map host.docker.internal to host-gateway",
    )
    holocene_mount = _mount(holocene, "/app")
    require(
        holocene_mount is not None
        and holocene_mount.get("source") == str((source_root / "holocene").resolve()),
        "Holocene web must bind the selected committed source root",
    )
    expected_env_file = str((source_root / "holocene" / ".env.holocene-web").resolve())
    require(
        holocene.get("env_file") == [{"path": expected_env_file, "required": False}],
        "Holocene web must retain its unresolved optional component env-file reference",
    )
    require(
        set(holocene.get("environment", {}))
        == {"NEXT_TELEMETRY_DISABLED", "HOLOCENE_API_INTERNAL_URL"},
        "Holocene rendered environment must contain only explicit non-secret Compose keys",
    )
    labels = holocene.get("labels", {})
    require(
        labels == EXPECTED_HOLOCENE_LABELS,
        "Holocene Traefik labels must exactly preserve the committed Host, auth, HQ, proxy, and port contract",
    )

    if model_name in {"tools", "full"}:
        for name, mode in (("pjangler-cli", "cli"), ("pjangler-mcp", "mcp")):
            tool = _service(model, name)
            require(
                set(tool.get("profiles", [])) == {"tools", "full"},
                f"{name} must be opt-in for tools/full",
            )
            require(
                not tool.get("ports") and not tool.get("expose"),
                f"{name} must have no listener",
            )
            require("healthcheck" not in tool, f"{name} must not fake HTTP health")
            require(
                tool.get("restart") == "no", f"{name} must be one-shot with restart=no"
            )
            require(
                tool.get("deploy", {}).get("replicas") == 0,
                f"{name} must stay run-only with zero service replicas",
            )
            require(
                tool.get("environment", {}).get("PJANGLER_TOOL_MODE") == mode,
                f"{name} mode must be {mode}",
            )
            tool_mount = _mount(tool, "/workspace")
            require(
                tool_mount is not None
                and tool_mount.get("source")
                == str((source_root / "pjangler").resolve())
                and tool_mount.get("read_only") is True,
                f"{name} must use the selected PJangler source read-only",
            )
        require(
            _service(model, "pjangler-mcp").get("stdin_open") is True,
            "PJangler MCP must keep stdin open for stdio transport",
        )
        require(
            _service(model, "pjangler-mcp").get("tty") is not True,
            "PJangler MCP must not allocate a TTY",
        )

    if model_name == "cloud":
        gate = _service(model, "cloud-unsupported")
        gate_command = " ".join(gate.get("command", []))
        require(gate.get("restart") == "no", "cloud rejection gate must be one-shot")
        require(
            "not cloud-production-ready" in gate_command and "exit 64" in gate_command,
            "cloud render must explicitly reject the local bind model",
        )
        require(
            any(
                mount.get("type") == "bind"
                for service in services.values()
                for mount in service.get("volumes", [])
            ),
            "cloud render must honestly expose that local bind mounts remain",
        )

    for name in PROFILE_SERVICES["default"]:
        require(
            not _service(model, name).get("profiles"),
            f"default local service {name} must render without profiles",
        )

    return errors


def render_models(compose_file: Path, source_root: Path) -> dict[str, dict[str, Any]]:
    required_sources = (
        source_root / "bloodbank" / "compose" / "nats" / "init.sh",
        source_root / "bloodbank" / "compose" / "nats" / "streams.json",
        source_root
        / "bloodbank"
        / "schemas"
        / "bloodbank"
        / "v1"
        / "lifecycle"
        / "snapshot.updated.v3.json",
        source_root / "candystore" / "dapr-components",
        source_root / "candystore" / "dapr-components" / "lifecycle-replies.yaml",
        source_root / "candystore" / "Dockerfile",
        source_root / "holocene" / "compose.yml",
        source_root / "holocene" / "packages" / "lifecycle-client" / "package.json",
        source_root / "momo" / "skill" / "scripts" / "lifecycle_client.py",
        source_root / "lifecycle" / "README.md",
        source_root / "pjangler" / "package.json",
        source_root / "pjangler" / "dist" / "index.js",
        source_root / "pjangler" / "dist" / "mcp-server.js",
    )
    missing = [str(path) for path in required_sources if not path.exists()]
    if missing:
        raise RuntimeError(
            f"source root is not a populated 33GOD monorepo; missing: {', '.join(missing)}"
        )

    env = os.environ.copy()
    env["GOD_SOURCE_ROOT"] = str(source_root.resolve())
    # Render-only validation resolves the secret path but never opens it or
    # supplies a secret value.
    env.setdefault(
        "LIFECYCLE_POSTGRES_PASSWORD_FILE",
        "/run/secrets/33god-lifecycle-postgres-password",
    )
    models: dict[str, dict[str, Any]] = {}
    for model_name in PROFILE_SERVICES:
        command = ["docker", "compose", "-f", str(compose_file)]
        if model_name != "default":
            command.extend(["--profile", model_name])
        command.extend(["config", "--no-env-resolution", "--format", "json"])
        result = subprocess.run(
            command, cwd=compose_file.parent, env=env, text=True, capture_output=True
        )
        if result.returncode:
            raise RuntimeError(
                f"{model_name} render failed (docker compose exited {result.returncode}; "
                "captured output suppressed to protect component env-file values)"
            )
        models[model_name] = json.loads(result.stdout)
    return models


def main() -> int:
    script = Path(__file__).resolve()
    platform_root = script.parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--compose-file", type=Path, default=platform_root / "compose.yaml"
    )
    parser.add_argument("--source-root", type=Path, default=platform_root.parent)
    parser.add_argument(
        "--rendered-json", type=Path, help="validate one pre-rendered JSON fixture"
    )
    parser.add_argument("--model", choices=PROFILE_SERVICES, default="default")
    args = parser.parse_args()

    try:
        if args.rendered_json:
            models = {args.model: json.loads(args.rendered_json.read_text())}
        else:
            models = render_models(
                args.compose_file.resolve(), args.source_root.resolve()
            )
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"compose semantic validation could not run: {exc}", file=sys.stderr)
        return 2

    errors = [
        error
        for name, model in models.items()
        for error in validate_model(name, model, args.source_root.resolve())
    ]
    if errors:
        print("compose semantic validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"compose semantic validation passed: {', '.join(models)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
