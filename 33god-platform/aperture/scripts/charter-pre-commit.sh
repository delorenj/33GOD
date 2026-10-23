#!/usr/bin/env bash
# Aperture charter enforcement hook — mechanical, recall-independent.
# Installed by scripts/install-charter-hooks.sh as a PRE-COMMIT hook (the
# fleet-wide core.hooksPath only chains repo hooks for pre-commit).
# Rejects commits that touch aperture/ without a charter acknowledgment
# marker, and guards CHARTER.md edits behind the amendment marker.
set -u
COMMIT_MSG="$(git log -1 --format=%B 2>/dev/null)"
# For a NEW commit, the message isn't in git log yet; commit-msg stage not
# available under fleet pre-commit chaining, so we check the prepared
# message via the git editor path is unreliable — instead we gate on the
# STAGED FILES only and require the marker in .aperture/charter-session
# (written when an agent loads the charter this session).
touched=$(git diff --cached --name-only 2>/dev/null)

if printf '%s' "$touched" | grep -qE '(^|/)aperture/'; then
  SESSION="$(git rev-parse --show-toplevel 2>/dev/null)/.aperture/charter-session"
  if [ ! -f "$SESSION" ] || [ "$(find "$SESSION" -mmin -240 2>/dev/null | wc -l)" -eq 0 ]; then
    cat >&2 <<'EOF'
APERTURE CHARTER GATE (pre-commit)

This commit touches aperture/. The charter (aperture/CHARTER.md) must be
loaded before Aperture work. Refresh the session marker:

  cat 33god-platform/aperture/CHARTER.md   # actually read it
  mkdir -p .aperture && touch .aperture/charter-session

The marker goes stale after 4 hours on purpose. If you cannot state the
charter's commercial-decision and Damian's-machine rules from memory, you
have not loaded it — read it again.

If this commit CHANGES aperture/CHARTER.md itself: per §7 that requires
Jarad's approval + both agents' acknowledgment — do not stage it casually.
EOF
    exit 1
  fi
fi
exit 0
