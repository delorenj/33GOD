# Warehouse Tour Mode: the screenplay

Status: **draft 1 for Jarad**, 2026-11-12. Initiative I-10, The Manual. A guided rail ride through Warehouse One, the counterpart to the open sandbox.

- **[J]** = Jarad's own words (his 2026-11-12 direction for tour mode). **[P]** = a proposal from this script. Everything not tagged [J] is [P]. Strike, rename or redraw any of it.
- **Canon:** [`../world/warehouse-bible.md`](../world/warehouse-bible.md) (objects, verbs, belt physics B1-B18). **Voice:** [`../world/tone.md`](../world/tone.md). **Bulbs:** [`../lightbulbs/README.md`](../lightbulbs/README.md).
- **Route truth:** the verified route research of 2026-11-12 (code plus the live big-chungus NATS server, and one live voice memo traced end to end on 2026-11-12, 01:25:28 to 01:26:51Z). **Code wins over the sketch.** Every place the script departs from Jarad's sketch is listed in the divergence ledger at the end, and each one is turned into an in-story correction, never followed silently.
- **Engine data:** the same tour as typed beats lives in [`../sandbox/src/tour/script.ts`](../sandbox/src/tour/script.ts). This file is the source; the `.ts` is the cut for the rail engine.

---

## Logline

On his first day in Warehouse One, Damian is handed an errand by a floor manager with no time: take this to the guys in Voxxy and bring back what they say. He gets it wrong in exactly the way everyone does, and the building's oddballs walk him through the right way, room by room, until the answer plays out of a speaker in the manager's hand.

## The shape in three legs [P]

1. **Leg A, the dock lesson (Scenes 2-7).** Damian does the reasonable wrong thing: he types the manager's request into Codex at his desk and presses Enter. The rail follows that moment as a parcel to the dock, where it becomes one post-it on the front belt. The leg ends on the turn: *that post-it is a note about a question, and nobody has been asked to do anything.* Damian's wrong idea is Jarad's sketch, so the correction lands as story, not as an erratum.
2. **Leg B, the memo run (Scenes 8-16).** The manager's errand was on the Agent Pad in Damian's vest the whole time. It enters through a different door, the memo door, and this is the route that is real today: memo desk, the first envelope, the express hatch, a workstation, the staffing desk, the voice booth (twice), and back to the manager's speaker. One barcode spans all of it.
3. **Side scenes (Scene 13, plus asides).** Rooms that are not on this request's route get a short, labelled visit while the workstation thinks: the clock and the sound wing. The return-slip window appears once, dashed, as an aside.

**The bridge between A and B is story, not data.** The Leg A parcel never becomes the Leg B envelope. They are two systems with two barcodes, and the last scene says so out loud.

**Why Warehouse One.** Damian's own building (Warehouse Two) has no crew hall, no memo desk, no voice booth, no cataloguer and no clock (bible 4.4). The tour is set in Jarad's building, with Damian as the visiting new hire. The manager says so in Scene 1.

## Production notes [P]

- **Comedy carries the concept.** Tone rule 9 caps a page at one wry line. Jarad's direction for this mode asks for "absolutely ridiculous characters" and "clever dialogue", so the tour relaxes that cap to *character-driven* comedy, and keeps everything else: no exclamation marks, no baby talk, no "Let's", no cartoon sound words, no condescension words. Every joke must be the model point said sideways. If you can delete a joke and lose nothing the reader needs, delete it.
- **Faces go on people.** Parcels, post-its, envelopes and tapes never have faces, never talk, never wave.
- **Locked verbs.** Stick, tear off a copy, sign off, stamp "still working", hand back, tear up, scrape, file, wait at the window. Nobody "delivers" a post-it. Post-it headlines are past tense; the one envelope says "invoke".
- **Real terms.** Once each, as "You'll hear this called X". JetStream, CloudEvents and "workqueue retention" stay off every face and out of every line.
- **Numbers.** Only stable ones are spoken. Live counts and timings that drift (hatch patience, hand limits) stay in the shot notes and evidence column, never in a line.
- **(verify)** marks a claim the route research rated *inferred* or *unverified*. Close it before the line ships.
- **Engine set ids.** Each scene names the engine set in `[brackets]`. The memo desk has no set id of its own yet, so it is staged at `[control]`: it is Holocene's, and it sits on the ground floor under the control room's mezzanine. Proposal for the engineer: give it its own set (`memodesk`) when the art pass reaches it, and keep the control room upstairs for watching only.

---

## The cast [P]

Twenty people, one building. Nobody is a mascot for a product; each is a job, and the job is the component. Damian is drawn with affection and nothing from his life beyond his first name.

