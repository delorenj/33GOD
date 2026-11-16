"""Tests for waybill.window (receipts, Claude/Codex transcripts and thread history are temp fixtures)."""
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waybill import window as W
from waybill.model import iso, ms

CSID = "11111111-aaaa-4bbb-8ccc-000000000001"
XSID = "01a1e288-d177-7eb3-a080-751c3ec47af9"
T1 = "2026-11-16T03:00:00.000Z"      # turn 1 typed entry
R1 = "2026-11-16T03:00:00.050Z"      # turn 1 UserPromptSubmit receipt (Claude writes the entry first)
S1 = "2026-11-16T03:00:20.000Z"      # turn 1 Stop receipt
T2 = "2026-11-16T03:05:00.000Z"
R2 = "2026-11-16T03:05:00.040Z"
S2 = "2026-11-16T03:05:09.000Z"


# ---------------------------------------------------------------- fixture builders (reused by the other test files)

def make_receipts(path, rows):
    con = sqlite3.connect(path)
    con.execute("create table invocations (invocation_id text primary key, cli text, native text, role text, event_type text, "
                "session_id text, identity_kind text, received_at text, updated_at text, status text, deduplicated integer)")
    for r in rows:
        inv, cli, native, sid, at = r[:5]
        con.execute("insert into invocations values (?,?,?,?,?,?,?,?,?,?,?)",
                    (inv, cli, native, "main", native.lower(), sid, "native", at, at, "completed", 0))
    con.commit()
    con.close()


def claude_user(ts, text, turn, prompt_id, source="typed", entrypoint="cli", cwd="/home/u/proj", sid=CSID):
    return {"type": "user", "isSidechain": False, "promptId": prompt_id, "uuid": f"u-{prompt_id}", "timestamp": ts,
            "promptSource": source, "turnPosition": {"promptIndex": turn, "turnIndex": turn}, "userType": "external",
            "entrypoint": entrypoint, "cwd": cwd, "sessionId": sid, "version": "2.1.325",
            "message": {"role": "user", "content": text}}


def claude_assistant(ts, ref, mid, blocks, usage, model="claude-opus-5-5", stop="end_turn", **extra):
    d = {"type": "assistant", "isSidechain": False, "timestamp": ts, "requestRef": ref, "requestedModel": "automaticai/auto/orchestrator",
         "effort": "high", "uuid": f"a-{ts}-{len(blocks)}",
         "message": {"model": model, "id": mid, "type": "message", "role": "assistant", "content": blocks, "stop_reason": stop, "usage": usage}}
    d.update(extra)
    return d


