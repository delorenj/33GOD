#!/usr/bin/env python3
"""Fan one project-scoped hook master into Claude, Codex, Kimi, and Hermes."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
REPO_ROOT = HOOK_DIR.parent.parent
MASTER = HOOK_DIR / "hooks.master.json"
QUIET = False


def log(message: str) -> None:
    if not QUIET:
        print(message)


def warn(message: str) -> None:
    print(f"[33god-hooks] {message}", file=sys.stderr)


def load_master() -> dict:
    return json.loads(MASTER.read_text())


def load_disabled_agents() -> set[str]:
    disabled: set[str] = set()
    path = REPO_ROOT / ".agents" / "local.json"
    if path.exists():
        try:
            disabled.update((json.loads(path.read_text()).get("hooks") or {}).get("disabled_agents") or [])
        except (OSError, json.JSONDecodeError) as exc:
            warn(f"ignoring malformed .agents/local.json: {exc}")
    for name in ("claude", "codex", "kimi", "hermes"):
        if os.environ.get(f"GOD_HOOKS_SKIP_{name.upper()}") == "1":
            disabled.add(name)
    return disabled


def agent_command(master: dict, agent_key: str, hook: dict) -> str:
    agent = master["agents"][agent_key]
    base = agent["base_dir"].replace("{repo}", str(REPO_ROOT))
    return (
        f"{base}/lib/hook-guard.sh {hook['id']} "
        f"{base}/{hook['script']} --client {agent_key}"
    )


def desired_commands(master: dict, agent_key: str) -> list[tuple[str, str | None, dict]]:
    agent = master["agents"][agent_key]
    unit = agent.get("timeout_unit", "s")
    mapping = agent["lifecycle_events"]
    result = []
    for hook in master["hooks"]:
        event = mapping.get(hook["lifecycle"])
        if not event:
            continue
        timeout = hook["timeout_s"] * (1000 if unit == "ms" else 1)
        result.append(
            (
                event,
                hook.get("matcher"),
                {
                    "type": "command",
                    "command": agent_command(master, agent_key, hook),
                    "timeout": timeout,
                },
            )
        )
    return result


def event_groups(master: dict, agent_key: str) -> dict[str, list[dict]]:
    buckets: dict[tuple[str, str | None], list[dict]] = {}
    order: list[tuple[str, str | None]] = []
    for event, matcher, command in desired_commands(master, agent_key):
        key = (event, matcher)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(command)
    groups: dict[str, list[dict]] = {}
    for event, matcher in order:
        group: dict = {"hooks": buckets[(event, matcher)]}
        if matcher is not None:
            group["matcher"] = matcher
        groups.setdefault(event, []).append(group)
    return groups


def hook_marker() -> str:
    return "/.agents/hooks/merge-forward/session-end.sh"


def strip_marked(hooks: dict) -> bool:
    changed = False
    marker = hook_marker()
    for event, groups in list(hooks.items()):
        if not isinstance(groups, list):
            warn(f"preserving non-list foreign hook group for {event}")
            continue
        new_groups = []
        for group in groups:
            if not isinstance(group, dict):
                new_groups.append(group)
                continue
            commands = group.get("hooks", []) if isinstance(group, dict) else []
            kept = [item for item in commands if marker not in str(item.get("command", ""))]
            if len(kept) != len(commands):
                changed = True
            if kept:
                updated = dict(group)
                updated["hooks"] = kept
                new_groups.append(updated)
            elif not commands:
                new_groups.append(group)
        if new_groups:
            hooks[event] = new_groups
        else:
            hooks.pop(event, None)
            changed = True
    return changed


def json_target(master: dict, agent_key: str) -> Path:
    raw = master["agents"][agent_key]["config_target"]
    path = Path(os.path.expanduser(raw))
    return path if path.is_absolute() else REPO_ROOT / path


def load_json_target(path: Path) -> dict | None:
    if not path.exists():
        return {"hooks": {}}
    try:
        data = json.loads(path.read_text() or "{}")
    except json.JSONDecodeError as exc:
        warn(f"refusing to modify invalid JSON at {path}: {exc}")
        return None
    if not isinstance(data, dict):
        warn(f"refusing to modify non-object JSON at {path}")
        return None
    return data


def backup_once(path: Path) -> None:
    backup = path.with_suffix(path.suffix + ".33god-bak")
    if path.exists() and not backup.exists():
        backup.write_text(path.read_text())


def install_json(master: dict, agent_key: str) -> None:
    path = json_target(master, agent_key)
    if agent_key == "codex" and not path.parent.exists():
        log("codex: config home absent, skipping")
        return
    data = load_json_target(path)
    if data is None:
        return
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        warn(f"refusing to replace non-object hooks key in {path}")
        return
    strip_marked(hooks)
    for event, groups in event_groups(master, agent_key).items():
        hooks.setdefault(event, []).extend(groups)
    serialized = json.dumps(data, indent=2) + "\n"
    if path.exists() and path.read_text() == serialized:
        log(f"{agent_key}: up to date")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_once(path)
    path.write_text(serialized)
    log(f"{agent_key}: installed into {path}")


def uninstall_json(master: dict, agent_key: str) -> None:
    path = json_target(master, agent_key)
    data = load_json_target(path) if path.exists() else None
    if data is None:
        return
    hooks = data.get("hooks")
    if isinstance(hooks, dict) and strip_marked(hooks):
        path.write_text(json.dumps(data, indent=2) + "\n")
        log(f"{agent_key}: uninstalled from {path}")


def check_json(master: dict, agent_key: str) -> bool:
    path = json_target(master, agent_key)
    if not path.exists():
        warn(f"DRIFT: {agent_key} target missing: {path}")
        return False
    data = load_json_target(path)
    if data is None:
        return False
    actual = sorted(
        item.get("command", "")
        for groups in (data.get("hooks") or {}).values()
        if isinstance(groups, list)
        for group in groups
        if isinstance(group, dict)
        for item in group.get("hooks", [])
        if isinstance(item, dict)
        if hook_marker() in item.get("command", "")
    )
    wanted = sorted(item[2]["command"] for item in desired_commands(master, agent_key))
    if actual != wanted:
        warn(f"DRIFT: {agent_key} hook projection differs from hooks.master.json")
        return False
    log(f"{agent_key}: in sync")
    return True


def kimi_target(master: dict) -> Path:
    agent = master["agents"]["kimi"]
    configured_home = os.environ.get(agent.get("config_home_env", ""))
    return Path(configured_home) / "config.toml" if configured_home else Path(os.path.expanduser(agent["config_target"]))


def kimi_markers(master: dict) -> tuple[str, str]:
    label = f"{master['marker']} ({REPO_ROOT.name})"
    return f"# >>> {label} BEGIN", f"# <<< {label} END"


def kimi_block(master: dict) -> str:
    begin, end = kimi_markers(master)
    lines = [begin]
    for event, matcher, item in desired_commands(master, "kimi"):
        lines.extend(["[[hooks]]", f'event = "{event}"'])
        if matcher:
            lines.append(f'matcher = "{matcher}"')
        lines.extend([f'command = "{item["command"]}"', f'timeout = {item["timeout"]}', ""])
    lines.append(end)
    return "\n".join(lines) + "\n"


def strip_kimi(text: str, master: dict) -> tuple[str, bool]:
    begin, end = kimi_markers(master)
    pattern = re.compile(r"\n?" + re.escape(begin) + r".*?" + re.escape(end) + r"\n?", re.DOTALL)
    updated, count = pattern.subn("", text)
    return updated, count > 0


# A [[hooks]] array-of-tables entry: the header plus every following line up to
# the next top-level [ header (or EOF). MULTILINE only — with DOTALL the inner
# `.` would cross newlines and the first match would swallow the rest of the
# file, taking every unrelated hook and section with it.
KIMI_HOOK_SECTION = re.compile(r"(?m)^\[\[hooks\]\][ \t]*\n(?:(?!\[).*\n?)*")


def strip_kimi_orphans(text: str, master: dict) -> tuple[str, int]:
    """Drop [[hooks]] entries we own that live OUTSIDE the marker block.

    Every earlier fan-out that ran before the marker block existed (or under a
    different repo-name marker) left a full copy behind. Because the old check
    only asked whether the marker block was present as a substring, those
    copies were invisible and the hook fired once per stray copy per session.
    """
    marker = hook_marker()
    removed = 0

    def drop(match: re.Match[str]) -> str:
        nonlocal removed
        if marker in match.group(0):
            removed += 1
            return ""
        return match.group(0)

    return KIMI_HOOK_SECTION.sub(drop, text), removed


def kimi_owned_commands(text: str) -> list[str]:
    """Every command in the file that this fan-out owns, block or not."""
    marker = hook_marker()
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - py<3.11
        return [
            line.split("=", 1)[1].strip().strip('"').strip("'")
            for line in text.splitlines()
            if line.strip().startswith("command") and marker in line
        ]
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        warn(f"kimi: config is not valid TOML ({exc}); falling back to text scan")
        return [
            line.split("=", 1)[1].strip().strip('"').strip("'")
            for line in text.splitlines()
            if line.strip().startswith("command") and marker in line
        ]
    hooks = data.get("hooks")
    if not isinstance(hooks, list):
        return []
    return [
        entry["command"]
        for entry in hooks
        if isinstance(entry, dict) and marker in str(entry.get("command", ""))
    ]


def install_kimi(master: dict) -> None:
    path = kimi_target(master)
    if not path.parent.exists():
        log("kimi: config home absent, skipping")
        return
    original = path.read_text() if path.exists() else ""
    body, _ = strip_kimi(original, master)
    body, orphans = strip_kimi_orphans(body, master)
    body = re.sub(r"(?m)^\s*hooks\s*=\s*\[\s*\]\s*\n?", "", body).rstrip("\n")
    updated = (body + "\n\n" if body else "") + kimi_block(master)
    if updated == original:
        log("kimi: up to date")
        return
    backup_once(path)
    path.write_text(updated)
    if orphans:
        log(f"kimi: reaped {orphans} orphaned copy(ies) of our hook outside the marker block")
    log(f"kimi: installed into {path}")


def uninstall_kimi(master: dict) -> None:
    path = kimi_target(master)
    if not path.exists():
        return
    updated, changed = strip_kimi(path.read_text(), master)
    if changed:
        path.write_text(updated.rstrip("\n") + ("\n" if updated.strip() else ""))
        log(f"kimi: uninstalled from {path}")


def check_kimi(master: dict) -> bool:
    path = kimi_target(master)
    if not path.exists():
        # Match check_json: a configured client whose config is gone is drift,
        # not a pass. Only an absent config HOME means "this client isn't here".
        if not path.parent.exists():
            log("kimi: config home absent, skipping")
            return True
        warn(f"DRIFT: kimi target missing: {path}")
        return False
    text = path.read_text()
    # Compare the FULL SET of commands we own, not just "is the block present".
    # A substring test passes while stray copies of the same hook sit outside
    # the block, silently multiplying how often it fires.
    actual = sorted(kimi_owned_commands(text))
    wanted = sorted(item[2]["command"] for item in desired_commands(master, "kimi"))
    if actual != wanted:
        extra = len(actual) - len(wanted)
        if extra > 0 and set(actual) == set(wanted):
            warn(f"DRIFT: kimi has {extra} duplicate copy(ies) of our hook (it would fire {len(actual)}x per session)")
        else:
            warn("DRIFT: kimi hook projection differs from hooks.master.json")
        return False
    if kimi_block(master).strip() not in text:
        warn("DRIFT: kimi hooks are present but not inside the managed marker block")
        return False
    log("kimi: in sync")
    return True


def hermes_paths(master: dict) -> tuple[Path, Path]:
    agent = master["agents"]["hermes"]
    return REPO_ROOT / agent["config_target"], REPO_ROOT / agent["allowlist_target"]


def install_hermes(master: dict) -> None:
    config, allowlist = hermes_paths(master)
    if not config.exists():
        log("hermes: local runtime absent, skipping")
        return
    try:
        import yaml
        data = yaml.safe_load(config.read_text()) or {}
    except Exception as exc:  # noqa: BLE001
        warn(f"hermes: cannot load runtime config: {exc}")
        return
    original_config = config.read_text()
    hooks = data.setdefault("hooks", {})
    marker = hook_marker()
    for event, entries in list(hooks.items()):
        hooks[event] = [entry for entry in entries if marker not in str(entry.get("command", ""))]
        if not hooks[event]:
            hooks.pop(event)
    commands = desired_commands(master, "hermes")
    for event, _matcher, item in commands:
        hooks.setdefault(event, []).append({"command": item["command"], "timeout": item["timeout"]})
    serialized_config = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    if serialized_config != original_config:
        backup_once(config)
        config.write_text(serialized_config)

    approvals = {"approvals": []}
    if allowlist.exists():
        try:
            approvals = json.loads(allowlist.read_text() or '{"approvals": []}')
        except json.JSONDecodeError:
            pass
    original_allowlist = allowlist.read_text() if allowlist.exists() else ""
    existing = approvals.setdefault("approvals", [])
    ours = {
        (entry.get("event"), entry.get("command")): entry
        for entry in existing
        if marker in str(entry.get("command", ""))
    }
    current = [entry for entry in existing if marker not in str(entry.get("command", ""))]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for event, _matcher, item in commands:
        current.append(
            ours.get((event, item["command"]))
            or {"approved_at": now, "approved_by": master["marker"], "command": item["command"], "event": event}
        )
    approvals["approvals"] = current
    serialized_allowlist = json.dumps(approvals, indent=2) + "\n"
    if serialized_allowlist != original_allowlist:
        backup_once(allowlist)
        allowlist.write_text(serialized_allowlist)
    log("hermes: up to date" if serialized_config == original_config and serialized_allowlist == original_allowlist else "hermes: installed into local runtime")


def uninstall_hermes(master: dict) -> None:
    config, allowlist = hermes_paths(master)
    marker = hook_marker()
    try:
        import yaml
    except ImportError:
        return
    if config.exists():
        data = yaml.safe_load(config.read_text()) or {}
        hooks = data.get("hooks") or {}
        changed = False
        for event, entries in list(hooks.items()):
            kept = [entry for entry in entries if marker not in str(entry.get("command", ""))]
            changed |= len(kept) != len(entries)
            if kept:
                hooks[event] = kept
            else:
                hooks.pop(event)
        if changed:
            config.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    if allowlist.exists():
        data = json.loads(allowlist.read_text() or '{"approvals": []}')
        kept = [entry for entry in data.get("approvals", []) if marker not in str(entry.get("command", ""))]
        if len(kept) != len(data.get("approvals", [])):
            data["approvals"] = kept
            allowlist.write_text(json.dumps(data, indent=2) + "\n")
    log("hermes: uninstalled from local runtime")


def check_hermes(master: dict) -> bool:
    config, allowlist = hermes_paths(master)
    if not config.exists():
        return True
    try:
        import yaml

        config_data = yaml.safe_load(config.read_text()) or {}
        allowlist_data = json.loads(allowlist.read_text() or '{"approvals": []}') if allowlist.exists() else {"approvals": []}
    except Exception as exc:  # noqa: BLE001
        warn(f"DRIFT: hermes hook projection could not be parsed: {exc}")
        return False
    config_commands = {
        entry.get("command")
        for entries in (config_data.get("hooks") or {}).values()
        for entry in entries
        if isinstance(entry, dict)
    }
    approved_commands = {
        entry.get("command")
        for entry in allowlist_data.get("approvals", [])
        if isinstance(entry, dict)
    }
    wanted = [item[2]["command"] for item in desired_commands(master, "hermes")]
    missing = [command for command in wanted if command not in config_commands or command not in approved_commands]
    if missing:
        warn(f"DRIFT: hermes runtime missing {len(missing)} hook projection(s)")
        return False
    log("hermes: in sync")
    return True


def check_hook_scripts(master: dict) -> bool:
    """Verify each hook actually points at something runnable.

    Every per-client check below compares wiring text to wiring text, so all
    four can report "in sync" while the single script they all invoke does not
    exist on disk. Validate the target before trusting the projection.
    """
    ok = True
    for hook in master["hooks"]:
        script = HOOK_DIR / hook["script"]
        if not script.exists():
            warn(f"DRIFT: hook script missing: {script} (hook id: {hook['id']})")
            warn("       every client's projection points at it — restore the script or drop the hook from hooks.master.json")
            ok = False
        elif not os.access(script, os.X_OK):
            warn(f"DRIFT: hook script not executable: {script} (hook id: {hook['id']})")
            ok = False
    return ok


def selected(target: str) -> list[str]:
    return ["claude", "codex", "kimi", "hermes"] if target == "all" else [target]


def main() -> int:
    global QUIET
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--install", action="store_true")
    mode.add_argument("--uninstall", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--target", choices=("all", "claude", "codex", "kimi", "hermes"), default="all")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    QUIET = args.quiet

    try:
        master = load_master()
        disabled = load_disabled_agents()
        ok = True
        if args.check:
            ok &= check_hook_scripts(master)
        for agent in selected(args.target):
            if not master["agents"][agent].get("enabled", True):
                continue
            if args.check:
                if agent in disabled:
                    continue
                ok &= {"claude": check_json, "codex": check_json, "kimi": check_kimi, "hermes": check_hermes}[agent](master, agent) if agent in {"claude", "codex"} else {"kimi": check_kimi, "hermes": check_hermes}[agent](master)
                continue
            if args.uninstall or agent in disabled:
                if agent == "claude":
                    continue
                {"codex": uninstall_json, "kimi": uninstall_kimi, "hermes": uninstall_hermes}[agent](master, agent) if agent == "codex" else {"kimi": uninstall_kimi, "hermes": uninstall_hermes}[agent](master)
                continue
            {"claude": install_json, "codex": install_json, "kimi": install_kimi, "hermes": install_hermes}[agent](master, agent) if agent in {"claude", "codex"} else {"kimi": install_kimi, "hermes": install_hermes}[agent](master)
        return 0 if ok else 1
    except Exception as exc:  # noqa: BLE001
        warn(f"{type(exc).__name__}: {exc}")
        return 1 if args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
