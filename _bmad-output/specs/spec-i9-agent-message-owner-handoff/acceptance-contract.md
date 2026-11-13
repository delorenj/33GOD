# Native Adapter acceptance contract

Planning proposal for Hermes Fleet adoption; derived from this spec's decision
log and inherited I-9 AD-2–6/8–9/12. **No test executed; no input authorized.**
These are bounded acceptance cases, not an instruction to keep researching or an
assertion that a native API/observer exists. Hermes Fleet is accountable for the
three native capability gates; crank owns admission/integrated proof, ASM owns
identity, and Bloodbank owns current-provider repairs.

## Smallest useful refinement

One owner-side contract, `agent.message`, with a supported-target capability
predicate, expected recipient incarnation, stable attempt correlation, submission
result semantics and a receiving-input evidence boundary. Do not design a generic
messaging bus, another agent runtime/detector, or terminal fallback. This proposal
sets required behavior, not a new wire protocol/CLI/implementation location.

Before implementation planning is called ready, Fleet supplies a contract document
and a **run manifest** for G1–G3: exact existing or proposed test entrypoint/argv,
source revision, executable digest, inputs, test-owned resources, expected events,
independent observer identity, result/evidence paths, teardown and stop conditions.
An absent invocation or missing observable marks its gate **BLOCKED**, not PASS.
This document does not invent a test command that does not yet exist. The owner's
next bounded deliverable is that contract/run manifest or one precise evidenced
unsupported outcome; no unbounded discovery task is requested.

## Shared test arrangement, future authorization required

- Disposable real local-Linux Claude session in isolated Zellij; independently
  corroborate namespace/boot/PID/start token/native UUID and pane association.
  Never use operator agents or send input to operator panes.
- Separate disabled/neighbor sessions, replacement process/session and no-agent
  cases; record complete bounded native submission and receiving-input traces for
  every destination, not only absence of terminal keys.
- Throwaway Redis on explicit non-production port/key/channel namespace for any
  integrated ASM/crank dependency, only after BB-32 isolation is verified. No
  production fallback or FLUSH cleanup. Standalone native contract planning does
  not require contacting Redis or finishing every extraction.
- Stable attempt marker/body digest and authoritative occurrence ID are recorded
  before possible submit. Record exact contract/procedure/config/executable/source
  revisions. No credentials, operator transcripts or unscoped logs in evidence.
- Separate sender events, independent receiver events and subsequent processing.
  No inference/task-completion requirement is added. No native permission/config
  changes to force admission. Observation gaps stop the run and produce UNPROVEN.

## G1 — External schema compatibility and unsupported no-send

**Accountable owner:** Hermes Fleet. **Current verdict:** NOT RUN / BLOCKED pending
owner-supported external contract and capability discriminator.

| Case | Given / when | Required observable result |
| --- | --- | --- |
| G1.1 compatible request | Exact owner-declared supported executable/interface/config; valid expected target and stable attempt; submit once under later authorization | Declared framing/schema and result semantics used; correlation survives; independent native trace distinguishes submit from acceptance |
| G1.2 unsupported build/schema | Build/interface/capability differs or version capability is unknown; request submission | Adapter reports unsupported before any native user submission; full outbound trace proves zero user frames, no terminal fallback |
| G1.3 invalid/missing evidence | Malformed request, missing incarnation/start token/session/attempt, unverified endpoint or ambiguous discovery | Refusal before submission with actionable reason; zero native user frames |
| G1.4 upgrade boundary | Run same contract suite on a changed executable/config before declaring capability supported | Old evidence remains historical; unknown/incompatible capability stays disabled, never assumes semver or permanent binary pin |

**Acceptance evidence:** owner contract/schema/version-capability table and run
manifest, per-case observed native-submit trace, exact expected/observed result and
executable/config digests. Internal extracted frame/offsets are investigation
input, not upstream compatibility commitment. A transport write success cannot
satisfy G3. Fixture-only protocol tests cannot certify native compatibility.

**Pass:** every required case passes against the declared real cohort and review
corroborates zero-submit exclusions. **Fail/unsupported:** any bypass or fallback;
**unproven:** missing trace/capability evidence. No send when unsupported.

## G2 — Exact receiving incarnation through asynchronous ingress

**Accountable owner:** Hermes Fleet for endpoint/ingress protection. **Crank owns**
the separate final-admission exclusion contract and its integration cases below.
**Current verdict:** NOT RUN / BLOCKED; installed optional pre-await session check
is not proof of a final generation fence.

| Case | Given / when | Required observable result |
| --- | --- | --- |
| G2.1 stable recipient | Independently match live expected process/native session and connected endpoint; submit | Only that incarnation can accept; receiver identity is corroborated independently of ASM and socket filename |
| G2.2 changed before send | Replace PID incarnation/endpoint or native UUID after discovery but before final validation | Zero native submission; explicit wrong/unverifiable recipient result |
| G2.3 change during ingress | In a controlled real disposable session, rotate/change native session across every owner-identified asynchronous check-to-admission boundary, or demonstrate a tested native invariant excluding that transition | No input acceptance by a different incarnation. If submission was already possible, sender result may be unknown and remains fenced; never claim zero submitted bytes after they may have left |
| G2.4 connected-path substitution | Change pathname target/reuse address after connection; exercise the actual supported route | Connected process/session validation prevents input reaching a replacement endpoint; no pathname-based retarget/fallback |

