#!/usr/bin/env bash
# peer-check.sh - read-only acceptance check for any 33GOD Mac peer, run over ssh.
#
#   peer-check.sh <ssh-target> [--json]
#
# Built one abstraction level up (belsky-doctrine): W10-3 asked for Damian's Mac;
# this script is the acceptance for every 33GOD Mac peer. Damian's values are the
# defaults, every host specific is a PEER_* env var (see the table below).
#
# Read-only, with ONE allowed write: a tagged synthetic hook event (session_id
# "peercheck-probe-<epoch>-<pid>", cli opencode, native session.created) is sent to
# the peer's hook-hub through bb-hook from a throwaway directory, and must show up
# in the peer's Candystore. Set PEER_PROBE=0 to skip it. The probe row stays in the
# store (Candystore has no delete API).
#
# Nothing here prints a secret value. Remote output is parsed locally and only ids,
# counts, states and perms are reported. launchctl output is filtered to four
# top-level fields before it leaves the peer.
#
# Result per check: PASS / WARN / FAIL plus one line of detail.
#   FAIL = a real defect on the peer. WARN = a known gap, drift or a thing that is
#   not this install's to fix. Exit code: 0 no FAIL, 1 at least one FAIL, 2 usage
#   or ssh error.
#
# Needs locally: bash, ssh, jq. Needs on the peer: sh, curl, docker, colima, nats,
# hindsight, launchctl, brew, git (all present on a 33GOD Mac peer).
# Written for bash 3.2 and newer (parses under macOS /bin/bash 3.2.57; run under bash 5).
#
# Overrides (defaults are Damian's Mac Studio; $HOME is expanded on the peer):
#   PEER_PATH               PATH used on the peer
#   PEER_COMPOSE_PROJECTS   space list of compose projects that must be up
#   PEER_NATS_URL           nats server url on the peer (nats://127.0.0.1:4222)
#   PEER_NATS_STREAMS       streams that must exist
#   PEER_HUB_URL            hook-hub read-only API (http://127.0.0.1:8685)
#   PEER_HOOK_CMD           bb-hook client used for the probe
#   PEER_CANDYSTORE_URL     (http://127.0.0.1:8683)
#   PEER_MAX_EVENT_AGE_S    newest Candystore event must be younger (7200)
#   PEER_PROBE              1 run the write probe, 0 skip (1)
#   PEER_PROBE_WAIT_S       how long to wait for the probe row (25)
#   PEER_CANDYBAR_URL       control plane (http://127.0.0.1:8700)
#   PEER_CANDYBAR_EXEC_URL  executor health (http://127.0.0.1:8701)
#   PEER_CANDYBAR_DIR       candybar checkout for 'doctor' ($HOME/code/33GOD/candybar)
#   PEER_CLOCK_OWN_RE       doctor violation ids matching this are 33GOD-owned
#   PEER_HINDSIGHT_URL      (http://127.0.0.1:8888); the CLI's own config carries the bearer
#   PEER_MIN_BANKS          fewest Hindsight banks accepted (1)
#   PEER_HERMES_LABEL       launchd label of the Hermes gateway (ai.hermes.gateway)
#   PEER_HERMES_STATE       gateway state file ($HOME/.hermes/gateway_state.json)
#   PEER_HERMES_HEALTH_URL  extra gateway health url, empty to skip (http://127.0.0.1:8642/health)
#   PEER_LAUNCHD_LABELS     33GOD native agents that must be running
#   PEER_BREW_SERVICES      brew services that must be started
#   PEER_REGISTRY_URL       pjangler registry (http://127.0.0.1:8764)
#   PEER_SECRETS_FILE       ($HOME/.config/33god/secrets.env)
#   PEER_SECRETS_SCAN_DIRS  where to look for stray copies
#   PEER_SECRETS_OWN_RE     stray copies matching this are install-introduced (FAIL)
#   PEER_REPO               33GOD checkout ($HOME/code/33GOD)
#   PEER_REPO_BRANCH        (main)
#   PEER_REPO_PLAIN_SUBS    submodules that are deliberately plain clones (candybar)
#   PEER_BOOT_LABEL         boot LaunchDaemon label (io.33god.colima)
#   PEER_BREW_COLIMA_LABEL  user agent the daemon retires (homebrew.mxcl.colima)
#   PEER_SSH_OPTS           extra ssh options

# $HOME in single quotes is deliberate: it is expanded on the peer, not here.
# shellcheck disable=SC2016
set -u
set -o pipefail

usage() {
  cat >&2 <<'EOF'
usage: peer-check.sh <ssh-target> [--json]

Read-only acceptance check for a 33GOD Mac peer (one tagged probe event is the
only write; PEER_PROBE=0 skips it). Exit 0 = no FAIL, 1 = FAIL, 2 = usage/ssh.
Host specifics: PEER_* env vars, documented at the top of this file.
EOF
  exit 2
}

TARGET=""
JSON=0
for a in "$@"; do
  case "$a" in
    --json) JSON=1 ;;
    -h|--help) usage ;;
    -*) echo "peer-check: unknown option $a" >&2; usage ;;
    *) if [ -z "$TARGET" ]; then TARGET=$a; else usage; fi ;;
  esac
done
[ -n "$TARGET" ] || usage
command -v jq >/dev/null 2>&1 || { echo "peer-check: jq is required locally" >&2; exit 2; }
command -v ssh >/dev/null 2>&1 || { echo "peer-check: ssh is required locally" >&2; exit 2; }

