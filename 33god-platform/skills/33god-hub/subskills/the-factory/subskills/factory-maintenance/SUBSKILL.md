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
`src/assets/*/` as an exemplar. Work out which face each camera sees: the station's `view` in `src/content.ts` and
`OVERVIEW`, turned into model space through the anchor's `rotY` (candybar: the station camera sees the right side,
the overview the front), and put the record's main beat on a face a camera sees. A re-forge starts from the last
failed run: read `~/.local/state/factory-forge/runs/<id>-<stamp>/verdict.json` and `asset-failed/` first, copy its
`build.py`, `NOTES.md` and `asset.json` into your directory, and spend the night on its weakest rubric lines.

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
- Anything that must run on through clip changes (a pendulum, a clock's hands) is not keyed: every clip restarts at
  t 0, so a keyed swing snaps on each crossfade. Drive it from a `Driver.tsx` on the floor's time.
- When the record's job varies by kind (runner, route, rule), bake one Work variant per kind (`Work`, `Work_X`, ...)
  and let a Driver pick per visit; one variant forever says "only this kind ever runs".

**D. Build and measure.** `mise run assets -- --only <id>`, then
`python3 tools/forge/glbcheck.py public/assets/<id>/model.glb --asset src/assets/<id>/asset.json` (the verifier's own
budget, clip, seam, socket and footprint checks). glbcheck does **not** check the manifest caps: `height` must be
<= 6 m (`manifest-height`); design to 5.8 from the first sketch.

**E. Look.** `python3 tools/forge/shoot.py <id> --out /tmp/forge-<id>-r1` (builds a temp site, drives a browser).
Read `contact-sheet.png`, then `turn-*`, the clip frames, `visit-*` and `situ.png`; `console.json` must be empty.

**F. Critique and improve.** Score against the rubric as a hard critic; write the three worst things; fix; rebuild;
re-shoot into `-r2`. At most 3 rounds. After round 1, also get an unanchored read: three read-only critics in
parallel (readability in stills, data-truth against the record, the code and the bible, craft), given the shots
dir, the record and `build.py`, never your conclusions. Keep the build running while they read. Check each claim
against the code or the bible before you act on it. A tall part (a mast, a lamp) between the clip camera and a beat
hides that beat in every frame.

**G. Finish.** `asset.json` per the contract (`forge.run` = the run stamp, `forge.rounds` = rounds really done,
`forge.score` honest, 7 to ship; `placement` agrees with the cast). Update the rubric lines in NOTES.md.
`mise run assets` and `npx tsc --noEmit` clean one last time. Optional `Driver.tsx` only when the generic
Accept → Work → Emit cannot show the real behaviour (contract §5). Then run the verifier itself, from
`33god-platform/`: `python3 scripts/factory_forge.py verify <id>` (~3 min; builds and shoots in /tmp, writes nothing
in the tree) and read `pass`/`failed`. It is the judge; glbcheck is only part of it.

**H. Feed back** (self-evolving, see the parent hub's "Evolve this skill"). Before your final reply, fold what
this run taught you into this file: fix the step that misled you or add one dated line under *Lessons*. Only
`src/assets/<id>/` and this skill's directory may change in a forge run.

### Lessons (dated, newest first; fold into the steps above when one generalises)

- `mise run assets` timing out at 300 s with no Blender output is not your build.py. Check
  `cat /proc/<blender pid>/wchan`. `request_wait_answer` means Blender is hung on a stuck gvfs FUSE backend
  (`gvfsd-mtp` under `/run/user/1000/gvfs`). Kill that backend and the build takes under 1 s. A station whose cast
  has two members (cataloguer: `enricher` + `turn-enricher`) needs a Driver. It draws the other member's primitive
  statically and routes its visits (by tag) to that member's spots, with release from its runner. Pick a Work
  variant from the loaded waybill span's `attrs`, not by alternating. A noise branch that emits no event never
  reaches a visit, so do not play it (2026-11-24, turn-enricher).
- A self-review passes its own inventions. The 2026-11-22 board scored 7 with a chart that ran on every copy
  (Prometheus scrapes on a timer and Grafana draws), green "acked" lips (a signature is not a success stamp), prices
  that `routes.json` does not hold, and a health lamp that blinked on fetches. The data-truth critic in step F caught
  all four. Grep the cited code for every number, name and colour you draw. Belt blue and slot hatches are canon for
  the belt and its envelope hatches, so never use them for an event leaving a reader (2026-11-23,
  aai-llm-observability).
- The clip camera sits 65 degrees right (plus `rotationY`, which turns the asset on the stage too), so a tall part
  at the front-right hides the Work beat; keep the right end behind the bench's front line. Blinks between the
  0.1/0.5/0.9 fracs leave Idle's three frames identical; a hand swinging out, upright, out is alive in all three and
  still seams. Point the data-truth critic at the component's own ledger, read-only: wax.db gave the real pass mix,
  per-pass run times (Work lengths) and three events per command, none of which the record holds. `Clip.key`'s
  `interp='LINEAR'` never reaches the exported curve (the glb samples eased): for a constant-speed contact (a paddle
  shoving an item) key every whole frame of the segment. Read the glb's samples to check (2026-11-25, wax).

- A tour-set station (entrance, voxxy, library, staffing, soundwing) has no `Hideable` primitive in `PROP_NAMES`
  (`src/assets/contract.ts`), so a station asset there cannot pass `manifest-replaces` honestly. Naming another
  station's prop hides the floor; naming the set's own prop (`StaffingDesk`) makes `parseManifest` drop the whole
  manifest. Ship `replaces: []`, flag it for the integrator, and expect that one failure. In step A, also grep the cast
  for other components on your station: `discover()` gives the station to the first id in sort order
  (2026-11-22, aai-llm-observability). The re-forge failed the same way on 2026-11-23. `COOL_AFTER` parks a
  component after two failures. `aai-gateway` shares `staffing` and will fail the same check, so a forge picked for a
  tour-set station should improve the asset for `asset-failed/` recovery and not expect to ship.
- shoot.py poses each clip at 0.1, 0.5 and 0.9 of its length (`FRACS`). Put each clip's key pose (the punch down,
  the item in the slot) on one of those times, or the frames, the verifier and Jarad never see it (2026-11-22).
- A part that rolls part of a turn (an odometer step) snaps back in the 0.15 s crossfade to the next clip, which
  holds it at rest. Roll whole turns: the exporter samples every frame and three slerps the short way, so a full
  turn loops and crossfades clean. Each `mise run assets -- --only` takes ~2 min of Blender, so batch your fixes
  per round (2026-11-22).

- A 6.9 m tower that self-scored 8 failed verify on `manifest-height` alone; every glbcheck line was green. Steps D
  and G now say so (2026-11-21, candybar).
- `AssetBody` freezes Idle on pause (time scale 0) behind an `isRunning()` guard, which is false at time scale 0, so
  Idle never thaws until a visit ends. A Driver must remember that it froze Idle (candybar's `froze` ref); a forge
  pose also stops Idle at 0 and must not be revived (2026-11-21, candybar).
- A /tmp Playwright script can import shoot.py's `Server`, `HIDE_HUD` and `contact_sheet`; run it with plain
  `python3` (`-I` drops the user site and Playwright with it). `HIDE_HUD` leaves the floor's drei labels on
  (2026-11-21, candybar).
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
- `manifest-replaces`: a station asset with an empty `replaces`. That failure is honest at a tour-set station, which
  has no primitive to hide (see Lessons, 2026-11-22). Recover it from `asset-failed/` once the check exempts those
  stations.

The pick order, verifier and wrapper are documented in `forge/README.md`; tests are
`python3 -m unittest tests.test_factory_forge` from `33god-platform/`.
