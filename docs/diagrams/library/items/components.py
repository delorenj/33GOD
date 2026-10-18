"""33GOD component cards: one brand.node() per component, each with its own
pictogram drawn from primitives inside the 40px PICTO box.

Pictogram family rules
- 40 x 40 box, 4px inset, strokes 2 (never thinner than 1.5), sharp joins.
- INK / INK_2 carry the form. At most ONE flow colour accent, and it names
  what the component is about (Bloodbank is the exception: its three lanes
  are the three streams, so it wears the three flow colours).
- Ochre is never used here except by the operator's own card.
- `PICTOGRAMS` maps item name -> fn(x, y, size) so the showcase can reuse
  every mark at its own size.
"""

from __future__ import annotations

import math

from brand import *  # noqa: F403


# --- pictogram toolkit -------------------------------------------------------


class _F:
    """A 40-unit frame at (x, y) scaled to `size`. All pictogram coordinates
    are written in the 40 grid and mapped here."""

    def __init__(self, x, y, size):
        self.x, self.y, self.u = x, y, size / 40
        self.w = max(1.5, 2 * self.u)  # the one family stroke

    def p(self, a, b):
        return (self.x + a * self.u, self.y + b * self.u)

    def line(self, pts, *, stroke=INK, width=None, style="solid", opacity=100,
             fill=TRANSPARENT, closed=None):
        return poly([self.p(*q) for q in pts], stroke=stroke, fill=fill,
                    width=width or self.w, style=style, opacity=opacity,
                    closed=closed)

    def rect(self, a, b, w, h, **kw):
        kw.setdefault("width", self.w)
        x, y = self.p(a, b)
        return rect(x, y, w * self.u, h * self.u, **kw)

    def circle(self, cx, cy, r, **kw):
        kw.setdefault("width", self.w)
        x, y = self.p(cx - r, cy - r)
        return ellipse(x, y, 2 * r * self.u, 2 * r * self.u, **kw)

    def diamond(self, cx, cy, r, **kw):
        kw.setdefault("width", self.w)
        x, y = self.p(cx - r, cy - r)
        return diamond(x, y, 2 * r * self.u, 2 * r * self.u, **kw)

    @staticmethod
    def arc(cx, cy, rx, ry, a0, a1, steps=20):
        """Elliptical arc points in grid units; 0deg east, clockwise."""
        out = []
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            out.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
        return out

    def head(self, tipx, tipy, dx, dy, size=6, color=INK):
        """Solid triangle arrowhead with its tip at (tipx, tipy) pointing
        along (dx, dy)."""
        n = math.hypot(dx, dy)
        dx, dy = dx / n, dy / n
        bx, by = tipx - dx * size, tipy - dy * size
        nx, ny = -dy * size * 0.6, dx * size * 0.6
        return self.line([(tipx, tipy), (bx + nx, by + ny), (bx - nx, by - ny)],
                         stroke=color, fill=color, width=1, closed=True)


# --- pictograms ----------------------------------------------------------------


def pic_bloodbank(x, y, size):
    """A bus rail feeding three lanes: event (solid), command (dashed),
    reply (ends in a dot)."""
    f = _F(x, y, size)
    els = [f.line([(5, 5), (5, 35)], stroke=INK)]
    els += [f.line([(5, 10), (30, 10)], stroke=SLATE),
            f.head(36, 10, 1, 0, 6.5, SLATE)]
    els += [f.line([(5, 20), (31, 20)], stroke=CLAY, style="dashed"),
            f.head(36, 20, 1, 0, 6.5, CLAY)]
    els += [f.line([(5, 30), (30, 30)], stroke=TEAL),
            f.circle(33.5, 30, 2.75, stroke=TEAL, fill=TEAL, width=1)]
    return els


