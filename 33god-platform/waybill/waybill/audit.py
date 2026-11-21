"""waybill audit: did everything that happened become an event? (critic plan Step 6, SPEC section 2c)

The event gap audit as a command anyone can re-run. It reads the window's archive once (the query waybill's
own read, SPEC 2b), runs the ground-truth adapters (audit_sources.py) next to it, and writes ONE query-mode
waybill whose `gaps[]` and `findings[]` carry the audit, plus a top-level `audit` block with every row
(additive: v1 allows extra top-level keys). The terminal gets a table and a done-condition:

    done when: no row is still 'silent' (approved exceptions aside), nothing is lost in transit, the
    query's conservation holds, and every bus message in the window is proved by id.

On demand only: nothing here schedules itself.
"""
from __future__ import annotations

import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable

from . import audit_sources as A
from . import model as M
from . import query as Q
from .assemble import waybill_id
from .registry import Registry, load as load_cast

AUDIT_VERSION = 1
SEVERITY = {"lost-in-transit": "broken", "silent": "warn", "partial": "warn", "declared-never-seen": "info"}
EXTRA_COMPONENTS = {"git-hooks": ("git hooks", "external")}


class TeeReader(Q.PsqlReader):
    """The query reader, keeping what it read: the audit's adapters reuse the window's rows and dead letters,
    so Candystore is read once."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.got: list[Q.Row] = []
        self.dead: list[dict] = []

    def rows(self, spec, where, as_of):
        for r in super().rows(spec, where, as_of):
            self.got.append(r)
            yield r

    def dead_letters(self, spec, as_of):
        self.dead = super().dead_letters(spec, as_of)
        return self.dead


@dataclass
class AuditSpec:
    days: float = 1.0
    until: float | None = None          # epoch ms; default: the archive's now less settle
    settle_s: float = 120.0
    only: list[str] = field(default_factory=list)
    skip: list[str] = field(default_factory=list)
    profile: str = "public"
    tz: str = Q.DEFAULT_TZ

    def adapters(self) -> list[str]:
        ids = [i for i in A.ADAPTERS if (not self.only or i in self.only) and i not in self.skip]
        unknown = [i for i in [*self.only, *self.skip] if i not in A.ADAPTERS]
        if unknown:
            raise ValueError(f"unknown adapter(s) {', '.join(unknown)}; known: {', '.join(A.ADAPTERS)}")
        return ids


def window(now_ms: float, days: float, until: float | None = None, settle_s: float = 120.0) -> tuple[float, float]:
    """[until - days, until): until defaults to the archive's present less a settle, so late writers land."""
    u = min(until if until is not None else now_ms, now_ms) - settle_s * 1000.0
    return u - days * A.DAY, u


# ---------------------------------------------------------------- run the adapters

def run_adapters(ctx: A.Ctx, ids: list[str], progress: Callable[[str], None] | None = None,
                 adapters: dict | None = None, parallel: int = 4, timeout: float | None = None) -> tuple[list[A.Row], list[dict]]:
    """Every adapter in its own daemon thread with a timeout. Skip -> a 'skipped' source with the reason;
    any other error -> an 'error' source; a hang -> an 'error' source that says it timed out."""
    adapters = adapters or A.ADAPTERS
    say = progress or (lambda s: None)
    out: dict[str, tuple[list[A.Row], dict]] = {}
    gate = threading.Semaphore(parallel)

    def one(i: str) -> None:
        fn, kind, full, public = adapters[i]
        loc = ctx.loc(full, public)
        with gate:
            t0 = time.monotonic()
            try:
                rows = fn(ctx)
                src = {"id": f"audit:{i}", "kind": kind, "locator": loc, "status": "ok" if rows else "empty",
                       "items": len(rows), "ms": 0.0, "error": None}
            except A.Skip as exc:
                rows, src = [], {"id": f"audit:{i}", "kind": kind, "locator": loc, "status": "skipped", "items": 0,
                                 "ms": 0.0, "error": str(exc)}
            except Exception as exc:  # noqa: BLE001 -- one source failing never sinks the audit
                rows, src = [], {"id": f"audit:{i}", "kind": kind, "locator": loc, "status": "error", "items": 0,
                                 "ms": 0.0, "error": f"{type(exc).__name__}: {str(exc)[:300]}"}
            src["ms"] = round((time.monotonic() - t0) * 1000.0, 1)
            out[i] = (rows, src)
            say(f"  audit {i:<12} {src['status']:<8} {len(rows):>3} row(s) {src['ms']:>9.0f} ms"
                + (f"  ({src['error']})" if src["error"] else ""))

    threads = {}
    for i in ids:
        th = threading.Thread(target=one, args=(i,), name=f"audit-{i}", daemon=True)
        th.start()
        threads[i] = th
    t_start = time.monotonic()
    for i, th in threads.items():
        limit = timeout if timeout is not None else (
            A.TIMEOUTS.get(i, 240.0) + (240.0 * ctx.days if i == "bus" else 60.0 * max(0.0, ctx.days - 1)) + parallel * 60.0)
        th.join(max(0.05, limit - (time.monotonic() - t_start)))
        if i not in out:
            fn, kind, full, public = adapters[i]
            out[i] = ([], {"id": f"audit:{i}", "kind": kind, "locator": ctx.loc(full, public), "status": "error", "items": 0,
                           "ms": round((time.monotonic() - t_start) * 1000.0, 1), "error": f"timed out after {limit:.0f} s"})
            say(f"  audit {i:<12} timed out")
    rows = [r for i in ids for r in out[i][0]]
    return rows, [out[i][1] for i in ids]