# ---------- defaults (Damian's values); $HOME is expanded on the peer ----------
dflt() { # name default
  if [ -z "${!1:-}" ]; then printf -v "$1" '%s' "$2"; fi
}
dflt PEER_PATH '$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin'
dflt PEER_COMPOSE_PROJECTS '33god-bus 33god-store candybar 33god-memory 33god-enricher plane-app n8n-foundation pjangler-registry'
dflt PEER_NATS_URL 'nats://127.0.0.1:4222'
dflt PEER_NATS_STREAMS 'BLOODBANK_EVENTS BLOODBANK_COMMANDS'
dflt PEER_HUB_URL 'http://127.0.0.1:8685'
dflt PEER_HOOK_CMD 'bb-hook'
dflt PEER_CANDYSTORE_URL 'http://127.0.0.1:8683'
dflt PEER_MAX_EVENT_AGE_S '7200'
dflt PEER_PROBE '1'
dflt PEER_PROBE_WAIT_S '25'
dflt PEER_CANDYBAR_URL 'http://127.0.0.1:8700'
dflt PEER_CANDYBAR_EXEC_URL 'http://127.0.0.1:8701'
dflt PEER_CANDYBAR_DIR '$HOME/code/33GOD/candybar'
dflt PEER_CLOCK_OWN_RE '^launchd:(io\.33god\.|ai\.hermes\.)'
dflt PEER_HINDSIGHT_URL 'http://127.0.0.1:8888'
dflt PEER_MIN_BANKS '1'
dflt PEER_HERMES_LABEL 'ai.hermes.gateway'
dflt PEER_HERMES_STATE '$HOME/.hermes/gateway_state.json'
if [ "${PEER_HERMES_HEALTH_URL+set}" != set ]; then PEER_HERMES_HEALTH_URL='http://127.0.0.1:8642/health'; fi
dflt PEER_LAUNCHD_LABELS 'io.33god.hook-hub io.33god.candybar-executor io.33god.pjangler-registry'
dflt PEER_BREW_SERVICES 'vinyl-server vinyl-client'
dflt PEER_REGISTRY_URL 'http://127.0.0.1:8764'
dflt PEER_SECRETS_FILE '$HOME/.config/33god/secrets.env'
dflt PEER_SECRETS_SCAN_DIRS '$HOME/.config $HOME/infra $HOME/33god-migration $HOME/.local $HOME/.hermes $HOME/.hindsight $HOME/code/33GOD $HOME/Documents $HOME/Desktop'
dflt PEER_SECRETS_OWN_RE '/33god-migration/|/config-backups/|/\.config/33god/|/code/33GOD/'
dflt PEER_REPO '$HOME/code/33GOD'
dflt PEER_REPO_BRANCH 'main'
dflt PEER_REPO_PLAIN_SUBS 'candybar'
dflt PEER_BOOT_LABEL 'io.33god.colima'
dflt PEER_BREW_COLIMA_LABEL 'homebrew.mxcl.colima'
dflt PEER_SSH_OPTS ''

# ---------- ssh plumbing ----------
WORK=$(mktemp -d "${TMPDIR:-/tmp}/peercheck.XXXXXX") || exit 2
cleanup() {
  ssh -O exit -o ControlPath="$WORK/cm" "$TARGET" >/dev/null 2>&1
  rm -rf "$WORK"
}
trap cleanup EXIT

# shellcheck disable=SC2206
SSH_ARGS=(-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=6
  -o ControlMaster=auto -o ControlPersist=120 -o ControlPath="$WORK/cm" $PEER_SSH_OPTS)

# Remote variables. Values may use $HOME (expanded on the peer) but no double
# quote or backtick.
PREAMBLE=""
export_remote() {
  local n v
  for n in "$@"; do
    v=${!n}
    case "$v" in
      *\"*|*\`*) echo "peer-check: $n must not contain a double quote or backtick" >&2; exit 2 ;;
    esac
    PREAMBLE="${PREAMBLE}${n}=\"${v}\"; "
  done
}
export_remote PEER_PATH PEER_COMPOSE_PROJECTS PEER_NATS_URL PEER_NATS_STREAMS PEER_HUB_URL \
  PEER_HOOK_CMD PEER_CANDYSTORE_URL PEER_CANDYBAR_URL PEER_CANDYBAR_EXEC_URL PEER_CANDYBAR_DIR \
  PEER_HINDSIGHT_URL PEER_HERMES_LABEL PEER_HERMES_STATE PEER_HERMES_HEALTH_URL \
  PEER_LAUNCHD_LABELS PEER_BREW_SERVICES PEER_REGISTRY_URL PEER_SECRETS_FILE \
  PEER_SECRETS_SCAN_DIRS PEER_REPO PEER_REPO_BRANCH PEER_BOOT_LABEL PEER_BREW_COLIMA_LABEL
PREAMBLE="${PREAMBLE}PATH=\"${PEER_PATH}\"; export PATH; "

