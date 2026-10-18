#!/usr/bin/env python3
"""Build the 33GOD Excalidraw library.

    python3 build.py            # write dist/, validate
    python3 build.py --check    # validate only

Item modules live in items/. Each exposes ITEMS, an ordered list of
(name, builder) pairs, where builder(x=0, y=0) returns a list of element
dicts from brand.py. Builders may tag elements with
local group names (groupIds=["glyph"]); they are namespaced per item here.
items/showcase.py may also expose SCENES, a list of (filename, builder)
pairs for composed example diagrams. A scene builder returns a list of
chunks (lists of elements); each chunk is finalized and grouped on its own,
so placing the same item twice never shares group ids.

Outputs (dist/):
  33god.excalidrawlib     the library (v2), one grouped unit per item
  33god-sheet.excalidraw  every item on one canvas with its name, for review
  <scene>.excalidraw      composed example diagrams from showcase.SCENES

Ids, seeds and fractional indices are derived from item names, so a rebuild
with no source change is byte-identical.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import brand  # noqa: E402

MODULES = ["items.brand_signals", "items.components", "items.flows"]
DIST = HERE / "dist"
SOURCE = "https://github.com/delorenj/33GOD"
# Fixed so the output is reproducible: 2026-10-18T00:00:00Z.
STAMP = 1792281600000

# Library order and review-sheet sections. Items not named here are appended
# under "More" so a new item never goes missing.
SECTIONS = [
    ("Brand", ["33GOD mark", "33GOD lockup", "Title block"]),
    ("Signals", ["Signal · Needs you", "Signal · Broken", "Signal · Stuck",
                 "Signal · Working", "Signal · No signal", "Signal · Quiet",
                 "Signal · Cleared", "Signal legend"]),
    ("Holocene patterns", ["Needs you · gate row", "Agent line", "Reading",
                           "Source strip", "All clear", "Census"]),
    ("Components", ["Bloodbank", "Candystore", "Holocene", "Krebs", "PJangler",
                    "Flume", "Momo", "Hermes gateway", "Hermes agent", "Hindsight",
                    "Pipeline MCP Hub", "Skillex", "HeyMa", "Pilot",
                    "External · Plane", "External · n8n", "External · GitHub",
                    "External · Event toaster", "Operator · You",
                    "Worker in worktree"]),
    ("Flows", ["Flow · Publish fact", "Flow · Command intent",
               "Flow · Lifecycle reply", "Flow · Durable delivery",
               "Flow · Recall / retain", "Flow · Ticket webhook", "Flow legend",
               "Event envelope", "Command envelope", "Lifecycle event pair"]),
    ("Templates", ["Krebs lifecycle track", "Ticket card", "Authority boundary",
                   "Facts / intent swimlanes", "Sequence lifelines", "Reject lane",
                   "Dead letter"]),
]
SHEET_WIDTH = 1480

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
ALLOWED_FONTS = {brand.SANS, brand.MONO}


def _digest(*parts: str) -> bytes:
    return hashlib.sha256("\x1f".join(parts).encode()).digest()


def _id(*parts: str) -> str:
    raw = _digest(*parts)
    return "".join(ALPHABET[b % 62] for b in raw[:20])


def _int(*parts: str) -> int:
    return int.from_bytes(_digest(*parts)[:4], "big") % 2_000_000_000


def _index(i: int) -> str:
    """Valid fractional-index keys in ascending order (a0..az, b00.., c000..)."""
    if i < 62:
        return "a" + ALPHABET[i]
    i -= 62
    if i < 62 ** 2:
        return "b" + ALPHABET[i // 62] + ALPHABET[i % 62]
    i -= 62 ** 2
    return "c" + ALPHABET[i // 3844] + ALPHABET[(i // 62) % 62] + ALPHABET[i % 62]


def finalize(name: str, elements: list[dict], *, group: bool = True,
             origin: bool = True) -> list[dict]:
    """Assign ids/seeds/indices, wire bound labels, group the item and move
    it to the origin. Returns new dicts; the builder's output is untouched."""
    els = [dict(e) for e in elements]
    by_obj = {id(src): out for src, out in zip(elements, els)}
    for n, e in enumerate(els):
        e["id"] = _id(name, "el", str(n))
        e["seed"] = _int(name, "seed", str(n))
        e["versionNonce"] = _int(name, "nonce", str(n))
        e["version"] = 1
        e["updated"] = STAMP
        e["groupIds"] = [_id(name, "g", g) for g in e.get("groupIds", [])]
    for e in els:
        src = e.pop("_container", None)
        if src is None:
            continue
        box = by_obj.get(id(src))
        if box is None:
            raise ValueError(f"{name}: label bound to a shape outside the item")
        e["containerId"] = box["id"]
        box["boundElements"] = (box.get("boundElements") or []) + [
            {"type": "text", "id": e["id"]}]
        e["groupIds"] = list(box["groupIds"])
    if group and els:
        gid = _id(name, "item")
        for e in els:
            e["groupIds"] = e["groupIds"] + [gid]
    if origin and els:
        x0, y0, _, _ = brand.bbox(els)
        for e in els:
            e["x"] = round(e["x"] - x0, 2)
            e["y"] = round(e["y"] - y0, 2)
    # Bound text must follow its container in z-order.
    for n, e in enumerate(els):
        e["index"] = _index(n)
    return els


