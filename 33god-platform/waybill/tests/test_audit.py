"""Tests for waybill audit (fixtures only: no database, no NATS, no live journal; temp dirs for the file sources)."""
import asyncio
import base64
import json
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from waybill import audit as AU
from waybill import audit_sources as A
from waybill import query as Q
from test_query import REG, SINCE, UNTIL, FakeReader, fixture_rows, row, uid
from test_schema import SCHEMA, validate

HOUR = A.HOUR


class FakeArchive(A.Archive):
    """present() from a known id set, keys() from {type: [keys]}, json() from a callback (default: empty)."""

    def __init__(self, known=(), keys=None, json_fn=None):
        super().__init__(run=lambda sql, t: None)
        self.known, self.keymap, self.json_fn, self.sql = set(known), keys or {}, json_fn, []

    def json(self, sql):
        self.sql.append(sql)
        return self.json_fn(sql) if self.json_fn else []

    def present(self, ids):
        return set(ids) & self.known

    def keys(self, types, key_sql, lo, hi, extra=""):
        out = set()
        for t in types:
            out |= set(self.keymap.get(t, []))
        return out


def ctx(rows=(), dead=(), archive=None, public=True):
    return A.Ctx(since=SINCE, until=UNTIL, registry=REG, archive=archive or FakeArchive(), rows=list(rows), dead=list(dead),
                 public=public)


def b64(obj):
    return base64.b64encode(json.dumps(obj).encode()).decode()


class TestHelpers(unittest.TestCase):
    def test_verdict_table(self):
        self.assertEqual(A.verdict(0, 0), "covered")
        self.assertEqual(A.verdict(10, 0), "silent")
        self.assertEqual(A.verdict(10, 0, lost=True), "lost-in-transit")
        self.assertEqual(A.verdict(10, 10), "covered")
        self.assertEqual(A.verdict(10, 12), "covered")
        self.assertEqual(A.verdict(10, 7), "partial")
        self.assertEqual(A.verdict(10, 7, lost=True), "lost-in-transit")
        self.assertEqual(A.verdict(100, 96, tolerance=0.05), "covered")
        self.assertEqual(A.verdict(None, 3), "covered")
        self.assertEqual(A.verdict(None, 0), "silent")

    def test_parse_ts_takes_nanoseconds_and_offsets(self):
        self.assertAlmostEqual(A.parse_ts("2026-11-21T13:06:00.123456789Z"), 1795266360123.456, places=2)
        self.assertEqual(A.parse_ts("2026-11-21T13:06:00Z"), A.parse_ts("2026-11-21T08:06:00-05:00"))
        self.assertEqual(A.parse_ts("2026-11-21 13:06:00"), A.parse_ts("2026-11-21T13:06:00Z"))
        self.assertIsNone(A.parse_ts("yesterday"))

    def test_subject_match(self):
        self.assertTrue(A.subject_match("bloodbank.cmd.>", "bloodbank.cmd.audio.task.start"))
        self.assertTrue(A.subject_match("bloodbank.cmd.*.task.start", "bloodbank.cmd.audio.task.start"))
        self.assertFalse(A.subject_match("bloodbank.cmd.cron.>", "bloodbank.cmd.audio.task.start"))
        self.assertFalse(A.subject_match("bloodbank.cmd.>", "bloodbank.cmd"))
        self.assertTrue(A.subject_match(">", "a"))

    def test_private_types_never_named(self):
        self.assertTrue(A.is_private("bloodbank.messaging.telegram.received"))
        self.assertFalse(A.is_private("bloodbank.agent.tool.requested"))


# ---------------------------------------------------------------- the bus

def msg(seq, subj, mid, t):
    return A.BusMsg(seq, subj, mid, t)


class TestBusClassify(unittest.TestCase):
    def test_bus_msg_header_body_and_404(self):
        h = {"Nats-Sequence": "7", "Nats-Subject": "bloodbank.evt.a.b", "Nats-Msg-Id": "id-1",
             "Nats-Time-Stamp": "2026-11-21T13:06:00.5Z"}
        m = A.bus_msg(h, b"{}")
        self.assertEqual((m.seq, m.subject, m.id), (7, "bloodbank.evt.a.b", "id-1"))
        self.assertEqual(A.bus_msg({**h, "Nats-Msg-Id": ""}, json.dumps({"id": "from-body"}).encode()).id, "from-body")
        self.assertIsNone(A.bus_msg({**h, "Nats-Msg-Id": ""}, b"not json").id)
        self.assertIsNone(A.bus_msg({"Status": "404", "Description": "Message Not Found"}, b""))

    def test_every_message_is_proved_by_id(self):
        a, b, c, d = uid(), uid(), uid(), uid()
        msgs = [msg(1, "s.x", a, 1), msg(2, "s.x", a, 2),          # a archived, then a duplicate
                msg(3, "s.x", b, 3),                                # b dead-lettered by event_id
                msg(4, "s.y", c, 4),                                # c dead-lettered: only its raw bytes name it
                msg(5, "s.y", d, 5),                                # d: nobody holds it
                msg(6, "s.y", None, 6)]                             # no id at all: unprovable
        per = A.classify_bus(msgs, {a}, {b}, [json.dumps({"id": c, "type": "x"})])
        self.assertEqual(dict(per["s.x"]), {"msgs": 3, "archived": 1, "dup": 1, "dead": 1})
        self.assertEqual(per["s.y"]["dead"], 1)
        self.assertEqual(per["s.y"]["missing"], 2)
        self.assertEqual(per["s.y"]["no_id"], 1)
        for c_ in per.values():
            self.assertEqual(c_["msgs"], c_["archived"] + c_["dup"] + c_["dead"] + c_["missing"])
        self.assertEqual(dict(A.missing_ids(msgs, {a}, {b}, [c])), {"s.y": [d]})

    def test_command_bounds(self):
        self.assertEqual(A.command_bounds(100, 100, 200, 200), (100, 100))      # contiguous
        self.assertEqual(A.command_bounds(100, 150, 180, 400), (30, 300))       # sparse: retained 150 and 400
        self.assertEqual(A.command_bounds(100, None, 100, 400), (0, 300))       # nothing retained inside


