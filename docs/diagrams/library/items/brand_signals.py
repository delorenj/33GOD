"""Brand and signal items: the mark, lockups, title blocks, the seven signal
glyphs as chips, and the Holocene row patterns (gate, agent line, reading).

Reference module: the other item modules follow the shape used here.
"""

from __future__ import annotations

from brand import *  # noqa: F403


def mark_item(x=0, y=0):
    """The 33GOD mark at a size that reads on a diagram."""
    return mark(x, y, 96)


def lockup(x=0, y=0):
    """Mark, wordmark, hairline, surface name: "33GOD | Holocene"."""
    els = mark(x, y, 48)
    els.append(text(x + 56, y + 6, "33GOD", size=SIZE_TITLE, color=INK))
    word_w, _ = measure("33GOD", SIZE_TITLE)
    rule_x = x + 56 + word_w + 14
    els.append(poly([(rule_x, y + 12), (rule_x, y + 38)], stroke=LINE_STRONG))
    els.append(text(rule_x + 14, y + 15, "Holocene", size=SIZE_HEADING, color=INK_3))
    return els


# --- small local helpers -----------------------------------------------------


def _tw(s, size, family=SANS):
    return measure(s, size, family)[0]


def _cy(y_center, size):
    """Top y that centres a single line of `size` text on `y_center`."""
    return y_center - size * LINE_HEIGHT / 2


def _chip_w(els):
    return els[0]["width"]


def _button(x, y, w, h, s, *, primary):
    if primary:
        box = rect(x, y, w, h, stroke=INK, fill=INK, rounded=True)
        return [box, label(box, s, size=SIZE_BODY, color=ON_INK)]
    box = rect(x, y, w, h, stroke=LINE_STRONG, rounded=True)
    return [box, label(box, s, size=SIZE_BODY, color=INK)]


# --- title block ---------------------------------------------------------------


def title_block(x=0, y=0):
    """The header every view opens with: kicker, one sentence that says what
    the diagram is for, a quieter line under it, a small lockup, a hairline."""
    w = 800
    els = []
    els.append(caps(x, y + 7, "33GOD · Platform context"))
    # small lockup, right edge on the block edge
    word = "33GOD"
    ww = _tw(word, SIZE_HEADING)
    lx = x + w - (24 + 8 + ww)
    els += mark(lx, y, 24)
    els.append(text(lx + 32, y + 1, word, size=SIZE_HEADING, color=INK))
    els.append(text(x, y + 32, "Facts flow into durable history; intent flows to agents.",
                    size=SIZE_TITLE, color=INK))
    els.append(text(x, y + 76, "Everything is an event. A command is intent, never proof that the work is done.",
                    size=SIZE_BODY, color=INK_2))
    els.append(hline(x, y + 108, w, stroke=LINE_STRONG))
    return els


# --- signal chips ----------------------------------------------------------------

_SIGNAL_CARDS = {
    "you": ("awaiting_operator", "Waiting on the operator."),
    "broken": ("dead_letter", "Failed, and will not recover alone."),
    "stuck": ("lease_expired", "Over its time budget."),
    "working": ("tool_running", "Running, inside its time budget."),
    "unknown": ("no_heartbeat", "Never observed. Not zero."),
    "quiet": ("idle", "Healthy and idle."),
    "cleared": ("completed", "Left the queue recently."),
}


def _signal_card(kind):
    def build(x=0, y=0):
        state, line = _SIGNAL_CARDS[kind]
        w = 248
        c = chip(x, y, SIGNALS[kind][2], kind=kind, h=24)
        els = list(c)
        els.append(text(x + _chip_w(c) + 12, y + _cy(12, SIZE_DATA), state,
                        size=SIZE_DATA, family=MONO, color=INK_3))
        els.append(hline(x, y + 36, w))
        els.append(text(x, y + 46, line, size=SIZE_SMALL, color=INK_2))
        return els
    return build


# --- signal legend -------------------------------------------------------------------

_LEGEND = [
    ("you", "A decision or an answer is waiting on the operator."),
    ("broken", "Failed, and will not recover without a change."),
    ("stuck", "Over its time budget, derived from time, never from an error."),
    ("working", "Doing the work it was given, inside its time budget."),
    ("unknown", "Never observed. Shown as no signal, never as zero."),
    ("quiet", "Healthy and idle. Healthy is quiet."),
    ("cleared", "Left the queue recently: shipped, closed, recovered."),
]


