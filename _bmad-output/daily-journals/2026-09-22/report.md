Daily Developer Report — 2026-09-22
Summary written by anthropic/claude-opus-5. Everything below it is rendered by the pipeline from files it read — every status, metric and caveat is on this page whether or not a model answered.

SUMMARY
-------
**The invoicing work in `james-brennan` and `intelliforia` is the day — 80 commits across the 5 repositories that moved, with 33 of them still not reachable from a checked-out branch.**

## What happened

### Invoicing and billing paths got fixed end to end
`james-brennan` carried 52 commits, the bulk of the day. The invoice line went from broken to composable: `b9e8378a` shipped the tax rules "without which no invoice can ever compose", `ed96a131` re-bound the testbed tax rule to the live location digest, and `2672d7cb` fixed a VOICE image that had the env var instead of the file. Ticket work: `f477049b` (JIMB-361) stops a tax rule expiring on the next job booked at the address; `7507b2c3` (JIMB-359) makes one phone call one Engine Room row; `81def411` (JIMB-357) reclassifies a post-commit exception as pending rather than a tool error; `d6b7380d` and `32eeb009` (JIMB-360) refuse a repair reading the wrong kill switch and retire undeliverable outbox commands. `a71915cb` (JIMB-350) added one test per write-path safeguard nothing was watching.

