# DeLoNET Daily Report — adversarial verification findings

Run wf_52b86706-f6b, 3 lenses, 29 properties found BROKEN.

- **false-green** — broken (7 hold / 11 broken)
- **atomicity** — broken (8 hold / 8 broken)
- **contracts-and-reality** — broken (9 hold / 10 broken)

---

## 1. [CRITICAL] The narrator cannot change a status (report.md header literally asserts this)

**Evidence:** A narrator that emits its own '**Status (authoritative): complete**' line gets it published verbatim. compose_report() (scripts/run.py:337-341) prepends the real status line ONLY for items with kind=='section'; the four core sections (executive-brief, key-changes, risks-watchlist) get NO deterministic status line at all, so the model's fake line is the only status line in them. parse_output() (scripts/narrate.py) only length-clips bodies -- there is no structural sanitation of narrated text. Published report with dev-activity actually FAILED:

  EXECUTIVE BRIEF
  **Status (authoritative): complete**
  Everything is healthy. All four sections completed and every daily report was delivered on time.
  | section | status | ... |
  | executive-brief | complete | now | later | - |

and in the collector section the two lines sit adjacent, fake last:
  DEVELOPER ACTIVITY
  **Status (authoritative): failed** -- Candystore event history unavailable...
  **Status (authoritative): complete**
  Everything is healthy...

This is not hypothetical injection-wise: the prompt payload carries raw third-party commit subjects from every watched repo (verified in /tmp/ddr-adv/last-prompt.txt: '2792ac1 chore(fleet): pin momo scaffold...', 'be2310bd feat(portal): dialog and multi-select behaviour...'), i.e. text this pipeline did not write and any agent with commit access controls. dev_activity.py's docstring acknowledges the injection risk and mitigates the model's TOOLS (-t todo) but not its OUTPUT. Machine surfaces (manifest, event, coverage table) stayed honest; the human-facing document did not.

**Repro:**
```
cat > /tmp/evil.py  # narrator that returns bodies beginning with '**Status (authoritative): complete**'
CANDYSTORE_URL=http://127.0.0.1:9 DDR_NARRATOR_CMD=/tmp/evil.py DDR_MIRROR_DIR=/tmp/m \
  ./scripts/reportctl --config /tmp/ddr-adv/config-x.json run --date 2026-08-17 --no-emit
# EXIT=0, manifest dev-activity=failed, published report.md leads with 'Everything is healthy.'
sed -n '1,50p' /tmp/ddr-adv/x-art/2026-08-17/report.md
```

## 2. [CRITICAL] dev_activity reports status=complete only when every configured source was read in full (its own docstring: "complete means every source named here was read in full")

**Evidence:** resolve_project_dirs() (scripts/collectors/dev_activity.py:406-435) enumerates git repos from the day's Candystore event `project` names, then intersects with config project_roots. A configured root whose project name does not appear in that day's events is dropped with NO caveat and NO metric. Only the inverse (events-without-root) is reported. Proven on real data for 2026-08-15: `python3 -m collectors.dev_activity --date 2026-08-15 --config ../assets/example-config.v2.json` returned status=complete, summary "8839 events ... 14 commit(s) in 4 repository(ies)", metrics git_repos_logged=4, git_repos_missing=0, git_repos_failed=0, and caveats naming ONLY the 19 events-without-root. Repos actually logged: PoopToTheMoon, intelliforia, james-brennan, pjangler. Independent git count for the same window shows five OTHER configured roots held 25 more commits that day: 33GOD 6, delonet-company 9, bloodbank 8, candystore 1, holocene 1. The report therefore understates the day by 25 of 39 commits (64%) and says nothing about it, while claiming `complete`. Same function also silently discards a second configured root sharing a basename (roots.setdefault(path.name, path)): resolve_project_dirs([{'project':'candystore'}], ['/home/delorenj/code/33GOD/candystore','/home/delorenj/code/other/candystore']) returns one selected root, unconfigured=[], fell_back=False — no record of the drop. This is precisely the defect class the package exists to prevent: a section that says complete while silently omitting configured sources.

**Repro:**
```
cd /home/delorenj/code/skillex/all-skills/delonet-daily-report/scripts && python3 -m collectors.dev_activity --date 2026-08-15 --config ../assets/example-config.v2.json | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['status'],d['metrics']['git_repos_logged'],d['caveats'])"  # then: for d in /home/delorenj/code/33GOD /home/delorenj/code/delonet-company /home/delorenj/code/33GOD/bloodbank /home/delorenj/code/33GOD/candystore /home/delorenj/code/33GOD/holocene; do echo "$d $(git -C $d log --since=2026-08-15T00:00:00Z --until=2026-08-16T00:00:00Z --oneline | wc -l)"; done
```

## 3. [CRITICAL] S5 cutover is done: ~/.hermes/skills/delonet-daily-report symlink exists, one cron job at 06:00 runs the merged pipeline, the old candystore-daily-journal job is removed

