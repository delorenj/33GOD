"""33GOD brand primitives for Excalidraw.

Tokens are the Holocene "Snow" theme (holocene/design/project/tokens.json).
Excalidraw's own dark mode inverts the canvas, so the library ships light
values only. Every helper returns plain Excalidraw element dicts; ids and
seeds are assigned later by build.py, so item modules never think about them.

Rules carried over from the design system (holocene/design/project/README.md):
- Ochre means you. Only the operator, a gate, or something waiting on the
  operator wears ochre. Never decoration.
- Healthy is quiet (ink-3). Moss is earned: shipped, closed, recovered.
- Shape before colour: every signal has a glyph that survives greyscale.
- Machine words stay machine words: subjects, SHAs, ids go in MONO.
- Corners barely soften; hairlines and space, not boxes.
"""

from __future__ import annotations

import math

# --- colour (Snow) -----------------------------------------------------------

GROUND = "#ebefec"
SURFACE = "#f6f8f6"
SUNKEN = "#e0e5e1"
LINE = "#d1d7d2"
LINE_STRONG = "#7b827c"
INK = "#1a201b"
INK_2 = "#454d46"
INK_3 = "#606761"
ON_INK = "#f6f8f6"

OCHRE, OCHRE_SOFT = "#835d13", "#f1e5cc"  # you
BRICK, BRICK_SOFT = "#9c4230", "#f8e0db"  # broken
HEATHER, HEATHER_SOFT = "#67567d", "#e9e3f1"  # stuck
LAKE, LAKE_SOFT = "#3a6479", "#dbe9f0"  # working
MOSS, MOSS_SOFT = "#43673f", "#deebdc"  # cleared

# Categorical series, assigned in order. In diagrams they name FLOWS, never
# state: slate = events (facts), clay = commands (intent), teal = lifecycle
# replies, sand = tickets, plum = memory, lichen = provisioning.
SLATE = "#2a6ea2"
CLAY = "#af6340"
TEAL = "#1493a5"
SAND = "#a88831"
PLUM = "#8a4976"
LICHEN = "#728b40"

FLOW = {
    "event": SLATE,
    "command": CLAY,
    "lifecycle": TEAL,
    "ticket": SAND,
    "memory": PLUM,
    "provision": LICHEN,
}

TRANSPARENT = "transparent"

# --- type --------------------------------------------------------------------
# Excalidraw has no Newsreader or Atkinson. Nunito carries display and sans,
# Cascadia carries everything a machine wrote.

SANS = 6  # Nunito
MONO = 3  # Cascadia

# Sizes on the Holocene scale, nudged up a step because diagrams are read
# zoomed out.
SIZE_DISPLAY = 36
SIZE_TITLE = 28
SIZE_STATEMENT = 20
SIZE_HEADING = 16
SIZE_BODY = 14
SIZE_SMALL = 13
SIZE_LABEL = 11
SIZE_DATA = 12

LINE_HEIGHT = 1.25

# Advance per font-size unit, used to pre-size text boxes and to place things
# after text. Excalidraw re-measures once fonts load; these are fitted to
# Nunito and Cascadia closely enough for layout.
_MONO_ADVANCE = 0.59
_NARROW = set("iljtf.,:;'|!()[]/\\` ")
_WIDE = set("mwMW@%")


def _sans_advance(ch: str) -> float:
    if ch in _NARROW:
        return 0.30
    if ch in _WIDE:
        return 0.88
    if ch.isupper() or ch.isdigit():
        return 0.66
    return 0.52


def measure(text: str, size: float, family: int = SANS) -> tuple[float, float]:
    lines = text.split("\n")
    if family == MONO:
        width = max(len(line) for line in lines) * size * _MONO_ADVANCE
    else:
        width = max(sum(_sans_advance(c) for c in line) for line in lines) * size
    height = len(lines) * size * LINE_HEIGHT
    return round(width, 2), round(height, 2)


# --- element factory ---------------------------------------------------------


def _base(kind: str, x: float, y: float, w: float, h: float, **kw) -> dict:
    el = {
        "type": kind,
        "x": round(x, 2),
        "y": round(y, 2),
        "width": round(w, 2),
        "height": round(h, 2),
        "angle": 0,
        "strokeColor": kw.pop("stroke", INK),
        "backgroundColor": kw.pop("fill", TRANSPARENT),
        "fillStyle": "solid",
        "strokeWidth": kw.pop("width", 1),
        "strokeStyle": kw.pop("style", "solid"),
        "roughness": 0,
        "opacity": kw.pop("opacity", 100),
        "groupIds": [],
        "frameId": None,
        "roundness": kw.pop("roundness", None),
        "boundElements": None,
        "link": None,
        "locked": False,
        "isDeleted": False,
    }
    el.update(kw)
    return el


