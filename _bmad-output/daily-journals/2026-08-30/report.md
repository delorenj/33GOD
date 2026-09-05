Daily Developer Report — 2026-08-30
Summary written by anthropic/claude-opus-5. Everything below it is rendered by the pipeline from files it read — every status, metric and caveat is on this page whether or not a model answered.

SUMMARY
-------
**A day of correction, not construction: the operator QA sweep on james-brennan reclassified or held eleven tickets that were sitting in Done, and most of the 83 commits went to closing gaps the board had already claimed were closed.**

## What happened

### The QA sweep reversed the board
Of 48 recorded decisions, the largest single cluster is undoing prior completions on `james-brennan`. Six tickets were reclassified from Done to Todo (`JIMB-34`, `JIMB-56`, `JIMB-57`, `JIMB-72`, `JIMB-75`, `JIMB-95`); six more were held and returned to Todo (`JIMB-89`, `JIMB-168`, `JIMB-170`, `JIMB-173`, `JIMB-181`, `JIMB-200`). Four were accepted (`JIMB-163`, `JIMB-188`, `JIMB-196`, `JIMB-214`). Evidence landed in `4b23516 wip(audit): checkpoint JIMB-163 evidence and QA sweep findings`.

### Relay/Surface authorization hardening — JIMB-204 and JIMB-210
The deepest engineering thread. Commits bound approvals to immutable state and closed authority gaps: `7e455a3`/`016480f` (approvals bound to immutable snapshots), `3b3c222 fix(relay): authorize commands before side effects`, `d2a27d1` (dispatch bound to immutable review actions), `60ff67d fix(relay): close JIMB-204 authority gaps`, `8344598`/`a0dd992` on Surface approval binding and recovery. Architecture revision 6 was adopted as the Workflow One target; immutability will be version-pinned at the application layer rather than via S3 Object Lock. `JIMB-204` stayed open after final review found two release-blocking liveness and crash-recovery gaps, and the `JIMB-210` deployment hold remains. `bf0f9b4 test(relay): make Miami Beach permanently ephemeral` follows the decision to drop artifact preservation from the rollout gate.

### Testbed run-identity work (JIMB-194)
A six-commit run — `c0335cc` exposing the developer job roster through `86cdf83`, `6ec515e`, `b1f00c0`, `1f6831e`, `2015f1f`, `362356e` — on run adoption, ownership and ECS history reconciliation.

### Contract grammar cleanup across 33GOD
`bloodbank` retired the bad ticket-lifecycle shape (`6b82d5f`, `28c708b` marking the runbook block un-runnable, `c06a4b0` making refusals say what happened); `candystore` `f17994e` and `holocene` `46e5d5c`/`86a6006` re-rendered without phantom event types. `33GOD` recorded six submodule pointer bumps to match.

### Two commits that admit prior failures
`7373f4b fix(check): the gate printed "all green" having run nothing` and `ae2d45e fix(mirror): the OpenAPI contract test has been inert since the file moved`.

## Needs you

- **A day of Codex work is quarantined pending your judgment.** `50d4e02` says plainly that the author does not trust it, parked it on a branch, and left a TODO to reconcile against main and tickets before merge. That reconciliation has not happened.
- **Report delivery is degraded**: `2026-08-26` has no published report and no staged generation in the archive. 5 of 6 due days delivered.
- **`james-brennan-pm/JIMB board-clearing heartbeat` is erroring** every 10 minutes — the `momo` skill is not installed. That is the loop that clears the JIMB board.
- **`delodocs-pm/delodocs-triage-second-pass` claims `ok` but is contradicted**: `obsidian` and `llm-wiki` skills are not installed.
- **8 gateway units are not running** (6 unknown to systemd, 2 inactive), and `hermes-tonnybox-pm-consumer.service` is not-found. `33god-pm.bak` shares a cron dir with `33god-pm`, so `delonet-daily-report` is registered twice.
- **`get.delo.sh` is flapping**: the container was restarted after HTTP 502 at least 14 times in the 20 operational events shown, out of 62 total.
- **Two mergeable PRs are stalled on you**: `delorenj/mcp-server-trello` #111 (fixes a process-exit bug — 294 orphaned processes, 6.5GB swap leak) and #115. CI passing, no human approval; pr-crusher is analysis-only and its tick was `blocked`.

