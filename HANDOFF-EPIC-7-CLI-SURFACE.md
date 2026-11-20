# Handoff: Epic 7, the 33GOD CLI Surface

**To:** Grolf (33god-pm), the owner of Epic 7
**From:** the skillex agent session for Jarad, 2026-11-19
**Status:** Epic 7 is in progress. Story 7.1 (step 1) is built and waiting for your verdict. Stories 7.2 to 7.7 are in your Backlog.

Call it **"Epic 7: 33GOD CLI Surface"** or **cli-surface**, which is its candidate key in `features.toml`. On Plane it is **33GOD-101**.

---

## 1. What this is, in one paragraph

33GOD has many component command-line tools (`pj`, `px`/`pilot`, `flume`/`fl`, `krebs`, `skillex`, `candybar`, `candystore`, `bb`, `wax`, `waybill`, `hermes`). Each one is installed, pinned and described differently. Jarad asked how the AWS CLI drives many services through one `aws` command, and whether 33GOD should copy that.

The answer we adopted is **not** one big dispatcher. Each component keeps its native binary as the canonical name and follows one shared contract:

- It is on PATH with a pinned runtime.
- It describes itself through the jdx `usage` spec.
- It speaks one JSON envelope (a superset of skillex v2).
- It uses one exit-code table.

A thin `33god` command does discovery and health only (`ls`, `where`, `versions`, `doctor --all`, `describe`). It is not a passthrough. That is the AWS shared-core idea without AWS's single codebase.

**Belsky level:** every 33GOD component CLI, not just the one that broke.

## 2. Where it lives (it is NOT spread across components)

All planning and tracking lives in this repo, the 33GOD root. Component repos hold only the code each story changes in that component.

| What | Path (relative to `~/code/33GOD`) |
|------|-----------------------------------|
| This handoff (start here) | `HANDOFF-EPIC-7-CLI-SURFACE.md` |
| Why: research (AWS internals, inventory, critique, verdict) | `_bmad-output/planning-artifacts/research/cli-surface-research-2026-11-19.md` |
| Decision record: Sprint Change Proposal | `_bmad-output/planning-artifacts/sprint-change-proposal-2026-11-19.md` |
| Architecture: AD-1 to AD-10, all ADOPTED | `_bmad-output/planning-artifacts/architecture/architecture-33GOD-2026-11-19-cli-surface/ARCHITECTURE-SPINE.md` |
| Epic and story breakdown | `_bmad-output/planning-artifacts/epics.md` → "Epic 7" |
| Sprint state | `_bmad-output/implementation-artifacts/sprint-status.yaml` → `epic-7` block |
| Story 7.1 spec plus evidence (Dev Agent Record) | `_bmad-output/implementation-artifacts/spec-7-1-resolve-and-runtime-pin-every-component-cli.md` |
| Feature inventory entry | `features.toml` → `[candidate.cli-surface]` (F1: inventory, not authorization) |
| The installer Story 7.1 built | `33god-platform/scripts/cli-launchers.py` and `33god-platform/cli-launchers.toml` |
| Operator docs | `33god-platform/README.md` → "Component CLIs on PATH"; the `33god-hub` skill → Commands |

**Plane board (33GOD):**

| Ticket | What |
|--------|------|
| 33GOD-101 | Epic 7 |
| 33GOD-102 | Story 7.1: resolve and runtime-pin every component CLI (**awaiting your verdict**) |
| 33GOD-103 | 7.2: adopt the `usage` spec as the self-describe contract |
| 33GOD-104 | 7.3: one JSON envelope and one exit-code table |
| 33GOD-105 | 7.4: `33god` discovery and health |
| 33GOD-106 | 7.5: argv guards unwrap `33god` (prerequisite for any passthrough) |
| 33GOD-107 | 7.6: retire `skills:sync` and pure-alias mise tasks (deploys stay) |
| 33GOD-108 | 7.7: generated hub-skill command blocks from usage specs |
| 33GOD-109 | 7.1 follow-up: sweep per-repo `npm:@delorenj/skillex` mise pins, then uninstall skillex 0.1.3 |
| 33GOD-110 | 7.1 follow-up: drop `agents/hermes/pm` from `_.path` in about 91 repos (client repos need Jarad) |
| 33GOD-111 | 7.1 follow-up: pjangler's skillex library at 0.4.4, the hard-coded node path in pjArgv, the `npm i -g` hint |
| 33GOD-112 | 7.1 follow-up: flume's `github:delorenj/skillex#f51ff3e` pin needs an F3 reason and exit ticket |
| 33GOD-113 | 7.1 follow-up: `check` should flag CLIs shadowed by npm's default prefix |