# single-quote a string for a POSIX shell
qs() { printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"; }

# rr [VAR='x' ...]  < snippet : run a POSIX sh snippet on the peer, stdout only.
rr() {
  local snippet extra="${1:-}"
  snippet=$(cat)
  ssh -n "${SSH_ARGS[@]}" "$TARGET" "/bin/sh -c $(qs "${PREAMBLE}${extra:+$extra; }${snippet}")" 2>/dev/null
}

# ---------- results ----------
N_PASS=0; N_WARN=0; N_FAIL=0
NDJSON="$WORK/results.ndjson"
: > "$NDJSON"
emit() { # status id detail
  local st=$1 id=$2 detail=$3
  case "$st" in PASS) N_PASS=$((N_PASS+1)) ;; WARN) N_WARN=$((N_WARN+1)) ;; FAIL) N_FAIL=$((N_FAIL+1)) ;; esac
  jq -cn --arg s "$st" --arg i "$id" --arg d "$detail" '{id:$i,status:$s,detail:$d}' >> "$NDJSON"
  if [ "$JSON" = 1 ]; then
    printf '%-4s  %-28s %s\n' "$st" "$id" "$detail" >&2
  else
    printf '%-4s  %-28s %s\n' "$st" "$id" "$detail"
  fi
}
pass() { emit PASS "$1" "$2"; }
warn() { emit WARN "$1" "$2"; }
fail() { emit FAIL "$1" "$2"; }

# curl status helper on the peer: "<http code> <body>" lines are parsed locally
# (bodies are health JSON, never secrets)

# ---------- 0. reachability ----------
START_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
INFO=$(rr <<'EOF'
echo "host=$(hostname)"
echo "uid=$(id -u)"
echo "home=$HOME"
echo "user=$(id -un)"
echo "os=$(uname -s) $(uname -m) $(sw_vers -productVersion 2>/dev/null)"
EOF
)
RC=$?
if [ $RC -ne 0 ] || [ -z "$INFO" ]; then
  echo "peer-check: cannot ssh to $TARGET (rc=$RC)" >&2
  exit 2
fi
getv() { printf '%s\n' "$1" | sed -n "s/^$2=//p" | head -1; }
P_HOST=$(getv "$INFO" host); P_UID=$(getv "$INFO" uid); P_USER=$(getv "$INFO" user)
P_OS=$(getv "$INFO" os); P_HOME=$(getv "$INFO" home)
if [ "$JSON" != 1 ]; then
  echo "peer-check $TARGET  host=$P_HOST user=$P_USER  $P_OS  start=$START_ISO"
  echo
fi
pass ssh "$P_USER@$P_HOST, $P_OS, BatchMode ok"

# ---------- 1. colima + docker context ----------
OUT=$(rr <<'EOF'
colima status 2>&1
echo "__rc=$?"
echo "__ctx=$(docker context show 2>&1)"
echo "__dockerps=$(docker ps -q 2>/dev/null | wc -l | tr -d ' ')"
EOF
)
if printf '%s\n' "$OUT" | grep -q '^__rc=0'; then
  d=$(printf '%s\n' "$OUT" | sed -n 's/.*msg="\(colima is running[^"]*\)".*/\1/p' | head -1)
  a=$(printf '%s\n' "$OUT" | sed -n 's/.*msg="arch: \([^"]*\)".*/\1/p' | head -1)
  pass colima "${d:-colima running}, arch ${a:-?}"
else
  fail colima "colima is not running: $(printf '%s\n' "$OUT" | grep -v '^__' | tail -1 | cut -c1-120)"
fi
CTX=$(getv "$OUT" __ctx); NRUN=$(getv "$OUT" __dockerps)
if [ "$CTX" = colima ] && [ "${NRUN:-0}" -gt 0 ] 2>/dev/null; then
  pass docker-context "plain docker uses context colima, $NRUN containers running"
elif [ "$CTX" = colima ]; then
  fail docker-context "context colima but 0 running containers"
else
  warn docker-context "docker context is '${CTX:-unknown}', not colima (plain docker over ssh may hit the wrong daemon)"
fi

# ---------- 2. compose projects ----------
PS=$(rr <<'EOF'
docker ps -a --format '{{.Label "com.docker.compose.project"}}|{{.Names}}|{{.Status}}|{{.State}}' 2>&1
EOF
)
for proj in $PEER_COMPOSE_PROJECTS; do
  total=0; up=0; healthy=0; oneshot=0; bad=""; starting=""
  while IFS='|' read -r p name status state; do
    [ "$p" = "$proj" ] || continue
    total=$((total+1))
    case "$state" in
      running)
        case "$status" in
          *"(unhealthy)"*) bad="$bad $name(unhealthy)" ;;
          *"health: starting"*) starting="$starting $name" ;;
          *"(healthy)"*) up=$((up+1)); healthy=$((healthy+1)) ;;
          *) up=$((up+1)) ;;
        esac ;;
      exited)
        case "$status" in
          "Exited (0)"*) oneshot=$((oneshot+1)) ;;
          *) bad="$bad $name($status)" ;;
        esac ;;
      *) bad="$bad $name($state)" ;;
    esac
  done <<EOF2
$PS
EOF2
  if [ "$total" -eq 0 ]; then
    fail "compose:$proj" "project not found (no containers carry com.docker.compose.project=$proj)"
  elif [ -n "$bad" ]; then
    fail "compose:$proj" "bad:$bad ($up up of $total)"
  elif [ -n "$starting" ]; then
    warn "compose:$proj" "still starting:$starting ($up up of $total)"
  else
    pass "compose:$proj" "$up up ($healthy healthy), $oneshot one-shot exited(0), $total containers"
  fi
done