Fleet's contract must explain same-process session rotation, exec/inherited
endpoint behavior and process-shared endpoint rejection. Either prove protection
for the supported cohort or mark that cohort unsupported. Do not manufacture a
registry entry or fake a receiving session to obtain callbacks. Owner must state
how the real ingress boundary can be exercised/observed; inability is BLOCKED,
not a fabricated race proof or permission to patch a live process.

**Crank integration cases, distinct accountable owner:**

- Pause a proposal worker across takeover. Only one final authority retains submit
  access; no predecessor can later write. A lease check followed by unfenced write
  fails even if no race happened in one run.
- Order revocation before last-point revalidation under uninterrupted exclusion:
  zero submission. Queue revocation after possible submission: block new admission,
  do not promise retraction, cancellation or continuous idle.
- Re-opt-in/new binding/authority takeover while old outcome is unknown: no new
  nudge to the same receiving incarnation. Held/silence/timeout do not clear it.
  Corroborated acceptance completes original without replay; terminal nonacceptance
  clears only if it rules out later native release.

**Acceptance evidence:** exact boundary map, independent process/session and
receiving-admission observations, complete submit traces, authority-order record,
expected/observed results and limitations. Fleet can plan its native boundary in
parallel; integrated Crank cases require the actual admission contract and identity
prerequisites. Any missing protection leaves input disabled.

## G3 — Independent receiving-input acceptance and exclusions

**Accountable owner:** Hermes Fleet for the native acceptance/receipt gate.
Crank's integrated cases are separated below. **Current verdict:** NOT RUN /
BLOCKED; no independently qualifying native input acceptance event corroborated.

| Case | Given / when | Required observable result |
| --- | --- | --- |
| G3.1 intended native input | Authorized supported native request to an independently bound disposable incarnation with stable marker/body | Independent receiver-side accepted-input record identifies exact incarnation, attempt marker/body digest and acceptance boundary; sender record alone cannot qualify |
| G3.2 native held/refused/unknown | Native inbox holds/refuses/drops, or transport times out/crashes after possible submit | Accurate separate native status; no input acceptance inferred from sender/preview/internal `delivered`; uncertain receipt reports uncertainty rather than retry policy |
| G3.3 native destination protection | Wrong/replaced/unverifiable receiving incarnation or unsupported native capability | Complete native submit/receiver traces establish declared zero-submit/refusal and no unintended acceptance; missing observation stays unproven |

### Crank-owned integrated acceptance cases

**Accountable owner:** Crank, using Fleet's G1–G3 contract and ASM/terminal facts.
These cases are integrated FR-6/admission proof, not Fleet's policy responsibility.

| Case | Given / when | Required observable result |
| --- | --- | --- |
| C3.1 opted-in rename/reorder | Selected opted-in incarnation receives one stable attempt/body; rename/reorder tab without identity change | Exactly one independently observed intended input acceptance, selection preserved |
| C3.2 complete policy negatives | Neighbor/disabled/replacement/unknown/stale/no-agent destinations | Complete bounded native submit plus receiving-input coverage proves zero unintended input; missing token/terminal silence alone insufficient |
| C3.3 duplicate/unknown occurrence | Duplicate authoritative trigger while action pending/complete/unknown; re-opt-in/new binding/takeover same receiver | Stable action reused; no duplicate input/new nudge while uncertain; occurrence equivalence/retention defined; unknown fencing per AD-6 |

Receiver evidence may be an established native event/transcript or exactly
specified receiving-input queue admission **only if** its semantics, target
binding and independent complete observation establish actual CLI input acceptance.
Model consumption or task completion is not required. Socket close, sender exit,
visible preview, a callback called `delivered`, or parked queue visibility alone
cannot pass this gate. The observer must not simply read the same ASM assertion
or sender journal as a second opinion.

**Acceptance evidence:** supported event/receipt schema, independent collection
method and coverage interval, exact destination map, per-case native input traces,
stable correlation/body/identity validation, expected/observed outcomes and
reviewer distinct from implementer. Missing observer/coverage is UNPROVEN; actual
unintended input is FAIL and stops the run.

## Verdict and stopping rules

G1/G2/G3 each report PASS / FAIL / UNPROVEN / NOT RUN with exact evidence. No
aggregate green hides a missing gate. Owner contract planning may be ready while
all three behavioral gates remain blocked. If any gate cannot be fulfilled, return
one precise unsupported-capability statement and consequence; do not broaden
scope, weaken the guarantee or start another research loop.

Hub/workflow demonstration, scoped FR-6 and full I-8 remain three independent
verdicts. Gate completion does not lift the economics cap or authorize deployment.
