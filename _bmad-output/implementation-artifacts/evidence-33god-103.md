# 33GOD-103 — Story 7.2 usage self-description evidence

Status: implementation landed in ten native owners; independent review and ticket transition remain with the parent PM. No board writes, envelope changes, passthrough, scheduler changes, or `33god.cli/1` schema were made.

## AC1 — tool upgrade before conversion

`mise exec -- usage --version` returned `usage 7.4.0` (was 3.3.0 before this story; current release checked before conversion).

## AC2 — exporter compatibility before dependence

The four isolated probes in `/home/delorenj/.hermes/profiles/33god-pm/cache/scratch/33god-103/` generated actual `.usage.kdl` files and corresponding JSON with `usage generate json`; `usage lint` exited 0 for each:

| Exporter | Pinned probe | Outcome |
| --- | --- | --- |
| `@usage-spec/commander` npm | 1.1.0 | KDL parses on usage 7.4.0; actual Skillex exporter omits registered `help`/`version` options, restored in its adapter. |
| `argparse-usage` PyPI | 0.1.1 | Minimal argparse KDL parses; static snapshots used for bb, candystore, waybill and wax to avoid runtime dependencies and side-effectful parser imports. |
| `usage-spec-typer` PyPI (`typer_usage`) | 1.2.1 with Typer 0.27.3 | Minimal and actual Candybar snapshots parse; incompatible with Typer 0.29.2 (`TyperOption.type` error), so Candybar retains its 0.27.3 pin and a shipped static snapshot. |
| `clap_usage` crate | 5.0.0 | Minimal Rust clap KDL parses; no owner in this story uses clap. |

Probe outputs: `commander.usage.kdl`, `argparse.usage.kdl`, `typer.usage.kdl`, `clap.usage.kdl`, plus `.json` counterparts. No component depends on an unverified exporter.

## AC3–4 — native owner inventory

Every listed emitted KDL was compared with its checked-in snapshot where applicable, then `mise exec -- usage lint -q <file>` and `usage generate json -f <file>` exited 0. `usage lint` info messages about missing optional help text are non-fatal. Root names in all ten specs remain the native names.

| CLI | Owner file and verification | Owner feature commit URL | Test result |
| --- | --- | --- | --- |
| px | `pilot/src/usage.js`, `pilot/bin/pilot.js`, `pilot/test/usage.test.js`; generated from COMMANDS/FLAGS/ALIASES; parser and mutation parity | https://github.com/delorenj/pilot/commit/7d0abcb645063484d2a6bd7fbc96d93c6e5d885e | `npm test`: 520 passed, 1 pre-existing heartbeat skip |
| skillex | `src/cli.ts`, `src/usage.ts`, `tests/node/usage.test.mjs`; Commander parity and real usage parser | https://github.com/delorenj/skillex/commit/0e44d81459d74fbc47314f6dee6c850176239123 (main descendant) | Node `npm test`: 1339 passed, 1 skipped; build/typecheck/lint passed. Pre-push legacy Python hook failed unchanged baseline `tests/unit/test_sync_aliases.py`; hook exclusion recorded when publishing. |
| pj | `pjangler/pj.usage.kdl`, `scripts/export-usage.mjs`, `src/index.ts`; parser-derived snapshot; `node scripts/export-usage.mjs --check` includes mutation probe | https://github.com/delorenj/pjangler/commit/20fc2b5e09e8986f6ff4138ccec9d9d57c9a4e02 | `npm test`: 130 passed, 0 failed, 1 pre-existing quarantined-failing; `npm run typecheck`, build passed |
| flume | `flume/packages/flume-hr/src/index.ts`; direct Commander export and `tests/usage-spec.test.mjs` | https://github.com/delorenj/flume/commit/fbc4204bda9a22cf21795025a1ce3b7e794d7efd | Focused test 1 passed, typecheck/build passed; full suite after template submodule initialization still had unrelated fixture failures and was stopped after >20 minutes; initial run 24 passed/35 failed because template submodule absent. |
| krebs | `krebs/krebs.usage.kdl`, `krebs/bin/krebs.mjs` (root-owned) | https://github.com/delorenj/33GOD/commit/f1297e1 | `node --test krebs/tick/test/*.test.mjs`: 83 passed (after building the pinned bloodbank n8n dist in isolated root worktree) |
| candybar | `candybar/src/candybar/cli/candybar.usage.kdl`, `scripts/export_usage.py`, `src/candybar/cli/main.py`; Typer snapshot `uv run python scripts/export_usage.py --check` | https://github.com/delorenj/candybar/commit/4b48e570f1dbe94fbb4b965ac2f4d989ca71bfc3 | CLI focused 156 passed; full pytest 2178 passed, 80 skipped, 10 failed in unrelated scheduling/context tests |
| bb | `bloodbank/cli/bb.usage.kdl`, `cli/bb.py`; static argparse snapshot | https://github.com/delorenj/bloodbank/commit/ed7c4b41e58a71a5e94976e99852b8b7136894da | `python3 -m py_compile cli/bb.py` passed; no matching bb unit suite located |
| candystore | `candystore/candystore/candystore.usage.kdl`, `candystore/cli.py`; static argparse snapshot | https://github.com/delorenj/candystore/commit/658e3742061fec2d6ad26ad2ffb68ddb688d3c3b | `uv run pytest -q`: 155 passed, 60 skipped |
| waybill | `33god-platform/waybill/waybill/waybill.usage.kdl`, `waybill/cli.py` (root-owned) | https://github.com/delorenj/33GOD/commit/44f6892 | CLI unittest: 34 passed; full unittest: 312 passed, 1 pre-existing `test_night` registry-summary assertion failed |
| wax | `/home/delorenj/HeyMa/components/wax/wax.usage.kdl`, `components/wax/bin/wax`; static argparse snapshot | https://github.com/delorenj/HeyMa/commit/37cd0b74357c817136a339ffbfad696cd1901fca | `/usr/bin/python3 -m unittest discover -s components/wax/tests -p '*cli*test*.py' -q`: 74 passed |

