---
title: 'The Director Rule: BMAD for a parent repo with pjangler-registered submodules'
status: 'accepted'
created: '2026-09-29'
accepted: '2026-09-29'
owner: 'grolf (33god-pm)'
---

<!-- Deliberately NOT named epics.md and deliberately uses no `## Epic N:` / `### Story N.M`
     headings: bmad sprint planning turns that grammar into a loop-dispatchable board. -->

# The Director Rule

> **The parent holds outcomes that span children. It never holds work inside one.**
> Applies to any repo with at least one submodule registered as a pjangler project (`pj list`).

## Why

Today the parent is doing its children's backlogs. Verified 2026-09-29:

- Of the 10 stories drafted in `epics.md`, 7 are pure child implementation (Holocene or Flume), 3 are mixed (1.3, 2.2, 2.5), **0 are pure integration**.
- Flume has `_bmad/` installed and an empty `_bmad-output/`, so Flume's whole Epic 2 is planned in the parent.
- Story 1.1 (Holocene code) was dispatched by `bmad-loop` from the parent's board. It paused a finished story because the spec stamped a Holocene SHA that does not exist in the parent repo. Story 2.1 stamped a parent SHA and passed, so success depended on which SHA the dev session wrote.
- Story 2.2 was ordered without knowing the 2026-09-23 named-agent work existed (`epic-2-context.md` never mentions it).

BMAD itself gives no help: its planning skills have no story type, owning repo or delegated story, and `bmad-loop` treats every `sprint-status.yaml` row as code to implement.
`bmad-architecture` is the one BMAD skill whose purpose ("keep separately built parts consistent") is director-level.

## The invariants (borrowed from how companies do it)

1. **Level is decided by who must be involved, not by size.** Parent artifact if and only if at least two children, or a timing dependency a child cannot see, are involved.
2. **One owner per fact.** Implementation facts belong to the child. Integration, timing and dependency facts belong to the parent.
3. **Link, don't copy.** The parent refers to `flume:2-1-<slug>` or `FLUME-12`, never restates scope.
4. **Pull, not push.** Delegation is a request the child accepts through its own intake and its own BMAD flow.
5. **Status is derived, never re-entered.**
6. **Acceptance-criteria split.** Parent ACs are checkable at the seam. A parent AC that needs a child's internals is a child AC in disguise.
7. **Default interaction is X-as-a-service at a contract seam.** Joint work is a time-boxed exception with an end date.

## Where each artifact lives

| Artifact | Parent (33GOD) | Child (submodule) |
|---|---|---|
| PRD | Platform PRD: requirements that only make sense across children | Product PRD (DeloHQ is a Holocene product) |
| Architecture | Cross-cutting ADs: authority boundary, inter-project contracts, deployment topology | Internal architecture and package layout |
| Epics | **Initiatives** in `initiatives.md` (integration outcomes) | Implementation epics in the child's `epics.md` |
| Stories | **Integration stories** (seam outcome plus delegations) | Implementation stories, specs, loops |
| `sprint-status.yaml` | **None** (see Guards) | The child's own; the loop runs here |
| Status | Plane board (Grolf) plus a derived rollup (Phase 3) | Child's board |

**The parent MAY hold:** Initiative, Integration Story, Milestone (a dated, checkable seam state), Dependency (`A blocked_by B`, cross-project), Decision (ADR plus `bloodbank.repo.decision.recorded`), traceability map (FR to child epics, derived).
**The parent MAY NOT hold:** a story owned by a child; any AC naming a path or symbol inside a child; a copy of a child's epic or story text; a child story key as its own key; a `spec-*.md` for child code.

### Keys

Parent keys are non-numeric: `I-1` for an initiative, `I-1.3` for an integration story.
The loop parser accepts only `epic-<digits>` and `<digits>-<digits>-<slug>` rows and ignores everything else, so a parent story can never be picked up even if someone pastes it into a sprint-status file. This is a deliberate departure from fork 3's reserved-numeric-range idea (`epic-101`), which would parse and therefore be dispatchable.
Cross-references are always project-qualified (`flume:2-1-portable-named-agent-contract-…`). A bare `2-1` is not a valid cross-project reference; `2-1` already exists on at least 10 boards under `~/code`.

## Delegation protocol