# ---------- 3. NATS streams ----------
for s in $PEER_NATS_STREAMS; do
  OUT=$(rr "S='$s'" <<'EOF'
nats --server "$PEER_NATS_URL" --timeout 5s stream info "$S" --json 2>/dev/null
EOF
)
  if printf '%s' "$OUT" | jq -e '.config.name' >/dev/null 2>&1; then
    d=$(printf '%s' "$OUT" | jq -r '"\(.state.messages) msgs, last_seq \(.state.last_seq), last \(.state.last_ts), \(.state.consumer_count) consumers, \(.config.retention)"')
    pass "nats:$s" "$d"
  else
    fail "nats:$s" "stream not found or nats unreachable at $PEER_NATS_URL"
  fi
done

# ---------- 4. hook-hub ----------
OUT=$(rr <<'EOF'
curl -s -m 5 "$PEER_HUB_URL/health"
EOF
)
if printf '%s' "$OUT" | jq -e '.hub' >/dev/null 2>&1; then
  d=$(printf '%s' "$OUT" | jq -r '.hub | "state \(.state), pid \(.pid), publish_enabled \(.publish_enabled), registry_error \(.registry_error), journal_error \(.journal_error), transport_error \(.transport_error), obs pending \(.observation_delivery.pending), socket present \(.socket.present)"')
  if printf '%s' "$OUT" | jq -e '.hub.state=="running" and .hub.registry_error==null and .hub.journal_error==null and .hub.transport_error==null and .hub.publish_enabled==true and .hub.socket.present==true' >/dev/null; then
    pass hook-hub "$d"
  else
    fail hook-hub "$d"
  fi
else
  fail hook-hub "no /health answer from $PEER_HUB_URL"
fi

# ---------- 5. candystore health + freshness ----------
OUT=$(rr <<'EOF'
echo "healthz=$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$PEER_CANDYSTORE_URL/healthz")"
echo "readyz=$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$PEER_CANDYSTORE_URL/readyz")"
echo "__now=$(date -u +%s)"
echo "__newest"
curl -s -m 10 "$PEER_CANDYSTORE_URL/events?limit=1&tools=0"
EOF
)
HZ=$(getv "$OUT" healthz); RZ=$(getv "$OUT" readyz)
BODY=$(printf '%s\n' "$OUT" | sed -n '/^__newest$/,$p' | sed 1d)
NOW=$(getv "$OUT" __now)
T=$(printf '%s' "$BODY" | jq -r '.events[0].time // empty' 2>/dev/null)
AGE=""
if [ -n "$T" ] && [ -n "$NOW" ]; then
  EV=$(printf '%s' "$T" | sed -E 's/\.[0-9]+Z$/Z/' | jq -Rr 'fromdateiso8601' 2>/dev/null)
  [ -n "$EV" ] && AGE=$((NOW - EV))
fi
if [ "$HZ" != 204 ] || [ "$RZ" != 204 ]; then
  fail candystore "healthz $HZ readyz $RZ (want 204/204)"
elif [ -z "$AGE" ]; then
  fail candystore "healthz 204 but no event found in /events"
elif [ "$AGE" -gt "$PEER_MAX_EVENT_AGE_S" ]; then
  fail candystore "healthz 204, newest event is ${AGE}s old (limit ${PEER_MAX_EVENT_AGE_S}s)"
else
  pass candystore "healthz 204, readyz 204, newest event ${AGE}s old ($(printf '%s' "$BODY" | jq -r '.events[0].type'))"
fi

# ---------- 6. live end-to-end probe (the one allowed write) ----------
if [ "$PEER_PROBE" = 1 ]; then
  SID="peercheck-probe-$(date -u +%s)-$$"
  OUT=$(rr "SID='$SID'" <<'EOF'
d=$(mktemp -d "${TMPDIR:-/tmp}/peercheck-probe.XXXXXX") || exit 3
cd "$d" || exit 3
git init -q >/dev/null 2>&1
printf '{"session_id":"%s","cwd":"%s"}' "$SID" "$d" | BB_HOOK_DEADLINE=10 $PEER_HOOK_CMD opencode session.created >/dev/null 2>&1
cd / && rm -rf "$d"
echo sent
EOF
)
  if [ "$OUT" != sent ]; then
    fail probe "could not send the synthetic event through $PEER_HOOK_CMD"
  else
    FOUND=""; i=0; T0=$(date +%s)
    while [ "$i" -lt "$PEER_PROBE_WAIT_S" ]; do
      R=$(rr <<'EOF'
curl -s -m 10 "$PEER_CANDYSTORE_URL/events?cli=opencode&type=bloodbank.agent.session.started&limit=30&tools=0"
EOF
)
      FOUND=$(printf '%s' "$R" | jq -r --arg s "$SID" '[.events[]? | select(.data.session_id==$s)][0].id // empty' 2>/dev/null)
      [ -n "$FOUND" ] && break
      i=$((i+1)); sleep 1
    done
    if [ -z "$FOUND" ]; then
      fail probe "event $SID sent to the hook-hub but not in Candystore after ${PEER_PROBE_WAIT_S}s (hub -> NATS -> Candystore broken)"
    else
      CODE=$(rr "EID='$FOUND'" <<'EOF'
curl -s -m 5 -o /dev/null -w '%{http_code}' "$PEER_CANDYSTORE_URL/events/$EID"
EOF
)
      if [ "$CODE" = 200 ]; then
        pass probe "$SID -> hub -> NATS -> Candystore event $FOUND (GET /events/id 200), $(( $(date +%s) - T0 ))s"
      else
        fail probe "event $FOUND listed but GET /events/$FOUND returned $CODE"
      fi
    fi
  fi
else
  warn probe "skipped (PEER_PROBE=0)"
fi

