# ASM ownership study (2026-11-06)

Status: **proposal, awaiting operator decisions** (see the end). Initiative: I-9 in `../initiatives.md`.

Method: three read-only readers (ASM internals, every consumer, intended ownership in the docs) and one judge told to try to refute the operator's hunch that the ASM is the rightful owner. Reader reports are in `evidence/`. Key defects were re-verified live afterwards (publisher imports the ASM in-process; asm.py never reads `BB_HOOK_PARENT_PID`; ghost rows `asm:a:*:x:22822.11015` exist; `session_id` is empty on every row).

## Verdict

Your gut is right for about half the list. The ASM should own everything that answers "which agent is this, and what is it doing right now": finding agent processes, tying each one to its Claude, Codex or Hermes session id, and its live state (idle, busy, needs you). It should come out of Bloodbank into its own formal repo. Six components in five repos already read it, yet it sits inside Bloodbank's hook plumbing with no manifest, no board and no API, and Bloodbank is the transport layer, which should not hold a state machine. The ASM should not own anything that talks to zellij: which tabs and panes exist, typing into a pane, switching or renaming tabs. Those jobs drive the terminal; they are not agent state, and the ASM's own design says a pane is not an agent's identity (headless Hermes agents have no pane at all). Give that terminal layer to the existing zellij-driver repo, filled with Deckard's well-built zellij code. Deckard and pjangler then become consumers of both, which matches your layering. There are two catches. First, the ASM has been broken in production since hook-hub started routing hooks on 2026-09-13: Claude agents show up twice, ghost rows never expire, and session ids are always empty. Fix that inside Bloodbank before moving it, or the new repo starts life with the bugs. Second, Bloodbank's publisher calls the ASM directly today. Moved out as-is, the bus would depend on something above it, so Bloodbank has to load it as a plug-in (a hook-hub handler) instead.

## The hunch, tested

WHERE THE OPERATOR IS RIGHT
(1) The ASM is the natural owner of agent-level facts. It is the only component with all of these: a single atomic arbiter (core/asm.lua), a process identity that pid reuse cannot fool (pid plus start time), a liveness sweeper, and a live feed of state changes (asm:transitions). It already has six readers: asm-tabpaint, asm-orcapaint, asmctl, flume-hr live.ts, Holocene hub.ts and Wingman events.py.
(2) It deserves a formal repo. It appears in no component manifest, no .project.json and no board (33god-platform components.yaml lists bloodbank as "event-backbone" and names no ASM paths). Its handler scripts live in a third repo (~/.agents/hooks/asm). Its identity constants are copied into hook-hub/hindsight.py. Under the Director Rule, a primitive used by five children should not hide inside one child's services/ folder.
(3) Deckard is a product, not an owner. Its lighting and media are just commands it runs: delohome for Hue, playerctl/wpctl for audio, wingman for voice (~/.config/deckard/config.toml). Its only owner-like code is a second copy of agent detection and state.

WHERE IT IS WRONG OR INCOMPLETE
(1) "Deckard is built on top of the ASM" is the intent, not the fact. grep finds no asm: read in any Deckard crate. Deckard runs its own fold of the bus in deckard-daemon/src/agents.rs (6276 lines, five states). Its ADR-001 (2026-08-17, written before the ASM existed on 2026-09-05) deliberately keeps Redis optional so a stranger can install it. Making the claim true is a migration step, and it needs one decision from you (keep or drop that stranger-install goal).
(2) The ASM should not own pane topology, pane input, tab focus or tab renaming. Those talk to zellij. Two are reads (which tabs and panes exist) and three are actions (type, focus, rename). Putting actions inside a state machine mixes "what is true" with "do something". It would also tie the ASM to zellij, when the ASM has to work for headless Hermes (0 of 1292 Hermes events had a pane, per the docstring at asm.py:168-186) and on hosts without zellij.
(3) Tab painting is a surface that reads the ASM; it is not part of the ASM's core. It can live in the ASM repo as a bundled optional surface, but it uses the terminal layer to rename tabs.
(4) The ASM is broken now, so it must be fixed before it moves. I verified the root cause: bb-hook's ENV_ALLOWLIST has no CLAUDE_PID or CODEX_PID, and the ancestry walk now starts inside hook-hub's publisher child, so it reaches hub.py and never finds the agent CLI. The fix is small and available: bb-hook sends parent_pid = os.getppid() (bb-hook:329), the hub passes it to every handler as BB_HOOK_PARENT_PID (hub.py:253), and asm.py never reads it. The live damage (asm-internals D1-D5): two rows per Claude agent, which hides bells on the tab bar; ghost rows keyed to the hub's pid 22822 that the sweeper keeps alive forever; session_id empty on 37 of 37 rows; Hermes liveness checking unit names that no longer exist (only hermes-gateway.service exists, verified).
(5) There is a layering trap in a naive extraction. publisher.py:136-170 imports core.asm in-process. If the ASM becomes its own repo and Bloodbank still imports it, the transport layer depends on a layer above it.
(6) The best agent-detection code is not the ASM's. pjangler's PJAN-202 panes.ts understands agents launched through an interpreter, caches on (pid, start time, comm), and validates Claude session files. That is stricter than the ASM's exact-name match on 7 CLIs (agents.py:28) and stricter than Deckard's pid-only cache (proc.rs:126). The ASM should take PJAN-202's rules as its canonical implementation, not keep its own.
(7) I-8 needs adjusting, not discarding. It binds a crank to a pane, which the ASM rejects as an identity. The middle path: bind the crank to the agent's session id, and treat the pane as where the agent currently is, looked up on every beat.