The static KDL files are the checked-in source for bb, candystore, waybill and wax. For pj, `node scripts/export-usage.mjs` regenerates from its Commander table; for candybar, `uv run python scripts/export_usage.py` regenerates from its Typer table. px and skillex export live from their registered authority. Flume exports live from its registered Commander tree.

## Review repair — 2026-11-19

The independent review correctly found lossy px positionals and location-dependent generated defaults. Those source gaps are repaired on child main; PATH installation is a separate, still-partial acceptance surface.

### Corrections and current commits

- **px:** dispatch authority now includes named positionals for every argument-bearing command; no help-text extraction or `arg1` fallback. The exporter preserves runtime cardinality, including optional variadic `NAME` for board create (`--name` alternative), optional title with a managed-only `--file` explanation, `idea --desired`, optional variadic move state, required epic refs, optional task status ref and operation-dependent run ref. Alias parity checks names, requiredness and variadic bits; mutations flip each and must fail. Runtime parsing, dispatch and zero-runtime-dependency policy are unchanged. https://github.com/delorenj/pilot/commit/0fd60dd87bb4b05c2278a8e6f594242afa292be3
- **pj:** all 16 cwd-derived defaults normalize to `.` with explicit current-directory help, preserving literal defaults and real package-version drift. The snapshot is regenerated at **1.5.61**, including the release that advanced main during repair. A registered hermetic regression compares repo and unrelated cwd output; canonical/worktree source exports were also byte-compared. https://github.com/delorenj/pjangler/commit/0babafd2e0b93b0bbb7cd70fb89a848f471a6bea (initial adapter repair: https://github.com/delorenj/pjangler/commit/876d735be1948e362b5ddf695d473255a23446b4)
- **Candybar:** the exported doctor policy default uses `<candybar-install>/deploy/scheduling-policy.json`, not an absolute worktree path. This is a documentation placeholder for the bundled resource, not a cwd-relative runtime change. The regression copies real source to two independent install roots and compares both rendered specs to the shipped snapshot, then runs the usage parser. No scheduling/policy runtime code changed. https://github.com/delorenj/candybar/commit/a7d53448fe20350cb89a277fc8f960528fb44bf5
- **Flume:** no tracked change was needed. The stale local build first failed because its declared `@usage-spec/commander` dependency was not installed; `npm install --ignore-scripts --no-audit --no-fund` added 3 packages with no tracked manifest/lock diff, and `npm run build` refreshed dist. https://github.com/delorenj/flume/commit/fbc4204bda9a22cf21795025a1ce3b7e794d7efd

### Executed checks

