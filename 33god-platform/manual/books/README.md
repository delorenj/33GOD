# Book plan

Status: plan v0, 2026-11-11. Only **Book 1 page 1** has a storyboard. Everything else is a title and an intent, to be revised from Damian's tell-backs. Grammar: [`../grammar/v0.md`](../grammar/v0.md). Meter: [`../scale-meter.md`](../scale-meter.md).

Rules for every book:

- A book is a route of 3-8 pages that ends on a finished "you built it" picture. It opens with a goal postcard identical to that last picture.
- One page, one idea, one screen. Page 0 (Cast and Signs) is optional. Every page works without it.
- **Concept books are drawn for the reader's own box** (an edition) but contain **no install state**. Bags and open or sealed waves live only in the Build book.
- Every concept book ends on a blank **"Your Town" sheet**: empty machine plate, empty wall, the four lines, a role key, and three prompts. What happens in your app? Who announces it? Who listens? This is the on-ramp for wannabe engineers.
- Before any page ships: read the "Forbidden" list in the grammar (section 9), run the evidence sheet, and re-probe the reader's box.

## Book 1: Announce, Don't Call (the event path; the thesis)

Goal: the reader can say why 33GOD is built from announcements on a bus that remembers, and why it is not services phoning each other. This is the "why an event system on NATS and Dapr" book.