1. **Author.** Grolf writes an Integration Story: outcome, seam ACs, `delegations[]`, `depends_on`. No task breakdown.
2. **Request.** For each delegation Grolf sends the child a Work Request: outcome, seam AC, priority signal, back-link (`33GOD:I-1.3`), labels `from:33god` and `int:I-1.3`. It says what must be true at the seam, never how.
   - Preferred (pull): Bloodbank command `bloodbank.cmd.agent.invocation.start` to the child PM, whose own intake creates the ticket and, through the child's BMAD flow, whatever epic or story it wants.
   - Practical form today: file the Work Request as a ticket on the child's board. The Plane-to-Bloodbank lane (ticket created, then grooming, then `bloodbank.cmd.agent.invocation.start`) delivers it to that board's PM. Filing goes through `px`.
   - A child with no PM has no receiver; hire one first (Flume was in this state until 2026-09-29, now `flume-pm`).
3. **Link.** A Plane relation (`blocked_by` or `relates_to`) from the parent ticket to the child ticket, through `px` (the only Plane writer).
4. **Implement.** The child owns triage, refinement, spec, loop, review and merge, run inside the child.
5. **Signal.** Child ticket Done emits `bloodbank.repo.task.completed` (schema exists). Grolf's reconcile pass matches it to the delegation.
6. **Verify at the seam.** "Child Done" is not "integration done". The parent story closes only on parent-owned evidence: a smoke command, event query or contract test that exercises the seam.

## Guards, strongest first

1. **No `sprint-status.yaml` in the parent.** Tested in a scratch project: with no board, `bmad-loop validate` fails and `run --dry-run` errors. This is the hard guard against `bmad-loop`. (Interactive `/bmad-build` can still be invoked, so also add the AGENTS.md pitfall.)
2. **Non-numeric keys**, so nothing in the parent parses as a loop row.
3. **`director.scope` lint in `pj audit`** (deterministic, no LLM):
   - R1 parent epic or story text must not reference paths inside a registered submodule.
   - R2 a story owned by a child must not be in a parent board.
   - R3 warn on title or AC overlap with a child epic or story (duplicate suspicion).
   - R4 every delegation resolves to a ticket ref or `pending`; orphan tickets labeled `from:<parent>` warn.
   - R5 fail if a parent story's spec or diff touches a child path. This would have flagged Story 1.1 on day one.
4. **Grolf's charter.** Its "never mutate code" rule is prose only today; only the interactive Momo agent has a structural no-Edit/Write guard. Whether Hermes can enforce a tool allowlist for Grolf is unverified, so do not rely on the charter alone.

## Grolf's role

- Flume composes Grolf's SOUL from `roles/pm.md`, shared by every per-repo PM. Do not hand-edit `SOUL.md`. Add a `director` role file and re-compose with `flume remediate hermes.pm-scaffold 33god`.
- New directives: never author a story owned by a child; delegate by request, never by task list; link, don't copy; derive status; close only on seam evidence; parent presence is opt-in. The list of children comes from the pjangler registry, never hand-maintained.
- Lifecycle: delegation is an axis, not a new phase.
  - triage: the first question becomes "who owns the code?"; child-owned means convert to a delegation, do not decompose.
  - refining: repair seam ACs, strip implementation ACs.
  - in progress: WIP=1 applies to parent-owned work only; waiting on a delegation is a relation, not a worker.
  - review: inspects seam evidence, not child code.
  - done: derived, never set by hand.
- BMAD at the parent level: `bmad-prd`, `bmad-architecture`, `bmad-correct-course` (to deliver a delegation into a child). Not `bmad-build` or `bmad-loop` for child work.

## Child side

Each child needs `_bmad/` installed (all but two already have it), its own `epics.md`, and its own board.
A delegation enters through `bmad-correct-course`, then a `bmad-sprint-planning` refresh, then `bmad-loop` run **inside the child**. Running in the child also removes the submodule baseline mismatch.
The child's resulting story key is recorded back on the parent story as a qualified ref.

## Prerequisites found (all verified 2026-09-29)

