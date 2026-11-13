# Verified intake and single planning handoff

Date: 2026-11-08. Parent coordination designation is accepted through user-supplied
delegated `pjangler-pm` disposition. Exactly one planning request has been published.
**Reconciled 2026-11-09:** flume-pm executed it once (2026-11-08 13:48:40–13:56:46Z)
and returned an actual reply: coordination **ACCEPTED**, Fleet contract adoption
**BLOCKED**. Fleet retains contract/mutation ownership; no code home is selected.

## Actual evidence and coverage

Earlier independent workflow `wf_da5e1134-282` inspected enrollment, selected role
and registry bindings plus scoped Pilot reads. Current targeted readback confirms:

| Evidence | Observed fact | Limit |
| --- | --- | --- |
| `33god-platform/components/hermes-fleet.yaml` | Fleet card names `hermes-agent-template` | No enrolled PM/board established by this card |
| Template and actual Hermes install roots | No `.project.json`/PM role at inspected paths; `~/code/hermes-agent` absent | Not workspace-wide proof no Fleet board exists |
| `pj list --json` | No Hermes/Fleet enrollment in returned registry | No invented PM from domain name |
| Flume manifest/role/selected registry row, rechecked before publish | Workspace `33god`, FLUME board `bf5663f0-8d37-41c6-97a3-437d45d64523`; profile/target `flume-pm`; registry schema integer 1; enabled true, gateway_scope fleet | Binding does not transfer Fleet ownership |
| Selected gateway state | `flume-pm` in served_profiles | Liveness is not execution/adoption proof |
| Earlier `px whoami --json` in Flume | Legacy; execution null, actors empty | No managed/native-actor readiness claim; legacy alone is not invalid routing |
| Earlier FLUME list, 74 returned issues | No matching native Claude message contract; FLUME-26/52 unrelated | Coverage is that returned list, not every board |

No credentials/chat identifiers/configuration or unrelated transcripts are copied.
No board writes or native proof input are authorized or performed by this handoff.

## Accepted coordination designation

The latest user-supplied delegated `pjangler-pm` disposition explicitly designates
existing `flume-pm`/FLUME **coordination-only** for this Fleet-owned planning
contract. This supersedes the earlier pending-designation recommendation, not its
historical evidence. Do not ask for that designation again. No standing authority,
new employee/board, code home or Fleet API is inferred.

## Supported transport and exactly one publication

- Naming authority: `bloodbank/docs/event-naming.md` §3.2, batch PM fan-out route.
- Payload authority: `bloodbank/schemas/bloodbank/agent/invocation.start.json`:
  `data.target_agent_id`, `prompt`, optional `thread_id`, `turn_id`, `context`.
- Producer: existing `bb emit`, canonical naming checks and full JSON Schema
  dry-run passed before publication. No new event type/payload contract invented.
- Command type `bloodbank.agent.invocation.start`; subject
  `bloodbank.cmd.agent.invocation.start`; schema
  `bloodbank.agent.invocation.start.v1`.
- `bb call` is not the agent response route: its implementation subscribes only to
  `bloodbank.rpy.lifecycle.task.invoke`. It was not used to publish this request.
- Command ID: `149134bb-3c88-4ebf-8ecf-98610e054933`.
- Correlation: `f9126f02-14cf-4fae-8a5c-00026336cefa`.
- Published envelope ID: `6da1f331-34cf-4b3d-9991-6c8719735c53`.
- Idempotency key: `d4568aa0-5fba-58a4-91b3-510421960016`.
- Publisher exit 0; transport publication only. No resend is authorized on
  uncertainty. Bounded correlated NATS lifecycle observation was armed first.
- First selected execution-journal read after publication: no matching row yet.
  This is pending observation, not accepted/rejected execution.

The existing generic invocation carries a **planning-only prompt boundary**, not
an invented distinct planning API or a new technically enforced sandbox.

## Scope actually requested

One turn to adopt/refine this package using read-only sources and return findings
in its final reply only. Search/reuse owner work, do not create/comment/link tickets.
Return separately:

1. Accepted/blocked coordination and Fleet contract-adoption receipt, authority limits.
2. Actual authoritative work/source/contract location or bounded no-match evidence.
3. Supported capability predicate or precise evidenced unsupported outcome.
4. G1–G3 runnable validation manifest, or exact blocked invocation/observable:
   entrypoint/argv (label proposals), revision/digest, disposable resources, inputs,
   expected events, independent observer, evidence, teardown and stopping rules.
5. Dependencies and next bounded owner result, not another unbounded research task.

Inputs are SPEC and companions, final AD-2–6/8–9/12 and existing feasibility
investigation. Reuse version-specific native findings; they do not certify support.
No code worker/subagent, file write, board mutation, implementation, native/socket/
pane proof input, focus/keys, runtime/configuration/service/clock, spend/model/cap,
Git publication/merge/deployment or repo creation is authorized. The catalog stays
proposal. Full request text and publication receipt are session scratch evidence;
no operator transcript is part of the request.

## Fleet owner intake: exact absence and proposed remedy (2026-11-09)

Read-only evidence; this records an absence, not a provisioning action.

