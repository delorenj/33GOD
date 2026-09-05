Daily Developer Report — 2026-08-19
Summary written by anthropic/claude-opus-5. Everything below it is rendered by the pipeline from files it read — every status, metric and caveat is on this page whether or not a model answered.

SUMMARY
-------
**The work was real and heavy — 99 commits, 297 sessions, 21,847 events — but the reporting pipeline meant to tell you about it has been silently failing for a week.**

## What happened

**Intelliforia's admin portal overhaul carried the day.** 65 commits on `design/admin-portal-overhaul`, and the shape of them is a genuine migration rather than churn: `79cba4f7` added the design-system shell, then a run of conversion commits pulled screen after screen onto it — `56cf3e8b` removed 152 jQuery calls, `525d5692` converted 6 screens *and* closed an IDOR, `c47fab0f` closed Phase 5. Several commits are the agent correcting itself in public: `e8183475` "correct two wrong claims in my own commit messages", `cae0644b` "state what the guards cannot prove", `6960b820` "measure the conversion honestly". Browser-level proof landed too (`cbd2a046`, `f6e5f493`). Staging got a real address in `3f5f0a2a` (`stg.delo.sh`).

**Docsidian was designed, not built.** All 9 recorded decisions belong to it and none carry an issue: TypeScript/ESM on Node ≥20 mirroring pjangler; the supervised `docsidian watch` process as the sole automatic trigger; the vault registry at `${XDG_CONFIG_HOME}/docsidian/vaults.toml`; lossless branch-workspace retirement to `.docsidian-archive/`; `.docsidian.toml` as an unsynced control-plane file. Note the contradiction inside the same day's decision log — one decision defers the watch process out of v1, a later one makes it the sole automatic trigger. 14 committing sessions, 1 commit each.

**Pjangler shipped seven releases** (`v1.3.1` → `v1.3.7`, all PJAN-44) mostly to drag CI back to green: Copier as a uv tool (`047f291`), PyYAML for the Hermes profile renderer (`26f3cae`), `9f23385` stopping `migrate` from reporting success it hasn't achieved. PJAN-77 landed the project notebook lifecycle (`a808463`) and its hook-coexistence test in bloodbank (`b741db5`). Elsewhere: james-brennan documented the three AWS accounts and retired Aurora (`e949419`); PoopToTheMoon spiked a headless blob engine at 32 green assertions.

## Needs you

- **Report delivery is degraded.** 5 of 6 due days in 2026-08-13..19 have no valid report. Worse, 6 completion events across 2026-08-16 and 2026-08-17 claimed success against an archive that holds nothing (16) or an invalid schema (17 — sections came back as `executive-brief`/`key-changes`/… instead of the required set). The pipeline lies when it fails.
- **The 06:00 cron is doubled.** `33god-pm.bak` shares a cron dir with `33god-pm`, so `delonet-daily-report` runs twice — a plausible source of the duplicate completion events.
- **`delodocs-triage-second-pass` claims `ok` but is contradicted**: skills `obsidian` and `llm-wiki` are not installed.
- **5 gateway units are not running** (bloodbank-pm, delonet-director, hermes-agent-pm unknown to systemd; delocontainers-pm, skillex-pm inactive), and 8 of 9 heartbeat timers have no next elapse — six last fired 2026-08-07.
- **PR #111 on `mcp-server-trello` is a critical bugfix sitting unmerged** — an unref'd 60s interval causing 294 orphaned processes and 6.5 GB swap over 59 days. Automerge is disabled; it needs a human review click.

## Worth noting

Intelliforia has 16 off-HEAD commits and 12 rebase/cherry-pick duplicates in one day — branch hygiene is drifting. And 21 event-active projects (HeyMa at 3,822 events, deckard at 751) have no configured git root, so none of their code work appears above.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): complete**

