"""Flows, envelopes, lifecycle and structural templates.

Connectors are drawn through brand.flow() so colour, dash and arrowhead keep
one meaning everywhere: slate event (fact), clay command (intent, dashed),
teal lifecycle reply, sand ticket, plum memory (dotted), lichen provision.

Reusable builders (all take x=0, y=0 and return element lists):
    flow_publish, flow_command, flow_lifecycle, flow_durable, flow_memory,
    flow_ticket, flow_legend, event_envelope, command_envelope,
    lifecycle_pair, krebs_track, ticket_card, authority_boundary,
    swimlanes, sequence_lifelines, reject_lane, dead_letter
"""

from __future__ import annotations

from brand import *  # noqa: F403

TEAL_SOFT = "#d6edf0"  # lifecycle highlight band; derived from TEAL

# --- small local helpers -------------------------------------------------------


def _chip_w(s, *, kind=None, family=SANS, size=SIZE_SMALL, pad_x=8):
    tw, _ = measure(s, size, family)
    return pad_x * 2 + (18 if kind else 0) + tw


def _kv(x, y, rows, key_w, *, size=SIZE_DATA, pitch=22, hi=None):
    """Mono key/value rows. `hi` is a row index drawn in INK, the rest quiet."""
    out = []
    for i, (k, v) in enumerate(rows):
        ry = y + i * pitch
        out.append(text(x, ry, k, size=size, family=MONO, color=INK_3))
        out.append(text(x + key_w, ry, v, size=size, family=MONO, color=INK))
    return out


def _dash_stripe(x, y, h, color, w=5, dash=10, gap=6):
    """An edge stripe that reads as dashed: the command flavour of the solid
    slate stripe. Built from rects so it stays crisp at any zoom."""
    out, cy = [], y
    while cy < y + h - 1:
        out.append(rect(x, cy, w, min(dash, y + h - cy), stroke=color, fill=color))
        cy += dash + gap
    return out


def _end(x, y, s, align):
    """Endpoint name. Caps style, except lowercase product names (n8n)."""
    if s == "n8n":
        return text(x, y, s, size=SIZE_LABEL, color=INK_3, align=align)
    return caps(x, y, s, align=align)


# --- 1. flow connectors ---------------------------------------------------------


def _flow_unit(x, y, kind, words, subject, src, dst, kicker, meaning, *,
               w=260, both=False):
    """A connector as a meaningful unit: endpoints, the typed arrow with its
    verb, the subject it travels on, and a one-line meaning."""
    ya = y + 28
    els = [
        _end(x, y, src, "left"),
        _end(x + w, y, dst, "right"),
        poly([(x, y + 16), (x, y + 40)], stroke=LINE_STRONG, width=2),
        poly([(x + w, y + 16), (x + w, y + 40)], stroke=LINE_STRONG, width=2),
    ]
    els += flow(kind, [(x + 8, ya), (x + w - 8, ya)], words, both=both)
    els.append(text(x + w / 2, y + 50, subject, size=SIZE_DATA, family=MONO,
                    color=INK_2, align="center"))
    els.append(hline(x, y + 78, w))
    els.append(caps(x, y + 90, kicker, color=INK_3))
    els.append(text(x, y + 108, meaning, size=SIZE_SMALL, color=INK_2))
    return els


def flow_publish(x=0, y=0):
    return _flow_unit(x, y, "event", "publish fact", "bloodbank.evt.>",
                      "Producer", "Bloodbank", "Event · fact",
                      "A fact. It already happened.")


def flow_command(x=0, y=0):
    return _flow_unit(x, y, "command", "command via JetStream", "bloodbank.cmd.>",
                      "Momo", "Hermes gateway", "Command · intent",
                      "Intent. Never proof it happened.", w=300)


def flow_lifecycle(x=0, y=0):
    return _flow_unit(x, y, "lifecycle", "started / completed / failed / rejected",
                      "bloodbank.rpy.>", "Hermes profile", "Bloodbank",
                      "Lifecycle · reply", "The only proof that work happened.",
                      w=380)


