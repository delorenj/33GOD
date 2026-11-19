"""scripts/cli-launchers.py: pinned-runtime ~/.local/bin wrappers for 33GOD CLIs (Story 7.1)."""

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "cli-launchers.py"
spec = importlib.util.spec_from_file_location("cli_launchers", MODULE)
launchers = importlib.util.module_from_spec(spec)
sys.modules["cli_launchers"] = launchers  # dataclasses look the module up while the class is built
spec.loader.exec_module(launchers)

FAKE_NODE = """#!/bin/sh
if [ "$1" = --version ]; then echo v24.9.9; exit 0; fi
exec /bin/sh "$@"
"""


def write(path: Path, text: str, mode: int | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if mode:
        path.chmod(mode)
    return path


class CliLaunchersTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.god = root / "god"
        self.bin = root / "bin"
        self.node = write(root / "node24" / "bin" / "node", FAKE_NODE, 0o755)
        write(self.god / "tool" / "package.json", json.dumps({"name": "@x/tool", "version": "1.2.3", "bin": {"tool": "bin/cli.js", "tl": "bin/cli.js"}}))
        write(self.god / "tool" / "bin" / "cli.js", "echo 1.2.3\n")
        self.config = write(root / "cli-launchers.toml", """
schema = 1
node = "24"
[[node_cli]]
package = "repo:tool"
bins = ["tool", "tl"]
probe = { bin = "tool", args = ["--version"], expect = "version" }
""")

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args: str) -> tuple[int, dict]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = launchers.main([*args, "--config", str(self.config), "--bin-dir", str(self.bin), "--node", str(self.node),
                                   "--god-root", str(self.god), "--json"])
        return code, json.loads(out.getvalue())

    def test_install_writes_pinned_wrappers_that_survive_a_decoy_node_and_check_passes(self):
        code, result = self.run_cli("install")
        self.assertEqual(code, 0, result["findings"])
        wrapper = (self.bin / "tool").read_text()
        self.assertIn(f"exec {self.node} {self.god / 'tool' / 'bin' / 'cli.js'} \"$@\"", wrapper)
        self.assertTrue(os.access(self.bin / "tl", os.X_OK))
        probe = result["data"]["probes"][0]
        self.assertEqual([r["env"] for r in probe["results"]], ["minimal-path", "decoy-node+node20-pin"])
        self.assertTrue(probe["ok"])
        code, result = self.run_cli("check")
        self.assertEqual(code, 0, result["findings"])
        self.assertEqual({l["status"] for l in result["data"]["launchers"]}, {"ok"})

    def test_install_is_idempotent(self):
        self.run_cli("install")
        before = (self.bin / "tool").stat().st_mtime_ns
        code, result = self.run_cli("install", "--no-probe")
        self.assertEqual(code, 0)
        self.assertEqual({l["status"] for l in result["data"]["launchers"]}, {"ok"})
        self.assertEqual((self.bin / "tool").stat().st_mtime_ns, before)

    def test_check_reports_drift_with_exit_6_and_install_replaces_a_symlink_not_its_target(self):
        self.run_cli("install")
        target = self.god / "tool" / "bin" / "cli.js"
        (self.bin / "tool").unlink()
        (self.bin / "tool").symlink_to(target)
        write(self.bin / "tl", "#!/bin/sh\necho hand edited\n", 0o755)
        code, result = self.run_cli("check", "--no-probe")
        self.assertEqual(code, 6)
        self.assertEqual(sorted(f["message"].split(":")[0] for f in result["findings"] if f["code"] == "E_DRIFT"), ["tl", "tool"])
        code, result = self.run_cli("install", "--no-probe")
        self.assertEqual(code, 0)
        self.assertFalse((self.bin / "tool").is_symlink())
        self.assertEqual(target.read_text(), "echo 1.2.3\n")

    def test_dry_run_writes_nothing(self):
        code, result = self.run_cli("install", "--dry-run")
        self.assertEqual(code, 0)
        self.assertFalse((self.bin / "tool").exists())
        self.assertTrue(all(l["status"].startswith("would-write") for l in result["data"]["launchers"]))

    def test_a_wrong_version_fails_the_probe(self):
        write(self.god / "tool" / "bin" / "cli.js", "echo 9.9.9\n")
        code, result = self.run_cli("install")
        self.assertEqual(code, 4)  # wrappers written, but the CLI does not report the declared version
        self.assertIn("E_PROBE_FAILED", {f["code"] for f in result["findings"]})

    def test_an_unresolvable_package_is_a_failure_not_a_silent_skip(self):
        write(self.config, self.config.read_text().replace("repo:tool", "repo:nope"))
        code, result = self.run_cli("install", "--no-probe")
        self.assertEqual(code, 1)
        self.assertEqual({l["status"] for l in result["data"]["launchers"]}, {"unresolved"})
        self.assertFalse((self.bin / "tool").exists())

    def test_bad_config_exits_2(self):
        write(self.config, 'schema = 1\n[[node_cli]]\npackage = "repo:tool"\nbins = ["tool"]\nprobe = { bin = "other" }\n')
        code, result = self.run_cli("check")
        self.assertEqual(code, 2)
        self.assertEqual(result["findings"][0]["code"], "E_CONFIG")

    def test_the_shipped_config_declares_every_story_7_1_cli(self):
        config = launchers.load_config(launchers.DEFAULT_CONFIG)
        node = {b for item in config["node_cli"] for b in item["bins"]}
        self.assertTrue({"pj", "pjangler", "px", "pilot", "flume", "fl", "krebs", "skillex"} <= node)
        self.assertEqual({p["name"] for p in config["python_cli"]}, {"candybar", "candystore", "bb", "wax", "waybill"})


if __name__ == "__main__":
    unittest.main()
