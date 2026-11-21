"""waybill command line: capture | record | show | publish | query | night | list (SPEC section 4)."""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable

from . import VERSION
from . import model as M
from .collectors import ALIASES, CLI_ONLY, REGISTRY

RECEIPTS = Path(os.environ.get("WAYBILL_RECEIPTS", str(Path.home() / ".local/state/33god/hook-hub/receipts.sqlite3")))
CANDYSTORE_HTTP = os.environ.get("WAYBILL_CANDYSTORE_URL", "http://127.0.0.1:8683")
DEFAULT_TIMEOUT_S = 25.0


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------- receipts helpers (read-only)

def receipts_query(sql: str, params: tuple = (), path: Path | None = None) -> list[tuple]:
    p = path or RECEIPTS
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=3)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def candystore_envelope(event_id: str, timeout: float = 2.0) -> dict | None:
    try:
        with urllib.request.urlopen(f"{CANDYSTORE_HTTP}/events/{event_id}/raw", timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def _publisher_event(invocation_id: str) -> str | None:
    rows = receipts_query("select event_id from executions where invocation_id=? and handler_id='bloodbank-publisher'",
                          (invocation_id,))
    return rows[0][0] if rows and rows[0][0] else None


# ---------------------------------------------------------------- window resolution

def fallback_window(session_id: str, cli: str | None = None, turn: int | None = None, latest: bool = False,
                    at: str | None = None, settle_ms: float = 15000.0) -> M.TurnWindow:
    """Receipts-only window, used when waybill.window is missing or broken. Coarser than window.py:
    turn N counts UserPromptSubmit receipts (about 4 days of retention), not the transcript."""
    if not session_id:
        last = receipts_query("select session_id from invocations where native='UserPromptSubmit' and session_id!=''"
                              + (" and cli=?" if cli else "") + " order by received_at desc limit 1",
                              (cli,) if cli else ())
        if not last:
            raise LookupError("no UserPromptSubmit receipt found")
        session_id = last[0][0]
    rows = receipts_query(
        "select invocation_id, cli, received_at from invocations where session_id=? and native='UserPromptSubmit'"
        + (" and cli=?" if cli else "") + " order by received_at", (session_id, cli) if cli else (session_id,))
    if not rows:
        raise LookupError(f"no UserPromptSubmit receipt for session {session_id} (receipts keep about 4 days)")
    idx = len(rows) - 1
    if turn is not None and not latest and not at:
        if not 1 <= turn <= len(rows):
            raise LookupError(f"session has {len(rows)} prompt receipt(s); turn {turn} is out of range")
        idx = turn - 1
    elif at:
        want = M.ms(at)
        if want is None:
            raise ValueError(f"--at {at!r} is not an ISO timestamp")
        before = [i for i, r in enumerate(rows) if (M.ms(r[2]) or 0) <= want + 1000]
        idx = before[-1] if before else 0
    inv, cli_, recv = rows[idx]
    t0 = M.ms(recv) or M.now_ms()
    nxt = M.ms(rows[idx + 1][2]) if idx + 1 < len(rows) else None
    stops = receipts_query(
        "select invocation_id, received_at from invocations where session_id=? and native in ('Stop','StopFailure')"
        " and received_at>=? order by received_at limit 1", (session_id, recv))
    stop_inv = turn_end = None
    if stops and (nxt is None or (M.ms(stops[0][1]) or 0) <= nxt):
        stop_inv, turn_end = stops[0][0], M.ms(stops[0][1])
    t_end = (turn_end + settle_ms) if turn_end else min(M.now_ms(), (nxt or M.now_ms()))
    w = M.TurnWindow(cli=cli_, surface="claude-code" if cli_ == "claude" else ("codex-cli" if cli_ == "codex" else cli_),
                     session_id=session_id, t0=t0, t_end=t_end, turn_end=turn_end, turn_index=idx + 1,
                     prompt_invocation_id=inv, stop_invocation_id=stop_inv, settle_ms=settle_ms)
    w.turn_source = "receipts"
    eid = _publisher_event(inv)
    env = candystore_envelope(eid) if eid else None
    data = (env or {}).get("data") if isinstance((env or {}).get("data"), dict) else {}
    w.prompt_text = data.get("prompt_text")
    w.turn_id = data.get("turn_id")
    w.cwd = data.get("working_directory") or data.get("cwd")
    return w


def resolve_window(session_id: str, cli: str | None = None, turn: int | None = None, latest: bool = False,
                   at: str | None = None, settle_ms: float = 15000.0) -> tuple[M.TurnWindow, str | None]:
    """(window, note). note is set when the receipts fallback was used."""
    try:
        W = importlib.import_module("waybill.window")
        resolve = getattr(W, "resolve")
    except Exception as exc:
        note = f"waybill.window unavailable ({type(exc).__name__}: {exc}); used the receipts fallback"
        return fallback_window(session_id, cli, turn, latest, at, settle_ms), note
    return resolve(session_id, cli, turn, latest, at, settle_ms), None


# ---------------------------------------------------------------- collector runner

def select_collectors(only: list[str] | None, skip: list[str] | None) -> list[str]:
    def expand(names: list[str]) -> set[str]:
        out: set[str] = set()
        for n in names:
            n = n.strip()
            if not n:
                continue
            out.update(ALIASES.get(n, [n.replace("-", "_")]))
        return out
    chosen = list(REGISTRY)
    if only:
        keep = expand(only)
        chosen = [c for c in chosen if c in keep] + sorted(k for k in keep if k not in REGISTRY)
    if skip:
        drop = expand(skip)
        chosen = [c for c in chosen if c not in drop]
    return chosen


def _error_fragment(name: str, err: str, t_ms: float, status: str = "error") -> M.Fragment:
    frag = M.Fragment(source=M.Source(id=name, kind="collector", locator=f"waybill.collectors.{name}",
                                      status=status, items=0, ms=round(t_ms, 1), error=err))
    if status == "error":
        frag.gaps.append(M.Gap(component=name, what=f"collector {name} produced nothing",
                               why=err, severity="warn"))
    return frag


def _timeout_fragment(name: str, partial: M.Fragment | None, limit: float) -> M.Fragment:
    """A collector hit the runner's deadline. Keep whatever it had parked in ctx.partials (a snapshot: the thread
    may still be appending) and say the data is partial; only a collector with nothing parked is an empty error."""
    msg = f"timed out after {limit:.0f} s"
    if partial is None:
        return _error_fragment(name, msg, limit * 1000.0)
    import copy
    src = copy.copy(partial.source)
    frag = M.Fragment(source=src)
    for attr in ("spans", "events", "links", "gaps", "findings"):
        setattr(frag, attr, list(getattr(partial, attr)))
    frag.components = dict(partial.components) if isinstance(partial.components, dict) else partial.components
    frag.facts = dict(partial.facts)
    frag.artifacts = dict(partial.artifacts)
    src.status = "ok" if (frag.spans or frag.events) else "error"   # the schema has no 'partial'; the gap says so
    src.error = f"{msg}; kept {len(frag.spans)} span(s) read before the deadline"
    src.ms = round(limit * 1000.0, 1)
    src.items = len(frag.spans)
    frag.gaps.append(M.Gap(component=name, what=f"collector {name} timed out",
                           why=f"{src.error}: later evidence from this source is missing", severity="warn"))
    return frag


def run_collectors(ctx: M.Ctx, names: list[str], progress: Callable[[str], None] | None = None,
                   timeout_s: float | None = None) -> list[M.Fragment]:
    """Run each collector in its own daemon thread with a deadline. Never raises."""
    limit = float(timeout_s if timeout_s is not None else ctx.timeout_s) + 5.0
    results: dict[str, M.Fragment] = {}
    started: dict[str, float] = {}
    threads: dict[str, threading.Thread] = {}

    def work(name: str) -> None:
        t = time.monotonic()
        try:
            mod = importlib.import_module(f"waybill.collectors.{name}")
            frag = mod.collect(ctx)
            if not isinstance(frag, M.Fragment):
                raise TypeError(f"collect() returned {type(frag).__name__}, not Fragment")
            if not frag.source.ms:
                frag.source.ms = round((time.monotonic() - t) * 1000.0, 1)
            results[name] = frag
        except ModuleNotFoundError as exc:
            missing = exc.name or ""
            msg = (f"module waybill.collectors.{name} is not installed" if missing.endswith(name)
                   else f"{type(exc).__name__}: {exc}")
            results[name] = _error_fragment(name, msg, (time.monotonic() - t) * 1000.0)
        except Exception as exc:
            results[name] = _error_fragment(name, f"{type(exc).__name__}: {exc}", (time.monotonic() - t) * 1000.0)

    for name in names:
        want = CLI_ONLY.get(name)
        if want and ctx.window.cli and ctx.window.cli != want:
            results[name] = _error_fragment(name, f"only applies to {want} sessions", 0.0, status="skipped")
            continue
        started[name] = time.monotonic()
        th = threading.Thread(target=work, args=(name,), name=f"waybill-{name}", daemon=True)
        threads[name] = th
        th.start()
    deadline = time.monotonic() + limit
    for name, th in threads.items():
        th.join(max(0.0, deadline - time.monotonic()))
        if th.is_alive():
            results[name] = _timeout_fragment(name, ctx.partials.get(name), limit)
        if progress:
            f = results.get(name)
            if f is not None:
                s = f.source
                progress(f"  {name:<18} {s.status:<7} {s.items:>5} items {s.ms:>8.0f} ms"
                         + (f"  {s.error}" if s.error else ""))
    return [results[n] for n in names if n in results]


def run_pipeline(window: M.TurnWindow, *, profile: str = "full", deep: bool = False, live: dict | None = None,
                 only: list[str] | None = None, skip: list[str] | None = None, mode: str = "capture",
                 argv: list[str] | None = None, extra_fragments: list[M.Fragment] | None = None,
                 timeout_s: float = DEFAULT_TIMEOUT_S, note: str | None = None,
                 progress: Callable[[str], None] | None = None) -> dict:
    from .assemble import assemble
    ctx = M.Ctx(window=window, profile=profile, deep=deep, live=live or {}, timeout_s=timeout_s)
    frags = run_collectors(ctx, select_collectors(only, skip), progress=progress, timeout_s=timeout_s)
    frags.extend(extra_fragments or [])
    if note:
        nf = M.Fragment(source=M.Source(id="window", kind="resolver", locator=str(RECEIPTS), status="ok", items=1))
        nf.gaps.append(M.Gap(component="hook-hub", what="turn window resolved from receipts only", why=note, severity="info"))
        frags.insert(0, nf)
    return assemble(window, frags, profile=profile, mode=mode, argv=argv)


def write_waybill(wb: dict, out: str | None, compact: bool = False) -> Path:
    path = Path(out) if out else Path.cwd() / f"{wb['id']}.waybill.json"
    # an existing dir, a trailing slash, or a suffix-less name means "write into this directory"
    if path.is_dir() or (out and (out.endswith(("/", "\\")) or not path.suffix)):
        path.mkdir(parents=True, exist_ok=True)
        path = path / f"{wb['id']}.waybill.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if path.suffix == ".gz":
        from . import query as Q
        tmp.write_bytes(Q.encode(wb, True))
        tmp.replace(path)
        return path
    tmp.write_text((json.dumps(wb, ensure_ascii=False, separators=(",", ":"), default=str) if compact
                    else json.dumps(wb, ensure_ascii=False, indent=1, default=str)) + "\n")
    tmp.replace(path)
    return path


def summary_lines(wb: dict) -> list[str]:
    st = wb.get("stats") or {}
    srcs = " ".join(f"{s['id']}:{s['status']}" for s in wb.get("sources") or [])
    gaps = wb.get("gaps") or []
    sev = {k: sum(1 for g in gaps if g.get("severity") == k) for k in ("broken", "warn", "info")}
    return [
        wb.get("title", ""),
        f"  {int(st.get('spans', 0))} spans · {int(st.get('events', 0))} events · {int(st.get('tools', 0))} tools · "
        f"{int(st.get('llm_calls', 0))} llm calls · {int(st.get('handlers', 0))} handlers "
        f"({int(st.get('handlers_skipped', 0))} skipped, {int(st.get('handlers_failed', 0))} failed)",
        f"  gaps: {sev['broken']} broken, {sev['warn']} warn, {sev['info']} info · findings: {len(wb.get('findings') or [])}",
        f"  sources: {srcs}",
    ]


# ---------------------------------------------------------------- subcommands

def _csv(v: str | None) -> list[str] | None:
    return [x.strip() for x in v.split(",") if x.strip()] if v else None


def cmd_capture(a: argparse.Namespace, argv: list[str]) -> int:
    settle_ms = float(a.settle) * 1000.0
    try:
        latest = bool(a.latest or (a.turn is None and not a.at))
        window, note = resolve_window(a.session, a.cli, a.turn, latest, a.at, settle_ms)
    except Exception as exc:
        _err(f"waybill: cannot resolve the turn: {type(exc).__name__}: {exc}")
        return 2
    src = getattr(window, "turn_source", None)
    if a.turn is not None and src == "receipts" and not note:
        note = (f"--turn {a.turn} was counted from hook-hub UserPromptSubmit receipts because the transcript could not "
                "place it; it can differ from the transcript's own turn index")
    print(f"capturing {window.cli} session {window.session_id} turn {window.turn_index or '?'}"
          + (f" [{'transcript turn index' if src == 'transcript' else 'counted from receipts'}]" if src else "")
          + f" ({M.iso(window.t0)} .. {M.iso(window.t_end)})", file=sys.stderr)
    wb = run_pipeline(window, profile=a.profile, deep=a.deep, only=_csv(a.only), skip=_csv(a.skip),
                      mode="capture", argv=argv, timeout_s=a.timeout, note=note,
                      progress=lambda s: print(s, file=sys.stderr))
    if a.max_kb:
        from .assemble import thin_to_budget
        wb = thin_to_budget(wb, int(a.max_kb * 1024))
    path = write_waybill(wb, a.output, compact=bool(a.max_kb))
    for line in summary_lines(wb):
        print(line)
    print(str(path))
    return 0


def cmd_record(a: argparse.Namespace, argv: list[str]) -> int:
    from . import live
    path = live.record(cli=a.cli, settle_s=a.settle, timeout_s=a.timeout, out=a.output, profile=a.profile,
                       deep=a.deep, only=_csv(a.only), skip=_csv(a.skip), argv=argv,
                       session=a.session, cwd=a.cwd, any_cwd=a.any)
    return 0 if path else 1


def load_waybill(path: str) -> dict:
    raw = Path(path).read_bytes()
    if raw[:2] == b"\x1f\x8b":        # .waybill.json.gz (a query waybill)
        import gzip
        raw = gzip.decompress(raw)
    wb = json.loads(raw.decode("utf-8"))
    if not isinstance(wb, dict) or wb.get("format") != "33god.waybill":
        raise ValueError(f"{path} is not a 33god.waybill document")
    if int(wb.get("version") or 0) != 1:
        raise ValueError(f"{path} has unsupported waybill version {wb.get('version')!r} (this reader knows 1)")
    return wb


def cmd_show(a: argparse.Namespace, argv: list[str]) -> int:
    from . import show
    try:
        wb = load_waybill(a.file)
    except (OSError, ValueError) as exc:
        _err(f"waybill: {exc}")
        return 2
    color = None if not a.no_color else False
    sys.stdout.write(show.render(wb, width=a.width, show_all=a.all, color=color))
    return 0


def cmd_publish(a: argparse.Namespace, argv: list[str]) -> int:
    from . import publish
    try:
        res = publish.publish(a.file, full=a.full, name=a.name, project=a.project, dry_run=a.dry_run)
    except Exception as exc:
        _err(f"waybill publish: {exc}")
        return 1
    print(res["json_url"])
    print(res["factory_url"])
    return 0


def recent_prompts(cli: str | None = None, limit: int = 20) -> list[dict]:
    rows = receipts_query(
        "select i.invocation_id, i.cli, i.session_id, i.received_at, i.status, "
        "(select e.event_id from executions e where e.invocation_id=i.invocation_id and e.handler_id='bloodbank-publisher') "
        "from invocations i where i.native='UserPromptSubmit'" + (" and i.cli=?" if cli else "")
        + " order by i.received_at desc limit ?", ((cli, limit) if cli else (limit,)))
    out = [{"invocation_id": r[0], "cli": r[1], "session_id": r[2], "received_at": r[3], "status": r[4],
            "event_id": r[5], "prompt": None, "turn_id": None, "turn": None, "turn_source": None} for r in rows]

    def fill(item: dict) -> None:
        env = candystore_envelope(item["event_id"]) if item["event_id"] else None
        data = (env or {}).get("data") if isinstance((env or {}).get("data"), dict) else {}
        item["prompt"] = data.get("prompt_text")
        item["turn_id"] = data.get("turn_id")
        try:     # the transcript's own turn index wins over the event's turn_id, then a receipts count
            from . import window as W
            ti = W.transcript_turn_index(item["session_id"], item["cli"], M.ms(item["received_at"]) or 0.0) \
                if item.get("session_id") else None
        except Exception:
            ti = None
        if ti:
            item["turn"], item["turn_source"] = ti, "transcript"
        elif ":turn:" in (item["turn_id"] or ""):
            item["turn"], item["turn_source"] = int(str(item["turn_id"]).rsplit(":", 1)[-1] or 0) or None, "event"
    ths = [threading.Thread(target=fill, args=(it,), daemon=True) for it in out]
    for t in ths:
        t.start()
    for t in ths:
        t.join(3.0)
    for it in out:      # last resort: count this session's prompt receipts up to this one
        if it.get("turn") is None and it.get("session_id"):
            try:
                n = receipts_query("select count(*) from invocations where session_id=? and native='UserPromptSubmit' "
                                   "and received_at<=?", (it["session_id"], it["received_at"]))
                if n and n[0][0]:
                    it["turn"], it["turn_source"] = int(n[0][0]), "receipts"
            except Exception:
                pass
    return out


def cmd_list(a: argparse.Namespace, argv: list[str]) -> int:
    try:
        items = recent_prompts(a.cli, a.limit)
    except sqlite3.Error as exc:
        _err(f"waybill: cannot read receipts at {RECEIPTS}: {exc}")
        return 2
    if a.json:
        print(json.dumps(items, indent=1))
        return 0
    if not items:
        print("no prompt receipts found")
        return 0
    print(f"{'received (UTC)':<24} {'cli':<7} {'session':<38} {'turn':<6} prompt")
    for it in items:
        words = " ".join((it.get("prompt") or "").split())
        words = (words[:58] + "…") if len(words) > 59 else (words or "(prompt text not in Candystore)")
        turn = "" if it.get("turn") is None else f"{it['turn']}{'*' if it.get('turn_source') == 'receipts' else ''}"
        print(f"{it['received_at']:<24} {it['cli']:<7} {it['session_id'] or '-':<38} {turn:<6} {words}")
    if any(it.get("turn_source") == "receipts" for it in items):
        print("\n* turn counted from hook-hub receipts (the transcript could not place it)")
    print("\ncapture one:  waybill capture --session <session> --at <received>")
    return 0


# ---------------------------------------------------------------- night

def cmd_night(a: argparse.Namespace, argv: list[str]) -> int:
    from datetime import date as _date, datetime as _dt, timedelta as _td
    from zoneinfo import ZoneInfo
    from . import night
    day = _date.fromisoformat(a.date) if a.date else (_dt.now(ZoneInfo(a.tz)).date() - _td(days=1))
    doc = night.build(day, a.start, a.end, a.tz, a.profile, a.label)
    out = Path(a.output) if a.output else Path(f"night-{day.isoformat()}.json")
    if out.is_dir():
        out = out / f"{day.isoformat()}.json"
    out.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    t = doc["totals"]
    print(f"{out}  {doc['window']['label']}  {t['events']:,} events  {t['components']} components  "
          f"{t['desks']} desks  {t['unmapped_events']:,} unmapped  {out.stat().st_size / 1024:.0f} KiB")
    return 0


# ---------------------------------------------------------------- query

def parse_when(text: str, tz: str) -> float:
    """ISO 8601 (a naive time or a bare date is read in tz) -> epoch ms."""
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo
    t = (text or "").strip()
    try:
        d = _dt.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"cannot read the time {text!r} (use ISO 8601, e.g. 2026-11-20T18:02 or 2026-11-20)") from None
    if d.tzinfo is None:
        d = d.replace(tzinfo=ZoneInfo(tz))
    return d.timestamp() * 1000.0