class FakeBus(A.NatsBus):
    """NatsBus with the wire replaced: streams {name: {seq: BusMsg}}, STREAM.INFO / CONSUMER.LIST from fixtures."""

    def __init__(self, streams, subjects=None, consumers=None, fail=()):
        super().__init__(chunk=3)
        self.streams, self.subjects, self.cons, self.fail = streams, subjects or {}, consumers or {}, set(fail)

    async def open(self):
        return self

    async def close(self):
        return None

    async def api(self, subject, body):
        name = subject.rsplit(".", 1)[-1]
        if name in self.fail:
            raise RuntimeError(f"stream {name} not found")
        if ".CONSUMER.LIST." in subject:
            cs = self.cons.get(name, [])
            return {"consumers": cs[body.get("offset", 0):], "total": len(cs)}
        msgs = self.streams.get(name, {})
        st = {"first_seq": min(msgs) if msgs else 1, "last_seq": max(msgs) if msgs else 0, "consumer_count": len(self.cons.get(name, []))}
        if body.get("subjects_filter"):
            st["subjects"] = self.subjects.get(name) or dict(Counter(m.subject for m in msgs.values()))
        return {"state": st, "config": {"retention": "workqueue" if "COMMANDS" in name else "limits"}}

    async def get(self, stream, seq, next_=False):
        self.gets += 1
        msgs = self.streams.get(stream, {})
        if not next_:
            return msgs.get(seq)
        nxt = [s for s in msgs if s >= seq]
        return msgs[min(nxt)] if nxt else None


class TestBusAdapter(unittest.TestCase):
    def test_adapter_bus_end_to_end(self):
        t = lambda m: SINCE + m * 60_000.0  # noqa: E731
        ok1, ok2, late, lost = uid(), uid(), uid(), uid()
        ev = {1: msg(1, "bloodbank.evt.x.y", uid(), SINCE - HOUR),           # before the window
              2: msg(2, "bloodbank.evt.x.y", ok1, t(1)),
              3: msg(3, "bloodbank.evt.x.y", ok1, t(2)),                     # duplicate
              4: msg(4, "bloodbank.evt.x.y", ok2, t(3)),
              5: msg(5, "bloodbank.evt.a.b", late, t(4)),                    # archived, envelope time outside the window
              6: msg(6, "bloodbank.evt.a.b", lost, t(5)),                    # nobody holds it
              7: msg(7, "bloodbank.evt.x.y", uid(), UNTIL + HOUR)}           # after
        cmd = {10: msg(10, "bloodbank.cmd.audio.task.start", uid(), SINCE - HOUR),
               40: msg(40, "bloodbank.cmd.audio.task.start", uid(), t(10)),
               70: msg(70, "bloodbank.cmd.audio.task.start", uid(), t(20)),
               99: msg(99, "bloodbank.cmd.audio.task.start", uid(), UNTIL + 60_000)}
        gib = {1: msg(1, "gib.evt.thing", uid(), t(1))}
        bus = FakeBus({A.EVENTS_STREAM: ev, A.COMMANDS_STREAM: cmd, A.GIB_STREAM: gib},
                      consumers={A.COMMANDS_STREAM: [{"config": {"filter_subject": "bloodbank.cmd.cron.>"}}]})
        rows = [row(t(1), "candybar", "bloodbank.x.y", rid=ok1), row(t(3), "candybar", "bloodbank.x.y", rid=ok2),
                row(t(30), "hook-hub", "bloodbank.only.http")]                # archived, never on the bus
        out = A.adapter_bus(ctx(rows, archive=FakeArchive(known={late})), bus_factory=lambda: bus)
        top = out[0]
        self.assertEqual((top.expected, top.archived, top.verdict), (4, 3, "lost-in-transit"))
        self.assertEqual(top.detail["seq"], [2, 7])
        self.assertEqual(top.detail["subjects"]["bloodbank.evt.x.y"]["dup"], 1)
        self.assertEqual(top.detail["subjects"]["bloodbank.evt.a.b"]["missing"], 1)
        self.assertEqual(top.detail["subjects"]["(no bus subject)"]["archive_only"], 1)
        miss = [r for r in out if r.thing == "bus subject bloodbank.evt.a.b"]
        self.assertEqual(len(miss), 1)
        self.assertIn(lost, miss[0].evidence)
        cm = next(r for r in out if r.thing.startswith(A.COMMANDS_STREAM))
        self.assertEqual((cm.bound, cm.expected, cm.archived, cm.verdict), ("≥", 31, 0, "silent"))   # seqs 40..70
        self.assertEqual(cm.tickets, ["BB-48"])
        stranded = next(r for r in out if r.thing.startswith("stranded command"))
        self.assertEqual((stranded.expected, stranded.tickets), (4, ["BB-49"]))
        g = next(r for r in out if r.thing.startswith(A.GIB_STREAM))
        self.assertEqual((g.expected, g.archived, g.verdict, g.tickets), (1, 0, "silent", ["CANDYS-80"]))

    def test_a_missing_stream_degrades_to_a_row_not_a_crash(self):
        bus = FakeBus({A.EVENTS_STREAM: {1: msg(1, "bloodbank.evt.x.y", uid(), SINCE + 1000)}}, fail={A.COMMANDS_STREAM, A.GIB_STREAM})
        out = A.adapter_bus(ctx(), bus_factory=lambda: bus)
        self.assertEqual(out[0].expected, 1)
        self.assertTrue(any("could not read" in r.evidence for r in out))
        self.assertFalse(any(r.thing.startswith(A.GIB_STREAM) for r in out))

    def test_no_nats_is_a_skip(self):
        class Down(A.NatsBus):
            async def open(self):
                raise A.Skip("NATS unreachable: ConnectionRefusedError")
        with self.assertRaises(A.Skip):
            A.adapter_bus(ctx(), bus_factory=Down)