def flow_durable(x=0, y=0):
    return _flow_unit(x, y, "event", "Dapr durable consumer", "candystore-events",
                      "Bloodbank", "Candystore", "Event · durable",
                      "Every event is kept in PostgreSQL.", w=280)


def flow_memory(x=0, y=0):
    return _flow_unit(x, y, "memory", "recall / retain", "api.hs.delo.sh",
                      "Agent", "Hindsight", "Memory · advisory",
                      "Advisory. Not ticket authority.", both=True)


def flow_ticket(x=0, y=0):
    return _flow_unit(x, y, "ticket", "signed raw HTTPS", "X-Plane-Signature",
                      "Plane", "n8n", "Ticket · webhook",
                      "HMAC checked over the raw body.", w=280)


# --- 2. legend -------------------------------------------------------------------

_LEGEND = [
    ("event", "Event", "Fact. Something happened and is stored."),
    ("command", "Command", "Intent; never completion evidence."),
    ("lifecycle", "Lifecycle", "Reply: started, completed, failed, rejected."),
    ("ticket", "Ticket", "Plane ticket traffic, signed at the edge."),
    ("memory", "Memory", "Hindsight recall and retain; advisory."),
    ("provision", "Provision", "Deterministic setup by PJangler."),
]


def flow_legend(x=0, y=0):
    w, pitch, top = 560, 40, 52
    h = top + pitch * len(_LEGEND) + 40
    els = [rect(x, y, w, h, stroke=LINE, fill=SURFACE),
           caps(x + 20, y + 16, "Flow legend"),
           hline(x + 20, y + 38, w - 40, stroke=LINE_STRONG)]
    for i, (kind, name, meaning) in enumerate(_LEGEND):
        ry = y + top + i * pitch
        cy = ry + pitch / 2
        style, head = FLOW_STYLE[kind]
        els.append(arrow([(x + 20, cy), (x + 84, cy)], stroke=FLOW[kind], width=2,
                         style=style, head=head))
        els.append(text(x + 108, cy - 10, name, size=SIZE_HEADING, color=INK))
        els.append(text(x + 212, cy - 8, meaning, size=SIZE_SMALL, color=INK_2))
        if i < len(_LEGEND) - 1:
            els.append(hline(x + 20, ry + pitch, w - 40))
    els.append(text(x + 20, y + h - 28, "Colour names the flow. Dash and head name the kind.",
                    size=SIZE_SMALL, color=INK_3))
    return els


# --- 3 / 4. envelopes ------------------------------------------------------------


def _envelope(x, y, *, kicker, color, subject, rows, note, dashed, w=448):
    pitch = 22
    rows_top = y + 74
    rows_h = len(rows) * pitch
    h = 74 + rows_h + 6 + 14 + 14 + 14
    els = [rect(x, y, w, h, stroke=color if dashed else LINE_STRONG, fill=SURFACE,
                style="dashed" if dashed else "solid")]
    if dashed:
        els += _dash_stripe(x, y, h, color)
    else:
        els.append(rect(x, y, 6, h, stroke=color, fill=color))
    tx = x + 24
    els.append(caps(tx, y + 14, kicker, color=color))
    els.append(text(tx, y + 34, subject, size=SIZE_BODY, family=MONO, color=INK))
    els.append(hline(tx, y + 62, w - 24 - 18))
    els += _kv(tx, rows_top, rows, 112)
    ny = rows_top + rows_h + 6
    els.append(hline(tx, ny, w - 24 - 18))
    els.append(caps(tx, ny + 14, note, color=color if dashed else INK_3))
    return els


