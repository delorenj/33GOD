# The Factory forge

Every Atlas component gets a body on the Factory floor, one a night. The forge is a Candybar job that picks
a component, has a headless Claude Code agent build (or later polish) its 3D asset against
[`CONTRACT.md`](CONTRACT.md), checks the result without trusting the agent, then commits, deploys and
showcases it.

| File | Job |
|---|---|
| [`CONTRACT.md`](CONTRACT.md) | The asset contract: registry `factory:` block, `src/assets/<id>/`, model, the four clips, runtime, rubric. |
| [`PROMPT.md`](PROMPT.md) | The agent's brief. `factory_forge.py prompt <id>` appends the run: the Atlas record, its neighbours, its station, the best existing asset as an exemplar, and in polish mode the last NOTES and score. |
| [`ledger.json`](ledger.json) | One row per run: `run, id, mode, outcome (shipped, failed, error), score, commit, tokens, showcase_url, duration_s`. |
| `../../scripts/factory_forge.py` | `pick`, `prompt`, `snapshot`, `verify`, `usage`, `showcase`, `ledger`. |
| `../../scripts/factory-forge.sh` | The candybar's entry: lock, pick, brief, agent, verify, commit, deploy, showcase, ledger. |
| `../tools/forge/shoot.py` | The agent's eyes and the verifier's: turntable, every clip across its length, a live visit, an in-situ shot, a contact sheet, a console log. |
| `../tools/forge/glbcheck.py` | The independent glb validator (budget, clips, Idle seam, sockets, footprint, textures). |
| `/home/delorenj/code/33GOD/.candybars/factory-forge.candybar.toml` | The schedule: 01:40 America/New_York, exec runner, timeout 6000 s. Enabled 2026-11-19 after the first shipped run (hook-hub). |
| `33god-platform/skills/33god-hub/subskills/the-factory/` | The **the-factory** skill hub and its `factory-maintenance` child: the agent's procedure and the lessons earlier nights learned. Self-evolving: each run may fold lessons back in; the wrapper lints them (`factory_forge.py skill`) and lands them in their own commit, on a pass or a fail. |

## Which component tonight

`factory_forge.py pick --explain` prints the ranked top ten with reasons. The Factory is about traffic, so:

1. Candidates are registry components with no `src/assets/<id>/asset.json`. A component whose last two forge
   runs failed steps back for a night ("cooling off"); an explicit `--component` ignores that.
2. A component with a factory **station** comes before one that only gets a kiosk.
3. Then the busiest in the newest night digest (`overnight/site/nights/*.json`, `events + credited`).
4. Then first-party before vendor, then id.

When every component has an asset the forge **polishes**: lowest `forge.score` first, ties to the oldest
`forge.run`. Stations come from `src/cast.generated.json` (rendered from the registry by `atlas.py render`);
until that file exists it falls back to the registry's `factory:` blocks, then to the old hand table.

## What the agent does

Follows the `factory-maintenance` skill (its "Forge one asset" steps; `PROMPT.md` is now only the identity, the
hard rules and the run's facts). It reads the contract and the warehouse bible, writes `NOTES.md` first (the metaphor, and which real behaviour each
clip plays, cited to the record), writes a deterministic `build.py` on the runtime's Blender harness
(`tools/assets/blender_run.py`), runs `mise run assets`, then up to three rounds of: `shoot.py`, read the PNGs,
critique against the rubric, improve. It writes only `src/assets/<id>/` and never commits.

## What the verifier checks (it trusts nothing the agent says)

`factory_forge.py verify <id> [--baseline FILE]` prints a JSON verdict, exit 1 on any failure:

- **scope**: nothing changed outside `src/assets/<id>/` since the pre-run `snapshot` (a content hash of every dirty
  or untracked path, so pre-existing dirt is not blamed on the agent);
- **manifest**: `asset.json` against the contract (format, id, placement agrees with the cast, footprint, handles,
  clips, sockets, budget, forge block) and `forge.score >= 7`;
- `build.py` present, `NOTES.md` present and covering all four clips;
- `mise run assets` builds the glb, and the glb itself, parsed independently: at most 15,000 triangles and 600 KB,
  all four clips within the contract lengths, a seamless Idle, the three sockets, footprint and height, origin on
  the floor, textures at most 512 px;
- `npx tsc --noEmit`, a temp `vite build`, the waybill selfcheck;
- `shoot.py` in a real browser with zero console errors and the asset loaded.

## Running it

```bash
../../scripts/factory-forge.sh --dry-run               # pick, brief, print the command; runs nothing
../../scripts/factory-forge.sh --component candybar    # one real run, now
../../scripts/factory-forge.sh --no-deploy --no-publish
python3 ../../scripts/factory_forge.py verify <id>     # check any asset by hand (needs a clean tree, or --baseline)
python3 tools/forge/shoot.py <id> --out /tmp/shots     # photograph it; --fixture shoots the runtime's test asset
python3 -m unittest tests.test_factory_forge           # from 33god-platform/
```

On a pass the wrapper commits **only** `src/assets/<id>/` (`feat(factory): <id> gets a body — <title>`), pushes,
runs `mise run assets && mise run build` (a build is a deploy), publishes a showcase page to MinIO through the
`artifacts` skill and logs the verified URL in the ledger (a second, ledger-only commit, so each row can carry the
asset commit's sha). On a failure it restores `src/assets/<id>/` to HEAD, removes the generated glb, logs the run
and exits 1. If claude itself produces nothing, the run is logged as `error` (it does not count against the
component). Every run leaves its prompt, the agent's JSON, the verdict and the screenshots in
`~/.local/state/factory-forge/runs/<id>-<stamp>/`.

## Enabling the nightly

Enabled 2026-11-19 after a proven real run (`candybar run factory-forge --wait`: hook-hub shipped at `c1614d8`).
`candybar pause factory-forge` stops it; `run` still works while paused. The wrapper writes `CANDYBAR_RESULT_FILE` with `metrics.token_spend` (input plus
output tokens from the agent's JSON), so the cost block fills in after the first night.
