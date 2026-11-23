#!/usr/bin/env python3
"""Isolated unit/integration probes; no production board, PM or scheduler writes."""
import copy
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fleet_recovery", HERE / "check.py")
assert spec is not None and spec.loader is not None
fleet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fleet)


def status():
    return {"version": 1, "generatedAt": "2030-01-01", "candystore": {"ok": True},
            "tick": {"watch": {"alive": True}, "overdue": False}, "scopes": [
                {"board": "BB", "agentId": "bloodbank-pm", "free": 1, "counts": {"wait-slot": 1},
                 "occupied": [], "tickets": [{"key": "BB-62", "state": "Todo", "stage": "wait-slot",
                  "labels": ["lifecycle:triaged"], "eta": "later", "updatedAt": "today"}],
                 "inFlight": [], "recent": [], "errors": [], "warnings": []}]}


def snapshot():
    return {"status": fleet.compact_status(status()), "tracked": [], "faults": []}


class FleetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ["TMPDIR"])
        self.runtime = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_gate_stable_dynamic_times_and_sorted_labels(self):
        a = status()
        b = copy.deepcopy(a)
        b["generatedAt"] = "2031-01-01"
        b["tick"]["last"] = {"at": "now"}
        b["scopes"][0]["tickets"][0].update(eta="soon", updatedAt="tomorrow", stageLabel="running 99m")
        self.assertEqual(fleet.compact_status(a), fleet.compact_status(b))
        s = {"last_hash": fleet.digest(snapshot()), "last_officer_at": 1000}
        self.assertEqual(fleet.gate(snapshot(), s, 1299), (False, "quiet: unchanged evidence"))
        self.assertTrue(fleet.gate(snapshot(), s, 2800)[0])

    def test_real_change_and_failed_backoff(self):
        s = {"last_hash": "different", "last_officer_at": 1000}
        self.assertTrue(fleet.gate(snapshot(), s, 1100)[0])
        for field in ("pending_at", "failed_at"):
            self.assertFalse(fleet.gate(snapshot(), s | {field: 1000}, 1100)[0])
            self.assertTrue(fleet.gate(snapshot(), s | {field: 1000}, 2801)[0])

    def test_compact_comments_hash_unclipped_history(self):
        t = {"ref": "BB-62", "label_names": [], "comments": [
            {"id": str(i), "created_at": str(i), "text": "x" * 2000} for i in range(5)]}
        before = fleet.compact_ticket(t)
        t["comments"][0]["text"] += "real old evidence change"
        after = fleet.compact_ticket(t)
        self.assertNotEqual(before["evidence_hash"], after["evidence_hash"])
        self.assertEqual(before["comments"], after["comments"])
        self.assertEqual(len(after["comments"]), 3)

    def test_unavailable_never_healthy_empty(self):
        for raw in ({}, status() | {"candystore": {"ok": False}}, status() | {"scopes": []}):
            with self.assertRaises(ValueError):
                fleet.compact_status(raw)
        with patch.object(fleet, "command_json", side_effect=ValueError("invalid")):
            data = fleet.collect()
        self.assertEqual(len(data["faults"]), 9)
        self.assertIsNone(data["status"])

    def stream(self, marker="real", result=True, code=0):
        events = [{"type": "tool_use", "name": "terminal"},
                  {"type": "tool_result", "name": "terminal", "is_error": False, "output": marker}]
        if result:
            events.append({"type": "result", "exit_code": code, "session_id": "test-only",
                           "text": json.dumps({"verdict": "continue", "note": "unit test", "roadmap": "open"}),
                           "tokens": {"total": 123}})
        return "\n".join(json.dumps(e) for e in events)

    def test_stream_requires_actual_terminal_result_and_session(self):
        self.assertTrue(fleet.parse_turn(self.stream(), 0, "real")["ok"])
        self.assertFalse(fleet.parse_turn(self.stream(marker="not verified"), 0, "real")["ok"])
        self.assertFalse(fleet.parse_turn(self.stream(result=False), 0, "real")["ok"])
        self.assertFalse(fleet.parse_turn(self.stream(), 124, "real")["ok"])
        self.assertFalse(fleet.parse_turn(self.stream() + "\n" + self.stream(), 0, "real")["ok"])
        self.assertFalse(fleet.parse_turn(self.stream().replace('"total": 123', '"total": null'), 0, "real")["ok"])

    def test_synchronous_child_real_subprocess_boundary(self):
        # A recording engine boundary, not an LLM or claimed production success.
        script = self.runtime / "engine.py"
        script.write_text("import sys\nassert sys.stdin.read() == 'test brief'\nprint(" + repr(self.stream()) + ")\n")
        with patch.object(fleet, "officer_command", return_value=[sys.executable, str(script)]):
            turn = fleet.run_officer("test brief", self.runtime, "real")
        self.assertTrue(turn["ok"])
        self.assertEqual(turn["tokens"], 123)
        self.assertTrue((self.runtime / "turn.jsonl").exists())

    def test_timeout_kills_process_group_and_returns_failure(self):
        with patch.object(fleet, "officer_command", return_value=[sys.executable, "-c", "import time;time.sleep(10)"]), \
                patch.object(fleet, "OFFICER_TIMEOUT", 0.05):
            turn = fleet.run_officer("x", self.runtime, "real")
        self.assertFalse(turn["ok"])
        self.assertEqual(turn["exit"], 124)
        self.assertIsNone(turn["tokens"])

    def test_corrupt_state_fails_closed(self):
        p = self.runtime / "state.json"
        p.write_text("{bad")
        with self.assertRaises(ValueError):
            fleet.read_json(p)

    def test_quiet_zero_tokens_no_officer(self):
        snap = snapshot()
        fleet.atomic(self.runtime / "state.json", {"last_hash": fleet.digest(snap), "last_officer_at": 1000})
        with patch.object(fleet, "collect", return_value=snap), patch.object(fleet.time, "time", return_value=1200), \
                patch.object(fleet, "run_officer") as officer, patch.dict(os.environ, {"CANDYBAR_RESULT_FILE": str(self.runtime / "result.json")}):
            self.assertEqual(fleet.execute(self.runtime), 0)
        officer.assert_not_called()
        self.assertEqual(json.loads((self.runtime / "result.json").read_text())["metrics"]["token_spend"], 0)

    def test_fault_quiet_stays_failed_not_fake_green(self):
        snap = snapshot() | {"faults": ["krebs:UNAVAILABLE:ValueError"]}
        fleet.atomic(self.runtime / "state.json", {"last_hash": fleet.digest(snap), "last_officer_at": 1000})
        with patch.object(fleet, "collect", return_value=snap), patch.object(fleet.time, "time", return_value=1200), \
                patch.object(fleet, "run_officer") as officer:
            self.assertEqual(fleet.execute(self.runtime), 1)
        officer.assert_not_called()

    def test_overlap_nonblocking_no_read_no_officer(self):
        with (self.runtime / "run.lock").open("a+") as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            with patch.object(fleet, "collect") as collect:
                self.assertEqual(fleet.execute(self.runtime), 0)
            collect.assert_not_called()

    def proof(self):
        fleet.atomic(self.runtime / "original.json", {"TEST_ONLY": "not a production receipt"})
        fixes = {k: {"installed": True, "independent_review": True, "reviewer": "review-test", "implementer": "worker-test",
                      "installed_probe_receipt": "original.json", "review_receipt": "original.json"} for k in fleet.FIXES}
        samples = [{"id": str(i), "at": 1000 + i * 300, "trigger": "scheduled", "invocation_id": str(i),
                    "data_ok": True, "warnings": [], "ready_scopes": ["BB"], "held_scopes": ["EARS"]} for i in range(3)]
        proof = {"fixes": fixes, "sample_ids": ["0", "1", "2"], "flow": {"BB": "original.json"},
                 "held_scopes": {"EARS": {"classification": "real test hold", "receipt": "original.json"}},
                 "no_unexplained_stale_ready": True, "no_fail_loops": True}
        fleet.atomic(self.runtime / "proof.json", proof)
        return {"verdict": "complete", "proof_file": "proof.json"}, samples, proof

    def test_completion_proof_happy_path_only_test_receipts(self):
        verdict, samples, _ = self.proof()
        proof = fleet.completion_proof(verdict, samples, self.runtime, 1610)
        self.assertTrue(proof["receipts"])
        self.assertEqual(proof["samples"], samples)

    def test_completion_rejects_early_manual_fault_stale_or_duplicate(self):
        verdict, samples, _ = self.proof()
        variants = [samples[:2], copy.deepcopy(samples), copy.deepcopy(samples), copy.deepcopy(samples), copy.deepcopy(samples)]
        variants[1][-1]["trigger"] = "manual"
        variants[2][-1]["data_ok"] = False
        variants[3][-1]["invocation_id"] = "0"
        variants[4][-1]["warnings"] = ["liveness"]
        for chosen in variants:
            with self.assertRaises(ValueError):
                fleet.completion_proof(verdict, chosen, self.runtime, 1610)
        with self.assertRaises(ValueError):
            fleet.completion_proof(verdict, samples, self.runtime, 9000)

    def test_completion_rejects_uninstalled_self_review_missing_flow_or_holds(self):
        verdict, samples, good = self.proof()
        for field in ("installed", "independent_review", "reviewer"):
            p = copy.deepcopy(good)
            p["fixes"]["BB-62"][field] = False
            fleet.atomic(self.runtime / "proof.json", p)
            with self.assertRaises(ValueError):
                fleet.completion_proof(verdict, samples, self.runtime, 1610)
        for field in ("flow", "held_scopes"):
            fleet.atomic(self.runtime / "proof.json", good | {field: {}})
            with self.assertRaises(ValueError):
                fleet.completion_proof(verdict, samples, self.runtime, 1610)
        with self.assertRaises(ValueError):
            fleet.evidence_file("../outside.json", self.runtime)

    def test_self_pause_only_named_owned_registration_readback(self):
        row = {"id": "unit-test-id", "name": fleet.NAME, "tags": ["project:33GOD"], "enabled": True}
        with patch.object(fleet, "api", side_effect=[[row], row | {"enabled": False}, row | {"enabled": False}]) as api, \
                patch.dict(os.environ, {"CANDYBAR_ID": "unit-test-id"}):
            self.assertIs(fleet.pause_self()["enabled"], False)
            self.assertEqual(api.call_args_list[1].args, ("POST", "/candybars/unit-test-id/enabled", {"enabled": False}))
        with patch.object(fleet, "api", return_value=[row]), patch.dict(os.environ, {"CANDYBAR_ID": "foreign"}):
            with self.assertRaises(ValueError):
                fleet.pause_self()

    def test_no_clock_or_publisher_in_officer_argv(self):
        argv = fleet.officer_command()
        self.assertIn("--query-file", argv)
        self.assertIn("--max-turns", argv)
        self.assertIn("terminal,file,no_mcp", argv)
        self.assertNotIn("cron", argv)
        self.assertNotIn("--yolo", argv)


if __name__ == "__main__":
    unittest.main(verbosity=2)