In `intelliforia`, INT-180 internal monthly provider invoicing landed as `2b5c78b3` (#767) after six off-main fixes — including `6c362fc4`, where a caveat switched itself off in October and a JSON `true` priced everyone at a cent. Separately `b5498035` closed INT-259: the admin gate sat inside the cached region, so a cache HIT skipped it.

### Agent plumbing: the Plane bridge came out
`bloodbank` `fbf61a9` and `holocene` `3e7337f` deleted the retired Plane webhook bridge and its HQ controls, while `33GOD` `5bb7a97` documents that ticket facts come only from the Plane webhook. Hook-hub gained layered recall (`b048a0c`, FLUME-18/19) and per-person-and-project session retention (`de36485`, FLUME-20); three no-op hermes hooks were dropped.

## Needs you

- **PR maintenance is dead, not idle.** The single tick on `delorenj/mcp-server-trello` failed: the credential broker rejected `prc_github_read_token` and `prc_github_write_token`. 0 PRs triaged. Fix the broker or nothing gets merged.
- **Report delivery is degraded** — 2026-09-16 and 2026-09-18 have no published report, and 2026-09-19 has duplicate completion events.
- **Developer activity is `partial`.** Pagination hit the 50-page cap at 50,000 events, so the day is not fully covered, and the Candystore heatmap endpoint timed out. 45,956 of those events landed in the 23:00Z hour alone — that spike is what blew the budget.
- **Fleet:** 9 gateway units not running, including your own `hermes-33god-pm-heartbeat.timer` (unknown to systemd). The Board Cranker loop is disabled, last ran 2026-09-05, and references 6 uninstalled skills.

## Worth noting

3,902 sessions, 0 decisions recorded. Two event-active projects (`bb`, `project`) still have no configured git root, so their commits are invisible here.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): partial** -- event pagination stopped at the 50-page budget (50000 events read); the day is not fully covered; heatmap unavailable (cannot reach http://127.0.0.1:8683/summary/heatmap?group=project&from=2026-09-22T00:00:00Z&to=2026-09-23T00:00:00Z: timed out); peak hour derived from events instead

50000 events across 4 project(s) on 2026-09-22: 3902 session(s), 0 decision(s), 4 committing session(s), 80 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (49 on the checked-out branch, 33 only on other refs); peak 2026-09-22T23:00:00Z (45956 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=4, decision_count=0, event_count=50000, git_commit_count=80, git_commit_replays_collapsed=2, git_commits_off_head=33, git_commits_on_head=49, git_repos_failed=0, git_repos_logged=5, git_repos_missing=0, git_repos_no_commits=4, git_repos_with_off_head_commits=2, git_root_name_collisions=0, git_roots_active_in_events=2, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=False, peak_hour=2026-09-22T23:00:00Z, peak_hour_event_count=45956, project_count=4, projects_without_root=2, session_count=3902
Caveats:
  git scope is 'all-refs': every ref of each configured repository was read for 2026-09-22 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  4 configured project root(s) were read across all refs of each repository and had no commits on 2026-09-22: delonet-company, PoopToTheMoon, pjangler, candystore
  33 of 82 commit(s) are not reachable from their repository's checked-out branch (unmerged or otherwise off-HEAD work) and are counted here: james-brennan 27 of 52 (checked out: main), intelliforia 6 of 9 (checked out: main)
  2 commit(s) repeat the author date and subject of another commit in the same window (rebase or cherry-pick copies) and were counted once, not twice: james-brennan 2
  2 project(s) active in events have no configured project root, so no git log was read for them: bb, project
Detail:
  === Events by CLI ===
    claude        32615
    antigravity   11447
    codex          5778
    unknown         108
    hermes           52
  
  === Events by project ===
    unknown         49370
    project           598
    intelliforia       18
    bb                 11
    james-brennan       3
  
  === Decisions recorded ===
    (no recorded decisions)
  
  === Sessions that committed ===
    project (codex, 0 turns): 2 commit(s)
    unknown (antigravity, 142 turns): 1 commit(s)
    unknown (claude, 7 turns): 6 commit(s)
    unknown (claude, 19 turns): 16 commit(s)
  
  === Operational notes ===
    (no notable operational events)
  
  === Git log by repository ===
  === 33GOD ===
    5bb7a97 docs(krebs,pm): ticket facts come only from the Plane webhook
    21a6f70 Declare the 33GOD project notebook
    924e97e chore(merge-forward): apply session tuning
    11d9852 Update flume named-agent memory support
    5f7f573 Re-enable 33god-pm grooming: make bloodbank.enabled explicit
    288e377 Bump flume: 1Password disk cache enabled fleet-wide
    154047a Bump flume: release checkouts cannot push (blobless partial clones)
    e709e0c Bump flume: fleet upgrade runbook, and the rename that revived an agent
    57078b7 Close the 7.4 finding: the drop-ins have a generator now
    dd5b2af Bump flume: the runtime drop-ins finally have a generator
    890c6bd Bump bloodbank: drop three no-op hermes hooks
    65459c5 Bump bloodbank: gemini and antigravity actually get their injected context
    314ef18 Bump bloodbank: stop sending hermes a redundant skills reminder
  
  === james-brennan ===
    (checked out: main; 27 of 52 commit(s) below are not reachable from it)
    91bfbfab chore(inventory): observed AWS services in run 35780429645 (#238)
    a7dab425 chore(inventory): observed AWS services in run 35780429645  [not reachable from main]
    a3a1c80a chore(devops): taskdefs at 7507b2c3  [not reachable from main]
    2899ffe7 chore(inventory): observed AWS services in run 35779387445 (#236)
    cd8fb73c chore(inventory): observed AWS services in run 35779387445  [not reachable from main]
    794016df chore(devops): taskdefs at 81def411 (#235)
    9941ab2b chore(devops): taskdefs at 81def411  [not reachable from main]
    7507b2c3 fix(JIMB-359): one phone call is one Engine Room row (#230)
    81def411 fix(JIMB-357): an exception past the commit is pending, not a tool error (#228)
    d4d15dd7 chore(inventory): observed AWS services in run 35777203999 (#234)
    cea15129 chore(inventory): observed AWS services in run 35777203999  [not reachable from main]
    d2a50524 chore(devops): taskdefs at a71915cb  [not reachable from main]
    d702e573 chore(inventory): observed AWS services in run 35775056895  [not reachable from main]
    7c9cc5a0 chore(devops): taskdefs at f477049b (#229)
    a536339a chore(inventory): observed AWS services in run 35772446272  [not reachable from main]
    7322f5f9 chore(devops): taskdefs at f477049b  [not reachable from main]
    015ac954 chore(inventory): observed AWS services in run 35772438448  [not reachable from main]
    a71915cb test(JIMB-350): one test per write-path safeguard nothing was watching (#226)
    82fa843f docs: correct the comments that still describe a pre-credential deployment (#225)
    7bc0769b fix(testbed): clean verifies its deletions and names what it could not remove (#224)
    f477049b fix(JIMB-361): a tax rule stops expiring on the next job booked at the address (#223)
    93700702 chore(inventory): observed AWS services in run 35756959222 (#222)
    5c664fd0 chore(inventory): observed AWS services in run 35756959222  [not reachable from main]
    2672d7cb fix(invoice): the VOICE image had the env var and not the file (#221)
    e7a25caf test(invoice): a closeout script that says nothing about tax, and a re-bind for it (#220)
    39c97bb9 chore(inventory): observed AWS services in run 35737664939 (#219)
    4e5a83d9 chore(inventory): observed AWS services in run 35737664939  [not reachable from main]
    ed96a131 fix(invoice): re-bind the testbed tax rule to the live location digest (#218)
    d2ab3548 chore(inventory): observed AWS services in run 35731875499 (#217)
    3ae9212f chore(inventory): observed AWS services in run 35731875499  [not reachable from main]
    b9e8378a fix(invoice): ship the tax rules, without which no invoice can ever compose (#216)
    8d6b6040 checkpoint: 2026-09-22T04:59:32Z auto-commit  [not reachable from main]
    18d1105b chore(inventory): observed AWS services in run 35688081088 (#215)  [not reachable from main; same author date and subject as 3a69f5d9, counted once]
    d56ef70e chore(inventory): observed AWS services in run 35685493968 (#210)  [not reachable from main; same author date and subject as 7715484e, counted once]
    3a69f5d9 chore(inventory): observed AWS services in run 35688081088 (#215)
    d768ee3d chore(inventory): observed AWS services in run 35688081088  [not reachable from main]
    19cc1553 chore(inventory): observed AWS services in run 35687369974  [not reachable from main]
    329229f2 chore(devops): taskdefs at 7b91f091  [not reachable from main]
    e3f4cdb2 docs(relay): the approve response is a snapshot of a closeout still in flight  [not reachable from main]
    7b91f091 docs: correct the closeout comments that still describe a pre-credential deployment (#211)
    c1ce11df docs(surface): the closeout's other two operations are the relay's, not another party's  [not reachable from main]
    7eddce32 docs(relay): app.py no longer claims the closeout routes to a human  [not reachable from main]
    cc8fd8f5 docs(relay,surface): correct the two comments that still describe a pre-dispatcher closeout  [not reachable from main]
    7715484e chore(inventory): observed AWS services in run 35685493968 (#210)
    4560c001 docs(relay): correct the two docstrings that still describe a pre-credential deployment  [not reachable from main]
    401037ae chore(inventory): observed AWS services in run 35685493968  [not reachable from main]
    d6b7380d fix(JIMB-360): refuse the repair when it is reading the wrong kill switch (#209)
    2598d6fe chore(inventory): observed AWS services in run 35672844027 (#208)
    287b81d2 chore(inventory): observed AWS services in run 35672844027  [not reachable from main]
    2b9e5847 chore(devops): taskdefs at 32eeb009 (#207)
    efd1bc61 chore(devops): taskdefs at 32eeb009  [not reachable from main]
    32eeb009 feat(JIMB-360): retire the outbox commands no dispatch can ever deliver (#206)
  
  === intelliforia ===
    (checked out: main; 6 of 9 commit(s) below are not reachable from it)
    2b5c78b3 feat(INT-180): internal monthly provider invoicing, and a gate on the rate setters (#767)
    581c8c37 fix(INT-180): say what the caveats survive, and pin the case they do not  [not reachable from main]
    9f51a208 fix(INT-180): the degraded page dropped the caveats it claims to render  [not reachable from main]
    2a997d60 test(INT-180): pin the caveat key spelling, or the silent lapse walks back in  [not reachable from main]
    6c362fc4 fix(INT-180): the caveat switched itself off in October, and a JSON `true` priced everyone at a cent  [not reachable from main]
    fba4dca7 fix(INT-180): re-point three rotted routes.py line anchors, and say why they rot  [not reachable from main]
    fee9d0c3 feat(INT-180): internal monthly provider invoicing, and a gate on the rate setters  [not reachable from main]
    b284796a fix(backfill): survive what heroku run actually does to the output (#763)
    b5498035 fix(security): the admin gate was inside the cached region, so a cache HIT skipped it (INT-259) (#761)
  
  === delonet-company ===
  (no commits)
  
  === PoopToTheMoon ===
  (no commits)
  
  === pjangler ===
  (no commits)
  
  === bloodbank ===
    0816415 feat(gateway): no key means enabled; invocation events echo command context
    fbf61a9 chore: delete the retired Plane webhook bridge and bb-triage-invoke
    de36485 feat(hook-hub): a session is retained into the person AND the project (FLUME-20)
    b048a0c feat(hook-hub): layered recall — the agent's memory, then the project's (FLUME-18/19)
    bef9d22 Drop three hermes hooks that spawn a process to do nothing
    97b605e Let trailer dialects actually receive the context shaped for them
    b35a055 Stop sending hermes a skills reminder it already renders better itself
  
  === candystore ===
  (no commits)
  
  === holocene ===
    3e7337f refactor(hq): drop the retired Plane webhook bridge controls

HERMES FLEET HEALTH
-------------------
**Status (authoritative): complete**

Hermes fleet: 25 agents registered; 0 timers (0 active, 0 failed); 3 cron jobs across 2 profiles (2 enabled); 2 job(s) reference a missing skill; 0 profile(s) with a stale ticker; 9 gateway unit(s) not running.
Metrics: agent_profile_dirs_missing=0, agents_registered=25, cron_jobs_enabled=2, cron_jobs_total=3, cron_jobs_unreadable=0, duplicate_cron_dirs=0, gateway_units_inactive=2, gateway_units_unknown=7, jobs_claiming_ok_contradicted=2, jobs_claiming_ok_unverified=1, jobs_with_missing_skill=2, jobs_with_past_next_run=0, profiles_scanned=37, profiles_unreadable_jobs=0, profiles_with_cron_jobs=2, profiles_with_stale_ticker=0, profiles_without_cron_dir=0, report_date=2026-09-22, sources_failed=0, sources_read=4, timers_active=0, timers_failed=0, timers_never_triggered=0, timers_total=0, timers_without_next_elapse=0, units_failed=0, units_not_found=1, units_total=20
Caveats:
  1 cron job(s) report last_status='ok' with no independent corroboration; last_status is a scheduler claim and is not treated as evidence of success
  2 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-09-23T10:03:44.621678Z (fleet state is current, not reconstructed for the report date)
  registry: 25 agents, 0 missing profile dir(s), 7 gateway unit(s) unknown to systemd, 2 not active
    agent 33god-pm: hermes-33god-pm-heartbeat.timer unknown to systemd
    agent client-portal-pm: hermes-client-portal-pm-heartbeat.timer unknown to systemd
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
  systemd units: 20 matching, 0 failed, 1 not-found
    unit hermes-tonnybox-pm-consumer.service: not-found/inactive/dead
  timers: 0 matching, 0 active, 0 failed, 0 with no next elapse, 0 never triggered
  cron: 37 profiles scanned (0 without a cron dir), 2 with jobs, 3 jobs (2 enabled), 0 stale ticker(s), 0 shared cron dir(s)
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-09-22T10:03:33.988323Z, next 2026-09-24T10:00:00Z
    job 33god-pm/Board Cranker implementation loop: disabled, schedule 'every 5m', last_status='ok' (claim, contradicted), last run 2026-09-05T12:48:43.347617Z, next none; skill(s) not installed: momo, project-lifecycle, subagent-driven-development, coding-strategy, pjangler, bloodbank-integration
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='ok' (claim, contradicted), last run 2026-09-23T06:10:20.112230Z, next 2026-09-23T13:00:00Z; skill(s) not installed: obsidian, llm-wiki

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 1 tick(s) across 1 of 1 tracked repositories on 2026-09-22; 0 PR(s) triaged, 0 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged; 1 tick(s) did not succeed.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=0, merge_candidates=0, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=0, prs_triaged=0, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=1, ticks_in_window=1, ticks_noop=0
Caveats:
  pr-crusher activity is read from its durable state, not Candystore: its Bloodbank publisher has been observed disabled, so absence of PR events on the bus does not mean absence of PR activity
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-09-22T04:00:00Z .. 2026-09-23T04:00:00Z for 2026-09-22 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 0
    tick 56 tick-000056-20260922T070006.287043Z completed=2026-09-22T07:00:09.042996Z provider=none provider_status=failed result_status=failed success=False automerge=False
      merge gate PR #None allowed=False attempted=False reasons: merge processing failed: credential broker rejected prc_github_write_token
      summary: runner/provider setup failed: credential broker rejected prc_github_read_token

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: DELIVERY DEGRADED -- 2 of 6 due day(s) in 2026-09-16..2026-09-22 have no valid published report (2 missing). 4 of 6 due days delivered over 2026-09-16..2026-09-22 (2 gap(s)); 5 completion event(s), 0 archive/event disagreement(s); delivered streak 3.
Metrics: archive_event_disagreements=0, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=3, days_archive_without_event=0, days_checked=7, days_delivered=4, days_event_without_archive=0, days_in_progress=1, days_invalid=0, days_missing=2, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=2, delivery_health=degraded, events_found=5, lookback_days=7
Caveats:
  DELIVERY DEGRADED: 2 of 6 due day(s) in 2026-09-16..2026-09-22 have no valid published report (2 missing)
  duplicate completion events for 2026-09-19; more than one run claimed the same day
Detail:
  window 2026-09-16..2026-09-22 (7 days), report_date 2026-09-22
  delivery health degraded: 2 of 6 due day(s) in 2026-09-16..2026-09-22 have no valid published report (2 missing)
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.reporting.report.completed: reachable
  2026-09-16 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/09/2026-09-16
  2026-09-17 delivered events=1 claimed=partial generation=3252122c267b4beaa3e75dde1d2f11ca
  2026-09-18 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/09/2026-09-18
  2026-09-19 delivered events=2 claimed=partial generation=527ce8a2d2f742b99a1c920c5d037f85
  2026-09-20 delivered events=1 claimed=partial generation=11f52f9cbf71413ebbc33c23c666aa20
  2026-09-21 delivered events=1 claimed=partial generation=9bae3dfec7d745dc9163e2e6b6d3b236
  2026-09-22 in-progress events=0 reason=this run is producing this day; it publishes after collection

COVERAGE
--------
3 of 4 enabled sections completed.
Degraded: dev-activity (partial).

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | partial | 2026-09-23T10:03:44.614745Z | 2026-09-24T10:03:44.614745Z | event pagination stopped at the 50-page budget (50000 events read); the day is not fully covered; heatmap unavailable (cannot reach http://127.0.0.1:8683/summar... (clipped from 284 characters) |
| fleet-health | complete | 2026-09-23T10:03:44.621678Z | 2026-09-24T10:03:44.621678Z | - |
| pr-maintenance | complete | 2026-09-23T10:03:44.699819Z | 2026-09-24T10:03:44.699819Z | - |
| report-delivery | complete | 2026-09-23T10:03:44.723442Z | 2026-09-24T10:03:44.723442Z | - |
Required: dev-activity (partial), report-delivery (complete).
Overall status partial is derived from the run manifest above, not asserted.

Run ddr-2026-09-22-a3477cd2 · generated 2026-09-23T10:04:20.059674Z · overall status: partial
