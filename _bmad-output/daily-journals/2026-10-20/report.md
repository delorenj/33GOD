Daily Developer Report — 2026-10-20
Summary written by anthropic/claude-opus-5. Everything below it is rendered by the pipeline from files it read — every status, metric and caveat is on this page whether or not a model answered.

SUMMARY
-------
**Holocene absorbed the bulk of the day — roughly 30 commits closing out HOLOC-12 plus HOLOC-6/7/8 — while the report pipeline you are reading has silently failed to deliver a valid day since 2026-10-14.**

## What happened

**Holocene voice/memo hardening was the day's center of gravity.** The HOLOC-12 slice closed across many commits and six merges (`096a263`, `6fb6618`, `228a0d7`, `421acbf`, `27d39ea`, `60e6fc5`, `6456c24`): `153c6e7` makes `upload-proxy` refuse a PUT for an unroutable agent with a 422 so the pad shows NOT sent instead of SENT; `98280f4` moves that 422's reason into the JSON body because HTTP/2 drops the status phrase; `f4d944a` stops the watcher ever sending a shortened prompt (`transcript_too_long` hold instead of a 20000-char slice, prompt sha256 persisted before publish); `b8109e9` persists the selected agent across cold start and flags a roster older than 15 min; `7d5593b` deletes the dead client-side `VoiceLoop` dispatcher that had been falling back to `33god-pm` for unknown agent names. HOLOC-14 got two review passes on `agent-pad` (`c08fba2`, `4c921b7`, `5ce34e9`) cutting up to 13 s of dead air per round trip. Alongside that, `19c8177` shipped the read-only Director portfolio projection (HOLOC-8), `517b70c` the POLR container panel (HOLOC-7), `89cb361` ticket-velocity timelines (HOLOC-6). HOLOC-10, HOLOC-11 closed as answered; HOLOC-15 is the day's one recorded decision — accepted and closed on 28/28 production avatars and an 11/11 review PASS.

**Bloodbank matched it on the backend:** `f58cf48` landed the Jev+Clairic async turn-enricher lane (#271), and `edfe8dd`/`9513507`/`09996b1` made a deliberate `memo:cancel` legal rather than a page — the bus-side half of HOLOC-12.

**PJangler ran the BMAD upgrade live** — PJAN-167 took seven commits through a real `pj migrate bmad.version` (6.11.1-next.1 → 6.12.4) with preflight, rollback and a named no-write contract violation, plus PJAN-174 crank toggles and PJAN-175 docs-sync pinning (echoed here in `a4a99ca`).

**Delonet-company shipped DNET-F1 and DNET-F8** (`bc1b14e`, `11bb45b`) reading the PJangler registry and manifest identity, fail-closed, with the Director read API served as a loopback read-only unit (`db5adbf`).

Client work: `james-brennan` NAVI-81/NAVI-88 and `intelliforia` INT-367 (parser-version staleness).

## Needs you

- **Report delivery is `failed`:** 0 of 6 due days delivered, 2026-10-14 through 10-19. All six published a completion event claiming `partial` with nothing archived — the runs reported success they did not achieve. Same cause every day: `report.json` is missing the `turn-facts` section the schema now requires. The `turn-facts` collector was built today, so tomorrow may self-heal; the six-day hole will not.
- **28 of 34 Hermes gateway units are unknown to systemd**, including `33god-pm`. `delonet-company-reporter` has no profile dir at all. `hermes-tonnybox-pm-consumer.service` is not-found.
- **Five cron jobs reference skills that are not installed** — including `33god-pm/delonet-daily-report` itself (`delonet-daily-report` missing), which is how a scheduler reports `ok` while delivering nothing. `33god-pm/cronjob_manage` is in `error` with a recorded `last_error`.
- **pr-crusher is fully blocked:** its one tick failed because the credential broker rejected both `prc_github_read_token` and `prc_github_write_token`. Zero PRs triaged.

## Worth noting

Event collection hit its 50-page budget at 50000 events — today is **not fully covered**, and 41687 of those events carry no project. 10 of 63 commits sit off `main`: all 4 in `james-brennan`, 4 of 5 in `intelliforia`, 2 in `pjangler`. 10 of 21 annotated turns reported a blocker (GPU full, browser access, TOWE-7 grooming), and `gruvato` alone produced 42 commits in one 41-turn session with no configured git root to read.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): partial** -- event pagination stopped at the 50-page budget (50000 events read); the day is not fully covered

