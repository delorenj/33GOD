# The nesting level meter for 33GOD

Status: draft v0, 2026-11-11. Built only from the **parent chain** in [`research/platform-map.md`](research/platform-map.md) (ground truth, 2026-11-11). Grammar rules: [`grammar/v0.md`](grammar/v0.md) section 7.

## How to read it

- A bar is a row of identical squares. Its length is **depth in the part-of tree**, nothing else. It is not size, importance, or kind of thing.
- `████` level 1, `███` level 2, `██` level 3, `█` level 4. Four levels is the cap. A fifth level means a new booklet.
- Level 0 is the table (everything Jarad runs). It has no bar.
- Parent means **"is part of or owned by"**. If A only *uses* B, that is a line, not a nest.
- Status marks: (live) solid, (partial) a bite out of a corner, (absent) dashed outline, (retired) grey with an X.
- Counts decay in days, so none are printed here. The map holds the dated numbers.

## Table zero

Everything Jarad runs: big-chungus (DeLoNET), a Lightsail VM, a DigitalOcean droplet. **Damian's Mac Studio is its own table.** It runs a separate partial 33GOD peer with its own bus, Candystore and hook-hub, and there is no federation between the two. The one thing both tables call is the Jev gateway (per `research/damian-reality.md`).

## The whole tree

Evidence column format: map row id; where it lives or how it was proved. All rows are from `platform-map.md` "Tree, row by row" and its evidence cells.

### Level 1: three bars beside each other

| Bar | Thing | Status | Evidence |
|---|---|---|---|
| `████` | **33GOD** | live | `god33`; `~/code/33GOD`; NATS `/jsz` shows BLOODBANK_EVENTS and BLOODBANK_COMMANDS |
| `████` | **LLM gateways** (AutomaticAI owns them, 33GOD only calls them) | live | `brains`; `api.automaticai.io` 200; `jev-litellm` container running |
| `████` | **Phonograph** (client captioning product, formerly Dubplate; NOT part of 33GOD or HeyMa) | live | `phonograph`; `phonograph/hooks.py` `VOX_URL` default `https://vox.delo.sh` |

### 33GOD, level 2 families and their parts

```
████ 33GOD
├ ███ Bloodbank (repo plus contract, not one process)
│   ├ ██ NATS JetStream ── █ BLOODBANK_EVENTS (7 d, limits)   █ BLOODBANK_COMMANDS (1 d, work queue)
│   ├ ██ naming contract and schemas
│   ├ ██ hook-hub ── █ bb-hook
│   ├ ██ bb / bb-emit
│   ├ ██ Dapr sidecars and placement   (partial: listen side only)
│   ├ ██ n8n-nodes-bloodbank
│   ├ ██ Hermes gateway bus plugin
│   ├ ██ bus helper services           (partial)
│   └ ██ Apicurio and EventCatalog     (absent: defined, not running)
├ ███ Memory ──── ██ Candystore · ██ Enricher · ██ Hindsight
├ ███ Candybar (the one clock) ── ██ heartbeat+dispatcher+api · ██ executor · ██ steward
├ ███ n8n (the glue) ── ██ Plane lifecycle lanes
├ ███ Workforce ── ██ hermes-gateway · ██ agent desks · ██ Flume · ██ role template · ██ Skillex
├ ███ Work board ── ██ Plane · ██ Pilot (px) · ██ PJangler · ██ Momo (partial) · ██ Krebs (partial)
├ ███ Voice ──┬ ██ HeyMa ──┬ █ waxd and wax CLI
│             │            ├ █ intake parts
│             │            └ █ n8n-nodes-heyma
│             ├ ██ Vinyl    (sibling of HeyMa, not inside it)
│             └ ██ Voxxy    (sibling, shared service)
├ ███ Eyes ── ██ Holocene · ██ Monitoring ── █ ntfy
├ ███ Aperture, the installer (partial)
├ ███ MCP hub (retired: dormant, mcp.delo.sh returns 404)
└ ███ The Manual (absent: planned)

████ LLM gateways ── ███ AutomaticAI gateway · ███ Jev
████ Phonograph    (no children in the map; arrows to Voxxy and to a copy of Vinyl's speech core)
```

### Row by row with evidence

