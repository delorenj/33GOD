# Managed execution activation

Implementation and installation are complete; no board is managed yet. The installed
release is `~/.local/share/krebs/releases/2fdd5b8369773327c6b3c815efda50a92d4d5eb9`.
Its descriptor pins the wheel, dependency lock, Pilot and complete Momo bundle.
Database configuration is `op://DeLoSecrets/Krebs Execution/database_url`.

1. Enroll the native 33GOD PM, interactive Codex, interactive Claude and controller
   repair identities in Plane; record only their `op://` key references. JIMB's
   existing George Carlin identity is verified on JIMB but lacks PX feedback access.
   Grant intended board memberships and verify `/api/v1/users/me/` under each key.
2. Populate each canonical `.project.json` execution binding using
   [the contract](execution-contract.md): mode `shadow`, policy version 2, exact
   state UUIDs, working label, PM/operator actor roles, unique native identities,
   runtime IDs, systemd prefixes and PM planner argv. Use the release descriptor's
   Pilot/Momo bundle digests. Derived indexes cannot activate a board.
3. Prove legacy heartbeat, sentinel, n8n dispatch, direct-label and callback fences
   for that board before recording `legacy_writers_fenced: true`. Preserve the
   current disabled reconciliation setting until its intended writer is ready.
4. Run the pinned interpreter with `-m krebs.launch RELEASE_DIR/release.json
   --readiness`. Both canary manifests are in this release; both must pass. A
   different activation cohort requires a new immutable descriptor/release.
5. Review the shadow observations; select managed mode only after the enrollment,
   exact lane, runtime and fence checks pass. Re-run readiness, then enable/start
   `krebs-execution.service` through the user systemd manager.
6. Exercise one controlled canary ticket through claim, start, question/Attention,
   answer/new generation, delivery, independent reviews, QA, documentation and
   Done. Verify Plane readback, actual actor provenance and Candystore receipt.
   Repeat crash/lease recovery before enrolling additional boards.

Rollback pauses managed execution and proves workers stopped before another
writer is allowed. Do not remove enrollment or enable legacy dispatch while a
managed worker can still mutate. Uncertain provider writes remain reconciled by
readback; they are not blindly retried.

The initial inventory has 20 PM roles, 17 enabled, 12 missing canonical project
IDs and zero managed activations. Repair each binding in its owning repository;
do not infer board ownership from a runtime registry alias.
