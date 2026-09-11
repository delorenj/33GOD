Daily Developer Report — 2026-09-09
Summary written by anthropic/claude-opus-5. Everything below it is rendered by the pipeline from files it read — every status, metric and caveat is on this page whether or not a model answered.

SUMMARY
-------
**Eleven security fixes shipped in intelliforia in a single day — and in the same 24 hours, a PM agent recorded over thirty decisions that all say the same thing about one ticket that never moved.**

## What happened

### Security backlog, intelliforia

The day's real output. On `security/backlog-2026-09`, eleven `fix(security)` commits closed a run of issues that were each a live exposure: empty CORS meaning "everyone" and cookies handed to cross-origin callers (#222), a wildcard OAuth client default with no way to de-authorize (#230), `/note-scoring` handing a live API key to anonymous visitors (#225), bearer tokens and clinical notes reaching the log drain (#226), password reset endpoints returning a live reset URL (#227), branded-email endpoints acting as open relays (#229), unbounded ZIP ingestion (#231), the embeddable widget building markup from AI feedback (#232), API key management scoped to org-admin (#223), and deletion of the cross-tenant note-evaluation cache endpoints (#233). `3c310c59` opened the runbook that frames them. Separately, Epic 40 (two-factor auth) landed as plan, epic and fifteen stories (`37450f77`). 21 commits total, 6 of them off the checked-out branch.

### JIMB-297 acceptance, james-brennan

28 commits, and the arc is a gate that held. `cdb7543` built the acceptance fixture unblocking the adversarial scenarios (JIMB-300), then three fixes chased it (`8155452`, `7bbc1c2`, `bd24770` — "one event loop, and derive each candidate's effect id instead of guessing it"). Two independent reviews passed AC1–AC7 with AC8 unexecuted; `aec8539` then recorded an autonomous adversarial **HOLD** citing significant drift, and the decision log holds JIMB-297 at live acceptance until AC8 has reviewed deploy and non-today closeout proof. `e012f83` generated the completed Exhibit B register from a grader run. 8 of 28 commits are off `main`, including every review commit.

### PR triage

One pr-crusher tick on `delorenj/mcp-server-trello`: PRs #115 and #111 both graded good and kept, both blocked — automerge disabled, threads unresolved, CI not successful, coverage not holding. Zero merges attempted.

## Needs you

- **TONNY-2 is a loop, not a blocker.** 30 of 72 shown decisions are near-identical restatements of "hold TONNY-2 at the adapter-only review-lane precondition." The agent is correctly refusing to duplicate work and correctly unable to proceed — the ticket-provider adapter exposes no distinct `in_review` lane. That is a one-time schema fix, and until you make it, that agent will keep spending passes saying so. One entry is visibly corrupted: `"...canonical review lanebbl no. Need clean. We'll create."`
- **2026-09-07 has no report at all.** Delivery is degraded: 5 of 6 due days, one gap, no `current.json` and no staged generation.
- **`hermes-automatic-ai-pm-heartbeat.service` is failed**, `hermes-tonnybox-pm-consumer.service` is not-found, and 9 gateway units are not running (6 unknown to systemd entirely, including `tonnybox-pm` — the agent generating all those decisions).
- **4 cron jobs claim `last_status='ok'` while missing skills they declare.** The JIMB hourly two-lane pass runs every 60m without `momo`, `project-lifecycle`, `project-invariants` or `coding-strategy` installed.

## Worth noting

33GOD, pjangler, bloodbank, candystore, holocene and delonet-company had zero commits across all refs. The platform is stable but untouched; all momentum is in client work. Also: `33god-pm.bak` shares a cron dir with `33god-pm`, so the daily report job exists twice and both fire.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): complete**

