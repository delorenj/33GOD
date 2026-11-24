"""Guard for the 33GOD component tour (overnight/site, served live at 33god.delo.sh).

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

import datetime
import json
import os
import re
import shutil
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


# ---------------------------------------------------------------- 1. every JSON parses

def test_every_json_parses():
    files = sorted(SITE.rglob("*.json"))
    assert {f.name for f in files} >= {"manifest.json", "score.json"}
    for f in files:
        load(f)


def test_no_night_story_left():
    """The page was a night story until 21 Nov 2026. No night file, no night code and no 'stealth' claim may come back."""
    assert not (SITE / "nights").exists(), "site/nights/ is gone: the page tells no night story"
    pat = re.compile(r"stealth|nights/|night=|33god\.night|waybill night", re.I)
    for f in sorted(SITE.rglob("*")):
        if f.is_file() and f.suffix in {".html", ".js", ".css", ".json"} and "vendor" not in f.parts:
            for n, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").split("\n"), 1):
                m = pat.search(line)
                assert not m, f"{f.relative_to(SITE)}:{n}: {m.group(0)!r} (the stage is 'In Development'; there is no night file)"


def test_log_subjects_are_real_bus_subjects():
    """The bus section's tape and every card show `bloodbank.evt.<domain>...`; the list view must spell them the same way."""
    for b in manifest()["beats"]:
        for l in b["log"]:
            assert l["subject"].startswith("bloodbank.evt."), f"{b['id']}: log subject {l['subject']!r} is not the real bus subject"


def test_no_internal_bookkeeping_in_copy():
    """Visitors read hover popovers and the list view: no file paths, CLI names or 'the card still says' notes."""
    pat = re.compile(r"~/|\.yaml|\.json|atlas/|schemas/|all-skills|hindsight bank|still says|\bregistry card\b", re.I)
    def walk(x, path):
        if isinstance(x, str):
            m = pat.search(x)
            assert not m, f"{path}: {m.group(0)!r} is bookkeeping, not copy: {x[:80]!r}"
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")
        elif isinstance(x, dict):
            for k, v in x.items():
                if k not in ("viewSimulationHref", "href", "_readme"):
                    walk(v, f"{path}.{k}")
    walk({k: v for k, v in manifest().items() if k != "transcript"}, "manifest")


# ---------------------------------------------------------------- 2. shape: what the JS dereferences

def test_manifest_shape():
    M = manifest()
    for k in ("site", "acts", "beats", "transcript", "nameplates"):
        assert k in M, f"manifest.json: missing {k}"
    ids = [b["id"] for b in M["beats"]]
    assert len(ids) == len(set(ids)), "duplicate beat ids"
    for b in M["beats"]:
        i = b["id"]
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", i), f"{i}: id is not kebab-case"
        assert isinstance(b.get("where"), str) and b["where"], f"{i}: where (the header names the place)"
        assert b["act"] in M["acts"], f"{i}: act {b['act']!r} is not in acts"
        for k in ("kicker", "title", "body"):
            assert isinstance(b.get(k), str), f"{i}: {k} must be a string"
        assert isinstance(b.get("tags"), list), f"{i}: tags"
        assert isinstance(b.get("log"), list) and b["log"], f"{i}: log needs at least one line (the log view shows only this)"
        for l in b["log"]:
            assert isinstance(l.get("subject"), str) and isinstance(l.get("note"), str), f"{i}: log line needs subject and note"
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
    assert M["site"]["status"] == "In Development", "the stage is In Development"
    for b in M["beats"]:
        if b["setPiece"] == "department.card":
            cc = b["copy"]
            ex = cc["exhibit"]
            assert ex["seats"] and ex["components"], f"{b['id']}: exhibit needs seats and components"
            for m in cc["members"]:
                assert m.get("name") and m.get("role") and m.get("line"), f"{b['id']}: member needs name, role, line: {m}"
            for f in cc["figures"]:
                assert f.get("n") and f.get("label") and f.get("detail"), f"{b['id']}: figure needs n, label, detail: {f}"
            for e in cc["events"]:
                assert e.get("type") and e.get("n"), f"{b['id']}: event needs type and n: {e}"
            assert cc["stamp"] and cc["eventsTitle"]
    # Every component the tour names is in the registry (components/<id>.yaml); "registry" is the registry itself.
    reg = Path(__file__).resolve().parents[1] / "components"
    for b in M["beats"]:
        named = list(b.get("covers") or []) + list((b.get("copy", {}).get("exhibit") or {}).get("components", []))
        for cid in named:
            assert cid == "registry" or (reg / f"{cid}.yaml").exists(), f"{b['id']}: component {cid!r} has no record in components/"
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
    "nav.label": (14, None, "5 nav labels share the header with the chip and the simulation link; each label <= 14 chars"),
    "where": (24, None, "the header's place name sits left of the 'n of N' count"),
    "dept.figure.n": (4, None, "department card numeral column is 62px at 26px type; '1.4M' fits, '12.4M' does not"),
    "dept.figure.label": (64, None, "department card label is 2 lines in the 14px column beside the numeral"),
    "dept.member.line": (80, None, "member row is clamped to 2 lines at 13px/18px"),
    "dept.member.role": (24, None, "eyebrow beside the member name"),
    "dept.event.type": (48, None, "mono 11px subject in the events list, one line"),
    "dept.stamp": (90, None, "13px/18px under the card"),
    "ask.watch.note": (200, None, "the line under the 'Open the 3D Factory' button"),
}
GENERIC_SKIP = {"premise", "org-chart", "numbers", "staff", "ask"}


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
            extra = c.get("aside", "")
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
    for b in M["beats"]:
        out.append(("where", f"{b['id']}.where", b["where"]))
        if b["setPiece"] == "department.card":
            cc = b["copy"]
            for k, f in enumerate(cc["figures"]):
                out += [("dept.figure.n", f"{b['id']}.figures[{k}].n", f["n"]), ("dept.figure.label", f"{b['id']}.figures[{k}].label", f["label"])]
            for m in cc["members"]:
                out += [("dept.member.line", f"{b['id']}.{m['name']}.line", m["line"]), ("dept.member.role", f"{b['id']}.{m['name']}.role", m["role"]),
                        ("entry.name", f"{b['id']}.{m['name']}.name", m["name"])]
            for e in cc["events"]:
                out.append(("dept.event.type", f"{b['id']}.{e['type']}", e["type"]))
            out.append(("dept.stamp", f"{b['id']}.stamp", cc["stamp"]))
    out.append(("ask.watch.note", "ask.watch.note", beat(M, "ask")["copy"]["watch"]["note"]))
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
    assert len(manifest()["site"]["nav"]) <= 5, "a 6th nav label wraps the header"


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
            assert re.fullmatch(r"\{(p:[^}]+|w:[^}]+|n|total|label|date|name|site\.(viewSimulationHref|viewFilm|viewSimulation))\}", tok), f"{path}: unknown token {tok}"


# ---------------------------------------------------------------- the front page (index.html)

FRONT_FILES = ("index.html", "front.js", "front.css", "tour.html")

# Budgets for the front record, measured at 360x780: the binding viewport now, because the phone is a first-class target.
# slot: (max chars, why). 328px is the text column at 360 (16px gutters); the measurements are in the README.
FRONT_BUDGETS = {
    "hero.kicker": (34, "mono 12px uppercase, .14em: about 9.6px a character, one line in 328px"),
    "hero.title": (16, "h1 is 41px at 360; 'A company built' (15) is 270px, 18 chars would wrap"),
    "hero.titleTurn": (16, "same line length as the title"),
    "hero.line": (160, "17px/25px, about 38 chars a line: 4 lines at 138, 5 at 190 pushes the tiles off the first screen"),
    "hero.primary": (22, "the one primary button: its label plus the chevron stays on one line"),
    "hero.tour": (18, "text link beside the button"),
    "hero.statsStamp": (28, "mono 12px, one line under the counts"),
    "stat.n": (3, "hero fact numeral: 24px display, 4 digits crowds its label"),
    "stat.short": (14, "hero fact label, 12.5px in a 2-up grid cell (about 100px)"),
    "stat.label": (36, "closing band cell is 150px wide: 3 lines at 36 chars"),
    "flagship.name": (14, "tile name, 20px display, 130px wide at 360: 'Holocene Auto' fits one line"),
    "flagship.short": (10, "the icon strip's label from 900px up"),
    "flagship.tag": (34, "tile tag, 13.5px, two lines in a 130px tile"),
    "flagship.kicker": (28, "mono 12px, .1em: one line beside the 56px badge"),
    "flagship.headline": (16, "h2 is 33px at 360"),
    "flagship.headlineTurn": (44, "italic turn: 3 lines at 41 chars"),
    "flagship.line": (110, "17px lede, 3 lines at 105 chars"),
    "chip.text": (34, "15px beside a 36px icon: one line in 280px"),
    "next.name": (14, "'Next: ' + name in mono 12px beside the three step markers: 20 chars is 312px of 328"),
    "pj.title": (28, "21px display h3 with the Illustration pill wrapping under it"),
    "pj.note": (34, "mono 11.5px uppercase under the title, one line"),
    "pj.step": (40, "15px in about 220px: two lines at 40 chars"),
    "pj.floor": (4, "the pill by the building"),
    "pj.floorNote": (32, "13px caption under the building"),
    "gw.bar": (22, "mono 13px beside the pill"),
    "gw.ask": (16, "mono 14px bold, right of the 'Asks for' label"),
    "gw.pool": (14, "pool kind, 13px"),
    "gw.state": (10, "mono 11px uppercase, right of the pool row"),
    "gw.chain": (14, "chip in the 'Subscription > Metered > Free' row"),
    "gw.chainNote": (48, "mono 12px, a line of its own: two lines at 48"),
    "gw.route": (40, "mono bold 11.5px: one line at 34, two at 40"),
    "gw.say": (90, "15px in 272px: 3 lines at 90 chars (the three decisions share one box, so the tallest sets it)"),
    "gw.stat.n": (3, "26px display numeral in a 75px cell"),
    "gw.stat.label": (16, "12px, two lines in a 75px cell"),
    "hm.part.name": (10, "mono 12px bold, .08em: 'PHONOGRAPH' is 86px of 110"),
    "hm.part.line": (44, "13px in a 110px tile: 4 lines at 44"),
    "hm.note": (52, "italic 15px: two lines"),
    "hm.call.label": (32, "mono 11.5px uppercase beside the pill: three lines at 32"),
    "hm.call.line": (56, "the phone is 300px: 15px, three lines at 56"),
    "hm.call.tag": (14, "mono 10.5px caps label over each line"),
    "fl.role.name": (16, "mono 12px bold caps"),
    "fl.role.line": (56, "13px beside the 22px icon: three lines at 56"),
    "fl.pipe": (10, "mono 12px caps in a 2-up cell: 'ONBOARDED' is 82px of 140"),
    "ha.screen.product": (16, "13px beside the mark and the signal"),
    "ha.screen.signal": (12, "13px, right of the product"),
    "ha.screen.line": (28, "28px display on the car screen: two lines"),
    "ha.screen.sub": (30, "13px beside the count"),
    "ha.standupTitle": (30, "mono 12px caps beside the pill: two lines"),
    "ha.standup": (44, "15px list row: two lines"),
    "stamp": (130, "12px under a piece, 3 lines in 296px"),
    "org.kicker": (24, "mono 12px caps"),
    "org.title": (32, "h2 is 31px at 360: two lines"),
    "org.line": (100, "17px, 3 lines"),
    "org.name": (14, "mono 11px caps in a 104px tile: 'INFRA-DOCTOR' (12) wraps at the hyphen, 16 would not fit"),
    "org.dept": (24, "12px under the name, two lines in a 104px tile"),
    "org.you": (40, "14px beside the 'You' label"),
    "well.kicker": (28, "mono 12px caps, centred"),
    "well.title": (28, "italic 36px display: one line at 22 chars, two at 28"),
    "well.stamp": (70, "mono 12px, two lines"),
    "ask.kicker": (24, "mono 12px caps"),
    "ask.title": (28, "h2 is 32px: two lines"),
    "ask.line": (60, "18px: two lines"),
    "ask.placeholder": (24, "16px in a 296px input"),
    "ask.button": (22, "full-width button"),
    "ask.note": (70, "mono 12px: two lines"),
    "ask.done": (120, "replaces the form: 15px, 4 lines"),
    "ask.sending": (12, "the button label while the post is in flight"),
    "ask.error": (60, "14px under the form: two lines"),
    "ask.watch": (36, "15px text link, one line in 328px"),
    "shelf.kicker": (24, "mono 12px caps, one line"),
    "shelf.title": (44, "h2 is 28px at 360: two lines at 44"),
    "shelf.line": (110, "17px, 3 lines in 328px"),
    "shelf.stamp": (60, "mono 14px under the cards: two lines in 328px"),
    "shelf.noOffer": (36, "16px bold offer line: one line at 36 in 296px"),
    "shelf.name": (14, "28px display h3 beside the status pill"),
    "shelf.pill": (16, "mono 14px pill beside the name: 'Android · Beta' (14) leaves 120px for the name"),
    "shelf.line.card": (110, "16px in 296px: 4 lines at 110"),
    "shelf.chip": (34, "14px pill: wraps to a second line past 34 chars, never past the card"),
    "shelf.offer": (40, "16px bold, 296px: two lines at 40"),
    "shelf.button": (28, "16px bold in a 296px button with a chevron: one line at 28"),
    "cta.short": (10, "label on the header button from 600px up"),
    "staged": (14, "the pill on every piece"),
}


