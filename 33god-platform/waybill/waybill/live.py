"""waybill record: arm live taps, wait for the next prompt, follow it to Stop, then capture.

Taps (all read-only):
  * core NATS subscription (nats-py, plain SUB, never a JetStream consumer) on bloodbank.evt.> and
    deckard.evt.attention; attention events are never stored anywhere else.
  * `redis-cli --json PSUBSCRIBE nlp:events asm:*` (nanoleaf painter states, ASM transitions pub/sub).
  * every 2 s: XRANGE/HGETALL/TTL of the session's ASM stream/hash and the hindsight capture buffer
    file, because both expire (900 s TTL) or are deleted after delivery.

ctx.live keys handed to the collectors (all times epoch ms):
  armed_at, prompt {session_id, invocation_id, received_ms, cli}, stop {invocation_id, received_ms} | None,
  nats [{subject, received_ms, headers, data (raw text), envelope (dict|None)}],
  redis [{pattern, channel, message (raw text), json (dict|None), received_ms}],
  asm {stream_key, hash_key, stream [{id, fields, j (the raw JSON string the asm collector reads), json (decoded)}], hash {..}, ttl, snap_ms, snapshots},
  capture {path, json | text, snap_ms, first_ms, deleted_ms, versions}
"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

from . import model as M

NATS_URL = os.environ.get("WAYBILL_NATS_URL", os.environ.get("NATS_URL", "nats://127.0.0.1:4222"))
NATS_SUBJECTS = ("bloodbank.evt.>", "deckard.evt.attention")
REDIS_PATTERNS = ("nlp:events", "asm:*")
CAPTURE_DIR = Path.home() / ".local/state/33god/hook-hub/capture"
MAX_MESSAGES = 200_000
POLL_S = 0.25
SNAP_S = 2.0


def _redis_base() -> list[str]:
    cmd = ["redis-cli"]
    if os.environ.get("WAYBILL_REDIS_HOST"):
        cmd += ["-h", os.environ["WAYBILL_REDIS_HOST"]]
    if os.environ.get("WAYBILL_REDIS_PORT"):
        cmd += ["-p", os.environ["WAYBILL_REDIS_PORT"]]
    return cmd


def redis_json(*args: str, timeout: float = 3.0) -> Any:
    """Run one read-only redis-cli command with --json output (argv list, no shell)."""
    allowed = {"GET", "HGETALL", "XRANGE", "SCAN", "TTL", "TYPE"}
    if args[0].upper() not in allowed:
        raise ValueError(f"redis command {args[0]} is not read-only")
    p = subprocess.run(_redis_base() + ["--json", *args], capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip() or f"redis-cli exit {p.returncode}")
    out = p.stdout.strip()
    return json.loads(out) if out else None


# ---------------------------------------------------------------- taps

class NatsTap:
    """A core-NATS subscriber in its own thread + event loop."""

    def __init__(self, url: str = NATS_URL, subjects: tuple[str, ...] = NATS_SUBJECTS) -> None:
        self.url, self.subjects = url, subjects
        self.msgs: list[dict] = []
        self.lock = threading.Lock()
        self.error: str | None = None
        self.dropped = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop: asyncio.Event | None = None
        self._ready = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self, wait_s: float = 5.0) -> bool:
        self.thread = threading.Thread(target=self._run, name="waybill-nats", daemon=True)
        self.thread.start()
        self._ready.wait(wait_s)
        return self.error is None and self._loop is not None

    def _run(self) -> None:
        try:
            import nats  # noqa: F401  (lazy: only record needs it)
        except Exception as exc:
            self.error = f"nats-py is not importable by {sys.executable}: {exc}"
            self._ready.set()
            return
        try:
            asyncio.run(self._main())
        except Exception as exc:
            self.error = self.error or f"{type(exc).__name__}: {exc}"
            self._ready.set()

    async def _main(self) -> None:
        import nats
        self._loop = asyncio.get_running_loop()
        self._stop = asyncio.Event()
        try:
            nc = await nats.connect(self.url, name="waybill-recorder", connect_timeout=3,
                                    allow_reconnect=True, max_reconnect_attempts=30, reconnect_time_wait=1)
        except Exception as exc:
            self.error = f"cannot connect to {self.url}: {type(exc).__name__}: {exc}"
            self._ready.set()
            return

        async def on_msg(msg: Any) -> None:
            recv = M.now_ms()
            text = msg.data.decode("utf-8", "replace") if msg.data else ""
            with self.lock:
                if len(self.msgs) >= MAX_MESSAGES:
                    self.dropped += 1
                    return
                self.msgs.append({"subject": msg.subject, "received_ms": recv,
                                  "headers": dict(msg.headers or {}), "data": text})

        try:
            for s in self.subjects:
                await nc.subscribe(s, cb=on_msg)  # plain core SUB: no JetStream consumer is created
            self._ready.set()
            await self._stop.wait()
        finally:
            try:
                await asyncio.wait_for(nc.drain(), timeout=3)
            except Exception:
                try:
                    await nc.close()
                except Exception:
                    pass

    def stop(self) -> None:
        if self._loop is not None and self._stop is not None:
            try:
                self._loop.call_soon_threadsafe(self._stop.set)
            except RuntimeError:
                pass
        if self.thread is not None:
            self.thread.join(5)

    def snapshot(self) -> list[dict]:
        with self.lock:
            return list(self.msgs)


class RedisTap:
    """`redis-cli --json PSUBSCRIBE ...` as a child process, one JSON array per line."""

    def __init__(self, patterns: tuple[str, ...] = REDIS_PATTERNS) -> None:
        self.patterns = patterns
        self.msgs: list[dict] = []
        self.lock = threading.Lock()
        self.error: str | None = None
        self.proc: subprocess.Popen | None = None
        self.thread: threading.Thread | None = None
        self.subscribed = 0

    def start(self) -> bool:
        try:
            self.proc = subprocess.Popen(_redis_base() + ["--json", "PSUBSCRIBE", *self.patterns],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1,
                                         start_new_session=True)
        except OSError as exc:
            self.error = f"cannot start redis-cli: {exc}"
            return False
        self.thread = threading.Thread(target=self._read, name="waybill-redis", daemon=True)
        self.thread.start()
        return True

    def _read(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        for line in self.proc.stdout:
            recv = M.now_ms()
            line = line.strip()
            if not line:
                continue
            try:
                arr = json.loads(line)
            except ValueError:
                continue
            if not isinstance(arr, list) or not arr:
                continue
            if arr[0] == "psubscribe":
                self.subscribed += 1
                continue
            if arr[0] == "pmessage" and len(arr) >= 4:
                msg = arr[3] if isinstance(arr[3], str) else json.dumps(arr[3])
                try:
                    parsed = json.loads(msg)
                except ValueError:
                    parsed = None
                with self.lock:
                    if len(self.msgs) < MAX_MESSAGES:
                        self.msgs.append({"pattern": arr[1], "channel": arr[2], "message": msg,
                                          "json": parsed if isinstance(parsed, dict) else None,
                                          "received_ms": recv})
        if self.proc.poll() not in (None, 0, -15) and not self.error:
            err = (self.proc.stderr.read() if self.proc.stderr else "") or ""
            self.error = err.strip() or f"redis-cli exited {self.proc.returncode}"

    def stop(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
            except OSError:
                self.proc.terminate()
            try:
                self.proc.wait(2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.thread is not None:
            self.thread.join(2)

    def snapshot(self) -> list[dict]:
        with self.lock:
            return list(self.msgs)


# ---------------------------------------------------------------- short-lived state snapshots

def snapshot_state(cli: str, sid: str, live: dict) -> None:
    now = M.now_ms()
    asm = live.setdefault("asm", {"stream_key": f"asm:t:{cli}:s:{sid}", "hash_key": f"asm:a:{cli}:s:{sid}",
                                  "stream": [], "hash": {}, "ttl": None, "snap_ms": None, "snapshots": 0})
    try:
        rows = redis_json("XRANGE", asm["stream_key"], "-", "+") or []
        have = {e["id"] for e in asm["stream"]}
        for row in rows:
            if not isinstance(row, list) or len(row) < 2 or row[0] in have:
                continue
            flat = row[1] if isinstance(row[1], list) else []
            fields = {flat[i]: flat[i + 1] for i in range(0, len(flat) - 1, 2)}
            j = None
            if isinstance(fields.get("j"), str):
                try:
                    j = json.loads(fields["j"])
                except ValueError:
                    j = None
            asm["stream"].append({"id": row[0], "fields": fields, "j": fields.get("j"), "json": j})
        h = redis_json("HGETALL", asm["hash_key"])
        if isinstance(h, dict) and h:
            asm["hash"] = h
        asm["ttl"] = redis_json("TTL", asm["stream_key"])
        asm["snap_ms"] = now
        asm["snapshots"] += 1
        asm.pop("error", None)
    except Exception as exc:
        asm["error"] = f"{type(exc).__name__}: {exc}"
    cap = live.setdefault("capture", {"path": str(CAPTURE_DIR / f"{cli}-{sid}.json"), "snap_ms": None,
                                      "first_ms": None, "deleted_ms": None, "versions": 0})
    p = Path(cap["path"])
    try:
        text = p.read_text(encoding="utf-8")
        if text != cap.get("_raw"):
            cap["_raw"] = text
            cap["versions"] += 1
            try:
                cap["json"] = json.loads(text)
                cap.pop("text", None)
            except ValueError:
                cap["text"] = text
        cap["first_ms"] = cap["first_ms"] or now
        cap["snap_ms"] = now
        cap["deleted_ms"] = None
    except FileNotFoundError:
        if cap.get("_raw") is not None and cap.get("deleted_ms") is None:
            cap["deleted_ms"] = now
    except OSError as exc:
        cap["error"] = str(exc)


# ---------------------------------------------------------------- receipts polling

def _receipts():
    from . import cli as C
    return C.receipts_query


def prompt_after(armed_at: float, cli: str | None) -> tuple[str, str, float] | None:
    try:
        from . import window as W
        fn = W.latest_prompt_after
    except Exception:
        fn = None
    if fn is not None:
        return fn(armed_at, cli)
    q = _receipts()
    sql = ("select session_id, invocation_id, received_at from invocations where native='UserPromptSubmit' "
           "and received_at>? and session_id is not null and session_id!=''")
    args: tuple = (M.iso(armed_at),)
    if cli:
        sql += " and cli=?"
        args += (cli,)
    rows = q(sql + " order by received_at limit 1", args)
    return (rows[0][0], rows[0][1], M.ms(rows[0][2]) or 0.0) if rows else None


def invocation_cli(invocation_id: str) -> str | None:
    rows = _receipts()("select cli from invocations where invocation_id=?", (invocation_id,))
    return rows[0][0] if rows else None


def stop_after(sid: str, after_ms: float) -> tuple[str, float] | None:
    rows = _receipts()(
        "select invocation_id, received_at from invocations where session_id=? and native in ('Stop','StopFailure')"
        " and received_at>=? order by received_at limit 1", (sid, M.iso(after_ms)))
    return (rows[0][0], M.ms(rows[0][1]) or 0.0) if rows else None


def next_prompt_after(armed_at: float, cli: str | None, exclude: set[str]) -> tuple[str, str, float] | None:
    """The first prompt of a session not in `exclude`: used to leave a helper session behind."""
    sql = ("select session_id, invocation_id, received_at from invocations where native='UserPromptSubmit' "
           "and received_at>? and session_id is not null and session_id!=''")
    args: tuple = (M.iso(armed_at),)
    if cli:
        sql += " and cli=?"
        args += (cli,)
    for r in _receipts()(sql + " order by received_at", args):
        if r[0] not in exclude:
            return (r[0], r[1], M.ms(r[2]) or 0.0)
    return None


def ended_without_stop(sid: str, after_ms: float) -> bool:
    """True when the session said SessionEnd but never Stop: codex spawns short helper sessions (a prompt and a
    SessionEnd, no Stop, no rollout file) next to the real one, and the first prompt after arming can be theirs."""
    q = _receipts()
    ended = q("select 1 from invocations where session_id=? and native='SessionEnd' and received_at>=? limit 1",
              (sid, M.iso(after_ms)))
    stopped = q("select 1 from invocations where session_id=? and native in ('Stop','StopFailure') "
                "and received_at>=? limit 1", (sid, M.iso(after_ms)))
    return bool(ended) and not stopped


def session_invocations(sid: str, t0: float, t1: float) -> set[str]:
    rows = _receipts()("select invocation_id from invocations where session_id=? and received_at between ? and ?",
                       (sid, M.iso(t0 - 5000), M.iso(t1)))
    return {r[0] for r in rows}


# ---------------------------------------------------------------- live fragments

def _envelope(text: str) -> dict | None:
    try:
        d = json.loads(text)
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def _mentions(env: dict, needles: set[str]) -> bool:
    if not needles:
        return False
    for k in ("correlationid", "causationid", "subject"):
        if env.get(k) in needles:
            return True
    data = env.get("data") if isinstance(env.get("data"), dict) else {}
    for k in ("session_id", "thread_id", "invocation_id", "correlationid"):
        if data.get(k) in needles:
            return True
    return False


def nats_fragment(tap: NatsTap | None, sid: str, cli: str, invs: set[str], t0: float, t1: float) -> M.Fragment:
    started = time.monotonic()
    src = M.Source(id="live-nats", kind="nats-core-sub", locator=f"{NATS_URL} SUB {' '.join(NATS_SUBJECTS)}")
    frag = M.Fragment(source=src)
    if tap is None or tap.error:
        src.status, src.error = "error", (tap.error if tap else "tap not started")
        frag.gaps.append(M.Gap(component="bb-nats", what="no live bus tap", why=src.error or "", severity="warn"))
        return frag
    needles = {sid, *invs}
    attention_seen = 0
    for m in tap.snapshot():
        if m["received_ms"] < t0 - 5000 or m["received_ms"] > t1:
            continue
        env = _envelope(m["data"])
        if env is None:
            continue
        if m["subject"].startswith("deckard."):
            if sid not in m["data"]:
                continue
            attention_seen += 1
            key = str(env.get("id") or int(m["received_ms"]))
            data = env.get("data") if isinstance(env.get("data"), dict) else {}
            what = data.get("reason") or data.get("state") or data.get("kind") or env.get("type") or "attention"
            sp = M.Span(id=M.Ids.notify("attention", key), kind="notify", component=frag.component("deckard"),
                        name="attention", summary=f"deckard raised an attention signal ({what}).",
                        phase="async_after", t0=m["received_ms"], t1=None, status="ok", sync=False,
                        refs={"event_id": env.get("id")} if env.get("id") else {},
                        attrs={"subject": m["subject"], "received_ms": m["received_ms"], "stored": False},
                        payload=frag.artifact(env, note="core-NATS only: deckard attention is never stored"),
                        evidence=["live-nats"])
            frag.spans.append(sp)
            continue
        if not env.get("id") or not _mentions(env, needles):
            continue
        frag.events.append(M.BusEvent(
            id=str(env["id"]), type=str(env.get("type") or "unknown"), t=M.ms(env.get("time")) or m["received_ms"],
            subject=m["subject"], stream=None, seq=None, correlationid=env.get("correlationid"),
            causationid=env.get("causationid"), producer=env.get("producer") or env.get("source"),
            payload=frag.artifact(env), consumers=[]))
    src.items = len(frag.events) + attention_seen
    src.status = "ok" if src.items else "empty"
    src.ms = round((time.monotonic() - started) * 1000.0, 1)
    if tap.dropped:
        frag.gaps.append(M.Gap(component="bb-nats", what=f"{tap.dropped} live messages not kept",
                               why=f"the tap buffer is capped at {MAX_MESSAGES} messages", severity="info"))
    return frag


def redis_fragment(tap: RedisTap | None, sid: str, cli: str, live: dict, t0: float, t1: float) -> M.Fragment:
    started = time.monotonic()
    src = M.Source(id="live-redis", kind="redis-psubscribe", locator=f"redis-cli PSUBSCRIBE {' '.join(REDIS_PATTERNS)}")
    frag = M.Fragment(source=src)
    if tap is None or tap.error:
        src.status, src.error = "error", (tap.error if tap else "tap not started")
        frag.gaps.append(M.Gap(component="redis", what="no live Redis pub/sub tap", why=src.error or "", severity="info"))
        return frag
    scope = f"{cli}:s:{sid}"
    asm = live.get("asm") or {}
    pane = (asm.get("hash") or {}).get("zellij_pane")
    zsession = (asm.get("hash") or {}).get("zellij_session")
    stream_by_seq = {str((e.get("json") or {}).get("seq")): e["id"] for e in asm.get("stream") or [] if e.get("json")}
    have_stream = bool(asm.get("stream"))
    n = 0
    for m in tap.snapshot():
        if m["received_ms"] < t0 - 5000 or m["received_ms"] > t1:
            continue
        j = m.get("json") or {}
        if m["channel"].startswith("nlp:"):
            mpane = str(j.get("pane") or "")
            if pane and zsession and mpane and mpane not in (f"{zsession}:{pane}", str(pane)):
                continue
            state = j.get("state") or "?"
            at = M.ms(j.get("ts")) or m["received_ms"]
            frag.spans.append(M.Span(
                id=M.Ids.notify("nanoleaf", str(int(at))), kind="notify", component=frag.component("ext:nanoleaf", "Nanoleaf panels", "device"),
                name=f"nanoleaf {state}", summary=f"The Nanoleaf painter set pane {mpane or '?'} to {state}.",
                phase="async_after", t0=at, status="ok", sync=False,
                attrs={"channel": m["channel"], "pane": mpane, "state": state,
                       "attribution": "pane" if pane else "time-only"},
                evidence=["live-redis"]))
            n += 1
        elif m["channel"].startswith("asm:"):
            if j.get("scope") != scope:
                continue
            if have_stream:
                continue  # the stream snapshot is the better record (the asm collector reads ctx.live)
            at = j.get("at_ms") or m["received_ms"]
            key = stream_by_seq.get(str(j.get("seq"))) or f"{int(at)}-0"
            frag.spans.append(M.Span(
                id=M.Ids.asm(key), kind="state", component=frag.component("asm", "Agent State Machine", "store"),
                name=f"{j.get('from', '?')} → {j.get('to', '?')}",
                summary=f"ASM moved {scope} from {j.get('from', '?')} to {j.get('to', '?')} ({j.get('reason', '?')}).",
                phase="async_after", t0=float(at), status="ok", sync=False,
                attrs={k: j.get(k) for k in ("from", "to", "reason", "held_ms", "seq", "turn", "tools", "subs")},
                refs={"seq": j.get("seq")}, evidence=["live-redis"]))
            n += 1
    src.items = n
    src.status = "ok" if n else "empty"
    src.ms = round((time.monotonic() - started) * 1000.0, 1)
    return frag


# ---------------------------------------------------------------- record

def record(cli: str | None = None, settle_s: float = 15.0, timeout_s: float = 900.0, out: str | None = None,
           profile: str = "full", deep: bool = False, only: list[str] | None = None, skip: list[str] | None = None,
           argv: list[str] | None = None, say: Callable[[str], None] | None = None) -> str | None:
    """Returns the written waybill path, or None when no prompt arrived."""
    from . import cli as C
    say = say or (lambda s: print(s, file=sys.stderr, flush=True))
    armed_at = M.now_ms()
    live: dict[str, Any] = {"armed_at": armed_at, "prompt": None, "stop": None}
    nt, rt = NatsTap(), RedisTap()
    nats_ok = nt.start()
    redis_ok = rt.start()
    say(f"armed at {M.iso(armed_at)} · nats {'ok' if nats_ok else 'DOWN: ' + str(nt.error)} · "
        f"redis {'ok' if redis_ok else 'DOWN: ' + str(rt.error)}")
    say(f"waiting for the next {cli or 'claude/codex'} prompt (timeout {int(timeout_s)} s) …")
    deadline = time.monotonic() + timeout_s
    sid = inv = None
    prompt_ms = None
    use_cli = cli
    interrupted = False
    rejected: set[str] = set()
    stop: tuple[str, float] | None = None
    try:
        while time.monotonic() < deadline:
            got = prompt_after(armed_at, cli)
            if got:
                sid, inv, prompt_ms = got
                break
            time.sleep(POLL_S)
        if not sid:
            say("no prompt arrived before the timeout; nothing recorded")
            return None
        use_cli = cli or invocation_cli(inv) or "claude"
        live["prompt"] = {"session_id": sid, "invocation_id": inv, "received_ms": prompt_ms, "cli": use_cli}
        say(f"recording {use_cli} session {sid}… (prompt {inv} at {M.iso(prompt_ms)})")
        last_snap = 0.0
        while time.monotonic() < deadline:
            if time.monotonic() - last_snap >= SNAP_S:
                snapshot_state(use_cli, sid, live)
                last_snap = time.monotonic()
            stop = stop_after(sid, prompt_ms)
            if stop:
                break
            if ended_without_stop(sid, prompt_ms):
                rejected.add(sid)
                nxt = next_prompt_after(armed_at, cli, rejected)
                if nxt is None:
                    time.sleep(POLL_S)
                    continue
                say(f"session {sid} ended without a Stop (a helper session); following {nxt[0]} instead")
                sid, inv, prompt_ms = nxt
                use_cli = cli or invocation_cli(inv) or use_cli
                live["prompt"] = {"session_id": sid, "invocation_id": inv, "received_ms": prompt_ms, "cli": use_cli}
                continue
            time.sleep(POLL_S)
        if stop:
            live["stop"] = {"invocation_id": stop[0], "received_ms": stop[1]}
            say(f"Stop {stop[0]} at {M.iso(stop[1])} (+{(stop[1] - prompt_ms) / 1000:.1f} s); settling {settle_s:g} s …")
        else:
            say("turn did not reach Stop before the timeout; capturing it as open")
        settle_end = time.monotonic() + settle_s
        while time.monotonic() < settle_end:
            if time.monotonic() - last_snap >= SNAP_S:
                snapshot_state(use_cli, sid, live)
                last_snap = time.monotonic()
            time.sleep(POLL_S)
    except KeyboardInterrupt:
        interrupted = True
        say("interrupted: writing what was recorded so far")
    finally:
        nt.stop()
        rt.stop()
    if not sid:
        say("no prompt was seen; nothing recorded")
        return None
    try:
        if not interrupted:
            snapshot_state(use_cli, sid, live)
    except Exception:
        pass
    live["nats"] = [dict(m, envelope=_envelope(m["data"])) for m in nt.snapshot()
                    if m["received_ms"] >= (prompt_ms or armed_at) - 5000]
    live["redis"] = rt.snapshot()
    for k in ("capture",):
        if isinstance(live.get(k), dict):
            live[k].pop("_raw", None)
    end = M.now_ms()
    try:
        window, note = C.resolve_window(sid, use_cli, None, False, M.iso(prompt_ms), settle_s * 1000.0)
    except Exception as exc:
        say(f"window resolution failed ({type(exc).__name__}: {exc}); using the live bounds")
        window = M.TurnWindow(cli=use_cli, surface="claude-code" if use_cli == "claude" else "codex-cli",
                              session_id=sid, t0=prompt_ms or armed_at, t_end=end,
                              turn_end=stop[1] if stop else None, prompt_invocation_id=inv,
                              stop_invocation_id=stop[0] if stop else None, settle_ms=settle_s * 1000.0)
        note = None
    if not window.t_end or window.t_end < end - 1:
        window.t_end = max(window.t_end or 0.0, end)
    invs = set()
    try:
        invs = session_invocations(sid, window.t0, window.t_end)
    except Exception:
        pass
    frags = [nats_fragment(nt, sid, use_cli, invs, window.t0, window.t_end),
             redis_fragment(rt, sid, use_cli, live, window.t0, window.t_end)]
    say(f"live taps: {frags[0].source.items} bus events, {frags[1].source.items} redis signals; running collectors …")
    try:
        wb = C.run_pipeline(window, profile=profile, deep=deep, live=live, only=only, skip=skip, mode="record",
                            argv=argv, extra_fragments=frags, note=note, progress=say)
    except KeyboardInterrupt:
        say("interrupted during capture: assembling the live fragments only")
        from .assemble import assemble
        wb = assemble(window, frags, profile=profile, mode="record", argv=argv)
    path = C.write_waybill(wb, out)
    for line in C.summary_lines(wb):
        print(line)
    print(str(path))
    return str(path)
