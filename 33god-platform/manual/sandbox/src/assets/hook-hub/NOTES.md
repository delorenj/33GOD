# hook-hub: the receiving dock

## What it is in the warehouse

The bible (section 4.1 card 5, section 4.2 "hook-hub: the receiving dock") makes hook-hub the **receiving
dock**: parcels in, post-its out. The record says the same thing in engineering words: hook-hub "receives every
agent hook and fans it out to handlers that publish, remember and alert", and "without it agent activity never
reaches the bus, memory or state machine".

The model is a cutaway dock shed in the dock's orange (`C.dock`) on a raised concrete platform with a
hazard-striped lip, trimmed in Bloodbank blue (the `bloodbank` zone colour, `#2563EB`): the copings, the front
canopy, the corner posts, the conveyor rails and the frame of the back slot. The south side (model +X) is left
open so the floor's cameras see inside, the way the floor shows every station.

- **Front (model +Z, faces west, toward the courier):** a dock canopy over the receiving door, a strip curtain
  in the door, the incoming roller conveyor (the courier's conveyor ends here; bible 3.4 rule 1 says it is
  horizontal rollers), rubber dock bumpers, a green OPEN lamp on the lintel, a knee wall beside the door (so the open side sees the
  curtain and the rollers), and the **driver's window** with its briefing-card
  sill and a stopwatch.
- **Inside:** the opening bench with a turntable (`socket_hold` rides it), a label reader with a red beam, the
  clerk, the **house stamp** over a yellow post-it pad, and a purple **phone to the lessons library**.
- **The job-card wall (model -X, the back wall, facing the open side):** **36 job cards**, one per row of
  `handlers.toml` at the record's import (record `evidence`: "handlers.toml (36 handlers)"). The 15 **window
  cards** (`mode = "sync"`, the courier waits for them) hang on the front board, each with a red stopwatch dot;
  the 21 **back-room cards** (`mode = "async"`) hang on the back board. Card colours are their real families:
  purple = Hindsight or Candystore (remember / recall), amber = notify and lights (alert), red = the two guards
  (`native-clock-guard`, which reads Candybar's policy, and `crank-keys-guard`), white = everything else. One
  back-room card hangs grey and crooked: `asm-blocked-amber` is `enabled = false` ("Lands OFF on purpose").
- **Back (model -Z, faces east, toward the belt):** the letterbox slot with a flap and the out-chute where the
  post-it leaves for the belt, and the **receipt printer** (the factory alias `hook-hub-receipts`).
- **Roof:** a box -> post-it icon (the primitive's own picture, kept) and the amber **alert beacon**.

## The four clips

The parcel the floor sends is a prompt parcel (`sim.ts`: the dock hand-off writes "turn started"). Work plays
what hook-hub does with **a Claude Code `prompt_submit` parcel**, read card by card from `handlers.toml`.

- **Idle (4 s, seamless):** the green OPEN lamp breathes (the dock is open; the floor's primitive draws a
  closed dock as a shutter, so an open door is the honest idle), the clerk shifts weight, the strip curtain
  sways in the draught, the label reader's head drifts. Every channel's first and last keys match.
- **Accept (1.2 s):** the parcel is caught at the end of the incoming rollers (`socket_in`, outside the door),
  the clerk leans in, the strip curtain parts strip by strip as the parcel pushes through, and `socket_in`
  carries it along the rollers onto the turntable, where it settles. This is the record's "receives every agent
  hook" and the `bb-hook -> hook-hub` relation (the conveyor is its unix socket).
- **Work (2.4 s, loopable):** hook-hub matches the parcel's role against the cards (`on = ["prompt_submit"]`).
  The turntable turns the parcel under the label reader's beam (reading the vendor's label). Then the **five
  window cards** that match a Claude prompt swing out in turn and stay out until all five have answered (`skill-reminder`, `crank-tag`,
  `hindsight-recall`, `codegraph-prompt`, `hub-selftest`), the stopwatch at the window runs while they do, the
  clerk lifts the purple **phone to the library** (`hindsight -> calls`, via `concerns.py` handlers) and a
  **briefing card** is pushed out of the driver's window (the sync answer, `additionalContext`, bible section 2).
  Then the window cards drop together and the **three back-room cards** swing (`hindsight-turn`, `nanoleaf`, `orca-status`), the amber beacon
  flashes for `nanoleaf` (the light panel: "alert"), and the **house stamp** comes down on the post-it pad: the
  synthesized `bloodbank-publisher`, the `agent-hooks` relation ("handlers.toml publisher handler"), which
  writes the one house post-it. 8 of the 36 cards move; the other 28 stay still, because they do not match.
- **Emit (0.9 s):** the back flap swings open and `socket_out` carries the new post-it, lying flat, from the
  pad up through the letterbox slot (it is in the slot at half time) onto the out-chute (`bb-nats -> publishes-to`, `BLOODBANK_EVENTS`); the
  runtime hands it to the floor at half time and the floor walks it to the belt. At the same time the receipt
  printer feeds a receipt: hook-hub's own observation publish (`observations.py:41`, an `HPUB` with
  `Nats-Msg-Id` and `Nats-Expected-Stream`, which waits for JetStream's ack: the bible's "registered" counter,
  B16). Everything settles to the Idle pose by the last frame.