# ---------- 7. turn.annotated in the last 24h ----------
OUT=$(rr <<'EOF'
now=$(date -u +%s)
from=$(date -u -r $((now-86400)) +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d @$((now-86400)) +%Y-%m-%dT%H:%M:%SZ)
curl -s -m 20 "$PEER_CANDYSTORE_URL/events?type=bloodbank.conversation.turn.annotated&from=$from&limit=1&total=1"
EOF
)
N=$(printf '%s' "$OUT" | jq -r '.total // empty' 2>/dev/null)
if [ -z "$N" ]; then
  fail turn-annotated "Candystore query failed"
elif [ "$N" -gt 0 ]; then
  pass turn-annotated "$N turn.annotated events in the last 24h, newest $(printf '%s' "$OUT" | jq -r '.events[0].time')"
else
  fail turn-annotated "0 turn.annotated events in the last 24h (turn-enricher not annotating)"
fi

# ---------- 8. candybar ----------
OUT=$(rr <<'EOF'
echo "cp=$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$PEER_CANDYBAR_URL/healthz")"
echo "cpbody=$(curl -s -m 5 "$PEER_CANDYBAR_URL/healthz")"
echo "ex=$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$PEER_CANDYBAR_EXEC_URL/healthz")"
echo "exbody=$(curl -s -m 5 "$PEER_CANDYBAR_EXEC_URL/healthz")"
echo "__jobs"
curl -s -m 10 "$PEER_CANDYBAR_URL/candybars"
EOF
)
JOBS=$(printf '%s\n' "$OUT" | sed -n '/^__jobs$/,$p' | sed 1d)
if [ "$(getv "$OUT" cp)" = 200 ] && getv "$OUT" cpbody | grep -q '"ok"'; then
  NJ=$(printf '%s' "$JOBS" | jq -r '[.[]|select(.enabled and (.archived|not))]|length' 2>/dev/null)
  pass candybar-control-plane "$PEER_CANDYBAR_URL/healthz ok, ${NJ:-?} enabled jobs registered"
else
  fail candybar-control-plane "healthz $(getv "$OUT" cp) $(getv "$OUT" cpbody)"
fi
if [ "$(getv "$OUT" ex)" = 200 ] && getv "$OUT" exbody | grep -q '"ok"'; then
  pass candybar-executor "$PEER_CANDYBAR_EXEC_URL/healthz ok"
else
  fail candybar-executor "healthz $(getv "$OUT" ex) $(getv "$OUT" exbody)"
fi
JOBROWS=$(printf '%s' "$JOBS" | jq -r '.[]? | select(.enabled and (.archived|not)) | [.id,.name]|@tsv' 2>/dev/null)
if [ -z "$JOBROWS" ]; then
  warn candybar-jobs "no enabled jobs registered (nothing to check)"
fi
while IFS="$(printf '\t')" read -r jid jname; do
  [ -n "$jid" ] || continue
  R=$(rr "ID='$jid'" <<'EOF'
curl -s -m 10 "$PEER_CANDYBAR_URL/candybars/$ID/invocations?limit=10"
EOF
)
  L=$(printf '%s' "$R" | jq -c '[.invocations[]? | select(.result != null)] | sort_by(.startedAt) | reverse | .[0] // empty' 2>/dev/null)
  if [ -z "$L" ]; then
    warn "candybar-job:$jname" "never ran (no finished invocation yet)"
  else
    res=$(printf '%s' "$L" | jq -r '.result'); at=$(printf '%s' "$L" | jq -r '.startedAt'); ec=$(printf '%s' "$L" | jq -r '.exitCode')
    if [ "$res" = success ]; then
      pass "candybar-job:$jname" "last run $at success (exit $ec)"
    else
      fail "candybar-job:$jname" "last run $at result=$res exit=$ec: $(printf '%s' "$L" | jq -r '(.errorMessage // .stderrTail // "")' | head -c 120)"
    fi
  fi
done <<EOF2
$JOBROWS
EOF2

# ---------- 9. candybar doctor --live ----------
OUT=$(rr <<'EOF'
cd "$PEER_CANDYBAR_DIR" 2>/dev/null || { echo "__nodir"; exit 0; }
out=$(candybar doctor --repo . --live --json 2>/dev/null); rc=$?
printf '%s\n' "$out"
echo "__RC=$rc"
EOF
)
if printf '%s\n' "$OUT" | grep -q '^__nodir'; then
  fail candybar-doctor "no candybar checkout at $PEER_CANDYBAR_DIR"
else
  RCD=$(printf '%s\n' "$OUT" | sed -n 's/^__RC=//p' | tail -1)
  DJ=$(printf '%s\n' "$OUT" | grep -v '^__RC=')
  if ! printf '%s' "$DJ" | jq -e '.checks' >/dev/null 2>&1; then
    fail candybar-doctor "doctor produced no JSON (rc=${RCD:-?})"
  else
    # each violation id with its section; repo-section violations are always 33GOD-owned
    ALLV=$(printf '%s' "$DJ" | jq -r '.checks | to_entries[] | .key as $k | .value.violations[]? | [$k,.id]|@tsv')
    OWN=0; OTH=0; OWNIDS=""
    while IFS="$(printf '\t')" read -r sec vid; do
      [ -n "$vid" ] || continue
      if [ "$sec" = repo ] || printf '%s' "$vid" | grep -Eq "$PEER_CLOCK_OWN_RE"; then
        OWN=$((OWN+1)); OWNIDS="$OWNIDS $vid"
      else
        OTH=$((OTH+1))
      fi
    done <<EOF2
