# Changed-behavior gates

Select checks that demonstrate the slice's actual behavior:

- Live routing failures: check the public response, backend, and affected data endpoint; an authentication redirect alone does not prove backend health. Correlate Traefik DNS/health errors with container recreation timestamps and the configured health-check interval. If service recovers without intervention, verify current route health and endpoint responses, then stop without a speculative restart or patch. Distinguish the observed failure and recovery from any unproven recreation trigger.
- Hook changes: native loader registration, one event to one handler receipt, payload and context output, hub-down behavior, and concurrent session identity.
- Event changes: validate the contract, broker delivery, and durable Candystore
  arrival. For ticket ingress or grooming, trace one ticket from Plane webhook
  through publication, trigger, eligibility, and invocation receipt; inspect
  successful runs for `skipped` output. For n8n consumers, exercise the intended
  node in the running server and read back its durable receipt and downstream
  result. A separate `n8n execute` process or native Data Table node does not
  prove Code or custom node table access.
- Dev Journal processing changes: verify the configured model route with one
  structured extraction before bulk processing. Check representative history
  for recurring faults described in different words, unrelated faults grouped
  together, and collector caveats promoted to tickets. For schedule changes,
  verify previous-day targeting and that a verified partial report counts as
  generated. For replay changes, check that reruns create no duplicate tickets
  or rollups.
- Managed ticket changes: resolve the canonical project and board binding, then
  prove the actual `px`/Krebs path with provider readback. A worker must claim
  before execution; evidence must belong to that attempt; an unanswered
  question must enter **Needs Attention**; and successful work is moved to Done
  automatically only after its evidence gate passes. A turn ending, review
  label, or accepted handoff is not completion. For recovery changes, exercise restart/lost-reply
  behavior, ensure old attempts cannot close newer ones, and ensure parked or
  expired workers do not retain execution capacity. For label writes, prove PM
  updates preserve unrelated labels and assignees and cannot remove the
  pipeline-owned `agent:working` label.
- Board consolidation: read archived status and tickets directly before moving
  or archiving a board; an archived board's empty list is not evidence that it
  has no open tickets. Read back the destination tickets before retiring a board.
- Managed activation: verify the exact native Plane actor, board membership,
  credential binding, and runtime loader before enabling a board. If enrollment
  is missing, leave the controller disabled and report activation as blocked;
  NewAPI model OAuth is not a substitute for Plane attribution. PM dispatch
  eligibility is separate: a missing `bloodbank.enabled` means enabled, while
  explicit `false` opts out. Verify provisioning preserves existing routing
  fields rather than writing empty values.
- Skill distribution changes: compare the canonical source with the installed
  bundle and load it through each affected native runtime; do not treat a
  source diff or catalog entry as installed parity.
- Holocene code changes: typecheck and build; add browser interaction or live
  route verification when the changed behavior is visible there.
- Compose or systemd changes: resolve the effective configuration, restart only affected units, and verify the running artifact.
- Template or generator changes: render an affected existing role into an
  isolated directory and compare owned files, executable modes, and retained
  routing fields while preserving foreign settings. Include a role that omits
  optional fields when that is the reported failure.
- Regression tests: run the focused test for the reproduced failure first.
  Check the allowed and denied behavior of a changed guard; use fault injection
  only when an ordinary assertion cannot prove the boundary. Expand to a broad
  suite only for a concrete remaining risk.
- Workflow changes: inspect `paths`/`paths-ignore`, required checks, and jobs
  with deployment or restart side effects before merge. If the change triggers
  one, verify its completion and the running commit separately from the merge.

Run the affected tests and direct boundary checks, not a fixed suite by habit. A
config file, selected handler, board status, or zero exit status alone is not
proof that its downstream work succeeded. For nested components, verify the
parent's pinned source is the committed canonical revision before integrated
checks. Treat idle clients as unobserved until exercised.

Preserve unrelated WIP. Land coherent units promptly on component main and root main. Do not add speculative review layers or repeat unchanged checks.
