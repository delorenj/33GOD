# turn-enricher: the tagging desk

## What it is in the warehouse

The record (`components/turn-enricher.yaml`) says it "reads each finished agent turn and tags it with its main
action, artifacts and blocker", so that "downstream reports read typed facts from it instead of re-reading raw
replies". In the warehouse that is a **tagging desk** at the cataloguer's station: a clerk's desk in the Memory
zone's purple (`memory` = `#7C4DBA`, `SET_DOMAIN.cataloguer`) that takes a copy of every `turn completed` post-it,
reads it, asks two outside experts, writes what they said on a fresh post-it and puts that back on the belt. The desk
has no clerk: the service is automated, so its instruments move on their own.

Each of the record's four wires gets one readable piece:

- **The copy in** (`consumes-from bb-nats`, `bloodbank.evt.conversation.turn.completed`, `main.py:68`): a tin
  **in-tray** at the front-left of the worktop and a slanted **reading lectern** with a warm reading lamp. The desk
  has no clip wire to the belt: `main.py` reads with a plain core `nc.subscribe`, no durable, no ack, so it only
  sees turns that arrive while it listens. The copy is a reader's copy and fades on the lectern once the desk is
  done with it (the floor's own copies fade the same way, `Moving.tsx`).
- **Line 1, Jev** (`calls jev-litellm`, `POST https://jev.delo.sh/typesafe/v1/systemone`, `main.py:73`): a desk
  **phone** (an outside call) whose handset rattles while the desk asks; the amber lamp on the gauge's housing is
  line 1 and lights while the desk asks Jev its one question, `signal` ("does this turn contain substantive work
  output?"). Jev's answer drives the big **signal gauge** on its post: a half dial,
  red from 0 to 0.5 (noise), green from 0.5 to 1, a dark tick at the threshold (`SIGNAL_THRESHOLD = 0.5`,
  `main.py:92`). Below the tick the turn is counted as noise and dropped; nothing is written.
- **Line 2, Clairic** (`calls cloudflare`, Workers AI `@cf/cloudflare/clairic`, `main.py:164`): the amber lamp on the
  lavender **facts board** is line 2; it lights while the desk asks Clairic for the three facts, and the board fills
  in. Three rows, one per field Clairic returns (`clairic_facts`, `main.py:176-193`): **action** (one white card
  with one written stroke: "the single main action, a 2-4 word verb phrase"), **artifacts** (four cream tabs: `MAX_ARTIFACTS = 4`, `main.py:96`), **blocker** (one red
  tab). A tab flips up only for a field Clairic gave (`p_null < 0.5`).
- **The post-it out** (`publishes-to bb-nats`, `bloodbank.evt.conversation.turn.annotated`, `main.py:69`): a yellow
  **pad** of post-its on the right of the worktop and a **pen arm** that writes the facts on the top sheet; the new
  post-it lifts off the pad and stands up, facing the camera, before the floor takes it.

Beside it, the station's other member keeps the look the floor's primitive gave it: the **Candystore enricher**
(`enricher`, same station in the cast) is the ochre desk, its ochre clerk and its green Dapr runner on their own
plinth at the left. It is static here; its copies land on its blotter and its summaries leave from its runner
(see *The four clips*).

## The four clips

The sim never sends this desk anything of its own: its only `cataloguer` traffic is the Candystore enricher's
`session ended` copy (`sim.ts:198`), and it has no `turn completed` kind at all. The desk's cycle runs for waybill
visits (`turn-enricher` stops) and the forge's visits. `Driver.tsx` (contract section 5) sorts the station's
traffic: a `session ended` copy, or a waybill visit tagged for the `enricher` but not the `turn-enricher`, glides
from where its flight ended onto the ochre desk's blotter and lies there; after the sim's own 2.6 s (`handOff`) the
summary leaves from the green runner (`release` with the runner's point) and the copy goes. Several of them run at
once, as the sim's own timers do. Everything else plays the contract's four clips, one turn at a time at the floor's
speed (`main.py` handles turns in order and never hurries, so the Driver does not speed up for a queue).

- **Idle (4 s, seamless):** the desk is subscribed and waiting. The reading lamp breathes and the gauge's needle
  trembles at rest on zero. First and last keys match on every channel.
- **Accept (1.0 s):** the copy of the `turn completed` post-it glides (eased) into the in-tray (`socket_in`), the
  tray dips under it and springs back, and the copy slides up onto the lectern (`socket_hold`), lying on its slope.
  The Driver sinks the thin copy onto each surface so it does not hover where a post-it's socket sits.
- **Work (2.5 s, loopable):** the turn is read and tagged, in the order `TurnEnricher.handle` runs
  (`main.py:327-366`). The reading lamp brightens; the handset lifts and the gauge's line-1 lamp lights (Jev); the
  needle swings up through the threshold into the green; line 1 goes dark and the board's line-2 lamp lights
  (Clairic); the action card flips up, then one artifact tab per artifact, while the blocker tab only twitches; the
  pen arm winds up and writes two lines on the pad's top sheet. In the last quarter second the board clears and the needle drops back, so the first key equals the
  last. The glb carries the two turns the waybills recorded: `Work` is the codex `ls` turn (signal 0.86, one
  artifact, no blocker) and `Work_B` the claude README turn (signal 0.55, four artifacts, no blocker). For a waybill
  visit the Driver picks the variant nearest the loaded waybill's own `turn-enricher` span (`attrs.artifacts`);
  otherwise it alternates. Neither recorded a blocker, so the blocker tab never rises. On the floor the new post-it
  lies on the pad from the moment the pen comes down (1.98 s), and the Driver draws each fact on it as the pen
  finishes that line: a dark stroke as long as the action phrase (2.13 s), then one purple tick per artifact (2.3 s).
- **Emit (1.0 s):** the copy fades on the lectern; the new post-it (`socket_out`) lifts off the pad, turns upright
  and rises to stand above the desk's front-right corner, facing the front-right cameras, with the facts written on
  it (the facts the pen wrote stay on it, both faces). The runtime hands it to the floor at half time
  (`bloodbank.evt.conversation.turn.annotated`, a core `nc.publish`, no PubAck). The pen arm parks.

Not drawn, because the record or the code gives no picture of it here: the noise branch. A turn under 0.5 is
dropped before Clairic and produces no event, so no waybill or visit ever carries one and no clip could honestly
play it; the gauge's red half and threshold tick are the gate's scale, and the needle always lands in the green
because only turns that passed are ever seen. Also not drawn: extractor pushback (a 429 pauses the
desk for Retry-After and counts, not queues, what arrives meanwhile), the per-minute stats line and the skipped
subagent turns.

**Sockets.** `socket_in` lies flat in the in-tray and travels up onto the lectern in Accept. `socket_hold` lies on
the lectern's slope under the lamp. `socket_out` starts flat on the pad's top sheet and rises to stand upright
above the pad in Emit.

## Where it stands

It IS the `cataloguer` station (`cast.generated.json`, placement `station`) and replaces the primitive
`Cataloguer`, which drew the enricher's desk, clerk and runner; the asset redraws those three in the same colours
and roughly where they stood (desk on the left half, runner at the left end), so nothing the floor relies on goes
missing. The anchor is `rotY = 0` (`anchors.ts`): model axes are world axes, origin on the floor at `CATALOGUER`
`[4.6, 0, 2]`.

Clearances in model space (x right, z front): the floor's "Enricher" sign (`Props.tsx` SIGNS.cataloguer, w 1.4)
hangs at z 0.45-0.49, 0.35-0.76 m up, x -0.73..0.73; nothing in that band comes forward of z 0.44 (the enricher's
desk front is at z 0.28, the tagging desk's at z 0.3). The glass shaft and day ruler stand at x -2.05; the runner's
left side is at x -1.72. The tour's newcomer stands at (-1.2, 1.4), in front of the runner. Two plinths (the
enricher's x -1.78..-0.44, the tagging desk's x -0.34..1.66) with a gap between them, so the two members read as two
desks. Footprint 3.5 x 1.5 m (built 3.49 x 1.44), height 2.7 m (built 2.60: the gauge housing's top). The gauge
and board yaw 0.25 rad toward the station camera (front-right).

## Rubric self-review

Two rounds. Round 1 (8.1k tris) was read by three unanchored critics (readability, data-truth, craft): readability
about 6/10, the out post-it was indistinguishable from the copy and popped in, the line lamps on the phone were
unreadable, the queue speed-up was invented, the ochre clerk read as the tagger, the copy hovered and idle was too
still. Round 2 fixed each: lamps moved onto the instruments they stand for, the desk unmanned and on its own
plinth, a lavender board with coloured tabs, facts written onto the new post-it as the pen lands, variant chosen
from the waybill, no queue speed-up, thin items sunk onto their surfaces, idle needle tremble and lamp breathing.

| Line | Max | Score | Why |
|---|---|---|---|
| Metaphor at 20 m and close | 2 | 1 | Close up the gauge (red/green, threshold tick), the three-row board and the pad read clearly. At 20 m (`situ`) the gauge reads but the board's tabs and the phone are small, and the unmanned desk sits behind the ochre clerk, who still looks like the one doing the work. |
| Idle | 1 | 1 | Lamp breathes, needle trembles; seam 0.0. |
| Accept / Work / Emit | 3 | 2 | Caught (tray dip), worked in the order `handle` runs (Jev gauge, then Clairic board, then pen) and stood up facing the camera. The facts on the new post-it exist only in the Driver, so forge stills show it blank, and the Driver's floor cycle was type-checked but not filmed on the floor this run. |
| Fit | 1 | 1 | Clears the sign band, shaft and tour spot; faces the front-right cameras; no clipping in `turn-*`. |
| Palette | 1 | 1 | Memory purple (`#7C4DBA`) for the desk, the primitive's ochre/green kept for the enricher, blue left to the belt. |
| Budget / build | 2 | 2 | 8,500 tris, 226 KB; glbcheck all ok; tsc clean; console clean. |
| **Total** | 10 | **8** | |

## For the integrator

- **One station, two components.** `cast.generated.json` puts both `enricher` (Candystore enricher) and
  `turn-enricher` at `cataloguer`; `discover()` gives the body to the first id in sort order, so this asset owns the
  station only while `enricher` has no asset. If `enricher` is forged it will take the station first and this desk
  will vanish. A station with two members wants one shared asset (this one already draws the enricher's corner) or
  a `near:` annex for the second.
- **The panel copy describes the other member.** `content.ts` names the cataloguer station "Enricher" and its text
  is the Candystore enricher's summary; it says nothing of the turn-enricher.
- **The sim has no `turn completed` traffic.** Its kinds are turn started, session ended, summary written, tick
  fired and invocation completed; on the ambient floor this desk only ever idles. A `turn completed` post-it on the
  front belt, copied to `cataloguer` and answered with a `turn annotated` post-it, would let it work.
- **`shoot.py` always sends a `parcel` visit**, which this desk (`handles: ["post"]`) filters out, so its `visit-*`
  frames show Idle; `visit(id)` with no kind would send `post`.
- **Blender hung on gvfs.** A build that timed out at 300 s with no output was Blender blocked on a stuck
  `gvfsd-mtp` FUSE backend under `/run/user/1000/gvfs` (`/proc/<pid>/wchan` = `request_wait_answer`). Killing the
  backend fixed it; `build.mjs` could pass Blender a scrubbed `XDG_RUNTIME_DIR` or a shorter timeout with a hint.
- **The record is silent on the noise gate's share.** Jev's `signal < 0.5` drops a turn without an event; the stats
  line (`noise=`, `annotated=`) would give the ratio the floor could draw.