$ALLV
EOF2
    UNK=$(printf '%s' "$DJ" | jq -r '[.checks[]?.unknown[]?]|length')
    CNT=$(printf '%s' "$DJ" | jq -r '[.checks[]?.counts // empty] | .[0] // {} | to_entries | map("\(.key) \(.value)") | join(", ")')
    d="status $(printf '%s' "$DJ" | jq -r .status) rc=${RCD:-?}; $OWN 33GOD-owned, $OTH owner-other violations; unknown $UNK; scanned: ${CNT:-n/a}"
    if [ "${RCD:-0}" -ge 2 ] 2>/dev/null; then
      fail candybar-doctor "doctor errored: $d"
    elif [ "$OWN" -gt 0 ]; then
      fail candybar-doctor "$d; 33GOD-owned:$OWNIDS"
    elif [ "$OTH" -gt 0 ] || [ "$UNK" -gt 0 ]; then
      warn candybar-doctor "$d (peer's own clocks, nothing disabled)"
    else
      pass candybar-doctor "$d"
    fi
  fi
fi

# ---------- 10. hindsight ----------
OUT=$(rr <<'EOF'
echo "noauth=$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$PEER_HINDSIGHT_URL/health")"
echo "__health"
hindsight health -o json 2>/dev/null
echo "__banks"
hindsight bank list -o json 2>/dev/null
EOF
)
NOAUTH=$(getv "$OUT" noauth)
HEALTH=$(printf '%s\n' "$OUT" | sed -n '/^__health$/,/^__banks$/p' | sed '1d;$d')
BANKS=$(printf '%s\n' "$OUT" | sed -n '/^__banks$/,$p' | sed 1d)
NB=$(printf '%s' "$BANKS" | jq -r 'length' 2>/dev/null)
if printf '%s' "$HEALTH" | jq -e '.status=="healthy"' >/dev/null 2>&1 && [ -n "$NB" ]; then
  names=$(printf '%s' "$BANKS" | jq -r '[.[].bank_id]|join(",")')
  d="healthy (db $(printf '%s' "$HEALTH" | jq -r .database)), bearer ok via CLI config, $NB banks: $names; no-bearer GET /health -> $NOAUTH"
  if [ "$NB" -lt "$PEER_MIN_BANKS" ]; then
    fail hindsight "$d (want >= $PEER_MIN_BANKS banks)"
  elif [ "$NOAUTH" = 200 ]; then
    fail hindsight "$d (API answers without a bearer)"
  elif [ "$NOAUTH" = 401 ]; then
    pass hindsight "$d"
  else
    warn hindsight "$d (expected 401 without a bearer)"
  fi
else
  fail hindsight "health/bank list failed with the CLI's bearer at $PEER_HINDSIGHT_URL (no-bearer code $NOAUTH)"
fi

# ---------- 11. hermes gateway ----------
OUT=$(rr <<'EOF'
launchctl print "gui/$(id -u)/$PEER_HERMES_LABEL" 2>&1 | awk '/^\t(state|pid|runs|last exit code) = /{sub(/^\t/,""); print "L:" $0}'
echo "__state"
jq -c '{gateway_state,pid,updated_at,profiles:(.served_profiles|length?)}' "$PEER_HERMES_STATE" 2>/dev/null
if [ -n "$PEER_HERMES_HEALTH_URL" ]; then echo "__health=$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$PEER_HERMES_HEALTH_URL")"; fi
EOF
)
LST=$(printf '%s\n' "$OUT" | sed -n 's/^L:state = //p' | head -1)
LPID=$(printf '%s\n' "$OUT" | sed -n 's/^L:pid = //p' | head -1)
LRUNS=$(printf '%s\n' "$OUT" | sed -n 's/^L:runs = //p' | head -1)
GS=$(printf '%s\n' "$OUT" | sed -n '/^__state$/,$p' | sed -n '2p')
GST=$(printf '%s' "$GS" | jq -r '.gateway_state // empty' 2>/dev/null)
GPR=$(printf '%s' "$GS" | jq -r '.profiles // "?"' 2>/dev/null)
HH=$(printf '%s\n' "$OUT" | sed -n 's/^__health=//p' | head -1)
if [ "$LST" = running ] && [ "$GST" = running ]; then
  d="launchd gui/$P_UID/$PEER_HERMES_LABEL running (pid $LPID, runs $LRUNS), gateway_state running, $GPR profiles served"
  if [ -n "$HH" ] && [ "$HH" != 200 ]; then
    fail hermes-gateway "$d; extra health $PEER_HERMES_HEALTH_URL returned $HH"
  else
    pass hermes-gateway "$d${HH:+; extra health $HH}"
  fi
else
  fail hermes-gateway "launchd state '${LST:-not loaded}', gateway_state '${GST:-unreadable}'"
fi

# ---------- 12. native 33GOD launchd agents ----------
for label in $PEER_LAUNCHD_LABELS; do
  OUT=$(rr "LBL='$label'" <<'EOF'
launchctl print "gui/$(id -u)/$LBL" 2>&1 | awk '/^\t(state|pid|runs|last exit code) = /{sub(/^\t/,""); print "L:" $0}'
EOF
)
  st=$(printf '%s\n' "$OUT" | sed -n 's/^L:state = //p' | head -1)
  pid=$(printf '%s\n' "$OUT" | sed -n 's/^L:pid = //p' | head -1)
  runs=$(printf '%s\n' "$OUT" | sed -n 's/^L:runs = //p' | head -1)
  le=$(printf '%s\n' "$OUT" | sed -n 's/^L:last exit code = //p' | head -1)
  if [ "$st" != running ]; then
    fail "launchd:$label" "state '${st:-not loaded in gui/$P_UID}'"
  elif [ -n "$le" ] && [ "$le" != "(never exited)" ] && [ "$le" != 0 ]; then
    warn "launchd:$label" "running (pid $pid, runs $runs) but last exit code $le (an earlier crash was recovered by KeepAlive)"
  else
    pass "launchd:$label" "running (pid $pid, runs $runs, last exit ${le:-none})"
  fi