def rect(x, y, w, h, *, stroke=INK, fill=TRANSPARENT, width=1, style="solid",
         rounded=False, opacity=100) -> dict:
    """Rectangle. `rounded` uses Excalidraw's adaptive radius; keep it for
    chips and buttons only. Panels and nodes stay sharp."""
    return _base("rectangle", x, y, w, h, stroke=stroke, fill=fill, width=width,
                 style=style, opacity=opacity,
                 roundness={"type": 3} if rounded else None)


def ellipse(x, y, w, h, *, stroke=INK, fill=TRANSPARENT, width=1, style="solid",
            opacity=100) -> dict:
    return _base("ellipse", x, y, w, h, stroke=stroke, fill=fill, width=width,
                 style=style, opacity=opacity)


def diamond(x, y, w, h, *, stroke=INK, fill=TRANSPARENT, width=1) -> dict:
    return _base("diamond", x, y, w, h, stroke=stroke, fill=fill, width=width)


def text(x, y, s, *, size=SIZE_BODY, family=SANS, color=INK, align="left",
         valign="top", width=None) -> dict:
    """Free-standing text. For text centred in a shape use `label()`.

    With align="center" or "right", `x` is the anchor (centre / right edge),
    so the text stays put when Excalidraw re-measures it.
    """
    w, h = measure(s, size, family)
    if width is not None:
        w = width
    left = x - w / 2 if align == "center" else x - w if align == "right" else x
    return _base("text", left, y, w, h, stroke=color, text=s, originalText=s,
                 fontSize=size, fontFamily=family, textAlign=align,
                 verticalAlign=valign, containerId=None, autoResize=True,
                 lineHeight=LINE_HEIGHT)


def caps(x, y, s, *, color=INK_3, size=SIZE_LABEL, align="left") -> dict:
    """The `label` style: small uppercase, quiet ink. Source text may be any
    case; it is upper-cased here so callers write sentence case."""
    return text(x, y, s.upper(), size=size, family=SANS, color=color, align=align)


def label(container: dict, s: str, *, size=SIZE_BODY, family=SANS, color=INK,
          align="center", valign="middle") -> dict:
    """Text bound inside `container` (rectangle, ellipse or diamond);
    Excalidraw keeps it centred when the shape is resized. One label per
    container. build.py wires containerId/boundElements once ids exist."""
    w, h = measure(s, size, family)
    t = _base("text", container["x"] + (container["width"] - w) / 2,
              container["y"] + (container["height"] - h) / 2, w, h,
              stroke=color, text=s, originalText=s, fontSize=size,
              fontFamily=family, textAlign=align, verticalAlign=valign,
              containerId=None, autoResize=True, lineHeight=LINE_HEIGHT)
    t["_container"] = container
    return t


def poly(points: list[tuple[float, float]], *, stroke=INK, fill=TRANSPARENT,
         width=1, style="solid", closed=None, opacity=100) -> dict:
    """Polyline in absolute coordinates. A closed path (first == last point,
    or closed=True) fills with `fill`."""
    pts = list(points)
    if closed is None:
        closed = fill != TRANSPARENT
    if closed and pts[0] != pts[-1]:
        pts.append(pts[0])
    x0, y0 = pts[0]
    rel = [[round(px - x0, 3), round(py - y0, 3)] for px, py in pts]
    xs = [p[0] for p in rel]
    ys = [p[1] for p in rel]
    el = _base("line", x0, y0, max(xs) - min(xs), max(ys) - min(ys),
               stroke=stroke, fill=fill, width=width, style=style,
               opacity=opacity, points=rel, lastCommittedPoint=None,
               startBinding=None, endBinding=None, startArrowhead=None,
               endArrowhead=None)
    if closed:
        el["polygon"] = True
    return el


def hline(x, y, w, *, stroke=LINE, width=1, style="solid") -> dict:
    """A hairline. The Holocene panel is a heading over one of these."""
    return poly([(x, y), (x + w, y)], stroke=stroke, width=width, style=style)


