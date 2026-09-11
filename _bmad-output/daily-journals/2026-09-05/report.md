Daily Developer Report — 2026-09-05
Summary written by anthropic/claude-opus-5. Everything below it is rendered by the pipeline from files it read — every status, metric and caveat is on this page whether or not a model answered.

SUMMARY
-------
**Bloodbank grew an Agent State Machine end-to-end today — event-driven core, sweeper, /proc-backed candidate resolution, board publication — and 33GOD, Holocene and Candystore all moved to consume it the same day.**

## What happened

### The Agent State Machine landed across four repositories

The day's centre of gravity. `bloodbank` carried eleven commits building it from nothing: `9abd694` (event-driven ASM over standardized hooks), `95b4757` (the sweeper's `stale` and `gone` states — "the two states no event can produce"), `4c29ff6` (candidate resolution via `/proc` as the live registry), `7fd8bbf` (a Hermes agent is a profile; the per-profile gateway is its pid), `1368aad` (per-pane state projected from the bus *and* from reality), `e359aa0` (sweeper discovers every live agent and publishes the board), plus `ed2d735` and `471396f` closing correctness gaps on the attention window and top-level board health. `02daea9` added `invocation.failed` so the bus carries a failure signal at all. `2f2d484` scaffolds the state machine onto any Plane board. `holocene` picked it up in `70d5118`, and `33GOD` pinned each step through nine bump commits ending at `3261811`.

### 33GOD-55's integration cost more than the work

Spec gate accepted, quality/security review accepted, then the integration transport collapsed repeatedly: an internally inconsistent receipt, a bad evidence hash, a Kimi launcher that failed *before* execution, two pre-execution output-schema rejections. Five distinct recovery decisions before `33GOD-55` was accepted as integrated on hash-consistent post-merge verification — which then unblocked `33GOD-54`, itself split into a no-source differential and publication child after exhausting its budget. `33GOD-56` went out as the sole no-source Board Cranker WIP.

### james-brennan: voice turn-taking, 34 commits

JIMB-282 shipped context-sensitive acknowledgements (`39b6128`, `c860b85`) after a refinement-then-hold-then-pull cycle. JIMB-264 landed waiting cues (`1be6bbe`, `5b60236`), JIMB-276 made EventBridge publisher status honest (`360bfbf`), and `7748bc4` opened a second implementation lane with exclusive ticket ownership. JIMB-222 stayed held all day — deployment parity, cohort/CRM geography repair, and AC5 live proof requiring separate Jarad and Damian receipts.

### candystore closed its critical path

Six commits: provenance classification (CANDYS-46), flat row contract and PM/ops summarizers (CANDYS-41/43), named lenses (CANDYS-47/48), bucketed header counts (CANDYS-49), project feed screen (CANDYS-52), then `f4ca797` recording the critical path complete with four data-forced corrections.

## Needs you

- **Four cron jobs claim `ok` while missing the skills they need to run.** `james-brennan-pm/JIMB hourly two-lane pass` is enabled, ran at 09:12 today, and lacks `momo`, `project-lifecycle`, `project-invariants`, `coding-strategy`. `delodocs-pm/delodocs-triage-second-pass` lacks `obsidian` and `llm-wiki`. Both are green in the scheduler and doing nothing.
- **`33god-pm.bak` shares its cron dir with `33god-pm`** — the `delonet-daily-report` job is duplicated across both profiles at identical schedule and last-run. Two profiles, one directory, one job firing twice or racing.
- **Eight gateway units are not running**: three inactive (`condaleeza`, `delocontainers-pm`, `ssbnk-pm`), five unknown to systemd entirely (`delonet-director` — which is also missing its heartbeat timer — plus `drumjangler-pm`, `hermes-agent-pm`, `intelliforia-voice-agent-pm`, `nautilus-trader-pm`). `hermes-automatic-ai-pm-heartbeat.service` is loaded/failed.
- **The Board Cranker loop is disabled** while `33GOD-56` was dispatched today as Board Cranker implementation work.
- **Fifteen `delo.sh` services 502'd and were restarted** in one operational sweep — `plane.delo.sh` across seven paths, plus `portainer`, `pgadmin`, `drive`, `ntfy`, `adguard`, `notebooklm`, `naipkins`, `get`. That pattern is host-level, not per-service.
- **pr-crusher's only tick failed**: tick 40 on `delorenj/mcp-server-trello`, provider `opencode_free`, "provider did not produce a schema-valid tick result". Same failure mode as the 33GOD-55 recoveries.

