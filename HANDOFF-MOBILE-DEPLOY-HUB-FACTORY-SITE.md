# Handoff: mobile-deploy-hub in the Factory and on the launch page

**Belsky level:** the mobile lane, meaning every mobile app the hub ships, not only the hub.

**To:** Grolf (33god-pm). You own intake, assignment and dispatch for this epic.
**From:** the mobile-deploy-hub session for Jarad, 2026-11-24.
**Request (Jarad, 2026-11-24):** "add the mobile deploy hub as a component in the factory and the marketing site."
**Plane:** epic **33GOD-130**, with stories 33GOD-131 to 133 in Todo and 33GOD-134 in Backlog. This doc links the tickets but does not track their status; the board does that.

---

## 1. What this is, in one paragraph

mobile-deploy-hub is the one road every mobile app version takes to a device. It is one reusable workflow, one composite action, a few Node tools and one strict policy file. An app runs `mise run deploy`. The hub bumps the version, builds the Android and iPad apps, publishes them, installs them in place on real devices, reads the installed version back, and announces the result on Bloodbank. A device that is away gets the build as `pending`, and a catch-up installs it when the device comes back. The hub is **already registered** in the Atlas and already stands on the Factory floor, but only as a kiosk in the crew annex, placed there by default by the 2026-11-17 drift audit. It has no body. On the launch page it appears only as one staff-roll line. So this work is mostly about deliberate placement, a body and real copy. The hub needs very little new registry work.

## 2. Verified starting state (2026-11-24)

| Fact | Evidence |
|---|---|
| The Atlas record exists, with `factory: {near: crew}` and no `public_card` | `33god-platform/components/mobile-deploy-hub.yaml` |
| It is rendered into the cast as a kiosk near crew, among 13 other crew kiosks | `jq '.components["mobile-deploy-hub"]' 33god-platform/manual/sandbox/src/cast.generated.json` |
| No body exists. Only candybar, hook-hub and turn-enricher have assets, and all three are **stations**. No kiosk asset has ever shipped. | `ls 33god-platform/manual/sandbox/src/assets/`, `forge/ledger.json` |
| No station is free: every SetId except `bays` is held | cast grouped by station; `manual/sandbox/src/waybill/stations.ts:17` |
| The nightly forge will not reach the hub for about 20 nights, because stations rank ahead of kiosks | `python3 33god-platform/scripts/factory_forge.py pick --explain` |
| A targeted forge run works | `factory_forge.py pick --component mobile-deploy-hub --explain` ranks it first |
| The relation evidence is stale. It cites `catchup.mjs:905`, but the anchor is now at `:1011` | the hub repo, `tools/catchup/catchup.mjs` |
| The hub is already in the public export (`public_card {}`) | `33god-platform/atlas/public.json` |
| The marketing site is the 33GOD launch page, an In Development preview with noindex. Its copy is one bind-mounted JSON file, so a merge is live immediately. | `components/launch-site.yaml`, `33god-platform/overnight/site/manifest.json` (staff roll at about line 1572), `overnight/README.md` |
| The hub serves 6 apps. Only Earshot and Shortwave have Atlas records (both `near: soundwing`). | the hub's `tools/ci/policy.json` `apps`, and `components/` |
| The hub has no registered PM | 33GOD-124 and FLUME-107 (related to 33GOD-131) |
| `atlas.py check` printed OK for 100 components | run 2026-11-24 |

## 3. Where it lives

Everything to edit is in this repo (`~/code/33GOD`). **Do not edit `~/code/mobile-deploy-hub`.** Read it for facts only: the hub has no PM, and its version and release flow is governed by its own policy.

| What | Path |
|---|---|
| Factory skill (read first) | `33god-platform/skills/33god-hub/subskills/the-factory/SUBSKILL.md`, then `subskills/factory-maintenance/` |
| Asset contract | `33god-platform/manual/sandbox/forge/CONTRACT.md` |
| Warehouse metaphor | `33god-platform/manual/world/warehouse-bible.md` |
| Hub record | `33god-platform/components/mobile-deploy-hub.yaml` |
| Launch page copy and tests | `33god-platform/overnight/site/manifest.json`, `33god-platform/tests/test_overnight_site.py` |
| Marketing charter | `~/.agents/workforce/peggy-olson/agent.yaml` |
| Art director | `flume/roles/art-director.md` |
| Hub facts (read only) | `~/code/mobile-deploy-hub/README.md`, `docs/features.md`, `tools/ci/policy.json` |

## 4. The tickets

| Ticket | Lane | What |
|---|---|---|
| 33GOD-130 | Backlog (container) | Epic |
| 33GOD-131 | Todo, ranked top | **A.** Place the hub deliberately, fix the stale evidence, and link earshot and shortwave to it |
| 33GOD-132 | Todo, blocked by 131 | **B.** Hand-targeted forge run: the first kiosk body |
| 33GOD-133 | Todo | **C.** The launch page gives the mobile lane a real presence |
| 33GOD-134 | Backlog, blocked by 131 | **D.** Atlas records for the four apps without one. This one needs Jarad. |

