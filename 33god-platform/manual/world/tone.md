# The Manual: tone guide

Status: revision 1, 2026-11-11. Initiative I-10. Governs every page and every lightbulb in the warehouse world ([`warehouse-bible.md`](warehouse-bible.md)). **[J]** = Jarad's direction. **[P]** = proposal, to be struck or rewritten by him.

## 1. The line [J]

The voice is very precise and, above all, **approachable**: no scary terminology, and no assumption that the reader already knows everything. It has to sit on a thin line.

- Too juvenile, and the vibe coder, who thinks they know more than they do, switches off.
- Too complex or overwhelming, and the veteran leaves, and the manual becomes useful only to veterans.

The buffer is a **clever analogy**. The veteran thinks "yes, that is how a bus works, good way to picture it." The vibe coder thinks "now that I can picture a bus, fan-out makes sense." Complexity is handled by going deeper into the analogy, never by adding vocabulary. Cohesion is handled by every analogy living in one warehouse.

**The double-reaction test [J].** Read each page and bulb twice, once as each reader. It passes only when both say "that is right" and neither says "that is talking down to me" or "I lost it."

**The third check [P].** After reading, can the vibe coder name one post-it and one envelope from their own app? If not, the analogy is decorating, not teaching.

## 2. Rules [P]

1. **Pictures first.** A title may name the term ("What is Normalization?"). The body pictures the warehouse first, and the real term comes after, once.
2. **"You'll hear this called X."** Never "Engineers call this X". The first stays a guide; the second sorts the reader into insiders and outsiders.
3. **One real term per line.** Two new words in a sentence is where readers fall off.
4. **A shelf of words the reader owns.** API, server, database, webhook, JSON, payload, prompt, model, container, deploy and log are used plainly, with no translation. Translating them is condescending.
5. **Translate only half-known words.** Bus, stream, consumer, ack, idempotent, sidecar. Keep JetStream, CloudEvents and "workqueue retention" off a page face entirely.
6. **Object budget.** At most 2 new world objects per page. At most 2 unfamiliar real names (v0 §6). A page that needs a third is two pages.
7. **Headlines on post-its are past tense** ("turn started", "ticket created"). Envelopes are imperatives ("start", "invoke").
8. **No faces on data.** Post-its, envelopes and parcels never smile. Faces go on people.
9. **Dry humour, sparingly.** One wry line per page is the ceiling. No baby talk, no exclamation marks, no "Let's...", no cartoon sound words.
10. **The verbs are locked** (bible, section 2): stick, tear off a copy, sign off, stamp "still working", hand back, tear up, scrape, file, wait at the window. Never "peel", never "deliver" a post-it.
11. **Stable numbers only.** A live count on a page face goes stale in a week. Prefer "about two dozen" or a stamped, dated figure.
12. **No condescension words:** simply, just, obviously, easy, of course, as you know, trivially, "all you need to do".
13. **Say where the picture breaks.** The honest "where it breaks" line is part of the page, not a footnote. A reader who finds the break alone stops trusting the rest.
14. **A warehouse aside is allowed, an Amazon aside is not.** "Warehouses call this induction" is fine when the real warehouse word exists and helps. Never use branded terms (FNSKU, ASIN, Problem Solve, the smile arrow) or Amazon colours and logos. The look stays generic LEGO-style.
15. **Say what a thing does before what it is called.** "Something that stamps each note with a number" before "sequence".

## 3. Words, plain to real [P]

On a page face, the world word leads and the real name is printed small (v0 D8).

| World word | Real term |
|---|---|
| post-it | event |
| envelope | command |
| the belt | the bus: a NATS JetStream stream (two of them) |
| poster | publisher |
| tear off a copy | subscribe and read |
| clip | durable consumer (a bookmark kept on the server) |
| visitor's pass and notebook | ephemeral consumer, with its own checkpoint |
| pick list | filter subjects |
| sign off | ack |
| hand back, "try again in a bit" | nak with a delay |
| tear up | term |
| stamp "still working" | in progress heartbeat |
| scraper | retention (max age) |
| belt number | stream sequence |
| Note ID | event id (the CloudEvents `id`) |
| barcode, "came after" | correlation id, causation id |
| form pad, house dictionary | schema, the allowlist of legal words |
| briefing card | the synchronous hook's answer |
| vendor, courier, dock | agent CLI, `bb-hook`, hook-hub |
| runner | Dapr sidecar |
| archive, cataloguer | Candystore, Enricher |
| clock, crew hall | Candybar, hermes-gateway |
| rules cabinet, control room | n8n, Holocene |

Two words that are never used on a face: **message** (it is a note, either a post-it or an envelope) and **command** without its picture (an envelope).

## 4. Do and do not [P]

| Do not | Do |
|---|---|
| "hook-hub normalizes heterogeneous hook payloads into CloudEvents." | "The dock opens each parcel and copies the news onto one house post-it." |
| "Engineers call this fan-out." | "Tear off a copy and the original stays on the belt. You'll hear this called fan-out." |
| "Simply ack the message when you're done." | "A worker signs off an envelope when it has finished with it." |
| "Nothing is lost." | "If the dock's door is shut, the courier turns round with the parcel still in hand, and no post-it gets written." |
| "The bus delivers the message to every subscriber." | "Posters stick notes on. Readers come to the belt and tear off a copy." |
| "Peel off a copy of the note." | "Tear off a copy of the note." |
| "Look at this magical little belt that never stops!" | "The belt turns slowly, all day, whether or not anyone is watching." |
| "It is idempotent, so it is safe to retry." | "Doing it twice leaves the same result as doing it once. You'll hear this called idempotent." |
| "Don't worry, it's super simple." | (Nothing. Say what happens.) |

## 5. Forbidden sentences

Carried over from grammar v0 §9.11 with nothing relaxed, because the code says otherwise:

- "forever" or "never expires" for the archive.
- "never stalls the agent" or "nothing is lost" (the courier turns round with the parcel when the dock is shut).
- "any listener can catch up" (it depends on that reader's start point and on the scraper).
- "px is the only Plane writer" (policy, not behaviour).
- "Dapr over NATS carries everything" (most runners only fetch; one also posts).
- "a job is gone when taken" (it is gone when signed off, torn up or scraped).

New in the warehouse: "a signature means it worked" (a signature means finished with the envelope), "every envelope gets handled" (some have no hatch), "the belt delivers" (it keeps; readers come to it).

## 6. Before a page ships

- [ ] Both readers say "that is right" (the double-reaction test).
- [ ] The vibe coder can name one post-it and one envelope from their own app.
- [ ] No more than 2 new world objects and 2 unfamiliar real names.
- [ ] Every word on the face is plain, owned by the reader, or translated once.
- [ ] No condescension words, no forbidden sentence, no locked verb changed.
- [ ] The "where it breaks" line is on the page where the picture would mislead.
- [ ] Every claim has an evidence row, and every (verify) is closed.
- [ ] Nothing here that Jarad has not seen: anything this guide adds beyond his direction is [P].
