# The Warehouse: story bible

Status: **revision 1 for Jarad**, 2026-11-11. Initiative I-10, The Manual. Supersedes `warehouse-bible.draft.md`, folding in four reviews (architect accuracy against code and the live NATS server, veteran engineer, vibe coder, theme cohesion). This is a series bible in the TV sense: one world, its canon objects, its cast, its rules, so every page and every lightbulb is written inside the same world.

- **Creative director: Jarad.** He is reworking `books/book-01/page-01.html` by hand and will bring Damian's in-person feedback. Nothing here overrides that.
- **Provenance marks.** **[J]** = Jarad's own words, from his 2026-11-11 direction (recorded in `feedback/LOG.md` FB-001). **[P]** = a proposal from this bible. A [P] is never a decision. Strike, rename or redraw any of it.
- **Ground truth:** [`research/platform-map.md`](../research/platform-map.md), [`scale-meter.md`](../scale-meter.md), [`research/damian-reality.md`](../research/damian-reality.md), plus code and the live big-chungus NATS server, read 2026-11-11. **Code wins.** Where those files are now stale, section 9.4 lists it.
- **Companion pages:** [`tone.md`](tone.md) (the tone guide, governs every page and bulb), [`../lightbulbs/README.md`](../lightbulbs/README.md) (the bulb catalog), [`../lightbulbs/normalization.md`](../lightbulbs/normalization.md) (the first finished modal).
- **(verify)** marks a claim not yet closed against code or a live box. Close it before a page prints it.

---

## 1. The premise in five sentences

1. Damian sits at his desk, asks Codex a question and presses Enter. [J]
2. Codex sends the question to its own model by its own road, and a copy of that moment is packed into a cardboard parcel, labelled in Codex's own words, which a courier carries along the conveyor to the hook-hub dock. [J for the parcel and the conveyor to hook-hub; P for the road and the courier]
3. At the dock the parcel is opened, the news is copied onto one house post-it, and an employee sticks the post-it onto the tall, two-sided belt that turns slowly in the middle of the floor. [J]
4. Anyone who cares about that kind of news tears off a copy, and the original stays on the belt [J]. If the news means work, one of those readers writes an envelope and sticks it on the back of the belt, for the one worker who will do it. [J for the envelope going to one; P for who writes it and where it goes]
5. Each book follows one parcel, note or envelope a little further through the building, and wherever a lightbulb bobs beside a station, clicking it teaches the engineering idea that station is built on. [J, with the per-book route P]

**The warehouse is beside the road, never on it.** [P] Codex's answer comes from Codex's own model, outside our fence. The warehouse is where everyone else finds out the moment happened, and the dock's window is the one place where it can hand Codex a briefing first (section 2, Briefing card). Your actual question is written on the post-it, so anyone who tears off a copy can read it (`clients/codex.py`: `turn.started` data carries `prompt_text`; check each vendor before printing it for one).

---

## 2. The canon objects

**One object, one meaning.** A page that needs a new meaning gets a new object, added to this table first. [J principle; table P] Rows tagged [P] are proposals until Jarad keeps them.

| Object | Means (real thing) | Look | Rules that never bend | Tag |
|---|---|---|---|---|
| **Parcel** (cardboard box) | One **raw hook payload** from one agent CLI, in that CLI's own dialect. | Brown box. Each **vendor** has its own box shape, tape stripe and handwritten label: Claude, Codex and Kimi all write `UserPromptSubmit`, Copilot writes `userPromptSubmitted`, Gemini `BeforeAgent`, Hermes `pre_llm_call`, opencode `chat.message`. No logos, only a colour stripe and a small name. | A parcel never goes on the belt. It exists only between a vendor's bay and the dock. Parcels go in, post-its come out. | J (box, travel to hook-hub), P (styles) |
| **Post-it** | An **event**: one fact that already happened, headline always in past tense. Lives on the front belt (`BLOODBANK_EVENTS`). | Yellow note, drawn as a **thick pad of identical sheets**. At L1 the face shows only the headline ("turn started"), a domain icon (speech bubble = conversation, ticket = repo, mic = audio, clock = cron, robot = agent) and the small **"from" corner**. Note ID, barcode and belt number appear from L2 up. The vendor's original packing slip is stapled to the back. | Unaddressed: nobody owns it. **Tearing off a copy leaves the note on the belt**: every reader tears off the top sheet and the same note still shows. Reading never removes it. Only age does (7 days). Never an order, never a to-do. | J (post-it, fan-out, copy remains), P (pad, corners) |
| **Envelope** | A **command**: an instruction for one worker, written as an imperative ("start", "invoke"). Lives on the back belt (`BLOODBANK_COMMANDS`). | Kraft envelope with a window, addressed to a kind of work (the label), the worker named inside, a signature box on the flap, and a **safe-to-repeat code** printed under the flap. | **At most one hatch can reach each kind of envelope.** It stays on the belt, marked "in hand", while it is worked. It leaves when the worker **signs it off** or **tears it up**, not when it is picked up, and the 1-day scraper takes it if neither happens. A signature means "I'm finished with this envelope", never "it worked": whether it worked is written on a post-it (started, completed, failed). Every envelope carries a safe-to-repeat code because the same envelope can come round twice. | J (envelope, goes to one), P (signature, code, tear up) |
| **Briefing card** | The **answer to a synchronous hook**: context hook-hub hands straight back to the CLI (`additionalContext`), for example a `hindsight-recall` result. | A printed card passed out through the dock's **driver's window** into the courier's hand. | **Never goes on the belt.** It goes back the way the parcel came, before the vendor carries on. If no card is ready in time, the courier leaves without one. | P (the code's own word: handler `hindsight-briefing`) |
| **Note ID** | The note's own **id** (the CloudEvents `id`). | A number printed in the top corner by whoever writes the note. | Unique to one note. **Never changes**, even when the note is stuck again or replayed. Copies of one note share it, two different notes never do. Every "safe to do twice" check in the building keys on it (the archive: `ON CONFLICT (id) DO NOTHING`, `candystore/db.py`). | P |
| **Barcode** and the **"came after" line** | The **correlation id** (`correlationid`) and the **causation id** (`causationid`). | A barcode sticker along the bottom, plus a small "came after #…" line. | **One barcode per conversation**, made from the vendor's own session number when the session opens (`clients/base.py` `get_correlation_id`). Every note from that conversation wears it. "Came after" names the note that led to this one; for a vendor's notes that is the note just before it in the same conversation (`core/session.py`). A barcode crosses rooms only when the next writer copies it. **Never a dedupe key.** | P |
| **Belt number** | The **stream sequence**. | A small number the loading point stamps as a note goes on. | Stamped by the belt, never by a writer. It counts arrivals, nothing else. | P |
| **Clip** | A **durable consumer**: a reader the belt remembers. | A coloured binder clip with a name tag, clamped on the belt, riding up with the notes. | **The clip lives on the belt, not in a reader's hand.** It marks the last point where everything above it is signed for. A reader may hold a handful of copies unsigned at once (the tag says how many); if it goes home, those come again. One clip per pick list; a reader may own several. | P (v0 bookmark flag, re-skinned) |
| **Visitor's pass** and **notebook** | An **ephemeral consumer** whose reader keeps its own checkpoint (Holocene). | A paper pass from the window and a pocket notebook. | The reader writes its own place in its notebook. Each visit it gets a fresh pass that starts at that number, never says "got it", and the pass is void when it leaves. The belt forgets it; the notebook remembers. | P |
| **Pick list** | A consumer's **filter subjects**. | A short list on the clip's tag. | The clip stops only at notes whose label is on the list. The rest slide past. | P |
| **Job card** | One **handler** inside hook-hub (about 35, `handlers.toml`). | Laminated card on a hook above the dock bench, with a stopwatch showing its time limit. | Detail level 3 only. | P |
| **Form pad** | A **schema** (`bloodbank/schemas/`). | Pre-printed tear-off pad, one per kind of note. | A note **should** be written on its form. The careful desks check; the belt does not. | P |
| **House dictionary** | The **allowlist** of legal words (`ALLOWED_DOMAINS`, entities and actions in `agent-hooks/core/validate.py`). | A thick book chained to the label desk. (Warehouses call this the item master.) | A label using a word not in the book is refused at the desk ("shape-valid is not contract-valid"). | P |
| **Lightbulb** | One **software engineering concept**, taught in a modal. | A small bulb bobbing up and down beside a station. Click it and a themed card opens, titled "What is X?". | Every bulb sits at the station whose behaviour *is* the concept. The picture comes first, the real term is named once, and the card says where else in the building you will meet it. | J |

