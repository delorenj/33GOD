#!/usr/bin/env python3
"""form-intake: one form backend for every page we host.

Any page on a *.delo.sh site can POST a form to its own origin at
``/_forms/<form>`` (Traefik routes that path on every delo.sh host here, see
``~/docker/core/traefik/traefik-data/dynamic/form-intake.yml``). No CORS, no
per-site backend, no third-party form service.

Each submission is:

1. stored first, in SQLite (``FORM_INTAKE_DB``, default
   ``~/.local/state/form-intake/forms.db``), so nothing depends on the bus being up;
2. then announced on Bloodbank as ``bloodbank.messaging.webform.received`` via
   ``bb emit --strict`` (the ntfy router turns that into a push), and the row is
   marked ``emitted`` once the bus accepted it. ``form-intake replay`` re-emits
   any row that never made it.

Stdlib only. Run ``form_intake.py serve`` (the systemd unit does), and
``form_intake.py list [--form F] [--site S]`` to read what came in.

Request contract (JSON or urlencoded body, max 16 KiB):

* field values are strings; up to 40 fields of up to 4000 chars each
* ``email``, when present, must look like an address
* names starting with ``_`` are not stored; ``_hp`` is the honeypot: a
  non-empty value gets a fake 201 and is dropped
* per-IP rate limit: 8 submissions per 10 minutes

Responses: ``201 {"ok": true, "id": ...}``, ``400``/``413``/``429`` with
``{"ok": false, "error": ...}``.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl

DB_PATH = Path(os.environ.get("FORM_INTAKE_DB", Path.home() / ".local/state/form-intake/forms.db"))
LISTEN = os.environ.get("FORM_INTAKE_LISTEN", "172.17.0.1:18811")
BB = os.environ.get("FORM_INTAKE_BB", str(Path.home() / ".local/bin/bb"))
SITE_RE = re.compile(os.environ.get("FORM_INTAKE_SITES", r"^([a-z0-9-]+\.)*delo\.sh$"))
EVENT_TYPE = "bloodbank.messaging.webform.received"

FORM_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
FIELD_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[A-Za-z]{2,}$")
MAX_BODY = 16 * 1024
MAX_FIELDS = 40
MAX_VALUE = 4000
RATE_N, RATE_WINDOW = 8, 600

SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
  id TEXT PRIMARY KEY,
  received_at TEXT NOT NULL,
  site TEXT NOT NULL,
  form TEXT NOT NULL,
  fields TEXT NOT NULL,
  page_url TEXT,
  ip TEXT,
  user_agent TEXT,
  emitted INTEGER NOT NULL DEFAULT 0,
  emit_error TEXT
);
CREATE INDEX IF NOT EXISTS idx_submissions_form ON submissions(site, form, received_at);
"""

_db_lock = threading.Lock()
_hits: dict[str, deque] = defaultdict(deque)


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


class Rejected(Exception):
    def __init__(self, status: int, error: str):
        super().__init__(error)
        self.status, self.error = status, error


def parse_fields(raw: bytes, content_type: str) -> dict[str, str]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise Rejected(400, "body is not utf-8")
    if "application/json" in content_type:
        try:
            data = json.loads(text) if text.strip() else {}
        except json.JSONDecodeError:
            raise Rejected(400, "body is not valid JSON")
        if not isinstance(data, dict):
            raise Rejected(400, "body must be a JSON object")
        pairs = list(data.items())
    else:
        pairs = parse_qsl(text, keep_blank_values=True)
    fields: dict[str, str] = {}
    for name, value in pairs:
        if not isinstance(name, str) or not FIELD_RE.match(name):
            raise Rejected(400, f"bad field name: {str(name)[:40]!r}")
        if isinstance(value, (int, float, bool)):
            value = json.dumps(value)
        if not isinstance(value, str):
            raise Rejected(400, f"field {name!r} must be a string")
        if len(value) > MAX_VALUE:
            raise Rejected(413, f"field {name!r} is too long")
        fields[name] = value.strip()
    if len(fields) > MAX_FIELDS:
        raise Rejected(413, "too many fields")
    return fields


def rate_ok(ip: str, now: float) -> bool:
    q = _hits[ip]
    while q and now - q[0] > RATE_WINDOW:
        q.popleft()
    if len(q) >= RATE_N:
        return False
    q.append(now)
    return True


def event_data(row: sqlite3.Row) -> dict:
    fields = json.loads(row["fields"])
    email = fields.get("email", "")
    name = fields.get("name", "")
    message = fields.get("message") or ", ".join(f"{k}: {v}" for k, v in fields.items())[:500]
    data = {
        "schema_version": 1,
        "direction": "inbound",
        "site": row["site"],
        "form": row["form"],
        "sender": {"handle": email or "anonymous", **({"display_name": name} if name else {})},
        "content": {"text": message or "(empty)", "format": "plain"},
        "fields": fields,
        "received_at": row["received_at"],
        "message_id": row["id"],
        "thread_id": f"{row['site']}:{row['form']}",
    }
    if row["page_url"]:
        data["page_url"] = row["page_url"]
    return data


