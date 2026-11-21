# candybar: the clock

## What it is in the warehouse

The bible (section 4.1 card 15, section 4.2 "Candybar: the clock") makes Candybar **the clock**: "one big bell on
the wall. When it rings, a planner reads the chore chart and writes an envelope for each chore due." The contract's
own example says the same: "the clock rings and drops envelopes". The record says it in engineering words: Candybar
is "the single clock that starts every recurring job on time" ("Bloodbank-driven cron registry, minute dispatcher,
host executor"), and "without it no recurring work runs, including Krebs dispatch and the daily report".

The model is a squat clock tower in the Triggers zone's red (`C.clock` = the `triggers` domain colour `#B23A48`),
with darker red corner pilasters, cream band courses and a brass bell in an open belfry under a dark red pyramid
roof. It stands 5.8 m, under the floor's 6 m cap, and the record's three real parts each get one readable piece at
a size that reads together:

- **The heartbeat** (`relations`: `publishes-to bb-nats` via `bloodbank.evt.cron.tick.fired`,
  `heartbeat/publisher.py:53`): the **bell** and its **hammer** in the belfry, the **pendulum** behind a window on
  the front, and a **cuckoo house** above the face (a brass gable over a pair of red doors), out of which the tick
  post-it comes onto a brass perch. As on a real cuckoo clock, the door is above the dial.
- **The registry** (`stores-in postgres`, "candybar registry DB"; the record's evidence counts 139 jobs): the
  **chore chart** on the tower's right side, a rack of 20 time cards (house style: the crew hall draws 4 desks for
  its 68). Each card's stripe is a runner kind. The record gives the total but no split, so the split is taken
  from the manifests on disk on 2026-11-21, deduplicated by name (114 of them: 57 `systemd`, 33 `exec`, 12
  `hermes`, 12 `n8n`): 10 black (systemd units), 6 red (exec: the clock's own hands), 2 teal (hermes runner, the
  crew hall's colour), 2 grey (n8n runner webhooks, the rules cabinet's colour). That is the bible's "the clock owns
  *when*, not always *who*", and the record's `schedules` wires to the executor, Hermes and n8n.
- **The dispatcher** (`consumes-from bb-nats`, durable `candybar-dispatcher-ticks`, `dispatcher/role.py:77`;
  `publishes-to bb-nats`, `bloodbank.cmd.cron.candybar.invoke`, `dispatcher/worker.py:312`): a big cream **punch
  clock** at the tower's right foot, directly under the chart, with a light tin in-tray (green lip: IN), a reading
  plate, a **press** whose light steel ram (smaller than the copy, so the copy shows round it) stamps the copy, a
  green "listening" lamp on the press and a tin **envelope chute** with red rails (OUT) on a cream pedestal, a stop
  at its foot. The planner at the desk in front (the floor's own `ClockCrew` prop) hands it the tick copy.

The **clock face** shows the floor's own time: its hour and minute hands are not keyed in any clip; `Driver.tsx`
turns them from `hoursNow()` every frame, exactly as the primitive `Clock` did (on the forge's stage, where the sim
never runs, they read 8:00, the floor's start hour). The **pendulum** is not keyed either: the Driver swings it
(2 s period, 0.22 rad) on the floor's time, so no clip change or crossfade ever snaps it, and it stops with the sim.

## The clips

The sim sends this station two different items, both of kind `post` (`src/sim/sim.ts`):

1. `tick fired` (every 5-7 s, "drawn far less often than the real one-a-minute tick"): the heartbeat's own
   post-it, which the floor then sticks on the front belt.
2. `chore due` (after the planner tears a copy of a tick off the belt, 55% of ticks): a copy in, an envelope
   (`bloodbank.cmd.cron.candybar.invoke`) out, which the floor sticks on the back belt for the hands.

A generic Accept -> Work -> Emit cannot tell the two apart, and playing one sequence for both would ring the bell
for a chore and read the chart for a tick the dispatcher has not consumed yet. So `Driver.tsx` (contract section 5)
plays a fifth clip, **Strike**, for a `tick fired` visit, and the contract's four clips, which are the
**dispatcher**, for every other visit (the planner's `chore due`, a waybill copy, a forge visit). The forge's pose
shots show the four contract clips.

- **Idle (4 s, seamless):** the heartbeat sleeping until the next minute boundary, and the dispatcher's durable
  clip waiting on the belt. The green lamp on the press breathes, the chart's scanner light drifts at the top row,
  the bell sways a hair (and the Driver's pendulum swings). First and last keys match on every channel.
- **Accept (1.0 s):** the planner's tick copy is caught in the punch clock's in-tray at the front (`socket_in`;
  the runtime eases it in from where the floor's flight ended), the tray dips under it and springs back, the lamp
  blinks twice (a message on `candybar-dispatcher-ticks`), and the copy slides up onto the reading plate under the
  press (`socket_hold`).
- **Work (2.0 s, loopable):** the dispatcher matches the chore chart against this minute (`worker.py`: every
  registry entry is matched against the tick's minute): the amber scanner sweeps linearly down all four rows
  (0.05-0.85 s), and the due card steps out of its slot and turns as the bar crosses its row. The press winds up
  and brings the ram down on the copy at 1.02 s and holds it there: the envelope's safe-to-repeat code is the
  candybar id plus the tick's minute (`command_for`: `identity = f"{entry.id}:{tick.data.tick_id}"`, `uuid5`). The
  Driver draws that code as a dark red ink mark on both faces of the copy from 1.0 s, and it rides the item down the
  chute in Emit. The ram lifts, the card goes back, the scanner returns to the top. The glb carries four variants,
  one per runner kind, each popping that kind's card: `Work` (exec, the krebs-tick card: the record's first wire,
  `krebs-tick.candybar.toml */10`), `Work_S` (systemd), `Work_H` (hermes), `Work_N` (n8n). The dispatcher sends the
  same invoke command whatever the runner, so the Driver rotates them per visit in the chart's proportions (S E S H
  S E S N S E: 5 / 3 / 1 / 1). One card per visit, because the sim sends one `chore due` per envelope.
- **Emit (1.0 s):** the runtime swaps the copy for an envelope (`out: 'env'`); the out flap drops and `socket_out`
  slides it off the plate and down the chute on the machine's right side, toward the camera; the runtime hands it
  to the floor at half time, which sticks it on the back belt for the hands (`publishes-to bb-nats`,
  `bloodbank.cmd.cron.candybar.invoke`). The flap closes and the lamp settles to the Idle pose.
- **Strike (2.2 s, Driver only):** the heartbeat publishes. The hammer winds back and holds, strikes the bell
  twice (0.32 s, 0.6 s), the bell swings away and settles, the cuckoo doors open (0.38-0.56 s), and the tick
  post-it (shown from 0.5 s) rides `socket_tick` out onto the perch by 0.9 s and stands there; the Driver hands it
  to the floor at 1.4 s, which sticks `tick fired` on the front belt (`bloodbank.evt.cron.tick.fired`,
  `heartbeat/publisher.py:53`). The doors close behind it (1.6-1.85 s). One strike per tick, never for a chore.
  The heartbeat does not wait on the dispatcher: a queued `tick fired` visit jumps the queue.

Not drawn, because the record gives no moving picture of it here: misfire coalescing and operator skips
(`worker.py`), the API's steward command (`candybar-steward` is its own component, a kiosk near the clock), the
reversible migration ledger, and the executor's run of the chore (`candybar-executor`, drawn today as the
`ClockCrew` hands).

**Sockets.** `socket_in` starts in the in-tray in front of the punch clock, lying flat, and travels up onto the
reading plate in Accept. `socket_hold` lies flat on the plate under the ram. `socket_out` starts on the plate and
runs off its right edge and down the chute to its foot. `socket_tick` (a fourth empty, read only by the Driver)
starts inside the cuckoo doorway, upright and facing front, and slides out onto the perch.

## Where it stands

It IS the `clock` station (`cast.generated.json`, placement `station`) and replaces the primitive `Clock` only.
`ClockCrew` (the planner's desk and the hands' desk) stays: the sim flies tick copies to `PLANNER` and envelopes to
`HANDS`, and the hands are the `candybar-executor` component. The anchor turns the model's front (+Z) to face
south-east (`anchors.ts`, `rotY = pi/4`), toward the belt and the planner. The tower's front wall is at model z
0.75 (pilasters to 0.80), right behind the floor's "the clock" sign (`Props.tsx` SIGNS.clock, model z 0.82,
1.15-1.65 m up), which hangs between the door and the pendulum window; nothing on the front sticks out in that band.

Clearances in model space (x right, z front), worked from `layout.ts` and `tour/sets.ts`: the planner's desk
starts at z 1.47 and its person stands at (0.60, 1.66); the in-tray's lip stops at z 1.14 and the perch's lip at
z 1.13 (3.7 m up). The tour's cast stands at (1.98, 1.13); the chute and its stop end at x 2.23, the front rail at
z 0.60. The hands' desk corner is at (-1.56, -1.56), 0.7 m from the plinth corner; the clock's kiosk annex starts
2.4 m out at the back right. Footprint 3.3 x 2.2 m (the punch clock and its chute stand out to the right; the bbox
is 3.28 x 2.19, centre offset 0.59 m to the right), height 5.8 m (the model measures 5.79).

## Rubric self-review

Two rounds. Round 1 went to three independent critics (art, animation, fit); round 2 took their findings: the
dispatcher's contrast (tin tray and chute, IN/OUT colours, a steel ram smaller than the copy, a pedestal for the
chute), bigger chart cards and stripes, the cuckoo gable and perch, a bigger hammer, the scanner's linear sweep with
the pop timed to the crossing, four Work variants, the ink mark, the Driver's pendulum, a longer Strike and its
perch dwell, tick-first queueing, and the Idle freeze after a pause.

| Line | Max | Score | Why |
| --- | --- | --- | --- |
| Metaphor | 2 | 2 | Bell, cuckoo and pendulum (heartbeat), chore chart striped by runner kind (registry), punch clock and chute (dispatcher): each from the record. |
| Idle | 1 | 1 | Seamless 4 s (seam 0.0); lamp, scanner and bell; the Driver's pendulum never snaps and thaws after a pause. |
| Accept / Work / Emit | 3 | 2.5 | Catch and dip, scan and pop, stamp with a visible mark, envelope down the chute. The popped card is small at 20 m. |
| Fit | 1 | 0.5 | Inside its footprint, clear of the desks, sign and annex; but the station camera sees the heartbeat edge-on (below). |
| Palette | 1 | 1 | Triggers red, cream, brass; teal and grey only on the chart stripes. |
| Budget / build | 2 | 2 | 10,542 tris, 266 KB; glbcheck, tsc and the shoot clean. |

Total 9 by the lines, scored down to **8**: the heartbeat, the half that says "clock", reads poorly from the
station camera.

## For the integrator

- **The station camera sees the clock's front edge-on.** `content.ts`'s clock view (pos `[1, 7.5, -9.5]`, target
  `[-5.2, 2.8, -4.6]`) sits at about (7.4, 2.5) in the model's space, about 70 degrees off the front: the chart
  and punch clock face it, but the dial, cuckoo house and Strike's post-it are a sliver. Moving the view to about
  `[3, 7.5, -6.5]` (target unchanged) puts dial and chart each about 45 degrees off. Turning the asset instead
  (`rotationY`) is not free: the tower's front corners stand at z 0.80 and the floor's sign at 0.82, so any turn
  pushes a corner through the sign.
- **`AssetBody.tsx` freezes Idle on a pause and never thaws it.** It sets Idle's time scale to 0 when paused,
  guarded by `isRunning()`, which is false once the time scale is 0, so Idle stays frozen after unpause until a
  visit ends. This Driver remembers who froze it (a `froze` ref; see `Driver.tsx`); the same fix belongs in
  `AssetBody`'s `sc.idle` line so it reaches every asset.

- **The 6 m height cap is not written down where a forge agent reads.** `factory_forge.py verify` fails
  `manifest-height` above 6 m, but `forge/CONTRACT.md` does not state the cap and `glbcheck.py` does not check it
  (it only checks the model against the manifest's own height). Last night's candybar (6.9 m, self-scored 8)
  passed every glbcheck line and failed the verify on this alone. Put "height <= 6" in the contract's asset.json
  table and in glbcheck.
- **`shoot.py` always sends a `parcel` visit** (`__factoryForge.visit(id, 'parcel')`). An asset that takes only
  `post` (or `env`) filters it out, as the contract says it should, so its `visit-*` frames show Idle. Calling
  `visit(id)` with no kind already sends the asset's first `handles` kind (`forge.ts`); shoot.py should do that.
- **A Driver does not know it is on the forge's stage.** `AssetProps` has no `stage`, and the sim is paused there,
  so a Driver that copies `AssetBody`'s speed rule plays nothing on the stage. This one checks `STAGE_ID === id`.
  Also, under a Driver `AssetBody` returns before it sets Idle's time scale, so this Driver does that itself.
- **The forge's frames cannot show Strike.** `pose()` takes only the four contract roles and `visit()` sends no
  tag, so Strike is seen only on the ambient floor. A `visit(id, kind, tag)` would let shoot.py film a Driver's own
  clips.
- **The hands are the executor.** When `candybar-executor` gets a body, `ClockCrew`'s hands desk should go with it;
  the planner's desk is Candybar's dispatcher and could fold into this asset then.
- **The record has no runner split.** The chart's stripes come from the manifests on disk (see above); a
  `runners:` count in the record (or the Atlas live audit reading `GET /candybars`) would make them data-true by
  construction.
