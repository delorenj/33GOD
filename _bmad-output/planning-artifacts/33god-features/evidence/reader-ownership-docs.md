# Where agent and terminal awareness belongs in 33GOD: architecture and ownership, reconstructed from the docs and the live box

Survey date: 2026-11-06. Read-only. I edited nothing, wrote no Redis keys and sent nothing to any pane. Dates are file ctimes (`ls -l --time=ctime`) or commit dates. Where a doc and the code or live state disagree, the code wins and I say so.

## Summary

1. **The ASM already exists, and it says it owns agent state.** The "redis-backed ASM (Agent State Machine)" is a folder inside Bloodbank: `bloodbank/services/agent-hooks/core/asm.py` and `asm.lua`, plus `agents.py`, `sweep.py`, `asmctl`, `asm-tabpaint` and `asm-orcapaint`. It was built in 11 commits on 2026-09-05 (`9abd694`…`e359aa0`). Its README calls it *"the SSOT for agent state on this box — surfaces read it, and nothing else re-derives it from the bus"* (`agent-hooks/README.md:379`). It already keeps a pane-to-agent index (`asm:idx:pane:{sess}:{pane}`) and finds live agents from /proc.
   - It is **not registered anywhere in the platform.** No component manifest, `contracts:` entry, Plane board or `.project.json` names it. `components/bloodbank.yaml` describes an "event-backbone" and lists no ASM or Redis paths.
2. **Deckard is not built on the ASM.**
   - Deckard's PRD and brief are dated 2026-08-17, 19 days before the ASM existed.
   - Its ADR-001 deliberately made embedded redb the default store and Redis an opt-in feature, so a stranger can install it from the README.
   - It reads Bloodbank NATS events directly and builds its **own** global agent registry with its own 5-state vocabulary.
   - It never reads `asm:*`. Live Redis has 0 `deckard*` keys.
   - It does not own lighting or media. It runs argv commands that call `delohome` (Hue), `playerctl`/`wpctl` and `wingman`.