def _front_items(M):
    F = M["front"]
    out = []

    def add(slot, where, text):
        out.append((slot, where, text))

    h = F["hero"]
    for k in ("kicker", "title", "titleTurn", "line", "primary", "statsStamp"):
        add(f"hero.{k}", f"front.hero.{k}", h[k])
    add("hero.tour", "front.hero.tour (the resolved label)", M["site"]["viewFilm"] if h["tour"] == "{site.viewFilm}" else h["tour"])
    for i, x in enumerate(F["stats"]):
        add("stat.n", f"front.stats[{i}].n", x["n"])
        add("stat.short", f"front.stats[{i}].short", x["short"])
        add("stat.label", f"front.stats[{i}].label", x["label"])
    add("cta.short", "front.ctaShort", F["ctaShort"])
    add("staged", "front.stagedLabel", F["stagedLabel"])
    for f in F["flagships"]:
        i = f["id"]
        for k, slot in (("name", "flagship.name"), ("short", "flagship.short"), ("tag", "flagship.tag"), ("kicker", "flagship.kicker"),
                        ("headline", "flagship.headline"), ("headlineTurn", "flagship.headlineTurn"), ("line", "flagship.line")):
            add(slot, f"front.{i}.{k}", f[k])
        for j, c in enumerate(f["chips"]):
            add("chip.text", f"front.{i}.chips[{j}]", c["text"])
        add("next.name", f"front.{i}.next.label", f["next"]["label"])
        p = f["piece"]
        if "stamp" in p:
            add("stamp", f"front.{i}.piece.stamp", p["stamp"])
        if i == "pjangler":
            add("pj.title", f"{i}.title", p["title"]); add("pj.note", f"{i}.note", p["note"])
            add("pj.floor", f"{i}.floor", p["floor"]); add("pj.floorNote", f"{i}.floorNote", p["floorNote"])
            for j, st in enumerate(p["steps"]):
                add("pj.step", f"{i}.steps[{j}]", st["text"])
        elif i == "gateway":
            add("gw.bar", f"{i}.bar", p["bar"]); add("gw.ask", f"{i}.ask.value", p["ask"]["value"])
            for j, k in enumerate(p["pools"]):
                add("gw.pool", f"{i}.pools[{j}]", k)
            for k, v in p["states"].items():
                add("gw.state", f"{i}.states.{k}", v)
            for j, c in enumerate(p["chain"]):
                add("gw.chain", f"{i}.chain[{j}]", c)
            add("gw.chainNote", f"{i}.chainNote", p["chainNote"])
            for j, d in enumerate(p["say"]):
                add("gw.route", f"{i}.say[{j}].route", d["route"]); add("gw.say", f"{i}.say[{j}].line", d["line"])
            for j, d in enumerate(p["stats"]):
                add("gw.stat.n", f"{i}.stats[{j}].n", d["n"]); add("gw.stat.label", f"{i}.stats[{j}].label", d["label"])
        elif i == "heyma":
            for j, d in enumerate(p["parts"]):
                add("hm.part.name", f"{i}.parts[{j}].name", d["name"]); add("hm.part.line", f"{i}.parts[{j}].line", d["line"])
            add("hm.note", f"{i}.note", p["note"])
            c = p["call"]
            add("hm.call.label", f"{i}.call.label", c["label"])
            for k in ("heard", "translated", "reply"):
                add("hm.call.line", f"{i}.call.{k}", c[k])
            for k in ("heardLabel", "translatedLabel", "replyLabel"):
                add("hm.call.tag", f"{i}.call.{k}", c[k])
        elif i == "flume":
            for j, r in enumerate(p["roles"] + [p["hire"]]):
                add("fl.role.name", f"{i}.roles[{j}].name", r["name"]); add("fl.role.line", f"{i}.roles[{j}].line", r["line"])
            for j, d in enumerate(p["pipeline"]):
                add("fl.pipe", f"{i}.pipeline[{j}]", d["text"])
        elif i == "holocene-auto":
            sc = p["screen"]
            add("ha.screen.product", f"{i}.screen.product", sc["product"]); add("ha.screen.signal", f"{i}.screen.signal", sc["signal"])
            add("ha.screen.line", f"{i}.screen.line", sc["line"]); add("ha.screen.sub", f"{i}.screen.sub", sc["sub"])
            add("ha.standupTitle", f"{i}.standupTitle", p["standupTitle"])
            for j, d in enumerate(p["standup"]):
                add("ha.standup", f"{i}.standup[{j}]", d)
    H = F["shelfHead"]
    for k in ("kicker", "title", "line", "stamp", "noOffer"):
        add(f"shelf.{k}", f"front.shelfHead.{k}", H[k])
    add("next.name", "front.shelfHead.next.label", H["next"]["label"])
    for x in F["shelf"]:
        w = f"front.shelf[{x['id']}]"
        add("shelf.name", f"{w}.name", x["name"]); add("shelf.pill", f"{w}.pill", x["pill"])
        add("shelf.line.card", f"{w}.line", x["line"]); add("shelf.button", f"{w}.button", x["button"])
        for j, c in enumerate(x["chips"]):
            add("shelf.chip", f"{w}.chips[{j}]", c)
        if x["offer"]:
            add("shelf.offer", f"{w}.offer", x["offer"])
    o = F["org"]
    for k in ("kicker", "title", "line"):
        add(f"org.{k}", f"front.org.{k}", o[k])
    oc = beat(M, "org-chart")["copy"]
    for d in oc["departments"]:
        add("org.name", f"org band {d['name']}", d["name"]); add("org.dept", f"org band {d['name']}.dept", d["dept"])
    add("org.you", "org band you", oc["you"]["line"])
    for k in ("kicker", "title", "stamp"):
        add(f"well.{k}", f"front.well.{k}", F["well"][k])
    for k in ("kicker", "title", "line", "placeholder", "button", "note", "done", "watch", "sending", "error"):
        add(f"ask.{k}", f"front.ask.{k}", F["ask"][k])
    return out


def _front_params():
    try:
        M = manifest()
        return [pytest.param(sl, w, t, id=w) for sl, w, t in _front_items(M)]
    except (AssertionError, KeyError):
        return []  # test_front_record_has_every_slot carries the real failure


@pytest.mark.parametrize("slot,where,text", _front_params())
def test_front_copy_budgets(slot, where, text):
    chars, why = FRONT_BUDGETS[slot]
    assert len(text) <= chars, f"{where}: {len(text)} chars > {chars} (measured at 360x780: {why})"


def test_front_record_has_every_slot():
    F = manifest().get("front")
    assert isinstance(F, dict), "manifest.json: missing the top-level `front` record (the front page's words)"
    for k in ("title", "aria", "stagedLabel", "ctaShort", "next", "hero", "stats", "flagships", "shelfHead", "shelf", "org", "well", "ask", "footer"):
        assert k in F, f"front.{k} is missing"
    for k in ("flagships", "progress", "skip", "home", "counts", "org", "more"):
        assert F["aria"].get(k), f"front.aria.{k}"
    for k in ("kicker", "title", "titleTurn", "line", "primary", "tour", "tourNote", "statsStamp"):
        assert F["hero"].get(k), f"front.hero.{k}"
    assert "{name}" in F["next"]
    assert 4 <= len(F["stats"]) <= 5 and any(x.get("hero") for x in F["stats"]), "the hero row shows the registry counts"
    for x in F["stats"]:
        for k in ("icon", "n", "short", "label"):
            assert x.get(k), f"front.stats: {x}: missing {k}"
    assert [f["id"] for f in F["flagships"]] == ["pjangler", "gateway", "heyma", "flume", "holocene-auto"], "five flagships, in this order"
    ids = [f["id"] for f in F["flagships"]]
    for n, f in enumerate(F["flagships"]):
        for k in ("num", "name", "short", "icon", "tag", "kicker", "headline", "headlineTurn", "line", "chips", "next", "piece"):
            assert f.get(k), f"front.{f['id']}.{k}"
        assert f["num"] == f"F-0{n + 1}"
        assert len(f["chips"]) == 3 and all(c.get("icon") and c.get("text") for c in f["chips"]), f"{f['id']}: three chips, each with icon and text"
        assert f["next"].get("label") and f["next"].get("to")
    pj, gw, hm, fl, ha = (f["piece"] for f in F["flagships"])
    assert len(pj["steps"]) == 6 and pj["title"] and pj["note"] and pj["floor"] and pj["floorNote"] and pj["aria"]
    assert len(gw["pools"]) == 5 and len(gw["say"]) == 3 and len(gw["stats"]) == 4 and gw["states"] and gw["chain"] and gw["stamp"] and gw["aria"]
    for k in ("drawing", "spent", "waiting", "backstop", "scouting", "grown"):
        assert gw["states"].get(k), f"gateway.states.{k}"
    assert len(hm["parts"]) == 4 and hm["note"] and hm["stamp"]
    for k in ("label", "heardLabel", "heard", "translatedLabel", "translated", "replyLabel", "reply"):
        assert hm["call"].get(k), f"heyma.call.{k}"
    assert len(fl["roles"]) == 3 and fl["hire"] and len(fl["pipeline"]) == 4 and fl["stamp"]
    assert ha["screen"] and len(ha["standup"]) == 4 and ha["standupTitle"] and ha["stamp"] and ha["aria"]
    oc = beat(manifest(), "org-chart")["copy"]
    for d in oc["departments"]:
        assert F["org"]["icons"].get(d["name"]), f"front.org.icons has no icon for {d['name']} (the org band shows every department)"
    for k in ("kicker", "title", "stamp"):
        assert F["well"].get(k)
    for k in ("kicker", "title", "line", "label", "placeholder", "button", "note", "done", "watch", "watchHref", "sending", "error"):
        assert F["ask"].get(k), f"front.ask.{k}"
    # the front form is the tour's sign-up (forms.js -> form-intake), so what it promises is what the tour promises
    tour_ask = beat(manifest(), "ask")["copy"]
    for k, tk in (("note", "previewNote"), ("done", "done"), ("sending", "sending"), ("error", "error"), ("label", "label"), ("placeholder", "placeholder"), ("button", "button")):
        assert F["ask"][k] == tour_ask[tk], f"front.ask.{k} drifted from the tour's ask.{tk}"
    assert F["footer"].get("tour") and F["footer"].get("simulation")
    del ids