def write_jsonl(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write((e if isinstance(e, str) else json.dumps(e, ensure_ascii=False)) + "\n")


UPS_CONTEXT = ("⚡ REMINDER: Before starting, check if any skills are relevant.\n > NOTE: grain of salt\n\n\n"
               "<!-- hindsight:recall bank=proj -->\nMemory one\nMemory two\n<!-- /hindsight:recall -->")


def claude_turn_entries(sid=CSID, with_second_turn=True):
    u1 = {"input_tokens": 2, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 1000, "output_tokens": 50}
    u2 = {"input_tokens": 3, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 20, "output_tokens": 30}
    e = [
        {"type": "api-request-blob", "pad": "x" * 5000},
        claude_user(T1, "do the thing", 1, "p1", sid=sid),
        {"type": "attachment", "timestamp": "2026-11-16T03:00:00.900Z", "isSidechain": False,
         "attachment": {"type": "hook_additional_context", "content": [UPS_CONTEXT], "hookName": "UserPromptSubmit",
                        "toolUseID": "hook-1", "hookEvent": "UserPromptSubmit"}},
        {"type": "api-request", "id": "req-1", "timestamp": "2026-11-16T03:00:01.000Z", "querySource": "repl_main_thread",
         "params": {"model": "automaticai/auto/orchestrator", "output_config": {"effort": "high"}}},
        claude_assistant("2026-11-16T03:00:03.000Z", "req-1", "msg-1", [{"type": "thinking", "thinking": ""}], u1, stop="tool_use"),
        claude_assistant("2026-11-16T03:00:04.000Z", "req-1", "msg-1",
                         [{"type": "tool_use", "id": "toolu_A", "name": "Bash", "input": {"command": "ls -la", "description": "list files"}}],
                         u1, stop="tool_use"),
        {"type": "attachment", "timestamp": "2026-11-16T03:00:04.100Z", "isSidechain": False,
         "attachment": {"type": "hook_success", "hookName": "PreToolUse:Bash", "toolUseID": "toolu_A", "hookEvent": "PreToolUse",
                        "durationMs": 12, "exitCode": 0}},
        {"type": "user", "isSidechain": False, "timestamp": "2026-11-16T03:00:05.000Z", "uuid": "u-res-A",
         "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_A", "content": "file1\nfile2", "is_error": False}]}},
        {"type": "api-request", "id": "req-2", "timestamp": "2026-11-16T03:00:05.200Z", "querySource": "repl_main_thread",
         "params": {"model": "automaticai/auto/orchestrator"}},
        claude_assistant("2026-11-16T03:00:08.000Z", "req-2", "msg-2", [{"type": "text", "text": "done"}], u2),
        {"type": "system", "subtype": "stop_hook_summary", "timestamp": "2026-11-16T03:00:20.010Z", "isSidechain": False,
         "hookCount": 1, "hookInfos": [{"command": "bb-hook --native Stop", "durationMs": 70}]},
        {"type": "system", "subtype": "turn_duration", "timestamp": "2026-11-16T03:00:20.050Z", "isSidechain": False,
         "durationMs": 20000, "messageCount": 6},
    ]
    if with_second_turn:
        e += [claude_user(T2, "second prompt", 2, "p2", sid=sid),
              {"type": "api-request", "id": "req-3", "timestamp": "2026-11-16T03:05:01.000Z", "querySource": "repl_main_thread",
               "params": {"model": "automaticai/auto/orchestrator"}},
              claude_assistant("2026-11-16T03:05:05.000Z", "req-3", "msg-3", [{"type": "text", "text": "ok"}], u2)]
    return e


def standard_receipts(path, sid=CSID):
    make_receipts(path, [
        ("inv-s0", "claude", "SessionStart", sid, "2026-11-16T02:59:59.000Z"),
        ("inv-p1", "claude", "UserPromptSubmit", sid, R1),
        ("inv-e1", "claude", "Stop", sid, S1),
        ("inv-p2", "claude", "UserPromptSubmit", sid, R2),
        ("inv-e2", "claude", "Stop", sid, S2),
        ("inv-x", "codex", "UserPromptSubmit", "other-session", "2026-11-16T03:06:00.000Z"),
    ])


