#!/usr/bin/env python3
"""Write and verify the ~/.local/bin launchers for every 33GOD component CLI (Story 7.1).

    cli-launchers.py install [--dry-run] [--no-probe]    write the launchers, then verify them
    cli-launchers.py check   [--no-probe]                verify only; exit 6 on drift (`--check` is an alias)
    cli-launchers.py upgrade <package...> | --all        `npm i -g` the named npm-distributed CLIs, then
                                                         rewrite their launchers [--dry-run to see the plan]

Each Node CLI declared in ../cli-launchers.toml gets a generated /bin/sh wrapper
that execs the pinned Node (resolved through mise) with the package's real `bin`
entry, so the CLI does not depend on the caller's cwd, PATH or mise pins. A
[[script_cli]] (hermes-pm) gets a symlink to its checkout file. Python CLIs are
only probed. No generated path carries a version directory (`.../installs/x/0.4.10/`):
npm CLIs live in the global npm prefix (~/.local/lib/node_modules/<pkg>), so
`upgrade` and `mise prune` can never leave a wrapper pointing at a deleted install.

Probes run every CLI from a scratch directory in three environments:
  minimal-path          `env -i HOME PATH=<bin_dir>:/usr/bin:/bin`
  decoy-node+node20-pin a decoy `node` first on PATH and a mise.toml pinning node 20
  mise-exec+node20-pin  `mise exec -- <cli>` with mise on PATH and the mise shims dir and <bin_dir>
                        in PATH as an agent shell has them, in a scratch dir whose trusted
                        mise.toml pins node 20. This is the probe that catches a global mise tool
                        (or any shim) putting a competing binary ahead of the launcher.
                        Limitation: the global mise config's [env] runs `op read`; with no
                        op session `mise exec` itself fails, and the probe reports
                        W_MISE_PROBE_SKIPPED (a warning, never a silent pass). --no-mise-probe skips it.
Every Node launcher's entry also gets a `node --check` (so bins with no safe live
invocation, such as pjangler-mcp, are still proven to exist and parse).

`npm i -g` (even --no-bin-links) deletes the generated wrappers of the package it
replaces, and refuses with EEXIST when one is present and --force is absent. Upgrade a
declared CLI with `upgrade`, never bare `npm i -g`: it runs `npm i -g --prefix <prefix>
--force --no-bin-links <pkg>@latest`, then re-runs install for those launchers (also when
npm fails), so PATH is never left without them.

--json prints the shared envelope {schema, command, ok, exit, data, findings}
(skillex's v2). Exits: 0 ok, 1 failure (a CLI is broken, unresolvable, or npm failed),
2 usage or config, 4 partial (install wrote some wrappers but not all), 6 drift (check:
a wrapper is missing or differs from what install would write).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PLATFORM = Path(__file__).resolve().parents[1]
GOD_ROOT = PLATFORM.parent
DEFAULT_CONFIG = PLATFORM / "cli-launchers.toml"
INSTALLER = "33god-platform/scripts/cli-launchers.py"
MARKER = "# 33god-cli-launcher v1"
SCHEMA = 2

OK, FAILURE, CONFIG, PARTIAL, DRIFT = 0, 1, 2, 4, 6
PROBE_TIMEOUT_S = 60
NPM_TIMEOUT_S = 900
PIN_MAJOR = "20"  # the node major the scratch mise.toml pins; must sit below the launcher's node
# A mise version directory (`.../installs/<tool>/0.4.10/...`). A launcher path containing one breaks on
# `mise upgrade` and `mise prune`. mise's major alias (`installs/node/24`) deliberately does not match.
VERSIONED_PATH = re.compile(r"/installs/[^/]+/v?\d+\.\d+")

LABEL_MINIMAL, LABEL_DECOY, LABEL_MISE = "minimal-path", "decoy-node+node20-pin", "mise-exec+node20-pin"


class ConfigError(Exception):
    pass


def expand(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value)))


def versioned_path(path: str | Path) -> bool:
    return bool(VERSIONED_PATH.search(str(path)))


def finding(code: str, severity: str, message: str, path: str | None = None, fix: str | None = None) -> dict:
    out = {"code": code, "severity": severity, "message": message}
    if path:
        out["path"] = path
    if fix:
        out["fix"] = fix
    return out


@dataclass
class Launcher:
    name: str
    package: str
    entry: Path | None = None
    kind: str = "node"  # node: generated /bin/sh wrapper; script: symlink to a checkout file
    version: str | None = None
    error: str | None = None
    status: str = "pending"
    previous: str | None = None

    def content(self, node: Path) -> str:
        kind, _, name = self.package.partition(":")
        if kind == "npm-global":
            refresh = [
                f"# Upgrade with: python3 {GOD_ROOT / INSTALLER} upgrade {name or self.name}",
                "# (bare `npm i -g` deletes this file; `upgrade` installs, then rewrites it.)",
            ]
        else:
            refresh = [f"# Source is a git checkout; after moving it run: python3 {GOD_ROOT / INSTALLER} install"]
        lines = [
            "#!/bin/sh",
            f"{MARKER}: generated by {INSTALLER}; do not edit.",
            f"# {self.name} <- {self.package}",
            *refresh,
            f'exec {shlex.quote(str(node))} {shlex.quote(str(self.entry))} "$@"',
        ]
        return "\n".join(lines) + "\n"

    def in_sync(self, target: Path, node: Path) -> bool:
        if not os.access(target, os.X_OK):
            return False
        if self.kind == "script":
            return target.is_symlink() and os.readlink(target) == str(self.entry)
        if target.is_symlink() or not target.is_file():
            return False
        return target.read_text(encoding="utf-8", errors="replace") == self.content(node)


@dataclass
class Plan:
    bin_dir: Path
    node: Path | None
    node_version: str | None
    node_major: str
    mise: str | None = None
    mise_shims: Path | None = None
    launchers: list[Launcher] = field(default_factory=list)
    probes: list[dict] = field(default_factory=list)
    python: list[dict] = field(default_factory=list)
    syntax: list[dict] = field(default_factory=list)
    upgrade: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)


class Resolver:
    def __init__(self, home: Path, god_root: Path, mise: str | None = None, node_override: Path | None = None):
        self.home = home
        self.god_root = god_root
        self.mise = mise or shutil.which("mise") or str(home / ".local/bin/mise")
        self.node_override = node_override

    def _mise(self, *args: str) -> str:
        done = subprocess.run([self.mise, *args], cwd=self.home, capture_output=True, text=True, timeout=600)
        if done.returncode != 0:
            raise ConfigError(f"mise {' '.join(args)} failed: {(done.stderr or done.stdout).strip()}")
        return done.stdout.strip()

    def node(self, major: str) -> Path:
        if self.node_override:
            return self.node_override
        try:
            where = self._mise("where", f"node@{major}")
        except ConfigError:
            self._mise("install", f"node@{major}")
            where = self._mise("where", f"node@{major}")
        concrete = Path(where)
        alias = concrete.parent / major
        base = alias if alias.exists() and alias.resolve() == concrete.resolve() else concrete
        node = base / "bin" / "node"
        if not os.access(node, os.X_OK):
            raise ConfigError(f"node@{major} resolved to {node}, which is not executable")
        return node

    def package_dir(self, spec: str, node: Path | None, npm_roots: list[Path]) -> Path:
        kind, _, name = spec.partition(":")
        if kind == "repo":
            return self.god_root / name
        if kind == "npm-global":
            roots = list(npm_roots)
            if node is not None:
                roots.append(node.parent.parent / "lib" / "node_modules")
            for root in roots:
                if (root / name / "package.json").is_file():
                    return root / name
            raise ConfigError(f"{name} is not installed in any of: {', '.join(map(str, roots))}")
        if kind == "mise-npm":
            raise ConfigError(f"{spec}: mise-npm is retired: its install path carries a version directory that "
                              f"`mise upgrade`/`mise prune` invalidates. Declare npm-global:{name} and run `upgrade`")
        raise ConfigError(f"unknown package kind in {spec!r} (repo:, npm-global:)")


def load_config(path: Path) -> dict:
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"{path}: {error}") from error
    if config.get("schema") != 1:
        raise ConfigError(f"{path}: schema must be 1")
    for item in config.get("node_cli", []):
        if not item.get("package") or not item.get("bins"):
            raise ConfigError(f"{path}: every [[node_cli]] needs package and bins")
        if item["package"].startswith("mise-npm:"):
            raise ConfigError(f"{path}: {item['package']}: mise-npm is retired (version directories in launcher paths); use npm-global:")
        for probe in node_probes(item):
            if probe.get("bin") not in item["bins"]:
                raise ConfigError(f"{path}: probe bin {probe.get('bin')!r} is not one of {item['bins']}")
    for item in config.get("script_cli", []):
        if not item.get("name") or not str(item.get("source", "")).startswith("repo:"):
            raise ConfigError(f"{path}: every [[script_cli]] needs a name and a repo:<path> source")
    names = ([b for item in config.get("node_cli", []) for b in item["bins"]] + [p["name"] for p in config.get("python_cli", [])]
             + [s["name"] for s in config.get("script_cli", [])])
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        raise ConfigError(f"{path}: names declared twice: {', '.join(duplicates)}")
    return config


def node_probes(item: dict) -> list[dict]:
    """The package's primary `probe` plus any extra `probes`, each naming one of its bins."""
    return ([item["probe"]] if item.get("probe") else []) + list(item.get("probes", []))


