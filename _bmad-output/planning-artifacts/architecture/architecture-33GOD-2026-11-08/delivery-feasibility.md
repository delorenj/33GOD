# I-9 delivery feasibility — focused mechanism comparison

Date: 2026-11-08. **Route/owner accepted in planning; capability gates remain.**
The later [delegated disposition](route-disposition.md) supersedes the pending
recommendation status below. Historical investigation findings are preserved.
Planning only: no target inbox connection, proof message, test-agent creation,
terminal input, service or runtime change. Independent review used native research
and source inspection, not behavioral execution.

## Accepted route and narrow change

The user-supplied delegated pjangler-pm disposition accepts the first proof using
a pane-bound local-Linux Claude Code native-inbox Adapter, no terminal keystroke
fallback, and assigns narrow `agent.message` contract ownership to Hermes Fleet
in planning. Crank retains policy, opt-in, serialized admission and attempts;
ASM retains facts; terminal-driver retains topology/actions. The assignment does
not claim work intake acceptance, an API or implementation readiness.

PRD FR-2's terminal-specific wording and Spine AD-5 plus necessary dependent
references are amended with [explicit provenance/impact](route-disposition.md).
FR-6/NFRs and other scope remain unchanged. This accepts the invariant contract,
not reverse-engineered protocol as a stable API. Compatibility, exact session
protection and independent receiving-input acceptance remain blocking enablement/
proof gates. Unsupported means no send. Missing wrappers alone do not block
architecture agreement. Fresh independent reconciliation, quality checks and
uncertainty-fence fix recheck have passed; the spine is final as an invariant
contract. Capability prerequisites, implementation readiness and deployed proof
remain separate and unproved. See [final gates](reviews/final-gates.md).

## Mechanism comparison

| Route | Evidence | Disposition |
| --- | --- | --- |
| Ordinary Zellij input after process precheck | Zellij 0.44.3 exposes pane-addressed writes; Deckard checks startup readiness | Reject for this proof: replacement/foreground race remains |
| Truly conditional terminal input | No inspected documented process-incarnation/foreground compare-and-write primitive | Not established; not the smallest evidenced path |
| Claude native inbox | Public native messaging; installed code has connected peer checks, session filtering and correlated status plumbing | Recommended capability-gated candidate; not yet a certified proof cohort |

A pidfd identifies a task but provides no conditional terminal write. PTY input
addresses an asynchronous terminal stream. Deckard `5266199`,
`crates/deckard-mux/src/cli.rs:410–460`, checks startup readiness then spawns a
Zellij action; `readiness.rs:79–111` does not fence input to an agent incarnation.
Read-only Zellij help supplies no expected PID/start/native-session/foreground
condition. This does not prove that an upstream extension is impossible.

Native delivery avoids pane-recipient retargeting. It is not a claim to eliminate
all state races: it does not reserve idleness or cancel accepted messages. Reject
terminal input for the missing recipient fence, not an absolute no-race standard
that the native route also cannot meet. Freezing processes, ptrace, injection and
modifying Zellij are outside the proposed solution.

## Public support versus installed implementation

Official documentation supports per-session inboxes, `ListAgents`/`SendMessage`,
and scripts/hooks posting to sockets. It describes optional Linux authentication,
inbound accept/hold/refuse and tool-boundary delivery. Linux messaging is available
from 2.1.224, and all providers on the same machine from 2.1.248. Public
`claude agents --json` supplies native session/PID/status when available. Inventory
status is an observation, not an idle reservation. Resume under another process is
not in-place delivery.

The fetched documentation does **not** establish a complete external deterministic
message/receipt schema or compatibility commitment. Tools available to an agent
are not automatically a callable no-inference API for crank. The installed code
below establishes technical mechanisms, not public protocol stability or the
version/capabilities of any particular running target.

### Bounded installed-code evidence

Executable: `/home/delorenj/.local/share/claude/versions/2.1.319`.
SHA256: `dabafec82ca1319fa43d8be36a10fc61b1d11821cb98ad5df04ad95e199b8eed`.
Locations below are decimal **byte offsets**, not source line numbers. Symbols
and offsets are version-specific; no executable or credential contents are copied.