def arrow(points: list[tuple[float, float]], *, stroke=INK, width=2,
          style="solid", head="triangle", tail=None, elbow=False) -> dict:
    """Arrow through absolute points. Heads: "arrow", "triangle", "bar",
    "dot", "circle", "diamond" or None."""
    x0, y0 = points[0]
    rel = [[round(px - x0, 3), round(py - y0, 3)] for px, py in points]
    xs = [p[0] for p in rel]
    ys = [p[1] for p in rel]
    return _base("arrow", x0, y0, max(xs) - min(xs), max(ys) - min(ys),
                 stroke=stroke, width=width, style=style, points=rel,
                 lastCommittedPoint=None, startBinding=None, endBinding=None,
                 startArrowhead=tail, endArrowhead=head, elbowed=elbow,
                 roundness=None)


def arc_points(cx, cy, r, start_deg, end_deg, steps=24) -> list[tuple[float, float]]:
    """Points along a circular arc; 0deg is east, angles grow clockwise
    (screen space)."""
    out = []
    for i in range(steps + 1):
        a = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def half_disc(cx, cy, r, side: str, *, fill=INK) -> dict:
    """Filled half-disc whose flat edge is the vertical through (cx, cy).
    side="left" bulges left, "right" bulges right."""
    pts = arc_points(cx, cy, r, 90, 270) if side == "left" else arc_points(cx, cy, r, -90, 90)
    return poly(pts, stroke=fill, fill=fill, width=1, closed=True)


# --- brand marks ---------------------------------------------------------------


def mark(x, y, size=48, *, ink=INK, lit=OCHRE) -> list[dict]:
    """The 33GOD mark: 33 against its mirror, four half-discs on a 24-unit
    grid, lower-right quadrant lit. Never recolour the lit quadrant, rotate
    or animate the mark. `size` is the grid box edge in px."""
    s = size / 24
    r = 5.25 * s
    return [
        half_disc(x + 11 * s, y + 6.75 * s, r, "left", fill=ink),
        half_disc(x + 11 * s, y + 17.25 * s, r, "left", fill=ink),
        half_disc(x + 13 * s, y + 6.75 * s, r, "right", fill=ink),
        half_disc(x + 13 * s, y + 17.25 * s, r, "right", fill=lit),
    ]


# --- signal glyphs ---------------------------------------------------------------
# Seven shapes on a 10-unit grid (assets/Glyphs). `size` is the glyph box.

SIGNALS = {
    # key: (colour, soft fill, word)
    "you": (OCHRE, OCHRE_SOFT, "Needs you"),
    "broken": (BRICK, BRICK_SOFT, "Broken"),
    "stuck": (HEATHER, HEATHER_SOFT, "Stuck"),
    "working": (LAKE, LAKE_SOFT, "Working"),
    "unknown": (INK_3, SUNKEN, "No signal"),
    "quiet": (INK_3, SUNKEN, "Quiet"),
    "cleared": (MOSS, MOSS_SOFT, "Cleared"),
}


def glyph(kind: str, x, y, size=16) -> list[dict]:
    c = SIGNALS[kind][0]
    u = size / 10
    if kind == "you":
        return [diamond(x + 0.45 * u, y + 0.45 * u, 9.1 * u, 9.1 * u, stroke=c, fill=c)]
    if kind == "broken":
        return [rect(x + 1 * u, y + 1 * u, 8 * u, 8 * u, stroke=c, fill=c)]
    if kind == "stuck":
        top = poly([(x + 1.2 * u, y + 1 * u), (x + 8.8 * u, y + 1 * u), (x + 5 * u, y + 4.85 * u)],
                   stroke=c, fill=c)
        bot = poly([(x + 1.2 * u, y + 9 * u), (x + 8.8 * u, y + 9 * u), (x + 5 * u, y + 5.15 * u)],
                   stroke=c, fill=c)
        return [top, bot]
    if kind == "working":
        ring = ellipse(x + 1.3 * u, y + 1.3 * u, 7.4 * u, 7.4 * u, stroke=c,
                       width=max(1, 1.3 * u * 0.75), opacity=32)
        sweep = poly(arc_points(x + 5 * u, y + 5 * u, 3.7 * u, -90, 0, 10), stroke=c,
                     width=max(1.5, 1.6 * u * 0.9))
        return [ring, sweep]
    if kind == "unknown":
        return [ellipse(x + 1.4 * u, y + 1.4 * u, 7.2 * u, 7.2 * u, stroke=c,
                        width=max(1, 1.2 * u * 0.75), style="dotted")]
    if kind == "quiet":
        return [rect(x + 1.4 * u, y + 4.25 * u, 7.2 * u, 1.5 * u, stroke=c, fill=c)]
    if kind == "cleared":
        return [ellipse(x + 1 * u, y + 1 * u, 8 * u, 8 * u, stroke=c, fill=c)]
    raise KeyError(kind)


