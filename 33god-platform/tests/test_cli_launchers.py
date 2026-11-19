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
if [ "$1" = --check ]; then exit 0; fi
exec /bin/sh "$@"
"""

# `mise exec -- cmd args`: runs cmd with PATH as given. `node --version` reports the scratch dir's node 20 pin.
FAKE_MISE = """#!/bin/sh
[ "$1" = exec ] || exit 64
shift; [ "$1" = -- ] && shift
if [ "$1" = node ] && [ "$2" = --version ]; then echo v20.1.0; exit 0; fi
exec "$@"
"""

# `npm install --global --prefix P ... <name>@<ver>`: lays down a package and, like the real npm, deletes the
# launchers of the package it replaces (BIN_DIR) while it does.
FAKE_NPM = """#!/bin/sh
prefix=; spec=
while [ $# -gt 0 ]; do
  case "$1" in --prefix) prefix=$2; shift;; --*) ;; *) spec=$1;; esac
  shift
done
echo "$spec" >> "$NPM_LOG"
[ -n "$NPM_FAIL" ] && { echo "npm error boom" >&2; exit 1; }
rm -f "$BIN_DIR/gtool" "$BIN_DIR/gt"
dir="$prefix/lib/node_modules/@x/gtool"
mkdir -p "$dir/bin"
printf '{"name":"@x/gtool","version":"2.0.0","bin":{"gtool":"bin/cli.js","gt":"bin/cli.js"}}' > "$dir/package.json"
echo "echo 2.0.0" > "$dir/bin/cli.js"
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

    def run_cli(self, *args: str, mise_probe: bool = False) -> tuple[int, dict]:
        out = io.StringIO()
        extra = [] if mise_probe else ["--no-mise-probe"]
        with contextlib.redirect_stdout(out):
            code = launchers.main([*args, "--config", str(self.config), "--bin-dir", str(self.bin), "--node", str(self.node),
                                   "--god-root", str(self.god), "--json", *extra])
        return code, json.loads(out.getvalue())

    def test_install_writes_pinned_wrappers_that_survive_a_decoy_node_and_check_passes(self):
        code, result = self.run_cli("install")
        self.assertEqual(code, 0, result["findings"])
        wrapper = (self.bin / "tool").read_text()
        self.assertIn(f"exec {self.node} {self.god / 'tool' / 'bin' / 'cli.js'} \"$@\"", wrapper)
        self.assertTrue(os.access(self.bin / "tl", os.X_OK))
        probe = result["data"]["probes"][0]
        self.assertEqual([r["env"] for r in probe["results"]], ["minimal-path", "decoy-node+node20-pin"])
        self.assertEqual([x["name"] for x in result["data"]["syntax"]], ["tool", "tl"])  # every bin's entry is `node --check`ed
        self.assertTrue(all(x["ok"] for x in result["data"]["syntax"]))
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

    # ---- G1/G3: no version directory in any generated path -------------------------------------------------

    def test_generated_paths_carry_no_mise_version_directory(self):
        self.run_cli("install", "--no-probe")
        for name in ("tool", "tl"):
            self.assertFalse(launchers.versioned_path((self.bin / name).read_text()), name)
        self.assertTrue(launchers.versioned_path("/h/.local/share/mise/installs/npm-delorenj-skillex/0.4.10/node_modules/x.js"))
        self.assertFalse(launchers.versioned_path("/h/.local/share/mise/installs/node/24/bin/node"))  # the major alias is fine
        self.assertFalse(launchers.versioned_path("/h/.local/lib/node_modules/@delorenj/skillex/dist/cli.js"))

    def test_an_entry_under_a_version_directory_is_refused_not_baked_in(self):
        versioned = self.god / ".local" / "share" / "mise" / "installs" / "npm-x" / "1.2.3" / "pkg"
        write(versioned / "package.json", json.dumps({"name": "@x/v", "version": "1.2.3", "bin": {"vv": "cli.js"}}))
        write(versioned / "cli.js", "echo 1.2.3\n")
        write(self.config, self.config.read_text() + '\n[[node_cli]]\npackage = "repo:.local/share/mise/installs/npm-x/1.2.3/pkg"\nbins = ["vv"]\n')
        code, result = self.run_cli("install", "--no-probe")
        self.assertNotEqual(code, 0)
        self.assertFalse((self.bin / "vv").exists())
        self.assertIn("E_VERSIONED_PATH", " ".join(f["message"] for f in result["findings"]))

    def test_the_symlinked_entry_is_not_realpathed(self):
        real = self.god / "elsewhere-1.2.3"
        real.mkdir()
        (self.god / "tool" / "bin" / "cli.js").rename(real / "cli.js")
        (self.god / "tool" / "bin" / "cli.js").symlink_to(real / "cli.js")
        self.run_cli("install", "--no-probe")
        self.assertIn(str(self.god / "tool" / "bin" / "cli.js"), (self.bin / "tool").read_text())
        self.assertNotIn("elsewhere-1.2.3", (self.bin / "tool").read_text())

    def test_mise_npm_is_retired(self):
        write(self.config, self.config.read_text().replace("repo:tool", "mise-npm:@x/tool"))
        code, result = self.run_cli("check")
        self.assertEqual(code, 2)
        self.assertIn("mise-npm is retired", result["findings"][0]["message"])

    # ---- G5: --check alias -----------------------------------------------------------------------------------

    def test_dash_dash_check_is_the_check_command(self):
        self.run_cli("install", "--no-probe")
        code, result = self.run_cli("--check", "--no-probe")
        self.assertEqual((code, result["command"]), (0, "cli-launchers check"))
        (self.bin / "tl").unlink()
        code, result = self.run_cli("--check", "--no-probe")
        self.assertEqual(code, 6)
        self.assertEqual(self.run_cli("check", "--check", "--no-probe")[0], 6)

    def test_dash_dash_check_cannot_be_combined_with_install_and_a_bare_call_is_usage(self):
        code, result = self.run_cli("install", "--check")
        self.assertEqual((code, result["findings"][0]["code"]), (2, "E_USAGE"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(launchers.main(["--config", str(self.config), "--json"]), 2)

    # ---- G5: script-type entries -----------------------------------------------------------------------------

    def with_script(self):
        script = write(self.god / "tools" / "pm-tool", '#!/bin/sh\nif [ "$1" = --where ]; then echo "$PM_FROM/agents/pm"; exit 0; fi\nexit 3\n', 0o755)
        write(self.config, self.config.read_text() + """
[[script_cli]]
name = "pm-tool"
source = "repo:tools/pm-tool"
probe = { args = ["--where"], expect = "suffix:agents/pm", env = { PM_FROM = "{god_root}" } }
""")
        return script

    def test_a_script_entry_is_symlinked_probed_and_checked_for_drift(self):
        script = self.with_script()
        code, result = self.run_cli("install")
        self.assertEqual(code, 0, result["findings"])
        self.assertEqual(os.readlink(self.bin / "pm-tool"), str(script))
        probe = next(p for p in result["data"]["probes"] if p["bin"] == "pm-tool")
        self.assertTrue(probe["ok"], probe)
        self.assertEqual(self.run_cli("check")[0], 0)
        (self.bin / "pm-tool").unlink()
        write(self.bin / "pm-tool", "#!/bin/sh\nexit 0\n", 0o755)  # a hand-made copy instead of the symlink
        code, result = self.run_cli("check", "--no-probe")
        self.assertEqual(code, 6)
        self.assertIn("pm-tool", [f["message"].split(":")[0] for f in result["findings"] if f["code"] == "E_DRIFT"])
        self.assertEqual(self.run_cli("install", "--no-probe")[0], 0)
        self.assertEqual(os.readlink(self.bin / "pm-tool"), str(script))

    def test_a_missing_script_source_is_unresolved(self):
        self.with_script().unlink()
        code, result = self.run_cli("install", "--no-probe")
        self.assertEqual(code, 4)  # the node launchers were written; the script was not
        self.assertFalse((self.bin / "pm-tool").exists())
        self.assertIn("pm-tool", " ".join(f["message"] for f in result["findings"]))

    # ---- G2: the mise exec probe is honest -------------------------------------------------------------------

    def mise_config(self):
        mise = write(Path(self.temp.name) / "fake-bin" / "mise", FAKE_MISE, 0o755)
        shims = Path(self.temp.name) / "shims"
        shims.mkdir()
        write(self.config, self.config.read_text().replace('node = "24"', f'node = "24"\nmise_shims = "{shims}"'))
        return mise, shims

    def run_mise(self, mise: Path, *args: str) -> tuple[int, dict]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = launchers.main([*args, "--config", str(self.config), "--bin-dir", str(self.bin), "--node", str(self.node),
                                   "--god-root", str(self.god), "--mise", str(mise), "--json"])
        return code, json.loads(out.getvalue())

    def test_mise_exec_probe_passes_when_nothing_shadows_the_launcher(self):
        mise, _ = self.mise_config()
        code, result = self.run_mise(mise, "install")
        self.assertEqual(code, 0, result["findings"])
        probe = result["data"]["probes"][0]
        self.assertEqual([r["env"] for r in probe["results"]], ["minimal-path", "decoy-node+node20-pin", "mise-exec+node20-pin"])
        self.assertTrue(probe["ok"])

    def test_mise_exec_probe_fails_when_a_shim_shadows_the_launcher(self):
        mise, shims = self.mise_config()
        write(shims / "tool", "#!/bin/sh\necho 'E_NODE_VERSION: shim ran node 20' >&2\nexit 2\n", 0o755)
        code, result = self.run_mise(mise, "install")
        self.assertEqual(code, 4)  # launchers written, but the CLI is shadowed in a mise context
        probe = result["data"]["probes"][0]
        self.assertEqual([r["ok"] for r in probe["results"]], [True, True, False])
        self.assertIn("mise-exec+node20-pin", " ".join(f["message"] for f in result["findings"] if f["code"] == "E_PROBE_FAILED"))
        # the same shim is invisible to the old two probes: that was the gap
        self.assertTrue(all(r["ok"] for r in probe["results"][:2]))

    def test_mise_exec_probe_is_skipped_loudly_when_mise_cannot_exec(self):
        broken = write(Path(self.temp.name) / "fake-bin" / "mise", "#!/bin/sh\necho 'op: not signed in' >&2\nexit 1\n", 0o755)
        code, result = self.run_mise(broken, "install")
        self.assertEqual(code, 0)
        self.assertEqual([r["env"] for r in result["data"]["probes"][0]["results"]], ["minimal-path", "decoy-node+node20-pin"])
        skipped = [f for f in result["findings"] if f["code"] == "W_MISE_PROBE_SKIPPED"]
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["severity"], "warning")
        self.assertIn("not signed in", skipped[0]["message"])

    # ---- G4: upgrade -----------------------------------------------------------------------------------------

    def upgrade_setup(self):
        root = Path(self.temp.name)
        self.prefix = root / "prefix"
        self.npm = write(root / "fake-bin" / "npm", FAKE_NPM, 0o755)
        self.npm_log = root / "npm.log"
        os.environ.update(NPM_LOG=str(self.npm_log), BIN_DIR=str(self.bin))
        os.environ.pop("NPM_FAIL", None)
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in ("NPM_LOG", "BIN_DIR", "NPM_FAIL")])
        write(self.prefix / "lib" / "node_modules" / "@x" / "gtool" / "package.json",
              json.dumps({"name": "@x/gtool", "version": "1.0.0", "bin": {"gtool": "bin/cli.js", "gt": "bin/cli.js"}}))
        write(self.prefix / "lib" / "node_modules" / "@x" / "gtool" / "bin" / "cli.js", "echo 1.0.0\n")
        write(self.config, self.config.read_text().replace('node = "24"', f'node = "24"\nnpm_prefix = "{self.prefix}"\nnpm_global_roots = ["{self.prefix}/lib/node_modules"]') + """
[[node_cli]]
package = "npm-global:@x/gtool"
bins = ["gtool", "gt"]
probe = { bin = "gtool", args = ["--version"], expect = "version" }
""")

    def run_upgrade(self, *args: str) -> tuple[int, dict]:
        return self.run_cli("upgrade", *args, "--npm", str(self.npm))

    def test_upgrade_dry_run_plans_the_npm_install_and_touches_nothing(self):
        self.upgrade_setup()
        self.run_cli("install", "--no-probe")
        before = (self.bin / "gtool").read_text()
        code, result = self.run_upgrade("gtool", "--dry-run")
        self.assertEqual(code, 0, result["findings"])
        [plan] = result["data"]["upgrade"]
        self.assertEqual(plan["package"], "npm-global:@x/gtool")
        self.assertEqual(plan["bins"], ["gtool", "gt"])
        self.assertEqual(plan["status"], "planned")
        self.assertEqual(plan["command"], [str(self.npm), "install", "--global", "--prefix", str(self.prefix), "--force", "--no-bin-links",
                                           "--no-fund", "--no-audit", "@x/gtool@latest"])
        self.assertFalse(self.npm_log.exists())
        self.assertEqual((self.bin / "gtool").read_text(), before)

    def test_upgrade_installs_then_rewrites_the_launchers_npm_deleted(self):
        self.upgrade_setup()
        self.run_cli("install", "--no-probe")
        self.assertIn("lib/node_modules/@x/gtool/bin/cli.js", (self.bin / "gtool").read_text())
        code, result = self.run_upgrade("gt@2.0.0")  # selected by bin name, with a version
        self.assertEqual(code, 0, result["findings"])
        self.assertEqual(self.npm_log.read_text().strip(), "@x/gtool@2.0.0")
        self.assertEqual({l["name"]: l["status"] for l in result["data"]["launchers"]}, {"gtool": "written", "gt": "written"})
        self.assertTrue(os.access(self.bin / "gtool", os.X_OK))  # npm removed them; upgrade put them back
        self.assertEqual([l["version"] for l in result["data"]["launchers"]], ["2.0.0", "2.0.0"])
        self.assertTrue(all(p["ok"] for p in result["data"]["probes"]))
        self.assertTrue((self.bin / "tool").exists())  # launchers of other packages are out of scope and untouched

    def test_a_failed_npm_still_repairs_the_launchers_and_says_so(self):
        self.upgrade_setup()
        self.run_cli("install", "--no-probe")
        (self.bin / "gtool").unlink()
        os.environ["NPM_FAIL"] = "1"
        code, result = self.run_upgrade("@x/gtool")
        self.assertEqual(code, 1)
        self.assertIn("E_NPM_FAILED", {f["code"] for f in result["findings"]})
        self.assertEqual(result["data"]["upgrade"][0]["status"], "failed")
        self.assertTrue(os.access(self.bin / "gtool", os.X_OK))  # PATH is not left broken

    def test_upgrade_refuses_undeclared_repo_and_empty_selections(self):
        self.upgrade_setup()
        for args in (("nope",), ("tool",), ()):  # `tool` is a repo: package, updated with git
            code, result = self.run_upgrade(*args)
            self.assertEqual((code, result["findings"][0]["code"]), (2, "E_USAGE"), args)
        code, result = self.run_upgrade("--all", "--dry-run")
        self.assertEqual([u["package"] for u in result["data"]["upgrade"]], ["npm-global:@x/gtool"])
        self.assertEqual(self.run_cli("install", "gtool")[0], 2)  # packages only mean something to upgrade

    def test_split_package_arg(self):
        split = launchers.split_package_arg
        self.assertEqual(split("pj"), ("pj", None))
        self.assertEqual(split("skillex@0.4.10"), ("skillex", "0.4.10"))
        self.assertEqual(split("@delorenj/pjangler"), ("@delorenj/pjangler", None))
        self.assertEqual(split("@delorenj/pjangler@1.5.57"), ("@delorenj/pjangler", "1.5.57"))

    def test_the_shipped_config_declares_every_story_7_1_cli(self):
        config = launchers.load_config(launchers.DEFAULT_CONFIG)
        node = {b for item in config["node_cli"] for b in item["bins"]}
        self.assertTrue({"pj", "pjangler", "px", "pilot", "flume", "fl", "krebs", "skillex"} <= node)
        self.assertEqual({p["name"] for p in config["python_cli"]}, {"candybar", "candystore", "bb", "wax", "waybill"})
        self.assertEqual([s["name"] for s in config["script_cli"]], ["hermes-pm"])
        packages = [item["package"] for item in config["node_cli"]]
        self.assertIn("npm-global:@delorenj/skillex", packages)  # one install path for npm CLIs: the npm prefix, no mise npm tool
        self.assertFalse([p for p in packages if p.startswith("mise-npm:")])
        probed = {p["bin"] for item in config["node_cli"] for p in launchers.node_probes(item)}
        self.assertTrue({"pj", "pjangler", "px", "pilot", "px-supervised", "flume", "fl", "krebs", "skillex"} <= probed)


if __name__ == "__main__":
    unittest.main()