| # | Name (engine id) | Job in the warehouse | Real component | Look brief for the 3D artist | Voice and comic engine |
|---|---|---|---|---|---|
| 1 | **Damian** (`damian`) | New hire, visitor's lanyard | The reader | Small and round, head a size too big, hi-vis vest that reaches his knees, a clipboard he holds like a shield, lanyard swinging. Bright orange vest, butter trim. | Earnest, quick, says the sensible wrong thing out loud so the reader does not have to. Never stupid, only new. |
| 2 | **Mr. Abernathy** (`manager`) | Floor manager | The person who wants something done (a human requester) | Tall, barrel-chested, short-sleeved shirt and a tie clip, headset, a stopwatch on a lanyard, always mid-stride. Charcoal and safety red. | Grave as a general, urgent as a sneeze. Gives orders in fragments while already walking away. Takes everything seriously except himself. |
| 3 | **Dash** (`dash`) | The courier, one uniform at every bay | `bb-hook` | Wiry, on roller skates, padded knee guards, a courier bag cut to fit exactly one box. Teal uniform, one bright stripe. | Unbothered pragmatist. "Door shut, I turn round." Treats drama as a waste of milliseconds. |
| 4 | **Odette** (`odette`) | Lessons librarian, on the phone to the dock | Hindsight, reached by the `hindsight-recall` job card | Elderly, cardigan, half-moon glasses on a chain, a headset over a bun, an hourglass on the desk. Plum and cream. | Answers every call with "Last time on this project..." and means it. Racing an hourglass with perfect calm. |
| 5 | **Fenwick** (`fenwick`) | Receiving clerk at the dock bench | `hook-hub` (dispatch, job cards, and the clerk at the back, `bloodbank-publisher`) | Long arms, sleeve garters, a letter opener behind each ear, a phrasebook in every pocket. Brick red, brass buttons. | Polyglot of vendor dialects. Translates with the pride of a sommelier and the patience of a saint. |
| 6 | **Inspector Cruz** (`cruz`) | Label desk inspector | Naming contract, schemas, `assert_contract` | Compact, immaculate, reading glasses pushed up, a chained dictionary the size of a paving slab, one rubber stamp in a holster. Forest green. | Deadpan bureaucrat who is in love with the rules and a little moved by a correct label. |
| 7 | **Kofi** (`kofi`) | The dock's poster | The agent-hooks publisher (core publish, then a ping) | Very tall and lanky, long fingers, a pad of house forms on a lanyard, walks with ceremonial care. Coral and white. | Reverent about sticking notes. Rings the doorbell, hears "come in", and leaves deeply satisfied. Learns on camera that "come in" is not "got it". |
| 8 | **Professor Haugen** (`haugen`) | Belt geologist | NATS JetStream, the two loops | Weathered field geologist, rock hammer, a measuring stick taller than she is, boots, a hard hat with a lamp. The only person allowed to wear belt blue. | Reads the belt like rock strata. Height is age, and she cannot be talked out of it. |
| 9 | **Monsieur Lefèvre** (`lefevre`) | The cataloguer, at his clip | Enricher | Tall, thin, cravat, a label gun in a holster, white gloves. Aubergine. | Fussy connoisseur who will not lower himself to read a note that is not on his list. |
| 10 | **Reggie** (`reggie`) | Doorman at the memo door | The Agent Pad and its upload proxy (Holocene Auto) | Broad, kind, peaked cap, a bell on a cord at his chest, a key ring the size of a dinner plate. Burgundy with gold piping. | Old-school doorman who remembers every address. Takes the tape, rings the desk, and never forgets to ring the bell when something comes back. |
| 11 | **Priya** (`priya`) | The memo desk | Holocene `inbox-watcher` | Small, fast, six rubber stamps in a belt, two pencils in her hair, a headset, a desk with a little window on each side. Saffron orange (darker than the post-its) and slate. | Frighteningly organised. Narrates her own checklist. Reads other people's ledgers because she does not trust a doorbell. |
| 12 | **Wren** (`wren`) | The Whisper booth | Warm GPU faster-whisper | Slight, enormous padded earmuffs, a typewriter that types silently, a padded booth. Sage green. | Speaks only in a whisper. Hears everything. Types it all. |
| 13 | **Mr. Okafor** (`okafor`) | Crew hall concierge, at the front desk | `hermes-gateway` and its bus plugin | Grand, tailcoat, white gloves, a ledger under one arm, a brass in-hand tray, a small "still working" stamp on a chain. Deep green and gold. | Five-star hotel manners applied to envelopes. Never takes credit for a job, only for the paperwork. |
| 14 | **Holly** (`holly`) | A workstation worker, badge "holocene-pm" | A Hermes profile | Overalls, a badge on a lanyard, a locker behind her, placards pinned up, a radio clipped to her strap. Frozen mid-pose until an envelope wakes her. Rust and cream. | Brilliant, brisk, and completely asleep until something arrives for her. |
| 15 | **Mags** (`mags`) | The staffing desk next door | The AutomaticAI gateway | Three desk phones, one in each hand and one on her shoulder, a rolodex, reading glasses on her head. Teal-green and mustard. | Phone juggler. "First agency that picks up." Knows which numbers ring out. |
| 16 | **Vinnie** (`vinnie`) | The voice booth's front window | Voxxy's `vox` core | Slick retro radio announcer, pencil moustache, a vintage ribbon mic, sleeves rolled. Indigo and red booth light. | Silky, theatrical, allergic to paperwork. "We don't take deliveries. Slide it under the door." |
| 17 | **Big Mo** (`mo`) | The voice in the booth's back room | Voxxy's `voxcpm` engine | Huge and gentle, cardigan, reading one script at a time on a music stand. Deep violet. | A warm baritone who will not read two scripts at once, however politely asked. |
| 18 | **Constance Bell** (`constance`) | The bellkeeper | Candybar, the clock | Railway conductor's uniform, pocket watch on a chain, a clipboard chore chart. Navy-black with brass. | Precise to the second, scandalised by private alarms. |
| 19 | **Gloria Waxman** (`gloria`) | Superintendent of the sound wing | HeyMa, waxd and intake | Silver curls, an ear trumpet, a cardigan with eight pockets, a key to a secure cage. Dusty rose. | Grand old dame of audio. Proud, a little sore that nobody collects her envelopes. |
| 20 | **Mr. Fitch** (`fitch`) | The archive's filing clerk | Candystore | Narrow, sleeve protectors, pencil behind the ear, a rolling ladder against the racks. Walnut brown. | Unflappable. Shrugs at duplicates. Can tell you a whole story from one barcode. |

**Colour rule** [P]: blue is the belt's, so only Professor Haugen wears it. Nobody's main colour is post-it yellow or envelope kraft, so the data objects always read first.

---

## The route map [P]