# ---------------------------------------------------------------- Candybar, hook-hub, gateway

class TestCandybar(unittest.TestCase):
    def test_runs_and_outcomes_by_invocation_id(self):
        db = {"inv": [["i1", "success", True], ["i2", "fail", True], ["i3", None, False]], "created": 1, "skips": 0, "steward": 2}
        types = Counter({"bloodbank.cron.tick.fired": 60, "bloodbank.cron.candybar.created": 1,
                         "bloodbank.cron.candybar.skipped": 5, "bloodbank.cron.candybar.steward.task.completed": 1})
        rows = {r.thing: r for r in A.classify_candybar(db, {"i1", "i2"}, {"i1"}, types, 60)}
        inv = rows["Candybar runs -> cron.candybar.invoked"]
        self.assertEqual((inv.expected, inv.archived, inv.verdict), (3, 2, "partial"))
        self.assertIn("i3", inv.evidence)
        fin = rows["Candybar finished runs -> completed | failed"]
        self.assertEqual((fin.expected, fin.archived, fin.verdict), (2, 1, "partial"))
        self.assertEqual(rows["scheduler minutes -> cron.tick.fired"].verdict, "covered")
        self.assertEqual(rows["occurrence skips -> cron.candybar.skipped"].verdict, "covered")
        self.assertEqual(rows["steward tasks -> steward events"].verdict, "partial")

    def test_unreachable_database_is_a_skip(self):
        orig = A.container_json
        A.container_json = lambda *a, **k: (_ for _ in ()).throw(A.Skip("candybar: No such container"))
        try:
            with self.assertRaises(A.Skip):
                A.adapter_candybar(ctx())
        finally:
            A.container_json = orig


def receipts_db(path, rows):
    con = sqlite3.connect(path)
    con.executescript("""
        create table invocations (invocation_id text primary key, cli text, native text, role text, event_type text,
            session_id text, identity_kind text, received_at text, updated_at text, status text, deduplicated integer);
        create table executions (invocation_id text, handler_id text, mode text, status text, reason text, selected_at text,
            started_at text, finished_at text, duration_ms real, exit_code integer, event_id text, event_type text, publish_status text);
    """)
    for inv, at, execs in rows:
        con.execute("insert into invocations values (?, 'claude', 'x', null, null, null, 'k', ?, ?, 'done', 0)", (inv, at, at))
        for h, st, reason, eid, et, ps in execs:
            con.execute("insert into executions values (?, ?, 'async', ?, ?, ?, null, null, null, null, ?, ?, ?)",
                        (inv, h, st, reason, at, eid, et, ps))
    con.commit()
    con.close()


