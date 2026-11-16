"""Terminal waterfall for a waybill, in the spirit of the DevTools Network panel.

render(wb, width=None, show_all=False, color=None) -> str
"""
from __future__ import annotations

import math
import os
import shutil
import sys
from collections import Counter, defaultdict
from typing import Any

GLYPH = {"ok": "✓", "skipped": "·", "failed": "✗", "timeout": "⏱", "pending": "…", "dropped": "⊘", "unknown": "?"}
SEV_GLYPH = {"broken": "✗", "warn": "!", "info": "·"}
KIND_COLOR = {
    "prompt": "1;97", "turn": "2", "hook": "33", "handler": "36", "context": "37", "memory": "96",
    "publish": "32", "consume": "92", "event": "32", "state": "90", "notify": "93", "llm": "35",
    "tool": "34", "file": "90", "group": "2;34",
}
STATUS_COLOR = {"ok": "32", "skipped": "2", "failed": "31", "timeout": "31", "pending": "33", "dropped": "31",
                "unknown": "2"}
SEV_COLOR = {"broken": "31", "warn": "33", "info": "2"}
TOOL_HOOKS = {"PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionRequest"}
SYNC_CH, ASYNC_CH, OPEN_CH, INSTANT_CH, GROUP_CH = "█", "▒", "┄", "◆", "░"
EVENT_GROUP_MIN = 3
FANOUT_MIN = 2      # usage / allowance events collapse into one row from this many on


class _Paint:
    def __init__(self, on: bool) -> None:
        self.on = on

    def __call__(self, text: str, code: str | None) -> str:
        if not self.on or not code or not text:
            return text
        return f"\x1b[{code}m{text}\x1b[0m"


def _fmt_ms(v: float | None) -> str:
    if v is None:
        return "–"
    a = abs(v)
    sign = "-" if v < 0 else ""
    if a < 1000:
        return f"{sign}{a:.0f}ms"
    if a < 60000:
        return f"{sign}{a / 1000:.2f}s" if a < 10000 else f"{sign}{a / 1000:.1f}s"
    m, s = divmod(a / 1000, 60)
    return f"{sign}{int(m)}m{int(s):02d}s"


def _fmt_delta(v: float) -> str:
    return ("+" if v >= 0 else "−") + _fmt_ms(abs(v))


def _fmt_tick(v: float) -> str:
    if v == 0:
        return "0"
    if abs(v) < 1000:
        return f"{v:.0f}ms"
    if abs(v) < 60000:
        s = v / 1000
        return f"{s:.0f}s" if s == int(s) else f"{s:.1f}s"
    m, s = divmod(v / 1000, 60)
    return f"{int(m)}m" if int(s) == 0 else f"{int(m)}m{int(s):02d}"


def _fit(s: str, n: int) -> str:
    if n <= 0:
        return ""
    if len(s) <= n:
        return s + " " * (n - len(s))
    return s[: max(0, n - 1)] + "…"


def _trim(s: str, n: int) -> str:
    """Cut to n columns with an ellipsis, no padding."""
    return s if len(s) <= n else s[: max(0, n - 1)] + "…"


def _pack(parts: list[str], width: int, sep: str = " · ") -> list[str]:
    """Join header parts with sep, wrapping onto more lines instead of cutting them off."""
    lines: list[str] = []
    cur = ""
    for part in parts:
        cand = part if not cur else cur + sep + part
        if len(cand) <= width or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = part
    if cur:
        lines.append(cur)
    return [_trim(ln, width) for ln in lines]


def _native(s: dict) -> str | None:
    a = s.get("attrs") or {}
    for k in ("native", "hook", "hook_event"):
        if isinstance(a.get(k), str):
            return a[k]
    return s.get("name")


def _toolish(s: dict) -> bool:
    k = s.get("kind")
    if k == "tool":
        return True
    if k == "hook":
        return _native(s) in TOOL_HOOKS
    if k in ("llm", "prompt", "turn", "context"):
        return False
    if (s.get("refs") or {}).get("tool_use_id"):
        return True
    if k == "state" and (s.get("attrs") or {}).get("reason") in ("tool_req", "tool_done"):
        return True
    if k == "publish" and str(s.get("name") or "").startswith(("agent.tool.", "tool.")):
        return True
    return False


