"""Guard for the overnight marketing page (overnight/site, served live at 33god.delo.sh).

The page reads its words from manifest.json and its scroll geometry from score.json, with no build step,
so a hand edit goes live the moment it is saved. These tests catch the three ways an edit breaks it:

  1. a file that does not parse (an invalid "\\." escape once blanked the whole page),
  2. a file that parses but does not match (score majors vs manifest beats, missing copy the JS reads),
  3. copy that overflows its slot (budgets measured in a real browser, see BUDGETS).

Run:      cd 33god-platform && python3 -m pytest tests/test_overnight_site.py -q
Browser:  OVERNIGHT_LAYOUT=1 python3 -m pytest tests/test_overnight_site.py -q -k Layout   (needs playwright + chromium)
Point at a copy of the site (to prove the guard catches a break): OVERNIGHT_SITE=/tmp/copy-of-site
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

SITE = Path(os.environ.get("OVERNIGHT_SITE") or Path(__file__).resolve().parents[1] / "overnight" / "site")


# ---------------------------------------------------------------- loading, with file:line:col errors

def _no_dupes(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise ValueError(f"duplicate key {k!r} (the last one silently wins)")
        seen[k] = v
    return dict(pairs)


def load(path: Path):
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text, object_pairs_hook=_no_dupes)
    except json.JSONDecodeError as e:
        rows = text.split("\n")
        lo, hi = max(1, e.lineno - 1), min(len(rows), e.lineno + 1)
        excerpt = []
        for n in range(lo, hi + 1):
            excerpt.append(f"{n:>5} | {rows[n - 1][:200]}")
            if n == e.lineno:
                excerpt.append(" " * (8 + max(0, e.colno - 1)) + "^")
        raise AssertionError(f"{path.name} does not parse: {e.msg} (line {e.lineno}, column {e.colno})\n" + "\n".join(excerpt)) from None
    except ValueError as e:
        raise AssertionError(f"{path.name}: {e}") from None


def manifest():
    return load(SITE / "manifest.json")


def score():
    return load(SITE / "score.json")


def beat(M, bid):
    return next(b for b in M["beats"] if b["id"] == bid)


def walk(x, path=""):
    """Every (path, value) leaf string in the manifest."""
    if isinstance(x, str):
        yield path, x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f"{path}[{i}]")


def mins(t: str) -> int:
    """The page's mins(): HH:MM before 12:00 counts as the next day, so the night runs 18:02 -> 07:41."""
    h, m = (int(p) for p in t.split(":"))
    v = h * 60 + m
    return v + 1440 if v < 720 else v


# ---------------------------------------------------------------- 1. every JSON parses

def test_every_json_parses():
    files = sorted(SITE.rglob("*.json"))
    assert {f.name for f in files} >= {"manifest.json", "score.json"}
    for f in files:
        load(f)


def test_nights_digest():
    for f in sorted((SITE / "nights").glob("*.json")):
        N = load(f)
        assert N.get("format") == "33god.night", f.name
        assert N.get("version") == 1, f.name
        W = N.get("window") or {}
        assert isinstance(W.get("minutes"), int) and W["minutes"] > 0, f"{f.name}: window.minutes"
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d", W.get("local_since", "")), f"{f.name}: window.local_since"


# ---------------------------------------------------------------- 2. shape: what the JS dereferences