def test_front_house_rules():
    """The front page keeps the tour's honesty rules."""
    M = manifest()
    F = M["front"]
    text = {p: s for p, s in walk(F) if not p.endswith("_readme")}
    assert F["hero"]["kicker"].endswith("In Development"), "the stage is In Development"
    for p, s in text.items():
        assert not re.search(r"stealth|\bfleets?\b", s, re.I), f"front.{p}: no 'stealth', no 'fleet'"
    # every figure on the page is dated 21 Nov 2026 (the counted-on date), and staged pieces say so
    assert M["site"]["countedOn"] == "21 Nov 2026"
    assert "21 Nov 2026" in F["hero"]["statsStamp"] and "21 Nov 2026" in F["well"]["kicker"] and "21 Nov 2026" in F["well"]["stamp"]
    assert "21 Nov 2026" in F["flagships"][1]["piece"]["stamp"], "the gateway's counts are dated"
    assert "illustration" in F["flagships"][1]["piece"]["stamp"].lower()
    for f in F["flagships"][2:]:
        assert "illustration" in f["piece"]["stamp"].lower(), f"{f['id']}: the staged piece says so"
    assert F["stagedLabel"] == M["site"]["stagedLabel"]
    assert "forms.js" in (SITE / "index.html").read_text(encoding="utf-8"), "the front sign-up posts through forms.js"
    assert "G33Forms.submit('briefing'" in (SITE / "front.js").read_text(encoding="utf-8")


def test_front_has_no_night_clock():
    """No night-shaped copy on the front page (the tour's rule): no clock times, no 'tonight', no moon."""
    F = manifest()["front"]
    for p, s in walk(F):
        if p.endswith("_readme"):
            continue
        assert not re.search(r"\btonight\b|\bmoon\b|\bnightly\b|\bovernight\b|\bevery night\b|\b\d{1,2}:\d{2}\b", s, re.I), f"front.{p}: {s!r} is night-shaped"


def test_front_files_and_links():
    for f in FRONT_FILES:
        assert (SITE / f).exists(), f"site/{f} is missing"
    idx = (SITE / "index.html").read_text(encoding="utf-8")
    assert 'name="robots" content="noindex, nofollow"' in idx
    for src in re.findall(r'<script[^>]+src="([^"]+)"', idx):
        assert not src.startswith("http"), f"index.html loads an external script: {src}"
    assert 'href="front.css"' in idx and 'src="front.js"' in idx
    tour = (SITE / "tour.html").read_text(encoding="utf-8")
    for src in ("score.js", "dolly.js", "overnight.js", "ds/bundle.js"):
        assert f'src="{src}"' in tour, f"tour.html lost {src}"
    # a front anchor must never be a tour beat id, or an old tour link could not be told from it
    M = manifest()
    beat_ids = {b["id"] for b in M["beats"]}
    anchors = {"top", "flagships", "shelf", "org-band", "counts", "briefing"} | {f"f-{f['id']}" for f in M["front"]["flagships"]}
    assert not (anchors & beat_ids), f"front anchors collide with tour beats: {anchors & beat_ids}"
    for f in M["front"]["flagships"]:
        assert f["next"]["to"] in anchors, f"{f['id']}: next points at {f['next']['to']!r}, not a front anchor"
    assert M["front"]["shelfHead"]["next"]["to"] in anchors
    css = (SITE / "front.css").read_text(encoding="utf-8")
    # raw colours live only in the token blocks at the top of front.css
    body = css.split("/* ---------- base ---------- */", 1)[1]
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", body), "front.css: a raw colour outside the token blocks"
    js = (SITE / "front.js").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9a-fA-F]{6}\b", js), "front.js: a raw colour (use tokens)"


# ---------------------------------------------------------------- the shelf (front.shelf[]): products that ship on their own in the store

STORE = "https://store.automaticai.io"
SHELF_STATUSES = ("on-sale", "preview")
SHELF_OPT_OUT = {}  # catalog id -> why the front page leaves it off; empty while every store product is on the shelf
STORE_REPO = Path(os.environ.get("STORE_REPO") or Path.home() / "code" / "automaticai-store")


def _shelf():
    F = manifest()["front"]
    return F["shelfHead"], F["shelf"]


def test_front_shelf_schema():
    """One generic card per entry: the same schema, the same budgets, and nothing but a store page to link to."""
    H, shelf = _shelf()
    for k in ("after", "kicker", "title", "line", "asOf", "noOffer", "newTab", "stamp", "next"):
        assert H.get(k), f"front.shelfHead.{k}"
    assert "{date}" in H["asOf"], "the offer line is dated per card"
    assert shelf, "front.shelf is a list of at least one product"
    ids = [x["id"] for x in shelf]
    assert len(set(ids)) == len(ids), "one card per product"
    for x in shelf:
        w = f"front.shelf[{x['id']}]"
        # a date belongs to an offer: a card with nothing for sale has no "as of" line (it would read like a sale listing)
        want = {"id", "name", "status", "pill", "line", "chips", "offer", "href", "button"} | ({"asOf"} if x["offer"] else set())
        assert set(x) == want, f"{w}: unexpected or missing keys {sorted(x)}"
        assert x["status"] in SHELF_STATUSES, f"{w}.status must be one of {SHELF_STATUSES}"
        assert 1 <= len(x["chips"]) <= 3, f"{w}: up to three chips"
        assert all(c and isinstance(c, str) for c in x["chips"])
        # https only, on the store's own host: never a payment link, an APK, a bucket or another site
        assert x["href"].startswith(STORE + "/"), f"{w}.href must be a page on {STORE}"
        assert re.fullmatch(re.escape(STORE) + r"/[a-z0-9-]+/", x["href"]), f"{w}.href must be the product's own page, one path segment, no query: {x['href']}"
        assert not re.search(r"stripe|\.apk|s3\.delo\.sh", x["href"], re.I), f"{w}.href must not be a payment or download link"
        assert x["href"] == f"{STORE}/{x['id']}/", f"{w}: the page is /{x['id']}/"
        if x["status"] == "on-sale":
            assert x["offer"] and "$" in x["offer"], f"{w}: an on-sale product shows its price"
        else:
            assert x["offer"] is None, f"{w}: a product that is not on sale shows no price"
        assert not re.search(r"\bbuy\b|\bpurchase\b|\border\b", x["button"], re.I), f"{w}.button: the button opens a page, it does not buy"
        if x["offer"]:
            assert re.fullmatch(r"\d{1,2} [A-Z][a-z]{2} 20\d\d", x["asOf"]), f"{w}.asOf is a date like '23 Nov 2026'"
    # buyable first, not-on-sale last
    flags = [x["status"] == "on-sale" for x in shelf]
    assert flags == sorted(flags, reverse=True), "on-sale products come first, the rest last"
    # the shelf sits after the flagship it names, and that flagship's Next link lands on it, so the chain is not skipped
    F = manifest()["front"]
    after = [f for f in F["flagships"] if f["id"] == H["after"]]
    assert after, f"shelfHead.after names a flagship: {H['after']!r}"
    assert after[0]["next"]["to"] == "shelf", "the flagship before the shelf links Next to it"
    nxt = [f for f in F["flagships"] if f"f-{f['id']}" == H["next"]["to"]]
    assert nxt and F["flagships"].index(nxt[0]) == F["flagships"].index(after[0]) + 1, "the shelf's Next goes to the flagship after it"
    assert H["next"]["label"] == nxt[0]["name"]


def test_front_shelf_house_rules():
    H, shelf = _shelf()
    seen = 0
    for p, s in walk(manifest()["front"]):
        if p.startswith("shelf"):
            seen += 1
            assert not re.search(r"clone anyone|consent|verif|battery|emergency|google play|iphone|\bios\b|voxy\b|stripe|\.apk", s, re.I), f"front.{p}: a claim the store page does not make: {s!r}"
    assert seen > 10, "the claims check reached the shelf's strings"
    hm = [x for x in shelf if x["id"] == "heyma"]
    if hm:
        assert hm[0]["status"] == "preview", "HeyMa is a preview until the store says otherwise"


def _local_catalog():
    path = STORE_REPO / "site" / "products.json"
    return load(path) if path.exists() else None


@pytest.mark.skipif(_local_catalog() is None, reason=f"no store checkout at {STORE_REPO} (set STORE_REPO)")
def test_front_shelf_agrees_with_the_store_catalog_on_disk():
    """The same drift guard the network check runs, against the store repo's products.json, so it runs everywhere the repo is cloned."""
    _, shelf = _shelf()
    _compare_with_catalog(shelf, _local_catalog())


def _compare_with_catalog(shelf, catalog):
    by_id = {p["id"]: p for p in catalog["products"]}
    for x in shelf:
        p = by_id.get(x["id"])
        assert p, f"shelf[{x['id']}]: the store catalog has no such product"
        assert x["href"] == p["url"], f"shelf[{x['id']}].href {x['href']} != catalog url {p['url']}"
        assert x["name"] == p["name"], f"shelf[{x['id']}].name != catalog name"
        assert x["status"] == p["status"], f"shelf[{x['id']}].status {x['status']} != catalog status {p['status']}"
        assert x["pill"] == p["statusLabel"], f"shelf[{x['id']}].pill {x['pill']!r} != catalog statusLabel {p['statusLabel']!r}"
        assert x["offer"] == (p["offer"]["text"] if p["offer"] else None), f"shelf[{x['id']}].offer {x['offer']!r} != catalog offer {p['offer']!r}"
        assert x["line"] == p["tagline"], f"shelf[{x['id']}].line drifted from the catalog tagline"
        if x["offer"]:
            when = datetime.date.fromisoformat(catalog["updated"])
            assert x["asOf"] == f"{when.day} {when.strftime('%b %Y')}", f"shelf[{x['id']}].asOf {x['asOf']!r} != the catalog's updated date {catalog['updated']}: re-read the offer, then update both"
        # a claim the store page makes only for normal messages must not lose that word on the way to a card
        for text in [*x["chips"], x["line"], p["card"], p["tagline"]]:
            if re.search(r"\bcalls?\b", text, re.I):
                assert re.search(r"\bnormal\b", text, re.I), f"shelf[{x['id']}]: {text!r} says calls hold messages without 'normal' (the alarm channel plays over calls)"
    # a product the store lists must be on the shelf, unless it is named here on purpose
    missing = [i for i in by_id if i not in {x["id"] for x in shelf} and i not in SHELF_OPT_OUT]
    assert not missing, f"the store lists {missing} but front.shelf has no entry for it (add one, or list it in SHELF_OPT_OUT with a reason)"


LIVE_LINKS = os.environ.get("OVERNIGHT_LIVE_LINKS") == "1"


def _fetch(url):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "33god-overnight-shelf-check"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read().decode("utf-8", "replace")