class TestHookHub(unittest.TestCase):
    def test_receipts_vs_mirrors_publishes_deckard_and_skips(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "receipts.sqlite3"
            at = A.iso_z(SINCE + HOUR)
            e1, e2, dk = uid(), uid(), uid()
            receipts_db(p, [
                ("old", A.iso_z(SINCE - 3 * HOUR), []),
                ("inv-1", at, [("bloodbank-publisher", "succeeded", None, e1, "bloodbank.agent.tool.requested", "sent")]),
                ("inv-2", at, [("bloodbank-publisher", "succeeded", None, e2, "bloodbank.agent.tool.completed", "sent"),
                               ("bloodbank-publisher", "succeeded", None, dk, "deckard.v1.agent.attention", "sent")]),
                ("inv-3", at, [("bloodbank-publisher", "skipped", "missing_pane_context", None, None, "skipped")]),
            ])
            rec = A.read_receipts(p, SINCE, UNTIL)
            self.assertEqual(sorted(rec["inv"]), ["inv-1", "inv-2", "inv-3"])
            rows = {r.thing: r for r in A.classify_hookhub(rec, {"inv-1", "inv-2"}, {e1})}
        hu = rows["hook invocations -> agent.hook.updated"]
        self.assertEqual((hu.expected, hu.archived, hu.verdict), (3, 2, "partial"))
        pub = rows["hook publishes (bloodbank.*) -> Candystore ids"]
        self.assertEqual((pub.expected, pub.archived, pub.verdict), (2, 1, "lost-in-transit"))
        self.assertIn(e2, pub.evidence)
        self.assertEqual(rows["Deckard attention sends -> Candystore"].tickets, ["BB-47"])
        self.assertEqual(rows["Deckard attention sends -> Candystore"].verdict, "lost-in-transit")
        pane = rows["publisher skips (missing_pane_context)"]
        self.assertEqual((pane.expected, pane.verdict, pane.tickets), (1, "partial", ["BB-52"]))

    def test_window_before_retention_is_a_skip_and_a_missing_db_too(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "receipts.sqlite3"
            receipts_db(p, [("new", A.iso_z(UNTIL + HOUR), [])])
            with self.assertRaises(A.Skip):
                A.read_receipts(p, SINCE, UNTIL)
            with self.assertRaises(A.Skip):
                A.read_receipts(Path(d) / "nope.sqlite3", SINCE, UNTIL)


class TestGateway(unittest.TestCase):
    def test_ledger_ids_vs_usage_ids_with_a_late_lookup(self):
        calls = []

        def cj(container, var, sql, timeout=150.0):
            calls.append((container, var))
            return [1, 2, 3]

        class Arch(FakeArchive):
            def keys(self, types, key_sql, lo, hi, extra=""):
                return {"newapi-log:3"} if extra else {"newapi-log:1"}

        orig_j, orig_p = A.container_json, A.container_psql
        A.container_json = cj
        A.container_psql = lambda *a, **k: 7
        try:
            rows = A.adapter_gateway(ctx(archive=Arch()))
        finally:
            A.container_json, A.container_psql = orig_j, orig_p
        self.assertEqual(calls, [(A.LEDGER_CONTAINER, "AAI_LLM_DATABASE_URL")])
        g = rows[0]
        self.assertEqual((g.expected, g.archived, g.verdict), (3, 2, "partial"))
        self.assertIn("newapi-log:2", g.evidence)
        lite = rows[1]
        self.assertEqual((lite.expected, lite.archived, lite.verdict, lite.tickets), (7, 0, "silent", ["no board"]))


# ---------------------------------------------------------------- transcripts, Hermes

def jl(path, objs):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(o) + "\n" for o in objs))