- **Flume's PM is `flume-pm` ("Flumey")**, created 2026-09-29: `flume/.project.json` lists it as provisioned, the Hermes registry row has `bloodbank.enabled: true` and `target_agent_id: flume-pm`, its `FLUME` board is `bf5663f0-8d37-41c6-97a3-437d45d64523`, and `hermes-flume-pm-gateway.service` is active. Registered and running; not yet exercised by a delegation.
- **`px` cannot go cross-board:** `~/.config/krebs/manifests.json` does not exist, and `px` has no relation or link command.
- **Plane cross-board relations exist:** `GET .../work-items/{id}/relations/` returns 200. POST is untested.
- **Holocene is not in the pjangler registry.** It has a PM and a `HOLOC` board in the Hermes registry. Only `pjangler`, `bb`, `flume`, `candystore` and `momo` are registered among the 8 submodules; `hermes-agent-template` and `mcp-hub` are not, and a rule keyed on registration excludes them.
- **pjangler is already in the loop for this:** `pj audit` has a rule framework (`AuditFinding`, existing `bmad.*` rules), so `director.scope` fits its shape.

## Where today's parent epics land

| Parent today | Verdict | Landing |
|---|---|---|
| Epic 1 (1.1, 1.2, 1.4, 1.5) | Holocene implementation | Move to Holocene BMAD; 1.1 already done, leave a tombstone `moved_to: holocene:1-1` |
| Story 1.3 | Split | Flume read-transport decision (AD-5) becomes a parent integration story; consumer work goes to Holocene |
| Epics 3-6 | Holocene implementation | Move to Holocene. The parent keeps one initiative, "DeloHQ executive surface", with only the seam stories (evidence contract, action catalog and receipt providers, Telegram and gateway boundary) |
| Stories 2.1-2.4 | Flume implementation, and already partly on Flume's board (FLUME-16, FLUME-21) | Not a blind move: reconcile with Flume's existing backlog. Delegated to Flumey as FLUME-25; 2.1 is done (tombstone); Flumey decides what becomes Flume BMAD stories and replies with a ref per story |
| Story 2.5 | Genuine integration (Flume, Bloodbank, gateway) | Stays in the parent as an integration story |
| FRs, NFRs, AD-1 | Platform PRD and architecture | Stay. AD-2 and AD-11 (package layout) move to Holocene architecture. FR-to-epic map becomes a derived table |

**Story 2.2 rescope (from the 2026-09-23 overlap check).** The Hermes profile, systemd and registry mechanics already exist as template steps 10, 70 and 80, but step 10 dies without an owning repo and `<project>/.agents/skills.json`. Story 2.1's validator also re-invented identity rules more loosely than the Sep 23 `readRoleIdentity()`. So 2.2 becomes: (1) make the 2.1 validator reuse the Sep 23 identity rules, (2) let step 10 accept a desk as its owning root, (3) build the new harness runner. It becomes Flume's first story.

**Superseded in part (2026-09-30).** Flume's Plane board already holds `FLUME-21` ("flume hire <name>: a named officer bound by banks, not a directory": hire by name with a charter instead of a repo, binding by declared banks, no faked repo) on top of the `FLUME-16` memory epic (`FLUME-17` to `FLUME-20`, `FLUME-22`), filed about 2026-09-22, four days before Epic 2 was written. The earlier overlap check looked at code and commits and missed the board. The rescope above is now Flumey's call under `FLUME-25`.

**Refinement to the rule.** A child's backlog is not necessarily BMAD: Flume's real backlog is 25 Plane tickets (`FLUME-12` and `FLUME-16` are Plane-native `[EPIC]`s) and its `_bmad-output/` is empty. "The child owns its epics" means wherever the child keeps them. `director.scope` R3 (duplicate suspicion) must therefore compare against the child's Plane board as well as its `epics.md`, and a delegation's first step is always "does the child already have this?"

## First dogfood initiative: I-1 "Flume agent rollout throughout the system"

Every story is `owner_project: 33god`; ACs are observable at the seam and name no child internals.