@pytest.mark.skipif(not LIVE_LINKS, reason="set OVERNIGHT_LIVE_LINKS=1 (fetches https://store.automaticai.io)")
def test_front_shelf_matches_the_live_store():
    """Never trust a status code: /heyma/ once answered 200 with the store's home page. Each shelf link's own <title> must name the
    product, and the live catalog must agree on status, pill and price."""
    _, shelf = _shelf()
    status, body = _fetch(f"{STORE}/products.json")
    assert status == 200
    catalog = json.loads(body)
    _compare_with_catalog(shelf, catalog)
    by_id = {p["id"]: p for p in catalog["products"]}
    for x in shelf:
        status, html = _fetch(x["href"])
        assert status == 200, f"{x['href']}: HTTP {status}"
        m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
        title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        assert x["name"] in title, f"{x['href']}: <title> is {title!r}, which does not name {x['name']} (a soft 404 shows the store home page)"
        assert title == by_id[x["id"]]["title"], f"{x['href']}: <title> {title!r} != catalog title {by_id[x['id']]['title']!r}"
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
        assert by_id[x["id"]]["platform"] in text, f"{x['href']}: the page never says the catalog platform {by_id[x['id']]['platform']!r}"
        if x["offer"]:
            price = re.search(r"\$\d+(?:\.\d\d)?", x["offer"]).group(0)
            assert price in html, f"{x['href']}: the page does not show the price {price} the shelf advertises"
        else:
            assert not re.search(r"\$\d", html), f"{x['href']}: the shelf says nothing is for sale but the page shows a price"


# ---------------------------------------------------------------- the pace: one press of Down is one section

PACE_KEYS = {"back", "launch", "settle", "smooth", "rush", "reach", "min", "dwell"}


def _share(v):
    return float(v[:-1]) / 100 if isinstance(v, str) and v.endswith("%") else v


def test_score_pace_shape():
    S = score()
    assert set(S.get("pace", {})) <= PACE_KEYS, f"unknown pace key(s) {set(S['pace']) - PACE_KEYS}"
    for k, v in S.get("pace", {}).items():
        assert isinstance(v, (int, float)) and v >= 0, f"pace.{k} must be a number of at least 0"
    assert S["pace"]["rush"] >= 1 and 0 <= S["pace"]["dwell"] <= 1
    d = S["defaults"]
    for k, fields in (("body", {"ms", "perStep", "play"}), ("out", {"len", "curve", "ms", "timing"}), ("in", {"ms", "hold"})):
        assert set(d.get(k, {})) <= fields, f"defaults.{k}: unknown field(s) {set(d.get(k, {})) - fields}"
    for m in S["majors"]:
        b = m.get("body")
        assert b and isinstance(b.get("ms"), (int, float)) and b["ms"] > 0, f"{m['id']}: every section needs body.ms (its pace is design)"
        play = b.get("play")
        assert play and len(play) == 2, f"{m['id']}: body.play must be [from, to]"
        a, z = _share(play[0]), _share(play[1])
        assert 0 <= a < z <= 1, f"{m['id']}: body.play {play} must run forward inside the body"
        assert set(b) <= {"ms", "play", "perStep"}, f"{m['id']}.body: unknown field(s)"
        for key in ("out", "in"):
            for f, v in (m.get(key) or {}).items():
                if f in ("ms", "hold", "settleMs"):
                    assert isinstance(v, (int, float)) and v >= 0, f"{m['id']}.{key}.{f} must be milliseconds"
        for mi in m.get("minors", []):
            assert "glide" not in mi, f"{m['id']}/{mi['id']}: `glide: false` is now `pace: false`"
            if "dwell" in mi:
                assert 0 <= mi["dwell"] <= 1, f"{m['id']}/{mi['id']}: dwell must be between 0 and 1"
            assert mi.get("pace", True) in (True, False)


def test_site_simulation_link():
    s = manifest()["site"]
    assert s["viewSimulationHref"].startswith("https://"), "the 3D simulation is a real link"
    assert 0 < len(s["viewSimulation"]) <= 24, "a longer label wraps the header"
    for k in ("next", "gauge", "gaugeText"):
        assert isinstance(s.get(k), str) and s[k].strip(), f"site.{k} must be a non-empty string"
    assert len(s["next"]) <= 40 and len(s["gauge"]) <= 60
    assert "{n}" in s["gaugeText"] and "{total}" in s["gaugeText"]
    assert len(s["scrollHint"]) <= 80, "the hero hint is one line under the buttons"


NODE = shutil.which("node")


@pytest.mark.skipif(not NODE, reason="node is not installed")
def test_score_stations_node():
    r = subprocess.run([NODE, str(Path(__file__).with_name("overnight_score_check.js"))], capture_output=True, text=True, env={**os.environ, "OVERNIGHT_SITE": str(SITE)})
    assert r.returncode == 0, r.stderr or r.stdout


# ---------------------------------------------------------------- optional: a real browser

LAYOUT = os.environ.get("OVERNIGHT_LAYOUT") == "1"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Browser:
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