50000 events across 12 project(s) on 2026-10-20: 34008 session(s), 1 decision(s), 7 committing session(s), 63 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (53 on the checked-out branch, 10 only on other refs); peak 2026-10-20T09:00:00Z (8988 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=7, decision_count=1, event_count=50000, git_commit_count=63, git_commit_replays_collapsed=0, git_commits_off_head=10, git_commits_on_head=53, git_repos_failed=0, git_repos_logged=7, git_repos_missing=0, git_repos_no_commits=2, git_repos_with_off_head_commits=3, git_root_name_collisions=0, git_roots_active_in_events=4, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=True, peak_hour=2026-10-20T09:00:00Z, peak_hour_event_count=8988, project_count=12, projects_without_root=8, session_count=34008
Caveats:
  git scope is 'all-refs': every ref of each configured repository was read for 2026-10-20 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  2 configured project root(s) were read across all refs of each repository and had no commits on 2026-10-20: PoopToTheMoon, candystore
  10 of 63 commit(s) are not reachable from their repository's checked-out branch (unmerged or otherwise off-HEAD work) and are counted here: james-brennan 4 of 4 (checked out: main), intelliforia 4 of 5 (checked out: main), pjangler 2 of 12 (checked out: main)
  8 project(s) active in events have no configured project root, so no git log was read for them: 33god, bb, client-portal, delodocs, greeninbetween, gruvato, infra, tower-of-dumb-things
Detail:
  === Events by CLI ===
    claude                        21702
    unknown                       16391
    hermes                         8400
    opencode                       1935
    antigravity                    1499
    codex                            67
    bb-emit                           4
    reportctl                         1
    memory_performance_analyzer       1
  
  === Events by project ===
    unknown                41687
    holocene                1888
    33god                   1769
    pjangler                1369
    greeninbetween          1126
    gruvato                  931
    client-portal            791
    james-brennan            279
    intelliforia              87
    infra                     47
    delodocs                  11
    tower-of-dumb-things      11
    bb                         4
  
  === Decisions recorded ===
    [HOLOC] HOLOC-15: Accept HOLOC-15 and close: production verified 28/28 avatars, 0 letter tiles; review PASS 11/11, 0 discrepancies
  
  === Sessions that committed ===
    holocene (claude, 16 turns): 6 commit(s)
    pjangler (antigravity, 114 turns): 2 commit(s)
    unknown (claude, 1 turns): 6 commit(s)
    unknown (claude, 12 turns): 9 commit(s)
    unknown (claude, 1 turns): 5 commit(s)
    unknown (claude, 4 turns): 7 commit(s)
    gruvato (claude, 41 turns): 42 commit(s)
  
  === Operational notes ===
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
    [unknown] completed: (no detail)
    [unknown] started: (no detail)
  
  === Git log by repository ===
  === 33GOD ===
    a4a99ca chore(pjangler): PJAN-175 advance core docs sync template
  
  === james-brennan ===
    (checked out: main; 4 of 4 commit(s) below are not reachable from it)
    fb90c35b feat(surface): a question card reads 'Question from \<technician>' instead of 'Job not identified' (NAVI-81) (#751)  [not reachable from main]
    25e0a32d feat(surface): a question card reads 'Question from \<technician>' instead of 'Job not identified' (NAVI-81)  [not reachable from main]
    1f737eb1 feat(relay): retire-phone marks a phone call the operator let go as handled; no count or sweep holds it (NAVI-88) (#750)  [not reachable from main]
    f66e57d3 feat(relay): retire-phone marks a phone call the operator let go as handled; no count or sweep holds it (NAVI-88)  [not reachable from main]
  
  === intelliforia ===
    (checked out: main; 4 of 5 commit(s) below are not reachable from it)
    018c2565 fix(INT-367): a parser version bump only marks the documents it changed as stale (#825)
    6285c222 test(INT-367): AST scan catches any comparison with PARSER_VERSION  [not reachable from main]
    ab5f5a3a fix(INT-367): state the v4 scope truthfully and pin the 97153/97155 side effect  [not reachable from main]
    27e2aa59 fix(INT-367): PARSER_CHANGES as records, not an int-keyed dict (org-settings guard)  [not reachable from main]
    1dc8e0aa fix(INT-367): a parser version bump only marks the documents it changed as stale  [not reachable from main]
  
  === delonet-company ===
    2b5fdb9 docs(DNET-F8): evidence, review dispositions, live verification; F8 deployed
    11bb45b fix(portfolio): read PJangler manifest identity (project_id), legacy project_slug as input only (DNET-F8)
    c331350 docs(DNET-F1): evidence, review dispositions, live verification; F1 deployed
    bc1b14e feat(portfolio): read the PJangler registry service, fail closed (DNET-F1)
    e6b0240 docs(contracts): independent-review fixes to the Director read API contract (DNET-5)
    db5adbf feat(ops): serve the Director read API as a loopback read-only user unit; contract review for HOLOC-8 (DNET-5)
  
  === PoopToTheMoon ===
  (no commits)
  
  === pjangler ===
    (checked out: main; 2 of 12 commit(s) below are not reachable from it)
    20468ee fix(bmad): PJAN-167 review follow-ups — rollback ordering, honest inventory, narrower exclusions, pins
    1b0e366 chore(template): PJAN-175 pin core docs sync task
    dc3dc96 fix(bmad): PJAN-167 keep runtime state out of tree snapshots and rollback
    11dc6ab chore(bmad): PJAN-167 live pj migrate bmad.version — BMAD 6.11.1-next.1 -> 6.12.4
    87a58f6 fix(bmad): PJAN-167 name the paths behind a g33 no-write contract violation
    f167047 fix(bmad): PJAN-167 live bmad.version upgrade — stable externals, honest errors, writable rollback
    7890213 feat(bmad): PJAN-167 g33 pre-update preflight, preservation handoff, and rollback
    4d1a17b Squash commits from PJAN-174-crank-commands
    b3fa118 PJAN-174: portable-test-paths — no machine-specific paths in the crank suite fixtures  [not reachable from main]
    c8558a9 PJAN-174: pj crank enable|disable|list|log — project-native crank toggles  [not reachable from main]
    282aa68 Merge remote-tracking branch 'origin/main' into wip/mise-config-update
    e3c9129 wip(mise): add env:materialize task watching .env.op
  
  === bloodbank ===
    f58cf48 feat(turn-enricher): Jev+Clairic async annotation lane for conversation turns (#271)
    09996b1 merge: HOLOC-12 - a deliberate memo cancel is muted in ntfy-router and legal in memo.failed (stage cancelled, after_dispatch)
    9513507 test(audio): fold the cancel-contract test fix into the stage 'cancelled' change
    edfe8dd fix(audio): memo:cancel is not a page; audio.memo.failed stage 'cancelled' + after_dispatch in the schema
  
  === candystore ===
  (no commits)
  
  === holocene ===
    19c8177 feat(director): HOLOC-8 read-only Director portfolio projection (Director tab)
    89cb361 feat(velocity): HOLOC-6 range-scoped ticket velocity timeline (1h/1d/3d, project lanes, time-scaled axis)
    5160411 docs(holoc-11): close as answered; AC table and supersession note
    5f80896 fix(containers): skips come from the newest finished run, so a run still probing does not blank them
    517b70c feat(containers): HOLOC-7 POLR: last run, recent restarts, skips, mood; correct cooldown and dead semantics
    1cb0ad2 docs(holoc-10): close as answered; record evidence decision
    9a86107 fix(agent-pad): blank referer/origin on the /roster dev proxy (HOLOC-15)
    68c94a8 merge: HOLOC-12 decision review fixes
    0ede193 fix(inbox-watcher): HOLOC-12 decision review: re-transcribe sends a fresh command, sticky batch lane, revive marker, stale verdicts, reply prompt match, cancel retract, sidecar cap, unwind wait
    ebae46b fix(voice): a failure or cancel the memo moved past (later stage fact, revive marker) no longer decides /voice
    60e6fc5 merge: HOLOC-12 operator decisions (part 2)
    6456c24 merge: HOLOC-12 operator decisions (part 1)
    20e3f15 feat(inbox-watcher): HOLOC-12 escalate turn timeouts to the batch lane, full-text sidecar for the phone, memo:cancel
    3536acc feat(voice): show cancelled, escalated and late-reply memos in /voice
    27d39ea merge: HOLOC-12 review fixes (part 3)
    421acbf merge: HOLOC-12 review fixes (part 2)
    228a0d7 merge: HOLOC-12 review fixes (part 1)
    081152a fix(upload-proxy,inbox-watcher): HOLOC-12 review - roster-based route check, re-transcribe truncated memos on retry
    8f5909b fix(agent-pad): HOLOC-12 review - final refusals only from the proxy, rejected rows self-heal
    c234282 fix(auto): HOLOC-12 - speak and tone a proxy rejection instead of silence
    98280f4 fix(upload-proxy): HOLOC-12 - the 422 for an unroutable agent carries its reason as JSON (HTTP/2 drops the status phrase, and the pad reads the body)
    096a263 merge: HOLOC-12 closing slice (worktree-wf_fe6073c1-588-3)
    72b009e merge: HOLOC-12 closing slice (worktree-wf_fe6073c1-588-2)
    6fb6618 merge: HOLOC-12 closing slice (worktree-wf_fe6073c1-588-1)
    153c6e7 feat(upload-proxy): HOLOC-12 - refuse a PUT under inbox/\<agent>/ for an agent the gateway cannot route (422, not stored, one terminal failed fact an hour per key; fails open when the registry or memo_common is unreadable), so the pad shows NOT sent instead of SENT; watcher README
    b8109e9 feat(agent-pad): HOLOC-12 - the selected agent survives a cold start (IndexedDB, restored as a selection only), a roster older than 15 min or whose last fetch failed is flagged (static), and a permanent 4xx upload rejection keeps the audio but stops retrying it
    f4d944a fix(inbox-watcher): HOLOC-12 - never send a shortened prompt (transcript_too_long hold instead of the 20000-char slice; compact() only shortens done/skipped memos; prompt sha256 persisted before the publish and verified at send), hold a memo whose object changed after discovery (object_changed), a memo held at receive for an unroutable agent retries from receive and a dispatch with no transcript is held (no_transcript) instead of a KeyError
    7d5593b chore(auto): HOLOC-12 - remove the dead client-side voice-loop dispatcher (VoiceLoop, VoiceLoopRunner, NatsClient, their tests); it published client-authored bloodbank.cmd.agent.invocation.start and fell back to 33god-pm for unknown agent names, and nothing called it
    5ce34e9 fix(agent-pad): HOLOC-14 re-review - request deadlines cover the body (a stalled body could still stop polling or hold the queue), the end-of-reply watchdog follows the reply's own length (a long answer was cut at 3 min and replayed) and stops the player before retrying, upload/mic states win over REPLY in the hero, a held first reply plays as soon as sound unlocks, readable driving cue (white name, ringed swatch, full opacity); voice-memos hop text says 2 s
    4c921b7 fix(agent-pad): HOLOC-14 review - a motion-free driving cue (the replying tile fills with its colour, hero reads REPLY / REPLY · \<agent>) since .still stops animation while driving; the replying agent always has a driving tile; a replay after a note bounces again; list/download requests time out (10 s / 30 s) so a hung request cannot stop polling; a 3 min watchdog clears a reply whose end is never reported; a send switches to fast polling at once; room for the bounce in the parked scroller
    c08fba2 feat(agent-pad): HOLOC-14 - the replying agent's tile bounces while its answer plays, and replies are polled every 2 s for 10 min after a note goes out (was a flat 15 s, up to 13 s of dead air per round trip)

HERMES FLEET HEALTH
-------------------
**Status (authoritative): complete**

Hermes fleet: 34 agents registered; 1 timers (1 active, 0 failed); 9 cron jobs across 4 profiles (7 enabled); 5 job(s) reference a missing skill; 0 profile(s) with a stale ticker; 28 gateway unit(s) not running.
Metrics: agent_profile_dirs_missing=1, agents_registered=34, cron_jobs_enabled=7, cron_jobs_total=9, cron_jobs_unreadable=0, duplicate_cron_dirs=0, gateway_units_inactive=0, gateway_units_unknown=28, jobs_claiming_ok_contradicted=4, jobs_claiming_ok_unverified=2, jobs_with_missing_skill=5, jobs_with_past_next_run=0, profiles_scanned=38, profiles_unreadable_jobs=0, profiles_with_cron_jobs=4, profiles_with_stale_ticker=0, profiles_without_cron_dir=0, report_date=2026-10-20, sources_failed=0, sources_read=4, timers_active=1, timers_failed=0, timers_never_triggered=0, timers_total=1, timers_without_next_elapse=0, units_failed=0, units_not_found=1, units_total=6
Caveats:
  2 cron job(s) report last_status='ok' with no independent corroboration; last_status is a scheduler claim and is not treated as evidence of success
  4 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-10-20T11:43:11.516447Z (fleet state is current, not reconstructed for the report date)
  registry: 34 agents, 1 missing profile dir(s), 28 gateway unit(s) unknown to systemd, 0 not active
    agent 33god-pm: hermes-33god-pm-gateway.service unknown to systemd
    agent bloodbank-pm: hermes-bloodbank-pm-gateway.service unknown to systemd
    agent candystore-pm: hermes-candystore-pm-gateway.service unknown to systemd
    agent client-portal-pm: hermes-client-portal-pm-gateway.service unknown to systemd
    agent deckard-pm: hermes-deckard-pm-gateway.service unknown to systemd
    agent delonet-company-reporter: profile dir delonet-company-reporter absent
    agent delonet-director: hermes-delonet-director-gateway.service unknown to systemd
    agent dumply: hermes-dumply-gateway.service unknown to systemd
    agent flume-pm: hermes-flume-pm-gateway.service unknown to systemd
    agent green-in-between-pm: hermes-green-in-between-pm-gateway.service unknown to systemd
    agent gruvato-pm: hermes-gruvato-pm-gateway.service unknown to systemd
    agent heyma-pm: hermes-heyma-pm-gateway.service unknown to systemd
    agent holocene-pm: hermes-holocene-pm-gateway.service unknown to systemd
    agent idealscenario-pm: hermes-idealscenario-pm-gateway.service unknown to systemd
    agent infra-pm: hermes-infra-pm-gateway.service unknown to systemd
    agent james-brennan-pm: hermes-james-brennan-pm-gateway.service unknown to systemd
    agent keepy-money-pm: hermes-keepy-money-pm-gateway.service unknown to systemd
    agent monitoring-pm: hermes-monitoring-pm-gateway.service unknown to systemd
    agent nautilus-trader-pm: hermes-nautilus-trader-pm-gateway.service unknown to systemd
    agent navi-pm: hermes-navi-pm-gateway.service unknown to systemd
    agent pile-of-dumb-things-pm: hermes-pile-of-dumb-things-pm-gateway.service unknown to systemd
    agent pjangler-pm: hermes-pjangler-pm-gateway.service unknown to systemd
    agent sidepiece-pm: hermes-sidepiece-pm-gateway.service unknown to systemd
    agent skillex-pm: hermes-skillex-pm-gateway.service unknown to systemd
    agent slowburns-pm: hermes-slowburns-pm-gateway.service unknown to systemd
    agent ssbnk-pm: hermes-ssbnk-pm-gateway.service unknown to systemd
    agent tonnybox-pm: hermes-tonnybox-pm-gateway.service unknown to systemd
    agent voxxy-pm: hermes-voxxy-pm-gateway.service unknown to systemd
    agent zshyzsh-pm: hermes-zshyzsh-pm-gateway.service unknown to systemd
  systemd units: 6 matching, 0 failed, 1 not-found
    unit hermes-tonnybox-pm-consumer.service: not-found/inactive/dead
  timers: 1 matching, 1 active, 0 failed, 0 with no next elapse, 0 never triggered
  cron: 38 profiles scanned (0 without a cron dir), 4 with jobs, 9 jobs (7 enabled), 0 stale ticker(s), 0 shared cron dir(s)
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, contradicted), last run 2026-10-20T10:04:58.869077Z, next 2026-10-21T10:00:00Z; skill(s) not installed: delonet-daily-report
    job 33god-pm/Board Cranker implementation loop: disabled, schedule 'every 5m', last_status='ok' (claim, contradicted), last run 2026-09-05T12:48:43.347617Z, next none; skill(s) not installed: coding-strategy, pjangler
    job 33god-pm/HOLOC-12 delivery supervision: disabled, schedule 'every 10m', last_status='never run' (claim, not-claimed), last run never, next 2026-10-11T12:35:49.722250Z
    job 33god-pm/cronjob_manage: enabled, schedule '*/5 * * * *', last_status='error' (claim, not-claimed), last run 2026-10-20T11:40:05.850828Z, next 2026-10-20T11:45:00Z; last_error recorded (386 chars, not copied here)
    job 33god-pm/crank-watchdog: enabled, schedule 'every 15m', last_status='ok' (claim, unverified), last run 2026-10-20T11:41:05.677977Z, next 2026-10-20T11:56:05.677977Z
    job 33god-pm/cronjob_manage: enabled, schedule '*/10 * * * *', last_status='ok' (claim, unverified), last run 2026-10-20T11:40:08.049606Z, next 2026-10-20T11:50:00Z
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='ok' (claim, contradicted), last run 2026-10-19T13:02:36.789719Z, next 2026-10-20T13:00:00Z; skill(s) not installed: obsidian, llm-wiki
    job dumply/daily-story: enabled, schedule '30 20 * * *', last_status='ok' (claim, contradicted), last run 2026-10-20T00:32:12.173124Z, next 2026-10-21T00:30:00Z; skill(s) not installed: trivia-video
    job pile-of-dumb-things-pm/foundry-daily: enabled, schedule '0 16 * * *', last_status='never run' (claim, not-claimed), last run never, next 2026-10-20T20:00:00Z; skill(s) not installed: ltf-make-game

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 1 tick(s) across 1 of 1 tracked repositories on 2026-10-20; 0 PR(s) triaged, 0 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged; 1 tick(s) did not succeed.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=0, merge_candidates=0, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=0, prs_triaged=0, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=1, ticks_in_window=1, ticks_noop=0
Caveats:
  pr-crusher activity is read from its durable state, not Candystore: its Bloodbank publisher has been observed disabled, so absence of PR events on the bus does not mean absence of PR activity
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-10-20T04:00:00Z .. 2026-10-21T04:00:00Z for 2026-10-20 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 0
    tick 84 tick-000084-20261020T070025.734615Z completed=2026-10-20T07:00:28.492971Z provider=none provider_status=failed result_status=failed success=False automerge=False
      merge gate PR #None allowed=False attempted=False reasons: merge processing failed: credential broker rejected prc_github_write_token
      summary: runner/provider setup failed: credential broker rejected prc_github_read_token

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: DELIVERY FAILED -- 6 of 6 due day(s) in 2026-10-14..2026-10-20 have no valid published report (6 invalid); 6 day(s) carry a completion event with no archived report -- an earlier run reported success it did not achieve. 0 of 6 due days delivered over 2026-10-14..2026-10-20 (6 gap(s)); 6 completion event(s), 6 archive/event disagreement(s); delivered streak 0.
Metrics: archive_event_disagreements=6, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=0, days_archive_without_event=0, days_checked=7, days_delivered=0, days_event_without_archive=6, days_in_progress=1, days_invalid=6, days_missing=0, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=6, delivery_health=failed, events_found=6, lookback_days=7
Caveats:
  DELIVERY FAILED: 6 of 6 due day(s) in 2026-10-14..2026-10-20 have no valid published report (6 invalid)
  DELIVERY FAILED: 6 day(s) carry a completion event with no archived report -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-10-14 published-but-never-archived (event-without-archive): 1 completion event(s) claim status partial, but the archive says invalid -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-10-15 published-but-never-archived (event-without-archive): 1 completion event(s) claim status partial, but the archive says invalid -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-10-16 published-but-never-archived (event-without-archive): 1 completion event(s) claim status partial, but the archive says invalid -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-10-17 published-but-never-archived (event-without-archive): 1 completion event(s) claim status partial, but the archive says invalid -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-10-18 published-but-never-archived (event-without-archive): 1 completion event(s) claim status partial, but the archive says invalid -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-10-19 published-but-never-archived (event-without-archive): 1 completion event(s) claim status partial, but the archive says invalid -- an earlier run reported success it did not achieve
Detail:
  window 2026-10-14..2026-10-20 (7 days), report_date 2026-10-20
  delivery health failed: 6 of 6 due day(s) in 2026-10-14..2026-10-20 have no valid published report (6 invalid); 6 day(s) carry a completion event with no archived report -- an earlier run reported success it did not achieve
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.reporting.report.completed: reachable
  2026-10-14 invalid events=1 claimed=partial cross_check=published-but-never-archived generation=aed22a0a56ea405097d51d389e71f144 reason=report.json is invalid: DailyReport sections must be exactly ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery', 'turn-facts'], got ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery']; run-manifest.json is invalid: RunManifest must cover enabled sections exactly once in config order
  2026-10-15 invalid events=1 claimed=partial cross_check=published-but-never-archived generation=2ba00a81a09547a5b4036c5433d943aa reason=report.json is invalid: DailyReport sections must be exactly ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery', 'turn-facts'], got ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery']; run-manifest.json is invalid: RunManifest must cover enabled sections exactly once in config order
  2026-10-16 invalid events=1 claimed=partial cross_check=published-but-never-archived generation=7e660d3a0cda46a3abc686825f181523 reason=report.json is invalid: DailyReport sections must be exactly ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery', 'turn-facts'], got ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery']; run-manifest.json is invalid: RunManifest must cover enabled sections exactly once in config order
  2026-10-17 invalid events=1 claimed=partial cross_check=published-but-never-archived generation=3e464b063fac48c288e1b8223771a7dc reason=report.json is invalid: DailyReport sections must be exactly ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery', 'turn-facts'], got ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery']; run-manifest.json is invalid: RunManifest must cover enabled sections exactly once in config order
  2026-10-18 invalid events=1 claimed=partial cross_check=published-but-never-archived generation=78be3ed1a7984062bc6fa23ebe1c5d1c reason=report.json is invalid: DailyReport sections must be exactly ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery', 'turn-facts'], got ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery']; run-manifest.json is invalid: RunManifest must cover enabled sections exactly once in config order
  2026-10-19 invalid events=1 claimed=partial cross_check=published-but-never-archived generation=d6651cd73a1d4084a5b021ba161eaea4 reason=report.json is invalid: DailyReport sections must be exactly ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery', 'turn-facts'], got ['summary', 'dev-activity', 'fleet-health', 'pr-maintenance', 'report-delivery']; run-manifest.json is invalid: RunManifest must cover enabled sections exactly once in config order
  2026-10-20 in-progress events=0 reason=this run is producing this day; it publishes after collection
  DISAGREEMENT 2026-10-14 published-but-never-archived (event-without-archive): 1 completion event(s) claim status partial, but the archive says invalid -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-10-15 published-but-never-archived (event-without-archive): 1 completion event(s) claim status partial, but the archive says invalid -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-10-16 published-but-never-archived (event-without-archive): 1 completion event(s) claim status partial, but the archive says invalid -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-10-17 published-but-never-archived (event-without-archive): 1 completion event(s) claim status partial, but the archive says invalid -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-10-18 published-but-never-archived (event-without-archive): 1 completion event(s) claim status partial, but the archive says invalid -- an earlier run reported success it did not achieve
  DISAGREEMENT 2026-10-19 published-but-never-archived (event-without-archive): 1 completion event(s) claim status partial, but the archive says invalid -- an earlier run reported success it did not achieve