**Ordering** (from epics.md):
1. 7.1 goes first.
2. 7.2 blocks 7.7.
3. 7.5 must land before any `33god` passthrough.
4. 7.3 and 7.6 roll out one component at a time, most-called first.

## 3. What Story 7.1 delivered

1. **Launchers.** `cli-launchers.py install` writes `~/.local/bin` wrappers that exec the pinned node 24 (`~/.local/share/mise/installs/node/24/bin/node`) on each CLI's entry file. It covers pj, pjangler, pjangler-mcp, pjangler-prompt, px, pilot, px-supervised, flume, fl, krebs and skillex. `hermes-pm` is declared as a symlink entry. Python CLIs (candybar, candystore, bb, wax, waybill) are probed.
2. **One npm install path.** npm-distributed CLIs install under prefix `~/.local`, and no launcher path contains a version folder (an `E_VERSIONED_PATH` guard enforces this). The global mise `npm:@delorenj/skillex` tool was removed (zshyzsh `d67984c`); its shim shadowed the launcher and broke skillex in node<24 repos.
3. **`upgrade <pkg...>|--all`** installs with the pinned node's npm and then rewrites the launchers. A bare `npm i -g` deletes them.
4. **`check` / `--check`** confirms the launchers are in sync, runs `node --check` on every entry, and probes every CLI in three environments: minimal PATH, decoy node plus a node-20 pin, and `mise exec` plus a node-20 pin. The last one fails on the old broken setup. Exit 0 means ok; exit 6 means drift.
5. **krebs-tick** (Candybar) runs `~/.local/bin/krebs tick --json`; 60 of 60 scheduled runs succeeded.
6. **hermes.** Bare `hermes` is the one global Hermes. PM-desk scoping is `hermes-pm` (hermes-agent-template `bin/hermes-pm`).
7. **pjangler 1.5.57.** `pj skills` execs the skillex on PATH, and `pj skills --version` matches `skillex --version`, both 0.4.10.

**Commits:**

| Repo | Commits |
|------|---------|
| 33GOD | `8251d2b`, `ccfd430`, `d179248` (and the lock-in `7f3eafd`) |
| krebs | `8d81df9` |
| hermes-agent-template | `268370d` |
| pjangler | `c0538f5`, `c7e72f9` |
| skillex | `e893edc`, `4641145` |
| zshyzsh | `d67984c` |

**Verify it yourself in 10 seconds:**

```bash
python3 ~/code/33GOD/33god-platform/scripts/cli-launchers.py --check   # exit 0
cd ~/code/chorescore && mise exec -- skillex --version                 # 0.4.10, not E_NODE_VERSION
```

## 4. Decisions that are yours

1. **The verdict on 33GOD-102.** AC1, AC2, AC3, AC4 and AC6 are met. **AC5 is partial:**
   - pjangler deliberately keeps `@delorenj/skillex@0.4.4` as a library for its parity audit. The AC says to remove it, and bumping it breaks 5 suites.
   - Per-repo `npm:@delorenj/skillex` mise pins still win in those repos (intelliforia gets 0.1.3). That work is in 33GOD-109.
   - flume's sha pin is reported but has no F3 exit ticket yet (33GOD-112).

   Accept these as follow-ups, or reopen the story.
2. **The Epic 7 Director Rule exception.** The sprint-status note says not to run bmad-loop in this repo, and each child repo's code lands in that child. Confirm or change it.
3. **What to queue next.** The recommendation is **7.2** (the usage spec). It unblocks 7.7 and gives `33god describe` something to read. **7.5** is a cheap, independent prerequisite you can run in parallel.

## 5. Needs Jarad (not yours to decide)

- The 33GOD-110 sweep touches client repos (james-brennan, ipm-prod, client-portal). Get Jarad's go-ahead first.
- zshyzsh `cd5b849` swept unrelated live config edits in with a skillex change. Jarad should review it.

## 6. Known risks

- Long-lived agent sessions started before 2026-11-19 keep stale PATH entries (`.../npm-delorenj-skillex/latest/...`, `<repo>/agents/hermes/pm`). Restart a pane if it misbehaves.
- npm's default global prefix (`installs/node/24.6.0/bin`) comes before `~/.local/bin` in login shells. A bare `npm i -g @delorenj/pjangler` would shadow `pj`, and `check` stays green (33GOD-113).
- Nothing runs `check` on a schedule. If you want that, it must be a Candybar job, not a new timer.
