from __future__ import annotations

import ast
import base64
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
LIVE_SCRIPT = PLATFORM_ROOT / "scripts" / "verify-lifecycle-live.py"
LIVE_SPEC = importlib.util.spec_from_file_location("verify_lifecycle_live", LIVE_SCRIPT)
assert LIVE_SPEC and LIVE_SPEC.loader
LIVE_HARNESS = importlib.util.module_from_spec(LIVE_SPEC)
LIVE_SPEC.loader.exec_module(LIVE_HARNESS)

PORT_OVERRIDE_KEYS = (
    "BLOODBANK_NATS_CLIENT_PORT",
    "BLOODBANK_NATS_MONITOR_PORT",
    "BLOODBANK_DAPR_PLACEMENT_PORT",
    "LIFECYCLE_PORT",
    "CANDYSTORE_POSTGRES_PORT",
    "CANDYSTORE_PORT",
    "CANDYSTORE_DAPR_HTTP_PORT",
)

RESOURCE_OVERRIDE_KEYS = (
    "BLOODBANK_NETWORK_NAME",
    "LIFECYCLE_NETWORK_NAME",
    "CANDYSTORE_NETWORK_NAME",
    "PROXY_NETWORK_NAME",
    "BLOODBANK_NATS_VOLUME",
    "LIFECYCLE_POSTGRES_VOLUME",
    "CANDYSTORE_POSTGRES_VOLUME",
    "HOLOCENE_NODE_MODULES_VOLUME",
    "HOLOCENE_WEB_NODE_MODULES_VOLUME",
    "HOLOCENE_WEB_NEXT_VOLUME",
)

IMAGE_OVERRIDE_KEYS = ("CANDYSTORE_IMAGE",)


class ComposeSemanticValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_root = Path(
            os.environ.get("GOD_SOURCE_ROOT", PLATFORM_ROOT.parent)
        ).resolve()
        required = [
            cls.source_root / name
            for name in ("bloodbank", "candystore", "holocene", "pjangler")
        ]
        cls.has_live_sources = all(path.is_dir() for path in required)
        cls.models = None
        if cls.has_live_sources:
            with mock.patch.dict(os.environ, {}, clear=False):
                for key in (
                    *PORT_OVERRIDE_KEYS,
                    *RESOURCE_OVERRIDE_KEYS,
                    *IMAGE_OVERRIDE_KEYS,
                ):
                    os.environ.pop(key, None)
                cls.models = VALIDATOR.render_models(
                    PLATFORM_ROOT / "compose.yaml", cls.source_root
                )

    def canonical_model(self, name: str = "default") -> dict:
        if self.models is None:
            self.skipTest("set GOD_SOURCE_ROOT to a populated 33GOD monorepo")
        return copy.deepcopy(self.models[name])

    def errors_for(self, model: dict, name: str = "default") -> list[str]:
        return VALIDATOR.validate_model(name, model, self.source_root)

    def test_failure_fixture_is_rejected_with_actionable_errors(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--rendered-json",
                str(FIXTURE),
                "--model",
                "default",
            ],
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
                if any(
                    marker in key.upper()
                    for marker in (
                        "TOKEN",
                        "SECRET",
                        "PASSWORD",
                        "CREDENTIAL",
                        "OPERATOR",
                    )
                ):
                    sensitive[key] = value.strip("'\"")

        rendered = json.dumps(model, sort_keys=True)
        leaked_key = any(key in rendered for key in sensitive)
        leaked_value = any(value and value in rendered for value in sensitive.values())
        self.assertFalse(
            leaked_key or leaked_value,
            "rendered model disclosed a sensitive Holocene env-file key or value",
        )
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
                VALIDATOR.render_models(
                    PLATFORM_ROOT / "compose.yaml", self.source_root
                )
        self.assertNotIn(secret_sentinel, str(raised.exception))
        self.assertIn("captured output suppressed", str(raised.exception))

    def test_candystore_subscription_mutations_are_rejected(self) -> None:
        mutations = {
            "SUBSCRIBE_PUBSUB": "other-pubsub",
            "SUBSCRIBE_TOPIC": "bloodbank.evt.v1.agent.>",
            "SUBSCRIBE_ROUTE": "/events/partial",
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                model = self.canonical_model()
                model["services"]["candystore"]["environment"][key] = value
                self.assertTrue(
                    any(
                        key in error and "canonical Bloodbank event path" in error
                        for error in self.errors_for(model)
                    ),
                    f"{key} mutation was not rejected",
                )

    def test_candystore_exact_schema_registry_mount_is_enforced(self) -> None:
        model = self.canonical_model()
        app = model["services"]["candystore"]
        mount = next(
            item for item in app["volumes"] if item["target"] == "/bloodbank-schemas"
        )
        self.assertTrue(mount["read_only"])
        self.assertEqual(
            mount["source"], str((self.source_root / "bloodbank" / "schemas").resolve())
        )

        mount["source"] = str((self.source_root / "candystore" / "schemas").resolve())
        app["environment"]["BLOODBANK_SCHEMAS_DIR"] = "/guessed-schemas"
        errors = self.errors_for(model)
        self.assertTrue(
            any(
                "exact checked-out Bloodbank schema registry" in error
                for error in errors
            )
        )
        self.assertTrue(any("BLOODBANK_SCHEMAS_DIR" in error for error in errors))

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
                    any(
                        "daprd command must retain" in error
                        for error in self.errors_for(model)
                    ),
                    f"{label} mutation was not rejected",
                )

        model = self.canonical_model()
        command = model["services"]["candystore-daprd"]["command"]
        index = command.index("--placement-host-address=dapr-placement:50005")
        command[index] = "--placement-host-address=attacker:50005"
        self.assertTrue(
            any(
                "daprd command must retain" in error for error in self.errors_for(model)
            )
        )

    def test_traefik_host_and_auth_mutations_are_rejected(self) -> None:
        mutations = {
            "malicious host": (
                "traefik.http.routers.holocene-web.rule",
                "Host(`attacker.example`)",
            ),
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
                    any(
                        "Traefik labels must exactly preserve" in error
                        for error in self.errors_for(model)
                    ),
                    f"{label} mutation was not rejected",
                )

    def test_exact_network_isolation_rejects_postgres_on_proxy(self) -> None:
        model = self.canonical_model()
        model["services"]["candystore-postgres"]["networks"]["proxy"] = None
        errors = self.errors_for(model)
        self.assertTrue(
            any("candystore-postgres network memberships" in error for error in errors)
        )

    def test_bloodbank_transport_mutations_are_rejected(self) -> None:
        model = self.canonical_model()
        model["services"]["nats-init"]["environment"]["NATS_URL"] = (
            "nats://attacker:4222"
        )
        errors = self.errors_for(model)
        self.assertTrue(
            any("nats-init must target canonical NATS" in error for error in errors)
        )

        model = self.canonical_model()
        model["services"]["candystore-daprd"]["networks"].pop("bloodbank-network")
        errors = self.errors_for(model)
        self.assertTrue(
            any("candystore-daprd network memberships" in error for error in errors)
        )

    def test_environment_selected_noncolliding_port_override_is_accepted(self) -> None:
        if not self.has_live_sources:
            self.skipTest("set GOD_SOURCE_ROOT to a populated 33GOD monorepo")
        overrides = {
            "BLOODBANK_NATS_CLIENT_PORT": "44991",
            "BLOODBANK_NATS_MONITOR_PORT": "44992",
            "BLOODBANK_DAPR_PLACEMENT_PORT": "44993",
            "LIFECYCLE_PORT": "44994",
            "CANDYSTORE_POSTGRES_PORT": "44995",
            "CANDYSTORE_PORT": "44996",
            "CANDYSTORE_DAPR_HTTP_PORT": "44997",
        }
        with mock.patch.dict(os.environ, overrides):
            models = VALIDATOR.render_models(
                PLATFORM_ROOT / "compose.yaml", self.source_root
            )
        errors = VALIDATOR.validate_model(
            "default", models["default"], self.source_root
        )
        self.assertEqual(errors, [])
        rendered_ports = {
            int(port["published"])
            for service in models["default"]["services"].values()
            for port in service.get("ports", [])
        }
        self.assertTrue(set(map(int, overrides.values())).issubset(rendered_ports))

    def test_environment_selected_port_collision_is_rejected(self) -> None:
        if not self.has_live_sources:
            self.skipTest("set GOD_SOURCE_ROOT to a populated 33GOD monorepo")
        with mock.patch.dict(
            os.environ,
            {"BLOODBANK_NATS_CLIENT_PORT": "44991", "LIFECYCLE_PORT": "44991"},
        ):
            models = VALIDATOR.render_models(
                PLATFORM_ROOT / "compose.yaml", self.source_root
            )
        errors = VALIDATOR.validate_model(
            "default", models["default"], self.source_root
        )
        self.assertTrue(
            any("published ports must not collide" in error for error in errors)
        )

    def test_canonical_defaults_and_caller_selected_resources_are_isolated(
        self,
    ) -> None:
        model = self.canonical_model()
        self.assertEqual(
            {key: model["volumes"][key]["name"] for key in VALIDATOR.EXPECTED_VOLUMES},
            VALIDATOR.EXPECTED_VOLUMES,
        )
        self.assertEqual(
            {
                key: model["networks"][key]["name"]
                for key in VALIDATOR.EXPECTED_NETWORKS
            },
            {key: key for key in VALIDATOR.EXPECTED_NETWORKS},
        )

        if not self.has_live_sources:
            self.skipTest("set GOD_SOURCE_ROOT to a populated 33GOD monorepo")
        overrides = {
            key: f"bartholomew-{index}"
            for index, key in enumerate(RESOURCE_OVERRIDE_KEYS)
        }
        with mock.patch.dict(os.environ, overrides):
            models = VALIDATOR.render_models(
                PLATFORM_ROOT / "compose.yaml", self.source_root
            )
        overridden = models["default"]
        actual_names = {
            entry["name"]
            for section in ("networks", "volumes")
            for entry in overridden[section].values()
        }
        self.assertTrue(set(overrides.values()).issubset(actual_names))
        self.assertEqual(
            VALIDATOR.validate_model("default", overridden, self.source_root), []
        )

    def test_lifecycle_exact_digest_and_no_build_are_enforced(self) -> None:
        model = self.canonical_model()
        for name in ("lifecycle-migrate", "lifecycle-bootstrap", "lifecycle"):
            self.assertEqual(
                model["services"][name]["image"], VALIDATOR.LIFECYCLE_IMAGE
            )
            self.assertNotIn("build", model["services"][name])

        model["services"]["lifecycle"]["image"] = (
            f"ghcr.io/delorenj/lifecycle@sha256:{'0' * 64}"
        )
        model["services"]["lifecycle"]["build"] = "../lifecycle"
        errors = self.errors_for(model)
        self.assertTrue(
            any("immutable image" in error and "lifecycle" in error for error in errors)
        )
        self.assertTrue(
            any("must never contain a Compose build" in error for error in errors)
        )

    def test_every_exercised_registry_image_is_digest_pinned(self) -> None:
        model = self.canonical_model()
        for name, expected in VALIDATOR.EXPECTED_PINNED_IMAGES.items():
            if name in model["services"]:
                self.assertEqual(model["services"][name]["image"], expected)
                self.assertIn("@sha256:", expected)
        self.assertEqual(model["services"]["candystore"]["image"], "candystore:local")
        self.assertIn("build", model["services"]["candystore"])

    def test_isolated_live_path_may_select_a_unique_local_candystore_image(
        self,
    ) -> None:
        if not self.has_live_sources:
            self.skipTest("set GOD_SOURCE_ROOT to a populated 33GOD monorepo")
        with mock.patch.dict(
            os.environ, {"CANDYSTORE_IMAGE": "candystore:aion-live-unique"}
        ):
            models = VALIDATOR.render_models(
                PLATFORM_ROOT / "compose.yaml", self.source_root
            )
        model = models["default"]
        self.assertEqual(
            model["services"]["candystore"]["image"], "candystore:aion-live-unique"
        )
        self.assertEqual(
            VALIDATOR.validate_model("default", model, self.source_root), []
        )

    def test_lifecycle_fail_closed_ordering_is_enforced(self) -> None:
        model = self.canonical_model()
        model["services"]["lifecycle-bootstrap"]["depends_on"] = {
            "lifecycle-postgres": {"condition": "service_started"}
        }
        model["services"]["lifecycle"]["depends_on"].pop("nats-init")
        errors = self.errors_for(model)
        self.assertTrue(
            any(
                "bootstrap must wait for successful migration" in error
                for error in errors
            )
        )
        self.assertTrue(
            any(
                "serve must wait for canonical stream initialization" in error
                for error in errors
            )
        )

    def test_lifecycle_storage_secret_and_network_isolation_are_enforced(self) -> None:
        model = self.canonical_model()
        postgres = model["services"]["lifecycle-postgres"]
        postgres["volumes"][0]["source"] = "candystore-pgdata"
        postgres["networks"]["proxy"] = None
        model["services"]["lifecycle"]["secrets"] = []
        errors = self.errors_for(model)
        self.assertTrue(any("dedicated lifecycle-pgdata" in error for error in errors))
        self.assertTrue(
            any("lifecycle-postgres network memberships" in error for error in errors)
        )
        self.assertTrue(any("lifecycle must mount only" in error for error in errors))

    def test_lifecycle_cli_health_and_bootstrap_contract_are_enforced(self) -> None:
        model = self.canonical_model()
        bootstrap = model["services"]["lifecycle-bootstrap"]
        bootstrap["command"] = ["python -m main bootstrap --lifecycle-id unsafe"]
        model["services"]["lifecycle"]["healthcheck"]["test"][-1] = (
            "http://127.0.0.1:8080/livez"
        )
        errors = self.errors_for(model)
        self.assertTrue(
            any("bootstrap must pass --actor-id" in error for error in errors)
        )
        self.assertTrue(any("published readiness CLI" in error for error in errors))

    def test_live_matrix_forbids_synthetic_or_second_lifecycle_writer(
        self,
    ) -> None:
        source = (PLATFORM_ROOT / "scripts" / "verify-lifecycle-live.py").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "def apply_internal_command",
            "apply_internal_command(",
            "from authority import LifecycleAuthority",
            "LifecycleAuthority(",
            "handle_command_envelope(",
            "LifecycleRepository(",
            "LIFECYCLE_INTERNAL_COMMAND",
            "aion-live-outage",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

        lifecycle_image_containers: list[str] = []
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if any(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "docker"
                and any(
                    isinstance(argument, ast.Name)
                    and argument.id == "LIFECYCLE_IMAGE"
                    for argument in call.args
                )
                for call in ast.walk(node)
            ):
                lifecycle_image_containers.append(node.name)
        self.assertEqual(lifecycle_image_containers, ["publish_jetstream"])
        self.assertNotIn(
            '"--network",\n            self.networks["lifecycle"]', source
        )

        autonomous_start = source.index('"autonomous-after-persistence"')
        autonomous = source[
            autonomous_start : source.index(
                "self.prestart_verdict_command_id", autonomous_start
            )
        ]
        self.assertIn("self.publish(autonomous_command)", autonomous)
        self.assertIn(
            'self.wait_command(autonomous_command["id"], "applied")',
            autonomous,
        )
        self.assertNotIn("apply_internal_command", autonomous)

        quiesce_start = source.index('"manual-before-repeated-restart"')
        quiesce = source[
            quiesce_start : source.index("quiesced_state =", quiesce_start)
        ]
        self.assertIn("self.publish(quiesce_command)", quiesce)
        self.assertIn(
            'self.wait_command(quiesce_command["id"], "applied")',
            quiesce,
        )
        self.assertNotIn("apply_internal_command", quiesce)

    def test_live_matrix_requires_real_durable_momo_obligation_execution(
        self,
    ) -> None:
        harness = (PLATFORM_ROOT / "scripts" / "verify-lifecycle-live.py").read_text(
            encoding="utf-8"
        )
        worker = (
            PLATFORM_ROOT.parent
            / "skills"
            / "momo"
            / "scripts"
            / "obligation_worker.py"
        ).read_text(encoding="utf-8")

        momo_start = harness.index(
            'print("[live] exercising real Momo durable obligation actor", flush=True)'
        )
        momo_end = harness.index(
            'print("[live] exercising Holocene read/action and browser surfaces", flush=True)',
            momo_start,
        )
        momo = harness[momo_start:momo_end]
        for forbidden in (
            '"complete-obligation"',
            '"artifact_sha256": "a" * 64',
            "completion_path.write_text(json.dumps(completion_event)",
            "completion_publish = run(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, momo)

        for required in (
            "start_momo_obligation_actor(",
            '"Momo durable actor readiness"',
            "invocation_publish_ack = self.publish_jetstream(",
            '"Momo obligation receipt"',
            "hashlib.sha256(artifact_bytes).hexdigest()",
            'len(set(artifact_sha256)) == 1',
            'receipt["artifact"]["sha256"] != artifact_sha256',
            'receipt["delivery"]["stream_sequence"]',
            'invocation_publish_ack["stream_sequence"]',
            'receipt["invocation"]["id"]',
            'receipt["completion"]["event_id"]',
            "completion_stream_message = self.stream_message(",
            'receipt["completion"]["duplicate"] is not False',
            'completion_stream_message["headers"]',
            '"Nats-Msg-Id": completion_event["id"]',
            '"receipt/artifact identity mismatch"',
        ):
            with self.subTest(required=required):
                self.assertIn(required, momo)

        ready = momo.index('"Momo durable actor readiness"')
        publish = momo.index("invocation_publish_ack = self.publish_jetstream(")
        receipt = momo.index('"Momo obligation receipt"', publish)
        authority = momo.index("momo_state = self.wait_state_version(", receipt)
        self.assertLess(ready, publish)
        self.assertLess(publish, receipt)
        self.assertLess(receipt, authority)

        for required in (
            "ConsumerConfig(",
            "durable_name=args.consumer",
            "ack_policy=AckPolicy.EXPLICIT",
            "filter_subject=INVOCATION_SUBJECT",
            "jetstream.pull_subscribe(",
            "await lifecycle_client.publish_envelope_async(",
            'completed_at = command["time"]',
            'headers={"Nats-Msg-Id": completion["id"]}',
            "await message.ack_sync(",
            'operations.append("completion_puback")',
            'operations.append("invocation_ack_sync")',
        ):
            with self.subTest(worker_required=required):
                self.assertIn(required, worker)
        puback = worker.index('operations.append("completion_puback")')
        ack = worker.index("await message.ack_sync(", puback)
        ack_recorded = worker.index('operations.append("invocation_ack_sync")', ack)
        self.assertLess(puback, ack)
        self.assertLess(ack, ack_recorded)

    def test_live_matrix_requires_real_holocene_browser_action(self) -> None:
        harness = (PLATFORM_ROOT / "scripts" / "verify-lifecycle-live.py").read_text(
            encoding="utf-8"
        )
        start = harness.index(
            'print("[live] exercising Holocene read/action and browser surfaces", flush=True)'
        )
        end = harness.index("    def execute(self)", start)
        holocene = harness[start:end]

        for forbidden in (
            'method="POST"',
            "/actions\"",
            '"playwright",\n                "screenshot"',
            '"wait-for-selector"',
            '"viewport-size"',
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, holocene)

        for required in (
            'browser_proof_script = holocene / "scripts" / "prove-lifecycle-browser.mjs"',
            'self.web_process = subprocess.Popen(',
            'wait_for("Holocene web page", page_ready)',
            '"node",\n                str(browser_proof_script)',
            'browser_receipt_path = self.proof_dir / "holocene-browser-receipt.json"',
            'request_receipt.get("browser_originated") is not True',
            'dialog.get("accepted") is not True',
            'click.get("clicked") is not True',
            'response_receipt.get("status") != 202',
            'json.loads(response_receipt.get("raw_body", "null"))',
            'browser_response.get("authority_accepted") is not False',
            'ui_success.get("visible") is not True',
            'browser_command_result = self.wait_command(',
            'browser_authority_state = self.wait_state_version(',
            'browser_candystore_projection = self.wait_projection(',
            'final_rendered.get("status") != "canceled"',
            'rendered_verdict.get("verdict") != "applied"',
            'image_bytes.startswith(b"\\x89PNG\\r\\n\\x1a\\n")',
        ):
            with self.subTest(required=required):
                self.assertIn(required, holocene)

        web_started = holocene.index("self.web_process = subprocess.Popen(")
        browser_invoked = holocene.index('"node",\n                str(browser_proof_script)')
        receipt_parsed = holocene.index("browser_receipt = json.loads(", browser_invoked)
        authority_observed = holocene.index(
            "browser_command_result = self.wait_command(", receipt_parsed
        )
        self.assertLess(web_started, browser_invoked)
        self.assertLess(browser_invoked, receipt_parsed)
        self.assertLess(receipt_parsed, authority_observed)

    def test_holocene_browser_script_rejects_passive_or_synthetic_proof(self) -> None:
        source = (
            PLATFORM_ROOT.parent
            / "holocene"
            / "scripts"
            / "prove-lifecycle-browser.mjs"
        ).read_text(encoding="utf-8")

        for forbidden in (
            "page.route(",
            "context.route(",
            "route.fulfill(",
            "route.continue(",
            "page.routeFromHAR(",
            "context.routeFromHAR(",
            "page.addInitScript(",
            "context.addInitScript(",
            "window.fetch =",
            "globalThis.fetch =",
            "page.setContent(",
            "playwright screenshot",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

        for required in (
            "chromium.launch({ headless: true })",
            'serviceWorkers: "block"',
            "await page.goto(pageUrl",
            'page.once("dialog"',
            'assert.equal(observed.type, "confirm"',
            "assert.equal(observed.message, expectedDialogMessage",
            "await dialog.accept()",
            "page.waitForRequest(",
            "page.waitForResponse(",
            "await actionButton.click(",
            "request.postData()",
            'assert.equal(requestReceipt.resource_type, "fetch")',
            "const responseRawBody = await response.text()",
            'assert.equal(response.request(), request, "HTTP 202 did not belong to the captured browser POST")',
            'assert.equal(response.fromServiceWorker(), false',
            'assert.equal(response.status(), 202',
            "assert.equal(responseBody.broker_processed, true)",
            "assert.equal(responseBody.authority_accepted, false)",
            "lifecycle-command-success",
            "lifecycle-command-verdict",
            'verdict.getAttribute("data-verdict") === "applied"',
            'root.getAttribute("data-source-causation-id") === commandEventId',
            "assert.notEqual(finalState.status, initialState.status",
            "await page.screenshot({ path: desktopPath, fullPage: true })",
            "await page.screenshot({ path: mobilePath, fullPage: true })",
            'contract_version: "holocene-lifecycle-browser-proof/v1"',
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)

        dialog = source.index('page.once("dialog"')
        click = source.index("await actionButton.click(", dialog)
        response_body = source.index(
            "const responseRawBody = await response.text()", click
        )
        rendered_outcome = source.index("const finalState = await renderedState", response_body)
        desktop = source.index("await page.screenshot({ path: desktopPath", rendered_outcome)
        mobile = source.index("await page.screenshot({ path: mobilePath", desktop)
        self.assertLess(dialog, click)
        self.assertLess(click, response_body)
        self.assertLess(response_body, rendered_outcome)
        self.assertLess(rendered_outcome, desktop)
        self.assertLess(desktop, mobile)

    def test_stored_nats_headers_require_unambiguous_canonical_message_id(
        self,
    ) -> None:
        event_id = "11111111-1111-4111-8111-111111111111"
        expected = {"Nats-Msg-Id": event_id}
        self.assertEqual(
            LIVE_HARNESS.stored_nats_headers(
                {"headers": {"Nats-Msg-Id": [event_id]}}
            ),
            expected,
        )

        block = f"NATS/1.0\r\nNats-Msg-Id: {event_id}\r\n\r\n".encode()
        self.assertEqual(
            LIVE_HARNESS.stored_nats_headers(
                {"hdrs": base64.b64encode(block).decode()}
            ),
            expected,
        )

        duplicate_block = (
            f"NATS/1.0\r\nNats-Msg-Id: {event_id}\r\n"
            f"Nats-Msg-Id: {event_id}\r\n\r\n"
        ).encode()
        with self.assertRaisesRegex(
            LIVE_HARNESS.LiveProofError, "ambiguous headers"
        ):
            LIVE_HARNESS.stored_nats_headers(
                {"hdrs": base64.b64encode(duplicate_block).decode()}
            )

    def test_live_matrix_proves_deployed_single_writer_outage_choreography(
        self,
    ) -> None:
        source = (PLATFORM_ROOT / "scripts" / "verify-lifecycle-live.py").read_text(
            encoding="utf-8"
        )
        for required in (
            'COMMAND_STREAM = "BLOODBANK_COMMANDS"',
            'COMMAND_CONSUMER = "lifecycle-authority-commands-v1"',
            "PGAPPNAME=",
            "BEGIN;",
            "FOR UPDATE;",
            "SELECT pg_sleep(300);",
            "pg_stat_activity",
            "pg_blocking_pids",
            "pg_terminate_backend",
            '"consumer",\n            "info"',
            '"--json"',
            'get("num_ack_pending", 0)',
            "outage_publish_ack = self.publish_jetstream(outage_command)",
            'self.compose("stop", "bloodbank-nats")',
            'self.compose("start", "bloodbank-nats")',
            'self.wait_command(outage_command["id"], "applied")',
            'any(item["published"] for item in outage_rows_during)',
            'item["verdict"] == "idempotent"',
            'recovered_counts["history"]',
            'recovered_counts["commands"]',
            'recovered_result != outage_result',
            '"no message found (10037)"',
            "command_removed_after_ack = wait_for(",
            "stream_outbox_sequences != sorted(stream_outbox_sequences)",
            "self.release_lifecycle_row_lock(check=False)",
            "self.release_lifecycle_recovery_guard(check=False)",
            "harness.cleanup()",
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)

        lock_start = source.index("self.start_lifecycle_row_lock()")
        lock_active = source.index("self.wait_lifecycle_row_lock()", lock_start)
        publish = source.index(
            "outage_publish_ack = self.publish_jetstream(outage_command)",
            lock_active,
        )
        ack_pending = source.index('get("num_ack_pending", 0)', publish)
        blocked_writer = source.index(
            "self.wait_blocked_lifecycle_writer()", ack_pending
        )
        nats_stop = source.index(
            'self.compose("stop", "bloodbank-nats")', blocked_writer
        )
        lock_release = source.index(
            "self.release_lifecycle_row_lock()", nats_stop
        )
        database_result = source.index(
            'self.wait_command(outage_command["id"], "applied")', lock_release
        )
        database_counts = source.index(
            "outage_committed_counts = self.counts()", database_result
        )
        pending_outbox = source.index(
            "outage_rows_during = [", database_counts
        )
        nats_start = source.index(
            'self.compose("start", "bloodbank-nats")', pending_outbox
        )
        persisted_pending = source.index(
            '"persisted ack-pending delivery after NATS restart"', nats_start
        )
        no_early_publication = source.index(
            '"outbox publication occurred before the deployed Lifecycle service recovered"',
            persisted_pending,
        )
        lifecycle_recovery = source.index(
            'self.compose("start", "lifecycle")', no_early_publication
        )
        redelivery = source.index(
            'f"{COMMAND_CONSUMER} durable redelivery acknowledgement"',
            lifecycle_recovery,
        )
        idempotent = source.index(
            'item["verdict"] == "idempotent"', redelivery
        )
        no_duplicates = source.index(
            '"durable command redelivery duplicated authoritative state, history, or command results"',
            idempotent,
        )
        self.assertLess(lock_start, lock_active)
        self.assertLess(lock_active, publish)
        self.assertLess(publish, ack_pending)
        self.assertLess(ack_pending, blocked_writer)
        self.assertLess(blocked_writer, nats_stop)
        self.assertLess(nats_stop, lock_release)
        self.assertLess(lock_release, database_result)
        self.assertLess(database_result, database_counts)
        self.assertLess(database_counts, pending_outbox)
        self.assertLess(pending_outbox, nats_start)
        self.assertLess(nats_start, persisted_pending)
        self.assertLess(persisted_pending, no_early_publication)
        self.assertLess(no_early_publication, lifecycle_recovery)
        self.assertLess(lifecycle_recovery, redelivery)
        self.assertLess(redelivery, idempotent)
        self.assertLess(idempotent, no_duplicates)

    def test_live_matrix_proves_true_prepublication_replay_and_final_health(
        self,
    ) -> None:
        source = (PLATFORM_ROOT / "scripts" / "verify-lifecycle-live.py").read_text(
            encoding="utf-8"
        )
        evidence_publish = source.index("prepublished_ack = self.publish_jetstream")
        stream_storage = source.index(
            "prepublished_stream_row = next(", evidence_publish
        )
        trusted_publication = source.index(
            "trusted_publication = datetime.fromisoformat", stream_storage
        )
        observation_wait = source.index(
            "persisted_prepublication = wait_for(", trusted_publication
        )
        preactivation = source.index("preactivation = wait_for(", observation_wait)
        activation = source.index("activation = wire_time()", preactivation)
        waiting_command = source.index("first = self.command(", activation)
        waiting_publish = source.index("self.publish(first)", waiting_command)
        waiting_reply = source.index(
            'self.wait_command(first["id"], "applied")', waiting_publish
        )
        first_waiting = source.index(
            "first_waiting = self.wait_state_version", waiting_reply
        )
        first_waiting_assertion = source.index(
            '"first WAITING authority snapshot did not expose the pending "',
            first_waiting,
        )
        replay_assertion = source.index(
            '"prepublished evidence replay rejection"', first_waiting_assertion
        )
        self.assertNotIn("set_evidence_consumer_pause", source)
        self.assertIn("'duplicate': bool(ack.duplicate)", source)
        self.assertLess(evidence_publish, stream_storage)
        self.assertLess(stream_storage, trusted_publication)
        self.assertLess(trusted_publication, observation_wait)
        self.assertLess(observation_wait, preactivation)
        self.assertLess(preactivation, activation)
        self.assertLess(activation, waiting_command)
        self.assertLess(waiting_command, waiting_publish)
        self.assertLess(waiting_publish, waiting_reply)
        self.assertLess(waiting_reply, first_waiting)
        self.assertLess(first_waiting, first_waiting_assertion)
        self.assertLess(first_waiting_assertion, replay_assertion)
        self.assertIn(
            'expected_state_version=preactivation["state_version"]',
            source[waiting_command:waiting_publish],
        )
        self.assertIn(
            '== first_waiting["state_version"]',
            source[replay_assertion : replay_assertion + 1000],
        )
        self.assertIn(
            '"causationid": prepublished_invocation_id',
            source[evidence_publish - 5000 : waiting_command],
        )
        self.assertIn(
            '"ordering_key": f"lifecycle:{self.lifecycle_id}"',
            source[evidence_publish - 5000 : waiting_command],
        )

        final_health = source.index(
            'self.wait_container_health("lifecycle", timeout=120)'
        )
        final_ps = source.index(
            'raw_ps = self.compose("ps", "-a", "--format", "json")',
            final_health,
        )
        self.assertLess(final_health, final_ps)

    def test_fixed_container_names_and_cross_authority_networks_are_rejected(
        self,
    ) -> None:
        model = self.canonical_model()
        model["services"]["lifecycle"]["container_name"] = "lifecycle"
        model["services"]["lifecycle"]["networks"]["candystore-internal"] = None
        errors = self.errors_for(model)
        self.assertTrue(
            any("without fixed container_name" in error for error in errors)
        )
        self.assertTrue(
            any("lifecycle network memberships" in error for error in errors)
        )

    def test_unpopulated_source_root_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "not a populated 33GOD monorepo"):
            VALIDATOR.render_models(
                PLATFORM_ROOT / "compose.yaml", PLATFORM_ROOT / "tests" / "fixtures"
            )


if __name__ == "__main__":
    unittest.main()
