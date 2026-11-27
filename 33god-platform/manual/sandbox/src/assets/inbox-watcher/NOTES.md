# inbox-watcher: the memo desk

## What it is in the warehouse

The record (`components/inbox-watcher.yaml`) says it "watches for new voice memos and sends them to transcription" and
is the "start of the Holocene memo pipeline". The tour already names it: **the memo desk** (`tour/script.ts`, Priya,
`real: 'Holocene inbox-watcher'`, stops `memodesk`, `envelope`, `ledger`), and draws a recording as **a small dark reel
with an amber hub** (`TourWorld.tsx` HeroObject). So on the floor it is a burnt-orange desk (Priya's own `#C2410C`) up
in the control room on the mezzanine, because its C4 parent is Holocene (`c4.parent: holocene`) and the cast gives it
the `control` station.

Each relation the clips play gets one readable piece (code cites are `holocene/services/inbox-watcher/`,
`iw` = `inbox_watcher.py`, `mc` = `memo_common.py`):

- **The bell** (`agent-pad -> inbox-watcher calls POST WATCHER_WAKE_URL :8697/wake`): a brass desk bell. The pad's
  upload proxy rings it after every upload (iw:5557), so the desk does not wait for its next look.
- **The watch lamp** (`reads minio, mc ls delo/holocene-auto inbox/`): a gooseneck lamp over the riser mouth. The main
  loop ticks every second (`TICK_S = 1`, iw:372); with the bell proven live it still lists the shelf every 15 s as a
  backstop (`WAKE_BACKSTOP_S`, iw:390).
- **The riser from MinIO's shelf** (`reads minio, mc cp`): a steel pipe up from the floor at the desk's left (MinIO is
  east, the desk's left) with an open orange mouth. A *copy* of the tape comes out of it and rolls onto the player.
  The original never leaves the `inbox/` shelf: the watcher never moves or deletes it (only two `mc rm` sites, both
  stale reply audio, iw:2973, 3378). The copy lives in a temp dir (iw:1712) that is swept the moment transcription
  ends (`shutil.rmtree`, iw:1759), so the reel vanishes in Work, before the envelope is written.
- **The registry card file** (`reads agents-registry`, `registry_route()`, mc:194-224): a rotary card file. On
  receive the desk looks up the worker named in the tape's shelf address (`inbox/<agent>/<yyyy>/<mm>/<dd>/<file>`,
  `agent_from_key`, mc:133); an unknown worker fails fast (iw:1679).
- **The pink speaking tube to Wren** (`calls transcribe`, warm Whisper server first, `transcribe --no-diarization
  --ephemeral` as fallback, iw:1784, 1810): runs off the deck's left edge and down to the floor, toward the
  Transcription kiosk by the sound wing. Pink is the Voice zone's colour, as on the wax asset's tube. A pink lamp on
  the player is lit while the line is open; the typed transcript comes back up as a white slip.
- **The status board** (`writes minio status/<date>/<memo_id>.json`, rewritten at every stage, mc:150; the car's seven
  stages `received|transcribing|heard|working|replying|done|failed`, `car_stage`, iw:843): left column four amber
  lamps the clips light in order; right column `replying` and `done` (dark: they come minutes later) and a red
  `failed` lamp (dark: failure is not played).
- **The post-it pad** (`publishes-to bb-nats facts bloodbank.audio.memo.<stage>`, iw:1040): a yellow pad; a sheet
  leaves for the belt through the window's slot at each step the clips play (`received`, `transcribed`,
  `dispatched`).
- **The envelope, the stamp and the hatch lamp** (`publishes-to bb-nats command bloodbank.cmd.agent.invocation.invoke`,
  iw:2566; `calls bb-nats HTTP monitor :8222/jsz`, mc:830): a stack of blank kraft envelopes, a writing pad, a stamp,
  and a green lamp at the window slot. Before it sends, the desk checks the monitor for a puller on the express lane's
  consumer (`bloodbank-hermes-gateway-interactive`): the lamp lights. Every `bb-emit` runs `--strict` (the envelope is
  checked against its schema before it goes, iw:2566): that is the stamp. Then the envelope goes out of the slot
  toward the back belt.
- **The reply horn** (`calls vox /synthesize-url`): a pink horn over the window. Once the agent answers (102-231 s
  later, README "Measured on six real memos") the desk has Vox speak the reply. Static: no clip plays that far.

