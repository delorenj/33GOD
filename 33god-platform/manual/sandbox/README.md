# The Factory: a 3D sandbox for the 33GOD Manual

Status: **experiment v0.1, 2026-11-12.** Initiative I-10. Every creative choice here is a proposal [P] for Jarad to keep, change or throw out.

Live at **https://manual.delo.sh/sandbox/**. Deep links:

- `?walk` skips the intro.
- `?at=<station>` flies to a station. The stations are `bays`, `courier`, `dock`, `labeldesk`, `belt`, `archive`, `rules`, `control`, `cataloguer`, `clock` and `crew`.
- `?bulb=<id>` opens a lightbulb.
- `?nofx` turns off bloom and vignette.

## What it is

The warehouse from [`../world/warehouse-bible.md`](../world/warehouse-bible.md), built as a small 3D world you can orbit, click and poke. The reader's first job is **Find Bloodbank**. Bloodbank is the department called Material Handling, painted blue on the floor. It has four parts, and the reader finds them by clicking: the courier, the receiving dock, the label desk and the belt.

The floor is a **running simulation of the canon**, not an animation. Every behaviour is a rule in [`src/sim/sim.ts`](src/sim/sim.ts):

| What you see | The rule it plays | Real thing |
|---|---|---|
| Couriers walk parcels from six vendor bays. Each parcel is tagged in its vendor's own hook word. | One raw hook per parcel, in the vendor's dialect | `bb-hook`, `hooks.master.json` |
| Parcels go into the dock and one house post-it comes out, "turn started", with the vendor in the "from" corner. | Normalization | hook-hub |
| Post-its climb the front of the belt, and envelopes climb the back. | Height is age. The front is scraped at 7 days, the back at 1 day. | `BLOODBANK_EVENTS` / `BLOODBANK_COMMANDS` |
| Translucent copies fly from notes to the archive, the control room and the rules cabinet, and the original stays put. | Fan-out. Readers come to the belt. | durable and ephemeral consumers |
| The archive sometimes gets a second copy and shows "already filed". | Dedupe on the Note ID | `ON CONFLICT (id) DO NOTHING` |
| The rules cabinet only takes "summary written" notes. | Pick list | filter subjects |
| The cataloguer's runner sticks summaries with no barcode and no "from" corner. | The one Dapr publisher, which skips the label desk | `enricher/main.py:164` |
| The clock rings, and envelopes go up the back of the belt. On the hour, a burst arrives. | Chores as commands | Candybar |
| A crew-hall desk takes an envelope only when it is free. The envelope stays pinned on the belt until it is signed off, and is sometimes handed back. | Work queue, ack, nak, max ack pending | hermes-gateway |
| Grey "audio task" envelopes ride up untouched to the 1-day scraper. | Commands with no consumer | the orphaned `audio.task.start` |
| The "Shut the dock" control makes couriers turn round with the parcel, and nothing queues. | Fail-open | `bb-hook` |

Click any note to see its face: the Note ID, the barcode, the belt number, its age, who has torn off a copy, and why it is still there.

There are seven lightbulbs. Normalization uses the drafted modal from [`../lightbulbs/normalization.md`](../lightbulbs/normalization.md). The other six are draft copy, written to [`../world/tone.md`](../world/tone.md): fail-open, fan-out, event versus command, retention, work queue and idempotent.

All copy lives in [`src/content.ts`](src/content.ts), so words can change without touching the scene.

## Run it

```bash
mise run dev      # hot reload on :5173
mise run build    # typecheck, then build into ../books/sandbox (gitignored)
```

A build is a deploy. The `manual-web` nginx container bind-mounts `../books` (see `~/docker/stacks/websites/manual/compose.yml`), so the new build is live on the next refresh.

## Play a waybill

A waybill is one recorded prompt: every hook, event, model call and side effect it caused, with real timings (format: [`../../waybill/SPEC.md`](../../waybill/SPEC.md)). The Factory can play one as a guided, data-true tour of the real components, seen from the prompt's point of view. It reuses the tour's camera flights and leaves the new-hire tour (`?tour`) and the sandbox untouched.

