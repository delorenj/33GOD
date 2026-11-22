---
title: '33GOD initiatives (integration work that spans children)'
governed_by: 'director-rule-plan.md'
created: '2026-09-29'
---

<!-- The parent holds outcomes that span children, never work inside one.
     NOT epics.md: keys here are I-n / I-n.m on purpose. bmad-loop only parses
     `epic-<digits>` and `<digits>-<digits>-<slug>`, so nothing in this file can be
     dispatched as code. Do not paste these into a sprint-status.yaml.
     Refer to child work only as `<project>:<key>` or a ticket ref (FLUME-12).
     Status is derived from the boards and events, never typed here. -->

# Initiatives

## I-1 Flume agent rollout throughout the system

**Outcome.** Every pjangler-registered project has a declared post held by a named
agent, the workforce is visible on the bus and in `/hq`, and a named specialist can be
invoked with no repo present.
**Owner:** `33god` (Grolf). Implementation is owned by the children named in each
story's delegations. The full story list (I-1.1 to I-1.8) is in
`director-rule-plan.md`; only the two below are authored so far.

### I-1.1 Flume and PJangler seam

```yaml
owner_project: 33god
delegations:
  - owner_project: pjangler
    request: pj audit and flume review agree on the same repo
  - owner_project: flume
    request: roster derives every PM post from the pjangler registry
depends_on: []
```

**Seam acceptance criteria**

- For any project registered in pjangler, `flume roster` shows its PM post with zero
  hand-maintained fields.
- `pj audit` and `flume review` agree on the same repo.
- The two binaries share only the handbook contract; neither imports the other.

**Seam evidence (executable).** Run `pj list` and `flume roster --json`; diff the
project ids and post states. Run `pj audit <repo>` and `flume review <repo>` for one
repo and compare findings on the fields both report.

### I-1.6 Company projection sourced from Flume

```yaml
owner_project: 33god
delegations:
  - owner_project: flume
    request: expose one company snapshot with a freshness envelope
  - owner_project: holocene
    request: build the /hq company view from that snapshot
depends_on: [I-1.1]
```

Resolves the transport decision deferred in the architecture spine (AD-5): how Flume
publishes the company projection, and retiring `org.yaml` as the hierarchy source. It
is the seam half of the former Story 1.3.

**Seam acceptance criteria**

- The `/hq` company view is built from one Flume snapshot carrying a freshness
  envelope.
- Hierarchy is no longer read from `org.yaml`.
- A change in Flume appears in `/hq` within the declared maximum age.

**Seam evidence (executable).** Change a post in Flume; measure the time until the
`/hq` API reflects it; assert it is under the declared maximum age and that
`org.yaml` is not opened during the request.

## I-2 Holocene Auto walking skeleton

**Outcome.** On Jarad's factory Honda Civic Si 2026 AAOS Google built-in system,
activity from multiple harnesses is available through one normalized view; the
driving voice interface routes a confirmed instruction to one supported
conversation, its real reply is heard through Voxxy, and an explicit broadcast
fact reaches multiple subscribers.
The complete conversational loop requires no screen reads or taps while driving;
detailed event browsing remains parked-only.

**Owner:** `33god` for integrated acceptance; `holocene` for the operator-facing
product. The cross-project seam contract is
[Holocene Auto](../specs/spec-holocene-auto/SPEC.md); its companions define current
capabilities, car modes, gaps, and bounded demonstration evidence. Child PMs own
all implementation stories. HOLOC-9 supplies the accepted emulator diagnostic
baseline; the next approved seams are final-answer publication (I-2.2) and isolated
real-speech evidence (I-2.3), not the full integrated driving product.

### I-2.1 Observability, voice, and conversation seams

```yaml
owner_project: 33god
delegations:
  - owner_project: holocene
    request: prove Honda-AAOS emulator feasibility and a legitimate category, installation, and driving-voice path before the integrated surface
    ticket_ref: HOLOC-9
  - owner_project: bb
    owner_component: bloodbank
    request: support schema-valid exact-conversation intent and correlated execution evidence without route substitution
    ticket_ref: pending
  - owner_project: candystore
    request: supply durable correlated event history and reconnect evidence for the car surface
    ticket_ref: pending
  - owner_project: transcription-queue
    owner_component: heyma
    binding_state: requires-reconciliation
    request: reconcile the moved checkout binding and provide schema-aligned final-transcript voice ingress usable from the head unit
    ticket_ref: pending
  - owner_project: infra
    request: verify the existing ASR bridge as a bounded head-unit recognition dependency
    ticket_ref: pending
  - owner_project: pending
    owner_component: hermes-fleet
    request: resolve the runtime-owning project and prove declared conversation continuity with resolved-session evidence
    ticket_ref: pending
  - owner_project: voxxy
    request: provide correlated short speech output with explicit synthesis and playback distinctions
    ticket_ref: pending
depends_on: []
```

**Seam acceptance criteria**

- Two harnesses are observable independently of Deckard panes with identity and
  freshness preserved.
- One confirmed utterance reaches the selected supported conversation and yields
  correlated lifecycle evidence plus an audible response; unsupported routes are
  read-only, never silently redirected.
- A confirmed typed broadcast fact reaches two passive subscribers and durable
  history; publication does not claim subscriber execution.
- Disconnect/reconnect preserves the demonstration history and does not duplicate
  the instruction; Driving/Unknown hides detailed activity but supports the
  validated hands-free selection, instruction, broadcast, reply, and cancel loop.
- First-release driving acceptance requires no display reads or taps; stationary
  staging alone is not final proof of movement-dependent hardware behavior.
- Honda-emulator feasibility, category/testing-route evidence, actual-car
  installation, and driving proof are distinct; host UX restrictions are obeyed
  and actual-vehicle ADB is never an installation dependency.

**Seam evidence.** Execute the staged acceptance sequence and collect canonical
event IDs, declared conversation and resolved-session identifiers, correlation
IDs, receipt and answer readback, device/activation proof, audio playback,
reconnect/broadcast observations, and non-screen interaction evidence as specified
in the contract's `acceptance.md` companion. APK installability alone is not
integration completion.

### I-2.2 Durable final assistant answers

```yaml
owner_project: 33god
delegations:
  - owner_project: bb
    owner_component: bloodbank
    request: publish a final assistant answer with exact invocation and conversation lineage, durable replay, and no repeated execution
    ticket_ref: BB-30
depends_on: []
related_to: [33GOD-16]
```

**Seam acceptance criteria**

- A valid targeted invocation producing a nonempty final assistant answer yields
  one schema-valid message fact, explicitly distinguishable from processing
  completion, commentary, tool output, history, and reasoning.
- Command, target/profile, correlation/causation, logical thread/turn, and native
  session/turn identities remain distinct and traceable. Concurrent or delegated
  turns cannot cross-wire the parent answer.
- Captured results and immutable event identity/body are persisted before publish;
  command acknowledgement follows acknowledged answer and terminal publication.
  Publication/restart/redelivery replays stored facts without rerunning execution.
  Pre-capture ambiguity is disclosed, not called global exactly-once delivery.
- Schema compatibility and deterministic failure/replay tests prove the contract;
  later authorized live verification proves durable Candystore arrival.

