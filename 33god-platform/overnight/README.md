# Overnight: the 33GOD launch page

One night at the company, told by the clock. You leave at 18:02, the company works until 07:41, and the page is that night.

**Live (preview, noindex):** https://33god.delo.sh

- Design system: [33GOD Overnight](https://claude.ai/artifact/3fX6X9vkEHw6tTG9z3DTQN), which extends [33GOD](https://claude.ai/artifact/BujKg4bcBTeuW1b1qwHDRA)
- Experience bible (laws, the original 21 beats, camera, open decisions; the page now has 23, see "Flagships" below): [Overnight: Experience Bible](https://claude.ai/artifact/THg8wjmCVLk5WMFUqGepXu)
- Copy source: [33GOD Landing Page](https://claude.ai/artifact/Liw6BUy95RR77TxhammtPo), `Main`

This is the first full pass: every beat is staged so the whole vision can be judged end to end. The content underneath is not final.

## What lives where

| Path | What it holds | Who edits it |
|---|---|---|
| `site/manifest.json` | The scene manifest. Every word on the page, one record per beat, plus the staged transcript. | Content |
| `site/score.json` | The scroll score: where each beat sits on the scroll (one major per beat), how long each section takes to play (`body.ms`, `pace`), and the set pieces' timelines and story beats (minors). | Design |
| `site/overnight.js` | Staging: the camera, the seating plan, which window is in which state, the set pieces, and the page's own chrome (the elevator gauge, the next-section caret). No copy, no scroll geometry. | Design |
| `site/score.js` | Scroll offset markers: compiles a score, samples it, and says where the stations are, what one move between two of them looks like (`move`), how far through the night you are (`where`, `Score.watch`) and where a half-dissolved state should finish (`seam`). Page-agnostic. | Design |
| `site/dolly.js` | The scroll playhead: spring smoothing, the timed move a keypress plays (one tween drives playhead and scroll), settle glides, cuts for nav jumps. Page-agnostic. | Design |
| `step-probe.py` | Presses Down through the whole night in a real browser and checks the rests, the timing, the stalls, the caret, the gauge and the arbitration rules. | Tooling |
| `site/nights/<date>.json` | A real night: a `33god.night` digest from `waybill night`. `site.night.src` in the manifest picks which one plays. | `waybill night` |
| `site/overnight.css` | Page layout and set-piece styles. Tokens only, no raw colours. | Design |
| `site/ds/tokens.css` | The Overnight tokens, written out from the design system's `tokens.json`, plus the few base 33GOD values the page uses. | Design system first, then here |
| `site/ds/bundle.js`, `site/ds/bundle.css` | The design system's six components (`window.Overnight`), copied unchanged. | Design system only |
| `site/vendor/` | React 18 UMD, vendored so the page has no CDN dependency. | Nobody |

## Changing the words

Edit `site/manifest.json` and refresh. The page fetches it with `no-cache`, and nginx serves the folder from a live bind mount, so there is no build and no deploy step.

Each beat carries design fields (`id`, `time`, `act`, `spectacle`, `camera`, `setPiece`) and content fields (`kicker`, `title`, `body`, `tags`, `staged`, `log`, and the per-beat extras under `copy`). Rewriting copy never moves a scene. Where a beat sits on the scroll is `site/score.json` (below).

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

House rules the test also pins: no string says "fleet" (the FLUME charter bans it; only `copy.quote` may), no leading or trailing space, no double space, no duplicate JSON key.

### The optional `detail` field

Any entry in any list in a beat's `copy` (`departments`, `staff`, `figures`, `parts`, `roles` and any list added later) may carry `detail`: the long form of its short `line` (or `label`). The short text stays on the card; `detail` opens as a popover on hover or keyboard focus (out of flow, so a card never changes size, and it opens upward from the lower half of a list), appears under the nameplate when you hover that component's window in the building, and is listed in full in the log view. Nothing renders unless the field is there, and nothing in `overnight.js` is keyed to a particular list.

### The guard

- A manifest or score that does not parse now shows a readable panel (file, message, line and column, the offending lines with a caret) instead of a blank page. A manifest that parses but has the wrong shape shows a panel too. Saving the fix publishes it.
- `cd 33god-platform && python3 -m pytest tests/test_overnight_site.py` parses every JSON file (duplicate keys fail), checks the manifest's shape, that the score's majors match the beats in order, the budgets above and the house rules. It takes under a second. `OVERNIGHT_LAYOUT=1` also drives the film at three viewports and presses through the whole night (`TestStepping`, at `?pace=0.2`); needs playwright and chromium, about 2.5 minutes. `tests/overnight_score_check.js` (plain node, run from the same file) checks the stations, moves and elevator readout against the real score. `OVERNIGHT_SITE=<dir>` points it at a copy.
- `?view=log` and `?view=film` choose the view (width under 760px and reduced motion still default to the log). `?pace=0.25` plays every move four times faster (see "The pace").
- `site.viewSimulation` ("View as 3D simulation") is a link in the header, next to "View as log", to `site.viewSimulationHref` (`https://manual.delo.sh/sandbox/?walk`: the Factory, a live 3D warehouse of 33GOD, in a new tab). It shows in both views. The header makes room for it by dropping the "In Development" status under 1360px wide and the five nav links under 1210px, so the link is the last thing to go. Under 600px (the phone log view) the header has no room, and the same link sits in the footer. It is the ambient simulation, not a nightly run: `waybill night` writes a `33god.night` digest and the Factory only plays `33god.waybill` files, and no job publishes a nightly one yet. When one exists, point `viewSimulationHref` at it.

## The score: scroll offset markers

`site/score.json` cuts the page's scroll into markers, each with a `start` and an `end`. The format is documented at the top of `site/score.js`, which knows nothing about this page: any scroll-driven page can compile a score.

- **Major**: a section. One per beat here, ids in manifest order (the page refuses a score that does not match). Inside a major the stage is pinned, so every px of scroll between `start` and `end` advances that beat's exhibit. A major has an `in` (an act statement, on beats that open an act), a body (the set piece's own timeline, `q`) and an `out` (the camera travel to the next beat), each with a curve. `start`/`end` are vh from the top of the film, times `scale` (0.8, the old `PACE`). `land` is where a reader who scrubbed into the beat comes to rest, and where a nav link cuts to.
- **Minor**: a timeline inside a major's body, with optional story beats (`beats`, or `steps` for N evenly spaced ones, `"@staff"` style counts read from the copy). A minor is no stop. It is the speed profile of its section: the tween eases into each beat and holds near it (`dwell`) without resting there. Its `curve` shapes the value between two beats (`"smoothstep"`, `"elevator"`, `"cubic-bezier(...)"`, or `{ "in": 0.6, "out": 0.3 }` for how hard it pulls away and how softly it lands). Staging reads thresholds from the score (`SC.minor(...)`, `SC.beatQ(...)`), never copies them, so moving a beat in `score.json` moves what happens there.
- **Scored set pieces**: the staff roll, the loop, the transcript push-in, JEV/voices/dictionary/tickets, the pull-backs into Krebs and the morning, Skillex shipping, the PJangler checklist, the gateway's switch/scout/settle, Heyma's call, the Flume pipeline and the car's standup. Everything else in a beat still scrubs freely off `q`.

## How the night runs

- **Press Down.** One press of Down (also Space, Page Down, or a click on the caret) plays one section: the camera travel out of the one you are in, the act statement if the next one opens an act, and the whole of the next section's exhibit, as one continuous move. When that section's content is done it stops, the caret appears, and nothing happens until you press again. 23 sections, 23 presses, about three minutes. Up, Page Up and Shift+Space go back one section, a little faster. Home and End cut. Nav links cut to a beat's landing; Down then plays the rest of that section.
- **The clock, the camera and the sky are all read off one playhead** (`site/dolly.js`). A move drives the playhead and the scroll position together, so the scrollbar travels with the film. When you scroll instead, a critically damped spring pulls the playhead toward the scroll position, so wheel notches, trackpad flicks and the scrollbar all play as one continuous move that eases in and out. `scroll-probe.py` measures that: 60 notches give 405 moving frames of 407 (it was 60 of 636 before the spring).
- **Scrolling stays free.** Wheel, touch and the scrollbar scrub the film like a video. Stop mid-section and it stays where you stopped: no automatic glide, so no tiny stops. Stop inside a camera travel or an act statement's handover (a half-dissolved state) and the dolly finishes it the way you were going: forward to the next section's landing, or back to the station behind. That is the only automatic move, takes about half a second, and is a rest, not a station: no caret. Any wheel, touch or scrollbar input mid-move hands control straight back at the playhead.
- **A held key plays one section.** Every auto-repeat is swallowed: release and press again. The same key again mid-move fast-forwards what is left once (4x); more presses are ignored, so nothing queues the next section. The other direction mid-move turns around to the station behind. Focus in the briefing form keeps its keys, and Space on a focused button is its click.
- **The elevator** on the left edge is a thin shaft with a small car: 0% at the top floor, 100% at the ground. A floor is a station (the top, then the end of each section; the four act openings have a longer tick). The car's ground bar sits on the building's ground line. It is a `progressbar` (`aria-valuenow`, `aria-valuetext` "Section 7 of 23"), faint, and not shown in the log view or under 900px. It follows the Spruce and Snow themes.
- **The caret** at the bottom centre is a thin, gently bobbing chevron and a real button ("Next section"). It shows only when the film is at rest on a station that has a next one: hidden while moving, while scrubbing between stations and at the very end. It stays on a tablet-width film (760 to 900px, where there is no Down key). It is hidden by opacity, not removed, so a keyboard user who pressed it keeps focus through the move and can press again. It never covers copy (`TestStepping` checks every station at 1280, 1440 and 820 wide). The bob stops under `prefers-reduced-motion`, where a press cuts to the station instead of playing the move.
- `score.js` and `dolly.js` have no dependencies and know nothing about this page. Any score-driven page gets the same: `Score.compile(spec)`, then `Dolly.create({ onFrame, move: score.move, seam: score.seam, origin })` for stepping, `Score.watch(score, cb)` for `{ progress, station, ready, moving }` (the elevator's reading and the "section done" signal), and `dolly.step(dir)` for a button. Details are at the top of each file.
- **The building** is 12 floors of 8 windows. 72 can light, one per first-party component in the registry count. One is yours. 23 stay dark all night, and one of those is the seat Flume fills at 05:12. PJangler builds a 13th floor at 04:12.
- **One cut**, from the building to the car at 07:30. That is also where the theme turns from Spruce to Snow.
- **View as log** shows the same night as one `LogLine` per beat. The page opens there under `prefers-reduced-motion` and on screens narrower than 760px.
- **Crank**: leave the film at rest for 20 seconds and one line appears in the strip under the ground line, beside the caret, where no copy ever sits.
- **Your place is in the URL.** Resting on a station writes the beat to the hash (`#staff`); a nav link or the briefing link does too, and the top clears it. A reload, or a shared `/#staff`, comes back there: the same station if this tab rested on it (kept in `sessionStorage`), else the beat's landing. The browser's own scroll restoration is off (`history.scrollRestoration = 'manual'`) so it does not fight that. Mid-body scrubbing is not saved: the hash is the last place you rested.

## The pace

A **station** is a resting place. There is exactly one per major, where its content is done (the end of its body, before its camera travel out), plus the very top: 24 stations, 23 moves. Nothing is derived by hand; `site/score.json` only says how long a section takes and where nothing happens. A **move** is one press: from the station you are on to the next. `score.move` samples the timeline of that stretch, smooths its speed, ramps it up from rest and down to rest (so every move starts and ends at zero speed, even one that starts mid-section), and hands the dolly one ease. The minors are the speed profile inside it: between two story beats the tween eases (`dwell`), so it slows toward a beat, lingers, and moves on, never stopping.

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

`?pace=0.25` multiplies every time by 0.25 (the tests use 0.2; try 0.8 if the night feels slow). Per section the defaults come to 2.6 to 19.4 seconds (the staff roll is longest, at 0.68s a person; the act statements stand for 2.7s); the whole night is 187 seconds. `node tests/overnight_score_check.js --json` prints the table for any edit.

## Flagships

A beat with `"flagship": true` is a flagship. Flagships are numbered `F-01`, `F-02` … in page order, prefixed to the beat's `kicker`, and `{flagships}` in an interlude kicker becomes their range (`F-01–F-05` today). Adding one is a manifest record plus its set piece; nothing is renumbered by hand.

| # | Beat | Time | Set piece |
|---|---|---|---|
| F-01 | `pjangler` | 04:12 | the 13th floor and its day-one checklist |
| F-02 | `gateway` | 04:37 | the power company: four pools, the router's decision, the nightly free-provider scout |
| F-03 | `heyma` | 04:40 | the audio parts and the translated call |
| F-04 | `flume` | 05:12 | the hire |
| F-05 | `holocene-auto` | 07:30 | the car |

**The gateway beat** sits at 04:37 because that is when the real `aai-free-scout` Candybar job fires (`candybar/deploy/migration/manifests/aai-free-scout/candybar.toml`). The `GATEWAY` window (ground floor) works all beat; the rest of the building stays ambient, which is the point: a pool runs dry and nothing flickers. The card's numbers (112 routes, 43 free models in 13 pools, 7 rungs, 3 roles) are counted from `~/code/client-portal/gateway/ops/routes.json` on 20 Nov 2026; which pool runs dry, and when, is staged and the card says so. Staging (`GW_SWITCH`, `GW_SCOUT`, `GW_METERS`) is in `overnight.js`; every word is in the beat's `copy`. Below 800px of height the card drops its tenancy note and its punch line so it never reaches the header.

## The real night

The page replays a real night of the company: **16–17 Nov 2026, 18:02 to 07:41 EST, 57,875 Bloodbank events from 30 components.** The clock time is the real time, so at 03:12 on the page you are looking at what the company did at 03:12 that night.

- **Working windows are real** in eight beats: the opening building once its windows have come on, the thesis beat (the held building), the numbers beat, and the ambient building in Act IV (staff, pjangler, gateway, heyma, flume, outside each beat's own set piece). A window is working when its component published on the bus in the last three minutes; Hook-hub handler work lights the component it was for. Seats left over after the named ones go to components that worked that night and have no seat of their own (hover shows the registry summary); a first-party Hermes PM desk that worked and has no PM seat gets one (`PM · 33GOD`); seats with no component stay dark. Hover works where the building is at full size (staff, pjangler, gateway, heyma, flume), not in the zoomed-out numbers beat. The film re-renders on a real minute only when that minute flips a window. Act III and every set piece stay staged. The list is `NIGHT_BEATS` in `overnight.js`.
- **The clock's label follows suit**: "Real night · 16–17 Nov 2026" over those eight beats, "A night, staged" everywhere else.
- **The counter under the clock is real** on every beat: events archived before that minute of the real night.
- **The log view** interleaves real lines (blue rule) with the staged beats: per beat, up to three real moments between that beat's time and the next, rare events first.
- **Still staged**: every set piece (the bus, the conference-room transcript, the tickets, the checklists, the car), and the window states those set pieces drive.

Make another night: `waybill night --date 2026-11-16 -o site/nights/` (defaults: last night, 18:02 to 07:41, America/New_York, public profile), then point `site.night.src` at it. `?night=YYYY-MM-DD` plays any file in `site/nights/` without editing the manifest; `?night=staged` turns the replay off. If the file fails to load, the page plays the staged night and says so in the console.

The digest holds producer, event type and local wall-clock minute only, never payloads. Candybar jobs and hook-hub handlers are credited to the component the work was for (client-project jobs stay with Candybar); third-party Hermes desks are aliased (`desk-3`) and message, call and payment event types are counted but never named in the public profile. If the file is malformed or its window misses the film's clock, the page plays the staged night.

## Real versus staged in this pass

| Element | State |
|---|---|
| Component names and their one-liners | Real, from the landing page copy |
| The five counts (72, 12, 214, 299, 1) | Real, stamped 15 Nov 2026 |
| Event subjects | Real, from the Bloodbank contract. Which subject sits on which beat is a first guess and needs a content pass. |
| Clock times, window activity | Real in the eight night beats when a night file loads (see above). Beat times themselves are staged. |
| Event counter under the clock | Real, from the night file |
| Transcript words, speaker names, the translated call | Staged, written for this pass |
| The briefing form | Lights your window and stores nothing. It says so under the field. |

## Not built yet

These wait on the open decisions in the bible: sound and the Vox standup, the one-machine reveal, and a designed phone layout (phones get the log view for now). The real-night replay and the event counter are in (above); "always last night" needs a Candybar job to rebuild the file each morning.

## Preview locally

```bash
cd site && python3 -m http.server 8765   # then open http://localhost:8765
```

## Hosting

`33god-web` is `nginx:alpine` with this `site/` folder bind-mounted read-only, routed by Traefik at `33god.delo.sh`. The stack is `~/docker/stacks/websites/33god/compose.yml`, the same shape as `manual.delo.sh`. The router adds `X-Robots-Tag: noindex, nofollow` while 33GOD is in stealth.
