from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


PLATFORM_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PLATFORM_ROOT / "scripts" / "validate-compose.py"
FIXTURE = PLATFORM_ROOT / "tests" / "fixtures" / "invalid-compose.json"
SPEC = importlib.util.spec_from_file_location("validate_compose", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

PORT_OVERRIDE_KEYS = (
    "BLOODBANK_NATS_CLIENT_PORT",
    "BLOODBANK_NATS_MONITOR_PORT",
    "BLOODBANK_DAPR_PLACEMENT_PORT",
    "CANDYSTORE_POSTGRES_PORT",
    "CANDYSTORE_PORT",
    "CANDYSTORE_DAPR_HTTP_PORT",
)


class ComposeSemanticValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_root = Path(os.environ.get("GOD_SOURCE_ROOT", PLATFORM_ROOT.parent)).resolve()
        required = [cls.source_root / name for name in ("bloodbank", "candystore", "holocene", "pjangler")]
        cls.has_live_sources = all(path.is_dir() for path in required)
        cls.models = None
        if cls.has_live_sources:
            with mock.patch.dict(os.environ, {}, clear=False):
                for key in PORT_OVERRIDE_KEYS:
                    os.environ.pop(key, None)
                cls.models = VALIDATOR.render_models(PLATFORM_ROOT / "compose.yaml", cls.source_root)

    def canonical_model(self, name: str = "default") -> dict:
        if self.models is None:
            self.skipTest("set GOD_SOURCE_ROOT to a populated 33GOD monorepo")
        return copy.deepcopy(self.models[name])

    def errors_for(self, model: dict, name: str = "default") -> list[str]:
        return VALIDATOR.validate_model(name, model, self.source_root)

    def test_failure_fixture_is_rejected_with_actionable_errors(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--rendered-json", str(FIXTURE), "--model", "default"],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("forbidden service bloodbank-candystore", result.stderr)
        self.assertIn("forbidden service platform-ready", result.stderr)
        self.assertIn("Candystore must have exactly postgres/app/daprd", result.stderr)

    def test_all_live_renders_pass_the_semantic_contract(self) -> None:
        if self.models is None:
            self.skipTest("set GOD_SOURCE_ROOT to a populated 33GOD monorepo")
        self.assertEqual(set(self.models), {"default", "tools", "full", "cloud"})
        errors = [
            error
            for model_name, model in self.models.items()
            for error in VALIDATOR.validate_model(model_name, model, self.source_root)
        ]
        self.assertEqual(errors, [])

    def test_holocene_env_file_is_not_expanded_or_disclosed(self) -> None:
        model = self.canonical_model()
        holocene = model["services"]["holocene-web"]
        env_file = self.source_root / "holocene" / ".env.holocene-web"
        sensitive: dict[str, str] = {}
        if env_file.is_file():
            for raw in env_file.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.startswith("export "):
                    line = line[7:].lstrip()
                key, value = (part.strip() for part in line.split("=", 1))
                if any(marker in key.upper() for marker in ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "OPERATOR")):
                    sensitive[key] = value.strip("'\"")

        rendered = json.dumps(model, sort_keys=True)
        leaked_key = any(key in rendered for key in sensitive)
        leaked_value = any(value and value in rendered for value in sensitive.values())
        self.assertFalse(leaked_key or leaked_value, "rendered model disclosed a sensitive Holocene env-file key or value")
        self.assertEqual(
            set(holocene.get("environment", {})),
            {"NEXT_TELEMETRY_DISABLED", "HOLOCENE_API_INTERNAL_URL"},
        )

    def test_render_failure_suppresses_captured_output(self) -> None:
        if not self.has_live_sources:
            self.skipTest("set GOD_SOURCE_ROOT to a populated 33GOD monorepo")
        secret_sentinel = "component-env-file-secret-sentinel"
        failure = SimpleNamespace(returncode=17, stdout="", stderr=secret_sentinel)
        with mock.patch.object(VALIDATOR.subprocess, "run", return_value=failure):
            with self.assertRaises(RuntimeError) as raised:
                VALIDATOR.render_models(PLATFORM_ROOT / "compose.yaml", self.source_root)
        self.assertNotIn(secret_sentinel, str(raised.exception))
        self.assertIn("captured output suppressed", str(raised.exception))

    def test_candystore_subscription_mutations_are_rejected(self) -> None:
        mutations = {
            "SUBSCRIBE_PUBSUB": "other-pubsub",
            "SUBSCRIBE_TOPIC": "bloodbank.evt.agent.>",
            "SUBSCRIBE_ROUTE": "/events/partial",
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                model = self.canonical_model()
                model["services"]["candystore"]["environment"][key] = value
                self.assertTrue(
                    any(key in error and "canonical Bloodbank event path" in error for error in self.errors_for(model)),
                    f"{key} mutation was not rejected",
                )

    def test_daprd_event_path_mutations_are_rejected(self) -> None:
        mutations = {
            "resources removed": "--resources-path=/components",
            "placement removed": "--placement-host-address=dapr-placement:50005",
        }
        for label, removed in mutations.items():
            with self.subTest(mutation=label):
                model = self.canonical_model()
                command = model["services"]["candystore-daprd"]["command"]
                command.remove(removed)
                self.assertTrue(
                    any("daprd command must retain" in error for error in self.errors_for(model)),
                    f"{label} mutation was not rejected",
                )

        model = self.canonical_model()
        command = model["services"]["candystore-daprd"]["command"]
        index = command.index("--placement-host-address=dapr-placement:50005")
        command[index] = "--placement-host-address=attacker:50005"
        self.assertTrue(any("daprd command must retain" in error for error in self.errors_for(model)))

    def test_traefik_host_and_auth_mutations_are_rejected(self) -> None:
        mutations = {
            "malicious host": ("traefik.http.routers.holocene-web.rule", "Host(`attacker.example`)"),
            "removed auth": ("traefik.http.routers.holocene-web.middlewares", None),
        }
        for label, (key, value) in mutations.items():
            with self.subTest(mutation=label):
                model = self.canonical_model()
                labels = model["services"]["holocene-web"]["labels"]
                if value is None:
                    labels.pop(key)
                else:
                    labels[key] = value
                self.assertTrue(
                    any("Traefik labels must exactly preserve" in error for error in self.errors_for(model)),
                    f"{label} mutation was not rejected",
                )

    def test_exact_network_isolation_rejects_postgres_on_proxy(self) -> None:
        model = self.canonical_model()
        model["services"]["candystore-postgres"]["networks"]["proxy"] = None
        errors = self.errors_for(model)
        self.assertTrue(any("candystore-postgres network memberships" in error for error in errors))

    def test_bloodbank_transport_mutations_are_rejected(self) -> None:
        model = self.canonical_model()
        model["services"]["nats-init"]["environment"]["NATS_URL"] = "nats://attacker:4222"
        errors = self.errors_for(model)
        self.assertTrue(any("nats-init must target canonical NATS" in error for error in errors))

        model = self.canonical_model()
        model["services"]["candystore-daprd"]["networks"].pop("bloodbank-network")
        errors = self.errors_for(model)
        self.assertTrue(any("candystore-daprd network memberships" in error for error in errors))

    def test_environment_selected_port_override_is_rejected(self) -> None:
        if not self.has_live_sources:
            self.skipTest("set GOD_SOURCE_ROOT to a populated 33GOD monorepo")
        with mock.patch.dict(os.environ, {"BLOODBANK_NATS_CLIENT_PORT": "4999"}):
            models = VALIDATOR.render_models(PLATFORM_ROOT / "compose.yaml", self.source_root)
        errors = VALIDATOR.validate_model("default", models["default"], self.source_root)
        self.assertTrue(
            any("NATS must publish exactly 4222 and 8222" in error and "4999" in error for error in errors)
        )

    def test_unpopulated_source_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "not a populated 33GOD monorepo"):
            VALIDATOR.render_models(PLATFORM_ROOT / "compose.yaml", PLATFORM_ROOT / "tests" / "fixtures")


if __name__ == "__main__":
    unittest.main()
