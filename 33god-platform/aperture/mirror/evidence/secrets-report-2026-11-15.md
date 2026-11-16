# Secrets + report lane, 2026-11-15 (Damian's Mac Studio and big-chungus)

**Executor:** aai (big-chungus, ssh to `hellosubconscious@100.117.109.60`). **Authority:** Jarad, untagged, 2026-11-15: "address all of the remaining things dangling, just optimize it for Damian, button it up" (Aperture charter section 3 rule 8: session explicitly handed over). **Scope:** PLAN.md W9-2 owner asks 1 and 3, W9-4/W9-5, and the clients-2026-11-15 item 5.

No secret value was printed, logged, committed or put in argv. Below: paths, key names, refs, ids, lengths and 8-char hashes.

## Outcome

| # | Item | Result |
|---|---|---|
| 1 | Damian gets a sending-only Resend key, swapped in, proven | **DONE.** |
| 2 | big-chungus Slack digest sent twice daily | **DONE** (`DDR_DELIVER_ONCE=1`), plus an **incident found and repaired** (section 2b). |
| 3 | Mac `~/.zshrc` plaintext `CLAUDE_CODE_OAUTH_TOKEN` | **DONE.** Removed from zshrc, kept unexported in the 0600 store. `claude -p` works through the gateway, `clients-check.py` 14 PASS / 0 FAIL / 1 N/A. |
| 4 | W9-5 jev-rollup on the Mac, scheduled on his Candybar | **DONE.** Terminal run, five scheduled fires and the hourly `roll` observed (section 5); only the 06:0x `day` compose awaits 2026-11-16. Needs no Jev key. |

## 1. Resend: Damian's own sending-only key

- Minted with Jarad's Resend key (`POST /api-keys`, `permission: sending_access`, `domain_id` = the verified `delo.sh` domain `fa339c16-e132-455f-81bb-eaeee8f3d9af`). Resend key id `559907bf-97c7-411e-8d67-fd77583be774`, name `damian-mac-studio-dev-journal`. Revoke: `DELETE /api-keys/559907bf-97c7-411e-8d67-fd77583be774`. Jarad's own key (`Main`, `22c682a8...`) untouched.
- 1Password: new DeLoSecrets item **`aruipintqwszqmjiuw46atthou`** ("Resend API Key - Damian Mac Studio dev-journal (sending-only, delo.sh)", field `credential`). `op read` round-trip equals the minted token. The temp file holding the token on big-chungus was shredded.
- Mac: `secrets.env` line `OP_DELOSECRETS_ARUIPINTQWSZQMJIUW46ATTHOU_CREDENTIAL` plus its `refmap.tsv` row **replaced** the old full-access line and row (`...WULYIISB24EHT3WKND6YNF2NYY_CREDENTIAL`, now gone from all three files). `host.env` `RESEND_API_KEY_REF` now `op://DeLoSecrets/aruipintqwszqmjiuw46atthou/credential`. All three files 0600 after an atomic flock-guarded write. Backup before: `~/.config/33god/config-backups/20261116T020642Z-resend/` (pointer `LATEST-resend`).
- Proof, on the Mac, through the real resolution path:
  - `env-op-resolve exec` then `GET /domains` and `GET /api-keys`: **HTTP 401 `restricted_api_key`: "This API key is restricted to only send emails"** (valid, and restricted).
  - the report's own `distribute.resend_api_key()` resolves a 36-char key whose sha256 prefix `fa980950` equals the minted key's, and the same `GET /domains` returns the same 401.
  - `reportctl validate` valid; `distribute --date 2026-11-14 --dry-run --once` ok, email target `already_delivered` (receipt from W9-2 intact). No email sent.
- Not proven, said plainly: that the key is *domain-scoped* beyond what the creation call accepted (`domain_id`). A send from a non-`delo.sh` domain was not attempted because Resend validates the `to` field first (both of my probes returned 422 validation, nothing sent). The real send is tomorrow's 06:00 run.
- Jarad's key was not revoked.

## 2. big-chungus: Slack digest twice a day

**Live invokers** (found, not assumed): Candybar `dev-journal-nightly` (06:00, exec `infra/scripts/dev-journal-hermes-nightly.sh`) and `dev-journal-ensure-nightly` (06:15, systemd `dev-journal-ensure-nightly.service`). Both shims exec the skill's `nightly.sh`, which reads `DDR_DELIVER_ONCE` from the host overlay. So the right place is `~/.config/33god/host.env`, not a manifest or unit env (an env on one would have missed the other).

- Appended `DDR_DELIVER_ONCE=1` to `~/.config/33god/host.env` (0600, not a repo, no re-registration needed). `hostsettings.py get DDR_DELIVER_ONCE` returns `1`.
- Installed skill is `2e2928d` (`--once`), same code the Mac runs.
- Dry run on the real config: `distribute --date 2026-11-14 --dry-run --once` lists vault, slack and s3 each as "would" exactly once.
- Single delivery shown for real in a sandbox (copy of the 2026-11-14 artifact and archive, vault target only, nothing of Jarad's): `distribute --once` #1 -> `delivered ['vault']`; #2 (the 06:15 shape) -> `delivered [] already_delivered ['vault']`. Sandbox deleted. (A true Slack double-send test would send mail to Jarad's workspace; the receipts logic is the same code path.)
- First real confirmation is tomorrow: Resend should show one Slack digest for 2026-11-15, not two.
- No commit: `host.env` is host-owned and outside any repo by design.

