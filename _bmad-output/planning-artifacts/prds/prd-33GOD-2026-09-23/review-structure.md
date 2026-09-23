# Editorial Review — Structure

This document exists to help a solo product owner and downstream UX,
architecture, and story-planning workflows make decisions from the DeloHQ PRD
without losing the product boundary. The selected model is **Strategic/Context
(Pyramid)**: lead with the thesis, establish the user and journeys, define the
capability spine, then state cross-cutting constraints and scope.

| Pass | Original Text | Revised Text | Changes |
| --- | --- | --- | --- |
| structure | §3 Glossary before §4 Features | PRESERVE §3 in its current position | The glossary is scaffolding for the FRs and prevents downstream readers from interpreting Employee, Agent, Evidence, or Canonical System differently. No word reduction. |
| structure | §5 Information Architecture and Experience Rules | PRESERVE §5 between feature requirements and authority boundaries | This short bridge translates the capability spine into navigation and attention rules before the document moves into ownership. Cutting it would make the UX handoff less usable. No word reduction. |
| structure | Repeated DeloHQ-is-not-the-authority statements in §1, §6, §8, and the addendum | PRESERVE the repetition at each decision point | This is load-bearing reinforcement, not true redundancy: vision establishes the thesis, §6 names owners, §8 protects scope, and the addendum records the naming decision. No word reduction. |
| structure | §12 Assumptions Index and §11 Open Questions | PRESERVE as the closing control surface | The assumptions and phase-gated questions belong after the requirements and metrics, where reviewers can distinguish committed behavior from unresolved implementation gates. No word reduction. |

The document is 4,151 words; no length target was provided. The structure pass
recommends no cuts or moves. The current length is appropriate for a chain-top
internal PRD whose FRs will be source-extracted by three downstream workflows.
The only structural defect found—the `8.1`/`8.2` headings under §9—was corrected
before this review was recorded.
