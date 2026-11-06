# Feature packaging design (2026-11-05)

> **Partly superseded.** Operator decisions of 2026-11-06 (see `../initiatives.md` I-9 and the `33god-features` skill) override this file: the catalog is `33GOD/features.toml`, not `~/.agents/features.toml`; features track main, so no `^0.4` version ranges; every feature has a formal repo; the CAND-49 pin is already gone (CAND-52). Atom owners in section 7 are replaced by `asm-ownership-study.md` (ASM and zellij-driver own what this file gave to Deckard and bloodbank).


- **Core** (design 3): convention-first feature homes, checks as the contract, claim sweeps, and live probes.
- **Lifecycle engine** (design 1): journal, clock ordering, adopt, why, implements-differential and lint, built on pj's RecipeRegistry and RecipeCheck.
- **Host rule** (design 2): the host holds pointers, never logic.

`†` marks a command, flag or route that does not exist yet.

## 0. Facts checked on the live box that shape the design

| Fact | Evidence | Consequence |
|---|---|---|
| Two jobs share the name `cronjob_manage`: 777c511a009c (crank) and 9b5dadbd1e4d (jev-rollup). | 33god-pm `cron/jobs.json`. `resolve_job_ref` raises `AmbiguousJobReference` (hermes-agent `cron/jobs.py:2001`). | Rename both before anything addresses a job by name. |
| `hermes cron edit <id> --name` exists, and `cron run --wait` resolves a name. | `hermes_cli/subcommands/cron.py` (edit parser); `cron_wait.py:128` | The rename is one live command. |
| `hermes cron status` takes no job argument and has no `--json`. | `hermes_cli/cron.py:1031` | The `agent.job` atom needs a change in the fork. |
| A monitor script gets no job id or output dir in its env. | `cron/scheduler_script.py:482` | The gate stub is rendered with the id until the fork exports `HERMES_CRON_OUTPUT_DIR`. |
| Only `candybar.transition_exec` writes `watchdog.json.local-report.json`, and the gate reads that file. | `transition_exec.py:135`; `zcrank-gate.py:232` | **All three designs dropped this wrapper from the watchdog argv, which would have killed the gate's watchdog wake.** It is kept here. |
| The watchdog's `load_contract` looks beside itself, then in `../bin/`, then in `~/.local/bin`. | `crank-watchdog.py:22-28` | Running `hermes/crank-watchdog.sh` from the checkout picks up the fresh `bin/zcrank.py` with no code change. |
| Of the profile copies, only `zcrank.py` differs (116 diff lines). The watchdog `.py` and `.sh`, `zcrank_attendance.py` and `zcrank-gate.sh` are byte-identical to source. | `cmp` | Moving the watchdog to source changes exactly one thing: it gains the PJAN-201 rules. |
| The live crank rows have no `project:` tag, and `register --update` adopts an untagged row in place. | API at :8700; `cli/control.py:531-537` | Ids 01a1793b… and 01a186c1… survive the move along with 2,804 invocations of history. |
| `--prune` runs only over the whole project, scoped by `project:<name>`. | `control.py:435-439` | One feature per repo until Candybar gets tag-scoped prune. |
| Exec `argv[0]` must be absolute or a bare command looked up on PATH; a relative path with a slash resolves against the project root. The user manager's PATH includes `~/.local/bin`. | `runners.py:90`; `systemctl --user show-environment` | Manifests can use bare `candybar` and `zcrank-*`. |
| :8764 serves `/health`, `/v1/registry`, `/v1/index`, `/v1/rebuild`, `/v1/remove` and `/v1/settings`. It has no resolve route. | `src/project/registryService.ts` | `/v1/resolve` is new pjangler work. |
| PJAN-202 is on origin/main (dd9eb4e), but the main checkout sits at 61a2812. | git | `pj crank panes --json` becomes the provisional provider as soon as the main checkout is pulled and rebuilt. |
| `~/code/33GOD/.project.json` has project_id `33god`, while the bank is `33GOD`. | file | `project.identity` must return `memory_bank` as its own field. |

## 1. The model