def test_manifest_shape():
    M = manifest()
    for k in ("site", "acts", "beats", "transcript", "nameplates"):
        assert k in M, f"manifest.json: missing {k}"
    ids = [b["id"] for b in M["beats"]]
    assert len(ids) == len(set(ids)), "duplicate beat ids"
    prev = -1
    for b in M["beats"]:
        i = b["id"]
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", i), f"{i}: id is not kebab-case"
        assert re.fullmatch(r"\d\d:\d\d", b["time"]), f"{i}: time"
        assert b["act"] in M["acts"], f"{i}: act {b['act']!r} is not in acts"
        for k in ("kicker", "title", "body"):
            assert isinstance(b.get(k), str), f"{i}: {k} must be a string"
        assert isinstance(b.get("tags"), list), f"{i}: tags"
        assert isinstance(b.get("log"), list) and b["log"], f"{i}: log needs at least one line (the log view shows only this)"
        for l in b["log"]:
            assert isinstance(l.get("subject"), str) and isinstance(l.get("note"), str), f"{i}: log line needs subject and note"
        assert mins(b["time"]) >= prev, f"{i}: time {b['time']} runs backwards"
        prev = mins(b["time"])
        if "interlude" in b:
            assert b["interlude"].get("kicker") and b["interlude"].get("line"), f"{i}: interlude needs kicker and line"
    for n in M["site"]["nav"]:
        assert n["beat"] in ids, f"nav {n['label']!r} points at missing beat {n['beat']}"
    c = lambda bid: beat(M, bid)["copy"]  # noqa: E731
    for s in c("staff")["staff"]:
        assert s.get("name") and s.get("line"), f"staff entry needs name and line: {s}"
    for d in c("org-chart")["departments"]:
        assert d.get("dept") and d.get("name") and d.get("line"), f"department needs dept, name, line: {d}"
    assert c("org-chart")["you"].get("label") and c("org-chart")["you"].get("line")
    for f in c("numbers")["figures"]:
        assert f.get("n") and f.get("label"), f"figure needs n and label: {f}"
    assert c("numbers")["stamp"]
    for bid, k in (("pjangler", "checklist"), ("flume", "pipeline"), ("holocene-auto", "standup"), ("runs-on-itself", "steps")):
        assert c(bid)[k], f"{bid}.copy.{k}"
    for k in ("speakers", "judgments", "tickets", "lines"):
        assert M["transcript"][k], f"transcript.{k}"
    # Regression pin: the thesis beat sits between the hero and the numbers.
    assert ids.index("premise") + 1 == ids.index("thesis") == ids.index("numbers") - 1, "thesis must sit between premise and numbers"


def test_score_matches_manifest():
    M, S = manifest(), score()
    mids, sids = [b["id"] for b in M["beats"]], [m["id"] for m in S["majors"]]
    if mids != sids:
        k = next((i for i, (a, b) in enumerate(zip(mids, sids)) if a != b), min(len(mids), len(sids)))
        pytest.fail(f"score.json majors differ from manifest beats at index {k}: manifest {mids[k] if k < len(mids) else None!r}, score {sids[k] if k < len(sids) else None!r}")
    prev_end = None
    for m in S["majors"]:
        assert m["end"] > m["start"], f"{m['id']}: end <= start"
        if prev_end is not None:
            assert m["start"] == prev_end, f"{m['id']}: starts at {m['start']}, previous major ends at {prev_end}"
        prev_end = m["end"]
        b = beat(M, m["id"])
        assert ("interlude" in b) == bool((m.get("in") or {}).get("len")), f"{m['id']}: manifest interlude and score `in` must agree"
    assert "scale" in S and "defaults" in S
    counts = {
        "staff": len(beat(M, "staff")["copy"]["staff"]), "loop": len(beat(M, "runs-on-itself")["copy"]["steps"]),
        "checklist": len(beat(M, "pjangler")["copy"]["checklist"]), "pipeline": len(beat(M, "flume")["copy"]["pipeline"]),
        "standup": len(beat(M, "holocene-auto")["copy"]["standup"]), "speakers": len(M["transcript"]["speakers"]),
        "judgments": len(M["transcript"]["judgments"]), "tickets": len(M["transcript"]["tickets"]),
    }
    for m in S["majors"]:
        for mi in m.get("minors", []):
            st = mi.get("steps")
            if isinstance(st, str):
                assert st.startswith("@") and st[1:] in counts, f"{m['id']}.{mi['id']}: unknown count {st}"
                assert counts[st[1:]] > 0, f"{m['id']}.{mi['id']}: {st} resolves to 0"


# ---------------------------------------------------------------- 3. copy budgets (measured, 1280x720 is the binding viewport)