| Key | Story | Delegations | Depends on | Seam AC |
|---|---|---|---|---|
| I-1.1 | Flume and PJangler seam | pjangler, flume | none | For any pjangler-registered project, `flume roster` shows its PM post with zero hand-maintained fields; `pj audit` and `flume review` agree on the same repo; the two binaries share only the handbook contract |
| I-1.2 | Workforce events on the bus | bloodbank, candystore | I-1.1 | Hire, onboard, offboard and review each emit a schema-valid event, queryable in Candystore by correlation id; durable consumers survive restart |
| I-1.3 | Registry and handbook seam | flume, hermes-agent-template | I-1.1 | `flume remediate hermes.registry-parity` is clean across all registry agents; an induced drift is detected within one reconcile cycle |
| I-1.4 | Named-agent invocation through the gateway (was 2.5) | flume, bloodbank, hermes-agent-template | I-1.3 | `bloodbank.cmd.agent.invocation.start` with a named `target_agent_id` yields `started` then `completed` or `failed` with echoed correlation id, with no repo context present |
| I-1.5 | Every project has a declared post | flume, each child PM | I-1.1 | `flume roster` lists every pjangler project with post state in {deployed, planned, none-by-decision}; zero unknown |
| I-1.6 | Company projection sourced from Flume (was 1.3 seam) | flume, holocene | I-1.1 | `/hq` company view is built from one Flume snapshot with a freshness envelope; hierarchy no longer read from `org.yaml`; a Flume change appears in `/hq` within the declared max age |
| I-1.7 | Skill packs survive the round trip | skillex, flume | none | Each named agent's desk `.agents/skills` symlinks resolve to canonical Skillex entries and stay valid after a Skillex sync |
| I-1.8 | Named identity end to end on the board | flume, pilot, krebs | I-1.5 | Plane ticket activity is attributed to the named agent, not only the post, across px and Krebs writes |

## Phases

**Phase 0 (about a day): write the rule and stop the bleeding.**
Land this document; add a one-line pointer in the parent `CLAUDE.md` ("bmad-loop runs in each child, never in the parent"); create `initiatives.md` with I-1.1 and I-1.6 only; freeze new parent implementation stories (Epics 3-6 stay backlog, nothing lost).

**Phase 1: one real delegation, end to end.**
First delegation: hand Epic 2's Flume-owned stories (2.1-2.4) to Flumey so Flume's own BMAD creates Flume's epic (Story 2.1 done, Story 2.2 rescoped). It is real work, it is Flume-only, and it exercises the whole path. Create `~/.config/krebs/manifests.json` to unblock `px --board`; file the ticket on `FLUME` with back-link labels (`from:33god`); add the relation through a minimal `px link`; observe the `agent.invocation.started` and later `task.completed` events; verify the seam by hand. Then repeat with I-1.6 across `HOLOC` and `FLUME`. Success is closing the loop once.

**Phase 2: lint.**
Deliver `director.scope` (R1-R5) to pjangler as a Work Request (the first delegation of the rule itself). Run against the parent. Expect red on Epics 1 and 3-6 on day one; that is the dogfood proof.

**Phase 3: migrate, charter, rollup.**
Move Epic 1 and 3-6 to Holocene and 2.1-2.4 to Flume with tombstones, in small commits verified per repo (the parent auto-checkpoint sweeps cross-repo moves into submodule working directories). Register Holocene with pjangler. Add the `director` role and re-compose Grolf. Add the derived `portfolio-status.yaml` rollup only if the Plane board proves not to be enough; do not build it up front.

## Phase 1 log