- **Feature home.** A repo, or `features/<name>/` inside one, that holds a `feature.toml`.
  - Convention covers `bin/`, `hermes/jobs/`, `hermes/stubs/`, `.candybars/`, `checks/`, `migrations/` and `schemas/`.
  - The manifest says only what paths cannot: required atoms, provided atoms, claims, params, state policy, and known re-implementations.
- **Desired state.** `~/.agents/features.toml`, tracked in delorenj/agents, with `[host.<hostname>]` tables.
- **Installed state.**
  - The receipt is `~/.local/state/33god/features/<name>.json`, in the skillex v2 shape: links carry raw/dev/ino, copies carry sha256, sources carry a commit.
  - During an apply, `<name>.journal` records each step for unwinding.
- **Atoms.**
  - A contract and its live probe live in the **owning** repo, at `contracts/atoms/<atom>.v<major>.toml`.
  - They are indexed through the existing `contracts:` key of 33god-platform `components/<id>.yaml`.
  - The host lock `~/.local/state/33god/atoms.lock` records which provider was chosen.
  - The owner is declared once, in the contract. A non-owner may serve only as `provisional`.
- **Engine.** `pj feature plan|apply|check|adopt|remove|why`†.
  - Each feature loads as a host-scoped `LifecycleRecipe`, so RecipeRegistry enforces unique ids, existing dependencies and no cycles.
  - Each artifact class is a `RecipeCheck{scope:"host", audit, migrate, remove†}`, which is the parity engine's existing audit, fix and re-audit contract.
  - There are six drivers, each a thin shell over an owner tool:
    - `link`: skillex's owned-link primitive.
    - `stub`: render plus sha256.
    - `hermes-job`: upsert by name through `hermes cron create` or `edit`.
    - `skillex`: select, then `skillex profile sync`.
    - `candybar`: `register --update --prune` run from the feature home.
    - `state`: Redis and directories; export, then `SCAN` and `DEL`.
- **Rules.**
  1. The clock starts **last** on apply and stops **first** on remove.
  2. The world beats the receipt. `check` and `--absent` sweep the claims on the live box. A receipt only grants permission to delete what still matches it.
  3. Ids live only in receipts and rendered stubs. `[lint] forbidden` enforces this across the declared consumer paths.
  4. A Hermes profile holds only rendered, logic-free stubs. All logic runs from one checkout.
  5. Every atom has one owner. Any other implementation is either `provisional` or declared under `[[implements]]` and differential-checked live. No fixtures.

## 2. Manifests

```toml
# ~/code/33GOD/crank/feature.toml
[feature]
name = "crank"
version = "0.4.0"
owner = "delorenj/crank"
scope = "host"
platforms = ["linux"]

[params]                      # rendered only into stubs and ~/.config/33god/features/crank.env
hermes_profile = { default = "33god-pm" }
# No session param: pane.topology's provider owns it (Deckard [mux] session).

[requires]                    # atom = major; resolved by live probe; owner declared in the contract
"pane.topology"    = "1"
"agent.process"    = "1"
"agent.session"    = "1"
"project.identity" = "1"
"agent.job"        = "1"
"clock"            = "1"
"jev.calls"        = "1"      # the jev-clairic feature, which stays in delorenj/agents

[provides]
"crank.binding" = { v = 1, cli = "zcrankctl keys --json", contract = "contracts/atoms/crank.binding.v1.toml" }
"pane.input"    = { v = 1, cli = "zcrank-act --json", provisional = true }   # until deckard-mux passes

[skills]
select = ["crank-engine"]     # skillex owns the text; the feature owns the selection

[claims]                      # anything matching is crank's, receipted or not
redis       = ["zcrank:*"]
paths       = ["~/.local/state/zcrank/", "~/.local/bin/zcrank*", "~/.local/bin/crank-*",
               "~/.hermes/profiles/{hermes_profile}/scripts/zcrank*",
               "~/.hermes/profiles/{hermes_profile}/scripts/crank-*",
               "~/.hermes/profiles/{hermes_profile}/skills/**/crank-*"]
hermes_jobs = ["crank-*"]
candybars   = ["project:crank"]

[state]
redis_schema = "schemas/redis/zcrank.v1.toml"   # tab hash, log-state partition, config
on_remove    = "export"                         # JSONL to ~/.local/state/33god/archive/ before SCAN+DEL
migrations   = "migrations/"

[[implements]]                # a known second implementation, checked live, never trusted
atom = "crank.binding"
by = "pjangler:src/crank/index.ts"
differential = "pj crank list --json"

[lint]
forbidden = ["777c511a009c", "01a1793b", "/home/delorenj", '"Workspace"']
paths     = ["**", "consumer:pjangler/src/crank/**", "consumer:wingman/sources/fleet.py"]
```