# Stage body is the viewport minus the 81px header: 639 / 779 / 999 px at 1280x720 / 1440x860 / 1920x1080.
# Each row: slot, max chars, max words (None = no limit), the measurement behind it.
BUDGETS = {
    "premise.body": (540, 90, "hero column is 561px of 591 available at 90 words, 1280x720; 120 words overflows (641 of 639)"),
    "premise.title": (14, None, "h1 clamp(46px,6.3vw,112px): 'You go home.' + turn must stay 2 lines (155px at 1280x720)"),
    "premise.titleTurn": (24, None, "a 30-char turn wraps to 3 lines (+77px)"),
    "premise.kicker": (80, None, "11px uppercase, about 90 chars a line in the 685px hero column"),
    "premise.secondary": (60, None, "link beside the CTA; longer wraps and adds 24px"),
    "caption.body": (430, 75, "460px column, 18px/28.8px; 75 words leaves 60px under the header with a 3-line title"),
    "org-chart.body": (380, 65, "quote + source share the column; 75 words leaves 40px, 90 words 11px at 1280x720"),
    "caption.body+aside": (622, None, "gateway is 621 chars (405 + 216) and sits 36px under the header at 1280x720: the accepted tightest caption"),
    "caption.kicker": (64, None, "20px italic display, one line up to 60 chars in the 461px column"),
    "caption.title": (62, None, "h2 clamp(28px,3.4vw,48px): 55 chars is 3 lines, 64+ is 4"),
    "figure.label": (90, None, "directory label column 187px at 1280, 15px/22px; 100 chars is 5 lines and 29px under the header"),
    "figure.n": (3, None, "display numeral column is 100px at 52px type; '2026' overflows into the label"),
    "numbers.stamp": (90, None, "13px/18px under the last row in a 303px column"),
    "department.line": (80, None, "cell is 204px at 1280, 13px/18px; 100 chars is 4 lines and 16px under the header, 130 pushes the YOU row under the nav"),
    "department.dept": (24, None, "11px uppercase eyebrow in a 196px cell"),
    "entry.name": (20, None, "mono 12px uppercase instrument"),
    "quote": (110, None, "blockquote is 444px wide at 1280: more than 110 chars is 3 lines"),
    "quoteSource": (80, None, "eyebrow, 2 lines at 80 chars"),
    "staff.line": (80, None, "nameplate is 240px wide; 90 chars leaves 11px above the viewport bottom at 1280x720, 120 runs off"),
    "detail": (280, None, "popover is cell width + 16px (about 220px); 280 chars is about 9 lines"),
    "nav.label": (14, None, "6 nav labels wrap the header; each label <= 14 chars"),
}
GENERIC_SKIP = {"premise", "org-chart", "hired-well", "numbers", "staff", "ask"}


def _items(M):
    """(slot, where, text) for every budgeted string."""
    out = []
    p = beat(M, "premise")
    out += [("premise.body", "premise.body", p["body"]), ("premise.title", "premise.title", p["title"]),
            ("premise.titleTurn", "premise.titleTurn", p["titleTurn"]), ("premise.kicker", "premise.kicker", p["kicker"]),
            ("premise.secondary", "premise.copy.secondary", p["copy"]["secondary"])]
    for b in M["beats"]:
        i, c = b["id"], b.get("copy", {})
        if i not in GENERIC_SKIP and b["body"]:
            out.append(("caption.body", f"{i}.body", b["body"]))
        if i == "org-chart":
            out.append(("org-chart.body", f"{i}.body", b["body"]))
        if i not in GENERIC_SKIP and b["body"]:
            extra = c.get("aside", "") + (c.get("note", "") if i == "holocene-auto" else "")
            out.append(("caption.body+aside", f"{i}.body+aside", b["body"] + extra))
        if i != "premise":
            if b["kicker"]:
                out.append(("caption.kicker", f"{i}.kicker", b["kicker"]))
            out.append(("caption.title", f"{i}.title", b["title"]))
    n = beat(M, "numbers")["copy"]
    for k, f in enumerate(n["figures"]):
        out += [("figure.label", f"numbers.figures[{k}].label", f["label"]), ("figure.n", f"numbers.figures[{k}].n", f["n"])]
    out.append(("numbers.stamp", "numbers.stamp", n["stamp"]))
    oc = beat(M, "org-chart")["copy"]
    for d in oc["departments"]:
        out += [("department.line", f"{d['name']}.line", d["line"]), ("department.dept", f"{d['name']}.dept", d["dept"]),
                ("entry.name", f"{d['name']}.name", d["name"])]
    out += [("quote", "org-chart.quote", oc["quote"]), ("quoteSource", "org-chart.quoteSource", oc["quoteSource"])]
    for s in beat(M, "staff")["copy"]["staff"]:
        out += [("staff.line", f"staff {s['name']}.line", s["line"]), ("entry.name", f"staff {s['name']}.name", s["name"])]
    for path, text in _details(M):
        out.append(("detail", path, text))
    for k, nv in enumerate(M["site"]["nav"]):
        out.append(("nav.label", f"nav[{k}]", nv["label"]))
    return out


