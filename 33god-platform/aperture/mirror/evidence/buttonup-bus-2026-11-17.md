# Button-up, lane A: Mac bus and repo (2026-11-17)

Run from big-chungus against `hellosubconscious@100.117.109.60` (colima docker via `DOCKER_HOST`). Times are UTC, 2026-11-18 00:1x to 00:2x. Mac repo pins at start: 33GOD `c316a97`, bloodbank `bfe2a1e`, candystore `e13b70a`, candybar clone `7d8fa50`. No secret value was printed. Damian's own services were not touched.

## 1. Turn-enricher rebuilt and redeployed

Note on the commit named in the task: `e147afb` is a commit in the 33GOD parent repo. It changes `33god-platform/enricher` (the embeddings enricher, `enricher-daprd`) and waybill. It does not touch bloodbank and it does not touch the turn-enricher. The Mac does not run that service. So the rebuild below carries only the bloodbank delta.

What changed in the turn-enricher build context since the running image (`6b2a2bf`): `services/turn-enricher/main.py` is unchanged (sha256 `b43766222d51...` before and after). `services/agent-hooks/core` changed in 4 files (asm.lua, asm.py, sweep.py, validate.py; validate.py adds the `genesis` domain, `harvest` entity and `published`/`publish` actions). Small, but it is in the image.

Recipe followed (W8-3 section 3.1 and the header of `mac/compose.enricher.yaml`):

```
git -C ~/code/33GOD/bloodbank archive bfe2a1e services/turn-enricher services/agent-hooks/core | tar -x -C ~/.local/share/33god/turn-enricher/src
   (old src/services/turn-enricher and src/services/agent-hooks removed first)
cd ~/.local/share/33god/turn-enricher/src/services
docker build --platform linux/arm64 --pull=false -t turn-enricher:mac-bfe2a1e -f turn-enricher/Dockerfile .
   -> sha256:b8d1b92da2bc6f92922160ce4d62d8074eb55661bf67592f3b80c25297464089  arm64  user=appuser
```

Source check, tree vs `git show bfe2a1e:<path>` (first 16 hex): main.py `b43766222d511686` OK, core/validate.py `70890d41ab155cd0` OK, core/envelope.py `578d5d944930a551` OK.

Compose: image line changed to `turn-enricher:mac-bfe2a1e@sha256:b8d1b92d...`, header comment updated, mode 0600. The Mac copy and the repo copy `mac/compose.enricher.yaml` have the same sha256 (`f238b91b02e9...`). The repo copy is edited but not committed.

Deploy:

```
env-op-resolve exec --env-file enricher.env.op -- docker compose -p 33god-enricher -f compose.enricher.yaml up -d
 Container bloodbank-turn-enricher Recreate / Recreated / Starting / Started
started=2026-11-18T00:21:24Z status=running restarts=0 cfgimage=turn-enricher:mac-bfe2a1e@sha256:b8d1b92d...
00:21:24,274 WARNING clairic DISABLED (CLAIRIC_ENABLED=false) ... extractors={'jev': 'jev-latest'}
00:21:24,292 INFO nats connected to nats://nats:4222
00:21:24,292 INFO subscribed: bloodbank.evt.conversation.turn.completed
```

The container has no Docker healthcheck (same as W8-3), so "healthy" here means running, restarts 0, NATS connected, subscribed, and no ERROR or Traceback in the log since start (grep count 0).

First attempt at the compose edit used perl and did not change the image line (the `@sha256` interpolated), so `up -d` printed "Running" and recreated nothing. Redone with Python; the table above is the second, real deploy.

Controlled turn (same method as W8-3 section 5; envelope built with `core.envelope.build_envelope` and schema-validated in the hook-hub venv, since system python has no jsonschema; published with `nats pub`):