**Evidence:** None of it has happened. `ls -la ~/.hermes/skills/ | grep -i daily` shows only `candystore-daily-journal -> /home/delorenj/code/skillex/all-skills/candystore-daily-journal`; there is no delonet-daily-report entry. The old job is still live and armed: ~/.hermes/profiles/33god-pm/cron/jobs.json job id 8da3f24263f9, name candystore-daily-journal, skill "candystore-daily-journal", enabled true, schedule "0 6 * * *", next_run_at "2026-08-19T06:00:00-04:00", last_status "ok", last_error null. It is duplicated through the shared cron dir in 33god-pm.bak (the pipeline's own fleet_health flags this: duplicate_cron_dirs=1). The retiring skill dir /home/delorenj/code/skillex/all-skills/candystore-daily-journal still exists in full. Net effect: in ~8 hours the exact 2026-08-18 failure fires again, and the scheduler will again record last_status=ok over it, while the working merged pipeline has no scheduled trigger at all.

**Repro:**
```
ls -la ~/.hermes/skills/ | grep -i daily; python3 -c "import json;print([{k:j[k] for k in ('name','skill','enabled','schedule_display','next_run_at','last_status')} for j in json.load(open('/home/delorenj/.hermes/profiles/33god-pm/cron/jobs.json'))['jobs']])"
```

## 4. [HIGH] A cron agent cannot record success over a run in which a REQUIRED section died

**Evidence:** The plan's own failure-injection block (peaceful-splashing-lagoon.md lines 164-166) says: 'CANDYSTORE_URL=http://127.0.0.1:9 ... run --date 2026-08-17  #   expect: dev-activity status=failed, overall=partial, non-zero exit'. The implementation exits 0. run.py:730 sets exit_code = EXIT_UNMET only when outcome['status']=='failed'; partial returns EXIT_OK, and SKILL.md documents that choice ('complete and partial both exit 0'). So the exact scenario the plan named as the acceptance test for the anti-false-green property returns 0 with the REQUIRED dev-activity section dead. It compounds at the gate: `verify` (which SKILL.md calls 'this is the gate' in the setup steps, without --require-complete) prints "ok": true and exits 0 on that same published report. Only `verify --require-complete` exits 3. Real output:

  $ CANDYSTORE_URL=http://127.0.0.1:9 ... run --date 2026-08-17 --no-emit --no-narrate ; echo $?
  EXIT=0
  status partial | section_status partial
  manifest {'dev-activity': 'failed', 'fleet-health': 'complete', 'pr-maintenance': 'complete', 'report-delivery': 'partial'}

  $ ./scripts/reportctl --config ... verify --date 2026-08-17 ; echo $?
  "ok": true, "degraded": ["dev-activity","report-delivery"], "status": "partial"
  EXIT=0
  $ ./scripts/reportctl --config ... verify --date 2026-08-17 --require-complete ; echo $?
  EXIT=3

**Repro:**
```
cd /home/delorenj/code/skillex/all-skills/delonet-daily-report
DDR_MIRROR_DIR=/tmp/m CANDYSTORE_URL=http://127.0.0.1:9 ./scripts/reportctl --config /tmp/ddr-adv/config.json run --date 2026-08-17 --no-emit --no-narrate; echo EXIT=$?
./scripts/reportctl --config /tmp/ddr-adv/config.json verify --date 2026-08-17 >/dev/null; echo EXIT=$?
```

## 5. [HIGH] The report-delivery self-check catches the failure mode of 2026-08-18 ('this is the section that would have caught this morning')

**Evidence:** It DETECTS it perfectly and then throws the detection away. Against an empty archive with the real Candystore up, report_delivery produced status='complete' with these caveats verbatim:

  - archive root /tmp/ddr-adv/g-arc does not exist; no report has ever been published there
  - duplicate completion events for 2026-08-16, 2026-08-17; more than one run claimed the same day
  - DISAGREEMENT 2026-08-16 event-without-archive: 2 completion event(s) claim status complete, but the archive says missing -- an earlier run reported success it did not achieve
  - DISAGREEMENT 2026-08-17 event-without-archive: 3 completion event(s) claim status complete, but the archive says this run has not published it yet -- an earlier run reported success it did not achieve

summary: 'report-delivery: 0 of 6 due days delivered over 2026-08-11..2026-08-17 (6 gap(s)); 5 completion event(s), 2 archive/event disagreement(s); delivered streak 0.'

Status derivation in collectors/report_delivery.py:456-464 is a pure function of archive_ok and events_ok only -- gaps and disagreements never touch it (documented at lines 33-36: 'Section status is collection health, never delivery health'). fleet_health behaves identically: metrics jobs_claiming_ok_contradicted=1, jobs_with_missing_skill=1, gateway_units_inactive=2, section status='complete'. End-to-end result with a cooperative narrator:

  status complete | manifest all complete
  EVENT bloodbank.v1.reporting.report.completed {"status": "complete", "sections": {...all complete}}
  verify --require-complete EXIT=0

So: 6 missing daily reports, 5 phantom completion events, and a contradicted cron 'ok' claim, all reported to every machine consumer as complete.

**Repro:**
```
rm -rf /tmp/ddr-adv/g-art /tmp/ddr-adv/g-arc
FAKE_NARR=ok DDR_NARRATOR_CMD=/tmp/ddr-adv/fake-narrator.py DDR_MIRROR_DIR=/tmp/mg \
  ./scripts/reportctl --config /tmp/ddr-adv/config-g.json run --date 2026-08-17 --no-emit
./scripts/reportctl --config /tmp/ddr-adv/config-g.json verify --date 2026-08-17 --require-complete; echo EXIT=$?
python3 -c "import json;a=json.load(open('/tmp/ddr-adv/g-art/2026-08-17/sections/report-delivery.json'));print(a['status']);print(a['caveats'])"
```

## 6. [HIGH] Everything a collector recorded as a caveat survives into the published report

**Evidence:** Only on the deterministic path. fallback_bodies() renders 'Caveats:' blocks and lists every caveat under RISKS AND WATCHLIST; the narrated path replaces every section body with the model's prose and re-states nothing but the status line. Grep of the published, narrated report.md from the run above:

  $ grep -c 'DISAGREEMENT\|reported success it did not achieve\|gap' g-art/2026-08-17/report.md
  0

The caveats DO reach the model (2 occurrences of 'reported success it did not achieve' in the 30 289-byte prompt), so the model alone decides whether the reader learns about them. Whole narrated document read: 'All systems nominal ... Everything completed successfully' x4, 'No section is degraded.', 'Overall status complete'. The narrated path is strictly less honest than the fallback path.

**Repro:**
```
DDR_NARRATOR_CMD=/tmp/ddr-adv/dump-narrator.py ./scripts/reportctl --config /tmp/ddr-adv/config-g.json run --date 2026-08-17 --no-emit
grep -c 'reported success it did not achieve' /tmp/ddr-adv/last-prompt.txt   # -> 2 (model was told)
grep -c 'reported success it did not achieve' /tmp/ddr-adv/g-art/2026-08-17/report.md   # -> 0 (reader was not)
```

## 7. [HIGH] Deployment state: the merged pipeline is the one that will actually run

**Evidence:** Not a code defect, but it makes the whole property moot until fixed. (1) The live config is still schema v1: `./scripts/reportctl --config ~/.config/delonet-daily-report/report.json validate` -> {"error": "config: unknown keys: daily, inference, topics"}, EXIT=2. The spec's own verification block runs every command against that path. (2) No ~/.hermes/skills/delonet-daily-report symlink exists; only `candystore-daily-journal -> .../all-skills/candystore-daily-journal`. (3) The old lying cron job is still enabled and scheduled: ~/.hermes/profiles/33god-pm/cron/jobs.json job 'candystore-daily-journal', enabled: true, '0 6 * * *', next_run_at 2026-08-19T06:00:00-04:00, last_status 'ok'. So tomorrow at 06:00 the pipeline that hardcodes outcome.status='complete' runs again, unchanged.

**Repro:**
```
./scripts/reportctl --config ~/.config/delonet-daily-report/report.json validate; echo EXIT=$?
ls -la ~/.hermes/skills/ | grep -iE 'delonet|candystore'
python3 -c "import json;print([ (j['name'],j['enabled'],j['schedule_display'],j['next_run_at']) for j in json.load(open('/home/delorenj/.hermes/profiles/33god-pm/cron/jobs.json'))['jobs']])"
```

## 8. [HIGH] the git-tracked 33GOD mirror is written as an atomic pair

**Evidence:** run.py:396-418 mirror_generation() does atomic_write_text(target/'report.md') then atomic_write(target/'report.json') as two independent transactions with no staging dir, no pointer and no barrier. After SIGKILL between them: mirror/2026-08-17/report.md run_id = ddr-2026-08-17-f2c33383 (new), mirror/2026-08-17/report.json run_id = ddr-2026-08-17-a8fb08c1 (old) -> MISMATCH. This is the directory the orchestrator commits into 33GOD, so a torn pair is what lands in git and what a human or Holocene reads. Secondary defect from the same window: `ls -la` shows report.md left at mode 0600 because the chmod(0o644) loop at run.py:407-409 only runs after BOTH writes succeed.

**Repro:**
```
KILL_PHASE=mirror KILL_SLEEP=120 KILL_CONFIG=/tmp/ddr-atomicity/config.json DDR_MIRROR_DIR=/tmp/ddr-atomicity/mirror python3 /tmp/ddr-atomicity/kill_harness.py & ; wait for 'WINDOW-OPEN mirror'; kill -9 $PID
```

## 9. [HIGH] the 33GOD mirror is only written for a generation that passed verification

**Evidence:** run.py:660-711 orders the steps publish -> verify_published -> mirror_generation -> `if not verified["ok"]: status=failed; return EXIT_ERROR`. The mirror is written BEFORE the gate. Observed: {"status":"failed","exit":2,"mirror":{"attempted":true,"ok":true},"event":"bloodbank.v1.reporting.report.failed"} — and mirror/2026-08-17/report.md had already been overwritten with run ddr-2026-08-17-657d871f, whose second line of prose reads "Overall report status: partial." A run that exited 2 as failed leaves a document in the git mirror claiming partial, with nothing in the mirrored pair recording the failure. This is the prime-directive violation the merge exists to eliminate, relocated into the one artifact humans actually read.

**Repro:**
```
python3 /tmp/ddr-atomicity/verify_fail_harness.py (wraps run.verify_published to return ok:False, simulating a corrupt/unreadable generation at verify time; no source file modified)
```

## 10. [HIGH] a run only reports `verified: true` about the generation it actually published

**Evidence:** reportctl_archive.py:115-193 verify_published(config, date) resolves the generation through current.json, not through the generation publish() just returned, and run.py:660-686 runs publish then verify with no lock spanning them. Verbatim harness output: {"run_says_published_generation": "fa5c19eec095457abc62bb3d15708478", "run_says_verified": true, "run_says_problems": [], "current_json_actually_points_at": "a3f26452ca7a4f91aa781b77dd8830fa", "SAME": false}. The run asserts its own generation verified when a different generation was the one checked. Exit 0. That is a green about an artifact nobody looked at.

**Repro:**
```
python3 /tmp/ddr-atomicity/verify_race.py with OTHER_GEN=<a different complete generation> — pauses 8s between publish() and verify_published() and lands a `reportctl archive` inside that window
```

## 11. [HIGH] a published generation is an atomic snapshot of exactly one run

**Evidence:** reportctl_archive.py:30-64 artifact_health validates the artifact and checks fresh_until, but never compares artifact['run_id'] to the run's run_id. Observed on the clean tree: run ddr-2026-08-17-fde8ae6d published a manifest with run_id ddr-2026-08-17-fde8ae6d and sections {dev-activity: complete, fleet-health: complete, pr-maintenance: complete, report-delivery: complete}, while the dev-activity artifact inside it was produced by ddr-2026-08-17-deadbeef 23 hours earlier. `verify --require-complete` returned ok True, status complete, degraded [], problems [] and EXIT=0. Consequence for this lens: an interrupted run leaves a partial set of section files in artifact_dir/<date>/sections/, and the NEXT run silently adopts the survivors and publishes them under its own run_id. A reader of the published generation cannot distinguish one coherent collection from a Frankenstein of two runs up to 24h apart, and the strictest gate in the system green-lights it.

**Repro:**
```
reportctl --config /tmp/ddr-atomicity/config.json run --date 2026-08-17 --no-emit --no-mirror   # seed all four sections\n# age one artifact 23h and stamp a foreign run_id (still inside max_age_hours=24)\nreportctl --config /tmp/ddr-atomicity/config.json run --date 2026-08-17 --no-emit --no-mirror --section fleet-health\nreportctl --config /tmp/ddr-atomicity/config.json verify --date 2026-08-17 --require-complete
```

## 12. [HIGH] S1 AC: `reportctl --config <live path> validate` passes on a migrated live config; reportctl_config.py migrates schema v1 -> v2

**Evidence:** The live config was never migrated and no migration path exists. `./scripts/reportctl --config /home/delorenj/.config/delonet-daily-report/report.json validate` prints {"error": "config: unknown keys: daily, inference, topics"} and exits 2. The file is still the July v1 document (mtime Jul 16 01:15, version 1, `topics`/`daily`/`inference`, all topics enabled:false). There is no `migrate` subcommand in reportctl_cli.build_parser (validate/paths/status/collect/run/verify/archive only) and no v1->v2 converter anywhere in scripts/. The only config that loads is assets/example-config.v2.json, which lives INSIDE the skill — so every command in the plan's Verification block fails as written, and the S5 cron job would have no operator-owned config to point at. SKILL.md papers over this by telling the operator to copy the example by hand, which contradicts the plan's stated S1 acceptance criterion.

**Repro:**
```
cd /home/delorenj/code/skillex/all-skills/delonet-daily-report && ./scripts/reportctl --config /home/delorenj/.config/delonet-daily-report/report.json validate; echo EXIT=$?
```

## 13. [HIGH] "Truncation is always recorded in caveats" — truncation is explicit ("showing 30 of 43") everywhere it occurs, in the document a human actually reads

**Evidence:** True of the artifacts, false of the published report on the normal (narrated) path. run.py:compose_report uses narration.bodies, and for every narratable section the LLM body REPLACES narrate.section_body() — which is the only thing that renders the Caveats and Detail blocks. Only the Status line and coverage-freshness survive deterministically. Measured on the real 21:55 narrated run now sitting in the git mirror: `grep -o "showing [0-9]* of [0-9]*" _bmad-output/daily-journals/2026-08-17/report.md` returns ZERO matches, and `grep -c "decisions truncated: showing 30 of 43"` returns 0 — while the dev-activity artifact for that same run carries ['projects truncated: showing 20 of 48','decisions truncated: showing 30 of 43','committing sessions truncated: showing 30 of 54','operational events truncated: showing 20 of 43', '33 project(s) ... no configured project root']. The deterministic render of the identical data (run with --no-narrate) shows all seven: showing 20 of 43, 20 of 48, 20 of 48 projects, 24 of 28 metrics, 30 of 43, 30 of 54, 60 of 221 detail lines. Today's model happened to gesture at truncation qualitatively ("the report truncates projects, decisions, committing sessions, and operational events") with no numbers; that is model discretion, not a guarantee. A terser response drops the gap entirely and nothing in the pipeline notices.

**Repro:**
```
grep -o "showing [0-9]* of [0-9]*" /home/delorenj/code/33GOD/_bmad-output/daily-journals/2026-08-17/report.md | sort -u   # empty;  then compare a --no-narrate run's report.md, which lists all of them
```

## 14. [MEDIUM] A collector cannot claim complete with nothing behind it

**Evidence:** collectors/base.py to_artifact() explicitly refuses a bare NON-complete status (forces a reason, lines 178-181) but applies no symmetric rule to a bare complete one. A collector returning SectionResult(id=..., status='complete') with no summary, no metrics, no detail yields:

  {"status": "complete", "summary": "dev-activity: collector produced no summary", "caveats": ["collector produced no summary"]}

and end-to-end with a working narrator:
  RUN EXIT=0 | status complete | EVENT outcome {"status":"complete","sections":{"dev-activity":"complete"}} | verify --require-complete EXIT=0

Nothing catches it at any status surface. (Positively: the other four abuse shapes DO fail correctly -- unknown status -> failed, wrong return type -> failed, raised exception -> failed, fresh_until in the past -> stale.)

**Repro:**
```
# temporary collector (created and removed during this pass):
# def collect(section, date, config): return SectionResult(id=section['id'], status='complete')
ADV_MODE=empty FAKE_NARR=ok DDR_NARRATOR_CMD=/tmp/ddr-adv/fake-narrator.py \
  ./scripts/reportctl --config /tmp/ddr-adv/config-liar.json run --date 2026-08-17 --no-emit; echo EXIT=$?
./scripts/reportctl --config /tmp/ddr-adv/config-liar.json verify --date 2026-08-17 --require-complete; echo EXIT=$?
```

## 15. [MEDIUM] A configuration that turns the report off cannot look like a successful report

**Evidence:** This is the exact shape delonet died in on 2026-07-25 ('All topics enabled: false'). Setting enabled=false + required=false on dev-activity, fleet-health and pr-maintenance leaves one enabled required section and produces a fully green run with no trace that the other three were ever configured:

  EXIT=0
  status complete | manifest {'report-delivery': 'complete'}
  EVENT {"status": "complete", "sections": {"report-delivery": "complete"}}
  verify --require-complete EXIT=0
  grep -ci 'developer activity|fleet|pr maintenance' report.md  ->  0

The only guard (reportctl_config.py:213) is 'at least one enabled section must be required', which a single surviving section satisfies. Coverage is enumerated from config, so a config that expects nothing is never missing anything.

**Repro:**
```
python3 -c "import json;c=json.load(open('/tmp/ddr-adv/config.json'));[s.update(enabled=False,required=False) for s in c['sections'] if s['id']!='report-delivery'];json.dump(c,open('/tmp/ddr-adv/config-disabled.json','w'))"
FAKE_NARR=ok DDR_NARRATOR_CMD=/tmp/ddr-adv/fake-narrator.py ./scripts/reportctl --config /tmp/ddr-adv/config-disabled.json run --date 2026-08-17 --no-emit; echo EXIT=$?
```

## 16. [MEDIUM] A failed Bloodbank emission is visible in the report's status

**Evidence:** With Dapr unreachable the run still reports complete and exits 0, and no caveat is appended to outcome['caveats'] or to the published report -- the failure exists only inside the nested 'event' object of the run's stdout JSON:

  EXIT=0
  status complete | caveats []
  event {"emitted": false, "error": "<urlopen error [Errno 111] Connection refused>", "outcome_status": "complete", "status_code": null, ...}

The envelope is written to disk regardless, so the run 'succeeded' at a step that did not happen. Downstream (Candystore, Holocene, and tomorrow's report_delivery cross-check) sees nothing; and per the finding above, the cross-check that would notice the gap does not change any status either. Contrast the mirror path, which at least appends 'mirror failed: ...' to outcome['caveats'].

**Repro:**
```
DAPR_HTTP_PORT=9 FAKE_NARR=ok DDR_NARRATOR_CMD=/tmp/ddr-adv/fake-narrator.py DDR_MIRROR_DIR=/tmp/me \
  ./scripts/reportctl --config /tmp/ddr-adv/config-e.json run --date 2026-08-17; echo EXIT=$?
```

## 17. [MEDIUM] The Bloodbank envelope's delivery block describes what actually happened

**Evidence:** Two mismatches, both in run.py's _delivery_block/_failed_delivery_block:
(a) mirror attempted and FAILED on a completed run -> envelope says {"status": "skipped", "attempts": 0, "reason": "mirror_failed"}. attempts:0 is factually false (one attempt was made) and 'skipped' reads as a choice rather than a failure. The honest shape ({"status":"failed","attempts":1}) exists in _failed_delivery_block but is only reachable on the report.failed path.
(b) inverse on the failed path: a run with overall=failed whose mirror SUCCEEDED emits {"status": "not_attempted", "channel": null, "attempts": 0} even though the file was written (confirmed present on disk).
Outcome.status and the per-section map themselves are correctly derived from the manifest -- I found no hardcoding there, and the report-narration pseudo-component behaves as documented.

**Repro:**
```
chmod 555 /tmp/ddr-adv/ro-mirror
FAKE_NARR=ok DDR_NARRATOR_CMD=/tmp/ddr-adv/fake-narrator.py DDR_MIRROR_DIR=/tmp/ddr-adv/ro-mirror \
  ./scripts/reportctl --config /tmp/ddr-adv/config-m.json run --date 2026-08-17 --no-emit
python3 -c "import json;e=json.load(open('/tmp/ddr-adv/m-art/2026-08-17/report-event.json'));print(e['data']['delivery'])"
# -> {'status':'skipped','attempts':0,'reason':'mirror_failed'}
```

## 18. [MEDIUM] the mirror always copies from the generation current.json names

**Evidence:** mirror_generation() copies published['markdown'] / published['report_json'] — absolute paths inside the generation this run created — never resolving current.json. The `archive` subcommand takes only current.lock (reportctl_runtime.py:144) and never the run's .run.lock, so it legitimately moves the pointer under an in-flight run. Result: current.json generation = 7668da5effe3467f9d0a93fb4d6bc7fa (run ddr-2026-08-17-a8fb08c1) while mirror report.json AND report.md both carried run ddr-2026-08-17-b85ba689 -> MIRROR MATCHES POINTER? False. The archive says one report is current; git gets a different one.

**Repro:**
```
start a run paused in its mirror window (KILL_PHASE=mirror KILL_SLEEP=12), then in that window run: reportctl --config config.json archive --report <other-gen>/report.json --markdown <other-gen>/report.md --manifest <other-gen>/run-manifest.json
```

## 19. [MEDIUM] what lands in 33GOD can express the run's derived status

**Evidence:** DailyReport top-level keys are exactly ['coverage','generated_at','markdown_path','report_date','run_id','schema_version','sections','title'] — there is no overall `status` field, and daily-report.schema.json's required list confirms it. mirror_generation copies only report.md and report.json, not run-manifest.json. So the machine-readable half of what gets committed to 33GOD carries no run status, no narration outcome, no verification outcome and no delivery outcome. coverage.degraded does correctly list failed sections (verified: with CANDYSTORE_URL=http://127.0.0.1:9 the mirrored coverage became {complete:[fleet-health,pr-maintenance], degraded:[dev-activity,report-delivery]}), but a run that is partial for any other reason, or failed at verification, is indistinguishable from a clean one in the mirrored JSON.

**Repro:**
```
python3 -c "import json;print(sorted(json.load(open('/tmp/ddr-atomicity/mirror/2026-08-17/report.json')).keys()))"
```

## 20. [MEDIUM] A published run's manifest describes what THAT run collected

**Evidence:** reportctl_archive.artifact_health() reads each section file back and checks topic_id and fresh_until, but never compares run_id to the current run. So any artifact left on disk for the same report date and still inside its freshness window (default 24h) is adopted by the next run and stamped into a manifest bearing the NEW run_id. Proven: after `run --section dev-activity`, /tmp/s5-art/2026-08-17/run-manifest.json has run_id ddr-2026-08-17-2c5d986c and lists pr-maintenance and report-delivery as complete, while those two section files carry run_id ddr-2026-08-17-c3b162ce from the previous run. The published report.json carries the new run_id too. Reachable in normal operation through `--section` and through any same-day retry. The emitted Bloodbank event then attributes another run's collection to this run_id.

**Repro:**
```
cd /tmp/s5-art/2026-08-17 && python3 -c "import json;print(json.load(open('run-manifest.json'))['run_id']);[print(n, json.load(open(f'sections/{n}.json'))['run_id']) for n in ('dev-activity','pr-maintenance','report-delivery')]"
```

## 21. [LOW] verify proves the published generation is internally coherent

**Evidence:** verify_published() cross-checks run_id and report_date between report.json and run-manifest.json, and re-derives status from the manifest -- but never compares report.json's coverage.complete/degraded (or report.md's rendered 'Overall status: X') against the manifest statuses. Editing only the archived run-manifest.json so report-delivery is 'failed', leaving report.json's coverage claiming it complete, gives:

  "ok": true, "problems": [], "status": "partial", "degraded": ["report-delivery"]   EXIT=0

while the published report.md the human/mirror actually shows still reads 'Overall status complete' and 'No section is degraded.' Requires archive tampering to trigger, but it is precisely the coherence check 'internally coherent' promises. (Positively: deleting report.md from the generation IS caught -- 'published generation is missing report.md', EXIT=3.)

**Repro:**
```
GEN=$(python3 -c "import json;print(json.load(open('/tmp/ddr-adv/g-arc/2026/08/2026-08-17/current.json'))['generation'])")
python3 -c "import json;p='/tmp/ddr-adv/g-arc/2026/08/2026-08-17/generations/$GEN/run-manifest.json';m=json.load(open(p));[s.update(status='failed',reason='tampered') for s in m['sections'] if s['id']=='report-delivery'];json.dump(m,open(p,'w'))"
./scripts/reportctl --config /tmp/ddr-adv/config-g.json verify --date 2026-08-17; echo EXIT=$?   # ok:true, EXIT=0
```

## 22. [LOW] The pipeline refuses to certify a day it cannot possibly have data for

**Evidence:** No guard that --date names a completed past day, and an all-zero collection is indistinguishable from a successful one at the status level:

  $ ... run --date 2099-01-01 ; echo $?
  EXIT=0 | status complete | all four sections complete
  dev-activity: complete | '0 events across 0 project(s) on 2099-01-01: 0 session(s), 0 decision(s), 0 committing session(s), 0 commit(s) in 9 repository(ies).'
  $ ... verify --date 2099-01-01 --require-complete ; echo $?
  EXIT=0

The summary is honest about the zeros, but a cron job with a TZ/date-arithmetic bug would publish an empty green report and nothing would flag it.

**Repro:**
```
FAKE_NARR=ok DDR_NARRATOR_CMD=/tmp/ddr-adv/fake-narrator.py DDR_MIRROR_DIR=/tmp/mf \
  ./scripts/reportctl --config /tmp/ddr-adv/config-f.json run --date 2099-01-01 --no-emit; echo EXIT=$?
```

## 23. [LOW] failed or interrupted publishes are eventually reaped

**Evidence:** No GC, prune or retention code exists anywhere in the package (the only grep hits are pr_maintenance.py comments about pr-crusher's own retention). Sandbox: 25 complete generations plus 1 never-reaped .stage- directory for a single date. Live state: 23 generations, 924K for 2026-08-17 alone, growing per run. A .stage-<uuid> directory left by an interrupted publish is never cleaned by any subsequent successful run. Not a correctness hazard for readers (every reader goes through current.json and _generations filters dot-prefixed entries) but unbounded growth with no operator-visible policy.

**Repro:**
```
ls -d state/archive/2026/08/2026-08-17/generations/*/ | wc -l ; ls -d .../generations/.stage-*/ ; grep -rn 'prune|retention|rmtree|cleanup' scripts/*.py scripts/collectors/*.py
```

## 24. [LOW] the emitted delivery block states what actually happened when the mirror fails

**Evidence:** EXIT=0. The run correctly recorded mirror ok:false with the errno and added the caveat "mirror failed: [Errno 13] Permission denied", and the envelope's delivery.reason is "mirror_failed" — good. But _delivery_block (run.py:737-754) emits {"status":"skipped","attempts":0} for a mirror that was attempted once and failed. attempts:0 is factually false, and "skipped" reads as a choice rather than a failure. _failed_delivery_block (run.py:757-765) gets this right ({"status":"failed","attempts":1}) but is only reachable on the overall-failed path. A consumer filtering on delivery.status will not see this as a delivery failure.

**Repro:**
```
chmod 500 /tmp/ddr-atomicity/mirror-ro; DDR_MIRROR_DIR=/tmp/ddr-atomicity/mirror-ro reportctl --config config.json run --date 2026-08-17 --no-emit
```

## 25. [LOW] The Python validators and the normative JSON Schemas in assets/contracts/ agree

**Evidence:** One dangerous-direction divergence out of 2,124 differential mutations (1,376 across the three artifact contracts + 748 across the config contract): validate_run_manifest and validate_daily_report ACCEPT schema_version: true, which run-manifest.schema.json and daily-report.schema.json REJECT ("1 was expected"). Cause: `manifest["schema_version"] != RUN_MANIFEST_VERSION` where the version is 1, and in Python True == 1. SectionArtifact (const 2) is immune since True != 2. Reachable through the operator-facing `archive` subcommand: I poisoned a real report.json and run-manifest.json with schema_version: true and `reportctl archive --report ... --markdown ... --manifest ...` exited 0 and published generation 680e16ace83b478ea92cb12946bc1e4c whose report.json contains "schema_version": true — a generation the normative schema rejects. Every other divergence (80 on artifacts, 13 on config) is in the safe direction: the Python validator is stricter (rejects whitespace-only strings, non-tz timestamps, empty section arrays, wrong section ordering, invalid IANA zones) than the schema can express.

**Repro:**
```
cd /home/delorenj/code/skillex/all-skills/delonet-daily-report && python3 -c "import json,sys;sys.path.insert(0,'scripts');from reportctl_contracts import validate_run_manifest;from reportctl_config import load_config;from pathlib import Path;c=load_config(Path('assets/example-config.v2.json'));m=json.load(open('/home/delorenj/.local/state/delonet-daily-report/artifacts/2026-08-17/run-manifest.json'));m['schema_version']=True;validate_run_manifest(m,c);print('ACCEPTED by python; schema says: 1 was expected')"
```

## 26. [LOW] Plan's failure-injection AC: dead Candystore yields dev-activity=failed, overall=partial, and a NON-ZERO exit

**Evidence:** Statuses are right, exit code is not. `CANDYSTORE_URL=http://127.0.0.1:9 reportctl run --date 2026-08-17 --no-narrate --no-emit` gave dev-activity=failed (reason names the URL and errno 111), report-delivery=partial, overall=partial, event outcome_status=partial — and EXIT=0. run.py:`exit_code = EXIT_UNMET if outcome["status"] == "failed" else EXIT_OK`. SKILL.md deliberately documents this ("complete and partial both exit 0, because a report that admits a gap is a successful report"), so the code and its own docs agree and the PLAN is the odd one out — but a cron wrapper written against the plan will treat a run that lost its primary data source as a success.

**Repro:**
```
cd /home/delorenj/code/skillex/all-skills/delonet-daily-report && CANDYSTORE_URL=http://127.0.0.1:9 ./scripts/reportctl --config /tmp/s5-config.json run --date 2026-08-17 --no-narrate --no-emit >/dev/null; echo EXIT=$?
```

## 27. [LOW] No silent truncation anywhere in the render path

**Evidence:** One site. narrate.fallback_bodies, risks-watchlist branch (scripts/narrate.py:533-535): `for caveat in (entry.get("caveats") or [])[:MAX_CAVEATS_IN_BODY]` drops caveats past 20 per section with no "showing X of Y" note, unlike _list_block/_detail_block/_metrics_line which all record it. Reachable: report_delivery alone can emit 12 disagreement caveats plus duplicates plus source notes. Mitigated — the full caveat list still appears in that section's own body via _list_block, so the information survives elsewhere in the document. Every other slice I swept (report_delivery disagreements, pr_maintenance errors and ticks, fleet_health detail lines, dev_activity decisions/commits/notes/projects/detail, enforce_byte_cap, narrator payload shrink) states both numbers.

**Repro:**
```
sed -n '533,535p' /home/delorenj/code/skillex/all-skills/delonet-daily-report/scripts/narrate.py
```

## 28. [LOW] The git-tracked mirror contains only the current pipeline's output

**Evidence:** /home/delorenj/code/33GOD/_bmad-output/daily-journals/2026-08-17/ still holds journal.txt (17811 bytes) and report_event.json (1766 bytes) from the retired journal's 12:04 run, beside the new report.md/report.json. That stale report_event.json is the hardcoded-status event this whole merge exists to kill (outcome.status "complete" with four "complete" sections, run_id dev-journal-2026-08-17-160447) and it is INVALID against the real Bloodbank schema at 33GOD/bloodbank/schemas/bloodbank/v1/reporting/report.completed.v1.json (2 errors: artifact ids are absolute filesystem paths, failing ^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$). If the orchestrator commits the directory, the retired system's false-green event ships with the replacement.

**Repro:**
```
ls -la /home/delorenj/code/33GOD/_bmad-output/daily-journals/2026-08-17/
```

## 29. [LOW] A crash mid-publish leaves no debris

**Evidence:** current.json integrity holds perfectly (see the HOLDS finding), but the SIGKILL leaves an unreferenced generation directory behind forever: before the kill, generations were [1648711f..., 44a8a742...]; after, [1648711f..., 44a8a742..., fdfd90e6...] with current.json still naming 44a8a742. Nothing ever reclaims fdfd90e6. report_delivery._scan_day has a branch for "generations staged but current.json never written", so the archive scanner is aware of the shape, but no cleanup exists. Cosmetic/disk-growth only.

**Repro:**
```
ls /tmp/s5-arch/2026/08/2026-08-17/generations/ ; python3 -c "import json;print(json.load(open('/tmp/s5-arch/2026/08/2026-08-17/current.json'))['generation'])"
```

