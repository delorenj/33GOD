# Overnight: the 33GOD launch page

One night at the company, told by the clock. You leave at 18:02, the company works until 07:41, and the page is that night.

**Live (preview, noindex):** https://33god.delo.sh

- Design system: [33GOD Overnight](https://claude.ai/artifact/3fX6X9vkEHw6tTG9z3DTQN), which extends [33GOD](https://claude.ai/artifact/BujKg4bcBTeuW1b1qwHDRA)
- Experience bible (laws, the 21 beats, camera, open decisions): [Overnight: Experience Bible](https://claude.ai/artifact/THg8wjmCVLk5WMFUqGepXu)
- Copy source: [33GOD Landing Page](https://claude.ai/artifact/Liw6BUy95RR77TxhammtPo), `Main`

This is the first full pass: every beat is staged so the whole vision can be judged end to end. The content underneath is not final.

## What lives where

| Path | What it holds | Who edits it |
|---|---|---|
| `site/manifest.json` | The scene manifest. Every word on the page, one record per beat, plus the staged transcript. | Content |
| `site/overnight.js` | Staging: the scroll dolly, the camera, the seating plan, which window is in which state, the set pieces. No copy. | Design |
| `site/dolly.js` | The scroll playhead: spring smoothing, cuts for nav jumps, seam settling. Page-agnostic. | Design |
| `site/nights/<date>.json` | A real night: a `33god.night` digest from `waybill night`. `site.night.src` in the manifest picks which one plays. | `waybill night` |
| `site/overnight.css` | Page layout and set-piece styles. Tokens only, no raw colours. | Design |
| `site/ds/tokens.css` | The Overnight tokens, written out from the design system's `tokens.json`, plus the few base 33GOD values the page uses. | Design system first, then here |
| `site/ds/bundle.js`, `site/ds/bundle.css` | The design system's six components (`window.Overnight`), copied unchanged. | Design system only |
| `site/vendor/` | React 18 UMD, vendored so the page has no CDN dependency. | Nobody |

## Changing the words

Edit `site/manifest.json` and refresh. The page fetches it with `no-cache`, and nginx serves the folder from a live bind mount, so there is no build and no deploy step.

Each beat carries design fields (`id`, `time`, `act`, `spectacle`, `camera`, `setPiece`, `len`) and content fields (`kicker`, `title`, `body`, `tags`, `staged`, `log`, and the per-beat extras under `copy`). Rewriting copy never moves a scene. `len` is the beat's scroll length in vh; `PACE` in `overnight.js` scales all of them at once.

## How the night runs

- **Scroll is the dolly.** Each beat holds for 72% of its length, then travels to the next. The clock, the camera and the sky are all read off one playhead, and the playhead only ever chases the scroll position.
- **The playhead is sprung** (`site/dolly.js`). A critically damped spring pulls it toward the scroll position every frame, so wheel notches, page-down and trackpad flicks all play as one continuous move that eases in and out. Every camera travel is smoothstepped too, so no move starts or stops at full speed. Before this, a mouse wheel played the night as a slideshow: 60 notches gave 60 frames of motion out of 636. `scroll-probe.py` measures it: now 409 of 412 frames move.
- **Seams finish themselves.** A seam is a stretch between two rest states: a camera travel with its caption crossfade, or an act's statement handing over to the beat's words. Stop scrolling inside one and the dolly glides to the nearer rest point, leaning the way you were going. `seam()` in `overnight.js` defines them; rest points sit where the arriving words are fully up.
- `dolly.js` has no dependencies and knows nothing about this page. Any scroll-driven page can use it: `Dolly.create({ onFrame, seam, origin })`, then `dolly.jump(px)` for nav links, which cut instead of gliding through the whole night.
- **The building** is 12 floors of 8 windows. 72 can light, one per first-party component in the registry count. One is yours. 23 stay dark all night, and one of those is the seat Flume fills at 05:12. PJangler builds a 13th floor at 04:12.
- **One cut**, from the building to the car at 07:30. That is also where the theme turns from Spruce to Snow.
- **View as log** shows the same night as one `LogLine` per beat. The page opens there under `prefers-reduced-motion` and on screens narrower than 760px.
- **Crank**: stop scrolling for 20 seconds and one line appears.

## The real night

The page replays a real night of the company: **16–17 Nov 2026, 18:02 to 07:41 EST, 57,875 Bloodbank events from 30 components.** The clock time is the real time, so at 03:12 on the page you are looking at what the company did at 03:12 that night.

- **Working windows are real** in six beats: the opening building once its windows have come on, the numbers beat, and the ambient building in Act IV (staff, pjangler, heyma, flume, outside each beat's own set piece). A window is working when its component published on the bus in the last three minutes; Hook-hub handler work lights the component it was for. Seats left over after the named ones go to components that worked that night and have no seat of their own (hover shows the registry summary); a first-party Hermes PM desk that worked and has no PM seat gets one (`PM · 33GOD`); seats with no component stay dark. Hover works where the building is at full size (staff, pjangler, heyma, flume), not in the zoomed-out numbers beat. The film re-renders on a real minute only when that minute flips a window. Act III and every set piece stay staged. The list is `NIGHT_BEATS` in `overnight.js`.
- **The clock's label follows suit**: "Real night · 16–17 Nov 2026" over those six beats, "A night, staged" everywhere else.
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
| Clock times, window activity | Real in the six night beats when a night file loads (see above). Beat times themselves are staged. |
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