## Worth noting

6 of 34 `james-brennan` commits are off-HEAD — the JIMB-261 Gemini series (`7a68fba`, `61151f6`, `1659180`, `ef0c571`) and `1cb930f` sit unmerged, consistent with JIMB-261 being on a reviewed Gemini hold with false WIP released. Report delivery is clean: 6 of 6 days, zero gaps, streak of 6. Four configured roots produced nothing today (`intelliforia`, `delonet-company`, `PoopToTheMoon`, `pjangler`), and three projects active in events (`bb`, `project`, `slowburns`) have no configured git root, so 4,206 slowburns events and 4,327 `project` events are visible only as decisions and sessions.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): complete**

14105 events across 6 project(s) on 2026-09-05: 308 session(s), 51 decision(s), 13 committing session(s), 60 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (55 on the checked-out branch, 6 only on other refs); peak 2026-09-05T12:00:00Z (1321 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=13, decision_count=51, event_count=14105, git_commit_count=60, git_commit_replays_collapsed=1, git_commits_off_head=6, git_commits_on_head=55, git_repos_failed=0, git_repos_logged=5, git_repos_missing=0, git_repos_no_commits=4, git_repos_with_off_head_commits=1, git_root_name_collisions=0, git_roots_active_in_events=3, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=True, peak_hour=2026-09-05T12:00:00Z, peak_hour_event_count=1321, project_count=6, projects_without_root=3, session_count=308
Caveats:
  decisions truncated: showing 30 of 51
  operational events truncated: showing 20 of 29
  git scope is 'all-refs': every ref of each configured repository was read for 2026-09-05 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  4 configured project root(s) were read across all refs of each repository and had no commits on 2026-09-05: intelliforia, delonet-company, PoopToTheMoon, pjangler
  6 of 61 commit(s) are not reachable from their repository's checked-out branch (unmerged or otherwise off-HEAD work) and are counted here: james-brennan 6 of 34 (checked out: main)
  1 commit(s) repeat the author date and subject of another commit in the same window (rebase or cherry-pick copies) and were counted once, not twice: james-brennan 1
  3 project(s) active in events have no configured project root, so no git log was read for them: bb, project, slowburns
Detail:
  === Events by CLI ===
    codex        5663
    hermes       4981
    claude       3075
    unknown       219
    copilot       166
    reportctl       1
  
  === Events by project ===
    project          4327
    slowburns        4206
    james-brennan    3450
    unknown          1350
    bb                524
    candystore        226
    intelliforia       22
  
  === Decisions recorded ===
    [james-brennan] JIMB-276: Use the second JIMB lane for JIMB-276's bounded EventBridge status repair
    [james-brennan] JIMB-282: Hold JIMB-282 at Gate 1 and return the sole WIP to its existing implementer
    [james-brennan] JIMB-282: Hold JIMB-282 at Gate 1 and return the sole WIP to its existing implementer
    [james-brennan] JIMB-282: Pull JIMB-282 into implementation as the sole WIP item
    [james-brennan] JIMB-282: Refine JIMB-282 into an explicit cue contract before implementation
    [james-brennan] JIMB-222: Gate JIMB-222 human QA behind notification and verifier readiness
    [james-brennan] JIMB-222: Continue holding JIMB-222 on AC5 live proof
    [33god] 33GOD-56: Dispatch 33GOD-56 as the sole no-source Board Cranker implementation WIP
    [33god] 33GOD-54: Split exhausted 33GOD-54 into a no-source sequential differential and publication child
    [33god] 33GOD-54: Resume 33GOD-54 as the sole implementation WIP after 33GOD-55 integrated the Git travel-guard repair
    [33god] 33GOD-55: Accept 33GOD-55 as integrated after hash-consistent post-merge verification and unblock 33GOD-54
    [33god] 33GOD-55: Treat post-merge verifier r1 as an environment failure and dispatch one fresh Kimi recovery
    [33god] 33GOD-55: Dispatch one fresh source-free post-merge verifier for 33GOD-55 instead of accepting an internally inconsistent integration receipt
    [33god] 33GOD-55: Hold 33GOD-55 integration acceptance until its evidence hash is corrected
    [33god] 33GOD-55: Dispatch one corrected 33GOD-55 Kimi prompt-mode integration transport recovery
    [james-brennan] JIMB-222: Hold JIMB-222 in E2E QA after deployment parity; require separate Jarad and Damian live approval receipts
    [33god] 33GOD-55: Hold 33GOD-55 after the Kimi recovery launcher failed before execution and preserve one corrected transport retry
    [33god] 33GOD-55: Dispatch the final 33GOD-55 integration transport recovery through Kimi without provider-side output schema enforcement
    [33god] 33GOD-55: Hold 33GOD-55 as sole WIP after integration recovery r2 was rejected before execution
    [33god] 33GOD-55: Hold 33GOD-55 integration after pre-execution output-schema rejection
    [33god] 33GOD-55: Accept 33GOD-55 quality/security review and dispatch immutable PR integration
    [james-brennan] JIMB-222: Deploy Surface at the same reviewed commit as the Relay correction
    [slowburns] SLOWBURNS-40: Hold SLOWBURNS-40 after safe F003/F004 activation until one additional acceptance unit and render are explicitly authorized
    [slowburns] SLOWBURNS-40: Accept the F003/F004 diagnostics patch after independent gates while keeping SLOWBURNS-40 on HOLD
    [james-brennan] JIMB-222: Hold JIMB-222 and repair cohort publication against current CRM geography
    [slowburns] SLOWBURNS-40: Hold the F003 quality gate for Cartesia safe request-ID loss and remediate before accepting diagnostics
    [33god] 33GOD-55: Accept 33GOD-55 specification gate and dispatch independent quality/security review
    [james-brennan] JIMB-222: Select JIMB-222 for evidence repair and independent QA, not a new implementation
    [33god] 33GOD-55: Retry 33GOD-55 specification review through Kimi on the unchanged immutable range
    [slowburns] SLOWBURNS-40: Hold SLOWBURNS-40 after the single replacement render and add sanitized provider diagnostics before any further live proof
    ... showing 30 of 51 decisions
  
  === Sessions that committed ===
    project (claude, 11 turns): 1 commit(s)
    project (claude, 23 turns): 1 commit(s)
    project (claude, 61 turns): 2 commit(s)
    project (claude, 54 turns): 1 commit(s)
    bb (claude, 20 turns): 1 commit(s)
    slowburns (codex, 2 turns): 2 commit(s)
    unknown (codex, 0 turns): 1 commit(s)
    unknown (codex, 6 turns): 4 commit(s)
    unknown (codex, 3 turns): 1 commit(s)
    unknown (codex, 0 turns): 1 commit(s)
    james-brennan (codex, 1 turns): 1 commit(s)
    unknown (codex, 9 turns): 1 commit(s)
    candystore (claude, 41 turns): 4 commit(s)
  
  === Operational notes ===
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    [unknown] updated: (no detail)
    [unknown] updated: (no detail)
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://plane.delo.sh/live/
    [unknown] exited: restarted container after HTTP 502 on https://plane.delo.sh/spaces/
    [unknown] exited: restarted container after HTTP 502 on https://plane.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://portainer.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://plane.delo.sh/god-mode/
    [unknown] exited: restarted container after HTTP 502 on https://plane.delo.sh/api/
    [unknown] exited: restarted container after HTTP 502 on https://plane.delo.sh/plane-bucket
    [unknown] exited: restarted container after HTTP 502 on https://pgadmin.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://notebooklm.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://adguard.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://drive.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://naipkins.delo.sh/api/naipkins/v1/healthz
    [unknown] exited: restarted container after HTTP 502 on https://ntfy.delo.sh/
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    ... showing 20 of 29 operational events
  
  === Git log by repository ===
  === 33GOD ===
    3261811 chore(bloodbank): bump — ASM board reports its own health
    8e5457b chore: bump bloodbank + holocene — ASM discovery and the remote board
    6028eba chore(bloodbank): bump for the agent-state projector
    3f433ee chore(bloodbank): bump to ASM candidate resolution (33GOD-58 step 1)
    82119f6 chore(bloodbank): bump — attention window ends on new work
    ec6e5f1 chore(bloodbank): bump to profile-keyed Hermes agent identity
    db339ba feat(bmad): land BMAD cycle outputs and component state — Aug 19 through Sept 4
    6f1d6c3 chore(bloodbank): bump to the ASM sweeper
    49fe9f4 chore(bloodbank): bump to the Agent State Machine
  
  === james-brennan ===
    (checked out: main; 6 of 34 commit(s) below are not reachable from it)
    360bfbf fix(JIMB-276): report EventBridge publisher status honestly
    97b0729 fix(voice): prevent conflicting OpenRouter reasoning parameters
    34d4555 chore(devops): taskdefs at 7ab1f5e
    7ab1f5e fix(voice): restore waiting speech during initial model latency
    8ea221e chore(devops): taskdefs at e3cc17f
    6efe81d fix(JIMB-276): report EventBridge publisher status honestly  [not reachable from main; same author date and subject as 360bfbf, counted once]
    2483a0f checkpoint: 2026-09-05T23:23:29Z auto-commit
    e3cc17f fix(voice): keep pending answers alive through incidental noise
    2385c4c chore(devops): taskdefs at c860b85
    2da6b91 Install PM claim snapshot through the supported cron script path
    7748bc4 Allow two implementation lanes with exclusive ticket ownership
    c860b85 fix(voice): make progress cues follow the current turn (JIMB-282)
    39b6128 JIMB-282: make Frank Line acknowledgements context-sensitive
    12d2856 checkpoint: 2026-09-05T21:22:29Z auto-commit
    6ddd983 docs(JIMB-282): refine acknowledgement acceptance
    1cb930f fix(surface): show the relay's real reason on a refused note read  [not reachable from main]
    38ce602 docs(JIMB-222): capture AC5 runtime blockers
    e674a51 docs(JIMB-222): record live AC5 hold
    4f7a04f docs(JIMB-222): record deployed parity hold
    1caf2bc checkpoint: 2026-09-05T08:06:22Z auto-commit
    10c2f93 chore(devops): taskdefs at edab4d7
    edab4d7 JIMB-222 derive published cohort from current CRM destination
    a54e2ae docs(JIMB-261): record reviewed Gemini hold
    449e994 checkpoint: 2026-09-05T05:02:23Z auto-commit
    ef0c571 fix(JIMB-261): preserve cancelled Gemini tool history  [not reachable from main]
    1659180 fix(JIMB-261): preserve Gemini reasoning across tool loopback  [not reachable from main]
    61151f6 fix(JIMB-261): pin Gemini low thinking on the phone path  [not reachable from main]
    7a68fba fix(JIMB-261): harden benchmark evidence parsing  [not reachable from main]
    ee3b33d checkpoint: 2026-09-05T01:58:27Z auto-commit
    4bbfa2d docs: record JIMB-264 deployment and live waiting-cue evidence
    5b60236 fix(technician): wait through spoken progress acknowledgements
    7974560 chore(devops): taskdefs at 1be6bbe
    1be6bbe fix(voice): speak waiting cues and report the conversation model (JIMB-264)
    0225a7a docs(JIMB-261): release false WIP on benchmark hold
  
  === intelliforia ===
  (no commits)
  
  === delonet-company ===
  (no commits)
  
  === PoopToTheMoon ===
  (no commits)
  
  === pjangler ===
  (no commits)
  
  === bloodbank ===
    2f2d484 feat(plane): scaffold the 33GOD state machine onto any board
    471396f fix(asm): set the board's top-level health so the card is not always unknown
    e359aa0 feat(asm): the sweeper now discovers every live agent and publishes the board
    1368aad feat(agent-state): project per-pane agent state from the bus AND from reality
    4c29ff6 feat(asm): candidate resolution for ticket claiming — /proc is the live registry
    02daea9 feat(agent-hooks): publish invocation.failed, so the bus carries a failure signal
    ed2d735 fix(asm): the attention window ends when the agent starts new work
    7fd8bbf feat(asm): a Hermes agent is a profile, and the per-profile gateway is its pid
    95b4757 feat(asm): sweeper — stale and gone, the two states no event can produce
    9abd694 feat(asm): event-driven Agent State Machine over the standardized hooks
    5dd6ef2 feat(n8n): show the pickup on the board a second after dispatch
  
  === candystore ===
    f4ca797 docs(plan): record the critical path complete, with four more data-forced corrections
    82bc802 feat(ui): the project feed screen (CANDYS-52)
    6cf14e2 feat(timeline): bucketed counts for the header strip (CANDYS-49)
    6fc7542 feat(feed): named lenses and tool-call collapse (CANDYS-47/48)
    bb0258e feat(feed): flat row contract + the PM/ops summarizers (CANDYS-41/43)
    d9747a3 feat(provenance): classify where every event came from (CANDYS-46)
  
  === holocene ===
    70d5118 feat(tooling): surface the Agent State Machine board

HERMES FLEET HEALTH
-------------------
**Status (authoritative): complete**

Hermes fleet: 28 agents registered; 15 timers (15 active, 0 failed); 6 cron jobs across 4 profiles (4 enabled); 4 job(s) reference a missing skill; 0 profile(s) with a stale ticker; 8 gateway unit(s) not running.
Metrics: agent_profile_dirs_missing=0, agents_registered=28, cron_jobs_enabled=4, cron_jobs_total=6, cron_jobs_unreadable=0, duplicate_cron_dirs=1, gateway_units_inactive=3, gateway_units_unknown=5, jobs_claiming_ok_contradicted=4, jobs_claiming_ok_unverified=2, jobs_with_missing_skill=4, jobs_with_past_next_run=0, profiles_scanned=40, profiles_unreadable_jobs=0, profiles_with_cron_jobs=4, profiles_with_stale_ticker=0, profiles_without_cron_dir=1, report_date=2026-09-05, sources_failed=0, sources_read=4, timers_active=15, timers_failed=0, timers_never_triggered=0, timers_total=15, timers_without_next_elapse=0, units_failed=1, units_not_found=1, units_total=69
Caveats:
  2 cron job(s) report last_status='ok' with no independent corroboration; last_status is a scheduler claim and is not treated as evidence of success
  4 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-09-06T10:00:46.256330Z (fleet state is current, not reconstructed for the report date)
  registry: 28 agents, 0 missing profile dir(s), 5 gateway unit(s) unknown to systemd, 3 not active
    agent condaleeza: hermes-condaleeza-gateway.service not active
    agent delocontainers-pm: hermes-delocontainers-pm-gateway.service not active
    agent delonet-director: hermes-delonet-director-gateway.service unknown to systemd; hermes-delonet-director-heartbeat.timer unknown to systemd
    agent drumjangler-pm: hermes-drumjangler-pm-gateway.service unknown to systemd
    agent hermes-agent-pm: hermes-hermes-agent-pm-gateway.service unknown to systemd
    agent intelliforia-voice-agent-pm: hermes-intelliforia-voice-agent-pm-gateway.service unknown to systemd
    agent nautilus-trader-pm: hermes-nautilus-trader-pm-gateway.service unknown to systemd
    agent ssbnk-pm: hermes-ssbnk-pm-gateway.service not active
  systemd units: 69 matching, 1 failed, 1 not-found
    unit hermes-automatic-ai-pm-heartbeat.service: loaded/failed/failed
    unit hermes-tonnybox-pm-consumer.service: not-found/inactive/dead
  timers: 15 matching, 15 active, 0 failed, 0 with no next elapse, 0 never triggered
  cron: 40 profiles scanned (1 without a cron dir), 4 with jobs, 6 jobs (4 enabled), 0 stale ticker(s), 1 shared cron dir(s)
    profile 33god-pm.bak: shares its cron dir with 33god-pm
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-09-05T10:02:06.505314Z, next 2026-09-07T10:00:00Z
    job 33god-pm/Board Cranker implementation loop: disabled, schedule 'every 5m', last_status='ok' (claim, contradicted), last run 2026-09-05T12:48:43.347617Z, next none; skill(s) not installed: momo, project-lifecycle, subagent-driven-development, coding-strategy, pjangler, bloodbank-integration
    job 33god-pm.bak/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-09-05T10:02:06.505314Z, next 2026-09-07T10:00:00Z
    job 33god-pm.bak/Board Cranker implementation loop: disabled, schedule 'every 5m', last_status='ok' (claim, contradicted), last run 2026-09-05T12:48:43.347617Z, next none; skill(s) not installed: momo, project-lifecycle, subagent-driven-development, coding-strategy, pjangler, bloodbank-integration
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='ok' (claim, contradicted), last run 2026-09-05T13:03:41.862415Z, next 2026-09-06T13:00:00Z; skill(s) not installed: obsidian, llm-wiki
    job james-brennan-pm/JIMB hourly two-lane pass: enabled, schedule 'every 60m', last_status='ok' (claim, contradicted), last run 2026-09-06T09:12:06.880007Z, next 2026-09-06T10:12:06.880007Z; skill(s) not installed: momo, project-lifecycle, project-invariants, coding-strategy

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 1 tick(s) across 1 of 1 tracked repositories on 2026-09-05; 0 PR(s) triaged, 0 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged; 1 tick(s) did not succeed.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=0, merge_candidates=0, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=0, prs_triaged=0, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=1, ticks_in_window=1, ticks_noop=0
Caveats:
  pr-crusher activity is read from its durable state, not Candystore: its Bloodbank publisher has been observed disabled, so absence of PR events on the bus does not mean absence of PR activity
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-09-05T04:00:00Z .. 2026-09-06T04:00:00Z for 2026-09-05 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 0
    tick 40 tick-000040-20260905T071353.352534Z completed=2026-09-05T07:14:55.587078Z provider=opencode_free provider_status=failed result_status=failed success=False automerge=False
      summary: provider did not produce a schema-valid tick result

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: 6 of 6 due days delivered over 2026-08-30..2026-09-05 (0 gap(s)); 6 completion event(s), 0 archive/event disagreement(s); delivered streak 6.
Metrics: archive_event_disagreements=0, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=6, days_archive_without_event=0, days_checked=7, days_delivered=6, days_event_without_archive=0, days_in_progress=1, days_invalid=0, days_missing=0, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=0, delivery_health=ok, events_found=6, lookback_days=7
Detail:
  window 2026-08-30..2026-09-05 (7 days), report_date 2026-09-05
  delivery health ok
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.reporting.report.completed: reachable
  2026-08-30 delivered events=1 claimed=complete generation=41135b0df7434d658f7b5bd65924f82b
  2026-08-31 delivered events=1 claimed=complete generation=a812ccd90e1f4a33b4c9bc5191fb4550
  2026-09-01 delivered events=1 claimed=complete generation=2d67cd88cf2d4aa28984166f64a4a497
  2026-09-02 delivered events=1 claimed=complete generation=c7254d3857b84e25a23ecb77dd1be6f6
  2026-09-03 delivered events=1 claimed=complete generation=9ae59ab2fea74beb9111f4b899d83602
  2026-09-04 delivered events=1 claimed=complete generation=1589bf5d21f44a90b8300e70ad825ddc
  2026-09-05 in-progress events=0 reason=this run is producing this day; it publishes after collection

COVERAGE
--------
4 of 4 enabled sections completed.
No section is degraded.

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | complete | 2026-09-06T10:00:46.249811Z | 2026-09-07T10:00:46.249811Z | - |
| fleet-health | complete | 2026-09-06T10:00:46.256330Z | 2026-09-07T10:00:46.256330Z | - |
| pr-maintenance | complete | 2026-09-06T10:00:46.335376Z | 2026-09-07T10:00:46.335376Z | - |
| report-delivery | complete | 2026-09-06T10:00:46.355477Z | 2026-09-07T10:00:46.355477Z | - |
Required: dev-activity (complete), report-delivery (complete).
Overall status complete is derived from the run manifest above, not asserted.

Run ddr-2026-09-05-ffbde4a0 · generated 2026-09-06T10:01:36.374247Z · overall status: complete