Beside it, the station's other members keep the look the primitive `ControlRoom` gave them: the mezzanine deck on four
posts, the visitor's window facing the belt, Holocene's screen and operator, its red notebook (the bible's "notebook
and visitor's pass", B6), and the stairs. They are static here. Holocene's wall is short and sits in the back-right
corner so it does not hide the desk from the forge's clip camera.

## The four clips

Every key pose sits on 0.1 / 0.5 / 0.9 of its clip. The item is the `env` the desk writes.

- **Idle (4 s, seamless):** the desk waits with the bell live. The watch lamp's bulb swells once a second (the main
  loop's `TICK_S = 1`) and its head sweeps the riser mouth and the trough. 0.4 s and 3.6 s: bulb bright, head left
  and right; 2.0 s: bulb low, head centred.
- **Accept (1.2 s):** the pad's upload proxy rings the bell (`POST /wake`). The card file turns once to the worker
  named in the tape's address (`registry_route`), the R lamp lights and a "received" post-it leaves through the
  slot; the T lamp follows at once (`done_stage received -> transcribe`, iw:1687). A copy of the tape comes out of the
  riser (`mc cp`) and rolls down the trough onto the cradle. A blank envelope is lifted from the stack onto the pad
  (`socket_in` -> `socket_hold`). 0.12: bell ringing; 0.6: post-it at the slot, tape in the trough; 1.08: tape on the
  cradle, envelope on the pad.
- **Work (3 s, loopable):** the tape spins with the pink line lamp lit, a bead runs down the tube to Wren and back,
  the level needle reads. At 1.18 s transcription ends: the line lamp goes out and the temp copy is swept (the reel
  lifts and vanishes, `rmtree`). The slip rises out of the player, the H lamp lights ("heard": the dispatch stage) and
  a "transcribed" post-it leaves. The slip goes into the envelope, the hatch lamp lights (a puller on the lane, `jsz`)
  and the `--strict` stamp comes down on the envelope. 0.3: spinning, bead in the tube; 1.5: slip up, post-it flying;
  2.7: stamp down, hatch lamp lit.
- **Emit (1.2 s):** the envelope lifts off the pad and goes out of the window slot toward the back belt
  (`bb-emit --kind command bloodbank.cmd.agent.invocation.invoke`); the runtime releases it at 0.6 s, in the slot.
  Then the W lamp lights ("working": the agent has it), the hatch lamp goes out and a "dispatched" post-it follows
  (published only after `bb-emit` returns, iw:2616). The board clears for the next memo while this one waits minutes
  for its agent. 0.12: lifting; 0.6: in the slot; 1.08: post-it at the slot, W lamp lit.

## Where it stands

`placement: station` at `control` (the cast), `replaces: ["ControlRoom"]`, `rotationY: 0`. The anchor turns it by pi,
so model +Z (the window and slot) faces the belt to the north, the riser and the pink tube stand on world east toward
MinIO and Wren, and the floor's cameras (south) see the back-left: the open rails, the desk's back, the tube and the
riser. Footprint 4.9 x 3.85 m (deck 3.5 x 3.4, stairs outside the right edge, riser outside the left), height 4.95 m.
The deck is at 2.8 m, lower than the primitive's 3.4, so in the forge frames the desk is the subject and not the legs.

## Rubric self-review

| # | Line | Max | Score | Why |
|---|---|---|---|---|
| 1 | Reads as the metaphor | 2 | 1.5 | A burnt-orange desk up in the control room with a bell, a lamp, a reel on a player, post-its and envelopes reads as "the memo desk". The riser still reads as a pipe more than a shelf feed, and the small props are small at 20 m. |
| 2 | Idle alive and seamless | 1 | 1 | Seamless (glbcheck 0.0); the 1 Hz bulb and the head sweep differ in all three frames. |
| 3 | The real job | 3 | 2 | Receive, transcribe, dispatch in the code's order: lamps by `car_stage`, the copy swept at the end of transcription, the post-it after the envelope. Lost: the item is a blank envelope from the start (the real envelope is written after the transcript), the beats are small in the clip camera, and the stamp is mostly hidden behind the stack. |
| 4 | Fits, faces traffic, no clipping | 1 | 0.75 | Window and slot face the belt, partners on the riser/tube side. The tape now comes out of an open mouth and vanishes above the player. Not checked frame by frame. |
| 5 | Palette | 1 | 1 | Holocene slate, Priya's orange, Voice pink only on the line to Wren and the horn; kraft envelopes, yellow post-its; no belt blue. |
| 6 | Budget, build | 2 | 1.5 | 13,676 tris, 329 KB, glbcheck all green, console has no errors. Held for the verifier. |
| | **Total** | 10 | **7.75 -> 7** | |

Round 1's three critics (readability, data truth, craft) scored it about 6. Their fixes, applied in round 2: Holocene's
wall moved out of the clip camera, a lower deck, the copy swept at the end of transcription, the R/T lamps together,
the dispatched post-it and W lamp after the envelope, seven stages on the board, the reply horn, the level needle, the
bead, an open riser mouth, the envelope lifted clear of the stack, a constant-speed reel. Round 3: lamps held lit for
a whole clip were dropped by the exporter (a constant channel falls back to the rest pose, off), now they breathe;
the stair handrail that crossed the desk was removed.

## For the integrator

- **No memo traffic reaches control.** The sim gives `control` a `post` copy of every belt note (Holocene's reads, no
  release) and nothing else; no waybill names `inbox-watcher`. So the desk takes `env` only, so it does not play a
  memo cycle for every belt note, and on the ambient floor it just idles. A memo source in the sim (a `bloodbank.audio.memo.*`
  fact stream, or a waybill that starts at the pad) would bring it to life.
- **Three members share control** (`holocene`, `holocene-api`, `inbox-watcher`). This asset draws Holocene's screen,
  operator and notebook statically. When Holocene gets its own asset, the two will need a Driver that routes each
  member's visits (the turn-enricher pattern).
- `src/content.ts`'s control view describes Holocene, not the memo desk.
- `shoot.py`'s `visit-*` frames send a `parcel`; this asset handles `env`, so those frames show Idle (known gap).
- The hatch lamp only shows the happy path (a puller on the interactive lane). `choose_lane` can also fall back to the
  batch lane after two probes or queue on interactive; one green lamp cannot say that.