done

# ---------- 13. brew services (vinyl) ----------
OUT=$(rr <<'EOF'
brew services list 2>/dev/null
EOF
)
for svc in $PEER_BREW_SERVICES; do
  row=$(printf '%s\n' "$OUT" | awk -v s="$svc" '$1==s{print $2}' | head -1)
  if [ "$row" = started ]; then
    pass "brew:$svc" "brew service started"
  else
    fail "brew:$svc" "brew service status '${row:-absent}'"
  fi
done

# ---------- 14. pjangler registry ----------
OUT=$(rr <<'EOF'
echo "code=$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$PEER_REGISTRY_URL/health")"
echo "__body"
curl -s -m 5 "$PEER_REGISTRY_URL/health"
EOF
)
BODY=$(printf '%s\n' "$OUT" | sed -n '/^__body$/,$p' | sed 1d)
if [ "$(getv "$OUT" code)" = 200 ] && printf '%s' "$BODY" | jq -e '.ok==true' >/dev/null 2>&1; then
  pass pjangler-registry "$PEER_REGISTRY_URL/health 200 $(printf '%s' "$BODY" | jq -c '{service,schema_version}')"
else
  fail pjangler-registry "health $(getv "$OUT" code) $(printf '%s' "$BODY" | head -c 100)"
fi

# ---------- 15. secrets file perms + strays ----------
OUT=$(rr <<'EOF'
perm=$(stat -f '%Lp' "$PEER_SECRETS_FILE" 2>/dev/null || stat -c '%a' "$PEER_SECRETS_FILE" 2>/dev/null)
echo "perm=$perm"
echo "__strays"
# shellcheck disable=SC2086
find $PEER_SECRETS_SCAN_DIRS -maxdepth 7 \( -name node_modules -o -name .git -o -name .venv \) -prune -o \
  \( -name 'secrets.env' -o -name 'secrets.env.*' -o -name 'secrets.env~' \) -print 2>/dev/null |
while IFS= read -r f; do
  p=$(stat -f '%Lp' "$f" 2>/dev/null || stat -c '%a' "$f" 2>/dev/null)
  printf '%s %s\n' "$p" "$f"
done
EOF
)
PERM=$(getv "$OUT" perm)
STRAYS=$(printf '%s\n' "$OUT" | sed -n '/^__strays$/,$p' | sed 1d)
SECREAL=$(rr <<'EOF'
printf '%s' "$PEER_SECRETS_FILE"
EOF
)
if [ -z "$PERM" ]; then
  fail secrets-perms "$PEER_SECRETS_FILE does not exist"
elif [ "$PERM" = 600 ]; then
  pass secrets-perms "$SECREAL mode 0600"
else
  fail secrets-perms "$SECREAL mode 0$PERM (want 0600)"
fi
OWNC=0; OTHC=0; OTHL=""; OWNL=""
while read -r p f; do
  [ -n "$f" ] || continue
  [ "$f" = "$SECREAL" ] && continue
  short=$(printf '%s' "$f" | sed "s#^$P_HOME#~#")
  if printf '%s' "$f" | grep -Eq "$PEER_SECRETS_OWN_RE"; then
    OWNC=$((OWNC+1)); OWNL="$OWNL $short(0$p)"
  else
    OTHC=$((OTHC+1)); OTHL="$OTHL $short(0$p)"
  fi
done <<EOF2
$STRAYS
EOF2
if [ "$OWNC" -gt 0 ]; then
  fail secrets-strays "$OWNC install-introduced secrets.env copies besides the live file:$OWNL; $OTHC outside this install${OTHL:+:$OTHL}"
elif [ "$OTHC" -gt 0 ]; then
  warn secrets-strays "no install-introduced copies; $OTHC secrets.env files outside this install:$OTHL"
else
  pass secrets-strays "no stray secrets.env copies under: $(printf '%s' "$PEER_SECRETS_SCAN_DIRS" | sed 's#\$HOME#~#g')"
fi

# ---------- 16. repo clean and at origin/main ----------
OUT=$(rr <<'EOF'
cd "$PEER_REPO" 2>/dev/null || { echo "NOREPO=1"; exit 0; }
echo "HEAD=$(git rev-parse HEAD)"
echo "DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
git status --porcelain 2>/dev/null | head -5 | sed 's/^/D:/'
echo "AHEAD=$(git rev-list --count "origin/$PEER_REPO_BRANCH..HEAD" 2>/dev/null)"
echo "REMOTE=$(GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=10' git ls-remote origin "refs/heads/$PEER_REPO_BRANCH" 2>/dev/null | cut -f1)"
git submodule status 2>/dev/null | awk '{print "S:" $0}'
EOF
)
if [ "$(getv "$OUT" NOREPO)" = 1 ]; then
  fail repo "no checkout at $PEER_REPO"