### 2b. INCIDENT, found and repaired: big-chungus `report.json` was overwritten with Damian's config

While reading the live config I found `~/.config/delonet-daily-report/report.json` (mtime 2026-11-15 13:31) **was Damian's Mac config followed by a stray shell tail** (`EOF`, `chmod 600 ~/.config/33god/host.env`, `ls -la ...`, `json-ok`), i.e. a heredoc intended for the Mac was run locally. `reportctl validate` failed with `Extra data: line 79`. Consequence if left: tomorrow's 06:00 `dev-journal-nightly` and 06:15 ensure would have exited 2 on Jarad's real Dev Journal, and the Slack/vault/s3 delivery would have stopped. It happened after today's 06:00 run, so no delivery was missed yet.

Repair: Jarad's config was reconstructed **verbatim** from the `cat -n` of the file in a 2026-11-08 Hermes request dump (`~/.hermes/profiles/infra-pm/sessions/request_dump_20261108_095024_...json`), then checked against the 2026-11-14 run: 10 project roots (the run's `git_roots_configured: 10`), the 5 sections (`dev-activity`, `fleet-health`, `pr-maintenance`, `report-delivery`, `turn-facts`), `anthropic/claude-opus-5` as narrator (the published `report.md` line 2), vault + s3 + slack enabled, email off. After: `reportctl validate` valid (5 sections, 10 roots), `verify --date 2026-11-14` coherent, dry-run distribute as above. **Caveat:** it is the 2026-11-08 text; if Jarad changed the config between 11-08 and 11-15 13:31 those edits are lost (nothing in the 11-14 run contradicts it). Damian's own Mac config was not affected. No `.bak` left beside it.

## 3. Mac `~/.zshrc` plaintext OAuth token