def pic_candystore(x, y, size):
    """A cylinder cut into strata; one stratum carries an event row."""
    f = _F(x, y, size)
    els = [f.line([(6, 9), (6, 31)]), f.line([(34, 9), (34, 31)])]
    els.append(f.line(f.arc(20, 31, 14, 4.5, 0, 180)))
    els.append(f.line(f.arc(20, 24, 14, 4.5, 0, 180), stroke=INK_2, width=f.w * 0.75))
    els.append(f.line(f.arc(20, 17, 14, 4.5, 0, 180), stroke=INK_2, width=f.w * 0.75))
    ex, ey = f.p(6, 4.5)
    els.append(ellipse(ex, ey, 28 * f.u, 9 * f.u, stroke=INK, fill=SURFACE, width=f.w))
    els.append(f.line([(14, 18.5), (26, 18.5)], stroke=SLATE))
    return els


def pic_holocene(x, y, size):
    """A window at night: three dark panes, one pane lit and working."""
    f = _F(x, y, size)
    els = [f.rect(4, 4, 32, 32, stroke=INK, width=f.w)]
    els.append(f.line([(20, 4), (20, 36)]))
    els.append(f.line([(4, 20), (36, 20)]))
    for px, py in ((7, 7), (23, 7), (7, 23)):
        els.append(f.rect(px, py, 10, 10, stroke=INK_2, fill=INK_2, width=1))
    gx, gy = f.p(22, 22)
    els += glyph("working", gx, gy, 12 * f.u)
    return els


def pic_krebs(x, y, size):
    """A state ring: eight stations on a track, one in progress."""
    f = _F(x, y, size)
    els = [f.circle(20, 20, 14, stroke=INK_2, width=f.w * 0.75)]
    for k in range(8):
        a = math.radians(-90 + 45 * k)
        cx, cy = 20 + 14 * math.cos(a), 20 + 14 * math.sin(a)
        if k == 3:
            els.append(f.circle(cx, cy, 3.6, stroke=SAND, fill=SAND, width=1))
        else:
            els.append(f.circle(cx, cy, 3.2, stroke=INK, fill=SURFACE, width=f.w))
    return els


def pic_pjangler(x, y, size):
    """A project folder with a provisioning plus."""
    f = _F(x, y, size)
    els = [f.line([(4, 33), (4, 8), (15, 8), (19, 13), (36, 13), (36, 33)], closed=True)]
    els.append(f.line([(20, 19), (20, 29)], stroke=LICHEN))
    els.append(f.line([(15, 24), (25, 24)], stroke=LICHEN))
    return els


def pic_flume(x, y, size):
    """An org tree: one lead, three reports, one seat still to be hired."""
    f = _F(x, y, size)
    els = [f.rect(14, 4, 12, 8, stroke=INK, fill=INK, width=1)]
    els.append(f.line([(20, 12), (20, 18)], stroke=INK_2))
    els.append(f.line([(8, 24), (8, 18), (32, 18), (32, 24)], stroke=INK_2))
    els.append(f.line([(20, 18), (20, 24)], stroke=INK_2))
    els.append(f.rect(3.5, 24, 9, 10, stroke=INK))
    els.append(f.rect(15.5, 24, 9, 10, stroke=INK))
    els.append(f.rect(27.5, 24, 9, 10, stroke=INK, style="dashed"))
    return els


def pic_momo(x, y, size):
    """A compass: the needle points at the next action (command clay)."""
    f = _F(x, y, size)
    els = [f.circle(20, 20, 16, stroke=INK)]
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        els.append(f.line([(20 + 16 * dx, 20 + 16 * dy), (20 + 12.5 * dx, 20 + 12.5 * dy)],
                          stroke=INK_2))
    a = math.radians(-45)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    tip = (20 + 11 * ux, 20 + 11 * uy)
    tail = (20 - 11 * ux, 20 - 11 * uy)
    l = (20 + 3.4 * nx, 20 + 3.4 * ny)
    r = (20 - 3.4 * nx, 20 - 3.4 * ny)
    els.append(f.line([tip, l, r], stroke=CLAY, fill=CLAY, width=1.5, closed=True))
    els.append(f.line([tail, l, r], stroke=INK_2, width=f.w * 0.75, closed=True))
    return els