else
  H=$(getv "$OUT" HEAD); DIRTY=$(getv "$OUT" DIRTY); AHEAD=$(getv "$OUT" AHEAD); REMOTE=$(getv "$OUT" REMOTE)
  SUBS=$(printf '%s\n' "$OUT" | sed -n 's/^S://p')
  NSUB=0; SUBBAD=""
  while read -r line; do
    [ -n "$line" ] || continue
    NSUB=$((NSUB+1))
    mark=${line:0:1}; rest=${line:1}; sname=$(printf '%s' "$rest" | awk '{print $2}')
    case "$mark" in
      "-") case " $PEER_REPO_PLAIN_SUBS " in *" $sname "*) : ;; *) SUBBAD="$SUBBAD $sname(uninitialised)" ;; esac ;;
      "+") SUBBAD="$SUBBAD $sname(moved off its pin)" ;;
      U*) SUBBAD="$SUBBAD $sname(conflict)" ;;
    esac
  done <<EOF2
$SUBS
EOF2
  base="HEAD ${H:0:7}, $NSUB submodules"
  if [ "${DIRTY:-0}" -gt 0 ]; then
    fail repo "$DIRTY uncommitted entries ($(printf '%s\n' "$OUT" | sed -n 's/^D://p' | head -3 | tr '\n' ';' | cut -c1-100)); $base"
  elif [ "${AHEAD:-0}" -gt 0 ] 2>/dev/null; then
    fail repo "$AHEAD unpushed commits ahead of origin/$PEER_REPO_BRANCH; $base"
  elif [ -n "$SUBBAD" ]; then
    warn repo "clean, but submodules:$SUBBAD; $base"
  elif [ -z "$REMOTE" ]; then
    warn repo "clean, no unpushed commits, but could not read origin/$PEER_REPO_BRANCH from the peer; $base"
  elif [ "$REMOTE" = "$H" ]; then
    pass repo "clean, == origin/$PEER_REPO_BRANCH (${H:0:7}); submodules at pins"
  else
    warn repo "clean, nothing unpushed, but behind origin/$PEER_REPO_BRANCH (${REMOTE:0:7}); the check is read-only so nothing was fetched; $base"
  fi
fi

# ---------- 17. boot daemon ----------
OUT=$(rr <<'EOF'
[ -f "/Library/LaunchDaemons/$PEER_BOOT_LABEL.plist" ] && echo "plist=1" || echo "plist=0"
launchctl print "system/$PEER_BOOT_LABEL" 2>&1 | awk '/^\t(state|pid|runs) = /{sub(/^\t/,""); print "L:" $0}'
pgrep -f 'boot-daemon/colima-run.sh' >/dev/null 2>&1 && echo "runner=1" || echo "runner=0"
launchctl print "gui/$(id -u)/$PEER_BREW_COLIMA_LABEL" >/dev/null 2>&1 && echo "brewagent=1" || echo "brewagent=0"
echo "fv=$(fdesetup status 2>/dev/null | head -1)"
echo "autorestart=$(pmset -g 2>/dev/null | awk '$1=="autorestart"{print $2}')"
EOF
)
PLIST=$(getv "$OUT" plist); RUNNER=$(getv "$OUT" runner); BA=$(getv "$OUT" brewagent)
FV=$(getv "$OUT" fv); AR=$(getv "$OUT" autorestart)
LST=$(printf '%s\n' "$OUT" | sed -n 's/^L:state = //p' | head -1)
case "$FV" in *"is On"*) FVN="FileVault ON: a cold or power-loss boot stops at the pre-boot screen, use 'sudo fdesetup authrestart' for planned reboots" ;; *) FVN="FileVault: ${FV:-unknown}" ;; esac
if [ "$PLIST" != 1 ]; then
  warn boot-daemon "not installed (no /Library/LaunchDaemons/$PEER_BOOT_LABEL.plist): Colima starts only at login. Run 'sudo ~/33god-boot-daemon.sh --apply' on the peer. $FVN"
elif [ "$LST" != running ] && [ "$RUNNER" != 1 ]; then
  fail boot-daemon "plist installed but the daemon is not running"
elif [ "$BA" = 1 ]; then
  warn boot-daemon "daemon running but the user agent $PEER_BREW_COLIMA_LABEL is still loaded (two supervisors)"
else
  pass boot-daemon "system/$PEER_BOOT_LABEL running, user agent retired, autorestart ${AR:-?}. $FVN"
fi

# ---------- 18. power ----------
SL=$(rr <<'EOF'
pmset -g 2>/dev/null | awk '$1=="sleep"{print $2}'
EOF
)
if [ "$SL" = 0 ]; then
  pass pmset "system sleep 0 (never)"
elif [ -z "$SL" ]; then
  warn pmset "could not read pmset"
else
  fail pmset "system sleep is $SL minutes (a sleeping peer drops the bus and every listener)"
fi

# ---------- summary ----------
END_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
if [ "$JSON" = 1 ]; then
  jq -s --arg t "$TARGET" --arg h "$P_HOST" --arg s "$START_ISO" --arg e "$END_ISO" \
    --argjson p "$N_PASS" --argjson w "$N_WARN" --argjson f "$N_FAIL" \
    '{target:$t,host:$h,started:$s,finished:$e,summary:{pass:$p,warn:$w,fail:$f},checks:.}' "$NDJSON"
else
  echo
  echo "summary: $N_PASS PASS, $N_WARN WARN, $N_FAIL FAIL   ($TARGET, $START_ISO to $END_ISO)"
fi
[ "$N_FAIL" -eq 0 ]