def _details(M):
    for b in M["beats"]:
        for k, v in b.get("copy", {}).items():
            if isinstance(v, list):
                for e in v:
                    if isinstance(e, dict) and "detail" in e:
                        yield f"{b['id']}.{k}[{e.get('name') or e.get('n')}].detail", e["detail"]


def _params():
    try:
        M = manifest()
    except AssertionError:
        return []  # test_every_json_parses carries the real failure
    return [pytest.param(s, w, t, id=w) for s, w, t in _items(M)]


@pytest.mark.parametrize("slot,where,text", _params())
def test_copy_budgets(slot, where, text):
    chars, words, why = BUDGETS[slot]
    assert len(text) <= chars, f"{where}: {len(text)} chars > {chars} (measured: {why})"
    if words:
        assert len(text.split()) <= words, f"{where}: {len(text.split())} words > {words} (measured: {why})"


def test_nav_is_five_or_fewer():
    assert len(manifest()["site"]["nav"]) <= 5, "a 6th nav label wraps the header to 95px"


def test_detail_is_a_real_long_form():
    M = manifest()
    for b in M["beats"]:
        for k, v in b.get("copy", {}).items():
            if isinstance(v, list):
                for e in v:
                    if isinstance(e, dict) and "detail" in e:
                        who = f"{b['id']}.{k}[{e.get('name') or e.get('n')}]"
                        assert isinstance(e["detail"], str) and e["detail"].strip(), f"{who}: detail must be a non-empty string"
                        assert e["detail"] != e.get("line", e.get("label")), f"{who}: detail repeats its line"
            elif isinstance(v, dict) and "detail" in v:
                pytest.fail(f"{b['id']}.{k}: detail only belongs on entries of a list")


# ---------------------------------------------------------------- house rules

def test_no_fleet():
    M = manifest()
    for path, s in walk(M):
        if path.endswith("copy.quote"):
            continue
        assert not re.search(r"\bfleets?\b", s, re.I), f"{path}: the charter rule is 'Never fleet'; say agents, staff or company"


def test_quote_marks_balanced():
    q = beat(manifest(), "org-chart")["copy"]["quote"]
    assert q.startswith("“") and q.endswith("”"), f"quote must open with “ and close with ” (the hand edit dropped the close): {q!r}"
    assert q.count("“") == q.count("”") and q.count("‘") == q.count("’"), f"unbalanced curly quotes: {q!r}"


def test_no_stray_whitespace():
    for path, s in walk(manifest()):
        if path == "_readme" or path.endswith("_readme"):
            continue
        assert s == s.strip(), f"{path}: leading or trailing whitespace"
        assert "  " not in s, f"{path}: double space"


def test_template_tokens():
    for path, s in walk(manifest()):
        if path.endswith("_readme"):
            continue
        assert s.count("{") == s.count("}"), f"{path}: unbalanced braces"
        for tok in re.findall(r"\{[^}]*\}", s):
            assert re.fullmatch(r"\{(p:[^}]+|w:[^}]+|flagships|n|label)\}", tok), f"{path}: unknown token {tok}"


# ---------------------------------------------------------------- optional: a real browser