| Command / surface | Actual result |
| --- | --- |
| Pilot `node --test test/usage.test.js` | 5 passed, 0 failed; real usage lint/JSON plus mode guards and argument mutations |
| Pilot `npm test` rerun | 529 tests: **528 passed, 0 failed, 1 skipped**, exit 0, 10.14 s |
| Pilot first full run | 527 passed, 1 failed, 1 skipped: randomized Trello 24-digit fixture interpreted as numeric ref (`no ticket TT-6.000006165573496e+23`); unchanged code passed rerun; not hidden as a clean first run |
| PJangler `node --test tests/usage-portability.test.mjs` | 1 passed, 0 failed; run on worktree and canonical checkout |
| PJangler `node scripts/check-hermetic-test-env.mjs` | PASS: 130 registered suites start from preamble, 0 exceptions |
| PJangler `node scripts/export-usage.mjs --check` | `pj usage snapshot matches parser`, exit 0 on canonical and worktree at 1.5.61; command-mutation drift probe passed |
| PJangler canonical/worktree `--stdout` exports + `cmp` | Byte-identical; all 16 cwd defaults portable |
| PJangler isolated `npm run build`; `node dist/index.js --usage-spec` + `cmp pj.usage.kdl` | Build and exact emitted snapshot comparison passed |
| Candybar `uv run python scripts/export_usage.py --check` | `candybar usage snapshot matches Typer commands`, exit 0 on canonical; explicit source-path invocation also passed in worktree |
| Candybar `python -m pytest -q tests/test_usage_portability.py` | **1 passed** on both canonical and worktree; separate install roots and cwd, usage lint/JSON passed |
| Flume `npm run build`; `mise exec -- node --test tests/usage-spec.test.mjs` | Build passed; **1 passed, 0 failed** |
| Actual PATH `flume --usage-spec`, `px --usage-spec` | Native KDL emitted; usage lint and JSON generation exited 0 |
| Skillex checkout `npm run build`; `mise exec -- node --test tests/node/usage.test.mjs`; `node dist/cli.js --usage-spec` | **2 passed, 0 failed**; actual Commander parity/mutation and terminator checks; emitted KDL lint/JSON passed |
| Repaired pj and Candybar KDL | usage 7.4.0 lint + JSON generation exit 0; optional-help info messages are non-fatal |

Bounded raw outputs and emitted KDL/JSON are in the existing scratch directory `33god-103/`, including `pilot-repair-full.log`, `pilot-repair-full-rerun.log`, `px-repaired.*`, `pj-final.json`, `pj-canonical.usage.kdl`, `pj-worktree.usage.kdl`, `pj-built-final.usage.kdl`, `candybar-repaired.*`, `flume-rebuilt.*` and `skillex-checkout.*`. Original four-exporter probes were not repeated. Full Flume/Candybar suites were deliberately not rerun.

### Remaining installed-distribution limitation

`skillex --usage-spec` on PATH still exits 2 with `E_USAGE: unknown option '--usage-spec'`. The installed package and `npm view @delorenj/skillex version` both report **0.4.10**. `cli-launchers.py upgrade skillex --dry-run --json` resolved the supported plan to `@delorenj/skillex@latest`, i.e. that same release; reinstalling it cannot supply the source-main feature. The checkout at https://github.com/delorenj/skillex/commit/4800fe51079d1d357f003fcc3e9b41150969a5a8 is verified, but installed-PATH acceptance is **not passed**. No npm publication, version/tag change, launcher hand-edit or distribution-policy change was authorized or performed. PJangler's npm PATH package is likewise not upgraded here: actual `pj --usage-spec` exits 1 with `error: unknown option '--usage-spec'`. Its canonical source and freshly built isolated dist are verified above; installed pj PATH acceptance is also not passed.

Only pilot, pjangler and Candybar root gitlinks are advanced by this repair; Flume's pointer is unchanged. Unrelated root WIP and PJangler `src/project/boardQuery.ts`, `tests/pjan-87-board-read-regressions.mjs`, `tests/pjan-120-credential-parity.mjs` remain untouched. `git unpushed` was run once and saved to `unpushed-repair.log`; its other owners' work was not altered. Repair branches were pushed, merged to child main and their own worktrees removed. Board state, comments and assignments remain solely with the parent PM.

### Installed native distribution — local committed-main tarballs (2026-11-19)

The previously open installed-PATH limitation is closed **locally**, without publishing to npm, changing a version/tag, editing package distribution policy, or changing the launcher registry. Clean independent worktrees built commits `skillex` `4800fe51079d1d357f003fcc3e9b41150969a5a8` and `pjangler` `0babafd2e0b93b0bbb7cd70fb89a848f471a6bea` with pinned Node 24.15.0/npm 11.12.1: `npm ci --ignore-scripts`, `npm run build`, and `npm pack --ignore-scripts --pack-destination "$TMPDIR"` all exited 0. Both worktrees remained source-clean. The npm tarballs had these SHA-256 hashes (the scratch copies are temporary, not published artifacts):

| Local tarball | SHA-256 | Packed source |
| --- | --- | --- |
| `delorenj-skillex-0.4.10.tgz` | `b015eefbaa85e8d3859c2cff1889e0ff7c2f232c8319fac52576dbdd4fd2edbf` | Skillex `4800fe51079d1d357f003fcc3e9b41150969a5a8` |
| `delorenj-pjangler-1.5.61.tgz` | `ccc3980309e11a6a47a2b6e707981b9276aa12586e70a41d15eae43ff5f79b2a` | PJangler `0babafd2e0b93b0bbb7cd70fb89a848f471a6bea` |

