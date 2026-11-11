# 33GOD platform map (ground truth, 2026-11-11)

Research input for I-10 "The Manual". Every row below was checked against live
processes, live NATS consumers, live HTTP endpoints or current code on
big-chungus on 2026-11-11. Where a doc disagreed with the code, the code won and
the disagreement is listed under "Stale traps".

## How to read the tree

- **Parent means "is a part of" or "is owned by".** A box sits inside another
  box only when it belongs to it, like a wheel belongs to a car.
- **"Uses" is an arrow, not a box.** If A only calls B, B does not go inside A.
  Those links are in the `talks via` column.
- **The meter.** Each level of the tree is one notch on the LEGO scale bar:
  - **L0** everything Jarad runs
  - **L1** a product (33GOD, the LLM gateways, Phonograph)
  - **L2** a family inside 33GOD (Bus, Memory, Clock, Glue, Workforce, Work board, Voice, Eyes, Installer)
  - **L3** a component you can point at (NATS, Candystore, HeyMa, Vinyl)
  - **L4** a part of a component (a daemon, a stream, a CLI)

## The tree at a glance

```
L0 Everything Jarad runs
├─ L1 33GOD (the agent factory)
│  ├─ L2 Bus ........ Bloodbank
│  │  ├─ L3 NATS JetStream ─ L4 BLOODBANK_EVENTS, BLOODBANK_COMMANDS
│  │  ├─ L3 Naming contract + schemas
│  │  ├─ L3 hook-hub ─ L4 bb-hook
│  │  ├─ L3 bb / bb-emit CLI
│  │  ├─ L3 Dapr sidecars + placement (subscribe side only)
│  │  ├─ L3 n8n-nodes-bloodbank
│  │  ├─ L3 Hermes gateway bus plugin
│  │  ├─ L3 helper services
│  │  └─ L3 Apicurio + EventCatalog (in compose, not running)
│  ├─ L2 Memory ..... Candystore, Enricher, Hindsight
│  ├─ L2 Clock ...... Candybar ─ L4 heartbeat, dispatcher, api, executor, steward
│  ├─ L2 Glue ....... n8n ─ L4 Plane lanes, custom nodes, workflow export
│  ├─ L2 Workforce .. Hermes gateway, 49 agent desks, Flume, job template, Skillex
│  ├─ L2 Work board . Plane, Pilot (px), PJangler, Momo, Krebs
│  ├─ L2 Voice ...... HeyMa ─ L4 waxd/wax + intake parts; Vinyl; Voxxy
│  ├─ L2 Eyes ....... Holocene, Monitoring ─ L4 ntfy
│  ├─ L2 Installer .. Aperture (G1-G8 bags + Damian mirror)
│  ├─ L2 MCP hub (dormant)
│  └─ L2 The Manual (this initiative, planned)
├─ L1 LLM gateways (shared brains) ─ L3 AutomaticAI gateway, Jev
└─ L1 Phonograph (client product, not 33GOD)
```

## Tree, row by row

Status: live = running and doing work today. partial = some of it runs, or it
runs but is frozen, idle or in shadow mode. retired = nothing runs. planned =
designed, not built.

### L0 and L1

| id | name | parent | kid sentence | what it really is | lives at | status | talks via |
|---|---|---|---|---|---|---|---|
| everything | Everything Jarad runs | (root) | All the computer stuff Jarad built and keeps running. | Root of the map. Holds 33GOD plus the neighbors 33GOD leans on or lends parts to. | big-chungus (DeLoNET), a Lightsail VM, a DigitalOcean droplet | live | n/a |
| god33 | 33GOD | everything | A factory where robot helpers do work and talk by messages. | Jarad's agentic dev platform: an event bus, memory, a clock, an AI workforce and its tools. Parent repo is a director repo of submodules. | `~/code/33GOD` | live | NATS subjects `bloodbank.evt.>` / `bloodbank.cmd.>` |
| brains | LLM gateways (shared brains) | everything | Doors every robot uses to reach a thinking computer. | AutomaticAI's model router plus the Jev judgment service. Owned by AutomaticAI, not 33GOD; 33GOD only calls them. | `~/code/client-portal/gateway`, `~/docker/stacks/ai/jev-litellm` | live | HTTPS OpenAI-compatible API |
| phonograph | Phonograph | everything | Live captions that translate English and Spanish in Teams calls. | Hosted Teams captioning and translation for an IntelliForia client. Bundles a pinned copy of Vinyl's speech core. | `~/code/dubplate`, droplet `phonograph.intellifornia.com` | live | HTTPS to Voxxy (`VOX_URL`, default `https://vox.delo.sh`) |