# ---------------------------------------------------------------- the done-condition

def done_condition(rows: list[A.Row], wb_stats: dict, sources: list[dict]) -> dict[str, Any]:
    silent = [r for r in rows if r.verdict == "silent" and not r.exempt]
    lost = [r for r in rows if r.verdict == "lost-in-transit" and not r.exempt]
    bus = [r for r in rows if r.source == "bus" and r.thing.startswith(A.EVENTS_STREAM)]
    bus_missing = sum(int(((r.detail or {}).get("subjects") and sum(s["missing"] for s in r.detail["subjects"].values())) or 0)
                      for r in bus)
    skipped = [s for s in sources if s["status"] in ("skipped", "error")]
    cons = bool(wb_stats.get("conservation_ok"))
    proven = bool(bus) and bus_missing == 0
    return {"silent": len(silent), "lost": len(lost), "skipped_sources": len(skipped), "conservation_ok": cons,
            "bus_proven": proven, "bus_missing": bus_missing,
            "done": not silent and not lost and cons and proven and not skipped,
            "silent_rows": [r.thing for r in silent]}


# ---------------------------------------------------------------- merge into the waybill

def _label(since: float, until: float, tz: str, days: float) -> tuple[str, str]:
    a, b = Q._hm(since, tz), Q._hm(until, tz)
    span = "the last day" if abs(days - 1) < 1e-9 else f"the last {days:g} days"
    return f"audit · {span} · {Q._dm(since, tz)} {a} to {Q._dm(until, tz)} {b}", f"in {span}, {a} to {b}"


def merge(wb: dict, rows: list[A.Row], sources: list[dict], spec: AuditSpec, since: float, until: float,
          registry: Registry | None = None) -> dict:
    """The audit, folded into the query waybill under the same contract (SPEC 2b, additive)."""
    reg = registry
    label, when = _label(since, until, spec.tz, spec.days)
    done = done_condition(rows, wb.get("stats") or {}, sources)
    qid = wb["origin"]["session_id"]
    wb["id"] = waybill_id(since, qid, "audit")
    wb["title"] = f"waybill audit · {label.split(' · ', 1)[1]}"
    text = f"You asked the archive: did everything that happened {when}, become an event?"
    wb["prompt"] = {"text": text, "chars": len(text), "sha256": M.sha256(text), "truncated": False}
    for s in wb.get("spans") or []:
        if s.get("id") == M.Ids.PROMPT:
            s["summary"] = text
    oq = wb["origin"].setdefault("query", {})
    oq["label"] = label
    oq["audit"] = {"days": spec.days, "adapters": [s["id"].split(":", 1)[1] for s in sources]}
    comps = wb.setdefault("components", {})
    for r in rows:
        if r.component not in comps:
            name, kind = EXTRA_COMPONENTS.get(r.component, (reg.name_of(r.component) if reg else r.component, "service"))
            comps[r.component] = {"id": r.component, "name": name, "kind": kind,
                                  "registry": bool(reg and reg.is_registry(r.component))}
    for r in rows:
        if r.verdict == "covered":
            continue
        tick = f" [{', '.join(r.tickets)}]" if r.tickets else ""
        sev = "info" if r.exempt else SEVERITY.get(r.verdict, "warn")
        wb["findings"].append({
            "severity": sev, "component": r.component,
            "title": f"{r.verdict}: {r.thing}{tick}",
            "detail": f"{r.bound}{_n(r.expected)} expected, {_n(r.archived)} archived. {r.evidence}"
                      + (f" Approved exception {r.exempt}." if r.exempt else ""),
            "evidence": [f"audit:{r.source}", *r.tickets]})
        if r.verdict in ("silent", "lost-in-transit") and not r.exempt:
            wb["gaps"].append({"component": r.component, "what": f"{r.thing}: {r.verdict}",
                               "why": f"{r.bound}{_n(r.expected)} expected, {_n(r.archived)} archived{tick}",
                               "severity": "broken" if r.verdict == "lost-in-transit" else "warn", "span": None})
    for s in sources:
        if s["status"] in ("skipped", "error"):
            wb["gaps"].append({"component": "waybill", "what": f"audit source {s['id'].split(':', 1)[1]} {s['status']}",
                               "why": s["error"] or s["status"], "severity": "info" if s["status"] == "skipped" else "warn",
                               "span": None})
    wb["sources"].extend(sources)
    v = Counter(r.verdict for r in rows)
    st = wb["stats"]
    st.update({"audit_rows": len(rows), "audit_covered": v["covered"], "audit_partial": v["partial"], "audit_silent": v["silent"],
               "audit_lost": v["lost-in-transit"], "audit_declared_never_seen": v["declared-never-seen"],
               "audit_exempt": sum(1 for r in rows if r.exempt), "audit_skipped_sources": done["skipped_sources"],
               "bus_proven": done["bus_proven"], "audit_done": done["done"],
               "findings": len(wb["findings"]), "gaps": len(wb["gaps"])})
    bus = next((r for r in rows if r.source == "bus" and r.thing.startswith(A.EVENTS_STREAM)), None)
    wb["audit"] = {"version": AUDIT_VERSION, "days": spec.days, "since": M.iso(since), "until": M.iso(until),
                   "rows": [r.as_dict() for r in rows if r.source != "bus" or r is not bus] + ([_bus_summary(bus)] if bus else []),
                   "bus": (bus.detail if bus else {}), "done": done,
                   "skipped": [{"source": s["id"].split(":", 1)[1], "status": s["status"], "reason": s["error"]}
                               for s in sources if s["status"] in ("skipped", "error")]}
    return wb