def chip(x, y, s, *, kind=None, color=INK_2, fill=SUNKEN, family=SANS,
         size=SIZE_SMALL, pad_x=8, h=22) -> list[dict]:
    """A pill: optional signal glyph, then words. Signal chips take their
    colour and soft fill from SIGNALS."""
    if kind:
        color, fill, _ = SIGNALS[kind]
    tw, _ = measure(s, size, family)
    g = 12 if kind else 0
    gap = 6 if kind else 0
    w = pad_x * 2 + g + gap + tw
    box = rect(x, y, w, h, stroke=fill, fill=fill, rounded=True)
    out = [box]
    if kind:
        out += glyph(kind, x + pad_x, y + (h - g) / 2, g)
    out.append(text(x + pad_x + g + gap, y + (h - size * LINE_HEIGHT) / 2, s,
                    size=size, family=family, color=color))
    return out


def bbox(elements: list[dict]) -> tuple[float, float, float, float]:
    xs, ys, xe, ye = [], [], [], []
    for e in elements:
        if e["type"] in ("line", "arrow"):
            for px, py in e["points"]:
                xs.append(e["x"] + px)
                ys.append(e["y"] + py)
                xe.append(e["x"] + px)
                ye.append(e["y"] + py)
        else:
            xs.append(e["x"])
            ys.append(e["y"])
            xe.append(e["x"] + e["width"])
            ye.append(e["y"] + e["height"])
    return min(xs), min(ys), max(xe), max(ye)


# --- shared diagram vocabulary -------------------------------------------------
# Every module draws nodes and flows through these two helpers so a diagram
# built from mixed items still reads as one system.

NODE_W = 240
NODE_PAD = 14
PICTO = 40


def node(x, y, name: str, role: str, detail: str | None = None, *,
         picto=None, w=NODE_W, kind="internal") -> list[dict]:
    """A 33GOD component card.

    role    the `label`-style kicker, sentence case in source ("Event bus").
    name    the component name in the heading size.
    detail  optional machine words in MONO (subjects, units, endpoints);
            may contain newlines.
    picto   callable(x, y, size) -> elements, drawn in a PICTO box at left.
    kind    "internal" (surface card, strong hairline), "external" (dashed,
            unfilled: Plane, n8n, GitHub), or "you" (the operator: ochre).
    """
    detail_h = measure(detail, SIZE_DATA, MONO)[1] + 8 if detail else 0
    h = NODE_PAD * 2 + 40 + detail_h
    if kind == "you":
        card = rect(x, y, w, h, stroke=OCHRE, fill=OCHRE_SOFT, width=2)
    elif kind == "external":
        card = rect(x, y, w, h, stroke=LINE_STRONG, style="dashed")
    else:
        card = rect(x, y, w, h, stroke=LINE_STRONG, fill=SURFACE)
    els = [card]
    tx = x + NODE_PAD
    if picto is not None:
        els += picto(x + NODE_PAD, y + NODE_PAD, PICTO)
        tx = x + NODE_PAD + PICTO + 12
    els.append(caps(tx, y + NODE_PAD, role, color=OCHRE if kind == "you" else INK_3))
    els.append(text(tx, y + NODE_PAD + 16, name, size=SIZE_HEADING + 2, color=INK))
    if detail:
        els.append(hline(x + NODE_PAD, y + NODE_PAD + 48, w - NODE_PAD * 2))
        els.append(text(x + NODE_PAD, y + NODE_PAD + 54, detail, size=SIZE_DATA,
                        family=MONO, color=INK_2))
    return els


FLOW_STYLE = {
    # kind: (stroke style, arrowhead)
    "event": ("solid", "triangle"),     # a fact: it happened
    "command": ("dashed", "triangle"),  # intent: it should happen; not evidence
    "lifecycle": ("solid", "dot"),      # started / completed / failed / rejected
    "ticket": ("solid", "triangle"),
    "memory": ("dotted", "triangle"),   # recall / retain, advisory only
    "provision": ("solid", "bar"),
}


def flow(kind: str, points: list[tuple[float, float]], words: str | None = None,
         *, both=False) -> list[dict]:
    """A typed connector. Colour and dash carry the flow kind (see FLOW and
    FLOW_STYLE); `words` is bound to the arrow in MONO so it rides along when
    the arrow is moved."""
    style, head = FLOW_STYLE[kind]
    a = arrow(points, stroke=FLOW[kind], width=2, style=style, head=head,
              tail=head if both else None)
    els = [a]
    if words:
        els.append(label(a, words, size=SIZE_DATA, family=MONO, color=FLOW[kind]))
    return els