**Seam evidence.** Canonical schema validation, exact command/turn/answer identifiers,
restart/publication-failure replay tests, consumer deduplication, and an authorized
live answer row. No ASR, TTS, mobile authentication, or arbitrary terminal resume is
part of this first authority-owner request.

### I-2.3 Isolated real speech and diagnostic playback

```yaml
owner_project: 33god
delegations:
  - owner_project: holocene
    request: prove a known isolated speech waveform through the emulator microphone, real final recognition, local audible acknowledgement, and bounded cancellation
    ticket_ref: HOLOC-10
depends_on: []
prerequisites: [holocene:HOLOC-9]
```

**Seam acceptance criteria**

- A known short synthetic/prerecorded phrase enters the Android microphone path,
  with waveform provenance, sample statistics, duration, and a silence control.
  Canned text written into transcript state cannot satisfy recognition.
- The current recognizer produces a nonempty final transcript and timing/callback
  evidence; unsupported, no-match, or network failure is a reproduced blocker,
  never replaced by a fixture transcript.
- Output derived from that final transcript is audibly rendered with recorded
  guest-output evidence and engine/asset identity. Platform-local diagnostic
  playback is labeled as such, not Vox synthesis or a real agent reply.
- Capture/playback cancellation, focus/resource release, and late-callback handling
  work under permitted host UX. Screen and simulated-key tests do not claim Honda
  steering-wheel, spoken stop, or non-screen driving support.
- No room microphone recording, assistant-default change, Play upload, actual-car
  modification, agent/broadcast dispatch, or direct engine/broker bypass occurs.
  CAP-8 and the eventual live Vox/agent loop remain required and unfulfilled.

**Seam evidence.** Input and output waveform identifiers/statistics, actual ASR
provider/support/final callbacks, transcript and latency, cancellation/focus/host
behavior, and explicit diagnostic-versus-live boundaries. This independent audio
slice may progress alongside I-2.2; shared runtime activation is serialized later.

## I-3 Repository import, dogfooded by Pilot adoption

**Outcome.** An existing local project or remote repository can become an official
33GOD submodule without losing local state or leaving project/workforce bindings
pointing at a retired checkout. Pilot is the first concrete adoption.

**Owner:** `33god` (Grolf), parent ticket `33GOD-79`. PJangler owns reusable import;
Flume owns workforce relocation where a deployment exists. Ticket titles initially
used I-2 in error; this I-3 key is canonical, and both boards carry the correction.

```yaml
owner_project: 33god
ticket_ref: 33GOD-79
delegations:
  - owner_project: pjangler
    request: import a local checkout or remote repository as a submodule while preserving identity and repairing declared bindings
    ticket_ref: PJAN-165
depends_on: []
```

**Seam acceptance criteria**

- Pilot is a real Git submodule with its canonical GitHub origin. Its history,
  tracked changes, untracked and ignored local state survive adoption.
- PJangler resolves project `px` to the adopted checkout with the same PX board;
  affected executable and workforce bindings remain usable without identity changes.
- Local-path and remote-URL import share enrollment behavior, provide a no-write
  preview, converge on rerun, and report recoverable failure rather than false success.
- The reusable command's child delivery is distinct from the one-time adoption;
  neither a filed work request nor the manual move proves the command is available.

**Seam evidence (executable).** Inspect `git ls-files --stage pilot`,
`git config -f .gitmodules --get submodule.pilot.url`, `pj info px --json`,
and `px whoami --json` from the adopted checkout. Compare preserved local-state
inventories and executable-link resolution. Exercise local and fresh-remote import
through the child's delivered CLI, including dry-run, collision and rerun cases.

## I-4 Repository-aware PM skills and a 33GOD BMAD integration companion

**Outcome.** PM desks prefer the skills installed in their own declared repository,
while new and existing 33GOD projects can install BMAD with an ecosystem-aware
companion that connects methodology to existing owner contracts.

**Owner:** `33god` (Grolf), parent ticket `33GOD-81`. Child PMs own their
implementation stories; the parent owns the seam acceptance below.

```yaml
owner_project: 33god
ticket_ref: 33GOD-81
delegations:
- owner_project: flume
  request: preserve repository-aware project skill discovery in PM desk provisioning and backfill registered PM desks through the locked generated-config writer
- owner_project: skillex
  request: author and package the canonical g33 BMAD integration expansion with executable setup, ecosystem mapping, and evidence-to-handoff capabilities
- owner_project: pjangler
  request: consume the companion installer in the owned BMAD installation and update path without copying package logic
related_work: [pjangler:PJAN-166]
depends_on: []
```

**Seam acceptance criteria**

- Every registered PM has its actual repository binding inventoried; verified
bindings enable project discovery and preserve existing trust entries. Missing
repositories or skill roots are disclosed, never silently omitted. The actual
runtime resolver proves project-before-profile selection where skills exist.
- The module maps BMAD planning, decomposition, implementation, and review to
existing ecosystem entrypoints, without introducing a scheduler, employee, or
second board. Krebs authority is conditional on actual project enrollment;
legacy board routing remains usable.
- Setup is portable, previewable, repeatable, and preserves upstream BMAD files
and operator customization. Registration must be visible to the actual BMAD
runtime resolver, not merely a YAML file or help row.
- Manual installation and PJangler's BMAD installation/update consume one package
implementation. Real fixture and live 33GOD checks prove the supported path;
unpublished source and live deployment claims remain distinguishable.
- Evidence-to-handoff separates worker claims from actual diff/test evidence and
distinguishes implemented, tested, installed, deployed, and outstanding work.
Existing Momo review and independent reviewer ownership remain intact.

**Seam evidence.** PM profile/repository inventory and fresh runtime resolver
readbacks; generated-config and lock-concurrency checks; canonical module schema,
help and override resolution tests; fresh install, preview, rerun, operator-edit,
and BMAD-update checks; live 33GOD activation and independent review artifacts.
The BMB YAML/TOML/scaffold reconciliation in `PJAN-166` remains separate: module
integration must not claim that installation wrinkle resolved incidentally.

## I-5 Employees use company identities across mail, access and code/tickets

**Outcome.** A named employee keeps one company identity across posts and agent
harnesses, receives invitations at `@agents.delo.sh`, requests only approved API
access, and leaves code/ticket comments with verified author attribution. Retirement
stops access while preserving the identity behind historical work.

**Owner:** `33god` for integrated acceptance, parent ticket `33GOD-82`.
Flume owns the employment/contact/access-binding epic `FLUME-46`; its seven
implementation stories live in Flume's own planning artifacts and board.
Pilot's owner request is `PX-13`. User directed autonomous research/planning on 2026-10-10.