class Env:
    """Temp receipts / Claude projects / Codex home wired through the env overrides."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.receipts = self.root / "receipts.sqlite3"
        self.projects = self.root / "claude-projects"
        self.codex = self.root / "codex"
        self.patch = mock.patch.dict(os.environ, {
            "WAYBILL_RECEIPTS": str(self.receipts), "WAYBILL_CLAUDE_PROJECTS": str(self.projects),
            "WAYBILL_CODEX_HOME": str(self.codex), "WAYBILL_CANDYSTORE_URL": "http://127.0.0.1:9"})

    def __enter__(self):
        self.patch.start()
        return self

    def __exit__(self, *a):
        self.patch.stop()
        self.tmp.cleanup()

    def claude_file(self, entries, sid=CSID, slug="-home-u-proj"):
        p = self.projects / slug / f"{sid}.jsonl"
        write_jsonl(p, entries)
        return p


def make_codex(env, sid=XSID, originator="codex_exec", source="exec", turns=2):
    """A rollout with `turns` turns plus state_5/thread_history rows pointing at exact byte offsets."""
    lines, bounds = [], []
    base = ms("2026-11-16T04:06:19.985Z")

    def line(ts_ms, typ, payload, ordinal):
        return json.dumps({"timestamp": iso(ts_ms), "ordinal": ordinal, "type": typ, "payload": payload}, ensure_ascii=False)

    ordinal = 0
    lines.append(line(base, "session_meta", {"id": sid, "cwd": "/tmp/proj", "originator": originator, "source": source,
                                              "base_instructions": {"text": "x"}}, ordinal))
    for t in range(turns):
        tid = f"01a1e288-d246-7832-9b7c-47{t:010d}"
        t_start = base + t * 60000
        start_idx = len(lines)
        ordinal += 1
        lines.append(line(t_start, "event_msg", {"type": "task_started", "turn_id": tid, "started_at": int(t_start / 1000),
                                                "turn_attribution": {"turn_trigger": "exec"}}, ordinal))
        ordinal += 1
        lines.append(line(t_start + 400, "response_item", {"type": "message", "role": "developer",
                                                         "content": [{"type": "input_text", "text": "## Memory\nbootstrap only"}]}, ordinal))
        ordinal += 1
        lines.append(line(t_start + 410, "turn_context", {"turn_id": tid, "cwd": "/tmp/proj", "model": "automaticai/auto/orchestrator", "effort": "high"}, ordinal))
        if t == 0:
            ordinal += 1
            lines.append(line(t_start + 900, "response_item", {"type": "message", "role": "developer", "content": [{"type": "input_text", "text":
                "AutomaticAI prompt proof marker: AAI_ROUTE_PROOF_c28b59f264c5b905977dbe6c65edbdd4. Keep this.\n\n"
                "<!-- hindsight:briefing bank=proj -->\nbriefing body\n<!-- /hindsight:briefing -->"}]}, ordinal))
        ordinal += 1
        lines.append(line(t_start + 1600, "response_item", {"type": "message", "role": "user", "content": [{"type": "input_text", "text": f"prompt number {t + 1}"}]}, ordinal))
        ordinal += 1
        lines.append(line(t_start + 1601, "event_msg", {"type": "item_completed", "item": {"type": "UserMessage", "id": "um", "content": [{"type": "text", "text": f"prompt number {t + 1}"}]}}, ordinal))
        ordinal += 1
        lines.append(line(t_start + 1620, "response_item", {"type": "message", "role": "developer", "content": [{"type": "input_text", "text":
            "⚡ REMINDER: check skills.\n\nAutomaticAI prompt proof marker: AAI_ROUTE_PROOF_c28b59f264c5b905977dbe6c65edbdd4. Keep this.\n\n"
            "<!-- hindsight:recall bank=proj -->\nrecalled memory\n<!-- /hindsight:recall -->"}]}, ordinal))
        # call 1: a failing shell command and a successful patch
        ordinal += 1
        lines.append(line(t_start + 3000, "response_item", {"type": "function_call", "name": "exec_command", "call_id": f"call_{t}_1",
                                                         "arguments": json.dumps({"cmd": "false"})}, ordinal))
        ordinal += 1
        lines.append(line(t_start + 3010, "response_item", {"type": "custom_tool_call", "name": "apply_patch", "call_id": f"call_{t}_2",
                                                         "input": "*** Begin Patch\n*** Add File: /tmp/proj/a.txt\n+hi\n*** End Patch"}, ordinal))
        ordinal += 1
        lines.append(line(t_start + 3100, "token_usage_record", {"turn_id": tid, "response_id": f"resp_{t}_1",
                         "usage": {"input_tokens": 1000, "cached_input_tokens": 400, "cache_write_input_tokens": 0, "output_tokens": 20, "reasoning_output_tokens": 5}}, ordinal))
        ordinal += 1
        lines.append(line(t_start + 3200, "response_item", {"type": "function_call_output", "call_id": f"call_{t}_1",
                                                         "output": "Chunk ID: 1\nProcess exited with code 1\nOutput:\n"}, ordinal))
        ordinal += 1
        lines.append(line(t_start + 3210, "response_item", {"type": "custom_tool_call_output", "call_id": f"call_{t}_2",
                                                         "output": "Exit code: 0\nWall time: 0 seconds\nOutput:\nSuccess."}, ordinal))
        ordinal += 1
        lines.append(line(t_start + 5000, "token_usage_record", {"turn_id": tid, "response_id": f"resp_{t}_2",
                         "usage": {"input_tokens": 1200, "cached_input_tokens": 1000, "cache_write_input_tokens": 0, "output_tokens": 7, "reasoning_output_tokens": 0}}, ordinal))
        ordinal += 1
        lines.append(line(t_start + 5050, "event_msg", {"type": "task_complete", "turn_id": tid, "started_at": int(t_start / 1000),
                                                       "completed_at": int(t_start / 1000) + 5, "duration_ms": 5050, "time_to_first_token_ms": 4000}, ordinal))
        bounds.append((tid, start_idx, len(lines), t_start))
    # byte offsets
    offs, off = [], 0
    for ln in lines:
        offs.append(off)
        off += len(ln.encode()) + 1
    total = off
    day = env.codex / "sessions" / "2026" / "11" / "15"
    day.mkdir(parents=True, exist_ok=True)
    rollout = day / f"rollout-2026-11-15T23-06-19-{sid}.jsonl"
    rollout.write_text("\n".join(lines) + "\n", encoding="utf-8")

    con = sqlite3.connect(env.codex / "state_5.sqlite")
    con.execute("create table threads (id text, rollout_path text, originator text, source text, thread_source text, cwd text, model text, "
                "reasoning_effort text, cli_version text, created_at_ms integer, updated_at_ms integer, title text)")
    con.execute("insert into threads values (?,?,?,?,?,?,?,?,?,?,?,?)", (sid, str(rollout), originator, source, "user", "/tmp/proj",
                                                                         "automaticai/auto/orchestrator", "high", "0.167.0", 0, 0, "t"))
    con.commit()
    con.close()
    con = sqlite3.connect(env.codex / "thread_history_1.sqlite")
    con.execute("create table thread_turns (thread_id text, turn_id text, rollout_ordinal integer, rollout_end_ordinal integer, "
                "rollout_byte_offset integer, rollout_end_byte_offset integer, started_at integer, completed_at integer, duration_ms integer, "
                "status text, first_user_item_id text, final_agent_item_id text, root_turn_id text)")
    for i, (tid, a, b, t_start) in enumerate(bounds):
        end_off = offs[b] if b < len(offs) else total
        con.execute("insert into thread_turns values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (sid, tid, a, b - 1, offs[a], end_off, int(t_start / 1000), int(t_start / 1000) + 5, 5050, "completed", "um", "fa", tid))
    con.commit()
    con.close()
    return rollout, [b[0] for b in bounds]


# ---------------------------------------------------------------- tests

class Surfaces(unittest.TestCase):
    def test_claude_surface(self):
        self.assertEqual(W.claude_surface("cli", "typed"), "claude-code")
        self.assertEqual(W.claude_surface("sdk-cli", "sdk"), "claude-code-headless")
        self.assertEqual(W.claude_surface("cli", "sdk"), "claude-code-headless")
        self.assertEqual(W.claude_surface("claude-desktop", "typed"), "claude-desktop")
        self.assertEqual(W.claude_surface(None, None), "claude-code")

    def test_codex_surface(self):
        self.assertEqual(W.codex_surface("codex_exec"), "codex-exec")
        self.assertEqual(W.codex_surface("exec"), "codex-exec")
        self.assertEqual(W.codex_surface("codex-tui"), "codex-cli")
        self.assertEqual(W.codex_surface("cli"), "codex-cli")
        self.assertEqual(W.codex_surface("codex_work_desktop"), "codex-desktop")
        self.assertEqual(W.codex_surface("Codex Desktop"), "codex-desktop")


class ClaudeResolve(unittest.TestCase):
    def setUp(self):
        self.env = Env().__enter__()
        standard_receipts(self.env.receipts)
        self.env.claude_file(claude_turn_entries())

    def tearDown(self):
        self.env.__exit__()

    def test_turn_one(self):
        w = W.resolve(CSID, turn=1)
        self.assertEqual((w.cli, w.surface), ("claude", "claude-code"))
        self.assertEqual(w.prompt_invocation_id, "inv-p1")
        self.assertEqual(w.stop_invocation_id, "inv-e1")
        self.assertEqual(w.turn_index, 1)
        self.assertEqual(w.turn_id, f"{CSID}:turn:1")
        self.assertEqual(w.prompt_text, "do the thing")
        self.assertEqual(w.cwd, "/home/u/proj")
        self.assertEqual(iso(w.turn_end), S1)
        self.assertEqual(w.t_end, ms(S1) + 15000)

    def test_t0_is_min_of_receipt_and_transcript(self):
        w = W.resolve(CSID, turn=1)
        self.assertEqual(iso(w.t0), T1)          # the transcript entry is 50 ms before the receipt

    def test_latest_and_default(self):
        self.assertEqual(W.resolve(CSID, latest=True).prompt_invocation_id, "inv-p2")
        self.assertEqual(W.resolve(CSID).prompt_invocation_id, "inv-p2")

    def test_at_picks_prompt_at_or_before(self):
        w = W.resolve(CSID, at="2026-11-16T03:03:00Z")
        self.assertEqual(w.prompt_invocation_id, "inv-p1")
        w = W.resolve(CSID, at="2026-11-16T03:06:00Z")
        self.assertEqual(w.turn_index, 2)

    def test_turn_end_falls_back_to_next_prompt_then_now(self):
        # drop the turn-1 Stop receipt: the next UserPromptSubmit ends the turn
        make_receipts_path = self.env.receipts
        os.remove(make_receipts_path)
        make_receipts(make_receipts_path, [
            ("inv-p1", "claude", "UserPromptSubmit", CSID, R1), ("inv-p2", "claude", "UserPromptSubmit", CSID, R2)])
        w = W.resolve(CSID, turn=1)
        self.assertEqual(iso(w.turn_end), R2)
        w2 = W.resolve(CSID, turn=2)
        self.assertIsNone(w2.turn_end)
        self.assertGreater(w2.t_end, ms(R2))

    def test_missing_turn_raises(self):
        with self.assertRaises(W.WindowError):
            W.resolve(CSID, turn=9)

    def test_invalid_session_id(self):
        with self.assertRaises(W.WindowError):
            W.resolve("bad id; drop table")

    def test_no_session_uses_latest_prompt(self):
        w = W.resolve(cli="claude")
        self.assertEqual(w.session_id, CSID)
        self.assertEqual(w.turn_index, 2)


class TranscriptFallback(unittest.TestCase):
    def test_receipts_aged_out(self):
        with Env() as env:
            make_receipts(env.receipts, [])
            env.claude_file(claude_turn_entries())
            w = W.resolve(CSID, turn=1)
            self.assertEqual(w.cli, "claude")
            self.assertIsNone(w.prompt_invocation_id)
            self.assertEqual(iso(w.t0), T1)
            self.assertEqual(w.turn_index, 1)
            self.assertEqual(iso(w.turn_end), T2)            # next prompt entry ends it

    def test_headless_surface_from_entrypoint(self):
        with Env() as env:
            make_receipts(env.receipts, [])
            env.claude_file([claude_user(T1, "hi", 1, "p1", source="sdk", entrypoint="sdk-cli")])
            self.assertEqual(W.resolve(CSID, turn=1).surface, "claude-code-headless")

    def test_candystore_fallback(self):
        events = {"session_id": CSID, "events": [
            {"type": "bloodbank.conversation.turn.started", "time": "2026-11-16T03:00:00.500Z", "actor": {"cli": "claude"}},
            {"type": "bloodbank.conversation.turn.completed", "time": "2026-11-16T03:00:21.000Z"}]}

        class Resp:
            def __enter__(s): return s
            def __exit__(s, *a): return False
            def read(s, *a): return json.dumps(events).encode()

        with Env() as env:
            make_receipts(env.receipts, [])
            with mock.patch("urllib.request.urlopen", return_value=Resp()):
                w = W.resolve(CSID, turn=1)
            self.assertEqual(w.cli, "claude")
            self.assertEqual(iso(w.t0), "2026-11-16T03:00:00.500Z")
            self.assertEqual(iso(w.turn_end), "2026-11-16T03:00:21.000Z")


class CodexResolve(unittest.TestCase):
    def test_codex_turns_by_byte_offsets(self):
        with Env() as env:
            standard = [
                ("c-s", "codex", "SessionStart", XSID, "2026-11-16T04:06:20.448Z"),
                ("c-p1", "codex", "UserPromptSubmit", XSID, "2026-11-16T04:06:20.982Z"),
                ("c-e1", "codex", "Stop", XSID, "2026-11-16T04:06:24.976Z"),
                ("c-p2", "codex", "UserPromptSubmit", XSID, "2026-11-16T04:07:21.000Z"),
            ]
            make_receipts(env.receipts, standard)
            rollout, tids = make_codex(env)
            w = W.resolve(XSID, turn=1)
            self.assertEqual((w.cli, w.surface), ("codex", "codex-exec"))
            self.assertEqual(w.turn_id, tids[0])
            self.assertEqual(w.turn_index, 1)
            self.assertEqual(w.transcript_path, str(rollout))
            self.assertEqual(w.prompt_text, "prompt number 1")
            self.assertEqual(iso(w.t0), "2026-11-16T04:06:19.985Z")   # task_started precedes the receipt
            self.assertEqual(w.cwd, "/tmp/proj")
            w2 = W.resolve(XSID, turn=2)
            self.assertEqual(w2.turn_id, tids[1])
            self.assertIsNone(w2.stop_invocation_id)

    def test_codex_without_receipts_uses_thread_turns(self):
        with Env() as env:
            make_receipts(env.receipts, [])
            _, tids = make_codex(env, originator="codex_work_desktop", source="vscode")
            w = W.resolve(XSID, turn=2)
            self.assertEqual(w.cli, "codex")
            self.assertEqual(w.surface, "codex-desktop")
            self.assertEqual(w.turn_id, tids[1])
            t_start = ms("2026-11-16T04:06:19.985Z") + 60000
            self.assertEqual(w.turn_end, (int(t_start / 1000) + 5) * 1000.0)


class LatestPromptAfter(unittest.TestCase):
    def test_latest_prompt_after(self):
        with Env() as env:
            standard_receipts(env.receipts)
            got = W.latest_prompt_after(ms("2026-11-16T03:01:00Z"), cli="claude")
            self.assertEqual(got[0], CSID)
            self.assertEqual(got[1], "inv-p2")
            self.assertAlmostEqual(got[2], ms(R2), places=0)
            self.assertIsNone(W.latest_prompt_after(ms("2026-11-16T03:10:00Z"), cli="claude"))
            self.assertEqual(W.latest_prompt_after(ms("2026-11-16T03:01:00Z"), cli="codex")[0], "other-session")
            self.assertEqual(W.latest_prompt_after(ms("2026-11-16T03:01:00Z"))[1], "inv-x")

    def test_missing_receipts_file_returns_none(self):
        with Env():
            self.assertIsNone(W.latest_prompt_after(0))


class ReadOnly(unittest.TestCase):
    def test_ro_connect_refuses_writes(self):
        with Env() as env:
            standard_receipts(env.receipts)
            with W.ro_connect(str(env.receipts)) as con:
                with self.assertRaises(sqlite3.OperationalError):
                    con.execute("delete from invocations")

    def test_ro_connect_closes_on_exit(self):
        with Env() as env:
            standard_receipts(env.receipts)
            with W.ro_connect(str(env.receipts)) as con:
                con.execute("select 1").fetchone()
            with self.assertRaises(sqlite3.ProgrammingError):
                con.execute("select 1")


if __name__ == "__main__":
    unittest.main()
