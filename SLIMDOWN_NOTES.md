# 33GOD Metarepo Slimdown — 2026-04-19

**Ticket:** [GOD-41](https://plane.delo.sh/33god/projects/25aa04a1-0549-45c9-8899-d5791a44846e/issues/)
**Epic:** GOD-40 — Blood Bank Event Backbone Rebuild
**Branch:** `GOD-41/slimdown-blood-bank-focus`
**Rollback tag:** `pre-slimdown-2026-04-19` (on `main`)

## Intent

Reduce the 33GOD metarepo's working context to the Blood Bank event backbone so
the NATS pivot (Story 02), Candy Store persistence (Story 03), Candy Bar
observability (Story 04), and the canonical smoke-test (Story 05) can be
executed without noise from higher-order components.

## Outcome

| Action | Submodules |
|---|---|
| Kept as submodules | `bloodbank`, `candybar`, `candystore`, `holyfields` |
| Removed from metarepo | `agent-forge`, `HeyMa`, `holocene`, `iMi`, `jelmore`, `theboard`, `theboardroom`, `TonnyBox`, `zellij-driver` |
| Untouched external repos | each removed submodule remains an independent repo on `github.com/delorenj/<name>` |

The `services/` folder is unchanged; `services/theboard-meeting-trigger` is
now dormant (no consumer present) and will re-activate when TheBoard returns.
`perth` was already external at `~/code/perth/` before this slimdown.

## Preservation ledger

Uncommitted work was committed and pushed before any deinit.

| Repo | Branch | Tag | Remote |
|---|---|---|---|
| `bloodbank` | `v3-refactor` (NATS pivot WIP preserved) | `pre-preservation-2026-04-19` | `github.com/delorenj/bloodbank` |
| `HeyMa` | `wip/transcribe-preservation-2026-04-19` | — | `github.com/delorenj/HeyMa` |
| (metarepo) | `pre-slimdown-2026-04-19` tag on `main` HEAD | — | `github.com/delorenj/33GOD` |

All other removal candidates were clean and in sync with their origins at
removal time (verified: `git -C <submodule> log origin/main..HEAD` returned
empty for each).

## Metarepo files touched

- `.gitmodules` — reduced from 13 entries to 4 retained
- `.git/config` / `.git/modules/*` — per-submodule metadata purged for removed set
- `compose.yml` — `holocene` service block deleted; `API_CORS_ORIGINS` trimmed
- `mise.toml` — `holocene` dropped from cascading COMPONENTS arrays, dedicated
  `holocene:*` and `*:frontend` task blocks removed, `theboard-rabbitmq`
  legacy container name dropped from health grep
- `AGENTS.md` — removed sections: AgentForge, Holocene, TheBoard, TheBoardRoom,
  HeyMa, Jelmore, Zellij Driver. `theboard-meeting-trigger` marked dormant.
- `components.toml` — reduced to `bloodbank`, `candybar`, `candystore`,
  `holyfields`, `hookd`; stale entries for `flume`, `perth`, `yi` also cleared
- `.githooks/pre-commit` — `COMPONENTS_CHANGED` case block trimmed to match
  retained set; added `candystore/*` pattern that was missing
- `.env.example` — `HOLOCENE_DOMAIN` removed

## Explicitly out of scope (leave dormant)

- `services/registry.yaml` — service topology retained verbatim; `theboard-*`
  service routes live but idle
- `services/theboard-meeting-trigger/` — code retained, service stays in
  registry, runtime will simply not match any producer until TheBoard returns
- `services/candystore/docs/` — stale internal docs folder, ignored
- `docs/*.md` — architectural docs reference old component layout; will be
  rewritten alongside Story 02 ADR (the NATS pivot naturally rewrites the
  same narrative)
- `.gitignore` — stale rules for removed paths left in place (no files to
  match anyway; harmless)
- `huuk/` — appeared as an untracked orphan on `main` (never was a submodule
  on `main` itself; was only gitlinked on the abandoned
  `GOD-38/amqp-reconnection-logic` branch). Working copy left in place; move
  or delete as housekeeping when convenient.
- `.git/modules/{degenerate,flume,perth,yi}` — orphan internal metadata from
  pre-existing removals; untouched in this PR. `git submodule status` already
  ignores them.

## Rollback

Full metarepo restore to pre-slimdown state:

```bash
cd ~/code/33GOD
git fetch origin --tags
git checkout pre-slimdown-2026-04-19
git checkout -b rollback/restore-pre-slimdown
git submodule update --init --recursive
```

Submodule-specific rollback (working trees restored from preservation):

```bash
# bloodbank
git -C bloodbank fetch origin
git -C bloodbank checkout pre-preservation-2026-04-19

# HeyMa
git -C HeyMa fetch origin
git -C HeyMa checkout wip/transcribe-preservation-2026-04-19
```

## Follow-up work (tracked in Plane)

| Ticket | Story |
|---|---|
| GOD-42 | Rebuild Blood Bank as NATS-based event backbone |
| GOD-43 | Candy Store PostgreSQL event persistence |
| GOD-44 | Candy Bar desktop observability MVP |
| GOD-45 | Benign idempotent Bloodbank smoke-test event + command |

These stories are blocked by Story 01 (this slimdown) and should proceed in
order: GOD-42 establishes NATS and the event envelope; GOD-43 and GOD-44
attach to the backbone; GOD-45 gates end-to-end health checks for all four.

## Verification commands

```bash
git submodule status --recursive   # expect exactly 4 entries
cat .gitmodules | grep -c '^\[submodule'  # expect 4
ls .git/modules/                    # expect bloodbank, candybar, candystore, holyfields (+ harmless orphans)
rg '\b(agent-forge|holocene|iMi|jelmore|HeyMa|theboard|theboardroom|zellij-driver|TonnyBox)\b' \
   compose.yml AGENTS.md mise.toml components.toml .githooks/pre-commit .env.example
# expect: only historical comments in compose.yml + dormancy note in AGENTS.md
```