def event_envelope(x=0, y=0):
    return _envelope(
        x, y, kicker="Event · fact", color=SLATE,
        subject="bloodbank.evt.repo.task.created",
        rows=[("id", "01JC8Y4Q7H2V9K3M5T6R0ZXEWB"),
              ("source", "urn:33god:integration:n8n:plane-webhook"),
              ("producer", "n8n"),
              ("correlationid", "plane-HOLOC-8-c7a91e"),
              ("time", "2026-10-18T09:41:07Z")],
        note="Fact · stored in Candystore", dashed=False)


def command_envelope(x=0, y=0):
    return _envelope(
        x, y, kicker="Command · intent", color=CLAY,
        subject="bloodbank.cmd.agent.invocation.start",
        rows=[("id", "01JC8Y5A3N6D1R8W2B4F7HQVCS"),
              ("producer", "momo"),
              ("target_agent", "holocene-pm"),
              ("thread_id", "thr_holoc8_7f3a"),
              ("correlationid", "plane-HOLOC-8-c7a91e"),
              ("time", "2026-10-18T09:41:09Z")],
        note="Intent · not evidence", dashed=True)


# --- 5. lifecycle pair -------------------------------------------------------------


def lifecycle_pair(x=0, y=0):
    w, gap, pad = 300, 100, 16
    h = 188
    cards = [
        ("working", "Started", "bloodbank.agent.invocation.started",
         "01JC8Y5B8M2K4T6V9X1ZQRHDNE", "2026-10-18T09:41:12Z"),
        ("cleared", "Completed", "bloodbank.agent.invocation.completed",
         "01JC8Y7G2P5S8W3C6F9JMTAXKB", "2026-10-18T09:43:52Z"),
    ]
    els = []
    corr_y = y + 80 + 2 * 22
    for i, (kind, word, subject, ident, when) in enumerate(cards):
        cx = x + i * (w + gap)
        els.append(rect(cx, y, w, h, stroke=LINE_STRONG, fill=SURFACE))
        els += chip(cx + pad, y + 14, word, kind=kind)
        els.append(text(cx + pad, y + 46, subject, size=SIZE_DATA, family=MONO, color=INK))
        els.append(hline(cx + pad, y + 70, w - 2 * pad))
        els.append(rect(cx + 6, corr_y - 3, w - 12, 22, stroke=TEAL_SOFT, fill=TEAL_SOFT))
        rows = [("id", ident[:16] + "…"), ("producer", "holocene-pm"),
                ("correlationid", "plane-HOLOC-8-c7a91e"), ("time", when)]
        for j, (k, v) in enumerate(rows):
            ry = y + 80 + j * 22
            els.append(text(cx + pad, ry, k, size=SIZE_DATA, family=MONO,
                            color=TEAL if k == "correlationid" else INK_3))
            els.append(text(cx + pad + 112, ry, v, size=SIZE_DATA, family=MONO,
                            color=INK))
    gx0, gx1 = x + w, x + w + gap
    els += flow("lifecycle", [(gx0 + 12, y + 25), (gx1 - 12, y + 25)])
    els.append(poly([(gx0, corr_y + 8), (gx1, corr_y + 8)], stroke=TEAL, width=2))
    els.append(ellipse(gx0 - 3, corr_y + 5, 6, 6, stroke=TEAL, fill=TEAL))
    els.append(ellipse(gx1 - 3, corr_y + 5, 6, 6, stroke=TEAL, fill=TEAL))
    els.append(caps(x + w + gap / 2, corr_y - 14, "same id", color=TEAL, align="center"))
    return els


# --- 6. Krebs lifecycle track --------------------------------------------------------

_STATES = ["backlog", "triage", "refining", "ready", "in_progress", "review", "qa", "done"]