```
00:22:01Z  Published 1131 bytes to "bloodbank.evt.conversation.turn.completed"   (producer buttonup-probe, text starts BUTTONUP-PROBE)
enricher:  00:22:02,133 INFO annotated: 3660d20f-f07e-481b-8a1f-71f239d68538 signal=0.970 action=None artifacts=0 blocker=None
Candystore (127.0.0.1:8683, correlationid 2e30b748-53f2-405a-9082-08e1c37f61ad):
  2cea0d81-d583-428d-ba40-f8585e6cbb61  2026-11-18T00:22:02.132Z  producer turn-enricher
  data.target_event_id=3660d20f-...  extractors={"jev": "jev-latest"}  signal 0.97  thread_id buttonup-probe-1794961321
```

Dead letters (psql inside `candystore-postgres`, `select count(*) from dead_letter`): 0 before, 0 after. Annotated rows in Candystore: 43 before, 44 after (the one probe). The two probe rows (turn.completed and turn.annotated, cli `buttonup-probe`) stay in the store; there is no delete API.

Organic annotations were already flowing before this deploy: the old container's log at 00:20 read `annotated=21 noise=22 received=60`, and Candystore holds 17 `turn.annotated` rows from the enricher for codex since 2026-11-16. That closes the W8-3 section 9 gap (no organic annotation observed).

event_embeddings at 0 rows: expected. Evidence:
- Nothing in Candystore writes it. The only `INSERT INTO event_embeddings` is in `33god-platform/enricher/main.py` (line 148), the embeddings enricher, which is a different service from the turn-enricher.
- That service is not deployed on the Mac by design: W8-3 section 2 ("the crash-looping `enricher-daprd` belongs to the other service ... amd64-only and 6.5 GB, and it is not part of W8-3") and finding 1 in section 12; `mac/compose.enricher.yaml` header lines 12-14; PLAN.md per-component table, Dapr row, and the turn-enricher row ("compose, optional consumer").
- W3-1.md line 16 and `W3-1.verify.md` line 25 record the table as present and at 0 rows from day one (`event_embeddings 0`).
- Consequence worth stating: semantic search by meaning has no vectors on the Mac, and e147afb's FK-race and `agent.session.annotated` fixes do not apply there.

Rollback: `docker rm -f bloodbank-turn-enricher`, put the old image line back (`turn-enricher:mac-6b2a2bf@sha256:803143ee...`, the image is still on the Mac) and re-run the same `up -d`.

## 2. Candystore image: no rebuild

Running: `candystore:mac-1ec755a` (started 2026-11-15T01:28Z, restarts 3 as before, healthy). Current pin `e13b70a`, 14 commits after `1ec755a`. The image copies `pyproject.toml`, `candystore/`, `migrations/`, `static/`. Diff of those paths: one file, `candystore/cli.py` (the `candystore context latest` CLI blank `CANDYSTORE_URL` fallback). `main.py`, `ingest.py`, `db.py`, `query.py`, migrations and static are unchanged. The server never runs `cli.py`, so the change does not matter to the container. The other 34 changed files are docs, agents/ desk files and tests. Left as is. `/healthz` 204, `/readyz` 204, events still arriving (37,110 at 00:24Z).

## 3. Hook-hub: notebook handlers disabled

Overlay `~/.config/33god/hook-hub-overlay.toml` (0600) already held one row (`hindsight-jot-flush`, disabled). Syntax from `bloodbank/services/hook-hub/README.md` "Host overlay": a `[[handler]]` row with a matching `id` replaces the base row field by field, so `enabled = false` alone retires it. Existing row kept; two rows appended with a comment, written to a temp file and renamed into place (no backup file left):

```
[[handler]]
id = "project-notebook-start"
enabled = false

[[handler]]
id = "project-notebook-end"
enabled = false
```

Failure evidence before (receipts DB `w2-3-receipts.sqlite3`, executions since 2026-11-16): `project-notebook-start failed notebook_handler_failed_open 109` (last 2026-11-17T03:34Z), `project-notebook-end failed notebook_handler_failed_open 22` (last 19:11Z).