```toml
# crank/.candybars/crank-beat.candybar.toml
[candybar]
name = "crank-beat"
tags = ["hermes-agent", "feature:crank"]
schedule = "*/5 * * * *"
timezone = "America/New_York"
noise = true
[candybar.runner]
kind = "hermes"
profile = "33god-pm"
job_id = "crank-beat"         # a NAME: HERMES_REF_RE allows it, cron run --wait resolves it
timeout_s = 1860

# crank/.candybars/crank-watchdog.candybar.toml
[candybar]
name = "crank-watchdog"
tags = ["ops", "no-agent", "feature:crank"]
schedule = "*/15 * * * *"
timezone = "UTC"
noise = true
[candybar.runner]
kind = "exec"                 # no workdir: starts in the project root
# transition-exec writes watchdog.json.local-report.json, which the gate reads. Never drop it.
argv = ["candybar", "transition-exec", "--state", "zcrank/watchdog.json", "--local-only", "--", "./hermes/crank-watchdog.sh"]
timeout_s = 180
```

`candybar transition-exec`† is the existing module exposed as a subcommand. A relative `--state` resolves under `$XDG_STATE_HOME`.

```toml
# crank/hermes/jobs/crank-beat.toml   (upserted BY NAME; the id lives only in the receipt)
name = "crank-beat"
prompt_file = "crank-beat.prompt.txt"
monitor_script = "zcrank-gate.sh"
skills = ["crank-engine"]
toolsets = ["terminal"]
context_from = ["self"]
workdir = "~/code/33GOD"
deliver = "local"
scheduler = "external"
[economics]                   # today's live values, verbatim; I-8 lifts them as one recorded change
max_daily_runs = 96
max_daily_tokens = 10_000_000
max_daily_usd = "40.00"
max_run_usd = "4.00"
```

```sh
# crank/hermes/stubs/zcrank-gate.sh.tmpl : the only kind of file allowed in a profile
#!/bin/sh
# GENERATED by pj feature (crank {version}). Do not edit: `pj feature check crank` byte-compares it.
export ZCRANK_GATE_LAST="${HERMES_CRON_OUTPUT_DIR:-$HOME/.hermes/profiles/{hermes_profile}/cron/output/{job_id}}/monitor_last_output.txt"
exec "$HOME/.local/bin/zcrank-gate"
```

Once the fork exports `HERMES_CRON_OUTPUT_DIR`, the `{job_id}` fallback is deleted and the stub's bytes are constant across versions and job ids.

Checks live in `crank/checks/*`. Each is executable, exits 0 or 1, and prints JSON `{ok, findings[], repair?}`:

| Check | What it verifies |
|---|---|
| `bins-complete` | Every `bin/*` has an owned link to this checkout. |
| `stubs-fresh` | Re-renders each stub from the receipt's inputs and byte-compares it. |
| `profile-clean` | A claim sweep of `{profile}/scripts` finds only receipted stubs. |
| `job-by-name` | `crank-beat` resolves to exactly the receipt's id, and no other job matches `crank-*`. |
| `candybars-synced` | Candybar reports SYNC ok for every `project:crank` row. |
| `watchdog-report-fresh` | The local report is version 1 and less than 35 minutes old. |
| `binding-agreement` | `zcrankctl`, `pj crank` and Wingman agree on live tabs (differential). |
| `beat-attended` | The last `usage_audit` row for the job is `completed`, not `refused_before_inference`. |

```toml
# ~/code/33GOD/pjangler/contracts/atoms/project.identity.v1.toml  (owner repo: contract + live probe)
[atom]
name = "project.identity"
major = 1
minor = 1                     # 1.1 adds memory_bank
owner = "pjangler"
interface = { http = "GET http://127.0.0.1:8764/v1/resolve?cwd={cwd}", cli = "pj project resolve --json --cwd {cwd}" }
returns = { project_id = "string", root = "path", memory_bank = "string", board = "string?" }
[[probe]]                     # run against the live box; no fixtures
cwd = "~/code/33GOD"
expect = '.project_id == "33god" and .memory_bank == "33GOD"'
[[probe]]
cwd = "~/code/33GOD/pjangler/.worktrees/PJAN-165-import"   # a linked worktree resolves to its main repo
expect = '.project_id == "pjangler"'
```

