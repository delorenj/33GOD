Daily Developer Report — 2026-09-20
Summary written by anthropic/claude-opus-5. Everything below it is rendered by the pipeline from files it read — every status, metric and caveat is on this page whether or not a model answered.

SUMMARY
-------
**The workforce/projects split shipped across three repos today — and the reporting pipeline that tells you about it has failed 4 of its last 6 due days.**

## What happened

### The Flume/PJangler split (15 commits, 3 repos)
The day's weight was a structural refactor. `73d524a feat(33GOD): Flume takes the workforce; PJangler keeps the projects` and its breaking counterpart `81759d9 refactor(PJAN-133)!: the workforce leaves pjangler for Flume` moved the workforce out. Flume then absorbed it: `5465d8d` registered the workforce component, `0c9a0e1` pinned envelope/public-shape/fixture fixes, `9adb246` pinned the ported test suite and four bug fixes.

PJangler got the matching subtraction under **PJAN-133** — `99115fe` stopped advertising what left, `2f43d1f` dropped the inert systemd consent path, `25645cc` rewrote docs and skills to describe what remains. **PJAN-134** landed separately: `dba593b` — an archived Plane board is not a board to bind to — pinned upstream as `ef255e0`. Adjacent: `206d9e9 feat(krebs): the ticket-provider adapters come home` and bloodbank's `ddf51d6`, splitting the project registry from the org chart. Docs closed the loop (`bf1321d`, `f59fb13`).

### james-brennan: lookups and CI (26 commits, 11 off `main`)
`ad259d7a` completed the unconnected-lookups protocol and asserted it from the server's source (**JIMB-356**, #197). **JIMB-349** came in two parts — `d56a7e90` stopped the migration suite writing into the tracked tree, `528aaefe` added the relay-half migration test, two siblings and a guard for the class. CI got unblocked by `963c1e4b` (**JIMB-354**, relay and voice actually start) with follow-up `7458d35c` giving each `setup-node` its own tool cache. `fd6a60c9` preserved visit lookup across report creation (**JIMB-333**). Everything else is bot churn — inventory and taskdef chores, each shadowed by an unmerged copy. That duplication *is* the 11 off-HEAD commits and the 1 collapsed replay.

## Needs you

- **Report delivery is degraded.** 4 of 6 due days have no valid published report (09-14, 09-15, 09-16, 09-18), and 09-19 has duplicate completion events. Probable cause is right there in fleet health: `33god-pm.bak` shares its cron dir with `33god-pm`, so `delonet-daily-report` is registered twice.
- **pr-crusher is dead in the water.** Its one tick on `delorenj/mcp-server-trello` failed — the credential broker rejected `prc_github_read_token` and `prc_github_write_token`. 0 PRs triaged, merge gate never attempted. Nothing merges until those tokens are fixed.
- **Fleet wiring is hollow.** 0 timers active, 9 gateway units not running, 7 unknown to systemd — including this agent's own `hermes-33god-pm-heartbeat.timer`. `delodocs-pm`'s ticker hasn't moved in 70,340s and its triage job reports `error`. Board Cranker has been disabled since 2026-09-05 and references six uninstalled skills.

## Worth noting

Developer activity is `partial` — pagination stopped at the 50,000-event budget while peak hour alone was 63,926, so the day is not fully covered, and 49,409 events have no project attribution. 3,873 sessions produced **0 recorded decisions**, which means a breaking refactor (`81759d9`) shipped with no decision event behind it. Five configured repos were silent: intelliforia, delonet-company, PoopToTheMoon, candystore, holocene.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): partial** -- event pagination stopped at the 50-page budget (50000 events read); the day is not fully covered

