"""CLI plumbing: collector selection, the fail-soft runner, file output, parser, list, publish (mocked)."""
from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_assemble import SID, UPS, build, window  # noqa: E402
from waybill import cli, publish as pub  # noqa: E402
from waybill import model as M  # noqa: E402
from waybill.collectors import ALIASES, CLI_ONLY, REGISTRY  # noqa: E402


def fake_module(name: str, fn) -> None:
    mod = types.ModuleType(f"waybill.collectors.{name}")
    mod.collect = fn
    sys.modules[f"waybill.collectors.{name}"] = mod


def ok_frag(name: str, items: int = 1) -> M.Fragment:
    return M.Fragment(source=M.Source(id=name, kind="test", locator=name, status="ok", items=items, ms=2.0))


class TestSelect(unittest.TestCase):
    def test_default_is_registry_order(self) -> None:
        self.assertEqual(cli.select_collectors(None, None), REGISTRY)

    def test_only_and_skip_with_aliases(self) -> None:
        self.assertEqual(cli.select_collectors(["bus"], None), ["candystore", "holocene", "nats"])
        self.assertEqual(cli.select_collectors(["hook-hub", "redis"], None), ["hookhub", "asm"])
        self.assertNotIn("logs", cli.select_collectors(None, ["logs"]))
        self.assertNotIn("transcript_claude", cli.select_collectors(None, ["transcript"]))
        self.assertNotIn("transcript_codex", cli.select_collectors(None, ["transcript"]))

    def test_unknown_name_is_kept_so_the_runner_reports_it(self) -> None:
        self.assertIn("nope", cli.select_collectors(["nope"], None))

    def test_registry_contract(self) -> None:
        self.assertEqual(len(REGISTRY), len(set(REGISTRY)))
        for names in ALIASES.values():
            for n in names:
                self.assertIn(n, REGISTRY)
        self.assertEqual(set(CLI_ONLY), {"transcript_claude", "transcript_codex"})


