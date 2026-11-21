"""The ground-truth adapters behind `waybill audit` (critic plan Step 6, SPEC section 2c).

Each adapter reads one source that knows what happened (the bus, a ledger, a database, a journal, transcript
files) and compares it with what Candystore archived. It returns audit `Row`s:

    (thing, expected_count, archived_count, verdict, evidence)

verdict is one of
    covered              everything the source saw became an event
    partial              some of it did (or the archive over-counts it)
    silent               it happened and no event exists at all
    lost-in-transit      it was emitted and the bus or the archive dropped it
    declared-never-seen  a schema or a registry surface promises it and it has never arrived

An adapter that cannot read its source raises `Skip(reason)`: the runner records a 'skipped' source with the
reason and the audit carries on. Everything here is read-only: sqlite opens `mode=ro`, Postgres runs with
`default_transaction_read_only` inside its own container (so no DSN leaves it), NATS is read with direct-get
and STREAM.INFO (no consumers are created, I-10.1).

The pure halves (`classify_*`, `seq_window`, `verdict`, ...) take plain data so tests/test_audit.py can feed
fixtures; the read halves are thin.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sqlite3
import subprocess
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from . import model as M
from .collectors import candystore as CS
from .night import PRIVATE_TYPES
from .registry import FIRST_PARTY_ROOT, Registry

VERDICTS = ("covered", "partial", "silent", "lost-in-transit", "declared-never-seen")
HOUR = 3600_000.0
DAY = 86400_000.0
NATS_URL = os.environ.get("WAYBILL_NATS_URL", "nats://127.0.0.1:4222")
EVENTS_STREAM, COMMANDS_STREAM, GIB_STREAM = "BLOODBANK_EVENTS", "BLOODBANK_COMMANDS", "GIB_EVENTS"
SCHEMAS_DIR = FIRST_PARTY_ROOT / "bloodbank" / "schemas"
POLICY_PATH = FIRST_PARTY_ROOT / "candybar" / "deploy" / "scheduling-policy.json"
RECEIPTS = Path("~/.local/state/33god/hook-hub/receipts.sqlite3").expanduser()
HERMES_PROFILES = Path("~/.hermes/profiles").expanduser()
CLAUDE_PROJECTS = Path("~/.claude/projects").expanduser()
CODEX_SESSIONS = Path("~/.codex/sessions").expanduser()
CRANK_SENDS = Path("~/.local/state/zcrank/sends.jsonl").expanduser()
CODE_ROOT = Path("~/code").expanduser()
CANDYBAR_CONTAINER = os.environ.get("WAYBILL_CANDYBAR_CONTAINER", "candybar")
LEDGER_CONTAINER = os.environ.get("WAYBILL_LEDGER_CONTAINER", "aai-llm-observability")
LITELLM_PG = os.environ.get("WAYBILL_LITELLM_PG", "jev-litellm-postgres")
# the usage exporter's own selection (monitoring/aai-llm-observability main.py FETCH_SQL): what it publishes
LEDGER_PREDICATE = ("type IN (2,5) AND (model_name LIKE 'automaticai/%' OR model_name LIKE 'aai/%' OR "
                    "(other LIKE '%\"automaticai_route\"%' AND other LIKE '%\"automaticai_account\"%') OR "
                    "(type = 2 AND channel_id > 0))")
NO_BOARD = "no board"


# ---------------------------------------------------------------- the row

@dataclass
class Row:
    source: str                     # adapter id
    thing: str                      # what was counted, in words
    component: str                  # who answers for it (registry id where there is one)
    expected: int | None            # what the source says happened (None: unknown)
    archived: int | None            # how many of those Candystore holds
    verdict: str
    evidence: str
    tickets: list[str] = field(default_factory=list)
    bound: str = ""                 # "≥" when expected is a lower bound
    exempt: str | None = None       # an approved exception (AD-22): shown, never counted by the done-condition
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if not d["detail"]:
            d.pop("detail")
        return d


class Skip(Exception):
    """The adapter's source is unreadable here; the reason is recorded and the audit carries on."""


def verdict(expected: int | None, archived: int | None, lost: bool = False, tolerance: float = 0.0) -> str:
    """expected 0 -> covered; nothing archived -> silent (lost-in-transit when it was emitted and dropped);
    archived >= expected (less the tolerance) -> covered; else partial (or lost-in-transit)."""
    if expected is None:
        return "covered" if archived else "silent"
    archived = archived or 0
    if expected <= 0:
        return "covered"
    if archived <= 0:
        return "lost-in-transit" if lost else "silent"
    if archived >= expected * (1.0 - tolerance):
        return "covered"
    return "lost-in-transit" if lost else "partial"


def is_private(t: str | None) -> bool:
    return bool(t) and str(t).startswith(PRIVATE_TYPES)


def short(t: str) -> str:
    return t[len("bloodbank."):] if t.startswith("bloodbank.") else t


def sample(items: Iterable[str], k: int = 3) -> str:
    xs = sorted(set(items))
    return ", ".join(xs[:k]) + (f" (+{len(xs) - k})" if len(xs) > k else "")