def pic_hermes_gateway(x, y, size):
    """A funnel: many in, a validation bar across it, one command out."""
    f = _F(x, y, size)
    els = [f.line([(4, 7), (36, 7)]), f.line([(4, 7), (20, 24), (36, 7)])]
    els.append(f.line([(10.5, 14.5), (29.5, 14.5)], stroke=INK_2, width=f.w * 0.75))
    els.append(f.line([(20, 24), (20, 29.5)], stroke=CLAY, style="solid"))
    els.append(f.head(20, 36, 0, 1, 6.5, CLAY))
    return els


def pic_hermes_agent(x, y, size):
    """An employee bust with a teal lifecycle dot: it reports what it did."""
    f = _F(x, y, size)
    els = [f.circle(18, 14, 6.5, stroke=INK)]
    els.append(f.line(f.arc(18, 35, 13, 11, 180, 360)))
    els.append(f.line([(5, 35), (31, 35)]))
    els.append(f.circle(32, 8, 3.2, stroke=TEAL, fill=TEAL, width=1))
    return els


def pic_hindsight(x, y, size):
    """A memory dot with echoes that fade as they recede."""
    f = _F(x, y, size)
    els = [f.circle(9, 20, 3.5, stroke=PLUM, fill=PLUM, width=1)]
    for r, o in ((9, 100), (16, 62), (23, 32)):
        els.append(f.line(f.arc(9, 20, r, r, -52, 52, 14), stroke=INK_2, opacity=o))
    return els


def pic_hub(x, y, size):
    """A hub with three spokes, one per tool."""
    f = _F(x, y, size)
    els = []
    leaves = [(20, 5.5), (33, 28), (7, 28)]
    for lx, ly in leaves:
        d = math.hypot(lx - 20, ly - 20)
        ux, uy = (lx - 20) / d, (ly - 20) / d
        els.append(f.line([(20 + 5 * ux, 20 + 5 * uy), (lx - 4.4 * ux, ly - 4.4 * uy)],
                          stroke=INK_2))
    els.append(f.circle(20, 20, 4.5, stroke=INK, fill=INK, width=1))
    for lx, ly in leaves:
        els.append(f.rect(lx - 4, ly - 4, 8, 8, stroke=INK, fill=SURFACE))
    return els


def pic_skillex(x, y, size):
    """A shelf of skills with one pulled out for distribution."""
    f = _F(x, y, size)
    els = [f.line([(3, 35), (37, 35)], stroke=INK)]
    els.append(f.rect(5, 11, 8, 24, stroke=INK))
    els.append(f.rect(14, 16, 8, 19, stroke=INK))
    els.append(f.line([(7, 17), (11, 17)], stroke=INK_2, width=f.w * 0.75))
    els.append(f.line([(16, 22), (20, 22)], stroke=INK_2, width=f.w * 0.75))
    els.append(f.line([(24, 35), (31, 35), (37, 13), (30, 13)], stroke=LICHEN, closed=True))
    return els


def pic_heyma(x, y, size):
    """A voice waveform."""
    f = _F(x, y, size)
    heights = [6, 14, 24, 32, 24, 14, 6]
    els = []
    for i, h in enumerate(heights):
        cx = 6.5 + 4.5 * i
        els.append(f.line([(cx, 20 - h / 2), (cx, 20 + h / 2)], stroke=INK_2 if h < 30 else INK))
    return els


def pic_pilot(x, y, size):
    """A terminal prompt; the cursor is a ticket-sand underscore."""
    f = _F(x, y, size)
    els = [f.rect(3, 6, 34, 28, stroke=INK)]
    els.append(f.line([(10, 14), (17, 20), (10, 26)], stroke=INK))
    els.append(f.line([(21, 27), (30, 27)], stroke=SAND))
    return els


def pic_plane(x, y, size):
    """A ticket with a perforated stub."""
    f = _F(x, y, size)
    pts = [(3, 9), (37, 9), (37, 16)]
    pts += f.arc(37, 20, 4, 4, -90, -270, 8)
    pts += [(37, 31), (3, 31), (3, 24)]
    pts += f.arc(3, 20, 4, 4, 90, -90, 8)
    pts += [(3, 9)]
    els = [f.line(pts, stroke=INK_2)]
    els.append(f.line([(27, 12.5), (27, 27.5)], stroke=SAND, style="dashed"))
    els.append(f.line([(11, 16), (22, 16)], stroke=INK_2, width=f.w * 0.75))
    els.append(f.line([(11, 24), (18, 24)], stroke=INK_2, width=f.w * 0.75))
    return els


