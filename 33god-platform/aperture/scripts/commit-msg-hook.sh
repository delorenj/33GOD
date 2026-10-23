#!/usr/bin/env bash
# Aperture charter enforcement hook — mechanical, recall-independent.
# Installed by scripts/install-charter-hooks.sh
# Rejects commits that (a) touch aperture/ without a charter acknowledgment
# marker, or (b) claim to change the charter without operator authorization.
set -u
COMMIT_MSG_FILE="$1"
msg=$(cat "$COMMIT_MSG_FILE")

# Files touched by this commit
touched=$(git diff --cached --name-only 2>/dev/null; git diff --name-only HEAD 2>/dev/null)

if printf '%s' "$touched" | grep -q '^33god-platform/aperture/\|^aperture/'; then
  if ! printf '%s' "$msg" | grep -qiE 'charter-ack|[Cc]harter v?[0-9]'; then
    cat >&2 <<'EOF'
APERTURE CHARTER GATE

This commit touches aperture/. Per aperture/CHARTER.md §6-7 you must:
  1. Have loaded aperture/CHARTER.md this session (read it: cat 33god-platform/aperture/CHARTER.md)
  2. Acknowledge it in the commit message with the marker: charter-ack
     (e.g. "g1 bundle: ... (charter-ack v1.0)")

If this commit CHANGES aperture/CHARTER.md itself, the message must also
contain "charter-amendment" and reference Jarad's approval; the hook will
still require both named agents' ack per §7.

Rejected: no charter marker in message.
EOF
    exit 1
  fi
  if printf '%s' "$touched" | grep -q 'CHARTER\.md'; then
    if ! printf '%s' "$msg" | grep -qi 'charter-amendment'; then
      echo "APERTURE CHARTER GATE: edits to CHARTER.md need 'charter-amendment' + Jarad approval reference in the message." >&2
      exit 1
    fi
  fi
fi
exit 0