@pytest.mark.skipif(not LAYOUT, reason="set OVERNIGHT_LAYOUT=1 (needs playwright + chromium; about 2.5 minutes)")
class TestLayout(_Browser):

    def test_film_fits(self, server, pw):
        M, S = manifest(), score()
        problems = []
        for w, h in self.VIEWPORTS:
            pg = pw.new_page(viewport={"width": w, "height": h})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.goto(server + "tour.html?view=film")
            pg.wait_for_selector(".hud")
            for m in S["majors"]:
                for f in (0.1, 0.5, 0.9):
                    y = (m["start"] + (m["end"] - m["start"]) * f) * S["scale"] * h / 100
                    pg.evaluate(f"window.scrollTo(0,{y})")
                    pg.wait_for_timeout(700)
                    r = pg.evaluate("""() => {
                      const R = s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return {top: r.top, bottom: r.bottom, left: r.left, right: r.right}; };
                      return { hud: R('.hud'), cap: R('.cap'), next: R('.next'), fail: !!document.querySelector('.fail'),
                               dir: R('.directory'), you: R('.org__you'), grid: R('.org__grid'), dept: R('.scard--dept') };
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
                    c, n = r["cap"], r["next"]
                    if c and n and not (n["right"] <= c["left"] or n["left"] >= c["right"] or n["bottom"] <= c["top"] or n["top"] >= c["bottom"]):
                        problems.append(f"{tag}: the next-section caret {n} covers the caption {c}")
                    if m["id"] == "numbers" and r["dir"] and (r["dir"]["top"] < hb + 16 or r["dir"]["bottom"] > h - 16):
                        problems.append(f"{tag}: directory {r['dir']['top']:.0f}-{r['dir']['bottom']:.0f}")
                    if m["id"] in ("clock-records", "agents-desk") and f < 0.9 and (not r["dept"] or r["dept"]["top"] < hb + 8 or r["dept"]["bottom"] > h - 16):
                        problems.append(f"{tag}: department card {r['dept']}")
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
            pg.goto(server + "tour.html?view=film")
            pg.wait_for_selector(".hud")
            for bid in ("numbers", "org-chart", "clock-records", "agents-desk"):
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
        pg.goto(server + "tour.html?view=log")
        pg.wait_for_selector(".logview")
        want = len({b["id"] for b in M["beats"] for v in b.get("copy", {}).values()
                    if isinstance(v, list) and any(isinstance(e, dict) and "detail" in e for e in v)})
        assert pg.locator("dl.logview__detail").count() >= want
        pg.close()


# ---------------------------------------------------------------- the front page in a real browser

FRONT_VIEWPORTS = [(360, 780), (412, 915), (820, 1180), (1024, 768), (1280, 720), (1440, 900), (1920, 1080)]


@pytest.mark.skipif(not LAYOUT, reason="set OVERNIGHT_LAYOUT=1 (needs playwright + chromium)")
class TestFront(_Browser):
    """Phone first: nothing under the fixed header, no sideways scroll, a pinned exhibit only if its whole stage fits."""

    def _open(self, pw, server, w, h, **kw):
        pg = pw.new_page(viewport={"width": w, "height": h}, **kw)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto(server)
        pg.wait_for_selector("html.ready")
        pg.errs = errs
        return pg

    def test_no_sideways_scroll_nothing_under_header(self, server, pw):
        problems = []
        for w, h in FRONT_VIEWPORTS:
            pg = self._open(pw, server, w, h)
            total = pg.evaluate("document.documentElement.scrollHeight")
            y = 0
            while y < total:
                pg.evaluate(f"window.scrollTo(0,{y})")
                pg.wait_for_timeout(120)
                r = pg.evaluate("""() => {
                  const hb = document.querySelector('.hdr').getBoundingClientRect().bottom;
                  const bad = [];
                  for (const e of document.querySelectorAll('h1,h2,h3,.btn,.cta,.chip,.fig,.fact')) {
                    if (getComputedStyle(e).display === 'none') continue;  // hidden on purpose (the phone drops counts the hero already has)
                    const b = e.getBoundingClientRect();
                    if (!b.width || b.right > innerWidth + 0.5 || b.left < -0.5) bad.push(e.className + ' x ' + Math.round(b.left) + '-' + Math.round(b.right));
                  }
                  return { sx: document.documentElement.scrollWidth - innerWidth, hb, bad };
                }""")
                if r["sx"] > 0:
                    problems.append(f"{w}x{h}@{y}: scrolls sideways by {r['sx']}px")
                if r["bad"]:
                    problems.append(f"{w}x{h}@{y}: off the sides {r['bad'][:3]}")
                y += int(h * 0.8)
            if pg.errs:
                problems.append(f"{w}x{h}: console errors {pg.errs[:3]}")
            pg.close()
        assert not problems, "\n".join(problems)

    def test_header_fits_on_a_phone(self, server, pw):
        for w, h in ((360, 780), (412, 915)):
            pg = self._open(pw, server, w, h)
            r = pg.evaluate("""() => { const q = s => document.querySelector(s).getBoundingClientRect();
              return { hdr: q('.hdr'), cta: q('.cta'), brand: q('.brand'), nav: q('.hdr nav') }; }""")
            assert r["hdr"]["height"] <= 60, f"{w}: header is {r['hdr']['height']}px tall"
            assert r["cta"]["right"] <= w and r["nav"]["right"] <= r["cta"]["left"] + 1, f"{w}: the CTA covers the nav {r}"
            assert r["cta"]["width"] <= 48, f"{w}: the phone CTA is compact, not full size ({r['cta']['width']}px)"
            small = pg.evaluate("""() => [...document.querySelectorAll('.hdr .nav a, .hdr .cta, .hdr .brand')].map(e => { const b = e.getBoundingClientRect(); return [e.className || e.id || e.tagName, Math.round(b.width), Math.round(b.height)]; }).filter(x => x[1] < 44 || x[2] < 44)""")
            assert not small, f"{w}: header tap targets under 44px: {small}"
            pg.close()

    def test_one_primary_button_on_the_first_phone_screen(self, server, pw):
        pg = self._open(pw, server, 360, 780)
        n = pg.evaluate("""() => [...document.querySelectorAll('.btn')].filter(b => { const r = b.getBoundingClientRect(); return r.top < innerHeight && r.bottom > 0 && getComputedStyle(b).display !== 'none'; }).length""")
        assert n == 1, f"{n} buttons on the first screen"
        pg.close()

    def test_hero_index_is_two_columns_on_a_phone(self, server, pw):
        pg = self._open(pw, server, 360, 780)
        xs = pg.evaluate("""() => [...document.querySelectorAll('.hero__idx .tiles > *')].map(e => Math.round(e.getBoundingClientRect().left))""")
        assert len(xs) == 5 and len(set(xs)) <= 2, f"flagship tiles are not a 2-column grid: lefts {xs}"
        pg.close()

    def test_pins_only_when_the_whole_stage_fits(self, server, pw):
        problems = []
        for w, h in FRONT_VIEWPORTS:
            pg = self._open(pw, server, w, h)
            pg.wait_for_timeout(400)
            info = pg.evaluate("""() => { const hdr = document.querySelector('.hdr').getBoundingClientRect().height;
              return [...document.querySelectorAll('.ex')].map(ex => ({ id: ex.id, pinned: ex.classList.contains('is-pinned'),
                need: ex.querySelector('.ex__stage').firstElementChild.getBoundingClientRect().height, avail: innerHeight - hdr })); }""")
            for e in info:
                if e["pinned"] and e["need"] > e["avail"] + 1:
                    problems.append(f"{w}x{h}: {e['id']} is pinned but needs {e['need']:.0f}px of {e['avail']:.0f}")
            if w <= 412 and any(e["pinned"] for e in info):
                problems.append(f"{w}x{h}: an exhibit pinned on a phone")
            pg.close()
        assert not problems, "\n".join(problems)

    def test_beats_advance_with_scroll(self, server, pw):
        for w, h in ((360, 780), (1280, 720)):
            pg = self._open(pw, server, w, h)
            seen = set()
            ex = pg.locator("#f-gateway")
            top = pg.evaluate("document.querySelector('#f-gateway').getBoundingClientRect().top + scrollY")
            hh = pg.evaluate("document.querySelector('#f-gateway').offsetHeight")
            for f in (0.05, 0.35, 0.7, 0.95):
                pg.evaluate(f"window.scrollTo(0,{top + hh * f - h * 0.4})")
                pg.wait_for_timeout(250)
                seen.add(ex.get_attribute("data-step"))
            assert len(seen) >= 2, f"{w}x{h}: gateway never changes step ({seen})"
            pg.close()

    def test_old_tour_links_go_to_the_tour(self, server, pw):
        M = manifest()
        for q, want in (("?view=film", "tour.html?view=film"), ("?pace=0.2", "tour.html?pace=0.2"), ("#flume", "tour.html#flume"), ("#ask", "tour.html#ask")):
            pg = pw.new_page(viewport={"width": 390, "height": 844})
            pg.goto(server + q)
            pg.wait_for_url(re.compile(re.escape(want) + "$"), timeout=8000)
            pg.close()
        pg = pw.new_page(viewport={"width": 390, "height": 844})
        pg.goto(server + "#f-gateway")
        pg.wait_for_selector("html.ready")
        assert pg.url.endswith("/#f-gateway") and "tour.html" not in pg.url
        pg.close()
        assert M["beats"], "tour beats exist"

    def test_reduced_motion_shows_final_states_and_never_pins(self, server, pw):
        pg = self._open(pw, server, 1440, 900, reduced_motion="reduce")
        assert pg.evaluate("document.documentElement.classList.contains('flat')")
        assert pg.evaluate("document.querySelectorAll('.ex.is-pinned').length") == 0
        steps = pg.evaluate("[...document.querySelectorAll('.ex')].map(e => [e.dataset.step, e.dataset.steps])")
        assert all(int(a) == int(b) - 1 for a, b in steps), f"reduced motion shows the final step: {steps}"
        pg.close()

    def test_ask_form_posts_the_briefing_signup(self, server, pw):
        A = manifest()["front"]["ask"]
        for status, body in ((200, '{"ok": true, "id": "x"}'), (500, '{"ok": false, "error": "' + A["error"] + '"}')):
            pg = self._open(pw, server, 390, 844)
            sent = []

            def answer(route, request, st=status, bd=body):
                sent.append(request.post_data)
                route.fulfill(status=st, content_type="application/json", body=bd)
            pg.route("**/_forms/briefing", answer)
            pg.evaluate("document.querySelector('#briefing').scrollIntoView()")
            pg.fill("#briefing input[type=email]", "someone@example.com")
            pg.click("#briefing button[type=submit]")
            pg.wait_for_timeout(500)
            assert sent and "someone@example.com" in sent[0], "the address goes to /_forms/briefing"
            text = pg.inner_text("#briefing")
            if status == 200:
                assert A["done"] in text and pg.locator("#ask-form").count() == 0
            else:
                assert A["error"] in text and pg.locator("#ask-form button").is_enabled(), "a failed post says so and lets you retry"
            pg.close()


    # ---- the shelf

    def test_shelf_follows_heyma_and_the_next_chain_reaches_it(self, server, pw):
        pg = self._open(pw, server, 390, 844)
        order = pg.evaluate("""() => [...document.querySelectorAll('main > section')].map(s => s.id)""")
        i = order.index("f-heyma")
        assert order[i + 1] == "shelf" and order[i + 2] == "f-flume", f"the shelf sits right after HeyMa, before Flume: {order}"
        assert pg.evaluate("document.querySelector('#shelf').matches('.ex, [data-flag]')") is False, "the shelf is not an exhibit: no pinning, no steps"
        assert pg.evaluate("document.querySelectorAll('#shelf .ex__num, #shelf .tile__n').length") == 0, "no F-number on the shelf"
        assert pg.evaluate("document.querySelector('#f-heyma .next').getAttribute('href')") == "#shelf"
        assert pg.evaluate("document.querySelector('#shelf .next').getAttribute('href')") == "#f-flume"
        # following the chain lands the shelf's heading below the header, then Flume's
        for start, target in (("#f-heyma .next", "#shelf"), ("#shelf .next", "#f-flume")):
            pg.evaluate(f"document.querySelector('{start}').scrollIntoView({{block: 'center'}})")
            pg.wait_for_timeout(200)
            pg.click(start)
            pg.wait_for_timeout(1200)
            r = pg.evaluate(f"({{ top: document.querySelector('{target}').getBoundingClientRect().top, hdr: document.querySelector('.hdr').getBoundingClientRect().bottom }})")
            assert -2 <= r["top"] - r["hdr"] <= 6, f"{target}: lands at {r['top']:.0f}px under a {r['hdr']:.0f}px header"
        pg.close()

    def test_shelf_cards_links_and_floors(self, server, pw):
        S = manifest()["front"]["shelf"]
        problems = []
        for w, h in FRONT_VIEWPORTS:
            pg = self._open(pw, server, w, h)
            pg.wait_for_timeout(300)
            r = pg.evaluate("""() => {
              const out = { cards: [], small: [], sx: document.documentElement.scrollWidth - innerWidth, hdr: document.querySelector('.hdr').getBoundingClientRect().bottom };
              for (const c of document.querySelectorAll('#shelf .shelf__card')) {
                const a = c.querySelector('a'), b = c.getBoundingClientRect(), ab = a.getBoundingClientRect();
                out.cards.push({ id: c.dataset.shelf, href: a.href, target: a.target, rel: a.rel, btnH: ab.height, left: b.left, right: b.right, btnRight: ab.right,
                  overflow: c.scrollWidth - c.clientWidth, offer: c.querySelector('.shelf__offer').innerText, pill: c.querySelector('.spill').innerText, primary: a.classList.contains('btn--quiet') ? 'quiet' : 'primary' });
              }
              const tw = document.createTreeWalker(document.querySelector('#shelf'), NodeFilter.SHOW_TEXT); let n;
              while ((n = tw.nextNode())) {
                const el = n.parentElement; if (!n.textContent.trim() || el.closest('.sr')) continue;
                const f = parseFloat(getComputedStyle(el).fontSize); if (f < 14) out.small.push(f + 'px ' + el.className + ' ' + n.textContent.trim().slice(0, 20));
              }
              return out;
            }""")
            if r["sx"] > 0:
                problems.append(f"{w}x{h}: scrolls sideways by {r['sx']}px")
            if [c["id"] for c in r["cards"]] != [x["id"] for x in S]:
                problems.append(f"{w}x{h}: cards {[c['id'] for c in r['cards']]} != manifest order")
            for c, x in zip(r["cards"], S):
                if c["href"] != x["href"] or c["target"] != "_blank" or "noopener" not in c["rel"]:
                    problems.append(f"{w}x{h}: {c['id']} link {c['href']} target={c['target']} rel={c['rel']}")
                if c["btnH"] < 44 or c["overflow"] > 0 or c["left"] < -0.5 or c["right"] > w + 0.5 or c["btnRight"] > c["right"] + 0.5:
                    problems.append(f"{w}x{h}: {c['id']} box {c}")
                if x["offer"] and (x["offer"] not in c["offer"] or x["asOf"] not in c["offer"]):
                    problems.append(f"{w}x{h}: {c['id']} offer line {c['offer']!r} is not the dated offer")
                if not x["offer"] and re.search(r"\d{4}|Offer as of", c["offer"]):
                    problems.append(f"{w}x{h}: {c['id']} has nothing for sale but its offer line is dated: {c['offer']!r}")
                if c["pill"] != x["pill"]:
                    problems.append(f"{w}x{h}: {c['id']} pill {c['pill']!r}")
                if (x["status"] == "on-sale") != (c["primary"] == "primary"):
                    problems.append(f"{w}x{h}: {c['id']}: only a product on sale gets the primary button")
            if w < 760 and r["small"]:
                problems.append(f"{w}x{h}: text under the 14px floor in the shelf: {r['small'][:3]}")
            pg.close()
        assert not problems, "\n".join(problems)

    def test_shelf_two_columns_from_a_tablet_one_on_a_phone(self, server, pw):
        for w, h, cols in ((360, 780, 1), (412, 915, 1), (768, 1024, 2), (1024, 768, 2), (1440, 900, 2)):
            pg = self._open(pw, server, w, h)
            xs = pg.evaluate("""() => [...document.querySelectorAll('#shelf .shelf__card')].map(c => Math.round(c.getBoundingClientRect().left))""")
            assert len(set(xs)) == cols, f"{w}x{h}: shelf cards at lefts {xs}, wanted {cols} column(s)"
            pg.close()

    def test_shelf_puts_buyable_first_whatever_the_data_order(self, server, pw):
        M = manifest()
        M["front"]["shelf"] = list(reversed(M["front"]["shelf"]))
        pg = pw.new_page(viewport={"width": 390, "height": 844})
        pg.route("**/manifest.json", lambda route, request: route.fulfill(status=200, content_type="application/json", body=json.dumps(M)))
        pg.goto(server)
        pg.wait_for_selector("html.ready")
        ids = pg.evaluate("[...document.querySelectorAll('#shelf .shelf__card')].map(c => c.dataset.shelf)")
        assert ids[0] == "earshot" and ids[-1] == "heyma", f"on-sale first, not-on-sale last: {ids}"
        pg.close()

    def test_shelf_drops_an_entry_that_is_not_a_store_page(self, server, pw):
        M = manifest()
        dropped = M["front"]["shelf"][0]["id"]
        kept = sorted(e["id"] for e in M["front"]["shelf"][1:])
        M["front"]["shelf"][0]["href"] = "https://buy.stripe.com/example"
        pg = pw.new_page(viewport={"width": 390, "height": 844})
        pg.route("**/manifest.json", lambda route, request: route.fulfill(status=200, content_type="application/json", body=json.dumps(M)))
        pg.goto(server)
        pg.wait_for_selector("html.ready")
        ids = pg.evaluate("[...document.querySelectorAll('#shelf .shelf__card')].map(c => c.dataset.shelf)")
        assert dropped not in ids and sorted(ids) == kept, f"a card whose href is not on the store is never drawn: {ids}"
        pg.close()


# ---------------------------------------------------------------- the phone and small-tablet tour (the flow view)

FLOW_PHONES = [(360, 640), (360, 780), (390, 844), (412, 915)]
FLOW_TEXT_JS = """() => {
  const small = [], w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
  while ((n = w.nextNode())) {
    const el = n.parentElement; if (!n.textContent.trim() || !el || el.closest('script,style,noscript')) continue;
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    if (!r.width || !r.height || cs.visibility === 'hidden') continue;
    const f = parseFloat(cs.fontSize); if (f < 14) small.push(f + 'px ' + el.className + ' "' + n.textContent.trim().slice(0, 24) + '"');
  }
  return small;
}"""


@pytest.mark.skipif(not LAYOUT, reason="set OVERNIGHT_LAYOUT=1 (needs playwright + chromium)")
class TestFlow(_Browser):
    """The tour on a phone (360-430px) and a small tablet: one column, each exhibit inline, a 14px floor, 44px targets, no sideways
    scroll, nothing under the header; an exhibit pins only if its whole stage fits, and its beats advance off the scroll."""

    def _open(self, pw, server, w, h, q="", **kw):
        pg = pw.new_page(viewport={"width": w, "height": h}, **kw)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type in ("error", "warning") else None)
        pg.goto(server + "tour.html" + q)
        pg.wait_for_selector(".fw[data-ready]")
        pg.wait_for_timeout(300)
        pg.errs = errs
        return pg

    def test_narrow_screens_open_the_flow_wide_ones_the_film(self, server, pw):
        for w, h, want in ((360, 640, ".fw"), (412, 915, ".fw"), (768, 1024, ".fw"), (820, 1180, ".fw"), (1024, 768, ".stage"), (1280, 720, ".stage")):
            pg = pw.new_page(viewport={"width": w, "height": h})
            pg.goto(server + "tour.html")
            pg.wait_for_selector(want)
            other = ".stage" if want == ".fw" else ".fw"
            assert pg.locator(other).count() == 0 and pg.locator(".logview").count() == 0, f"{w}x{h}: opened the wrong view"
            pg.close()
        pg = pw.new_page(viewport={"width": 390, "height": 844})
        pg.goto(server + "tour.html?view=log")
        pg.wait_for_selector(".logview")
        assert pg.locator(".fw").count() == 0, "?view=log still opens the plain list"
        pg.close()

    def test_no_sideways_scroll_nothing_under_header_no_console_errors(self, server, pw):
        problems = []
        for w, h in FLOW_PHONES + [(768, 1024)]:
            pg = self._open(pw, server, w, h)
            pg.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")   # every disclosure open: the long subjects, the transcripts
            pg.wait_for_timeout(200)
            total = pg.evaluate("document.documentElement.scrollHeight")
            y = 0
            while y < total:
                pg.evaluate(f"window.scrollTo(0,{y})")
                pg.wait_for_timeout(60)
                r = pg.evaluate("""() => {
                  const hb = document.getElementById('fw-hdr').getBoundingClientRect().bottom, bad = [];
                  for (const e of document.querySelectorAll('.fw h1, .fw h2, .fw h3, .fw-subj, .fw-btn, .fw-cta, .fw-chip, .fw-fig, .fw-dept, .fw-pool, .fw-ticket, .fw-tags li')) {
                    const b = e.getBoundingClientRect(); if (!b.width) continue;
                    if (b.right > innerWidth + 0.5 || b.left < -0.5) bad.push(e.className + ' x ' + Math.round(b.left) + '-' + Math.round(b.right));
                  }
                  return { sx: document.documentElement.scrollWidth - innerWidth, hb, bad };
                }""")
                if r["sx"] > 0:
                    problems.append(f"{w}x{h}@{y}: scrolls sideways by {r['sx']}px")
                if r["bad"]:
                    problems.append(f"{w}x{h}@{y}: off the sides {r['bad'][:3]}")
                y += int(h * 0.8)
            # a jump lands the section's head just under the header, never behind it
            for beat in manifest()["beats"][1:]:
                pg.evaluate(f"document.getElementById('{beat['id']}').scrollIntoView()")
                pg.wait_for_timeout(40)
                top = pg.evaluate(f"document.querySelector('#{beat['id']} h2').getBoundingClientRect().top")
                hb = pg.evaluate("document.getElementById('fw-hdr').getBoundingClientRect().bottom")
                if top < hb - 0.5:
                    problems.append(f"{w}x{h}: {beat['id']} heading is under the header ({top:.0f} < {hb:.0f})")
            if pg.errs:
                problems.append(f"{w}x{h}: console {pg.errs[:3]}")
            pg.close()
        assert not problems, "\n".join(problems[:20])

    def test_nothing_readable_under_14px_and_every_target_is_44px(self, server, pw):
        problems = []
        for w, h in FLOW_PHONES:
            pg = self._open(pw, server, w, h)
            pg.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
            small = pg.evaluate(FLOW_TEXT_JS)
            if small:
                problems.append(f"{w}x{h}: {len(small)} text runs under 14px, e.g. {small[:3]}")
            tiny = pg.evaluate("""() => [...document.querySelectorAll('.fw a[href], .fw button, .fw summary, .fw input:not(.gate__hp)')].filter(e => {
                if (e.closest('.fw-tape')) return false; const r = e.getBoundingClientRect(); return r.width && (r.height < 43.5 || r.width < 43.5); })
                .map(e => (e.className || e.tagName) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height))""")
            if tiny:
                problems.append(f"{w}x{h}: targets under 44px {tiny[:4]}")
            pg.close()
        assert not problems, "\n".join(problems)

    def test_header_is_compact_and_the_tour_button_is_gone(self, server, pw):
        M = manifest()["site"]
        for w, h in ((360, 640), (412, 915)):
            pg = self._open(pw, server, w, h)
            r = pg.evaluate("""() => { const q = s => document.querySelector(s).getBoundingClientRect();
              return { hdr: q('.fw-hdr'), cta: q('.fw-cta'), brand: q('.fw-brand'), nav: q('.fw-nav') }; }""")
            assert r["hdr"]["height"] <= 60, f"{w}: header is {r['hdr']['height']}px tall"
            assert r["cta"]["right"] <= w and r["nav"]["right"] <= r["cta"]["left"] + 1, f"{w}: the CTA covers the nav {r}"
            assert pg.locator(".fw-nav a").count() == len(M["nav"])
            assert pg.locator("a.fw-brand").get_attribute("href") == "index.html", "the brand is the way back to the front page"
            assert pg.get_by_text(M["viewFilm"], exact=True).count() == 0, "the page offers a tour of itself"
            pg.click(".fw-cta")
            pg.wait_for_timeout(900)
            r = pg.evaluate("(() => { const b = document.querySelector('#ask input[type=email]').getBoundingClientRect(); return [b.top, b.bottom, document.getElementById('fw-hdr').getBoundingClientRect().bottom]; })()")
            assert r[2] <= r[0] and r[1] <= h, f"{w}x{h}: the briefing CTA does not bring the form on screen under the header {r}"
            pg.close()

    def test_pins_only_when_the_whole_stage_fits(self, server, pw):
        problems, pinned = [], {}
        for w, h in FLOW_PHONES + [(768, 1024)]:
            pg = self._open(pw, server, w, h)
            info = pg.evaluate("""() => { const hdr = document.getElementById('fw-hdr').offsetHeight;
              return [...document.querySelectorAll('.fw-s')].map(s => ({ id: s.id, pinned: s.classList.contains('is-pinned'),
                need: s.firstElementChild.getBoundingClientRect().height, avail: innerHeight - hdr })); }""")
            pinned[(w, h)] = sum(1 for e in info if e["pinned"])
            # measured with the section pinned, its stage is the screen below the header: it never needs more
            for e in info:
                if e["pinned"] and e["need"] > e["avail"] + 1.5:
                    problems.append(f"{w}x{h}: {e['id']} is pinned but its stage is {e['need']:.0f}px of {e['avail']:.0f}")
            pg.close()
        assert pinned[(360, 640)] == 0, f"a 640px-tall phone cannot hold a stage under the header: {pinned}"
        assert pinned[(768, 1024)] >= 5, f"a tablet holds most stages: {pinned}"
        assert not problems, "\n".join(problems)

    def test_beats_advance_with_scroll_pinned_or_not(self, server, pw):
        for w, h in ((360, 640), (390, 844), (768, 1024)):
            pg = self._open(pw, server, w, h)
            seen, pools = set(), set()
            top = pg.evaluate("document.getElementById('gateway').getBoundingClientRect().top + scrollY")
            hh = pg.evaluate("document.getElementById('gateway').offsetHeight")
            for f in [x / 20 for x in range(0, 21)]:
                pg.evaluate(f"window.scrollTo(0,{top + (hh - h * 0.5) * f})")
                pg.wait_for_timeout(80)
                seen.add(pg.inner_text("#gateway .fw-decision code"))
                pools.add(pg.evaluate("[...document.querySelectorAll('#gateway .fw-pool')].map(p => p.className).join('|')"))
            assert len(seen) >= 2 and len(pools) >= 2, f"{w}x{h}: the gateway never changes as you scroll ({seen})"
            pg.close()

    def test_every_word_is_still_on_the_page(self, server, pw):
        M = manifest()
        norm = lambda t: re.sub(r"\s+", "", t)   # the lead, the "More" and the notes are separate blocks: compare the words, not the spacing
        pg = self._open(pw, server, 390, 844)
        pg.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
        for i, b in enumerate(M["beats"]):
            sid = "premise" if i == 0 else b["id"]
            text = norm(pg.evaluate(f"document.getElementById('{sid}').textContent"))
            for sentence in re.split(r"(?<=[.!?])\s+", b["body"]):   # the arrival's lead and "More" have the buttons between them
                assert norm(sentence) in text, f"{b['id']}: the body is cut at {sentence!r}"
            if b.get("copy", {}).get("aside"):
                assert norm(b["copy"]["aside"]) in text, f"{b['id']}: the aside is cut"
            for l in b.get("log", []):
                assert norm(l["subject"]) in text, f"{b['id']}: event subject {l['subject']} is missing"
                if l.get("note"):
                    assert norm(l["note"]) in text, f"{b['id']}: the note on {l['subject']} is missing"
        pg.close()

    def test_default_view_is_short_on_words(self, server, pw):
        """The point of the disclosures: far fewer words open by default than the list view, none lost (see the test above)."""
        pg = self._open(pw, server, 412, 915)
        flow = pg.evaluate("document.querySelector('.fw').innerText.split(/\\s+/).filter(Boolean).length")
        pg.close()
        pg = pw.new_page(viewport={"width": 412, "height": 915})
        pg.goto(server + "tour.html?view=log")
        pg.wait_for_selector(".logview")
        log = pg.evaluate("document.querySelector('.logview').innerText.split(/\\s+/).filter(Boolean).length")
        pg.close()
        assert flow < 0.8 * log, f"the flow opens with {flow} words, the list with {log}"

    def test_reduced_motion_never_pins_and_shows_final_states(self, server, pw):
        for w, h in ((390, 844), (1440, 900)):
            ctx = pw.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
            pg = ctx.new_page()
            pg.goto(server + "tour.html")
            pg.wait_for_selector(".fw[data-ready]")
            pg.wait_for_timeout(300)
            assert pg.evaluate("document.documentElement.classList.contains('fw-flat')")
            assert pg.evaluate("document.querySelectorAll('.fw-s.is-pinned').length") == 0
            last = manifest()["beats"][[b["id"] for b in manifest()["beats"]].index("gateway")]["copy"]["decisions"][-1]["route"]
            assert pg.inner_text("#gateway .fw-decision code") == last, f"{w}: reduced motion shows the first state, not the last"
            assert pg.evaluate("[...document.querySelectorAll('.fw-rv')].every(e => getComputedStyle(e).opacity === '1')")
            ctx.close()

    def test_the_footer_and_the_list_are_one_tap_apart(self, server, pw):
        M = manifest()["site"]
        pg = self._open(pw, server, 390, 844)
        assert pg.locator(f'.fw-foot a[href="{M["viewSimulationHref"]}"]').count() == 1, "the footer carries the 3D simulation link"
        pg.click(f'.fw-foot button:has-text("{M["viewLog"]}")')
        pg.wait_for_selector(".logview")
        assert pg.locator("a.hud__brief").is_visible() and pg.locator(".hud__nav button.btn").count() == 0, "the list's header offers the briefing, not the tour"
        pg.click(f'.logview__tour')
        pg.wait_for_selector(".fw[data-ready]")
        pg.close()

    def test_ask_form_posts_the_briefing_signup(self, server, pw):
        A = beat(manifest(), "ask")["copy"]
        pg = self._open(pw, server, 390, 844)
        sent = []

        def answer(route, request):
            sent.append(request.post_data)
            route.fulfill(status=200, content_type="application/json", body='{"ok": true, "id": "x"}')
        pg.route("**/_forms/briefing", answer)
        pg.evaluate("document.getElementById('ask').scrollIntoView()")
        pg.fill("#ask-email-flow", "someone@example.com")
        pg.click("#ask button[type=submit]")
        pg.wait_for_timeout(500)
        assert sent and "someone@example.com" in sent[0]
        assert A["done"] in pg.inner_text("#ask")
        pg.close()

    def test_reload_and_deep_links_keep_the_place(self, server, pw):
        pg = self._open(pw, server, 390, 844, "#heyma")
        pg.wait_for_timeout(300)
        top = pg.evaluate("document.querySelector('#heyma h2').getBoundingClientRect().top")
        assert 40 < top < 400, f"#heyma did not land on its section (heading at {top})"
        pg.evaluate("window.scrollTo(0, 7000)")
        pg.wait_for_timeout(300)
        y = pg.evaluate("scrollY")
        pg.reload()
        pg.wait_for_selector(".fw[data-ready]")
        pg.wait_for_timeout(400)
        assert abs(pg.evaluate("scrollY") - y) < 300, "a reload lost the place"
        pg.close()


# ---------------------------------------------------------------- one press of Down is one section

@pytest.mark.skipif(not LAYOUT, reason="set OVERNIGHT_LAYOUT=1 (needs playwright + chromium)")
class TestStepping(_Browser):
    """Presses the real page. ?pace=0.2 plays every move five times faster, so the whole tour is about 35 seconds."""
    PACE = 0.2

    def test_every_press_is_one_section(self, server):
        probe = Path(__file__).resolve().parents[1] / "overnight" / "step-probe.py"
        r = subprocess.run([sys.executable, str(probe), server, "--pace", str(self.PACE), "--json"], capture_output=True, text=True, timeout=400)
        assert r.stdout.strip(), r.stderr
        rep = json.loads(r.stdout)
        assert not rep["failed"], "\n".join(rep["failed"][:20])
        S = score()
        assert len(rep["moves"]) == len(S["majors"]), "one rest per major"
        # each move lasts what the score says (the node check prints the table for this viewport height)
        if NODE:
            t = subprocess.run([NODE, str(Path(__file__).with_name("overnight_score_check.js")), "--json"], capture_output=True, text=True, env={**os.environ, "OVERNIGHT_SITE": str(SITE)})
            nominal = json.loads(t.stdout)["720"]["forwardMs"]
            for mv, ms in zip(rep["moves"], nominal):
                want = ms * self.PACE
                assert 0.6 * want <= mv["ms"] <= 1.4 * want, f"{mv['major']}: moved for {mv['ms']}ms, the score says {want:.0f}ms"
        staff = next(m for m in rep["moves"] if m["major"] == "staff")
        assert staff["max_frame_gap_ms"] <= 150, f"the staff roll stuttered: a {staff['max_frame_gap_ms']}ms gap between frames"

    def test_simulation_link_and_header(self, server, pw):
        M = manifest()["site"]
        # the link is the last thing the header drops: it stays from a 900px window up to wide, and no header wraps
        for w, h in self.VIEWPORTS + [(1204, 800), (1210, 800), (1100, 800), (1024, 768), (820, 1180)]:
            pg = pw.new_page(viewport={"width": w, "height": h})
            pg.goto(server + "tour.html?view=film")
            pg.wait_for_selector(".hud")
            a = pg.locator("a.hud__sim")
            assert a.is_visible(), f"{w}: the 3D simulation link is hidden"
            assert a.get_attribute("href") == M["viewSimulationHref"] and a.get_attribute("target") == "_blank" and "noopener" in a.get_attribute("rel")
            assert a.inner_text() == M["viewSimulation"]
            hh = pg.evaluate("document.querySelector('.hud').getBoundingClientRect().height")
            assert hh <= 82, f"{w}: the header wrapped to {hh}px"
            pg.click(".hud__nav button.btn")           # View as log: the link stays
            pg.wait_for_selector(".logview")
            assert pg.locator("a.hud__sim").is_visible()
            pg.close()

    def test_phone_reaches_the_simulation_from_the_footer(self, server, pw):
        M = manifest()["site"]
        for q, sel in (("tour.html", ".fw-foot a[target=_blank]"), ("tour.html?view=log", "a.foot__sim")):
            pg = pw.new_page(viewport={"width": 390, "height": 844})
            pg.goto(server + q)
            pg.wait_for_selector(".fw[data-ready], .logview")
            assert not pg.locator("a.hud__sim").is_visible() and pg.locator(sel).is_visible(), q
            assert pg.locator(sel).get_attribute("href") == M["viewSimulationHref"]
            assert pg.evaluate("document.documentElement.scrollWidth") <= 390, "the phone header overflowed"
            pg.close()

    def test_tablet_keeps_the_caret(self, server, pw):
        """760 to 900px opens the film: no Down key on a tablet, so the caret must be there (the gauge may go)."""
        pg = pw.new_page(viewport={"width": 820, "height": 1180}, has_touch=True)
        pg.goto(server + "tour.html?view=film&pace=0.2")
        pg.wait_for_selector(".stage")
        pg.wait_for_timeout(700)
        assert pg.locator(".next").is_visible() and not pg.locator(".gauge").is_visible()
        pg.tap(".next")
        pg.wait_for_function("document.querySelector('.stage').dataset.station === '1' && document.querySelector('.stage').dataset.motion === 'rest'", timeout=20000)
        pg.close()

    def test_reload_and_deep_links_keep_the_place(self, server, pw):
        pg = pw.new_page(viewport={"width": 1280, "height": 720})
        pg.goto(server + "tour.html?view=film&pace=0.1")
        pg.wait_for_selector(".stage")
        pg.wait_for_timeout(700)
        for _ in range(3):
            pg.keyboard.press("ArrowDown")
            pg.wait_for_timeout(100)
            pg.wait_for_function("document.querySelector('.stage').dataset.motion === 'rest'", timeout=20000)
        assert pg.evaluate("location.hash") == "#numbers"
        pg.reload()
        pg.wait_for_selector(".stage")
        pg.wait_for_timeout(1200)
        st = pg.evaluate("({s: +document.querySelector('.stage').dataset.station, m: document.querySelector('.stage').dataset.motion, b: document.querySelector('.stage').dataset.beat})")
        assert st == {"s": 3, "m": "rest", "b": "numbers"}, f"a reload lost the place: {st}"
        pg.close()
        pg = pw.new_page(viewport={"width": 1280, "height": 720})   # a fresh tab: the hash alone
        pg.goto(server + "tour.html?view=film#staff")
        pg.wait_for_selector(".stage")
        pg.wait_for_timeout(1200)
        assert pg.evaluate("document.querySelector('.stage').dataset.beat") == "staff"
        pg.close()

    def test_tablet_card_and_loop_label_fit(self, server, pw):
        """1024x768: the department card is only as wide as the gap by the building. Nothing may run past it or be cut mid-sentence."""
        S = score()
        pg = pw.new_page(viewport={"width": 1024, "height": 768})
        pg.goto(server + "tour.html?view=film")
        pg.wait_for_selector(".hud")
        bad = []
        for mid in ("clock-records", "agents-desk", "runs-on-itself"):
            m = next(x for x in S["majors"] if x["id"] == mid)
            y = (m["start"] + (m["end"] - m["start"]) * 0.6) * S["scale"] * 768 / 100
            pg.evaluate(f"window.scrollTo(0,{y})")
            pg.wait_for_timeout(1500)
            bad += pg.evaluate("""(mid) => {
              const out = [], inside = (e, box) => { const r = e.getBoundingClientRect(); return r.right <= box.right + 0.5 && r.left >= box.left - 0.5; };
              if (mid === 'runs-on-itself') {
                const ring = document.querySelector('.loop__ring').getBoundingClientRect(), lab = document.querySelector('.loop__core .eyebrow').getBoundingClientRect();
                const cx = ring.left + ring.width / 2, cy = ring.top + ring.height / 2, rad = ring.width / 2;
                for (const [x, y] of [[lab.left, lab.top], [lab.right, lab.top], [lab.left, lab.bottom], [lab.right, lab.bottom]])
                  if (Math.hypot(x - cx, y - cy) > rad - 4) out.push('loop label corner outside the ring');
                return out;
              }
              const card = document.querySelector('.scard--dept'); if (!card) return ['no department card'];
              const box = card.getBoundingClientRect();
              card.querySelectorAll('.dept__name,.dept__role,.dept__n,.dept__label,.dept__stamp').forEach(e => {
                if (!inside(e, box)) out.push(e.className + ' runs past the card: ' + e.textContent.slice(0, 30));
              });
              card.querySelectorAll('.dept__label').forEach(e => { if (e.scrollHeight > e.clientHeight + 1) out.push('label cut: ' + e.textContent.slice(0, 30)); });
              return out;
            }""", mid)
        pg.close()
        assert not bad, "\n".join(bad)

    def test_header_does_not_jitter(self, server, pw):
        S = score()
        pg = pw.new_page(viewport={"width": 1280, "height": 720})
        pg.goto(server + "tour.html?view=film")
        pg.wait_for_selector(".hud")
        xs = {}
        for m in S["majors"][2:]:
            y = (m["start"] + (m["end"] - m["start"]) * 0.5) * S["scale"] * 720 / 100
            pg.evaluate(f"window.scrollTo(0,{y})")
            pg.wait_for_timeout(450)
            xs[m["id"]] = round(pg.evaluate("document.querySelector('.hud__nav').getBoundingClientRect().left"))
        pg.close()
        assert len(set(xs.values())) == 1, f"the header nav moves with the place name: {xs}"

    def test_log_view_deep_link_scrolls_to_the_entry(self, server, pw):
        pg = pw.new_page(viewport={"width": 390, "height": 844})
        pg.goto(server + "tour.html?view=log#flume")
        pg.wait_for_selector("#log-flume")
        pg.wait_for_timeout(500)
        top = pg.evaluate("document.getElementById('log-flume').getBoundingClientRect().top")
        assert pg.evaluate("window.scrollY") > 500 and 0 <= top < 200, f"#flume did not land on its entry (top {top})"
        pg.close()

    def test_log_view_has_no_empty_window_before_the_close(self, server, pw):
        pg = pw.new_page(viewport={"width": 390, "height": 844})
        pg.goto(server + "tour.html?view=log")
        pg.wait_for_selector(".logview__ask")
        assert pg.locator(".logview__you").count() == 0, "an unlit window with no label sits above the close"
        pg.close()

    def test_log_view_has_no_film_chrome(self, server, pw):
        for w, h in ((1280, 720), (390, 844)):
            pg = pw.new_page(viewport={"width": w, "height": h})
            pg.goto(server + "tour.html?view=log")
            pg.wait_for_selector(".logview")
            assert pg.locator(".gauge").count() == 0 and pg.locator(".next").count() == 0, f"{w}: the log view shows film chrome"
            pg.close()
        pg = pw.new_page(viewport={"width": 390, "height": 844})   # narrow screens open in the flow, which has no film chrome either
        pg.goto(server + "tour.html")
        pg.wait_for_selector(".fw[data-ready]")
        assert pg.locator(".gauge").count() == 0 and pg.locator(".next").count() == 0 and pg.locator(".stage").count() == 0
        pg.close()

    def test_reduced_motion_cuts(self, server, pw):
        ctx = pw.new_context(viewport={"width": 1280, "height": 720}, reduced_motion="reduce")
        pg = ctx.new_page()
        pg.goto(server + "tour.html?view=film")
        pg.wait_for_selector(".stage")
        pg.wait_for_timeout(600)
        pg.keyboard.press("ArrowDown")
        pg.wait_for_timeout(150)
        st = pg.evaluate("({m: document.querySelector('.stage').dataset.motion, s: +document.querySelector('.stage').dataset.station, y: scrollY})")
        assert st["m"] == "rest" and st["s"] == 1, f"a step under reduced motion must be a cut to the station: {st}"
        ctx.close()

    def test_caret_and_gauge_never_cover_copy(self, server, pw):
        """At every station, at the viewports that bind (and a tablet, where the film still opens): the caret and the
        Crank pill clear the captions, the cards and the nameplates; the gauge's ground sits on the ground line (48px above the stage bottom)."""
        problems = []
        for w, h in ((1280, 720), (1440, 860), (820, 1180)):
            pg = pw.new_page(viewport={"width": w, "height": h})
            pg.goto(server + "tour.html?view=film&pace=0.1")
            pg.wait_for_selector(".stage")
            pg.wait_for_timeout(700)
            for n in range(23):
                if n:
                    pg.keyboard.press("ArrowDown")
                    pg.wait_for_timeout(100)
                    pg.wait_for_function("document.querySelector('.stage').dataset.motion === 'rest'", timeout=30000)
                    pg.wait_for_timeout(500)
                hits = pg.evaluate("""() => {
                  const pill = document.querySelector('.crank'); pill.textContent = 'Still there? Crank keeps things moving.'; pill.classList.add('is-on');
                  const R = e => e.getBoundingClientRect(), caret = R(document.querySelector('.next')), gauge = R(document.querySelector('.gauge')), crank = R(pill);
                  const hit = (a, b) => !(a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom);
                  const out = [];
                  document.querySelectorAll('.cap, .scard, .plate, .roll, .org__grid, .directory, .car__screen, .car__list, .gate, .glass, .captions .on-caption, .cap__hint, .cap__actions').forEach(e => {
                    const r = R(e); if (r.width < 2 || r.height < 2) return;
                    if (e.closest('[style*="opacity: 0"]')) return;
                    if (hit(caret, r)) out.push('caret over ' + e.className);
                    if (hit(gauge, r)) out.push('gauge over ' + e.className);
                    if (hit(crank, r)) out.push('crank pill over ' + e.className);
                  });
                  if (gauge.width > 0) {
                    // the world's ground line is 48px above the stage bottom (the camera moves the building, not that line's rest)
                    const ground = R(document.querySelector('.stage')).bottom - 48, bar = R(document.querySelector('.gauge__ground')).bottom;
                    if (Math.abs(ground - bar) > 2) out.push('gauge ground ' + bar + ' is not the ground line ' + ground);
                  }
                  return out;
                }""")
                for hh in hits:
                    problems.append(f"{w}x{h} station {n}: {hh}")
            pg.close()
        assert not problems, "\n".join(problems[:20])