```toml
# ~/.agents/features.toml  (delorenj/agents)
[host.big-chungus]
jev-clairic = "^0.9"
crank = "^0.4"
hindsight-hooks = "^1"
[host.mac]
hindsight-hooks = "^1"        # crank declares platforms = ["linux"]
```

## 3. Installing crank on a fresh box

Starting point:

- 33GOD is cloned with its submodules.
- pj is installed, the Candybar daemons are up, and the :8764 registry is up.
- Redis is on :6379, the zellij session is running, and the op service token is present.
- Hermes profile 33god-pm exists as a real directory. Creating it is flume's job, not crank's.

```
$ pj feature add crank
resolve   crank -> ~/code/33GOD/crank (submodule, initialised) @3f1c2ab v0.4.0
desired   ~/.agents/features.toml [host.big-chungus] += crank "^0.4"   (commit + push on --apply)
atoms     live probes; contract owner in brackets
  pane.topology@1     pj crank panes --json        PASS  provisional  [owner deckard: deckard mux panes† ABSENT]
  agent.process@1     pj crank panes --json        PASS  provisional  [owner deckard]
  agent.session@1     pj crank panes --json        PASS  provisional  [owner bloodbank: asmctl scope† ABSENT]
  project.identity@1  GET :8764/v1/resolve         PASS  [owner pjangler]  probe 33god/33GOD ok
  agent.job@1         hermes cron status --json    PASS  [owner hermes-agent]
  clock@1             candybar :8700               PASS  [owner candybar]
  jev.calls@1         feature jev-clairic          PASS  (installed earlier in this converge)
claims    zcrank:* 0 · paths 0 · hermes crank-* 0 · candybars project:crank 0     clean
lint      0 forbidden strings in crank/** and declared consumers
plan      (state, links, job, stub, skill, then the clock LAST)
  1 dir    + ~/.local/state/zcrank/
  2 links  + 8 ~/.local/bin/{zcrank.py,zcrank_identity.py,zcrank_attendance.py,zcrankctl,
                             zcrank-gate,zcrank-gate.py,crank-watchdog,zcrank-act}   (bin/* glob)
  3 job    + hermes -p 33god-pm cron create --name crank-beat --scheduler external  (hermes/jobs/crank-beat.toml)
  4 stub   + 33god-pm/scripts/zcrank-gate.sh   (rendered; input job_id from step 3)
  5 skill  + skillex select crank-engine; skillex profile sync 33god-pm --skillex-only
  6 clock  + candybar register --update --prune   (cwd crank/): crank-beat, crank-watchdog
dry run. --apply to act.

$ pj feature add crank --apply
journal ~/.local/state/33god/features/crank.journal
 1 ok  dir     ~/.local/state/zcrank/
 2 ok  links   8/8                                     re-audit bins-complete ok
 3 ok  job     crank-beat -> 5d0e9a71c2f4              id written to receipt only
 4 ok  stub    zcrank-gate.sh sha256 9e1c...            re-audit stubs-fresh ok
 5 ok  skill   crank-engine -> 33god-pm (activation v2/ab12...)
 6 ok  clock   crank-beat 01b3..., crank-watchdog 01b3...  tag project:crank   doctor --live ok
checks  ok bins-complete  ok stubs-fresh  ok profile-clean  ok job-by-name  ok candybars-synced
        ~  watchdog-report-fresh (pending run)   ~ beat-attended (pending tick)
receipt ~/.local/state/33god/features/crank.json
git     delorenj/agents "feat(features): crank on big-chungus" pushed

$ candybar run crank-watchdog --wait                  # Candybar policy: one terminal invocation, then its effect
crank-watchdog  ok
$ pj feature check crank --prove
  ok watchdog-report-fresh  watchdog.json.local-report.json v1, 6s old
  ok beat-attended          crank-beat tick 14:05 usage_audit outcome=completed
$ cd ~/code/acme && pj crank enable --interval 1h      # enrollment stays runtime state in the claimed namespace
```