def find_session(correlation: str) -> tuple[str, str | None] | None:
    """(session_id, cli) of the hook-hub session a Candystore correlation id names, or None."""
    from .collectors import candystore as CS
    try:
        direct = receipts_query("select session_id, cli from invocations where session_id=? limit 1", (correlation,))
        if direct:
            return direct[0][0], direct[0][1]
        for sid, cli in receipts_query("select distinct session_id, cli from invocations where session_id != '' and cli='codex'"):
            if CS.correlation_id(cli, sid) == correlation:
                return sid, cli
    except sqlite3.Error:
        return None
    return None


def session_upgrade(correlation: str, since: float, until: float) -> tuple[M.TurnWindow | None, list[str]]:
    """A single-session query inside hook-hub's receipt retention is a capture: (window, notes).
    window is None when the session is not in the receipts, started before them, or holds several prompts
    in the window; notes then lists the --at values a capture would take."""
    found = find_session(correlation)
    if not found:
        return None, []
    sid, cli = found
    try:
        rows = receipts_query("select received_at from invocations where session_id=? and native='UserPromptSubmit' "
                              "order by received_at", (sid,))
        oldest = receipts_query("select min(received_at) from invocations")[0][0]
    except sqlite3.Error:
        return None, []
    inside = [r[0] for r in rows if since - 1000 <= (M.ms(r[0]) or 0) <= until + 1000]
    if not rows or (oldest and (M.ms(oldest) or 0) > since):
        return None, []             # the receipts do not reach back to the start of the query
    if len(inside) != 1:
        return None, [f"waybill capture --session {sid} --at {r}" for r in inside[:10]]
    window, _note = resolve_window(sid, cli, None, False, inside[0])
    return window, []