AGENT TURN FACTS
----------------
**Status (authoritative): complete**

On 2026-10-20 agents produced 21 annotated turn(s) across 6 project(s); busiest: 33god (7), unknown (7), holocene (3), and 3 more. 10 turn(s) reported a blocker.
Metrics: annotated_turns=21, avg_signal=0.914, candystore_reachable=True, candystore_url=http://127.0.0.1:8683, low_signal_turns=2, projects=6, turns_with_blockers=10
Caveats:
  2 annotated turn(s) on 2026-10-20 had data.signal below 0.5 or missing and were excluded from the metrics
Detail:
  33god: 7 turns, top actions: Implemented the turn-enricher service, turn_facts, turn reply
  bb: 2 turns, top actions: Implemented the turn-enricher service
  greeninbetween: 1 turns, top actions: The smoke test passed
  holocene: 3 turns, top actions: Found it, trace which agent owns it, Upload, pickup, dispatch
  infra: 1 turns, top actions: (none recorded)
  unknown: 7 turns, top actions: turn reply, sign out and sign in with `jaradd@gmail.com`, checked \**October 19
  unknown: BLOCKED - browser access
  33god: BLOCKED - TOWE-7 grooming
  unknown: BLOCKED - The AutomaticAI login currently lacks access to outbound-profile management
  unknown: BLOCKED - A cellular call won’t pass through Telnyx merely because Telnyx handles your incoming calls
  33god: BLOCKED - 33god
  unknown: BLOCKED - TOWE-7 grooming
  holocene: BLOCKED - GPU is full
  unknown: BLOCKED - The lid
  unknown: BLOCKED - I couldn't open the design artifact
  unknown: BLOCKED - Junk heap

COVERAGE
--------
4 of 5 enabled sections completed.
Degraded: dev-activity (partial).

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | partial | 2026-10-20T11:43:11.508359Z | 2026-10-21T11:43:11.508359Z | event pagination stopped at the 50-page budget (50000 events read); the day is not fully covered |
| fleet-health | complete | 2026-10-20T11:43:11.516447Z | 2026-10-21T11:43:11.516447Z | - |
| pr-maintenance | complete | 2026-10-20T11:43:11.599988Z | 2026-10-21T11:43:11.599988Z | - |
| report-delivery | complete | 2026-10-20T11:43:11.666547Z | 2026-10-21T11:43:11.666547Z | - |
| turn-facts | complete | 2026-10-20T11:43:11.687543Z | 2026-10-21T11:43:11.687543Z | - |
Required: dev-activity (partial), report-delivery (complete).
Overall status partial is derived from the run manifest above, not asserted.

Run ddr-2026-10-20-7844b27e · generated 2026-10-20T11:43:47.688578Z · overall status: partial