def krebs_track(x=0, y=0, current="in_progress"):
    nw, nh, gap = 92, 44, 20
    pitch = nw + gap
    total = len(_STATES) * nw + (len(_STATES) - 1) * gap
    ny = y + 76
    nx = {s: x + i * pitch for i, s in enumerate(_STATES)}
    els = [caps(x, y, "Krebs · ticket lifecycle"),
           text(x + total, y, "krebs/spec/lifecycle.v1.yaml", size=SIZE_LABEL,
                family=MONO, color=INK_3, align="right"),
           hline(x, y + 22, total, stroke=LINE_STRONG)]
    for s in _STATES:
        if s == current:
            box = rect(nx[s], ny, nw, nh, stroke=LAKE, fill=LAKE_SOFT, width=2)
            col = LAKE
        elif s == "done":
            box = rect(nx[s], ny, nw, nh, stroke=MOSS, fill=MOSS_SOFT)
            col = MOSS
        else:
            box = rect(nx[s], ny, nw, nh, stroke=LINE_STRONG, fill=SURFACE)
            col = INK_2
        els += [box, label(box, s, size=SIZE_DATA, family=MONO, color=col)]
    for a, b in zip(_STATES, _STATES[1:]):
        els.append(arrow([(nx[a] + nw + 3, ny + nh / 2), (nx[b] - 3, ny + nh / 2)],
                         stroke=INK_3, width=1.5, head="triangle"))
    cw = _chip_w("Working", kind="working")
    els += chip(nx[current] + (nw - cw) / 2, y + 40, "Working", kind="working")
    ny2 = ny + nh + 8
    els.append(text(nx["in_progress"] + 22, ny2, "WIP = 1", size=SIZE_DATA,
                    family=MONO, color=INK_3))
    els.append(text(nx["review"] + 22, ny2, "reviewer ≠\nimplementer", size=SIZE_DATA,
                    family=MONO, color=INK_3))
    els.append(caps(nx["done"] + nw / 2, ny2, "Terminal", align="center"))
    # blocked: terminal, needs the operator, branches off the working states
    bus_y = ny + nh + 56
    for s in ("in_progress", "review", "qa"):
        els.append(poly([(nx[s] + 10, ny + nh), (nx[s] + 10, bus_y)], stroke=OCHRE,
                        width=1.5, style="dashed"))
    els.append(poly([(nx["in_progress"] + 10, bus_y), (nx["qa"] + 10, bus_y)],
                    stroke=OCHRE, width=1.5, style="dashed"))
    bw = 140
    bx = nx["review"] + 10 - bw / 2
    by = bus_y + 28
    els.append(arrow([(nx["review"] + 10, bus_y), (nx["review"] + 10, by - 2)],
                     stroke=OCHRE, width=2, head="triangle"))
    els.append(rect(bx, by, bw, nh, stroke=OCHRE, fill=OCHRE_SOFT, width=2))
    els += glyph("you", bx + 14, by + (nh - 16) / 2, 16)
    els.append(text(bx + 40, by + (nh - SIZE_DATA * LINE_HEIGHT) / 2, "blocked",
                    size=SIZE_DATA, family=MONO, color=OCHRE))
    els.append(caps(bx + bw + 14, by + (nh - SIZE_LABEL * LINE_HEIGHT) / 2,
                    "Terminal · needs you", color=OCHRE))
    return els


# --- 7. ticket card ----------------------------------------------------------------------


def ticket_card(x=0, y=0):
    w, h = 380, 214
    els = [rect(x, y, w, h, stroke=LINE_STRONG, fill=SURFACE),
           rect(x, y, 5, h, stroke=SAND, fill=SAND)]
    tx = x + 24
    els.append(caps(tx, y + 14, "Ticket · Plane"))
    els.append(text(tx, y + 32, "HOLOC-8", size=SIZE_STATEMENT, family=MONO, color=INK))
    phase_w = _chip_w("in_progress", kind="working", family=MONO, size=SIZE_DATA)
    els += chip(x + w - 16 - phase_w, y + 32, "in_progress", kind="working",
                family=MONO, size=SIZE_DATA)
    els.append(text(tx, y + 68, "Show hook health on the\nmission-control board.",
                    size=SIZE_HEADING, color=INK))
    els.append(hline(tx, y + 116, w - 24 - 16))
    els.append(caps(tx, y + 128, "Assignee"))
    els.append(text(tx, y + 146, "holocene-pm", size=SIZE_DATA, family=MONO, color=INK))
    lx = x + 200
    els.append(caps(lx, y + 128, "Labels"))
    for word in ("holocene", "hooks"):
        els += chip(lx, y + 144, word)
        lx += _chip_w(word) + 6
    els.append(hline(tx, y + 178, w - 24 - 16))
    els.append(text(tx, y + 188, "plane.delo.sh · workspace 33god", size=SIZE_LABEL,
                    family=MONO, color=INK_3))
    return els


