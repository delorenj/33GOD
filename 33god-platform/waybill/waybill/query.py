"""waybill query: any Candystore query as a replayable `33god.waybill` (recorder.mode 'query', SPEC section 2b).

A capture follows one prompt. A query is the wide shot: every event Candystore archived that matches a
filter set inside a window (last night, the last 2 hours, one project's errors, one session), written as a
waybill the Factory plays like any other. One read seam (`PsqlReader`; GET /export replaces it when
CANDYS-78 lands), one resolver (registry.py, the map atlas.py renders into the Factory cast), and a
deterministic condensing pass so a 100k-event night still plays as about 60 stops:

  - The window is cut into at most 12 chapters (whole local minutes, equal length).
  - Kept events stay individual BusEvents with a `publish:<id>` span at their resolved component: dead
    letters, the exemplars a finding names, rare ones (at most 12 of that producer+type in the window), then
    failures (type or data says failed / exhausted / denied / breached, ...), round-robin across groups so one
    noisy job cannot starve the rest. At most 400. A query that fits under the cap keeps everything.
  - Everything else folds into `batch` spans per (component, type, chapter): count, first/last time, a
    per-minute series, at most 3 exemplar ids, the producers, the failed count.
  - Spans the Factory director keys on are synthesized from kept events: `tool:<tool_use_id>` (tool
    requested/completed), `llm:<request_id>` (llm.usage.recorded joined by data.request_id, never by
    correlationid), `hook:<inv>` + `handler:<inv>:<id>` (agent.hook.updated mirrors; system.hook.updated is
    the hub heartbeat, not a mirror).
  - Conservation: kept events + batched events == Candystore's own count for the query + dead letters
    handled. When it does not hold, stats.conservation_ok is false and a broken gap says by how much.

Read-only: `default_transaction_read_only`, time-window bounded, keyset paging on (time, id) over
idx_events_time, an as_of fence on received_at so the count and the pages agree. The filters are rendered
by Candystore's own `query._filters` inside its container, so `--lens errors` means exactly what the
Candystore UI means by it.

The public profile follows the night digest's rules (night.py): message, call and payment types are
counted but never named (they fold into a `private` batch and are never kept), third-party Hermes desks
become `desk-<n>`, tenant slugs `tenant-<n>` and unresolvable producers `producer-<n>`; aliased producers
carry no envelope payload.
"""
from __future__ import annotations

import base64
import bisect
import gzip
import hashlib
import json
import math
import os
import re
import socket
import subprocess
import time
import urllib.parse
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Iterable, Iterator
from zoneinfo import ZoneInfo

from . import VERSION
from . import model as M
from .assemble import FORMAT, SCHEMA_VERSION, apply_profile, component_record, fmt_duration, waybill_id
from .collectors import candystore as CS
from .night import PRIVATE_TYPES, _first_party_desk, night_window
from .registry import HANDLER_OWNERS, Registry, load as load_cast, short_type, worker_resolver

MODE = "query"
DEFAULT_TZ = "America/New_York"
NIGHT_FROM, NIGHT_TO = "18:02", "07:41"
CHAPTERS_MAX = 12
STOPS_PER_CHAPTER = 5
MIN_CHAPTER_MIN = 5          # a chapter is never shorter than this, so a short window gets fewer chapters
KEEP_MAX = 400
RARE = 12                    # a producer+type seen at most this often in the window is kept whole
EXEMPLARS = 3
FINDING_GROUPS_MAX = 24
PAGE = 20_000
RECEIVED_AT_MARGIN_MS = 24 * 3600 * 1000.0
GATEWAY = "aai-gateway"
ARCHIVE = "candystore"
CONSUMER = CS.CONSUMER
APP_CONTAINER = os.environ.get("WAYBILL_CANDYSTORE_APP", "candystore")
CANDYSTORE_URL = os.environ.get("WAYBILL_CANDYSTORE_URL", "http://127.0.0.1:8683")

FAIL_WORDS = ("failed", "exhausted", "denied", "breached")
FAIL_VALUES = FAIL_WORDS + ("failure", "error", "timeout", "timed_out")
_FAIL_TYPE = re.compile(r"\.(failed|exhausted|denied|breached)$")
HOOK_MIRROR = "bloodbank.agent.hook.updated"
TOOL_TYPES = ("bloodbank.agent.tool.requested", "bloodbank.agent.tool.completed")
USAGE_TYPES = ("bloodbank.llm.usage.recorded", "bloodbank.llm.allowance.observed")

# Filters a query may carry: the contract's set plus the other `_filters` keys Candystore understands.
FILTER_KEYS = ("type", "producer", "project", "correlation", "scope", "lens", "q", "class", "domain", "service", "cli")
_TO_CANDYSTORE = {"correlation": "correlationid", "class": "provenance"}
_FROM_URL = {"correlationid": "correlation", "provenance": "class"}
# filters a dead letter can be matched against in Python (its raw envelope); the rest need Candystore's SQL
_DEAD_MATCHABLE = {"type", "producer", "correlation", "scope", "domain"}

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


# ---------------------------------------------------------------- the query

@dataclass
class QuerySpec:
    since: float                                  # epoch ms
    until: float                                  # epoch ms
    clock: str = "time"                           # time (producer's envelope time, indexed) | received_at (archive time)
    filters: dict[str, str] = field(default_factory=dict)
    label: str | None = None
    when: str | None = None                       # the window as a phrase inside the prompt text
    tz: str = DEFAULT_TZ
    profile: str = "public"
    budget_stops: int = CHAPTERS_MAX * STOPS_PER_CHAPTER
    include_dead_letters: bool = True

    def normalized(self) -> dict[str, Any]:
        return {"since": M.iso(self.since), "until": M.iso(self.until), "clock": self.clock,
                "filters": {k: self.filters[k] for k in sorted(self.filters) if self.filters[k]}}

    def query_id(self) -> str:
        return "q_" + hashlib.sha256(json.dumps(self.normalized(), sort_keys=True).encode()).hexdigest()[:12]


def is_failure(event_type: str | None, data: Any) -> bool:
    """The keep rule's failure test, the same one the SQL header pass computes (FAILED_SQL)."""
    if _FAIL_TYPE.search(event_type or ""):
        return True
    if not isinstance(data, dict):
        return False
    for k in ("outcome", "status"):
        v = data.get(k)
        if isinstance(v, str) and v.lower() in FAIL_VALUES:
            return True
    if event_type == HOOK_MIRROR:
        inv = data.get("invocation") if isinstance(data.get("invocation"), dict) else {}
        if inv.get("status") in ("failed", "timed_out"):
            return True
        for e in inv.get("executions") or []:
            if isinstance(e, dict) and e.get("status") in ("failed", "timed_out"):
                return True
    return False


def failure_severity(event_type: str) -> str:
    """A failed tool call is the agent's own business (grep found nothing); everything else is a warning."""
    return "info" if event_type.startswith("bloodbank.agent.tool.") else "warn"


_IN = ",".join(f"'{v}'" for v in FAIL_VALUES)
FAILED_SQL = (
    "coalesce(type ~ '\\.(failed|exhausted|denied|breached)$'"
    f" or lower(data->>'outcome') in ({_IN}) or lower(data->>'status') in ({_IN})"
    f" or (type = '{HOOK_MIRROR}' and (data->'invocation'->>'status' in ('failed', 'timed_out')"
    " or jsonb_path_exists(data, '$.invocation.executions[*] ? (@.status == \"failed\" || @.status == \"timed_out\")'))),"
    " false)"
)
WORKER_SQL = "case when starts_with(type, 'bloodbank.cron.candybar.') then data->>'name' end"


# ---------------------------------------------------------------- the read seam

@dataclass
class Row:
    """One archived event header (pass 1). t = envelope time, ra = received_at, both epoch ms."""
    id: str
    t: float
    ra: float | None
    producer: str
    type: str
    source: str | None
    failed: bool
    worker: str | None = None


