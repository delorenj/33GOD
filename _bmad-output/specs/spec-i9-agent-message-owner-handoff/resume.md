# Exact resume point — I-9 implementation orchestration

## Current driver state — supersedes prior planning-only pause

User-supplied pjangler-pm relay authorizes self-driving ticketed implementation,
owner PM coordination and necessary tickets. Still no merge/push/publication/
production deploy/spend/cap/competing clocks/destructive infra/native unsafe input.
Main is orchestrator only; protect PJAN-198 and all unrelated dirty files.

- **FLUME-76** (`da77ef98-2a08-4451-a32f-ee6ef32c40f4`) is In Progress, sole
  implementer `i9-flume-contract-worker` / `a4c4188dda9afb650`. Owns isolated
  FLUME-76 branch/worktree, finite coordination contract/manifest/local validator,
  no native runtime code. On return: read exact base/head/evidence, launch fresh
  SPEC reviewer; only on PASS launch distinct fresh QUALITY reviewer; fixes go
  back to same implementer. Local commit allowed; no landing/publication.
- **BB-32** fresh validation-only worker `i9-bb32-validation` / `a30b3acee00b41180`
  on existing candidate; do not launch another implementer. Initial literal6379
  poison-endpoint stop corrected to verify actual no-connect guards before safe
  isolated test execution. No production Redis contact/FLUSH permitted.
- **BB-35** existing sole coordinator `green-in-between-9d`, address
  `uds:/run/user/1000/cc-socks/4146616.sock`; original worker
  `a27565613436fcb2e`, reported207 tests, fresh SPEC/QUALITY workflow
  `wf_0a39d164-171`. Source fix separates queued delivery ownership from execution
  slots after thread lock. Exact live delivery mapping still to corroborate.
  Do not duplicate workers/review. Peer activation worker/plans have separate
  authority; this driver does not approve/request deployment/merge/push/restart.
- Original request below unchanged/unresent. **Reconciled 2026-11-09** (see
  "Original request outcome" below): executed once by flume-pm 13:48:40–13:56:46Z
  2026-11-08, actual final reply found. Coordination ACCEPTED; Fleet contract
  adoption BLOCKED; contract ABSENT; capability UNSUPPORTED; G1–G3 NOT RUN.
  No recurring watcher/poll.
- FLUME-76 bb9f560 rooted SPEC: BLOCKED_NOT_REVIEWED (mutation driver denied) with
  executed P1: manifest stale vs this reconciliation (checker exit 1 at :211).
  Currency + regression-decoupling repair routed to the same implementer; fresh
  rooted SPEC then QUALITY on the revised frozen head.

## Original request outcome — reconciled 2026-11-09

Evidence: `/home/delorenj/.claude/tmp/i9-flume-original-request-reconciliation-2026-11-09.json`
(sha256 `d0990398727cadf03ca9657c1652e8b73497f2aef718929dce1cbf55ef53b585`).

- **Transport/execution:** one selected journal row (mode=ro): profile flume-pm,
  state `completed`, outcome `success`, created 2026-11-08T13:48:40.160176Z, updated
  13:56:46.047665Z; no rejection/failure/detach. Terminal events
  `3fe51b58-…` invocation.completed and `d16988b9-…` turn.completed. Candystore
  holds exactly those plus the two started events; none carries reply text.
- **Actual owner reply:** flume-pm session `20261108_084840_86474df2`, final assistant
  message 3949 (finish `stop`, 13:56:45.783575Z, 13879 chars), copied verbatim to
  `/home/delorenj/.claude/tmp/i9-flume-pm-final-reply-2026-11-08.md`
  (sha256 `e779f054f306a7002e1cec6946eea49a10d762917ab63ac7745abcf7c25b5854`).
- **Disposition, kept separate:** coordination receipt **ACCEPTED** (coordination-only,
  no contract ownership/code home); Fleet contract adoption **BLOCKED**; authoritative
  `agent.message` contract **ABSENT**; capability predicate **UNSUPPORTED** as a
  compatibility contract (2.1.319 is a candidate only, zero submit); G1–G3
  **BLOCKED / NOT RUN** with exact unprovable boundaries; next bounded owner result is
  Hermes Fleet's own intake (contract + run manifest, or evidenced unsupported).
- Lifecycle `completed` is execution evidence; the reply is the planning disposition;
  neither is Fleet adoption, API readiness, input enablement or behavioral proof.
  No resend, no exactly-once claim. The 10:14:20Z PENDING snapshot below stays
  historical and true for its instant.

Continue actual workers/gates and readiness as evidence arrives, not another
parent planning cycle. Missing schema/fence/acceptance blocks input only.

## Historical bounded observer and immutable request

As of 2026-11-08T10:14:20Z: original bounded observer expired without a receipt;
no observer remains active or rearmed. Independently ready parent planning is
resolved. At that time only the actual P2 owner response blocked this bounded
refinement turn; that response has since been reconciled (section above). This
does not mean other owners' implementation/identity/proof dependencies are
complete or authorized.

## Immutable request identity — never resend

