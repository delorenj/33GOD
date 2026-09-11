Daily Developer Report — 2026-09-06
Summary written by anthropic/claude-opus-5. Everything below it is rendered by the pipeline from files it read — every status, metric and caveat is on this page whether or not a model answered.

SUMMARY
-------
**A client account was holding the owner's personal memory credential, and today that got closed out — three commits deep — in the middle of the heaviest voice-stack day of the week.**

## What happened

**james-brennan voice/relay dominated** — 78 of the day's 98 commits. The security thread is the one that matters: `a3eaf2b` took the owner's personal memory credential out of the client's account, `653acea` closed "the last three paths to the owner's personal Hindsight," and `35823a2` made memory's failure audible instead of silent. Alongside that, `ad3bb72` finally root-caused the five-day ConnectError as a nested subdomain. Ticket work landed across JIMB-276 (EventBridge publisher diagnostics merged, `ea9bee8`), JIMB-280 (AC2 enriched schedule + AC6 provider-failure coverage), JIMB-284 (Testbed count vocabulary), JIMB-286 (Quiet Room waiting rail removed, autonomous verdict recorded), and JIMB-293 (`15ddc8b` stopped the agent reading the schema aloud and retiring unheard questions). `05f0f77` extracted the transport-neutral conversation core — Phase 1 — and `e9fe42f` added a developer trace channel plus a model swap that needs no deploy. JIMB-282 is on an independent Gate 1 **hold** (`2329294`).

**The ASM/agent-state contract shipped across three repos.** Bloodbank landed 10 commits — bell/gate split with structural surface class (`e8250af`), tabpaint and PRESENT-vs-WORKING semantics (`bcdfa6c`), Agent Hook Telemetry (`e4858bd`), closed Plane label set (`c6dfd19`), and an optional `ephemeral` envelope extension for worktree-origin events (`dbef526`). Candystore surfaced `ephemeral` in `/events` previews (`f5a1fd8`) and 33GOD tracked it through nine bump commits. 33GOD also landed worktree side-effect keying by directory (`b849310`) and a fleet worktree policy skill (`e5acf54`). Holocene was documentation-only: IA redesign decided, ground truth verified, adversarial review fixes, hollowness safeguard (`58af0b2`).

## Needs you

- **Nine gateway units are not running** — six unknown to systemd (`delonet-director`, `drumjangler-pm`, `hermes-agent-pm`, `intelliforia-voice-agent-pm`, `nautilus-trader-pm`, `tonnybox-pm`), three inactive. `hermes-automatic-ai-pm-heartbeat.service` is loaded/failed. `hermes-tonnybox-pm-consumer.service` is not-found.
- **`james-brennan-pm/JIMB hourly two-lane pass` runs hourly with four skills not installed** (`momo`, `project-lifecycle`, `project-invariants`, `coding-strategy`) and reports `last_status='ok'` — a claim the pipeline flags as contradicted. Four jobs total are in that state.
- **tonnybox burned most of the day's 132 decisions on idle sentinel passes** — nearly every recorded decision is a variant of "the canonical TONNY board has no work to drive." That loop is spending cycles to discover nothing, with its consumer unit missing.
- **pr-crusher tick 41 failed** on `delorenj/mcp-server-trello`: provider `opencode_free` did not produce a schema-valid result. Its Bloodbank publisher has been observed disabled, so the bus cannot be trusted to show PR activity.
- **`33god-pm.bak` shares its cron dir with `33god-pm`**, duplicating the daily-report job.

## Worth noting

11 james-brennan commits are unreachable from `main` and 10 more are rebase/cherry-pick replays of JIMB-280/282 work — the same fixes exist two and three times. Five projects active in events (`slowburns` 3,306 events, `project` 2,675, `vinyl`, `bb`, `deckard`) have no configured git root, so their commits are invisible here. Report delivery is clean: 6 of 6 due days, zero gaps.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): complete**

