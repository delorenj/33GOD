# Recovery Implementation Brief — 33GOD-43

Ticket: 33GOD-43 — "Publish schema-validated invocation commands from n8n"
Campaign: board-cranker (33GOD epic, story 1 of 8)
Role: recovery implementer (single WIP item; this is the one live implementation lane)
Repo: bloodbank — isolated worktree ONLY.

## Absolute boundaries

- Work ONLY inside `/tmp/bloodbank-board-cranker-43` (git worktree, branch `fix/issue-43-board-cranker-command-publisher`, base `9de80e24ec0586c68d0c95457941592d973771e1`).
- NEVER touch `/home/delorenj/code/33GOD/bloodbank` (primary checkout), pjangler, or any other repo.
- NEVER push to `main`. Push only the feature branch to `origin`.
- NEVER disable, skip, or fabricate tests/evidence. Real gate output only.
- Do not commit until every gate passes.

## Prior state (from the stopped earlier worker)

A previous worker left a partial UNCOMMITTED diff. Inspect every hunk before continuing; keep what is correct, fix what is wrong, complete what is missing.

Changed files (verified against worktree):
- M `integrations/n8n-nodes-bloodbank/codegen/generate-events.mjs`
- M `integrations/n8n-nodes-bloodbank/package-lock.json`
- M `integrations/n8n-nodes-bloodbank/package.json`
- M `integrations/n8n-nodes-bloodbank/src/index.ts`
- M `integrations/n8n-nodes-bloodbank/src/nats.ts`
- M `integrations/n8n-nodes-bloodbank/src/nodes/Bloodbank/eventSchemas.ts` (generated — must only change via codegen)
- M `integrations/n8n-nodes-bloodbank/test/nats-contract.test.cjs`
- M `schemas/bloodbank/agent/invocation.start.json`
- ?? `integrations/n8n-nodes-bloodbank/src/registry.ts` (untracked)
- ?? `integrations/n8n-nodes-bloodbank/test/publisher-node.test.cjs` (untracked)

Prior RED/GREEN logs: none were verified by the controller. You MUST produce fresh RED→GREEN evidence yourself (instructions below).

## Acceptance criteria (all five required)

1. The canonical invocation schema requires a non-empty prompt and target, validates the complete command envelope, and preserves `bloodbank.agent.invocation.start` plus `bloodbank.cmd.agent.invocation.start` without a version token.
2. Explicit command mode emits command identity, target-scoped stable idempotency, single-consumer delivery, correlation, causation, schema references, and the canonical command subject; malformed input fails before transport.
3. Repository routing reads the canonical fleet registry, resolves exactly one enabled fleet target, and fails closed for absent, disabled, mismatched, or ambiguous routes without workflow-embedded profile names.
4. Event mode remains backward compatible and generated files are changed through code generation only.
5. Strict RED→GREEN evidence covers the positive path, malformed envelope/data fields, kind/schema mismatches, extension overwrite attempts, zero-publish failures, and unchanged event behavior.

## RED→GREEN evidence (mandatory)

Save all logs under `/tmp/bloodbank-board-cranker-43/.evidence/`:

1. RED for the new/changed tests: `git stash -u` in the worktree → run the new tests (`npm test` in `integrations/n8n-nodes-bloodbank`) → capture failing output to `.evidence/red-tests.log` → `git stash pop`.
2. GREEN: run the same tests with the implementation applied → capture passing output to `.evidence/green-tests.log`.
3. If a test cannot be made to fail against the base (e.g. file did not exist), capture the equivalent RED (compile/import error or missing-behavior failure) and explain it in the handback.

## Gates (run in order, capture full output under `.evidence/`)

1. `cd /tmp/bloodbank-board-cranker-43/integrations/n8n-nodes-bloodbank && npm test` → `.evidence/gate1-npm-test.log`
2. `cd /tmp/bloodbank-board-cranker-43 && mise run smoketest:schemas` → `.evidence/gate2-smoketest-schemas.log`
3. `cd /tmp/bloodbank-board-cranker-43 && mise run smoketest:command` → `.evidence/gate3-smoketest-command.log`
4. `cd /tmp/bloodbank-board-cranker-43 && python3 -m pytest services/hermes-gateway/tests -q` → `.evidence/gate4-gateway-tests.log`

All four must exit 0. If a gate fails, fix and re-run the failed gate plus any dependent gate. Do not proceed to commit with a failing gate.

## Completion contract

1. Commit ALL changes on the current branch:
   `git add -A && git commit -m "bloodbank: add schema-validated n8n command publishing"`
2. Push: `git push -u origin fix/issue-43-board-cranker-command-publisher`
3. Write machine-readable handback to:
   `/home/delorenj/code/33GOD/_bmad-output/implementation-artifacts/handback/33GOD-43.handback.json`
   Shape: `{"schema_version":"1.0","issue":"33GOD-43","repo_slug":"bloodbank","status":"DONE"|"DONE_WITH_CONCERNS"|"BLOCKED","summary":"...","checks":{"tests_passed":true,"lint_passed":bool,"type_check_passed":bool|null,"mutation_check_passed":bool},"git":{"branch":"fix/issue-43-board-cranker-command-publisher","base_sha":"9de80e24ec0586c68d0c95457941592d973771e1","head_sha":"<post-commit sha>"},"worker":{"agent_id":"codex-33god-43-recovery","pid":<pid>,"host":"big-chungus"},"evidence":["/tmp/bloodbank-board-cranker-43/.evidence/red-tests.log","/tmp/bloodbank-board-cranker-43/.evidence/green-tests.log",<gate logs>],"test_log":"<path to green log>","findings":[],"meta":{"recovery":true,"prior_worker_stopped":true}}`
4. Final message: report status, head SHA, and gate results in under 10 lines.

## Time budget

Target under 90 minutes. If you are BLOCKED (gate cannot pass, missing external dependency, ambiguity in ACs), stop, write the handback with status BLOCKED and exact evidence, and end — do not loop.