# --- 8. authority boundary ------------------------------------------------------------------


def authority_boundary(x=0, y=0):
    w, h = 520, 168
    pad = 20
    return [
        rect(x, y, w, h, stroke=LINE_STRONG, style="dashed"),
        caps(x + pad, y + 16, "Authority · Candystore", color=INK_2),
        text(x + w - pad, y + 15, "candystore-events", size=SIZE_LABEL, family=MONO,
             color=INK_3, align="right"),
        hline(x + pad, y + 38, w - 2 * pad, stroke=LINE_STRONG),
        caps(x + pad, y + 52, "Owns"),
        text(x + pad, y + 68, "Durable event history, audit and replay.", size=SIZE_BODY,
             color=INK),
        caps(x + pad, y + 100, "Not authoritative for"),
        text(x + pad, y + 116, "Ticket state, agent memory and routing.", size=SIZE_BODY,
             color=INK_2),
    ]


# --- 9. swimlanes ------------------------------------------------------------------------------


def swimlanes(x=0, y=0, w=900, h=360, lane=180, arrows=True):
    """Facts over intent. `w`, `h` and `lane` (height of the facts lane) let a
    diagram size it to its nodes; `arrows=False` drops the hairline direction
    arrows at the foot of each lane when connectors cross there."""
    col = 232
    pad = 24
    els = [
        rect(x, y, w, h, stroke=LINE_STRONG),
        hline(x, y + lane, w, stroke=LINE_STRONG),
        poly([(x + col, y), (x + col, y + h)], stroke=LINE),
        rect(x, y, 5, lane, stroke=SLATE, fill=SLATE),
        *_dash_stripe(x, y + lane, h - lane, CLAY),
        caps(x + pad, y + 20, "Facts", color=INK_2),
        text(x + pad, y + 40, "Events flow left to right\ninto durable history.",
             size=SIZE_BODY, color=INK),
        text(x + pad, y + lane - 28, "bloodbank.evt.>", size=SIZE_LABEL, family=MONO,
             color=INK_3),
        caps(x + pad, y + lane + 20, "Intent", color=INK_2),
        text(x + pad, y + lane + 40, "Commands request work;\nthey do not claim it\nhappened.",
             size=SIZE_BODY, color=INK),
        text(x + pad, y + h - 28, "bloodbank.cmd.>", size=SIZE_LABEL, family=MONO,
             color=INK_3),
    ]
    if arrows:
        els += [
            arrow([(x + col + 24, y + lane - 16), (x + w - 24, y + lane - 16)],
                  stroke=LINE_STRONG, width=1, head="arrow"),
            arrow([(x + col + 24, y + h - 16), (x + w - 24, y + h - 16)],
                  stroke=LINE_STRONG, width=1, style="dashed", head="arrow"),
        ]
    return els


# --- 10. sequence lifelines -----------------------------------------------------------------------