def _fmt_int(n: float | int | None) -> str:
    if n is None:
        return "?"
    n = float(n)
    if n >= 1e6:
        return f"{n / 1e6:.1f}M"
    if n >= 1e4:
        return f"{n / 1e3:.0f}k"
    if n >= 1e3:
        return f"{n / 1e3:.1f}k"
    return f"{int(n)}"


class _Layout:
    def __init__(self, width: int, a: float, b: float) -> None:
        self.width = max(60, width)
        self.start_w, self.dur_w, self.comp_w = 8, 7, 14
        self.name_w = 38
        fixed = self.start_w + 1 + self.dur_w + 1 + 1 + 1 + self.comp_w + 1 + 1 + 1 + 1   # ... name ' │' bar '│'
        self.bar_w = self.width - fixed - self.name_w
        if self.bar_w < 24:
            self.name_w = max(18, self.name_w - (24 - self.bar_w))
            self.comp_w = 12 if self.bar_w < 24 else self.comp_w
            fixed = self.start_w + 1 + self.dur_w + 1 + 1 + 1 + self.comp_w + 1 + 1 + 1 + 1   # ... name ' │' bar '│'
            self.bar_w = max(10, self.width - fixed - self.name_w)
        self.a, self.b = a, (b if b > a else a + 1.0)
        self.left_w = self.start_w + 1 + self.dur_w + 1 + 1 + 1 + self.comp_w + 1

    def col(self, t: float) -> int:
        x = (t - self.a) / (self.b - self.a) * (self.bar_w - 1)
        return min(self.bar_w - 1, max(0, int(round(x))))


def _bar(lay: _Layout, t0: float | None, t1: float | None, ch: str, open_end: bool = False) -> list[str]:
    cells = [" "] * lay.bar_w
    if t0 is None:
        return cells
    c0 = lay.col(t0)
    if t1 is None:
        if open_end:
            for i in range(c0, lay.bar_w):
                cells[i] = OPEN_CH
            cells[c0] = "▌"
        else:
            cells[c0] = INSTANT_CH
        return cells
    c1 = max(c0, lay.col(t1))
    for i in range(c0, c1 + 1):
        cells[i] = ch
    return cells


def _axis(lay: _Layout) -> str:
    span = lay.b - lay.a
    target = span / max(1, lay.bar_w / 12)
    mag = 10 ** math.floor(math.log10(max(target, 1e-3)))
    step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= target)
    cells = [" "] * lay.bar_w
    t = math.ceil(lay.a / step) * step
    last_end = -2
    while t <= lay.b + 1e-9:
        c = lay.col(t)
        label = _fmt_tick(t)
        if c > last_end + 1 and c + len(label) <= lay.bar_w:
            for i, chx in enumerate(label):
                cells[c + i] = chx
            last_end = c + len(label)
        t += step
    return "".join(cells)


def _bounds(wb: dict) -> tuple[float, float]:
    lo, hi = 0.0, float((wb.get("clock") or {}).get("duration_ms") or 0.0)
    for s in wb.get("spans") or []:
        for k in ("t0", "t1"):
            v = s.get(k)
            if isinstance(v, (int, float)):
                lo, hi = min(lo, v), max(hi, v)
    for e in wb.get("events") or []:
        for k in ("t", "stored", "archived"):
            v = e.get(k)
            if isinstance(v, (int, float)):
                lo, hi = min(lo, v), max(hi, v)
    return lo, hi


def _count_desc(sid: str, kids: dict[str, list[dict]], seen: set | None = None) -> int:
    seen = seen if seen is not None else set()
    n = 0
    for c in kids.get(sid, []):
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        n += 1 + _count_desc(c["id"], kids, seen)
    return n


def _collect_desc(sid: str, kids: dict[str, list[dict]], out: list[dict], seen: set) -> None:
    for c in kids.get(sid, []):
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        out.append(c)
        _collect_desc(c["id"], kids, out, seen)