**Held back from v1** [P]. Real, but rare or not built. Draw none of these until a page needs one.

- **Confirmation stub** (a reply, `bloodbank.rpy.*`): the stub is called out as it goes onto the back belt. Every asker waiting at the window hears it, and only the one whose ticket number matches keeps it, then has Pilot check its numbered seal (`bloodbank/cli/call.py`: one shared reply subject, matched by `causationid`; the HMAC check happens in Pilot). Nobody signs the copy on the belt, so it rides until the 1-day scraper. Most work today reports "done" with a post-it instead.
- **REPLAY tag**: a note stuck again later, wearing an orange REPLAY tag and keeping its original Note ID and barcode (`streams.json` replay posture). The tooling is planned: `bb replay` is a stub today (V3-007).
- **Exceptions desk** (dead-letter streams): drawn dashed, because it is planned (V3-007), not built.

**The verbs** [P]. They carry the meaning, so they never change: a poster **sticks** a note on; a reader **tears off a copy**; a worker **signs off** an envelope, stamps it **"still working"**, **hands it back** with a "try again in a bit" label, or **tears it up** (refused for good: malformed, or addressed to a desk that does not exist); the scraper **scrapes**; the archive **files**; a courier **waits at the window** for a briefing card. Never "peel" (peeling removes a note), never "deliver" a post-it.

**Banned objects** [P]: a parcel on the belt; a post-it with an address; a post-it as a to-do; a sticky note anywhere off the belt (the ticket board uses white printed cards); an envelope with no signature box; a clip in a hand (notebooks are fine); a note without a Note ID; a belt number written by a writer; a face on a note, envelope or parcel (faces go on people); a bulb with no station.

---

## 3. The belt (the bus), worked out precisely

Jarad's picture [J]: a long vertical, two-sided conveyor belt that never stops turning, with post-its and envelopes stuck all over it. After the dock, every note heads to the belt, and an employee sticks it on.

### 3.1 The proposal in one picture

The belt stands in a tall **glass shaft** in the middle of the floor, and holds **two loops mounted back to back**. [P] It is called **the belt** on every page, never "the tower": supply chains use "control tower" for a room that watches, and this belt watches nothing.

- **Front belt, the post-it face** = `BLOODBANK_EVENTS` (subjects `bloodbank.evt.>`, retention `limits`, `max_age` 7d, `discard` old, `max_msgs` and `max_bytes` unlimited). It faces the open floor.
- **Back belt, the envelope face** = `BLOODBANK_COMMANDS` (subjects `bloodbank.cmd.>` and `bloodbank.rpy.>`, retention `workqueue`, `max_age` 1d). It faces the crew hall.
- **Glass on both sides,** so from the floor you see yellow and kraft across the belt together, which keeps Jarad's "all over" picture while each loop holds one kind of note. [P]
- **A day ruler** runs up the shaft's side: *Today* at the loading point, *1 day* at the back scraper, *7 days* at the front scraper. Height reads as age with no motion needed. [P]
- **The return legs** inside each loop are drawn empty under a "no recirculation" sign: nothing comes round again. [P]
- **A small green sister belt** in a corner = `GIB_EVENTS` (`gib.evt.>`, 30 days). It belongs to Green in Between, Jarad's pool game, not to 33GOD, and nothing in 33GOD reads it (0 consumers live). It is in the belt's own blueprint (`streams.json`), so every building that follows the blueprint has one, empty or not, Damian's included. Keep it off story pages; one line on the L3 spec plate is enough. [P]
- The whole belt is **one NATS JetStream server** (container `bloodbank-nats`). One belt per building.

**Why two loops and not one belt with two sides:** a single loop would carry its front over the top and down its back, so a post-it would arrive on the envelope face. That teaches that events become commands by waiting. Two loops keep each face's rules separate, which is exactly what two streams are. From outside it is still Jarad's two-sided belt: "inside it's two loops, so nothing on the front ever wraps round to the back." [P]

### 3.2 Belt physics (every behaviour is a JetStream behaviour)

Live values read from the big-chungus server (`:8222/jsz`) on 2026-11-11.

| # | What the belt does | The real behaviour | Source |
|---|---|---|---|
| B1 | **The bottom is "now".** Posters stick notes on at the loading point, which stamps each with the next belt number. | Publish appends to the stream; the server assigns the sequence. | JetStream |
| B2 | **The belt creeps upward at the speed of the clock, always.** Height is age. It never speeds up and waits for nobody. It does not deliver anything: it is a noticeboard that slowly scrolls up, and everyone comes to it. | Retention is by age; a stream holds messages whether or not anyone reads them. | `streams.json` |
| B3 | **The scrapers.** A bar at the 7-day mark on the front belt takes whatever reaches it, read or not. The back belt's scraper sits at the 1-day mark. | `max_age` 7d / 1d with `discard: old`; no count or size limit, so **only age** scrapes a post-it. | `streams.json`, live |
| B4 | **The sorter at the loading point** reads one word on the outside label: `evt` goes to the front, `cmd` and `rpy` to the back. It never opens the note. (Warehouses call this sortation.) | Subject-based stream binding; the kind marker exists "so NATS can route without deserializing". Readers still trust the note's own `kind` field. | `docs/event-naming.md` §3 |
| B5 | **The belt does not proofread.** It takes any note whose label fits a loop. Checks happen at the desks where notes are written, when they happen at all. Live exhibit: the cataloguer's runner sticks session-summary notes that never pass the label desk, so they wear no barcode, no form and no "from" corner (B18). | NATS does no schema validation. `assert_contract` runs only in some publishers. | `validate.py:1026`; live `bloodbank.evt.report.session.completed`, `type com.dapr.event.sent` |
| B6 | **Clips live on the belt.** A reader the belt remembers keeps its clip there while it is away. A reader that keeps its own place uses a notebook and a visitor's pass instead (the control room). | Durable consumer state is in the server. Holocene uses an ephemeral ordered consumer with `ack none` and its own checkpoint. | live jsz; `holocene/packages/bloodbank-client/src/index.ts` |
| B7 | **Pick lists.** A clip can stop only at certain notes, such as "ticket created". One clip per pick list; one reader may own several clips. | Consumer filter subjects (Ticket Grooming filters `bloodbank.evt.repo.task.created`; one n8n workflow owns two durables). | live jsz |
| B8 | **A new reader's first day.** Its clip starts at the top (the oldest note still there), at the bottom (only what arrives from now), or at a marked time or number. Never "from the beginning of time". Back-belt hatches always start at the top: they see every envelope still unsigned. | `deliverPolicy` all (archive), new (cataloguer), by start time or sequence (artifact clerk, control room). Work-queue streams reject `DeliverPolicy.NEW`. | `pubsub.yaml`, `enricher-pubsub.yaml`, `candybar/executor/role.py` |
| B9 | **Tear off, then sign.** A reader tears off a copy and signs for it when it has finished with it. It may hold a handful unsigned at once (the cataloguer allows 32). No signature in time and the same note is offered to that reader again; if the reader restarts, the unsigned ones come again. | Explicit ack, `ackWait` (archive 30 s, cataloguer 300 s), `maxAckPending`. Redelivery means a reader can see one note twice. | the two pubsub yamls |
| B10 | **Falling behind.** A reader that is behind works down toward now while the belt carries its unread notes up toward the scraper. If it reads slower than notes arrive, its clip rides up until the scraper takes notes it never saw; they are gone for it. | Messages removed by `max_age` are gone for every consumer. Forbidden: "any listener can catch up". | `streams.json`; grammar v0 §9 |
| B11 | **At most one hatch per kind of envelope.** A worker takes one and it stays on the belt marked "in hand". An envelope **nobody has a hatch for** waits unsigned until the 1-day scraper. Live: 130 `audio.task.start` envelopes from the sound wing wait with no hatch at all, and Damian's back belt has no hatches. | Work-queue streams refuse overlapping consumers; a message matching no consumer just ages out. | live stream subjects; `~/HeyMa/components/wax/src/wax/passes.py` |
| B12 | **Sign off, stamp, hand back, tear up.** The worker signs off when it is finished with the envelope. While it works it stamps "still working" now and then, which resets the timer. It can hand the envelope back with "try again in a bit", or tear it up for good. No signature or stamp in time and it is offered again. **A signature is not a success stamp:** the crew hall signs off an envelope it has closed as failed, and the clock signs off chores it skipped. | `ack` after the work, `in_progress()`, `nak(delay)`, `term()`, `ack_wait` redelivery. | `hermes-gateway/.../adapter.py` (`_not_run`, `term`), `candybar/executor/worker.py` |
| B13 | **Tries.** Some hatches count: the crew hall allows 5 tries, or 8 at its express hatch. The clock's hatches never give up, so the 1-day scraper is their only limit. When the crew hall knows a turn never ran, it closes the envelope with a "failed" post-it. Otherwise, after the last try the envelope just stops being offered and waits for the scraper. **No lost-and-found bin on the belt yet.** | `max_deliver` 5 and 8 (Hermes lanes), -1 (Candybar); dead-letter streams are V3-007. | live jsz; `adapter.py` `_last_delivery`; `streams.json` |
| B14 | **One hand at a time is not done once.** An envelope can come round twice if its worker goes quiet, so every envelope carries a safe-to-repeat code and careful workers keep a ledger: the clock's hands look the code up and never run a chore twice, and the crew hall re-sticks the same post-its for an envelope it already finished. | At-least-once delivery; `idempotency_key` is required on every command. "Effectively-once execution rests on the registry, not the bus." | `validate.py` `REQUIRED_COMMAND_FIELDS`; `candybar/executor/worker.py` docstring |
| B15 | **The duplicate guard.** Some posters also print the Note ID on the back. Within **2 minutes**, the loading point refuses a second note with the same ID. The dock's own poster prints none, so its notes rely on the archive's check alone. | `Nats-Msg-Id` dedupe inside `duplicate_window` = 120 s on all three streams. Hook-hub's agent notes are a plain PUB with no headers. | live jsz; `nats_publish.py` |
| B16 | **Doorbell or registered.** The dock's poster rings, hears "come in", drops the note through the slot and leaves: the answer means the belt heard it, not that the note is on the belt, and if the door is shut the note is dropped with no retry. The clock's and the crew hall's posters, and the dock's own receipt clerk, wait at the counter for a **receipt with the belt number on it**, and try again if none comes. | Core PUB + PING/PONG ("a PONG is transport progress, never evidence that JetStream stored an event") versus JetStream PubAck. | `agent-hooks/core/nats_publish.py`, `core/publisher.py`; `hook-hub/observations.py`; `candybar/bus.py`; `adapter.py` |
| B17 | **Order is arrival.** Notes sit in the order they arrived, which is not always the order things happened: a re-stuck note arrives late under its old Note ID. Within one conversation, the dock keeps them in order. | Stream order = publish order; hook-hub serializes the publisher per session. | `hub.py` session lock |
| B18 | **Anyone in the building can stick a note.** There is no lock on the loading point. The regulars are listed on the posters' card (section 4, card 9). | No publish permissions on the local server. | live server config (verify per box) |

