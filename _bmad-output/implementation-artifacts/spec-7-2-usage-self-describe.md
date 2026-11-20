---
title: '7.2 Adopt usage as the self-describe contract (33GOD-103)'
type: feature
created: '2026-11-19'
status: in-progress
route: dispatch
review_loop_iteration: 0
baseline_commit: 7df9ca1c312926cfd7e73d92e1d813625a3a9991
context: []
---

<frozen-after-approval reason="Delegated user-approved AC1-5; implementation and main publication authorized">

## Intent

Every component must expose its command surface in jdx usage KDL, without scraping help at consumption time. Upgrade usage first, verify framework exporters, convert px and skillex first with parser/table drift tests, then convert the remaining eight one at a time.

## Boundaries & Constraints

Always keep native names canonical. Generate px and skillex from their own command table/parser, retaining px's zero-runtime-dependency rule. Verify real output with the installed usage parser. A static .usage.kdl is allowed for the other eight, particularly where an exporter does not fit or modifying the live parser would collide with unrelated work. Record exporter failures and fallback choices. Planning is in the root under the explicit Epic 7 exception; code is in its native owner. Use isolated worktrees, preserve unrelated changes, publish verified slices to component main then root own-only pointers/evidence. No board or assignment writes.

Never create a bespoke schema, migrate envelopes or exit tables, add passthrough, change scheduling, run parent bmad-loop, or sweep unrelated gitlinks. No production command actions are needed for description tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected behavior | Error handling |
| --- | --- | --- | --- |
| Description | px/skillex --usage-spec without project configuration | KDL only on stdout, exit 0, no network or actions | Propagate export failure |
| Parser drift | New command, alias, argument or option | Generated spec changes; parity test notices omissions | Test fails |
| Terminator | --usage-spec after -- | Not a root description request | Native parsing unchanged |
| Unavailable exporter | Missing/broken/incompatible exporter | Record actual failure; static usage spec for affected remaining component | Do not add broken runtime dependency |

</frozen-after-approval>

## Code Map

- `pilot/src/surface.js`: COMMANDS, FLAGS, OPTIONS, ALIASES are dispatch/help authority; use built-ins to serialize these directly. `pilot/bin/pilot.js` must short-circuit before binding/network.
- `skillex/src/cli.ts`: Commander 15 program and register* functions; generate after registration before parse. `tests/node/` holds Node tests; package build produces dist.
- `pjangler/src/index.ts`, `flume/packages/flume-hr/src/index.ts`: Commander trees. Flume's shared index has active unrelated changes; static fallback avoids collision.
- `krebs/bin/krebs.mjs`: parseArgs, parent-owned source.
- `candybar/src/candybar/cli/main.py`: Typer 0.27.3 tree.
- `bloodbank/cli/bb.py`, `candystore/candystore/cli.py`, `33god-platform/waybill/waybill/cli.py`, external `HeyMa/components/wax/bin/wax`: argparse owners; prefer static snapshot when importing has side effects or live parser is dirty.

## Tasks & Acceptance

**Execution:**
- [ ] `evidence-33god-103.md` — record current mise usage and all four real exporter probes before adoption.
- [ ] `pilot/src/usage.js`, `pilot/bin/pilot.js`, `pilot/test/usage.test.js` — zero-dependency table export, terminal guard and drift coverage; land px.
- [ ] `skillex/src/cli.ts`, `skillex/tests/node/usage.test.mjs`, package manifests — verified Commander export and drift coverage; land skillex.
- [ ] `pj.usage.kdl` in pjangler — full parser-derived snapshot and verification; land.
- [ ] `flume.usage.kdl` in flume — parser-derived static snapshot without shared-index collision; land.
- [ ] `krebs/krebs.usage.kdl` — describe parseArgs commands; land parent slice.
- [ ] `candybar.usage.kdl` in candybar — Typer exporter or static fallback; land.
- [ ] `bb.usage.kdl` in bloodbank — argparse snapshot; land.
- [ ] `candystore.usage.kdl` in candystore — argparse snapshot; land.
- [ ] `33god-platform/waybill/waybill.usage.kdl` — argparse snapshot; land parent slice.
- [ ] `components/wax/wax.usage.kdl` in HeyMa — static snapshot; land external owner.
- [ ] `evidence-33god-103.md` — permanent per-AC commands/exits, paths, commit URLs and remaining blockers; remote-main and git unpushed checks.

**Acceptance Criteria:**
- Given usage was 3.3.0, when conversion starts, then mise resolves the current release and usage --version proves it (AC1).
- Given four named exporters, when probed, then each exists and its actual output is parsed or its failure/fallback is recorded before dependency adoption (AC2).
- Given px and skillex, when described first, then each emits valid usage KDL from its own authority and its repository tests catch parser/spec drift (AC3).
- Given the other eight, when converted sequentially, then each answers --usage-spec or ships a valid static .usage.kdl (AC4).
- Given all ten conversions, when reviewed, then native names remain canonical with no bespoke schema, envelope migration, passthrough or scheduling change (AC5).

## Implementation Notes

Preflight PASS with legacy enrollment WARN. CodeGraph is populated but sidecar is predominantly fake embeddings; direct authority-file reads used instead of semantic claims. No unresolved intent gaps; reversible additive interface only. Parent authorized implementation without another human checkpoint and main publication, superseding generic build no-remote default. Dirty sprint-status is intentionally not modified.

## Spec Change Log

## Review Triage Log

## Verification

Run actual usage lint plus usage generate json on every spec. Run px offline suite and skillex build/typecheck/focused parity tests. Use mutation-sensitive parity tests, not only success-exit assertions. For static fallbacks record source and regeneration command, and prove command/flag inventory where parsers can safely load. Verify origin main contains each exact commit; run git unpushed in every written repo. Independent parent review remains distinct from implementer verification.
