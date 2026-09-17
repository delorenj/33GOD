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
import threading
import uuid

import pytest

from krebs.adapters import PilotProvider
from krebs.contract import LANES, Rejected


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
            self.reply(200, state["issue"])

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["writes"].append(("POST", self.path, body))
            assert self.path.endswith("/comments/"), self.path
            comment = {"id": str(uuid.uuid4()), **body}
            state["comments"].append(comment)
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
    actor = {"native_user_id": "fixture-native", "key_ref": "op://DeLoSecrets/fixture/key"}
    with plane_server() as (state, base):
        project = {"base": base, "workspace": "fixture", "board": "fixture-board",
                   "manifest": str(tmp_path / ".project.json"), "states": state["states"],
                   "working_label": "working-label", "skill_path": str(skill),
                   "skill_version": hashlib.sha256(skill.read_bytes()).hexdigest(),
                   "pilot_helper_sha256": hashlib.sha256(helper.read_bytes()).hexdigest()}
        yield PilotProvider(helper), project, actor, state


def test_real_provider_preserves_unrelated_labels_assigns_native_and_posts_one_question(provider_world):
    provider, project, actor, state = provider_world
    assert provider.verify(project, actor)["native_user_id"] == actor["native_user_id"]
    initial = provider.ticket(project, actor, "FIXTURE-7")
    assert initial["id"] == "fixture-ticket" and initial["lane"] == "Todo"
    action = {"lane": "In Progress", "working": True, "assign": True}
    marker = str(uuid.uuid4())
    assert not provider.reconcile(project, actor, initial["id"], action, marker)["matched"]
    provider.apply(project, actor, initial["id"], action, marker)
    assert provider.reconcile(project, actor, initial["id"], action, marker)["matched"]
    assert set(state["issue"]["labels"]) == {"unrelated-label", "working-label"}
    assert set(state["issue"]["assignees"]) == {"existing-assignee", "fixture-native"}
    action = {"lane": "Needs Attention", "working": False,
              "question": {"id": "fixture-question", "text": "Use <A> or B?", "context": "Current café scope"}}
    marker = str(uuid.uuid4())
    provider.apply(project, actor, initial["id"], action, marker)
    assert provider.reconcile(project, actor, initial["id"], action, marker)["matched"]
    provider.apply(project, actor, initial["id"], action, marker)
    assert len(state["comments"]) == 1
    assert "question_id=fixture-question" in state["comments"][0]["comment_html"]
    assert "&lt;A&gt;" in state["comments"][0]["comment_html"]
    assert state["issue"]["labels"] == ["unrelated-label"]
    assert len(state["writes"]) == 3


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
        provider.apply(project, actor, "fixture-ticket", {"lane": "In Progress"}, str(uuid.uuid4()))
    assert state["writes"] == []
