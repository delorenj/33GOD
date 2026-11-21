---
name: the-factory
description: The Factory, the 3D toy-warehouse picture of 33GOD (React Three Fiber, manual/sandbox, live at manual.delo.sh/sandbox) and its link to the Atlas component registry. Covers the factory block in components/*.yaml, the generated cast (cast.generated.json), stations, kiosks and the annex, ?at=<component> deep links, the asset contract (src/assets/<id>/, build.py on Blender, Idle/Accept/Work/Emit clips, socket_in/hold/out), AssetBody and visits, the nightly factory-forge Candybar that gives one component a body a night, its verifier, ledger and showcase pages. Use when placing or moving a component on the floor, a component missing or in the wrong place, building, polishing or repairing a 3D asset or its animation, a parcel or post-it passing through a station wrongly, running, debugging or tuning the nightly forge (failed verdict, scope, cost), or deploying the Factory site.
metadata:
  archetype: self-evolving
  parent: 33god-hub
  budget_lines: 150
---

# The Factory

The Factory is a warm toy warehouse that shows how 33GOD works: a parcel is one raw vendor hook, a post-it is
an event, an envelope is a command, and every station is a real component. It is a Vite + React Three Fiber
site in `~/code/33GOD/33god-platform/manual/sandbox`, served live from `../books/sandbox` at
https://manual.delo.sh/sandbox/. **A build is a deploy.** It plays two kinds of traffic: the ambient simulation,
and recorded waybills (one prompt's real flight through the system).

**How it is linked to the Atlas.** The Atlas registry (`33god-platform/components/<id>.yaml`, 98 components) is
the single source of where things stand. Each record has a `factory:` block, either `station: <setId>` (it *is*
that station) or `near: <setId>` (it gets a kiosk in that station's annex), plus optional `aliases:`.
`atlas.py render` writes the cast (`manual/sandbox/src/cast.generated.json`); the Factory reads only the cast and
keeps no table of its own; `atlas.py check` fails when the cast is stale. So every Atlas component has a place on
the floor, `?at=<id>` flies the camera to it, and the Atlas links each component back to the Factory. A
component's **body** (its 3D asset) lives in `manual/sandbox/src/assets/<id>/`, named by the same registry id.

## Rules on every route

- The registry is the truth. To move a component, edit its `factory:` block and re-render; never edit the cast,
  `stations.ts` tables or scene code to place one component.
- `build.py` is the source of an asset; `public/assets/<id>/model.glb` is generated and gitignored.
- Never run `mise run build` in `manual/sandbox` to "test": it deploys. Test builds go to a temp outDir
  (`tools/forge/shoot.py` does this for you).
- An asset must be data-true: its Work clip shows what the Atlas record says the component does.
- A bad asset can never take the site down: a failed glb falls back to the primitive prop. Keep it that way.

## Ask the system first

| Question | Ask |
|---|---|
| Where does component X stand? | `jq '.components["X"]' manual/sandbox/src/cast.generated.json` |
| Is the cast in step with the registry? | `python3 33god-platform/scripts/atlas.py check` |
| Which components have a body, and how good? | `jq '.runs[-10:]' manual/sandbox/forge/ledger.json`; `ls manual/sandbox/src/assets/` |
| What would the forge do tonight? | `python3 33god-platform/scripts/factory_forge.py pick --explain` |
| Did last night's forge run, and what did it cost? | `cd ~/code/33GOD/candybar && uv run candybar show factory-forge -n 5` |
| Does an asset pass the contract? | `python3 33god-platform/scripts/factory_forge.py verify <id>` (clean tree, or `--baseline`) |
| What does it look like? | `python3 manual/sandbox/tools/forge/shoot.py <id> --out /tmp/shots`, then read `contact-sheet.png` |

(Paths are relative to `~/code/33GOD` unless they start with `manual/`, which means `33god-platform/manual/`.)

## Routes: read exactly one, then come back

| When you are… | Read |
|---|---|
| Building, polishing or repairing a component's 3D asset; running, debugging or tuning the nightly forge; recovering a failed forge run | [subskills/factory-maintenance/SUBSKILL.md](subskills/factory-maintenance/SUBSKILL.md) |
| Writing or checking an asset against the rules (directory, `asset.json`, model, clips, sockets, budget, rubric) | `33god-platform/manual/sandbox/forge/CONTRACT.md` (the contract is the source; this hub does not copy it) |
| Placing, moving or aliasing a component on the floor | the "Place a component" steps below |
| The warehouse metaphor: what each object and station means | `33god-platform/manual/world/warehouse-bible.md` |

### Place a component

1. Edit `33god-platform/components/<id>.yaml`: `factory: {station: <setId>}` or `factory: {near: <setId>}`.
   SetIds are the `SetId` union in `manual/sandbox/src/waybill/stations.ts` (bays, courier, dock, labeldesk,
   belt, archive, rules, control, cataloguer, clock, crew, entrance, voxxy, library, staffing, soundwing). A
   station holds one component; a second one standing there goes `near:` the same set.
2. `python3 33god-platform/scripts/atlas.py render && python3 33god-platform/scripts/atlas.py check`.
3. Commit the record and the cast together (the 33GOD pre-commit hook re-renders and stages the cast too).
4. Open `https://manual.delo.sh/sandbox/?at=<id>` after the next build to see it.

## Not here

| Topic | Go to |
|---|---|
| Recording or replaying one prompt's flight (waybills), `waybill publish` links that open in the Factory | the `waybill` skill |
| The registry itself, Atlas views, drift audit | the 33god-hub component map (`references/component-map.md`) and `atlas.py --help` |
| Scheduling anything (the forge's clock) | the `candybar` skill |
| Publishing pages | the `artifacts` skill |

## Gotchas

- A component that shares a station with another stays a primitive; `verify` refuses a second body for a station
  (`station-free`) → `factory-maintenance`.
- The tour-set stations (entrance, voxxy, library, staffing, soundwing) ignore `replaces` today (2026-11-19).
- The overnight tour page (`overnight/`) is a different site and shares no data with the forge. The forge ranks on last night's waybill (`factory_forge.py traffic`).

## Evolve this skill

This subtree is a **self-evolving skill** (archetype owned by Skillex; see SKRILL-49, "Self-Evolving Skill
tree"). When a task routed here teaches you something that would have saved time, fold it back before you finish:

1. Put the lesson where it bites: change the step, add an "Ask the system" row, or add one dated gotcha line
   (`(2026-11-19, hook-hub run)`). Never append a diary; rewrite what is now wrong.
2. Keep each file under its `budget_lines`. If your edit pushes it over, split: move the largest coherent
   section into `subskills/<name>/SUBSKILL.md` (name + description frontmatter, `parent:` set) and leave one
   route row. Merge a child back when it shrinks under a third of its budget.
3. Every relative link must resolve; no nested `SKILL.md`; commit the skill with the change that taught it.
