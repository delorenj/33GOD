---
title: "The Manual: LEGO-style picture manuals for 33GOD"
initiative: I-10
created: 2026-11-11
status: draft
owner: 33god
dogfood: Damian
project_home: 33god-platform/manual
vision: THE_MANUAL.md
---

# The Manual: LEGO-style picture manuals for 33GOD

## Problem

33GOD has no customer-facing documentation system. What exists is a wall of text (the 2026-10-27 Field Guide is about 1,200 visible-text tokens on one page, fallback-authored), README files that contradict live code, and Jarad's own head. Docs here go stale in days. Damian, who runs his own 33GOD peer on a Mac Studio, **freezes at a wall of text** and has asked Jarad for a manual he can read in one page.

The harder problem is the mental model. A newcomer's first thought is never "event bus on NATS JetStream with a sidecar". It is "services call each other". A simplified picture that teaches the wrong model is worse than no picture. The manual has to be **simple and accurate**.

## Readers

1. **Damian, first.** A smart, busy coach and creative operator, not a software shop. He reaches 33GOD through Codex, Plane in a browser, Telegram bots and Obsidian, not a terminal. He has a real dev toolchain, so the limit is attention, not capability. He is a peer, never a client. He is the dogfood: every page is tested on him first.
2. **Wannabe software engineers, second.** People who could build cool things if they grokked the high level. They need a reusable thinking tool, not only a 33GOD tour: the same grammar should let them sketch their own system.

## Success

**Per page:** Damian tells the page back correctly after one read. Scored three ways: complete, incomplete but safe, wrong. Only "wrong" is a fail. n = 1 is a fast first gate, not validation.

**Per page, mechanical:** it fits one screen, uses only atoms the grammar defines, stays under the word budget, and every claim it draws has an evidence row traced to live code or config.

**For the grammar:** every change cites a feedback-log row. Three clean cold reads in a row earn a looser word cap.

**Beat the baseline:** the Field Guide at about 1,200 tokens. Page 1 spends 12 visible words.

## Scope v0

1. **Visual grammar v0** ("Blip & Wall"): a small fixed set of LEGO-manual atoms mapped onto software concepts, four typed line kinds, a nesting level meter, a colour code, a word budget, a page template and a forbidden list. [`grammar/v0.md`](../../../../33god-platform/manual/grammar/v0.md)
2. **The nesting meter** for the whole platform from the platform map's parent chain, with corrections to Jarad's example. [`scale-meter.md`](../../../../33god-platform/manual/scale-meter.md)
3. **Book 1 page 1, "Press Enter"**, drawn from its storyboard and published as a web page Damian can comment on. [`page-01.storyboard.md`](../../../../33god-platform/manual/books/book-01/page-01.storyboard.md)
4. **The book plan and the feedback log**, so the next pages are driven by what Damian says, not by this brief. [`books/README.md`](../../../../33god-platform/manual/books/README.md), [`feedback/LOG.md`](../../../../33god-platform/manual/feedback/LOG.md)

## Non-goals

- No wall-of-text docs, paragraphs, or "getting started" prose.
- No full platform coverage yet. Book 1 only, page by page.
- No install guide in the concept books. Install state lives in the Build book, gated on the Mac mirror being correct.
- No new tooling for authoring beyond what a page needs (a lint for word budget and evidence rows comes after Damian has read page 1).
- Not a replacement for the Aperture install bags or the platform map. Not marketing, not a customer-facing site for outsiders.
- No work inside a child project. A child that wants a page gets a delegated ticket (Director Rule).

## Approach

**Grammar first, then pages, and every page carries its evidence.**

1. Map each LEGO atom to a software concept only where it does the same cognitive job (step number, new-part outline, submodel callout, correct-orientation frame, the 1:1 bar). Add the atoms LEGO never needed: typed lines, a "this is simplified" badge, status marks.
2. Anchor each metaphor to the live system, not the docs. The bus is a **notice wall** where notes are pinned and listeners read at their own pace, never a post office. Mail is addressed and the bus is not.
3. Teach the thesis (why events on a bus that remembers, and why not direct calls) on a single page: you press Enter, a note is pinned, the bus keeps it a week, Candystore reads it from the bus.
4. Every claim has an evidence row: a file and line or a command, the box, the date, and whether it is stable or live. Code wins over docs. Pages are drawn for the reader's own box.
5. Test with Damian: a 5-second glance, a one-read tell-back, transfer questions, then change the grammar citing his words.

## Risks

| Risk | Mitigation |
|---|---|
| A simple picture teaches a false model. | Evidence row per claim, squint badge on every distortion, wrong-picture frames, scoped claims. The architect lens was treated as a veto. |
| Page 1 is too dense for the 5-second glance. | Hard cuts already made. A written cut order. A 30-word cap, 2 unfamiliar names, 4 chunks. |
| n = 1 reader. A coach is not the "wannabe engineer". | Treat as a gate, not validation. Add engineer-readers before any claim of "works". |
| Evidence decays in days (counts, statuses, Damian's Mac). | Print stable facts only. Dated xN stamps. Hazards expire in 30 days. Re-probe before each publish. |
| Docs and research are wrong in places (Candystore is stdlib not FastAPI, `nats_publish` path, "px is the only writer", the old 15-second hang hazard). | Listed in the storyboard and `scale-meter.md`. Fix the map before any page letters those facts. |
| The page's premise is unproven on his box: every Mac turn event so far came from mirror-driven runs. | One real interactive Enter by Damian before publish. |
| Colour and shape choices fail colour-blind or greyscale readers. | Shape twin for every colour, a greyscale pass before ship. Untested so far. |
| Damian cannot comment where the page lives. | Open question: choose the comment channel before publish. |
| LEGO is a trademark. | Generic bricks, no logo or type, "LEGO-style" in text. |
| The Mac mirror is incomplete (W5-W10 not started, several services degraded or blocked), so a page about "your box" can go false. | Concept books carry no install state. The Build book is gated. |

## Next steps

1. **Jarad:** review grammar v0 and the open questions (meter placement, comment channel, device).
2. **Orchestrator or Jarad:** fix `research/platform-map.md` (the three errors above).
3. **Draw page 1** from the storyboard and publish it as a web page Damian can comment on.
4. **Damian:** press Enter once in Codex on his Mac to prove the premise, then read page 1 and tell it back.
5. **Log** the tell-back in `feedback/LOG.md`. Apply the first grammar change with a cited row.
6. Draw page 2 ("Off? Notes Wait") only after page 1 has a scored tell-back.