Ways in:

- **`?waybill=<url>`** plays a file straight away. The URL is absolute, or relative to the site base: `/sandbox/?waybill=waybills/fixture-claude-prompt.waybill.json`. Add `&stop=7` to start at a stop. The fetch sends no credentials, so a cross-origin file needs CORS.
- **Play a waybill** (the button in the controls and on the intro) opens a picker: the samples listed in `public/waybills/index.json`, a file chooser, and a link box.
- **Drag a `.json` or `.json.gz` anywhere** on the page.

**Gzip.** The loader (URL, picker, drop zone, link box) accepts a gzip-compressed waybill: it sniffs the gzip magic bytes (`1f 8b`), so `x.waybill.json.gz` and a server that sends gzip bytes without `Content-Encoding` both work, and inflates with `DecompressionStream('gzip')`. A server that does send `Content-Encoding: gzip` is decoded by the browser and loads as plain JSON. A big turn can therefore ship whole, with no thinning: list it in `public/waybills/index.json` as `"file": "claude-big-turn.waybill.json.gz"`. The self-check inflates `.gz` samples too.

What you see: a bar of real numbers on top (duration, tokens, findings), a card per stop with the real component names, and a DevTools-style waterfall along the bottom. Rows are grouped by component, bars sit on the real millisecond axis (fit-to-stop by default; linear and log are the overviews; tick labels thin out so they never overprint), solid bars are things the prompt waited on, hatched bars ran alongside, red is broken. Click any bar or row to jump to its stop and open the inspector: when, who and outcome first, then a collapsed Details section (ids cut to 8 characters, click to copy; belt number, status and reason, timings, attrs), the payload preview and the list of readers (clip, visitor's pass, or core subscriber; seen or inferred). The waterfall scrolls to the stop's own span row (a model call lands on its bar, not on a usage note) and to any selected row. A model call's two usage / allowance notes, when they were only filed and collected, fold into one "routine usage notes" row. The last stop is "What did not happen": one-line findings with a severity chip (click for the detail) and the gaps folded into a count ("14 things we could not see"); in 3D at most three findings and three gap tags, on a ladder so they do not overprint.

Keys: <kbd>Space</kbd> play or pause, <kbd>←</kbd> <kbd>→</kbd> previous and next stop, <kbd>Esc</kbd> closes the inspector, then leaves. On a phone the header is one line (title, findings chip, a menu, Leave), the dots become `n/N`, at most two labels show per frame, and the waterfall folds into a mini-strip; tap it to open the full one, with a one-line caption kept above it.

Stop card: **Inspect** sits in the card header. Times are signed once (`-2.43 s`, never `+-`; `(before Enter)` is spelled out). A stop that starts earlier than the one before it says so ("Back in time: ..."), which happens when the session opens before Enter. The briefing card is a big outlined envelope that flies from the dock to the bay, with the camera framing both; a crew stop stands up one figure per subagent with a count badge; a tool round shows the tool running now (`Bash · 12 of 34`); post-it copies are about a unit wide with a trail; the model call shows orbiting dots and `model · seconds` under one gateway name.

How it maps (all in `src/waybill/`):

| File | Job |
|---|---|
| `types.ts` | The v1 types and a tolerant reader: refuses an unknown major version, defaults missing arrays, draws unknown span kinds as a generic kiosk. |
| `stations.ts` | Registry id to station table. Components with no station get a kiosk, placed deterministically beside the station they relate to, tagged with their real id. Adding a component needs no 3D work. |
| `director.ts` | A pure function, waybill to stops. A hook and its handlers are one dock stop (sync cards in the window, async in the back room), the injected context is a separate briefing-card stop, a long tool loop is several stops (rounds of at most 5 tool calls, split at 45 s silences, so a 5 minute turn is watchable), each bus event is a belt stop with its fan-out, and the last stop is the findings and gaps. |
| `WaybillWorld.tsx` | The 3D layer, a pure function of one playhead number. The ambient sim is paused and its flyers, bulbs and labels are hidden. |
| `WaybillHud.tsx`, `Waterfall.tsx`, `Inspector.tsx`, `Picker.tsx` | The panels, the waterfall, the inspector and the loader UI. |
| `state.ts`, `load.ts` | Player state (its own small store; the sandbox store only gained `mode: 'waybill'`) and the loaders. |

Self-check for the pure parts, no framework: `node --import ./tools/waybill/register.mjs --experimental-strip-types tools/waybill/selfcheck.ts [file]`. It also prints the stop list.

`public/waybills/fixture-claude-prompt.waybill.json` is hand-written, public-profile and has no personal text. Its ids and timings follow a real 2026-11-16 capture; the prompt, tools and model calls are illustrative.

## Stack, and where it deliberately departs from the "edge stack" brief

- **React Three Fiber 9, drei 10, three r187, zustand 5, @react-three/postprocessing 3, Vite 8.**
- **The simulation brain is zustand**, plus a small scheduler in `sim.ts`. The 3D components only *read* from it. That keeps the rules in one inspectable file, which veterans can read directly.
- **Renderer: WebGL for now, not WebGPU.** pmndrs postprocessing and some drei helpers are still WebGL-only. The WebGPU path is R3F's async `gl` factory with `three/webgpu`'s `WebGPURenderer`, which falls back to WebGL2 on its own, plus TSL post-processing. It belongs in phase 4 below, once the art is settled.
- **No Rapier for the bus, on purpose.** The brief's "watch backpressure pile up physically" would teach the wrong model of Bloodbank:
  - Nothing piles up at the dock. The courier turns round.
  - Envelopes wait *on the belt*. They do not tumble into a heap.
  - The hatch is bounded by the number of free desks.

  Physics belongs to things that really are physical: walking around, knocking over a vendor's parcel stack, and the toys in the sandbox. It does not belong to how messages behave.
- **No Leva in the reader's view.** The reader-facing controls are custom: play and pause, 1×/4×/16×, "Shut the dock", "Sources" and "Go to…". Leva can come back as a `?debug` panel for tuning.
- **Labels are DOM** (drei `Html`), which keeps them crisp and puts them in the reader's own font. `src/world/Tag.tsx` hides any label that the belt stands in front of.

## Proposed road to a flagship [P]

1. **Art direction (Jarad).** Settle the look first:
   - LEGO-style brick-built props with real models (Blender → glTF → `gltfjsx`), baked ambient occlusion, a character design for the crew, and a sound bed (belt hum, the bell, paper).
   - The current shapes are placeholders built from primitives. They are kept on purpose so the art can be swapped piece by piece.
2. **Walk mode.**
   - A third-person or first-person walker (a Rapier character controller), with a touch joystick on phones.
   - Stations "light up" as you approach.
   - A floor map with fog over the parts you have not found yet.
3. **Depth.**
   - All 22 lightbulbs from the catalog.
   - The other departments as zones on the same floor: the crew hall wing, the sound wing, the control room and the lessons library.
   - Theatre.js guided tours, one per book chapter, that also work as the "Words version" walk-through.
4. **Live belt.**
   - A read-only bridge from the real bus to the browser, sampled and with payloads redacted, so the belt shows the reader's *own* post-its.
   - Damian's edition then runs on his machine's belt.
5. **Reach.**
   - The WebGPU renderer with WebGL fallback.
   - Instanced notes, KTX2 textures and a mobile frame budget.
   - Accessibility: a text twin for every station, reduced motion, and keyboard navigation through the stations.

## Known gaps in v0.1

- The archive, control room and crew hall are blocks, not rooms you can see into.
- The hatch has no visible door on the belt.
- Notes are readable only up close or through the inspector.
- Every lightbulb except Normalization is draft copy.
- Nothing is persisted, so a refresh restarts the floor.