If a step fails, the journal unwinds the completed steps in reverse. The clock is last, so a half-install never fires. The new job id 5d0e9a71c2f4 propagates nowhere: Candybar, the gate, `engine.ts` and the skill all address `crank-beat`. The install writes to one repo only, delorenj/agents, for the desired-state line.

## 4. Upgrade, then rollback

I-8's pane-bound registry lands in pjangler, and deckard-mux ships its CLI with PJAN-202's (pid, starttime, comm) cache key.

```
$ git -C ~/code/33GOD submodule update --remote crank pjangler && git -C ~/code/deckard pull
$ pj feature plan
crank 0.4.0 (3f1c2ab) -> 0.5.0 (8be07d1)
atoms   + pane.binding@1   GET :8764/v1/bindings    PASS [owner pjangler]
        agent.process@1    deckard mux agents --json  PASS -> relock provisional pjangler -> owner deckard
                           differential pj crank panes vs deckard: 23/23 live panes agree
steps   (clock FIRST off, LAST on)
 1 clock  candybar pause crank-beat crank-watchdog
 2 state  export zcrank:* (31 keys) -> ~/.local/state/33god/archive/crank-0.4.0.jsonl
          migrations/0005-tab-to-binding.py: 10 tab keys -> 7 bindings;
          3 match no live pane (client-portal, Holocene, james-brennan-techj): export only
 3 links  + zcrank-bind (bin/* glob diff)   = 8 unchanged, targets are source
 4 stub   = zcrank-gate.sh (same inputs)     <- the copy that used to rot
 5 job    ~ crank-beat prompt 41c0 -> 7aa1  (hermes cron edit crank-beat --prompt ...)
 6 clock  candybar register --update --prune; resume
$ pj feature apply
checks 8/8 ok   binding-agreement: zcrankctl, pj crank, deckard agree on 7/7 live bindings
lint   ok: index.ts canon/candidateNames removed; the fingerprint for the tab-name rule is gone
```

There is no rollback verb, because main is production. A rollback is `git -C crank revert 8be07d1 && git push && pj feature apply`. The `state` driver sees the schema go from 2 back to 1 and replays `crank-0.4.0.jsonl` through the migration's `down`.

## 5. Uninstall

```
$ pj feature remove crank --apply
consumers  pjangler pj crank (optional crank.binding) -> prints "crank is not enabled on this host"
           wingman sources/fleet.py reads zcrank:* (fingerprint hit, undeclared) -> advisory
 1 clock   candybar pause + archive crank-beat, crank-watchdog (ids from receipt)   doctor --live: 0 native clocks
 2 job     hermes -p 33god-pm cron remove 5d0e9a71c2f4 (receipt id; name still matches)
 3 stub    rm scripts/zcrank-gate.sh (sha == receipt; a foreign edit is quarantined, not deleted)
 4 skill   skillex deselect crank-engine; profile sync prunes owned links only
 5 links   rm 9 links (dev/ino and target match)
 6 state   export -> ~/.local/state/33god/archive/crank-0.5.0.jsonl
           SCAN MATCH zcrank:* + DEL per key on redis-cli -p 6379 (never FLUSH*); rm -r ~/.local/state/zcrank/
sweep      the claims, re-read from the world rather than the receipt
  redis zcrank:*                         0
  ~/.local/bin/zcrank*, crank-*          0
  33god-pm/scripts/zcrank*, crank-*      0
  33god-pm/skills/**/crank-*             1  devops/crank-watchdog-adversarial-review (curator-made, no receipt) -> archived
  hermes jobs crank-*                    0
  candybars project:crank (active)       0
result     ABSENT ok   (pj feature check crank --absent exits 0)
kept       jev-clairic (desired in its own right)
desired    ~/.agents/features.toml -= crank   committed + pushed
stays      pj crank compiled into pj; bloodbank crank.* schemas (owned by Wingman); git history
```

## 6. Second feature: hindsight-hooks, reusing project.identity

