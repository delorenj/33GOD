# I-9 owner-contract readiness gate

## Current implementation orchestration — superseding scope, 2026-11-08

The user-supplied pjangler-pm relay now authorizes ticketed isolated implementation
and necessary owning-PM ticket coordination; it does not authorize merge, push,
publication, production deployment, spend/cap lift, competing clocks or unsafe input.
Earlier planning-only boundaries below are historical except those retained limits.

- **FLUME-76 In Progress:** sole implementer `i9-flume-contract-worker`, dispatched
  for coordination handoff/manifest and local structural validation, not Fleet native
  runtime code. Actual source/code-home or precise blocker is a required output.
  Fresh independent SPEC then QUALITY at frozen head 456facc: both PASS (below).
- **BB-32:** existing candidate/implementer retained; independent validation worker
  `i9-bb32-validation` verifies real disposable Redis ownership before tests. No fresh
  test PASS claimed yet. BB-33 remains blocked by the existing BB-32 prerequisite.
- **BB-35:** concrete head-of-line admission defect routed to existing sole
  coordinator `green-in-between-9d`; existing patch/reviews are not duplicated.
  Source counts fetched tasks before conversation lock, so same-thread waiters
  consume admission. Live 4/4 ack occupancy corroborates stall; exact current
  delivery-ID-to-handler mapping remains owner evidence, not inferred from old rows.
