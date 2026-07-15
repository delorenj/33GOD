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
    "candystore-pgdata": "candystore_pgdata",
    "holocene-node-modules": "holocene_holocene_node_modules",
    "holocene-web-node-modules": "holocene_holocene_web_node_modules",
    "holocene-web-next": "holocene_holocene_web_next",
}

EXPECTED_NETWORKS = {"bloodbank-network", "candystore-internal", "proxy"}

EXPECTED_SERVICE_NETWORKS = {
    "bloodbank-nats": {"bloodbank-network"},
    "nats-init": {"bloodbank-network"},
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

EXPECTED_CANDYSTORE_EVENT_ENV = {
    "SUBSCRIBE_PUBSUB": "bloodbank-pubsub",
    "SUBSCRIBE_TOPIC": "bloodbank.evt.v1.>",
    "SUBSCRIBE_ROUTE": "/events/all",
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
    "traefik.http.routers.holocene-hq.rule": "Host(`holocene.delo.sh`) && PathPrefix(`/hq`)",
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
    return next((mount for mount in service.get("volumes", []) if mount.get("target") == target), None)


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


def validate_model(model_name: str, model: dict[str, Any], source_root: Path) -> list[str]:
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

    candystore_services = {name for name in actual_services if "candystore" in name}
    require(
        candystore_services == {"candystore-postgres", "candystore", "candystore-daprd"},
        f"Candystore must have exactly postgres/app/daprd, got {sorted(candystore_services)}",
    )

    networks = model.get("networks", {})
    allowed_networks = EXPECTED_NETWORKS | ({"default"} if model_name in {"tools", "full"} else set())
    require(set(networks) == allowed_networks, f"network set must be {sorted(allowed_networks)}")
    for name in EXPECTED_NETWORKS:
        network = networks.get(name, {})
        require(network.get("name") == name, f"network {name} must retain exact external name")
        require(network.get("external") is True, f"network {name} must be external")

    for name, service in services.items():
        actual_memberships = set(service.get("networks", {}))
        expected_memberships = EXPECTED_SERVICE_NETWORKS.get(name)
        if expected_memberships is not None:
            require(
                actual_memberships == expected_memberships,
                f"service {name} network memberships must be exactly {sorted(expected_memberships)}",
            )

    volumes = model.get("volumes", {})
    require(set(volumes) == set(EXPECTED_VOLUMES), "only the five adopted named volumes may be declared")
    for key, name in EXPECTED_VOLUMES.items():
        volume = volumes.get(key, {})
        require(volume.get("name") == name, f"volume {key} must resolve to {name}")
        require(volume.get("external") is True, f"volume {key} must be external to prevent empty replacement data")

    nats_ports = _published_ports(_service(model, "bloodbank-nats"))
    require(
        nats_ports == {(4222, 4222, ""), (8222, 8222, "")},
        f"NATS must publish exactly 4222 and 8222; rendered {sorted(nats_ports)}",
    )
    require(
        _published_ports(_service(model, "dapr-placement")) == {(50005, 50005, "")},
        "Dapr placement must publish exactly 50005",
    )
    require(
        _published_ports(_service(model, "candystore-postgres")) == {(5434, 5432, "127.0.0.1")},
        "Candystore PostgreSQL must bind 127.0.0.1:5434 -> 5432",
    )
    require(
        _published_ports(_service(model, "candystore")) == {(8683, 3001, "127.0.0.1")},
        "Candystore app must bind 127.0.0.1:8683 -> 3001",
    )
    require(
        _published_ports(_service(model, "candystore-daprd")) == {(3504, 3500, "127.0.0.1")},
        "Candystore daprd must bind 127.0.0.1:3504 -> 3500",
    )
    for name, service in services.items():
        require(
            all(int(port.get("published", 0)) != 4000 for port in service.get("ports", [])),
            f"service {name} must not publish the host Holocene API port 4000",
        )

    nats_mount = _mount(_service(model, "bloodbank-nats"), "/data/jetstream")
    require(nats_mount is not None and nats_mount.get("source") == "bloodbank-nats-data", "NATS must use the adopted JetStream volume")

    init = _service(model, "nats-init")
    require(_dependency(init, "bloodbank-nats") == "service_healthy", "nats-init must wait for healthy NATS")
    for relative, target in (("compose/nats/streams.json", "/work/streams.json"), ("compose/nats/init.sh", "/work/init.sh")):
        mount = _mount(init, target)
        expected_source = str((source_root / "bloodbank" / relative).resolve())
        require(
            mount is not None and mount.get("source") == expected_source and mount.get("read_only") is True,
            f"nats-init must read-only mount Bloodbank {relative}",
        )
    require(set(init.get("entrypoint", [])) == {"/bin/sh", "/work/init.sh"}, "nats-init must execute Bloodbank's tracked initializer")
    require(init.get("environment", {}).get("NATS_URL") == "nats://nats:4222", "nats-init must target canonical NATS DNS and port")
    require(
        _service(model, "bloodbank-nats").get("environment", {}).get("BLOODBANK_NATS_URL") == "nats://nats:4222",
        "Bloodbank NATS service metadata must retain canonical NATS DNS and port",
    )
    require(_aliases(_service(model, "bloodbank-nats"), "bloodbank-network") >= {"nats"}, "NATS must retain the nats DNS alias")
    placement = _service(model, "dapr-placement")
    require(_aliases(placement, "bloodbank-network") >= {"dapr-placement"}, "placement must retain the dapr-placement DNS alias")
    require(placement.get("command", []) == ["./placement", "--port", "50005"], "placement must listen on canonical port 50005")

    postgres = _service(model, "candystore-postgres")
    app = _service(model, "candystore")
    daprd = _service(model, "candystore-daprd")
    require(_aliases(postgres, "candystore-internal") >= {"postgres"}, "Candystore PostgreSQL must retain postgres DNS")
    require(_aliases(app, "candystore-internal") >= {"candystore-app"}, "Candystore app must retain candystore-app DNS")
    require(_aliases(app, "proxy") >= {"candystore"}, "Candystore must retain its proxy DNS alias")
    for key, expected in EXPECTED_CANDYSTORE_EVENT_ENV.items():
        require(
            app.get("environment", {}).get(key) == expected,
            f"Candystore {key} must remain {expected!r} for the canonical Bloodbank event path",
        )
    require(_dependency(app, "candystore-postgres") == "service_healthy", "Candystore app must wait for healthy PostgreSQL")
    require("/readyz" in " ".join(app.get("healthcheck", {}).get("test", [])), "Candystore dependency health must use /readyz")
    require(_dependency(daprd, "nats-init") == "service_completed_successfully", "Candystore daprd must wait for stream initialization")
    require(_dependency(daprd, "dapr-placement") == "service_started", "Candystore daprd must depend on placement")
    require(_dependency(daprd, "candystore") == "service_healthy", "Candystore daprd must wait for the ready app")
    daprd_mount = _mount(daprd, "/components")
    require(
        daprd_mount is not None
        and daprd_mount.get("source") == str((source_root / "candystore" / "dapr-components").resolve())
        and daprd_mount.get("read_only") is True,
        "Candystore daprd must exclusively mount Candystore's durable component contract read-only",
    )
    require(len(daprd.get("volumes", [])) == 1, "Candystore daprd must have only the canonical /components mount")
    require(
        daprd.get("command", []) == EXPECTED_CANDYSTORE_DAPRD_COMMAND,
        "Candystore daprd command must retain the canonical app, component, and placement event path",
    )

    preflight = _service(model, "holocene-api-preflight")
    require(_dependency(preflight, "candystore") == "service_healthy", "Holocene host API preflight must follow Candystore readiness")
    require("http://host.docker.internal:4000/health" in preflight.get("command", []), "Holocene preflight must check the host API boundary")
    holocene = _service(model, "holocene-web")
    require(not holocene.get("ports"), "Holocene web must have no published port")
    require(set(holocene.get("expose", [])) == {"3001"}, "Holocene web must expose only container port 3001")
    require(set(holocene.get("networks", {})) == {"proxy"}, "Holocene web must attach only to proxy")
    require(_aliases(holocene, "proxy") >= {"holocene-web"}, "Holocene web must retain its proxy DNS alias")
    require(_dependency(holocene, "holocene-api-preflight") == "service_completed_successfully", "Holocene web must wait for the host API preflight")
    require(
        holocene.get("environment", {}).get("HOLOCENE_API_INTERNAL_URL") == "http://host.docker.internal:4000",
        "Holocene web must cross the host boundary at host.docker.internal:4000",
    )
    extra_hosts = json.dumps(holocene.get("extra_hosts", {}), sort_keys=True)
    require("host.docker.internal" in extra_hosts and "host-gateway" in extra_hosts, "Holocene web must map host.docker.internal to host-gateway")
    holocene_mount = _mount(holocene, "/app")
    require(
        holocene_mount is not None and holocene_mount.get("source") == str((source_root / "holocene").resolve()),
        "Holocene web must bind the selected committed source root",
    )
    expected_env_file = str((source_root / "holocene" / ".env.holocene-web").resolve())
    require(
        holocene.get("env_file") == [{"path": expected_env_file, "required": False}],
        "Holocene web must retain its unresolved optional component env-file reference",
    )
    require(
        set(holocene.get("environment", {})) == {"NEXT_TELEMETRY_DISABLED", "HOLOCENE_API_INTERNAL_URL"},
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
            require(set(tool.get("profiles", [])) == {"tools", "full"}, f"{name} must be opt-in for tools/full")
            require(not tool.get("ports") and not tool.get("expose"), f"{name} must have no listener")
            require("healthcheck" not in tool, f"{name} must not fake HTTP health")
            require(tool.get("restart") == "no", f"{name} must be one-shot with restart=no")
            require(tool.get("deploy", {}).get("replicas") == 0, f"{name} must stay run-only with zero service replicas")
            require(tool.get("environment", {}).get("PJANGLER_TOOL_MODE") == mode, f"{name} mode must be {mode}")
            tool_mount = _mount(tool, "/workspace")
            require(
                tool_mount is not None
                and tool_mount.get("source") == str((source_root / "pjangler").resolve())
                and tool_mount.get("read_only") is True,
                f"{name} must use the selected PJangler source read-only",
            )
        require(_service(model, "pjangler-mcp").get("stdin_open") is True, "PJangler MCP must keep stdin open for stdio transport")
        require(_service(model, "pjangler-mcp").get("tty") is not True, "PJangler MCP must not allocate a TTY")

    if model_name == "cloud":
        gate = _service(model, "cloud-unsupported")
        gate_command = " ".join(gate.get("command", []))
        require(gate.get("restart") == "no", "cloud rejection gate must be one-shot")
        require("not cloud-production-ready" in gate_command and "exit 64" in gate_command, "cloud render must explicitly reject the local bind model")
        require(any(mount.get("type") == "bind" for service in services.values() for mount in service.get("volumes", [])), "cloud render must honestly expose that local bind mounts remain")

    for name in PROFILE_SERVICES["default"]:
        require(not _service(model, name).get("profiles"), f"default local service {name} must render without profiles")

    return errors


def render_models(compose_file: Path, source_root: Path) -> dict[str, dict[str, Any]]:
    required_sources = (
        source_root / "bloodbank" / "compose" / "nats" / "init.sh",
        source_root / "bloodbank" / "compose" / "nats" / "streams.json",
        source_root / "candystore" / "dapr-components",
        source_root / "candystore" / "Dockerfile",
        source_root / "holocene" / "compose.yml",
        source_root / "pjangler" / "package.json",
        source_root / "pjangler" / "dist" / "index.js",
        source_root / "pjangler" / "dist" / "mcp-server.js",
    )
    missing = [str(path) for path in required_sources if not path.exists()]
    if missing:
        raise RuntimeError(f"source root is not a populated 33GOD monorepo; missing: {', '.join(missing)}")

    env = os.environ.copy()
    env["GOD_SOURCE_ROOT"] = str(source_root.resolve())
    models: dict[str, dict[str, Any]] = {}
    for model_name in PROFILE_SERVICES:
        command = ["docker", "compose", "-f", str(compose_file)]
        if model_name != "default":
            command.extend(["--profile", model_name])
        command.extend(["config", "--no-env-resolution", "--format", "json"])
        result = subprocess.run(command, cwd=compose_file.parent, env=env, text=True, capture_output=True)
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
    parser.add_argument("--compose-file", type=Path, default=platform_root / "compose.yaml")
    parser.add_argument("--source-root", type=Path, default=platform_root.parent)
    parser.add_argument("--rendered-json", type=Path, help="validate one pre-rendered JSON fixture")
    parser.add_argument("--model", choices=PROFILE_SERVICES, default="default")
    args = parser.parse_args()

    try:
        if args.rendered_json:
            models = {args.model: json.loads(args.rendered_json.read_text())}
        else:
            models = render_models(args.compose_file.resolve(), args.source_root.resolve())
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"compose semantic validation could not run: {exc}", file=sys.stderr)
        return 2

    errors = [error for name, model in models.items() for error in validate_model(name, model, args.source_root.resolve())]
    if errors:
        print("compose semantic validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"compose semantic validation passed: {', '.join(models)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
