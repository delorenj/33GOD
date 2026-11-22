"""form-intake: the /_forms/<form> backend (33god-platform/form-intake).

Runs the real HTTP handler on a loopback port against a temp SQLite DB and a
stub `bb` that records what it was asked to publish.
"""
from __future__ import annotations

import importlib.util
import json
import os
import stat
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "form-intake" / "form_intake.py"


@pytest.fixture()
def intake(tmp_path, monkeypatch):
    log = tmp_path / "bb.log"
    bb = tmp_path / "bb"
    bb.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" >> {log}\n[ -f {tmp_path}/fail ] && exit 3\nexit 0\n")
    bb.chmod(bb.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("FORM_INTAKE_DB", str(tmp_path / "forms.db"))
    monkeypatch.setenv("FORM_INTAKE_BB", str(bb))
    spec = importlib.util.spec_from_file_location("form_intake_under_test", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), mod.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def post(path, body, host="33god.delo.sh", ctype="application/json", ip="203.0.113.9"):
        data = json.dumps(body).encode() if ctype == "application/json" else body.encode()
        req = urllib.request.Request(base + path, data=data, method="POST", headers={
            "Content-Type": ctype, "X-Forwarded-Host": host, "CF-Connecting-IP": ip,
            "Referer": f"https://{host}/"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    yield mod, post, log, tmp_path
    srv.shutdown()


def _wait_emitted(mod, sid, want=1):
    for _ in range(50):
        with mod.db() as c:
            row = c.execute("SELECT emitted, emit_error FROM submissions WHERE id=?", (sid,)).fetchone()
        if row and (row["emitted"] == want and (want or row["emit_error"])):
            return row
        time.sleep(0.05)
    raise AssertionError(f"row {sid} never reached emitted={want}")


def test_stores_then_publishes(intake):
    mod, post, log, _ = intake
    status, body = post("/_forms/briefing", {"email": "a@example.com", "_page": "tour"})
    assert status == 201 and body["ok"]
    _wait_emitted(mod, body["id"])
    with mod.db() as c:
        row = c.execute("SELECT * FROM submissions WHERE id=?", (body["id"],)).fetchone()
    assert row["site"] == "33god.delo.sh" and row["form"] == "briefing"
    assert json.loads(row["fields"]) == {"email": "a@example.com"}  # _-prefixed dropped
    args = log.read_text().splitlines()
    assert args[args.index("--type") + 1] == "bloodbank.messaging.webform.received"
    data = json.loads(args[args.index("--data") + 1])
    assert data["sender"]["handle"] == "a@example.com"
    assert data["thread_id"] == "33god.delo.sh:briefing" and data["message_id"] == body["id"]


def test_bus_down_keeps_row_and_replay_recovers(intake):
    mod, post, _, tmp = intake
    (tmp / "fail").write_text("")
    status, body = post("/_forms/briefing", {"email": "b@example.com"})
    assert status == 201
    row = _wait_emitted(mod, body["id"], want=0)
    assert row["emit_error"]
    (tmp / "fail").unlink()
    assert mod.cmd_replay(None) == 0
    _wait_emitted(mod, body["id"])


def test_urlencoded_body(intake):
    _, post, _, _ = intake
    status, body = post("/_forms/contact", "email=c%40example.com&message=hi", ctype="application/x-www-form-urlencoded")
    assert status == 201, body


@pytest.mark.parametrize("path,payload,host,code", [
    ("/_forms/briefing", {"email": "nope"}, "33god.delo.sh", 400),
    ("/_forms/briefing", {}, "33god.delo.sh", 400),
    ("/_forms/Bad_Slug", {"email": "a@example.com"}, "33god.delo.sh", 404),
    ("/_forms/briefing", {"email": "a@example.com"}, "evil.example.com", 400),
    ("/_forms/briefing", {"email": "a@example.com", "x": "y" * 5000}, "33god.delo.sh", 413),
    ("/_forms/briefing", {"bad name!": "x"}, "33god.delo.sh", 400),
])
def test_rejections(intake, path, payload, host, code):
    _, post, _, _ = intake
    status, body = post(path, payload, host=host)
    assert status == code and body["ok"] is False and body["error"]


def test_honeypot_fakes_success_and_stores_nothing(intake):
    mod, post, _, _ = intake
    status, body = post("/_forms/briefing", {"email": "bot@example.com", "_hp": "gotcha"})
    assert status == 201 and body["ok"]
    with mod.db() as c:
        assert c.execute("SELECT count(*) FROM submissions").fetchone()[0] == 0


def test_rate_limit_per_ip(intake):
    mod, post, _, _ = intake
    for i in range(mod.RATE_N):
        assert post("/_forms/briefing", {"email": f"r{i}@example.com"}, ip="198.51.100.7")[0] == 201
    assert post("/_forms/briefing", {"email": "r@example.com"}, ip="198.51.100.7")[0] == 429
    assert post("/_forms/briefing", {"email": "r@example.com"}, ip="198.51.100.8")[0] == 201