## Recommended home

A split across two homes. (1) A new formal repo, delorenj/asm, added as a 33GOD submodule and keeping the CLI name asmctl. It owns agent process detection, agent identity, native session binding (process to Claude/Codex/Hermes session id) and live agent state, including needs-input and its acknowledgement. It also carries the tab and Orca painters as optional bundled surfaces. (2) The existing delorenj/zellij-driver repo, repurposed as the terminal driver and filled with code lifted from deckard-mux. It owns everything that talks to zellij: tab and pane topology, the readiness check, the safe zellij-call wrapper, focus by tab id, rename by tab id, and verified pane input. It knows nothing about agents. Bloodbank keeps hook intake and loads the ASM as a hook-hub plug-in. Crank owns its bindings. pjangler owns project identity and wraps the others in pj commands. Deckard, Holocene, Wingman and Flume only consume.

## Candidates

| Score | Candidate | For | Against |
|---|---|---|---|
| 9 | (f) Split: new delorenj/asm repo for agent facts + repurposed zellij-driver for terminal topology and actuation | Each fact gets one owner at the right layer. The ASM keeps its charter (pane is not identity) and works headless. Terminal code stays in Rust, where the mature version already lives (deckard-mux depends only on deckard-core, verified in its Cargo.toml), so Deckard can link it as a library and keep a single binary. Lower layers never call higher ones. It matches your rule that products and control surfaces consume. | Two repos to formalize (boards, PMs, manifests) while pj import (PJAN-165) has been stuck since 2026-10-03, so both adoptions are manual. zellij-driver carries stale Perth intent-tracking docs that must be archived. The painters straddle both layers. |
| 6 | (a) New standalone ASM repo owning all seven responsibilities | One repo, one board, one PM, which is cheapest for a solo dev. Your gut, literally. The ASM already stores zellij_session/zellij_pane and runs the tab painter. | It makes the state machine also a terminal driver, so an agent-state repo would send keystrokes. It ties the ASM to zellij even though Hermes has no panes. Deckard would have to call a Python tool for topology instead of linking Rust code. The best topology code (deckard-mux readiness gate DECK-42, consistent topology bracketing, focus by id) is Rust and would need a port or a mixed-language repo. As the owner of the four agent facts alone, this candidate scores 8; the 6 reflects taking all seven. |
| 6 | (g) One new repo holding both an ASM module and a terminal module | Formal-repo overhead is paid once, and module boundaries can still enforce that the terminal module never imports the ASM. | Layering then depends on discipline inside one repo instead of repo boundaries. A Rust terminal module plus a Python ASM makes a mixed toolchain. Deckard would depend on the agent-state repo just to list panes. |
| 6 | (e) zellij-driver (existing lower-level repo) | For the terminal half only: public, Rust, named for exactly this job, no agent knowledge (correct for the bottom layer), dormant since 2026-08-09 so nothing breaks if it is repurposed. | Its current scope is Perth intent tracking with Redis, RabbitMQ (lapin) and axum dependencies, and it focuses tabs by name (src/zellij.rs:107). It needs a slim library crate and archived docs. As owner of agent state it would score 2: wrong layer. |
| 3 | (b) ASM stays inside bloodbank agent-hooks | Zero migration. The hook-path fold stays in-process and fast (EVAL p50 0.023 ms per asm.py). The 76 tests stay where they are. | The transport layer keeps owning a state fold. It stays unregistered and invisible to platform:validate. The publisher hard-wires it. Handler scripts and constants stay scattered across three repos. It breaks your rule that every feature lives in a formal repo. Consumers keep reading raw keys because nothing pushes an API into existence. |
| 3 | (c) Deckard's deckard-mux | The most mature terminal code on the box: readiness gate, consistent topology, focus by tab id, tolerant zellij JSON parsing. It is the right code to lift. | Deckard is a product, and products consume rather than own primitives. Its repo is private, and its stranger-install pillar shapes design choices. The deployed binary lacks DECK-42. Its process cache is keyed by pid alone (proc.rs:126), so a reused pid inherits the old verdict. It has no read interface (no socket, no mux subcommand). It runs a competing state machine. I-8 already says it is a reference, not a runtime dependency. Best donor, wrong owner. |
| 2 | (d) pjangler | PJAN-202 has the strictest detection on the box, and pj is your global control surface. | A control surface that owns primitives inverts the layering: Deckard (Rust) would depend on a Node CLI. pjangler's manifest role is provisioning and project identity (AD-1). PJAN-202 is exactly the drift pattern of a wrapper growing its own implementation. It is not even deployed (dist lacks inventoryPanes). |

## Layer model

