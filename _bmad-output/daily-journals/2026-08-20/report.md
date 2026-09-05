Daily Developer Report — 2026-08-20
Summary written by anthropic/claude-opus-5. Everything below it is rendered by the pipeline from files it read — every status, metric and caveat is on this page whether or not a model answered.

SUMMARY
-------
**Six commits dug `intelliforia` staging out of a hole that had been silently eating scheduled work — and meanwhile this report's own delivery pipeline only landed 2 of 6 due days in the last week.**

## What happened

**Staging reclamation in `intelliforia` was the day's heaviest thread.** Six commits, and the interesting ones are diagnoses, not features. `ff9ea4ae` found that web was resolving `redis` to the neighbours' shared-redis, *"so no task ran"* — a silent failure class, not a crash. `24dc8b19` restored the `db:pull-prod` task the nightly refresh invokes, and `dc02691f` published the db on `127.0.0.1:55432` because `pull_prod_db.sh` requires it. `5cf63696` fixed `--init-env` still generating the stg. config. `c6a97a5d` reclaimed `staging.intelliforia.com` now that the Heroku app is retired, and `e8ff00a6` merged `origin/main` into `design/admin-portal-overhaul`. That is a nightly refresh path that was broken in at least four independent places.

**`pjangler` ran a tight PJAN-77 notebook loop** — seven commits, six of them on that ticket: recovering rejected v1.14 note creates (`e7112f4`), hydrating scoped note details (`3473957`), isolating audit evidence (`21dde70`), aligning the baseline state ceiling (`e980808`), then docs (`a6d22cd`). Plus `f67916f`, untracking Codex CLI runtime droppings swept in by auto-checkpoints.

**`james-brennan` shipped voice ingress**: `632f672` added a Pipecat ingress for the Frank Line beside the live relay, and `d051adc` made TTS switchable *"so a missing Cartesia account is not a blocker"* — dependency risk defused before it bit.

**`PoopToTheMoon` was design-only**: three docs commits recording the static ladder correction (v0.2.0), its sprint change proposal, and the party-mode session that killed the physics frame.

Volume: 3,934 events, 141 sessions, 32 projects, peaking at 985 events in the 21:00Z hour. Only 10 sessions committed. **Zero decisions were recorded all day** despite a physics frame being killed and a staging domain reclaimed.

## Needs you

