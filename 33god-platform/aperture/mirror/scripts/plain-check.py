#!/usr/bin/env python3
"""plain-check: prove a 33GOD Mac peer's AI apps are back to plain (33god-mode off).

The inverse of clients-check.py. Runs ON the peer (stdlib, python 3.11+ for tomllib):
    ssh <peer> '/opt/homebrew/bin/python3 -I - [--live]' < plain-check.py

Static checks: no gateway, no 33GOD hooks, no 33GOD catalog skills, no 33GOD
instructions, in every file Claude Code and Codex (CLI and Desktop) read.
--live runs one headless turn per client binary (Claude CLI, Codex CLI, the Codex
binary bundled in ChatGPT.app) and proves: the turn works on the user's own
account, the provider is not the gateway, and NOTHING about the turn reached the
33GOD bus (Candystore has zero events for the session id).
Never prints a secret value. Prints one JSON document; exit 1 if any FAIL.
"""
import json, os, re, shlex, subprocess, sys, time

HOME = os.path.expanduser("~")
LIVE = "--live" in sys.argv
OUT = []
GW = re.compile(r"automaticai|aai-gateway-token")
HOOK = re.compile(r"bb-hook|/\.agents/hooks/|hindsight|candystore|33god|hook-hub")
CATALOG = re.compile(r"code/skillex/all-skills/|/\.local/share/ego/")


def add(client, req, ok, ev):
    OUT.append({"client": client, "check": req, "status": "PASS" if ok else "FAIL", "evidence": ev})


def sh(cmd, timeout=60):
    e = dict(os.environ, PATH="/opt/homebrew/bin:/usr/local/bin:%s/.local/bin:" % HOME + os.environ.get("PATH", ""))
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, env=e, stdin=subprocess.DEVNULL)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def hooks_of(doc):
    return [h.get("command", "") for gs in (doc.get("hooks") or {}).values() for g in gs for h in g.get("hooks", [])]


import tomllib
cs = json.load(open(f"{HOME}/.claude/settings.json"))
cfg = tomllib.load(open(f"{HOME}/.codex/config.toml", "rb"))
ch = json.load(open(f"{HOME}/.codex/hooks.json"))

# ---- Claude Code
blob = json.dumps({k: cs.get(k) for k in ("apiKeyHelper", "env")})
add("claude", "no-gateway", not GW.search(blob), "apiKeyHelper=%s env keys=%s" % (cs.get("apiKeyHelper"), sorted((cs.get("env") or {}).keys())))
ours = [c for c in hooks_of(cs) if HOOK.search(c)]
add("claude", "no-33god-hooks", not ours, "33GOD hooks=%d, own hooks kept=%d" % (len(ours), len(hooks_of(cs)) - len(ours)))
local = f"{HOME}/.claude/settings.local.json"
if os.path.exists(local):
    t = open(local).read()
    add("claude", "settings.local-clean", not GW.search(t) and not HOOK.search(t), "settings.local.json has gateway/33GOD refs: %s" % bool(GW.search(t) or HOOK.search(t)))
cj = f"{HOME}/.claude.json"
if os.path.exists(cj):
    mcp = json.load(open(cj)).get("mcpServers", {}) or {}
    bad = [k for k, v in mcp.items() if GW.search(json.dumps(v)) or HOOK.search(json.dumps(v))]
    add("claude", "no-33god-mcp", not bad, "user MCP servers=%s, 33GOD ones=%s" % (sorted(mcp), bad))
md = f"{HOME}/.claude/CLAUDE.md"
t = open(md).read() if os.path.exists(md) else ""
add("claude", "no-33god-instructions", not re.search(r"33GOD|Candybar|hindsight|bloodbank|Jarad", t, re.I),
    "~/.claude/CLAUDE.md %s" % ("absent" if not t else "%d bytes" % len(t)))

# ---- Codex
add("codex", "no-gateway-provider", cfg.get("model_provider", "openai") == "openai" and not GW.search(str(cfg.get("model", ""))),
    "model_provider=%s model=%s" % (cfg.get("model_provider", "(default openai)"), cfg.get("model")))
add("codex", "no-gateway-anywhere", not GW.search(json.dumps({k: v for k, v in cfg.items() if k not in ("projects", "hooks")})),
    "gateway refs outside projects/hooks.state: %s" % bool(GW.search(json.dumps({k: v for k, v in cfg.items() if k not in ("projects", "hooks")}))))
