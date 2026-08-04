#!/usr/bin/env bash
# Stage the per-agent runtime config/secrets via a TRANSIENT Hermes profile.
# HERMES_HOME is the ignored ./runtime directory; this profile dir is a staging area
# (cred-stripped .env + SOUL) that 20-runtime-repo.sh folds into the runtime and
# then replaces with a symlink ~/.hermes/profiles/<name> -> ./runtime. That
# symlink is load-bearing: hermes resolves `--profile <name>` invocations
# through it (recreating it wrongly if it goes missing).
# shellcheck source=_lib.sh
source "$(dirname "$0")/_lib.sh"
load_role_env

already_done 10-hermes-profile && { log "[10] profile already created — skipping"; exit 0; }

log "[10] creating hermes profile: $PROFILE_NAME"
PROFILE_HOME="$HOME/.hermes/profiles/$PROFILE_NAME"

# Set repo path to directory where .git is
REPO_PATH="$(cd "$ROLE_DIR" && git rev-parse --show-toplevel 2>/dev/null || echo "$ROLE_DIR")"

if [[ -d "$PROFILE_HOME" ]]; then
  log "    profile dir already exists; reusing"
else
  # --clone (NOT --clone-all): copies config.yaml, .env, SOUL.md only.
  # --clone-all has a recursion bug — it copies the entire ~/.hermes tree,
  #   including profiles/ itself, producing nested profiles/<name>/profiles/<name>/...
  # We do explicit skill + plugin + hooks copies below to avoid that.
  "$HERMES_BIN" profile create "$PROFILE_NAME" --clone --no-alias
fi

# Manually copy the inheritable bits that --clone doesn't get.
# These are content-only dirs; safe to mirror without recursion risk.
log "    mirroring skills, plugins, hooks from default profile"
for sub in skills plugins hooks cron skins; do
  src="$HOME/.hermes/$sub"
  dst="$PROFILE_HOME/$sub"
  if [[ -d "$src" && "$src" != "$PROFILE_HOME"* ]]; then
    mkdir -p "$dst"
    # cp -R, dereferencing symlinks; -u to preserve newer if dst exists
    cp -RLu "$src/." "$dst/" 2>/dev/null || cp -RL "$src/." "$dst/" 2>/dev/null || true
  fi
done

# Strip any inherited gateway/runtime state so this profile boots clean.
rm -f "$PROFILE_HOME/gateway.pid" "$PROFILE_HOME/gateway_state.json" \
      "$PROFILE_HOME/processes.json" "$PROFILE_HOME/state.db" 2>/dev/null || true
# Belt-and-suspenders: if a profiles/ dir somehow exists, remove it
[[ -d "$PROFILE_HOME/profiles" ]] && rm -rf "$PROFILE_HOME/profiles"

# Strip inherited messaging-platform credentials from the cloned .env.
# `profile create --clone` copies the DEFAULT profile's .env verbatim — and the
# default profile is an operator's own agent (e.g. Condaleeza on Slack). Without
# this, every sub-agent inherits the parent's bot token and would (a) hijack the
# parent's Slack/Telegram socket if it ever connects, and (b) crash-loop: the
# gateway treats an inherited-but-unusable platform as "configured", fails to
# connect it, and exits non-fatal only when ZERO platforms are configured. A
# sub-agent must establish its OWN identity via the Wire steps (30-telegram etc),
# never borrow the parent's.
PROFILE_ENV="$PROFILE_HOME/.env"
if [[ -f "$PROFILE_ENV" ]]; then
  # Some Hermes versions implement `profile create --clone` by symlinking the
  # cloned .env back to the default profile.  Never sanitize through that
  # symlink: doing so would delete the operator's fleet-wide provider secrets.
  # Break only the .env link into a private, mode-0600 copy first.
  if [[ -L "$PROFILE_ENV" ]]; then
    log "    detaching cloned .env symlink before profile-local sanitization"
    PROFILE_ENV_COPY="$PROFILE_HOME/.env.profile-local.$$"
    cp -L "$PROFILE_ENV" "$PROFILE_ENV_COPY"
    chmod 600 "$PROFILE_ENV_COPY"
    mv -fT "$PROFILE_ENV_COPY" "$PROFILE_ENV"
  fi
  log "    stripping inherited platform credentials from profile .env"
  python3 - "$PROFILE_ENV" <<'PYEOF'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1])