- **Whose:** Damian's own. It is an `sk-ant-oat01-` Claude Code `setup-token` (108 chars); `~/.claude.json` on the Mac is `damian@hellosubconscious.com` (Damian Miller, Stripe subscription); the zshrc line predates all aperture work (file mtime 2026-05-30). The profile endpoint returns 403 for a setup-token (inference-only scope), so ownership is inferred from those three facts, not from an identity API.
- **Conflict:** it was dead, not harmful, today: `apiKeyHelper` (gateway token) outranks it, `clients-check.py` and a live `claude -p` both report the gateway. It was a standing hazard: a plaintext credential, and the silent fallback that would send Damian's traffic direct to Anthropic, invisible to the gateway ledger, if the helper ever failed.
- **Change:** the `export` line is replaced by a two-line comment in `~/.zshrc` (a fresh `zsh -ic` has no `CLAUDE_CODE_OAUTH_TOKEN`). The value is kept, **unexported**, in `secrets.env` as `OP_DAMIANLOCAL_CLAUDE_CODE_OAUTH_TOKEN_CREDENTIAL` with refmap row `op://DamianLocal/claude-code-oauth-token/credential` (Damian's own namespace, like `plane-pilot`; forward ref, no vault item; deliberately **not** copied into Jarad's DeLoSecrets because it is Damian's subscription credential). Not sourced from zshrc: sourcing it would have re-exported it and kept the hazard. Resolver round-trip: the new ref resolves to a 108-char value.
- Backup before: `~/.config/33god/config-backups/20261116T021149Z-zshrc/` (`zshrc.redacted` = the old zshrc with the token replaced by a placeholder, so no second plaintext copy; `secrets.env`, `refmap.tsv`; pointer `LATEST-zshrc`). Restoring the line = `export CLAUDE_CODE_OAUTH_TOKEN=$(env-op-resolve ...)` from the stored key.
- Verified: `zsh -lic 'claude -p --output-format json "Reply with exactly: DAMIAN-LANE-OK"'` -> `DAMIAN-LANE-OK`, `is_error: False`, model `automaticai/auto/orchestrator` (his lane). `clients-check.py` (static, on the Mac): **14 PASS, 0 FAIL, 1 N/A** (Claude Desktop not installed), same as the 2026-11-15 baseline.

## 4. W9-5: jev-rollup on the Mac

**Finding that removes the blocker:** `jev-rollup` is bus-fed (README: "`jev-rollup-run` resolves no credential at all"). It reads Candystore `turn.annotated` events and joins reply text from `turn.completed`. The Jev key is not on this path, so none was needed. Damian's `damian-studio` Jev key stays untouched in the store for the extractor tools, which are out of scope.

**The private repo problem, solved without a new permission:** the Mac's `~/.agents` is a `delorenj/agents` checkout but it is stale (pre-W9-1, no host overlay), dirty, and cannot fetch ("Repository not found": the Mac has no access, by design). It was not touched. Instead the five files the sidecar needs were **vendored byte-for-byte** into the public `delorenj/candybar` repo, `deploy/mac/jev-rollup/`, commit **`19b46f6`** on `main` (next to the other Mac manifests): `jev-rollup`, `jev-rollup-run`, `jev-env.sh`, `jev_hostenv.py` (from agents `tools/jev-clairic/bin`), `jev-rollup-cadence.sh` (from `hermes/`), all from agents commit `85b9498` (W9-1). `VENDORED.sha256` pins the bytes; `install.sh` refuses to run on a mismatch. No crank tooling, no `jev-secrets`, no key plumbing was vendored. **No new GitHub permission was granted.** Drift risk: this is a copy; re-vendor when `jev-rollup` changes (README says how).

- Install (Mac): `install.sh` copied the five files to `~/.local/share/33god/jev-rollup/` and linked `jev-rollup` and `jev-rollup-run` into `~/.local/bin`. Runs under the Mac's stock `/usr/bin/python3` 3.9.6.
- Manifest: `mac-jev-rollup`, `*/10 * * * *`, `America/New_York`, exec runner (`TZ` and `PATH` pinned; the cadence decides tick/roll/day from the wall clock). Missed-fire policy at the top of the manifest: coalesce (AD-6); a tick is cursor-based so a missed fire loses nothing; a missed `day` is `jev-rollup-run day` by hand. No `on_failure` (Damian has no alert destination; ntfy is W10-1).
- Registration read back from the Mac's Candybar API: id `01a1e223-58c2-7004-aa6e-73ce07198228`, schedule, timezone, tags and runner as committed; created disabled, `candybar resume` -> `state enabled`.
- Terminal invocation: `candybar run mac-jev-rollup --wait` -> invocation `2dab776b-d8a4-493b-a633-ced7d1dd45b2`, `success`, exit 0, 345 ms. Effect: cursor written (`feed: annotated`, from the Mac Candystore's latest annotated event) and an inbox of 2 project files (`hellosubconscious.md`, `unattributed.md`, 309 B) from real Mac turns.
- No rollup email exists (the sidecar writes files), so the "fold into the morning report / at most one send" branch did not apply. No email was sent.
- Clocks: Mac crontab still 15 lines, 33 LaunchAgents; `doctor --live` does not mention jev-rollup. No cron, launchd or timer was added.
- Scheduled observation: section 5.

## 5. First scheduled run

Observed on the Mac (`candybar history mac-jev-rollup -n 8`): five `trigger=scheduled`, `success` rows at 21:20, 21:30, 21:40, 21:50 and **22:00** (108 to 159 ms each), after the manual 21:15 run. The 22:00 fire is the first with minute < 10, so the cadence ran `roll` as well: the inbox went from 2 files to **0** and the rollup artifact exists, `~/.local/state/jev-rollup/rollups/2026-11-15/{hellosubconscious.md,unattributed.md}` (`jev-rollup-run status`: `rollup days: ['2026-11-15']`). Content is real Mac turns (a Hermes headline about the missing report-delivery history, and the Codex Desktop gateway probe). No plaintext key file exists or was created (the path reads none).

Not yet observed: the 06:00-06:09 `day` step (composes `DAY.md` for 2026-11-15); first chance is 2026-11-16 06:00. `ls ~/.local/state/jev-rollup/rollups/2026-11-15/DAY.md` after it. Cost reads `unmeasured` until Candybar aggregates (144 runs/day at about 0.1 s each).

## Asks / not done

1. **Output location (Damian's decision):** rollups go to `~/.local/state/jev-rollup/rollups/<date>/<project>.md` (+ `DAY.md`), not into his Obsidian vault (`~/code/HSub`), because the vault mapping is an open owner decision (PLAN section 5, W10-2) and a launchd job writing under `~/Documents` would hit macOS TCC. One line in `~/.config/33god/host.env`, `JEV_ROLLUP_DIR=...`, redirects it.
2. **Check tomorrow after 06:00** (unchanged from W9-4): `candybar history mac-dev-journal-nightly -n 5` for the first `trigger=scheduled` row and the second email, now sent with the restricted key. If it fails with `restricted_api_key` on send, the key lacks `delo.sh` send permission: re-mint without `domain_id`.
3. **Jarad:** confirm one Slack digest (not two) for 2026-11-15 in Resend; confirm the restored `report.json` has no 11-08 -> 11-15 edits missing (section 2b).
4. **Hygiene, not done:** the W9-2 agent's stray local heredoc is the cause of 2b; nothing guards `report.json` against a clobber. A `reportctl validate` in the nightly shim's first line would have failed loudly instead of silently on the next run (it does already exit 2, so the failure is loud, but only at 06:00).
5. Damian should decide whether to keep the old OAuth token (`OP_DAMIANLOCAL_CLAUDE_CODE_OAUTH_TOKEN_CREDENTIAL`) or revoke it at claude.ai; it is his credential and I did not revoke it.