3. **Agent detection has been written at least four times:**
   - ASM `core/agents.py` (2026-09-05)
   - Deckard `deckard-mux/src/proc.rs`
   - pjangler `src/crank/panes.ts` (PJAN-202, 2026-11-05, an explicit port of Deckard's proc.rs)
   - the zcrank engine (`~/.agents/tools/jev-clairic/bin/zcrank.py`)

   There are also at least two competing state vocabularies: the ASM's 10 states, and Deckard's 5, which Holocene ported on 2026-10-06.
4. **The newest planning record points away from the ASM.** I-8 (`initiatives.md:442-488`, 2026-11-05) gives pane discovery to pjangler and makes Deckard's proc.rs the "reference contract … not a runtime dependency". It never mentions the ASM, even though the ASM docstring argues against keying by pane (`asm.py:171-177`).
5. **No earlier proposal to make the ASM its own repo exists** in any doc, initiative, commit or memory I searched. The only recorded open question is the reverse. A hindsight entry from 2026-11-05 asks *"whether Deckard becomes runtime owner of pane/agent detection"*.
6. **A formal repo has a clear shape today.** The cleanest example is the Pilot adoption, commit `808817f`, detailed in section 4. The reusable command for it (`pj import`, PJAN-165) has been stuck in Needs Attention since 2026-10-03, so adoption is still done by hand.

---

## 1. The intended layer model

### 1a. What the docs say

| Source (ctime) | Layer model |
|---|---|
| `33god-platform/docs/product-map.md:54-62` (2026-10-26, newest) | 1 Runtime core: Bloodbank, Dapr, NATS, Candystore. 2 Control plane: Holocene, Pipeline MCP Hub, platform manifests. 3 Provisioning: PJangler, CommonProject, Hermes templates. 4 Agent capability: Skillex, Hindsight, **canonical hooks**. 5 Operator experience: Candybar, HeyMa, docs. 6 Planned execution: Flume, then ACP, then Bloodbank, then Hermes. |
| `33god-platform/aperture/research/inventory-2026-10-23.md` (2026-10-23) | 8 shippable groups: G1 Bloodbank core bus, G2 integration plane, G3 agent fleet runtime, G4 observability, G5 project tooling, G6 voice, G7 enrichment and memory, G8 orchestration and apps. Line 41-42: **"Jarad-only layers, deliberately not shipped: desktop orchestration (zellij Workspace, asm painters, deckard, orca, crank/zcrank)"**. The ship board's `data.json:479` says the same. |
| `33god-platform/components.yaml` (2026-10-26) plus `components/*.yaml` | Roles per component: bloodbank `event-backbone`, candystore `event-audit-trail`, holocene `control-plane-dashboard`, krebs `ticket-lifecycle-engine`, pjangler `provisioning-control-plane`, flume `workforce`, hermes-fleet `agent-runtime-fleet`, pilot `plane-board-cli`, candybar `bloodbank-cron-framework`, pipeline-mcp-hub `tool-dispatch-gateway`, skillex, hindsight, heyma, momo. **No ASM, Deckard, Wingman or crank component.** |
| `README.md:28-57` (2026-09-20) | Groups: "Core pipeline", "Provisioning & orchestration", "Integrations & surfaces". This is stale in places; see section 5. |

### 1b. Reconstructed model

This combines the docs above with the live dependencies I checked. The layer names for ASM, Deckard and Wingman are my inference, because no doc places them.

| Layer | Members | Evidence |
|---|---|---|
| L0 Host primitives (not owned by any component) | zellij, /proc, host Redis `127.0.0.1:6379` (host listener, not a container: `ss -ltnp`), NATS, Postgres, systemd | Redis 6379 appears in no component manifest. UNVERIFIED who is meant to own it. |
| L1 Transport and durable facts ("past tense") | Bloodbank (schemas, subjects, JetStream, canonical agent hooks), Candystore (history) | `docs/event-journey.md:39-48`; product-map L1 |
| L1' Live state folds ("present tense" primitives) | **ASM** (agent state, inside bloodbank agent-hooks), Krebs (ticket lifecycle machine), Candybar (clock) | ASM README `:376-445`. The Holocene IA calls ASM "THE CROWN JEWEL" (`holocene/_bmad-output/planning-artifacts/ia-redesign-2026-09/VERIFIED-GROUND-TRUTH.md:37`, 2026-09-06). Holocene ground truth `:285-286` names the "present-tense ↔ past-tense" join gap. |
| L2 Identity and authority registries | PJangler (project identity, registry `:8764`), Flume (workforce), Pilot (sole Plane writer), Krebs v2 (execution authority), Hindsight (memory) | AD-1 (`ARCHITECTURE-SPINE.md:42`); `krebs/README.md:5-17` |
| L3 Control surfaces | `pj` (the operator's "global control surface/CLI"), Holocene (read model plus command gateway), MCP hub, Momo | Holocene AD-1/AD-7. The operator's stated role for pjangler is wider than its manifest, which says only "Project subsystem bootstrapper CLI and MCP server… Employees are Flume's" (`components/pjangler.yaml:5`). |
| L4 Products and surfaces (operator desktop) | Deckard (Stream Deck), Wingman (voice pair programmer), asm-tabpaint and asm-orcapaint, crank/zcrank, HeyMa | The Aperture inventory calls this the operator-only layer. Deckard and Wingman are pjangler-registered projects (`pj list`) but not platform components. |

**The operator's framing compared with the code:**
- *pjangler as the global control surface wrapping lower-level commands.* This is how `pj` behaves: `pj audit`, `migrate`, `crank`, `skills` (passthrough to skillex), `board`, `link`. It is not how the platform docs describe it. Every manifest and README still calls it a "provisioning control plane / bootstrapper" (`README.md:41`, `components/pjangler.yaml:3-5`, `product-map.md:58`).
- *Deckard as a higher-level hardware product on top of the ASM.* Nothing in the code or docs supports this; see section 3. The closest real example of "a higher-level product on the ASM" is **Wingman**. It subscribes to `asm:transitions` (`~/code/Wingman/src/wingman/sources/events.py:30`) and classifies tabs from ASM state (`Wingman/AGENTS.md:11-16`, ctime 2026-10-24). Deckard's office mode only runs `wingman toggle` and `wingman ptt` (`~/.config/deckard/config.toml`).

---

## 2. Every stated ownership rule, and where it is written

| Rule | Where (ctime) | Status |
|---|---|---|
| "Bloodbank owns schemas/transport, PJangler owns identity/provisioning, Director owns intake/capacity/receipts, child PMs own child execution, **Toad observes**, Krebs owns lifecycle, and read models are non-authoritative." | **Hindsight only.** Bank `33GOD`, source document `delonet-director-rollout-2026-08-15` (session summary). `rg` across 33GOD, `~/.agents`, `~/.hermes/profiles` and deckard found no file containing it, and neither did `git log -S` in 33GOD. | Partly stale. Toad was retired on 2026-08-21 (`33god-platform/CHANGELOG.pipeline.md:291-297`, commit `8a04200`). |
| AD-1: "Flume owns workforce identity and policy; PJangler owns project identity; Krebs and Pilot own ticket lifecycle; Bloodbank and Candystore own event transport and durable history; Hermes owns runtime execution and receipts. DeloHQ may project… only the owning system may mutate or complete its fact." | `_bmad-output/planning-artifacts/architecture/architecture-33GOD-2026-09-23/ARCHITECTURE-SPINE.md:38-42` (2026-09-23) | Current, and the most authoritative statement of ownership. **Silent on live agent and pane state.** |
| Authority boundary table: Bloodbank = schemas, subjects, JetStream; Candystore = history; Holocene = read model, "not authoritative for event truth, command execution"; PJangler/fleet registry = project and agent identity plus route eligibility; Hindsight = memory | `docs/event-journey.md:37-48` (2026-09-23) | Current. No agent-state row. |
| Ownership matrix: `.project.json` and PJangler own project and permanent agent identity; Krebs owns lifecycle ("no private state machine"); Flume owns hierarchy; the Hermes fleet registry owns profiles; Bloodbank owns command ingress; Holocene is operator mission control | `33god-platform/docs/litellm-agent-control-plane-integration.md:50-66` (2026-08-13) | Older but consistent. |
| Krebs "must own the only canonical ticket-lifecycle state machine"; consumers use it "by pointer, never by copy" (FR12) | `PRD.md:402-420` (2026-08-21); `README.md:145-146` ("One lifecycle machine") | Current. Its spirit (one machine, consumed by pointer) is the precedent the operator's item 1 appeals to. |
| "PJangler is now the sole deterministic project lifecycle authority, with Momo retaining ongoing project orchestration." | `CHANGELOG.pipeline.md:295-297` (2026-08-21) | Current. |
| Flume "took the agent deploy, org chart and review surfaces out of PJangler, which is a project bootstrapper and registry and should never have owned a workforce." | `README.md:69-71`; commit `5465d8d` message (2026-09-20) | Current. This is a precedent for pulling a cross-cutting capability out of the repo it grew up in. |
| Krebs: "Pilot owns the Plane API adapter; Momo is the shared PM playbook; Hermes/systemd supervise runs; PJangler owns canonical bindings." The n8n Plane to Bloodbank workflow is "the single live normalizer". | `krebs/README.md:5-17` (2026-09-22) | Current. |
| Director Rule: "One owner per fact. Implementation facts belong to the child. Integration, timing and dependency facts belong to the parent." | `_bmad-output/planning-artifacts/director-rule-plan.md:32` (accepted 2026-09-29) | Current. |
| "Candybar owns **when** recurring work runs" | `CLAUDE.md` (root and global); `candybar/README.md:9` | Current. Violated live by `asm-sweep.timer`, a native 15-second systemd timer that is active (`systemctl --user list-timers`). |
| **ASM:** "It is the SSOT for agent state on this box — surfaces read it, and nothing else re-derives it from the bus. Two folds of one stream are two answers to one question, and they will disagree." / "`asm.lua` is the only writer." / "A surface reads `asm:*` and renders. It may PROPOSE through `asm.fire()`; it may not decide." | `bloodbank/services/agent-hooks/README.md:376-433` (2026-10-18) | Written as a rule but not enforced: Deckard and the Holocene port both re-fold the bus (section 3). |
| ASM identity: "NOT the zellij pane… settled by measurement rather than taste" (33 of 90 codex sessions had both paned and unpaned events; headless Hermes is 0 of 1292 paned) | `bloodbank/services/agent-hooks/core/asm.py:168-186` (introduced 2026-09-05) | In direct conflict with I-8's pane-bound crank. |
| "deckard ALREADY owns amber via publisher.py::_fanout_alert -> deckard.evt.attention" | `bloodbank/services/hook-hub/handlers.toml:324` (2026-10-30) | Current. The bus publishes a subject named after a product. |
| Deckard: "Canonical attention hooks are managed by Bloodbank `services/agent-hooks`… do not install a second publisher." / "delohome… owns the Hue bridge address and key"; office audio goes through `playerctl`/`wpctl`. | `~/code/deckard/docs/current-state.md:258-260`, `:176-177` (2026-10-23); `~/.config/deckard/config.toml` ("delohome owns the Hue bridge and its key; deckard holds neither") | Current. |
| I-8: "pjangler owns `pj crank` (discovery, registry, TUI). The zcrank engine (`~/.agents/tools/jev-clairic`, delorenj/agents) has no board yet. Deckard's `deckard-mux/src/proc.rs` is the reference contract for pane attribution; it is not a runtime dependency." | `_bmad-output/planning-artifacts/initiatives.md:452-455` (commit `026aed8`, 2026-11-05) | The newest planning statement. It does not mention the ASM. |
| Holocene IA: ASM/Redis is "the ONLY gate oracle" | `holocene/.../ia-redesign-2026-09/DECIDED-IA.md:37` (2026-09-06) | Holocene later also added `deckard-state.ts`, "read agent state the way Deckard does" (`holocene/apps/api/src/deckard-state.ts`, commit `2aa2852`, 2026-10-06). The direction is therefore mixed. |
| Skills are owned by components | `README.md:118-133`; `PRD.md:380-381` | Current. |

**Agent and pane awareness has no owner in any architecture document.** AD-1, the event-journey authority table, the ACP matrix and every component manifest leave live agent state, pane topology, agent-process detection, pane input and tab focus unassigned. The only places that claim them are an ASM README inside a Bloodbank service directory, a Deckard design doc, and I-8.

---

## 3. Earlier proposals and decisions: ASM, pane awareness, Deckard's dependencies

### 3a. Timeline

| Date | Event | Evidence |
|---|---|---|
| Before 2026-08-17 | The Nanoleaf agent wall used **"Redis as the state seam. Hooks and pollers only *write*; the daemon only *reads*. Anything that can talk to Redis can drive a surface."** Its vocabulary was `active/hitl/error/idle`, with a separate hook writer and /proc writer. | `~/code/deckard/PRD.md:39-55`. The origin commit `dc2bda8` (`scripts/nanoleaf-panels/`) is not in zshyzsh, deckard, `~/.agents` or bloodbank: **location UNVERIFIED**. |
| 2026-08-17 | Deckard PRD and brief: "v1 public release", "Open source, public, packaged for Linux" (`PRODUCT-BRIEF.md:143`); pillar `installable-by-a-stranger` (`.momo/pillars.md:26`). | PRD and brief ctime 2026-09-23 |
| 2026-08-17 | **Deckard ADR-001: "embedded by default, Redis opt-in".** It rejects "Redis mandatory" because it breaks goal G6. The reversal trigger is "multi-host fan-out becomes a v1 requirement". `scripts/check-core-purity.sh` fails the build if the default flips. | `~/code/deckard/docs/adr/001-state-seam.md` (ctime 2026-09-09) |
| 2026-08-21 to 26 | Deckard attention flash. Bloodbank's publisher gained `_fanout_alert`, which sends to `deckard.evt.attention` on core NATS (outside JetStream). | `deckard/_bmad-output/implementation-artifacts/spec-hook-notification-attention-flash.md:73`; `asm.py:10-13` |
| **2026-09-05** | **The ASM was born in Bloodbank.** Commits: `9abd694` (event-driven ASM), `95b4757` (sweeper), `7fd8bbf`, `ed2d735`, `4c29ff6` ("/proc is the live registry", for 33GOD-58 ticket claiming), `e359aa0`, `2334800` ("the tab bar is a surface on the state machine, not a second one"), `e8250af`. The daily journal says "33GOD, Holocene and Candystore all moved to consume it". | `git -C bloodbank log --grep=asm`; `_bmad-output/daily-journals/2026-09-05/report.md:6-12` |
| 2026-09-05 | `~/.agents/hooks/asm/{log-transition,notify-stale}.sh` added as hook-hub transition handlers (`d211f53`, `5e6970e`). | `handlers.toml:297-335` |
| 2026-09-06 | `d484d03` "fix(asm): stop the tab blink from drowning deckard". The Holocene IA declared ASM the crown jewel. | bloodbank log; Holocene IA |
| 2026-10-02 | Holocene Auto brownfield: "Identity is CLI plus process/starttime or Hermes profile, **not pane identity**". It also found that the ASM writes empty `session_id`/`correlationid`. | `_bmad-output/specs/spec-holocene-auto/brownfield.md:51-59`. I-2.1's acceptance criteria require harnesses to be "observable **independently of Deckard panes**" (`initiatives.md:128-129`). |
| 2026-10-06 | Holocene ported Deckard's 5-state vocabulary for the hub (`2aa2852`). | `holocene/apps/api/src/deckard-state.ts:1-14` |
| 2026-10-18 | `asm-orcapaint` surface for Orca cards (`0975238`). | bloodbank log |
| 2026-10-23 | Aperture classed "asm painters, deckard, orca, crank/zcrank" as operator-only and "deliberately not shipped". | `inventory-2026-10-23.md:41-42` |
| **2026-11-05** | I-8 plus PJAN-202 (now Done): `pj crank panes` is a "port of Deckard's `crates/deckard-mux/src/proc.rs`, which solved this first and is the reference contract". It reads /proc, `~/.claude/sessions` and `zellij list-panes`. **It never reads `asm:*`.** | `pjangler/src/crank/panes.ts:1-25`; commits `146e534`…`2800bdb`; `px show PJAN-202` gives Done |
| 2026-11-05 | Hindsight (pjangler bank) records the open questions: "whether Deckard becomes runtime owner of pane/agent detection, whether crank gets its own repo (delorenj/crank) as submodule, whether features.toml is tracked per machine…, whether to drop pinned Hermes image (CAND-49)". | `hindsight memory recall pjangler …` |
| 2026-11-05 (proposal only, `/tmp`) | `/tmp/feature-design.md` §7 gives `pane.topology`, `agent.process`, `pane.input` and `tab.focus` to **deckard-mux**, and `agent.session`/`agent.state` to **bloodbank ASM**. | `/tmp/feature-design.md:364-382` |

**A standalone ASM project:** I found no proposal, initiative, ticket, ADR or memory for one. I searched `_bmad-output` in 33GOD, bloodbank, pjangler and flume, plus krebs, the aperture research, the bloodbank commit log, and hindsight banks `33GOD`, `bloodbank` and `pjangler`. The question is new.

### 3b. Deckard's actual dependencies (verified)

- **zellij CLI** in poll mode. The WASM plugin is disabled after the CliPipe incident (`config.toml [mux] source = "poll"`).
- **Bloodbank NATS**: `bloodbank.evt.agent.{tool,session,invocation}.>`, `bloodbank.evt.conversation.turn.>` and `deckard.evt.attention` (`current-state.md:262-267`). These feed its **own global agent registry**, identified as `zellij:{session}:{pane}`, `hermes:{profile}` or `{cli}:{correlationid}` (`:280-290`). This is a second fold of the stream, which the ASM README forbids.
- **pjangler registry** `http://127.0.0.1:8764/v1/registry` for 33GOD mode (`config.toml [33god]`; `current-state.md:142,326`).
- **delohome** for Hue scenes, **playerctl/wpctl** for audio, **wingman** for voice (`config.toml [[office.button]]`; `current-state.md:176-177`).
- **Its own /proc agent classifier** (`crates/deckard-mux/src/proc.rs`, ctime 2026-09-23) and pane topology (`panes.rs`, `readiness.rs`).
- **Its own store**: redb by default (`current-state.md:28`). Redis behind the `redis-store` feature, under its own namespace (`crates/deckard-daemon/src/store/redis.rs:224-240`).
- **Not the ASM.** `grep 'asm:'` over the deckard source finds nothing, and live Redis has 0 `deckard*` keys.
- Services `deckard.service`, `asm-tabpaint.service`, `asm-orcapaint.service` and `asm-sweep.timer` are all `active`.

### 3c. Live ASM state

Redis 6379, read-only SCAN/HGET/GET, taken 2026-11-06 at about 11:06 EST:

- `asm:*`: 94 keys. 37 `asm:a`, 36 `asm:t`, 18 `asm:idx:pane`, plus `asm:live` (zset, 37), `asm:seen` and `asm:sweeper`.
- **22 of 37 rows are `basis=discovered, state=unknown`.** The sweeper found these processes through /proc but never observed them publishing.
- Hook-side Claude rows resolve on rung 4 (`claude:s:<sid>`, `pid=0`, `asm.py:218-223`), not the process key the README promises (`cli:p:pid.starttime`, README `:426`). **The code wins over the README here.**
- Result: **9 panes hold two rows for one Claude agent** (`claude/discovered` plus `claude/sid`), for example `Workspace:159`, `:150` and `:93`. The ASM's "one agent, one row" invariant is currently broken for Claude.
- Example: `asm:idx:pane:Workspace:159` points to `claude:s:b707c159-…`, a row with `zellij_session=Workspace`, `zellij_pane=159`, `cwd=/home/delorenj/HeyMa`, `state=tool_running`.
- `zcrank:*`: 20 keys keyed by **tab name** (`zcrank:tab:HeyMa`, `zcrank:log:gruvato`, …).

### 3d. Who consumes the ASM, and who re-implements it

| Reads `asm:*` | Re-implements agent/pane detection instead |
|---|---|
| Holocene `apps/api/src/hub.ts` (2026-10-18) | Deckard `deckard-mux/src/proc.rs` plus its own NATS fold (`deckard-daemon/src/agents.rs`) |
| Flume `packages/flume-hr/src/org/live.ts` (2026-09-20) | pjangler `src/crank/panes.ts` (`AGENT_CLIS` at `:41`, `readClaudeSession`) |
| Wingman `src/wingman/sources/events.py:30` (`asm:transitions`) | zcrank engine `zcrank.py` (tab and pane classification, screen scraping) |
| `asm-tabpaint`, `asm-orcapaint`, `asmctl` | ASM's own `core/agents.py` (`AGENT_COMMS`) is a separate copy of the CLI list |
| `~/.agents/hooks/asm/*` through hook-hub | Holocene `deckard-state.ts` (a vocabulary port) |

### 3e. What the evidence says about the operator's "ASM is the rightful owner"

This section is my inference, not a quoted decision.

**Supporting evidence:**
- The ASM is the only thing that **declares itself** the source of truth for agent state and forbids re-folding (`README.md:379-381`).
- It already holds the pane index, /proc discovery (`agents.py:1-16`: "/proc is" the true live registry), the sweeper, transition pub/sub and transition handlers.
- It has five consumers across four repos.
- It serves domains beyond the terminal: ticket claiming (33GOD-58), Flume's live org, Orca cards on the Mac and phone, and Wingman.
- Under the Director Rule, a primitive used by five children should not be hidden inside one child's `services/` directory with no manifest. `components/bloodbank.yaml` lists `hooks.master.json` as source of truth but not `asm.py`/`asm.lua`, so `platform:validate` and the changelog process cannot see it.
- Deckard's lighting and media are just argv to other tools, which is consistent with Deckard being a surface rather than an owner.

**Complications to resolve:**
- Deckard's pillar and ADR-001 rule out a mandatory Redis dependency for stranger installs. Building Deckard on the ASM needs either a packaged, installable ASM or Deckard keeping an embedded fallback.
- The ASM rejects the pane as identity (`asm.py:171-177`), while I-8 binds crank to panes. The ASM already stores the pane as a field and secondary index, which is a possible middle path.
- The ASM's live identity join is degraded (duplicate rows; empty `correlationid`/`session_id`, brownfield.md `:55`).
- The ASM runs inside the Bloodbank hook process on purpose, because `deckard.evt.attention` is invisible to JetStream (`asm.py:8-20`). Extracting it means Bloodbank's publisher calls an external package.
- `asm-sweep.timer` is a native timer that would need to move under Candybar.
- The `/tmp` design's assumption that Deckard owns pane topology is contradicted by I-8 ("not a runtime dependency") and by the ASM's charter. Its only support is that Deckard's implementation is the most mature (stable `tab_id`, lifetimes, DECK-42 readiness). The survey digest itself recommended the ASM for session and state (`/tmp/crank-survey-digest.md:154,158`).

---

## 4. How a component becomes a "formal repo" in 33GOD today

### 4a. Written rules

- "A service joins the active registry only when its repository or immutable deployment contract, health check, lifecycle owner, source-of-truth paths, and validation gates are real." (`33god-platform/docs/litellm-agent-control-plane-integration.md:68-72`, 2026-08-13; repeated in `product-map.md:38-41`, 2026-10-26.)
- A component is excluded "until a repository and contract exist, matching the rule applied to Flume, Holyfields, and Hookd" (`PRD.md:102-106`). Flume was dropped "until the repo path and platform contract are real" and re-added in `5465d8d`.
- Director Rule, child side: each child needs `_bmad/`, its own `epics.md`, its own board and a PM to receive delegations. "A child with no PM has no receiver; hire one first" (`director-rule-plan.md:65,95-97`).
- Pins sit at tip; runtime is never source; cross-component changes go into `CHANGELOG.pipeline.md` and `changes/*.jsonl` (`README.md:139-154`; `components.yaml:67-76`).
- `ticket_provider` in `.project.json` is the only board binding (pjangler `AGENTS.md`).
- CI: private repos use `runs-on: [self-hosted, Linux, delonet]` (global `CLAUDE.md`).
- I-3 (`initiatives.md:219-255`) makes "existing repo becomes an official 33GOD submodule" a reusable capability (PJAN-165 `pj import`). **PJAN-165 has been in Needs Attention (started) since 2026-10-03** (`px show PJAN-165`), so every adoption is still manual.

### 4b. Concrete example: Pilot (adopted 2026-10-06, 33GOD-79)

Parent commit `808817f` "chore(pilot): land the pilot submodule adoption (33GOD-79)" touched:
- `.gitmodules`, adding `pilot` with url `git@github.com:delorenj/pilot.git`
- the `pilot` gitlink (mode 160000)
- `33god-platform/components.yaml`, adding `components/pilot.yaml`
- `33god-platform/components/pilot.yaml` (24 lines: `id`, `role: plane-board-cli`, `repo: ../pilot`, `compose.profiles: [tools]`, `health.commands: node --test`, `source_of_truth`, `changelog.topics`, `public_card`)
- `33god-platform/CHANGELOG.pipeline.md`, the "Pilot adopted as a monorepo submodule" entry
- `33god-platform/changes/2026-10-03-pilot-submodule-adoption.jsonl`

Inside the child repo:
- `pilot/.project.json`: `project_id: px`, `ticket_provider {type: plane, workspace: 33god, identifier: PX, board_id: 35730097-…, state: linked}`, `agents.pilot-pm {role: pm, role_dir: agents/hermes/pm, provisioning_state: provisioned}`, and the `bmad.companion` g33 adapter
- `_bmad/`, `_bmad-output/`, `AGENTS.md` and `CLAUDE.md`, `mise.toml`, `.copier-answers.yml` (CommonProject), `.agents/`
- `.github/workflows/test.yml` and `code-review.yml`, both `runs-on: [self-hosted, Linux, delonet]`. The repo is PRIVATE (`gh repo view`).

Elsewhere:
- Registry: `pj info px --json` reports `registry.status: indexed` at `http://localhost:8764`.
- PM runtime: `~/.hermes/profiles/pilot-pm` exists. The Hermes PM is seated by Flume (`flume hire pm`, `README.md:42`).
- Hindsight bank `pilot` exists.

Flume's registration (`5465d8d`, 2026-09-20) is the minimal version: `.gitmodules`, the gitlink, `components.yaml` and `components/flume.yaml`.

### 4c. The shapes that exist today are inconsistent

| Shape | Members |
|---|---|
| Submodule plus component manifest plus pj-registered board | bloodbank (`bb`/BB), candystore, flume, holocene, momo, pilot (`px`/PX), pjangler (PJAN) |
| Submodule, **not** pj-registered (absent from `pj list`) | hermes-agent-template, mcp-hub, monitoring. Also noted in `director-rule-plan.md:112` on 2026-09-29. |
| **In-tree** component (no own repo) | krebs (72 tracked files). "Promoting it to its own repository is an open issue, not a settled decision" (`PRD.md:91-95`). Also `33god-platform/` and `agents-facade/`. |
| Component manifest but an **untracked nested clone** | candybar (`?? candybar/` in parent `git status`; submodule removed in `5dfe3f8` on 2026-09-17; manifest re-added in `426150d` on 2026-10-26) |
| External manifest (`repo: ../../x`) | skillex, hindsight (`~/.agents`), heyma |
| Standalone, pj-registered with board and PM, **no component manifest** | deckard (`~/code/deckard`, DECK board, `deckard-pm`), wingman |
| **Not registered at all** | the ASM (inside bloodbank); delorenj/agents (`~/.agents`, which holds the zcrank engine and has no board per `initiatives.md:453`, no `agents` row in `pj list`, no `agents-pm` profile) |

---

## 5. Stale or conflicting sources I found (the newer artifact wins)

| Stale claim | Newer truth |
|---|---|
| `README.md:23` (2026-09-20) says "Twelve components". | `components.yaml` lists 14 (2026-10-26). |
| `README.md:51` and `PRD.md:89` describe Candybar as "service registry hub and topology visualization". | `components/candybar.yaml` (2026-10-26) and `CLAUDE.md`: "bloodbank-cron-framework", the single clock. |
| `PRD.md:113-116` calls Flume a planned boundary. | Flume has been a registered submodule since 2026-09-20. |
| The Hindsight ownership rule says "Toad observes". | Toad retired 2026-08-21. |
| The ASM README (`:426`) says scope is always `cli:p:pid.starttime`. | Code rung 4 (`asm.py:218-223`) plus live rows: Claude hook rows are `claude:s:<sid>` with pid 0, which produces duplicate rows. |
| The ASM README says "nothing else re-derives it from the bus". | Deckard's registry and Holocene's `deckard-state.ts` both fold the bus independently. |
| Deckard `AGENTS.md:20` reports status as of "September 23, 2026". | `docs/current-state.md` (2026-10-23) is the current reference. |
| `/tmp/feature-design.md` §7 says Deckard owns pane topology and agent detection. | That was a proposal, never adopted. I-8 (2026-11-05) says the opposite (not a runtime dependency), and the ASM claims agent state. |

## Files relevant to the next step

- `/home/delorenj/code/33GOD/bloodbank/services/agent-hooks/{README.md,core/asm.py,core/asm.lua,core/agents.py,core/sweep.py,bin/asmctl}`
- `/home/delorenj/code/33GOD/bloodbank/services/hook-hub/handlers.toml`
- `/home/delorenj/code/33GOD/_bmad-output/planning-artifacts/initiatives.md` (I-8)
- `/home/delorenj/code/33GOD/_bmad-output/planning-artifacts/director-rule-plan.md`
- `/home/delorenj/code/33GOD/_bmad-output/planning-artifacts/architecture/architecture-33GOD-2026-09-23/ARCHITECTURE-SPINE.md`
- `/home/delorenj/code/33GOD/33god-platform/{components.yaml,components/*.yaml,docs/product-map.md,docs/litellm-agent-control-plane-integration.md,CHANGELOG.pipeline.md}`
- `/home/delorenj/code/33GOD/pjangler/src/crank/panes.ts`
- `/home/delorenj/code/deckard/{PRD.md,docs/adr/001-state-seam.md,docs/current-state.md,crates/deckard-mux/src/proc.rs}`
- `/home/delorenj/code/33GOD/holocene/apps/api/src/{hub.ts,deckard-state.ts}`
- `/home/delorenj/code/Wingman/src/wingman/sources/events.py`