**Status (2026-10-15, independently verified; one operator step from Done).**
Implemented and live-proven: `FLUME-47` enrollment, `FLUME-48` Access-authenticated
requests, `FLUME-49` company mail, `FLUME-50` scoped GitHub installation tokens (Grolf),
`FLUME-52` native Plane identities (Grolf and Rererere), `FLUME-55`, `FLUME-56`, and
`PX-13` (`px identity verify|comment`) are Done. Read back by the verifier: Grolf's
conversation and inline sandbox comments are authored by `gr0lfbot[bot]` (id
341820121); the two Plane sandbox comments on TEST-14 carry distinct actors
`292ac356` (Grolf) and `ba82e3bd` (Rererere). `FLUME-53` (retirement) is built, twice
independently reviewed and canaried live on Rererere (suspend/restore, disposable
retirement) but stays in E2E; `FLUME-51` (code-review authorship) is built and proven for
Grolf but stays In Progress. **Both are blocked on one operator action:** the
`colrerererebot` GitHub App (5296560) has no installation, because the GitHub
passkey ("Confirm access") prompt for its install on `delorenj/flume-identity-sandbox` is
waiting in the operator's browser. Without it, the "two distinct native GitHub bots"
acceptance criterion is unproven. `FLUME-46` therefore stays open. Not claimed: any board
cutover (Grolf's Hermes PM still resolves Plane as the operator), Plane token expiry
(unobservable through the key), FLUME-39 gateway evidence (gateway link `unverified`).

```yaml
owner_project: 33god
ticket_ref: 33GOD-82
delegations:
  - owner_project: flume
    ticket_ref: FLUME-46
    request: extend existing named employees with stable company identity, Cloudflare-first contact/auth bindings, approved provider access and retirement
  - owner_project: px
    owner_component: pilot
    ticket_ref: PX-13
    request: verify installed Plane native identity and membership, preserve authenticated actor routing, and read back employee-authored sandbox comments
related_work: [flume:FLUME-39, 33god:33GOD-63]
depends_on: []
```

**Seam acceptance criteria**

- One employee retains its stable subject through Hermes and a plain client;
  another employee cannot select its credentials or retrieve its invitations.
- `agents.delo.sh` receiving works through literal Cloudflare routing rules,
  without changing apex mail or buying per-employee mailboxes. Current account
  entitlements, service-token capacity and Worker/storage costs are measured;
  arbitrary outbound email remains optional, not assumed free.
- GitHub and Plane readbacks show the native principals declared in Flume's
  bindings. Shared-bot text attribution is never labeled native-distinct;
  mutable git author/email fields are not authenticated comment authorship.
- Existing Grolf/33god-pm Plane candidates are reconciled before account adoption.
  Pilot owns provider writes, PJangler owns project enrollment and Krebs retains
  managed execution. Model-gateway tokens do not establish a Plane identity.
- Suspension denies new grants/mail access; provider retirement is proven or its
  residual expiry/manual action is explicit. Static upstream keys cannot be made
  short-lived by an internal timer. History remains linked to retired subjects.
- Durable evidence uses existing Bloodbank/Candystore contracts without credentials
  or raw verification mail. Schema additions, if needed, are owned by Bloodbank.

**Seam evidence.** Two canary employees, one sandbox code repository and ticket
board, actual provider-author readbacks, cross-harness identity receipts,
negative identity/mail tests, measured revocation/expiry and cost/capacity checks.
Source tests, sandbox evidence and live deployment remain separate claims.
No workforce rollout or board-mode cutover is part of this planning pass.

**Canonical child plan:**
[Flume company identity](../../flume/_bmad-output/planning-artifacts/employee-company-identity/epics.md),
with requirements, architecture and cited research alongside it. Child stories
are not duplicated here. Planning publication advances the Flume gitlink only;
unrelated component pins and main-checkout work are preserved.

## I-6 Aperture — productize and monetize the 33GOD stack

**Outcome.** The 8-domain stack ships as per-group Docker images + one compose
bring-up, proven on Damien's machine (dogfood), with monetization avenues
evaluated and the first one selected for execution.
**Owner:** `33god` (Grolf). Project home: `33god-platform/aperture/` — all
implementation artifacts live there; children contribute images for their own
components on delegation.
**Phase 1:** wrap the 8 groups (ship board: 38 components) as images, deploy
on Damien's machine group by group, check off live.
**Phase 2:** evaluate monetization avenues (lease agents / license stack /
productize subsystems / ecosystem story) — notes in
`33god-platform/aperture/research/monetization/`.
**Phase 3:** generalization (GOD_* config surface, secrets pattern, docs).

```yaml
owner_project: 33god
project_home: 33god-platform/aperture
dogfood_target: Damien
depends_on: []
```

### I-6.1 Damian Studio peer install (source mirror)

Install a full 33GOD peer on Damian's Mac Studio (tuxedo-morpho.ts.net) from
source, replacing Docker Desktop with headless Colima and migrating Damian's
five existing stacks with data intact. Interim `secrets.env` store (0600,
outside repos) stands in for deferred 1Password; Jev is used only as a remote
LiteLLM pass-through with Damian's `damian-studio` key, all other inference via
the AutomaticAI gateway. Plan and evidence: `33god-platform/aperture/mirror/PLAN.md`
(+ `survey-2026-11-10.json`).

### I-6.2 HeyMa backend on the Mac, one transcribe-cpp engine

**Outcome.** A Mac runs its own HeyMa backend from Homebrew
(`delorenj/tap/vinyl-server`, later `delorenj/tap/wax`), so Damian's dictation
and meetings never leave his network, and Vinyl runs one engine on every host:
transcribe-cpp (Metal on Apple silicon, Vulkan/CPU on big-chungus), taking
upstream Orca's November 2026 speech rebuild. Owner decision 2026-11-15: straight
to transcribe-cpp on both hosts. Replaces PLAN.md W8 "Step 2".
**Owner:** HeyMa (`heyma-pm`). Stories: Vinyl
`components/vinyl/_bmad-output/planning-artifacts/epics.md` (Epics 1-3) and HeyMa
`_bmad-output/planning-artifacts/epics.md` (Epic 2, Wax on macOS).

```yaml
owner_project: heyma
child_backlogs: [vinyl, heyma]
parent: I-6.1
done_when: "Vinyl story 2.5 accepted on Damian's Mac (dictation via 127.0.0.1:7733); Wax Epic 2 accepted later"
```

## I-7 Candybar schedule view in Holocene

**Outcome.** The Candybar cron framework, which now runs the homelab's scheduled
jobs, has a live inbox-style view in Holocene: Definitions and Schedule tabs,
current, past and upcoming rows with countdowns, a noise toggle, and skip
operations, patched live from Candybar's SSE stream.
**Owner:** `33god` (Grolf). Candybar owns the contract and the API (Epic 6 is a
delegation record only, `CAND-6`). Holocene owns the view.

```yaml
owner_project: 33god
delegations:
  - owner_project: holocene
    request: build the Candybar schedule view against candybar's holocene-view-contract.md
    ticket_ref: HOLOC-24
  - owner_project: candybar
    request: keep holocene-view-contract.md and the live API in step (contract-parsing tests)
    ticket_ref: CAND-6
depends_on: []
```

**Seam acceptance criteria**

- The view renders `GET /schedule` from `https://candybar.delo.sh` and patches
  from `GET /schedule/stream` with no polling. A reconnect resumes via
  `Last-Event-ID`, and a `reset` triggers exactly one refetch.
- Skip and noise actions taken in the view round-trip through the API and come
  back as stream events.
- A contract change lands in candybar first (contract file + Epic 5 story ACs in
  the same commit). Holocene never reads the Candybar database or bus directly.

**Seam evidence (executable).** `curl -N https://candybar.delo.sh/schedule/stream`
shows `ready`, then `current.advanced` each minute. Candybar's
`tests/test_schedule_stream.py` parses the contract's trigger list. On the
Holocene side, the evidence is the view open beside `GET /schedule` with the two
agreeing through a minute boundary.

## I-8 Pane-bound crank

**Outcome.** A crank is bound to one live agent pane (Claude, OpenCode, Kimi,
Codex…) and its agent session, not to a project or a tab name. The crank TUI
lists the panes being driven. Each crank has a durable record (tab, pane, agent
CLI, session id, workspace path, crank count, Candystore history link) and its
own workspace of deterministic scripts. Each beat costs a short brief instead of
a ~600k-token sweep. The Hermes economics cap on crank-beat (`777c511a009c`) is
removed only after this lands. Until then the cap stays, and Candybar remains the
only clock.
**Owner:** `33god` (Grolf). ASM owns agent discovery, identity, session and state;
the terminal driver owns topology and terminal actions. `delorenj/crank` owns the
crank registry and engine; pjangler remains the `pj crank` CLI/TUI control surface.
These boundaries were approved on 2026-11-07; implementation has not migrated yet.
PJAN-202 is the provisional read-only provider until the owner APIs land.

```yaml
owner_project: 33god
delegations:
  - owner_project: pjangler
    request: exact read-only inventory of live agent panes (pane -> pid -> agent CLI -> session id/status)
    ticket_ref: PJAN-202
  - owner_project: crank
    request: crank-owned bindings to agent sessions and a lean engine; migrate existing tab keys
    ticket_ref: pending
  - owner_project: pjangler
    request: pj crank wraps the crank-owned registry and ASM inventory; TUI lists the driven agents and current panes
    ticket_ref: pending
  - owner_project: candybar
    request: record a Hermes economics refusal as a failure, not success
    ticket_ref: pending
depends_on: []
```

**Seam acceptance criteria**

- `pj crank panes --json`, the engine and Deckard agree with the ASM inventory
  joined to terminal topology. Provisional providers remain until owner APIs land;
  an independent process/session check validates the ASM, not just its consumers.
- A tab rename, or a pane moved between tabs, never changes which pane a crank
  drives. After a zellij restart, the agent session id re-finds the pane.
- A pane with no agent process cannot hold an enabled crank.
- The cap is lifted only after the slices above are Done, as one recorded change
  to the job economics.

**Seam evidence (executable).** `pj crank panes --json` beside `deckard status`
on the live `Workspace` session; Claude rows cross-checked against
`~/.claude/sessions/<pid>.json`.

**Approved amendment (2026-11-07).** Bind crank to agent identity/session, with the
pane treated as its current location. Session rotation/resume and process reuse
must be resolved explicitly in the architecture before writes migrate; never
silently retarget a binding by cwd or pane alone. The registry belongs to crank,
not pjangler. ASM and terminal ownership are split; Deckard requires ASM, with no
second fallback state fold. I-9 carries shared foundation outcomes; I-8 depends
only on its required contracts, not on completion of every I-9 consumer migration.

**Operator redefinition (2026-11-18, crank v2, PJAN-214 / BB-42).** A crank is bound to
ONE live interactive agent session (cli + native session id + pid and its /proc start
time) in one pane of the canonical zellij session; the pane is location only. Each crank
is its own Candybar (`<project>/.candybars/crank-<cli>-<sid8>-<pid>.candybar.toml`,
git-ignored machine-wide), created by the hook-hub `crank-attach` row on SessionStart and
removed (archived, manifest deleted) on SessionEnd, pane close, policy off or a dead
process; every removal emits `bloodbank.crank.binding.ended` with its reason, and
`orphan_reaped` is the non-explicit termination. Policy is the `.project.json` `crank`
block (enabled, interval, prompt, target, rules) over `~/.config/33god/crank.toml`.
Decisions recorded with it:
- **AD-3 amended:** the project block is the standing opt-in for every interactive
  session that starts in the project; there is no per-session opt-in step.
- **Dropped criterion:** "after a zellij restart the session id re-finds the pane". A
  closed pane or session deletes its crank; a new session gets a new one.
- **Provisional homes (F1):** `delorenj/crank` does not exist yet, so the registry lives
  in pjangler `src/crank/{policy,binding,sessions}.ts` and the engine in jev-clairic
  `bin/crank-pane`. Candybar is the registry (rows tagged `crank-session`); Redis
  (`crank.lua` on statekit) is only the live projection, never the source of truth.
- **Tab model retired from `pj crank`:** enabling v2 turns the project's legacy
  `zcrank:tab:*` switch off; the 33god-pm crank-beat sweep retires once v2 is proven.
- **Known accumulation:** Candybar has no hard delete (CAND-54), so ended cranks stay
  archived rows.

## I-9 33GOD features: formal repos, one owner per atom

**Outcome.** Cross-repo capabilities that become hard to maintain or extend can
be promoted to features with a dedicated formal hub repo, listed in root
`features.toml`. Single-repo functionality remains a component; it does not need
a feature repo. The hub binds all participant parts through contracts, links and
seam acceptance; it does not absorb their implementation backlogs. Every shared
building block ("atom") has exactly one owning repo. Agents follow the
`33god-features` global skill. Crank is the first promoted feature; the initial
survey's other entries are candidates, not eleven approved repo extractions.

**Decided by the operator (2026-11-06).**
- F1 (clarified 2026-11-07): a feature is a cross-repo capability promoted because
  its parts are hard to maintain/extend. Its dedicated formal repo is the tracked
  hub; single-repo work is a component. Crank goes first and owns its registry;
  pjangler's CLI/TUI integration is a participating part of the feature.
- F2: `features.toml` here is the full catalog and the planning map. An install
  disables features in its own untracked `~/.config/33god/features.toml`.
- F3: no pins. A pin is a temporary bandage with a reason and an exit ticket;
  features merge to main. CAND-49's pinned Hermes image is gone (CAND-52, Done).

**Approved direction (2026-11-07)** (study:
`33god-features/asm-ownership-study.md`): split the primitives. ASM owns agent facts;
a separate terminal driver owns topology, focus, rename and pane input. The
operator delegated repo choice; the architect selected **new
`delorenj/terminal-driver`**, not repurposing `zellij-driver`. Perth is implemented
code with intent/snapshot storage, an installed `zdrive` CLI and an Agentboard
bridge contract; its dormant service is not evidence of safe replacement. Leave
it unchanged and do not reuse `zdrive`. Extract neutral terminal code from
Deckard without a reverse dependency on deckard-core; keep agent detection in ASM.
Start with Zellij only. Deckard requires ASM: retire its
second state fold rather than preserve a no-Redis fallback. pjangler, Holocene,
Wingman and Flume consume. These are target boundaries, not deployment claims.
The initial feature design remains research input, not a finalized BMAD architecture.

**BMAD next:** a scoped platform PRD for I-9, then shared architecture and a
contract/migration review. Reuse the survey and recorded decisions; do not restart
discovery or replace unrelated platform documents. Child PMs own implementation
epics/stories, with detail generated just in time for each migration wave. Explain
the method as it is used: learning BMAD is an explicit secondary goal.

**Owner:** `33god`. Each slice is delegated to its owning repo's board.

```yaml
owner_project: 33god
delegations:
  - owner_project: candybar
    request: drop the CAND-49 pinned Hermes image; crank-beat back on the native hermes runner
    ticket_ref: CAND-52 (Done, 79ad305)
  - owner_project: bloodbank
    request: ASM tests never touch production Redis (throwaway redis, prefix, CI)
    ticket_ref: BB-32
  - owner_project: bloodbank
    request: fix ASM identity (BB_HOOK_PARENT_PID, session_id, one row per agent, ghost purge)
    ticket_ref: BB-33
  - owner_project: asm (new repo, split approved; extraction pending)
    request: extract the ASM with history; asmctl --json verbs; PJAN-202 detection rules
    ticket_ref: pending
  - owner_project: terminal-driver (new component repo; creation pending)
    request: terminal-only library/API extracted from deckard-mux with neutral types; no agent logic or deckard-core dependency
    ticket_ref: pending
  - owner_project: crank (new repo)
    request: create delorenj/crank as the first formal feature repo; feature.toml; adopt live candybar rows
    ticket_ref: pending
  - owner_project: pjangler
    request: pj feature check (read-only) against features.toml and feature.toml
    ticket_ref: pending
depends_on: []
related_initiatives: [I-8]
```

**Seam acceptance criteria**

- Every promoted `[feature.*]` in `features.toml` has a dedicated formal hub;
  `[candidate.*]` entries are not automatically promoted. The hub links participant
  contributions without taking ownership of their component internals.
- Every `[atoms]` row is `owned`; `pj feature why <atom>` lists no duplicate copy
  that is not declared provisional or `[[implements]]`.
- No pin without a reason and an open ticket; no hardcoded job id, candybar id,
  session name or home path in any feature (lint).
- `asmctl doctor --json` reports no duplicate rows, no ghost rows and no empty
  session ids on the live box.


## I-10 The Manual — LEGO-style picture manuals for 33GOD

**Outcome.** Anyone who does not have Jarad's attention span can understand
33GOD from a manual built like a LEGO instruction booklet. Each page is one
page or less. Pictures and arrows do the work, and the reader comes away with an
accurate mental model of the platform, not a simplified false one. The manual is
built from a small, fixed visual grammar that maps LEGO manual atoms onto
software concepts. One example: the 1:1 scale bar becomes a nesting-level meter.
The 33GOD platform is the long bar, HeyMa a shorter bar inside it, wax and vinyl
shorter bars inside HeyMa, and so on down. Every page is drawn from that grammar.

**Dogfood:** Damian, the first reader, who freezes at a wall of text. A page is
done when Damian can tell it back correctly after one read. Feedback arrives as
comments on the published page.

**Owner:** `33god`. Project home: `33god-platform/manual/` (grammar spec,
storyboards, page sources, feedback log). Vision: `THE_MANUAL.md`. Brief:
`briefs/brief-the-manual-2026-11-11/`. Each child may later be asked for one
"what my component is" page, drawn in the shared grammar. Those requests are
delegations, not work done here.

```yaml
owner_project: 33god
project_home: 33god-platform/manual
vision: THE_MANUAL.md
dogfood_target: Damian
delegations: []
depends_on: []
related_initiatives: [I-6.1]
```

**Seam acceptance criteria**

- One visual grammar (v0 and later) is versioned in the project home. Every page
  uses only the atoms the grammar defines, and a new atom needs a grammar change
  first.
- Every page fits on one screen or printed page. Words are labels, not
  paragraphs, and the word budget is set by the grammar.
- Every claim a page draws about the system can be traced to live code or config
  (the page's source lists its evidence). A page is never shipped for being
  pretty when it is wrong.
- Damian's tell-back of each published page is recorded in the feedback log, and
  each change to the grammar cites the feedback that drove it.

### I-10.1 Waybill — the prompt's own tour of the Factory

**Outcome.** Jarad types one prompt in Claude Code, Codex CLI or Codex Desktop
and can follow it through every component in causal order, with every side effect
recorded. It works like DevTools tracking one network request. The recording is
a `33god.waybill` v1 JSON dump, and the Factory (`manual/sandbox`) plays it back
as a guided, data-true tour. This replaces the scripted tour, which did not work
as a teaching device; `?tour` stays as it is. Damian gets the visual version, and
Jarad gets the proof that the system works together, including what broke or
never happened.

**Owner:** `33god` (it spans hook-hub, Bloodbank, Candystore, Holocene, Hindsight,
ASM and the gateway, so it lives here under the Director Rule). The recorder
lives in `33god-platform/waybill/` (`SPEC.md`, `waybill capture|record|show|publish|list`).
The player lives in `manual/sandbox/src/waybill/`. Deep link:
`https://manual.delo.sh/sandbox/?waybill=<url>`.

```yaml
owner_project: 33god
project_home: 33god-platform/waybill
spec: 33god-platform/waybill/SPEC.md
dogfood_target: [Jarad, Damian]
delegations: [BB-37, BB-38, BB-39, BB-40, BB-41, BB-33, CANDYS-73, 33GOD-95]
depends_on: [I-10]
related_initiatives: [I-12]
```

**Seam acceptance criteria**

- Every span, event and consumer in a waybill comes from a named source with
  evidence. Inferred consumers are marked as inferred, and anything that cannot
  be observed is recorded as a Gap, never invented.
- The recorder only reads from live systems. It creates no JetStream consumers
  and does no publishing.
- The `public` profile scrubs credentials and truncates memory, context and tool
  text before anything leaves the box.
- The Factory renders a waybill as a pure function of the playhead, unmapped
  components get auto-placed kiosks, and the end card lists findings and gaps.

**Delegations surfaced by the first recordings (ticketed 2026-11-17)**

- BB-37 (high): hook-hub's PATH lacks mise shims and `~/.local/bin`, so
  codegraph-prompt and code-review-graph-* never run. The claude-notify symlink
  also dangles.
- BB-38 (high): hook-hub receipt journal SQLite contention. It caused 7.6k
  OperationalErrors, 1,617 invocations stuck in `received`, and mis-stamped
  handler starts.
- BB-39: agent-hooks `publish_status=sent` is only a core-NATS PONG. Publish
  with a PubAck instead. No loss was observed, because Holocene does store the
  events.
- BB-40: traceparent is all zeros on every event.
- BB-41: two n8n JetStream consumers are unbound with backlogs (1,732 and 1,420
  messages).
- BB-33 (existing, commented): ASM never reaches `gone`, and its hash has no
  session_id.
- CANDYS-73: candystore-context exits 1 outside a registered project instead of
  skipping.
- 33GOD-95 (high): the enricher's `report.session.completed` is dead-lettered
  on every session, and the event_embeddings foreign key races Candystore's
  insert.
- Not yet ticketed: a per-handler stdout tee in hook-hub, so waybills can show
  what each handler injected.

### I-10.2 Query waybills and event completeness

**Outcome.** Any Candystore query, not only one prompt, becomes a replayable
`33god.waybill` that the Factory plays. "Everything the company did last night"
is one command and one file. On top of that, two things hold, and a command
anyone can re-run proves them:

- Every archived event is pictured accurately in the simulation. Missing
  components get modelled.
- Everything that actually happens shows up as an event.

This replaces a nightly pipeline. Jarad asked for it on 2026-11-21. Neighbouring
level (`belsky-doctrine`): any query becomes a waybill, and the gap audit becomes
a command.

**Owner:** `33god`. The parent-side code is in `33god-platform/` (not a
submodule):

- `waybill/` holds the query builder and the audit.
- `scripts/atlas.py` and `components/` hold the resolver.
- `manual/sandbox/` holds the Factory query mode.

Everything inside a child (Candystore export, Bloodbank emitters, timers, unit
failures) is delegated below as tickets on the child's own board. Evidence for
every ticket comes from the read-only research run of 2026-11-21: the coverage
census, the emission gap audit and the critic pass.

```yaml
owner_project: 33god
project_home: 33god-platform/waybill
spec: 33god-platform/waybill/SPEC.md   # §2, additive: recorder.mode query, origin.query, batch/chapter spans
dogfood_target: [Jarad, Damian]
delegations: [CANDYS-55, CANDYS-78, CANDYS-79, CANDYS-80, BB-46, BB-47, BB-48, BB-49, BB-50, BB-51, BB-52, BB-53, CAND-55, MONI-3, INFR-155, INFR-156, SKRILL-53, DOCS-2]
depends_on: [I-10.1]
related_initiatives: [I-10, I-8]
```

**Decisions (Jarad, 2026-11-21)**

- **(a)** `waybill night` and the `33god.night` file stay for now, because the
  overnight marketing page still reads them. `waybill query --last-night` is the
  convenience path.
  Superseded 2026-11-21: the page became a component tour and `waybill night` and
  `night.py` were retired. `waybill night` now prints a pointer to
  `waybill query --last-night` and exits 2.
- **(b)** `33god.waybill` stays v1. Changes are additive only: the
  `recorder.mode: query` enum value, the `origin.query` object, and `chapter`
  and `batch` span kinds. Older players map an unknown mode to capture.
- **(c)** Product projects (tiller, `gib-*`, `local-script:*`) become one
  "tenant annex" station keyed by project slug, added as a factory extra. Their
  `atlas_ignore` stays for the registry graph.
- **(d)** Archiving commands is a Bloodbank design ticket (BB-48). It must never
  be a mirror or consumer on the `BLOODBANK_COMMANDS` workqueue.

**Parent-side work (built here)**

1. **Registry resolver.** `atlas.py render` emits one producer and source map
   into `src/cast.generated.json`. `waybill/registry.py` (moved out of
   `night.py`) and the player both read it, so the two cannot drift. The work
   also covers:
   - a `source:` surface kind, so relayed events land on their real owner;
   - the registry fixes: `n8n-plane-webhook` moves to plane-hook; producers for
     enricher, kimi and gemini; a `copilot-cli` alias; an `ext:antigravity` bay;
     zellij-sentinel taken off the ignore list;
   - the tenant annex extra;
   - the `isMirror` fix: `system.hook.updated` no longer counts as a hook
     receipt.
2. **`waybill query`** (`collectors/candystore_query.py`). It reads a query
   (`--since/--until`, `--last`, `--last-night` or `--from-url`, plus filters).
   - It synthesizes `publish:<id>`, `tool:<tool_use_id>`, `llm:<request_id>`
     (joined by `data.request_id`, never by `correlationid`) and `hook:<inv>`
     spans.
   - It keeps rare events and failures, up to 400.
   - It folds everything else into at most 12 chapters of `batch` spans, with
     counts, per-minute sparklines and exemplars.
   - It writes gzipped compact JSON: under 2 MB gz for a 14-hour night.
   - It runs a conservation check: kept events plus batch counts equals the
     Candystore total plus dead letters handled.
3. **Factory query mode** (`manual/sandbox`):
   - the "You asked the archive…" prompt, chapter pacing, batch pallets and a
     bucketed waterfall;
   - fixes for the `director.ts` hot spots, with `direct()` under 400 ms on a
     folded 100k-event fixture;
   - one crew-hall desk per Hermes profile, and the tenant annex;
   - kiosks for each new emitter as its delegation lands.
4. **`waybill audit --days N`.** It compares stream sequence ranges with
   Candystore ids using direct-get or `subjects_filter`, never a JetStream
   consumer (I-10.1 rule), and has one adapter per ground-truth source. Its
   `gaps[]` and `findings[]` feed the Factory end card. It runs on demand; if
   it ever needs to recur, it gets a Candybar manifest.

**Delegations (filed 2026-11-21, idempotent markers `I-10.2:<slug>`)**

The lane column is the lane at filing. Live status comes from the boards
(`px show <ref>`) and is never typed here.

| Child | Ticket | Ask | Lane at filing |
|---|---|---|---|
| candystore | CANDYS-55 (existing, commented) | `idx_events_received_at`. Its migration is now `011` (006 is taken). It blocks CANDYS-78 | Backlog |
| candystore | CANDYS-78 | `GET /export`: NDJSON with a keyset cursor (`received_at`, `id`), `include=dead_letter`, a 24 h default and 7 d cap, counts from `/summary/timeline`. Relates to CANDYS-60, 74 and 75 | Backlog |
| candystore | CANDYS-79 | Emit `system.event.dead_lettered` on every drop (9,033 silent drops) | Backlog |
| candystore | CANDYS-80 | Decide and wire `gib.evt.>` ingestion for the tenant annex (GIB_EVENTS: 394 messages, 0 consumers) | Backlog |
| bloodbank | BB-46 | Hermes `repo.decision.recorded`: fill service, domain and kind (2.7% dead-lettered) | Backlog |
| bloodbank | BB-47 | Dual-publish Deckard attention as `bloodbank.evt.agent.attention.raised` (0 of about 105 a day archived) | Backlog |
| bloodbank | BB-48 | Command archive design, per decision (d): about 17k commands a day, 0 archived | Backlog |
| bloodbank | BB-49 | A consumer for `cmd.audio.task.start`, or stop publishing it (72 stranded) | Backlog |
| bloodbank | BB-50 | Hermes: `session.started` for subagent, oneshot and cron; `messaging.telegram.*`; the +22% `tool.requested` over-count | Backlog |
| bloodbank | BB-51 | ASM transition events, with the sweep publishing only its changes. Relates to BB-33 | Backlog |
| bloodbank | BB-52 | hook-hub `missing_pane_context` skip (14 Hermes approval requests dropped) | Backlog |
| bloodbank | BB-53 | Schemas: wax `audio.*`, `memory.*`, `repo.commit`/`push`, `crank.nudge.*`, `system.service.*`, `system.event.dead_lettered`, `project.artifact.published`, `agent.attention.raised` | Backlog |
| candybar | CAND-55 | Five native timers: asm-sweep, infra-doctor, the deadman, hermes-gateway-watchdog and op-token-guard. Migrate each, or keep it native under an exception Jarad approves that names its event. All five already have blanket "canonical exclusion" entries in `deploy/scheduling-policy.json` | Backlog |
| monitoring | MONI-3 | A shared `OnFailure=` publisher, `system.service.failed`, rate-limited for crash loops (33,637 failures in 3 days) | Backlog |
| infra | INFR-155 | infra-doctor, the deadman and the gateway watchdog publish state changes and ntfy alerts as events | Backlog |
| infra | INFR-156 | `hermes-gateway-restart` publishes `restart_requested` and `restarted` | Backlog |
| skillex | SKRILL-53 | artifacts `publish.py` emits `project.artifact.published` after a verified receipt (75 silent publishes) | Backlog |
| delodocs | DOCS-2 | curator-serve (NRestarts 144,934) and delodocs-inbox-watchdog (25,099) point at the removed `DeLoDocs/_vault`. Copies of the scripts are in `~/code/obsops/scripts`. 2026-11-21: Jarad killed curator-serve, curator-drain and the inbox watchdog: units disabled and deleted, launchers removed, the idle `curator-drain` JetStream consumer deleted. Nothing consumes `curator.file.received` now | Done (killed) |
| infra | INFR-157 | Hindsight `memory.*` events through Hindsight's webhook (7,419 silent operations in 3 days). The server is `~/docker/stacks/ai/hindsight` (DeLoContainers; the DELO board was archived 2026-10-18) and the hooks are `~/.agents/hooks/hindsight` (delorenj/agents, no `.project.json`), so it is homed on the infra board | Backlog |
| infra | INFR-158 | jev-litellm: a success callback that publishes `llm.usage.recorded` (12,525 calls bypassing the gateway in 3 days). Lives in `~/docker/stacks/ai/jev-litellm/compose.yml` (DELO board archived), homed on the infra board | Backlog |
| infra | INFR-159 | Global git hooks: `post-commit`/`pre-push` publish `repo.commit.recorded`/`repo.push.completed` (2,297 commits and 1,059 pushes in 3 days). Lives in `~/.agents/git/hooks`, the target of `~/.config/git/hooks` (delorenj/agents, no board), homed on the infra board | Backlog |
| infra | INFR-160 | zcrank-send: `crank.nudge.sent`/`refused` (259 sent and 38 refused in 3 days). Lives in `~/.agents/tools/jev-clairic/bin/zcrank-send` (delorenj/agents). The crank repo is still pending under I-8, so it is homed on the infra board | Backlog |
| bloodbank | BB-54 | Krebs tick, dispatch, repair and orphan-release decisions emit no events (krebs has no board) | Backlog |
| bloodbank | BB-55 | plane-hook (`delonet-n8n-workflows`): publish `repo.task.transitioned` and `deleted`; only created is published | Backlog |
| bloodbank | BB-56 | 2 of 61 headless `claude -p` children of Hermes PMs fire no hooks (hermes-fleet) | Backlog |
| bloodbank | BB-57 | opencode: prove `session.started` for every session in `opencode.db` (nearly silent 2026-11-13 to 11-19) | Backlog |
| bloodbank | BB-58 | JetStream consumers `enricher-events` (83 pending) and `smoke-check` (orphaned, 45 pending) are not draining | Backlog |
| bloodbank | BB-59 | Cast components that declare a producer and published nothing, or that nothing measures: emit, measure or exempt each | Backlog |
| voxxy | VOXXY-3 | vox has emitted zero events, ever: `audio.speech.synthesized` and `failed` | Backlog |
| monitoring | MONI-4 | OOM kills (kernel and systemd-oomd) emit no event: `system.service.oom_killed` | Backlog |
| skillex | SKRILL-54 | artifacts `publish.py` serves `.json.gz` as `application/json`; use `application/gzip` | Backlog |

Comments were also posted on CAND-55, BB-50, DOCS-2 and MONI-3 with the
findings of the second audit pass (marker `I-10.2`). Every audit row with no
live event now names one of the tickets above.

**Seam acceptance criteria**

- `waybill query --last-night` writes a v1 waybill that plays in the Factory in
  60 stops or fewer and under 2 MB gz, with `stats.conservation_ok: true`.
  Players older than this change still load it.
- Every producer resolves, through the one map in `cast.generated.json`, to one
  of: a registry component, an extra, the tenant annex, or `unknown` named in a
  finding. Nothing is dropped, and Python and the player never disagree
  (selfcheck).
- `waybill audit --days 3` has no row marked "silent", and no row marked
  "lost-in-transit" without an open delegation above. The recorder creates no
  JetStream consumers and does no publishing.
- Before closing, each delegation shows that its PM picked it up: triaged and
  moved off Backlog on its own board.

## I-11 Agent ownership and impact awareness

**Outcome.** A new request produces an accountable-owner brief separately from
interested projects; a meaningful contract change reaches its actual affected
owners as a concise handoff or FYI, with delivery/handling evidence and no chatter
loop. Voxxy-to-Phonograph is the first product-backed seam, not a fleet rollout.

**Owner:** `33god` (Grolf) for integrated acceptance. The
[seam spec](../specs/spec-agent-impact-awareness/SPEC.md) and its companions hold
the policy, current evidence and acceptance cases. Child PMs own all implementation
epics/stories. This request authorizes planning and intake, not deployment,
workforce provisioning or native input. No new feature repo is presumed.

```yaml
owner_project: 33god
ticket_ref: 33GOD-89
delegations:
  - owner_project: bb
    owner_component: bloodbank
    target_agent_id: bloodbank-pm
    request: refine canonical request/change checkpoints, consumed native context and targeted notification/receipt contracts
    ticket_ref: BB-36
  - owner_project: transcription-queue
    owner_component: heyma
    target_agent_id: heyma-pm
    request: refine a reusable independent-project classifier seam without copying Wax logic or adding notification effects to enrichment
    ticket_ref: HEYMA-13
  - owner_project: pjangler
    target_agent_id: pjangler-pm
    request: refine canonical aliases and evidence-backed contract dependency metadata for owner/relevance consumers
    ticket_ref: PJAN-205
  - owner_project: flume
    target_agent_id: flume-pm
    request: refine workforce responsibility/recipient declarations, reconcile FLUME-6/7, and identify the actual Phonograph receiver or enrollment gap
    ticket_ref: FLUME-84
  - owner_project: voxxy
    target_agent_id: voxxy-pm
    request: confirm the voice-catalog/synthesis consumer seam and bounded no-deploy awareness pilot
    ticket_ref: VOXXY-2
related_initiatives: [I-1, I-4, I-9]
depends_on: []
```

### I-11.1 Request ownership and relevance seam

**Seam acceptance:** one true new external request yields separately evidenced
owner and independent relevance judgments; declared scope outranks probabilities;
ambiguous ownership abstains; actual native context is consumed before skill
selection on each claimed harness. Repeated pre-LLM/tool calls do not re-admit the
request. Unknown classifier/registry results remain unknown, never empty success.

### I-11.2 Meaningful-change and targeted notice seam

**Seam acceptance:** evidence of a changed consumer-used contract includes that
consumer regardless of low semantic score; internal/no-op edits do not wake it.
Batch boundaries and a cheap scope-change check replace per-tool inference.
Outbox/inbox dedupe, exact target revalidation, stored/accepted/handled receipts,
expiry and causal hop limits prevent duplicate work and acknowledgement loops.
FYI does not authorize implementation or transfer ticket ownership.

### I-11.3 Voxxy-to-Phonograph pilot

**Seam acceptance:** canonical `voxxy` and `phonograph` identities resolve despite
Vox/Dubplate aliases, and owner-confirmed `/voices` and `/synthesize` dependencies
yield one actionable notice to a real eligible receiver. Phonograph currently
has no declared PM; that is an activation gap, not permission to invent or hire
one. Planned, committed and deployed claims require distinct evidence. Replays,
negative edits and receipt messages neither duplicate work nor cause fanout.

**Seam evidence.** The spec's acceptance matrix requires labelled shadow cases,
actual Jev results/cost/latency, native context-consumption proof and independently
observed destination handling. These are future gates, not evidence produced by
this planning pass. Child intake readback, PM acceptance, implementation and live
activation remain separate claims. No parent sprint board or child code loop.

**Decision basis.** Canonical `momo/PILLARS.md` #1 limits the first slice to a
revenue-facing consumer; #2 reuses Wax/Jev and hook/bus infrastructure; #3 keeps
one owner per identity/classifier atom; #4 uses Adapter/Strategy/Observer seams.
No event type is registered by this initiative.

## I-12 The Atlas — one map of every component, one showcase page each

**Outcome.** There is exactly one map of 33GOD, and everything else is drawn
from it. Every component (50+ across source, runtime, contracts and products)
has one evidence-backed record in the component registry
(`33god-platform/components/*.yaml`); the C4 views (system context, containers,
components) and the Atlas page are generated from those records, and a gate
fails when they drift. The same records are the source for the marketing layer:
one stylized, one-screen teaser page per component that people *want* to flip
through (eye candy first, a story that builds page to page), an index, and later
campaigns. The pages tease what each part does and how the parts fit; they never
publish source, internal paths, hostnames or secrets, because the combination is
the moat (`visibility: private-source`).

**Why now.** Genesis (genesis.delo.sh) leases 33GOD agents to clients; trust is
the unknown. The showcase is how a prospect gets curious before they use a desk.

**Owner:** `33god`. Project home: `33god-platform/atlas/` (generated views,
page sources, design system). Registry: `33god-platform/components/`.

**Phases**

1. **Inventory + C4** — sweep source, runtime, event contracts and every existing
   list (components.yaml 14, ship board 38, features.toml, `pj list`, agents
   registry), merge into the registry, render C4 + Atlas, add the drift gate.
2. **Design system** — a real 33GOD showcase design system (art direction, type,
   motion, illustration grammar), superseding the minimal Holocene tokens and the
   Field Guide for marketing surfaces. Coordinates with I-10's visual grammar
   rather than replacing it.
3. **Component pages** — one page per component, one screen, generated from the
   registry record plus an authored story beat; ordered so the sequence tells the
   story of the platform.
4. **Index + campaign** — the landing index and the first outreach campaign,
   tied to Genesis desks as the call to action.

**Roles (delegation, not built here):** an art director and graphic designers
(design system, pages) and a director of marketing (content, campaigns) are
Flume hires; requesting them is a delegation to `flume-pm`.

```yaml
owner_project: 33god
project_home: 33god-platform/atlas
registry: 33god-platform/components
delegations: [FLUME-85, FLUME-86, FLUME-87]  # art director, graphic designers (blocked by 85), director of marketing; filed 2026-11-14
depends_on: []
related_initiatives: [I-6, I-10]
```

**Seam acceptance criteria**

- One registry. No second component list is created; the ship board, the
  Manual and any page read the registry or are marked as historical snapshots.
- Every record carries evidence (file, unit or command); every relation names a
  mechanism (subject, route, CLI, MCP, table) and targets a known id. The gate
  (`mise run platform:atlas:check`) fails otherwise, and fails when the rendered
  views are older than the registry.
- A component page fits one screen, is generated from its record, and makes no
  claim the record does not back.
- Public pages carry no source, internal paths, hostnames, credentials or
  personal names.
- **Scrub rule (2026-11-14):** a public page reads only `atlas/public.json`,
  never `atlas.json` or a component record. The export keeps name, kind, domain,
  status, summary, tech and `public_card`, and draws each wire as from, to and
  kind only: no mechanism (`via`), evidence, runtime or role notes. The scrub lint
  in `atlas.py check` fails on any hostname, IP, port, home path, file name,
  secret reference, event subject, machine name or owner handle left in the
  export. Fix a hit by rewording the registry, never by editing the export.
  The art director's sign-off includes checking each page against this rule,
  personal names included, which the lint cannot catch.
- **Drift control (2026-11-17):** the registry stays true to the running system
  in three tiers. (1) *Commit:* the versioned `.githooks/pre-commit` dispatcher
  (installed by mise on enter) re-renders the Atlas into any commit that touches
  the registry and runs `check`, so views can never lag. (2) *Audit:*
  `atlas.py audit --live` (`mise run platform:atlas:audit`) checks every
  relation's cited line still holds its recorded `anchor`, finds running
  systemd units, containers, Candystore producers and repos that no record's
  `surfaces:` claims (non-33GOD workloads go in `components.yaml`
  `atlas_ignore` with a reason), and flags `status` that disagrees with what is
  running. (3) *Schedule:* the `atlas-drift` candybar (daily 07:17) runs
  `scripts/atlas-drift.sh`: it heals moved evidence lines and stale renders and
  pushes them, and files one Plane ticket per distinct finding set (keyed by
  the finding digest) with a report on MinIO for the rest. A new component is
  done when it has a record whose `surfaces:` claim it; a new relation is done
  when it has `path:line` evidence and an anchor (`atlas.py anchor`).
  Baseline: 33GOD-94 (14 unregistered surfaces).

## I-13 Self-evolving skills and the skill tree

**Outcome.** Every skill is a node in one balanced tree with a single root: each node has one parent (one
route), siblings do not overlap, and a node that grows past its budget splits into lazily loaded children (a
node that shrinks merges back). Skills declared **self-evolving** get better with use: every task routed
through one folds its lessons back into it, written for the next run's speed, inside the budget. Agents load
one root skill and traverse to what they need, instead of reading ~134 descriptions in every session.

**Why now.** Jarad declared the Self-Evolving Skill archetype on 2026-11-19 while building the Factory forge,
whose nightly agent repeats the same task and should learn from each night. The global listing costs ~55k
characters of descriptions per session, and overlapping skills already route agents wrong.

**Owner:** `skillex` (SKRILL, `skillex-pm`): the archetype doc, `skillex tree` (show, route, add, balance,
split, merge), lint and activation. **Dogfood (33GOD, live):** `the-factory` hub under `33god-hub` and its
self-evolving child `factory-maintenance`, fed nightly by the factory-forge (`c73260a`). Brief:
[skill-tree-brief.md](skill-tree-brief.md).

```yaml
owner_project: skillex
project_home: skillex (docs/skills, src/core/skill-graph.ts)
dogfood: 33god-platform/skills/33god-hub/subskills/the-factory
delegations: [SKRILL-49]   # skillex-pm, filed 2026-11-19
depends_on: []
related_initiatives: [I-10, I-12]
```

**Seam acceptance criteria**

- `skillex tree add the-factory --dry-run` places it under `33god-hub`, and `factory-maintenance` under
  `the-factory`, with no overlap warning; adding a deliberately overlapping skill warns and names the sibling.
- A self-evolving node's lessons land through the owner's gate and keep `skillex skill lint` clean at any depth
  (budget, parent route, links, no nested `SKILL.md`); the forge's `factory_forge.py skill` is the first
  instance, and Skillex's lint replaces it once it covers the same rules.
- `skillex tree balance --dry-run` over the global skills reports every hub out of fan-out bounds, every
  oversize node and every overlapping sibling pair, and proposes the move for each.
- Routing accuracy is measured, not asserted: a fixed set of real task prompts traced through the tree
  (`skillex tree route`) lands on the right leaf, and the set runs in Skillex's tests.
- Single-root activation is a selection change (depth-1 listing first, then root only), reversible, and never
  removes a skill from disk.
