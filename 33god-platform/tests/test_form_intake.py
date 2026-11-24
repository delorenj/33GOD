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


class _Keep3xx(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):  # a 303 is the answer under test, not something to follow
        return None


_NO_REDIRECTS = urllib.request.build_opener(_Keep3xx)


@pytest.fixture()
def intake(tmp_path, monkeypatch):
    log = tmp_path / "bb.log"
    bb = tmp_path / "bb"
    bb.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" >> {log}\n[ -f {tmp_path}/fail ] && exit 3\nexit 0\n")
    bb.chmod(bb.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("FORM_INTAKE_DB", str(tmp_path / "forms.db"))
    monkeypatch.setenv("FORM_INTAKE_BB", str(bb))
    monkeypatch.setenv("FORM_INTAKE_CORS_ORIGINS", "https://store.automaticai.io, https://Other.Example.org/")
    spec = importlib.util.spec_from_file_location("form_intake_under_test", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), mod.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def call(method, path, body=None, host="33god.delo.sh", ctype="application/json", ip="203.0.113.9", origin=None,
             headers=None):
        data = None
        if body is not None:
            data = json.dumps(body).encode() if ctype == "application/json" else body.encode()
        hdrs = {"Content-Type": ctype, "X-Forwarded-Host": host, "CF-Connecting-IP": ip, "Referer": f"https://{host}/"}
        if origin is not None:
            hdrs["Origin"] = origin
        hdrs.update(headers or {})
        req = urllib.request.Request(base + path, data=data, method=method, headers=hdrs)
        try:
            with _NO_REDIRECTS.open(req, timeout=5) as r:
                raw, status, hdrs = r.read(), r.status, r.headers
        except urllib.error.HTTPError as e:
            raw, status, hdrs = e.read(), e.code, e.headers
        return status, (json.loads(raw) if raw else None), hdrs

    def post(path, body, **kw):
        status, payload, _ = call("POST", path, body, **kw)
        return status, payload

    post.call = call
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
    assert data["sender"]["handle"] == "a@example.com"  # delo.sh sites: unchanged, the full address
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


# --- cross-origin: sites we host off delo.sh (the store on Cloudflare Pages) -------------------------

STORE = "https://store.automaticai.io"


def _row(mod, sid):
    with mod.db() as c:
        return c.execute("SELECT * FROM submissions WHERE id=?", (sid,)).fetchone()


def test_cors_origins_are_parsed_exactly():
    import importlib.util as u
    spec = u.spec_from_file_location("fi_parse", SRC)
    mod = u.module_from_spec(spec); spec.loader.exec_module(mod)
    assert mod.parse_origins("https://a.example.com, https://B.example.com/  http://localhost:8080") == {
        "https://a.example.com", "https://b.example.com", "http://localhost:8080"}
    assert mod.parse_origins("") == frozenset()
    for bad in ("store.automaticai.io", "https://a.example.com/path", "*", "https://*.example.com"):
        with pytest.raises(ValueError):
            mod.parse_origins(bad)


def test_preflight_from_an_allowlisted_origin(intake):
    _, post, _, _ = intake
    status, body, h = post.call("OPTIONS", "/_forms/store-notify", host="forms.delo.sh", origin=STORE)
    assert status == 204 and body is None
    assert h["Access-Control-Allow-Origin"] == STORE
    assert h["Access-Control-Allow-Methods"] == "POST"
    assert h["Access-Control-Allow-Headers"].lower() == "content-type"
    assert int(h["Access-Control-Max-Age"]) >= 600
    assert "Origin" in h["Vary"]


@pytest.mark.parametrize("origin", ["https://evil.example.com", "https://store.automaticai.io.evil.com",
                                    "http://store.automaticai.io", "null", None])
def test_preflight_refused_for_any_other_origin(intake, origin):
    _, post, _, _ = intake
    status, _, h = post.call("OPTIONS", "/_forms/store-notify", host="forms.delo.sh", origin=origin)
    assert status == 403
    assert "Access-Control-Allow-Origin" not in h


def test_preflight_on_a_bad_path_is_404_without_allowing_anything_else(intake):
    _, post, _, _ = intake
    status, _, h = post.call("OPTIONS", "/_forms/Bad_Slug", host="forms.delo.sh", origin=STORE)
    assert status == 404 and h["Access-Control-Allow-Origin"] == STORE  # so the page can read the error
    assert "Access-Control-Allow-Methods" not in h


def test_allowlisted_cross_origin_post_is_stored_under_the_origin_host(intake):
    mod, post, log, _ = intake
    status, body, h = post.call("POST", "/_forms/store-notify", {"email": "test+heyma@automaticai.io", "product": "heyma", "_hp": ""},
                                host="forms.delo.sh", origin=STORE)
    assert status == 201 and body["ok"], body
    assert h["Access-Control-Allow-Origin"] == STORE and "Origin" in h["Vary"]
    _wait_emitted(mod, body["id"])
    row = _row(mod, body["id"])
    assert row["site"] == "store.automaticai.io" and row["form"] == "store-notify"
    assert json.loads(row["fields"]) == {"email": "test+heyma@automaticai.io", "product": "heyma"}
    args = log.read_text().splitlines()
    assert args[args.index("--source") + 1] == "urn:33god:form-intake:store.automaticai.io"
    data = json.loads(args[args.index("--data") + 1])
    assert data["thread_id"] == "store.automaticai.io:store-notify"
    # The store promises deletion on request: the bus (Candystore keeps every event, ntfy caches the push)
    # gets no address at all, masked or not. The SQLite row is the only copy.
    assert data["fields"] == {"product": "heyma"} and data["withheld"] == ["email"]
    assert data["sender"]["handle"] == "anonymous"
    assert data["content"]["text"] == "store-notify from store.automaticai.io: product: heyma"
    assert "@" not in log.read_text() and "automaticai.io" not in data["content"]["text"].split(": ", 1)[1]


def test_allowlist_matches_case_and_trailing_slash_insensitively(intake):
    mod, post, _, _ = intake
    status, body, h = post.call("POST", "/_forms/store-notify", {"email": "a@example.com"}, host="forms.delo.sh",
                                origin="https://other.example.org")
    assert status == 201 and h["Access-Control-Allow-Origin"] == "https://other.example.org"
    assert _row(mod, body["id"])["site"] == "other.example.org"


def test_errors_to_an_allowlisted_origin_carry_cors_so_the_page_can_show_them(intake):
    _, post, _, _ = intake
    status, body, h = post.call("POST", "/_forms/store-notify", {"email": "nope"}, host="forms.delo.sh", origin=STORE)
    assert status == 400 and body["error"] and h["Access-Control-Allow-Origin"] == STORE


@pytest.mark.parametrize("origin", ["https://evil.example.com", "https://store.automaticai.io.evil.com",
                                    "http://store.automaticai.io", "https://forms.delo.sh.evil.com", "not a url"])
def test_non_allowlisted_cross_origin_post_is_refused_and_stores_nothing(intake, origin):
    mod, post, log, _ = intake
    status, body, h = post.call("POST", "/_forms/store-notify", {"email": "a@example.com", "product": "heyma"},
                                host="forms.delo.sh", origin=origin)
    assert status == 403 and body["ok"] is False
    assert "Access-Control-Allow-Origin" not in h
    with mod.db() as c:
        assert c.execute("SELECT count(*) FROM submissions").fetchone()[0] == 0
    assert not log.exists()


def test_a_urlencoded_cross_origin_post_is_held_to_the_same_allowlist(intake):
    # A plain <form> post needs no preflight, so the POST itself must check the Origin.
    _, post, _, _ = intake
    form = "application/x-www-form-urlencoded"
    assert post("/_forms/store-notify", "email=a%40example.com", host="forms.delo.sh", ctype=form, origin="https://evil.example.com")[0] == 403
    assert post("/_forms/store-notify", "email=a%40example.com", host="forms.delo.sh", ctype=form, origin=STORE)[0] == 201


def test_cross_origin_post_still_needs_a_served_endpoint_host(intake):
    _, post, _, _ = intake
    status, body = post("/_forms/store-notify", {"email": "a@example.com"}, host="evil.example.com", origin=STORE)
    assert status == 400 and "not served" in body["error"]


@pytest.mark.parametrize("origin", [None, "https://33god.delo.sh", "https://33god.delo.sh/", "http://33god.delo.sh"])
def test_same_origin_delo_sh_is_unchanged(intake, origin):
    mod, post, _, _ = intake
    status, body, h = post.call("POST", "/_forms/briefing", {"email": "s@example.com"}, origin=origin)
    assert status == 201, body
    assert "Access-Control-Allow-Origin" not in h
    assert _row(mod, body["id"])["site"] == "33god.delo.sh"


@pytest.mark.parametrize("host", ["33god.delo.sh", "forms.delo.sh"])
@pytest.mark.parametrize("ctype,body", [("application/json", {"email": "victim@example.org", "product": "heyma"}),
                                        ("application/x-www-form-urlencoded", "email=victim%40example.org&product=heyma")])
def test_an_opaque_null_origin_is_refused_everywhere(intake, host, ctype, body):
    # A sandboxed iframe on any third-party page sends Origin: null; none of our pages ever does.
    mod, post, log, _ = intake
    status, payload, h = post.call("POST", "/_forms/store-notify", body, host=host, ctype=ctype, origin="null",
                                   headers={"Sec-Fetch-Mode": "navigate"})
    assert status == 403 and payload["ok"] is False
    assert "Access-Control-Allow-Origin" not in h and "Location" not in h
    with mod.db() as c:
        assert c.execute("SELECT count(*) FROM submissions").fetchone()[0] == 0
    assert not log.exists()


@pytest.mark.parametrize("origin", [None, "https://forms.delo.sh"])
def test_the_cors_endpoint_host_takes_only_an_allowlisted_origin(intake, origin):
    # forms.delo.sh serves no pages, so a row can never be stored under its own name.
    mod, post, _, _ = intake
    status, body = post("/_forms/store-notify", {"email": "a@example.com", "product": "heyma"}, host="forms.delo.sh", origin=origin)
    assert status == 403 and body["ok"] is False
    with mod.db() as c:
        assert c.execute("SELECT count(*) FROM submissions WHERE site = 'forms.delo.sh'").fetchone()[0] == 0


def test_a_delo_sh_row_with_personal_fields_publishes_them_and_an_off_site_row_withholds_them(intake):
    mod, post, log, _ = intake
    status, body, _ = post.call("POST", "/_forms/contact", {"email": "x@example.org", "name": "Ann Lee", "message": "Hi there",
                                                           "product": "heyma", "plan": "Big Plan"}, host="forms.delo.sh", origin=STORE)
    assert status == 201
    _wait_emitted(mod, body["id"])
    args = log.read_text().splitlines()
    data = json.loads(args[args.index("--data") + 1])
    assert data["fields"] == {"product": "heyma"}
    assert data["withheld"] == ["email", "message", "name", "plan"]
    assert "Ann" not in log.read_text() and "Hi there" not in log.read_text() and "@" not in log.read_text()
    assert json.loads(_row(mod, body["id"])["fields"])["name"] == "Ann Lee"  # the row keeps all of it


# --- no JavaScript: a plain form post from a listed site goes back to its page --------------------

NAV = {"Sec-Fetch-Mode": "navigate", "Accept": "text/html,application/xhtml+xml"}
FORM = "application/x-www-form-urlencoded"


def test_a_plain_form_post_from_a_listed_origin_is_303_back_to_its_page(intake):
    mod, post, _, _ = intake
    status, body, h = post.call("POST", "/_forms/store-notify", "email=n%40example.com&product=heyma&_back=%2Fheyma%2F&_hp=",
                                host="forms.delo.sh", ctype=FORM, origin=STORE, headers=NAV)
    assert status == 303 and body is None
    assert h["Location"] == "https://store.automaticai.io/heyma/#store-notify-saved"
    with mod.db() as c:
        rows = c.execute("SELECT * FROM submissions").fetchall()
    assert len(rows) == 1 and json.loads(rows[0]["fields"]) == {"email": "n@example.com", "product": "heyma"}  # _back not stored


@pytest.mark.parametrize("body,frag", [("email=nope&product=heyma&_back=%2Fheyma%2F", "store-notify-error"),
                                       ("email=bot%40example.com&_hp=x&_back=%2Fheyma%2F", "store-notify-saved"),
                                       ("email=&_back=%2Fheyma%2F", "store-notify-error")])
def test_a_plain_form_post_error_or_honeypot_also_goes_back(intake, body, frag):
    mod, post, _, _ = intake
    status, _, h = post.call("POST", "/_forms/store-notify", body, host="forms.delo.sh", ctype=FORM, origin=STORE, headers=NAV)
    assert status == 303 and h["Location"] == f"https://store.automaticai.io/heyma/#{frag}"
    with mod.db() as c:
        assert c.execute("SELECT count(*) FROM submissions").fetchone()[0] == 0


@pytest.mark.parametrize("back", ["%2F%2Fevil.example.com%2F", "https%3A%2F%2Fevil.example.com%2F", "heyma", "%2Fa%3Fb%3Dc"])
def test_the_way_back_never_leaves_the_listed_origin(intake, back):
    _, post, _, _ = intake
    status, _, h = post.call("POST", "/_forms/store-notify", f"email=w%40example.com&product=heyma&_back={back}",
                             host="forms.delo.sh", ctype=FORM, origin=STORE, headers={**NAV, "Referer": "https://evil.example.com/x/"})
    assert status == 303 and h["Location"] == "https://store.automaticai.io/#store-notify-saved"


def test_the_way_back_can_come_from_a_same_origin_referer(intake):
    _, post, _, _ = intake
    status, _, h = post.call("POST", "/_forms/store-notify", "email=r%40example.com&product=heyma", host="forms.delo.sh",
                             ctype=FORM, origin=STORE, headers={**NAV, "Referer": "https://store.automaticai.io/voxxy/?x=1"})
    assert status == 303 and h["Location"] == "https://store.automaticai.io/voxxy/#store-notify-saved"


@pytest.mark.parametrize("ctype,body,headers", [
    ("application/json", {"email": "j@example.com", "product": "heyma"}, NAV),                 # JSON callers: unchanged
    (FORM, "email=f%40example.com&product=heyma", {"Sec-Fetch-Mode": "cors"}),                # a script's urlencoded fetch
])
def test_script_callers_still_get_json(intake, ctype, body, headers):
    _, post, _, _ = intake
    status, payload, h = post.call("POST", "/_forms/store-notify", body, host="forms.delo.sh", ctype=ctype, origin=STORE, headers=headers)
    assert status == 201 and payload["ok"] and "Location" not in h and h["Access-Control-Allow-Origin"] == STORE


def test_a_plain_form_post_from_an_unlisted_origin_is_403_not_a_redirect(intake):
    _, post, _, _ = intake
    status, payload, h = post.call("POST", "/_forms/store-notify", "email=u%40example.com", host="forms.delo.sh", ctype=FORM,
                                   origin="https://evil.example.com", headers=NAV)
    assert status == 403 and payload["ok"] is False and "Location" not in h


def test_same_origin_delo_sh_plain_form_post_still_gets_json(intake):
    _, post, _, _ = intake
    status, payload, h = post.call("POST", "/_forms/contact", "email=d%40example.com", ctype=FORM, origin="https://33god.delo.sh", headers=NAV)
    assert status == 201 and payload["ok"] and "Location" not in h


def test_another_delo_sh_page_cannot_post_cross_origin(intake):
    _, post, _, _ = intake
    status, _ = post("/_forms/briefing", {"email": "s@example.com"}, host="forms.delo.sh", origin="https://overnight.delo.sh")
    assert status == 403


def test_honeypot_from_an_allowlisted_origin_fakes_success_with_cors(intake):
    mod, post, _, _ = intake
    status, body, h = post.call("POST", "/_forms/store-notify", {"email": "bot@example.com", "_hp": "x"}, host="forms.delo.sh", origin=STORE)
    assert status == 201 and body["ok"] and h["Access-Control-Allow-Origin"] == STORE
    with mod.db() as c:
        assert c.execute("SELECT count(*) FROM submissions").fetchone()[0] == 0


# --- reading and deleting rows ----------------------------------------------------------------------

def _cli(mod, capsys, *argv):
    capsys.readouterr()
    assert mod.main(list(argv)) == 0
    return capsys.readouterr().out


def test_list_emails_by_product_is_the_one_time_send_list(intake, capsys):
    mod, post, _, _ = intake
    for email, product in [("A@example.com", "heyma"), ("b@example.com", "heyma"), ("a@example.com", "heyma"), ("c@example.com", "voxxy")]:
        assert post.call("POST", "/_forms/store-notify", {"email": email, "product": product}, host="forms.delo.sh", origin=STORE)[0] == 201
    out = _cli(mod, capsys, "list", "--form", "store-notify", "--field", "product=heyma", "--emails")
    assert out.split() == ["a@example.com", "b@example.com"]
    assert "c@example.com" in _cli(mod, capsys, "list", "--form", "store-notify", "--site", "store.automaticai.io")


def test_delete_by_email_and_by_field(intake, capsys):
    mod, post, _, _ = intake
    for email, product in [("x@example.com", "heyma"), ("y@example.com", "heyma"), ("x@example.com", "voxxy")]:
        assert post.call("POST", "/_forms/store-notify", {"email": email, "product": product}, host="forms.delo.sh", origin=STORE)[0] == 201
    assert _cli(mod, capsys, "delete", "--email", "X@Example.com").strip() == "deleted 2"
    assert _cli(mod, capsys, "delete", "--form", "store-notify", "--field", "product=heyma").strip() == "deleted 1"
    with mod.db() as c:
        assert c.execute("SELECT count(*) FROM submissions").fetchone()[0] == 0
    with pytest.raises(SystemExit):
        mod.main(["delete"])
