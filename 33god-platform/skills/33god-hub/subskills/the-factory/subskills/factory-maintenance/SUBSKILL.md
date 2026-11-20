---
name: factory-maintenance
description: Build, polish and repair Factory 3D assets, and run the nightly factory-forge that does it. The procedure the forge agent follows every night (brief, NOTES first, build.py on the Blender harness, mise run assets, glbcheck, shoot.py, critique rounds, asset.json) plus the operator runbook (pick, dry run, run now through Candybar, read the verdict and ledger, recover a failed run from asset-failed, pause, cost). Use when giving a component a body, improving an asset's model or animation, a forge run failed or cost too much, or a station's parcel hand-off looks wrong.
metadata:
  archetype: self-evolving
  parent: the-factory
  budget_lines: 200
---

# Factory maintenance

Two jobs share this skill: **forging** an asset (what the nightly agent does, and what you do by hand) and
**operating** the forge. Paths are relative to `~/code/33GOD/33god-platform/manual/sandbox` unless they start
with `33god-platform/` or `~`. The rules every asset must meet are in `forge/CONTRACT.md`; read it before step B.

## Forge one asset (the nightly procedure)

Budget: one night is ~35 min, ~60 turns and ~$10 (2026-11-19 runs). Aim to ship in two critique rounds; take the
third only for a rubric line below target.

**A. Brief yourself.** Read `forge/CONTRACT.md`, then `../world/warehouse-bible.md` (canon objects, the cast) and
`../world/tone.md`, then the Atlas record (`33god-platform/components/<id>.yaml`: `description`, `role_in_system`,
`relations` with `via`/`evidence`), then `src/world/Props.tsx` (palette `C`, the primitive you replace and its
neighbours) and `src/domains.ts` (domain colour), `src/sim/layout.ts` + `src/world/Scene.tsx` (what stands around
the station). Then `tools/assets/blender_run.py`, the Blender harness, and the best existing asset in
`src/assets/*/` as an exemplar.

**B. Write `NOTES.md` first**, before geometry: *What it is in the warehouse*; *The four clips* (what is on screen,
which real behaviour, cited to the record, what the item does at each socket); *Where it stands* (placement,
footprint, replaces, facing); *Rubric self-review* (one line per contract §6 item); *For the integrator*
(anything outside your directory that looks wrong).

**C. Write `build.py`**: deterministic (seeded, no timestamps), primitives with bevels, flat PBR colours, roughness
0.5-0.8, no image textures. Front (where traffic arrives) is +Z, origin on the floor at the footprint centre.
Merge static parts; every moving part its own named node; three socket empties; four actions with the contract's
lengths; export through the harness. Use the harness helpers instead of rewriting them.

Animation craft:
- Idle loops seamlessly (first key = last key on every channel) and is never still: a breathing light, a ticking
  needle, a slow fan.
- Accept visibly catches the item: anticipation, action, settle. Move `socket_in` → `socket_hold` along the path.
- Work is loopable and shows the real job (stamp, sort, copy, ring, file, gate). Ease in and out; offset parts.
- Emit sends the result out of `socket_out` and returns to the Idle pose.

**D. Build and measure.** `mise run assets`, then
`python3 tools/forge/glbcheck.py public/assets/<id>/model.glb --asset src/assets/<id>/asset.json` (the verifier's own
budget, clip, seam, socket and footprint checks).

**E. Look.** `python3 tools/forge/shoot.py <id> --out /tmp/forge-<id>-r1` (builds a temp site, drives a browser).
Read `contact-sheet.png`, then `turn-*`, the clip frames, `visit-*` and `situ.png`; `console.json` must be empty.

**F. Critique and improve.** Score against the rubric as a hard critic; write the three worst things; fix; rebuild;
re-shoot into `-r2`. At most 3 rounds.

**G. Finish.** `asset.json` per the contract (`forge.run` = the run stamp, `forge.rounds` = rounds really done,
`forge.score` honest, 7 to ship; `placement` agrees with the cast). Update the rubric lines in NOTES.md.
`mise run assets` and `npx tsc --noEmit` clean one last time. Optional `Driver.tsx` only when the generic
Accept → Work → Emit cannot show the real behaviour (contract §5).