| Level | Bar | Thing | Parent | Status | Evidence (map id; where) |
|---|---|---|---|---|---|
| 2 | `███` | Bloodbank | 33GOD | live | `bus`; `bloodbank/compose/nats/streams.json`; `bloodbank/services/*` |
| 3 | `██` | NATS JetStream | Bloodbank | live | `nats`; container `bloodbank-nats` (`nats:2.10-alpine`) |
| 4 | `█` | BLOODBANK_EVENTS | NATS | live | `stream-evt`; `streams.json`: subjects `bloodbank.evt.>`, retention `limits`, max_age `7d`, discard `old` (checked in code 2026-11-11) |
| 4 | `█` | BLOODBANK_COMMANDS | NATS | live | `stream-cmd`; `streams.json`: `bloodbank.cmd.>` and `bloodbank.rpy.>`, retention `workqueue`, max_age `1d` (checked in code) |
| 3 | `██` | Naming contract and schemas | Bloodbank | live | `contract`; `bloodbank/docs/event-naming.md`; type is `bloodbank.<domain>.<entity>.<action>` |
| 3 | `██` | hook-hub | Bloodbank | live | `hookhub`; `bloodbank/services/hook-hub/hub.py`; `hook-hub.service` active |
| 4 | `█` | bb-hook | hook-hub | live | `bbhook`; `bloodbank/services/hook-hub/client/bb-hook` |
| 3 | `██` | bb / bb-emit | Bloodbank | live | `bbcli`; `bloodbank/cli/bb.py`, `bloodbank/bin/bb-emit` |
| 3 | `██` | Dapr sidecars and placement | Bloodbank | partial | `dapr`; `candystore/dapr-components/pubsub.yaml`, `33god-platform/enricher/dapr-components/enricher-pubsub.yaml`; placement idle, no actors |
| 3 | `██` | n8n-nodes-bloodbank | Bloodbank | live | `n8nnodes`; `bloodbank/integrations/n8n-nodes-bloodbank` v0.8.1 |
| 3 | `██` | Hermes gateway bus plugin | Bloodbank | live | `hermesplugin`; `bloodbank/services/hermes-gateway/` |
| 3 | `██` | Bus helper services | Bloodbank | partial | `bbhelpers`; artifact-sidecar and target-watch running, heartbeat-tick legacy and not running |
| 3 | `██` | Apicurio and EventCatalog | Bloodbank | absent | `registry`; defined in `bloodbank/compose`, not in `docker ps` |
| 2 | `███` | Memory | 33GOD | live | `memory` |
| 3 | `██` | Candystore | Memory | live | `candystore`; `candystore/candystore/ingest.py` `SUBSCRIBE_TOPIC bloodbank.evt.>`. **Code wins:** the map says FastAPI, the code is a Python stdlib `http.server` (`main.py:9`) |
| 3 | `██` | Enricher | Memory | live | `enricher`; durable `enricher-events`, deliverPolicy `new` |
| 3 | `██` | Hindsight | Memory | live | `hindsight`; `api.hs.delo.sh` healthy |
| 2 | `███` | Candybar | 33GOD | live | `clock`; `candybar.delo.sh/healthz` 200; own repo |
| 3 | `██` | heartbeat + dispatcher + api | Candybar | live | `cb-heartbeat`; consumer `candybar-dispatcher-ticks` |
| 3 | `██` | executor | Candybar | live | `cb-executor`; `candybar-executor.service` |
| 3 | `██` | steward | Candybar | live | `cb-steward`; `candybar-steward.service` |
| 2 | `███` | n8n | 33GOD | live | `glue`; `~/.n8n`, `n8n.delo.sh` |
| 3 | `██` | Plane lifecycle lanes | n8n | live | `lanes`; one durable consumer per lane, `n8n-<workflowId>-*` |
| 2 | `███` | Workforce | 33GOD | live | `workforce`; `~/.hermes` |
| 3 | `██` | hermes-gateway | Workforce | live | `hermesgw`; `hermes-gateway.service` |
| 3 | `██` | Agent desks | Workforce | live | `desks`; `~/.hermes/profiles/<name>`, `agents-registry.yaml` |
| 3 | `██` | Flume | Workforce | live | `flume`; `33GOD/flume` |
| 3 | `██` | Role template | Workforce | live | `template`; `33GOD/hermes-agent-template` |
| 3 | `██` | Skillex | Workforce | live | `skillex`; `~/code/skillex` |
| 2 | `███` | Work board | 33GOD | live | `workboard` |
| 3 | `██` | Plane | Work board | live | `plane`; `plane.delo.sh` 200 |
| 3 | `██` | Pilot (px) | Work board | live | `pilot`; `33GOD/pilot/bin/pilot.js`. Policy: the only Plane writer. Behaviour: n8n also writes labels. |
| 3 | `██` | PJangler | Work board | live | `pjangler`; `127.0.0.1:8764` |
| 3 | `██` | Momo | Work board | partial | `momo`; a skill, spec and adapter, no daemon |
| 3 | `██` | Krebs | Work board | partial | `krebs`; contract docs plus `adapters/tp` scripts, v2 engine not running |
| 2 | `███` | Voice | 33GOD | live | `voice`; Aperture group G6 |
| 3 | `██` | HeyMa | Voice | live | `heyma`; `~/HeyMa`, `waxd.service` |
| 4 | `█` | waxd and wax CLI | HeyMa | live | `waxd`; `~/HeyMa/bin/waxd`, `components/wax` |
| 4 | `█` | Intake parts | HeyMa | live | `heyma-intake`; hotkey, Syncthing, Telnyx (shadow mode) |
| 4 | `█` | n8n-nodes-heyma | HeyMa | live | `heyma-n8n`; `~/HeyMa/components/n8n-nodes-heyma` |
| 3 | `██` | Vinyl | Voice | live | `vinyl`; apt `vinyl`; source is a submodule in `~/HeyMa` **for co-location only** |
| 3 | `██` | Voxxy | Voice | live | `voxxy`; `~/code/voxxy`, `vox.delo.sh` |
| 2 | `███` | Eyes | 33GOD | live | `eyes` |
| 3 | `██` | Holocene | Eyes | live | `holocene`; `holocene-api.service`; consumer `holocene_*` |
| 3 | `██` | Monitoring | Eyes | live | `monitoring`; `33GOD/monitoring` |
| 4 | `█` | ntfy | Monitoring | live | `ntfy` |
| 2 | `███` | Aperture | 33GOD | partial | `aperture`; groups G1-G8 plus the Mac mirror (W2-W4 done, W5-W10 not) |
| 2 | `███` | MCP hub | 33GOD | retired | `mcphub`; `mcp.delo.sh` returns 404 |
| 2 | `███` | The Manual | 33GOD | absent | `manual`; initiative I-10 |
| 2 | `███` | AutomaticAI gateway | LLM gateways | live | `aaigw`; `~/code/client-portal/gateway` |
| 2 | `███` | Jev | LLM gateways | live | `jev`; `~/docker/stacks/ai/jev-litellm` |