def _is_fanout_noise(e: dict) -> bool:
    """llm.usage.recorded and the allowance events fan out once per model call: one row beats ten."""
    t = str(e.get("type") or "")
    return "llm.usage" in t or "allowance" in t


def _type_label(e: dict) -> str:
    """The bloodbank type, plus the type the bus stored it under when that differs (Dapr: com.dapr.event.sent)."""
    t = (e.get("type") or "").replace("bloodbank.", "")
    if e.get("stored_type") and e["stored_type"] != e.get("type"):
        t += f" (stored as {e['stored_type']})"
    return t


def _fanout_text(e: dict, wb_comp: dict, limit_names: int = 6) -> tuple[str, list[tuple[str, str]]]:
    bits = []
    if e.get("observed_on_bus") is False:
        bits.append("never seen on the bus")
    if e.get("seq") is not None:
        bits.append(f"seq {e['seq']}")
    t = e.get("t")
    if e.get("stored") is not None and t is not None:
        bits.append(f"stored {_fmt_delta(e['stored'] - t)}")
    if e.get("archived") is not None and t is not None:
        bits.append(f"archived {_fmt_delta(e['archived'] - t)}")
    cons = e.get("consumers") or []
    obs = [c for c in cons if c.get("evidence") == "observed"]
    inf = [c for c in cons if c.get("evidence") != "observed"]
    parts: list[tuple[str, str]] = []
    for c in obs:
        oc = c.get("outcome") or "unknown"
        parts.append((f"●{c.get('name')} {oc}", "31" if oc in ("dropped", "rate-limited") else "32"))
    if inf:
        shown = inf[:limit_names]
        more = len(inf) - len(shown)
        parts.append(("inferred: " + ", ".join(f"○{c.get('name')}" for c in shown) + (f" (+{more})" if more else ""), "2"))
    if not cons:
        parts.append(("no consumer known", "2"))
    head = f"↳ {_type_label(e)}" + (" · " + " · ".join(bits) if bits else "")
    return head, parts