29677 events across 7 project(s) on 2026-09-09: 360 session(s), 72 decision(s), 19 committing session(s), 49 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (35 on the checked-out branch, 14 only on other refs); peak 2026-09-09T20:00:00Z (3898 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=19, decision_count=72, event_count=29677, git_commit_count=49, git_commit_replays_collapsed=0, git_commits_off_head=14, git_commits_on_head=35, git_repos_failed=0, git_repos_logged=2, git_repos_missing=0, git_repos_no_commits=7, git_repos_with_off_head_commits=2, git_root_name_collisions=0, git_roots_active_in_events=3, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=True, peak_hour=2026-09-09T20:00:00Z, peak_hour_event_count=3898, project_count=7, projects_without_root=4, session_count=360
Caveats:
  decisions truncated: showing 30 of 72
  operational events truncated: showing 20 of 55
  git scope is 'all-refs': every ref of each configured repository was read for 2026-09-09 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  7 configured project root(s) were read across all refs of each repository and had no commits on 2026-09-09: 33GOD, delonet-company, PoopToTheMoon, pjangler, bloodbank, candystore, holocene
  14 of 49 commit(s) are not reachable from their repository's checked-out branch (unmerged or otherwise off-HEAD work) and are counted here: james-brennan 8 of 28 (checked out: main), intelliforia 6 of 21 (checked out: security/backlog-2026-09)
  4 project(s) active in events have no configured project root, so no git log was read for them: deckard, intelliforia-mobile, project, slowburns
Detail:
  === Events by CLI ===
    hermes         15902
    claude         13353
    unknown          213
    codex            140
    antigravity       55
    hermes-agent      13
    reportctl          1
  
  === Events by project ===
    unknown               17406
    intelliforia           8469
    james-brennan          3586
    deckard                 130
    intelliforia-mobile      50
    pjangler                 25
    project                  10
    slowburns                 1
  
  === Decisions recorded ===
    [tonnybox] TONNY-2: Hold TONNY-2 as provider-blocked; do not dispatch a redundant implementer or a review that lacks the required review lane.
    [tonnybox] (no issue): Hold TONNY-2 outside active execution until the canonical review lanebbl no. Need clean. We'll create.
    [tonnybox] TONNY-2: Hold TONNY-2 on adapter review-state provisioning; do not dispatch duplicate implementation
    [tonnybox] TONNY-2: Hold TONNY-2 unstarted and do not delegate until an adapter-visible in_review state exists
    [tonnybox] TONNY-2: Attribution correction: end this pass blocked at TONNY-2's adapter-only review-lane precondition; do not duplicate verified implementation
    [tonnybox] TONNY-2: End this pass blocked at TONNY-2's adapter-only review-lane precondition; do not duplicate verified implementation
    [tonnybox] TONNY-2: End this pass blocked at TONNY-2's adapter-only review-lane precondition; do not duplicate verified implementation
    [tonnybox] TONNY-2: End this pass blocked at TONNY-2's adapter-only review-lane precondition; do not duplicate verified implementation
    [tonnybox] TONNY-2: End this pass blocked at TONNY-2's adapter-only review-lane precondition; do not duplicate verified implementation
    [tonnybox] TONNY-2: End this pass blocked at TONNY-2's adapter-only review-lane precondition; do not duplicate verified implementation
    [tonnybox] TONNY-2: Hold TONNY-2 outside active WIP until tp can place it in a distinct review lane; do not duplicate verified implementation.
    [tonnybox] TONNY-2: Hold TONNY-2 outside active WIP until tp can place it in a distinct review lane; do not duplicate its verified implementation.
    [tonnybox] TONNY-2: Keep TONNY-2 unstarted at the adapter-only review boundary; do not duplicate completed implementation or bypass tp.
    [tonnybox] TONNY-2: Hold TONNY-2 outside active WIP until an adapter-visible review lane exists; do not duplicate its verified implementation.
    [tonnybox] TONNY-2: Hold TONNY-2 at the provider review-lane precondition and stop this pass blocked
    [tonnybox] TONNY-2: Hold TONNY-2 unstarted at the adapter-only review-lane precondition; do not duplicate completed implementation
    [tonnybox] TONNY-2: Hold TONNY-2 unstarted until an adapter-visible review lane exists; do not duplicate implementation or bypass tp.
    [tonnybox] TONNY-2: Hold TONNY-2 at the provider review-lane precondition; do not duplicate completed implementation
    [james-brennan] JIMB-297: Hold JIMB-297 at autonomous review until AC8 has reviewed deploy and live non-today closeout proof
    [tonnybox] TONNY-2: Stop this sentinel pass with TONNY-2 held unstarted at the adapter-only review-lane precondition
    [tonnybox] TONNY-2: Keep TONNY-2 held in unstarted and end this pass blocked until the review lane is adapter-resolvable
    [tonnybox] TONNY-2: Keep TONNY-2 held in unstarted and end this pass blocked until the review lane is adapter-resolvable
    [tonnybox] TONNY-2: Keep TONNY-2 held at unstarted and end this pass blocked on the absent adapter-visible review state
    [tonnybox] TONNY-2: Hold TONNY-2 at the adapter-only review boundary; do not duplicate completed implementation
    [tonnybox] TONNY-2: Keep TONNY-2 unstarted and end this pass blocked at the adapter-only review-lane precondition
    [tonnybox] TONNY-2: Hold TONNY-2 at the adapter review-lane precondition; do not duplicate implementation or bypass the ticket-provider contract
    [tonnybox] TONNY-2: Hold TONNY-2 at the adapter review-lane precondition; do not dispatch duplicate implementation work.
    [tonnybox] TONNY-2: Hold TONNY-2 at unstarted and stop this pass because its required review lane remains unavailable through the approved adapter
    [tonnybox] TONNY-2: Keep TONNY-2 unstarted and end this pass blocked at the adapter-only review-lane precondition; do not duplicate completed implementation
    [tonnybox] TONNY-2: Hold TONNY-2 unstarted until the adapter exposes a distinct review lane; do not duplicate completed implementation
    ... showing 30 of 72 decisions
  
  === Sessions that committed ===
    james-brennan (claude, 23 turns): 1 commit(s)
    james-brennan (claude, 87 turns): 1 commit(s)
    intelliforia (claude, 23 turns): 1 commit(s)
    intelliforia (claude, 395 turns): 6 commit(s)
    intelliforia (claude, 1616 turns): 1 commit(s)
    intelliforia (claude, 49 turns): 1 commit(s)
    unknown (claude, 164 turns): 1 commit(s)
    unknown (claude, 24 turns): 1 commit(s)
    deckard (codex, 1 turns): 1 commit(s)
    deckard (codex, 4 turns): 1 commit(s)
    deckard (codex, 3 turns): 1 commit(s)
    unknown (claude, 31 turns): 1 commit(s)
    unknown (claude, 20 turns): 3 commit(s)
    unknown (claude, 16 turns): 2 commit(s)
    unknown (claude, 9 turns): 1 commit(s)
    unknown (claude, 13 turns): 1 commit(s)
    unknown (claude, 102 turns): 1 commit(s)
    intelliforia-mobile (claude, 109 turns): 1 commit(s)
    intelliforia (claude, 5 turns): 1 commit(s)
  
  === Operational notes ===
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] started: (no detail)
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] started: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    ... showing 20 of 55 operational events
  
  === Git log by repository ===
  === 33GOD ===
  (no commits)
  
  === james-brennan ===
    (checked out: main; 8 of 28 commit(s) below are not reachable from it)
    e012f83 feat(acceptance): generate the completed Exhibit B register from a grader run
    64766e4 fix(acceptance): the three defects standing between the grader and an honest register
    7b1ac27 checkpoint: 2026-09-09T18:53:52Z auto-commit
    cf6df6e docs(pm): hold JIMB-297 at live acceptance gate
    e9bce48 docs(pm): record JIMB-297 autonomous HOLD result  [not reachable from main]
    a4828a5 docs(pm): record bounded board-pass stop
    c501844 docs(pm): record bounded board-pass stop
    aec8539 review(jimb-297): autonomous adversarial HOLD — AC8 unexecuted, significant drift  [not reachable from main]
    b9a9ab0 review(jimb-297): independent Gate 2 code-quality review (AC1-AC7 pass; AC8 unexecuted)  [not reachable from main]
    15bbbee checkpoint: 2026-09-09T08:07:27Z auto-commit
    c8e29fd fix(jimb-297): correct false evidence command and broken diff link  [not reachable from main]
    4ba8775 review(jimb-297): independent Gate 2 code-quality review — approved (AC1-AC7 pass; AC8 unexecuted)  [not reachable from main]
    0143473 review(jimb-297): independent Gate 1 spec-compliance review (AC1-AC7 pass; AC8 unexecuted)  [not reachable from main]
    3458d8e chore(jimb-297): integration/evidence-repair — merge current origin/main, clear IAM blocker  [not reachable from main]
    b7dcf5f Merge remote-tracking branch 'origin/main' into hermes/jimb-297-closeout-window-20260908  [not reachable from main]
    d73d07d chore(devops): taskdefs at bd24770 — the receipt the deploy left uncommitted
    0e2ed53 docs(pm): record bounded board-pass stop
    6247f62 checkpoint: 2026-09-09T03:03:00Z auto-commit
    bd24770 fix(qa): one event loop, and derive each candidate's effect id instead of guessing it
    6d9d350 checkpoint: 2026-09-09T02:02:20Z auto-commit
    b2a97f5 chore(devops): taskdefs at 7bbc1c2
    7bbc1c2 fix(qa): the fixture must bring its own visit, or its approval collides
    6f89a64 docs(qa): the fixture is a thing that can break, so it has a row
    15dec7c chore(devops): taskdefs at 8155452
    f500250 checkpoint: 2026-09-09T01:02:09Z auto-commit
    8155452 fix(qa): the fixture bound another Case's snapshot, and its own approver's account
    cdb7543 feat(qa): the acceptance fixture that unblocks the adversarial scenarios (JIMB-300)
    434ff72 chore(devops): taskdefs at 8ce5592
  
  === intelliforia ===
    (checked out: security/backlog-2026-09; 6 of 21 commit(s) below are not reachable from it)
    38865de7 fix(security): stop empty CORS meaning "everyone", and stop handing cookies to cross-origin callers (#222)
    2e649da3 fix(security): take the wildcard out of the OAuth client default, and make de-authorization possible at all (#230)
    9bb395ae fix(security): stop /note-scoring handing a live API key to anonymous visitors (#225)
    050574ed fix(security): stop the embeddable widget building markup from AI feedback (#232)
    3489d89e test(security): drop a #227 fixture row that models an impossible state
    2ead85a8 fix(security): API key management is organization-admin only (#223)
    cd1a0b2c fix(security): stop bearer tokens and clinical notes reaching the log drain (#226)
    548a6d83 fix(security): stop password reset endpoints handing back a live reset URL (#227)
    7c543913 fix(security): bound ZIP ingestion before decompressing anything (#231)
    855b33d0 fix(security): stop the branded-email endpoints being open relays (#229)
    d78b511c fix(security): delete the cross-tenant note-evaluation cache endpoints (#233)
    3c310c59 docs(security): open the runbook for the September security backlog
    37450f77 Epic 40: two-factor authentication — plan, epic, and fifteen stories (#734)
    24f75e43 docs(epic-40): reconcile the plan with what #739 and #744 actually shipped  [not reachable from security/backlog-2026-09]
    6304b9a0 Deploy coverage report from run 1411 488ced437d98fd95e368277aa74f9f027f3dfabf  [not reachable from security/backlog-2026-09]
    488ced43 Pin SkyCare prod ID in manual-only defaults (#752)
    2fde2dba Tighten SCR-008 duration-depth scoring rules  [not reachable from security/backlog-2026-09]
    1a1e8a06 docs(stories): re-anchor Epic 40 line references after main moved  [not reachable from security/backlog-2026-09]
    869a2d05 Merge remote-tracking branch 'origin/main' into docs/epic-40-two-factor-authentication  [not reachable from security/backlog-2026-09]
    f4295ecf Deploy coverage report from run 1406 c5d7122ba5c7fa67b3f55465f8448461f087f614  [not reachable from security/backlog-2026-09]
    c5d7122b fix(skills): remove .github/skills, the last committed skill projection (#751)
  
  === delonet-company ===
  (no commits)
  
  === PoopToTheMoon ===
  (no commits)
  
  === pjangler ===
  (no commits)
  
  === bloodbank ===
  (no commits)
  
  === candystore ===
  (no commits)
  
  === holocene ===
  (no commits)

HERMES FLEET HEALTH
-------------------
**Status (authoritative): complete**

Hermes fleet: 29 agents registered; 16 timers (16 active, 0 failed); 6 cron jobs across 4 profiles (4 enabled); 4 job(s) reference a missing skill; 0 profile(s) with a stale ticker; 9 gateway unit(s) not running.
Metrics: agent_profile_dirs_missing=0, agents_registered=29, cron_jobs_enabled=4, cron_jobs_total=6, cron_jobs_unreadable=0, duplicate_cron_dirs=1, gateway_units_inactive=3, gateway_units_unknown=6, jobs_claiming_ok_contradicted=4, jobs_claiming_ok_unverified=2, jobs_with_missing_skill=4, jobs_with_past_next_run=0, profiles_scanned=40, profiles_unreadable_jobs=0, profiles_with_cron_jobs=4, profiles_with_stale_ticker=0, profiles_without_cron_dir=0, report_date=2026-09-09, sources_failed=0, sources_read=4, timers_active=16, timers_failed=0, timers_never_triggered=0, timers_total=16, timers_without_next_elapse=0, units_failed=1, units_not_found=1, units_total=58
Caveats:
  2 cron job(s) report last_status='ok' with no independent corroboration; last_status is a scheduler claim and is not treated as evidence of success
  4 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-09-10T10:01:26.942229Z (fleet state is current, not reconstructed for the report date)
  registry: 29 agents, 0 missing profile dir(s), 6 gateway unit(s) unknown to systemd, 3 not active
    agent automatic-ai-pm: hermes-automatic-ai-pm-gateway.service not active
    agent delocontainers-pm: hermes-delocontainers-pm-gateway.service not active
    agent delonet-director: hermes-delonet-director-gateway.service unknown to systemd; hermes-delonet-director-heartbeat.timer unknown to systemd
    agent drumjangler-pm: hermes-drumjangler-pm-gateway.service unknown to systemd
    agent hermes-agent-pm: hermes-hermes-agent-pm-gateway.service unknown to systemd
    agent intelliforia-voice-agent-pm: hermes-intelliforia-voice-agent-pm-gateway.service unknown to systemd
    agent nautilus-trader-pm: hermes-nautilus-trader-pm-gateway.service unknown to systemd
    agent ssbnk-pm: hermes-ssbnk-pm-gateway.service not active
    agent tonnybox-pm: hermes-tonnybox-pm-gateway.service unknown to systemd
  systemd units: 58 matching, 1 failed, 1 not-found
    unit hermes-automatic-ai-pm-heartbeat.service: loaded/failed/failed
    unit hermes-tonnybox-pm-consumer.service: not-found/inactive/dead
  timers: 16 matching, 16 active, 0 failed, 0 with no next elapse, 0 never triggered
  cron: 40 profiles scanned (0 without a cron dir), 4 with jobs, 6 jobs (4 enabled), 0 stale ticker(s), 1 shared cron dir(s)
    profile 33god-pm.bak: shares its cron dir with 33god-pm
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-09-09T10:02:40.623702Z, next 2026-09-11T10:00:00Z
    job 33god-pm/Board Cranker implementation loop: disabled, schedule 'every 5m', last_status='ok' (claim, contradicted), last run 2026-09-05T12:48:43.347617Z, next none; skill(s) not installed: momo, project-lifecycle, subagent-driven-development, coding-strategy, pjangler, bloodbank-integration
    job 33god-pm.bak/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-09-09T10:02:40.623702Z, next 2026-09-11T10:00:00Z
    job 33god-pm.bak/Board Cranker implementation loop: disabled, schedule 'every 5m', last_status='ok' (claim, contradicted), last run 2026-09-05T12:48:43.347617Z, next none; skill(s) not installed: momo, project-lifecycle, subagent-driven-development, coding-strategy, pjangler, bloodbank-integration
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='ok' (claim, contradicted), last run 2026-09-09T13:23:25.146990Z, next 2026-09-10T13:00:00Z; skill(s) not installed: obsidian, llm-wiki
    job james-brennan-pm/JIMB hourly two-lane pass: enabled, schedule 'every 60m', last_status='ok' (claim, contradicted), last run 2026-09-10T09:07:06.289659Z, next 2026-09-10T10:07:06.289659Z; skill(s) not installed: momo, project-lifecycle, project-invariants, coding-strategy

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 1 tick(s) across 1 of 1 tracked repositories on 2026-09-09; 2 PR(s) triaged, 2 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=0, merge_candidates=2, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=0, prs_triaged=2, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=0, ticks_in_window=1, ticks_noop=0
Caveats:
  pr-crusher activity is read from its durable state, not Candystore: its Bloodbank publisher has been observed disabled, so absence of PR events on the bus does not mean absence of PR activity
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-09-09T04:00:00Z .. 2026-09-10T04:00:00Z for 2026-09-09 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 0
    tick 44 tick-000044-20260909T071356.573365Z completed=2026-09-09T07:15:20.635411Z provider=opencode_free provider_status=complete result_status=complete success=True automerge=False
      PR #115 ci=True coverage=True grade=good disposition=keep mergeable=True draft=False threads_resolved=False head=4b051923b344
      PR #111 ci=False coverage=False grade=good disposition=keep mergeable=True draft=False threads_resolved=False head=e2e916a115af
      merge gate PR #115 allowed=False attempted=False reasons: automerge disabled; review threads are not resolved; CI is not successful; coverage is not holding
      merge gate PR #111 allowed=False attempted=False reasons: automerge disabled; review threads are not resolved; CI is not successful; coverage is not holding
      summary: Analyzed PRs #115 and #111 from runner-verified evidence. #115 is a good, mergeable mechanical addition with CI and coverage checks green, but its position validation is too broad and review comments remain unresolved. #111 is a good timer-lifecycle fix with tests, but lacks a test/coverage check and review approval. No GitHub mutations were performed.
      note: PR #115: keep; grade good; hold for validation narrowing and review-thread resolution.
      note: PR #111: keep; grade good; hold pending test/coverage CI and review approval.

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: DELIVERY DEGRADED -- 1 of 6 due day(s) in 2026-09-03..2026-09-09 have no valid published report (1 missing). 5 of 6 due days delivered over 2026-09-03..2026-09-09 (1 gap(s)); 5 completion event(s), 0 archive/event disagreement(s); delivered streak 1.
Metrics: archive_event_disagreements=0, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=1, days_archive_without_event=0, days_checked=7, days_delivered=5, days_event_without_archive=0, days_in_progress=1, days_invalid=0, days_missing=1, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=1, delivery_health=degraded, events_found=5, lookback_days=7
Caveats:
  DELIVERY DEGRADED: 1 of 6 due day(s) in 2026-09-03..2026-09-09 have no valid published report (1 missing)
Detail:
  window 2026-09-03..2026-09-09 (7 days), report_date 2026-09-09
  delivery health degraded: 1 of 6 due day(s) in 2026-09-03..2026-09-09 have no valid published report (1 missing)
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.reporting.report.completed: reachable
  2026-09-03 delivered events=1 claimed=complete generation=9ae59ab2fea74beb9111f4b899d83602
  2026-09-04 delivered events=1 claimed=complete generation=1589bf5d21f44a90b8300e70ad825ddc
  2026-09-05 delivered events=1 claimed=complete generation=4ac32fc52b1e4f14951337626ad5cc08
  2026-09-06 delivered events=1 claimed=complete generation=8e2ac83288994170be88aab7e592b974
  2026-09-07 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/09/2026-09-07
  2026-09-08 delivered events=1 claimed=complete generation=c088996ef49146ada1b9326fffed0936
  2026-09-09 in-progress events=0 reason=this run is producing this day; it publishes after collection

COVERAGE
--------
4 of 4 enabled sections completed.
No section is degraded.

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | complete | 2026-09-10T10:01:26.935805Z | 2026-09-11T10:01:26.935805Z | - |
| fleet-health | complete | 2026-09-10T10:01:26.942229Z | 2026-09-11T10:01:26.942229Z | - |
| pr-maintenance | complete | 2026-09-10T10:01:27.002505Z | 2026-09-11T10:01:27.002505Z | - |
| report-delivery | complete | 2026-09-10T10:01:27.020131Z | 2026-09-11T10:01:27.020131Z | - |
Required: dev-activity (complete), report-delivery (complete).
Overall status complete is derived from the run manifest above, not asserted.

Run ddr-2026-09-09-8f5c7666 · generated 2026-09-10T10:02:08.500457Z · overall status: complete