- L0 Host (zellij, /proc, Redis :6379, NATS, systemd): owns the raw machinery; must never hold 33GOD logic or be "owned" by a component's code.
- L1a Bloodbank (hook intake + transport): owns hooks.master.json, bb-hook, hook-hub and its handler registry, event schemas and subjects; must never own a state fold, import a higher layer (today's publisher.py -> core.asm), or name a product in a subject (today's deckard.evt.attention).
- L1b zellij-driver (terminal driver): owns every zellij call: tab/pane topology by id, readiness check, safe invocation (session, env, timeouts), focus by tab id, rename by tab id, verified pane input; must never know what an agent is or read the ASM.
- L2 ASM (delorenj/asm): owns agent process detection, agent identity (pid+start time, or Hermes profile when headless), native session binding, live state, needs-input and ack, liveness, the transition feed and its history events; may read Bloodbank hook frames, /proc, Redis and optionally zellij-driver for tab names; must never type into a pane, focus, rename, or use a pane as identity.
- L2' Peer fact owners (pjangler project identity registry :8764, Candybar clock, Krebs ticket lifecycle): each owns one fact; must never re-derive agent or terminal state.
- L3 Features (crank, hindsight-hooks, ...): own only their own state (zcrank:*, their jobs and schedules) and compose L1/L2 atoms (crank checks ASM "idle", then calls zellij-driver send); must never keep a private copy of topology, detection or state.
- L4 Control surfaces (pj, Holocene): wrap and chain lower commands and render read models; must never grow their own implementation of a primitive (PJAN-202 is the cautionary example).
- L5 Products and desktop surfaces (Deckard, Wingman, tab painter, Orca painter, Orca, nanoleaf): render and act through lower layers; Deckard's lights and media stay commands to delohome/playerctl/wpctl; must never run a second agent-state machine.

## Atom ownership (proposed)