def validate(name: str, els: list[dict]) -> list[str]:
    errs = []
    if not els:
        return [f"{name}: empty item"]
    ids = [e["id"] for e in els]
    if len(ids) != len(set(ids)):
        errs.append(f"{name}: duplicate element ids")
    for e in els:
        if e["type"] == "text":
            if e["fontFamily"] not in ALLOWED_FONTS:
                errs.append(f"{name}: text {e['text']!r} uses font {e['fontFamily']}")
            if not e["text"].strip():
                errs.append(f"{name}: empty text element")
        if e["type"] in ("line", "arrow") and len(e["points"]) < 2:
            errs.append(f"{name}: {e['type']} with fewer than 2 points")
        if e.get("roughness") != 0:
            errs.append(f"{name}: roughness must be 0 (architect)")
        for k in ("x", "y", "width", "height"):
            v = e[k]
            if v != v or abs(v) > 20000:
                errs.append(f"{name}: bad {k}={v}")
        if any(k.startswith("_") for k in e):
            errs.append(f"{name}: leaked private key on {e['type']}")
    x0, y0, x1, y1 = brand.bbox(els)
    if not name.startswith("scene:") and (x1 - x0 > 1800 or y1 - y0 > 1400):
        errs.append(f"{name}: item is {x1 - x0:.0f}x{y1 - y0:.0f}, too large for a library tile")
    return errs


def load_items() -> list[tuple[str, callable]]:
    out = []
    for mod in MODULES:
        try:
            m = importlib.import_module(mod)
        except ModuleNotFoundError as exc:
            if exc.name == mod:
                print(f"skip {mod}: not written yet", file=sys.stderr)
                continue
            raise
        out.extend(m.ITEMS)
    return out


def ordered(built):
    """Items in SECTIONS order, with any unlisted items under "More"."""
    by = dict(built)
    out, seen = [], set()
    for title, names in SECTIONS:
        rows = [(n, by[n]) for n in names if n in by]
        seen.update(n for n, _ in rows)
        if rows:
            out.append((title, rows))
    rest = [(n, e) for n, e in built if n not in seen]
    if rest:
        out.append(("More", rest))
    return out