- **2026-09-30, cross-board access.** `px --board <child>` needs a registry of `.project.json` paths. The file `~/.config/krebs/manifests.json` was deliberately not created: when it exists, every `px` call on the machine validates every listed path, so one bad entry would break px for all agents. The same registry is passed for one invocation through the `KREBS_MANIFESTS` environment variable (a JSON array; identical semantics, no persistent effect). Promote it to the file once the path is proven.
- **2026-09-30, first delegation.** Work Request filed on Flume's board as `FLUME-25` through `px backlog create` (labels `from:33god`, `int:I-1`). Observed on the bus via Candystore (`127.0.0.1:8683`): `bloodbank.repo.task.created` from `n8n-plane-webhook` at 01:57:32.779Z, then `bloodbank.agent.invocation.started` from `hermes-agent:flume-pm` about 300 ms later. No skipped or failed event.
- **Attribution caveat.** The ticket was created with the shared Plane key, so Plane attributes it to the operator rather than to Grolf. Grolf's own agent token is the fix (an I-1.8 concern).
- **Intake worked (about 3 min).** Flumey groomed `FLUME-25` through the grooming lane: added `spike` and `lifecycle:triaged`, raised priority to `high` ("parent is blocked on its reply"), left state in Backlog, left the description alone. Read from its session in the fleet gateway's `state.db` (session title "Groom FLUME-25 ticket on Plane board"), not from the event alone.
- **Delegation stopped at the handoff.** Moved to Todo with `px move` at 02:02:20Z, which fired `agent.invocation.started` with `reason: ticket-delegation` 219 ms later. Flumey (about 3 min) added four testable acceptance criteria to the description, claimed the ticket (In Progress), and posted a "PM dispatch" comment for "the worker picking this up". It reports it has no agent-dispatch channel in that environment, so **no worker started, the flume repo is untouched, and the reconcile has not happened.** `FLUME-25` now sits In Progress with nobody working on it.
- **Root cause found: no PM on the fleet could dispatch a worker, not just Flumey.** Every command sent to a PM over Bloodbank runs as a turn on the `bloodbank` platform, whose toolsets come from `platform_toolsets.bloodbank` in the target desk's generated config. Nothing set it, so Hermes fell back to a nonexistent `hermes-bloodbank` toolset: MCP tools only. Grooming worked, delegation could not, and nothing errored (all 18 recorded Bloodbank turns had zero native tools). Tracked and closed as `FLUME-26`.
- **Fixed (2026-09-30).** Fleet base `platform_toolsets.bloodbank` = `delegation, skills, todo, session_search, terminal, file, web`; 22 PM desks rendered, the 3 routable non-PM employees (reporter, legal, director) pinned to none. No adapter change and no restart: `delegate_task` is already synchronous on this platform (`supports_async_delivery = False`), and config is read per turn. Guard: audit rule `hermes.bloodbank-toolsets` (flume `f9403c5`), passing on the live fleet.
- **Proven on a fresh ticket (`FLUME-27`, cancelled after).** The PM called `delegate_task`; one worker ran synchronously and returned a `sha256sum` and `wc -l` that match independently computed values; the checkout stayed clean; the PM commented the outputs. Two forks disagreed on sync vs async before this; the code settled it (`delegate_tool.py`, `gateway/session_context.py`).
- **Sessions are per ticket.** A ticket's grooming and delegation turns share one session that keeps its tool schema until `session_reset` (04:00 local or 24 h idle). `FLUME-25` was groomed before the fix, so re-dispatching it immediately did not test the fix, and the PM correctly parked it (Awaiting Decision, `lifecycle:blocked`). It needs a fresh session (after the 04:00 rotation) to be re-dispatched.
- **Still open:** `FLUME-28` (nothing structural stops a delegation turn from claiming In Progress without a worker); fleet-wide `max_inflight: 4` and the 30-minute turn cap; five flume suites that fail on pristine code (`fleet-status`, `fleet-health`, `fleet-scaffold`, `fleet-profile`, `pjan-86`).
- **First real delegation (`FLUME-25`, re-dispatched 2026-09-30 09:41Z, fresh session): dispatch works, completion does not yet.** The PM called `delegate_task` and a worker subagent started (its own session, parent = the PM's). Two more limits showed that the 342 s smoke worker hid:
  1. **Tool deadline (fixed).** Hermes cuts any tool call at `timeouts.tools.*` (stock 420 s). The call errored `timed out after 420.0s`, the worker kept running detached, and the PM, finding it alive, claimed the ticket In Progress and ended its turn. The fleet base now sets both keys to 1800 (= `agent.gateway_timeout`), every desk is re-rendered, and `hermes.bloodbank-toolsets` asserts it (flume `f6398ff`).
  2. **Worker speed (open, needs a decision).** The worker model (`delegation.model` = `deepseek/deepseek-v4-flash` via OpenRouter) has a median 41 s and mean 94 s per call, max 319 s, against a 12 s median for the PM's model. After 22+ minutes the worker was still exploring the repo with no artifact. A reconcile-sized task needs tens of steps, so it cannot fit in one PM turn (30 min cap) at that speed.
- **Where FLUME-25 stands.** In Progress with a worker still running detached; the flume checkout is untouched and nothing has been posted. The PM's turn is over, so nothing will verify the result. `FLUME-26` carries a correction to its close-out (it said "proven"; it was proven for workers under 7 minutes); `FLUME-28` carries the new evidence for the structural guard.
- **Correction (same day): the slow worker did finish.** It wrote the document and posted its reply itself at 10:17Z, about 36 minutes in, after the PM's turn had ended (the detached worker survives its PM; it delivered because its brief told it to write the artifact and post to the ticket). My "no artifact yet" report was stale.
- **Seam verification found real defects (this is protocol step 6 working).** The document claimed `memory.write_bank` "must be exactly `agent-<id>`, enforced by the schema and the validator"; the schema is `^agent-[a-z0-9-_]+$` and the check is `startsWith("agent-")`, weaker than `readRoleIdentity()` (which also rejects reserved banks, a name equal to the post id, and unvalidated `recall_banks`, and caps them at 16). It also filed 2.1 as "covered by FLUME-21" (it is shipped), mapped 2.2 to a ticket whose text does not contain its gaps, and dropped 2.3/2.4 (the owner's inaugural specialists). Sent back through the ticket, not fixed by the parent.
- **Worker model decided: personal Kimi through the AutomaticAI gateway (2026-09-30).** Policy: all agent inference goes through `api.automaticai.io`. Token `hermes-fleet-workers` (scoped to `automaticai/personal/kimi-2.8` and `kimi-k3`, 90 days), delegation set to `automaticai/personal/kimi-2.8` at `high` effort, **staged on `flume-pm` and `fleet-bloodbank-gateway` only** (env is applied at process start; a desk whose process was not restarted would send a literal `${…}` key). Second pass of the same task: **~4 minutes** (vs ~36), gateway ledger confirms `kimi-personal`, native `kimi-for-coding`, effort `high`, quota 0 (subscription), 17 requests, 0.5M prompt tokens. The reviewed correction fixed all four defects, checked against the code (flume `a406c82`; it also filed `FLUME-29`).
- **`FLUME-25` closed by the director after verification; Epic 2 stories 2.1-2.4 tombstoned in `epics.md` with the returned refs** (2.1 done at `flume:6b1f429`+`7c10c85`; 2.2 `FLUME-21`+`FLUME-29`; 2.3 and 2.4 `FLUME-29`). Story 2.5 stays here as `I-1.4`.
- **Fleet promotion (2026-09-30, owner approved: per-member keys, fall back to the fleet key, restarts OK).** The worker routing now lives in the fleet base as a **named provider** (`providers.automaticai`: `key_env`, `extra_body.reasoning_effort: high`) with `delegation.provider: automaticai`; the base maps `AUTOMATICAI_GATEWAY_KEY` to the fleet token (`hermes-fleet-workers`), and each registered member overrides that one line in its delta with its own `hermes-<profile>` token. Two things I got wrong first, both caught by measuring rather than reading: the `base_url` + `${VAR}` design cannot carry a desk's own key inside the shared Bloodbank gateway (config `${VAR}` reads plain `os.environ`; `key_env` goes through the per-turn secret scope), and Hermes never sent the effort for a named provider, so the route default (`max`) applied until it was put in the provider's `extra_body`. Proven on `flume-pm` in the gateway ledger: consumer `hermes-flume-pm`, `kimi-personal`, `kimi-for-coding`, effort `high` requested, quota 0. Guard: flume rule `hermes.gateway-routing` (`451df8e`), red on all 26 members before the rollout.
- **Fleet rollout result (2026-09-30).** 26 of 26 registered members carry their own token (`hermes.gateway-routing` passes: "26 of 26 members carry their own token, 0 use the fleet token"); 33 desks re-rendered; 17 processes restarted one at a time, all healthy (the Bloodbank gateway plus 16 desk gateways). Nine registered gateway units are stopped or absent and pick the config up whenever they next start (`skillex-pm` and `delocontainers-pm` are deliberately stopped; I did not start them). A second member is proven live: `33god-pm` (Grolf) shows consumer `hermes-33god-pm`, `kimi-personal`, `kimi-for-coding`, effort `high` requested, quota 0. Not covered: three legacy desks that are not under base+delta inheritance (`drumjangler-pm`, `nautilus_trader-pm`, `never-deployed-pm`) keep their frozen config, so their workers are unchanged. `condaleeza`'s Telegram reports `missing_credentials` after restart; that is pre-existing (it is a Slack-only agent and logged the same on 26 Sep).
- **The gateway's login is the bottleneck.** `gateway-tokens.py` logs in as `delo-relay` on every call and never logs out. That hit two limits: a fixed-window login limiter (429) and a cap of 50 active sessions (409 `AUTH_SESSION_LIMIT`, sessions live 30 days). I revoked 48 idle leaked sessions with the same three-column write the application uses (`status`, `revoked_at`, `revoked_reason`), because the API only lets a user revoke their own sessions and the admin paths reset passwords or demote. Follow-up worth filing against the gateway tooling: log out after each call, or add a batch mode.
- **Role definition + fallback chain (2026-09-30, `FLUME-32`, Backlog, not yet dispatched).** Owner decisions: `reports_to` is explicit per agent, defaulting to the department manager; fallback chain goes entirely through the gateway. Findings behind it: 1 named agent exists (Grolf; `flume-pm` is a post, not named), 0 Epic 2 repo-independent specialists; hierarchy lives in hand-edited `~/.hermes/org.yaml` (department `manager` + `members`) and nothing in flume writes it; skill loadout, fallback chain and org placement are all set by hand outside the role file. **The owner's chain named five routes and four do not exist** (`personal/sol-5.5`, `personal/sonnet-5.5`, `intelliforia/sonnet-5.5`, `personal/kimi-k2.8` answer HTTP 400; only `glm-5.3` is real). Live catalog: `sol`, `sol-6.1`, `astra`, `claude-opus-5.5` (personal and intelliforia), `glm-5.3`, `glm-5.3-flash`, `kimi-2.8`, `kimi-k3`, `kimi-k3s`; there is no Sonnet route on any account. **Kimi's weekly limit is exhausted right now** (403 on all three Kimi routes; recurring since 09-09), and every other catalog route answers. The ticket therefore requires chain entries to be validated against the live catalog and holds the default values for a follow-up comment.
- **Still open, needs decisions (not done):** everything else that still bypasses the gateway on every desk: the primary model (direct `api.kimi.com/coding`), both fallbacks (`openai-codex` needs the Astra/Sol grant, which is not connected, and paid OpenRouter must be an explicit choice), 16 `auxiliary.*` selectors and `moa` on OpenRouter.

## Risks

- **Ceremony creep** for a solo developer: keep parent artifacts to frontmatter plus seam ACs, and let the machine derive status.
- **Vague seam ACs rot:** require an executable check (smoke command, event query, contract test) per integration story.
- **Reprovision traps:** Grolf's SOUL is generated; edit the Flume role file and re-compose, never the generated file. Four registries record each repo path.
- **`px` is the only Plane writer:** a direct REST relation POST would bypass it; a stopgap must be flagged as a bypass.
- **Lint false positives:** R3 is warn-only; R1, R2 and R5 are path- and registry-based and precise.

## Defaults assumed unless changed

- `bmad-loop` runs inside each child.
- Parent presence threshold: at least two children, or a timing dependency on another child.
- The dependency record is a native Plane cross-board `blocked_by` relation, delivered through `px link`.

## Decisions (2026-09-29)

1. DeloHQ (PRD, epics, AD-2, AD-11) moves wholly to Holocene.
2. Flume gets its own PM rather than Grolf driving the `FLUME` board: `flume-pm` ("Flumey"), created and onboarded 2026-09-29.
3. Parent keys are non-numeric: `I-n` and `I-n.m`.
4. Grolf gets a new `director` role file, composed by Flume, rather than a `portfolio:` block on `pm`.
5. Epics 3-6 are tombstoned in place until Holocene starts them; Flume's 2.1-2.4 move first.

## Status of the phases

- **Phase 0 (2026-09-29):** this plan accepted; pointer added to the parent `CLAUDE.md`; `initiatives.md` created with I-1.1 and I-1.6; `epics.md` frozen with owner notes and tombstones on every epic.
- **Transitional gap:** Epic 1's rows are still in the parent's `sprint-status.yaml` until they migrate to Holocene (Phase 3), so a bare `bmad-loop run` in the parent could still pick up Story 1.2. The rule is to not run it there; the structural guard (no parent board) arrives with the Epic 1 migration.