- Original command/correlation remain unresent. **Reconciled 2026-11-09:** executed
  once by flume-pm (completed/success 13:48:40–13:56:46Z 2026-11-08); actual reply:
  coordination ACCEPTED, Fleet adoption BLOCKED, contract ABSENT, capability
  UNSUPPORTED, G1–G3 NOT RUN ([intake](intake-and-handoff.md#response-and-admission-state)).
  Missing native G1–G3 still blocks dependent input, not independent development.
- **FLUME-76 bb9f560:** rooted independent SPEC BLOCKED_NOT_REVIEWED (reviewer's own
  mutation driver denied) with executed P1: manifest stale vs the reconciliation.
  Currency + regression-decoupling repair routed to the same implementer.
- **FLUME-76 0d707fc:** rooted SPEC FAIL (stale "remains pending" blocker false green;
  currency negatives never reached `check_currency`); repaired by the same implementer.
- **FLUME-76 456facc (current frozen head), 2026-11-09:** fresh rooted SPEC **PASS**
  (session `8265ad52-1800-46ff-a78d-976d1d170eb3`) then distinct fresh rooted QUALITY
  **PASS** (session `b3b3bc8f-0bca-48bc-8c35-cfc009e28072`), both dontAsk, no bypass,
  cwd = FLUME-76 worktree. Executed: structural + currency checks exit 0; 75/75
  structural and 7/7 currency negatives rejected (currency-stage). No P1/P2; P3 notes
  (default-off evidence-override seam unmarked, untested invariants, narrow free-text
  guards, executable pinned by self-consistency) are non-blocking and not routed.
  Gates passed is not landing: no merge/push authorized; ticket stays In Progress
  awaiting operator merge disposition. Native G1–G3 BLOCKED_NOT_RUN unchanged.
- Peer BB-35 activation/landing plans are under that session's separate authority;
  this driver has neither approved nor requested production activation.

- **FLUME-76 handed off 2026-11-09:** In Progress → `E2E Testing & QA` as reviewed
  local delivery at 456facc, **not merged** (orchestrator cannot approve merges).
- **FLUME-77 (new, In Progress):** safety/evidence P3 follow-ups (override seam
  marker/URI escaping/tempdir confinement, executable constant pin, durable in-repo
  evidence, stale-claim guard, doc accuracy), relates-to FLUME-76, stacked on 456facc.
  Sole implementer `i9-flume-contract-worker`. Test inflation/style items deferred.
- **FLUME-77 handed off 2026-11-09:** In Progress → `E2E Testing & QA` as reviewed
  local delivery at **5637ebf**, **not merged/pushed**; stacked on 456facc, lands
  after FLUME-76. Gate history: f86305d SPEC-1 PASS, QUALITY-1 reviewer PASS but its
  P3-1 (pending stale-claim guard narrower than reviewed 456facc) treated by the
  orchestrator as a P2 guard regression and repaired by the same implementer;
  5637ebf fresh rooted SPEC-2 PASS (`0804d0af-…`) then distinct QUALITY-2 PASS
  (`9779a670-…`), dontAsk, no bypass. Executed: checks exit 0; 89+3 structural,
  7+10 currency. Non-blocking P3 residuals recorded on the ticket, not routed
  (adoption-regex boundary corners, prose BLOCKED→ACCEPTED flip, `;` cost untested,
  parity wording scope, pending-side negation).
- **Fleet owner intake route — residual capability blocker (read-only evidence
  2026-11-09):** Plane board `HERPM` "HermesAgentTemplate"
  (`565f8557-7c76-4f84-a167-0926c113ecfd`, workspace 33god, not archived; 2 tickets,
  last activity 2026-08-20) exists, matching the Fleet card's `hermes-agent-template`
  repo (`github.com/delorenj/hermes-agent-template`, public). It is **unbound**: no
  `.project.json` in `~/code/33GOD/hermes-agent-template` or `~/.hermes/hermes-agent`;
  no Hermes PM profile or Bloodbank target in the live `agents-registry.yaml` (only
  2026-08-04 backup rows, bloodbank null); `px` refuses writes there (no bound repo,
  no Krebs ownership registry). So no supported owner intake/write or command route
  exists; Flume coordination is not Fleet adoption. Finite next action (owner/operator
  authority, not this driver): enroll `hermes-agent-template` to HERPM (`pj init`
  binding) and hire its Hermes PM (`flume hire`); then file one HERPM intake ticket
  for the native contract + G1–G3 run manifest, linked to FLUME-76/I-9. No resend,
  no speculative native input.
- **BB-32/BB-33 recheck 2026-11-09:** BB-32 In Progress, candidate e16635f1 with a
  six-file artifact still UNCOMMITTED in `.worktrees/feat-bb-32-asm-test-isolation`;
  AC1/2/3/5 PASS locally (independent 84+2+19 unittest receipts, owned port only);
  AC4 OPEN solely for remote CI execution, which needs checkpoint + publication
  through bloodbank-pm (push not authorized for this driver). BB-33 Todo, blocked by
  BB-32. No new worker dispatched: the residual is owner publication authority.

**Readiness:** FLUME-76 bounded coordination implementation ready/active; native
Adapter implementation not ready without true owner/source decisions; native input
BLOCKED/NOT RUN. Hub/workflow, scoped FR-6 and full I-8 remain separate outcomes.

## Prior planning gate record

Date: 2026-11-08. Intent: **`bmad-sprint-planning` readiness-only**. No sprint
tracking/stories generated. Scope: bounded parent handoff SPEC and companions,
final I-9 architecture and actual intake/catalog evidence, not implementation.

## Verdicts

| Question | Verdict | Meaning |
| --- | --- | --- |
| Spec coherence/preservation | PASS for planning proposal | CAP-1–3, inherited constraints, finite cases and owner boundaries preserved |
| Coordinator designation / supported request preparation | PASS | Delegated pjangler-pm designates actual flume-pm/FLUME coordination-only; existing naming/schema and target binding checked; one request published |
| Owner planning adoption/refinement complete? | Coordination response PASS; Fleet adoption BLOCKED (re-derived 2026-11-09) | Actual flume-pm reply received: coordination ACCEPTED; Fleet contract adoption BLOCKED, contract ABSENT, capability UNSUPPORTED. The reply is not adoption |
| Could a developer implement without inventing missing decisions? | FAIL | Missing owner-supported schema/capability, final async incarnation protection, independent acceptance observable and runnable G1–G3 manifest |
| Input enablement / G1–G3 proof | BLOCKED / NOT RUN | Unsupported means no native submit; no terminal fallback or weaker guarantee |

Accepted coordination is not Fleet contract/mutation ownership, a code-home
selection or API readiness. Missing wrappers alone do not block architecture
agreement; the listed native contract gaps block implementation/enablement.

## Independent checks and corrections

Main-assistant consolidation of returned independent reviews, not reviewer-authored
reports. Returns remain in workflow/task journals.

- `wf_19b50976-3d9`: initial readiness CONCERNS/implementation FAIL; found mixed
  Fleet G3/Crank policy ownership and phrase-as-node graph edge.
- `wf_2731908a-943`: targeted PASS after splitting Fleet native G3 from Crank
  C3.1–C3.3 and typing P1 → P2 adoption-authority; no criteria dropped.
- Current independent read-only reviewer `ab90425315fe7d430`: bounded planning
  CONCERNS, implementation FAIL, no inherited criteria loss verified. Identified
  stale readiness language as the documentary defect: designation is now accepted,
  request published, response pending. This re-derivation corrects that wording.
- Self-check: stable unique CAP-1–3 and local Markdown links PASS; raw catalog hash
  remains `e0867bb27ceb4205c946c3568a7abd48d3c7cf103f1169f529302912a05f81e4`.

## Remaining findings and narrow remedies

1. **Owner planning response received; Fleet adoption blocked (re-derived
   2026-11-09, main-assistant consolidation, not an independent readiness run).**
   The single request (command `149134bb-3c88-4ebf-8ecf-98610e054933`, correlation
   `f9126f02-14cf-4fae-8a5c-00026336cefa`) was executed once by flume-pm
   2026-11-08 13:48:40–13:56:46Z and its final reply was reconciled without resend.
   Coordination is ACCEPTED; Fleet contract adoption BLOCKED; no authoritative
   contract, code home or owner ticket exists; capability UNSUPPORTED; G1–G3 NOT RUN.
   Remedy: the next owner result belongs to Hermes Fleet's own intake, which has no
   enrolled board/PM today; no further FLUME planning turn or resend. Implementation
   FAIL and native G1–G3 BLOCKED/NOT RUN are unchanged.

   Historical record of the pending interval: At 10:06Z the exact stored command was
   read back at BLOODBANK_COMMANDS sequence **160790**, beyond this durable's
   delivered stream sequence **160027**; 4 ack pending/7 pending/0 waiting. No
   selected journal execution/reply yet. This proves retained, not-yet-delivered
   work for this durable, not an unsupported route or owner refusal. Gateway is
   active/running; root cause of occupied/stalled batch work is not established.
   Final snapshot 10:14:20Z: command still retained seq160790; delivered seq160027,
   4 ack pending/7 pending/0 waiting; no selected journal row or correlated events.
   Original observer expired at 10:13:53Z with no terminal receipt. No owner answer
   exists to incorporate. **PENDING / observation expired**, not route rejection,
   adoption or native unsupported. No observer is active or rearmed. Remedy: durable
   exact resume on actual later response/evidence; **no resend, infrastructure repair
   or recurring poll**. See [resume.md](resume.md). Readiness reevaluated after expiry:
   independent planning resolved, owner response dependency alone blocks this turn;
   implementation FAIL and native G1–G3 BLOCKED/NOT RUN remain unchanged.
2. **Native schema/compatibility and recipient-incarnation contract missing.**
   Owner refinement must name an exact supported interface/capability predicate
   and G1/G2 run manifest, or precise evidenced unsupported capability. Never code
   a guessed API or skip protection across async ingress.
3. **Independent receiving-input observable unestablished.** Fleet must define G3
   evidence semantics/collection and finite runnable manifest; Crank integrates C3
   separately. No native input test is authorized now.
4. **Identity/isolation/admission dependencies incomplete.** Dated BB-32 In Progress
   blocks BB-33 Todo; PJAN-202 Done is discovery only. Reuse actual owner evidence;
   ticket state cannot certify dependency behavior.

## Authorized operation and boundary

The single planning-only turn has been published, not merely prepared. It requests
read-only reuse of owner work and a final reply containing planning disposition,
authoritative sources, capability predicate and G1–G3 manifest or precise unsupported
evidence. It does not authorize further dispatch. After the actual response,
incorporate its findings and rerun readiness; pending is not a completed handoff.

No code workers, owner board writes, implementation, native/pane proof input,
service/clock, spend/model/cap changes, Git publication, merge or deployment. Exact
catalog delta stays unapplied proposal. No native gate, hub demonstration, scoped
FR-6 proof or full-I-8 verdict is promoted by this planning request.