## Worth noting

Effort is concentrated to the point of monoculture: `james-brennan` is 17,567 of 28,633 events, and 4 of 9 configured repos had no commits at all. 11 projects active in events have no configured git root, so their work is invisible to this report. Peak load was 15:00Z at 5,519 events; 369 sessions produced commits from only 7.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): complete**

28633 events across 15 project(s) on 2026-08-30: 369 session(s), 48 decision(s), 7 committing session(s), 83 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (83 on the checked-out branch, 0 only on other refs); peak 2026-08-30T15:00:00Z (5519 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=7, decision_count=48, event_count=28633, git_commit_count=83, git_commit_replays_collapsed=0, git_commits_off_head=0, git_commits_on_head=83, git_repos_failed=0, git_repos_logged=5, git_repos_missing=0, git_repos_no_commits=4, git_repos_with_off_head_commits=0, git_root_name_collisions=0, git_roots_active_in_events=4, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=True, peak_hour=2026-08-30T15:00:00Z, peak_hour_event_count=5519, project_count=15, projects_without_root=11, session_count=369
Caveats:
  decisions truncated: showing 30 of 48
  operational events truncated: showing 20 of 62
  git scope is 'all-refs': every ref of each configured repository was read for 2026-08-30 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  4 configured project root(s) were read across all refs of each repository and had no commits on 2026-08-30: intelliforia, delonet-company, PoopToTheMoon, pjangler
  11 project(s) active in events have no configured project root, so no git log was read for them: global-instruction-files, hermes-agent, intelliforia-mobile, memories, mirror, project-fuckudeer, relay, skills, and 3 more
Detail:
  === Events by CLI ===
    codex         13959
    claude        11103
    hermes         2806
    unknown         382
    copilot         271
    antigravity     111
    reportctl         1
  
  === Events by project ===
    james-brennan              17567
    intelliforia                4897
    unknown                     3605
    vinyl                        887
    relay                        724
    global-instruction-files     609
    bloodbank                    144
    33GOD                         74
    james-brennan.git             34
    memories                      32
    project-fuckudeer             20
    surface                       15
    wax                           11
    hermes-agent.git               5
    mirror                         4
    intelliforia-mobile            2
    skills                         1
    intelliforia.git               1
    project-fuckudeer.git          1
  
  === Decisions recorded ===
    [james-brennan] JIMB-163: Accept and complete JIMB-163 in the operator QA sweep
    [james-brennan] JIMB-34: Reclassify JIMB-34 from Done to Todo
    [james-brennan] JIMB-56: Reclassify JIMB-56 from Done to Todo
    [james-brennan] JIMB-57: Reclassify JIMB-57 from Done to Todo
    [james-brennan] JIMB-72: Reclassify JIMB-72 from Done to Todo
    [james-brennan] JIMB-75: Reclassify JIMB-75 from Done to Todo
    [james-brennan] JIMB-95: Reclassify JIMB-95 from Done to Todo
    [james-brennan] JIMB-168: Hold JIMB-168 and return it to Todo
    [james-brennan] JIMB-170: Hold JIMB-170 and return it to Todo
    [james-brennan] JIMB-173: Hold JIMB-173 and return it to Todo
    [james-brennan] JIMB-181: Hold JIMB-181 and return it to Todo
    [james-brennan] JIMB-89: Hold JIMB-89 and return it to Todo
    [james-brennan] JIMB-188: Accept JIMB-188 after operator QA sweep
    [james-brennan] JIMB-196: Accept JIMB-196 after operator QA sweep
    [james-brennan] JIMB-214: Accept JIMB-214 after operator QA sweep
    [james-brennan] JIMB-200: Hold JIMB-200 and return it to Todo
    [james-brennan] JIMB-207: Make the visible Workflow One cycle the orchestration authority and keep JIMB-210 as sole product WIP
    [james-brennan] JIMB-210: Stop this Momo pass with JIMB-210 as the sole implementation WIP
    [james-brennan] JIMB-222: Keep cohort authorization and cohort badges in JIMB-222, distinct from developer-call origin work
    [james-brennan] JIMB-210: Remove Miami Beach artifact preservation from the JIMB-210 and JIMB-204 rollout gate
    [james-brennan] JIMB-210: Adopt JIMB-210 architecture revision 6 as the Workflow One implementation target
    [james-brennan] JIMB-210: Use version-pinned application immutability for JIMB-210 evidence and do not enable S3 Object Lock
    [james-brennan] JIMB-204: Accept JIMB-204's frozen source checkpoint while retaining the JIMB-210 deployment hold
    [james-brennan] JIMB-132: Use the production S3 evidence-reference shape as JIMB-132's canonical contract
    [james-brennan] JIMB-198: Remove Jim's address from Surface without adding replacement UI
    [james-brennan] JIMB-210: Gate every Relay rollout on migration proof and committed recovery, and separate phone-session presence from Case workflow state
    [james-brennan] JIMB-204: Keep JIMB-204 active after final review found two release-blocking liveness and crash-recovery gaps
    [james-brennan] JIMB-221: Refine the Boiler Room redesign as a glance-first summary with complete reconciliable detail
    [james-brennan] JIMB-214: Accept the Surface UX spike and harden visual, fixture, CSS, and catalog contracts before extracting components
    [james-brennan] JIMB-188: Accept JIMB-188 for dependents after current production watcher review
    ... showing 30 of 48 decisions
  
  === Sessions that committed ===
    global-instruction-files (codex, 8 turns): 1 commit(s)
    james-brennan (claude, 544 turns): 2 commit(s)
    james-brennan (claude, 336 turns): 3 commit(s)
    james-brennan (claude, 341 turns): 1 commit(s)
    james-brennan (claude, 192 turns): 1 commit(s)
    james-brennan (claude, 145 turns): 2 commit(s)
    james-brennan (claude, 553 turns): 1 commit(s)
  
  === Operational notes ===
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [wax] updated: (no detail)
    [wax] started: (no detail)
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] completed: (no detail)
    ... showing 20 of 62 operational events
  
  === Git log by repository ===
  === 33GOD ===
    813f633 chore(submodules): bump momo for the step-02-apply de-duplication
    46d0b26 chore(submodules): bump momo, candystore, holocene for the ticket-lifecycle grammar fix
    2c9a1db chore(33GOD): bump bloodbank for the runbook second-pass fix
    033928f chore(33GOD): bump bloodbank and holocene for the deployed-docs contract sweep
    b162360 chore(bloodbank): bump gitlink for the contract-refusal message fixes
    46209db chore(pjangler): advance the pinned pointer past the stranded grammar work
  
  === james-brennan ===
    9f4408b checkpoint: 2026-08-30T23:36:22Z auto-commit
    3872479 chore(devops): taskdefs at 4b23516
    4b23516 wip(audit): checkpoint JIMB-163 evidence and QA sweep findings
    555ef0c checkpoint: 2026-08-30T20:34:18Z auto-commit
    14a87ac wip(skills): move tracked skill docs to skills.bak and symlink
    85c1a34 checkpoint: update .env.op,.gitignore,sync-skills.py, +24 more (27 files changed, 5513 insertions(+), 659 deletions(-))
    50d4e02 Codex has been working all day. I don't trust it. That's why all these changes are being put in a branch. TODO: reconcile all changes against main + tickets. If all checks out as good/value-add, merge back into main trunk
    9f33e75 fix(context): reject transient deployment claims
    61c8e6e fix(context): separate policy from runtime truth
    7e5eb21 docs(context): route agent startup through invariants
    29839d9 ci(context): enforce project skill invariants
    212beb8 Merge remote-tracking branch 'origin/main'
    15b3973 feat(deploy): add fail-closed FieldOpsLine cutover gate
    de91b81 docs(workflow): route delivery through project invariants
    1b9cedd fix(context): make project invariants unavoidable
    6c468a9 chore(devops): taskdefs at bf0f9b4
    bf0f9b4 test(relay): make Miami Beach permanently ephemeral
    aac810d docs(relay): preserve JIMB-210 acquisition spike
    d4642bd docs(relay): lock JIMB-210 cutover architecture
    5657fda docs(relay): record JIMB-204 source checkpoint
    0bc75f5 fix(relay): finish JIMB-204 quiet-room contract [skip ci]
    34a5fbb docs(relay): preserve JIMB-210 incident evidence
    5e2602d docs(board): record workflow evidence and UX spike
    a0dd992 fix(surface): harden JIMB-204 approval recovery
    3da6243 chore(devops): taskdefs at 60ff67d
    60ff67d fix(relay): close JIMB-204 authority gaps
    8344598 fix(surface): enforce JIMB-204 approval binding
    e644802 chore(devops): taskdefs at d2a27d1
    d2a27d1 fix(relay): bind dispatch to immutable review actions
    a74b7f6 Merge remote-tracking branch 'origin/main'
    016480f fix(surface): bind approvals to immutable snapshots
    d44b057 chore(devops): taskdefs at 49b8d30
    49b8d30 Merge remote-tracking branch 'origin/main'
    7e455a3 fix(relay): bind approvals to immutable snapshots
    6f39d82 chore(devops): taskdefs at 3b3c222
    3b3c222 fix(relay): authorize commands before side effects
    a943c53 fix(relay): recover tokenless terminal closeouts
    f5772c0 Merge remote-tracking branch 'origin/main'
    5959e6e fix(surface): purge retired Stuck design sync
    986cf11 chore(devops): taskdefs at bb56078
    bb56078 feat(relay): unify terminal closeout approval
    10b4110 feat(surface): unify terminal closeouts in Quiet Room
    8ba9d4d docs(workflow): record delivery evidence
    6ea0382 chore(devops): taskdefs at 86cdf83
    86cdf83 fix(testbed): retain active run ownership
    0aab108 chore(devops): taskdefs at 6ec515e
    6ec515e fix(testbed): preserve active run identity
    97e1584 chore(devops): taskdefs at b1f00c0
    b1f00c0 fix(testbed): make run adoption durable
    3dbbcf8 chore(devops): taskdefs at 1f6831e
    1f6831e fix(testbed): reconcile complete ECS run history
    f2feb0c chore(devops): taskdefs at 2015f1f
    2015f1f fix(testbed): adopt accepted ECS runs
    3949a91 chore(devops): taskdefs at ff5db8f
    ff5db8f chore(devops): taskdefs at 362356e
    362356e fix(testbed): settle roster after ECS stop
    649529a chore(devops): taskdefs at 3e177af
    3e177af Merge remote-tracking branch 'origin/main'
    8d8ba4a fix(testbed): close JIMB-194 acceptance gaps
    3bebc66 chore(devops): taskdefs at c0335cc
    c0335cc feat(testbed): expose developer job roster (JIMB-194)
    7373f4b fix(check): the gate printed "all green" having run nothing
    36c34de chore(devops): taskdefs at ab4641b
    ab4641b feat(repo): keep a bare `rg` out of the client record — increment 1
    c9f2a20 feat(devops): iam:apply refuses to delete a grant it cannot see
    744043f chore(devops): taskdefs at 40f07d0
    40f07d0 fix(relay): the line loads tomorrow's board for the last four hours of every evening
    dd0b852 docs: the boundary is field-ops-line, not line
    bd301da docs: name the boundaries, and settle the Terraform question
    f4128a0 fix(devops): exec-relay.json was one statement short of the live role
    ae2d45e fix(mirror): the OpenAPI contract test has been inert since the file moved
  
  === intelliforia ===
  (no commits)
  
  === delonet-company ===
  (no commits)
  
  === PoopToTheMoon ===
  (no commits)
  
  === pjangler ===
  (no commits)
  
  === bloodbank ===
    28c708b docs(lifecycle): fix the second retired-shape block in the runbook and mark it un-runnable
    6b82d5f docs(lifecycle): stop the contract repo from publishing the retired shape as guidance
    c06a4b0 fix(contract): make refusals say what actually happened, and teach §9
  
  === candystore ===
    f17994e fix(bloodbank): re-render ticket-lifecycle without the phantom event types
  
  === holocene ===
    46e5d5c fix(bloodbank): re-render ticket-lifecycle without the phantom event types
    86a6006 docs(scrum-master): retire the v1/repo-slug event grammar from the kanban bridge contract