LAYOUT = os.environ.get("OVERNIGHT_LAYOUT") == "1"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.skipif(not LAYOUT, reason="set OVERNIGHT_LAYOUT=1 (needs playwright + chromium; about 1.5 minutes)")
class TestLayout:
    VIEWPORTS = [(1280, 720), (1440, 860), (1920, 1080)]

    @pytest.fixture(scope="class")
    def server(self):
        port = _free_port()
        proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "-d", str(SITE)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.8)
        yield f"http://127.0.0.1:{port}/"
        proc.terminate()

    @pytest.fixture(scope="class")
    def pw(self):
        sync = pytest.importorskip("playwright.sync_api")
        with sync.sync_playwright() as p:
            try:
                b = p.chromium.launch(args=["--disable-smooth-scrolling"])
            except Exception as e:  # chromium not installed
                pytest.skip(f"chromium will not launch: {e}")
            yield b
            b.close()

    def test_film_fits(self, server, pw):
        M, S = manifest(), score()
        problems = []
        for w, h in self.VIEWPORTS:
            pg = pw.new_page(viewport={"width": w, "height": h})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.goto(server + "?view=film&night=staged")
            pg.wait_for_selector(".hud")
            for m in S["majors"]:
                for f in (0.1, 0.5, 0.9):
                    y = (m["start"] + (m["end"] - m["start"]) * f) * S["scale"] * h / 100
                    pg.evaluate(f"window.scrollTo(0,{y})")
                    pg.wait_for_timeout(700)
                    r = pg.evaluate("""() => {
                      const R = s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return {top: r.top, bottom: r.bottom}; };
                      return { hud: R('.hud'), cap: R('.cap'), fail: !!document.querySelector('.fail'),
                               dir: R('.directory'), you: R('.org__you'), grid: R('.org__grid') };
                    }""")
                    tag = f"{m['id']}@{f} {w}x{h}"
                    if r["fail"]:
                        problems.append(f"{tag}: the failure panel is showing")
                        continue
                    hb = r["hud"]["bottom"]
                    if r["hud"]["bottom"] - r["hud"]["top"] > 82:
                        problems.append(f"{tag}: header wrapped to {r['hud']['bottom'] - r['hud']['top']:.0f}px")
                    if r["cap"] and m["id"] not in ("ask",):
                        gap = 16 if m["id"] == "org-chart" else 24
                        if r["cap"]["top"] < hb + gap or r["cap"]["bottom"] > h - gap:
                            problems.append(f"{tag}: caption {r['cap']['top']:.0f}-{r['cap']['bottom']:.0f} outside {hb + gap:.0f}-{h - gap}")
                    if m["id"] == "numbers" and r["dir"] and (r["dir"]["top"] < hb + 16 or r["dir"]["bottom"] > h - 16):
                        problems.append(f"{tag}: directory {r['dir']['top']:.0f}-{r['dir']['bottom']:.0f}")
                    if m["id"] == "org-chart" and r["you"] and r["grid"] and (r["you"]["top"] < hb + 16 or r["grid"]["bottom"] > h - 16):
                        problems.append(f"{tag}: org chart {r['you']['top']:.0f}-{r['grid']['bottom']:.0f}")
            if errs:
                problems.append(f"{w}x{h}: console errors {errs[:3]}")
            pg.close()
        assert not problems, "\n".join(problems)

    def test_detail_popovers_stay_on_screen(self, server, pw):
        S = score()
        problems = []
        for w, h in self.VIEWPORTS:
            pg = pw.new_page(viewport={"width": w, "height": h})
            pg.goto(server + "?view=film&night=staged")
            pg.wait_for_selector(".hud")
            for bid in ("numbers", "org-chart"):
                m = next(x for x in S["majors"] if x["id"] == bid)
                pg.evaluate(f"window.scrollTo(0,{(m['start'] + (m['end'] - m['start']) * 0.6) * S['scale'] * h / 100})")
                pg.wait_for_timeout(900)
                hb = pg.evaluate("document.querySelector('.hud').getBoundingClientRect().bottom")
                for k in range(pg.locator(".has-detail").count()):
                    el = pg.locator(".has-detail").nth(k)
                    el.focus()
                    r = el.locator(".detail").bounding_box()
                    if not r or r["y"] < hb or r["y"] + r["height"] > h:
                        problems.append(f"{bid}[{k}] {w}x{h}: popover {r}")
            pg.close()
        assert not problems, "\n".join(problems)

    def test_log_view_lists_details(self, server, pw):
        M = manifest()
        pg = pw.new_page(viewport={"width": 390, "height": 844})
        pg.goto(server + "?view=log")
        pg.wait_for_selector(".logview")
        want = len({b["id"] for b in M["beats"] for v in b.get("copy", {}).values()
                    if isinstance(v, list) and any(isinstance(e, dict) and "detail" in e for e in v)})
        assert pg.locator("dl.logview__detail").count() >= want
        pg.close()