### 3.3 Where readers stand

- **Clips and the day ruler** [P]: on story pages, show how far behind a reader is by how far its clip sits from the loading point on the day ruler. That is enough until Book 6.
- **Picking lifts** (L2 and up, Book 6) [P]: each reader has an order-picker lift on a rail beside the front belt. Its **height shows how old the note it is working on is**, and **a counter on the lift shows how many notes are still below it.** Engineers watch both (lag in time, lag in count). A burst packs a thousand notes into a hand's width, so height alone is not a count.
- **Rooms that never leave their room** (the archive, the cataloguer) send a **runner** to the belt for them (card 11).
- **The control room** reads from a visitor's window with its pass and notebook (B6).
- **The back belt has no lifts.** It has **hatches** into the crew hall and the clock, one per kind of envelope (B11). Count them: the crew hall has two (ordinary, and an **express hatch** "for commands a human is waiting on"), the clock has two (the hands and the caretaker). Two billing hatches also open onto the back belt (`milkshake-farm-invoice`, `milkshake-mercury-hook`): tag them "not ours" until their owner is confirmed (verify).

### 3.4 What the belt must never imply

1. **The belt is not transport.** Its motion is the clock, its height is age, and readers come to it. The conveyor from the vendors' bays to the dock *is* transport (the socket from `bb-hook` to hook-hub): draw it as horizontal rollers, visibly unlike the vertical belt.
2. Reading does **not** remove a post-it. Only the scraper does.
3. An envelope is **not** gone when taken. It is gone when signed off, torn up, or scraped.
4. A signature is **not** a success stamp. Success and failure are post-its.
5. One hand at a time is **not** "done once". Repeats happen; safe-to-repeat codes and ledgers absorb them.
6. The belt is **not** the archive. It keeps 7 days. The archive keeps its own copy with no promise of how long ("forever" is a forbidden word).
7. Notes are **not** prioritised, and belt order is **not** always the order things happened (B17).
8. There is **not** one belt per topic. One front belt carries every domain; icons and pick lists do the sorting.
9. The belt does **not** check labels (B5).
10. Every note does **not** pass through hook-hub. Only vendor parcels do. The rules cabinet (n8n), the clock, the crew hall, the sound wing and Jarad's hand stamp (`bb-emit`) stick house notes directly; they arrive floor-ready, already in the house format.
11. **"Nothing is lost" is false.** If the dock door is shut, the courier turns round with the parcel still in hand and no post-it is ever written (`bb-hook` fails open). If the belt's door is shut, the dock's note is dropped with no retry.
12. A heard note is **not** a stored note (B16).
13. **The runner is not part of the belt, and "Dapr carries everything" is false.** Most runners only fetch. One, the cataloguer's, also sticks one kind of note (its session summary), and that note skips the label desk. Every other writer sticks by hand.
14. **Every envelope does not get handled** (B11).
15. **The warehouse is never on the road** between a vendor and its model (section 1).
16. Jarad's and Damian's buildings do **not** share a belt (no federation).

---

## 4. The cast

### 4.1 The cast table

Three tiers [P], so the world stays a map and not a gift shop. **Core** parts get a full card, a drill-down ladder and bulbs. **Supporting** parts get a short card and a bulb only when it is strong. **Extras** get a name plate. Status per building: live, partial, absent on Damian's Mac (dashed tape), or outside the fence. Every "where it breaks" line is said on the page wherever the picture would otherwise mislead.

