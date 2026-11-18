# Button-up, big-chungus side (2026-11-17)

Lane C. Items 1, 3, 4, 5. Item 2 is in `W0-3-reboot-2026-11-14.md`. Nothing here is committed by the lane; the orchestrator commits.

Belsky level: the asker is the Jev key cleanup on one host; the level is every Jev caller and every host that follows the typesafe-ai recipe, which now resolve the key from 1Password by reference and have no plaintext copy to copy.

## 1. Jev key files shredded

Checked with `OP_CACHE=off op read`, sha256 prefixes only, no value printed.

| File on big-chungus | Vault item | Match |
|---|---|---|
| `~/.config/jev-clairic/typesafe.key` (40 B) | `op://DeLoSecrets/olonpzrcmxdx52vhoib3uyfzdi/credential` ("Jev LiteLLM ingress master key") | equal; file sha `2cc31ac430d92867` = vault value plus trailing newline; trimmed `a48718b72faff764` = vault value |
| `~/.config/jev-clairic/typesafe.key.direct.bak` (107 B) | `op://DeLoSecrets/ol3fqfppauwvsos5zz5dumyvoi/credential` ("Jev") | equal, `b9efdc7f342598ef` both sides |

Readers: `rg -F typesafe.key` over `~/.agents`, `~/code/infra`, `~/.config`, `~/.local/bin`, `~/code/33GOD`, `~/docker`, `~/.config/systemd`, `~/code/client-portal`, plus `lsof`. Live code reads nothing. The `jev-*` wrappers go through `jev-env.sh` and `jev-secrets` (`JEV_API_KEY_REF` in `~/.config/33god/host.env`, set to the ingress item above). Remaining hits are prose only: `~/.config/33god/host.env` comment, `~/.agents/fix.log` (old log lines), `test_host_overlay.py` (asserts the string is absent), planning docs and prior evidence, and two skill/compose comments fixed below.

Done: `shred -u` on both, rc 0, directory now empty (`~/.config/jev-clairic/` left in place).