class TestTranscripts(unittest.TestCase):
    def test_claude_and_codex_sessions_in_the_window(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            s_in, s_head, s_old = uid(), uid(), uid()
            at = A.iso_z(SINCE + HOUR)
            jl(root / "claude" / "-proj" / f"{s_in}.jsonl", [{"type": "summary"}, {"sessionId": s_in, "timestamp": at, "entrypoint": "cli"}])
            jl(root / "claude" / "-proj" / f"{s_head}.jsonl", [{"sessionId": s_head, "timestamp": at, "entrypoint": "sdk-cli"}])
            jl(root / "claude" / "-proj" / f"{s_old}.jsonl", [{"sessionId": s_old, "timestamp": A.iso_z(SINCE - 2 * A.DAY), "entrypoint": "cli"}])
            jl(root / "claude" / "-proj" / "subagents" / "x" / "deep.jsonl", [{"sessionId": uid(), "timestamp": at}])
            cx = uid()
            day = time.strftime("%Y/%m/%d", time.gmtime((SINCE + HOUR) / 1000))
            jl(root / "codex" / day / f"rollout-x-{cx}.jsonl", [{"type": "session_meta", "timestamp": at,
                                                                 "payload": {"id": cx, "timestamp": at, "originator": "codex_cli_rs"}}])
            cl = A.claude_sessions(root / "claude", SINCE, UNTIL)
            self.assertEqual(sorted(s["sid"] for s in cl), sorted([s_in, s_head]))
            co = A.codex_sessions(root / "codex", SINCE, UNTIL)
            self.assertEqual([s["sid"] for s in co], [cx])
        inter = A.classify_sessions("i", "claude-code", [s for s in cl if s["entrypoint"] == "cli"], {s_in}, set(), [])
        self.assertEqual((inter.expected, inter.archived, inter.verdict), (1, 1, "covered"))
        head = A.classify_sessions("h", "claude-code", [s for s in cl if s["entrypoint"] != "cli"], set(), {s_head}, ["not yet ticketed"])
        self.assertEqual((head.verdict, head.tickets), ("silent", ["not yet ticketed"]))
        self.assertIn("1 of them have other events", head.evidence)


def hermes_db(path, sessions, messages):
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript("create table sessions (id text, source text, started_at real, message_count integer, tool_call_count integer);"
                      "create table messages (session_id text, role text, timestamp real, tool_calls text);")
    con.executemany("insert into sessions values (?, ?, ?, ?, 0)", sessions)
    con.executemany("insert into messages values (?, ?, ?, ?)", messages)
    con.commit()
    con.close()


class TestHermes(unittest.TestCase):
    def test_sessions_tools_and_inbound_messages(self):
        t = (SINCE + HOUR) / 1000.0
        with tempfile.TemporaryDirectory() as d:
            hermes_db(Path(d) / "desk-a" / "state.db", [("s1", "telegram", t, 4), ("s2", "cron", t, 2), ("s3", "cron", t, 0)],
                      [("s1", "user", t, None), ("s1", "assistant", t, json.dumps([{"id": 1}, {"id": 2}])),
                       ("s2", "assistant", t, json.dumps([{"id": 3}])), ("s2", "assistant", t - 10 * 86400, json.dumps([{"id": 4}]))])
            st = A.read_hermes(Path(d), SINCE, UNTIL)
        self.assertEqual((sorted(st["sessions"]), st["tools"], st["tg"]), ([("s1", "telegram"), ("s2", "cron")], 3, 1))
        rows = {r.thing: r for r in A.classify_hermes(st, {"sessions": ["s1", "s2"], "started": ["s2"], "tools": 4, "tg": 0, "turns": 2})}
        self.assertEqual(rows["Hermes sessions with messages -> any desk event"].verdict, "covered")
        ss = rows["Hermes sessions -> session.started"]
        self.assertEqual((ss.expected, ss.archived, ss.verdict), (2, 1, "partial"))
        self.assertIn("telegram 0/1", ss.evidence)
        tools = rows["Hermes tool calls -> tool.requested"]
        self.assertEqual(tools.verdict, "partial")           # 4 published for 3 real calls: an over-count
        self.assertIn("over-count +1", tools.evidence)
        self.assertEqual(rows["Hermes inbound chat messages -> inbound message events"].verdict, "silent")
        self.assertTrue(all(r.tickets == ["BB-50"] for r in rows.values()))
        self.assertFalse(any("Telegram" in r.thing for r in rows.values()))

    def test_no_profiles_is_a_skip(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(A.Skip):
            A.read_hermes(Path(d), SINCE, UNTIL)


# ---------------------------------------------------------------- systemd, git, hindsight, crank

class TestSystemd(unittest.TestCase):
    def test_timers_exceptions_loops_failures(self):
        lines = [json.dumps({"MESSAGE_ID": "39f53479d3a045ac8e11786248231fbf", "USER_UNIT": "asm-sweep.service", "JOB_RESULT": "done"})] * 5
        lines += [json.dumps({"MESSAGE_ID": "be02cf6855d2428ba40df7e9d022f03d", "USER_UNIT": "asm-sweep.service"})]
        lines += [json.dumps({"MESSAGE_ID": "39f53479d3a045ac8e11786248231fbf", "USER_UNIT": "candybar-watchdog.service"})] * 2
        lines += [json.dumps({"MESSAGE_ID": "5eb03494b6584870a536b337290809b3", "USER_UNIT": "curator-serve.service"})] * 150
        lines += [json.dumps({"MESSAGE_ID": "d9b373ed55a64feb8242e02dbe79a49c", "USER_UNIT": "newapi-allowances.service"})] * 3
        lines += [json.dumps({"MESSAGE_ID": "fe6faa94e7774663a0da52717891d8ef", "UNIT": "app.slice"})]
        lines += [json.dumps({"MESSAGE_ID": "39f53479d3a045ac8e11786248231fbf", "USER_UNIT": "hermes-gateway.service"})] * 2
        lines += ["not json", json.dumps({"MESSAGE_ID": "unknown", "USER_UNIT": "x.service"})]
        journal = A.parse_journal(lines)
        self.assertEqual(journal["asm-sweep.service"]["done"], 5)
        timers = [{"unit": "asm-sweep.timer", "activates": "asm-sweep.service"},
                  {"unit": "candybar-watchdog.timer", "activates": "candybar-watchdog.service"},
                  {"unit": "systemd-tmpfiles-clean.timer", "activates": "systemd-tmpfiles-clean.service"}]
        policy = {"candybar-watchdog.timer": {"owner": "Candybar", "reason": "page-only self-watchdog (AD-22)"},
                  "systemd-tmpfiles-clean.timer": {"owner": "OS/vendor", "reason": "os"}}
        rows = A.classify_systemd(timers, policy, journal, Counter({"asm-sweep": 2}), REG, Counter(), props=lambda u: {"NRestarts": "9"})
        by = {r.thing: r for r in rows}
        asm = by["native timer asm-sweep.timer runs -> any event"]
        self.assertEqual((asm.expected, asm.archived, asm.verdict, asm.tickets), (6, 2, "partial", ["CAND-55", "BB-51"]))
        wd = by["native timer candybar-watchdog.timer runs -> any event"]
        self.assertEqual((wd.exempt, wd.verdict, wd.tickets), ("AD-22", "silent", []))
        self.assertFalse(any("tmpfiles" in r.thing for r in rows))
        loop = by["crash loop curator-serve.service -> any event"]
        self.assertEqual((loop.expected, loop.tickets), (150, ["DOCS-2"]))
        self.assertIn("NRestarts 9", loop.evidence)
        self.assertEqual(by["unit failures -> any failure event"].expected, 4)   # newapi 3 + an asm-sweep start failure
        self.assertEqual(by["unit failures -> any failure event"].tickets, ["MONI-3"])
        self.assertEqual(by["OOM kills -> any event"].expected, 1)
        gw = by["hermes-gateway (re)starts -> any event"]
        self.assertEqual((gw.expected, gw.verdict, gw.tickets), (2, "silent", ["INFR-156"]))


class TestGit(unittest.TestCase):
    def test_repos_worktrees_commits_and_pushes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "code"
            repo = root / "proj"
            repo.mkdir(parents=True)
            env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
                   "GIT_COMMITTER_EMAIL": "t@example.invalid", "PATH": "/usr/bin:/bin", "HOME": d}
            ts = int((SINCE + HOUR) / 1000)
            run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True,  # noqa: E731
                                            env={**env, "GIT_AUTHOR_DATE": f"@{ts}", "GIT_COMMITTER_DATE": f"@{ts}"})
            run("init", "-q")
            run("commit", "-q", "--allow-empty", "-m", "one")
            run("commit", "-q", "--allow-empty", "-m", "two")
            run("worktree", "add", "-q", str(root / "proj-wt"), "-b", "wt")
            reflog = repo / ".git" / "logs" / "refs" / "remotes" / "origin" / "main"
            reflog.parent.mkdir(parents=True)
            z = "0" * 40
            reflog.write_text(f"{z} {'a' * 40} t <t> {ts} +0000\tupdate by push\n{z} {'b' * 40} t <t> {ts} +0000\tfetch: fast-forward\n"
                              f"{z} {'c' * 40} t <t> {ts - 10 * 86400} +0000\tupdate by push\n")
            repos = A.find_repos(root)
            self.assertEqual(len(repos), 1)                       # the worktree folds into its repo
            self.assertEqual(len(A.reflog_pushes(Path(next(iter(repos))), SINCE, UNTIL)), 1)
            rows = A.adapter_git(ctx(), root=root)
        self.assertEqual((rows[0].expected, rows[0].archived, rows[0].verdict), (2, 0, "silent"))
        self.assertEqual((rows[1].expected, rows[1].tickets), (1, ["no board"]))


