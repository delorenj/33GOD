# Skillex volume-UUID ownership, team-inbox cutover, receipt heal, resync on Candybar (2026-11-15)

Done on Damian's Mac Studio (uid 501) over SSH under Aperture charter rule 8 (Jarad handed the session over, untagged, 2026-11-15) and on big-chungus.
Owner approval (Jarad, 2026-11-15): "go on team-inbox cutover, key skillex on volume UUID and address all of the remaining things dangling, just optimize it for Damian, button it up".
Everything below is tool output. No secret was printed. Plan rows: W1-3 (leftover), W5-4, and the "Skillex checkout is dirty/diverged" risk (row 9).

## 1. Skillex keys ownership on volume UUID + inode (skillex repo, `~/code/skillex`)

Root cause, from `W1-3-apply-2026-11-15.md`: receipts recorded `st_dev`; the Mac's Data volume went `16777233 -> 16777234` at the 2026-11-14 restart and every receipt read `E_OWNERSHIP_CHANGED`. The earlier fix was a one-off script rewriting `dev`.

What changed (`src/core/volume-identity.ts`, `activation-ownership.ts`, `reconciliation.ts`, `profile-sync.ts`, `profile-state.ts`):

| Requirement | Result |
|---|---|
| Record `volumeUuid` in new receipts | Activation and profile receipts carry `volumeUuid` next to `dev`/`ino`. macOS: `df -P <path>` names the device, `diskutil info -plist <device>` gives the APFS `VolumeUUID`. Linux: `findmnt -no UUID -T`, then `blkid` on the mount source, then none (falls back to `st_dev`). A symlink is looked up through its parent directory. |
| Cache per mount | Cached per device number for the process (also caches failures). |
| Renumbered dev, same UUID | Accepted. |
| Different UUID | Refused (`E_OWNERSHIP_CHANGED` / `E_PROFILE_ROOT_CHANGED`), even when the device number was reused. |
| Legacy dev-only receipt | A differing `dev` is accepted when ino, kind and link target match; a different inode is refused. |
| Upgrade, apply paths only | A matching entry with a stale record is carried forward with the fresh identity and stored by the next receipt write. A stale `dev`/`volumeUuid` alone is NOT drift (`status`, `show`, previews, an idle `sync` stay clean and write nothing); only `sync` / `profile sync` ever write. |
| Linux fallback | No resolvable id: `volumeUuid` omitted, `dev` recorded and compared as before. |

Two things the live Mac taught me, both fixed before the final release:
- `diskutil info` rejects an arbitrary path ("Could not find disk"), so 0.4.5 silently degraded to dev-only on the Mac. 0.4.6 resolves the device with `df` first.
- 0.4.5/0.4.6 planned a `write-receipt` for every legacy receipt, which would have turned `status`/`show` exit 6 across the whole fleet until each scope synced. 0.4.7 compares receipts without `dev`/`volumeUuid`, so legacy receipts upgrade on their next real write.

Tests: `tests/node/volume-identity.test.mjs` (9): macOS df+diskutil parse, Linux findmnt/blkid/fallback, new receipt records the id, renumbered dev ok (read-only clean, real write refreshes it), different UUID refused with the receipt untouched, legacy dev-only upgrade, legacy different-inode refused, Linux fallback, global scope renumbering. Migration/cutover compare sites ignore the new field (`sansVolume`). Full `npm run check` with `TMPDIR=/tmp`: 1327 tests, 1326 pass, 0 fail (1 skipped, a filesystem-ownership test that needs root). Python suite: 974 passed, 5 skipped. Note for the next person: the default `TMPDIR` under `~/.claude/tmp` makes ~30 profile tests fail with `E_RECEIPT_UNSAFE_PATH`; use `TMPDIR=/tmp SKILLEX_TEST_TMPDIR=/tmp`. The pre-push hook also races (pytest vs `dist/` rebuild) and failed twice on a re-run; it passed unchanged on the third push, nothing was bypassed.

## 2. Release and deploy