def pic_n8n(x, y, size):
    """Two inputs (raw body, signature) merge at a verify-and-route diamond;
    one fact leaves in slate."""
    f = _F(x, y, size)
    els = [f.line([(9.8, 12.6), (16.5, 19.4)], stroke=INK_2),
           f.line([(9.8, 27.4), (16.5, 20.6)], stroke=INK_2)]
    els.append(f.circle(7, 10, 3.6, stroke=INK_2))
    els.append(f.circle(7, 30, 3.6, stroke=INK_2))
    els.append(f.diamond(22, 20, 6.5, stroke=INK_2))
    els.append(f.line([(28.5, 20), (31, 20)], stroke=SLATE))
    els.append(f.head(37, 20, 1, 0, 6.5, SLATE))
    return els


def pic_github(x, y, size):
    """A branch merging back into main."""
    f = _F(x, y, size)
    branch = [(8, 29)] + [(8, 18)]
    branch += f.arc(13, 18, 5, 5, 180, 270, 8)
    branch += f.arc(27, 18, 5, 5, 270, 360, 8)
    branch += [(32, 18), (32, 29)]
    els = [f.line(branch, stroke=INK_2)]
    els.append(f.line([(11.2, 30), (16.8, 30)], stroke=INK_2))
    els.append(f.line([(23.2, 30), (28.8, 30)], stroke=INK_2))
    for cx, cy in ((8, 30), (20, 30), (32, 30), (20, 13)):
        els.append(f.circle(cx, cy, 3.2, stroke=INK, fill=SURFACE))
    return els


def pic_toaster(x, y, size):
    """A toaster popping a slice: a signal that is gone once seen."""
    f = _F(x, y, size)
    els = [f.rect(4, 22, 32, 12, stroke=INK_2)]
    els.append(f.line([(12, 28), (28, 28)], stroke=INK_2, width=f.w * 0.75))
    slice_ = [(12, 22), (12, 13)]
    slice_ += f.arc(16, 13, 4, 4, 180, 360, 8)
    slice_ += f.arc(24, 13, 4, 4, 180, 360, 8)
    slice_ += [(28, 22)]
    els.append(f.line(slice_, stroke=INK_3, opacity=70))
    return els


def pic_operator(x, y, size):
    """The needs-you diamond, the only ochre pictogram."""
    return glyph("you", x, y, size)


def pic_worker(x, y, size):
    """Lucide git-branch, on the family stroke; the work item is a sand dot."""
    f = _F(x, y, size)
    s = 40 / 24

    def g(a, b):
        return (a * s, b * s)

    els = [f.line([g(6, 3), g(6, 15)], stroke=INK)]
    els.append(f.line([g(*q) for q in f.arc(9, 9, 9, 9, 0, 90, 12)], stroke=INK))
    els.append(f.circle(6 * s, 18 * s, 3 * s, stroke=INK, fill=SURFACE))
    els.append(f.circle(18 * s, 6 * s, 3 * s, stroke=SAND, fill=SAND))
    return els


PICTOGRAMS = {
    "Bloodbank": pic_bloodbank,
    "Candystore": pic_candystore,
    "Holocene": pic_holocene,
    "Krebs": pic_krebs,
    "PJangler": pic_pjangler,
    "Flume": pic_flume,
    "Momo": pic_momo,
    "Hermes gateway": pic_hermes_gateway,
    "Hermes agent": pic_hermes_agent,
    "Hindsight": pic_hindsight,
    "Pipeline MCP Hub": pic_hub,
    "Skillex": pic_skillex,
    "HeyMa": pic_heyma,
    "Pilot": pic_pilot,
    "External · Plane": pic_plane,
    "External · n8n": pic_n8n,
    "External · GitHub": pic_github,
    "External · Event toaster": pic_toaster,
    "Operator · You": pic_operator,
    "Worker in worktree": pic_worker,
}


# --- cards -----------------------------------------------------------------------


