Daily Developer Report — 2026-09-01
Summary written by anthropic/claude-opus-5. Everything below it is rendered by the pipeline from files it read — every status, metric and caveat is on this page whether or not a model answered.

SUMMARY
-------
**PJangler took 50 of the day's 93 commits and moved from story 1.1 to a finished story 1.5 — and almost every one of those stories needed a review pass to catch a gate that was reporting success it hadn't earned.**

## What happened

### Fleet convergence in `pjangler` (PJAN-86 → PJAN-100)

The epic-1 fleet convergence work ran end to end. Story 1.1 landed the fleet authority and managed-state contract (`f214d24`, `c5b1cd5`), 1.2 built registry-wide fleet inventory and identity-conflict detection (`95efa13`), 1.3 reported fleet provenance through the shared CLI and MCP (`3239f52`), 1.4 delivered parse-safe registry-wide fleet status (`ff6e1bf`), and 1.5 made partial fleet health truthful and actionable (`9976655`, finalized in `c5acc06`).

The adversarial review layer did real work rather than rubber-stamping. `a72c06b` says it plainly — "the baseline was lying, and the policy stage had no test." `be63c54` closes PJAN-95 review pass 2 on "bounds, filters, and a gate that was lying." `427a654` was 18 patches with 9 deferred; `7a348b4` was 22 patches with 9 mutation-verified. `002b9df` (PJAN-100) stopped counting test-fixture copies of `src` as coverage, and `b5ee2c3` gave the bundle-size gate a real ceiling after `8c839ca` dropped sourcemaps from the published tarball. Five `chore(release): v1.4.4 [skip ci]` commits fired for one version number.

`33GOD` itself only moved gitlinks — all five commits (`d3a25c6`, `f13b004`, `2bbc368`, `c091266`, `c7161a3`) are submodule bumps tracking pjangler's story progression.

### Cartesia voice agents in `james-brennan`

35 commits, second-heaviest repo. `6305953` merged `feat/248-cartesia-agents` for JIMB-250. The theme was making the voice agent behave under real call conditions: `55fef7a` speak through slow model turns, `24cbe3e` preserve work through hold backchannels, `49e53fc` let the conversation model speak, `ee145b5` prewarm candidate rollover. `4c67446` redacted Cartesia call credentials from logs; `88dc7db` exposed authenticated field-ops MCP tools. `64fecb3` added evidence-ranked visit matching with price-outlier flags. `da4ea57` (Workflow 1 closeout readiness gate) is not reachable from `main`.

### Elsewhere

`intelliforia` had 4 commits, all off the checked-out `docs/epic-40-two-factor-authentication` branch — `2f14ecd6` landed a rule catalog per code, Account Owner role and one scoring standard (#738). `bloodbank`, `candystore`, `holocene`, `delonet-company` and `PoopToTheMoon` were silent.

## Needs you

- **`hermes-automatic-ai-pm-heartbeat.service` is loaded/failed.** That agent's heartbeat is not running.
- **The JIMB board-clearing heartbeat is erroring every 10 minutes** because the `momo` skill is not installed in `james-brennan-pm`. It will keep failing on schedule until installed.
- **`delodocs-triage-second-pass` claims `last_status='ok'` but that claim is contradicted** — `obsidian` and `llm-wiki` are not installed. It reports success while missing its tools.
- **8 gateway units are not running**: 6 unknown to systemd (`delonet-director`, `drumjangler-pm`, `hermes-agent-pm`, `intelliforia-voice-agent-pm`, `nautilus-trader-pm`, `ssbnk-pm`) and 2 inactive (`condaleeza`, `delocontainers-pm`). `hermes-tonnybox-pm-consumer.service` is not-found.
- **Report delivery is degraded**: 2026-08-26 has no published report and no staged generation. 5 of 6 due days delivered.
- **pr-crusher's only tick failed** — tick 36 on `delorenj/mcp-server-trello`, provider `opencode_free` did not produce a schema-valid result. 0 PRs triaged.
- **`33god-pm.bak` shares its cron dir with `33god-pm`**, so `delonet-daily-report` is registered twice with identical last-run timestamps.

## Worth noting

**Zero decisions were recorded** across 13,472 events and 174 sessions. Every architectural call made in those pjangler review passes exists only as a commit subject.

15 of 18 active projects have no configured git root — `feat-cartesia-agents` alone generated 1,963 events with no repo read. Peak hour was 04:00 UTC at 1,578 events, which is overnight loop work, not you.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): complete**

