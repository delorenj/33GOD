Daily Developer Report — 2026-08-31
Summary written by anthropic/claude-opus-5. Everything below it is rendered by the pipeline from files it read — every status, metric and caveat is on this page whether or not a model answered.

SUMMARY
-------
**The Cartesia cutover reached production on the james-brennan voice line, and almost everything else today was the closeout, IAM and docs work trailing behind it.**

## What happened

**Voice line goes Cartesia.** `5b925f3 feat(voice): add agentic Cartesia field ops line` was followed by `2c20f03 fix(technician): recognize Cartesia production ingress` and `9c61d87 docs(architecture): re-probe all five planes; the diagrams catch the Cartesia cutover`. The same cutover drove the day's only non-james-brennan decision cluster: `SLOWBURNS-40` was decided twice — first "a deterministic primary-first TTS adapter using only a standard Cartesia runtime key", then hardened for "canonical output claims, provider-authentic envelopes, bounded I/O, and phase-aware manual recovery before quality approval". Slowburns produced 12 commits from a single 61-turn codex session, but it has no configured project root, so no git log was read for it — those commits are unverified here.

**Fail-closed provider closeout (JIMB-207).** The heaviest ticket of the day, and it was worked in two places at once: `e18b39b fix(JIMB-207): make Sentinel closeout truthful` and `36c7d18` in james-brennan, mirrored across all 8 pjangler commits (`9e51fc0`, `1b5c168`, `280739a`, `f4fcb3c`, plus `2c0e2a6 fix(ticket-provider): refresh PM adapter from canonical JIMB-207 hardening`). Decision: keep JIMB-207 the sole Started issue while Damian's acceptance findings land in the cycle (JIMB-232).

**Reversible removals and approval parity.** `bf65215`/`8d92f81` made Quiet Room removal reversible (JIMB-230, JIMB-247); `e623791` removed the Boiler Room (JIMB-236). `475f26d fix(JIMB-222): developers approve at full parity` shipped, yet JIMB-222 was deliberately held in Todo — blocked on the JIMB-210/JIMB-204 cloud base. Supporting fixes: relay IAM `s3:PutObjectTagging` (`b916160`), version-scoped spool tags (`f0875ed`, `f90e87e`), JIMB-229 capture back to sweep-only scope (`f91f0b4`).

**Intelliforia shipped staging, invisibly.** All 15 intelliforia commits are off-HEAD (checked out `docs/epic-40-two-factor-authentication`): Epic 37 admin portal design system (`6bb6d96f`), `4f74141e feat(staging): deploy to the DigitalOcean droplet from GitHub Actions`, and two attempts at the same What's New CI script fix (`aca64d41`, `de305e1f`).

## Needs you

- **get.delo.sh is in a restart loop.** 15 of the 20 shown operational events (of 77) are `restarted container after HTTP 502`. A jacksnaps decision recorded the "smallest reversible runtime repair" — recreate the VPN namespace, reattach gluetun — and the restarts continued anyway.
- **Report delivery is degraded.** 2026-08-26 has no published report and no staged generation. The `33god-pm` daily-report job last ran 2026-08-31 and next runs 2026-09-02 — it is skipping days, and `33god-pm.bak` shares its cron dir, so it fires twice when it does fire.
- **Two cron jobs claim `ok` while missing their skills**: `delodocs-pm/delodocs-triage-second-pass` (no `obsidian`, `llm-wiki` — and it decided to move zero files) and `james-brennan-pm/JIMB board-clearing heartbeat` (no `momo`). Both are lying green.
- **8 of 28 gateway units are not running**, 6 unknown to systemd entirely; `hermes-tonnybox-pm-consumer.service` is not-found.

## Worth noting

The trello PR queue moved nothing: 2 PRs triaged, 0 merges attempted, both blocked on the same four reasons including "automerge disabled". And 6 configured repos — `33GOD`, `bloodbank`, `candystore`, `holocene`, `delonet-company`, `PoopToTheMoon` — had zero commits on any ref.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): complete**

