# The Manual (I-10)

LEGO-style picture manuals for 33GOD. Pictures and arrows, one page at most, colourful and childlike, and an **accurate** mental model underneath. First reader and dogfood: **Damian**, who freezes at a wall of text and runs his own 33GOD peer on a Mac Studio. Second audience: wannabe software engineers who could build cool things if they grokked the high level.

- Vision (Jarad, unedited): [`THE_MANUAL.md`](../../THE_MANUAL.md)
- Initiative and seam acceptance criteria: [`initiatives.md`, section "I-10 The Manual"](../../_bmad-output/planning-artifacts/initiatives.md)
- Product brief: [`brief-the-manual-2026-11-11`](../../_bmad-output/planning-artifacts/briefs/brief-the-manual-2026-11-11/brief.md)

## What lives where

| Path | What it holds | State |
|---|---|---|
| [`research/`](research/) | Ground truth the grammar stands on: [`platform-map.md`](research/platform-map.md) (what really runs, 2026-11-11), [`lego-atoms.md`](research/lego-atoms.md) (LEGO atoms, comprehension research), [`damian-reality.md`](research/damian-reality.md) (his box, his world). Read-only inputs. | written |
| [`grammar/`](grammar/) | The visual grammar. [`v0.md`](grammar/v0.md) is "Blip & Wall": atoms, lines, colours, word budget, page template, forbidden list. One file per version. | v0 |
| [`scale-meter.md`](scale-meter.md) | The nesting level meter for the whole platform, from the map's parent chain, with evidence and corrections to Jarad's example. | v0 |
| [`books/`](books/) | The book plan ([`README.md`](books/README.md)) and, per book, page storyboards. Book 1 page 1 is ready to draw: [`page-01.storyboard.md`](books/book-01/page-01.storyboard.md). | Book 1 p1 |
| [`feedback/`](feedback/) | [`LOG.md`](feedback/LOG.md): Damian's tell-back of each page, verbatim, plus the standing hypotheses. | template |

Planned, not yet created (per page, in `books/book-NN/`): `page-NN.svg` or `.html` (the drawn page), `page-NN.evidence.md` (the evidence sheet), `page-NN.twin.txt` (the alt-text twin).

## The iteration loop

```
draft page ──► Damian reads ──► tell-back + comments ──► feedback/LOG.md row (FB-nnn)
     ▲                                                          │
     └──────── grammar change (vN+1) cites FB-nnn ◄─────────────┘
```

1. **Draft** a page from its storyboard. Use only atoms in the grammar. A new atom needs a grammar change first.
2. **Prove** it: every claim has an evidence row, checked against live code or config, never against docs alone. Re-probe the reader's box.
3. **Publish** as a web page Damian can comment on.
4. **Read.** 5-second glance, one-read tell-back, transfer questions. Score complete, incomplete but safe, or wrong. Only "wrong" fails.
5. **Log** it in `feedback/LOG.md` with his words verbatim.
6. **Change** the grammar or the page. The commit cites the `FB-nnn` row. Bump the grammar version.

## Rules that do not bend

- One page, one idea, one screen. Words are labels, not paragraphs.
- A page is never shipped for being pretty when it is wrong. Code wins over docs. When they disagree, the evidence sheet says so.
- Docs here go stale in days. Use file mtimes as a compass, and print only stable facts (7 days), never live counts.
- The Director Rule: this directory holds the manual. A child project that wants a "what my component is" page gets a delegated ticket, not work done here.
- Generic bricks, no LEGO logo or type. Say "LEGO-style".
