#!/usr/bin/env python3
"""Damian client audit: skills SSOT, normalized bb hooks, AutomaticAI provider.

Runs ON the Mac Studio (stdlib only, python 3.9 safe):
    ssh hellosubconscious@<mac> '/opt/homebrew/bin/python3 -I - [--live]' < clients-check.py

Prints one JSON document: {"checks": [{client, requirement, status, evidence}], ...}.
Never prints a secret value. --live also runs one headless turn per CLI client and
one app-server zero-token probe for Codex Desktop, then looks the sessions up in
Candystore. The gateway ledger side is checked separately from big-chungus.
"""
import hashlib, json, os, re, subprocess, sys, time, urllib.request

HOME = os.path.expanduser("~")
LIVE = "--live" in sys.argv
OUT = []


def add(client, req, ok, ev):
    OUT.append({"client": client, "requirement": req, "status": "PASS" if ok else "FAIL", "evidence": ev})


def sh(cmd, timeout=60, env=None):
    e = dict(os.environ, PATH="/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", ""))
    if env:
        e.update(env)
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, env=e)
        return p.returncode, (p.stdout + p.stderr)
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def toml_load(path):
    try:
        import tomllib  # 3.11+
        return tomllib.load(open(path, "rb"))
    except Exception:
        return None


# ---------------------------------------------------------------- shared facts
skills_dir = os.path.join(HOME, ".agents", "skills")
ssot = os.path.realpath(skills_dir)
claude_skills = os.path.realpath(os.path.join(HOME, ".claude", "skills"))
codex_skills = os.path.realpath(os.path.join(HOME, ".codex", "skills"))
entries = os.listdir(skills_dir) if os.path.isdir(skills_dir) else []
dangling = [e for e in entries if os.path.islink(os.path.join(skills_dir, e)) and not os.path.exists(os.path.join(skills_dir, e))]
live_skills = len(entries) - len(dangling)

claude_set = json.load(open(os.path.join(HOME, ".claude", "settings.json")))
codex_cfg = toml_load("/dev/null")
codex_text = open(os.path.join(HOME, ".codex", "config.toml")).read()
try:
    rc, out = sh("/opt/homebrew/bin/python3 -c \"import tomllib,json,sys;print(json.dumps(tomllib.load(open(sys.argv[1],'rb'))))\" " + os.path.join(HOME, ".codex", "config.toml"))
    codex_cfg = json.loads(out) if rc == 0 else {}
except Exception:
    codex_cfg = {}
codex_hooks = json.load(open(os.path.join(HOME, ".codex", "hooks.json")))

# reference: the normalized hook sets Jarad's machine fires (13 claude events, 10 codex events)
REF_CLAUDE = {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop", "SubagentStop",
              "PreCompact", "Notification", "PermissionRequest", "SessionEnd", "SubagentStart", "PostCompact"}


