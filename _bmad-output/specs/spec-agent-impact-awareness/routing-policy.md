# I-11 routing and notification policy

Author: 33god-pm. Planning contract, not an installed policy. Source: Jarad's voice memo and the append-only spec memlog. Defaults below require pilot calibration and owning-component acceptance.

## Three different questions

| Question | Evidence | Result |
|---|---|---|
| Who is accountable? | Explicit scoped ticket/request, canonical project manifest, Flume responsibility declaration | One owner per bounded task; multiple tasks for a cross-project request. A current chat's repository is context, not ownership of every request. |
| Who may care? | Independent Jev yes/no relevance per project over compact project descriptions and verified aliases | Zero, one or many interested projects; scores need not sum to one. A project name used only as an example is not a work assignment. |
| Who is affected? | Declared consumer-to-provider contract dependency plus changed contract/evidence | Include the consumer even if the prompt never names it. Missing graph coverage is unknown, not proof of no impact. |

Precedence: explicit authorized scope/owner declaration > proven contract dependency for notifications > semantic suggestions. Conflicting declarations produce `owner unresolved` with evidence; do not silently pick or mutate ownership. A user may explicitly keep work with the present agent; that preserves relevant FYIs but never grants another project's code scope. Named specialists may have responsibility without a repo; resolve them only from Flume declarations, never from a fabricated project.

## Checkpoint A: request admission

Run once for a real new external request, before skill selection when supported native ordering is proven. Include the bounded current request, declared work item, real cwd/project resolution and compact eligible project/workforce metadata. Preserve the original prompt. Do not repeatedly treat Hermes pre_llm_call, tool replies, injected context, compaction, notice delivery or receipt messages as new user intent.

1. Resolve deterministic identity/ownership from owner APIs; create no new registry.
2. Reuse HeyMa's independent `noul` strategy, but use separately versioned questions for ownership likelihood versus actionable relevance. Do not reuse “mentions this project” as “owns this work.”
3. Return a compact context brief: owner and basis, interested projects/scores, known impacted consumers, suggested `handle here | propose handoff | split across owners | unresolved`, and explicit missing evidence.
4. Combined fresh lookup/classifier wall budget: **1,500 ms**, returning earlier where possible. Cancellation must bound child/network work. This is a proposed budget to measure against the shared hook deadline, not a claim current Wax's 120-second runner meets it.
5. On timeout/provider/registry failure, mark **classification pending/unavailable**, not `no relevant projects`; preserve deterministic ownership and ordinary in-scope work. Known cross-scope writes remain subject to the existing owner guard. A later result attaches only to its original turn/revision and cannot reroute a running worker.

## Checkpoint B: meaningful change boundary

Cheap local bookkeeping observes successful file-mutating operations, changed canonical project roots and known contract paths. Read-only calls and failed edits do not enter the change set. A pre-tool check may invalidate the brief when a request crosses into a new project/contract; it performs no model call unless admitting that genuinely new boundary, and never scores every tool.

Accumulate one work-item/change-set batch. Evaluate at commit, true turn end, explicit handoff or another supported batch boundary, whichever first closes the batch. A proven release/pre-publication adapter may produce an **intended change** notice before publication; turn-end/commit observation by itself provides no before-release guarantee. Review diff + base/head or dirty-tree digest, affected contract identifiers and owner-approved dependency edges—not the whole transcript. If hooks missed shell-driven mutations, compare the source diff; disclose an incomplete diff, never report complete coverage.

Use `planned`, `applied locally`, `committed`, `published` and `deployed` only when corresponding evidence exists. A deployment notice requires an actual deployment receipt. A later state updates the same notice lineage rather than restarting a conversation. A cancelled plan gets an explicit correction; it is not an applied-change notice.

## Provisional scoring rules

| Signal | Starting behavior |
|---|---|
| Independent relevance < .60 | Keep no recipient wakeup; retain aggregate/no-match evidence if classification actually succeeded. |
| .60 <= relevance < .75 | Local advisory to the source agent only. |
| Relevance >= .75 plus an actionable evidence-linked relationship | One batched FYI to the declared recipient, subject to expiry, eligibility and dedupe. Score alone cannot invent a relationship. |
| Ownership likelihood >= .90 and >= .20 margin over runner-up, with no binding resolving it | Propose a handoff; source PM retains responsibility until explicit acceptance. Lower/ambiguous scores abstain. Never automatic reassignment. |
| Explicit recipient or verified changed contract used by a consumer | Include regardless of semantic threshold. Dependency evidence must match the changed contract, not merely “both are audio projects.” |