def sequence_lifelines(x=0, y=0):
    hw, hh, step = 150, 40, 260
    names = ["Producer", "Bloodbank", "Consumer"]
    cx = [x + hw / 2 + i * step for i in range(3)]
    els = []
    for n, c in zip(names, cx):
        box = rect(c - hw / 2, y, hw, hh, stroke=LINE_STRONG, fill=SURFACE)
        els += [box, label(box, n, size=SIZE_BODY, color=INK)]
        els.append(poly([(c, y + hh), (c, y + 300)], stroke=LINE_STRONG, width=1,
                        style="dashed"))
    msgs = [
        (1, 0, 1, "event", "publish fact", "bloodbank.evt.>", y + 96),
        (2, 1, 2, "event", "durable delivery", "candystore-events", y + 176),
        (3, 2, 1, "lifecycle", "completed", "bloodbank.rpy.>", y + 256),
    ]
    for n, a, b, kind, words, subject, my in msgs:
        els += flow(kind, [(cx[a], my), (cx[b], my)], words)
        bx = cx[a] + 10 if b > a else cx[a] - 30
        badge = ellipse(bx, my - 34, 20, 20, stroke=INK_3, fill=SURFACE)
        els += [badge, label(badge, str(n), size=SIZE_LABEL, family=MONO, color=INK_2)]
        els.append(text((cx[a] + cx[b]) / 2, my + 10, subject, size=SIZE_LABEL,
                        family=MONO, color=INK_3, align="center"))
    return els


# --- 11 / 12. brick sinks -----------------------------------------------------------------------------


def reject_lane(x=0, y=0):
    cx, cw, ch = x + 80, 400, 148
    cy = y
    els = [caps(x, cy + 44, "Webhook"),
           arrow([(x, cy + 70), (cx - 2, cy + 70)], stroke=BRICK, width=2, head="bar"),
           rect(cx, cy, cw, ch, stroke=BRICK, fill=BRICK_SOFT, width=2)]
    els += glyph("broken", cx + 16, cy + 14, 20)
    els.append(caps(cx + 48, cy + 17, "Reject lane", color=BRICK))
    for i, line in enumerate(["unknown webhook_id", "bad HMAC", "missing route"]):
        els.append(text(cx + 20, cy + 50 + i * 20, line, size=SIZE_SMALL, family=MONO,
                        color=INK))
    els.append(poly([(cx + 20, cy + 114), (cx + cw - 20, cy + 114)], stroke=BRICK,
                    width=1, opacity=40))
    els.append(text(cx + 20, cy + 122, "Rejected at the edge. No event is published.",
                    size=SIZE_SMALL, color=BRICK))
    return els


def dead_letter(x=0, y=0):
    w, h = 288, 134
    els = [rect(x, y, w, h, stroke=BRICK, fill=BRICK_SOFT, width=2)]
    els += glyph("broken", x + 16, y + 16, 28)
    els.append(caps(x + 56, y + 16, "Parked after retries", color=BRICK))
    els.append(text(x + 56, y + 32, "Dead letter", size=SIZE_STATEMENT - 2, color=INK))
    els.append(poly([(x + 16, y + 68), (x + w - 16, y + 68)], stroke=BRICK, width=1,
                    opacity=40))
    els.append(text(x + 16, y + 80, "bloodbank.evt.repo.task.created", size=SIZE_DATA,
                    family=MONO, color=INK))
    els.append(text(x + 16, y + 102, "retries", size=SIZE_DATA, family=MONO, color=INK_3))
    els.append(text(x + 16 + 72, y + 102, "5 of 5", size=SIZE_DATA, family=MONO,
                    color=INK))
    return els


ITEMS = [
    ("Flow · Publish fact", flow_publish),
    ("Flow · Command intent", flow_command),
    ("Flow · Lifecycle reply", flow_lifecycle),
    ("Flow · Durable delivery", flow_durable),
    ("Flow · Recall / retain", flow_memory),
    ("Flow · Ticket webhook", flow_ticket),
    ("Flow legend", flow_legend),
    ("Event envelope", event_envelope),
    ("Command envelope", command_envelope),
    ("Lifecycle event pair", lifecycle_pair),
    ("Krebs lifecycle track", krebs_track),
    ("Ticket card", ticket_card),
    ("Authority boundary", authority_boundary),
    ("Facts / intent swimlanes", swimlanes),
    ("Sequence lifelines", sequence_lifelines),
    ("Reject lane", reject_lane),
    ("Dead letter", dead_letter),
]