13472 events across 18 project(s) on 2026-09-01: 174 session(s), 0 decision(s), 21 committing session(s), 93 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (88 on the checked-out branch, 5 only on other refs); peak 2026-09-01T04:00:00Z (1578 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=21, decision_count=0, event_count=13472, git_commit_count=93, git_commit_replays_collapsed=0, git_commits_off_head=5, git_commits_on_head=88, git_repos_failed=0, git_repos_logged=4, git_repos_missing=0, git_repos_no_commits=5, git_repos_with_off_head_commits=2, git_root_name_collisions=0, git_roots_active_in_events=3, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=True, peak_hour=2026-09-01T04:00:00Z, peak_hour_event_count=1578, project_count=18, projects_without_root=15, session_count=174
Caveats:
  projects truncated: showing 20 of 22
  git scope is 'all-refs': every ref of each configured repository was read for 2026-09-01 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  5 configured project root(s) were read across all refs of each repository and had no commits on 2026-09-01: delonet-company, PoopToTheMoon, bloodbank, candystore, holocene
  5 of 93 commit(s) are not reachable from their repository's checked-out branch (unmerged or otherwise off-HEAD work) and are counted here: james-brennan 1 of 35 (checked out: main), intelliforia 4 of 4 (checked out: docs/epic-40-two-factor-authentication)
  15 project(s) active in events have no configured project root, so no git log was read for them: .agents, DeLoContainers, agents, automatic-ai, bmad-loop-setup, client-portal, f1776ae630fee7445826, feat-cartesia-agents, and 7 more
Detail:
  === Events by CLI ===
    claude      10084
    codex        2263
    hermes       1052
    unknown        72
    reportctl       1
  
  === Events by project ===
    pjangler                8901
    feat-cartesia-agents    1963
    unknown                 1119
    newapi                   674
    james-brennan            269
    automatic-ai             246
    memories                  74
    .agents                   66
    repo                      54
    project-fuckudeer         32
    stories                   19
    james-brennan.git         16
    pjangler.git              15
    wax                       12
    DeLoContainers.git         2
    hermes-agent               2
    f1776ae630fee7445826       2
    bmad-loop-setup            2
    agents                     1
    client-portal.git          1
    ... showing 20 of 22 projects
  
  === Decisions recorded ===
    (no recorded decisions)
  
  === Sessions that committed ===
    pjangler (claude, 71 turns): 4 commit(s)
    pjangler (claude, 138 turns): 1 commit(s)
    pjangler (claude, 65 turns): 4 commit(s)
    pjangler (claude, 113 turns): 1 commit(s)
    pjangler (claude, 15 turns): 1 commit(s)
    pjangler (claude, 26 turns): 1 commit(s)
    pjangler (claude, 29 turns): 1 commit(s)
    pjangler (claude, 15 turns): 1 commit(s)
    pjangler (claude, 12 turns): 1 commit(s)
    pjangler (claude, 19 turns): 1 commit(s)
    pjangler (claude, 268 turns): 1 commit(s)
    pjangler (claude, 257 turns): 1 commit(s)
    pjangler (claude, 178 turns): 1 commit(s)
    pjangler (claude, 43 turns): 1 commit(s)
    pjangler (claude, 188 turns): 2 commit(s)
    pjangler (claude, 47 turns): 1 commit(s)
    pjangler (claude, 96 turns): 2 commit(s)
    pjangler (claude, 12 turns): 1 commit(s)
    pjangler (claude, 159 turns): 1 commit(s)
    pjangler (claude, 150 turns): 1 commit(s)
    pjangler (codex, 0 turns): 1 commit(s)
  
  === Operational notes ===
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
  
  === Git log by repository ===
  === 33GOD ===
    d3a25c6 chore(PJAN-96): bump pjangler to story 1.5 final (review pass complete)
    f13b004 chore(PJAN-96): bump pjangler to story 1.5 (truthful, actionable health)
    2bbc368 chore(PJAN-95): advance pjangler to story 1.4 review pass 2
    c091266 chore(33GOD): bump pjangler gitlink to the story 1.3 review pass
    c7161a3 chore: advance pjangler to 3239f52 (story 1.3 fleet provenance)
  
  === james-brennan ===
    (checked out: main; 1 of 35 commit(s) below are not reachable from it)
    da4ea57 feat(surface): add Workflow 1 closeout readiness gate  [not reachable from main]
    8fa48e6 chore(devops): mirror capture at 64fecb3
    df1656e chore(devops): taskdefs at 64fecb3
    a02884b docs: describe evidence-ranked Field Ops matching
    64fecb3 feat(voice): rank visit evidence and flag price outliers
    16a09b8 chore(devops): taskdefs at 18bf068
    86b068a docs: describe Field Ops knowledge and memory architecture
    18bf068 feat(voice): add curated knowledge and scoped memory
    f64c3ee chore(devops): taskdefs at ee145b5
    ee145b5 fix(voice): prewarm candidate rollover
    058f87f docs: update Field Ops agent architecture
    4a3c10d chore(devops): taskdefs at 49e53fc
    7715ab7 test(technician): accept model-authored closeout speech
    49e53fc fix(voice): let the conversation model speak
    e405011 fix(voice): rail identity confirmation
    9850ec1 test(technician): acknowledge field ops hold cue
    33631ed checkpoint: 2026-09-01T03:03:09Z auto-commit
    0bbf4c5 fix(surface): open Cartesia call transcripts
    19dd416 chore(devops): taskdefs at 24cbe3e
    24cbe3e fix(voice): preserve work through hold backchannels
    7a2137b chore(devops): taskdefs at 55fef7a
    55fef7a fix(voice): speak through slow model turns
    8c07c93 test(technician): add JIMB-250 partial-address call
    c65403c chore(devops): mirror capture at 6305953
    595410f chore(devops): taskdefs at 6305953
    6305953 Merge feat/248-cartesia-agents for JIMB-250
    18a59a1 chore(technician): refresh voice dependency lock
    df3cab4 chore(voice): wire field ops MCP credential
    88dc7db feat(voice): expose authenticated field ops MCP tools
    4c67446 fix(voice): redact Cartesia call credentials from logs
    4e81546 perf(voice): warm candidate snapshot before calls
    b15a8e7 feat(mirror): project technician visit assignments
    3bd1864 Merge branch 'main' into feat/248-cartesia-agents
    d743bb3 chore(devops): preserve feature checkpoint taskdefs
    62753b9 feat(voice): add light-rails field ops controller
  
  === intelliforia ===
    (checked out: docs/epic-40-two-factor-authentication; 4 of 4 commit(s) below are not reachable from it)
    18c75113 docs(stories): re-anchor Epic 40 line references after main moved  [not reachable from docs/epic-40-two-factor-authentication]
    1b1dfb56 Merge remote-tracking branch 'origin/main' into docs/epic-40-two-factor-authentication  [not reachable from docs/epic-40-two-factor-authentication]
    3f430b6a Deploy coverage report from run 1330 2f14ecd6a4c785f585aeea9c4303933dd81b0671  [not reachable from docs/epic-40-two-factor-authentication]
    2f14ecd6 Rule catalog per code, Account Owner role, one scoring standard, internal score digest (#738)  [not reachable from docs/epic-40-two-factor-authentication]
  
  === delonet-company ===
  (no commits)
  
  === PoopToTheMoon ===
  (no commits)
  
  === pjangler ===
    2779fd4 chore(release): v1.4.4 [skip ci]
    c5acc06 docs(PJAN-96): finalize story 1.5 — review triage, result, deferred work
    ae9606e chore(release): v1.4.4 [skip ci]
    8763986 fix(PJAN-96): a conflict ruling authorizes the observation, not the row (DW-81)
    a72c06b fix(PJAN-96): review pass 1 — the baseline was lying, and the policy stage had no test
    0c4c4a9 chore(release): v1.4.4 [skip ci]
    2dc20d7 docs(PJAN-96): state the output/health import cycle from each file's own side
    b5ee2c3 fix(PJAN-96): stop publishing sourcemaps and give the size gate a real ceiling
    8c839ca build(PJAN-96): drop sourcemaps from the published tarball (DW-7)
    2b17c23 chore(release): v1.4.4 [skip ci]
    8d5256f fix(PJAN-96): resolve row classification from the contract's DECLARED entries
    58f90ea chore(release): v1.4.4 [skip ci]
    9976655 feat(PJAN-96): make partial fleet health truthful and actionable
    fd41cff chore(release): v1.4.4 [skip ci]
    002b9df fix(PJAN-100): stop counting test fixture copies of src as coverage
    fc0b482 docs(PJAN-96): plan story 1.5 — truthful, actionable partial health
    d5caa98 chore(PJAN-95): bank story 1.4 done
    be63c54 fix(PJAN-95): review pass 2 — bounds, filters, and a gate that was lying
    5f27761 fix(PJAN-98): make the pjan-67 ordering check state what it means
    91e2128 fix(PJAN-98): honour -o/-D/-w in both plane curl stubs
    3ce86ec fix(PJAN-97): run the pipefail probes under bash, not sh
    f4066f2 feat(PJAN-95): land story 1.4 dev output stalled by an API 529
    b344f9b test(PJAN-95): cover MCP cancellation on the status command's own children
    ff6e1bf feat(PJAN-95): story 1.4 — parse-safe registry-wide fleet status
    7b9a1c3 docs(PJAN-95): plan story 1.4 — parse-safe registry-wide fleet status
    564d40b chore(PJAN-94): bank story 1.3 done after its review pass
    427a654 fix(PJAN-94): story 1.3 review pass — 18 patches, 9 deferred
    06287ec chore(PJAN-94): land story 1.3 dev handoff and raise the session timeout
    3239f52 feat(PJAN): story 1.3 — report fleet provenance through shared CLI and MCP
    25fb406 merge(PJAN-93): reconcile the orchestrator's squash with the pushed history
    6064d8e story 1-2-discover-the-complete-fleet-and-detect-identity-conflicts: implemented and reviewed via bmad-loop
    3500e02 chore(PJAN-93): land the orchestrator's ledger sync and token ceiling
    7a348b4 fix(PJAN-93): second review pass on story 1.2 -- 22 patches, 9 mutation-verified
    88ffd1b fix(PJAN-93): close the story 1.2 review pass
    caf3878 docs(PJAN-92): pin that a scoped inventory reports FLEET health, not slice health
    95efa13 feat(PJAN-92): story 1.2 -- registry-wide fleet inventory and identity conflicts
    9f0693e chore(PJAN-92): bank story 1.1 done and its deferred ledger
    a57a62f fix(PJAN-92): remove the second guard-disabling NUL, in src/project/identity.ts
    aa7e4dd fix(PJAN-92): close the story 1.1 review pass
    e728540 fix(PJAN-93): requeue story 1.1 so its review actually runs
    d23a305 chore(PJAN-93): record build-auto block on story 1.2 continuity gate
    e6e979b chore(PJAN-91): bank story 1.1 and give the loop room to finish a story
    c5b1cd5 feat(PJAN-92): complete the fleet authority and managed-state contract
    f214d24 feat(PJAN-91): declare the fleet authority and managed-state contract
    0319f67 docs(PJAN-91): compile epic 1 fleet convergence developer context
    6f2d816 docs(PJAN-91): plan sprint 1 of the fleet convergence epic
    07afa0d chore(PJAN-90): upgrade the bmad-loop harness to 0.11.1
    76deb14 test(PJAN-89): isolate the parity suite from the real mise trust store
    04c7ef8 docs(PJAN-86): plan registry-wide fleet convergence epic
  
  === bloodbank ===
  (no commits)
  
  === candystore ===
  (no commits)
  
  === holocene ===
  (no commits)

HERMES FLEET HEALTH
-------------------
**Status (authoritative): complete**

Hermes fleet: 28 agents registered; 15 timers (15 active, 0 failed); 4 cron jobs across 4 profiles (4 enabled); 2 job(s) reference a missing skill; 0 profile(s) with a stale ticker; 8 gateway unit(s) not running.
Metrics: agent_profile_dirs_missing=0, agents_registered=28, cron_jobs_enabled=4, cron_jobs_total=4, cron_jobs_unreadable=0, duplicate_cron_dirs=1, gateway_units_inactive=2, gateway_units_unknown=6, jobs_claiming_ok_contradicted=1, jobs_claiming_ok_unverified=2, jobs_with_missing_skill=2, jobs_with_past_next_run=0, profiles_scanned=39, profiles_unreadable_jobs=0, profiles_with_cron_jobs=4, profiles_with_stale_ticker=0, profiles_without_cron_dir=1, report_date=2026-09-01, sources_failed=0, sources_read=4, timers_active=15, timers_failed=0, timers_never_triggered=0, timers_total=15, timers_without_next_elapse=0, units_failed=1, units_not_found=1, units_total=59
Caveats:
  2 cron job(s) report last_status='ok' with no independent corroboration; last_status is a scheduler claim and is not treated as evidence of success
  1 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-09-02T10:01:01.191332Z (fleet state is current, not reconstructed for the report date)
  registry: 28 agents, 0 missing profile dir(s), 6 gateway unit(s) unknown to systemd, 2 not active
    agent condaleeza: hermes-condaleeza-gateway.service not active
    agent delocontainers-pm: hermes-delocontainers-pm-gateway.service not active
    agent delonet-director: hermes-delonet-director-gateway.service unknown to systemd; hermes-delonet-director-heartbeat.timer unknown to systemd
    agent drumjangler-pm: hermes-drumjangler-pm-gateway.service unknown to systemd
    agent hermes-agent-pm: hermes-hermes-agent-pm-gateway.service unknown to systemd
    agent intelliforia-voice-agent-pm: hermes-intelliforia-voice-agent-pm-gateway.service unknown to systemd
    agent nautilus-trader-pm: hermes-nautilus-trader-pm-gateway.service unknown to systemd
    agent ssbnk-pm: hermes-ssbnk-pm-gateway.service unknown to systemd
  systemd units: 59 matching, 1 failed, 1 not-found
    unit hermes-automatic-ai-pm-heartbeat.service: loaded/failed/failed
    unit hermes-tonnybox-pm-consumer.service: not-found/inactive/dead
  timers: 15 matching, 15 active, 0 failed, 0 with no next elapse, 0 never triggered
  cron: 39 profiles scanned (1 without a cron dir), 4 with jobs, 4 jobs (4 enabled), 0 stale ticker(s), 1 shared cron dir(s)
    profile 33god-pm.bak: shares its cron dir with 33god-pm
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-09-01T10:03:15.219087Z, next 2026-09-03T10:00:00Z
    job 33god-pm.bak/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-09-01T10:03:15.219087Z, next 2026-09-03T10:00:00Z
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='ok' (claim, contradicted), last run 2026-09-01T13:10:36.638554Z, next 2026-09-02T13:00:00Z; skill(s) not installed: obsidian, llm-wiki
    job james-brennan-pm/JIMB board-clearing heartbeat: enabled, schedule 'every 10m', last_status='error' (claim, not-claimed), last run 2026-09-02T09:57:44.779774Z, next 2026-09-02T10:07:44.779774Z; skill(s) not installed: momo; last_error recorded (142 chars, not copied here)

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 1 tick(s) across 1 of 1 tracked repositories on 2026-09-01; 0 PR(s) triaged, 0 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged; 1 tick(s) did not succeed.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=0, merge_candidates=0, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=0, prs_triaged=0, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=1, ticks_in_window=1, ticks_noop=0
Caveats:
  pr-crusher activity is read from its durable state, not Candystore: its Bloodbank publisher has been observed disabled, so absence of PR events on the bus does not mean absence of PR activity
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-09-01T04:00:00Z .. 2026-09-02T04:00:00Z for 2026-09-01 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 0
    tick 36 tick-000036-20260901T071233.403147Z completed=2026-09-01T07:13:13.008479Z provider=opencode_free provider_status=failed result_status=failed success=False automerge=False
      summary: provider did not produce a schema-valid tick result

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: DELIVERY DEGRADED -- 1 of 6 due day(s) in 2026-08-26..2026-09-01 have no valid published report (1 missing). 5 of 6 due days delivered over 2026-08-26..2026-09-01 (1 gap(s)); 5 completion event(s), 0 archive/event disagreement(s); delivered streak 5.
Metrics: archive_event_disagreements=0, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=5, days_archive_without_event=0, days_checked=7, days_delivered=5, days_event_without_archive=0, days_in_progress=1, days_invalid=0, days_missing=1, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=1, delivery_health=degraded, events_found=5, lookback_days=7
Caveats:
  DELIVERY DEGRADED: 1 of 6 due day(s) in 2026-08-26..2026-09-01 have no valid published report (1 missing)
Detail:
  window 2026-08-26..2026-09-01 (7 days), report_date 2026-09-01
  delivery health degraded: 1 of 6 due day(s) in 2026-08-26..2026-09-01 have no valid published report (1 missing)
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.reporting.report.completed: reachable
  2026-08-26 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-26
  2026-08-27 delivered events=1 claimed=complete generation=1472ef2e152c42aa94012cce38fb34ba
  2026-08-28 delivered events=1 claimed=complete generation=001568c972584cae9965b922dcef9126
  2026-08-29 delivered events=1 claimed=complete generation=e841776cf5764df5ad7cfca76f89fbbd
  2026-08-30 delivered events=1 claimed=complete generation=41135b0df7434d658f7b5bd65924f82b
  2026-08-31 delivered events=1 claimed=complete generation=a812ccd90e1f4a33b4c9bc5191fb4550
  2026-09-01 in-progress events=0 reason=this run is producing this day; it publishes after collection

COVERAGE
--------
4 of 4 enabled sections completed.
No section is degraded.

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | complete | 2026-09-02T10:01:01.184562Z | 2026-09-03T10:01:01.184562Z | - |
| fleet-health | complete | 2026-09-02T10:01:01.191332Z | 2026-09-03T10:01:01.191332Z | - |
| pr-maintenance | complete | 2026-09-02T10:01:01.245980Z | 2026-09-03T10:01:01.245980Z | - |
| report-delivery | complete | 2026-09-02T10:01:01.267112Z | 2026-09-03T10:01:01.267112Z | - |
Required: dev-activity (complete), report-delivery (complete).
Overall status complete is derived from the run manifest above, not asserted.

Run ddr-2026-09-01-e28b33f7 · generated 2026-09-02T10:01:47.620558Z · overall status: complete
