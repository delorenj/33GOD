# Monetization avenue 2 — License the whole stack

**Model.** Sell a license; customer deploys the 8-group stack on their own
hardware (or we deploy it for them). Phase 1's dogfood on Damien's machine is
literally the first fulfillment of this avenue.

**What phase 1 already gives us**
- Eight images + one compose = the installable product skeleton
- Dependency-ordered bring-up (G1→G8) with the ship board as the runbook
- Damien's deployment as the reference install + testimonial

**Gaps to close (phase 3 generalization)**
- Config surface: every Jarad-specific path/endpoint/secret behind `GOD_*` env
- Licensing/enforcement decision: per-seat, per-deployment, annual? Source-available
  vs binary? (This repo currently private-source — that's a start.)
- Multi-tenant secrets pattern (`.env.op` refs + customer's own vault)
- Install docs per group; one whole-stack runbook; a `compose up` that works
  on a clean machine
- Versioned releases (SemVer per group image; the mise-versioning skill already
  covers the pattern)

**Pricing signals to gather**
- What a solo dev / small team pays for: Linear+Claude Code+Cursor bundles
  today ($100–300/mo/head) vs what this stack replaces
- Our own measured productivity gains (crank logs, enrichment signals, LLM
  observability deltas) = the demo material

**Fit with the moat.** Highest ceiling — the full stack is the thing nobody
else has. Also highest effort.

**Risk.** Support burden across heterogeneous installs; secrets hygiene;
open-sourcing pressure on components (can be a feature: open core, paid
control plane).