39585 events across 7 project(s) on 2026-09-06: 609 session(s), 132 decision(s), 34 committing session(s), 98 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (97 on the checked-out branch, 11 only on other refs); peak 2026-09-06T23:00:00Z (3989 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=34, decision_count=132, event_count=39585, git_commit_count=98, git_commit_replays_collapsed=10, git_commits_off_head=11, git_commits_on_head=97, git_repos_failed=0, git_repos_logged=6, git_repos_missing=0, git_repos_no_commits=3, git_repos_with_off_head_commits=1, git_root_name_collisions=0, git_roots_active_in_events=2, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=True, peak_hour=2026-09-06T23:00:00Z, peak_hour_event_count=3989, project_count=7, projects_without_root=5, session_count=609
Caveats:
  decisions truncated: showing 30 of 132
  committing sessions truncated: showing 30 of 34
  operational events truncated: showing 20 of 128
  git scope is 'all-refs': every ref of each configured repository was read for 2026-09-06 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  3 configured project root(s) were read across all refs of each repository and had no commits on 2026-09-06: intelliforia, delonet-company, pjangler
  11 of 108 commit(s) are not reachable from their repository's checked-out branch (unmerged or otherwise off-HEAD work) and are counted here: james-brennan 11 of 78 (checked out: main)
  10 commit(s) repeat the author date and subject of another commit in the same window (rebase or cherry-pick copies) and were counted once, not twice: james-brennan 10
  5 project(s) active in events have no configured project root, so no git log was read for them: bb, deckard, project, slowburns, vinyl
Detail:
  === Events by CLI ===
    hermes         19479
    claude         14557
    codex           5187
    unknown          352
    hermes-agent       9
    reportctl          1
  
  === Events by project ===
    unknown         16916
    james-brennan   16173
    slowburns        3306
    project          2675
    vinyl             373
    bb                131
    deckard             7
    candystore          4
  
  === Decisions recorded ===
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): Stop this orchestration pass idle; no board work exists to claim or review
    [tonnybox] (no issue): Stop this sentinel pass idle; the board has no claimable, active, or review work.
    [tonnybox] (no issue): End this continuous orchestration pass idle: TONNY has no active milestone or tickets to drive.
    [james-brennan] JIMB-292: Expand JIMB-292 only to its existing Testbed reachability assertions
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): Stop this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): Stop this sentinel pass idle: canonical TONNY board has no active milestone or issues
    [james-brennan] JIMB-292: Use the free Surface lane for JIMB-292's bounded Testbed switch replacement
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: two adapter sweeps confirm the canonical TONNY board has no work to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): Stop this continuous ticket sentinel pass idle: TONNY has no active milestone or project issues to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): Stop this continuous orchestration pass idle: the canonical TONNY board has no active milestone or issues to drive.
    [tonnybox] (no issue): Stop this continuous orchestration pass idle: the canonical TONNY board has no active milestone or issues to drive.
    [tonnybox] (no issue): Stop this orchestration pass idle; the canonical TONNY board contains no work to drive.
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: TONNY has no active milestone or project issues to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    [tonnybox] (no issue): End this continuous ticket sentinel pass idle: the canonical TONNY board has no work to drive
    ... showing 30 of 132 decisions
  
  === Sessions that committed ===
    james-brennan (claude, 68 turns): 6 commit(s)
    james-brennan (claude, 809 turns): 1 commit(s)
    james-brennan (claude, 73 turns): 2 commit(s)
    slowburns (codex, 1 turns): 1 commit(s)
    project (claude, 7 turns): 1 commit(s)
    project (claude, 7 turns): 1 commit(s)
    unknown (codex, 11 turns): 2 commit(s)
    unknown (codex, 1 turns): 1 commit(s)
    project (claude, 32 turns): 1 commit(s)
    james-brennan (claude, 19 turns): 1 commit(s)
    james-brennan (claude, 7 turns): 1 commit(s)
    james-brennan (claude, 37 turns): 1 commit(s)
    james-brennan (claude, 46 turns): 1 commit(s)
    slowburns (codex, 24 turns): 8 commit(s)
    james-brennan (claude, 8 turns): 1 commit(s)
    james-brennan (claude, 28 turns): 2 commit(s)
    unknown (codex, 6 turns): 1 commit(s)
    james-brennan (claude, 39 turns): 1 commit(s)
    james-brennan (claude, 125 turns): 1 commit(s)
    james-brennan (claude, 17 turns): 1 commit(s)
    james-brennan (claude, 86 turns): 3 commit(s)
    vinyl (codex, 10 turns): 2 commit(s)
    james-brennan (claude, 316 turns): 7 commit(s)
    james-brennan (claude, 332 turns): 5 commit(s)
    vinyl (codex, 10 turns): 1 commit(s)
    project (claude, 59 turns): 2 commit(s)
    james-brennan (claude, 39 turns): 1 commit(s)
    james-brennan (claude, 210 turns): 2 commit(s)
    project (claude, 7 turns): 1 commit(s)
    project (claude, 19 turns): 1 commit(s)
    ... showing 30 of 34 committing sessions
  
  === Operational notes ===
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://candystore.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://cal.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://assets.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://cadvisor.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://cal.delo.sh/api/v2
    [unknown] exited: restarted container after HTTP 502 on https://alerts.delo.sh/
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://adguard.delo.sh/
    ... showing 20 of 128 operational events
  
  === Git log by repository ===
  === 33GOD ===
    b849310 worktrees: directory-keyed side effects (hindsight banks, CLI history, shell state)
    bc4804b chore(bloodbank): bump — tab blink disabled
    b235bf4 chore(bloodbank): bump — hermes/copilot events carry working_directory
    e5acf54 worktrees: fleet worktree policy skill + worktrunk integration
    8312856 chore(bloodbank): bump — bell/gate split and the structural surface class
    ede04e3 chore(bloodbank): bump — telemetry hash keeps verdicts and test data out
    f73298f chore: bump — Agent Hook Telemetry replaces the two static hook checks
    42696db chore: bump — Agent Hook Telemetry replaces the two static hook checks
    8fa1868 chore(bloodbank): bump to the ASM tab-bar surface
    d3afa36 chore(bloodbank): bump for the closed board label set
    d0cafa7 chore(bloodbank): bump for tabpaint and presence-vs-activity semantics
    d0cfdea feat(33god-hub): route to the platform's own skills
  
  === james-brennan ===
    (checked out: main; 11 of 78 commit(s) below are not reachable from it)
    7225e7c Merge branch 'worktree-fix-bargein-state-test'
    96eafb0 test(technician): the state assertion pinned the relay's spelling, not the published one
    686343d test(technician): every call script asserted a state the record never publishes
    219a507 chore(devops): taskdefs at 8fc60c1
    2ed40c3 test(technician): the JIMB-293 script walked into two traps of its own making
    8fc60c1 test(technician): a call script for the JIMB-293 status question, and fix the Frank Line secret ref
    1e965f1 chore(devops): taskdefs at 15ddc8b
    15ddc8b fix(voice,relay): stop reading the schema aloud and retiring unheard questions (JIMB-293)
    f100e56 chore(pm): record JIMB-280 and JIMB-286 acceptance blockers
    a8e595f fix(surface): treat a not-yet-loaded identity as loading, not denial  [not reachable from main]
    5c90007 chore(pm): record JIMB-286 acceptance and JIMB-289 triage
    68077b4 docs(review): record JIMB-286 autonomous verdict
    cbb51c9 fix(surface): remove Quiet Room waiting rail (JIMB-286)
    3e9fe31 fix(surface): remove Quiet Room waiting rail (JIMB-286)
    1e33e29 docs(workshop): Frank Line disclosure policy brief for Jim (JIMB-285)
    430023d chore(devops): taskdefs at 05f0f77
    05f0f77 refactor(voice): extract the transport-neutral conversation core (Phase 1)
    e4fb8f3 fix(surface): name the transcript speakers Agent and Technician
    d1a404a chore(JIMB-284): checkpoint acceptance decision
    0c9d79a docs(JIMB-284): record final review and live evidence
    a20a754 fix(surface): match Testbed count vocabulary (JIMB-284)
    0bd87de checkpoint: 2026-09-06T15:42:20Z auto-commit
    01fc878 chore(devops): taskdefs at 653acea
    653acea fix(voice): close the last three paths to the owner's personal Hindsight
    ad3bb72 docs(voice): the five-day ConnectError was a nested subdomain
    c9e6486 chore(devops): taskdefs at a3eaf2b
    613e788 fix(surface): match Testbed count vocabulary (JIMB-284)  [not reachable from main; same author date and subject as a20a754, counted once]
    a3eaf2b fix(voice): take the owner's personal memory credential out of the client's account
    35823a2 fix(testbed,voice): make the board a fixture, and make memory's failure audible
    061c9b1 fix(surface): clarify Testbed job counts (JIMB-284)
    05ae2a1 feat(docs): mise run docs:setup opens the runbook as a designed page
    32cbf4b fix(voice): the Pipecat path answered as Greg, not Skylar
    53f122b docs: a runbook for standing up a second workstation
    c04abbb fix(hooks): project recall was dead on any python below 3.11, and starved above it
    4e57dac chore(devops): taskdefs at e841922
    e841922 checkpoint: 2026-09-06T11:36:55Z auto-commit
    2cdb6ec fix(JIMB-280): page GorillaDesk jobs_for_day and preserve mirror failure through voice build_session
    a3bb7e5 fix(JIMB-280): repair AC2 enriched schedule for technician and AC6 provider-failure coverage
    2329294 docs(JIMB-282): record independent Gate 1 hold
    90e3992 docs(JIMB-282): replace stale evidence with current-ref proof
    4fdfafb docs(JIMB-280): update evidence to current-ref f35c73c — all AC satisfied, no product changes needed
    858217e chore(pm): record JIMB-280 and JIMB-282 lane recovery
    c2c4711 fix(JIMB-280): page GorillaDesk jobs_for_day and preserve mirror failure through voice build_session  [not reachable from main; same author date and subject as 2cdb6ec, counted once]
    02a7da7 fix(JIMB-280): repair AC2 enriched schedule for technician and AC6 provider-failure coverage  [not reachable from main; same author date and subject as a3bb7e5, counted once]
    9559b33 docs(JIMB-282): record independent Gate 1 hold  [not reachable from main; same author date and subject as 2329294, counted once]
    bcd0cb0 fix(JIMB-280): repair AC2 enriched schedule for technician and AC6 provider-failure coverage  [not reachable from main; same author date and subject as a3bb7e5, counted once]
    d487093 docs(JIMB-282): replace stale evidence with current-ref proof  [not reachable from main; same author date and subject as 90e3992, counted once]
    786341f docs(JIMB-280): update evidence to current-ref f35c73c — all AC satisfied, no product changes needed  [not reachable from main; same author date and subject as 4fdfafb, counted once]
    5fd1341 chore(pm): record JIMB-280 and JIMB-282 lane recovery  [not reachable from main; same author date and subject as 858217e, counted once]
    d6baf60 docs(JIMB-280): update evidence to current-ref f35c73c — all AC satisfied, no product changes needed  [not reachable from main; same author date and subject as 4fdfafb, counted once]
    7751ee0 docs(JIMB-282): replace stale evidence with current-ref proof  [not reachable from main; same author date and subject as 90e3992, counted once]
    909c526 chore(devops): taskdefs at f35c73c
    f35c73c fix(voice): bound the trace's per-call clocks
    61d1f0e chore(devops): taskdefs at f71914a
    8c40044 docs(mise): say which bench scores the line that answers the phone
    719711d style(voice): name the codes on the swallows the trace channel is built around
    f71914a docs(voice): which models will let you watch them think, measured
    241d5b7 chore(devops): taskdefs at c11dcc9
    72714ef fix(voice): the model probe was registered and structurally unable to fire
    c11dcc9 fix(voice,relay): make logging deliberate, and fix what the first live swap found
    e091162 chore(devops): taskdefs at d2d66d2
    d2d66d2 fix(voice): time the tools where the clock is honest, and price a model swap
    e9fe42f feat(voice): a developer trace channel and a model swap that needs no deploy
    ce7b855 checkpoint: 2026-09-06T04:29:59Z auto-commit
    297cf42 chore(devops): taskdefs at f1b138a
    f1b138a checkpoint: 2026-09-06T02:26:49Z auto-commit
    c762bc6 fix(technician): recognize direct confirmation of the selected visit
    a6efe2f fix(technician): listen through full schedules before advancing the call
    509a9ed chore(devops): taskdefs at 070b6b0
    070b6b0 fix(JIMB-280): deliver developer schedules and retain interrupted save receipts
    14ba64a docs(JIMB-276): retain completed Plane acceptance receipts
    0143167 docs(JIMB-276): record final review and landed diagnostic proof
    ea9bee8 Merge JIMB-276 EventBridge publisher diagnostics
    775964d fix(technician): wait for the final model acknowledgement before signing off
    60454f5 test(voice): accept numeric transcription of property confirmation
    0e3f6c0 test(voice): confirm the deployed property readback in live cue scenario
    318af0f fix(technician): recognize spoken one moment after numeric transcription
    34cea8c chore(devops): taskdefs at 97b0729
  
  === intelliforia ===
  (no commits)
  
  === delonet-company ===
  (no commits)
  
  === PoopToTheMoon ===
    a5748c0 feat(placement): measure socket layouts before freezing saved geometry
    98a626e fix(env): resolve 1Password references without plaintext files
  
  === pjangler ===
  (no commits)
  
  === bloodbank ===
    dbef526 envelope: optional 'ephemeral' extension for worktree-origin events
    d484d03 fix(asm): stop the tab blink from drowning deckard
    365b9be fix(hooks): every hermes and copilot event now says which repo it came from
    e8250af feat(asm): split attention into bell and gate, and make the surface class structural
    6124588 fix(asm): keep surface verdicts out of the telemetry hash, and tests out of prod
    e4858bd feat(hooks): Agent Hook Telemetry — did the hooks actually fire?
    2334800 feat(asm): the tab bar is a surface on the state machine, not a second one
    c6dfd19 feat(plane): close the functional label set, and reconcile drift
    bcdfa6c feat(agent-state): tabpaint, and promote as PRESENT rather than WORKING
    f2bb1a2 feat(agent-state): discover panes by observation, and clear a bell on focus
  
  === candystore ===
    f5a1fd8 query: surface envelope 'ephemeral' extension in /events previews
  
  === holocene ===
    58af0b2 docs(ia): hollowness safeguard — the hatch is never optional
    cd524fc docs(ia): design canvas source + adversarial review fixes
    1713287 docs(ia): decided IA redesign, verified ground truth, current-state audit
    8a2494d Pjangler migrate'
    e714303 feat(tooling): surface Agent Hook Telemetry