- **Report delivery is degraded.** 4 of 6 due days in 2026-08-14..2026-08-20 have no valid report. Worse, 2026-08-16 and 2026-08-17 carry 2 and 4 completion events claiming success against an archive that says *missing* and *invalid*. 2026-08-17's report.json has the wrong section set entirely. Runs are reporting success they did not achieve — the events cannot be trusted as delivery evidence.
- **`delodocs-pm/delodocs-triage-second-pass` claims `last_status='ok'` while missing the `obsidian` and `llm-wiki` skills.** A contradicted claim; that job is not doing what it says.
- **4 Hermes gateway units are not running** — `bloodbank-pm`, `delonet-director` and `hermes-agent-pm` are unknown to systemd, `candybar-pm` is inactive. `hermes-tonnybox-pm-consumer.service` is not-found.
- **`33god-pm.bak` shares its cron dir with `33god-pm`**, so `delonet-daily-report` is registered twice and ran twice.
- **The tiller job failed**: service-account key not found at `/app/secrets/tiller-sa-key.json`.
- **pr-crusher did nothing it could do.** 2 PRs triaged on `delorenj/mcp-server-trello` (#111, #115), both graded keep/good, both blocked solely on `REVIEW_REQUIRED` with zero reviews. Under the analysis-only contract it cannot approve. Those PRs need a human review or they sit forever.

## Worth noting

- 28 of 32 active projects have no configured git root — `automatic-ai` (599 events), `newapi` (542), `open-notebook` (428) and `brand` (368) are among the busiest things on the box and no commits were read for any of them. The commit count is a floor, not a measure.
- `33GOD`, `bloodbank`, `candystore`, `holocene` and `delonet-company` had no commits on any ref.
- pr-crusher's Bloodbank publisher has been observed disabled; only 2 lifecycle events reached the bus. Bus silence there is not evidence of quiet.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): complete**

3934 events across 32 project(s) on 2026-08-20: 141 session(s), 0 decision(s), 10 committing session(s), 18 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (18 on the checked-out branch, 0 only on other refs); peak 2026-08-20T21:00:00Z (985 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=10, decision_count=0, event_count=3934, git_commit_count=18, git_commit_replays_collapsed=0, git_commits_off_head=0, git_commits_on_head=18, git_repos_failed=0, git_repos_logged=4, git_repos_missing=0, git_repos_no_commits=5, git_repos_with_off_head_commits=0, git_root_name_collisions=0, git_roots_active_in_events=4, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=True, peak_hour=2026-08-20T21:00:00Z, peak_hour_event_count=985, project_count=32, projects_without_root=28, session_count=141
Caveats:
  projects truncated: showing 20 of 39
  operational events truncated: showing 20 of 46
  git scope is 'all-refs': every ref of each configured repository was read for 2026-08-20 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  5 configured project root(s) were read across all refs of each repository and had no commits on 2026-08-20: 33GOD, delonet-company, bloodbank, candystore, holocene
  28 project(s) active in events have no configured project root, so no git log was read for them: DeLoContainers, HeyMa, TheChung, automatic-ai, brand, brief-PoopToTheMoon-2026-08-05, client-portal, codex-desktop, and 20 more
Detail:
  === Events by CLI ===
    claude         2978
    codex           659
    antigravity     183
    unknown         105
    hermes            8
    reportctl         1
  
  === Events by project ===
    automatic-ai                     599
    newapi                           542
    open-notebook                    428
    brand                            368
    PoopToTheMoon                    296
    docsidian                        252
    relay                            206
    intelliforia                     202
    voice                            136
    james-brennan                    117
    hindsight                        105
    docker                            98
    staging                           97
    wax                               89
    unknown                           86
    TheChung                          78
    infra                             71
    memories                          70
    i-am-so-confused-with-twilio      14
    traefik                           13
    ... showing 20 of 39 projects
  
  === Decisions recorded ===
    (no recorded decisions)
  
  === Sessions that committed ===
    PoopToTheMoon (claude, 39 turns): 1 commit(s)
    docker (claude, 49 turns): 4 commit(s)
    hindsight (codex, 1 turns): 2 commit(s)
    PoopToTheMoon (claude, 88 turns): 1 commit(s)
    newapi (claude, 417 turns): 2 commit(s)
    staging (claude, 115 turns): 4 commit(s)
    intelliforia (claude, 12 turns): 2 commit(s)
    relay (claude, 95 turns): 2 commit(s)
    docsidian (claude, 33 turns): 1 commit(s)
    docsidian (claude, 45 turns): 2 commit(s)
  
  === Operational notes ===
    [unknown] failed: service-account key not found at /app/secrets/tiller-sa-key.json — create one in GCP, enable the Sheets API, and share the sheet with its client_email
    [unknown] started: (no detail)
    [unknown] exited: Observed unmanaged container exit: plane-migrator status=exited exit_code=0 restart_policy=no compose_file=/home/delorenj/docker/stacks/websites/plane/compose.yml
    [unknown] exited: Observed unmanaged container exit: relay-db-test status=exited exit_code=255 restart_policy=no compose_file=/home/delorenj/code/james-brennan/apps/relay/docker-compose.test.yml
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
    [wax] updated: (no detail)
    [wax] started: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    ... showing 20 of 46 operational events
  
  === Git log by repository ===
  === 33GOD ===
  (no commits)
  
  === james-brennan ===
    d051adc feat(voice): make TTS switchable so a missing Cartesia account is not a blocker
    632f672 feat(voice): Pipecat ingress for the Frank Line, beside the live relay
  
  === intelliforia ===
    ff9ea4ae fix(staging): web resolved `redis` to the neighbours' shared-redis, so no task ran
    dc02691f fix(local): publish db on 127.0.0.1:55432, which pull_prod_db.sh requires
    24dc8b19 fix(staging): restore the db:pull-prod task the nightly refresh invokes
    e8ff00a6 Merge remote-tracking branch 'origin/main' into design/admin-portal-overhaul
    5cf63696 fix(staging): --init-env was still generating the stg. config
    c6a97a5d feat(staging): reclaim staging.intelliforia.com now that the Heroku app is retired
  
  === delonet-company ===
  (no commits)
  
  === PoopToTheMoon ===
    af742ca docs(gdd): static ladder correction — v0.2.0
    69d7f18 docs(design): sprint change proposal — static ladder correction
    10a3e2c docs(design): record party-mode session that killed the physics frame
  
  === pjangler ===
    f67916f chore: untrack Codex CLI runtime droppings swept in by auto-checkpoints
    a6d22cd docs(PJAN-77): document project notebook commands
    e980808 fix(PJAN-77): align notebook baseline state ceiling
    c44f2c5 chore(PJAN-77): link project notebook canary
    21dde70 fix(PJAN-77): isolate notebook audit evidence
    3473957 fix(PJAN-77): hydrate scoped note details
    e7112f4 fix(PJAN-77): recover rejected v1.14 note creates
  
  === bloodbank ===
  (no commits)
  
  === candystore ===
  (no commits)
  
  === holocene ===
  (no commits)

HERMES FLEET HEALTH
-------------------
**Status (authoritative): complete**

Hermes fleet: 29 agents registered; 10 timers (10 active, 0 failed); 3 cron jobs across 3 profiles (3 enabled); 1 job(s) reference a missing skill; 0 profile(s) with a stale ticker; 4 gateway unit(s) not running.
Metrics: agent_profile_dirs_missing=0, agents_registered=29, cron_jobs_enabled=3, cron_jobs_total=3, cron_jobs_unreadable=0, duplicate_cron_dirs=1, gateway_units_inactive=1, gateway_units_unknown=3, jobs_claiming_ok_contradicted=1, jobs_claiming_ok_unverified=2, jobs_with_missing_skill=1, jobs_with_past_next_run=0, profiles_scanned=36, profiles_unreadable_jobs=0, profiles_with_cron_jobs=3, profiles_with_stale_ticker=0, profiles_without_cron_dir=0, report_date=2026-08-20, sources_failed=0, sources_read=4, timers_active=10, timers_failed=0, timers_never_triggered=0, timers_total=10, timers_without_next_elapse=0, units_failed=0, units_not_found=1, units_total=49
Caveats:
  2 cron job(s) report last_status='ok' with no independent corroboration; last_status is a scheduler claim and is not treated as evidence of success
  1 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-08-21T10:00:22.345161Z (fleet state is current, not reconstructed for the report date)
  registry: 29 agents, 0 missing profile dir(s), 3 gateway unit(s) unknown to systemd, 1 not active
    agent bloodbank-pm: hermes-bloodbank-pm-gateway.service unknown to systemd
    agent candybar-pm: hermes-candybar-pm-gateway.service not active
    agent delonet-director: hermes-delonet-director-gateway.service unknown to systemd; hermes-delonet-director-heartbeat.timer unknown to systemd
    agent hermes-agent-pm: hermes-hermes-agent-pm-gateway.service unknown to systemd
  systemd units: 49 matching, 0 failed, 1 not-found
    unit hermes-tonnybox-pm-consumer.service: not-found/inactive/dead
  timers: 10 matching, 10 active, 0 failed, 0 with no next elapse, 0 never triggered
  cron: 36 profiles scanned (0 without a cron dir), 3 with jobs, 3 jobs (3 enabled), 0 stale ticker(s), 1 shared cron dir(s)
    profile 33god-pm.bak: shares its cron dir with 33god-pm
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-08-20T10:02:03.435813Z, next 2026-08-22T10:00:00Z
    job 33god-pm.bak/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-08-20T10:02:03.435813Z, next 2026-08-22T10:00:00Z
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='ok' (claim, contradicted), last run 2026-08-20T13:03:10.953518Z, next 2026-08-21T13:00:00Z; skill(s) not installed: obsidian, llm-wiki

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 1 tick(s) across 1 of 1 tracked repositories on 2026-08-20; 2 PR(s) triaged, 2 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged; 1 tick(s) were no-ops.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=0, merge_candidates=2, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=1, prs_triaged=2, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=0, ticks_in_window=1, ticks_noop=1
Caveats:
  pr-crusher activity is read from its durable state, not Candystore: its Bloodbank publisher has been observed disabled, so absence of PR events on the bus does not mean absence of PR activity
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-08-20T04:00:00Z .. 2026-08-21T04:00:00Z for 2026-08-20 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 1
    tick 24 tick-000024-20260820T071151.244986Z completed=2026-08-20T07:12:25.061885Z provider=opencode provider_status=noop result_status=noop success=True automerge=False
      PR #111 ci=success coverage=unknown grade=good disposition=keep mergeable=False draft=False threads_resolved=True head=e2e916a115af
      PR #115 ci=success coverage=unknown grade=good disposition=keep mergeable=False draft=False threads_resolved=True head=4b051923b344
      merge gate PR #111 allowed=False attempted=False reasons: automerge disabled; coverage is not holding; candidate is not mergeable
      merge gate PR #115 allowed=False attempted=False reasons: automerge disabled; coverage is not holding; candidate is not mergeable
      summary: Analysis-only tick (HARD RUNNER CONTRACT: auto-merge disabled, no side effects, no tool/network calls). Triaged both open PRs from RUNNER-VERIFIED GITHUB EVIDENCE only. #115 (feat: pos param on add_card_to_list / add_cards_to_list) — keep/good: clean mechanical 1:1 endpoint widening that matches existing update_card_details/move_card pos semantics; widens the floor, does not raise the North-Star c... (clipped from 1162 chars)
      note: PR #115 triage: keep/good. Adds optional `pos` (top/bottom/positive number) to add_card_to_list and per-card pos to add_cards_to_list, forwarded to POST /cards via TrelloClient.addCard/batchAddCards. Idiomatic fit is good (mirrors existing pos semantics in update_card_details/move_card). North-Star: floor-widener, not ceiling-raiser. Gap: no tests for the new param (coverage floor). CI GitGuardian... (clipped from 686 chars)
      note: PR #111 triage: keep/good. Fixes #92 by storing the 60s performance-monitoring interval, calling unref?.() so a stdio server exits on stdin EOF, and adding stopPerformanceMonitoring() (idempotent clear). New tests/unit/health-monitor-timer.test.ts asserts unref is called and stop is idempotent. Reproduction evidence in PR body is concrete (1.8.1 hangs ~21s post-EOF; patch exits ~1s). North-Star: s... (clipped from 728 chars)
      note: No-op rationale: the only blockers on both keeps are REVIEW_REQUIRED with zero reviews. Under the HARD RUNNER CONTRACT I am analysis-only and auto-merge is disabled, so I cannot submit the approving review that would unblock either merge. No coding, commenting, labeling, reviewing, closing, or branch updates were performed. No evidence was fetched beyond the runner-supplied payload.

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: DELIVERY DEGRADED -- 4 of 6 due day(s) in 2026-08-14..2026-08-20 have no valid published report (3 missing, 1 invalid); 2 day(s) carry a completion event with no archived report -- an earlier run reported success it did not achieve. 2 of 6 due days delivered over 2026-08-14..2026-08-20 (4 gap(s)); 8 completion event(s), 2 archive/event disagreement(s); delivered streak 2.
Metrics: archive_event_disagreements=2, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=2, days_archive_without_event=0, days_checked=7, days_delivered=2, days_event_without_archive=2, days_in_progress=1, days_invalid=1, days_missing=3, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=4, delivery_health=degraded, events_found=8, lookback_days=7
Caveats:
  DELIVERY DEGRADED: 4 of 6 due day(s) in 2026-08-14..2026-08-20 have no valid published report (3 missing, 1 invalid)
  DELIVERY DEGRADED: 2 day(s) carry a completion event with no archived report -- an earlier run reported success it did not achieve
  duplicate completion events for 2026-08-16, 2026-08-17; more than one run claimed the same day
  DISAGREEMENT 2026-08-16 published-but-never-archived (event-without-archive): 2 completion event(s) claim status complete, but the archive says missing -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-08-17 published-but-never-archived (event-without-archive): 4 completion event(s) claim status complete, but the archive says invalid -- an earlier run reported success it did not achieve
Detail:
  window 2026-08-14..2026-08-20 (7 days), report_date 2026-08-20
  delivery health degraded: 4 of 6 due day(s) in 2026-08-14..2026-08-20 have no valid published report (3 missing, 1 invalid); 2 day(s) carry a completion event with no archived report -- an earlier run reported success it did not achieve
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.v1.reporting.report.completed: reachable
  2026-08-14 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-14
  2026-08-15 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-15
  2026-08-16 missing events=2 claimed=complete cross_check=published-but-never-archived reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-16
  2026-08-17 invalid events=4 claimed=complete cross_check=published-but-never-archived generation=14844fcd69ad47fb9adf2860f203c489 reason=report.json is invalid: DailyReport sections must be exactly ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery'], got ['executive-brief', 'key-changes', 'risks-watchlist', 'coverage-freshness', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery']
  2026-08-18 delivered events=1 claimed=complete generation=d746fa58127544879b19e64bcc0629f3
  2026-08-19 delivered events=1 claimed=complete generation=7a5d63d5fcf9494f979d5d27592d56de
  2026-08-20 in-progress events=0 reason=this run is producing this day; it publishes after collection
  DISAGREEMENT 2026-08-16 published-but-never-archived (event-without-archive): 2 completion event(s) claim status complete, but the archive says missing -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-08-17 published-but-never-archived (event-without-archive): 4 completion event(s) claim status complete, but the archive says invalid -- an earlier run reported success it did not achieve

COVERAGE
--------
4 of 4 enabled sections completed.
No section is degraded.

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | complete | 2026-08-21T10:00:22.339624Z | 2026-08-22T10:00:22.339624Z | - |
| fleet-health | complete | 2026-08-21T10:00:22.345161Z | 2026-08-22T10:00:22.345161Z | - |
| pr-maintenance | complete | 2026-08-21T10:00:22.389208Z | 2026-08-22T10:00:22.389208Z | - |
| report-delivery | complete | 2026-08-21T10:00:22.406640Z | 2026-08-22T10:00:22.406640Z | - |
Required: dev-activity (complete), report-delivery (complete).
Overall status complete is derived from the run manifest above, not asserted.

Run ddr-2026-08-20-36527430 · generated 2026-08-21T10:00:50.982620Z · overall status: complete