**H. Feed back** (self-evolving, see the parent hub's "Evolve this skill"). Before your final reply, fold what
this run taught you into this file: fix the step that misled you or add one dated line under *Lessons*. Only
`src/assets/<id>/` and this skill's directory may change in a forge run.

### Lessons (dated, newest first; fold into the steps above when one generalises)

- `shoot.py`'s `visit-*` frames send a `parcel`: an asset that handles only `post` or `env` filters it out and those
  frames show Idle. Check the cycle yourself: serve the temp dist with `vite preview` and call
  `__factoryForge.visit('<id>', '<kind>')` from a /tmp Playwright script, then watch `?at=<id>` (hide the HUD with
  shoot.py's `HIDE_HUD`) for the station's real traffic (2026-11-20, candybar).
- A Driver gets no `stage` flag and the sim is paused on the forge's stage, so copying `AssetBody`'s speed rule makes
  it play nothing there; use `STAGE_ID === id` for real time. A station with two kinds of traffic on one kind
  (candybar: `tick fired` vs `chore due`, both `post`) can branch on `visit.tag` in a Driver and play a fifth clip
  on a fourth socket; the forge cannot pose that clip, so film it on the floor (2026-11-20, candybar).
- Show the Emit to the camera. The hero and situ cameras look at the open side; a `socket_out` slot facing away
  (toward the belt) hid the post-it leaving (2026-11-19, hook-hub, scored 7 for it).
- Few big readable parts beat many small ones: 36 job cards read as texture at 20 m (2026-11-19, hook-hub r1).
- Forge frames show the first `handles` kind on Emit too (`AssetBody.pose()` ignores the visit's `out`). Do not
  chase it in the model; it is a runtime gap, noted for the integrator (2026-11-19).
- A glb cannot read store state (e.g. `useWorld.dockShut`). A state picture needs a named node plus a `Driver.tsx`
  (2026-11-19, hook-hub).
- The record can be stale against the code (hook-hub: 36 handlers in the record, 38 in `handlers.toml`). Model the
  record, flag the drift under "For the integrator" (2026-11-19).

## Operate the forge

The forge is the `factory-forge` Candybar (exec, `40 1 * * *` America/New_York, manifest
`~/code/33GOD/.candybars/factory-forge.candybar.toml`) running `33god-platform/scripts/factory-forge.sh`:
pick → brief (`forge/PROMPT.md` + the run's record) → headless Claude → independent `verify` → on pass commit only
the asset and this skill, push, `mise run assets && mise run build` (deploy), showcase page, ledger; on fail
restore the asset, keep the agent's work in the run dir, still land lessons, ledger, exit 1.

| Task | Do |
|---|---|
| See tonight's pick | `python3 33god-platform/scripts/factory_forge.py pick --explain` |
| Dry run (no agent, no commit) | `33god-platform/scripts/factory-forge.sh --dry-run [--component <id>]` |
| Run one now, metered | `cd ~/code/33GOD/candybar && uv run candybar run factory-forge --wait --timeout 6300` (leave the 33god-platform tree alone while it runs) |
| Force a component | `33god-platform/scripts/factory-forge.sh --component <id>` (ignores cool-off; unmetered) |
| Read a run | `~/.local/state/factory-forge/runs/<id>-<stamp>/`: `verdict.json` (`failed`, every check), `claude.json`, `shots/contact-sheet.png`, `deploy.log` |
| Recover a falsely failed asset | copy `<run>/asset-failed/` back into `src/assets/<id>/`, then `verify <id>` by hand and commit |
| History and cost | `uv run candybar show factory-forge -n 5`; `manual/sandbox/forge/ledger.json` |
| Pause / resume | `uv run candybar pause factory-forge` / `resume` |

Verdict checks that fail most, and why:
- `scope`: something in `33god-platform/` outside the asset and skill dirs changed during the run. Paths elsewhere
  in the monorepo are listed but ignored (other writers). Do not edit the platform tree while a run is live.
- `ship-score`: the agent scored under 7; read its NOTES rubric and the shots, not just the number.
- `station-free`: another component already has the body for that station; pick a `near:` component or move one.

The pick order, verifier and wrapper are documented in `forge/README.md`; tests are
`python3 -m unittest tests.test_factory_forge` from `33god-platform/`.
