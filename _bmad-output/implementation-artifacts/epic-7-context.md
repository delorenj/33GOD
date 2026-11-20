# Epic 7 Context: 33GOD CLI Surface

## Goal

Make the native component CLIs usable from any shell and mechanically discoverable through one standard contract, without building an umbrella dispatcher. Planning stays in 33GOD under the approved Epic 7 Director Rule exception; implementation belongs to each component repository. No bmad-loop runs in the parent.

## Stories

- Story 7.1: Resolve and runtime-pin every component CLI
- Story 7.2: Adopt the usage spec as the self-describe contract
- Story 7.3: One JSON envelope and one exit-code table
- Story 7.4: 33god discovery and health
- Story 7.5: Argv guards unwrap 33god
- Story 7.6: Retire skills:sync and pure-alias mise tasks
- Story 7.7: Generate hub-skill command blocks from usage specs

## Requirements & Constraints

Native names px, skillex, pj, flume, krebs, candybar, bb, candystore, waybill and wax remain canonical. Aliases may exist but are not the platform execution spelling. Interpreter selection must not depend on ambient PATH or cwd pins. Do not replace component authority with a platform dispatcher, lifecycle engine, or scheduler. Candybar remains the only recurring clock.

Dogfood platform entrypoints (PILLARS #2), expose a liftable standard interface (#3), and adapt each framework rather than introduce another schema (#4). Components own implementation; the root owns integration and evidence. Preserve unrelated shared-checkout changes and land verified slices promptly.

## Technical Decisions

Use jdx usage KDL as the self-description format. Before the first conversion upgrade usage through mise to its current release. Prove each named framework exporter exists and produces parser-valid KDL before depending on it: @usage-spec/commander, usage-spec-typer, argparse-usage and clap_usage. If an exporter is missing or broken, ship a static .usage.kdl. Never create 33god.cli/1. Syntax comes from the parser or command table; no remote execution authority follows from a spec.

Output-envelope migration is a separate story. Its target is a superset of skillex v2, with optional additive fields. Existing pj raw JSON and Flume schema_version consumers must move before breaking changes. The shared exit table will be 0/1/2/3/4/5/6/130; native differences remain declared until conversion.

33god is discovery and health only, reading the component registry and usage specs. No passthrough until argv guard unwrapping and alias tests land. Do not invent a second component list or new feature atoms. Mise retains builds, tests, deploys, runtime tools and environment; only proven pure aliases and skill-operation wrappers are retired in their own story.

## Cross-Story Dependencies

7.1 precedes adoption. Convert px and skillex first in 7.2; the remaining eight follow sequentially. 7.2 blocks 7.7. 7.5 is required before any passthrough. Envelope conversion is per-component and consumer-first. Story 7.1 was accepted with tracked follow-ups 33GOD-109/111/112; do not absorb them into 7.2.