def _bus_summary(r: A.Row) -> dict:
    d = r.as_dict()
    d["detail"] = {k: v for k, v in (r.detail or {}).items() if k != "subjects"}
    return d


def _n(x: int | None) -> str:
    return "?" if x is None else f"{x:,}"


# ---------------------------------------------------------------- the whole run

def run(spec: AuditSpec, reader: TeeReader | None = None, registry: Registry | None = None,
        progress: Callable[[str], None] | None = None, adapters: dict | None = None, archive: A.Archive | None = None,
        manifests: dict[str, str] | None = None, holocene: bool = True) -> tuple[dict, list[A.Row]]:
    say = progress or (lambda s: None)
    ids = [i for i in spec.adapters() if adapters is None or i in adapters] if adapters else spec.adapters()
    reader = reader or TeeReader()
    reg = registry or load_cast()
    now = reader.now_ms()
    since, until = window(now, spec.days, spec.until, spec.settle_s)
    label, when = _label(since, until, spec.tz, spec.days)
    qs = Q.QuerySpec(since=since, until=until, clock="time", filters={}, label=label, when=when, tz=spec.tz,
                     profile=spec.profile, include_dead_letters=True)
    say(f"waybill audit: {M.iso(since)} .. {M.iso(until)} ({spec.days:g} day(s)), adapters: {', '.join(ids)}")
    wb = Q.run(qs, reader, reg, manifests=manifests, holocene=holocene, progress=say)
    ctx = A.Ctx(since=since, until=until, registry=reg, archive=archive or A.Archive(), rows=reader.got, dead=reader.dead,
                public=spec.profile == "public")
    rows, sources = run_adapters(ctx, ids, say, adapters)
    return merge(wb, rows, sources, spec, since, until, reg), rows


# ---------------------------------------------------------------- the terminal

def table(rows: list[A.Row], width: int = 64) -> list[str]:
    out = [f"{'source':<12} {'thing':<{width}} {'expected':>10} {'archived':>10}  {'verdict':<20} tickets"]
    out.append("-" * len(out[0]))
    for r in rows:
        thing = r.thing if len(r.thing) <= width else r.thing[: width - 1] + "…"
        verdict = r.verdict + (" (exempt)" if r.exempt else "")
        out.append(f"{r.source:<12} {thing:<{width}} {r.bound + _n(r.expected):>10} {_n(r.archived):>10}  {verdict:<20} "
                   f"{', '.join(r.tickets)}")
        out.append(f"{'':<12}   {r.evidence}")
    return out


def done_lines(done: dict) -> list[str]:
    s = "DONE" if done["done"] else "NOT DONE"
    return [f"done-condition: {s} · silent rows {done['silent']} · lost in transit {done['lost']} · "
            f"conservation {'ok' if done['conservation_ok'] else 'BROKEN'} · bus {'proven by id' if done['bus_proven'] else 'NOT proven'}"
            f" ({done['bus_missing']} unexplained) · skipped sources {done['skipped_sources']}"]
