Daily Developer Report — 2026-08-29
Summary written by anthropic/claude-opus-5. Everything below it is rendered by the pipeline from files it read — every status, metric and caveat is on this page whether or not a model answered.

SUMMARY
-------
**The day’s center of gravity was `james-brennan`: live-call operations, scheduling, invoicing, deployment, and operator visibility advanced rapidly, but 20 commits remain off `main`.**

## What happened

The strongest product movement was the end-to-end operating path in `james-brennan`. `JIMB-202` connected relay records and audio to the browser (`70821b4`, `60970ac`), corrected live-panel behavior (`d642fd9`), and fixed cancelled-record reporting (`ae4963f`). The Engine Room gained streaming dialogue (`bb8dc1f`), cross-room call visibility (`89df344`), and a proper idle state (`f871d14`). One related failure-path fix, `9a286a3` for `JIMB-204`, is not reachable from `main`.

Scheduling and case handling also moved materially. `JIMB-194` added viable-visit reporting (`3ecd0c4`), missing/conflicting-fact call scripts (`c316b04`), and multiple technician corrections for case binding, verdicts, conflicts, and one-line cues. `JIMB-196` preserved state required by the fence (`fd167f2`) and recorded evidence for `ACC-B3-001` (`2919a70`).

The commercial workflow advanced from review through invoice creation. `JIMB-181` made stopped Cases priceable and approvals actionable in place (`f0c5b8e`, `287c0a2`, `6656a33`, `a83a336`). `JIMB-186` added source-attributed invoice figures (`3ac5506`), invoice creation after approval (`e0dba67`), and fixes for composition and delivery paths (`52ec7b7`, `8309e96`). CI and deployment were tightened around expiring AWS identity and parity-based verification (`2a2c443`, `7fa34e0`, `59677f2`).

Across the platform, Bloodbank’s retired grammar was removed consistently. `bloodbank` exposed its naming contract through the CLI (`4ee7bea`) and fixed `bb-emit` to include and validate the actor (`19d90f8`). Matching sentinel and Hermes corrections landed across `33GOD`, `delonet-company`, `pjangler`, `candystore`, and `holocene`. `pjangler` also shipped `v1.4.3`, restored trusted publishing (`fa15945`), made project identity local by default (`e3aab0b`), and decommissioned the old ticket lifecycle under `PJAN-27`.

## Needs you

- Decide whether to recover or discard the 20 `james-brennan` commits not reachable from checked-out `main`; leaving them off-HEAD risks losing fixes including `JIMB-204` and the PostHog proxy.
- Restore the missing 2026-08-26 daily report. Delivery is degraded: 1 of 6 due days has no archive generation or completion event.
- Fix `delodocs-triage-second-pass`: it claims `ok` while required skills `obsidian` and `llm-wiki` are absent.
- Nightly PR maintenance produced no valid result for `delorenj/mcp-server-trello`; its sole tick failed schema validation, so no PR was triaged.
- Eight Hermes gateway units are not running, including five inactive and three unknown to systemd; `hermes-tonnybox-pm-consumer.service` is also not found.

## Worth noting

The pipeline read all nine configured repositories successfully and counted 158 commits after collapsing 17 replayed copies. Activity coverage remains incomplete for 15 event-active projects that have no configured Git root.

DEVELOPER ACTIVITY
------------------
**Status (authoritative): complete**