Inspected npm's package contents: Skillex includes `dist/cli.js`, `dist/index.js`, package metadata and its declared `@usage-spec/commander` runtime dependency; PJangler includes all four declared executable entries and both `pj.usage.kdl` and `dist/pj.usage.kdl`, whose SHA-256 equals the committed snapshot `0873475b311145432daf51f67937dff0e58a4d6ad4dcda266f95ca998e09fd76`. PJangler's declared `@delorenj/skillex: latest` dependency was **not** changed; local Skillex was installed separately from the verified tarball after PJangler.

Before install, the installed package directories and generated `pj`/`skillex` wrappers were copied to the Hermes profile scratch directory for rollback. Installed both absolute tarball paths with pinned npm `install -g --prefix ~/.local --force --no-bin-links --ignore-scripts --no-audit --no-fund`, then regenerated wrappers via the existing `cli-launchers.py install` against the canonical root checkout. First attempting that installer from the root worktree returned exit 4 because its `repo:` targets are absent there and temporarily wrote a worktree-targeted Krebs wrapper; rerunning from the canonical root after both installs returned **exit 0, no findings**, and restored exact original generated wrapper hashes: `skillex` `bed1195797dc7a8d853a966c970bf88249ab7cf0985986e6a7704493ff218883`, `pj` `209a292e9ca42957b95e3393986d96519452f093bfae62ce714a73043db43fff`. No launcher file was hand-edited.

Actual installed binaries on PATH now emit native KDL: `skillex --usage-spec` (36,904 bytes), `pj --usage-spec` (27,102 bytes, byte-identical to the committed PJ snapshot), `px --usage-spec` (57,463 bytes). All three pass **usage 7.4.0** `lint -q` and `generate json -f`; generated JSON root names are respectively `skillex`, `pj`, `px`. Optional missing-help notices are informational. For each of these three, minimal PATH (`env -i` with `~/.local/bin:/usr/bin:/bin`) and an unrelated scratch cwd with `mise exec` produce byte-identical KDL. `cli-launchers.py check --json` returned **exit 0, no findings**: all 10 configured live probes passed under minimal PATH, decoy Node + Node 20 pin, and `mise exec` with Node 20 pin. Installed `pj --version` is **1.5.61**; installed `skillex --version` remains **0.4.10** (the number is not provenance; tarball hash and source commit above are).

All other seven native binaries (`flume`, `krebs`, `candybar`, `bb`, `candystore`, `waybill`, `wax`) emitted KDL from PATH, linted and generated JSON on usage 7.4.0, preserving their root names. Focused repair gates rerun: Pilot `node --test test/usage.test.js` **5 passed**, Skillex `node --test tests/node/usage.test.mjs` **2 passed**, PJangler snapshot `--check` **exit 0** and portability **1 passed**, Candybar snapshot `--check` **exit 0** and portability **1 passed**. Flume initially failed `spawnSync usage ENOENT` because the shell PATH did not include mise's usage binary; `mise exec -- node --test tests/usage-spec.test.mjs` then **1 passed**. No full suites were repeated. Probe JSON and emitted KDL/JSON live in `$TMPDIR/33god-103-*` temporarily. This local installation does not imply an npm registry release or other-machine rollout. Ticket review and board state remain with the parent PM.

## Initial publication and limits (historical; repair commits above supersede these refs)

Feature commits and remote main ancestry were verified via `git ls-remote origin refs/heads/main`; main pointers at final verification were pilot `c52c64b94ba81387480cabb1fe81c67890e5ce5b`, skillex `9f60ff749bc3f56a58342daceadc711c3b15d686`, pjangler `5eef14090e68fac8035ad5702bd3a45cb505d9b2`, flume `fbc4204bda9a22cf21795025a1ce3b7e794d7efd`, candybar `4b48e570f1dbe94fbb4b965ac2f4d989ca71bfc3`, bloodbank `ed7c4b41e58a71a5e94976e99852b8b7136894da`, candystore `658e3742061fec2d6ad26ad2ffb68ddb688d3c3b`, wax `37cd0b74357c817136a339ffbfad696cd1901fca`. Existing dirty shared checkouts and unrelated worktree commits remain untouched; `git unpushed` reports those other owners' work, not a pending Story 7.2 commit. Parent pointers were committed only for this story's five newly advanced submodules (pilot was already pinned). The parent PM must independently review and decide ticket state.
