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
**Owner:** `33god` (Grolf). pjangler owns `pj crank` (discovery, registry, TUI).
The zcrank engine (`~/.agents/tools/jev-clairic`, delorenj/agents) has no board
yet. Deckard's `deckard-mux/src/proc.rs` is the reference contract for pane
attribution; it is not a runtime dependency.

```yaml
owner_project: 33god
delegations:
  - owner_project: pjangler
    request: exact read-only inventory of live agent panes (pane -> pid -> agent CLI -> session id/status)
    ticket_ref: PJAN-202
  - owner_project: pjangler
    request: crank registry keyed by pane + agent session, and a TUI that lists panes; migrate existing tab keys
    ticket_ref: pending
  - owner_project: agents
    owner_component: jev-clairic
    request: zcrank engine consumes the pane inventory and registry; lean beat; suggestion accept via TAB
    ticket_ref: pending
  - owner_project: candybar
    request: record a Hermes economics refusal as a failure, not success
    ticket_ref: pending
depends_on: []
```

**Seam acceptance criteria**

- `pj crank panes --json` and the engine name the same agent panes, and their
  per-tab counts equal `deckard status` `agents=` on the live session.
- A tab rename, or a pane moved between tabs, never changes which pane a crank
  drives. After a zellij restart, the agent session id re-finds the pane.
- A pane with no agent process cannot hold an enabled crank.
- The cap is lifted only after the slices above are Done, as one recorded change
  to the job economics.

**Seam evidence (executable).** `pj crank panes --json` beside `deckard status`
on the live `Workspace` session; Claude rows cross-checked against
`~/.claude/sessions/<pid>.json`.

**Pending amendment (I-9, proposed 2026-11-06, awaiting operator approval).** The
ASM ownership study (`33god-features/asm-ownership-study.md`) recommends: bind a
crank to the agent's session (cli + session id) and look the pane up live on each
beat, because the ASM's design rejects a pane as agent identity; discovery moves
from pjangler to the ASM (PJAN-202's rules become the reference, not Deckard's
`proc.rs`, which caches by pid alone); the crank registry lives in `delorenj/crank`;
pane input goes through `zellij-driver`; and the oracle becomes
`asmctl agents --json --topology` instead of `deckard status`. Until approved, the
text above stands. The cap still stays until I-8 lands.

## I-9 33GOD features: formal repos, one owner per atom

**Outcome.** Every 33GOD feature (crank, hindsight hooks, tab painting, target-watch…)
lives in a formal repo and is listed in the catalog `features.toml` at this repo's
root. Every shared building block ("atom": which panes exist, which agent is in a
pane, its session, its live state, project identity, the clock) has exactly one
owning repo; every other copy is provisional or retired. Agents follow the
`33god-features` global skill while the migration runs. Crank dogfoods it first.

**Decided by the operator (2026-11-06).**
- F1: anything declared a feature is tracked in a formal repo. Crank goes first.
- F2: `features.toml` here is the full catalog and the planning map. An install
  disables features in its own untracked `~/.config/33god/features.toml`.
- F3: no pins. A pin is a temporary bandage with a reason and an exit ticket;
  features merge to main. CAND-49's pinned Hermes image is gone (CAND-52, Done).

**Proposed, awaiting approval** (`33god-features/asm-ownership-study.md`): split the
primitives. A new `delorenj/asm` (out of bloodbank) owns agent facts: process
detection, identity, native session binding, live state and attention.
`delorenj/zellij-driver`, repurposed with Deckard's deckard-mux code, owns
everything that talks to zellij: topology, focus, rename, pane input. Deckard,
pjangler, Holocene, Wingman and Flume consume. The design of features themselves
is `33god-features/feature-packaging-design.md`.

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
  - owner_project: asm (new repo, pending approval)
    request: extract the ASM with history; asmctl --json verbs; PJAN-202 detection rules
    ticket_ref: pending
  - owner_project: zellij-driver (pending approval)
    request: terminal driver lifted from deckard-mux; zdrive tabs|panes|focus|rename|send --json
    ticket_ref: pending
  - owner_project: crank (new repo)
    request: create delorenj/crank as the first formal feature repo; feature.toml; adopt live candybar rows
    ticket_ref: pending
  - owner_project: pjangler
    request: pj feature check (read-only) against features.toml and feature.toml
    ticket_ref: pending
depends_on: [I-8]
```

**Seam acceptance criteria**

- Every `[feature.*]` in `features.toml` has `status = "formal"`: its repo exists,
  has a board, a `feature.toml`, and is a 33GOD submodule.
- Every `[atoms]` row is `owned`; `pj feature why <atom>` lists no duplicate copy
  that is not declared provisional or `[[implements]]`.
- No pin without a reason and an open ticket; no hardcoded job id, candybar id,
  session name or home path in any feature (lint).
- `asmctl doctor --json` reports no duplicate rows, no ghost rows and no empty
  session ids on the live box.