| Item | Evidence |
|---|---|
| Commits (main, pushed) | `d2394f2` feat, `def7efd` macOS fix, `b57245a` drift fix, `b4b0292` cutover script (below); releases `769d367` 0.4.5, `53ac210` 0.4.6, `39fde58` 0.4.7 |
| Tags | `v0.4.5`, `v0.4.6`, `v0.4.7` pushed |
| npm | `@delorenj/skillex` 0.4.5, 0.4.6, 0.4.7 published (`npm publish --ignore-scripts --otp`, OTP from the vault `NPM` item; the repo's `prepublishOnly` check had just passed). `npm view` = 0.4.7. 0.4.5 and 0.4.6 are superseded; use 0.4.7. |
| big-chungus | `mise install npm:@delorenj/skillex@0.4.7`; `latest`, `0`, `0.4` now point at 0.4.7. `skillex --version` = `0.4.7`. Global `skillex status` exit 0 (after the normal `skillex sync --scope global`, one `write-receipt`: the catalog moved and the receipt now carries `volumeUuid` on 70/70 records). Full resync run: `ok - 44 strict desks (44 current)`, 0 refused, 0 error; `33god-pm`, `infra-pm`, `flume-pm` `show_exit 0`. |
| Mac | Installed from the packed tarball into `~/.local/share/skillex-npm` with the Mac's Node 24; wrapper `~/.local/bin/skillex-npm` comment updated; `skillex --version` = `0.4.7`. Previous 0.3.1 install is `skillex-npm-0.3.1.tgz` in `~/.config/33god/config-backups/20261116T022304Z-skillex-volume-uuid/` (with the old wrapper and a tarball of `~/.local/state/skillex`). |

## 3. Team-inbox cutover (`hello-subconscious-team-inbox-team-inbox`), applied

- Backup first: `~/.config/33god/config-backups/20261116T022853Z-team-inbox-cutover/` (`desk-skills.tgz`, `config.yaml`, `config.delta.yaml`, the whole skillex state).
- `.skillex-selection` created with `skillex init --project <desk>/.skillex-selection` (`{"inherit_global": true}`), the same shape as the other desks.
- Preview (`hermes-skillex-cutover.py`, the current repo copy staged on the Mac, run with `uv run --with pyyaml`): `alias false`, `owned 60`, `preserve 55`, `config_change false`, `applied false`. The 55 were the 33 dangling `bmad-*` links, 21 deselected skills and `parallel-work-coordinator`. The unowned `.hub` is an idle hub (empty lock, quarantine and caches), which the policy tolerates in place.
- Apply: `applied true, exit 0, idempotent true`; quarantine `~/.hermes/.skill-quarantine/hello-subconscious-team-inbox-team-inbox/20261115T213050-9c9e8ed7` holds all 55 (nothing deleted). Then `profile sync --skillex-only`: re-preview `changes []`, `profile show` exit 0, 60 managed (identical to the global selection: missing `[]`, extra `[]`), 0 dangling links.
- Config detour, and the fix: the cutover refused ("non-generated config needs explicit config migration") because this desk's `config.yaml` is hand-maintained. I first ran the renderer's `absorb` + `render` on it; the effective config then differed from the live one (`memory.provider` `''` -> `hindsight`, the 1Password `binary_path` dropped, new terminal defaults). I reverted both files byte-for-byte from the backup (`cmp` identical) before anything restarted. The cutover owns `skills.external_dirs` only, and it was already `[]`, so `scripts/hermes-skillex-cutover.py` now leaves a hand-maintained config alone when `external_dirs` is already empty in both files and still refuses otherwise (commit `b4b0292`, unit test added; 11 pass). The renderer's own backups of that detour are in `~/.hermes/.profile-config-backups/20261115T212946-{absorb,render}/`; the live config is the original.
- Gateway check after the cutover (no restart needed, none done): `launchctl` `ai.hermes.gateway-hello-subconscious-team-inbox-team-inbox` running, pid 1344, never exited; `gateway_state.json` `running`, telegram `connected`, api_server `connected`; `curl http://127.0.0.1:8642/health` -> `200 {"status": "ok"}`.

## 4. Other drifted receipts, healed through normal skillex commands (preview, apply, re-preview)

| Scope | Command | Result |
|---|---|---|
| Global (`~`) | `skillex sync --scope global` | `write-receipt` applied; re-preview `[]`; `status` exit 0 |
| Desks `aai-team`, `private-desk`, `space-owner`, `lamp-ops-task-agent-team-inbox`, `music-lab-pm` | `profile sync <desk> --project <selection> --skillex-only` | each `write-receipt` (upgrade) applied; re-preview `[]`; `profile show` exit 0 |
| `~/code/hello-subconscious-team-inbox` project root | `skillex sync --scope project --project <repo>` | the repo's `.agents/skills` was empty (receipt claimed 125 absent links); applied 8 `create-directory`, 61 links (60 global + `parallel-work-coordinator`), re-preview `[]`, `status` exit 0, `git status` clean (`.agents/skills/` is in Damian's global git ignore) |

