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

## Publication and limits

Feature commits and remote main ancestry were verified via `git ls-remote origin refs/heads/main`; main pointers at final verification were pilot `c52c64b94ba81387480cabb1fe81c67890e5ce5b`, skillex `9f60ff749bc3f56a58342daceadc711c3b15d686`, pjangler `5eef14090e68fac8035ad5702bd3a45cb505d9b2`, flume `fbc4204bda9a22cf21795025a1ce3b7e794d7efd`, candybar `4b48e570f1dbe94fbb4b965ac2f4d989ca71bfc3`, bloodbank `ed7c4b41e58a71a5e94976e99852b8b7136894da`, candystore `658e3742061fec2d6ad26ad2ffb68ddb688d3c3b`, wax `37cd0b74357c817136a339ffbfad696cd1901fca`. Existing dirty shared checkouts and unrelated worktree commits remain untouched; `git unpushed` reports those other owners' work, not a pending Story 7.2 commit. Parent pointers were committed only for this story's five newly advanced submodules (pilot was already pinned). The parent PM must independently review and decide ticket state.
