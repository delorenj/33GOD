# Changed-behavior gates

Select checks that demonstrate the slice's actual behavior:

- Live routing failures: check the public response, backend, and affected data endpoint; an authentication redirect alone does not prove backend health. Correlate Traefik DNS/health errors with container recreation timestamps and the configured health-check interval. If service recovers without intervention, verify current route health and endpoint responses, then stop without a speculative restart or patch. Distinguish the observed failure and recovery from any unproven recreation trigger.
- Hook changes: native loader registration, one event to one handler receipt, payload and context output, hub-down behavior, and concurrent session identity.
- Event changes: contract validation, broker delivery, and durable Candystore arrival.
- Managed ticket changes: resolve the canonical project and board binding, then
  prove the actual `px`/Krebs path with provider readback. A worker must claim
  before execution; evidence must belong to that attempt; an unanswered
  question must enter **Needs Attention**; and successful work is moved to Done
  automatically only after its evidence gate passes. A turn ending, review
  label, or accepted handoff is not completion. For recovery changes, exercise restart/lost-reply
  behavior, ensure old attempts cannot close newer ones, and ensure parked or
  expired workers do not retain execution capacity.
- Managed activation: verify the exact native Plane actor, board membership,
  credential binding, and runtime loader before enabling a board. If enrollment
  is missing, leave the controller disabled and report activation as blocked;
  NewAPI model OAuth is not a substitute for Plane attribution.
- Skill distribution changes: compare the canonical source with the installed
  bundle and load it through each affected native runtime; do not treat a
  source diff or catalog entry as installed parity.
- Holocene changes: typecheck, build, browser interaction, and live route verification.
- Compose or systemd changes: resolve the effective configuration, restart only affected units, and verify the running artifact.
- Template or generator changes: render into an isolated temporary directory and compare the intended owned projection while preserving foreign settings.
- Test additions or changes: run newly added or changed tests once before a
  long regression phase so import/fixture setup failures are separated from
  behavior failures. Do not treat a broad green suite, a negative regex, or a
  dead vocabulary check as proof. For a changed guard, use positive behavior
  and one targeted mutation or fault injection that should make the test fail;
  distinguish live tripwires from strings that never occur in current source.
  Keep known-red or boundary-unproven suites advisory until the failure is
  understood and the relevant boundary is exercised. Do not enable a slow
  suite merely because it exists or to improve a test-count metric.
- Workflow changes: inspect `paths`/`paths-ignore`, required checks, and jobs
  with deployment or restart side effects before merge. If the change triggers
  one, verify its completion and the running commit separately from the merge.

Run the affected tests and direct boundary checks, not a fixed suite by habit. A
config file, selected handler, board status, or zero exit status alone is not
proof that its downstream work succeeded. For nested components, verify the
parent's pinned source is the committed canonical revision before integrated
checks. Treat idle clients as unobserved until exercised.

Preserve unrelated WIP. Land coherent units promptly on component main and root main. Do not add speculative review layers or repeat unchanged checks.