| Atom | Owner | Interface | Copies to retire | Notes |
|---|---|---|---|---|
| pane.topology (sessions, tabs by stable tab_id, panes by pane_id, tab membership, readiness) | zellij-driver | zdrive tabs --json; zdrive panes --json [--session S] (one consistent snapshot bracketed by list-tabs, readiness-checked); Rust library crate for Deckard | deckard-mux panes.rs/cli.rs/readiness.rs (lifted, then deckard-mux becomes a thin adapter); asm-tabpaint list-panes --tab text parse (asm-tabpaint:117-156); zcrank.py:260 panes_for, :269 tab_owners; zcrankctl:156 panes_with_number, :201 live_tabs; pjangler index.ts:402 liveTabs, :469 runListPanes and the pane-cwds.json cache; Wingman sources/zellij.py list_tabs/list_panes; nlpanels zellij.py; orca-sync-repos:37 | Live list-panes --json --all took 4.2 s, versus about 10 ms for the text form (consumers L4). One owner means one fix for speed and for the column parsing (two-space versus whitespace splitting, L11). pane_cwd and terminal_command are unreliable and must not be used for attribution. |
| zellij invocation (session flag, env handling, timeouts, readiness check) | zellij-driver | zdrive zj -- <args>; library function | per-copy env -u ZELLIJ... in zcrank.py:249, zcrankctl:146, index.ts:402; asm-tabpaint blanking vars to ""; crank-engine SKILL.md raw calls | The deployed Deckard lacks the DECK-42 readiness check, which matters because polling a starting session can crash zellij. |
| tab.focus | zellij-driver | zdrive focus --tab-id N --json | Wingman zellij.py:105 go-to-tab-name; zellij-driver src/zellij.rs:107 (by name); legacy streamdeck controller; zcrankctl:218 resolve_tab fuzzy prefix | By id only. Focusing by name breaks as soon as the painter adds a glyph (L12). |
| tab.rename | zellij-driver | zdrive rename --tab-id N --name S | raw rename-tab-by-id in asm-tabpaint | A primitive with no policy. Deciding what a tab name should show belongs to the painter. |
| pane.input | zellij-driver | zdrive send --pane P --expect PID:STARTTIME (--text T / --keys K) --verify --json (refuses if the pane no longer hosts that process; reads the screen back) | crank-engine SKILL.md:36 raw write-chars/send-keys; zcrank engine raw write-chars; Wingman act.py (becomes a client) | "Only when the agent is idle" is a condition the caller checks through the ASM. The terminal layer checks only that the expected process is still in the pane. Deckard keeps sending no input, by design. |
| agent.process (which executables are agents; pid, start time, comm, argv, cwd, pane id from environ, tty, foreground) | asm | asmctl agents --json; data/agent-clis.toml, checked against bloodbank hooks.master.json | bloodbank agents.py:28 AGENT_COMMS and asm.py:85 COMM_FOR_CLI (replaced); pjangler panes.ts:41 AGENT_CLIS + :280 ProcScanner (rules ported into the ASM, then panes.ts becomes a client); Deckard proc.rs:73/:126 in 33GOD mode; flume-hr ASM_CLIS; zcrank screen-scrape detection as a primary source | Use PJAN-202's rules (interpreter-aware matching, the (pid, start time, comm) cache, tty and foreground ranking) as the canonical ones. They correctly demote daemonized processes like opencode serve (L3). |
| agent.identity (scope) | asm | scope field on every row and output: cli:p:pid.starttime, or hermes:a:profile when headless | hook-hub/hindsight.py:277-283 copied constants (read from asm data instead); Deckard registry keys zellij:{session}:{pane} | Fix in place first: start the ancestry walk at BB_HOOK_PARENT_PID; never key to the hub pid; merge the discovered and observed rows into one per agent. |
| agent.session (native session id: Claude sessionId, Codex thread id, Hermes session) | asm | asmctl state --json --session S / --pid P; new index asm:idx:sid:{cli}:{sid} -> scope; session_id field actually filled | pjangler panes.ts:391 readClaudeSession (ported); Deckard attribution.rs fallback ladder; hub receipts.py native_session_id logic stays in the hub but feeds the ASM through BB_HOOK_SESSION_ID | Sources: hook payload or BB_HOOK_SESSION_ID, ~/.claude/sessions/<pid>.json validated against start time, CODEX_THREAD_ID, hermes terminal_breadcrumbs. UNVERIFIED: whether a Claude session id survives /clear or resume. |
| agent.state (10-state fold) plus one shared coarse display mapping | asm | asmctl state --json; asmctl watch --json (NDJSON); Redis schema v1 (asm:a, asm:live, asm:transitions); bus event bloodbank.evt.agent.state.transitioned (new, schema owned by bloodbank) for Candystore history | Deckard deckard-daemon/src/agents.rs fold (33GOD mode; kept only as a no-Redis fallback if you keep G6); holocene deckard-state.ts and agent-activity.ts latches; nlp:pane:* writer; zcrank.py:327 classify and zcrank-gate LLM state (fallback only); Wingman classify ASM_MAP and glyph reading | Ends 8 state vocabularies (L9). The display mapping that collapses 10 states to Deckard's 5 lives in the ASM, so Holocene, Deckard, Wingman and orcapaint agree by construction. |
| agent.attention (bell versus gate, lifetime, ack) | asm | part of agent.state; asmctl ack SCOPE | Deckard AttentionBroker pending-amber state (Deckard keeps its approval UI); handlers.toml:328 asm-blocked-amber workaround | You choose one lifetime: the ASM's 30-minute bell and 12-hour gate, or Deckard's never-decays amber. |
| agent-to-pane join (which agent is in which pane and tab) | asm | asmctl agents --json --topology (adds tab_id/tab_name by calling zdrive when present) | pj crank panes as a provider (becomes a wrapper); Wingman fleet.py best_rows workaround | The ASM depends downward on zellij-driver here, and only optionally. |
| tab painting and marker set | asm (surfaces/tabpaint, an optional desktop surface) | markers.toml as data; painter publishes base (glyph-free) name per tab_id | glyph regexes at zcrank.py:79, zcrankctl:55, zcrank-gate.py:75, index.ts:69, Wingman zellij.py:17, crank-watchdog.py:44 | Name stripping becomes unnecessary once every consumer keys by id (I-8). The session comes from config, no longer hard-coded "Workspace". |
| crank.binding | crank (delorenj/crank, to be created) | crank bindings --json; keyed by (cli, session_id), pane looked up live through the ASM | pjangler index.ts canon/candidateNames/resolveTabForProject; zcrankctl stored_keys; crank-watchdog canon; Wingman fleet.py crank_enabled | pj crank becomes the TUI and wrapper only, matching your framing of pjangler. |
| agent.hooks and event vocabulary | bloodbank | hooks.master.json; hook-hub handler drop-ins (new); sync.py --check | deckard hooks.rs fallback installer; publisher.py hard-wired _asm_observe | Unchanged owner. Bloodbank stops importing the ASM. |
| project.identity | pjangler | GET :8764/v1/resolve (new) and pj project resolve --json | bloodbank board.py board_for (moves into the ASM temporarily, then becomes a client); Deckard projects.rs:203; Wingman fleet.py:113; asm-orcapaint deepest-worktree rule | Unchanged from the feature design. This is pjangler's legitimate owned fact under AD-1. |

## New repo: delorenj/asm (33GOD submodule at ~/code/33GOD/asm; the CLI keeps the name asmctl)

The single source of truth for agent facts on a host: which processes are agents, who each agent is, which native session it is running, and what it is doing right now (including needs-input and its acknowledgement). It also covers liveness, the live transition feed and durable transition events. It also ships two optional desktop surfaces (tab painter, Orca painter) that read those facts. It never talks to zellij except an optional read of zdrive for tab names.