ours = [c for c in hooks_of(ch) if HOOK.search(c)]
add("codex", "no-33god-hooks", not ours, "33GOD hooks=%d, own hooks kept=%d" % (len(ours), len(hooks_of(ch)) - len(ours)))
inline = cfg.get("hooks", {})
inl = [k for k in inline if k != "state"]
add("codex", "no-inline-hooks", not any(HOOK.search(json.dumps(inline.get(k))) for k in inl), "inline [hooks] tables: %s" % inl)
mcp = cfg.get("mcp_servers", {})
add("codex", "no-33god-mcp", not [k for k, v in mcp.items() if GW.search(json.dumps(v)) or HOOK.search(json.dumps(v))], "mcp_servers=%s" % sorted(mcp))
ag = f"{HOME}/.codex/AGENTS.md"
t = open(ag).read() if os.path.exists(ag) else ""
add("codex", "no-33god-instructions", not re.search(r"33GOD|Candybar|hindsight|bloodbank|Jarad", t, re.I),
    "~/.codex/AGENTS.md %s" % ("absent" if not t else "%d bytes" % len(t)))

# ---- Skills (Claude reads ~/.claude/skills, Codex reads ~/.codex/skills and ~/.agents/skills)
seen = {}
for d in (f"{HOME}/.claude/skills", f"{HOME}/.codex/skills", f"{HOME}/.agents/skills"):
    if not os.path.isdir(d):
        continue
    for e in os.listdir(d):
        p = os.path.join(d, e)
        tgt = os.path.realpath(p)
        seen.setdefault(e, tgt)
cat = sorted(e for e, t in seen.items() if CATALOG.search(t))
add("skills", "no-33god-catalog-skills", not cat, "skills visible=%d: %s; 33GOD catalog ones=%s" % (len(seen), sorted(seen), cat))
# the peer's own shared skills must stay visible to Claude (it reads only ~/.claude/skills)
own = sorted(e for e in os.listdir(f"{HOME}/.agents/skills") if not e.startswith(".") and e != "synced"
             and not CATALOG.search(os.path.realpath(f"{HOME}/.agents/skills/{e}"))) if os.path.isdir(f"{HOME}/.agents/skills") else []
cl = set(os.listdir(f"{HOME}/.claude/skills")) if os.path.isdir(f"{HOME}/.claude/skills") else set()
add("skills", "own-skills-visible-to-claude", all(e in cl for e in own), "own shared skills=%s, missing from ~/.claude/skills=%s" % (own, [e for e in own if e not in cl]))
st = f"{HOME}/.config/skillex/skillex.toml"
if os.path.exists(st):
    en = (tomllib.load(open(st, "rb")).get("cli", {}).get("codex", {}) or {}).get("enabled")
    add("skills", "skillex-global-sync-off", en is not True, "skillex [cli.codex] enabled=%s" % en)

# ---- projects: instructions/hooks in the user's own repos that wire agents to 33GOD
# (~/code/33GOD itself is 33GOD by definition and is skipped)
import glob
PROJ = re.compile(r"big-chungus|burro-salmon|hindsight-cli|hindsight memory (recall|retain)|bb-hook|hook-hub")
bad = []
for pat in ("code/*/AGENTS.md", "code/*/CLAUDE.md", "code/*/*/AGENTS.md", "code/*/*/CLAUDE.md",
            "code/*/.claude/settings.json", "code/*/*/.claude/settings.json", "code/*/mise.toml", "code/*/*/mise.toml"):
    for f in glob.glob(os.path.join(HOME, pat)):
        if "/code/33GOD/" in f or "/node_modules/" in f:
            continue
        try:
            t = open(f, errors="ignore").read()
        except OSError:
            continue
        hit = PROJ.search(t) or (f.endswith("settings.json") and re.search(r"hindsight|candystore|33god|bb-hook|hook-hub", t))
        if hit:
            bad.append("%s (%s)" % (f.replace(HOME, "~"), hit.group(0)))
add("projects", "no-33god-project-wiring", not bad, "project files wiring agents to 33GOD: %s" % (sorted(set(bad)) or "none"))

