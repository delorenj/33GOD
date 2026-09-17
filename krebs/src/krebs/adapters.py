"""Trusted bindings, native identity, and supervised stop proof."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
from .contract import LANES, canonical, require


def secret(ref):
    require(isinstance(ref, str) and ref.startswith("op://"), "actor requires an enrolled op:// credential")
    result = subprocess.run(["op", "read", ref], capture_output=True, text=True, check=False)
    require(result.returncode == 0, "actor credential unavailable")
    return result.stdout.strip()

class Registry:
    def __init__(self, paths):
        self.paths = paths

    def project(self, project_id):
        documents = [(path, json.loads(Path(path).read_text())) for path in self.paths]
        require(sum(doc.get("project_id") == project_id for _, doc in documents) == 1, "missing or duplicate canonical project_id")
        for path, doc in documents:
            if doc.get("project_id") == project_id:
                tp, lifecycle = doc.get("ticket_provider", {}), doc.get("execution", {})
                require(tp.get("type", tp.get("provider")) == "plane", "managed provider is not Plane")
                require(tp.get("workspace") and tp.get("board_id"), "board binding missing")
                require(lifecycle.get("mode") in {"managed", "shadow"}, "execution is not enrolled")
                actors = lifecycle.get("actors", {})
                native_ids = [a.get("native_user_id") for a in actors.values()]
                require(len(native_ids) == len(set(native_ids)), "distinct actors require distinct native identities")
                return {**lifecycle, "project_id": project_id, "workspace": tp["workspace"], "board": tp["board_id"], "base": tp.get("base_url", "https://plane.delo.sh"), "manifest": str(path)}
        raise ValueError("project is not registered")

    def authenticate(self, command, auth):
        project = self.project(command["project_id"])
        actor = project.get("actors", {}).get(command["actor_id"])
        require(actor is not None, "actor not enrolled for board")
        require(actor.get("native_user_id") and actor.get("runtime_id") == command["runtime_id"], "actor runtime/native enrollment mismatch")
        key = secret(actor.get("key_ref"))
        require(isinstance(auth, dict) and isinstance(auth.get("wire"), str), "signed wire required")
        require(json.loads(auth["wire"]) == command, "signed wire differs from command")
        expected = hmac.new(key.encode(), auth["wire"].encode(), hashlib.sha256).hexdigest()
        require(isinstance(auth.get("signature"), str) and hmac.compare_digest(expected, auth["signature"]), "command ingress authentication failed")
        return project, actor

class PilotProvider:
    def __init__(self, helper):
        self.helper = str(Path(helper).resolve())

    def call(self, project, actor, operation, **data):
        request = {"version": 2, "operation": operation, "binding": {
            "base": project["base"], "workspace": project["workspace"], "board": project["board"],
            "keyRef": actor["key_ref"], "nativeUserId": actor["native_user_id"],
            "states": project.get("states", {}), "workingLabel": project.get("working_label")}, **data}
        proc = subprocess.run(["node", self.helper], input=canonical(request), capture_output=True, text=True, timeout=60)
        require(proc.returncode == 0, "Pilot provider operation failed; reconcile durable intent")
        return json.loads(proc.stdout)

    def verify(self, project, actor):
        require(project.get("pilot_helper_sha256") == hashlib.sha256(Path(self.helper).read_bytes()).hexdigest(), "Pilot provider helper pin missing or changed")
        skill = Path(project.get("skill_path", str(Path(project["manifest"]).parent / ".agents/skills/momo/SKILL.md")))
        require(skill.is_file() and project.get("skill_version") == hashlib.sha256(skill.read_bytes()).hexdigest(), "installed Momo skill pin missing or changed")
        require(set(LANES) <= set(project.get("states", {})), "exact lane bindings incomplete")
        require(project.get("working_label"), "working label binding missing")
        return self.call(project, actor, "verify")

    def ticket(self, project, actor, ticket_id):
        return self.call(project, actor, "get", ticket_id=ticket_id)

    def reconcile(self, project, actor, ticket_id, action, marker):
        return self.call(project, actor, "reconcile", ticket_id=ticket_id, action=action, marker=marker)

    def apply(self, project, actor, ticket_id, action, marker):
        return self.call(project, actor, "apply", ticket_id=ticket_id, action=action, marker=marker)

class Runtime:
    """Only enrolled systemd units can prove stop; client booleans are never proof."""
    def stop(self, project, attempt):
        actor = project["actors"][attempt["actor_id"]]
        adapter = actor.get("runtime", {})
        require(adapter.get("adapter") == "systemd", "runtime has no installed stop-proof adapter")
        prefix = adapter.get("unit_prefix", "")
        require(re.fullmatch(r"[a-zA-Z0-9_-]+", prefix) is not None and prefix, "invalid runtime unit prefix")
        require(re.fullmatch(r"[a-zA-Z0-9_-]+", attempt["run_id"]) is not None, "invalid supervised run id")
        unit = f"{prefix}-{attempt['run_id']}.service"
        subprocess.run(["systemctl", "--user", "stop", unit], capture_output=True, timeout=60)
        probe = subprocess.run(["systemctl", "--user", "show", unit, "--property=ActiveState,SubState,MainPID", "--value"], capture_output=True, text=True, timeout=10)
        # A missing unit also returns inactive/dead/0 on systemd. This proves there
        # is no unit-owned worker; readiness requires dispatch exclusively via it.
        values = set(probe.stdout.splitlines())
        require(probe.returncode == 0 and "0" in values and "inactive" in values and "dead" in values, "old runtime still live or stop proof unavailable")
        return {"unit": unit, "state": "stopped"}

    def running(self, project, attempt):
        adapter = project["actors"][attempt["actor_id"]].get("runtime", {})
        require(adapter.get("adapter") == "systemd", "runtime adapter unavailable")
        prefix, run = adapter.get("unit_prefix", ""), attempt["run_id"]
        require(bool(re.fullmatch(r"[a-zA-Z0-9_-]+", prefix)) and bool(re.fullmatch(r"[a-zA-Z0-9_-]+", run)), "invalid unit identity")
        probe = subprocess.run(["systemctl", "--user", "show", f"{prefix}-{run}.service", "--property=ActiveState", "--value"], capture_output=True, text=True, timeout=10)
        require(probe.returncode == 0, "runtime liveness proof unavailable")
        return probe.stdout.strip() in {"active", "activating"}

    def start(self, project, attempt, argv):
        require(isinstance(argv, list) and argv and all(isinstance(x, str) for x in argv), "worker argv required")
        actor = project["actors"][attempt["actor_id"]]
        adapter = actor.get("runtime", {})
        require(adapter.get("adapter") == "systemd", "runtime adapter unavailable")
        prefix, run = adapter.get("unit_prefix", ""), attempt["run_id"]
        require(bool(re.fullmatch(r"[a-zA-Z0-9_-]+", prefix)) and bool(re.fullmatch(r"[a-zA-Z0-9_-]+", run)), "invalid unit identity")
        unit = f"{prefix}-{run}.service"
        probe = subprocess.run(["systemctl", "--user", "show", unit, "--property=LoadState", "--value"], capture_output=True, text=True, timeout=10)
        if probe.returncode == 0 and probe.stdout.strip() == "loaded":
            return {"unit": unit, "existing": True}
        result = subprocess.run(["systemd-run", "--user", "--unit", unit,
            "--property=KillMode=control-group", "--property=Restart=no", "--property=TimeoutStopSec=15",
            "--setenv=KREBS_RUN_ID=" + run, "--setenv=PILOT_ACTOR_ID=" + attempt["actor_id"],
            "--working-directory=" + str(Path(project["manifest"]).parent), "--", *argv], capture_output=True, timeout=30)
        require(result.returncode == 0, "supervised dispatch failed")
        return {"unit": unit, "existing": False}
