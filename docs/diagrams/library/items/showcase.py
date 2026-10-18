"""Composed example diagrams, built only from library items.

SCENES is a list of (filename, builder) pairs. Each builder returns a list of
chunks; every chunk is the element list of one placed item, so build.py
finalizes and groups each on its own. Nothing here draws a node or a
connector by hand: nodes come from items.components, structure and legends
from items.flows and items.brand_signals, connectors from brand.flow().

    33god-pipeline.excalidraw  the platform-context event journey
    33god-preview.excalidraw   a curated sheet; rendered to dist/33god.png
"""

from __future__ import annotations

from brand import *  # noqa: F403
from items import brand_signals as bs
from items import components as cp
from items import flows as fl

GAP = 4  # air between a connector tip and a node edge


class _Box:
    """Geometry of one placed node, read back from the card rectangle that
    every brand.node() puts first in its element list."""

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.cx, self.cy = x + w / 2, y + h / 2
        self.l, self.r, self.t, self.b = x, x + w, y, y + h


def _place(builder, x, cy):
    """Place a component card with its left edge at x and centre line at cy."""
    h = builder(0, 0)[0]["height"]
    top = cy - h / 2
    els = builder(x, top)
    card = els[0]
    return els, _Box(card["x"], card["y"], card["width"], card["height"])


def _words(kind, x, y, s, align="center"):
    """Mono words for a connector that bends, in the flow colour."""
    return text(x, y, s, size=SIZE_DATA, family=MONO, color=FLOW[kind], align=align)


# --- the platform-context event journey ----------------------------------------


def build_pipeline():
    chunks = []
    X = [264 + i * 392 for i in range(5)]  # five columns, 152px between cards
    SW, SH, LANE = X[-1] + cp.NODE_W + 32, 810, 380
    SY = 176  # swimlane top
    FA, B1, B2 = 215, 500, 712  # centre lines, relative to the swimlane

    chunks.append(bs.title_block(0, 0))
    chunks.append(bs.source_strip(SW - 872, 20))
    chunks.append(fl.swimlanes(0, SY, w=SW, h=SH, lane=LANE, arrows=False))

    def put(builder, col_x, cy):
        els, box = _place(builder, col_x, SY + cy)
        chunks.append(els)
        return box

    # facts lane
    plane = put(cp.external_plane, X[0], FA)
    n8n = put(cp.external_n8n, X[1], FA)
    bank = put(cp.bloodbank, X[2], FA)
    store = put(cp.candystore, X[3], FA)
    holo = put(cp.holocene, X[4], FA)
    toast = put(cp.external_event_toaster, X[3], 75)
    # intent lane
    you = put(cp.operator_you, X[0], B1)
    momo = put(cp.momo, X[1], B1)
    gate = put(cp.hermes_gateway, X[3], B1)
    agent = put(cp.hermes_agent, X[4], B1)
    mem = put(cp.hindsight, X[4], B2)

    def straight(kind, a, b, words):
        chunks.append(flow(kind, [(a.r + GAP, a.cy), (b.l - GAP, b.cy)], words))

    # facts: Plane -> n8n -> Bloodbank -> Candystore -> Holocene
    straight("ticket", plane, n8n, "signed webhook")
    straight("event", n8n, bank, "canonical fact")
    straight("event", bank, store, "durable")
    straight("event", store, holo, "read model")
    # facts: Bloodbank -> Event toaster
    tx = bank.cx
    chunks.append(flow("event", [(tx, bank.t - GAP), (tx, toast.cy), (toast.l - GAP, toast.cy)]))
    chunks.append([_words("event", (tx + toast.l) / 2, toast.cy - 22, "ephemeral signal")])

    # intent: Operator -> Momo
    straight("command", you, momo, "directs")
    # intent: Momo -> Bloodbank commands (enters the bus from below)
    mx = bank.x + 48
    chunks.append(flow("command", [(momo.r + GAP, B1 + SY), (mx, B1 + SY), (mx, bank.b + GAP)]))
    chunks.append([_words("command", (momo.r + mx) / 2, B1 + SY - 22, "bloodbank.cmd.>")])
    # intent: Bloodbank -> Hermes gateway (durable pull)
    gx, gy = bank.x + 120, gate.cy - 30
    chunks.append(flow("command", [(gx, bank.b + GAP), (gx, gy), (gate.l - GAP, gy)]))
    chunks.append([_words("command", (gx + gate.l) / 2, gy - 22, "pull consumer")])
    # intent: gateway -> agent (registry-gated dispatch)
    straight("command", gate, agent, "dispatch")

    # lifecycle replies climb back to the bus; gateway lower, agent upper
    ly1, ly2 = SY + 330, SY + 310
    gx2, ax2 = gate.x + 60, agent.cx
    chunks.append(flow("lifecycle", [(gx2, gate.t - GAP), (gx2, ly1),
                                     (bank.x + 168, ly1), (bank.x + 168, bank.b + GAP)]))
    chunks.append(flow("lifecycle", [(ax2, agent.t - GAP), (ax2, ly2),
                                     (bank.x + 208, ly2), (bank.x + 208, bank.b + GAP)]))
    chunks.append([_words("lifecycle", (bank.x + 208 + ax2) / 2, ly2 - 22,
                          "started / completed / failed / rejected")])
    chunks.append([_words("lifecycle", (bank.x + 168 + gx2) / 2, ly1 + 8, "rejected")])

    # memory: agent <-> Hindsight (advisory)
    chunks.append(flow("memory", [(agent.cx, agent.b + GAP), (agent.cx, mem.t - GAP)], both=True))
    chunks.append([_words("memory", agent.cx + 12, (agent.b + mem.t) / 2 - 7, "recall / retain", "left")])

    # the operator and the gate waiting on them
    gate_row = bs.gate_row(X[0], SY + B2 - 36)
    chunks.append(gate_row)
    chunks.append([poly([(you.cx, you.b + 4), (you.cx, SY + B2 - 36 - 4)], stroke=OCHRE, width=2)])

    # legends and the authority boundary
    ly = SY + SH + 72
    chunks.append(fl.flow_legend(0, ly))
    chunks.append(bs.signal_legend(632, ly))
    chunks.append(fl.authority_boundary(632 + 620 + 72, ly))
    return chunks


# --- curated preview ---------------------------------------------------------------


def build_preview():
    ch = []
    ch.append(bs.lockup(0, 0))
    ch.append(bs.title_block(0, 92))
    ch.append(bs.gate_row(0, 252))
    ch.append(bs.agent_line(0, 352))
    ch.append(bs.reading(0, 448))
    ch.append(bs.census(330, 448))
    ch.append(bs.signal_legend(860, 0))
    # components
    cards = [cp.bloodbank, cp.candystore, cp.hermes_gateway, cp.hermes_agent, cp.operator_you]
    for i, b in enumerate(cards):
        ch.append(b(i * 310, 640))
    # flows
    ch.append(fl.flow_publish(0, 836))
    ch.append(fl.flow_command(340, 836))
    ch.append(fl.flow_lifecycle(720, 836))
    ch.append(fl.flow_durable(1160, 836))
    # templates
    ch.append(fl.krebs_track(0, 1040))
    ch.append(fl.ticket_card(1020, 1040))
    return ch


SCENES = [
    ("33god-pipeline.excalidraw", build_pipeline),
    ("33god-preview.excalidraw", build_preview),
]