| Page | Title | One idea | Atoms introduced | Evidence anchors |
|---|---|---|---|---|
| 0 | Cast and Signs | Picture-only inventory: Blip, You, the four roles, the four lines, the three marks. | Inventory | Grammar |
| **1** | **Press Enter** | You press Enter, a note is pinned on the bus, the bus keeps it a week, Candystore reads it. Nobody phones anybody. | Blip, wall, calendar, NOTE and ASK lines, copy rule, check/X frame, squint | `streams.json`, `hub.py:611`, `nats_publish.py`, `pubsub.yaml`, `main.py` `do_POST`. [Storyboard](book-01/page-01.storyboard.md). |
| 2 | Off? Notes Wait | A listener that was asleep catches up from its own bookmark. Two listeners, two bookmarks. The oldest note ages out after 7 days. | Bookmark flag on the wall, multi-builder, dashed seat (absent on this box) | `W3-1.md` line 148 (728 earlier rows in 20 s on Damian's Mac, 0 redelivered). Returning-listener resume only. |
| 3 | Ask or Announce? | Announce a fact when nobody needs to answer. Ask when you must wait. A hook is an ask, a publish is not. Draws bb-hook, resolves wink 3. | ASK in full, hourglass, bb-hook | `handlers.toml` (`candystore-context` sync 5000 ms, `hindsight-recall` sync 11000 ms), `hub.py:611` async publisher, `W2-4.md` hang bound. Hindsight retain is async (`handlers.toml`). |
| 4 | How Deep? | How deep something nests, taught on things already met: the wall (a stream) is inside NATS, inside Bloodbank, inside 33GOD. Plates are a different thing. | Level meter, baseplate, plates versus levels, squint on flattened "kind" | `scale-meter.md`; map chain `god33 > bus > nats > stream-evt`. |
| 5 | Plug In Another | A new listener appears and the speaker does not change. A new listener starts by its own rule: from the start (Candystore) or from now (Enricher). | Contract tags in full (tiles), independent badge, multiplier | `pubsub.yaml` deliverPolicy `all`, `enricher-pubsub.yaml` deliverPolicy `new`. New-listener start only, never mixed with page 2. |
| 6 | One Job, One Worker | A job is not a note. One worker takes it, and it leaves the wall when the worker finishes. | JOB line, Chore, commands wall | `streams.json` BLOODBANK_COMMANDS `workqueue`, 1 d; consumers `bloodbank-hermes-gateway`, `candybar-executor-invoke`. Say "gone when done", not "gone when taken". |
| 7 | The Helper at the Door | Why a sidecar: the app stays plain HTTP while a helper speaks the bus, keeps its place and retries. Listen side only. Two apps. No publisher uses it. Resolves wink 7. | Sidecar, ASK with hourglass to the app | `pubsub.yaml`, `enricher-pubsub.yaml`, `main.py` `/dapr/subscribe`. The READMEs say "Dapr over NATS"; the code says otherwise (platform-map stale trap 2). |
| Y | Your Town | Blank sheet. | | |

## Book 2: The Neighborhood (the level meter in depth)

Goal: place any 33GOD part on the meter and tell nesting (is part of) from using (a line).

1. 33GOD from the table (levels 1 and 2)
2. Next door, not inside (Phonograph and the LLM gateways; "uses" is a line)
3. Voice zoom (33GOD > Voice > HeyMa > waxd; Vinyl and Voxxy siblings; Jarad's example corrected)
4. Bus zoom (Bloodbank is the rulebook and the repo, NATS is the server of walls, a stream is one wall)
5. Your Town

## Book 3: The Factory Floor (events become work)

Goal: follow a ticket and a chore from trigger to result across the bus. Introduces the rotate arrow into plan view and the two-way brick (listens, then speaks). Untested until written, and may force a grammar change.

1. A ticket becomes a job (Plane webhook, n8n lane, note, job, desk, started and completed notes). Draw px as the ticket CLI and n8n as its own ask to Plane. **Never print "px is the only Plane writer".**
2. One clock (Candybar: a tick is a note, the dispatcher turns it into a job, the executor does it and emits invoked and completed. One clock only. The n8n chip sweep is a Candybar-invoked webhook, not a second clock.)
3. A desk (soul, memory, skills, door; honest status lights on Damian's six)
4. Hiring a desk (Flume, role template, Skillex)
5. The brain is next door (the "+" brick: AutomaticAI gateway and Jev are a different product)
6. Memory whispers back (hook-hub asks Hindsight before the prompt: ask. Retain after the turn: async.)
7. Your Town

## Book 4: The Voice (the Voice family and the example Jarad gave)

Goal: place HeyMa, wax, Vinyl, Voxxy and Phonograph on the meter and say why Vinyl is a sibling and Phonograph a neighbour.

1. Say it (three doors in: hotkey, phone via Syncthing, a phone call)
2. Saved before anything (archive to S3 first, then transcribe)
3. Inside HeyMa (waxd and the wax CLI)
4. Eight little jobs (x8; the model door is a "+" brick)
5. Ping (a transcription-completed note reaches an n8n lane and a phone buzz)
6. Three siblings, one neighbour (HeyMa, Vinyl, Voxxy; Phonograph next door). Gate: do not print the client's name beyond Damian without Jarad.
7. Your Town

## Book 5: Eyes and Paper (seeing it and reading about it)

1. See-through (Holocene reads the bus, window brick)
2. Ping (ntfy)
3. The daily paper (one daily report and its verify gate)
4. Is it alive? (check-it ribbons for bus, memory, clock, board, desks)
5. Your Town

## Book 6: Your Box (Build book, the only place install state lives)

Goal: numbered build steps for the Mac peer, with "+" bricks for Jarad's pieces. **Gated:** do not publish until W8-2 is done and `damian-setup.sh` is corrected (its step A looks in the wrong places for the Mac, step B needs a `RESEND_API_KEY` that is not in the store, and `big-chungus` does not resolve from the Mac until the Tailscale share lands).

1. Bag map (the W0-W10 route and which bags are open on this box, read from evidence files)
2. Bag 1: the floor (Colima plate)
3. Bag 2: the bus and hook-hub
4. Bag 3: Candystore
5. Bag 4: the board (Plane and px)
6. Three things only you can do (Tailscale share, setup script, HeyMa)
7. After a reboot (hazard: Colima starts only at GUI login; OpenSign needs Docker Desktop)

## Book 7: Careful (wrong pictures and live hazards)

Goal: cure the wrong mental models people actually hold. Every page is a crossed-out picture beside the true one, and doubles as a tell-back test. Re-date every hazard, 30-day expiry.

1. Nobody plugs into anybody (notes versus asks)
2. The bus is not the vault (7 days on the wall; Candystore keeps its own copy. Say "keeps", never "forever")
3. Dapr is a helper, not the bus (listen side only; the READMEs are wrong)
4. One clock (Candybar owns *when*)
5. Your Mac wakes after login (Colima, OpenSign, Hindsight stale pid)
6. Docs lie, boxes do not (how to run a check-it and trust the box over the page). **Stale-claim trap:** do not cite the old "hung hook-hub delays an agent 15 s" hazard. `W2-4.md` bounded it to about 1 s on the Mac.

## Book 8: Add a Piece (for wannabe engineers, later)

Goal: write a 10-line listener and watch it receive a note.

1. Pin a new listener on the wall
2. Read one note (the envelope)
3. Add your own announcement
4. Check it

## Order of work

Book 1 first, page by page, each gated on Damian's tell-back. Book 2 and Book 6 are next-most-likely because Damian's own box and his nesting question come first. Re-order from feedback, not from this file.
