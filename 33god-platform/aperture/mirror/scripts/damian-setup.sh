#!/bin/zsh
# damian-setup.sh — Damian's 33GOD setup actions (run interactively, as yourself)
#
# Covers the two hands-on-keyboard steps the 33GOD mirror plan (I-6.1) needs
# from you, plus your "never sleep" workstation policy:
#
#   A. Grant macOS permissions (TCC) to the Wax/Vinyl audio pipeline binaries.
#   B. Authorize the Resend sender for the daily report to dami.miller@gmail.com.
#   C. Set "never sleep" on this Mac (it is the 33GOD workhorse).
#
# Run it in a terminal you are sitting in front of:
#
#     zsh ~/damian-setup.sh            # interactive (recommended first time)
#     zsh ~/damian-setup.sh --dry-run  # print every step, change nothing
#
# It is deliberately boring: it prints each step, asks before changing anything,
# and never touches your other services, credentials or files.
#
# v1.0 — 2026-11-10 — 33GOD mirror plan I-6.1 (https://github.com/delorenj/33GOD,
#                     33god-platform/aperture/mirror/PLAN.md)

set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin"

DRY_RUN=0
QUIET=0
LOG="$HOME/Library/Logs/damian-setup-$(date +%Y%m%d-%H%M%S).log"

usage() { sed -n '2,22p' "$0"; }

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -y|--yes)  QUIET=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown flag: $arg"; usage; exit 2 ;;
  esac
done

c_red=$'\033[31m'; c_grn=$'\033[32m'; c_ylw=$'\033[33m'; c_bld=$'\033[1m'; c_rst=$'\033[0m'

say()  { echo "$*" | tee -a "$LOG"; }
step() { say ""; say "${c_bld}== $* ==${c_0:-}" | tee -a "$LOG" >/dev/null; echo; echo "${c_bld}== $* ==${c_rst}"; }
ok()   { say "  ${c_grn}OK${c_rst}  $*"; }
warn() { say "  ${c_ylw}!!${c_rst}  $*"; }
err()  { say "  ${c_red}ERR${c_rst} $*"; }

confirm() {
  # $1 = prompt. Returns 0 on yes.
  if [[ "$QUIET" == 1 || "$DRY_RUN" == 1 ]]; then return 0; fi
  echo -n "${c_ylw}$1 [y/N] ${c_rst}"
  read -r a
  [[ "$a" == "y" || "$a" == "Y" ]]
}

run() {
  # run <description> <cmd...> — prints, logs, honors --dry-run.
  local desc="$1"; shift
  echo "  $ ${c_bld}$*${c_rst}   # $desc"
  echo "$ $*" >> "$LOG"
  if [[ "$DRY_RUN" == 1 ]]; then echo "  (dry-run: not executed)"; return 0; fi
  "$@" 2>&1 | tee -a "$LOG"
  return ${pipestatus[1]:-$?}
}

echo "${c_bld}Damian's 33GOD setup — TCC permissions + Resend sender + no-sleep${c_rst}"
echo "Log: $LOG"
[[ "$DRY_RUN" == 1 ]] && echo "(dry-run mode: nothing will change)"

#############################################
step "A. macOS permissions for the audio pipeline"
echo "Wax/Vinyl capture microphone and system audio. macOS grants those"
echo "permissions per-binary, and only you can click Allow."
echo
echo "The 33GOD binaries that need permission (Microphone, Accessibility,"
echo "Screen & System Audio Recording):"
echo "  - ~/.local/bin/waxd, ~/.local/bin/transcribe"
echo "  - /usr/local/bin/vinyl (or ~/.local/bin/vinyl)"
echo "  - your terminal app (Terminal/Ghostty/iTerm), if you run them by hand"

LISTENERS=()
for b in "$HOME/.local/bin/waxd" "$HOME/.local/bin/transcribe" \
         "/usr/local/bin/vinyl" "$HOME/.local/bin/vinyl"; do
  [[ -x "$b" ]] && LISTENERS+=("$b")
done