candystore-context, last 24h and since 11-16: no failures. All 117 runs were `skipped handler_binary_missing` and 2 were `skipped not_first_turn`; the last real `failed` is 2026-11-10 and the last `timed_out` is 2026-11-12. So it was left enabled, as instructed. See surprises: it is a silent no-op because `~/.local/bin/candystore` does not exist on the Mac.

Restart: `launchctl kickstart -k gui/501/io.33god.hook-hub` (W2-3 names the `gui/501` domain; `user/501` says the service is not found), rc 0. pid 15297 became 12001 at 00:23:15Z. The restart also loaded the new bloodbank checkout (`bfe2a1e`) into the hub process.

```
/health: state running pid 12001 registry_error None journal_error None transport_error None publish_enabled True
registry: [.../bloodbank/services/hook-hub/handlers.toml, ~/.config/33god/hook-hub-overlay.toml]
/v1/hooks/status: project-notebook-start enabled=False disabled; project-notebook-end enabled=False disabled;
                  hindsight-jot-flush enabled=False disabled; candystore-context enabled=True configured
hub.log: config loaded: 36 handlers, 83 bindings / listening on ...hook-hub.sock / receipt API listening on 127.0.0.1:8685
```

Test hook event: an opencode `session.created` over the Unix socket (`~/.local/state/33god/hook-hub.sock`), from a throwaway git repo (removed after). Opencode `session.created` was chosen because it selects the notebook-start binding but none of the session-end writers. Reply `exit_code 0`, invocation `ffc7e123-76b8-4fe6-9772-753543c7dc2e`:

```
bloodbank-publisher      async  succeeded
hindsight-briefing       sync   skipped  no_briefing_models
candystore-context       sync   skipped  handler_binary_missing
project-notebook-start   sync   skipped  disabled            <- the retired handler no longer runs
code-review-graph-status sync   skipped  repository_not_indexed
bmad-loop-relay          async  skipped  missing_environment
hub-selftest             sync   succeeded
```

Delivery: the publisher's event `a80e5a66-57f9-590f-8f68-0dc0bab7f05b` is in Candystore as `bloodbank.agent.session.started`, cli opencode, `data.session_id buttonup-hook-probe-1794961437`, 00:23:57Z, plus the hub's `hook.updated` observation. BLOODBANK_EVENTS: 35,525 messages, last_seq 37219, last_ts 00:24:00Z, 3 consumers. The first probe (id `4d9a58f8-...`) is also in Candystore.

Counters since the restart: `project-notebook-*` has 0 `failed` rows (only my 2 `skipped disabled` rows), against 131 failures in the 1.5 days before. Organic session traffic during the 1-minute window was too thin to prove the counters keep flat over time; the registry state (`enabled=False`) is the durable proof, the receipts are the spot check.