| Location, approximately | Observed mechanism | Limit |
| --- | --- | --- |
| 291227080 | Native sender checks connected peer PID, UID and expected process-start token before writing on that descriptor | Internal sender options, not proof that every public send path requests them |
| 317741355 | User ingress drops an optional `session_id` unequal to the current native UUID | Optional; occurs before asynchronous work, not a demonstrated generation fence at final queue admission |
| 317742655 | Prompt carries UUID and peer origin with `msg_id`, then passes inbound gate and enters queue | Origin `from` is sender-authored; queueing is not proof of consumption |
| 317743295 | Status handling correlates `orig_msg_id`; reply paths undergo namespace/peer validation | Not an ACK on the original stream; arbitrary external callback registration is unestablished |
| 317768668 | Callback sends `peer_message_status`, preserving message correlation and expected peer process checks | No supported external receipt subscription contract established |
| 315830654 | Held-message release emits `delivered` after release-to-queue callback | This status alone cannot prove model-input acceptance or transcript persistence |

The installed frame accepts user content plus optional session constraint, UUID,
message ID, sender/reply address and priority. The inspected standard native sender
constructs a user frame but does not visibly include the receiving `session_id`;
its existence in the receiver must not be assumed to protect every send.

Linux `SO_PEERCRED` and a connected Unix stream bind the transport endpoint, rather
than resolving its pathname again for every write. They do not alone establish a
native UUID or prevent same-process exec, inherited-descriptor use or session
rotation. The receiver checks session before awaiting materialization/self-sender
work; this trace has **not** proved a repeat check or cancellation at final queue
admission. An owner must establish stable session incarnation through that interval,
a supported final session fence, or declare that target capability unsupported.
Do not claim the source check closes this remaining identity seam.

No receiver-side event was established as the required acceptance observable. Callback
`delivered`, terminal echo, sender exit, socket close and UI preview are insufficient
by themselves. FR-6 does not require model consumption: a receiving-input queue
admission could qualify if the exact queue's semantics, session binding and
independent observation establish actual CLI input acceptance rather than merely
transport receipt or parked input. That has not been established here. The native
candidate is technically grounded but **not yet supported for an FR-6 behavioral
PASS**.

## Owner contract — accepted boundaries, capability gates unproved

1. **First cohort, only after corroboration:** local Linux Claude Code, still bound
   to the explicitly selected live pane/session/process incarnation. No headless
   delivery, cross-pane migration, session rotation or restart recovery is added.
   All other CLIs/routes are unsupported for this first proof; no terminal fallback.
2. **Identity:** ASM supplies namespace, native UUID, host/boot boundary, PID,
   canonical start token, observation time and eligibility/freshness. Adapter
   independently corroborates the connected endpoint and native session incarnation.
   Resolve canonical token units/equality through owner contracts, not guesses.
   Missing, stale, ambiguous or unverified facts cause zero submission.
3. **One final submit authority:** workers may propose attempts but cannot send
   directly. Crank's single submit authority serializes binding changes, revocation
   and final admission. Retain that exclusion through final revalidation and submit;
   an expiring lease alone cannot let a paused old sender write after takeover.
   A successor cannot acquire send authority while its predecessor can still submit.
   Exact crash/takeover exclusion belongs in the owner contract before enablement;
   a split-brain or unverifiable authority yields no send.
4. **Last controllable point:** after endpoint/session validation, immediately
   before the irreversible native write, revalidate active binding generation,
   revocation and fresh ASM eligibility under the same admission exclusion. A
   revocation ordered before this point prevents submit. Record decision and
   observation times. Socket setup/prechecks must not be followed by an unfenced
   worker or detached callback that can submit after authority is lost.
5. **Asynchronous limit:** the eligibility observation is not continuous-idleness
   enforcement. A later state change may occur before native dequeue. Once bytes
   may have been submitted, revocation blocks new admissions but does not retract
   that input or guarantee against later held-message release. Do not change native
   permissions/settings to force acceptance. Submission uncertainty is fenced, not
   treated as cancellation.