**Moves in**
- bloodbank services/agent-hooks/core/asm.py, core/asm.lua, core/sweep.py, core/agents.py (history kept via git filter-repo over the 16 ASM commits)
- a copy of core/resp.py (bloodbank keeps its own) and core/board.py (temporary, until pjangler /v1/resolve exists)
- bin/asmctl; bin/asm-tabpaint and bin/asm-orcapaint into surfaces/
- ops/systemd/asm-* units, installed by one mise task (today the painter symlinks were made by hand)
- tests/test_asm.py, rewritten to run against a throwaway Redis on a random port with a key and channel prefix
- ~/.agents/hooks/asm/log-transition.sh and notify-stale.sh from delorenj/agents
- identity constants (IDENTITY_ENV_FOR_CLI, NOT_AN_AGENT_PROFILE) as a data file that hook-hub/hindsight.py reads
- PJAN-202's detection rules from pjangler src/crank/panes.ts, ported to Python: interpreter-aware matching, the (pid, start time, comm) cache, Claude session-file validation, tty and foreground ranking
- the ASM section of agent-hooks/README.md (lines 376-445), corrected to match the code
- the sweeper's clock record: an owner-approved exception inside this repo, or its Candybar manifest
- feature.toml (provides agent.process, agent.identity, agent.session, agent.state, agent.attention; requires agent.hooks and redis) and contracts/atoms/*.toml with live probes

**Stays out**
- hooks.master.json, bb-hook, hook-hub, publisher.py, event schemas and NATS subjects (bloodbank)
- every zellij call: topology, readiness, focus, rename, pane input (zellij-driver)
- crank bindings (zcrank:*) and the crank engine (crank)
- project identity (pjangler registry)
- Deckard's Stream Deck, approvals, office buttons, lights and media (deckard, via delohome/playerctl/wpctl)
- durable history storage (Candystore, fed by the bus event)
- ticket-claim policy behind asmctl who (fleet PM or Krebs; operator decision)
- any rewrite into another language

**API surface**
- CLI (all verbs support --json): asmctl agents [--topology] (one row per live agent: scope, cli, pid, starttime, session_id, cwd, zellij_session, pane, state, display_state, since); asmctl state [--scope S | --pid P | --session S | --pane SESSION:PANE]; asmctl watch (NDJSON transitions); asmctl log SCOPE; asmctl ack SCOPE; asmctl sweep; asmctl doctor (live probe: duplicate rows, ghost rows, empty session ids, sweeper age, CLI list versus hooks.master.json); asmctl observe (the hook-hub handler entry point)
- Redis schema v1, documented in schemas/redis/asm.v1.toml and keeping today's key names so no consumer breaks: asm:a:{scope} hash (session_id now filled), asm:t:{scope} stream, asm:live zset, asm:idx:pane:{sess}:{pane}, new asm:idx:sid:{cli}:{sid}, asm:seen, asm:sweeper; pub/sub asm:transitions. Consumers may read keys; only asm.lua writes
- Bloodbank, consumed: hook frames through a hook-hub handler drop-in row, with BB_HOOK_PARENT_PID and BB_HOOK_SESSION_ID in env and a client-side timestamp for ordering
- Bloodbank, published: bloodbank.evt.agent.state.transitioned (one per real state change; schema owned by bloodbank) so Candystore keeps history beyond the 900 s stream TTL
- No socket. Redis is the read path for daemons (Deckard already has a redis-store feature), and the CLI with --json is the read path for scripts and agents

**Runtime:** Python 3 standard library plus the existing Redis Lua arbiter, moved as-is rather than rewritten. Packaged with pyproject.toml and installed with uv tool install, so asmctl is on PATH. Units are user systemd .service files fired by Candybar, or the 15 s sweeper under a recorded exception. Tests use a throwaway redis-server on a random port and never 6379. Visibility follows bloodbank (public today): GitHub-hosted runners are allowed if public, otherwise [self-hosted, Linux, delonet].

**Formal repo shape:** Follow the Pilot adoption (33GOD commit 808817f). In the parent: .gitmodules entry and gitlink 'asm'; 33god-platform/components/asm.yaml (role agent-state, repo ../asm, health asmctl doctor --json, source_of_truth core/asm.lua + schemas/redis/asm.v1.toml + data/agent-clis.toml, changelog topics); a components.yaml entry; a CHANGELOG.pipeline.md entry and changes/*.jsonl; features.toml catalog row 'asm'. In the child: .project.json with ticket_provider (new Plane board, identifier ASM) and agents.asm-pm (seated with flume hire pm); _bmad/ and _bmad-output/; AGENTS.md with CLAUDE.md/GEMINI.md symlinks; mise.toml with test, install and doctor tasks; CommonProject copier answers; .agents/skills as the skills source of truth; a CI workflow; hindsight bank 'asm'; registered with pj (pj info asm --json shows indexed). The zellij-driver repurpose gets the same shape: board, PM, external manifest, archived Perth docs.

## Migration slices

| # | Repo | Size | Slice | Depends on |
|---|---|---|---|---|
| 1 | delorenj/agents | 3-4 hours | Write the system-wide migration skill (layer model, atom ownership table, rules: one owner per atom, products and control surfaces consume, no new copies of a primitive, every feature has a formal repo, pins are temporary bandages with a ticket) and add a one-line pointer to it in ~/.agents/AGENTS.md | operator approval of this decision |
| 2 | delorenj/33god | 2 hours | Record the decision in the parent: rewrite I-8 owners and acceptance criteria, add the cross-project initiative for agent-state and terminal ownership with delegations to bloodbank, asm, zellij-driver, deckard, pjangler, holocene, flume and wingman | 1 |
| 3 | delorenj/bloodbank | 3 hours | Isolate ASM tests from production: throwaway redis-server on a random port, configurable key and channel prefix so tests can never reach the live painters, and add test_asm.py to CI (today CI runs only test_attention*.py) | none |
| 4 | delorenj/bloodbank | 1-1.5 days | Fix ASM identity in place: start the ancestry walk at BB_HOOK_PARENT_PID, fill session_id from BB_HOOK_SESSION_ID or the payload, never create a scope keyed to the hub pid, merge discovered and observed rows into one per agent, stop treating a per-profile gateway unit as Hermes liveness, drop events older than the last turn boundary using a client timestamp, add asmctl doctor, and purge the listed ghost rows by exact key (never FLUSH) | 3 |
| 5 | delorenj/asm (new) + delorenj/33god (submodule, manifest, changelog) | 1 day | Create delorenj/asm with history (filter-repo), the formal repo shape, pyproject packaging and one install task for all units; bloodbank keeps a temporary shim that imports the installed package | 4 |
| 6 | delorenj/bloodbank + delorenj/asm + delorenj/agents | 1 day | Invert the dependency: hook-hub loads handler drop-ins, the ASM installs its own 'observe' row with per-agent ordering, publisher.py drops _asm_observe and the shim, the asm-log and asm-stale-alert scripts move from delorenj/agents into asm, and hindsight.py reads identity constants from asm data | 5 |
| 7 | delorenj/asm | 2 days | ASM machine interface and canonical detection: asmctl --json verbs, PJAN-202 rules ported, data/agent-clis.toml checked against hooks.master.json, session binding from Claude session files, CODEX_THREAD_ID and Hermes breadcrumbs, asm:idx:sid index, display-state mapping, Redis schema v1 document, atom contracts with live probes | 6 |
| 8 | delorenj/zellij-driver | 2-3 days | Repurpose zellij-driver as the terminal driver: a slim library crate (serde and nix only) lifted from deckard-mux, plus zdrive tabs, panes, focus, rename, send --expect --verify and zj, all with --json; freeze or retire the Perth intent features and archive their docs; formal repo shape | none (runs in parallel with 3-7) |
| 9 | delorenj/asm | half a day | Move the painters onto the new primitives: tabpaint renames by tab id through zdrive, publishes base names and markers.toml, reads its session from config; orcapaint reads the asmctl JSON | 7, 8 |
| 10 | delorenj/pjangler | half a day | pj crank panes becomes a wrapper over asmctl agents --json --topology; delete the duplicated detection in panes.ts; rebuild and deploy the main checkout | 7, 8 |
| 11 | delorenj/crank (new) + delorenj/agents + delorenj/pjangler | 2-3 days | Create delorenj/crank per the feature design: bindings keyed by (cli, session_id) with the pane looked up live through the ASM; the engine checks ASM 'idle' and then calls zdrive send --expect --verify; the crank-engine skill stops sending raw write-chars; then lift the Hermes economics cap as one recorded change | 7, 8, 10 |
| 12 | delorenj/deckard | 2-3 days | Deckard consumes: deckard-mux becomes a thin adapter over the zellij-driver crate; in 33GOD mode, agent state comes from ASM Redis v1; the builtin fold stays only as the no-Redis fallback (if G6 is kept) with its pid-only cache fixed; redeploy, which also ships DECK-42 | 7, 8 |
| 13 | delorenj/bloodbank + delorenj/asm | 1 day | Bus history and subject cleanup: add the bloodbank.evt.agent.state.transitioned schema and have the ASM publish it for Candystore; rename deckard.evt.attention to bloodbank.evt.agent.attention, publishing on both subjects for a short window | 6 |
| 14 | holocene + flume + Wingman | 1-1.5 days | Consumers stop re-deriving: Holocene drops deckard-state.ts and the agent-activity latches in favor of the ASM display mapping; flume-hr reads agent-clis data; Wingman stops reading tab glyphs and subscribes to the new attention subject | 7, 13 |
| 15 | infra + bloodbank + delorenj/agents + deckard | half a day to 1 day | Retire leftovers: nanoleaf nlp:pane writer reads the ASM instead, the dead zellij-notify handler row, asm-log's bash spawn on every transition, the stale Hermes-profile zcrank.py, the glyph regex copies, and Deckard's agents.rs fold if G6 is dropped | 9-14 |

## Effect on the feature-packaging design and I-8

FEATURE DESIGN (/tmp/feature-design.md)
(1) Section 7 owners change:
- pane.topology, zellij invocation, pane.input and tab.focus move from deckard-mux to zellij-driver (zdrive ... --json).
- agent.process moves from deckard-mux to the ASM.
- agent.session and agent.state move from "bloodbank ASM" to delorenj/asm.
- The tab marker set moves to asm surfaces/tabpaint.
- Add a new tab.rename atom owned by zellij-driver, and an agent.attention atom owned by the ASM.
- Deckard is no longer an owner anywhere. It becomes a consumer feature (deckard-attention requires agent.state, pane.topology and tab.focus).
(2) crank's feature.toml:
- pane.input leaves crank's [provides] (the provisional zcrank-act) and becomes a requirement on zellij-driver.
- The "only when idle" guard becomes crank's own composition: read the ASM, then send.
- The comment "pane.topology's provider owns it (Deckard [mux] session)" now points at zdrive's config.
- crank.binding stays in crank permanently. It does not later move into pjangler, and it is keyed by agent session, not pane.
(3) The install and upgrade transcripts change their owner brackets: [owner zellij-driver] and [owner asm] replace [owner deckard] and [owner bloodbank]. The upgrade step that relocks agent.process to Deckard goes away.

YOUR ITEMS 2-4
(4) Item 3:
- The desired-state file moves from ~/.agents/features.toml (delorenj/agents, [host.*] tables) to features.toml at the root of delorenj/33god. It becomes the full catalog, every feature on by default, and also a planning guide.
- Per-install disables go in a local, untracked override (for example ~/.config/33god/features.toml). Missing means everything is on.
- The engine must refuse, or clearly cascade, when someone disables a feature others need (asm is required by crank, deckard-attention and Holocene).
(5) Item 4:
- The catalog carries no semver ranges such as crank = "^0.4". Features track main.
- A pin is an explicit temporary entry with a reason and a ticket, and pj feature check flags it while it exists.
- The CAND-49 pinned Hermes image is dropped now, not as a later "retire" item.
(6) Item 2:
- Every feature lives in a formal repo. That means delorenj/crank (verified: it does not exist yet) and delorenj/asm must be created.
- Whether a features/<name>/ folder inside an owning repo still counts (hindsight-hooks inside bloodbank) is your call.
- Crank dogfoods the rule first.

I-8 (PANE-BOUND CRANK)
(7) Owners:
- Discovery (process, session, state) moves from pjangler to the ASM.
- The registry moves to crank.
- pjangler keeps the pj crank TUI and wrapper.
- Terminal actions go to zellij-driver.
- PJAN-202's rules, not Deckard's proc.rs, become the reference, ported into the ASM. proc.rs has the pid-reuse bug.
(8) Binding model:
- A crank binds to the agent's session (cli + session id), and the pane is where that agent currently is, looked up on every beat. This reconciles I-8 with the ASM's "a pane is not identity" rule.
- It keeps the acceptance criterion that a rename or a moved pane never changes which agent is driven.
- After a zellij restart, the session id finds the agent again (UNVERIFIED whether a Claude session id survives /clear).
(9) Acceptance and dependencies:
- The criterion "per-tab counts equal deckard status agents=" becomes "equal asmctl agents --json --topology". Deckard agrees by construction once slice 12 lands.
- I-8 gains delegations to bloodbank (identity fix), asm and zellij-driver, and depends on slices 4, 7 and 8.
- The Hermes economics cap stays until slice 11.

## Risks

- Extracting before fixing would freeze the live identity bugs (duplicate Claude rows, ghost rows on hub pid 22822, empty session_id) into the new repo. Slice 4 must land and pass asmctl doctor first.
- Moving the ASM out of the publisher process adds a process spawn per hook and can reorder events (hub publish is async with 2 slots, hub.py:57). The handler needs per-agent ordering and a client timestamp. Measure hook latency before and after.
- Redis 6379 is production and shared with nanoleaf and Holocene. Any test or ghost-row purge can reach live painters or wipe state. Test helpers must force a random port, purges delete exact keys only, and nothing ever runs FLUSH* (the memory notes a past live FLUSHALL incident).
- Claude session-id stability is UNVERIFIED. If /clear, compaction or resume changes the id, session-keyed crank bindings drop. They need a fallback (same cwd + same pane + same CLI, confirmed by you) and a doctor finding.
- Deckard's stranger-install goal (ADR-001, pillar G6) conflicts with requiring the ASM's Redis. Keeping a fallback fold means two state machines survive in standalone mode, so they must be differential-checked and never trusted equally.
- Renaming deckard.evt.attention breaks Wingman (events.py:34) and Deckard unless both subjects are published for a while.
- Two formal repos to stand up by hand (pj import, PJAN-165, has been stuck since 2026-10-03). The overhead may tempt a shortcut that leaves zellij-driver half-repurposed, with stale Perth docs misleading future agents. Archive those docs in the same commit.
- zellij's JSON is unstable (fields vanished by 0.44.3; list-panes --json --all took 4.2 s live). The terminal driver must tolerate missing fields and prefer the fast reads.
- Raw-key consumers (Holocene, Flume, Wingman) break if key names change mid-migration. Keep the v1 names until slice 14 is done.
- The 15 s sweeper is still a clock outside Candybar. Its current exception lives in Candybar's policy file, owned by 'Candybar / infra owners', not in the ASM's component as the global rule requires.
- Scope creep: rewriting the ASM in Rust or adding a socket daemon is tempting and buys nothing now. Move first, then improve.
- The painters live in a platform repo but are desktop-only. Keep them optional so a headless install does not pull zellij expectations.

## Decisions only the operator can make

- [ ] Approve the split: the ASM gets agent facts (process, identity, session, state, attention); zellij-driver gets everything that talks to zellij (topology, focus, rename, pane input). The alternative is one new repo for all seven.
- [ ] Repo name and visibility: delorenj/asm with the CLI staying asmctl, public like bloodbank today, or private.
- [ ] Repurpose zellij-driver (freeze or retire the Perth intent tracking and archive its docs), or start a fresh repo for the terminal driver.
- [ ] Deckard's stranger-install goal (ADR-001, G6). Keep it, so Deckard keeps a builtin agent fold only as a no-Redis fallback, or drop it, so Deckard requires the ASM and deletes agents.rs. Note that the deckard repo is PRIVATE today even though its pillar says public.
- [ ] Is a failed tool call 'red'? The ASM says yes for 30 s. Deckard and Holocene say only a failed turn or invocation is an error. Recommendation: Deckard's rule, because agents recover from tool errors constantly.
- [ ] Needs-input (amber) lifetime: the ASM's 30-minute bell and 12-hour gate with ack, or Deckard's never-decays amber.
- [ ] The 15 s sweeper: approve a recorded exception inside the asm repo (cheap), or fund computing staleness on read so the timer can be deleted (about 2 days).
- [ ] Does 'every feature in its own formal repo' allow a features/<name>/ folder inside the owning repo (hindsight-hooks in bloodbank), or must every feature get its own repo?
- [ ] Crank registry owner: the crank repo (recommended) or pjangler, as I-8 says today.
- [ ] Ticket-claim selection (asmctl who): keep it in the ASM as a query, or move it to the fleet PM or Krebs.
- [ ] Approve the one-off deletion of the specific ghost rows (claude/copilot/gemini/hermes/opencode :x:22822.11015 and their stream and index keys) as part of slice 4.

## Live defects found

- Identity ladder broken since 00f36a8 (2026-09-13). Verified: bb-hook ENV_ALLOWLIST (hook-hub/client/bb-hook:58) has no CLAUDE_PID/CODEX_PID; the rung-3 walk in asm.py starts at os.getpid() inside hook-hub's publisher child; yet bb-hook sends parent_pid=os.getppid() (bb-hook:329) and hub.py:253 exports BB_HOOK_PARENT_PID, which asm.py never reads.
- Two rows per Claude agent (claude:s:<sid> observed plus claude:p:<pid> discovered, stuck at unknown) on 8-9 panes. Per the asm-internals replay, this hides bells on panes 93 and 160 and makes asm:idx:pane flip every 15 s.
- Ghost rows keyed to hub pid 22822 (claude/copilot/gemini/hermes/opencode :x:22822.11015, 'stale for 197.9h'; claude one 'awaiting_human' on pane 41, which does not exist). sweep.py:206-212 refreshes their TTL every tick, so the Holocene stat is permanently critical and the Candybar tab shows red.
- session_id and correlationid are always empty: asm.py:438 hard-codes them to "" and asm.lua:284-285 overwrites them; 37 of 37 rows are empty.
- Hermes liveness queries hermes-*-gateway.service (sweep.py:69-72), but only hermes-gateway.service exists (verified with systemctl --user list-units).
- test_asm.py targets production Redis 127.0.0.1:6379 by default and publishes on the live asm:transitions channel; a test|attention field sits in production asm:seen.
- Layering violations: bloodbank's publisher imports the ASM in-process (publisher.py:136-170, verified); bloodbank publishes a product-named subject deckard.evt.attention (publisher.py:38) and hub.py:188-189 assigns type deckard.v1.agent.attention; the ASM writes a Holocene-named key (holocene:tooling:stat:agent-state-machine).
- Clock policy: asm-sweep.timer's exception lives in candybar/deploy/scheduling-policy.json:43-46 with owner 'Candybar / infra owners', not in the ASM's own component as ~/.agents/AGENTS.md requires. The same file carries blanket OS/vendor exclusions, which the global rule says do not exist (verified by reading the file).
- Deployment lag: the deployed Deckard binary (2026-10-15) lacks DECK-42's readiness check and can crash zellij when polling a starting session; the deployed pj lacks PJAN-202 'crank panes'.
- Deckard proc.rs:126 caches the agent verdict by pid alone, so a reused pid inherits the previous process's verdict.
- The ASM README claims to be the single source of truth ('nothing else re-derives it from the bus'), but Deckard agents.rs and Holocene deckard-state.ts/agent-activity.ts both fold the bus independently.
- The ASM is unregistered: no components/*.yaml, no .project.json, no board. delorenj/agents (which holds the zcrank engine and the ASM handler scripts) is also unregistered.
- handlers.toml:257 zellij-notify is enabled but points at a script that does not exist; asm-log matches every transition and spawns a bash process each time.
- Tab 13 is named 'herm 🔴es': a glyph in the middle of the name that no stripper removes. Crank bindings point at tab names that no longer exist (client-portal, Intelliforia, 'Pile of Dumb Things', Holocene).
- The Hermes profile copy of zcrank.py (Oct 29) is stale against the repo copy (Nov 4); which copy the PM runs is UNVERIFIED.
- hindsight-capture-sweep.service is in a failed state (per the consumers report).
- I-8's acceptance criterion uses 'deckard status' as the oracle, even though Deckard does not own agent state and reads no ASM key.
- Rule breach by an upstream reader: /tmp/asm-keys-survey.txt and /tmp/asm-survey-panes.json were created during the read-only survey and still exist (verified with ls). I did not delete them, because this pass is read-only.

Ticketed so far: BB-32 (ASM tests touch production Redis), BB-33 (ASM identity broken since 2026-09-13).