def signal_legend(x=0, y=0):
    """All seven signals: glyph and word in the soft chip, then what it means."""
    w = 620
    els = [caps(x, y, "Signals"), hline(x, y + 22, w, stroke=LINE_STRONG)]
    top = y + 36
    pitch = 36
    for i, (kind, meaning) in enumerate(_LEGEND):
        ry = top + i * pitch
        els += chip(x, ry, SIGNALS[kind][2], kind=kind, h=24)
        els.append(text(x + 124, ry + _cy(12, SIZE_BODY), meaning, size=SIZE_BODY, color=INK_2))
    els.append(hline(x, top + len(_LEGEND) * pitch - 4, w))
    els.append(text(x, top + len(_LEGEND) * pitch + 6,
                    "Shape first, colour second. Every signal reads in greyscale.",
                    size=SIZE_SMALL, color=INK_3))
    return els


# --- needs-you gate row -----------------------------------------------------------------


def gate_row(x=0, y=0):
    """Holocene NeedsYou row: the only filled row in the system. Ochre-soft
    ground, ochre diamond, the question as a sentence, then the two actions."""
    w, h = 760, 72
    els = [rect(x, y, w, h, stroke=OCHRE, fill=OCHRE_SOFT)]
    els += glyph("you", x + 16, y + 24, 20)
    tx = x + 52
    els.append(caps(tx, y + 11, "Needs you", color=OCHRE))
    kx = tx + _tw("NEEDS YOU", SIZE_LABEL) + 14
    ref = chip(kx, y + 8, "HOLOC-8", color=INK_2, fill=SURFACE, family=MONO,
               size=SIZE_DATA, h=20)
    els += ref
    els.append(text(kx + _chip_w(ref) + 12, y + _cy(18, SIZE_DATA), "4m",
                    size=SIZE_DATA, family=MONO, color=INK_3))
    els.append(text(tx, y + 36, "holocene-pm asks whether HOLOC-8 should land as one PR or three.",
                    size=SIZE_BODY, color=INK))
    bh = 32
    by = y + (h - bh) / 2
    els += _button(x + w - 16 - 104, by, 104, bh, "Go to pane", primary=False)
    els += _button(x + w - 16 - 104 - 8 - 80, by, 80, bh, "Answer", primary=True)
    return els


# --- agent line -------------------------------------------------------------------------------


def agent_line(x=0, y=0):
    """Holocene AgentLine: a sentence first, then the facts."""
    w = 640
    els = glyph("working", x, y + 1, 18)
    ident = "bloodbank-pm"
    els.append(text(x + 30, y + _cy(10, SIZE_BODY), ident, size=SIZE_BODY, family=MONO, color=INK))
    sx = x + 30 + _tw(ident, SIZE_BODY, MONO) + 14
    els.append(text(sx, y + _cy(10, SIZE_BODY), "is renaming the NATS subjects before it opens a PR.",
                    size=SIZE_BODY, color=INK_2))
    cx = x + 30
    cy = y + 30
    for s in ("BLOOD-41", "blood-41/subject-rename", "12m", "7 tools"):
        c = chip(cx, cy, s, color=INK_2, fill=SUNKEN, family=MONO, size=SIZE_DATA, h=22)
        els += c
        cx += _chip_w(c) + 8
    els.append(hline(x, y + 66, w))
    return els


# --- reading tile -------------------------------------------------------------------------------


def reading(x=0, y=0):
    """A Reading: label, figure, a sentence that says whether it is normal,
    and its age. The sparkline is the last seven days."""
    w, h = 264, 124
    els = [rect(x, y, w, h, stroke=LINE, fill=SURFACE)]
    els.append(caps(x + 16, y + 14, "Detectors evaluated"))
    els.append(text(x + w - 16, y + _cy(20, SIZE_DATA), "4s", size=SIZE_DATA, family=MONO,
                    color=INK_3, align="right"))
    els.append(text(x + 16, y + 34, "9", size=32, color=INK))
    sx0, sx1 = x + w - 16 - 104, x + w - 16
    base = y + 64
    ys = [4, 4, 5, 7, 10, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14]
    pts = [(sx0 + (sx1 - sx0) * i / (len(ys) - 1), base - v) for i, v in enumerate(ys)]
    els.append(hline(sx0, base + 2, sx1 - sx0, stroke=LINE))
    els.append(poly(pts, stroke=LAKE, width=2))
    ex, ey = pts[-1]
    els.append(ellipse(ex - 3, ey - 3, 6, 6, stroke=LAKE, fill=LAKE))
    els.append(hline(x + 16, y + 84, w - 32))
    els.append(text(x + 16, y + 94, "The same 9 for 2 days.", size=SIZE_SMALL, color=INK_2))
    return els


