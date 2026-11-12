---
id: SPEC-agent-impact-awareness
initiative: I-11
companions:
  - routing-policy.md
  - brownfield.md
  - acceptance.md
sources: []
---

# Agent ownership and impact awareness

## Why

PMs and named agents need to recognize who owns a request and who should know about a change without relying on memory or broadcasting every action. Jarad requests hook-driven checks that reuse HeyMa's project extraction, declared project/workforce ownership, and Bloodbank delivery. The first product-backed seam is Voxxy voice-contract awareness for Phonograph.

## Capabilities

- **CAP-1**
  - **intent:** Identify the accountable owner and separately surface relevant projects when a new request arrives.
  - **success:** Declared ownership and explicit task scope outrank semantic scores; cross-project work has distinct child ownership; ambiguous ownership abstains; no suggestion transfers an active task or starts a second worker.
- **CAP-2**
  - **intent:** Warn affected consumers when meaningful changes alter a contract they use.
  - **success:** A Voxxy voice-catalog or synthesis-contract change includes Phonograph through its verified dependency even at low semantic relevance; an unrelated internal edit creates no recipient wakeup; planned, applied and deployed changes remain distinct.
- **CAP-3**
  - **intent:** Deliver concise, targeted handoffs or FYIs with an attributable result and no communication loop.
  - **success:** Each recipient has deduplicated stored, accepted and handled evidence; FYI does not authorize implementation; duplicate delivery, failed classification, missing recipients and receipt feedback cannot create duplicate work or recursive notices.
- **CAP-4**
  - **intent:** Demonstrate a useful second caller of the existing classifier before broad rollout.
  - **success:** The acceptance matrix proves independent project scoring, native context consumption, dependency-based targeting, bounded cost/latency, and actual recipient handling on a separately authorized pilot; absent recipient enrollment remains a visible activation gap.

## Constraints

- Parent owns integration outcomes only. Child PMs author implementation epics/stories and perform their own independent spec/quality reviews; no child loop or implementation story in the root.
- PJangler owns project identity and dependency metadata; Flume owns employee/role responsibility and recipient eligibility; HeyMa owns the reusable classifier; Bloodbank owns hook intake, behavioral dispatch and event contracts; Candystore owns durable event history.
- Ownership is authority, relevance is an estimate, and dependency impact is a third evidence source. No independent score set is normalized to sum to one.
- Reuse canonical hook ingress and generated adapters, not profile scripts, a new scheduler, or a fleet-wide competing agent consumer. Treat each harness's context injection and before-skills ordering as unproven until exercised.
- Thresholds, deadlines, caps and expiry in routing-policy.md are provisional pilot decisions, versioned and calibrated before activation; HeyMa's historical mention-classification results do not certify impact accuracy.
- No new event type, payload registration, workforce provisioning, service/configuration/clock changes, deployment, push or implementation is authorized by this planning package.

## Non-goals

- Universal auto-reassignment, autonomous implementation from FYIs, all-agent LLM wakeups, a replacement ticket lifecycle or a new feature repository.
- Per-tool Jev calls, semantic scores treated as ownership facts, inferred agent IDs, terminal input, or reuse of I-9's native-message work as a notification API.
- Real TTS/playback, live breaking voice changes, fleet rollout, notebook repair, or model spending during this planning pass.

## Success signal

For an authorized Voxxy voice-contract change, the source agent receives a clear owner/affected-project brief and the verified Phonograph receiver handles exactly one actionable notice with source evidence and a disposition. An unrelated edit causes no recipient wakeup. Loss, redelivery and acknowledgement do not duplicate work. Source/test, installed-hook and actual-delivery claims are reported separately.

## Assumptions

- Existing gatewayed Jev and hook-hub are the intended reuse surfaces, subject to owner contract review; extracting a shared callable interface may be required.
- The starting bands are .60 for local advisory and .75 for eligible semantic FYIs; known contract dependencies bypass semantic suppression. These are testable defaults, not measured accuracy.

## Open Questions

- Which actual supported receiver does Phonograph's owner designate? Its manifest has no agents and the fleet registry has no matching target. Flume may resolve the intake gap but is not authorized here to hire or enable one.
- Which supported harness first proves new-user-turn identity, context consumption and ordering before skill selection? Repeated Hermes pre_llm_call alone is not proof of a new request.
- Which existing schema can carry the awareness fact and handled disposition, or what owner-approved schema delta is needed? Bloodbank decides; do not fabricate names.