| Field | Value |
| --- | --- |
| Coordinator | flume-pm / FLUME, coordination-only |
| Contract owner | Hermes Fleet; no code home selected |
| Command | `149134bb-3c88-4ebf-8ecf-98610e054933` |
| Correlation | `f9126f02-14cf-4fae-8a5c-00026336cefa` |
| Envelope | `6da1f331-34cf-4b3d-9991-6c8719735c53` |
| Idempotency | `d4568aa0-5fba-58a4-91b3-510421960016` |
| Thread | `i9-agent-message-planning:f9126f02-14cf-4fae-8a5c-00026336cefa` |
| Subject | `bloodbank.cmd.agent.invocation.start` |
| Stored command | `BLOODBANK_COMMANDS` sequence `160790`, 09:59:07.11897492Z |

The one authorization has been exercised. Do not rerun producer argv, replay,
publish a replacement, contact the target through another lane, or ask for the
coordination designation again. No transport failure has been established.

## Existing observation, not a new clock

- Harness background task `bp5gw1kd3` completed: **observer expired**, output
  `OBSERVATION_TIMEOUT: no terminal receipt; do not resend`. Exit 0 means the
  observer finished, not owner execution/adoption. No observer is running.
- Started `2026-11-08T09:58:53.579009Z`; expired at fixed deadline
  **2026-11-08T10:13:53.579009Z** (900 seconds). Do not extend/rearm or create
  another watcher/recurring polling.
- Script: `/home/delorenj/.claude/tmp/i9-flume-planning-observer.py`.
- Exact correlated events, if any:
  `/home/delorenj/.claude/tmp/i9-flume-planning-events.jsonl`.
- Selected stored-command receipt:
  `/home/delorenj/.claude/tmp/i9-flume-stored-command-receipt.json`.
- Dispatch/publication record:
  `/home/delorenj/.claude/tmp/i9-flume-planning-dispatch.json` and
  `i9-flume-planning-publish-receipt.txt` in the same scratch directory.
- Observer output:
  `/home/delorenj/.claude/tmp/claude-1000/-home-delorenj-code-33GOD-pjangler/c2658124-14f1-4b76-9a7a-cc33b2023fd7/tasks/bp5gw1kd3.output`.

Final scoped snapshot at **10:14:20.883733Z**: no correlated observed events,
selected execution row or matching Candystore events; selected command still
stored with correct IDs/target at seq160790. Durable `bloodbank-hermes-gateway`
delivered stream seq160027 (below 160790), 4 ack pending, 7 pending, 0 waiting;
no consumer API error. Earlier gateway snapshot was active/running, ExecMainStatus 0.
Evidence: `/home/delorenj/.claude/tmp/i9-flume-observer-expiry-evidence.json`.
Verdict at that snapshot: **owner response PENDING; observation expired; command
retained and not yet delivered by this durable**. This was not a concrete
rejection/failed route, adoption or native unsupported result. Batch cause unknown;
no repair authorized. Superseded for current state by the 2026-11-09 reconciliation.

## Resume only when a real later response/evidence or authorized continuation arrives

1. Read only its output and this correlation's events. Check exact command,
   correlation, target and thread. Failure/detach/completion facts are transport/
   execution evidence, not adoption. Detachment is nonterminal.
2. If an actual reply is present, preserve its exact scoped content/provenance;
   separate accepted coordination from Fleet adoption, supported API/capability,
   runnable manifest and unrun G1–G3. A lifecycle `completed` without actual answer
   is not the requested planning disposition. Do not fabricate absent reply text.
3. If required, make **one bounded read-only** selected journal query:
   `/home/delorenj/.hermes/bloodbank-hermes-gateway-state.sqlite3`, opened SQLite
   URI `mode=ro`, table executions WHERE command_id equals the ID above. Select
   only state/profile/outcome/rejection/failure/timestamps and selected terminal
   events. Do not scan unrelated prompts/transcripts or write the journal.
   A similarly scoped Candystore correlation read may corroborate durable facts;
   empty projection alone is not proof of failed execution.
4. Expiry is already recorded: **observer expired, owner response pending**. Change
   that only for actual new response or concrete terminal rejection/failure evidence.
   Preserve IDs and final queue snapshot. Timeout is not no-route, native unsupported,
   refusal, cancellation, adoption or permission to resend. A later reply may arrive.
5. Append actual evidence/disposition to `.memlog.md` through `_bmad/scripts/memlog.py`.
   Re-derive intake/readiness/resume and any affected SPEC/companions. Run readiness
   only, no stories/tracking. Keep separate planning/API/input/behavior verdicts.
6. Update existing bound 33GOD notebook note `note:nhon335tjfxrrtn0j0i5` through
   `pj notebook`, preserve prior material, verify exact readback. No Git publication.

## Resolved independent planning

Coordinator designation, schema/route checks and single publication are complete.
P1 → P2 authority prerequisite is satisfied, not P2 adoption. Fleet G1–G3 versus
Crank C3 cases, incarnation-scoped unknown fencing, dependency graph and exact
catalog proposal are recorded. Current proposal checks passed; features.toml is
unchanged. No independent authorized parent decision remains to manufacture while
waiting. Owner contract absence is not fixed by another parent-only planning cycle.

Boundary remains no boards/code workers/implementation/native proof input/operator
panes/services/restarts/configuration/clocks/spend/model/cap/Git publication/merge/
deploy. Catalog stays proposal. Hub demonstration, scoped FR-6 and full I-8 remain
independent and none is promoted.