Not healable by any skillex command, left alone and reported (they were already broken and nothing consumes them):
- Genuine ownership changes, correctly refused (`E_OWNERSHIP_CHANGED`): `pjangler-learning-lab`, `space`, `hello-subconscious-company`, `Music Lab`, `Music Lab/Sound`. Their `.agents/skills` directories were re-created after the receipt was written (inode changed, not just `dev`; receipts were written under the old host name `Mac.attlocal.net`), and they hold real BMAD copies Skillex never owned. `root adopt` and `normalize` refuse for the same reason. There is no supported "retire this stale receipt" command; I did not hand-edit.
- Orphan receipts for `mission-control`, `ipm-aai`, `damian-engineering-workflow`: the project directories no longer exist under `~/code` (only copies under `~/code.backup`). Inert.

## 5. W5-4: resync moved from launchd to Candybar

- Manifest committed: `candybar/deploy/mac/skillex-hermes-resync/{candybar.toml,README.md}` (commit `0f76d84`, pushed). Name `mac-skillex-hermes-resync`, `*/15 * * * *` UTC, exec runner, `timeout_s 900`, missed-fire policy (AD-6 run-at-wake, coalesce, overlap refused) and idempotency documented at the top. The script pair lives at `~/.local/share/33god/skillex-hermes-resync/` on the Mac (not in the diverged `~/code/skillex` checkout, which was not touched).
- Registered on the Mac Candybar (127.0.0.1:8700): `candybar register` -> id `01a1e234-70aa-7e25-a94f-77ecb95079d4`, read back with `candybar show` (schedule, runner, state).
- Terminal invocation and effect: manual `candybar run --wait` -> `success in 6.8s (exit 0)`; `hermes-resync.last.json` `status ok`, `counts {ok: 6, error: 0, refused: 0, total: 6}`, `exit 0`, all six desks `show_exit 0`, including the team-inbox desk that errored before. The first scheduled fire (`trigger=scheduled`, Sun 21:45 EST) also `success`, 6.8 s, `last.json` rewritten at `2026-11-16T02:45:06Z`, same counts.
- Old clock retired: `launchctl bootout` + `launchctl disable gui/501/io.33god.skillex-hermes-resync`, plist moved out of `~/Library/LaunchAgents`; copies in `~/.config/33god/config-backups/20261116T023430Z-skillex-resync-launchd/` (`.plist` and `.plist.retired`) for rollback. `launchctl list | grep skillex` is empty. The agent's `WatchPaths` catalog-HEAD trigger went with it: on the Mac the catalog only moves when an operator moves it and the 15-minute fire catches up.
- `candybar doctor --live` on the Mac: no skillex entry any more. It still fails on Damian's own launchd/cron jobs (`com.openclaw.*`, `com.hellosubconscious.task-backup`, `com.damian.private-desk-transcriber`, `com.citrolabs.EgoUpdater.wake`, three user crontab entries). Those are his services; per plan decision 8 they stay visible and nothing was disabled.

## Open items

- The five stale project-root receipts and three orphan receipts above need either a new "retire receipt" skillex command or Damian's say-so to move the directories aside and `root adopt`; neither is urgent, nothing syncs those roots.
- The Mac's catalog (`~/code/skillex/all-skills`, `c281845`) is still 4 ahead and 75 behind with the old staged-deletion set (W1-3 note); skillex scripts are no longer read from that checkout.
- Candybar parent pin (`33GOD/candybar`) and skillex pin bumps are left to the orchestrator's usual bump commit.

## Follow-up: receipt retire (0.4.8)

Closes the open item above ("no supported retire-this-stale-receipt command"). Done on big-chungus and on Damian's Mac (Aperture charter rule 8, Jarad handed the session over, untagged, "address all of the remaining things dangling... button it up"). Everything below is tool output; no secret was printed.