| # | Real name | Warehouse role [P unless marked] | Tier | Where the fit breaks | Bulbs |
|---|---|---|---|---|---|
| 1 | big-chungus; Damian's Mac Studio | **The building**: Warehouse One (Jarad's), Warehouse Two (Damian's) | supporting | A building's floor is space; ours is CPU and memory, and one greedy room can starve the rest. Warehouse One also has rooms in other towns (a Lightsail VM, a droplet). | none |
| 2 | Docker containers; Colima | **Cabins** that arrive furnished; on the Mac they stand inside **the enclosure**, whose gate opens only after a console login | supporting | Cabins never travel anywhere. Native services are brick rooms, not cabins. | reserve: container |
| 3 | Agent CLIs (Claude, Codex, Kimi, Gemini, Copilot, Hermes, opencode, Antigravity) | **Vendors**, each packing its own boxes in its own label language [J: "parcels from Claude, Kimi, Codex, Hermes, etc"] | core | They are not companies on our lot: they are programs on the owner's desk. Hermes is a vendor *and* the crew hall. | (before-picture for Normalization) |
| 4 | bb-hook | **The courier**: one courier in one uniform, working every vendor's bay | core | One small program run once per hook, not a person; the "conveyor" is a unix socket and takes milliseconds. | Hook; Fail-open |
| 5 | hook-hub | **The receiving dock** (sign: RECEIVING) with its bench, its job cards and its driver's window [J: "goes in as a box and out as a post-it note"] | core | One daemon with about 35 job cards, not a crew. Normalization covers the label, not the whole body (the packing slip rides on the back). | Normalization [J]; Asking vs announcing |
| 6 | Bloodbank | **Material Handling**: the department that owns the dock, the belt, the label standard and the posters' training | supporting | A department implies a manager; Bloodbank is a repo and a contract, with no central publisher service. | none |
| 7 | Naming contract, schemas, validator | **The label desk**: house dictionary, form pads, inspector | core | Not one desk: copies of the inspector sit at several benches, some writers skip it, and the belt never inspects. | Schema |
| 8 | NATS JetStream and its streams | **The belt**: front loop, back loop, the sister belt [J: "a long vertical two-sided conveyor belt"] | core | Its motion is age, not delivery. Two loops, not one. | Bus; Stream (log); Fan-out; Event vs command; Retention; Work queue |
| 9 | Publishers | **Posters**: the people who stick notes on [J: "an employee sticks it"] | core | Sticking takes milliseconds, and anyone in the building may do it. Two ways to stick (doorbell, registered). | none (shares Bus) |
| 10 | Consumers | **Clips** (durable), **visitor's passes and notebooks** (ephemeral), **pick lists**, **picking lifts** | core | A clip rides up with the note it marks. Some readers keep their place in their own notebook. | Bookmark; Loose coupling |
| 11 | Dapr sidecars (+ idle placement) | **Runners** who fetch notes for a room-bound clerk (warehouses call this role a water spider) | core | A runner is a process bolted to the app. The cataloguer's runner also sticks one kind of note. | Sidecar |
| 12 | Candystore | **The archive**: racks at the back of the floor, a filing clerk, a rejects drawer, a lookup counter | core | No retention promise. Its racks also hold the cataloguer's tags. | Idempotent |
| 13 | Enricher | **The cataloguer**, who writes locator tags and end-of-session summaries | supporting | It tags only finished tool calls, phones the archive's counter directly for a summary, and sticks notes that skip the label desk. | reserve: search by meaning |
| 14 | Hindsight | **The lessons library**: logbooks per project and per worker | supporting | Not on the belt: reached over the phone line (HTTPS). Absent from Damian's building as ours (verify what his dock's library cards point at). | reserve: retrieval |
| 15 | Candybar | **The clock**: one bell, the planner, the hands, the caretaker | core | The clock owns *when*, not always *who* does the chore. A signed list of alarms stays outside it, each with a named owner and reason. | Single source of truth |
| 16 | hermes-gateway + bus plugin | **The crew hall**: one front desk, one set of plumbing, two hatches on the back belt | core | One program: "walking to a workstation" is a function call. | Acknowledgement; Backpressure |
| 17 | Hermes profiles | **Workstations**: badge (SOUL), locker (memory), how-to placards (skills), radio (gateway door such as Telegram) | supporting | A workstation is only its files until an envelope or a call wakes it. A badge that fails the safety scan is not read at all. | reserve: separation of concerns |
| 18 | Skillex | **The tool crib**: the master copy of every how-to placard | supporting | A workstation's placard points to the master; it is an address (a symlink), not a window. | reserve: reference, not copy |
| 19 | Flume + role template | **HR and the badge office**, with the **job description binder** | supporting | HR furnishes a workstation; it does not judge the work. The role and lanes come from the template. | reserve: template |
| 20 | pjangler | **The building directory** in the lobby | supporting | Written to as well as read: projects are registered and moved. | reserve: registry |
| 21 | Plane + px | **The ticket board** (white printed cards in pockets, never sticky notes) and **the marker** | supporting | px is the intended writer by policy, but the rules cabinet and shift leads also write on the board. | none |
| 22 | n8n (+ lanes, n8n-nodes-bloodbank) | **The rules cabinet**: rule cards wired to their own clips; one card is a second receiving dock for the ticket board's bell | supporting | It also has side doors (webhooks in, direct board writes out) that skip the belt. | (Normalization, second sighting) |
| 23 | PM desks, Momo, Krebs | **Shift leads**, the **shift lead's playbook** (Momo), the **handover binder** (Krebs, mostly unopened) | supporting | "Lead" implies authority; a PM desk mostly grooms and comments. | none |
| 24 | AutomaticAI gateway; LLM providers | **The staffing desk next door**, sending work to **agencies across town** | supporting | Next door in ownership, not place (a cloud VM). A fallback list can look healthy while its unfunded members are skipped. | Gateway |
| 25 | Jev | **The inspector on call**, who only stamps pass/fail, one of a list, or a score | supporting | One of possibly two lines between the buildings (Hindsight may be the other; verify). | none |
| 26 | Holocene | **The control room** on the mezzanine, reading from a visitor's window | supporting | It sees only what was stuck on the belt: from here, quiet and dead look the same. | Observability; Eventual consistency; Correlation ID |
| 27 | Monitoring stack + ntfy | **Maintenance**: sensors on every machine, rounds on a timer, the machine log, an andon light, a radio page to Jarad | supporting | Prometheus pulls on a timer, which is honest "rounds"; it is not fired by the clock. | (Observability, shared) |
| 28 | Telegram, ntfy, Plane comments | **The outbound dock**: last-mile carriers (Telegram), shipment notices (ntfy pings) | supporting | A place, not a component: each room ships its own way. | none |
| 29 | HeyMa / waxd / intake | **The sound wing**: an inbound dock with three doors, the secure cage, eight passes | supporting | It sticks notes from its own outbox (not a vendor), and issues envelopes nobody collects (B11). Absent on Damian's Mac. | reserve: back up first |
| 30 | Vinyl | **The dictation mic** at your own workstation | extra | A sibling of the sound wing that only borrows its word list; on the Mac it would phone Jarad's building. | none |
| 31 | Voxxy | **The voice booth**: slide a script under the door, get a recording back | extra | Only the caller gets the recording; no speakers in the ceiling. | none |
| 32 | Bus helper services | **Specialist clerks** with their own clips (artifacts, the vault projector, target watch, cost, curator) | extra | "artifact-sidecar" is not a runner. | none |
| 33 | Aperture | **Flat-pack crates** for building a second warehouse | extra | Some crates are still being designed. Site Office binder only. | none |
| 34 | Jarad and Damian | **Two owners, two buildings, no belt between them** | extra | Readers will ask to send a note across; today the answer is no. | none |

### 4.2 Core cards

Each card: the story, why the fit is tight (the real behaviour and its file), where it breaks (said honestly), the drill-down ladder (L1 floor view, L2 station close-up, L3 inside the machine, with its **spec plate**: the one object used for settings at L3 everywhere), and its bulbs. All [P] unless tagged.

#### 3. Vendors (the agent CLIs) [J]

- **Story:** vendors' vans pull up to the inbound bays. Each packs its boxes its own way and writes the label in its own words. Hermes is a vendor too: the crew hall's own workers ship boxes to the same dock.
- **Why tight:** every CLI has its own hook dialect. One master packing sheet (`agent-hooks/hooks.master.json`) is generated out to each vendor's config (Claude settings, Copilot, Codex, Hermes config, the Antigravity bundle; Gemini, Kimi, opencode and OpenClaw have client folders too) and maps each native hook to one role, such as `prompt_submit`.
- **Breaks:** the vendors are programs on the owner's own desk, not companies on our lot. Antigravity has no prompt hook at all.
- **Ladder:** L1 a row of bays with different vans. L2 one box with its handwritten label. L3 the master packing sheet on the wall: one sheet, many dialects, generated, never hand-edited.
- **Bulbs:** none of its own; it is the "before" picture for Normalization.

#### 4. bb-hook: the courier

