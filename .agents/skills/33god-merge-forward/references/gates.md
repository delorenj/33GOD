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
  or rollups. For report delivery retries, prove one real delivery receipt and
  a second invocation that sends nothing; distinguish provider delivery from
  Inbox placement and manual execution from a scheduled fire.
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
- Cross-host or cross-repository distribution: check source provenance and
  authorized destination before copying private files or committing them into
  a public component. A curated bundle, not the full upstream catalog, is the
  parity baseline when that is what the owner shipped. A stale gitdir, renamed
  remote, or staged deletions do not alone prove that tree needs repair.
  For skills, compare the authorized bundle with the installed selection and
  load it through each affected installed native runtime; a catalog entry or
  valid symlink alone does not prove runtime loading. Mark absent clients
  unverified rather than claiming parity. When correcting a public exposure,
  distinguish current-tree removal from reachable history and external copies;
  rewriting history requires explicit authorization.
- Holocene code changes: typecheck and build; add browser interaction or live
  route verification when the changed behavior is visible there.
- Factory asset changes: inspect the meaningful animation at the floor's actual
  overview scale, not just in close-up. Clean asset validation, typechecks, and
  console output do not prove the mechanism reads at that distance. Use the
  Factory's temporary-output checks; its normal build output is a live deploy,
  not an authorized validation step in an asset-only run.
- Scroll/playhead changes: exercise small wheel and keyboard inputs separated
  by pauses in both directions across a transition, including stopping midway.
  Verify progress is not repeatedly snapped back to the starting boundary;
  frame-motion counts or a fast continuous scroll alone miss this failure.
- Event-derived replay changes (select affected paths): reconcile totals with
  source events, separating activity credited to another component from counted
  events. Check attribution precedence with representative jobs and handlers.
  On the page, verify real versus staged labels and behavior at beat boundaries,
  view-switch restoration, and staged fallback for malformed or incompatible
  replay data. Check public output omits private event details even when those
  events still count.
- Release-console uploads: a platform consumes a version/build identifier once it enters any release draft, so `already used` means attached to a draft elsewhere, not uploaded. Before minting a new identifier or re-dropping the same artifact, read the track's drafts, its artifact library, and sibling tracks read-only to find the owning draft, and add from the library rather than re-uploading. Page metadata can lag processing or drop entries; decode the artifact's own manifest and signature to confirm version, package, and signing identity.
- Configuration or credential-location changes: inspect consumers of the old
  location, including scheduled jobs, before removing it. Preserve unrelated
  native settings; exercise affected consumers with their actual scheduler or
  noninteractive environment, not just the newly working CLI. Do not restore a
  plaintext credential to satisfy a legacy reader; migrate that reader.
- Compose, systemd, or launchd changes: resolve the effective configuration;
  select container contexts explicitly and restart only affected units.
  Verify the running artifact and intended client's reachability, not just
  server-local health. For changed readiness probes, prove an unreachable
  endpoint fails. For startup changes, distinguish service restart, GUI login,
  and boot recovery; claim only the path exercised.
- Template or generator changes: render an affected existing role into an
  isolated directory and compare owned files, executable modes, and retained
  routing fields while preserving foreign settings. Include a role that omits
  optional fields when that is the reported failure.
- Regression tests: run the focused test for the reproduced failure first.
  Check the allowed and denied behavior of a changed guard; use fault injection
  only when an ordinary assertion cannot prove the boundary. Expand to a broad
  suite only for a concrete remaining risk.
- Build/check tooling failures: when parallel runs empty a shared output tree,
  stage builds separately and serialize shared publication/check access; verify
  overlapping runs, not just a serial retry. When ownership guards reject test
  fixtures because TMPDIR is inside a checkout, use a non-repository temp root
  for those fixtures rather than weakening the guard.
- Workflow changes: inspect `paths`/`paths-ignore`, required checks, and jobs
  with deployment or restart side effects before merge. If the change triggers
  one, verify its completion and the running commit separately from the merge.

Run the affected tests and direct boundary checks, not a fixed suite by habit. A
config file, selected handler, board status, or zero exit status alone is not
proof that its downstream work succeeded. For nested components, verify the
parent's pinned source is the committed canonical revision before integrated
checks. Treat idle clients as unobserved until exercised.

Preserve unrelated WIP. Triage audit failures against the current slice before
remediating them: a finding caused by another agent's in-progress work is a
coordination input, not a gate for unrelated delivery. Land coherent units
promptly on component main and root main unless the task assigns delivery to a
wrapper. Do not add speculative review layers or repeat unchanged checks.