Each ticket carries its own numbered acceptance criteria. In brief:

- **4A, placement.** The default is `near: soundwing`, beside the phone apps it delivers. `crew` is an agent workstation hall, and the hub isn't one. Change only the `factory:` block, then `atlas.py render && atlas.py check`, and commit the record together with the cast. Before you rewrite `runtime`/`surfaces`, check how the Android catch-up is started, because the hub's `.candybars/` holds only the iPad catch-up. Use only relation kinds that `atlas.py` already accepts.
- **4B, body. ON HOLD (Jarad, 2026-11-24: $10-21 per model is too much).** Do not start a real forge run until Jarad chooses a cheaper path: either a trimmed forge loop or a kit pilot (see the comment on 33GOD-132). A dry run is fine. The contract shape still applies: The manifest needs `placement: kiosk`, `replaces: []`, a footprint of at most 1.4 × 1.3, and handles env in and post out. A kiosk body animates only during waybill playback or on the turntable; record that as a gotcha. Do not edit anything in 33god-platform during the run (scope check).
- **4C, launch page.** Peggy chooses the tier and writes the copy. The art director signs off on the look and does the privacy review. A coding worker edits `manifest.json`. Do not use a flagship slot or a store-shelf card. The merge goes live, so it waits for Jarad's explicit go.
- **4D, app records.** Every record goes automatically into the public `atlas/public.json`, and Navi is a client product. This waits for Jarad to accept it and say which apps can be named.

## 5. The hub, data-true (for the body and the copy)

**Behaviours you may depict or claim:**
1. One deploy contract. Every app plugs in through the same thin caller, and its hash is checked.
2. A strict, versioned policy. Every job logs its digest.
3. Patch bump and tag by the hub only. A version is never reused.
4. A shared device queue, first in first out, with a position and an ETA. Leases are time-capped.
5. In-place installs with a readback of the version and checksum. The hub never uninstalls, clears data or downgrades.
6. An away device is `pending`, not failed, and it is caught up automatically when it returns.
7. Store lanes exist. **TestFlight is opt-in** and Play needs an explicit flag.
8. Each run attempt emits one Bloodbank event: `bloodbank.project.deployment.completed` or `.failed`. Each delivery is `installed`, `pending`, `skipped` or `failed`. The event subject is fine on the Factory floor but must stay out of public copy.

**Never depict or claim:** "every device confirmed" (the completion contract is deferred), anything on the hub's "Not built" list (`docs/features.md`: `mhub status`, durable TestFlight tracking, auto-rebuild before expiry, catch-up heartbeats), or an install count.

**Never put in public copy or an asset:** hostnames, LAN addresses, device models or serials, signer hashes, team ids, package or bundle ids, the `callers.accept` hash, vault refs, repo paths, ticket ids, or personal names. The hub repo itself is public; the six app repos are private.

**Canon:** an app build is not a "parcel". In the bible a parcel is a raw vendor hook. Treat apps as the hub's cargo, coming in as an envelope (the deploy call) and going out as a post-it (the deployment event). A new canon word or object needs Jarad.

## 6. Decisions that are yours (Grolf)

- Whether to accept the soundwing default in 4A or argue for crew, dock or belt. Record the reason.
- Assigning 4C to Peggy Olson and the art director, and choosing the coding worker.
- Ordering: 4A first, so 4B has a final placement.

## 7. Needs Jarad (park each as one exact ask)

- **4C merge:** the launch page goes live on merge, so it needs an explicit go.
- **4D:** which of Tower of Lost Things, Green In Between, Gruvato and Navi may be named in the public export. Navi is an AutomaticAI-io client product.
- **Forge spend for 4B:** none until Jarad picks the cheaper path (comment on 33GOD-132).
- **Any new station, SetId or canon object**, such as an "outbound dock".
- Grolf's planning-only intake on MOBI (33GOD-124 and FLUME-107) is a separate question. This epic does not depend on it.

## 8. Non-goals

- Do not touch the hub repo's release flow, deploy any app, bump a version or mint a tag. Mobile ships only through the hub.
- Do not trigger the FLUME-85/86/87 Atlas campaign briefs or any outreach or spend.
- Do not hand-edit `cast.generated.json`, `stations.ts` or scene code to place a component.
- Never run `mise run build` in `manual/sandbox` as a test, because a build is a deploy.

## 9. Done means

Every story's criteria are met, every repo touched has a clean `git unpushed`, and the closeout states both halves: what the hub got (a deliberate place, a body, launch-page presence) and what the mobile lane got (the apps linked to the hub, consistent launch-page treatment, a proven kiosk-forge path).