**Command.** `skillex receipt list [--state valid|stale|orphan|invalid|foreign-host]` and `skillex receipt retire [targets...] [--all-stale] [--apply] [--force] [--backup-dir <path>]`. Targets are a receipt id (8+ hex), a project/scope path or a skill-root path. Preview is the default (`--json` envelope like every command). `stale` = the skill root exists but its inode is not the recorded one (the `E_OWNERSHIP_CHANGED` case); `orphan` = the scope or skill root path no longer exists. `--apply` copies the receipt JSON to the backup dir (default `<state>/skillex/retired-receipts/<UTC ts>-receipt-retire/`, plus a `receipt-retire.json` manifest), reads the copy back, then unlinks the original under the same lock sync takes. A currently valid receipt, one carrying an interrupted-operation journal, or an unreadable one is refused unless `--force`; another host's receipt is never retired. A refused named target stops the whole apply with nothing retired. Skill roots are never read, written, moved or deleted. Tests: `tests/node/receipt-retire.test.mjs` (7).

**Release.** skillex `f51ff3e` on main (feature `b5073f2`, release `d203bb8`, tooling fixes `b8a6b05` and `f51ff3e`), tag `v0.4.8` pushed, `@delorenj/skillex@0.4.8` published (`npm publish` with the OTP from the vault `NPM` item; the registry took about two minutes to show it). big-chungus: `mise cache clear` then `mise install npm:@delorenj/skillex@0.4.8` (aube's metadata cache otherwise answers "no version matches"), `skillex --version` 0.4.8, global `status` exit 0, global `sync --dry-run` 0 changes. Mac: `npm pack @delorenj/skillex@0.4.8`, installed with the Mac's Node 24 into `~/.local/share/skillex-npm`, wrapper `~/.local/bin/skillex-npm` comment bumped (the old wrapper is in `~/.config/33god/config-backups/pre-0.4.8/`), `skillex` -> `skillex-npm` -> 0.4.8.

**Mac, the 8 inert receipts.** Before: `8 valid, 5 stale, 3 orphan`. `receipt retire --all-stale` preview (exit 0, nothing written) named exactly these: stale `pjangler-learning-lab`, `space`, `hello-subconscious-company`, `Music Lab`, `Music Lab/Sound`; orphan `mission-control`, `ipm-aai`, `damian-engineering-workflow`. `--apply --backup-dir ~/.config/33god/config-backups/20261116T033218Z-receipt-retire` retired 8, exit 0; the backup holds the 8 JSON files and `receipt-retire.json`. After: `8 valid, 0 stale, 0 orphan`. A listing hash of each of the five stale projects' `.agents/skills` trees (their real BMAD content) is identical before and after. Global `skillex status` exit 0; the six desks (`aai-team`, `private-desk`, `space-owner`, `lamp-ops-task-agent-team-inbox`, `music-lab-pm`, `hello-subconscious-team-inbox-team-inbox`) `profile show` exit 0. Candybar `mac-skillex-hermes-resync --wait`: `success in 6.8s (exit 0)`; `hermes-resync.last.json` `ok - 6 strict desks (6 current)`, counts `ok 6, error 0, refused 0`. The Mac's `~/code/skillex` is still `main` ahead 1 (Damian-local coaching pack) and `all-skills` is still on `damian-local`; neither was touched (the catalog head read 1cab875, one Damian-side skill commit newer than at the 0.4.7 deploy).

**Tooling fixes found on the way (skillex repo).**
- The Node tests failed in ~30 profile/parity tests whenever `TMPDIR` sat inside a Git repo (agent shells export `~/.claude/tmp`), because receipts are refused under a source repository. `npm test` now preloads `tests/node/hermetic-tmp.mjs`, which falls back to `/tmp` when `TMPDIR` is inside a repository; the Kimi/Hermes client-root failures were this and nothing else (no live host state). Default-`TMPDIR` run: 1334 tests, 0 fail.
- The pre-push `parallel: false` was already set; the hook still failed at random. Pytest never cleans `dist/`; the real hazards were (a) overlapping gates from several agents sharing `dist/` while `scripts/build.mjs` deleted every `.js`/`.d.ts` before rebuilding, and (b) the conftest tripwire on the real `~/.agents/skills` mtime firing when another agent synced globally mid-run (reproduced on the first push of this release). Fixes: the build now stages to `.build-stage-<pid>/`, takes a lock and publishes by per-file rename (a reader loop during two concurrent builds saw `dist/cli.js` missing 0 times in 150 polls); the pre-push gate is one job, `scripts/pre-push-checks.sh`, holding a per-checkout `flock` across node-check, ruff, mypy, pytest; a pytest failure is rerun once with `--lf`.
- Left as found: big-chungus has 64 orphan profile receipts (`skillex receipt list --state orphan`, deleted or moved Hermes profile dirs). Not retired here (not asked); `skillex receipt retire --all-stale` previews them.
