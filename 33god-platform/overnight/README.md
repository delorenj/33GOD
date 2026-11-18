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

## Real versus staged in this pass

| Element | State |
|---|---|
| Component names and their one-liners | Real, from the landing page copy |
| The five counts (72, 12, 214, 299, 1) | Real, stamped 15 Nov 2026 |
| Event subjects | Real, from the Bloodbank contract. Which subject sits on which beat is a first guess and needs a content pass. |
| Clock times, window activity | Staged, labelled once beside the clock |
| Transcript words, speaker names, the translated call | Staged, written for this pass |
| The briefing form | Lights your window and stores nothing. It says so under the field. |

## Not built yet

These wait on the open decisions in the bible: sound and the Vox standup, the real-night replay, the live event counter, the one-machine reveal, and a designed phone layout (phones get the log view for now).

## Preview locally

```bash
cd site && python3 -m http.server 8765   # then open http://localhost:8765
```

## Hosting

`33god-web` is `nginx:alpine` with this `site/` folder bind-mounted read-only, routed by Traefik at `33god.delo.sh`. The stack is `~/docker/stacks/websites/33god/compose.yml`, the same shape as `manual.delo.sh`. The router adds `X-Robots-Tag: noindex, nofollow` while 33GOD is in stealth.