21847 events across 27 project(s) on 2026-08-19: 297 session(s), 9 decision(s), 38 committing session(s), 99 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (95 on the checked-out branch, 16 only on other refs); peak 2026-08-19T15:00:00Z (3917 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=38, decision_count=9, event_count=21847, git_commit_count=99, git_commit_replays_collapsed=12, git_commits_off_head=16, git_commits_on_head=95, git_repos_failed=0, git_repos_logged=6, git_repos_missing=0, git_repos_no_commits=3, git_repos_with_off_head_commits=1, git_root_name_collisions=0, git_roots_active_in_events=6, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=True, peak_hour=2026-08-19T15:00:00Z, peak_hour_event_count=3917, project_count=27, projects_without_root=21, session_count=297
Caveats:
  projects truncated: showing 20 of 38
  committing sessions truncated: showing 30 of 38
  operational events truncated: showing 20 of 33
  git scope is 'all-refs': every ref of each configured repository was read for 2026-08-19 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  3 configured project root(s) were read across all refs of each repository and had no commits on 2026-08-19: delonet-company, candystore, holocene
  16 of 111 commit(s) are not reachable from their repository's checked-out branch (unmerged or otherwise off-HEAD work) and are counted here: intelliforia 16 of 65 (checked out: design/admin-portal-overhaul)
  12 commit(s) repeat the author date and subject of another commit in the same window (rebase or cherry-pick copies) and were counted once, not twice: intelliforia 12
  21 project(s) active in events have no configured project root, so no git log was read for them: DeLoContainers, HeyMa, IPM Home Services Ops Relay, PoopFactory, claude-runtime, codex-desktop, deckard, docsidian, and 13 more
Detail:
  === Events by CLI ===
    claude      15903
    codex        5426
    hermes        214
    unknown       157
    copilot       146
    reportctl       1
  
  === Events by project ===
    intelliforia                   7935
    open-notebook                  4678
    HeyMa                          3822
    docsidian                      1096
    33GOD                           987
    pjangler                        871
    deckard                         751
    james-brennan                   664
    unknown                         413
    wax                             139
    PoopToTheMoon                   132
    infra                            87
    relay                            43
    IPM Home Services Ops Relay      42
    slowburns                        32
    intelliforia-mobile              16
    memories                         16
    issue-evidence                   15
    hookprobe                        15
    DeLoContainers.git               14
    ... showing 20 of 38 projects
  
  === Decisions recorded ===
    [docsidian] (no issue): docsidian will be implemented in TypeScript/ESM on Node.js >= 20 with commander for the CLI and vitest for tests, mirroring pjangler.
    [docsidian] (no issue): The supervised per-repo docsidian watch process is deferred out of v1; the manual docsidian sync command is the sole sync trigger.
    [docsidian] (no issue): Docsidian will use one supervised per-repo `docsidian watch` CLI process, enabled by `docsidian init`, as the sole automatic trigger; it will serialize generation-fenced reconciliations from repository, destination, HEAD, and ref events, run full startup and internal recovery scans, install no Git hooks or external timer in v1, and populate an inventoried non-checked-out branch only on first checkout.
    [docsidian] (no issue): Docsidian will leave a merged branch workspace active while its local ref exists and, when disappearance of that ref is observed, losslessly retire each destination's workspace to `\<dest>/\<RepoName>/.docsidian-archive/\<archive-generation>/\<literal-branch>/` with restore metadata, permitting deletion only through an explicit purge command.
    [docsidian] (no issue): Docsidian will store the user-wide managed-vault registry at `${XDG_CONFIG_HOME:-$HOME/.config}/docsidian/vaults.toml`, allow `DOCSIDIAN_REGISTRY` to override that path, and permit only atomic, locked `docsidian vault set` and `docsidian vault remove` operations to mutate it.
    [docsidian] (no issue): `gdrive` will denote a pre-mounted filesystem root and docsidian will transfer through it with the same rsync-based N-way reconciliation used for the local destination, while mounting, authentication, and cloud queue draining remain outside docsidian and an unhealthy mount causes only the Drive leg to fail closed and retry later.
    [docsidian] (no issue): Active workspaces will use literal full Git branch names, the trunk folder will use the resolved trunk branch's actual name, stale prefix workspaces will be retired before materialization, and any branch set that is non-injective under a destination's case or Unicode semantics will cause that destination to fail closed rather than rename or overwrite content.
    [docsidian] (no issue): Docsidian will import a newly authored, path-safe regular file from any destination when its normalized repo-relative path is absent from the last-sync baseline and matches `include − exclude − reserved paths`, writing it immediately only for the checked-out branch and recording it durably for replay on any other branch.
    [docsidian] (no issue): `.docsidian.toml` will remain an unsynced control-plane file that is read only from the repository root and is unconditionally excluded from every transfer and destination import even when an include glob matches it.
  
  === Sessions that committed ===
    open-notebook (codex, 9 turns): 1 commit(s)
    PoopToTheMoon (claude, 19 turns): 1 commit(s)
    PoopToTheMoon (claude, 23 turns): 6 commit(s)
    deckard (claude, 5 turns): 1 commit(s)
    HeyMa (claude, 165 turns): 2 commit(s)
    docsidian (claude, 103 turns): 1 commit(s)
    docsidian (claude, 75 turns): 1 commit(s)
    docsidian (claude, 21 turns): 1 commit(s)
    docsidian (claude, 15 turns): 1 commit(s)
    docsidian (claude, 8 turns): 1 commit(s)
    docsidian (claude, 10 turns): 1 commit(s)
    docsidian (claude, 4 turns): 1 commit(s)
    33GOD (claude, 16 turns): 1 commit(s)
    docsidian (codex, 11 turns): 1 commit(s)
    docsidian (claude, 38 turns): 1 commit(s)
    deckard (claude, 16 turns): 1 commit(s)
    docsidian (claude, 24 turns): 1 commit(s)
    docsidian (claude, 35 turns): 1 commit(s)
    intelliforia (claude, 30 turns): 2 commit(s)
    intelliforia (claude, 169 turns): 1 commit(s)
    intelliforia (claude, 216 turns): 1 commit(s)
    pjangler (claude, 138 turns): 3 commit(s)
    james-brennan (claude, 63 turns): 1 commit(s)
    intelliforia (claude, 30 turns): 2 commit(s)
    docsidian (claude, 23 turns): 1 commit(s)
    pjangler (claude, 145 turns): 5 commit(s)
    james-brennan (claude, 15 turns): 2 commit(s)
    intelliforia (claude, 391 turns): 2 commit(s)
    intelliforia (claude, 58 turns): 1 commit(s)
    intelliforia (claude, 174 turns): 1 commit(s)
    ... showing 30 of 38 committing sessions
  
  === Operational notes ===
    [unknown] failed: service-account key not found at /app/secrets/tiller-sa-key.json — create one in GCP, enable the Sheets API, and share the sheet with its client_email
    [unknown] started: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [unknown] failed: service-account key not found at /app/secrets/tiller-sa-key.json — create one in GCP, enable the Sheets API, and share the sheet with its client_email
    [unknown] started: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] started: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] started: (no detail)
    [wax] updated: (no detail)
    ... showing 20 of 33 operational events
  
  === Git log by repository ===
  === 33GOD ===
    83b74ad chore(reporting): refresh mirrored reports after the narrator rework
    54510cb feat(reporting): schedule the merged daily report nightly at 06:00
  
  === james-brennan ===
    957a390 checkpoint: 2026-08-19T23:29:59Z auto-commit
    54df24e docs(devops): state which username belongs on which login screen
    4ccaa8e checkpoint: 2026-08-19T14:19:53Z auto-commit
    8fa5d0d chore(git): actually untrack the LibreOffice lock file
    98040c8 docs(devops): diagram the account estate, credential by credential
    da5e561 chore(git): untrack .lastagent
    e949419 feat(inventory): retire Aurora, and the ledger row that outlived it
    f0efe34 docs(devops): record the account renames and Brennan Prod's new root email
    3e82201 docs(devops): the three AWS accounts, and which one actually holds anything
    1f81a79 chore(git): untrack the LibreOffice lock file and ignore the pattern
    af72303 feat(inventory): a console link per row, and the client's real name
    fc3d8c8 Chont
    8bcfec8 checkpoint: 2026-08-19T00:04:49Z auto-commit
  
  === intelliforia ===
    (checked out: design/admin-portal-overhaul; 16 of 65 commit(s) below are not reachable from it)
    0e64f9bf docs(staging): correct how is_production() is actually keyed
    2b938b7e docs(stories): real timings, and the demo failure modes that were tested
    7e2c0ba2 fix(test): a Ctrl-C no longer leaves a worktree registered
    979f5f3a docs(stories): record what two adversarial audits found, including what they could not break
    cae0644b docs(stories): state what the guards cannot prove, and reconcile the five template counts
    d1d44325 fix: honest guards, a focus stack, and a demo that cannot poison the tree
    cb51bcf0 test(portal): exercise the two paths nothing touched, and stop a skip reading as a pass
    fc48bad2 fix(portal): a close mid-upload lost the import and poisoned the next open
    528d563b docs(stories): 39 checks, and the string-by-string diff against #720
    a19ebf45 test(portal): guard the two glyphs, and sample the busy state in flight
    f2286420 fix(portal): restore the two glyphs the bulk-import port dropped
    2dc014cd docs(stories): 37 checks, and record the harness defect found by collision
    7b2baf2a test(portal): cover the import paths the first browser run left out
    edb4b63a fix(test): mutate a throwaway worktree, never the tree you are sitting in
    3500a94d docs(stories): make the commit count accurate and say what the commits are
    c91a9a8e docs(stories): record the browser proof, and narrow the limits section to what is still true
    cbd2a046 test(portal): drive the two rebase screens in a real browser
    5e62d323 docs(stories): the rebase integration proof, including where it was wrong first
    6960b820 test(portal): measure the conversion honestly
    f6e5f493 test(portal): prove the rebase lost nothing, on four axes
    79cd833e feat(portal): port #720's bulk provider import onto the shell
    6ccfebe5 feat(portal): convert the email policy screen, and give it a way in
    903d23d8 docs(stories): name all six unreachable templates, and correct the 37.6 delete list
    3f5f0a2a feat(staging): serve staging on stg.delo.sh so it is reachable without the other zone
    cdaeda8b docs(stories): close Story 37.5 — Phase 5 complete
    c47fab0f feat(portal): convert the settings cluster — Phase 5 complete
    56cf3e8b feat(portal): convert the jQuery-heavy screens; 152 jQuery calls removed
    eb547074 feat(portal): convert 8 more screens, and stop quoting prices the app never charges
    5d5f2fb4 feat(portal): convert 8 more screens, and fix a crash I shipped in all_notes
    525d5692 feat(portal): convert 6 more screens, close an IDOR, delete invented statistics
    507255a6 feat(portal): phase 5 components, and the tables DataTables never sorted
    e8183475 docs: correct two wrong claims in my own commit messages
    e6a12cc3 fix(local): keep the stack up across a docker daemon restart
    a5c9c38a chore(staging): land the staging deploy scripts, which were stranded on a branch
    ba8c5bfe docs(stories): record Epic 37 — admin portal design system
    c59a57a5 feat(portal): convert the providers roster to the new shell (Epic 37 phase 4)
    feef56b1 feat(portal): merge both dashboards into one Overview (Epic 37 phase 4)
    47a711a0 feat(portal): convert the notes list to the new shell, and make its filters work
    a936824c feat(portal): convert note detail to the new shell (Epic 37 phase 4)
    3668ce51 feat(portal): dialog and multi-select behaviour (Epic 37 phase 3)
    9e985c55 fix(local): publish port 3000 on IPv4 only so http://localhost:3000 works
    79cba4f7 feat(portal): add the design-system shell and stylesheet (Epic 37 phase 2)
    3ecdadad fix(local): pin postgres 17 so the local stack can open its own volume
    07234a58 test(portal): smoke-cover every admin page that renders a template
    6ab78f65 design: specify cadence-aware nudging, and record why the log can't explain it
    28080e51 design: settle the screen topology — Notes and Providers, not one screen with a toggle
    7937a379 design: correct the contrast floor and record two cascade traps
    f64bfffc design: capture product truth and the admin portal design system
    09ae9f9c docs(stories): name all six unreachable templates, and correct the 37.6 delete list  [not reachable from design/admin-portal-overhaul; same author date and subject as 903d23d8, counted once]
    2fd77883 feat(staging): serve staging on stg.delo.sh so it is reachable without the other zone  [not reachable from design/admin-portal-overhaul; same author date and subject as 3f5f0a2a, counted once]
    14c0d55e docs(stories): close Story 37.5 — Phase 5 complete  [not reachable from design/admin-portal-overhaul; same author date and subject as cdaeda8b, counted once]
    041231bd feat(portal): convert the settings cluster — Phase 5 complete  [not reachable from design/admin-portal-overhaul; same author date and subject as c47fab0f, counted once]
    d1cf32d5 feat(portal): convert the jQuery-heavy screens; 152 jQuery calls removed  [not reachable from design/admin-portal-overhaul; same author date and subject as 56cf3e8b, counted once]
    b3e0bdef feat(portal): convert 8 more screens, and stop quoting prices the app never charges  [not reachable from design/admin-portal-overhaul; same author date and subject as eb547074, counted once]
    31b369c5 feat(portal): convert 8 more screens, and fix a crash I shipped in all_notes  [not reachable from design/admin-portal-overhaul; same author date and subject as 5d5f2fb4, counted once]
    999f84ec feat(portal): convert 6 more screens, close an IDOR, delete invented statistics  [not reachable from design/admin-portal-overhaul; same author date and subject as 525d5692, counted once]
    3f6efd73 feat(portal): phase 5 components, and the tables DataTables never sorted  [not reachable from design/admin-portal-overhaul; same author date and subject as 507255a6, counted once]
    5926cd58 docs: correct two wrong claims in my own commit messages  [not reachable from design/admin-portal-overhaul; same author date and subject as e8183475, counted once]
    bfefae87 fix(local): keep the stack up across a docker daemon restart  [not reachable from design/admin-portal-overhaul; same author date and subject as e6a12cc3, counted once]
    135149f6 Deploy coverage report from run 1271 48ad26f6bc1a19d4909139288ba6a480c3ed75d7  [not reachable from design/admin-portal-overhaul]
    48ad26f6 Add no_issues review state, short-session repeat exemption, and review-driven board (#722)
    962489db chore(staging): land the staging deploy scripts, which were stranded on a branch  [not reachable from design/admin-portal-overhaul; same author date and subject as a5c9c38a, counted once]
    018d7423 Harden short-session and review backfill  [not reachable from design/admin-portal-overhaul]
    ff4b0a6c Allow repeats in short sessions; tweak email CTA  [not reachable from design/admin-portal-overhaul]
    049a9384 Add no_issues review state across tracker  [not reachable from design/admin-portal-overhaul]
  
  === delonet-company ===
  (no commits)
  
  === PoopToTheMoon ===
    1c301de test(spike): run the poop factory headlessly, 32 assertions green
    0429f5a feat(spike): poop factory blob engine + factory floor rig
    9235fab docs(arch): add game architecture doc through step 3
    0df0667 chore(agents): refresh GitHub agent descriptors from skill sync
    06e7c7a chore(repo): adopt pjangler CommonProject scaffolding
    c540b68 chore(bmad): land BMAD/GDS skill sync
    b945ab5 chore(git): ignore agent session exports and spike build output
  
  === pjangler ===
    0992d2d fix(PJAN-77): accept verified Skillex projection
    a808463 feat(PJAN-77): implement project notebook lifecycle
    ebafc8f docs(PJAN-77): finalize project notebook plan
    9e069c8 release(PJAN-44): v1.3.7
    ab896f8 test(pjan-71): pin the timezone so relative ages match on CI
    f381dff release(PJAN-44): v1.3.6
    26f3cae ci: install PyYAML for the Hermes profile renderer
    576aeab release(PJAN-44): v1.3.5
    2edb6cb ci: give uv its own Python so the Copier attestation can pass
    2807c25 release(PJAN-44): v1.3.4
    047f291 ci: install Copier as a uv tool so the lifecycle tests can trust it
    23e8664 release(PJAN-44): v1.3.3
    4ca643d test(PJAN-76): stop a fixture resolving BMAD from the live registry
    90b4ac3 release(PJAN-44): v1.3.2
    63eb234 fix(PJAN-76): BMAD is owned by bmad-method, not a frozen Skillex pack
    3377974 release(PJAN-44): v1.3.1
    0e0f38d build: bump hermes-agent-template to published main and refresh the PM scaffold
    5a4529d fix: unblock the release gate — npm test is green again
    e4e4426 chore: apply mise.config-root parity to pjangler itself
    9f23385 fix(PJAN-75): stop migrate reporting success it has not achieved
    3fff575 Merge branch 'fix/PJAN-67-fleet-env-authority'
    b8e7e7d build(PJAN-67): regenerate bundled entrypoints and refresh evidence
    7e8945c build: link pjangler bins into ~/.local/bin so they survive a node switch
  
  === bloodbank ===
    b741db5 test(PJAN-77): prove hook coexistence
  
  === candystore ===
  (no commits)
  
  === holocene ===
  (no commits)

HERMES FLEET HEALTH
-------------------
**Status (authoritative): complete**

Hermes fleet: 28 agents registered; 9 timers (9 active, 0 failed); 3 cron jobs across 3 profiles (3 enabled); 1 job(s) reference a missing skill; 0 profile(s) with a stale ticker; 5 gateway unit(s) not running.
Metrics: agent_profile_dirs_missing=0, agents_registered=28, cron_jobs_enabled=3, cron_jobs_total=3, cron_jobs_unreadable=0, duplicate_cron_dirs=1, gateway_units_inactive=2, gateway_units_unknown=3, jobs_claiming_ok_contradicted=1, jobs_claiming_ok_unverified=2, jobs_with_missing_skill=1, jobs_with_past_next_run=0, profiles_scanned=35, profiles_unreadable_jobs=0, profiles_with_cron_jobs=3, profiles_with_stale_ticker=0, profiles_without_cron_dir=0, report_date=2026-08-19, sources_failed=0, sources_read=4, timers_active=9, timers_failed=0, timers_never_triggered=0, timers_total=9, timers_without_next_elapse=8, units_failed=0, units_not_found=1, units_total=46
Caveats:
  2 cron job(s) report last_status='ok' with no independent corroboration; last_status is a scheduler claim and is not treated as evidence of success
  1 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-08-20T10:00:51.703286Z (fleet state is current, not reconstructed for the report date)
  registry: 28 agents, 0 missing profile dir(s), 3 gateway unit(s) unknown to systemd, 2 not active
    agent bloodbank-pm: hermes-bloodbank-pm-gateway.service unknown to systemd
    agent delocontainers-pm: hermes-delocontainers-pm-gateway.service not active
    agent delonet-director: hermes-delonet-director-gateway.service unknown to systemd; hermes-delonet-director-heartbeat.timer unknown to systemd
    agent hermes-agent-pm: hermes-hermes-agent-pm-gateway.service unknown to systemd
    agent skillex-pm: hermes-skillex-pm-gateway.service not active
  systemd units: 46 matching, 0 failed, 1 not-found
    unit hermes-tonnybox-pm-consumer.service: not-found/inactive/dead
  timers: 9 matching, 9 active, 0 failed, 8 with no next elapse, 0 never triggered
    timer hermes-33god-pm-heartbeat.timer: no next elapse (last 2026-08-07T14:10:01.541781Z)
    timer hermes-automatic-ai-pm-heartbeat.timer: no next elapse (last 2026-08-07T14:10:01.539280Z)
    timer hermes-candystore-pm-heartbeat.timer: no next elapse (last 2026-08-07T14:10:01.539880Z)
    timer hermes-deckard-pm-heartbeat.timer: no next elapse (last 2026-08-18T13:29:18.774259Z)
    timer hermes-heyma-pm-heartbeat.timer: no next elapse (last 2026-08-07T14:10:01.540650Z)
    timer hermes-pjangler-pm-heartbeat.timer: no next elapse (last 2026-08-07T14:10:01.540046Z)
    timer hermes-slowburns-pm-heartbeat.timer: no next elapse (last 2026-08-07T14:10:01.539435Z)
    timer hermes-voxxy-pm-heartbeat.timer: no next elapse (last 2026-08-18T13:29:18.774107Z)
  cron: 35 profiles scanned (0 without a cron dir), 3 with jobs, 3 jobs (3 enabled), 0 stale ticker(s), 1 shared cron dir(s)
    profile 33god-pm.bak: shares its cron dir with 33god-pm
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-08-19T10:02:14.142005Z, next 2026-08-21T10:00:00Z
    job 33god-pm.bak/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-08-19T10:02:14.142005Z, next 2026-08-21T10:00:00Z
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='ok' (claim, contradicted), last run 2026-08-19T13:12:56.292440Z, next 2026-08-20T13:00:00Z; skill(s) not installed: obsidian, llm-wiki

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 1 tick(s) across 1 of 1 tracked repositories on 2026-08-19; 2 PR(s) triaged, 2 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=0, merge_candidates=2, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=0, prs_triaged=2, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=0, ticks_in_window=1, ticks_noop=0
Caveats:
  pr-crusher activity is read from its durable state, not Candystore: its Bloodbank publisher has been observed disabled, so absence of PR events on the bus does not mean absence of PR activity
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-08-19T04:00:00Z .. 2026-08-20T04:00:00Z for 2026-08-19 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 0
    tick 23 tick-000023-20260819T070228.497421Z completed=2026-08-19T07:03:16.545822Z provider=opencode provider_status=complete result_status=complete success=True automerge=False
      PR #111 ci=green coverage=adequate grade=good disposition=keep mergeable=True draft=False threads_resolved=True head=e2e916a115af
      PR #115 ci=green coverage=missing grade=good disposition=keep mergeable=True draft=False threads_resolved=True head=4b051923b344
      merge gate PR #111 allowed=False attempted=False reasons: automerge disabled; CI is not successful; coverage is not holding
      merge gate PR #115 allowed=False attempted=False reasons: automerge disabled; CI is not successful; coverage is not holding
      summary: Analyzed 2 open PRs (analysis-only, auto-merge disabled, no side effects taken). PR #111: critical bugfix unref'ing health-monitor interval (fixes #92 — 294 orphaned processes / 6.5 GB swap in production), includes 2 new unit tests, CI green, mergeable, needs review. PR #115: adds optional pos param to add_card_to_list + batch add_cards_to_list, mechanical 1:1 Trello API passthrough (widens floor,... (clipped from 538 chars)
      note: PR #111 triage: KEEP. Critical bugfix — TrelloHealthMonitor.startPerformanceMonitoring() created a 60s setInterval whose handle was never stored, unref'd, or cleared. A referenced timer pins the Node event loop, so a stdio MCP server never exits after client disconnect (stdin EOFs, process reparented to init, runs forever). Author reports 294 orphaned processes holding 6.5 GB swap over 59 days. Fi... (clipped from 988 chars)
      note: PR #115 triage: KEEP. Adds optional pos (string|number) to add_card_to_list and per-card pos to add_cards_to_list (batch), forwarded to POST /cards. Matches existing update_card_details/move_card pos semantics; omitted pos keeps Trello default (bottom). Clean 16-line diff across src/index.ts (+12) and src/trello-client.ts (+4). CI green (GitGuardian SUCCESS). Mergeable. Review required (0 reviews)... (clipped from 916 chars)
      note: Priority ordering: PR #111 before PR #115. #111 is a critical production bugfix with tests and clear reproduction; #115 is a nice-to-have feature lacking automated tests. If side effects were permitted under this contract: post triage comments on both, apply pr-crusher/keep + pr-crusher/good labels, request tests on #115, approve #111, then squash-merge #111. No mutating actions emitted per analys... (clipped from 417 chars)

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: DELIVERY DEGRADED -- 5 of 6 due day(s) in 2026-08-13..2026-08-19 have no valid published report (4 missing, 1 invalid); 2 day(s) carry a completion event with no archived report -- an earlier run reported success it did not achieve. 1 of 6 due days delivered over 2026-08-13..2026-08-19 (5 gap(s)); 7 completion event(s), 2 archive/event disagreement(s); delivered streak 1.
Metrics: archive_event_disagreements=2, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=1, days_archive_without_event=0, days_checked=7, days_delivered=1, days_event_without_archive=2, days_in_progress=1, days_invalid=1, days_missing=4, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=5, delivery_health=degraded, events_found=7, lookback_days=7
Caveats:
  DELIVERY DEGRADED: 5 of 6 due day(s) in 2026-08-13..2026-08-19 have no valid published report (4 missing, 1 invalid)
  DELIVERY DEGRADED: 2 day(s) carry a completion event with no archived report -- an earlier run reported success it did not achieve
  duplicate completion events for 2026-08-16, 2026-08-17; more than one run claimed the same day
  DISAGREEMENT 2026-08-16 published-but-never-archived (event-without-archive): 2 completion event(s) claim status complete, but the archive says missing -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-08-17 published-but-never-archived (event-without-archive): 4 completion event(s) claim status complete, but the archive says invalid -- an earlier run reported success it did not achieve
Detail:
  window 2026-08-13..2026-08-19 (7 days), report_date 2026-08-19
  delivery health degraded: 5 of 6 due day(s) in 2026-08-13..2026-08-19 have no valid published report (4 missing, 1 invalid); 2 day(s) carry a completion event with no archived report -- an earlier run reported success it did not achieve
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.v1.reporting.report.completed: reachable
  2026-08-13 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-13
  2026-08-14 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-14
  2026-08-15 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-15
  2026-08-16 missing events=2 claimed=complete cross_check=published-but-never-archived reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-16
  2026-08-17 invalid events=4 claimed=complete cross_check=published-but-never-archived generation=14844fcd69ad47fb9adf2860f203c489 reason=report.json is invalid: DailyReport sections must be exactly ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery'], got ['executive-brief', 'key-changes', 'risks-watchlist', 'coverage-freshness', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery']
  2026-08-18 delivered events=1 claimed=complete generation=d746fa58127544879b19e64bcc0629f3
  2026-08-19 in-progress events=0 reason=this run is producing this day; it publishes after collection
  DISAGREEMENT 2026-08-16 published-but-never-archived (event-without-archive): 2 completion event(s) claim status complete, but the archive says missing -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-08-17 published-but-never-archived (event-without-archive): 4 completion event(s) claim status complete, but the archive says invalid -- an earlier run reported success it did not achieve

COVERAGE
--------
4 of 4 enabled sections completed.
No section is degraded.

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | complete | 2026-08-20T10:00:51.696794Z | 2026-08-21T10:00:51.696794Z | - |
| fleet-health | complete | 2026-08-20T10:00:51.703286Z | 2026-08-21T10:00:51.703286Z | - |
| pr-maintenance | complete | 2026-08-20T10:00:51.751181Z | 2026-08-21T10:00:51.751181Z | - |
| report-delivery | complete | 2026-08-20T10:00:51.767872Z | 2026-08-21T10:00:51.767872Z | - |
Required: dev-activity (complete), report-delivery (complete).
Overall status complete is derived from the run manifest above, not asserted.

Run ddr-2026-08-19-f7c13723 · generated 2026-08-20T10:01:19.966243Z · overall status: complete
