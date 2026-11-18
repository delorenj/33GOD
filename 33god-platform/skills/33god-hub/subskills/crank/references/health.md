# Is the crank alive?

Report four things separately: **scheduler freshness**, **actual fires**, **per-session
outcome**, and **attention and host health**. A missing or unreadable signal means
*unknown*. It never means "recovered" or "healthy".

## 1. Bindings and their clocks

```bash
pj crank sessions --all          # every binding: pane, interval, last success, next fire, last class
curl -s http://127.0.0.1:8700/candybars | jq '.[] | select(.name|startswith("crank-"))'
cd ~/code/33GOD/candybar && uv run candybar show <binding>   # latest terminal invocation
```

A live interactive session in a crank-enabled project with no binding is an **attach
fault**. Look in `~/.local/state/crank/hooks.jsonl` for its refusal reason. A binding whose
latest invocation is stale or failing is a **clock fault**.

## 2. What the fires did

`pj crank log`, or `~/.local/state/crank/log/<binding>.jsonl`, has one row per fire: the
class seen and whether the officer ran. A run of `working` rows on a pane that is plainly
stuck means the gate misread it. See [fire-and-officer.md](fire-and-officer.md) for the
liveness checks:

- A **wedged turn**: frozen screen, zero CPU-tick growth (`/proc/<pid>/stat` fields 14+15
  sampled twice ~12s apart), and no writes under the CLI's session storage.
- A **phantom wait**: the pane says it is waiting, but background workflows are advancing.
  Leave it alone.

Any single signal can lie. Require all three.

## 3. The prompt says `⚠ crank stalled`

The v2 rule: the binding has not fired for max(15m, 2×interval + 5m), counted from the latest
of `last_fire`, `since` and `reclocked_ms`, or its Redis hash expired under a live pane
pointer. Check the binding's Candybar row first, then its log. `crank_fire` re-creates an
expired hash from the facts it carries, so one successful fire clears it.

No crank segment at all is correct for an unbound pane, an unreachable Redis, or a legacy
hash under a quiet engine. See [state.md](state.md).

## 4. Attention: watchdog and host

- `crank-watchdog` (Candybar, `*/15`) writes
  `~/.local/state/zcrank/watchdog.json.local-report.json`. `scheduling-policy-drift` writes
  `~/.local/state/candybar-scheduling-policy/transitions.json.local-report.json`.
- `crank-attention-officer` (Candybar exec row, `10,25,40,55`) runs
  `~/.agents/tools/jev-clairic/bin/crank-attention`. It reads both reports through
  `zcrank-gate.py`'s readers and wakes its officer only for a key nobody has read, or one
  unread for 1h+ (PJAN-218).
- `crank-attention --status [KEY]` shows who read alarm KEY and what they concluded.
  `--dry-run` prints the brief without running the officer.
- `crank-watchdog.sh --dry-run --state-file <scratch>` diagnoses without delivering.

## Expected, not faults

- Candybar `crank-beat` is disabled and Hermes job `777c511a009c` is paused (PJAN-216, since
  2026-11-18). An old `cron/output/777c511a009c/` is normal.
- `crank:engine` and the `crank:p:*` hashes stop refreshing once the legacy scan stops. The
  prompt ignores them.
- `no_change`, `skipped` or `completed` on a scheduler row proves that a tick ran, not that
  a pane was attended. Per-fire log rows are the evidence.