def probe_entry(bin_name: str, probe: dict, god_root: Path, version: str | None = None) -> dict:
    env = {k: str(v).replace("{god_root}", str(god_root)) for k, v in (probe.get("env") or {}).items()}
    return {"bin": bin_name, "args": list(probe.get("args", ["--version"])), "expect": probe.get("expect", "version"),
            "exit": int(probe.get("exit", 0)), "env": env, "version": version}


def build_plan(config: dict, resolver: Resolver, bin_dir: Path | None = None, only: set[str] | None = None) -> Plan:
    """`only` restricts the plan to those node_cli package specs (the upgrade path)."""
    major = str(config.get("node", "24"))
    plan = Plan(bin_dir=bin_dir or expand(config.get("bin_dir", "~/.local/bin")), node=None, node_version=None, node_major=major,
                mise=resolver.mise, mise_shims=expand(config.get("mise_shims", "~/.local/share/mise/shims")))
    try:
        plan.node = resolver.node(major)
        done = subprocess.run([str(plan.node), "--version"], capture_output=True, text=True, timeout=30)
        plan.node_version = done.stdout.strip()
        got = plan.node_version.lstrip("v").split(".")[0]
        if done.returncode != 0 or not got.isdigit() or int(got) < int(major):
            plan.findings.append(finding("E_NODE_TOO_OLD", "error", f"{plan.node} reports {plan.node_version!r}; need Node >= {major}", str(plan.node)))
        if versioned_path(plan.node):
            plan.findings.append(finding("W_NODE_VERSIONED_PATH", "warning",
                                         f"{plan.node} carries a version directory (no node/{major} alias); `mise prune` can break the wrappers",
                                         str(plan.node), fix=f"mise install node@{major} (creates the installs/node/{major} alias)"))
    except (ConfigError, OSError, subprocess.SubprocessError) as error:
        plan.findings.append(finding("E_NODE_UNRESOLVED", "error", str(error), fix=f"mise install node@{major}"))
    npm_roots = [expand(r) for r in config.get("npm_global_roots", [])]
    for item in config.get("node_cli", []):
        spec = item["package"]
        if only is not None and spec not in only:
            continue
        try:
            pkg = resolver.package_dir(spec, plan.node, npm_roots)
            manifest = json.loads((pkg / "package.json").read_text(encoding="utf-8"))
            bins = manifest.get("bin") or {}
            if isinstance(bins, str):
                bins = {manifest["name"].split("/")[-1]: bins}
        except (ConfigError, OSError, ValueError) as error:
            for name in item["bins"]:
                plan.launchers.append(Launcher(name, spec, error=str(error), status="unresolved"))
            continue
        for name in item["bins"]:
            if name not in bins:
                plan.launchers.append(Launcher(name, spec, error=f"{pkg}/package.json has no bin {name!r}", status="unresolved"))
                continue
            entry = Path(os.path.normpath(pkg / bins[name]))  # never realpath: that would bake in a version directory
            if not entry.is_file():
                plan.launchers.append(Launcher(name, spec, error=f"bin entry {entry} does not exist (unbuilt?)", status="unresolved"))
                continue
            if versioned_path(entry):
                plan.launchers.append(Launcher(name, spec, error=f"E_VERSIONED_PATH: {entry} carries a version directory", status="unresolved"))
                continue
            plan.launchers.append(Launcher(name, spec, entry=entry, version=manifest.get("version")))
        for probe in node_probes(item):
            plan.probes.append(probe_entry(probe["bin"], probe, resolver.god_root, manifest.get("version")))
    if only is None:
        for item in config.get("script_cli", []):
            source = resolver.god_root / item["source"].partition(":")[2]
            if not source.is_file() or not os.access(source, os.X_OK):
                plan.launchers.append(Launcher(item["name"], item["source"], kind="script", error=f"{source} is missing or not executable", status="unresolved"))
            else:
                plan.launchers.append(Launcher(item["name"], item["source"], entry=source, kind="script"))
            if item.get("probe"):
                plan.probes.append(probe_entry(item["name"], item["probe"], resolver.god_root))
        for item in config.get("python_cli", []):
            plan.python.append({"name": item["name"], "args": list(item.get("probe", ["--help"])), "expect": "exit0", "exit": 0, "env": {}})
    for launcher in plan.launchers:
        if launcher.error:
            plan.findings.append(finding("E_UNRESOLVED", "error", f"{launcher.name}: {launcher.error}", fix=f"install or build {launcher.package}, then re-run install"))
    return plan