def emit(submission_id: str) -> bool:
    """Publish one stored row; mark it emitted. Returns True on success."""
    with _db_lock, db() as conn:
        row = conn.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    if row is None:
        return False
    err = None
    try:
        proc = subprocess.run(
            [BB, "emit", "--strict", "--type", EVENT_TYPE, "--source", f"urn:33god:form-intake:{row['site']}",
             "--producer", "form-intake", "--service", "form-intake", "--actor-type", "service",
             "--actor-id", "form-intake", "--data", json.dumps(event_data(row))],
            capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout).strip()[-500:] or f"exit {proc.returncode}"
    except Exception as exc:  # noqa: BLE001 -- recorded on the row, replayable
        err = repr(exc)[:500]
    with _db_lock, db() as conn:
        conn.execute("UPDATE submissions SET emitted = ?, emit_error = ? WHERE id = ?",
                     (0 if err else 1, err, submission_id))
    if err:
        print(f"form-intake: emit failed for {submission_id}: {err}", file=sys.stderr, flush=True)
    return err is None


class Handler(BaseHTTPRequestHandler):
    server_version = "form-intake/1"

    def _send(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _site(self) -> str:
        host = (self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or "").split(",")[0]
        return host.strip().split(":")[0].lower()

    def _ip(self) -> str:
        for h in ("CF-Connecting-IP", "X-Real-IP", "X-Forwarded-For"):
            v = self.headers.get(h)
            if v:
                return v.split(",")[0].strip()
        return self.client_address[0]

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") in ("/_forms", "/_forms/health"):
            return self._send(200, {"ok": True, "service": "form-intake"})
        if self.path.rstrip("/") == "/_forms/whoami":
            return self._send(200, {"site": self._site(), "ip": self._ip(), "headers": {
                h: self.headers.get(h) for h in ("CF-Connecting-IP", "X-Real-IP", "X-Forwarded-For", "X-Forwarded-Host")}})
        self._send(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            parts = self.path.split("?")[0].strip("/").split("/")
            if len(parts) != 2 or parts[0] != "_forms" or not FORM_RE.match(parts[1]):
                raise Rejected(404, "POST /_forms/<form>, form = [a-z0-9-]")
            form, site = parts[1], self._site()
            if not SITE_RE.match(site):
                raise Rejected(400, f"site {site!r} is not served")
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise Rejected(413, "body too large")
            fields = parse_fields(self.rfile.read(length), self.headers.get("Content-Type", ""))
            if fields.get("_hp"):
                return self._send(201, {"ok": True, "id": str(uuid.uuid4())})
            fields = {k: v for k, v in fields.items() if not k.startswith("_")}
            if not any(fields.values()):
                raise Rejected(400, "empty submission")
            if "email" in fields and not EMAIL_RE.match(fields["email"]):
                raise Rejected(400, "That email address does not look right.")
            if not rate_ok(self._ip(), time.monotonic()):
                raise Rejected(429, "Too many tries from here. Wait a few minutes and try again.")
            sid = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            with _db_lock, db() as conn:
                conn.execute(
                    "INSERT INTO submissions (id, received_at, site, form, fields, page_url, ip, user_agent)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (sid, now, site, form, json.dumps(fields), (self.headers.get("Referer") or "")[:500] or None,
                     self._ip(), (self.headers.get("User-Agent") or "")[:300]))
            threading.Thread(target=emit, args=(sid,), daemon=True).start()
            self._send(201, {"ok": True, "id": sid})
        except Rejected as r:
            self._send(r.status, {"ok": False, "error": r.error})
        except Exception as exc:  # noqa: BLE001
            print(f"form-intake: {exc!r}", file=sys.stderr, flush=True)
            self._send(500, {"ok": False, "error": "Could not save that. Try again in a minute."})

    def log_message(self, fmt: str, *args) -> None:
        print(f"form-intake: {self._ip()} {fmt % args}", file=sys.stderr, flush=True)


def cmd_serve(_: argparse.Namespace) -> int:
    host, port = LISTEN.rsplit(":", 1)
    db().close()
    srv = ThreadingHTTPServer((host, int(port)), Handler)
    print(f"form-intake: listening on {LISTEN}, db {DB_PATH}", file=sys.stderr, flush=True)
    srv.serve_forever()
    return 0


def cmd_list(a: argparse.Namespace) -> int:
    q, args = "SELECT * FROM submissions WHERE 1=1", []
    if a.form:
        q += " AND form = ?"; args.append(a.form)
    if a.site:
        q += " AND site = ?"; args.append(a.site)
    q += " ORDER BY received_at DESC LIMIT ?"; args.append(a.limit)
    with db() as conn:
        rows = [dict(r) | {"fields": json.loads(r["fields"])} for r in conn.execute(q, args)]
    if a.json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            mark = "" if r["emitted"] else "  [not on bus]"
            print(f"{r['received_at']}  {r['site']}/{r['form']}  {json.dumps(r['fields'])}{mark}")
    return 0


def cmd_replay(_: argparse.Namespace) -> int:
    with db() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM submissions WHERE emitted = 0")]
    failed = [i for i in ids if not emit(i)]
    print(f"replayed {len(ids) - len(failed)}/{len(ids)}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="form-intake", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("serve", help="run the HTTP intake").set_defaults(fn=cmd_serve)
    ls = sub.add_parser("list", help="show recent submissions")
    ls.add_argument("--form"); ls.add_argument("--site"); ls.add_argument("--limit", type=int, default=50)
    ls.add_argument("--json", action="store_true")
    ls.set_defaults(fn=cmd_list)
    sub.add_parser("replay", help="re-emit rows the bus never accepted").set_defaults(fn=cmd_replay)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
