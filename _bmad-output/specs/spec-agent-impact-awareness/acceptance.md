# I-11 seam acceptance and pilot sequence

These are required future checks, not results executed in the planning pass. Parent acceptance exercises supported seams; child internals/tests belong to child PMs. No real synthesis, voice change or agent provisioning is required to plan the pilot.

## Smallest delivery sequence

1. **Owner planning:** HeyMa returns the reusable classifier seam; PJangler returns canonical metadata/alias/dependency proposal; Flume returns responsibility/recipient contract and an evidenced Phonograph receiver or gap; Bloodbank returns checkpoint/context/delivery contract; Voxxy confirms the pilot contracts and consumer evidence. Each owner reconciles existing work and authors only its own BMAD stories. They may plan concurrently; one owner per ticket/file scope.
2. **Shadow replay:** source-controlled, human-labelled request/change cases through the shared classifier and deterministic policy, no recipient wakeups. Live Jev replay is separately authorized/budgeted; never substitute expected scores for returned evidence.
3. **Native hook proof:** exercise actual context-consuming harnesses on disposable sessions, with actual new-turn identity. Show what the model receives before its first skill action. Separately prove true meaningful-change boundaries and failed/missed-edit behavior. Unsupported harnesses remain explicit.
4. **Targeted pilot:** only after receiver enrollment and delivery contracts are verified and live activation authorized, send one benign intended-contract notice using current schemas/targets. Read the actual recipient disposition. No breaking Voxxy deployment, real TTS or broad rollout.
5. **Expansion:** broaden only after the gates below pass, following owning-component implementation reviews and source/install/activation proof. This package does not approve merges or runtime cutover.

## Required cases

| Case | Expected seam result | Evidence |
|---|---|---|
| Voice memo says Vox, Voxxy, Phonograph and old Dubplate | Canonical projects `voxxy` / `phonograph`, no extra Dubplate project and no Vinyl substitution | Registry/alias revision, actual independent scores, source brief |
| Request belongs to a different owner but merely mentions the current repo | Propose handoff or split; no autonomous reassignment/duplicate worker | Declared scope, result brief, no unintended claim/write |
| Multi-project request | Both project relevances can be high, not forced into a softmax winner | Raw typed answers + question/model revision |
| Ordinary external request repeated verbatim later | New request is evaluated/admitted; cached semantics may be reused, not silently deduped as old intent | Distinct native turn IDs + same input digest |
| Repeated pre_llm_call/tool loop for one request | One request-admission result; no repeated paid inference | Native turn lineage, hook receipts, actual call count |
| Voxxy planned change to `/voices` IDs/catalog or `/synthesize` contract | Phonograph is mandatory affected consumer even at low semantic relevance | Versioned source/declared edge, changed-contract evidence, one target notice |
| Unrelated Voxxy comment/internal refactor, no contract delta | No Phonograph LLM wakeup | Source diff, no-op decision, dispatch evidence |
| Source edit crosses into a new project via file tool or shell | Cheap invalidation; new boundary has explicit ownership, not per-tool model use | Canonical path resolution and cumulative diff |
| Failed file edit / pure read | No change notice | Tool outcome plus unchanged source digest |
| Cancelled plan / committed but not deployed | Correction or accurate committed phase; never falsely deployed | Notice revision chain, source receipt; absent deployment evidence |
| Registry/Jev unavailable, malformed score, too-large input, deadline | Visible unknown/pending/partial coverage; deterministic ownership retained; no fabricated empty success | Hook deadline, reason, missing partitions, no unintended routing |
| Semantic-only overflow >8 recipients | Overflow retained and disclosed; mandatory dependency recipients not lost | Full candidate count, selected/deferred/mandatory targets |
| Stale cache after alias/dependency/recipient change | Invalidate relevant cache; revalidate target before send | Snapshot revision key, final eligibility read |
| Broker ack, then consumer crash; handler completion, then ack loss | Redelivery same IDs; one accepted/handled effect; stored != handled | PubAck, durable inbox/outbox rows, exact disposition/event IDs |
| Missing/disabled Phonograph recipient | Explicit undeliverable; no guessed agent, terminal fallback or successful-handled claim | Selected registry evidence and failure disposition |
| FYI received; recipient replies “got it” | No classifier/fanout recursion, no new work claim | Root lineage, origin and hop fields, zero child notices |
| Notice itself points to the wrong owner | At most one verified forward, no bounce loop | Visited targets + hop budget and forward disposition |

## Pilot metrics and stopping rules

Use at least **30 labelled request/change cases**, including positive, negative, alias-only and ambiguous examples. Human labels and immutable source references must be prepared before reading model scores. Keep calibration and held-out cases distinct; report class counts/confusion matrix and actual observed results, not a universal accuracy claim. Initial activation target: >=90% actionable-FYI precision on held-out cases and **100% inclusion of known changed-contract dependencies**. If sample size is too small for confidence, disclose it and retain shadow-only use. Never adjust test labels to make thresholds pass.

Measure added request-path p50/p95 latency and actual inference calls/tokens/cost: proposed p95 <=1.5s and no source-turn path beyond its cancellation deadline. A complete dependency hit may be deterministic and require zero model calls. The new-user-turn test must distinguish cached scores from duplicate admission. Planned batch target: at most one FYI per recipient/root-work/contract/change-set revision, no notice from no-op edits, no automatic implementation from FYIs, zero acknowledgement-driven loops.

Stop pilot activation if recipient identity, before-skills context, contract naming, native turn identity, duplicate recovery or mandatory dependency coverage is unproven. Continue nonblocked component planning and shadow evaluation; do not park all work on a human sign-off. Missing permission for live actions is an explicit boundary, not an invitation to deploy.

## Final evidence bundle

Return independently: implemented source revision, test commands/exits and raw results, installed adapter/config receipt, actual injected-context/native turn proof, stored command/fact IDs and PubAck, exact recipient-accepted and handled disposition, any owner ticket reference, cost/latency, replay/crash negatives and outstanding gaps. Independent reviewer must differ from implementer. Parent closes the integration only on its own seam evidence, never because child tickets are Done.
