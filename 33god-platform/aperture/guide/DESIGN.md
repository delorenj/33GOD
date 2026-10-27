# 33GOD Field Guide — design system

## Direction
A *project dossier* as the organizing object. The first view is a single synthetic Studio Notes record moving from file to directory to tools. The whole guide borrows from precise wayfinding and technical field manuals, not terminal cosplay. Light background suits reading at a desk; cobalt is the committed identity plane, while ink and ice carry long-form explanation.

## Surface contract
- **Thesis:** one project identity can be found across tools; refuse generic feature cards and an abstract hero.
- **Own world:** cobalt title band, oversized dossier, hairline connectors, tabular annotations, open white reading space, restrained rounded geometry, high-contrast ink.
- **Story:** meet Studio Notes → understand source and index → prepare/maintain → separate the two meanings of migration → locate the fleet boundary → see the domain map and next action.
- **First viewport:** compact top navigation and title lead into a full-width three-part visual specimen; its plain-language caption reveals the mechanism without scrolling to a code block.
- **Form:** field-guide dossier / process map. No live service is queried. Interaction locally rehearses source/index/consumer steps; underlying prose remains present without script.

## Tokens and layout
Tokens live in `style.css` for reuse by future guide modules: `--ink`, `--paper`, `--ice`, `--blue`, `--blue-deep`, `--muted`, `--line`, `--measure`, `--page`, spacing and radius values. UI uses a system sans stack for legibility and a system mono stack **only** for code, IDs and commands. The page shell caps at 1180px; article prose caps near 70ch. Breakpoint at 760px stacks the specimen and unpins the table of contents. At narrow widths controls wrap and code scrolls within its own bounds. Do not use fixed height on reading sections.

## Components
- Guide masthead: actual 33GOD split-circle mark beside a 33GOD Field Guide label, chapter label and in-page navigation only. The cobalt visual world remains intact; the SVG's ink/pop fills are the live Holocene inverse-header colors, not the black/gold standalone variant.
- Dossier: three distinct representations of one synthetic project, not cards of three unrelated features. Explicit DEMO seal. Arrows/connector labels carry direction. Detail selector is an enhancement, never the only source of meaning.
- Chapter section: concise heading and prose, with a marginal index on wide screens.
- Command ledger: native closed-by-default `<details>` keeps examples optional; each row has a purpose/prerequisite and optional copy action, never execution. Syntax-only migration placeholder has no copy action. The full ledger is exposed in print even while closed on screen.
- Two-authority schematic: project/board and agent/profile lanes; typography distinguishes ownership, not hue alone.
- Domain atlas: eight canonical G labels, ordered by learning journey but each retains original group number, all future entries marked planned and unlinked.

## Behavior and access
HTML is complete without JS. JS augments dossier step highlighting and command copy with `aria-live` feedback; clipboard failure explicitly invites manual selection. No forms or backend. Focus uses dark blue on light surfaces and pale yellow on cobalt, each >3:1 against the adjacent ground. Links point only to real anchors. Reduced-motion removes transitions; print compacts the hero and dossier, shows all command rows, and hides controls/navigation. Any timestamped operating note is dated, not a dashboard.

## Boundaries
This design system belongs to `aperture/guide/`, not the ship-board dashboard. Future chapter pages may share `style.css` and the masthead grammar, but they must not reuse the Studio Notes specimen as a generic hero. No external resources or private project identities.

## Authorship note
Claude CLI was invoked to author this artifact, but returned `Not logged in · Please run /login` with zero model tokens. This design and implementation are a local fallback, **not Claude-authored**; do not present them as such. The CLI receipt is in the task's scratch directory, outside this publishable guide.
