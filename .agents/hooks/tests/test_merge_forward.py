from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKER = ROOT / ".agents/skills/33god-merge-forward/scripts/rebalance.py"


class MergeForwardRecoveryTests(unittest.TestCase):
    def test_restored_worker_resolves_canonical_repo_and_true_close(self):
        spec = importlib.util.spec_from_file_location("merge_forward_worker", WORKER)
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        self.assertEqual(worker.REPO_ROOT, ROOT)
        record = worker.parse_payload('{"session_id":"test","hook_event_name":"SessionEnd"}', "codex")
        self.assertEqual(record["quiet_seconds"], 2)
        self.assertTrue(all(text in (WORKER.parents[1] / "SKILL.md").read_text() for text in worker.REQUIRED_INVARIANTS))

    def test_dry_run_reads_supplied_evidence_without_launching_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            transcript = root / "transcript.jsonl"
            transcript.write_text("\n".join(json.dumps({"type": "user", "message": {"role": "user", "content": "Investigate hooks and verify the resulting migration"}}) for _ in range(2)))
            payload = {"session_id": "merge-forward-test", "cwd": str(ROOT), "hook_event_name": "SessionEnd", "transcript_path": str(transcript)}
            environment = {**os.environ, "XDG_STATE_HOME": str(root / "state"), "GOD_MERGE_FORWARD_REBALANCE_CODEX": "/does-not-exist"}
            completed = subprocess.run([sys.executable, str(WORKER), "--client", "codex", "--stdin", "--dry-run"],
                                       input=json.dumps(payload), capture_output=True, text=True, env=environment, timeout=3)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            response = json.loads(completed.stdout)
            self.assertTrue(response["eligible"])
            self.assertEqual(response["user_turns"], 2)
            self.assertFalse(list((root / "state").rglob("last-result.json")))

    def test_project_fanout_does_not_reinstall_hub_owned_tuner(self):
        source = ROOT / ".agents/hooks/sync.py"
        spec = importlib.util.spec_from_file_location("root_hook_sync", source)
        sync = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sync)
        master = json.loads((source.parent / "hooks.master.json").read_text())
        for cli in master["agents"]:
            self.assertEqual(sync.desired_commands(master, cli), [])


if __name__ == "__main__":
    unittest.main()