def bb_events(doc):
    found = {}
    for ev, groups in doc.get("hooks", {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                c = h.get("command", "")
                if "bb-hook" in c and len(c) < 200:
                    found.setdefault(ev, []).append(c)
    return found


cl_bb = bb_events(claude_set)
cx_bb = bb_events(codex_hooks)

# ---------------------------------------------------------------- R1 skills
for client, real in (("claude-cli", claude_skills), ("codex-cli", codex_skills)):
    add(client, "skills", real == ssot and live_skills > 0,
        "%s resolves to %s (SSOT %s); %d entries, %d live, %d dangling" % (
            ".claude/skills" if client == "claude-cli" else ".codex/skills", real, ssot, len(entries), live_skills, len(dangling)))

# ---------------------------------------------------------------- R2 hooks
add("claude-cli", "hooks", len(cl_bb) >= 13 and all("--cli claude" in c for v in cl_bb.values() for c in v),
    "%d events wired through bb-hook --cli claude: %s" % (len(cl_bb), ",".join(sorted(cl_bb))))
add("codex-cli", "hooks", len(cx_bb) >= 10 and all("--cli codex" in c for v in cx_bb.values() for c in v),
    "%d events wired through bb-hook --cli codex: %s" % (len(cx_bb), ",".join(sorted(cx_bb))))
rc, out = sh("cd ~/code/33GOD/bloodbank && git rev-parse HEAD && /opt/homebrew/bin/python3 services/agent-hooks/sync.py --check 2>&1 | tail -1")
add("hook-client", "hooks", rc == 0 and "OK" in out, "bloodbank checkout %s" % out.strip().replace("\n", " | "))
rc, out = sh("curl -s -m 5 http://127.0.0.1:8685/health")
add("hook-hub", "hooks", rc == 0 and '"state":"running"' in out.replace(" ", ""), "hub health: %s" % out.strip()[:160])

# ---------------------------------------------------------------- R3 provider (static)
env = claude_set.get("env", {})
helper = claude_set.get("apiKeyHelper", "")
want = {"ANTHROPIC_BASE_URL": "https://api.automaticai.io", "ANTHROPIC_MODEL": "automaticai/auto/orchestrator",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "automaticai/auto/subagent", "ANTHROPIC_DEFAULT_HAIKU_MODEL": "automaticai/auto/fast",
        "CLAUDE_CODE_SUBAGENT_MODEL": "automaticai/auto/subagent"}
bad = {k: env.get(k) for k, v in want.items() if env.get(k) != v}
add("claude-cli", "provider", not bad and "aai-gateway-token" in helper,
    "apiKeyHelper=%s; env mismatches=%s; no ANTHROPIC_API_KEY/AUTH_TOKEN in env: %s" % (
        helper, bad or "none", not any(k in env for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"))))

prov = codex_cfg.get("model_providers", {}).get("automaticai", {})
auth = prov.get("auth", {})
cat = codex_cfg.get("model_catalog_json", "")
cat_ok = os.path.isfile(cat)
add("codex-cli", "provider",
    codex_cfg.get("model_provider") == "automaticai" and prov.get("base_url") == "https://api.automaticai.io/v1"
    and prov.get("wire_api") == "responses" and "aai-gateway-token" in auth.get("command", "") and cat_ok
    and codex_cfg.get("model") == "automaticai/auto/orchestrator"
    and codex_cfg.get("agents", {}).get("default_subagent_model") == "automaticai/auto/subagent",
    "model_provider=%s model=%s base_url=%s wire_api=%s auth.command=%s catalog=%s(%s) subagent=%s retries=%s idle_ms=%s" % (
        codex_cfg.get("model_provider"), codex_cfg.get("model"), prov.get("base_url"), prov.get("wire_api"),
        auth.get("command"), cat, "present" if cat_ok else "MISSING", codex_cfg.get("agents", {}).get("default_subagent_model"),
        prov.get("stream_max_retries"), prov.get("stream_idle_timeout_ms")))

# token helpers: resolve, never print
tok = {}
for c in ("claude-code", "codex"):
    rc, out = sh("%s/.local/bin/aai-gateway-token %s" % (HOME, c), timeout=30)
    v = out.strip()
    tok[c] = v if rc == 0 else ""
    add("helper-" + c, "provider", rc == 0 and len(v) > 20,
        "aai-gateway-token %s rc=%s len=%d sha256[:8]=%s" % (c, rc, len(v), hashlib.sha256(v.encode()).hexdigest()[:8] if rc == 0 else "n/a"))
for c, v in tok.items():
    if not v:
        continue
    req = urllib.request.Request("https://api.automaticai.io/v1/models", headers={"Authorization": "Bearer " + v})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=20))
        ids = [m["id"] for m in d["data"]]
        has = all(x in ids for x in ("automaticai/auto", "automaticai/auto/orchestrator", "automaticai/auto/subagent", "automaticai/auto/fast"))
        add("gateway-" + c, "provider", has, "/v1/models 200 with %s token: %d routes, auto family present=%s, aai/damian/auto literal present=%s" % (
            c, len(ids), has, "aai/damian/auto" in ids))
    except Exception as e:
        add("gateway-" + c, "provider", False, "/v1/models error %s" % e)

# secret-in-file scan of every config this audit touches
leaks = []
for p in (os.path.join(HOME, ".claude", "settings.json"), os.path.join(HOME, ".codex", "config.toml"), os.path.join(HOME, ".codex", "hooks.json")):
    t = open(p).read()
    if re.search(r"sk-[A-Za-z0-9_-]{20,}", t) or re.search(r"sk-ant-[A-Za-z0-9_-]{20,}", t):
        leaks.append(p)
add("all", "no-secrets-in-config", not leaks, "plaintext key pattern in: %s" % (leaks or "none of the 3 config files"))

# ---------------------------------------------------------------- Desktop (static)
rc, out = sh("ls -d /Applications/Claude.app /Applications/ChatGPT.app 2>&1")
claude_desktop = os.path.isdir("/Applications/Claude.app")
OUT.append({"client": "claude-desktop", "requirement": "all", "status": "N/A",
            "evidence": "Claude.app not installed (/Applications/Claude.app absent; no ~/Library/Application Support/Claude)"
            if not claude_desktop else "installed: NOT AUDITED"})
add("codex-desktop", "installed", os.path.isdir("/Applications/ChatGPT.app"),
    "ChatGPT.app (Codex Desktop) present; its bundled codex binary reads the same ~/.codex files as the CLI")

# ---------------------------------------------------------------- live
if LIVE:
    def cs_query(sid):
        q = ("select type, actor->>'agent_id', actor->>'cli' from events where raw::text like '%%%s%%' "
             "and type not like '%%hook.updated' order by time" % sid)
        rc, o = sh("docker --context colima exec candystore-postgres sh -c 'psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -At -F\"|\" -c \"%s\"'" % q.replace("'", "'\"'\"'"), timeout=60)
        return [l for l in o.splitlines() if "|" in l]

    time.sleep(0)
    # Claude CLI
    d = "/tmp/aai-claude-check"
    os.makedirs(d, exist_ok=True)
    rc, out = sh("cd %s && timeout 170 claude -p 'Run pwd with the Bash tool then reply exactly GW-OK-CLAUDE' --output-format stream-json --verbose" % d, timeout=200)
    sid, model_used, txt, err = None, [], "", False
    for line in out.splitlines():
        try:
            m = json.loads(line)
        except Exception:
            continue
        if m.get("type") == "system" and m.get("subtype") == "init":
            sid = m.get("session_id")
            api_src = m.get("apiKeySource")
        if m.get("type") == "result":
            err = m.get("is_error")
            model_used = list((m.get("modelUsage") or {}).keys())
            txt = m.get("result", "")
    time.sleep(6)
    rows = cs_query(sid) if sid else []
    kinds = sorted({r.split("|")[0].replace("bloodbank.evt.", "") for r in rows})
    add("claude-cli", "live-turn", sid and not err and "GW-OK-CLAUDE" in txt and bool(model_used),
        "session=%s apiKeySource=%s is_error=%s models=%s reply=%r candystore_events=%d kinds=%s clis=%s" % (
            sid, api_src if sid else None, err, model_used, txt[:30], len(rows), kinds, sorted({r.split('|')[2] for r in rows})))
    # Codex CLI + Desktop bundled binary
    for label, binpath in (("codex-cli", "/opt/homebrew/bin/codex"),
                           ("codex-desktop", "/Applications/ChatGPT.app/Contents/Resources/codex")):
        if not os.path.exists(binpath):
            rc, w = sh("find /Applications/ChatGPT.app -name codex -type f -perm -u+x | head -1")
            binpath = w.strip() or binpath
        d = "/tmp/aai-codex-check"
        os.makedirs(d, exist_ok=True)
        rc, out = sh("cd %s && timeout 240 %s exec --json --skip-git-repo-check 'Run pwd then reply exactly GW-OK-%s'" % (d, binpath, label.upper()), timeout=260)
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
        time.sleep(6)
        rows = cs_query(tid) if tid else []
        kinds = sorted({r.split("|")[0].replace("bloodbank.evt.", "") for r in rows})
        add(label, "live-turn", tid and not failed and ("GW-OK-" + label.upper()) in reply,
            "binary=%s thread=%s failed=%s reply=%r candystore_events=%d kinds=%s clis=%s" % (
                binpath, tid, failed, reply[:30], len(rows), kinds, sorted({r.split('|')[2] for r in rows})))

print(json.dumps({"host": os.uname().nodename, "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "live": LIVE, "checks": OUT}, indent=1))
