# Thread: Overnight launch page, first full pass, hosted at 33god.delo.sh

Date: 2026-11-16 (America/New_York). Operator: Jarad. Agent: Claude (claude.ai session, 33GOD project).

## Ask

Apply the 33GOD Overnight design system to the launch-page plan so the whole vision can be seen working end to end before the content is perfected, and host it at `33god.delo.sh`.

## Inputs read

| Input | Where | Used for |
|---|---|---|
| 33GOD Overnight design system | https://claude.ai/artifact/3fX6X9vkEHw6tTG9z3DTQN (`project/README.md`, `tokens.json`, `components/bundle.js`, `bundle.css`, `index.d.ts`) | Tokens, the six components, the seven laws |
| Overnight: Experience Bible | https://claude.ai/artifact/THg8wjmCVLk5WMFUqGepXu | The 21 beats, times, set pieces, camera moves, real-versus-staged rules, open decisions |
| 33GOD Landing Page (Design) | https://claude.ai/artifact/Liw6BUy95RR77TxhammtPo, `project/Main.dc.html` and `Direction-A-Overnight.dc.html` | All copy; the storyboard frames |
| Bloodbank subjects | grep of `~/code/33GOD/bloodbank` for `bloodbank.<…>` strings | Real event subjects for the log view |

## What was built

`33god-platform/overnight/` in the 33GOD repo:

- `site/index.html`, `site/overnight.js`, `site/overnight.css`: a scroll-driven page. Scroll is the dolly; each beat holds 72% of its length and travels 28%. The clock, camera, sky and window states are all functions of scroll position.
- `site/manifest.json`: the scene manifest. 21 beat records with design fields and content fields, the site chrome copy, and the staged Act III transcript. No copy lives in JS.
- `site/ds/`: the design system's `bundle.js` and `bundle.css` copied byte for byte (sizes match the artifact: 4241 and 3535 bytes), and `tokens.css` written out from `tokens.json`.
- `site/vendor/`: React 18.3.1 UMD from npm, so the page needs no CDN. Fonts still load from Google Fonts, as the design system specifies.
- `README.md`: how to edit, what is real versus staged, what is not built.

Staging decisions made in this pass (all in `overnight.js`, all reversible):

1. The building is 12 floors by 8 windows: 72 lightable (one per first-party component in the registry count), 1 yours, 23 dark. PJangler adds a 13th floor at 04:12.
2. Fourteen components have fixed seats because set pieces need them (`PLACED`). The 22 staff are seated by floor so the staff roll climbs. The rest are scattered by a deterministic hash.
3. The conference room is WAX's window. The Act III push-in scales the building 9x about that window and the transcript glass grows out of it.
4. Acts open with a full-stage statement (`interlude` on a beat record): Act II, Act III, Act IV, and the flagships.
5. At 07:38 the lights go out from the top floor down, so the ask at 07:41 has one light only: yours, on submit.
6. Dawn is a horizon band masked to the scene half of the stage, so it never sits behind words.

## Hosting

- Stack: `~/docker/stacks/websites/33god/compose.yml` (DeLoContainers repo). `nginx:alpine`, container `33god-web`, read-only bind mount of `…/33god-platform/overnight/site`, on the external `proxy` network.
- Traefik router `god33`: `Host(33god.delo.sh)`, `websecure`, `letsencrypt`, plus middleware `god33-stealth` adding `X-Robots-Tag: noindex, nofollow`. The page also carries `<meta name="robots" content="noindex, nofollow">`.
- Brought up with `docker compose up -d` from the stack folder. No Traefik or gateway restart.
- Files written through the device bridge landed as mode 600/700; nginx (uid 101) could not read them until they were set to 664/775, matching `manual/books`.

Before this work `https://33god.delo.sh/` returned 404 (wildcard DNS, no router), so nothing was replaced.

## Verification

- `curl` against `https://33god.delo.sh`: 200 for `/`, `/manifest.json`, `/overnight.js`, `/ds/bundle.js`, `/vendor/react-dom.production.min.js`; `x-robots-tag: noindex, nofollow` present.
- Headless Chrome at 1440x860, 1280x720 and 1920x1080: every beat screenshotted and looked at, locally and against the live URL. No console errors.
- Interactions: the header CTA jumps to 07:41 in the morning theme; submitting the form lights exactly one `window-you`; the log view lists 26 lines; `prefers-reduced-motion` and a 390px viewport both open in the log view.
- One bug found and fixed in verification: a nav jump into Act III mounted the glass with no scrubbed styles until the next scroll event. A layout effect now re-runs the frame when the beat changes.

## Needs Jarad

1. **The briefing form stores nothing.** It lights the window and says "Preview build" under the field. It needs a destination before this is shown to anyone.
2. **Copy I had to place or write**, all in `manifest.json`: "Agents are employees. The pipeline is the company." moved from the old hero to the 18:05 numbers beat; "The lobby directory" kicker; flagship titles merged as "PJangler. The project factory."; the scroll hint; the log-view lead; the staged transcript, speaker names, tickets and the translated call.
3. **Log view pairings.** Subjects are real, but which subject sits on which beat is a guess.
4. **Open decisions from the bible** are untouched: sound, real-night replay, live counter, one-machine reveal, byline (kept, as in `Main`), phones (log view for now).
5. **33god.delo.sh is public** behind Cloudflare with no auth, like `manual.delo.sh`. It is noindex. Say if it should sit behind auth while in stealth.

## Lessons for the next person

- The Cowork `device_bash` shell is a VM that sees only the connected folder. Git, Docker and anything outside that folder go through Desktop Commander's `start_process`, which runs on big-chungus itself.
- Files committed through the device bridge arrive owner-only. Anything nginx serves from a bind mount needs `chmod` afterwards.
- A websites stack needs no Traefik change: labels on the container are enough, and `*.delo.sh` already resolves.