# ---- git: guards off, but the passive global ignore list stays (git-checkpoint runs `git add -A`)
rc, hp = sh("git config --global --get core.hooksPath")
add("git", "no-33god-git-guards", not hp.strip(), "core.hooksPath=%s" % (hp.strip() or "(unset)"))
rc, ex = sh("git config --global --get core.excludesFile")
xdg = os.path.exists(f"{HOME}/.config/git/ignore")
add("git", "global-ignore-present", bool(ex.strip()) or xdg, "core.excludesFile=%s, ~/.config/git/ignore=%s" % (ex.strip() or "(unset)", xdg))

# ---- live turns
if LIVE:
    def cs_count(sid):
        q = "select count(*) from events where raw::text like '%%%s%%'" % sid
        rc, o = sh("docker --context colima exec candystore-postgres sh -c 'psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -At -c \"%s\"'" % q.replace("'", "'\"'\"'"), timeout=60)
        return o.strip() if rc == 0 else "query-error: " + o.strip()[:120]

    d = "/tmp/plain-check"
    os.makedirs(d, exist_ok=True)
    # run it the way the user does: an interactive terminal (zsh -i loads ~/.zshrc, where the login lives)
    inner = "claude -p 'Run pwd with the Bash tool then reply exactly PLAIN-OK-CLAUDE' --output-format stream-json --verbose"
    rc, out = sh("cd %s && timeout 170 zsh -ic %s </dev/null" % (d, shlex.quote(inner)), timeout=200)
    sid = src = None; models = []; txt = ""; err = True
    for line in out.splitlines():
        try:
            m = json.loads(line)
        except Exception:
            continue
        if m.get("type") == "system" and m.get("subtype") == "init":
            sid, src = m.get("session_id"), m.get("apiKeySource")
        if m.get("type") == "result":
            err, txt, models = m.get("is_error"), m.get("result", ""), list((m.get("modelUsage") or {}).keys())
    time.sleep(8)
    n = cs_count(sid) if sid else "n/a"
    add("claude", "live-turn-plain", bool(sid) and not err and "PLAIN-OK-CLAUDE" in txt and src != "apiKeyHelper"
        and not any(GW.search(x) for x in models),
        "session=%s apiKeySource=%s models=%s reply=%r" % (sid, src, models, txt[:30]))
    add("claude", "live-turn-not-on-bus", n == "0", "candystore events for session: %s" % n)

    for label, binpath in (("codex-cli", "/opt/homebrew/bin/codex"),
                           ("codex-desktop", "/Applications/ChatGPT.app/Contents/Resources/codex")):
        if not os.path.exists(binpath):
            rc, w = sh("find /Applications/ChatGPT.app -name codex -type f -perm -u+x | head -1")
            binpath = w.strip() or binpath
        rc, out = sh("cd %s && timeout 240 '%s' exec --json --skip-git-repo-check 'Run pwd then reply exactly PLAIN-OK-%s'" % (d, binpath, label.upper()), timeout=260)
        tid, reply, failed = None, "", False
        for line in out.splitlines():
            try:
                m = json.loads(line)
            except Exception:
                continue
            if m.get("type") == "thread.started":
                tid = m.get("thread_id")
            if m.get("type") == "item.completed" and m["item"].get("type") == "agent_message":
                reply = m["item"].get("text", "")
            if m.get("type") in ("turn.failed", "error"):
                failed = True
        prov = "unknown"
        if tid:
            rc, f = sh("grep -rl '%s' %s/.codex/sessions 2>/dev/null | head -1" % (tid, HOME))
            if f.strip():
                try:
                    meta = json.loads(open(f.strip()).readline())
                    prov = meta.get("payload", {}).get("model_provider", "unknown")
                except Exception:
                    pass
        time.sleep(8)
        n = cs_count(tid) if tid else "n/a"
        add(label, "live-turn-plain", bool(tid) and not failed and ("PLAIN-OK-" + label.upper()) in reply and prov != "automaticai",
            "binary=%s thread=%s provider=%s failed=%s reply=%r" % (binpath, tid, prov, failed, reply[:30]))
        add(label, "live-turn-not-on-bus", n == "0", "candystore events for thread: %s" % n)

print(json.dumps({"host": os.uname().nodename, "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "live": LIVE, "checks": OUT}, indent=1))
sys.exit(1 if any(c["status"] == "FAIL" for c in OUT) else 0)
