---
title: "I-9: Maintainable cross-repository features in 33GOD"
status: draft
created: 2026-11-07
updated: 2026-11-08
project: 33GOD
initiative: I-9
working_mode: coaching
entry_point: vision-and-features
---

# PRD: I-9 — Maintainable cross-repository features

## Document purpose

Define the platform-level outcomes and observable requirements for managing
cross-repository capabilities as tracked features, with crank as the first proof.
This is a coaching-mode work in progress, not an approved requirements baseline.
Architecture decisions and mechanism details are preserved in `addendum.md`.
The decision trail lives in `.memlog.md`.

The parent owns cross-repository outcomes and seam acceptance; component PMs own
implementation epics, stories and execution in their respective repositories.

## Vision — initial user input

> “I want to change crank without hunting through eight repos.”

The primary desired outcome is to remove the hunt for crank's participating parts
when changing it. Whether the feature hub should also coordinate execution and
verification across component repos remains to be elicited. This statement does
not imply moving all implementation into one repository.

## Discovery checkpoint

Coaching is in Vision + Features. The opening outcome is recorded; success
measures, release scope and functional requirements are not finalized. Existing
research and approved boundaries are inputs, not a completed PRD.

Next: clarify what should happen when the operator starts a crank change at the
feature hub.

## Source inputs

- [Initiatives I-8 and I-9](../../initiatives.md)
- [Feature catalog](../../../../features.toml)
- [ASM ownership study](../../33god-features/asm-ownership-study.md)
- [Initial packaging research](../../33god-features/feature-packaging-design.md)
- [Director Rule](../../director-rule-plan.md)

The initial studies contain superseded proposals. The operator's 2026-11-07
clarifications and the initiative's accepted decisions take precedence.