def cmd_query(a: argparse.Namespace, argv: list[str]) -> int:
    from . import query as Q
    from . import publish as P
    tz = a.tz
    reader = Q.PsqlReader()
    try:
        now = reader.now_ms()
        filters = {k: v for k, v in {"type": a.type, "producer": a.producer, "project": a.project, "correlation": a.correlation,
                                     "scope": a.scope, "lens": a.lens, "q": a.q, "class": a.cls}.items() if v}
        since = until = None
        event = None
        kind, extra = "window", ""
        if a.from_url:
            u = Q.parse_candystore_url(a.from_url)
            filters = {**u["filters"], **filters}
            event = u["event"]
            if u["from"]:
                since = parse_when(u["from"], tz)
            if u["to"]:
                until = parse_when(u["to"], tz)
        if a.last_night:
            since, until = Q.last_night(now, tz)
            kind = "last-night"
        elif a.last:
            until = now if not a.until else parse_when(a.until, tz)
            since = until - Q.parse_duration(a.last)
            kind = "last"
        else:
            if a.since:
                since = parse_when(a.since, tz)
            if a.until:
                until = parse_when(a.until, tz)
        if event and since is None:
            t = reader.event_time(event)
            if t is None:
                _err(f"waybill query: event {event} is not in the archive")
                return 2
            since, until = t - 60_000.0, t + 60_000.0
        if since is None and filters.get("correlation"):
            span = reader.session_span(filters["correlation"])
            if span:
                since, until = span[0], span[1] + 1000.0
                kind, extra = "session", filters["correlation"]
        if since is None:
            until = now if until is None else until
            since = until - 24 * 3600 * 1000.0         # Candystore's own default window
        elif until is None:
            until = now
        if until <= since:
            _err("waybill query: the window is empty (--until is not after --since)")
            return 2
        clamped = until > now - 2000.0 and kind == "last-night"
        label = a.label or Q.window_label(kind, since, min(until, now - 2000.0) if clamped else until, tz, clamped, extra)[0]
        when = Q.window_label(kind, since, min(until, now - 2000.0) if clamped else until, tz, clamped, extra)[1]
        if clamped:
            until = min(until, now - 2000.0)
    except (ValueError, RuntimeError) as exc:
        _err(f"waybill query: {exc}")
        return 2
    spec = Q.QuerySpec(since=since, until=until, clock=a.clock, filters=filters, label=label, when=when, tz=tz,
                       profile=a.profile, budget_stops=a.budget_stops, include_dead_letters=a.include_dead_letters)

    # a single session inside hook-hub's retention is a capture: richer, and it says so
    only_session = set(k for k, v in filters.items() if v) == {"correlation"}
    if only_session and not a.no_capture:
        window, ats = session_upgrade(filters["correlation"], since, until)
        if window is not None:
            print(f"single-session query inside hook-hub retention: upgraded to a capture of {window.cli} session "
                  f"{window.session_id} turn {window.turn_index or '?'} (--no-capture keeps the query waybill)", file=sys.stderr)
            wb = run_pipeline(window, profile="public" if a.profile == "public" else "full", mode="capture",
                              argv=argv if argv[:1] == ["waybill"] else ["waybill", *argv],
                              progress=lambda s: print(s, file=sys.stderr))
            path = write_waybill(wb, a.output, compact=True)
            for line in summary_lines(wb):
                print(line)
            print(str(path))
            return _maybe_publish(a, str(path), P)
        if ats:
            print("this session has several prompts in the window; capture one turn with:\n  " + "\n  ".join(ats), file=sys.stderr)

    t_all = time.monotonic()
    try:
        wb = Q.run(spec, reader, progress=lambda s: print(s, file=sys.stderr))
    except Exception as exc:
        _err(f"waybill query: {type(exc).__name__}: {exc}")
        return 1
    out = a.output or f"{wb['id']}.waybill.json.gz"
    if Path(out).is_dir() or out.endswith(("/", "\\")) or not Path(out).suffix:
        out = str(Path(out) / f"{wb['id']}.waybill.json.gz")
    gz = out.endswith(".gz")
    wb, size = Q.fit_budget(wb, int(a.max_kb * 1024), gz)
    path = write_waybill(wb, out, compact=True)
    size = path.stat().st_size
    st = wb["stats"]
    wall = time.monotonic() - t_all
    print(wb["title"])
    print(f"  {st['query_total']:,} events matched + {st['dead_letters']} dead letter(s): {st['kept_events']} kept, "
          f"{st['batched_events']:,} in {st['batches']} batches over {st['chapters']} chapters")
    print(f"  conservation: {'ok' if st['conservation_ok'] else 'BROKEN'} "
          f"({st['kept_events']} + {st['batched_events']} = {st['kept_events'] + st['batched_events']} of "
          f"{st['query_total'] + st['dead_letters']}) · unresolved producers: {st['unresolved_producers']} · "
          f"{st['spans']} spans · {st['events']} events · {len(wb.get('findings') or [])} findings · "
          f"{len(wb.get('gaps') or [])} gaps")
    print(f"  {size / 1024:.0f} KiB{' gz' if gz else ''} (limit {a.max_kb:g}) · {wall:.1f} s wall")
    print(str(path))
    if not st["conservation_ok"]:
        return 3
    return _maybe_publish(a, str(path), P)