Recipe fixes (repos are Jarad's own):

- `~/code/skillex/all-skills/typesafe-ai/SKILL.md`: fleet wiring, Verify probe and break-glass probe now use `JEV_API_KEY_REF` / `op read` by UUID, say never to write the key to disk, and note the shred. The title ref `op://DeLoSecrets/Jev/credential` became the UUID ref. I ran the new Verify snippet through the ingress: `{'ok': {'type': 'noul', 'noul': 0.96}}`.
  - all-skills commit `ae0335a`, pushed; skillex pointer bump `a80fda2`, pushed.
- `~/docker/stacks/ai/jev-litellm/compose.yml:29`: comment no longer names the file. docker commit `ea4f771`, pushed.

## 3. PJAN-213 (pjangler registry pg pool crash)

Ticket: **PJAN-213** https://plane.delo.sh/33god/browse/PJAN-213/ (Backlog, medium, label bug, idempotency key `pjangler-registry-pg-pool-error-2026-11-17`). Filed with `px task create` from `~/code/33GOD/pjangler`. Not implemented.

Cited code (pjangler main `8d00d67`):

- `src/project/registryService.ts:50`: `new Pool({ database, connectionTimeoutMillis: 5000, statement_timeout: 15000 })`, no `pool.on('error')`. This is the registry's pool.
- `src/project/RegistryStore.ts:116`: second `new Pool(...)` in `PgRegistryStore`, same gap.
- `rg "pool.on|\.on\('error'|uncaughtException"` finds no pool or process-level error handler in `src`.

Proof of the crash, Damian's Mac `~/infra/pjangler-registry/logs/registry.err`: `Unhandled 'error' event ... error: terminating connection due to administrator command ... Emitted 'error' event on BoundPool instance at Client.idleListener (pg-pool/index.js:62)`, then `Connection terminated unexpectedly`, then repeated `connect ECONNREFUSED 127.0.0.1:18765` until Postgres returned. KeepAlive recovered it (service up at 20:29:08 on 11-14).

Fix in the ticket: `pool.on('error', ...)` after each Pool (log, do not exit); retry with backoff around `index.initialize()` at `registryService.ts:52` so cold boot waits for PG; optional `keepAlive: true`; unit test that `pool.emit('error', ...)` does not throw. Repro steps are in the ticket.

## 4. Gateway token 68 (`aai:damien`), read-only

Via `ops/gateway-tokens.py status damien --json` and a read-only SQL session (`default_transaction_read_only=on`) through `aai.psql`. Nothing revoked or changed.

- Token 68: name `aai:damien:1791293532132213684`, status 1 (enabled), group `aai-personal`, user_id 5, never expires, unlimited quota, 13 model routes. Created 2026-10-06 13:32:12 UTC.
- `tokens.accessed_time`: 2026-10-06 13:32:12 UTC, equal to creation, so that field was never advanced; do not trust it as last-used.
- `logs` by `token_id=68`: 866 requests ever, last at **2026-10-06 17:58:01 UTC**.
- Last 30 days (to 2026-11-18 00:19 UTC): **0 requests**. No daily buckets, no models.
- Context: `damien-*` tokens are the live ones. `aai:damien-personal` (113) last accessed 2026-11-17 03:11, `-hindsight` (129) 2026-11-12, probes 134/136/137 on 2026-11-14. Their combined requests in 30 days by name match: 350, last 2026-11-17 22:54 UTC.
- Reading: token 68 has been idle for 42 days and was superseded by the `damien-*` tokens. It is a safe revoke candidate, but it is an owner call; not done.

## 5. Daily report: config, delivery, receipts

Config: `~/.config/delonet-daily-report/report.json` validates (`reportctl validate`: `valid: true`, version 2, 5 sections, required `dev-activity` and `report-delivery`).

Dates. The report for day D is generated at 06:00 EST on D+1. So "2026-11-16 and 2026-11-17" below means the two mornings, reports for 11-15 and 11-16. The 11-17 report is not due until 11-18 06:00 (`reportctl verify --date 2026-11-17` says no published report, which is correct today).

`reportctl verify`:
- 11-16 report: ok, coherent, status `partial`, no required failures. `dev-activity` is partial: "event pagination stopped at the 50-page budget (50000 events read)". All other sections complete.

Delivery receipts (`artifacts/<date>/deliveries.json`, `--once` ledger), one successful receipt per target:

| Morning | Report | vault | slack digest | s3 |
|---|---|---|---|---|
| 2026-11-16 | 11-15, gen `09f4c763...` | 11:03:36Z | 11:03:36Z id `01a1e406-d8e1-...` | 11:03:36Z |
| 2026-11-17 | 11-16, gen `099e48f7...` | 11:04:23Z | 11:04:24Z id `01a1e92d-eeed-...` | 11:04:24Z |

Resend (read-only `GET /emails`, key from the vault, nothing printed). The slack target is an email to the channel's Slack address through Resend, `last_event: delivered`:

- 2026-11-16: exactly one `Dev Journal — 2026-11-15 [partial]` to the dev-journal Slack address (`01a1e406-d8e1-...`, 11:03:36Z).
- 2026-11-17: exactly one `Dev Journal — 2026-11-16 [partial]` to the Slack address (`01a1e92d-eeed-...`, 11:04:24Z).
- Result: the digest went out **once per day** on both mornings, and no 06:15 `ensure` duplicate exists. The last duplicate at 11:15Z was 2026-11-15 (report 11-14, `01a1deea-ed6a-...`), before `DDR_DELIVER_ONCE=1` took effect.
- Other mail those days is a different flow, not the Slack digest: one `Dev Journal — D` (processing pending) to the owner at about 11:05 to 11:07Z, `Updated: Dev Journal — 2026-11-16` at 14:07Z on 11-17, and one `[complete]` mail to a second recipient at about 11:00Z.

Findings to carry (not changed):
1. `dev-journal-reconcile.service` fails every tick (exit 3). It scans 28 old dates from 2026-09-24 on; those reports and manifests fail validation (`DailyReport sections must be exactly [...]`, `RunManifest must cover enabled sections exactly once`). This is old-schema archive data, unrelated to the 11-16 report, but the unit is permanently red.
2. The `dev-activity` 50-page cap truncates busy days (11-16, 50000 events). The report says so honestly; raising the page budget would fix it.
3. Nightly and ensure runs left no journal lines in the user journal for 05:58 to 06:20; the receipts and Resend log are the proof of delivery.

## Not done

Nothing in the lane was refused. Token 68 is not revoked (read-only by instruction). No evidence file or other file here was committed.
- token 68 aai:damien revoked 2026-11-17 by orchestrator after lane C showed 0 requests in 30 days (last 2026-10-06); damien-personal (113) and damien-hindsight (129) still status 1.