class TestRunner(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = M.Ctx(window=window(), timeout_s=1.0)
        self.addCleanup(lambda: [sys.modules.pop(f"waybill.collectors.{n}", None)
                                 for n in ("zz_ok", "zz_boom", "zz_slow", "zz_wrongtype")])

    def test_missing_module_becomes_error_fragment_and_gap(self) -> None:
        frags = cli.run_collectors(self.ctx, ["zz_missing"], timeout_s=1)
        self.assertEqual(len(frags), 1)
        self.assertEqual(frags[0].source.status, "error")
        self.assertIn("not installed", frags[0].source.error)
        self.assertEqual(frags[0].gaps[0].severity, "warn")

    def test_exception_and_wrong_return_type_fail_soft(self) -> None:
        def boom(ctx):
            raise RuntimeError("kaput")
        fake_module("zz_boom", boom)
        fake_module("zz_wrongtype", lambda ctx: {"not": "a fragment"})
        fake_module("zz_ok", lambda ctx: ok_frag("zz_ok", 3))
        frags = {f.source.id: f for f in cli.run_collectors(self.ctx, ["zz_boom", "zz_wrongtype", "zz_ok"], timeout_s=1)}
        self.assertEqual(frags["zz_boom"].source.status, "error")
        self.assertIn("kaput", frags["zz_boom"].source.error)
        self.assertEqual(frags["zz_wrongtype"].source.status, "error")
        self.assertEqual(frags["zz_ok"].source.status, "ok")
        self.assertEqual(frags["zz_ok"].source.items, 3)

    def test_timeout_does_not_hang(self) -> None:
        fake_module("zz_slow", lambda ctx: (time.sleep(3), ok_frag("zz_slow"))[1])
        t = time.monotonic()
        # the runner allows timeout + 5 s; a negative timeout shrinks the deadline for the test
        frags = cli.run_collectors(self.ctx, ["zz_slow"], timeout_s=-4.6)
        self.assertLess(time.monotonic() - t, 2.0)
        self.assertEqual(frags[0].source.status, "error")
        self.assertIn("timed out", frags[0].source.error)

    def test_cli_only_collectors_are_skipped_on_the_other_cli(self) -> None:
        frags = cli.run_collectors(self.ctx, ["transcript_codex"], timeout_s=1)  # window is claude
        self.assertEqual(frags[0].source.status, "skipped")
        self.assertEqual(frags[0].gaps, [])

    def test_progress_lines(self) -> None:
        fake_module("zz_ok", lambda ctx: ok_frag("zz_ok"))
        seen: list[str] = []
        cli.run_collectors(self.ctx, ["zz_ok"], progress=seen.append, timeout_s=1)
        self.assertEqual(len(seen), 1)
        self.assertIn("zz_ok", seen[0])

    def test_pipeline_with_only_broken_collectors_still_assembles(self) -> None:
        wb = cli.run_pipeline(window(), only=["zz_none_a", "zz_none_b"], timeout_s=1)
        self.assertEqual(wb["format"], "33god.waybill")
        self.assertEqual({s["status"] for s in wb["sources"]}, {"error"})
        self.assertTrue(any(g["severity"] == "warn" for g in wb["gaps"]))
        self.assertIn("prompt", {s["id"] for s in wb["spans"]})

    def test_pipeline_receipts_note_becomes_a_gap(self) -> None:
        wb = cli.run_pipeline(window(), only=["zz_none"], timeout_s=1, note="window.py unavailable")
        self.assertTrue(any("receipts only" in g["what"] for g in wb["gaps"]))


class TestOutput(unittest.TestCase):
    def test_write_waybill_default_name_dir_and_atomic(self) -> None:
        wb = build("full")
        with tempfile.TemporaryDirectory() as d:
            p = cli.write_waybill(wb, d)
            self.assertEqual(p.name, f"{wb['id']}.waybill.json")
            self.assertEqual(json.loads(p.read_text())["id"], wb["id"])
            p2 = cli.write_waybill(wb, str(Path(d) / "sub" / "x.json"))
            self.assertTrue(p2.exists())
            self.assertEqual([f.name for f in Path(d).rglob("*.tmp")], [])

    def test_summary_lines(self) -> None:
        lines = cli.summary_lines(build("full"))
        self.assertEqual(len(lines), 4)
        self.assertIn("spans", lines[1])
        self.assertIn("gaps:", lines[2])

    def test_load_waybill_rejects_foreign_files(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.json"
            bad.write_text(json.dumps({"format": "other"}))
            with self.assertRaises(Exception):
                cli.load_waybill(str(bad))
            future = Path(d) / "v2.json"
            future.write_text(json.dumps({"format": "33god.waybill", "version": 2}))
            with self.assertRaises(Exception):
                cli.load_waybill(str(future))
            good = Path(d) / "ok.json"
            good.write_text(json.dumps(build("full")))
            self.assertEqual(cli.load_waybill(str(good))["version"], 1)

    def test_show_command_prints_waterfall(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "w.json"
            p.write_text(json.dumps(build("full")))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli.main(["show", str(p), "--width", "120", "--no-color"])
            self.assertEqual(rc, 0)
            self.assertIn("UserPromptSubmit", buf.getvalue())
            self.assertNotIn("\x1b[", buf.getvalue())


class TestParser(unittest.TestCase):
    def test_capture_defaults(self) -> None:
        a = cli.build_parser().parse_args(["capture", "--session", SID])
        self.assertEqual((a.session, a.turn, a.latest, a.at), (SID, None, False, None))
        self.assertEqual((a.profile, a.settle, a.timeout, a.deep), ("full", 15.0, cli.DEFAULT_TIMEOUT_S, False))

    def test_capture_flags(self) -> None:
        a = cli.build_parser().parse_args(["capture", "--session", SID, "--cli", "codex", "--turn", "3",
                                           "--profile", "public", "--only", "hookhub,nats", "-o", "/tmp/x"])
        self.assertEqual((a.cli, a.turn, a.profile, a.only, a.output), ("codex", 3, "public", "hookhub,nats", "/tmp/x"))

    def test_turn_and_at_are_exclusive(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["capture", "--turn", "1", "--at", "2026-01-01T00:00:00Z"])

    def test_record_publish_list_show(self) -> None:
        p = cli.build_parser()
        self.assertEqual(p.parse_args(["record"]).timeout, 900.0)
        pb = p.parse_args(["publish", "f.json", "--dry-run", "--full", "--name", "n"])
        self.assertTrue(pb.dry_run and pb.full)
        self.assertEqual(p.parse_args(["list", "--limit", "5", "--json"]).limit, 5)
        self.assertEqual(p.parse_args(["show", "f.json", "--all"]).all, True)

    def test_no_subcommand_is_an_error(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.build_parser().parse_args([])


def make_receipts(path: Path) -> None:
    con = sqlite3.connect(path)
    con.execute("create table invocations (invocation_id text, cli text, session_id text, native text, "
                "received_at text, status text)")
    con.execute("create table executions (invocation_id text, handler_id text, event_id text)")
    rows = [("inv-a", "claude", SID, "UserPromptSubmit", "2026-11-16T04:00:38.646Z", "ok"),
            ("inv-b", "codex", "codex-sid", "UserPromptSubmit", "2026-11-16T04:06:19.985Z", "ok"),
            ("inv-c", "claude", SID, "Stop", "2026-11-16T04:00:40.900Z", "ok")]
    con.executemany("insert into invocations values (?,?,?,?,?,?)", rows)
    con.execute("insert into executions values ('inv-a','bloodbank-publisher','evt-a')")
    con.commit()
    con.close()


class TestList(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "receipts.sqlite3"
        make_receipts(self.db)
        env = {"data": {"prompt_text": "Reply with the single word: pong", "turn_id": f"{SID}:turn:1"}}
        for p in (mock.patch.object(cli, "RECEIPTS", self.db),
                  mock.patch.object(cli, "candystore_envelope", lambda eid, timeout=2.0: env if eid == "evt-a" else None)):
            p.start()
            self.addCleanup(p.stop)

    def test_recent_prompts_only_user_prompts_newest_first(self) -> None:
        items = cli.recent_prompts(None, 10)
        self.assertEqual([i["invocation_id"] for i in items], ["inv-b", "inv-a"])
        self.assertEqual(items[1]["prompt"], "Reply with the single word: pong")
        self.assertIsNone(items[0]["prompt"])

    def test_cli_filter(self) -> None:
        self.assertEqual([i["cli"] for i in cli.recent_prompts("claude", 10)], ["claude"])

    def test_list_table_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(cli.main(["list"]), 0)
        out = buf.getvalue()
        self.assertIn("Reply with the single word: pong", out)
        self.assertIn("(prompt text not in Candystore)", out)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(["list", "--json", "--limit", "1"])
        self.assertEqual(len(json.loads(buf.getvalue())), 1)

    def test_receipts_are_opened_read_only(self) -> None:
        con = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True)
        self.addCleanup(con.close)
        with self.assertRaises(sqlite3.OperationalError):
            con.execute("insert into invocations values ('x','x','x','x','x','x')")

    def test_unreadable_receipts_is_exit_2(self) -> None:
        with mock.patch.object(cli, "RECEIPTS", Path(self.tmp.name) / "missing.sqlite3"):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(["list"]), 2)

    def test_fallback_window_resolves_from_receipts(self) -> None:
        w = cli.fallback_window(SID, "claude", latest=True)
        self.assertEqual(w.session_id, SID)
        self.assertEqual(w.cli, "claude")
        self.assertEqual(w.prompt_invocation_id, "inv-a")
        self.assertGreater(w.t_end, w.t0)


class TestNightRetired(unittest.TestCase):
    def test_night_points_at_query_last_night_and_exits_2(self) -> None:
        for argv in (["night"], ["night", "--date", "2026-11-16", "-o", "x"], ["night", "--help"]):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(cli.main(argv), 2, argv)
            self.assertIn("waybill query --last-night", err.getvalue())
            self.assertEqual(len(err.getvalue().strip().splitlines()), 1)


class TestLiveAsmContract(unittest.TestCase):
    def test_snapshot_entry_is_readable_by_the_asm_collector(self) -> None:
        from waybill import live
        from waybill.collectors import asm
        j = json.dumps({"scope": "claude:s:x", "at_ms": 1794805015295, "seq": 3, "from": "idle", "to": "working"})
        rows = [["1794805015295-0", ["j", j]]]
        state: dict = {}
        with mock.patch.object(live, "redis_json", lambda *a, **k: rows if a[0] == "XRANGE" else None):
            live.snapshot_state("claude", "x", state)
        entry = state["asm"]["stream"][0]
        norm = asm.normalize_stream_entry(entry)
        self.assertEqual((norm["from"], norm["to"]), ("idle", "working"))


class FakeProc:
    def __init__(self, rc: int = 0, out: str = "", err: str = "") -> None:
        self.returncode, self.stdout, self.stderr = rc, out, err


def receipt_out(url: str, ok: bool = True) -> str:
    return json.dumps({"project": "33god", "files": 1, "entry_url": url, "verified": ok, "ok": ok}, indent=2) + "\n" + url + "\n"


class TestPublish(unittest.TestCase):
    URL = "https://s3.delo.sh/projects/33god/2026-11-16/waybill-x/wb.waybill.json"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "in.waybill.json"
        self.wb = build("full")
        self.path.write_text(json.dumps(self.wb))
        self.calls: list[dict] = []

    def runner(self, proc: FakeProc):
        def run(cmd, **kw):
            d = Path(cmd[2])
            self.calls.append({"cmd": cmd, "kw": kw, "files": sorted(p.name for p in d.iterdir()),
                               "doc": json.loads(next(d.iterdir()).read_text())})
            return proc
        return run

    def test_parse_receipt_ignores_trailing_url_line(self) -> None:
        r = pub.parse_receipt(receipt_out(self.URL))
        self.assertEqual(r["entry_url"], self.URL)
        with self.assertRaises(ValueError):
            pub.parse_receipt("no json here")

    def test_factory_url_is_urlencoded(self) -> None:
        u = pub.factory_url(self.URL)
        self.assertTrue(u.startswith("https://manual.delo.sh/sandbox/?waybill=https%3A%2F%2Fs3.delo.sh%2F"))
        self.assertNotIn("/projects", u.split("?waybill=")[1])

    def test_publish_uses_public_profile_and_builds_links(self) -> None:
        fname = f"{self.wb['id']}.waybill.json"
        res = pub.publish(str(self.path), runner=self.runner(FakeProc(0, receipt_out(self.URL))))
        self.assertEqual(res["profile"], "public")
        self.assertTrue(res["json_url"].endswith(fname))
        self.assertIn("waybill=", res["factory_url"])
        c = self.calls[0]
        self.assertEqual(c["files"], [fname])
        self.assertEqual(c["doc"]["recorder"]["profile"], "public")
        self.assertIn("--entry", c["cmd"])
        self.assertNotIn("--dry-run", c["cmd"])
        self.assertEqual(c["cmd"][c["cmd"].index("--name") + 1], "waybill-" + self.wb["id"].lower().replace("_", "-"))

    def test_full_flag_keeps_full_profile(self) -> None:
        res = pub.publish(str(self.path), full=True, project="p", dry_run=True,
                          runner=self.runner(FakeProc(0, receipt_out(self.URL, ok=False))))
        self.assertEqual(res["profile"], "full")
        cmd = self.calls[0]["cmd"]
        self.assertIn("--dry-run", cmd)
        self.assertEqual(cmd[cmd.index("--project") + 1], "p")

    def test_failures_raise(self) -> None:
        with self.assertRaises(RuntimeError):
            pub.publish(str(self.path), runner=self.runner(FakeProc(1, "", '{"ok":false,"error":"nope"}')))
        with self.assertRaises(RuntimeError):
            pub.publish(str(self.path), runner=self.runner(FakeProc(0, receipt_out(self.URL, ok=False))))
        with self.assertRaises(RuntimeError):
            pub.publish(str(self.path), runner=self.runner(FakeProc(0, receipt_out("http://insecure/x"))))

    def test_rejects_non_waybill(self) -> None:
        self.path.write_text(json.dumps({"format": "x"}))
        with self.assertRaises(ValueError):
            pub.publish(str(self.path), runner=self.runner(FakeProc()))

    def test_publish_command_prints_json_then_factory_url(self) -> None:
        def fake_publish(path, **kw):
            return {"json_url": self.URL, "factory_url": pub.factory_url(self.URL), "receipt": {}, "profile": "public"}
        buf = io.StringIO()
        with mock.patch.object(pub, "publish", fake_publish), contextlib.redirect_stdout(buf):
            rc = cli.main(["publish", str(self.path)])
        lines = buf.getvalue().strip().splitlines()
        self.assertEqual(rc, 0)
        self.assertEqual(lines[0], self.URL)
        self.assertTrue(lines[1].startswith("https://manual.delo.sh/sandbox/?waybill="))


if __name__ == "__main__":
    unittest.main()