19473 events across 15 project(s) on 2026-08-31: 317 session(s), 6 decision(s), 14 committing session(s), 87 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (66 on the checked-out branch, 21 only on other refs); peak 2026-08-31T02:00:00Z (4230 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=14, decision_count=6, event_count=19473, git_commit_count=87, git_commit_replays_collapsed=0, git_commits_off_head=21, git_commits_on_head=66, git_repos_failed=0, git_repos_logged=3, git_repos_missing=0, git_repos_no_commits=6, git_repos_with_off_head_commits=2, git_root_name_collisions=0, git_roots_active_in_events=4, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=True, peak_hour=2026-08-31T02:00:00Z, peak_hour_event_count=4230, project_count=15, projects_without_root=11, session_count=317
Caveats:
  projects truncated: showing 20 of 23
  operational events truncated: showing 20 of 77
  git scope is 'all-refs': every ref of each configured repository was read for 2026-08-31 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  6 configured project root(s) were read across all refs of each repository and had no commits on 2026-08-31: 33GOD, delonet-company, PoopToTheMoon, bloodbank, candystore, holocene
  21 of 87 commit(s) are not reachable from their repository's checked-out branch (unmerged or otherwise off-HEAD work) and are counted here: james-brennan 6 of 64 (checked out: main), intelliforia 15 of 15 (checked out: docs/epic-40-two-factor-authentication)
  11 project(s) active in events have no configured project root, so no git log was read for them: 222-dev-approvals, feat-cartesia-agents, memories, project-fuckudeer, relay, slowburns, surface, technician, and 3 more
Detail:
  === Events by CLI ===
    claude        11724
    codex          5957
    antigravity     797
    hermes          748
    unknown         246
    reportctl         1
  
  === Events by project ===
    james-brennan          12587
    intelliforia            1974
    slowburns               1292
    unknown                 1219
    feat-cartesia-agents    1028
    222-dev-approvals        426
    pjangler                 345
    relay                    171
    vinyl                     77
    surface                   75
    wax                       69
    memories                  56
    james-brennan.git         54
    voice                     54
    PoopToTheMoon             17
    technician                12
    project-fuckudeer         10
    pjangler.git               2
    intelliforia.git           1
    PoopToTheMoon.git          1
    ... showing 20 of 23 projects
  
  === Decisions recorded ===
    [jacksnaps] (no issue): Restore the operator-requested get.delo.sh media service with the smallest reversible runtime repair: recreate the failed VPN namespace, remove only the proven orphan docker-proxy, explicitly reattach gluetun to proxy, and verify the public route
    [slowburns] SLOWBURNS-40: Harden Cartesia fallback around canonical output claims, provider-authentic envelopes, bounded I/O, and phase-aware manual recovery before quality approval
    [delodocs] (no issue): Hold the first 10 triage files; none has the upstream processed release state, so move zero files.
    [slowburns] SLOWBURNS-40: Implement SLOWBURNS-40 as a deterministic primary-first TTS adapter using only a standard Cartesia runtime key
    [james-brennan] JIMB-222: Keep JIMB-222 in Todo as the urgent Damian developer-approval blocker until the JIMB-210 and JIMB-204 cloud base is deployed
    [james-brennan] JIMB-232: Place Damian's live acceptance findings and their named handoff dependencies in the active Workflow One cycle while keeping JIMB-207 as the sole Started issue
  
  === Sessions that committed ===
    james-brennan (claude, 61 turns): 1 commit(s)
    james-brennan (claude, 8 turns): 1 commit(s)
    james-brennan (antigravity, 5 turns): 1 commit(s)
    james-brennan (claude, 69 turns): 2 commit(s)
    james-brennan (antigravity, 52 turns): 2 commit(s)
    james-brennan (antigravity, 4 turns): 1 commit(s)
    james-brennan (antigravity, 31 turns): 1 commit(s)
    james-brennan (antigravity, 135 turns): 2 commit(s)
    james-brennan (codex, 19 turns): 2 commit(s)
    slowburns (codex, 61 turns): 12 commit(s)
    james-brennan (claude, 126 turns): 1 commit(s)
    james-brennan (claude, 24 turns): 2 commit(s)
    james-brennan (claude, 27 turns): 2 commit(s)
    vinyl (codex, 13 turns): 1 commit(s)
  
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
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [wax] updated: (no detail)
    [wax] started: (no detail)
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    ... showing 20 of 77 operational events
  
  === Git log by repository ===
  === 33GOD ===
  (no commits)
  
  === james-brennan ===
    (checked out: main; 6 of 64 commit(s) below are not reachable from it)
    9c61d87 docs(architecture): re-probe all five planes; the diagrams catch the Cartesia cutover
    2c20f03 fix(technician): recognize Cartesia production ingress
    8cd9486 chore(devops): taskdefs at ab2c18c
    f63d8fe docs(context): fan out AGENTS.md per boundaries.md step 9, retire laptop-timer remnants
    f51cca3 docs(deploy): add notes about cutover refusal, transient parity mismatch, and IAM triggers to deploy skill
    ab2c18c checkpoint: 2026-08-31T22:56:59Z auto-commit
    ed072a3 chore(devops): taskdefs at 80727bd
    f0875ed fix(iam): keep spool tags version-scoped
    f90e87e fix(voice): prove exact-version spool tags
    b916160 fix(relay): IAM policy missing s3:PutObjectTagging in task-fieldopsline tasks
    ab02dcf fix(surface): Testbed.tsx type error in clearResult ids property
    80727bd fix(relay): remove obsolete test_costs_publisher parity assertions
    daca4c3 chore(devops): taskdefs at 5b925f3
    8d92f81 feat: implement reversible Quiet Room removal (JIMB-247)
    5b925f3 feat(voice): add agentic Cartesia field ops line
    57bdeab checkpoint: 2026-08-31T21:55:35Z auto-commit
    7cd7ad5 Merge origin/main into damian/247-230  [not reachable from main]
    1926927 fix(hindsight): restore canonical endpoint and relative links
    55e554f chore(devops): taskdefs at bf65215
    7a3e3e3 checkpoint: 2026-08-31T18:53:02Z auto-commit  [not reachable from main]
    bf65215 feat(JIMB-230,JIMB-247): make Quiet Room removal reversible
    2455445 docs(hindsight): clarify local dotenv handoff
    b78b748 feat(hindsight): make developer handoff self-bootstrapping
    bb1383a checkpoint: 2026-08-31T17:52:24Z auto-commit
    e1dd1e0 docs: record blocked BMAD auto-run for JIMB-230/247
    6d5ee71 Add mise run claude launcher for Kimi-routed Claude Code
    24e1968 chore(devops): taskdefs at cda940a
    cda940a fix(JIMB-240): the live badge clears when the newest call ends, even without turns
    7eec3b2 checkpoint: 2026-08-31T16:50:42Z auto-commit
    af971bd Configure Claude Code project settings to route to Kimi API
    ad27c27 Revert invalid Kimi model entries from Claude settings
    52fe2c6 Configure project-scoped Claude settings for Kimi models
    05c00ab chore(devops): taskdefs at 929af71
    929af71 fix(JIMB-243,JIMB-244): the line knows Jim, and a refusal says which one it is
    28a915a checkpoint: 2026-08-31T13:48:53Z auto-commit
    24f0a47 chore(devops): taskdefs at 475f26d
    475f26d fix(JIMB-222): developers approve at full parity, and the badge is the cohort
    a699b12 Merge remote-tracking branch 'origin/main' into 229-mirror-fix
    181a5fe chore(devops): taskdefs at 6580d8d
    ac88d7f docs(JIMB-229): evidence — three consecutive green scheduled runs, drift surfaced live
    6580d8d feat(JIMB-237): record what the technician said when no job matched
    a6f7ae2 fix(JIMB-212): an old open frame is not the call on the line
    c23bdc7 docs: add dated Workflow 1 acceptance workbook  [not reachable from main]
    e623791 JIMB-236: remove the Boiler Room
    50d53af docs(JIMB-229): inventory row for the sweep-only capture at taskdef :11
    27e98d8 docs: complete Workflow 1 handoff release packet  [not reachable from main]
    f91f0b4 fix(JIMB-229): restore the 15-minute capture to sweep-only scope
    dae09e3 checkpoint: 2026-08-31T06:44:39Z auto-commit
    87e062d fix(surface): grant fenced AutomaticAI approval access  [not reachable from main]
    a6d47f0 checkpoint: 2026-08-31T05:42:22Z auto-commit
    36c7d18 fix(JIMB-207): merge fail-closed provider closeout
    25587e4 fix(voice): let caller finish the closeout report  [not reachable from main]
    d954b95 checkpoint: 2026-08-31T04:41:50Z auto-commit
    e18b39b fix(JIMB-207): make Sentinel closeout truthful
    c93f67f fix(ticket-provider): merge canonical JIMB-207 hardening into installed PM scripts
    8577400 checkpoint: 2026-08-31T03:41:15Z auto-commit
    14d3428 chore(devops): taskdefs at 245e82b
    245e82b fix(relay): green the five write-path suites against 0009's causal contract
    c0ba4aa docs(evidence): JIMB-193, JIMB-186 and JIMB-195 were satisfied and unwritten
    cb61871 fix(gate): track the six project skills again, and make the gate see a symlink
    db2582e checkpoint: 2026-08-31T02:40:32Z auto-commit
    9f814af Merge pull request #6 from AutomaticAI-io/codex/workflow-1-handoff-package
    6887844 checkpoint: 2026-08-31T00:37:29Z auto-commit
    c6f4d6c docs: add Workflow 1 handoff acceptance package
  
  === intelliforia ===
    (checked out: docs/epic-40-two-factor-authentication; 15 of 15 commit(s) below are not reachable from it)
    8068b5de Address PR #738 review findings  [not reachable from docs/epic-40-two-factor-authentication]
    9242a5e3 Merge origin/main into rules_continue  [not reachable from docs/epic-40-two-factor-authentication]
    615f43f0 Deploy coverage report from run 1326 80f24c666ca0cd832c9d6354e92d6e284dd6c160  [not reachable from docs/epic-40-two-factor-authentication]
    80f24c66 story(37.10): restore session tracker visual craft (#737)  [not reachable from docs/epic-40-two-factor-authentication]
    b38cb3d5 Unify rule checks and add internal score digest  [not reachable from docs/epic-40-two-factor-authentication]
    ac6af779 Deploy coverage report from run 1323 6bb6d96f65f99c752064adaf37acb90eadeb9281  [not reachable from docs/epic-40-two-factor-authentication]
    96ad8c53 Deploy coverage report from run 1322 de305e1fa0908711a89dfc75102fb24fa0620678  [not reachable from docs/epic-40-two-factor-authentication]
    6bb6d96f Epic 37: admin portal design system, and the staging environment that proves it (#727)  [not reachable from docs/epic-40-two-factor-authentication]
    de305e1f fix(ci): give the What's New build a script that exists in a fresh checkout (#736)  [not reachable from docs/epic-40-two-factor-authentication]
    ae822d20 fix(staging): deploy a named ref, and stop the image label from lying  [not reachable from docs/epic-40-two-factor-authentication]
    aca64d41 fix(ci): give the What's New build a script that exists in a fresh checkout  [not reachable from docs/epic-40-two-factor-authentication]
    7585c1bf Give the redesign's date call sites names, and re-target the board tests  [not reachable from docs/epic-40-two-factor-authentication]
    5e0c86cc test(tracker): re-target the board tests onto the redesign's idiom  [not reachable from docs/epic-40-two-factor-authentication]
    d3bf2054 Merge origin/main into design/admin-portal-overhaul  [not reachable from docs/epic-40-two-factor-authentication]
    4f74141e feat(staging): deploy to the DigitalOcean droplet from GitHub Actions  [not reachable from docs/epic-40-two-factor-authentication]
  
  === delonet-company ===
  (no commits)
  
  === PoopToTheMoon ===
  (no commits)
  
  === pjangler ===
    f4fcb3c fix(JIMB-207): project proven comment closeout
    ba4b05d test(JIMB-207): assert committed Sentinel modes
    280739a fix(JIMB-207): preserve executable Sentinel projections
    19e48df fix(JIMB-207): preserve projected script modes
    1b5c168 fix(JIMB-207): project fail-closed provider closeout
    c0350a7 fix(JIMB-207): project configured close-gate slug
    9e51fc0 fix(JIMB-207): project truthful autonomous closeout
    2c0e2a6 fix(ticket-provider): refresh PM adapter from canonical JIMB-207 hardening
  
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
Metrics: agent_profile_dirs_missing=0, agents_registered=28, cron_jobs_enabled=4, cron_jobs_total=4, cron_jobs_unreadable=0, duplicate_cron_dirs=1, gateway_units_inactive=2, gateway_units_unknown=6, jobs_claiming_ok_contradicted=2, jobs_claiming_ok_unverified=2, jobs_with_missing_skill=2, jobs_with_past_next_run=0, profiles_scanned=39, profiles_unreadable_jobs=0, profiles_with_cron_jobs=4, profiles_with_stale_ticker=0, profiles_without_cron_dir=0, report_date=2026-08-31, sources_failed=0, sources_read=4, timers_active=15, timers_failed=0, timers_never_triggered=0, timers_total=15, timers_without_next_elapse=0, units_failed=0, units_not_found=1, units_total=56
Caveats:
  2 cron job(s) report last_status='ok' with no independent corroboration; last_status is a scheduler claim and is not treated as evidence of success
  2 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-09-01T10:01:03.626714Z (fleet state is current, not reconstructed for the report date)
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
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-08-31T10:01:36.653158Z, next 2026-09-02T10:00:00Z
    job 33god-pm.bak/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-08-31T10:01:36.653158Z, next 2026-09-02T10:00:00Z
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='ok' (claim, contradicted), last run 2026-08-31T13:05:33.550279Z, next 2026-09-01T13:00:00Z; skill(s) not installed: obsidian, llm-wiki
    job james-brennan-pm/JIMB board-clearing heartbeat: enabled, schedule 'every 10m', last_status='ok' (claim, contradicted), last run 2026-09-01T09:44:21.196135Z, next 2026-09-01T10:04:23.946618Z; skill(s) not installed: momo

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 1 tick(s) across 1 of 1 tracked repositories on 2026-08-31; 2 PR(s) triaged, 2 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=0, merge_candidates=2, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=0, prs_triaged=2, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=0, ticks_in_window=1, ticks_noop=0
Caveats:
  pr-crusher activity is read from its durable state, not Candystore: its Bloodbank publisher has been observed disabled, so absence of PR events on the bus does not mean absence of PR activity
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-08-31T04:00:00Z .. 2026-09-01T04:00:00Z for 2026-08-31 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 0
    tick 35 tick-000035-20260831T070308.651514Z completed=2026-08-31T07:04:37.186492Z provider=opencode_free provider_status=complete result_status=complete success=True automerge=False
      PR #115 ci=pass coverage=pass grade=good disposition=keep mergeable=MERGEABLE draft=False threads_resolved=False head=4b051923b344
      PR #111 ci=partial coverage=unknown grade=good disposition=keep mergeable=MERGEABLE draft=False threads_resolved=False head=e2e916a115af
      merge gate PR #115 allowed=False attempted=False reasons: automerge disabled; review threads are not resolved; CI is not successful; coverage is not holding; candidate is not mergeable
      merge gate PR #111 allowed=False attempted=False reasons: automerge disabled; review threads are not resolved; CI is not successful; coverage is not holding; candidate is not mergeable
      summary: Analyzed 2 open PRs in delorenj/mcp-server-trello. PR #115 (feat(cards): support pos parameter when creating cards) is a good-grade feature addition with green CI (Test+coverage gate SUCCESS, GitGuardian SUCCESS) but unresolved copilot review comments suggesting schema tightening from z.union([z.string(), z.number()]) to z.enum(['top','bottom']) + z.number().positive(). Review state COMMENTED, not... (clipped from 842 chars)
      note: PR #115: pos parameter feature - CI green (Test+coverage gate SUCCESS, GitGuardian SUCCESS), copilot review with 2 suppressed comments suggesting z.union([z.string(), z.number()]) should be narrowed to z.enum(['top','bottom']) + z.number().positive(). Review state COMMENTED, not APPROVED. threads_resolved=false.
      note: PR #111: health monitor timer unref fix - GitGuardian SUCCESS, but no Test+coverage gate visible in statusCheckRollup. ReviewDecision REVIEW_REQUIRED, no reviews. threads_resolved=false.

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: DELIVERY DEGRADED -- 1 of 6 due day(s) in 2026-08-25..2026-08-31 have no valid published report (1 missing). 5 of 6 due days delivered over 2026-08-25..2026-08-31 (1 gap(s)); 5 completion event(s), 0 archive/event disagreement(s); delivered streak 4.
Metrics: archive_event_disagreements=0, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=4, days_archive_without_event=0, days_checked=7, days_delivered=5, days_event_without_archive=0, days_in_progress=1, days_invalid=0, days_missing=1, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=1, delivery_health=degraded, events_found=5, lookback_days=7
Caveats:
  DELIVERY DEGRADED: 1 of 6 due day(s) in 2026-08-25..2026-08-31 have no valid published report (1 missing)
Detail:
  window 2026-08-25..2026-08-31 (7 days), report_date 2026-08-31
  delivery health degraded: 1 of 6 due day(s) in 2026-08-25..2026-08-31 have no valid published report (1 missing)
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.reporting.report.completed: reachable
  2026-08-25 delivered events=1 claimed=complete generation=0c92b6f7abf8482188b536c9cc5eedf8
  2026-08-26 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-26
  2026-08-27 delivered events=1 claimed=complete generation=1472ef2e152c42aa94012cce38fb34ba
  2026-08-28 delivered events=1 claimed=complete generation=001568c972584cae9965b922dcef9126
  2026-08-29 delivered events=1 claimed=complete generation=e841776cf5764df5ad7cfca76f89fbbd
  2026-08-30 delivered events=1 claimed=complete generation=41135b0df7434d658f7b5bd65924f82b
  2026-08-31 in-progress events=0 reason=this run is producing this day; it publishes after collection

COVERAGE
--------
4 of 4 enabled sections completed.
No section is degraded.

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | complete | 2026-09-01T10:01:03.619988Z | 2026-09-02T10:01:03.619988Z | - |
| fleet-health | complete | 2026-09-01T10:01:03.626714Z | 2026-09-02T10:01:03.626714Z | - |
| pr-maintenance | complete | 2026-09-01T10:01:03.679475Z | 2026-09-02T10:01:03.679475Z | - |
| report-delivery | complete | 2026-09-01T10:01:03.699731Z | 2026-09-02T10:01:03.699731Z | - |
Required: dev-activity (complete), report-delivery (complete).
Overall status complete is derived from the run manifest above, not asserted.

Run ddr-2026-08-31-3421ed9a · generated 2026-09-01T10:02:08.994603Z · overall status: complete
