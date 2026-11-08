# I-9 — Architecture inputs preserved from discovery

These are prior operator decisions and a delegated engineering choice, not a
completed architecture or newly elicited PRD requirements.

- **Component versus feature:** single-repo functionality is a component. A
  cross-repo capability becomes a feature candidate when its scattered parts
  become hard to maintain or extend. A promoted feature has its own formal repo
  as a tracked hub; participant implementations stay in their owning components.
- **First proof:** crank is the first promoted feature. Its registry and engine
  belong in the crank repo. The pj integration belongs in pjangler but is a
  participating part of the crank feature.
- **Authority split:** ASM owns agent facts (process, identity, session, state,
  attention). A separate terminal driver owns terminal topology and actions.
- **Deckard:** must require ASM; no independently maintained fallback state fold.
- **Terminal home:** the operator delegated this choice. A new terminal-driver
  component was selected to avoid repurposing the implemented Perth/zdrive
  product and its existing consumers. Zellij is the first backend; other
  backends are not promised. Generic terminal code may be extracted from Deckard,
  but must not depend back on Deckard or take ownership of agent classification.
- **Catalog:** `33GOD/features.toml` is tracked centrally, both as catalog and as
  a guide for expanding the pipeline. Per-install disables are local overrides.
- **Source policy:** features track main. Pins are temporary bandages carrying
  a reason and exit ticket, not permanent deployment architecture.
- **Continuity constraints:** Candybar remains the only recurring clock. The
  crank economics cap remains until I-8's completion conditions are met.

Mechanisms in earlier research (manifest fields, command names, receipts,
rollback implementation and proposed CLI interfaces) remain architecture input,
not frozen requirements merely because a sample transcript showed them.