def _q(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"


class PsqlReader:
    """Candystore through `docker exec candystore-postgres psql` (read-only). The one place the query
    builder touches the archive: swap it for a GET /export client (CANDYS-78) without touching the fold."""

    kind = "postgres"

    def __init__(self, timeout: float = 300.0, page: int = PAGE, app_container: str = APP_CONTAINER):
        self.timeout, self.page, self.app = timeout, page, app_container
        self.locator = f"docker exec {CS.PG_CONTAINER} psql (read-only), filters by docker exec {app_container} candystore.query._filters"
        self.pages = 0

    # -- helpers
    def _json(self, sql: str) -> Any:
        return CS.psql_json(sql, self.timeout)

    def now_ms(self) -> float:
        return float(self._json("select to_json(extract(epoch from now()) * 1000);"))

    def where(self, filters: dict[str, str]) -> str:
        """Candystore's own WHERE for these filters (query._filters, rendered inside its container)."""
        kw = {_TO_CANDYSTORE.get(k, k): v for k, v in filters.items() if v}
        if not kw:
            return "true"
        script = ("import json, sys\nfrom candystore.query import _filters\nfrom candystore.db import cursor\n"
                  "where, params = _filters(**json.loads(sys.stdin.read()))\n"
                  "with cursor() as cur:\n    print(json.dumps(cur.mogrify(' AND '.join(where), params).decode()))\n")
        p = subprocess.run(["docker", "exec", "-i", self.app, "python", "-c", script], input=json.dumps(kw),
                           capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            tail = (p.stderr or p.stdout).strip().splitlines()
            raise RuntimeError(f"Candystore could not render the filters: {tail[-1] if tail else 'no output'}")
        return json.loads(p.stdout.strip().splitlines()[-1])

    @staticmethod
    def window_sql(spec: QuerySpec, as_of: float) -> str:
        lo, hi = M.iso(spec.since), M.iso(min(spec.until, as_of))
        fence = f"received_at <= {_q(M.iso(as_of))}::timestamptz"
        if spec.clock == "received_at":
            mlo, mhi = M.iso(spec.since - RECEIVED_AT_MARGIN_MS), M.iso(spec.until + RECEIVED_AT_MARGIN_MS)
            return (f"time >= {_q(mlo)}::timestamptz and time < {_q(mhi)}::timestamptz and received_at >= {_q(lo)}::timestamptz"
                    f" and received_at < {_q(hi)}::timestamptz and {fence}")
        return f"time >= {_q(lo)}::timestamptz and time < {_q(hi)}::timestamptz and {fence}"

    # -- the reads
    def count(self, spec: QuerySpec, where: str, as_of: float) -> int:
        return int(self._json(f"select to_json(count(*)) from events where {self.window_sql(spec, as_of)} and ({where});") or 0)

    def page_sql(self, spec: QuerySpec, where: str, as_of: float, after: tuple[str, str] | None) -> str:
        key = f" and (time, id) > ({_q(after[0])}::timestamptz, {_q(after[1])}::uuid)" if after else ""
        return (
            "with p as (select id, time, received_at, producer, type, source,"
            f" {FAILED_SQL} as failed, {WORKER_SQL} as worker from events"
            f" where {self.window_sql(spec, as_of)} and ({where}){key} order by time, id limit {int(self.page)})"
            " select json_build_object('rows', coalesce((select json_agg(json_build_array(id::text,"
            " extract(epoch from time) * 1000, extract(epoch from received_at) * 1000, producer, type, source, failed,"
            " worker) order by time, id) from p), '[]'::json),"
            " 'last', (select json_build_array(time::text, id::text) from p order by time desc, id desc limit 1));"
        )

    def rows(self, spec: QuerySpec, where: str, as_of: float) -> Iterator[Row]:
        after = None
        while True:
            res = self._json(self.page_sql(spec, where, as_of, after)) or {}
            self.pages += 1
            got = res.get("rows") or []
            for r in got:
                yield Row(r[0], float(r[1]), float(r[2]) if r[2] is not None else None, r[3] or "", r[4] or "",
                          r[5], bool(r[6]), r[7])
            if len(got) < self.page or not res.get("last"):
                return
            after = tuple(res["last"])

    def envelopes(self, ids: list[str]) -> dict[str, dict]:
        good = sorted({i for i in ids if _UUID.match(i or "")})
        out: dict[str, dict] = {}
        for i in range(0, len(good), 200):
            arr = "array[" + ",".join(_q(x) for x in good[i:i + 200]) + "]::uuid[]"
            for r in self._json("select coalesce(json_agg(json_build_object('id', id::text, 'received_at', received_at,"
                                f" 'raw', raw)), '[]'::json) from events where id = any({arr});") or []:
                out[r["id"]] = r
        return out

    def dead_letters(self, spec: QuerySpec, as_of: float) -> list[dict]:
        lo, hi = M.iso(spec.since), M.iso(min(spec.until, as_of))
        # nul-sanitized rows were archived after the NUL strip (they are in events too): not a loss
        return self._json(
            "select coalesce(json_agg(json_build_object('id', id, 'event_id', event_id, 'topic', topic, 'reason', reason,"
            " 'error', left(error, 600), 'received_at', received_at, 'raw_b64', encode(raw, 'base64')) order by received_at, id),"
            f" '[]'::json) from dead_letter where received_at >= {_q(lo)}::timestamptz and received_at < {_q(hi)}::timestamptz"
            f" and received_at <= {_q(M.iso(as_of))}::timestamptz and reason <> 'nul-sanitized';") or []

    def session_span(self, correlation: str) -> tuple[float, float] | None:
        if not _UUID.match(correlation or ""):
            return None
        r = self._json(f"select json_build_array(extract(epoch from min(time)) * 1000, extract(epoch from max(time)) * 1000)"
                       f" from events where correlationid = {_q(correlation)}::uuid;")
        return (float(r[0]), float(r[1])) if r and r[0] is not None else None

    def event_time(self, event_id: str) -> float | None:
        if not _UUID.match(event_id or ""):
            return None
        r = self._json(f"select to_json(extract(epoch from time) * 1000) from events where id = {_q(event_id)}::uuid;")
        return float(r) if r is not None else None

    def explain(self, spec: QuerySpec, where: str, as_of: float) -> str:
        sql = self.page_sql(spec, where, as_of, None).rstrip(";")
        p = subprocess.run(CS.PSQL_ARGV, input="set default_transaction_read_only = on;\nexplain " + sql + ";\n",
                           capture_output=True, text=True, timeout=60)
        return (p.stdout or p.stderr).strip()


# ---------------------------------------------------------------- windows

_DUR = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(s|sec|m|min|h|hr|d|day|w)s?\s*$", re.I)


def parse_duration(text: str) -> float:
    """'2h', '30m', '1d', '90s' -> ms."""
    m = _DUR.match(text or "")
    if not m:
        raise ValueError(f"cannot read the duration {text!r} (use e.g. 30m, 2h, 1d)")
    n, u = float(m.group(1)), m.group(2).lower()[0]
    return n * {"s": 1000.0, "m": 60_000.0, "h": 3_600_000.0, "d": 86_400_000.0, "w": 604_800_000.0}[u]


def _human_duration(ms_: float) -> str:
    mins = int(round(ms_ / 60_000.0))
    if mins % 1440 == 0 and mins:
        n, unit = mins // 1440, "day"
    elif mins % 60 == 0 and mins:
        n, unit = mins // 60, "hour"
    else:
        n, unit = mins, "minute"
    return f"{n} {unit}{'s' if n != 1 else ''}" if n != 1 else f"{unit}"


def _hm(epoch_ms: float, tz: str) -> str:
    return datetime.fromtimestamp(epoch_ms / 1000.0, ZoneInfo(tz)).strftime("%H:%M")


def _dm(epoch_ms: float, tz: str) -> str:
    d = datetime.fromtimestamp(epoch_ms / 1000.0, ZoneInfo(tz))
    return f"{d.day} {d.strftime('%b')}"


def last_night(now_ms: float, tz: str = DEFAULT_TZ, start: str = NIGHT_FROM, end: str = NIGHT_TO) -> tuple[float, float]:
    """Yesterday's 18:02 to today's 07:41 in tz (night.py's convention), as epoch ms."""
    day = datetime.fromtimestamp(now_ms / 1000.0, ZoneInfo(tz)).date() - timedelta(days=1)
    lo, hi = night_window(day, start, end, tz)
    return lo.timestamp() * 1000.0, hi.timestamp() * 1000.0


def window_label(kind: str, since: float, until: float, tz: str, clamped: bool = False, extra: str = "") -> tuple[str, str]:
    """(label, when-phrase). label: 'Last night, 18:02 to 07:41'; when: 'last night, 18:02 to 07:41'."""
    a, b = _hm(since, tz), _hm(until, tz)
    so_far = " (so far)" if clamped else ""
    if kind == "last-night":
        return f"Last night, {a} to {b}{so_far}", f"last night, {a} to {b}{so_far}"
    if kind == "last":
        h = _human_duration(until - since)
        return f"The last {h}, {a} to {b}", f"in the last {h}, {a} to {b}"
    if kind == "session":
        return f"Session {extra[:8]}, {_dm(since, tz)} {a} to {b}", f"in session {extra[:8]}, {_dm(since, tz)} {a} to {b}"
    end = b if _dm(since, tz) == _dm(until, tz) else f"{_dm(until, tz)} {b}"
    return f"{_dm(since, tz)} {a} to {end}{so_far}", f"between {_dm(since, tz)} {a} and {end}{so_far}"


def parse_candystore_url(url: str) -> dict[str, Any]:
    """A Candystore UI or API link -> {filters, from, to, event}. Paths: /projects/<slug>, /sessions/<id>,
    /events/<id>; query: type scope domain producer service cli correlationid project class lens q from to."""
    u = urllib.parse.urlsplit(url)
    qs = urllib.parse.parse_qs(u.query)
    filters: dict[str, str] = {}
    for k, v in qs.items():
        k2 = _FROM_URL.get(k, k)
        if k2 in FILTER_KEYS and v and v[-1]:
            filters[k2] = v[-1]
    parts = [urllib.parse.unquote(p) for p in u.path.split("/") if p]
    event = None
    if len(parts) >= 2 and parts[0] == "projects":
        filters["project"] = parts[1]
    elif len(parts) >= 2 and parts[0] == "sessions":
        filters["correlation"] = parts[1]
    elif len(parts) >= 2 and parts[0] == "events" and _UUID.match(parts[1]):
        event = parts[1]
        filters["q"] = parts[1]
    return {"filters": filters, "from": (qs.get("from") or [None])[-1], "to": (qs.get("to") or [None])[-1], "event": event}


def describe_filters(filters: dict[str, str]) -> str:
    names = {"type": "type", "producer": "producer", "project": "project", "correlation": "session", "scope": "scope",
             "lens": "lens", "q": "text", "class": "class", "domain": "domain", "service": "service", "cli": "cli"}
    out = []
    for k in FILTER_KEYS:
        if filters.get(k):
            v = filters[k]
            out.append(f"{names[k]} '{v}'" if k == "q" else f"{names[k]} {v[:8] if k == 'correlation' else v}")
    return ", ".join(out)


# ---------------------------------------------------------------- condensing

@dataclass
class Item:
    """One thing the query has to account for: an archived event (row) or a dead letter."""
    id: str
    clock_t: float                  # epoch ms on the query's clock (chapter / minute assignment)
    t: float                        # envelope time, epoch ms
    ra: float | None                # received_at (Candystore), epoch ms
    producer: str
    type: str
    source: str | None
    failed: bool
    worker: str | None = None
    dead: dict | None = None        # the dead_letter row (+ parsed env) for a dead letter
    comp: str = M.Ids.PROMPT
    owner: str | None = None
    via: str = "unknown"
    shown_producer: str = ""
    shown_type: str = ""
    private: bool = False
    aliased: bool = False
    chapter: int = 0
    keep: str | None = None


@dataclass
class Batch:
    comp: str
    type: str                       # shown type (the real one, or 'private')
    chapter: int
    count: int = 0
    failed: int = 0
    t0: float = 0.0
    t1: float = 0.0
    ids: list[str] = field(default_factory=list)
    minutes: Counter = field(default_factory=Counter)
    producers: Counter = field(default_factory=Counter)
    credit: Counter = field(default_factory=Counter)


class Aliases:
    """Public-profile names for things that are not ours to name (night.py's rules)."""

    def __init__(self, registry: Registry, public: bool):
        self.reg, self.public = registry, public
        self.records = registry.records
        self.desk: dict[str, str] = {}
        self.tenant: dict[str, str] = {}
        self.producer: dict[str, str] = {}

    def apply(self, it: Item, res) -> None:
        it.comp, it.owner, it.via = res.id, res.owner, res.via
        it.shown_producer = it.producer or "(none)"
        it.shown_type = it.type
        if not self.public:
            return
        if it.type.startswith(PRIVATE_TYPES):
            it.private, it.shown_type = True, "private"
        if res.via == "desk" and res.key and res.key != "unknown" and res.id.startswith("hermes-desk:") \
                and not _first_party_desk(res.key, self.records):
            alias = self.desk.setdefault(res.key, f"desk-{len(self.desk) + 1}")
            it.comp, it.shown_producer, it.aliased = f"hermes-desk:{alias}", f"hermes-agent:{alias}", True
        elif res.via == "tenant" and res.key and not _first_party_desk(res.key, self.records):
            alias = self.tenant.setdefault(res.key, f"tenant-{len(self.tenant) + 1}")
            prefix = res.id[: len(res.id) - len(res.key)]
            it.comp, it.shown_producer, it.aliased = f"{prefix}{alias}", alias, True
        elif res.via == "unknown":
            alias = self.producer.setdefault(it.producer or "(none)", f"producer-{len(self.producer) + 1}")
            it.shown_producer, it.aliased = alias, True


def chapter_bounds(since: float, until: float, budget_stops: int = CHAPTERS_MAX * STOPS_PER_CHAPTER) -> list[float]:
    """n+1 boundaries (epoch ms). Whole minutes from `since` when the window is long enough, n <= 12."""
    total = max(0.0, until - since)
    cap = max(1, min(CHAPTERS_MAX, int(budget_stops) // STOPS_PER_CHAPTER or 1))
    minutes = total / 60_000.0
    n = max(1, min(cap, math.ceil(minutes / MIN_CHAPTER_MIN) if minutes else 1))
    whole = int(minutes)
    if whole >= n:
        b = [since + (i * whole // n) * 60_000.0 for i in range(n)]
    else:
        b = [since + i * total / n for i in range(n)]
    return b + [until]


def _chapter_of(bounds: list[float], t: float) -> int:
    i = bisect.bisect_right(bounds, t) - 1
    return min(max(i, 0), len(bounds) - 2)


def _spread(ids: list[str], k: int = EXEMPLARS) -> list[str]:
    """First, middle and last (deterministic) of a time-ordered id list."""
    if len(ids) <= k:
        return list(ids)
    picks = sorted({0, len(ids) // 2, len(ids) - 1} if k == 3 else {round(i * (len(ids) - 1) / (k - 1)) for i in range(k)})
    return [ids[i] for i in picks][:k]


def _dead_env(r: dict) -> dict:
    try:
        text = base64.b64decode(r.get("raw_b64") or "").decode("utf-8", "replace")
        env = json.loads(text) if text else {}
        return env if isinstance(env, dict) else {"raw": text}
    except (ValueError, TypeError):
        return {}


def _dead_matches(env: dict, filters: dict[str, str]) -> bool:
    et, _ = CS.normalize_type(env)
    for k, v in filters.items():
        if not v:
            continue
        vals = [x.strip() for x in v.split(",") if x.strip()]
        if k == "type" and et not in vals:
            return False
        if k == "producer" and (env.get("producer") or "") != v:
            return False
        if k == "correlation" and str(env.get("correlationid") or "") != v:
            return False
        if k == "domain" and (env.get("domain") or "") != v:
            return False
        if k == "scope":
            st = re.sub(r"^bloodbank\.(v[0-9]+\.)?", "", et).split(".")
            if not any(st[: len(s.split("."))] == s.split(".") for s in vals):
                return False
    return True


# ---------------------------------------------------------------- build

class Builder:
    def __init__(self, spec: QuerySpec, registry: Registry | None = None, manifests: dict[str, str] | None = None,
                 progress: Callable[[str], None] | None = None):
        self.spec = spec
        self.reg = registry or load_cast()
        self.public = spec.profile == "public"
        self.alias = Aliases(self.reg, self.public)
        self.who = worker_resolver(self.reg.records, self.reg.owner, manifests or {}, HANDLER_OWNERS)
        self.progress = progress or (lambda s: None)
        self.frag = M.Fragment(source=M.Source(id=ARCHIVE, kind="postgres", locator=""))   # artifact store
        self.spans: list[dict] = []
        self.events: list[dict] = []
        self.links: list[dict] = []
        self.gaps: list[dict] = []
        self.findings: list[dict] = []
        self.sources: list[dict] = []

    # -- small emitters
    def gap(self, component: str, what: str, why: str, severity: str = "info", span: str | None = None) -> None:
        self.gaps.append({"component": component, "what": what, "why": why, "severity": severity, "span": span})

    def finding(self, severity: str, title: str, detail: str, component: str, evidence: list[str]) -> None:
        self.findings.append({"severity": severity, "title": title, "detail": detail, "component": component,
                              "evidence": evidence})

    def source(self, sid: str, kind: str, locator: str, status: str, items: int, ms_: float, error: str | None = None) -> None:
        self.sources.append({"id": sid, "kind": kind, "locator": locator, "status": status, "items": int(items),
                             "ms": round(ms_, 1), "error": error})

    def rel(self, t: float | None) -> float | None:
        return None if t is None else round(t - self.spec.since, 3)

    # -- the pass
    def build(self, rows: Iterable[Row], total: int, dead_rows: list[dict], envelopes: Callable[[list[str]], dict],
              holocene: Callable[[list[str]], dict] | None = None, as_of: float | None = None,
              notes: list[tuple[str, str, str]] | None = None) -> dict:
        spec = self.spec
        bounds = chapter_bounds(spec.since, spec.until, spec.budget_stops)
        n_ch = len(bounds) - 1
        items: list[Item] = []
        seen: set[str] = set()
        for r in rows:
            if r.id in seen:
                continue
            seen.add(r.id)
            items.append(Item(r.id, (r.ra if spec.clock == "received_at" and r.ra is not None else r.t), r.t, r.ra,
                              r.producer, r.type, r.source, r.failed, r.worker))
        fetched = len(items)
        n_dead = 0
        for d in dead_rows:
            env = d.get("_env") if isinstance(d.get("_env"), dict) else _dead_env(d)
            eid = env.get("id") or d.get("event_id") or f"dead_letter:{d.get('id')}"
            if eid in seen:
                continue            # archived after all (a retry landed): not a loss
            seen.add(eid)
            et, _subj = CS.normalize_type(env) if env else ("unknown", d.get("topic"))
            ra = M.ms(d.get("received_at"))
            items.append(Item(eid, ra or spec.since, M.ms(env.get("time")) or ra or spec.since, None,
                              env.get("producer") or env.get("source") or "", et, env.get("source"), True,
                              dead={**d, "_env": env}))
            n_dead += 1
        items.sort(key=lambda it: (it.clock_t, it.id))
        for it in items:
            self.alias.apply(it, self.reg.resolve(it.producer, it.type, it.source))
            it.chapter = _chapter_of(bounds, it.clock_t)

        # ---- keep rules
        by_pt = Counter((it.producer, it.type) for it in items if not it.dead)
        fail_groups: dict[tuple[str, str], list[Item]] = {}
        unresolved: dict[str, list[Item]] = {}
        for it in items:
            if it.failed and not it.dead and not it.private:
                fail_groups.setdefault((it.comp, it.type), []).append(it)
            if it.via == "unknown":
                unresolved.setdefault(it.producer or "(none)", []).append(it)
        named: list[Item] = []
        groups = sorted(fail_groups.items(), key=lambda kv: (failure_severity(kv[0][1]) != "warn", -len(kv[1]), kv[0]))
        for _k, g in groups[:FINDING_GROUPS_MAX]:
            named += [x for x in g if x.id in set(_spread([y.id for y in g]))]
        for _p, g in sorted(unresolved.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            named += [x for x in g if x.id in set(_spread([y.id for y in g])) and not x.private]

        keepable = [it for it in items if not it.private]
        kept: dict[str, Item] = {}

        def take(it: Item, why: str) -> bool:
            if it.id in kept:
                return True
            if len(kept) >= KEEP_MAX:
                return False
            it.keep = why
            kept[it.id] = it
            return True

        if len(keepable) <= KEEP_MAX:
            for it in keepable:
                take(it, "dead_letter" if it.dead else "all")
        else:
            for it in keepable:
                if it.dead:
                    take(it, "dead_letter")
            for it in named:
                take(it, "finding")

            def fail_round(limit: int) -> None:
                """Round-robin across (component, type) failure groups so one noisy job cannot starve the rest."""
                queues = [[x for x in g if x.id not in kept] for _k, g in groups]
                while any(queues) and limit > 0 and len(kept) < KEEP_MAX:
                    for q in queues:
                        if q and limit > 0 and take(q.pop(0), "failure"):
                            limit -= 1

            # failures and rare events split what is left: a night of 1,200 failures must not push out every
            # rare one (the odd event nobody expected), nor the reverse
            fail_round(max(0, (KEEP_MAX - len(kept)) // 2))
            for it in keepable:
                if not it.dead and by_pt[(it.producer, it.type)] <= RARE:
                    take(it, "rare")
            fail_round(KEEP_MAX)
        # what met a keep rule but did not fit
        overflow: Counter = Counter()
        for it in keepable:
            if it.id in kept:
                continue
            if it.dead:
                overflow["dead_letter"] += 1
            elif it.failed:
                overflow["failure"] += 1
            elif by_pt[(it.producer, it.type)] <= RARE:
                overflow["rare"] += 1
        if overflow:
            self.gap(ARCHIVE, f"{sum(overflow.values())} event(s) met a keep rule but were folded into batches",
                     f"the {KEEP_MAX}-event cap was reached ("
                     + ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in sorted(overflow.items())) + "); they still count in "
                     "their batch, with failures in batch.attrs.failed", "warn")

        # ---- batches
        batches: dict[tuple[str, str, int], Batch] = {}
        for it in items:
            if it.id in kept:
                continue
            key = (it.comp, it.shown_type, it.chapter)
            b = batches.get(key)
            if b is None:
                b = batches[key] = Batch(it.comp, it.shown_type, it.chapter, t0=it.clock_t, t1=it.clock_t)
            b.count += 1
            b.failed += 1 if it.failed else 0
            b.t0, b.t1 = min(b.t0, it.clock_t), max(b.t1, it.clock_t)
            b.ids.append(it.id)
            b.minutes[int((it.clock_t - bounds[it.chapter]) // 60_000)] += 1
            b.producers[it.shown_producer] += 1
            if it.worker and not it.private:
                owner = self.who(it.worker)
                if owner and owner != it.comp:
                    b.credit[owner] += 1

        # ---- envelopes for kept archived events (pass 2), holocene seq for them
        live_ids = [i for i, it in kept.items() if not it.dead]
        t_env = time.monotonic()
        envs: dict[str, dict] = {}
        try:
            envs = envelopes(live_ids) if live_ids else {}
            self.source("candystore-envelopes", "postgres", "events.raw by id (kept events only)", "ok" if envs or not live_ids
                        else "empty", len(envs), (time.monotonic() - t_env) * 1000.0)
        except Exception as exc:
            self.source("candystore-envelopes", "postgres", "events.raw by id (kept events only)", "error", 0,
                        (time.monotonic() - t_env) * 1000.0, f"{type(exc).__name__}: {exc}")
            self.gap(ARCHIVE, "kept events carry no envelope payloads", f"{type(exc).__name__}: {exc}", "warn")
        holo: dict[str, dict] = {}
        if holocene is not None and live_ids:
            t_h = time.monotonic()
            try:
                holo = holocene(live_ids)
                self.source("holocene", "sqlite", "Holocene events.sqlite3 by event id (kept events only)",
                            "ok" if holo else "empty", len(holo), (time.monotonic() - t_h) * 1000.0)
            except Exception as exc:
                self.source("holocene", "sqlite", "Holocene events.sqlite3 by event id (kept events only)", "error", 0,
                            (time.monotonic() - t_h) * 1000.0, f"{type(exc).__name__}: {exc}")

        # ---- chapter spans
        ch_events = Counter(it.chapter for it in items)
        ch_kept = Counter(it.chapter for it in kept.values())
        ch_batches = Counter(b.chapter for b in batches.values())
        ch_failed = Counter(it.chapter for it in items if it.failed)
        total_by_group = Counter(self._group(it.comp)[0] for it in items)
        ch_group: dict[int, Counter] = {}
        for it in items:
            ch_group.setdefault(it.chapter, Counter())[self._group(it.comp)[0]] += 1
        for n in range(n_ch):
            lo, hi = bounds[n], bounds[n + 1]
            title_who = self._dominant(ch_group.get(n, Counter()), total_by_group, len(items))
            name = f"{_hm(lo, spec.tz)}-{_hm(hi, spec.tz)} · {title_who}"
            ev_n = ch_events.get(n, 0)
            comps = len({it.comp for it in items if it.chapter == n}) if ev_n else 0
            self.spans.append({
                "id": f"chapter:{n + 1}", "kind": "chapter", "component": ARCHIVE, "name": name,
                "summary": (f"{ev_n} event(s) from {comps} component(s) between {_hm(lo, spec.tz)} and {_hm(hi, spec.tz)}: "
                            f"{ch_kept.get(n, 0)} kept, the rest in {ch_batches.get(n, 0)} batch(es)") if ev_n
                else f"Nothing matched between {_hm(lo, spec.tz)} and {_hm(hi, spec.tz)}.",
                "phase": "async_after", "t0": self.rel(lo), "t1": self.rel(hi),
                "status": "ok", "parent": None, "refs": {},
                "attrs": {"index": n + 1, "events": ev_n, "kept": ch_kept.get(n, 0), "batches": ch_batches.get(n, 0),
                          "failed": ch_failed.get(n, 0), "minutes": math.ceil((hi - lo) / 60_000.0),
                          "at": M.iso(lo), "until": M.iso(hi), "who": title_who},
                "evidence": [ARCHIVE],
            })

        # ---- batch spans
        rank: dict[int, int] = {}
        for b in sorted(batches.values(), key=lambda b: (b.chapter, -b.count, b.comp, b.type)):
            rank[b.chapter] = rank.get(b.chapter, 0) + 1
            st = short_type(b.type)
            mins = math.ceil((bounds[b.chapter + 1] - bounds[b.chapter]) / 60_000.0)
            attrs = {"count": b.count, "type": b.type, "producers": [p for p, _ in b.producers.most_common()],
                     "chapter": b.chapter + 1, "per_minute": [b.minutes.get(m, 0) for m in range(max(1, mins))],
                     "exemplars": [] if b.type == "private" else _spread(b.ids), "failed": b.failed, "rank": rank[b.chapter]}
            if b.credit:
                attrs["credit"] = dict(b.credit.most_common(8))
            self.spans.append({
                "id": f"batch:{b.comp}:{st}:{b.chapter + 1}", "kind": "batch", "component": b.comp, "name": st,
                "summary": f"{b.count} × {st}", "phase": "async_after", "t0": self.rel(b.t0), "t1": self.rel(b.t1),
                "status": "failed" if b.failed else "ok", "parent": f"chapter:{b.chapter + 1}", "refs": {},
                "attrs": attrs, "evidence": [ARCHIVE],
            })

        # ---- kept events
        for it in sorted(kept.values(), key=lambda x: (x.clock_t, x.id)):
            self._kept_event(it, envs.get(it.id), holo.get(it.id))
        self._synthesize(kept, envs)

        # ---- findings
        for (comp, et), g in groups[:FINDING_GROUPS_MAX]:
            st = short_type(et)
            workers = Counter(x.worker for x in g if x.worker)
            prods = Counter(x.shown_producer for x in g)
            detail = (f"{len(g)} {st} event(s) reported a failure between {_hm(g[0].clock_t, spec.tz)} and "
                      f"{_hm(g[-1].clock_t, spec.tz)}, in {len({x.chapter for x in g})} chapter(s)"
                      + (f"; jobs: {', '.join(f'{w} ×{n}' for w, n in workers.most_common(5))}" if workers else "")
                      + (f"; producers: {', '.join(f'{p} ×{n}' for p, n in prods.most_common(3))}" if not workers else "") + ".")
            self.finding(failure_severity(et), f"{len(g)} × {st} at {self.reg.name_of(comp) if not comp.startswith(('hermes-desk:', 'tenant:')) else comp}",
                         detail, comp, [M.Ids.evt(i) for i in _spread([x.id for x in g])] + [ARCHIVE])
        if len(groups) > FINDING_GROUPS_MAX:
            rest = groups[FINDING_GROUPS_MAX:]
            self.finding("info", f"{len(rest)} more failure group(s) not listed",
                         f"{sum(len(g) for _k, g in rest)} failure event(s) in {len(rest)} smaller (component, type) group(s); "
                         "they are in their batches' attrs.failed.", ARCHIVE, [ARCHIVE])
        dead = [it for it in items if it.dead]
        if dead:
            by_reason: dict[tuple[str, str], list[Item]] = {}
            for it in dead:
                by_reason.setdefault((it.dead.get("reason") or "dead_letter", short_type(it.shown_type)), []).append(it)
            for (reason, st), g in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
                ids = _spread([x.id for x in g])
                err = (g[0].dead.get("error") or "")[:200]
                self.finding("broken", f"{len(g)} × {st} dead-lettered by Candystore ({reason})",
                             f"Candystore refused {len(g)} {st} event(s) from {', '.join(sorted({x.shown_producer for x in g})[:4])}"
                             f" ({reason}{': ' + err if err else ''}). They never reached the archive; they appear here as "
                             "events whose candystore-events consumer outcome is dropped.", ARCHIVE,
                             [M.Ids.evt(i) for i in ids] + [ARCHIVE])
                self.gap(ARCHIVE, f"{len(g)} {st} event(s) were dead-lettered, not archived",
                         f"dead_letter reason {reason}; Candystore emits no event when it drops one", "warn",
                         M.Ids.publish(ids[0]))
        n_unres = len(unresolved)
        if unresolved:
            n_ev = sum(len(g) for g in unresolved.values())
            names = (", ".join(f"{p} ×{len(g)}" for p, g in sorted(unresolved.items(), key=lambda kv: -len(kv[1]))[:12])
                     if not self.public else f"{n_unres} producer name(s) withheld in the public profile")
            ev_ids = [M.Ids.evt(x.id) for g in unresolved.values() for x in g if x.id in kept][:9]
            self.finding("warn", f"{n_ev} event(s) from {n_unres} producer(s) resolve to no component",
                         f"Not a registry producer, source rule, tenant or desk: {names}. They sit at the 'unknown' kiosk "
                         "until components/*.yaml gains a surface for them.", "unknown", ev_ids + [ARCHIVE])

        # ---- the frame: prompt, turn, components
        label = spec.label or window_label("window", spec.since, spec.until, spec.tz)[0]
        prompt_text = self.prompt_text()
        self.spans.append({"id": M.Ids.PROMPT, "kind": "prompt", "component": ARCHIVE, "name": "query",
                           "summary": prompt_text, "phase": "prompt_submit", "t0": 0.0, "t1": 0.0, "status": "ok",
                           "sync": True, "parent": None, "refs": {}, "attrs": {"derived": "query"}, "evidence": []})
        self.spans.append({"id": M.Ids.TURN, "kind": "turn", "component": ARCHIVE, "name": "query",
                           "summary": f"The archive replays {total + n_dead} event(s): {label}.", "phase": "prompt_submit",
                           "t0": 0.0, "t1": self.rel(spec.until), "status": "ok", "parent": None, "refs": {},
                           "attrs": {"derived": "query"}, "evidence": []})
        for note in notes or []:
            self.gap(*note)
        self.gap(ARCHIVE, "commands (bloodbank.cmd.> / rpy.>) are not in this replay",
                 "Candystore archives only bloodbank.evt.>; BLOODBANK_COMMANDS is a 24 h workqueue nobody archives "
                 "(Bloodbank design ticket, I-10.2)", "info")

        # ---- conservation
        kept_n = len(kept)
        batched_n = sum(b.count for b in batches.values())
        ok = (kept_n + batched_n == total + n_dead) and fetched == total
        if not ok:
            self.gap(ARCHIVE, "conservation check failed: the replay does not account for every matched event",
                     f"kept {kept_n} + batched {batched_n} = {kept_n + batched_n}, but Candystore counted {total} and "
                     f"{n_dead} dead letter(s) were handled ({total + n_dead}); the pages returned {fetched} row(s)", "broken")
            self.finding("broken", "conservation check failed", f"kept {kept_n} + batched {batched_n} != "
                         f"total {total} + dead letters {n_dead} (pages returned {fetched})", ARCHIVE, [ARCHIVE])

        comps = self._components()
        spans = sorted(self.spans, key=lambda s: (s["t0"] if s["t0"] is not None else 0.0, _KIND_ORDER.get(s["kind"], 9), s["id"]))
        events = sorted(self.events, key=lambda e: (e["t"], e["id"]))
        stats: dict[str, Any] = {
            "query_total": total, "kept_events": kept_n, "batched_events": batched_n, "batches": len(batches),
            "chapters": n_ch, "dead_letters": n_dead, "conservation_ok": ok, "unresolved_producers": n_unres,
            "fetched_rows": fetched, "spans": len(spans), "events": len(events), "links": len(self.links),
            "artifacts": len(self.frag.artifacts), "gaps": len(self.gaps), "findings": len(self.findings),
            "components": len(comps), "failures": sum(1 for it in items if it.failed),
        }
        for s in spans:
            stats[f"spans_{s['kind']}"] = stats.get(f"spans_{s['kind']}", 0) + 1
        qid = spec.query_id()
        origin_query = {"since": M.iso(spec.since), "until": M.iso(spec.until), "clock": spec.clock,
                        "filters": {k: spec.filters[k] for k in FILTER_KEYS if spec.filters.get(k)},
                        "total": total, "dead_letters": n_dead, "candystore": CANDYSTORE_URL, "label": label,
                        "tz": spec.tz, "as_of": M.iso(as_of) if as_of else None}
        wb = {
            "format": FORMAT, "version": SCHEMA_VERSION,
            "id": waybill_id(spec.since, qid, "query"),
            "title": f'candystore query · "{label}" · {fmt_duration(spec.until - spec.since)}',
            "recorded_at": _iso_now(),
            "recorder": {"name": "waybill", "version": VERSION, "host": socket.gethostname(), "mode": MODE,
                         "profile": spec.profile},
            "origin": {"cli": "candystore", "surface": "query", "session_id": qid, "turn_id": None, "turn_index": None,
                       "cwd": None, "project": spec.filters.get("project") or None, "model": None, "query": origin_query},
            "prompt": {"text": prompt_text, "chars": len(prompt_text), "sha256": M.sha256(prompt_text), "truncated": False},
            "clock": {"t0": M.iso(spec.since), "t_end": M.iso(spec.until), "duration_ms": round(spec.until - spec.since, 1),
                      "settle_ms": 0.0, "turn_end_ms": self.rel(spec.until)},
            "components": comps, "spans": spans, "events": events, "links": self.links,
            "artifacts": self.frag.artifacts, "gaps": self.gaps, "findings": self.findings,
            "sources": self.sources, "stats": stats,
        }
        return apply_profile(wb, spec.profile)

    # -- pieces
    def prompt_text(self) -> str:
        spec = self.spec
        when = spec.when or window_label("window", spec.since, spec.until, spec.tz)[1]
        f = describe_filters(spec.filters)
        return f"You asked the archive: {'every event matching ' + f if f else 'everything the company did'} {when}"

    def _group(self, cid: str) -> tuple[str, str]:
        if cid.startswith("hermes-desk:"):
            return "hermes-desk:*", "the PM desks"
        if cid.startswith(self.reg.tenants.get("prefix", "tenant:")):
            return "tenant:*", "the tenant annex"
        if cid == self.reg.unknown:
            return cid, "unattributed producers"
        return cid, self.reg.name_of(cid)

    def _dominant(self, here: Counter, overall: Counter, n_all: int) -> str:
        """The chapter's title: the one or two groups most characteristic of it (count weighted by lift)."""
        n_here = sum(here.values())
        if not n_here:
            return "quiet"
        names = {}
        scored = []
        for g, n in here.items():
            share = n / n_here
            if share < 0.05 and len(here) > 1:
                continue
            lift = share / (overall[g] / n_all) if overall[g] and n_all else 1.0
            scored.append((-(n * lift), g))
        scored.sort()
        top = [g for _s, g in scored[:2]]
        if len(top) == 2 and here[top[0]] / n_here >= 0.75 and here[top[1]] / n_here < 0.1:
            top = top[:1]
        for g in top:
            names[g] = self._group(g if g != "hermes-desk:*" and g != "tenant:*" else ("hermes-desk:x" if g == "hermes-desk:*" else "tenant:x"))[1]
        return " and ".join(names[g] for g in top) or "quiet"

    def _kept_event(self, it: Item, rec: dict | None, holo: dict | None) -> None:
        spec = self.spec
        env = (it.dead or {}).get("_env") if it.dead else ((rec or {}).get("raw") if isinstance((rec or {}).get("raw"), dict) else None)
        env = env or {}
        et = it.type
        subject = env.get("subject") or (CS.normalize_type(env)[1] if env else None) or ("bloodbank.evt." + short_type(et) if et.startswith("bloodbank.") else None)
        ra = M.ms((rec or {}).get("received_at")) or it.ra
        chapter = f"chapter:{it.chapter + 1}"
        pub = M.Ids.publish(it.id)
        dead = it.dead is not None
        consumers = [{"name": CONSUMER, "component": ARCHIVE, "kind": "durable", "filter": "bloodbank.evt.>",
                      "outcome": "dropped" if dead else "archived",
                      "t": self.rel(M.ms(it.dead.get("received_at")) if dead else ra), "evidence": "observed", "span": None}]
        stream = seq = stored = None
        if holo:
            stream, seq, stored = holo.get("stream"), holo.get("sequence"), M.ms(holo.get("collected_at"))
            consumers.append({"name": "holocene", "component": "holocene", "kind": "ephemeral", "filter": "bloodbank.evt.>",
                              "outcome": "collected", "t": self.rel(stored), "evidence": "observed", "span": None})
        payload = None
        if env and not (self.public and it.aliased):
            shaped = dict(env)
            if self.public and short_type(et).startswith("conversation.") and isinstance(shaped.get("data"), dict):
                shaped["data"] = {k: "«dropped»" for k in shaped["data"]}
            elif self.public and short_type(et).startswith("agent.tool.") and isinstance(shaped.get("data"), dict):
                # a tool call's arguments are the agent's working notes (shell lines, file paths): names only
                d = dict(shaped["data"])
                if isinstance(d.get("arguments"), dict):
                    d["arguments"] = {k: "«dropped»" for k in d["arguments"]}
                shaped["data"] = d
            payload = CS.envelope_artifact(self.frag, shaped, spec.profile,
                                           "Candystore dead_letter.raw" if dead else None)
        ev = {"id": it.id, "type": et, "subject": subject, "stream": stream or "BLOODBANK_EVENTS",
              "seq": int(seq) if isinstance(seq, (int, float)) else None, "t": self.rel(it.t),
              "stored": self.rel(stored), "archived": None if dead else self.rel(ra),
              "correlationid": env.get("correlationid"), "causationid": env.get("causationid"),
              "producer": it.shown_producer, "publisher_span": pub, "consumers": consumers}
        if payload:
            ev["payload"] = payload
        if env.get("type") and env.get("type") != et:
            ev["stored_type"] = env["type"]
        self.events.append(ev)
        status = "dropped" if dead else ("failed" if it.failed else "ok")
        reason = (it.dead.get("reason") if dead else None)
        attrs = {"type": et, "producer": it.shown_producer, "at": M.iso(it.t), "chapter": it.chapter + 1, "keep": it.keep,
                 "resolved_via": it.via}
        if it.owner and it.owner != it.comp:
            attrs["owner"] = it.owner
        if it.worker:
            attrs["job"] = it.worker
        span = {"id": pub, "kind": "publish", "component": it.comp, "name": short_type(et),
                "summary": self._describe(it, env), "phase": "async_after", "t0": self.rel(it.t), "t1": None,
                "status": status, "reason": reason, "parent": chapter, "refs": {"event_id": it.id}, "attrs": attrs,
                "evidence": [ARCHIVE]}
        if reason is None:
            span.pop("reason")
        self.spans.append(span)
        self.links.append({"from": pub, "to": M.Ids.evt(it.id), "kind": "publishes"})

    def _describe(self, it: Item, env: dict) -> str:
        st = short_type(it.type)
        data = env.get("data") if isinstance(env.get("data"), dict) else {}
        who = it.shown_producer
        if it.dead:
            err = (it.dead.get("error") or "")[:160]
            return f"{who} published {st}; Candystore dead-lettered it ({it.dead.get('reason') or 'dead_letter'}{': ' + err if err else ''})."
        if st.startswith("cron.candybar.") and data.get("name"):
            err = data.get("error") if isinstance(data.get("error"), dict) else {}
            tail = f": {str(err.get('message'))[:160]}" if err.get("message") else (f" (exit {data.get('exit_code')})" if data.get("exit_code") not in (None, 0) else "")
            return f"Candybar job {data['name']} {st.rsplit('.', 1)[-1]}{tail}."
        if st.startswith("agent.tool.") and data.get("tool_name"):
            out = f", outcome {data['outcome']}" if data.get("outcome") else ""
            return f"{who} {st.rsplit('.', 1)[-1]} tool {data['tool_name']}{out}."
        if st.startswith("llm.usage.") and data:
            return (f"Gateway usage for {data.get('returned_model') or data.get('native_model') or 'a model call'}"
                    f" ({data.get('outcome') or '?'}, {data.get('latency_ms') or '?'} ms).")
        if it.type == HOOK_MIRROR:
            inv = data.get("invocation") if isinstance(data.get("invocation"), dict) else {}
            bad = [e.get("handler_id") for e in inv.get("executions") or [] if isinstance(e, dict) and e.get("status") in ("failed", "timed_out")]
            return (f"hook-hub mirrored {inv.get('native') or 'a hook'} ({inv.get('status') or '?'})"
                    + (f"; failed: {', '.join(str(b) for b in bad[:4])}" if bad else "") + ".")
        return f"{who} published {st}" + (" (it reports a failure)" if it.failed else "") + "."

    def _synthesize(self, kept: dict[str, Item], envs: dict[str, dict]) -> None:
        """tool:<tool_use_id>, llm:<request_id> and hook:<inv> (+ handlers) from kept events."""
        tools: dict[str, dict[str, tuple[Item, dict]]] = {}
        llms: dict[str, list[tuple[Item, dict]]] = {}
        hooks: dict[str, tuple[Item, dict]] = {}
        for it in kept.values():
            if it.dead:
                continue
            env = (envs.get(it.id) or {}).get("raw")
            data = env.get("data") if isinstance(env, dict) and isinstance(env.get("data"), dict) else None
            if data is None:
                continue
            if it.type in TOOL_TYPES and data.get("tool_call_id"):
                tools.setdefault(str(data["tool_call_id"]), {})[it.type.rsplit(".", 1)[-1]] = (it, data)
            elif it.type in USAGE_TYPES and data.get("request_id"):
                llms.setdefault(str(data["request_id"]), []).append((it, data))
            elif it.type == HOOK_MIRROR and isinstance(data.get("invocation"), dict):
                inv = data["invocation"].get("invocation_id") or env.get("correlationid")
                prev = hooks.get(inv)
                rev = data.get("revision") or 0
                if inv and (prev is None or rev >= (prev[1].get("revision") or 0)):
                    hooks[inv] = (it, data)
        for tuid, pair in tools.items():
            req, comp = pair.get("requested"), pair.get("completed")
            first = (req or comp)[0]
            tool_comp = self._cli_component(first.producer, first.comp)
            data = (req or comp)[1]
            failed = bool(comp and comp[0].failed)
            sid = M.Ids.tool(tuid)
            self.spans.append({
                "id": sid, "kind": "tool", "component": tool_comp, "name": str(data.get("tool_name") or "tool"),
                "summary": f"{first.shown_producer} ran {data.get('tool_name') or 'a tool'}"
                           + (f", outcome {comp[1].get('outcome')}" if comp and comp[1].get("outcome") else "")
                           + ("" if req and comp else " (only one side of the call is in this replay)") + ".",
                "phase": "tool", "t0": self.rel((req or comp)[0].t), "t1": self.rel(comp[0].t) if comp else None,
                "status": "failed" if failed else ("ok" if comp else "pending"), "sync": True,
                "parent": f"chapter:{first.chapter + 1}", "refs": {"tool_use_id": tuid, "event_id": first.id},
                "attrs": {"tool": data.get("tool_name"), "requested": req[0].id if req else None,
                          "completed": comp[0].id if comp else None}, "evidence": [ARCHIVE]})
            for side in (req, comp):
                if side:
                    self.links.append({"from": sid, "to": M.Ids.evt(side[0].id), "kind": "records",
                                       "label": side[0].type.rsplit(".", 1)[-1]})
        for rid, evs in llms.items():
            usage = next(((i, d) for i, d in evs if i.type == USAGE_TYPES[0]), evs[0])
            it, d = usage
            end = M.ms(d.get("occurred_at")) or it.t
            lat = d.get("latency_ms") if isinstance(d.get("latency_ms"), (int, float)) else None
            u = d.get("usage") if isinstance(d.get("usage"), dict) else {}
            sid = f"llm:{rid if not rid.isdigit() else 'req-' + rid}"
            self.spans.append({
                "id": sid, "kind": "llm", "component": GATEWAY,
                "name": str(d.get("returned_model") or d.get("native_model") or d.get("route") or "model call"),
                "summary": f"A {d.get('returned_model') or d.get('native_model') or 'model'} call through the gateway"
                           f" ({d.get('outcome') or 'observed'}"
                           + (f", {u.get('input_tokens')} in / {u.get('output_tokens')} out" if u else "") + ").",
                "phase": "model_call", "t0": self.rel(end - lat if lat is not None else end), "t1": self.rel(end),
                "status": "failed" if it.failed else "ok", "parent": f"chapter:{it.chapter + 1}",
                "refs": {"request_id": rid, "event_id": it.id},
                "attrs": {"route": d.get("route"), "model_served": d.get("returned_model"), "model_requested": d.get("requested_model"),
                          "latency_ms": lat, "outcome": d.get("outcome"), "usage": u or None,
                          "session_id": d.get("session_id"), "service_call": True}, "evidence": [ARCHIVE]})
            for i, _d in evs:
                self.links.append({"from": sid, "to": M.Ids.evt(i.id), "kind": "records", "label": short_type(i.type)})
        for inv, (it, data) in hooks.items():
            iv = data["invocation"]
            tl = [M.ms(x.get("at")) for x in iv.get("timeline") or [] if isinstance(x, dict) and x.get("at")]
            t0 = M.ms(iv.get("received_at")) or (min(tl) if tl else it.t)
            t1 = M.ms(iv.get("updated_at")) or (max(tl) if tl else None)
            hid = M.Ids.hook(inv)
            self.spans.append({
                "id": hid, "kind": "hook", "component": "hook-hub", "name": str(iv.get("native") or "hook"),
                "summary": f"hook-hub ran {iv.get('native') or 'a hook'} for {iv.get('cli') or 'an agent'} ({iv.get('status') or '?'}).",
                "phase": _HOOK_PHASE.get(str(iv.get("role") or ""), "async_after"), "t0": self.rel(t0), "t1": self.rel(t1),
                "status": _EXEC_STATUS.get(str(iv.get("status")), "unknown"), "parent": f"chapter:{it.chapter + 1}",
                "refs": {"invocation_id": inv, "event_id": it.id},
                "attrs": {"native": iv.get("native"), "cli": iv.get("cli"), "role": iv.get("role")}, "evidence": [ARCHIVE]})
            self.links.append({"from": hid, "to": M.Ids.evt(it.id), "kind": "mirrors", "label": "hook.updated"})
            for e in iv.get("executions") or []:
                if not isinstance(e, dict) or not e.get("handler_id"):
                    continue
                hs = M.Ids.handler(inv, str(e["handler_id"]))
                span = {"id": hs, "kind": "handler", "component": "hook-hub", "name": str(e["handler_id"]),
                        "summary": f"{e['handler_id']} {e.get('status') or '?'}" + (f" ({e['reason']})" if e.get("reason") else "")
                                   + (f" in {e['duration_ms']} ms" if isinstance(e.get("duration_ms"), (int, float)) else "") + ".",
                        "phase": _HOOK_PHASE.get(str(iv.get("role") or ""), "async_after"),
                        "t0": self.rel(M.ms(e.get("started_at")) or M.ms(e.get("selected_at")) or t0),
                        "t1": self.rel(M.ms(e.get("finished_at"))), "status": _EXEC_STATUS.get(str(e.get("status")), "unknown"),
                        "reason": e.get("reason"), "sync": e.get("mode") == "sync", "parent": hid,
                        "refs": {"invocation_id": inv, "handler_id": e["handler_id"]},
                        "attrs": {"handler_id": e["handler_id"], "mode": e.get("mode"), "duration_ms": e.get("duration_ms")},
                        "evidence": [ARCHIVE]}
                if e.get("reason") is None:
                    span.pop("reason")
                if e.get("event_id"):
                    span["refs"]["event_id"] = e["event_id"]
                    if e["event_id"] in kept:
                        self.links.append({"from": hs, "to": M.Ids.publish(e["event_id"]), "kind": "calls"})
                self.spans.append(span)

    def _cli_component(self, producer: str, fallback: str) -> str:
        """Tools run in the CLI (its bay), whoever published the event."""
        cid = self.reg.canonical(f"ext:{producer}") if producer else None
        return cid if cid and cid.startswith("ext:") else fallback

    def _components(self) -> dict[str, dict]:
        ids: set[str] = set()
        for s in self.spans:
            ids.add(s["component"])
        for e in self.events:
            for c in e["consumers"]:
                ids.add(c["component"])
        out = {}
        for cid in sorted(ids):
            rec = component_record(cid)
            name = self.reg.name_of(cid)
            if cid.startswith("hermes-desk:"):
                kind = "service"
            elif cid.startswith(self.reg.tenants.get("prefix", "tenant:")):
                kind = "external"
            else:
                kind = rec["kind"] if rec["kind"] != "external" or cid.startswith("ext:") else "service"
                if cid in self.reg.extras and self.reg.extras[cid].get("station") == "bays":
                    kind = "cli"
            out[cid] = {"id": cid, "name": name, "kind": kind, "registry": self.reg.is_registry(cid)}
        return out


_KIND_ORDER = {"prompt": 0, "turn": 1, "chapter": 2, "batch": 3}
_EXEC_STATUS = {"succeeded": "ok", "failed": "failed", "timed_out": "timeout", "skipped": "skipped",
                "received": "pending", "selected": "pending", "started": "pending", "interrupted": "failed"}
_HOOK_PHASE = {"pre_tool": "pre_tool", "post_tool": "post_tool", "prompt": "prompt_submit", "prompt_submit": "prompt_submit",
               "stop": "turn_end", "session_start": "session_start", "session_end": "session_end"}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# ---------------------------------------------------------------- run, write, budget

def run(spec: QuerySpec, reader: PsqlReader | None = None, registry: Registry | None = None,
        manifests: dict[str, str] | None = None, holocene: bool = True,
        progress: Callable[[str], None] | None = None) -> dict:
    """Read the archive for spec and build the waybill. Raises on a read error the waybill cannot explain."""
    from .registry import candybar_manifests
    reader = reader or PsqlReader()
    say = progress or (lambda s: None)
    notes: list[tuple[str, str, str]] = []
    t_all = time.monotonic()
    now = reader.now_ms()
    as_of = now - 2000.0
    if spec.until > now + 5000.0:
        notes.append((ARCHIVE, "the window ends in the future", f"cut at {M.iso(as_of)}, the archive's present", "info"))
    if spec.clock == "received_at":
        notes.append((ARCHIVE, "received_at clock: rows whose envelope time is more than 24 h from their archive time are missed",
                      "events has no received_at index yet (CANDYS-55), so the read is bounded by time ± 24 h", "info"))
    b = Builder(spec, registry, manifests if manifests is not None else candybar_manifests(), progress)
    t0 = time.monotonic()
    where = reader.where(spec.filters)
    b.source("candystore-filters", "python", f"docker exec {getattr(reader, 'app', APP_CONTAINER)} candystore.query._filters",
             "ok", len([k for k in spec.filters if spec.filters[k]]), (time.monotonic() - t0) * 1000.0)
    t0 = time.monotonic()
    total = reader.count(spec, where, as_of)
    say(f"  candystore count   {total:>8} events  {(time.monotonic() - t0) * 1000:>7.0f} ms")
    t0 = time.monotonic()
    rows = list(reader.rows(spec, where, as_of))
    read_ms = (time.monotonic() - t0) * 1000.0
    say(f"  candystore headers {len(rows):>8} rows    {read_ms:>7.0f} ms  ({getattr(reader, 'pages', 0)} page(s))")
    b.source(ARCHIVE, getattr(reader, "kind", "postgres"), getattr(reader, "locator", "candystore"), "ok" if rows else "empty",
             len(rows), read_ms)
    dead: list[dict] = []
    if spec.include_dead_letters:
        unmatchable = sorted(k for k in spec.filters if spec.filters[k] and k not in _DEAD_MATCHABLE)
        t0 = time.monotonic()
        if unmatchable:
            b.source("candystore-dead-letters", "postgres", "dead_letter by received_at", "skipped", 0, 0.0,
                     f"filters {', '.join(unmatchable)} need Candystore's SQL; a dead letter has only its raw bytes")
            notes.append((ARCHIVE, "dead letters left out", f"the {', '.join(unmatchable)} filter(s) cannot be matched "
                          "against a dead letter's raw bytes", "info"))
        else:
            try:
                raw = reader.dead_letters(spec, as_of)
                for d in raw:
                    d["_env"] = _dead_env(d)
                dead = [d for d in raw if _dead_matches(d["_env"], spec.filters)]
                b.source("candystore-dead-letters", "postgres", "dead_letter by received_at (read-only)",
                         "ok" if dead else "empty", len(dead), (time.monotonic() - t0) * 1000.0)
            except Exception as exc:
                b.source("candystore-dead-letters", "postgres", "dead_letter by received_at", "error", 0,
                         (time.monotonic() - t0) * 1000.0, f"{type(exc).__name__}: {exc}")
                notes.append((ARCHIVE, "dead letters could not be read", f"{type(exc).__name__}: {exc}", "warn"))
    holo = None
    if holocene:
        from .collectors import holocene as H
        holo = H.lookup
    wb = b.build(rows, total, dead, reader.envelopes, holo, as_of, notes)
    wb["stats"]["wall_ms"] = round((time.monotonic() - t_all) * 1000.0, 1)
    return wb


def dumps(wb: dict) -> bytes:
    return (json.dumps(wb, ensure_ascii=False, separators=(",", ":"), default=str) + "\n").encode("utf-8")


def encode(wb: dict, gz: bool) -> bytes:
    raw = dumps(wb)
    return gzip.compress(raw, compresslevel=9, mtime=0) if gz else raw


def fit_budget(wb: dict, max_bytes: int, gz: bool) -> tuple[dict, int]:
    """Shrink the written file to max_bytes, cheapest loss first: envelope payloads, then handler spans.
    Batches, kept events and the conservation stats are never touched."""
    size = len(encode(wb, gz))
    if size <= max_bytes:
        return wb, size
    dropped = []
    if wb.get("artifacts"):
        n = len(wb["artifacts"])
        wb["artifacts"] = {}
        for e in wb.get("events") or []:
            e.pop("payload", None)
        dropped.append(f"{n} envelope payload(s)")
        size = len(encode(wb, gz))
    if size > max_bytes:
        hs = {s["id"] for s in wb["spans"] if s["kind"] == "handler"}
        if hs:
            wb["spans"] = [s for s in wb["spans"] if s["id"] not in hs]
            wb["links"] = [ln for ln in wb["links"] if ln["from"] not in hs and ln["to"] not in hs]
            dropped.append(f"{len(hs)} handler span(s)")
            size = len(encode(wb, gz))
    if dropped:
        wb["findings"].append({"severity": "info", "title": f"--max-kb {max_bytes // 1024}: dropped {', '.join(dropped)}",
                               "detail": "the file was over budget; batches, kept events and the counts are whole",
                               "component": "waybill", "evidence": []})
    if size > max_bytes:
        wb["gaps"].append({"component": "waybill", "what": f"still {size // 1024} KiB, over --max-kb {max_bytes // 1024}",
                           "why": "batches and kept events are never dropped", "severity": "warn", "span": None})
    wb["stats"]["findings"], wb["stats"]["gaps"] = len(wb["findings"]), len(wb["gaps"])
    return wb, len(encode(wb, gz))
