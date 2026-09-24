Daily Developer Report — 2026-09-23
Deterministic render — no narration (narrator output was not valid JSON: Unterminated string starting at: line 1 column 150 (char 149)). Every status below was derived by the pipeline from files it read.

SUMMARY
-------
3 of 4 sections completed; report status partial. No narration this run (narrator output was not valid JSON: Unterminated string starting at: line 1 column 150 (char 149)).

Needs attention:
- Developer Activity is partial: event pagination stopped at the 50-page budget (50000 events read); the day is not fully covered

Section detail follows below.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): partial** -- event pagination stopped at the 50-page budget (50000 events read); the day is not fully covered

50000 events across 9 project(s) on 2026-09-23: 26510 session(s), 1 decision(s), 20 committing session(s), 162 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (132 on the checked-out branch, 30 only on other refs); peak 2026-09-23T00:00:00Z (45068 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=20, decision_count=1, event_count=50000, git_commit_count=162, git_commit_replays_collapsed=0, git_commits_off_head=30, git_commits_on_head=132, git_repos_failed=0, git_repos_logged=9, git_repos_missing=0, git_repos_no_commits=0, git_repos_with_off_head_commits=2, git_root_name_collisions=0, git_roots_active_in_events=4, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=True, peak_hour=2026-09-23T00:00:00Z, peak_hour_event_count=45068, project_count=9, projects_without_root=5, session_count=26510
Caveats:
  git scope is 'all-refs': every ref of each configured repository was read for 2026-09-23 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  30 of 162 commit(s) are not reachable from their repository's checked-out branch (unmerged or otherwise off-HEAD work) and are counted here: james-brennan 18 of 38 (checked out: main), intelliforia 12 of 15 (checked out: main)
  5 project(s) active in events have no configured project root, so no git log was read for them: bb, deckard, idealscenario, momo, project
Detail:
  === Events by CLI ===
    claude        44345
    unknown        2119
    codex          1509
    kimi           1047
    antigravity     840
    hermes          139
    reportctl         1
  
  === Events by project ===
    unknown         38749
    pjangler         5089
    project          2216
    deckard          2138
    idealscenario     666
    intelliforia      632
    james-brennan     451
    bb                 47
    momo                7
    candystore          5
  
  === Decisions recorded ===
    [DECK] (no issue): Replace deckard@\<session>.service with config-driven deckard.service; 'deckard run' takes its session from [mux] session and refuses under auto; the unit pins PATH
  
  === Sessions that committed ===
    unknown (claude, 21 turns): 4 commit(s)
    unknown (claude, 1 turns): 4 commit(s)
    unknown (claude, 1 turns): 2 commit(s)
    unknown (claude, 1 turns): 3 commit(s)
    unknown (claude, 1 turns): 2 commit(s)
    unknown (claude, 1 turns): 1 commit(s)
    unknown (claude, 1 turns): 3 commit(s)
    unknown (claude, 1 turns): 1 commit(s)
    unknown (claude, 1 turns): 3 commit(s)
    unknown (claude, 1 turns): 1 commit(s)
    unknown (claude, 1 turns): 1 commit(s)
    unknown (claude, 1 turns): 2 commit(s)
    unknown (claude, 35 turns): 48 commit(s)
    deckard (claude, 14 turns): 36 commit(s)
    unknown (antigravity, 78 turns): 1 commit(s)
    james-brennan (claude, 15 turns): 13 commit(s)
    unknown (codex, 1 turns): 1 commit(s)
    unknown (claude, 3 turns): 1 commit(s)
    idealscenario (claude, 3 turns): 4 commit(s)
    idealscenario (claude, 3 turns): 2 commit(s)
  
  === Operational notes ===
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
  
  === Git log by repository ===
  === 33GOD ===
    fc5e537 docs: adopt DeloHQ architecture spine as spec
    6314222 chore: pj migrate --all to 33god parity (PJAN-137)
    07de0b0 Land the 2026-09-22 daily journal
    d5f2f58 Bump submodules: named agent Grolf, TonnyBox parity, skills sync, scaffold refresh
    1f5c633 skills(krebs, platform): ticket facts come only from the Plane webhook
    8a4e7fd 33god-pm is Grolf: the fleet's first named agent (@Gr0lfBot)
    56d8b15 Bump bloodbank: ingress reconcile, chip claim rule, 0.7.2 lane prompts
    c689784 Land the 2026-09-20 and 2026-09-21 daily journals
    5833d5a Bump submodules: follow-ups landed (scaffold, propagation, boards, flood, durable triggers)
    16cdfce fix(soul): project memory names the bank the hooks actually write
    b76c276 docs(delohq): add architecture spine
    09e517e hermes pm scaffold: full flume remediate to hermes-agent-template 020d6d9
    d637762 krebs tp adapters: extended ticket states, per-role configured
    7607e79 docs(delohq): finalize product requirements
    60465bc docs: Bloodbank route activation defaults to allow, not default-deny
    3a8a447 docs(cli-hook-audit): say 'stub' for the OpenClaw watcher so docs:drift stops reading it as an incomplete marker
    bc92d1b docs(delohq): clarify flume executive-surface boundary
    9c21633 Bump submodules: triage lane overhaul, default-on activation, op cache fallout
    a74a3fe 33god-pm: 80-registry.sh from hermes-agent-template ad40c9d
    dc39da8 33god-pm: refresh .scripts to hermes-agent-template 4582731
    57efcf6 fix(pm SOUL): task.invoke create is data.command.operation, not op
    b4d8800 No key means enabled: 33god-pm role comment and 80-registry.sh
  
  === james-brennan ===
    (checked out: main; 18 of 38 commit(s) below are not reachable from it)
    ccbb24da fix(deploy): the deploy's own parity check must stay strict, and pin its sha (#259)
    45233bc7 chore(inventory): observed AWS services in run 35931932219 (#258)
    a0277a6c chore(devops): taskdefs at d818b3d  [not reachable from main]
    4da863aa chore(inventory): observed AWS services in run 35931932219  [not reachable from main]
    1c4c42eb fix(deploy): the deploy's own parity check must stay strict, and pin its sha  [not reachable from main]
    a624a5a7 chore(devops): taskdefs at d818b3d3 (#256)
    1bc029d5 chore(inventory): observed AWS services in run 35931192463 (#257)
    756bdeac chore(inventory): observed AWS services in run 35931192463  [not reachable from main]
    66862b14 chore(devops): taskdefs at d818b3d3  [not reachable from main]
    d818b3d3 fix: parity asks whether the system is current, and no test races a stopwatch (#255)
    0a2deda4 fix: parity asks whether the system is current, and no test races a stopwatch  [not reachable from main]
    6cf979e5 fix(tasks): drop skills:provision:packs from the catalogue, it no longer exists (#254)
    75416068 fix(tasks): drop skills:provision:packs from the catalogue, it no longer exists  [not reachable from main]
    3c9a0ded chore(devops): taskdefs at 63d9177 (#253)
    b4d50047 chore(devops): taskdefs at 63d9177  [not reachable from main]
    63d9177b chore: pj migrate --all to 33god parity (PJAN-137)  [not reachable from main]
    941a4849 chore/scaffold refresh 0208c9e (#251)
    f1d65d96 Cleanup Repo (#250)
    151d6112 hermes pm scaffold: refresh .scripts to hermes-agent-template 0208c9e  [not reachable from main]
    c1eca12f Merge branch 'main' of github.com:AutomaticAI-io/james-brennan  [not reachable from main]
    b6f2915a Cleanup Repo  [not reachable from main]
    34262b9e docs(board-taxonomy): the chip is the stateless Ticket Pickup Chip (#249)
    ae917c21 chore(inventory): observed AWS services in run 35872906508  [not reachable from main]
    931e1a14 james-brennan-pm: full scaffold refresh to hermes-agent-template 020d6d9 (#248)
    1f128c39 fix(sync-docs): a delete we are not allowed to make is not a sync failure (#247)
    a2438ff9 james-brennan-pm: 80-registry.sh from hermes-agent-template ad40c9d (#246)
    dfd6f582 james-brennan-pm: 80-registry.sh from hermes-agent-template ad40c9d  [not reachable from main]
    2007f4bc james-brennan-pm: refresh .scripts to hermes-agent-template 4582731 (#245)
    38f08436 james-brennan-pm: refresh .scripts to hermes-agent-template 4582731  [not reachable from main]
    11af1393 fix(sync-docs): "gorilladesk-" is not an OpenAI key (#244)
    d210fb87 The task sweep: file all 170, quarantine the 18 that are spent, and make the fence bite (#241)
    a6d3cade chore(inventory): observed AWS services in run 35805131310 (#243)
    27a1f585 chore(inventory): observed AWS services in run 35805131310  [not reachable from main]
    1ab88174 chore(devops): taskdefs at 91ae80e2 (#242)
    2a9401ef chore(devops): taskdefs at 91ae80e2  [not reachable from main]
    91ae80e2 Land the orphaned capability probes, the JIMB-359 identity fix, and the 7507b2c3 taskdefs (#239)
    6d0f4709 No key means enabled: 80-registry.sh projects an absent bloodbank.enabled as true (#240)
    2db187da No key means enabled: 80-registry.sh projects an absent bloodbank.enabled as true  [not reachable from main]
  
  === intelliforia ===
    (checked out: main; 12 of 15 commit(s) below are not reachable from it)
    55db9afb Deploy coverage report from run 1495 cb886e593f5052578e78685f4fed48306a791827  [not reachable from main]
    58945ab8 test(INT-255): assert ONE alembic head, not that INT-269's is the tip  [not reachable from main]
    852612e5 feat(tracker): the score IS the checklist, and org 232's rubric columns go quiet  [not reachable from main]
    9d5274d7 feat(scoring): capture barriers, and backfill them without re-parsing  [not reachable from main]
    7dafa26f feat(scoring): wire the check run into scoring for Supportive  [not reachable from main]
    66a2bd16 feat(scoring): the named check run that replaces the rubric score  [not reachable from main]
    cb886e59 feat(INT-269/INT-270): org-scoped session labels, and per-org Status/Compliance columns (#766)
    b211e0e9 Merge main (#768) into INT-269, re-deriving every billing anchor again  [not reachable from main]
    a640d3d6 Deploy coverage report from run 1493 03f423a1c21b26bdf18fe0f05df36a5d7bf49e7f  [not reachable from main]
    03f423a1 Validate suggested notes before returning (#768)
    e31c1e81 Deploy coverage report from run 1492 daf221c869a04eadd73d7211c0626e1d5d200860  [not reachable from main]
    daf221c8 chore: pj migrate --all to 33god parity (PJAN-137)
    d0a02820 Merge main into INT-269, re-deriving every billing anchor  [not reachable from main]
    4b111d86 Async suggested-note generation with polling  [not reachable from main]
    3a3e0813 Validate suggested notes before returning  [not reachable from main]
  
  === delonet-company ===
    432941d chore: pj migrate --all to 33god parity (PJAN-137)
    5636847 hermes pm scaffold: refresh .scripts to hermes-agent-template 0208c9e
    3835073 fix(soul): project memory names the bank the hooks actually write
    66cb883 hermes pm scaffold: full flume remediate to hermes-agent-template 020d6d9
    c9d32df delonet-director: 80-registry.sh from hermes-agent-template ad40c9d
    e97309d delonet-director: refresh .scripts to hermes-agent-template 4582731
    ff09168 No key means enabled: 80-registry.sh projects an absent bloodbank.enabled as true
  
  === PoopToTheMoon ===
    f74d926 chore: pj migrate --all to 33god parity (PJAN-137)
  
  === pjangler ===
    98ef73e chore: pj migrate --all to 33god parity (PJAN-137)
    7fe6364 merge(PJAN-135): land the mise.toml rewrite / guidance-guard / signal-relay work
    940e558 fix(PJAN-135): mise.versioning leaves a note that mentions its marker alone
    11c063f hermes pm scaffold: refresh .scripts to hermes-agent-template 0208c9e
    ef59d59 chore(PJAN-135): fold currentSkillActivations into the existing ./skills import
    8553592 fix(PJAN-135): the other two mise.toml writers are parse-verified too
    b684439 fix(PJAN-135): plan-time block for a dangling alias on another filesystem
    6117b86 test(PJAN-135): the guidance guard resolves every command word and every fix literal
    1f53c08 test(PJAN-135): crash at every step restores exactly; F15 through the real pj CLI
    7ddcbb0 fix(PJAN-135): pj skills relays termination signals to skillex and ends like it
    d79a747 fix(PJAN-135): mise.toml rewrites are structural and parse-verified
    83c12f2 fix(PJAN-135): classify every root collision before replacing any link
    b00ec28 fix(PJAN-135): skills-root conversion is one verified, journaled, reversible plan
    2665798 skill(projects): enrollment routes a board; a project need not be a git repo
    0200026 docs(PJAN-136): a "dead agent" report is a claim; check the board before offboarding
    0a6db1b fix(PJAN-136): tonnybox-pm is not dead; drop it from DEAD_AGENT_IDS
    c498e91 chore(PJAN-135): bump CommonProject — template drops the unmaintained registry URL
    346d179 fix(init): adopt a non-git project that carries .project.json
    b650436 fix(PJAN-135): mise hooks use run; skills:sync pin passes mise's npm age gate
    3e9cbe6 feat(PJAN-135): pj skills runs the bundled skillex; guidance names only runnable commands
    dd69ac6 fix(PJAN-135): replace a stub .agents/skills entry wholly contained in its alias copy
    54089e1 test(PJAN-135): run the skill-roots suite in the canonical runner
    519f39c test(PJAN-135): prove lossless skills-root conversion on real repos and core
    57509c5 fix(PJAN-135): migrate --all re-runs rules an earlier migration unblocked
    648c092 fix(PJAN-135): convert CLI skills roots losslessly and clear legacy root links
    482cb1f hermes pm scaffold: full flume remediate to hermes-agent-template 020d6d9
    b8b06d6 fix(pm): give the role a plane block (PJAN)
    ff46d14 pjangler-pm: 80-registry.sh from hermes-agent-template ad40c9d
    b505496 pjangler-pm: refresh .scripts to hermes-agent-template 4582731
    03f8405 No key means enabled: 80-registry.sh projects an absent bloodbank.enabled as true
  
  === bloodbank ===
    75df537 chore: pj migrate --all to 33god parity (PJAN-137)
    09abb5d hermes pm scaffold: refresh .scripts to hermes-agent-template 0208c9e
    0e507b5 skill(bloodbank-integration): n8n lanes, agents never emit ticket facts, routing merge
    8dafd7e fix(n8n-nodes-bloodbank): 0.7.2 — lane prompts say agent:working is pipeline-owned
    84a3466 docs(n8n): reconcile workflow names its per-sweep cap; 0.7.1 live proofs
    c85f05e fix(n8n-nodes-bloodbank): 0.7.1 — capped, fault-tolerant ingress sweep; update keys that tell one save's rows apart
    a5b9e06 docs(n8n): live proof that a parked ticket loses its chip, a claimed one keeps it
    ff40595 fix(n8n): chip counts only a move to In Progress as a claim
    1dc307d docs(n8n): live proofs for the ingress reconcile and the chip's claim check
    7b4c661 feat(n8n): Plane Ingress Reconcile workflow (U4hYm3BYPPeZNDHQ), exported live
    4a07fc0 feat(n8n-nodes-bloodbank): 0.7.0 — Plane ingress reconcile, chip keeps a claim made mid-turn
    c446de7 docs: hook.updated now runs ~2/s after hook-hub coalescing
    f67bddf hermes pm scaffold: full flume remediate to hermes-agent-template 020d6d9
    924f523 fix(n8n): shrink the sweep's untouched-since-turn slack from 30s to 5s
    622af08 fix(n8n): stale-chip sweep never strips a px claim marker
    32226d0 feat(n8n): pin the stale-chip sweep minute; re-export lanes after live durability proof
    290879d feat(n8n-nodes-bloodbank): 0.6.0 — durable JetStream event triggers, byte-identical re-dispatch
    b4c96e0 fix(toaster): cap each event type's toast rate so one noisy type cannot use the whole budget
    009f1c6 fix(hook-hub): coalesce hook.updated revisions; stop the backfill scan starving hook writes
    5e90da9 docs(skill): the toaster no longer forwards every event
    0620f43 fix(smoketest): schema-contract-consistency accepts a command schema's [command, reply] kind enum
    78ed0b6 bloodbank-pm: 80-registry.sh from hermes-agent-template ad40c9d
    cef5829 bloodbank-pm: refresh .scripts to hermes-agent-template 4582731
    9cae28d feat(n8n): chip survives a ticket deleted mid-turn; lane docs cover all four workflows
    5860663 fix(toaster): stop self-DoSing ntfy; mute hook pulses, digest tool calls, back off on 429
    558849f docs(bloodbank): route activation defaults to allow, not deny
    7f66b9d feat(n8n): stateless pickup chip; lanes surface every skip
    8c12ad3 fix(n8n-nodes-bloodbank): deploy copies with --checksum; docs name the schema as the alias source
    ffcfc54 feat(n8n-nodes-bloodbank): 0.5.0 — skips on their own output and on the bus, enrolled boards route, schema-owned provider aliases
    bf76503 No key means enabled: 80-registry.sh projects an absent bloodbank.enabled as true
  
  === candystore ===
    59fb78a chore: pj migrate --all to 33god parity (PJAN-137)
    bca133f hermes pm scaffold: refresh .scripts to hermes-agent-template 0208c9e
    c35bdb7 hermes pm scaffold: full flume remediate to hermes-agent-template 020d6d9
    700eade fix(project): bind candystore back to CANDYS, the board that holds its tickets
    c872a15 chore(bmad): sync ticket-lifecycle from momo (px move, no repo.task emits)
    9b9a3d0 fix(pm): name the CNDY board in the role's plane binding
    fbd86f8 fix(project): bind candystore to its live CNDY board (dd2afab7)
    1c836d4 candystore-pm: 80-registry.sh from hermes-agent-template ad40c9d
    1eca2d3 candystore-pm: refresh .scripts to hermes-agent-template 4582731
    0faf7af No key means enabled: 80-registry.sh projects an absent bloodbank.enabled as true
  
  === holocene ===
    3b87443 chore: pj migrate --all to 33god parity (PJAN-137)
    f9d6717 hermes pm scaffold: refresh .scripts to hermes-agent-template 0208c9e
    c63a704 hermes pm scaffold: full flume remediate to hermes-agent-template 020d6d9
    36b2872 fix(pm): point the role's board id at HOLOC (727a2b17)
    1c0dee5 chore(bmad): sync ticket-lifecycle from momo (px move, no repo.task emits)
    e03b3b1 feat(deploy): mise deploy|deploy:api|deploy:web build-on-deploy; land bmad/opencode config
    b03cb31 holocene-pm: 80-registry.sh from hermes-agent-template ad40c9d
    a0e3381 holocene-pm: refresh .scripts to hermes-agent-template 4582731
    e468ade No key means enabled: 80-registry.sh projects an absent bloodbank.enabled as true

HERMES FLEET HEALTH
-------------------
**Status (authoritative): complete**

Hermes fleet: 25 agents registered; 0 timers (0 active, 0 failed); 3 cron jobs across 2 profiles (2 enabled); 2 job(s) reference a missing skill; 0 profile(s) with a stale ticker; 9 gateway unit(s) not running.
Metrics: agent_profile_dirs_missing=0, agents_registered=25, cron_jobs_enabled=2, cron_jobs_total=3, cron_jobs_unreadable=0, duplicate_cron_dirs=0, gateway_units_inactive=2, gateway_units_unknown=7, jobs_claiming_ok_contradicted=2, jobs_claiming_ok_unverified=0, jobs_with_missing_skill=2, jobs_with_past_next_run=0, profiles_scanned=37, profiles_unreadable_jobs=0, profiles_with_cron_jobs=2, profiles_with_stale_ticker=0, profiles_without_cron_dir=0, report_date=2026-09-23, sources_failed=0, sources_read=4, timers_active=0, timers_failed=0, timers_never_triggered=0, timers_total=0, timers_without_next_elapse=0, units_failed=0, units_not_found=1, units_total=20
Caveats:
  2 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-09-24T11:49:56.782060Z (fleet state is current, not reconstructed for the report date)
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
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='error' (claim, not-claimed), last run 2026-09-24T10:00:16.969239Z, next 2026-09-25T10:00:00Z; last_error recorded (53 chars, not copied here)
    job 33god-pm/Board Cranker implementation loop: disabled, schedule 'every 5m', last_status='ok' (claim, contradicted), last run 2026-09-05T12:48:43.347617Z, next none; skill(s) not installed: momo, project-lifecycle, subagent-driven-development, coding-strategy, pjangler, bloodbank-integration
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='ok' (claim, contradicted), last run 2026-09-23T13:07:48.660188Z, next 2026-09-24T13:00:00Z; skill(s) not installed: obsidian, llm-wiki

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 1 tick(s) across 1 of 1 tracked repositories on 2026-09-23; 0 PR(s) triaged, 0 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged; 1 tick(s) did not succeed.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=0, merge_candidates=0, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=0, prs_triaged=0, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=1, ticks_in_window=1, ticks_noop=0
Caveats:
  pr-crusher activity is read from its durable state, not Candystore: its Bloodbank publisher has been observed disabled, so absence of PR events on the bus does not mean absence of PR activity
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-09-23T04:00:00Z .. 2026-09-24T04:00:00Z for 2026-09-23 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 0
    tick 57 tick-000057-20260923T070733.639835Z completed=2026-09-23T07:07:36.459863Z provider=none provider_status=failed result_status=failed success=False automerge=False
      merge gate PR #None allowed=False attempted=False reasons: merge processing failed: credential broker rejected prc_github_write_token
      summary: runner/provider setup failed: credential broker rejected prc_github_read_token

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: DELIVERY DEGRADED -- 1 of 6 due day(s) in 2026-09-17..2026-09-23 have no valid published report (1 missing). 5 of 6 due days delivered over 2026-09-17..2026-09-23 (1 gap(s)); 6 completion event(s), 0 archive/event disagreement(s); delivered streak 4.
Metrics: archive_event_disagreements=0, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=4, days_archive_without_event=0, days_checked=7, days_delivered=5, days_event_without_archive=0, days_in_progress=1, days_invalid=0, days_missing=1, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=1, delivery_health=degraded, events_found=6, lookback_days=7
Caveats:
  DELIVERY DEGRADED: 1 of 6 due day(s) in 2026-09-17..2026-09-23 have no valid published report (1 missing)
  duplicate completion events for 2026-09-19; more than one run claimed the same day
Detail:
  window 2026-09-17..2026-09-23 (7 days), report_date 2026-09-23
  delivery health degraded: 1 of 6 due day(s) in 2026-09-17..2026-09-23 have no valid published report (1 missing)
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.reporting.report.completed: reachable
  2026-09-17 delivered events=1 claimed=partial generation=3252122c267b4beaa3e75dde1d2f11ca
  2026-09-18 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/09/2026-09-18
  2026-09-19 delivered events=2 claimed=partial generation=527ce8a2d2f742b99a1c920c5d037f85
  2026-09-20 delivered events=1 claimed=partial generation=11f52f9cbf71413ebbc33c23c666aa20
  2026-09-21 delivered events=1 claimed=partial generation=9bae3dfec7d745dc9163e2e6b6d3b236
  2026-09-22 delivered events=1 claimed=partial generation=f81e6439133a4d6b9e8e90d668c47f05
  2026-09-23 in-progress events=0 reason=this run is producing this day; it publishes after collection

COVERAGE
--------
3 of 4 enabled sections completed.
Degraded: dev-activity (partial).

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | partial | 2026-09-24T11:49:56.775274Z | 2026-09-25T11:49:56.775274Z | event pagination stopped at the 50-page budget (50000 events read); the day is not fully covered |
| fleet-health | complete | 2026-09-24T11:49:56.782060Z | 2026-09-25T11:49:56.782060Z | - |
| pr-maintenance | complete | 2026-09-24T11:49:56.840254Z | 2026-09-25T11:49:56.840254Z | - |
| report-delivery | complete | 2026-09-24T11:49:56.859432Z | 2026-09-25T11:49:56.859432Z | - |
Required: dev-activity (partial), report-delivery (complete).
Overall status partial is derived from the run manifest above, not asserted.

Run ddr-2026-09-23-59c7d684 · generated 2026-09-24T11:50:38.457407Z · overall status: partial
