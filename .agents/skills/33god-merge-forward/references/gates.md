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
  pipeline-owned `agent:working` label. For a board that looks stalled, read
  `krebs status` or the tick journal before changing anything; triage and
  queued turns write nothing visible to Plane. For trigger or cadence changes,
  prove overlapping scheduled and event-triggered ticks both complete, and that
  a scope never holds two board turns at once; a removed fixed interval may
  have been the only thing spacing them.
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
- Factory asset changes: read the fixed overview and station camera views
  before shaping the model, then inspect the meaningful animation from those
  views in exported playback, not just in a modeling close-up. The Factory
  exporter can drop a property held constant for a whole clip and restore its
  resting value; check held states such as lit lamps in the export. A passing
  verifier does not prove fixed-camera readability; do not move an out-of-scope
  camera to make the asset pass. Forge stills omit behavior a
  runtime Driver adds; exercise it on the floor or report it unverified. If no
  relevant traffic reaches the station, report idle-only floor proof and hand
  off the integration gap rather than editing out-of-scope simulation code.
  Use the Factory's temporary-output checks; its normal build output is a live
  deploy, not an authorized validation step in an asset-only run. Check the
  verifier's manifest rules against the assigned placement before building. If
  a required field cannot be true (for example, nothing hideable at the
  station), leave it honest, flag it for the integrator, and report the
  verifier failure rather than a pass.
- Scroll/playhead and page-layout changes: exercise small wheel and keyboard
  inputs separated by pauses in both directions across a transition, including
  stopping midway, plus a held key's auto-repeat. Verify progress is not snapped
  back to the starting boundary and a held key cannot outrun the playhead;
  frame-motion counts or one fast continuous scroll miss these failures. Check
  layout at phone, tablet, and small-laptop viewports, not only one desktop
  size; on a phone, check sideways scroll, content under a fixed header, and
  pinned stages taller than the visible height. When positions are cached
  rather than measured per frame, resize a loaded page and
  compare it with a fresh load at the target size, snapshotting both only after
  fonts load and page height stops changing. For frame-rate or animation work
  on the shared box, run old and new interleaved and compare main-thread busy
  time under CPU throttling at 1x and 2x pixel density; 60 fps can hide a
  costly frame loop. If a timing test fails under load, check whether its page
  loads the changed code, then rerun it and the untested remainder on a
  settled box rather than the whole suite.
- Event-derived replay changes (select affected paths): reconcile totals with
  source events, separating activity credited to another component from counted
  events. Check attribution precedence with representative jobs and handlers.
  On the page, verify real versus staged labels and behavior at beat boundaries,
  view-switch restoration, and staged fallback for malformed or incompatible
  replay data. Public output must copy only an allowlist of event fields; fetch
  the published copy anonymously and search it for private names, paths, and
  keys, even though those events still count.
- Public product copy: check each capability claim against live source and
  runtime state, such as route config and scheduler history, not the brief or
  design docs. A paused job or unbuilt input is not a present capability; reword
  it or label it staged, and tell the user where copy departs from the brief.
  For outbound product or store links, read the landed page's content: a host
  that serves its home page with 200 for unknown paths hides a missing page.
- Release-console uploads: a platform consumes a version/build identifier once it enters any release draft, so `already used` means attached to a draft elsewhere, not uploaded. Before minting a new identifier or re-dropping the same artifact, read the track's drafts, its artifact library, and sibling tracks read-only to find the owning draft, and add from the library rather than re-uploading. Page metadata can lag processing or drop entries; decode the artifact's own manifest and signature to confirm version, package, and signing identity.
- Configuration or credential-location changes: inspect consumers of the old
  location, including scheduled jobs, before removing it. Preserve unrelated
  native settings; exercise affected consumers with their actual scheduler or
  noninteractive environment, not just the newly working CLI. Do not restore a
  plaintext credential to satisfy a legacy reader; migrate that reader. When
  disabling a platform integration, remove only platform-owned blocks; shared
  settings such as a global git ignore may guard the user's own automation.
  A running GUI app keeps its startup config until relaunched; a CLI turn with
  its bundled binary proves the file, not the live app.
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