def describe(path: Path) -> str:
    if path.is_symlink():
        return f"symlink -> {os.readlink(path)}"
    if path.is_file():
        return "generated wrapper" if MARKER in path.read_text(encoding="utf-8", errors="replace") else "file"
    return "missing"


def compare(plan: Plan) -> None:
    for launcher in plan.launchers:
        if launcher.error or plan.node is None:
            continue
        target = plan.bin_dir / launcher.name
        launcher.previous = describe(target)
        if launcher.in_sync(target, plan.node):
            launcher.status = "ok"
        else:
            launcher.status = "missing" if launcher.previous == "missing" else "drift"


def write(plan: Plan, dry_run: bool) -> None:
    plan.bin_dir.mkdir(parents=True, exist_ok=True)
    for launcher in plan.launchers:
        if launcher.status not in ("missing", "drift"):
            continue
        if dry_run:
            launcher.status = f"would-write ({launcher.status})"
            continue
        target = plan.bin_dir / launcher.name
        if launcher.kind == "script":
            tmp = plan.bin_dir / f".{launcher.name}.{os.getpid()}.link"
            tmp.unlink(missing_ok=True)
            try:
                os.symlink(launcher.entry, tmp)
                os.replace(tmp, target)
            except BaseException:
                tmp.unlink(missing_ok=True)
                raise
            launcher.status = "written"
            continue
        fd, tmp_name = tempfile.mkstemp(prefix=f".{launcher.name}.", dir=plan.bin_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(launcher.content(plan.node))
            os.chmod(tmp_name, 0o755)
            os.replace(tmp_name, target)  # replaces a symlink itself, never its target
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
        launcher.status = "written"


def probe_envs(plan: Plan, scratch: Path, mise_probe: bool) -> list[dict]:
    """Probe environments. `mise` ones run the CLI under `mise exec` by bare name, so PATH order decides."""
    home = str(Path.home())
    decoy = scratch / "decoy-bin"
    decoy.mkdir()
    (decoy / "node").write_text("#!/bin/sh\necho 'decoy node on PATH: the launcher did not pin its interpreter' >&2\nexit 97\n")
    (decoy / "node").chmod(0o755)
    (scratch / "mise.toml").write_text(f'[tools]\nnode = "{PIN_MAJOR}"\n')
    minimal = f"{plan.bin_dir}:/usr/bin:/bin"
    envs = [{"label": LABEL_MINIMAL, "env": {"HOME": home, "PATH": minimal}},
            {"label": LABEL_DECOY, "env": {"HOME": home, "PATH": f"{decoy}:{minimal}"}}]
    if mise_probe:
        order = [str(plan.mise_shims), str(plan.bin_dir), str(Path(plan.mise).parent) if plan.mise else "", "/usr/bin", "/bin"]
        path = ":".join(dict.fromkeys(part for part in order if part))
        mise_env = {"HOME": home, "PATH": path, "MISE_TRUSTED_CONFIG_PATHS": str(scratch)}
        ready = mise_ready(plan, scratch, mise_env)
        if ready is None:
            envs.append({"label": LABEL_MISE, "env": mise_env, "mise": plan.mise})
        else:
            plan.findings.append(finding("W_MISE_PROBE_SKIPPED", "warning", f"the {LABEL_MISE} probe did not run: {ready}",
                                         fix="check `mise exec -- node --version` in a dir pinning node 20 (global [env] `op read` needs an op session)"))
    return envs


def mise_ready(plan: Plan, scratch: Path, env: dict) -> str | None:
    """None when `mise exec` works in the scratch dir and its node pin really shadows the launcher's node."""
    if not plan.mise or not (shutil.which(plan.mise) or os.access(plan.mise, os.X_OK)):
        return f"mise not found ({plan.mise})"
    try:
        done = subprocess.run([plan.mise, "exec", "--", "node", "--version"], cwd=scratch, env=env, capture_output=True, text=True,
                              timeout=300, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as error:
        return str(error)
    if done.returncode != 0:
        return f"mise exec failed: {(done.stderr or done.stdout).strip()[-300:]}"
    major = done.stdout.strip().lstrip("v").split(".")[0]
    if not major.isdigit() or int(major) >= int(plan.node_major):
        return f"the scratch pin did not take effect (node {done.stdout.strip()!r} under mise exec)"
    return None


def evaluate(probe: dict, code: int, out: str, err: str) -> tuple[bool, str, str]:
    first = (out or err).splitlines()[0] if (out or err) else ""
    expect, want = probe["expect"], probe.get("exit", 0)
    if code != want:
        return False, f"exit {code} (want {want}): {(err or out)[-300:]}", first
    if expect == "version":
        return bool(probe.get("version")) and probe["version"] in first, f"printed {first!r}, expected version {probe.get('version')}", first
    for kind in ("prefix", "suffix"):
        if expect.startswith(f"{kind}:"):
            text = expect[len(kind) + 1:]
            good = first.startswith(text) if kind == "prefix" else first.endswith(text)
            return good, f"printed {first!r}, expected it to {'start' if kind == 'prefix' else 'end'} with {text!r}", first
    return True, "", first


def run_probes(plan: Plan, mise_probe: bool = True) -> None:
    jobs = [(p["bin"] if "bin" in p else p["name"], p) for p in plan.probes + plan.python]
    with tempfile.TemporaryDirectory(prefix="33god-cli-probe-") as temp:
        scratch = Path(temp)
        envs = probe_envs(plan, scratch, mise_probe)
        for name, probe in jobs:
            probe["results"] = []
            exe = plan.bin_dir / name
            if not os.access(exe, os.X_OK):
                probe["ok"] = False
                plan.findings.append(finding("E_CLI_MISSING", "error", f"{name}: {exe} is missing or not executable", str(exe)))
                continue
            for spec in envs:
                argv = [spec["mise"], "exec", "--", name, *probe["args"]] if spec.get("mise") else [str(exe), *probe["args"]]
                try:
                    done = subprocess.run(argv, cwd=scratch, env={**spec["env"], **probe.get("env", {})}, capture_output=True, text=True,
                                          timeout=PROBE_TIMEOUT_S, stdin=subprocess.DEVNULL)
                    out, code, err = done.stdout.strip(), done.returncode, done.stderr.strip()
                except subprocess.TimeoutExpired:
                    out, code, err = "", -1, f"timed out after {PROBE_TIMEOUT_S}s"
                good, why, first = evaluate(probe, code, out, err)
                probe["results"].append({"env": spec["label"], "ok": good, "exit": code, "first_line": first})
                if not good:
                    plan.findings.append(finding("E_PROBE_FAILED", "error", f"{name} {' '.join(probe['args'])} [{spec['label']}]: {why}", str(exe)))
            probe["ok"] = all(r["ok"] for r in probe["results"])
        probed_bins = {name for name, _ in jobs}
        for launcher in plan.launchers:
            if launcher.kind != "node" or launcher.entry is None or plan.node is None:
                continue
            try:
                done = subprocess.run([str(plan.node), "--check", str(launcher.entry)], capture_output=True, text=True, timeout=PROBE_TIMEOUT_S,
                                      stdin=subprocess.DEVNULL)
                good, why = done.returncode == 0, (done.stderr or done.stdout).strip()[-300:]
            except (OSError, subprocess.SubprocessError) as error:
                good, why = False, str(error)
            plan.syntax.append({"name": launcher.name, "entry": str(launcher.entry), "ok": good, "live_probe": launcher.name in probed_bins})
            if not good:
                plan.findings.append(finding("E_SYNTAX", "error", f"{launcher.name}: `node --check {launcher.entry}` failed: {why}", str(launcher.entry)))


def summarize(plan: Plan, command: str, probed: bool) -> dict:
    failures = any(f["severity"] == "error" for f in plan.findings)
    drift = [launcher.name for launcher in plan.launchers if launcher.status in ("missing", "drift") or launcher.status.startswith("would-write")]
    if command == "check" and drift:
        for name in drift:
            plan.findings.append(finding("E_DRIFT", "error", f"{name}: {plan.bin_dir / name} differs from the generated launcher",
                                         str(plan.bin_dir / name), fix=f"python3 {GOD_ROOT / INSTALLER} install"))
    if failures:
        written = any(launcher.status in ("ok", "written") for launcher in plan.launchers)
        exit_code = PARTIAL if command in ("install", "upgrade") and written else FAILURE
        if any(f["code"] == "E_NPM_FAILED" for f in plan.findings):
            exit_code = FAILURE
    elif drift and command == "check":
        exit_code = DRIFT
    else:
        exit_code = OK
    data = {
        "bin_dir": str(plan.bin_dir),
        "node": {"major": plan.node_major, "path": str(plan.node) if plan.node else None, "version": plan.node_version},
        "launchers": [{"name": l.name, "package": l.package, "kind": l.kind, "entry": str(l.entry) if l.entry else None, "version": l.version,
                       "status": l.status, "previous": l.previous, **({"error": l.error} if l.error else {})} for l in plan.launchers],
        "probes": plan.probes if probed else [],
        "python": plan.python if probed else [],
        "syntax": plan.syntax if probed else [],
        "upgrade": plan.upgrade,
    }
    return {"schema": SCHEMA, "command": f"cli-launchers {command}", "ok": exit_code == OK, "exit": exit_code, "data": data, "findings": plan.findings}


def render(result: dict) -> str:
    data = result["data"]
    lines = [f"node {data['node']['version'] or '?'} ({data['node']['path']})  bin_dir {data['bin_dir']}"]
    for u in data["upgrade"]:
        lines.append(f"  npm {u['status']:<10} {' '.join(u['command'])}")
    for l in data["launchers"]:
        extra = f"  (was {l['previous']})" if l["status"] == "written" and l["previous"] else ""
        lines.append(f"  {l['status']:<22} {l['name']:<16} {l['entry'] or l.get('error')}{extra}")
    for p in data["probes"] + data["python"]:
        name = p.get("bin") or p.get("name")
        verdict = "ok " if p.get("ok") else "BAD"
        detail = "; ".join(f"{r['env']}: {r['first_line'] or 'exit ' + str(r['exit'])}" for r in p.get("results", []))
        lines.append(f"  probe {verdict} {name} {' '.join(p['args'])}  {detail}")
    bad = [s["name"] for s in data["syntax"] if not s["ok"]]
    if data["syntax"]:
        lines.append(f"  node --check {len(data['syntax']) - len(bad)}/{len(data['syntax'])} entries parse" + (f"; BAD: {', '.join(bad)}" if bad else ""))
    for f in result["findings"]:
        lines.append(f"{f['severity'].upper()} {f['code']}: {f['message']}" + (f"  fix: {f['fix']}" if f.get("fix") else ""))
    lines.append(f"{result['command']}: {'ok' if result['ok'] else 'exit ' + str(result['exit'])}")
    return "\n".join(lines)


def split_package_arg(arg: str) -> tuple[str, str | None]:
    """`pj`, `pjangler`, `@delorenj/pjangler` or `skillex@0.4.10` -> (name as typed, requested version or None)."""
    name, at, version = arg.rpartition("@")
    if not at or not name:  # no version part, or only the scope's leading @
        return arg, None
    return name, version or None


def select_upgrade_targets(config: dict, names: list[str], everything: bool) -> list[tuple[dict, str | None]]:
    items = [item for item in config.get("node_cli", []) if item["package"].startswith("npm-global:")]
    if everything:
        return [(item, None) for item in items]
    targets = []
    for arg in names:
        typed, version = split_package_arg(arg)
        hit = [item for item in items if typed in (item["package"].partition(":")[2], item["package"].rpartition("/")[2], *item["bins"])]
        if not hit:
            declared = ", ".join(item["package"].partition(":")[2] for item in items)
            raise ConfigError(f"{arg!r} is not a declared npm-global package (declared: {declared}); repo: packages are updated with git")
        targets.append((hit[0], version))
    return targets


def run_upgrade(plan: Plan, config: dict, resolver: Resolver, targets: list[tuple[dict, str | None]], dry_run: bool, npm: Path | None) -> None:
    """npm-install each target into the declared prefix; the caller re-runs install for those launchers either way."""
    if plan.node is None:
        return
    prefix = expand(config.get("npm_prefix", "~/.local"))
    npm = npm or plan.node.parent / "npm"
    env = {**os.environ, "PATH": f"{plan.node.parent}:{os.environ.get('PATH', '')}"}
    for item, version in targets:
        name = item["package"].partition(":")[2]
        command = [str(npm), "install", "--global", "--prefix", str(prefix), "--force", "--no-bin-links", "--no-fund", "--no-audit", f"{name}@{version or 'latest'}"]
        record = {"package": item["package"], "bins": item["bins"], "command": command, "status": "planned" if dry_run else "pending", "exit": None}
        plan.upgrade.append(record)
        if dry_run:
            continue
        try:
            done = subprocess.run(command, capture_output=True, text=True, timeout=NPM_TIMEOUT_S, env=env, stdin=subprocess.DEVNULL)
            record.update(status="ok" if done.returncode == 0 else "failed", exit=done.returncode, output_tail=(done.stdout + done.stderr).strip()[-400:])
        except (OSError, subprocess.SubprocessError) as error:
            record.update(status="failed", exit=-1, output_tail=str(error))
        if record["status"] == "failed":
            plan.findings.append(finding("E_NPM_FAILED", "error", f"{name}: npm install exited {record['exit']}: {record.get('output_tail', '')[-200:]}",
                                         fix="launchers were re-written from whatever is installed; fix npm and re-run upgrade"))


def usage_exit(parser: argparse.ArgumentParser, as_json: bool, command: str, message: str) -> int:
    if as_json:
        print(json.dumps({"schema": SCHEMA, "command": f"cli-launchers {command}", "ok": False, "exit": CONFIG, "data": None,
                          "findings": [finding("E_USAGE", "error", message)]}, indent=2))
        return CONFIG
    parser.error(message)
    return CONFIG


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli-launchers.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("command", nargs="?", choices=["install", "check", "upgrade"])
    parser.add_argument("packages", nargs="*", help="upgrade: declared npm packages, by package name, short name or bin (pj, skillex@0.4.10)")
    parser.add_argument("--check", dest="check_alias", action="store_true", help="alias of the `check` command")
    parser.add_argument("--all", action="store_true", help="upgrade: every declared npm-global package")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--bin-dir", type=Path, help="override bin_dir from the config")
    parser.add_argument("--node", type=Path, help="use this node binary instead of resolving it through mise")
    parser.add_argument("--mise", help="mise binary (default: the one on PATH)")
    parser.add_argument("--npm", type=Path, help="upgrade: npm binary (default: the pinned node's npm)")
    parser.add_argument("--god-root", type=Path, default=GOD_ROOT, help="root that repo: packages resolve against")
    parser.add_argument("--dry-run", action="store_true", help="install/upgrade: say what would happen; change nothing")
    parser.add_argument("--no-probe", action="store_true", help="skip running the CLIs")
    parser.add_argument("--no-mise-probe", action="store_true", help="skip the `mise exec` probe environment")
    parser.add_argument("--json", action="store_true", help="print the {schema, command, ok, exit, data, findings} envelope")
    args = parser.parse_args(argv)
    command = args.command
    if args.check_alias:
        if command not in (None, "check"):
            return usage_exit(parser, args.json, command, f"--check is an alias of the check command; it cannot be combined with {command}")
        command = "check"
    if command is None:
        return usage_exit(parser, args.json, "?", "a command is required: install, check (or --check), upgrade")
    if args.packages and command != "upgrade":
        return usage_exit(parser, args.json, command, f"{command} takes no package names (got {' '.join(args.packages)})")
    if command == "upgrade" and not args.packages and not args.all:
        return usage_exit(parser, args.json, command, "upgrade needs at least one package (pj, skillex, ...) or --all")
    try:
        config = load_config(args.config)
    except ConfigError as error:
        result = {"schema": SCHEMA, "command": f"cli-launchers {command}", "ok": False, "exit": CONFIG, "data": None,
                  "findings": [finding("E_CONFIG", "error", str(error), str(args.config))]}
        print(json.dumps(result, indent=2) if args.json else f"ERROR {error}", file=sys.stdout if args.json else sys.stderr)
        return CONFIG
    resolver = Resolver(Path.home(), args.god_root, mise=args.mise, node_override=args.node)
    targets, only = [], None
    if command == "upgrade":
        try:
            targets = select_upgrade_targets(config, args.packages, args.all)
        except ConfigError as error:
            return usage_exit(parser, args.json, command, str(error))
        only = {item["package"] for item, _ in targets}
    plan = build_plan(config, resolver, args.bin_dir, only=only) if command != "upgrade" else None
    if command == "upgrade":
        # npm first, then the plan is built from what is on disk now; a failed npm still gets its launchers repaired
        pre = Plan(bin_dir=args.bin_dir or expand(config.get("bin_dir", "~/.local/bin")), node=None, node_version=None, node_major=str(config.get("node", "24")))
        try:
            pre.node = resolver.node(pre.node_major)
        except ConfigError as error:
            pre.findings.append(finding("E_NODE_UNRESOLVED", "error", str(error), fix=f"mise install node@{pre.node_major}"))
        run_upgrade(pre, config, resolver, targets, args.dry_run, args.npm)
        plan = build_plan(config, resolver, args.bin_dir, only=only)
        plan.upgrade, plan.findings = pre.upgrade, pre.findings + [f for f in plan.findings if f not in pre.findings]
    compare(plan)
    if command in ("install", "upgrade") and plan.node is not None:
        write(plan, args.dry_run)
    probed = not args.no_probe and not (command in ("install", "upgrade") and args.dry_run)
    if probed:
        run_probes(plan, mise_probe=not args.no_mise_probe)
    result = summarize(plan, command, probed)
    print(json.dumps(result, indent=2) if args.json else render(result))
    return result["exit"]


if __name__ == "__main__":
    sys.exit(main())