def _audit_ids() -> list[str]:
    from .audit_sources import ADAPTERS
    return list(ADAPTERS)


def cmd_audit(a: argparse.Namespace, argv: list[str]) -> int:
    from . import audit as AU
    from . import publish as P
    from . import query as Q
    split = lambda s: [x.strip() for x in (s or "").split(",") if x.strip()]  # noqa: E731
    try:
        spec = AU.AuditSpec(days=a.days, until=parse_when(a.until, a.tz) if a.until else None, settle_s=a.settle,
                            only=split(a.only), skip=split(a.skip), profile=a.profile, tz=a.tz)
        spec.adapters()
        if a.days <= 0:
            raise ValueError("--days must be positive")
    except ValueError as exc:
        _err(f"waybill audit: {exc}")
        return 2
    t_all = time.monotonic()
    try:
        wb, rows = AU.run(spec, progress=lambda s: print(s, file=sys.stderr))
    except Exception as exc:
        _err(f"waybill audit: {type(exc).__name__}: {exc}")
        return 1
    out = a.output or f"{wb['id']}.waybill.json.gz"
    if Path(out).is_dir() or out.endswith(("/", "\\")) or not Path(out).suffix:
        out = str(Path(out) / f"{wb['id']}.waybill.json.gz")
    wb, _ = Q.fit_budget(wb, int(a.max_kb * 1024), out.endswith(".gz"))
    path = write_waybill(wb, out, compact=True)
    done = wb["audit"]["done"]
    if a.json:
        print(json.dumps({**wb["audit"], "waybill": str(path), "id": wb["id"]}, ensure_ascii=False, indent=1, default=str))
    else:
        print(wb["title"])
        for line in AU.table(rows):
            print(line)
        st = wb["stats"]
        print(f"query: {st['query_total']:,} events + {st['dead_letters']} dead letter(s) · {len(wb['findings'])} findings · "
              f"{len(wb['gaps'])} gaps · {path.stat().st_size / 1024:.0f} KiB · {time.monotonic() - t_all:.1f} s wall")
        for line in AU.done_lines(done):
            print(line)
        print(str(path))
    if not done["conservation_ok"]:
        return 3
    rc = _maybe_publish(a, str(path), P)
    return 4 if a.strict and done["silent"] and rc == 0 else rc


