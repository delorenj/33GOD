# Warehouse Tour Mode: the screenplay

Status: **draft 2 for Jarad**, 2026-11-12. Initiative I-10, The Manual. A guided rail ride through Warehouse One, the counterpart to the open sandbox. Draft 2 answers two critic reviews: accuracy first, then tone, then the rest.

- **[J]** = Jarad's own words (his 2026-11-12 direction for tour mode). **[P]** = a proposal from this script. Everything not tagged [J] is [P]. Strike, rename or redraw any of it.
- **Canon:** [`../world/warehouse-bible.md`](../world/warehouse-bible.md) (objects, verbs, belt physics B1-B18). **Voice:** [`../world/tone.md`](../world/tone.md). **Bulbs:** [`../lightbulbs/README.md`](../lightbulbs/README.md).
- **Route truth:** the verified route research of 2026-11-12 (code, the live big-chungus NATS server, and one live voice memo traced end to end: correlation `bdd7a80d-11a6-597d-860f-96a943bba9da`, upload 2026-11-12 01:25:28Z, final reply 03:08:22Z). **Code wins over the sketch.** Every place the script departs from Jarad's sketch is listed in the divergence ledger, and each one is turned into an in-story correction, never followed silently.
- **Engine data:** the same tour as typed beats lives in [`../sandbox/src/tour/script.ts`](../sandbox/src/tour/script.ts). This file is the source; the `.ts` is the cut for the rail engine. The dialogue below is generated from the `.ts`, so the two cannot drift; edit both together.

---

## Logline

On his first day in Warehouse One, Damian is handed an errand by a floor manager with no time: take this to the guys in Voxxy and bring back what they say. He does the sensible wrong thing first, and the building's oddballs walk him through the right way, room by room, until the answer plays out of the pad in his own vest.

## The shape in three legs [P]

1. **Leg A, the dock lesson (Scenes 2-7).** Damian types the manager's request into Codex and presses Enter. The rail follows that moment as a parcel to the dock, where it becomes one post-it on the front belt. The leg ends on the turn: *that post-it is a note about a question, and nobody has been asked to do anything.* Damian's wrong idea is Jarad's sketch, so the correction lands as story, not as an erratum.
2. **Leg B, the memo run (Scenes 8-12, 14-19).** The errand was on the Agent Pad in Damian's vest the whole time. It enters through a different door, the memo door, and this is the route that is real today: memo desk, the first envelope, the express hatch, a workstation, the staffing desk, the voice booth, and back to the pad. One barcode spans all of it. It is told in two envelopes, because that is what the live run did: a quick answer, then a follow-up an hour and forty-two minutes later.
3. **Side scenes (Scene 13).** Rooms that are not on this request's route get a short, labelled visit while the workstation thinks: the clock and the sound wing. Ten more rooms are never entered; they sit dashed on the lobby plaque and on the end card (`OFF_ROUTE`).

**The bridge between A and B is story, not data.** The Leg A parcel never becomes the Leg B envelope. They are two systems with two barcodes, and Fitch says so out loud in Scene 19.

**Why Warehouse One.** Damian's own building (Warehouse Two) has no crew hall, no memo desk, no voice booth, no cataloguer and no clock (bible 4.4). The tour is set in Jarad's building, with Damian as the visiting new hire. Abernathy says so in Scene 1.

## Production notes [P]

- **Comedy carries the concept.** Tone rule 9 caps a page at one wry line. Jarad's direction for this mode asks for "absolutely ridiculous characters" and "clever dialogue", so the tour relaxes that cap to *character-driven* comedy, and keeps everything else: no exclamation marks, no baby talk, no "Let's", no cartoon sound words, no condescension words, nobody called "son" or "kid". Every joke must be the model point said sideways. If you can delete a joke and lose nothing the reader needs, delete it.
- **Accuracy over comedy.** Where a joke and a fact disagree, the fact wins and the joke goes. Draft 2 cut or rewrote every line a critic found false.
- **The memo's words are staged; its shape and timings are the real run's.** What Damian says into the pad, and the answers Holly writes, are invented for the tour. The sequence of post-its, the two envelopes, and the timings on the pad's clock come from trace `bdd7a80d`.
- **The stopwatch spine.** Abernathy clicks a stopwatch in Scene 1 and the HUD shows the pad's own "Working" clock (`split` on a beat): 0:00 at the memo door; 0:01 at the memo desk, the envelope and the hatch; 0:08, 0:17 and 0:26 at the early booth visit (the three keep-alive clips); 1:12 at the signing off and the ledger; 1:14 at the pad (first sound); 1:24, then 1:42:33 at "Later"; 1:42:33, 1:42:37 and 1:42:42 at the late booth visit (three chunks); 1:42:42 at the end. Leg A has no clock: a typed prompt has no stopwatch.
- **Honest two-envelope staging.** The express `invoke` envelope gets a quick answer plus a `BACKGROUND:` line the desk never speaks. After that answer is spoken, the memo desk writes a second `start` envelope for the ordinary hatch (`voice_followup`, same barcode, same thread). That follow-up is spoken as "Holly, follow-up. ..." in three pieces. The two envelopes have different Note IDs on every note.
- **Hold-keepalive clips are file copies.** The early booth visit shows ready-made "Still on it" recordings from a shelf (the PhraseBank). Voxxy is not asked to render them. Spoken progress from the workstation is conditional: most voice turns write none, and Holly says so.
- **Chunking belongs to the memo desk.** Cleaning the text for speech and cutting it at sentence ends are the desk's jobs (`clean_for_speech`, `split_for_speech`, one `TtsGate` turn per piece). Voxxy core has no chunking. One-at-a-time is the GPU lock under the voice engine, and waiters queue. Recordings are cached for an hour.
- **The same-Note-ID lesson is a labelled what-if.** The traced run has no duplicate Note IDs. Fitch teaches the real mechanism (`ON CONFLICT (id) DO NOTHING`) as "a what-if, because it did not happen today", then says that two envelopes are two jobs, not a repeat.
- **Faces go on people.** Parcels, post-its, envelopes and tapes never have faces, never talk, never wave.
- **Locked verbs.** Stick, tear off a copy, sign off, stamp "still working", hand back, tear up, scrape, file, wait at the window. Nobody "delivers" a post-it. Post-it headlines are past tense; the first envelope says "invoke".
- **Real terms.** Once each, as "You'll hear this called X". JetStream, CloudEvents and "workqueue retention" stay off every face and out of every line.
- **Numbers.** Only stable ones are spoken, and the staged ones are labelled. Spoken numbers in the lines are the traced run's (one minute fourteen, an hour and forty-one minutes, about forty notes, fourteen kinds) or settings (a hundred and sixty letters, an hour in the cache). Recheck them before the script ships; live counts that drift (hatch patience, hand limits) stay in the evidence column.
- **(verify)** marks a claim the route research rated *inferred* or *unverified*. Close it before the line ships.
- **Engine set ids.** Each scene names the engine set in `[brackets]`. The memo desk has no set id of its own yet, so it is staged at `[control]`: it is Holocene's, and it sits on the ground floor under the control room's mezzanine. Proposal for the engineer: give it its own set (`memodesk`) when the art pass reaches it.

---

## The cast [P]

Twenty people, one building. Nobody is a mascot for a product; each is a job, and the job is the component. Everyone is drawn to the same proportions; height differs, bodies do not. Damian is drawn with affection and nothing from his life beyond his first name.

| # | Name (engine id) | Job in the warehouse | Real component | Look brief for the 3D artist | Voice and comic engine |
|---|---|---|---|---|---|
| 1 | **Damian** (`damian`) | New hire, visitor's lanyard | The reader | Same proportions as everyone. A hi-vis vest that reaches his knees (the vest says "new", not the body), a clipboard he holds like a shield, a lanyard swinging. Bright orange vest, butter trim. | Earnest, quick, says the sensible wrong thing out loud so the reader does not have to. Never stupid, only new. |
| 2 | **Mr. Abernathy** (`manager`) | Floor manager | The person who wants something done (a human requester) | Tall, barrel-chested, short-sleeved shirt and a tie clip, headset, a stopwatch on a lanyard, always mid-stride. Charcoal and safety red. | Grave as a general, short-tempered, urgent as a sneeze. Gives orders in fragments. Takes everything seriously except himself. |
| 3 | **Dash** (`dash`) | The courier, one uniform at every bay | `bb-hook` | Wiry, on roller skates, padded knee guards, a courier bag cut to fit exactly one box. Teal uniform, one bright stripe. | Unbothered pragmatist. "Shut, I turn round." Treats drama as a waste of milliseconds. |
| 4 | **Odette** (`odette`) | Lessons librarian, on the phone to the dock | Hindsight, reached by the `hindsight-recall` job card | Elderly, cardigan, half-moon glasses on a chain, a headset over a bun, an hourglass on the desk. Plum and cream. | Answers every call with "Last time on this project..." and means it. Racing an hourglass with perfect calm. |
| 5 | **Fenwick** (`fenwick`) | Receiving clerk at the dock bench | `hook-hub` (dispatch, job cards, and the clerk at the back, `bloodbank-publisher`) | Long arms, sleeve garters, a letter opener behind each ear, a phrasebook in every pocket. Brick red, brass buttons. | Polyglot of vendor dialects. Translates with the pride of a sommelier and the patience of a saint. |
| 6 | **Inspector Cruz** (`cruz`) | Label desk inspector | Naming contract, schemas, `assert_contract` | Compact, immaculate, reading glasses pushed up, a chained dictionary the size of a paving slab, one rubber stamp in a holster. Forest green. | Deadpan bureaucrat who is in love with the rules and a little moved by a correct label. |
| 7 | **Kofi** (`kofi`) | The dock's poster | The agent-hooks publisher (core publish, then a ping) | Very tall and lanky, long fingers, a pad of house forms on a lanyard, walks with ceremonial care. Coral and white. | Reverent about sticking notes. Rings the doorbell, hears "come in", and leaves deeply satisfied. Learns on camera that "come in" is not "got it". |
| 8 | **Professor Haugen** (`haugen`) | Belt geologist | NATS JetStream, the two loops | Weathered field geologist, rock hammer, a measuring stick taller than she is, boots, a hard hat with a lamp. The only person allowed to wear belt blue. | Reads the belt like rock strata. Height is age, and she cannot be talked out of it. |
| 9 | **Monsieur Lefèvre** (`lefevre`) | The cataloguer, at his clip | Enricher | Tall, thin, cravat, a label gun in a holster, white gloves. Aubergine. | Fussy connoisseur who will not lower himself to read a note that is not on his list. |
| 10 | **Reggie** (`reggie`) | Doorman at the memo door | The Agent Pad and its upload proxy (Holocene Auto) | Broad, kind, peaked cap, a bell on a cord at his chest, a key ring the size of a dinner plate, and a brass listening cup on a hose that runs from his desk to the loading slot. Burgundy with gold piping. | Old-school doorman who remembers every address. Takes the tape, rings the desk, and walks to the shelf himself if the hose goes quiet. |
| 11 | **Priya** (`priya`) | The memo desk | Holocene `inbox-watcher` | Small, fast, six rubber stamps in a belt, two pencils in her hair, a headset, a desk with a little window on each side. Saffron orange (darker than the post-its) and slate. | Frighteningly organised. Narrates her own checklist. Reads other people's ledgers because she does not trust a doorbell. |
| 12 | **Wren** (`wren`) | The Whisper booth | Warm GPU faster-whisper | Slight, enormous padded earmuffs, a typewriter that types silently, a padded booth. Sage green. Never speaks: Priya reads the typewriter aloud. | The silent one. Hears everything. Types it all. |
| 13 | **Mr. Okafor** (`okafor`) | Crew hall concierge, at the front desk | `hermes-gateway` and its bus plugin | Grand, tailcoat, white gloves, a ledger under one arm, a brass in-hand tray, a small "still working" stamp on a chain. Deep green and gold. | Five-star hotel manners applied to envelopes. Never takes credit for a job, only for the paperwork. |
| 14 | **Holly** (`holly`) | A workstation worker, badge "holocene-pm" | A Hermes profile | Overalls, a badge on a lanyard, a locker behind her, placards pinned up, a radio clipped to her strap. Frozen mid-pose until an envelope wakes her. Rust and cream. | Brilliant, brisk, and completely asleep until something arrives for her. |
| 15 | **Mags** (`mags`) | The staffing desk next door | The AutomaticAI gateway | Three desk phones, one in each hand and one on her shoulder, a rolodex, reading glasses on her head. Teal-green and mustard. | Phone juggler. "First agency that picks up." Knows which numbers ring out. |
| 16 | **Vinnie** (`vinnie`) | The voice booth's front window | Voxxy's `vox` core | Slick retro radio announcer, pencil moustache, a vintage ribbon mic, sleeves rolled. Indigo and red booth light. | Silky, theatrical, allergic to paperwork. "We don't take deliveries. Slide it under the door." |
| 17 | **Big Mo** (`mo`) | The voice in the booth's back room | Voxxy's `voxcpm` engine | Huge and gentle, cardigan, reading one script at a time on a music stand. Deep violet. | A warm baritone who will not read two scripts at once, however politely asked. |
| 18 | **Constance Bell** (`constance`) | The bellkeeper | Candybar, the clock | Railway conductor's uniform, pocket watch on a chain, a clipboard chore chart. Navy-black with brass. | Precise to the second, scandalised by private alarms. |
| 19 | **Gloria Waxman** (`gloria`) | Superintendent of the sound wing | HeyMa, waxd and intake | Silver curls, a blazer with eight pockets, headphones round her neck, a key to a secure cage. Dusty rose. No deafness gag: she hears fine. | Grand old dame of audio. Proud, a little sore that nobody collects her envelopes. |
| 20 | **Mr. Fitch** (`fitch`) | The archive's filing clerk | Candystore | Narrow, sleeve protectors, pencil behind the ear, a rolling ladder against the racks. Walnut brown. | Unflappable. Shrugs at duplicates. Can tell you a whole story from one barcode. |

