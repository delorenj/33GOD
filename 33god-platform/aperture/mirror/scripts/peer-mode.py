#!/opt/homebrew/bin/python3
"""33god-mode: switch this Mac's AI apps between plain and 33GOD.

  33god-mode            show which mode each part is in
  33god-mode off        plain: Claude Code and Codex (CLI and Desktop) run on your own
                        accounts, with no 33GOD hooks, skills, instructions or gateway
  33god-mode on         put the 33GOD setup back exactly as it was
  33god-mode status --json

Built one abstraction level up (belsky-doctrine): Jarad asked for Damian's Mac; this
is the switch for every 33GOD Mac peer. The 33GOD services (hook-hub, Candystore,
Candybar, Hindsight, the pjangler registry, Hermes, Postgres) keep running in both
modes. "off" only cuts the apps loose from them, so flipping back is instant.

What "off" changes, and nothing else:
  ~/.claude/settings.json   drops apiKeyHelper, the gateway env keys, every 33GOD hook
  ~/.codex/config.toml      drops the AutomaticAI provider and its model/catalog/subagent
                            keys, the gateway env Codex hands to child shells, and the
                            33GOD escape-hatch profile; puts your own model back
  ~/.codex/hooks.json       drops every 33GOD hook
  CLAUDE.md / AGENTS.md     drops the 33GOD-injected <!-- name:start/end --> blocks
                            (~/.claude/CLAUDE.md, ~/.codex/AGENTS.md, ~/AGENTS.md)
  ~/.claude/skills, ~/.codex/skills
                            the links into the shared 33GOD folder become plain folders
  ~/.agents/skills and ~/code/*/.agents/skills
                            parks every 33GOD catalog skill (moved, never deleted)
  ~/.gitconfig              drops core.hooksPath when it points at the 33GOD git guards.
                            core.excludesFile (a passive ignore list) stays: without it
                            your own git-checkpoint hook would commit node_modules,
                            worktrees and .env files
  skillex                   turns off its Codex global sync, so a stray `skillex sync`
                            cannot re-link the catalog while plain
Your own entries (git-checkpoint hooks, lamp MCP, ChatGPT plugins, your commands and
your own skills, trusted projects, your CLAUDE.md sections and your own
<!-- name:start/end --> blocks) are never touched. Your own skills in the shared
folder stay visible to Claude through links in ~/.claude/skills.

Every switch copies each file it changes to
~/.config/33god/config-backups/<stamp>-33god-mode-before-<mode>/ first. What "off"
removed is kept in ~/.config/33god/mode/ (parked.json, parked-skills/), and "on" puts
exactly that back, merged with anything you changed in between.
Quit and reopen Claude and Codex (ChatGPT app: Cmd+Q) after a switch.

Exit: 0 ok, 1 refused or failed, 2 usage.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

H = Path.home()
E = os.environ.get
CLAUDE_SETTINGS = Path(E("PEER_CLAUDE_SETTINGS", H / ".claude/settings.json"))
CODEX_HOME = Path(E("CODEX_HOME", H / ".codex"))
CODEX_CFG = CODEX_HOME / "config.toml"
CODEX_HOOKS = CODEX_HOME / "hooks.json"
AGENTS_HOME = Path(E("PEER_AGENTS_HOME", H / ".agents"))
STATE = Path(E("PEER_MODE_DIR", H / ".config/33god/mode"))
PARKED = STATE / "parked.json"
PARKED_SKILLS = STATE / "parked-skills"
BACKUPS = Path(E("PEER_MODE_BACKUPS", H / ".config/33god/config-backups"))
DOCS = [Path(p) for p in E("PEER_DOCS", f"{H}/.claude/CLAUDE.md:{CODEX_HOME}/AGENTS.md:{H}/AGENTS.md").split(":")]
APP_SKILL_DIRS = [Path(p) for p in E("PEER_APP_SKILL_DIRS", f"{H}/.claude/skills:{CODEX_HOME}/skills").split(":")]
SKILL_DIR_GLOBS = E("PEER_SKILL_DIRS", f"{AGENTS_HOME}/skills:{H}/code/*/.agents/skills:{H}/code/*/*/.agents/skills").split(":")
SKILL_LOCK = AGENTS_HOME / ".skill-lock.json"

HOOK_RE = re.compile(E("PEER_HOOK_RE", r"bb-hook|/\.agents/hooks/|hindsight|candystore|33god|hook-hub"))
SKILL_LINK_RE = re.compile(E("PEER_SKILL_LINK_RE", r"skillex/all-skills/|/\.local/share/ego/"))
GATEWAY_RE = re.compile(r"automaticai|aai-gateway-token")
BLOCK_RE = re.compile(r"\n*<!-- ([A-Za-z0-9_.:-]+):start -->\n.*?<!-- \1:end -->\n?", re.S)
# Only blocks 33GOD owns are parked; a peer's own blocks (e.g. damian:breadth-first) stay.
OWN_BLOCK_RE = re.compile(E("PEER_BLOCK_RE", r"^(agents:|delegate-to-|33god|hindsight|candybar|candystore|bloodbank|hermes)"))
# App skill folders that do NOT read the shared ~/.agents/skills themselves (Codex does),
# so the peer's own skills there are linked in while plain.
MIRROR_SKILL_DIRS = [Path(p) for p in E("PEER_MIRROR_SKILL_DIRS", f"{H}/.claude/skills").split(":") if p]
SKILLEX_TOML = Path(E("PEER_SKILLEX_TOML", H / ".config/skillex/skillex.toml"))
CLAUDE_GW_ENV = {
    "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL", "CLAUDE_CODE_MAX_CONTEXT_TOKENS",
    "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY",
    "CLAUDE_CODE_GATEWAY_MODEL_DISCOVERY_TIMEOUT_MS", "API_TIMEOUT_MS",
}
CODEX_PLAIN_MODEL = E("PEER_CODEX_MODEL", "gpt-6.1-terra")
# Tables 33GOD adds to config.toml. shell_environment_policy is 33GOD's only when its
# .set carries the gateway (Codex Desktop imported it from the gateway Claude settings).
CODEX_GW_TABLES_RE = re.compile(r"^(model_providers\.automaticai(\..*)?|profiles\.openai-direct)$")
GIT_KEYS = ("core.hooksPath",)


# ================================================================ helpers
def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except FileNotFoundError:
        return default


def atomic_write(p, text, mode=None):
    p = Path(p)
    tmp = p.with_name(p.name + ".33god-mode-tmp")
    tmp.write_text(text)
    if mode is None and p.exists():
        mode = p.stat().st_mode & 0o777
    if mode is not None:
        os.chmod(tmp, mode)
    tmp.replace(p)


def dumpj(d):
    return json.dumps(d, indent=2) + "\n"


def lexists(p):
    return os.path.lexists(p)


# ================================================================ hooks (Claude + Codex JSON)
def split_hooks(hooks):
    """(kept, removed); a group mixing 33GOD and your hooks keeps yours."""
    kept, removed = {}, {}
    for event, groups in (hooks or {}).items():
        for g in groups:
            inner = g.get("hooks", [])
            ours = [h for h in inner if HOOK_RE.search(h.get("command", ""))]
            mine = [h for h in inner if not HOOK_RE.search(h.get("command", ""))]
            if ours:
                removed.setdefault(event, []).append({**g, "hooks": ours})
            if mine:
                kept.setdefault(event, []).append({**g, "hooks": mine})
    return kept, removed


def merge_hooks(hooks, add):
    hooks = json.loads(json.dumps(hooks or {}))
    for event, groups in (add or {}).items():
        have = hooks.setdefault(event, [])
        cmds = {h.get("command") for g in have for h in g.get("hooks", [])}
        for g in groups:
            new = [h for h in g.get("hooks", []) if h.get("command") not in cmds]
            if new:
                have.append({**g, "hooks": new})
    return hooks


def park_hooks(slot, hooks):
    kept, removed = split_hooks(hooks)
    if removed:
        slot["hooks"] = merge_hooks(slot.get("hooks"), removed)
        slot["hooks_full"], slot["hooks_left"] = hooks, kept
    return kept, removed


def unpark_hooks(slot, hooks):
    # unchanged since "off": the exact original (same order keeps Codex's per-index trust hashes valid)
    if slot.get("hooks_full") is not None and hooks == slot.get("hooks_left"):
        return slot["hooks_full"]
    return merge_hooks(hooks, slot.get("hooks"))


def count_hooks(hooks, ours=True):
    return sum(1 for gs in (hooks or {}).values() for g in gs for h in g.get("hooks", [])
               if bool(HOOK_RE.search(h.get("command", ""))) == ours)


# ================================================================ Codex config.toml text surgery
TABLE_RE = re.compile(r"^\s*\[\[?\s*([^\]]+?)\s*\]\]?\s*(#.*)?$")
KEY_RE = re.compile(r"^\s*([A-Za-z0-9_\-\"\.]+)\s*=")


def toml_sections(text):
    out, cur, buf = [], None, []
    for line in text.splitlines(keepends=True):
        m = TABLE_RE.match(line)
        if m and not line.lstrip().startswith("#"):
            out.append((cur, buf))
            cur, buf = m.group(1).strip(), [line]
        else:
            buf.append(line)
    out.append((cur, buf))
    return out


def pull_key(lines, key):
    out, got = [], None
    for line in lines:
        m = KEY_RE.match(line)
        if got is None and m and m.group(1).strip('"') == key:
            got = line
            continue
        out.append(line)
    return out, got


def first_key_at(lines):
    return next((i for i, l in enumerate(lines) if KEY_RE.match(l)), len(lines))


def codex_off(text):
    parked = {"top": {}, "keys": {}, "tables": []}
    cfg = tomllib.loads(text)
    sep_gw = GATEWAY_RE.search(json.dumps(cfg.get("shell_environment_policy", {}).get("set", {})))
    new = []
    for name, lines in toml_sections(text):
        if name is None:
            if cfg.get("model_provider") == "automaticai" or GATEWAY_RE.search(str(cfg.get("model", ""))):
                for k in ("model_provider", "model", "model_catalog_json"):
                    lines, got = pull_key(lines, k)
                    if got:
                        parked["top"][k] = got
                lines.insert(first_key_at(lines), f'model = "{CODEX_PLAIN_MODEL}"\n')
            new.append((name, lines))
        elif CODEX_GW_TABLES_RE.match(name) or (sep_gw and name in ("shell_environment_policy", "shell_environment_policy.set")):
            parked["tables"].append("".join(lines))
        elif name == "agents":
            lines2, got = pull_key(lines, "default_subagent_model")
            if got and GATEWAY_RE.search(got):
                parked["keys"].setdefault(name, []).append(got)
                lines = lines2
            new.append((name, lines))
        else:
            new.append((name, lines))
    return "".join("".join(b) for _, b in new), parked


def codex_on(text, parked):
    if parked.get("full") is not None and text == parked.get("left"):
        return parked["full"]
    secs = toml_sections(text)
    have = {n for n, _ in secs}
    new = []
    for name, lines in secs:
        if name is None and parked.get("top"):
            for k in ("model_provider", "model", "model_catalog_json"):
                lines, _ = pull_key(lines, k)
            at = first_key_at(lines)
            for k in ("model_catalog_json", "model", "model_provider"):
                if k in parked["top"]:
                    lines.insert(at, parked["top"][k])
        if name in parked.get("keys", {}):
            for kl in reversed(parked["keys"][name]):
                lines, _ = pull_key(lines, KEY_RE.match(kl).group(1))
                lines.insert(1, kl)
        new.append((name, lines))
    out = "".join("".join(b) for _, b in new)
    for name, kls in parked.get("keys", {}).items():
        if name not in have:
            out = out.rstrip("\n") + f"\n\n[{name}]\n" + "".join(kls)
    for t in parked.get("tables", []):
        tname = TABLE_RE.match(t.splitlines()[0]).group(1).strip()
        if tname not in have:
            out = out.rstrip("\n") + "\n\n" + t.rstrip("\n") + "\n"
    return out


# ================================================================ skills
def skill_dirs():
    out = []
    for g in SKILL_DIR_GLOBS:
        for d in sorted(glob.glob(g)):
            p = Path(d)
            if p.is_dir() and not p.is_symlink():
                out.append(p)
    seen, uniq = set(), []
    for p in out:
        r = os.path.realpath(p)
        if r not in seen:
            seen.add(r)
            uniq.append(p)
    return uniq


def locked_names():
    d = read_json(SKILL_LOCK, {}) or {}
    s = d.get("skills", {})
    return set(s) if isinstance(s, dict) else set()


def is_33god_skill(entry, lock, agents_skills):
    if entry.name.startswith("."):
        return False
    if entry.is_symlink():
        t = os.readlink(entry)
        return bool(SKILL_LINK_RE.search(t) or SKILL_LINK_RE.search(os.path.realpath(entry)))
    # real folders delivered by the 33GOD ~/.agents copy are named in its committed lock file
    return entry.is_dir() and agents_skills and entry.name in lock


def scan_skills():
    lock = locked_names()
    agents = os.path.realpath(AGENTS_HOME / "skills")
    res = []
    for d in skill_dirs():
        is_agents = os.path.realpath(d) == agents
        for e in sorted(d.iterdir()):
            res.append((d, e, is_33god_skill(e, lock, is_agents)))
    return res


def slot_name(d):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(Path(d).relative_to(H)) if str(d).startswith(str(H)) else str(d)).strip("_")


def park_skills(parked):
    rec = parked.setdefault("skills", [])
    n = 0
    for d, e, ours in scan_skills():
        if not ours:
            continue
        item = {"dir": str(d), "name": e.name}
        if e.is_symlink():
            item.update(kind="link", target=os.readlink(e))
            e.unlink()
        else:
            dst = PARKED_SKILLS / slot_name(d) / e.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if lexists(dst):
                shutil.rmtree(dst) if dst.is_dir() and not dst.is_symlink() else dst.unlink()
            shutil.move(str(e), dst)
            item.update(kind="dir", parked=str(dst))
        rec.append(item)
        n += 1
    return n


def unpark_skills(parked):
    n = 0
    for item in parked.get("skills", []):
        dst = Path(item["dir"]) / item["name"]
        if lexists(dst):
            continue  # you re-added it while plain; yours wins
        if not Path(item["dir"]).is_dir():
            continue
        if item["kind"] == "link":
            os.symlink(item["target"], dst)
        elif Path(item["parked"]).exists():
            shutil.move(item["parked"], dst)
        n += 1
    return n


def app_skill_dirs_off(parked):
    rec = parked.setdefault("app_skill_dirs", {})
    shared = AGENTS_HOME / "skills"
    lock = locked_names()
    for p in APP_SKILL_DIRS:
        if p.is_symlink() and os.path.realpath(p) == os.path.realpath(shared):
            rec[str(p)] = os.readlink(p)
            p.unlink()
            p.mkdir()
    # keep the peer's own shared skills visible to apps that only read their own folder
    for p in MIRROR_SKILL_DIRS:
        if str(p) in rec and p.is_dir() and not p.is_symlink() and shared.is_dir():
            for e in sorted(shared.iterdir()):
                if not e.name.startswith(".") and not is_33god_skill(e, lock, True) and not lexists(p / e.name):
                    os.symlink(e, p / e.name)
    return list(rec)


def app_skill_dirs_on(parked, stamp):
    out = []
    for path, target in parked.get("app_skill_dirs", {}).items():
        p = Path(path)
        if p.is_dir() and not p.is_symlink():
            shared = os.path.realpath(AGENTS_HOME / "skills")
            extra = [e for e in p.iterdir() if e.name != ".system"
                     and not (e.is_symlink() and os.path.realpath(e).startswith(shared + os.sep))]
            if extra:
                keep = p.with_name(p.name + f".plain-{stamp}")
                shutil.move(str(p), keep)
                print(f"  note: skills you added to {p} while plain are kept at {keep}")
            else:
                shutil.rmtree(p)
        if not lexists(p):
            os.symlink(target, p)
            out.append(path)
    return out


# ================================================================ instruction files
def docs_off(parked):
    rec = parked.setdefault("docs", {})
    out = []
    for p in DOCS:
        if not p.is_file():
            continue
        text = p.read_text()
        blocks = [m.group(0) for m in BLOCK_RE.finditer(text) if OWN_BLOCK_RE.search(m.group(1))]
        if not blocks:
            continue
        left = BLOCK_RE.sub(lambda m: "\n" if OWN_BLOCK_RE.search(m.group(1)) else m.group(0), text).rstrip("\n") + "\n"
        rec[str(p)] = {"full": text, "left": left, "blocks": blocks}
        atomic_write(p, left)
        out.append(str(p))
    return out


def docs_on(parked):
    out = []
    for path, r in parked.get("docs", {}).items():
        p = Path(path)
        if not p.exists():
            continue
        text = p.read_text()
        if text == r["left"]:
            new = r["full"]
        else:
            new = text.rstrip("\n") + "\n"
            for b in r["blocks"]:
                name = BLOCK_RE.match(b).group(1)
                if f"<!-- {name}:start -->" not in new:
                    new += "\n" + b.strip("\n") + "\n"
        atomic_write(p, new)
        out.append(path)
    return out


# ================================================================ git guards
def git(*a):
    p = subprocess.run(["git", "config", "--global", *a], capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


def git_off(parked):
    rec = parked.setdefault("git", {})
    agents = os.path.realpath(AGENTS_HOME)
    for k in GIT_KEYS:
        rc, v = git("--get", k)
        if rc == 0 and v and os.path.realpath(os.path.expanduser(v)).startswith(agents):
            rec[k] = v
            git("--unset", k)
    return list(rec)


def git_on(parked):
    out = []
    for k, v in parked.get("git", {}).items():
        rc, cur = git("--get", k)
        if rc != 0 or not cur:
            git(k, v)
            out.append(k)
    return out


# ================================================================ skillex global sync
SKX_RE = re.compile(r"^(\s*enabled\s*=\s*)(true|false)(.*)$")


def skillex_codex(text, want):
    """Flip [cli.codex] enabled; returns (new_text, old_value or None)."""
    out, cur, old = [], None, None
    for line in text.splitlines(keepends=True):
        m = TABLE_RE.match(line)
        if m and not line.lstrip().startswith("#"):
            cur = m.group(1).strip()
        elif cur == "cli.codex" and old is None and SKX_RE.match(line.rstrip("\n")):
            mm = SKX_RE.match(line.rstrip("\n"))
            old = mm.group(2)
            line = f"{mm.group(1)}{want}{mm.group(3)}" + ("\n" if line.endswith("\n") else "")
        out.append(line)
    return "".join(out), old


def skillex_off(parked):
    if not SKILLEX_TOML.is_file():
        return []
    text = SKILLEX_TOML.read_text()
    root = (tomllib.loads(text).get("cli", {}).get("codex", {}) or {})
    if root.get("enabled") is not True or not os.path.realpath(os.path.expanduser(str(root.get("global_root", "")))).startswith(os.path.realpath(AGENTS_HOME)):
        return []
    new, old = skillex_codex(text, "false")
    if old != "true":
        return []
    parked["skillex"] = {"path": str(SKILLEX_TOML), "full": text, "left": new}
    atomic_write(SKILLEX_TOML, new)
    return [str(SKILLEX_TOML)]


def skillex_on(parked):
    r = parked.get("skillex")
    if not r or not Path(r["path"]).is_file():
        return []
    text = Path(r["path"]).read_text()
    new = r["full"] if text == r["left"] else skillex_codex(text, "true")[0]
    atomic_write(r["path"], new)
    return [r["path"]]


def skillex_state():
    try:
        return (tomllib.loads(SKILLEX_TOML.read_text()).get("cli", {}).get("codex", {}) or {}).get("enabled")
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return None


# ================================================================ status
def status():
    s = {}
    c = read_json(CLAUDE_SETTINGS, {}) or {}
    s["claude.gateway"] = bool(GATEWAY_RE.search(json.dumps({k: c.get(k) for k in ("apiKeyHelper", "env")})))
    s["claude.33god_hooks"] = count_hooks(c.get("hooks"))
    s["claude.own_hooks"] = count_hooks(c.get("hooks"), ours=False)
    s["claude.login"] = ("env CLAUDE_CODE_OAUTH_TOKEN" if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
                         else "gateway apiKeyHelper" if s["claude.gateway"] else "keychain or none (run /login if Claude asks)")
    try:
        cfg = tomllib.loads(CODEX_CFG.read_text())
    except FileNotFoundError:
        cfg = {}
    s["codex.provider"] = cfg.get("model_provider", "openai")
    s["codex.model"] = cfg.get("model")
    s["codex.gateway_env"] = bool(GATEWAY_RE.search(json.dumps(cfg.get("shell_environment_policy", {}))))
    ch = read_json(CODEX_HOOKS, {}) or {}
    s["codex.33god_hooks"] = count_hooks(ch.get("hooks"))
    s["codex.own_hooks"] = count_hooks(ch.get("hooks"), ours=False)
    ours = mine = 0
    for _, e, o in scan_skills():
        if e.name.startswith("."):
            continue
        ours, mine = (ours + 1, mine) if o else (ours, mine + 1)
    s["skills.33god_live"], s["skills.own"] = ours, mine
    s["skills.app_dirs_linked"] = [str(p) for p in APP_SKILL_DIRS
                                   if p.is_symlink() and os.path.realpath(p) == os.path.realpath(AGENTS_HOME / "skills")]
    s["docs.33god_blocks"] = {str(p): b for p in DOCS if p.is_file()
                              for b in [[m.group(1) for m in BLOCK_RE.finditer(p.read_text()) if OWN_BLOCK_RE.search(m.group(1))]] if b}
    s["skillex.codex_global_sync"] = skillex_state()
    s["git.guards"] = {k: v for k in GIT_KEYS for rc, v in [git("--get", k)]
                       if rc == 0 and os.path.realpath(os.path.expanduser(v)).startswith(os.path.realpath(AGENTS_HOME))}
    flags = [s["claude.gateway"], s["claude.33god_hooks"] > 0, s["codex.provider"] == "automaticai",
             s["codex.gateway_env"], s["codex.33god_hooks"] > 0, s["skills.33god_live"] > 0,
             bool(s["skills.app_dirs_linked"]), bool(s["docs.33god_blocks"]), bool(s["git.guards"])]
    s["mode"] = "on" if all(flags) else ("off" if not any(flags) else "mixed")
    s["last_switch"] = read_json(STATE / "state.json", {}) or {}
    return s


def show(s):
    word = {"on": "33GOD is ON", "off": "33GOD is OFF (plain)", "mixed": "MIXED (part on, part off)"}
    print(word[s["mode"]])
    print(f"  Claude Code : gateway {'yes' if s['claude.gateway'] else 'no'}, 33GOD hooks {s['claude.33god_hooks']}, "
          f"your hooks {s['claude.own_hooks']}; login: {s['claude.login']}")
    print(f"  Codex       : provider {s['codex.provider']} (model {s['codex.model']}), gateway env "
          f"{'yes' if s['codex.gateway_env'] else 'no'}, 33GOD hooks {s['codex.33god_hooks']}, your hooks {s['codex.own_hooks']}")
    print(f"  Skills      : 33GOD {s['skills.33god_live']} live, yours {s['skills.own']}; "
          f"app folders linked to the shared folder: {len(s['skills.app_dirs_linked'])}")
    print(f"  Instructions: 33GOD blocks in {len(s['docs.33god_blocks'])} file(s)")
    print(f"  Git guards  : {'on' if s['git.guards'] else 'off'}")
    if s["skillex.codex_global_sync"] is not None:
        print(f"  skillex     : Codex global sync {'on' if s['skillex.codex_global_sync'] else 'off'}")
    if s["last_switch"]:
        print(f"  Last switch : {s['last_switch'].get('mode')} at {s['last_switch'].get('at')}")


# ================================================================ switch
def backup(want, stamp):
    d = BACKUPS / f"{stamp}-33god-mode-before-{want}"
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    files = [CLAUDE_SETTINGS, CODEX_CFG, CODEX_HOOKS, H / ".gitconfig", SKILLEX_TOML, *DOCS]
    for p in files:
        if p.is_file():
            shutil.copy2(p, d / re.sub(r"[^A-Za-z0-9._-]+", "_", str(p.relative_to(H))).strip("_"))
    lines = [f"{e} -> {os.readlink(e) if e.is_symlink() else '(dir)'}  [{'33god' if o else 'yours'}]"
             for _, e, o in scan_skills()]
    lines += [f"{p} -> {os.readlink(p) if p.is_symlink() else '(dir)'}" for p in APP_SKILL_DIRS if lexists(p)]
    (d / "skills-listing.txt").write_text("\n".join(lines) + "\n")
    return d


def go_off(parked):
    did = []
    c = read_json(CLAUDE_SETTINGS)
    if c is not None:
        pc = parked.setdefault("claude", {})
        if "apiKeyHelper" in c and GATEWAY_RE.search(c["apiKeyHelper"]):
            pc["apiKeyHelper"] = c.pop("apiKeyHelper")
        env = c.get("env", {})
        if GATEWAY_RE.search(env.get("ANTHROPIC_BASE_URL", "")):
            pc["env"] = {k: env.pop(k) for k in list(env) if k in CLAUDE_GW_ENV}
        if "env" in c and not env:
            c.pop("env")
        kept, removed = park_hooks(pc, c.get("hooks"))
        if removed:
            c["hooks"] = kept
        atomic_write(PARKED, dumpj(parked), 0o600)
        atomic_write(CLAUDE_SETTINGS, dumpj(c))
        did.append("claude settings")
    if CODEX_CFG.exists():
        text = CODEX_CFG.read_text()
        new, pk = codex_off(text)
        if pk["top"] or pk["keys"] or pk["tables"]:
            if tomllib.loads(new).get("model_provider", "openai") != "openai":
                raise SystemExit("codex switch did not take; nothing written for codex")
            pk["full"], pk["left"] = text, new
            parked["codex"] = pk
            atomic_write(PARKED, dumpj(parked), 0o600)
            atomic_write(CODEX_CFG, new)
            did.append("codex config")
    ch = read_json(CODEX_HOOKS)
    if ch is not None:
        kept, removed = park_hooks(parked.setdefault("codex_hooks", {}), ch.get("hooks"))
        if removed:
            ch["hooks"] = kept
            atomic_write(PARKED, dumpj(parked), 0o600)
            atomic_write(CODEX_HOOKS, dumpj(ch))
            did.append("codex hooks")
    for step, fn in (("instructions", docs_off), ("app skill folders", app_skill_dirs_off),
                     ("skills", park_skills), ("git guards", git_off), ("skillex sync", skillex_off)):
        r = fn(parked)
        atomic_write(PARKED, dumpj(parked), 0o600)
        if r:
            did.append(f"{step} ({r if isinstance(r, int) else len(r)})")
    return did


def go_on(parked, stamp):
    did = []
    c = read_json(CLAUDE_SETTINGS)
    pc = parked.get("claude", {})
    if c is not None and pc:
        if "apiKeyHelper" in pc:
            c["apiKeyHelper"] = pc["apiKeyHelper"]
        if pc.get("env"):
            c["env"] = {**c.get("env", {}), **pc["env"]}
        if pc.get("hooks"):
            c["hooks"] = unpark_hooks(pc, c.get("hooks"))
        atomic_write(CLAUDE_SETTINGS, dumpj(c))
        did.append("claude settings")
    if CODEX_CFG.exists() and parked.get("codex"):
        new = codex_on(CODEX_CFG.read_text(), parked["codex"])
        tomllib.loads(new)
        atomic_write(CODEX_CFG, new)
        did.append("codex config")
    ch = read_json(CODEX_HOOKS)
    if ch is not None and parked.get("codex_hooks", {}).get("hooks"):
        ch["hooks"] = unpark_hooks(parked["codex_hooks"], ch.get("hooks"))
        atomic_write(CODEX_HOOKS, dumpj(ch))
        did.append("codex hooks")
    for step, r in (("instructions", docs_on(parked)), ("app skill folders", app_skill_dirs_on(parked, stamp)),
                    ("skills", unpark_skills(parked)), ("git guards", git_on(parked)),
                    ("skillex sync", skillex_on(parked))):
        if r:
            did.append(f"{step} ({r if isinstance(r, int) else len(r)})")
    return did


def main():
    args = sys.argv[1:] or ["status"]
    want = args[0]
    if want in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if want == "status":
        s = status()
        print(json.dumps(s, indent=2)) if "--json" in args else show(s)
        return 0
    if want not in ("on", "off"):
        print("say: 33god-mode on | 33god-mode off | 33god-mode status", file=sys.stderr)
        return 2
    before = status()
    if before["mode"] == want:
        print(f"Already {want}. Nothing changed.")
        show(before)
        return 0
    STATE.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    bdir = backup(want, stamp)
    parked = read_json(PARKED, {}) or {}
    if want == "off":
        did = go_off(parked)
    else:
        did = go_on(parked, stamp)
        shutil.move(str(PARKED), STATE / f"parked.{stamp}.restored.json") if PARKED.exists() else None
    atomic_write(STATE / "state.json", dumpj({"mode": want, "at": stamp, "backup": str(bdir), "changed": did}), 0o600)
    print(f"33GOD is now {want.upper()}. Changed: {', '.join(did) or 'nothing'}.")
    print(f"Backup: {bdir}")
    print("Now quit Claude and Codex (ChatGPT app: Cmd+Q) and open them again.")
    after = status()
    show(after)
    return 0 if after["mode"] == want else 1


if __name__ == "__main__":
    sys.exit(main())