```toml
# ~/code/33GOD/bloodbank/features/hindsight-hooks/feature.toml
[feature]
name = "hindsight-hooks"
version = "1.0.0"
owner = "delorenj/bloodbank"
scope = "host"
[requires]
"project.identity" = "1"      # needs minor 1.1 (memory_bank); crank's "1" is unaffected
"agent.hooks"      = "1"
"agent.session"    = "1"
[claims]
hook_handlers = ["hindsight-*"]   # rows bloodbank already owns in hook-hub/handlers.toml; no new loader
paths         = ["~/.local/state/33god/hook-hub/bank-exists.json"]
candybars     = ["feature:hindsight-hooks"]   # needs Candybar tag-scoped prune (bloodbank hosts several features)
```

The feature also moves four manifests into `bloodbank/features/hindsight-hooks/.candybars/`: `hindsight-capture-sweep`, `hindsight-memory-analysis`, `hindsight-template-sweep` and `hindsight-write-probe`. They come out of `candybar/deploy/migration/manifests/`. `register --update` adopts their live rows.

```
$ pj feature add hindsight-hooks --apply
atoms  project.identity@1  GET :8764/v1/resolve   LOCKED (shared with crank)   probe memory_bank ok
       agent.hooks@1       bloodbank sync.py --check                PASS [owner bloodbank]
       agent.session@1     pj crank panes --json (provisional)       LOCKED (shared with crank)
plan   = handler rows recall, briefing, turn, retain, session-end   lint: every command path exists
       + candybar adopt x4 (tag feature:hindsight-hooks)
$ pj feature why project.identity
owner      pjangler   contracts/atoms/project.identity.v1.toml (33god-platform components/pjangler.yaml)
provider   GET 127.0.0.1:8764/v1/resolve   probe pass 14:02Z
consumers  crank "1", hindsight-hooks "1", deckard-attention "1" (builtin fallback)
retire     fingerprint hits: zcrank_identity.py:61, pjangler index.ts:483, bloodbank board.py board_for,
           deckard projects.rs:203, hindsight.py:201 resolve_bank
```

The reuse is real, not cosmetic:

- `resolve_bank`'s ladder (override file, env, origin remote, checkout name) moves once into the registry as `memory_bank`.
- `concerns.py` calls `/v1/resolve` with a 1s timeout and caches the answer the way it caches `bank-exists.json`.
- A consumer that used `project_id` would write to `33god`. That bank was deleted in the 2026-08-17 consolidation, so the write would silently create a new, empty one.

A third feature, deckard-attention, binds pane.topology, agent.state and project.identity with builtin fallbacks, and reads `crank.binding` as an optional atom.

## 7. Atom ownership