**Colour rule** [P]: blue is the belt's, so only Professor Haugen wears it. Nobody's main colour is post-it yellow or envelope kraft, so the data objects always read first.

**Staging conventions for people** [P]:

- **Wren** never speaks. The scene shows a silent typewriter; Priya reads out what it typed. In the engine she is `present` on the memo desk beat and never a speaker.
- **Reggie's ear.** The pad hears about new notes through one core NATS subscription in the upload proxy. In the world that is a brass cup on the wall at the loading slot with a hose down to Reggie's desk. It has no clip and no notebook: it hears a note or it does not, and Reggie walks to the shelf if the hose goes quiet (the polling fallback). It is a new canon object, listed below.

---

## Staging data: the cue vocabulary [P]

Every `Line` in `script.ts` is `{ who, text, cue?, hold? }`. The playable engine ignores `cue`; the animation pass plays it. `hold` is milliseconds of silence *before the next line* (the pause before Cruz's stamp is the joke). A `Beat` may also carry `present` (people on set who never speak), `split` (a reading on the pad's clock, shown in a HUD corner) and `side` (a labelled side scene). These are the 73 cues the script uses:

| Cue | Business | Used in |
|---|---|---|
| `drop-pad-in-vest` | drops a small Agent Pad into Damian's vest pocket without looking | `brief` |
| `stopwatch-click` | clicks the stopwatch on his lanyard | `brief`, `closing` |
| `pat-clipboard` | patting his clipboard, not his vest | `brief` |
| `enter-key-down` | typing; the Enter key goes down | `enter` |
| `catch-parcel` | catches the parcel one-handed as it slides out | `enter` |
| `what-if-open` | the picture desaturates: a what-if insert begins | `courier`, `barcode` |
| `what-if-close` | back to colour, the what-if over | `courier`, `barcode` |
| `glance-alarm-clock-bin` | a glance at a bin of confiscated alarm clocks under the window | `window` |
| `hourglass-flip` | flips the hourglass | `window` |
| `card-slides-out` | a printed briefing card slides out of the window | `window` |
| `taste-label` | reads the label aloud like a wine list, tasting the words | `receiving` |
| `hold-up-postit` | holds up the finished post-it, packing slip stapled to the back | `receiving` |
| `stamp-refuse` | the REFUSED stamp comes down | `labeldesk` |
| `tap-dictionary` | taps the chained dictionary | `labeldesk` |
| `stamp` | a stamp comes down | `labeldesk`, `signoff` |
| `bow-to-slot` | bows to the slot after ringing the doorbell | `loading` |
| `tap-glass` | taps the glass with the measuring stick | `loading` |
| `face-slot` | turns to the slot and speaks to it | `loading` |
| `ruler-tilt-up` | the camera tilts up the day ruler | `loading` |
| `rock-hammer` | taps the belt with the rock hammer | `loading` |
| `runner-sprints` | the archive's runner tears off a copy and sprints for the racks | `readers` |
| `bin-note` | copies the note, then drops the copy in the bin | `readers` |
| `pan-rules` | the camera pans to the rules cabinet; one card's pick list is in frame | `readers` |
| `tap-vest` | taps Damian's vest | `turn` |
| `pad-record-light` | the pad's red record light blinks | `turn` |
| `headset-on-hook` | Abernathy's headset hangs on a hook behind him, still on | `memodoor` |
| `read-pad` | reads the pad | `memodoor` |
| `tape-drops-inbox` | the tape drops into the inbox bin under a tab: holocene-pm / today | `memodoor` |
| `ring-desk-bell` | rings a small bell on a cord toward the memo desk | `memodoor` |
| `glance-directory` | a glance at the lobby board behind him (the building directory) | `memodoor` |
| `glance-ticket-board` | a glance at the ticket board on the wall: white printed cards, none for this memo | `memodesk` |
| `whisper-typing` | Wren types on a silent typewriter, whispering to herself | `memodesk` |
| `quick-desk-glance` | a glance at the quick desk's half-shuttered window | `memodesk` |
| `glance-ntfy-bell` | a glance at the maintenance bell on the wall | `memodesk` |
| `draw-envelope` | pulls a kraft envelope from a drawer; the window label reads "invoke" | `envelope` |
| `copy-barcode` | copies the barcode on by hand | `envelope`, `followup` |
| `stamp-ring` | stamp, then through the doorbell slot marked BACK | `envelope` |
| `shutter-ledger-up` | raises the shutter on the ledger window | `envelope` |
| `in-hand-ribbon` | a red ribbon tethers the envelope to the belt: IN HAND | `hatch` |
| `ledger-line` | writes one line in the ledger | `hatch` |
| `registered-counter` | walks two post-its to the registered counter; a receipt with a belt number comes back | `hatch` |
| `glance-registry-board` | a glance at the registry board: holocene-pm to workstation 7 | `hatch` |
| `unfreeze` | unfreezes mid-reach | `staffing`, `followup` |
| `dial-dead-air` | dials; the line is dead | `staffing` |
| `dial-answer` | dials the next number; someone picks up | `staffing` |
| `stamp-still-working` | stamps the tethered envelope STILL WORKING | `staffing` |
| `no-postit-appears` | nothing appears at the registered counter | `staffing` |
| `slip-under-door` | a script slides under the door | `booth1`, `booth2` |
| `cue-clip-plays` | a ready-made recording from the cue shelf plays | `booth1` |
| `pocket-watch` | checks her pocket watch against the bell, to the second | `clock` |
| `point-alarm-bin` | points at the bin of confiscated alarms under the dock window | `clock` |
| `point-grey-stack` | points her pencil at the stack of grey envelopes on the back loop | `soundwing` |
| `glance-at-haugen` | a glance across the floor toward Haugen's belt | `soundwing` |
| `regard-palm` | regards his own open palm, like a receipt: empty | `signoff`, `followup` |
| `glance-up-mezzanine` | glances up at the mezzanine | `signoff` |
| `ledger-wink` | winks at the camera over the open ledger | `ledger` |
| `open-session-book` | opens a session book at a page headed with the memo's barcode | `ledger` |
| `tear-off-line` | tears the BACKGROUND line off the page and pockets it | `ledger` |
| `clean-for-speech` | runs a pencil down the answer, striking asterisks and anything a person cannot say | `ledger` |
| `pad-clock-stops` | the pad's working clock stops | `pad` |
| `point-ear` | points at the ear: a brass cup on the wall, a hose running to the loading slot | `pad` |
| `fetch-from-shelf` | the pad fetches a recording from the reply shelf | `pad` |
| `voice-from-pad` | Big Mo's voice plays, small and tinny, from the pad | `pad` |
| `later-card` | title card over black: LATER | `followup` |
| `write-session-book` | writes the page into her session book | `followup` |
| `cut-at-full-stops` | scissors at the full stops: the answer becomes three slips, the first shortest | `booth2` |
| `point-at-mo` | points through the window at Mo, alone at his music stand | `booth2` |
| `mo-lock` | holds one hand up: the lock | `booth2` |
| `mo-reads` | reads the slip into the mic; a recording slides out under the door | `booth2` |
| `voiced-postit` | a "voiced" post-it goes up as each recording reaches the reply shelf | `booth2` |
| `pull-drawer` | pulls the drawer for the barcode; slots light down the racks | `barcode` |
| `glance-mezzanine` | a glance up at the control room window | `barcode` |
| `hand-pad` | hands Abernathy the pad | `closing` |

---

## The route map [P]