- **Story:** one courier, in one uniform, works every bay. The vendor hands over the parcel; the courier carries it down the conveyor to the dock. For some parcels the vendor waits while the courier stands at the **driver's window** for a briefing card. If the dock door is shut, the courier turns round with the parcel still in hand, and the vendor carries on as if nothing happened.
- **Why tight:** every native hook runs the same `bb-hook <cli> <native-event>`, which hands the payload to hook-hub over a unix socket. Its one hard rule: "it never wedges an agent". Every failure path prints nothing and exits 0, "exactly as if no hook were installed", with no spool (`hook-hub/client/bb-hook`).
- **Breaks:** the conveyor is a socket and takes milliseconds. Nothing waits at a curb: the moment simply never becomes a post-it. A stuck (not shut) dock costs the vendor about a second, never the old 15 s figure (`W2-4` fix pass).
- **Ladder:** L1 the courier at the bays. L2 the courier at a shut door, turning round, box still in hand, empty curb. L3 the courier's card: "door open: push the box through and wait at the window if the card says so; door shut: turn round".
- **Bulbs:** **What is a hook?** (at the vendor's bay: the peg a program leaves out for your own code). **What is fail-open?** (at the shut door).

#### 5. hook-hub: the receiving dock [J]

- **Story:** every conveyor ends at a long bench under a RECEIVING sign. A clerk opens each parcel, reads the vendor's label, and writes the news on **one house post-it**, with the vendor's name in the small "from" corner and the original packing slip stapled to the back. The barcode printer adds the conversation's barcode. A poster takes the post-it to the belt. At the **driver's window**, clerks answer the parcels that wait: a clerk runs to the lessons library and hands a briefing card out to the courier ("last time on this project you learned..."), and a guard confiscates alarm clocks from any vendor who tries to install one (card 15).
- **Why tight:** hook-hub turns each dialect into one house event: a CloudEvents envelope whose type comes from the lifecycle map (`prompt_submit` → `bloodbank.conversation.turn.started`), checked by `assert_contract`. Vendor identity goes in `actor.cli` / `actor.provider`, never in the type (`bloodbank/CLAUDE.md`): that is the "from" corner. Most job cards match the house role (`on = ["prompt_submit"]` in `handlers.toml`). While the dock is open, a prompt parcel waits at the window: on Codex's prompt the cards run `skill-reminder` (1 s), `hindsight-recall` (11 s), `codegraph-prompt` (2 s) and a routing check (1 s). The post-it itself is written by a separate clerk at the back, `bloodbank-publisher`, which `hub.py` adds for every hook and runs without making the courier wait. A repeated parcel gets the earlier answer, not a second run (`hub.py`, `deduplicated`).
- **Breaks:** one program, about 35 cards, not a crew. The label is normalized; the body still carries the vendor's raw payload on the back (`clients/codex.py`: `raw = {"hook", "payload"}`), so a veteran opening one archived note will see Codex's own JSON. A few cards still read one vendor's word or serve only some vendors (`candystore-context-kimi` exists because Kimi needs its own twin).
- **Ladder:** L1 the dock with conveyors arriving from every bay and post-its leaving for the belt. L2 a Codex box and a Gemini box, different labels, becoming the same yellow "turn started". L3 the wall of job cards: window cards (sync) with stopwatches, back-room cards (async), and the clerk at the back who writes the post-it.
- **Bulbs:** **Normalization** [J], bobbing beside the bench. **Asking vs announcing**, at the driver's window.

#### 7. The label desk (naming contract, schemas, validator)

- **Story:** beside the dock, a desk with the chained **house dictionary**, the **form pads** and an inspector with a stamp. A label with a word not in the dictionary, a vendor's name in the headline, or a version number is refused. Anyone may ask for the dictionary (`bb contract`) or a dry stamp that shows exactly what would be stuck, without sticking it (`bb emit --check`).
- **Why tight:** type is `bloodbank.<domain>.<entity>.<action>`; the subject adds `evt|cmd|rpy`. Every word must be on an explicit allowlist in `validate.py`. No version token ("breaking payload changes get a new action or entity", `streams.json`). Commands must also carry an actor, a command id, a safe-to-repeat code and a delivery block (`REQUIRED_COMMAND_FIELDS`).
- **Breaks:** copies of the inspector sit at several benches (hook-hub, `bb-emit`; the rules cabinet's poster always checks envelopes but checks post-its only when asked, `nats.ts`). Writers that skip the desk can stick anything, and the belt never inspects (B5).
- **Ladder:** L1 the desk beside the dock. L2 the inspector refusing "codex" in a headline and moving Codex to the "from" corner. L3 the dictionary open at the domain page (`conversation`, `agent`, `repo`, `audio`, `cron`...) and one form pad.
- **Bulbs:** **What is a schema (a contract)?**

#### 8. The belt (NATS JetStream and its streams) [J]

- **Story:** section 3. The tallest thing on the floor, glass-sided, visible from every wing.
- **Why tight:** section 3.2, B1 to B18, with live values.
- **Breaks:** section 3.4. The big one: motion is age, not delivery.
- **Ladder:** L1 the belt from across the floor, day ruler on its side. L2 the loading point and its sorter, a scraper, the hatches. L3 the gearbox's spec plate, one row per loop: label pattern, kind of loop, scraper height, duplicate window (copied from `streams.json` and the live server), plus one line for the green sister belt.
- **Bulbs:** **What is a bus?** (the loading point), **What is a stream (a log)?** (the day ruler), **Fan-out** (the front face), **Event vs command** (where the faces meet at the edge), **Retention** (the scraper), **Work queue** (the back belt).

#### 9. Publishers: the posters [J]

- **Story:** a **poster** is anyone with news who walks up to the loading point and sticks a note on. There is no poster department: each room has its own, with a pad of house forms. Two ways to stick. At the **doorbell**, you ring, hear "come in", drop the note through the slot and leave. At the **registered counter**, you wait for a receipt with the belt number on it, and try again if none comes. (Warehouses call putting goods onto a belt induction.)
- **Why tight:** publishing is a call from inside each service, with no central publisher (`bloodbank/CLAUDE.md`). Doorbell = core PUB then PING/PONG (`agent-hooks/core/nats_publish.py`), whose own docstring says a PONG "is transport progress, never evidence that JetStream stored an event" (`hook-hub/observations.py`). Registered = JetStream publish with a PubAck and the Note ID as `Nats-Msg-Id` (`candybar/bus.py`, the Hermes adapter).
- **The regulars** (B18): the dock's poster (every vendor note; doorbell, no retry if the door is shut); the dock's receipt clerk (registered); the rules cabinet; the clock; the crew hall; the sound wing's outbox; the cost bridge (verify the owner); the cataloguer's runner; and Jarad's hand stamp `bb-emit`, a command-line poster that can also do a dry stamp (`--check`).
- **Breaks:** sticking takes milliseconds and the belt does not check who. "Material Handling" trains the posters; it does not stick anything. Every writer keeps its own copy of the rules.
- **Ladder:** L1 workers walking up to the belt from every room. L2 the doorbell and the registered counter side by side, with the same note. L3 spec plate per poster: does it print the Note ID on the back (yes or no), and does it wait for a receipt (yes or no).
- **Bulbs:** none of its own; it shares **What is a bus?**

#### 10. Consumers: clips, passes, pick lists, lifts [J, for the tearing off]

- **Story:** a reader stands at the belt, **tears off a copy** of each note it cares about, and **signs** once it has dealt with it. Most readers hand the belt a **clip** with a name tag to remember where they got to. The control room takes a **visitor's pass** and keeps its own **notebook** instead. A clip may carry a **pick list** (stop only at "ticket created"). From Book 6, each reader gets a **picking lift** that shows how old the note in its hand is and how many are still below.
- **Why tight:** a durable consumer's position, ack state and filter live on the server (about two dozen on the front loop at last count, 2026-11-11). `ackWait` is how long it may sit on an unsigned copy, `maxAckPending` how many it may hold, `deliverPolicy` where a new clip starts (B8, B9). Holocene's reader is ephemeral, `ack none`, started by sequence, with its own checkpoint (`holocene/packages/bloodbank-client/src/index.ts`).
- **Breaks:** a clip is a number on the server, not a thing stuck to a note. We draw it riding up so that height reads as age. Some readers keep their own place, so "the belt remembers everyone" is false. A clip nobody comes back for keeps its notes pinned until the scraper takes them (the abandoned `smoke-check` clip holds 28 unread).
- **Ladder:** L1 a few coloured clips at different heights. L2 one clip's tag: name, pick list, how many unsigned. L3 spec plate: start point, patience, hand limit, tries.
- **Bulbs:** **What is a bookmark?** (clip rail). **What is loose coupling?** (a new clip arrives and nobody at the dock notices: Damian's one reader).

#### 11. Dapr sidecars: the runners

- **Story:** some rooms have no window onto the belt (the archive, the cataloguer). Each has a **runner** who stands at the belt on its behalf, tears off copies, walks them to the room's door and waits for "got it" before signing. A runner and its room come as a pair. (Warehouses call this role a water spider.) A placement office sits in the corner, staffed and idle.
- **Why tight:** the Dapr pubsub component subscribes to a JetStream durable (archive: durable `candystore-events`, group `candystore`, `deliverPolicy` all, `ackWait` 30 s; cataloguer: new, `maxAckPending` 32, 300 s) and POSTs each message to the app's route; HTTP 200 is the ack (`candystore/dapr-components/pubsub.yaml`, `enricher-pubsub.yaml`).
- **Breaks:** a runner is a process bolted to its app, not a separate worker pool. **The cataloguer's runner also posts one kind of note**, `report.session.completed`, through its own sidecar (`enricher/main.py` `emit_event`): 506 live on 2026-11-11, `type com.dapr.event.sent`, `source enricher`, no barcode or "came after". Most runners only fetch, so "Dapr carries everything" stays forbidden. The artifact clerk is not a runner.
- **Ladder:** L1 a runner at each windowless door. L2 a runner at the archive's counter, waiting for "got it". L3 spec plate: durable name, group, start point, patience, hand limit.
- **Bulbs:** **What is a sidecar?**

#### 12. Candystore: the archive

- **Story:** racks at the back of the floor. A filing clerk copies each post-it into a slot labelled with its **Note ID**. If the slot is taken, the clerk shrugs and moves on. A **rejects drawer** holds notes it cannot file. A **lookup counter** hands back a conversation's story, or the original packing slip for one note.
- **Why tight:** `ON CONFLICT (id) DO NOTHING` on the CloudEvents id (`candystore/db.py`), so a note that arrives twice is filed once. A `dead_letter` table takes what cannot be stored. The counter is `GET /sessions/<id>` and `/events/<id>/raw`. PostgreSQL 17 with pgvector.
- **Breaks:** the archive makes no retention promise, and "keeps everything forever" stays forbidden. The rejects drawer is a drop path: it logs the note and acks with 200, so nothing retries it. The racks also hold the cataloguer's tags. The dock's own notes rely on this clerk alone for dedupe (B15).
- **Ladder:** L1 racks, one clerk, one counter. L2 the clerk with two slots, new and taken. L3 spec plate: the clip it holds on the belt (starts at the top, 30 s patience).
- **Bulbs:** **What does idempotent mean?** (the racks). You've already met it as upsert.

#### 15. Candybar: the clock

- **Story:** one big **bell** on the wall. When it rings, a **planner** reads the chore chart and writes an envelope for each chore due. The **hands** take them, look up the safe-to-repeat code, do the chore, and stamp "still working" along the way. A **caretaker** looks for chores that went quiet. **No private alarms:** a guard at the dock's window refuses any worker who tries to set one. Stopwatches inside a single job are fine.
- **Why tight:** Candybar owns when; `candybar doctor --live` audits it. The executor dedupes on `idempotency_key`, skips an overlapping or coalesced run with a signature, and sends `in_progress` stamps ("effectively-once execution rests on the registry, not the bus", `candybar/executor/worker.py`). Its hatches (`candybar-executor-invoke`, 1 h patience, never gives up; `candybar-steward`, 10 min) read the back belt. `native-clock-guard` denies crontab, new timers, `at` and Hermes cron at the window.
- **Breaks:** the clock owns **when**, not always **who**: execution can be a service or a Hermes job. The guard fails open; the doctor is the backstop. A signed list of alarms stays outside it (43 rows on 2026-11-11, each with an owner and a reason, `deploy/scheduling-policy.json`).
- **Ladder:** L1 the bell and a chore chart. L2 the planner's envelope and the hands' ledger. L3 spec plate: one chore's manifest card (name, when, who runs it, what counts as done).
- **Bulbs:** **What is a single source of truth?** You've already met it as "one cron".

#### 16. hermes-gateway: the crew hall

- **Story:** a long hall with **workstations** along the walls and one **front desk**. Two hatches open onto the back belt: ordinary, and an **express hatch** for commands a human is waiting on. The desk takes an envelope, walks it to the workstation named inside, and signs off only after the work is done. Meanwhile it stamps "still working", and sticks post-its: started, completed, failed. It hands an envelope back when it is full, or tears up one it can never run.
- **Why tight:** `bloodbank-hermes-gateway` (filter `cmd.agent.invocation.start`, 5 tries, 3 min patience) and `-interactive` (`invoke`, 8 tries, at most 4 in hand). The adapter acks after the turn, calls `in_progress`, `nak(delay)` and `term()` (rejected, closed route, invalid command). `_not_run` closes the envelope as failed and signs off only on the last try. A finished envelope's ledger replays its post-its without running again. At capacity it stops fetching (`hermes-gateway/.../adapter.py`).
- **Breaks:** it is one program, and "walking to a workstation" is a function call. A signature is not success. There is no lost-and-found yet (B13). Hermes is a vendor and the crew hall.
- **Ladder:** L1 the hall and its two hatches. L2 the front desk with an in-hand tray and a stamp. L3 spec plate per hatch: filter, tries, patience, hand limit.
- **Bulbs:** **What is an acknowledgement (and why things arrive twice)?**. **What is backpressure?**

### 4.3 Supporting cards (compact)

One short card each: the picture, the fit, the break. A bulb appears only where the table in 4.1 names one. All [P].

- **1. The building (big-chungus; Damian's Mac Studio).** Warehouse One is Jarad's, Warehouse Two is Damian's. One floor, shared by every room. *Fit:* a greedy room starves the others, exactly as one heavy job slows every agent. *Breaks:* floor space here is CPU and memory; Warehouse One also has rooms in other towns.
- **2. Cabins (Docker) and the enclosure (Colima).** Furnished cabins arrive on a truck and are set on the floor. On the Mac they stand inside a fenced enclosure whose gate opens only after a console login. *Breaks:* cabins never travel; native services are brick rooms.
- **6. Material Handling (Bloodbank).** The department that owns the dock, the belt, the label standard and the posters' training. *Breaks:* a department implies a manager. Bloodbank is a repo and a contract.
- **13. The cataloguer (Enricher).** Reads finished tool-call notes, writes **locator tags** (so the archive can find them) and an end-of-session summary. It phones the archive's counter for the session facts (`GET /sessions/<id>`) and ignores every other kind of note. *Breaks:* its summary notes skip the label desk (card 11).
- **14. The lessons library (Hindsight).** Logbooks per project and per worker. A clerk fetches a briefing card from it at the driver's window ("last time on this project..."), and a recorder writes lessons back after a turn. *Breaks:* reached over the phone line, not the belt. Hindsight's recorder skips Hermes and opencode. On Damian's Mac the library's address is unverified (verify).
- **17. Workstations (Hermes profiles).** Each has a **badge** (SOUL, who it is), a **locker** (its memory), **how-to placards** (skills) and a **radio** (its door to the outside, such as Telegram). *Breaks:* a workstation is only its files until an envelope or a call wakes it. A badge that fails the safety scan is not read at all, and the worker works with a blank badge.
- **18. The tool crib (Skillex).** The master copy of every how-to placard. A workstation's placard is an address, not a window; a strict desk takes only the placards its role lists. *Breaks:* a symlink is an address, not a copy.
- **19. HR and the badge office, with the job description binder (Flume plus the role template).** HR furnishes a workstation: badge, lanes, placards. *Breaks:* it does not judge the work; the role and lanes come from the template. Reserve bulb: template.
- **20. The building directory (pjangler).** The lobby board that says which project lives where. *Breaks:* people write on it too (register, move).
- **21. The ticket board and the marker (Plane and px).** White printed cards in pockets (never sticky notes), moved by one marker. *Breaks:* the rules cabinet and the shift leads also write on the board. The marker is the intended writer by policy.
- **22. The rules cabinet (n8n, its lanes, `n8n-nodes-bloodbank`).** Rule cards wired to their own clips; one card is a second receiving dock for the board's bell, turning ticket webhooks into house post-its (Normalization, second sighting). *Breaks:* it has side doors, webhooks in and direct board writes out, that skip the belt.
- **23. Shift leads (PM desks), the playbook (Momo), the handover binder (Krebs).** A shift lead grooms the board and comments. The playbook is the order of play; the binder holds leases and handover notes, mostly unopened. *Breaks:* "lead" implies authority; a PM desk mostly grooms and comments.
- **24. The staffing desk next door (AutomaticAI gateway) and the agencies across town (LLM providers).** The desk sends a request to the first agency that can take it, then the next on its list. *Breaks:* next door in ownership, not place. A fallback list can look healthy while its unfunded members are skipped.
- **25. The inspector on call (Jev).** Stamps pass or fail, picks one from a list, or gives a score; never writes the work. *Breaks:* one of possibly two lines from Warehouse One to Warehouse Two (verify).
- **26. The control room (Holocene).** A mezzanine over the floor. Its window shows what is on the belt, one pass and one notebook per visit. *Breaks:* it sees only what was stuck on the belt; from the mezzanine, quiet and dead look the same. Bulbs: Observability, Eventual consistency, Correlation ID.
- **27. Maintenance (monitoring stack and ntfy).** Sensors on every machine, **rounds** on a timer (Prometheus pulls; that is honest rounds, not the clock), a **machine log**, an **andon light** and a radio page to Jarad. *Breaks:* rounds are not fired by the clock.
- **28. The outbound dock (Telegram, ntfy, Plane comments).** Where results leave the building: last-mile carriers and shipment notices. *Breaks:* a place, not a component; each room ships its own way.
- **29. The sound wing (HeyMa, waxd, intake).** An inbound dock with **three doors**, a **secure cage** the audio goes into first, and **eight passes** over one transcript. *Breaks:* it posts notes from its own outbox, and it issues envelopes nobody collects (130 `audio.task.start` envelopes with no hatch, B11). Absent on Damian's Mac.

#### Extras (name plates)

- **30. The dictation mic (Vinyl).** At your own workstation. It borrows the sound wing's word list and, on the Mac, would phone Jarad's building.
- **31. The voice booth (Voxxy).** Slide a script under the door, get a recording back. Only the caller gets it: no speakers in the ceiling.
- **32. Specialist clerks.** Helpers with their own clips: the artifact clerk (starts from a marked time), the vault projector, target watch, cost, curator. The artifact clerk is not a runner.
- **33. Flat-pack crates (Aperture).** Crates for building a second warehouse. Some are still being designed. Site Office binder only, gated on W8-2.
- **34. Jarad and Damian.** Two owners, two buildings, no belt between them. Readers will ask to send a note across; today the answer is no.

### 4.4 Outside the fence [P]

Things a reader will ask about, which the warehouse does not hold. A page that needs one draws it **outside the fence**: dark grey with a plus tab (v0's "not ours"), never dashed, because dashed already means "absent on this reader's box".

| Thing | Picture | Why it is outside |
|---|---|---|
| Phonograph (the "+" in the old wall) | A neighbouring shop across the road | It is not part of the flow; draw it only if a page needs the neighbour |
| LLM providers | Agencies across town (card 24) | Their answers never cross our belt |
| Green in Between (GIB) | The green sister belt in the corner, spec plate only | Jarad's pool game, not a 33GOD flow; 0 consumers live |
| MCP hub | A boarded-up window | Not in use (verify before a page says so) |
| heartbeat-tick | The old clock in a drawer | Retired; liveness is the gateway's, scheduling is the clock's |
| Apicurio, EventCatalog | Flat-pack racking still in its crate | Planned or not wired (verify) |
| Damian's own services | Warehouse Two, dashed where a part is absent | It has the belt and the archive, and no cataloguer, clock, crew hall, sound wing or control room |
| The two milkshake billing hatches | A pair of hatches tagged "not ours" | Owner unconfirmed (verify) |

*A reader will ask "does it touch the road?" The answer is in section 1: the warehouse is beside the road, never on it.*

---

## 5. The lightbulbs

Jarad's idea [J]: a small bulb bobs beside a station. Click it and a themed modal opens, titled "What is X?", and teaches the engineering idea that station is built on. Bulbs repeat across the whole manual as its teaching device.

### 5.1 Rules for bulbs [P]

1. **Every bulb sits at the station whose behaviour is the concept.** No station, no bulb. A bulb on a concept the building does not show is a lecture.
2. **The picture comes first.** The title may name the term ("What is Normalization?"); the body pictures the warehouse first, then names the real term once.
3. **A modal has five beats.** The picture; the one real term; why bother; "you've probably done this"; "you'll spot it again". An optional cousin line ends it. About 180 words, trimmed to fit. The code evidence for a bulb sits in the catalog row ([`lightbulbs/README.md`](../lightbulbs/README.md)), never in the modal.
4. **At most one new bulb per page.** A concept met again gets a "spot it again" line at its next station, not a second bulb.
5. **"You've probably done this" names something the reader has built**: a Stripe plus PayPal checkout, an `await`, an upsert, a Slack "new messages" line. This is the buffer that serves both readers: the veteran thinks "yes, that's exactly it", and the vibe coder thinks "oh, I did that".
6. **Status is shown.** Each bulb is *modal drafted*, *proposal* or *reserve* in the catalog. Only Normalization [J] is drafted.

### 5.2 The set: 22 bulbs, proposed [P]

"Already met" is the line the modal's third beat is built on. Station and one-line analogy for each are in the catalog.

| # | Bulb | You have already met it as | Spot it again at |
|---|---|---|---|
| 1 | Normalization [J] | Stripe and PayPal both becoming one "payment received" record | the board's bell; the clock's envelopes |
| 2 | What is a hook? | `addEventListener`; a webhook you register | every vendor's bay |
| 3 | Asking vs announcing | `await fetch()` versus a push notification | the dock's window, the post-it |
| 4 | What is a bus? | one group chat instead of calling each person | the loading point |
| 5 | What is a stream (a log)? | a git log or a bank statement: lines get added, never edited | the day ruler |
| 6 | Fan-out | one button with several click handlers | the archive, the cataloguer and the control room, all reading one note |
| 7 | Event vs command | "the oven beeped" versus "take the cake out" | where the front face meets the back |
| 8 | Loose coupling | adding a plugin without editing the app | a new clip (verify the history claim before a page tells one) |
| 9 | Bookmark | Slack's "New messages" line | every clip |
| 10 | Retention | "keep my messages for 30 days" | the scraper |
| 11 | Work queue | the ticket machine at a deli counter | the back belt |
| 12 | Acknowledgement, and why things arrive twice | a courier who needs a signature | the crew hall hatch |
| 13 | What does idempotent mean? | an upsert; pressing the lift button twice | the clock's ledger |
| 14 | Sidecar | a log shipper running beside your app | the runner at the archive |
| 15 | Schema | a form's required fields; TypeScript types | the form pads |
| 16 | Single source of truth | one cron instead of ten | the bell |
| 17 | Fail-open | an analytics script that fails and the page still loads | the courier at a shut door |
| 18 | Correlation ID | an order number repeated through every email | the barcode on every note |
| 19 | Eventual consistency | a like count that catches up a moment later | the control room window |
| 20 | Backpressure | a "429, slow down" | the crew hall's in-hand tray |
| 21 | Observability | a car dashboard | the control room and the andon light |
| 22 | Gateway | a switchboard in front of many lines | the staffing desk |

**Your Warehouse sheet** (end of each book) carries one more bulb, *Does a corner shop need a belt?*, so a reader with a small app hears that a belt is optional.

**Reserves, drafted only if a page wants one:** container, search by meaning, retrieval, reference not copy, template, registry, back up first, separation of concerns (retired from the first set as too generic).

---

## 6. The first modal

**Normalization** [J] is finished in [`lightbulbs/normalization.md`](../lightbulbs/normalization.md), written in the final tone. It sits beside the receiving dock's bench, the first station that does what the word means. Its evidence note is one line in that file.

---

## 7. Tone

The full guide is [`world/tone.md`](tone.md). It governs every page and every bulb. The line Jarad drew [J]: approachable above all, with no scary terminology and no assumption the reader knows everything; not so juvenile that vibe coders lose interest, and not so complex that veterans leave or the manual serves only them. The buffer is a clever analogy that makes the veteran think "yes, that is how a bus works" and the vibe coder think "now fan-out makes sense."

The rules that bite hardest:

- **The body pictures first; titles may name the term.** One real term per line.
- **A shelf of words the reader already owns** (API, server, database, webhook, JSON, payload, prompt, model, container, deploy, log) is used plainly. Only half-known words get translated.
- **At most 2 new world objects per page, and at most 2 unfamiliar real names.**
- **No condescension words** (simply, just, obviously, easy, of course).
- **The verbs are locked** (section 2). Dry humour, no baby talk, no exclamation marks.
- **Forbidden sentences** (grammar v0 §9.11, all still in force): "forever", "never stalls the agent", "nothing is lost", "any listener can catch up", "px is the only Plane writer", "Dapr over NATS carries everything", "a job is gone when taken".

---

## 8. The story route [P]

Every book follows one parcel, note or envelope a little further into the building. **Jarad reworks the order, the pages and the images; this is only a starting route.** Each page introduces at most 2 new world objects.

| Book | Title | Follows | Pages (new bulb in brackets) |
|---|---|---|---|
| **1** | **One Question** (default: Damian's edition) | Damian's question, from the Enter key to the belt | 1 Damian Asks Codex (beside the road). 2 Every Tool Packs Its Own Box (hook). 3 Receiving (Normalization [J]). 4 One Belt, Every Room (bus). 5 Tear Off a Copy (fan-out): Damian's one reader, with "add a second reader tomorrow and nobody at the dock notices". **Y** Your Warehouse: a worked online-shop example with four prompts, plus "Does a corner shop need a belt?" |
| 2 | Where Notes Are Kept | a note's first week | The Belt Keeps a Week (stream). The Scraper (retention). A Clip on the Belt (bookmark). The Runner at the Door (sidecar). Safe to Do Twice (idempotent). A New Reader Moves In (loose coupling; verify the history claim). A Briefing at the Window (asking vs announcing). Y |
| 3 | The Back of the Belt (Jarad's edition) | an envelope | A Note Is Not an Order (event vs command). One Envelope, At Most One Hatch (work queue, with an orphan squint). Signed Off, Not Taken (acknowledgement). One Bell, No Private Alarms (single source of truth). The Bell, the Planner, the Hands. Done Is a Post-it. Y |
| 4 | The Crew Hall | a ticket, through the rooms | Ticket Board and Marker. The Board Rings a Bell. The Rules Cabinet. An Envelope for the Shift Lead. Anatomy of a Workstation. The Tool Crib and HR. The Staffing Desk (gateway). Y |
| 5 | The Sound Wing | a recording | Three Doors In. Into the Cage First. Eight Passes Over One Transcript. The Mic and the Voice Booth. Across the Road. Y |
| 6 | The Control Room and the Night Shift | a barcode, across rooms | The Window Over the Floor (observability). Follow the Barcode (correlation ID; use F2 JIMB-459 as the cross-room example). A Breath Behind (eventual consistency). The Dock Door Is Shut (fail-open). Too Many at Once (backpressure; the escalator picture, B10). Clips Nobody Comes Back For (the `smoke-check` clip). Two Buildings, No Shared Belt. Y |
| off route | The Site Office binder | Aperture's flat-pack crates | gated on W8-2; not scheduled |

**Why Book 1 starts beside the road.** Page 1 shows Damian pressing Enter, and Codex answering by its own road, outside the fence (section 1). That is the one place a vibe coder would otherwise wonder whether the warehouse sits between them and the model.

---

## 9. Migration from grammar v0

### 9.1 Carries over unless this bible says otherwise

- **Evidence discipline** (v0 §8): every claim a page draws has a row in its evidence sheet and a tiny numbered evidence dot; code wins over docs; only stable facts print on a face; the (verify) rule.
- **The word budget** (v0 §6): 30 visible words per page, labels of 3 words or fewer, one 7-word caption, 2 unfamiliar real names.
- **The page regions** (v0 §4, R1 to R4), the **check and X frame**, the **squint sticker** (a wink and a page numeral, at most 2 per page) and the **status marks**: solid = live, a bite out of a corner = partial, dashed outline = not running on this reader's box, grey with an X = retired.
- **The forbidden-sentences list** (v0 §9.11).
- **Colour meanings** (v0 §5), with one change: yellow = post-its (things in flight), **kraft = envelopes**, blue = the belt and nothing else. Dapr's runners keep their own colour, never blue (D3).
- **The four lines**, re-skinned: NOTE (an arrow carrying a post-it), JOB (an arrow carrying an envelope), ASK (the coiled cord with an hourglass, now the courier at the driver's window) and KEEP (an arrow ending in a drum, now the archive rack). No fifth line.
- **The reader is drawn as a person**: Damian as an outline on tan, one recurring figure.

### 9.2 Retired or transformed [P]

| v0 | Becomes |
|---|---|
| Notice wall (D1) | **The belt**: two loops, one glass shaft |
| Calendar for retention | **The scraper** and the **day ruler** |
| Blip (the face) | **The post-it.** No face on any data object; faces go on people |
| Chore | **The envelope** |
| Mail is banned (D1) | **Still banned for events** (post office, mailroom, mailbox and "deliver" stay banned on any face). "Envelope" and "addressed to a kind of work" are allowed for commands only, on the back loop |
| Pin, read, copy (v0 verbs) | **Stick, tear off a copy** (section 2) |
| Bricks for components | People, rooms and machines on the floor |
| Baseplates | The slab, the enclosure and the cabins |
| Contract tags | The corner icon and the pick list |
| Multi-builder bar | **Picking lifts** (Book 6) |
| The "+" (not ours) | **Outside the fence** (4.4): dark grey, a plus tab, never dashed |
| Level meter | **Optional.** If added, it is not one of Jarad's four questions |
| Bookmark flag on the wall (D4) | **The clip**, clamped on the belt |
| Real name printed small (D8) | **Kept.** The world name on the face, the real name small |
| Dapr is never bus-coloured (D3) | **Kept.** Runners wear their own colour, never the belt's |

### 9.3 Decisions for Jarad [P]

Each has a recommended default that stays in force until he changes it.

1. **Book 1's building.** Default: Damian's edition, so his one reader is the point of the book. *(His in-person feedback will say.)*
2. **Art direction.** Default: LEGO-style, a brick-built warehouse, generic: no Amazon logos, colours or brand terms.
3. **The rename set on the page faces.** The belt, vendors and courier, posters, "tear off a copy", the Note ID, the briefing card, the rules cabinet, workstations. Default: adopt, with the world name on the face and the real name small (v0 D8).
4. **Blip.** Default: retire the face; the post-it is the event.
5. **Replies (confirmation stubs).** Default: leave out of v1 and fold "done" into post-its.

Smaller calls, defaults applied: a two-loop glass belt; kraft envelopes; GIB on the spec plate only; picking lifts only from Book 6; 22 bulbs.

### 9.4 Ground-truth notes that are stale or contradicted by code [P]

- **The Enricher publishes through Dapr.** `enricher/main.py` `emit_event` posts to its sidecar, so `bloodbank.evt.report.session.completed` is stuck by a runner, not by hand (506 live on 2026-11-11, `type com.dapr.event.sent`, `source enricher`). `research/platform-map.md` (the `dapr` row and stale trap 2) says Dapr only subscribes. Code wins; this bible teaches the exception (card 11). **Engineering choice, not Jarad's:** move that emit to raw NATS with a house envelope, or keep the exception.
- **`research/platform-map.md` F1 step 3** names `bloodbank-publish`; the code's handler id is `bloodbank-publisher`, synthesized in `hub.py`.
- **`research/damian-reality.md` line 23's "15 s" figure** for a hung hub is stale: W2-4 bounded it to about 1 s.
- **Still open (verify before a page prints it):** who owns the two milkshake billing hatches; where Hindsight's handler points on Damian's Mac; which sync handler answers on his dock; `prompt_text` for each vendor; the loose-coupling history claim.