class TestHindsight(unittest.TestCase):
    def test_day_buckets_overlapping_the_window(self):
        def run(argv):
            if argv[1] == "bank":
                return json.dumps([{"bank_id": "a"}, {"bank_id": "b"}])
            if argv[3] == "b":
                raise A.Skip("exit 1")
            return json.dumps({"buckets": [{"time": A.iso_z(SINCE - 2 * A.DAY), "actions": {"retain": 50}},
                                           {"time": A.iso_z(SINCE - HOUR), "actions": {"retain": 3, "recall": 4}}]})
        r = A.adapter_hindsight(ctx(), run=run)[0]
        self.assertEqual((r.expected, r.archived, r.verdict), (7, 0, "silent"))
        self.assertIn("2 banks (1 unreadable)", r.evidence)


class TestCrank(unittest.TestCase):
    def test_sends_in_the_window(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sends.jsonl"
            jl(p, [{"ts": A.iso_z(SINCE + HOUR)}, {"ts": A.iso_z(SINCE - HOUR)}, {"nope": 1}])
            r = A.adapter_crank(ctx([row(SINCE + 1, "crank", "bloodbank.crank.nudge.sent")]), path=p)[0]
            self.assertEqual((r.expected, r.archived, r.verdict), (1, 1, "covered"))
            with self.assertRaises(A.Skip):
                A.adapter_crank(ctx(), path=Path(d) / "missing.jsonl")


# ---------------------------------------------------------------- declared, dead letters

class TestDeclared(unittest.TestCase):
    def test_schemas_registry_surfaces_and_unknown_producers(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for i, (t, k) in enumerate([("bloodbank.a.seen", "event"), ("bloodbank.a.never", "event"), ("bloodbank.a.dead", "event"),
                                        ("bloodbank.messaging.dm.sent", "event"), ("bloodbank.cmd.go", "command")]):
                (root / f"s{i}.json").write_text(json.dumps({"properties": {"type": {"const": t}, "kind": {"const": k}}}))
            (root / "junk.json").write_text("{nope")
            decl = A.declared_types(root)
        self.assertEqual(decl["bloodbank.cmd.go"], "command")
        rows = A.classify_declared(decl, {"bloodbank.a.seen"}, {"bloodbank.a.dead"},
                                   Counter({"bloodbank.a.seen": 3, "bloodbank.no.schema": 2}),
                                   {"candybar", "hook-hub", "hermes-agent:x"}, ["candybar", "mystery-box"], REG)
        by = {r.thing: r for r in rows}
        dn = by["schema-declared event types -> ever archived"]
        self.assertEqual((dn.expected, dn.archived, dn.verdict), (4, 2, "declared-never-seen"))
        self.assertIn("a.never", dn.evidence)
        self.assertNotIn("messaging", dn.evidence)               # a private type counts but is never named
        bare = by["archived types -> a Bloodbank schema"]
        self.assertEqual((bare.expected, bare.archived, bare.verdict, bare.tickets), (2, 1, "partial", ["BB-53"]))
        surf = by["registry producer surfaces -> ever seen"]
        self.assertEqual(surf.verdict, "declared-never-seen")    # claude-code and krebs never published here
        unk = by["window producers -> a registry component"]
        self.assertEqual((unk.expected, unk.archived), (2, 1))
        self.assertNotIn("mystery-box", unk.evidence)            # public profile: unresolved producers are not named


class TestDeadLetters(unittest.TestCase):
    def test_dead_letters_vs_dead_lettered_events_and_groups(self):
        dead = [{"_env": {"type": "bloodbank.repo.decision.recorded"}, "reason": "schema"},
                {"_env": {"type": "bloodbank.repo.decision.recorded"}, "reason": "schema"},
                {"_env": {"type": "bloodbank.messaging.dm.sent"}, "reason": "malformed"},
                {"_env": {}, "reason": "malformed"}]
        rows = A.classify_dead(dead, 0)
        self.assertEqual((rows[0].expected, rows[0].verdict, rows[0].tickets), (4, "silent", ["CANDYS-79"]))
        dec = next(r for r in rows if "decision" in r.thing)
        self.assertEqual((dec.expected, dec.verdict, dec.tickets), (2, "lost-in-transit", ["BB-46"]))
        self.assertTrue(any(r.thing == "dead-lettered a private type (malformed)" for r in rows))
        self.assertTrue(any("(unparseable)" in r.thing for r in rows))


# ---------------------------------------------------------------- the runner, the merge, the table

def fake_adapters(**fns):
    return {k: (fn, "fixture", f"/private/{k}", f"{k} fixture") for k, fn in fns.items()}


def raise_(exc):
    def f(c):
        raise exc
    return f


class TestRunner(unittest.TestCase):
    def test_skip_error_and_timeout_degrade_to_sources(self):
        good = lambda c: [A.Row("candybar", "t", "candybar", 1, 1, "covered", "e")]  # noqa: E731
        hang = lambda c: time.sleep(5) or []  # noqa: E731
        ad = fake_adapters(candybar=good, hookhub=raise_(A.Skip("receipts not found")), gateway=raise_(RuntimeError("boom")),
                           git=hang)
        rows, sources = AU.run_adapters(ctx(), list(ad), adapters=ad, timeout=0.5)
        st = {s["id"]: s for s in sources}
        self.assertEqual(len(rows), 1)
        self.assertEqual(st["audit:candybar"]["status"], "ok")
        self.assertEqual((st["audit:hookhub"]["status"], st["audit:hookhub"]["error"]), ("skipped", "receipts not found"))
        self.assertEqual(st["audit:gateway"]["status"], "error")
        self.assertIn("RuntimeError: boom", st["audit:gateway"]["error"])
        self.assertEqual(st["audit:git"]["status"], "error")
        self.assertIn("timed out", st["audit:git"]["error"])
        self.assertEqual(st["audit:candybar"]["locator"], "candybar fixture")    # public profile: no local path
        for s in sources:
            self.assertEqual(validate(s, SCHEMA["$defs"]["Source"], SCHEMA), [])

    def test_spec_rejects_unknown_adapters(self):
        with self.assertRaises(ValueError):
            AU.AuditSpec(only=["bus", "nope"]).adapters()
        self.assertEqual(AU.AuditSpec(skip=["bus"]).adapters()[0], "candybar")

    def test_window_ends_before_now_by_the_settle(self):
        s, u = AU.window(UNTIL, 1.0, settle_s=120)
        self.assertEqual((u, u - s), (UNTIL - 120_000.0, A.DAY))
        self.assertEqual(AU.window(UNTIL, 1.0, until=UNTIL + A.DAY, settle_s=0)[1], UNTIL)    # never past the archive's now


class TeeFake(FakeReader):
    def __init__(self, rows, dead=None):
        super().__init__(rows, dead)
        self.got, self.dead = [], []

    def now_ms(self):
        return UNTIL + 120_000.0

    def rows(self, spec, where, as_of):
        for r in self.rows_:
            if spec.since <= r.t < spec.until:
                self.got.append(r)
                yield r

    def count(self, spec, where, as_of):
        return sum(1 for r in self.rows_ if spec.since <= r.t < spec.until)

    def dead_letters(self, spec, as_of):
        self.dead = list(self.dead_)
        return self.dead


class TestMerge(unittest.TestCase):
    def build(self):
        span = (UNTIL - SINCE) / A.DAY
        rows_ = [r for r in fixture_rows() if r.t >= SINCE]
        ad = fake_adapters(
            bus=lambda c: [A.Row("bus", f"{A.EVENTS_STREAM} messages -> Candystore ids", "bloodbank", 10, 10, "covered", "ok",
                                 detail={"subjects": {"bloodbank.evt.x": {"msgs": 10, "archived": 10, "dup": 0, "dead": 0,
                                                                          "missing": 0, "no_id": 0, "archive_only": 0}}})],
            candybar=lambda c: [A.Row("candybar", "Candybar runs -> cron.candybar.invoked", "candybar", len(c.rows), 5, "partial", "x")],
            systemd=lambda c: [A.Row("systemd", "native timer asm-sweep.timer runs -> any event", "asm", 9, 0, "silent", "x",
                                     tickets=["CAND-55", "BB-51"]),
                               A.Row("systemd", "native timer candybar-watchdog.timer runs -> any event", "candybar-watchdog", 2, 0,
                                     "silent", "x", exempt="AD-22")],
            hookhub=lambda c: [A.Row("hookhub", "Deckard attention sends -> Candystore", "deckard", 3, 0, "lost-in-transit", "x",
                                     tickets=["BB-47"])],
            git=raise_(A.Skip("no repos")),
            declared=lambda c: [A.Row("declared", "schema-declared event types -> ever archived", "event-contract", 4, 2,
                                      "declared-never-seen", "x")],
        )
        spec = AU.AuditSpec(days=span, settle_s=120)
        return AU.run(spec, TeeFake(rows_), REG, adapters=ad, archive=FakeArchive(), manifests={}, holocene=False)

    def test_the_audit_is_a_valid_query_waybill(self):
        wb, rows = self.build()
        self.assertEqual(validate(wb, SCHEMA, SCHEMA), [])
        self.assertEqual(wb["recorder"]["mode"], "query")
        self.assertEqual(wb["origin"]["surface"], "query")
        self.assertTrue(wb["prompt"]["text"].startswith("You asked the archive: did everything that happened"))
        self.assertTrue(wb["origin"]["query"]["label"].startswith("audit · "))
        self.assertEqual(wb["origin"]["query"]["audit"]["adapters"], ["bus", "candybar", "hookhub", "systemd", "git", "declared"])
        self.assertTrue(wb["title"].startswith("waybill audit · "))
        self.assertTrue(wb["id"].startswith("wb_"))
        for v in wb["stats"].values():
            self.assertIsInstance(v, (int, float, bool))
        self.assertTrue(wb["stats"]["conservation_ok"])
        self.assertEqual(wb["stats"]["audit_rows"], len(rows))

    def test_findings_gaps_and_done_condition(self):
        wb, rows = self.build()
        titles = [f["title"] for f in wb["findings"]]
        self.assertIn("silent: native timer asm-sweep.timer runs -> any event [CAND-55, BB-51]", titles)
        sev = {f["title"].split(":", 1)[1].split(" [")[0].strip(): f["severity"] for f in wb["findings"]
               if (f["evidence"] or [""])[0].startswith("audit:")}
        self.assertEqual(sev["Deckard attention sends -> Candystore"], "broken")
        self.assertEqual(sev["native timer candybar-watchdog.timer runs -> any event"], "info")     # exempt
        gaps = [g["what"] for g in wb["gaps"]]
        self.assertIn("native timer asm-sweep.timer runs -> any event: silent", gaps)
        self.assertNotIn("native timer candybar-watchdog.timer runs -> any event: silent", gaps)
        self.assertIn("audit source git skipped", gaps)
        done = wb["audit"]["done"]
        self.assertEqual((done["silent"], done["lost"], done["bus_proven"], done["done"]), (1, 1, True, False))
        self.assertEqual(done["silent_rows"], ["native timer asm-sweep.timer runs -> any event"])
        self.assertIn("asm", wb["components"])
        self.assertEqual(wb["audit"]["bus"]["subjects"]["bloodbank.evt.x"]["msgs"], 10)
        self.assertNotIn("subjects", wb["audit"]["rows"][-1].get("detail", {}))     # the per-subject table lives once
        self.assertEqual(wb["audit"]["skipped"], [{"source": "git", "status": "skipped", "reason": "no repos"}])

    def test_table_and_done_lines(self):
        wb, rows = self.build()
        lines = AU.table(rows)
        self.assertTrue(lines[0].startswith("source"))
        self.assertTrue(any("silent (exempt)" in ln for ln in lines))
        self.assertEqual(len(lines), 2 + 2 * len(rows))
        d = AU.done_lines(wb["audit"]["done"])[0]
        self.assertIn("NOT DONE", d)
        self.assertIn("silent rows 1", d)
        self.assertIn("bus proven by id", d)
        js = json.loads(json.dumps(wb["audit"], default=str))
        self.assertEqual(js["version"], 1)


if __name__ == "__main__":
    unittest.main()