def _maybe_publish(a: argparse.Namespace, path: str, P) -> int:
    if not a.publish:
        return 0
    try:
        res = P.publish(path, full=False, name=a.name, project=a.artifact_project)
    except Exception as exc:
        _err(f"waybill query --publish: {exc}")
        return 1
    print(res["json_url"])
    print(res["factory_url"])
    return 0


# ---------------------------------------------------------------- argparse

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="waybill", description="A flight recorder for one prompt across 33GOD.")
    p.add_argument("--version", action="version", version=f"waybill {VERSION}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--settle", type=float, default=15.0, help="seconds to keep collecting after Stop (default 15)")
        sp.add_argument("--profile", choices=("full", "public"), default="full",
                        help="full keeps everything the sources hold (local use); public redacts prompts, paths, "
                             "hostnames and user names and cuts long text, so the file is safe to commit or publish "
                             "(default full)")
        sp.add_argument("--deep", action="store_true", help="allow credentialed lookups (gateway traces)")
        sp.add_argument("-o", "--output", help="output file or directory (default ./<id>.waybill.json)")
        sp.add_argument("--only", help="comma-separated collectors to run")
        sp.add_argument("--skip", help="comma-separated collectors to skip")

    c = sub.add_parser("capture", help="rebuild a past turn from what every source still holds")
    c.add_argument("--session", help="native session id (default: the most recent prompt of any session)")
    c.add_argument("--cli", choices=("claude", "codex"), help="CLI (default: from the receipts)")
    g = c.add_mutually_exclusive_group()
    g.add_argument("--turn", type=int, help="1-based turn index")
    g.add_argument("--latest", action="store_true", help="the most recent turn (default)")
    g.add_argument("--at", help="ISO time: the turn whose prompt was submitted at or just before it")
    common(c)
    c.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S, help="per-collector timeout in seconds")
    c.add_argument("--max-kb", type=float, help="shrink the output to this many KiB (compact JSON), cheapest loss first; "
                   "meant for committed public samples")
    c.set_defaults(func=cmd_capture)

    r = sub.add_parser("record", help="arm live taps, wait for the next prompt, follow it to Stop")
    r.add_argument("--cli", choices=("claude", "codex"), help="only follow prompts from this CLI")
    r.add_argument("--session", help="follow this native session id only")
    r.add_argument("--cwd", help="only follow sessions working in or around this directory (default: the current directory)")
    r.add_argument("--any", action="store_true", help="follow a prompt from any working directory "
                   "(cron, Crank and child sessions are still ignored)")
    common(r)
    r.add_argument("--timeout", type=float, default=900.0, help="give up after this many seconds (default 900)")
    r.set_defaults(func=cmd_record)

    s = sub.add_parser("show", help="DevTools-style waterfall in the terminal")
    s.add_argument("file", help="a .waybill.json file written by capture or record")
    s.add_argument("--width", type=int, help="terminal width (default: detected)")
    s.add_argument("--all", action="store_true", help="do not collapse tool loops, repeated events or the llm.usage / allowance fan-out")
    s.add_argument("--no-color", action="store_true")
    s.set_defaults(func=cmd_show)

    pb = sub.add_parser("publish", help="publish to MinIO (public profile) and print the Factory link")
    pb.add_argument("file", help="the .waybill.json file to publish (the public profile is cut from it)")
    pb.add_argument("--full", action="store_true", help="publish the full profile as is (no public cut)")
    pb.add_argument("--name", help="artifact name (default: waybill-<id>)")
    pb.add_argument("--project", help="artifact project slug (default: the publish script's own resolution)")
    pb.add_argument("--dry-run", action="store_true", help="show the publish plan, upload nothing")
    pb.set_defaults(func=cmd_publish)

    nt = sub.add_parser("night", help="digest a window of wall-clock time (default: last night 18:02-07:41) into a 33god.night file")
    nt.add_argument("--date", help="the evening the night starts on, YYYY-MM-DD (default: yesterday in --tz)")
    nt.add_argument("--from", dest="start", default="18:02", help="local start time (default 18:02)")
    nt.add_argument("--to", dest="end", default="07:41", help="local end time; at or before --from means the next day (default 07:41)")
    nt.add_argument("--tz", default="America/New_York", help="time zone of --date/--from/--to (default America/New_York)")
    nt.add_argument("--profile", choices=("full", "public"), default="public",
                    help="public (default) aliases third-party Hermes desks and drops unmapped producer names")
    nt.add_argument("--label", help="human label for the window (default: e.g. '16–17 Nov 2026')")
    nt.add_argument("-o", "--output", help="output file or directory (default ./night-<date>.json)")
    nt.set_defaults(func=cmd_night)

    q = sub.add_parser("query", help="replay any Candystore query (last night, last 2h, one project's errors) as a waybill",
                       description="Any window of the Bloodbank archive as a replayable waybill: rare events, failures and "
                                   "dead letters stay individual, the rest folds into per-minute batches under at most 12 chapters.")
    w = q.add_argument_group("window (default: the last 24 hours, Candystore's own)")
    w.add_argument("--since", help="ISO time or date, read in --tz when it has no offset")
    w.add_argument("--until", help="ISO time (default now)")
    w.add_argument("--last", metavar="DUR", help="the last DUR up to now, e.g. 30m, 2h, 1d")
    w.add_argument("--last-night", action="store_true", help="last night, 18:02 to 07:41 in --tz (what `waybill night` digests)")
    w.add_argument("--from-url", metavar="URL", help="a Candystore UI link: its filters and from/to; /sessions/<id> and /events/<id> work")
    f = q.add_argument_group("filters (Candystore's own, so --lens errors means what the UI means)")
    f.add_argument("--type", help="event type(s), comma-separated")
    f.add_argument("--producer", help="exact producer")
    f.add_argument("--project", help="project slug")
    f.add_argument("--correlation", help="correlation id (a session id): one session inside hook-hub retention upgrades to a capture")
    f.add_argument("--scope", help="type scope(s), e.g. agent.hook")
    f.add_argument("--lens", help="a Candystore lens (errors, decisions, ...)")
    f.add_argument("--q", help="free text (a UUID matches an event or correlation id exactly)")
    f.add_argument("--class", dest="cls", help="provenance class")
    q.add_argument("--clock", choices=("time", "received_at"), default="time",
                   help="time (default, indexed) or received_at (when Candystore archived it)")
    q.add_argument("--tz", default="America/New_York", help="time zone for --last-night, chapter titles and bare times (default America/New_York)")
    q.add_argument("--label", help="window label (default: derived, e.g. 'Last night, 18:02 to 07:41')")
    q.add_argument("--budget-stops", type=int, default=60, help="stops a playback should have; chapters = stops/5, at most 12 (default 60)")
    q.add_argument("--max-kb", type=float, default=4096, help="size limit of the written file in KiB (default 4096)")
    q.add_argument("--profile", choices=("public", "full"), default="public",
                   help="public (default): message/call/payment types counted never named, third-party desks aliased, "
                        "unknown producers numbered, text cut; full keeps names and payloads (local use only)")
    q.add_argument("--include-dead-letters", action=argparse.BooleanOptionalAction, default=True,
                   help="show Candystore's dead letters as dropped events (default on)")
    q.add_argument("--no-capture", action="store_true", help="never upgrade a single-session query to a capture")
    q.add_argument("-o", "--output", help="output file (.waybill.json.gz is gzipped) or directory (default ./<id>.waybill.json.gz)")
    q.add_argument("--publish", action="store_true", help="then publish to MinIO and print the Factory link")
    q.add_argument("--name", help="artifact name for --publish")
    q.add_argument("--artifact-project", help="artifact project slug for --publish")
    q.set_defaults(func=cmd_query)

    au = sub.add_parser("audit", help="the event gap audit: did everything that happened become an event? (on demand)",
                        description="Compare every ground-truth source (the bus by id, Candybar, hook-hub, the gateway ledger, "
                                    "transcripts, Hermes, systemd, git, Hindsight, schemas, dead letters) with Candystore and "
                                    "write one query-mode waybill whose gaps and findings carry the audit (SPEC 2c).")
    au.add_argument("--days", type=float, default=1.0, help="window length in days, ending now less --settle (default 1)")
    au.add_argument("--until", help="ISO end of the window (default: the archive's now less --settle)")
    au.add_argument("--settle", type=float, default=120.0, help="seconds left for late writers at the end (default 120)")
    au.add_argument("--only", help="comma-separated adapters to run (default all): " + ",".join(_audit_ids()))
    au.add_argument("--skip", help="comma-separated adapters to leave out")
    au.add_argument("--json", action="store_true", help="print the audit block as JSON instead of the table")
    au.add_argument("--tz", default="America/New_York", help="time zone for labels (default America/New_York)")
    au.add_argument("--profile", choices=("public", "full"), default="public",
                    help="public (default) names no third-party desk, private type or local path; full keeps them")
    au.add_argument("--max-kb", type=float, default=4096, help="size limit of the written file in KiB (default 4096)")
    au.add_argument("--strict", action="store_true", help="exit 4 while any non-exempt row is still silent")
    au.add_argument("-o", "--output", help="output file or directory (default ./<id>.waybill.json.gz)")
    au.add_argument("--publish", action="store_true", help="then publish to MinIO and print the Factory link")
    au.add_argument("--name", help="artifact name for --publish")
    au.add_argument("--artifact-project", help="artifact project slug for --publish")
    au.set_defaults(func=cmd_audit)

    ls = sub.add_parser("list", help="recent prompt invocations to pick one to capture")
    ls.add_argument("--cli", choices=("claude", "codex"), help="only list prompts from this CLI")
    ls.add_argument("--limit", type=int, default=20, help="how many recent prompts to list (default 20)")
    ls.add_argument("--json", action="store_true", help="print the rows as JSON instead of a table")
    ls.set_defaults(func=cmd_list)
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--usage-spec" in argv and "--" not in argv[:argv.index("--usage-spec")]:
        sys.stdout.write(Path(__file__).with_name("waybill.usage.kdl").read_text())
        return 0
    a = build_parser().parse_args(argv)
    try:
        return int(a.func(a, ["waybill", *argv]) or 0)
    except KeyboardInterrupt:
        _err("interrupted")
        return 130
    except BrokenPipeError:
        return 0
