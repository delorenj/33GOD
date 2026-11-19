# Factory asset contract (v1)

Every Atlas component can have a body on the Factory floor. One registry, one floor:

- The **Atlas registry** (`33god-platform/components/<id>.yaml`) says *where* a component stands, in its
  `factory:` block. The Factory reads that through a generated cast file; it keeps no table of its own.
- A **Factory asset** (`manual/sandbox/src/assets/<id>/`) says *what it looks like and how it moves*. The
  directory name is the Atlas registry id, exactly.
- The **Factory forge** (`factory-forge`, a nightly Candybar job) picks one component a night and builds or
  polishes its asset against this contract.

A component with no asset still appears: as its station's primitive prop, or as a kiosk tagged with its real
id. Adding an asset never needs a scene edit.

## 1. Registry: the `factory:` block

```yaml
factory:
  station: dock        # it IS this station (one of the SetIds in src/waybill/stations.ts), or
  near: dock           # it has no station; its kiosk stands in the annex beside this one
  aliases: [hermes-gw] # optional: other ids waybills or older tables use for this component
```

Exactly one of `station` / `near` per component. `scripts/atlas.py render` writes
`manual/sandbox/src/cast.generated.json` (committed: it is the Factory's input, rendered like the Atlas
outputs, and `atlas.py check` fails when it is stale or names an unknown id).

## 2. The asset directory

```
src/assets/<id>/
  asset.json    # the manifest below (required)
  build.py      # Blender (bpy) script that builds the model and its clips, deterministic (required)
  NOTES.md      # what the thing is in the warehouse, what each clip shows, which real behaviour it plays (required)
  Driver.tsx    # optional: behaviour beyond the generic clip sequence (export default a component taking AssetProps)
```

`build.py` is the source. Its output, `public/assets/<id>/model.glb`, is generated and gitignored;
`mise run assets` rebuilds any stale glb (`build` depends on it). An asset whose build fails is skipped with
a warning and the floor falls back to the primitive, so a bad asset can never take the site down.

### asset.json

```json
{
  "format": "33god.factory-asset",
  "version": 1,
  "id": "hook-hub",
  "title": "The receiving dock",
  "placement": "station",
  "replaces": ["Dock"],
  "footprint": [3.2, 2.4],
  "height": 2.6,
  "scale": 1,
  "rotationY": 0,
  "handles": ["parcel", "post"],
  "clips": { "idle": "Idle", "accept": "Accept", "work": "Work", "emit": "Emit" },
  "sockets": { "in": "socket_in", "hold": "socket_hold", "out": "socket_out" },
  "budget": { "tris": 15000, "glbKB": 600 },
  "forge": { "run": "2026-11-18T01:30-0500", "rounds": 2, "score": 8 }
}
```

| Field | Meaning |
|---|---|
| `placement` | `station` (stands at its Atlas station's anchor) or `kiosk` (stands in its annex slot) |
| `replaces` | Primitive props in `src/world/Props.tsx` this asset hides when it loads (station assets only) |
| `footprint` | Metres, x by z, at scale 1. Must fit the slot: a kiosk slot is 1.4 x 1.3 |
| `handles` | What passes through it: `parcel` (raw vendor hook), `post` (house post-it / event), `env` (envelope / command), `summary`, `any` |
| `clips` | Names of the four glTF animations (below) |
| `sockets` | Names of the three empties the traffic is parented to |
| `forge` | Written by the forge: when it was built, review rounds, self-score 0-10 against the rubric |

## 3. The model

- **Units:** metres, Y up in three (Blender Z up, exported with +Y up). Origin on the floor at the footprint
  centre; the front (where traffic arrives) faces +Z.
- **Look:** the Factory's warm toy-warehouse style (`manual/world/warehouse-bible.md`, palette `C` in
  `src/world/Props.tsx`): bevelled, chunky, readable at 20 m, flat PBR colours, roughness 0.5-0.8. No image
  textures except an optional baked AO map of at most 512 px. The component's domain colour
  (`src/domains.ts`) appears on it.
- **Budget:** at most 15,000 triangles and 600 KB of glb. Merge static parts; keep moving parts as separate,
  named nodes.
- **Sockets:** three empties, `socket_in` (where an arriving item is caught), `socket_hold` (where it sits
  while the component works on it) and `socket_out` (where the result leaves). Sockets may be animated.

## 4. The animation cycle

Four glTF animations, exported as separate actions (NLA strips or actions with fake users):

| Clip | Plays | Length | Rule |
|---|---|---|---|
| `Idle` | always, when nothing is passing through | 2-6 s | Seamless loop. Alive, never still: a breathing light, a ticking part. |
| `Accept` | an item arrives | 0.6-1.5 s | Catches the item at `socket_in` and moves it to `socket_hold`. |
| `Work` | while the item is held | 0.8-3 s | Loopable. Shows the real job this component does to the item. |
| `Emit` | the result leaves | 0.5-1.2 s | Sends the output out of `socket_out` and settles back into the Idle pose. |

The animation must be **data-true**: `Work` depicts what the component really does, taken from its Atlas
record (`description`, `role_in_system`, `relations`). The dock stamps a raw parcel into one house post-it;
the clock rings and drops envelopes; the archive files a copy and keeps the original. `NOTES.md` says which
real behaviour each clip plays and cites the record.

## 5. Runtime

`src/assets/` discovers every `asset.json` at build time (`import.meta.glob`). For each asset:

- `<AssetBody id>` loads the glb, loops `Idle`, and on each **visit** runs `Accept -> Work -> Emit`,
  crossfading 0.15 s, with the visiting item's mesh parented to `socket_in`, then `socket_hold`, then released
  from `socket_out`. Visits queue (at most 4 waiting); a busy queue plays `Work` faster, never skips `Accept`.
- **Visits** come from `useVisits(id)`, which merges the two sources of traffic:
  - the ambient simulation (`src/sim/sim.ts`): a parcel, post-it or envelope reaching the component's station
    or kiosk;
  - waybill playback (`src/waybill/`): the playhead reaching a stop at the component.
- A `Driver.tsx`, when present, receives `{ id, gltf, actions, sockets, visits, playhead }` and may replace
  the generic sequence.
- Station assets hide the props named in `replaces`; kiosk assets render at their annex slot in both the
  ambient floor and waybill playback, replacing the generic kiosk box.
- `?at=<component id>` flies the camera to that component (station or kiosk); `?at=<id>&forge` frames the
  asset alone on a turntable for the forge's screenshots.

## 6. Forge rubric (0-10, the forge's self-review; 7 to ship)

1. Reads as the warehouse metaphor for this component at 20 m and up close (2)
2. Idle loop is seamless and alive (1)
3. Accept / Work / Emit show the real job, with the item visibly caught, worked and sent on (3)
4. Fits its slot, faces the traffic, no clipping into neighbours or the belt (1)
5. Palette and style match the floor; domain colour present (1)
6. Within budget; build, typecheck and selfcheck pass; no console errors (2)