| Scene | Title | Engine set(s) | The object at this step | Real hop |
|---|---|---|---|---|
| 1 | The Briefing | `entrance` | a tape on the Agent Pad (unsent, in Damian's vest) | none yet |
| 2 | Enter | `bays` | **parcel** (Codex's own dialect) | Codex `UserPromptSubmit` hook |
| 3 | The Courier | `courier` | parcel | `bb-hook` over the hub's socket, fail-open |
| 4 | The Driver's Window | `library` (parcel waits at `dock`) | parcel waits; a **briefing card** goes back | hook-hub sync job cards, `hindsight-recall` |
| 5 | Receiving | `dock`, `labeldesk` | **post-it**, "turn started" | `bloodbank-publisher`, Codex adapter, `assert_contract` |
| 6 | The Belt | `belt`, `cataloguer` | post-it on the front belt; copies torn off | doorbell publish, `BLOODBANK_EVENTS`, readers |
| 7 | Nobody Asked Anybody | `belt` (the edge) | post-it, unaddressed | the turn: no command is written at the dock |
| 8 | The Memo Door | `entrance` | **recording** (a tape), then post-it "memo uploaded" | Agent Pad PUT, upload proxy, the shelf, wake call |
| 9 | The Memo Desk | `control` ×2 | post-its "memo received", "memo transcribed", then the **envelope**, "invoke" | inbox-watcher, Whisper, `bb-emit --kind command` |
| 10 | The Express Hatch | `crew` | envelope on the back belt, then "in hand" | `BLOODBANK_COMMANDS`, interactive hatch |
| 11 | The Workstation Phones Out | `staffing` | envelope in hand; "invocation progressed" post-its | Hermes turn, gateway route, Hindsight (verify) |
| 12 | The Voice Booth, Part One | `voxxy` | a short script under the door; post-it "memo narrated" | `POST /synthesize-url`, plain HTTP |
| 13 | While You Wait (side scenes) | `clock`, `soundwing` | none on route | Candybar; HeyMa |
| 14 | Signed Off | `crew` | envelope signed off; post-its "invocation completed", "turn completed" | ack after the turn |
| 15 | Take Their Result | `control`, `voxxy` | a ledger line, a session-book page, then the **recording** of the reply | gateway SQLite ledger, `state.db`, Voxxy in chunks |
| 16 | Bring It Back | `entrance`, `archive` | post-its "memo voiced", "memo replied"; the barcode read back | reply shelf, speaker line, car-or-phone, Candystore |

**Every Bloodbank part is visited:** the courier (3), the dock (4-5), the label desk (5), the posters (6, 9, 10), the belt's front (6-7) and back (10), clips, a visitor's pass and runners (6), the archive (16). **Off-route rooms get labelled side scenes:** the clock and the sound wing (13), the rules cabinet (13, one line), the return-slip window (14, one line).

---

## The scenes

Format for every scene: **set** (engine id), **shot**, **the beat** (what the reader must understand, at most two model points), **dialogue**, **lightbulb**, **where the picture breaks**, **evidence**. Stage directions are in *italics*. All dialogue is [P] unless tagged [J].

### SCENE 1. The Briefing

- **Set:** `[entrance]`. The entrance arch, WAREHOUSE ONE painted on the lintel, a visitor's-pass desk, the rail platform with one small open car.
- **Shot:** Wide and low. Abernathy enters frame left mid-stride and never fully stops; the camera has to pan to keep him. Damian stands under his lanyard. On "it's packaged up" Abernathy drops a small Agent Pad into Damian's vest pocket without looking. Damian does not notice. The camera does (a two-frame push-in on the pocket, its red record light glowing: *unsent*).
- **The beat:** The errand: a question goes in, an answer comes back. This is Warehouse One, Jarad's building, not Damian's. Plant the pad.

**ABERNATHY** [J]: Look, I know you're new here. But what better way to learn your way around. The campus. Or something.

**ABERNATHY** [J]: I need you to deliver this message to the guys down in Voxxy. Now, it's packaged up. So you're gonna have to take it through processing yourself.

**ABERNATHY** [J]: When the guys are done, take their result and bring it back here. I'll be waiting for you.

**DAMIAN:** Processing. Right. Where's the message?

**ABERNATHY:** On you. This is Warehouse One, twice the rooms of yours, so stay on the rail. *(already leaving)* I'll be here. Waiting. Seriously.

**DAMIAN:** *(patting his clipboard, not his vest)* On me. So it's whatever I write down.

- **Lightbulb:** none.
- **Where the picture breaks:** none needed yet. The pad is a real device (car, phone or browser); the "tape" it holds is a recorded voice memo.
- **Evidence:** bible 4.4 (Damian's building has no crew hall, memo desk or voice booth); route research, framing note.

### SCENE 2. Enter

- **Set:** `[bays]`. Damian's own typing desk at the Codex bay: a keyboard, a screen, and a small hatch in the desk's side with a roller under it.
- **Shot:** Macro on the Enter key going down. Cut to the hatch: one brown box slides out with a stripe and a handwritten label, `UserPromptSubmit`. No logo. Dash skates into frame and catches it one-handed.
- **The beat:** Pressing Enter fires a hook, and the vendor packs one parcel in its own dialect. The vendor talks to its own model by its own road; the warehouse is beside the road, never on it.

**DAMIAN:** *(typing)* Dear Voxxy. The manager wants an answer, please. Love, Damian. *(Enter)*

**DASH:** Box for the dock.

**DAMIAN:** It's for Voxxy.

**DASH:** It's for the dock. That label is Codex saying "he asked something", in Codex's own handwriting. Every vendor writes its own.

**DAMIAN:** And the answer?

**DASH:** Codex already went to its own model, by its own road. We're not on that road. I carry the news that you asked.

- **Lightbulb:** none here. (Catalog bulb 2, *What is a hook?*, belongs at this bay when it is drafted.)
- **Where the picture breaks:** vendors are programs on your own desk, not companies with vans. The parcel is a copy of the moment, not your question's trip to the model.
- **Evidence:** `bloodbank/services/agent-hooks/clients/codex.py:56-57`; `hooks.master.json:28-32` (`UserPromptSubmit` → role `prompt_submit`); bible section 1.

### SCENE 3. The Courier

- **Set:** `[courier]`. Horizontal rollers from the bays to a roller door marked RECEIVING, drawn flat and fast, visibly unlike the tall vertical belt.
- **Shot:** Tracking shot beside Dash. On Damian's question, a desaturated "what if" insert: the door is shut, Dash pivots on one skate and rolls back with the box still under her arm. The curb in front of the door stays empty. Back to colour.
- **The beat:** If the dock is shut, the courier turns round, nothing queues, and the vendor never waits. No post-it is ever written for that moment.

**DAMIAN:** What if the dock's closed?

**DASH:** Then I turn round with the box. I don't knock twice, I don't leave it on the step, and I don't bother Codex about it.

**DAMIAN:** So the news...

**DASH:** Never gets written down. No queue, no second try. You'll hear this called fail-open: the helper is down, the real work carries on without it.

**DAMIAN:** That's a little bleak.

**DASH:** It's a little fast. The whole trip takes a few thousandths of a second. The skates are for morale.

- **Lightbulb:** **failopen** (*What is Fail-open?*), bobbing beside the shut door in the insert.
- **Where the picture breaks:** the "conveyor" is a local socket between one small program and another. Nothing waits at a curb: a shut door means the moment never becomes a post-it at all.
- **Evidence:** `bloodbank/services/hook-hub/client/bb-hook:1-30,197-211,334-371,543-546` (every failure prints nothing and exits 0, no spool).

### SCENE 4. The Driver's Window

- **Set:** `[library]`, while the parcel waits at `[dock]`. The engine's hero marker hangs over the dock's driver's window; the camera visits the lessons library.
- **Shot:** Open on Dash idling at a small window cut into the dock wall, box under her arm, a laminated job card with a stopwatch clipped above the frame. A phone rings. Whip to the library: Odette lifts the receiver and flips an hourglass with her other hand. Back to the window: a printed card slides out into Dash's palm.
- **The beat:** Some parcels wait at the window for an answer, a briefing card, which goes back to the vendor inside a time limit and never goes on the belt. The lessons library is reached by phone, not by the belt.

**FENWICK:** *(through the window)* Codex question. Window cards run in order: reminders, the library, the code map. You wait, Dash.

**DASH:** I always wait at the window. It's the only place anyone hands me anything back.

**ODETTE:** *(on the phone, hourglass running)* Last time on this project, you learned the voice booth reads one script at a time. Card's printing.

**FENWICK:** *(slides the card out)* Briefing card. It goes back to Codex before Codex carries on. It never goes on the belt.

**DAMIAN:** And if the library's slow?

**ODETTE:** Then the card leaves without my paragraph, dear. The hourglass doesn't wait for me, and neither does Codex.

- **Lightbulb:** none in the sandbox set. (Catalog bulb 3, *Asking vs announcing*, belongs at this window when drafted: at the window you wait for an answer; a post-it announces and nobody waits.)
- **Where the picture breaks:** the job cards are functions inside one program, not clerks; the library is a phone call over the internet, and the window's whole budget is a few seconds. Odette's line is a planted callback: Scene 15 pays it off.
- **Evidence:** `hook-hub/hub.py:65-66,670-722,729-741` (sync budget 2.5 s default, 14 s max); `handlers.toml:11-50,65-77,168-176` (`skill-reminder` 1 s, `hindsight-recall` 11 s, `codegraph-prompt` 2 s).

### SCENE 5. Receiving

Two camera stops.

**5a.** `[dock]`. The long bench under the RECEIVING sign. Fenwick at the front; at the back, a second station where the post-it is written.

- **Shot:** Fenwick slits the Codex box with the letter opener from behind his ear, reads the label aloud like a wine list, and writes one yellow post-it. Close on the post-it: headline "turn started", a speech-bubble icon, a small "from: Codex" corner, a barcode along the bottom, a "came after" line. He staples the original packing slip to its back. Dash is already gone.
- **The beat:** Parcels in, one house post-it out, written one way whatever the vendor said. The barcode is one per conversation.

**FENWICK:** Codex writes "UserPromptSubmit". Gemini writes "BeforeAgent". opencode writes "chat.message". They all mean one thing, and the house writes it one way.

**FENWICK:** *(holds up the post-it)* "Turn started." Codex goes in the small corner, never the headline. Its own packing slip, stapled to the back.

**DAMIAN:** What's the stripe along the bottom?

**FENWICK:** The barcode. One per conversation, made from Codex's own session number. Every note from this chat wears it. "Came after" names the note before it.

**DASH:** *(off, skating away)* I don't wait for any of that. The back room writes it after I've gone.

- **Lightbulb:** **normalization** (*What is Normalization?*, the drafted modal), bobbing beside the bench.

**5b.** `[labeldesk]`. Inspector Cruz's desk beside the dock: the chained house dictionary, the form pads, one stamp.

- **Shot:** Cruz holds the post-it at arm's length, stamp hovering. A beat of pure silence. Then the stamp comes down.
- **The beat:** The label desk checks house words, and the vendor's name never goes in the headline. The question itself rides on the post-it, so anyone who tears off a copy can read it.

**CRUZ:** Headline?

**FENWICK:** "Codex turn started."

**CRUZ:** Refused. Vendors live in the corner. The headline uses house words only, and every word is in the book. *(taps the chained dictionary)*

**DAMIAN:** What's written inside? My question?

**CRUZ:** Word for word. Anyone who tears off a copy can read what you asked.

**DAMIAN:** I wrote "Love, Damian."

**CRUZ:** Then the whole building knows. *(stamp)*

- **Lightbulb:** none here. (Catalog bulb 15, *What is a schema?*, belongs at this desk.)
- **Where the picture breaks:** the dock is one program with about 35 job cards, not a crew, and the post-it is written by a separate back-room clerk the courier never waits for. The label is house format; the body still carries Codex's raw payload on the back. Copies of the inspector sit at several benches, some writers skip the desk, and the belt never checks anything.
- **Evidence:** `hook-hub/hub.py:595-626,656-668,712-715` (`bloodbank-publisher`, async, serialised per session); `agent-hooks/clients/codex.py:149-157` (`turn.started`, `prompt_text`, raw payload kept); `clients/base.py:267-285` (correlation from session id, causation = previous note); `core/validate.py:1026` (`assert_contract`).

### SCENE 6. The Belt

Two camera stops.

**6a.** `[belt]`. The loading point at the foot of the glass shaft; a doorbell with a brass slot; the sorter; the day ruler up the side.

- **Shot:** Kofi carries the post-it in both hands like a ring on a cushion, rings the doorbell, hears a muffled "come in", posts it through the slot and turns away glowing. Inside: a stamp prints a belt number, the sorter reads one word on the label ("evt") and the note starts up the front loop. Tilt up the day ruler: *Today*, *1 day*, *7 days*. Professor Haugen's measuring stick enters frame.
- **The beat:** The dock's poster uses a doorbell: "come in" means heard, not kept. On the belt, height is age, and the scraper takes notes at seven days, read or not.

**KOFI:** *(rings, beams)* "Come in," it says. So it's on.

**HAUGEN:** It says it heard you. That isn't the same as kept, Kofi. Your doorbell never waits for a receipt.

**KOFI:** And if the door's shut?

**HAUGEN:** Then your note hits the floor and nobody tries again. *(to Damian)* Now watch it climb. Height is age. At the seven-day mark, the scraper takes it, read or not.

**DAMIAN:** So the belt carries it to Voxxy.

**HAUGEN:** The belt carries it nowhere. It's a noticeboard that scrolls up at the speed of the clock. Readers come to it.

- **Lightbulb:** **retention** (*What is Retention?*), at the scraper.

**6b.** `[cataloguer]`. Beside the front belt, where the readers stand: the archive's runner, the control room's visitor's window above, Lefèvre's aubergine clip on the belt.

- **Shot:** Three quick cuts as the post-it passes: the archive's runner tears off the top sheet and sprints for the racks; up on the mezzanine a hand with a visitor's pass copies a number into a notebook; the artifact clerk's clip lets it slide past. Then Lefèvre's clip lets it slide past too, and he turns his nose up.
- **The beat:** Readers tear off copies and the original stays. A reader's pick list lets other notes slide past.

**HAUGEN:** Readers. The archive's runner tears off a copy for the racks. The control room reads through its visitor's window, pass in one hand, notebook in the other.

**DAMIAN:** They took it off the belt?

**HAUGEN:** They took a copy. The original stays for the next reader. You'll hear this called fan-out.

**LEFEVRE:** *(his clip lets the note slide past)* "Turn started"? Non. I tag finished tool calls. A question is not a finished anything.

**DAMIAN:** So who's reading it for Voxxy?

**LEFEVRE:** Look at the clips, monsieur. Do you see one for Voxxy?

- **Lightbulb:** **fanout** (*What is Fan-out?*).
- **Where the picture breaks:** real streams do not move; the climb stands for age. The doorbell's "come in" is the server hearing the note, not storing it, and the dock's notes carry no duplicate-guard number. A clip is a bookmark the server keeps, not a binder clip, and the control room keeps its own place in its own notebook, so "the belt remembers everyone" is false.
- **Evidence:** `agent-hooks/core/nats_publish.py:131-174`, `core/publisher.py:276` (plain publish then ping, no message id, no retry); `bloodbank/compose/nats/streams.json:35-42` (front loop, 7 days); live `:8222/jsz` 2026-11-12 (about two dozen readers on the front loop, including `candystore-events`, `enricher-events` and Holocene's).

### SCENE 7. Nobody Asked Anybody

- **Set:** `[belt]`, the edge of the shaft where the yellow front meets the kraft back through the glass.
- **Shot:** Damian walks round the shaft with his nose to the glass, past his own yellow note climbing the front, until he can see the back loop: envelopes, kraft, windowed, none of them his. Haugen waits for him to arrive at the thought. Then she taps his vest. The red record light is blinking.
- **The beat:** A post-it announces; an envelope asks one worker to do one thing. Nothing at the dock writes envelopes, and Voxxy is not on the belt at all. (The turn of the act: Leg A ends here.)

**HAUGEN:** That's a note about a question. It says "he asked". It doesn't ask anyone to do anything.

**DAMIAN:** Then how does anything get done?

**HAUGEN:** Somebody writes an envelope: one instruction, for one worker, round the back. Nobody at the dock writes envelopes.

**DAMIAN:** And Voxxy?

**HAUGEN:** Not on the belt at all. No clip, no hatch. They have a door you slide things under. *(taps his vest)* What's that?

**DAMIAN:** *(pulls out the Agent Pad: "1 memo, unsent")* The manager's message. It was on me the whole time.

- **Lightbulb:** **eventcommand** (*Event or command?*), where the two faces meet.
- **Where the picture breaks:** in the real format every note, post-it or not, travels in the same standard wrapper; the warehouse keeps the word "envelope" for commands only, so one object keeps one meaning. And Damian's typed question stops here for good: it never becomes the errand. Leg B is a different system with its own barcode.
- **Evidence:** grep of `hook-hub` and `agent-hooks` (no command written anywhere); `~/code/voxxy/README.md:628-629` (wrapping Voxxy in Bloodbank is listed as future work).

### SCENE 8. The Memo Door

- **Set:** `[entrance]`, round the side of the arch: a brass slot marked MEMOS, Reggie in his cap, and behind him the **upload shelf**, four labelled bins: *inbox*, *status*, *progress*, *replies*.
- **Shot:** Damian sprints back along the rail. Abernathy's spot is empty; his headset hangs on a hook, still on. Reggie takes one look at the pad and points at the slot. Damian presses send. The tape drops into the *inbox* bin under a tab reading "holocene-pm / today". Reggie prints a barcode from the bin's address, rings a small bell on a cord towards the memo desk, and sticks one post-it at the doorbell.
- **The beat:** The errand comes in through a different door, the memo door, not the dock. The tape's shelf address becomes the barcode that every note from this errand will wear. And the memo is for a worker; Voxxy gives the answer a voice, it does not write it.

**REGGIE:** Memo door. Pads only. That's a tape, son, not a parcel. Parcels go to the dock.

**DAMIAN:** It's for Voxxy.

**REGGIE:** *(reads the pad)* It's for holocene-pm. That's a worker. Voxxy doesn't answer questions. Voxxy reads answers out loud.

**DAMIAN:** *(presses send)*

**REGGIE:** On the shelf: inbox, holocene-pm, today. That shelf address is your barcode now. Every note from this errand wears it.

**REGGIE:** *(rings the bell, sticks a note)* "Memo uploaded." And a ring for the memo desk, so it doesn't wait for its next look round. Miss the ring and it finds the tape a few seconds later anyway.

- **Lightbulb:** none.
- **Where the picture breaks:** the memo door is a web upload from the pad to the upload proxy, nothing to do with the dock; the tape is not a canon parcel, because parcels are raw hooks only. The real pad uploads when the recording stops; the "unsent memo" in Damian's vest is a story device. The shelf is object storage. Reggie's post-it also goes through a doorbell: heard, not kept.
- **Evidence:** `holocene/services/inbox-watcher/README.md:7-19`; `holocene/services/upload-proxy/upload_proxy.py:635-648,1041-1046,1100-1116` (PUT `/upload/inbox/<agent>/...`, bucket `holocene-auto`, `audio.memo.uploaded`, memo id = uuid5 of the shelf address); `inbox_watcher.py:4800-4829` (`/wake`, 5 s fallback listing).

### SCENE 9. The Memo Desk

Two camera stops, both `[control]`: the ground floor under the control room's mezzanine, which is Holocene's. (The control room upstairs only watches. The memo desk downstairs writes.)

**9a.** Receive and transcribe.

- **Shot:** Priya's desk has three little windows: one onto Wren's padded booth (open), one onto the crew hall's ledger (shutter down), one onto a shelf of session books (shutter down). The bell rings; Priya is already moving. Stamp, check a routing board ("holocene-pm: routable"), pull the tape, glance at a level meter, slide the tape through the open window. Wren types on a silent typewriter and whispers. Stamp again.
- **The beat:** The memo desk turns the tape into text, and records each thing it has done as a post-it. Some memos it answers itself; this one is for a worker.

**PRIYA:** Ring heard. "Memo received", stuck. Worker holocene-pm, routable. Level's fine. Wren?

**WREN:** *(whispering)* He said: "Holly. Why does the car take so long to talk back. Thirty words. Go."

**PRIYA:** "Memo transcribed", stuck: the words, how long it ran, which ears heard it.

**DAMIAN:** Couldn't you answer it yourself?

**PRIYA:** Some memos I can, at the quick desk, with no envelope at all. This one is addressed to a worker. So it gets an envelope.

**9b.** The envelope.

- **Shot:** Priya pulls a kraft envelope from a drawer. Inserts, close: the window label reads "agent invocation **invoke**"; inside, "holocene-pm"; a barcode sticker copied from the memo; a signature box on the flap; a safe-to-repeat code under the flap. She runs it under a small copy of Inspector Cruz's stamp, posts it through a doorbell slot marked BACK, sticks one more post-it, and raises the shutter on the ledger window.
- **The beat:** The memo desk, not the dock, writes the tour's first envelope: an imperative, for one worker, carrying the copied barcode and a safe-to-repeat code. It goes out by doorbell, so the desk checks the crew hall's ledger to learn it landed.

**PRIYA:** An envelope. One instruction, for one worker. Outside, "invoke". Inside: holocene-pm, his words, the thread, and which agency to phone.

**DAMIAN:** That's the first envelope I've seen anyone write.

**PRIYA:** I copy the barcode on. A barcode only crosses rooms when the next writer copies it. And a safe-to-repeat code under the flap, because envelopes can come round twice.

**PRIYA:** *(stamp, doorbell)* Checked, rung, gone. "Memo dispatched." And I don't trust doorbells, so I'll read the crew hall's ledger to see it landed.

- **Lightbulb:** none here. (The idempotent bulb waits for the archive in Scene 16.)
- **Where the picture breaks:** the memo desk is one service doing half a dozen jobs, and Wren is a speech-to-text model on a graphics card, reached over the web, not over the belt. "Invoke" is the express kind of envelope, for a human who is waiting; the ordinary kind says "start". The ledger window is a file on the same machine, not anything on the belt. Canon update owed: the bible lists only the dock's poster as a doorbell (B16); the memo desk and the memo door ring doorbells too.
- **Evidence:** `inbox_watcher.py:1502-1525,1672-1682,1926` (received, Whisper at `:8766`, transcribed; the fast desk `MEMO_CONVERSE`); `inbox_watcher.py:62,181,2356-2363,2398-2426,2448-2456` and `bloodbank/bin/bb-emit:60,137-143,326-329` (`--strict --kind command --type bloodbank.agent.invocation.invoke`, correlation = memo id, command id, idempotency key = uuid5 of type and correlation, single consumer, `dispatched`, ledger check); `core/validate.py:161-168,345`.

### SCENE 10. The Express Hatch

- **Set:** `[crew]`. Round the back of the shaft: the back loop climbing, and in the crew hall wall, hatch doors. Two are the crew hall's (ORDINARY; EXPRESS, with a small plate: "a human is waiting"). Further along, two in the clock's brass. Two more tagged NOT OURS.
- **Shot:** The envelope climbs the back loop. The express hatch slides open and a white-gloved hand draws it halfway in. It does not come off the belt: a red ribbon tethers it, with a tag reading IN HAND. Okafor checks it, runs a finger down a registry board ("holocene-pm → workstation 7"), writes one line in his ledger, and walks two post-its to a counter where a clerk hands back a receipt with a belt number on it.
- **The beat:** One hatch per kind of envelope; the express hatch takes it, and taken is not gone: it stays on the belt, in hand, until signed off. The crew hall posts its own notes at the registered counter, with no dock involved.

**OKAFOR:** Welcome to the crew hall. Express hatch, for envelopes a human is waiting on. Each kind of envelope has one hatch at most.

**DAMIAN:** You've taken it, so it's off the belt.

**OKAFOR:** Taken is not gone, sir. It stays on the belt, marked in hand, until I sign it off. If I go quiet, it will be offered again.

**OKAFOR:** One line in my ledger. Then two post-its at the registered counter, "turn started" and "invocation started", and I wait for a receipt with the belt number on it.

**DAMIAN:** "Turn started." That's what the dock wrote for me.

**OKAFOR:** Same words, different poster, different barcode. The dock had nothing to do with this one.

- **Lightbulb:** **workqueue** (*What is a Work queue?*), at the hatch.
- **Where the picture breaks:** the crew hall is one program, and "walking to workstation 7" is a function call. The back loop's scraper sits at one day: an envelope nobody signs off is gone by tomorrow. The hatch's patience, tries and hand limit are real settings, and they stay on its spec plate, not in dialogue (they drift: the live server and the docs disagree today).
- **Evidence:** `bloodbank/compose/nats/streams.json:67-75` (back loop, 1 day); live `:8222/jsz` 2026-11-12 (six hatches: two gateway, two Candybar, two milkshake; interactive hatch `bloodbank-hermes-gateway-interactive`, filter `bloodbank.cmd.agent.invocation.invoke`, ack wait 180 s, max deliver 8, max ack pending 4); `hermes-gateway/.../adapter.py:366,479,565-595,1603-1613`, `contract.py:246-330,429-442,474-497`.

### SCENE 11. The Workstation Phones Out

- **Set:** `[staffing]`. Holly's workstation (badge, locker, placards, radio) on one side of a wall; on the other, the staffing desk next door, Mags with three phones.
- **Shot:** Holly is frozen mid-reach, like a paused film. Okafor sets the envelope's ticket on her desk and she unfreezes in the same motion. She reads, lifts a phone; the cord runs through the wall to Mags. Mags dials, gets nothing, dials the next number, gets an answer. Through the window behind them: out on the back loop, Okafor stamps the tethered envelope STILL WORKING. Each time Holly mutters to herself, a yellow post-it appears at the registered counter. (A second cord, unlabelled, runs from Holly's locker to the library: Odette, hourglass. (verify))
- **The beat:** A workstation sleeps until an envelope wakes it; its model call goes through the staffing desk to agencies across town, trying a list in order. While it works, the crew hall stamps the envelope "still working" and posts the worker's progress, never the final answer.

**HOLLY:** *(unfreezing)* Envelope for me. Badge, locker, placards. Right. I need a model.

**MAGS:** Staffing desk. The envelope names a route, so I ring the first agency on its list. If it rings out, I try the next number.

**DAMIAN:** Is the agency in the building?

**MAGS:** Across town, love. Their answers come back to Holly, never across your belt.

**OKAFOR:** *(stamping)* "Still working." Every so often, so nobody thinks I've gone quiet and offers it to someone else.

**HOLLY:** Thinking out loud. *(a post-it appears)* "Invocation progressed": bits of my working. Never the final answer.

- **Lightbulb:** none in the sandbox set. (Catalog bulb 22, *What is a gateway?*, belongs at Mags's desk.)
- **Where the picture breaks:** "next door" is about ownership, not place: the staffing desk runs on a server elsewhere. A fallback list can look healthy while the members nobody pays for are skipped. The workstation is only files until an envelope wakes it. The progress notes and the library line are inferred from the gateway's docs and schemas, not traced live (verify both before the scene ships).
- **Evidence:** `hermes-gateway/README.md:395-403,498-499,611-620`; `schemas/bloodbank/agent/invocation.progressed.json`; `hook-hub/handlers.toml:93-96` (the Hermes plugin retains per turn); `inbox_watcher.py:181` (model route in the envelope). Confidence: inferred.

### SCENE 12. The Voice Booth, Part One

- **Set:** `[voxxy]`. A padded booth with a red ON AIR light, a front window with Vinnie behind it, and a slot at the foot of the door marked SCRIPTS. In the back room, Big Mo at a music stand.
- **Shot:** Damian arrives empty-handed (the hero marker still hangs over the crew hall: the envelope is in hand there). A short typed slip slides under the door from off-screen, initialled "P., memo desk". Vinnie passes it back without looking. Mo reads it into the mic. Seconds later a small recording slides back out under the door, and an off-screen hand takes it.
- **The beat:** Voxxy is not on the belt. It is a plain API call: a script slid under the door, a recording handed back while the caller waits. This first visit is a progress report, not the answer.

**DAMIAN:** I've come about the manager's message. Are you the guys?

**VINNIE:** We're the guys. We don't take deliveries, kid. No envelopes, no clips, no hatch. You slide it under the door.

*(A slip slides under the door.)*

**VINNIE:** Like that. Priya reads Holly's working off the archive, and every half minute or so she sends me the newest line.

**MO:** *(a warm baritone, reading)* "Holly is checking the memo desk's timings now."

**VINNIE:** Script in, recording out, and she waits at the door for it. It's a plain API call. No belt in it anywhere. She files it and sticks "memo narrated".

**DAMIAN:** So that wasn't the answer.

- **Lightbulb:** none.
- **Where the picture breaks:** the booth reads one script at a time per voice, so two callers queue at the door, not on the belt. Wrapping Voxxy in Bloodbank is listed in its own README as a future idea, and nothing like it exists today. Whether the pad plays progress recordings aloud is not confirmed here (verify).
- **Evidence:** `holocene/services/inbox-watcher/README.md:41-45,108-125`; `inbox_watcher.py:3910-4045` (polls Candystore every 1.5 s, never in the first 15 s, at most once per 30 s, about 2 s per render, `progress/` files, `audio.memo.narrated`); live narrated notes at 2026-11-12T01:25:36, :45 and :54Z.

### SCENE 13. While You Wait (side scenes)

Labelled on screen as **SIDE SCENE: not on this errand's route**. Two camera stops while Holly works.

**13a.** `[clock]`. The bell on the wall, the chore chart, the planner's desk, two brass hatches onto the back loop.

- **Shot:** Constance checks her pocket watch against the bell, to the second. On the way past the rules cabinet, the camera catches one of its clips closing on a crew-hall post-it, and moves on without comment. (What the rules cabinet does with a memo's notes is unverified; keep it a glance, never a claim.)
- **The beat:** The clock owns *when*. Its chores go out as envelopes through its own hatches, and its hands check the safe-to-repeat code first. One bell, no private alarms.

**DAMIAN:** Is this on my route?

**CONSTANCE:** No. Nothing on your errand waits for a bell. I own when things happen, not what anyone asked.

**CONSTANCE:** When I ring, the planner writes an envelope for each chore due. My hands take them through my two hatches and check the safe-to-repeat code before they lift a finger.

**DAMIAN:** Could I set a reminder to collect the answer?

**CONSTANCE:** *(does not blink)* A private alarm. In this building. One bell, no private alarms. The guard at the dock's window confiscates them.

**13b.** `[soundwing]`. Three inbound doors, the secure cage, a rack of eight passes, and through the glass, grey envelopes on the back loop.

- **Shot:** Gloria takes out her ear trumpet to hear Damian, then points it at the back loop: a stack of grey envelopes rising untouched past every hatch.
- **The beat:** The sound wing is a separate audio system, and it never calls Voxxy. Some of its envelopes have no hatch at all, so they ride up unsigned until the one-day scraper.

**DAMIAN:** You do audio. Do you send things to Voxxy?

**GLORIA:** Never have. My wing takes recordings in through three doors, locks them in the cage first, and runs eight passes over each transcript.

**GLORIA:** We write envelopes too. Look at that stack. *(the grey envelopes)* No hatch for that kind. Up they go, unsigned, until the one-day scraper.

**DAMIAN:** So not every envelope gets handled.

**GLORIA:** Some never get opened, dear. An envelope with no hatch is a letter to an empty room.

- **Lightbulb:** none. (Catalog bulb 16, *Single source of truth*, belongs at the bell.)
- **Where the picture breaks:** the clock owns when, not always who: a chore can run as a service or a Hermes job. A signed list of alarms stays outside the clock, each with a named owner and reason, and the guard at the window fails open, with an audit as the backstop. The sound wing is absent on Damian's Mac; its hatchless envelopes are enrichment passes over transcripts, not speech, and have no form pad.
- **Evidence:** bible card 15 (`candybar/executor/worker.py`, `native-clock-guard`); bible B11 and card 29 (`~/HeyMa/components/wax/src/wax/passes.py`, `audio.task.start` with no hatch); route research (waxd does not call Voxxy).

### SCENE 14. Signed Off

- **Set:** `[crew]`, the front desk and the express hatch.
- **Shot:** Holly hangs up, writes her answer into a book on the shelf behind her (spine: "holocene-pm, sessions"), and freezes mid-reach again. Okafor walks two post-its to the registered counter, takes his receipts, and only then signs the envelope's flap. The ribbon unclips; the envelope leaves the belt into his out-tray. Damian holds out his hand, palm up. Okafor regards the hand.
- **The beat:** The envelope is signed off after the work, and a signature means finished, not succeeded: success or failure is a post-it. The answer itself is not on any post-it.

**OKAFOR:** Holly has finished. "Invocation completed", "turn completed", stuck. Then I sign it off, which means I'm finished with it, not that it worked. That's on the post-it.

**DAMIAN:** *(reading the "completed" post-it)* This says which hatch and how long it took. Where's the answer?

**OKAFOR:** In Holly's session book, sir. Post-its say what happened, not what was said.

**DAMIAN:** Don't I get a reply slip?

**OKAFOR:** There is a window for those. Dashed tape: Pilot and Krebs use it, and nobody is at it today. In this hall, done is a post-it.

- **Lightbulb:** none in the sandbox set. (Catalog bulb 12, *Acknowledgement, and why things arrive twice*, belongs at this hatch.)
- **Where the picture breaks:** the crew hall also signs off envelopes it has closed as failed, and it re-sticks the same post-its for an envelope it already finished rather than running it twice. Reply slips are real in code: Pilot asks with `bb call` and listens on one shared reply line, matching by "came after"; Krebs would answer. Krebs is not running, there is no live reply traffic, and the n8n trigger's reply path has no live workflow (unverified). Draw the window dashed or not at all.
- **Evidence:** `hermes-gateway/README.md:1-14,471-529`; `schemas/bloodbank/agent/invocation.completed.json` (no reply text); live trace 01:26:39.716Z; `bloodbank/cli/call.py:21,53-55`, `krebs/src/krebs/service.py:62-77`, `pilot/src/lifecycle.js:15-26`; live jsz (no Krebs consumer).

### SCENE 15. Take Their Result

Two camera stops.

**15a.** `[control]`, the memo desk. Both shutters go up.

- **Shot:** Priya raises the ledger shutter: through it, Okafor's ledger open at one line, "finished". She raises the second shutter: Holly's session book, open at a thread headed with the memo's barcode. She copies the newest answer onto a script slip and checks the time it was written against the time she sent the envelope. Then she presses a small brass key into Damian's palm.
- **The beat:** The requester learns the work is done by reading the crew hall's ledger, and reads the answer from the workstation's session book. The answer text never rides the belt.

**PRIYA:** I don't wait for the post-it. I read the crew hall's ledger, the line for my envelope. It says finished.

**PRIYA:** Then Holly's session book: the thread with my memo's barcode, the newest answer, written after I sent the envelope.

**DAMIAN:** So the answer never went on the belt.

**PRIYA:** Not a word of it. The belt has notes about the answer. The answer lives in Holly's book.

**DAMIAN:** "Take their result and bring it back." I thought I'd be carrying something.

**PRIYA:** You are. *(the key)* A key to a shelf. Come on. It needs a voice.

**15b.** `[voxxy]`, the second visit.

- **Shot:** A long script slides under the door. Vinnie whistles, takes a pair of scissors to it at the full stops, and feeds the pieces to Mo one by one. Mo reads each in turn; recordings slide out under the door one after another. Vinnie racks a copy of each on a shelf with a one-hour sand timer. Damian looks from the script to Mo and back.
- **The beat:** The reply is cleaned up for speech, cut at sentence ends, and read one piece at a time, each recording coming back to the caller. No envelope, hatch or reply slip is involved. (Pays off Odette's line in Scene 4.)

**VINNIE:** Thirty words, he asked for. She wrote ninety. Long ones I cut at the full stops. Three pieces.

**MO:** One at a time. *(reading)* "Because your memo goes through a desk, a hatch, a workstation and a voice booth..."

**VINNIE:** Each piece goes out the moment it's done, and Priya takes it at the door. We keep a copy on the rack for an hour. Then it's gone.

**DAMIAN:** The librarian said you only read one script at a time.

**MO:** She's always right. Give me two at once and the second one waits at the door.

- **Lightbulb:** none.
- **Where the picture breaks:** the ledger is a database file on the same machine, and the session book is the workstation's own database; neither is on the belt, and the archive is only the fallback when the ledger has no line. The booth tries its voices in order (one is live), converts the audio, and hands back an address the desk fetches the file from. How many pieces depends on the length of the reply.
- **Evidence:** `holocene/services/inbox-watcher/memo_common.py:512-545,578-650`; `inbox_watcher.py:2484-2505,2626-2640,2726-2760` (ledger by command id; `state.db` by source and chat id, freshness check); `inbox_watcher.py:3078-3135,4764-4795`; `~/code/voxxy/app/main.py:628-657`; `~/code/voxxy/compose.yml` (cache 3600 s, engine chain); one request at a time per engine; split above about 160 spoken characters.

### SCENE 16. Bring It Back

Two camera stops.

**16a.** `[entrance]`. The reply bin on the upload shelf, Reggie's bell, Abernathy's empty spot.

- **Shot:** Damian turns the brass key in the *replies* bin and a recording drops in, then another, then another. Each time, a post-it is stuck: "memo voiced". Reggie listens at the belt for memo notes and, each time, rings a bell on a cord that runs to a pad. A car parked outside the arch has a pad on its dash; Abernathy's pad is in his hand. Reggie checks the car's pad first and hands the reply to Abernathy's. Abernathy strides in with the pad at his ear. Big Mo's voice is heard, small and tinny.
- **The beat:** Each finished piece goes on the reply shelf and is announced by a post-it that says where it is, never the sound itself. A bell from the memo door tells the pad to fetch and play it, and exactly one of car or phone speaks.

**REGGIE:** Piece one's on the reply shelf. "Memo voiced". The post-it says where it is and what it says. Never the sound itself.

**REGGIE:** *(rings the cord)* That's my bell to the pad. It fetches the piece off the shelf and plays it. Car or phone, never both.

**ABERNATHY:** *(pad at his ear)* "...and the booth reads one script at a time." *(lowers it)* I said thirty words.

**REGGIE:** "Memo replied", stuck. That's the last step anyone in here can see. The pad sends back "memo played" when it's done.

**ABERNATHY:** You took the long way round.

**DAMIAN:** I took both ways round.

**16b.** `[archive]`. The archive's racks and its lookup counter, Mr. Fitch on his rolling ladder.

- **Shot:** Fitch scans the barcode on Damian's key. Down the racks, slots light one after another, about forty, and the camera rides the ladder past them like a train past stations. Abernathy holds up a single yellow post-it he tore off a copy of on his way in: "turn started", from Codex. Fitch scans it: a different set of slots, three racks away.
- **The beat:** The archive filed every note of the run, once each, even the ones that turned up twice. One barcode, copied by every writer, rebuilds the whole errand; Damian's Codex question wears a different barcode, because it was a different system.

**FITCH:** Barcode, please. *(scans)* Uploaded, received, transcribed, dispatched, started, narrated three times, completed, voiced, replied, played. About forty notes, one barcode.

**DAMIAN:** Some of those came in twice.

**FITCH:** Then I filed them once. Same Note ID, same slot. *(a shrug)* You'll hear this called idempotent.

**ABERNATHY:** *(holds up the Codex post-it)* And this one?

**FITCH:** Different barcode. A Codex chat. It says he asked something, and nobody was asked to do anything.

**ABERNATHY:** *(reading the back of it)* Good work, Damian. And stop writing "Love, Damian" on things. The whole building reads them.

- **Lightbulb:** **idempotent** (*What does Idempotent mean?*), at the racks.
- **Where the picture breaks:** the archive is a reader that tore off copies; it is not the belt, and it makes no promise about how long it keeps them. The readback works only because every writer on this errand copied the memo's barcode. The control room upstairs rebuilds the same run from the same barcode. The dock's notes, like Damian's, rely on this clerk alone to catch a repeat.
- **Evidence:** `holocene/services/upload-proxy/upload_proxy.py:1123-1135,1295-1350,1680-1760` (one subscription to memo notes, a push line to the pad, polling fallback); `inbox_watcher.py:3184-3190,3199-3295,3763-3845` (replies bin, `memo.voiced` per piece, car-or-phone claim, `memo.replied`); `schemas/bloodbank/audio/memo.voiced.json`, `memo.replied.json`; `candystore/db.py` (`ON CONFLICT (id) DO NOTHING`); `memo_common.py:485-500,526-575`; live `GET :8683/events?correlationid=bdd7a80d-11a6-597d-860f-96a943bba9da` (about 40 notes, 14 kinds).

---

## The divergence ledger [P]

Every place Jarad's sketch and the real route differ, and how the script turns each into story.

| Jarad's sketch | What the code does | Where the script handles it |
|---|---|---|
| The hook hub packages the prompt into a parcel in a Bloodbank event. | The dock *unpacks*: a vendor's raw hook (the parcel) goes in, one house post-it comes out, packing slip on the back. | Scene 5a: "Parcels in, one house post-it out." |
| Then it's put in its envelope. | The dock writes no envelopes. Envelope means command, and nothing at the dock writes a command. | Scene 7, the turn: "Nobody at the dock writes envelopes." |
| The prompt rides to Voxxy. | A typed prompt only ever becomes a post-it ("turn started" with the question on it). It cannot reach Voxxy by itself. | Leg A ends at Scene 7; Leg B starts at a different door (Scene 8). |
| The belt carries it round to visit every component. | The belt keeps; readers come to it and tear off copies, and one hatch pulls each envelope. | Scenes 6a ("The belt carries it nowhere") and 6b; the rail is the visitor's route, not the note's. |
| The guys down in Voxxy process the message. | Voxxy is not on the belt: no hatch, no clip. A workstation answers; Voxxy gives the answer a voice over a plain API call. | Scene 8 ("Voxxy reads answers out loud"), Scene 12 ("We don't take deliveries"). |
| Take their result and bring it back. | No result rides the belt. The memo desk reads the crew hall's ledger and the workstation's session book; the audio goes via the reply shelf and a push to the pad. | Scenes 14, 15a ("A key to a shelf"), 16a. |
| (implied) A reply comes back on the bus. | Reply slips exist in code only for Pilot and Krebs (not running) and the n8n trigger (no live use). This errand reports done with a post-it, "memo replied". | Scene 14 aside, dashed window. |
| (research suggestion) the sound wing as a route to Voxxy. | The sound wing never calls Voxxy, and its hatchless envelopes are transcript passes, not speech. | Scene 13b. |
| A tour that visits every component on one request. | Not every room sits on any one request's route. | Scene 13, labelled side scenes. |

## Canon updates owed [P]

Before any of this prints, the bible needs these (one object, one meaning: new objects go in the table first).

1. **New world objects:** the **tape** (a recorded voice memo, between the pad and the Whisper booth); the **upload shelf** with its bins (inbox, status, progress, replies); the **ledger** (the crew hall's execution journal); the **session book** (a workstation's own record of its turns); the **memo door**, the **memo desk** and the **Whisper booth** as places. The tape must never be drawn as a parcel.
2. **B16 and card 9 (the regulars):** the memo desk and the memo door are doorbell posters too, not only the dock's poster. The memo desk compensates by reading the crew hall's ledger.
3. **Card 31 (the voice booth)** grows from an extra to a supporting part: callers are the memo desk and the Hermes voice plugin, over plain HTTP; it reads one script at a time per voice and keeps recordings for an hour.
4. **Doc drift:** `bloodbank/cli/call.py`'s docstring says reply lines are "correlation-specific"; the code listens on one fixed line, so the bible's held-back paragraph is right. Live, the batch hatch's hand limit is 68 and the express hatch's is 4, while the gateway docs say 4 and 2. No hand limit goes in a line.

## Open (verify) before shipping [P]

- Scene 11: that the crew hall posts "invocation progressed" from the workstation's interim lines, and that the Hermes plugin calls the library on every turn (route research: inferred).
- Scene 12: whether the pad plays progress recordings aloud.
- Scene 13a: what the rules cabinet's clips do with crew-hall notes on a memo run.
- Scene 14: the n8n trigger's reply path (unverified, no live workflow found).

## Notes for the engineer [P]

- Sets used: `entrance`, `bays`, `courier`, `library`, `dock`, `labeldesk`, `belt`, `cataloguer`, `control` (as the memo desk), `crew`, `staffing`, `voxxy`, `clock`, `soundwing`, `archive`. The `rules` station appears only as a glance in 13a.
- Hero forms: the `slip` form is never used, because reply slips are held back. The tape uses `recording`.
- Beats are one camera stop each; scenes with two stops are two beats in `script.ts`.
- Scene 4 is the one stop where the hero is somewhere else (the parcel waits at the dock window while the camera visits the library), and Scenes 11, 12 and 13 keep the envelope's marker hanging over the crew hall while the camera is elsewhere.