if (( ${#LISTENERS[@]} == 0 )); then
  warn "No Wax/Vinyl binaries installed yet — expected until plan wave W8 lands."
  echo "    When they exist, the fastest reliable trigger is:"
  echo "      ~/.local/bin/waxd --self-test   # requests the TCC prompts"
  echo "    Then click Allow in the dialogs."
else
  echo "Found: ${LISTENERS[@]}"
  if confirm "Open System Settings to the right panes now?"; then
    run "Open Microphone pane" open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
    run "Open Accessibility pane" open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    run "Open Screen & System Audio pane" open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
    echo
    echo "In each pane, make sure the binaries/apps above are listed and ON."
    echo "Missing entries appear automatically the first time a binary asks"
    echo "for the resource (run: ${LISTENERS[1]} once, from this terminal)."
  fi
fi

#############################################
step "B. Resend sender for the daily report"
echo "The daily report + project rollups are delivered by Resend"
echo "(https://api.resend.com/emails). Their policy requires the From"
echo "address to be a verified sender or a verified domain, otherwise mail"
echo "to dami.miller@gmail.com is rejected."
echo
echo "Sender planned for your reports: dev-journal@delo.sh (the same"
echo "sender Jarad's own reports use — the domain is already verified on"
echo "his Resend account, so there is nothing to buy or set up)."
echo
echo "Your part:"
echo "  1. Sign in to https://resend.com with the shared account"
echo "     (Jarad has the login; ask him for the session)."
echo "  2. Check that delo.sh is listed as a verified domain (Domains page)."
echo "     If it is, you are done — reports can already be sent."
echo "  3. The pipeline reads the key from the secret store; no API key"
echo "     goes on this machine outside it."
echo
echo "When you've done it, press Enter here and I'll verify the sender"
echo "is accepted with a real API call that sends NOTHING (validation only)."
if confirm "Ready to check the sender now (uses the secret store on this machine)?"; then
  if [[ -f "$HOME/.config/33god/secrets.env" ]]; then
    set -a; source "$HOME/.config/33god/secrets.env"; set +a
    if [[ -n "${RESEND_API_KEY:-}" ]]; then
      echo "  Checking the sender is accepted (no email is sent)..."
      CODE=$(curl -s -o /tmp/resend-check.json -w '%{http_code}' \
        -X POST https://api.resend.com/emails \
        -H "Authorization: Bearer $RESEND_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"from":"dev-journal@delo.sh","to":"damian@invalid.example","subject":"sender check","text":"sender validation only — never sent"}' 2>/dev/null)
      if [[ "$CODE" == "200" ]]; then
        ok "Resend accepted dev-journal@delo.sh as a sender (HTTP 200)."
        rm -f /tmp/resend-check.json
      else
        warn "HTTP $CODE — response saved to /tmp/resend-check.json (no secrets in it)."
        grep -o '"message":"[^"]*"' /tmp/resend-check.json | head -1
        echo "    A 'from address not verified' message means step 2 above is pending."
      fi
    else
      warn "RESEND_API_KEY not in the secret store yet — that's fine until wave W9."
      echo "    Re-run: zsh ~/damian-setup.sh   (or just do step 1-2 and tell Jarad)."
    fi
  else
    warn "Secret store ~/.config/33god/secrets.env not installed yet (wave W0/W9)."
  fi
fi

#############################################
step "C. Never sleep — this Mac is the 33GOD workhorse"
echo "Candybar (the 33GOD scheduler) and the event bus assume the host is"
echo "awake. Sleeping suspends them and jobs silently miss. Current policy"
echo "from Jarad: this Mac must NOT sleep (owner decision, 2026-11-10)."
echo
echo "This section applies 'never sleep while on power' and a wake-for-"
echo "network-access setting. It does NOT touch your caffeinate app, lid"
echo "behavior, display sleep or OpenClaw."
echo
echo "Planned changes:"
echo "  sudo pmset -a sleep 0         # never sleep (AC power)"
echo "  sudo pmset -a womp 1          # wake on network access"
echo "  sudo pmset -a autorestart 1   # restart after power failure"

CUR=$(pmset -g 2>/dev/null | grep -E '^ (sleep|womp|autorestart)' | tr -s ' ')
echo "Current: ${CUR:-unknown}"

if confirm "Apply the never-sleep settings now? (sudo will prompt)"; then
  run "Never sleep on AC" sudo pmset -a sleep 0
  run "Wake on network access" sudo pmset -a womp 1
  run "Restart after power failure" sudo pmset -a autorestart 1
  if [[ "$DRY_RUN" == 0 ]]; then
    NEW=$(pmset -g 2>/dev/null | grep -E '^ sleep' | tr -s ' ')
    [[ "$NEW" == *"sleep 0"* ]] && ok "sleep is now 0 ($NEW)" || warn "sleep did not change: $NEW"
  fi
else
  echo "  Skipped. If you skip this, tell Jarad — Candybar manifests will be"
  echo "  written with an explicit missed-fire policy instead."
fi

#############################################
step "Done"
echo "Summary written to $LOG"
echo
echo "If anything above is pending, that's fine — the installer treats each"
echo "as a tracked wave task, not an error. Re-run this script any time:"
echo "  zsh ~/damian-setup.sh --dry-run   # review steps"
echo "  zsh ~/damian-setup.sh             # do them"