Use one independent question per eligible project, not categorical choice/softmax. Consider all eligible registry projects. Deterministically partition questions/context within provider limits; if any part is missing, surface exact omissions. Start with a <=30K-character decision window; larger evidence uses bounded chunks with declared aggregation and full-text digest. Long-input .75 from HeyMa is evidence about mentions, not validated impact calibration. Store question/model/policy versions, input digest, snapshot versions, actual scores, truncation and uncertainty. Never label the scores calibrated probabilities until measured.

Cache successful judgments for **10 minutes** keyed by semantic evidence hash, question/model/policy revision and project/dependency snapshot versions. Carry stable native turn identity for admission idempotency separately: repeated identical text from a genuine new user turn is not a duplicate request. Revalidate owner/recipient before sending even on a cache hit. Never cache a transport error as successful empty output. No live Jev calls are part of planning.

## Delivery, batching and cost

- Publish one immutable, schema-governed fact for passive observers. Target only the selected recipients for agent processing through existing invocation routing; a fanout list inside a workqueue command does not implement broadcast.
- Each passive subscriber needs its own durable identity/consumer. Do not put every PM in one competing-consumer group and assume all received it. No LLM wakeup for uninterested agents.
- Aggregate per root work item + contract + recipient. Flush at commit/turn end/explicit boundary; no timer-only trailing flush or private polling loop. Merge a prior planned notice into the same notice revision.
- Cap semantic-only FYIs at **8 recipients per change batch**, matching the existing pass's conservative starting shape. Retain overflow and explain it in the source brief; never silently drop mandatory dependency or explicit recipients. Split required recipients into transport batches without an LLM fleet broadcast.
- FYI means awareness only. `handoff request` asks for an accountable acceptance; neither form authorizes code changes, duplicate claim or merge. Recipient may handle, mark not relevant, identify already-covered work, decline with evidence, or accept a scoped handoff. Actual follow-up uses its owning board; Krebs remains conditional on enrollment.
- Use scoped ingress configuration and existing authorized budgets. Report actual classifier request count, token/cost evidence when available; unknown cost is not zero. No new provider/key/budget is created here.

## Minimum logical payload (proposal, not a registered schema)

Carry notice/root-work IDs; original request/event, source agent/project and target IDs; owner versus FYI/handoff intent; planned/applied phase; changed contract and evidence references; independent score plus basis; dependency/registry/policy/question/model revisions; change-set base/head/digest; source summary and why the recipient cares; requested action/disposition; creation/expiry; and correlation/causation lineage. Keep IDs in envelope/data, never event type or subject tokens. Exclude credentials and whole private transcripts. Bloodbank chooses compatible canonical fields/types.

## Receipts and recovery

Distinguish:

1. **Stored:** schema-valid event/command persisted and broker PubAck observed.
2. **Recipient accepted:** destination durably records this notice ID/target/revision in its inbox. Invocation started alone is not handled evidence.
3. **Handled:** actual destination disposition with reason and any resulting owner ticket/ref, correlated to the exact notice. Invocation `completed/success` without that disposition is insufficient.
4. **Work completed:** separate lifecycle/evidence gate; a receipt or accepted handoff never implies implementation.

Use owner-owned durable outbox/inbox dedupe, not in-memory best effort. Dedupe by root work, recipient, contract, change revision and notice intent; retries preserve envelope/notice/command IDs and body. Allow **3 total attempts** inside a bounded invocation. After uncertain possible delivery, reconcile the exact ID before resend; never generate fresh IDs to bypass uncertainty. On exhaustion leave an actionable delivery failure, not silent success or a second clock. Receipt retention starts at **30 days**, notice expiry **24 hours**; owners must ensure retention covers every supported retry/replay window. Expired/offline/disabled/missing recipient is recorded, never redirected to another agent or terminal. Revalidate fleet schema, enabled boolean, profile and exact target immediately before dispatch.

## Loop prevention

Tag origin as external request, genuine source change, notice, or receipt. Only the first two can cause classification. Preserve root_work_id, notice_id, revision, causal parent and visited target set. A notice may be forwarded at most **one hop** to a newly verified actual owner; acknowledgements/handled messages do not fan out or invoke classification. A recipient's genuinely new contract change may create a new child notice, but must cite that new evidence and root lineage; replying “got it” cannot. Replay identical input/revision yields identical target decisions via stored results, not a new model draw.

## Decision basis

Pillars are referenced from `momo/PILLARS.md`, not copied. #1 chooses a narrow revenue-facing Phonograph pilot over fleet rebuild; #2 reuses Wax/Jev and current hook/bus tooling; #3 keeps one owner per shared classifier/identity atom; #4 uses Adapter for harnesses, Strategy for scoring and Observer for notices, with outbox at the real distributed seam. Global `agent-is-an-employee`, `zero-dollar-defaults` and `it-behaves-like-it-looks` favor concise handoffs, bounded inference and honest receipts.
