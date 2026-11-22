# Overnight: the 33GOD front page and component tour

A building with one window per component. Scroll down it, one section at a time, and each department lights up with what it does and a few numbers counted from the real system. The stage is In Development; the page says so and is noindex.

(The folder is still called `overnight/`. It used to tell one night as a story; on 21 Nov 2026 it became a tour, because the story read as a brag reel. Nothing night-shaped is left, and a test keeps it that way.)

**Live (preview, noindex):** https://33god.delo.sh (the front page). The 21-section tour is at https://33god.delo.sh/tour.html.

- Design system: [33GOD Overnight](https://claude.ai/artifact/3fX6X9vkEHw6tTG9z3DTQN), which extends [33GOD](https://claude.ai/artifact/BujKg4bcBTeuW1b1qwHDRA)
- Copy source for the first pass: [33GOD Landing Page](https://claude.ai/artifact/Liw6BUy95RR77TxhammtPo), `Main`. The tour's own copy is `site/manifest.json`; every number in it is counted and dated 21 Nov 2026.

The tour has 21 sections in six parts: Arrival (building, thesis, lobby), The bylaws (org chart, bus, the loop), The platform (clock and records, the agents' desk), The work (PJangler, Flume, Krebs, Pilot, Skillex, the Gateway), The voice (HeyMa, Wax, Voice-ID, Jev, Holocene Auto) and The staff (the roll, and "Watch it work").

## The front page ("Flagships")

`site/index.html` is the front page; the tour that used to be the front page is `site/tour.html` (same scripts, unchanged). The front page picks five flagships and gives each one a set piece: **PJangler** (a crane lifts a building; the 13th floor is the one that gets dropped), **the Gateway** (one door, a pool of subscriptions, metered and free routes), **HeyMa** (transcription, translation and dictation, with a phone frame for the call), **Flume** (the workforce: hire, onboard, review) and **Holocene Auto** (an Android Automotive app in internal testing, in front of a sunrise). Then one band of icon tiles for the org chart, the counts, and the briefing form.

Order on the page: header (mark, flagship nav, one CTA, a five-segment progress strip), hero, five exhibits, the org band, "The building, counted." (five counts, dated 21 Nov 2026), the ask, the footer. The hero and the footer link to the tour ("Take the tour", `site.viewFilm`). Old tour links keep working: `index.html?view=` or `?pace=` redirects at once (an inline script), and `index.html#<beat-id>` redirects once the manifest is loaded, both to `tour.html` with the same query and hash. Front anchors are `top`, `flagships`, `f-<id>`, `org-band`, `counts` and `briefing`; a test keeps them from ever equalling a tour beat id.

**Every word is in `manifest.json`'s top-level `front` record**, plus the org band's department names and lines, which it reads from the tour's `org-chart` beat so the two cannot drift. `front.js` fetches the manifest and renders everything from it; there is no copy in `index.html`, `front.js` or `front.css`, except the `<noscript>` line. The five flagship accents are `:root` tokens at the top of `front.css` (a dark and a morning variant each); they go upstream into the design system's `tokens.json`, and then out of `front.css`. No raw colours anywhere else.

What was borrowed from the two other directions (and what was not):

| Graft | Became |
|---|---|
| Tour link | "Take the tour" in the hero (a text link beside the one button) and in the footer |
| Night-lite illustration | the PJangler crane and 13th floor, the sunrise behind the Holocene Auto screen, a skyline-and-stars strip along the foot of each dark stage (in flow, never behind text), a phone frame for the HeyMa call |
| Showroom stats row | four registry counts with icons in the hero (components, domains, event schemas, connections); the closing band shows all five, with "1 human" |
| Showroom "Next F-0n" | a "Next: name" link with three step markers on every exhibit |
| Org chart icons | one band of 12 department tiles in one neutral family colour, with one ochre "You" row, between Holocene Auto and the counts |
| Not borrowed | hover-only content, six department colours, the bento grid |

### The phone is the binding viewport

The page is designed at 360x780 first (the design range is 360 to 430). Rules, each tested in `TestFront`:

- **Pin only if it fits.** An exhibit is pinned (sticky, three beats driven by scroll) only when its whole stage fits the small-viewport height minus the header, measured in JS (`measure()`, re-run on resize, on fonts loading and on rotation). Otherwise it flows, and its three beats advance off where the piece sits in the viewport. Nothing pins on a phone; at 820x1180, 1280x720, 1440x900 and 1920x1080 the exhibits that fit pin; HeyMa flows at 1024x768 (it needs 835px of 704).
- **Header:** the mark, a horizontally scrollable icon-only flagship nav (the active item scrolls into view), a 40px mail-icon CTA, and the progress strip. The wordmark appears from 400px, the CTA label ("Briefing") from 600px, short nav names from 900px, full names from 1180px.
- **Hero:** one column; the flagship index is a 2-column grid of tiles (Holocene Auto spans both), never five across below 760px; one primary button per screen, the tour as a text link.
- **Set pieces adapt to their own width**, not the viewport's (`@container piece`), so a pinned panel and a flowing panel use the same layout rules.
- **A 14px floor below 760px.** Nothing a person reads is under 14px on a phone (`--fs-s` in the phone block at the end of `front.css`); tap targets are 44px (Next links, footer links, the brand). Only the step bars and star dots are smaller. On a phone each exhibit reads badge, headline, line, the piece, the three bullets, Next; the gateway stats are 2x2, the HeyMa part cards are compact, the org tiles are 2 up (3 from 500px), and the closing band shows only "1 human" (the four registry counts are in the hero already).
- No horizontal scroll, nothing under the fixed header, nothing cut off; `prefers-reduced-motion` never pins and shows each piece's final state; a reload restores the scroll position.

### The briefing form on the front page

It is the same sign-up as the tour's: `forms.js` posts `briefing` to `/_forms/briefing` (see "The briefing form" below), with the honeypot. The words under and after it (`note`, `done`, `sending`, `error`) are tested to equal the tour's `ask` copy, so the two forms promise the same thing.

### Front copy budgets (measured at 360x780)

`tests/test_overnight_site.py` has one budget per front slot (`FRONT_BUDGETS`, with the reason beside each). The ones that bind:

| Slot | Budget | Why |
|---|---|---|
| `hero.title` / `titleTurn` | 16 chars each | the h1 is 41px, one line each in 328px |
| `hero.line` | 160 chars | 4 lines; 5 pushes the tiles off the first screen |
| `hero.primary` / `hero.tour` | 22 / 18 chars | one line each |
| `stat.short` / `stat.n` | 14 / 3 chars | the 2-up fact cell is about 100px |
| `flagship.name` / `tag` | 14 / 34 chars | the tile is about 130px wide |
| `flagship.headline` / `headlineTurn` / `line` | 16 / 44 / 110 chars | 33px h2, 17px lede |
| `chip.text` | 34 chars | one line beside a 36px icon |
| `next.name` | 14 chars | "Next: name" beside the three markers |
| `gw.say`, `hm.part.line`, `fl.role.line` | 90 / 44 / 56 chars | the panel cells at their narrowest |
| `org.name` / `org.dept` | 14 / 24 chars | the tile is 104px wide |
| `well.title` / `ask.title` | 28 chars | two lines |

Tests: `test_front_record_has_every_slot` (the record has every slot the page reads), `test_front_house_rules` and `test_front_has_no_night_clock` (no "stealth", no "fleet", no night-shaped words, figures dated, staged pieces labelled), `test_front_files_and_links`, and `TestFront` (browser, `OVERNIGHT_LAYOUT=1`).

## What lives where

The tour and the front page share the manifest, the tokens and the design-system bundle. Front-only files:

| Path | What it holds | Who edits it |
|---|---|---|
| `site/index.html` | The front page shell: head, the tour redirect, the icon sprite, `#front`. | Design |
| `site/front.js` | Renders the front page from `manifest.json`'s `front` record; the drawn art, the pin-if-it-fits measuring, the scroll drivers. Plain JS, no libraries. | Design |
| `site/front.css` | Front page styles and the flagship accent tokens. | Design |
| `site/tour.html` | The 21-section tour (the old front page). | Design |

| Path | What it holds | Who edits it |
|---|---|---|
| `site/manifest.json` | The scene manifest. Every word on the page, one record per beat, plus the staged transcript. | Content |
| `site/score.json` | The scroll score: where each beat sits on the scroll (one major per beat), how long each section takes to play (`body.ms`, `pace`), and the set pieces' timelines and story beats (minors). | Design |
| `site/overnight.js` | Staging: the camera, the seating plan, which window is in which state, the set pieces, and the page's own chrome (the elevator gauge, the next-section caret). No copy, no scroll geometry. | Design |
| `site/score.js` | Scroll offset markers: compiles a score, samples it, and says where the stations are, what one move between two of them looks like (`move`), where you are in the tour (`where`, `Score.watch`) and where a half-dissolved state should finish (`seam`). Page-agnostic. | Design |
| `site/dolly.js` | The scroll playhead: spring smoothing, the timed move a keypress plays (one tween drives playhead and scroll), settle glides, cuts for nav jumps. Page-agnostic. | Design |
| `step-probe.py` | Presses Down through the whole tour (`tour.html`) in a real browser and checks the rests, the timing, the stalls, the caret, the gauge and the arbitration rules. | Tooling |
| `site/overnight.css` | Page layout and set-piece styles. Tokens only, no raw colours. | Design |
| `site/ds/tokens.css` | The Overnight tokens, written out from the design system's `tokens.json`, plus the few base 33GOD values the page uses. | Design system first, then here |
| `site/ds/bundle.js`, `site/ds/bundle.css` | The design system's six components (`window.Overnight`), copied unchanged. | Design system only |
| `site/vendor/` | React 18 UMD, vendored so the page has no CDN dependency. | Nobody |

## Changing the words

Edit `site/manifest.json` and refresh. The page fetches it with `no-cache`, and nginx serves the folder from a live bind mount, so there is no build and no deploy step.

Each beat carries design fields (`id`, `act`, `where`, `setPiece`, `covers`) and content fields (`kicker`, `title`, `body`, `tags`, `staged`, `log`, and the per-beat extras under `copy`). `where` is the place name the header shows over “n of N”. `covers` names the components the section is about, by id in `components/<id>.yaml`; a test fails on an id with no record. `staged` is true on illustration (the badge says so); a section with counted numbers says “Real figures · 21 Nov 2026”. Rewriting copy never moves a scene. Where a beat sits on the scroll is `site/score.json` (below).

### Copy budgets

Copy that does not fit its slot pushes the layout under the fixed header (this is how the page broke after the long hand edit). Each budget below was measured in a browser at 1280x720, the binding viewport (stage body is the viewport minus the 81px header). `tests/test_overnight_site.py` enforces them and its failure message names the slot, the count and the measurement.

| Slot | Budget (target) | Why |
|---|---|---|
| `premise.body` (hero lede) | 540 chars, 90 words (aim 60) | the hero column is 561px of 591 at 90 words |
| `premise.title` / `titleTurn` | 14 / 24 chars | keeps the h1 to two lines |
| `premise.kicker` / `copy.secondary` | 80 / 60 chars | one line each |
| caption `body` (every other beat, `thesis` included) | 430 chars, 75 words (aim 55) | 60px clear of the header with a 3-line title |
| `org-chart.body` (shares its column with the quote) | 380 chars, 65 words | quote + source take 120px |
| caption `body` + `aside` | 622 chars | the gateway is the tightest caption shipped |
| caption `kicker` / `title` | 64 / 62 chars | one line / three lines at most |
| `figures[].label` / `n` / `numbers.stamp` | 90 (aim 64) / 3 / 90 chars | the directory column is 187px wide |
| `departments[].line` and `staff[].line` | 80 chars (aim 64) | the cell is 204px, the nameplate 240px; CSS clamps a line to 3 lines |
| `dept` label / entry `name` | 24 / 20 chars | one line |
| `copy.quote` / `quoteSource` | 110 / 80 chars | two lines. Open and close it with curly quotes. |
| `detail` (any entry) | 280 chars (aim 220) | the popover is about 220px wide |
| `site.nav` | 5 labels, 14 chars each | a 6th wraps the header |
| `where` (every beat) | 24 chars | the header's place name |
| department card `figures[].n` / `label` | 4 / 64 chars | numeral column is 62px at 26px type; the label is two lines |
| department card `members[].line` / `role` | 80 / 24 chars | clamped to 2 lines |
| department card `events[].type` / `stamp` | 48 / 90 chars | one mono line / two lines |
| `ask.copy.watch.note` | 200 chars | the line under the 3D Factory button |

House rules the test also pins: no string, file or comment says “stealth” and nothing refers to a night file (`site/nights/` is gone); no string says "fleet" (the FLUME charter bans it; only `copy.quote` may), no leading or trailing space, no double space, no duplicate JSON key.

### The department card

`department.card` is the generic exhibit: any component or group of components gets a section by adding a manifest record and a score major, with no change to `overnight.js`. The record's `copy` holds `exhibit {seats, components, live}` (the window names that work during the section, the registry ids, and whether the figures are counted), `members` (name, role, line), `figures` (n, label, detail), `eventsTitle`, `events` (type, n) and `stamp`. Every other window in the building is dark in an exhibit section; the building leans toward the focus floor. Clock and records and the agents' desk use it today. Bespoke exhibits (the directory, org chart, bus, loop, checklist, pipeline, gateway card, glass) are the same shape one level down: data in `copy`, staging in `overnight.js`.

### The optional `detail` field

Any entry in any list in a beat's `copy` (`departments`, `staff`, `figures`, `parts`, `roles` and any list added later) may carry `detail`: the long form of its short `line` (or `label`). The short text stays on the card; `detail` opens as a popover on hover or keyboard focus (out of flow, so a card never changes size, and it opens upward from the lower half of a list), appears under the nameplate when you hover that component's window in the building, and is listed in full in the log view. Nothing renders unless the field is there, and nothing in `overnight.js` is keyed to a particular list.

### The guard

- A manifest or score that does not parse now shows a readable panel (file, message, line and column, the offending lines with a caret) instead of a blank page. A manifest that parses but has the wrong shape shows a panel too. Saving the fix publishes it.
- `cd 33god-platform && python3 -m pytest tests/test_overnight_site.py` parses every JSON file (duplicate keys fail), checks the manifest's shape, that the score's majors match the beats in order, the budgets above and the house rules. It takes under a second. `OVERNIGHT_LAYOUT=1` also drives the film at three viewports and presses through the whole tour (`TestStepping`, at `?pace=0.2`); needs playwright and chromium, about 2.5 minutes. `tests/overnight_score_check.js` (plain node, run from the same file) checks the stations, moves and elevator readout against the real score. `OVERNIGHT_SITE=<dir>` points it at a copy.
- `?view=log` and `?view=film` choose the view. The list view is the tour as a directory: one entry per section, with its real event subjects and no camera. (width under 760px and reduced motion still default to the log). `?pace=0.25` plays every move four times faster (see "The pace").
- `site.viewSimulation` ("View as 3D simulation") is a link in the header, next to "View as log", to `site.viewSimulationHref` (`https://manual.delo.sh/sandbox/?walk`: the Factory, a live 3D warehouse of 33GOD, in a new tab). It shows in both views. The header makes room for it by dropping the "In Development" status under 1360px wide and the five nav links under 1210px, so the link is the last thing to go. Under 600px (the phone log view) the header has no room, and the same link sits in the footer. The link points at a published `33god.waybill` of the real archive of 20 Nov 2026 (81,003 events from 41 components); to play another day, publish a new waybill and change the one href. The last section's “Open the 3D Factory” button and the hero's second link use the same href (`{site.viewSimulationHref}` in the copy).

## The score: scroll offset markers

`site/score.json` cuts the page's scroll into markers, each with a `start` and an `end`. The format is documented at the top of `site/score.js`, which knows nothing about this page: any scroll-driven page can compile a score.

- **Major**: a section. One per beat here, ids in manifest order (the page refuses a score that does not match). Inside a major the stage is pinned, so every px of scroll between `start` and `end` advances that beat's exhibit. A major has an `in` (an act statement, on beats that open an act), a body (the set piece's own timeline, `q`) and an `out` (the camera travel to the next beat), each with a curve. `start`/`end` are vh from the top of the film, times `scale` (0.8, the old `PACE`). `land` is where a reader who scrubbed into the beat comes to rest, and where a nav link cuts to.
- **Minor**: a timeline inside a major's body, with optional story beats (`beats`, or `steps` for N evenly spaced ones, `"@staff"` style counts read from the copy). A minor is no stop. It is the speed profile of its section: the tween eases into each beat and holds near it (`dwell`) without resting there. Its `curve` shapes the value between two beats (`"smoothstep"`, `"elevator"`, `"cubic-bezier(...)"`, or `{ "in": 0.6, "out": 0.3 }` for how hard it pulls away and how softly it lands). Staging reads thresholds from the score (`SC.minor(...)`, `SC.beatQ(...)`), never copies them, so moving a beat in `score.json` moves what happens there.
- **Scored set pieces**: the staff roll, the loop, the transcript glass (Pilot's tickets, Wax's push-in, Voice-ID's speakers, Jev's judgments), Skillex shipping, the PJangler checklist, the gateway's switch and scout, HeyMa's call, the Flume pipeline and the car's standup. Everything else in a beat still scrubs freely off `q`.

## How the tour runs

- **Press Down.** One press of Down (also Space, Page Down, or a click on the caret) plays one section: the camera travel out of the one you are in, the act statement if the next one opens an act, and the whole of the next section's exhibit, as one continuous move. When that section's content is done it stops, the caret appears, and nothing happens until you press again. 21 sections, 21 presses, about two and a half minutes. Up, Page Up and Shift+Space go back one section, a little faster. Home and End cut. Nav links cut to a beat's landing; Down then plays the rest of that section.
- **The camera and every exhibit are read off one playhead** (`site/dolly.js`). A move drives the playhead and the scroll position together, so the scrollbar travels with the film. When you scroll instead, a critically damped spring pulls the playhead toward the scroll position, so wheel notches, trackpad flicks and the scrollbar all play as one continuous move that eases in and out. `scroll-probe.py` measures that: 60 notches give 405 moving frames of 407 (it was 60 of 636 before the spring).
- **Scrolling stays free.** Wheel, touch and the scrollbar scrub the film like a video. Stop mid-section and it stays where you stopped: no automatic glide, so no tiny stops. Stop inside a camera travel or an act statement's handover (a half-dissolved state) and the dolly finishes it the way you were going: forward to the next section's landing, or back to the station behind. That is the only automatic move, takes about half a second, and is a rest, not a station: no caret. Any wheel, touch or scrollbar input mid-move hands control straight back at the playhead.
- **A held key plays one section.** Every auto-repeat is swallowed: release and press again. The same key again mid-move fast-forwards what is left once (4x); more presses are ignored, so nothing queues the next section. The other direction mid-move turns around to the station behind. Focus in the briefing form keeps its keys, and Space on a focused button is its click.
- **The elevator** on the left edge is a thin shaft with a small car: 0% at the top floor, 100% at the ground. A floor is a station (the top, then the end of each section; the four part openings have a longer tick). The car's ground bar sits on the building's ground line. It is a `progressbar` (`aria-valuenow`, `aria-valuetext` "Section 7 of 22"), faint, and not shown in the list view or under 900px.
- **The caret** at the bottom centre is a thin, gently bobbing chevron and a real button ("Next section"). It shows only when the film is at rest on a station that has a next one: hidden while moving, while scrubbing between stations and at the very end. It stays on a tablet-width film (760 to 900px, where there is no Down key). It is hidden by opacity, not removed, so a keyboard user who pressed it keeps focus through the move and can press again. It never covers copy (`TestStepping` checks every station at 1280, 1440 and 820 wide). The bob stops under `prefers-reduced-motion`, where a press cuts to the station instead of playing the move.
- `score.js` and `dolly.js` have no dependencies and know nothing about this page. Any score-driven page gets the same: `Score.compile(spec)`, then `Dolly.create({ onFrame, move: score.move, seam: score.seam, origin })` for stepping, `Score.watch(score, cb)` for `{ progress, station, ready, moving }` (the elevator's reading and the "section done" signal), and `dolly.step(dir)` for a button. Details are at the top of each file.
- **The building** is 12 floors of 8 windows: 96 seats. 80 are first-party components in the registry count (21 Nov 2026), one is yours and one is the seat Flume fills, which leaves 14 dark. PJangler builds a 13th floor. In an exhibit section the focus windows work and the rest are dark; elsewhere the building is lit.
- **One cut**, from the building to the car, at Holocene Auto.
- **Read as list** shows the same tour as one directory entry per beat. The page opens there under `prefers-reduced-motion` and on screens narrower than 760px.
- **Crank**: leave the film at rest for 20 seconds and one line appears in the strip under the ground line, beside the caret, where no copy ever sits.
- **Your place is in the URL.** Resting on a station writes the beat to the hash (`#pjangler`); a nav link or the briefing link does too, and the top clears it. A reload, or a shared `/#pjangler`, comes back there: the same station if this tab rested on it (kept in `sessionStorage`), else the beat's landing. The browser's own scroll restoration is off (`history.scrollRestoration = 'manual'`) so it does not fight that. Mid-body scrubbing is not saved: the hash is the last place you rested.

## The pace

A **station** is a resting place. There is exactly one per major, where its content is done (the end of its body, before its camera travel out), plus the very top: 22 stations, 21 moves. Nothing is derived by hand; `site/score.json` only says how long a section takes and where nothing happens. A **move** is one press: from the station you are on to the next. `score.move` samples the timeline of that stretch, smooths its speed, ramps it up from rest and down to rest (so every move starts and ends at zero speed, even one that starts mid-section), and hands the dolly one ease. The minors are the speed profile inside it: between two story beats the tween eases (`dwell`), so it slows toward a beat, lingers, and moves on, never stopping.

Every field is optional; units are milliseconds unless it says a share. A field on a major overrides the same one under `defaults`.

| Field | Meaning | Default |
|---|---|---|
| `defaults.body.ms`, major `body.ms` | How long the section's body (its exhibit) takes. Raised to fit if a stepped minor would get under `perStep` ms a step. | 5000 |
| `defaults.body.perStep` | Floor for a stepped minor: `steps x perStep` ms. Adding a staff entry never turns the roll into a blur. | 650 |
| `body.play` | `["30%", "95%"]`: the share of the body in which the exhibit really changes. Before and after it the tween rushes (`pace.rush` x), so dead air is not played. Measured per exhibit; re-check it if you re-time an `rv()` in `overnight.js`. | whole body |
| `out.ms` | The camera travel into the next section, when stepping. Eased as the travel's `timing`, else linear if its `curve` already shapes the picture (so it is not eased twice), else smoothstep. | 1400 |
| `out.settleMs` | The glide when a reader stops inside that travel (not a step). | 300 + 500 per screen |
| `in.ms`, `in.hold` | An act statement: the time from its landing to the start of the body, and how long the statement stands still to be read. The hold is time inside a move, not a stop. | 900, 1800 |
| minor `dwell` | 0 to 1: how hard the tween eases into and out of each beat (speed at a beat is `1 - dwell` of the average). 0 where the minor's own `curve` already shapes the value. | `pace.dwell` (0.5) |
| minor `timing` | A curve for the stretch between two beats, instead of `dwell`. | |
| minor `pace: false` | The minor adds no beats to the profile (the glass, a window opening). Replaces `glide: false`. | |
| `pace.back` | A move back takes this share of the forward time. | 0.55 |
| `pace.launch`, `pace.settle`, `pace.smooth` | Ramp up, ramp down, and the window that smooths the speed, in ms. | 280, 420, 200 |
| `pace.rush` | Speed through a body's dead stretches. | 5 |
| `pace.reach` | Share of the viewport height within which you count as being on a station. | 0.03 |
| `pace.min` | No move is shorter than this. | 450 |

`?pace=0.25` multiplies every time by 0.25 (the tests use 0.2; try 0.8 if the tour feels slow). Per section the defaults come to 2.6 to 16.4 seconds (the staff roll is longest, at 0.68s a person; the part statements stand for 2.7s); the whole tour is about 158 seconds. `node tests/overnight_score_check.js --json` prints the table for any edit.

## Real versus illustrated

| Element | State |
|---|---|
| Component names and their one-liners | Real, from the registry (`33god-platform/components/*.yaml`) |
| The lobby numbers (80, 13, 226, 300, 1) | Real, counted 21 Nov 2026; each carries its source in `detail` |
| Department card figures and event counts | Real, counted 21 Nov 2026 over the 7 days to that date; the card's stamp says so |
| Event subjects | Real, from the Bloodbank contract |
| Window activity in the building | Illustration. Which windows light for a section is staged. |
| Transcript words, speaker names, the translated call | Illustration, written for the page, and the badge says so |
| The Gateway card's dry pool and new pool | Illustration (the router, roles, pools and counts are real; which pool runs dry is staged) |
| The briefing form | Lights your window and stores nothing. It says so under the field. |
| “Open the 3D Factory” | The real archive of 20 Nov 2026, played in the Factory at `manual.delo.sh` |

Counting rule: a number that is not in the repo or a dated query does not go on the page. Re-count and re-date a figure when you touch it.

## Not built yet

Sound. The tour (`tour.html`) still has no designed phone layout (phones get its list view); the front page is phone-first. Keyboard stepping per flagship (Down jumps a beat) is not built on the front page.

## Preview locally

```bash
cd site && python3 -m http.server 8765   # then open http://localhost:8765
```

## Hosting

`33god-web` is `nginx:alpine` with this `site/` folder bind-mounted read-only, routed by Traefik at `33god.delo.sh`. The stack is `~/docker/stacks/websites/33god/compose.yml`, the same shape as `manual.delo.sh`. The router adds `X-Robots-Tag: noindex, nofollow` while 33GOD is In Development.

## The briefing form

"Request a briefing" is a real sign-up. `site/forms.js` posts it to `/_forms/briefing` on the page's own origin; Traefik sends `/_forms/*` on every `*.delo.sh` host to the one `form-intake` service (`33god-platform/form-intake`, README there), which stores the address in SQLite and then publishes `bloodbank.messaging.webform.received` (the ntfy router pushes it). Read the sign-ups with `python3 33god-platform/form-intake/form_intake.py list --form briefing`. Any other page gets a form the same way: load `forms.js` and call `G33Forms.submit('<form>', {email: ...})`.