# Identity-bearing platform creds that must be per-agent, not inherited.
keys = (
    "SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "SLACK_ALLOWED_USERS",
    "SLACK_SIGNING_SECRET", "SLACK_HOME_CHANNEL",
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USERS",
    "DISCORD_BOT_TOKEN", "DISCORD_ALLOWED_USERS", "DISCORD_HOME_CHANNEL",
    "DISCORD_HOME_CHANNEL_NAME",
)
# Only touch *uncommented* assignments (leave the template's `# KEY=` examples).
pat = re.compile(r"^\s*(?:%s)=" % "|".join(keys))
lines = p.read_text().splitlines(keepends=True)
kept = [ln for ln in lines if not pat.match(ln)]
if len(kept) != len(lines):
    p.write_text("".join(kept))
PYEOF
  chmod 600 "$PROFILE_ENV"
fi

if [[ "$ROLE" == "pm" ]]; then
  VOX_URL_VALUE="${VOX_URL:-$(config_get fleet.vox_url 'https://vox.delo.sh')}"
  if [[ -n "$VOX_URL_VALUE" ]]; then
    log "    ensuring VOX_URL is present for PM voice mode"
    python3 - "$PROFILE_ENV" "$VOX_URL_VALUE" <<'PYEOF'
import pathlib, sys

path = pathlib.Path(sys.argv[1])
vox_url = sys.argv[2]
lines = path.read_text().splitlines() if path.exists() else []
for idx, line in enumerate(lines):
    if line.startswith("VOX_URL="):
        lines[idx] = f'VOX_URL="{vox_url}"'
        break
else:
    lines.append(f'VOX_URL="{vox_url}"')
path.write_text("\n".join(lines) + "\n")
PYEOF
    chmod 600 "$PROFILE_ENV"
  fi
fi

# Apply role-specific config overrides.
log "    setting terminal.cwd = $REPO_PATH"
env HERMES_HOME="$PROFILE_HOME" "$HERMES_BIN" config set terminal.cwd "$REPO_PATH"

# Canonical shared-skill source of truth + local PM fallback sync.
CANONICAL_SKILLS_DIR="${CANONICAL_SKILLS_DIR:-$(config_get fleet.canonical_skills_dir '/home/delorenj/.agents/skills')}"
CANONICAL_PM_SKILL_SRC="$CANONICAL_SKILLS_DIR/subagent-driven-development"
LOCAL_PM_SKILL_DST="$PROFILE_HOME/skills/software-development/subagent-driven-development"

if [[ -d "$CANONICAL_SKILLS_DIR" ]]; then
  log "    setting skills.external_dirs[0] = $CANONICAL_SKILLS_DIR"
  env HERMES_HOME="$PROFILE_HOME" "$HERMES_BIN" config set skills.external_dirs.0 "$CANONICAL_SKILLS_DIR"

  # Ensure key PM/local-ops skills are symlinked into runtime/profile skills root.
  # This preserves canonical ownership and keeps updates instant across agents.
  read -r -a SYMLINKED_RUNTIME_SKILLS <<< "${SYMLINKED_RUNTIME_SKILLS:-$(config_get fleet.symlinked_runtime_skills 'delonet-conventions delonet-dotenv hermes-pm-template-maintenance hindsight subagent-driven-development')}"
  mkdir -p "$PROFILE_HOME/skills"

  for skill_name in "${SYMLINKED_RUNTIME_SKILLS[@]}"; do
    src="$CANONICAL_SKILLS_DIR/$skill_name"
    dst="$PROFILE_HOME/skills/$skill_name"

    if [[ ! -f "$src/SKILL.md" ]]; then
      warn "    skipping runtime skill symlink (missing SKILL.md): $src"
      continue
    fi

    if [[ -L "$dst" && "$(readlink "$dst")" == "$src" ]]; then
      log "    runtime skill symlink already set: $dst -> $src"
      continue
    fi

    [[ -e "$dst" || -L "$dst" ]] && rm -rf "$dst"
    ln -s "$src" "$dst"
    log "    symlinked runtime skill: $dst -> $src"
  done
else
  warn "    canonical skills dir missing: $CANONICAL_SKILLS_DIR"
fi

if [[ -f "$CANONICAL_PM_SKILL_SRC/SKILL.md" ]]; then
  log "    syncing canonical PM workflow skill -> $LOCAL_PM_SKILL_DST"
  mkdir -p "$LOCAL_PM_SKILL_DST"
  cp -f "$CANONICAL_PM_SKILL_SRC/SKILL.md" "$LOCAL_PM_SKILL_DST/SKILL.md"
else
  warn "    canonical PM skill missing: $CANONICAL_PM_SKILL_SRC/SKILL.md"
fi

# Install the project's SOUL.md into the profile so the agent loads it.
if [[ -f "$ROLE_DIR/SOUL.md" ]]; then
  cp "$ROLE_DIR/SOUL.md" "$PROFILE_HOME/SOUL.md"
  log "    installed SOUL.md into profile"
fi

mark_done 10-hermes-profile