| Atom | Owning repo | Interface | Duplicate copies to retire |
|---|---|---|---|
| pane.topology@1 (session, tab_id, pane_id, cwd, terminal pid; readiness-gated) | deckard (crates/deckard-mux) | `deckard mux panes --json`†, a socket over the daemon's PaneMap with a direct-read fallback. Provisional: `pj crank panes --json` (pjangler, dd9eb4e). | zcrank.py:249 zj, :260 panes_for, :269 tab_owners; zcrank_identity.py:107 owners_from_panes, :156 resolve_panes; zcrankctl:146 zj, :156 panes_with_number, :201 live_tabs; pjangler index.ts:401 liveTabs, :430 livePanes, :598 resolvePaneCwds, plus the shared pane-cwds.json cache. panes.ts readPaneTable becomes a client. |
| zellij invocation (env unset, timeout, readiness) | deckard-mux | `deckard mux zj -- <args>`† | The per-copy `env -u ZELLIJ -u ZELLIJ_SESSION_NAME` in zcrank.py, zcrankctl, index.ts, asm-tabpaint and crank-engine SKILL.md. |
| agent.process@1 | deckard-mux proc.rs plus `data/agent-clis.toml` | `deckard mux agents --json`†. Provisional: `pj crank panes --json`. | pjangler panes.ts:41 AGENT_CLIS (moves to reading the TOML); bloodbank agents.py AGENT_COMMS; Deckard's pid-only cache key (replaced by (pid, starttime, comm)); zcrank.py:235-246 screen-scrape detection. |
| agent.session@1 | bloodbank (agent-hooks core/asm.py) | `asmctl scope --json --pid P --starttime S`†, procStart-validated | panes.ts:365 readClaudeSession (becomes a client); deckard attribution.rs fallback ladder. |
| agent.state@1 | bloodbank ASM | `asmctl state --json`† and `bloodbank.evt.agent.*` | zcrank.py:327 classify (kept as fallback only); holocene deckard-state.ts port. |
| project.identity@1 | pjangler (registry :8764) | `GET /v1/resolve?cwd=`† and `pj project resolve --json`† | zcrank_identity.py:61; pjangler index.ts:483 projectIdentity; bloodbank board.py and agents.py board_for; deckard projects.rs:203; hindsight.py:201 resolve_bank; concerns.py repository(). |
| crank.binding@1, then pane.binding@1 | crank now; pjangler registry after I-8 (its delegation) | `zcrankctl keys --json`†, then `GET /v1/bindings`† | zcrank.py:120-161 tab_keys_for and crank_enabled; zcrankctl:74-119 stored_keys; pjangler index.ts:90 canon, :722 candidateNames, :761 resolveTabForProject; crank-watchdog.py:44 canon; Wingman fleet.py. |
| tab marker set | bloodbank (asm-tabpaint) | `markers.toml`† as data; deleted once bindings are by id | Regexes at zcrank.py:79, zcrankctl:55, zcrank-gate.py:75, index.ts:69 and crank-watchdog.py:44. |
| pane.input@1 | deckard-mux | `deckard mux send --pane P --expect pid:starttime --when idle`†. Provisional: `zcrank-act`†. | Raw `zellij action write-chars`/`send-keys` in crank-engine SKILL.md:36-37. |
| tab.focus@1 | deckard-mux | `deckard mux focus --json`† (go-to-tab-by-id) | zcrankctl:218 resolve_tab fuzzy prefix, as used for navigation. |
| agent.job@1 | hermes-agent fork | `hermes cron status <name> --json`†, plus `HERMES_CRON_OUTPUT_DIR`† in the monitor env | pjangler engine.ts:12-14, :110 and :208-218 (the admit() copy and ENGINE_DEFAULT_JOB_ID); zcrank-gate.sh:8 id path; candybar launch.py:16 JOB_ID. |
| clock@1 | candybar | `.candybars/*.candybar.toml`, `register --update --prune`, `transition-exec`† | candybar/deploy/migration/manifests/crank-*; CAND-49 launch.py, activate.py and the pinned image; Hermes job 061c4dbedc1c. The due-math copies (zcrank.py CRON/GRACE, index.ts ZCRANK_CRON_SECONDS) read the schedule from the manifest instead. |
| agent.hooks@1 | bloodbank agent-hooks | hooks.master.json and `sync.py --install/--check` | deckard hooks.rs fallback installer; orca claude-hook.sh. |
| jev.calls@1 | delorenj/agents (jev-clairic feature) | `jev_clairic_calls.py` on PATH, with an env-file of op:// refs | `~/.config/jev-clairic/typesafe.key` and its `.direct.bak`, both plaintext. |
| zcrank Redis schema | crank | `schemas/redis/zcrank.v1.toml` | pj writing zcrank:log states by hand (the engine's exclusion list at zcrank.py:65); the crank-engine SKILL.md Registry section. |

## 8. Each drift item, its killer, and the check that keeps it dead

| Drift | Killer | Check that catches it |
|---|---|---|
| Stale profile `zcrank.py` | The watchdog runs from the checkout under `candybar transition-exec`. The profile holds only stubs. | `profile-clean` |
| Missing `zcrank_identity` and `zcrank_attendance` links | The `bin/*` glob is the list. | `bins-complete` |
| Orphan `zcrank-scan.sh` | Adopted into the repo (`hermes/`) in slice 1, then retired along with the skill/prompt conflict. | `profile-clean` |
| `777c511a009c` and `'Workspace'` | Jobs are addressed by name. The topology provider owns the session. | `job-by-name` and `[lint] forbidden` |
| Four copies of the tab-key rule | One `crank.binding` provider, then the pjangler `pane.binding`. | `binding-agreement` and fingerprints |
| Candybar manifests in the wrong repo | `register --update` adopts the rows into `project:crank`. | `candybars-synced` |
| Drift between audits | An hourly Candybar row runs `pj feature check --all --emit` and publishes `bloodbank.feature.drift.detected`†. | n/a |
