---
title: "DeloHQ PRD Addendum"
status: final
created: 2026-09-23
updated: 2026-09-23
product: DeloHQ
project: 33GOD
---

# DeloHQ PRD Addendum

## Boundary decision

The product is intentionally split into an executive experience and the domain
authorities it presents:

| Option | Decision | Reason |
| --- | --- | --- |
| Make DeloHQ a new authority and system of record | Rejected | It would duplicate workforce, ticket, event, runtime, and history ownership. |
| Rename the entire experience to Flume | Deferred/rejected for v1 | Flume is the workforce authority and currently does not own projects, tickets, runtime, or the executive presentation. |
| Keep DeloHQ as the executive experience powered by Flume and hosted by Holocene | Adopted | It preserves a clear user-facing concept while keeping domain ownership convergent. |

DeloHQ may eventually earn its own repository or deployment if the experience
needs an independent release cadence, but that is a scaling decision rather than
an MVP prerequisite. The current product name is therefore retained as a
user-facing surface name, while Flume remains the workforce layer underneath it.

## Downstream handoff notes

- UX should define how Company, Now, Executive Inbox, Agent Office, Decision
  detail, Exception detail, and Action Receipt fit together on mobile.
- Architecture should define projection freshness, evidence provenance,
  authority boundaries, bounded action contracts, idempotency, and the exact
  Telegram-to-DeloHQ handoff.
- Story planning should preserve the distinction between an accepted request and
  a completed outcome. A success response without canonical completion Evidence
  is not an accepted completion criterion.
- The first release should evolve the existing Holocene `/hq` path. It should
  not introduce a second dashboard, a second event stream, or a DeloHQ-owned
  workforce roster.

## Preserved idea-bank material

The brief's idea bank remains a source for later discovery, not MVP scope. The
most promising deferred items are Company replay, governed delegation slips,
selective Hindsight context, voice brief navigation, and a future TDLib adapter.
Each must consume the same DeloHQ product model rather than create a parallel
source of company identity or action truth.