| Scene | Title | Engine set(s) | The object at this step | Real hop |
|---|---|---|---|---|
| 1 | The Briefing | `entrance` | a tape on the Agent Pad (unsent, in Damian's vest) | none yet |
| 2 | Enter | `bays` | **parcel** (Codex's own dialect) | Codex `UserPromptSubmit` hook |
| 3 | The Courier | `courier` | parcel | `bb-hook` over the hub's socket, fail-open |
| 4 | The Driver's Window | `library` (parcel waits at `dock`) | parcel waits; a **briefing card** goes back | hook-hub sync job cards, `hindsight-recall` |
| 5 | Receiving | `dock`, `labeldesk` | **post-it**, "turn started" | `bloodbank-publisher`, Codex adapter, `assert_contract` |
| 6 | The Belt | `belt`, `cataloguer` | post-it on the front belt; copies torn off | doorbell publish, `BLOODBANK_EVENTS`, readers, the rules cabinet's pick list |
| 7 | Nobody Asked Anybody | `belt` (the edge) | post-it, unaddressed | the turn: no command is written at the dock |
| 8 | The Memo Door | `entrance` | **recording** (a tape), then post-it "memo uploaded" | Agent Pad PUT, upload proxy, the shelf, wake call |
| 9 | The Memo Desk | `control` x2 | post-its "memo received", "transcribed", "routed", then the **envelope**, "invoke" | inbox-watcher, Whisper, `bb-emit --kind command` |
| 10 | The Express Hatch | `crew` | envelope on the back belt, then "in hand" | `BLOODBANK_COMMANDS`, interactive hatch |
| 11 | The Workstation Phones Out | `staffing` | envelope in hand; no progress post-it | Hermes turn, gateway route |
| 12 | The Voice Booth, Early | `voxxy` | keep-alive clips from a shelf; post-it "memo narrated" | PhraseBank file copies; no Voxxy render |
| 13 | While You Wait (side scenes) | `clock`, `soundwing` | none on route | Candybar; HeyMa |
| 14 | Signed Off | `crew` | envelope signed off; post-its "invocation completed", "turn completed" | ack after the turn |
| 15 | The Ledger and the Session Book | `control` | a ledger line, a session-book page, the answer cleaned for speech | gateway SQLite ledger, `state.db`, `split_background` |
| 16 | First Sound | `entrance` | **recording** on the pad; post-its "voiced", "replied", "played" | reply shelf, the ear, speaker line |
| 17 | Later | `crew` | second **envelope**, "start", same barcode | ordinary hatch, `voice_followup` |
| 18 | The Voice Booth, Late | `voxxy` | three scripts under the door; three recordings; post-its "voiced" | `clean_for_speech`, `split_for_speech`, `TtsGate`, `POST /synthesize-url` |
| 19 | Bring It Back | `archive`, `entrance` | the barcode read back; the pad handed over | Candystore, `ON CONFLICT (id) DO NOTHING` |

**Every Bloodbank part is visited:** the courier (3), the dock (4-5), the label desk (5), the posters (6, 9, 10), the belt's front (6-7) and back (10), clips, a visitor's pass and runners (6), the archive (19). **Off-route rooms get labelled side scenes:** the clock and the sound wing (13), the rules cabinet (6, one line and a pan). **Ten more rooms are never entered** and are shown dashed on the lobby plaque and the end card:

| Room | Real component | Why the rail skips it |
|---|---|---|
| The ticket board and the marker | Plane and px | No ticket is involved in a memo. White printed cards in pockets, never sticky notes. |
| HR and the job description binder | Flume and the role template | HR furnishes a workstation. Holly was furnished long before the tour began. |
| The building directory | pjangler | The lobby board says which project lives where. Glanced at in the lobby, never used by the errand. |
| The tool crib | Skillex | The master copy of every how-to placard. Holly’s placards point at it. |
| Shift leads and the playbook | PM desks and Momo | They groom the ticket board and comment. Nothing on this errand asks them. |
| The inspector on call | Jev | Stamps pass or fail on request. Nobody called him. |
| Maintenance | monitoring stack and ntfy | Sensors, rounds and a radio page. Only a failed memo rings its bell, and this one did not fail. |
| The outbound dock | Telegram and ntfy pings | Where results leave the building by other roads. This answer left by the pad. |
| The dictation mic | Vinyl | Sits at your own workstation, beside the sound wing’s word list. |
| Flat-pack crates | Aperture | Crates for building a second warehouse. Some are still being designed. |

---

## The scenes

Format for every scene: **set** (engine id), **shot**, **the beat** (what the reader must understand, at most two model points), **dialogue** (generated from `script.ts`; stage directions in italics are the line's `cue`), **lightbulb**, **where the picture breaks**, **evidence**. All dialogue is [P] unless tagged [J].

### SCENE 1. The Briefing

*The entrance.* *(engine: `brief`)*

- **Set:** `[entrance]`. The entrance arch, WAREHOUSE ONE painted on the lintel, a visitor-pass desk, the rail platform with one small open car, and a lobby plaque with the rail map (ten rooms drawn dashed: see the end card).
- **Shot:** Wide and low. Abernathy enters frame left mid-stride and never fully stops; the camera has to pan to keep him. Damian stands under his lanyard. On "it's packaged up" Abernathy drops a small Agent Pad into Damian's vest pocket without looking. Damian does not notice. The camera does (a two-frame push-in on the pocket, its red record light glowing: *unsent*). On "Clock's running" Abernathy clicks a stopwatch; it stays on his lanyard for the whole tour.
- **The beat:** The errand: a question goes in, an answer comes back. This is Warehouse One, not Damian's building, and the rail does not enter every room. Plant the pad and the stopwatch.
- **Teaches (the notebook line):** The errand: a question goes in, an answer comes back. This is Warehouse One, not your building, and the rail does not enter every room.

**ABERNATHY** [J]: Look, I know you're new here. But what better way to learn your way around. The campus. Or something.

**ABERNATHY** [J]: *(drops a small Agent Pad into Damian's vest pocket without looking)* I need you to deliver this message to the guys down in Voxxy. Now, it's packaged up. So you're gonna have to take it through processing yourself.

**ABERNATHY** [J]: When the guys are done. Just take their result and bring it back here. I'll be waiting for you.

**DAMIAN**: Processing. Right. Where's the message?

**ABERNATHY**: *(clicks the stopwatch on his lanyard)* On you. And this isn't your building. It has rooms yours hasn't got yet. Stay on the rail. Clock's running.

**DAMIAN**: *(patting his clipboard, not his vest)* On me. So it's whatever I write down.

- **Lightbulb:** none.
- **Where the picture breaks:** None needed yet. The pad is a real device (car, phone or browser); the "tape" it holds is a recorded voice memo. The pad's working clock is real, and the stopwatch is its twin.
- **Evidence:** Bible 4.4 (Damian's building has no crew hall, memo desk or voice booth); route research, framing note; `[J]` lines are Jarad's, word for word, including "Just take their result and bring it back here."

### SCENE 2. Enter

*Enter.* *(engine: `enter`)*

- **Set:** `[bays]`. Damian's own typing desk at the Codex bay: a keyboard, a screen, and a small hatch in the desk's side with a roller under it.
- **Shot:** Macro on the Enter key going down. Cut to the hatch: one brown box slides out with a stripe and a handwritten label, `UserPromptSubmit`. No logo. Dash skates into frame and catches it one-handed.
- **The beat:** Pressing Enter fires a hook, and the vendor packs one parcel in its own dialect. The vendor holds your question until a briefing card comes back, then takes its own road to its own model. The warehouse is beside that road, never on it.
- **Teaches (the notebook line):** Pressing Enter fires a hook, and the vendor packs one parcel in its own words. The vendor holds the question until a briefing card comes back, then takes its own road to its model. The warehouse sits beside that road, never on it.

**DAMIAN**: *(typing; the Enter key goes down)* Dear Voxxy. The manager wants an answer, please. Love, Damian. And... Enter.

**DASH**: *(catches the parcel one-handed as it slides out)* Box for the dock.

**DAMIAN**: It's for Voxxy.

**DASH**: It's for the dock. That label is Codex saying “he asked something”, in Codex's own handwriting. Every vendor writes its own.

**DAMIAN**: And the answer?

**DASH**: Codex holds your question while I wait at the window for a card. Then it takes its own road to its own model. We're not on that road. We're beside it.

- **Lightbulb:** none here. (Catalog bulb 2, *What is a hook?*, belongs at this bay when it is drafted.)
- **Where the picture breaks:** Vendors are programs on your own desk, not companies with vans. The parcel is a copy of the moment, not your question's trip to the model. Codex does not stop to wait for the warehouse's post-it, only for the briefing card (Scene 4).
- **Evidence:** `bloodbank/services/agent-hooks/clients/codex.py:56-57`; `hooks.master.json:28-32` (`UserPromptSubmit` to role `prompt_submit`); bible section 1.

### SCENE 3. The Courier

*The courier.* *(engine: `courier`, bulb `failopen`)*

- **Set:** `[courier]`. Horizontal rollers from the bays to a roller door marked RECEIVING, drawn flat and fast, visibly unlike the tall vertical belt.
- **Shot:** Tracking shot beside Dash. On Damian's question, a desaturated "what if" insert (`what-if-open`): the door is shut, Dash pivots on one skate and rolls back with the box still under her arm. The curb in front of the door stays empty. Back to colour on `what-if-close`, with Dash's second, slower line.
- **The beat:** If the dock is shut, the courier turns round at once, nothing queues, and no post-it is written. A jammed dock is slower, a short wait and then a shorter one for half a minute. Either way the vendor's real work carries on. That is fail-open.
- **Teaches (the notebook line):** A shut door turns the courier round at once, with the parcel still in hand and no post-it written. A jammed door costs the vendor a short wait, then a shorter one for half a minute. That is fail-open.

**DAMIAN**: What if the dock's closed?

**DASH**: *(the picture desaturates: a what-if insert begins)* Shut, I turn round at once. Box still under my arm, no post-it written, nothing queued. I don't knock twice and I don't leave it on the step.

**DAMIAN**: So the news...

**DASH**: Never gets written down. You'll hear this called fail-open: when the helper is down, the real work carries on without it.

**DAMIAN**: That's a little bleak.

**DASH**: *(back to colour, the what-if over)* Shut is quick. Jammed is slower: a short wait the first time, then a shorter one for half a minute. The skates are for morale.

- **Lightbulb:** **failopen** (*What is Fail-open?*), bobbing beside the shut door in the insert.
- **Where the picture breaks:** The "conveyor" is a local socket between one small program and another. Nothing waits at a curb: a shut door means the moment never becomes a post-it at all. A stuck door is the expensive case, not a shut one. The Mac wrapper bounds the wait to about one second (W2-4).
- **Evidence:** `bloodbank/services/hook-hub/client/bb-hook:1-30,197-211,334-371,543-546` (every failure prints nothing and exits 0, no spool); 3 s deadline, then 0.25 s probes for 30 s after one stall; `content.ts` failopen bulb.

### SCENE 4. The Driver's Window

*The driver’s window.* *(engine: `window`)*

- **Set:** `[library]`, while the parcel waits at `[dock]`. The engine's hero marker hangs over the dock's driver's window; the camera visits the lessons library. A bin of confiscated alarm clocks sits under the window (a plant for Scene 13).
- **Shot:** Open on Dash idling at a small window cut into the dock wall, box under her arm, a laminated job card with a stopwatch clipped above the frame. A phone rings. Whip to the library: Odette lifts the receiver and flips an hourglass with her other hand. Back to the window: a printed card slides out into Dash's palm. Fenwick's first line is written for two clerks: one at the back is already writing the post-it, one at the window runs the cards.
- **The beat:** Some parcels wait at the window for a briefing card, which goes back to the vendor inside a time limit and never goes on the belt. The post-it is written by a different clerk while you wait. The lessons library is reached by phone, not by the belt.
- **Teaches (the notebook line):** Some parcels wait at the window for a briefing card. It goes back to the vendor inside a time limit and never goes on the belt. The post-it is written by a different clerk while you wait.

**FENWICK**: *(a glance at a bin of confiscated alarm clocks under the window)* Codex question. Two clerks, one parcel. At the back, a clerk is already writing the post-it. Up front, the window cards run for you: reminders, the library, the code map.

**DASH**: I always wait at the window. It's the only place anyone hands me anything back.

**ODETTE**: *(flips the hourglass)* Last time on this project, you learned the voice booth reads one script at a time. Card's printing.

**FENWICK**: *(a printed briefing card slides out of the window)* Briefing card. It goes back to Codex before Codex carries on. It never goes on the belt.

**DAMIAN**: Doesn't the archive have a card too?

**FENWICK**: The archive hands its card out when a session opens, not at every question.

**ODETTE**: And if the hourglass runs out, the card leaves without my paragraph, dear. Codex will wait that long, and not a second more.

- **Lightbulb:** none in the sandbox set. (Catalog bulb 3, *Asking vs announcing*, belongs at this window when drafted.)
- **Where the picture breaks:** The job cards are functions inside one program, not clerks; the library is a phone call over the internet, and the window's whole budget is a few seconds. The archive's card is handed out when a session opens, not at every question, so Damian's "doesn't the archive have a card too" is answered, not dodged. Odette's "last time" line is a planted callback: Scene 18 pays it off.
- **Evidence:** `hook-hub/hub.py:65-66,670-722,729-741` (sync budget 2.5 s default, 14 s max); `handlers.toml:11-50,65-77,168-176` (`skill-reminder` 1 s, `hindsight-recall` 11 s, `codegraph-prompt` 2 s); `bloodbank-publisher` runs async, serialised per session (`hub.py:595-626`). (verify) the session-open timing of the archive card against `handlers.toml` before the line ships.

### SCENE 5. Receiving

2 camera stops.

**5a.** Receiving. *(engine: `receiving`, bulb `normalization`)*

- **Set:** `[dock]`. The long bench under the RECEIVING sign. Fenwick at the front; at the back, a second station where the post-it is written.
- **Shot:** Fenwick slits the Codex box with the letter opener from behind his ear, reads the label aloud like a wine list (`taste-label`), and writes one yellow post-it. Close on the post-it: headline "turn started", a speech-bubble icon, a small "from: Codex" corner, a barcode along the bottom, a "came after" line. He staples the original packing slip to its back. Dash has her card and is already waiting at the window.
- **The beat:** Parcels in, one house post-it out, written one way whatever the vendor said. The barcode is one per conversation.
- **Teaches (the notebook line):** Parcels in, one house post-it out: “turn started”, vendor in the corner. One barcode per conversation. That is normalization.

**FENWICK**: *(reads the label aloud like a wine list, tasting the words)* Codex writes “UserPromptSubmit”. A capital on every word, very sure of itself. Gemini writes “BeforeAgent”. Same news, different vineyard.

**FENWICK**: *(holds up the finished post-it, packing slip stapled to the back)* The house writes it one way. “Turn started.” The vendor’s own packing slip goes stapled to the back.

**DAMIAN**: What's the stripe along the bottom?

**FENWICK**: The barcode. One per conversation, made from Codex’s own session number. Every note from this chat wears it. “Came after” names the note before.

**DASH**: Still waiting on my card. The post-it isn't my department.

**5b.** The label desk. *(engine: `labeldesk`)*

- **Set:** `[labeldesk]`. Inspector Cruz's desk beside the dock: the chained house dictionary, the form pads, one stamp.
- **Shot:** Cruz holds the post-it at arm's length, stamp hovering. A beat of pure silence (the `hold` before the second "Then the whole building knows" is the joke). Then the stamp comes down.
- **The beat:** The label desk checks house words, and the vendor's name never goes in the headline. The question itself rides on the post-it, so anyone who tears off a copy can read it.
- **Teaches (the notebook line):** The label desk allows house words only, and the vendor never goes in the headline. Your question rides on the post-it for anyone to read.

**DAMIAN**: Shouldn’t it say “Codex turn started”? So people know who.

**CRUZ**: *(the REFUSED stamp comes down)* Refused.
*[hold 400 ms before the next line]*

**CRUZ**: *(taps the chained dictionary)* Vendors live in the corner. The headline says what happened, in house words, and every word is in the book.

**DAMIAN**: What's written inside? My question?

**CRUZ**: Word for word. Anyone who tears off a copy can read what you asked.

**DAMIAN**: I wrote “Love, Damian.”
*[hold 600 ms before the next line]*

**CRUZ**: *(a stamp comes down)* Then the whole building knows.

- **Lightbulb:** **normalization** (*What is Normalization?*, the drafted modal), bobbing beside the bench. None at the label desk. (Catalog bulb 15, *What is a schema?*, belongs there.)
- **Where the picture breaks:** The dock is one program with about 35 job cards, not a crew, and the post-it is written by a separate back-room clerk the courier never waits for. The label is house format; the body still carries Codex's raw payload on the back. Copies of the inspector sit at several benches, some writers skip the desk, and the belt never checks anything. Damian's "Codex turn started" is the natural mistake; Cruz's refusal is the real rule.
- **Evidence:** `hook-hub/hub.py:595-626,656-668,712-715` (`bloodbank-publisher`, async, serialised per session); `agent-hooks/clients/codex.py:149-157` (`turn.started`, `prompt_text`, raw payload kept); `clients/base.py:267-285` (correlation from session id, causation = previous note); `core/validate.py:1026` (`assert_contract`).

### SCENE 6. The Belt

2 camera stops.

**6a.** The belt. *(engine: `loading`, bulb `retention`)*

- **Set:** `[belt]`. The loading point at the foot of the glass shaft; a doorbell with a brass slot; the sorter; the day ruler up the side.
- **Shot:** Kofi carries the post-it in both hands like a ring on a cushion, rings the doorbell, hears a muffled "come in", posts it through the slot and bows to the slot (`bow-to-slot`). Haugen's measuring stick enters frame and taps the glass. Damian thanks the slot, which is the joke and the lesson: it heard, it did not keep. Inside: a stamp prints a belt number, the sorter reads one word on the label ("evt") and the note starts up the front loop. Tilt up the day ruler: *Today*, *1 day*, *7 days*.
- **The beat:** The dock's poster uses a doorbell: "come in" means heard, not kept. On the belt, height is age, and the scraper takes notes at seven days, read or not. The belt carries nothing sideways; readers come to it.
- **Teaches (the notebook line):** The dock’s poster rings a doorbell: heard is not kept. On the belt height is age, and the scraper takes post-its at seven days, read or not.

**KOFI**: *(bows to the slot after ringing the doorbell)* “Come in.” Another one safely home.

**HAUGEN**: *(taps the glass with the measuring stick)* It said it heard you, Kofi. It has never once said it kept one.

**KOFI**: ...Never once?

**DAMIAN**: *(turns to the slot and speaks to it)* Thank you.

**HAUGEN**: It heard that. Whether it kept it is another matter. And if the door's shut, your note hits the floor and nobody tries again.

**HAUGEN**: *(the camera tilts up the day ruler)* Now watch it climb. Height is age: the bottom is a minute ago, the top is a week. At seven days the scraper takes it, read or not.

**DAMIAN**: So the belt carries it to Voxxy.

**HAUGEN**: *(taps the belt with the rock hammer)* Carries it? Nothing on this belt has moved an inch sideways in its life. It's sediment. Readers come to it.

**6b.** Tear off a copy. *(engine: `readers`, bulb `fanout`)*

- **Set:** `[cataloguer]`. Beside the front belt, where the readers stand: the archive's runner, the control room's visitor's window above, Lefèvre's aubergine clip on the belt, and the rules cabinet at the edge of frame.
- **Shot:** Three quick cuts as the post-it passes: the archive's runner tears off the top sheet and sprints for the racks (`runner-sprints`); up on the mezzanine a hand with a visitor's pass copies a number into a notebook; Lefèvre's clip copies it and he bins the copy (`bin-note`). Haugen pans the camera to the rules cabinet (`pan-rules`): one card's pick list says "invocation completed" and nothing else. Every other note slides past it.
- **The beat:** Readers tear off copies and the original stays. A pick list lets other notes slide past. Nobody is reading for Voxxy.
- **Teaches (the notebook line):** Readers tear off copies and the original stays. A pick list, like the rules cabinet’s “invocation completed”, lets other notes slide past. That is fan-out.

**HAUGEN**: *(the archive's runner tears off a copy and sprints for the racks)* Readers. The archive's runner tears off a copy for the racks (you'll hear that runner called a sidecar). The control room reads through its visitor's window, pass in one hand, notebook in the other.

**DAMIAN**: They took it off the belt?

**HAUGEN**: They took a copy. The original stays for the next reader. You'll hear this called fan-out.

**LEFÈVRE**: *(copies the note, then drops the copy in the bin)* “Turn started”? Non. I take a copy of everything, monsieur, then bin what is not a finished tool call. A question is not a finished anything.

**HAUGEN**: *(the camera pans to the rules cabinet; one card's pick list is in frame)* That card at the rules cabinet is fussier. It wants only “invocation completed”. Everything else slides past it. That is a pick list.

**DAMIAN**: So who's reading it for Voxxy?

**LEFÈVRE**: Look at the clips, monsieur. Do you see one for Voxxy?

- **Lightbulb:** **retention** (*What is Retention?*) at the scraper in 6a; **fanout** (*What is Fan-out?*) in 6b.
- **Where the picture breaks:** Real streams do not move; the climb stands for age. The doorbell's "come in" is the server hearing the note, not storing it, and the dock's notes carry no duplicate-guard number. A clip is a bookmark the server keeps, not a binder clip, and the control room keeps its own place in its own notebook, so "the belt remembers everyone" is false. Lefèvre copies every note and bins the unfinished ones; he never leaves a note unread. The pick list shown at the rules cabinet is an example; real cards choose their own.
- **Evidence:** `agent-hooks/core/nats_publish.py:131-174`, `core/publisher.py:276` (plain publish then ping, no message id, no retry); `bloodbank/compose/nats/streams.json:35-42` (front loop, 7 days); live `:8222/jsz` 2026-11-12 (about two dozen readers on the front loop, including `candystore-events`, `enricher-events` and Holocene's); `33god-platform/enricher/main.py:164`; `n8n-nodes-bloodbank` durable triggers.

### SCENE 7. Nobody Asked Anybody

*Nobody asked anybody.* *(engine: `turn`, bulb `eventcommand`)*

- **Set:** `[belt]`, the edge of the shaft where the yellow front meets the kraft back through the glass.
- **Shot:** Damian walks round the shaft with his nose to the glass, past his own yellow note climbing the front, until he can see the back loop: envelopes, kraft, windowed, none of them his. Haugen waits for him to arrive at the thought. Then she taps his vest (`tap-vest`). The red record light is blinking (`pad-record-light`).
- **The beat:** A post-it announces; an envelope asks one worker to do one thing. Nothing at the dock writes envelopes, and Voxxy is not on the belt at all. (The turn of the act: Leg A ends here.)
- **Teaches (the notebook line):** A post-it says what happened; an envelope asks one worker to do one thing. Nothing at the dock writes envelopes, and Voxxy is not on the belt.

**HAUGEN**: That's a note about a question. It says “he asked”. It doesn't ask anyone to do anything.

**DAMIAN**: So how does my message get to Voxxy?

**HAUGEN**: You keep saying “message”. In here that's a post-it or an envelope. A post-it says what happened. An envelope asks one worker to do one thing, and nobody at the dock writes envelopes.

**DAMIAN**: And Voxxy?

**HAUGEN**: *(taps Damian's vest)* Not on the belt at all. No clip, no hatch. They have a door you slide things under. What’s that in your vest?

**DAMIAN**: *(the pad's red record light blinks)* The manager's pad. One memo, unsent. It was on me the whole time.

- **Lightbulb:** **eventcommand** (*Event or command?*), where the two faces meet.
- **Where the picture breaks:** In the real format every note, post-it or not, travels in the same standard wrapper; the warehouse keeps the word "envelope" for commands only, so one object keeps one meaning. And Damian's typed question stops here for good: it never becomes the errand. Leg B is a different system with its own barcode.
- **Evidence:** Grep of `hook-hub` and `agent-hooks` (no command written anywhere); `~/code/voxxy/README.md:628-629` (wrapping Voxxy in Bloodbank is listed as future work).

### SCENE 8. The Memo Door

*The memo door.* *(engine: `memodoor`, pad clock `0:00`)*

- **Set:** `[entrance]`, round the side of the arch: a brass slot marked MEMOS, Reggie in his cap, and behind him the **upload shelf**, four labelled bins: *inbox*, *status*, *progress*, *replies*. Above the slot hangs the ear: a brass cup with a hose that runs away along the wall toward the loading slot (it is paid off in Scene 16). The pad's working clock starts: 0:00.
- **Shot:** Damian sprints back along the rail. Abernathy's spot is empty; his headset hangs on a hook, still on (`headset-on-hook`). Reggie takes one look at the pad and points at the slot. Damian presses send. The tape drops into the *inbox* bin under a tab reading "holocene-pm / today". Reggie prints a barcode from the bin's address, rings a small bell on a cord towards the memo desk, and sticks one post-it at the doorbell. A glance at the lobby board behind him: the building directory (`glance-directory`), not used today.
- **The beat:** The errand comes in through a different door, the memo door, not the dock. The tape's shelf address becomes the barcode that every note from this errand will wear. And the memo is for a worker; Voxxy gives the answer a voice, it does not write it.
- **Teaches (the notebook line):** The errand enters by the memo door, not the dock. The tape’s shelf address becomes the barcode every later note wears.

**REGGIE**: *(Abernathy's headset hangs on a hook behind him, still on)* Memo door. Pads only. That's a tape, not a parcel. Parcels go to the dock.

**DAMIAN**: It's for Voxxy.

**REGGIE**: *(reads the pad)* It's for holocene-pm. That's a worker. Voxxy doesn't answer questions. Voxxy reads answers out loud.

**REGGIE**: *(the tape drops into the inbox bin under a tab: holocene-pm / today)* On the shelf: inbox, holocene-pm, today. That shelf address is your barcode now. Every note from this errand wears it.

**REGGIE**: *(rings a small bell on a cord toward the memo desk)* “Memo uploaded”, stuck. And a ring for the memo desk, so it doesn't wait for its next look round. Miss the ring and it finds the tape a few seconds later anyway.

**REGGIE**: *(a glance at the lobby board behind him (the building directory))* Lobby board's behind you if you ever need to find a project. Not on your rail today.

- **Lightbulb:** none.
- **Where the picture breaks:** The memo door is a web upload from the pad to the upload proxy, nothing to do with the dock; the tape is not a canon parcel, because parcels are raw hooks only. The real pad uploads when the recording stops; the "unsent memo" in Damian's vest is a story device. The shelf is object storage. Reggie's post-it also goes through a doorbell: heard, not kept. The words of the memo are staged; the timings are the run's.
- **Evidence:** `holocene/services/inbox-watcher/README.md:7-19`; `holocene/services/upload-proxy/upload_proxy.py:635-648,1041-1046,1100-1116` (PUT `/upload/inbox/<agent>/...`, bucket `holocene-auto`, `audio.memo.uploaded`, memo id = uuid5 of the shelf address); `inbox_watcher.py:4800-4829` (`/wake`, 5 s fallback listing); live trace `bdd7a80d`, upload 01:25:28Z.

### SCENE 9. The Memo Desk

2 camera stops.

**9a.** The memo desk. *(engine: `memodesk`, pad clock `0:01`; present, silent: wren)*

- **Set:** `[control]` (ground floor, under the mezzanine; Holocene's memo desk). Wren is `present` and never speaks.
- **Shot:** Priya's desk has three little windows: one onto Wren's padded booth (open), one onto the crew hall's ledger (shutter down), one onto a shelf of session books (shutter down). The bell rings; Priya is already moving. She glances at the ticket board on the wall (`glance-ticket-board`: white printed cards, none for this memo), stamps, checks the routing board, pulls the tape and slides it through Wren's window. Wren types on a silent typewriter (`whisper-typing`); Priya reads the page. A glance at the quick desk's half-shuttered window (`quick-desk-glance`), and a glance at the maintenance bell on the wall (`glance-ntfy-bell`).
- **The beat:** The memo desk turns the tape into text, and records each thing it has done as a post-it. Some memos it can answer itself at the quick desk with no envelope; the quick desk looked at this one and said: a job for a worker. A failed memo is the one memo post-it that rings the maintenance bell.
- **Teaches (the notebook line):** The memo desk turns the tape into text and sticks a post-it for each step. A quick question can be answered at the desk; a memo for a worker gets an envelope.

**PRIYA**: *(a glance at the ticket board on the wall: white printed cards, none for this memo)* Ring heard. “Memo received”, stuck. Worker holocene-pm, routable. Wren?

**PRIYA**: *(Wren types on a silent typewriter, whispering to herself)* Wren types it, silently. He said: “Holly. Why does the car take so long to talk back. Thirty words. Go.”

**PRIYA**: “Memo transcribed”, stuck: the words, how long it ran, which ears heard it.

**DAMIAN**: Couldn't you answer it yourself?

**PRIYA**: *(a glance at the quick desk's half-shuttered window)* Some I can, at the quick desk, with no envelope at all. “Routed”, stuck. The quick desk looked at this one and said: a job for a worker.

**PRIYA**: *(a glance at the maintenance bell on the wall)* And if I can't finish, I stick “memo failed”. That is the one memo post-it that rings the maintenance bell.

**9b.** The first envelope. *(engine: `envelope`, pad clock `0:01`)*

- **Set:** `[control]`.
- **Shot:** Priya pulls a kraft envelope from a drawer (`draw-envelope`). Inserts, close: the window label reads "agent invocation **invoke**"; inside, "holocene-pm"; a barcode sticker copied from the memo by hand (`copy-barcode`); a signature box on the flap. She runs it under a small copy of Inspector Cruz's stamp, posts it through a doorbell slot marked BACK (`stamp-ring`), sticks "memo dispatched", and raises the shutter on the ledger window (`shutter-ledger-up`).
- **The beat:** The memo desk, not the dock, writes the tour's first envelope: an imperative, for one worker, carrying the copied barcode. It goes out by doorbell, so the desk checks the crew hall's ledger to learn it landed.
- **Teaches (the notebook line):** The memo desk, not the dock, writes the envelope: “invoke”, for one worker, with the copied barcode. It goes out by doorbell, so the desk reads the crew hall’s ledger to learn whether anyone took it.

**PRIYA**: *(pulls a kraft envelope from a drawer; the window label reads "invoke")* An envelope. One instruction, for one worker. Outside, “invoke”. Inside: holocene-pm, his words, the thread.

**DAMIAN**: That's the first envelope I've seen anyone write.

**PRIYA**: *(copies the barcode on by hand)* I copy the barcode on. A barcode only crosses rooms when the next writer copies it.

**PRIYA**: *(stamp, then through the doorbell slot marked BACK)* Checked, rung, gone. “Memo dispatched.”

**PRIYA**: *(raises the shutter on the ledger window)* A doorbell only says it heard. The ledger is how I find out whether anyone took it. No line, and I stop waiting and tell the sender.

- **Lightbulb:** none here. (The idempotent bulb waits for the archive in Scene 19.)
- **Where the picture breaks:** The memo desk is one service doing half a dozen jobs, and Wren is a speech-to-text model on a graphics card, reached over the web, not over the belt. "Invoke" is the express kind of envelope, for a human who is waiting; the ordinary kind says "start" (Scene 17 uses it). The ledger window is a file on the same machine, not anything on the belt. "Routed" is real: the quick desk records its decision as a post-it. Canon update owed: the bible lists only the dock's poster as a doorbell (B16); the memo desk and the memo door ring doorbells too.
- **Evidence:** `inbox_watcher.py:1502-1525,1672-1682,1926` (received, Whisper at `:8766`, transcribed; the quick desk `MEMO_CONVERSE`, live memo showed `routed`); `inbox_watcher.py:62,181,2356-2363,2398-2426,2448-2456` and `bloodbank/bin/bb-emit:60,137-143,326-329` (`--strict --kind command --type bloodbank.agent.invocation.invoke`, correlation = memo id, command id, idempotency key = uuid5 of type and correlation, single consumer, `dispatched`, ledger check); `core/validate.py:161-168,345`; `holocene/services/inbox-watcher/README.md:451` (`bloodbank-ntfy-router` pushes the `failed` fact). (verify) that `routed` is always stuck when the quick desk declines.

### SCENE 10. The Express Hatch

*The express hatch.* *(engine: `hatch`, pad clock `0:01`; bulb `workqueue`)*

- **Set:** `[crew]`. Round the back of the shaft: the back loop climbing, and in the crew hall wall, hatch doors. Two are the crew hall's (ORDINARY; EXPRESS, with a small plate: "a human is waiting"). Further along, two in the clock's brass. Two more tagged NOT OURS. A registry board on the wall.
- **Shot:** The envelope climbs the back loop. The express hatch slides open and a white-gloved hand draws it halfway in. It does not come off the belt: a red ribbon tethers it, with a tag reading IN HAND (`in-hand-ribbon`). Okafor checks it, runs a finger down the registry board (`glance-registry-board`: "holocene-pm to workstation 7"), writes one line in his ledger (`ledger-line`), and walks two post-its to the registered counter where a clerk hands back a receipt with a belt number on it (`registered-counter`).
- **The beat:** One hatch per kind of envelope; the express hatch takes it, and taken is not gone: it stays on the belt, in hand, until signed off. If it comes round twice, the ledger has its number and the same post-its are stuck again; the work is not done twice. The crew hall posts its own notes at the registered counter, with no dock involved.
- **Teaches (the notebook line):** One hatch per kind of envelope. Taken is not gone: it stays on the belt, in hand, until signed off. If it comes round twice, the ledger knows it. That is a work queue.

**OKAFOR**: Welcome to the crew hall. Express hatch, for envelopes a human is waiting on. Each kind of envelope has one hatch at most.

**DAMIAN**: You've taken it, so it's off the belt.

**OKAFOR**: *(a red ribbon tethers the envelope to the belt: IN HAND)* Taken is not gone, sir. It stays on the belt, marked in hand, until I sign it off. If I go quiet, it will be offered again.

**OKAFOR**: *(writes one line in the ledger)* If it comes round twice, my ledger has its number. I stick the same post-its again and I don't do the work twice.

**OKAFOR**: *(walks two post-its to the registered counter; a receipt with a belt number comes back)* One line in my ledger. Then two post-its at the registered counter, “turn started” and “invocation started”, and I wait for a receipt with the belt number on it.

**DAMIAN**: “Turn started.” That's what the dock wrote for me.

**OKAFOR**: Same words, different poster, different barcode. The dock had nothing to do with this one.

**OKAFOR**: *(a glance at the registry board: holocene-pm to workstation 7)* The registry board tells me which workstation is named inside. Who gets onto that board is HR’s business. Not on your rail.

- **Lightbulb:** **workqueue** (*What is a Work queue?*), at the hatch.
- **Where the picture breaks:** The crew hall is one program, and "walking to workstation 7" is a function call. The back loop's scraper sits at one day: an envelope nobody signs off is gone by tomorrow. The hatch's patience, tries and hand limit are real settings, and they stay on its spec plate, not in dialogue (they drift: the live server and the docs disagree today). Who gets onto the registry board is HR's business and not on this rail.
- **Evidence:** `bloodbank/compose/nats/streams.json:67-75` (back loop, 1 day); live `:8222/jsz` 2026-11-12 (six hatches: two gateway, two Candybar, two milkshake; interactive hatch `bloodbank-hermes-gateway-interactive`, filter `bloodbank.cmd.agent.invocation.invoke`, ack wait 180 s, max deliver 8, max ack pending 4); `hermes-gateway/.../adapter.py:366,479,565-595,1603-1613`, `contract.py:246-330,429-442,474-497`; the gateway journal `executions` row by command id.

### SCENE 11. The Workstation Phones Out

*The workstation phones out.* *(engine: `staffing`)*

- **Set:** `[staffing]`. Holly's workstation (badge, locker, placards, radio) on one side of a wall; on the other, the staffing desk next door, Mags with three phones.
- **Shot:** Holly is frozen mid-reach, like a paused film. Okafor sets the envelope's ticket on her desk and she unfreezes in the same motion (`unfreeze`). She reads, lifts a phone; the cord runs through the wall to Mags. Mags dials a number: dead air (`dial-dead-air`). She dials the next number on her list and someone picks up (`dial-answer`). Through the window behind them: out on the back loop, Okafor stamps the tethered envelope STILL WORKING (`stamp-still-working`). At the registered counter, no post-it appears (`no-postit-appears`) while Holly says why.
- **The beat:** A workstation sleeps until an envelope wakes it; its model call goes through the staffing desk to agencies across town, trying a list in order, the one named first. While it works, the crew hall stamps the envelope "still working". Progress post-its appear only when the worker says something next to a tool call, and most voice turns write none.
- **Teaches (the notebook line):** A workstation sleeps until an envelope wakes it. Its model call goes through the staffing desk, which tries the agency named, then the next on its list. Progress post-its appear only when the worker says something next to a tool call.

**HOLLY**: *(unfreezes mid-reach)* Who I am. What I remember. What I can do. Right. Somebody get me a brain.

**MAGS**: *(dials; the line is dead)* Staffing desk. The envelope names the agency it wants. I ring that one first.

**MAGS**: *(dials the next number; someone picks up)* That one hasn't been paid. I try the next number on my list. There we are. First agency that picks up.

**DAMIAN**: Is the agency in the building?

**MAGS**: Across town, love. Their answers go back to Holly, never across your belt.

**OKAFOR**: *(stamps the tethered envelope STILL WORKING)* “Still working.” Every so often, so nobody thinks I've gone quiet and offers it to someone else.

**HOLLY**: *(nothing appears at the registered counter)* When I say something next to a tool call, the hall sticks it up as “invocation progressed”. I said nothing today. Most turns I say nothing.

- **Lightbulb:** none in the sandbox set. (Catalog bulb 22, *What is a gateway?*, belongs at Mags's desk.)
- **Where the picture breaks:** "Next door" is about ownership, not place: the staffing desk runs on a server elsewhere. A fallback list can look healthy while the members nobody pays for are skipped. The workstation is only files until an envelope wakes it. The progress post-it is real but conditional, and this run writes none; Holly says so on camera, which closes the old (verify) on progress notes. The cord from Holly's locker to the library is dropped: it was never confirmed.
- **Evidence:** `hermes-gateway/README.md:395-403,498-499,611-620`; `schemas/bloodbank/agent/invocation.progressed.json`; `hook-hub/handlers.toml:93-96` (the Hermes plugin retains per turn); `inbox_watcher.py:181` (model route in the envelope); the traced run has no `progressed` note.

### SCENE 12. The Voice Booth, Early

*The voice booth, early.* *(engine: `booth1`, pad clock `0:08 · 0:17 · 0:26`)*

- **Set:** `[voxxy]`. A padded booth with a red ON AIR light, a front window with Vinnie behind it, and a slot at the foot of the door marked SCRIPTS. In the back room, Big Mo at a music stand. A shelf of labelled clips on the memo desk side of the door (the PhraseBank). The pad clock reads 0:08, then 0:17, then 0:26.
- **Shot:** Damian arrives empty-handed (the hero marker still hangs over the crew hall: the envelope is in hand there). A short typed slip slides under the door from off-screen (`slip-under-door`). Vinnie passes it back without looking. A ready-made recording slides out from the shelf and plays (`cue-clip-plays`); Priya's hand, off-screen, took it from the shelf, not from Mo. Mo never opens his mouth. Vinnie ends: "So today it's the shelf."
- **The beat:** Voxxy is not on the belt: a script slides under the door and a recording comes back. The "still on it" clips are ready-made recordings on a shelf, never a Voxxy render. Spoken progress from the worker is possible, but most voice turns write none.
- **Teaches (the notebook line):** Voxxy is not on the belt: a script slides under the door and a recording comes back. The “still on it” clips are a shelf of ready-made recordings, never a Voxxy render. Spoken progress is possible, but most turns write none.

**DAMIAN**: I've come about the manager's memo. Are you the guys?

**VINNIE**: We're the guys. You're early. We read answers out loud, and nobody's written one yet.

**VINNIE**: *(a script slides under the door)* And we don't take deliveries. No envelopes, no clips, no hatch. You slide it under the door.

**PRIYA**: *(a ready-made recording from the cue shelf plays)* “Still on it.” Off my own shelf, made ahead of time. A file copy. It never went through your window.

**DAMIAN**: Why play it at all?

**PRIYA**: Because a worker can be quiet a long while, and the car shouldn't be. If a worker writes a line next to a tool call, I can slide that under the door instead. Most turns write none.

**VINNIE**: So today it's the shelf. We'll be here when there's an answer.

- **Lightbulb:** none.
- **Where the picture breaks:** Voxxy reads one script at a time per voice, so two callers queue at the door, not on the belt. Wrapping Voxxy in Bloodbank is listed in its own README as a future idea, and nothing like it exists today. The three early clips are keep-alive clips: file copies from the PhraseBank, played by the pad and dropped while the driver records. They are announced as post-its ("memo narrated"), but no Voxxy render happens on the critical path. The staged "Still on it" is one of the real lines.
- **Evidence:** `holocene/services/inbox-watcher/README.md:995-1013` (hold cues and keep-alives, PhraseBank file copy about 1 ms); `inbox_watcher.py:340-350,4138-4241` (hold keep-alive first at 7 s after dispatch, then every 8 s, at most 3); live narrated notes at 2026-11-12T01:25:36, :45 and :54Z (pad clock 0:08, 0:17, 0:26); `inbox_watcher.py:3910-4045` (the agent's own spoken progress, never in the first 15 s). (verify) that the three live `narrated` notes are keep-alive clips and not progress renders; the 8, 17 and 26 second spacing says keep-alive.

### SCENE 13. While You Wait (side scenes)

2 camera stops.

**13a.** Side scene: the clock. *(engine: `clock`, side scene)*

- **Set:** `[clock]`. The bell on the wall, the chore chart, the planner's desk, two brass hatches onto the back loop. Labelled on screen: **SIDE SCENE, not on this errand's route**.
- **Shot:** Constance checks her pocket watch against the bell, to the second (`pocket-watch`). On the way, the camera passes the bin of confiscated alarm clocks (`point-alarm-bin`) it planted in Scene 4.
- **The beat:** The clock owns *when*. Its chores go out as envelopes through its own hatches ("invoke" for its hands, "steward" for its caretaker); one hatch per kind, one worker each. One bell, no private alarms.
- **Teaches (the notebook line):** Side scene: the clock owns when. Its chores go out as envelopes, one hatch per kind, and there is one bell and no private alarms.

**DAMIAN**: Is this on my route?

**CONSTANCE**: *(checks her pocket watch against the bell, to the second)* No. Nothing on your errand waits for a bell. I own when things happen, not what anyone asked.

**CONSTANCE**: When I ring, the planner writes an envelope for each chore due. My hands take the “invoke” ones. My caretaker takes the “steward” ones. One hatch per kind, one worker each.

**DAMIAN**: Could I set a reminder to collect the answer?

**CONSTANCE**: *(points at the bin of confiscated alarms under the dock window)* A private alarm. In this building. One bell, no private alarms. You'll find them in the bin under the dock's window.

**13b.** Side scene: the sound wing. *(engine: `soundwing`, side scene)*

- **Set:** `[soundwing]`. Three inbound doors, the secure cage, a rack of eight passes, and through the glass, grey envelopes on the back loop. Labelled on screen: **SIDE SCENE**.
- **Shot:** Gloria gestures with a pencil at the back loop (`point-grey-stack`): a stack of grey envelopes rising untouched past every hatch. When she says "Don't tell the Professor" she glances across the floor toward Haugen's belt (`glance-at-haugen`), with a half-second hold.
- **The beat:** The sound wing is a separate audio system, and it never calls Voxxy. Some of its envelopes have no hatch at all, so they ride up unsigned until the one-day scraper. It also sticks a post-it copy so the archive can find them.
- **Teaches (the notebook line):** Side scene: the sound wing never calls Voxxy. Some of its envelopes have no hatch, so they wait for the scraper; a post-it copy is stuck so the archive can find them.

**DAMIAN**: You do audio. Do you send things to Voxxy?

**GLORIA**: Never have. My wing takes recordings in through three doors, locks them in the cage first, and runs eight passes over each transcript.

**GLORIA**: *(points her pencil at the stack of grey envelopes on the back loop)* We write envelopes too. That stack. Letters to an empty room, every one. No hatch for that kind. Up they go, unsigned, until the one-day scraper.

**DAMIAN**: Isn't that what post-its are for?

**GLORIA**: *(a glance across the floor toward Haugen's belt)* We write one of those too. A copy of the envelope, so the archive can find it. Don’t tell the Professor.
*[hold 500 ms before the next line]*

- **Lightbulb:** none. (Catalog bulb 16, *Single source of truth*, belongs at the bell.)
- **Where the picture breaks:** The clock owns when, not always who: a chore can run as a service or a Hermes job. A signed list of alarms stays outside the clock, each with a named owner and reason, and the guard at the window fails open, with an audit as the backstop. The sound wing is absent on Damian's Mac; its hatchless envelopes are enrichment passes over transcripts, not speech, and have no form pad. Nothing on this errand waits for a bell.
- **Evidence:** Bible card 15 (`candybar/executor/worker.py`, `native-clock-guard`); live jsz (`candybar-executor-invoke`, `candybar-steward`); bible B11 and card 29 (`~/HeyMa/components/wax/src/wax/passes.py`, `audio.task.start` with no hatch); route research (waxd does not call Voxxy). (verify) that the sound wing sticks a post-it copy of every hatchless envelope, as Gloria says.

### SCENE 14. Signed Off

*Signed off.* *(engine: `signoff`, pad clock `1:12`)*

- **Set:** `[crew]`, the front desk and the express hatch. Pad clock 1:12.
- **Shot:** Holly hangs up, writes her answer into a book on the shelf behind her (spine: "holocene-pm, sessions"), and freezes mid-reach again. Okafor regards his own open palm like a receipt (`regard-palm`): empty. He walks two post-its to the registered counter, takes his receipts, and only then signs the envelope's flap (`stamp`). The ribbon unclips; the envelope leaves the belt into his out-tray. He glances up at the mezzanine (`glance-up-mezzanine`).
- **The beat:** The envelope is signed off after the work, and a signature means finished, not succeeded: success or failure is the post-it's last word. The answer itself is not on any post-it.
- **Teaches (the notebook line):** The hall sticks “completed” and signs the envelope off. A signature means finished with the envelope, not that it worked. The completed post-it never carries the answer.

**OKAFOR**: *(regards his own open palm, like a receipt: empty)* Holly has put her pen down. Taken was not gone. Now it is.

**OKAFOR**: *(a stamp comes down)* Two post-its at the registered counter, “invocation completed” and “turn completed”, same barcode as the first two. Then I sign the envelope off.

**DAMIAN**: Where is the answer? On the post-it?

**OKAFOR**: *(regards his own open palm, like a receipt: empty)* Done is a post-it, sir. It says finished, how long it took, which hatch. It has never once carried an answer.

**OKAFOR**: And my signature means I am finished with the envelope. Not that it went well. Read the post-it’s last word: completed, or failed.

**DAMIAN**: So who has the answer?

**OKAFOR**: *(glances up at the mezzanine)* Holly wrote it in her own session book. Somebody is on their way to read it. I believe they have been reading my ledger since the first second.

- **Lightbulb:** none in the sandbox set. (Catalog bulb 12, *Acknowledgement, and why things arrive twice*, belongs at this hatch.)
- **Where the picture breaks:** The crew hall also signs off envelopes it has closed as failed, and it re-sticks the same post-its for an envelope it already finished rather than running it twice. Reply slips are real in code but not in service: Pilot asks with `bb call` and listens on one shared reply line, matching by "came after"; Krebs would answer, and Krebs is not running. The window for return slips stays dashed and unvisited (held back from v1).
- **Evidence:** `hermes-gateway/README.md:1-14,471-529`; `schemas/bloodbank/agent/invocation.completed.json` (lane, elapsed time, detach flags; no reply text); live trace 01:26:39.716Z (pad clock 1:12); `bloodbank/cli/call.py:21,53-55`, `krebs/src/krebs/service.py:62-77`, `pilot/src/lifecycle.js:15-26`; live jsz (no Krebs consumer).

### SCENE 15. The Ledger and the Session Book

*The ledger and the session book.* *(engine: `ledger`, pad clock `1:12`)*

- **Set:** `[control]`, the memo desk. Both shutters go up. Pad clock 1:12.
- **Shot:** Priya raises the ledger shutter: through it, Okafor's ledger open at one line, "finished". She winks at the camera over it (`ledger-wink`). She raises the second shutter: Holly's session book, open at a thread headed with the memo's barcode (`open-session-book`). She copies the newest answer onto a script slip and checks when it was written against when she sent the envelope. A last line on the page is marked BACKGROUND; she tears it off and pockets it (`tear-off-line`). She runs a pencil down the answer, striking asterisks and anything a person cannot say (`clean-for-speech`), and slides it toward the booth door.
- **The beat:** The requester learns the work is done by reading the crew hall's ledger, and reads the answer from the workstation's session book. The answer never rides the belt. A BACKGROUND line is a promise, never spoken.
- **Teaches (the notebook line):** The memo desk learns the turn is done by reading the crew hall’s ledger, not by waiting for a post-it. The answer lives in the worker’s session book, never on the belt. A BACKGROUND line is a promise and is never spoken.

**PRIYA**: *(winks at the camera over the open ledger)* I did not wait for the post-it. I read Okafor’s ledger. One line for that envelope’s number: done, and how long.

**DAMIAN**: You and the ledger seem close.

**PRIYA**: It tells me the truth and it does not ask me to dinner.

**PRIYA**: *(opens a session book at a page headed with the memo's barcode)* The answer is not on the belt anywhere. It is in Holly’s session book: her newest page for this barcode, checked fresh against when I sent the envelope.

**PRIYA**: “Three steps in a row: it hears you, thinks, then speaks. Each one waits for the one before. I’ll time each step and follow up.” Twenty-six words. Under the thirty.

**PRIYA**: *(tears the BACKGROUND line off the page and pockets it)* And under it, a line that starts “BACKGROUND”. That is Holly’s note to me, not to the car. I never read it out. It is a promise, not an answer.

**PRIYA**: *(runs a pencil down the answer, striking asterisks and anything a person cannot say)* The answer I clean for the car. No asterisks, no code, nothing a person cannot say. Then it goes under the booth door.

- **Lightbulb:** none.
- **Where the picture breaks:** The ledger is a database file on the same machine, and the session book is the workstation's own database; neither is on the belt, and the archive is only the fallback when the ledger has no line. The staged answer is 26 words; the real run's was different. The BACKGROUND marker is matched in capitals only and never inside a code fence. Priya's answer is one piece because it is under about 160 letters.
- **Evidence:** `holocene/services/inbox-watcher/memo_common.py:512-545,578-650`; `inbox_watcher.py:2484-2505,2626-2640,2726-2760` (ledger by command id; `state.db` by source and chat id, freshness check); `inbox_watcher.py:527` (`split_background`); `README.md:466-492` (answer-then-background); `clean_for_speech` at `inbox_watcher.py:4503`.

### SCENE 16. First Sound

*First sound.* *(engine: `pad`, pad clock `1:14`)*

- **Set:** `[entrance]`, the memo door again. Pad clock 1:14.
- **Shot:** The pad in Damian's vest has been counting. The clock stops (`pad-clock-stops`). Reggie points at the ear on the wall (`point-ear`), and the camera follows the hose down to the loading slot, where the cup trembles. A recording comes off the reply shelf to the pad (`fetch-from-shelf`) and Big Mo's voice plays, small and tinny (`voice-from-pad`) while Reggie reads the words aloud. Two post-its go up behind him: "replied", then "played".
- **The beat:** The pad hears about new notes through an ear at the loading slot, then fetches the recording from the reply shelf. A post-it is the doorbell, the shelf is the pickup, and polling is the fallback.
- **Teaches (the notebook line):** The pad hears about new notes through an ear at the loading slot, then fetches the recording from the reply shelf. A post-it is the doorbell, the shelf is the pickup, and polling is the fallback.

**REGGIE**: *(the pad's working clock stops)* Pad’s clock stopped. One minute fourteen. First sound.

**DAMIAN**: How did it know?

**REGGIE**: *(points at the ear: a brass cup on the wall, a hose running to the loading slot)* The ear. A cup on the wall at the loading slot and a hose down to my desk. It hears every memo post-it that goes up. No clip, no notebook. It hears, or it does not.

**REGGIE**: If the hose goes quiet, I walk to the shelf every few seconds and look. Slower, but it gets there.

**REGGIE**: *(the pad fetches a recording from the reply shelf)* “Voiced”, stuck: that piece is on the reply shelf, the car can start speaking from here. A post-it is the doorbell and the shelf is the pickup. Nobody sticks sound to a post-it.

**REGGIE**: *(Big Mo's voice plays, small and tinny, from the pad)* It says: “Three steps in a row: it hears you, thinks, then speaks. Each one waits for the one before. I’ll time each step and follow up.”
*[hold 500 ms before the next line]*

**REGGIE**: “Replied”, stuck. Then your pad tells me it played it, and “played” goes up. That is the last thing anybody here can see.

- **Lightbulb:** none.
- **Where the picture breaks:** The ear is one core subscription in the upload proxy that serves a push line to the pad; it keeps no place and no notebook, so a missed note is not replayed, and polling is the fallback. Exactly one of car and phone speaks a reply; that arbiter is real and not staged here. "Replied" is the last hop the pipeline can observe, and the pad reports "played" back. A post-it never carries sound.
- **Evidence:** `holocene/services/upload-proxy/upload_proxy.py:1123-1135,1295-1350,1680-1760` (one core subscription to `bloodbank.evt.audio.memo.>`, SSE `/upload/events`, S3 fetch on a voiced or replied note, polling fallback); `inbox_watcher.py:3184-3190,3199-3295,3763-3845` (`memo.voiced`, `memo.replied`, car-or-phone claim); live trace: first sound 01:26:42Z (1:14), replied 01:26:51Z, played 01:26:56.8Z. (verify) the pad's "Working" label before it appears on the HUD.

### SCENE 17. Later

*Later.* *(engine: `followup`, pad clock `1:24, then 1:42:33`)*

- **Set:** `[crew]`. Pad clock 1:24, then a title card, then 1:42:33.
- **Shot:** A second kraft envelope climbs the back loop, this time to the ordinary hatch, with the same barcode and a different number (`copy-barcode`). Holly unfreezes (`unfreeze`) and says she remembers the first answer, because the book is the same. Title card over black: LATER (`later-card`), held a beat. Back at the front desk, Okafor regards his palm again (`regard-palm`); the ribbon is unclipped. Holly writes her page into the book (`write-session-book`).
- **The beat:** A long ask becomes a second envelope for the ordinary hatch, with the same barcode and the same thread. There is no stopwatch on that hatch, and nothing is narrated while it runs. One follow-up per memo.
- **Teaches (the notebook line):** A long ask becomes a second envelope for the ordinary hatch, with the same barcode and the same thread. There is no stopwatch on that hatch, and nothing is narrated while it runs.

**OKAFOR**: *(copies the barcode on by hand)* Second envelope for Holly. Same barcode, same thread, different number. The memo desk wrote it the moment the first answer went out.

**OKAFOR**: Kind “start”. That is the ordinary hatch, the one with no stopwatch on it. Two hours, and Holly may use them.

**HOLLY**: *(unfreezes mid-reach)* Same thread, so I remember the first answer. I promised to time each step. Back in a bit.

**OKAFOR**: *(title card over black: LATER)* No “still on it” clips for this one, the desk upstairs tells me. Nobody is holding a line.
*[hold 800 ms before the next line]*

**OKAFOR**: *(regards his own open palm, like a receipt: empty)* An hour and forty-one minutes. Completed, turn completed, signed off. Same two post-its, new numbers, same barcode.

**HOLLY**: *(writes the page into her session book)* Timed it. Listening, about a second. Thinking, most of a minute. Speaking starts two seconds after I finish. Writing it in my book.

**DAMIAN**: Do you do this for every memo?

**HOLLY**: Only when I say I will. One follow-up per memo, and then I stop.

- **Lightbulb:** none.
- **Where the picture breaks:** The follow-up envelope is written after the quick answer has been spoken, not before; the desk waits for "replied". The ordinary hatch has no wall clock but a two-hour deadline, and the live trace ran 1 h 41 m. A follow-up that fails or only hands off again is spoken as such instead of failing the memo; that branch is not staged. The staged content (timing each step) is invented; the live run's follow-up was about a deployed voice fix.
- **Evidence:** `holocene/services/inbox-watcher/README.md:466-492` (follow-up N: same thread id, `MEMO_FOLLOWUP_LANE` batch, 2 h deadline, `lane_reason=voice_followup`, `followup_of_command_id`, "<agent>, follow-up.", `MEMO_FOLLOWUP_MAX=1`); live trace: dispatched 01:26:52Z (pad clock 1:24), invocation `fc7b326e` completed 03:07:55Z.

### SCENE 18. The Voice Booth, Late

*The voice booth, late.* *(engine: `booth2`, pad clock `1:42:33 · 1:42:37 · 1:42:42`)*

- **Set:** `[voxxy]`, the second visit. Pad clock 1:42:33, 1:42:37, 1:42:42.
- **Shot:** A long script slides under the door. Priya takes scissors to it at the full stops (`cut-at-full-stops`): three slips, the first shortest. Vinnie points through the window at Mo, alone at his music stand (`point-at-mo`); Mo holds one hand up (`mo-lock`). He reads each slip in turn (`mo-reads`); each recording slides out under the door and Priya racks it on the reply shelf, a "voiced" post-it going up each time (`voiced-postit`). A sand timer on the rack runs an hour. Vinnie ends on the rack.
- **The beat:** The memo desk cleans the answer and cuts it into pieces; each piece goes under the booth door on its own. Voxxy does no cutting, reads one script at a time, and keeps each recording for an hour. (Pays off Odette's line in Scene 4.)
- **Teaches (the notebook line):** The memo desk cleans the answer and cuts it into pieces, and each piece goes under the booth door on its own. Voxxy does no cutting, reads one script at a time, and keeps each recording for an hour.

**PRIYA**: *(scissors at the full stops: the answer becomes three slips, the first shortest)* Holly’s follow-up, cleaned for the car. It is longer than a hundred and sixty letters, so I cut it at the full stops. Short piece first, so you hear something sooner. Longer ones after.

**VINNIE**: *(a script slides under the door)* We do not cut. We read what is slid under the door, whole. She does the cutting.

**VINNIE**: *(points through the window at Mo, alone at his music stand)* And one at a time. Mo has one chest.

**MO**: *(holds one hand up: the lock)* One. Voice. One. At. A. Time.

**VINNIE**: Piece two waits at the door until piece one is done. Waiters queue.

**MO**: *(reads the slip into the mic; a recording slides out under the door)* “Holly, follow-up. I timed each step.”
*[hold 400 ms before the next line]*

**MO**: *(reads the slip into the mic; a recording slides out under the door)* “Listening takes about a second. Thinking takes most of a minute, and that is the slow part.”
*[hold 400 ms before the next line]*

**MO**: *(reads the slip into the mic; a recording slides out under the door)* “Speaking starts two seconds after the thinking ends. If you want it faster, shorten the thinking, not the talking.”

**PRIYA**: *(a "voiced" post-it goes up as each recording reaches the reply shelf)* Each piece goes on the reply shelf, with a “voiced” post-it, and the pad plays them as they land.

**VINNIE**: We keep each recording an hour. After that it is gone. She takes her copy before then.

- **Lightbulb:** none.
- **Where the picture breaks:** Piece sizes grow (about 110, then 170, then 300 letters), so the first sound arrives sooner than a single long render would. One piece at a time is the GPU lock under the voice engine: two concurrent renders each take twice as long, and the desk's own gate also holds one render at a time, so a quick turn queued behind a three-piece follow-up starts after the current piece, not all three. Voxxy hands back an address that the desk fetches the file from; the desk then uploads each piece to the reply shelf. The follow-up is spoken as "Holly, follow-up". The pad plays every reply unit of a memo it sent.
- **Evidence:** `inbox_watcher.py:289-291` (`MEMO_REPLY_CHUNKS`, min 160 letters, limits 110,170,300), `4503` (`clean_for_speech`), `4566` (`split_for_speech`), `4628-4665` (`TtsGate`: one vox render at a time, replies before narration, FIFO within a priority); `inbox_watcher.py:3078-3135,4764-4795`; `~/code/voxxy/app/main.py:628-657`; `~/code/voxxy/compose.yml` (`VOX_AUDIO_TTL_SECONDS` 3600, `VOX_ENGINES`); live voiced notes 03:08:01, :05 and :10Z (chunk 1 of 3 took 3.86 s to render).

### SCENE 19. Bring It Back

2 camera stops.

**19a.** One barcode, forty notes. *(engine: `barcode`, bulb `idempotent`)*

- **Set:** `[archive]`. The archive's racks and its lookup counter, Mr. Fitch on his rolling ladder.
- **Shot:** Fitch pulls the drawer for the barcode (`pull-drawer`). Down the racks, slots light one after another, about forty, and the camera rides the ladder past them like a train past stations. A glance up at the control room window (`glance-mezzanine`): the same trick, off the same barcode. For the what-if, the picture goes desaturated again (`what-if-open`), a finished envelope's post-its stuck a second time with the same Note IDs; Fitch files each once; back to colour on `what-if-close`, where two envelopes are two different sets of notes.
- **The beat:** The archive filed every note of the run, and one barcode, copied by every writer, rebuilds the whole errand: about forty notes, fourteen kinds, two envelopes. A repeat of the same Note ID is filed once. Two envelopes are two jobs, not a repeat. That is idempotent. Damian's Codex question wears a different barcode, because it was a different system.
- **Teaches (the notebook line):** The archive can rebuild a whole run from one barcode: about forty notes, fourteen kinds, two envelopes. A repeat of the same Note ID is filed once. Two envelopes are two jobs, not a repeat. That is idempotent.

**FITCH**: *(pulls the drawer for the barcode; slots light down the racks)* Barcode, please. Ah. The memo tape. About forty notes, one barcode.

**FITCH**: Fourteen kinds. Uploaded, received, transcribed, routed, dispatched. The hall’s pair, turn started and invocation started. Three clips narrated. Completed. Voiced, replied, played.

**FITCH**: *(a glance up at the control room window)* Each one says what “came after” it. Follow them and the whole run reads like a diary. The control room does the same trick, off the same barcode.

**DAMIAN**: Is my Codex question in there?

**FITCH**: That wears a different barcode, from a different door. Nothing joins the two but you.

**DAMIAN**: What if one of these came twice?

**FITCH**: *(the picture desaturates: a what-if insert begins)* A what-if, because it did not happen today. Say the hall replays a finished envelope’s post-its, same Note IDs. I file each one once and move on.

**FITCH**: *(back to colour, the what-if over)* Two envelopes is not that. Two envelopes is two jobs, with their own Note IDs. Both filed. Not twice.

**19b.** Back at the entrance. *(engine: `closing`, pad clock `1:42:42`)*

- **Set:** `[entrance]`. Abernathy's spot, where he said he would be waiting. Pad clock 1:42:42.
- **Shot:** Damian hands over the pad (`hand-pad`). Abernathy plays the quick answer and clicks his stopwatch (`stopwatch-click`) at 1:14. The long one has been waiting on the pad since lunch. A beat of silence, then the third check. On the last line he clicks the stopwatch again and the HUD freezes on the pad clock.
- **The beat:** The errand ends where it began: a question went in by one door and an answer came back to the pad. The third check is the reader's: name one post-it and one envelope from your own app.
- **Teaches (the notebook line):** The errand ends where it began: a question went in by one door and an answer came back to the pad. The third check is yours: name one post-it and one envelope from your own app.

**ABERNATHY**: *(clicks the stopwatch on his lanyard)* Well?

**DAMIAN**: *(hands Abernathy the pad)* Their result.

**ABERNATHY**: “Three steps in a row.” That is the quick one. First sound at one minute fourteen. I have waited longer for the lift.

**DAMIAN**: The long one came an hour and forty-two minutes in.

**ABERNATHY**: I went for lunch. It was waiting on the pad when I came back. That is the idea.

**ABERNATHY**: You walked the building. Now do it in your own shop. Name me one post-it it would stick, and one envelope it would write.

**DAMIAN**: Now?

**ABERNATHY**: *(clicks the stopwatch on his lanyard)* Take your time. No, don’t. Clock’s running.

- **Lightbulb:** **idempotent** (*What does Idempotent mean?*), at the racks in 19a.
- **Where the picture breaks:** The archive is a reader that tore off copies; it is not the belt, and it makes no promise about how long it keeps them. The readback works only because every writer on this errand copied the memo's barcode. The control room upstairs rebuilds the same run from the same barcode. The dock's notes, like Damian's, rely on this clerk alone to catch a repeat. The traced run has no duplicate Note IDs, so the repeat is a labelled what-if. The "about forty" and "fourteen kinds" are the traced run's counts, not constants.
- **Evidence:** `candystore/db.py` (`INSERT ... ON CONFLICT (id) DO NOTHING`; durable consumer `candystore-events`, ack wait 30 s); `memo_common.py:485-500,526-575`; live `GET :8683/events?correlationid=bdd7a80d-11a6-597d-860f-96a943bba9da` (about 40 notes, 14 kinds, 0 duplicate ids; two commands `af569a5c` and `fc7b326e`); Holocene `/voice` and `memo:trace` rebuild from the same barcode. (verify) that the crew hall replays a finished envelope's post-its with the same Note IDs before the what-if line stays as spoken.

---

## The divergence ledger [P]

Every place Jarad's sketch and the real route differ, and how the script turns each into story.

| Jarad's sketch | What the code does | Where the script handles it |
|---|---|---|
| The hook hub packages the prompt into a parcel in a Bloodbank event. | The dock *unpacks*: a vendor's raw hook (the parcel) goes in, one house post-it comes out, packing slip on the back. | Scene 5a: "Parcels in, one house post-it out." |
| Then it's put in its envelope. | The dock writes no envelopes. Envelope means command, and nothing at the dock writes a command. | Scene 7: "Nobody at the dock writes envelopes." |
| The prompt rides to Voxxy. | A typed prompt only ever becomes a post-it ("turn started" with the question on it). It cannot reach Voxxy by itself. | Leg A ends at Scene 7; Leg B starts at a different door (Scene 8), and Fitch says the two barcodes never meet (Scene 19a). |
| The belt carries it round to visit every component. | The belt keeps; readers come to it and tear off copies, and one hatch pulls each envelope. | Scene 6a: "Nothing on this belt has moved an inch sideways in its life. It's sediment."; the rail is the visitor's route, not the note's. |
| The guys down in Voxxy process the message. | Voxxy is not on the belt: no hatch, no clip. A workstation answers; Voxxy gives the answer a voice over a plain API call. | Scene 8 ("Voxxy reads answers out loud"), Scene 12 ("We don't take deliveries"). |
| Take their result and bring it back. | No result rides the belt. The memo desk reads the crew hall's ledger and the workstation's session book; the audio goes via the reply shelf and a push to the pad. | Scenes 14, 15, 16, 18, 19b: the result comes back as a recording on the pad. |
| (implied) A reply comes back on the bus. | Reply slips exist in code only for Pilot and Krebs (not running) and the n8n trigger (no live use). This errand reports done with a post-it and a shelf. | Scene 14 ("done is a post-it") and the dashed return-slip window, held back from v1. |
| (research suggestion) the sound wing as a route to Voxxy. | The sound wing never calls Voxxy, and its hatchless envelopes are transcript passes, not speech. | Scene 13b. |
| A tour that visits every component on one request. | Not every room sits on any one request's route. | Scene 1 ("It has rooms yours hasn't got yet"), Scene 13 side scenes, and the `OFF_ROUTE` plaque and end card. |
| (draft 1) One errand, one envelope, one answer. | The live run used two envelopes: an express `invoke` for a quick answer, then a `start` follow-up an hour and forty-two minutes later (the `BACKGROUND:` hand-off). | Scenes 9b, 15, 17, 18. |
| (draft 1) The "still on it" voice is Voxxy at work. | Keep-alive clips are file copies from a shelf; nothing is rendered for them. | Scene 12. |
| (draft 1) Fitch files the repeats from Damian's run once. | The traced run has no duplicate Note IDs. Two envelopes are two jobs. | Scene 19a: a labelled what-if, then "two envelopes is two jobs, not twice". |

## Canon updates owed [P]

Before any of this prints, the bible needs these (one object, one meaning: new objects go in the table first).

1. **New world objects:** the **tape** (a recorded voice memo, between the pad and the Whisper booth); the **upload shelf** with its bins (inbox, status, progress, replies); the **ledger** (the crew hall's execution journal); the **session book** (a workstation's own record of its turns); the **ear at the loading slot** (one core subscription that hears memo post-its for the pad, keeps no place and no notebook, with shelf polling as the fallback); the **cue shelf** (ready-made keep-alive recordings, file copies, never a Voxxy render); the **memo door**, the **memo desk** and the **Whisper booth** as places. The tape must never be drawn as a parcel.
2. **B16 and card 9 (the regulars):** the memo desk and the memo door are doorbell posters too, not only the dock's poster. The memo desk compensates by reading the crew hall's ledger; the ear is the one reader of those doorbells that is not a clip.
3. **Card 31 (the voice booth)** grows from an extra to a supporting part, and gets a correction: callers are the memo desk and the Hermes voice plugin, over plain HTTP; it reads one script at a time per engine and keeps recordings for an hour. **Chunking is the memo desk's job** (`clean_for_speech`, `split_for_speech`), not Voxxy's: card 31 must not say Voxxy cuts replies.
4. **The "memo narrated" post-it** covers keep-alive clips as well as the worker's spoken progress. Say so where the bible lists post-it kinds.
5. **Doc drift:** `bloodbank/cli/call.py`'s docstring says reply lines are "correlation-specific"; the code listens on one fixed line, so the bible's held-back paragraph is right. Live, the batch hatch's hand limit is 68 and the express hatch's is 4, while the gateway docs say 4 and 2. No hand limit goes in a line.

## Open (verify) before shipping [P]

- Scene 4: that the archive's card is handed out when a session opens (`handlers.toml`), as Fenwick says.
- Scene 9: that `routed` is stuck whenever the quick desk declines a memo.
- Scene 12: that the three live `narrated` notes (pad clock 0:08, 0:17, 0:26) are keep-alive clips and not progress renders.
- Scene 13b: that the sound wing sticks a post-it copy of each hatchless envelope.
- Scene 16: the pad's own wording on its working clock, before it goes on the HUD.
- Scene 19a: that the crew hall replays a finished envelope's post-its with the same Note IDs (the what-if). If it does not, replace the what-if with a plain redelivery of an unsigned post-it from the belt (the archive's 30-second signature wait).

**Closed by draft 2:** progress post-its (Holly says nothing and says why); the Holly-locker-to-library cord (dropped); the rules cabinet's clips on a memo run (the cabinet is one pan in Scene 6b with its pick list called an example); the n8n reply path (dropped with the held-back return-slip window).

## Notes for the engineer [P]

- **Sets used:** `entrance`, `bays`, `courier`, `library`, `dock`, `labeldesk`, `belt`, `cataloguer`, `control` (as the memo desk), `crew`, `staffing`, `voxxy`, `clock`, `soundwing`, `archive`. All 15 already resolve in `sets.ts`; no new set id is required. The optional one is `memodesk`, when the art pass reaches it.
- **Props to add to existing sets** (what the script now needs on screen): the **ear** (brass cup and hose) at the entrance, plus the upload shelf with four bins and the reply shelf; the **cue shelf** at the voice booth door; a **registry board** and an IN HAND ribbon at the crew hall; the **bin of confiscated alarm clocks** under the dock window; the **lobby plaque** with ten dashed rooms (`OFF_ROUTE`); Wren's silent typewriter at the memo desk; a **session book shelf** behind Holly; a sand-timer rack at the booth.
- **Engine tasks, in order of value:** (1) `END_CARD` and `OFF_ROUTE` on the end card (done in `TourHud.tsx`: headline, ask, collapsed notebook, collapsed off-route list); (2) `beat.present` in the cast list (done in `TourWorld.tsx`); (3) the `split` HUD corner for the pad's clock; (4) a `side` ribbon on the two side scenes; (5) play `cue` and `hold` when the animation pass lands; (6) Damian's oversized vest (the oversized head is already removed).
- Hero forms: the `slip` form is never used, because reply slips are held back. The tape uses `recording`.
- Beats are one camera stop each; scenes with two stops are two beats in `script.ts`. 19 scenes, 24 stops, 162 lines, 73 cues.
- Scene 4 is the one stop where the hero is somewhere else (the parcel waits at the dock window while the camera visits the library), and Scenes 11, 12 and 13 keep the envelope's marker hanging over the crew hall while the camera is elsewhere.
- `script.ts` is self-contained: it imports nothing, and `cd sandbox && npx tsc --noEmit -p .` passes.