# ---------------------------------------------------------------- resize, rotation: a resized page must equal a fresh load
#
# Every page caches geometry (front.js geom(), flow.js readGeo(), the film's track top) and re-reads it only on a resize, a
# font, or a ResizeObserver. On 2026-11-23 a perf pass dropped the front page's resize listener and 521 tests stayed green, because
# none of them ever resized a page: pin decisions and --avail stayed at the old size until a reload. These tests open a page at
# one size, resize it to another, and require the same state a fresh load at the second size gives, at several scroll positions.

SNAPSHOT = """() => {
  const keep = ['--avail', '--q', '--f'];
  const props = [], pinned = [], steps = [];
  document.querySelectorAll('*').forEach((e, i) => {
    if (e.style && e.style.length) for (const k of keep) { const v = e.style.getPropertyValue(k); if (v !== '') props.push([i, k, v.trim()]); }
    if (e.classList.contains('is-pinned')) pinned.push(e.id || e.className);
    if (e.dataset && e.dataset.step !== undefined) steps.push([e.id || e.className, e.dataset.step]);
  });
  return { height: document.documentElement.scrollHeight, props, pinned, steps };
}"""


def _same(a, b):
    """Differences between two SNAPSHOTs: numbers within 0.02 (or 1.5px for px) are equal."""
    out = []
    if abs(a["height"] - b["height"]) > 2:
        out.append(f"page height {a['height']} vs fresh {b['height']}")
    if a["pinned"] != b["pinned"]:
        out.append(f"pinned {a['pinned']} vs fresh {b['pinned']}")
    if a["steps"] != b["steps"]:
        out.append(f"steps {a['steps']} vs fresh {b['steps']}")
    pa = {(i, k): v for i, k, v in a["props"]}
    pb = {(i, k): v for i, k, v in b["props"]}
    for key in sorted(set(pa) | set(pb)):
        va, vb = pa.get(key), pb.get(key)
        if va == vb:
            continue
        try:
            fa, fb = float(va.replace("px", "")), float(vb.replace("px", ""))
            if abs(fa - fb) <= (1.5 if "px" in (va or "") else 0.02):
                continue
        except (AttributeError, ValueError):
            pass
        out.append(f"element {key[0]} {key[1]} = {va} vs fresh {vb}")
    return out