HERMES FLEET HEALTH
-------------------
**Status (authoritative): complete**

Hermes fleet: 29 agents registered; 16 timers (16 active, 0 failed); 6 cron jobs across 4 profiles (4 enabled); 4 job(s) reference a missing skill; 0 profile(s) with a stale ticker; 9 gateway unit(s) not running.
Metrics: agent_profile_dirs_missing=0, agents_registered=29, cron_jobs_enabled=4, cron_jobs_total=6, cron_jobs_unreadable=0, duplicate_cron_dirs=1, gateway_units_inactive=3, gateway_units_unknown=6, jobs_claiming_ok_contradicted=4, jobs_claiming_ok_unverified=2, jobs_with_missing_skill=4, jobs_with_past_next_run=0, profiles_scanned=40, profiles_unreadable_jobs=0, profiles_with_cron_jobs=4, profiles_with_stale_ticker=0, profiles_without_cron_dir=0, report_date=2026-09-06, sources_failed=0, sources_read=4, timers_active=16, timers_failed=0, timers_never_triggered=0, timers_total=16, timers_without_next_elapse=0, units_failed=1, units_not_found=1, units_total=58
Caveats:
  2 cron job(s) report last_status='ok' with no independent corroboration; last_status is a scheduler claim and is not treated as evidence of success
  4 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-09-07T10:01:45.517558Z (fleet state is current, not reconstructed for the report date)
  registry: 29 agents, 0 missing profile dir(s), 6 gateway unit(s) unknown to systemd, 3 not active
    agent automatic-ai-pm: hermes-automatic-ai-pm-gateway.service not active
    agent condaleeza: hermes-condaleeza-gateway.service not active
    agent delocontainers-pm: hermes-delocontainers-pm-gateway.service not active
    agent delonet-director: hermes-delonet-director-gateway.service unknown to systemd; hermes-delonet-director-heartbeat.timer unknown to systemd
    agent drumjangler-pm: hermes-drumjangler-pm-gateway.service unknown to systemd
    agent hermes-agent-pm: hermes-hermes-agent-pm-gateway.service unknown to systemd
    agent intelliforia-voice-agent-pm: hermes-intelliforia-voice-agent-pm-gateway.service unknown to systemd
    agent nautilus-trader-pm: hermes-nautilus-trader-pm-gateway.service unknown to systemd
    agent tonnybox-pm: hermes-tonnybox-pm-gateway.service unknown to systemd
  systemd units: 58 matching, 1 failed, 1 not-found
    unit hermes-automatic-ai-pm-heartbeat.service: loaded/failed/failed
    unit hermes-tonnybox-pm-consumer.service: not-found/inactive/dead
  timers: 16 matching, 16 active, 0 failed, 0 with no next elapse, 0 never triggered
  cron: 40 profiles scanned (0 without a cron dir), 4 with jobs, 6 jobs (4 enabled), 0 stale ticker(s), 1 shared cron dir(s)
    profile 33god-pm.bak: shares its cron dir with 33god-pm
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-09-06T10:02:30.840284Z, next 2026-09-08T10:00:00Z
    job 33god-pm/Board Cranker implementation loop: disabled, schedule 'every 5m', last_status='ok' (claim, contradicted), last run 2026-09-05T12:48:43.347617Z, next none; skill(s) not installed: momo, project-lifecycle, subagent-driven-development, coding-strategy, pjangler, bloodbank-integration
    job 33god-pm.bak/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-09-06T10:02:30.840284Z, next 2026-09-08T10:00:00Z
    job 33god-pm.bak/Board Cranker implementation loop: disabled, schedule 'every 5m', last_status='ok' (claim, contradicted), last run 2026-09-05T12:48:43.347617Z, next none; skill(s) not installed: momo, project-lifecycle, subagent-driven-development, coding-strategy, pjangler, bloodbank-integration
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='ok' (claim, contradicted), last run 2026-09-06T13:02:15.633775Z, next 2026-09-07T13:00:00Z; skill(s) not installed: obsidian, llm-wiki
    job james-brennan-pm/JIMB hourly two-lane pass: enabled, schedule 'every 60m', last_status='ok' (claim, contradicted), last run 2026-09-07T08:00:12.943106Z, next 2026-09-07T11:00:44.354657Z; skill(s) not installed: momo, project-lifecycle, project-invariants, coding-strategy

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 1 tick(s) across 1 of 1 tracked repositories on 2026-09-06; 0 PR(s) triaged, 0 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged; 1 tick(s) did not succeed.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=0, merge_candidates=0, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=0, prs_triaged=0, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=1, ticks_in_window=1, ticks_noop=0
Caveats:
  pr-crusher activity is read from its durable state, not Candystore: its Bloodbank publisher has been observed disabled, so absence of PR events on the bus does not mean absence of PR activity
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-09-06T04:00:00Z .. 2026-09-07T04:00:00Z for 2026-09-06 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 0
    tick 41 tick-000041-20260906T070944.108532Z completed=2026-09-06T07:10:48.204799Z provider=opencode_free provider_status=failed result_status=failed success=False automerge=False
      summary: provider did not produce a schema-valid tick result

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: 6 of 6 due days delivered over 2026-08-31..2026-09-06 (0 gap(s)); 6 completion event(s), 0 archive/event disagreement(s); delivered streak 6.
Metrics: archive_event_disagreements=0, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=6, days_archive_without_event=0, days_checked=7, days_delivered=6, days_event_without_archive=0, days_in_progress=1, days_invalid=0, days_missing=0, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=0, delivery_health=ok, events_found=6, lookback_days=7
Detail:
  window 2026-08-31..2026-09-06 (7 days), report_date 2026-09-06
  delivery health ok
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.reporting.report.completed: reachable
  2026-08-31 delivered events=1 claimed=complete generation=a812ccd90e1f4a33b4c9bc5191fb4550
  2026-09-01 delivered events=1 claimed=complete generation=2d67cd88cf2d4aa28984166f64a4a497
  2026-09-02 delivered events=1 claimed=complete generation=c7254d3857b84e25a23ecb77dd1be6f6
  2026-09-03 delivered events=1 claimed=complete generation=9ae59ab2fea74beb9111f4b899d83602
  2026-09-04 delivered events=1 claimed=complete generation=1589bf5d21f44a90b8300e70ad825ddc
  2026-09-05 delivered events=1 claimed=complete generation=4ac32fc52b1e4f14951337626ad5cc08
  2026-09-06 in-progress events=0 reason=this run is producing this day; it publishes after collection

COVERAGE
--------
4 of 4 enabled sections completed.
No section is degraded.

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | complete | 2026-09-07T10:01:45.510916Z | 2026-09-08T10:01:45.510916Z | - |
| fleet-health | complete | 2026-09-07T10:01:45.517558Z | 2026-09-08T10:01:45.517558Z | - |
| pr-maintenance | complete | 2026-09-07T10:01:45.568743Z | 2026-09-08T10:01:45.568743Z | - |
| report-delivery | complete | 2026-09-07T10:01:45.585984Z | 2026-09-08T10:01:45.585984Z | - |
Required: dev-activity (complete), report-delivery (complete).
Overall status complete is derived from the run manifest above, not asserted.

Run ddr-2026-09-06-69c5d283 · generated 2026-09-07T10:02:38.845307Z · overall status: complete
