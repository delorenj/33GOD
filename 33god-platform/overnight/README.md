# Overnight: the 33GOD launch page

One night at the company, told by the clock. You leave at 18:02, the company works until 07:41, and the page is that night.

**Live (preview, noindex):** https://33god.delo.sh

- Design system: [33GOD Overnight](https://claude.ai/artifact/3fX6X9vkEHw6tTG9z3DTQN), which extends [33GOD](https://claude.ai/artifact/BujKg4bcBTeuW1b1qwHDRA)
- Experience bible (laws, the original 21 beats, camera, open decisions; the page now has 22, see "Flagships" below): [Overnight: Experience Bible](https://claude.ai/artifact/THg8wjmCVLk5WMFUqGepXu)
- Copy source: [33GOD Landing Page](https://claude.ai/artifact/Liw6BUy95RR77TxhammtPo), `Main`

This is the first full pass: every beat is staged so the whole vision can be judged end to end. The content underneath is not final.

## What lives where

| Path | What it holds | Who edits it |
|---|---|---|
| `site/manifest.json` | The scene manifest. Every word on the page, one record per beat, plus the staged transcript. | Content |
| `site/score.json` | The scroll score: where each beat sits on the scroll (one major per beat), and the set pieces' timelines and story beats (minors). | Design |
| `site/overnight.js` | Staging: the camera, the seating plan, which window is in which state, the set pieces. No copy, no scroll geometry. | Design |
| `site/score.js` | Scroll offset markers: compiles a score, samples it, and says where the glides and stops are. Page-agnostic. | Design |
| `site/dolly.js` | The scroll playhead: spring smoothing, timed glides, keyboard stepping, cuts for nav jumps. Page-agnostic. | Design |
| `site/nights/<date>.json` | A real night: a `33god.night` digest from `waybill night`. `site.night.src` in the manifest picks which one plays. | `waybill night` |
| `site/overnight.css` | Page layout and set-piece styles. Tokens only, no raw colours. | Design |
| `site/ds/tokens.css` | The Overnight tokens, written out from the design system's `tokens.json`, plus the few base 33GOD values the page uses. | Design system first, then here |
| `site/ds/bundle.js`, `site/ds/bundle.css` | The design system's six components (`window.Overnight`), copied unchanged. | Design system only |
| `site/vendor/` | React 18 UMD, vendored so the page has no CDN dependency. | Nobody |

## Changing the words

Edit `site/manifest.json` and refresh. The page fetches it with `no-cache`, and nginx serves the folder from a live bind mount, so there is no build and no deploy step.

Each beat carries design fields (`id`, `time`, `act`, `spectacle`, `camera`, `setPiece`) and content fields (`kicker`, `title`, `body`, `tags`, `staged`, `log`, and the per-beat extras under `copy`). Rewriting copy never moves a scene. Where a beat sits on the scroll is `site/score.json` (below).

## The score: scroll offset markers

`site/score.json` cuts the page's scroll into markers, each with a `start` and an `end`. The format is documented at the top of `site/score.js`, which knows nothing about this page: any scroll-driven page can compile a score.

- **Major**: a section. One per beat here, ids in manifest order (the page refuses a score that does not match). Inside a major the stage is pinned, so every px of scroll between `start` and `end` advances that beat's exhibit. A major has an `in` (an act statement, on beats that open an act), a body (the set piece's own timeline, `q`) and an `out` (the camera travel to the next beat), each with a curve. `start`/`end` are vh from the top of the film, times `scale` (0.8, the old `PACE`). `land` is where a reader arriving from the beat before comes to rest.
- **Minor**: a timeline inside a major's body, with optional story beats (`beats`, or `steps` for N evenly spaced ones, `"@staff"` style counts read from the copy). Its `curve` shapes each stretch between two stops (`"smoothstep"`, `"elevator"`, `"cubic-bezier(...)"`, or `{ "in": 0.6, "out": 0.3 }` for how hard it pulls away and how softly it lands). Staging reads thresholds from the score (`SC.minor(...)`, `SC.beatQ(...)`), never copies them, so moving a beat in `score.json` moves what happens there.
- **Scored set pieces**: the staff roll, the loop, the transcript push-in, JEV/voices/dictionary/tickets, the pull-backs into Krebs and the morning, Skillex shipping, the PJangler checklist, the gateway's switch/scout/settle, Heyma's call, the Flume pipeline and the car's standup. Everything else in a beat still scrubs freely off `q`.

## How the night runs

- **Scroll is the dolly.** Each beat holds for 72% of its length, then travels to the next (the defaults in `score.json`). The clock, the camera and the sky are all read off one playhead, and the playhead only ever chases the scroll position.
- **The playhead is sprung** (`site/dolly.js`). A critically damped spring pulls it toward the scroll position every frame, so wheel notches, page-down and trackpad flicks all play as one continuous move that eases in and out. Every camera travel is smoothstepped too, so no move starts or stops at full speed. Before this, a mouse wheel played the night as a slideshow: 60 notches gave 60 frames of motion out of 636. `scroll-probe.py` measures it: now 409 of 412 frames move.
- **Seams finish themselves.** A seam (a glide) is a stretch between two stops: a camera travel with its caption crossfade, an act's statement handing over to the beat's words, or the stretch between two story beats of a minor. Stop scrolling inside one and the dolly plays on to the next stop the way you were going, as one timed move along the stretch's curve (300ms plus 500ms a screen unless the score says otherwise). Any scroll input mid-glide hands control straight back. The score derives every glide and stop from its markers.
- **The keyboard steps through the night.** Space, Page Down and the down arrow glide to the next stop; Shift+Space, Page Up and the up arrow to the one before. Home and End still cut. Focus in the briefing form keeps its keys.
- `dolly.js` has no dependencies and knows nothing about this page. Any scroll-driven page can use it: `Dolly.create({ onFrame, seam, stop, origin })` (`seam` and `stop` straight from a compiled score), then `dolly.jump(px)` for nav links, which cut instead of gliding through the whole night. Nav links land on the beat's `land` stop.
- **The building** is 12 floors of 8 windows. 72 can light, one per first-party component in the registry count. One is yours. 23 stay dark all night, and one of those is the seat Flume fills at 05:12. PJangler builds a 13th floor at 04:12.
- **One cut**, from the building to the car at 07:30. That is also where the theme turns from Spruce to Snow.
- **View as log** shows the same night as one `LogLine` per beat. The page opens there under `prefers-reduced-motion` and on screens narrower than 760px.
- **Crank**: stop scrolling for 20 seconds and one line appears.

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

- **Working windows are real** in seven beats: the opening building once its windows have come on, the numbers beat, and the ambient building in Act IV (staff, pjangler, gateway, heyma, flume, outside each beat's own set piece). A window is working when its component published on the bus in the last three minutes; Hook-hub handler work lights the component it was for. Seats left over after the named ones go to components that worked that night and have no seat of their own (hover shows the registry summary); a first-party Hermes PM desk that worked and has no PM seat gets one (`PM · 33GOD`); seats with no component stay dark. Hover works where the building is at full size (staff, pjangler, gateway, heyma, flume), not in the zoomed-out numbers beat. The film re-renders on a real minute only when that minute flips a window. Act III and every set piece stay staged. The list is `NIGHT_BEATS` in `overnight.js`.
- **The clock's label follows suit**: "Real night · 16–17 Nov 2026" over those seven beats, "A night, staged" everywhere else.
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
| Clock times, window activity | Real in the seven night beats when a night file loads (see above). Beat times themselves are staged. |
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
