"""Real Node provider/HTTP protocol against an isolated Plane-shaped server.

This exercises production serialization, pagination, native identity, assignment,
labels, comments and readback. It does not contact or mutate the live Plane board.
"""
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import threading
import uuid

import pytest

from krebs.adapters import PilotProvider
from krebs.bundles import bundle_digest
from krebs.contract import LANES, Rejected
from krebs.controller import Controller
from krebs.store import Store


@contextmanager
def plane_server():
    state = {
        "native": "fixture-native", "member": True,
        "states": {lane: str(uuid.uuid4()) for lane in LANES},
        "comments": [], "writes": [], "requests": [],
    }
    state["issue"] = {"id": "fixture-ticket", "sequence_id": 7, "name": "Fixture task",
                      "description_html": "<p>Frozen scope</p>",
                      "state": state["states"]["Todo"], "labels": ["unrelated-label"],
                      "assignees": ["existing-assignee"]}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, value):
            body = json.dumps(value).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            state["requests"].append(("GET", self.path))
            assert self.headers.get("X-API-Key") == "public-test-fixture-only"
            if self.path.endswith("/users/me/"):
                return self.reply(200, {"id": state["native"]})
            if self.path.endswith("/members/"):
                # Native membership on page two proves the real pagination path.
                return self.reply(200, {"results": [{"member": {"id": "someone-else"}}],
                                       "next": self.path + "?page=2"})
            if self.path.endswith("/members/?page=2"):
                return self.reply(200, {"results": [{"member": {"id": state["native"]}}]
                                       if state["member"] else [], "next": None})
            if self.path.endswith("/states/"):
                return self.reply(200, [{"name": lane, "id": ident}
                                       for lane, ident in state["states"].items()])
            if self.path.endswith("/labels/"):
                return self.reply(200, [{"id": "working-label", "name": "agent:working"}])
            if self.path.endswith("/comments/"):
                if state.get("attention_patch_applied"):
                    state["comment_reads_after_patch"] = state.get("comment_reads_after_patch", 0) + 1
                    if state.get("fail_before_comment") and state["comment_reads_after_patch"] == 2:
                        state["fail_before_comment"] = False
                        return self.reply(503, {"error": "fixture read outage before comment"})
                return self.reply(200, state["comments"])
            if self.path.endswith("/issues/"):
                return self.reply(200, [state["issue"]])
            if self.path.endswith("/issues/fixture-ticket/"):
                return self.reply(200, state["issue"])
            return self.reply(404, {"error": "unexpected fixture request"})

        def do_PATCH(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["writes"].append(("PATCH", self.path, body))
            state["issue"].update(body)
            if state.get("edit_scope_on_state") == body.get("state"):
                state["issue"]["name"] = "Human changed scope during transition"
            if body.get("state") == state["states"]["Needs Attention"]:
                state["attention_patch_applied"] = True
                if state.get("lose_patch_response"):
                    state["lose_patch_response"] = False
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    return
            self.reply(200, state["issue"])

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["writes"].append(("POST", self.path, body))
            assert self.path.endswith("/comments/"), self.path
            comment = {"id": str(uuid.uuid4()), **body}
            state["comments"].append(comment)
            if state.get("lose_comment_response"):
                state["lose_comment_response"] = False
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            self.reply(201, comment)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.fixture
def provider_world(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    pilot = Path(os.environ.get("KREBS_TEST_PILOT", str(root.parent / "pilot")))
    helper = pilot / "src/provider-helper.js"
    assert helper.is_file(), "Pilot checkout required (KREBS_TEST_PILOT)"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    op = bin_dir / "op"
    op.write_text("#!/bin/sh\nprintf '%s' public-test-fixture-only\n")
    op.chmod(0o700)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    skill = root / "momo/skill/SKILL.md"
    actor = {"native_user_id": "fixture-native", "key_ref": "op://DeLoSecrets/fixture/key",
             "role": "pm", "runtime_id": "fixture-host",
             "runtime": {"adapter": "systemd", "unit_prefix": "fixture-worker", "planner_argv": ["/usr/bin/true"]}}
    with plane_server() as (state, base):
        project = {"base": base, "workspace": "fixture", "board": "fixture-board",
                   "manifest": str(tmp_path / ".project.json"), "states": state["states"],
                   "working_label": "working-label", "skill_path": str(skill),
                   "skill_version": hashlib.sha256(skill.read_bytes()).hexdigest(),
                   "pilot_helper_sha256": hashlib.sha256(helper.read_bytes()).hexdigest(),
                   "pilot_bundle_sha256": bundle_digest(pilot, "pilot"),
                   "momo_bundle_sha256": bundle_digest(skill.parent, "momo"),
                   "mode": "managed", "policy_version": 2, "pm_actor": "pm", "controller_actor": "repair",
                   "legacy_writers_fenced": True, "actors": {"pm": actor, "repair": {
                       "native_user_id": "fixture-repair", "key_ref": "op://DeLoSecrets/fixture/repair",
                       "role": "operator", "runtime_id": "fixture-controller",
                       "runtime": {"adapter": "systemd", "unit_prefix": "fixture-repair"}}}}
        yield PilotProvider(helper), project, actor, state


@pytest.mark.parametrize("failure", [None, "lose_patch_response", "lose_comment_response", "fail_before_comment", "scope_change"])
def test_real_provider_preserves_unrelated_labels_assigns_native_and_posts_one_question(provider_world, failure):
    provider, project, actor, state = provider_world
    dsn = os.environ.get("KREBS_TEST_DSN")
    if not dsn:
        pytest.skip("disposable Postgres required for durable provider authorization")
    project.update(project_id="http-test-" + uuid.uuid4().hex, board=str(uuid.uuid4()),
                   mode="managed", policy_version=2, pm_actor="pm", controller_actor="repair",
                   legacy_writers_fenced=True)
    actor.update(role="pm", runtime_id="fixture-host",
                 runtime={"adapter": "systemd", "unit_prefix": "fixture-worker", "planner_argv": ["/usr/bin/true"]})
    project["actors"] = {"pm": actor, "repair": {
        "role": "operator", "native_user_id": "fixture-repair", "key_ref": "op://DeLoSecrets/fixture/repair",
        "runtime_id": "fixture-controller", "runtime": {"adapter": "systemd", "unit_prefix": "fixture-repair"}}}

    class Registry:
        def authenticate(self, command, auth):
            assert auth == "pm"
            return project, actor

    class Runtime:
        def start(self, *args):
            return {"started": True}

        def present(self, *args):
            return True

        def stop(self, *args):
            return {"stopped": True}

    store = Store(dsn)
    store.migrate()
    controller = Controller(store, Registry(), provider, Runtime())
    run = str(uuid.uuid4())

    def command(operation, payload):
        with store.board_lock(project["project_id"]) as conn:
            board = store.board(conn, project)
        ident = str(uuid.uuid4())
        return {"version": 2, "operation": operation, "project_id": project["project_id"],
                "command_id": ident, "idempotency_key": ident, "ticket_id": "fixture-ticket",
                "actor_id": "pm", "runtime_id": "fixture-host", "run_id": run,
                "generation": board["generation"], "expected_revision": board["revision"],
                "correlation_id": ident, "causation_id": ident, "payload": payload}

    assert provider.verify(project, actor)["native_user_id"] == actor["native_user_id"]
    initial = provider.ticket(project, actor, "FIXTURE-7")
    assert initial["id"] == "fixture-ticket" and initial["lane"] == "Todo"
    claim = command("claim", {"acceptance": {"profile": "fixture"}, "artifact": "fixture-commit",
                              "ticket_revision": initial["revision"]})
    assert controller.execute(claim, "pm")["lane"] == "In Progress"
    assert set(state["issue"]["labels"]) == {"unrelated-label", "working-label"}
    assert set(state["issue"]["assignees"]) == {"existing-assignee", "fixture-native"}
    attention = command("attention", {"question_id": "fixture-question", "question": "Use <A> or B?",
                                      "context": "Current café scope"})
    if failure and failure != "scope_change":
        state[failure] = True
        with pytest.raises(Rejected):
            controller.execute(attention, "pm")
        # Recreate the controller to exercise persisted step recovery rather
        # than relying on any in-process knowledge of the HTTP result.
        controller = Controller(store, Registry(), provider, Runtime())
    receipt = controller.execute(attention, "pm")
    assert receipt["lane"] == "Needs Attention"
    assert controller.execute(attention, "pm") == receipt
    assert len(state["comments"]) == 1
    assert "question_id=fixture-question" in state["comments"][0]["comment_html"]
    assert "&lt;A&gt;" in state["comments"][0]["comment_html"]
    assert state["issue"]["labels"] == ["unrelated-label"]
    assert len(state["writes"]) == 3
    # Resume under a fresh generation, deliver the artifact, and move through
    # each exact review/documentation lane using the same production adapter.
    run = str(uuid.uuid4())
    current = provider.ticket(project, actor, "fixture-ticket")
    acceptance = {"profile": "fixture"}
    resumed = command("resume", {"question_id": "fixture-question", "answer": "Use A",
                                 "acceptance": acceptance, "artifact": "delivered-commit",
                                 "ticket_revision": current["revision"]})
    assert controller.execute(resumed, "pm")["generation"] == 2
    controller.execute(command("start", {"argv": ["/usr/bin/true"]}), "pm")
    controller.execute(command("finish", {"outcome": "success", "artifact": "delivered-commit"}), "pm")
    for kind in ("spec", "quality"):
        review = command("review", {"artifact": "delivered-commit", "acceptance": acceptance,
                                     "kind": kind, "passed": True, "receipt": "fixture-review:" + kind})
        review["run_id"] = str(uuid.uuid4())
        controller.execute(review, "pm")
    evidence = {"artifact": "delivered-commit", "acceptance": acceptance}
    for gate in ("tests", "docs", "notebook", "skill", "main", "push", "deployment"):
        evidence[gate] = {"passed": True, "receipt": "fixture-evidence:" + gate}
    if failure == "scope_change":
        state["edit_scope_on_state"] = state["states"]["E2E Testing & QA"]
        with pytest.raises(Rejected, match="content changed"):
            controller.execute(command("handoff", {"lane": "E2E Testing & QA", "evidence": evidence}), "pm")
        with store.board_lock(project["project_id"]) as conn:
            board = store.board(conn, project)
            assert board["active"]["revoked"] and board["active"]["acceptance"] is None
        assert state["issue"]["state"] != state["states"]["Done"]
        return
    for lane in ("E2E Testing & QA", "Ready for Documentation", "Done"):
        result = controller.execute(command("complete" if lane == "Done" else "handoff",
                                             {"lane": lane, "evidence": evidence}), "pm")
        assert result["lane"] == lane
        assert state["issue"]["state"] == state["states"][lane]
    with store.board_lock(project["project_id"]) as conn:
        assert store.board(conn, project)["active"] is None
    assert state["issue"]["labels"] == ["unrelated-label"]
    assert len(state["comments"]) == 1


def test_provider_apply_without_durable_intent_is_rejected(provider_world):
    provider, project, actor, state = provider_world
    with pytest.raises(Rejected):
        provider.apply(project, actor, "fixture-ticket", {"lane": "In Progress"}, str(uuid.uuid4()))
    assert state["writes"] == []


@pytest.mark.parametrize("failure", ["identity", "membership", "lane"])
def test_real_provider_rejects_enrollment_before_mutation(provider_world, failure):
    provider, project, actor, state = provider_world
    if failure == "identity":
        actor["native_user_id"] = "wrong-native"
    elif failure == "membership":
        state["member"] = False
    else:
        project["states"] = {**state["states"], "Needs Attention": "wrong-state"}
    with pytest.raises(Rejected):
        provider.verify(project, actor)
    assert state["requests"], "must reach real provider enrollment checks"
    assert state["writes"] == []
