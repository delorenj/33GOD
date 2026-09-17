"""Opt-in, real Postgres/NATS/Pilot/Bloodbank integration; no live Plane writes.

KREBS_TEST_DSN and KREBS_TEST_NATS_URL must name disposable test services.
Only the external Plane/runtime adapters and secret lookup are fixtures.
"""
import asyncio
import json
import os
from pathlib import Path
import shlex
import sys
import uuid

import nats
import pytest

from krebs import adapters, service
from krebs.controller import Controller
from krebs.store import Store


class FixtureProvider:
    def __init__(self):
        self.lane = "Todo"
        self.revision = "source-1"
        self.writes = 0

    def verify(self, project, actor):
        assert actor["native_user_id"] == "fixture-native-pm"

    def ticket(self, *args):
        return {"lane": self.lane, "revision": self.revision}

    def reconcile(self, project, actor, ticket, action, marker):
        return {"matched": self.lane == action.get("lane"), "revision": self.revision}

    def apply(self, project, actor, ticket, action, marker):
        self.writes += 1
        self.lane = action["lane"]
        self.revision = f"source-{self.writes + 1}"


class FixtureRuntime:
    def stop(self, *args):
        return {"stopped": True}

    def start(self, *args):
        return {"started": True}


def test_real_pilot_bloodbank_controller_roundtrip(tmp_path, monkeypatch):
    dsn = os.environ.get("KREBS_TEST_DSN")
    url = os.environ.get("KREBS_TEST_NATS_URL")
    if not dsn or not url:
        pytest.skip("disposable Postgres and NATS required")
    root = Path(__file__).resolve().parents[2]
    pilot = Path(os.environ.get("KREBS_TEST_PILOT", str(root.parent / "pilot")))
    assert (pilot / "bin/pilot.js").is_file(), "set KREBS_TEST_PILOT to Pilot checkout"
    # This is deliberately not a real credential or a file containing one.
    fixture_key = "public-test-fixture-only"
    monkeypatch.setattr(adapters, "secret", lambda ref: fixture_key)
    monkeypatch.setattr(service, "secret", lambda ref: fixture_key)
    monkeypatch.setenv("NATS_URL", url)
    project_id = "transport-test-" + uuid.uuid4().hex
    manifest = {
        "project_id": project_id,
        "ticket_provider": {"type": "plane", "workspace": "fixture", "board_id": str(uuid.uuid4())},
        "execution": {
            "mode": "managed", "pm_actor": "pm", "controller_actor": "repair",
            "legacy_writers_fenced": True, "policy_version": 2, "skill_version": "fixture",
            "actors": {"pm": {
                "key_ref": "op://DeLoSecrets/test-only-fixture/key", "native_user_id": "fixture-native-pm",
                "runtime_id": "fixture-host", "role": "pm", "runtime": {"adapter": "systemd"},
            }},
        },
    }
    manifest_path = tmp_path / ".project.json"
    manifest_path.write_text(json.dumps(manifest))
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps({"acceptance": {"text": "Review café\n雪", "ratio": 1.0},
                                   "artifact": "fixture-revision", "ticket_revision": "source-1"}))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "op").write_text("#!/bin/sh\nprintf '%s' public-test-fixture-only\n")
    (bin_dir / "bb").write_text(
        f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(root / 'bloodbank/bin/bb'))} \"$@\"\n"
    )
    for executable in bin_dir.iterdir():
        executable.chmod(0o700)
    env = {**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
           "NATS_URL": url, "PILOT_CONFIG_DIR": str(tmp_path / "pilot-config")}
    store = Store(dsn)
    store.migrate()
    provider = FixtureProvider()
    controller = Controller(store, adapters.Registry([manifest_path]), provider, FixtureRuntime())

    async def exercise():
        nc = await nats.connect(url)
        js = nc.jetstream()
        await js.add_stream(name="BLOODBANK_COMMANDS", subjects=["bloodbank.cmd.>", "bloodbank.rpy.>"])
        await js.add_stream(name="BLOODBANK_EVENTS", subjects=["bloodbank.evt.>"])
        serving = asyncio.create_task(service.serve(controller))
        try:
            for _ in range(100):
                if serving.done():
                    await serving
                try:
                    await js.consumer_info("BLOODBANK_COMMANDS", "krebs-execution-v2")
                    break
                except nats.js.errors.NotFoundError:
                    await asyncio.sleep(0.02)
            run_id = str(uuid.uuid4())
            command_id = str(uuid.uuid4())
            argv = ["node", str(pilot / "bin/pilot.js"), "task", "claim", "fixture-ticket",
                    "--actor", "pm", "--run-id", run_id, "--command-id", command_id,
                    "--file", str(payload), "--json"]

            async def invoke():
                proc = await asyncio.create_subprocess_exec(*argv, cwd=tmp_path, env=env,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                stdout, stderr = await asyncio.wait_for(proc.communicate(), 40)
                assert proc.returncode == 0, stderr.decode()
                return json.loads(stdout)

            first = await invoke()
            assert first["status"] == "result" and first["lane"] == "In Progress"
            assert first["command_id"] == command_id
            assert provider.writes == 1
            # Replay through all client/transport layers is the same operation.
            assert await invoke() == first
            assert provider.writes == 1
            await service.publish_outbox(store, js)
            with store.connect() as conn:
                event = conn.execute("SELECT * FROM krebs.outbox WHERE envelope->>'causationid'=%s", (command_id,)).fetchone()
            assert event and event["published_at"]
            stored = await js.get_last_msg("BLOODBANK_EVENTS", event["subject"])
            # The stream's stored envelope keeps the command causation intact.
            assert json.loads(stored.data)["causationid"] == command_id
        finally:
            serving.cancel()
            await asyncio.gather(serving, return_exceptions=True)
            await nc.drain()

    asyncio.run(exercise())
