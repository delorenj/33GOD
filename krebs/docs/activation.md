# Managed execution activation

Implementation and installation are complete; no board is managed yet. The installed
release is `~/.local/share/krebs/releases/2fdd5b8369773327c6b3c815efda50a92d4d5eb9`.
Its descriptor pins the wheel, dependency lock, Pilot and complete Momo bundle.
Database configuration is `op://DeLoSecrets/Krebs Execution/database_url`.

1. Complete the verified PM enrollments below, then select interactive/controller
   Plane identities. Model-provider OAuth through NewAPI is a separate binding;
   it does not currently authenticate a Plane/Krebs actor.
   - James Brennan PM: George Carlin,
     `op://DeLoSecrets/Plane/API Keys - Agent Roster/George Carlin`, native ID
     `2d34d5ca-2433-478f-8132-ccb99cec714a`. Native identity and JIMB membership
     pass. PX feedback membership remains missing.
   - 33GOD PM: Grolf,
     `op://DeLoSecrets/Plane/API Keys - Agent Roster/Grolf`, native ID
     `62b4fef6-b0fe-4cd2-bcd7-53737a61feb4`. Native identity passes; bootstrap
     operator membership readback finds no membership on 33GOD or PX. Grolf's
     member/state/label/issue requests return 403 despite project detail reads
     succeeding. Add the intended project memberships before readiness.
   - Interactive Codex/Claude/Kimi: use `api.automaticai.io` for the requested
     model-provider OAuth path. The inspected NewAPI relay validates NewAPI
     tokens, and its Claude follower copies the upstream OAuth access token;
     no Plane/Krebs actor bridge was found. Keep these model credentials
     separate from Plane attribution and enroll distinct native Plane actors
     for Codex, Claude and Kimi when their ticket access is needed.
   - Controller repairs: native Plane actor/key reference is still unspecified.
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