The first probe, run with cwd inside `~/code/33GOD/bloodbank`, showed `hindsight-briefing`, `candystore-context` and `code-review-graph-status` as `failed nonzero_exit`. Cause: `~/code/33GOD/bloodbank/.mise.toml` is not trusted on the Mac, so the mise `python3` shim exits 1 whenever a handler runs with that directory as cwd. Reproduced by hand (`mise ERROR ... not trusted. Trust them with mise trust`). It is a probe artifact, not a regression from the overlay. I did not run `mise trust` (Damian's host config, not asked).

Rollback: delete the two appended rows (and their comment) from the overlay; the hub hot-reloads on mtime, or `launchctl kickstart -k gui/501/io.33god.hook-hub`.

## 4. Candybar clone GC

`~/code/33GOD/candybar` (plain clone, no alternates, no worktrees, not under `.git/modules`):

- `git fetch origin` then `HEAD = origin/main = 7d8fa5075dc9238e6f3b1b2a6bc21fa54ef8c44f`, `## main...origin/main` clean.
- Local branches: `main` only. Stashes: none. Remote-tracking refs: 7, all equal to `git ls-remote origin` (so none was stale).
- `git for-each-ref --contains 19b46f6` returned nothing, `git rev-list --all | grep 19b46f6` count 0, and `git reflog --all` had no entry for it. So only the object itself kept it alive.
- Before: `git cat-file -t 19b46f6` printed `commit` (it was `feat(deploy/mac): mac-jev-rollup ... vendored from agents 85b9498`, 2026-11-15).

```
git reflog expire --expire=now --all && git gc --prune=now      rc 0
git cat-file -t 19b46f6   -> fatal: Not a valid object name 19b46f6      rc=128
git rev-parse --verify --quiet 19b46f6^{commit}                          rc=1
git fsck --connectivity-only                                             rc 0
git count-objects -vH: count 0, in-pack 3487, packs 1, size-pack 2.27 MiB, garbage 0
HEAD still 7d8fa50 = origin/main, status clean
```

This Mac clone is now clean of the pre-scrub object. Other copies of that object (any other clone, the Mac's old Candybar copy if one exists) are not covered by this step.

## 5. Codex Desktop GUI hooks

Candystore (Mac, 127.0.0.1:8683), codex events since 2026-11-16: 1,136 rows (hook-hub 628, codex-cli 491, turn-enricher 17). Types include 19 `agent.session.started` and 25 `agent.session.ended`.

The Candystore rows do not carry an entrypoint or originator. The only source-like field is `data.payload.source` on `session.started`, and that is the Codex session-start reason: `fork` 15, `resume` 3, `startup` 1. It cannot tell Desktop from CLI. `transcript_path` is null on the ones sampled.

Definitive answer comes from the local rollout headers (`session_meta` line only: id, originator, source, cli_version; read-only on `~/.codex/sessions`). Joined to the 19 Candystore sessions:

| Sessions | originator | source | cli_version |
|---|---|---|---|
| 1 (`01a1e787`, 2026-11-17T03:23Z, repo `code`, startup) | `Codex Desktop` | vscode | 0.169.0-alpha.11.1 |
| 3 (`01a1e64c`, `01a1b691`, `01a1bd58`, resumes) | `codex-tui` | vscode | 0.167.0 / 0.167.1 |
| 15 (all `fork`, repo `space`, 2026-11-16T23:46Z to 11-17T03:34Z) | no local rollout found | n/a | n/a |

So yes: at least one Codex Desktop GUI session reached the bus since 11-16, and at least 3 came from the TUI. No `codex exec` originator appears. The 15 fork sessions (branch `codex/space-station-prd`) cannot be classified: their rollout files are not under `~/.codex/sessions` or `archived_sessions`. The Codex Desktop app is installed (`~/Library/Application Support/Codex`, `~/.codex/app-server-control`), and forks fit Desktop thread forks, but that is inference, not proof. Not changed anything here.

## Surprises and findings

1. `~/.local/bin/candystore` is missing on the Mac. `candystore-context` therefore skips on every session start (117 times since 11-16): agents on the Mac get no cross-session briefing. Installing the CLI (`mise run cli:install` in candystore) would turn it on. Not done; not in this lane's list.
2. `~/code/33GOD/bloodbank/.mise.toml` is untrusted on the Mac. Any agent session whose cwd is that repo has its hook handlers (python3 via the mise shim) exit 1. Probably only bites when work happens inside bloodbank on the Mac.
3. `e147afb` lives in the parent repo and the embeddings enricher, not in bloodbank; the lane description attributed it to bloodbank. No Mac effect.
4. Codex Desktop events cannot be told apart from TUI events in Candystore today, because the hook payload and envelope drop the originator. A one-line addition to the codex hook adapter (copy `originator` from the rollout `session_meta`) would make the question answerable from the store alone.
5. The enricher has no Docker healthcheck, so `docker ps` cannot say "healthy" for it. Adding one would need a compose change and is left alone.

Not committed. Changed outside this file: `mac/compose.enricher.yaml` in this repo (image pin), plus Mac-side compose, overlay, new image tag `mac-bfe2a1e`, Candybar clone gc, hook-hub restart.
