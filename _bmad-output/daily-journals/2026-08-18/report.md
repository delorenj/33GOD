Daily Developer Report — 2026-08-18
Summary written by anthropic/claude-opus-5. Everything below it is rendered by the pipeline from files it read — every status, metric and caveat is on this page whether or not a model answered.

SUMMARY
-------
**Deckard shipped Sprint 1 to close on verified CI, while the report pipeline that tells you this has silently failed 6 of the last 7 days.**

## What happened

**Deckard dominated the day** — 2,778 events, 12 committing sessions, and 10 of the 17 recorded decisions. Sprint 1 closed: `DECK-20` (CI) was accepted with a green GitHub run in 2m03s cold and all nine guards carrying in-CI negative controls that were *independently broken* to confirm they go red. `DECK-19` was accepted at `05ce844` after a pre-merge hardening round closed three latent secret-handling findings. `DECK-18` landed the single-writer rule as a compile-time constraint, verified by 15 forge attacks from a genuinely downstream crate. Then the honest part: `DECK-24` was **reopened after acceptance** because an independent reviewer arrived late with a blocking finding that self-verification missed — and it reproduced. Five surviving material findings routed to `DECK-25` through `DECK-29`.

**Pjangler is grinding.** Five commits, all on `PJAN-67` (`fbf28fe`, `74bd682`, `c648f93`, `457142d`, `3eacb85`) hardening crash recovery, fleet lifecycle fail-closed behavior, and Hermes execution-tree attestation. It was held four separate times today — after the ninth, tenth, eleventh and twelfth independent SPEC reviews, with ten High fail-closed defects still outstanding at the tenth. All five commits sit off the checked-out `feat/PJAN-77-project-notebook` branch.

**Intelliforia's Epic 37 admin-portal work** produced 11 commits — Overview dashboard merge, providers roster, notes list and note detail converted to the new shell — plus merged PRs `#719`, `#720` (bulk provider CSV import) and `#721` (`VAL-037`, 30-day signature window). Eight of the 11 are unreachable from `design/admin-portal-overhaul`.

**Event plumbing** got wired end to end: `bloodbank` `36023b6` added `forward_envelope` for pre-built CloudEvents, `candystore` `20e887a` subscribed to `bloodbank.evt.>`, and 33GOD `0121135` pinned the publisher-enabling submodules. `james-brennan` shipped `JIMB-153` (alarm on proof age, not on success) and `JIMB-142` (New York night counting), and refined `JIMB-155` into eight testable criteria backed by a CSV in-repo rather than a hosted sheet.

## Needs you

- **Report delivery is degraded.** 5 days missing, 1 invalid (2026-08-17 emitted the wrong section set entirely). Worse: 2026-08-16 and 2026-08-17 both carry completion events claiming success against an archive that has nothing. Runs are reporting wins they did not achieve — the pipeline cannot be trusted to tell you when it breaks.
- **Five Hermes gateways are not running:** `bloodbank-pm`, `delonet-director`, `hermes-agent-pm` are *unknown to systemd*; `delocontainers-pm` and `skillex-pm` are inactive. `hermes-tonnybox-pm-consumer.service` is not-found.
- **8 of 9 heartbeat timers have no next elapse.** Six last fired 2026-08-07. They are active and doing nothing.
- `delodocs-pm/delodocs-triage-second-pass` claims `ok` but is missing the `obsidian` and `llm-wiki` skills.
- **Tiller failed:** no service-account key at `/app/secrets/tiller-sa-key.json`.

## Worth noting

`33god-pm.bak` shares a cron dir with `33god-pm`, so `delonet-daily-report` runs twice on the same schedule — likely the source of the duplicate completion events. pr-crusher triaged PRs `#111` and `#115` across two ticks; both are keep/good and blocked only on `REVIEW_REQUIRED`, but analysis-only mode means no approval can be submitted. They are stuck until you approve or the runner is unlocked.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): complete**