def bloodbank(x=0, y=0):
    return node(x, y, "Bloodbank", "Event bus",
                "bloodbank.evt.>\nbloodbank.cmd.>\nbloodbank.rpy.>",
                picto=pic_bloodbank)


def candystore(x=0, y=0):
    return node(x, y, "Candystore", "Event store",
                "PostgreSQL\ncandystore-events", picto=pic_candystore)


def holocene(x=0, y=0):
    return node(x, y, "Holocene", "Mission control",
                "SSE · /hq · Holocene Auto", picto=pic_holocene)


def krebs(x=0, y=0):
    return node(x, y, "Krebs", "Lifecycle engine",
                "lifecycle.v1\none state machine", picto=pic_krebs)


def pjangler(x=0, y=0):
    return node(x, y, "PJangler", "Provisioning", "pjangler init", picto=pic_pjangler)


def flume(x=0, y=0):
    return node(x, y, "Flume", "Workforce", "flume hire pm", picto=pic_flume)


def momo(x=0, y=0):
    return node(x, y, "Momo", "PM orchestrator", "roadmap · next action",
                picto=pic_momo)


def hermes_gateway(x=0, y=0):
    return node(x, y, "Hermes gateway", "Command gateway",
                "validate → route →\njournal → dispatch", picto=pic_hermes_gateway)


def hermes_agent(x=0, y=0):
    return node(x, y, "holocene-pm", "Hermes agent",
                "started · completed\nfailed · rejected", picto=pic_hermes_agent)


def hindsight(x=0, y=0):
    return node(x, y, "Hindsight", "Memory", "recall · retain · reflect",
                picto=pic_hindsight)


def pipeline_mcp_hub(x=0, y=0):
    return node(x, y, "Pipeline MCP Hub", "Tool hub",
                "list_domains\nlist_domain_tools\ncall_domain_tool", picto=pic_hub)


def skillex(x=0, y=0):
    return node(x, y, "Skillex", "Skill registry", ".agents/skills", picto=pic_skillex)


def heyma(x=0, y=0):
    return node(x, y, "HeyMa", "Voice", "WhisperLiveKit · ElevenLabs",
                picto=pic_heyma)


def pilot(x=0, y=0):
    return node(x, y, "Pilot", "Plane CLI", "px · pilot", picto=pic_pilot)


def external_plane(x=0, y=0):
    return node(x, y, "Plane", "Tickets", "plane.delo.sh", picto=pic_plane,
                kind="external")


def external_n8n(x=0, y=0):
    return node(x, y, "n8n", "Ingress", "Plane → Bloodbank · HMAC", picto=pic_n8n,
                kind="external")


def external_github(x=0, y=0):
    return node(x, y, "GitHub", "Source", "worktree → main", picto=pic_github,
                kind="external")


def external_event_toaster(x=0, y=0):
    return node(x, y, "Event toaster", "Ephemeral signal", "fire-and-forget",
                picto=pic_toaster, kind="external")


def operator_you(x=0, y=0):
    return node(x, y, "You", "Operator", "review gate · blocked", picto=pic_operator,
                kind="you")


def worker_in_worktree(x=0, y=0):
    return node(x, y, "Worker", "Implements a ticket", "HOLOC-8 · wt/holoc-8",
                picto=pic_worker)


ITEMS = [
    ("Bloodbank", bloodbank),
    ("Candystore", candystore),
    ("Holocene", holocene),
    ("Krebs", krebs),
    ("PJangler", pjangler),
    ("Flume", flume),
    ("Momo", momo),
    ("Hermes gateway", hermes_gateway),
    ("Hermes agent", hermes_agent),
    ("Hindsight", hindsight),
    ("Pipeline MCP Hub", pipeline_mcp_hub),
    ("Skillex", skillex),
    ("HeyMa", heyma),
    ("Pilot", pilot),
    ("External · Plane", external_plane),
    ("External · n8n", external_n8n),
    ("External · GitHub", external_github),
    ("External · Event toaster", external_event_toaster),
    ("Operator · You", operator_you),
    ("Worker in worktree", worker_in_worktree),
]