HERMES FLEET HEALTH
-------------------
**Status (authoritative): complete**

Hermes fleet: 28 agents registered; 15 timers (15 active, 0 failed); 4 cron jobs across 4 profiles (4 enabled); 2 job(s) reference a missing skill; 0 profile(s) with a stale ticker; 8 gateway unit(s) not running.
Metrics: agent_profile_dirs_missing=0, agents_registered=28, cron_jobs_enabled=4, cron_jobs_total=4, cron_jobs_unreadable=0, duplicate_cron_dirs=1, gateway_units_inactive=2, gateway_units_unknown=6, jobs_claiming_ok_contradicted=1, jobs_claiming_ok_unverified=2, jobs_with_missing_skill=2, jobs_with_past_next_run=0, profiles_scanned=39, profiles_unreadable_jobs=0, profiles_with_cron_jobs=4, profiles_with_stale_ticker=0, profiles_without_cron_dir=0, report_date=2026-08-30, sources_failed=0, sources_read=4, timers_active=15, timers_failed=0, timers_never_triggered=0, timers_total=15, timers_without_next_elapse=0, units_failed=0, units_not_found=1, units_total=56
Caveats:
  2 cron job(s) report last_status='ok' with no independent corroboration; last_status is a scheduler claim and is not treated as evidence of success
  1 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-08-31T10:00:33.938014Z (fleet state is current, not reconstructed for the report date)
  registry: 28 agents, 0 missing profile dir(s), 6 gateway unit(s) unknown to systemd, 2 not active
    agent condaleeza: hermes-condaleeza-gateway.service not active
    agent delocontainers-pm: hermes-delocontainers-pm-gateway.service not active
    agent delonet-director: hermes-delonet-director-gateway.service unknown to systemd; hermes-delonet-director-heartbeat.timer unknown to systemd
    agent drumjangler-pm: hermes-drumjangler-pm-gateway.service unknown to systemd
    agent hermes-agent-pm: hermes-hermes-agent-pm-gateway.service unknown to systemd
    agent intelliforia-voice-agent-pm: hermes-intelliforia-voice-agent-pm-gateway.service unknown to systemd
    agent nautilus-trader-pm: hermes-nautilus-trader-pm-gateway.service unknown to systemd
    agent ssbnk-pm: hermes-ssbnk-pm-gateway.service unknown to systemd
  systemd units: 56 matching, 0 failed, 1 not-found
    unit hermes-tonnybox-pm-consumer.service: not-found/inactive/dead
  timers: 15 matching, 15 active, 0 failed, 0 with no next elapse, 0 never triggered
  cron: 39 profiles scanned (0 without a cron dir), 4 with jobs, 4 jobs (4 enabled), 0 stale ticker(s), 1 shared cron dir(s)
    profile 33god-pm.bak: shares its cron dir with 33god-pm
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-08-30T10:01:27.233140Z, next 2026-09-01T10:00:00Z
    job 33god-pm.bak/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-08-30T10:01:27.233140Z, next 2026-09-01T10:00:00Z
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='ok' (claim, contradicted), last run 2026-08-30T13:12:18.730635Z, next 2026-08-31T13:00:00Z; skill(s) not installed: obsidian, llm-wiki
    job james-brennan-pm/JIMB board-clearing heartbeat: enabled, schedule 'every 10m', last_status='error' (claim, not-claimed), last run 2026-08-31T09:53:35.148460Z, next 2026-08-31T10:03:35.148460Z; skill(s) not installed: momo; last_error recorded (142 chars, not copied here)

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 1 tick(s) across 1 of 1 tracked repositories on 2026-08-30; 2 PR(s) triaged, 2 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged; 1 tick(s) did not succeed.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=0, merge_candidates=2, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=0, prs_triaged=2, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=1, ticks_in_window=1, ticks_noop=0
Caveats:
  pr-crusher activity is read from its durable state, not Candystore: its Bloodbank publisher has been observed disabled, so absence of PR events on the bus does not mean absence of PR activity
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-08-30T04:00:00Z .. 2026-08-31T04:00:00Z for 2026-08-30 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 0
    tick 34 tick-000034-20260830T070030.135551Z completed=2026-08-30T07:01:12.994793Z provider=opencode_free provider_status=blocked result_status=blocked success=False automerge=False
      PR #111 ci=passing coverage=not_verified grade=good disposition=keep mergeable=MERGEABLE draft=False threads_resolved=0 head=e2e916a115af
      PR #115 ci=passing coverage=not_verified grade=good disposition=keep mergeable=MERGEABLE draft=False threads_resolved=0 head=4b051923b344
      summary: Analysis of two open PRs complete but cannot advance: PR #111 (fix/unref-health-monitor-interval) fixes a critical process-exit bug (294 orphaned processes, 6.5GB swap leak) and PR #115 (feat/add-card-pos) adds card position creation support. Both are mergeable with passing CI, but neither has human review approval. As an analysis-only runner, I cannot perform required side effects (approve, merge... (clipped from 497 chars)

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: DELIVERY DEGRADED -- 1 of 6 due day(s) in 2026-08-24..2026-08-30 have no valid published report (1 missing). 5 of 6 due days delivered over 2026-08-24..2026-08-30 (1 gap(s)); 5 completion event(s), 0 archive/event disagreement(s); delivered streak 3.
Metrics: archive_event_disagreements=0, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=3, days_archive_without_event=0, days_checked=7, days_delivered=5, days_event_without_archive=0, days_in_progress=1, days_invalid=0, days_missing=1, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=1, delivery_health=degraded, events_found=5, lookback_days=7
Caveats:
  DELIVERY DEGRADED: 1 of 6 due day(s) in 2026-08-24..2026-08-30 have no valid published report (1 missing)