### L2 families inside 33GOD, with their L3 and L4 parts

| id | name | parent | kid sentence | what it really is | lives at | status | talks via |
|---|---|---|---|---|---|---|---|
| bus | Bloodbank (the bus) | god33 | The mail system every part uses to send messages. | A repo and a contract, not one process: NATS config and schemas, hook-hub, the CLI, the Hermes plugin, n8n nodes and helpers. | `33GOD/bloodbank` | live | NATS JetStream |
| nats | NATS JetStream | bus | The post office that holds every message for a week. | Container `bloodbank-nats` (nats:2.10) on 4222/8222, compose project `33god-platform`. | container `bloodbank-nats` | live | NATS protocol |
| stream-evt | BLOODBANK_EVENTS | nats | A diary of everything that happened, kept seven days. | JetStream stream on `bloodbank.evt.>`, limits retention, 7 days, about 1.1M messages. | `bloodbank/compose/nats/streams.json` | live | consumers: candystore-events, enricher-events, holocene_*, n8n-*, candybar-dispatcher-ticks |
| stream-cmd | BLOODBANK_COMMANDS | nats | A to-do pile where each job goes to one worker. | Work-queue stream on `bloodbank.cmd.>` and `bloodbank.rpy.>`, 1 day. | `bloodbank/compose/nats/streams.json` | live | consumers: bloodbank-hermes-gateway, candybar-executor-invoke, candybar-steward |
| contract | Naming contract and schemas | bus | Rules for how every message must be written. | Type `bloodbank.<domain>.<entity>.<action>`; subject adds `evt`/`cmd`/`rpy`. CloudEvents 1.0 JSON envelopes; `kind` is authoritative. | `bloodbank/docs/event-naming.md`, `bloodbank/schemas/` | live | n/a |
| hookhub | hook-hub | bus | Hears every AI helper and pins a note about it on the bus. | Python daemon: 35 handlers, 83 bindings, 9 CLIs. Answers some hooks inline (memory recall), runs the rest in the background, publishes raw NATS. | `bloodbank/services/hook-hub/hub.py`, `hook-hub.service`, socket `/run/user/1000/33god/hook-hub.sock`, health `:8685` | live | Unix socket in; NATS 127.0.0.1:4222 out |
| bbhook | bb-hook | hookhub | A tiny messenger each AI helper calls after every move. | Client every native CLI hook runs; designed to never stall the agent. | `bloodbank/services/hook-hub/client/bb-hook` (linked from `~/.agents/hooks/` and `~/.local/bin/`) | live | Unix socket to hook-hub |
| bbcli | bb / bb-emit | bus | A command you type to send a message yourself. | Operator CLI; `bb emit` passes through to `bin/bb-emit`, which publishes to NATS directly. | `bloodbank/cli/bb.py`, `bloodbank/bin/bb-emit` | live | NATS |
| dapr | Dapr sidecars and placement | bus | Helpers that carry mail from the post office to two apps. | Subscribe side only: `candystore-daprd` and `enricher-daprd` (daprd 1.13) turn NATS messages into HTTP POSTs. Placement on 50005 is idle: no actors. No publisher uses Dapr. | containers `candystore-daprd`, `enricher-daprd`, `bloodbank-dapr-placement` | partial | `pubsub.jetstream` component `bloodbank-pubsub` |
| n8nnodes | n8n-nodes-bloodbank | bus | Building blocks that let n8n send and hear messages. | n8n community nodes v0.8.1: Bloodbank, BloodbankTrigger, DevJournal, Fleet, PlaneBloodbank. Copied into n8n. | `bloodbank/integrations/n8n-nodes-bloodbank` | live | NATS (`nats.ts`) |
| hermesplugin | Hermes gateway bus plugin | bus | Lets the AI workers pick up jobs from the mail. | Platform plugin loaded by `hermes-gateway`; consumers `bloodbank-hermes-gateway` (`bloodbank.cmd.agent.invocation.start`) and `-interactive` (`...invocation.invoke`); producer `hermes-agent:<profile>`. | `bloodbank/services/hermes-gateway/` | live | nats-py |
| bbhelpers | Bus helper services | bus | Small helpers that watch the mail for special jobs. | artifact-sidecar, artifact-vault-projector, target-watch (running); cost-bridge (running from a scratchpad copy); heartbeat-tick (legacy, not running). | `bloodbank/services/*` | partial | NATS |
| registry | Apicurio and EventCatalog | bus | A planned library card catalog for message shapes. | Defined in bloodbank compose and in Aperture G1, not running here. | `bloodbank/compose/docker-compose.yml` | planned | n/a |
| memory | Memory family | god33 | Where the factory remembers what happened. | Candystore (every event), Enricher (search vectors and summaries), Hindsight (learned facts). | various | live | NATS in, HTTP out |
| candystore | Candystore | memory | A library that keeps its own copy of every message. | Python stdlib http.server (candystore/main.py:9) plus Postgres (pgvector pg16). Dapr pushes every `bloodbank.evt.>` to `/events/all`; idempotent insert. About 4.96M events, about 156k a day. | `33GOD/candystore`, API 127.0.0.1:8683, DB 127.0.0.1:5434 | live | Dapr durable `candystore-events`; HTTP `/events`, `/sessions`, `/context/latest` |
| enricher | Enricher | memory | Reads new messages and makes them easy to search. | FastAPI: local BAAI/bge-small embeddings into candystore-postgres; session summaries via the AutomaticAI gateway. | `33god-platform/enricher`, container `enricher` + `enricher-daprd` | live | Dapr durable `enricher-events` (deliver new) |
| hindsight | Hindsight | memory | A notebook where helpers write down lessons to remember. | vectorize-io/hindsight 0.10.1 with LiteLLM and reranker containers. Banks per repo. hook-hub recalls before a prompt and retains after a turn. | `~/docker/stacks/ai/hindsight`, `https://api.hs.delo.sh` | live | HTTPS; hook-hub handlers `hindsight-recall` / `hindsight-retain` |
| clock | Candybar (the clock) | god33 | The one clock that says when chores happen. | Single scheduler for every recurring job: 121 jobs (99 enabled). Runners: exec, systemd, hermes, n8n. | `33GOD/candybar` (own repo), `candybar.delo.sh` | live | NATS ticks and commands |
| cb-heartbeat | heartbeat, dispatcher, api | clock | Ticks every minute and decides which chores are due. | One container `candybar` with roles heartbeat, dispatcher, api on 127.0.0.1:8700. Dispatcher filter `bloodbank.evt.cron.tick.>`. | container `candybar` | live | publishes `cron.tick.fired`, `cmd.cron.candybar.invoke` |
| cb-executor | executor | clock | The hands that actually do each chore. | Host service; consumer `candybar-executor-invoke` on `bloodbank.cmd.cron.candybar.invoke`; emits invoked and completed facts. | `candybar-executor.service`, `candybar/executor/` | live | NATS |
| cb-steward | steward | clock | A helper that handles the clock's caretaking jobs. | Host service; consumer `candybar-steward` on `bloodbank.cmd.cron.candybar.steward`. | `candybar-steward.service` | live | NATS |
| glue | n8n (the glue) | god33 | Picture-wires that connect apps without writing code. | n8n under PM2 on 5678; 90 workflows, 60 active. Normalizes Plane webhooks onto the bus and runs the ticket lanes. | `~/.n8n`, `n8n.delo.sh`, exports in `~/code/delonet-n8n-workflows` | live | HTTP webhooks in, NATS via n8n-nodes-bloodbank |
| lanes | Plane lifecycle lanes | glue | Wires that move a ticket from new to being worked on. | Workflows: Plane to Bloodbank, Ticket Grooming, Ticket Delegation, Groomed-in-Todo, Pickup Chip, Lane Errors, Ingress Reconcile. Each listens on its own durable `n8n-<workflowId>-*`. | n8n DB, workflow ids e.g. `6wAGA5pdrmHLyhs2` | live | NATS consumers per lane |
| workforce | Workforce (Hermes fleet) | god33 | The team of AI workers, each with its own desk. | One Hermes install serving 48 profiles from one gateway, staffed by Flume from a job template, skilled by Skillex. | `~/.hermes` | live | NATS commands in, Telegram, HTTPS to LLM gateway |
| hermesgw | hermes-gateway | workforce | The office building all the AI workers share. | `hermes-gateway.service` running Jarad's fork of hermes-agent 0.22.7 (`~/.hermes/hermes-agent`); platforms: bloodbank plus per-profile Telegram. | `~/.hermes/hermes-agent`, `hermes-gateway.service` | live | NATS (plugin), Telegram |
| desks | Agent desks (profiles) | workforce | Each worker's own desk, notes and name tag. | 49 profile dirs, 46 registry rows (e.g. heyma-pm: Plane HEYMA, Telegram bot, `bloodbank.enabled`). Model `automaticai/auto`, TTS `vox`. | `~/.hermes/profiles/<name>`, `~/.hermes/agents-registry.yaml` | live | registry read by n8n Fleet node |
| flume | Flume | workforce | The hiring office that adds and checks on workers. | HR CLI and MCP: hire, onboard, roster, review. Employee = Hermes agent, desk = profile, org chart = registry. | `33GOD/flume`, `~/.local/bin/flume` | live | writes registry and profiles |
| template | Hermes agent template | workforce | The job description every new worker starts from. | Versioned `role.yaml` contract and runtime config Flume renders employees from. | `33GOD/hermes-agent-template` | live | files |
| skillex | Skillex | workforce | A shelf of how-to cards workers can pick up. | 454 skills; canonical root `~/.agents/skills`; PM desks are Skillex-only. | `~/code/skillex` | live | files and symlinks |
| workboard | Work board family | god33 | Where jobs are written down and tracked. | Plane holds tickets; px writes them; PJangler knows the projects; Momo drives the board; Krebs holds contracts. | various | live | HTTP Plane API |
| plane | Plane | workboard | A sticky-note wall for every project's jobs. | Self-hosted makeplane v1.4.3. Sends signed webhooks to n8n. | `~/docker/stacks/websites/plane`, `plane.delo.sh` | live | webhook to `n8n.delo.sh/webhook/plane` |
| pilot | Pilot (px) | workboard | A command that writes and moves tickets. | Ticketing CLI v0.5.0; the only Plane writer by policy. | `33GOD/pilot/bin/pilot.js` (`px`, `pilot`) | live | Plane REST |
| pjangler | PJangler | workboard | The phone book of every project. | Project registry service on 127.0.0.1:8764; `pj list` shows 53 projects. | `33GOD/pjangler`, `pjangler-project-registry.service` | live | HTTP, CLI |
| momo | Momo | workboard | Instructions for steering the job board by hand. | A skill, a spec and an adapter; no daemon. | `33GOD/momo` | partial | via px |
| krebs | Krebs | workboard | Rules for handing jobs over; mostly not switched on. | Contract docs and `adapters/tp` scripts PM desks use. The v2 engine does not run; n8n is the only webhook normalizer. | `33GOD/krebs` | partial | scripts |
| voice | Voice family | god33 | Parts that listen, write down and speak out loud. | Aperture group G6: HeyMa (Wax), Vinyl, Voxxy. Siblings, not nested in each other. | various | live | NATS, HTTP |
| heyma | HeyMa | voice | Records talks, saves them safely, then writes them down. | The Wax audio pipeline: record, archive to S3, transcribe, enrich. One daemon. | `~/HeyMa` | live | outbox to NATS (`audio.*`, `task.*`) |
| waxd | waxd and wax CLI | heyma | The machine inside HeyMa that does every step. | `waxd.service` runs the pipeline; `wax` is its CLI (Holocene calls `wax --json catalog`). | `~/HeyMa/bin/waxd`, `components/wax` | live | NATS outbox, S3, LLM gateway, Jev |
| heyma-intake | HeyMa intake parts | heyma | Three doors where recordings come in. | Hotkey `Ctrl+\`, phone via Syncthing (`syncthing-audio`), calls via Telnyx (`telnyx-s3-intake`, telephony in shadow mode). | `~/HeyMa/components/*` | live | files, S3, webhooks |
| heyma-n8n | n8n-nodes-heyma | heyma | Building blocks so n8n can use HeyMa. | n8n nodes, symlinked into n8n. | `~/HeyMa/components/n8n-nodes-heyma` | live | n8n |
| vinyl | Vinyl | voice | Turns your talking into typing, right on the computer. | Local dictation: `vinyld` (parakeet), `vinyld-serve` 7733, `vinyl-live` 7734 (frozen prototype), `vinyl-tray`. Own product; never feeds Wax; only reads Wax's `Dictionary.yaml`. | apt pkg `vinyl` 0.4.1.1; source a submodule in `~/HeyMa` for co-location only | live | local HTTP |
| voxxy | Voxxy (vox) | voice | Gives the robots a voice to talk out loud. | Universal TTS over HTTP and MCP: containers `vox` and `voxxy-engine-voxcpm`; ElevenLabs fallback; vibevoice engine not running. | `~/code/voxxy`, `vox.delo.sh` | live | HTTP, MCP |
| eyes | Eyes family | god33 | Screens and alarms that show how the factory is doing. | Holocene (mission control) plus the monitoring stack. | various | live | NATS, HTTP, Prometheus |
| holocene | Holocene | eyes | A big screen showing what every part is doing. | Mission control: `holocene-api.service` (node, :4000), `holocene-web` container, own NATS consumer on `bloodbank.evt.>`. | `33GOD/holocene` | live | NATS, HTTP, `wax` CLI |
| monitoring | Monitoring stack | eyes | Gauges and alarms that watch the machines. | Prometheus, Grafana, Loki, Alloy, OTel, Alertmanager, exporters (incl. `nats-exporter`), ntfy, LLM observability. | `33GOD/monitoring` | live | Prometheus scrape, ntfy |
| ntfy | ntfy | monitoring | Sends a ping to Jarad's phone. | Push notification server; e.g. n8n Transcription Notifications posts to topic `audio`. | `33GOD/monitoring` compose | live | HTTP |
| aperture | Aperture (installer) | god33 | Step-by-step bags to build 33GOD on another computer. | Eight install groups G1 (bus) to G8 (orchestration and apps), plus the mirror plan for Damian's Mac Studio. W2-W4 done there; W5-W10 not. | `33god-platform/aperture` | partial | n/a |
| mcphub | MCP hub | god33 | An old tool switchboard that is turned off. | Submodule last touched 2026-08-25; `mcp.delo.sh` returns 404; no process. Dormant, not formally retired. | `33GOD/mcp-hub` | retired | n/a |
| manual | The Manual | god33 | Picture instructions for building and using 33GOD. | Initiative I-10: LEGO-style manual, dogfooded by Damian. | `33god-platform/manual` | planned | n/a |
| aaigw | AutomaticAI gateway | brains | One door to many thinking computers, picking a good one. | new-api Go fork running on a Lightsail VM; routes like `automaticai/auto`, `automaticai/free`. Used by Hermes, Enricher and Wax. | `~/code/client-portal/gateway`, `api.automaticai.io` | live | OpenAI-compatible HTTPS |
| jev | Jev | brains | Answers only yes, no, a choice, or a score. | LiteLLM container passing `/typesafe/*` to typesafe.ai; typed judgments, no chat. Used by Wax classification passes. | `~/docker/stacks/ai/jev-litellm`, `jev.delo.sh` | live | HTTPS |

## The five flows (every hop proven on 2026-11-11)

### F1. An AI helper does something, and the library keeps it

1. Claude Code fires a native hook. `~/.claude/settings.json` runs `~/.agents/hooks/bb-hook --cli claude --native <Event>`.
2. `bb-hook` writes to hook-hub over the Unix socket `/run/user/1000/33god/hook-hub.sock`.
3. hook-hub's `bloodbank-publish` handler sends raw NATS to 127.0.0.1:4222 on subject `bloodbank.evt.agent.tool.requested`, which lands in `BLOODBANK_EVENTS`.
4. `candystore-daprd` (durable `candystore-events`, filter `bloodbank.evt.>`) POSTs to Candystore `/events/all`.
5. Candystore sanitizes and inserts idempotently into Postgres.
   Proof: `GET 127.0.0.1:8683/events` returned a `claude-code` `agent.tool.requested` at 2026-11-11T15:07:29Z.
6. The same message also reaches `enricher-events` (embeddings) and `holocene_*` (dashboard).

### F2. A new Plane ticket gets groomed by an AI project manager

Ticket JIMB-459, correlation `aa3b9102-8439-5446-9f88-ba203f05ba30`.

1. Plane sends a signed webhook to `n8n.delo.sh/webhook/plane`. The n8n "Plane to Bloodbank" workflow (`iMw484J1ZCqKME2C`) publishes `bloodbank.evt.repo.task.created` (14:32:00.547Z, producer `n8n-plane-webhook`).
2. Ticket Grooming (`6wAGA5pdrmHLyhs2`, durable filter `bloodbank.evt.repo.task.created`) uses the Fleet node to find the PM in the agents registry, then publishes `bloodbank.cmd.agent.invocation.start`.
3. The Hermes plugin consumer `bloodbank-hermes-gateway` takes the command. `hermes-agent:james-brennan-pm` emits `agent.invocation.started` (14:32:02.289Z, reason `ticket-grooming`).
4. The PM comments on the ticket. Plane echoes it back as `repo.task.appended` (14:34:59Z).
5. Hermes emits `agent.invocation.completed` (14:35:27.679Z), then `conversation.turn.completed`.
6. Ticket Pickup Chip (`wWXgCZiiIBWaRRzE`, filter `agent.invocation.started|completed|failed`) adds and removes the `agent:working` label.

### F3. The clock ticks, and a chore runs

1. The Candybar heartbeat publishes `bloodbank.evt.cron.tick.fired` (`tick:29906834`, 15:14:00.001Z).
2. The dispatcher (durable `candybar-dispatcher-ticks`, filter `bloodbank.evt.cron.tick.>`) finds due jobs and publishes `bloodbank.cmd.cron.candybar.invoke`.
3. The executor (consumer `candybar-executor-invoke`) emits `cron.candybar.invoked` (15:14:00.057Z) and runs the job.
4. The executor emits `cron.candybar.completed` (15:14:01.724Z): holocene-pad-roster, exit 0, 1640 ms, correlation `127f22b2-...`.

### F4. Jarad talks, and a transcript appears

Wax item `81db0233af4ef56f`.

1. waxd records the audio and emits `audio.file.recorded` (14:48:48Z).
2. Backup comes first: the audio is copied to `s3://recordings/` and verified, then `file.sent` (14:48:49Z).
3. faster-whisper large-v3 transcribes 30 minutes of audio in 120 s.
4. 8 enrichment passes emit `task.requested` and 7 emit `task.completed` (14:50:49-53Z). Chat passes use the AutomaticAI gateway chain; classification passes use Jev.
5. waxd emits `transcription.completed` (14:50:56Z) and then `file.closed`. The note lands in `~/d/Transcripts`.
6. n8n Transcription Notifications (durable filter `bloodbank.evt.audio.transcription.completed`) pings ntfy topic `audio`. Candystore keeps every step.

### F5. You type a prompt, and memory whispers back

1. Claude Code's `UserPromptSubmit` hook runs `bb-hook`, which reaches hook-hub over the socket.
2. hook-hub's `hindsight-recall` handler runs inline (`prompt_submit`, 11000 ms budget). It queries `api.hs.delo.sh` for the repo's bank and returns the answer to the CLI as added context.
3. At turn end, `hindsight-retain` saves the turn in the background.
   Proof: hook-hub `/health` activity: recall succeeded 244 times for claude (mean 378 ms, last 2026-11-11T15:06:10Z) and 61 times for codex; retain succeeded 3,831 times for claude. This flow is proven by handler stats, not by a single traced event.

## Stale traps (docs that will lie to a newcomer)

1. **Root `README.md` (2026-09-20)** gets Candybar and HeyMa wrong.
   - It calls Candybar an "optional service registry hub and topology visualization". It is the platform's single scheduler.
   - It places HeyMa at `~/code/HeyMa` as "WhisperLiveKit plus ElevenLabs". HeyMa lives at `~/HeyMa`, is the Wax pipeline and transcribes with faster-whisper. Voxxy does the speaking.
2. **"Dapr over NATS"** (bloodbank `README.md`, root README "with Dapr placement").
   - Every publisher (hook-hub, n8n nodes, Candybar, the Hermes plugin, `bb-emit`) talks raw NATS.
   - Dapr is only the subscribe side for Candystore and Enricher. Placement is idle and has no actors.
   - ADR-0001 is still "TBD".
3. **Hindsight's "Platform Map" mental model** has four errors:
   - It names `hermes-fleet-bloodbank-gateway.service`. No such unit exists; the consumer `bloodbank-hermes-gateway` lives inside `hermes-gateway.service`.
   - It says the command subject is `bloodbank.cmd.v1.agent.invocation.start`. The live subject has no `v1`.
   - It lists Holyfields as a component. No `holyfields` directory exists; the schemas live in bloodbank.
   - It gives Candystore Postgres 17. The live image is `pgvector/pgvector:pg16`.
4. **Naming contract "`{domain}.{entity}.{action}`, locked 2026-02-28"** (Hindsight conventions). This was superseded on 2026-05-14:
   - the type is `bloodbank.<domain>.<entity>.<action>`;
   - the subject adds `evt`/`cmd`/`rpy`.
5. **`aperture/mirror/PLAN.md` header says "nothing executed".** The evidence folder shows W2-W4 done on Damian's Mac (NATS, hook-hub, Candystore with an empty DB, pjangler, px).
6. **`~/code/HeyMa` is a retired checkout** (`STALE-CHECKOUT.md`, 2026-08-19). The real one is `~/HeyMa`.
7. **`~/code/vox` is not Voxxy.** It is an empty April 2026 VoxCPM experiment. Voxxy is `~/code/voxxy`.
8. **Two dead components look alive in the repo:**
   - `bloodbank/services/heartbeat-tick` is a legacy Dapr publisher and is not running. Candybar's heartbeat makes the ticks.
   - Apicurio and EventCatalog are in `bloodbank/compose`, but not running.
9. **The running bus containers belong to compose project `33god-platform`.** `bloodbank/compose/docker-compose.yml` describes them, but `bloodbank-cost-bridge` was started from a Claude scratchpad copy of the repo.
10. **The Wax model chain looks healthy from the tray.** It actually runs `auto/fast` then `free`, because the middle four members are unfunded (2026-11-02). The `provision-inference` docstring still lists old pass names.
11. **The MCP hub is a submodule, but it is dormant.** `mcp.delo.sh` returns 404 on every path.
12. **Project memory says "Network moved to 10.0.0.x".** The only LAN is 192.168.1.0/24.
13. **Hermes `tts.provider: voxxy` silently falls back.** The registry key is `vox`.

## Corrections to Jarad's example "33GOD > HeyMa > wax, vinyl, phonograph > voxxy"

1. **Wax is HeyMa's engine** (`waxd`), so HeyMa > waxd is right. Vinyl and Phonograph are not Wax's siblings inside HeyMa.
2. **Vinyl is its own product in the Voice family.** It sits in HeyMa's folder only as a git submodule "for co-location", and it never feeds Wax.
3. **Phonograph is not part of HeyMa or 33GOD.** It is a client captioning product on a DigitalOcean droplet that bundles a copy of Vinyl's speech core. It sits beside 33GOD at L1.
4. **Voxxy is not inside Phonograph.** It is a shared speaking service that Phonograph and Hermes both call: an arrow, not a box. Its home is the 33GOD Voice family (Aperture G6).
5. **Corrected nesting:** 33GOD > Voice > {HeyMa > waxd, Vinyl, Voxxy}. Phonograph sits beside 33GOD and points arrows at Voxxy and at a copy of Vinyl.