6. **Stable attempts:** one logical action is binding incarnation plus an
   authoritative trigger occurrence, with defined occurrence equivalence and
   deduplication retention. Persist the stable attempt before possible submission;
   duplicate dispatch reuses it. Crash/timeout after possible submission becomes
   outcome-unknown. No blind replay or fresh nudge to the same receiving process/
   native-session incarnation across opt-out/re-opt-in, new binding IDs or authority
   takeover. Reconcile only by corroborated receiving-input acceptance (complete
   original without replay) or terminal nonacceptance ruling out later native
   release. Silence, timeout and held status cannot clear it. This is not universal
   exactly-once delivery.
7. **Honest milestones:** proposed, admitted, transport-submitted, held/refused/
   dropped, receiver input-accepted and subsequent processing remain separate.
   Receiver-side acceptance evidence must correlate the attempt marker/body digest
   and native session/process. Queue release alone never becomes observed-delivered.
8. **Acceptance prerequisites:** owner-supported schema/discovery/receipt contract,
   tested capability/compatibility boundary, exact session-incarnation protection
   and an independently corroboratable receiving-input event. A tested executable
   digest records evidence; it is not a permanent deployment pin. Unsupported
   capabilities fail closed on upgrade. Do not fabricate Claude registry entries
   or impersonate a native session to make callbacks work.

## Future proof, not present authorization

Use separately authorized disposable real Claude sessions, isolated Zellij and an
explicit throwaway Redis endpoint/key/channel namespace. Observe **native sends
and receiving inputs**, not just terminal keys. Independent observation must
corroborate the receiving process/native UUID without copying ASM's assertions.

Required scenarios: enabled target across rename/reorder; disabled and neighboring
sessions; replacement process/session; unknown/stale identity; empty pane; duplicate
trigger; revocation before final admission; change after possible submission;
unknown outcome; stale sender/takeover. Record complete bounded submission and
receiving-input observations for every destination. An unchanged terminal is not
proof of no native input. Stop on any unintended input or observation gap.

A correlated native transcript/receiver event could satisfy the acceptance
contract **if its semantics and completeness are established**. No such supported
observable was corroborated here, so do not name an invented command or claim
that an observer already exists. Missing coverage means unproven, never PASS.

## Independent review and status

- Native-feasibility skeptic, task `a2569b30686e21c21`: recommends native candidate,
  terminal rejection and architecture agreement independent of deployed proof;
  flags external support, exact session binding and acceptance observability.
- Scope skeptic, task `a3d27930da728b83f`: identifies FR-2/AD-5 route conflict,
  unassigned native-message owner and continued pane-bound scope; requires an
  explicit delegated disposition, not silent transport substitution.
- Both received the bounded installed-code correction. This consolidation is
  author-written, not reviewer-authored or an independent reapproval of its edits.

| Claim | Current state |
| --- | --- |
| Native mechanism exists | Established by public docs and bounded installed-code inspection |
| Native route is a technically credible architecture candidate | Yes, with explicit capability prerequisites and asynchronous limits |
| Route/owner contract agreed | Accepted by later delegated pjangler-pm disposition, planning only |
| Owner Adapter ready | Not established; support, session fence and observer prerequisites unresolved |
| First CLI certified for behavioral proof | None yet; Claude is the only proposed candidate |
| Scoped FR-6 / full I-8 behavior PASS | Not run here |

Do not park the architecture because owner APIs have not been built. The route/
ownership disposition is accepted and fresh independent reconciliation, quality
checks and correction recheck passed. Architecture is final; capability
prerequisites, implementation readiness and deployed proof stay separate and
unproved. See [final gate disposition](reviews/final-gates.md).

## Sources

- https://code.claude.com/docs/en/cross-session-messaging.md — public inbox support,
  controls and timing; fetched 2026-11-08.
- https://code.claude.com/docs/en/agent-view.md — JSON inventory and resume/copy semantics.
- https://zellij.dev/documentation/cli-actions — public input actions.
- https://man7.org/linux/man-pages/man7/unix.7.html — connected socket and peer credentials.
- https://man7.org/linux/man-pages/man2/pidfd_open.2.html — stable task handle.
- https://man7.org/linux/man-pages/man7/pty.7.html — terminal-stream semantics.
- Native researcher `aa36c2cf5c9149606` plus bounded main-assistant inspection of the
  executable identified above; no target socket connection or proof input.
- [Architecture](ARCHITECTURE-SPINE.md) and [gate disposition](reviews/gate-disposition.md).