Detail:
  window 2026-08-24..2026-08-30 (7 days), report_date 2026-08-30
  delivery health degraded: 1 of 6 due day(s) in 2026-08-24..2026-08-30 have no valid published report (1 missing)
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.reporting.report.completed: reachable
  2026-08-24 delivered events=1 claimed=complete generation=98b545accde943d0809aa4a9b0cda913
  2026-08-25 delivered events=1 claimed=complete generation=0c92b6f7abf8482188b536c9cc5eedf8
  2026-08-26 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-26
  2026-08-27 delivered events=1 claimed=complete generation=1472ef2e152c42aa94012cce38fb34ba
  2026-08-28 delivered events=1 claimed=complete generation=001568c972584cae9965b922dcef9126
  2026-08-29 delivered events=1 claimed=complete generation=e841776cf5764df5ad7cfca76f89fbbd
  2026-08-30 in-progress events=0 reason=this run is producing this day; it publishes after collection

COVERAGE
--------
4 of 4 enabled sections completed.
No section is degraded.

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | complete | 2026-08-31T10:00:33.931956Z | 2026-09-01T10:00:33.931956Z | - |
| fleet-health | complete | 2026-08-31T10:00:33.938014Z | 2026-09-01T10:00:33.938014Z | - |
| pr-maintenance | complete | 2026-08-31T10:00:33.986630Z | 2026-09-01T10:00:33.986630Z | - |
| report-delivery | complete | 2026-08-31T10:00:34.004580Z | 2026-09-01T10:00:34.004580Z | - |
Required: dev-activity (complete), report-delivery (complete).
Overall status complete is derived from the run manifest above, not asserted.

Run ddr-2026-08-30-59538da4 · generated 2026-08-31T10:01:15.804230Z · overall status: complete