def iso_z(ms: float) -> str:
    return datetime.fromtimestamp(ms / 1000.0, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def parse_ts(s: str | None) -> float | None:
    """ISO 8601 (nanosecond fractions and a Z welcome) -> epoch ms."""
    if not s:
        return None
    s = str(s).strip().replace(" ", "T")
    m = re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?(Z|[+-]\d\d:?\d\d)?$", s)
    if not m:
        return None
    frac = (m.group(2) or ".0")[:7]
    tz = m.group(3) or "Z"
    tz = "+00:00" if tz == "Z" else (tz if ":" in tz else tz[:3] + ":" + tz[3:])
    try:
        return datetime.fromisoformat(m.group(1) + frac + tz).timestamp() * 1000.0
    except ValueError:
        return None


def q(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"


def uuid_array(ids: Iterable[str]) -> str:
    good = sorted({i for i in ids if CS.is_uuid(i)})
    return "array[" + ",".join(q(x) for x in good) + "]::uuid[]" if good else "array[]::uuid[]"


def text_array(xs: Iterable[str]) -> str:
    xs = sorted({str(x) for x in xs if x is not None})
    return "array[" + ",".join(q(x) for x in xs) + "]::text[]" if xs else "array[]::text[]"


# ---------------------------------------------------------------- read seams

# runs inside a container that holds the DSN in its environment: SQL on stdin, one JSON value on stdout
_INPG = (
    "import json, os, sys\nimport psycopg\n"
    "dsn = os.environ[sys.argv[1]].replace('postgresql+psycopg://', 'postgresql://')\n"
    "with psycopg.connect(dsn, options='-c default_transaction_read_only=on -c statement_timeout=120000',"
    " connect_timeout=10) as con:\n"
    "    with con.cursor() as cur:\n        cur.execute(sys.stdin.read())\n        print(json.dumps(cur.fetchone()[0], default=str))\n"
)


def container_json(container: str, env_var: str, sql: str, timeout: float = 150.0) -> Any:
    """One read-only statement returning one JSON value, run by psycopg inside `container` with the DSN in
    `env_var` there. The DSN never leaves the container."""
    try:
        p = subprocess.run(["docker", "exec", "-i", container, "python3", "-c", _INPG, env_var], input=sql,
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Skip(f"{container}: {type(exc).__name__}") from exc
    if p.returncode != 0:
        tail = (p.stderr or p.stdout).strip().splitlines()
        raise Skip(f"{container}: {tail[-1][:200] if tail else f'exit {p.returncode}'}")
    out = p.stdout.strip()
    return json.loads(out.splitlines()[-1]) if out else None


def container_psql(container: str, sql: str, timeout: float = 120.0) -> Any:
    """Same, through the container's own psql and its POSTGRES_USER (Postgres images without python)."""
    argv = ["docker", "exec", "-i", container, "sh", "-c",
            'psql -X -q -A -t -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "${POSTGRES_DB:-$POSTGRES_USER}" -f -']
    try:
        p = subprocess.run(argv, input="set default_transaction_read_only = on;\n" + sql + "\n",
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Skip(f"{container}: {type(exc).__name__}") from exc
    if p.returncode != 0:
        tail = (p.stderr or p.stdout).strip().splitlines()
        raise Skip(f"{container}: {tail[-1][:200] if tail else f'exit {p.returncode}'}")
    out = p.stdout.strip()
    return json.loads(out) if out else None


class Archive:
    """Candystore, read-only, every statement bounded by `time` (idx_events_time / idx_events_type_time) or
    by primary key. events has no received_at index (CANDYS-55), so nothing here filters on it alone."""

    def __init__(self, timeout: float = 300.0, run: Callable[[str, float], Any] | None = None):
        self.timeout = timeout
        self._run = run or CS.psql_json

    def json(self, sql: str) -> Any:
        return self._run(sql, self.timeout)

    def present(self, ids: Iterable[str]) -> set[str]:
        """Which of these event ids Candystore holds (any time), by primary key in batches of 500."""
        good = sorted({i for i in ids if CS.is_uuid(i)})
        out: set[str] = set()
        for i in range(0, len(good), 500):
            got = self.json(f"select coalesce(json_agg(id::text), '[]'::json) from events where id = any({uuid_array(good[i:i + 500])});")
            out.update(got or [])
        return out

    def keys(self, types: Iterable[str], key_sql: str, lo: float, hi: float, extra: str = "") -> set[str]:
        """Distinct values of key_sql over events of these types in [lo, hi) (envelope time)."""
        types = sorted(set(types))
        if not types:
            return set()
        got = self.json(f"select coalesce(json_agg(distinct k), '[]'::json) from (select {key_sql} as k from events"
                        f" where type = any({text_array(types)}) and time >= {q(M.iso(lo))}::timestamptz"
                        f" and time < {q(M.iso(hi))}::timestamptz{extra}) x where k is not null;")
        return set(got or [])


@dataclass
class Ctx:
    since: float                         # epoch ms, inclusive
    until: float                         # epoch ms, exclusive
    registry: Registry
    archive: Archive
    rows: list = field(default_factory=list)        # query.Row of the window (the query waybill's own read)
    dead: list[dict] = field(default_factory=list)  # dead letters of the window (query.PsqlReader.dead_letters)
    public: bool = True
    home: Path = field(default_factory=Path.home)
    _ids: set[str] | None = None
    _types: Counter | None = None
    _producers: Counter | None = None

    @property
    def days(self) -> float:
        return (self.until - self.since) / DAY

    @property
    def ids(self) -> set[str]:
        if self._ids is None:
            self._ids = {r.id for r in self.rows}
        return self._ids

    @property
    def types(self) -> Counter:
        if self._types is None:
            self._types = Counter(r.type for r in self.rows)
        return self._types

    @property
    def producers(self) -> Counter:
        if self._producers is None:
            self._producers = Counter(r.producer for r in self.rows)
        return self._producers

    def count_types(self, pred: Callable[[str], bool]) -> int:
        return sum(n for t, n in self.types.items() if pred(t))

    def archived_ids(self, ids: Iterable[str]) -> set[str]:
        """Which ids Candystore holds: the window first, then by primary key."""
        ids = set(ids)
        hit = ids & self.ids
        rest = ids - hit
        return hit | (self.archive.present(rest) if rest else set())

    def loc(self, full: str, public: str) -> str:
        """A source locator: the path on the full profile, a generic name on the public one."""
        return public if self.public else full


# ---------------------------------------------------------------- 1. the bus (JetStream) vs the archive, by id

@dataclass
class BusMsg:
    seq: int
    subject: str
    id: str | None
    t: float            # JetStream timestamp, epoch ms


def bus_msg(headers: dict | None, data: bytes) -> BusMsg | None:
    """A direct-get reply -> BusMsg (None for a 404 / no message). The id is Nats-Msg-Id, else the body's id."""
    h = headers or {}
    if h.get("Status") or not h.get("Nats-Sequence"):
        return None
    mid = h.get("Nats-Msg-Id")
    if not mid:
        try:
            mid = (json.loads(data) or {}).get("id")
        except (ValueError, AttributeError, UnicodeDecodeError):
            mid = None
    return BusMsg(int(h["Nats-Sequence"]), h.get("Nats-Subject", ""), str(mid) if mid else None,
                  parse_ts(h.get("Nats-Time-Stamp")) or 0.0)


def subject_match(pattern: str, subject: str) -> bool:
    """NATS subject wildcards: `*` one token, `>` the rest (at least one token)."""
    p, s = pattern.split("."), subject.split(".")
    for i, tok in enumerate(p):
        if tok == ">":
            return len(s) > i
        if i >= len(s) or (tok != "*" and tok != s[i]):
            return False
    return len(p) == len(s)


def classify_bus(msgs: Iterable[BusMsg], archived: set[str], dead_ids: set[str], dead_raw: list[str]) -> dict[str, Counter]:
    """Every message in the window, by id: archived, a duplicate of one already counted, dead-lettered, or
    missing (no id, or an id nobody holds). Per subject: msgs == archived + dup + dead + missing."""
    per: dict[str, Counter] = defaultdict(Counter)
    seen: set[str] = set()
    for m in msgs:
        c = per[m.subject]
        c["msgs"] += 1
        if not m.id:
            c["missing"] += 1
            c["no_id"] += 1
            continue
        if m.id in seen:
            c["dup"] += 1
            continue
        seen.add(m.id)
        if m.id in archived:
            c["archived"] += 1
        elif m.id in dead_ids or any(m.id in r for r in dead_raw):
            c["dead"] += 1
        else:
            c["missing"] += 1
    return per


def missing_ids(msgs: Iterable[BusMsg], archived: set[str], dead_ids: set[str], dead_raw: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for m in msgs:
        if m.id and m.id not in archived and m.id not in dead_ids and not any(m.id in r for r in dead_raw):
            out[m.subject].append(m.id)
    return out


def command_bounds(lo_since: int, first_since: int | None, lo_until: int, first_until: int) -> tuple[int, int]:
    """Commands published in the window, from a workqueue that deleted most of them. lo_* = one past the last
    retained message before the instant, first_* = the first retained one at or after it. Every sequence in
    [first_since, lo_until) was assigned inside the window (lower bound); every one inside it lies in
    [lo_since, first_until) (upper bound)."""
    lower = max(0, lo_until - first_since) if first_since is not None and first_since < lo_until else 0
    return lower, max(lower, first_until - lo_since)


class NatsBus:
    """JetStream through direct-get and STREAM.INFO / CONSUMER.LIST only: it never creates a consumer."""

    def __init__(self, url: str = NATS_URL, chunk: int = 1000, timeout: float = 20.0):
        self.url, self.chunk, self.timeout = url, chunk, timeout
        self.nc = None
        self.gets = 0

    async def open(self) -> "NatsBus":
        try:
            import nats  # noqa: PLC0415
        except ImportError as exc:
            raise Skip("nats-py is not installed in this interpreter (set WAYBILL_PYTHON)") from exc
        try:
            self.nc = await nats.connect(self.url, name="waybill-audit", allow_reconnect=False, connect_timeout=5)
        except Exception as exc:  # noqa: BLE001
            raise Skip(f"NATS unreachable: {type(exc).__name__}") from exc
        return self

    async def close(self) -> None:
        if self.nc:
            await self.nc.close()

    async def api(self, subject: str, body: dict) -> dict:
        r = await self.nc.request(subject, json.dumps(body).encode(), timeout=self.timeout)
        d = json.loads(r.data or b"{}")
        if d.get("error"):
            raise RuntimeError(f"{subject}: {d['error'].get('description', d['error'])}")
        return d

    async def info(self, stream: str, subjects: bool = False) -> dict:
        body: dict[str, Any] = {"subjects_filter": ">"} if subjects else {}
        d = await self.api(f"$JS.API.STREAM.INFO.{stream}", body)
        if subjects:
            subs = dict((d.get("state") or {}).get("subjects") or {})
            total = int(d.get("total") or len(subs))
            while len(subs) < total:
                more = await self.api(f"$JS.API.STREAM.INFO.{stream}", {**body, "offset": len(subs)})
                got = (more.get("state") or {}).get("subjects") or {}
                if not got:
                    break
                subs.update(got)
            d.setdefault("state", {})["subjects"] = subs
        return d

    async def get(self, stream: str, seq: int, next_: bool = False) -> BusMsg | None:
        body: dict[str, Any] = {"seq": int(seq)}
        if next_:
            body["next_by_subj"] = ">"
        r = await self.nc.request(f"$JS.API.DIRECT.GET.{stream}", json.dumps(body).encode(), timeout=self.timeout)
        self.gets += 1
        return bus_msg(r.headers, r.data)

    async def seq_at(self, stream: str, t: float, first: int, last: int) -> int:
        """One past the last retained message stamped before t (first when there is none)."""
        lo, hi = first, last + 1
        while lo < hi:
            mid = (lo + hi) // 2
            m = await self.get(stream, mid, next_=True)
            if m is None or m.t >= t:
                hi = mid
            else:
                lo = m.seq + 1
        return lo

    async def window(self, stream: str, s1: int, s2: int) -> list[BusMsg]:
        import asyncio  # noqa: PLC0415
        out: list[BusMsg] = []
        for c in range(s1, s2, self.chunk):
            got = await asyncio.gather(*[self.get(stream, s) for s in range(c, min(s2, c + self.chunk))])
            out.extend(m for m in got if m is not None)
        return out

    async def consumers(self, stream: str) -> list[dict]:
        out: list[dict] = []
        while True:
            d = await self.api(f"$JS.API.CONSUMER.LIST.{stream}", {"offset": len(out)})
            got = d.get("consumers") or []
            out.extend(got)
            if not got or len(out) >= int(d.get("total") or 0):
                return out


def consumer_filters(consumers: list[dict]) -> list[str]:
    out: list[str] = []
    for c in consumers:
        cfg = c.get("config") or {}
        fs = cfg.get("filter_subjects") or ([cfg["filter_subject"]] if cfg.get("filter_subject") else [">"])
        out.extend(fs)
    return out


def command_types() -> set[str]:
    """Types the Bloodbank schemas declare as commands (kind const 'command')."""
    return {t for t, k in declared_types().items() if k == "command"}


_DECLARED: dict[str, str] | None = None


def declared_types(root: Path = SCHEMAS_DIR) -> dict[str, str]:
    """type -> kind ('event' | 'command') from every Bloodbank schema with a `type` const."""
    global _DECLARED
    if _DECLARED is not None and root == SCHEMAS_DIR:
        return _DECLARED
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*.json")) if root.is_dir() else []:
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        props = s.get("properties") if isinstance(s, dict) else None
        t = ((props or {}).get("type") or {}).get("const") if isinstance(props, dict) else None
        if isinstance(t, str):
            k = ((props or {}).get("kind") or {}).get("const")
            out.setdefault(t, k if k in ("event", "command") else "event")
    if root == SCHEMAS_DIR:
        _DECLARED = out
    return out


def _dead_raw(ctx: Ctx, extra: list[dict]) -> tuple[set[str], list[str]]:
    ids, raws = set(), []
    for d in [*ctx.dead, *extra]:
        if d.get("event_id"):
            ids.add(str(d["event_id"]))
        try:
            raws.append(base64.b64decode(d.get("raw_b64") or "").decode("utf-8", "replace"))
        except (ValueError, TypeError):
            pass
    return ids, raws


def _nearby_dead(ctx: Ctx) -> list[dict]:
    """Dead letters an hour either side of the window: a message near the edge may die just outside it."""
    lo, hi = M.iso(ctx.since - HOUR), M.iso(ctx.until + HOUR)
    a, b = M.iso(ctx.since), M.iso(ctx.until)
    return ctx.archive.json(
        "select coalesce(json_agg(json_build_object('event_id', event_id, 'raw_b64', encode(raw, 'base64'))), '[]'::json)"
        f" from dead_letter where ((received_at >= {q(lo)}::timestamptz and received_at < {q(a)}::timestamptz)"
        f" or (received_at >= {q(b)}::timestamptz and received_at < {q(hi)}::timestamptz)) and reason <> 'nul-sanitized';") or []


def adapter_bus(ctx: Ctx, bus_factory: Callable[[], NatsBus] = NatsBus) -> list[Row]:
    import asyncio  # noqa: PLC0415

    async def read() -> dict:
        bus = await bus_factory().open()
        try:
            out: dict[str, Any] = {}
            ev = await bus.info(EVENTS_STREAM, subjects=True)
            st = ev["state"]
            s1 = await bus.seq_at(EVENTS_STREAM, ctx.since, st["first_seq"], st["last_seq"])
            s2 = await bus.seq_at(EVENTS_STREAM, ctx.until, st["first_seq"], st["last_seq"])
            out["events"] = {"first": st["first_seq"], "last": st["last_seq"], "s1": s1, "s2": s2,
                             "subjects": len(st.get("subjects") or {}), "msgs": await bus.window(EVENTS_STREAM, s1, s2)}
            try:
                cm = await bus.info(COMMANDS_STREAM, subjects=True)
                cs = cm["state"]
                f, l_ = cs["first_seq"], cs["last_seq"]
                lo_s = await bus.seq_at(COMMANDS_STREAM, ctx.since, f, l_)
                lo_u = await bus.seq_at(COMMANDS_STREAM, ctx.until, f, l_)
                fs = await bus.get(COMMANDS_STREAM, lo_s, next_=True)
                fu = await bus.get(COMMANDS_STREAM, lo_u, next_=True)
                out["commands"] = {"first": f, "last": l_, "retained": cs.get("subjects") or {},
                                   "bounds": command_bounds(lo_s, fs.seq if fs else None, lo_u, fu.seq if fu else l_ + 1),
                                   "filters": consumer_filters(await bus.consumers(COMMANDS_STREAM)),
                                   "retention": (cm.get("config") or {}).get("retention")}
            except Exception as exc:  # noqa: BLE001
                out["commands_error"] = f"{type(exc).__name__}: {exc}"
            try:
                gb = await bus.info(GIB_STREAM)
                gs = gb["state"]
                g1 = await bus.seq_at(GIB_STREAM, ctx.since, gs["first_seq"], gs["last_seq"])
                g2 = await bus.seq_at(GIB_STREAM, ctx.until, gs["first_seq"], gs["last_seq"])
                out["gib"] = {"msgs": await bus.window(GIB_STREAM, g1, g2), "consumers": gs.get("consumer_count", 0)}
            except Exception as exc:  # noqa: BLE001
                out["gib_error"] = f"{type(exc).__name__}: {exc}"
            out["gets"] = bus.gets
            return out
        finally:
            await bus.close()

    got = asyncio.run(read())
    ev = got["events"]
    msgs: list[BusMsg] = ev["msgs"]
    ids = {m.id for m in msgs if m.id}
    archived = ctx.archived_ids(ids)
    dead_ids, dead_raw = _dead_raw(ctx, _nearby_dead(ctx))
    per = classify_bus(msgs, archived, dead_ids, dead_raw)
    miss = missing_ids(msgs, archived, dead_ids, dead_raw)
    tot = Counter()
    for c in per.values():
        tot.update({k: v for k, v in c.items() if isinstance(v, int)})
    # archived in the window but never on the bus inside it (HTTP / other ingest), received well inside it
    sub_of: dict[str, Counter] = defaultdict(Counter)
    by_id = {r.id: r for r in ctx.rows}
    for m in msgs:
        r = by_id.get(m.id or "")
        if r:
            sub_of[r.type][m.subject] += 1
    only: Counter = Counter()
    for r in ctx.rows:
        if r.id not in ids and r.ra is not None and ctx.since + 60_000 <= r.ra < ctx.until - 60_000:
            only[sub_of[r.type].most_common(1)[0][0] if sub_of.get(r.type) else "(no bus subject)"] += 1
    subjects = {}
    for s, c in sorted(per.items()):
        subjects[s] = {k: int(c.get(k, 0)) for k in ("msgs", "archived", "dup", "dead", "missing", "no_id")}
        subjects[s]["archive_only"] = int(only.get(s, 0))
    for s, n in only.items():
        subjects.setdefault(s, {k: 0 for k in ("msgs", "archived", "dup", "dead", "missing", "no_id")})["archive_only"] = int(n)
    unique = tot["msgs"] - tot["dup"]
    no_id = f" ({tot['no_id']} without an id)" if tot["no_id"] else ""
    rows = [Row("bus", f"{EVENTS_STREAM} messages -> Candystore ids", "bloodbank", unique, tot["archived"],
                verdict(unique, tot["archived"], lost=bool(tot["dead"] or tot["missing"])),
                f"seq {ev['s1']}..{ev['s2'] - 1} ({tot['msgs']} msgs, {len(per)} subjects): archived {tot['archived']},"
                f" duplicate {tot['dup']}, dead-lettered {tot['dead']}, missing {tot['missing']}{no_id};"
                f" archived without a bus message {sum(only.values())}",
                detail={"seq": [ev["s1"], ev["s2"]], "stream": [ev["first"], ev["last"]], "gets": got.get("gets", 0),
                        "subjects": subjects, "stream_subjects": ev["subjects"]})]
    for s, xs in sorted(miss.items(), key=lambda kv: -len(kv[1])):
        name = "a private subject" if is_private("bloodbank." + s.split(".evt.", 1)[-1]) else s
        c = per[s]
        rows.append(Row("bus", f"bus subject {name}", "bloodbank", c["msgs"] - c["dup"], c["archived"], "lost-in-transit",
                        f"{len(xs)} id(s) on the bus that neither Candystore nor a dead letter holds: {sample(xs)}"))
    if "commands" in got:
        cm = got["commands"]
        lower, upper = cm["bounds"]
        ctypes = command_types()
        arch = ctx.count_types(lambda t: t in ctypes)
        # no retained command inside the window gives no lower bound: say "?" and let the upper bound speak
        exp = lower if lower or not upper else None
        rows.append(Row("bus", f"{COMMANDS_STREAM} commands -> Candystore", "bloodbank", exp, arch,
                        verdict(exp, arch), f"{cm.get('retention')} stream: at least {lower}, at most {upper} commands"
                        f" in the window; acked commands are deleted, so the bus cannot be replayed; {arch} archived",
                        tickets=["BB-48"], bound="≥" if exp else "", detail={"bounds": [lower, upper]}))
        for subj, n in sorted(cm["retained"].items(), key=lambda kv: -kv[1]):
            if not any(subject_match(f, subj) for f in cm["filters"]):
                rows.append(Row("bus", f"stranded command {subj}", "bloodbank", int(n), 0, "lost-in-transit",
                                f"{n} retained command(s) and no consumer filter matches {subj}; the workqueue expires them",
                                tickets=["BB-49"] if "audio.task.start" in subj else []))
    elif got.get("commands_error"):
        rows.append(Row("bus", f"{COMMANDS_STREAM} commands", "bloodbank", None, None, "silent",
                        f"could not read the stream: {got['commands_error']}", tickets=["BB-48"]))
    if "gib" in got:
        gm = got["gib"]["msgs"]
        gids = {m.id for m in gm if m.id}
        garch = ctx.archived_ids(gids)
        rows.append(Row("bus", f"{GIB_STREAM} messages -> Candystore", "candystore", len(gids), len(garch & gids),
                        verdict(len(gids), len(garch & gids)),
                        f"{len(gm)} msgs in the window, {got['gib']['consumers']} consumer(s) on the stream; Candystore subscribes"
                        " to bloodbank.evt.> only", tickets=["CANDYS-80"]))
    return rows


# ---------------------------------------------------------------- 2. Candybar runs vs cron.candybar.*

def _win(ctx: Ctx, col: str) -> str:
    return f"{col} >= {q(M.iso(ctx.since))}::timestamptz and {col} < {q(M.iso(ctx.until))}::timestamptz"


def classify_candybar(db: dict, invoked: set[str], finished: set[str], types: Counter, minutes: int) -> list[Row]:
    inv = db.get("inv") or []
    ids = {r[0] for r in inv}
    done = {r[0] for r in inv if r[2]}
    hit, fin = ids & invoked, done & finished
    steward_t = sum(n for t, n in types.items() if ".steward." in t)
    rows = [
        Row("candybar", "Candybar runs -> cron.candybar.invoked", "candybar", len(ids), len(hit), verdict(len(ids), len(hit)),
            f"{len(ids)} invocation rows in the window; {len(ids - hit)} without an invoked event"
            + (f": {sample(ids - hit)}" if ids - hit else "")),
        Row("candybar", "Candybar finished runs -> completed | failed", "candybar", len(done), len(fin), verdict(len(done), len(fin)),
            f"{len(done)} finished ({fmt_counts(Counter(r[1] or 'unfinished' for r in inv), 3)}); {len(done - fin)} without an outcome event"),
        Row("candybar", "candybars created -> cron.candybar.created", "candybar", int(db.get("created") or 0),
            types.get("bloodbank.cron.candybar.created", 0),
            verdict(int(db.get("created") or 0), types.get("bloodbank.cron.candybar.created", 0)), "candybars.created_at in the window"),
        Row("candybar", "scheduler minutes -> cron.tick.fired", "candybar", minutes, types.get("bloodbank.cron.tick.fired", 0),
            verdict(minutes, types.get("bloodbank.cron.tick.fired", 0), tolerance=0.01), "one tick per minute of the window"),
        Row("candybar", "occurrence skips -> cron.candybar.skipped", "candybar", int(db.get("skips") or 0),
            types.get("bloodbank.cron.candybar.skipped", 0),
            verdict(int(db.get("skips") or 0), types.get("bloodbank.cron.candybar.skipped", 0)),
            f"the database keeps occurrence skips only; {types.get('bloodbank.cron.candybar.skipped', 0)} skipped events archived"
            " (overlap skips included)"),
    ]
    if db.get("steward"):
        rows.append(Row("candybar", "steward tasks -> steward events", "candybar-steward", int(db["steward"]), steward_t,
                        verdict(int(db["steward"]), steward_t), "steward_tasks.created_at in the window"))
    return rows


def adapter_candybar(ctx: Ctx) -> list[Row]:
    db = container_json(CANDYBAR_CONTAINER, "DATABASE_URL",
                        "select json_build_object("
                        "'inv', (select coalesce(json_agg(json_build_array(id::text, result, finished_at is not null)), '[]'::json)"
                        f" from invocations where {_win(ctx, 'created_at')}),"
                        f" 'created', (select count(*) from candybars where {_win(ctx, 'created_at')}),"
                        f" 'skips', (select count(*) from skips where {_win(ctx, 'created_at')}),"
                        f" 'steward', (select count(*) from steward_tasks where {_win(ctx, 'created_at')}))") or {}
    lo, hi = ctx.since - HOUR, ctx.until + HOUR
    invoked = ctx.archive.keys(["bloodbank.cron.candybar.invoked"], "data->>'invocation_id'", lo, hi)
    finished = ctx.archive.keys(["bloodbank.cron.candybar.completed", "bloodbank.cron.candybar.failed"],
                                "data->>'invocation_id'", lo, hi)
    return classify_candybar(db, invoked, finished, ctx.types, int(round(ctx.days * 1440)))


# ---------------------------------------------------------------- 3. hook-hub receipts vs hook.updated and agent events

def read_receipts(path: Path, since: float, until: float) -> dict:
    if not path.exists():
        raise Skip("hook-hub receipts database not found")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
    try:
        n = con.execute("select count(*) from invocations").fetchone()[0]
        if not n:
            raise Skip("hook-hub receipts database is empty")
        # retention start: skip the first half-percent (a handful of stragglers survive the prune)
        start = con.execute("select received_at from invocations order by received_at limit 1 offset ?", (n // 200,)).fetchone()[0]
        lo, hi = max(iso_z(since), start), iso_z(until)
        if lo >= hi:
            raise Skip(f"hook-hub keeps receipts only since {start}")
        inv = [r[0] for r in con.execute("select invocation_id from invocations where received_at >= ? and received_at < ?", (lo, hi))]
        pubs = con.execute("select e.event_id, e.event_type from executions e join invocations i using (invocation_id)"
                           " where i.received_at >= ? and i.received_at < ? and e.handler_id = 'bloodbank-publisher'"
                           " and e.publish_status = 'sent' and e.event_id is not null", (lo, hi)).fetchall()
        skips = dict(con.execute("select coalesce(e.reason, ''), count(*) from executions e join invocations i using (invocation_id)"
                                 " where i.received_at >= ? and i.received_at < ? and e.handler_id = 'bloodbank-publisher'"
                                 " and e.status = 'skipped' group by 1", (lo, hi)).fetchall())
        return {"start": start, "lo": lo, "clipped": lo > iso_z(since), "inv": inv, "pubs": pubs, "skips": skips}
    finally:
        con.close()


def classify_hookhub(rec: dict, mirrors: set[str], archived: set[str]) -> list[Row]:
    inv = set(rec["inv"])
    clip = f"; receipts kept since {rec['start'][:16]}Z, window clipped to {rec['lo'][:16]}Z" if rec.get("clipped") else ""
    bb = {i for i, t in rec["pubs"] if not str(t or "").startswith("deckard.")}
    dk = {i for i, t in rec["pubs"] if str(t or "").startswith("deckard.")}
    skips = dict(rec.get("skips") or {})
    pane = int(skips.pop("missing_pane_context", 0))
    rows = [Row("hookhub", "hook invocations -> agent.hook.updated", "hook-hub", len(inv), len(inv & mirrors),
                verdict(len(inv), len(inv & mirrors)), f"{len(inv)} receipts in the window{clip}"),
            Row("hookhub", "hook publishes (bloodbank.*) -> Candystore ids", "agent-hooks", len(bb), len(bb & archived),
                verdict(len(bb), len(bb & archived), lost=True),
                f"publisher receipts marked sent; {len(bb - archived)} id(s) not archived"
                + (f": {sample(bb - archived)}" if bb - archived else "")
                + (f"; other skips {sorted(skips.items())}" if skips else ""))]
    if dk:
        rows.append(Row("hookhub", "Deckard attention sends -> Candystore", "deckard", len(dk), len(dk & archived),
                        verdict(len(dk), len(dk & archived), lost=True),
                        "sent on core NATS as deckard.v1.* only; no JetStream copy, so nothing can archive them",
                        tickets=["BB-47"]))
    if pane:
        rows.append(Row("hookhub", "publisher skips (missing_pane_context)", "agent-hooks", pane, 0, "partial",
                        "the hook ran and was mirrored, but its agent event was never published", tickets=["BB-52"]))
    return rows


def adapter_hookhub(ctx: Ctx, path: Path = RECEIPTS) -> list[Row]:
    rec = read_receipts(path, ctx.since, ctx.until)
    lo = parse_ts(rec["lo"]) or ctx.since
    mirrors = ctx.archive.keys(["bloodbank.agent.hook.updated"], "data->'invocation'->>'invocation_id'", lo - HOUR, ctx.until + HOUR)
    archived = ctx.archived_ids(i for i, _ in rec["pubs"])
    return classify_hookhub(rec, mirrors, archived)


# ---------------------------------------------------------------- 4. gateway usage ledger vs llm.usage.recorded

def adapter_gateway(ctx: Ctx) -> list[Row]:
    rows: list[Row] = []
    ids = container_json(LEDGER_CONTAINER, "AAI_LLM_DATABASE_URL",
                         f"select coalesce(json_agg(id), '[]'::json) from logs where created_at >= {int(ctx.since // 1000)}"
                         f" and created_at < {int(ctx.until // 1000)} and ({LEDGER_PREDICATE})") or []
    want = {f"newapi-log:{i}" for i in ids}
    t = ["bloodbank.llm.usage.recorded"]
    got = ctx.archive.keys(t, "data->>'usage_id'", ctx.since - HOUR, ctx.until + HOUR) & want
    rest = want - got
    if rest:   # a backfill can publish a day late: look a day either side, only for these ids
        got |= ctx.archive.keys(t, "data->>'usage_id'", ctx.since - DAY, ctx.until + DAY,
                                extra=f" and data->>'usage_id' = any({text_array(rest)})")
    rows.append(Row("gateway", "gateway usage ledger -> llm.usage.recorded", "aai-gateway", len(want), len(want & got),
                    verdict(len(want), len(want & got)),
                    f"ledger rows the usage exporter selects; {len(want - got)} without an event"
                    + (f": {sample(want - got)}" if want - got else "")))
    try:
        n = int(container_psql(LITELLM_PG, "select to_json(count(*)) from \"LiteLLM_SpendLogs\" where \"startTime\" >= "
                               f"{q(iso_z(ctx.since)[:-1].replace('T', ' '))} and \"startTime\" < {q(iso_z(ctx.until)[:-1].replace('T', ' '))};") or 0)
        arch = sum(c for p, c in ctx.producers.items() if "jev-litellm" in p)
        rows.append(Row("gateway", "jev-litellm spend logs -> any event", "jev-litellm", n, arch, verdict(n, arch),
                        "LiteLLM_SpendLogs rows in the window; the proxy publishes nothing to Bloodbank", tickets=[NO_BOARD]))
    except Skip as exc:
        rows.append(Row("gateway", "jev-litellm spend logs", "jev-litellm", None, None, "silent", f"unreadable: {exc}",
                        tickets=[NO_BOARD]))
    return rows


def fmt_counts(c: Counter | dict, k: int = 4) -> str:
    items = c.most_common(k) if isinstance(c, Counter) else sorted(c.items(), key=lambda kv: -kv[1])[:k]
    return ", ".join(f"{a} {b}" for a, b in items) or "none"


# ---------------------------------------------------------------- 5. Claude / Codex transcripts vs session.started

def claude_sessions(root: Path, since: float, until: float) -> list[dict]:
    """Top-level Claude Code transcripts that started in the window: {sid, t, entrypoint}."""
    out = []
    for p in root.glob("*/*.jsonl") if root.is_dir() else []:
        try:
            if p.stat().st_mtime * 1000.0 < since:
                continue
            sid = t = ep = None
            with p.open(encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh):
                    if i > 60:
                        break
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(o, dict):
                        continue
                    sid = sid or o.get("sessionId")
                    t = t or parse_ts(o.get("timestamp"))
                    ep = ep or o.get("entrypoint")
                    if sid and t and ep:
                        break
        except OSError:
            continue
        if sid and t and since <= t < until:
            out.append({"sid": str(sid), "t": t, "entrypoint": ep or "cli"})
    return out


def codex_sessions(root: Path, since: float, until: float) -> list[dict]:
    out = []
    d0 = datetime.fromtimestamp(since / 1000.0 - 86400, timezone.utc).date()
    d1 = datetime.fromtimestamp(until / 1000.0 + 86400, timezone.utc).date()
    day = d0
    from datetime import timedelta  # noqa: PLC0415
    while day <= d1:
        for p in (root / f"{day:%Y/%m/%d}").glob("rollout-*.jsonl"):
            try:
                with p.open(encoding="utf-8", errors="replace") as fh:
                    o = json.loads(fh.readline() or "{}")
            except (OSError, ValueError):
                continue
            pl = o.get("payload") or {}
            t = parse_ts(pl.get("timestamp") or o.get("timestamp"))
            if o.get("type") == "session_meta" and pl.get("id") and t and since <= t < until:
                out.append({"sid": str(pl["id"]), "t": t, "originator": pl.get("originator") or "codex"})
        day += timedelta(days=1)
    return out


def classify_sessions(label: str, cli: str, sess: list[dict], started: set[str], any_event: set[str],
                      tickets: list[str], kinds: str = "") -> Row:
    ids = {s["sid"] for s in sess}
    hit = ids & started
    miss = ids - hit
    other = {s for s in miss if CS.correlation_id(cli, s) in any_event}
    return Row("transcripts", label, "agent-hooks", len(ids), len(hit), verdict(len(ids), len(hit)),
               f"{len(ids)} transcript(s) started in the window{kinds}; {len(miss)} without session.started"
               + (f" ({len(other)} of them have other events, {len(miss) - len(other)} have none)" if miss else ""),
               tickets=tickets)


def correlations_with_events(ctx: Ctx, corrs: Iterable[str]) -> set[str]:
    corrs = sorted({c for c in corrs if CS.is_uuid(c)})
    if not corrs:
        return set()
    lo, hi = q(M.iso(ctx.since - HOUR)), q(M.iso(ctx.until + DAY))
    return set(ctx.archive.json(
        f"select coalesce(json_agg(c::text), '[]'::json) from unnest({uuid_array(corrs)}) c where exists (select 1 from events e"
        f" where e.correlationid = c and e.time >= {lo}::timestamptz and e.time < {hi}::timestamptz);") or [])


def adapter_transcripts(ctx: Ctx, claude_root: Path = CLAUDE_PROJECTS, codex_root: Path = CODEX_SESSIONS) -> list[Row]:
    cl = claude_sessions(claude_root, ctx.since, ctx.until)
    cx = codex_sessions(codex_root, ctx.since, ctx.until)
    if not cl and not cx and not claude_root.is_dir() and not codex_root.is_dir():
        raise Skip("no Claude or Codex transcript directory on this machine")
    started = ctx.archive.keys(["bloodbank.agent.session.started"],
                               "coalesce(data->>'session_id', data->'payload'->>'session_id')", ctx.since - HOUR, ctx.until + HOUR)
    miss = [("claude-code", s["sid"]) for s in cl if s["sid"] not in started] + [("codex", s["sid"]) for s in cx if s["sid"] not in started]
    anyev = correlations_with_events(ctx, [CS.correlation_id(c, s) for c, s in miss])
    inter = [s for s in cl if s["entrypoint"] == "cli"]
    head = [s for s in cl if s["entrypoint"] != "cli"]
    return [classify_sessions("Claude Code interactive sessions -> session.started", "claude-code", inter, started, anyev, []),
            classify_sessions("Claude Code headless sessions (-p, SDK) -> session.started", "claude-code", head, started, anyev,
                              ["not yet ticketed"], f" ({fmt_counts(Counter(s['entrypoint'] for s in head))})"),
            classify_sessions("Codex sessions -> session.started", "codex", cx, started, anyev, [],
                              f" ({fmt_counts(Counter(s['originator'] for s in cx))})")]


# ---------------------------------------------------------------- 6. Hermes state.db vs the desks' events

def read_hermes(root: Path, since: float, until: float) -> dict:
    dbs = sorted(root.glob("*/state.db")) if root.is_dir() else []
    if not dbs:
        raise Skip("no Hermes profile state.db on this machine")
    s, u = since / 1000.0, until / 1000.0
    sess: list[tuple[str, str]] = []
    tools = tg = 0
    errors = 0
    for p in dbs:
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=5)
            try:
                sess += [(str(a), str(b or "unknown")) for a, b in con.execute(
                    "select id, source from sessions where started_at >= ? and started_at < ? and coalesce(message_count, 0) > 0", (s, u))]
                for (tc,) in con.execute("select tool_calls from messages where timestamp >= ? and timestamp < ?"
                                         " and tool_calls is not null and tool_calls not in ('', '[]', 'null')", (s, u)):
                    try:
                        v = json.loads(tc)
                        tools += len(v) if isinstance(v, list) else 1
                    except (ValueError, TypeError):
                        tools += 1
                tg += con.execute("select count(*) from messages m join sessions x on x.id = m.session_id where x.source = 'telegram'"
                                  " and m.role = 'user' and m.timestamp >= ? and m.timestamp < ?", (s, u)).fetchone()[0]
            finally:
                con.close()
        except sqlite3.Error:
            errors += 1
    return {"profiles": len(dbs), "errors": errors, "sessions": sess, "tools": tools, "tg": tg}


HERMES_PRODUCERS = "(producer like 'hermes-agent:%' or producer = 'hermes')"


def read_hermes_archive(ctx: Ctx) -> dict:
    lo, hi = q(M.iso(ctx.since - HOUR)), q(M.iso(ctx.until + HOUR))
    s, u = q(M.iso(ctx.since)), q(M.iso(ctx.until))
    key = "coalesce(data->>'session_id', data->'payload'->>'session_id')"
    return ctx.archive.json(
        "select json_build_object("
        f"'sessions', (select coalesce(json_agg(distinct k), '[]'::json) from (select {key} k from events where time >= {lo}::timestamptz"
        f" and time < {hi}::timestamptz and {HERMES_PRODUCERS}) x where k is not null),"
        f" 'started', (select coalesce(json_agg(distinct k), '[]'::json) from (select {key} k from events where type = 'bloodbank.agent.session.started'"
        f" and time >= {lo}::timestamptz and time < {hi}::timestamptz and {HERMES_PRODUCERS}) x where k is not null),"
        f" 'tools', (select count(*) from events where type = 'bloodbank.agent.tool.requested' and time >= {s}::timestamptz"
        f" and time < {u}::timestamptz and {HERMES_PRODUCERS}),"
        f" 'tg', (select count(*) from events where type = 'bloodbank.messaging.telegram.received' and time >= {s}::timestamptz"
        f" and time < {u}::timestamptz),"
        f" 'turns', (select count(*) from events where type = 'bloodbank.conversation.turn.started' and time >= {s}::timestamptz"
        f" and time < {u}::timestamptz and {HERMES_PRODUCERS}));") or {}


def classify_hermes(st: dict, ar: dict, public: bool = True) -> list[Row]:
    sess = st["sessions"]
    ids = {a for a, _ in sess}
    anyev, started = set(ar.get("sessions") or []), set(ar.get("started") or [])
    by_src = defaultdict(lambda: [0, 0])
    for a, src in sess:
        by_src[src][0] += 1
        by_src[src][1] += a in started
    srcs = ", ".join(f"{k} {v[1]}/{v[0]}" for k, v in sorted(by_src.items(), key=lambda kv: -kv[1][0]))
    tools, arch_t = int(st["tools"]), int(ar.get("tools") or 0)
    over = arch_t - tools
    tv = "partial" if tools and arch_t > tools * 1.05 else verdict(tools, arch_t, tolerance=0.05)
    note = f"{st['profiles']} profile(s)" + (f", {st['errors']} unreadable" if st["errors"] else "")
    msg = "inbound chat messages" if public else "Telegram user messages"
    return [
        Row("hermes", "Hermes sessions with messages -> any desk event", "hermes-fleet", len(ids), len(ids & anyev),
            verdict(len(ids), len(ids & anyev)), f"{note}; sessions started in the window", tickets=["BB-50"]),
        Row("hermes", "Hermes sessions -> session.started", "hermes-fleet", len(ids), len(ids & started),
            verdict(len(ids), len(ids & started)), f"by source (started/sessions): {srcs or 'none'}", tickets=["BB-50"]),
        Row("hermes", "Hermes tool calls -> tool.requested", "hermes-fleet", tools, arch_t, tv,
            f"assistant tool calls in state.db vs tool.requested from the desks: "
            + (f"over-count +{over} ({over * 100 // max(1, tools)}%)" if over > 0 else f"{-over} short"), tickets=["BB-50"]),
        Row("hermes", f"Hermes {msg} -> inbound message events", "hermes-fleet", int(st["tg"]), int(ar.get("tg") or 0),
            verdict(int(st["tg"]), int(ar.get("tg") or 0)), f"{int(ar.get('turns') or 0)} desk turn.started events in the window",
            tickets=["BB-50"]),
    ]


def adapter_hermes(ctx: Ctx, root: Path = HERMES_PROFILES) -> list[Row]:
    return classify_hermes(read_hermes(root, ctx.since, ctx.until), read_hermes_archive(ctx), ctx.public)


# ---------------------------------------------------------------- 7. systemd --user timers, failures, crash loops

JOURNAL_IDS = {
    "39f53479d3a045ac8e11786248231fbf": "done",          # started / finished (JOB_RESULT done)
    "be02cf6855d2428ba40df7e9d022f03d": "start_failed",  # failed to start (JOB_RESULT failed)
    "d9b373ed55a64feb8242e02dbe79a49c": "failed",        # "Failed with result"
    "5eb03494b6584870a536b337290809b3": "restart",       # restart scheduled
    "fe6faa94e7774663a0da52717891d8ef": "oom",           # the kernel OOM killer
    "d989611b15e44c9dbf31e3c81256e4ed": "oom",           # systemd-oomd
}
TIMER_TICKETS = {"asm-sweep.timer": ["BB-51"], "infra-doctor.timer": ["INFR-155"], "infra-doctor-deadman.timer": ["INFR-155"],
                 "hermes-gateway-watchdog.timer": ["INFR-155"]}
CRASH_LOOP = 100
CRASH_TICKETS = {"curator-serve.service": ["DOCS-2"], "delodocs-inbox-watchdog.service": ["DOCS-2"]}
UNIT_EVENT_PREFIXES = ("bloodbank.system.service.", "bloodbank.system.timer.", "bloodbank.system.unit.", "bloodbank.systemd.")


def parse_journal(lines: Iterable[str]) -> dict[str, Counter]:
    out: dict[str, Counter] = defaultdict(Counter)
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        k = JOURNAL_IDS.get(d.get("MESSAGE_ID") or "")
        u = d.get("USER_UNIT") or d.get("UNIT")
        if k and u:
            if isinstance(u, list):
                u = u[0]
            out[str(u)][k] += 1
    return out


def read_journal(since: float, until: float) -> dict[str, Counter]:
    argv = ["journalctl", "--user", "--since", f"@{since / 1000:.3f}", "--until", f"@{until / 1000:.3f}", "-o", "json",
            "--output-fields=MESSAGE_ID,USER_UNIT,UNIT,JOB_RESULT", "--no-pager", *[f"MESSAGE_ID={m}" for m in JOURNAL_IDS]]
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Skip(f"journalctl --user: {type(exc).__name__}") from exc
    if p.returncode != 0 and not p.stdout:
        raise Skip(f"journalctl --user exit {p.returncode}: {p.stderr.strip()[:160]}")
    return parse_journal(p.stdout.splitlines())


def read_timers() -> list[dict]:
    try:
        p = subprocess.run(["systemctl", "--user", "list-timers", "--all", "--no-pager", "--output=json"],
                           capture_output=True, text=True, timeout=30)
        return json.loads(p.stdout or "[]")
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise Skip(f"systemctl --user list-timers: {type(exc).__name__}") from exc


def read_policy(path: Path = POLICY_PATH) -> dict[str, dict]:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out = {}
    for e in d.get("exceptions") or []:
        i = str(e.get("id") or "")
        if i.startswith("systemd:user:"):
            out[i[len("systemd:user:"):]] = e
    return out


def unit_props(unit: str) -> dict[str, str]:
    try:
        p = subprocess.run(["systemctl", "--user", "show", "-p", "NRestarts,ActiveState,SubState,Result", unit],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    return dict(line.split("=", 1) for line in p.stdout.splitlines() if "=" in line)


def unit_component(reg: Registry, unit: str) -> str | None:
    base = re.sub(r"\.(service|timer|socket|slice)$", "", unit)
    cid = reg.canonical(base)
    if cid and reg.is_registry(cid):
        return cid
    best = None
    for c in reg.components:
        if base.startswith(c + "-") and (best is None or len(c) > len(best)):
            best = c
    return best


def classify_systemd(timers: list[dict], policy: dict[str, dict], journal: dict[str, Counter], unit_ev: Counter,
                     reg: Registry, types: Counter, props: Callable[[str], dict] = unit_props) -> list[Row]:
    rows: list[Row] = []
    vendor = 0

    def ev(unit: str) -> int:
        base = re.sub(r"\.(service|timer)$", "", unit)
        return sum(n for k, n in unit_ev.items() if re.sub(r"\.(service|timer)$", "", str(k)) == base)

    for t in sorted(timers, key=lambda x: x.get("unit") or ""):
        unit, svc = t.get("unit") or "", t.get("activates") or ""
        pol = policy.get(unit) or {}
        if "OS/vendor" in str(pol.get("owner") or ""):
            vendor += 1
            continue
        j = journal.get(svc, Counter())
        runs = j["done"] + j["start_failed"]
        exempt = "AD-22" if "AD-22" in str(pol.get("reason") or "") else None
        rows.append(Row("systemd", f"native timer {unit} runs -> any event", unit_component(reg, svc) or "candybar", runs, ev(svc),
                        verdict(runs, ev(svc)),
                        f"{runs} run(s) of {svc} in the journal ({j['start_failed']} failed to start); a second clock outside Candybar"
                        + (" (approved exception AD-22)" if exempt else ""),
                        tickets=[] if exempt else ["CAND-55", *TIMER_TICKETS.get(unit, [])], exempt=exempt))
    loops, fails = [], Counter()
    for u, c in journal.items():
        if c["restart"] >= CRASH_LOOP:
            loops.append(u)
        elif c["failed"] or c["start_failed"]:
            fails[u] = c["failed"] + c["start_failed"]
    for u in sorted(loops, key=lambda x: -journal[x]["restart"]):
        pr = props(u)
        n = journal[u]["restart"]
        rows.append(Row("systemd", f"crash loop {u} -> any event", unit_component(reg, u) or "mon-alerts", n, ev(u), verdict(n, ev(u)),
                        f"{n} restarts in the window; now {pr.get('ActiveState', '?')}/{pr.get('SubState', '?')}"
                        f" result {pr.get('Result', '?')}, NRestarts {pr.get('NRestarts', '?')}",
                        tickets=CRASH_TICKETS.get(u, ["MONI-3"])))
    if fails:
        arch = sum(ev(u) for u in fails)
        rows.append(Row("systemd", "unit failures -> any failure event", "mon-alerts", sum(fails.values()), arch,
                        verdict(sum(fails.values()), arch), f"{len(fails)} unit(s): {fmt_counts(fails, 3)}", tickets=["MONI-3"]))
    oom = sum(c["oom"] for c in journal.values())
    if oom:
        arch = sum(n for t, n in types.items() if "oom" in t)
        rows.append(Row("systemd", "OOM kills -> any event", "mon-alerts", oom, arch, verdict(oom, arch),
                        f"kernel / systemd-oomd kills in {sum(1 for c in journal.values() if c['oom'])} unit(s)",
                        tickets=["not yet ticketed"]))
    gw = journal.get("hermes-gateway.service", Counter())["done"]
    arch = sum(n for t, n in types.items() if "gateway" in t and "restart" in t)
    rows.append(Row("systemd", "hermes-gateway (re)starts -> any event", "hermes-gw", gw, arch, verdict(gw, arch),
                    "journal starts of hermes-gateway.service", tickets=["INFR-156"]))
    for r in rows:
        if vendor and r.thing.startswith("native timer"):
            r.detail["os_vendor_timers_not_counted"] = vendor
    return rows


def adapter_systemd(ctx: Ctx) -> list[Row]:
    timers = read_timers()
    journal = read_journal(ctx.since, ctx.until)
    types = [t for t in ctx.types if t.startswith(UNIT_EVENT_PREFIXES)]
    unit_ev: Counter = Counter()
    if types:
        got = ctx.archive.json(
            "select coalesce(json_object_agg(k, n), '{}'::json) from (select coalesce(data->>'unit', data->>'service', data->>'name') k,"
            f" count(*) n from events where type = any({text_array(types)}) and {_win(ctx, 'time')} group by 1) x where k is not null;") or {}
        unit_ev = Counter({k: int(v) for k, v in got.items()})
    return classify_systemd(timers, read_policy(), journal, unit_ev, ctx.registry, ctx.types)


# ---------------------------------------------------------------- 8. git commits and pushes under ~/code

SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target", ".cache", ".worktrees", ".git"}


def find_repos(root: Path, depth: int = 4) -> dict[str, Path]:
    """git common dir -> one checkout of it, for every repo (and submodule, and worktree) up to depth."""
    out: dict[str, Path] = {}

    def walk(d: Path, lvl: int) -> None:
        try:
            ents = list(os.scandir(d))
        except OSError:
            return
        for e in ents:
            if e.name == ".git":
                common = git_common_dir(Path(e.path))
                if common:
                    out.setdefault(common, d)
        if lvl >= depth:
            return
        for e in ents:
            if e.is_dir(follow_symlinks=False) and e.name not in SKIP_DIRS and not e.name.startswith("."):
                walk(Path(e.path), lvl + 1)

    walk(root, 0)
    return out


def git_common_dir(dotgit: Path) -> str | None:
    try:
        if dotgit.is_dir():
            return str(dotgit.resolve())
        txt = dotgit.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not txt.startswith("gitdir:"):
        return None
    gd = (dotgit.parent / txt.split(":", 1)[1].strip()).resolve()
    if gd.parent.name == "worktrees":
        return str(gd.parent.parent)
    return str(gd)


def reflog_pushes(common: Path, since: float, until: float) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    base = common / "logs" / "refs" / "remotes"
    for f in base.rglob("*") if base.is_dir() else []:
        try:
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                head, _, msg = line.partition("\t")
                if not msg.startswith("update by push"):
                    continue
                parts = head.split()
                if len(parts) >= 2 and since <= float(parts[-2]) * 1000.0 < until:
                    out.add((str(f.relative_to(base)), parts[1]))
        except (OSError, ValueError, IndexError):
            continue
    return out


def adapter_git(ctx: Ctx, root: Path = CODE_ROOT) -> list[Row]:
    repos = find_repos(root)
    if not repos:
        raise Skip("no git repositories under the code root")
    s, u = int(ctx.since // 1000), int(ctx.until // 1000)

    def one(item: tuple[str, Path]) -> tuple[set[str], int]:
        common, wt = item
        try:
            p = subprocess.run(["git", "-C", str(wt), "log", "--all", f"--since=@{s}", f"--until=@{u}", "--format=%H"],
                               capture_output=True, text=True, timeout=60)
            shas = set(p.stdout.split())
        except (OSError, subprocess.TimeoutExpired):
            shas = set()
        return shas, len(reflog_pushes(Path(common), ctx.since, ctx.until))

    shas: set[str] = set()
    pushes = 0
    with ThreadPoolExecutor(8) as ex:
        for a, b in ex.map(one, repos.items()):
            shas |= a
            pushes += b
    commit_ev = ctx.count_types(lambda t: bool(re.match(r"^bloodbank\.(repo|git|vcs)\.", t)) and "commit" in t)
    push_ev = ctx.count_types(lambda t: bool(re.match(r"^bloodbank\.(repo|git|vcs)\.", t)) and "push" in t)
    ev = f"{len(repos)} repositories (worktrees and submodules folded by git common dir)"
    return [Row("git", "git commits -> repo commit events", "git-hooks", len(shas), commit_ev, verdict(len(shas), commit_ev),
                f"{ev}; distinct shas by committer date", tickets=[NO_BOARD]),
            Row("git", "git pushes -> repo push events", "git-hooks", pushes, push_ev, verdict(pushes, push_ev),
                "remote-tracking reflog entries 'update by push' in the window", tickets=[NO_BOARD])]


# ---------------------------------------------------------------- 9. Hindsight's own audit log

def adapter_hindsight(ctx: Ctx, run: Callable[[list[str]], str] | None = None) -> list[Row]:
    def sh(argv: list[str]) -> str:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            raise Skip(f"{' '.join(argv[:3])}: exit {p.returncode}")
        return p.stdout
    run = run or sh
    try:
        d = json.loads(run(["hindsight", "bank", "list", "-o", "json"]) or "[]")
    except (OSError, ValueError) as exc:
        raise Skip(f"hindsight bank list: {type(exc).__name__}") from exc
    banks = [b["bank_id"] for b in (d.get("banks", d) if isinstance(d, dict) else d) if isinstance(b, dict) and b.get("bank_id")]

    def stats(b: str) -> Counter:
        try:
            s = json.loads(run(["hindsight", "audit", "stats", b, "--period", "day", "-o", "json"]) or "{}")
        except (Skip, OSError, ValueError):
            return Counter({"_error": 1})
        c: Counter = Counter()
        for k in s.get("buckets") or []:
            t0 = parse_ts(k.get("time"))
            if t0 is not None and t0 < ctx.until and t0 + DAY > ctx.since:
                c.update({a: int(n) for a, n in (k.get("actions") or {}).items()})
        return c

    tot: Counter = Counter()
    with ThreadPoolExecutor(8) as ex:
        for c in ex.map(stats, banks):
            tot.update(c)
    err = tot.pop("_error", 0)
    n = sum(tot.values())
    arch = ctx.count_types(lambda t: t.startswith(("bloodbank.memory.", "bloodbank.hindsight.")))
    return [Row("hindsight", "Hindsight operations -> memory events", "hindsight", n, arch, verdict(n, arch),
                f"{len(banks)} banks{f' ({err} unreadable)' if err else ''}, day buckets overlapping the window (the audit API"
                f" buckets by day at the finest): {fmt_counts(tot, 4)}", tickets=[NO_BOARD])]


# ---------------------------------------------------------------- 10. declared but never seen (schemas, registry surfaces)

def distinct_all(ctx: Ctx, col: str) -> set[str]:
    """Every distinct value of an indexed column, all time, by a recursive skip-scan (one index probe per value)."""
    return set(ctx.archive.json(
        f"with recursive t(v) as (select min({col}) from events union all select (select min({col}) from events where {col} > t.v)"
        f" from t where t.v is not null) select coalesce(json_agg(v), '[]'::json) from t where v is not null;") or [])


def dead_letter_types(ctx: Ctx) -> set[str]:
    return set(ctx.archive.json(
        "select coalesce(json_agg(distinct t), '[]'::json) from (select substring(encode(raw, 'escape')"
        " from '\"type\"\\s*:\\s*\"([^\"]+)\"') t from dead_letter) x where t is not null;") or [])


def classify_declared(decl: dict[str, str], seen: set[str], dead_t: set[str], window_types: Counter, producers_seen: set[str],
                      window_producers: Iterable[str], reg: Registry, public: bool = True) -> list[Row]:
    rows: list[Row] = []
    ev = sorted(t for t, k in decl.items() if k == "event")
    never = [t for t in ev if t not in seen and t not in dead_t]
    shown = [short(t) for t in never if not (public and is_private(t))]
    rows.append(Row("declared", "schema-declared event types -> ever archived", "event-contract", len(ev), len(ev) - len(never),
                    "declared-never-seen" if never else "covered",
                    f"{len(never)} of {len(ev)} declared event types never reached Candystore (nor a dead letter)"
                    + (f": {sample(shown, 6)}" if shown else ""), detail={"never": never if not public else len(never)}))
    bb = {t: n for t, n in window_types.items() if t.startswith("bloodbank.")}
    bare = {t: n for t, n in bb.items() if t not in decl}
    named = {short(t): n for t, n in bare.items() if not (public and is_private(t))}
    rows.append(Row("declared", "archived types -> a Bloodbank schema", "event-contract", len(bb), len(bb) - len(bare),
                    verdict(len(bb), len(bb) - len(bare)),
                    f"{len(bare)} type(s) in the window with no schema ({sum(bare.values())} events)"
                    + (f": {fmt_counts(named, 5)}" if named else ""), tickets=["BB-53"]))
    exact = {p: c for p, c in reg._exact.items()}
    never_p = sorted(p for p in exact if p not in producers_seen)
    never_g = sorted(g for g, _ in reg._globs if not any(re.fullmatch(_glob_re(g), p) for p in producers_seen))
    comps = Counter(exact[p] for p in never_p) + Counter(c for g, c in reg._globs if g in never_g)
    total = len(exact) + len(reg._globs)
    rows.append(Row("declared", "registry producer surfaces -> ever seen", "event-contract", total, total - len(never_p) - len(never_g),
                    "declared-never-seen" if never_p or never_g else "covered",
                    f"{len(never_p) + len(never_g)} of {total} declared producer surfaces never published; most by component:"
                    f" {fmt_counts(comps, 5)}"))
    wp = sorted(set(window_producers))
    unk = [p for p in wp if reg.resolve(p).via == "unknown"]
    rows.append(Row("declared", "window producers -> a registry component", "event-contract", len(wp), len(wp) - len(unk),
                    verdict(len(wp), len(wp) - len(unk)), f"{len(unk)} producer(s) resolve to no component"
                    + (f": {sample(unk, 4)}" if unk and not public else "")))
    return rows


def _glob_re(g: str) -> str:
    return "".join(".*" if ch == "*" else "." if ch == "?" else re.escape(ch) for ch in g)


def adapter_declared(ctx: Ctx) -> list[Row]:
    decl = declared_types()
    if not decl:
        raise Skip("no Bloodbank schemas found")
    return classify_declared(decl, distinct_all(ctx, "type"), dead_letter_types(ctx), ctx.types, distinct_all(ctx, "producer"),
                             ctx.producers, ctx.registry, ctx.public)


# ---------------------------------------------------------------- 11. dead letters

DEAD_TICKETS = {"bloodbank.repo.decision.recorded": ["BB-46"]}


def classify_dead(dead: list[dict], dead_events: int, public: bool = True) -> list[Row]:
    rows = [Row("deadletters", "dead letters -> system.event.dead_lettered", "candystore", len(dead), dead_events,
                verdict(len(dead), dead_events), "Candystore drops them into dead_letter without an event", tickets=["CANDYS-79"])]
    groups: Counter = Counter()
    for d in dead:
        env = d.get("_env") or {}
        t = CS.normalize_type(env)[0] if env else ""
        groups[(t or "(unparseable)", str(d.get("reason") or "?"))] += 1
    for (t, reason), n in groups.most_common(10):
        name = "a private type" if public and is_private(t) else short(t)
        rows.append(Row("deadletters", f"dead-lettered {name} ({reason})", "candystore", n, 0, "lost-in-transit",
                        f"{n} message(s) reached Candystore and were refused: {reason}", tickets=DEAD_TICKETS.get(t, [])))
    return rows


def adapter_deadletters(ctx: Ctx) -> list[Row]:
    from .query import _dead_env  # noqa: PLC0415
    for d in ctx.dead:
        d.setdefault("_env", _dead_env(d))
    return classify_dead(ctx.dead, ctx.types.get("bloodbank.system.event.dead_lettered", 0), ctx.public)


# ---------------------------------------------------------------- 12. crank nudges

def adapter_crank(ctx: Ctx, path: Path = CRANK_SENDS) -> list[Row]:
    if not path.exists():
        raise Skip("no crank send log on this machine")
    n = 0
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                t = parse_ts((json.loads(line) or {}).get("ts"))
            except (ValueError, AttributeError):
                continue
            if t is not None and ctx.since <= t < ctx.until:
                n += 1
    arch = ctx.count_types(lambda t: t.startswith("bloodbank.crank.nudge"))
    return [Row("crank", "crank pane sends -> crank.nudge events", "crank", n, arch, verdict(n, arch),
                "zcrank-send's own send log", tickets=[NO_BOARD])]


# ---------------------------------------------------------------- the table of adapters

ADAPTERS: dict[str, tuple[Callable[[Ctx], list[Row]], str, str, str]] = {
    # id: (adapter, kind, full locator, public locator)
    "bus": (adapter_bus, "nats", f"{NATS_URL} direct-get + STREAM.INFO + CONSUMER.LIST (no consumers)", "NATS JetStream direct-get"),
    "candybar": (adapter_candybar, "postgres", f"docker exec {CANDYBAR_CONTAINER} psycopg (read-only)", "Candybar database (read-only)"),
    "hookhub": (adapter_hookhub, "sqlite", f"{RECEIPTS} (mode=ro)", "hook-hub receipts (read-only)"),
    "gateway": (adapter_gateway, "postgres", f"docker exec {LEDGER_CONTAINER} psycopg + docker exec {LITELLM_PG} psql (read-only)",
                "gateway usage ledger (read-only)"),
    "transcripts": (adapter_transcripts, "files", f"{CLAUDE_PROJECTS}/*/*.jsonl + {CODEX_SESSIONS}", "Claude and Codex transcripts"),
    "hermes": (adapter_hermes, "sqlite", f"{HERMES_PROFILES}/*/state.db (mode=ro)", "Hermes desk state databases (read-only)"),
    "systemd": (adapter_systemd, "journal", "journalctl --user + systemctl --user list-timers", "systemd --user journal"),
    "git": (adapter_git, "git", f"git log --all + remote reflogs under {CODE_ROOT}", "git repositories"),
    "hindsight": (adapter_hindsight, "cli", "hindsight audit stats --period day", "Hindsight audit log"),
    "declared": (adapter_declared, "postgres", f"{SCHEMAS_DIR} + the cast's producer surfaces + skip-scans on events indexes",
                 "Bloodbank schemas and the registry"),
    "deadletters": (adapter_deadletters, "postgres", "candystore dead_letter (read-only)", "Candystore dead letters"),
    "crank": (adapter_crank, "file", str(CRANK_SENDS), "crank send log"),
}
TIMEOUTS = {"bus": 300.0}       # seconds, plus 240 s a day of window for the bus