@pytest.mark.skipif(not LAYOUT, reason="set OVERNIGHT_LAYOUT=1 (needs playwright + chromium)")
class TestResize(_Browser):
    """A page resized (or a phone rotated) must look and behave like a fresh load at the new size."""

    def _settle(self, pg, ms=450):
        """Wait out the rAF-coalesced resize handling, then until fonts are in and the page height holds still for 4 frames
        spaced 120ms apart (a fresh load reflows for up to a second while late fonts and the exhibits' measure land)."""
        pg.wait_for_timeout(ms)
        pg.evaluate("""() => new Promise(done => {
          const t0 = performance.now(); let last = -1, same = 0;
          (document.fonts ? document.fonts.ready : Promise.resolve()).then(function poll() {
            requestAnimationFrame(() => requestAnimationFrame(() => {
              const h = document.documentElement.scrollHeight;
              same = h === last ? same + 1 : 0; last = h;
              if (same >= 3 || performance.now() - t0 > 6000) done(); else setTimeout(poll, 120);
            }));
          });
        })""")

    def _compare(self, pw, url, ready, a, b, fractions=(0.0, 0.2, 0.45, 0.7, 0.95)):
        problems = []
        resized = pw.new_page(viewport={"width": a[0], "height": a[1]})
        errs = []
        resized.on("pageerror", lambda e: errs.append(str(e)))
        resized.goto(url); resized.wait_for_selector(ready); self._settle(resized)
        resized.evaluate("window.scrollTo(0, document.documentElement.scrollHeight * 0.3)"); self._settle(resized, 250)
        resized.set_viewport_size({"width": b[0], "height": b[1]}); self._settle(resized, 700)
        fresh = pw.new_page(viewport={"width": b[0], "height": b[1]})
        fresh.goto(url); fresh.wait_for_selector(ready); self._settle(fresh)
        for f in fractions:
            for pg in (resized, fresh):
                pg.evaluate(f"window.scrollTo(0, Math.round((document.documentElement.scrollHeight - innerHeight) * {f}))")
                self._settle(pg)
            for d in _same(resized.evaluate(SNAPSHOT), fresh.evaluate(SNAPSHOT)):
                problems.append(f"{a[0]}x{a[1]} -> {b[0]}x{b[1]} at {int(f * 100)}%: {d}")
        if errs:
            problems.append(f"{a} -> {b}: page errors {errs[:3]}")
        resized.close(); fresh.close()
        return problems

    def test_front_page(self, server, pw):
        problems = []
        for a, b in (((1280, 900), (900, 500)), ((900, 500), (1280, 900)), ((390, 844), (844, 390)), ((844, 390), (390, 844)), ((1440, 900), (412, 915))):
            problems += self._compare(pw, server, "html.ready", a, b)
        assert not problems, "\n".join(problems[:25])

    def test_flow_view(self, server, pw):
        problems = []
        for a, b in (((390, 844), (768, 1024)), ((768, 1024), (390, 844)), ((390, 844), (844, 390)), ((844, 390), (390, 844)), ((360, 640), (430, 932))):
            problems += self._compare(pw, server + "tour.html?view=flow", ".fw[data-ready]", a, b)
        assert not problems, "\n".join(problems[:25])

    def test_film_view(self, server, pw):
        """The film caches the track's top; after a resize, the page height and where Down lands must match a fresh load."""
        url = server + "tour.html?view=film&pace=0.2"

        def press(pg, n):
            for _ in range(n):
                pg.keyboard.press("ArrowDown")
                try:
                    pg.wait_for_function("document.querySelector('.stage').dataset.motion === 'moving'", timeout=1500)
                except Exception:
                    pass
                pg.wait_for_function("document.querySelector('.stage').dataset.motion === 'rest'", timeout=60000)
                pg.wait_for_timeout(80)

        def state(pg):
            return pg.evaluate("() => ({ y: Math.round(scrollY), station: +document.querySelector('.stage').dataset.station, height: document.documentElement.scrollHeight })")

        problems = []
        for a, b, before, after in (((1280, 720), (1000, 640), 2, 1), ((1000, 640), (1440, 900), 4, 2)):
            resized = pw.new_page(viewport={"width": a[0], "height": a[1]})
            resized.goto(url); resized.wait_for_selector(".stage"); self._settle(resized, 900)
            press(resized, before)
            resized.set_viewport_size({"width": b[0], "height": b[1]}); self._settle(resized, 900)
            press(resized, after)
            fresh = pw.new_page(viewport={"width": b[0], "height": b[1]})
            fresh.goto(url); fresh.wait_for_selector(".stage"); self._settle(fresh, 900)
            press(fresh, before + after)
            r, f = state(resized), state(fresh)
            if r["station"] != f["station"] or abs(r["y"] - f["y"]) > 2 or abs(r["height"] - f["height"]) > 2:
                problems.append(f"{a} -> {b}, {before}+{after} presses: resized {r} vs fresh {f}")
            resized.close(); fresh.close()
        assert not problems, "\n".join(problems)