- **The board exists.** Plane board `HERPM` "HermesAgentTemplate" (`565f8557-7c76-4f84-a167-0926c113ecfd`, workspace `33god`) has `archived_at` null and only 2 tickets: HERPM-1 (last activity 2026-07-31) and HERPM-2 (last activity 2026-08-20). It matches the Fleet card's `hermes-agent-template` repo (`github.com/delorenj/hermes-agent-template`, public).
- **Nothing is bound to it:**
  - Neither `~/code/33GOD/hermes-agent-template` nor `~/.hermes/hermes-agent` has a `.project.json`.
  - Neither repo mentions `HERPM` or the board id.
  - The live `~/.hermes/agents-registry.yaml` (2026-11-05) has no Hermes PM profile and no Bloodbank `target_agent_id` for it. Only the 2026-08-04 registry backups contain a `hermes-agent` PM row, and that row has bloodbank fields null.
  - `px` refuses writes to the board: no repo is bound to it and there is no Krebs ownership registry. `px show HERPM-n` reads still work.
- **What follows from the absence:**
  - No supported owner intake, ticket-write route or command target exists for Hermes Fleet.
  - The flume-pm coordination reply is not Fleet adoption.
  - Native G1–G3 stay BLOCKED / NOT RUN.
  - No resend, and no speculative native input.
- **Proposed remedy.** This is NOT approved: it needs owner/operator authority for profile and board provisioning, and this driver has not done it.
  1. Bind `hermes-agent-template` to HERPM (`pj init` enrollment).
  2. Hire its Hermes PM (`flume hire`).
  3. File one HERPM intake ticket for the native `agent.message` contract and its G1–G3 run manifest, linked to FLUME-76 and I-9.

## Response and admission state

**Current (reconciled 2026-11-09, no resend): executed once; actual reply received.**
Evidence `/home/delorenj/.claude/tmp/i9-flume-original-request-reconciliation-2026-11-09.json`.
One mode=ro journal row: flume-pm, `completed`/`success`, created 13:48:40.160176Z,
updated 13:56:46.047665Z, no rejection/failure/detach. Candystore: the four correlated
lifecycle events only, no reply text. Actual reply: flume-pm session
`20261108_084840_86474df2` message 3949 (finish `stop`), verbatim copy
`/home/delorenj/.claude/tmp/i9-flume-pm-final-reply-2026-11-08.md`, sha256
`e779f054f306a7002e1cec6946eea49a10d762917ab63ac7745abcf7c25b5854`. It returns,
against the five requested items:

1. Coordination **ACCEPTED** (coordination-only, read-only turn); Fleet contract
   adoption **BLOCKED** (Fleet retains ownership; nothing supported to adopt).
2. Authoritative native `agent.message` contract/wire API **ABSENT**: no Fleet
   contract, owner ticket, code home or public API; Hermes `agent/message_*` modules
   are internal conversation persistence, not native CLI messaging.
3. Capability predicate **UNSUPPORTED** as a compatibility contract: executable cohort
   partial (2.1.319 sha256 `dabafec8…` inspected, no owner table); external schema,
   async incarnation fence and independent acceptance observable all ABSENT.
4. G1/G2/G3 **BLOCKED / NOT RUN** with exact unprovable boundaries; only existing
   entrypoints are FLUME-76 structural checks; Fleet adapter/observer PROPOSED, no argv.
5. Next bounded owner result: Hermes Fleet through its own intake (not FLUME) returns
   the contract + G1–G3 run manifest, or its own evidenced unsupported statement.

Lifecycle completion is execution evidence; the reply is the coordination
disposition; neither is Fleet adoption, API readiness, input enablement or proof.
No exactly-once claim.

**Historical (2026-11-08): pending, durably queued; bounded observation expired.** Original observer
`bp5gw1kd3` ended at its fixed 10:13:53.579009Z deadline with
`OBSERVATION_TIMEOUT: no terminal receipt; do not resend`. Its process exit 0 is
not owner execution success. No watcher remains active; none was rearmed.

Final scoped read-only snapshot 2026-11-08T10:14:20.883733Z: exact command retained
in `BLOODBANK_COMMANDS` sequence **160790**, stored at `09:59:07.11897492Z`, IDs
and flume-pm target match. Batch durable delivered stream sequence **160027**, below
this command; 4 ack pending, 7 pending, 0 waiting, no API error. No selected execution
row, correlated observed event or matching Candystore event. This establishes
stored work not delivered by that durable, not route rejection/refusal. Earlier
gateway snapshot active/running, ExecMainStatus 0; historical NRestarts 7 proves
nothing about this request. Batch occupancy/stall cause is unestablished.

No resend, rearm, recurring poll/clock or infrastructure repair. Observation timeout
is neither a failed route nor adoption/native unsupported evidence. At that snapshot
the owner response was PENDING; it later arrived (current state above). Native
G1–G3 remains BLOCKED/NOT RUN.

## Existing owner work, dated prior readback

- [BB-32](https://plane.delo.sh/33god/browse/BB-32/): In Progress, explicit blocks
  BB-33 relation; isolated real Redis/key/channel test prerequisite.
- [BB-33](https://plane.delo.sh/33god/browse/BB-33/): Todo, blocked by BB-32;
  Bloodbank current ASM caller/native-session repair, not duplicate Fleet work.
- [PJAN-202](https://plane.delo.sh/33god/browse/PJAN-202/): Done; read-only discovery,
  not submission/acceptance capability. CAND-52 is not reopened.
- I-8/I-9 initiative links remain parent outcome authority. Unlinked native work is
  unverified, not an invented ticket. These dated readbacks are not deployed proof.