def render(wb: dict, width: int | None = None, show_all: bool = False, color: bool | None = None) -> str:
    if color is None:
        color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    P = _Paint(bool(color))
    width = width or shutil.get_terminal_size((160, 40)).columns
    lo, hi = _bounds(wb)
    lay = _Layout(width, lo, hi)
    out: list[str] = []
    st = wb.get("stats") or {}
    org = wb.get("origin") or {}
    clk = wb.get("clock") or {}
    model = org.get("model") or {}

    # ---- header
    out.append(P(_trim(wb.get("title") or wb.get("id") or "waybill", width), "1"))
    l2 = [f"{org.get('cli')}/{org.get('surface')}", f"session {org.get('session_id')}"]
    if org.get("turn_index") is not None or org.get("turn_id"):
        l2.append(f"turn {org.get('turn_index') if org.get('turn_index') is not None else '?'}"
                  + (f" ({org['turn_id']})" if org.get("turn_id") else ""))
    if org.get("cwd"):
        home = os.path.expanduser("~")
        l2.append(f"cwd {str(org['cwd']).replace(home, '~')}")
    if org.get("project"):
        l2.append(f"project {org['project']}")
    out.extend(P(ln, "2") for ln in _pack(l2, width))
    l3 = []
    if model:
        l3.append(f"model {model.get('requested') or '?'} → {model.get('served') or '?'}")
    l3.append(f"t0 {clk.get('t0')}")
    l3.append(f"turn {_fmt_ms(clk.get('duration_ms'))}")
    l3.append(f"settle {_fmt_ms(clk.get('settle_ms'))}")
    l3.append(f"{wb.get('recorder', {}).get('mode', '?')}/{wb.get('recorder', {}).get('profile', '?')}")
    out.extend(P(ln, "2") for ln in _pack(l3, width))
    l4 = [f"{int(st.get('spans', 0))} spans", f"{int(st.get('events', 0))} events",
          f"{int(st.get('tools', 0))} tools", f"{int(st.get('llm_calls', 0))} llm calls",
          f"tokens {_fmt_int(st.get('tokens_in'))} in / {_fmt_int(st.get('tokens_out'))} out"]
    if st.get("sync_wait_ms") is not None:
        l4.append(f"prompt waited {_fmt_ms(st['sync_wait_ms'])} on hooks")
    l4.append(f"handlers {int(st.get('handlers_ok', 0))} ok/{int(st.get('handlers_skipped', 0))} skipped/"
              f"{int(st.get('handlers_failed', 0))} failed")
    l4.append(f"consumers {int(st.get('consumers_observed', 0))} observed/{int(st.get('consumers_inferred', 0))} inferred")
    out.extend(_pack(l4, width))
    out.append("")

    # ---- column header + axis
    hdr = (_fit("start", lay.start_w) + " " + _fit("dur", lay.dur_w) + " " + " " + " "
           + _fit("component", lay.comp_w) + " " + _fit("name", lay.name_w) + " ")
    out.append(P(hdr + "│" + _axis(lay) + "│", "2"))

    # ---- tree
    spans = wb.get("spans") or []
    byid = {s["id"]: s for s in spans}
    kids: dict[str, list[dict]] = defaultdict(list)
    roots: list[dict] = []
    for s in spans:
        p = s.get("parent")
        if p and p in byid and p != s["id"]:
            kids[p].append(s)
        else:
            roots.append(s)
    for k in kids:
        kids[k].sort(key=lambda s: (s.get("t0") or 0.0, s["id"]))
    ev_by_pub: dict[str, list[dict]] = defaultdict(list)
    loose: list[dict] = []
    # llm.usage.recorded / allowance fire once per model call: collapse each type into one 'N× type' row unless --all
    noisy: dict[str, list[dict]] = defaultdict(list)
    for e in wb.get("events") or []:
        if _is_fanout_noise(e):
            noisy[e.get("type") or "?"].append(e)
    collapsed: dict[str, list[dict]] = {} if show_all else {t: v for t, v in noisy.items() if len(v) >= FANOUT_MIN}
    for e in wb.get("events") or []:
        if (e.get("type") or "?") in collapsed:
            continue
        if e.get("publisher_span") in byid:
            ev_by_pub[e["publisher_span"]].append(e)
        else:
            loose.append(e)

    items: list[tuple[float, str, Any]] = [(s.get("t0") or 0.0, "span", s) for s in roots]
    items += [(min(e.get("t") or 0.0 for e in evs), "evgroup", evs) for evs in collapsed.values()]
    if show_all:
        items += [(e.get("t") or 0.0, "event", e) for e in loose]
    else:
        by_type: dict[str, list[dict]] = defaultdict(list)
        for e in loose:
            by_type[e.get("type") or "?"].append(e)
        for t, evs in by_type.items():
            if len(evs) >= EVENT_GROUP_MIN:
                items.append((min(e.get("t") or 0.0 for e in evs), "evgroup", evs))
            else:
                items += [(e.get("t") or 0.0, "event", e) for e in evs]
    def order(x: tuple) -> tuple:
        obj = x[2]
        sid = obj.get("id", "") if isinstance(obj, dict) else ""
        return (x[0], 0 if sid == "turn" else 1, 0 if x[1] == "span" else 1, sid)
    items.sort(key=order)

    def row(start: float | None, dur: float | None, status: str, comp: str, name: str, depth: int,
            cells: list[str], kind: str, dim: bool = False, note: str = "") -> str:
        g = GLYPH.get(status, "?")
        label = ("  " * depth) + name + (f" {note}" if note else "")
        line = _fmt_ms(start).rjust(lay.start_w) if start is not None else " " * lay.start_w
        line += " " + (_fmt_ms(dur).rjust(lay.dur_w) if dur is not None else " " * lay.dur_w)
        line += " " + P(g, STATUS_COLOR.get(status)) + " "
        line += P(_fit(comp, lay.comp_w), "2") + " "
        line += P(_fit(label, lay.name_w), "2" if dim else None) + " "
        bar = "".join(cells)
        line += P("│", "2") + P(bar, KIND_COLOR.get(kind)) + P("│", "2")
        return line

    def span_row(s: dict, depth: int, note: str = "") -> str:
        t0, t1 = s.get("t0"), s.get("t1")
        sync = bool(s.get("sync"))
        ch = SYNC_CH if sync else ASYNC_CH
        cells = _bar(lay, t0, t1, ch, open_end=(t1 is None and s.get("status") == "pending"))
        dur = (t1 - t0) if (t0 is not None and t1 is not None) else None
        name = s.get("name") or s["id"]
        if s.get("kind") == "hook":
            name = f"⧉ {name}"
        if s.get("reason") and s.get("status") != "ok":
            note = (f"[{s['reason']}] " + note).strip()
        return row(t0, dur, s.get("status") or "unknown", s.get("component") or "?", name, depth, cells,
                   s.get("kind") or "", dim=s.get("status") == "skipped", note=note)

    def fanout_rows(e: dict, depth: int) -> list[str]:
        head, parts = _fanout_text(e, wb.get("components") or {})
        pad = " " * lay.left_w + "  " * (depth + 1)
        avail = max(20, lay.width - len(pad))
        text = head + "  →  "
        plain = text + "  ".join(p for p, _ in parts)
        if len(plain) > avail:
            # wrap onto a second line rather than truncating the consumer list
            first = text
            rest = []
            for p, c in parts:
                if len(first) + len(p) + 2 <= avail and not rest:
                    first += p + "  "
                else:
                    rest.append((p, c))
            lines = [pad + P(_trim(first.rstrip(), avail), "2")]
            if rest:
                cont = "   " + "  ".join(p for p, _ in rest)
                lines.append(pad + P(_fit(cont, avail).rstrip(), "2"))
            return lines
        colored = P(text, "2") + "  ".join(P(p, c) for p, c in parts)
        return [pad + colored]

    def event_row(e: dict, depth: int) -> list[str]:
        cells = _bar(lay, e.get("t"), None, INSTANT_CH)
        for k, mark in (("stored", "▴"), ("archived", "▾")):
            if e.get(k) is not None:
                c = lay.col(e[k])
                if cells[c] == " ":
                    cells[c] = mark
        name = "◆ " + _type_label(e)
        lines = [row(e.get("t"), None, "ok", e.get("producer") or "bus", name, depth, cells, "event")]
        lines += fanout_rows(e, depth)
        return lines

    def group_row(evs: list[dict], depth: int) -> list[str]:
        ts = [e.get("t") or 0.0 for e in evs]
        cells = [" "] * lay.bar_w
        for t in ts:
            cells[lay.col(t)] = INSTANT_CH
        et = _type_label(evs[0])
        obs = sum(1 for e in evs for c in e.get("consumers") or [] if c.get("evidence") == "observed")
        seqs = [e["seq"] for e in evs if e.get("seq") is not None]
        note = f"seq {min(seqs)}…{max(seqs)}" if seqs else "no seq"
        return [row(min(ts), max(ts) - min(ts), "ok", evs[0].get("producer") or "bus",
                    f"◆ {len(evs)}× {et}", depth, cells, "event",
                    note=f"({note}, {obs} observed deliveries" + (", --all expands)" if _is_fanout_noise(evs[0]) else ")"))]

    def run_row(run: list[dict], depth: int) -> str:
        members: list[dict] = []
        seen: set = set()
        for s in run:
            if s["id"] not in seen:
                seen.add(s["id"])
                members.append(s)
                _collect_desc(s["id"], kids, members, seen)
        t0s = [m["t0"] for m in members if m.get("t0") is not None]
        t1s = [m.get("t1") if m.get("t1") is not None else m.get("t0") for m in members]
        t1s = [x for x in t1s if x is not None]
        a, b = (min(t0s) if t0s else None), (max(t1s) if t1s else None)
        tools = Counter(m.get("name") or "?" for m in members if m.get("kind") == "tool")
        hooks = sum(1 for m in members if m.get("kind") == "hook")
        failed = sum(1 for m in members if m.get("status") in ("failed", "timeout", "dropped"))
        bits = [f"{sum(tools.values())} tools " + " ".join(f"{n}×{c}" if c > 1 else n for n, c in tools.most_common(4))]
        if hooks:
            bits.append(f"{hooks} hooks")
        if failed:
            bits.append(f"{failed} failed")
        cells = _bar(lay, a, b, GROUP_CH)
        return row(a, (b - a) if a is not None and b is not None else None, "failed" if failed else "ok",
                   run[0].get("component") or "tools", "▸ " + " · ".join(bits), depth, cells, "group",
                   note=f"(+{len(members)} rows, --all)")

    def emit(sibs: list[tuple[float, str, Any]], depth: int, guard: set) -> None:
        i = 0
        while i < len(sibs):
            _, typ, obj = sibs[i]
            if typ == "span" and not show_all and _toolish(obj):
                j = i
                while j < len(sibs) and sibs[j][1] == "span" and _toolish(sibs[j][2]):
                    j += 1
                if j - i >= 2:
                    out.append(run_row([x[2] for x in sibs[i:j]], depth))
                    i = j
                    continue
            if typ == "span":
                s = obj
                if s["id"] in guard:
                    i += 1
                    continue
                guard.add(s["id"])
                children = kids.get(s["id"], [])
                hide = (not show_all) and _toolish(s) and children
                out.append(span_row(s, depth, note=(f"(+{_count_desc(s['id'], kids)} rows)" if hide else "")))
                for e in ev_by_pub.get(s["id"], []):
                    if not hide:
                        out.extend(fanout_rows(e, depth))
                if not hide and children:
                    emit([(c.get("t0") or 0.0, "span", c) for c in children], depth + 1, guard)
            elif typ == "event":
                out.extend(event_row(obj, depth))
            elif typ == "evgroup":
                out.extend(group_row(obj, depth))
            i += 1

    emit(items, 0, set())
    out.append("")

    # ---- findings, gaps, sources
    findings = wb.get("findings") or []
    if findings:
        out.append(P(f"Findings ({len(findings)})", "1"))
        order = {"broken": 0, "warn": 1, "info": 2}
        for f in sorted(findings, key=lambda f: order.get(f.get("severity"), 3)):
            sev = f.get("severity") or "info"
            out.append(f"  {P(SEV_GLYPH.get(sev, '·'), SEV_COLOR.get(sev))} {P(_fit(sev, 6), SEV_COLOR.get(sev))} "
                       f"{_fit(f.get('component') or '', 14)} {_trim(str(f.get('title')), max(20, lay.width - 26))}")
            if f.get("detail"):
                out.append(P(f"{' ' * 25}{_fit(f['detail'], max(20, lay.width - 25)).rstrip()}", "2"))
        out.append("")
    gaps = wb.get("gaps") or []
    if gaps:
        out.append(P(f"Gaps ({len(gaps)})", "1"))
        grouped: dict[tuple, list[dict]] = defaultdict(list)
        for g in gaps:
            grouped[(g.get("severity") or "info", g.get("component") or "", g.get("what") or "")].append(g)
        order = {"broken": 0, "warn": 1, "info": 2}
        for (sev, comp, what), gs in sorted(grouped.items(), key=lambda kv: (order.get(kv[0][0], 3), kv[0][1])):
            n = f" ×{len(gs)}" if len(gs) > 1 else ""
            out.append(f"  {P(SEV_GLYPH.get(sev, '·'), SEV_COLOR.get(sev))} {P(_fit(sev, 6), SEV_COLOR.get(sev))} "
                       f"{_fit(comp, 14)} {_fit(what + n, max(20, lay.width - 26)).rstrip()}")
            why = gs[0].get("why")
            if why:
                out.append(P(f"{' ' * 25}{_fit(why, max(20, lay.width - 25)).rstrip()}", "2"))
        out.append("")
    srcs = wb.get("sources") or []
    if srcs:
        out.append(P("Sources", "1"))
        for s in srcs:
            stt = s.get("status") or "?"
            c = {"ok": "32", "empty": "33", "error": "31", "skipped": "2"}.get(stt)
            line = (f"  {_fit(s.get('id') or '?', 18)} {P(_fit(stt, 7), c)} {str(s.get('items', 0)).rjust(5)} items "
                    f"{_fmt_ms(s.get('ms')).rjust(8)}  ")
            tail = s.get("error") or s.get("locator") or ""
            out.append(line + P(_fit(tail, max(10, lay.width - len(line))).rstrip(), "2"))
        out.append("")
    return "\n".join(out) + "\n"