Note the LLM gateways: they are components, but the meter measures only parent depth, so they sit at level 2 under their own level-1 product. The map's own "L-numbers" disagree here, so the meter never labels levels "product / family / component". A "what kind of thing" label belongs on the brick's shape, never on the bar.

## Corrections to Jarad's example

Jarad's sketch: *33GOD is a long bar; HeyMa shorter inside it; wax, vinyl and phonograph shorter inside HeyMa; Voxxy shorter inside phonograph.* He said not to take it literally. Here is what the live map says.

1. **A level is missing.** It is 33GOD > **Voice** > HeyMa > waxd. HeyMa does not sit directly under 33GOD with every voice thing inside it. That gives the clean staircase of four bars: `████ 33GOD`, `███ Voice`, `██ HeyMa`, `█ waxd`. This is why the meter fits his idea so well.
2. **Wax is right inside HeyMa.** Wax is HeyMa's engine: `waxd` plus the `wax` CLI.
3. **Vinyl is a sibling of HeyMa, not a child.** It is its own product in the Voice family. Its source sits in `~/HeyMa` only as a git submodule for co-location. It never feeds Wax and only reads Wax's `Dictionary.yaml`.
4. **Phonograph is a neighbour, not a child.** It is a client captioning product on a droplet, level 1 beside 33GOD. It bundles a pinned copy of Vinyl's speech core (drawn as a ghost duplicate) and calls Voxxy over HTTP.
5. **Voxxy is not inside Phonograph.** It is a shared service that Phonograph (`VOX_URL`) and Hermes (TTS provider `vox`) both call. That is an arrow from each, not a box. Its home is Voice.

Corrected chain for his four names:

```
████ 33GOD
 └ ███ Voice
    ├ ██ HeyMa ── █ waxd
    ├ ██ Vinyl
    └ ██ Voxxy  ◄── ASK arrows from Hermes and from Phonograph

████ Phonograph  ── ASK arrow to Voxxy · ghost copy of Vinyl's speech core
```

## What the meter distorts (say it on the page)

- Length means depth, not size or importance. Phonograph draws four squares because it is level 1, not because it is big.
- It flattens "kind". A component can be shallower than a family.
- It says nothing about where something runs. That is the plates (runs-on), a different atom.
- It says nothing about who talks to whom. That is the four lines.

## Where the map disagrees with the code (the orchestrator should fix the map; I did not edit it)

- `candystore` row says "FastAPI app". Code: Python stdlib `http.server` (`candystore/candystore/main.py:9`, `candystore/CLAUDE.md`).
- The F1 flow and the `hookhub` row point at `services/hook-hub/nats_publish.py`. The file is `bloodbank/services/agent-hooks/core/nats_publish.py`. hook-hub imports it (`hook-hub/observations.py:17`, `session_capture.py:69`) and the publisher path reaches it through `core/publisher.py:33`.
- The "px is the only Plane writer" line in the `pilot` row is policy. n8n's Ticket Pickup Chip also writes labels to Plane, and PM agents comment through the API.

## Damian's edition

The tree does not change on his Mac. The plates under it do, and the dashed outlines (absent here) do. On 2026-11-10 his box had: NATS and Dapr placement, Candystore, Plane and n8n inside a Colima VM; hook-hub and the pjangler registry as native LaunchAgents; OpenSign on Docker Desktop. Not installed there: Candybar, Flume, Enricher, Hindsight stack, HeyMa, Vinyl, Holocene (W5-W10). Evidence: `33god-platform/aperture/mirror/evidence/` and `research/damian-reality.md`. His evidence is dated 2026-11-10 and must be re-probed read-only before any page claims it.