24286 events across 17 project(s) on 2026-08-29: 283 session(s), 11 decision(s), 45 committing session(s), 158 commit(s) across 9 of 9 configured repository(ies) read across all refs of each repository (155 on the checked-out branch, 20 only on other refs); peak 2026-08-29T16:00:00Z (4307 events).
Metrics: candystore_reachable=True, candystore_url=http://127.0.0.1:8683, commit_count=45, decision_count=11, event_count=24286, git_commit_count=158, git_commit_replays_collapsed=17, git_commits_off_head=20, git_commits_on_head=155, git_repos_failed=0, git_repos_logged=7, git_repos_missing=0, git_repos_no_commits=2, git_repos_with_off_head_commits=1, git_root_name_collisions=0, git_roots_active_in_events=2, git_roots_configured=9, git_roots_duplicated=0, git_roots_unread=0, git_roots_unusable=0, git_scope=all-refs, heatmap_read=True, peak_hour=2026-08-29T16:00:00Z, peak_hour_event_count=4307, project_count=17, projects_without_root=15, session_count=283
Caveats:
  projects truncated: showing 20 of 21
  committing sessions truncated: showing 30 of 45
  operational events truncated: showing 20 of 65
  git scope is 'all-refs': every ref of each configured repository was read for 2026-08-29 -- branches, tags and fetched remote-tracking refs, excluding refs/stash, refs/notes/* -- not only the checked-out branch; work that exists only in a clone this host has not fetched is out of reach
  2 configured project root(s) were read across all refs of each repository and had no commits on 2026-08-29: intelliforia, PoopToTheMoon
  20 of 175 commit(s) are not reachable from their repository's checked-out branch (unmerged or otherwise off-HEAD work) and are counted here: james-brennan 20 of 137 (checked out: main)
  17 commit(s) repeat the author date and subject of another commit in the same window (rebase or cherry-pick copies) and were counted once, not twice: james-brennan 17
  15 project(s) active in events have no configured project root, so no git log was read for them: .agents, DeLoContainers, automatic-ai, deliverables, hindsight, memories, mirror, n8n-nodes-bloodbank, and 7 more
Detail:
  === Events by CLI ===
    claude      23923
    unknown       201
    codex         159
    hermes          2
    reportctl       1
  
  === Events by project ===
    james-brennan         16829
    vinyl                  4251
    bloodbank              1218
    .agents                1020
    surface                 373
    unknown                 170
    hindsight                94
    relay                    87
    mirror                   77
    voice                    40
    project-fuckudeer        35
    wax                      34
    memories                 17
    deliverables             14
    james-brennan.git         9
    automatic-ai              8
    src                       4
    vinyl.git                 2
    n8n-nodes-bloodbank       2
    DeLoContainers.git        1
    ... showing 20 of 21 projects
  
  === Decisions recorded ===
    [unknown] (no issue): (no title)
    [unknown] (no issue): (no title)
    [vinyl] (no issue): (no title)
    [bloodbank] (no issue): (no title)
    [bloodbank] (no issue): expose the allowlist through bb contract
    [bloodbank] (no issue): (no title)
    [vinyl] (no issue): (no title)
    [unknown] (no issue): bb-emit now sets actor
    [vinyl] (no issue): (no title)
    [candybar] (no issue): (no title)
    [33god] (no issue): (no title)
  
  === Sessions that committed ===
    james-brennan (claude, 381 turns): 3 commit(s)
    james-brennan (claude, 88 turns): 1 commit(s)
    james-brennan (claude, 25 turns): 1 commit(s)
    james-brennan (claude, 45 turns): 1 commit(s)
    james-brennan (claude, 63 turns): 1 commit(s)
    james-brennan (claude, 19 turns): 1 commit(s)
    james-brennan (claude, 67 turns): 1 commit(s)
    james-brennan (claude, 81 turns): 1 commit(s)
    james-brennan (claude, 29 turns): 1 commit(s)
    james-brennan (claude, 200 turns): 3 commit(s)
    james-brennan (claude, 7 turns): 1 commit(s)
    james-brennan (claude, 7 turns): 1 commit(s)
    james-brennan (claude, 58 turns): 1 commit(s)
    james-brennan (claude, 58 turns): 2 commit(s)
    james-brennan (claude, 47 turns): 2 commit(s)
    james-brennan (claude, 35 turns): 1 commit(s)
    james-brennan (claude, 124 turns): 4 commit(s)
    james-brennan (claude, 110 turns): 1 commit(s)
    james-brennan (claude, 21 turns): 1 commit(s)
    vinyl (codex, 19 turns): 1 commit(s)
    james-brennan (claude, 347 turns): 5 commit(s)
    hindsight (claude, 325 turns): 1 commit(s)
    james-brennan (claude, 31 turns): 1 commit(s)
    james-brennan (claude, 141 turns): 1 commit(s)
    james-brennan (claude, 123 turns): 1 commit(s)
    james-brennan (claude, 545 turns): 1 commit(s)
    james-brennan (claude, 345 turns): 1 commit(s)
    james-brennan (claude, 54 turns): 1 commit(s)
    james-brennan (claude, 434 turns): 10 commit(s)
    james-brennan (claude, 109 turns): 1 commit(s)
    ... showing 30 of 45 committing sessions
  
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
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [wax] updated: (no detail)
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    [unknown] exited: restarted container after HTTP 502 on https://get.delo.sh/
    ... showing 20 of 65 operational events
  
  === Git log by repository ===
  === 33GOD ===
    3516fa1 chore(bloodbank): bump gitlink for the contract discoverability CLI
    61b67b1 docs(bloodbank): retire the versioned subject from the docs agents treat as authority
    6e167d2 chore(bloodbank): bump gitlink for the bb-emit actor fix
    649c735 chore(hermes-agent-template): pin the SOUL deleted-family cleanup
    476c0f3 chore(pjangler): advance the pinned pointer onto the grammar-migration fixes
    9c1dfd5 fix(soul): stop instructing the PM to publish a deleted command family
    fa7a8a7 chore(bloodbank): advance the gitlink onto the forward_envelope comment fix
    63db22d fix(hermes): teach this agent the live Bloodbank grammar, not the retired one
    70ce392 chore(pjangler): advance the gitlink onto the landed init-board and skills work
    13509b1 fix(sentinel): retire the repo.issue.* close-gate emission
    e0e7f51 chore(momo): advance the gitlink onto the landed skill correction
    978f98c fix(drift): make the bloodbank-routing guard guard something again
  
  === james-brennan ===
    (checked out: main; 20 of 137 commit(s) below are not reachable from it)
    dd81818 chore(repo): untrack .lastagent, which .gitignore never could
    15667f3 chore(repo): the root stops being a folder of loose documents
    e465409 chore(devops): taskdefs at 2030332
    2030332 chore(voice,devops): the workstation serves nothing of Jim's
    11c6f89 docs(devops): the runbook said CI runs green, and the relay half never had
    6ea7dbe chore(devops): taskdefs at d6b0935
    d6b0935 fix(devops): the deploy role could not pass the role the relay taskdef names
    53bb18a chore(devops): taskdefs at bb8dc1f
    bb8dc1f feat(surface,relay): the Engine Room streams the dialogue as it is spoken
    89df344 feat(surface): a live call is now visible from every room, not only the one showing it
    f871d14 feat(surface): the Engine Room had no idle state, so the log became the page
    22aecac fix(surface): the copy explained itself instead of naming things
    6df4166 chore(devops): taskdefs at dca8ec6
    dca8ec6 fix(voice,relay): four tool returns handed back a sentence with no instruction to say it
    9a286a3 fix(surface,JIMB-204): the Engine Room's live channel failed silently, so no one could tell why  [not reachable from main]
    f37b36f chore(devops): taskdefs at ae4963f
    ae4963f fix(surface,JIMB-202): a cancelled record read reported itself as an outage
    b68def5 chore(devops): taskdefs at d642fd9
    d642fd9 feat(surface,JIMB-202): the live panel never cleared for a call we placed, and the room around it was mostly other modes' numbers
    60970ac feat(surface,JIMB-202): three proxies so the record and its audio reach a browser the relay cannot see
    70821b4 feat(relay,JIMB-202): the recording reference had no way to become audio, and the record had no route
    c8f4c41 chore(devops): taskdefs at 96df0f1
    546447b docs: the fixture rule caught its own author within the hour of writing it
    96df0f1 feat(voice,JIMB-203): /healthz reported a key it could not spend as an ability to speak
    8817a9e docs: one of the four was the same mistake inverted, not a fourth of the same
    72e1c05 fix(devops,JIMB-202): the voice container fanned every live frame into its own empty subscriber set
    f6980b3 chore(devops): taskdefs at 3ecd0c4
    390cd8a docs: the three ways a green suite lied today, written down as rules
    3ecd0c4 feat(relay,JIMB-194): relay:schedule says which viable visits already have a Case
    c47814d fix(surface,JIMB-200): the developer line was domain-shaped, and two of the five seats are at Jim's domain
    4f84a0c fix(technician,JIMB-194): the conflict was parked on a turn the line never gives
    54505c5 fix(technician,JIMB-194): the line declining correctly was scored as our own crash
    48fe7e2 feat(surface,JIMB-200): a developer session was materially different and nothing on screen said so
    402509e docs(voice,JIMB-199): the header still said "no retries", and the diagnosis had nowhere to live
    7e5b8d5 chore(devops): taskdefs at 7745aa8
    7745aa8 checkpoint: update .lastagent,AGENTS.md,Masthead.tsx, +5 more (8 files changed, 453 insertions(+), 143 deletions(-))
    4e2eca7 fix(technician,JIMB-194): two cues answered from one line that could only be said once
    f47c722 checkpoint: 2026-08-29T17:05:09Z auto-commit
    888e454 fix(technician,JIMB-194): every manifest still said a call can move exactly one row
    135f632 fix(technician,JIMB-194): the first real run bound a stranger's Case and graded itself against it
    2a8cb36 docs(devops): a skill for the instrument that places the call
    28bd67c Merge remote-tracking branch 'origin/main'
    1a7076f fix(relay,JIMB-194): W1-2 and W1-3 returned a fixed verdict without ever looking
    3ebb723 chore(devops): taskdefs at 305ccda
    305ccda fix(relay,sweep): a package states its reason once and nothing ever asks again
    93f8a44 merge: taskdefs at 84d1af9 alongside the JIMB-194 call scripts
    c316b04 feat(technician,JIMB-194): scripts for the missing-fact and conflicting-fact calls
    4fc2db7 chore(devops): taskdefs at 84d1af9
    84d1af9 docs(relay): the publisher still called it the Meter Room
    d9f91ae refactor(surface,boiler-room): mode 4 is the Boiler Room, and the smoke test knows it
    a778c78 fix(technician,JIMB-194): the collector listed a dict, so no run ever read a Case back
    2919a70 evidence(relay,JIMB-196): ACC-B3-001 is EVIDENCED — the after, against b692ef5
    4dc648c chore(devops): taskdefs at b692ef5
    6f77677 chore(devops): taskdefs at fd167f2
    b692ef5 feat(relay,JIMB-194): the schedule said "7 the line will accept" and four of them hold
    fd167f2 fix(relay,JIMB-196): the stored job payload dropped the state the fence reads
    f3cd040 chore(devops): taskdefs at 5b37521
    5b37521 fix(devops,JIMB-195): a wrong-account run was reported as a Twilio failure
    0763d45 fix(mirror): a stub carried a mutable class attribute nothing read
    b71e2f6 docs: Jarad's restructure of AGENTS.md — apps first, and the TODOs named
    161ea24 checkpoint: 2026-08-29T15:01:09Z auto-commit
    adcb997 docs: three tenets the boards defect taught, in the section about belief
    3938184 fix(relay,devops): the operator control shipped without the boards it reads
    0a68e24 chore(devops): taskdefs at e7440b1
    c796bfd feat(surface): serve PostHog capture from a first-party proxy  [not reachable from main]
    e7440b1 chore(devops): taskdefs at 9712be2
    9712be2 fix(relay,surface): the publisher answered "can we write" by looking at the one container that may not
    8c75439 refactor(surface): the loose end three parallel redesigns left, and a count that outlived its room
    c6e0175 chore(devops): taskdefs at 9999e23
    9999e23 refactor(surface,engine-room): a showroom got filed under modes, and it cost 34 constants
    2618e17 chore(devops): taskdefs at bf4479b
    bf4479b feat(surface,relay): the dev control loads a day of Miami Beach work, and it is absent on Jim's account
    89cf1c9 refactor(surface,cockpit): the margin was four blocks, two of which the plate already draws
    ccaa69c chore(devops): taskdefs at ef093b1
    ef093b1 docs(devops): the deploy script rested its safety on a registry guarantee it does not have
    dbfe59b chore(devops): taskdefs at 34b4f94
    34b4f94 chore(devops): taskdefs at 09ff93c
    46cfbaa docs(devops): the runbook said there is no CI, from inside the repo that has it
    09ff93c test(relay,JIMB-190): the publisher and the Meter Room diverged in an hour, and nothing noticed
    da47048 chore(devops): taskdefs at 59677f2
    fa54820 feat(surface,meter-room): the fourth mode, and a cost is data rather than a task
    59677f2 ci(devops): "I could not see it" and "it is fine" were the same answer
    c9b2b51 chore(devops): taskdefs at 7fa34e0
    7fa34e0 ci(devops): the deploy moves off the laptop, and parity is what says it landed
    16fbdc7 chore(devops): taskdefs at 33af594
    b9281e3 feat(relay,JIMB-190): costs:v1 — every vendor, its payer, and the ones that will not answer
    33af594 docs(devops): the deploy runbook, with parity as the definition of deployed
    089dc41 fix(surface,JIMB-187): the rows denied a capability that had shipped hours earlier
    2a2c443 feat(devops): CI gets an AWS identity that expires, scoped to the deploy it performs
    91844a7 feat(relay,JIMB-187): the controls that unstick, and three of the four already existed
    a7b7eda feat(relay,JIMB-187): the publisher counted a fortnight-old outage as live work
    b8e25c2 feat(surface,JIMB-187): the margin counted 48 stuck calls and offered no way to reach one
    8b003aa fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as e7ce4f5, counted once]
    e7ce4f5 fix(hermes): teach this agent the live Bloodbank grammar, not the retired one
    2f33e61 fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main]
    652c856 fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    7174905 fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    7d19152 fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    9e0efe4 fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    b5e37a9 fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    492b068 fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    76262b2 fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    e291def fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    5e1b14d fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    aec334c fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    60c1788 fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    fa7ae0b fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    ca487e2 fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    08eae3d fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    9a707c4 fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    a2deced fix(hermes): teach this agent the live Bloodbank grammar, not the retired one  [not reachable from main; same author date and subject as 2f33e61, counted once]
    600f9ca chore(devops): the taskdefs named e44ee4f while the service ran f0c5b8e
    0a00a19 docs(relay,JIMB-186): the adversarial pass on the write-scope split, and the one hole it found
    439b5a9 chore: land the in-flight tree — taskdefs, the fence tests, and pilot
    f0c5b8e feat(relay,JIMB-181): the card could not price the 44 Cases that are stopped on a price
    6da3798 docs(relay,JIMB-186): the write-scope split, whose code landed inside 4fc178a
    8932dd4 docs(sentinel): land the prose half of the repo.issue.* retirement
    4fc178a refactor(sentinel): retire the repo.issue.* emissions; keep the gate, retarget its test
    a83a336 feat(surface,JIMB-181): the card approves in place, and the note is the thing he approves
    6656a33 feat(surface,JIMB-181): the card could not name the Case whose note it was about to file
    287c0a2 feat(surface,JIMB-181): the card can read the note, and approve can no longer hand back the key to its own gate
    2a2dc33 docs(agents): the private backend is the write path, and only one of the two fences is permanent
    e44ee4f fix(devops): the container that answers the phone could not price the call it took
    d645483 fix(relay): testbed mail moves to delo.sh, where a catch-all means every address just works
    8309e96 fix(relay,JIMB-186): a composed invoice nothing can post reached nobody at all
    52ec7b7 fix(relay,JIMB-186): nothing composed the invoice on any path a real call takes
    17f5ddf docs(agents): the example address was the one that would have bounced
    05be09f fix(relay): the testbed inbox is founders@, and the default it replaced would have bounced
    e0dba67 feat(relay,JIMB-186): the approved invoice is raised after the note lands, and ACC-B2-W1-1 closes
    3c6b4b4 feat(relay): a price a named human sets at review, when nobody said one
    3ac5506 feat(relay,JIMB-186): every figure on the invoice names where it came from, and the stored one is what gets written
    a088871 feat(relay,JIMB-186): the invoice capability is on, and two stale refusals stop lying about it
    c2e9932 docs(agents): the no-contact-details line contradicted the section above it
    04e50ca feat(relay): testbed customers get a plus-addressed inbox, so a send can be watched
    b3508ce docs(agents): the things that are true every turn, filed under the question they answer
    1499296 docs(agents): the fence exists so testing can be reckless, and that has to be read first
    1bdda81 fix(relay): a ring-back about a job already reported crashed the call it exists to serve
  
  === intelliforia ===
  (no commits)
  
  === delonet-company ===
    b468d2f fix(director): drop the deleted contract-declaration event, land the scaffold fix
    32cbb72 fix(hermes): teach this agent the live Bloodbank grammar, not the retired one
    04b1d8d fix(sentinel): retire the repo.issue.* close-gate emission
  
  === PoopToTheMoon ===
  (no commits)
  
  === pjangler ===
    fa15945 ci: restore the workflow filename npm's trusted publisher is pinned to
    f7848da chore(release): v1.4.3 [skip ci]
    3dcefea test(project-identity): pass the fleet registry in instead of reading $HOME
    a1c6f04 test(pjan-86): own the Git repo the hermes fixtures are inspected in
    655b3e0 test(project-registry): give agent provisioning a hermetic PJángler CLI
    14a437e ci: guard the publish loop on the actor, not only the commit message
    8af11bf ci: test with coverage behind a ratchet, and publish every green main
    e3aab0b fix(cli): `pj project identity` with no argument means this project
    e1d1387 chore(templates): bump hermes-agent to the SOUL deleted-family cleanup
    b5b8a84 fix(PJAN-27): finish the ticket-lifecycle decommission in CommonProject
    0a5ad18 fix(skills): re-project the two vendored skillex skills instead of patching them
    9273c8f fix(init): make the board the ingress's job, not an opt-in it never mentioned
    74978fd fix(PJAN-27): decommission pjangler's ticket-lifecycle workflow
    acb25ed fix(sentinel): retire the repo.issue.* close-gate emission
  
  === bloodbank ===
    4ee7bea feat(cli): publish the naming contract instead of only enforcing it
    19d90f8 fix(bb-emit): emit an actor, and check the envelope before publishing it
    b062f4e docs(registry): record the full shipped state through the ingress fix
    6a230f7 docs(agent-hooks): drop the survived first line that still promised vN tolerance
    d107e6e refactor(agent-hooks): publish deckard attention on the de-versioned subject
    235ad5b fix(sentinel): retire the repo.issue.* close-gate emission
  
  === candystore ===
    359d26c fix(env): point the example subscribe topic at the wildcard that actually matches
    716dffc fix(sentinel): retire the repo.issue.* close-gate emission
  
  === holocene ===
    fc461aa fix(sentinel): retire the repo.issue.* close-gate emission

HERMES FLEET HEALTH
-------------------
**Status (authoritative): complete**

Hermes fleet: 28 agents registered; 15 timers (15 active, 0 failed); 3 cron jobs across 3 profiles (3 enabled); 1 job(s) reference a missing skill; 0 profile(s) with a stale ticker; 8 gateway unit(s) not running.
Metrics: agent_profile_dirs_missing=0, agents_registered=28, cron_jobs_enabled=3, cron_jobs_total=3, cron_jobs_unreadable=0, duplicate_cron_dirs=1, gateway_units_inactive=5, gateway_units_unknown=3, jobs_claiming_ok_contradicted=1, jobs_claiming_ok_unverified=2, jobs_with_missing_skill=1, jobs_with_past_next_run=0, profiles_scanned=39, profiles_unreadable_jobs=0, profiles_with_cron_jobs=3, profiles_with_stale_ticker=0, profiles_without_cron_dir=0, report_date=2026-08-29, sources_failed=0, sources_read=4, timers_active=15, timers_failed=0, timers_never_triggered=0, timers_total=15, timers_without_next_elapse=0, units_failed=0, units_not_found=1, units_total=59
Caveats:
  2 cron job(s) report last_status='ok' with no independent corroboration; last_status is a scheduler claim and is not treated as evidence of success
  1 cron job(s) report last_status='ok' while an observable fact contradicts it
Detail:
  observed at 2026-08-30T10:00:32.260195Z (fleet state is current, not reconstructed for the report date)
  registry: 28 agents, 0 missing profile dir(s), 3 gateway unit(s) unknown to systemd, 5 not active
    agent condaleeza: hermes-condaleeza-gateway.service not active
    agent delocontainers-pm: hermes-delocontainers-pm-gateway.service not active
    agent delonet-director: hermes-delonet-director-gateway.service unknown to systemd; hermes-delonet-director-heartbeat.timer unknown to systemd
    agent drumjangler-pm: hermes-drumjangler-pm-gateway.service not active
    agent hermes-agent-pm: hermes-hermes-agent-pm-gateway.service unknown to systemd
    agent intelliforia-voice-agent-pm: hermes-intelliforia-voice-agent-pm-gateway.service not active
    agent nautilus-trader-pm: hermes-nautilus-trader-pm-gateway.service not active
    agent ssbnk-pm: hermes-ssbnk-pm-gateway.service unknown to systemd
  systemd units: 59 matching, 0 failed, 1 not-found
    unit hermes-tonnybox-pm-consumer.service: not-found/inactive/dead
  timers: 15 matching, 15 active, 0 failed, 0 with no next elapse, 0 never triggered
  cron: 39 profiles scanned (0 without a cron dir), 3 with jobs, 3 jobs (3 enabled), 0 stale ticker(s), 1 shared cron dir(s)
    profile 33god-pm.bak: shares its cron dir with 33god-pm
    job 33god-pm/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-08-29T10:02:21.034199Z, next 2026-08-31T10:00:00Z
    job 33god-pm.bak/delonet-daily-report: enabled, schedule '0 6 * * *', last_status='ok' (claim, unverified), last run 2026-08-29T10:02:21.034199Z, next 2026-08-31T10:00:00Z
    job delodocs-pm/delodocs-triage-second-pass: enabled, schedule '0 9 * * *', last_status='ok' (claim, contradicted), last run 2026-08-29T13:01:35.276600Z, next 2026-08-30T13:00:00Z; skill(s) not installed: obsidian, llm-wiki

NIGHTLY PR MAINTENANCE
----------------------
**Status (authoritative): complete**

pr maintenance: 1 tick(s) across 1 of 1 tracked repositories on 2026-08-29; 0 PR(s) triaged, 0 merge candidate(s); 0 merge(s) attempted, 0 confirmed merged; 1 tick(s) did not succeed.
Metrics: bloodbank_events_published=2, bloodbank_events_skipped=0, merge_candidates=0, merges_attempted=0, merges_completed=0, merges_unconfirmed=0, noop_streak=0, prs_triaged=0, repos_tracked=1, repos_with_ticks=1, state_files_unusable=0, ticks_failed=1, ticks_in_window=1, ticks_noop=0
Caveats:
  pr-crusher activity is read from its durable state, not Candystore: its Bloodbank publisher has been observed disabled, so absence of PR events on the bus does not mean absence of PR activity
  2 pr-crusher lifecycle event(s) did reach Bloodbank
Detail:
  window: 2026-08-29T04:00:00Z .. 2026-08-30T04:00:00Z for 2026-08-29 (America/New_York)
  state directory: /home/delorenj/.local/state/pr-crusher
  === delorenj/mcp-server-trello (git-github.com-delorenj-mcp-server-trello.git-7bef4efbe7ba8cc5) ===
    noop streak at the end of the window: 0
    tick 33 tick-000033-20260829T070010.905746Z completed=2026-08-29T07:02:35.556728Z provider=opencode_free provider_status=failed result_status=failed success=False automerge=False
      summary: provider did not produce a schema-valid tick result

DAILY REPORT AND DELIVERY HEALTH
--------------------------------
**Status (authoritative): complete**

report-delivery: DELIVERY DEGRADED -- 1 of 6 due day(s) in 2026-08-23..2026-08-29 have no valid published report (1 missing). 5 of 6 due days delivered over 2026-08-23..2026-08-29 (1 gap(s)); 5 completion event(s), 0 archive/event disagreement(s); delivered streak 2.
Metrics: archive_event_disagreements=0, archive_readable=True, candystore_reachable=True, consecutive_delivered_streak=2, days_archive_without_event=0, days_checked=7, days_delivered=5, days_event_without_archive=0, days_in_progress=1, days_invalid=0, days_missing=1, days_unpublished_but_archived=0, days_unreadable=0, delivery_gaps=1, delivery_health=degraded, events_found=5, lookback_days=7
Caveats:
  DELIVERY DEGRADED: 1 of 6 due day(s) in 2026-08-23..2026-08-29 have no valid published report (1 missing)
Detail:
  window 2026-08-23..2026-08-29 (7 days), report_date 2026-08-29
  delivery health degraded: 1 of 6 due day(s) in 2026-08-23..2026-08-29 have no valid published report (1 missing)
  archive /home/delorenj/.local/state/delonet-daily-report/archive: readable
  candystore http://127.0.0.1:8683 type=bloodbank.reporting.report.completed: reachable
  2026-08-23 delivered events=1 claimed=complete generation=0c3230c650d84d3f8d28308949df22d8
  2026-08-24 delivered events=1 claimed=complete generation=98b545accde943d0809aa4a9b0cda913
  2026-08-25 delivered events=1 claimed=complete generation=0c92b6f7abf8482188b536c9cc5eedf8
  2026-08-26 missing events=0 reason=no current.json and no staged generation under /home/delorenj/.local/state/delonet-daily-report/archive/2026/08/2026-08-26
  2026-08-27 delivered events=1 claimed=complete generation=1472ef2e152c42aa94012cce38fb34ba
  2026-08-28 delivered events=1 claimed=complete generation=001568c972584cae9965b922dcef9126
  2026-08-29 in-progress events=0 reason=this run is producing this day; it publishes after collection

COVERAGE
--------
4 of 4 enabled sections completed.
No section is degraded.

| section | status | generated | fresh until | reason |
|---|---|---|---|---|
| dev-activity | complete | 2026-08-30T10:00:32.253800Z | 2026-08-31T10:00:32.253800Z | - |
| fleet-health | complete | 2026-08-30T10:00:32.260195Z | 2026-08-31T10:00:32.260195Z | - |
| pr-maintenance | complete | 2026-08-30T10:00:32.307568Z | 2026-08-31T10:00:32.307568Z | - |
| report-delivery | complete | 2026-08-30T10:00:32.327259Z | 2026-08-31T10:00:32.327259Z | - |
Required: dev-activity (complete), report-delivery (complete).
Overall status complete is derived from the run manifest above, not asserted.

Run ddr-2026-08-29-97531665 · generated 2026-08-30T10:01:09.712145Z · overall status: complete