def sheet(built: list[tuple[str, list[dict]]]) -> list[dict]:
    """Every item on one canvas, by section and captioned, for visual review
    and the preview image. Shelf-packed to SHEET_WIDTH."""
    els: list[dict] = []
    gap_x, gap_y, cap, sec_gap = 56, 48, 30, 72
    y = 0.0
    for title, rows in ordered(built):
        els.extend(finalize("sheet-section:" + title, [
            brand.caps(0, y, title, color=brand.INK_2, size=brand.SIZE_SMALL),
            brand.hline(0, y + 24, SHEET_WIDTH, stroke=brand.LINE_STRONG),
        ], group=False, origin=False))
        y += 24 + 32
        x, row_h = 0.0, 0.0
        for name, items in rows:
            _, _, w, h = brand.bbox(items)
            cw = max(w, brand.measure(name, brand.SIZE_DATA, brand.MONO)[0])
            if x > 0 and x + cw > SHEET_WIDTH:
                x, y, row_h = 0.0, y + row_h + gap_y, 0.0
            for e in items:
                e2 = dict(e)
                e2["x"] = round(e["x"] + x, 2)
                e2["y"] = round(e["y"] + y + cap, 2)
                els.append(e2)
            caption = brand.text(x, y, name, size=brand.SIZE_DATA,
                                 family=brand.MONO, color=brand.INK_3)
            els.extend(finalize("sheet-caption:" + name, [caption], group=False,
                                origin=False))
            x += cw + gap_x
            row_h = max(row_h, h + cap)
        y += row_h + sec_gap
    for n, e in enumerate(els):
        e["index"] = _index(n)
    return els


def scene_doc(elements: list[dict]) -> dict:
    return {
        "type": "excalidraw",
        "version": 2,
        "source": SOURCE,
        "elements": elements,
        "appState": {"viewBackgroundColor": brand.GROUND, "gridSize": 20},
        "files": {},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--only", action="append", metavar="MODULE",
                    help="build just these item modules (e.g. items.flows); repeatable")
    ap.add_argument("--out", type=Path, default=DIST,
                    help="output directory (use a scratch dir with --only)")
    ap.add_argument("--no-scenes", action="store_true")
    args = ap.parse_args()
    if args.only:
        MODULES[:] = args.only

    built, errs, names = [], [], set()
    for name, builder in load_items():
        if name in names:
            errs.append(f"duplicate item name {name!r}")
        names.add(name)
        try:
            els = finalize(name, builder())
        except Exception as exc:  # report every broken item, not just the first
            errs.append(f"{name}: builder raised {exc!r}")
            continue
        errs += validate(name, els)
        built.append((name, els))

    scenes = []
    try:
        if args.no_scenes:
            raise ModuleNotFoundError(name="items.showcase")
        showcase = importlib.import_module("items.showcase")
        for fname, builder in getattr(showcase, "SCENES", []):
            els = []
            for n, chunk in enumerate(builder()):
                fin = finalize(f"scene:{fname}:{n}", chunk, group=len(chunk) > 1,
                               origin=False)
                errs += validate(f"scene:{fname}:{n}", fin)
                els.extend(fin)
            for n, e in enumerate(els):
                e["index"] = _index(n)
            scenes.append((fname, els))
    except ModuleNotFoundError as exc:
        if exc.name != "items.showcase":
            raise

    for e in errs:
        print("ERROR", e, file=sys.stderr)
    print(f"{len(built)} items, {sum(len(e) for _, e in built)} elements, "
          f"{len(scenes)} scenes, {len(errs)} errors")
    if errs:
        return 1
    if args.check:
        return 0

    built = [(n, e) for _, rows in ordered(built) for n, e in rows]
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    lib = {
        "type": "excalidrawlib",
        "version": 2,
        "source": SOURCE,
        "libraryItems": [
            {"id": _id(name, "libitem"), "status": "published", "created": STAMP,
             "name": name, "elements": els}
            for name, els in built
        ],
    }
    (out / "33god.excalidrawlib").write_text(json.dumps(lib, indent=1) + "\n")
    (out / "33god-sheet.excalidraw").write_text(json.dumps(scene_doc(sheet(built)), indent=1) + "\n")
    for fname, els in scenes:
        (out / fname).write_text(json.dumps(scene_doc(els), indent=1) + "\n")
    (out / "item-names.json").write_text(json.dumps([n for n, _ in built], indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