# --- source strip -----------------------------------------------------------------------------------


def source_strip(x=0, y=0):
    """The strip that tops every live view. A stale feed says so in the stuck
    colour with a tilde; a feed never observed says no signal, not zero."""
    feeds = [
        ("quiet", "Bloodbank", "2s", INK_3, True),
        ("quiet", "Candystore", "3s", INK_3, True),
        ("quiet", "Hermes gateway", "11s", INK_3, True),
        ("stuck", "Plane webhook", "~ 6m", HEATHER, True),
        ("unknown", "Hindsight", "No signal", INK_3, False),
    ]
    els = [caps(x, y + _cy(14, SIZE_LABEL) + 1, "Sources")]
    cx = x + 84
    for kind, name, age, color, is_mono in feeds:
        els += glyph(kind, cx, y + 6, 16)
        els.append(text(cx + 24, y + _cy(14, SIZE_SMALL), name, size=SIZE_SMALL, color=INK))
        ax = cx + 24 + _tw(name, SIZE_SMALL) + 8
        fam = MONO if is_mono else SANS
        size = SIZE_DATA if is_mono else SIZE_SMALL
        els.append(text(ax, y + _cy(14, size), age, size=size, family=fam, color=color))
        cx = ax + _tw(age, size, fam) + 28
    els.append(hline(x, y + 36, cx - 28 - x))
    return els


# --- all clear ----------------------------------------------------------------------------------------


def all_clear(x=0, y=0):
    """The empty state that proves it is empty. Quiet, not moss."""
    w = 560
    els = [caps(x, y, "Needs you"), hline(x, y + 22, w, stroke=LINE_STRONG)]
    els += glyph("quiet", x + 4, y + 50, 20)
    els.append(text(x + 36, y + 49, "Nothing needs you. 9 detectors evaluated, newest 4s ago.",
                    size=SIZE_STATEMENT, color=INK))
    els.append(hline(x, y + 92, w))
    return els


# --- census ---------------------------------------------------------------------------------------------


def census(x=0, y=0):
    """A population at a glance: one cell per Hermes gateway. Quiet cells are
    empty outlines so the few that are not quiet are the only things drawn."""
    cols, cell, gap = 12, 28, 4
    n = 24
    state = {3: "working", 6: "broken", 10: "stuck", 17: "broken"}
    gw = cols * cell + (cols - 1) * gap
    els = [caps(x, y, "Hermes gateways"),
           text(x + gw, y + _cy(7, SIZE_DATA), "24", size=SIZE_DATA, family=MONO,
                color=INK_3, align="right"),
           hline(x, y + 22, gw, stroke=LINE_STRONG)]
    gy = y + 36
    for i in range(n):
        cx = x + (i % cols) * (cell + gap)
        cy = gy + (i // cols) * (cell + gap)
        kind = state.get(i, "quiet")
        if kind == "quiet":
            els.append(rect(cx, cy, cell, cell, stroke=LINE))
        else:
            _, soft, _ = SIGNALS[kind]
            els.append(rect(cx, cy, cell, cell, stroke=soft, fill=soft))
        els += glyph(kind, cx + (cell - 16) / 2, cy + (cell - 16) / 2, 16)
    cap_y = gy + 2 * cell + gap + 14
    lead = "2 of 24 gateways broken: "
    els.append(text(x, cap_y, lead, size=SIZE_BODY, color=INK))
    names = "delodocs-pm, voxxy-pm."
    els.append(text(x + _tw(lead, SIZE_BODY) - 4, cap_y + _cy(9, SIZE_DATA) - _cy(9, SIZE_BODY) + 1,
                    names, size=SIZE_DATA + 1, family=MONO, color=INK))
    return els


ITEMS = [
    ("33GOD mark", mark_item),
    ("33GOD lockup", lockup),
    ("Title block", title_block),
    ("Signal · Needs you", _signal_card("you")),
    ("Signal · Broken", _signal_card("broken")),
    ("Signal · Stuck", _signal_card("stuck")),
    ("Signal · Working", _signal_card("working")),
    ("Signal · No signal", _signal_card("unknown")),
    ("Signal · Quiet", _signal_card("quiet")),
    ("Signal · Cleared", _signal_card("cleared")),
    ("Signal legend", signal_legend),
    ("Needs you · gate row", gate_row),
    ("Agent line", agent_line),
    ("Reading", reading),
    ("Source strip", source_strip),
    ("All clear", all_clear),
    ("Census", census),
]