14057 events across 20 project(s) on 2026-08-18: 274 session(s), 17 decision(s), 21 committing session(s), 27 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (14 on the checked-out branch, 13 only on other refs); peak 2026-08-18T20:00:00Z (2399 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=21, decision_count=17, event_count=14057, git_commit_count=27, git_commit_replays_collapsed=0, git_commits_off_head=13, git_commits_on_head=14, git_repos_failed=0, git_repos_logged=7, git_repos_missing=0, git_repos_no_commits=2, git_repos_with_off_head_commits=2, git_root_name_collisions=0, git_roots_active_in_events=7, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=True, peak_hour=2026-08-18T20:00:00Z, peak_hour_event_count=2399, project_count=20, projects_without_root=13, session_count=274
Caveats:
  projects truncated: showing 20 of 29
  operational events truncated: showing 20 of 62
  git scope is 'all-refs': every ref of each configured repository was read for 2026-08-18 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  2 configured project root(s) were read across all refs of each repository and had no commits on 2026-08-18: delonet-company, holocene
  13 of 27 commit(s) are not reachable from their repository's checked-out branch (unmerged or otherwise off-HEAD work) and are counted here: intelliforia 8 of 11 (checked out: design/admin-portal-overhaul), pjangler 5 of 5 (checked out: feat/PJAN-77-project-notebook)
  13 project(s) active in events have no configured project root, so no git log was read for them: 33god-platform, agent-hooks, cli, codex-desktop, deckard, infra, issue-evidence, memories, and 5 more
Detail:
  === Events by CLI ===
    claude         9074
    codex          2601
    hermes         2122
    unknown         179
    antigravity      78
    reportctl         3
  
  === Events by project ===
    33GOD                3483
    deckard              2778
    pjangler             2452
    unknown              2230
    james-brennan        1339
    project-fuckudeer     625
    intelliforia          407
    33god-platform        187
    voxxy                 124
    wax                   120
    bloodbank              62
    skillex                34
    slowburns              33
    memories               33
    cli                    33
    candystore             28
    infra                  21
    PoopToTheMoon          16
    deckard.git            11
    issue-evidence         10
    ... showing 20 of 29 projects
  
  === Decisions recorded ===
    [deckard] DECK-24: Reopen DECK-24 after acceptance: the independent reviewer delivered late with a blocking finding that my own verification missed, and I reproduced it
    [deckard] DECK-24: QA-clear all seven Sprint 1 tickets rather than holding any back to active; route the five surviving material findings to new tickets DECK-25 through DECK-29 and fix the three mechanical ones under DECK-24
    [deckard] DECK-24: Refine DECK-24 in place and pull it, rather than bouncing it for empty acceptance criteria
    [pjangler] PJAN-67: Hold PJAN-67 after final12 file-transaction review
    [james-brennan] JIMB-155: Refined JIMB-155 from an intent sketch into eight testable criteria, and fixed the substrate as a CSV in the repo rather than a hosted sheet
    [pjangler] PJAN-67: Hold PJAN-67 after final11 transaction review
    [deckard] DECK-20: ACCEPT DECK-20 and close Sprint 1. CI is verifiably green on GitHub in 2m03s cold, and all nine guards carry in-CI negative controls that were independently broken to confirm they go red
    [deckard] DECK-20: Pull DECK-20 (CI), the last Sprint 1 ticket, and grant it a one-ticket exception to the no-push rule because AC7 cannot be verified without a real GitHub Actions run
    [deckard] DECK-19: ACCEPT DECK-19 at 05ce844 after a pre-merge hardening round closed three latent secret-handling findings, each re-verified against the delta by the reviewer that raised them
    [deckard] DECK-19: DECK-19 passes its gate; spending one extra hardening round on the two medium findings before merge rather than filing them, because MEDIUM(1) arms a trap for DECK-8 and both fixes are one line on a branch already in hand
    [pjangler] PJAN-67: Hold PJAN-67 after final10; ten High fail-closed defects remain
    [voxxy] (no issue): prune-local-gitignore-duplicates
    [agents] (no issue): centralize-generated-artifact-ignores
    [deckard] DECK-19: Pull DECK-19 (config + op:// resolution). Resolved two places where PRD 9's config schema is stale relative to decisions made since, and constrained how the worker may handle real credentials
    [pjangler] PJAN-67: Hold PJAN-67 after tenth independent SPEC found backfill ordering and exchange-recovery loss
    [deckard] DECK-18: ACCEPT DECK-18. The single-writer rule is now enforced at compile time, verified by 15 forge attacks from a genuinely downstream crate. Four deferred findings routed to DECK-4, DECK-8, DECK-20 and new DECK-23
    [pjangler] PJAN-67: Hold PJAN-67 after ninth independent SPEC found remaining executable fleet consumers
  
  === Sessions that committed ===
    deckard (claude, 63 turns): 1 commit(s)
    skillex (antigravity, 16 turns): 1 commit(s)
    deckard (claude, 41 turns): 3 commit(s)
    deckard (claude, 39 turns): 2 commit(s)
    33GOD (claude, 26 turns): 1 commit(s)
    project-fuckudeer (claude, 133 turns): 1 commit(s)
    33GOD (claude, 34 turns): 1 commit(s)
    intelliforia (claude, 151 turns): 3 commit(s)
    james-brennan (claude, 3 turns): 1 commit(s)
    james-brennan (claude, 74 turns): 2 commit(s)
    james-brennan (claude, 53 turns): 1 commit(s)
    intelliforia (claude, 110 turns): 2 commit(s)
    PoopToTheMoon (codex, 4 turns): 1 commit(s)
    deckard (claude, 40 turns): 2 commit(s)
    deckard (claude, 87 turns): 1 commit(s)
    voxxy (claude, 40 turns): 1 commit(s)
    deckard (claude, 33 turns): 2 commit(s)
    deckard (claude, 19 turns): 1 commit(s)
    deckard (claude, 8 turns): 1 commit(s)
    deckard (claude, 8 turns): 2 commit(s)
    deckard (claude, 112 turns): 3 commit(s)
  
  === Operational notes ===
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
    [wax] started: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] started: (no detail)
    [wax] updated: (no detail)
    ... showing 20 of 62 operational events
  
  === Git log by repository ===
  === 33GOD ===
    0121135 fix(platform): project bloodbank.evt.> and pin the publisher-enabling submodules
    9b3cf0a chore(journal): backfill 2026-08-17 developer journal
  
  === james-brennan ===
    9c28a7d chore(ledger): decision events from the JIMB-155 inventory pass
    47175e3 chore(ledger): JIMB-155 — record the close-gate pass
    2b5cdc1 feat(inventory): JIMB-155 — a component ledger that notices, and the skill that keeps it current
    219796e fix(mirror): JIMB-153 — the alarm now reaches a human; JIMB-142 re-verified at the wake
    2b2c4b3 fix(mirror): JIMB-142 — brennan/prod counts its nights in America/New_York
    7d3b046 feat(mirror): JIMB-153 — alarm on the age of the newest proof, not on a success
  
  === intelliforia ===
    (checked out: design/admin-portal-overhaul; 8 of 11 commit(s) below are not reachable from it)
    2060594b Deploy coverage report from run 1268 6bec91ccc30fa825300038247966e66af1d49a73  [not reachable from design/admin-portal-overhaul]
    6bec91cc VAL-037: replace same-day sig check with 30-day window (#721)
    7cd8deb2 Deploy coverage report from run 1266 0a72a723a99c70a020314ad2b001d9df7596c9a1  [not reachable from design/admin-portal-overhaul]
    0a72a723 Add bulk provider CSV import endpoint and UI (#720)
    f7830f2f docs(stories): record Epic 37 — admin portal design system  [not reachable from design/admin-portal-overhaul]
    1faddb09 feat(portal): convert the providers roster to the new shell (Epic 37 phase 4)  [not reachable from design/admin-portal-overhaul]
    7bd92bf3 feat(portal): merge both dashboards into one Overview (Epic 37 phase 4)  [not reachable from design/admin-portal-overhaul]
    4b957bc3 Deploy coverage report from run 1262 ca78ac1bbfe471dd161675755877a0ae34efa69e  [not reachable from design/admin-portal-overhaul]
    ca78ac1b Add source doc viewer and manual-only UI gating (#719)
    956fbbcf feat(portal): convert the notes list to the new shell, and make its filters work  [not reachable from design/admin-portal-overhaul]
    d693dabe feat(portal): convert note detail to the new shell (Epic 37 phase 4)  [not reachable from design/admin-portal-overhaul]
  
  === delonet-company ===
  (no commits)
  
  === PoopToTheMoon ===
    1bdb3a0 docs(gdd): budget five altitude bands
  
  === pjangler ===
    (checked out: feat/PJAN-77-project-notebook; 5 of 5 commit(s) below are not reachable from it)
    fbf28fe fix(PJAN-67): harden crash recovery and template execution  [not reachable from feat/PJAN-77-project-notebook]
    74bd682 fix(PJAN-67): attest immutable Hermes execution tree  [not reachable from feat/PJAN-77-project-notebook]
    c648f93 fix(PJAN-67): make fleet data lifecycle fail closed  [not reachable from feat/PJAN-77-project-notebook]
    457142d fix(PJAN-67): close fleet environment execution paths  [not reachable from feat/PJAN-77-project-notebook]
    3eacb85 fix(PJAN-67): attest fleet parser lifecycle boundary  [not reachable from feat/PJAN-77-project-notebook]
  
  === bloodbank ===
    36023b6 feat(agent-hooks): add forward_envelope for pre-built CloudEvents
  
  === candystore ===
    20e887a fix(ingest): subscribe to bloodbank.evt.> so v2 events are projected
  
  === holocene ===
  (no commits)

HERMES FLEET HEALTH
-------------------
**Status (authoritative): complete**

Hermes fleet: 28 agents registered; 9 timers (9 active, 0 failed); 3 cron jobs across 3 profiles (3 enabled); 1 job(s) reference a missing skill; 0 profile(s) with a stale ticker; 5 gateway unit(s) not running.
Metrics: agent_profile_dirs_missing=0, agents_registered=28, cron_jobs_enabled=3, cron_jobs_total=3, cron_jobs_unreadable=0, duplicate_cron_dirs=1, gateway_units_inactive=2, gateway_units_unknown=3, jobs_claiming_ok_contradicted=1, jobs_claiming_ok_unverified=2, jobs_with_missing_skill=1, jobs_with_past_next_run=0, profiles_scanned=35, profiles_unreadable_jobs=0, profiles_with_cron_jobs=3, profiles_with_stale_ticker=0, profiles_without_cron_dir=0, report_date=2026-08-18, sources_failed=0, sources_read=4, timers_active=9, timers_failed=0, timers_never_triggered=0, timers_total=9, timers_without_next_elapse=8, units_failed=0, units_not_found=1, units_total=46
Caveats:
  2 cron job(s) report last_status='ok' with no independent corroboration; last_status is a scheduler claim and is not treated as evidence of success
  1 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-08-19T16:45:01.471352Z (fleet state is current, not reconstructed for the report date)
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
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-08-19T10:02:14.142005Z, next 2026-08-20T10:00:00Z
    job 33god-pm.bak/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-08-19T10:02:14.142005Z, next 2026-08-20T10:00:00Z
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='ok' (claim, contradicted), last run 2026-08-19T13:12:56.292440Z, next 2026-08-20T13:00:00Z; skill(s) not installed: obsidian, llm-wiki

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 2 tick(s) across 1 of 1 tracked repositories on 2026-08-18; 2 PR(s) triaged, 2 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=2, merge_candidates=2, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=0, prs_triaged=2, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=0, ticks_in_window=2, ticks_noop=0
Caveats:
  pr-crusher did not publish 2 lifecycle event(s) to Bloodbank (skipped: publisher disabled); this activity is absent from Candystore and was read from pr-crusher's durable state instead
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-08-18T04:00:00Z .. 2026-08-19T04:00:00Z for 2026-08-18 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 0
    tick 21 tick-000021-20260818T070849.890593Z completed=2026-08-18T07:09:08.726514Z provider=opencode provider_status=complete result_status=complete success=True automerge=False
      PR #111 ci=success coverage=pass grade=good disposition=keep mergeable=True draft=False threads_resolved=True head=e2e916a115af
      PR #115 ci=success coverage=gap grade=good disposition=keep mergeable=True draft=False threads_resolved=True head=4b051923b344
      merge gate PR #111 allowed=False attempted=False reasons: automerge disabled; coverage is not holding
      merge gate PR #115 allowed=False attempted=False reasons: automerge disabled; coverage is not holding
      summary: Analysis-only tick (auto-merge disabled, no side effects permitted). Triaged 2 open PRs from RUNNER-VERIFIED evidence. #115 (feat: pos param on card creation) is a keep/good — competent mechanical 1:1 parameter forwarding matching existing update_card_details/move_card pos semantics, but widens the floor rather than raising the North-Star ceiling, and ships new behavior with NO tests (coverage gap... (clipped from 975 chars)
    tick 22 tick-000022-20260818T211024.481724Z completed=2026-08-18T21:11:04.075708Z provider=opencode provider_status=complete result_status=complete success=True automerge=False
      PR #111 ci=green coverage=tests_added grade=good disposition=keep mergeable=True draft=False threads_resolved=True head=e2e916a115af
      PR #115 ci=green coverage=no_new_tests grade=good disposition=keep mergeable=True draft=False threads_resolved=True head=4b051923b344
      merge gate PR #111 allowed=False attempted=False reasons: automerge disabled; CI is not successful; coverage is not holding
      merge gate PR #115 allowed=False attempted=False reasons: automerge disabled; CI is not successful; coverage is not holding
      summary: Analysis-only tick (auto-merge disabled; no side effects permitted per HARD RUNNER CONTRACT). Triaged 2 open PRs from runner-verified evidence only. #111 (fix: unref health monitor interval, #92) — keep/good: high-impact bug fix with tests, CI green, mergeable, blocked only on REVIEW_REQUIRED; highest-priority actionable (oldest, has tests, lowest risk). #115 (feat: pos param on card creation) — k... (clipped from 661 chars)
      note: PR #111 triaged: keep/good. Fixes #92 (orphaned stdio processes from a referenced setInterval never unref'd/cleared). Stores handle, unref's it, adds stopPerformanceMonitoring(). Ships with tests (tests/unit/health-monitor-timer.test.ts, 43 lines). CI: GitGuardian SUCCESS. Mergeable, not draft. reviewDecision REVIEW_REQUIRED, no reviews submitted (the gemini-code-assist comment is a sunset notice,... (clipped from 627 chars)
      note: PR #115 triaged: keep/good. Adds optional pos (top/bottom/positive number) to add_card_to_list and add_cards_to_list, forwarded to POST /cards via TrelloClient. Mechanical 1:1 param mapping — widens the floor of exposed endpoints, does not raise the North-Star ceiling (no opinionated workflow encapsulation). CI: GitGuardian SUCCESS. Mergeable, not draft. reviewDecision REVIEW_REQUIRED, no reviews.... (clipped from 568 chars)
      note: No mutating actions emitted: HARD RUNNER CONTRACT forbids all side effects (no reviews, comments, labels, merges, pushes, file writes). Both PRs are blocked only on REVIEW_REQUIRED; a single approving review would unblock each toward merge, but cannot be submitted in analysis-only mode. Recommend next non-analysis tick submit APPROVE reviews for #111 (tests present, low risk) and, after a coverage... (clipped from 412 chars)

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: DELIVERY DEGRADED -- 6 of 7 due day(s) in 2026-08-12..2026-08-18 have no valid published report (5 missing, 1 invalid); 2 day(s) carry a completion event with no archived report -- an earlier run reported success it did not achieve. 1 of 7 due days delivered over 2026-08-12..2026-08-18 (6 gap(s)); 7 completion event(s), 2 archive/event disagreement(s); delivered streak 1.
Metrics: archive_event_disagreements=2, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=1, days_archive_without_event=0, days_checked=7, days_delivered=1, days_event_without_archive=2, days_in_progress=0, days_invalid=1, days_missing=5, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=6, delivery_health=degraded, events_found=7, lookback_days=7
Caveats:
  DELIVERY DEGRADED: 6 of 7 due day(s) in 2026-08-12..2026-08-18 have no valid published report (5 missing, 1 invalid)
  DELIVERY DEGRADED: 2 day(s) carry a completion event with no archived report -- an earlier run reported success it did not achieve
  duplicate completion events for 2026-08-16, 2026-08-17; more than one run claimed the same day
  DISAGREEMENT 2026-08-16 published-but-never-archived (event-without-archive): 2 completion event(s) claim status complete, but the archive says missing -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-08-17 published-but-never-archived (event-without-archive): 4 completion event(s) claim status complete, but the archive says invalid -- an earlier run reported success it did not achieve
Detail:
  window 2026-08-12..2026-08-18 (7 days), report_date 2026-08-18
  delivery health degraded: 6 of 7 due day(s) in 2026-08-12..2026-08-18 have no valid published report (5 missing, 1 invalid); 2 day(s) carry a completion event with no archived report -- an earlier run reported success it did not achieve
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.v1.reporting.report.completed: reachable
  2026-08-12 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-12
  2026-08-13 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-13
  2026-08-14 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-14
  2026-08-15 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-15
  2026-08-16 missing events=2 claimed=complete cross_check=published-but-never-archived reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-16
  2026-08-17 invalid events=4 claimed=complete cross_check=published-but-never-archived generation=14844fcd69ad47fb9adf2860f203c489 reason=report.json is invalid: DailyReport sections must be exactly ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery'], got ['executive-brief', 'key-changes', 'risks-watchlist', 'coverage-freshness', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery']
  2026-08-18 delivered events=1 claimed=complete generation=040264346dd146f6be042bcf715d6f0d
  DISAGREEMENT 2026-08-16 published-but-never-archived (event-without-archive): 2 completion event(s) claim status complete, but the archive says missing -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-08-17 published-but-never-archived (event-without-archive): 4 completion event(s) claim status complete, but the archive says invalid -- an earlier run reported success it did not achieve

COVERAGE
--------
4 of 4 enabled sections completed.
No section is degraded.

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | complete | 2026-08-19T16:45:01.465048Z | 2026-08-20T16:45:01.465048Z | - |
| fleet-health | complete | 2026-08-19T16:45:01.471352Z | 2026-08-20T16:45:01.471352Z | - |
| pr-maintenance | complete | 2026-08-19T16:45:01.513788Z | 2026-08-20T16:45:01.513788Z | - |
| report-delivery | complete | 2026-08-19T16:45:01.526872Z | 2026-08-20T16:45:01.526872Z | - |
Required: dev-activity (complete), report-delivery (complete).
Overall status complete is derived from the run manifest above, not asserted.

Run ddr-2026-08-18-a7a9e553 · generated 2026-08-19T16:45:30.638067Z · overall status: complete