50000 events across 2 project(s) on 2026-09-20: 3873 session(s), 0 decision(s), 0 committing session(s), 40 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (30 on the checked-out branch, 11 only on other refs); peak 2026-09-20T07:00:00Z (63926 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=0, decision_count=0, event_count=50000, git_commit_count=40, git_commit_replays_collapsed=1, git_commits_off_head=11, git_commits_on_head=30, git_repos_failed=0, git_repos_logged=4, git_repos_missing=0, git_repos_no_commits=5, git_repos_with_off_head_commits=1, git_root_name_collisions=0, git_roots_active_in_events=1, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=True, peak_hour=2026-09-20T07:00:00Z, peak_hour_event_count=63926, project_count=2, projects_without_root=1, session_count=3873
Caveats:
  git scope is 'all-refs': every ref of each configured repository was read for 2026-09-20 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  5 configured project root(s) were read across all refs of each repository and had no commits on 2026-09-20: intelliforia, delonet-company, PoopToTheMoon, candystore, holocene
  11 of 41 commit(s) are not reachable from their repository's checked-out branch (unmerged or otherwise off-HEAD work) and are counted here: james-brennan 11 of 26 (checked out: main)
  1 commit(s) repeat the author date and subject of another commit in the same window (rebase or cherry-pick copies) and were counted once, not twice: james-brennan 1
  1 project(s) active in events have no configured project root, so no git log was read for them: project
Detail:
  === Events by CLI ===
    claude    44283
    hermes     4202
    unknown     855
    codex       660
  
  === Events by project ===
    unknown         49409
    james-brennan     588
    project             3
  
  === Decisions recorded ===
    (no recorded decisions)
  
  === Sessions that committed ===
    (no commits in session-end events)
  
  === Operational notes ===
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
  
  === Git log by repository ===
  === 33GOD ===
    bf1321d docs(33GOD): architecture reflects the pjangler/flume split
    f59fb13 docs(33GOD): the platform describes the split, and the fleet skills are reachable again
    ef255e0 chore(pjangler): pin the archived-board guard (PJAN-134)
    0c9a0e1 chore(flume): pin the envelope, public-shape and fixture fixes
    9492db2 chore(pjangler): pin the inert-systemd-input removal
    9adb246 chore(flume): pin the ported test suite and its four bug fixes
    206d9e9 feat(krebs): the ticket-provider adapters come home
    73d524a feat(33GOD): Flume takes the workforce; PJangler keeps the projects
    5465d8d feat(flume): register the workforce component
  
  === james-brennan ===
    (checked out: main; 11 of 26 commit(s) below are not reachable from it)
    6e85a12a chore(inventory): observed AWS services in run 35524277063 (#199)
    612728c9 chore(inventory): observed AWS services in run 35524277063  [not reachable from main]
    9a6d2ae2 chore(devops): taskdefs at ad259d7a (#198)
    4d5b8a59 chore(devops): taskdefs at ad259d7a  [not reachable from main]
    ad259d7a fix(JIMB-356): complete the unconnected-lookups protocol, and assert it from the server's source (#197)
    e362a30d chore(inventory): observed AWS services in run 35520765146 (#196)
    6e2d90fa chore(inventory): observed AWS services in run 35520765146  [not reachable from main]
    a385d99f chore(inventory): observed AWS services in run 35520494162 (#195)
    9ad73476 chore(devops): taskdefs at 528aaefe (#194)
    ca2b3aa3 chore(inventory): observed AWS services in run 35520494162  [not reachable from main]
    bbdefb5d chore(devops): taskdefs at 528aaefe  [not reachable from main]
    7458d35c fix(ci): give every setup-node its own tool cache (JIMB-354 follow-up) (#193)
    528aaefe fix(JIMB-349): relay half — the migration test, its two siblings, and a guard for the class (#192)
    775f7e8b chore(inventory): observed AWS services in run 35513988481 (#191)  [not reachable from main; same author date and subject as bbeb0785, counted once]
    bbeb0785 chore(inventory): observed AWS services in run 35513988481 (#191)
    b976c75f chore(inventory): observed AWS services in run 35513988481  [not reachable from main]
    aac74608 checkpoint: 2026-09-20T08:05:32Z auto-commit  [not reachable from main]
    963c1e4b fix(ci): let relay and voice actually start, and stop the gate mislabelling why they did not (JIMB-354) (#188)
    d56a7e90 fix(JIMB-349): stop the migration suite writing into the tracked tree, and make a recurrence loud (#187)
    d673c91e checkpoint: 2026-09-19T13:43:51Z auto-commit (#186)
    3b6a9010 chore(inventory): observed AWS services in run 35497060953 (#190)
    13c56960 chore(inventory): observed AWS services in run 35497060953  [not reachable from main]
    64e4598c chore(devops): taskdefs at fd6a60c9 (#189)
    59924177 chore(devops): taskdefs at fd6a60c9  [not reachable from main]
    fd6a60c9 fix(relay): preserve visit lookup across report creation (JIMB-333) (#175)
    bb7c9652 Merge main into JIMB-333 to reach the self-hosted runners  [not reachable from main]
  
  === intelliforia ===
  (no commits)
  
  === delonet-company ===
  (no commits)
  
  === PoopToTheMoon ===
  (no commits)
  
  === pjangler ===
    25645cc docs(PJAN-133): make pjangler's docs and skills describe what it still does
    dba593b fix(PJAN-134): an archived Plane board is not a board to bind to
    2f43d1f fix(PJAN-133): drop the inert systemd consent path
    99115fe fix(PJAN-133): stop advertising what left, stop writing what is not ours
    81759d9 refactor(PJAN-133)!: the workforce leaves pjangler for Flume
  
  === bloodbank ===
    ddf51d6 docs(bloodbank): split the project registry from the org chart
  
  === candystore ===
  (no commits)
  
  === holocene ===
  (no commits)

HERMES FLEET HEALTH
-------------------
**Status (authoritative): complete**

Hermes fleet: 24 agents registered; 0 timers (0 active, 0 failed); 5 cron jobs across 3 profiles (3 enabled); 3 job(s) reference a missing skill; 1 profile(s) with a stale ticker; 9 gateway unit(s) not running.
Metrics: agent_profile_dirs_missing=0, agents_registered=24, cron_jobs_enabled=3, cron_jobs_total=5, cron_jobs_unreadable=0, duplicate_cron_dirs=1, gateway_units_inactive=2, gateway_units_unknown=7, jobs_claiming_ok_contradicted=2, jobs_claiming_ok_unverified=2, jobs_with_missing_skill=3, jobs_with_past_next_run=0, profiles_scanned=39, profiles_unreadable_jobs=0, profiles_with_cron_jobs=3, profiles_with_stale_ticker=1, profiles_without_cron_dir=2, report_date=2026-09-20, sources_failed=0, sources_read=4, timers_active=0, timers_failed=0, timers_never_triggered=0, timers_total=0, timers_without_next_elapse=0, units_failed=0, units_not_found=1, units_total=19
Caveats:
  2 cron job(s) report last_status='ok' with no independent corroboration; last_status is a scheduler claim and is not treated as evidence of success
  2 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-09-21T10:02:08.444723Z (fleet state is current, not reconstructed for the report date)
  registry: 24 agents, 0 missing profile dir(s), 7 gateway unit(s) unknown to systemd, 2 not active
    agent 33god-pm: hermes-33god-pm-heartbeat.timer unknown to systemd
    agent deckard-pm: hermes-deckard-pm-heartbeat.timer unknown to systemd
    agent delocontainers-pm: hermes-delocontainers-pm-gateway.service not active
    agent delonet-director: hermes-delonet-director-gateway.service unknown to systemd; hermes-delonet-director-heartbeat.timer unknown to systemd
    agent gruvato-pm: hermes-gruvato-pm-gateway.service unknown to systemd
    agent heyma-pm: hermes-heyma-pm-heartbeat.timer unknown to systemd
    agent infra-pm: hermes-infra-pm-heartbeat.timer unknown to systemd
    agent james-brennan-pm: hermes-james-brennan-pm-heartbeat.timer unknown to systemd
    agent keepy-money-pm: hermes-keepy-money-pm-gateway.service unknown to systemd
    agent nautilus-trader-pm: hermes-nautilus-trader-pm-gateway.service unknown to systemd
    agent pjangler-pm: hermes-pjangler-pm-heartbeat.timer unknown to systemd
    agent sidepiece-pm: hermes-sidepiece-pm-gateway.service unknown to systemd
    agent skillex-pm: hermes-skillex-pm-gateway.service not active
    agent slowburns-pm: hermes-slowburns-pm-heartbeat.timer unknown to systemd
    agent ssbnk-pm: hermes-ssbnk-pm-gateway.service unknown to systemd; hermes-ssbnk-pm-heartbeat.timer unknown to systemd
    agent tonnybox-pm: hermes-tonnybox-pm-gateway.service unknown to systemd; hermes-tonnybox-pm-heartbeat.timer unknown to systemd
  systemd units: 19 matching, 0 failed, 1 not-found
    unit hermes-tonnybox-pm-consumer.service: not-found/inactive/dead
  timers: 0 matching, 0 active, 0 failed, 0 with no next elapse, 0 never triggered
  cron: 39 profiles scanned (2 without a cron dir), 3 with jobs, 5 jobs (3 enabled), 1 stale ticker(s), 1 shared cron dir(s)
    profile 33god-pm.bak: shares its cron dir with 33god-pm
    profile delodocs-pm: ticker last moved 70340s ago
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-09-20T10:10:06.213583Z, next 2026-09-22T10:00:00Z
    job 33god-pm/Board Cranker implementation loop: disabled, schedule 'every 5m', last_status='ok' (claim, contradicted), last run 2026-09-05T12:48:43.347617Z, next none; skill(s) not installed: momo, project-lifecycle, subagent-driven-development, coding-strategy, pjangler, bloodbank-integration
    job 33god-pm.bak/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-09-20T10:10:06.213583Z, next 2026-09-22T10:00:00Z
    job 33god-pm.bak/Board Cranker implementation loop: disabled, schedule 'every 5m', last_status='ok' (claim, contradicted), last run 2026-09-05T12:48:43.347617Z, next none; skill(s) not installed: momo, project-lifecycle, subagent-driven-development, coding-strategy, pjangler, bloodbank-integration
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='error' (claim, not-claimed), last run 2026-09-20T14:29:18.568645Z, next 2026-09-21T13:00:00Z; skill(s) not installed: obsidian, llm-wiki; last_error recorded (53 chars, not copied here)

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 1 tick(s) across 1 of 1 tracked repositories on 2026-09-20; 0 PR(s) triaged, 0 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged; 1 tick(s) did not succeed.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=0, merge_candidates=0, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=0, prs_triaged=0, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=1, ticks_in_window=1, ticks_noop=0
Caveats:
  pr-crusher activity is read from its durable state, not Candystore: its Bloodbank publisher has been observed disabled, so absence of PR events on the bus does not mean absence of PR activity
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-09-20T04:00:00Z .. 2026-09-21T04:00:00Z for 2026-09-20 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 0
    tick 54 tick-000054-20260920T071047.598929Z completed=2026-09-20T07:10:50.339709Z provider=none provider_status=failed result_status=failed success=False automerge=False
      merge gate PR #None allowed=False attempted=False reasons: merge processing failed: credential broker rejected prc_github_write_token
      summary: runner/provider setup failed: credential broker rejected prc_github_read_token

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: DELIVERY DEGRADED -- 4 of 6 due day(s) in 2026-09-14..2026-09-20 have no valid published report (4 missing). 2 of 6 due days delivered over 2026-09-14..2026-09-20 (4 gap(s)); 3 completion event(s), 0 archive/event disagreement(s); delivered streak 1.
Metrics: archive_event_disagreements=0, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=1, days_archive_without_event=0, days_checked=7, days_delivered=2, days_event_without_archive=0, days_in_progress=1, days_invalid=0, days_missing=4, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=4, delivery_health=degraded, events_found=3, lookback_days=7
Caveats:
  DELIVERY DEGRADED: 4 of 6 due day(s) in 2026-09-14..2026-09-20 have no valid published report (4 missing)
  duplicate completion events for 2026-09-19; more than one run claimed the same day
Detail:
  window 2026-09-14..2026-09-20 (7 days), report_date 2026-09-20
  delivery health degraded: 4 of 6 due day(s) in 2026-09-14..2026-09-20 have no valid published report (4 missing)
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.reporting.report.completed: reachable
  2026-09-14 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/09/2026-09-14
  2026-09-15 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/09/2026-09-15
  2026-09-16 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/09/2026-09-16
  2026-09-17 delivered events=1 claimed=partial generation=3252122c267b4beaa3e75dde1d2f11ca
  2026-09-18 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/09/2026-09-18
  2026-09-19 delivered events=2 claimed=partial generation=527ce8a2d2f742b99a1c920c5d037f85
  2026-09-20 in-progress events=0 reason=this run is producing this day; it publishes after collection

COVERAGE
--------
3 of 4 enabled sections completed.
Degraded: dev-activity (partial).

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | partial | 2026-09-21T10:02:08.429024Z | 2026-09-22T10:02:08.429024Z | event pagination stopped at the 50-page budget (50000 events read); the day is not fully covered |
| fleet-health | complete | 2026-09-21T10:02:08.444723Z | 2026-09-22T10:02:08.444723Z | - |
| pr-maintenance | complete | 2026-09-21T10:02:08.501580Z | 2026-09-22T10:02:08.501580Z | - |
| report-delivery | complete | 2026-09-21T10:02:08.518355Z | 2026-09-22T10:02:08.518355Z | - |
Required: dev-activity (partial), report-delivery (complete).
Overall status partial is derived from the run manifest above, not asserted.

Run ddr-2026-09-20-3382716d · generated 2026-09-21T10:03:03.753642Z · overall status: partial