**Sockets.** `socket_in` starts on the incoming rollers 0.25 m outside the door at parcel height and travels to
the turntable during Accept. `socket_hold` is a child of the turntable, so the parcel turns with it in Work.
`socket_out` starts just above the post-it pad (where the stamp wrote the note), is rotated 90 degrees so a
post-it lies flat, and leaves through the slot to the chute's end, 0.15 m beyond the back wall.

Not drawn, because the record or the code does not support a moving picture of it: the `candystore` read (a
lookup at the archive's counter, `concerns.py:293`) and the `candybar` read (the clock guard's policy file) are
present only as their cards on the wall. The ASM socket (`asm -> hook-hub`) is the ASM kiosk's own job.

## Where it stands

It IS the `dock` station (`cast.generated.json`, placement `station`) and replaces the primitive `Dock`. The
station anchor turns the model's +Z to face west (`anchors.ts`, `rotY = -pi/2`), so the receiving door looks at
the courier's conveyor (`DOCK.door`, world x -11.5 = model z +2.0) and the back slot looks east at the belt
(`DOCK.out`). The open south side (model +X) faces the dock's station camera and the overview, and carries the
sign rail at model x 2.05, right behind where the floor's RECEIVING sign hangs (`Props.tsx` SIGNS.dock, world
z 2.13), so the sign reads as mounted. The platform stops at model x 1.85, clear of the label desk's clerk
(world z 1.9-2.3). The north wall (model -X 1.85) stays 0.5 m clear of the dock's kiosk annex (world z -2.35).
The roof icon and beacon stay under 3.5 m, below the Normalization bulb (world y 4.1) and the station label
(y 4.9). Footprint 4.0 x 4.6 m (the canopy and bumpers overhang at the door, the chute at the slot), height 3.5 m.

## Rubric self-review

Three shoot rounds (`/tmp/forge-hook-hub-r1..r3`), console clean every round. 10,032 tris, 304.5 KB, glbcheck all
green.

| Criterion | Score | Why |
| --- | --- | --- |
| Reads as its metaphor | 8 | Orange dock shed, door and curtain in, slot out, box->post-it roof icon: the primitive's picture, now with an inside. |
| Record-true behaviour | 8 | 36 cards from `handlers.toml`, sync vs async boards, real families, the disabled card, the 8 that match a Claude `prompt_submit`. |
| Clip readability | 6 | Accept, the stamp, the phone, the beacon and the Emit slot read from the hero angle; the card fan-out reads only up close, and at floor scale it is a flicker. |
| Craft / polish | 6 | Clean silhouette and palette; the north and east faces are flat orange slabs and the clerk is a blob behind the turntable. |
| Fit in situ | 8 | Sign hangs on the rail, clears the label desk, kiosk annex and bulb; matches the floor's toy style. |
| **Overall** | **7** | Ships. |

Fixed across rounds: r2 cut the front wall beside the door down to a knee wall (the parcel and curtain were hidden
during Accept), slowed Emit so the item is caught in the slot at half time (it was behind the back wall), and
brightened the beacon lens (it read as a brown blob). r3 held the window cards out until all five answer (single
frames missed the fan-out), and dropped the front corner post that doubled the sign-rail post in front of the door.

Biggest remaining weakness: the post-it leaving is only half seen from the hero angle (the slot faces the belt,
away from the open side), and the outside of the shed (north and east walls) has no detail.

## For the integrator

- **The visiting item's look in forge poses and forge visits.** `AssetBody` `pose()` shows the first
  `handles` kind for Accept, Work *and* Emit, and `__factoryForge.visit()` sends no `out`, so forge frames show
  a parcel leaving through the slot. On the real floor the sim's dock hand-off passes `out: 'post'`, so a
  post-it leaves. A `pose()` that used the visit's `out` (or the asset's) for Emit would make the shots honest.
- **The record is two cards stale.** `handlers.toml` gained `crank-attach` and `crank-detach` (both async) on
  2026-11-18 (bloodbank `482e4d0`, BB-42): 38 rows now, 37 enabled. The model draws the record's 36. Re-run the
  Atlas import and the wall grows two back-room cards.
- **The shut dock.** The primitive `Dock` drops a shutter when `useWorld.dockShut` is true (the fail-open
  lesson). A glb cannot read store state, so with this asset loaded that picture is lost. A small `Driver.tsx`
  or a runtime hook that scales a named node (`door_shutter`) from `dockShut` would bring it back; this model
  has no shutter node yet because nothing could drive it.
