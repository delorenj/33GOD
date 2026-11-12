# Lightbulbs: the catalog

Status: revision 1, 2026-11-11. Initiative I-10. The lightbulb is Jarad's device [J]: a small bulb bobs beside a station, and clicking it opens a themed modal titled "What is X?" that teaches the engineering idea the station is built on. The set below, and every status other than Normalization, is a **proposal [P]**.

Rules for bulbs: [`../world/warehouse-bible.md`](../world/warehouse-bible.md) section 5. Voice: [`../world/tone.md`](../world/tone.md).

Status values: **drafted** (finished modal copy exists), **proposal** (concept and station chosen, no copy), **reserve** (written only if a page wants it). "First page" is the earliest page in the proposed route (bible section 8). Jarad may move any of them.

| # | Concept | Station | One-line analogy | Status | First page |
|---|---|---|---|---|---|
| 1 | What is Normalization? [J] | the receiving dock's bench | Many parcels in, one house post-it out | **drafted** ([`normalization.md`](normalization.md)) | B1 p3 |
| 2 | What is a hook? | the vendor's bay | A hook is a peg a program leaves out for your own code to hang on | proposal | B1 p2 |
| 3 | Asking vs announcing | the driver's window | At the window you wait for an answer; a post-it announces and nobody waits | proposal | B2 |
| 4 | What is a bus? | the loading point | One belt every room sticks to, instead of everyone phoning everyone | proposal | B1 p4 |
| 5 | What is a stream (a log)? | the day ruler | A noticeboard that only ever gets added to, and scrolls up with age | proposal | B2 |
| 6 | Fan-out | the front belt | Tear off a copy, and the original stays up for the next reader | proposal | B1 p5 |
| 7 | Event vs command | where the front face meets the back | A post-it says it happened; an envelope asks one worker to do it | proposal | B3 |
| 8 | What is loose coupling? | a new clip arriving on the belt | A new reader moves in and nobody at the dock notices | proposal | B2 (verify the history claim) |
| 9 | What is a bookmark? | the clip rail | A clip marks where everything above has been signed for | proposal | B2 |
| 10 | What is retention? | the scraper | A bar at the 7-day mark takes whatever reaches it, read or not | proposal | B2 |
| 11 | What is a work queue? | the back belt's hatches | One hatch per kind of envelope, so one worker takes each one | proposal | B3 |
| 12 | Acknowledgement, and why things arrive twice | the crew hall hatch | A courier who needs a signature will come round again if nobody signs | proposal | B3 |
| 13 | What does idempotent mean? | the archive's racks | Doing it twice leaves the same result as doing it once | proposal | B2 |
| 14 | What is a sidecar? | the runner at the archive | A helper who stands at the belt for a room with no window | proposal | B2 |
| 15 | What is a schema? | the label desk | A form pad: this is what a note of this kind should say | proposal | B2 or B4 |
| 16 | What is a single source of truth? | the clock | One bell on the wall, and no private alarms anywhere | proposal | B3 |
| 17 | What is fail-open? | the courier at a shut door | If the dock is shut, the courier turns round and the vendor carries on | proposal | B6 |
| 18 | What is a correlation ID? | the barcode printer at the dock | One barcode per conversation, copied onto every note it causes | proposal | B6 |
| 19 | What is eventual consistency? | the control room window | The window shows the floor a moment late, never in the same instant | proposal | B6 |
| 20 | What is backpressure? | the crew hall's in-hand tray | When the tray is full, the desk stops taking envelopes | proposal | B6 |
| 21 | What is observability? | the control room and the andon light | Working out what happened from the floor, without going in | proposal | B6 |
| 22 | What is a gateway? | the staffing desk | One desk in front of many agencies, trying them in order | proposal | B4 |
| Y | Does a corner shop need a belt? | the Your Warehouse sheet | A small shop with one person at the till does not | proposal | end of each book |

**Reserves** (drafted only if a page asks): container, search by meaning, retrieval, reference not copy, template, registry, back up first, separation of concerns (retired from the first set as too generic).

## "You've already met this" lines

Each modal's third beat names something the reader has probably built. Proposed:

| Concept | Already met as |
|---|---|
| Normalization | Stripe and PayPal both becoming one "payment received" |
| Hook | `addEventListener`; a webhook you register |
| Asking vs announcing | `await fetch()` versus a push notification |
| Bus | a group chat instead of calling each person |
| Stream (log) | a git log, a bank statement |
| Fan-out | one button with several click handlers |
| Event vs command | "the oven beeped" versus "take the cake out" |
| Loose coupling | adding a plugin without editing the app |
| Bookmark | Slack's "New messages" line |
| Retention | "keep my messages for 30 days" |
| Work queue | the ticket machine at a deli counter |
| Acknowledgement | a courier who needs a signature |
| Idempotent | pressing the lift button twice; a signup form that ignores an email it already has |
| Sidecar | a log shipper running beside your app |
| Schema | a form's required fields; TypeScript types |
| Single source of truth | one cron instead of ten |
| Fail-open | an analytics script that fails and the page still loads |
| Correlation ID | an order number repeated through every email |
| Eventual consistency | a like count that catches up a moment later |
| Backpressure | a "429, slow down" |
| Observability | a car dashboard |
| Gateway | a switchboard in front of many lines |

## Evidence

Each row's code evidence is in [`../world/warehouse-bible.md`](../world/warehouse-bible.md): the belt physics table (section 3.2, B1 to B18) and the core cards (section 4.2). A bulb's evidence goes in its own file next to this one, as `normalization.md` does, never in the modal.
