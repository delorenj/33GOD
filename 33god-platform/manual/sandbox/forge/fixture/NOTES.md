# fixture: the pipeline test crate

Not an Atlas component. A bevelled crate with a hinged lid, a stamp and a lamp, used only to prove the asset
pipeline end to end (`build.py` -> `mise run assets` -> `public/assets/fixture/model.glb` -> `<AssetBody>` ->
`window.__factoryForge`). It mounts only with `?fixture` in dev or forge mode, as a kiosk for the fake id
`fixture`, and never renders on the normal floor.

| Clip | Shows |
|---|---|
| Idle (4 s) | the lamp breathes, the lid rattles once |
| Accept (1 s) | the lid opens; `socket_in` carries the item from the front into the crate |
| Work (1.6 s) | the stamp comes down twice; the lid jumps under it; the lamp flashes |
| Emit (0.8 s) | the lid flips open; `socket_out` lifts the result over the front lip; the lid shuts |
